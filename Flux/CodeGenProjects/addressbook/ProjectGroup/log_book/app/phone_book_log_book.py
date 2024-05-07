import multiprocessing
import os
from typing import Set
import signal
import sys

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.log_book.log_book import get_transaction_counts_n_timeout_from_config
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.phone_book_base_log_book import (
    PhoneBookBaseLogBook, StratLogDetail)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client, get_reset_log_book_cache_wrapper_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import PairStratBaseModel
from FluxPythonUtils.scripts.utility_functions import configure_logger


LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

strat_alert_bulk_update_counts_per_call, strat_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("strat_alert_config"), is_server_config=False))


class PhoneBookLogBook(PhoneBookBaseLogBook):
    underlying_partial_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_read_portfolio_alert_by_id_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_by_id_http: Callable[..., Any] | None = None

    def __init__(self, regex_file_dir_path: str, log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        process_name = multiprocessing.current_process().name
        datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
        log_file_name = f"{process_name}_logs_{datetime_str}.log"
        log_dir: PurePath = PurePath(__file__).parent.parent / "log" / "tail_executors"
        configure_logger(logging.DEBUG, log_file_dir_path=str(log_dir),
                         log_file_name=log_file_name)

        logging.info(f"Logging for {process_name}")
        super().__init__(regex_file_dir_path, log_prefix_regex_pattern_to_callable_name_dict, simulation_mode)
        self.pattern_for_pair_strat_db_updates: str = get_pattern_for_pair_strat_db_updates()
        self.symbol_side_pattern: str = get_symbol_side_pattern()
        self.reset_log_book_cache_pattern: str = get_reset_log_book_cache_wrapper_pattern()
        PhoneBookLogBook.initialize_underlying_http_callables()
        if self.simulation_mode:
            print(f"CRITICAL: tail executor for process: {process_name} running in simulation mode...")
            alert_brief: str = "PairStrat Log analyzer running in simulation mode"
            self.send_portfolio_alerts(severity=self.get_severity("critical"), alert_brief=alert_brief)

        # running queue handling for pair_start_api_ops
        Thread(target=self._pair_strat_api_ops_queue_handler, daemon=True, name="db_queue_handler").start()
        logging.info(f"Thread Started: db_queue_handler")

        # running queue handling for portfolio and strat alerts
        self.run_queue_handler()
        # running raw_performance thread
        raw_performance_handler_thread = Thread(target=self._handle_raw_performance_data_queue, daemon=True,
                                                name="raw_performance_handler")
        logging.info(f"Thread Started: raw_performance_handler")

        raw_performance_handler_thread.start()

        self.terminate_triggered: bool = False
        signal.set_wakeup_fd(-1)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signal_type: int, *args) -> None:
        if not self.terminate_triggered:
            super()._signal_handler(signal_type, *args)

            # exiting all threads
            self.pair_strat_api_ops_queue.put("EXIT")
            self.strat_alert_queue.put("EXIT")
            self.portfolio_alert_queue.put("EXIT")
            self.raw_performance_data_queue.put("EXIT")

            for _, queue_ in self.pydantic_type_name_to_patch_queue_cache_dict.items():
                queue_.put("EXIT")
        # else not required: avoiding multiple terminate calls

    def _handle_strat_alert_queue_err_handler(self, *args):
        try:
            pydantic_obj_list: List[StratAlertBaseModel] = args[0]     # single unprocessed pydantic object is passed
            for pydantic_obj in pydantic_obj_list:
                self.send_portfolio_alerts(pydantic_obj.severity, pydantic_obj.alert_brief, pydantic_obj.alert_details)
        except Exception as e:
            err_str_ = f"_handle_strat_alert_queue_err_handler failed, passed args: {args};;; exception: {e}"
            log_book_service_http_client.portfolio_alert_fail_logger_query_client(err_str_)

    def _handle_strat_alert_query_call_from_alert_queue_handler(self, strat_alerts: List[StratAlertBaseModel]):
        strat_alert_data_list: List[Dict[str, Any]] = []
        for strat_alert in strat_alerts:
            strat_alert_data_list.append({
                "strat_id": strat_alert.strat_id,
                "severity": strat_alert.severity,
                "alert_brief": strat_alert.alert_brief,
                "alert_details": strat_alert.alert_details
            })
        log_book_service_http_client.handle_strat_alerts_from_tail_executor_query_client(strat_alert_data_list)
        return strat_alerts

    def _handle_strat_alert_queue(self):
        alert_queue_handler(
            self.is_running, self.strat_alert_queue, strat_alert_bulk_update_counts_per_call,
            strat_alert_bulk_update_timeout,
            self._handle_strat_alert_query_call_from_alert_queue_handler,
            self._handle_strat_alert_queue_err_handler)

    def run_queue_handler(self):
        portfolio_alert_handler_thread = Thread(target=self._handle_portfolio_alert_queue, daemon=True,
                                                name="Portfolio_alert_handler")
        logging.info(f"Thread Started: Portfolio_alert_handler")

        strat_alert_handler_thread = Thread(target=self._handle_strat_alert_queue, daemon=True,
                                            name="strat_alert_handler")
        logging.info(f"Thread Started: strat_alert_handler")

        portfolio_alert_handler_thread.start()
        strat_alert_handler_thread.start()

    def _handle_strat_alert_exception(self, message: str, e: Exception) -> None:
        msg_brief_n_detail = message.split(PhoneBookBaseLogBook.log_seperator)
        msg_detail = f"_process_strat_alert_message failed with exception: {e}"
        if len(msg_brief_n_detail) == 2:
            msg_brief = msg_brief_n_detail[0]
            msg_detail += f", strat_detail: {msg_brief_n_detail[1]}"
        else:
            msg_brief = msg_brief_n_detail[0]

        logging.exception(f"_process_strat_alert_message failed - {message = }, exception: {e}")
        self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=msg_brief,
                                   alert_details=msg_detail)

    def _process_strat_alert_message_with_symbol_side(self, prefix: str, message: str, matched_text: str) -> None:
        try:
            log_message: str = message.replace(self.symbol_side_pattern, "")
            error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=prefix, log_message=log_message)

            # if error pattern does not match, ignore creating alert
            if error_dict is None:
                return

            args: str = matched_text.replace(self.symbol_side_pattern, "").strip()
            symbol_side_set: Set = set()

            # kwargs separated by "," if any
            for arg in args.split(","):
                key, value = [x.strip() for x in arg.split("=")]
                symbol_side_set.add(value)

            if len(symbol_side_set) == 0:
                raise Exception("no symbol-side pair found while creating strat alert, ")

            symbol_side: str = list(symbol_side_set)[0]
            symbol, side = symbol_side.split("-")
            strat_id: int | None = self.strat_id_by_symbol_side_dict.get(symbol_side)

            if strat_id is None or self.strat_alert_cache_dict_by_strat_id_dict.get(strat_id) is None:

                pair_strat_obj: PairStratBaseModel = self._get_pair_strat_obj_from_symbol_side(symbol, side)
                if pair_strat_obj is None:
                    raise Exception(f"No pair strat found for symbol_side: {symbol_side}")
                if not pair_strat_obj.is_executor_running:
                    raise Exception(f"StartExecutor Server not running for pair_strat: {pair_strat_obj}")

                strat_id = pair_strat_obj.id
                update_strat_alert_cache(strat_id, self.strat_alert_cache_dict_by_strat_id_dict,
                                         log_book_service_http_client.filtered_strat_alert_by_strat_id_query_client)
                self.strat_id_by_symbol_side_dict[symbol_side] = strat_id
            # else not required: alert cache exists

            severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)
            self._send_strat_alerts(strat_id, severity, alert_brief, alert_details)
        except Exception as e:
            self._handle_strat_alert_exception(message, e)

    def process_strat_alert_message_with_symbol_side(self, prefix: str, message: str) -> None:
        try:
            pattern: re.Pattern = re.compile(f"{self.symbol_side_pattern}(.*?){self.symbol_side_pattern}")
            match = pattern.search(message)
            if not match:
                raise Exception("unexpected error in _process_strat_alert_message. strat alert pattern not matched")

            matched_text = match[0]
            self._process_strat_alert_message_with_symbol_side(prefix, message, matched_text)
        except Exception as e:
            self._handle_strat_alert_exception(message, e)

    def process_strat_alert_message_with_strat_id(self, prefix: str, message: str,
                                                  pair_strat_id: int | None = None) -> None:
        try:
            error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=prefix, log_message=message)

            # if error pattern does not match, ignore creating alert
            if error_dict is None:
                return

            strat_id = pair_strat_id
            if self.strat_alert_cache_dict_by_strat_id_dict.get(strat_id) is None:
                try:
                    pair_strat: PairStratBaseModel = email_book_service_http_client.get_pair_strat_client(strat_id)
                except Exception as e:
                    raise Exception(f"get_pair_strat_client failed: Can't find pair_start with id: {strat_id}")
                else:
                    if not pair_strat.is_executor_running:
                        raise Exception(f"StartExecutor Server not running for pair_strat: {pair_strat}")

                update_strat_alert_cache(strat_id, self.strat_alert_cache_dict_by_strat_id_dict,
                                         log_book_service_http_client.filtered_strat_alert_by_strat_id_query_client)
                symbol_side = (f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}-"
                               f"{pair_strat.pair_strat_params.strat_leg1.side}")
                self.strat_id_by_symbol_side_dict[symbol_side] = strat_id

            severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)
            self._send_strat_alerts(strat_id, severity, alert_brief, alert_details)
        except Exception as e:
            self._handle_strat_alert_exception(message, e)

    # strat lvl alert handling
    def _send_strat_alerts(self, strat_id: int, severity: str, alert_brief: str,
                           alert_details: str | None = None) -> None:
        logging.debug(f"sending strat alert with {strat_id = }, {severity = }, "
                      f"{alert_brief = }, {alert_details = }")
        try:
            if not self.service_up:
                raise Exception("service up check failed. waiting for the service to start...")
            # else not required

            if not alert_details:
                alert_details = None
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            create_or_update_alert(self.strat_alert_cache_dict_by_strat_id_dict[strat_id],
                                   self.strat_alert_queue,
                                   StratAlertBaseModel, PortfolioAlertBaseModel,
                                   severity, alert_brief, alert_details, strat_id)
        except Exception as e:
            err_msg: str = (f"_send_strat_alerts failed, exception: {e} received {strat_id = }, "
                            f"{severity = }, {alert_brief = }, {alert_details = }")
            logging.exception(err_msg)
            self.send_portfolio_alerts(severity=PhoneBookBaseLogBook.get_severity("error"),
                                       alert_brief=alert_brief,
                                       alert_details=err_msg)

    def _handle_reset_log_book_cache(self, matched_pattern):
        try:
            matched_pattern: str = matched_pattern.replace(self.reset_log_book_cache_pattern, "").strip()

            strat_key = matched_pattern.split(self.symbol_side_pattern)[-1]
            strat_id = strat_key.split("_")[-1]
            strat_id = parse_to_int(strat_id)

            pattern: re.Pattern = re.compile(f"{self.symbol_side_pattern}(.*?){self.symbol_side_pattern}")
            match = pattern.search(matched_pattern)
            if not match:
                raise Exception("unexpected error in _process_strat_alert_message. strat alert pattern not matched")

            matched_text = match[0]

            args: str = matched_text.replace(self.symbol_side_pattern, "").strip()
            symbol_side_set = set()

            # kwargs separated by "," if any
            for arg in args.split(","):
                key, value = [x.strip() for x in arg.split("=")]
                symbol_side_set.add(value)

            for symbol_side in symbol_side_set:
                self.strat_id_by_symbol_side_dict.pop(symbol_side, None)
                logging.info(f"Removed {symbol_side = } from strat_id_by_symbol_side_dict if existed")
            self.strat_alert_cache_dict_by_strat_id_dict.pop(strat_id, None)
            logging.info(f"Removed {strat_id = } from strat_alert_cache_by_strat_id_dict if existed")

        except Exception as e:
            err_msg: str = (f"_handle_reset_log_book_cache failed - cant clear cache"
                            f"received {matched_pattern = }")
            err_detail: str = f"exception: {e}, "
            logging.exception(f"{err_msg}{self.log_seperator}{err_detail}")
            self.send_portfolio_alerts(severity=PhoneBookBaseLogBook.get_severity("error"),
                                       alert_brief=err_msg,
                                       alert_details=err_detail)

    def handle_pair_strat_matched_log_message(self, log_prefix: str, log_message: str,
                                              log_detail: StratLogDetail):
        logging.debug(f"Processing log line: {log_message[:200]}...")

        # handling ResetLogBookCache
        if match := (
                re.compile(fr"{self.reset_log_book_cache_pattern}.*{self.reset_log_book_cache_pattern}"
                           ).search(log_message)):
            logging.info("Found ResetLogBookCache pattern")
            self._handle_reset_log_book_cache(match[0])
            return

        if log_message.startswith(self.pattern_for_pair_strat_db_updates):
            # handle pair_strat db updates
            logging.info(f"phone_book update found: {log_message}")
            self.process_pair_strat_api_ops(log_message)
            return

        if hasattr(log_detail, "strat_id_find_callable") and log_detail.strat_id_find_callable is not None:
            # handle strat alert message
            logging.info(f"Strat alert message from strat_id based log: {log_message}")
            pair_strat_id = log_detail.strat_id_find_callable(log_detail.log_file_path)
            self.process_strat_alert_message_with_strat_id(log_prefix, log_message, pair_strat_id)
            return

        # put in method
        if match := re.compile(fr"{self.symbol_side_pattern}.*{self.symbol_side_pattern}").search(log_message):
            # handle strat alert message
            logging.info(f"Strat alert message: {log_message}")
            self._process_strat_alert_message_with_symbol_side(log_prefix, log_message, match[0])
            return

        # Sending ERROR/WARNING type log to portfolio_alerts
        error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=log_prefix, log_message=log_message)
        if error_dict is not None:
            severity, alert_brief, alert_details = self._create_alert(error_dict)
            self.send_portfolio_alerts(severity=severity, alert_brief=alert_brief, alert_details=alert_details)
        # else not required: error pattern doesn't match, no alerts to send

