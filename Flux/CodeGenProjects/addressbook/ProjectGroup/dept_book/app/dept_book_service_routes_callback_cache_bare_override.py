# project imports
from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_routes_callback import DeptBookServiceRoutesCallback


class DeptBookServiceRoutesCallbackCacheBareOverride(DeptBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
