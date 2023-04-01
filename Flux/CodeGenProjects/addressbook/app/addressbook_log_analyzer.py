# System imports
import logging
import os
import time
from pathlib import PurePath
from typing import List, Optional
from pendulum import DateTime
import re

# Project imports
from FluxPythonUtils.scripts.utility_functions import configure_logger
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer

os.environ["DBType"] = "beanie"
from FluxPythonUtils.scripts.utility_functions import get_host_port_from_env
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Alert, \
    PortfolioStatusBaseModel
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import create_alert
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator

host, port = get_host_port_from_env()
debug_mode: bool = False if (debug_env := os.getenv("DEBUG")) is None or len(debug_env) == 0 or debug_env == "0" \
    else True


class AddressbookLogAnalyzer(LogAnalyzer):
    def __init__(self, log_files: Optional[List[str]]):
        logging.info(f"starting log analyzer. monitoring log_files: {log_files}")
        self.strat_manager_service_web_client = StratManagerServiceWebClient(host=host, port=port)
        super().__init__(log_files, debug_mode=debug_mode)

    def _send_alerts(self, severity: str, alert_brief: str, alert_details: str):
        logging.debug(f"sending alert with severity: {severity}, alert_brief: {alert_brief}, "
                      f"alert_details: {alert_details}")
        created: bool = False
        while not created:
            try:
                alert_obj: Alert | None = None
                if not alert_details:
                    alert_details = None
                portfolio_status: PortfolioStatusBaseModel = \
                    self.strat_manager_service_web_client.get_portfolio_status_client(1)
                if portfolio_status.portfolio_alerts is not None:
                    for portfolio_alert in portfolio_status.portfolio_alerts:
                        stored_alert_brief = portfolio_alert.alert_brief
                        stored_alert_brief = stored_alert_brief.split(":", 3)[-1].strip()
                        stored_alert_brief = re.sub(f'0x[a-f0-9]*', '', stored_alert_brief)

                        stored_alert_details = portfolio_alert.alert_details
                        if stored_alert_details is not None:
                            stored_alert_details = re.sub(f'0x[a-f0-9]*', '', stored_alert_details)

                        cleaned_alert_brief = alert_brief.split(":", 3)[-1].strip()
                        cleaned_alert_brief = re.sub(f'0x[a-f0-9]*', '', cleaned_alert_brief)
                        cleaned_alert_details = alert_details
                        if alert_details is not None:
                            cleaned_alert_details = re.sub(f'0x[a-f0-9]*', '', cleaned_alert_details)

                        if cleaned_alert_brief == stored_alert_brief and \
                                cleaned_alert_details == stored_alert_details and \
                                severity == portfolio_alert.severity:
                            alert_obj = portfolio_alert
                            alert_obj.last_update_date_time = DateTime.utcnow()
                            alert_obj.alert_count += 1
                            break
                        # else not required
                if alert_obj is None:
                    alert_obj = create_alert(alert_brief=alert_brief, alert_details=alert_details,
                                             severity=severity)
                portfolio_status.portfolio_alerts = [alert_obj]
                self.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status)
                created = True
            except Exception as e:
                logging.error(f"_send_alerts failed;;;exception: {e}")
                time.sleep(30)

    def _process_trade_simulator_message(self, message: str):
        # remove $$$ from beginning of message
        try:
            message: str = message[3:]
            args: List[str] = message.split("~~")
            method_name = args.pop(0)

            kwargs = {}
            # get method kwargs separated by "^^" if any
            for arg in args:
                key, value = arg.split("^^")
                kwargs[key] = value

            callback_method = getattr(TradeSimulator, method_name)
            callback_method(**kwargs)
        except Exception as e:
            logging.exception(f"_process_trade_simulator_message failed, message: {message};;; exception: {e}")


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
