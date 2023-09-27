# project imports
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_routes_callback import LogAnalyzerServiceRoutesCallback


class LogAnalyzerServiceRoutesCallbackBeanieBareOverride(LogAnalyzerServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
