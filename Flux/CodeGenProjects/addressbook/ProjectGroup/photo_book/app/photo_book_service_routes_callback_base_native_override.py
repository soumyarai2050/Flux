# standard imports
import logging
from threading import Thread
import time
import os
import datetime
from queue import Queue
import subprocess
import re

# project imports
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert, submitted_task_result, submit_task_with_first_completed_wait,
    handle_refresh_configurable_data_members)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_routes_msgspec_callback import PhotoBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    handle_patch_db_queue_updater, get_update_obj_list_for_journal_type_update,
    get_update_obj_for_snapshot_type_update, UpdateType, non_existing_obj_read_fail_regex_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import CURRENT_PROJECT_DIR as PAIR_STRAT_ENGINE_DIR


class PhotoBookServiceRoutesCallbackBaseNativeOverride(PhotoBookServiceRoutesCallback):
    underlying_partial_update_all_plan_view_http: Callable[..., Any] | None = None
    underlying_read_plan_view_http: Callable[..., Any] | None = None
    underlying_update_plan_view_http: Callable[..., Any] | None = None
    underlying_process_plan_view_updates_query_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.model_type_name_to_patch_queue_cache_dict: Dict[str, Queue] = {}
        self.max_fetch_from_queue = config_yaml_dict.get("max_fetch_from_patch_queue_for_server")
        if self.max_fetch_from_queue is None:
            self.max_fetch_from_queue = 10  # setting default value

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_http_msgspec_routes import (
            underlying_partial_update_all_plan_view_http, underlying_read_plan_view_http,
            underlying_update_plan_view_http, underlying_process_plan_view_updates_query_http)
        cls.underlying_partial_update_all_plan_view_http = underlying_partial_update_all_plan_view_http
        cls.underlying_read_plan_view_http = underlying_read_plan_view_http
        cls.underlying_update_plan_view_http = underlying_update_plan_view_http
        cls.underlying_process_plan_view_updates_query_http = underlying_process_plan_view_updates_query_http

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
            service_up_flag_env_var = os.environ.get(f"photo_book_{sv_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: plan view engine service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_photo_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
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
        PhotoBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()

        logging.debug("Triggered server launch pre override")
        self.port = sv_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override, killing file_watcher and tail executor processes")

        # Exiting running threads
        for _, queue_ in self.model_type_name_to_patch_queue_cache_dict.items():
            queue_.put("EXIT")

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

    def _plan_view_patch_all_by_async_submit(self, plan_view_list: List[PlanView]):
        try:
            if self.asyncio_loop is not None:
                run_coro = (PhotoBookServiceRoutesCallbackBaseNativeOverride.
                            underlying_partial_update_all_plan_view_http(plan_view_list))
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_partial_update_all_plan_view_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            submitted_task_result(future)

        except Exception as e:
            err_str_ = f"_plan_view_patch_all_by_async_submit failed with exception: {e};;; {plan_view_list=}"
            logging.error(err_str_)
            raise Exception(err_str_)

    async def process_plan_view_updates_query_pre(
            self, process_pair_plan_api_ops_class_type: Type[ProcessPairPlanAPIOps], payload_dict: Dict[str, Any]):
        kwargs = payload_dict.get("kwargs")
        update_type = kwargs.get("update_type")
        basemodel_type_name = kwargs.get("basemodel_type_name")
        method_name = kwargs.get("method_name")
        update_json_list = kwargs.get("update_json_list")

        if method_name == "patch_all_plan_view_client":
            # currently using passed basemodel_type_name only since in patch ultimately json is passed
            # to method_callable so even if BaseModel variant is passed of Model, it will not affect
            method_callable = self._plan_view_patch_all_by_async_submit

            for update_json in update_json_list:
                handle_patch_db_queue_updater(update_type, self.model_type_name_to_patch_queue_cache_dict,
                                              basemodel_type_name, method_name, update_json,
                                              get_update_obj_list_for_journal_type_update,
                                              get_update_obj_for_snapshot_type_update,
                                              method_callable, self.dynamic_queue_handler_err_handler,
                                              self.max_fetch_from_queue, self._snapshot_type_callable_err_handler,
                                              parse_to_model=True)
        else:
            logging.exception(f"Unsupported {method_name=} for process_plan_view_updates_query, currently "
                              f"only supports 'patch_all_plan_view_client';;; {payload_dict=}")
        return []

    def dynamic_queue_handler_err_handler(self, basemodel_type: str, update_type: UpdateType,
                                          err_obj: Exception, pending_updates: List[PlanViewBaseModel]):
        if isinstance(err_obj, HTTPException):
            non_existing_objs_id_list: List[str] = re.findall(non_existing_obj_read_fail_regex_pattern, str(err_obj.detail))
            non_existing_plan_views = []
            if non_existing_objs_id_list:

                for pending_plan_view in pending_updates:
                    if pending_plan_view.id in non_existing_objs_id_list:
                        non_existing_plan_views.append(non_existing_plan_views)
                        pending_updates.remove(pending_plan_view)

                err_str_ = ("Found some plan_view objects which didn't exist while patch-all was called - removing "
                            f"these objects from pending updates to ensure next updates don't fail;;; {non_existing_plan_views=}")
                logging.warning(err_str_)
                return
            # else not required: handling this error as usual way if not of patch-all fail due to non-existing objs

        err_str_brief = (f"handle_dynamic_queue_for_patch running for basemodel_type: "
                         f"{basemodel_type} and update_type: {update_type} failed")
        err_str_detail = f"exception: {err_obj}, {pending_updates=}"
        logging.exception(f"{err_str_brief};;; {err_str_detail}")

    def _snapshot_type_callable_err_handler(self, basemodel_class_type: Type[MsgspecBaseModel], kwargs):
        err_str_brief = ("Can't find _id key in patch kwargs dict - ignoring this update in "
                         "get_update_obj_for_snapshot_type_update, "
                         f"basemodel_class_type: {basemodel_class_type.__name__}, "
                         f"{kwargs = }")
        logging.exception(f"{err_str_brief}")

    async def reset_all_plan_view_count_n_severity_query_pre(
            self, reset_all_plan_view_count_n_severity_class_type: Type[ResetAllPlanViewCountNSeverity]):
        plan_view_list: List[PlanView] = \
            await PhotoBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_view_http()

        tasks: List = []
        for plan_view in plan_view_list:
            plan_view.plan_alert_aggregated_severity = Severity.Severity_UNSPECIFIED
            plan_view.plan_alert_count = 0

            task = asyncio.create_task(
                PhotoBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_view_http(
                    plan_view),
                name=str(f"{plan_view.id}"))
            tasks.append(task)

        if tasks:
            await submit_task_with_first_completed_wait(tasks, 10)
        return []

    async def _update_plan_view_post(self, stored_plan_view_obj: PlanView | Dict,
                                      updated_plan_view_obj: PlanView | Dict):
        if isinstance(stored_plan_view_obj, dict):
            obj_id = stored_plan_view_obj.get("_id")
            stored_unload_plan = stored_plan_view_obj.get("unload_plan")
            stored_recycle_plan = stored_plan_view_obj.get("recycle_plan")
        else:
            obj_id = stored_plan_view_obj.id
            stored_unload_plan = stored_plan_view_obj.unload_plan
            stored_recycle_plan = stored_plan_view_obj.recycle_plan

        if isinstance(updated_plan_view_obj, dict):
            updated_unload_plan = updated_plan_view_obj.get("unload_plan")
            updated_recycle_plan = updated_plan_view_obj.get("recycle_plan")
        else:
            updated_unload_plan = updated_plan_view_obj.unload_plan
            updated_recycle_plan = updated_plan_view_obj.recycle_plan

        if not stored_unload_plan and updated_unload_plan:
            script_path: str = str(PAIR_STRAT_ENGINE_DIR / "pyscripts" / "unload_plan.py")
            cmd: List[str] = ["python", script_path, f"{obj_id}", "--force", "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered unload event for plan_id={obj_id} at {DateTime.utcnow()};;;"
                            f"{cmd=}, {launcher=}")
        if not stored_recycle_plan and updated_recycle_plan:
            script_path: str = str(PAIR_STRAT_ENGINE_DIR / "pyscripts" / "recycle_plan.py")
            cmd: List[str] = ["python", script_path, f"{obj_id}", "--force", "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered recycle event for plan_id={obj_id} at {DateTime.utcnow()};;;"
                            f"{cmd=}, {launcher=}")

    async def update_plan_view_post(self, stored_plan_view_obj: PlanView, updated_plan_view_obj: PlanView):
        await self._update_plan_view_post(stored_plan_view_obj, updated_plan_view_obj)

    async def partial_update_plan_view_post(self, stored_plan_view_obj_json: Dict[str, Any],
                                             updated_plan_view_obj_json: Dict[str, Any]):
        await self._update_plan_view_post(stored_plan_view_obj_json, updated_plan_view_obj_json)

    async def partial_update_all_plan_view_post(self, stored_plan_view_dict_list: List[Dict[str, Any]],
                                                 updated_plan_view_dict_list: List[Dict[str, Any]]):
        tasks: List = []
        for idx, updated_plan_view_obj in enumerate(updated_plan_view_dict_list):

            task = asyncio.create_task(
                self._update_plan_view_post(stored_plan_view_dict_list[idx], updated_plan_view_obj),
                name=f"{str(updated_plan_view_obj.get('_id'))}")
            tasks.append(task)

        if tasks:
            await submit_task_with_first_completed_wait(tasks, 10)

    async def handle_plan_view_updates_query_pre(
            self, handle_plan_view_update_class_type: Type[HandlePlanViewUpdate], payload: List[Dict[str, Any]]):

        for log_data in payload:
            message = log_data.get("message")
            message: str = message[len("^^^"):]
            args: List[str] = message.split("~~")
            basemodel_type_name: str = args.pop(0)
            update_type: str = args.pop(0)
            method_name: str = args.pop(0)

            # kwargs_list = []
            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by key_val_sep if any
            for arg in args:
                key, value = arg.split("^^")
                kwargs[key] = value
                # kwargs_list.append({key: value})

            data = {"kwargs": {"update_type": update_type, "basemodel_type_name": basemodel_type_name,
                               "method_name": method_name, "update_json_list": [kwargs]}}

            await PhotoBookServiceRoutesCallbackBaseNativeOverride.underlying_process_plan_view_updates_query_http(data)
        return []
