# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.post_book.generated.FastApi.post_book_service_routes_callback import PostBookServiceRoutesCallback


class PostBookServiceRoutesCallbackBeanieBareOverride(PostBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
