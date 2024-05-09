import time

import pendulum
import pytest
import os
import copy

os.environ["DBType"] = "beanie"

# Project Imports
from Flux.CodeGenProjects.BarterEngine.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.BarterEngine.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from tests.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *


@pytest.fixture()
def max_loop_count_per_side():
    max_loop_count_per_side = 10
    return max_loop_count_per_side


@pytest.fixture()
def leg1_leg2_symbol_list():
    return [
        ("CB_Sec_1", "EQT_Sec_1"),
        ("CB_Sec_2", "EQT_Sec_2"),
        ("CB_Sec_3", "EQT_Sec_3"),
        ("CB_Sec_4", "EQT_Sec_4"),
        ("CB_Sec_5", "EQT_Sec_5"),
        ("CB_Sec_6", "EQT_Sec_6"),
        ("CB_Sec_7", "EQT_Sec_7"),
        ("CB_Sec_8", "EQT_Sec_8"),
        ("CB_Sec_9", "EQT_Sec_9"),
        ("CB_Sec_10", "EQT_Sec_10")
    ]


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


@pytest.fixture
def clean_and_set_limits(expected_chore_limits_, expected_portfolio_limits_, expected_portfolio_status_,
                         expected_system_control_):
    # deleting existing executors
    clean_executors_and_today_activated_symbol_side_lock_file()

    # cleaning all collections
    clean_all_collections_ignoring_ui_layout()
    clear_cache_in_model()

    # updating portfolio_alert
    clean_log_book_alerts()

    # updating strat_collection
    renew_strat_collection()

    # setting limits
    set_n_verify_limits(expected_chore_limits_, expected_portfolio_limits_)

    # creating portfolio_status
    create_n_verify_portfolio_status(copy.deepcopy(expected_portfolio_status_))

    # creating kill switch
    create_n_verify_system_control(expected_system_control_)

    # creating fx_symbol_overview
    create_fx_symbol_overview()

    # time for override get refreshed
    min_refresh_interval = ps_config_yaml_dict.get("min_refresh_interval")
    if min_refresh_interval is None:
        min_refresh_interval = 30
    time.sleep(min_refresh_interval)


@pytest.fixture()
def market_depth_basemodel_list():
    input_data = []

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for side, px, qty, dev in [("BID", 99, 90, -1), ("ASK", 121, 70, 1)]:
            input_data.extend([
                {
                    "symbol": symbol,
                    "exch_time": get_utc_date_time(),
                    "arrival_time": get_utc_date_time(),
                    "side": side,
                    "px": px,
                    "qty": qty+10,
                    "position": 0,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": get_utc_date_time(),
                    "arrival_time": get_utc_date_time(),
                    "side": side,
                    "px": px+(dev*1),
                    "qty": qty-20,
                    "position": 1,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": get_utc_date_time(),
                    "arrival_time": get_utc_date_time(),
                    "side": side,
                    "px": px+(dev*2),
                    "qty": qty+10,
                    "position": 2,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": get_utc_date_time(),
                    "arrival_time": get_utc_date_time(),
                    "side": side,
                    "px": px+(dev*3),
                    "qty": qty-20,
                    "position": 3,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": get_utc_date_time(),
                    "arrival_time": get_utc_date_time(),
                    "side": side,
                    "px": px+(dev*4),
                    "qty": qty+20,
                    "position": 4,
                    "market_maker": "string",
                    "is_smart_depth": False
                }
            ])

    market_depth_basemodel_list = [MarketDepthBaseModel(**market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def top_of_book_list_():
    leg1_last_barter_px, leg2_last_barter_px = get_both_side_last_barter_px()
    input_data = [
        {
            "symbol": "CB_Sec_1",
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
            "symbol": "EQT_Sec_1",
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
def pair_securities_with_sides_():
    yield {
        "security1": {"sec_id": "CB_Sec_1", "sec_type": "TICKER"}, "side1": "BUY",
        "security2": {"sec_id": "EQT_Sec_1", "sec_type": "TICKER"}, "side2": "SELL"
    }


@pytest.fixture()
def last_barter_fixture_list():
    input_data = []
    for index, symbol_n_px in enumerate([("CB_Sec_1", 116), ("EQT_Sec_1", 117)]):
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
                    "participation_period_last_barter_qty_sum": 0,
                    "applicable_period_seconds": 0
                }
            }
        ])
    yield input_data


@pytest.fixture()
def symbol_overview_obj_list():
    symbol_overview_obj_list = []
    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        symbol_overview_obj_list.append(
            SymbolOverviewBaseModel(**{
              "symbol": symbol,
              "limit_up_px": 150,
              "limit_dn_px": 50,
              "conv_px": 90,
              "closing_px": 95,
              "open_px": 95,
              "last_update_date_time": get_utc_date_time(),
              "force_publish": False
            })
        )
    yield symbol_overview_obj_list


@pytest.fixture()
def expected_strat_status_(pair_securities_with_sides_):
    yield StratStatusBaseModel(**{
      "total_buy_qty": 0,
      "total_sell_qty": 0,
      "total_chore_qty": 0,
      "total_open_buy_qty": 0,
      "total_open_sell_qty": 0,
      "avg_open_buy_px": 0,
      "avg_open_sell_px": 0,
      "total_open_buy_notional": 0,
      "total_open_sell_notional": 0,
      "total_open_exposure": 0,
      "total_fill_buy_qty": 0,
      "total_fill_sell_qty": 0,
      "avg_fill_buy_px": 0,
      "avg_fill_sell_px": 0,
      "total_fill_buy_notional": 0,
      "total_fill_sell_notional": 0,
      "total_fill_exposure": 0,
      "total_cxl_buy_qty": 0,
      "total_cxl_sell_qty": 0,
      "avg_cxl_buy_px": 0,
      "avg_cxl_sell_px": 0,
      "total_cxl_buy_notional": 0,
      "total_cxl_sell_notional": 0,
      "total_cxl_exposure": 0,
      "average_premium": 0,
      "balance_notional": 300000,
      "strat_status_update_seq_num": 0
    })


@pytest.fixture()
def expected_strat_limits_():
    yield StratLimitsBaseModel(**{
      "max_open_chores_per_side": 5,
      "max_single_leg_notional": 300000,
      "max_open_single_leg_notional": 300000,
      "max_net_filled_notional": 160000,
      "max_concentration": 10,
      "limit_up_down_volume_participation_rate": 1,
      "cancel_rate": {
        "max_cancel_rate": 60,
        "applicable_period_seconds": 0,
        "waived_min_chores": 5
      },
      "market_barter_volume_participation": {
        "max_participation_rate": 40,
        "applicable_period_seconds": 180
      },
      "market_depth": {
        "participation_rate": 10,
        "depth_levels": 3
      },
      "residual_restriction": {
        "max_residual": 150_000,
        "residual_mark_seconds": 10
      },
      "eligible_brokers": [],
      "strat_limits_update_seq_num": 0,
      "min_chore_notional": 100,
      "min_chore_notional_allowance": 1000
    })


@pytest.fixture()
def expected_chore_limits_():
    yield ChoreLimitsBaseModel(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                               max_chore_qty=500, max_chore_notional=90_000)


@pytest.fixture()
def expected_brokers_(leg1_leg2_symbol_list) -> List[BrokerOptional]:
    sec_positions: List[SecPositionOptional] = []
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list:
        cb_sec_position: SecPositionOptional = (
            SecPositionOptional(security=SecurityOptional(sec_id=buy_symbol, sec_type=SecurityType.SEDOL)))
        cb_positions: List[PositionOptional] = [PositionOptional(type=PositionType.SOD, priority=0,
                                                                 available_size=10_000, allocated_size=10_000,
                                                                 consumed_size=0,
                                                                 pos_disable=False, premium_percentage=2)]
        cb_sec_position.positions = cb_positions
        sec_positions.append(cb_sec_position)
        eqt_sec_position: SecPositionOptional = (
            SecPositionOptional(security=SecurityOptional(sec_id=f"{sell_symbol}.SS", sec_type=SecurityType.RIC)))
        eqt_positions: List[PositionOptional] = [
            PositionOptional(type=PositionType.SOD, priority=0, available_size=10_000, allocated_size=10_000,
                             consumed_size=0, pos_disable=False, premium_percentage=2),
            PositionOptional(type=PositionType.LOCATE, priority=1, available_size=10_000, allocated_size=10_000,
                             consumed_size=0, pos_disable=False, premium_percentage=2),
            PositionOptional(type=PositionType.PTH, priority=2, available_size=10_000, allocated_size=10_000,
                             consumed_size=0, pos_disable=False, premium_percentage=2)
        ]
        eqt_sec_position.positions = eqt_positions
        sec_positions.append(eqt_sec_position)
    broker: BrokerOptional = BrokerOptional(broker="BKR", bkr_priority=10, bkr_disable=False,
                                            sec_positions=sec_positions)
    return [broker]


@pytest.fixture()
def expected_portfolio_limits_(expected_brokers_):
    rolling_max_chore_count = RollingMaxChoreCountOptional(max_rolling_tx_count=15, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxChoreCountOptional(max_rolling_tx_count=15, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=20, max_open_notional_per_side=2_000_000,
                                                    max_gross_n_open_notional=2_400_000,
                                                    rolling_max_chore_count=rolling_max_chore_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=expected_brokers_)
    return portfolio_limits_obj


@pytest.fixture()
def pair_strat_(pair_securities_with_sides_):
    yield PairStratBaseModel(**{
        "last_active_date_time": get_utc_date_time(),
        "frequency": 1,
        "pair_strat_params": {
            "strat_mode": StratMode.StratMode_Normal,
            "strat_type": StratType.Premium,
            "strat_leg1": {
              "exch_id": "E1",
              "sec": pair_securities_with_sides_["security1"],
              "side": pair_securities_with_sides_["side1"]
            },
            "strat_leg2": {
              "exch_id": "E1",
              "sec": pair_securities_with_sides_["security2"],
              "side": pair_securities_with_sides_["side2"]
            },
            "exch_response_max_seconds": 5,
            "common_premium": 40,
            "hedge_ratio": 5
        },
        "pair_strat_params_update_seq_num": 0,
        "market_premium": 0
    })


def empty_pair_side_bartering_brief_obj(symbol: str, side: str, sec_type: str | None = SecurityType.TICKER):
    return PairSideBarteringBriefOptional(**{
        "security": {
          "sec_id": symbol,
          "sec_type": sec_type
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
def expected_strat_brief_(pair_securities_with_sides_):
    pair_buy_side_bartering_brief = empty_pair_side_bartering_brief_obj(pair_securities_with_sides_["security1"]["sec_id"],
                                                                    pair_securities_with_sides_["side1"])
    pair_sell_side_bartering_brief = empty_pair_side_bartering_brief_obj(pair_securities_with_sides_["security2"]["sec_id"],
                                                                     pair_securities_with_sides_["side2"])
    yield StratBriefBaseModel(pair_buy_side_bartering_brief=pair_buy_side_bartering_brief,
                              pair_sell_side_bartering_brief=pair_sell_side_bartering_brief,
                              consumable_nett_filled_notional=160_000)


@pytest.fixture()
def expected_symbol_side_snapshot_():
    yield [
        SymbolSideSnapshotBaseModel(**{
            "security": {
              "sec_id": "CB_Sec_1",
              "sec_type": SecurityType.TICKER
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
        SymbolSideSnapshotBaseModel(**{
            "security": {
                "sec_id": "EQT_Sec_1",
                "sec_type": SecurityType.TICKER
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
def expected_portfolio_status_():
    yield PortfolioStatusBaseModel(**{
        "_id": 1,
        "overall_buy_notional": 0,
        "overall_sell_notional": 0,
        "overall_buy_fill_notional": 0,
        "overall_sell_fill_notional": 0,
        "open_chores": 0
    })


@pytest.fixture()
def expected_system_control_():
    yield SystemControlBaseModel(_id=1, kill_switch=False, pause_all_strats=False)


@pytest.fixture()
def buy_chore_(pair_securities_with_sides_):
    yield ChoreJournalBaseModel(**{
        "chore": {
            "chore_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 100,
            "qty": 90,
            "chore_notional": 0,
            "underlying_account": "bartering_account",
            "text": [
              "test_string"
            ]
        },
        "chore_event_date_time": DateTime.utcnow(),
        "chore_event": "OE_NEW"
    })


@pytest.fixture()
def expected_buy_chore_snapshot_(pair_securities_with_sides_):
    yield ChoreSnapshotBaseModel(**{
        "chore_brief": {
            "chore_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 0,
            "qty": 0,
            "chore_notional": 0,
            "underlying_account": "bartering_account",
            "text": [],
            "exchange": "bartering_exchange"
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
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "chore_status": "OE_UNACK"
    })


@pytest.fixture()
def buy_fill_journal_(pair_securities_with_sides_):
    yield FillsJournalBaseModel(**{
        "chore_id": "O1",
        "fill_px": 90,
        "fill_qty": 50,
        "fill_notional": 0,
        "fill_symbol": pair_securities_with_sides_["security1"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side1"],
        "underlying_account": "bartering_account",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F1"
    })


@pytest.fixture()
def chore_cxl_request(email_book_service_web_client_, buy_chore_):
    placed_chore_ack_obj = copy.deepcopy(buy_chore_)
    placed_chore_ack_obj.chore_event = "OE_CXL"

    created_chore_journal_obj = \
        email_book_service_web_client_.create_chore_journal_client(placed_chore_ack_obj)

    yield created_chore_journal_obj


@pytest.fixture()
def sell_chore_(pair_securities_with_sides_):
    yield ChoreJournalBaseModel(**{
        "chore": {
            "chore_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 110,
            "qty": 70,
            "chore_notional": 0,
            "underlying_account": "bartering_account",
            "text": [
              "test_string"
            ]
        },
        "chore_event_date_time": DateTime.utcnow(),
        "chore_event": "OE_NEW"
    })


@pytest.fixture()
def expected_sell_chore_snapshot_(pair_securities_with_sides_):
    yield ChoreSnapshotBaseModel(**{
        "chore_brief": {
            "chore_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 0,
            "qty": 0,
            "chore_notional": 0,
            "underlying_account": "bartering_account",
            "text": [],
            "exchange": "bartering_exchange"
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
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "chore_status": "OE_UNACK"
    })


@pytest.fixture()
def sell_fill_journal_(pair_securities_with_sides_):
    yield FillsJournalBaseModel(**{
        "chore_id": "O2",
        "fill_px": 120,
        "fill_qty": 30,
        "fill_notional": 0,
        "fill_symbol": pair_securities_with_sides_["security2"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side2"],
        "underlying_account": "bartering_account",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F2"
    })


@pytest.fixture()
def sample_alert():
    yield AlertOptional(**{
          "dismiss": False,
          "severity": "Severity_ERROR",
          "alert_count": 0,
          "alert_brief": "Sample Alert",
          "alert_details": "Fixture for sample alert",
          "impacted_chore": [
            {
              "chore_id": "O1",
              "security": {
                "sec_id": "CB_Sec_1",
                "sec_type": SecurityType.TICKER
              },
              "side": Side.BUY,
              "px": 10,
              "qty": 10,
              "chore_notional": 100,
              "underlying_account": "bartering_account",
              "text": [
                "sample alert"
              ]
            }
          ]
        })


@pytest.fixture()
def cb_eqt_security_records_(leg1_leg2_symbol_list) -> List[List[any]] | None:
    yield


@pytest.fixture()
def static_data_(cb_eqt_security_records_):
    yield


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
                "vwap": 150,
                "vwap_change": 2.5
            },
            "leg2": {
                "sec": {
                    "sec_id": "EQT_Sec_1",
                    "sec_type": "TICKER"
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
            "symbol": "CB_Sec_1",
            "exch_id": "EXCH"
        },
        "start_time": current_time,
        "end_time": current_time.add(seconds=1),
        "vwap": 150,
        "vwap_change": 2.5,
        "volume": 1_000
    }
    yield bar_data_json


class SampleBaseModel1(BaseModel):
    _id_count: ClassVar[int] = 0
    id: int = Field(default_factory=(lambda: SampleBaseModel1.inc_id()), alias="_id")
    field1: bool | None = None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


class SampleBaseModel2(BaseModel):
    _id_count: ClassVar[int] = 0
    id: int = Field(default_factory=(lambda: SampleBaseModel2.inc_id()), alias="_id")
    field1: int | None = None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


class SampleBaseModel(BaseModel):
    _id_count: ClassVar[int] = 0
    id: int = Field(default_factory=(lambda: SampleBaseModel.inc_id()), alias="_id")
    field1: SampleBaseModel1
    field2: List[SampleBaseModel2]
    field3: SampleBaseModel2 | None = None
    field4: List[SampleBaseModel1] | None = None
    field5: bool = False
    field6: SampleBaseModel2 | None
    field7: pendulum.DateTime | SkipJsonSchema[None]
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

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

    sample_json = sample.model_dump(by_alias=True)
    yield sample_json, SampleBaseModel
