# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_routes_callback import LogBookServiceRoutesCallback


class LogBookServiceRoutesCallbackCacheBareOverride(LogBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
