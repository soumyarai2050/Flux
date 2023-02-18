# system imports
import time
from typing import List, Type, Dict
import threading
from pathlib import PurePath
from datetime import date
import logging

# third-party package imports
from pendulum import DateTime
from pydantic import BaseModel
from fastapi import HTTPException

# project imports
from FluxPythonUtils.scripts.utility_functions import avg_of_new_val_sum_to_avg, store_json_or_dict_to_file, \
    load_json_dict_from_file, load_yaml_configurations
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import \
    OrderJournal, OrderSnapshot, OrderSnapshotOptional, PairStrat, FillsJournal, Alert, Severity, \
    PairStratOptional, StratStatus, PortfolioLimits, StratState, \
    StratLimits, Side, OrderEventType, PortfolioStatusOptional, OrderStatusType, SymbolSideSnapshot, \
    SymbolSideSnapshotOptional, OrderLimits, PairSideTradingBrief, StratBriefOptional, StratBrief, \
    PortfolioStatus, CancelRate, MarketTradeVolumeParticipation, OpenInterestParticipation, ResidualRestriction, \
    Residual, OrderBrief
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import TopOfBook
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import is_service_up, \
    get_portfolio_limits, create_portfolio_limits, get_order_limits, create_order_limits, except_n_log_alert, \
    create_alert, update_strat_status_lock

PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

market_data_service_web_client = MarketDataServiceWebClient(port=8040)


class ServiceState(BaseModel):
    ready: bool = False
    last_exception: Exception | None = None
    error_prefix: str = ""
    first_error_time: DateTime | None = None

    class Config:
        arbitrary_types_allowed = True

    def record_error(self, e: Exception) -> int:
        """
        returns time in seconds since first error if error is repeated, 0 otherwise
        if new error - record error in last error and update first error time with
        """
        if self.last_exception == e:
            return self.first_error_time.diff(DateTime.utcnow()).in_seconds()
        else:
            self.last_exception = e
            self.first_error_time = DateTime.utcnow()
            return 0

    def handle_exception(self, e: Exception):
        error_str: str = f"{self.error_prefix}{e}"
        logging.error(error_str, exc_info=True)
        if (last_error_interval_in_sec := self.record_error(e)) == 0:
            # raise alert
            pass
        elif last_error_interval_in_sec > (60 * 5):
            # it's been 5 minutes the error is still not resolved - re-alert
            pass


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

    def _app_launch_pre_thread_func(self):
        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")

        while True:
            time.sleep(self.min_refresh_interval)
            if not self.service_ready:
                if is_service_up():
                    if (order_limits := get_order_limits()) is None:
                        order_limits = create_order_limits()
                    if (portfolio_limits := get_portfolio_limits()) is None:
                        portfolio_limits = create_portfolio_limits()
                    self.service_ready = True
            else:
                # any periodic refresh code goes here - for now we can just return
                return

    # Example 0 of 5: pre- and post-launch server
    def app_launch_pre(self):
        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    async def create_order_journal_pre(self, order_journal_obj: OrderJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            raise HTTPException(status_code=503, detail="create_order_journal_pre not ready - service is not "
                                                        "initialized yet")
        # updating order notional in order journal obj
        order_journal_obj.order.order_notional = order_journal_obj.order.px * order_journal_obj.order.qty

    async def create_order_journal_post(self, order_journal_obj: OrderJournal):
        with OrderSnapshot.reentrant_lock:
            with PairStrat.reentrant_lock:
                await self._update_order_snapshot_from_order_journal(order_journal_obj)

    async def _check_state_and_get_order_snapshot_obj(self, order_journal_obj: OrderJournal,  # NOQA
                                                      expected_status_list: List[str],
                                                      received_journal_event: str) -> OrderSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_order_snapshot_order_id_filter_json
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(
                order_journal_obj.order.order_id))
        if len(order_snapshot_objs) == 1:
            order_snapshot_obj = order_snapshot_objs[0]
            if order_snapshot_obj.order_status in expected_status_list:
                return order_snapshot_obj
            else:
                err_str = f"order_journal - {order_journal_obj} received to update status of " \
                          f"order_snapshot - {order_snapshot_obj}, but order_snapshot " \
                          f"doesn't contain any order_status of list {expected_status_list}"
                await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                              order_journal_obj.order.side, err_str)
        elif len(order_snapshot_objs) == 0:
            err_str = f"Could not find any order for {received_journal_event} status - {order_journal_obj}"
            await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                          order_journal_obj.order.side, err_str)
        else:
            err_str = f"Match should return list of only one order_snapshot obj per order_id, " \
                      f"returned {order_snapshot_objs}"
            await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                          order_journal_obj.order.side, err_str)

    async def _create_update_symbol_side_snapshot_from_order_journal(self, order_journal_obj: OrderJournal,  # NOQA
                                                                     order_snapshot_obj: OrderSnapshot
                                                                     ) -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http, underlying_create_symbol_side_snapshot_http, \
            underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(order_journal_obj.order.security.sec_id,
                                                          order_journal_obj.order.side))

        if len(symbol_side_snapshot_objs) == 0:
            if order_journal_obj.order_event == OrderEventType.OE_NEW:
                security = order_journal_obj.order.security
                side = order_journal_obj.order.side
                symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(), security=security,
                                                              side=side,
                                                              avg_px=order_journal_obj.order.px,
                                                              total_qty=order_journal_obj.order.qty,
                                                              total_filled_qty=0, avg_fill_px=0,
                                                              total_fill_notional=0, last_update_fill_qty=0,
                                                              last_update_fill_px=0, total_cxled_qty=0,
                                                              avg_cxled_px=0, total_cxled_notional=0,
                                                              last_update_date_time=DateTime.utcnow(),
                                                              frequency=1
                                                              )
                symbol_side_snapshot_obj = \
                    await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
                return symbol_side_snapshot_obj
            else:
                err_str = "Can't handle order_journal event if not OE_NEW to create symbol_side_snapshot"
                await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                              order_journal_obj.order.side, err_str)
        elif len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            match order_journal_obj.order_event:
                case OrderEventType.OE_NEW:
                    updated_symbol_side_snapshot_obj.frequency = symbol_side_snapshot_obj.frequency + 1
                    updated_symbol_side_snapshot_obj.avg_px = \
                        avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                  order_journal_obj.order.px,
                                                  updated_symbol_side_snapshot_obj.frequency
                                                  )
                    updated_symbol_side_snapshot_obj.total_qty = symbol_side_snapshot_obj.total_qty + order_journal_obj.order.qty
                    updated_symbol_side_snapshot_obj.last_update_date_time = DateTime.utcnow()
                case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                    updated_symbol_side_snapshot_obj.total_cxled_qty = symbol_side_snapshot_obj.total_cxled_qty + order_snapshot_obj.cxled_qty
                    updated_symbol_side_snapshot_obj.total_cxled_notional = symbol_side_snapshot_obj.total_cxled_notional + order_snapshot_obj.cxled_notional
                    updated_symbol_side_snapshot_obj.avg_cxled_px = \
                        updated_symbol_side_snapshot_obj.total_cxled_notional / \
                        updated_symbol_side_snapshot_obj.total_cxled_qty
                    updated_symbol_side_snapshot_obj.last_update_date_time = DateTime.utcnow()
                case other:
                    err_str = f"Unsupported StratEventType for symbol_side_snapshot update {other}"
                    await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                                  order_journal_obj.order.side, err_str)
            updated_symbol_side_snapshot_obj = \
                await underlying_partial_update_symbol_side_snapshot_http(updated_symbol_side_snapshot_obj)
            return updated_symbol_side_snapshot_obj
        else:
            err_str = "SymbolSideSnapshot can't be multiple for single symbol and side combination, " \
                      f"received {len(symbol_side_snapshot_objs)} - {symbol_side_snapshot_objs}"
            await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                          order_journal_obj.order.side, err_str)

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
            updated_symbol_side_snapshot_obj.last_update_date_time = DateTime.utcnow()
            updated_symbol_side_snapshot_obj = \
                await underlying_partial_update_symbol_side_snapshot_http(updated_symbol_side_snapshot_obj)
            return updated_symbol_side_snapshot_obj
        else:
            err_str = f"SymbolSideSnapshot must be only one per symbol, recieved {len(symbol_side_snapshot_objs)}, " \
                      f"- {symbol_side_snapshot_objs}"
            await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                          order_snapshot_obj.order_brief.side, err_str)

    async def _update_order_snapshot_from_order_journal(self, order_journal_obj: OrderJournal):
        match order_journal_obj.order_event:
            case OrderEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    create_order_snapshot_http
                order_snapshot_obj = OrderSnapshot(_id=OrderSnapshot.next_id(),
                                                   order_brief=order_journal_obj.order,
                                                   filled_qty=0, avg_fill_px=0,
                                                   fill_notional=0,
                                                   cxled_qty=0,
                                                   avg_cxled_px=0,
                                                   cxled_notional=0,
                                                   last_update_fill_qty=0,
                                                   last_update_fill_px=0,
                                                   last_update_date_time=
                                                   order_journal_obj.order_event_date_time,
                                                   order_status=OrderStatusType.OE_UNACK)
                order_snapshot_obj = await create_order_snapshot_http(order_snapshot_obj)
                symbol_side_snapshot = \
                    await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                      order_snapshot_obj)
                await self._update_pair_strat_from_order_journal(order_journal_obj, order_snapshot_obj)
                await self._update_portfolio_status_from_order_journal(
                    order_journal_obj, order_snapshot_obj)
                await self._update_strat_brief_from_order(order_snapshot_obj, symbol_side_snapshot)

            case OrderEventType.OE_ACK:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj,
                                                                       [OrderStatusType.OE_UNACK],
                                                                       OrderEventType.OE_ACK)
                await underlying_partial_update_order_snapshot_http(
                    OrderSnapshotOptional(_id=order_snapshot_obj.id,
                                          last_update_date_time=order_journal_obj.order_event_date_time,
                                          order_status=OrderStatusType.OE_ACKED))
            case OrderEventType.OE_CXL:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_ACKED], OrderEventType.OE_CXL)
                await underlying_partial_update_order_snapshot_http(
                    OrderSnapshotOptional(_id=order_snapshot_obj.id,
                                          last_update_date_time=order_journal_obj.order_event_date_time,
                                          order_status=OrderStatusType.OE_CXL_UNACK))
            case OrderEventType.OE_CXL_ACK:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_ACKED],
                        OrderEventType.OE_CXL_ACK)
                order_brief_obj = OrderBrief(**order_snapshot_obj.order_brief.dict())
                if order_journal_obj.order.text:
                    order_brief_obj.text.extend(order_journal_obj.order.text)
                # else not required: If no text is present in order_journal then updating
                # order snapshot with same obj

                cxled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                cxled_notional = cxled_qty * order_snapshot_obj.order_brief.px
                avg_cxled_px = cxled_notional / cxled_qty
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
                await self._update_pair_strat_from_order_journal(
                    order_journal_obj, order_snapshot_obj)
                await self._update_portfolio_status_from_order_journal(
                    order_journal_obj, order_snapshot_obj)
                await self._update_strat_brief_from_order(order_snapshot_obj, symbol_side_snapshot)

            case OrderEventType.OE_CXL_REJ:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = await self._check_state_and_get_order_snapshot_obj(
                    order_journal_obj, [OrderStatusType.OE_CXL_UNACK], OrderEventType.OE_CXL_REJ)
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
            case OrderEventType.OE_REJ:
                from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot_obj = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_ACKED], OrderEventType.OE_REJ)
                order_brief_obj = OrderBrief(**order_snapshot_obj.order_brief.dict())
                order_brief_obj.text.extend(order_journal_obj.order.text)
                cxled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                cxled_notional = order_snapshot_obj.cxled_qty * order_snapshot_obj.order_brief.px
                avg_cxled_px = cxled_notional / cxled_qty
                order_snapshot_obj = await underlying_partial_update_order_snapshot_http(
                    OrderSnapshotOptional(
                        _id=order_snapshot_obj.id,
                        order_brief=order_brief_obj,
                        cxled_qty=cxled_qty,
                        cxled_notional=cxled_notional,
                        avg_cxled_px=avg_cxled_px,
                        last_update_date_time=order_journal_obj.order_event_date_time,
                        order_status=OrderStatusType.OE_DOD))
                await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj, order_snapshot_obj)
                symbol_side_snapshot = await self._update_pair_strat_from_order_journal(
                    order_journal_obj, order_snapshot_obj)
                await self._update_portfolio_status_from_order_journal(
                    order_journal_obj, order_snapshot_obj)
                await self._update_strat_brief_from_order(order_snapshot_obj, symbol_side_snapshot)

            case other:
                err_str = f"Unsupported Order event - {other} in order_journal object - {order_journal_obj}"
                await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                              order_journal_obj.order.side, err_str)

    async def _update_pair_strat_from_order_journal(self, order_journal_obj: OrderJournal,
                                                    order_snapshot: OrderSnapshot):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            partial_update_pair_strat_http, underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json
        pair_strat_objs = await underlying_read_pair_strat_http(get_pair_strat_sec_filter_json
                                                                (order_journal_obj.order.security.sec_id))
        if len(pair_strat_objs) == 1:
            updated_strat_status_obj = pair_strat_objs[0].strat_status
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
                                updated_strat_status_obj.total_cxl_buy_notional / updated_strat_status_obj.total_cxl_buy_qty
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - updated_strat_status_obj.total_cxl_sell_notional
                        case other:
                            err_str = f"Unsupported Order Event type {other}"
                            await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                                          order_journal_obj.order.side, err_str)
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
                                updated_strat_status_obj.total_cxl_sell_notional / updated_strat_status_obj.total_cxl_sell_qty
                            updated_strat_status_obj.total_cxl_exposure = \
                                updated_strat_status_obj.total_cxl_buy_notional - updated_strat_status_obj.total_cxl_sell_notional
                        case other:
                            err_str = f"Unsupported Order Event type {other}"
                            await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                                          order_journal_obj.order.side, err_str)
                    if updated_strat_status_obj.total_open_sell_qty == 0:
                        updated_strat_status_obj.avg_open_sell_px = 0
                    else:
                        updated_strat_status_obj.avg_open_sell_px = \
                            updated_strat_status_obj.total_open_sell_notional / updated_strat_status_obj.total_open_sell_qty
                case other:
                    err_str = f"Unsupported Side Type {other} received in order journal {order_journal_obj} " \
                              f"while updating strat_status"
                    await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                                  order_journal_obj.order.side, err_str)
            updated_strat_status_obj.total_order_qty = \
                updated_strat_status_obj.total_buy_qty + updated_strat_status_obj.total_sell_qty
            updated_strat_status_obj.total_open_exposure = \
                updated_strat_status_obj.total_open_buy_notional - updated_strat_status_obj.total_open_sell_notional

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_objs[0].id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()
            updated_pair_strat_obj.frequency = pair_strat_objs[0].frequency + 1
            await partial_update_pair_strat_http(updated_pair_strat_obj)
        else:
            err_str = "Pair_strat can't have more than one obj with same symbol in pair_strat_params, " \
                      f"received - {pair_strat_objs}"
            await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                          order_journal_obj.order.side, err_str)

    async def _update_portfolio_status_from_order_journal(self, order_journal_obj: OrderJournal,
                                                          order_snapshot_obj: OrderSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_status_http, underlying_partial_update_portfolio_status_http

        portfolio_status_objs = await underlying_read_portfolio_status_http()
        if len(portfolio_status_objs) == 1:
            portfolio_status_obj = portfolio_status_objs[0]
            match order_journal_obj.order.side:
                case Side.BUY:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            portfolio_status_obj.overall_buy_notional += \
                                order_journal_obj.order.px * order_journal_obj.order.qty
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_buy_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                            portfolio_status_obj.overall_buy_notional -= \
                                (order_snapshot_obj.order_brief.px * total_buy_unfilled_qty)
                case Side.SELL:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            portfolio_status_obj.overall_sell_notional += \
                                order_journal_obj.order.px * order_journal_obj.order.qty
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_sell_unfilled_qty = \
                                order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                            portfolio_status_obj.overall_sell_notional -= \
                                (order_snapshot_obj.order_brief.px * total_sell_unfilled_qty)
                case other:
                    err_str = f"Unsupported Side Type {other} received in order journal {order_journal_obj} " \
                              f"while updating strat_status"
                    await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                                  order_journal_obj.order.side, err_str)
            updated_portfolio_status = PortfolioStatusOptional(
                _id=portfolio_status_obj.id,
                overall_buy_notional=portfolio_status_obj.overall_buy_notional,
                overall_sell_notional=portfolio_status_obj.overall_sell_notional
            )
            await underlying_partial_update_portfolio_status_http(updated_portfolio_status)

        else:
            if len(portfolio_status_objs) > 1:
                err_str = f"Portfolio Status collection should have only one document, received {portfolio_status_objs}"
                await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                              order_journal_obj.order.side, err_str)
            else:
                err_str = f"Received Empty Portfolio Status from db while updating order journal relate fields"
                await self.update_strat_alert_by_sec_and_side(order_journal_obj.order.security.sec_id,
                                                              order_journal_obj.order.side, err_str)

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
            underlying_read_portfolio_status_http, underlying_partial_update_portfolio_status_http

        portfolio_status_objs = await underlying_read_portfolio_status_http()
        if len(portfolio_status_objs) == 1:
            portfolio_status_obj = portfolio_status_objs[0]
            match order_snapshot_obj.order_brief.side:
                case Side.BUY:
                    portfolio_status_obj.overall_buy_fill_notional += \
                        order_snapshot_obj.last_update_fill_px * order_snapshot_obj.last_update_fill_qty
                case Side.SELL:
                    portfolio_status_obj.overall_sell_fill_notional += \
                        order_snapshot_obj.last_update_fill_px * order_snapshot_obj.last_update_fill_qty
                case other:
                    err_str = f"Unsupported Side Type {other} received in order snapshot {order_snapshot_obj} " \
                              f"while updating strat_status"
                    await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                                  order_snapshot_obj.order_brief.side, err_str)
            updated_portfolio_status = PortfolioStatusOptional(
                _id=portfolio_status_obj.id,
                overall_buy_fill_notional=portfolio_status_obj.overall_buy_fill_notional,
                overall_sell_fill_notional=portfolio_status_obj.overall_sell_fill_notional
            )
            await underlying_partial_update_portfolio_status_http(updated_portfolio_status)
        else:
            if len(portfolio_status_objs) > 1:
                err_str = f"Portfolio Status collection should have only one document, received {portfolio_status_objs}"
                await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                              order_snapshot_obj.order_brief.side, err_str)
            else:
                err_str = f"Received Empty Portfolio Status from db while updating order journal relate fields"
                await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                              order_snapshot_obj.order_brief.side, err_str)

    async def _update_pair_strat_from_fill_journal(self, order_snapshot_obj: OrderSnapshot):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            partial_update_pair_strat_http, underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json
        pair_strat_objs = await underlying_read_pair_strat_http(get_pair_strat_sec_filter_json
                                                                (order_snapshot_obj.order_brief.security.sec_id))
        if len(pair_strat_objs) == 1:
            updated_strat_status_obj = pair_strat_objs[0].strat_status
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
                case other:
                    err_str = f"Unsupported Side Type {other} received in order snapshot {order_snapshot_obj} " \
                              f"while updating strat_status"
                    await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                                  order_snapshot_obj.order_brief.side, err_str)
            updated_strat_status_obj.total_open_exposure = \
                updated_strat_status_obj.total_open_buy_notional - updated_strat_status_obj.total_open_sell_notional
            updated_strat_status_obj.total_fill_exposure = \
                updated_strat_status_obj.total_fill_buy_notional - updated_strat_status_obj.total_fill_sell_notional

            updated_pair_strat_obj = PairStratOptional()
            updated_pair_strat_obj.id = pair_strat_objs[0].id
            updated_pair_strat_obj.strat_status = updated_strat_status_obj
            updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()
            updated_pair_strat_obj.frequency = pair_strat_objs[0].frequency + 1
            await partial_update_pair_strat_http(updated_pair_strat_obj)
        else:
            err_str = "Pair_strat can't have more than one obj with same symbol in pair_strat_params, " \
                      f"received - {pair_strat_objs}"
            await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                          order_snapshot_obj.order_brief.side, err_str)

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
                        last_update_fill_px=last_update_fill_px, last_update_date_time=DateTime.utcnow()))
                symbol_side_snapshot = \
                    await self._update_symbol_side_snapshot_from_fills_journal(fills_journal_obj, order_snapshot_obj)
                await self._update_pair_strat_from_fill_journal(order_snapshot_obj)
                await self._update_portfolio_status_from_fill_journal(order_snapshot_obj)
                await self._update_strat_brief_from_order(order_snapshot_obj, symbol_side_snapshot)

            else:
                err_str = f"Fill received for snapshot having status OE_DOD - received: " \
                          f"fill_journal - {fills_journal_obj}, snapshot - {order_snapshot_obj}"
                await self.update_strat_alert_by_sec_and_side(order_snapshot_obj.order_brief.security.sec_id,
                                                              order_snapshot_obj.order_brief.side, err_str)

        elif len(order_snapshot_objs) == 0:
            err_str = f"Could not find any order snapshot with order-id {fills_journal_obj.order_id} in " \
                      f"{order_snapshot_objs}"
            logging.exception(err_str)
            raise Exception(err_str)
        else:
            err_str = f"Match should return list of only one order_snapshot obj, " \
                      f"returned {order_snapshot_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    # Example: Soft API Query Interfaces

    async def get_symbol_side_snapshot_from_symbol_side_query_pre(self, symbol_side_snapshot_class_type: Type[
        SymbolSideSnapshot], security_id: str, side: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        return await underlying_read_symbol_side_snapshot_http(
            get_symbol_side_snapshot_from_symbol_side(security_id, side))

    async def get_pair_strat_sec_filter_json_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json
        return await underlying_read_pair_strat_http(get_pair_strat_sec_filter_json(security_id))

    def _set_new_strat_limit(self, pair_strat_obj: PairStrat):  # NOQA
        cancel_rate = CancelRate(max_cancel_rate=20, applicable_period_seconds=6)
        market_trade_volume_participation = MarketTradeVolumeParticipation(max_participation_rate=30,
                                                                           applicable_period_seconds=5)
        market_depth = OpenInterestParticipation(participation_rate=10, depth_levels=3)
        residual_restriction = ResidualRestriction(max_residual=70, residual_mark_seconds=4)
        pair_strat_obj.strat_limits = StratLimits(max_open_orders_per_side=2,
                                                  max_cb_notional=300_000,
                                                  max_open_cb_notional=30_000,
                                                  max_net_filled_notional=60_000,
                                                  max_concentration=1,
                                                  limit_up_down_volume_participation_rate=1,
                                                  eligible_brokers=[],
                                                  cancel_rate=cancel_rate,
                                                  market_trade_volume_participation=market_trade_volume_participation,
                                                  market_depth=market_depth,
                                                  residual_restriction=residual_restriction
                                                  )

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
            residual = Residual(security=pair_strat_obj.pair_strat_params.strat_leg1.sec, max_residual_notional=2500)
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
                                                      residual=residual, balance_notional=0.0)
        else:
            err_str = f"_add_pair_strat_status called with unexpected pre-set strat_status: {pair_strat_obj}"
            await self.update_strat_alert_by_sec_and_side(pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                                                          pair_strat_obj.pair_strat_params.strat_leg1.side, err_str)

    @except_n_log_alert(severity=Severity.Severity_ERROR)
    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
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

        # creating strat_brief for both leg securities
        await self._create_strat_brief_from_pair_strat_pre(pair_strat_obj)

        # creating symbol_side_snapshot for both leg securities if not already exists
        await self._create_symbol_snapshot_if_not_exists_from_pair_strat_pre(pair_strat_obj)

        # creating portfolio_status if not already exists
        await self._create_portfolio_status_if_not_exists()

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
                                                              frequency=0)
                created_symbol_side_snapshot = \
                    await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
                logging.debug(f"Created SymbolSideSnapshot {created_symbol_side_snapshot} for security {security} and "
                              f"side {side} in pre call of pair_strat {pair_strat_obj}")

            elif len(symbol_side_snapshots) == 1:
                # Symbol and side snapshot already exists
                pass
            else:
                err_str = f"SymbolSideSnapshot must be one per symbol and side, received {symbol_side_snapshots} for " \
                          f"security {security} and side {side}"
                await self.update_strat_alert_by_sec_and_side(security.sec_id, side, err_str)

    async def _create_portfolio_status_if_not_exists(self) -> None:  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_portfolio_status_http, underlying_create_portfolio_status_http

        portfolio_status_obj_list = await underlying_read_portfolio_status_http()

        if len(portfolio_status_obj_list) == 0:
            portfolio_status: PortfolioStatus = PortfolioStatus(_id=PortfolioStatus.next_id(), kill_switch=False,
                                                                portfolio_alerts=[], overall_buy_notional=0,
                                                                overall_sell_notional=0, overall_buy_fill_notional=0,
                                                                overall_sell_fill_notional=0)
            created_portfolio_status = await underlying_create_portfolio_status_http(portfolio_status)
            logging.debug(f"Created empty PortfolioStatus {created_portfolio_status}")
        elif len(portfolio_status_obj_list) == 1:
            # expected result therefor passing
            pass
        else:
            err_str = f"PortfolioStatus must have only one document, received {portfolio_status_obj_list}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def _update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat) -> bool:
        """
        Return true if object further updated false otherwise
        """
        is_updated = False
        if updated_pair_strat_obj.strat_status is None:
            err_str = f"_update_pair_strat_pre called with NO set strat_status: {updated_pair_strat_obj}"
            await self.update_strat_alert_by_sec_and_side(
                stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id,
                stored_pair_strat_obj.pair_strat_params.strat_leg1.side, err_str)
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
        updated_pair_strat_obj.frequency += 1
        await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()
        logging.debug(f"further updated by _update_pair_strat _pre: (updated pair_strat obj)")

    async def _get_order_limits(self) -> OrderLimits:  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_order_limits_http
        order_limits_objs: List[OrderLimits] = await underlying_read_order_limits_http()

        if len(order_limits_objs) == 1:
            return order_limits_objs[0]
        else:
            err_str = f"OrderLimits must always have only one stored document, received: {len(order_limits_objs)} ;;; " \
                      f"{order_limits_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def _get_pair_strat_from_symbol(self, symbol: str) -> PairStrat:  # NOQA
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json

        pair_strat_objs_list = await underlying_read_pair_strat_http(get_pair_strat_sec_filter_json(symbol))

        if len(pair_strat_objs_list) == 1:
            return pair_strat_objs_list[0]
        else:
            err_str = "PairStrat should be one document per symbol, " \
                      f"received {len(pair_strat_objs_list)} - {pair_strat_objs_list}"
            logging.exception(err_str)
            raise Exception(err_str)

    def _get_top_of_book_from_symbol(self, symbol: str):
        top_of_book_list: List[TopOfBook] = market_data_service_web_client.get_top_of_book_from_index_client(symbol)
        if len(top_of_book_list) != 1:
            err_str = f"TopOfBook should be one per symbol received {len(top_of_book_list)} - {top_of_book_list}"
            logging.exception(err_str)
            raise Exception(err_str)
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
                err_str = "received empty aggregated list of objects from aggregation on OrderSnapshot to " \
                          f"get last {sum_period} sec total order sum"
                await self.update_strat_alert_by_sec_and_side(symbol, symbol_side_snapshot.side, err_str)

    def _get_participation_period_last_trade_qty_sum(self, top_of_book: TopOfBook,  # NOQA
                                                     applicable_period_seconds: int):
        market_trade_volume_list = top_of_book.market_trade_volume

        for market_trade_volume in market_trade_volume_list:
            if market_trade_volume.applicable_period_seconds == applicable_period_seconds:
                return market_trade_volume.participation_period_last_trade_qty_sum
        else:
            err_str = f"Couldn't find any match of applicable_period_seconds param {applicable_period_seconds} in" \
                      f"list of market_trade_volume in TopOfBook - {top_of_book}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def _update_strat_brief_from_order(self, order_snapshot: OrderSnapshot,
                                             symbol_side_snapshot: SymbolSideSnapshot):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        security = symbol_side_snapshot.security
        side = symbol_side_snapshot.side
        symbol = security.sec_id
        pair_strat_obj: PairStrat = await self._get_pair_strat_from_symbol(symbol)
        open_qty = (symbol_side_snapshot.total_qty -
                    (symbol_side_snapshot.total_filled_qty + symbol_side_snapshot.total_cxled_qty))
        if pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id == symbol:
            other_leg_symbol = pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id
        else:
            other_leg_symbol = pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id
        other_leg_side = Side.BUY if side == Side.SELL else Side.SELL
        other_leg_symbol_side_snapshots = \
            await underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(other_leg_symbol, other_leg_side))
        if len(other_leg_symbol_side_snapshots) != 1:
            err_str = f"SymbolSideSnapshot must be one per symbol and side, received " \
                      f"{len(other_leg_symbol_side_snapshots)}, complete list - {other_leg_symbol_side_snapshots}"
            await self.update_strat_alert_by_sec_and_side(other_leg_symbol, other_leg_side, err_str)
            raise Exception(err_str)
        else:
            other_leg_symbol_side_snapshot = other_leg_symbol_side_snapshots[0]
        other_leg_total_open_qty = (other_leg_symbol_side_snapshot.total_qty -
                                    (other_leg_symbol_side_snapshot.total_filled_qty +
                                     other_leg_symbol_side_snapshot.total_cxled_qty))
        open_notional = open_qty * order_snapshot.order_brief.px
        consumable_notional = \
            pair_strat_obj.strat_limits.max_cb_notional - symbol_side_snapshot.total_fill_notional - \
            open_notional
        consumable_open_notional = \
            pair_strat_obj.strat_limits.max_open_cb_notional - open_notional
        top_of_book_obj = self._get_top_of_book_from_symbol(symbol)
        consumable_concentration = \
            ((top_of_book_obj.total_trading_security_size / 100) * pair_strat_obj.strat_limits.max_concentration) - \
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
        if (computed_residual_qty := (open_qty - other_leg_total_open_qty)) > 0:
            residual_qty = computed_residual_qty
        else:
            residual_qty = 0
        other_leg_residual_qty = 0 if (other_leg_computed_residual_qty := (other_leg_total_open_qty - open_qty)) <= 0 \
            else other_leg_computed_residual_qty
        other_leg_top_of_book = self._get_top_of_book_from_symbol(other_leg_symbol)
        indicative_consumable_residual = pair_strat_obj.strat_status.residual.max_residual_notional - \
                                         ((residual_qty * top_of_book_obj.last_trade.px) -
                                          (other_leg_residual_qty * other_leg_top_of_book.last_trade.px))

        new_pair_side_brief_obj = PairSideTradingBrief(security=security, side=side,
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
                                                       all_bkr_cxlled_qty=symbol_side_snapshot.total_cxled_qty,
                                                       open_notional=open_notional,
                                                       open_qty=open_qty
                                                       )

        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_strat_brief_http, underlying_partial_update_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol
        strat_brief_objs = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol))
        if len(strat_brief_objs) == 1:
            strat_brief_obj = strat_brief_objs[0]
            if symbol == strat_brief_obj.pair_buy_side_trading_brief.security.sec_id:
                updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                         pair_buy_side_trading_brief=new_pair_side_brief_obj)
            elif symbol == strat_brief_obj.pair_sell_side_trading_brief.security.sec_id:
                updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                         pair_sell_side_trading_brief=new_pair_side_brief_obj)
            else:
                err_str = f"No one of Both pair_side_trading_brief fields of strat_brief obj {strat_brief_obj} " \
                          f"contains symbol {symbol}"
                logging.exception(err_str)
                raise Exception(err_str)

            await underlying_partial_update_strat_brief_http(updated_strat_brief)

        else:
            err_str = f"StratBrief must be one per symbol, " \
                      f"received {len(strat_brief_objs)} - {strat_brief_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    async def update_strat_alert_by_sec_and_side(self, sec_id: str, side: Side, alert_brief: str,
                                                 alert_details: str | None = None,
                                                 severity: Severity = Severity.Severity_ERROR):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_pair_strat_http, underlying_partial_update_pair_strat_http
        alert: Alert = create_alert(alert_brief, alert_details, [], severity)
        with update_strat_status_lock:
            pair_strat_list: List[PairStrat] = await underlying_read_pair_strat_http()
            for pair_strat in pair_strat_list:
                if (pair_strat.pair_strat_params.strat_leg1.sec.sec_id == sec_id and
                    pair_strat.pair_strat_params.strat_leg1.side == side) or \
                        (pair_strat.pair_strat_params.strat_leg2.sec.sec_id == sec_id and
                         pair_strat.pair_strat_params.strat_leg2.side == side):
                    strat_status: StratStatus = StratStatus(strat_state=pair_strat.strat_status.strat_state,
                                                            strat_alerts=(
                                                                pair_strat.strat_status.strat_alerts.append(alert)))
                    pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id,
                                                                              strat_status=strat_status)
                    await underlying_partial_update_pair_strat_http(pair_strat_updated)
                else:
                    continue
            else:
                logging.error(f"security: {sec_id}, side: {side} combo was not found in any of the pair strats while "
                              f"raising alert;;; alert_brief: {alert_brief}, alert_details: {alert_details}")

    async def get_strat_brief_from_symbol_query_pre(self, strat_brief_class_type: Type[StratBrief], security_id: str):
        from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.addressbook.app.aggregate import get_strat_brief_from_symbol
        return await underlying_read_strat_brief_http(get_strat_brief_from_symbol(security_id))
