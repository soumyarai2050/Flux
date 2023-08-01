# project imports
from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_routes_callback import MarketDataServiceRoutesCallback


class MarketDataServiceRoutesCallbackCacheOverride(MarketDataServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
