# System imports
import logging
import os
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


LOG_ANALYZER_DATA_DIR = PurePath(__file__).parent.parent / 'generated'


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, log_file_path_and_name):
        super().__init__(log_file_path_and_name)
        self.strat_manager_service_web_client = StratManagerServiceWebClient()
        self._analyze_log()

    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str):
        portfolio_status_obj_list: List[PortfolioStatus] = \
            self.strat_manager_service_web_client.get_all_portfolio_status_client()
        if len(portfolio_status_obj_list) == 1:
            portfolio_status_base_model = PortfolioStatusBaseModel(**portfolio_status_obj_list[0].dict())
            alert_obj = Alert(dismiss=False, severity=severity, alert_brief=alert_brief,
                              alert_details=alert_details, impacted_order=None)
            portfolio_status_base_model.portfolio_alerts.append(alert_obj)
            self.strat_manager_service_web_client.put_portfolio_status_client(portfolio_status_base_model)
        else:
            err_str = f"send_alerts failed - portfolio_status_obj count expected 1 found: " \
                       f"{len(portfolio_status_obj_list)} while raising alert with severity: {severity}, brief: " \
                       f"{alert_brief}, alert_details: {alert_details}"
            logging.critical(err_str)


if __name__ == '__main__':
    def main():
        configure_logger('debug', str(LOG_ANALYZER_DATA_DIR), 'log_analyzer.log')
        AddressbookLogAnalyzer(str(LOG_ANALYZER_DATA_DIR / 'beanie_logs.log'))

    main()
