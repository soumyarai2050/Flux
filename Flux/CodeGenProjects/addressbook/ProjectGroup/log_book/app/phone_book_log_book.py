import ast
import datetime
import logging
import multiprocessing
import os
import re
from typing import Set
import signal
import sys
import inspect

# Project imports
from FluxPythonUtils.log_book.log_book import get_transaction_counts_n_timeout_from_config
from FluxPythonUtils.scripts.utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.phone_book_base_log_book import (
    PhoneBookBaseLogBook, StratLogDetail)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client, get_reset_log_book_cache_wrapper_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_pattern)

strat_alert_bulk_update_counts_per_call, strat_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("strat_alert_config"), is_server_config=False))


class PhoneBookLogBook(PhoneBookBaseLogBook):
    underlying_partial_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_read_portfolio_alert_by_id_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_by_id_http: Callable[..., Any] | None = None

    def __init__(self, log_detail, regex_file_dir_path: str,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        process_name = multiprocessing.current_process().name
        datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
        log_file_name = f"{process_name}_logs_{datetime_str}.log"
        log_dir: PurePath = PurePath(__file__).parent.parent / "log" / "tail_executors"
        configure_logger(logging.DEBUG, log_file_dir_path=str(log_dir),
                         log_file_name=log_file_name)
        logging.info(f"Logging for {process_name}")

        super().__init__(log_detail, regex_file_dir_path,
                         log_prefix_regex_pattern_to_callable_name_dict, simulation_mode)
        self.pattern_for_pair_strat_db_updates: str = get_pattern_for_pair_strat_db_updates()
        self.symbol_side_pattern: str = get_symbol_side_pattern()
        self.reset_log_book_cache_pattern: str = get_reset_log_book_cache_wrapper_pattern()
        PhoneBookLogBook.initialize_underlying_http_callables()

        # running queue handling for pair_start_api_ops
        Thread(target=self._pair_strat_api_ops_queue_handler, daemon=True, name="db_queue_handler").start()
        logging.info(f"Thread Started: db_queue_handler")

        # running queue handling for portfolio and strat alerts
        self.run_queue_handler()
        # running raw_performance thread
        raw_performance_handler_thread = Thread(target=self._handle_raw_performance_data_queue, daemon=True,
                                                name="raw_performance_handler")
        raw_performance_handler_thread.start()
        logging.info(f"Thread Started: raw_performance_handler")

        self.strat_pause_regex_pattern: List[re.Pattern] = [re.compile(fr'{pattern}') for pattern in
                                                            config_yaml_dict.get("strat_pause_regex_pattern")]
        self.pos_disable_regex_pattern: List[re.Pattern] = [re.compile(fr'{pattern}') for pattern in
                                                            config_yaml_dict.get("pos_disable_regex_pattern")]
        self.run_startup_checks()

        self.terminate_triggered: bool = False
        signal.set_wakeup_fd(-1)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def run_startup_checks(self):
        if self.simulation_mode:
            alert_brief: str = "PairStrat Log analyzer running in simulation mode"
            print(f"CRITICAL: {alert_brief}")
            alert_meta = get_alert_meta_obj(PurePath(__file__).name, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow())
            self.send_portfolio_alerts(severity=self.get_severity("critical"), alert_brief=alert_brief,
                                       alert_meta=alert_meta)
        # else - system not running in simulation node

    def _signal_handler(self, signal_type: int, *args) -> None:
        if not self.terminate_triggered:
            super()._signal_handler(signal_type, *args)

            # exiting all threads
            self.pair_strat_api_ops_queue.put("EXIT")
            self.strat_alert_queue.put("EXIT")
            self.portfolio_alert_queue.put("EXIT")
            self.raw_performance_data_queue.put("EXIT")

            for _, queue_ in self.model_type_name_to_patch_queue_cache_dict.items():
                queue_.put("EXIT")
        # else not required: avoiding multiple terminate calls

    def _handle_strat_alert_queue_err_handler(self, *args):
        try:
            strat_alert_obj_list: List[StratAlertBaseModel] = args[0]    # single unprocessed basemodel object is passed
            strat_alert_obj: StratAlertBaseModel
            for strat_alert_obj in strat_alert_obj_list:
                alert_meta = strat_alert_obj.alert_meta
                component_path: str | None = None
                source_file_name: str | None = None
                line_num: int | None = None
                alert_create_date_time: DateTime | None = None
                first_detail = None
                latest_detail = None
                if alert_meta is not None:
                    component_path = alert_meta.component_file_path
                    source_file_name = alert_meta.source_file_name
                    line_num = alert_meta.line_num
                    alert_create_date_time = alert_meta.alert_create_date_time
                    first_detail = alert_meta.first_detail
                    latest_detail = alert_meta.latest_detail
                alert_meta = get_alert_meta_obj(component_path, source_file_name,
                                                line_num, alert_create_date_time,
                                                first_detail, latest_detail)
                self.send_portfolio_alerts(strat_alert_obj.severity, strat_alert_obj.alert_brief, alert_meta)
        except Exception as e:
            err_str_ = f"_handle_strat_alert_queue_err_handler failed, passed args: {args};;; exception: {e}"
            log_book_service_http_client.portfolio_alert_fail_logger_query_client(err_str_)

    def _handle_strat_alert_query_call_from_alert_queue_handler(self, strat_alerts: List[StratAlertBaseModel]):
        strat_alert_data_list: List[Dict[str, Any]] = []
        for strat_alert in strat_alerts:
            strat_alert_dict = {
                "strat_id": strat_alert.strat_id,
                "severity": strat_alert.severity,
                "alert_brief": strat_alert.alert_brief
            }
            if strat_alert.alert_meta:
                strat_alert_dict.update(alert_meta=strat_alert.alert_meta)
            strat_alert_data_list.append(strat_alert_dict)
        log_book_service_http_client.handle_strat_alerts_from_tail_executor_query_client(strat_alert_data_list)
        return strat_alerts

    def _handle_strat_alert_queue(self):
        alert_queue_handler_for_create_only(
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

    def _force_trigger_strat_pause(self, pair_strat_id: int, error_event_msg: str):
        try:
            updated_pair_strat: PairStratBaseModel = PairStratBaseModel.from_kwargs(
                _id=pair_strat_id, strat_state=StratState.StratState_PAUSED)
            email_book_service_http_client.patch_pair_strat_client(
                updated_pair_strat.to_json_dict(exclude_none=True))
            err_ = f"Force paused {pair_strat_id=}, {error_event_msg}"
            logging.critical(err_)
            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow())
            self._send_strat_alerts(pair_strat_id, PhoneBookBaseLogBook.get_severity("critical"),
                                    err_, alert_meta)
        except Exception as e:
            alert_brief: str = f"force_trigger_strat_pause failed for {pair_strat_id=}, {error_event_msg=}"
            alert_details: str = f"exception: {e}"
            logging.critical(f"{alert_brief};;;{alert_details}")
            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
            self.send_portfolio_alerts(severity=PhoneBookBaseLogBook.get_severity("critical"),
                                       alert_brief=alert_brief, alert_meta=alert_meta)

    def _handle_strat_pause_pattern_match(self, pair_strat_id: int, message: str, pattern: re.Pattern):
        msg_brief: str = message.split(";;;")[0]
        err_: str = f"Matched {pattern.pattern=}, pausing strat with {pair_strat_id=};;;{msg_brief=}"
        self._force_trigger_strat_pause(pair_strat_id, err_)

    def _handle_pos_disable_pattern_match(self, pair_strat_id: int, message: str, pattern: re.Pattern):
        pass

    def _handle_strat_alert_exception(self, message: str, e: Exception,
                                      severity: str | None = None,
                                      log_date_time: DateTime | None = None,
                                      log_source_file_name: str | None = None,
                                      line_num: int | None = None) -> None:
        msg_brief_n_detail = message.split(PhoneBookBaseLogBook.log_seperator, 1)
        msg_detail = f"_process_strat_alert_message failed with exception: {e}"
        if len(msg_brief_n_detail) == 2:
            msg_brief = msg_brief_n_detail[0]
            msg_detail += f", strat_detail: {msg_brief_n_detail[1]}"
        else:
            msg_brief = msg_brief_n_detail[0]

        logging.exception(f"_process_strat_alert_message failed - {message=}, exception: {e}")

        if severity is None:
            severity = self.get_severity("error")
        alert_meta = get_alert_meta_obj(self.component_file_path, log_source_file_name,
                                        line_num, log_date_time, msg_detail)
        self.send_portfolio_alerts(severity=severity, alert_brief=msg_brief, alert_meta=alert_meta)

    def _process_strat_alert_message_with_symbol_side(self, prefix: str, message: str, matched_text: str,
                                                      log_date_time: DateTime | None = None,
                                                      log_source_file_name: str | None = None,
                                                      line_num: int | None = None) -> None:
        severity: str | None = None
        try:
            log_message: str = message.replace(self.symbol_side_pattern, "")
            error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=prefix, log_message=log_message)

            # if error pattern does not match, ignore creating alert
            if error_dict is None:
                return
            severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)

            args: str = matched_text.replace(self.symbol_side_pattern, "").strip()
            symbol_side_set: Set = set()

            # kwargs separated by "," if any
            for arg in args.split(","):
                key, value = [x.strip() for x in arg.split("=")]
                symbol_side_set.add(value)

            if len(symbol_side_set) == 0:
                raise Exception("no symbol-side pair found while creating strat alert")

            symbol_side: str = list(symbol_side_set)[0]
            symbol, side = symbol_side.split("-")
            strat_id: int | None = self.strat_id_by_symbol_side_dict.get(symbol_side)

            if strat_id is None or self.strat_alert_cache_dict_by_strat_id_dict.get(strat_id) is None:

                pair_strat_obj: PairStratBaseModel = self._get_pair_strat_obj_from_symbol_side(symbol, Side(side))
                if pair_strat_obj is None:
                    raise Exception(f"No pair strat found for symbol_side: {symbol_side}")
                if pair_strat_obj.server_ready_state < 2:
                    raise Exception(f"StreetBook Server not running for {strat_id=}")

                strat_id = pair_strat_obj.id
                update_strat_alert_cache(strat_id, self.strat_alert_cache_dict_by_strat_id_dict,
                                         log_book_service_http_client.filtered_strat_alert_by_strat_id_query_client)
                for symbol_side in symbol_side_set:
                    self.strat_id_by_symbol_side_dict[symbol_side] = strat_id
            # else not required: alert cache exists

            # handle strat_state update mismatch
            if "Strat state changed from StratState_ACTIVE to StratState_PAUSED" in message:
                log_book_service_http_client.strat_state_update_matcher_query_client(strat_id, message,
                                                                                         self.component_file_path)

            pattern: re.Pattern
            for pattern in self.strat_pause_regex_pattern:
                if pattern.search(message):
                    self._handle_strat_pause_pattern_match(strat_id, message, pattern)
                    break
            for pattern in self.pos_disable_regex_pattern:
                if pattern.search(message):
                    self._handle_pos_disable_pattern_match(strat_id, message, pattern)
                    break

            alert_meta = get_alert_meta_obj(self.component_file_path, log_source_file_name,
                                            line_num, log_date_time, alert_details)
            self._send_strat_alerts(strat_id, severity, alert_brief, alert_meta)
        except Exception as e:
            self._handle_strat_alert_exception(message, e, severity, log_date_time, log_source_file_name, line_num)

    def process_strat_alert_message_with_symbol_side(self, prefix: str, message: str,
                                                     log_date_time: DateTime | None = None,
                                                     log_source_file_name: str | None = None,
                                                     line_num: int | None = None) -> None:
        try:
            pattern: re.Pattern = re.compile(f"{self.symbol_side_pattern}(.*?){self.symbol_side_pattern}")
            match = pattern.search(message)
            if not match:
                raise Exception("unexpected error in _process_strat_alert_message. strat alert pattern not matched")

            matched_text = match[0]
            self._process_strat_alert_message_with_symbol_side(prefix, message, matched_text,
                                                               log_date_time, log_source_file_name, line_num)
        except Exception as e:
            self._handle_strat_alert_exception(message, e, log_date_time=log_date_time,
                                               log_source_file_name=log_source_file_name, line_num=line_num)

    def process_strat_alert_message_with_strat_id(self, prefix: str, message: str,
                                                  pair_strat_id: int | None = None,
                                                  log_date_time: DateTime | None = None,
                                                  log_source_file_name: str | None = None,
                                                  line_num: int | None = None) -> None:
        severity: str | None = None
        try:
            error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=prefix, log_message=message)

            # if error pattern does not match, ignore creating alert
            if error_dict is None:
                return
            severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)

            strat_id = pair_strat_id

            # handle strat_state update mismatch
            if "Strat state changed from StratState_ACTIVE to StratState_PAUSED" in message:
                log_book_service_http_client.strat_state_update_matcher_query_client(strat_id, message,
                                                                                         self.component_file_path)

            pattern: re.Pattern
            for pattern in self.strat_pause_regex_pattern:
                if pattern.search(message):
                    self._handle_strat_pause_pattern_match(strat_id, message, pattern)
                    break
            for pattern in self.pos_disable_regex_pattern:
                if pattern.search(message):
                    self._handle_pos_disable_pattern_match(strat_id, message, pattern)
                    break

            alert_meta = get_alert_meta_obj(self.component_file_path, log_source_file_name,
                                            line_num, log_date_time, alert_details)
            self._send_strat_alerts(strat_id, severity, alert_brief, alert_meta)
        except Exception as e:
            self._handle_strat_alert_exception(message, e, severity, log_date_time, log_source_file_name, line_num)

    # strat lvl alert handling
    def _send_strat_alerts(self, strat_id: int, severity_str: str, alert_brief: str,
                           alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending strat alert with {strat_id=}, {severity_str=}, "
                      f"{alert_brief=}, {alert_meta=}")
        try:
            if not self.service_up:
                raise Exception("service up check failed. waiting for the service to start...")
            # else not required

            if self.strat_alert_cache_dict_by_strat_id_dict.get(strat_id) is None:
                try:
                    pair_strat: PairStratBaseModel = email_book_service_http_client.get_pair_strat_client(strat_id)
                except Exception as e:
                    raise Exception(f"get_pair_strat_client failed: Can't find pair_start with id: {strat_id}")
                else:
                    if pair_strat.server_ready_state < 2:
                        raise Exception(f"StartExecutor Server not running for pair_strat: {pair_strat}")

                update_strat_alert_cache(strat_id, self.strat_alert_cache_dict_by_strat_id_dict,
                                         log_book_service_http_client.filtered_strat_alert_by_strat_id_query_client)
                symbol_side = (f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}-"
                               f"{pair_strat.pair_strat_params.strat_leg1.side}")
                self.strat_id_by_symbol_side_dict[symbol_side] = strat_id

            severity: Severity = get_severity_type_from_severity_str(severity_str=severity_str)
            create_or_update_alert(self.strat_alert_cache_dict_by_strat_id_dict[strat_id],
                                   self.strat_alert_queue, StratAlertBaseModel, PortfolioAlertBaseModel,
                                   severity, alert_brief, strat_id, alert_meta)
        except Exception as e:
            err_msg: str = (f"_send_strat_alerts failed, exception: {e} received {strat_id=}, "
                            f"{severity_str=}, {alert_brief=}, {alert_meta=}")
            logging.exception(err_msg)
            alert_meta = get_alert_meta_obj(alert_meta.component_file_path, alert_meta.source_file_name,
                                            alert_meta.line_num, alert_meta.alert_create_date_time, err_msg)
            self.send_portfolio_alerts(severity=severity_str, alert_brief=alert_brief,
                                       alert_meta=alert_meta)

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
                logging.info(f"Removed {symbol_side=} from strat_id_by_symbol_side_dict if existed")
            self.strat_alert_cache_dict_by_strat_id_dict.pop(strat_id, None)
            logging.info(f"Removed {strat_id=} from strat_alert_cache_by_strat_id_dict if existed")

        except Exception as e:
            err_msg: str = (f"_handle_reset_log_book_cache failed - cant clear cache"
                            f"received {matched_pattern=}")
            err_detail: str = f"exception: {e}, "
            logging.exception(f"{err_msg}{self.log_seperator}{err_detail}")
            alert_meta = get_alert_meta_obj(self.component_file_path, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(), err_detail)
            self.send_portfolio_alerts(severity=PhoneBookBaseLogBook.get_severity("error"),
                                       alert_brief=err_msg, alert_meta=alert_meta)

    def handle_pair_strat_matched_log_message(self, log_prefix: str, log_message: str,
                                              log_detail: StratLogDetail,
                                              log_date_time: DateTime | None = None,
                                              log_source_file_name: str | None = None,
                                              line_num: int | None = None):
        logging.debug(f"Processing log line: {log_message[:200]}...")

        # handling ResetLogBookCache
        if match := (
                re.compile(fr"{self.reset_log_book_cache_pattern}(.*?){self.reset_log_book_cache_pattern}"
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
            self.process_strat_alert_message_with_strat_id(log_prefix, log_message, pair_strat_id,
                                                           log_date_time, log_source_file_name, line_num)
            return

        # put in method
        if match := re.compile(fr"{self.symbol_side_pattern}.*{self.symbol_side_pattern}").search(log_message):
            # handle strat alert message
            logging.info(f"Strat alert message: {log_message}")
            self._process_strat_alert_message_with_symbol_side(log_prefix, log_message, match[0],
                                                               log_date_time, log_source_file_name, line_num)
            return

        # Sending ERROR/WARNING type log to portfolio_alerts
        error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=log_prefix, log_message=log_message)
        if error_dict is not None:
            component_path = self.component_file_path
            severity, alert_brief, alert_details = self._create_alert(error_dict)
            alert_meta = get_alert_meta_obj(component_path, log_source_file_name,
                                            line_num, log_date_time, alert_details)
            self.send_portfolio_alerts(severity=severity, alert_brief=alert_brief, alert_meta=alert_meta)
        else:
            # if some log has reached here it is definitely some alert required log line since we tail with grep and
            # this log matched that grep - most likely its some unconventional log like background log
            alert_brief = f"{log_prefix}{log_message}"
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief)

