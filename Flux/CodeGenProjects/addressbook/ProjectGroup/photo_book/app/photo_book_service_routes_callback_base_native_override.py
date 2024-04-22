# standard imports
import logging
from threading import Thread
import time
import os
import datetime
from queue import Queue

# project imports
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_routes_callback import PhotoBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    handle_patch_db_queue_updater, get_update_obj_list_for_journal_type_update,
    get_update_obj_for_snapshot_type_update, UpdateType)


class PhotoBookServiceRoutesCallbackBaseNativeOverride(PhotoBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
        self.asyncio_loop = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.pydantic_type_name_to_patch_queue_cache_dict: Dict[str, Queue] = {}
        self.max_fetch_from_queue = config_yaml_dict.get("max_fetch_from_patch_queue_for_server")
        if self.max_fetch_from_queue is None:
            self.max_fetch_from_queue = 10  # setting default value

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
            service_up_flag_env_var = os.environ.get(f"photo_book_{sv_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                    print(f"INFO: service is ready: {datetime.datetime.now().time()}")

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
            else:
                should_sleep = True

    def app_launch_pre(self):
        # PhotoBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()

        logging.debug("Triggered server launch pre override")
        self.port = sv_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override, killing file_watcher and tail executor processes")

        # Exiting running threads
        for _, queue_ in self.pydantic_type_name_to_patch_queue_cache_dict.items():
            queue_.put("EXIT")

    async def process_strat_view_updates_query_pre(
            self, process_pair_strat_api_ops_class_type: Type[ProcessPairStratAPIOps], payload_dict: Dict[str, Any]):
        kwargs = payload_dict.get("kwargs")
        update_type = kwargs.get("update_type")
        pydantic_basemodel_type_name = kwargs.get("pydantic_basemodel_type_name")
        method_name = kwargs.get("method_name")
        update_json_list = kwargs.get("update_json_list")

        method_callable = getattr(email_book_service_http_client, method_name)

        for update_json in update_json_list:
            handle_patch_db_queue_updater(update_type, self.pydantic_type_name_to_patch_queue_cache_dict,
                                          pydantic_basemodel_type_name, method_name, update_json,
                                          get_update_obj_list_for_journal_type_update,
                                          get_update_obj_for_snapshot_type_update,
                                          method_callable, self.dynamic_queue_handler_err_handler,
                                          self.max_fetch_from_queue, self._snapshot_type_callable_err_handler,
                                          parse_to_pydantic=True)
        return []

    def dynamic_queue_handler_err_handler(self, pydantic_basemodel_type: str, update_type: UpdateType,
                                          err_str_: Exception):
        err_str_brief = (f"handle_dynamic_queue_for_patch running for pydantic_basemodel_type: "
                         f"{pydantic_basemodel_type} and update_type: {update_type} failed")
        err_str_detail = f"exception: {err_str_}"
        logging.exception(f"{err_str_brief};;; {err_str_detail}")

    def _snapshot_type_callable_err_handler(self, pydantic_basemodel_class_type: Type[BaseModel], kwargs):
        err_str_brief = ("Can't find _id key in patch kwargs dict - ignoring this update in "
                         "get_update_obj_for_snapshot_type_update, "
                         f"pydantic_basemodel_class_type: {pydantic_basemodel_class_type.__name__}, "
                         f"{kwargs = }")
        logging.exception(f"{err_str_brief}")
