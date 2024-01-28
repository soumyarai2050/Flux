import os
import time
import re
from threading import Thread
from queue import Queue

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger, create_logger
from FluxPythonUtils.log_book.log_book import LogDetail, get_transaction_counts_n_timeout_from_config
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.pair_strat_engine_base_log_book import (
    PairStratEngineBaseLogBook, StratLogDetail)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import log_book_service_http_client

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

portfolio_alert_bulk_update_counts_per_call, portfolio_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("portfolio_alert_configs")))

debug_mode: bool = False if ((debug_env := os.getenv("LS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True


class LogSimulatorLogBook(PairStratEngineBaseLogBook):

    def __init__(self, regex_file: str, log_details: List[LogDetail] | None = None,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        super().__init__(regex_file, log_details, log_prefix_regex_pattern_to_callable_name_dict, simulation_mode)
        logging.info(f"starting log_simulator log analyzer. monitoring logs: {log_details}")
        if self.simulation_mode:
            print("CRITICAL: LogSimulator log analyzer running in simulation mode...")
            alert_brief: str = "LogSimulator Log analyzer running in simulation mode"
            self.send_portfolio_alerts(severity=self.get_severity("critical"), alert_brief=alert_brief, alert_details="")
        self.portfolio_alert_fail_logger = create_logger("portfolio_alert_fail_logger", logging.DEBUG,
                                                         str(CURRENT_PROJECT_LOG_DIR),
                                                         simulator_portfolio_alert_fail_log)

        self.run_queue_handler()
        self.run()

    def _handle_portfolio_alert_queue_err_handler(self, *args):
        pass

    def _handle_portfolio_alert_queue(self):
        LogSimulatorLogBook.queue_handler(
            self.portfolio_alert_queue, portfolio_alert_bulk_update_counts_per_call,
            portfolio_alert_bulk_update_timeout,
            log_book_service_http_client.patch_all_portfolio_alert_client,
            self._handle_portfolio_alert_queue_err_handler)

    def run_queue_handler(self):
        portfolio_alert_handler_thread = Thread(target=self._handle_portfolio_alert_queue, daemon=True)
        portfolio_alert_handler_thread.start()

    def _init_service(self) -> bool:
        if self.service_up:
            return True
        else:
            self.service_up = is_log_book_service_up(ignore_error=True)
            if self.service_up:
                portfolio_alert: PortfolioAlert = log_book_service_http_client.get_portfolio_alert_client(1)
                if portfolio_alert.alerts is not None:
                    self.portfolio_alerts_cache = portfolio_alert.alerts
                else:
                    self.portfolio_alerts_cache = list()
                return True
            return False

    def _process_trade_simulator_message(self, message: str) -> None:
        try:
            if not self.simulation_mode:
                raise Exception("Received trade simulator message but log analyzer not running in simulation mode")
            # remove $$$ from beginning of message
            message: str = message[3:]
            args: List[str] = message.split("~~")
            method_name: str = args.pop(0)
            host: str = args.pop(0)
            port: int = parse_to_int(args.pop(0))

            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by "^^" if any
            for arg in args:
                key, value = arg.split("^^")
                kwargs[key] = value

            executor_web_client = self._get_executor_http_client_from_pair_strat(port, host)

            callback_method: Callable = getattr(executor_web_client, method_name)
            callback_method(**kwargs)
            logging.info(f"Called {method_name} with kwargs: {kwargs}")

        except Exception as e:
            alert_brief: str = f"_process_trade_simulator_message failed in log analyzer"
            alert_details: str = f"message: {message}, exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                       alert_details=alert_details)

    def handle_log_simulator_matched_log_message(self, log_prefix: str, log_message: str, log_detail: LogDetail):
        # put in method
        if log_message.startswith("$$$"):
            # handle trade simulator message
            logging.info(f"Trade simulator message: {log_message}")
            self._process_trade_simulator_message(log_message)
            return

        logging.debug(f"Processing log simulator line: {log_message[:200]}...")
        error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=log_prefix, log_message=log_message)
        if error_dict is not None:
            severity, alert_brief, alert_details = self._create_alert(error_dict)
            self.send_portfolio_alerts(severity=severity, alert_brief=alert_brief, alert_details=alert_details)
        # else not required: error pattern doesn't match, no alerts to send


if __name__ == '__main__':
    def main():
        simulation_mode: bool = config_yaml_dict.get("simulate_log_book", False)
        # to suppress new alerts, add regex pattern to the file
        suppress_alert_regex_file: PurePath = LOG_ANALYZER_DATA_DIR / "suppress_alert_regex.txt"
        # register new logs directory and log details below
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        strat_executor_log_dir: PurePath = PurePath(__file__).parent.parent.parent / "strat_executor" / "log"

        datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
        log_file_name = f"log_simulator_logs_{datetime_str}.log"
        configure_logger(logging.DEBUG, log_file_dir_path=str(log_dir),
                         log_file_name=log_file_name)

        pair_strat_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                   r"DEBUG|INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
        log_prefix_regex_pattern_to_callable_name_dict = {
            pair_strat_log_prefix_regex_pattern: "handle_log_simulator_matched_log_message"
        }
        log_cmd_prefix_regex_pattern_to_callable_name_dict = {
            pair_strat_log_prefix_regex_pattern: "handle_log_book_cmd_log_message"
        }

        log_details: List[LogDetail] = [
            StratLogDetail(service="log_simulator",
                           log_file_path=str(strat_executor_log_dir / f"log_simulator_*_{datetime_str}.log"), critical=True,
                           log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                           log_file_path_is_regex=True),
            StratLogDetail(
                service="log_book_cmd_log",
                log_file_path=str(CURRENT_PROJECT_LOG_DIR / log_book_cmd_log),
                critical=False,
                log_prefix_regex_pattern_to_callable_name_dict=log_cmd_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
        ]

        LogSimulatorLogBook(regex_file=str(suppress_alert_regex_file), log_details=log_details,
                                simulation_mode=simulation_mode)
    main()
