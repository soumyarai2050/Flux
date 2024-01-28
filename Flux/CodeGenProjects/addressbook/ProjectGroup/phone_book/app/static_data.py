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
                cls.static_data.load_security_float()
                return cls.static_data

    def load_security_float(self):
        self._security_float_by_ticker = {
            "CB_Sec_1": 10_000_000,
            "CB_Sec_2": 15_000_000,
            "CB_Sec_3": 18_000_000,
            "CB_Sec_4": 20_000_000,
            "CB_Sec_5": 22_000_000,
            "CB_Sec_6": 10_000_000,
            "CB_Sec_7": 15_000_000,
            "CB_Sec_8": 18_000_000,
            "CB_Sec_9": 20_000_000,
            "CB_Sec_10": 22_000_000,
            "EQT_Sec_1": 4_000_000,
            "EQT_Sec_2": 4_000_000,
            "EQT_Sec_3": 5_400_000,
            "EQT_Sec_4": 5_000_000,
            "EQT_Sec_5": 10_000_000,
            "EQT_Sec_6": 4_000_000,
            "EQT_Sec_7": 4_000_000,
            "EQT_Sec_8": 5_400_000,
            "EQT_Sec_9": 5_000_000,
            "EQT_Sec_10": 10_000_000
        }

    def get_security_float_from_ticker(self, ticker: str):
        if ticker in self._security_float_by_ticker:
            return self._security_float_by_ticker[ticker]
        logging.error(f"get_security_float_from_ticker: security float not found for ticker: {ticker}")
        return None

