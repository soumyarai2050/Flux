# Standard imports
import re
from typing import List, Dict, Type
import logging

# 3rd party imports
from pydantic import BaseModel

# Project imports
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer, LogDetail, ABC


class AppLogAnalyzer(LogAnalyzer, ABC):
    def __init__(self, regex_file: str, config_yaml_dict: Dict, webclient_object,
                 raw_performance_data_model_type: Type[BaseModel],
                 log_details: List[LogDetail] | None = None,
                 log_prefix_regex_pattern_to_callable_name_dict: Dict[str, str] | None = None,
                 debug_mode: bool = False):
        super().__init__(regex_file, config_yaml_dict, webclient_object,
                         raw_performance_data_model_type, log_details=log_details,
                         log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict)
        logging.info(f"starting pair_strat log analyzer. monitoring logs: {log_details}")
        self.severity_map: Dict[str, str] = {
            "error": "Severity_ERROR",
            "critical": "Severity_CRITICAL",
            "warning": "Severity_WARNING"
        }
        self.error_patterns: Dict[str, re.Pattern] = {
            "error": re.compile(r"ERROR"),
            "critical": re.compile(r"CRITICAL"),
            "warning": re.compile(r"WARNING")
        }
        if debug_mode:
            logging.warning(f"Running log analyzer in DEBUG mode;;; log_files: {self.log_details}, "
                            f"debug_mode: {debug_mode}")
            self.error_patterns.update({
                "info": re.compile(r"INFO"),
                "debug": re.compile(r"DEBUG")
            })
            self.severity_map.update({
                "info": "Severity_INFO",
                "debug": "Severity_DEBUG"
            })

    def _get_severity(self, error_type: str) -> str:
        error_type = error_type.lower()
        if error_type in self.severity_map:
            return self.severity_map[error_type]
        else:
            return 'Severity_UNKNOWN'
