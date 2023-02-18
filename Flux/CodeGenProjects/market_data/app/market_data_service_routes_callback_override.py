import logging
from pendulum import DateTime
# project imports
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.pair_strat_engine.generated.strat_manager_service_web_client import StratManagerServiceWebClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_routes_callback import \
    MarketDataServiceRoutesCallback

market_data_service_web_client_internal = MarketDataServiceWebClient()
market_data_service_web_client_external = StratManagerServiceWebClient(port=8080)


class MarketDataServiceRoutesCallbackOverride(MarketDataServiceRoutesCallback):

    def __init__(self):
        super().__init__()
