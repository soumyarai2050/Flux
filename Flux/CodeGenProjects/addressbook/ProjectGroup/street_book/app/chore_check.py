import random

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import get_symbol_side_key


class ChoreControl:
    ORDER_CONTROL_SUCCESS: Final[int] = 0x0
    ORDER_CONTROL_PLACE_NEW_ORDER_FAIL: Final[int] = 0x1
    ORDER_CONTROL_EXCEPTION_FAIL: Final[int] = 0x2
    ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL: Final[int] = 0x4
    ORDER_CONTROL_UNSUPPORTED_SIDE_FAIL: Final[int] = 0x8
    ORDER_CONTROL_NO_BREACH_PX_FAIL: Final[int] = 0x10
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
    ORDER_CONTROL_BUY_ORDER_MAX_PX_FAIL: Final[int] = 0x20000
    ORDER_CONTROL_SELL_ORDER_MIN_PX_FAIL: Final[int] = 0x40000
    ORDER_CONTROL_NETT_FILLED_NOTIONAL_FAIL: Final[int] = 0x80000
    ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL: Final[int] = 0x100000
    ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL: Final[int] = 0x200000
    ORDER_CONTROL_INIT_AS_FAIL = 0x400000
    ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL: Final[int] = 0x800000
    ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL: Final[int] = 0x1000000

    @classmethod
    def check_min_chore_notional_normal(cls, chore_limits: ChoreLimitsBaseModel, chore_usd_notional: float,
                                        system_symbol: str, side: Side):
        # min chore notional is to be an chore opportunity condition instead of chore check
        if round(chore_limits.min_chore_notional) > round(chore_usd_notional):
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked chore_opportunity < min_chore_notional limit: "
                          f"{chore_usd_notional} < {chore_limits.min_chore_notional}, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return cls.ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_min_chore_notional_relaxed(cls, chore_limits: ChoreLimitsBaseModel, chore_usd_notional: float,
                                         system_symbol: str, side: Side):
        min_chore_notional_relaxed = random.randint(int(chore_limits.min_chore_notional),
                                                    int(chore_limits.min_chore_notional+chore_limits.
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
    def check_min_chore_notional_aggressive(cls, chore_limits: ChoreLimitsBaseModel, chore_usd_notional: float,
                                            system_symbol: str, side: Side):
        # todo: currently same as normal - needs to be impl
        # min chore notional is to be an chore opportunity condition instead of chore check
        return cls.check_min_chore_notional_normal(chore_limits, chore_usd_notional, system_symbol, side)

    @classmethod
    def check_min_chore_notional(cls, pair_strat: PairStrat, chore_limits: ChoreLimitsBaseModel, chore_usd_notional: float,
                                 system_symbol: str, side: Side):
        if pair_strat.pair_strat_params.strat_mode == StratMode.StratMode_Aggressive:
            # min chore notional is to be an chore opportunity condition instead of chore check
            checks_passed_ = ChoreControl.check_min_chore_notional_aggressive(chore_limits, chore_usd_notional,
                                                                              system_symbol, side)
        elif pair_strat.pair_strat_params.strat_mode == StratMode.StratMode_Relaxed:
            checks_passed_ = ChoreControl.check_min_chore_notional_relaxed(chore_limits, chore_usd_notional,
                                                                           system_symbol, side)
        else:
            checks_passed_ = ChoreControl.check_min_chore_notional_normal(chore_limits, chore_usd_notional,
                                                                          system_symbol, side)
        return checks_passed_

    @classmethod
    def check_max_chore_notional(cls, chore_limits: ChoreLimitsBaseModel, chore_usd_notional: float,
                                 system_symbol: str, side: Side):
        if chore_limits.max_chore_notional < chore_usd_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, breaches max_chore_notional limit, expected less than: "
                          f"{chore_limits.max_chore_notional}, found: {chore_usd_notional = }, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            # err_dict["max_chore_notional"] = f"{int(chore_limits.max_chore_notional)}"
            return ChoreControl.ORDER_CONTROL_MAX_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_chore_qty(cls, chore_limits: ChoreLimitsBaseModel, qty: int, system_symbol: str, side: Side):
        if chore_limits.max_chore_qty < qty:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated chore, breaches max_chore_qty limit, expected less than: "
                          f"{chore_limits.max_chore_qty}, found: {qty = }, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return ChoreControl.ORDER_CONTROL_MAX_ORDER_QTY_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS


if __name__ == "__main__":
    print(ChoreControl.ORDER_CONTROL_INIT_AS_FAIL)
    print(hex(256))
    print(hex(16384))
    print(hex(8192))
    chore_check: ChoreControl = ChoreControl()
