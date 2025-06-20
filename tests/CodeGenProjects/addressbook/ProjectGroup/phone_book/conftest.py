import time

import pendulum
import pytest
import os
import copy
import polars

os.environ["ModelType"] = "msgspec"

# Project Imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.ORMModel.log_book_service_model_imports import *
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager
from tests.CodeGenProjects.AddressBook.ProjectGroup.conftest import *

TRADING_ACCOUNT: Final[str] = "TRADING_ACCOUNT_ZERODHA_BKR"
TRADING_EXCHANGE: Final[str] = "ZERODHA"


@pytest.fixture()
def max_loop_count_per_side():
    max_loop_count_per_side = 10
    return max_loop_count_per_side


@pytest.fixture()
def refresh_sec_update_fixture() -> int:
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    min_refresh_interval = 5
    executor_config_dict["min_refresh_interval"] = min_refresh_interval
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))

    yield min_refresh_interval
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


@pytest.fixture()
def top_of_book_list_():
    leg1_last_barter_px, leg2_last_barter_px = get_both_side_last_barter_px()
    input_data = [
        {
            "symbol": "Type1_Sec_1",
            "bid_quote": {
                "px": 110,
                "qty": 20,
                "last_update_date_time": "2023-02-13T20:30:33.165Z"
            },
            "ask_quote": {
                "px": 120,
                "qty": 40,
                "last_update_date_time": "2023-02-13T20:30:31.165Z"
            },
            "last_barter": {
                "px": leg1_last_barter_px,
                "qty": 150,
                "last_update_date_time": "2023-02-13T20:30:35.165Z"
            },
            "total_bartering_security_size": 100,
            "market_barter_volume": [
                {
                    "participation_period_last_barter_qty_sum": 90,
                    "applicable_period_seconds": 180
                }
            ],
            "last_update_date_time": "2023-02-13T20:30:34.165Z"
        },
        {
            "symbol": "Type2_Sec_1",
            "bid_quote": {
                "px": 110,
                "qty": 20,
                "last_update_date_time": "2023-02-13T20:30:33.165Z"
            },
            "ask_quote": {
                "px": 120,
                "qty": 40,
                "last_update_date_time": "2023-02-13T20:30:31.165Z"
            },
            "last_barter": {
                "px": leg2_last_barter_px,
                "qty": 150,
                "last_update_date_time": "2023-02-13T20:30:35.165Z"
            },
            "total_bartering_security_size": 100,
            "market_barter_volume": [
                {
                    "participation_period_last_barter_qty_sum": 90,
                    "applicable_period_seconds": 180
                }
            ],
            "last_update_date_time": "2023-02-13T20:30:34.165Z"
        }
    ]
    yield input_data


@pytest.fixture()
def last_barter_fixture_list():
    input_data = []
    for index, symbol_n_px in enumerate([("Type1_Sec_1", 116), ("Type2_Sec_1", 117)]):
        symbol, px = symbol_n_px
        input_data.extend([
            {
                "symbol_n_exch_id": {
                    "symbol": symbol,
                    "exch_id": "Exch"
                },
                "exch_time": get_utc_date_time(),
                "arrival_time": get_utc_date_time(),
                "px": px,
                "qty": 150,
                "market_barter_volume": {
                    "participation_period_last_barter_qty_sum": 1000,
                    "applicable_period_seconds": 180
                }
            }
        ])
    yield input_data


def empty_pair_side_bartering_brief_obj(symbol: str, side: str, sec_id_source: str | None = SecurityIdSource.TICKER):
    return PairSideBarteringBriefBaseModel.from_dict({
        "security": {
          "sec_id": symbol,
          "sec_id_source": sec_id_source
        },
        "side": side,
        "last_update_date_time": DateTime.utcnow(),
        "consumable_open_chores": 0,
        "consumable_notional": 0,
        "consumable_open_notional": 0,
        "consumable_concentration": 0,
        "participation_period_chore_qty_sum": 0,
        "consumable_cxl_qty": 0,
        "indicative_consumable_participation_qty": 0,
        "residual_qty": 0,
        "indicative_consumable_residual": 0,
        "all_bkr_cxlled_qty": 0,
        "open_notional": 0,
        "open_qty": 0
    })


@pytest.fixture()
def expected_plan_brief_(pair_securities_with_sides_):
    pair_buy_side_bartering_brief = empty_pair_side_bartering_brief_obj(pair_securities_with_sides_["security1"]["sec_id"],
                                                                    pair_securities_with_sides_["side1"])
    pair_sell_side_bartering_brief = empty_pair_side_bartering_brief_obj(pair_securities_with_sides_["security2"]["sec_id"],
                                                                     pair_securities_with_sides_["side2"])
    yield PlanBriefBaseModel.from_kwargs(pair_buy_side_bartering_brief=pair_buy_side_bartering_brief,
                                          pair_sell_side_bartering_brief=pair_sell_side_bartering_brief,
                                          consumable_nett_filled_notional=160_000)


@pytest.fixture()
def expected_symbol_side_snapshot_():
    yield [
        SymbolSideSnapshotBaseModel.from_dict({
            "security": {
              "sec_id": "Type1_Sec_1",
              "sec_id_source": SecurityIdSource.TICKER
            },
            "side": "BUY",
            "avg_px": 0,
            "total_qty": 0,
            "total_filled_qty": 0,
            "avg_fill_px": 0,
            "total_fill_notional": 0,
            "last_update_fill_qty": 0,
            "last_update_fill_px": 0,
            "total_cxled_qty": 0,
            "avg_cxled_px": 0,
            "total_cxled_notional": 0,
            "last_update_date_time": "2023-02-13T20:30:35.165Z",
            "chore_count": 0
        }),
        SymbolSideSnapshotBaseModel.from_dict({
            "security": {
                "sec_id": "Type2_Sec_1",
                "sec_id_source": SecurityIdSource.TICKER
            },
            "side": "SELL",
            "avg_px": 0,
            "total_qty": 0,
            "total_filled_qty": 0,
            "avg_fill_px": 0,
            "total_fill_notional": 0,
            "last_update_fill_qty": 0,
            "last_update_fill_px": 0,
            "total_cxled_qty": 0,
            "avg_cxled_px": 0,
            "total_cxled_notional": 0,
            "last_update_date_time": "2023-02-13T20:30:36.165Z",
            "chore_count": 0
        })
    ]


@pytest.fixture()
def buy_chore_(pair_securities_with_sides_):
    yield ChoreLedgerBaseModel.from_dict({
        "chore": {
            "chore_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 100,
            "qty": 90,
            "chore_notional": 0,
            "underlying_account": TRADING_ACCOUNT,
            "text": [
              "test_string"
            ]
        },
        "chore_event_date_time": DateTime.utcnow(),
        "chore_event": "OE_NEW"
    })


@pytest.fixture()
def expected_buy_chore_snapshot_(pair_securities_with_sides_):
    yield ChoreSnapshotBaseModel.from_dict({
        "chore_brief": {
            "chore_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "bartering_security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 0,
            "qty": 0,
            "chore_notional": 0,
            "underlying_account": TRADING_ACCOUNT,
            "text": [],
            "exchange": TRADING_EXCHANGE
        },
        "filled_qty": 0,
        "avg_fill_px": 0,
        "fill_notional": 0,
        "last_update_fill_qty": 0,
        "last_update_fill_px": 0,
        "total_amend_up_qty": 0,
        "total_amend_dn_qty": 0,
        "cxled_qty": 0,
        "avg_cxled_px": 0,
        "cxled_notional": 0,
        "last_lapsed_qty": 0,
        "total_lapsed_qty": 0,
        "total_amd_rej_qty": None,
        "pending_amend_dn_qty": 0,
        "pending_amend_dn_px": 0,
        "pending_amend_up_qty": 0,
        "pending_amend_up_px": 0,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "chore_status": "OE_UNACK"
    })


@pytest.fixture()
def buy_fill_ledger_(pair_securities_with_sides_):
    yield DealsLedgerBaseModel.from_dict({
        "chore_id": "O1",
        "fill_px": 90,
        "fill_qty": 50,
        "fill_notional": 0,
        "fill_symbol": pair_securities_with_sides_["security1"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side1"],
        "underlying_account": TRADING_ACCOUNT,
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F1"
    })


@pytest.fixture()
def chore_cxl_request(email_book_service_web_client_, buy_chore_):
    placed_chore_ack_obj = copy.deepcopy(buy_chore_)
    placed_chore_ack_obj.chore_event = "OE_CXL"

    created_chore_ledger_obj = \
        email_book_service_web_client_.create_chore_ledger_client(placed_chore_ack_obj)

    yield created_chore_ledger_obj


@pytest.fixture()
def sell_chore_(pair_securities_with_sides_):
    yield ChoreLedgerBaseModel.from_dict({
        "chore": {
            "chore_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 110,
            "qty": 70,
            "chore_notional": 0,
            "underlying_account": TRADING_ACCOUNT,
            "text": [
              "test_string"
            ]
        },
        "chore_event_date_time": DateTime.utcnow(),
        "chore_event": "OE_NEW"
    })


@pytest.fixture()
def expected_sell_chore_snapshot_(pair_securities_with_sides_):
    yield ChoreSnapshotBaseModel.from_dict({
        "chore_brief": {
            "chore_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "bartering_security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 0,
            "qty": 0,
            "chore_notional": 0,
            "underlying_account": TRADING_ACCOUNT,
            "text": [],
            "exchange": TRADING_EXCHANGE
        },
        "filled_qty": 0,
        "avg_fill_px": 0,
        "fill_notional": 0,
        "last_update_fill_qty": 0,
        "last_update_fill_px": 0,
        "total_amend_up_qty": 0,
        "total_amend_dn_qty": 0,
        "cxled_qty": 0,
        "avg_cxled_px": 0,
        "cxled_notional": 0,
        "last_lapsed_qty": 0,
        "total_lapsed_qty": 0,
        "pending_amend_dn_qty": 0,
        "pending_amend_dn_px": 0,
        "pending_amend_up_qty": 0,
        "pending_amend_up_px": 0,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "chore_status": "OE_UNACK"
    })


@pytest.fixture()
def sell_fill_ledger_(pair_securities_with_sides_):
    yield DealsLedgerBaseModel(**{
        "chore_id": "O2",
        "fill_px": 120,
        "fill_qty": 30,
        "fill_notional": 0,
        "fill_symbol": pair_securities_with_sides_["security2"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side2"],
        "underlying_account": TRADING_ACCOUNT,
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F2"
    })


@pytest.fixture()
def sample_alert():
    yield AlertBaseModel.from_dict({
          "dismiss": False,
          "severity": "Severity_ERROR",
          "alert_count": 0,
          "alert_brief": "Sample Alert",
          "alert_details": "Fixture for sample alert",
          "impacted_chore": [
            {
              "chore_id": "O1",
              "security": {
                "sec_id": "Type1_Sec_1",
                "sec_id_source": SecurityIdSource.TICKER
              },
              "side": Side.BUY,
              "px": 10,
              "qty": 10,
              "chore_notional": 100,
              "underlying_account": TRADING_ACCOUNT,
              "text": [
                "sample alert"
              ]
            }
          ]
        })


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
                    "sec_id": "Type1_Sec_1",
                    "sec_id_source": "TICKER"
                },
                "exch_id": "EXCH1",
                "vwap": 150,
                "vwap_change": 2.5
            },
            "leg2": {
                "sec": {
                    "sec_id": "Type2_Sec_1",
                    "sec_id_source": "TICKER"
                },
                "exch_id": "EXCH2",
                "vwap": 10,
                "vwap_change": 0.5
            },
            "mkt_premium": "10",
            "mkt_premium_change": "2"
        }
    }
    yield dash_json


@pytest.fixture()
def bar_data_():
    current_time = DateTime.utcnow()
    bar_data_json = {
        "symbol_n_exch_id": {
            "symbol": "Type1_Sec_1",
            "exch_id": "EXCH"
        },
        "start_time": current_time,
        "end_time": current_time.add(seconds=1),
        "vwap": 150,
        "vwap_change": 2.5,
        "volume": 1_000
    }
    yield bar_data_json


class SampleBaseModel1(MsgspecBaseModel, kw_only=True):
    _id_count: ClassVar[int] = 0
    _id: int = field(default_factory=(lambda: SampleBaseModel1.inc_id()))
    field1: bool | None = None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


class SampleBaseModel2(MsgspecBaseModel, kw_only=True):
    _id_count: ClassVar[int] = 0
    _id: int = field(default_factory=(lambda: SampleBaseModel2.inc_id()))
    field1: int | None = None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


class SampleBaseModel(MsgspecBaseModel, kw_only=True):
    _id_count: ClassVar[int] = 0
    _id: int = field(default_factory=(lambda: SampleBaseModel.inc_id()))
    field1: SampleBaseModel1
    field2: List[SampleBaseModel2]
    field3: SampleBaseModel2 | None = None
    field4: List[SampleBaseModel1] | None = None
    field5: bool = False
    field6: SampleBaseModel2 | None
    field7: pendulum.DateTime | None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


@pytest.fixture()
def get_missing_id_json():
    sample = SampleBaseModel(
        field1=SampleBaseModel1(field1=True),
        field2=[SampleBaseModel2(field1=7), SampleBaseModel2(field1=18), SampleBaseModel2(field1=45)],
        field3=SampleBaseModel2(field1=10),
        field4=[SampleBaseModel1(field1=True), SampleBaseModel1(field1=False), SampleBaseModel1(field1=True)],
        field6=SampleBaseModel2(field1=6), field7=DateTime.utcnow()
    )

    sample_json = sample.to_dict()
    yield sample_json, SampleBaseModel


@pytest.fixture
def sample_quote_df():
    return polars.DataFrame({
        'px': [100.5],
        'qty': [1000],
        'premium': [0.5],
        'last_update_date_time': [pendulum.now('UTC')]
    })


@pytest.fixture
def sample_top_of_book_df():
    return polars.DataFrame({
        '_id': [1],
        'symbol': ['AAPL'],
        'total_bartering_security_size': [10000],
        'last_update_date_time': [pendulum.now('UTC')]
    })