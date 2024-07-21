import pytest
from copy import deepcopy


@pytest.fixture()
def single_strat_single_data():
    payload_dict = [
        {
            "strat_id": 1,
            "chore_journal": {
                "_id": 1,
                "chore": {
                    "chore_id": "CB_Sec_1-2023-10-26T21:54:59.672447+00:00",
                    "security": {
                        "sec_id": "CB_Sec_1",
                        "sec_id_source": "TICKER"
                    },
                    "side": "BUY",
                    "px": 100,
                    "qty": 90,
                    "chore_notional": 18000,
                    "underlying_account": "bartering_account",
                    "exchange": "bartering_exchange",
                    "text": [
                        "SIM: Choreing CB_Sec_1/CB_Sec_1, qty 90 and px 100.0"
                    ]
                },
                "chore_event_date_time": "2023-10-26T21:54:59.672Z",
                "chore_event": "OE_NEW",
                "current_period_chore_count": None
            },
            "chore_snapshot": {
                "_id": 4,
                "chore_status": "OE_ACKED",
                "chore_brief": {
                    "chore_id": "CB_Sec_1-2023-10-26T21:55:04.015464+00:00",
                    "security": {
                        "sec_id": "CB_Sec_1",
                        "sec_id_source": "TICKER"
                    },
                    "side": "BUY",
                    "px": 100,
                    "qty": 90,
                    "chore_notional": 18000,
                    "underlying_account": "bartering_account",
                    "exchange": "bartering_exchange",
                    "text": [
                        "SIM: Choreing CB_Sec_1/CB_Sec_1, qty 90 and px 100.0"
                    ]
                },
                "filled_qty": 45,
                "avg_fill_px": 100,
                "fill_notional": 9000,
                "last_update_fill_qty": 45,
                "last_update_fill_px": 100,
                "cxled_qty": 0,
                "avg_cxled_px": 0,
                "cxled_notional": 0,
                "create_date_time": "2023-10-26T21:55:04.015Z",
                "last_update_date_time": "2023-10-26T21:55:04.117Z",
                "last_n_sec_total_qty": None
            },
            "strat_brief": {
                "_id": 1,
                "pair_buy_side_bartering_brief": {
                    "security": {
                        "sec_id": "CB_Sec_1",
                        "sec_id_source": "TICKER"
                    },
                    "side": "BUY",
                    "last_update_date_time": "2023-10-26T21:55:04.117Z",
                    "consumable_open_chores": 10,
                    "consumable_notional": 264000,
                    "consumable_open_notional": 12000,
                    "consumable_concentration": 999820,
                    "participation_period_chore_qty_sum": 180,
                    "consumable_cxl_qty": 108,
                    "indicative_consumable_participation_qty": 3420,
                    "residual_qty": 0,
                    "indicative_consumable_residual": 100000,
                    "all_bkr_cxlled_qty": 0,
                    "open_notional": 18000,
                    "open_qty": 90
                },
                "pair_sell_side_bartering_brief": {
                    "security": {
                        "sec_id": "EQT_Sec_1",
                        "sec_id_source": "TICKER"
                    },
                    "side": "SELL",
                    "last_update_date_time": "2023-10-26T21:54:56.728Z",
                    "consumable_open_chores": 10,
                    "consumable_notional": 300000,
                    "consumable_open_notional": 30000,
                    "consumable_concentration": 400000,
                    "participation_period_chore_qty_sum": 0,
                    "consumable_cxl_qty": 0,
                    "indicative_consumable_participation_qty": 0,
                    "residual_qty": 0,
                    "indicative_consumable_residual": 100000,
                    "all_bkr_cxlled_qty": 0,
                    "open_notional": 0,
                    "open_qty": 0
                },
                "consumable_nett_filled_notional": 0
            }
        }
    ]
    return payload_dict


@pytest.fixture()
def single_strat_multi_data(single_strat_single_data):
    payload_dict = []
    for index in range(5):
        payload = deepcopy(single_strat_single_data[0])
        payload["chore_journal"]["chore"]["px"] = 100 * (index + 1)
        payload["chore_snapshot"]["chore_brief"]["px"] = 100 * (index + 1)
        payload["strat_brief"]["pair_buy_side_bartering_brief"]["open_qty"] = 5 * (index + 1)
        payload["strat_brief"]["pair_sell_side_bartering_brief"]["open_qty"] = 10 * (index + 1)
        payload_dict.append(payload)

    return payload_dict


@pytest.fixture()
def multi_strat_single_data(single_strat_single_data):
    payload_dict = []
    for index in range(5):
        payload = deepcopy(single_strat_single_data[0])
        payload["strat_id"] = index+1
        payload["chore_journal"]["chore"]["px"] = 100 * (index+1)
        payload["chore_snapshot"]["chore_brief"]["px"] = 100 * (index+1)
        payload["strat_brief"]["pair_buy_side_bartering_brief"]["open_qty"] = 5 * (index+1)
        payload["strat_brief"]["pair_sell_side_bartering_brief"]["open_qty"] = 10 * (index+1)
        payload_dict.append(payload)

    return payload_dict


@pytest.fixture()
def multi_strat_multi_data(single_strat_single_data):
    payload_dict = []
    for i in range(5):
        for j in range(5):
            payload = deepcopy(single_strat_single_data[0])
            payload["strat_id"] = i+1
            # payload["strat_id"] = (i*5)+j
            payload["chore_journal"]["chore"]["px"] = 100 * (j+1)
            payload["chore_snapshot"]["chore_brief"]["px"] = 100 * (j+1)
            payload["strat_brief"]["pair_buy_side_bartering_brief"]["open_qty"] = 5 * (j+1)
            payload["strat_brief"]["pair_sell_side_bartering_brief"]["open_qty"] = 10 * (j+1)
            payload_dict.append(payload)

    return payload_dict
