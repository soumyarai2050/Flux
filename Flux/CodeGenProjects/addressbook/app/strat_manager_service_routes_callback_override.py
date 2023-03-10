# system imports
import logging
import time
from typing import List, Type, Tuple, Dict, FrozenSet, Set
import threading
from pathlib import PurePath
from datetime import date, datetime

# third-party package imports
from pendulum import DateTime, local_timezone
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.addressbook.app.service_state import ServiceState
from FluxPythonUtils.scripts.utility_functions import avg_of_new_val_sum_to_avg, store_json_or_dict_to_file, \
    load_json_dict_from_file, load_yaml_configurations, get_host_port_from_env
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import TopOfBookBaseModel
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import is_service_up, \
    create_alert, update_strat_alert_by_sec_and_side_async, get_new_strat_limits, \
    get_single_exact_match_ongoing_strat_from_symbol_n_side, get_portfolio_limits, is_ongoing_pair_strat, \
    create_portfolio_limits, get_order_limits, create_order_limits, except_n_log_alert

PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

host, port = get_host_port_from_env()

strat_manager_service_web_client = StratManagerServiceWebClient(host, port)
market_data_service_web_client = MarketDataServiceWebClient(host, 8040)


class StratManagerServiceRoutesCallbackOverride(StratManagerServiceRoutesCallback):

    def __init__(self):
        self.service_ready: bool = False
        # dict of pair_strat_id and their activated tickers from today
        self.active_ticker_pair_strat_id_dict_lock: threading.Lock = threading.Lock()
        self.pair_strat_id_n_today_activated_tickers_dict_file_name: str = f'pair_strat_id_n_today_activated_' \
                                                                           f'tickers_dict_{date.today()}'
        self.pair_strat_id_n_today_activated_tickers_dict: Dict[str, int] | None = \
            load_json_dict_from_file(self.pair_strat_id_n_today_activated_tickers_dict_file_name, PROJECT_DATA_DIR,
                                     must_exist=False)
        if self.pair_strat_id_n_today_activated_tickers_dict is None:
            self.pair_strat_id_n_today_activated_tickers_dict = dict()
        config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"
        config_dict = load_yaml_configurations(str(config_file_path))
        self.min_refresh_interval: int = int(config_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30

        self.minimum_refresh_interval = 30
        super().__init__()

    def _check_and_create_order_and_portfolio_limits(self) -> None:
        if (order_limits := get_order_limits()) is None:
            order_limits = create_order_limits()
        if (portfolio_limits := get_portfolio_limits()) is None:
            portfolio_limits = create_portfolio_limits()
        return

    def _app_launch_pre_thread_func(self):
        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            if not self.service_ready:
                try:
                    if is_service_up():
                        self._check_and_create_order_and_portfolio_limits()
                        self.service_ready = True
                    else:
                        should_sleep = True
                except Exception as e:
                    logging.error("unexpected: service startup threw exception, "
                                  f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                  f";;;exception: {e}", exc_info=True)
            else:
                should_sleep = True
                # any periodic refresh code goes here
                try:
                    # Gets all open orders, updates residuals and raises pause to strat if req
                    strat_manager_service_web_client.get_open_order_snapshots_by_order_status_query_client(["OE_ACKED"])
                except Exception as e:
                    logging.error("periodic open order check failed, "
                                  "periodic order state checks will not be honored and retried in next periodic cycle"
                                  f";;;exception: {e}", exc_info=True)

    # Example 0 of 5: pre- and post-launch server
    def app_launch_pre(self):
        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    async def create_order_journal_pre(self, order_journal_obj: OrderJournal) -> None:
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            raise HTTPException(status_code=503, detail="create_order_journal_pre not ready - service is not "
                                                        "initialized yet")
        # updating order notional in order journal obj

        if order_journal_obj.order_event == OrderEventType.OE_NEW and order_journal_obj.order.px == 0:
            top_of_book_obj = self._get_top_of_book_from_symbol(order_journal_obj.order.security.sec_id)
            order_journal_obj.order.px = top_of_book_obj.last_trade.px
        # If order_journal is not new then we don't care about px, we care about event_type and if order is new
        # and px is not 0 then using provided px

        if order_journal_obj.order.px is not None and order_journal_obj.order.qty is not None:
            order_journal_obj.order.order_notional = order_journal_obj.order.px * order_journal_obj.order.qty
        else:
            order_journal_obj.order.order_notional = 0

    async def create_order_journal_post(self, order_journal_obj: OrderJournal):
        with OrderSnapshot.reentrant_lock:
            with PairStrat.reentrant_lock:
                await self._update_order_snapshot_from_order_journal(order_journal_obj)

    async def _get_order_snapshot_from_order_journal_order_id(self,
                                                              order_journal_obj: OrderJournal) -> OrderSnapshot | None:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json

        order_id = order_journal_obj.order.order_id
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(order_id))
        if len(order_snapshot_objs) == 1:
            return order_snapshot_objs[0]
        elif len(order_snapshot_objs) == 0:
            err_str_ = f"Could not find any order snapshot with order_id {order_id} to be updated for " \
                       f"order_journal {order_journal_obj}"
            await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                           order_journal_obj.order.side, err_str_)
        else:
            err_str_ = f"Match should return list of only one order_snapshot obj per order_id, " \
                       f"returned {order_snapshot_objs} to be updated for order_journal {order_journal_obj}"
            await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                           order_journal_obj.order.side, err_str_)

    async def _check_state_and_get_order_snapshot_obj(self, order_journal_obj: OrderJournal,  # NOQA
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
                err_str_ = f"order_journal - {order_journal_obj} received to update status of " \
                           f"order_snapshot - {order_snapshot_obj}, but order_snapshot " \
                           f"doesn't contain any order_status of list {expected_status_list}"
                await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                               order_journal_obj.order.side, err_str_)
        # else not required: error occurred in _get_order_snapshot_from_order_journal_order_id,
        # alert must have updated

    async def _create_symbol_side_snapshot_for_new_order(self,
                                                         new_order_journal_obj: OrderJournal) -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
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
                                                      order_create_count=1
                                                      )
        symbol_side_snapshot_obj = \
            await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
        return symbol_side_snapshot_obj


    async def _create_update_symbol_side_snapshot_from_order_journal(self, order_journal_obj: OrderJournal,  # NOQA
                                                                     order_snapshot_obj: OrderSnapshot
                                                                     ) -> SymbolSideSnapshot | None:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http, underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(order_journal_obj.order.security.sec_id,
                                                          order_journal_obj.order.side))
        # If no symbol_side_snapshot for symbol-side of received order_journal
        if len(symbol_side_snapshot_objs) == 0:
            if order_journal_obj.order_event == OrderEventType.OE_NEW:
                created_symbol_side_snapshot = await self._create_symbol_side_snapshot_for_new_order(order_journal_obj)
                return created_symbol_side_snapshot
            else:
                err_str_ = "Can't handle order_journal event if not OE_NEW to create symbol_side_snapshot"
                await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                               order_journal_obj.order.side, err_str_)
                return
        # If symbol_side_snapshot exists for order_id from order_journal
        elif len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            match order_journal_obj.order_event:
                case OrderEventType.OE_NEW:
                    updated_symbol_side_snapshot_obj.order_create_count = symbol_side_snapshot_obj.order_create_count + 1
                    updated_symbol_side_snapshot_obj.avg_px = \
                        avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                  order_journal_obj.order.px,
                                                  updated_symbol_side_snapshot_obj.order_create_count
                                                  )
                    updated_symbol_side_snapshot_obj.total_qty = symbol_side_snapshot_obj.total_qty + order_journal_obj.order.qty
                    updated_symbol_side_snapshot_obj.last_update_date_time = order_journal_obj.order_event_date_time
                case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                    updated_symbol_side_snapshot_obj.total_cxled_qty = symbol_side_snapshot_obj.total_cxled_qty + order_snapshot_obj.cxled_qty
                    updated_symbol_side_snapshot_obj.total_cxled_notional = symbol_side_snapshot_obj.total_cxled_notional + order_snapshot_obj.cxled_notional
                    updated_symbol_side_snapshot_obj.avg_cxled_px = (updated_symbol_side_snapshot_obj.total_cxled_notional / updated_symbol_side_snapshot_obj.total_cxled_qty) if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0
                    updated_symbol_side_snapshot_obj.last_update_date_time = order_journal_obj.order_event_date_time
                case other_:
                    err_str_ = f"Unsupported StratEventType for symbol_side_snapshot update {other_}"
                    await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                                   order_journal_obj.order.side, err_str_)
                    return
            updated_symbol_side_snapshot_obj = \
                await underlying_partial_update_symbol_side_snapshot_http(updated_symbol_side_snapshot_obj)
            return updated_symbol_side_snapshot_obj
        else:
            err_str_ = "SymbolSideSnapshot can't be multiple for single symbol and side combination, " \
                       f"received {len(symbol_side_snapshot_objs)} - {symbol_side_snapshot_objs}"
            await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                           order_journal_obj.order.side, err_str_)
            return

    async def _update_symbol_side_snapshot_from_fills_journal(self, fills_journal: FillsJournal,  # NOQA
                                                              order_snapshot_obj: OrderSnapshot) -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http, \
            underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(order_snapshot_obj.order_brief.security.sec_id,
                                                          order_snapshot_obj.order_brief.side))

        if len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            updated_symbol_side_snapshot_obj.total_filled_qty = \
                symbol_side_snapshot_obj.total_filled_qty + fills_journal.fill_qty
            updated_symbol_side_snapshot_obj.total_fill_notional = \
                symbol_side_snapshot_obj.total_fill_notional + fills_journal.fill_notional
            updated_symbol_side_snapshot_obj.avg_fill_px = \
                updated_symbol_side_snapshot_obj.total_fill_notional / updated_symbol_side_snapshot_obj.total_filled_qty
            updated_symbol_side_snapshot_obj.last_update_fill_px = fills_journal.fill_px
            updated_symbol_side_snapshot_obj.last_update_fill_qty = fills_journal.fill_qty
            updated_symbol_side_snapshot_obj.last_update_date_time = fills_journal.fill_date_time
            updated_symbol_side_snapshot_obj = \
                await underlying_partial_update_symbol_side_snapshot_http(updated_symbol_side_snapshot_obj)
            return updated_symbol_side_snapshot_obj
        else:
            err_str_ = f"SymbolSideSnapshot must be only one per symbol, recieved {len(symbol_side_snapshot_objs)}, " \
                       f"- {symbol_side_snapshot_objs}"
            await update_strat_alert_by_sec_and_side_async(order_snapshot_obj.order_brief.security.sec_id,
                                                           order_snapshot_obj.order_brief.side, err_str_)

    async def _update_order_snapshot_from_order_journal(self, order_journal_obj: OrderJournal):
        match order_journal_obj.order_event:
            case OrderEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_create_order_snapshot_http
                order_snapshot_obj = OrderSnapshot(_id=OrderSnapshot.next_id(),
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
                order_snapshot_obj = await underlying_create_order_snapshot_http(order_snapshot_obj)
                symbol_side_snapshot = \
                    await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                      order_snapshot_obj)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot_obj,
                                                                                    symbol_side_snapshot)
                    await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot_obj,
                                                                     updated_strat_brief)
                    await self._update_portfolio_status_from_order_journal(
                        order_journal_obj, order_snapshot_obj)
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already

            case OrderEventType.OE_ACK:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj,
                                                                       [OrderStatusType.OE_UNACK])
                if order_snapshot_obj is not None:
                    await underlying_partial_update_order_snapshot_http(
                        OrderSnapshotOptional(_id=order_snapshot_obj.id,
                                              last_update_date_time=order_journal_obj.order_event_date_time,
                                              order_status=OrderStatusType.OE_ACKED))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj, [OrderStatusType.OE_ACKED])
                if order_snapshot_obj is not None:
                    await underlying_partial_update_order_snapshot_http(
                        OrderSnapshotOptional(_id=order_snapshot_obj.id,
                                              last_update_date_time=order_journal_obj.order_event_date_time,
                                              order_status=OrderStatusType.OE_CXL_UNACK))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL_ACK:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_ACKED])
                if order_snapshot_obj is not None:
                    order_brief_obj = OrderBrief(**order_snapshot_obj.order_brief.dict())
                    if order_journal_obj.order.text:
                        order_brief_obj.text.extend(order_journal_obj.order.text)
                    # else not required: If no text is present in order_journal then updating
                    # order snapshot with same obj

                    cxled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                    cxled_notional = cxled_qty * order_snapshot_obj.order_brief.px
                    avg_cxled_px = (cxled_notional / cxled_qty) if cxled_qty != 0 else 0
                    order_snapshot_obj = await underlying_partial_update_order_snapshot_http(
                        OrderSnapshotOptional(_id=order_snapshot_obj.id,
                                              order_brief=order_brief_obj,
                                              cxled_qty=cxled_qty,
                                              cxled_notional=cxled_notional,
                                              avg_cxled_px=avg_cxled_px,
                                              last_update_date_time=order_journal_obj.order_event_date_time,
                                              order_status=OrderStatusType.OE_DOD))
                    symbol_side_snapshot = await self._create_update_symbol_side_snapshot_from_order_journal(
                        order_journal_obj, order_snapshot_obj)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot_obj,
                                                                                        symbol_side_snapshot)
                        await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot_obj,
                                                                         updated_strat_brief)
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot_obj)
                    # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                    # is None then it means some error occurred in
                    # _create_update_symbol_side_snapshot_from_order_journal which would have got added to alert already

                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_CXL_REJ:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = await self._check_state_and_get_order_snapshot_obj(
                    order_journal_obj, [OrderStatusType.OE_CXL_UNACK])
                if order_snapshot_obj is not None:
                    if order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty > 0:
                        order_status = OrderStatusType.OE_ACKED
                    elif order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty > 0:
                        order_status = OrderStatusType.OE_OVER_FILLED
                    else:
                        order_status = OrderStatusType.OE_FILLED
                    await underlying_partial_update_order_snapshot_http(
                        OrderSnapshotOptional(_id=order_snapshot_obj.id,
                                              last_update_date_time=order_journal_obj.order_event_date_time,
                                              order_status=order_status))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_REJ:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj, [OrderStatusType.OE_ACKED])

                if order_snapshot_obj is not None:
                    order_brief_obj = OrderBrief(**order_snapshot_obj.order_brief.dict())
                    order_brief_obj.text.extend(order_journal_obj.order.text)
                    cxled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                    cxled_notional = order_snapshot_obj.cxled_qty * order_snapshot_obj.order_brief.px
                    avg_cxled_px = (cxled_notional / cxled_qty) if cxled_qty != 0 else 0
                    order_snapshot_obj = await underlying_partial_update_order_snapshot_http(
                        OrderSnapshotOptional(
                            _id=order_snapshot_obj.id,
                            order_brief=order_brief_obj,
                            cxled_qty=cxled_qty,
                            cxled_notional=cxled_notional,
                            avg_cxled_px=avg_cxled_px,
                            last_update_date_time=order_journal_obj.order_event_date_time,
                            order_status=OrderStatusType.OE_DOD))
                    symbol_side_snapshot = \
                        await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                          order_snapshot_obj)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot_obj,
                                                                                        symbol_side_snapshot)
                        await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot_obj,
                                                                         updated_strat_brief)
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot_obj)
                    # else not require_create_update_symbol_side_snapshot_from_order_journald:
                    # if symbol_side_snapshot is None then it means some error occurred in
                    # _create_update_symbol_side_snapshot_from_order_journal which would have
                    # got added to alert already
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case other_:
                err_str_ = f"Unsupported Order event - {other_} in order_journal object - {order_journal_obj}"
                await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                               order_journal_obj.order.side, err_str_)

    async def _update_pair_strat_from_order_journal(self, order_journal_obj: OrderJournal,
                                                    order_snapshot: OrderSnapshot, strat_brief: StratBrief):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            partial_update_pair_strat_http
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
                                order_journal_obj.order.qty * order_snapshot.order_brief.px
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_buy_unfilled_qty = \
                                order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            updated_strat_status_obj.total_open_buy_qty -= total_buy_unfilled_qty
                            updated_strat_status_obj.total_open_buy_notional -= \
                                (total_buy_unfilled_qty * order_snapshot.order_brief.px)
                            updated_strat_status_obj.total_cxl_buy_qty += order_snapshot.cxled_qty
                            updated_strat_status_obj.total_cxl_buy_notional += \
                                order_snapshot.cxled_qty * order_snapshot.order_brief.px
                            updated_strat_status_obj.avg_cxl_buy_px = \
                                (
                                        updated_strat_status_obj.total_cxl_buy_notional / updated_strat_status_obj.total_cxl_buy_qty) \
                                    if updated_strat_status_obj.total_cxl_buy_qty != 0 else 0
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - updated_strat_status_obj.total_cxl_sell_notional
                        case other_:
                            err_str_ = f"Unsupported Order Event type {other_}"
                            await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                                           order_journal_obj.order.side, err_str_)
                            return
                    if updated_strat_status_obj.total_open_buy_qty == 0:
                        updated_strat_status_obj.avg_open_buy_px = 0
                    else:
                        updated_strat_status_obj.avg_open_buy_px = \
                            updated_strat_status_obj.total_open_buy_notional / updated_strat_status_obj.total_open_buy_qty
                case Side.SELL:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            updated_strat_status_obj.total_sell_qty += order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_sell_qty += order_journal_obj.order.qty
                            updated_strat_status_obj.total_open_sell_notional += \
                                order_journal_obj.order.qty * order_journal_obj.order.px
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_sell_unfilled_qty = \
                                order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            updated_strat_status_obj.total_open_sell_qty -= total_sell_unfilled_qty
                            updated_strat_status_obj.total_open_sell_notional -= \
                                (total_sell_unfilled_qty * order_snapshot.order_brief.px)
                            updated_strat_status_obj.total_cxl_sell_qty += order_snapshot.cxled_qty
                            updated_strat_status_obj.total_cxl_sell_notional += \
                                order_snapshot.cxled_qty * order_snapshot.order_brief.px
                            updated_strat_status_obj.avg_cxl_sell_px = \
                                (updated_strat_status_obj.total_cxl_sell_notional /
                                 updated_strat_status_obj.total_cxl_sell_qty) \
                                    if updated_strat_status_obj.total_cxl_sell_qty != 0 else 0
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - \
                                updated_strat_status_obj.total_cxl_sell_notional
                        case other_:
                            err_str_ = f"Unsupported Order Event type {other_}"
                            await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                                           order_journal_obj.order.side, err_str_)
                            return
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            updated_strat_status_obj.total_open_sell_notional / \
                            updated_strat_status_obj.total_open_sell_qty
                case other_:
                    err_str_ = f"Unsupported Side Type {other_} received in order journal {order_journal_obj} " \
                               f"while updating strat_status"
                    await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                                   order_journal_obj.order.side, err_str_)
                    return
            updated_strat_status_obj.total_order_qty = \
                updated_strat_status_obj.total_buy_qty + updated_strat_status_obj.total_sell_qty
            updated_strat_status_obj.total_open_exposure = \
                updated_strat_status_obj.total_open_buy_notional - updated_strat_status_obj.total_open_sell_notional
            if updated_strat_status_obj.total_fill_buy_notional < updated_strat_status_obj.total_fill_sell_notional:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_buy_notional
            else:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_sell_notional

            updated_residual = self.__get_residual_obj(order_snapshot, strat_brief)
            updated_strat_status_obj.residual = updated_residual

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_obj.id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            updated_pair_strat_obj.last_active_date_time = order_journal_obj.order_event_date_time
            updated_pair_strat_obj.frequency = pair_strat_obj.frequency + 1
            await partial_update_pair_strat_http(updated_pair_strat_obj)
        else:
            logging.error(f"error: received pair_strat for symbol:{order_journal_obj.order.security.sec_id} "
                          f"and side:{order_journal_obj.order.side} as None")
            return

    def __get_residual_obj(self, order_snapshot: OrderSnapshot, strat_brief: StratBrief) -> Residual | None:
        if order_snapshot.order_brief.side == Side.BUY:
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

        residual_notional = abs((residual_qty * top_of_book_obj.last_trade.px) -
                                (other_leg_residual_qty * other_leg_top_of_book.last_trade.px))
        if order_snapshot.order_brief.side == Side.BUY:
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
            # If residual is 0, setting residual field as None
            return

    async def _update_pair_strat_from_fill_journal(self, order_snapshot_obj: OrderSnapshot,
                                                   strat_brief_obj: StratBrief):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            partial_update_pair_strat_http
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
                        order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.order_brief.px
                    if updated_strat_status_obj.total_open_buy_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_buy_px = \
                            updated_strat_status_obj.total_open_buy_notional / updated_strat_status_obj.total_open_buy_qty
                    updated_strat_status_obj.total_fill_buy_qty += order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_fill_buy_notional += \
                        order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.last_update_fill_px
                    updated_strat_status_obj.avg_fill_buy_px = \
                        updated_strat_status_obj.total_fill_buy_notional / updated_strat_status_obj.total_fill_buy_qty
                case Side.SELL:
                    updated_strat_status_obj.total_open_sell_qty -= order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_open_sell_notional -= \
                        (order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.order_brief.px)
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            updated_strat_status_obj.total_open_sell_notional / updated_strat_status_obj.total_open_sell_qty
                    updated_strat_status_obj.total_fill_sell_qty += order_snapshot_obj.last_update_fill_qty
                    updated_strat_status_obj.total_fill_sell_notional += \
                        order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.last_update_fill_px
                    updated_strat_status_obj.avg_fill_sell_px = \
                        updated_strat_status_obj.total_fill_sell_notional / updated_strat_status_obj.total_fill_sell_qty
                case other_:
                    err_str_ = f"Unsupported Side Type {other_} received in order snapshot {order_snapshot_obj} " \
                               f"while updating strat_status"
                    await update_strat_alert_by_sec_and_side_async(order_snapshot_obj.order_brief.security.sec_id,
                                                                   order_snapshot_obj.order_brief.side, err_str_)
                    return
            updated_strat_status_obj.total_open_exposure = \
                updated_strat_status_obj.total_open_buy_notional - updated_strat_status_obj.total_open_sell_notional
            updated_strat_status_obj.total_fill_exposure = \
                updated_strat_status_obj.total_fill_buy_notional - updated_strat_status_obj.total_fill_sell_notional
            if updated_strat_status_obj.total_fill_buy_notional < updated_strat_status_obj.total_fill_sell_notional:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_buy_notional
            else:
                updated_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - updated_strat_status_obj.total_fill_sell_notional

            updated_residual = self.__get_residual_obj(order_snapshot_obj, strat_brief_obj)
            updated_strat_status_obj.residual = updated_residual

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_obj.id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            updated_pair_strat_obj.last_active_date_time = order_snapshot_obj.last_update_date_time
            updated_pair_strat_obj.frequency = pair_strat_obj.frequency + 1
            await partial_update_pair_strat_http(updated_pair_strat_obj)
        else:
            logging.error(f"error: received pair_strat for symbol:{order_snapshot_obj.order_brief.security.sec_id} "
                          f"and side:{order_snapshot_obj.order_brief.side} as None")
            return

    async def _get_max_order_counts(self, order_journal_obj: OrderJournal) -> int | None:  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_limits_by_id_http, underlying_get_last_n_sec_orders_by_event_query_http
        portfolio_limits_obj = await underlying_read_portfolio_limits_by_id_http(1)

        order_count_period_seconds = \
            portfolio_limits_obj.rolling_max_order_count.order_count_period_seconds
        max_order_count = portfolio_limits_obj.rolling_max_order_count.max_order_count

        order_counts_updated_order_journals = \
            await underlying_get_last_n_sec_orders_by_event_query_http(order_journal_obj.order.security.sec_id,
                                                                       order_count_period_seconds,
                                                                       OrderEventType.OE_NEW)

        for queried_order_journal in reversed(order_counts_updated_order_journals):
            if queried_order_journal.id == order_journal_obj.id:
                return max_order_count - queried_order_journal.current_period_order_count
        else:
            err_str_ = f"List of query received order_journals doesn't have current order_journal, " \
                       f"current order_journal {order_journal_obj}, list of received " \
                       f"order_journals {order_counts_updated_order_journals}"
            logging.error(err_str_)
            return

    async def _update_portfolio_status_from_order_journal(self, order_journal_obj: OrderJournal,
                                                          order_snapshot_obj: OrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_status_by_id_http, underlying_partial_update_portfolio_status_http

        portfolio_status_obj = await underlying_read_portfolio_status_by_id_http(1)

        match order_journal_obj.order.side:
            case Side.BUY:
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        if portfolio_status_obj.overall_buy_notional is None:
                            portfolio_status_obj.overall_buy_notional = 0
                        portfolio_status_obj.overall_buy_notional += \
                            order_journal_obj.order.px * order_journal_obj.order.qty
                        current_period_available_buy_order_count = \
                            await self._get_max_order_counts(order_journal_obj)
                        if current_period_available_buy_order_count is not None:
                            portfolio_status_obj.current_period_available_buy_order_count = \
                                current_period_available_buy_order_count
                        else:
                            logging.error("error: Couldn't update current_period_available_buy_order_count field "
                                          "of PortfolioStatus since something went wrong in _get_max_order_counts "
                                          "function call")

                    case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                        total_buy_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        portfolio_status_obj.overall_buy_notional -= \
                            (order_snapshot_obj.order_brief.px * total_buy_unfilled_qty)
            case Side.SELL:
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        if portfolio_status_obj.overall_sell_notional is None:
                            portfolio_status_obj.overall_sell_notional = 0
                        portfolio_status_obj.overall_sell_notional += \
                            order_journal_obj.order.px * order_journal_obj.order.qty
                        current_period_available_sell_order_count = \
                            await self._get_max_order_counts(order_journal_obj)
                        if current_period_available_sell_order_count is not None:
                            portfolio_status_obj.current_period_available_sell_order_count = \
                                current_period_available_sell_order_count
                        else:
                            logging.error("error: Couldn't update current_period_available_buy_order_count field "
                                          "of PortfolioStatus since something went wrong in _get_max_order_counts "
                                          "function call")
                    case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                        total_sell_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        portfolio_status_obj.overall_sell_notional -= \
                            (order_snapshot_obj.order_brief.px * total_sell_unfilled_qty)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order journal {order_journal_obj} " \
                           f"while updating strat_status"
                await update_strat_alert_by_sec_and_side_async(order_journal_obj.order.security.sec_id,
                                                               order_journal_obj.order.side, err_str_)
                return
        updated_portfolio_status = PortfolioStatusOptional(
            _id=portfolio_status_obj.id,
            overall_buy_notional=portfolio_status_obj.overall_buy_notional,
            overall_sell_notional=portfolio_status_obj.overall_sell_notional,
            current_period_available_buy_order_count=portfolio_status_obj.current_period_available_buy_order_count,
            current_period_available_sell_order_count=portfolio_status_obj.current_period_available_sell_order_count
        )
        await underlying_partial_update_portfolio_status_http(updated_portfolio_status)

    async def create_fills_journal_pre(self, fills_journal_obj: FillsJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            raise HTTPException(status_code=503, detail="create_order_journal_pre not ready - service is not "
                                                        "initialized yet")
        # Updating notional field in fills journal
        fills_journal_obj.fill_notional = fills_journal_obj.fill_px * fills_journal_obj.fill_qty

    async def create_fills_journal_post(self, fills_journal_obj: FillsJournal):
        with OrderSnapshot.reentrant_lock:
            with PairStrat.reentrant_lock:
                await self._update_fill_update_in_snapshot(fills_journal_obj)

    async def _update_portfolio_status_from_fill_journal(self, order_snapshot_obj: OrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_status_by_id_http, underlying_partial_update_portfolio_status_http

        portfolio_status_obj = await underlying_read_portfolio_status_by_id_http(1)
        match order_snapshot_obj.order_brief.side:
            case Side.BUY:
                if portfolio_status_obj.overall_buy_notional is None:
                    portfolio_status_obj.overall_buy_notional = 0
                portfolio_status_obj.overall_buy_notional += \
                    (order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.last_update_fill_px) - \
                    (order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.order_brief.px)
                portfolio_status_obj.overall_buy_fill_notional += \
                    order_snapshot_obj.last_update_fill_px * order_snapshot_obj.last_update_fill_qty
            case Side.SELL:
                if portfolio_status_obj.overall_sell_notional is None:
                    portfolio_status_obj.overall_sell_notional = 0
                portfolio_status_obj.overall_sell_notional += \
                    (order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.last_update_fill_px) - \
                    (order_snapshot_obj.last_update_fill_qty * order_snapshot_obj.order_brief.px)
                portfolio_status_obj.overall_sell_fill_notional += \
                    order_snapshot_obj.last_update_fill_px * order_snapshot_obj.last_update_fill_qty
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order snapshot {order_snapshot_obj} " \
                           f"while updating strat_status"
                await update_strat_alert_by_sec_and_side_async(order_snapshot_obj.order_brief.security.sec_id,
                                                               order_snapshot_obj.order_brief.side, err_str_)
                return
        updated_portfolio_status = PortfolioStatusOptional(
            _id=portfolio_status_obj.id,
            overall_buy_notional=portfolio_status_obj.overall_buy_notional,
            overall_buy_fill_notional=portfolio_status_obj.overall_buy_fill_notional,
            overall_sell_notional=portfolio_status_obj.overall_sell_notional,
            overall_sell_fill_notional=portfolio_status_obj.overall_sell_fill_notional
        )
        await underlying_partial_update_portfolio_status_http(updated_portfolio_status)

    async def _update_fill_update_in_snapshot(self, fills_journal_obj: FillsJournal):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_snapshot_http, underlying_partial_update_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(
                fills_journal_obj.order_id))
        if len(order_snapshot_objs) == 1:
            order_snapshot_obj = order_snapshot_objs[0]
            if order_snapshot_obj.order_status != OrderStatusType.OE_DOD:
                if (last_filled_qty := order_snapshot_obj.filled_qty) is not None:
                    updated_filled_qty = last_filled_qty + fills_journal_obj.fill_qty
                else:
                    updated_filled_qty = fills_journal_obj.fill_qty
                if (last_filled_notional := order_snapshot_obj.fill_notional) is not None:
                    updated_fill_notional = last_filled_notional + fills_journal_obj.fill_notional
                else:
                    updated_fill_notional = fills_journal_obj.fill_notional
                updated_avg_fill_px = updated_fill_notional / updated_filled_qty
                last_update_fill_qty = fills_journal_obj.fill_qty
                last_update_fill_px = fills_journal_obj.fill_px

                order_snapshot_obj = \
                    await underlying_partial_update_order_snapshot_http(OrderSnapshotOptional(
                        _id=order_snapshot_obj.id, filled_qty=updated_filled_qty, avg_fill_px=updated_avg_fill_px,
                        fill_notional=updated_fill_notional, last_update_fill_qty=last_update_fill_qty,
                        last_update_fill_px=last_update_fill_px,
                        last_update_date_time=fills_journal_obj.fill_date_time))
                symbol_side_snapshot = \
                    await self._update_symbol_side_snapshot_from_fills_journal(fills_journal_obj, order_snapshot_obj)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot_obj,
                                                                                    symbol_side_snapshot)
                    await self._update_pair_strat_from_fill_journal(order_snapshot_obj, updated_strat_brief)
                    await self._update_portfolio_status_from_fill_journal(order_snapshot_obj)
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already

            else:
                err_str_ = f"Fill received for snapshot having status OE_DOD - received: " \
                           f"fill_journal - {fills_journal_obj}, snapshot - {order_snapshot_obj}"
                await update_strat_alert_by_sec_and_side_async(order_snapshot_obj.order_brief.security.sec_id,
                                                               order_snapshot_obj.order_brief.side, err_str_)

        elif len(order_snapshot_objs) == 0:
            err_str_ = f"Could not find any order snapshot with order-id {fills_journal_obj.order_id} in " \
                       f"{order_snapshot_objs}"
            logging.exception(err_str_)
            raise Exception(err_str_)
        else:
            err_str_ = f"Match should return list of only one order_snapshot obj, " \
                       f"returned {order_snapshot_objs}"
            logging.exception(err_str_)
            raise Exception(err_str_)

    # Example: Soft API Query Interfaces

    async def get_symbol_side_snapshot_from_symbol_side_query_pre(self, symbol_side_snapshot_class_type: Type[
        SymbolSideSnapshot], security_id: str, side: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        return await underlying_read_symbol_side_snapshot_http(
            get_symbol_side_snapshot_from_symbol_side(security_id, side))

    # Code-generated
    async def get_pair_strat_sec_filter_json_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter
        return await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(security_id))

    def _set_new_strat_limit(self, pair_strat_obj: PairStrat) -> None:  # NOQA
        pair_strat_obj.strat_limits = get_new_strat_limits()

    def _set_derived_side(self, pair_strat_obj: PairStrat):  # NOQA
        raise_error = False
        if pair_strat_obj.pair_strat_params.strat_leg2.side is None:
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

    def _set_derived_exchange(self, pair_strat_obj: PairStrat):  # NOQA
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
    async def _add_pair_strat_status(self, pair_strat_obj: PairStrat):
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
                                                      total_cxl_exposure=0.0, average_premium=0.0, balance_notional=0.0)
        else:
            err_str_ = f"_add_pair_strat_status called with unexpected pre-set strat_status: {pair_strat_obj}"
            await update_strat_alert_by_sec_and_side_async(pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                                                           pair_strat_obj.pair_strat_params.strat_leg1.side, err_str_)

    @except_n_log_alert(severity=Severity.Severity_ERROR)
    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            raise HTTPException(status_code=503, detail="create_pair_strat_pre not ready - service is not "
                                                        "initialized yet")
        # expectation: no strat limit or status is set while creating a strat, this call creates these
        if pair_strat_obj.strat_status is not None:
            raise Exception("error: create_pair_strat_pre called with pre-set strat_status, "
                            f"pair_strat_obj: {pair_strat_obj}")
        if pair_strat_obj.strat_limits is not None:
            raise Exception(
                f"error: create_pair_strat_pre called with pre-set strat_limits, pair_strat_obj{pair_strat_obj}")
        await self._add_pair_strat_status(pair_strat_obj)
        self._set_new_strat_limit(pair_strat_obj)
        self._set_derived_side(pair_strat_obj)
        self._set_derived_exchange(pair_strat_obj)
        # get security name from : pair_strat_params.strat_legs and then redact pattern
        # security.sec_id (a pattern in positions) where there is a value match
        dismiss_filter_agg_pipeline = {'redact': [("pos_disable", False), ("br_disable", False),
                                                  ("security.sec_id",
                                                   pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                                                   pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id)]}
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_limits_http

        filtered_portfolio_limits: List[PortfolioLimits] = await underlying_read_portfolio_limits_http(
            dismiss_filter_agg_pipeline)
        if len(filtered_portfolio_limits) == 1:
            pair_strat_obj.strat_limits.eligible_brokers = [eligible_broker for eligible_broker in
                                                            filtered_portfolio_limits[0].eligible_brokers if
                                                            len(eligible_broker.sec_positions) != 0]
        elif len(filtered_portfolio_limits) > 1:
            raise Exception(f"filtered_portfolio_limits expected: 1, found: {str(len(filtered_portfolio_limits))}, for "
                            f"filter: {dismiss_filter_agg_pipeline}, filtered_portfolio_limits: "
                            f"{filtered_portfolio_limits}; "
                            "use SWAGGER UI to check / fix and re-try")
        else:
            logging.warning(f"No filtered_portfolio_limits found for pair-strat: {pair_strat_obj}")
        pair_strat_obj.frequency = 1
        pair_strat_obj.last_active_date_time = DateTime.utcnow()

    @except_n_log_alert(severity=Severity.Severity_ERROR)
    async def create_pair_strat_post(self, pair_strat_obj: PairStrat):
        # creating strat_brief for both leg securities
        await self._create_strat_brief_from_pair_strat_pre(pair_strat_obj)
        # creating symbol_side_snapshot for both leg securities if not already exists
        await self._create_symbol_snapshot_if_not_exists_from_pair_strat_pre(pair_strat_obj)

    async def _create_strat_brief_from_pair_strat_pre(self, pair_strat_obj: PairStrat):  # NOQA
        sec1_pair_side_trading_brief_obj = \
            PairSideTradingBrief(security=pair_strat_obj.pair_strat_params.strat_leg1.sec,
                                 side=pair_strat_obj.pair_strat_params.strat_leg1.side,
                                 last_update_date_time=DateTime.utcnow(),
                                 consumable_open_orders=0.0, consumable_notional=0.0, consumable_open_notional=0.0,
                                 consumable_concentration=0.0, participation_period_order_qty_sum=0.0,
                                 consumable_cxl_qty=0.0, indicative_consumable_participation_qty=0.0,
                                 residual_qty=0.0, indicative_consumable_residual=0.0, all_bkr_cxlled_qty=0.0,
                                 open_notional=0.0, open_qty=0.0)
        sec2_pair_side_trading_brief_obj = \
            PairSideTradingBrief(security=pair_strat_obj.pair_strat_params.strat_leg2.sec,
                                 side=pair_strat_obj.pair_strat_params.strat_leg2.side,
                                 last_update_date_time=DateTime.utcnow(),
                                 consumable_open_orders=0.0, consumable_notional=0.0, consumable_open_notional=0.0,
                                 consumable_concentration=0.0, participation_period_order_qty_sum=0.0,
                                 consumable_cxl_qty=0.0, indicative_consumable_participation_qty=0.0,
                                 residual_qty=0.0, indicative_consumable_residual=0.0, all_bkr_cxlled_qty=0.0,
                                 open_notional=0.0, open_qty=0.0)

        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_create_strat_brief_http
        strat_brief_obj: StratBrief = StratBrief(_id=StratBrief.next_id(),
                                                 pair_buy_side_trading_brief=sec1_pair_side_trading_brief_obj,
                                                 pair_sell_side_trading_brief=sec2_pair_side_trading_brief_obj,
                                                 consumable_nett_filled_notional=0.0)
        created_underlying_strat_brief = await underlying_create_strat_brief_http(strat_brief_obj)
        logging.debug(f"Created strat brief {created_underlying_strat_brief} in pre call of pair_strat of "
                      f"obj {pair_strat_obj}")

    async def _create_symbol_snapshot_if_not_exists_from_pair_strat_pre(self, pair_strat_obj: PairStrat):  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        pair_symbol_side_list = [
            (pair_strat_obj.pair_strat_params.strat_leg1.sec, pair_strat_obj.pair_strat_params.strat_leg1.side),
            (pair_strat_obj.pair_strat_params.strat_leg2.sec, pair_strat_obj.pair_strat_params.strat_leg2.side)
        ]

        for security, side in pair_symbol_side_list:
            symbol_side_snapshots = \
                await underlying_read_symbol_side_snapshot_http(
                    get_symbol_side_snapshot_from_symbol_side(security.sec_id, side))

            if len(symbol_side_snapshots) == 0:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_create_symbol_side_snapshot_http
                symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(),
                                                              security=security,
                                                              side=side, avg_px=0, total_qty=0,
                                                              total_filled_qty=0, avg_fill_px=0.0,
                                                              total_fill_notional=0.0, last_update_fill_qty=0,
                                                              last_update_fill_px=0, total_cxled_qty=0, avg_cxled_px=0,
                                                              total_cxled_notional=0,
                                                              last_update_date_time=DateTime.utcnow(),
                                                              order_create_count=0)
                created_symbol_side_snapshot = \
                    await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
                logging.debug(f"Created SymbolSideSnapshot {created_symbol_side_snapshot} for security {security} and "
                              f"side {side} in pre call of pair_strat {pair_strat_obj}")

            elif len(symbol_side_snapshots) == 1:
                # Symbol and side snapshot already exists
                pass
            else:
                err_str_ = f"SymbolSideSnapshot must be one per symbol and side, received {symbol_side_snapshots} for " \
                           f"security {security} and side {side}"
                await update_strat_alert_by_sec_and_side_async(security.sec_id, side, err_str_)
    async def _update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat,
                                     updated_pair_strat_obj: PairStrat) -> bool | None:
        """
        Return true if object further updated false otherwise
        """
        is_updated = False
        if updated_pair_strat_obj.strat_status is None:
            err_str_ = f"_update_pair_strat_pre called with NO set strat_status: {updated_pair_strat_obj}"
            await update_strat_alert_by_sec_and_side_async(
                stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                stored_pair_strat_obj.pair_strat_params.strat_leg1.side, err_str_)
            return
        if updated_pair_strat_obj.strat_status.strat_state == StratState.StratState_ACTIVE:
            strat_alerts = self._apply_checks_n_alert(updated_pair_strat_obj)
            if len(strat_alerts) != 0:
                # some check is violated, move strat to error
                updated_pair_strat_obj.strat_status.strat_state = StratState.StratState_ERROR
                if updated_pair_strat_obj.strat_status.strat_alerts is None:
                    updated_pair_strat_obj.strat_status.strat_alerts = strat_alerts
                else:
                    updated_pair_strat_obj.strat_status.strat_alerts += strat_alerts
                is_updated = True
            # else not required - no alerts - all checks passed
            if stored_pair_strat_obj.strat_status.strat_state != StratState.StratState_ACTIVE:
                dict_dirty: bool = False
                with self.active_ticker_pair_strat_id_dict_lock:
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
                                               self.pair_strat_id_n_today_activated_tickers_dict, PROJECT_DATA_DIR)
            # else not required: pair_strat_id_n_today_activated_tickers_dict is updated only if we activate a new strat
        return is_updated

    async def update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            raise HTTPException(status_code=503, detail="update_pair_strat_pre not ready - service is not "
                                                        "initialized yet")

        updated_pair_strat_obj.frequency += 1
        await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()
        logging.debug(f"further updated by _update_pair_strat_pre: {updated_pair_strat_obj}")

    async def get_order_of_matching_suffix_order_id(self, order_id: str) -> str | None:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_of_matching_suffix_order_id_filter
        stored_order_list: List[OrderJournal] = await underlying_read_order_journal_http(
            get_order_of_matching_suffix_order_id_filter(order_id))
        if len(stored_order_list) > 0:
            return stored_order_list[0].order.order_id
        else:
            return None

    async def _get_order_limits(self) -> OrderLimits:  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_limits_http
        order_limits_objs: List[OrderLimits] = await underlying_read_order_limits_http()

        if len(order_limits_objs) == 1:
            return order_limits_objs[0]
        else:
            err_str_ = f"OrderLimits must always have only one stored document, received: {len(order_limits_objs)} ;;; " \
                       f"{order_limits_objs}"
            logging.exception(err_str_)
            raise Exception(err_str_)

    async def _get_pair_strat_from_symbol(self, symbol: str) -> PairStrat:  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter

        pair_strat_objs_list = await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter(symbol))
        if len(pair_strat_objs_list) == 1:
            return pair_strat_objs_list[0]
        else:
            err_str_: str = f"PairStrat should be one document per symbol, received {(len(pair_strat_objs_list))};;;" \
                            f"{pair_strat_objs_list}"
            logging.exception(err_str_)
            raise Exception(err_str_)

    def _get_top_of_book_from_symbol(self, symbol: str):
        top_of_book_list: List[TopOfBookBaseModel] = market_data_service_web_client.get_top_of_book_from_index_client(
            symbol)
        if len(top_of_book_list) != 1:
            err_str_ = f"TopOfBook should be one per symbol received {len(top_of_book_list)} - {top_of_book_list}"
            logging.exception(err_str_)
            raise Exception(err_str_)
        else:
            return top_of_book_list[0]

    async def _get_participation_period_order_qty_sum(self, symbol: str, strat_limits_obj: StratLimits,  # NOQA
                                                      symbol_side_snapshot: SymbolSideSnapshot) -> int:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_total_sum_of_last_n_sec

        sum_period = strat_limits_obj.market_trade_volume_participation.applicable_period_seconds
        if sum_period == 0:
            return symbol_side_snapshot.total_qty
        else:
            agg_objs = \
                await underlying_read_order_snapshot_http(get_order_total_sum_of_last_n_sec(symbol, sum_period))

            if len(agg_objs) > 0:
                return agg_objs[-1].last_n_sec_total_qty
            else:
                err_str_ = "received empty aggregated list of objects from aggregation on OrderSnapshot to " \
                           f"get last {sum_period} sec total order sum"
                await update_strat_alert_by_sec_and_side_async(symbol, symbol_side_snapshot.side, err_str_)

    def _get_participation_period_last_trade_qty_sum(self, top_of_book: TopOfBookBaseModel,  # NOQA
                                                     applicable_period_seconds: int):
        market_trade_volume_list = top_of_book.market_trade_volume

        for market_trade_volume in market_trade_volume_list:
            if market_trade_volume.applicable_period_seconds == applicable_period_seconds:
                return market_trade_volume.participation_period_last_trade_qty_sum
        else:
            err_str_ = f"Couldn't find any match of applicable_period_seconds param {applicable_period_seconds} in" \
                       f"list of market_trade_volume in TopOfBook - {top_of_book}"
            logging.exception(err_str_)
            raise Exception(err_str_)

    async def _update_strat_brief_from_order(self, order_snapshot: OrderSnapshot,
                                             symbol_side_snapshot: SymbolSideSnapshot) -> StratBrief | None:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_strat_brief_http, underlying_partial_update_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol

        security = symbol_side_snapshot.security
        side = symbol_side_snapshot.side
        symbol = security.sec_id
        strat_brief_objs = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol))
        if len(strat_brief_objs) == 1:
            strat_brief_obj = strat_brief_objs[0]
            pair_strat_obj: PairStrat = await get_single_exact_match_ongoing_strat_from_symbol_n_side(symbol, side)
            if pair_strat_obj is not None:
                open_qty = (symbol_side_snapshot.total_qty -
                            (symbol_side_snapshot.total_filled_qty + symbol_side_snapshot.total_cxled_qty))
                open_notional = open_qty * order_snapshot.order_brief.px
                consumable_notional = \
                    pair_strat_obj.strat_limits.max_cb_notional - symbol_side_snapshot.total_fill_notional - \
                    open_notional
                consumable_open_notional = \
                    pair_strat_obj.strat_limits.max_open_cb_notional - open_notional
                top_of_book_obj = self._get_top_of_book_from_symbol(symbol)
                consumable_concentration = \
                    ((
                             top_of_book_obj.total_trading_security_size / 100) * pair_strat_obj.strat_limits.max_concentration) - \
                    open_notional - symbol_side_snapshot.total_fill_notional
                consumable_open_orders = \
                    pair_strat_obj.strat_limits.max_open_orders_per_side - open_qty
                consumable_cxl_qty = (((symbol_side_snapshot.total_filled_qty + open_qty +
                                        symbol_side_snapshot.total_cxled_qty) / 100) *
                                      pair_strat_obj.strat_limits.cancel_rate.max_cancel_rate) - \
                                     symbol_side_snapshot.total_cxled_qty
                participation_period_order_qty_sum = \
                    await self._get_participation_period_order_qty_sum(symbol, pair_strat_obj.strat_limits,
                                                                       symbol_side_snapshot)
                applicable_period_second = pair_strat_obj.strat_limits.market_trade_volume_participation.applicable_period_seconds
                participation_period_last_trade_qty_sum = \
                    self._get_participation_period_last_trade_qty_sum(top_of_book_obj, applicable_period_second)
                max_participation_rate = pair_strat_obj.strat_limits.market_trade_volume_participation.max_participation_rate
                indicative_consumable_participation_qty = ((participation_period_last_trade_qty_sum / 100) *
                                                           max_participation_rate) - participation_period_order_qty_sum

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

                if symbol == strat_brief_obj.pair_buy_side_trading_brief.security.sec_id:
                    updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                             pair_buy_side_trading_brief=updated_pair_side_brief_obj)
                elif symbol == strat_brief_obj.pair_sell_side_trading_brief.security.sec_id:
                    updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                             pair_sell_side_trading_brief=updated_pair_side_brief_obj)
                else:
                    err_str_ = f"error: None of the 2 pair_side_trading_brief(s) contain symbol: {symbol} in " \
                               f"strat_brief: {strat_brief_obj}"
                    logging.exception(err_str_)
                    raise Exception(err_str_)

                updated_strat_brief = await underlying_partial_update_strat_brief_http(updated_strat_brief)
                return updated_strat_brief
            else:
                logging.error(f"error: received pair_strat for symbol:{symbol} and side:{side} as None")
                return

        else:
            err_str_ = f"StratBrief must be one per symbol, " \
                       f"received {len(strat_brief_objs)} for symbol {symbol};;;StratBriefs: {strat_brief_objs}"
            logging.exception(err_str_)
            raise Exception(err_str_)

    async def get_strat_brief_from_symbol_query_pre(self, strat_brief_class_type: Type[StratBrief], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol
        return await underlying_read_strat_brief_http(get_strat_brief_from_symbol(security_id))

    async def get_open_order_snapshots_by_order_status_query_pre(self, order_snapshot_class_type: Type[OrderSnapshot],
                                                                 order_status: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_open_order_snapshots_by_order_status
        return await underlying_read_order_snapshot_http(get_open_order_snapshots_by_order_status(order_status))

    async def get_open_order_snapshots_by_order_status_query_post(self, order_snapshot_obj_list_: List[OrderSnapshot]):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_snapshot_http, underlying_partial_update_portfolio_status_http, \
            underlying_read_portfolio_limits_by_id_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_last_n_sec_orders_by_event

        # 1. cancel any expired from passed open orders
        await self.cxl_expired_open_orders(order_snapshot_obj_list_)

        # 2. If specified interval rejected orders count exceed threshold - trigger kill switch
        # get limit from portfolio limits
        portfolio_limits_obj: PortfolioLimits = await underlying_read_portfolio_limits_by_id_http(1)
        max_allowed_rejection_within_period = portfolio_limits_obj.rolling_max_reject_count.max_order_count
        period_in_sec = portfolio_limits_obj.rolling_max_reject_count.order_count_period_seconds
        ack_order_snapshot_obj_list: List[OrderSnapshot] = \
            await underlying_read_order_snapshot_http(get_last_n_sec_orders_by_event(None, period_in_sec, "OE_REJ"))
        if len(ack_order_snapshot_obj_list) > max_allowed_rejection_within_period:
            logging.debug(f"max_allowed_rejection_within_period breached found : {len(ack_order_snapshot_obj_list)} "
                          f"rejections in past period - initiating auto-kill switch")
            # single top level objects are hardcoded id=1 , saves the query portfolio status, if always id=1
            portfolio_status: PortfolioStatusOptional = PortfolioStatusOptional(id=1,
                                                                                kill_switch=True)
            await underlying_partial_update_portfolio_status_http(portfolio_status)
        # else not required -

        # 3. No one expects anything useful to be returned - just return empty list
        return []

    async def cxl_expired_open_orders(self, order_snapshot_obj_list: List[OrderSnapshot]):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
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
                                                        side=order_snapshot.order_brief.side)
                # trigger cancel if it does not already exist for this order id, otherwise log for alert
                from Flux.CodeGenProjects.addressbook.app.aggregate import get_cancel_order_by_order_id_filter
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_read_cancel_order_http
                cxl_order_list: List[CancelOrder] | None = await underlying_read_cancel_order_http(
                    get_cancel_order_by_order_id_filter(cancel_order.order_id))
                if cxl_order_list is None or len(cxl_order_list) == 0:
                    await underlying_create_cancel_order_http(cancel_order)
                else:
                    logging.error(f"cxl_expired_open_orders failed: Prior cxl request found in DB for this order-id: "
                                  f"{cancel_order.order_id}, use swagger to delete this order-id form DB to trigger "
                                  f"cxl request again;;;order_snapshot: {order_snapshot}")
            # else not required: If pair_strat_obj is None or If time-delta is still less than
            # residual_mark_seconds then avoiding cancellation of order

    async def get_last_n_sec_orders_by_event_query_pre(self, order_journal_class_type: Type[OrderJournal],
                                                       symbol: str | None, last_n_sec: int, order_event: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_last_n_sec_orders_by_event
        return await underlying_read_order_journal_http(get_last_n_sec_orders_by_event(symbol, last_n_sec, order_event))

    async def get_ongoing_strats_query_pre(self, ongoing_strat_symbols_class_type: Type[OngoingStratSymbols]):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter

        pair_strat_list: List[PairStrat] = await underlying_read_pair_strat_http(get_ongoing_pair_strat_filter())
        ongoing_symbols: Set[str] = set()

        for pair_strat in pair_strat_list:
            buy_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            sell_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            ongoing_symbols.add(buy_symbol)
            ongoing_symbols.add(sell_symbol)

        ongoing_strat_symbols = OngoingStratSymbols(symbols=list(ongoing_symbols))
        return [ongoing_strat_symbols]

    @staticmethod
    def get_id_from_strat_key(unloaded_strat_key: str) -> int:
        parts: List[str] = (unloaded_strat_key.split("_"))
        return int(parts[-1])

    async def update_strat_collection_pre(self, stored_strat_collection_obj: StratCollection,
                                          updated_strat_collection_obj: StratCollection):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_by_id_http
        updated_strat_collection_loaded_strat_keys_frozenset = frozenset(updated_strat_collection_obj.loaded_strat_keys)
        stored_strat_collection_loaded_strat_keys_frozenset = frozenset(stored_strat_collection_obj.loaded_strat_keys)
        # existing items in stored loaded frozenset but not in the updated stored frozen set need to move to done state
        unloaded_strat_keys_frozenset = stored_strat_collection_loaded_strat_keys_frozenset.difference(
            updated_strat_collection_loaded_strat_keys_frozenset)
        if len(unloaded_strat_keys_frozenset) != 0:
            unloaded_strat_key: str
            for unloaded_strat_key in unloaded_strat_keys_frozenset:
                pair_strat_id: int = self.get_id_from_strat_key(unloaded_strat_key)
                pair_strat = await underlying_read_pair_strat_by_id_http(pair_strat_id)
                if is_ongoing_pair_strat(pair_strat):
                    error_str = f"unloading and ongoing pair strat key: {unloaded_strat_key} is not supported, " \
                                f"current strat status: {pair_strat.strat_status.strat_state}"
                    logging.error(error_str)
                    raise HTTPException(status_code=503, detail=error_str)
