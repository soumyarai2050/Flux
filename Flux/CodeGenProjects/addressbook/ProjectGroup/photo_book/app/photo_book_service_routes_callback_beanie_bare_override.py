# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_routes_callback import PhotoBookServiceRoutesCallback


class PhotoBookServiceRoutesCallbackBeanieBareOverride(PhotoBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
