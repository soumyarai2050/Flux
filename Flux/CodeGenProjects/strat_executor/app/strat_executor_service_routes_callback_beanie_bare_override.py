# project imports
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_routes_callback import StratExecutorServiceRoutesCallback


class StratExecutorServiceRoutesCallbackBeanieBareOverride(StratExecutorServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
