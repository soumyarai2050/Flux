# project imports
from typing import Type, Callable

from FluxPythonUtils.scripts.general_utility_functions import parse_to_int, is_first_param_list_type

# standard imports
import time
import queue
from threading import Thread
import re
from typing import Final

# 3rd party imports
from fastapi import HTTPException

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.ORMModel.projects_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.base_log_book_core_msgspec_model import *
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_msgspec_routes import MsgspecModel


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


def get_severity_type_from_severity_str(severity_str: str) -> Severity:
    return Severity[severity_str]


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
                               bulk_transaction_timeout: int, oldest_entry_time: DateTime) -> int:
    if not log_payload_cache_list:
        remaining_timeout_secs = bulk_transaction_timeout
    else:
        remaining_timeout_secs = (
                bulk_transaction_timeout - (DateTime.utcnow() - oldest_entry_time).total_seconds())
    return remaining_timeout_secs


async def update_alert_caches(alerts_cache_cont: AlertsCacheCont, alert_obj,
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


def create_or_update_alert(create_alert_list, upload_alert_list, alerts_cache_dict,
                           alert_type, severity: Severity, alert_brief: str,
                           alert_meta: AlertMeta | AlertMetaBaseModel | None = None,
                           **kwargs) -> None:
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
        create_alert_method: Callable = kwargs.get("create_alert_method")

        alert_obj = create_alert_method(alert_type=alert_type, alert_brief=alert_brief,
                                        severity=severity, alert_meta=alert_meta, **kwargs)
        alerts_cache_dict[cache_key] = alert_obj
        create_alert_list.append(alert_obj)


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


def get_key_meta_data_from_obj(alert_obj):
    component_file_path = None
    source_file_name = None
    line_num = None
    if alert_obj.alert_meta:
        component_file_path = alert_obj.alert_meta.component_file_path
        source_file_name = alert_obj.alert_meta.source_file_name
        line_num = alert_obj.alert_meta.line_num
    return component_file_path, source_file_name, line_num
