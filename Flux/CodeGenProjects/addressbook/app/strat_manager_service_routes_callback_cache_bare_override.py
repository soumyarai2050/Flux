# project imports
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes_callback import StratManagerServiceRoutesCallback


class StratManagerServiceRoutesCallbackCacheBareOverride(StratManagerServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
