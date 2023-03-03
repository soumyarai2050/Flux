# System imports
import logging
import os
import time
from typing import List, Dict
from pathlib import PurePath

# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer
os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Alert, \
    PortfolioStatusBaseModel
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_cache_model import PortfolioStatus

host = os.getenv("HOST")
if host is None or len(host) == 0:
    host = "127.0.0.1"

port = os.getenv("PORT")
if port is None or len(port) == 0:
    int_port = 8000
else:
    int_port = int(port)


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, log_file_path_and_name):
        super().__init__(log_file_path_and_name)
        self.strat_manager_service_web_client = StratManagerServiceWebClient(host=host, port=int_port)
        self._analyze_log()

    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str):
        created: bool = False
        while not created:
            try:
                portfolio_status_base_model = PortfolioStatusBaseModel(_id=1)
                alert_obj = Alert(_id=Alert.next_id(), dismiss=False, severity=severity, alert_brief=alert_brief,
                                  alert_details=alert_details, impacted_order=None)
                portfolio_status_base_model.portfolio_alerts = [alert_obj]
                self.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_base_model)
                created = True
                alert_created: bool = False
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
