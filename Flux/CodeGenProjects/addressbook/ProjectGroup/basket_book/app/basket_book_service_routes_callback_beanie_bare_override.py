# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_routes_callback import BasketBookServiceRoutesCallback


class BasketBookServiceRoutesCallbackBeanieBareOverride(BasketBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
