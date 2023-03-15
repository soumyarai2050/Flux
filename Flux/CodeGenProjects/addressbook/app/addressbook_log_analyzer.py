# System imports
import logging
import os
import time
from pathlib import PurePath
from typing import List, Optional

# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer

os.environ["DBType"] = "beanie"
from FluxPythonUtils.scripts.utility_functions import get_host_port_from_env
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Alert, \
    PortfolioStatusBaseModel


host, port = get_host_port_from_env()
debug_mode: bool = False if (debug_env := os.getenv("DEBUG")) is None or len(debug_env) == 0 or debug_env == "0" \
    else True


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, log_files: Optional[List[str]]):
        self.strat_manager_service_web_client = StratManagerServiceWebClient(host=host, port=port)
        super().__init__(log_files, debug_mode=debug_mode)

    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str):
        logging.debug(f"sending alert with severity: {severity}, alert_brief: {alert_brief}, "
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
                time.sleep(30)


if __name__ == '__main__':
    def main():
        from datetime import datetime
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        market_data_log_dir: PurePath = PurePath(__file__).parent.parent.parent / "market_data" / "log"
        datetime_str: str = datetime.now().strftime("%Y%m%d")
        log_files: List[str] = [
            str(market_data_log_dir / f"market_data_beanie_logs_{datetime_str}.log"),
            str(log_dir / f"addressbook_beanie_logs_{datetime_str}.log"),
            str(log_dir / f"strat_executor_{datetime_str}.log")
        ]
        configure_logger("debug", str(log_dir), f"addressbook_log_analyzer_{datetime_str}.log")
        AddressbookLogAnalyzer(log_files)

    main()
