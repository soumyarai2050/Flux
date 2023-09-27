# project imports
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_routes_callback import LogAnalyzerServiceRoutesCallback
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import *


class LogAnalyzerServiceRoutesCallbackBaseNativeOverride(LogAnalyzerServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass

    def get_generic_read_route(self):
        pass

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
