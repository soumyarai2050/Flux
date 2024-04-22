# standard imports
import datetime
import time
import queue
from threading import Thread, current_thread
import re

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import (
    YAMLConfigurationManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_client import (
    LogBookServiceHttpClient)

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_LOG_DIR = PurePath(__file__).parent.parent / "log"

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

la_host, la_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

log_book_service_http_client = \
    LogBookServiceHttpClient.set_or_get_if_instance_exists(la_host, la_port)

datetime_str = datetime.datetime.now().strftime("%Y%m%d")
portfolio_alert_fail_log = f"portfolio_alert_fail_logs_{datetime_str}.log"
simulator_portfolio_alert_fail_log = f"simulator_portfolio_alert_fail_logs_{datetime_str}.log"


class UpdateType(StrEnum):
    JOURNAL_TYPE = auto()
    SNAPSHOT_TYPE = auto()


def create_alert(
        strat_alert_type: Type[StratAlert] | Type[StratAlertBaseModel],
        portfolio_alert_type: Type[PortfolioAlert] | Type[PortfolioAlertBaseModel],
        alert_brief: str, alert_details: str | None = None,
        severity: Severity = Severity.Severity_ERROR,
        strat_id: int | None = None) -> StratAlertBaseModel | PortfolioAlertBaseModel:
    """
    Handles strat alerts if strat id is passed else handles portfolio alerts
    """
    kwargs = {}
    kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False,
                  last_update_date_time=DateTime.utcnow(), alert_count=1)
    if alert_details is not None:
        kwargs.update(alert_details=alert_details)
    if strat_id is not None:
        kwargs["strat_id"] = strat_id
        start_alert = strat_alert_type(**kwargs)
        if hasattr(strat_alert_type, "next_id"):
            # used in server process since db is initialized in that process -
            # putting id so that object can be cached with id - to avoid put http with cached obj without id
            start_alert.id = strat_alert_type.next_id()
        return start_alert
    else:
        portfolio_alert = portfolio_alert_type(**kwargs)
        if hasattr(portfolio_alert_type, "next_id"):
            # used in server process since db is initialized in that process -
            # putting id so that object can be cached with id - to avoid put http with cached obj without id
            portfolio_alert.id = portfolio_alert_type.next_id()
        return portfolio_alert


def is_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            log_book_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def init_service(portfolio_alerts_cache: Dict[str, PortfolioAlertBaseModel]) -> bool:
    if is_log_book_service_up(ignore_error=True):
        try:
            # block for task to finish
            portfolio_alert_list: List[PortfolioAlertBaseModel] = (
                log_book_service_http_client.get_all_portfolio_alert_client())  # returns list - empty or with objs

        except Exception as e:
            err_str_ = f"get_all_portfolio_alert_client failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

        for portfolio_alert in portfolio_alert_list:
            alert_key = get_alert_cache_key(portfolio_alert.severity, portfolio_alert.alert_brief,
                                            portfolio_alert.alert_details)
            portfolio_alerts_cache[alert_key] = portfolio_alert
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


def get_pattern_for_pair_strat_db_updates():
    pattern = config_yaml_dict.get("pattern_for_pair_strat_db_updates")
    if pattern is None:
        pattern = "^^^"
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


def get_update_obj_list_for_journal_type_update(
        pydantic_basemodel_class_type: Type[BaseModel], update_type: str, method_name: str, patch_queue: queue.Queue,
        max_fetch_from_queue: int, parse_to_pydantic: bool | None = None) -> List[Dict] | str:  # blocking function
    update_dict_list: List[Dict] = []
    fetch_counts: int = 0

    kwargs: Dict = patch_queue.get()
    fetch_counts += 1

    # handling thread exit
    if kwargs == "EXIT":
        logging.info(f"Exiting get_update_obj_list_for_journal_type_update")
        return "EXIT"

    if parse_to_pydantic:
        pydantic_object = pydantic_basemodel_class_type(**kwargs)
        update_dict_list.append(jsonable_encoder(pydantic_object, by_alias=True, exclude_none=True))
    else:
        update_dict_list.append(jsonable_encoder(fetch_counts, by_alias=True, exclude_none=True))

    while not patch_queue.empty():
        kwargs: Dict = patch_queue.get()
        fetch_counts += 1

        # handling thread exit
        if kwargs == "EXIT":
            logging.info(f"Exiting get_update_obj_list_for_journal_type_update")
            return "EXIT"

        if parse_to_pydantic:
            pydantic_object = pydantic_basemodel_class_type(**kwargs)
            update_dict_list.append(jsonable_encoder(pydantic_object, by_alias=True, exclude_none=True))
        else:
            update_dict_list.append(jsonable_encoder(fetch_counts, by_alias=True, exclude_none=True))

        if fetch_counts >= max_fetch_from_queue:
            return update_dict_list
    return update_dict_list


def get_update_obj_for_snapshot_type_update(
        pydantic_basemodel_class_type: Type[BaseModel], update_type: str, method_name: str, patch_queue: queue.Queue,
        max_fetch_from_queue: int, err_handler_callable: Callable,
        parse_to_pydantic: bool | None = None) -> List[Dict] | str:  # blocking function
    id_to_obj_dict = {}
    fetch_counts: int = 0

    kwargs: Dict = patch_queue.get()
    fetch_counts += 1

    # handling thread exit
    if kwargs == "EXIT":
        logging.info(f"Exiting get_update_obj_for_snapshot_type_update")
        return "EXIT"

    # _id from the kwargs dict is of string type which may or may not be same as datatype of pydantic_object.id
    # use obj_id to store/fetch item from dict for consistency
    obj_id = kwargs.get("_id")
    if parse_to_pydantic:
        pydantic_object = pydantic_basemodel_class_type(**kwargs)
        id_to_obj_dict[obj_id] = pydantic_object
    else:
        id_to_obj_dict[obj_id] = kwargs

    while not patch_queue.empty():
        kwargs: Dict = patch_queue.get()
        fetch_counts += 1

        # handling thread exit
        if kwargs == "EXIT":
            logging.info(f"Exiting get_update_obj_for_snapshot_type_update")
            return "EXIT"

        obj_id = kwargs.get("_id")

        if obj_id is not None:
            pydantic_object_or_kwargs = id_to_obj_dict.get(obj_id)

            if pydantic_object_or_kwargs is None:
                if parse_to_pydantic:
                    pydantic_object = pydantic_basemodel_class_type(**kwargs)
                    id_to_obj_dict[obj_id] = pydantic_object
                else:
                    id_to_obj_dict[obj_id] = kwargs
            else:
                # updating already existing object
                if parse_to_pydantic:
                    for key, val in kwargs.items():
                        cached_pydantic_object = pydantic_object_or_kwargs
                        setattr(cached_pydantic_object, key, val)
                else:
                    cached_kwargs = pydantic_object_or_kwargs
                    cached_kwargs.update(kwargs)
        else:
            err_handler_callable()

        if fetch_counts >= max_fetch_from_queue:
            break

    obj_json_list: List[Dict] = []
    for _, obj in id_to_obj_dict.items():
        obj_json_list.append(jsonable_encoder(obj, by_alias=True, exclude_none=True))

    return obj_json_list


def handle_patch_db_queue_updater(
        update_type: str, pydantic_type_name_to_patch_queue_cache_dict: Dict[str, queue.Queue],
        pydantic_basemodel_type_name: str, method_name: str, update_data,
        journal_type_handler_callable: Callable, snapshot_type_handler_callable: Callable,
        update_handler_callable: Callable, error_handler_callable: Callable,
        max_fetch_from_queue: int, snapshot_type_callable_err_handler: Callable,
        parse_to_pydantic: bool | None = None):
    if update_type in UpdateType.__members__:
        update_type: UpdateType = UpdateType(update_type)

        update_cache_dict = pydantic_type_name_to_patch_queue_cache_dict

        patch_queue = update_cache_dict.get(pydantic_basemodel_type_name)

        if patch_queue is None:
            patch_queue = queue.Queue()

            Thread(target=handle_dynamic_queue_for_patch_n_patch_all,
                   args=(pydantic_basemodel_type_name, method_name, update_type,
                         patch_queue, journal_type_handler_callable, snapshot_type_handler_callable,
                         update_handler_callable, error_handler_callable, max_fetch_from_queue,
                         snapshot_type_callable_err_handler, parse_to_pydantic, ),
                   name=f"{pydantic_basemodel_type_name}_handler").start()
            logging.info(f"Thread Started: {pydantic_basemodel_type_name}_handler")

            update_cache_dict[pydantic_basemodel_type_name] = patch_queue

        patch_queue.put(update_data)
    else:
        raise Exception(f"Unsupported {update_type = } in handle_dynamic_queue_updater")


def handle_dynamic_queue_for_patch_n_patch_all(pydantic_basemodel_type: str, method_name: str,
                                               update_type: UpdateType, patch_queue: queue.Queue,
                                               journal_type_handler_callable: Callable,
                                               snapshot_type_handler_callable: Callable,
                                               update_handler_callable: Callable, error_handler_callable: Callable,
                                               max_fetch_from_queue: int,
                                               snapshot_type_callable_err_handler: Callable,
                                               parse_to_pydantic: bool | None = None):
    pydantic_basemodel_class_type: Type[BaseModel] = eval(pydantic_basemodel_type)

    while 1:
        try:
            if update_type == UpdateType.JOURNAL_TYPE:
                # blocking call
                update_res: List[Any] | Any = (
                    journal_type_handler_callable(pydantic_basemodel_class_type, update_type, method_name, patch_queue,
                                                  max_fetch_from_queue, parse_to_pydantic))

            else:  # if update_type is UpdateType.SNAPSHOT_TYPE
                # blocking call
                update_res: List[Any] | Any = (
                    snapshot_type_handler_callable(pydantic_basemodel_class_type, update_type, method_name, patch_queue,
                                                   max_fetch_from_queue, snapshot_type_callable_err_handler,
                                                   parse_to_pydantic))

            if update_res == "EXIT":
                return

            while 1:
                try:
                    update_handler_callable(update_res)
                    logging.info(f"called {update_handler_callable.__name__} with {update_res = } in "
                                 f"handle_dynamic_queue_for_patch_n_patch_all")
                    break
                except Exception as e:
                    if not should_retry_due_to_server_down(e):
                        raise Exception(e)
        except Exception as e:
            error_handler_callable(pydantic_basemodel_type, update_type, e)


def _alert_queue_handler_err_handler(e, pydantic_obj_list, queue_obj, err_handling_callable,
                                     web_client_callable, client_connection_fail_retry_secs):
    # Handling patch-all race-condition if some obj got removed before getting updated due to wait
    pattern = ".*objects with ids: {(.*)} out of requested .*"
    match_list: List[str] = re.findall(pattern, str(e))
    if match_list:
        # taking first occurrence
        non_existing_id_list: List[int] = [parse_to_int(_id.strip())
                                           for _id in match_list[0].split(",")]
        non_existing_obj = []
        for pydantic_obj in pydantic_obj_list:
            if pydantic_obj.id in non_existing_id_list:
                non_existing_obj.append(pydantic_obj)
            else:
                queue_obj.put(pydantic_obj)  # putting back all other existing jsons
        logging.debug(f"Calling Error handler func provided with param: {non_existing_obj}")
        err_handling_callable(non_existing_obj)
    elif "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
        logging.exception(
            f"Connection Error occurred while calling {web_client_callable.__name__}, "
            f"will stay on wait for 5 secs and again retry - ignoring all data for this call")

        if client_connection_fail_retry_secs is None:
            client_connection_fail_retry_secs = 5 * 60  # 5 minutes
        time.sleep(client_connection_fail_retry_secs)
    else:
        logging.exception(
            f"Some Error Occurred while calling {web_client_callable.__name__}, "
            f"sending all updates to err_handling_callable, {str(e)}")
        err_handling_callable(pydantic_obj_list)


def alert_queue_handler(run_state: bool, queue_obj: queue.Queue, bulk_transactions_counts_per_call: int,
                        bulk_transaction_timeout: int, create_web_client_callable: Callable[..., Any],
                        err_handling_callable, update_web_client_callable: Callable[..., Any] | None = None,
                        created_alert_id_dict: Dict[int, bool] | None = None,
                        client_connection_fail_retry_secs: int | None = None):
    create_pydantic_obj_list = []
    update_pydantic_obj_list = []
    queue_fetch_counts: int = 0
    oldest_entry_time: DateTime = DateTime.utcnow()
    while True:
        if not create_pydantic_obj_list and not update_pydantic_obj_list:
            remaining_timeout_secs = bulk_transaction_timeout
        else:
            remaining_timeout_secs = (
                    bulk_transaction_timeout - (DateTime.utcnow() - oldest_entry_time).total_seconds())

        if not remaining_timeout_secs < 1:
            try:
                pydantic_obj = queue_obj.get(timeout=remaining_timeout_secs)  # timeout based blocking call

                if pydantic_obj == "EXIT":
                    logging.info(f"Exiting alert_queue_handler")
                    return

                if created_alert_id_dict is not None:
                    # if created_alert_id_dict is passed then using both update and create mechanism
                    if created_alert_id_dict.get(pydantic_obj.id) is not None:
                        update_pydantic_obj_list.append(pydantic_obj)
                    else:
                        create_pydantic_obj_list.append(pydantic_obj)
                        created_alert_id_dict[pydantic_obj.id] = True
                else:
                    # if created_alert_id_dict is not passed then only creating
                    create_pydantic_obj_list.append(pydantic_obj)

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
            logging.info(f"Found {run_state = } in alert_queue_handler - Exiting while loop")
            return

        if create_pydantic_obj_list:

            # handling create list
            try:
                res = create_web_client_callable(create_pydantic_obj_list)
            except HTTPException as http_e:
                _alert_queue_handler_err_handler(http_e.detail, create_pydantic_obj_list, queue_obj,
                                                 err_handling_callable,
                                                 create_web_client_callable, client_connection_fail_retry_secs)
            except Exception as e:
                _alert_queue_handler_err_handler(e, create_pydantic_obj_list, queue_obj, err_handling_callable,
                                                 create_web_client_callable, client_connection_fail_retry_secs)
            create_pydantic_obj_list.clear()  # cleaning list to start fresh cycle

        if update_pydantic_obj_list:
            # handling update list
            try:
                res = update_web_client_callable(update_pydantic_obj_list)
            except HTTPException as http_e:
                _alert_queue_handler_err_handler(http_e.detail, update_pydantic_obj_list, queue_obj,
                                                 err_handling_callable,
                                                 update_web_client_callable, client_connection_fail_retry_secs)
            except Exception as e:
                _alert_queue_handler_err_handler(e, update_pydantic_obj_list, queue_obj, err_handling_callable,
                                                 update_web_client_callable, client_connection_fail_retry_secs)
            update_pydantic_obj_list.clear()  # cleaning list to start fresh cycle

        queue_fetch_counts = 0
        oldest_entry_time = DateTime.utcnow()
        # else not required since even after timeout no data found


def clean_alert_str(alert_str: str) -> str:
    # remove object hex memory path
    cleaned_alert_str: str = re.sub(r"0x[a-f0-9]*", "", alert_str)
    # remove all numeric digits
    cleaned_alert_str = re.sub(r"-?[0-9]*", "", cleaned_alert_str)
    # remove any pydantic_object_id (str type id)
    cleaned_alert_str = re.sub(r"\'[a-fA-F0-9]{24}\' ", "", cleaned_alert_str)
    cleaned_alert_str = cleaned_alert_str.split("...check the file:")[0]
    return cleaned_alert_str


def get_alert_cache_key(severity: Severity, alert_brief: str, alert_details: str | None = None):
    # updated_alert_brief: str = alert_brief.split(":", 3)[-1].strip()
    updated_alert_brief = clean_alert_str(alert_str=alert_brief)
    updated_alert_details = None
    if alert_details:
        updated_alert_details = clean_alert_str(alert_str=alert_details)
    return f"{severity}@#@{updated_alert_brief}@#@{updated_alert_details}"


def create_or_update_alert(alerts_cache_dict: Dict[str, StratAlertBaseModel | StratAlert] |
                                               Dict[str, StratAlertBaseModel | StratAlert] | None,
                           alert_queue: queue.Queue,
                           strat_alert_type: Type[StratAlert] | Type[StratAlertBaseModel],
                           portfolio_alert_type: Type[PortfolioAlert] | Type[PortfolioAlertBaseModel],
                           severity: Severity, alert_brief: str, alert_details: str | None = None,
                           strat_id: int | None = None) -> None:
    """
    Handles strat alerts if strat id is passed else handles portfolio alerts
    """
    cache_key = get_alert_cache_key(severity, alert_brief, alert_details)
    stored_alert = alerts_cache_dict.get(cache_key)

    if stored_alert is not None:
        updated_alert_count: int = stored_alert.alert_count + 1
        updated_last_update_date_time: DateTime = DateTime.utcnow()

        # update the stored_alert in cache
        stored_alert.dismiss = False
        stored_alert.alert_brief = alert_brief
        stored_alert.alert_count = updated_alert_count
        stored_alert.last_update_date_time = updated_last_update_date_time

        alert_queue.put(stored_alert)
    else:
        # create a new stored_alert
        alert_obj: StratAlertBaseModel | PortfolioAlertBaseModel = (
            create_alert(alert_brief=alert_brief, alert_details=alert_details,
                         severity=severity, strat_id=strat_id, strat_alert_type=strat_alert_type,
                         portfolio_alert_type=portfolio_alert_type))
        alerts_cache_dict[cache_key] = alert_obj

        alert_queue.put(alert_obj)


# def _create_or_update_alert(alerts: List[StratAlertBaseModel] | List[StratAlert] |
#                                          List[PortfolioAlertBaseModel] | List[PortfolioAlert] | None,
#                            alert_queue: queue.Queue,
#                            strat_alert_type: Type[StratAlert] | Type[StratAlertBaseModel],
#                            portfolio_alert_type: Type[PortfolioAlert] | Type[PortfolioAlertBaseModel],
#                            severity: Severity, alert_brief: str, alert_details: str | None = None,
#                            strat_id: int | None = None) -> None:
#     """
#     Handles strat alerts if strat id is passed else handles portfolio alerts
#     """
#
#     alert_obj: StratAlertBaseModel | PortfolioAlertBaseModel | None = None
#     if alerts is not None:
#         # stored_alert is stored cache alert for current strat_id
#         for stored_alert in alerts:
#             stored_alert_brief: str = stored_alert.alert_brief
#             stored_alert_brief = stored_alert_brief.split(":", 3)[-1].strip()
#             stored_alert_brief = clean_alert_str(alert_str=stored_alert_brief)
#
#             stored_alert_details: str | None = stored_alert.alert_details
#             if stored_alert_details is not None:
#                 stored_alert_details = clean_alert_str(alert_str=stored_alert_details)
#
#             updated_alert_brief: str = alert_brief.split(":", 3)[-1].strip()
#             updated_alert_brief = clean_alert_str(alert_str=updated_alert_brief)
#             updated_alert_details: str | None = alert_details
#             if alert_details is not None:
#                 updated_alert_details = clean_alert_str(alert_str=updated_alert_details)
#
#             if updated_alert_brief == stored_alert_brief and severity == stored_alert.severity:
#                 # handling truncated mismatch
#                 if updated_alert_details is not None and stored_alert_details is not None:
#                     if len(updated_alert_details) > len(stored_alert_details):
#                         updated_alert_details = updated_alert_details[:len(stored_alert_details)]
#                     else:
#                         stored_alert_details = stored_alert_details[:len(updated_alert_details)]
#                 if updated_alert_details == stored_alert_details:
#                     updated_alert_count: int = stored_alert.alert_count + 1
#                     updated_last_update_date_time: DateTime = DateTime.utcnow()
#
#                     # update the stored_alert in cache
#                     stored_alert.dismiss = False
#                     stored_alert.alert_brief = alert_brief
#                     stored_alert.alert_count = updated_alert_count
#                     stored_alert.last_update_date_time = updated_last_update_date_time
#
#                     alert_queue.put(stored_alert)
#                     return
#
#                 # else not required: stored_alert details not matched
#             # else not required: stored_alert not matched with existing alerts
#     if alert_obj is None:
#         # create a new stored_alert
#         alert_obj: StratAlertBaseModel | PortfolioAlertBaseModel = (
#             create_alert(alert_brief=alert_brief, alert_details=alert_details,
#                          severity=severity, strat_id=strat_id, strat_alert_type=strat_alert_type,
#                          portfolio_alert_type=portfolio_alert_type))
#         alerts.append(alert_obj)
#
#         alert_queue.put(alert_obj)
#
#         return


def update_strat_alert_cache(
        strat_id: int, strat_alert_cache_by_strat_id_dict: Dict[int, Dict[str, StratAlertBaseModel | StratAlert]],
        filter_query_callable: Callable[..., Any]) -> None:
    if strat_id not in strat_alert_cache_by_strat_id_dict:
        try:
            # block for task to finish
            strat_alert_list: List[StratAlertBaseModel] = filter_query_callable(strat_id)
        except Exception as e:
            err_str_ = f"{filter_query_callable.__name__} failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        else:
            strat_alert_cache_by_strat_id_dict[strat_id] = {}
            for strat_alert in strat_alert_list:
                alert_key = get_alert_cache_key(strat_alert.severity, strat_alert.alert_brief,
                                                strat_alert.alert_details)
                strat_alert_cache_by_strat_id_dict[strat_id][alert_key] = strat_alert


async def async_update_strat_alert_cache(
        strat_id: int, strat_alert_cache_by_strat_id_dict: Dict[int, Dict[str, StratAlertBaseModel | StratAlert]],
        filter_query_callable: Callable[..., Any]) -> None:
    if strat_id not in strat_alert_cache_by_strat_id_dict:
        try:
            # block for task to finish
            strat_alert_list: List[StratAlertBaseModel] = await filter_query_callable(strat_id)
        except Exception as e:
            err_str_ = f"{filter_query_callable.__name__} failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        else:
            strat_alert_cache_by_strat_id_dict[strat_id] = {}
            for strat_alert in strat_alert_list:
                alert_key = get_alert_cache_key(strat_alert.severity, strat_alert.alert_brief,
                                                strat_alert.alert_details)
                strat_alert_cache_by_strat_id_dict[strat_id][alert_key] = strat_alert
