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

# project imports
from Flux.CodeGenProjects.post_trade_engine.generated.FastApi.post_trade_engine_service_routes_callback import (
    PostTradeEngineServiceRoutesCallback)
from Flux.CodeGenProjects.post_trade_engine.app.post_trade_engine_service_helper import *
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_engine_service_helper import (
    strat_manager_service_http_client)
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import (
    StratState, StratStatusBaseModel)
from Flux.CodeGenProjects.strat_executor.app.aggregate import (get_last_n_sec_orders_by_event,
                                                               get_order_snapshot_order_id_filter_json)
from Flux.CodeGenProjects.post_trade_engine.app.aggregate import get_open_order_counts


class ContainerObject(BaseModel):
    order_journals: List[OrderJournal]
    order_snapshots: List[OrderSnapshot]
    strat_brief: StratBrief | None = None


class PostTradeEngineServiceRoutesCallbackBaseNativeOverride(PostTradeEngineServiceRoutesCallback):
    underlying_read_order_journal_http: Callable[..., Any] | None = None
    underlying_read_order_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_order_snapshot_http: Callable[..., Any] | None = None
    underlying_update_all_order_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_order_journal_http: Callable[..., Any] | None = None
    underlying_read_strat_brief_by_id_http: Callable[..., Any] | None = None
    underlying_create_strat_brief_http: Callable[..., Any] | None = None
    underlying_update_strat_brief_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_orders_by_event_query_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.post_trade_engine.generated.FastApi.post_trade_engine_service_http_routes import (
            underlying_read_order_journal_http, underlying_read_order_snapshot_http,
            underlying_create_all_order_snapshot_http, underlying_update_all_order_snapshot_http,
            underlying_create_all_order_journal_http, underlying_read_strat_brief_by_id_http,
            underlying_create_strat_brief_http, underlying_update_strat_brief_http,
            underlying_get_last_n_sec_orders_by_event_query_http)
        cls.underlying_read_order_journal_http = underlying_read_order_journal_http
        cls.underlying_read_order_snapshot_http = underlying_read_order_snapshot_http
        cls.underlying_create_all_order_snapshot_http = underlying_create_all_order_snapshot_http
        cls.underlying_update_all_order_snapshot_http = underlying_update_all_order_snapshot_http
        cls.underlying_create_all_order_journal_http = underlying_create_all_order_journal_http
        cls.underlying_read_strat_brief_by_id_http = underlying_read_strat_brief_by_id_http
        cls.underlying_create_strat_brief_http = underlying_create_strat_brief_http
        cls.underlying_update_strat_brief_http = underlying_update_strat_brief_http
        cls.underlying_get_last_n_sec_orders_by_event_query_http = underlying_get_last_n_sec_orders_by_event_query_http

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
        self.container_model: Type = ContainerObject

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
                        self.service_ready = True

                        # Running portfolio_limit_check_queue_handler
                        Thread(target=self.portfolio_limit_check_queue_handler, daemon=True).start()

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

    async def get_last_n_sec_orders_by_event_query_pre(self, order_journal_class_type: Type[OrderJournal],
                                                       last_n_sec: int, order_event: str):
        return await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_journal_http(
            get_last_n_sec_orders_by_event(last_n_sec, order_event))

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

    async def create_order_snapshot_pre(self, order_snapshot_obj: OrderSnapshot):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_order_snapshot_pre not ready - service is not initialized yet"
            logging.error(err_str_)

    async def create_strat_brief_pre(self, strat_brief_obj: StratBrief):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_strat_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)

    async def check_portfolio_limits_query_pre(self, check_portfolio_limits_class_type: Type[CheckPortfolioLimits],
                                               payload_dict: Dict[str, Any]):
        self.portfolio_limit_check_queue.put(payload_dict)
        return []

    async def create_or_update_order_snapshot(self, order_snapshot_list: List[OrderSnapshot]):
        order_id_to_latest_order_snapshot_dict = {}
        # Taking latest order_snapshots based on order_id
        for order_snapshot in order_snapshot_list:
            order_id_to_latest_order_snapshot_dict[order_snapshot.order_brief.order_id] = order_snapshot

        async with OrderSnapshot.reentrant_lock:
            create_order_snapshots: List[OrderSnapshot] = []
            update_order_snapshots: List[OrderSnapshot] = []
            for order_id, order_snapshot in order_id_to_latest_order_snapshot_dict.items():
                filtered_order_snapshot_list: List[OrderSnapshot] = (
                    await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http(
                        get_order_snapshot_order_id_filter_json(order_id)))

                if len(filtered_order_snapshot_list) == 0:
                    order_snapshot.id = OrderSnapshot.next_id()    # overriding id to make it unique for this server db
                    create_order_snapshots.append(order_snapshot)
                elif len(filtered_order_snapshot_list) > 1:
                    err_str = (f"Unexpected: There must only max one order_snapshot with order_id: "
                               f"{order_snapshot.order_brief.order_id} but found {len(filtered_order_snapshot_list)}, "
                               f"avoiding this order_snapshot create/update, "
                               f"found order_snapshot list: {filtered_order_snapshot_list}")
                    logging.error(err_str)
                    return False
                else:
                    stored_order_snapshot = filtered_order_snapshot_list[0]
                    order_snapshot.id = stored_order_snapshot.id    # updating id to stored id for patch
                    update_order_snapshots.append(order_snapshot)

            if create_order_snapshots:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_create_all_order_snapshot_http(
                    create_order_snapshots)
            if update_order_snapshots:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_update_all_order_snapshot_http(
                    update_order_snapshots)

    def _get_order_journal_from_payload(self, payload_dict: Dict[str, Any]):
        order_journal: OrderJournal | None = None
        if (order_journal_dict := payload_dict.get("order_journal")) is not None:
            order_journal_dict["_id"] = OrderJournal.next_id()  # overriding id for this server db if exists
            order_journal = OrderJournal(**order_journal_dict)
        # else not required: Fills update doesn't contain order_journal
        return order_journal

    def _get_order_snapshot_from_payload(self, payload_dict: Dict[str, Any]):
        order_snapshot: OrderSnapshot | None = None
        if (order_snapshot_dict := payload_dict.get("order_snapshot")) is not None:
            # _id override for order_snapshot is done in create/update time since more cleanup is done
            # before create/update call, to know about extra cleanup check function to create/update order_snapshot
            order_snapshot = OrderSnapshot(**order_snapshot_dict)
        return order_snapshot

    def _get_strat_brief_from_payload(self, payload_dict: Dict[str, Any]):
        strat_brief: StratBrief | None = None
        if (strat_brief_dict := payload_dict.get("strat_brief")) is not None:
            # _id override for strat brief is not required since it will have same id as
            # it's respective executor strat_id, so it will be unique here too
            strat_brief = StratBrief(**strat_brief_dict)
        return strat_brief

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

        container_obj: ContainerObject = strat_id_to_container_obj_dict.get(strat_id)
        if container_obj is not None:
            if order_journal is not None:
                container_obj.order_journals.append(order_journal)
            container_obj.order_snapshots.append(order_snapshot)
            if strat_brief is not None:
                container_obj.strat_brief = strat_brief
        else:
            order_journal_list = []
            if order_journal is not None:
                order_journal_list.append(order_journal)
            container_obj = self.container_model(order_journals=order_journal_list,
                                                 order_snapshots=[order_snapshot],
                                                 strat_brief=strat_brief)
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
            try:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_by_id_http(
                    strat_brief.id)
            except HTTPException as http_e:
                # creating if no object exists with id
                if "Id not Found:" in http_e.detail:
                    await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_brief_http(
                        strat_brief)
                else:
                    logging.exception(f"underlying_read_strat_brief_by_id_http failed "
                                      f"with http_exception: {http_e.detail}")
            except Exception as e:
                logging.exception(f"underlying_read_strat_brief_by_id_http failed "
                                  f"with exception: {e}")
            else:
                await PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_brief_http(
                    strat_brief)

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
            except Exception as e:
                logging.exception(f"underlying_create_order_journal_http failed "
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

    def check_max_open_baskets(self, max_open_baskets: int) -> bool:
        pause_all_strats = False
        run_coro = PostTradeEngineServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http(
            get_open_order_counts())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            order_snapshot_list: List[OrderSnapshot] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_order_snapshot_http failed with exception: {e}")
        else:
            open_order_count: int = len(order_snapshot_list)

            if max_open_baskets - open_order_count < 0:
                logging.error(f"max_open_baskets breached, allowed max_open_baskets: "
                              f"{max_open_baskets}, current open_order_count {open_order_count} - "
                              f"initiating all strat pause")
                pause_all_strats = True
        return pause_all_strats

    def check_rolling_max_order_count(self, rolling_order_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_strats = False
        run_coro = (PostTradeEngineServiceRoutesCallbackBaseNativeOverride.
                    underlying_get_last_n_sec_orders_by_event_query_http(rolling_order_count_period_seconds,
                                                                         OrderEventType.OE_NEW))
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            order_count_updated_order_journals = future.result()
        except Exception as e:
            logging.exception(f"underlying_get_last_n_sec_orders_by_event_query_http failed "
                              f"with exception: {e}")
        else:
            if len(order_count_updated_order_journals) == 1:
                rolling_new_order_count = order_count_updated_order_journals[-1].current_period_order_count
            elif len(order_count_updated_order_journals) > 1:
                err_str_ = ("Must receive only one object in list by get_last_n_sec_orders_by_event_query, "
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

    def check_rolling_max_rej_count(self, rolling_rej_count_period_seconds: int, max_rolling_tx_count: int):
        run_coro = (PostTradeEngineServiceRoutesCallbackBaseNativeOverride.
                    underlying_get_last_n_sec_orders_by_event_query_http(rolling_rej_count_period_seconds, "OE_REJ"))
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        pause_all_strats = False

        # block for task to finish
        try:
            order_count_updated_order_journals: List[OrderJournal] = future.result()
        except Exception as e:
            logging.exception(f"underlying_get_last_n_sec_orders_by_event_query_http failed for Rej check"
                              f"with exception: {e}")
        else:
            if len(order_count_updated_order_journals) == 1:
                rolling_rej_order_count = order_count_updated_order_journals[0].current_period_order_count
            elif len(order_count_updated_order_journals) > 0:
                err_str_ = ("Must receive only one object in list from get_last_n_sec_orders_by_event_query, "
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

    def check_all_portfolio_limits(self) -> bool:
        from Flux.CodeGenProjects.post_trade_engine.generated.FastApi.post_trade_engine_service_http_routes import (
            underlying_read_strat_brief_http)

        portfolio_limits = strat_manager_service_http_client.get_portfolio_limits_client(portfolio_limits_id=1)

        pause_all_strats = False

        # Checking portfolio_limits.max_open_baskets
        if self.check_max_open_baskets(portfolio_limits.max_open_baskets):
            pause_all_strats = True

        # Checking portfolio_limits.max_open_notional_per_side for both sides
        run_coro = underlying_read_strat_brief_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        total_buy_open_notional = 0
        total_sell_open_notional = 0
        try:
            strat_brief_list: List[StratBrief] = future.result()
        except Exception as e:
            logging.exception(f"underlying_get_open_order_count_query_http failed "
                              f"with exception: {e}")
        else:
            # Todo LAZY: Add aggregation for total_open_notional
            # Buy side check
            for strat_brief in strat_brief_list:
                total_buy_open_notional += strat_brief.pair_buy_side_trading_brief.open_notional

            if portfolio_limits.max_open_notional_per_side < total_buy_open_notional:
                logging.error(f"max_open_notional_per_side breached for BUY side, "
                              f"allowed max_open_notional_per_side: {portfolio_limits.max_open_notional_per_side}, "
                              f"current total_buy_open_notional {total_buy_open_notional}"
                              f" - initiating all strat pause")
                pause_all_strats = True

            # Sell side check
            for strat_brief in strat_brief_list:
                total_sell_open_notional += strat_brief.pair_sell_side_trading_brief.open_notional

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
        if self.check_rolling_max_order_count(
                portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds,
                portfolio_limits.rolling_max_order_count.max_rolling_tx_count):
            pause_all_strats = True

        # checking portfolio_limits.rolling_max_reject_count
        if self.check_rolling_max_rej_count(
                portfolio_limits.rolling_max_reject_count.rolling_tx_count_period_seconds,
                portfolio_limits.rolling_max_reject_count.max_rolling_tx_count):
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

            # Updating db
            self.update_db(order_journal_list, order_snapshot_list, strat_brief)

            # Checking Portfolio limits and Pausing ALL Strats if limit found breached
            if self.check_all_portfolio_limits():
                self.pause_all_strats()

    def portfolio_limit_check_queue_handler(self):
        while 1:
            strat_id_list: List[int] = []
            strat_id_to_container_obj_dict: Dict[int, ContainerObject] = {}
            payload_dict: Dict[str, Any] = self.portfolio_limit_check_queue.get()   # blocking call
            self.update_strat_id_list_n_dict_from_payload(strat_id_list,
                                                          strat_id_to_container_obj_dict, payload_dict)

            while not self.portfolio_limit_check_queue.empty():
                payload_dict: Dict[str, Any] = self.portfolio_limit_check_queue.get()  # blocking call
                self.update_strat_id_list_n_dict_from_payload(strat_id_list, strat_id_to_container_obj_dict,
                                                              payload_dict)
            # Does db operations and checks portfolio_limits and raises all-strat pause if any limit breaches
            self._portfolio_limit_check_queue_handler(strat_id_list, strat_id_to_container_obj_dict)

    def pause_all_strats(self):
        pair_strat_list = strat_manager_service_http_client.get_all_pair_strat_client()

        for pair_strat in pair_strat_list:
            if pair_strat.is_executor_running and pair_strat.port is not None and pair_strat.host is not None:
                strat_executor_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(pair_strat.host,
                                                                                                     pair_strat.port)
                strat_status = strat_executor_client.get_strat_status_client(pair_strat.id)
                # TODO: make query instead of get and patch calls
                if strat_status.strat_state == StratState.StratState_ACTIVE:
                    update_strat_status_obj = StratStatusBaseModel(_id=pair_strat.id,
                                                                   strat_state=StratState.StratState_PAUSED)
                    strat_executor_client.patch_strat_status_client(jsonable_encoder(update_strat_status_obj,
                                                                                     by_alias=True, exclude_none=True))
            # else not required: pair_strat which are still not running or still not activated

    async def pause_all_strats_query_pre(self, pause_all_strats_class_type: Type[PauseAllStrats]):
        self.pause_all_strats()
        return []
