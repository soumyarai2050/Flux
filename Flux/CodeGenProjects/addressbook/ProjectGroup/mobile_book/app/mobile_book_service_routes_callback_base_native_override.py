# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_routes_callback import MobileBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_service_helper import md_port
from FluxPythonUtils.scripts.general_utility_functions import except_n_log_alert


class MobileBookServiceRoutesCallbackBaseNativeOverride(MobileBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass

    def app_launch_pre(self):
        self.port = md_port

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):  # todo: impl this method for this server
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """
        pass
