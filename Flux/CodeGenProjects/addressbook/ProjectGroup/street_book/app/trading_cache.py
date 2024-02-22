from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.generated.StreetBook.strat_manager_service_base_trading_cache import \
    StratManagerServiceBaseTradingCache
from Flux.CodeGenProjects.addressbook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_trading_cache import \
    StreetBookServiceBaseTradingCache


class TradingCache(StratManagerServiceBaseTradingCache, StreetBookServiceBaseTradingCache):

    def __init__(self):
        StratManagerServiceBaseTradingCache.__init__(self)
        StreetBookServiceBaseTradingCache.__init__(self)
