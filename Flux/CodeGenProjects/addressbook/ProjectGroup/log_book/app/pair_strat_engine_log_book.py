import logging
import os
import time
import re
from threading import Thread
from queue import Queue
from typing import Set

os.environ["DBType"] = "beanie"
# Project imports
from FluxPythonUtils.log_book.log_book import LogDetail, get_transaction_counts_n_timeout_from_config
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.pair_strat_engine_base_log_book import (
    PairStratEngineBaseLogBook, StratLogDetail)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import \
    PairStratBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.app.pair_strat_engine_service_helper import (
    strat_manager_service_http_client, is_ongoing_strat, Side)
from FluxPythonUtils.scripts.utility_functions import create_logger


LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

portfolio_alert_bulk_update_counts_per_call, portfolio_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("portfolio_alert_configs")))
strat_alert_bulk_update_counts_per_call, strat_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("strat_alert_config")))


class PairStratEngineLogBook(PairStratEngineBaseLogBook):
    underlying_partial_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_partial_update_all_strat_alert_http: Callable[..., Any] | None = None
    underlying_read_portfolio_alert_by_id_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_by_id_http: Callable[..., Any] | None = None

    asyncio_loop: ClassVar[asyncio.AbstractEventLoop | None] = None

    def __init__(self, regex_file: str, log_details: List[LogDetail] | None = None,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 simulation_mode: bool = False):
        super().__init__(regex_file, log_details, log_prefix_regex_pattern_to_callable_name_dict, simulation_mode)
        logging.info(f"starting pair_strat log analyzer. monitoring logs: {log_details}")
        if self.simulation_mode:
            print("CRITICAL: PairStrat log analyzer running in simulation mode...")
            alert_brief: str = "PairStrat Log analyzer running in simulation mode"
            self.send_portfolio_alerts(severity=self.get_severity("critical"), alert_brief=alert_brief)

        if PairStratEngineLogBook.asyncio_loop is None:
            err_str_ = ("Couldn't find asyncio_loop class data member in PairStratEngineLogBook, "
                        "exiting PairStratEngineLogBook run.")
            logging.critical(err_str_)
            self.send_portfolio_alerts(severity=self.get_severity("critical"), alert_brief=err_str_)
            raise Exception(err_str_)
        self.portfolio_alert_fail_logger = create_logger("portfolio_alert_fail_logger", logging.DEBUG,
                                                         str(CURRENT_PROJECT_LOG_DIR), portfolio_alert_fail_log)

    def start_analyzer(self):
        Thread(target=self._pair_strat_api_ops_queue_handler, daemon=True).start()
        self.run_queue_handler()
        self.run()

    def _handle_strat_alert_queue_err_handler(self, *args):
        try:
            alerts_list = []
            for pydantic_obj_json in args[0]:
                alerts_json = pydantic_obj_json.get("alerts")
                for alerts_json_ in alerts_json:
                    alerts_list.append(Alert(**alerts_json_))
            portfolio_alert = PortfolioAlertBaseModel(_id=1, alerts=alerts_list)
            self.portfolio_alert_queue.put(jsonable_encoder(portfolio_alert, by_alias=True, exclude_none=True))
        except Exception as e:
            err_str_ = f"_handle_strat_alert_queue_err_handler failed, passed args: {args};;; exception: {e}"
            self.portfolio_alert_fail_logger.exception(err_str_)

    def _handle_strat_alert_queue(self):
        PairStratEngineLogBook.queue_handler(
            self.strat_alert_queue, strat_alert_bulk_update_counts_per_call,
            strat_alert_bulk_update_timeout,
            self.patch_all_strat_alert_client_with_asyncio_loop,
            self._handle_strat_alert_queue_err_handler)

    def patch_all_strat_alert_client_with_asyncio_loop(self, pydantic_obj_json_list: Dict):
        run_coro = PairStratEngineLogBook.underlying_partial_update_all_strat_alert_http(pydantic_obj_json_list)
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

    def _process_strat_alert_message(self, prefix: str, message: str, pair_strat_id: int | None = None) -> None:
        try:
            if pair_strat_id is None:
                pattern: re.Pattern = re.compile("%%(.*?)%%")
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

                if len(symbol_side_set) == 0:
                    raise Exception("no symbol-side pair found while creating strat alert, ")

                # adding log analyzer event handler to be triggered from log pattern in log pattern
                if "ResetLogBookCache" in log_message:
                    # update strat_id_by_symbol_side_dict cache if strat is DONE, this prevents alert for new strat
                    # created with already existing symbol_side to be created in the correct strat_alerts
                    symbol_side: str
                    for symbol_side in symbol_side_set:
                        self.strat_id_by_symbol_side_dict.pop(symbol_side, None)
                    return

                symbol_side: str = list(symbol_side_set)[0]
                symbol, side = symbol_side.split("-")
                strat_id: int | None = self.strat_id_by_symbol_side_dict.get(symbol_side)

                if strat_id is None or self.strat_alert_cache_by_strat_id_dict.get(strat_id) is None:

                    pair_strat_obj: PairStratBaseModel = self._get_pair_strat_obj_from_symbol_side(symbol, side)
                    strat_id = pair_strat_obj.id

                    if pair_strat_obj is None:
                        raise Exception(f"No ongoing pair strat found for symbol_side: {symbol_side}")
                    if not pair_strat_obj.is_executor_running:
                        raise Exception(f"StartExecutor Server not running for pair_strat: {pair_strat_obj}")

                    self._update_strat_alert_cache(strat_id)
                    self.strat_id_by_symbol_side_dict[symbol_side] = strat_id
                # else not required: alert cache exists

            else:
                error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=prefix, log_message=message)

                # if error pattern does not match, ignore creating alert
                if error_dict is None:
                    return

                strat_id = pair_strat_id
                if self.strat_alert_cache_by_strat_id_dict.get(strat_id) is None:
                    try:
                        pair_strat: PairStratBaseModel = strat_manager_service_http_client.get_pair_strat_client(strat_id)
                    except Exception as e:
                        raise Exception(f"get_pair_strat_client failed: Can't find pair_start with id: {strat_id}")
                    else:
                        if not is_ongoing_strat(pair_strat):
                            raise Exception(f"pair_strat of id: {strat_id} is not in ongoing state while updating "
                                            f"strat_alert cache, pair_strat: {pair_strat}")

                        self._update_strat_alert_cache(strat_id)
                        symbol_side = f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}-{pair_strat.pair_strat_params.strat_leg1.side}"
                        self.strat_id_by_symbol_side_dict[symbol_side] = strat_id

            severity, alert_brief, alert_details = self._create_alert(error_dict=error_dict)
            self._send_strat_alerts(strat_id, severity, alert_brief, alert_details)
        except Exception as e:
            alert_brief: str = f"_process_strat_alert_message failed - {message}"
            alert_details: str = f"exception: {e}"
            logging.exception(f"{alert_brief};;; {alert_details}")
            self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                       alert_details=alert_details)

    # strat lvl alert handling
    def _send_strat_alerts(self, strat_id: int, severity: str, alert_brief: str, alert_details: str) -> None:
        logging.debug(f"sending strat alert with strat_id: {strat_id} severity: {severity}, alert_brief: "
                      f"{alert_brief}, alert_details: {alert_details}")
        while True:
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
                break
            except Exception as e:
                alert_details: str = f"_send_strat_alerts failed;;;exception: {e}"
                logging.exception(f"{alert_brief};;; {alert_details}")
                self.send_portfolio_alerts(severity=self.get_severity("error"), alert_brief=alert_brief,
                                           alert_details=alert_details)

    def handle_pair_strat_matched_log_message(self, log_prefix: str, log_message: str,
                                              log_detail: StratLogDetail):
        if hasattr(log_detail, "strat_id_find_callable") and log_detail.strat_id_find_callable is not None:
            # handle strat alert message
            logging.info(f"Strat alert message from strat_id based log: {log_message}")
            pair_strat_id = log_detail.strat_id_find_callable(log_detail.log_file_path)
            self._process_strat_alert_message(log_prefix, log_message, pair_strat_id)
            return

        # put in method
        if re.compile(r"%%.*%%").search(log_message):
            # handle strat alert message
            logging.info(f"Strat alert message: {log_message}")
            self._process_strat_alert_message(log_prefix, log_message)
            return

        if log_message.startswith("^^^"):
            # handle pair_strat db updates
            logging.info(f"pair_strat_engine update found: {log_message}")
            self.process_pair_strat_api_ops(log_message)
            return

        # Sending ERROR/WARNING type log to portfolio_alerts
        logging.debug(f"Processing log line: {log_message[:200]}...")
        error_dict: Dict[str, str] | None = self._get_error_dict(log_prefix=log_prefix, log_message=log_message)
        if error_dict is not None:
            severity, alert_brief, alert_details = self._create_alert(error_dict)
            self.send_portfolio_alerts(severity=severity, alert_brief=alert_brief, alert_details=alert_details)
        # else not required: error pattern doesn't match, no alerts to send
