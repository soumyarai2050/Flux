from typing import Dict, ClassVar, Optional
import logging
from threading import Lock


class SecurityRecordManager:
    static_data: ClassVar[Optional['SecurityRecordManager']] = None
    get_instance_mutex: ClassVar[Lock] = Lock()

    def __init__(self):
        self._security_float_by_ticker: Dict[str, float] | None = dict()

    @classmethod
    def get_loaded_instance(cls, from_cache: bool = False):
        if cls.static_data is not None:
            return cls.static_data
        with cls.get_instance_mutex:
            if cls.static_data is not None:
                return cls.static_data
            else:
                cls.static_data = SecurityRecordManager()
                return cls.static_data

    def get_security_float_from_ticker(self, ticker: str):
        ticker_suffix = ticker.split("_")[-1]
        if ticker_suffix.isnumeric():
            return int(ticker_suffix) * 1_000_000
        else:
            logging.error(f"Invalid ticker: {ticker_suffix!r}, cannot get security float - must have int suffix")
