# standard imports
from pathlib import PurePath
import os

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.raw_performance_data_processor import (RawPerformanceDataProcessor,
                                                                                 MongoConnectionReqs)
from FluxPythonUtils.scripts.utility_functions import (YAMLConfigurationManager,
                                                       get_primary_native_host_n_port_from_config_dict)
os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_http_client import (
    LogAnalyzerServiceHttpClient)
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import (
    ProcessedPerformanceAnalysisBaseModel)


PAIR_STRAT_DATA_DIR = PurePath(__file__).parent.parent / "data"
config_yaml_path = PAIR_STRAT_DATA_DIR / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
host = config_yaml_dict.get("server_host")
port = config_yaml_dict.get("main_server_beanie_port")
log_analyzer_service_web_client = LogAnalyzerServiceHttpClient.set_or_get_if_instance_exists(host, port)


if __name__ == "__main__":
    db_name = config_yaml_dict.get("db_name")
    if db_name is None:
        db_name = "log_analyzer"
    mongo_connection_reqs = MongoConnectionReqs(
        db=db_name,
        collection="RawPerformanceData"
    )

    raw_performance_data_processor = (
        RawPerformanceDataProcessor(log_analyzer_service_web_client,
                                    ProcessedPerformanceAnalysisBaseModel, mongo_connection_reqs,
                                    config_yaml_dict))
    raw_performance_data_processor.run()
