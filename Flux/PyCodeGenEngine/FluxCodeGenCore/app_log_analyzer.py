# Standard imports
import re
from typing import List, Dict, Type
import logging

# Project imports
from FluxPythonUtils.log_analyzer.tail_executor import TailExecutor, LogDetail, ABC


class AppTailExecutor(TailExecutor, ABC):
    severity_map: Dict[str, str] = {
        "error": "Severity_ERROR",
        "critical": "Severity_CRITICAL",
        "warning": "Severity_WARNING"
    }

    def __init__(self, log_detail: LogDetail, regex_file_dir_path: str, config_yaml_dict: Dict,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 debug_mode: bool = False):
        super().__init__(log_detail, regex_file_dir_path, config_yaml_dict,
                         log_prefix_regex_pattern_to_callable_name_dict)
        self.error_patterns: Dict[str, re.Pattern] = {
            "error": re.compile(r"ER(R)?OR"),
            "critical": re.compile(r"CRIT(ICAL)?"),
            "warning": re.compile(r"WARN(ING)?")
        }
        if debug_mode:
            self.error_patterns.update({
                "info": re.compile(r"INFO"),
                "debug": re.compile(r"DEB(U)?G")
            })
            self.severity_map.update({
                "info": "Severity_INFO",
                "debug": "Severity_DEBUG"
            })

    @classmethod
    def get_severity(cls, error_type: str) -> str:
        error_type = error_type.lower()
        if error_type in cls.severity_map:
            return cls.severity_map[error_type]
        else:
            return 'Severity_UNKNOWN'
