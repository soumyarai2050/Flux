# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.strat_manager_service_routes_callback_base_native_override import *


class StratManagerServiceRoutesCallbackCacheNativeOverride(StratManagerServiceRoutesCallbackBaseNativeOverride):
    def __init__(self):
        super().__init__()

    def get_generic_read_route(self):
        from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_beanie_routes import generic_read_http
        return generic_read_http
