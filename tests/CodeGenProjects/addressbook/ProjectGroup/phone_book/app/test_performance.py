import concurrent.futures
import copy
import threading
import time
import timeit
import traceback
from typing import Dict

import pytest
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *


def _place_sanity_complete_buy_sell_pair_chores_with_pair_plan(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 111360
    expected_plan_limits_.market_barter_volume_participation.max_participation_rate = 80
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_plan, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list, market_depth_basemodel_list))

    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        sell_ack_chore_id = None

        leg1_last_barter: LastBarterBaseModel | None = None
        leg2_last_barter: LastBarterBaseModel | None = None
        for loop_count in range(total_chore_count_for_each_side):
            if leg1_last_barter is not None:
                last_barter_fixture_list[0]["market_barter_volume"]["participation_period_last_barter_qty_sum"] = leg1_last_barter.market_barter_volume.participation_period_last_barter_qty_sum
            if leg2_last_barter is not None:
                last_barter_fixture_list[1]["market_barter_volume"]["participation_period_last_barter_qty_sum"] = leg2_last_barter.market_barter_volume.participation_period_last_barter_qty_sum
            leg1_last_barter, leg2_last_barter = run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port,
                                                              create_counts_per_side=10)

            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, 98, 20, executor_web_client,
                                                           buy_inst_type)

            buy_ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                                   buy_symbol, executor_web_client,
                                                                                   loop_wait_secs=1,
                                                                                   last_chore_id=buy_ack_chore_id)
            buy_ack_chore_id = buy_ack_chore_ledger.chore.chore_id
            # deals_ledger = get_latest_fill_ledger_from_chore_id(buy_ack_chore_id, executor_web_client)
            time.sleep(1)
            sell_chore: NewChoreBaseModel = place_new_chore(sell_symbol, Side.SELL, 96, 20, executor_web_client,
                                                            sell_inst_type)
            sell_ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                                    sell_symbol, executor_web_client,
                                                                                    loop_wait_secs=1,
                                                                                    last_chore_id=sell_ack_chore_id)
            # plan_status: PlanStatusBaseModel = executor_web_client.get_plan_status_client(active_pair_plan.id)
            # plan_view: PlanViewBaseModel = photo_book_web_client.get_plan_view_client(
            #     active_pair_plan.id)
            sell_ack_chore_id = sell_ack_chore_ledger.chore.chore_id
            # assert plan_status.balance_notional == plan_view.balance_notional, \
            #     f"Mismatched {plan_status.balance_notional = }, {plan_view.balance_notional = }"
            check_plan_view_computes(active_pair_plan.id, executor_web_client)

        return buy_symbol, sell_symbol, active_pair_plan, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_place_sanity_parallel_buy_sell_pair_chores_to_check_plan_view(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_contact_limits_, refresh_sec_update_fixture):
    # Updating contact limits
    expected_contact_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
    expected_contact_limits_.max_open_baskets = 51
    expected_contact_limits_.max_gross_n_open_notional = 20_000_000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    max_loop_count_per_side = 50
    leg1_leg2_symbol_list = []
    total_plans = 40
    for i in range(1, total_plans + 1):
        leg1_symbol = f"Type1_Sec_{i}"
        leg2_symbol = f"Type2_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_sell_pair_chores_with_pair_plan,
                                   leg1_leg2_symbol_tuple[0], leg1_leg2_symbol_tuple[1], copy.deepcopy(pair_plan_),
                                   copy.deepcopy(expected_plan_limits_), copy.deepcopy(expected_plan_status_),
                                   copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side, refresh_sec_update_fixture)
                   for idx, leg1_leg2_symbol_tuple in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            future.result()

    # Since total_fill_sell_notional < total_fill_buy_notional
    px = 96
    qty = 20
    plan_view_list = photo_book_web_client.get_all_plan_view_client()
    expected_balance_notional = (expected_plan_limits_.max_single_leg_notional -
                                 max_loop_count_per_side * qty * get_px_in_usd(px))
    for plan_view in plan_view_list:
        assert plan_view.balance_notional == expected_balance_notional, \
                (f"Mismatched: overall_buy_notional must be "
                 f"{expected_balance_notional}, found {plan_view.balance_notional}")


def _create_infinite_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, cpp_port: int):
    leg1_last_barter: LastBarterBaseModel | None = None
    leg2_last_barter: LastBarterBaseModel | None = None
    while True:
        if leg1_last_barter is not None:
            last_barter_fixture_list[0]["market_barter_volume"][
                "participation_period_last_barter_qty_sum"] = leg1_last_barter.market_barter_volume.participation_period_last_barter_qty_sum
        if leg2_last_barter is not None:
            last_barter_fixture_list[1]["market_barter_volume"][
                "participation_period_last_barter_qty_sum"] = leg2_last_barter.market_barter_volume.participation_period_last_barter_qty_sum
        leg1_last_barter, leg2_last_barter = (
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, cpp_port,
                           create_counts_per_side=10, gap_secs=0.001))


def _place_sanity_complete_buy_sell_pair_chores_with_pair_plan_and_parallel_market_updates(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 111360
    expected_plan_limits_.market_barter_volume_participation.max_participation_rate = 80
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_plan, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list, market_depth_basemodel_list))

    threading.Thread(target=_create_infinite_last_barter, args=(buy_symbol, sell_symbol, last_barter_fixture_list,
                                                               active_pair_plan.cpp_port, ), daemon=True).start()
    time.sleep(10)

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        sell_ack_chore_id = None

        for loop_count in range(total_chore_count_for_each_side):
            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, 98, 20, executor_web_client,
                                                           buy_inst_type)

            buy_ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                                   buy_symbol, executor_web_client,
                                                                                   loop_wait_secs=1,
                                                                                   last_chore_id=buy_ack_chore_id)
            buy_ack_chore_id = buy_ack_chore_ledger.chore.chore_id
            # deals_ledger = get_latest_fill_ledger_from_chore_id(buy_ack_chore_id, executor_web_client)
            time.sleep(1)
            sell_chore: NewChoreBaseModel = place_new_chore(sell_symbol, Side.SELL, 96, 20, executor_web_client,
                                                            sell_inst_type)
            sell_ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                                    sell_symbol, executor_web_client,
                                                                                    loop_wait_secs=1,
                                                                                    last_chore_id=sell_ack_chore_id)
            # plan_status: PlanStatusBaseModel = executor_web_client.get_plan_status_client(active_pair_plan.id)
            # plan_view: PlanViewBaseModel = photo_book_web_client.get_plan_view_client(
            #     active_pair_plan.id)
            sell_ack_chore_id = sell_ack_chore_ledger.chore.chore_id
            # assert plan_status.balance_notional == plan_view.balance_notional, \
            #     f"Mismatched {plan_status.balance_notional = }, {plan_view.balance_notional = }"
            check_plan_view_computes(active_pair_plan.id, executor_web_client)

        return buy_symbol, sell_symbol, active_pair_plan, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def test_stress_with_parallel_md_updates(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_contact_limits_, refresh_sec_update_fixture):
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["allow_multiple_unfilled_chore_pairs_per_plan"] = True
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))

    try:
        # Updating contact limits
        expected_contact_limits_.rolling_max_chore_count.max_rolling_tx_count = 200
        expected_contact_limits_.max_open_baskets = 200
        expected_contact_limits_.max_gross_n_open_notional = 20_000_000
        email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

        max_loop_count_per_side = 50
        leg1_leg2_symbol_list = []
        total_plans = 40
        pair_plan_list = []
        for i in range(1, total_plans + 1):
            leg1_symbol = f"Type1_Sec_{i}"
            leg2_symbol = f"Type2_Sec_{i}"
            leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
            results = [executor.submit(_place_sanity_complete_buy_sell_pair_chores_with_pair_plan_and_parallel_market_updates,
                                       leg1_leg2_symbol_tuple[0], leg1_leg2_symbol_tuple[1], copy.deepcopy(pair_plan_),
                                       copy.deepcopy(expected_plan_limits_), copy.deepcopy(expected_plan_status_),
                                       copy.deepcopy(symbol_overview_obj_list),
                                       copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                       max_loop_count_per_side, refresh_sec_update_fixture)
                       for idx, leg1_leg2_symbol_tuple in enumerate(leg1_leg2_symbol_list)]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())
                future.result()

        # Since total_fill_sell_notional < total_fill_buy_notional
        px = 96
        qty = 20
        plan_view_list = photo_book_web_client.get_all_plan_view_client()
        expected_balance_notional = (expected_plan_limits_.max_single_leg_notional -
                                     max_loop_count_per_side * qty * get_px_in_usd(px))
        for plan_view in plan_view_list:
            assert plan_view.balance_notional == expected_balance_notional, \
                    (f"Mismatched: overall_buy_notional must be "
                     f"{expected_balance_notional}, found {plan_view.balance_notional}")
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


def _place_sanity_complete_buy_chores_with_pair_plan(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 111360
    expected_plan_limits_.market_barter_volume_participation.max_participation_rate = 80
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    (active_pair_plan, executor_web_client, buy_inst_type, sell_inst_type,
     config_file_path, config_dict, config_dict_str) = handle_pre_chore_test_requirements(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list)

    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        px = 98
        qty = 20

        # updating last_barter for this test
        for last_barter_fixture in last_barter_fixture_list:
            last_barter_fixture["qty"] = 500

        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client,
                                                           buy_inst_type)

            ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               buy_symbol, executor_web_client,
                                                                               last_chore_id=buy_ack_chore_id)
            # buy_ack_chore_id = ack_chore_ledger.chore.chore_id
            # deals_ledger = get_latest_fill_ledger_from_chore_id(buy_ack_chore_id, executor_web_client)
        return buy_symbol, sell_symbol, active_pair_plan, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _place_sanity_complete_buy_chores(buy_symbol, sell_symbol, pair_plan_,
                                      expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                                      last_barter_fixture_list, market_depth_basemodel_list,
                                      max_loop_count_per_side, refresh_sec_update_fixture):
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 111360
    expected_plan_limits_.market_barter_volume_participation.max_participation_rate = 80
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    (created_pair_plan, executor_web_client, buy_inst_type, sell_inst_type,
     config_file_path, config_dict, config_dict_str) = handle_pre_chore_test_requirements(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        px = 98
        qty = 20

        # updating last_barter for this test
        for last_barter_fixture in last_barter_fixture_list:
            last_barter_fixture["qty"] = 500

        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port,
                           create_counts_per_side=10)

            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client,
                                                           buy_inst_type)

            ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               buy_symbol, executor_web_client,
                                                                               last_chore_id=buy_ack_chore_id)
            buy_ack_chore_id = ack_chore_ledger.chore.chore_id
            # deals_ledger = get_latest_fill_ledger_from_chore_id(buy_ack_chore_id, executor_web_client)
        return buy_symbol, sell_symbol, created_pair_plan, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _place_sanity_complete_sell_chores(buy_symbol, sell_symbol, created_pair_plan,
                                       last_barter_fixture_list, max_loop_count_per_side, executor_web_client):

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, created_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, created_pair_plan)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing sell chores
        sell_ack_chore_id = None
        px = 96
        qty = 20

        # updating last_barter for this test
        for last_barter_fixture in last_barter_fixture_list:
            last_barter_fixture["qty"] = 500

        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port,
                           create_counts_per_side=10)
            sell_chore: ChoreLedger = place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client,
                                                       sell_inst_type)
            ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               sell_symbol, executor_web_client,
                                                                               last_chore_id=sell_ack_chore_id)
            plan_status: PlanStatusBaseModel = executor_web_client.get_plan_status_client(created_pair_plan.id)
            # time.sleep(2)
            plan_view = photo_book_web_client.get_plan_view_client(created_pair_plan.id)
            assert plan_status.balance_notional == plan_view.balance_notional, \
                f"Mismatched {plan_status.balance_notional=}, {plan_view.balance_notional=}"

            # ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
            #                                                                    sell_symbol, executor_web_client,
            #                                                                    last_chore_id=sell_ack_chore_id)
            sell_ack_chore_id = ack_chore_ledger.chore.chore_id
            # deals_ledger = get_latest_fill_ledger_from_chore_id(sell_ack_chore_id, executor_web_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def test_place_sanity_parallel_complete_chores(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_contact_limits_, refresh_sec_update_fixture):
    # Updating contact limits
    expected_contact_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    temp_list = []
    max_loop_count_per_side = 10
    leg1_leg2_symbol_list = []
    for i in range(1, 21):
        leg1_leg2_symbol_list.append((f"Type1_Sec_{i}", f"Type2_Sec_{i}"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_chores, leg1_symbol, leg2_symbol,
                                   copy.deepcopy(pair_plan_), copy.deepcopy(expected_plan_limits_),
                                   copy.deepcopy(expected_plan_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side, refresh_sec_update_fixture)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            buy_symbol_, sell_symbol_, created_pair_plan, executor_web_client = future.result()
            temp_list.append((buy_symbol_, sell_symbol_, created_pair_plan, executor_web_client))

    px = 98
    qty = 20
    plans_count = len(leg1_leg2_symbol_list)
    contact_status = email_book_service_native_web_client.get_contact_status_client(1)
    assert contact_status.overall_buy_notional == plans_count * max_loop_count_per_side * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_buy_notional must be "
         f"{plans_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, found "
         f"{contact_status.overall_buy_notional}")
    assert (contact_status.overall_buy_fill_notional ==
            plans_count * max_loop_count_per_side * qty * get_px_in_usd(px)), \
        (f"Mismatched: overall_buy_fill_notional must be "
         f"{plans_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, "
         f"found {contact_status.overall_buy_fill_notional}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(temp_list)) as executor:
        results = [executor.submit(_place_sanity_complete_sell_chores, buy_symbol_, sell_symbol_,
                                   created_pair_plan, copy.deepcopy(last_barter_fixture_list),
                                   max_loop_count_per_side, executor_web_client)
                   for buy_symbol_, sell_symbol_, created_pair_plan, executor_web_client in temp_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    px = 96
    qty = 20
    contact_status = email_book_service_native_web_client.get_contact_status_client(1)
    assert contact_status.overall_sell_notional == plans_count * max_loop_count_per_side * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_sell_notional must be "
         f"{plans_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, found "
         f"{contact_status.overall_sell_notional}")
    assert (contact_status.overall_sell_fill_notional ==
            plans_count * max_loop_count_per_side * qty * get_px_in_usd(px)), \
        (f"Mismatched: overall_sell_fill_notional must be "
         f"{plans_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, "
         f"found {contact_status.overall_sell_fill_notional}")
    return created_pair_plan, executor_web_client


@pytest.mark.nightly
def _test_place_sanity_parallel_complete_chores_to_check_plan_view(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_contact_limits_, refresh_sec_update_fixture):
    # Updating contact limits
    expected_contact_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
    expected_contact_limits_.max_open_baskets = 51
    expected_contact_limits_.max_gross_n_open_notional = 8_000_000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    temp_list = []
    max_loop_count_per_side = 50
    leg1_leg2_symbol_list = []
    total_plans = 20
    pair_plan_list = []
    for i in range(1, total_plans+1):
        leg1_symbol = f"Type1_Sec_{i}"
        leg2_symbol = f"Type2_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_plan_basemodel = create_plan(leg1_symbol, leg2_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_chores_with_pair_plan, leg1_leg2_symbol_tuple[0],
                                   leg1_leg2_symbol_tuple[1], pair_plan_list[idx],
                                   copy.deepcopy(expected_plan_limits_), copy.deepcopy(expected_plan_status_),
                                   copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side, refresh_sec_update_fixture)
                   for idx, leg1_leg2_symbol_tuple in enumerate(leg1_leg2_symbol_list)]

        done, not_done = concurrent.futures.wait(
            results, return_when=concurrent.futures.FIRST_EXCEPTION
        )
        if not_done:
            # at least one future has raised - you can return here
            # or propagate the exception
            # list(not_done)[0].result()  # re-raises exception here
            if list(not_done)[0].exception() is not None:
                raise Exception(list(not_done)[0].exception())

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            buy_symbol_, sell_symbol_, created_pair_plan, executor_web_client = future.result()
            temp_list.append((buy_symbol_, sell_symbol_, created_pair_plan, executor_web_client))

    px = 98
    qty = 20
    plans_count = len(leg1_leg2_symbol_list)
    plan_view_list = photo_book_web_client.get_all_plan_view_client()
    expected_balance_notional = (expected_plan_limits_.max_single_leg_notional -
                                 plans_count * max_loop_count_per_side * qty * get_px_in_usd(px))
    for plan_view in plan_view_list:
        assert (plan_view.balance_notional == expected_balance_notional,
           (f"Mismatched: overall_buy_notional must be "
            f"{expected_balance_notional}, found {plan_view.balance_notional}"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(temp_list)) as executor:
        results = [executor.submit(_place_sanity_complete_sell_chores, buy_symbol_, sell_symbol_,
                                   created_pair_plan, copy.deepcopy(last_barter_fixture_list),
                                   max_loop_count_per_side, executor_web_client)
                   for buy_symbol_, sell_symbol_, created_pair_plan, executor_web_client in temp_list]

        if not_done:
            # at least one future has raised - you can return here
            # or propagate the exception
            # list(not_done)[0].result()  # re-raises exception here
            if list(not_done)[0].exception() is not None:
                raise Exception(list(not_done)[0].exception())

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    px = 96
    qty = 20
    plans_count = len(leg1_leg2_symbol_list)
    plan_view_list = photo_book_web_client.get_all_plan_view_client()
    expected_balance_notional = (expected_plan_limits_.max_single_leg_notional -
                                 plans_count * max_loop_count_per_side * qty * get_px_in_usd(px))
    for plan_view in plan_view_list:
        assert (plan_view.balance_notional == expected_balance_notional,
                (f"Mismatched: overall_buy_notional must be "
                 f"{expected_balance_notional}, found {plan_view.balance_notional}"))
    return created_pair_plan, executor_web_client


@pytest.mark.nightly
def test_timeit_5000_reads(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                           expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                           last_barter_fixture_list, market_depth_basemodel_list,
                           buy_chore_, sell_chore_,
                           max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    max_loop_count_per_side = 50
    _, _, _, executor_web_client = _place_sanity_complete_buy_sell_pair_chores_with_pair_plan(
        buy_symbol, sell_symbol, pair_plan_,
        copy.deepcopy(expected_plan_limits_), copy.deepcopy(expected_plan_status_),
        copy.deepcopy(symbol_overview_obj_list),
        copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
        max_loop_count_per_side, refresh_sec_update_fixture)

    # reading chore_snapshot 5000 times
    total_read_counts = 5000
    total_chore_snapshot_obj = max_loop_count_per_side*2
    start_time = timeit.default_timer()
    for i in range(total_read_counts):
        val = executor_web_client.get_all_chore_snapshot_client()
        assert len(val) == total_chore_snapshot_obj, \
            f"Mismatched: length of chore snapshot must be {total_chore_snapshot_obj}, found {len(val)}"
    end_time = timeit.default_timer()

    total_time = (end_time - start_time)
    print(f"Total time taken for 5000 reads of 50 chore_snapshot is: {total_time} secs")

# Msgspec - Total time taken for 5000 reads of 50 chore_snapshot is: 44.873951098999896 secs
# Beanie - Total time taken for 5000 reads of 50 chore_snapshot is: 76.9152190049972 secs


@pytest.mark.nightly
def test_timeit_5000_patch(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                           expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                           last_barter_fixture_list, market_depth_basemodel_list,
                           buy_chore_, sell_chore_,
                           max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    active_pair_plan, executor_http_client = (
        create_n_activate_plan(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                expected_plan_status_, symbol_overview_obj_list,
                                market_depth_basemodel_list))

    total_patch_counts = 5000
    start_time = timeit.default_timer()
    for i in range(total_patch_counts):
        active_pair_plan.pair_plan_params.exch_response_max_seconds = i
        active_pair_plan.pair_plan_params.hedge_ratio = float(i)
        # active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id = "i"
        updated_obj = (
            email_book_service_native_web_client.patch_pair_plan_client(
                active_pair_plan.to_json_dict(exclude_none=True)))
        active_pair_plan.last_active_date_time = updated_obj.last_active_date_time
        active_pair_plan.frequency = updated_obj.frequency
        active_pair_plan.pair_plan_params_update_seq_num = updated_obj.pair_plan_params_update_seq_num
        assert updated_obj == active_pair_plan, \
            f"Mismatched pair_plan obj: expected {active_pair_plan}, updated {updated_obj}"
    end_time = timeit.default_timer()

    total_time = (end_time - start_time)
    print(f"Total time taken for 5000 patch of pair_plan is: {total_time} secs")

# Total time taken for 5000 patch of pair_plan is: 26.107542213998386 secs - with bug
# Total time taken for 5000 patch of pair_plan is: 31.730079086999922 secs - with deepcopy
# Total time taken for 5000 patch of pair_plan is: 27.38354792700011 secs - with extra fetch
