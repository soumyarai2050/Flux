# project imports
from typing import Type, Callable

from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.ORMModel.log_book_service_model_imports import *
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int, is_first_param_list_type)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_client import (
    LogBookServiceHttpClient)

# standard imports
import datetime
import logging
import time
import queue
from threading import Thread, current_thread
import re
import threading

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_LOG_DIR = PurePath(__file__).parent.parent / "log"

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

la_host, la_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))
la_view_port = parse_to_int(config_yaml_dict.get("view_port"))

log_book_service_http_view_client = \
    LogBookServiceHttpClient.set_or_get_if_instance_exists(la_host, la_port, view_port=la_view_port)
log_book_service_http_main_client = \
    LogBookServiceHttpClient.set_or_get_if_instance_exists(la_host, la_port)

if config_yaml_dict.get("use_view_clients"):
    log_book_service_http_client = log_book_service_http_view_client
else:
    log_book_service_http_client = log_book_service_http_main_client

datetime_str = datetime.datetime.now().strftime("%Y%m%d")
contact_alert_fail_log = f"contact_alert_fail_logs_{datetime_str}.log"
simulator_contact_alert_fail_log = f"simulator_contact_alert_fail_logs_{datetime_str}.log"

# pattern to find non-existing ids of objects which were not found while patch-all
non_existing_obj_read_fail_regex_pattern: Final[str] = r".*objects with ids: \{(.*?)\} out of requested .*"


class UpdateType(StrEnum):
    JOURNAL_TYPE = auto()
    SNAPSHOT_TYPE = auto()


class AlertsCacheCont(MsgspecBaseModel, kw_only=True):
    name: str | None = None
    re_mutex: AsyncRLock = field(default_factory=AsyncRLock)
    alert_id_to_obj_dict: Dict = field(default_factory=dict)
    create_alert_obj_dict: Dict = field(default_factory=dict)   # temporary field: used in alert_queue_handler
    update_alert_obj_dict: Dict = field(default_factory=dict)   # temporary field: used in alert_queue_handler


def create_alert(
        plan_alert_type: Type[PlanAlert],
        contact_alert_type: Type[ContactAlert],
        alert_brief: str, severity: Severity = Severity.Severity_ERROR, plan_id: int | None = None,
        alert_meta: AlertMeta | None = None) -> PlanAlert | ContactAlert:
    """
    Handles plan alerts if plan id is passed else handles contact alerts
    """
    kwargs = {}
    kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False,
                  last_update_analyzer_time=DateTime.utcnow(), alert_count=1)
    if alert_meta:
        kwargs['alert_meta'] = alert_meta
    if plan_id is not None:
        kwargs["plan_id"] = plan_id
        start_alert = plan_alert_type.from_dict(kwargs)
        if hasattr(plan_alert_type, "next_id"):
            # used in server process since db is initialized in that process -
            # putting id so that object can be cached with id - to avoid put http with cached obj without id
            start_alert.id = plan_alert_type.next_id()
        return start_alert
    else:
        contact_alert = contact_alert_type.from_dict(kwargs)
        if hasattr(contact_alert_type, "next_id"):
            # used in server process since db is initialized in that process -
            # putting id so that object can be cached with id - to avoid put http with cached obj without id
            contact_alert.id = contact_alert_type.next_id()
        return contact_alert


def is_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            log_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def is_view_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            log_book_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def init_service(contact_alerts_cache: Dict[str, ContactAlertBaseModel]) -> bool:
    if is_log_book_service_up(ignore_error=True):
        try:
            # block for task to finish
            contact_alert_list: List[ContactAlertBaseModel] = (
                log_book_service_http_client.get_all_contact_alert_client())  # returns list - empty or with objs

        except Exception as e:
            err_str_ = f"get_all_contact_alert_client failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

        for contact_alert in contact_alert_list:
            component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
            alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                            component_file_path, source_file_name, line_num)
            contact_alerts_cache[alert_key] = contact_alert
        return True
    return False


def get_severity_type_from_severity_str(severity_str: str) -> Severity:
    return Severity[severity_str]


def get_pattern_to_restart_tail_process():
    pattern = config_yaml_dict.get("pattern_to_restart_tail_process")
    if pattern is None:
        pattern = "---"
    return pattern


def get_pattern_to_force_kill_tail_process():
    pattern = config_yaml_dict.get("pattern_to_force_kill_tail_process")
    if pattern is None:
        pattern = "-@-"
    return pattern


def get_pattern_to_remove_file_from_created_cache():
    pattern = config_yaml_dict.get("pattern_to_remove_file_from_created_cache")
    if pattern is None:
        pattern = "-*-"
    return pattern


def get_pattern_for_plan_view_db_updates():
    pattern = config_yaml_dict.get("pattern_for_plan_view_db_updates")
    if pattern is None:
        pattern = "^^^"
    return pattern


def get_pattern_for_pair_plan_db_updates():
    pattern = config_yaml_dict.get("pattern_for_pair_plan_db_updates")
    if pattern is None:
        pattern = "^*^"
    return pattern


def get_pattern_for_log_simulator():
    pattern = config_yaml_dict.get("pattern_for_log_simulator")
    if pattern is None:
        pattern = "$$$"
    return pattern


def get_field_seperator_pattern():
    pattern = config_yaml_dict.get("field_seperator")
    if pattern is None:
        pattern = "~~"
    return pattern


def get_key_val_seperator_pattern():
    pattern = config_yaml_dict.get("key_val_seperator")
    if pattern is None:
        pattern = "^^"
    return pattern


def should_retry_due_to_server_down(exception: Exception) -> bool:
    if "Failed to establish a new connection: [Errno 111] Connection refused" in str(exception):
        logging.exception("Connection Error in phone_book server call, "
                          "likely server is down, retrying call ...")
        time.sleep(1)
    elif "service is not initialized yet" in str(exception):
        # Check is server up
        logging.exception("phone_book service not up yet, likely server "
                          "restarted but is not ready yet, retrying call ...")
        time.sleep(1)
    elif ("('Connection aborted.', ConnectionResetError(104, 'Connection reset "
          "by peer'))") in str(exception):
        logging.exception(
            "phone_book service connection error, retrying call ...")
        time.sleep(1)
    else:
        return False
    return True


def get_update_obj_list_for_ledger_type_update(
        basemodel_class_type: Type[MsgspecBaseModel], update_type: str, method_name: str, patch_queue: queue.Queue,
        max_fetch_from_queue: int, update_dict_list: List[MsgspecModel | Dict],
        parse_to_model: bool | None = None) -> List[Dict] | str:  # blocking function
    fetch_counts: int = 0

    kwargs: Dict = patch_queue.get()
    fetch_counts += 1

    # handling thread exit
    if kwargs == "EXIT":
        logging.info(f"Exiting get_update_obj_list_for_ledger_type_update")
        return "EXIT"

    if parse_to_model:
        basemodel_object = basemodel_class_type.from_dict(kwargs, strict=False)
        update_dict_list.append(basemodel_object.to_dict(exclude_none=True))
    else:
        update_dict_list.append(kwargs)

    while not patch_queue.empty():
        kwargs: Dict = patch_queue.get()
        fetch_counts += 1

        # handling thread exit
        if kwargs == "EXIT":
            logging.info(f"Exiting get_update_obj_list_for_ledger_type_update")
            return "EXIT"

        if parse_to_model:
            basemodel_object = basemodel_class_type.from_dict(kwargs, strict=False)
            update_dict_list.append(basemodel_object.to_dict(exclude_none=True))
        else:
            update_dict_list.append(kwargs)

        if fetch_counts >= max_fetch_from_queue:
            return update_dict_list
    return update_dict_list


def get_obj_id_to_put_as_key(obj_id) -> str:
    # type-casting to str to avoid duplicate key generation if obj_id is of varying types like str and int - this
    # happens when obj are passed from logs and direct json calls, due to which obj_id is str in logs case and
    # specific type like int for direct json call cases
    return str(obj_id)


def get_update_obj_for_snapshot_type_update(
        msgspec_class_type: Type[MsgspecBaseModel], update_type: str, method_name: str, patch_queue: queue.Queue,
        max_fetch_from_queue: int, err_handler_callable: Callable, pending_updates: List[Dict],
        parse_to_msgspec_obj: bool | None = None) -> List[Dict] | List[MsgspecModel] | str:  # blocking function
    id_to_obj_dict = {}
    if pending_updates:
        # adding pending updates to dict that will be used to return from this function - avoids any pending updates
        # to be missed
        if parse_to_msgspec_obj:
            for snapshot_obj_dict in pending_updates:
                msgspec_object = msgspec_class_type.from_dict(snapshot_obj_dict, strict=False)
                obj_id = get_obj_id_to_put_as_key(msgspec_object.id)
                id_to_obj_dict[obj_id] = msgspec_object
        else:
            for snapshot_obj_dict in pending_updates:
                obj_id = get_obj_id_to_put_as_key(snapshot_obj_dict.get('_id'))
                id_to_obj_dict[obj_id] = snapshot_obj_dict

    # else not required: if no snapshot exists already to be send through client then nothing to add in id_to_obj_dict

    fetch_counts: int = 0

    kwargs: Dict = patch_queue.get()
    fetch_counts += 1

    # handling thread exit
    if kwargs == "EXIT":
        logging.info(f"Exiting get_update_obj_for_snapshot_type_update")
        return "EXIT"

    # _id from the kwargs dict is of string type which may or may not be same as datatype of msgspec_object.id
    # use obj_id to store/fetch item from dict for consistency
    obj_id = kwargs.get("_id")

    if obj_id is not None:
        obj_id = get_obj_id_to_put_as_key(obj_id)
        if parse_to_msgspec_obj:
            msgspec_object = msgspec_class_type.from_dict(kwargs, strict=False)
            if obj_id not in id_to_obj_dict:
                id_to_obj_dict[obj_id] = msgspec_object
            else:
                msgspec_object = msgspec_class_type.from_dict(kwargs, strict=False)
                for key, val in kwargs.items():
                    if key == "_id":
                        key = "id"
                    cached_msgspec_object = id_to_obj_dict[obj_id]
                    setattr(cached_msgspec_object, key, getattr(msgspec_object, key))
        else:
            if obj_id not in id_to_obj_dict:
                id_to_obj_dict[obj_id] = kwargs
            else:
                cached_kwargs = id_to_obj_dict[obj_id]
                cached_kwargs.update(kwargs)
    else:
        err_handler_callable()

    while not patch_queue.empty():
        kwargs: Dict = patch_queue.get()
        fetch_counts += 1

        # handling thread exit
        if kwargs == "EXIT":
            logging.info(f"Exiting get_update_obj_for_snapshot_type_update")
            return "EXIT"

        obj_id = kwargs.get("_id")

        if obj_id is not None:
            obj_id = get_obj_id_to_put_as_key(obj_id)
            msgspec_object_or_kwargs = id_to_obj_dict.get(obj_id)

            if msgspec_object_or_kwargs is None:
                if parse_to_msgspec_obj:
                    msgspec_object = msgspec_class_type.from_dict(kwargs, strict=False)
                    id_to_obj_dict[obj_id] = msgspec_object
                else:
                    id_to_obj_dict[obj_id] = kwargs
            else:
                # updating already existing object
                if parse_to_msgspec_obj:
                    msgspec_object = msgspec_class_type.from_dict(kwargs, strict=False)
                    for key, val in kwargs.items():
                        if key == "_id":
                            key = "id"
                        cached_msgspec_object = msgspec_object_or_kwargs
                        setattr(cached_msgspec_object, key, getattr(msgspec_object, key))
                else:
                    cached_kwargs = msgspec_object_or_kwargs
                    cached_kwargs.update(kwargs)
        else:
            err_handler_callable()

        if fetch_counts >= max_fetch_from_queue:
            break

    obj_json_list: List[Dict]
    if parse_to_msgspec_obj:
        obj_json_list = []
        for _, obj in id_to_obj_dict.items():
            obj_json_list.append(obj.to_dict(exclude_none=True))
    else:
        obj_json_list = list(id_to_obj_dict.values())

    return obj_json_list


def handle_patch_db_queue_updater(
        update_type: str, model_type_name_to_patch_queue_cache_dict: Dict[str, queue.Queue],
        basemodel_type_name: str, method_name: str, update_data,
        ledger_type_handler_callable: Callable, snapshot_type_handler_callable: Callable,
        update_handler_callable: Callable, error_handler_callable: Callable,
        max_fetch_from_queue: int, snapshot_type_callable_err_handler: Callable,
        parse_to_model: bool | None = None):
    if update_type in UpdateType.__members__:
        update_type: UpdateType = UpdateType(update_type)

        update_cache_dict = model_type_name_to_patch_queue_cache_dict

        patch_queue = update_cache_dict.get(basemodel_type_name)

        if patch_queue is None:
            patch_queue = queue.Queue()

            Thread(target=handle_dynamic_queue_for_patch_n_patch_all,
                   args=(basemodel_type_name, method_name, update_type,
                         patch_queue, ledger_type_handler_callable, snapshot_type_handler_callable,
                         update_handler_callable, error_handler_callable, max_fetch_from_queue,
                         snapshot_type_callable_err_handler, parse_to_model,),
                   name=f"{basemodel_type_name}_handler").start()
            logging.info(f"Thread Started: {basemodel_type_name}_handler")

            update_cache_dict[basemodel_type_name] = patch_queue

        patch_queue.put(update_data)
    else:
        raise Exception(f"Unsupported {update_type=} in handle_dynamic_queue_updater")


def handle_dynamic_queue_for_patch_n_patch_all(basemodel_type: str, method_name: str,
                                               update_type: UpdateType, patch_queue: queue.Queue,
                                               ledger_type_handler_callable: Callable,
                                               snapshot_type_handler_callable: Callable,
                                               update_handler_callable: Callable, error_handler_callable: Callable,
                                               max_fetch_from_queue: int,
                                               snapshot_type_callable_err_handler: Callable,
                                               parse_to_model: bool | None = None):
    try:
        basemodel_class_type: Type[MsgspecBaseModel] = eval(basemodel_type)

        is_param_list_type = is_first_param_list_type(update_handler_callable)

        pending_updates = []
        while 1:
            try:
                if update_type == UpdateType.JOURNAL_TYPE:
                    # blocking call
                    pending_updates: List[Any] | Any = (
                        ledger_type_handler_callable(basemodel_class_type, update_type, method_name, patch_queue,
                                                      max_fetch_from_queue, pending_updates, parse_to_model))

                else:  # if update_type is UpdateType.SNAPSHOT_TYPE
                    # blocking call
                    pending_updates: List[Any] | Any = (
                        snapshot_type_handler_callable(basemodel_class_type, update_type, method_name, patch_queue,
                                                       max_fetch_from_queue, snapshot_type_callable_err_handler,
                                                       pending_updates, parse_to_model))

                if pending_updates == "EXIT":
                    return

                while 1:
                    try:
                        if is_param_list_type:
                            update_handler_callable(pending_updates)
                            logging.info(f"called {update_handler_callable.__name__} with {pending_updates=} in "
                                         f"handle_dynamic_queue_for_patch_n_patch_all")
                        else:
                            for pending_update in pending_updates:
                                update_handler_callable(pending_update)
                                logging.info(f"called {update_handler_callable.__name__} with {pending_update=} in "
                                             f"handle_dynamic_queue_for_patch_n_patch_all")
                                pending_updates.remove(pending_update)     # cleaning all updates that went fine
                        # only gets cleared if client call was successful else keeps data for further updates
                        pending_updates = []
                        break
                    except Exception as e:
                        if not should_retry_due_to_server_down(e):  # stays within loop if server is down
                            logging.exception(e)
                            raise e
            except Exception as e:
                error_handler_callable(basemodel_type, update_type, e, pending_updates)
    except Exception as e:
        logging.exception(e)
        raise Exception(e)


def alert_queue_handler_err_handler(e, model_obj_list, queue_obj, err_handling_callable,
                                    web_client_callable, client_connection_fail_retry_secs: int | None = None):
    # Handling patch-all race-condition if some obj got removed before getting updated due to wait
    # pattern1: happens in patch_all and in put_all when stored_obj is fetched before update operation and hence
    #           error is raised before updating obj
    match_list1: List[str] = re.findall(non_existing_obj_read_fail_regex_pattern, str(e))

    # pattern2: happens in put_all when obj is updated and then missing ids are found and error is raised
    pattern2 = r"Can't find document objects with ids: \[(.*?)\] to update"
    match_list2: List[str] = re.findall(pattern2, str(e))

    if match_list1:
        # taking first occurrence
        non_existing_id_list: List[int] = [parse_to_int(_id.strip())
                                           for _id in match_list1[0].split(",")]
        non_existing_obj = []
        for model_obj in model_obj_list:
            if model_obj.id in non_existing_id_list:
                non_existing_obj.append(model_obj)
            else:
                queue_obj.put(model_obj)  # putting back all other existing jsons
        logging.debug(f"Calling Error handler func provided with param: {non_existing_obj}")
        err_handling_callable(non_existing_obj)
    elif match_list2:
        # taking first occurrence
        non_existing_id_list: List[int] = [parse_to_int(_id.strip())
                                           for _id in match_list2[0].split(",")]
        non_existing_obj = []
        for model_obj in model_obj_list:
            if model_obj.id in non_existing_id_list:
                non_existing_obj.append(model_obj)
            # else not required: if obj's id is not in non-existing list then doing nothing since it got updated
            # already in put_all call (patch_all always belongs to pattern1)
        logging.debug(f"Calling Error handler func provided with param: {non_existing_obj}")
        err_handling_callable(non_existing_obj)
    elif "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
        if client_connection_fail_retry_secs is None:
            client_connection_fail_retry_secs = 5 * 60  # 5 minutes

        logging.exception(
            f"Connection Error occurred while calling {web_client_callable.__name__}, "
            f"will stay on wait for {client_connection_fail_retry_secs} secs and again retry - "
            f"ignoring all data for this call")

        time.sleep(client_connection_fail_retry_secs)
    else:
        logging.exception(
            f"Some Error Occurred while calling {web_client_callable.__name__}, "
            f"sending all updates to err_handling_callable, {str(e)}")
        err_handling_callable(model_obj_list)


def alert_queue_handler_for_create_only(
        run_state: bool, queue_obj: queue.Queue, bulk_transactions_counts_per_call: int,
        bulk_transaction_timeout: int, create_web_client_callable: Callable[..., Any],
        err_handling_callable, client_connection_fail_retry_secs: int | None = None):
    create_model_obj_list = []
    queue_fetch_counts: int = 0
    oldest_entry_time: DateTime = DateTime.utcnow()
    while True:
        if not create_model_obj_list:
            remaining_timeout_secs = bulk_transaction_timeout
        else:
            remaining_timeout_secs = (
                    bulk_transaction_timeout - (DateTime.utcnow() - oldest_entry_time).total_seconds())

        if not remaining_timeout_secs < 1:
            try:
                alert_obj = queue_obj.get(timeout=remaining_timeout_secs)  # timeout based blocking call

                if alert_obj == "EXIT":
                    logging.info(f"Exiting alert_queue_handler")
                    return

                create_model_obj_list.append(alert_obj)
                queue_fetch_counts += 1
            except queue.Empty:
                # since bulk update timeout limit has breached, will call update
                pass
            else:
                if queue_fetch_counts < bulk_transactions_counts_per_call:
                    continue
                # else, since bulk update count limit has breached, will call update
        # since bulk update remaining timeout limit <= 0, will call update

        if not run_state:
            # Exiting this function if run state is turned False
            logging.info(f"Found {run_state=} in alert_queue_handler - Exiting while loop")
            return

        if create_model_obj_list:

            # handling create list
            try:
                res = create_web_client_callable(create_model_obj_list)
            except HTTPException as http_e:
                alert_queue_handler_err_handler(http_e.detail, create_model_obj_list, queue_obj,
                                                err_handling_callable,
                                                create_web_client_callable, client_connection_fail_retry_secs)
            except Exception as e:
                alert_queue_handler_err_handler(e, create_model_obj_list, queue_obj, err_handling_callable,
                                                create_web_client_callable, client_connection_fail_retry_secs)
            create_model_obj_list.clear()  # cleaning list to start fresh cycle

        queue_fetch_counts = 0
        oldest_entry_time = DateTime.utcnow()
        # else not required since even after timeout no data found


def get_remaining_timeout_secs(log_payload_cache_list: List[Dict],
                               bulk_transaction_timeout: int, oldest_entry_time: DateTime.utcnow()) -> int:
    if not log_payload_cache_list:
        remaining_timeout_secs = bulk_transaction_timeout
    else:
        remaining_timeout_secs = (
                bulk_transaction_timeout - (DateTime.utcnow() - oldest_entry_time).total_seconds())
    return remaining_timeout_secs


async def update_alert_caches(alerts_cache_cont: AlertsCacheCont, alert_obj: PlanAlert | ContactAlert,
                              is_new_object: bool) -> None:
    async with alerts_cache_cont.re_mutex:
        if is_new_object:
            alerts_cache_cont.create_alert_obj_dict[alert_obj.id] = alert_obj
        else:
            alerts_cache_cont.update_alert_obj_dict[alert_obj.id] = alert_obj
        alerts_cache_cont.alert_id_to_obj_dict[alert_obj.id] = alert_obj


def clean_alert_str(alert_str: str) -> str:
    # remove object hex memory path
    cleaned_alert_str: str = re.sub(r"0x[a-f0-9]*", "", alert_str)
    # remove any model_object_id (str type id)
    cleaned_alert_str = re.sub(r"\'[a-fA-F0-9]{24}\' ", "", cleaned_alert_str)
    # remove all numeric digits
    cleaned_alert_str = re.sub(r"-?[0-9]*", "", cleaned_alert_str)
    cleaned_alert_str = cleaned_alert_str.split("...check the file:")[0]
    return cleaned_alert_str


def get_alert_cache_key(severity: Severity, alert_brief: str, component_path: str | None = None,
                        source_file_path: str | None = None, line_num: int | None = None) -> str:
    # updated_alert_brief: str = alert_brief.split(":", 3)[-1].strip()
    updated_alert_brief = clean_alert_str(alert_str=alert_brief)
    alert_key = f"{severity}@#@{updated_alert_brief}"
    # if component_path:
    #     alert_key += f"@#@{component_path}"
    if source_file_path:
        alert_key += f"@#@{source_file_path}"
    if line_num:
        alert_key += f"@#@{line_num}"
    return alert_key


def create_or_update_alert(create_alert_list: List[PlanAlert | ContactAlert],
                           upload_alert_list: List[PlanAlert | ContactAlert],
                           alerts_cache_dict: Dict[str, PlanAlertBaseModel | PlanAlert] |
                                               Dict[str, PlanAlertBaseModel | PlanAlert] | None,
                           plan_alert_type: Type[PlanAlert] | Type[PlanAlertBaseModel],
                           contact_alert_type: Type[ContactAlert] | Type[ContactAlertBaseModel],
                           severity: Severity, alert_brief: str, plan_id: int | None = None,
                           alert_meta: AlertMeta | AlertMetaBaseModel | None = None) -> None:
    """
    Handles plan alerts if plan id is passed else handles contact alerts
    """
    if alert_meta:
        cache_key = get_alert_cache_key(severity, alert_brief, alert_meta.component_file_path,
                                        alert_meta.source_file_name, alert_meta.line_num)
    else:
        cache_key = get_alert_cache_key(severity, alert_brief)
    stored_alert = alerts_cache_dict.get(cache_key)

    if stored_alert is not None:
        updated_alert_count: int = stored_alert.alert_count + 1
        last_update_analyzer_time: DateTime = DateTime.utcnow()

        # update the stored_alert in cache
        stored_alert.dismiss = False
        stored_alert.alert_brief = alert_brief
        stored_alert.alert_count = updated_alert_count
        stored_alert.last_update_analyzer_time = last_update_analyzer_time
        if alert_meta:
            if stored_alert.alert_meta is not None:
                if alert_meta.component_file_path is not None:
                    stored_alert.alert_meta.component_file_path = alert_meta.component_file_path
                if alert_meta.source_file_name is not None:
                    stored_alert.alert_meta.source_file_name = alert_meta.source_file_name
                if alert_meta.line_num is not None:
                    stored_alert.alert_meta.line_num = alert_meta.line_num
                if alert_meta.alert_create_date_time is not None:
                    stored_alert.alert_meta.alert_create_date_time = alert_meta.alert_create_date_time
                if alert_meta.first_detail:
                    if stored_alert.alert_meta.first_detail is None:
                        stored_alert.alert_meta.first_detail = alert_meta.first_detail
                    # else not required: avoid update of first_detail once it is set
                if alert_meta.latest_detail:
                    if stored_alert.alert_meta.latest_detail is None:
                        stored_alert.alert_meta.latest_detail = alert_meta.latest_detail
                    else:
                        if stored_alert.alert_meta.latest_detail != alert_meta.latest_detail:
                            stored_alert.alert_meta.latest_detail = alert_meta.latest_detail
                        # else not required: avoiding update if same latest alert detail is found
            else:
                stored_alert.alert_meta = alert_meta

        upload_alert_list.append(stored_alert)

    else:
        if alert_meta is not None:
            # avoiding empty detail fields
            if not alert_meta.first_detail:
                alert_meta.first_detail = None
            if not alert_meta.latest_detail:
                alert_meta.latest_detail = None

            # if first_detail and latest_detail are same at create time then removing latest_detail to only take
            # first_detail with value at creation time
            if alert_meta.first_detail == alert_meta.latest_detail:
                alert_meta.latest_detail = None

        # create a new stored_alert
        alert_obj: PlanAlert | ContactAlert = (
            create_alert(alert_brief=alert_brief, severity=severity, plan_id=plan_id,
                         plan_alert_type=plan_alert_type, contact_alert_type=contact_alert_type,
                         alert_meta=alert_meta))
        alerts_cache_dict[cache_key] = alert_obj
        create_alert_list.append(alert_obj)


def update_plan_alert_cache(
        plan_id: int, plan_alert_cache_by_plan_id_dict: Dict[int, Dict[str, PlanAlertBaseModel | PlanAlert]],
        filter_query_callable: Callable[..., Any]) -> None:
    if plan_id not in plan_alert_cache_by_plan_id_dict:
        try:
            # block for task to finish
            plan_alert_list: List[PlanAlertBaseModel] = filter_query_callable(plan_id)
        except Exception as e:
            err_str_ = f"{filter_query_callable.__name__} failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        else:
            plan_alert_cache_by_plan_id_dict[plan_id] = {}
            for plan_alert in plan_alert_list:
                component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(plan_alert)
                alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                                component_file_path, source_file_name, line_num)
                plan_alert_cache_by_plan_id_dict[plan_id][alert_key] = plan_alert


def get_alert_meta_obj(component_path: str | None = None,
                       source_file_name: str | None = None, line_num: int | None = None,
                       alert_create_date_time: DateTime | None = None, first_detail: str | None = None,
                       latest_detail: str | None = None,
                       alert_meta_type: Type[AlertMeta] | Type[AlertMetaBaseModel] | None = None
                       ) -> AlertMetaBaseModel | AlertMeta | None:
    if alert_meta_type is None:
        alert_meta_type = AlertMeta

    alert_meta = alert_meta_type()
    alert_meta_has_update = False
    if component_path is not None:
        alert_meta_has_update = True
        alert_meta.component_file_path = component_path
    if source_file_name is not None:
        alert_meta_has_update = True
        alert_meta.source_file_name = source_file_name
    if line_num is not None:
        alert_meta_has_update = True
        alert_meta.line_num = line_num
    if alert_create_date_time:
        alert_meta_has_update = True
        alert_meta.alert_create_date_time = alert_create_date_time
    if first_detail:
        alert_meta_has_update = True
        alert_meta.first_detail = first_detail
        # if latest_detail is passed it will be replaced in next if condition
        alert_meta.latest_detail = first_detail
    if latest_detail:
        alert_meta_has_update = True
        alert_meta.latest_detail = latest_detail

    if alert_meta_has_update:
        return alert_meta
    else:
        return None


def get_key_meta_data_from_obj(alert_obj: PlanAlert | ContactAlert | PlanAlertBaseModel | ContactAlertBaseModel):
    component_file_path = None
    source_file_name = None
    line_num = None
    if alert_obj.alert_meta:
        component_file_path = alert_obj.alert_meta.component_file_path
        source_file_name = alert_obj.alert_meta.source_file_name
        line_num = alert_obj.alert_meta.line_num
    return component_file_path, source_file_name, line_num


def client_call_log_str(basemodel_type: Type | None, client_callable: Callable, db_pattern: str,
                        update_type: UpdateType | None = None, **kwargs):
    if update_type is None:
        update_type = UpdateType.JOURNAL_TYPE

    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_str = (f"{db_pattern}"
               f"{basemodel_type.__name__ if basemodel_type is not None else 'basemodel_type is None'}{fld_sep}{update_type.value}"
               f"{fld_sep}{client_callable.__name__}{fld_sep}")
    for k, v in kwargs.items():
        log_str += f"{k}{val_sep}{v}"
        if k != list(kwargs)[-1]:
            log_str += fld_sep

    return log_str


def plan_view_client_call_log_str(basemodel_type: Type | None, client_callable: Callable,
                                   update_type: UpdateType | None = None, **kwargs) -> str:
    plan_view_db_pattern: str = get_pattern_for_plan_view_db_updates()
    log_str = client_call_log_str(basemodel_type, client_callable, plan_view_db_pattern, update_type, **kwargs)
    return log_str


def pair_plan_client_call_log_str(basemodel_type: Type | None, client_callable: Callable,
                                   update_type: UpdateType | None = None, **kwargs) -> str:
    pair_plan_db_pattern: str = get_pattern_for_pair_plan_db_updates()
    log_str = client_call_log_str(basemodel_type, client_callable, pair_plan_db_pattern, update_type, **kwargs)
    return log_str


def enable_disable_log_str_start_pattern() -> str:
    return "*^*"


def enable_disable_plan_alerts_log_str(plan_id: int, symbol_side_key_list: List[str], action: bool):
    enable_disable_start_pattern = enable_disable_log_str_start_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_str = f"{enable_disable_start_pattern}{plan_id}{val_sep}{symbol_side_key_list}{val_sep}{action}"
    return log_str


def remove_plan_alert_by_start_id_pattern() -> str:
    return "-***-"


def remove_plan_alert_by_start_id_log_str(plan_id: int) -> str:
    remove_plan_alert_by_start_id_pattern_str = remove_plan_alert_by_start_id_pattern()
    return f"{remove_plan_alert_by_start_id_pattern_str}{plan_id}"
