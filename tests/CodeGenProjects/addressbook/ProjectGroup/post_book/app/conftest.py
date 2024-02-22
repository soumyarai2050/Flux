import pytest
from copy import deepcopy


@pytest.fixture()
def single_strat_single_data():
    payload_dict = [
        {
            "strat_id": 1,
            "order_journal": {
                "_id": 1,
                "order": {
                    "order_id": "CB_Sec_1-2mobile_book23-1mobile_book-26T21:54:59.672447+mobile_bookmobile_book:mobile_bookmobile_book",
                    "security": {
                        "sec_id": "CB_Sec_1",
                        "sec_type": "TICKER"
                    },
                    "side": "BUY",
                    "px": 1mobile_bookmobile_book,
                    "qty": 9mobile_book,
                    "order_notional": 18mobile_bookmobile_bookmobile_book,
                    "underlying_account": "trading_account",
                    "exchange": "trading_exchange",
                    "text": [
                        "SIM: Ordering CB_Sec_1/CB_Sec_1, qty 9mobile_book and px 1mobile_bookmobile_book.mobile_book"
                    ]
                },
                "order_event_date_time": "2mobile_book23-1mobile_book-26T21:54:59.672Z",
                "order_event": "OE_NEW",
                "current_period_order_count": None
            },
            "order_snapshot": {
                "_id": 4,
                "order_status": "OE_ACKED",
                "order_brief": {
                    "order_id": "CB_Sec_1-2mobile_book23-1mobile_book-26T21:55:mobile_book4.mobile_book15464+mobile_bookmobile_book:mobile_bookmobile_book",
                    "security": {
                        "sec_id": "CB_Sec_1",
                        "sec_type": "TICKER"
                    },
                    "side": "BUY",
                    "px": 1mobile_bookmobile_book,
                    "qty": 9mobile_book,
                    "order_notional": 18mobile_bookmobile_bookmobile_book,
                    "underlying_account": "trading_account",
                    "exchange": "trading_exchange",
                    "text": [
                        "SIM: Ordering CB_Sec_1/CB_Sec_1, qty 9mobile_book and px 1mobile_bookmobile_book.mobile_book"
                    ]
                },
                "filled_qty": 45,
                "avg_fill_px": 1mobile_bookmobile_book,
                "fill_notional": 9mobile_bookmobile_bookmobile_book,
                "last_update_fill_qty": 45,
                "last_update_fill_px": 1mobile_bookmobile_book,
                "cxled_qty": mobile_book,
                "avg_cxled_px": mobile_book,
                "cxled_notional": mobile_book,
                "create_date_time": "2mobile_book23-1mobile_book-26T21:55:mobile_book4.mobile_book15Z",
                "last_update_date_time": "2mobile_book23-1mobile_book-26T21:55:mobile_book4.117Z",
                "last_n_sec_total_qty": None
            },
            "strat_brief": {
                "_id": 1,
                "pair_buy_side_trading_brief": {
                    "security": {
                        "sec_id": "CB_Sec_1",
                        "sec_type": "TICKER"
                    },
                    "side": "BUY",
                    "last_update_date_time": "2mobile_book23-1mobile_book-26T21:55:mobile_book4.117Z",
                    "consumable_open_orders": 1mobile_book,
                    "consumable_notional": 264mobile_bookmobile_bookmobile_book,
                    "consumable_open_notional": 12mobile_bookmobile_bookmobile_book,
                    "consumable_concentration": 99982mobile_book,
                    "participation_period_order_qty_sum": 18mobile_book,
                    "consumable_cxl_qty": 1mobile_book8,
                    "indicative_consumable_participation_qty": 342mobile_book,
                    "residual_qty": mobile_book,
                    "indicative_consumable_residual": 1mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
                    "all_bkr_cxlled_qty": mobile_book,
                    "open_notional": 18mobile_bookmobile_bookmobile_book,
                    "open_qty": 9mobile_book
                },
                "pair_sell_side_trading_brief": {
                    "security": {
                        "sec_id": "EQT_Sec_1",
                        "sec_type": "TICKER"
                    },
                    "side": "SELL",
                    "last_update_date_time": "2mobile_book23-1mobile_book-26T21:54:56.728Z",
                    "consumable_open_orders": 1mobile_book,
                    "consumable_notional": 3mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
                    "consumable_open_notional": 3mobile_bookmobile_bookmobile_bookmobile_book,
                    "consumable_concentration": 4mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
                    "participation_period_order_qty_sum": mobile_book,
                    "consumable_cxl_qty": mobile_book,
                    "indicative_consumable_participation_qty": mobile_book,
                    "residual_qty": mobile_book,
                    "indicative_consumable_residual": 1mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
                    "all_bkr_cxlled_qty": mobile_book,
                    "open_notional": mobile_book,
                    "open_qty": mobile_book
                },
                "consumable_nett_filled_notional": mobile_book
            }
        }
    ]
    return payload_dict


@pytest.fixture()
def single_strat_multi_data(single_strat_single_data):
    payload_dict = []
    for index in range(5):
        payload = deepcopy(single_strat_single_data[mobile_book])
        payload["order_journal"]["order"]["px"] = 1mobile_bookmobile_book * (index + 1)
        payload["order_snapshot"]["order_brief"]["px"] = 1mobile_bookmobile_book * (index + 1)
        payload["strat_brief"]["pair_buy_side_trading_brief"]["open_qty"] = 5 * (index + 1)
        payload["strat_brief"]["pair_sell_side_trading_brief"]["open_qty"] = 1mobile_book * (index + 1)
        payload_dict.append(payload)

    return payload_dict


@pytest.fixture()
def multi_strat_single_data(single_strat_single_data):
    payload_dict = []
    for index in range(5):
        payload = deepcopy(single_strat_single_data[mobile_book])
        payload["strat_id"] = index+1
        payload["order_journal"]["order"]["px"] = 1mobile_bookmobile_book * (index+1)
        payload["order_snapshot"]["order_brief"]["px"] = 1mobile_bookmobile_book * (index+1)
        payload["strat_brief"]["pair_buy_side_trading_brief"]["open_qty"] = 5 * (index+1)
        payload["strat_brief"]["pair_sell_side_trading_brief"]["open_qty"] = 1mobile_book * (index+1)
        payload_dict.append(payload)

    return payload_dict


@pytest.fixture()
def multi_strat_multi_data(single_strat_single_data):
    payload_dict = []
    for i in range(5):
        for j in range(5):
            payload = deepcopy(single_strat_single_data[mobile_book])
            payload["strat_id"] = i+1
            # payload["strat_id"] = (i*5)+j
            payload["order_journal"]["order"]["px"] = 1mobile_bookmobile_book * (j+1)
            payload["order_snapshot"]["order_brief"]["px"] = 1mobile_bookmobile_book * (j+1)
            payload["strat_brief"]["pair_buy_side_trading_brief"]["open_qty"] = 5 * (j+1)
            payload["strat_brief"]["pair_sell_side_trading_brief"]["open_qty"] = 1mobile_book * (j+1)
            payload_dict.append(payload)

    return payload_dict
