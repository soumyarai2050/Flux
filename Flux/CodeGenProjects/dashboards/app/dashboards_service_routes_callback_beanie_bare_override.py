# project imports
from Flux.CodeGenProjects.dashboards.generated.FastApi.dashboards_service_routes_callback import DashboardsServiceRoutesCallback


class DashboardsServiceRoutesCallbackBeanieBareOverride(DashboardsServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
