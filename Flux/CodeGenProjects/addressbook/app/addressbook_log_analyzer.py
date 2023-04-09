# System imports
import logging
import os
import time
from pathlib import PurePath
from typing import List, Dict
from pendulum import DateTime
import re
from threading import Lock

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger,get_host_port_from_env, load_yaml_configurations
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer, LogDetail
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import create_alert
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import is_service_up

host, port = get_host_port_from_env()
debug_mode: bool = False if (debug_env := os.getenv("DEBUG")) is None or len(debug_env) == 0 or debug_env == "0" \
    else True

PAIR_STRAT_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, regex_file: str, log_details: List[LogDetail] | None = None, simulation_mode: bool = False):
        if log_details is None:
            log_details = []
        logging.info(f"starting log analyzer. monitoring logs: {log_details}")
        self.portfolio_alerts_cache: List[Alert] = list()
        self.service_up: bool = False
        self.send_alert_lock: Lock = Lock()
        self.strat_manager_service_web_client: StratManagerServiceWebClient = \
            StratManagerServiceWebClient(host=host, port=port)
        super().__init__(regex_file=regex_file, log_details=log_details, simulation_mode=simulation_mode,
                         debug_mode=debug_mode)

    def _init_service(self) -> bool:
        if self.service_up:
            return True
        else:
            self.service_up = is_service_up(ignore_error=True)
            if self.service_up:
                portfolio_status: PortfolioStatusBaseModel = \
                    self.strat_manager_service_web_client.get_portfolio_status_client(1)
                self.portfolio_alerts_cache = portfolio_status.portfolio_alerts
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
                    self.strat_manager_service_web_client.patch_portfolio_status_client(updated_portfolio_status)
                    created = True
                except Exception as e:
                    logging.error(f"_send_alerts failed;;;exception: {e}")
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
        cleaned_alert_str = re.sub(r"[0-9]*", "", cleaned_alert_str)
        return cleaned_alert_str

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

            callback_method = getattr(TradeSimulator, method_name)
            callback_method(**kwargs)
        except Exception as e:
            alert_brief: str = f"_process_trade_simulator_message failed in log analyzer"
            alert_details: str = f"message: {message}, exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            self._send_alerts(severity=self._get_severity("error"), alert_brief=alert_brief,
                              alert_details=alert_details)


if __name__ == '__main__':
    def main():
        from datetime import datetime
        # read log analyzer run configuration
        config_dict_path: PurePath = PAIR_STRAT_DATA_DIR / "config.yaml"
        config_dict: Dict = load_yaml_configurations(str(config_dict_path))
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
            LogDetail(service="strat_executor",
                      log_file=str(log_dir / f"strat_executor_{datetime_str}.log"), critical=True)
        ]
        configure_logger("debug", str(log_dir), f"addressbook_log_analyzer_{datetime_str}.log")
        AddressbookLogAnalyzer(regex_file=str(suppress_alert_regex_file), log_details=log_details,
                                   simulation_mode=simulation_mode)

    main()
