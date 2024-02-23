from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_trading_cache import \
    EmailBookServiceBaseTradingCache
from Flux.CodeGenProjects.addressbook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_trading_cache import \
    StreetBookServiceBaseTradingCache


class TradingCache(EmailBookServiceBaseTradingCache, StreetBookServiceBaseTradingCache):

    def __init__(self):
        EmailBookServiceBaseTradingCache.__init__(self)
        StreetBookServiceBaseTradingCache.__init__(self)
