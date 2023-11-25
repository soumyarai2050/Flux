import os
import time
import re
from threading import Thread
from queue import Queue

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger, get_symbol_side_key
from FluxPythonUtils.log_analyzer.log_analyzer import LogDetail, get_transaction_counts_n_timeout_from_config
from Flux.PyCodeGenEngine.FluxCodeGenCore.app_log_analyzer import AppLogAnalyzer
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import \
    PairStratBaseModel
from Flux.CodeGenProjects.log_analyzer.app.log_analyzer_service_helper import *
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_engine_service_helper import (
    strat_manager_service_http_client, is_ongoing_strat)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import (
    performance_benchmark_service_http_client, RawPerformanceDataBaseModel)

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)


debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

portfolio_alert_bulk_update_counts_per_call, portfolio_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("portfolio_alert_configs")))
strat_alert_bulk_update_counts_per_call, strat_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("strat_alert_config")))


class PairStratEngineLogAnalyzer(AppLogAnalyzer):
    underlying_partial_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_partial_update_all_strat_alert_http: Callable[..., Any] | None = None
    underlying_read_portfolio_alert_by_id_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_by_id_http: Callable[..., Any] | None = None

    asyncio_loop: ClassVar[asyncio.AbstractEventLoop | None] = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_http_routes import (
            underlying_partial_update_all_portfolio_alert_http, underlying_partial_update_all_strat_alert_http,
            underlying_read_portfolio_alert_by_id_http, underlying_read_strat_alert_by_id_http)
        cls.underlying_partial_update_all_portfolio_alert_http = underlying_partial_update_all_portfolio_alert_http
        cls.underlying_partial_update_all_strat_alert_http = underlying_partial_update_all_strat_alert_http
        cls.underlying_read_portfolio_alert_by_id_http = underlying_read_portfolio_alert_by_id_http
        cls.underlying_read_strat_alert_by_id_http = underlying_read_strat_alert_by_id_http

    def __init__(self, regex_file: str, log_details: List[LogDetail] | None = None,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        super().__init__(regex_file, config_yaml_dict, performance_benchmark_service_http_client,
                         RawPerformanceDataBaseModel, log_details=log_details,
                         log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                         debug_mode=debug_mode)
        logging.info(f"starting pair_strat log analyzer. monitoring logs: {log_details}")
        PairStratEngineLogAnalyzer.initialize_underlying_http_callables()
        self.simulation_mode = simulation_mode
        self.portfolio_alerts_model_exist: bool = False
        self.portfolio_alerts_cache: List[Alert] = list()
        self.strat_id_by_symbol_side_dict: Dict[str, int] = dict()
        self.strat_alert_cache_by_strat_id_dict: Dict[int, List[Alert]] = dict()
        self.service_up: bool = False
        self.portfolio_alert_queue: Queue = Queue()
        self.strat_alert_queue: Queue = Queue()
        self.port_to_executor_web_client: Dict[int, StratExecutorServiceHttpClient] = {}
        if self.simulation_mode:
            print("CRITICAL: PairStrat log analyzer running in simulation mode...")
            alert_brief: str = "PairStrat Log analyzer running in simulation mode"
            self._send_alerts(severity=self._get_severity("critical"), alert_brief=alert_brief, alert_details="")

        if PairStratEngineLogAnalyzer.asyncio_loop is None:
            err_str_ = ("Couldn't find asyncio_loop class data member in PairStratEngineLogAnalyzer, "
                        "exiting PairStratEngineLogAnalyzer run.")
            logging.error(err_str_)
            raise Exception(err_str_)

        self.run_queue_handler()
        self.run()

    def _handle_portfolio_alert_queue_err_handler(self, *args):
        pass

    def _handle_strat_alert_queue_err_handler(self, *args):
        alerts_list = []
        for pydantic_obj_json in args[0]:
            alerts_json = pydantic_obj_json.get("alerts")
            for alerts_json_ in alerts_json:
                alerts_list.append(Alert(**alerts_json_))
        portfolio_alert = PortfolioAlertBaseModel(_id=1, alerts=alerts_list)
        self.portfolio_alert_queue.put(jsonable_encoder(portfolio_alert, by_alias=True, exclude_none=True))

    def _handle_portfolio_alert_queue(self):
        PairStratEngineLogAnalyzer.queue_handler(
            self.portfolio_alert_queue, portfolio_alert_bulk_update_counts_per_call,
            portfolio_alert_bulk_update_timeout,
            self.patch_all_portfolio_alert_client_with_asyncio_loop,
            self._handle_portfolio_alert_queue_err_handler)

    def _handle_strat_alert_queue(self):
        PairStratEngineLogAnalyzer.queue_handler(
            self.strat_alert_queue, strat_alert_bulk_update_counts_per_call,
            strat_alert_bulk_update_timeout,
            self.patch_all_strat_alert_client_with_asyncio_loop,
            self._handle_strat_alert_queue_err_handler)

    def patch_all_portfolio_alert_client_with_asyncio_loop(self, pydantic_obj_json_list: Dict):
        run_coro = PairStratEngineLogAnalyzer.underlying_partial_update_all_portfolio_alert_http(pydantic_obj_json_list)
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

    def patch_all_strat_alert_client_with_asyncio_loop(self, pydantic_obj_json_list: Dict):
        run_coro = PairStratEngineLogAnalyzer.underlying_partial_update_all_strat_alert_http(pydantic_obj_json_list)
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            return future.result()
        except HTTPException as http_e:
            err_str_ = f"underlying_partial_update_all_strat_alert_http failed with http_exception: {http_e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        except Exception as e:
            err_str_ = f"underlying_partial_update_all_strat_alert_http failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def run_queue_handler(self):
        portfolio_alert_handler_thread = Thread(target=self._handle_portfolio_alert_queue, daemon=True)
        strat_alert_handler_thread = Thread(target=self._handle_strat_alert_queue, daemon=True)
        portfolio_alert_handler_thread.start()
        strat_alert_handler_thread.start()

    def _init_service(self) -> bool:
        if self.service_up:
            return True
        else:
            self.service_up = is_log_analyzer_service_up(ignore_error=True)
            if self.service_up:
                run_coro = PairStratEngineLogAnalyzer.underlying_read_portfolio_alert_by_id_http(1)
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
                        alert_obj = Alert(_id=alert.id, dismiss=False, alert_count=updated_alert_count,
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
        cleaned_alert_str = cleaned_alert_str.split("...check the file:")[0]
        return cleaned_alert_str

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

    def _get_pair_strat_obj_from_symbol_side(self, symbol: str, side: Side) -> PairStratBaseModel | None:
        pair_strat_list: List[PairStratBaseModel] = \
            strat_manager_service_http_client.get_pair_strat_from_symbol_side_query_client(
                sec_id=symbol, side=side)

        if len(pair_strat_list) == 0:
            return None
        elif len(pair_strat_list) == 1:
            pair_strat_obj: PairStratBaseModel = pair_strat_list[0]
            return pair_strat_obj

    def _get_executor_http_client_from_pair_strat(self, port_: int, host_: str) -> StratExecutorServiceHttpClient:
        executor_web_client = self.port_to_executor_web_client.get(port_)
        if executor_web_client is None:
            executor_web_client = (
                StratExecutorServiceHttpClient.set_or_get_if_instance_exists(host_, port_))
            self.port_to_executor_web_client[port_] = executor_web_client
        return executor_web_client

    def _process_strat_alert_message(self, prefix: str, message: str) -> None:
        try:
            pattern: re.Pattern = re.compile("%%.*%%")
            match = pattern.search(message)
            if not match:
                raise Exception("unexpected error in _process_strat_alert_message. strat alert pattern not matched")

            matched_text = match[0]
            log_message: str = message.replace("%%", "")
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
                raise Exception("no symbol-side pair found while creating strat alert, ")
            else:
                symbol_side: str = list(symbol_side_set)[0]
                symbol, side = symbol_side.split("-")
                strat_id: int | None = self.strat_id_by_symbol_side_dict.get(symbol_side)
                if strat_id is None or self.strat_alert_cache_by_strat_id_dict.get(strat_id) is None:

                    pair_strat_obj: PairStratBaseModel = self._get_pair_strat_obj_from_symbol_side(symbol, side)

                    if pair_strat_obj is None:
                        pass
                    else:
                        if not pair_strat_obj.is_executor_running:
                            raise Exception(f"StartExecutor Server not running for pair_strat: {pair_strat_obj}")

                        if not is_ongoing_strat(pair_strat_obj):
                            raise Exception(f"Strat Executor for symbol & side: {symbol} & {side} is not "
                                            f"in ongoing state while creating strat_alert, pair_strat: "
                                            f"{pair_strat_obj}")

                        strat_id = pair_strat_obj.id
                        run_coro = PairStratEngineLogAnalyzer.underlying_read_strat_alert_by_id_http(strat_id)
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
                            self.strat_alert_cache_by_strat_id_dict[strat_id] = list()
                        self.strat_id_by_symbol_side_dict[symbol_side] = strat_id
                # else not required: alert cache exists

                severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)
                self._send_strat_alerts(strat_id, severity, alert_brief, alert_details)
        except Exception as e:
            alert_brief: str = f"_process_strat_alert_message failed in log analyzer"
            alert_details: str = f"message: {message}, exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            self._send_alerts(severity=self._get_severity("error"), alert_brief=alert_brief,
                              alert_details=alert_details)

    # portfolio lvl alerts handling
    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str) -> None:
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
                updated_portfolio_alert: PortfolioAlertBaseModel = \
                    PortfolioAlertBaseModel(_id=1, alerts=[alert_obj])
                self.portfolio_alert_queue.put(jsonable_encoder(updated_portfolio_alert,
                                                                by_alias=True, exclude_none=True))
                created = True
            except Exception as e:
                logging.exception(f"_send_alerts failed;;;exception: {e}")
                self.service_up = False
                time.sleep(30)

    # strat lvl alert handling
    def _send_strat_alerts(self, strat_id: int, severity: str, alert_brief: str, alert_details: str) -> None:
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
                updated_strat_alert: StratAlertBaseModel = StratAlertBaseModel(_id=strat_id, alerts=[alert_obj])
                self.strat_alert_queue.put(jsonable_encoder(updated_strat_alert,
                                                            by_alias=True, exclude_none=True))
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
        alert_details: str = f"{log_detail.service} log file path: {log_detail.log_file_path}"
        self._send_alerts(severity=self._get_severity("error"), alert_brief=alert_brief,
                          alert_details=alert_details)

    def notify_tail_error_in_log_service(self, brief_msg_str: str, detail_msg_str: str):
        self._send_alerts(severity=self._get_severity("warning"), alert_brief=brief_msg_str,
                          alert_details=detail_msg_str)

    def handle_pair_strat_matched_log_message(self, log_prefix: str, log_message: str):
        # put in method
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


if __name__ == '__main__':
    def main():
        from datetime import datetime
        simulation_mode: bool = config_yaml_dict.get("simulate_log_analyzer", False)
        # to suppress new alerts, add regex pattern to the file
        suppress_alert_regex_file: PurePath = LOG_ANALYZER_DATA_DIR / "suppress_alert_regex.txt"
        # register new logs directory and log details below
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        pair_strat_engine_log_dir: PurePath = code_gen_projects_path / "pair_strat_engine" / "log"
        market_data_log_dir: PurePath = code_gen_projects_path / "market_data" / "log"
        strat_executor_log_dir: PurePath = code_gen_projects_path / "strat_executor" / "log"
        datetime_str: str = datetime.now().strftime("%Y%m%d")

        configure_logger("debug", str(log_dir), f"pair_strat_engine_log_analyzer_{datetime_str}.log")
        pair_strat_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                   r"DEBUG|INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
        log_prefix_regex_pattern_to_callable_name_dict = {
            pair_strat_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
        }

        log_details: List[LogDetail] = [
            LogDetail(service="pair_strat_engine_beanie_fastapi",
                      log_file_path=str(
                          pair_strat_engine_log_dir / f"pair_strat_engine_beanie_logs_*_{datetime_str}.log"),
                      critical=True,
                      log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                      log_file_path_is_regex=True),
            LogDetail(service="pair_strat_engine_cache_fastapi",
                      log_file_path=str(
                          pair_strat_engine_log_dir / f"pair_strat_engine_cache_logs_*_{datetime_str}.log"),
                      critical=True,
                      log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                      log_file_path_is_regex=True),
            LogDetail(service="market_data_beanie_fastapi",
                      log_file_path=str(market_data_log_dir / f"market_data_beanie_logs_*_{datetime_str}.log"),
                      critical=True,
                      log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                      log_file_path_is_regex=True),
            LogDetail(service="strat_executor",
                      log_file_path=str(strat_executor_log_dir / f"strat_executor_*_{datetime_str}.log"), critical=True,
                      log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                      log_file_path_is_regex=True)
        ]

        PairStratEngineLogAnalyzer(regex_file=str(suppress_alert_regex_file), log_details=log_details,
                                   simulation_mode=simulation_mode)

    main()


