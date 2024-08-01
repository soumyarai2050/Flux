import logging
import os
from threading import Thread
import math
import subprocess
import stat
import random
import ctypes

os.environ["DBType"] = "beanie"

from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.chore_check import ChoreControl
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_data_manager import BarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.strat_cache import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import get_bartering_link, BarteringLinkBase, is_test_run, \
    config_dict
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import \
    get_consumable_participation_qty_http, get_symbol_side_key, \
    get_strat_brief_log_key, create_stop_md_script, executor_config_yaml_dict, MobileBookMutexManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    create_md_shell_script, MDShellEnvData, email_book_service_http_client, guaranteed_call_pair_strat_client)
from FluxPythonUtils.scripts.utility_functions import clear_semaphore, perf_benchmark_sync_callable
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.Pydentic.post_book_service_model_imports import (
    IsPortfolioLimitsBreached)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_helper import (
    post_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.mobile_book_cache import (
    MobileBookContainer, TopOfBook, MarketDepth, LastBarter, MarketBarterVolume, add_container_obj_for_symbol, get_mobile_book_container)


class MobileBookContainerCache(BaseModel):
    leg_1_mobile_book_container: MobileBookContainer
    leg_2_mobile_book_container: MobileBookContainer
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class StreetBook:
    # Query Callables
    underlying_get_aggressive_market_depths_query_http: Callable[..., Any] | None = None
    underlying_handle_strat_activate_query_http: Callable[..., Any] | None = None

    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    asyncio_loop: asyncio.AbstractEventLoop
    mobile_book_provider: ctypes.CDLL

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes import (
            underlying_get_market_depths_query_http, underlying_handle_strat_activate_query_http)
        cls.underlying_get_aggressive_market_depths_query_http = underlying_get_market_depths_query_http
        cls.underlying_handle_strat_activate_query_http = underlying_handle_strat_activate_query_http

    @staticmethod
    def executor_trigger(bartering_data_manager_: BarteringDataManager, strat_cache: StratCache,
                         mobile_book_container_cache: MobileBookContainerCache):
        street_book: StreetBook = StreetBook(bartering_data_manager_, strat_cache, mobile_book_container_cache)
        street_book_thread = Thread(target=street_book.run, daemon=True).start()
        return street_book, street_book_thread

    """ 1 instance = 1 thread = 1 pair strat"""

    def __init__(self, bartering_data_manager_: BarteringDataManager, strat_cache: StratCache,
                 mobile_book_container_cache: MobileBookContainerCache):
        # prevents consuming any market data older than current time
        self.is_dev_env = True
        self.allow_multiple_open_chores_per_strat: Final[bool] = allow_multiple_open_chores_per_strat \
            if (allow_multiple_open_chores_per_strat :=
                executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat")) is not None else False
        self.leg1_consumed_depth_time: DateTime = DateTime.utcnow()
        self.leg2_consumed_depth_time: DateTime = DateTime.utcnow()
        self.leg1_consumed_depth: MarketDepth | None = None
        self.leg2_consumed_depth: MarketDepth | None = None

        self.pair_street_book_id: str | None = None
        self.is_test_run: bool = is_test_run
        self.is_sanity_test_run: bool = config_dict.get("is_sanity_test_run")

        self.bartering_data_manager: BarteringDataManager = bartering_data_manager_
        self.strat_cache: StratCache = strat_cache
        self.mobile_book_container_cache: MobileBookContainerCache = mobile_book_container_cache
        self.leg1_fx: float | None = None

        self._system_control_update_date_time: DateTime | None = None
        self._strat_brief_update_date_time: DateTime | None = None
        self._chore_snapshots_update_date_time: DateTime | None = None
        self._chore_journals_update_date_time: DateTime | None = None
        self._fills_journals_update_date_time: DateTime | None = None
        self._chore_limits_update_date_time: DateTime | None = None
        self._new_chores_update_date_time: DateTime | None = None
        self._new_chores_processed_slice: int = 0
        self._cancel_chores_update_date_time: DateTime | None = None
        self._cancel_chores_processed_slice: int = 0
        self._top_of_books_update_date_time: DateTime | None = None
        self._tob_leg1_update_date_time: DateTime | None = None
        self._tob_leg2_update_date_time: DateTime | None = None
        self._processed_tob_date_time: DateTime | None = None

        self.strat_limit: StratLimits | StratLimitsBaseModel | None = None
        self.last_chore_timestamp: DateTime | None = None

        self.leg1_notional: float = 0
        self.leg2_notional: float = 0

        self.chore_pase_seconds = 0
        # internal rejects to use:  -ive internal_reject_count + current date time as chore id
        self.internal_reject_count = 0
        # 1-time prepare param used by update_aggressive_market_depths_in_cache call for this strat [init on first use]
        self.aggressive_symbol_side_tuples_dict: Dict[str, List[Tuple[str, str]]] = {}
        StreetBook.initialize_underlying_http_routes()  # Calling underlying instances init

        # attributes to be set in run method
        self.leg_1_symbol: str | None = None
        self.leg_1_side: Side | None = None
        self.leg_2_symbol: str | None = None
        self.leg_2_side: Side | None = None

    def check_chore_eligibility(self, side: Side, check_notional: float) -> bool:
        strat_brief, self._strat_brief_update_date_time = \
            self.strat_cache.get_strat_brief(self._strat_brief_update_date_time)
        if side == Side.BUY:
            if strat_brief.pair_buy_side_bartering_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False
        else:
            if strat_brief.pair_sell_side_bartering_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False

    def init_aggressive_symbol_side_tuples_dict(self) -> bool:
        if self.aggressive_symbol_side_tuples_dict:
            logging.warning("init_aggressive_symbol_side_tuples_dict invoked on pre-initialized "
                            "aggressive_symbol_side_tuples_dict")
            return True  # its pre-initialized, not ideal, but not wrong either

        # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
        pair_strat: PairStrat = self._get_latest_pair_strat()
        if pair_strat is None:
            logging.error("init_aggressive_symbol_side_tuples_dict invoked but no pair strat found in cache")
            return False

        leg1 = pair_strat.pair_strat_params.strat_leg1
        leg1_sec: str = leg1.sec.sec_id
        leg1_aggressive_side_str: str = "ASK" if leg1.side == Side.BUY else "BID"
        leg2 = pair_strat.pair_strat_params.strat_leg2
        leg2_sec: str = leg2.sec.sec_id
        leg2_aggressive_side_str: str = "ASK" if leg2.side == Side.BUY else "BID"

        self.aggressive_symbol_side_tuples_dict = {"symbol_side_tuple_list": [(leg1_sec, leg1_aggressive_side_str),
                                                                              (leg2_sec, leg2_aggressive_side_str)]}
        return True

    def extract_strat_specific_legs_from_tobs(self, pair_strat, top_of_books) -> Tuple[TopOfBook | None,
                                                                                       TopOfBook | None]:
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        leg1_tob, leg2_tob = self.extract_legs_from_tobs(pair_strat, top_of_books)
        # Note: Not taking tob mutex since symbol never changes in tob
        if leg1_tob is not None and self.strat_cache.leg1_bartering_symbol is None:
            logging.debug(f"ignoring ticker: {leg1_tob.symbol = } not found in strat_cache, "
                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
            leg1_tob = None
        if leg2_tob is not None and self.strat_cache.leg2_bartering_symbol is None:
            logging.debug(f"ignoring ticker: {leg2_tob.symbol = } not found in strat_cache, "
                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
            leg2_tob = None
        return leg1_tob, leg2_tob

    @staticmethod
    def _get_tob_str(tob: TopOfBook) -> str:
        with MobileBookMutexManager(StreetBook.mobile_book_provider, tob):
            return str(tob)

    @staticmethod
    def extract_legs_from_tobs(pair_strat, top_of_books) -> Tuple[TopOfBook | None, TopOfBook | None]:
        leg1_tob: TopOfBook | None = None
        leg2_tob: TopOfBook | None = None
        error = False
        # Note: Not taking tob mutex since symbol never changes in tob
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[0].symbol:
            leg1_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[1].symbol:
                    leg2_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol = }, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg2.sec.sec_id}, pair_strat_key: "
                                  f" {get_pair_strat_log_key(pair_strat)};;; top_of_book: "
                                  f"{StreetBook._get_tob_str(top_of_books[1])}")
                    error = True
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[0].symbol:
            leg2_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[1].symbol:
                    leg1_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol = }, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg1.sec.sec_id} pair_strat_key: "
                                  f"{get_pair_strat_log_key(pair_strat)};;; top_of_book: "
                                  f"{StreetBook._get_tob_str(top_of_books[1])}")
                    error = True
        else:
            logging.error(f"unexpected security found in top_of_books[0]: {top_of_books[0].symbol = }, "
                          f"expected either: {pair_strat.pair_strat_params.strat_leg1.sec.sec_id} or "
                          f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id} in pair_strat_key: "
                          f"{get_pair_strat_log_key(pair_strat)};;; top_of_book: "
                          f"{StreetBook._get_tob_str(top_of_books[1])}")
            error = True
        if error:
            return None, None
        else:
            return leg1_tob, leg2_tob

    def bartering_link_internal_chore_state_update(
            self, chore_event: ChoreEventType, chore_id: str, side: Side | None = None,
            bartering_sec_id: str | None = None, system_sec_id: str | None = None,
            underlying_account: str | None = None, msg: str | None = None):
        # coro needs public method
        run_coro = self.bartering_link.internal_chore_state_update(chore_event, chore_id, side, bartering_sec_id,
                                                                 system_sec_id, underlying_account, msg)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)
        # block for start_executor_server task to finish
        try:
            return future.result()
        except Exception as e:
            logging.exception(f"_internal_reject_new_chore failed with exception: {e}")

    def internal_reject_new_chore(self, new_chore: NewChoreBaseModel, reject_msg: str):
        self.internal_reject_count += 1
        internal_reject_chore_id: str = str(self.internal_reject_count * -1) + str(DateTime.utcnow())
        self.bartering_link_internal_chore_state_update(
            ChoreEventType.OE_INT_REJ, internal_reject_chore_id, new_chore.side, None,
            new_chore.security.sec_id, None, reject_msg)

    def set_unack(self, system_symbol: str, unack_state: bool):
        if self.strat_cache._pair_strat.pair_strat_params.strat_leg1.sec.sec_id == system_symbol:
            self.strat_cache.set_has_unack_leg1(unack_state)
        if self.strat_cache._pair_strat.pair_strat_params.strat_leg2.sec.sec_id == system_symbol:
            self.strat_cache.set_has_unack_leg2(unack_state)

    def check_unack(self, system_symbol: str):
        pair_strat, _ = self.strat_cache.get_pair_strat()
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == system_symbol:
            if self.strat_cache.has_unack_leg1():
                return True
            # else not required, final return False covers this
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == system_symbol:
            if self.strat_cache.has_unack_leg2():
                return True
            # else not required, final return False covers this
        else:
            logging.error(f"check_unack: unknown {system_symbol = }, check force failed for strat_cache: "
                          f"{self.strat_cache.get_key()}, "
                          f"pair_strat_key_key: {get_pair_strat_log_key(pair_strat)}")
        return False

    def place_new_chore(self, top_of_book: TopOfBookBaseModel, strat_brief: StratBriefBaseModel,
                        chore_limits: ChoreLimitsBaseModel, pair_strat: PairStrat, px: float, usd_px: float, qty: int,
                        side: Side, system_symbol: str, err_dict: Dict[str, any] | None = None,
                        is_eqt: bool | None = None, check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS) -> int:
        ret_val: int
        if err_dict is None:
            err_dict = dict()
        try:
            bartering_symbol, account, exchange = self.strat_cache.get_metadata(system_symbol)
            if bartering_symbol is None or account is None or exchange is None:
                logging.error(f"unable to send chore, couldn't find metadata for: symbol {system_symbol}, meta-data:"
                              f" {bartering_symbol = }, {account = }, {exchange = } "
                              f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL

            # block new chore if any prior unack chore exist
            if self.check_unack(system_symbol):
                error_msg: str = f"past chore on {system_symbol = } is in unack state, dropping chore with " \
                                 f"{px = }, {qty = }, {side = }, symbol_side_key: " \
                                 f"{get_symbol_side_key([(system_symbol, side)])}"
                logging.error(error_msg)
                return ChoreControl.ORDER_CONTROL_CHECK_UNACK_FAIL

            if ChoreControl.ORDER_CONTROL_SUCCESS == (ret_val := self.check_new_chore(top_of_book, strat_brief,
                                                                                      chore_limits, pair_strat,
                                                                                      px, usd_px, qty, side,
                                                                                      system_symbol, account,
                                                                                      exchange, err_dict, check_mask)):
                # check and block chore if strat not in activ state [second fail-safe-check]
                # If pair_strat is not active, don't act, just return [check MD state and take action if required]
                pair_strat = self._get_latest_pair_strat()
                if pair_strat.strat_state != StratState.StratState_ACTIVE or self._is_outside_bartering_hours():
                    logging.error("Secondary Block place chore - strat not in activ state or outside market hours")
                    return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

                # set unack for subsequent chores - this symbol to be blocked until this chore goes through
                self.set_unack(system_symbol, True)
                if not self.bartering_link_place_new_chore(px, qty, side, bartering_symbol, system_symbol, account,
                                                         exchange):
                    # reset unack for subsequent chores to go through - this chore did fail to go through
                    self.set_unack(system_symbol, False)
                    return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:
                    return ChoreControl.ORDER_CONTROL_SUCCESS  # chore sent out successfully
            else:
                return ret_val
        except Exception as e:
            logging.exception(f"place_new_chore failed for: {system_symbol} px-qty-side: {px}-{qty}-{side}, with "
                              f"exception: {e}")
            return ChoreControl.ORDER_CONTROL_EXCEPTION_FAIL
        finally:
            pass

    def bartering_link_place_new_chore(self, px, qty, side, bartering_symbol, system_symbol, account, exchange):
        run_coro = self.bartering_link.place_new_chore(px, qty, side, bartering_symbol, system_symbol,
                                                     account, exchange)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for task to finish
        try:
            chore_sent_status = future.result()
            return chore_sent_status
        except Exception as e:
            logging.exception(f"bartering_link_place_new_chore failed for {system_symbol = } "
                              f"px-qty-side: {px}-{qty}-{side} with exception;;;{e}")
            return False

    def check_consumable_concentration(self, strat_brief: StratBrief | StratBriefBaseModel,
                                       bartering_brief: PairSideBarteringBrief, qty: int,
                                       side_str: str) -> bool:
        if bartering_brief.consumable_concentration - qty < 0:
            if bartering_brief.consumable_concentration == 0:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {side_str} chore, unexpected: consumable_concentration found 0! "
                              f"for start_cache: {self.strat_cache.get_key()}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
            else:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {side_str} chore, not enough consumable_concentration: "
                              f"{strat_brief.pair_sell_side_bartering_brief.consumable_concentration} needed: {qty = }, "
                              f"for start_cache: {self.strat_cache.get_key()}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
            return False
        else:
            return True

    def check_strat_limits(self, strat_brief: StratBriefBaseModel,
                           px: float, usd_px: float, qty: int, side: Side,
                           chore_usd_notional: float, system_symbol: str, err_dict: Dict[str, any]):
        checks_passed = ChoreControl.ORDER_CONTROL_SUCCESS
        symbol_overview: SymbolOverviewBaseModel | None = None
        symbol_overview_tuple = \
            self.strat_cache.get_symbol_overview_from_symbol(system_symbol)
        if symbol_overview_tuple:
            symbol_overview, _ = symbol_overview_tuple
            if not symbol_overview:
                logging.error(f"blocked generated {side} chore, symbol_overview missing for {system_symbol = }, "
                              f"for strat_cache: {self.strat_cache.get_key()}, limit up/down check needs "
                              f"symbol_overview, strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL
            elif not symbol_overview.limit_dn_px or not symbol_overview.limit_up_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked symbol_side_key: {get_symbol_side_key([(system_symbol, side)])} chore, "
                              f"limit up/down px not available limit-dn px: {symbol_overview.limit_dn_px}, found "
                              f"{px = }, {symbol_overview.limit_up_px = }")
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL
            # else all good to continue limit checks

        if side == Side.SELL:
            # max_open_chores_per_side check
            if strat_brief.pair_sell_side_bartering_brief.consumable_open_chores < 0:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated SELL chore, not enough consumable_open_chores: "
                              f"{strat_brief.pair_sell_side_bartering_brief.consumable_open_chores} for strat_cache: "
                              f"{self.strat_cache.get_key()}, strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL

            # max_open_single_leg_notional check
            if chore_usd_notional > strat_brief.pair_sell_side_bartering_brief.consumable_open_notional:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked symbol_side_key: {get_symbol_side_key([(system_symbol, side)])} chore, "
                              f"breaches available consumable open notional, expected less than: "
                              f"{strat_brief.pair_sell_side_bartering_brief.consumable_open_notional}, chore needs:"
                              f" {chore_usd_notional}")
                checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL

            # covers: max single_leg notional, max open cb notional & max net filled notional
            # ( TODO Urgent: validate and add this description to log detail section ;;;)
            # Checking max_single_leg_notional
            if chore_usd_notional > strat_brief.pair_sell_side_bartering_brief.consumable_notional:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated SELL chore, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_sell_side_bartering_brief.consumable_notional}, chore needs: "
                              f"{chore_usd_notional} - the check covers: max cb notional, max open cb notional, "
                              f"max net filled notional, for start_cache: {self.strat_cache.get_key()}, "
                              f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL

            # Checking max_concentration
            if not self.check_consumable_concentration(strat_brief, strat_brief.pair_sell_side_bartering_brief, qty,
                                                       "SELL"):
                checks_passed |= ChoreControl.ORDER_CONTROL_MAX_CONCENTRATION_FAIL

            # limit down - TODO : Important : Upgrade this to support bartering at Limit Dn within the limit Dn limit
            if px < symbol_overview.limit_dn_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated SELL chore, limit down bartering not allowed on day-1, px "
                              f"expected higher than limit-dn px: {symbol_overview.limit_dn_px}, found {px = } for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief_log_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_LIMIT_DOWN_FAIL

        elif side == Side.BUY:
            # max_open_chores_per_side check
            if strat_brief.pair_buy_side_bartering_brief.consumable_open_chores < 0:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated BUY chore, not enough consumable_open_chores: "
                              f"{strat_brief.pair_buy_side_bartering_brief.consumable_open_chores} for strat_cache: "
                              f"{self.strat_cache.get_key()}, strat_brief: {get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL

            # max_open_single_leg_notional check
            if chore_usd_notional > strat_brief.pair_buy_side_bartering_brief.consumable_open_notional:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked symbol_side_key: {get_symbol_side_key([(system_symbol, side)])} chore, "
                              f"breaches available consumable open notional, chore needs: "
                              f"{strat_brief.pair_buy_side_bartering_brief.consumable_open_notional}, expected less than:"
                              f" {chore_usd_notional}")
                checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL

            if chore_usd_notional > strat_brief.pair_buy_side_bartering_brief.consumable_notional:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated BUY chore, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_buy_side_bartering_brief.consumable_notional}, chore needs: "
                              f"{chore_usd_notional} for strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL
            # Checking max_concentration
            if not self.check_consumable_concentration(strat_brief, strat_brief.pair_buy_side_bartering_brief, qty,
                                                       "BUY"):
                checks_passed |= ChoreControl.ORDER_CONTROL_MAX_CONCENTRATION_FAIL

            # Buy - not allowed more than limit up px
            # limit up - TODO : Important : Upgrade this to support bartering at Limit Up within the limit Up limit
            if px > symbol_overview.limit_up_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated BUY chore, limit up bartering not allowed on day-1, px "
                              f"expected lower than limit-up px: {symbol_overview.limit_up_px}, found {px = } for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_LIMIT_UP_FAIL

        consumable_participation_qty: int = get_consumable_participation_qty_http(
            system_symbol, side, self.strat_limit.market_barter_volume_participation.applicable_period_seconds,
            self.strat_limit.market_barter_volume_participation.max_participation_rate, StreetBook.asyncio_loop)
        if consumable_participation_qty is not None and consumable_participation_qty != 0:
            if consumable_participation_qty - qty < 0:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated chore, not enough consumable_participation_qty available, "
                              f"expected higher than chore {qty = }, found {consumable_participation_qty = } for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}, {system_symbol = }, {side = }, "
                              f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL
                if (consumable_participation_qty * usd_px) > self.strat_limit.min_chore_notional:
                    err_dict["consumable_participation_qty"] = f"{consumable_participation_qty}"
            # else check passed - no action
        else:
            strat_brief_key: str = get_strat_brief_log_key(strat_brief)
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"Received unusable {consumable_participation_qty = } from "
                          f"get_consumable_participation_qty_http, {system_symbol = }, {side = }, "
                          f"applicable_period_seconds: "
                          f"{self.strat_limit.market_barter_volume_participation.applicable_period_seconds}, "
                          f"strat_brief_key: {strat_brief_key}, check failed")
            checks_passed |= ChoreControl.ORDER_CONTROL_UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL
        # checking max_net_filled_notional
        if chore_usd_notional > strat_brief.consumable_nett_filled_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, not enough consumable_nett_filled_notional available, "
                          f"remaining {strat_brief.consumable_nett_filled_notional = }, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL

        return checks_passed

    def _get_tob_last_barter_px(self, top_of_book: TopOfBook, side: Side) -> float | None:
        with MobileBookMutexManager(self.mobile_book_provider, top_of_book):
            if top_of_book.last_barter is None or math.isclose(top_of_book.last_barter.px, 0):
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated chore, symbol: {top_of_book.symbol}, {side = } as "
                              f"top_of_book.last_barter.px is none or 0, symbol_side_key: "
                              f" {get_symbol_side_key([(top_of_book.symbol, side)])}")
                return None
            return top_of_book.last_barter.px

    def get_breach_threshold_px(self, top_of_book: TopOfBook, chore_limits: ChoreLimitsBaseModel,
                                side: Side, system_symbol: str) -> float | None:
        # TODO important - check and change reference px in cases where last px is not available
        last_barter_px = self._get_tob_last_barter_px(top_of_book, side)
        if last_barter_px is None:
            return None     # error logged in _get_tob_last_barter_px

        if side != Side.BUY and side != Side.SELL:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated unsupported side chore, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return None  # None return blocks the chore from going further

        return self._get_breach_threshold_px(top_of_book, chore_limits, side, system_symbol,
                                             last_barter_px)

    def _get_aggressive_tob_ask_quote_px(self, tob: TopOfBook, side: Side) -> int | None:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if not tob.ask_quote or not tob.ask_quote.px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated BUY chore, {tob.symbol = }, {side = } as aggressive_quote"
                              f" is not found or has no px, symbol_side_key: "
                              f"{get_symbol_side_key([(tob.symbol, side)])};;;aggressive_quote: {tob.ask_quote}")
                return None  # None return blocks the chore from going further
            else:
                return tob.ask_quote.px

    def _get_aggressive_tob_bid_quote_px(self, tob: TopOfBook, side: Side) -> int | None:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if not tob.bid_quote or not tob.bid_quote.px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated SELL chore, {tob.symbol = }, {side = } as aggressive_quote"
                              f" is not found or has no px, symbol_side_key: "
                              f"{get_symbol_side_key([(tob.symbol, side)])};;; aggressive_quote: {tob.bid_quote}")
                return None  # None return blocks the chore from going further
            else:
                return tob.bid_quote.px

    def _get_px_by_max_level(self, system_symbol: str, side: Side, chore_limits: ChoreLimitsBaseModel) -> float | None:
        px_by_max_level: float = 0

        if system_symbol == self.leg_1_symbol:
            mobile_book_container = self.mobile_book_container_cache.leg_1_mobile_book_container
        else:
            mobile_book_container = self.mobile_book_container_cache.leg_2_mobile_book_container

        if chore_limits.max_px_levels == 0:
            if side == Side.SELL:
                market_depths = mobile_book_container.get_ask_market_depths()
            else:
                market_depths = mobile_book_container.get_bid_market_depths()

            market_depth = market_depths[0]
            if market_depth is not None:
                px_by_max_level = market_depth.px

        else:
            max_px_level: int = chore_limits.max_px_levels
            if max_px_level > 0:
                aggressive_side = Side.BUY if side == Side.SELL else Side.SELL
            else:
                # when chore_limits.max_px_levels < 0, aggressive side is same as current side
                aggressive_side = side
                max_px_level = abs(max_px_level)

            # getting aggressive market depth
            if aggressive_side == Side.SELL:
                market_depths = mobile_book_container.get_ask_market_depths()
            else:
                market_depths = mobile_book_container.get_bid_market_depths()

            for lvl in range(max_px_level - 1, -1, -1):
                # lvl reducing from max_px_level to 0
                market_depth = market_depths[lvl]
                if market_depth is not None:
                    px_by_max_level = market_depth.px
                    break

        if math.isclose(px_by_max_level, 0):
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, {system_symbol = }, {side = }, unable to find valid px"
                          f" based on {chore_limits.max_px_levels = } limit from available depths, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])};;;"
                          f"depths: {[str(market_depth) for market_depth in market_depths]}")
            return None
        return px_by_max_level

    def _get_breach_threshold_px(self, top_of_book: TopOfBook, chore_limits: ChoreLimitsBaseModel,
                                 side: Side, system_symbol: str, last_barter_px: float) -> float | None:

        px_by_max_level = self._get_px_by_max_level(system_symbol, side, chore_limits)
        if px_by_max_level is None:
            # _get_px_by_max_level logs error internally
            return None

        if side == Side.BUY:
            aggressive_quote_px: float | None = self._get_aggressive_tob_ask_quote_px(top_of_book, side)
            if not aggressive_quote_px:
                return None     # error logged in _get_aggressive_tob_ask_quote_px
            max_px_by_deviation: float = last_barter_px + (
                    last_barter_px / 100 * chore_limits.max_px_deviation)
            max_px_by_basis_point: float = aggressive_quote_px + (aggressive_quote_px / 100 * (
                    chore_limits.max_basis_points / 100))
            logging.debug(f"{max_px_by_basis_point = }, {max_px_by_deviation = }, {px_by_max_level = }")
            return min(max_px_by_basis_point, max_px_by_deviation, px_by_max_level)
        else:
            aggressive_quote_px: float | None = self._get_aggressive_tob_bid_quote_px(top_of_book, side)
            if not aggressive_quote_px:
                return None     # error logged in _get_aggressive_tob_ask_quote_px
            min_px_by_deviation: float = last_barter_px - (
                    last_barter_px / 100 * chore_limits.max_px_deviation)
            min_px_by_basis_point: float = aggressive_quote_px - (aggressive_quote_px / 100 * (
                    chore_limits.max_basis_points / 100))
            logging.debug(f"{min_px_by_basis_point = }, {min_px_by_deviation = }, {px_by_max_level = }")
            return max(min_px_by_deviation, min_px_by_basis_point, px_by_max_level)

    def check_new_chore(self, top_of_book: TopOfBookBaseModel, strat_brief: StratBriefBaseModel,
                        chore_limits: ChoreLimitsBaseModel, pair_strat: PairStrat, px: float, usd_px: float,
                        qty: int, side: Side, system_symbol: str, account: str, exchange: str,
                        err_dict: Dict[str, any], check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS) -> int:
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS

        chore_usd_notional = usd_px * qty

        checks_passed_ = ChoreControl.check_min_chore_notional(pair_strat, self.strat_limit, chore_usd_notional,
                                                               system_symbol, side)

        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS: checks_passed |= checks_passed_

        if check_mask == ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL:
            return checks_passed  # skip other checks - they were conducted before, this is adjusted chore
        checks_passed_ = ChoreControl.check_max_chore_notional(chore_limits, chore_usd_notional, system_symbol, side)

        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS: checks_passed |= checks_passed_

        checks_passed_ = ChoreControl.check_max_chore_qty(chore_limits, qty, system_symbol, side)

        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS: checks_passed |= checks_passed_

        if top_of_book:
            breach_px: float = self.get_breach_threshold_px(top_of_book, chore_limits, side, system_symbol)
            if breach_px is not None:
                if side == Side.BUY:
                    if px > breach_px:
                        # @@@ below error log is used in specific test case for string matching - if changed here
                        # needs to be changed in test also
                        logging.error(f"blocked generated BUY chore, chore {px = } > allowed max_px {breach_px}, "
                                      f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                        checks_passed |= ChoreControl.ORDER_CONTROL_BUY_ORDER_MAX_PX_FAIL
                elif side == Side.SELL:
                    if px < breach_px:
                        # @@@ below error log is used in specific test case for string matching - if changed here
                        # needs to be changed in test also
                        logging.error(f"blocked generated SELL chore, chore {px = } < allowed min_px {breach_px}, "
                                      f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                        checks_passed |= ChoreControl.ORDER_CONTROL_SELL_ORDER_MIN_PX_FAIL
                else:
                    logging.error(f"blocked generated unsupported {side = } chore, chore {px = }, {qty = }, "
                                  f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                    checks_passed |= ChoreControl.ORDER_CONTROL_UNSUPPORTED_SIDE_FAIL
            else:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                              f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}, "
                              f"{px = }, {usd_px = }")
                checks_passed |= ChoreControl.ORDER_CONTROL_NO_BREACH_PX_FAIL
        else:
            logging.error(f"blocked generated chore, unable to conduct px checks: top_of_book is sent None for strat: "
                          f"{self.strat_cache}, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            checks_passed |= ChoreControl.ORDER_CONTROL_NO_TOB_FAIL

        checks_passed |= self.check_strat_limits(strat_brief, px, usd_px, qty, side, chore_usd_notional,
                                                 system_symbol, err_dict)

        # TODO LAZY Read config "chore_pace_seconds" to pace chores (needed for testing - not a limit)
        if self.chore_pase_seconds > 0:
            # allow chores only after chore_pase_seconds
            if self.last_chore_timestamp.add(seconds=self.chore_pase_seconds) < DateTime.now():
                checks_passed |= ChoreControl.ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL

        return checks_passed

    @staticmethod
    def create_n_run_md_shell_script(pair_strat, generation_start_file_path, generation_stop_file_path):
        subscription_data = \
            [
                (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg1.sec.sec_id_source)),
                (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg2.sec.sec_id_source))
            ]
        db_name = os.environ["DB_NAME"]
        exch_code = "SS" if pair_strat.pair_strat_params.strat_leg1.exch_id == "SSE" else "SZ"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=pair_strat.host,
                           port=pair_strat.port, db_name=db_name, exch_code=exch_code,
                           project_name="street_book"))

        create_stop_md_script(str(generation_start_file_path), str(generation_stop_file_path))
        os.chmod(generation_stop_file_path, stat.S_IRWXU)

        if os.path.exists(generation_start_file_path):
            # first stopping script if already exists
            subprocess.Popen([f"{generation_stop_file_path}"])
        create_md_shell_script(md_shell_env_data, str(generation_start_file_path), mode="MD")
        os.chmod(generation_start_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{generation_start_file_path}"])

    def _mark_strat_state_as_error(self, pair_strat: PairStratBaseModel):
        alert_str: str = \
            (f"Marking strat_state to ERROR for strat: {self.pair_street_book_id} "
             f"{get_pair_strat_log_key(pair_strat)};;; {pair_strat = }")
        logging.info(alert_str)
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
            _id=pair_strat.id, strat_state=StratState.StratState_ERROR)

    def _mark_strat_state_as_done(self, pair_strat: PairStratBaseModel):
        alert_str: str = \
            (f"graceful shut down processing for strat: {self.pair_street_book_id} "
             f"{get_pair_strat_log_key(pair_strat)};;; {pair_strat = }")
        logging.info(alert_str)
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
            _id=pair_strat.id, strat_state=StratState.StratState_DONE)

    def _set_strat_pause_when_portfolio_limit_check_fails(self):
        pair_strat_tuple = self.strat_cache.get_pair_strat()
        if pair_strat_tuple is not None:
            pair_strat, _ = pair_strat_tuple
            logging.critical("Putting Activated Strat to PAUSE, found portfolio_limits breached already, "
                             f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; {pair_strat = }")
            guaranteed_call_pair_strat_client(
                PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
                _id=pair_strat.id, strat_state=StratState.StratState_PAUSED)
        else:
            logging.error(f"Can't find pair_strat in strat_cache, found portfolio_limits "
                          f"breached but couldn't update strat_status: {str(self.strat_cache) = }")

    def check_n_pause_strat_before_run_if_portfolio_limit_breached(self):
        # Checking if portfolio_limits are still not breached
        is_portfolio_limits_breached_model_list: List[IsPortfolioLimitsBreached] = (
            post_book_service_http_client.is_portfolio_limits_breached_query_client())

        if len(is_portfolio_limits_breached_model_list) == 1:
            is_portfolio_limits_breached: bool = (
                is_portfolio_limits_breached_model_list[0].is_portfolio_limits_breached)
            if is_portfolio_limits_breached:
                self._set_strat_pause_when_portfolio_limit_check_fails()
            # else not required: if portfolio_limits are fine then ignore
        elif len(is_portfolio_limits_breached_model_list) == 0:
            logging.critical("PairStrat service seems down, can't check portfolio_limits before current strat "
                             "activation - putting strat to pause")
            self._set_strat_pause_when_portfolio_limit_check_fails()
        else:
            err_str_ = ("is_portfolio_limits_breached_query_client must return list of exact one "
                        f"IsPortfolioLimitsBreached model, but found "
                        f"{len(is_portfolio_limits_breached_model_list) = }, "
                        f"{is_portfolio_limits_breached_model_list = }")
            logging.error(err_str_)

    def run(self):
        ret_val: int = -5000

        # Getting pre-requisites ready before strat active runs
        run_coro = StreetBook.underlying_handle_strat_activate_query_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e_:
            logging.exception(
                f"underlying_handle_strat_activate_query_http failed: Exiting executor run trigger, "
                f"exception: {e_}")
            return -5001

        max_retry_count: Final[int] = 10
        retry_count: int = 0
        pair_strat_tuple: Tuple[PairStratBaseModel, DateTime] | None = None
        pair_strat: PairStratBaseModel | None = None
        while pair_strat_tuple is None or pair_strat is None:
            # getting pair_strat
            pair_strat_tuple = self.strat_cache.get_pair_strat()
            if pair_strat_tuple is None:
                logging.error("Can't find pair_strat_tuple even while entered executor's run method, likely bug "
                              "in loading strat_cache with pair_strat")
                if retry_count < max_retry_count:
                    retry_count += 1
                    continue
                else:
                    return -3000

            pair_strat, _ = pair_strat_tuple
            if pair_strat is None:
                logging.error("Can't find pair_strat from pair_strat_tuple even while entered "
                              "executor's run method, likely bug in loading strat_cache with pair_strat")
                if retry_count < max_retry_count:
                    retry_count += 1
                    continue
                else:
                    return -3001

        # setting index for leg1 and leg2 symbols
        self.leg_1_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        self.leg_1_side = pair_strat.pair_strat_params.strat_leg1.side
        self.leg_2_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        self.leg_2_side = pair_strat.pair_strat_params.strat_leg2.side

        scripts_dir = PurePath(__file__).parent.parent / "scripts"
        # start file generator
        start_sh_file_path = scripts_dir / f"start_ps_id_{pair_strat.id}_md.sh"
        stop_sh_file_path = scripts_dir / f"stop_ps_id_{pair_strat.id}_md.sh"

        try:
            StreetBook.create_n_run_md_shell_script(pair_strat, start_sh_file_path, stop_sh_file_path)
            self.check_n_pause_strat_before_run_if_portfolio_limit_breached()

            while 1:
                try:
                    ret_val = self.internal_run()
                except Exception as e:
                    logging.exception(f"Run returned with exception - sending again, exception: {e}")
                finally:
                    if ret_val == 1:
                        logging.info(f"explicit strat shutdown requested for: {self.pair_street_book_id}, "
                                     f"going down")
                        break
                    elif ret_val != 0:
                        logging.error(f"Error: Run returned, code: {ret_val} - sending again")
                    else:
                        pair_strat, _ = self.strat_cache.get_pair_strat()
                        if pair_strat.strat_state != StratState.StratState_DONE:
                            self._mark_strat_state_as_done(pair_strat)
                            logging.debug(f"StratStatus with id: {self.pair_street_book_id} Marked Done, "
                                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
                            ret_val = 0
                        else:
                            logging.error(f"unexpected, pair_strat: {self.pair_street_book_id} "
                                          f"was already Marked Done, pair_strat_key: "
                                          f"{get_pair_strat_log_key(pair_strat)}")
                            ret_val = -4000  # helps find the error location
                        break
        except Exception as e:
            logging.exception(f"Some Error occurred in run method of executor, exception: {e}")
            ret_val = -4001
        finally:
            # running, stop md script
            subprocess.Popen([f"{stop_sh_file_path}"])

            if ret_val != 0 and ret_val != 1:
                self._mark_strat_state_as_error(pair_strat)

            # removing created scripts
            try:
                if os.path.exists(start_sh_file_path):
                    os.remove(start_sh_file_path)
                if os.path.exists(stop_sh_file_path):
                    os.remove(stop_sh_file_path)
            except Exception as e:
                err_str_ = (f"Something went wrong while deleting md scripts, "
                            f"exception: {e}")
                logging.error(err_str_)

        return ret_val

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat - may extend to accept symbol and send revised px according to underlying currency
        """
        return px / self.leg1_fx

    @perf_benchmark_sync_callable("street_book")
    def _check_tob_n_place_non_systematic_chore(self, new_chore: NewChoreBaseModel, pair_strat: PairStrat,
                                                strat_brief: StratBriefBaseModel, chore_limits: ChoreLimitsBaseModel,
                                                top_of_books: List[TopOfBookBaseModel]) -> int:
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        barter_tob: TopOfBookBaseModel | None = None
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        if leg1_tob is not None:
            if self.strat_cache.leg1_bartering_symbol == new_chore.security.sec_id:
                barter_tob = leg1_tob

        if barter_tob is None and leg2_tob is not None:
            if self.strat_cache.leg2_bartering_symbol == new_chore.security.sec_id:
                barter_tob = leg2_tob

        if barter_tob is None:
            err_str_ = f"unable to send new_chore: no matching leg in this strat: {new_chore} " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;;" \
                       f"{self.strat_cache = }, {pair_strat = }"
            logging.error(err_str_)
            return False
        else:
            usd_px = self.get_usd_px(new_chore.px, new_chore.security.sec_id)
            chore_placed: int = self.place_new_chore(barter_tob, strat_brief, chore_limits, pair_strat,
                                                     new_chore.px, usd_px,
                                                     new_chore.qty, new_chore.side,
                                                     system_symbol=new_chore.security.sec_id)
            return chore_placed

    @staticmethod
    def get_leg1_leg2_ratio(leg1_px: float, leg2_px: float):
        if math.isclose(leg2_px, 0):
            return 0
        return leg1_px / leg2_px

    def _get_bid_tob_px_qty(self, tob: TopOfBook) -> Tuple[float | None, int | None]:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if tob.bid_quote is not None:
                has_valid_px_qty = True
                if not tob.bid_quote.qty:
                    logging.error(f"Invalid {tob.bid_quote.qty = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                elif math.isclose(tob.bid_quote.px, 0):
                    logging.error(f"Invalid {tob.bid_quote.px = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                if has_valid_px_qty:
                    return tob.bid_quote.px, tob.bid_quote.qty
            else:
                logging.error(f"Can't find bid_quote in top of book, {tob.symbol = };;; {tob = }")
        return None, None

    def _get_ask_tob_px_qty(self, tob: TopOfBook) -> Tuple[float | None, int | None]:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if tob.ask_quote is not None:
                has_valid_px_qty = True
                if not tob.ask_quote.qty:
                    logging.error(f"Invalid {tob.ask_quote.qty = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                elif math.isclose(tob.ask_quote.px, 0):
                    logging.error(f"Invalid {tob.ask_quote.px = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                if has_valid_px_qty:
                    return tob.ask_quote.px, tob.ask_quote.qty
            else:
                logging.error(f"Can't find ask_quote in top of book, {tob.symbol = };;; {tob = }")
        return None, None

    def _place_chore(self, pair_strat: PairStratBaseModel, strat_brief: StratBriefBaseModel,
                     chore_limits: ChoreLimitsBaseModel, side: TickType, tob: TopOfBookBaseModel) -> float:
        """returns float posted notional of the chore sent"""
        # fail-safe
        pair_strat = self.strat_cache.get_pair_strat_obj()
        if pair_strat is not None:
            # If pair_strat not active, don't act, just return [check MD state and take action if required]
            if pair_strat.strat_state != StratState.StratState_ACTIVE or self._is_outside_bartering_hours():
                logging.error("Blocked place chore - strat not in activ state")
                return 0  # no chore sent = no posted notional
        if side == TickType.BID:
            px, qty = self._get_bid_tob_px_qty(tob)
        else:
            px, qty = self._get_ask_tob_px_qty(tob)

        if px is None or qty is None:
            return 0  # no chore sent = no posted notional

        # Note: not taking tob mutex since symbol is not changed
        ask_usd_px: float = self.get_usd_px(px, tob.symbol)
        chore_placed = self.place_new_chore(tob, strat_brief, chore_limits, pair_strat, px,
                                            ask_usd_px, qty,
                                            Side.BUY, tob.symbol)
        if chore_placed == ChoreControl.ORDER_CONTROL_SUCCESS:
            posted_notional = px * qty
            return posted_notional

    @perf_benchmark_sync_callable("street_book")
    def _check_tob_and_place_chore(self, pair_strat: PairStratBaseModel | PairStrat, strat_brief: StratBriefBaseModel,
                                   chore_limits: ChoreLimitsBaseModel, top_of_books: List[TopOfBookBaseModel]) -> int:
        posted_leg1_notional: float = 0
        posted_leg2_notional: float = 0
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        barter_tob: TopOfBookBaseModel
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        chore_placed: int = ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
        if leg1_tob is not None and self.strat_cache.leg1_bartering_symbol is not None:
            if abs(self.leg1_notional) <= abs(self.leg2_notional):
                # process primary leg
                if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:  # execute aggressive buy
                    posted_leg1_notional = self._place_chore(pair_strat, strat_brief, chore_limits, TickType.ASK,
                                                             leg1_tob)
                    if math.isclose(posted_leg1_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg1_notional = self._place_chore(pair_strat, strat_brief, chore_limits, TickType.BID,
                                                             leg1_tob)
                    if math.isclose(posted_leg1_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if leg2_tob is not None and self.strat_cache.leg2_bartering_symbol is not None:
            if abs(self.leg2_notional) <= abs(self.leg1_notional):
                # process secondary leg
                if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:  # execute aggressive buy
                    posted_leg2_notional = self._place_chore(pair_strat, strat_brief, chore_limits, TickType.ASK,
                                                             leg2_tob)
                    if math.isclose(posted_leg2_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg2_notional = self._place_chore(pair_strat, strat_brief, chore_limits, TickType.BID,
                                                             leg2_tob)
                    if math.isclose(posted_leg2_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if chore_placed == ChoreControl.ORDER_CONTROL_SUCCESS:
            self.last_chore_timestamp = DateTime.now()
            self.leg1_notional += posted_leg1_notional
            self.leg2_notional += posted_leg2_notional
            logging.debug(f"strat-matched ToB for pair_strat_key {get_pair_strat_log_key(pair_strat)}: "
                          f"{[str(tob) for tob in top_of_books]}")
        return chore_placed

    def _both_side_tob_has_data(self, leg_1_tob: TopOfBook, leg_2_tob: TopOfBook) -> bool:
        if leg_1_tob is not None and leg_2_tob is not None:
            with (MobileBookMutexManager(self.mobile_book_provider, leg_1_tob, leg_2_tob)):
                if leg_1_tob.last_update_date_time is not None and leg_2_tob.last_update_date_time is not None:
                    return True
        return False

    def _get_tob_symbol(self, tob: TopOfBook) -> str:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            return tob.symbol

    def _get_tob_last_update_date_time(self, tob: TopOfBook) -> DateTime:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            return tob.last_update_date_time

    def _get_tob_bid_quote_px(self, tob: TopOfBook) -> float | None:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if tob.bid_quote is not None:
                return tob.bid_quote.px
            else:
                logging.info(f"Can't find bid_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    def _get_tob_ask_quote_px(self, tob: TopOfBook) -> float | None:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if tob.ask_quote is not None:
                return tob.ask_quote.px
            else:
                logging.info(f"Can't find ask_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    def _get_tob_bid_quote_last_update_date_time(self, tob: TopOfBook) -> DateTime | None:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if tob.bid_quote is not None:
                return tob.bid_quote.last_update_date_time
            else:
                logging.info(f"Can't find bid_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    def _get_tob_ask_quote_last_update_date_time(self, tob: TopOfBook) -> DateTime | None:
        with MobileBookMutexManager(self.mobile_book_provider, tob):
            if tob.ask_quote is not None:
                return tob.ask_quote.last_update_date_time
            else:
                logging.info(f"Can't find ask_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    @perf_benchmark_sync_callable("street_book")
    def _check_tob_and_place_chore_test(self, pair_strat: PairStratBaseModel | PairStrat,
                                        strat_brief: StratBriefBaseModel, chore_limits: ChoreLimitsBaseModel,
                                        top_of_books: List[TopOfBookBaseModel]) -> int:
        buy_top_of_book: TopOfBookBaseModel | None = None
        sell_top_of_book: TopOfBookBaseModel | None = None

        if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
            buy_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            sell_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        else:
            buy_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            sell_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id

        chore_placed: int = ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        leg_1_top_of_book: TopOfBook = (
            self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book(
                self._top_of_books_update_date_time))
        leg_2_top_of_book = (
            self.mobile_book_container_cache.leg_2_mobile_book_container.get_top_of_book(
                self._top_of_books_update_date_time))

        if self._both_side_tob_has_data(leg_1_top_of_book, leg_2_top_of_book):
            top_of_books = [leg_1_top_of_book, leg_2_top_of_book]

            latest_update_date_time: DateTime | None = None
            for top_of_book in top_of_books:
                if latest_update_date_time is None:
                    tob_symbol = self._get_tob_symbol(top_of_book)
                    if tob_symbol == buy_symbol:
                        buy_top_of_book = top_of_book
                        sell_top_of_book = None
                    elif tob_symbol == sell_symbol:
                        sell_top_of_book = top_of_book
                        buy_top_of_book = None
                    else:
                        err_str_ = f"top_of_book with unsupported test symbol received, {top_of_book = }, " \
                                   f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                        logging.error(err_str_)
                        raise Exception(err_str_)
                    latest_update_date_time = self._get_tob_last_update_date_time(top_of_book)
                else:
                    latest_update_date_time_ = self._get_tob_last_update_date_time(top_of_book)
                    if latest_update_date_time_ > latest_update_date_time:
                        tob_symbol = self._get_tob_symbol(top_of_book)
                        if tob_symbol == buy_symbol:
                            buy_top_of_book = top_of_book
                            sell_top_of_book = None
                        elif tob_symbol == sell_symbol:
                            sell_top_of_book = top_of_book
                            buy_top_of_book = None
                        else:
                            err_str_ = f"top_of_book with unsupported test symbol received, {top_of_book = }, " \
                                       f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                            logging.error(err_str_)
                            raise Exception(err_str_)
                        latest_update_date_time = latest_update_date_time_
            # tob tuple last_update_date_time is set to least of the 2 tobs update time
            # setting it to latest_update_date_time to allow chore to be placed
            self._top_of_books_update_date_time = latest_update_date_time

            if buy_top_of_book is not None:
                bid_quote_last_update_date_time = self._get_tob_bid_quote_last_update_date_time(buy_top_of_book)
                if bid_quote_last_update_date_time == self._top_of_books_update_date_time:
                    buy_tob_bid_px = self._get_tob_bid_quote_px(buy_top_of_book)
                    if buy_tob_bid_px == 100:
                        px = random.randint(90, 100)
                        qty = random.randint(85, 95)
                        usd_px: float = self.get_usd_px(px, buy_symbol)
                        chore_placed = self.place_new_chore(buy_top_of_book, strat_brief, chore_limits,
                                                            pair_strat, px, usd_px, qty,
                                                            Side.BUY, buy_symbol)
            elif sell_top_of_book is not None:
                ask_quote_last_update_date_time = self._get_tob_ask_quote_last_update_date_time(sell_top_of_book)
                if ask_quote_last_update_date_time == self._top_of_books_update_date_time:
                    sell_tob_ask_px = self._get_tob_ask_quote_px(sell_top_of_book)
                    if sell_tob_ask_px == 120:
                        px = random.randint(100, 110)
                        qty = random.randint(95, 105)
                        usd_px: float = self.get_usd_px(px, sell_symbol)
                        chore_placed = self.place_new_chore(sell_top_of_book, strat_brief, chore_limits,
                                                            pair_strat, px, usd_px, qty,
                                                            Side.SELL, sell_symbol)
            else:
                err_str_ = "TOB updates could not find any updated buy or sell tob, " \
                           f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                logging.debug(err_str_)
            return chore_placed
        return False

    def get_leg1_fx(self):
        if self.leg1_fx:
            return self.leg1_fx
        else:
            if not self.strat_cache.leg1_fx_symbol_overview:
                self.strat_cache.leg1_fx_symbol_overview = \
                    StratCache.fx_symbol_overview_dict[self.strat_cache.leg1_fx_symbol]
            if self.strat_cache.leg1_fx_symbol_overview and self.strat_cache.leg1_fx_symbol_overview.closing_px and \
                    (not math.isclose(self.strat_cache.leg1_fx_symbol_overview.closing_px, 0)):
                self.leg1_fx = self.strat_cache.leg1_fx_symbol_overview.closing_px
                return self.leg1_fx
            else:
                logging.error(f"unable to find fx_symbol_overview for "
                              f"{self.strat_cache.leg1_fx_symbol = };;; {self.strat_cache = }")
                return None

    def process_cxl_request(self):
        cancel_chores_and_date_tuple = self.strat_cache.get_cancel_chore(self._cancel_chores_update_date_time)
        if cancel_chores_and_date_tuple is not None:
            cancel_chores, self._cancel_chores_update_date_time = cancel_chores_and_date_tuple
            if cancel_chores is not None:
                final_slice = len(cancel_chores)
                unprocessed_cancel_chores: List[CancelChoreBaseModel] = \
                    cancel_chores[self._cancel_chores_processed_slice:final_slice]
                self._cancel_chores_processed_slice = final_slice
                for cancel_chore in unprocessed_cancel_chores:
                    if not cancel_chore.cxl_confirmed:
                        self.bartering_link_place_cxl_chore(
                            cancel_chore.chore_id, cancel_chore.side, None, cancel_chore.security.sec_id,
                            underlying_account="NA")

                # if some update was on existing cancel_chores then this semaphore release was for that update only,
                # therefore returning True to continue and wait for next semaphore release
                return True
        # all else return false - no cancel_chore to process
        return False

    def bartering_link_place_cxl_chore(self, chore_id, side, bartering_sec_id, system_sec_id, underlying_account):
        # coro needs public method
        run_coro = self.bartering_link.place_cxl_chore(chore_id, side, bartering_sec_id, system_sec_id, underlying_account)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for start_executor_server task to finish
        try:
            # ignore return chore_journal: don't generate cxl chores in system, just treat cancel acks as unsol cxls
            if not (res := future.result()):
                logging.error(f"bartering_link_place_cxl_chore failed, {res = } returned")
        except Exception as e:
            logging.exception(f"bartering_link_place_cxl_chore failed with exception: {e}")

    def is_pair_strat_done(self, strat_brief: StratBriefBaseModel) -> int:
        """
        Args:
            strat_brief:
        Returns:
            0: indicates done; no notional to consume on at-least 1 leg & no-open chores for this strat in market
            -1: indicates needs-processing; strat has notional left to consume on either of the legs
            + number: indicates finishing: no notional to consume on at-least 1 leg but open chores for strat in market
        """
        strat_done: bool = False
        open_chore_count: int = self.strat_cache.get_open_chore_count_from_cache()

        if 0 == open_chore_count and (
                strat_brief.pair_sell_side_bartering_brief.consumable_notional < self.strat_limit.min_chore_notional):
            # sell leg of strat is done - if either leg is done - strat is done
            logging.info(f"Sell Side Leg is done, no open chores remaining + sell-remainder: "
                         f"{strat_brief.pair_sell_side_bartering_brief.consumable_notional} is less than allowed"
                         f" {self.strat_limit.min_chore_notional = }, no further chores possible")
            strat_done = True
        # else not required, more notional to consume on sell leg - strat done is set to 1 (no error, not done)
        if 0 == open_chore_count and (
                strat_brief.pair_buy_side_bartering_brief.consumable_notional < self.strat_limit.min_chore_notional):
            # buy leg of strat is done - if either leg is done - strat is done
            logging.info(f"Buy Side Leg is done, no open chores remaining + buy-remainder: "
                         f"{strat_brief.pair_buy_side_bartering_brief.consumable_notional} is less than allowed"
                         f" {self.strat_limit.min_chore_notional = }, no further chores possible")
            strat_done = True
        # else not required, more notional to consume on buy leg - strat done is set to 1 (no error, not done)
        if strat_done:
            if 0 == open_chore_count:
                logging.info(f"Strat is done")
            else:
                logging.warning(f"Strat is finishing [if / after strat open chores: {open_chore_count} are filled]")
            return open_chore_count  # [ returns 0 or + ive number] - Done or Finishing
        else:
            return -1  # in progress

    def _get_latest_system_control(self) -> SystemControlBaseModel | None:
        system_control: SystemControlBaseModel | None = None
        system_control_tuple = self.bartering_data_manager.bartering_cache.get_system_control()
        if system_control_tuple is None:
            logging.warning("no kill_switch found yet - strat will not trigger until kill_switch arrives")
            return None
        else:
            system_control, self._system_control_update_date_time = system_control_tuple
        return system_control

    def is_strat_ready_for_next_opportunity(self, log_error: bool = False) -> bool:
        open_chore_count: int = self.strat_cache.get_open_chore_count_from_cache()
        if self.strat_cache.has_unack_leg():
            if log_error:
                logging.debug(f"blocked opportunity search, has unack leg and {open_chore_count} open chore(s)")
            return False
        elif (not self.allow_multiple_open_chores_per_strat) and 0 != open_chore_count:
            if log_error:
                logging.debug(f"blocked opportunity search, has {open_chore_count} open chore(s)")
            return False
        else:
            return True

    def _get_latest_pair_strat(self) -> PairStrat | None:
        pair_strat_tuple = self.strat_cache.get_pair_strat()
        if pair_strat_tuple is not None:
            pair_strat, _ = pair_strat_tuple
            if pair_strat:
                return pair_strat
            else:
                logging.error(f"pair_strat in pair_strat_tuple is None for: {self.strat_cache = }")
        else:
            logging.error(f"pair_strat_tuple is None for: {self.strat_cache = }")
        return None

    def _is_outside_bartering_hours(self):
        if self.is_sanity_test_run or self.is_test_run or self.is_dev_env: return False
        return False

    def internal_run(self):
        logging.debug("Started street_book run")
        while 1:
            self.strat_limit = None
            try:
                # self.strat_cache.notify_semaphore.acquire()
                StreetBook.mobile_book_provider.acquire_notify_semaphore()
                # remove all unprocessed signals from semaphore, logic handles all new updates in single iteration
                # clear_semaphore(self.strat_cache.notify_semaphore)

                # 0. Checking if strat_cache stopped (happens most likely when strat is not ongoing anymore)
                if self.strat_cache.stopped:
                    self.strat_cache.set_pair_strat(None)
                    return 1  # indicates explicit shutdown requested from server

                # 1. check if portfolio status has updated since we last checked
                system_control: SystemControlBaseModel | None = self._get_latest_system_control()
                if system_control is None:
                    continue

                # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
                pair_strat: PairStrat = self._get_latest_pair_strat()
                if pair_strat is None:
                    return -1

                # If pair_strat is not active, don't act, just return [check MD state and take action if required]
                if pair_strat.strat_state != StratState.StratState_ACTIVE or self._is_outside_bartering_hours():
                    continue
                else:
                    strat_limits_tuple = self.strat_cache.get_strat_limits()
                    self.strat_limit, strat_limits_update_date_time = strat_limits_tuple

                # 3. check if any cxl chore is requested and send out
                if self.process_cxl_request():
                    continue

                strat_brief: StratBriefBaseModel | None = None
                # strat doesn't need to check if strat_brief is updated or not
                # strat_brief_tuple = self.strat_cache.get_strat_brief(self._strat_brief_update_date_time)
                strat_brief_tuple = self.strat_cache.get_strat_brief()
                if strat_brief_tuple:
                    strat_brief, self._strat_brief_update_date_time = strat_brief_tuple
                    if strat_brief:
                        pass
                    else:
                        logging.error(f"can't proceed, strat_brief found None for strat-cache: "
                                      f"{self.strat_cache.get_key()};;; [ {self.strat_cache=} ]")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"can't proceed! strat_brief_tuple: {strat_brief_tuple} not found for strat-cache: "
                                  f"{self.strat_cache.get_key()};;; [ {self.strat_cache=} ]")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                chore_limits: ChoreLimitsBaseModel | None = None
                chore_limits_tuple = self.bartering_data_manager.bartering_cache.get_chore_limits()
                if chore_limits_tuple:
                    chore_limits, _ = chore_limits_tuple
                    if chore_limits and self.strat_limit:
                        strat_done_counter = self.is_pair_strat_done(strat_brief)
                        if 0 == strat_done_counter:
                            return 0  # triggers graceful shutdown
                        elif -1 != strat_done_counter:
                            # strat is finishing: waiting to close pending strat_done_counter number of open chores
                            continue
                        # else not needed - move forward, more processing needed to complete the strat
                    else:
                        logging.error(f"Can't proceed: chore_limits/strat_limit not found for bartering_cache: "
                                      f"{self.bartering_data_manager.bartering_cache}; {self.strat_cache = }")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"chore_limits_tuple not found for strat: {self.strat_cache}, can't proceed")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                # 4. get top_of_book (new or old to be checked by respective strat based on strat requirement)

                leg_1_top_of_book = (
                    self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book())
                leg_2_top_of_book = (
                    self.mobile_book_container_cache.leg_2_mobile_book_container.get_top_of_book())

                if not self._both_side_tob_has_data(leg_1_top_of_book, leg_2_top_of_book):
                    logging.warning(f"strats need both sides of TOB to be present, "
                                    f"found  only leg_1 or only leg_2 or neither of them"
                                    f";;;tob found: {leg_1_top_of_book = }, "
                                    f"{leg_2_top_of_book = }")
                    continue

                top_of_books = [leg_1_top_of_book, leg_2_top_of_book]

                # 5. ensure leg1_fx is present - otherwise don't proceed - retry later
                if not self.get_leg1_fx():
                    logging.error(f"USD fx rate not found for strat: {self.strat_cache.get_key()}, unable to proceed, "
                                  f"fx symbol: {self.strat_cache.leg1_fx_symbol}, we'll retry in next attempt")
                    continue

                # 6. If kill switch is enabled - don't act, just return
                if system_control.kill_switch:
                    logging.debug("not-progressing: kill switch enabled")
                    continue

                # 7. continue only if past-pair (iff triggered) has no open/unack chores
                if not self.is_strat_ready_for_next_opportunity(log_error=True):
                    continue

                # 8. If any manual new_chore requested: apply risk checks
                # (maybe no strat param checks?) & send out
                new_chores_and_date_tuple = self.strat_cache.get_new_chore(self._new_chores_update_date_time)
                if new_chores_and_date_tuple is not None:
                    new_chores, self._new_chores_update_date_time = new_chores_and_date_tuple
                    if new_chores is not None:
                        final_slice = len(new_chores)
                        unprocessed_new_chores: List[NewChoreBaseModel] = (
                            new_chores[self._new_chores_processed_slice:final_slice])
                        self._new_chores_processed_slice = final_slice
                        for new_chore in unprocessed_new_chores:
                            if system_control and not system_control.kill_switch:
                                self._check_tob_n_place_non_systematic_chore(new_chore, pair_strat, strat_brief,
                                                                             chore_limits, top_of_books)
                                continue
                            else:
                                # kill switch in force - drop the chore
                                logging.error(f"kill switch is enabled, dropping non-systematic "
                                              f"new-chore request;;; {new_chore = } "
                                              "non-systematic new chore call")
                                continue
                # else no new_chore to process, ignore and move to next step

                if self.is_sanity_test_run:
                    self._check_tob_and_place_chore_test(pair_strat, strat_brief, chore_limits, top_of_books)
                else:
                    self._check_tob_and_place_chore(pair_strat, strat_brief, chore_limits, top_of_books)
                continue  # all good - go next run
            except Exception as e:
                logging.exception(f"Run returned with exception: {e}")
                return -1
        # we are outside while 1 (strat processing loop) - graceful shut down this strat processing
        return 0
