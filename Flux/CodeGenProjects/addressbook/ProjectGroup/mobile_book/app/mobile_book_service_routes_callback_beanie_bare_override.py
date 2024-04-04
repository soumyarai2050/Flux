# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_routes_callback import MobileBookServiceRoutesCallback


class MobileBookServiceRoutesCallbackBeanieBareOverride(MobileBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
