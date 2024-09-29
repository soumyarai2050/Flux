from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_bartering_cache import \
    EmailBookServiceBaseBarteringCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_bartering_cache import \
    StreetBookServiceBaseBarteringCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_cache import BaseBarteringCache


class BarteringCache(BaseBarteringCache, EmailBookServiceBaseBarteringCache, StreetBookServiceBaseBarteringCache):

    def __init__(self):
        BaseBarteringCache.__init__(self)
        EmailBookServiceBaseBarteringCache.__init__(self)
        StreetBookServiceBaseBarteringCache.__init__(self)
