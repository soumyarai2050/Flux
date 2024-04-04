# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_routes_callback import EmailBookServiceRoutesCallback


class EmailBookServiceRoutesCallbackBeanieBareOverride(EmailBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass
