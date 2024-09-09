import math
from enum import Enum
from typing import Final
import logging
import random

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    MobileBookMutexManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.mobile_book_cache import TopOfBook


class ChoreControl:
    # if new const added here, MUST add in dict below
    ORDER_CONTROL_SUCCESS: Final[int] = 0x0  # b0
    ORDER_CONTROL_PLACE_NEW_ORDER_FAIL: Final[int] = 0x1  # b01
    ORDER_CONTROL_EXCEPTION_FAIL: Final[int] = 0x2  # b10
    ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL: Final[int] = 0x4  # b100
    ORDER_CONTROL_UNSUPPORTED_SIDE_FAIL: Final[int] = 0x8  # b1000
    ORDER_CONTROL_NO_BREACH_PX_FAIL: Final[int] = 0x10  # b10000 and so on
    ORDER_CONTROL_NO_TOB_FAIL: Final[int] = 0x20
    ORDER_CONTROL_EXTRACT_AVAILABILITY_FAIL: Final[int] = 0x40
    ORDER_CONTROL_CHECK_UNACK_FAIL: Final[int] = 0x80
    ORDER_CONTROL_LIMIT_UP_FAIL: Final[int] = 0x100
    ORDER_CONTROL_LIMIT_DOWN_FAIL: Final[int] = 0x200
    ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL: Final[int] = 0x400
    ORDER_CONTROL_MAX_ORDER_NOTIONAL_FAIL: Final[int] = 0x800
    ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL: Final[int] = 0x1000
    ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL: Final[int] = 0x2000
    ORDER_CONTROL_UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL: Final[int] = 0x4000
    ORDER_CONTROL_MAX_CONCENTRATION_FAIL: Final[int] = 0x8000
    ORDER_CONTROL_MAX_ORDER_QTY_FAIL: Final[int] = 0x10000
    ORDER_CONTROL_ORDER_MAX_PX_FAIL: Final[int] = 0x20000
    ORDER_CONTROL_ORDER_MIN_PX_FAIL: Final[int] = 0x40000
    ORDER_CONTROL_NETT_FILLED_NOTIONAL_FAIL: Final[int] = 0x80000
    ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL: Final[int] = 0x100000
    ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL: Final[int] = 0x200000
    ORDER_CONTROL_INIT_AS_FAIL = 0x400000
    ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL: Final[int] = 0x800000
    ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL: Final[int] = 0x1000000
    chore_control_type_dict: Final[Dict[int, str]] = {
        0x0: "SUCCESS",
        0x1: "PLACE_NEW_ORDER_FAIL",
        0x2: "EXCEPTION_FAIL",
        0x4: "REQUIRED_DATA_MISSING_FAIL",
        0x8: "UNSUPPORTED_SIDE_FAIL",
        0x10: "NO_BREACH_PX_FAIL",
        0x20: "NO_TOB_FAIL",
        0x40: "EXTRACT_AVAILABILITY_FAIL",
        0x80: "CHECK_UNACK_FAIL",
        0x100: "LIMIT_UP_FAIL",
        0x200: "LIMIT_DOWN_FAIL",
        0x400: "MIN_ORDER_NOTIONAL_FAIL",
        0x800: "MAX_ORDER_NOTIONAL_FAIL",
        0x1000: "CONSUMABLE_NOTIONAL_FAIL",
        0x2000: "CONSUMABLE_PARTICIPATION_QTY_FAIL",
        0x4000: "UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL",
        0x8000: "MAX_CONCENTRATION_FAIL",
        0x10000: "MAX_ORDER_QTY_FAIL",
        0x20000: "ORDER_MAX_PX_FAIL",
        0x40000: "ORDER_MIN_PX_FAIL",
        0x80000: "NETT_FILLED_NOTIONAL_FAIL",
        0x100000: "MAX_OPEN_ORDERS_FAIL",
        0x200000: "ORDER_PASE_SECONDS_FAIL",
        0x400000: "INIT_AS_FAIL",
        0x800000: "CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL",
        0x1000000: "CONSUMABLE_OPEN_NOTIONAL_FAIL",
    }

    # Min Allowed EQT chore QTY Hardcoded to 200
    MIN_EQT_ORDER_QTY: Final[int] = 20

    # max of single lot notional across both legs [lazy init]
    finishing_chore_min_notional: float | None = None

    max_spread_in_bips: ClassVar[int]

    @classmethod
    def check_min_chore_notional_normal(cls, strat_limits: StratLimits | StratLimitsBaseModel,
                                        chore_usd_notional: float, system_symbol: str, side: Side):
        # min chore notional is to be an chore opportunity condition instead of chore check
        min_chore_notional: float
        if (strat_limits.min_chore_notional_allowance and
                strat_limits.min_chore_notional > strat_limits.min_chore_notional_allowance):
            min_chore_notional = strat_limits.min_chore_notional - strat_limits.min_chore_notional_allowance
        else:
            min_chore_notional = strat_limits.min_chore_notional
        if round(min_chore_notional) > round(chore_usd_notional):
            if (strat_limits.min_chore_notional_allowance and
                    strat_limits.min_chore_notional > strat_limits.min_chore_notional_allowance):
                min_chore_notional_str = f"{strat_limits.min_chore_notional_allowance} applied {min_chore_notional}"
            else:
                min_chore_notional_str = f"{strat_limits.min_chore_notional=:.2f}"
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked chore_opportunity {min_chore_notional_str} < {chore_usd_notional=:.2f}, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return cls.ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_min_chore_notional_relaxed(cls, strat_limits: StratLimits | StratLimitsBaseModel,
                                         chore_usd_notional: float, system_symbol: str, side: Side):
        min_chore_notional_relaxed = random.randint(int(strat_limits.min_chore_notional),
                                                    int(strat_limits.min_chore_notional+strat_limits.
                                                        min_chore_notional_allowance))

        # min chore notional is to be an chore opportunity condition instead of chore check
        if min_chore_notional_relaxed > round(chore_usd_notional):
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked chore_opportunity < min_chore_notional_relaxed limit: "
                          f"{chore_usd_notional} < {min_chore_notional_relaxed}, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return cls.ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_min_chore_notional_aggressive(cls, strat_limits: StratLimits | StratLimitsBaseModel,
                                            chore_usd_notional: float, system_symbol: str, side: Side):
        # todo: currently same as normal - needs to be impl
        # min chore notional is to be an chore opportunity condition instead of chore check
        return cls.check_min_chore_notional_normal(strat_limits, chore_usd_notional, system_symbol, side)

    @classmethod
    def check_min_algo_chore_notional(cls, new_ord: NewChoreBaseModel, chore_usd_notional: float):
        if new_ord.finishing_chore:
            # check_min_chore_notional should not be applied to finishing chore
            return cls.ORDER_CONTROL_SUCCESS

        return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_min_chore_notional(cls, pair_strat: PairStrat, strat_limits: StratLimits | StratLimitsBaseModel,
                                 new_ord: NewChoreBaseModel, chore_usd_notional: float):
        if new_ord.finishing_chore:
            # check_min_chore_notional should not be applied to finishing chore
            return cls.ORDER_CONTROL_SUCCESS
        # else continue with check
        system_symbol = new_ord.security.sec_id
        if pair_strat.pair_strat_params.strat_mode == StratMode.StratMode_Aggressive:
            # min chore notional is to be an chore opportunity condition instead of chore check
            checks_passed_ = ChoreControl.check_min_chore_notional_aggressive(strat_limits, chore_usd_notional,
                                                                              system_symbol, new_ord.side)
        elif pair_strat.pair_strat_params.strat_mode == StratMode.StratMode_Relaxed:
            checks_passed_ = ChoreControl.check_min_chore_notional_relaxed(strat_limits, chore_usd_notional,
                                                                           system_symbol, new_ord.side)
        else:
            checks_passed_ = ChoreControl.check_min_chore_notional_normal(strat_limits, chore_usd_notional,
                                                                          system_symbol, new_ord.side)
        return checks_passed_

    @classmethod
    def check_max_chore_notional_(cls, max_chore_notional: float, chore_usd_notional: float,
                                 system_symbol: str, side: Side):
        if max_chore_notional < chore_usd_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, breaches max_chore_notional limit, expected less than: "
                          f"{max_chore_notional=}, found: {chore_usd_notional=}, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            # err_dict["max_chore_notional"] = f"{int(chore_limits.max_chore_notional)}"
            return ChoreControl.ORDER_CONTROL_MAX_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_chore_notional(cls, chore_limits: ChoreLimits | ChoreLimitsBaseModel, chore_usd_notional: float,
                                 system_symbol: str, side: Side, is_algo: bool = False):
        if not is_algo:
            return cls.check_max_chore_notional_(chore_limits.max_chore_notional, chore_usd_notional, system_symbol,
                                                 side)
        else:
            return cls.check_max_chore_notional_(chore_limits.max_chore_notional_algo, chore_usd_notional,
                                                 system_symbol, side)

    @classmethod
    def check_max_chore_qty_(cls, max_chore_qty: int, qty: int, system_symbol: str, side: Side) -> int:
        if max_chore_qty < qty:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, breaches max_chore_qty limit, expected less than: "
                          f"{max_chore_qty}, found: {qty}, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return ChoreControl.ORDER_CONTROL_MAX_ORDER_QTY_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_chore_qty(cls, chore_limits: ChoreLimits | ChoreLimitsBaseModel, qty: int, system_symbol: str,
                            side: Side, is_algo: bool = False):
        if not is_algo:
            return cls.check_max_chore_qty_(chore_limits.max_chore_qty, qty, system_symbol, side)
        else:
            return cls.check_max_chore_qty_(chore_limits.max_chore_qty_algo, qty, system_symbol, side)

    @classmethod
    def check_min_eqt_chore_qty(cls, chore_limits: ChoreLimits | ChoreLimitsBaseModel, qty: int, system_symbol: str,
                                side: Side, is_algo: bool = False):
        if qty >= cls.MIN_EQT_ORDER_QTY:
            return cls.ORDER_CONTROL_SUCCESS
        else:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, breaches min_eqt_chore_qty hard-coded-limit, expected {qty=} >= "
                          f"{cls.MIN_EQT_ORDER_QTY=}, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return ChoreControl.ORDER_CONTROL_MAX_ORDER_QTY_FAIL

    @classmethod
    def check_max_contract_qty_(cls, max_contract_qty, qty: int, system_symbol: str, side: Side) -> int:
        if max_contract_qty < qty:
            logging.error(f"blocked generated chore, breaches max_contract_qty limit, unexpected {max_contract_qty=} < "
                          f"{qty=}, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return ChoreControl.ORDER_CONTROL_MAX_ORDER_QTY_FAIL
        else:
            return ChoreControl.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_contract_qty(cls, chore_limits: ChoreLimits | ChoreLimitsBaseModel, qty: int,
                               system_symbol: str, side: Side, is_algo: bool = False):
        if not is_algo:
            return cls.check_max_contract_qty_(chore_limits.max_contract_qty, qty, system_symbol, side)
        else:
            return cls.check_max_contract_qty_(chore_limits.max_contract_qty_algo, qty, system_symbol, side)

    ##################### Price Control Impls ################################

    @staticmethod
    def px_breached(breach_px: float, px: float, side: Side, system_symbol: str) -> bool:
        breached: bool = False
        if breach_px is not None:
            if side == Side.BUY:
                if px > breach_px:
                    breached = True
            elif side == Side.SELL:
                if px < breach_px:
                    breached = True
            else:
                logging.error(f"blocked symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}, chore has "
                              f"unsupported side: {side}, px: {px}")
                breached = True
        return breached

    # Utility methods - ideally different file - not here
    @staticmethod
    def get_last_barter_reference_px(top_of_book: TopOfBook, side: Side, system_symbol: str,
                                    sym_overview) -> float | None:
        reference_px: float | None = None
        with MobileBookMutexManager(top_of_book):
            if not top_of_book.last_barter:
                # if its auction / SOD time - handling missing last barter by using reference_px as closing px instead
                logging.warning(f"generated {str(side)} chore, symbol: {system_symbol}; top_of_book.last_barter is found "
                                f"None, using closing px as reference px symbol_side_key: "
                                f"{get_symbol_side_key([(system_symbol, side)])};;;tob: {top_of_book}")
                if sym_overview is not None:
                    reference_px = sym_overview.closing_px
            else:
                reference_px = top_of_book.last_barter.px
            return reference_px

    @staticmethod
    def get_spread_in_bips(px1: float, px2: float) -> int:
        gap_in_bips = int(abs(px1 - px2) / ((px1 + px2) / 2) * 10000)
        return gap_in_bips

    @staticmethod
    def get_tick_size(system_symbol: str) -> float | None:
        # if we are here - tick-size was not found in symbol overview - compute - update - return
        if system_symbol.rfind('.') == -1:
            # assume this is CB leg
            return 0.001
        else:
            # this is EQT leg
            return 0.01

    @staticmethod
    def _get_px_by_max_level(system_symbol: str, side: Side, chore_limits: ChoreLimitsBaseModel,
                             mobile_book_container) -> float | None:
        px_by_max_level: float = 0

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
            logging.error(f"blocked generated chore, {system_symbol=}, {side=}, unable to find valid px"
                          f" based on {chore_limits.max_px_levels=} limit from available depths, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])};;;"
                          f"depths: {[str(market_depth) for market_depth in market_depths]}")
            return None
        return px_by_max_level

    @staticmethod
    def _get_tob_bid_n_ask_quote_px(tob: TopOfBook, side: Side, system_symbol: str) -> Tuple[int, int] | None:
        with MobileBookMutexManager(tob):
            if not (tob.ask_quote and tob.ask_quote.px and tob.bid_quote and tob.bid_quote.px):
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {str(side)} chore, symbol: {system_symbol}, side: {side} as tob"
                              f" has incomplete data, symbol_side_key: "
                              f"{get_symbol_side_key([(system_symbol, side)])};;;TOB: {tob}")
                return None     # None return blocks the chore from going further
            else:
                return tob.bid_quote.px, tob.ask_quote.px

    @staticmethod
    def get_breach_threshold_px(tob: TopOfBook, sym_ovrw_getter: Callable,
                                chore_limits: ChoreLimitsBaseModel, side: Side, system_symbol: str,
                                mobile_book_container, is_algo: bool = False) -> float | None:
        """
        Args:
            tob:
            sym_ovrw_getter:
            chore_limits:
            side:
            system_symbol:
            mobile_book_container:
            is_algo:
        Returns:
            min breach threshold and max breach threshold
        """
        breach_threshold_px: float | None = None  # None if returned blocks the chore from going further
        px_by_max_level = ChoreControl._get_px_by_max_level(system_symbol, side, chore_limits, mobile_book_container)
        if px_by_max_level is None:
            # _get_px_by_max_level logs error internally
            return None
        sym_ovrw = sym_ovrw_getter(system_symbol)
        last_barter_reference_px: float | None = ChoreControl.get_last_barter_reference_px(tob, side, system_symbol,
                                                                                         sym_ovrw)

        tick_size: float = sym_ovrw.tick_size if sym_ovrw.tick_size else ChoreControl.get_tick_size(system_symbol)
        if not tick_size:
            logging.error(f"blocked generated {str(side)} chore, tick size missing for: {system_symbol}, "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return None

        tob_quote_px_tuple = ChoreControl._get_tob_bid_n_ask_quote_px(tob, side, system_symbol)
        if tob_quote_px_tuple is None:
            return None     # error logged in _get_tob_bid_n_ask_quote_px
        bid_quote_px, ask_quote_px = tob_quote_px_tuple

        spread_in_bips: int | None = ChoreControl.get_spread_in_bips(ask_quote_px, bid_quote_px)

        max_px_deviation = chore_limits.max_px_deviation if not is_algo else chore_limits.max_px_deviation_algo

        # A basis point is 1/100th of a percent. For example, 50 basis points = 0.50%, and 100 basis points = 1%
        max_basis_points = chore_limits.max_basis_points if not is_algo else chore_limits.max_basis_points_algo
        if side == Side.BUY:
            aggressive_quote_px: float | None = ask_quote_px
            if not aggressive_quote_px:
                return None  # error logged in _get_aggressive_tob_ask_quote_px
            max_px_by_lt_deviation: float = last_barter_reference_px + (last_barter_reference_px / 100 * max_px_deviation)

            # BBBO is the Best Bid or Best Offer price, depending on which side of the market you're analyzing
            # 1 + (bps / 10,000): This factor adjusts the BBBO price by the given number of basis points
            # below same as: aggressive_quote.px * (1 + (max_basis_points / 10000))
            max_px_by_bbbo_basis_point: float = aggressive_quote_px + (aggressive_quote_px * (max_basis_points / 10000))

            breach_threshold_px = min(max_px_by_bbbo_basis_point, max_px_by_lt_deviation, px_by_max_level)
            # breach_threshold_px = min(max_px_by_bbbo_basis_point, max_px_by_lt_deviation)
            # implies don't fail price check if target price is within last_barter + 1 tick OR aggressive BBBO + 1 tick
            breach_threshold_px_by_tick_size: float
            if spread_in_bips and spread_in_bips <= ChoreControl.max_spread_in_bips:
                min_px_by_bbo_n_tick_size: float = aggressive_quote_px + tick_size
                min_px_by_last_barter_n_tick_size: float = last_barter_reference_px + tick_size
                min_px_by_tick_size = max(min_px_by_bbo_n_tick_size, min_px_by_last_barter_n_tick_size)
                breach_threshold_px_by_tick_size: float = max(min_px_by_tick_size, breach_threshold_px)
            else:
                breach_threshold_px_by_tick_size = breach_threshold_px

        else:  # side == Side.SELL
            aggressive_quote_px: float | None = bid_quote_px
            if not aggressive_quote_px:
                return None  # error logged in _get_aggressive_tob_ask_quote_px
            min_px_by_lt_deviation: float = last_barter_reference_px - (last_barter_reference_px / 100 * max_px_deviation)
            # below same as: aggressive_quote.px * (1 - (max_basis_points / 10000))
            min_px_by_bbbo_basis_point: float = aggressive_quote_px - (aggressive_quote_px * (max_basis_points / 10000))

            breach_threshold_px = max(min_px_by_bbbo_basis_point, min_px_by_lt_deviation, px_by_max_level)
            # breach_threshold_px = max(min_px_by_bbbo_basis_point, min_px_by_lt_deviation)
            # implies don't fail price check if target price is within last_barter - 1 tick OR aggressive BBBO - 1 tick
            breach_threshold_px_by_tick_size: float
            if spread_in_bips and spread_in_bips <= ChoreControl.max_spread_in_bips:
                max_px_by_bbo_n_tick_size: float = aggressive_quote_px - tick_size
                max_px_by_last_barter_n_tick_size: float = last_barter_reference_px - tick_size
                max_px_by_tick_size = min(max_px_by_bbo_n_tick_size, max_px_by_last_barter_n_tick_size)
                breach_threshold_px_by_tick_size: float = min(max_px_by_tick_size, breach_threshold_px)
            else:
                breach_threshold_px_by_tick_size = breach_threshold_px
        return breach_threshold_px_by_tick_size

    @staticmethod
    def _get_tob_last_barter_px(top_of_book: TopOfBook, side: Side) -> float | None:
        with MobileBookMutexManager(top_of_book):
            if top_of_book.last_barter is None or math.isclose(top_of_book.last_barter.px, 0):
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated chore, symbol: {top_of_book.symbol}, side: {side} as "
                              f"top_of_book.last_barter.px is none or 0, symbol_side_key: "
                              f" {get_symbol_side_key([(top_of_book.symbol, side)])}")
                return None
            return top_of_book.last_barter.px

    @staticmethod
    def get_breach_threshold_px_ext(top_of_book: TopOfBook, sym_ovrw_getter: Callable,
                                    chore_limits: ChoreLimitsBaseModel, side: Side, system_symbol: str,
                                    mobile_book_container, is_algo: bool = False) -> float | None:
        # TODO important - check and change reference px in cases where last px is not available
        last_barter_px = ChoreControl._get_tob_last_barter_px(top_of_book, side)
        if last_barter_px is None:
            return None  # error logged in _get_tob_last_barter_px

        if side != Side.BUY and side != Side.SELL:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated unsupported side chore, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return None  # None return blocks the chore from going further

        breach_threshold_px = ChoreControl.get_breach_threshold_px(top_of_book, sym_ovrw_getter, chore_limits, side,
                                                                   system_symbol, mobile_book_container, is_algo)
        return breach_threshold_px

    @staticmethod
    def check_px(top_of_book: TopOfBook, sym_ovrw_getter: Callable, chore_limits: ChoreLimitsBaseModel,
                 px: float, usd_px: float, qty: int, side: Side, system_symbol: str,
                 mobile_book_container, is_algo: bool = False) -> int:
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        if top_of_book:

            high_breach_px: float = ChoreControl.get_breach_threshold_px_ext(
                top_of_book, sym_ovrw_getter, chore_limits, Side.BUY, system_symbol, mobile_book_container, is_algo)
            low_breach_px: float = ChoreControl.get_breach_threshold_px_ext(
                top_of_book, sym_ovrw_getter, chore_limits, Side.SELL, system_symbol, mobile_book_container, is_algo)

            if high_breach_px is not None and low_breach_px is not None:
                high_breach: bool = ChoreControl.px_breached(high_breach_px, px, Side.BUY, system_symbol)
                low_breach: bool = ChoreControl.px_breached(low_breach_px, px, Side.SELL, system_symbol)
                if high_breach or low_breach:
                    ord_detail: str = (f"side: {side}, px: {px}, qty: {qty}, symbol_side_key: "
                                       f"{get_symbol_side_key([(system_symbol, side)])}")
                    if px > high_breach_px:
                        logging.error(f"blocked generated {side} chore, chore-{px=} > {high_breach_px=:.3f}; "
                                      f"{low_breach_px=:.3f}, {ord_detail=};;;{high_breach=}/{low_breach=}; "
                                      f"{top_of_book=}")
                        checks_passed |= ChoreControl.ORDER_CONTROL_ORDER_MAX_PX_FAIL
                    elif px < low_breach_px:
                        logging.error(f"blocked generated {side} chore, chore-{px=} < {low_breach_px=:.3f}; "
                                      f"{high_breach_px=:.3f}, {ord_detail=};;;{high_breach=}/{low_breach=}; "
                                      f"{top_of_book=}")
                        checks_passed |= ChoreControl.ORDER_CONTROL_ORDER_MIN_PX_FAIL
                    else:
                        logging.error(f"Unexpected condition, chore_px: {px} not found in breach but found "
                                      f"{high_breach=} and {low_breach=}, with {high_breach_px=:.3f} / "
                                      f"{low_breach_px=:.3f}; blocked generated chore, {ord_detail=};;;{top_of_book=}")
                        checks_passed |= ChoreControl.ORDER_CONTROL_EXCEPTION_FAIL
                # else not required, chore is good to go further
            else:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                high_breach_px_str = f"{high_breach_px=:.3f}" if high_breach_px else f"{high_breach_px=}"
                low_breach_px_str = f"{low_breach_px=:.3f}" if low_breach_px else f"{low_breach_px=}"
                logging.error(f"blocked generated chore, {high_breach_px_str} / {low_breach_px_str} is returned None "
                              f"from get_breach_threshold_px for symbol_side_key: "
                              f"{get_symbol_side_key([(system_symbol, side)])}, {px=}, {usd_px=};;;{top_of_book=}")
                checks_passed |= ChoreControl.ORDER_CONTROL_NO_BREACH_PX_FAIL
        else:
            logging.error(f"blocked generated chore, unable to conduct px checks: top_of_book is sent None for "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            checks_passed |= ChoreControl.ORDER_CONTROL_NO_TOB_FAIL
        return checks_passed


if __name__ == "__main__":
    print(ChoreControl.ORDER_CONTROL_INIT_AS_FAIL)
    print(hex(256))
    print(hex(16384))
    print(hex(8192))
    chore_check: ChoreControl = ChoreControl()
