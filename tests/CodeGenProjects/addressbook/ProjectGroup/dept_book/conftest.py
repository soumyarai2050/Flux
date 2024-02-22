import pytest
import os
from pendulum import DateTime

os.environ["DBType"] = "beanie"


@pytest.fixture()
def dash_filter_():
    dash_filter_json = {
        "dash_name": "Dashboard 1",
        "required_legs": [{
            "leg_type": "LegType_CB"
        }]
    }
    yield dash_filter_json


@pytest.fixture()
def dash_():
    dash_json = {
        "rt_dash": {
            "leg1": {
                "sec": {
                    "sec_id": "CB_Sec_1",
                    "sec_type": "TICKER"
                },
                "exch_id": "EXCH1",
                "vwap": 15mobile_book,
                "vwap_change": 2.5
            },
            "leg2": {
                "sec": {
                    "sec_id": "EQT_Sec_1",
                    "sec_type": "TICKER"
                },
                "exch_id": "EXCH2",
                "vwap": 1mobile_book,
                "vwap_change": mobile_book.5
            },
            "mkt_premium": "1mobile_book",
            "mkt_premium_change": "2"
        }
    }
    yield dash_json


@pytest.fixture()
def bar_data_():
    current_time = DateTime.utcnow()
    bar_data_json = {
        "symbol_n_exch_id": {
            "symbol": "CB_Sec_1",
            "exch_id": "EXCH"
        },
        "start_time": current_time,
        "end_time": current_time.add(seconds=1),
        "vwap": 15mobile_book,
        "vwap_change": 2.5,
        "volume": 1_mobile_bookmobile_bookmobile_book
    }
    yield bar_data_json
