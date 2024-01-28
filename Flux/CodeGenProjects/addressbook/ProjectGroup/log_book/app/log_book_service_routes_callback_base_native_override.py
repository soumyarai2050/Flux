# standard imports
import subprocess

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_routes_callback import LogBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.pair_strat_engine_log_book import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import StratViewBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.app.pair_strat_engine_service_helper import (
    pair_strat_client_call_log_str, UpdateType, strat_manager_service_http_client)
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert, create_logger
# standard imports
from datetime import datetime

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

project_group_path = PurePath(__file__).parent.parent.parent
pair_strat_engine_log_dir: PurePath = project_group_path / "pair_strat_engine" / "log"
market_data_log_dir: PurePath = project_group_path / "market_data" / "log"
strat_executor_log_dir: PurePath = project_group_path / "strat_executor" / "log"
portfolio_monitor_log_dir: PurePath = project_group_path / "post_trade_engine" / "log"


class LogBookServiceRoutesCallbackBaseNativeOverride(LogBookServiceRoutesCallback):
    pair_strat_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DEBUG|INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
    background_log_prefix_regex_pattern: str = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : )?(" \
                                               r"DEBUG|INFO|WARNING|ERROR|CRITICAL):"
    log_prefix_regex_pattern_to_callable_name_dict = {
        pair_strat_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    log_cmd_prefix_regex_pattern_to_callable_name_dict = {
        pair_strat_log_prefix_regex_pattern: "handle_log_book_cmd_log_message"
    }
    background_log_prefix_regex_pattern_to_callable_name_dict = {
        background_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    underlying_read_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_create_portfolio_alert_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        self.pair_strat_engine_log_book: PairStratEngineLogBook | None = None
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        create_logger("log_book_cmd_log", logging.DEBUG, str(CURRENT_PROJECT_LOG_DIR),
                      log_book_cmd_log)

    def initialize_underlying_http_callables(self):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_routes import (
            underlying_read_portfolio_alert_http, underlying_create_portfolio_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_alert_http = (
            underlying_read_portfolio_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_portfolio_alert_http = (
            underlying_create_portfolio_alert_http)

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"log_book_{la_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        # starting log_book script once log analyzer service is up
                        PairStratEngineLogBook.asyncio_loop = self.asyncio_loop
                        self.pair_strat_engine_log_book = (LogBookServiceRoutesCallbackBaseNativeOverride.
                                                               start_pair_strat_log_book_script())

                        app_dir = PurePath(__file__).parent.parent / "app"
                        script_path = app_dir / 'log_simulator_log_book.py'
                        subprocess.Popen(['python', str(script_path), '&'])

                        self.service_ready = True
                        print(f"INFO: service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            # creating portfolio_alerts model if not exist already
                            run_coro = self.check_n_create_portfolio_alert()
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                            # block for task to finish
                            try:
                                future.result()
                                self.service_up = True
                                should_sleep = False
                            except Exception as e:
                                err_str_ = f"check_n_create_portfolio_alert failed with exception: {e}"
                                self.pair_strat_engine_log_book.portfolio_alert_fail_logger.exception(err_str_)
                                raise Exception(err_str_)
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        self.pair_strat_engine_log_book.portfolio_alert_fail_logger.exception(
                            "Unexpected: service startup threw exception, "
                            f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                            f";;;exception: {e}")
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
            else:
                should_sleep = True

    def get_generic_read_route(self):
        pass

    async def check_n_create_portfolio_alert(self):
        async with PortfolioAlert.reentrant_lock:
            portfolio_alert_list: List[PortfolioAlert] = (
                await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_alert_http())
            if len(portfolio_alert_list) == 0:
                portfolio_alert = PortfolioAlert(_id=1, alerts=[], alert_update_seq_num=0)
                await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_portfolio_alert_http(
                    portfolio_alert)

    def app_launch_pre(self):
        self.initialize_underlying_http_callables()

        self.port = la_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    @staticmethod
    def start_pair_strat_log_book_script() -> PairStratEngineLogBook:
        datetime_str = LogBookServiceRoutesCallbackBaseNativeOverride.datetime_str
        log_prefix_regex_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.log_prefix_regex_pattern_to_callable_name_dict)
        background_log_prefix_regex_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.background_log_prefix_regex_pattern_to_callable_name_dict)
        log_details: List[StratLogDetail] = [
            StratLogDetail(
                service="pair_strat_engine_beanie_fastapi",
                log_file_path=str(
                    pair_strat_engine_log_dir / f"pair_strat_engine_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="pair_strat_engine_background_debug",
                log_file_path=str(
                    pair_strat_engine_log_dir / f"pair_strat_engine_background_logs.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                background_log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="pair_strat_engine_background",
                log_file_path=str(
                    pair_strat_engine_log_dir / f"pair_strat_engine_background_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=background_log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="strat_executor",
                log_file_path=str(strat_executor_log_dir / f"strat_executor_*_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=True,
                strat_id_find_callable=strat_id_from_executor_log_file),
            StratLogDetail(
                service="post_trade_engine",
                log_file_path=str(portfolio_monitor_log_dir / f"post_trade_engine_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=True),
            StratLogDetail(
                service="log_book_cmd_log",
                log_file_path=str(CURRENT_PROJECT_LOG_DIR / log_book_cmd_log),
                critical=False,
                log_prefix_regex_pattern_to_callable_name_dict=
                LogBookServiceRoutesCallbackBaseNativeOverride.log_cmd_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
        ]
        suppress_alert_regex_file: PurePath = LOG_ANALYZER_DATA_DIR / "suppress_alert_regex.txt"

        simulation_mode: bool = config_yaml_dict.get("simulate_log_book", False)

        pair_strat_engine_log_book = PairStratEngineLogBook(str(suppress_alert_regex_file), log_details,
                                                                    simulation_mode=simulation_mode)
        pair_strat_log_book_thread = Thread(target=pair_strat_engine_log_book.start_analyzer, daemon=True)
        pair_strat_log_book_thread.start()
        return pair_strat_engine_log_book

    async def read_all_ui_layout_pre(self):
        # Setting asyncio_loop in ui_layout_pre since it called to check current service up
        attempt_counts = 3
        for _ in range(attempt_counts):
            if not self.asyncio_loop:
                self.asyncio_loop = asyncio.get_running_loop()
                time.sleep(1)
            else:
                break
        else:
            err_str_ = (f"self.asyncio_loop couldn't set as asyncio.get_running_loop() returned None for "
                        f"{attempt_counts} attempts")
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.critical(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    async def update_portfolio_alert_pre(self, stored_portfolio_alert_obj: PortfolioAlert,
                                         updated_portfolio_alert_obj: PortfolioAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_portfolio_alert_pre not ready - service is not initialized yet"
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_portfolio_alert_obj.alert_update_seq_num is None:
            updated_portfolio_alert_obj.alert_update_seq_num = 0
        updated_portfolio_alert_obj.alert_update_seq_num += 1
        return updated_portfolio_alert_obj

    async def partial_update_portfolio_alert_pre(self, stored_portfolio_alert_obj: PortfolioAlert,
                                                 updated_portfolio_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_portfolio_alert_pre not ready - service is not initialized yet"
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if stored_portfolio_alert_obj.alert_update_seq_num is None:
            stored_portfolio_alert_obj.alert_update_seq_num = 0
        updated_portfolio_alert_obj_json["alert_update_seq_num"] = stored_portfolio_alert_obj.alert_update_seq_num + 1
        return updated_portfolio_alert_obj_json

    async def partial_update_all_portfolio_alert_pre(self, stored_portfolio_alert_obj_list: List[PortfolioAlert],
                                                     updated_portfolio_alert_obj_json_list: List[Dict]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_all_portfolio_alert_pre not ready - service is not initialized yet"
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        for index, stored_portfolio_alert_obj in enumerate(stored_portfolio_alert_obj_list):
            if stored_portfolio_alert_obj.alert_update_seq_num is None:
                stored_portfolio_alert_obj.alert_update_seq_num = 0
            updated_portfolio_alert_obj_json_list[index]["alert_update_seq_num"] = (
                    stored_portfolio_alert_obj.alert_update_seq_num + 1)
            return updated_portfolio_alert_obj_json_list

    async def create_strat_alert_pre(self, strat_alert_obj: StratAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = (f"create_strat_alert_pre not ready - service is not initialized yet, "
                        f"strat_alert id: {strat_alert_obj.id};;; strat_alert: {strat_alert_obj}")
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

    async def create_strat_alert_post(self, strat_alert_obj: StratAlert):
        # updating StratView for this strat using log analyzer functionality to update pair_start_engine
        strat_alert_aggregated_severity = strat_alert_obj.strat_alert_aggregated_severity
        strat_alert_count = strat_alert_obj.alert_count

        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=strat_alert_obj.id,
                                                 strat_alert_aggregated_severity=strat_alert_aggregated_severity,
                                                 strat_alert_count=strat_alert_count)
        self.pair_strat_engine_log_book.process_pair_strat_api_ops(log_str)

    async def update_strat_alert_pre(self, stored_strat_alert_obj: StratAlert, updated_strat_alert_obj: StratAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_strat_alert_pre not ready - service is not initialized yet"
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_strat_alert_obj.alert_update_seq_num is None:
            updated_strat_alert_obj.alert_update_seq_num = 0
        updated_strat_alert_obj.alert_update_seq_num += 1
        return updated_strat_alert_obj

    async def update_strat_alert_post(self, stored_strat_alert_obj: StratAlert, updated_strat_alert_obj: StratAlert):
        # updating StratView for this strat using log analyzer functionality to update pair_start_engine
        strat_alert_aggregated_severity = updated_strat_alert_obj.strat_alert_aggregated_severity
        strat_alert_count = updated_strat_alert_obj.alert_count

        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_alert_obj.id,
                                                 strat_alert_aggregated_severity=strat_alert_aggregated_severity,
                                                 strat_alert_count=strat_alert_count)
        self.pair_strat_engine_log_book.process_pair_strat_api_ops(log_str)

    async def partial_update_all_strat_alert_pre(self, stored_strat_alert_obj_list: List[StratAlert],
                                                 updated_strat_alert_obj_json_list: List[Dict]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_all_strat_alert_pre not ready - service is not initialized yet"
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        for index, stored_strat_alert_obj in enumerate(stored_strat_alert_obj_list):
            if stored_strat_alert_obj.alert_update_seq_num is None:
                stored_strat_alert_obj.alert_update_seq_num = 0
            updated_strat_alert_obj_json_list[index]["alert_update_seq_num"] = (
                    stored_strat_alert_obj.alert_update_seq_num + 1)
        return updated_strat_alert_obj_json_list

    async def partial_update_all_strat_alert_post(self, stored_strat_alert_obj_list: List[StratAlert],
                                                  updated_strat_alert_obj_list: List[StratAlertOptional]):
        # updating StratView for this strat using log analyzer functionality to update pair_start_engine
        for updated_strat_alert_obj in updated_strat_alert_obj_list:
            strat_alert_aggregated_severity = updated_strat_alert_obj.strat_alert_aggregated_severity
            strat_alert_count = updated_strat_alert_obj.alert_count

            log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                     strat_manager_service_http_client.patch_all_strat_view_client,
                                                     UpdateType.SNAPSHOT_TYPE, _id=updated_strat_alert_obj.id,
                                                     strat_alert_aggregated_severity=strat_alert_aggregated_severity,
                                                     strat_alert_count=strat_alert_count)
            self.pair_strat_engine_log_book.process_pair_strat_api_ops(log_str)

    async def partial_update_strat_alert_pre(self, stored_strat_alert_obj: StratAlert,
                                             updated_strat_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_strat_alert_pre not ready - service is not initialized yet"
            self.pair_strat_engine_log_book.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if stored_strat_alert_obj.alert_update_seq_num is None:
            stored_strat_alert_obj.alert_update_seq_num = 0
        updated_strat_alert_obj_json["alert_update_seq_num"] = stored_strat_alert_obj.alert_update_seq_num + 1
        return updated_strat_alert_obj_json

    async def partial_update_strat_alert_post(self, stored_strat_alert_obj: StratAlert,
                                              updated_strat_alert_obj: StratAlertOptional):
        # updating StratView for this strat using log analyzer functionality to update pair_start_engine
        strat_alert_aggregated_severity = updated_strat_alert_obj.strat_alert_aggregated_severity
        strat_alert_count = updated_strat_alert_obj.alert_count

        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_alert_obj.id,
                                                 strat_alert_aggregated_severity=strat_alert_aggregated_severity,
                                                 strat_alert_count=strat_alert_count)
        self.pair_strat_engine_log_book.process_pair_strat_api_ops(log_str)

    async def log_book_restart_tail_query_pre(
            self, log_book_restart_tail_class_type: Type[LogBookRestartTail], log_file_name: str,
            start_timestamp: str | None = None):
        log_pattern_to_restart_tail_process(log_file_name, start_timestamp)
        return []

    async def log_book_force_kill_tail_query_pre(
            self, log_book_force_kill_tail_class_type: Type[LogBookForceKillTail], log_file_name: str):
        log_pattern_to_force_kill_tail_process(log_file_name)
        return []

    async def log_book_remove_file_from_created_cache_query_pre(
            self, log_book_remove_file_from_created_cache_class_type: Type[LogBookRemoveFileFromCreatedCache],
            log_file_path_list: List[str]):
        for log_file_path in log_file_path_list:
            log_pattern_to_remove_file_from_created_cache(log_file_path)
        return []

def strat_id_from_executor_log_file(file_name: str) -> int | None:
    # Using regex to extract the number
    number_pattern = re.compile(r'strat_executor_(\d+)_logs_\d{8}\.log')

    match = number_pattern.search(file_name)

    if match:
        extracted_number = match.group(1)
        return parse_to_int(extracted_number)
    return None
