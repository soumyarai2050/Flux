from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_bartering_cache import \
    EmailBookServiceBaseBarteringCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_base_bartering_cache import BasketBookServiceBaseBarteringCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_cache import BaseBarteringCache


class BasketBarteringCache(BaseBarteringCache, BasketBookServiceBaseBarteringCache, EmailBookServiceBaseBarteringCache):

    def __init__(self):
        BaseBarteringCache.__init__(self)
        BasketBookServiceBaseBarteringCache.__init__(self)
        EmailBookServiceBaseBarteringCache.__init__(self)
