import time
import pytest
import os
import copy

os.environ["DBType"] = "beanie"

# Project Imports
from Flux.CodeGenProjects.market_data.generated.Pydentic.market_data_service_model_imports import \
    MarketDepthBaseModel, SymbolOverviewBaseModel
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from tests.CodeGenProjects.addressbook.app.utility_test_functions import set_n_verify_limits, \
    create_n_verify_portfolio_status, create_fx_symbol_overview, clean_all_collections_ignoring_ui_layout, \
    get_ps_n_md_db_names, test_config_file_path, clean_today_activated_ticker_dict, clear_cache_in_model
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase, config_file_path
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator


@pytest.fixture()
def max_loop_count_per_side():
    max_loop_count_per_side = 5
    return max_loop_count_per_side


@pytest.fixture()
def buy_sell_symbol_list():
    return [
        ("CB_Sec_1", "EQT_Sec_1"),
        ("CB_Sec_2", "EQT_Sec_2"),
        ("CB_Sec_3", "EQT_Sec_3"),
        ("CB_Sec_4", "EQT_Sec_4"),
        ("CB_Sec_5", "EQT_Sec_5")
    ]


@pytest.fixture()
def residual_wait_sec() -> int:
    return 80


@pytest.fixture()
def config_dict():
    original_yaml_content_str = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path), load_as_str=True)
    TradingLinkBase.reload_configs()
    TradeSimulator.reload_symbol_configs()
    yield TradingLinkBase.config_dict

    # reverting back file
    YAMLConfigurationManager.update_yaml_configurations(original_yaml_content_str, str(config_file_path))
    TradingLinkBase.reload_configs()
    TradeSimulator.reload_symbol_configs()
    time.sleep(2)


@pytest.fixture
def clean_and_set_limits(expected_order_limits_, expected_portfolio_limits_, expected_portfolio_status_):
    clean_today_activated_ticker_dict()
    ps_db_name, md_db_name = get_ps_n_md_db_names(test_config_file_path)
    # cleaning all collections
    clean_all_collections_ignoring_ui_layout(ps_db_name, md_db_name)
    clear_cache_in_model()

    # setting limits
    set_n_verify_limits(expected_order_limits_, expected_portfolio_limits_)

    # creating portfolio_status
    create_n_verify_portfolio_status(copy.deepcopy(expected_portfolio_status_))

    # creating symbol_override for fx
    create_fx_symbol_overview()


@pytest.fixture()
def market_depth_basemodel_list():
    input_data = []

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for side, px, qty, dev in [("BID", 100, 90, -1), ("ASK", 110, 70, 1)]:
            input_data.extend([
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:30.165Z",
                    "side": side,
                    "px": px,
                    "qty": qty+10,
                    "position": 1,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:31.165Z",
                    "side": side,
                    "px": px+(dev*1),
                    "qty": qty-20,
                    "position": 2,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:32.165Z",
                    "side": side,
                    "px": px+(dev*2),
                    "qty": qty+10,
                    "position": 3,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:31.165Z",
                    "side": side,
                    "px": px+(dev*3),
                    "qty": qty-20,
                    "position": 4,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:32.165Z",
                    "side": side,
                    "px": px+(dev*4),
                    "qty": qty+20,
                    "position": 5,
                    "market_maker": "string",
                    "is_smart_depth": False
                }
            ])

    market_depth_basemodel_list = [MarketDepthBaseModel(**market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def top_of_book_list_():
    input_data = []
    for index, symbol in enumerate(["CB_Sec_1", "EQT_Sec_1"]):
        input_data.extend([
            {
                "symbol": symbol,
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
                "last_trade": {
                    "px": 116,
                    "qty": 150,
                    "last_update_date_time": "2023-02-13T20:30:35.165Z"
                },
                "total_trading_security_size": 100,
                "market_trade_volume": [
                    {
                        "participation_period_last_trade_qty_sum": 90,
                        "applicable_period_seconds": 180
                    }
                ],
                "last_update_date_time": "2023-02-13T20:30:34.165Z"
            }

        ])
    yield input_data


@pytest.fixture()
def pair_securities_with_sides_():
    yield {
        "security1": {"sec_id": "CB_Sec_1", "sec_type": "TICKER"}, "side1": "BUY",
        "security2": {"sec_id": "EQT_Sec_1", "sec_type": "TICKER"}, "side2": "SELL"
    }


@pytest.fixture()
def last_trade_fixture_list():
    input_data = []
    for index, symbol in enumerate(["CB_Sec_1", "EQT_Sec_1"]):
        input_data.extend([
            {
                "symbol": symbol,
                "time": "2023-03-10T09:19:12.019Z",
                "px": 116,
                "qty": 150,
                "exchange": "Exch",
                "special_conditions": "none",
                "past_limit": False,
                "unreported": False,
                "market_trade_volume": {
                    "participation_period_last_trade_qty_sum": 0,
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
              "last_update_date_time": "2023-03-12T13:11:22.329Z",
              "force_publish": False
            })
        )
    yield symbol_overview_obj_list


@pytest.fixture()
def expected_start_status_(pair_securities_with_sides_):
    yield StratStatus(**{
      "strat_state": "StratState_READY",
      "total_buy_qty": 0,
      "total_sell_qty": 0,
      "total_order_qty": 0,
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
      "strat_alerts": []
    })


@pytest.fixture()
def expected_strat_limits_():
    yield StratLimits(**{
      "max_open_orders_per_side": 5,
      "max_cb_notional": 300000,
      "max_open_cb_notional": 30000,
      "max_net_filled_notional": 160000,
      "max_concentration": 10,
      "limit_up_down_volume_participation_rate": 1,
      "cancel_rate": {
        "max_cancel_rate": 60,
        "applicable_period_seconds": 0,
        "waived_min_orders": 5
      },
      "market_trade_volume_participation": {
        "max_participation_rate": 40,
        "applicable_period_seconds": 180
      },
      "market_depth": {
        "participation_rate": 10,
        "depth_levels": 3
      },
      "residual_restriction": {
        "max_residual": 100_000,
        "residual_mark_seconds": 40
      },
      "eligible_brokers": []
    })


@pytest.fixture()
def expected_order_limits_():
    yield OrderLimitsBaseModel(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                               max_order_qty=500, min_order_notional=100, max_order_notional=90_000)


@pytest.fixture()
def expected_brokers_(buy_sell_symbol_list) -> List[Broker]:
    sec_positions: List[SecPosition] = []
    for buy_symbol, sell_symbol in buy_sell_symbol_list:
        cb_sec_position: SecPosition = SecPosition(security=Security(sec_id=buy_symbol, sec_type=SecurityType.SEDOL))
        cb_positions: List[Position] = [Position(type=PositionType.SOD, priority=0, available_size=10_000,
                                                 allocated_size=10_000, consumed_size=0)]
        cb_sec_position.positions = cb_positions
        sec_positions.append(cb_sec_position)
        eqt_sec_position: SecPosition = SecPosition(security=Security(sec_id=f"{sell_symbol}.SS", sec_type=SecurityType.RIC))
        eqt_positions: List[Position] = [
            Position(type=PositionType.SOD, priority=0, available_size=10_000, allocated_size=10_000, consumed_size=0),
            Position(type=PositionType.LOCATE, priority=1, available_size=10_000, allocated_size=10_000,
                     consumed_size=0),
            Position(type=PositionType.PTH, priority=2, available_size=10_000, allocated_size=10_000, consumed_size=0)
        ]
        eqt_sec_position.positions = eqt_positions
        sec_positions.append(eqt_sec_position)
    broker: Broker = Broker(broker="BKR", bkr_priority=10, sec_positions=sec_positions)
    yield [broker]


@pytest.fixture()
def expected_portfolio_limits_(expected_brokers_):
    rolling_max_order_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                                    max_gross_n_open_notional=2_400_000,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=expected_brokers_)
    yield portfolio_limits_obj


@pytest.fixture()
def pair_strat_(pair_securities_with_sides_):
    yield PairStratBaseModel(**{
        "last_active_date_time": "2023-02-13T20:30:31.165Z",
        "frequency": 1,
        "pair_strat_params": {
        "strat_leg1": {
          "exch_id": None,
          "sec": pair_securities_with_sides_["security1"],
          "side": pair_securities_with_sides_["side1"]
        },
        "strat_leg2": {
          "exch_id": None,
          "sec": pair_securities_with_sides_["security2"],
          "side": pair_securities_with_sides_["side2"]
        },
        "exch_response_max_seconds": 5,
        "common_premium": 40,
        "hedge_ratio": 5
        },
        "pair_strat_params_update_seq_num": 0,
        "strat_status_update_seq_num": 0,
        "strat_limits_update_seq_num": 0
    })


def empty_pair_side_trading_brief_obj(symbol: str, side: str, sec_type: str | None = SecurityType.TICKER):
    return PairSideTradingBrief(**{
        "security": {
          "sec_id": symbol,
          "sec_type": sec_type
        },
        "side": side,
        "last_update_date_time": DateTime.utcnow(),
        "consumable_open_orders": 0,
        "consumable_notional": 0,
        "consumable_open_notional": 0,
        "consumable_concentration": 0,
        "participation_period_order_qty_sum": 0,
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
    pair_buy_side_trading_brief = empty_pair_side_trading_brief_obj(pair_securities_with_sides_["security1"]["sec_id"],
                                                                    pair_securities_with_sides_["side1"])
    pair_sell_side_trading_brief = empty_pair_side_trading_brief_obj(pair_securities_with_sides_["security2"]["sec_id"],
                                                                     pair_securities_with_sides_["side2"])
    yield StratBriefBaseModel(pair_buy_side_trading_brief=pair_buy_side_trading_brief,
                              pair_sell_side_trading_brief=pair_sell_side_trading_brief,
                              consumable_nett_filled_notional=0)


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
            "order_count": 0
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
            "order_count": 0
        })
    ]


@pytest.fixture()
def expected_portfolio_status_():
    yield PortfolioStatusBaseModel(**{
        "_id": 1,
        "kill_switch": False,
        "portfolio_alerts": [],
        "overall_buy_notional": 0,
        "overall_sell_notional": 0,
        "overall_buy_fill_notional": 0,
        "overall_sell_fill_notional": 0,
        "alert_update_seq_num": 0
    })


@pytest.fixture()
def buy_order_(pair_securities_with_sides_):
    yield OrderJournalBaseModel(**{
        "order": {
            "order_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 100,
            "qty": 90,
            "order_notional": 0,
            "underlying_account": "trading_account",
            "text": [
              "test_string"
            ]
        },
        "order_event_date_time": DateTime.utcnow(),
        "order_event": "OE_NEW"
    })


@pytest.fixture()
def expected_buy_order_snapshot_(pair_securities_with_sides_):
    yield OrderSnapshotBaseModel(**{
        "order_brief": {
            "order_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 0,
            "qty": 0,
            "order_notional": 0,
            "underlying_account": "trading_account",
            "text": []
        },
        "filled_qty": 0,
        "avg_fill_px": 0,
        "fill_notional": 0,
        "last_update_fill_qty": 0,
        "last_update_fill_px": 0,
        "cxled_qty": 0,
        "avg_cxled_px": 0,
        "cxled_notional": 0,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "order_status": "OE_UNACK"
    })


@pytest.fixture()
def buy_fill_journal_(pair_securities_with_sides_):
    yield FillsJournalBaseModel(**{
        "order_id": "O1",
        "fill_px": 90,
        "fill_qty": 50,
        "fill_notional": 0,
        "fill_symbol": pair_securities_with_sides_["security1"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side1"],
        "underlying_account": "trading_account",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F1"
    })


@pytest.fixture()
def order_cxl_request(strat_manager_service_web_client_, buy_order_):
    placed_order_ack_obj = copy.deepcopy(buy_order_)
    placed_order_ack_obj.order_event = "OE_CXL"

    created_order_journal_obj = \
        strat_manager_service_web_client_.create_order_journal_client(placed_order_ack_obj)

    yield created_order_journal_obj


@pytest.fixture()
def sell_order_(pair_securities_with_sides_):
    yield OrderJournalBaseModel(**{
        "order": {
            "order_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 110,
            "qty": 70,
            "order_notional": 0,
            "underlying_account": "trading_account",
            "text": [
              "test_string"
            ]
        },
        "order_event_date_time": DateTime.utcnow(),
        "order_event": "OE_NEW"
    })


@pytest.fixture()
def expected_sell_order_snapshot_(pair_securities_with_sides_):
    yield OrderSnapshotBaseModel(**{
        "order_brief": {
            "order_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 0,
            "qty": 0,
            "order_notional": 0,
            "underlying_account": "trading_account",
            "text": []
        },
        "filled_qty": 0,
        "avg_fill_px": 0,
        "fill_notional": 0,
        "last_update_fill_qty": 0,
        "last_update_fill_px": 0,
        "cxled_qty": 0,
        "avg_cxled_px": 0,
        "cxled_notional": 0,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "order_status": "OE_UNACK"
    })


@pytest.fixture()
def sell_fill_journal_(pair_securities_with_sides_):
    yield FillsJournalBaseModel(**{
        "order_id": "O2",
        "fill_px": 120,
        "fill_qty": 30,
        "fill_notional": 0,
        "fill_symbol": pair_securities_with_sides_["security2"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side2"],
        "underlying_account": "trading_account",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F2"
    })


@pytest.fixture()
def sample_alert():
    yield Alert(**{
          "dismiss": False,
          "severity": "Severity_ERROR",
          "alert_count": 0,
          "alert_brief": "Sample Alert",
          "alert_details": "Fixture for sample alert",
          "impacted_order": [
            {
              "order_id": "O1",
              "security": {
                "sec_id": "CB_Sec_1",
                "sec_type": SecurityType.TICKER
              },
              "side": Side.BUY,
              "px": 10,
              "qty": 10,
              "order_notional": 100,
              "underlying_account": "trading_account",
              "text": [
                "sample alert"
              ]
            }
          ]
        })


@pytest.fixture()
def cb_eqt_security_records_(buy_sell_symbol_list) -> List[List[any]] | None:
    yield


@pytest.fixture()
def static_data_(cb_eqt_security_records_):
    yield
