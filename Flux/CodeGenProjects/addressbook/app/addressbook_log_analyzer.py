# System imports
import logging
import os
import time
from pathlib import PurePath
from typing import Callable, Set
from pendulum import DateTime
import re
from threading import Lock
from fastapi.encoders import jsonable_encoder

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger, \
    YAMLConfigurationManager, get_native_host_n_port_from_config_dict
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer, LogDetail
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import create_alert
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import is_service_up

config_yaml_path = PurePath(__file__).parent.parent / "data" / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
host, port = get_native_host_n_port_from_config_dict(config_yaml_dict)
debug_mode: bool = False if (debug_env := os.getenv("DEBUG")) is None or len(debug_env) == 0 or debug_env == "0" \
    else True

PAIR_STRAT_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, regex_file: str, log_details: List[LogDetail] | None = None,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        super().__init__(regex_file=regex_file, log_details=log_details,
                         log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict)
        logging.info(f"starting pair_strat log analyzer. monitoring logs: {log_details}")
        self.simulation_mode = simulation_mode
        self.portfolio_alerts_cache: List[Alert] = list()
        self.strat_id_by_symbol_side_dict: Dict[str, int] = dict()
        self.strat_alert_cache_by_strat_id_dict: Dict[int, List[Alert]] = dict()
        self.service_up: bool = False
        self.send_alert_lock: Lock = Lock()
        self.strat_manager_service_web_client: StratManagerServiceWebClient = \
            StratManagerServiceWebClient.set_or_get_if_instance_exists(host, port)
        self.severity_map: Dict[str, str] = {
            "error": "Severity_ERROR",
            "critical": "Severity_CRITICAL",
            "warning": "Severity_WARNING"
        }
        self.error_patterns: Dict[str, re.Pattern] = {
            "error": re.compile(r"ERROR"),
            "critical": re.compile(r"CRITICAL"),
            "warning": re.compile(r"WARNING")
        }
        if debug_mode:
            logging.warning(f"Running log analyzer in DEBUG mode;;; log_files: {self.log_details}, "
                            f"debug_mode: {debug_mode}")
            self.error_patterns.update({
                "info": re.compile(r"INFO"),
                "debug": re.compile(r"DEBUG")
            })
            self.severity_map.update({
                "info": "Severity_INFO",
                "debug": "Severity_DEBUG"
            })
        if self.simulation_mode:
            print("CRITICAL: log analyzer running in simulation mode...")
            alert_brief: str = "Log analyzer running in simulation mode"
            self._send_alerts(severity=self._get_severity("critical"), alert_brief=alert_brief, alert_details="")

        self.run()

    def _init_service(self) -> bool:
        if self.service_up:
            return True
        else:
            self.service_up = is_service_up(ignore_error=True)
            if self.service_up:
                portfolio_status: PortfolioStatusBaseModel = \
                    self.strat_manager_service_web_client.get_portfolio_status_client(1)
                if portfolio_status.portfolio_alerts is not None:
                    self.portfolio_alerts_cache = portfolio_status.portfolio_alerts
                else:
                    self.portfolio_alerts_cache = list()
                return True
            return False

    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str) -> None:
        with self.send_alert_lock:
            logging.debug(f"sending alert with severity: {severity}, alert_brief: {alert_brief}, "
                          f"alert_details: {alert_details}")
            created: bool = False
            while self.run_mode and not created:
                try:
                    if not self.service_up:
                        service_ready: bool = self._init_service()
                        if not service_ready:
                            raise Exception("service up check failed. waiting for the service to start...")
                        # else not required: proceed to creating alert
                    # else not required

                    if not alert_details:
                        alert_details = None
                    severity: Severity = self.get_severity_type_from_severity_str(severity_str=severity)
                    alert_obj: Alert = self.create_or_update_alert(self.portfolio_alerts_cache, severity, alert_brief,
                                                                   alert_details)
                    updated_portfolio_status: PortfolioStatusBaseModel = \
                        PortfolioStatusBaseModel(_id=1, portfolio_alerts=[alert_obj])
                    self.strat_manager_service_web_client.patch_portfolio_status_client(jsonable_encoder(updated_portfolio_status, by_alias=True, exclude_none=True))
                    created = True
                except Exception as e:
                    logging.exception(f"_send_alerts failed;;;exception: {e}")
                    self.service_up = False
                    time.sleep(30)

    def create_or_update_alert(self, alerts: List[Alert] | None, severity: Severity, alert_brief: str,
                               alert_details: str | None) -> Alert:
        alert_obj: Alert | None = None
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

                if cleaned_alert_brief == stored_alert_brief and \
                        cleaned_alert_details == stored_alert_details and \
                        severity == alert.severity:
                    updated_alert_count: int = alert.alert_count + 1
                    updated_last_update_date_time: DateTime = DateTime.utcnow()
                    alert_obj = Alert(_id=alert.id, dismiss=False, alert_count=updated_alert_count,
                                      alert_brief=alert_brief, severity=alert.severity,
                                      last_update_date_time=updated_last_update_date_time)
                    # update the alert in cache
                    alert.dismiss = False
                    alert.alert_brief = alert_brief
                    alert.alert_count = updated_alert_count
                    alert.last_update_date_time = updated_last_update_date_time
                    break
                # else not required: alert not matched with existing alerts
        if alert_obj is None:
            # create a new alert
            alert_obj: Alert = create_alert(alert_brief=alert_brief, alert_details=alert_details,
                                            severity=severity)
            alerts.append(alert_obj)
        return alert_obj

    def get_severity_type_from_severity_str(self, severity_str: str) -> Severity:
        return Severity[severity_str]

    def clean_alert_str(self, alert_str: str) -> str:
        # remove object hex memory path
        cleaned_alert_str: str = re.sub(r"0x[a-f0-9]*", "", alert_str)
        # remove all numeric digits
        cleaned_alert_str = re.sub(r"-?[0-9]*", "", cleaned_alert_str)
        return cleaned_alert_str

    def _get_severity(self, error_type: str) -> str:
        error_type = error_type.lower()
        if error_type in self.severity_map:
            return self.severity_map[error_type]
        else:
            return 'Severity_UNKNOWN'

    def _create_alert(self, error_dict: Dict) -> List[str]:
        alert_brief_n_detail_lists: List[str] = error_dict["line"].split(";;;", 1)
        if len(alert_brief_n_detail_lists) == 2:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = alert_brief_n_detail_lists[1]
        else:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = ". ".join(alert_brief_n_detail_lists[1:])
        alert_brief = self._truncate_str(alert_brief).strip()
        alert_details = self._truncate_str(alert_details).strip()
        severity = self._get_severity(error_dict["type"])
        return [severity, alert_brief, alert_details]

    def _process_trade_simulator_message(self, message: str) -> None:
        try:
            if not self.simulation_mode:
                raise Exception("Received trade simulator message but log analyzer not running in simulation mode")
            # remove $$$ from beginning of message
            message: str = message[3:]
            args: List[str] = message.split("~~")
            method_name: str = args.pop(0)

            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by "^^" if any
            for arg in args:
                key, value = arg.split("^^")
                kwargs[key] = value

            callback_method: Callable = getattr(TradeSimulator, method_name)
            callback_method(**kwargs)
        except Exception as e:
            alert_brief: str = f"_process_trade_simulator_message failed in log analyzer"
            alert_details: str = f"message: {message}, exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            self._send_alerts(severity=self._get_severity("error"), alert_brief=alert_brief,
                              alert_details=alert_details)

    def _process_strat_alert_message(self, prefix: str, message: str) -> None:
        try:
            pattern: re.Pattern = re.compile("%%.*%%")
            match = pattern.search(message)
            if not match:
                raise Exception("unexpected error in _process_strat_alert_message. strat alert pattern not matched")

            matched_text = match[0]
            log_message: str = message.replace(matched_text, " ")
            error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=prefix, log_message=log_message)

            # if error pattern does not match, ignore creating alert
            if error_dict is None:
                return

            args: str = matched_text.replace("%%", "").strip()
            symbol_side_set: Set = set()

            # kwargs separated by "," if any
            for arg in args.split(","):
                key, value = [x.strip() for x in arg.split("=")]
                symbol_side_set.add(value)
                break

            if len(symbol_side_set) == 0:
                raise Exception("no symbol-side pair found while creating strat alert")
            else:
                symbol_side: str = list(symbol_side_set)[0]
                symbol, side = symbol_side.split("-")
                strat_id: int | None = self.strat_id_by_symbol_side_dict.get(symbol_side)
                if strat_id is None or self.strat_alert_cache_by_strat_id_dict.get(strat_id) is None:
                    pair_strat_list: List[PairStrat] = \
                        self.strat_manager_service_web_client.get_ongoing_strat_from_symbol_side_query_client(
                            sec_id=symbol, side=side)
                    if len(pair_strat_list) == 0:
                        raise Exception(f"no ongoing pair strat found for symbol_side: {symbol_side} while creating "
                                        f"strat alert")
                    elif len(pair_strat_list) == 1:
                        pair_strat_obj: PairStrat = pair_strat_list[0]
                        strat_id = pair_strat_obj.id
                        if pair_strat_obj.strat_status.strat_alerts is not None:
                            self.strat_alert_cache_by_strat_id_dict[strat_id] = \
                                pair_strat_list[0].strat_status.strat_alerts
                        else:
                            self.strat_alert_cache_by_strat_id_dict[strat_id] = list()
                    else:
                        raise Exception(f"multiple pair strat found for symbol_side: {symbol_side} while creating "
                                        f"strat alert, expected 1")
                # else not required: alert cache exists

                severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)
                self._send_strat_alerts(strat_id, severity, alert_brief, alert_details)
        except Exception as e:
            alert_brief: str = f"_process_strat_alert_message failed in log analyzer"
            alert_details: str = f"message: {message}, exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            self._send_alerts(severity=self._get_severity("error"), alert_brief=alert_brief,
                              alert_details=alert_details)

    def _send_strat_alerts(self, strat_id: int, severity: str, alert_brief: str, alert_details: str) -> None:
        with self.send_alert_lock:
            logging.debug(f"sending strat alert with strat_id: {strat_id} severity: {severity}, alert_brief: "
                          f"{alert_brief}, alert_details: {alert_details}")
            created: bool = False
            while self.run_mode and not created:
                try:
                    if not self.service_up:
                        raise Exception("service up check failed. waiting for the service to start...")
                    # else not required

                    if not alert_details:
                        alert_details = None
                    severity: Severity = self.get_severity_type_from_severity_str(severity_str=severity)
                    alert_obj: Alert = self.create_or_update_alert(self.strat_alert_cache_by_strat_id_dict[strat_id],
                                                                   severity, alert_brief, alert_details)
                    updated_pair_strat: PairStratBaseModel = \
                        PairStratBaseModel(_id=strat_id, strat_status=StratStatusOptional())
                    updated_pair_strat.strat_status.strat_alerts = [alert_obj]
                    self.strat_manager_service_web_client.patch_pair_strat_client(jsonable_encoder(updated_pair_strat, by_alias=True, exclude_none=True))
                    created = True
                except Exception as e:
                    logging.exception(f"_send_strat_alerts failed;;;exception: {e}")
                    time.sleep(30)

    def _get_error_dict(self, log_prefix: str, log_message: str) -> \
            Dict[str, str] | None:
        # shift
        for error_type, pattern in self.error_patterns.items():
            match = pattern.search(log_prefix)
            if match:
                error_dict: Dict = {
                    'type': error_type,
                    'line': log_prefix.replace(pattern.search(log_prefix)[0], " ") + log_message
                }
                logging.info(f"Error pattern matched, creating alert. error_dict: {error_dict}")
                return error_dict
        return None

    def notify_no_activity(self, log_detail: LogDetail):
        alert_brief: str = f"No new logs found for {log_detail.service} for last " \
                           f"{self.log_refresh_threshold} seconds"
        alert_details: str = f"{log_detail.service} log file path: {log_detail.log_file}"
        self._send_alerts(severity=self._get_severity("error"), alert_brief=alert_brief,
                          alert_details=alert_details)

    def notify_tail_error_in_log_service(self, brief_msg_str: str, detail_msg_str: str):
        self._send_alerts(severity=self._get_severity("warning"), alert_brief=brief_msg_str,
                          alert_details=detail_msg_str)

    def handle_pair_strat_matched_log_message(self, log_prefix: str, log_message: str):
        # put in method
        if log_message.startswith("$$$"):
            # handle trade simulator message
            logging.info(f"Trade simulator message: {log_message}")
            self._process_trade_simulator_message(log_message)
            return

        if re.compile(r"%%.*%%").search(log_message):
            # handle strat alert message
            logging.info(f"Strat alert message: {log_message}")
            self._process_strat_alert_message(log_prefix, log_message)
            return

        logging.debug(f"Processing log line: {log_message[:200]}...")
        error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=log_prefix, log_message=log_message)
        if error_dict is not None:
            severity, alert_brief, alert_details = self._create_alert(error_dict)
            self._send_alerts(severity=severity, alert_brief=alert_brief, alert_details=alert_details)
        # else not required: error pattern doesn't match, no alerts to send

    def handle_perf_benchmark_matched_log_message(self, log_prefix: str, log_message: str):
        pattern = re.compile("_timeit_.*_timeit_")
        if search_obj := re.search(pattern, log_message):
            found_pattern = search_obj.group()
            found_pattern = found_pattern[8:-8]  # removing beginning and ending _timeit_
            found_pattern_list = found_pattern.split("~")  # splitting pattern values
            if len(found_pattern_list) == 5:
                callable_name, date_time, start_time, end_time, delta = found_pattern_list
                if callable_name != "underlying_create_raw_performance_data_http":
                    raw_performance_data_obj = RawPerformanceDataBaseModel()
                    raw_performance_data_obj.callable_name = callable_name
                    raw_performance_data_obj.call_date_time = pendulum.parse(date_time)
                    raw_performance_data_obj.start_time_it_val = parse_to_float(start_time)
                    raw_performance_data_obj.end_time_it_val = parse_to_float(end_time)
                    raw_performance_data_obj.delta = parse_to_float(delta)

                    self.strat_manager_service_web_client.create_raw_performance_data_client(
                        raw_performance_data_obj)
                    logging.debug(f"Created raw_performance_data in db for callable {callable_name} "
                                  f"with datetime {date_time}")
                # else not required: avoiding callable underlying_create_raw_performance_data to avoid infinite loop
            else:
                err_str_: str = f"Found timeit pattern but internally only contains {found_pattern_list}, " \
                                f"ideally must contain callable_name, date_time, start_time, end_time & delta " \
                                f"seperated by '~'"
                logging.exception(err_str_)
        # else not required: if no pattern is matched ignoring this log_message


if __name__ == '__main__':
    def main():
        from datetime import datetime
        # read log analyzer run configuration
        config_dict_path: PurePath = PAIR_STRAT_DATA_DIR / "config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(str(config_dict_path))
        simulation_mode: bool = config_dict.get("simulate_log_analyzer", False)
        # to suppress new alerts, add regex pattern to the file
        suppress_alert_regex_file: PurePath = PAIR_STRAT_DATA_DIR / "suppress_alert_regex.txt"
        # register new logs directory and log details below
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        market_data_log_dir: PurePath = PurePath(__file__).parent.parent.parent / "market_data" / "log"
        datetime_str: str = datetime.now().strftime("%Y%m%d")
        log_details: List[LogDetail] = [
            LogDetail(service="market_data_beanie_fastapi",
                      log_file=str(market_data_log_dir / f"market_data_beanie_logs_{datetime_str}.log"), critical=True),
            LogDetail(service="addressbook_beanie_fastapi",
                      log_file=str(log_dir / f"addressbook_beanie_logs_{datetime_str}.log"), critical=True),
            LogDetail(service="addressbook_cache_fastapi",
                      log_file=str(log_dir / f"addressbook_cache_logs_{datetime_str}.log"), critical=True),
            LogDetail(service="strat_executor",
                      log_file=str(log_dir / f"strat_executor_{datetime_str}.log"), critical=True)
        ]
        configure_logger("debug", str(log_dir), f"addressbook_log_analyzer_{datetime_str}.log")
        pair_strat_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                   r"DEBUG|INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
        perf_benchmark_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                       r"TIMING) : \[[a-zA-Z._]* : \d*] : "
        log_prefix_regex_pattern_to_callable_name_dict = {
            pair_strat_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message",
            perf_benchmark_log_prefix_regex_pattern: "handle_perf_benchmark_matched_log_message"
        }

        AddressbookLogAnalyzer(regex_file=str(suppress_alert_regex_file), log_details=log_details,
                                   log_prefix_regex_pattern_to_callable_name_dict=
                                   log_prefix_regex_pattern_to_callable_name_dict,
                                   simulation_mode=simulation_mode)

    main()


