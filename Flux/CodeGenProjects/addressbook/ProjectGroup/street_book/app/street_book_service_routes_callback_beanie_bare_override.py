# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_routes_callback import StreetBookServiceRoutesCallback


class StreetBookServiceRoutesCallbackBeanieBareOverride(StreetBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
