from enum import Enum
from typing import Final
import logging

from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import get_symbol_side_key


class OrderControl:
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
    def check_min_order_notional(cls, order_limits, order_usd_notional, system_symbol, side):
        # min order notional is to be a order opportunity condition instead of order check
        if round(order_limits.min_order_notional) > round(order_usd_notional):
            logging.error(f"blocked order_opportunity < min_order_notional limit: "
                          f"{order_usd_notional} < {order_limits.min_order_notional}, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            return cls.ORDER_CONTROL_MIN_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_order_notional(cls, order_limits, order_usd_notional, system_symbol, side):
        if order_limits.max_order_notional < order_usd_notional:
            logging.error(f"blocked generated order, breaches max_order_notional limit, expected less than: "
                          f"{order_limits.max_order_notional}, found: {order_usd_notional}, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            # err_dict["max_order_notional"] = f"{int(order_limits.max_order_notional)}"
            return OrderControl.ORDER_CONTROL_MAX_ORDER_NOTIONAL_FAIL
        else:
            return cls.ORDER_CONTROL_SUCCESS

    @classmethod
    def check_max_order_qty(cls, order_limits, qty, system_symbol, side):
        if order_limits.max_order_qty < qty:
            logging.error(f"blocked generated order, breaches max_order_qty limit, expected less than: "
                          f"{order_limits.max_order_qty}, found: {qty}, symbol_side_key: "
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
