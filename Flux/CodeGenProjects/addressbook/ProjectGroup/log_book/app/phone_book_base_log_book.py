import logging
import os
import re
import threading
from queue import Queue
from typing import Set
from datetime import timedelta
import inspect

# third-party imports
import pendulum

# Project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from FluxPythonUtils.log_book.log_book import LogDetail, get_transaction_counts_n_timeout_from_config
from FluxPythonUtils.scripts.utility_functions import get_last_log_line_date_time, parse_to_float, is_file_modified
from Flux.PyCodeGenEngine.FluxCodeGenCore.app_log_book import AppLogBook
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client, is_ongoing_strat, Side, UpdateType)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import (
    performance_benchmark_service_http_client, RawPerformanceDataBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.aggregate import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    be_port, basket_book_service_http_client)

LOG_ANALYZER_DATA_DIR = (
        PurePath(__file__).parent.parent / "data"
)

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

portfolio_alert_bulk_update_counts_per_call, portfolio_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("portfolio_alert_configs"),
                                                 is_server_config=False))


# Updating LogDetail to have strat_id_finder_callable
class StratLogDetail(LogDetail, kw_only=True):
    strat_id_find_callable: Callable[[str], int] | None = None


class PairStratDbUpdateDataContainer(msgspec.Struct):
    method_name: str
    basemodel_type: str
    kwargs: Dict[str, Any]
    update_type: UpdateType | None = None


class PhoneBookBaseLogBook(AppLogBook):
    underlying_partial_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_read_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_msgspec_routes import (
            underlying_partial_update_all_portfolio_alert_http, underlying_read_portfolio_alert_http,
            underlying_read_strat_alert_http)
        cls.underlying_partial_update_all_portfolio_alert_http = underlying_partial_update_all_portfolio_alert_http
        cls.underlying_read_portfolio_alert_http = underlying_read_portfolio_alert_http
        cls.underlying_read_strat_alert_http = underlying_read_strat_alert_http

    def __init__(self, log_detail: LogDetail, regex_file_dir_path: str,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        super().__init__(log_detail, regex_file_dir_path, config_yaml_dict,
                         log_prefix_regex_pattern_to_callable_name_dict, debug_mode=debug_mode)
        PhoneBookBaseLogBook.initialize_underlying_http_callables()
        self.market: Market = Market(MarketID.IN)
        self.simulation_mode = simulation_mode
        self.portfolio_alerts_model_exist: bool = False
        self.portfolio_alerts_cache_dict: Dict[str, PortfolioAlertBaseModel] = {}
        self.strat_id_by_symbol_side_dict: Dict[str, int] = {}
        self.strat_alert_cache_dict_by_strat_id_dict: Dict[int, Dict[str, StratAlertBaseModel]] = {}
        self.service_up: bool = False
        self.portfolio_alert_queue: Queue = Queue()
        self.strat_alert_queue: Queue = Queue()
        self.pair_strat_api_ops_queue: Queue = Queue()
        self.raw_performance_data_queue: queue.Queue = queue.Queue()
        self.port_to_executor_web_client: Dict[int, StreetBookServiceHttpClient] = {}
        self.model_type_name_to_patch_queue_cache_dict: Dict[str, Queue] = {}
        self.phone_book_snapshot_type_update_cache_dict: Dict[str, Queue] = {}
        self.field_sep = get_field_seperator_pattern()
        self.key_val_sep = get_key_val_seperator_pattern()
        self.pattern_for_pair_strat_db_updates = get_pattern_for_pair_strat_db_updates()
        self.pattern_to_restart_tail_process: str = get_pattern_to_restart_tail_process()
        self.pattern_to_force_kill_tail_process: str = get_pattern_to_force_kill_tail_process()
        self.pattern_to_remove_file_from_created_cache: str = get_pattern_to_remove_file_from_created_cache()
        self.max_fetch_from_queue = config_yaml_dict.get("max_fetch_from_patch_queue_for_tail_ex")
        if self.max_fetch_from_queue is None:
            self.max_fetch_from_queue = 10  # setting default value
        self.pattern_for_log_simulator = get_pattern_for_log_simulator()

    def _handle_portfolio_alert_queue_err_handler(self, *args):
        err_str_ = (f"_handle_portfolio_alert_queue_err_handler failed in tail executor of process: "
                    f", passed args: {args}")
        log_book_service_http_client.portfolio_alert_fail_logger_query_client(err_str_)

    def _handle_portfolio_alert_query_call_from_alert_queue_handler(
            self, portfolio_alerts: List[PortfolioAlertBaseModel]):
        portfolio_alert_data_list: List[Dict[str, Any]] = []
        for portfolio_alert in portfolio_alerts:
            portfolio_alert_dict = {
                "severity": portfolio_alert.severity,
                "alert_brief": portfolio_alert.alert_brief
            }
            if portfolio_alert.alert_meta:
                portfolio_alert_dict.update(alert_meta=portfolio_alert.alert_meta)
            portfolio_alert_data_list.append(portfolio_alert_dict)

        log_book_service_http_client.handle_portfolio_alerts_from_tail_executor_query_client(
            portfolio_alert_data_list)
        return portfolio_alerts

    def _handle_portfolio_alert_queue(self):
        alert_queue_handler_for_create_only(
            self.is_running, self.portfolio_alert_queue, portfolio_alert_bulk_update_counts_per_call,
            portfolio_alert_bulk_update_timeout,
            self._handle_portfolio_alert_query_call_from_alert_queue_handler,
            self._handle_portfolio_alert_queue_err_handler)

    def handle_raw_performance_data_queue_err_handler(self, model_obj_list):
        pass

    def _handle_raw_performance_data_queue(self):
        raw_performance_data_bulk_create_counts_per_call, raw_perf_data_bulk_create_timeout = (
            get_transaction_counts_n_timeout_from_config(self.config_yaml_dict.get("raw_perf_data_config")))
        client_connection_fail_retry_secs = self.config_yaml_dict.get("perf_bench_client_connection_fail_retry_secs")
        if client_connection_fail_retry_secs:
            client_connection_fail_retry_secs = parse_to_int(client_connection_fail_retry_secs)
        alert_queue_handler_for_create_only(
            self.is_running, self.raw_performance_data_queue, raw_performance_data_bulk_create_counts_per_call,
            raw_perf_data_bulk_create_timeout,
            performance_benchmark_service_http_client.create_all_raw_performance_data_client,
            self.handle_raw_performance_data_queue_err_handler,
            client_connection_fail_retry_secs=client_connection_fail_retry_secs)

    def _create_alert(self, error_dict: Dict) -> Tuple[str, str, str]:
        alert_brief_n_detail_lists: List[str] = (
            error_dict["line"].split(PhoneBookBaseLogBook.log_seperator, 1))
        if len(alert_brief_n_detail_lists) == 2:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = alert_brief_n_detail_lists[1]
        else:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = ". ".join(alert_brief_n_detail_lists[1:])

        alert_brief = self._truncate_str(alert_brief).strip()
        alert_details = self._truncate_str(alert_details).strip()
        severity = self.get_severity(error_dict["type"])
        return severity, alert_brief, alert_details

    def _get_pair_strat_obj_from_symbol_side(self, symbol: str, side: Side) -> PairStratBaseModel | None:
        pair_strat_list: List[PairStratBaseModel] = \
            (email_book_service_http_client.
             get_ongoing_or_single_exact_non_ongoing_pair_strat_from_symbol_side_query_client(
                sec_id=symbol, side=side))

        if len(pair_strat_list) == 0:
            return None
        elif len(pair_strat_list) == 1:
            pair_strat_obj: PairStratBaseModel = pair_strat_list[0]
            return pair_strat_obj

    def _get_executor_http_client_from_pair_strat(self, port_: int, host_: str) -> StreetBookServiceHttpClient:
        executor_web_client = self.port_to_executor_web_client.get(port_)
        if executor_web_client is None:
            executor_web_client = (
                StreetBookServiceHttpClient.set_or_get_if_instance_exists(host_, port_))
            self.port_to_executor_web_client[port_] = executor_web_client
        return executor_web_client

    def _pair_strat_api_ops_queue_handler(self):
        while 1:
            pair_strat_api_ops_data: PairStratDbUpdateDataContainer = self.pair_strat_api_ops_queue.get()

            # handling graceful exit of this thread
            if pair_strat_api_ops_data == "EXIT":
                logging.info(f">> Exiting {threading.current_thread().name}")
                return

            try:
                method_name = pair_strat_api_ops_data.method_name
                model_basemodel_type = pair_strat_api_ops_data.basemodel_type
                kwargs = pair_strat_api_ops_data.kwargs
                callback_method: Callable = getattr(email_book_service_http_client, method_name)

                while 1:
                    try:
                        if model_basemodel_type != "None":
                            # API operations other than update
                            basemodel_class_type: Type[MsgspecModel] = eval(model_basemodel_type)

                            if isinstance(kwargs, list):  # put_all or post_all
                                model_obj_list = []
                                for kwarg in kwargs:
                                    model_object = basemodel_class_type.from_dict(kwarg)
                                    model_obj_list.append(model_object)
                                callback_method(model_obj_list)
                            else:
                                model_object = basemodel_class_type.from_dict(kwargs)
                                callback_method(model_object)
                        else:
                            # query handling
                            callback_method(**kwargs)
                        break
                    except Exception as e:
                        if not should_retry_due_to_server_down(e):
                            alert_brief: str = f"{method_name} failed in pair_strat log analyzer"
                            alert_details: str = f"{model_basemodel_type=}, exception: {e}"
                            logging.exception(f"{alert_brief}{PhoneBookBaseLogBook.log_seperator} "
                                              f"{alert_details}")
                            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                                            inspect.currentframe().f_lineno, DateTime.utcnow(),
                                                            alert_details)
                            self.send_portfolio_alerts(severity=self.get_severity("error"),
                                                       alert_brief=alert_brief,
                                                       alert_meta=alert_meta)
                            break
            except Exception as e:
                err_str_brief = f"_pair_strat_db_update_queue_handler failed"
                err_str_detail = f"exception: {e}"
                logging.exception(f"{err_str_brief}{PhoneBookBaseLogBook.log_seperator} {err_str_detail}")
                alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                                inspect.currentframe().f_lineno, DateTime.utcnow(),
                                                err_str_detail)
                self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                           alert_meta=alert_meta)

    def _snapshot_type_callable_err_handler(self, model_basemodel_class_type: Type[BaseModel], kwargs):
        err_str_brief = ("Can't find _id key in patch kwargs dict - ignoring this update in "
                         "get_update_obj_for_snapshot_type_update, "
                         f"model_basemodel_class_type: {model_basemodel_class_type.__name__}, "
                         f"{kwargs=}")
        logging.exception(f"{err_str_brief}")
        alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                        inspect.currentframe().f_lineno, DateTime.utcnow())
        self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                   alert_meta=alert_meta)

    def dynamic_queue_handler_err_handler(self, basemodel_type: str, update_type: UpdateType,
                                          err_str_: Exception):
        err_str_brief = (f"handle_dynamic_queue_for_patch running for basemodel_type: "
                         f"{basemodel_type} and update_type: {update_type} failed")
        err_str_detail = f"exception: {err_str_}"
        logging.exception(f"{err_str_brief}{PhoneBookBaseLogBook.log_seperator} "
                          f"{err_str_detail}")
        alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                        inspect.currentframe().f_lineno, DateTime.utcnow(),
                                        err_str_detail)
        self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=err_str_brief,
                                   alert_meta=alert_meta)

    def _get_update_obj_list_for_journal_type_update(
            self, basemodel_class_type: Type[BaseModel], update_type: str, method_name: str,
            patch_queue: Queue, max_fetch_from_queue: int, update_json_list: List[MsgspecModel | Dict],
            parse_to_model: bool | None = None):
        # blocking function
        update_json_list = get_update_obj_list_for_journal_type_update(
            basemodel_class_type, update_type, method_name, patch_queue,
            max_fetch_from_queue, update_json_list, parse_to_model=parse_to_model)

        # handling interrupt
        if update_json_list == "EXIT":
            return "EXIT"

        container_json = {"update_json_list": update_json_list, "update_type": update_type,
                          "basemodel_type_name": basemodel_class_type.__name__,
                          "method_name": method_name}
        return container_json

    def get_update_obj_for_snapshot_type_update(
            self, msgspec_class_type: Type[MsgspecModel], update_type: str, method_name: str,
            patch_queue: Queue, max_fetch_from_queue: int, err_handler_callable: Callable,
            update_res: Dict,
            parse_to_model: bool | None = None):
        if update_res:
            update_res = update_res.get("update_json_list")
        else:
            update_res = []

        # blocking function
        update_json_list = get_update_obj_for_snapshot_type_update(
            msgspec_class_type, update_type, method_name, patch_queue,
            max_fetch_from_queue, err_handler_callable, update_res, parse_to_model)

        # handling interrupt
        if update_json_list == "EXIT":
            return "EXIT"

        container_json = {"update_json_list": update_json_list, "update_type": update_type,
                          "basemodel_type_name": msgspec_class_type.__name__,
                          "method_name": method_name}
        return container_json

    def process_pair_strat_api_ops(self, message: str):
        try:
            # remove pattern_for_pair_strat_db_updates from beginning of message
            message: str = message[len(self.pattern_for_pair_strat_db_updates):]
            args: List[str] = message.split(self.field_sep)
            basemodel_type_name: str = args.pop(0)
            update_type: str = args.pop(0)
            method_name: str = args.pop(0)

            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by key_val_sep if any
            for arg in args:
                key, value = arg.split(self.key_val_sep)
                kwargs[key] = value

            handle_patch_db_queue_updater(update_type, self.model_type_name_to_patch_queue_cache_dict,
                                          basemodel_type_name, method_name, kwargs,
                                          self._get_update_obj_list_for_journal_type_update,
                                          self.get_update_obj_for_snapshot_type_update,
                                          photo_book_service_http_client.process_strat_view_updates_query_client,
                                          self.dynamic_queue_handler_err_handler, self.max_fetch_from_queue,
                                          self._snapshot_type_callable_err_handler)
        except Exception as e:
            alert_brief: str = f"_process_pair_strat_db_updates failed in log analyzer"
            alert_details: str = f"{message=}, exception: {e}"
            logging.exception(f"{alert_brief}{PhoneBookBaseLogBook.log_seperator} "
                              f"{alert_details}")
            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(),
                                            alert_details)
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                       alert_meta=alert_meta)

    # portfolio lvl alerts handling
    def send_portfolio_alerts(self, severity: str, alert_brief: str,
                              alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending alert with {severity=}, {alert_brief=}, "
                      f"{alert_meta=}")
        try:
            if not self.service_up:
                self.service_up: bool = init_service(self.portfolio_alerts_cache_dict)
                if not self.service_up:
                    raise Exception("service up check failed. waiting for the service to start...")
                # else not required: proceed to creating alert
            # else not required

            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            create_or_update_alert(self.portfolio_alerts_cache_dict, self.portfolio_alert_queue,
                                   StratAlertBaseModel, PortfolioAlertBaseModel,
                                   severity, alert_brief, alert_meta=alert_meta)
        except Exception as e:
            err_str_ = (f"send_portfolio_alerts failed, exception: {e};;; "
                        f"received: {severity=}, {alert_brief=}, {alert_meta=}")
            logging.exception(err_str_)
            log_book_service_http_client.portfolio_alert_fail_logger_query_client(err_str_)
            self.service_up = False

    def _get_error_dict(self, log_prefix: str, log_message: str) -> \
            Dict[str, str] | None:
        # shift
        for error_type, pattern in self.error_patterns.items():
            match = pattern.search(log_prefix)
            if match:
                error_dict: Dict = {
                    'type': error_type,
                    'line': log_message
                }
                logging.info(f"Error pattern matched, creating alert. {error_dict=}")
                return error_dict
        return None

    def _send_strat_alerts(self, strat_id: int, severity_str: str, alert_brief: str,
                           alert_meta: AlertMeta | None = None) -> None:
        """
        Handling to be implemented to send strat alert in derived class
        """
        raise NotImplementedError

    def send_to_portfolio_or_strat_alert(self, severity: str, alert_brief: str, alert_meta: AlertMeta,
                                         log_detail: LogDetail | StratLogDetail):
        if log_detail.strat_id_find_callable is not None:
            strat_id: int | None = log_detail.strat_id_find_callable(log_detail.log_file_path)
            if strat_id is not None:
                self._send_strat_alerts(strat_id=strat_id, severity_str=severity, alert_brief=alert_brief,
                                        alert_meta=alert_meta)
                return
        # all else case - send to portfolio alert
        self.send_portfolio_alerts(severity=severity, alert_brief=alert_brief, alert_meta=alert_meta)

    def notify_no_activity(self, log_detail: LogDetail):
        if os.path.exists(log_detail.log_file_path):
            _, last_modified_timestamp = is_file_modified(log_detail.log_file_path, log_detail.data_snapshot_version)
            log_detail.data_snapshot_version = last_modified_timestamp
            last_modified_date_time: DateTime = pendulum.from_timestamp(last_modified_timestamp, tz="UTC")
            non_activity_secs: int = int((DateTime.utcnow() - last_modified_date_time).total_seconds())
            if non_activity_secs > log_detail.poll_timeout:
                non_activity_period_description: str
                if non_activity_secs >= 60:
                    non_activity_mins = int(non_activity_secs / 60)
                    non_activity_period_description = f"almost {non_activity_mins} minute(s)"
                else:
                    non_activity_period_description = f"{non_activity_secs} seconds"
                alert_brief: str = (f"No new logs found for {log_detail.service} for last "
                                    f"{non_activity_period_description}")
                alert_details: str = f"{log_detail.service} log file path: {log_detail.log_file_path}"
                alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                                inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
                # log as warning if bartering not started yet
                severity = self.get_severity("warning") if self.market.is_bartering_session_not_started() else (
                    self.get_severity("error"))
                self.send_to_portfolio_or_strat_alert(severity=severity, alert_brief=alert_brief, alert_meta=alert_meta,
                                                      log_detail=log_detail)
            # else not required: new logs are generated but filtered out
        else:
            logging.error(f"notify_no_activity failed, {log_detail.log_file_path=} does not exist")

    def notify_unexpected_activity(self, log_detail: LogDetail):
        alert_brief: str = f"Unexpected: new logs found in {os.path.basename(log_detail.log_file_path)}"
        alert_details: str = f"{log_detail.log_file_path=}"
        alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                        inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
        self.send_to_portfolio_or_strat_alert(severity=self.get_severity("error"), alert_brief=alert_brief,
                                              alert_meta=alert_meta, log_detail=log_detail)

    def notify_tail_event_in_log_service(self, severity: str, brief_msg_str: str, detail_msg_str: str,
                                         source_file_name: str, line_num: int,
                                         alert_create_date_time: DateTime):
        alert_meta = get_alert_meta_obj(self.component_file_path, source_file_name,
                                        line_num, alert_create_date_time, detail_msg_str)
        self.send_portfolio_alerts(severity=self.get_severity(severity), alert_brief=brief_msg_str,
                                   alert_meta=alert_meta)

    def notify_error(self, error_msg: str, source_name: str, line_num: int, log_create_date_time: DateTime):
        log_seperator_index: int = error_msg.find(PhoneBookBaseLogBook.log_seperator)

        msg_brief: str
        msg_detail: str | None = None
        if log_seperator_index != -1:
            msg_brief = error_msg[:log_seperator_index]
            msg_detail = error_msg[log_seperator_index + len(PhoneBookBaseLogBook.log_seperator):]
        else:
            msg_brief = error_msg
        alert_meta = get_alert_meta_obj(self.component_file_path, source_name,
                                        line_num, log_create_date_time, msg_detail)
        self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=msg_brief,
                                   alert_meta=alert_meta)

    def _process_barter_simulator_message(self, message: str) -> None:
        try:
            if not self.simulation_mode:
                raise Exception("Received barter simulator message but log analyzer not running in simulation mode")
            # remove pattern_for_log_simulator from beginning of message
            message: str = message[len(self.pattern_for_log_simulator):]
            args: List[str] = message.split(self.field_sep)
            method_name: str = args.pop(0)
            host: str = args.pop(0)
            port: int = parse_to_int(args.pop(0))

            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by key_val_sep if any
            for arg in args:
                key, value = arg.split(self.key_val_sep)
                kwargs[key] = value

            if port == be_port:
                executor_web_client = basket_book_service_http_client
            else:
                executor_web_client = self._get_executor_http_client_from_pair_strat(port, host)

            callback_method: Callable = getattr(executor_web_client, method_name)
            callback_method(**kwargs)
            logging.info(f"Called {method_name} with kwargs: {kwargs}")

        except Exception as e:
            alert_brief: str = f"_process_barter_simulator_message failed in log analyzer"
            alert_details: str = f"message: {message}, exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(),
                                            alert_details)
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                       alert_meta=alert_meta)

    def handle_log_simulator_matched_log_message(self, log_prefix: str, log_message: str, log_detail: LogDetail,
                                                 log_date_time: DateTime | None = None,
                                                 log_source_file_name: str | None = None,
                                                 line_num: int | None = None):
        logging.debug(f"Processing log simulator line: {log_message[:200]}...")
        # put in method
        if log_message.startswith(self.pattern_for_log_simulator):
            # handle barter simulator message
            logging.info(f"Barter simulator message: {log_message=}")
            self._process_barter_simulator_message(log_message)
            return

        error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=log_prefix, log_message=log_message)
        if error_dict is not None:
            severity, alert_brief, alert_details = self._create_alert(error_dict)
            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(),
                                            alert_details)
            self.send_portfolio_alerts(severity=severity, alert_brief=alert_brief, alert_meta=alert_meta)
        # else not required: error pattern doesn't match, no alerts to send

    def handle_perf_benchmark_matched_log_message(self, log_prefix: str, log_message: str, log_detail: LogDetail,
                                                  log_date_time: DateTime | None = None,
                                                  log_source_file_name: str | None = None,
                                                  line_num: int | None = None):
        pattern = re.compile(f"{self.timeit_pattern}.*{self.timeit_pattern}")
        if search_obj := re.search(pattern, log_message):
            found_pattern = search_obj.group()
            found_pattern = found_pattern[8:-8]  # removing beginning and ending _timeit_
            found_pattern_list = found_pattern.split(self.timeit_field_separator)  # splitting pattern values
            if len(found_pattern_list) == 3:
                callable_name, start_time, delta = found_pattern_list
                if callable_name != "underlying_create_raw_performance_data_http":
                    raw_performance_data_obj = RawPerformanceDataBaseModel()
                    raw_performance_data_obj.callable_name = callable_name
                    raw_performance_data_obj.start_time = pendulum.parse(start_time)
                    raw_performance_data_obj.delta = parse_to_float(delta)
                    raw_performance_data_obj.project_name = log_detail.service

                    self.raw_performance_data_queue.put(raw_performance_data_obj)
                    logging.debug(f"Created raw_performance_data entry in queue for callable {callable_name} "
                                  f"with start_datetime {start_time}")
                # else not required: avoiding callable underlying_create_raw_performance_data to avoid infinite loop
            else:
                err_str_: str = f"Found timeit pattern but internally only contains {found_pattern_list}, " \
                                f"ideally must contain callable_name, start_time & delta " \
                                f"seperated by '~'"
                logging.exception(err_str_)
        # else not required: if no pattern is matched ignoring this log_message

    def handle_tail_restart(self, log_detail: LogDetail):
        system_datetime: pendulum.DateTime = (
            log_detail.last_processed_utc_datetime.in_timezone(tz=pendulum.local_timezone()))
        system_datetime += timedelta(milliseconds=1)
        restart_datetime: str = system_datetime.format("YYYY-MM-DD HH:mm:ss,SSS")
        logging.warning(f"Restarting tail for {log_detail.log_file_path=} from {restart_datetime=}")
        log_book_service_http_client.log_book_restart_tail_query_client(log_detail.log_file_path,
                                                                                restart_datetime)

