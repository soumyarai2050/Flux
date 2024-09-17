import time

import pendulum
import pytest
import os
import copy

os.environ["DBType"] = "msgspec"

# Project Imports
from tests.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *


@pytest.fixture()
def cb_eqt_security_records_(leg1_leg2_symbol_list) -> List[List[any]] | None:
    yield


@pytest.fixture()
def static_data_(cb_eqt_security_records_):
    yield


@pytest.fixture()
def pair_securities_with_sides_():
    yield {
        "security1": {"sec_id": "CB_Sec_1", "sec_id_source": "TICKER", "inst_type": "CB"}, "side1": "BUY",
        "security2": {"sec_id": "EQT_Sec_1", "sec_id_source": "TICKER", "inst_type": "EQT"}, "side2": "SELL"
    }


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
        ("CB_Sec_10", "EQT_Sec_10"),
        ("CB_Sec_11", "EQT_Sec_11"),
        ("CB_Sec_12", "EQT_Sec_12"),
        ("CB_Sec_13", "EQT_Sec_13"),
        ("CB_Sec_14", "EQT_Sec_14"),
        ("CB_Sec_15", "EQT_Sec_15"),
        ("CB_Sec_16", "EQT_Sec_16"),
        ("CB_Sec_17", "EQT_Sec_17"),
        ("CB_Sec_18", "EQT_Sec_18"),
        ("CB_Sec_19", "EQT_Sec_19"),
        ("CB_Sec_20", "EQT_Sec_20")
    ]


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

    market_depth_basemodel_list = [MarketDepthBaseModel.from_dict(market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def symbol_overview_obj_list():
    symbol_overview_obj_list = []
    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        symbol_overview_obj_list.append(
            SymbolOverviewBaseModel.from_dict({
              "symbol": symbol,
              "limit_up_px": 150,
              "limit_dn_px": 50,
              "conv_px": 90,
              "closing_px": 80,
              "open_px": 80,
              "lot_size": 100,  # should be greater than 100
              "tick_size": 0.001,
              "last_update_date_time": get_utc_date_time(),
              "force_publish": False
            })
        )
    yield symbol_overview_obj_list


@pytest.fixture()
def pair_strat_(pair_securities_with_sides_):
    yield PairStratBaseModel.from_dict({
        "last_active_date_time": get_utc_date_time(),
        "frequency": 1,
        "pair_strat_params": PairStratParamsBaseModel.from_dict({
            "strat_mode": StratMode.StratMode_Normal,
            "strat_type": StratType.Premium,
            "strat_leg1": StratLegBaseModel.from_dict({
              "exch_id": "SSE",
              "sec": pair_securities_with_sides_["security1"],
              "side": pair_securities_with_sides_["side1"],
              "fallback_broker": "ZERODHA",
              "fallback_route": "BR_QFII"
            }),
            "strat_leg2": StratLegBaseModel.from_dict({
              "exch_id": "SSE",
              "sec": pair_securities_with_sides_["security2"],
              "side": pair_securities_with_sides_["side2"],
              "fallback_broker": "ZERODHA",
              "fallback_route": "BR_CONNECT"
            }),
            "exch_response_max_seconds": 5,
            "common_premium": 40,
            "hedge_ratio": 1,
            "mstrat": "Mstrat_1"
        }),
        "pair_strat_params_update_seq_num": 0,
        "market_premium": 0
    })


@pytest.fixture()
def expected_strat_limits_():
    yield StratLimitsBaseModel.from_dict({
      "max_open_chores_per_side": 5,
      "max_single_leg_notional": 300000,
      "max_open_single_leg_notional": 300000,
      "max_net_filled_notional": 160000,
      "max_concentration": 10,
      "limit_up_down_volume_participation_rate": 1,
      "cancel_rate": {
        "max_cancel_rate": 60,
        "applicable_period_seconds": 0,
        "waived_initial_chores": 5
      },
      "market_barter_volume_participation": {
        "max_participation_rate": 40,
        "applicable_period_seconds": 180,
        "min_allowed_notional": 0
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
      "min_chore_notional_allowance": 1000,
      "eqt_sod_disable": False
    })


@pytest.fixture()
def expected_chore_limits_():
    yield ChoreLimitsBaseModel.from_kwargs(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                               max_chore_qty=500, max_chore_notional=90_000, max_basis_points_algo=1500,
                               max_px_deviation_algo=20, max_chore_qty_algo=500, max_chore_notional_algo=90_000)


@pytest.fixture()
def expected_portfolio_limits_(expected_brokers_):
    rolling_max_chore_count = RollingMaxChoreCountBaseModel.from_kwargs(max_rolling_tx_count=15,
                                                                        rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxChoreCountBaseModel.from_kwargs(max_rolling_tx_count=15,
                                                                         rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = (
        PortfolioLimitsBaseModel.from_kwargs(_id=1, max_open_baskets=20, max_open_notional_per_side=2_000_000,
                                             max_gross_n_open_notional=2_400_000,
                                             rolling_max_chore_count=rolling_max_chore_count,
                                             rolling_max_reject_count=rolling_max_reject_count,
                                             eligible_brokers=expected_brokers_, eligible_brokers_update_count=0))
    return portfolio_limits_obj


@pytest.fixture()
def expected_brokers_(leg1_leg2_symbol_list) -> List[BrokerBaseModel]:
    sec_positions: List[SecPositionBaseModel] = []
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list:
        cb_sec_position: SecPositionBaseModel = (
            SecPositionBaseModel.from_kwargs(
                security=SecurityBaseModel.from_kwargs(sec_id=buy_symbol, sec_id_source=SecurityIdSource.SEDOL)))
        cb_positions: List[PositionBaseModel] = \
            [PositionBaseModel.from_kwargs(type=PositionType.SOD, priority=0,
                                           available_size=10_000, allocated_size=10_000,
                                           consumed_size=0,
                                           pos_disable=False, premium_percentage=2)]
        cb_sec_position.positions = cb_positions
        sec_positions.append(cb_sec_position)
        eqt_sec_position: SecPositionBaseModel = (
            SecPositionBaseModel.from_kwargs(security=SecurityBaseModel.from_kwargs(sec_id=f"{sell_symbol}.SS",
                                                            sec_id_source=SecurityIdSource.RIC)))
        eqt_positions: List[PositionBaseModel] = [
            PositionBaseModel.from_kwargs(type=PositionType.SOD, priority=0,
                                          available_size=10_000, allocated_size=10_000,
                                          consumed_size=0, pos_disable=False, premium_percentage=2),
            PositionBaseModel.from_kwargs(type=PositionType.LOCATE, priority=1,
                                          available_size=10_000, allocated_size=10_000,
                                          consumed_size=0, pos_disable=False, premium_percentage=2),
            PositionBaseModel.from_kwargs(type=PositionType.PTH, priority=2, available_size=10_000,
                                          allocated_size=10_000, consumed_size=0,
                                          pos_disable=False, premium_percentage=2)
        ]
        eqt_sec_position.positions = eqt_positions
        sec_positions.append(eqt_sec_position)
    broker: BrokerBaseModel = BrokerBaseModel.from_kwargs(broker="ZERODHA", bkr_priority=10, bkr_disable=False,
  												    		sec_positions=sec_positions)
    return [broker]


@pytest.fixture()
def expected_portfolio_status_():
    yield PortfolioStatusBaseModel.from_dict({
        "_id": 1,
        "overall_buy_notional": 0,
        "overall_sell_notional": 0,
        "overall_buy_fill_notional": 0,
        "overall_sell_fill_notional": 0,
        "open_chores": 0
    })


@pytest.fixture()
def expected_system_control_():
    yield SystemControlBaseModel.from_kwargs(_id=1, kill_switch=False, pause_all_strats=False)


@pytest.fixture()
def expected_strat_status_(pair_securities_with_sides_):
    yield StratStatusBaseModel.from_dict({
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
