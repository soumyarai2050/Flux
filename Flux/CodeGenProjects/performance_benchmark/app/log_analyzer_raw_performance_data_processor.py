# standard imports
from pathlib import PurePath
import os

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.raw_performance_data_processor import (RawPerformanceDataProcessor,
                                                                                 MongoConnectionReqs)
from FluxPythonUtils.scripts.utility_functions import (YAMLConfigurationManager,
                                                       get_primary_native_host_n_port_from_config_dict)
os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import (
    performance_benchmark_service_http_client)
from Flux.CodeGenProjects.performance_benchmark.generated.Pydentic.performance_benchmark_service_model_imports import (
    ProcessedPerformanceAnalysisBaseModel)


PAIR_STRAT_DATA_DIR = PurePath(__file__).parent.parent / "data"
config_yaml_path = PAIR_STRAT_DATA_DIR / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))


if __name__ == "__main__":
    db_name = config_yaml_dict.get("db_name")
    if db_name is None:
        db_name = "log_analyzer"
    mongo_connection_reqs = MongoConnectionReqs(
        db=db_name,
        collection="RawPerformanceData"
    )

    raw_performance_data_processor = (
        RawPerformanceDataProcessor(performance_benchmark_service_http_client,
                                    ProcessedPerformanceAnalysisBaseModel, mongo_connection_reqs,
                                    config_yaml_dict))
    raw_performance_data_processor.run()
