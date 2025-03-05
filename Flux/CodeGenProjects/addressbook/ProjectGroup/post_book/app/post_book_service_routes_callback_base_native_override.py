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
import datetime

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.FastApi.post_book_service_routes_msgspec_callback import (
    PostBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from FluxPythonUtils.scripts.general_utility_functions import except_n_log_alert, handle_refresh_configurable_data_members
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.aggregate import (
    get_open_chore_counts, get_last_n_sec_chores_by_events)


MsgspecType = TypeVar('MsgspecType', bound=msgspec.Struct)


class ContainerObject(msgspec.Struct, kw_only=True):
    chore_journals: List[ChoreJournal]
    chore_snapshots: List[ChoreSnapshot]
    plan_brief: PlanBrief | None = None
    contact_status_updates: List[ContactStatusUpdatesContainer]


class PostBookServiceRoutesCallbackBaseNativeOverride(PostBookServiceRoutesCallback):
    underlying_read_chore_journal_http: Callable[..., Any] | None = None
    underlying_read_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_update_all_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_create_all_chore_journal_http: Callable[..., Any] | None = None
    underlying_read_plan_brief_http: Callable[..., Any] | None = None
    underlying_create_plan_brief_http: Callable[..., Any] | None = None
    underlying_update_plan_brief_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_chores_by_events_query_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.FastApi.post_book_service_http_routes_imports import (
            underlying_read_chore_journal_http, underlying_read_chore_snapshot_http,
            underlying_create_all_chore_snapshot_http, underlying_update_all_chore_snapshot_http,
            underlying_create_all_chore_journal_http, underlying_read_plan_brief_http,
            underlying_create_plan_brief_http, underlying_update_plan_brief_http,
            underlying_get_last_n_sec_chores_by_events_query_http)
        cls.underlying_read_chore_journal_http = underlying_read_chore_journal_http
        cls.underlying_read_chore_snapshot_http = underlying_read_chore_snapshot_http
        cls.underlying_create_all_chore_snapshot_http = underlying_create_all_chore_snapshot_http
        cls.underlying_update_all_chore_snapshot_http = underlying_update_all_chore_snapshot_http
        cls.underlying_create_all_chore_journal_http = underlying_create_all_chore_journal_http
        cls.underlying_read_plan_brief_http = underlying_read_plan_brief_http
        cls.underlying_create_plan_brief_http = underlying_create_plan_brief_http
        cls.underlying_update_plan_brief_http = underlying_update_plan_brief_http
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
        self.contact_limit_check_queue: Queue = Queue()
        self.update_contact_status_queue: Queue = Queue()
        self.container_model: MsgspecType = ContainerObject
        self.chore_id_to_chore_snapshot_cache_dict: Dict[str, ChoreSnapshot] = {}
        self.chore_id_to_open_chore_snapshot_cache_dict: Dict[str, ChoreSnapshot] = {}
        self.plan_id_to_plan_brief_cache_dict: Dict[int, PlanBrief] = {}

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
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
                        # Updating chore_snapshot cache and plan_brief cache
                        self.load_existing_chore_snapshot()
                        self.load_existing_plan_brief()

                        # Running contact_limit_check_queue_handler
                        Thread(target=self.contact_limit_check_queue_handler, daemon=True).start()
                        Thread(target=self._update_contact_status_n_check_contact_limits, daemon=True).start()
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
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

    async def create_plan_brief_pre(self, plan_brief_obj: PlanBrief):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_plan_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

    async def update_plan_brief_pre(self, updated_plan_brief_obj: PlanBrief):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_plan_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        return updated_plan_brief_obj

    async def partial_update_plan_brief_pre(self, stored_plan_brief_obj: PlanBrief,
                                             updated_plan_brief_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "partial_update_plan_brief_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)
        return updated_plan_brief_obj_json

    async def check_contact_limits_query_pre(self, check_contact_limits_class_type: Type[CheckContactLimits],
                                               payload_dict: Dict[str, Any]):
        self.contact_limit_check_queue.put(payload_dict)
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

    def load_existing_plan_brief(self):
        run_coro = (
            PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_brief_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            plan_brief_list: List[PlanBrief] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_plan_brief_http failed - ignoring cache load of plan_brief "
                              f"from db, exception: {e}")
            return None

        # Setting cache data member
        self._load_existing_plan_brief(plan_brief_list)

    def _load_existing_plan_brief(self, plan_brief_list: List[PlanBrief]):
        for plan_brief in plan_brief_list:
            self.plan_id_to_plan_brief_cache_dict[plan_brief.id] = plan_brief

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

    def _get_plan_brief_from_payload(self, payload_dict: Dict[str, Any]):
        plan_brief: PlanBrief | None = None
        if (plan_brief_dict := payload_dict.get("plan_brief")) is not None:
            # _id override for plan brief is not required since it will have same id as
            # it's respective executor plan_id, so it will be unique here too
            plan_brief = PlanBrief.from_dict(plan_brief_dict)
        return plan_brief

    def _get_contact_status_updates_from_payload(self, payload_dict: Dict[str, Any]):
        contact_status_updates: ContactStatusUpdatesContainer | None = None
        if (contact_status_updates_dict := payload_dict.get("contact_status_updates")) is not None:
            contact_status_updates = ContactStatusUpdatesContainer.from_dict(contact_status_updates_dict)
        return contact_status_updates

    def update_plan_id_list_n_dict_from_payload(self, plan_id_list: List[int],
                                                 plan_id_to_container_obj_dict: Dict[int, ContainerObject],
                                                 payload_dict: Dict[str, Any]):
        """
        updates plan_id_to_container_obj_dict param - returns None
        """
        plan_id = payload_dict.get("plan_id")
        if plan_id is None:
            logging.error("Payload doesn't contain plan_id, might be a bug at queue updater, "
                          f"ignoring this update, payload_received in queue: {payload_dict}")
            return None

        added_id: bool = False
        if plan_id not in plan_id_list:
            added_id = True
            plan_id_list.append(plan_id)

        chore_journal: ChoreJournal | None = self._get_chore_journal_from_payload(payload_dict)

        chore_snapshot: ChoreSnapshot | None = self._get_chore_snapshot_from_payload(payload_dict)
        if chore_snapshot is None:
            logging.error("Payload doesn't contain chore_snapshot, might be a bug at queue updater, "
                          f"ignoring this update, payload_received in queue: {payload_dict}")

            # rollback plan_id_list if id was added in this call
            if added_id:
                plan_id_list.remove(plan_id)
            return None

        plan_brief: PlanBrief | None = self._get_plan_brief_from_payload(payload_dict)
        contact_status_updates: ContactStatusUpdatesContainer | None = (
            self._get_contact_status_updates_from_payload(payload_dict))

        container_obj: ContainerObject = plan_id_to_container_obj_dict.get(plan_id)
        if container_obj is not None:
            if chore_journal is not None:
                container_obj.chore_journals.append(chore_journal)
            container_obj.chore_snapshots.append(chore_snapshot)
            if plan_brief is not None:
                container_obj.plan_brief = plan_brief
            if contact_status_updates is not None:
                container_obj.contact_status_updates.append(contact_status_updates)
        else:
            chore_journal_list = []
            contact_status_updates_list = []
            if chore_journal is not None:
                chore_journal_list.append(chore_journal)
            if contact_status_updates is not None:
                contact_status_updates_list.append(contact_status_updates)
            container_obj = self.container_model(chore_journals=chore_journal_list,
                                                 chore_snapshots=[chore_snapshot],
                                                 plan_brief=plan_brief,
                                                 contact_status_updates=contact_status_updates_list)

            plan_id_to_container_obj_dict[plan_id] = container_obj
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

    async def create_or_update_plan_brief(self, plan_brief: PlanBrief):
        async with PlanBrief.reentrant_lock:
            if plan_brief.id not in self.plan_id_to_plan_brief_cache_dict:
                await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_create_plan_brief_http(
                    plan_brief)
            else:
                await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_brief_http(
                    plan_brief)
            self.plan_id_to_plan_brief_cache_dict[plan_brief.id] = plan_brief

    def update_db(self, chore_journal_list: List[ChoreJournal],
                  chore_snapshot_list: List[ChoreSnapshot],
                  plan_brief: PlanBrief):
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

        # creating or updating plan_brief
        if plan_brief is not None:
            run_coro = self.create_or_update_plan_brief(plan_brief)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"create_or_update_plan_brief failed "
                                  f"with exception: {e}")

    def check_max_open_baskets(self, max_open_baskets: int, open_chore_count: int) -> bool:
        pause_all_plans = False

        if max_open_baskets - open_chore_count < 0:
            # this is kept < (less than) and not <= (less than equal) intentionally - this avoids all plan
            # pause on consumable value which is exact same as limit, above limit all plan pause is called

            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(
                f"max_open_baskets breached, allowed {max_open_baskets=}, current {open_chore_count=} - "
                f"initiating all plan pause")
            pause_all_plans = True
        return pause_all_plans

    async def check_rolling_max_chore_count(self, rolling_chore_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_plans = False

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
                             f"period is {max_rolling_tx_count}, initiating all plan pause")
            pause_all_plans = True
        return pause_all_plans

    async def check_rolling_max_rej_count(self, rolling_rej_count_period_seconds: int, max_rolling_tx_count: int):
        pause_all_plans = False

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
                             f"- initiating all plan pause")
            pause_all_plans = True
        return pause_all_plans

    async def check_all_contact_limits(self) -> bool:
        contact_limits = email_book_service_http_client.get_contact_limits_client(contact_limits_id=1)
        contact_status = email_book_service_http_client.get_contact_status_client(contact_status_id=1)

        pause_all_plans = False

        # Checking contact_limits.max_open_baskets
        if contact_status.open_chores is not None:
            max_open_baskets_breached = self.check_max_open_baskets(contact_limits.max_open_baskets,
                                                                    contact_status.open_chores)
            if max_open_baskets_breached:
                pause_all_plans = True
        # else not required: considering None as no open chore is present

        # block for task to finish
        total_buy_open_notional = 0
        total_sell_open_notional = 0
        async with PlanBrief.reentrant_lock:
            for plan_brief in self.plan_id_to_plan_brief_cache_dict.values():
                # Buy side check
                total_buy_open_notional += plan_brief.pair_buy_side_bartering_brief.open_notional
                # Sell side check
                total_sell_open_notional += plan_brief.pair_sell_side_bartering_brief.open_notional

        if contact_limits.max_open_notional_per_side < total_buy_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_open_notional_per_side breached for BUY side, "
                             f"allowed max_open_notional_per_side: {contact_limits.max_open_notional_per_side}, "
                             f"current {total_buy_open_notional=}"
                             f" - initiating all plan pause")
            pause_all_plans = True

        if contact_limits.max_open_notional_per_side < total_sell_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_open_notional_per_side breached for SELL side, "
                             f"allowed max_open_notional_per_side: {contact_limits.max_open_notional_per_side}, "
                             f"current {total_sell_open_notional=}"
                             f" - initiating all plan pause")
            pause_all_plans = True

        # Checking contact_limits.max_gross_n_open_notional
        total_open_notional = total_buy_open_notional + total_sell_open_notional
        total_gross_n_open_notional = (total_open_notional + contact_status.overall_buy_fill_notional +
                                       contact_status.overall_sell_fill_notional)
        if contact_limits.max_gross_n_open_notional < total_gross_n_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.critical(f"max_gross_n_open_notional breached, "
                             f"allowed {contact_limits.max_gross_n_open_notional=}, "
                             f"current {total_gross_n_open_notional=}"
                             f" - initiating all plan pause")
            pause_all_plans = True

        # Checking contact_limits.rolling_max_chore_count
        rolling_max_chore_count_breached: bool = await self.check_rolling_max_chore_count(
            contact_limits.rolling_max_chore_count.rolling_tx_count_period_seconds,
            contact_limits.rolling_max_chore_count.max_rolling_tx_count)
        if rolling_max_chore_count_breached:
            pause_all_plans = True  # any failure logged in check_rolling_max_chore_count

        # checking contact_limits.rolling_max_reject_count
        rolling_max_rej_count_breached: bool = await self.check_rolling_max_rej_count(
            contact_limits.rolling_max_reject_count.rolling_tx_count_period_seconds,
            contact_limits.rolling_max_reject_count.max_rolling_tx_count)
        if rolling_max_rej_count_breached:
            pause_all_plans = True  # any failure logged in check_rolling_max_rej_count
        return pause_all_plans

    def _contact_limit_check_queue_handler(self, plan_id_list: List[int],
                                             plan_id_to_container_obj_dict: Dict[int, ContainerObject]):
        """post pickup form queue - data [list] is now in dict/list"""
        for plan_id in plan_id_list:
            container_object = plan_id_to_container_obj_dict.get(plan_id)
            chore_journal_list = container_object.chore_journals
            chore_snapshot_list = container_object.chore_snapshots
            plan_brief = container_object.plan_brief
            contact_status_updates_list = container_object.contact_status_updates

            # Updating db
            self.update_db(chore_journal_list, chore_snapshot_list, plan_brief)

            # updating update_contact_status_queue - handler gets data and constantly tries
            #                                          to update until gets success
            for contact_status_updates in contact_status_updates_list:
                self.update_contact_status_queue.put(contact_status_updates)

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

    def _update_contact_status_vals(self, buy_notional_update, sell_notional_update, buy_fill_notional_update,
                                      sell_fill_notional_update, contact_status_updates):
        if contact_status_updates.buy_notional_update:
            buy_notional_update += contact_status_updates.buy_notional_update
        if contact_status_updates.sell_notional_update:
            sell_notional_update += contact_status_updates.sell_notional_update
        if contact_status_updates.buy_fill_notional_update:
            buy_fill_notional_update += contact_status_updates.buy_fill_notional_update
        if contact_status_updates.sell_fill_notional_update:
            sell_fill_notional_update += contact_status_updates.sell_fill_notional_update
        return buy_notional_update, sell_notional_update, buy_fill_notional_update, sell_fill_notional_update

    def _update_contact_status_n_check_contact_limits(self):
        while 1:
            buy_notional_update = 0
            sell_notional_update = 0
            buy_fill_notional_update = 0
            sell_fill_notional_update = 0

            counter = 0
            contact_status_updates: ContactStatusUpdatesContainer = self.update_contact_status_queue.get()
            buy_notional_update, sell_notional_update, buy_fill_notional_update, sell_fill_notional_update = (
                self._update_contact_status_vals(buy_notional_update, sell_notional_update, buy_fill_notional_update,
                                                   sell_fill_notional_update, contact_status_updates))
            counter += 1

            while not self.update_contact_status_queue.empty():
                contact_status_updates: ContactStatusUpdatesContainer = self.update_contact_status_queue.get()
                buy_notional_update, sell_notional_update, buy_fill_notional_update, sell_fill_notional_update = (
                    self._update_contact_status_vals(buy_notional_update, sell_notional_update,
                                                       buy_fill_notional_update, sell_fill_notional_update,
                                                       contact_status_updates))
                counter += 1

            while 1:
                try:
                    email_book_service_http_client.update_contact_status_by_chore_or_fill_data_query_client(
                        overall_buy_notional=buy_notional_update,
                        overall_sell_notional=sell_notional_update,
                        overall_buy_fill_notional=buy_fill_notional_update,
                        overall_sell_fill_notional=sell_fill_notional_update,
                        open_chore_count=len(self.chore_id_to_open_chore_snapshot_cache_dict))
                except Exception as e:
                    res = self.check_connection_or_service_not_ready_error(e)  # True if connection or service up error
                    if not res:
                        logging.exception(
                            f"update_contact_status_by_chore_or_fill_data_query_client failed with exception: {e}")
                        break
                    else:
                        logging.info("Retrying update_contact_status_by_chore_or_fill_data_query_client in 1 sec")
                        time.sleep(1)
                else:
                    break

            while 1:
                # Checking Contact limits and Pausing ALL Plans if limit found breached
                run_coro = self.check_all_contact_limits()
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                # block for task to finish
                try:
                    pause_all_plans: bool = future.result()
                except Exception as e:
                    res = self.check_connection_or_service_not_ready_error(e)  # True if connection or service up error
                    if not res:
                        logging.exception(f"check_all_contact_limits failed, exception: {e}")
                        return None
                    else:
                        logging.info("Retrying check_all_contact_limits in 1 sec")
                        time.sleep(1)
                else:
                    break
            if pause_all_plans:
                while 1:
                    try:
                        email_book_service_http_client.pause_all_active_plans_query_client()
                    except Exception as e:
                        # True if connection or service up error
                        res = self.check_connection_or_service_not_ready_error(e)
                        if not res:
                            logging.exception(
                                f"pause_all_active_plans_query_client failed with exception {e}")
                            break
                        else:
                            logging.info("Retrying pause_all_active_plans_query_client in 1 sec")
                            time.sleep(1)
                    else:
                        break

    async def is_contact_limits_breached_query_pre(
            self, is_contact_limits_breached_class_type: Type[IsContactLimitsBreached]):
        """
        :return: returns empty list if exception occurs
        """
        try:
            pause_all_plans = await self.check_all_contact_limits()
        except Exception as e:
            # True if connection or service up error
            res = self.check_connection_or_service_not_ready_error(e)
            if res:
                logging.exception("phone_book seems down, returning empty list from "
                                  "is_contact_limits_breached_query_pre")
                return []
        else:
            return [IsContactLimitsBreached(is_contact_limits_breached=pause_all_plans)]

    def contact_limit_check_queue_handler(self):
        post_book_queue_update_limit = config_yaml_dict.get("post_book_queue_update_limit")
        while 1:
            plan_id_list: List[int] = []
            plan_id_to_container_obj_dict: Dict[int, ContainerObject] = {}
            update_counter = 0
            payload_dict: Dict[str, Any] = self.contact_limit_check_queue.get()  # blocking call
            self.update_plan_id_list_n_dict_from_payload(plan_id_list,
                                                          plan_id_to_container_obj_dict, payload_dict)
            update_counter += 1

            while not self.contact_limit_check_queue.empty():
                payload_dict: Dict[str, Any] = self.contact_limit_check_queue.get()
                self.update_plan_id_list_n_dict_from_payload(plan_id_list, plan_id_to_container_obj_dict,
                                                              payload_dict)
                update_counter += 1
                if post_book_queue_update_limit and update_counter >= post_book_queue_update_limit:
                    break

            # Does db operations and checks contact_limits and raises all-plan pause if any limit breaches
            self._contact_limit_check_queue_handler(plan_id_list, plan_id_to_container_obj_dict)

    async def reload_cache_query_pre(self, reload_cache_class_type: Type[ReloadCache]):
        # clearing cache dict
        self.chore_id_to_chore_snapshot_cache_dict.clear()
        self.chore_id_to_open_chore_snapshot_cache_dict.clear()
        self.plan_id_to_plan_brief_cache_dict.clear()

        chore_snapshot_list: List[ChoreSnapshot] = \
            await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http()
        self._load_existing_chore_snapshot(chore_snapshot_list)

        plan_brief_list: List[PlanBrief] = \
            await PostBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_brief_http()
        self._load_existing_plan_brief(plan_brief_list)

        return []
