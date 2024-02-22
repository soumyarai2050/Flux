import random

from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.street_book.app.street_book_service_helper import get_symbol_side_key


class OrderControl:
    ORDER_CONTROL_SUCCESS: Final[int] = mobile_bookxmobile_book
    ORDER_CONTROL_PLACE_NEW_ORDER_FAIL: Final[int] = mobile_bookx1
    ORDER_CONTROL_EXCEPTION_FAIL: Final[int] = mobile_bookx2
    ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL: Final[int] = mobile_bookx4
    ORDER_CONTROL_UNSUPPORTED_SIDE_FAIL: Final[int] = mobile_bookx8
    ORDER_CONTROL_NO_BREACH_PX_FAIL: Final[int] = mobile_bookx1mobile_book
    ORDER_CONTROL_NO_TOB_FAIL: Final[int] = mobile_bookx2mobile_book

    ORDER_CONTROL_EXTRACT_AVAILABILITY_FAIL: Final[int] = mobile_bookx4mobile_book
    ORDER_CONTROL_CHECK_UNACK_FAIL: Final[int] = mobile_bookx8mobile_book
    ORDER_CONTROL_LIMIT_UP_FAIL: Final[int] = mobile_bookx1mobile_bookmobile_book
    ORDER_CONTROL_LIMIT_DOWN_FAIL: Final[int] = mobile_bookx2mobile_bookmobile_book
    ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL: Final[int] = mobile_bookx4mobile_bookmobile_book
    ORDER_CONTROL_MAX_ORDER_NOTIONAL_FAIL: Final[int] = mobile_bookx8mobile_bookmobile_book
    ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL: Final[int] = mobile_bookx1mobile_bookmobile_bookmobile_book
    ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL: Final[int] = mobile_bookx2mobile_bookmobile_bookmobile_book
    ORDER_CONTROL_UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL: Final[int] = mobile_bookx4mobile_bookmobile_bookmobile_book
    ORDER_CONTROL_MAX_CONCENTRATION_FAIL: Final[int] = mobile_bookx8mobile_bookmobile_bookmobile_book
    ORDER_CONTROL_MAX_ORDER_QTY_FAIL: Final[int] = mobile_bookx1mobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_BUY_ORDER_MAX_PX_FAIL: Final[int] = mobile_bookx2mobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_SELL_ORDER_MIN_PX_FAIL: Final[int] = mobile_bookx4mobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_NETT_FILLED_NOTIONAL_FAIL: Final[int] = mobile_bookx8mobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL: Final[int] = mobile_bookx1mobile_bookmobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL: Final[int] = mobile_bookx2mobile_bookmobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_INIT_AS_FAIL = mobile_bookx4mobile_bookmobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL: Final[int] = mobile_bookx8mobile_bookmobile_bookmobile_bookmobile_bookmobile_book
    ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL: Final[int] = mobile_bookx1mobile_bookmobile_bookmobile_bookmobile_bookmobile_bookmobile_book

    @classmethod
    def check_min_order_notional_normal(cls, order_limits: OrderLimits, order_usd_notional: float,
                                        system_symbol: str, side: Side):
        # min order notional is to be an order opportunity condition instead of order check
        if round(order_limits.min_order_notional) > round(order_usd_notional):
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked order_opportunity < min_order_notional limit: "
                          f"{order_usd_notional} < {order_limits.min_order_notional}, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return cls.ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_min_order_notional_relaxed(cls, order_limits: OrderLimits, order_usd_notional: float,
                                         system_symbol: str, side: Side):
        min_order_notional_relaxed = random.randint(int(order_limits.min_order_notional),
                                                    int(order_limits.min_order_notional+order_limits.
                                                        min_order_notional_allowance))

        # min order notional is to be an order opportunity condition instead of order check
        if min_order_notional_relaxed > round(order_usd_notional):
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked order_opportunity < min_order_notional_relaxed limit: "
                          f"{order_usd_notional} < {min_order_notional_relaxed}, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return cls.ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_min_order_notional_aggressive(cls, order_limits: OrderLimits, order_usd_notional: float,
                                            system_symbol: str, side: Side):
        # todo: currently same as normal - needs to be impl
        # min order notional is to be an order opportunity condition instead of order check
        return cls.check_min_order_notional_normal(order_limits, order_usd_notional, system_symbol, side)

    @classmethod
    def check_min_order_notional(cls, pair_strat: PairStrat, order_limits: OrderLimits, order_usd_notional: float,
                                 system_symbol: str, side: Side):
        if pair_strat.pair_strat_params.strat_mode == StratMode.StratMode_Aggressive:
            # min order notional is to be an order opportunity condition instead of order check
            checks_passed_ = OrderControl.check_min_order_notional_aggressive(order_limits, order_usd_notional,
                                                                              system_symbol, side)
        elif pair_strat.pair_strat_params.strat_mode == StratMode.StratMode_Relaxed:
            checks_passed_ = OrderControl.check_min_order_notional_relaxed(order_limits, order_usd_notional,
                                                                           system_symbol, side)
        else:
            checks_passed_ = OrderControl.check_min_order_notional_normal(order_limits, order_usd_notional,
                                                                          system_symbol, side)
        return checks_passed_

    @classmethod
    def check_max_order_notional(cls, order_limits: OrderLimits, order_usd_notional: float,
                                 system_symbol: str, side: Side):
        if order_limits.max_order_notional < order_usd_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated order, breaches max_order_notional limit, expected less than: "
                          f"{order_limits.max_order_notional}, found: {order_usd_notional = }, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            # err_dict["max_order_notional"] = f"{int(order_limits.max_order_notional)}"
            return OrderControl.ORDER_CONTROL_MAX_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_order_qty(cls, order_limits: OrderLimits, qty: int, system_symbol: str, side: Side):
        if order_limits.max_order_qty < qty:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated order, breaches max_order_qty limit, expected less than: "
                          f"{order_limits.max_order_qty}, found: {qty = }, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return OrderControl.ORDER_CONTROL_MAX_ORDER_QTY_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS


if __name__ == "__main__":
    print(OrderControl.ORDER_CONTROL_INIT_AS_FAIL)
    print(hex(256))
    print(hex(16384))
    print(hex(8192))
    order_check: OrderControl = OrderControl()
