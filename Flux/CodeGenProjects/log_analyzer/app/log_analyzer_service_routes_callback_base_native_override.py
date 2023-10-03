# project imports
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_routes_callback import LogAnalyzerServiceRoutesCallback
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import *
from Flux.CodeGenProjects.log_analyzer.app.pair_strat_engine_log_analyzer import *
from Flux.CodeGenProjects.log_analyzer.app.log_analyzer_service_helper import *
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert

# standard imports
from datetime import datetime

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)
pair_strat_engine_log_dir: PurePath = code_gen_projects_path / "pair_strat_engine" / "log"
market_data_log_dir: PurePath = code_gen_projects_path / "market_data" / "log"
strat_executor_log_dir: PurePath = code_gen_projects_path / "strat_executor" / "log"


class LogAnalyzerServiceRoutesCallbackBaseNativeOverride(LogAnalyzerServiceRoutesCallback):
    pair_strat_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DEBUG|INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
    log_prefix_regex_pattern_to_callable_name_dict = {
        pair_strat_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    datetime_str: str = datetime.now().strftime("%Y%m%d")

    def __init__(self):
        super().__init__()
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30

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
            service_up_flag_env_var = os.environ.get(f"log_analyzer_{server_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True

                        # starting log_analyzer script once log analyzer service is up
                        thread = (
                            Thread(target=LogAnalyzerServiceRoutesCallbackBaseNativeOverride.start_log_analyzer_script,
                                   daemon=True))
                        thread.start()

                if not self.service_up:
                    try:
                        if is_log_analyzer_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
            else:
                should_sleep = True

    def get_generic_read_route(self):
        pass

    def app_launch_pre(self):
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    @staticmethod
    def start_log_analyzer_script():
        datetime_str = LogAnalyzerServiceRoutesCallbackBaseNativeOverride.datetime_str
        log_prefix_regex_pattern_to_callable_name_dict = (
            LogAnalyzerServiceRoutesCallbackBaseNativeOverride.log_prefix_regex_pattern_to_callable_name_dict)
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
                      log_file_path=str(strat_executor_log_dir / f"strat_executor_beanie_*_{datetime_str}.log"),
                      critical=True,
                      log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                      log_file_path_is_regex=True)
        ]
        suppress_alert_regex_file: PurePath = LOG_ANALYZER_DATA_DIR / "suppress_alert_regex.txt"

        simulation_mode: bool = config_yaml_dict.get("simulate_log_analyzer", False)

        pair_strat_log_analyzer_thread = Thread(target=PairStratEngineLogAnalyzer,
                                                kwargs={"regex_file": str(suppress_alert_regex_file),
                                                        "log_details": log_details,
                                                        "simulation_mode": simulation_mode}, daemon=True)
        pair_strat_log_analyzer_thread.start()
        # PairStratEngineLogAnalyzer(regex_file=str(suppress_alert_regex_file), log_details=log_details,
        #                            simulation_mode=simulation_mode)

    async def get_raw_performance_data_of_callable_query_pre(
            self, raw_performance_data_of_callable_class_type: Type[RawPerformanceDataOfCallable], callable_name: str):
        from Flux.PyCodeGenEngine.FluxCodeGenCore.aggregate_core import \
            get_raw_performance_data_from_callable_name_agg_pipeline
        from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_http_routes import \
            underlying_read_raw_performance_data_http

        raw_performance_data_list = \
            await underlying_read_raw_performance_data_http(
                get_raw_performance_data_from_callable_name_agg_pipeline(callable_name), self.get_generic_read_route())

        raw_performance_data_of_callable = RawPerformanceDataOfCallable(raw_performance_data=raw_performance_data_list)

        return [raw_performance_data_of_callable]

    async def update_portfolio_alert_pre(self, stored_portfolio_alert_obj: PortfolioAlert,
                                         updated_portfolio_alert_obj: PortfolioAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_portfolio_alert_pre not ready - service is not initialized yet"
            logging.error(err_str_)
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
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if stored_portfolio_alert_obj.alert_update_seq_num is None:
            updated_portfolio_alert_obj_json["alert_update_seq_num"] = 0
        updated_portfolio_alert_obj_json["alert_update_seq_num"] = stored_portfolio_alert_obj.alert_update_seq_num + 1
        return updated_portfolio_alert_obj_json

    async def create_strat_alert_pre(self, strat_alert_obj: StratAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = (f"create_strat_alert_pre not ready - service is not initialized yet, "
                        f"strat_alert id: {strat_alert_obj.id};;; strat_alert: {strat_alert_obj}")
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

    async def update_strat_alert_pre(self, stored_strat_alert_obj: StratAlert, updated_strat_alert_obj: StratAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_strat_alert_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_strat_alert_obj.alert_update_seq_num is None:
            updated_strat_alert_obj.alert_update_seq_num = 0
        updated_strat_alert_obj.alert_update_seq_num += 1
        return updated_strat_alert_obj

    async def partial_update_strat_alert_pre(self, stored_strat_alert_obj: StratAlert,
                                             updated_strat_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_strat_alert_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if stored_strat_alert_obj.alert_update_seq_num is None:
            updated_strat_alert_obj_json["alert_update_seq_num"] = 0
        updated_strat_alert_obj_json["alert_update_seq_num"] = stored_strat_alert_obj.alert_update_seq_num + 1
        return updated_strat_alert_obj_json
