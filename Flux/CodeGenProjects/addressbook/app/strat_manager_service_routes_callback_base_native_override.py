# python imports
import copy
import json
import logging
import time
from typing import Type, Set, Final
import asyncio
from pathlib import PurePath
from datetime import date
import threading

# third-party package imports
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

# project imports
from Flux.CodeGenProjects.addressbook.app.service_state import ServiceState
from FluxPythonUtils.scripts.utility_functions import avg_of_new_val_sum_to_avg, store_json_or_dict_to_file, \
    load_json_dict_from_file, YAMLConfigurationManager, parse_to_int, get_native_host_n_port_from_config_dict
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.market_data.generated.Pydentic.market_data_service_model_imports import TopOfBookBaseModel, \
    SymbolOverviewBaseModel
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback
from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import is_service_up, \
    create_alert, get_new_strat_limits, \
    get_single_exact_match_ongoing_strat_from_symbol_n_side, get_portfolio_limits, is_ongoing_pair_strat, \
    create_portfolio_limits, get_order_limits, create_order_limits, except_n_log_alert, \
    get_consumable_participation_qty, get_order_journal_log_key, get_order_snapshot_log_key, \
    get_symbol_side_snapshot_log_key, \
    get_symbol_side_key, get_fills_journal_log_key, get_pair_strat_log_key, get_strat_brief_log_key, \
    get_ongoing_strats_from_symbol_n_side
from Flux.CodeGenProjects.addressbook.app.static_data import SecurityRecordManager

CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

MARKET_DATA_DIR = PurePath(__file__).parent.parent.parent / "market_data"
md_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(MARKET_DATA_DIR / "data" / "config.yaml"))


native_host, native_port = get_native_host_n_port_from_config_dict(config_yaml_dict)
market_data_service_cache_host, market_data_service_cache_port = \
    md_config_yaml_dict.get("beanie_host"), parse_to_int(md_config_yaml_dict.get("beanie_port"))


strat_manager_service_native_web_client = \
    StratManagerServiceWebClient.set_or_get_if_instance_exists(native_host, native_port)
market_data_service_web_client = \
    MarketDataServiceWebClient.set_or_get_if_instance_exists(market_data_service_cache_host,
                                                             market_data_service_cache_port)


class StratManagerServiceRoutesCallbackBaseNativeOverride(StratManagerServiceRoutesCallback):
    def __init__(self):
        self.asyncio_loop = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.static_data: SecurityRecordManager | None = None
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, SymbolOverviewBaseModel | None] = {"USD|SGD": None}
        self.usd_fx = None

        # dict of pair_strat_id and their activated tickers from today
        self.active_ticker_pair_strat_id_dict_lock: asyncio.Lock = asyncio.Lock()
        self.pair_strat_id_n_today_activated_tickers_dict_file_name: str = f'pair_strat_id_n_today_activated_' \
                                                                           f'tickers_dict_{date.today()}'
        self.pair_strat_id_n_today_activated_tickers_dict: Dict[str, int] | None = \
            load_json_dict_from_file(self.pair_strat_id_n_today_activated_tickers_dict_file_name, CURRENT_PROJECT_DATA_DIR,
                                     must_exist=False)
        if self.pair_strat_id_n_today_activated_tickers_dict is None:
            self.pair_strat_id_n_today_activated_tickers_dict = dict()
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30

        self.minimum_refresh_interval = 30
        super().__init__()

    def static_data_periodic_refresh(self):
        pass

    def _check_and_create_order_and_portfolio_limits(self) -> None:
        if (order_limits := get_order_limits()) is None:
            order_limits = create_order_limits()
        if (portfolio_limits := get_portfolio_limits()) is None:
            portfolio_limits = create_portfolio_limits()
        return

    @except_n_log_alert(severity=Severity.Severity_CRITICAL)
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        md_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "md_service failed, exception: ")
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            # validate essential services are up, if so, set service ready state to true
            # static data and md service are considered essential
            if self.service_up and static_data_service_state.ready and md_service_state.ready:
                self.service_ready = True
            if not self.service_up:
                try:
                    if is_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                        self._check_and_create_order_and_portfolio_limits()
                        self.service_up = True
                        should_sleep = False
                    else:
                        should_sleep = True
                        service_up_no_error_retry_count -= 1
                except Exception as e:
                    logging.exception("unexpected: service startup threw exception, "
                                      f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                      f";;;exception: {e}", exc_info=True)
            else:
                should_sleep = True
                # any periodic refresh code goes here
                try:
                    # Gets all open orders, updates residuals and raises pause to strat if req
                    strat_manager_service_native_web_client.trigger_residual_check_query_client(["OE_ACKED", "OE_UNACK"])
                except Exception as e:
                    logging.exception("periodic open order check failed, "
                                      "periodic order state checks will not be honored and retried in next periodic cycle"
                                      f";;;exception: {e}", exc_info=True)
                # service loop: manage all sub-services within their private try-catch to allow high level service to
                # remain partially operational even if some sub-service is not available for any reason
                if not static_data_service_state.ready:
                    try:
                        self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                        if self.static_data is not None:
                            static_data_service_state.ready = True
                        else:
                            raise Exception("self.static_data init to None, unexpected!!")
                    except Exception as e:
                        static_data_service_state.handle_exception(e)
                else:
                    # refresh static data periodically (maybe more in future)
                    try:
                        self.static_data_periodic_refresh()
                    except Exception as e:
                        static_data_service_state.handle_exception(e)
                        static_data_service_state.ready = False  # forces re-init in next iteration

                if not md_service_state.ready:
                    try:
                        if self.update_fx_symbol_overview_dict_from_http():
                            md_service_state.ready = True
                        else:
                            logging.error("md service init failed - we re-try in a bit")
                    except Exception as e:
                        md_service_state.handle_exception(e)
                        md_service_state.ready = False  # forces re-try in next iteration

    async def read_all_portfolio_status_pre(self):
        if not self.asyncio_loop:
            self.asyncio_loop = asyncio.get_running_loop()

    def update_fx_symbol_overview_dict_from_http(self) -> bool:
        symbol_overviews: List[SymbolOverviewBaseModel] = \
            market_data_service_web_client.get_all_symbol_overview_client()
        if symbol_overviews:
            symbol_overview_: SymbolOverviewBaseModel
            for symbol_overview_ in symbol_overviews:
                if symbol_overview_.symbol in self.fx_symbol_overview_dict:
                    # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
                    self.fx_symbol_overview_dict[symbol_overview_.symbol] = symbol_overview_
                    self.usd_fx = symbol_overview_.closing_px
                    return True
        # all else - return False
        return False

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat for now - may extend to accept symbol and send revised px according to
        underlying trading currency
        """
        return px / self.usd_fx

    def get_local_px_or_notional(self, px_or_notional: float, system_symbol: str):
        return px_or_notional * self.usd_fx

    def app_launch_pre(self):
        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    async def create_order_journal_pre(self, order_journal_obj: OrderJournal) -> None:
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_order_journal_pre not ready - service is not initialized yet, " \
                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # updating order notional in order journal obj

        if order_journal_obj.order_event == OrderEventType.OE_NEW and order_journal_obj.order.px == 0:
            top_of_book_obj = self._get_top_of_book_from_symbol(order_journal_obj.order.security.sec_id)
            if top_of_book_obj is not None:
                order_journal_obj.order.px = top_of_book_obj.last_trade.px
            else:
                err_str_ = f"received order journal px 0 and to update px, received TOB also as {top_of_book_obj}, " \
                           f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
        # If order_journal is not new then we don't care about px, we care about event_type and if order is new
        # and px is not 0 then using provided px

        if order_journal_obj.order.px is not None and order_journal_obj.order.qty is not None:
            order_journal_obj.order.order_notional = \
                self.get_usd_px(order_journal_obj.order.px,
                                order_journal_obj.order.security.sec_id) * order_journal_obj.order.qty
        else:
            order_journal_obj.order.order_notional = 0

    async def create_order_journal_post(self, order_journal_obj: OrderJournal):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            residual_compute_shared_lock
        async with residual_compute_shared_lock:
            await self._update_order_snapshot_from_order_journal(order_journal_obj)

    def get_generic_read_route(self):
        return None

    async def _get_symbol_side_snapshot_from_symbol_side(self, symbol: str,
                                                         side: Side) -> List[SymbolSideSnapshot] | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(get_symbol_side_snapshot_from_symbol_side(symbol, side),
                                                            self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) > 1:
            err_str_ = f"Found multiple objects of symbol_side_snapshot for key: " \
                       f"{get_symbol_side_key([(symbol, side)])}"
            logging.error(err_str_)
            return None
        else:
            return symbol_side_snapshot_objs

    async def _get_order_snapshot_from_order_journal_order_id(self,
                                                              order_journal_obj: OrderJournal) -> OrderSnapshot | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json

        order_id = order_journal_obj.order.order_id
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(order_id),
                                                      self.get_generic_read_route())
        if len(order_snapshot_objs) == 1:
            return order_snapshot_objs[0]
        elif len(order_snapshot_objs) == 0:
            err_str_ = f"Could not find any order snapshot with order_id {order_id} to be updated for " \
                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)};;; " \
                       f"order_journal: {order_journal_obj}"
            logging.error(err_str_)
        else:
            err_str_ = f"Match should return list of only one order_snapshot obj per order_id, " \
                       f"returned {order_snapshot_objs} to be updated for order_journal_key " \
                       f"{get_order_journal_log_key(order_journal_obj)};;; order_journal: {order_journal_obj}"
            logging.error(err_str_)

    async def _check_state_and_get_order_snapshot_obj(self, order_journal_obj: OrderJournal,
                                                      expected_status_list: List[str]) -> OrderSnapshot | None:
        """
        Checks if order_snapshot holding order_id of passed order_journal has expected status
        from provided statuses list and then returns that order_snapshot
        """
        order_snapshot_obj = await self._get_order_snapshot_from_order_journal_order_id(order_journal_obj)
        if order_snapshot_obj is not None:
            if order_snapshot_obj.order_status in expected_status_list:
                return order_snapshot_obj
            else:
                ord_journal_key: str = get_order_journal_log_key(order_journal_obj)
                ord_snapshot_key: str = get_order_snapshot_log_key(order_snapshot_obj)
                err_str_: str = f"_check_state_and_get_order_snapshot_obj: order_journal: {ord_journal_key} " \
                                f"received with event: {order_journal_obj.order_event}, to update status of " \
                                f"order_snapshot: {ord_snapshot_key}, with status: " \
                                f"{order_snapshot_obj.order_status}, but order_snapshot doesn't contain any of " \
                                f"expected statuses: {expected_status_list}" \
                                f";;; order_journal: {order_journal_obj}, order_snapshot_obj: {order_snapshot_obj}"
                logging.error(err_str_)
        # else not required: error occurred in _get_order_snapshot_from_order_journal_order_id,
        # alert must have updated

    async def _create_symbol_side_snapshot_for_new_order(self,
                                                         new_order_journal_obj: OrderJournal) -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_create_symbol_side_snapshot_http
        security = new_order_journal_obj.order.security
        side = new_order_journal_obj.order.side
        symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(), security=security,
                                                      side=side,
                                                      avg_px=new_order_journal_obj.order.px,
                                                      total_qty=new_order_journal_obj.order.qty,
                                                      total_filled_qty=0, avg_fill_px=0,
                                                      total_fill_notional=0, last_update_fill_qty=0,
                                                      last_update_fill_px=0, total_cxled_qty=0,
                                                      avg_cxled_px=0, total_cxled_notional=0,
                                                      last_update_date_time=new_order_journal_obj.order_event_date_time,
                                                      order_count=1
                                                      )
        symbol_side_snapshot_obj = \
            await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
        return symbol_side_snapshot_obj

    async def _create_update_symbol_side_snapshot_from_order_journal(self, order_journal: OrderJournal,
                                                                     order_snapshot_obj: OrderSnapshot
                                                                     ) -> SymbolSideSnapshot | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http, underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(order_journal.order.security.sec_id,
                                                          order_journal.order.side), self.get_generic_read_route())
        # If no symbol_side_snapshot for symbol-side of received order_journal
        if len(symbol_side_snapshot_objs) == 0:
            if order_journal.order_event == OrderEventType.OE_NEW:
                created_symbol_side_snapshot = await self._create_symbol_side_snapshot_for_new_order(order_journal)
                return created_symbol_side_snapshot
            else:
                err_str_: str = f"no OE_NEW detected for order_journal_key: {get_order_journal_log_key(order_journal)} " \
                                f"failed to create symbol_side_snapshot " \
                                f";;; order_journal: {order_journal}"
                logging.error(err_str_)
                return
        # If symbol_side_snapshot exists for order_id from order_journal
        elif len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            match order_journal.order_event:
                case OrderEventType.OE_NEW:
                    updated_symbol_side_snapshot_obj.order_count = symbol_side_snapshot_obj.order_count + 1
                    updated_symbol_side_snapshot_obj.avg_px = \
                        avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                  order_journal.order.px,
                                                  updated_symbol_side_snapshot_obj.order_count
                                                  )
                    updated_symbol_side_snapshot_obj.total_qty = symbol_side_snapshot_obj.total_qty + order_journal.order.qty
                    updated_symbol_side_snapshot_obj.last_update_date_time = order_journal.order_event_date_time
                case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                    updated_symbol_side_snapshot_obj.total_cxled_qty = symbol_side_snapshot_obj.total_cxled_qty + order_snapshot_obj.cxled_qty
                    updated_symbol_side_snapshot_obj.total_cxled_notional = symbol_side_snapshot_obj.total_cxled_notional + order_snapshot_obj.cxled_notional
                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                            self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                          symbol_side_snapshot_obj.security.sec_id) /
                            updated_symbol_side_snapshot_obj.total_cxled_qty) \
                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0
                    updated_symbol_side_snapshot_obj.last_update_date_time = order_journal.order_event_date_time
                case other_:
                    err_str_ = f"Unsupported StratEventType for symbol_side_snapshot update {other_} " \
                               f"{get_order_journal_log_key(order_journal)}"
                    logging.error(err_str_)
                    return
            updated_symbol_side_snapshot_obj = \
                await underlying_partial_update_symbol_side_snapshot_http(
                    json.loads(updated_symbol_side_snapshot_obj.json(by_alias=True, exclude_none=True)))
            return updated_symbol_side_snapshot_obj
        else:
            err_str_ = f"SymbolSideSnapshot can't be multiple for single symbol and side combination, " \
                       f"order_journal_key: {get_order_journal_log_key(order_journal)}, " \
                       f"received {len(symbol_side_snapshot_objs)} - {symbol_side_snapshot_objs}"
            logging.error(err_str_)
            return

    async def _update_symbol_side_snapshot_from_fill_applied_order_snapshot(self,
                                                                            order_snapshot_obj: OrderSnapshot) \
            -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http, \
            underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(order_snapshot_obj.order_brief.security.sec_id,
                                                          order_snapshot_obj.order_brief.side),
                self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            updated_symbol_side_snapshot_obj.total_filled_qty = \
                symbol_side_snapshot_obj.total_filled_qty + order_snapshot_obj.last_update_fill_qty
            updated_symbol_side_snapshot_obj.total_fill_notional = \
                symbol_side_snapshot_obj.total_fill_notional + \
                (self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                 order_snapshot_obj.order_brief.security.sec_id) *
                 order_snapshot_obj.last_update_fill_qty)
            updated_symbol_side_snapshot_obj.avg_fill_px = \
                self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_fill_notional,
                                              symbol_side_snapshot_obj.security.sec_id) / \
                updated_symbol_side_snapshot_obj.total_filled_qty
            updated_symbol_side_snapshot_obj.last_update_fill_px = order_snapshot_obj.last_update_fill_px
            updated_symbol_side_snapshot_obj.last_update_fill_qty = order_snapshot_obj.last_update_fill_qty
            updated_symbol_side_snapshot_obj.last_update_date_time = order_snapshot_obj.last_update_date_time
            updated_symbol_side_snapshot_obj = \
                await underlying_partial_update_symbol_side_snapshot_http(
                    json.loads(updated_symbol_side_snapshot_obj.json(by_alias=True, exclude_none=True)))
            return updated_symbol_side_snapshot_obj
        else:
            err_str_ = f"SymbolSideSnapshot must be only one per symbol," \
                       f" order_snapshot_key: {get_order_snapshot_log_key(order_snapshot_obj)}, " \
                       f"received {len(symbol_side_snapshot_objs)}, - {symbol_side_snapshot_objs}"
            logging.error(err_str_)

    async def create_order_snapshot_pre(self, order_snapshot_obj: OrderSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if order_snapshot_obj.order_brief.security.sec_type is None:
            order_snapshot_obj.order_brief.security.sec_type = SecurityType.TICKER

    async def create_symbol_side_snapshot_pre(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if symbol_side_snapshot_obj.security.sec_type is None:
            symbol_side_snapshot_obj.security.sec_type = SecurityType.TICKER

    async def update_cxl_order_for_order_cxl_ack(self,
                                                 order_snapshot: OrderSnapshot) -> CancelOrder | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_cancel_order_http, underlying_partial_update_cancel_order_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_by_order_id_filter

        cxl_order_list: List[CancelOrder] | None = await underlying_read_cancel_order_http(
            get_order_by_order_id_filter(order_snapshot.order_brief.order_id), self.get_generic_read_route())

        if len(cxl_order_list) == 1:
            # if cxl-confirmed field is already True
            if cxl_order_list[0].cxl_confirmed:
                err_str_ = f"received cxl_order obj for order_id {order_snapshot.order_brief.order_id} already having " \
                           f"cxl_confirmed field True while updating cxl_order in between order_snapshot update " \
                           f"order_snapshot: {get_order_snapshot_log_key(order_snapshot)};;; " \
                           f"order_snapshot: {order_snapshot}"
                logging.error(err_str_)
                return None
        else:
            if len(cxl_order_list) > 1:
                err_str_ = f"There must be only one cancel_order obj per order_id, " \
                           f"received {len(cxl_order_list)} for order_id {order_snapshot.order_brief.order_id}" \
                           f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot)};;; " \
                           f"cxl_order_list {cxl_order_list} for order_snapshot {order_snapshot}"
                logging.error(err_str_)
                return None
            else:
                # unsolicited cxl case
                return CancelOrderOptional()
        updated_cxl_order = CancelOrderOptional(_id=cxl_order_list[0].id, cxl_confirmed=True)
        confirm_marked_cxl_oder = await underlying_partial_update_cancel_order_http(
            json.loads(updated_cxl_order.json(by_alias=True, exclude_none=True)))
        return confirm_marked_cxl_oder

    async def _update_order_snapshot_from_order_journal(self, order_journal_obj: OrderJournal):
        match order_journal_obj.order_event:
            case OrderEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_create_order_snapshot_http

                order_snapshot = OrderSnapshot(_id=OrderSnapshot.next_id(),
                                               order_brief=order_journal_obj.order,
                                               filled_qty=0, avg_fill_px=0,
                                               fill_notional=0,
                                               cxled_qty=0,
                                               avg_cxled_px=0,
                                               cxled_notional=0,
                                               last_update_fill_qty=0,
                                               last_update_fill_px=0,
                                               create_date_time=order_journal_obj.order_event_date_time,
                                               last_update_date_time=order_journal_obj.order_event_date_time,
                                               order_status=OrderStatusType.OE_UNACK)
                order_snapshot = await underlying_create_order_snapshot_http(order_snapshot)
                symbol_side_snapshot = \
                    await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                      order_snapshot)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot,
                                                                                    symbol_side_snapshot)
                    await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot,
                                                                     symbol_side_snapshot, updated_strat_brief)
                    await self._update_portfolio_status_from_order_journal(
                        order_journal_obj, order_snapshot)
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already

            case OrderEventType.OE_ACK:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj,
                                                                       [OrderStatusType.OE_UNACK])
                if order_snapshot is not None:
                    await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                         last_update_date_time=order_journal_obj.order_event_date_time,
                                                         order_status=OrderStatusType.OE_ACKED).json(by_alias=True,
                                                                                                     exclude_none=True)))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj, [OrderStatusType.OE_UNACK,
                                                                                           OrderStatusType.OE_ACKED])
                if order_snapshot is not None:
                    await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                         last_update_date_time=order_journal_obj.order_event_date_time,
                                                         order_status=OrderStatusType.OE_CXL_UNACK).json(by_alias=True,
                                                                                                         exclude_none=True)))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL_ACK:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_ACKED,
                                            OrderStatusType.OE_UNACK])
                if order_snapshot is not None:
                    order_brief = OrderBrief(**order_snapshot.order_brief.dict())
                    if order_journal_obj.order.text:
                        if order_brief.text:
                            order_brief.text.extend(order_journal_obj.order.text)
                        else:
                            order_brief.text = order_journal_obj.order.text
                    # else not required: If no text is present in order_journal then updating
                    # order snapshot with same obj

                    cxled_qty = order_snapshot.order_brief.qty - order_snapshot.filled_qty
                    cxled_notional = cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                 order_snapshot.order_brief.security.sec_id)
                    avg_cxled_px = \
                        (self.get_local_px_or_notional(cxled_notional, order_snapshot.order_brief.security.sec_id) /
                         cxled_qty) if cxled_qty != 0 else 0
                    order_snapshot = await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                         order_brief=order_brief,
                                                         cxled_qty=cxled_qty,
                                                         cxled_notional=cxled_notional,
                                                         avg_cxled_px=avg_cxled_px,
                                                         last_update_date_time=order_journal_obj.order_event_date_time,
                                                         order_status=OrderStatusType.OE_DOD).json(by_alias=True,
                                                                                                   exclude_none=True)))

                    # updating cancel_order object for this id
                    cxl_marked_cxl_order = await self.update_cxl_order_for_order_cxl_ack(order_snapshot)
                    if cxl_marked_cxl_order is None:
                        return None

                    symbol_side_snapshot = await self._create_update_symbol_side_snapshot_from_order_journal(
                        order_journal_obj, order_snapshot)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot,
                                                                                        symbol_side_snapshot)
                        await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot,
                                                                         symbol_side_snapshot, updated_strat_brief)
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot)
                    # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                    # is None then it means some error occurred in
                    # _create_update_symbol_side_snapshot_from_order_journal which would have got added to alert already

                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_CXL_REJ:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = await self._check_state_and_get_order_snapshot_obj(
                    order_journal_obj, [OrderStatusType.OE_CXL_UNACK])
                if order_snapshot is not None:
                    if order_snapshot.order_brief.qty > order_snapshot.filled_qty:
                        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                            underlying_read_order_journal_http
                        from Flux.CodeGenProjects.addressbook.app.aggregate import \
                            get_last_n_order_journals_from_order_id
                        last_3_order_journals_from_order_id = \
                            await underlying_read_order_journal_http(
                                get_last_n_order_journals_from_order_id(order_journal_obj.order.order_id, 3),
                                self.get_generic_read_route())
                        if last_3_order_journals_from_order_id:
                            if last_3_order_journals_from_order_id[0].order_event == OrderEventType.OE_CXL_REJ:
                                if last_3_order_journals_from_order_id[-1].order_event == OrderEventType.OE_NEW:
                                    order_status = OrderStatusType.OE_UNACK
                                elif last_3_order_journals_from_order_id[-1].order_event == OrderEventType.OE_ACK:
                                    order_status = OrderStatusType.OE_ACKED
                                else:
                                    err_str_ = "3rd order journal from order_journal of status OE_CXL_REJ, must be" \
                                               "of status OE_ACK and OE_UNACK, received last 3 order_journals " \
                                               f"{last_3_order_journals_from_order_id}, " \
                                               f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                                    logging.error(err_str_)
                                    return None
                            else:
                                err_str_ = "Recent order journal must be of status OE_CXL_REJ, " \
                                           f"received last 3 order_journals {last_3_order_journals_from_order_id}, " \
                                           f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                                logging.error(err_str_)
                                return None
                        else:
                            err_str_ = f"Received empty list while fetching last 3 order_journals for " \
                                       f"order_id {order_journal_obj.order.order_id}, " \
                                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                            logging.error(err_str_)
                            return None
                    elif order_snapshot.order_brief.qty < order_snapshot.filled_qty:
                        order_status = OrderStatusType.OE_OVER_FILLED
                    else:
                        order_status = OrderStatusType.OE_FILLED
                    await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                         last_update_date_time=order_journal_obj.order_event_date_time,
                                                         order_status=order_status).json(by_alias=True, exclude_none=True)))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_REJ:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj, [OrderStatusType.OE_UNACK,
                                                                                           OrderStatusType.OE_ACKED])
                if order_snapshot is not None:
                    order_brief = OrderBrief(**order_snapshot.order_brief.dict())
                    if order_brief.text:
                        order_brief.text.extend(order_journal_obj.order.text)
                    else:
                        order_brief.text = order_journal_obj.order.text
                    cxled_qty = order_snapshot.order_brief.qty - order_snapshot.filled_qty
                    cxled_notional = \
                        order_snapshot.cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                   order_snapshot.order_brief.security.sec_id)
                    avg_cxled_px = \
                        (self.get_local_px_or_notional(cxled_notional, order_snapshot.order_brief.security.sec_id) /
                         cxled_qty) if cxled_qty != 0 else 0
                    order_snapshot = await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(
                            _id=order_snapshot.id,
                            order_brief=order_brief,
                            cxled_qty=cxled_qty,
                            cxled_notional=cxled_notional,
                            avg_cxled_px=avg_cxled_px,
                            last_update_date_time=order_journal_obj.order_event_date_time,
                            order_status=OrderStatusType.OE_DOD).json(by_alias=True, exclude_none=True)))
                    symbol_side_snapshot = \
                        await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                          order_snapshot)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot,
                                                                                        symbol_side_snapshot)
                        await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot,
                                                                         symbol_side_snapshot, updated_strat_brief)
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot)
                    # else not require_create_update_symbol_side_snapshot_from_order_journald:
                    # if symbol_side_snapshot is None then it means some error occurred in
                    # _create_update_symbol_side_snapshot_from_order_journal which would have
                    # got added to alert already
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case other_:
                err_str_ = f"Unsupported Order event - {other_} in order_journal_key: " \
                           f"{get_order_journal_log_key(order_journal_obj)}, order_journal: {order_journal_obj}"
                logging.error(err_str_)

    async def _update_pair_strat_from_order_journal(self, order_journal_obj: OrderJournal,
                                                    order_snapshot: OrderSnapshot,
                                                    symbol_side_snapshot: SymbolSideSnapshot,
                                                    strat_brief: StratBrief):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_partial_update_pair_strat_http
        pair_strat_obj = await get_single_exact_match_ongoing_strat_from_symbol_n_side(
            order_journal_obj.order.security.sec_id,
            order_journal_obj.order.side)
        if pair_strat_obj is not None:
            updated_strat_status_obj = pair_strat_obj.strat_status
            strat_limits = pair_strat_obj.strat_limits
            match order_journal_obj.order.side:
                case Side.BUY:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            updated_strat_status_obj.total_buy_qty += order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_buy_qty += order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_buy_notional += \
                                order_journal_obj.order.qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                              order_snapshot.order_brief.security.sec_id)
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_buy_unfilled_qty = \
                                order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            updated_strat_status_obj.total_open_buy_qty -= total_buy_unfilled_qty
                            updated_strat_status_obj.total_open_buy_notional -= \
                                (total_buy_unfilled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                          order_snapshot.order_brief.security.sec_id))
                            updated_strat_status_obj.total_cxl_buy_qty += order_snapshot.cxled_qty
                            updated_strat_status_obj.total_cxl_buy_notional += \
                                order_snapshot.cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                           order_snapshot.order_brief.security.sec_id)
                            updated_strat_status_obj.avg_cxl_buy_px = \
                                (
                                        self.get_local_px_or_notional(updated_strat_status_obj.total_cxl_buy_notional,
                                                                      order_journal_obj.order.security.sec_id) /
                                        updated_strat_status_obj.total_cxl_buy_qty) \
                                    if updated_strat_status_obj.total_cxl_buy_qty != 0 else 0
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - \
                                updated_strat_status_obj.total_cxl_sell_notional
                        case other_:
                            err_str_ = f"Unsupported Order Event type {other_}, " \
                                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                            logging.error(err_str_)
                            return
                    if updated_strat_status_obj.total_open_buy_qty == 0:
                        updated_strat_status_obj.avg_open_buy_px = 0
                    else:
                        updated_strat_status_obj.avg_open_buy_px = \
                            self.get_local_px_or_notional(updated_strat_status_obj.total_open_buy_notional,
                                                          order_journal_obj.order.security.sec_id) / \
                            updated_strat_status_obj.total_open_buy_qty
                case Side.SELL:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            updated_strat_status_obj.total_sell_qty += order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_sell_qty += order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_sell_notional += \
                                order_journal_obj.order.qty * self.get_usd_px(order_journal_obj.order.px,
                                                                              order_journal_obj.order.security.sec_id)
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_sell_unfilled_qty = \
                                order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            updated_strat_status_obj.total_open_sell_qty -= total_sell_unfilled_qty
                            updated_strat_status_obj.total_open_sell_notional -= \
                                (total_sell_unfilled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                           order_snapshot.order_brief.security.sec_id))
                            updated_strat_status_obj.total_cxl_sell_qty += order_snapshot.cxled_qty
                            updated_strat_status_obj.total_cxl_sell_notional += \
                                order_snapshot.cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                           order_snapshot.order_brief.security.sec_id)
                            updated_strat_status_obj.avg_cxl_sell_px = \
                                self.get_local_px_or_notional(updated_strat_status_obj.total_cxl_sell_notional,
                                                              order_journal_obj.order.security.sec_id) / \
                                updated_strat_status_obj.total_cxl_sell_qty \
                                    if updated_strat_status_obj.total_cxl_sell_qty != 0 else 0
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - \
                                updated_strat_status_obj.total_cxl_sell_notional
                        case other_:
                            err_str_ = f"Unsupported Order Event type {other_} " \
                                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                            logging.error(err_str_)
                            return
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            self.get_local_px_or_notional(updated_strat_status_obj.total_open_sell_notional,
                                                          order_journal_obj.order.security.sec_id) / \
                            updated_strat_status_obj.total_open_sell_qty
                case other_:
                    err_str_ = f"Unsupported Side Type {other_} received in order_journal_key: " \
                               f"{get_order_journal_log_key(order_journal_obj)} while updating strat_status;;; " \
                               f"order_journal {order_journal_obj}"
                    logging.error(err_str_)
                    return
            updated_strat_status_obj.total_order_qty = \
                updated_strat_status_obj.total_buy_qty + updated_strat_status_obj.total_sell_qty
            updated_strat_status_obj.total_open_exposure = updated_strat_status_obj.total_open_buy_notional - \
                                                           updated_strat_status_obj.total_open_sell_notional
            if updated_strat_status_obj.total_fill_buy_notional < updated_strat_status_obj.total_fill_sell_notional:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_buy_notional
            else:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_sell_notional

            updated_residual = self.__get_residual_obj(order_snapshot.order_brief.side, strat_brief)
            if updated_residual is not None:
                updated_strat_status_obj.residual = updated_residual

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_obj.id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            updated_pair_strat_obj.last_active_date_time = order_journal_obj.order_event_date_time
            updated_pair_strat_obj.frequency = pair_strat_obj.frequency + 1
            self._pause_strat_if_limits_breached(pair_strat_obj, updated_pair_strat_obj,
                                                 strat_brief, symbol_side_snapshot)
            await underlying_partial_update_pair_strat_http(
                json.loads(updated_pair_strat_obj.json(by_alias=True, exclude_none=True)))
        else:
            logging.error(f"error: received pair_strat as None, order_journal_key: "
                          f"{get_order_journal_log_key(order_journal_obj)}")
            return

    def _pause_strat_if_limits_breached(self, existing_pair_strat: PairStrat,
                                        updated_pair_strat_: PairStrat, strat_brief_: StratBrief,
                                        symbol_side_snapshot_: SymbolSideSnapshot):
        if (residual_notional := updated_pair_strat_.strat_status.residual.residual_notional) is not None:
            if residual_notional > (max_residual := existing_pair_strat.strat_limits.residual_restriction.max_residual):
                alert_brief: str = f"residual notional: {residual_notional} > max residual: {max_residual}"
                alert_details: str = f"strat details: {updated_pair_strat_}"
                alert: Alert = create_alert(alert_brief, alert_details, None, Severity.Severity_INFO)
                updated_pair_strat_.strat_status.strat_state = StratState.StratState_PAUSED
                updated_pair_strat_.strat_status.strat_alerts = [alert]
            # else not required: if residual is in control then nothing to do

        if symbol_side_snapshot_.order_count > existing_pair_strat.strat_limits.cancel_rate.waived_min_orders:
            if symbol_side_snapshot_.side == Side.BUY:
                if strat_brief_.pair_buy_side_trading_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_buy_side_trading_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, currently is {consumable_cxl_qty} " \
                                        f"for symbol {strat_brief_.pair_buy_side_trading_brief.security.sec_id} and " \
                                        f"side {Side.BUY}"
                        alert_brief: str = err_str_
                        alert_details: str = f"strat details: {updated_pair_strat_}, " \
                                             f"symbol_side_snapshot: {symbol_side_snapshot_}"
                        alert: Alert = create_alert(alert_brief, alert_details, None, Severity.Severity_INFO)
                        updated_pair_strat_.strat_status.strat_state = StratState.StratState_PAUSED
                        updated_pair_strat_.strat_status.strat_alerts = [alert]
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single buy order then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if buy side all_bkr_cxlled_qty is 0
            else:
                if strat_brief_.pair_sell_side_trading_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_sell_side_trading_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, currently is {consumable_cxl_qty} " \
                                        f"for symbol {strat_brief_.pair_sell_side_trading_brief.security.sec_id} and " \
                                        f"side {Side.SELL}"
                        alert_brief: str = err_str_
                        alert_details: str = f"strat details: {updated_pair_strat_}, " \
                                             f"symbol_side_snapshot: {symbol_side_snapshot_}"
                        alert: Alert = create_alert(alert_brief, alert_details, None, Severity.Severity_INFO)
                        updated_pair_strat_.strat_status.strat_state = StratState.StratState_PAUSED
                        updated_pair_strat_.strat_status.strat_alerts = [alert]
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single sell order then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if sell side all_bkr_cxlled_qty is 0
            # else not required: if order count is less than waived_min_orders

    def __get_residual_obj(self, side: Side, strat_brief: StratBrief) -> Residual | None:
        if side == Side.BUY:
            residual_qty = strat_brief.pair_buy_side_trading_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_sell_side_trading_brief.residual_qty
            top_of_book_obj = \
                self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_trading_brief.security.sec_id)
            other_leg_top_of_book = \
                self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_trading_brief.security.sec_id)
        else:
            residual_qty = strat_brief.pair_sell_side_trading_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_buy_side_trading_brief.residual_qty
            top_of_book_obj = \
                self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_trading_brief.security.sec_id)
            other_leg_top_of_book = \
                self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_trading_brief.security.sec_id)

        if top_of_book_obj is None or other_leg_top_of_book is None:
            logging.error(f"Received both leg's TOBs as {top_of_book_obj} and {other_leg_top_of_book}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            return None

        residual_notional = abs((residual_qty * self.get_usd_px(top_of_book_obj.last_trade.px,
                                                                top_of_book_obj.symbol)) -
                                (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_trade.px,
                                                                          other_leg_top_of_book.symbol)))
        if side == Side.BUY:
            if (residual_qty * top_of_book_obj.last_trade.px) > \
                    (other_leg_residual_qty * other_leg_top_of_book.last_trade.px):
                residual_security = strat_brief.pair_buy_side_trading_brief.security
            else:
                residual_security = strat_brief.pair_sell_side_trading_brief.security
        else:
            if (residual_qty * top_of_book_obj.last_trade.px) > \
                    (other_leg_residual_qty * other_leg_top_of_book.last_trade.px):
                residual_security = strat_brief.pair_sell_side_trading_brief.security
            else:
                residual_security = strat_brief.pair_buy_side_trading_brief.security

        if residual_notional > 0:
            updated_residual = Residual(security=residual_security, residual_notional=residual_notional)
            return updated_residual
        else:
            updated_residual = Residual(security=residual_security, residual_notional=0)
            return updated_residual

    async def _update_pair_strat_from_fill_journal(self, order_snapshot_obj: OrderSnapshot,
                                                   symbol_side_snapshot: SymbolSideSnapshot,
                                                   strat_brief_obj: StratBrief):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_partial_update_pair_strat_http
        pair_strat_obj = \
            await get_single_exact_match_ongoing_strat_from_symbol_n_side(
                order_snapshot_obj.order_brief.security.sec_id,
                order_snapshot_obj.order_brief.side)
        if pair_strat_obj is not None:
            updated_strat_status_obj = pair_strat_obj.strat_status
            strat_limits = pair_strat_obj.strat_limits
            match order_snapshot_obj.order_brief.side:
                case Side.BUY:
                    updated_strat_status_obj.total_open_buy_qty -= order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_open_buy_notional -= \
                        order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                                  order_snapshot_obj.order_brief.security.sec_id)
                    if updated_strat_status_obj.total_open_buy_qty == 0:
                        updated_strat_status_obj.avg_open_buy_px = 0
                    else:
                        updated_strat_status_obj.avg_open_buy_px = \
                            self.get_local_px_or_notional(updated_strat_status_obj.total_open_buy_notional,
                                                          order_snapshot_obj.order_brief.security.sec_id) / \
                            updated_strat_status_obj.total_open_buy_qty
                    updated_strat_status_obj.total_fill_buy_qty += order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_fill_buy_notional += \
                        order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                            order_snapshot_obj.last_update_fill_px,
                            order_snapshot_obj.order_brief.security.sec_id)
                    updated_strat_status_obj.avg_fill_buy_px = \
                        self.get_local_px_or_notional(updated_strat_status_obj.total_fill_buy_notional,
                                                      order_snapshot_obj.order_brief.security.sec_id) / \
                        updated_strat_status_obj.total_fill_buy_qty
                case Side.SELL:
                    updated_strat_status_obj.total_open_sell_qty -= order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_open_sell_notional -= \
                        (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                                   order_snapshot_obj.order_brief.security.sec_id))
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            self.get_local_px_or_notional(updated_strat_status_obj.total_open_sell_notional,
                                                          order_snapshot_obj.order_brief.security.sec_id) / \
                            updated_strat_status_obj.total_open_sell_qty
                    updated_strat_status_obj.total_fill_sell_qty += order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_fill_sell_notional += \
                        order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                            order_snapshot_obj.last_update_fill_px,
                            order_snapshot_obj.order_brief.security.sec_id)
                    updated_strat_status_obj.avg_fill_sell_px = \
                        self.get_local_px_or_notional(updated_strat_status_obj.total_fill_sell_notional,
                                                      order_snapshot_obj.order_brief.security.sec_id) / \
                        updated_strat_status_obj.total_fill_sell_qty
                case other_:
                    err_str_ = f"Unsupported Side Type {other_} received for order_snapshot_key: " \
                               f"{get_order_snapshot_log_key(order_snapshot_obj)} while updating strat_status;;; " \
                               f"order_snapshot: {order_snapshot_obj}"
                    logging.error(err_str_)
                    return
            updated_strat_status_obj.total_open_exposure = updated_strat_status_obj.total_open_buy_notional - \
                                                           updated_strat_status_obj.total_open_sell_notional
            updated_strat_status_obj.total_fill_exposure = updated_strat_status_obj.total_fill_buy_notional - \
                                                           updated_strat_status_obj.total_fill_sell_notional
            if updated_strat_status_obj.total_fill_buy_notional < updated_strat_status_obj.total_fill_sell_notional:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_buy_notional
            else:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_sell_notional

            updated_residual = self.__get_residual_obj(order_snapshot_obj.order_brief.side, strat_brief_obj)
            if updated_residual is not None:
                updated_strat_status_obj.residual = updated_residual

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_obj.id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            updated_pair_strat_obj.last_active_date_time = order_snapshot_obj.last_update_date_time
            updated_pair_strat_obj.frequency = pair_strat_obj.frequency + 1
            self._pause_strat_if_limits_breached(pair_strat_obj, updated_pair_strat_obj,
                                                 strat_brief_obj, symbol_side_snapshot)
            await underlying_partial_update_pair_strat_http(
                json.loads(updated_pair_strat_obj.json(by_alias=True, exclude_none=True)))
        else:
            logging.error(f"error: received pair_strat as None, order_snapshot_key: "
                          f"{get_order_snapshot_log_key(order_snapshot_obj)}")
            return

    async def _update_portfolio_status_from_order_journal(self, order_journal_obj: OrderJournal,
                                                          order_snapshot_obj: OrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_portfolio_status_by_id_http, underlying_partial_update_portfolio_status_http

        portfolio_status_obj = await underlying_read_portfolio_status_by_id_http(1)
        match order_journal_obj.order.side:
            case Side.BUY:
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        if portfolio_status_obj.overall_buy_notional is None:
                            portfolio_status_obj.overall_buy_notional = 0
                        portfolio_status_obj.overall_buy_notional += \
                            self.get_usd_px(order_journal_obj.order.px, order_journal_obj.order.security.sec_id) * \
                            order_journal_obj.order.qty
                    case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                        total_buy_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        portfolio_status_obj.overall_buy_notional -= \
                            (self.get_usd_px(order_snapshot_obj.order_brief.px,
                                             order_snapshot_obj.order_brief.security.sec_id) * total_buy_unfilled_qty)
            case Side.SELL:
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        if portfolio_status_obj.overall_sell_notional is None:
                            portfolio_status_obj.overall_sell_notional = 0
                        portfolio_status_obj.overall_sell_notional += \
                            self.get_usd_px(order_journal_obj.order.px, order_journal_obj.order.security.sec_id) * \
                            order_journal_obj.order.qty
                    case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                        total_sell_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        portfolio_status_obj.overall_sell_notional -= \
                            (self.get_usd_px(order_snapshot_obj.order_brief.px,
                                             order_snapshot_obj.order_brief.security.sec_id) * total_sell_unfilled_qty)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order_journal of key: " \
                           f"{get_order_journal_log_key(order_journal_obj)} while updating strat_status;;; " \
                           f"order_journal_obj: {order_journal_obj} "
                logging.error(err_str_)
                return
        updated_portfolio_status = PortfolioStatusOptional(
            _id=portfolio_status_obj.id,
            overall_buy_notional=portfolio_status_obj.overall_buy_notional,
            overall_sell_notional=portfolio_status_obj.overall_sell_notional
        )
        updated_portfolio_status = await underlying_partial_update_portfolio_status_http(
            json.loads(updated_portfolio_status.json(by_alias=True, exclude_none=True)))

    async def create_fills_journal_pre(self, fills_journal_obj: FillsJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_fills_journal_pre not ready - service is not initialized yet, " \
                       f"fills_journal_key: {get_fills_journal_log_key(fills_journal_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # Updating notional field in fills journal
        fills_journal_obj.fill_notional = \
            self.get_usd_px(fills_journal_obj.fill_px, fills_journal_obj.fill_symbol) * fills_journal_obj.fill_qty

    async def create_fills_journal_post(self, fills_journal_obj: FillsJournal):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            residual_compute_shared_lock
        async with residual_compute_shared_lock:
            await self._apply_fill_update_in_order_snapshot(fills_journal_obj)

    async def _update_portfolio_status_from_fill_journal(self, order_snapshot_obj: OrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_portfolio_status_by_id_http, underlying_partial_update_portfolio_status_http

        portfolio_status_obj = await underlying_read_portfolio_status_by_id_http(1)
        match order_snapshot_obj.order_brief.side:
            case Side.BUY:
                if portfolio_status_obj.overall_buy_notional is None:
                    portfolio_status_obj.overall_buy_notional = 0
                portfolio_status_obj.overall_buy_notional += \
                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                                                               order_snapshot_obj.order_brief.security.sec_id)) - \
                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                               order_snapshot_obj.order_brief.security.sec_id))
                if portfolio_status_obj.overall_buy_fill_notional is None:
                    portfolio_status_obj.overall_buy_fill_notional = 0
                portfolio_status_obj.overall_buy_fill_notional += \
                    self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                    order_snapshot_obj.order_brief.security.sec_id) * \
                    order_snapshot_obj.last_update_fill_qty
            case Side.SELL:
                if portfolio_status_obj.overall_sell_notional is None:
                    portfolio_status_obj.overall_sell_notional = 0
                portfolio_status_obj.overall_sell_notional += \
                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                                                               order_snapshot_obj.order_brief.security.sec_id)) - \
                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                               order_snapshot_obj.order_brief.security.sec_id))
                if portfolio_status_obj.overall_sell_fill_notional is None:
                    portfolio_status_obj.overall_sell_fill_notional = 0
                portfolio_status_obj.overall_sell_fill_notional += \
                    self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                    order_snapshot_obj.order_brief.security.sec_id) * \
                    order_snapshot_obj.last_update_fill_qty
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order snapshot of key " \
                           f"{get_order_snapshot_log_key(order_snapshot_obj)} while updating strat_status;;; " \
                           f"order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)
                return
        updated_portfolio_status = PortfolioStatusOptional(
            _id=portfolio_status_obj.id,
            overall_buy_notional=portfolio_status_obj.overall_buy_notional,
            overall_buy_fill_notional=portfolio_status_obj.overall_buy_fill_notional,
            overall_sell_notional=portfolio_status_obj.overall_sell_notional,
            overall_sell_fill_notional=portfolio_status_obj.overall_sell_fill_notional
        )
        updated_portfolio_status = await underlying_partial_update_portfolio_status_http(
            json.loads(updated_portfolio_status.json(by_alias=True, exclude_none=True)))

    async def _apply_fill_update_in_order_snapshot(self, fills_journal_obj: FillsJournal) -> None:
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_snapshot_http, underlying_partial_update_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(
                fills_journal_obj.order_id), self.get_generic_read_route())
        if len(order_snapshot_objs) == 1:
            order_snapshot_obj = order_snapshot_objs[0]
            if order_snapshot_obj.order_status == OrderStatusType.OE_ACKED:
                if (total_filled_qty := order_snapshot_obj.filled_qty) is not None:
                    updated_total_filled_qty = total_filled_qty + fills_journal_obj.fill_qty
                else:
                    updated_total_filled_qty = fills_journal_obj.fill_qty
                received_fill_notional = fills_journal_obj.fill_notional
                last_update_fill_qty = fills_journal_obj.fill_qty
                last_update_fill_px = fills_journal_obj.fill_px

                if order_snapshot_obj.order_brief.qty == updated_total_filled_qty:
                    order_status = OrderStatusType.OE_FILLED
                elif order_snapshot_obj.order_brief.qty < updated_total_filled_qty:
                    vacant_fill_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                    non_required_received_fill_qty = fills_journal_obj.fill_qty - vacant_fill_qty
                    updated_total_filled_qty = order_snapshot_obj.order_brief.qty
                    order_status = OrderStatusType.OE_FILLED
                    received_fill_notional = self.get_usd_px(fills_journal_obj.fill_px,
                                                             fills_journal_obj.fill_symbol) * vacant_fill_qty
                    last_update_fill_qty = vacant_fill_qty

                    logging.warning(f"Unexpected: Received fill that makes order_snapshot OVER_FILLED, "
                                    f"vacant_fill_qty: {vacant_fill_qty}, received fill_qty "
                                    f"{fills_journal_obj.fill_qty}, taking only vacant_fill_qty for order_fill and "
                                    f"ignoring remaining {non_required_received_fill_qty} from fills_journal_key "
                                    f"{get_fills_journal_log_key(fills_journal_obj)};;; fills_journal {fills_journal_obj}")
                else:
                    order_status = order_snapshot_obj.order_status

                if (last_filled_notional := order_snapshot_obj.fill_notional) is not None:
                    updated_fill_notional = last_filled_notional + received_fill_notional
                else:
                    updated_fill_notional = received_fill_notional
                updated_avg_fill_px = \
                    self.get_local_px_or_notional(updated_fill_notional,
                                                  fills_journal_obj.fill_symbol) / updated_total_filled_qty

                order_snapshot_obj = \
                    await underlying_partial_update_order_snapshot_http(json.loads(OrderSnapshotOptional(
                        _id=order_snapshot_obj.id, filled_qty=updated_total_filled_qty, avg_fill_px=updated_avg_fill_px,
                        fill_notional=updated_fill_notional, last_update_fill_qty=last_update_fill_qty,
                        last_update_fill_px=last_update_fill_px,
                        last_update_date_time=fills_journal_obj.fill_date_time, order_status=order_status).json(
                        by_alias=True, exclude_none=True)))
                symbol_side_snapshot = \
                    await self._update_symbol_side_snapshot_from_fill_applied_order_snapshot(order_snapshot_obj)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot_obj,
                                                                                    symbol_side_snapshot)
                    await self._update_pair_strat_from_fill_journal(order_snapshot_obj, symbol_side_snapshot,
                                                                    updated_strat_brief)
                    await self._update_portfolio_status_from_fill_journal(order_snapshot_obj)
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already
            elif order_snapshot_obj.order_status == OrderStatusType.OE_FILLED:
                err_str_ = f"Unsupported - Fill received for completely filled order_snapshot, " \
                           f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot_obj)}, ignoring this " \
                           f"fill journal;;; fill_journal: {fills_journal_obj}, order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)
            else:
                err_str_ = f"Unsupported - Fill received for order_snapshot having status " \
                           f"{order_snapshot_obj.order_status}, order_snapshot_key: " \
                           f"{get_order_snapshot_log_key(order_snapshot_obj)};;; " \
                           f"fill_journal: {fills_journal_obj}, order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)

        elif len(order_snapshot_objs) == 0:
            err_str_ = f"Could not find any order snapshot with order-id {fills_journal_obj.order_id}, " \
                       f"fill_journal_key: {get_fills_journal_log_key(fills_journal_obj)};;; " \
                       f"order_snapshot_list: {order_snapshot_objs}"
            logging.error(err_str_)
        else:
            err_str_ = f"Match should return list of only one order_snapshot obj, " \
                       f"returned {len(order_snapshot_objs)}, fills_journal_key: " \
                       f"{get_fills_journal_log_key(fills_journal_obj)};;; order_snapshot_list: {order_snapshot_objs}"
            logging.error(err_str_)

    # Example: Soft API Query Interfaces

    async def get_symbol_side_snapshot_from_symbol_side_query_pre(self, symbol_side_snapshot_class_type: Type[
        SymbolSideSnapshot], security_id: str, side: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        return await underlying_read_symbol_side_snapshot_http(
            get_symbol_side_snapshot_from_symbol_side(security_id, side), self.get_generic_read_route())

    # Code-generated
    async def get_pair_strat_sec_filter_json_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter
        return await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(security_id),
                                                     self.get_generic_read_route())

    def _set_new_strat_limit(self, pair_strat_obj: PairStrat) -> None:
        pair_strat_obj.strat_limits = get_new_strat_limits()

    def _set_derived_side(self, pair_strat_obj: PairStrat):
        raise_error = False
        if pair_strat_obj.pair_strat_params.strat_leg2.side is None or \
                pair_strat_obj.pair_strat_params.strat_leg2.side == Side.SIDE_UNSPECIFIED:
            if pair_strat_obj.pair_strat_params.strat_leg1.side == Side.BUY:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.SELL
            elif pair_strat_obj.pair_strat_params.strat_leg1.side == Side.SELL:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.BUY
            else:
                raise_error = True
        elif pair_strat_obj.pair_strat_params.strat_leg1.side is None:
            raise_error = True
        # else not required, all good
        if raise_error:
            # handles pair_strat_obj.pair_strat_params.strat_leg1.side == None and all other unsupported values
            raise Exception(f"error: _set_derived_side called with unsupported side combo on legs, leg1: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg1.side} leg2: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg2.side} in pair strat: {pair_strat_obj}")

    def _set_derived_exchange(self, pair_strat_obj: PairStrat):
        """
        update the exchange of derived (if we have one)
        """
        return

    def _apply_checks_n_alert(self, pair_strat_obj: PairStrat, is_create: bool = False) -> List[Alert]:
        """
        implement any strat management checks here (create / update strats)
        """
        return []

    # synchronously called on webservice call
    def _add_pair_strat_status(self, pair_strat_obj: PairStrat):
        if pair_strat_obj.strat_status is None:  # add case
            strat_state: StratState = StratState.StratState_READY
            strat_alerts = self._apply_checks_n_alert(pair_strat_obj, is_create=True)
            if len(strat_alerts) != 0:  # some security is restricted
                strat_state = StratState.StratState_ERROR
            pair_strat_obj.strat_status = StratStatus(strat_state=strat_state, strat_alerts=strat_alerts,
                                                      fills_brief=[], open_orders_brief=[], total_buy_qty=0,
                                                      total_sell_qty=0, total_order_qty=0, total_open_buy_qty=0,
                                                      total_open_sell_qty=0, avg_open_buy_px=0.0, avg_open_sell_px=0.0,
                                                      total_open_buy_notional=0.0, total_open_sell_notional=0.0,
                                                      total_open_exposure=0.0, total_fill_buy_qty=0,
                                                      total_fill_sell_qty=0, avg_fill_buy_px=0.0, avg_fill_sell_px=0.0,
                                                      total_fill_buy_notional=0.0, total_fill_sell_notional=0.0,
                                                      total_fill_exposure=0.0, total_cxl_buy_qty=0.0,
                                                      total_cxl_sell_qty=0.0, avg_cxl_buy_px=0.0, avg_cxl_sell_px=0.0,
                                                      total_cxl_buy_notional=0.0, total_cxl_sell_notional=0.0,
                                                      total_cxl_exposure=0.0, average_premium=0.0,
                                                      balance_notional=pair_strat_obj.strat_limits.max_cb_notional)
        else:
            pair_strat_obj.strat_status.strat_state = StratState.StratState_ERROR
            err_str_ = f"_add_pair_strat_status called with unexpected pre-set strat_status for: " \
                       f"{get_pair_strat_log_key(pair_strat_obj)}"
            logging.error(f"{err_str_};;;pair_strat: {pair_strat_obj}")

    @except_n_log_alert(severity=Severity.Severity_ERROR)
    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)};;; pair_strat: {pair_strat_obj}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # expectation: no strat limit or status is set while creating a strat, this call creates these
        if pair_strat_obj.strat_status is not None:
            err_str_ = f"error: create_pair_strat_pre called with pre-set strat_status, pair_strat_key: " \
                       f"{get_pair_strat_log_key(pair_strat_obj)};;; pair_strat_obj: {pair_strat_obj}"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)
        if pair_strat_obj.strat_limits is not None:
            err_str_ = f"error: create_pair_strat_pre called with pre-set strat_limits, pair_strat_key: " \
                       f"{get_pair_strat_log_key(pair_strat_obj)};;; pair_strat_obj{pair_strat_obj}"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)
        # expectation: strat_leg2 is not None
        if pair_strat_obj.pair_strat_params.strat_leg2 is None:
            err_str_ = f"error: create_pair_strat_pre called with unset strat_leg2, pair_strat_key: " \
                       f"{get_pair_strat_log_key(pair_strat_obj)};;; pair_strat_obj: {pair_strat_obj}"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)
        self._set_new_strat_limit(pair_strat_obj)
        self._add_pair_strat_status(pair_strat_obj)
        self._set_derived_side(pair_strat_obj)
        self._set_derived_exchange(pair_strat_obj)
        # get security name from : pair_strat_params.strat_legs and then redact pattern
        # security.sec_id (a pattern in positions) where there is a value match
        dismiss_filter_agg_pipeline = {'redact': [("security.sec_id",
                                                   pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                                                   pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id)]}
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_portfolio_limits_http

        filtered_portfolio_limits: List[PortfolioLimits] = await underlying_read_portfolio_limits_http(
            dismiss_filter_agg_pipeline, self.get_generic_read_route())
        if len(filtered_portfolio_limits) == 1:
            if filtered_portfolio_limits[0].eligible_brokers is not None:
                pair_strat_obj.strat_limits.eligible_brokers = [eligible_broker for eligible_broker in
                                                                filtered_portfolio_limits[0].eligible_brokers if
                                                                eligible_broker.sec_positions]
        elif len(filtered_portfolio_limits) > 1:
            err_str_ = f"filtered_portfolio_limits expected: 1, pair_strat_key: " \
                       f"{get_pair_strat_log_key(pair_strat_obj)}, found: " \
                       f"{str(len(filtered_portfolio_limits))}, for filter: " \
                       f"{dismiss_filter_agg_pipeline}, filtered_portfolio_limits: " \
                       f"{filtered_portfolio_limits}; use SWAGGER UI to check / fix and re-try "
            logging.error(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)
        else:
            logging.warning(f"No filtered_portfolio_limits found for pair_strat of key: "
                            f"{get_pair_strat_log_key(pair_strat_obj)};;; pair-strat: {pair_strat_obj}")
        pair_strat_obj.frequency = 1
        pair_strat_obj.pair_strat_params_update_seq_num = 0
        pair_strat_obj.strat_limits_update_seq_num = 0
        pair_strat_obj.strat_status_update_seq_num = 0
        pair_strat_obj.last_active_date_time = DateTime.utcnow()

    async def _create_strat_brief_for_ready_to_active_pair_strat(self, pair_strat_obj: PairStrat):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol
        symbol = pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id
        side = pair_strat_obj.pair_strat_params.strat_leg1.side
        # since strat_brief has both symbols as pair_strat has, so any symbol will give same strat_brief
        strat_brief_objs_list = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol),
                                                                       self.get_generic_read_route())

        if len(strat_brief_objs_list) > 1:
            err_str_ = f"strat_brief must be only one per symbol received {strat_brief_objs_list} symbol_side_key: " \
                       f"{get_symbol_side_key([(symbol, side)])}"
            logging.error(err_str_)
            return
        elif len(strat_brief_objs_list) == 1:
            err_str_ = f"strat_brief must not exist for this symbol while strat is converting from ready to active, " \
                       f"pair_strat_key: {get_symbol_side_key([(symbol, side)])};;; " \
                       f"strat_brief_list: {strat_brief_objs_list}"
            logging.error(err_str_)
            return
        else:
            # If no strat_brief exists for this symbol
            consumable_open_orders = pair_strat_obj.strat_limits.max_open_orders_per_side
            consumable_notional = pair_strat_obj.strat_limits.max_cb_notional
            consumable_open_notional = pair_strat_obj.strat_limits.max_open_cb_notional
            security_float = self.static_data.get_security_float_from_ticker(symbol)
            if security_float is not None:
                consumable_concentration = \
                    (security_float / 100) * pair_strat_obj.strat_limits.max_concentration
            else:
                consumable_concentration = 0
            participation_period_order_qty_sum = 0
            consumable_cxl_qty = 0
            from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                underlying_get_executor_check_snapshot_query_http
            applicable_period_second = \
                pair_strat_obj.strat_limits.market_trade_volume_participation.applicable_period_seconds
            executor_check_snapshot_list = \
                await underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                        applicable_period_second)
            if len(executor_check_snapshot_list) == 1:
                indicative_consumable_participation_qty = \
                    get_consumable_participation_qty(executor_check_snapshot_list,
                                                     pair_strat_obj.strat_limits.market_trade_volume_participation.max_participation_rate)
            else:
                logging.error("Received unexpected length of executor_check_snapshot_list from query "
                              f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                              f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                              f"get_executor_check_snapshot_query pre implementation")
                indicative_consumable_participation_qty = 0
            residual_qty = 0
            indicative_consumable_residual = pair_strat_obj.strat_limits.residual_restriction.max_residual
            all_bkr_cxlled_qty = 0
            open_notional = 0
            open_qty = 0

            sec1_pair_side_trading_brief_obj = \
                PairSideTradingBrief(security=pair_strat_obj.pair_strat_params.strat_leg1.sec,
                                     side=pair_strat_obj.pair_strat_params.strat_leg1.side,
                                     last_update_date_time=DateTime.utcnow(),
                                     consumable_open_orders=consumable_open_orders,
                                     consumable_notional=consumable_notional,
                                     consumable_open_notional=consumable_open_notional,
                                     consumable_concentration=consumable_concentration,
                                     participation_period_order_qty_sum=participation_period_order_qty_sum,
                                     consumable_cxl_qty=consumable_cxl_qty,
                                     indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                     residual_qty=residual_qty,
                                     indicative_consumable_residual=indicative_consumable_residual,
                                     all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                     open_notional=open_notional, open_qty=open_qty)
            sec2_pair_side_trading_brief_obj = \
                PairSideTradingBrief(security=pair_strat_obj.pair_strat_params.strat_leg2.sec,
                                     side=pair_strat_obj.pair_strat_params.strat_leg2.side,
                                     last_update_date_time=DateTime.utcnow(),
                                     consumable_open_orders=consumable_open_orders,
                                     consumable_notional=consumable_notional,
                                     consumable_open_notional=consumable_open_notional,
                                     consumable_concentration=consumable_concentration,
                                     participation_period_order_qty_sum=participation_period_order_qty_sum,
                                     consumable_cxl_qty=consumable_cxl_qty,
                                     indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                     residual_qty=residual_qty,
                                     indicative_consumable_residual=indicative_consumable_residual,
                                     all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                     open_notional=open_notional, open_qty=open_qty)

            from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                underlying_create_strat_brief_http
            buy_side_trading_brief = sec1_pair_side_trading_brief_obj \
                if sec1_pair_side_trading_brief_obj.side == Side.BUY else sec2_pair_side_trading_brief_obj
            sell_side_trading_brief = sec1_pair_side_trading_brief_obj \
                if sec1_pair_side_trading_brief_obj.side == Side.SELL else sec2_pair_side_trading_brief_obj
            strat_brief_obj: StratBrief = StratBrief(_id=StratBrief.next_id(),
                                                     pair_buy_side_trading_brief=buy_side_trading_brief,
                                                     pair_sell_side_trading_brief=sell_side_trading_brief,
                                                     consumable_nett_filled_notional=0.0)
            created_underlying_strat_brief = await underlying_create_strat_brief_http(strat_brief_obj)
            logging.debug(f"Created strat brief in pre call of pair_strat of "
                          f"key: {get_pair_strat_log_key(pair_strat_obj)};;; pair_strat: {pair_strat_obj}, "
                          f"created strat_brief: {created_underlying_strat_brief}")

    async def _create_symbol_snapshot_for_ready_to_active_pair_strat(self, pair_strat_obj: PairStrat):
        pair_symbol_side_list = [
            (pair_strat_obj.pair_strat_params.strat_leg1.sec, pair_strat_obj.pair_strat_params.strat_leg1.side),
            (pair_strat_obj.pair_strat_params.strat_leg2.sec, pair_strat_obj.pair_strat_params.strat_leg2.side)
        ]

        for security, side in pair_symbol_side_list:
            symbol_side_snapshots = await self._get_symbol_side_snapshot_from_symbol_side(security.sec_id, side)

            if symbol_side_snapshots is not None:
                if len(symbol_side_snapshots) == 1:
                    err_str_ = f"SymbolSideSnapshot must not be present for this symbol and side when strat is " \
                               f"converted converted from ready to active, symbol_side_key: " \
                               f"{get_symbol_side_key([(security.sec_id, side)])}, " \
                               f"symbol_side_snapshot_list {symbol_side_snapshots}"
                    logging.error(err_str_)
                    return
                elif len(symbol_side_snapshots) > 1:
                    err_str_ = f"SymbolSideSnapshot must be one per symbol and side, symbol_side_key: " \
                               f"{get_symbol_side_key([(security.sec_id, side)])}, symbol_side_snapshot_list: " \
                               f"{symbol_side_snapshots}"
                    logging.error(err_str_)
                    return
                # else not required: good if no symbol_side_snapshot exists already (we create new)

                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_create_symbol_side_snapshot_http
                symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(),
                                                              security=security,
                                                              side=side, avg_px=0, total_qty=0,
                                                              total_filled_qty=0, avg_fill_px=0.0,
                                                              total_fill_notional=0.0, last_update_fill_qty=0,
                                                              last_update_fill_px=0, total_cxled_qty=0,
                                                              avg_cxled_px=0,
                                                              total_cxled_notional=0,
                                                              last_update_date_time=DateTime.utcnow(),
                                                              order_count=0)
                created_symbol_side_snapshot: SymbolSideSnapshot = \
                    await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
                logging.debug(f"Created SymbolSideSnapshot with key: "
                              f"{get_symbol_side_snapshot_log_key(created_symbol_side_snapshot)};;;"
                              f"new SymbolSideSnapshot: {created_symbol_side_snapshot}")
            else:
                logging.error("unexpected: None symbol_side_snapshots received - this is likely a bug, "
                              f"pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)}")

    async def _update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat,
                                     updated_pair_strat_obj: PairStrat) -> bool | None:
        """
        Return true if object further updated false otherwise
        """
        is_updated = False
        if updated_pair_strat_obj.strat_status is None:
            err_str_ = f"_update_pair_strat_pre called with NO set strat_status, " \
                       f"pair_strat_key: {get_pair_strat_log_key(updated_pair_strat_obj)};;;" \
                       f"pair_strat: {updated_pair_strat_obj}"
            logging.error(err_str_)
            return
        if updated_pair_strat_obj.strat_status.strat_state == StratState.StratState_ACTIVE:
            strat_alerts = self._apply_checks_n_alert(updated_pair_strat_obj)
            if len(strat_alerts) != 0:
                # some check is violated, move strat to error
                updated_pair_strat_obj.strat_status.strat_state = StratState.StratState_ERROR
                if updated_pair_strat_obj.strat_status.strat_alerts is None:
                    updated_pair_strat_obj.strat_status.strat_alerts = strat_alerts
                else:
                    updated_pair_strat_obj.strat_status.strat_alerts.extend(strat_alerts)
                is_updated = True
            # else not required - no alerts - all checks passed
            if stored_pair_strat_obj.strat_status.strat_state != StratState.StratState_ACTIVE:
                dict_dirty: bool = False
                async with self.active_ticker_pair_strat_id_dict_lock:
                    if updated_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id not \
                            in self.pair_strat_id_n_today_activated_tickers_dict:
                        self.pair_strat_id_n_today_activated_tickers_dict[
                            updated_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id] = updated_pair_strat_obj.id
                        dict_dirty = True
                    if updated_pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id not \
                            in self.pair_strat_id_n_today_activated_tickers_dict:
                        self.pair_strat_id_n_today_activated_tickers_dict[
                            updated_pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id] = updated_pair_strat_obj.id
                        dict_dirty = True
                if dict_dirty:
                    store_json_or_dict_to_file(self.pair_strat_id_n_today_activated_tickers_dict_file_name,
                                               self.pair_strat_id_n_today_activated_tickers_dict, CURRENT_PROJECT_DATA_DIR)

            # else not required: pair_strat_id_n_today_activated_tickers_dict is updated only if we activate a new strat
        return is_updated

    async def update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(updated_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_pair_strat_obj.frequency is None:
            updated_pair_strat_obj.frequency = 0
        updated_pair_strat_obj.frequency += 1

        if updated_pair_strat_obj.strat_status_update_seq_num is None:
            updated_pair_strat_obj.strat_status_update_seq_num = 0
        updated_pair_strat_obj.strat_status_update_seq_num += 1

        if updated_pair_strat_obj.pair_strat_params_update_seq_num is None:
            updated_pair_strat_obj.pair_strat_params_update_seq_num = 0
        updated_pair_strat_obj.pair_strat_params_update_seq_num += 1

        if updated_pair_strat_obj.strat_limits_update_seq_num is None:
            updated_pair_strat_obj.strat_limits_update_seq_num = 0
        updated_pair_strat_obj.strat_limits_update_seq_num += 1

        await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()
        logging.debug(f"further updated by _update_pair_strat_pre, pair_strat_key: "
                      f"{get_pair_strat_log_key(updated_pair_strat_obj)};;; "
                      f"pair_strat: {updated_pair_strat_obj}")
        return updated_pair_strat_obj

    async def partial_update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj_dict: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "partial_update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(stored_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        updated_pair_strat_obj_dict["frequency"] = stored_pair_strat_obj.frequency + 1

        if updated_pair_strat_obj_dict.get("strat_status") is not None:
            if stored_pair_strat_obj.strat_status_update_seq_num is None:
                updated_pair_strat_obj_dict["strat_status_update_seq_num"] = 0
            updated_pair_strat_obj_dict[
                "strat_status_update_seq_num"] = stored_pair_strat_obj.strat_status_update_seq_num + 1

        if updated_pair_strat_obj_dict.get("pair_strat_params") is not None:
            if stored_pair_strat_obj.pair_strat_params_update_seq_num is None:
                updated_pair_strat_obj_dict["pair_strat_params_update_seq_num"] = 0
            updated_pair_strat_obj_dict["pair_strat_params_update_seq_num"] = \
                stored_pair_strat_obj.pair_strat_params_update_seq_num + 1

        if updated_pair_strat_obj_dict.get("strat_limits") is not None:
            if stored_pair_strat_obj.strat_limits_update_seq_num is None:
                updated_pair_strat_obj_dict["strat_limits_update_seq_num"] = 0
            updated_pair_strat_obj_dict[
                "strat_limits_update_seq_num"] = stored_pair_strat_obj.strat_limits_update_seq_num + 1

        # After use of below compare_n_patch_dict we are also having one more compare_n_patch_dict call in
        # generic_patch_http causing below issues (or may be more which not got debugged yet):
        # 1. When there is intended delete required for alerts, alerts get removed in below compare_n_patch_dict
        #    function's output but when again compared in compare_n_patch_dict call in generic_patch_http, since
        #    update_dict for that call will not have intended delete alerts but stored_dict will still have all
        #    alerts, delete intended alerts get ignored
        # 2. If we need to add impacted_order in any alert then since we are calling compare_n_patch_dict 2 times,
        #    impacted_order objects get duplicated
        # To handle these before returning making state of alerts same as it would have been before going
        # to be passed in compare_n_patch_dict call in generic_patch_http
        # same goes for strat_limits.eligible_brokers
        original_strat_alerts = []
        original_eligible_brokers = []
        if (strat_status := updated_pair_strat_obj_dict.get("strat_status")) is not None:
            if (strat_alerts := strat_status.get("strat_alerts")) is not None:
                original_strat_alerts = copy.deepcopy(strat_alerts)

        if (strat_limits := updated_pair_strat_obj_dict.get("strat_limits")) is not None:
            if (eligible_brokers := strat_limits.get("eligible_brokers")) is not None:
                original_eligible_brokers = copy.deepcopy(eligible_brokers)

        updated_pydantic_obj_dict = compare_n_patch_dict(copy.deepcopy(stored_pair_strat_obj.dict(by_alias=True)),
                                                         updated_pair_strat_obj_dict)
        updated_pair_strat_obj = PairStratOptional(**updated_pydantic_obj_dict)

        id_to_alerts_dict_before_underlying_pre_update = {alert.id: alert for alert in
                                                          updated_pair_strat_obj.strat_status.strat_alerts}
        await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        id_to_alerts_dict_after_underlying_pre_update = {alert.id: alert for alert in
                                                         updated_pair_strat_obj.strat_status.strat_alerts}

        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()
        logging.debug(f"further updated by _update_pair_strat_pre, pair_strat_key: "
                      f"{get_pair_strat_log_key(stored_pair_strat_obj)};;; pair_strat: {updated_pair_strat_obj} ")

        # retrieving newly added alerts by _update_pair_strat_pre call
        new_alerts = []
        for alert_id, alert in id_to_alerts_dict_after_underlying_pre_update.items():
            # getting alerts updated from _update_pair_strat_pre call
            if alert_id not in id_to_alerts_dict_before_underlying_pre_update:
                new_alerts.append(alert)
            else:
                if alert != id_to_alerts_dict_before_underlying_pre_update[alert_id]:
                    err_str_ = "Modifying alerts in _update_pair_strat_pre call not supported, " \
                               f"pair_strat_key: {get_pair_strat_log_key(stored_pair_strat_obj)};;; " \
                               f"original alert - {id_to_alerts_dict_before_underlying_pre_update[alert_id]}, " \
                               f"modified alert - {alert}"
                    logging.error(err_str_)
                    raise HTTPException(status_code=500, detail=err_str_)
                # else not required: ignore alert if not modified in _update_pair_strat_pre call

        # making state of alerts and eligible brokers same as it would have been before going
        # to be passed in compare_n_patch_dict call in generic_patch_http
        updated_pair_strat_obj.strat_status.strat_alerts = original_strat_alerts
        updated_pair_strat_obj.strat_status.strat_alerts.extend(new_alerts)
        updated_pair_strat_obj.strat_limits.eligible_brokers = original_eligible_brokers
        return json.loads(updated_pair_strat_obj.json(by_alias=True, exclude_none=True))

    async def create_portfolio_status_pre(self, portfolio_status_obj: PortfolioStatus):
        portfolio_status_obj.alert_update_seq_num = 0

    async def update_portfolio_status_pre(self, stored_portfolio_status_obj: PortfolioStatus,
                                          updated_portfolio_status_obj: PortfolioStatus):
        if stored_portfolio_status_obj.alert_update_seq_num is None:
            updated_portfolio_status_obj.alert_update_seq_num = 1
        else:
            updated_portfolio_status_obj.alert_update_seq_num = stored_portfolio_status_obj.alert_update_seq_num + 1
        return updated_portfolio_status_obj

    async def partial_update_portfolio_status_pre(self, stored_portfolio_status_obj: PortfolioStatus,
                                                  updated_portfolio_status_obj_json: Dict):
        if updated_portfolio_status_obj_json.get("portfolio_alerts"):
            if stored_portfolio_status_obj.alert_update_seq_num is None:
                updated_portfolio_status_obj_json["alert_update_seq_num"] = 1
            else:
                updated_portfolio_status_obj_json["alert_update_seq_num"] = \
                    stored_portfolio_status_obj.alert_update_seq_num + 1
        return updated_portfolio_status_obj_json

    async def _force_publish_symbol_overview_for_ready_to_active_strat(self, pair_strat: PairStrat) -> None:
        symbols_list = [pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                        pair_strat.pair_strat_params.strat_leg2.sec.sec_id]

        for symbol in symbols_list:
            symbol_overview_obj_list = \
                market_data_service_web_client.get_symbol_overview_from_symbol_query_client(symbol)
            if len(symbol_overview_obj_list) != 0:
                if len(symbol_overview_obj_list) == 1:
                    updated_symbol_overview = SymbolOverviewBaseModel(_id=symbol_overview_obj_list[0].id,
                                                                      force_publish=True)
                    market_data_service_web_client.patch_symbol_overview_client(
                        jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True))
                else:
                    err_str_ = f"symbol_overview must be one per symbol, pair_strat_key: " \
                               f"{get_pair_strat_log_key(pair_strat)};;; symbol_overview_list: {symbol_overview_obj_list} "
                    logging.error(err_str_)
            # else not required: avoiding force publish if no symbol_overview exists

    async def _create_related_models_if_strat_is_active(self, stored_pair_strat_obj: PairStrat,
                                                        updated_pair_strat_obj: PairStrat) -> None:
        if stored_pair_strat_obj.strat_status.strat_state == StratState.StratState_READY:
            if updated_pair_strat_obj.strat_status.strat_state == StratState.StratState_ACTIVE:
                # creating strat_brief for both leg securities
                await self._create_strat_brief_for_ready_to_active_pair_strat(updated_pair_strat_obj)
                # creating symbol_side_snapshot for both leg securities if not already exists
                await self._create_symbol_snapshot_for_ready_to_active_pair_strat(updated_pair_strat_obj)
                # changing symbol_overview force_publish to True if exists
                await self._force_publish_symbol_overview_for_ready_to_active_strat(updated_pair_strat_obj)
            # else not required: if strat status is not active then avoiding creations
        # else not required: If stored strat is already active then related models would have been already created

    async def update_pair_strat_post(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        await self._create_related_models_if_strat_is_active(stored_pair_strat_obj, updated_pair_strat_obj)

    async def partial_update_pair_strat_post(self, stored_pair_strat_obj: PairStrat,
                                             updated_pair_strat_obj: PairStratOptional):
        await self._create_related_models_if_strat_is_active(stored_pair_strat_obj, updated_pair_strat_obj)

    async def get_last_order_journal_matching_suffix_order_id(self, order_id_suffix: str) -> OrderJournal | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_of_matching_suffix_order_id_filter

        stored_order_list: List[OrderJournal] = await underlying_read_order_journal_http(
            get_order_of_matching_suffix_order_id_filter(order_id_suffix, sort=-1, limit=1),
            self.get_generic_read_route())
        if len(stored_order_list) > 0:
            return stored_order_list[0]
        else:
            return None

    def _get_top_of_book_from_symbol(self, symbol: str):
        top_of_book_list: List[TopOfBookBaseModel] = \
            market_data_service_web_client.get_top_of_book_from_index_client(symbol)
        if len(top_of_book_list) != 1:
            err_str_ = f"TopOfBook should be one per symbol received {len(top_of_book_list)} for symbol {symbol} " \
                       f"- {top_of_book_list}"
            logging.error(err_str_)
            return None
        else:
            return top_of_book_list[0]

    async def _update_strat_brief_from_order(self, order_snapshot: OrderSnapshot,
                                             symbol_side_snapshot: SymbolSideSnapshot) -> StratBrief | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_strat_brief_http, underlying_partial_update_strat_brief_http, \
            underlying_get_executor_check_snapshot_query_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol

        security = symbol_side_snapshot.security
        side = symbol_side_snapshot.side
        symbol = security.sec_id
        strat_brief_objs = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol),
                                                                  self.get_generic_read_route())
        if len(strat_brief_objs) == 1:
            strat_brief_obj = strat_brief_objs[0]
            pair_strat_obj: PairStrat = await get_single_exact_match_ongoing_strat_from_symbol_n_side(symbol, side)
            if pair_strat_obj is not None:
                open_qty = (symbol_side_snapshot.total_qty -
                            (symbol_side_snapshot.total_filled_qty + symbol_side_snapshot.total_cxled_qty))
                open_notional = open_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                           order_snapshot.order_brief.security.sec_id)
                consumable_notional = \
                    pair_strat_obj.strat_limits.max_cb_notional - symbol_side_snapshot.total_fill_notional - \
                    open_notional
                consumable_open_notional = \
                    pair_strat_obj.strat_limits.max_open_cb_notional - open_notional
                security_float = self.static_data.get_security_float_from_ticker(symbol)
                if security_float is not None:
                    consumable_concentration = \
                        (security_float / 100) * pair_strat_obj.strat_limits.max_concentration - \
                        (open_qty + symbol_side_snapshot.total_filled_qty)
                else:
                    consumable_concentration = 0
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_get_open_order_count_query_http
                open_orders_count = await underlying_get_open_order_count_query_http(symbol)
                consumable_open_orders = \
                    pair_strat_obj.strat_limits.max_open_orders_per_side - open_orders_count[0].open_order_count
                consumable_cxl_qty = (((symbol_side_snapshot.total_filled_qty + open_qty +
                                        symbol_side_snapshot.total_cxled_qty) / 100) *
                                      pair_strat_obj.strat_limits.cancel_rate.max_cancel_rate) - \
                                     symbol_side_snapshot.total_cxled_qty
                applicable_period_second = \
                    pair_strat_obj.strat_limits.market_trade_volume_participation.applicable_period_seconds
                executor_check_snapshot_list = \
                    await underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                            applicable_period_second)
                if len(executor_check_snapshot_list) == 1:
                    participation_period_order_qty_sum = \
                        executor_check_snapshot_list[0].last_n_sec_order_qty
                    indicative_consumable_participation_qty = \
                        get_consumable_participation_qty(executor_check_snapshot_list,
                                                         pair_strat_obj.strat_limits.market_trade_volume_participation.max_participation_rate)
                else:
                    logging.error("Received unexpected length of executor_check_snapshot_list from query "
                                  f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                                  f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                                  f"get_executor_check_snapshot_query pre implementation")
                    indicative_consumable_participation_qty = 0
                    participation_period_order_qty_sum = 0

                updated_pair_side_brief_obj = \
                    PairSideTradingBrief(security=security, side=side,
                                         last_update_date_time=order_snapshot.last_update_date_time,
                                         consumable_open_orders=consumable_open_orders,
                                         consumable_notional=consumable_notional,
                                         consumable_open_notional=consumable_open_notional,
                                         consumable_concentration=consumable_concentration,
                                         participation_period_order_qty_sum=participation_period_order_qty_sum,
                                         consumable_cxl_qty=consumable_cxl_qty,
                                         indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                         all_bkr_cxlled_qty=symbol_side_snapshot.total_cxled_qty,
                                         open_notional=open_notional,
                                         open_qty=open_qty)

                if side == Side.BUY:
                    other_leg_residual_qty = strat_brief_obj.pair_sell_side_trading_brief.residual_qty
                    stored_pair_strat_trading_brief = strat_brief_obj.pair_buy_side_trading_brief
                    other_leg_symbol = strat_brief_obj.pair_sell_side_trading_brief.security.sec_id
                else:
                    other_leg_residual_qty = strat_brief_obj.pair_buy_side_trading_brief.residual_qty
                    stored_pair_strat_trading_brief = strat_brief_obj.pair_sell_side_trading_brief
                    other_leg_symbol = strat_brief_obj.pair_buy_side_trading_brief.security.sec_id
                top_of_book_obj = self._get_top_of_book_from_symbol(symbol)
                other_leg_top_of_book = self._get_top_of_book_from_symbol(other_leg_symbol)
                if top_of_book_obj is not None and other_leg_top_of_book is not None:
                    if order_snapshot.order_status == OrderStatusType.OE_DOD:
                        residual_qty = stored_pair_strat_trading_brief.residual_qty + \
                                       (order_snapshot.order_brief.qty - order_snapshot.filled_qty)
                        # Updating residual_qty
                        updated_pair_side_brief_obj.residual_qty = residual_qty
                    else:
                        residual_qty = stored_pair_strat_trading_brief.residual_qty
                        updated_pair_side_brief_obj.residual_qty = residual_qty
                    updated_pair_side_brief_obj.indicative_consumable_residual = \
                        pair_strat_obj.strat_limits.residual_restriction.max_residual - \
                        ((residual_qty * top_of_book_obj.last_trade.px) -
                         (other_leg_residual_qty * other_leg_top_of_book.last_trade.px))
                else:
                    logging.error(f"received buy TOB as {top_of_book_obj} and sel TOB as {other_leg_top_of_book}, "
                                  f"order_snapshot_key: {order_snapshot}")
                    return

                if symbol == strat_brief_obj.pair_buy_side_trading_brief.security.sec_id:
                    updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                             pair_buy_side_trading_brief=updated_pair_side_brief_obj)
                elif symbol == strat_brief_obj.pair_sell_side_trading_brief.security.sec_id:
                    updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                             pair_sell_side_trading_brief=updated_pair_side_brief_obj)
                else:
                    err_str_ = f"error: None of the 2 pair_side_trading_brief(s) contain symbol: {symbol} in " \
                               f"strat_brief of key: {get_strat_brief_log_key(strat_brief_obj)};;; strat_brief: " \
                               f"{strat_brief_obj}"
                    logging.exception(err_str_)
                    return

                updated_strat_brief = \
                    await underlying_partial_update_strat_brief_http(
                        json.loads(updated_strat_brief.json(by_alias=True, exclude_none=True)))
                return updated_strat_brief
            else:
                logging.error(f"error: received pair_strat as None, symbol_side_key: "
                              f"{get_symbol_side_key([(symbol, side)])}")
                return

        else:
            err_str_ = f"StratBrief must be one per symbol, received {len(strat_brief_objs)} for symbol {symbol}, " \
                       f"order_snapshot_key: {order_snapshot};;;StratBriefs: {strat_brief_objs}"
            logging.exception(err_str_)
            return

    async def get_strat_brief_from_symbol_query_pre(self, strat_brief_class_type: Type[StratBrief], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol

        return await underlying_read_strat_brief_http(get_strat_brief_from_symbol(security_id),
                                                      self.get_generic_read_route())

    async def trigger_residual_check_query_pre(self, order_snapshot_class_type: Type[OrderSnapshot],
                                               order_status: List[str]):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_open_order_snapshots_by_order_status

        return await underlying_read_order_snapshot_http(get_open_order_snapshots_by_order_status(order_status),
                                                         self.get_generic_read_route())

    async def trigger_residual_check_query_post(self, order_snapshot_obj_list_: List[OrderSnapshot]):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_journal_http, underlying_partial_update_portfolio_status_http, \
            underlying_read_portfolio_limits_by_id_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_last_n_sec_orders_by_event

        # 1. cancel any expired from passed open orders
        await self.cxl_expired_open_orders(order_snapshot_obj_list_)

        # 2. If specified interval rejected orders count exceed threshold - trigger kill switch
        # get limit from portfolio limits
        portfolio_limits_obj: PortfolioLimits = await underlying_read_portfolio_limits_by_id_http(1)
        max_allowed_rejection_within_period = portfolio_limits_obj.rolling_max_reject_count.max_rolling_tx_count
        period_in_sec = portfolio_limits_obj.rolling_max_reject_count.rolling_tx_count_period_seconds
        order_count_updated_order_journals: List[OrderJournal] = \
            await underlying_read_order_journal_http(get_last_n_sec_orders_by_event(None, period_in_sec, "OE_REJ"),
                                                     self.get_generic_read_route())
        if len(order_count_updated_order_journals) == 1:
            if order_count_updated_order_journals[0].current_period_order_count > max_allowed_rejection_within_period:
                logging.debug(f"max_allowed_rejection_within_period breached found : "
                              f"{order_count_updated_order_journals[0].current_period_order_count} "
                              f"rejections in past period - initiating auto-kill switch")
                # single top level objects are hardcoded id=1 , saves the query portfolio status, if always id=1
                portfolio_status: PortfolioStatusOptional = PortfolioStatusOptional(id=1,
                                                                                    kill_switch=True)
                await underlying_partial_update_portfolio_status_http(
                    json.loads(portfolio_status.json(by_alias=True, exclude_none=True)))
        elif len(order_count_updated_order_journals) != 0:
            err_str_ = "Must receive only one object from get_last_n_sec_orders_by_event_query, " \
                       f"received: {order_count_updated_order_journals}"
            logging.error(err_str_)
        # else not required - no rejects found - no action

        # 3. No one expects anything useful to be returned - just return empty list
        return []

    async def cxl_expired_open_orders(self, order_snapshot_obj_list: List[OrderSnapshot]):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_create_cancel_order_http
        for order_snapshot in order_snapshot_obj_list:
            symbol = order_snapshot.order_brief.security.sec_id
            side = order_snapshot.order_brief.side
            pair_strat_obj = await get_single_exact_match_ongoing_strat_from_symbol_n_side(symbol, side)
            time_delta = DateTime.utcnow() - order_snapshot.create_date_time
            if pair_strat_obj is not None and (time_delta.total_seconds() >
                                               pair_strat_obj.strat_limits.residual_restriction.residual_mark_seconds):
                cancel_order: CancelOrder = CancelOrder(order_id=order_snapshot.order_brief.order_id,
                                                        security=order_snapshot.order_brief.security,
                                                        side=order_snapshot.order_brief.side,
                                                        cxl_confirmed=False)
                # trigger cancel if it does not already exist for this order id, otherwise log for alert
                from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_by_order_id_filter
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_read_cancel_order_http
                cxl_order_list: List[CancelOrder] | None = await underlying_read_cancel_order_http(
                    get_order_by_order_id_filter(cancel_order.order_id), self.get_generic_read_route())
                if not cxl_order_list:
                    await underlying_create_cancel_order_http(cancel_order)
                else:
                    if len(cxl_order_list) == 1:
                        if not cxl_order_list[0].cxl_confirmed:
                            logging.error(f"cxl_expired_open_orders failed: Prior cxl request found in DB for this "
                                          f"order-id: {cancel_order.order_id}, use swagger to delete this order-id "
                                          f"from DB to trigger cxl request again, order_snapshot_key: "
                                          f"{get_order_snapshot_log_key(order_snapshot)};;;order_snapshot: {order_snapshot}")
                    else:
                        logging.error(f"There must be only one cancel_order obj per order_id, received "
                                      f"{cxl_order_list} for order_id {order_snapshot.order_brief.order_id}, "
                                      f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot)}")
            # else not required: If pair_strat_obj is None or If time-delta is still less than
            # residual_mark_seconds then avoiding cancellation of order

    async def get_last_n_sec_orders_by_event_query_pre(self, order_journal_class_type: Type[OrderJournal],
                                                       symbol: str | None, last_n_sec: int, order_event: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_last_n_sec_orders_by_event
        return await underlying_read_order_journal_http(get_last_n_sec_orders_by_event(symbol, last_n_sec, order_event),
                                                        self.get_generic_read_route())

    async def get_ongoing_strats_symbol_n_exch_query_pre(self,
                                                         ongoing_strat_symbols_class_type: Type[
                                                             OngoingStratsSymbolNExchange]):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter

        pair_strat_list: List[PairStrat] = await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(),
                                                                                 self.get_generic_read_route())
        ongoing_symbol_n_exch_set: Set[str] = set()
        ongoing_strat_symbols_n_exchange = OngoingStratsSymbolNExchange(symbol_n_exchange=[])

        before_len: int = 0
        for pair_strat in pair_strat_list:
            leg1_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            leg1_exch = pair_strat.pair_strat_params.strat_leg1.exch_id
            leg2_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            leg2_exch = pair_strat.pair_strat_params.strat_leg2.exch_id
            leg1_symbol_n_exch = SymbolNExchange(symbol=leg1_symbol, exchange=leg1_exch)
            leg2_symbol_n_exch = SymbolNExchange(symbol=leg2_symbol, exchange=leg2_exch)

            ongoing_symbol_n_exch_set.add(f"{leg1_symbol}_{leg1_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_strat_symbols_n_exchange.symbol_n_exchange.append(leg1_symbol_n_exch)
                before_len += 1

            ongoing_symbol_n_exch_set.add(f"{leg2_symbol}_{leg2_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_strat_symbols_n_exchange.symbol_n_exchange.append(leg2_symbol_n_exch)
                before_len += 1
        return [ongoing_strat_symbols_n_exchange]

    @staticmethod
    def get_id_from_strat_key(unloaded_strat_key: str) -> int:
        parts: List[str] = (unloaded_strat_key.split("-"))
        return int(parts[-1])

    async def _delete_strat_brief_for_unload_strat(self, pair_strat_obj: PairStrat):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_strat_brief_http, underlying_delete_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol

        symbol = pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id

        # since strat_brief has both symbols as pair_strat has, so any symbol will give same strat_brief
        strat_brief_objs_list = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol),
                                                                       self.get_generic_read_route())

        if len(strat_brief_objs_list) > 1:
            err_str_ = f"strat_brief must be only one per symbol, pair_strat_key: " \
                       f"{get_pair_strat_log_key(pair_strat_obj)};;; strat_brief_list: {strat_brief_objs_list}"
            logging.error(err_str_)
            return
        elif len(strat_brief_objs_list) == 1:
            strat_brief_obj = strat_brief_objs_list[0]
            await underlying_delete_strat_brief_http(strat_brief_obj.id)
            return
        else:
            err_str_ = f"Could not find any strat_brief with symbol {symbol} already existing to be deleted " \
                       f"while strat unload, pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)}"
            logging.error(err_str_)
            return

    async def _delete_symbol_side_snapshot_from_unload_strat(self, pair_strat_obj):
        pair_symbol_side_list = [
            (pair_strat_obj.pair_strat_params.strat_leg1.sec, pair_strat_obj.pair_strat_params.strat_leg1.side),
            (pair_strat_obj.pair_strat_params.strat_leg2.sec, pair_strat_obj.pair_strat_params.strat_leg2.side)
        ]

        for security, side in pair_symbol_side_list:
            symbol_side_snapshots = await self._get_symbol_side_snapshot_from_symbol_side(security.sec_id, side)

            if len(symbol_side_snapshots) == 1:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                    underlying_delete_symbol_side_snapshot_http
                symbol_side_snapshot = symbol_side_snapshots[0]
                await underlying_delete_symbol_side_snapshot_http(symbol_side_snapshot.id)
            elif len(symbol_side_snapshots) > 1:
                err_str_ = f"SymbolSideSnapshot must be one per symbol and side, symbol_side_key: " \
                           f"{get_symbol_side_key([(security.sec_id, side)])};;; symbol_side_snapshot: " \
                           f"{symbol_side_snapshots}"
                logging.error(err_str_)
                return
            else:
                err_str_ = f"Could not find symbol_side_snapshot for symbol_side_key " \
                           f"{get_symbol_side_key([(security.sec_id, side)])}, " \
                           f"must be present already to be deleted while strat unload;;; " \
                           f"pair_strat: {pair_strat_obj}"
                logging.error(err_str_)
                return
        return

    async def _force_unpublish_symbol_overview_from_unload_strat(self, pair_strat_obj: PairStrat):
        symbols_list = [pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                        pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id]

        for symbol in symbols_list:
            symbol_overview_obj_list = \
                market_data_service_web_client.get_symbol_overview_from_symbol_query_client(symbol)
            if len(symbol_overview_obj_list) != 0:
                if len(symbol_overview_obj_list) == 1:
                    updated_symbol_overview = SymbolOverviewBaseModel(_id=symbol_overview_obj_list[0].id,
                                                                      force_publish=False)
                    market_data_service_web_client.patch_symbol_overview_client(
                        jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True))
                else:
                    err_str_ = f"symbol_overview must be one per symbol, pair_strat_key: " \
                               f"{get_pair_strat_log_key(pair_strat_obj)}" \
                               f";;; symbol_overview_list: {symbol_overview_obj_list}"
                    logging.error(err_str_)
            else:
                err_str_ = f"Could not find symbol_overview for symbol {symbol} while unloading strat, " \
                           f"pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)};;; " \
                           f"pair_strat: {pair_strat_obj}"
                logging.error(err_str_)

    async def _delete_strat_relative_models(self, pair_strat_obj: PairStrat):
        # deleting related strat_brief
        await self._delete_strat_brief_for_unload_strat(pair_strat_obj)

        # deleting related symbol_side_snapshot
        await self._delete_symbol_side_snapshot_from_unload_strat(pair_strat_obj)

        # Force un-publish related symbol_overview
        await self._force_unpublish_symbol_overview_from_unload_strat(pair_strat_obj)

    async def unload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_pair_strat_by_id_http, underlying_update_pair_strat_http
        updated_strat_collection_loaded_strat_keys_frozenset = frozenset(updated_strat_collection_obj.loaded_strat_keys)
        stored_strat_collection_loaded_strat_keys_frozenset = frozenset(stored_strat_collection_obj.loaded_strat_keys)
        # existing items in stored loaded frozenset but not in the updated stored frozen set need to move to done state
        unloaded_strat_keys_frozenset = stored_strat_collection_loaded_strat_keys_frozenset.difference(
            updated_strat_collection_loaded_strat_keys_frozenset)
        if len(unloaded_strat_keys_frozenset) != 0:
            unloaded_strat_key: str
            for unloaded_strat_key in unloaded_strat_keys_frozenset:
                if unloaded_strat_key in updated_strat_collection_obj.buffered_strat_keys:  # unloaded not deleted
                    pair_strat_id: int = self.get_id_from_strat_key(unloaded_strat_key)
                    pair_strat = await underlying_read_pair_strat_by_id_http(pair_strat_id)
                    if is_ongoing_pair_strat(pair_strat):
                        error_str = f"unloading and ongoing pair strat key: {unloaded_strat_key} is not supported, " \
                                    f"current strat state: {pair_strat.strat_status.strat_state}, " \
                                    f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}"
                        logging.error(error_str)
                        raise HTTPException(status_code=400, detail=error_str)
                    elif pair_strat.strat_status.strat_state == StratState.StratState_DONE:
                        # removing and updating relative models
                        await self._delete_strat_relative_models(pair_strat)

                        strat_status = StratStatus(strat_state=StratState.StratState_READY, strat_alerts=[])
                        updated_pair_strat = PairStratOptional(_id=pair_strat.id,
                                                               pair_strat_params=pair_strat.pair_strat_params,
                                                               strat_status=strat_status,
                                                               pair_strat_params_update_seq_num=0,
                                                               strat_status_update_seq_num=0,
                                                               strat_limits_update_seq_num=0)
                        await underlying_update_pair_strat_http(updated_pair_strat)

                # else: deleted not unloaded - nothing to do , DB will remove entry

    async def reload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_pair_strat_by_id_http, underlying_delete_pair_strat_http, underlying_create_pair_strat_http
        updated_strat_collection_buffered_strat_keys_frozenset = frozenset(
            updated_strat_collection_obj.buffered_strat_keys)
        stored_strat_collection_buffered_strat_keys_frozenset = frozenset(
            stored_strat_collection_obj.buffered_strat_keys)
        # existing items in stored buffered frozenset but not in the updated stored frozen set need to
        # move to ready state
        reloaded_strat_keys_frozenset = stored_strat_collection_buffered_strat_keys_frozenset.difference(
            updated_strat_collection_buffered_strat_keys_frozenset)
        if len(reloaded_strat_keys_frozenset) != 0:
            reloaded_strat_key: str
            for reloaded_strat_key in reloaded_strat_keys_frozenset:
                if reloaded_strat_key in updated_strat_collection_obj.loaded_strat_keys:  # loaded not deleted
                    pair_strat_id: int = self.get_id_from_strat_key(reloaded_strat_key)
                    pair_strat = await underlying_read_pair_strat_by_id_http(pair_strat_id)
                    if is_ongoing_pair_strat(pair_strat):
                        error_str = f"reloading and ongoing pair strat key: {reloaded_strat_key} is not supported, " \
                                    f"current strat state: {pair_strat.strat_status.strat_state}, " \
                                    f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}"
                        logging.error(error_str)
                        raise HTTPException(status_code=400, detail=error_str)
                    elif pair_strat.strat_status.strat_state == StratState.StratState_READY:
                        # deleting existing pair_strat and then recreating strat with same id and pair_strat_params
                        # so that new pair_strat is loaded with the latest limits
                        existing_pair_strat_params = pair_strat.pair_strat_params
                        await underlying_delete_pair_strat_http(pair_strat_id)
                        new_pair_strat = PairStrat(_id=pair_strat_id, pair_strat_params=existing_pair_strat_params)
                        try:
                            await underlying_create_pair_strat_http(new_pair_strat)
                        except Exception as e:
                            from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
                                update_strat_collection_http
                            updated_strat_collection_obj.loaded_strat_keys.remove(reloaded_strat_key)
                            await update_strat_collection_http(updated_strat_collection_obj)

                            err_str_ = f"Failed to create strat of key {reloaded_strat_key} after deletion " \
                                       f"while reloading, pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; " \
                                       f"deleted_pair_strat: {pair_strat}, raised exception {e}"
                            logging.error(err_str_)
                            raise HTTPException(status_code=400, detail=err_str_)
                # else: deleted not loaded - nothing to do , DB will remove entry

    async def update_strat_collection_pre(self, stored_strat_collection_obj: StratCollection,
                                          updated_strat_collection_obj: StratCollection):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_collection_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # handling unloading pair_strats
        await self.unload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        # handling reloading pair_strat
        await self.reload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        return updated_strat_collection_obj

    async def get_symbol_side_underlying_account_cumulative_fill_qty_query_pre(
            self, fills_journal_class_type: Type[FillsJournal], symbol: str, side: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_fills_journal_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import \
            get_symbol_side_underlying_account_cumulative_fill_qty
        return await underlying_read_fills_journal_http(
            get_symbol_side_underlying_account_cumulative_fill_qty(symbol, side), self.get_generic_read_route())

    async def get_underlying_account_cumulative_fill_qty_query_pre(
            self, underlying_account_cum_fill_qty_class_type: Type[UnderlyingAccountCumFillQty],
            symbol: str, side: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            get_symbol_side_underlying_account_cumulative_fill_qty_query_http
        fill_journal_obj_list = await get_symbol_side_underlying_account_cumulative_fill_qty_query_http(symbol, side)

        underlying_accounts: Set[str] = set()
        underlying_accounts_cum_fill_qty_obj: UnderlyingAccountCumFillQty = UnderlyingAccountCumFillQty(
            underlying_account_n_cumulative_fill_qty=[]
        )
        for fill_journal_obj in fill_journal_obj_list:
            if (underlying_acc := fill_journal_obj.underlying_account) not in underlying_accounts:
                underlying_accounts.add(underlying_acc)
                underlying_accounts_cum_fill_qty_obj.underlying_account_n_cumulative_fill_qty.append(
                    UnderlyingAccountNCumFillQty(underlying_account=underlying_acc,
                                                 cumulative_qty=fill_journal_obj.underlying_account_cumulative_fill_qty)
                )
        return [underlying_accounts_cum_fill_qty_obj]

    async def get_last_n_sec_order_qty(self, symbol: str, side: Side, last_n_sec: int) -> int | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_total_sum_of_last_n_sec

        last_n_sec_order_qty: int | None = None
        if last_n_sec == 0:
            symbol_side_snapshots = await self._get_symbol_side_snapshot_from_symbol_side(symbol, side)
            if symbol_side_snapshots is not None:
                if len(symbol_side_snapshots) == 1:
                    symbol_side_snapshot = symbol_side_snapshots[0]
                else:
                    err_str_ = f"Could not find symbol_side_snapshot, symbol_side_key: " \
                               f"{get_symbol_side_key([(symbol, side)])}"
                    logging.error(err_str_)
                    return None
                last_n_sec_order_qty = symbol_side_snapshot.total_qty
            else:
                err_str_ = f"Found multiple symbol_side_snapshot for symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}, must be only one"
                logging.exception(err_str_)
        else:
            agg_objs = \
                await underlying_read_order_snapshot_http(get_order_total_sum_of_last_n_sec(symbol, last_n_sec),
                                                          self.get_generic_read_route())

            if len(agg_objs) > 0:
                last_n_sec_order_qty = agg_objs[-1].last_n_sec_total_qty
            else:
                last_n_sec_order_qty = 0
                err_str_ = "received empty list of aggregated objects from aggregation on OrderSnapshot to " \
                           f"get last {last_n_sec} sec total order sum, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.debug(err_str_)
        return last_n_sec_order_qty

    async def get_last_n_sec_trade_qty(self, symbol: str, side: Side) -> int | None:
        pair_strat = await get_single_exact_match_ongoing_strat_from_symbol_n_side(symbol, side)
        last_n_sec_trade_qty: int | None = None
        if pair_strat is not None:
            applicable_period_seconds = \
                pair_strat.strat_limits.market_trade_volume_participation.applicable_period_seconds
            last_n_sec_market_trade_vol_obj_list = \
                market_data_service_web_client.get_last_n_sec_total_qty_query_client(symbol, applicable_period_seconds)
            if last_n_sec_market_trade_vol_obj_list:
                last_n_sec_trade_qty = last_n_sec_market_trade_vol_obj_list[0].last_n_sec_trade_vol
            else:
                logging.error(f"could not receive any last_n_sec_market_trade_vol_obj to get last_n_sec_trade_qty "
                              f"for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, likely bug in "
                              f"get_last_n_sec_total_qty_query pre impl")
        return last_n_sec_trade_qty

    async def get_rolling_new_order_count(self, symbol: str) -> int | None:
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_portfolio_limits_by_id_http, underlying_get_last_n_sec_orders_by_event_query_http
        portfolio_limits_obj = await underlying_read_portfolio_limits_by_id_http(1)

        rolling_order_count_period_seconds = \
            portfolio_limits_obj.rolling_max_order_count.rolling_tx_count_period_seconds

        order_count_updated_order_journals = \
            await underlying_get_last_n_sec_orders_by_event_query_http(symbol,
                                                                       rolling_order_count_period_seconds,
                                                                       OrderEventType.OE_NEW)
        if len(order_count_updated_order_journals) == 1:
            rolling_new_order_count = order_count_updated_order_journals[-1].current_period_order_count
        elif len(order_count_updated_order_journals) > 1:
            err_str_ = "Must receive only one object by get_last_n_sec_orders_by_event_query, " \
                       f"received {order_count_updated_order_journals} for symbol {symbol}"
            logging.error(err_str_)
            return None
        else:
            rolling_new_order_count = 0
        return rolling_new_order_count

    async def get_list_of_underlying_account_n_cumulative_fill_qty(self, symbol: str, side: Side):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            get_underlying_account_cumulative_fill_qty_query_http
        underlying_account_cum_fill_qty_obj_list = \
            await get_underlying_account_cumulative_fill_qty_query_http(symbol, side)
        return underlying_account_cum_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty

    async def get_executor_check_snapshot_query_pre(self, executor_check_snapshot_class_type: Type[
        ExecutorCheckSnapshot], symbol: str, side: Side, last_n_sec: int):

        last_n_sec_order_qty = await self.get_last_n_sec_order_qty(symbol, side, last_n_sec)

        last_n_sec_trade_qty = await self.get_last_n_sec_trade_qty(symbol, side)

        rolling_new_order_count = await self.get_rolling_new_order_count(symbol)

        if last_n_sec_order_qty is not None and \
                last_n_sec_trade_qty is not None and \
                rolling_new_order_count is not None:
            # if no data is found by respective queries then all fields are set to 0 and every call returns
            # executor_check_snapshot object (except when exception occurs)
            executor_check_snapshot = \
                ExecutorCheckSnapshot(last_n_sec_trade_qty=last_n_sec_trade_qty,
                                      last_n_sec_order_qty=last_n_sec_order_qty,
                                      rolling_new_order_count=rolling_new_order_count)
            return [executor_check_snapshot]
        else:
            # will only return [] if some error occurred
            logging.error(f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}, "
                          f"Received last_n_sec_order_qty - {last_n_sec_order_qty}, "
                          f"last_n_sec_trade_qty - {last_n_sec_trade_qty}, "
                          f"rolling_new_order_count - {rolling_new_order_count} and  last_n_sec - {last_n_sec}")
            return []

    async def get_open_order_count_query_pre(self, open_order_count_class_type: Type[OpenOrderCount], symbol: str):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_open_order_snapshots_for_symbol

        open_orders = await underlying_read_order_snapshot_http(get_open_order_snapshots_for_symbol(symbol),
                                                                self.get_generic_read_route())

        open_order_count = OpenOrderCount(open_order_count=len(open_orders))
        return [open_order_count]

    async def update_residuals_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str, side: Side,
                                         residual_qty: int):
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_pair_strat_http, journal_shared_lock, underlying_read_strat_brief_http, \
            underlying_partial_update_pair_strat_http, underlying_partial_update_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter, \
            get_strat_brief_from_symbol

        async with journal_shared_lock:
            # updating residual qty
            strat_brief_objs = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(security_id),
                                                                      self.get_generic_read_route())

            if len(strat_brief_objs) == 1:
                strat_brief_obj = strat_brief_objs[0]
                if side == Side.BUY:
                    update_trading_side_brief = \
                        PairSideTradingBriefOptional(
                            residual_qty=strat_brief_obj.pair_buy_side_trading_brief.residual_qty + residual_qty)
                    update_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                            pair_buy_side_trading_brief=update_trading_side_brief)

                else:
                    update_trading_side_brief = \
                        PairSideTradingBriefOptional(
                            residual_qty=strat_brief_obj.pair_sell_side_trading_brief.residual_qty + residual_qty)
                    update_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                            pair_sell_side_trading_brief=update_trading_side_brief)

                updated_strat_brief = await underlying_partial_update_strat_brief_http(
                    json.loads(update_strat_brief.json(by_alias=True, exclude_none=True)))
            else:
                err_str_ = f"StratBrief must be one per symbol, received {len(strat_brief_objs)} " \
                           f"for symbol_side_key: {get_symbol_side_key([(security_id, side)])};;;" \
                           f"StratBriefs: {strat_brief_objs}"
                logging.exception(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # updating pair_strat's residual notional
            ongoing_pair_strats = await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(security_id),
                                                                        self.get_generic_read_route())
            if len(ongoing_pair_strats) == 1:
                ongoing_pair_strat = ongoing_pair_strats[0]
                updated_residual = self.__get_residual_obj(side, updated_strat_brief)
                if updated_residual is not None:
                    strat_status = StratStatusOptional(residual=updated_residual)
                    update_pair_strat = PairStratOptional(_id=ongoing_pair_strat.id, strat_status=strat_status)
                    await underlying_partial_update_pair_strat_http(
                        json.loads(update_pair_strat.json(by_alias=True, exclude_none=True)))

                else:
                    err_str_ = f"Something went wrong while computing residual for security_side_key: " \
                               f"{get_symbol_side_key([(security_id, side)])}"
                    logging.exception(err_str_)
                    raise HTTPException(status_code=500, detail=err_str_)
            else:
                err_str_ = f"Expected one pair_strat per symbol, symbol_side_key: " \
                           f"{get_symbol_side_key([(security_id, side)])}, received {ongoing_pair_strats}"
                logging.exception(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # nothing to send since this query updates residuals only
            return []

    async def get_ongoing_strat_from_symbol_side_query_pre(self, pair_strat_class_type: Type[PairStrat], sec_id: str,
                                                           side: Side):
        ongoing_strat = await get_single_exact_match_ongoing_strat_from_symbol_n_side(sec_id, side)
        if ongoing_strat is None:
            # checking if no match found or if something unexpected happened
            match_level_1_pair_strats, match_level_2_pair_strats = \
                await get_ongoing_strats_from_symbol_n_side(sec_id, side)
            if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
                return []
            else:
                err_str_ = "Something unexpected happened while fetching ongoing strats, " \
                           f"please check logs for more details, symbol_side_snapshot: " \
                           f"{get_symbol_side_key([(sec_id, side)])}"
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
        return [ongoing_strat]

    async def create_command_n_control_pre(self, command_n_control_obj: CommandNControl):
        match command_n_control_obj.command_type:
            case CommandType.CLEAR_STRAT:
                async with self.active_ticker_pair_strat_id_dict_lock:
                    self.pair_strat_id_n_today_activated_tickers_dict.clear()
                    store_json_or_dict_to_file(self.pair_strat_id_n_today_activated_tickers_dict_file_name,
                                               self.pair_strat_id_n_today_activated_tickers_dict,
                                               CURRENT_PROJECT_DATA_DIR)
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_beanie_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_command_n_control_pre failed. unrecognized command_type: {other_}")

    async def get_raw_performance_data_of_callable_query_pre(
            self, raw_performance_data_of_callable_class_type: Type[RawPerformanceDataOfCallable], callable_name: str):
        from Flux.CodeGenProjects.addressbook.app.aggregate import \
            get_raw_performance_data_from_callable_name_agg_pipeline
        from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
            underlying_read_raw_performance_data_http

        raw_performance_data_list = \
            await underlying_read_raw_performance_data_http(
                get_raw_performance_data_from_callable_name_agg_pipeline(callable_name), self.get_generic_read_route())

        raw_performance_data_of_callable = RawPerformanceDataOfCallable(raw_performance_data=raw_performance_data_list)

        return [raw_performance_data_of_callable]

    async def filtered_notify_order_journal_update_query_ws_pre(self):
        return filter_ws_order_journal

    async def filtered_notify_order_snapshot_update_query_ws_pre(self):
        return filter_ws_order_snapshot

    async def filtered_notify_symbol_side_snapshot_update_query_ws_pre(self):
        return filter_ws_symbol_side_snapshot

    async def filtered_notify_fills_journal_update_query_ws_pre(self):
        return filter_ws_fills_journal

    async def filtered_notify_pair_strat_update_query_ws_pre(self):
        return filter_ws_pair_strat

    async def filtered_notify_strat_brief_update_query_ws_pre(self):
        return filter_ws_strat_brief


def filter_ws_order_journal(order_journal_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    order = order_journal_obj_json.get("order")
    if order is not None:
        security = order.get("security")
        if security is not None:
            sec_id = security.get("sec_id")
            if sec_id is not None:
                if sec_id in symbols:
                    return True
    return False


def filter_ws_order_snapshot(order_snapshot_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    order = order_snapshot_obj_json.get("order")
    if order is not None:
        security = order.get("security")
        if security is not None:
            sec_id = security.get("sec_id")
            if sec_id is not None:
                if sec_id in symbols:
                    return True
    return False


def filter_ws_symbol_side_snapshot(symbol_side_snapshot_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    security = symbol_side_snapshot_obj_json.get("security")
    if security is not None:
        sec_id = security.get("sec_id")
        if sec_id is not None:
            if sec_id == symbols:
                return True
    return False


def filter_ws_fills_journal(fills_journal_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    fill_symbol = fills_journal_obj_json.get("fill_symbol")
    if fill_symbol is not None:
        if fill_symbol == symbols:
            return True
    return False


def filter_ws_pair_strat(pair_strat_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    pair_strat_params = pair_strat_obj_json.get("pair_strat_params")
    if pair_strat_params is not None:
        strat_leg1 = pair_strat_params.get("strat_leg1")
        strat_leg2 = pair_strat_params.get("strat_leg2")
        if strat_leg1 is not None and strat_leg2 is not None:
            security1 = strat_leg1.get("sec")
            security2 = strat_leg2.get("sec")
            if security1 is not None and security2 is not None:
                sec1_id = security1.get("sec_id")
                sec2_id = security2.get("sec_id")
                if sec1_id in symbols or sec2_id in symbols:
                    return True
    return False


def filter_ws_strat_brief(strat_brief_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    pair_buy_side_trading_brief = strat_brief_obj_json.get("pair_buy_side_trading_brief")
    pair_sell_side_trading_brief = strat_brief_obj_json.get("pair_sell_side_trading_brief")
    if pair_buy_side_trading_brief is not None and pair_sell_side_trading_brief is not None:
        security_buy = pair_buy_side_trading_brief.get("security")
        security_sell = pair_sell_side_trading_brief.get("security")
        if security_buy is not None and security_sell is not None:
            sec1_id = security_buy.get("sec_id")
            sec2_id = security_sell.get("sec_id")
            if sec1_id in symbols or sec2_id in symbols:
                return True
    return False

