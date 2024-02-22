import time

import pendulum
import pytest
import os
import copy

os.environ["DBType"] = "beanie"

# Project Imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.Pydentic.strat_manager_service_model_imports import *


@pytest.fixture()
def max_loop_count_per_side():
    max_loop_count_per_side = 1mobile_book
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
        ("CB_Sec_1mobile_book", "EQT_Sec_1mobile_book")
    ]


@pytest.fixture()
def refresh_sec_update_fixture() -> int:
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    min_refresh_interval = 1mobile_book
    executor_config_dict["min_refresh_interval"] = min_refresh_interval
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))

    yield min_refresh_interval
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


@pytest.fixture
def db_names_list(leg1_leg2_symbol_list):
    db_names_list = [
        f"phone_book_{PAIR_STRAT_BEANIE_PORT}",
        f"log_analyzer_{LOG_ANALYZER_BEANIE_PORT}",
    ]

    for i in range(len(leg1_leg2_symbol_list)):
        db_names_list.append(f"strat_executor_{8mobile_book4mobile_book + i + 1}")
    return db_names_list


@pytest.fixture
def clean_and_set_limits(expected_order_limits_, expected_portfolio_limits_, expected_portfolio_status_,
                         expected_system_control_, db_names_list):
    # deleting existing executors
    clean_executors_and_today_activated_symbol_side_lock_file()

    # cleaning all collections
    clean_all_collections_ignoring_ui_layout(db_names_list)
    clear_cache_in_model()

    # updating portfolio_alert
    renew_portfolio_alert()

    # updating strat_collection
    renew_strat_collection()

    # setting limits
    set_n_verify_limits(expected_order_limits_, expected_portfolio_limits_)

    # creating portfolio_status
    create_n_verify_portfolio_status(copy.deepcopy(expected_portfolio_status_))

    # creating kill switch
    create_n_verify_system_control(expected_system_control_)

    # creating fx_symbol_overview
    create_fx_symbol_overview()

    # time for override get refreshed
    min_refresh_interval = ps_config_yaml_dict.get("min_refresh_interval")
    if min_refresh_interval is None:
        min_refresh_interval = 3mobile_book
    time.sleep(min_refresh_interval)


@pytest.fixture()
def market_depth_basemodel_list():
    input_data = []

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for side, px, qty, dev in [("BID", 1mobile_book9, 9mobile_book, -1), ("ASK", 121, 7mobile_book, 1)]:
            input_data.extend([
                {
                    "symbol": symbol,
                    "exch_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "arrival_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "side": side,
                    "px": px,
                    "qty": qty+1mobile_book,
                    "position": mobile_book,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "arrival_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "side": side,
                    "px": px+(dev*1),
                    "qty": qty-2mobile_book,
                    "position": 1,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "arrival_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "side": side,
                    "px": px+(dev*2),
                    "qty": qty+1mobile_book,
                    "position": 2,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "arrival_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "side": side,
                    "px": px+(dev*3),
                    "qty": qty-2mobile_book,
                    "position": 3,
                    "market_maker": "string",
                    "is_smart_depth": False
                },
                {
                    "symbol": symbol,
                    "exch_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "arrival_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:3mobile_book.165Z",
                    "side": side,
                    "px": px+(dev*4),
                    "qty": qty+2mobile_book,
                    "position": 4,
                    "market_maker": "string",
                    "is_smart_depth": False
                }
            ])

    market_depth_basemodel_list = [MarketDepthBaseModel(**market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def top_of_book_list_():
    leg1_last_trade_px, leg2_last_trade_px = get_both_leg_last_trade_px()
    input_data = [
        {
            "symbol": "CB_Sec_1",
            "bid_quote": {
                "px": 11mobile_book,
                "qty": 2mobile_book,
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:33.165Z"
            },
            "ask_quote": {
                "px": 12mobile_book,
                "qty": 4mobile_book,
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:31.165Z"
            },
            "last_trade": {
                "px": leg1_last_trade_px,
                "qty": 15mobile_book,
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:35.165Z"
            },
            "total_trading_security_size": 1mobile_bookmobile_book,
            "market_trade_volume": [
                {
                    "participation_period_last_trade_qty_sum": 9mobile_book,
                    "applicable_period_seconds": 18mobile_book
                }
            ],
            "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:34.165Z"
        },
        {
            "symbol": "EQT_Sec_1",
            "bid_quote": {
                "px": 11mobile_book,
                "qty": 2mobile_book,
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:33.165Z"
            },
            "ask_quote": {
                "px": 12mobile_book,
                "qty": 4mobile_book,
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:31.165Z"
            },
            "last_trade": {
                "px": leg2_last_trade_px,
                "qty": 15mobile_book,
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:35.165Z"
            },
            "total_trading_security_size": 1mobile_bookmobile_book,
            "market_trade_volume": [
                {
                    "participation_period_last_trade_qty_sum": 9mobile_book,
                    "applicable_period_seconds": 18mobile_book
                }
            ],
            "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:34.165Z"
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
def last_trade_fixture_list():
    input_data = []
    for index, symbol_n_px in enumerate([("CB_Sec_1", 116), ("EQT_Sec_1", 117)]):
        symbol, px = symbol_n_px
        input_data.extend([
            {
                "symbol_n_exch_id": {
                    "symbol": symbol,
                    "exch_id": "Exch"
                },
                "exch_time": "2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:19:12.mobile_book19Z",
                "arrival_time": "2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:19:12.mobile_book19Z",
                "px": px,
                "qty": 15mobile_book,
                "market_trade_volume": {
                    "participation_period_last_trade_qty_sum": mobile_book,
                    "applicable_period_seconds": mobile_book
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
              "limit_up_px": 15mobile_book,
              "limit_dn_px": 5mobile_book,
              "conv_px": 9mobile_book,
              "closing_px": 95,
              "open_px": 95,
              "last_update_date_time": "2mobile_book23-mobile_book3-12T13:11:22.329Z",
              "force_publish": False
            })
        )
    yield symbol_overview_obj_list


@pytest.fixture()
def expected_strat_status_(pair_securities_with_sides_):
    yield StratStatusBaseModel(**{
      "total_buy_qty": mobile_book,
      "total_sell_qty": mobile_book,
      "total_order_qty": mobile_book,
      "total_open_buy_qty": mobile_book,
      "total_open_sell_qty": mobile_book,
      "avg_open_buy_px": mobile_book,
      "avg_open_sell_px": mobile_book,
      "total_open_buy_notional": mobile_book,
      "total_open_sell_notional": mobile_book,
      "total_open_exposure": mobile_book,
      "total_fill_buy_qty": mobile_book,
      "total_fill_sell_qty": mobile_book,
      "avg_fill_buy_px": mobile_book,
      "avg_fill_sell_px": mobile_book,
      "total_fill_buy_notional": mobile_book,
      "total_fill_sell_notional": mobile_book,
      "total_fill_exposure": mobile_book,
      "total_cxl_buy_qty": mobile_book,
      "total_cxl_sell_qty": mobile_book,
      "avg_cxl_buy_px": mobile_book,
      "avg_cxl_sell_px": mobile_book,
      "total_cxl_buy_notional": mobile_book,
      "total_cxl_sell_notional": mobile_book,
      "total_cxl_exposure": mobile_book,
      "average_premium": mobile_book,
      "balance_notional": 3mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
      "strat_status_update_seq_num": mobile_book
    })


@pytest.fixture()
def expected_strat_limits_():
    yield StratLimitsBaseModel(**{
      "max_open_orders_per_side": 5,
      "max_single_leg_notional": 3mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
      "max_open_single_leg_notional": 3mobile_bookmobile_bookmobile_bookmobile_bookmobile_book,
      "max_net_filled_notional": 16mobile_bookmobile_bookmobile_bookmobile_book,
      "max_concentration": 1mobile_book,
      "limit_up_down_volume_participation_rate": 1,
      "cancel_rate": {
        "max_cancel_rate": 6mobile_book,
        "applicable_period_seconds": mobile_book,
        "waived_min_orders": 5
      },
      "market_trade_volume_participation": {
        "max_participation_rate": 4mobile_book,
        "applicable_period_seconds": 18mobile_book
      },
      "market_depth": {
        "participation_rate": 1mobile_book,
        "depth_levels": 3
      },
      "residual_restriction": {
        "max_residual": 1mobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
        "residual_mark_seconds": 1mobile_book
      },
      "eligible_brokers": [],
      "strat_limits_update_seq_num": mobile_book
    })


@pytest.fixture()
def expected_order_limits_():
    yield OrderLimitsBaseModel(_id=1, max_basis_points=15mobile_bookmobile_book, max_px_deviation=2mobile_book, max_px_levels=4,
                               max_order_qty=5mobile_bookmobile_book, min_order_notional=1mobile_bookmobile_book, max_order_notional=9mobile_book_mobile_bookmobile_bookmobile_book,
                               min_order_notional_allowance=1mobile_bookmobile_bookmobile_book)


@pytest.fixture()
def expected_brokers_(leg1_leg2_symbol_list) -> List[BrokerOptional]:
    sec_positions: List[SecPositionOptional] = []
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list:
        cb_sec_position: SecPositionOptional = (
            SecPositionOptional(security=SecurityOptional(sec_id=buy_symbol, sec_type=SecurityType.SEDOL)))
        cb_positions: List[PositionOptional] = [PositionOptional(type=PositionType.SOD, priority=mobile_book,
                                                                 available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book,
                                                                 consumed_size=mobile_book,
                                                                 pos_disable=False, premium_percentage=2)]
        cb_sec_position.positions = cb_positions
        sec_positions.append(cb_sec_position)
        eqt_sec_position: SecPositionOptional = (
            SecPositionOptional(security=SecurityOptional(sec_id=f"{sell_symbol}.SS", sec_type=SecurityType.RIC)))
        eqt_positions: List[PositionOptional] = [
            PositionOptional(type=PositionType.SOD, priority=mobile_book, available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book,
                             consumed_size=mobile_book, pos_disable=False, premium_percentage=2),
            PositionOptional(type=PositionType.LOCATE, priority=1, available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book,
                             consumed_size=mobile_book, pos_disable=False, premium_percentage=2),
            PositionOptional(type=PositionType.PTH, priority=2, available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book,
                             consumed_size=mobile_book, pos_disable=False, premium_percentage=2)
        ]
        eqt_sec_position.positions = eqt_positions
        sec_positions.append(eqt_sec_position)
    broker: BrokerOptional = BrokerOptional(broker="BKR", bkr_priority=1mobile_book, bkr_disable=False,
                                            sec_positions=sec_positions)
    return [broker]


@pytest.fixture()
def expected_portfolio_limits_(expected_brokers_):
    rolling_max_order_count = RollingMaxOrderCountOptional(max_rolling_tx_count=15, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCountOptional(max_rolling_tx_count=15, rolling_tx_count_period_seconds=2)

    print(expected_brokers_, type(expected_brokers_))
    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=2mobile_book, max_open_notional_per_side=2_mobile_bookmobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
                                                    max_gross_n_open_notional=2_4mobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=expected_brokers_)
    return portfolio_limits_obj


@pytest.fixture()
def pair_strat_(pair_securities_with_sides_):
    yield PairStratBaseModel(**{
        "last_active_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:31.165Z",
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
            "common_premium": 4mobile_book,
            "hedge_ratio": 5
        },
        "pair_strat_params_update_seq_num": mobile_book,
        "market_premium": mobile_book
    })


def empty_pair_side_trading_brief_obj(symbol: str, side: str, sec_type: str | None = SecurityType.TICKER):
    return PairSideTradingBriefOptional(**{
        "security": {
          "sec_id": symbol,
          "sec_type": sec_type
        },
        "side": side,
        "last_update_date_time": DateTime.utcnow(),
        "consumable_open_orders": mobile_book,
        "consumable_notional": mobile_book,
        "consumable_open_notional": mobile_book,
        "consumable_concentration": mobile_book,
        "participation_period_order_qty_sum": mobile_book,
        "consumable_cxl_qty": mobile_book,
        "indicative_consumable_participation_qty": mobile_book,
        "residual_qty": mobile_book,
        "indicative_consumable_residual": mobile_book,
        "all_bkr_cxlled_qty": mobile_book,
        "open_notional": mobile_book,
        "open_qty": mobile_book
    })


@pytest.fixture()
def expected_strat_brief_(pair_securities_with_sides_):
    pair_buy_side_trading_brief = empty_pair_side_trading_brief_obj(pair_securities_with_sides_["security1"]["sec_id"],
                                                                    pair_securities_with_sides_["side1"])
    pair_sell_side_trading_brief = empty_pair_side_trading_brief_obj(pair_securities_with_sides_["security2"]["sec_id"],
                                                                     pair_securities_with_sides_["side2"])
    yield StratBriefBaseModel(pair_buy_side_trading_brief=pair_buy_side_trading_brief,
                              pair_sell_side_trading_brief=pair_sell_side_trading_brief,
                              consumable_nett_filled_notional=16mobile_book_mobile_bookmobile_bookmobile_book)


@pytest.fixture()
def expected_symbol_side_snapshot_():
    yield [
        SymbolSideSnapshotBaseModel(**{
            "security": {
              "sec_id": "CB_Sec_1",
              "sec_type": SecurityType.TICKER
            },
            "side": "BUY",
            "avg_px": mobile_book,
            "total_qty": mobile_book,
            "total_filled_qty": mobile_book,
            "avg_fill_px": mobile_book,
            "total_fill_notional": mobile_book,
            "last_update_fill_qty": mobile_book,
            "last_update_fill_px": mobile_book,
            "total_cxled_qty": mobile_book,
            "avg_cxled_px": mobile_book,
            "total_cxled_notional": mobile_book,
            "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:35.165Z",
            "order_count": mobile_book
        }),
        SymbolSideSnapshotBaseModel(**{
            "security": {
                "sec_id": "EQT_Sec_1",
                "sec_type": SecurityType.TICKER
            },
            "side": "SELL",
            "avg_px": mobile_book,
            "total_qty": mobile_book,
            "total_filled_qty": mobile_book,
            "avg_fill_px": mobile_book,
            "total_fill_notional": mobile_book,
            "last_update_fill_qty": mobile_book,
            "last_update_fill_px": mobile_book,
            "total_cxled_qty": mobile_book,
            "avg_cxled_px": mobile_book,
            "total_cxled_notional": mobile_book,
            "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:36.165Z",
            "order_count": mobile_book
        })
    ]


@pytest.fixture()
def expected_portfolio_status_():
    yield PortfolioStatusBaseModel(**{
        "_id": 1,
        "portfolio_alerts": [],
        "overall_buy_notional": mobile_book,
        "overall_sell_notional": mobile_book,
        "overall_buy_fill_notional": mobile_book,
        "overall_sell_fill_notional": mobile_book
    })


@pytest.fixture()
def expected_system_control_():
    yield SystemControlBaseModel(_id=1, kill_switch=False)


@pytest.fixture()
def buy_order_(pair_securities_with_sides_):
    yield OrderJournalBaseModel(**{
        "order": {
            "order_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 1mobile_bookmobile_book,
            "qty": 9mobile_book,
            "order_notional": mobile_book,
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
            "px": mobile_book,
            "qty": mobile_book,
            "order_notional": mobile_book,
            "underlying_account": "trading_account",
            "text": [],
            "exchange": "trading_exchange"
        },
        "filled_qty": mobile_book,
        "avg_fill_px": mobile_book,
        "fill_notional": mobile_book,
        "last_update_fill_qty": mobile_book,
        "last_update_fill_px": mobile_book,
        "cxled_qty": mobile_book,
        "avg_cxled_px": mobile_book,
        "cxled_notional": mobile_book,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "order_status": "OE_UNACK"
    })


@pytest.fixture()
def buy_fill_journal_(pair_securities_with_sides_):
    yield FillsJournalBaseModel(**{
        "order_id": "O1",
        "fill_px": 9mobile_book,
        "fill_qty": 5mobile_book,
        "fill_notional": mobile_book,
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
            "px": 11mobile_book,
            "qty": 7mobile_book,
            "order_notional": mobile_book,
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
            "px": mobile_book,
            "qty": mobile_book,
            "order_notional": mobile_book,
            "underlying_account": "trading_account",
            "text": [],
            "exchange": "trading_exchange"
        },
        "filled_qty": mobile_book,
        "avg_fill_px": mobile_book,
        "fill_notional": mobile_book,
        "last_update_fill_qty": mobile_book,
        "last_update_fill_px": mobile_book,
        "cxled_qty": mobile_book,
        "avg_cxled_px": mobile_book,
        "cxled_notional": mobile_book,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "order_status": "OE_UNACK"
    })


@pytest.fixture()
def sell_fill_journal_(pair_securities_with_sides_):
    yield FillsJournalBaseModel(**{
        "order_id": "O2",
        "fill_px": 12mobile_book,
        "fill_qty": 3mobile_book,
        "fill_notional": mobile_book,
        "fill_symbol": pair_securities_with_sides_["security2"]["sec_id"],
        "fill_side": pair_securities_with_sides_["side2"],
        "underlying_account": "trading_account",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F2"
    })


@pytest.fixture()
def sample_alert():
    yield AlertOptional(**{
          "dismiss": False,
          "severity": "Severity_ERROR",
          "alert_count": mobile_book,
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
              "px": 1mobile_book,
              "qty": 1mobile_book,
              "order_notional": 1mobile_bookmobile_book,
              "underlying_account": "trading_account",
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


class SampleBaseModel1(BaseModel):
    _id_count: ClassVar[int] = mobile_book
    id: int = Field(default_factory=(lambda: SampleBaseModel1.inc_id()), alias="_id")
    field1: bool | None = None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


class SampleBaseModel2(BaseModel):
    _id_count: ClassVar[int] = mobile_book
    id: int = Field(default_factory=(lambda: SampleBaseModel2.inc_id()), alias="_id")
    field1: int | None = None

    @classmethod
    def inc_id(cls):
        cls._id_count += 1
        return cls._id_count


class SampleBaseModel(BaseModel):
    _id_count: ClassVar[int] = mobile_book
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
        field3=SampleBaseModel2(field1=1mobile_book),
        field4=[SampleBaseModel1(field1=True), SampleBaseModel1(field1=False), SampleBaseModel1(field1=True)],
        field6=SampleBaseModel2(field1=6), field7=DateTime.utcnow()
    )

    sample_json = sample.model_dump(by_alias=True)
    yield sample_json, SampleBaseModel
