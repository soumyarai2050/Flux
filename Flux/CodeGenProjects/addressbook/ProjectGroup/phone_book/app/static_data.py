from typing import Dict, ClassVar, Optional, List, Tuple
import logging
from threading import Lock
from enum import auto
from pathlib import PurePath

from fastapi_restful.enums import StrEnum

from FluxPythonUtils.scripts.utility_functions import dict_or_list_records_csv_reader
from FluxPythonUtils.scripts.model_base_utils import MsgspecBaseModel

STATIC_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)


class SecType(StrEnum):
    SecType_UNSPECIFIED = auto()
    CB = auto()
    EQT = auto()


class SecurityRecord(MsgspecBaseModel):
    sec_type: SecType | None = None
    ric: str | None = None
    secondary_ric: str | None = None
    ticker: str | None = None
    exchange_code: str | None = None
    sedol: str | None = None
    equityFloat: int | None = None
    amount_outstanding: float | None = None
    conv_px: float | None = None
    closing_px: float | None = None
    lot_size: int | None = None
    settled_tradable: bool | None = None
    executed_tradable: bool | None = None
    limit_up_px: float | None = None
    limit_dn_px: float | None = None
    tick_size: float | None = None
    figi: str | None = None


class SecurityRecordManager:
    static_data: ClassVar[Optional['SecurityRecordManager']] = None
    get_instance_mutex: ClassVar[Lock] = Lock()

    def __init__(self, from_cache: bool = False):
        self.cache_barter_ready_records_prefix: str = "barter_ready_records"
        self.barter_ready_records_by_ticker: Dict[str, SecurityRecord] = {}
        self.barter_ready_eqt_ticker_by_cb_ticker: Dict[str, str] = {}
        self.barter_ready_eqt_records_by_ric: Dict[str, SecurityRecord] = {}
        self.barter_ready_cb_records_by_sedol: Dict[str, SecurityRecord] = {}
        self.from_cache = from_cache
        if self.from_cache:
            self.load_from_cache()
        else:  # loading static data from source not supported
            raise NotImplementedError

    @classmethod
    def get_loaded_instance(cls, from_cache: bool = False):
        if cls.static_data is not None:
            return cls.static_data
        with cls.get_instance_mutex:
            if cls.static_data is not None:
                return cls.static_data
            else:
                cls.static_data = SecurityRecordManager(from_cache)
                return cls.static_data

    def load_from_cache(self):
        barter_ready_record_list: List[SecurityRecord] = \
            dict_or_list_records_csv_reader(self.cache_barter_ready_records_prefix, SecurityRecord, STATIC_DATA_DIR)  # NOQA
        barter_ready_record: SecurityRecord
        for barter_ready_record in barter_ready_record_list:
            self.barter_ready_records_by_ticker[barter_ready_record.ticker] = barter_ready_record
            if barter_ready_record.sec_type == SecType.CB:
                eqt_ticker: str = "EQT_Sec_" + barter_ready_record.ticker.split("_")[-1]
                self.barter_ready_eqt_ticker_by_cb_ticker[barter_ready_record.ticker] = eqt_ticker
                if barter_ready_record.sedol:
                    self.barter_ready_cb_records_by_sedol[barter_ready_record.sedol] = barter_ready_record
            if barter_ready_record.sec_type == SecType.EQT:
                if barter_ready_record.ric:
                    self.barter_ready_eqt_records_by_ric[barter_ready_record.ric] = barter_ready_record
                if barter_ready_record.secondary_ric:
                    self.barter_ready_eqt_records_by_ric[barter_ready_record.secondary_ric] = barter_ready_record

    def get_security_float_from_ticker(self, ticker: str):
        security_record = self.barter_ready_records_by_ticker.get(ticker)
        if security_record is not None:
            security_float: int | float | None = None
            if security_record.amount_outstanding:
                security_float = security_record.amount_outstanding
            elif security_record.equityFloat:
                security_float = security_record.equityFloat
            if security_float is not None:
                return int(security_float)
            return None
        else:
            return None

    def is_opposite_side_tradable(self, ticker: str):
        security_record = self.barter_ready_records_by_ticker.get(ticker)
        if security_record:
            if security_record.settled_tradable or security_record.executed_tradable:
                return True
        else:
            logging.error(f"is_opposite_side_tradable called with {ticker=}, for which no record found in "
                          f"barter_ready_records_by_ticker, default False will be returned")
        # all else return False
        return False

    def is_cb_ticker(self, ticker: str):
        security_record = self.barter_ready_records_by_ticker.get(ticker)
        if security_record is not None:
            if security_record.sec_type == SecType.CB:
                return True
        return False

    def is_eqt_ticker(self, ticker: str):
        security_record = self.barter_ready_records_by_ticker.get(ticker)
        if security_record is not None:
            if security_record.sec_type == SecType.EQT:
                return True
        return False

    def get_underlying_eqt_ticker_from_cb_ticker(self, ticker: str):
        return self.barter_ready_eqt_ticker_by_cb_ticker.get(ticker)

    def get_security_record_from_ticker(self, ticker: str) -> SecurityRecord | None:
        security_record: SecurityRecord
        if security_record := self.barter_ready_records_by_ticker.get(ticker):
            return security_record
        else:
            return None

    def get_exchange_from_ticker(self, ticker: str):
        security_record: SecurityRecord
        if security_record := self.barter_ready_records_by_ticker.get(ticker):
            return security_record.exchange_code
        else:
            return None

    def refresh(self) -> bool:
        self.load_from_cache()
        return False

    def get_sedol_from_ticker(self, ticker: str):
        security_record: SecurityRecord
        if security_record := self.barter_ready_records_by_ticker.get(ticker):
            return security_record.sedol
        else:
            return None

    def get_connect_n_qfii_rics_from_ticker(self, ticker: str) -> Tuple[str | None, str | None]:
        sec_rec: SecurityRecord
        if sec_rec := self.barter_ready_records_by_ticker[ticker]:
            return sec_rec.ric, sec_rec.secondary_ric
        else:
            logging.error(f"unsupported {ticker=} not found in barter_ready_records_by_ticker")
            return None, None

    def get_ric_from_ticker(self, ticker: str) -> str | None:
        sec_rec: SecurityRecord
        if sec_rec := self.barter_ready_records_by_ticker[ticker]:
            return sec_rec.ric
        else:
            logging.error(f"unsupported {ticker=} not found in barter_ready_records_by_ticker")
            return None

    def is_cn_connect_restricted(self, ticker: str, side_str: str | None = None) -> bool | None:
        return self.is_cn_connect_restricted_(ticker, side_str)

    @staticmethod
    def is_cn_connect_restricted_(self, ticker: str, side_str: str | None = None) -> bool | None:
        return False

    def is_restricted(self, ticker: str) -> bool | None:
        return False

    def get_ticker_from_sedol(self, sedol: str):
        sec_rec: SecurityRecord
        if sec_rec := self.barter_ready_cb_records_by_sedol[sedol]:
            return sec_rec.ticker
        else:
            logging.error(f"unsupported {sedol=} not found in barter_ready_records_by_ticker")
            return None

    def get_ticker_from_ric(self, ric: str):
        sec_rec: SecurityRecord
        if sec_rec := self.barter_ready_eqt_records_by_ric[ric]:
            return sec_rec.ticker
        else:
            logging.error(f"unsupported {ric=} not found in barter_ready_records_by_ticker")
            return None
