# standard imports
import logging
import time
from threading import Thread
from typing import Type, Callable

import msgspec
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from queue import Queue
import asyncio
from pydantic import BaseModel
import datetime

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.FastApi.post_book_service_routes_msgspec_callback import (
    PostBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert, handle_refresh_configurable_data_members
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.aggregate import (
    get_open_chore_counts, get_last_n_sec_chores_by_events)


MsgspecType = TypeVar('MsgspecType', bound=msgspec.Struct)


class ContainerObject(msgspec.Struct, kw_only=True):
    chore_journals: List[ChoreJournal]
    chore_snapshots: List[ChoreSnapshot]
    strat_brief: StratBrief | None = None
    portfolio_status_updates: List[PortfolioStatusUpdatesContainer]


class PostBookServiceRoutesCallbackBaseNativeOverride(PostBookServiceRoutesCallback):
    underlying_read_chore_journal_http: Callable[..., Any] | None = None
    underlying_read_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_update_all_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_chore_journal_http: Callable[..., Any] | None = None
    underlying_read_strat_brief_http: Callable[..., Any] | None = None
    underlying_create_strat_brief_http: Callable[..., Any] | None = None
    underlying_update_strat_brief_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_chores_by_events_query_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.FastApi.post_book_service_http_routes_imports import (
            underlying_read_chore_journal_http, underlying_read_chore_snapshot_http,
            underlying_create_all_chore_snapshot_http, underlying_update_all_chore_snapshot_http,
            underlying_create_all_chore_journal_http, underlying_read_strat_brief_http,
            underlying_create_strat_brief_http, underlying_update_strat_brief_http,
            underlying_get_last_n_sec_chores_by_events_query_http)
        cls.underlying_read_chore_journal_http = underlying_read_chore_journal_http
        cls.underlying_read_chore_snapshot_http = underlying_read_chore_snapshot_http
        cls.underlying_create_all_chore_snapshot_http = underlying_create_all_chore_snapshot_http
        cls.underlying_update_all_chore_snapshot_http = underlying_update_all_chore_snapshot_http
        cls.underlying_create_all_chore_journal_http = underlying_create_all_chore_journal_http
        cls.underlying_read_strat_brief_http = underlying_read_strat_brief_http
        cls.underlying_create_strat_brief_http = underlying_create_strat_brief_http
        cls.underlying_update_strat_brief_http = underlying_update_strat_brief_http
        cls.underlying_get_last_n_sec_chores_by_events_query_http = underlying_get_last_n_sec_chores_by_events_query_http

    def __init__(self):
        super().__init__()
        self.port = None
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.portfolio_limit_check_queue: Queue = Queue()
        self.update_portfolio_status_queue: Queue = Queue()
        self.container_model: MsgspecType = ContainerObject
        self.chore_id_to_chore_snapshot_cache_dict: Dict[str, ChoreSnapshot] = {}
        self.chore_id_to_open_chore_snapshot_cache_dict: Dict[str, ChoreSnapshot] = {}
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
            service_up_flag_env_var = os.environ.get(f"post_book_{pt_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        # Updating chore_snapshot cache and strat_brief cache
                        self.load_existing_chore_snapshot()
                        self.load_existing_strat_brief()

                        # Running portfolio_limit_check_queue_handler
                        Thread(target=self.portfolio_limit_check_queue_handler, daemon=True).start()
                        Thread(target=self._update_portfolio_status_n_check_portfolio_limits, daemon=True).start()
                    self.service_ready = True
                    print(f"INFO: post barter engine service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_post_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    last_modified_timestamp = os.path.getmtime(config_yaml_path)
                    if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                        self.config_yaml_last_modified_timestamp = last_modified_timestamp

                        handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                 str(config_yaml_path))
            else:
                should_sleep = True

    def app_launch_pre(self):
        PostBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()

        logging.debug("Triggered server launch pre override")
        self.port = pt_port
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

    async def get_last_n_sec_chores_by_events_query_pre(self, chore_journal_class_type: Type[ChoreJournal],
                                                        last_n_sec: int, chore_event_list: List[str]):
        return await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_journal_http(
            get_last_n_sec_chores_by_events(last_n_sec, chore_event_list))

    async def get_open_chore_count_query_pre(self, open_chore_count_class_type: Type[OpenChoreCount], symbol: str):
        open_chores = await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http(
            get_open_chore_counts())

        open_chore_count = OpenChoreCount(open_chore_count=len(open_chores))
        return [open_chore_count]

    async def create_chore_journal_pre(self, chore_journal_obj: ChoreJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_chore_journal_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def create_chore_snapshot_pre(self, chore_snapshot_obj: ChoreSnapshot):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_chore_snapshot_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def update_chore_snapshot_pre(self, updated_chore_snapshot_obj: ChoreSnapshot):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_chore_snapshot_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        return updated_chore_snapshot_obj

    async def partial_update_chore_snapshot_pre(self, stored_chore_snapshot_obj: ChoreSnapshot,
                                                updated_chore_snapshot_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "partial_update_chore_snapshot_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        return updated_chore_snapshot_obj_json

    async def create_strat_brief_pre(self, strat_brief_obj: StratBrief):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_strat_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def update_strat_brief_pre(self, updated_strat_brief_obj: StratBrief):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        return updated_strat_brief_obj

    async def partial_update_strat_brief_pre(self, stored_strat_brief_obj: StratBrief,
                                             updated_strat_brief_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "partial_update_strat_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        return updated_strat_brief_obj_json

    async def check_portfolio_limits_query_pre(self, check_portfolio_limits_class_type: Type[CheckPortfolioLimits],
                                               payload_dict: Dict[str, Any]):
        self.portfolio_limit_check_queue.put(payload_dict)
        return []

    def load_existing_chore_snapshot(self):
        run_coro = (
            PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            chore_snapshot_list: List[ChoreSnapshot] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_chore_snapshot_http failed - ignoring cache load of chore_snapshot "
                              f"from db, exception: {e}")
            return None

        self._load_existing_chore_snapshot(chore_snapshot_list)

    def _update_open_chore_snapshot_cache(self, chore_snapshot: ChoreSnapshot):
        chore_id = chore_snapshot.chore_brief.chore_id
        cached_open_chore_snapshot = self.chore_id_to_open_chore_snapshot_cache_dict.get(chore_id)
        if cached_open_chore_snapshot is not None:
            if chore_snapshot.chore_status not in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED]:
                self.chore_id_to_open_chore_snapshot_cache_dict[chore_id] = chore_snapshot
            else:
                # removing from cache if chore is not open anymore
                del self.chore_id_to_open_chore_snapshot_cache_dict[chore_id]
        else:
            if chore_snapshot.chore_status not in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED]:
                self.chore_id_to_open_chore_snapshot_cache_dict[chore_id] = chore_snapshot
            # else not required: if chore_id_to_open_chore_snapshot_cache_dict doesn't contain this chore_snapshot,
            # and it is not open then avoiding its caching

    def _load_existing_chore_snapshot(self, chore_snapshot_list: List[ChoreSnapshot]):
        # Setting cache data member
        for chore_snapshot in chore_snapshot_list:
            self.chore_id_to_chore_snapshot_cache_dict[chore_snapshot.chore_brief.chore_id] = chore_snapshot

            # updating open_chore_snapshots
            self._update_open_chore_snapshot_cache(chore_snapshot)

    def load_existing_strat_brief(self):
        run_coro = (
            PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http())
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

    async def create_or_update_chore_snapshot(self, chore_snapshot_list: List[ChoreSnapshot]):
        async with ChoreSnapshot.reentrant_lock:
            create_chore_snapshots: List[ChoreSnapshot] = []
            update_chore_snapshots: List[ChoreSnapshot] = []
            for chore_snapshot in chore_snapshot_list:
                if chore_snapshot.chore_status == ChoreStatusType.OE_UNACK:
                    create_chore_snapshots.append(chore_snapshot)
                else:
                    update_chore_snapshots.append(chore_snapshot)

            if create_chore_snapshots:
                await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_chore_snapshot_http(
                    create_chore_snapshots)
            if update_chore_snapshots:
                await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_chore_snapshot_http(
                    update_chore_snapshots)

    def _get_chore_journal_from_payload(self, payload_dict: Dict[str, Any]) -> ChoreJournal | None:
        chore_journal: ChoreJournal | None = None
        if (chore_journal_dict := payload_dict.get("chore_journal")) is not None:
            chore_journal_dict["_id"] = ChoreJournal.next_id()  # overriding id for this server db if exists
            chore_journal = ChoreJournal.from_dict(chore_journal_dict)
        # else not required: Fills update doesn't contain chore_journal
        return chore_journal

    def _get_chore_snapshot_from_payload(self, payload_dict: Dict[str, Any]) -> ChoreSnapshot | None:
        chore_snapshot: ChoreSnapshot | None = None
        if (chore_snapshot_dict := payload_dict.get("chore_snapshot")) is not None:
            chore_brief = chore_snapshot_dict.get("chore_brief")
            if chore_brief is None:
                logging.error("chore_snapshot_dict doesn't have 'chore_brief' key - "
                              f"ignoring this chore_snapshot create/update, {chore_snapshot_dict=}")
                return None
            else:
                chore_id = chore_brief.get("chore_id")
            cached_chore_snapshot = self.chore_id_to_chore_snapshot_cache_dict.get(chore_id)
            if cached_chore_snapshot is None:
                chore_snapshot_dict["_id"] = ChoreSnapshot.next_id()  # overriding id for this server db if exists
            else:
                chore_snapshot_dict["_id"] = cached_chore_snapshot.id  # updating _id from existing cache object
            chore_snapshot = ChoreSnapshot.from_dict(chore_snapshot_dict)
            self.chore_id_to_chore_snapshot_cache_dict[chore_snapshot.chore_brief.chore_id] = chore_snapshot

            # updating open_chore_snapshots
            self._update_open_chore_snapshot_cache(chore_snapshot)

        return chore_snapshot

    def _get_strat_brief_from_payload(self, payload_dict: Dict[str, Any]):
        strat_brief: StratBrief | None = None
        if (strat_brief_dict := payload_dict.get("strat_brief")) is not None:
            # _id override for strat brief is not required since it will have same id as
            # it's respective executor strat_id, so it will be unique here too
            strat_brief = StratBrief.from_dict(strat_brief_dict)
        return strat_brief

    def _get_portfolio_status_updates_from_payload(self, payload_dict: Dict[str, Any]):
        portfolio_status_updates: PortfolioStatusUpdatesContainer | None = None
        if (portfolio_status_updates_dict := payload_dict.get("portfolio_status_updates")) is not None:
            portfolio_status_updates = PortfolioStatusUpdatesContainer.from_dict(portfolio_status_updates_dict)
        return portfolio_status_updates

    def update_strat_id_list_n_dict_from_payload(self, strat_id_list: List[int],
                                                 strat_id_to_container_obj_dict: Dict[int, ContainerObject],
                                                 payload_dict: Dict[str, Any]):
        """
        updates strat_id_to_container_obj_dict param - returns None
        """
        strat_id = payload_dict.get("strat_id")
        if strat_id is None:
            logging.error("Payload doesn't contain strat_id, might be a bug at queue updater, "
                          f"ignoring this update, payload_received in queue: {payload_dict}")
            return None

        added_id: bool = False
        if strat_id not in strat_id_list:
            added_id = True
            strat_id_list.append(strat_id)

        chore_journal: ChoreJournal | None = self._get_chore_journal_from_payload(payload_dict)

        chore_snapshot: ChoreSnapshot | None = self._get_chore_snapshot_from_payload(payload_dict)
        if chore_snapshot is None:
            logging.error("Payload doesn't contain chore_snapshot, might be a bug at queue updater, "
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
            if chore_journal is not None:
                container_obj.chore_journals.append(chore_journal)
            container_obj.chore_snapshots.append(chore_snapshot)
            if strat_brief is not None:
                container_obj.strat_brief = strat_brief
            if portfolio_status_updates is not None:
                container_obj.portfolio_status_updates.append(portfolio_status_updates)
        else:
            chore_journal_list = []
            portfolio_status_updates_list = []
            if chore_journal is not None:
                chore_journal_list.append(chore_journal)
            if portfolio_status_updates is not None:
                portfolio_status_updates_list.append(portfolio_status_updates)
            container_obj = self.container_model(chore_journals=chore_journal_list,
                                                 chore_snapshots=[chore_snapshot],
                                                 strat_brief=strat_brief,
                                                 portfolio_status_updates=portfolio_status_updates_list)

            strat_id_to_container_obj_dict[strat_id] = container_obj
        return None

    def add_chore_journals(self, chore_journal_list: List[ChoreJournal]):
        run_coro = PostBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_chore_journal_http(
            chore_journal_list)
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"underlying_create_all_chore_journal_http failed "
                              f"with exception: {e}")

    async def create_or_update_strat_brief(self, strat_brief: StratBrief):
        async with StratBrief.reentrant_lock:
            if strat_brief.id not in self.strat_id_to_strat_brief_cache_dict:
                await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_brief_http(
                    strat_brief)
            else:
                await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_brief_http(
                    strat_brief)
            self.strat_id_to_strat_brief_cache_dict[strat_brief.id] = strat_brief

    def update_db(self, chore_journal_list: List[ChoreJournal],
                  chore_snapshot_list: List[ChoreSnapshot],
                  strat_brief: StratBrief):
        # creating chore_journals
        if chore_journal_list:
            self.add_chore_journals(chore_journal_list)

        # creating or updating chore_snapshot
        if chore_snapshot_list:
            run_coro = self.create_or_update_chore_snapshot(chore_snapshot_list)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

            # block for task to finish
            try:
                future.result()
            except HTTPException as http_e:
                logging.exception(f"create_or_update_chore_snapshot failed "
                                  f"with http_exception: {http_e.detail}")
            except Exception as e:
                logging.exception(f"create_or_update_chore_snapshot failed "
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

    def check_max_open_baskets(self, max_open_baskets: int, open_chore_count: int) -> bool:
        pause_all_strats = False

        if max_open_baskets - open_chore_count < 0:
            # this is kept < (less than) and not <= (less than equal) intentionally - this avoids all strat
            # pause on consumable value which is exact same as limit, above limit all strat pause is called

            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(
                f"max_open_baskets breached, allowed {max_open_baskets=}, current {open_chore_count=} - "
                f"initiating all strat pause")
            pause_all_strats = True
        return pause_all_strats

    async def check_rolling_max_chore_count(self, rolling_chore_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_strats = False

        chore_count_updated_chore_journals: List[ChoreJournal] = (
            await PostBookServiceRoutesCallbackBaseNativeOverride.
            underlying_get_last_n_sec_chores_by_events_query_http(rolling_chore_count_period_seconds,
                                                                  [ChoreEventType.OE_NEW]))

        if len(chore_count_updated_chore_journals) == 1:
            rolling_new_chore_count = chore_count_updated_chore_journals[-1].current_period_chore_count
        elif len(chore_count_updated_chore_journals) > 1:
            err_str_ = ("Must receive only one object in list by get_last_n_sec_chores_by_events_query, "
                        f"received {len(chore_count_updated_chore_journals)}, skipping rolling_max_chore_count check, "
                        f"received list: {chore_count_updated_chore_journals}")
            logging.error(err_str_)
            return False
        else:
            rolling_new_chore_count = 0
        if rolling_new_chore_count > max_rolling_tx_count:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"rolling_max_chore_count breached: "
                             f"{chore_count_updated_chore_journals[0].current_period_chore_count} "
                             f"chores in past {rolling_chore_count_period_seconds} secs, allowed chores within this "
                             f"period is {max_rolling_tx_count}, initiating all strat pause")
            pause_all_strats = True
        return pause_all_strats

    async def check_rolling_max_rej_count(self, rolling_rej_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_strats = False

        chore_count_updated_chore_journals: List[ChoreJournal] = (
            await PostBookServiceRoutesCallbackBaseNativeOverride.
            underlying_get_last_n_sec_chores_by_events_query_http(
                rolling_rej_count_period_seconds, [ChoreEventType.OE_BRK_REJ, ChoreEventType.OE_EXH_REJ]))
        if len(chore_count_updated_chore_journals) == 1:
            rolling_rej_chore_count = chore_count_updated_chore_journals[0].current_period_chore_count
        elif len(chore_count_updated_chore_journals) > 0:
            err_str_ = ("Must receive only one object in list from get_last_n_sec_chores_by_events_query, "
                        f"received: {len(chore_count_updated_chore_journals)}, avoiding this check, "
                        f"received list: {chore_count_updated_chore_journals}")
            logging.error(err_str_)
            return False
        else:
            rolling_rej_chore_count = 0

        if rolling_rej_chore_count > max_rolling_tx_count:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_allowed_rejection_within_period breached: "
                             f"{chore_count_updated_chore_journals[0].current_period_chore_count} "
                             f"rejections in past {rolling_rej_count_period_seconds} secs, "
                             f"allowed rejections within this period is {max_rolling_tx_count}"
                             f"- initiating all strat pause")
            pause_all_strats = True
        return pause_all_strats

    async def check_all_portfolio_limits(self) -> bool:
        portfolio_limits = email_book_service_http_client.get_portfolio_limits_client(portfolio_limits_id=1)
        portfolio_status = email_book_service_http_client.get_portfolio_status_client(portfolio_status_id=1)

        pause_all_strats = False

        # Checking portfolio_limits.max_open_baskets
        if portfolio_status.open_chores is not None:
            max_open_baskets_breached = self.check_max_open_baskets(portfolio_limits.max_open_baskets,
                                                                    portfolio_status.open_chores)
            if max_open_baskets_breached:
                pause_all_strats = True
        # else not required: considering None as no open chore is present

        # block for task to finish
        total_buy_open_notional = 0
        total_sell_open_notional = 0
        async with StratBrief.reentrant_lock:
            for strat_brief in self.strat_id_to_strat_brief_cache_dict.values():
                # Buy side check
                total_buy_open_notional += strat_brief.pair_buy_side_bartering_brief.open_notional
                # Sell side check
                total_sell_open_notional += strat_brief.pair_sell_side_bartering_brief.open_notional

        if portfolio_limits.max_open_notional_per_side < total_buy_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_open_notional_per_side breached for BUY side, "
                             f"allowed max_open_notional_per_side: {portfolio_limits.max_open_notional_per_side}, "
                             f"current {total_buy_open_notional=}"
                             f" - initiating all strat pause")
            pause_all_strats = True

        if portfolio_limits.max_open_notional_per_side < total_sell_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_open_notional_per_side breached for SELL side, "
                             f"allowed max_open_notional_per_side: {portfolio_limits.max_open_notional_per_side}, "
                             f"current {total_sell_open_notional=}"
                             f" - initiating all strat pause")
            pause_all_strats = True

        # Checking portfolio_limits.max_gross_n_open_notional
        total_open_notional = total_buy_open_notional + total_sell_open_notional
        total_gross_n_open_notional = (total_open_notional + portfolio_status.overall_buy_fill_notional +
                                       portfolio_status.overall_sell_fill_notional)
        if portfolio_limits.max_gross_n_open_notional < total_gross_n_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_gross_n_open_notional breached, "
                             f"allowed {portfolio_limits.max_gross_n_open_notional=}, "
                             f"current {total_gross_n_open_notional=}"
                             f" - initiating all strat pause")
            pause_all_strats = True

        # Checking portfolio_limits.rolling_max_chore_count
        rolling_max_chore_count_breached: bool = await self.check_rolling_max_chore_count(
            portfolio_limits.rolling_max_chore_count.rolling_tx_count_period_seconds,
            portfolio_limits.rolling_max_chore_count.max_rolling_tx_count)
        if rolling_max_chore_count_breached:
            pause_all_strats = True  # any failure logged in check_rolling_max_chore_count

        # checking portfolio_limits.rolling_max_reject_count
        rolling_max_rej_count_breached: bool = await self.check_rolling_max_rej_count(
            portfolio_limits.rolling_max_reject_count.rolling_tx_count_period_seconds,
            portfolio_limits.rolling_max_reject_count.max_rolling_tx_count)
        if rolling_max_rej_count_breached:
            pause_all_strats = True  # any failure logged in check_rolling_max_chore_count
        return pause_all_strats

    def _portfolio_limit_check_queue_handler(self, strat_id_list: List[int],
                                             strat_id_to_container_obj_dict: Dict[int, ContainerObject]):
        """post pickup form queue - data [list] is now in dict/list"""
        for strat_id in strat_id_list:
            container_object = strat_id_to_container_obj_dict.get(strat_id)
            chore_journal_list = container_object.chore_journals
            chore_snapshot_list = container_object.chore_snapshots
            strat_brief = container_object.strat_brief
            portfolio_status_updates_list = container_object.portfolio_status_updates

            # Updating db
            self.update_db(chore_journal_list, chore_snapshot_list, strat_brief)

            # updating update_portfolio_status_queue - handler gets data and constantly tries
            #                                          to update until gets success
            for portfolio_status_updates in portfolio_status_updates_list:
                self.update_portfolio_status_queue.put(portfolio_status_updates)

    @staticmethod
    def check_connection_or_service_not_ready_error(exception: Exception) -> bool:
        if "Failed to establish a new connection: [Errno 111] Connection refused" in str(exception):
            logging.exception("Connection Error in phone_book server call, likely server is "
                              "down")
        elif "service is not initialized yet" in str(exception):
            logging.exception("phone_book service not up yet, likely server restarted, but is "
                              "not ready yet")
        elif "('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))" in str(exception):
            logging.exception("phone_book service connection error")
        elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
              "it from responding to requests" in str(exception) and "status_code: 503" in str(exception)):
            logging.exception("phone_book service connection error")
        else:
            return False
        return True

    def _update_portfolio_status_vals(self, buy_notional_update, sell_notional_update, buy_fill_notional_update,
                                      sell_fill_notional_update, portfolio_status_updates):
        if portfolio_status_updates.buy_notional_update:
            buy_notional_update += portfolio_status_updates.buy_notional_update
        if portfolio_status_updates.sell_notional_update:
            sell_notional_update += portfolio_status_updates.sell_notional_update
        if portfolio_status_updates.buy_fill_notional_update:
            buy_fill_notional_update += portfolio_status_updates.buy_fill_notional_update
        if portfolio_status_updates.sell_fill_notional_update:
            sell_fill_notional_update += portfolio_status_updates.sell_fill_notional_update
        return buy_notional_update, sell_notional_update, buy_fill_notional_update, sell_fill_notional_update

    def _update_portfolio_status_n_check_portfolio_limits(self):
        while 1:
            buy_notional_update = 0
            sell_notional_update = 0
            buy_fill_notional_update = 0
            sell_fill_notional_update = 0

            counter = 0
            portfolio_status_updates: PortfolioStatusUpdatesContainer = self.update_portfolio_status_queue.get()
            buy_notional_update, sell_notional_update, buy_fill_notional_update, sell_fill_notional_update = (
                self._update_portfolio_status_vals(buy_notional_update, sell_notional_update, buy_fill_notional_update,
                                                   sell_fill_notional_update, portfolio_status_updates))
            counter += 1

            while not self.update_portfolio_status_queue.empty():
                portfolio_status_updates: PortfolioStatusUpdatesContainer = self.update_portfolio_status_queue.get()
                buy_notional_update, sell_notional_update, buy_fill_notional_update, sell_fill_notional_update = (
                    self._update_portfolio_status_vals(buy_notional_update, sell_notional_update,
                                                       buy_fill_notional_update, sell_fill_notional_update,
                                                       portfolio_status_updates))
                counter += 1

            while 1:
                try:
                    email_book_service_http_client.update_portfolio_status_by_chore_or_fill_data_query_client(
                        overall_buy_notional=buy_notional_update,
                        overall_sell_notional=sell_notional_update,
                        overall_buy_fill_notional=buy_fill_notional_update,
                        overall_sell_fill_notional=sell_fill_notional_update,
                        open_chore_count=len(self.chore_id_to_open_chore_snapshot_cache_dict))
                except Exception as e:
                    res = self.check_connection_or_service_not_ready_error(e)  # True if connection or service up error
                    if not res:
                        logging.exception(
                            f"update_portfolio_status_by_chore_or_fill_data_query_client failed with exception: {e}")
                        break
                    else:
                        logging.info("Retrying update_portfolio_status_by_chore_or_fill_data_query_client in 1 sec")
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
                    res = self.check_connection_or_service_not_ready_error(e)  # True if connection or service up error
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
                        email_book_service_http_client.pause_all_active_strats_query_client()
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
                logging.exception("phone_book seems down, returning empty list from "
                                  "is_portfolio_limits_breached_query_pre")
                return []
        else:
            return [IsPortfolioLimitsBreached(is_portfolio_limits_breached=pause_all_strats)]

    def portfolio_limit_check_queue_handler(self):
        post_book_queue_update_limit = config_yaml_dict.get("post_book_queue_update_limit")
        while 1:
            strat_id_list: List[int] = []
            strat_id_to_container_obj_dict: Dict[int, ContainerObject] = {}
            update_counter = 0
            payload_dict: Dict[str, Any] = self.portfolio_limit_check_queue.get()  # blocking call
            self.update_strat_id_list_n_dict_from_payload(strat_id_list,
                                                          strat_id_to_container_obj_dict, payload_dict)
            update_counter += 1

            while not self.portfolio_limit_check_queue.empty():
                payload_dict: Dict[str, Any] = self.portfolio_limit_check_queue.get()
                self.update_strat_id_list_n_dict_from_payload(strat_id_list, strat_id_to_container_obj_dict,
                                                              payload_dict)
                update_counter += 1
                if post_book_queue_update_limit and update_counter >= post_book_queue_update_limit:
                    break

            # Does db operations and checks portfolio_limits and raises all-strat pause if any limit breaches
            self._portfolio_limit_check_queue_handler(strat_id_list, strat_id_to_container_obj_dict)

    async def reload_cache_query_pre(self, reload_cache_class_type: Type[ReloadCache]):
        # clearing cache dict
        self.chore_id_to_chore_snapshot_cache_dict.clear()
        self.chore_id_to_open_chore_snapshot_cache_dict.clear()
        self.strat_id_to_strat_brief_cache_dict.clear()

        chore_snapshot_list: List[ChoreSnapshot] = \
            await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http()
        self._load_existing_chore_snapshot(chore_snapshot_list)

        strat_brief_list: List[StratBrief] = \
            await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http()
        self._load_existing_strat_brief(strat_brief_list)

        return []
