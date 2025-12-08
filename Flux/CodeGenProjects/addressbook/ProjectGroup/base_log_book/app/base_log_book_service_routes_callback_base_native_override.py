# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.base_log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.aggregate import *
from FluxPythonUtils.scripts.service import Service


# standard imports
from datetime import datetime

# We once faced this issue - keeping this link here for future refrence - not relevant now
# https://pythonspeed.com/articles/python-multiprocessing/

class BaseLogBookServiceRoutesCallbackBaseNativeOverride(Service):
    log_seperator: str = ';;;'
    max_str_size_in_bytes: int = 2048
    severity_map: Dict[str, Severity] = {
        "debug": Severity.Severity_DEBUG,
        "info": Severity.Severity_INFO,
        "error": Severity.Severity_ERROR,
        "critical": Severity.Severity_CRITICAL,
        "warning": Severity.Severity_WARNING,
        "exception": Severity.Severity_ERROR
    }
    severity_to_log_lvl_map: Dict[Severity, str] = {
        Severity.Severity_DEBUG: "debug",
        Severity.Severity_INFO: "info",
        Severity.Severity_ERROR: "error",
        Severity.Severity_CRITICAL: "critical",
        Severity.Severity_WARNING: "warning"
    }
    datetime_str: str = datetime.now().strftime("%Y%m%d")

    def __init__(self):
        super().__init__()

    def _is_str_limit_breached(self, text: str) -> bool:
        if len(text.encode("utf-8")) > BaseLogBookServiceRoutesCallbackBaseNativeOverride.max_str_size_in_bytes:
            return True
        return False

    def _truncate_str(self, text: str) -> str:
        if self._is_str_limit_breached(text):
            text = text.encode("utf-8")[:BaseLogBookServiceRoutesCallbackBaseNativeOverride.max_str_size_in_bytes].decode()
            text += f"...check the component file to see the entire log"
        return text

    def _create_alert(self, message: str, level: str, source_file: str) -> Tuple[Severity, str, str]:
        alert_brief_n_detail_lists: List[str] = (
            message.split(BaseLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator, 1))
        if len(alert_brief_n_detail_lists) == 2:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = alert_brief_n_detail_lists[1]
        else:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = ". ".join(alert_brief_n_detail_lists[1:])

        alert_brief = self._truncate_str(alert_brief).strip()
        alert_details = self._truncate_str(alert_details).strip()
        severity: Severity = BaseLogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get(level.lower())
        return severity, alert_brief, alert_details
