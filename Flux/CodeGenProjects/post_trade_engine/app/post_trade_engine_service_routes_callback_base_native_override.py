# standard imports
import logging
import time
from threading import Thread
from typing import Type, Callable
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from queue import Queue
import asyncio
from pydantic import BaseModel
import datetime

# project imports
from Flux.CodeGenProjects.post_trade_engine.generated.FastApi.post_trade_engine_service_routes_callback import (
    PostTradeEngineServiceRoutesCallback)
from Flux.CodeGenProjects.post_trade_engine.app.post_trade_engine_service_helper import *
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_engine_service_helper import (
    strat_manager_service_http_client, PairStratBaseModel, StratState, guaranteed_call_pair_strat_client)
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert
from Flux.CodeGenProjects.post_trade_engine.app.aggregate import get_open_order_counts, get_last_n_sec_orders_by_events


class ContainerObject(BaseModel):
    order_journals: List[OrderJournal]
    order_snapshots: List[OrderSnapshot]
    strat_brief: StratBrief | None = None
    portfolio_status_updates: List[PortfolioStatusUpdatesContainer]


class PostTradeEngineServiceRoutesCallbackBaseNativeOverride(PostTradeEngineServiceRoutesCallback):
    underlying_read_order_journal_http: Callable[..., Any] | None = None
    underlying_read_order_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_order_snapshot_http: Callable[..., Any] | None = None
    underlying_update_all_order_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_order_journal_http: Callable[..., Any] | None = None
    underlying_read_strat_brief_http: Callable[..., Any] | None = None
    underlying_create_strat_brief_http: Callable[..., Any] | None = None
    underlying_update_strat_brief_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_orders_by_events_query_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.post_trade_engine.generated.FastApi.post_trade_engine_service_http_routes import (
            underlying_read_order_journal_http, underlying_read_order_snapshot_http,
            underlying_create_all_order_snapshot_http, underlying_update_all_order_snapshot_http,
            underlying_create_all_order_journal_http, underlying_read_strat_brief_http,
            underlying_create_strat_brief_http, underlying_update_strat_brief_http,
            underlying_get_last_n_sec_orders_by_events_query_http)
        cls.underlying_read_order_journal_http = underlying_read_order_journal_http
        cls.underlying_read_order_snapshot_http = underlying_read_order_snapshot_http
        cls.underlying_create_all_order_snapshot_http = underlying_create_all_order_snapshot_http
        cls.underlying_update_all_order_snapshot_http = underlying_update_all_order_snapshot_http
        cls.underlying_create_all_order_journal_http = underlying_create_all_order_journal_http
        cls.underlying_read_strat_brief_http = underlying_read_strat_brief_http
        cls.underlying_create_strat_brief_http = underlying_create_strat_brief_http
        cls.underlying_update_strat_brief_http = underlying_update_strat_brief_http
        cls.underlying_get_last_n_sec_orders_by_events_query_http = underlying_get_last_n_sec_orders_by_events_query_http

    def __init__(self):
        super().__init__()
        self.port = None
        self.asyncio_loop = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.portfolio_limit_check_queue: Queue = Queue()
        self.update_portfolio_status_queue: Queue = Queue()
        self.container_model: Type = ContainerObject
        self.order_id_to_order_snapshot_cache_dict: Dict[str, OrderSnapshot] = {}
        self.strat_id_to_strat_brief_cache_dict: Dict[int, StratBrief] = {}

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"post_trade_engine_{pm_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        # Updating order_snapshot cache and strat_brief cache
                        self.load_existing_order_snapshot()
                        self.load_existing_strat_brief()

                        # Running portfolio_limit_check_queue_handler
                        Thread(target=self.portfolio_limit_check_queue_handler, daemon=True).start()
                        Thread(target=self._update_portfolio_status_n_check_portfolio_limits, daemon=True).start()
                    self.service_ready = True
                    print(f"INFO: service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_post_trade_engine_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
            else:
                should_sleep = True

    def app_launch_pre(self):
        PostTradeEngineServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()

        logging.debug("Triggered server launch pre override")
        self.port = pm_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    async def read_all_ui_layout_pre(self):
        # Setting asyncio_loop in ui_layout_pre since it called to check current service up
        attempt_counts = 3
        for _ in range(attempt_counts):
            if not self.asyncio_loop:
                self.asyncio_loop = asyncio.get_running_loop()
                time.sleep(1)
            else:
                break
        else:
            err_str_ = (f"self.asyncio_loop couldn't set as asyncio.get_running_loop() returned None for "
                        f"{attempt_counts} attempts")
            logging.critical(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    async def get_last_n_sec_orders_by_events_query_pre(self, order_journal_class_type: Type[OrderJournal],
                                                        last_n_sec: int, order_event_list: List[str]):
        return await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_journal_http(
            get_last_n_sec_orders_by_events(last_n_sec, order_event_list))

    async def get_open_order_count_query_pre(self, open_order_count_class_type: Type[OpenOrderCount], symbol: str):
        open_orders = await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http(
            get_open_order_counts())

        open_order_count = OpenOrderCount(open_order_count=len(open_orders))
        return [open_order_count]

    async def create_order_journal_pre(self, order_journal_obj: OrderJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_order_journal_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def create_order_snapshot_pre(self, order_snapshot_obj: OrderSnapshot):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_order_snapshot_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def create_strat_brief_pre(self, strat_brief_obj: StratBrief):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_strat_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def check_portfolio_limits_query_pre(self, check_portfolio_limits_class_type: Type[CheckPortfolioLimits],
                                               payload_dict: Dict[str, Any]):
        self.portfolio_limit_check_queue.put(payload_dict)
        return []

    def load_existing_order_snapshot(self):
        run_coro = (
            PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            order_snapshot_list: List[OrderSnapshot] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_order_snapshot_http failed - ignoring cache load of order_snapshot "
                              f"from db, exception: {e}")
            return None

        self._load_existing_order_snapshot(order_snapshot_list)

    def _load_existing_order_snapshot(self, order_snapshot_list: List[OrderSnapshot]):
        # Setting cache data member
        for order_snapshot in order_snapshot_list:
            self.order_id_to_order_snapshot_cache_dict[order_snapshot.order_brief.order_id] = order_snapshot

    def load_existing_strat_brief(self):
        run_coro = (
            PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            strat_brief_list: List[StratBrief] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_strat_brief_http failed - ignoring cache load of strat_brief "
                              f"from db, exception: {e}")
            return None

        # Setting cache data member
        self._load_existing_strat_brief(strat_brief_list)

    def _load_existing_strat_brief(self, strat_brief_list: List[StratBrief]):
        for strat_brief in strat_brief_list:
            self.strat_id_to_strat_brief_cache_dict[strat_brief.id] = strat_brief

    async def create_or_update_order_snapshot(self, order_snapshot_list: List[OrderSnapshot]):
        async with OrderSnapshot.reentrant_lock:
            create_order_snapshots: List[OrderSnapshot] = []
            update_order_snapshots: List[OrderSnapshot] = []
            for order_snapshot in order_snapshot_list:
                if order_snapshot.order_status == OrderStatusType.OE_UNACK:
                    create_order_snapshots.append(order_snapshot)
                else:
                    update_order_snapshots.append(order_snapshot)

            if create_order_snapshots:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_create_all_order_snapshot_http(
                    create_order_snapshots)
            if update_order_snapshots:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_update_all_order_snapshot_http(
                    update_order_snapshots)

    def _get_order_journal_from_payload(self, payload_dict: Dict[str, Any]) -> OrderJournal | None:
        order_journal: OrderJournal | None = None
        if (order_journal_dict := payload_dict.get("order_journal")) is not None:
            order_journal_dict["_id"] = OrderJournal.next_id()  # overriding id for this server db if exists
            order_journal = OrderJournal(**order_journal_dict)
        # else not required: Fills update doesn't contain order_journal
        return order_journal

    def _get_order_snapshot_from_payload(self, payload_dict: Dict[str, Any]) -> OrderSnapshot | None:
        order_snapshot: OrderSnapshot | None = None
        if (order_snapshot_dict := payload_dict.get("order_snapshot")) is not None:
            order_brief = order_snapshot_dict.get("order_brief")
            if order_brief is None:
                logging.error("order_snapshot_dict doesn't have 'order_brief' key - "
                              f"ignoring this order_snapshot create/update, order_snapshot_dict: {order_snapshot_dict}")
                return None
            else:
                order_id = order_brief.get("order_id")
            cached_order_snapshot = self.order_id_to_order_snapshot_cache_dict.get(order_id)
            if cached_order_snapshot is None:
                order_snapshot_dict["_id"] = OrderSnapshot.next_id()    # overriding id for this server db if exists
            else:
                order_snapshot_dict["_id"] = cached_order_snapshot.id   # updating _id from existing cache object
            order_snapshot = OrderSnapshot(**order_snapshot_dict)
            self.order_id_to_order_snapshot_cache_dict[order_snapshot.order_brief.order_id] = order_snapshot
        return order_snapshot

    def _get_strat_brief_from_payload(self, payload_dict: Dict[str, Any]):
        strat_brief: StratBrief | None = None
        if (strat_brief_dict := payload_dict.get("strat_brief")) is not None:
            # _id override for strat brief is not required since it will have same id as
            # it's respective executor strat_id, so it will be unique here too
            strat_brief = StratBrief(**strat_brief_dict)
        return strat_brief

    def _get_portfolio_status_updates_from_payload(self, payload_dict: Dict[str, Any]):
        portfolio_status_updates: PortfolioStatusUpdatesContainer | None = None
        if (portfolio_status_updates_dict := payload_dict.get("portfolio_status_updates")) is not None:
            portfolio_status_updates = PortfolioStatusUpdatesContainer(**portfolio_status_updates_dict)
        return portfolio_status_updates

    def update_strat_id_list_n_dict_from_payload(self, strat_id_list: List[int],
                                                 strat_id_to_container_obj_dict: Dict[int, ContainerObject],
                                                 payload_dict: Dict[str, Any]):
        strat_id = payload_dict.get("strat_id")
        if strat_id is None:
            logging.error("Payload doesn't contain strat_id, might be a bug at queue updater, "
                          f"ignoring this update, payload_received in queue: {payload_dict}")
            return None

        added_id: bool = False
        if strat_id not in strat_id_list:
            added_id = True
            strat_id_list.append(strat_id)

        order_journal: OrderJournal | None = self._get_order_journal_from_payload(payload_dict)

        order_snapshot: OrderSnapshot | None = self._get_order_snapshot_from_payload(payload_dict)
        if order_snapshot is None:
            logging.error("Payload doesn't contain order_snapshot, might be a bug at queue updater, "
                          f"ignoring this update, payload_received in queue: {payload_dict}")

            # rollback strat_id_list if id was added in this call
            if added_id:
                strat_id_list.remove(strat_id)
            return None

        strat_brief: StratBrief | None = self._get_strat_brief_from_payload(payload_dict)
        portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
            self._get_portfolio_status_updates_from_payload(payload_dict))

        container_obj: ContainerObject = strat_id_to_container_obj_dict.get(strat_id)
        if container_obj is not None:
            if order_journal is not None:
                container_obj.order_journals.append(order_journal)
            container_obj.order_snapshots.append(order_snapshot)
            if strat_brief is not None:
                container_obj.strat_brief = strat_brief
            if portfolio_status_updates is not None:
                container_obj.portfolio_status_updates.append(portfolio_status_updates)
        else:
            order_journal_list = []
            portfolio_status_updates_list = []
            if order_journal is not None:
                order_journal_list.append(order_journal)
            if portfolio_status_updates is not None:
                portfolio_status_updates_list.append(portfolio_status_updates)
            container_obj = self.container_model(order_journals=order_journal_list,
                                                 order_snapshots=[order_snapshot],
                                                 strat_brief=strat_brief,
                                                 portfolio_status_updates=portfolio_status_updates_list)
            strat_id_to_container_obj_dict[strat_id] = container_obj

    def add_order_journals(self, order_journal_list: List[OrderJournal]):
        run_coro = PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_create_all_order_journal_http(
            order_journal_list)
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"underlying_create_all_order_journal_http failed "
                              f"with exception: {e}")

    async def create_or_update_strat_brief(self, strat_brief: StratBrief):
        async with StratBrief.reentrant_lock:
            if strat_brief.id not in self.strat_id_to_strat_brief_cache_dict:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_brief_http(
                    strat_brief)
            else:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_brief_http(
                    strat_brief)
            self.strat_id_to_strat_brief_cache_dict[strat_brief.id] = strat_brief

    def update_db(self, order_journal_list: List[OrderJournal],
                  order_snapshot_list: List[OrderSnapshot],
                  strat_brief: StratBrief):
        # creating order_journals
        if order_journal_list:
            self.add_order_journals(order_journal_list)

        # creating or updating order_snapshot
        if order_snapshot_list:
            run_coro = self.create_or_update_order_snapshot(order_snapshot_list)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

            # block for task to finish
            try:
                future.result()
            except HTTPException as http_e:
                logging.exception(f"create_or_update_order_snapshot failed "
                                  f"with http_exception: {http_e.detail}")
            except Exception as e:
                logging.exception(f"create_or_update_order_snapshot failed "
                                  f"with exception: {e}")

        # creating or updating strat_brief
        if strat_brief is not None:
            run_coro = self.create_or_update_strat_brief(strat_brief)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"create_or_update_strat_brief failed "
                                  f"with exception: {e}")

    async def check_max_open_baskets(self, max_open_baskets: int) -> bool:
        pause_all_strats = False
        order_snapshot_list: List[OrderSnapshot] = await (
            PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http(
                get_open_order_counts()))
        open_order_count: int = len(order_snapshot_list)

        if max_open_baskets - open_order_count < 0:
            logging.error(f"max_open_baskets breached, allowed max_open_baskets: "
                          f"{max_open_baskets}, current open_order_count {open_order_count} - "
                          f"initiating all strat pause")
            pause_all_strats = True
        return pause_all_strats

    async def check_rolling_max_order_count(self, rolling_order_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_strats = False

        order_count_updated_order_journals: List[OrderJournal] = (
            await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.
            underlying_get_last_n_sec_orders_by_events_query_http(rolling_order_count_period_seconds,
                                                                 [OrderEventType.OE_NEW]))

        if len(order_count_updated_order_journals) == 1:
            rolling_new_order_count = order_count_updated_order_journals[-1].current_period_order_count
        elif len(order_count_updated_order_journals) > 1:
            err_str_ = ("Must receive only one object in list by get_last_n_sec_orders_by_events_query, "
                        f"received {len(order_count_updated_order_journals)}, avoiding this check, "
                        f"received list: {order_count_updated_order_journals}")
            logging.error(err_str_)
            return False
        else:
            rolling_new_order_count = 0
        if rolling_new_order_count > max_rolling_tx_count:
            logging.error(f"max_allowed_orders_within_period breached: "
                          f"{order_count_updated_order_journals[0].current_period_order_count} "
                          f"orders in past {rolling_order_count_period_seconds} secs, "
                          f"allowed orders within this period is {max_rolling_tx_count}"
                          f"- initiating all strat pause")
            pause_all_strats = True
        return pause_all_strats

    async def check_rolling_max_rej_count(self, rolling_rej_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_strats = False

        order_count_updated_order_journals: List[OrderJournal] = (
            await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.
            underlying_get_last_n_sec_orders_by_events_query_http(
                rolling_rej_count_period_seconds, [OrderEventType.OE_BRK_REJ, OrderEventType.OE_EXH_REJ]))
        if len(order_count_updated_order_journals) == 1:
            rolling_rej_order_count = order_count_updated_order_journals[0].current_period_order_count
        elif len(order_count_updated_order_journals) > 0:
            err_str_ = ("Must receive only one object in list from get_last_n_sec_orders_by_events_query, "
                        f"received: {len(order_count_updated_order_journals)}, avoiding this check, "
                        f"received list: {order_count_updated_order_journals}")
            logging.error(err_str_)
            return False
        else:
            rolling_rej_order_count = 0

        if rolling_rej_order_count > max_rolling_tx_count:
            logging.error(f"max_allowed_rejection_within_period breached: "
                          f"{order_count_updated_order_journals[0].current_period_order_count} "
                          f"rejections in past {rolling_rej_count_period_seconds} secs, "
                          f"allowed rejections within this period is {max_rolling_tx_count}"
                          f"- initiating all strat pause")
            pause_all_strats = True
        return pause_all_strats

    async def check_all_portfolio_limits(self) -> bool:
        portfolio_limits = strat_manager_service_http_client.get_portfolio_limits_client(portfolio_limits_id=1)

        pause_all_strats = False

        # Checking portfolio_limits.max_open_baskets
        max_open_baskets_breached = await self.check_max_open_baskets(portfolio_limits.max_open_baskets)
        if max_open_baskets_breached:
            pause_all_strats = True

        # block for task to finish
        total_buy_open_notional = 0
        total_sell_open_notional = 0
        async with StratBrief.reentrant_lock:
            for strat_brief in self.strat_id_to_strat_brief_cache_dict.values():
                # Buy side check
                total_buy_open_notional += strat_brief.pair_buy_side_trading_brief.open_notional
                # Sell side check
                total_sell_open_notional += strat_brief.pair_sell_side_trading_brief.open_notional

        if portfolio_limits.max_open_notional_per_side < total_buy_open_notional:
            logging.error(f"max_open_notional_per_side breached for BUY side, "
                          f"allowed max_open_notional_per_side: {portfolio_limits.max_open_notional_per_side}, "
                          f"current total_buy_open_notional {total_buy_open_notional}"
                          f" - initiating all strat pause")
            pause_all_strats = True

        if portfolio_limits.max_open_notional_per_side < total_sell_open_notional:
            logging.error(f"max_open_notional_per_side breached for SELL side, "
                          f"allowed max_open_notional_per_side: {portfolio_limits.max_open_notional_per_side}, "
                          f"current total_sell_open_notional {total_sell_open_notional}"
                          f" - initiating all strat pause")
            pause_all_strats = True

        # Checking portfolio_limits.max_gross_n_open_notional
        portfolio_status = strat_manager_service_http_client.get_portfolio_status_client(portfolio_status_id=1)
        total_open_notional = total_buy_open_notional + total_sell_open_notional
        total_gross_n_open_notional = (total_open_notional + portfolio_status.overall_buy_fill_notional +
                                       portfolio_status.overall_sell_fill_notional)
        if portfolio_limits.max_gross_n_open_notional < total_gross_n_open_notional:
            logging.error(f"max_gross_n_open_notional breached, "
                          f"allowed max_gross_n_open_notional: {portfolio_limits.max_gross_n_open_notional}, "
                          f"current total_gross_n_open_notional {total_gross_n_open_notional}"
                          f" - initiating all strat pause")
            pause_all_strats = True

        # Checking portfolio_limits.rolling_max_order_count
        rolling_max_order_count_breached: bool = await self.check_rolling_max_order_count(
                portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds,
                portfolio_limits.rolling_max_order_count.max_rolling_tx_count)
        if rolling_max_order_count_breached:
            pause_all_strats = True

        # checking portfolio_limits.rolling_max_reject_count
        rolling_max_rej_count_breached: bool = await self.check_rolling_max_rej_count(
                portfolio_limits.rolling_max_reject_count.rolling_tx_count_period_seconds,
                portfolio_limits.rolling_max_reject_count.max_rolling_tx_count)
        if rolling_max_rej_count_breached:
            pause_all_strats = True
        return pause_all_strats

    def _portfolio_limit_check_queue_handler(self, strat_id_list: List[int],
                                             strat_id_to_container_obj_dict: Dict[int, ContainerObject]):
        """post pickup form queue - data [list] is now in dict/list"""
        for strat_id in strat_id_list:
            container_object = strat_id_to_container_obj_dict.get(strat_id)
            order_journal_list = container_object.order_journals
            order_snapshot_list = container_object.order_snapshots
            strat_brief = container_object.strat_brief
            portfolio_status_updates_list = container_object.portfolio_status_updates

            # Updating db
            self.update_db(order_journal_list, order_snapshot_list, strat_brief)

            # updating update_portfolio_status_queue - handler gets data and constantly tries
            #                                          to update until gets success
            for portfolio_status_updates in portfolio_status_updates_list:
                self.update_portfolio_status_queue.put(portfolio_status_updates)

    @staticmethod
    def check_connection_or_service_not_ready_error(exception: Exception) -> bool:
        if "Failed to establish a new connection: [Errno 111] Connection refused" in str(exception):
            logging.exception("Connection Error in pair_strat_engine server call, likely server is "
                              "down")
        elif "service is not initialized yet" in str(exception):
            logging.exception("pair_strat_engine service not up yet, likely server restarted, but is "
                              "not ready yet")
        elif "('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))" in str(exception):
            logging.exception("pair_strat_engine service connection error")
        elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
              "it from responding to requests" in str(exception) and "status_code: 503" in str(exception)):
            logging.exception("pair_strat_engine service connection error")
        else:
            return False
        return True

    def _update_portfolio_status_n_check_portfolio_limits(self):
        while 1:
            portfolio_status_updates: PortfolioStatusUpdatesContainer = self.update_portfolio_status_queue.get()

            while 1:
                try:
                    strat_manager_service_http_client.update_portfolio_status_by_order_or_fill_data_query_client(
                        overall_buy_notional=portfolio_status_updates.buy_notional_update,
                        overall_sell_notional=portfolio_status_updates.sell_notional_update,
                        overall_buy_fill_notional=portfolio_status_updates.buy_fill_notional_update,
                        overall_sell_fill_notional=portfolio_status_updates.sell_fill_notional_update)
                except Exception as e:
                    res = self.check_connection_or_service_not_ready_error(e)   # True if connection or service up error
                    if not res:
                        logging.exception(
                            f"update_portfolio_status_by_order_or_fill_data_query_client failed with exception: {e}")
                        break
                    else:
                        logging.info("Retrying update_portfolio_status_by_order_or_fill_data_query_client in 1 sec")
                        time.sleep(1)
                else:
                    break

            while 1:
                # Checking Portfolio limits and Pausing ALL Strats if limit found breached
                run_coro = self.check_all_portfolio_limits()
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                # block for task to finish
                try:
                    pause_all_strats: bool = future.result()
                except Exception as e:
                    res = self.check_connection_or_service_not_ready_error(e)   # True if connection or service up error
                    if not res:
                        logging.exception(f"check_all_portfolio_limits failed, exception: {e}")
                        return None
                    else:
                        logging.info("Retrying check_all_portfolio_limits in 1 sec")
                        time.sleep(1)
                else:
                    break

            if pause_all_strats:
                while 1:
                    try:
                        strat_manager_service_http_client.pause_all_active_strats_query_client()
                    except Exception as e:
                        # True if connection or service up error
                        res = self.check_connection_or_service_not_ready_error(e)
                        if not res:
                            logging.exception(
                                f"pause_all_active_strats_query_client failed with exception {e}")
                            break
                        else:
                            logging.info("Retrying pause_all_active_strats_query_client in 1 sec")
                            time.sleep(1)
                    else:
                        break

    async def is_portfolio_limits_breached_query_pre(
            self, is_portfolio_limits_breached_class_type: Type[IsPortfolioLimitsBreached]):
        """
        :return: returns empty list if exception occurs
        """
        try:
            pause_all_strats = await self.check_all_portfolio_limits()
        except Exception as e:
            # True if connection or service up error
            res = self.check_connection_or_service_not_ready_error(e)
            if res:
                logging.exception("pair_strat_engine seems down, returning empty list from "
                                  "is_portfolio_limits_breached_query_pre")
                return []
        else:
            return [IsPortfolioLimitsBreached(is_portfolio_limits_breached=pause_all_strats)]

    def portfolio_limit_check_queue_handler(self):
        while 1:
            strat_id_list: List[int] = []
            strat_id_to_container_obj_dict: Dict[int, ContainerObject] = {}
            payload_dict: Dict[str, Any] = self.portfolio_limit_check_queue.get()   # blocking call
            self.update_strat_id_list_n_dict_from_payload(strat_id_list,
                                                          strat_id_to_container_obj_dict, payload_dict)

            while not self.portfolio_limit_check_queue.empty():
                payload_dict: Dict[str, Any] = self.portfolio_limit_check_queue.get()
                self.update_strat_id_list_n_dict_from_payload(strat_id_list, strat_id_to_container_obj_dict,
                                                              payload_dict)
            # Does db operations and checks portfolio_limits and raises all-strat pause if any limit breaches
            self._portfolio_limit_check_queue_handler(strat_id_list, strat_id_to_container_obj_dict)

    async def reload_cache_query_pre(self, reload_cache_class_type: Type[ReloadCache]):
        # clearing cache dict
        self.order_id_to_order_snapshot_cache_dict.clear()
        self.strat_id_to_strat_brief_cache_dict.clear()

        order_snapshot_list: List[OrderSnapshot] = \
            await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http()
        self._load_existing_order_snapshot(order_snapshot_list)

        strat_brief_list: List[StratBrief] = \
            await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http()
        self._load_existing_strat_brief(strat_brief_list)

        return []
