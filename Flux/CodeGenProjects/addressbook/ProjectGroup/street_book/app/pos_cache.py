import logging
from datetime import datetime
from pathlib import PurePath
from threading import RLock
from typing import Final, Dict, List, Tuple, ClassVar

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.model_extensions import (
    BrokerData, SecPosExtended)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import (
    NewChoreBaseModel, NewChore)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    Position, Side, Broker, BrokerBaseModel, BrokerRoute)
from FluxPythonUtils.scripts.general_utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase)


zerodha_bkr = BrokerData(eqt_qfii_account="TRADING_ACCOUNT_ZERODHA_BKR",
                         eqt_connect_account="_NOT_SUPPORTED",
                         eqt_connect_route="_NOT_SUPPORTED", eqt_qfii_route="ZERODHA",
                         cb_qfii_account="TRADING_ACCOUNT_ZERODHA_BKR", cb_qfii_route="ZERODHA")
kotak_bkr = BrokerData(eqt_qfii_account="TRADING_ACCOUNT_KOTAK_BKR", eqt_connect_account="TRADING_ACCOUNT_KOTAK_BKR",
                       eqt_connect_route="KOTAK", eqt_qfii_route="KOTAK")


def get_bkr_data(bkr: str) -> BrokerData | None:
    match bkr.lower():
        case "zerodha":
            return zerodha_bkr
        case "kotak":
            return kotak_bkr
        case unknown_bkr:
            err_str_ = f"get_bkr_data: unsupported broker: {unknown_bkr}"
            logging.error(err_str_)
            return None


class PosCache:
    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()

    def __init__(self, static_data: SecurityRecordManager):
        # sanity test constants
        self.BROKER = "ZERODHA"
        self.TRADING_ACCOUNT = "TRADING_ACCOUNT_ZERODHA_BKR"
        self.TRADING_EXCHANGE = "ZERODHA"

        self.orig_sod_n_intraday_pos_dict = None
        self.market = Market(MarketID.IN)
        self._static_data: Final[SecurityRecordManager] = static_data
        self.symbols_n_sec_id_source_dict: Dict[str, str] = {}
        self.sec_positions_header_str = (
            "ticker, bkr, pos_disable, type, available, allocated, consumed, bot, sld, plan_consumed, acquire, "
            "incurred, carry, mplan, priority, premium_percentage")
        # helps prevent reverse bartering on intraday positions where security level constraints exists
        self.no_executed_tradable_symbol_replenishing_side_dict: Dict[str, Side] = {}  # supplied by executor
        # current plan bartering symbol and side dict - helps block intraday non recovery position updates
        self.bartering_symbol_side_dict: Dict[str, Side] = {}  # supplied by executor
        self._sec_positions_dict: Dict[str, List[SecPosExtended]] = dict()
        self._pos_cache_lock: RLock = RLock()
        self._local_open_chores: int = 0
        self._started: bool = False  # enables plan to control if trigger init required
        self._start_lock: RLock = RLock()
        self.eqt_fallback_broker: str = "KOTAK"
        self.eqt_fallback_route: BrokerRoute = BrokerRoute.BR_QFII
        self.cb_fallback_broker: str = "ZERODHA"
        self.cb_fallback_route: BrokerRoute = BrokerRoute.BR_QFII

    def started(self):
        return self._started

    def extract_availability_list(self, new_ord: NewChoreBaseModel) -> Tuple[bool, List[SecPosExtended]]:
        """
        only for use by chore creators - position back fillers should not use extract_availability instead
        allows acquiring optimal position(s) based on chore with ticker/RIC
        thread safe - underlying _extract_availability takes position lock
        @@@ TODO: Needs generalization for non EQT-CB / non QFII-Connect Chores
        Args:
            new_ord:
        Returns: Tuple [is_available, List[sec_pos_extended]]
        """
        sec_pos_extended: SecPosExtended = SecPosExtended.from_kwargs(
            broker="ZERODHA", bkr_data=get_bkr_data("ZERODHA"), security=new_ord.security, positions=[])
        sec_pos_extended.bartering_account = self.TRADING_ACCOUNT
        sec_pos_extended.bartering_route = self.TRADING_EXCHANGE
        return True, [sec_pos_extended]

    def extract_availability(self, new_ord: NewChore | NewChoreBaseModel) -> Tuple[bool, SecPosExtended | None]:
        sec_pos_extended: SecPosExtended = SecPosExtended.from_kwargs(
            broker="ZERODHA", bkr_data=get_bkr_data("ZERODHA"), security=new_ord.security, positions=[])
        sec_pos_extended.bartering_account = self.TRADING_ACCOUNT
        sec_pos_extended.bartering_route = self.TRADING_EXCHANGE
        return True, sec_pos_extended

    def return_availability(self, ticker: str, sec_pos: SecPosExtended) -> bool:
        if not self._started:
            logging.error(f"returning sec_pos failed for {ticker} - self._started id false;;;{sec_pos}")
            return False
        return True

    def start(self, brokers: List[BrokerBaseModel], sod_n_intraday_pos_dict: Dict[str, Dict[str, List[Position]]],
              bartering_symbol_side_dict: Dict[str, str], symbols_n_sec_id_source_dict: Dict[str, str],
              no_executed_tradable_symbol_replenishing_side_dict: Dict[str, Side], config_dict: Dict) -> bool:
        with self._start_lock:
            if self.started():
                return self._started
            else:
                self.bartering_symbol_side_dict = bartering_symbol_side_dict
                self.symbols_n_sec_id_source_dict = symbols_n_sec_id_source_dict
                self.no_executed_tradable_symbol_replenishing_side_dict = \
                    no_executed_tradable_symbol_replenishing_side_dict
            self._started = True
            return self._started

    def update_sec_limits(self, brokers: List[Broker | BrokerBaseModel]):
        if not self._started:
            logging.warning("update_sec_limits call without starting pos_cache - ignoring the call")
            return


if __name__ == "__main__":
    def main():
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        datetime_str: str = datetime.now().strftime("%Y%m%d")
        configure_logger("debug", str(log_dir), f"{__file__}_{datetime_str}.log")


    main()
