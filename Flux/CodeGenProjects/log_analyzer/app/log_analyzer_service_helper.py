from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import (
    YAMLConfigurationManager, get_symbol_side_key)
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_http_client import (
    LogAnalyzerServiceHttpClient)
from Flux.CodeGenProjects.pair_strat_engine.generated.FastApi.strat_manager_service_http_client import (
    StratManagerServiceHttpClient)

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

la_host, la_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

server_port = os.environ.get("PORT")
if server_port is not None and parse_to_int(server_port) != la_port:
    err_str = (f"Env var 'PORT' can't be different from 'main_server_beanie_port' key present in data/config.yaml of "
               f"this project, change config.yaml instead to use custom ports")
    logging.exception(err_str)
    raise Exception(err_str)

log_analyzer_service_http_client = \
    LogAnalyzerServiceHttpClient.set_or_get_if_instance_exists(la_host, la_port)

# pair_strat_service handling
pair_strat_config_yaml_path = PurePath(__file__).parent.parent.parent / "pair_strat_engine" / "data" / "config.yaml"
pair_strat_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(pair_strat_config_yaml_path))
pair_strat_port = pair_strat_config_yaml_dict.get("main_server_beanie_port")

ps_host, ps_port = pair_strat_config_yaml_dict.get("server_host"), parse_to_int(pair_strat_port)
strat_manager_service_http_client = \
    StratManagerServiceHttpClient.set_or_get_if_instance_exists(ps_host, ps_port)


def create_alert(alert_brief: str, alert_details: str | None = None,
                 severity: Severity = Severity.Severity_ERROR) -> Alert:
    kwargs = {}
    kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False, last_update_date_time=DateTime.utcnow(),
                  alert_count=1)
    if alert_details is not None:
        kwargs.update(alert_details=alert_details)
    return Alert(**kwargs)


def is_log_analyzer_service_up(ignore_error: bool = False) -> bool:
    try:
        portfolio_alerts_list: List[PortfolioAlertBaseModel] = (
            log_analyzer_service_http_client.get_all_portfolio_alert_client())

        # also creating portfolio_alerts model if not exist already
        if not portfolio_alerts_list:
            portfolio_alerts = PortfolioAlertBaseModel(_id=1, alerts=[], alert_update_seq_num=0)
            log_analyzer_service_http_client.create_portfolio_alert_client(portfolio_alerts)

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "is_strat_ongoing_query_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False
