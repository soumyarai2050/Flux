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
            "CB_Sec_1": 1mobile_book_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_2": 15_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_3": 18_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_4": 2mobile_book_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_5": 22_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_6": 1mobile_book_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_7": 15_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_8": 18_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_9": 2mobile_book_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "CB_Sec_1mobile_book": 22_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_1": 4_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_2": 4_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_3": 5_4mobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_4": 5_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_5": 1mobile_book_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_6": 4_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_7": 4_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_8": 5_4mobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_9": 5_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
            "EQT_Sec_1mobile_book": 1mobile_book_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book
        }

    def get_security_float_from_ticker(self, ticker: str):
        if ticker in self._security_float_by_ticker:
            return self._security_float_by_ticker[ticker]
        logging.error(f"get_security_float_from_ticker: security float not found for ticker: {ticker}")
        return None

