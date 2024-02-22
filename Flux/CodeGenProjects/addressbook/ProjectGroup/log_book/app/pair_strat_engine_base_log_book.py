import logging
import os
import time
import re
from threading import Thread
from queue import Queue
from typing import Set

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.log_book.log_book import LogDetail, get_transaction_counts_n_timeout_from_config
from Flux.PyCodeGenEngine.FluxCodeGenCore.app_log_book import AppLogBook
from Flux.CodeGenProjects.addressbook.ProjectGroup.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.app.pair_strat_engine_service_helper import (
    strat_manager_service_http_client, is_ongoing_strat, Side, UpdateType)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import (
    performance_benchmark_service_http_client, RawPerformanceDataBaseModel)

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == mobile_book or debug_env == "mobile_book") else True

portfolio_alert_bulk_update_counts_per_call, portfolio_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("portfolio_alert_configs")))
strat_alert_bulk_update_counts_per_call, strat_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("strat_alert_config")))


# Updating LogDetail to have strat_id_finder_callable
class StratLogDetail(LogDetail):
    strat_id_find_callable: Callable[[str], int] | None = None


class PairStratDbUpdateDataContainer(BaseModel):
    method_name: str
    pydantic_basemodel_type: str
    kwargs: Dict[str, Any]
    update_type: UpdateType | None = None


class PairStratEngineBaseLogBook(AppLogBook):
    underlying_partial_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_partial_update_all_strat_alert_http: Callable[..., Any] | None = None
    underlying_read_portfolio_alert_by_id_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_by_id_http: Callable[..., Any] | None = None

    asyncio_loop: ClassVar[asyncio.AbstractEventLoop | None] = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_routes import (
            underlying_partial_update_all_portfolio_alert_http, underlying_partial_update_all_strat_alert_http,
            underlying_read_portfolio_alert_by_id_http, underlying_read_strat_alert_by_id_http)
        cls.underlying_partial_update_all_portfolio_alert_http = underlying_partial_update_all_portfolio_alert_http
        cls.underlying_partial_update_all_strat_alert_http = underlying_partial_update_all_strat_alert_http
        cls.underlying_read_portfolio_alert_by_id_http = underlying_read_portfolio_alert_by_id_http
        cls.underlying_read_strat_alert_by_id_http = underlying_read_strat_alert_by_id_http

    def __init__(self, regex_file: str, log_details: List[LogDetail] | None = None,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False, log_detail_type: Type[LogDetail] | None = None):
        super().__init__(regex_file, config_yaml_dict, performance_benchmark_service_http_client,
                         RawPerformanceDataBaseModel, log_details=log_details,
                         log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                         debug_mode=debug_mode, log_detail_type=log_detail_type)
        PairStratEngineBaseLogBook.initialize_underlying_http_callables()
        self.simulation_mode = simulation_mode
        self.portfolio_alerts_model_exist: bool = False
        self.portfolio_alerts_cache: List[AlertOptional] = list()
        self.strat_id_by_symbol_side_dict: Dict[str, int] = dict()
        self.strat_alert_cache_by_strat_id_dict: Dict[int, List[Alert]] = dict()
        self.service_up: bool = False
        self.portfolio_alert_queue: Queue = Queue()
        self.strat_alert_queue: Queue = Queue()
        self.pair_strat_api_ops_queue: Queue = Queue()
        self.port_to_executor_web_client: Dict[int, StratExecutorServiceHttpClient] = {}
        self.pair_strat_engine_journal_type_update_cache_dict: Dict[str, Queue] = {}
        self.pair_strat_engine_snapshot_type_update_cache_dict: Dict[str, Queue] = {}
        self.field_sep = get_field_seperator_pattern()
        self.key_val_sep = get_key_val_seperator_pattern()
        self.pattern_for_pair_strat_db_updates = get_pattern_for_pair_strat_db_updates()
        self.pattern_to_restart_tail_process: str = get_pattern_to_restart_tail_process()
        self.pattern_to_force_kill_tail_process: str = get_pattern_to_force_kill_tail_process()
        self.pattern_to_remove_file_from_created_cache: str = get_pattern_to_remove_file_from_created_cache()

    def _handle_portfolio_alert_queue_err_handler(self, *args):
        err_str_ = f"_handle_portfolio_alert_queue_err_handler failed, passed args: {args}"
        self.portfolio_alert_fail_logger.exception(err_str_)

    def _handle_portfolio_alert_queue(self):
        PairStratEngineBaseLogBook.queue_handler(
            self.portfolio_alert_queue, portfolio_alert_bulk_update_counts_per_call,
            portfolio_alert_bulk_update_timeout,
            self.patch_all_portfolio_alert_client_with_asyncio_loop,
            self._handle_portfolio_alert_queue_err_handler)

    def patch_all_portfolio_alert_client_with_asyncio_loop(self, pydantic_obj_json_list: Dict):
        run_coro = PairStratEngineBaseLogBook.underlying_partial_update_all_portfolio_alert_http(pydantic_obj_json_list)
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            return future.result()
        except HTTPException as http_e:
            err_str_ = f"underlying_partial_update_all_portfolio_alert_http failed with http_exception: {http_e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        except Exception as e:
            err_str_ = f"underlying_partial_update_all_portfolio_alert_http failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def _init_service(self) -> bool:
        if self.service_up:
            return True
        else:
            self.service_up = is_log_book_service_up(ignore_error=True)
            if self.service_up:
                run_coro = PairStratEngineBaseLogBook.underlying_read_portfolio_alert_by_id_http(1)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                try:
                    # block for task to finish
                    portfolio_alert: PortfolioAlert = future.result()
                except HTTPException as http_e:
                    err_str_ = f"underlying_read_portfolio_alert_by_id_http failed with http_exception: {http_e}"
                    logging.error(err_str_)
                    raise Exception(err_str_)
                except Exception as e:
                    err_str_ = f"underlying_read_portfolio_alert_by_id_http failed with exception: {e}"
                    logging.error(err_str_)
                    raise Exception(err_str_)

                if portfolio_alert.alerts is not None:
                    self.portfolio_alerts_cache = portfolio_alert.alerts
                else:
                    self.portfolio_alerts_cache = list()
                return True
            return False

    def create_or_update_alert(self, alerts: List[AlertOptional] | List[Alert] | None, severity: Severity,
                               alert_brief: str, alert_details: str | None = None) -> AlertOptional:
        alert_obj: AlertOptional | None = None
        if alerts is not None:
            for alert in alerts:
                stored_alert_brief: str = alert.alert_brief
                stored_alert_brief = stored_alert_brief.split(":", 3)[-1].strip()
                stored_alert_brief = self.clean_alert_str(alert_str=stored_alert_brief)

                stored_alert_details: str | None = alert.alert_details
                if stored_alert_details is not None:
                    stored_alert_details = self.clean_alert_str(alert_str=stored_alert_details)

                cleaned_alert_brief: str = alert_brief.split(":", 3)[-1].strip()
                cleaned_alert_brief = self.clean_alert_str(alert_str=cleaned_alert_brief)
                cleaned_alert_details: str | None = alert_details
                if alert_details is not None:
                    cleaned_alert_details = self.clean_alert_str(alert_str=cleaned_alert_details)

                if cleaned_alert_brief == stored_alert_brief and severity == alert.severity:
                    # handling truncated mismatch
                    if cleaned_alert_details is not None and stored_alert_details is not None:
                        if len(cleaned_alert_details) > len(stored_alert_details):
                            cleaned_alert_details = cleaned_alert_details[:len(stored_alert_details)]
                        else:
                            stored_alert_details = stored_alert_details[:len(cleaned_alert_details)]
                    if cleaned_alert_details == stored_alert_details:
                        updated_alert_count: int = alert.alert_count + 1
                        updated_last_update_date_time: DateTime = DateTime.utcnow()
                        alert_obj = AlertOptional(_id=alert.id, dismiss=False, alert_count=updated_alert_count,
                                                  alert_brief=alert_brief, severity=alert.severity,
                                                  last_update_date_time=updated_last_update_date_time)
                        # update the alert in cache
                        alert.dismiss = False
                        alert.alert_brief = alert_brief
                        alert.alert_count = updated_alert_count
                        alert.last_update_date_time = updated_last_update_date_time
                        break
                    # else not required: alert details not matched
                # else not required: alert not matched with existing alerts
        if alert_obj is None:
            # create a new alert
            alert_obj: AlertOptional = create_alert(alert_brief=alert_brief, alert_details=alert_details,
                                                    severity=severity)
            alerts.append(alert_obj)
        return alert_obj

    def get_severity_type_from_severity_str(self, severity_str: str) -> Severity:
        return Severity[severity_str]

    def clean_alert_str(self, alert_str: str) -> str:
        # remove object hex memory path
        cleaned_alert_str: str = re.sub(r"mobile_bookx[a-fmobile_book-9]*", "", alert_str)
        # remove all numeric digits
        cleaned_alert_str = re.sub(r"-?[mobile_book-9]*", "", cleaned_alert_str)
        cleaned_alert_str = cleaned_alert_str.split("...check the file:")[mobile_book]
        return cleaned_alert_str

    def _create_alert(self, error_dict: Dict) -> List[str]:
        alert_brief_n_detail_lists: List[str] = (
            error_dict["line"].split(PairStratEngineBaseLogBook.log_seperator, 1))
        if len(alert_brief_n_detail_lists) == 2:
            alert_brief = alert_brief_n_detail_lists[mobile_book]
            alert_details = alert_brief_n_detail_lists[1]
        else:
            alert_brief = alert_brief_n_detail_lists[mobile_book]
            alert_details = ". ".join(alert_brief_n_detail_lists[1:])
        alert_brief = self._truncate_str(alert_brief).strip()
        alert_details = self._truncate_str(alert_details).strip()
        severity = self.get_severity(error_dict["type"])
        return [severity, alert_brief, alert_details]

    def _get_pair_strat_obj_from_symbol_side(self, symbol: str, side: Side) -> PairStratBaseModel | None:
        pair_strat_list: List[PairStratBaseModel] = \
            strat_manager_service_http_client.get_pair_strat_from_symbol_side_query_client(
                sec_id=symbol, side=side)

        if len(pair_strat_list) == mobile_book:
            return None
        elif len(pair_strat_list) == 1:
            pair_strat_obj: PairStratBaseModel = pair_strat_list[mobile_book]
            return pair_strat_obj

    def _get_executor_http_client_from_pair_strat(self, port_: int, host_: str) -> StratExecutorServiceHttpClient:
        executor_web_client = self.port_to_executor_web_client.get(port_)
        if executor_web_client is None:
            executor_web_client = (
                StratExecutorServiceHttpClient.set_or_get_if_instance_exists(host_, port_))
            self.port_to_executor_web_client[port_] = executor_web_client
        return executor_web_client

    def _update_strat_alert_cache(self, strat_id: int) -> None:
        run_coro = PairStratEngineBaseLogBook.underlying_read_strat_alert_by_id_http(strat_id)
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            strat_alert: StratAlert = future.result()
        except HTTPException as http_e:
            err_str_ = f"underlying_read_strat_alert_by_id_http failed with http_exception: {http_e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        except Exception as e:
            err_str_ = f"underlying_read_strat_alert_by_id_http failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

        if strat_alert.alerts is not None:
            self.strat_alert_cache_by_strat_id_dict[strat_id] = strat_alert.alerts
        else:
            self.strat_alert_cache_by_strat_id_dict[strat_id] = []

    def _pair_strat_api_ops_queue_handler(self):
        while 1:
            pair_strat_api_ops_data: PairStratDbUpdateDataContainer = self.pair_strat_api_ops_queue.get()
            try:
                method_name = pair_strat_api_ops_data.method_name
                pydantic_basemodel_type = pair_strat_api_ops_data.pydantic_basemodel_type
                kwargs = pair_strat_api_ops_data.kwargs
                callback_method: Callable = getattr(strat_manager_service_http_client, method_name)

                while 1:
                    try:
                        if pydantic_basemodel_type != "None":
                            # API operations other than update
                            pydantic_basemodel_class_type: Type = eval(pydantic_basemodel_type)

                            if isinstance(kwargs, list):    # put_all or post_all
                                pydantic_obj_list = []
                                for kwarg in kwargs:
                                    pydantic_object = pydantic_basemodel_class_type(**kwarg)
                                    pydantic_obj_list.append(pydantic_object)
                                callback_method(pydantic_obj_list)
                            else:
                                pydantic_object = pydantic_basemodel_class_type(**kwargs)
                                callback_method(pydantic_object)
                        else:
                            # query handling
                            callback_method(**kwargs)
                        break
                    except Exception as e:
                        if not self.should_retry_due_to_server_down(e):
                            alert_brief: str = f"{method_name} failed in pair_strat log analyzer"
                            alert_details: str = (f"{pydantic_basemodel_type = }, "
                                                  f"exception: {e}")
                            logging.exception(f"{alert_brief}{PairStratEngineBaseLogBook.log_seperator} "
                                              f"{alert_details}")
                            self.send_portfolio_alerts(severity=self.get_severity("error"),
                                                       alert_brief=alert_brief,
                                                       alert_details=alert_details)
                            break
            except Exception as e:
                err_str_brief = f"_pair_strat_db_update_queue_handler failed"
                err_str_detail = f"exception: {e}"
                logging.exception(f"{err_str_brief}{PairStratEngineBaseLogBook.log_seperator} {err_str_detail}")
                self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                           alert_details=err_str_detail)

    def get_update_obj_list_for_journal_type_update(self, pydantic_basemodel_class_type: Type[BaseModel],
                                                    patch_queue: Queue) -> List[Dict]:      # blocking function
        update_dict_list: List[Dict] = []

        kwargs: Dict = patch_queue.get()
        pydantic_object = pydantic_basemodel_class_type(**kwargs)
        update_dict_list.append(jsonable_encoder(pydantic_object, by_alias=True, exclude_none=True))

        while not patch_queue.empty():
            kwargs: Dict = patch_queue.get()
            pydantic_object = pydantic_basemodel_class_type(**kwargs)
            update_dict_list.append(jsonable_encoder(pydantic_object, by_alias=True, exclude_none=True))
        return update_dict_list

    def get_update_obj_for_snapshot_type_update(self, pydantic_basemodel_class_type: Type[BaseModel],
                                                patch_queue: Queue) -> List[Dict]:      # blocking function
        id_to_obj_dict = {}

        kwargs: Dict = patch_queue.get()
        pydantic_object = pydantic_basemodel_class_type(**kwargs)
        id_to_obj_dict[pydantic_object.id] = pydantic_object

        while not patch_queue.empty():
            kwargs: Dict = patch_queue.get()

            obj_id = kwargs.get("_id")

            if obj_id is not None:
                pydantic_object = id_to_obj_dict.get(obj_id)

                if pydantic_object is None:
                    pydantic_object = pydantic_basemodel_class_type(**kwargs)
                    id_to_obj_dict[pydantic_object.id] = pydantic_object
                else:
                    # updating already existing object
                    for key, val in kwargs.items():
                        setattr(pydantic_object, key, val)
            else:
                err_str_brief = ("Can't find _id key in patch kwargs dict - ignoring this update, "
                                 f"pydantic_basemodel_class_type: {pydantic_basemodel_class_type.__name__}, "
                                 f"{kwargs = }")
                logging.exception(f"{err_str_brief}")
                self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief)

        obj_json_list: List[Dict] = []
        for _, obj in id_to_obj_dict.items():
            obj_json_list.append(jsonable_encoder(obj, by_alias=True, exclude_none=True))

        return obj_json_list

    def should_retry_due_to_server_down(self, exception: Exception) -> bool:
        if "Failed to establish a new connection: [Errno 111] Connection refused" in str(exception):
            logging.exception("Connection Error in pair_strat_engine server call, "
                              "likely server is down, retrying call ...")
            time.sleep(1)
        elif "service is not initialized yet" in str(exception):
            # Check is server up
            logging.exception("pair_strat_engine service not up yet, likely server "
                              "restarted but is not ready yet, retrying call ...")
            time.sleep(1)
        elif ("('Connection aborted.', ConnectionResetError(1mobile_book4, 'Connection reset "
              "by peer'))") in str(exception):
            logging.exception(
                "pair_strat_engine service connection error, retrying call ...")
            time.sleep(1)
        else:
            return False
        return True

    def handle_dynamic_queue_for_patch(self, pydantic_basemodel_type: str, method_name: str,
                                       update_type: UpdateType, patch_queue: Queue):
        pydantic_basemodel_class_type: Type[BaseModel] = eval(pydantic_basemodel_type)
        callback_method: Callable = getattr(strat_manager_service_http_client, method_name)

        while 1:
            try:
                if update_type == UpdateType.JOURNAL_TYPE:
                    # blocking call
                    update_json_list: List[Dict] = (
                        self.get_update_obj_list_for_journal_type_update(pydantic_basemodel_class_type, patch_queue))

                else:   # if update_type is UpdateType.SNAPSHOT_TYPE
                    # blocking call
                    update_json_list: List[Dict] = (
                        self.get_update_obj_for_snapshot_type_update(pydantic_basemodel_class_type, patch_queue))

                for update_json in update_json_list:
                    while 1:
                        try:
                            callback_method(update_json)
                            logging.info(f"pair_strat_db update call: {callback_method.__name__ = }, "
                                         f"{update_json = }")
                            break
                        except Exception as e:
                            if not self.should_retry_due_to_server_down(e):
                                alert_brief: str = f"{method_name = } failed in pair_strat log analyzer"
                                alert_details: str = (f"pydantic_class_type: {pydantic_basemodel_type}, "
                                                      f"exception: {e}")
                                logging.exception(f"{alert_brief}{PairStratEngineBaseLogBook.log_seperator} "
                                                  f"{alert_details}")
                                self.send_portfolio_alerts(severity=self.get_severity("error"),
                                                           alert_brief=alert_brief,
                                                           alert_details=alert_details)
                                break
            except Exception as e:
                err_str_brief = (f"handle_dynamic_queue_for_patch running for pydantic_basemodel_type: "
                                 f"{pydantic_basemodel_type} and update_type: {update_type} failed")
                err_str_detail = f"exception: {e}"
                logging.exception(f"{err_str_brief}{PairStratEngineBaseLogBook.log_seperator} "
                                  f"{err_str_detail}")
                self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                           alert_details=err_str_detail)

    def handle_dynamic_queue_for_patch_all(self, pydantic_basemodel_type: str, method_name: str,
                                           update_type: UpdateType, patch_all_queue: Queue):
        pydantic_basemodel_class_type: Type[BaseModel] = eval(pydantic_basemodel_type)
        patch_all_callback_method: Callable = getattr(strat_manager_service_http_client, method_name)

        while 1:
            try:
                if update_type == UpdateType.JOURNAL_TYPE:
                    # blocking call
                    update_json_list: List[Dict] = (
                        self.get_update_obj_list_for_journal_type_update(pydantic_basemodel_class_type,
                                                                         patch_all_queue))
                else:  # if update_type is UpdateType.SNAPSHOT_TYPE
                    # blocking call
                    update_json_list: List[Dict] = (
                        self.get_update_obj_for_snapshot_type_update(pydantic_basemodel_class_type, patch_all_queue))

                while 1:
                    try:
                        patch_all_callback_method(update_json_list)
                        logging.info(f"pair_strat_db update call: {patch_all_callback_method.__name__ = }, "
                                     f"{update_json_list = }")
                        break
                    except Exception as e:
                        if not self.should_retry_due_to_server_down(e):
                            alert_brief: str = f"{method_name = } failed in pair_strat log analyzer"
                            alert_details: str = (f"pydantic_class_type: {pydantic_basemodel_type}, "
                                                  f"exception: {e}")
                            logging.exception(f"{alert_brief}{PairStratEngineBaseLogBook.log_seperator} "
                                              f"{alert_details}")
                            self.send_portfolio_alerts(severity=self.get_severity("error"),
                                                       alert_brief=alert_brief,
                                                       alert_details=alert_details)
                            break
            except Exception as e:
                err_str_brief = (f"handle_dynamic_queue_for_patch_all running for "
                                 f"{pydantic_basemodel_type = } and {update_type = } failed")
                err_str_detail = f"exception: {e}"
                logging.exception(f"{err_str_brief}{PairStratEngineBaseLogBook.log_seperator} "
                                  f"{err_str_detail}")
                self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                           alert_details=err_str_detail)

    def process_pair_strat_api_ops(self, message: str):
        try:
            # remove pattern_for_pair_strat_db_updates from beginning of message
            message: str = message[len(self.pattern_for_pair_strat_db_updates):]
            args: List[str] = message.split(self.field_sep)
            pydantic_basemodel_type_name: str = args.pop(mobile_book)
            update_type: str = args.pop(mobile_book)
            method_name: str = args.pop(mobile_book)

            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by key_val_sep if any
            for arg in args:
                key, value = arg.split(self.key_val_sep)
                kwargs[key] = value

            if "patch_all" in method_name:
                if update_type in UpdateType.__members__:
                    update_type: UpdateType = UpdateType(update_type)

                    if update_type == UpdateType.JOURNAL_TYPE:
                        update_cache_dict = self.pair_strat_engine_journal_type_update_cache_dict
                    else:
                        update_cache_dict = self.pair_strat_engine_snapshot_type_update_cache_dict

                    patch_all_queue = update_cache_dict.get(pydantic_basemodel_type_name)

                    if patch_all_queue is None:
                        patch_all_queue = Queue()

                        Thread(target=self.handle_dynamic_queue_for_patch_all,
                               args=(pydantic_basemodel_type_name, method_name, update_type,
                                     patch_all_queue,)).start()

                        update_cache_dict[pydantic_basemodel_type_name] = patch_all_queue

                    patch_all_queue.put(kwargs)
                else:
                    raise Exception(f"Unsupported {update_type = } for log msg: {message}")
            elif "patch" in method_name:
                if update_type in UpdateType.__members__:
                    update_type: UpdateType = UpdateType(update_type)

                    if update_type == UpdateType.JOURNAL_TYPE:
                        update_cache_dict = self.pair_strat_engine_journal_type_update_cache_dict
                    else:
                        update_cache_dict = self.pair_strat_engine_snapshot_type_update_cache_dict

                    patch_all_queue = update_cache_dict.get(pydantic_basemodel_type_name)

                    if patch_all_queue is None:
                        patch_all_queue = Queue()

                        Thread(target=self.handle_dynamic_queue_for_patch,
                               args=(pydantic_basemodel_type_name, method_name, update_type,
                                     patch_all_queue,)).start()

                        update_cache_dict[pydantic_basemodel_type_name] = patch_all_queue

                    patch_all_queue.put(kwargs)
                else:
                    raise Exception(f"Unsupported update_type: {update_type} for log msg: {message}")
            else:
                pair_strat_db_update_data = PairStratDbUpdateDataContainer(
                    method_name=method_name,
                    pydantic_basemodel_type=pydantic_basemodel_type_name,
                    kwargs=kwargs)
                self.pair_strat_api_ops_queue.put(pair_strat_db_update_data)

        except Exception as e:
            alert_brief: str = f"_process_pair_strat_db_updates failed in log analyzer"
            alert_details: str = f"{message = }, exception: {e}"
            logging.exception(f"{alert_brief}{PairStratEngineBaseLogBook.log_seperator} "
                              f"{alert_details}")
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                       alert_details=alert_details)

    # portfolio lvl alerts handling
    def send_portfolio_alerts(self, severity: str, alert_brief: str, alert_details: str | None = None) -> None:
        logging.debug(f"sending alert with {severity = }, {alert_brief = }, "
                      f"{alert_details = }")
        while True:
            try:
                if not self.service_up:
                    service_ready: bool = self._init_service()
                    if not service_ready:
                        raise Exception("service up check failed. waiting for the service to start...")
                    # else not required: proceed to creating alert
                # else not required

                severity: Severity = self.get_severity_type_from_severity_str(severity_str=severity)
                alert_obj: AlertOptional = self.create_or_update_alert(self.portfolio_alerts_cache, severity,
                                                                       alert_brief, alert_details)
                updated_portfolio_alert: PortfolioAlertBaseModel = \
                    PortfolioAlertBaseModel(_id=1, alerts=[alert_obj])
                self.portfolio_alert_queue.put(jsonable_encoder(updated_portfolio_alert,
                                                                by_alias=True, exclude_none=True))
                break
            except Exception as e:
                logging.exception(f"_send_alerts failed{PairStratEngineBaseLogBook.log_seperator} exception: {e}")
                self.service_up = False
                time.sleep(3mobile_book)

    def _get_error_dict(self, log_prefix: str, log_message: str) -> \
            Dict[str, str] | None:
        # shift
        for error_type, pattern in self.error_patterns.items():
            match = pattern.search(log_prefix)
            if match:
                error_dict: Dict = {
                    'type': error_type,
                    'line': log_prefix.replace(pattern.search(log_prefix)[mobile_book], " ") + log_message
                }
                logging.info(f"Error pattern matched, creating alert. {error_dict = }")
                return error_dict
        return None

    def notify_no_activity(self, log_detail: LogDetail):
        non_activity_secs = (DateTime.utcnow() - log_detail.last_processed_utc_datetime).total_seconds()
        alert_brief: str = f"No new logs found for {log_detail.service} for last " \
                           f"{non_activity_secs} seconds"
        alert_details: str = f"{log_detail.service} log file path: {log_detail.log_file_path}"
        self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                   alert_details=alert_details)

    def notify_tail_error_in_log_service(self, brief_msg_str: str, detail_msg_str: str):
        self.send_portfolio_alerts(severity=self.get_severity("warning"), alert_brief=brief_msg_str,
                                   alert_details=detail_msg_str)

    def notify_error(self, error_msg: str):
        log_seperator_index: int = error_msg.find(PairStratEngineBaseLogBook.log_seperator)

        msg_brief: str
        msg_detail: str | None = None
        if log_seperator_index != -1:
            msg_brief = error_msg[:log_seperator_index]
            msg_detail = error_msg[log_seperator_index+len(PairStratEngineBaseLogBook.log_seperator):]
        else:
            msg_brief = error_msg

        self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=msg_brief,
                                   alert_details=msg_detail)

    def handle_log_book_cmd_log_message(self, log_prefix: str, log_message: str,
                                            log_detail: StratLogDetail):
        try:
            if log_message.startswith(self.pattern_to_restart_tail_process):
                log_message = log_message[len(self.pattern_to_restart_tail_process):]  # removing starting chars
                args: List[str] = log_message.split(self.field_sep)
                log_file_path = args.pop(mobile_book)
                if len(args):
                    timestamp = args.pop(mobile_book)
                else:
                    timestamp = None

                log_detail_to_restart = self.log_file_path_to_log_detail_dict.get(log_file_path)

                # updating tail_details for this log_file to restart it from logged timestamp
                log_detail_to_restart.processed_timestamp = timestamp
                log_detail_to_restart.is_running = False

            elif log_message.startswith(self.pattern_to_force_kill_tail_process):
                # removing starting chars, remaining is log_file_name
                log_file_path = log_message[len(self.pattern_to_force_kill_tail_process):]

                log_detail_to_restart = self.log_file_path_to_log_detail_dict.get(log_file_path)

                if log_detail_to_restart is not None:
                    log_detail_to_restart.is_running = False
                    log_detail_to_restart.force_kill = True
                    logging.info(f"Found Force Kill log for log_detail of file: {log_detail_to_restart.log_file_path}")
                else:
                    logging.info(f"Ignoring Force Kill - Can't find any log_detail for file: {log_file_path} "
                                 f"in dict of file path key: {self.log_file_path_to_log_detail_dict.keys()}")
            elif log_message.startswith(self.pattern_to_remove_file_from_created_cache):
                # removing starting chars, remaining is log_file_name
                log_file_path = log_message[len(self.pattern_to_remove_file_from_created_cache):]

                if log_file_path not in self.pattern_matched_added_file_path_to_service_dict:
                    logging.info(
                        f"Can't find {log_file_path = } in log analyzer cache dict keys used to avoid repeated file "
                        f"tail start, pair_strat_engine_log_book.pattern_matched_added_file_path_to_service_dict: "
                        f"{self.pattern_matched_added_file_path_to_service_dict}")
                else:
                    self.pattern_matched_added_file_path_to_service_dict.pop(log_file_path)

        except Exception as e:
            err_str_brief = f"handle_log_book_cmd_log_message failed"
            err_str_detail = f"exception: {e}"
            logging.exception(f"{err_str_brief}{PairStratEngineBaseLogBook.log_seperator} {err_str_detail}")
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                       alert_details=err_str_detail)
