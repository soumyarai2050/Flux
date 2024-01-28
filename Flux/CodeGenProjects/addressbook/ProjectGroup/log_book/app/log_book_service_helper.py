import datetime
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import (
    YAMLConfigurationManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_client import (
    LogBookServiceHttpClient)

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_LOG_DIR = PurePath(__file__).parent.parent / "log"

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

la_host, la_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

log_book_service_http_client = \
    LogBookServiceHttpClient.set_or_get_if_instance_exists(la_host, la_port)

datetime_str = datetime.datetime.now().strftime("%Y%m%d")
log_book_cmd_log = f"log_book_cmd_logs_{datetime_str}.log"
portfolio_alert_fail_log = f"portfolio_alert_fail_logs_{datetime_str}.log"
simulator_portfolio_alert_fail_log = f"simulator_portfolio_alert_fail_logs_{datetime_str}.log"


def create_alert(alert_brief: str, alert_details: str | None = None,
                 severity: Severity = Severity.Severity_ERROR) -> AlertOptional:
    kwargs = {}
    kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False, last_update_date_time=DateTime.utcnow(),
                  alert_count=1)
    if alert_details is not None:
        kwargs.update(alert_details=alert_details)
    return AlertOptional(**kwargs)


def is_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            log_book_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def log_pattern_to_restart_tail_process(log_file_name: str, restart_time: str | None = None):
    log_str = f"---{log_file_name}"
    if restart_time is not None:
        log_str += f"~~{restart_time}"
    logger = logging.getLogger("log_book_cmd_log")
    logger.info(log_str)


def log_pattern_to_force_kill_tail_process(log_file_name: str):
    log_str = f"-@-{log_file_name}"
    logger = logging.getLogger("log_book_cmd_log")
    logger.info(log_str)


def log_pattern_to_remove_file_from_created_cache(log_file_name: str):
    log_str = f"-*-{log_file_name}"
    logger = logging.getLogger("log_book_cmd_log")
    logger.info(log_str)
