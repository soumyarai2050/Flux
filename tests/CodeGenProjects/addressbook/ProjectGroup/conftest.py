import time
import os
import copy

import pendulum
import pytest

os.environ["ModelType"] = "msgspec"

# Project Imports
from tests.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.BarterEngine.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *


@pytest.fixture()
def cb_eqt_security_records_(leg1_leg2_symbol_list) -> List[List[any]] | None:
    yield


@pytest.fixture()
def static_data_(cb_eqt_security_records_):
    yield


@pytest.fixture()
def pair_securities_with_sides_():
    yield {
        "security1": {"sec_id": "Type1_Sec_1", "sec_id_source": "TICKER", "inst_type": "CB"}, "side1": "BUY",
        "security2": {"sec_id": "Type2_Sec_1", "sec_id_source": "TICKER", "inst_type": "EQT"}, "side2": "SELL"
    }


@pytest.fixture()
def leg1_leg2_symbol_list():
    return [
        ("Type1_Sec_1", "Type2_Sec_1"),
        ("Type1_Sec_2", "Type2_Sec_2"),
        ("Type1_Sec_3", "Type2_Sec_3"),
        ("Type1_Sec_4", "Type2_Sec_4"),
        ("Type1_Sec_5", "Type2_Sec_5"),
        ("Type1_Sec_6", "Type2_Sec_6"),
        ("Type1_Sec_7", "Type2_Sec_7"),
        ("Type1_Sec_8", "Type2_Sec_8"),
        ("Type1_Sec_9", "Type2_Sec_9"),
        ("Type1_Sec_10", "Type2_Sec_10"),
        ("Type1_Sec_11", "Type2_Sec_11"),
        ("Type1_Sec_12", "Type2_Sec_12"),
        ("Type1_Sec_13", "Type2_Sec_13"),
        ("Type1_Sec_14", "Type2_Sec_14"),
        ("Type1_Sec_15", "Type2_Sec_15"),
        ("Type1_Sec_16", "Type2_Sec_16"),
        ("Type1_Sec_17", "Type2_Sec_17"),
        ("Type1_Sec_18", "Type2_Sec_18"),
        ("Type1_Sec_19", "Type2_Sec_19"),
        ("Type1_Sec_20", "Type2_Sec_20"),
        ("Type1_Sec_21", "Type2_Sec_21"),
        ("Type1_Sec_22", "Type2_Sec_22"),
        ("Type1_Sec_23", "Type2_Sec_23"),
        ("Type1_Sec_24", "Type2_Sec_24"),
        ("Type1_Sec_25", "Type2_Sec_25"),
        ("Type1_Sec_26", "Type2_Sec_26"),
        ("Type1_Sec_27", "Type2_Sec_27"),
        ("Type1_Sec_28", "Type2_Sec_28"),
        ("Type1_Sec_29", "Type2_Sec_29"),
        ("Type1_Sec_30", "Type2_Sec_30"),
        ("Type1_Sec_31", "Type2_Sec_31"),
        ("Type1_Sec_32", "Type2_Sec_32"),
        ("Type1_Sec_33", "Type2_Sec_33"),
        ("Type1_Sec_34", "Type2_Sec_34"),
        ("Type1_Sec_35", "Type2_Sec_35"),
        ("Type1_Sec_36", "Type2_Sec_36"),
        ("Type1_Sec_37", "Type2_Sec_37"),
        ("Type1_Sec_38", "Type2_Sec_38"),
        ("Type1_Sec_39", "Type2_Sec_39"),
        ("Type1_Sec_40", "Type2_Sec_40")
    ]


@pytest.fixture
def clean_and_set_limits(expected_chore_limits_, expected_contact_limits_, expected_contact_status_,
                         expected_system_control_):
    # deleting existing executors
    clean_executors_and_today_activated_symbol_side_lock_file()

    # removing basket executor if exists
    # clean_basket_book()

    # cleaning all collections
    clean_all_collections_ignoring_ui_layout()
    clear_cache_in_model()

    # updating contact_alert
    clean_log_book_alerts()

    # updating plan_collection
    renew_plan_collection()

    # setting limits
    set_n_verify_limits(expected_chore_limits_, expected_contact_limits_)

    # creating contact_status
    create_n_verify_contact_status(copy.deepcopy(expected_contact_status_))

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
def market_depth_basemodel_list(request):
    input_data = []
    position_lvl = getattr(request, "param", 5)

    for symbol in ["Type1_Sec_1", "Type2_Sec_1"]:
        for side, px, qty, dev in [("BID", 99.0, 90, -1), ("ASK", 121.0, 70, 1)]:
            for pos in range(position_lvl):
                qty = qty+20 if pos == position_lvl-1 else (qty + 10 if pos % 2 != 0 else qty-20)
                input_data.append(
                    {
                        "symbol": symbol,
                        "exch_time": get_utc_date_time(),
                        "arrival_time": get_utc_date_time(),
                        "side": side,
                        "px": px+(dev*pos),
                        "qty": qty,
                        "position": pos,
                        "market_maker": "string",
                        "is_smart_depth": False
                    })

    market_depth_basemodel_list = [MarketDepthBaseModel.from_dict(market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def symbol_overview_obj_list():
    symbol_overview_obj_list = []
    for symbol in ["Type1_Sec_1", "Type2_Sec_1"]:
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
def pair_plan_(pair_securities_with_sides_):
    yield PairPlanBaseModel.from_dict({
        "last_active_date_time": get_utc_date_time(),
        "frequency": 1,
        "pair_plan_params": PairPlanParamsBaseModel.from_dict({
            "plan_mode": PlanMode.PlanMode_Normal,
            "plan_type": PlanType.Premium,
            "plan_leg1": PlanLegBaseModel.from_dict({
              "exch_id": "NYSE",
              "sec": pair_securities_with_sides_["security1"],
              "side": pair_securities_with_sides_["side1"],
              "fallback_broker": "ZERODHA",
              "fallback_route": "BR_QFII"
            }),
            "plan_leg2": PlanLegBaseModel.from_dict({
              "exch_id": "NYSE",
              "sec": pair_securities_with_sides_["security2"],
              "side": pair_securities_with_sides_["side2"],
              "fallback_broker": "ZERODHA",
              "fallback_route": "BR_CONNECT"
            }),
            "exch_response_max_seconds": 5,
            "common_premium": 40,
            "hedge_ratio": 1,
            "mplan": "Mplan_1"
        }),
        "pair_plan_params_update_seq_num": 0,
        "market_premium": 0
    })


@pytest.fixture()
def expected_plan_limits_():
    yield PlanLimitsBaseModel.from_dict({
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
      "plan_limits_update_seq_num": 0,
      "min_chore_notional": 100,
      "min_chore_notional_allowance": 1000,
      "eqt_sod_disable": False
    })


@pytest.fixture()
def expected_chore_limits_():
    yield ChoreLimitsBaseModel.from_kwargs(
        _id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
        max_chore_qty=500, max_chore_notional=90_000, max_basis_points_algo=1500,
        max_px_deviation_algo=20, max_chore_qty_algo=500, max_chore_notional_algo=90_000)


@pytest.fixture()
def expected_contact_limits_(expected_brokers_) -> ContactLimitsBaseModel:
    rolling_max_chore_count = RollingMaxChoreCountBaseModel.from_kwargs(max_rolling_tx_count=15,
                                                                        rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxChoreCountBaseModel.from_kwargs(max_rolling_tx_count=15,
                                                                         rolling_tx_count_period_seconds=2)

    contact_limits_obj = (
        ContactLimitsBaseModel.from_kwargs(_id=1, max_open_baskets=20, max_open_notional_per_side=2_000_000,
                                             max_gross_n_open_notional=2_400_000,
                                             rolling_max_chore_count=rolling_max_chore_count,
                                             rolling_max_reject_count=rolling_max_reject_count,
                                             eligible_brokers=expected_brokers_, eligible_brokers_update_count=0))
    return contact_limits_obj


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
    broker: BrokerBaseModel = BrokerBaseModel.from_kwargs(broker="ZERODHA", bkr_priority=10,
                                                          bkr_disable=False, sec_positions=sec_positions)
    return [broker]


@pytest.fixture()
def expected_contact_status_():
    yield ContactStatusBaseModel.from_dict({
        "_id": 1,
        "overall_buy_notional": 0,
        "overall_sell_notional": 0,
        "overall_buy_fill_notional": 0,
        "overall_sell_fill_notional": 0,
        "open_chores": 0
    })


@pytest.fixture()
def expected_system_control_():
    yield SystemControlBaseModel.from_kwargs(_id=1, kill_switch=False, pause_all_plans=False,
                                             load_buffer_plans=False, cxl_baskets=False)


@pytest.fixture()
def expected_plan_status_(pair_securities_with_sides_):
    yield PlanStatusBaseModel.from_dict({
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
      "plan_status_update_seq_num": 0
    })
