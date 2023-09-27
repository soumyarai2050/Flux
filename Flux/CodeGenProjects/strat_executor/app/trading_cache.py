from typing import Tuple
from pendulum import DateTime

from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_base_trading_cache import \
    StratManagerServiceBaseTradingCache
from Flux.CodeGenProjects.market_data.generated.StratExecutor.market_data_service_base_trading_cache import \
    MarketDataServiceBaseTradingCache


class TradingCache(StratManagerServiceBaseTradingCache, MarketDataServiceBaseTradingCache):

    def __init__(self):
        StratManagerServiceBaseTradingCache.__init__(self)
        MarketDataServiceBaseTradingCache.__init__(self)
