# System imports
import logging
import os
import time
from pathlib import PurePath

# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Alert, \
    PortfolioStatusBaseModel

host: str = "127.0.0.1" if (host_env := os.getenv("HOST")) is None or len(host_env) == 0 else host_env
port: str = "8020" if (port_env := os.getenv("PORT")) is None or len(port_env) == 0 else port_env
int_port: int = int(port)
debug_mode: bool = False if (debug_env := os.getenv("DEBUG")) is None or len(debug_env) == 0 or debug_env == "0" \
    else debug_env


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, log_file_path_and_name):
        super().__init__(log_file_path_and_name, debug_mode=debug_mode)
        self.strat_manager_service_web_client = StratManagerServiceWebClient(host=host, port=int_port)
        self._analyze_log()

    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str):
        logging.debug(f"sending alert severity: {severity}, alert_brief: {alert_brief};;;"
                      f"alert_details: {alert_details}")
        created: bool = False
        while not created:
            try:
                portfolio_status_base_model: PortfolioStatusBaseModel = PortfolioStatusBaseModel(_id=1)
                alert_obj: Alert = Alert(_id=Alert.next_id(), dismiss=False, severity=severity, alert_brief=alert_brief,
                                         alert_details=alert_details, impacted_order=None)
                portfolio_status_base_model.portfolio_alerts = [alert_obj]
                self.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_base_model)
                created = True
            except Exception as e:
                logging.error(f"_send_alerts failed;;; exception: {e}", exc_info=True)
                time.sleep(60)


if __name__ == '__main__':
    def main():
        from datetime import datetime
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        datetime_str: str = datetime.now().strftime("%Y%m%d")
        configure_logger('debug', str(log_dir), f'addressbook_log_analyzer_{datetime_str}.log')
        AddressbookLogAnalyzer(str(log_dir / f'addressbook_beanie_logs_{datetime_str}.log'))

    main()
