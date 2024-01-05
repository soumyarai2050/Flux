from Flux.CodeGenProjects.performance_benchmark.generated.Pydentic.performance_benchmark_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import (
    YAMLConfigurationManager)
from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_http_client import (
    PerformanceBenchmarkServiceHttpClient)


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

pb_host, pb_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

performance_benchmark_service_http_client = \
    PerformanceBenchmarkServiceHttpClient.set_or_get_if_instance_exists(pb_host, pb_port)


def is_performance_benchmark_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            performance_benchmark_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False
