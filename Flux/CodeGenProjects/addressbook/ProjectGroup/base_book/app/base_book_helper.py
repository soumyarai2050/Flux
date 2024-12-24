import logging
import threading
from typing import List, Final
import math
import sys

# project imports
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import ChoreStatusType
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager, SecurityRecord
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from FluxPythonUtils.scripts.utility_functions import parse_to_int


def chore_has_terminal_state(chore_snapshot: ChoreSnapshot) -> bool:
    return chore_snapshot.chore_status in TERMINAL_STATES + OTHER_TERMINAL_STATES


def create_symbol_overview_pre_helper(static_data: SecurityRecordManager, symbol_overview_obj: SymbolOverview):
    ticker: str = symbol_overview_obj.symbol
    security_record: SecurityRecord | None = static_data.get_security_record_from_ticker(ticker)
    err: str | None = None
    if (not symbol_overview_obj.limit_dn_px) or (math.isclose(symbol_overview_obj.limit_dn_px, 0)) or (
            not symbol_overview_obj.limit_up_px) or (math.isclose(symbol_overview_obj.limit_up_px, 0)):
        err: str = (f"Unexpected: {symbol_overview_obj.limit_up_px=}, {symbol_overview_obj.limit_dn_px=} for "
                    f"{ticker=}, in MD symbol_overview_obj, ")
        if security_record:
            err += (f"enriching from static data instead, {security_record.limit_up_px=} and "
                    f"{security_record.limit_dn_px=}")
            symbol_overview_obj.limit_up_px = security_record.limit_up_px
            symbol_overview_obj.limit_dn_px = security_record.limit_dn_px
        # else not required - handled via "if err and not security_record" section

    symbol_overview_obj.conv_px = check_n_update_conv_px(ticker, symbol_overview_obj.conv_px, security_record)

    if (not symbol_overview_obj.lot_size) or (math.isclose(symbol_overview_obj.lot_size, 0)):
        err: str = f"Unexpected! {symbol_overview_obj.lot_size=} for {ticker=}, in MD symbol_overview_obj, "
        if security_record:
            err += f"enriching from static data instead, {security_record.lot_size=}"
            symbol_overview_obj.lot_size = security_record.lot_size
        # else not required - handled via "if err and not security_record" section

    if (not symbol_overview_obj.tick_size) or (math.isclose(symbol_overview_obj.tick_size, 0)):
        debug_: str = f"Found {symbol_overview_obj.tick_size=} for {ticker=}, in MD symbol_overview_obj, "
        if security_record:
            debug_ += f"enriching from static data instead, {security_record.tick_size=}"
            symbol_overview_obj.tick_size = security_record.tick_size

    if err and not security_record:
        err += f"enriching from static data failed too, no security_record found for {ticker}"
        logging.warning(f"{err}")

    # check and add last update datetime to current time if not present [log warning]
    if not symbol_overview_obj.last_update_date_time:
        local_now: DateTime = DateTime.now(tz="Asia/Shanghai")
        symbol_overview_obj.last_update_date_time = local_now
        logging.warning(f"symbol_overview_obj.last_update_date_time not found, set to local: {local_now}")


def update_symbol_overview_pre_helper(static_data: SecurityRecordManager, stored_symbol_overview_obj: SymbolOverview,
                                      updated_symbol_overview_obj: SymbolOverview):
    # don't act if stored and updated are same - stored was cleaned in such cases
    if stored_symbol_overview_obj and stored_symbol_overview_obj.conv_px and updated_symbol_overview_obj.conv_px and (
            not math.isclose(stored_symbol_overview_obj.conv_px, updated_symbol_overview_obj.conv_px)):
        ticker = updated_symbol_overview_obj.symbol if (
            updated_symbol_overview_obj.symbol) else stored_symbol_overview_obj.symbol
        security_record: SecurityRecord | None = static_data.get_security_record_from_ticker(ticker)
        updated_symbol_overview_obj.conv_px = check_n_update_conv_px(ticker, updated_symbol_overview_obj.conv_px,
                                                                     security_record)
    return updated_symbol_overview_obj


def partial_update_symbol_overview_pre_helper(static_data: SecurityRecordManager,
                                              stored_symbol_overview_obj_json: Dict,
                                              updated_symbol_overview_obj_json: Dict):
    # don't act if stored and updated are same - stored was cleaned in such cases
    updated_conv_px = updated_symbol_overview_obj_json.get("conv_px")
    stored_conv_px = stored_symbol_overview_obj_json.get("conv_px")
    symbol_ = stored_symbol_overview_obj_json.get("symbol")
    if stored_symbol_overview_obj_json and stored_conv_px and updated_conv_px and (
            not math.isclose(stored_conv_px, updated_conv_px)):
        ticker = symbol_ if symbol_ else updated_symbol_overview_obj_json.get("symbol")
        security_record: SecurityRecord | None = static_data.get_security_record_from_ticker(ticker)
        updated_symbol_overview_obj_json["conv_px"] = check_n_update_conv_px(ticker, updated_conv_px, security_record)
    return updated_symbol_overview_obj_json


def get_bkr_from_underlying_account(underlying_account: str, inst_type: InstrumentType) -> str | None:
    bkr: str = underlying_account.split("_", 4)[2]
    return bkr


class MobileBookMutexManager:
    def __init__(self, *args):
        self._mutex_list: List[threading.Lock] = []
        for arg in args:
            try:
                mutex: threading.Lock = arg.get_lock()
            except AttributeError as attr_err:
                logging.exception(f"{arg} does not have a 'lock' attribute. Exception: {attr_err}")
            except Exception as e_:
                logging.exception(f"An error occurred while accessing 'lock' attribute on {arg}. Exception: {e_}")
            else:
                self._mutex_list.append(mutex)

    def __enter__(self):
        for mutex in self._mutex_list:
            mutex.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for mutex in self._mutex_list:
            mutex.release()


def is_chore_status_terminal(chore_status: ChoreStatusType) -> bool:
    return chore_status in TERMINAL_STATES + OTHER_TERMINAL_STATES


TERMINAL_STATES: Final[List[ChoreStatusType]] = [ChoreStatusType.OE_DOD]
OTHER_TERMINAL_STATES: Final[List[ChoreStatusType]] = [ChoreStatusType.OE_FILLED,
                                                       ChoreStatusType.OE_OVER_FILLED, ChoreStatusType.OE_OVER_CXLED]
NON_FILLED_TERMINAL_STATES: Final[List[ChoreStatusType]] = [ChoreStatusType.OE_DOD,
                                                            ChoreStatusType.OE_OVER_FILLED,
                                                            ChoreStatusType.OE_OVER_CXLED]


def check_n_update_conv_px(ticker: str, conv_px: float | None, security_record: SecurityRecord):
    if (not conv_px) or (math.isclose(conv_px, 0)):
        err: str = f"Unexpected! {conv_px=} for {ticker=}, in MD symbol_overview_obj, "
        if security_record:
            err += f"enriching from static data instead, {security_record.conv_px=}"
            conv_px = security_record.conv_px
        # else not required - handled via "if err and not security_record" section
    elif security_record and security_record.conv_px and (not math.isclose(security_record.conv_px, 0)):
        if not math.isclose(security_record.conv_px, conv_px):
            logging.error(f"static data conv_px: {security_record.conv_px} mismatches symbol_overview conv_px: "
                          f"{conv_px}, proceeding with static data conv_px for {security_record.ticker}")
            conv_px = security_record.conv_px
    return conv_px


def get_pair_strat_id_from_cmd_argv(raise_exception: bool | None = True) -> int | None:
    if len(sys.argv) > 2:
        pair_strat_id = sys.argv[1]
        return parse_to_int(pair_strat_id)
    else:
        if raise_exception:
            err_str_ = ("Can't find pair_strat_id as cmd argument, "
                        "Usage: python launch_beanie_fastapi.py <PAIR_STRAT_ID>, "
                        f"current args: {sys.argv}")
            logging.error(err_str_)
            raise Exception(err_str_)
        else:
            return None
