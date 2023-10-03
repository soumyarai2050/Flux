from typing import Tuple
from pendulum import DateTime

from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_base_trading_cache import \
    StratManagerServiceBaseTradingCache
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_base_trading_cache import \
    StratExecutorServiceBaseTradingCache


class TradingCache(StratManagerServiceBaseTradingCache, StratExecutorServiceBaseTradingCache):

    def __init__(self):
        StratManagerServiceBaseTradingCache.__init__(self)
        StratExecutorServiceBaseTradingCache.__init__(self)
