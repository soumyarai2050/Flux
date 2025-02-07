# standard imports
import copy
import math
import time
import traceback
import concurrent.futures

import pytest

# project imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager


PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
test_config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"


# limit breach chore blocks test-cases
@pytest.mark.nightly
def test_min_chore_notional_breach_in_normal_plan_mode1(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests the enforcement of minimum chore notional limits in normal planegy mode.

        This test validates that chores with notional value less than the computed minimum chore
        notional threshold are blocked when plan_limits.min_chore_notional exceeds
        plan_limits.min_chore_notional_allowance. The computed minimum chore notional is
        determined as: min_chore_notional = plan_limits.min_chore_notional - plan_limits.min_chore_notional_allowance

        Test Flow:
        1. Sets up a bartering pair with initial configurations and market depth
        2. Executes a positive test case with default limits to verify normal chore placement
        3. Modifies planegy limits to create a breach condition:
           - Sets min_chore_notional_allowance to 1000
           - Sets min_chore_notional to 21000
        4. Attempts to place an chore that should be blocked due to computed notional limit (20000)
        5. Verifies that appropriate alerts are generated for blocked chores

        Key Validations:
        - Confirms successful chore placement under normal conditions
        - Verifies chore blocking when computed notional limits are breached
        - Checks for proper alert messages in planegy and contact alerts
        - Ensures simulator configuration updates are properly applied
    """

    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative check
        # updating plan_limits
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)
        plan_limits.min_chore_notional_allowance = 1000
        plan_limits.min_chore_notional = 21000.0
        executor_http_client.put_plan_limits_client(plan_limits)

        # based on street_book logic, min_chore_notional will become 20000 and chore can be placed with
        # maximum 19000 chore_notional
        min_chore_notional = plan_limits.min_chore_notional - plan_limits.min_chore_notional_allowance

        time.sleep(1)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = (f"blocked chore_opportunity {plan_limits.min_chore_notional_allowance} applied "
                     f"{min_chore_notional} < chore_usd_notional")
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_min_chore_notional_breach_in_normal_plan_mode2(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests the enforcement of minimum chore notional limits in normal planegy mode for edge cases
        of min_chore_notional_allowance configuration.

        This test validates that chores with notional value less than min_chore_notional are blocked
        in two specific scenarios:
        1. When min_chore_notional_allowance > min_chore_notional
        2. When min_chore_notional_allowance is None

        Test Flow:
        1. Sets up a bartering pair with initial configurations and market depth
        2. Executes a positive test case with default limits to verify normal chore placement
        3. Tests first negative scenario (min_chore_notional_allowance > min_chore_notional):
           - Sets min_chore_notional_allowance to 21000
           - Sets min_chore_notional to 20000
        4. Tests second negative scenario (min_chore_notional_allowance is None):
           - Sets min_chore_notional_allowance to None
           - Sets min_chore_notional to 19500
        5. Verifies that appropriate alerts are generated for blocked chores in both scenarios

        Key Validations:
        - Confirms successful chore placement under normal conditions
        - Verifies chore blocking in both edge cases
        - Checks for proper alert messages in planegy and contact alerts
        - Validates that min_chore_notional_allowance is not used in threshold calculation
          when it's greater than min_chore_notional or None
    """

    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative check - checking min_chore_notional_allowance > min_chore_notional
        # updating plan_limits
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)
        plan_limits.min_chore_notional_allowance = 21000
        plan_limits.min_chore_notional = 20000.00
        executor_http_client.put_plan_limits_client(plan_limits)

        # based on street_book logic, min_chore_notional will become 20000 and chore can be placed with
        # maximum 19000 chore_notional - min_chore_notional_allowance will not be used in calculating
        # min_chore_notional since min_chore_notional_allowance > min_chore_notional
        min_chore_notional = f"{plan_limits.min_chore_notional=:.2f}"
        time.sleep(1)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = f"blocked chore_opportunity {min_chore_notional} < chore_usd_notional"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative check - checking min_chore_notional_allowance == None
        # updating plan_limits
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)
        plan_limits.min_chore_notional_allowance = None
        plan_limits.min_chore_notional = 19500.00
        executor_http_client.put_plan_limits_client(plan_limits)

        # based on street_book logic, min_chore_notional will become 20000 and chore can be placed with
        # maximum 19000 chore_notional - min_chore_notional_allowance will not be used in calculating
        # min_chore_notional since min_chore_notional_allowance = None
        min_chore_notional = f"{plan_limits.min_chore_notional=:.2f}"
        time.sleep(1)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = f"blocked chore_opportunity {min_chore_notional} < chore_usd_notional"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_min_chore_notional_breach_in_relaxed_plan_mode(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_chore_limits_, refresh_sec_update_fixture):
    """
        Tests the enforcement of minimum chore notional limits in relaxed planegy mode, where the
        minimum chore notional threshold is randomized.

        This test validates that chores with notional value less than a randomly computed
        min_chore_notional are blocked in relaxed planegy mode. The random min_chore_notional
        is generated between min_chore_notional and (min_chore_notional + min_chore_notional_allowance).

        Test Flow:
        1. Sets up a bartering pair with initial configurations and market depth in relaxed mode
        2. Executes a positive test case with default limits to verify normal chore placement
        3. Modifies planegy limits to create a breach condition:
           - Sets min_chore_notional_allowance to 500
           - Sets min_chore_notional to 19500
        4. Attempts to place an chore that should be blocked due to randomized notional limit
        5. Verifies that appropriate alerts are generated and validates the randomized threshold

        Key Validations:
        - Confirms successful chore placement under normal conditions
        - Verifies chore blocking when below randomized threshold
        - Checks for proper alert messages in planegy and contact alerts
        - Validates that the threshold used is truly randomized by ensuring it's different
          from the base min_chore_notional
        - Handles debug mode configurations for testing flexibility

        Prerequisites:
        - Requires properly configured symbol pairs
        - Needs market depth and last barter fixtures
        - Assumes bartering simulator is operational
        - Requires PlanMode_Relaxed configuration
    """
    test_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
    debug_mode = test_config_dict.get("debug_mode")
    if debug_mode:
        debug_residual_mark_seconds_limit = test_config_dict.get("debug_residual_mark_seconds_limit")
        if debug_residual_mark_seconds_limit is not None:
            expected_plan_limits_.residual_restriction.residual_mark_seconds = debug_residual_mark_seconds_limit
        else:
            expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        debug_residual_wait_sec = test_config_dict.get("debug_residual_wait_sec")
        if debug_residual_wait_sec is not None:
            residual_wait_sec = debug_residual_wait_sec
        else:
            residual_wait_sec = 4 * refresh_sec_update_fixture
    else:
        expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 PlanMode.PlanMode_Relaxed))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        debug_max_wait_sec = None
        if debug_mode:
            debug_max_wait_sec = test_config_dict.get("debug_max_wait_sec")

        kwargs = {"expected_chore_event": ChoreEventType.OE_NEW,
                  "expected_symbol": buy_symbol,
                  "executor_web_client": executor_http_client}
        placed_chore_journal = debug_callable_handler(debug_max_wait_sec,
                                                      get_latest_chore_journal_with_event_and_symbol, kwargs)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative check
        # updating plan_limits
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)
        plan_limits.min_chore_notional_allowance = 500
        plan_limits.min_chore_notional = 19500.00
        executor_http_client.put_plan_limits_client(plan_limits)

        # based on street_book logic, min_chore_notional will be random value between 19500 & 20000 and
        # chore can be placed with maximum 19000 chore_notional
        min_chore_notional = f"{plan_limits.min_chore_notional=:.2f}"
        time.sleep(1)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = f"blocked chore_opportunity < min_chore_notional_relaxed limit"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        limit_alert = (
            check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg))

        # Using regex to extract the value after the '<' symbol
        value_pattern = re.compile(r'<\s*(\d+(?:\.\d+)?)')

        match = value_pattern.search(limit_alert.alert_brief)

        if match:
            extracted_value = match.group(1)
            assert extracted_value != expected_plan_limits_.min_chore_notional, \
                ("When plan_mode is relaxed, min_chore_notional is replaced by random value between "
                 "min_chore_notional and min_chore_notional+min_chore_notional_allowance but found value same as"
                 f"expected_chore_limits_.min_chore_notional, "
                 f"expected_chore_limits_.min_chore_notional: {expected_plan_limits_.min_chore_notional}, "
                 f"expected_chore_limits_.min_chore_notional_allowance: "
                 f"{expected_plan_limits_.min_chore_notional_allowance}, "
                 f"extracted_value from alert: {extracted_value}")
        else:
            assert False, "Can't find match to get value after < in alert brief"

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_min_eqt_qty_in_buy_sell_plan(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_chore_limits_, refresh_sec_update_fixture):
    """
        Tests the enforcement of minimum equity quantity limits for both buy and sell chores in a
        bartering planegy.

        This test validates that equity instrument type chores with equity quantity less than the hard-coded minimum
        equity quantity (min_eqt_qty=20) are blocked, while chores above this threshold are allowed
        to be placed.

        Test Flow:
        1. Sets up a bartering pair with initial configurations and market depth
        2. Executes positive test cases:
           - Places a buy chore (px=97, qty=90)
           - Places a sell chore (px=96, qty=90)
        3. Attempts to place a sell chore below minimum equity quantity:
           - Places a sell chore (px=96, qty=10)
        4. Verifies that the chore is blocked and appropriate alerts are generated

        Key Validations:
        - Confirms successful chore placement for chores above min_eqt_qty
        - Verifies chore blocking when quantity is below min_eqt_qty
        - Checks for proper alert messages in planegy and contact alerts
        - Validates behavior for both buy and sell sides of the bartering pair

        Prerequisites:
        - Requires properly configured symbol pairs
        - Needs market depth and last barter fixtures
        - Assumes bartering simulator is operational
        - Requires proper instrument types for both buy and sell sides
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        px = 97
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 96
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                           sell_symbol, executor_http_client)
        last_chore_id = new_chore_journal.chore.chore_id

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Now placing eqt chore with less then min_eqt_qty=20
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 96
        qty = 10
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                           sell_symbol, executor_http_client,
                                                                           expect_no_chore=True,
                                                                           last_chore_id=last_chore_id)

        check_str = f"blocked generated chore, breaches min_eqt_chore_qty hard-coded-limit"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_min_eqt_qty_in_sell_buy_plan(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_chore_limits_, refresh_sec_update_fixture):
    """
        Tests the enforcement of minimum equity quantity limits for a sell-buy planegy.

        This test validates that equity instrument chores with quantities below the hard-coded
        minimum equity quantity (min_eqt_qty=20) are blocked in a planegy configured with
        sell leg1 and buy leg2, while chores above this threshold are allowed through.

        Test Flow:
        1. Sets up a bartering pair with sell-buy configuration
        2. Places valid test chores:
           - Sell chore on leg1 (px=97, qty=90)
           - Buy chore on leg2 (px=96, qty=90)
        3. Attempts to place chore below minimum equity quantity:
           - Buy chore (px=96, qty=10)
        4. Verifies chore blocking and alert generation

        Key Validations:
        - Confirms successful chore placement above min_eqt_qty
        - Verifies chore blocking below min_eqt_qty
        - Checks alert message generation
        - Validates threshold enforcement

    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    leg1_symbol, leg2_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 leg1_side=Side.SELL, leg2_side=Side.BUY))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Positive check
        run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        px = 97
        qty = 90
        place_new_chore(leg1_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              leg1_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 96
        qty = 90
        place_new_chore(leg2_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                           leg2_symbol, executor_http_client)
        last_chore_id = new_chore_journal.chore.chore_id

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Now placing eqt chore with less then min_eqt_qty=20
        run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 96
        qty = 10
        place_new_chore(leg2_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                           leg2_symbol, executor_http_client,
                                                                           expect_no_chore=True,
                                                                           last_chore_id=last_chore_id)

        check_str = f"blocked generated chore, breaches min_eqt_chore_qty hard-coded-limit"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_max_chore_notional_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                   pair_plan_, expected_plan_limits_,
                                   expected_plan_status_, symbol_overview_obj_list,
                                   last_barter_fixture_list, market_depth_basemodel_list,
                                   buy_chore_, sell_chore_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests enforcement of maximum chore notional limits.

        This test validates that chores exceeding the maximum notional value are properly
        blocked. It ensures the system enforces upper bounds on individual chore sizes
        based on their notional value.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Places valid chore within notional limits
        3. Updates chore limits:
           - Sets max_chore_notional to 8000
        4. Attempts to place chore exceeding limit
        5. Verifies blocking and alerts

        Key Validations:
        - Confirms successful chore placement within limits
        - Verifies chore blocking above max notional
        - Checks appropriate alert generation
        - Validates notional calculations
        - Ensures limit updates take effect immediately
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))
    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative check
        # updating chore_limits
        chore_limits = email_book_service_native_web_client.get_chore_limits_client(1)
        # based on street_book logic, max_chore_notional set to 8000 and
        # chore can be placed with minimum 8075 chore_notional
        chore_limits.max_chore_notional = 8000
        email_book_service_native_web_client.put_chore_limits_client(chore_limits)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = f"blocked generated chore, breaches max_chore_notional limit, expected less than"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        limit_alert = (
            check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg))
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_max_chore_qty_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                              pair_plan_, expected_plan_limits_,
                              expected_plan_status_, symbol_overview_obj_list,
                              last_barter_fixture_list, market_depth_basemodel_list,
                              buy_chore_, sell_chore_,
                              max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests enforcement of maximum chore quantity limits.

        This test validates that chores exceeding the maximum quantity limit are properly
        blocked. It ensures the system enforces upper bounds on individual chore sizes
        based on quantity.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Places valid chore within quantity limits
        3. Updates chore limits:
           - Sets max_chore_qty to 80
        4. Attempts to place chore exceeding limit
        5. Verifies blocking and alerts

        Key Validations:
        - Confirms successful chore placement within limits
        - Verifies chore blocking above max quantity
        - Checks appropriate alert generation
        - Validates quantity calculations
        - Ensures limit updates take effect immediately
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # updating chore_limits
        chore_limits = email_book_service_native_web_client.get_chore_limits_client(1)
        # based on street_book logic, max_chore_qty set to 8000 and
        # chore can be placed with minimum 85 qty
        chore_limits.max_chore_qty = 80
        email_book_service_native_web_client.put_chore_limits_client(chore_limits)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = "blocked generated chore, breaches max_chore_qty limit, expected less than"
        assert_fail_msg = f"can't find alert_str: {check_str} in plan or contact_alerts"
        time.sleep(5)
        # assert in call
        limit_alert = (
            check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg))

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_with_wrong_tob(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                            pair_plan_, expected_plan_limits_,
                                            expected_plan_status_, symbol_overview_obj_list,
                                            last_barter_fixture_list, market_depth_basemodel_list,
                                            buy_chore_, sell_chore_, max_loop_count_per_side,
                                            refresh_sec_update_fixture):
    """
        Tests chore placement validation when the Top of Book (TOB) data is invalid or missing.

        This test verifies that chores are blocked when the Top of Book data is either missing
        or contains invalid prices (0 or null). It ensures the system properly handles edge cases
        in market data quality.

        Test Flow:
        1. Sets up bartering environment with initial conditions
        2. Creates test scenarios with invalid TOB data:
           - Sets last barter price to 0
           - Creates missing TOB conditions
        3. Attempts chore placement under invalid conditions
        4. Verifies proper handling and alerts
        5. Validates system recovery with valid TOB data

        Key Validations:
        - Confirms chore blocking when TOB data is invalid
        - Verifies appropriate alert generation
        - Checks system behavior with missing market data
        - Validates recovery when valid TOB data is restored
        - Ensures proper breach threshold calculations

        Notes:
        - Tests both buy and sell chore scenarios
        - Includes validation of alert message content
        - Verifies proper error handling in edge cases
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 [], market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        sample_buy_last_barter = copy.deepcopy(last_barter_fixture_list[0])
        sample_buy_last_barter["px"] = 0
        sample_sell_last_barter = copy.deepcopy(last_barter_fixture_list[1])
        sample_sell_last_barter["px"] = 0
        run_last_barter(buy_symbol, sell_symbol,
                       [sample_buy_last_barter, sample_sell_last_barter],
                       active_pair_plan.cpp_port)

        # Negative Check - since buy tob is missing last_barter and sell side last_barter.px is 0 both
        # chores must get blocked
        px = 100
        qty = 90
        check_str = f"blocked generated chore, symbol: {buy_symbol}, side: Side.BUY as " \
                    f"top_of_book.last_barter.px is none or 0"
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)

        check_str = ("blocked generated chore, high_breach_px=None / low_breach_px=None is returned None "
                     f"from get_breach_threshold_px for symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

        px = 100
        qty = 90
        check_str = f"blocked generated chore, symbol: {sell_symbol}, side: Side.SELL as " \
                    f"top_of_book.last_barter.px is none or 0"
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)

        check_str = ("blocked generated chore, high_breach_px=None / low_breach_px=None is returned None "
                     f"from get_breach_threshold_px for symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

        # Positive check - if tob is fine then chores must get placed

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        # required to make sell side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)

        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_with_unsupported_side(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                   pair_plan_, expected_plan_limits_,
                                                   expected_plan_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   buy_chore_, sell_chore_,
                                                   max_loop_count_per_side, refresh_sec_update_fixture):
    """
       Tests the system's handling of chore placement attempts with unsupported bartering sides.

       This test validates that the system properly blocks chores when an unsupported or
       unspecified bartering side is provided. It ensures robust handling of invalid chore
       side specifications.

       Test Flow:
       1. Sets up bartering pair with initial configurations
       2. Executes a positive test case with valid chore side
       3. Attempts to place chores with unsupported sides:
          - Uses Side.SIDE_UNSPECIFIED
       4. Verifies proper blocking and alert generation
       5. Validates system maintains integrity

       Key Validations:
       - Confirms successful chore placement with valid sides
       - Verifies proper blocking of unsupported sides
       - Checks alert message generation and content
       - Ensures system stability during invalid attempts
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))
    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated unsupported side"
        assert_fail_msg = "Could not find any alert containing message to block chores due to unsupported side"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.SIDE_UNSPECIFIED, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_with_0_depth_px(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                             pair_plan_, expected_plan_limits_,
                                             expected_plan_status_, symbol_overview_obj_list,
                                             last_barter_fixture_list, market_depth_basemodel_list,
                                             buy_chore_, sell_chore_,
                                             max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests the system's handling of chore placement when market depth prices are zero, since no
        market depth is found.

        This test validates that chores are properly blocked when market depth prices
        are zero or invalid, ensuring the system maintains price integrity and prevents
        potentially erroneous barters.

        Test Flow:
        1. Sets up bartering environment without initial market depth
        2. Attempts chore placement with zero market depth prices
        3. Verifies proper blocking and alert generation
        4. Adds valid market depth data
        5. Confirms system recovery and proper chore processing

        Key Validations:
        - Verifies chore blocking with zero market depth prices
        - Confirms appropriate alert generation
        - Checks system recovery with valid market depth
        - Validates breach threshold calculations
        - Ensures proper handling of price validation logic

        Prerequisites:
        - Requires properly configured symbol pairs
        - Needs last barter fixtures
        - Bartering simulator must be operational

        Notes:
        - Includes both negative and positive test cases
        - Tests system resilience to invalid market data
        - Verifies proper error handling and recovery
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, []))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Negative Check: currently no market_depth exists so default px_by_max_level=0 will be used

        # placing new non-systematic new_chore
        time.sleep(5)
        px = 100
        qty = 90
        check_str = f"blocked generated chore, system_symbol='{buy_symbol}', side=<Side.BUY: 'BUY'>, " \
                    f"unable to find valid px based on chore_limits.max_px_levels"
        assert_fail_msg = "Could not find any alert containing message to block chores due to 0 market depth px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)

        check_str = ("blocked generated chore, high_breach_px=None / low_breach_px=None is returned None from "
                     f"get_breach_threshold_px for symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

        # positive test case: Putting valid market depth
        create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list, active_pair_plan.cpp_port)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_with_none_aggressive_quote(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                        pair_plan_, expected_plan_limits_,
                                                        expected_plan_status_, symbol_overview_obj_list,
                                                        last_barter_fixture_list, market_depth_basemodel_list,
                                                        buy_chore_, sell_chore_,
                                                        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement validation when aggressive quote data is missing or invalid.

        This test verifies that the system properly handles scenarios where aggressive quote
        data (best bid/ask) is missing or incomplete, ensuring proper chore validation and
        blocking under such conditions.

        Test Flow:
        1. Sets up bartering pair with incomplete market depth data
        2. Creates scenarios with missing aggressive quotes:
           - Omits zeroth level market depth
           - Creates incomplete TOB conditions
        3. Attempts chore placement under these conditions
        4. Verifies proper handling and alerts
        5. Tests system recovery with complete data

        Key Validations:
        - Confirms chore blocking with incomplete quotes
        - Verifies appropriate alert generation
        - Checks system behavior with partial market data
        - Validates proper threshold calculations
        - Ensures system recovery with complete data

        Notes:
        - Tests both buy and sell scenarios
        - Includes validation of quote completeness
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, []))

    # not creating sell symbol's 0th bid md and buy_symbol's 0th ask md
    buy_zeroth_ask_md = None
    sell_zeroth_bid_md = None
    for md in market_depth_basemodel_list:
        if md.symbol == buy_symbol:
            if md.side == TickType.ASK and md.position == 0:
                buy_zeroth_ask_md = md
            else:
                created_market_depth = cpp_create_market_depth_client(active_pair_plan.cpp_port, md)
                created_market_depth.id = None
                created_market_depth.cumulative_avg_px = None
                created_market_depth.cumulative_notional = None
                created_market_depth.cumulative_qty = None
                assert created_market_depth == md, \
                    f"Mismatch created market_depth: expected {md} received {created_market_depth}"
        else:
            if md.side == TickType.BID and md.position == 0:
                sell_zeroth_bid_md = md
            else:
                created_market_depth = cpp_create_market_depth_client(active_pair_plan.cpp_port, md)
                created_market_depth.id = None
                created_market_depth.cumulative_avg_px = None
                created_market_depth.cumulative_notional = None
                created_market_depth.cumulative_qty = None
                assert created_market_depth == md, \
                    f"Mismatch created market_depth: expected {md} received {created_market_depth}"

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Negative Check
        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = (f"blocked generated Side.BUY chore, symbol: {buy_symbol}, side: Side.BUY as "
                     f"tob has incomplete data")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)
        check_str = ("blocked generated chore, high_breach_px=None / low_breach_px=.* is returned None from "
                     f"get_breach_threshold_px for symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = (f"blocked generated Side.SELL chore, symbol: {sell_symbol}, side: Side.SELL as "
                     f"tob has incomplete data")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)
        check_str = ("blocked generated chore, high_breach_px=.* / low_breach_px=None is returned None from "
                     f"get_breach_threshold_px for symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_msg)

        # creating earlier skipped market depths also
        for md in [buy_zeroth_ask_md, sell_zeroth_bid_md]:
            created_market_depth = cpp_create_market_depth_client(active_pair_plan.cpp_port, md)
            created_market_depth.id = None
            created_market_depth.cumulative_avg_px = None
            created_market_depth.cumulative_notional = None
            created_market_depth.cumulative_qty = None
            assert created_market_depth == md, \
                f"Mismatch created market_depth: expected {md} received {created_market_depth}"
            time.sleep(1)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))
        time.sleep(1)

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)

        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# FIXME: currently failing since executor doesn't start place chore checks without tob
def _test_px_check_if_tob_none(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                               pair_plan_, expected_plan_limits_,
                               expected_start_status_, symbol_overview_obj_list,
                               last_barter_fixture_list, market_depth_basemodel_list,
                               top_of_book_list_, refresh_sec_update_fixture):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # explicitly setting waived_initial_chores to 10 for this test case
    active_pair_plan, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

        # Deleting all tobs
        tob_list = executor_http_client.get_all_top_of_book_client()
        for tob in tob_list:
            executor_http_client.delete_top_of_book_client(tob.id, return_obj_copy=False)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated chore, unable to conduct px checks: top_of_book is sent None for plan"
        assert_fail_message = "Could not find any alert containing message to block chores due to no tob"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client,
                                                                      )
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _put_n_assert_market_depth(active_pair_plan_cpp_port, market_depth_basemodel):
    updated_market_depth = cpp_put_market_depth_client(active_pair_plan_cpp_port,
                                                       market_depth_basemodel)

    assert math.isclose(updated_market_depth.cumulative_avg_px, market_depth_basemodel.cumulative_avg_px), \
        (f"Mismatched market_depth.cumulative_avg_px, expected {market_depth_basemodel.cumulative_avg_px}, "
         f"updated {updated_market_depth.cumulative_avg_px}")
    updated_market_depth.cumulative_avg_px = market_depth_basemodel.cumulative_avg_px
    assert updated_market_depth == market_depth_basemodel, \
        f"Mismatched market_depth: expected: {market_depth_basemodel}, updated: {updated_market_depth}"

@pytest.mark.nightly
def test_breach_threshold_px_for_max_buy_n_min_sell_px_by_basis_points(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests price threshold enforcement based on basis point calculations for buy and sell chores.

        This test validates the system's enforcement of maximum buy and minimum sell price
        thresholds calculated using basis points from reference prices. It ensures chores
        outside these thresholds are properly blocked.

        Test Flow:
        1. Sets up bartering environment with specific market conditions
        2. Tests buy chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
        3. Tests sell chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
        4. Verifies proper alert generation for violations

        Key Validations:
        - Confirms proper calculation of basis point thresholds
        - Verifies chore blocking outside thresholds
        - Validates successful placement within thresholds
        - Checks alert message generation and content
        - Ensures proper price validation logic

        Prerequisites:
        - Requires properly configured symbol pairs
        - Needs market depth and last barter fixtures
        - Bartering simulator must be operational

        Notes:
        - Tests both buy and sell side threshold calculations
        - Includes comprehensive price validation
        - Verifies proper handling of basis point calculations
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # updating sell market depth to make its max depth px value greater than calculated max_px_by_basis_point
        sell_px = 85
        stored_market_depths = cpp_get_all_market_depth_client(active_pair_plan.cpp_port)
        for market_depth_basemodel in stored_market_depths:
            if market_depth_basemodel.symbol == buy_symbol:
                if market_depth_basemodel.side == "ASK":
                    market_depth_basemodel.px = sell_px + (5 * market_depth_basemodel.position)
                market_depth_basemodel.exch_time = get_utc_date_time()
                market_depth_basemodel.arrival_time = get_utc_date_time()

                _put_n_assert_market_depth(active_pair_plan.cpp_port, market_depth_basemodel)
                time.sleep(1)

        # below are computes expected for HIGH breach px:
        # ask_quote_px = 85
        # bid_quote_px = 99
        # last_barter_reference_px = 116
        # aggressive_quote_px = 85
        # with this:
        # max_px_by_basis_point = 97.75
        # max_px_by_deviation = 139.2
        # px_by_max_level = 105
        # >>> breach_threshold_px i.e. min of above is max_px_by_basis_point = 97.75
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for buy chore - chore block since px > max_breach_threshold_px
        # placing new non-systematic new_chore
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 98
        qty = 90
        check_str = "blocked generated Side.BUY chore, chore-px=98.0 > high_breach_px=97.750; low_breach_px=95.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # below are computes expected for LOW breach px:
        # ask_quote_px = 85
        # bid_quote_px = 99
        # last_barter_reference_px = 116
        # aggressive_quote_px = 99
        # with this:
        # min_px_by_basis_point = 84.15
        # min_px_by_deviation = 92.8
        # px_by_max_level = 95
        # >>> breach_threshold_px i.e. max of above is px_by_max_level = 95
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for buy chore - chore block since px < min_breach_threshold_px
        # placing new non-systematic new_chore
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 94
        qty = 90
        check_str = "blocked generated Side.BUY chore, chore-px=94.0 < low_breach_px=95.000; high_breach_px=97.750"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Positive check for buy chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

        px = 97
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # checking min_px_by_basis_point

        # updating last_barter for sell symbol
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        sample_last_barter_obj = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
        sample_last_barter_obj.px = 100
        sample_last_barter_obj.exch_time = get_utc_date_time()
        sample_last_barter_obj.arrival_time = get_utc_date_time()
        cpp_create_last_barter_client(active_pair_plan.cpp_port, sample_last_barter_obj)

        # updating buy market depth to make its max depth px value less than calculated max_px_by_basis_point
        buy_px = 100
        stored_market_depths = cpp_get_all_market_depth_client(active_pair_plan.cpp_port)
        for pos in range(4, -1, -1):
            for market_depth_basemodel in stored_market_depths:
                if market_depth_basemodel.symbol == sell_symbol:
                    if market_depth_basemodel.side == "BID" and market_depth_basemodel.position == pos:
                        market_depth_basemodel.px = buy_px - (5 * market_depth_basemodel.position)
                        market_depth_basemodel.exch_time = get_utc_date_time()
                        market_depth_basemodel.arrival_time = get_utc_date_time()

                        cpp_put_market_depth_client(active_pair_plan.cpp_port, market_depth_basemodel)
                        time.sleep(1)
                        break

        # below are computes expected for LOW breach px:
        # ask_quote_px = 121
        # bid_quote_px = 100
        # last_barter_reference_px = 100
        # aggressive_quote_px = 100
        # with this:
        # min_px_by_basis_point = 85
        # min_px_by_deviation = 80
        # px_by_max_level = 80
        # >>> breach_threshold_px i.e. max of above is min_px_by_basis_point = 85
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for sell chore - chore block since px < min_breach_threshold_px
        # placing new non-systematic new_chore
        # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 84
        qty = 90
        check_str = "blocked generated Side.SELL chore, chore-px=84.0 < low_breach_px=85.000; high_breach_px=120.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # below are computes expected for HIGH breach px:
        # ask_quote_px = 121
        # bid_quote_px = 100
        # last_barter_reference_px = 100
        # aggressive_quote_px = 121
        # with this:
        # max_px_by_basis_point = 139.15
        # max_px_by_deviation = 120
        # px_by_max_level = 125
        # >>> breach_threshold_px i.e. min of above is max_px_by_deviation = 120
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for sell chore - chore block since px > max_breach_threshold_px
        # placing new non-systematic new_chore
        # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        px = 121
        qty = 90
        check_str = "blocked generated Side.SELL chore, chore-px=121.0 > high_breach_px=120.000; low_breach_px=85.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Positive check for sell chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px
        # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        sample_last_barter_obj = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
        sample_last_barter_obj.px = 100
        sample_last_barter_obj.exch_time = get_utc_date_time()
        sample_last_barter_obj.arrival_time = get_utc_date_time()
        cpp_create_last_barter_client(active_pair_plan.cpp_port, sample_last_barter_obj)

        px = 86
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_for_min_buy_n_max_sell_px_by_bbo_n_tick_size(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests price threshold enforcement based on BBO (Best Bid/Offer) and tick size calculations.

        This test validates the system's enforcement of minimum buy and maximum sell price
        thresholds calculated using BBO and tick size rules. It ensures chores are properly
        validated against these thresholds.

        Test Flow:
        1. Configures test environment with specific BBO conditions
        2. Tests buy chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Validates against BBO-based thresholds
           - Checks tick size compliance
        3. Tests sell chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Validates against BBO-based thresholds
           - Checks tick size compliance
        4. Verifies alert generation for violations

        Key Validations:
        - Confirms proper calculation of BBO thresholds
        - Verifies tick size compliance
        - Validates chore blocking outside thresholds
        - Checks alert generation and content
        - Ensures proper price validation logic

        Notes:
        - Tests both buy and sell side validations
        - Includes tick size compliance checks
        - Verifies proper threshold calculations
    """
    buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]

    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["max_spread_in_bips"] = 5000   # making it very large
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))

    try:
        # updating bid market depth to make its lowest depth px value greater than calculated max_px_by_basis_point
        buy_bid_px = 100
        sell_bid_px = 85
        sell_ask_px = 80
        for market_depth_basemodel in market_depth_basemodel_list:
            if market_depth_basemodel.symbol == buy_symbol and market_depth_basemodel.side == "BID":
                market_depth_basemodel.px = buy_bid_px
                buy_bid_px -= 1
            elif market_depth_basemodel.symbol == sell_symbol:
                if market_depth_basemodel.side == "ASK":
                    market_depth_basemodel.px = sell_ask_px
                    sell_ask_px += 5
                else:
                    market_depth_basemodel.px = sell_bid_px
                    sell_bid_px -= 1

        expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        residual_wait_sec = 4 * refresh_sec_update_fixture
        buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
            underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                     expected_plan_status_, symbol_overview_obj_list,
                                                     last_barter_fixture_list, market_depth_basemodel_list))

        config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

        buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
        sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            buy_sample_last_barter = LastBarterBaseModel.from_dict(last_barter_fixture_list[0])
            buy_sample_last_barter.px = 80
            buy_sample_last_barter.exch_time = get_utc_date_time()
            buy_sample_last_barter.arrival_time = get_utc_date_time()
            buy_sample_last_barter.market_barter_volume.participation_period_last_barter_qty_sum = 2000
            cpp_create_last_barter_client(active_pair_plan.cpp_port, buy_sample_last_barter)

            # below are computes expected for HIGH breach px:
            # ask_quote_px = 121
            # bid_quote_px = 100
            # last_barter_reference_px = 80
            # aggressive_quote_px = 121
            # with this:
            # max_px_by_basis_point = 139.15
            # max_px_by_deviation = 96
            # px_by_max_level = 125
            # >>> breach_threshold_px i.e. min of above is max_px_by_deviation=96
            # min_px_by_bbo_n_tick_size = 121.001
            # min_px_by_last_barter_n_tick_size = 80.001
            # >>> min_px_by_tick_size i.e. max of above is min_px_by_bbo_n_tick_size=121.001
            # >>> final breach_threshold_px i.e. max of min_px_by_tick_size and breach_threshold_px is
            #     min_px_by_tick_size=121.001

            # Negative Check for buy chore - chore block since px > max_breach_threshold_px
            # placing new non-systematic new_chore
            px = 122
            qty = 90
            check_str = ("blocked generated Side.BUY chore, chore-px=122.0 > "
                         "high_breach_px=121.001; low_breach_px=79.999")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # below are computes expected for LOW breach px:
            # ask_quote_px = 121
            # bid_quote_px = 100
            # last_barter_reference_px = 80
            # aggressive_quote_px = 100
            # with this:
            # min_px_by_basis_point = 85
            # min_px_by_deviation = 64
            # px_by_max_level = 96
            # >>> breach_threshold_px i.e. max of above is px_by_max_level = 96
            # max_px_by_bbo_n_tick_size = 99.999
            # max_px_by_last_barter_n_tick_size = 79.999
            # >>> max_px_by_tick_size i.e. min of above is max_px_by_last_barter_n_tick_size = 79.999
            # >>> final breach_threshold_px i.e. min of min_px_by_tick_size and breach_threshold_px is
            #     min_px_by_tick_size=79.999

            # Negative Check for buy chore - chore block since px < min_breach_threshold_px
            # placing new non-systematic new_chore
            px = 79
            qty = 90
            check_str = ("blocked generated Side.BUY chore, chore-px=79.0 < "
                         "low_breach_px=79.999; high_breach_px=121.001")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # Positive check for buy chore - chore places since min_breach_threshold_px < px =< max_breach_threshold_px
            px = 121
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
            # Internally checks if chore_journal is found with OE_NEW state
            placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                  buy_symbol, executor_http_client)

            if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
                time.sleep(residual_wait_sec)

            sell_sample_last_barter = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
            sell_sample_last_barter.px = 110
            sell_sample_last_barter.exch_time = get_utc_date_time()
            sell_sample_last_barter.arrival_time = get_utc_date_time()
            cpp_create_last_barter_client(active_pair_plan.cpp_port, sell_sample_last_barter)

            # below are computes expected for LOW breach px:
            # ask_quote_px = 80
            # bid_quote_px = 85
            # last_barter_reference_px = 110
            # aggressive_quote_px = 85
            # with this:
            # min_px_by_basis_point = 73
            # min_px_by_deviation = 88
            # px_by_max_level = 81
            # >>> breach_threshold_px i.e. max of above is min_px_by_deviation=88
            # max_px_by_bbo_n_tick_size = 84.99
            # max_px_by_last_barter_n_tick_size = 109.99
            # >>> max_px_by_tick_size i.e. min of above is min_px_by_bbo_n_tick_size=84.99
            # >>> final breach_threshold_px i.e. min of max_px_by_tick_size and breach_threshold_px is
            #     min_px_by_tick_size=84.99

            # Negative Check for sell chore - chore block since px < min_breach_threshold_px
            # placing new non-systematic new_chore
            px = 84
            qty = 90
            check_str = ("blocked generated Side.SELL chore, chore-px=84.0 < low_breach_px=84.999; "
                         "high_breach_px=110.001")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # below are computes expected for HIGH breach px :
            # ask_quote_px = 80
            # bid_quote_px = 85
            # last_barter_reference_px = 110
            # aggressive_quote_px = 80
            # with this:
            # max_px_by_basis_point = 92
            # max_px_by_deviation = 132
            # px_by_max_level = 100
            # >>> breach_threshold_px i.e. min of above is max_px_by_basis_point = 92
            # min_px_by_bbo_n_tick_size = 80.001
            # min_px_by_last_barter_n_tick_size = 110.001
            # >>> min_px_by_tick_size i.e. max of above is min_px_by_last_barter_n_tick_size = 110.001
            # >>> final breach_threshold_px i.e. max of min_px_by_tick_size and breach_threshold_px is
            #     min_px_by_last_barter_n_tick_size = 110.001

            # Negative Check for sell chore - chore block since px > max_breach_threshold_px
            # placing new non-systematic new_chore
            px = 111
            qty = 90
            check_str = ("blocked generated Side.SELL chore, chore-px=111.0 > high_breach_px=110.001; "
                         "low_breach_px=84.999")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # Positive check for sell chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px
            px = 85
            qty = 90
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

            # Internally checks if chore_journal is found with OE_NEW state
            placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                  sell_symbol, executor_http_client)

        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_for_min_buy_n_max_sell_px_by_last_barter_n_tick_size(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests price threshold enforcement based on last barter prices and tick size rules.

        This test validates the system's enforcement of minimum buy and maximum sell price
        thresholds calculated using last barter prices and tick size rules. It ensures chores
        are properly validated against these thresholds.

        Test Flow:
        1. Sets up test environment with specific last barter prices
        2. Tests buy chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Places chores relative to last barter price
           - Validates against tick size rules
        3. Tests sell chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Places chores relative to last barter price
           - Validates against tick size rules
        4. Verifies proper alert generation

        Key Validations:
        - Confirms proper calculation of last barter price thresholds
        - Verifies tick size compliance
        - Validates chore blocking outside thresholds
        - Checks alert message generation
        - Ensures proper price validation logic

        Notes:
        - Tests both buy and sell side validations
        - Includes tick size compliance checks
        - Verifies proper threshold calculations
    """
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["max_spread_in_bips"] = 5000   # making it very large
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))

    try:
        expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        residual_wait_sec = 4 * refresh_sec_update_fixture
        buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
            underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                     expected_plan_status_, symbol_overview_obj_list,
                                                     last_barter_fixture_list, market_depth_basemodel_list))

        config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

        buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
        sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            # updating sell market depth to make its max depth px value greater than calculated max_px_by_basis_point
            sell_px = 85
            stored_market_depths = cpp_get_all_market_depth_client(active_pair_plan.cpp_port)
            for market_depth_basemodel in stored_market_depths:
                if market_depth_basemodel.symbol == buy_symbol:
                    if market_depth_basemodel.side == "ASK":
                        market_depth_basemodel.px = sell_px + (5 * market_depth_basemodel.position)
                    market_depth_basemodel.exch_time = get_utc_date_time()
                    market_depth_basemodel.arrival_time = get_utc_date_time()

                    _put_n_assert_market_depth(active_pair_plan.cpp_port, market_depth_basemodel)
                    time.sleep(1)

            # below are computes expected for HIGH breach px:
            # ask_quote_px = 99
            # bid_quote_px = 85
            # last_barter_reference_px = 116
            # aggressive_quote_px = 99
            # with this:
            # max_px_by_basis_point = 113.85
            # max_px_by_deviation = 139.2
            # px_by_max_level = 105
            # >>> breach_threshold_px i.e. min of above is px_by_max_level = 105
            # min_px_by_bbo_n_tick_size = 99.001
            # min_px_by_last_barter_n_tick_size = 116.001
            # >>> min_px_by_tick_size i.e. max of above is min_px_by_last_barter_n_tick_size = 116.001
            # >>> final breach_threshold_px i.e. max of min_px_by_tick_size and breach_threshold_px is
            #     min_px_by_last_barter_n_tick_size = 116.001

            # Negative Check for buy chore - chore block since px > max_breach_threshold_px
            # placing new non-systematic new_chore
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
            px = 117
            qty = 90
            check_str = ("blocked generated Side.BUY chore, chore-px=117.0 > high_breach_px=116.001; "
                         "low_breach_px=95.000")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # below are computes expected for LOW breach px:
            # ask_quote_px = 121
            # bid_quote_px = 130
            # last_barter_reference_px = 116
            # aggressive_quote_px = 121
            # with this:
            # min_px_by_basis_point = 102.85
            # min_px_by_deviation = 92.8
            # px_by_max_level = 95
            # >>> breach_threshold_px i.e. max of above is px_by_max_level = 95
            # max_px_by_bbo_n_tick_size = 120.999
            # max_px_by_last_barter_n_tick_size = 115.999
            # >>> max_px_by_tick_size i.e. min of above is max_px_by_last_barter_n_tick_size = 115.999
            # >>> final breach_threshold_px i.e. min of max_px_by_tick_size and breach_threshold_px is
            #     px_by_max_level = 95

            # Negative Check for buy chore - chore block since px < min_breach_threshold_px>
            # placing new non-systematic new_chore
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
            px = 94
            qty = 90
            check_str = "blocked generated Side.BUY chore, chore-px=94.0 < low_breach_px=95.000; high_breach_px=116.001"
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # Positive check for buy chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

            px = 116
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

            # Internally checks if chore_journal is found with OE_NEW state
            placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                  buy_symbol, executor_http_client)

            if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
                time.sleep(residual_wait_sec)

            # checking min_px_by_basis_point

            # updating last_barter for sell symbol
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
            sample_last_barter_obj = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
            sample_last_barter_obj.px = 100
            sample_last_barter_obj.exch_time = get_utc_date_time()
            sample_last_barter_obj.arrival_time = get_utc_date_time()
            cpp_create_last_barter_client(active_pair_plan.cpp_port, sample_last_barter_obj)

            # updating buy market depth to make its max depth px value less than calculated max_px_by_basis_point
            buy_px = 130
            stored_market_depths = cpp_get_all_market_depth_client(active_pair_plan.cpp_port)
            for pos in range(4, -1, -1):
                for market_depth_basemodel in stored_market_depths:
                    if market_depth_basemodel.symbol == sell_symbol:
                        if market_depth_basemodel.side == "BID" and market_depth_basemodel.position == pos:
                            market_depth_basemodel.px = buy_px - (5 * market_depth_basemodel.position)
                            market_depth_basemodel.exch_time = get_utc_date_time()
                            market_depth_basemodel.arrival_time = get_utc_date_time()

                            cpp_put_market_depth_client(active_pair_plan.cpp_port, market_depth_basemodel)
                            time.sleep(1)
                            break

            # below are computes expected for LOW breach px:
            # ask_quote_px = 121
            # bid_quote_px = 130
            # last_barter_reference_px = 100
            # aggressive_quote_px = 130
            # with this:
            # min_px_by_basis_point = 110.5
            # min_px_by_deviation = 80
            # px_by_max_level = 80
            # >>> breach_threshold_px i.e. max of above is min_px_by_basis_point = 110.5
            # max_px_by_bbo_n_tick_size = 129.999
            # max_px_by_last_barter_n_tick_size = 99.999
            # >>> max_px_by_tick_size i.e. min of above is max_px_by_last_barter_n_tick_size = 99.999
            # >>> final breach_threshold_px i.e. min of max_px_by_tick_size and breach_threshold_px is
            #     max_px_by_last_barter_n_tick_size = 99.999

            # Negative Check for sell chore - chore block since px < min_breach_threshold_px
            # placing new non-systematic new_chore
            # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
            px = 98
            qty = 90
            check_str = ("blocked generated Side.SELL chore, chore-px=98.0 < low_breach_px=99.999; "
                         "high_breach_px=121.001")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # below are computes expected for HIGH breach px:
            # ask_quote_px = 121
            # bid_quote_px = 130
            # last_barter_reference_px = 100
            # aggressive_quote_px = 121
            # with this:
            # max_px_by_basis_point = 139.15
            # max_px_by_deviation = 120
            # px_by_max_level = 125
            # >>> breach_threshold_px i.e. min of above is max_px_by_deviation = 120
            # min_px_by_bbo_n_tick_size = 121.001
            # min_px_by_last_barter_n_tick_size = 100.001
            # >>> min_px_by_tick_size i.e. max of above is min_px_by_bbo_n_tick_size = 121.001
            # >>> final breach_threshold_px i.e. max of max_px_by_tick_size and breach_threshold_px is
            #     min_px_by_bbo_n_tick_size = 121.001

            # Negative Check for sell chore - chore block since px > max_breach_threshold_px
            # placing new non-systematic new_chore
            # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
            px = 122
            qty = 90
            check_str = ("blocked generated Side.SELL chore, chore-px=122.0 > high_breach_px=121.001; "
                         "low_breach_px=99.999")
            assert_fail_message = f"cant find any alert with msg: {check_str!r}"
            handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                          check_str, assert_fail_message,
                                                                          active_pair_plan, executor_http_client)

            # Positive check for sell chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px
            # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
            sample_last_barter_obj = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
            sample_last_barter_obj.px = 100
            sample_last_barter_obj.exch_time = get_utc_date_time()
            sample_last_barter_obj.arrival_time = get_utc_date_time()
            cpp_create_last_barter_client(active_pair_plan.cpp_port, sample_last_barter_obj)

            px = 100
            qty = 90
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

            # Internally checks if chore_journal is found with OE_NEW state
            placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                  sell_symbol, executor_http_client)

        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_for_buy_max_n_sell_min_px_by_deviation(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests price threshold enforcement based on maximum buy and minimum sell price deviations.

        This test validates the system's enforcement of price thresholds calculated using
        allowed deviations from reference prices. It ensures chores outside the allowed
        deviation ranges are properly blocked.

        Test Flow:
        1. Sets up test environment with reference prices
        2. Tests buy chore scenarios:
           - Places chores with various deviations
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Checks threshold compliance
        3. Tests sell chore scenarios:
           - Places chores with various deviations
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Checks threshold compliance
        4. Verifies alert generation

        Key Validations:
        - Confirms proper calculation of deviation thresholds
        - Verifies chore blocking outside deviation limits
        - Validates successful placement within limits
        - Checks alert message generation
        - Ensures proper price validation logic

        Notes:
        - Tests both buy and sell side validations
        - Includes deviation calculation checks
        - Verifies proper threshold enforcement
    """
    buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]
    # updating bid market depth to make its lowest depth px value greater than calculated max_px_by_basis_point
    buy_bid_px = 100
    sell_bid_px = 85
    sell_ask_px = 80
    for market_depth_basemodel in market_depth_basemodel_list:
        if market_depth_basemodel.symbol == buy_symbol and market_depth_basemodel.side == "BID":
            market_depth_basemodel.px = buy_bid_px
            buy_bid_px -= 1
        elif market_depth_basemodel.symbol == sell_symbol:
            if market_depth_basemodel.side == "ASK":
                market_depth_basemodel.px = sell_ask_px
                sell_ask_px += 5
            else:
                market_depth_basemodel.px = sell_bid_px
                sell_bid_px -= 1

    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        buy_sample_last_barter = LastBarterBaseModel.from_dict(last_barter_fixture_list[0])
        buy_sample_last_barter.px = 80
        buy_sample_last_barter.exch_time = get_utc_date_time()
        buy_sample_last_barter.arrival_time = get_utc_date_time()
        buy_sample_last_barter.market_barter_volume.participation_period_last_barter_qty_sum = 2000
        cpp_create_last_barter_client(active_pair_plan.cpp_port, buy_sample_last_barter)

        # below are computes expected for HIGH breach px:
        # ask_quote_px = 121
        # bid_quote_px = 100
        # last_barter_reference_px = 80
        # aggressive_quote_px = 121
        # with this:
        # max_px_by_basis_point = 139.15
        # max_px_by_deviation = 96
        # px_by_max_level = 125
        # >>> breach_threshold_px i.e. min of above is max_px_by_deviation = 96
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for buy chore - chore block since px > max_breach_threshold_px
        # placing new non-systematic new_chore
        px = 97
        qty = 90
        check_str = "blocked generated Side.BUY chore, chore-px=97.0 > high_breach_px=96.000; low_breach_px=96.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # below are computes expected for LOW breach px:
        # ask_quote_px = 121
        # bid_quote_px = 100
        # last_barter_reference_px = 80
        # aggressive_quote_px = 100
        # with this:
        # min_px_by_basis_point = 85
        # min_px_by_deviation = 64
        # px_by_max_level = 96
        # >>> breach_threshold_px i.e. max of above is min_px_by_basis_point = 96
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for buy chore - chore block since px < min_breach_threshold_px
        # placing new non-systematic new_chore
        px = 95
        qty = 90
        check_str = "blocked generated Side.BUY chore, chore-px=95.0 < low_breach_px=96.000; high_breach_px=96.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Positive check for buy chore - chore places since min_breach_threshold_px < px =< max_breach_threshold_px
        px = 96
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        sell_sample_last_barter = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
        sell_sample_last_barter.px = 110
        sell_sample_last_barter.exch_time = get_utc_date_time()
        sell_sample_last_barter.arrival_time = get_utc_date_time()
        cpp_create_last_barter_client(active_pair_plan.cpp_port, sell_sample_last_barter)

        # below are computes expected for LOW breach px:
        # ask_quote_px = 80
        # bid_quote_px = 85
        # last_barter_reference_px = 110
        # aggressive_quote_px = 85
        # with this:
        # min_px_by_basis_point = 72.25
        # min_px_by_deviation = 88
        # px_by_max_level = 81
        # >>> breach_threshold_px i.e. max of above is min_px_by_deviation = 88
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for sell chore - chore block since px < min_px_by_deviation = 88
        # placing new non-systematic new_chore
        px = 87
        qty = 90
        check_str = "blocked generated Side.SELL chore, chore-px=87.0 < low_breach_px=88.000; high_breach_px=92.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # below are computes expected for HIGH breach px:
        # ask_quote_px = 80
        # bid_quote_px = 85
        # last_barter_reference_px = 110
        # aggressive_quote_px = 80
        # with this:
        # max_px_by_basis_point = 92
        # max_px_by_deviation = 132
        # px_by_max_level = 100
        # >>> breach_threshold_px i.e. min of above is max_px_by_basis_point = 92
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for sell chore - chore block since px > max_breach_threshold_px
        # placing new non-systematic new_chore
        px = 93
        qty = 90
        check_str = "blocked generated Side.SELL chore, chore-px=93.0 > high_breach_px=92.000; low_breach_px=88.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Positive check for sell chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px
        px = 89
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_breach_threshold_px_for_px_by_max_depth(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                 pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 buy_chore_, sell_chore_,
                                                 max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests price threshold enforcement based on maximum market depth levels.

        This test validates the system's enforcement of price thresholds calculated using
        maximum market depth levels. It ensures chores are properly validated against
        price levels derived from market depth data.

        Test Flow:
        1. Sets up test environment with market depth data
        2. Tests buy chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Checks compliance
        3. Tests sell chore scenarios:
           - Places chores above max threshold
           - Places chores below min threshold
           - Places valid chores within thresholds
           - Checks compliance
        4. Verifies alert generation

        Key Validations:
        - Confirms proper calculation of depth-based thresholds
        - Verifies chore blocking beyond max depth
        - Validates successful placement within limits
        - Checks alert message generation
        - Ensures proper depth level validation

        Notes:
        - Tests both buy and sell side validations
        - Includes market depth level checks
        - Verifies proper threshold calculations
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # updating sell market depth to make its max depth px value lowest of all values
        sell_px = 91
        stored_market_depths = cpp_get_all_market_depth_client(active_pair_plan.cpp_port)
        for market_depth_basemodel in stored_market_depths:
            if market_depth_basemodel.symbol == buy_symbol:
                if market_depth_basemodel.side == "ASK":
                    market_depth_basemodel.px = sell_px + market_depth_basemodel.position
                market_depth_basemodel.exch_time = get_utc_date_time()
                market_depth_basemodel.arrival_time = get_utc_date_time()

                cpp_put_market_depth_client(active_pair_plan.cpp_port, market_depth_basemodel)
                time.sleep(1)

        # max_px_by_basis_point = 109.2
        # max_px_by_deviation = 139.2
        # px_by_max_level = 95
        # >>> min comes px_by_max_level which is being tested in this test

        # below are computes expected for HIGH breach px:
        # ask_quote_px = 91
        # bid_quote_px = 99
        # last_barter_reference_px = 116
        # aggressive_quote_px = 91
        # with this:
        # max_px_by_basis_point = 104.65
        # max_px_by_deviation = 139.2
        # px_by_max_level = 95
        # >>> breach_threshold_px i.e. min of above is px_by_max_level = 95
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for buy chore - chore block since px > max_breach_threshold_px
        # placing new non-systematic new_chore
        px = 96
        qty = 90
        check_str = "blocked generated Side.BUY chore, chore-px=96.0 > high_breach_px=95.000; low_breach_px=95.000"
        assert_fail_message = "Could not find any alert containing message to block chores tob last barter px as 0"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # below are computes expected for LOW breach px:
        # ask_quote_px = 91
        # bid_quote_px = 99
        # last_barter_reference_px = 116
        # aggressive_quote_px = 99
        # with this:
        # min_px_by_basis_point = 84.15
        # min_px_by_deviation = 92.8
        # px_by_max_level = 95
        # >>> breach_threshold_px i.e. max of above is px_by_max_level = 95
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for buy chore - chore block since px < min_breach_threshold_px
        # placing new non-systematic new_chore
        px = 94
        qty = 90
        check_str = "blocked generated Side.BUY chore, chore-px=94.0 < low_breach_px=95.000; high_breach_px=95.000"
        assert_fail_message = "Could not find any alert containing message to block chores tob last barter px as 0"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Positive check for buy chore - chore places since min_breach_threshold_px <= px =< max_breach_threshold_px

        px = 95
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # checking min_px_by_basis_point
        sell_sample_last_barter = LastBarterBaseModel.from_dict(last_barter_fixture_list[1])
        sell_sample_last_barter.px = 110
        sell_sample_last_barter.exch_time = get_utc_date_time()
        sell_sample_last_barter.arrival_time = get_utc_date_time()
        cpp_create_last_barter_client(active_pair_plan.cpp_port, sell_sample_last_barter)

        # updating buy market depth to make its max depth px value less than calculated max_px_by_basis_point
        buy_px = 100
        stored_market_depths = cpp_get_all_market_depth_client(active_pair_plan.cpp_port)
        for pos in range(4, -1, -1):
            for market_depth_basemodel in stored_market_depths:
                if market_depth_basemodel.symbol == sell_symbol:
                    if market_depth_basemodel.side == "BID" and market_depth_basemodel.position == pos:
                        market_depth_basemodel.px = buy_px - pos
                        market_depth_basemodel.exch_time = get_utc_date_time()
                        market_depth_basemodel.arrival_time = get_utc_date_time()

                        cpp_put_market_depth_client(active_pair_plan.cpp_port, market_depth_basemodel)
                        time.sleep(1)
                        break

        # min_px_by_basis_point = 85
        # min_px_by_deviation = 88
        # px_by_max_level = 95
        # >>> max comes px_by_max_level which is being tested in this test

        # below are computes expected for LOW breach px:
        # ask_quote_px = 121
        # bid_quote_px = 100
        # last_barter_reference_px = 110
        # aggressive_quote_px = 100
        # with this:
        # min_px_by_basis_point = 85
        # min_px_by_deviation = 88
        # px_by_max_level = 96
        # >>> breach_threshold_px i.e. max of above is px_by_max_level = 96
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for sell chore - chore block since px < min_breach_threshold_px
        # placing new non-systematic new_chore
        px = 95
        qty = 90
        check_str = "blocked generated Side.SELL chore, chore-px=95.0 < low_breach_px=96.000; high_breach_px=125.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # below are computes expected for HIGH breach px:
        # ask_quote_px = 121
        # bid_quote_px = 100
        # last_barter_reference_px = 110
        # aggressive_quote_px = 121
        # with this:
        # max_px_by_basis_point = 139.15
        # max_px_by_deviation = 132
        # px_by_max_level = 125
        # >>> breach_threshold_px i.e. min of above is px_by_max_level = 125
        # since spread_in_bips > max_spread_in_bips in this test, breach_threshold_px_by_tick_size
        # will not be considered

        # Negative Check for sell chore - chore block since px < max_breach_threshold_px
        # placing new non-systematic new_chore
        px = 126
        qty = 90
        check_str = "blocked generated Side.SELL chore, chore-px=126.0 > high_breach_px=125.000; low_breach_px=96.000"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Positive check for sell chore - chore places since min_breach_threshold_px < px < max_breach_threshold_px

        px = 97
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# chore limits
def test_max_contract_qty(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                          buy_chore_, sell_chore_, buy_fill_journal_,
                          sell_fill_journal_, expected_buy_chore_snapshot_,
                          expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
                          pair_plan_, expected_plan_limits_, expected_plan_status_,
                          expected_plan_brief_, expected_contact_status_,
                          last_barter_fixture_list, symbol_overview_obj_list,
                          market_depth_basemodel_list, expected_chore_limits_,
                          expected_contact_limits_, max_loop_count_per_side,
                          leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
        Tests enforcement of maximum contract quantity limits.

        This test validates that chores exceeding the maximum contract quantity limit are
        properly blocked. It ensures the system enforces upper bounds on contract-based
        chore sizes.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Places valid chore within contract limits
        3. Updates chore limits:
           - Sets max_contract_qty to a restrictive value
        4. Attempts to place chore exceeding limit
        5. Verifies blocking and alerts

        Key Validations:
        - Confirms successful chore placement within limits
        - Verifies chore blocking above max contract quantity
        - Checks appropriate alert generation
        - Validates contract quantity calculations
        - Ensures limit updates take effect immediately

    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Updating chore_limits for Negative check
        expected_chore_limits_.max_contract_qty = 80
        updated_chore_limits = ChoreLimitsBaseModel.from_kwargs(_id=1, max_contract_qty=80)
        updated_chore_limits = email_book_service_native_web_client.patch_chore_limits_client(
            updated_chore_limits.to_dict(exclude_none=True))
        assert updated_chore_limits == expected_chore_limits_

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated chore, breaches max_contract_qty limit"
        assert_fail_message = "Could not find any alert containing message to block chores " \
                              "due to contract qty breach"
        # placing new non-systematic new_chore
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
        print(f"symbol: {buy_symbol}, Created new_chore obj")

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(
            ChoreEventType.OE_NEW, buy_symbol, executor_http_client, expect_no_chore=True,
            last_chore_id=placed_chore_journal.chore.chore_id)

        time.sleep(5)
        check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan.id, check_str, assert_fail_message)
        assert True
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)


# @@@ deprecated: no street_book can be set to ready without symbol_overview
# def test_plan_limits_with_none_symbol_overview(static_data_, clean_and_set_limits, buy_sell_symbol_list,
#                                                 pair_plan_, expected_plan_limits_,
#                                                 expected_start_status_, symbol_overview_obj_list,
#                                                 last_barter_fixture_list, market_depth_basemodel_list,
#                                                 buy_chore_, sell_chore_,
#                                                 max_loop_count_per_side, residual_wait_sec):
#     # Creating Plan
#     active_pair_plan = create_n_activate_plan(buy_symbol, sell_symbol, copy.deepcopy(pair_plan_),
#                                                 copy.deepcopy(expected_plan_limits_),
#                                                 copy.deepcopy(expected_start_status_))
#
#     # running Last Barter
#     run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list)
#
#     # creating market_depth
#     create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)
#
#     # Adding plan in plan_collection
#     create_if_not_exists_and_validate_plan_collection(active_pair_plan)
#
#     # buy test
#     run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list)
#     loop_count = 1
#     run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, is_non_systematic_run=True)
#
#     # placing new non-systematic new_buy_chore
#     px = 100
#     qty = 90
#     check_str = "blocked generated BUY chore, symbol_overview_tuple missing for symbol"
#     assert_fail_message = "Could not find any alert containing message to block chores due to no symbol_overview"
#     handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
#                                                                   check_str, assert_fail_message)
#     # placing new non-systematic new_sell_chore
#     px = 110
#     qty = 70
#     check_str = "blocked generated SELL chore, symbol_overview_tuple missing for symbol"
#     assert_fail_message = "Could not find any alert containing message to block chores due to no symbol_overview"
#     handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
#                                                                   check_str, assert_fail_message)


@pytest.mark.nightly
def test_plan_limits_with_none_or_o_limit_up_down_px(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore validation behavior when limit up/down prices are missing or zero.

        This test validates that the system properly handles and blocks chores when
        symbol overview configurations have missing (None) or zero limit up/down prices.
        It ensures proper risk management when price limits are undefined.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Modifies symbol overview data:
           - Sets limit_up_px to None
           - Sets limit_dn_px to 0
        3. Attempts to place chores
        4. Verifies proper blocking and alerts
        5. Tests recovery with valid limits

        Key Validations:
        - Confirms chore blocking with missing limits
        - Verifies appropriate alert generation
        - Checks proper handling of None values
        - Validates proper handling of zero values
        - Ensures system recovery with valid limits
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        limit_up_px = None
        limit_dn_px = None
        # removing symbol_overview's limit_up/limit_down px
        stored_symbol_overview_obj_list = executor_http_client.get_all_symbol_overview_client()
        for symbol_overview in stored_symbol_overview_obj_list:
            limit_up_px = symbol_overview.limit_up_px
            symbol_overview.limit_up_px = None
            limit_dn_px = symbol_overview.limit_dn_px
            symbol_overview.limit_dn_px = 0
            # updating symbol_overview
            updated_symbol_overview = executor_http_client.put_symbol_overview_client(symbol_overview)
            assert updated_symbol_overview == symbol_overview, \
                f"Mismatched: expected {symbol_overview}, received: {updated_symbol_overview}"

        # Negative Check
        # placing new non-systematic new_chore
        px = 90
        qty = 95
        check_str = "limit up/down px not available limit-dn px"
        assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)

        updated_symbol_overview_json_list = []
        symbol_overview_list_ = executor_http_client.get_all_symbol_overview_client()
        for symbol_overview_ in symbol_overview_list_:
            symbol_overview_.limit_up_px = limit_up_px
            symbol_overview_.limit_dn_px = limit_dn_px
            updated_symbol_overview = executor_http_client.put_symbol_overview_client(symbol_overview_)
            assert updated_symbol_overview == symbol_overview_, \
                f"Mismatched: expected {symbol_overview_}, received: {updated_symbol_overview}"

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_update_max_open_chores_per_side_updates_consumable_open_chores(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests that updates to max_open_chores_per_side correctly propagate to consumable_open_chores.

        This test validates that changes to the maximum number of open chores per side setting
        properly update the consumable_open_chores value in the plan_brief. It ensures
        chore limits are correctly synchronized across the system.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Tests multiple update scenarios:
           - Sets max_open_chores_per_side to 0
           - Sets max_open_chores_per_side to 10
        3. Verifies planegy brief updates for each change:
           - Checks buy side consumable_open_chores
           - Checks sell side consumable_open_chores
        4. Validates immediate update propagation

        Key Validations:
        - Verifies updates apply to both buy and sell sides
        - Checks immediate reflection of limit changes
        - Validates proper handling of zero values
        - Ensures synchronization between limits and brief
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    # updating max_open_chores_per_side
    for expected_max_open_chores_per_side in [0, 10]:
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)
        plan_limits.max_open_chores_per_side = expected_max_open_chores_per_side
        executor_http_client.put_plan_limits_client(plan_limits)

        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        assert plan_brief.pair_buy_side_bartering_brief.consumable_open_chores == plan_limits.max_open_chores_per_side, \
            (f"Mismatched buy consumable_open_chores: expected {plan_limits.max_open_chores_per_side}, "
             f"found {plan_brief.pair_buy_side_bartering_brief.consumable_open_chores}")
        assert plan_brief.pair_sell_side_bartering_brief.consumable_open_chores == plan_limits.max_open_chores_per_side, \
            (f"Mismatched sell consumable_open_chores: expected {plan_limits.max_open_chores_per_side}, "
             f"found {plan_brief.pair_sell_side_bartering_brief.consumable_open_chores}")


@pytest.mark.nightly
def test_plan_limits_with_0_consumable_open_chores(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                    pair_plan_, expected_plan_limits_,
                                                    expected_plan_status_, symbol_overview_obj_list,
                                                    last_barter_fixture_list, market_depth_basemodel_list,
                                                    buy_chore_, sell_chore_,
                                                    max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement behavior when consumable_open_chores is zero.

        This test validates that the system properly blocks chore placement attempts when
        the consumable_open_chores count reaches zero. It ensures bartering stops appropriately
        when chore limits are exhausted.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Places initial chores until successful
        3. Sets consumable_open_chores to 0
        4. Attempts to place additional chores
        5. Verifies proper blocking and alerts

        Key Validations:
        - Confirms successful chore placement with positive consumable_open_chores
        - Verifies chore blocking when consumable_open_chores is zero
        - Checks appropriate alert generation
        - Validates limit enforcement for both buy and sell sides
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative Check
        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # since only one plan in current test
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_buy_side_bartering_brief.consumable_open_chores = 0
        updated_plan_brief = \
            executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert updated_plan_brief.pair_buy_side_bartering_brief.consumable_open_chores == 0, \
            "Updated plan_brief.pair_buy_side_bartering_brief.consumable_open_chores to 0 using http route call but " \
            f"received unexpected returned value {updated_plan_brief}"

        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = "blocked generated Side.BUY chore, not enough consumable_open_chores"
        assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # since only one plan in current test
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_sell_side_bartering_brief.consumable_open_chores = -1
        updated_plan_brief = \
            executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert updated_plan_brief.pair_sell_side_bartering_brief.consumable_open_chores == -1

        # placing new non-systematic new_chore
        px = 92
        qty = 90
        check_str = "blocked generated Side.SELL chore, not enough consumable_open_chores"
        assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_plan, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _check_max_single_leg_notional_updates_before_placing_chore(
        leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan, executor_http_client,
        residual_wait_sec, chore_symbol, side):

    # Positive check
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    time.sleep(1)
    px = 98
    qty = 90
    inst_type: InstrumentType = get_inst_type(side, activated_plan)
    place_new_chore(chore_symbol, side, px, qty, executor_http_client, inst_type)
    # Internally checks if chore_journal is found with OE_NEW state
    placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                          chore_symbol, executor_http_client)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        time.sleep(residual_wait_sec)  # wait to get open chore residual

    # Negative check
    # updating max_single_leg_notional such that consumable_notional becomes less than next chore notional
    stored_plan_limits = executor_http_client.get_plan_limits_client(activated_plan.id)
    stored_plan_brief = executor_http_client.get_plan_brief_client(activated_plan.id)
    if side == Side.BUY:
        current_consumable_notional = stored_plan_brief.pair_buy_side_bartering_brief.consumable_notional
    else:
        current_consumable_notional = stored_plan_brief.pair_sell_side_bartering_brief.consumable_notional
    non_chore_placable_consumable_notional = 17000
    # since when max_single_leg_notional is updated, updated delta is what is added to consumable_notional
    # delta = stored_max_single_leg_notional - updated_max_single_leg_notional
    # updated_max_single_leg_notional = stored_max_single_leg_notional - delta
    # so this delta will become -ive and when will be added to current consumable notional will make it to 17000
    updated_max_single_leg_notional = (stored_plan_limits.max_single_leg_notional -
                                       (current_consumable_notional - non_chore_placable_consumable_notional))
    updated_plan_limits = executor_http_client.patch_plan_limits_client(
        {"_id": activated_plan.id, "max_single_leg_notional": updated_max_single_leg_notional})
    assert updated_plan_limits.max_single_leg_notional == updated_max_single_leg_notional, \
        (f"Mismatch max_single_leg_notional: expected {updated_max_single_leg_notional} "
         f"found {updated_plan_limits.max_single_leg_notional}")

    updated_plan_brief = executor_http_client.get_plan_brief_client(activated_plan.id)
    if side == Side.BUY:
        assert updated_plan_brief.pair_buy_side_bartering_brief.consumable_notional == non_chore_placable_consumable_notional, \
            (f"Mismatched updated buy consumable_notional: expected {non_chore_placable_consumable_notional}, "
             f"updated {updated_plan_brief.pair_buy_side_bartering_brief.consumable_notional}")
    else:
        assert updated_plan_brief.pair_sell_side_bartering_brief.consumable_notional == non_chore_placable_consumable_notional, \
            (f"Mismatched updated buy consumable_notional: expected {non_chore_placable_consumable_notional}, "
             f"updated {updated_plan_brief.pair_sell_side_bartering_brief.consumable_notional}")

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    # placing new non-systematic new_chore
    check_str = f"blocked generated Side.{side.value} chore, breaches available consumable notional"
    assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
    handle_place_chore_and_check_str_in_alert_for_executor_limits(chore_symbol, side, px, qty,
                                                                  check_str, assert_fail_msg,
                                                                  activated_plan, executor_http_client,
                                                                  last_chore_id=placed_chore_journal.chore.chore_id)

    # reverting back max_single_leg_notional by updating it back to last value that will make consumable notional
    # worthy to place chore - this checks if max_single_leg_notional is exhausted and we increase it then
    # all chores gets placed till it is again exhausted
    updated_plan_limits = executor_http_client.patch_plan_limits_client(
        {"_id": activated_plan.id, "max_single_leg_notional": stored_plan_limits.max_single_leg_notional})
    assert updated_plan_limits.max_single_leg_notional == stored_plan_limits.max_single_leg_notional, \
        (f"Mismatch max_single_leg_notional: expected {stored_plan_limits.max_single_leg_notional} "
         f"found {updated_plan_limits.max_single_leg_notional}")

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    time.sleep(1)
    inst_type: InstrumentType = get_inst_type(side, activated_plan)
    place_new_chore(chore_symbol, side, px, qty, executor_http_client, inst_type)
    # Internally checks if chore_journal is found with OE_NEW state
    placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                          chore_symbol, executor_http_client,
                                                                          last_chore_id=placed_chore_journal.chore.chore_id)


def _check_max_open_single_leg_notional_updates_before_placing_chore(
        leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan, executor_http_client,
        residual_wait_sec, chore_symbol, side):

    # Positive check
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    time.sleep(1)
    px = 98
    qty = 90
    inst_type: InstrumentType = get_inst_type(side, activated_plan)
    place_new_chore(chore_symbol, side, px, qty, executor_http_client, inst_type)
    # Internally checks if chore_journal is found with OE_NEW state
    placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                          chore_symbol, executor_http_client)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        time.sleep(residual_wait_sec)  # wait to get open chore residual

    # Negative check
    # updating max_single_leg_notional such that consumable_notional becomes less than next chore notional
    stored_plan_limits = executor_http_client.get_plan_limits_client(activated_plan.id)
    stored_plan_brief = executor_http_client.get_plan_brief_client(activated_plan.id)
    if side == Side.BUY:
        current_consumable_open_notional = stored_plan_brief.pair_buy_side_bartering_brief.consumable_open_notional
    else:
        current_consumable_open_notional = stored_plan_brief.pair_sell_side_bartering_brief.consumable_open_notional
    non_chore_placable_consumable_open_notional = 17000
    # since when max_open_single_leg_notional is updated, updated delta is what is added to consumable_open_notional
    # delta = stored_max_open_single_leg_notional - updated_max_open_single_leg_notional
    # updated_max_open_single_leg_notional = stored_max_open_single_leg_notional - delta
    # so this delta will become -ive and when will be added to current consumable_open_notional will make it to 17000
    updated_max_open_single_leg_notional = (stored_plan_limits.max_open_single_leg_notional -
                                            (current_consumable_open_notional - non_chore_placable_consumable_open_notional))
    updated_plan_limits = executor_http_client.patch_plan_limits_client(
        {"_id": activated_plan.id, "max_open_single_leg_notional": updated_max_open_single_leg_notional})
    assert updated_plan_limits.max_open_single_leg_notional == updated_max_open_single_leg_notional, \
        (f"Mismatch max_open_single_leg_notional: expected {updated_max_open_single_leg_notional} "
         f"found {updated_plan_limits.max_open_single_leg_notional}")

    updated_plan_brief = executor_http_client.get_plan_brief_client(activated_plan.id)
    if side == Side.BUY:
        assert updated_plan_brief.pair_buy_side_bartering_brief.consumable_open_notional == updated_max_open_single_leg_notional, \
            (f"Mismatched updated buy consumable_open_notional: expected {updated_max_open_single_leg_notional}, "
             f"updated {updated_plan_brief.pair_buy_side_bartering_brief.consumable_open_notional}")
    else:
        assert updated_plan_brief.pair_sell_side_bartering_brief.consumable_open_notional == updated_max_open_single_leg_notional, \
            (f"Mismatched updated sell consumable_open_notional: expected {updated_max_open_single_leg_notional}, "
             f"updated {updated_plan_brief.pair_sell_side_bartering_brief.consumable_open_notional}")

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    # placing new non-systematic new_chore
    check_str = (f"blocked chore with symbol_side_key: %%symbol-side={chore_symbol}-{side.value}%%, "
                 f"breaches available consumable open notional")
    assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
    handle_place_chore_and_check_str_in_alert_for_executor_limits(chore_symbol, side, px, qty,
                                                                  check_str, assert_fail_msg,
                                                                  activated_plan, executor_http_client,
                                                                  last_chore_id=placed_chore_journal.chore.chore_id)

    # reverting back max_single_leg_notional by updating it back to last value that will make consumable notional
    # worthy to place chore - this checks if max_single_leg_notional is exhausted and we increase it then
    # all chores gets placed till it is again exhausted
    updated_plan_limits = executor_http_client.patch_plan_limits_client(
        {"_id": activated_plan.id, "max_open_single_leg_notional": stored_plan_limits.max_open_single_leg_notional})
    assert updated_plan_limits.max_open_single_leg_notional == stored_plan_limits.max_open_single_leg_notional, \
        (f"Mismatch max_open_single_leg_notional: expected {stored_plan_limits.max_open_single_leg_notional} "
         f"found {updated_plan_limits.max_open_single_leg_notional}")

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    time.sleep(1)
    inst_type: InstrumentType = get_inst_type(side, activated_plan)
    place_new_chore(chore_symbol, side, px, qty, executor_http_client, inst_type)
    # Internally checks if chore_journal is found with OE_NEW state
    placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                          chore_symbol, executor_http_client,
                                                                          last_chore_id=placed_chore_journal.chore.chore_id)


@pytest.mark.nightly
def test_max_single_leg_notional_updates_pre_buy_chore_placing(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore validation when max_single_leg_notional is updated before buy chore placement.

        This test validates that changes to max_single_leg_notional properly affect the ability
        to place buy chores. It ensures that notional limits are correctly enforced after
        updates and that consumable notional is accurately recalculated.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Updates max_single_leg_notional:
           - Sets initial value allowing chore placement
           - Updates to restrictive value blocking chores
           - Restores original value
        3. Tests chore placement at each stage:
           - Places chores before limit change
           - Attempts chores after restrictive change
           - Verifies chores after limit restoration
        4. Validates consumable notional updates
        5. Verifies proper alerts and blocking

        Key Validations:
        - Confirms proper notional limit tracking
        - Verifies chore blocking at restricted limits
        - Checks consumable notional recalculation
        - Validates alert message generation
        - Ensures proper limit restoration handling
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    leg1_symbol, leg2_symbol, activated_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_plan.id)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 30
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        _check_max_single_leg_notional_updates_before_placing_chore(
            leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan, executor_http_client,
            residual_wait_sec, leg1_symbol, Side.BUY)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_max_single_leg_notional_updates_pre_sell_chore_placing(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore validation when max_single_leg_notional is updated before sell chore placement.

        This test validates that changes to max_single_leg_notional properly affect the ability
        to place sell chores. It ensures that notional limits are correctly enforced after
        updates and that consumable notional is accurately recalculated.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Updates max_single_leg_notional:
           - Sets initial value allowing chore placement
           - Updates to restrictive value blocking chores
           - Restores original value
        3. Tests chore placement at each stage:
           - Places chores before limit change
           - Attempts chores after restrictive change
           - Verifies chores after limit restoration
        4. Validates consumable notional updates
        5. Verifies proper alerts and blocking

        Key Validations:
        - Confirms proper notional limit tracking
        - Verifies chore blocking at restricted limits
        - Checks consumable notional recalculation
        - Validates alert message generation
        - Ensures proper limit restoration handling
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    leg1_symbol, leg2_symbol, activated_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 leg1_side=Side.SELL, leg2_side=Side.BUY))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_plan.id)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 30
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        _check_max_single_leg_notional_updates_before_placing_chore(
            leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan, executor_http_client,
            residual_wait_sec, leg1_symbol, Side.SELL)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_with_high_consumable_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                    pair_plan_, expected_plan_limits_,
                                                    expected_plan_status_, symbol_overview_obj_list,
                                                    last_barter_fixture_list, market_depth_basemodel_list,
                                                    buy_chore_, sell_chore_,
                                                    max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore blocking when consumable notional limits are exceeded.

        This test validates that chores are properly blocked when they would exceed
        the available consumable notional limits.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Places initial successful chore
        3. Modifies planegy brief:
           - Sets buy side consumable notional to 17000
           - Sets sell side consumable notional to 16500
        4. Attempts to place chores exceeding limits:
           - Buy chore with notional > 17000
           - Sell chore with notional > 16500
        5. Verifies proper blocking and alerts

        Key Validations:
        - Confirms successful chore placement within limits
        - Verifies chore blocking when limits exceeded
        - Checks appropriate alert generation
        - Validates consumable notional calculations
        - Ensures proper limit enforcement for both sides
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, activated_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 30
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, activated_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activated_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(activated_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        # Negative check
        # updating plan_brief to make limits less than next chores
        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # Only one plan_brief must exist for each executor
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_buy_side_bartering_brief.consumable_notional = 17000
        plan_brief.pair_sell_side_bartering_brief.consumable_notional = 16500
        updated_plan_brief = \
            executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert updated_plan_brief == plan_brief, (f"Mismatched PlanBrief: Expected {plan_brief}, "
                                                    f"updated: {updated_plan_brief}")

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activated_plan.cpp_port)
        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = "blocked generated Side.BUY chore, breaches available consumable notional"
        assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      activated_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        # placing new non-systematic new_chore
        px = 96
        qty = 90
        check_str = "blocked generated Side.SELL chore, breaches available consumable notional"
        assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      activated_plan, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_updating_max_concentration_updates_consumable_concentration(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests updates to maximum concentration limits and their effect on consumable concentration.

        This test validates that changes to maximum concentration limits properly update
        the consumable concentration values.

        Test Flow:
        1. Sets up initial concentration limits
        2. Tests various concentration updates:
           - Tests zero concentration
           - Tests positive concentration values
        3. Verifies consumable updates
        4. Tests chore placement under limits
        5. Validates limit enforcement

        Key Validations:
        - Confirms proper concentration limit updates
        - Verifies consumable concentration calculations
        - Checks position limit enforcement
        - Validates limit update propagation
        - Ensures proper risk control updates
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)

        # Note: security_float value is kept based on barter_ready_records.csv value - please change
        # here also if changed in file
        security_float = 1000000
        expected_consumable_concentration = int(plan_limits.max_concentration * (security_float/100))
        assert plan_brief.pair_buy_side_bartering_brief.consumable_concentration == expected_consumable_concentration, \
            (f"Mismatched consumable_concentration, expected {expected_consumable_concentration}, "
             f"updating {plan_brief.pair_buy_side_bartering_brief.consumable_concentration}")
        assert plan_brief.pair_sell_side_bartering_brief.consumable_concentration == expected_consumable_concentration, \
            (f"Mismatched consumable_concentration, expected {expected_consumable_concentration}, "
             f"updating {plan_brief.pair_sell_side_bartering_brief.consumable_concentration}")

        last_max_concentration = plan_limits.max_concentration
        plan_limits.max_concentration = 0
        updated_plan_limits = executor_http_client.put_plan_limits_client(plan_limits)
        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        assert plan_brief.pair_buy_side_bartering_brief.consumable_concentration == updated_plan_limits.max_concentration, \
            (f"Mismatched consumable_concentration, expected {updated_plan_limits.max_concentration}, "
             f"updating {plan_brief.pair_buy_side_bartering_brief.consumable_concentration}")
        assert plan_brief.pair_sell_side_bartering_brief.consumable_concentration == updated_plan_limits.max_concentration, \
            (f"Mismatched consumable_concentration, expected {updated_plan_limits.max_concentration}, "
             f"updating {plan_brief.pair_sell_side_bartering_brief.consumable_concentration}")

        _place_chore_n_check_consumable_concentration_is_0(buy_symbol, sell_symbol,
                                                           active_pair_plan, executor_http_client)

        plan_limits.max_concentration = last_max_concentration
        executor_http_client.put_plan_limits_client(plan_limits)
        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        assert plan_brief.pair_buy_side_bartering_brief.consumable_concentration == expected_consumable_concentration, \
            (f"Mismatched consumable_concentration, expected {expected_consumable_concentration}, "
             f"updating {plan_brief.pair_buy_side_bartering_brief.consumable_concentration}")
        assert plan_brief.pair_sell_side_bartering_brief.consumable_concentration == expected_consumable_concentration, \
            (f"Mismatched consumable_concentration, expected {expected_consumable_concentration}, "
             f"updating {plan_brief.pair_sell_side_bartering_brief.consumable_concentration}")

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _place_chore_n_check_consumable_concentration_is_0(
        buy_symbol, sell_symbol, active_pair_plan, executor_http_client, placed_chore_journal=None):
    # placing new non-systematic new_chore
    px = 98
    qty = 90
    check_str = "blocked generated BUY chore, unexpected: consumable_concentration found 0!"
    assert_fail_message = "Could not find any alert containing message to block chores due to less " \
                          "consumable concentration"
    last_chore_id = placed_chore_journal.chore.chore_id if placed_chore_journal is not None else None
    handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message,
                                                                  active_pair_plan, executor_http_client,
                                                                  last_chore_id=last_chore_id)
    # placing new non-systematic new_chore
    px = 92
    qty = 90
    check_str = "blocked generated SELL chore, unexpected: consumable_concentration found 0!"
    handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message,
                                                                  active_pair_plan, executor_http_client)

@pytest.mark.nightly
def test_plan_limits_with_less_consumable_concentration(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                         pair_plan_, expected_plan_limits_,
                                                         expected_plan_status_, symbol_overview_obj_list,
                                                         last_barter_fixture_list, market_depth_basemodel_list,
                                                         buy_chore_, sell_chore_,
                                                         max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore blocking when consumable concentration is insufficient.

        This test validates that chores are properly blocked when the available
        consumable concentration is insufficient for the requested chore size.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Places successful chore within limits
        3. Modifies planegy brief:
           - Sets buy side consumable concentration to 10
           - Sets sell side consumable concentration to 10
        4. Attempts chores exceeding concentration limits
        5. Sets concentration to 0 and tests blocking
        6. Verifies alerts and blocking behavior

        Key Validations:
        - Confirms chore blocking with insufficient concentration
        - Verifies blocking with zero concentration
        - Checks alert message generation
        - Validates concentration calculations
        - Tests both buy and sell sides

        Notes:
        - Tests low and zero concentration scenarios
        - Includes proper alert verification
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative Check

        # Checking alert when consumable_concentration < chore_qty
        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # since only one plan in current test
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_buy_side_bartering_brief.consumable_concentration = 10
        plan_brief.pair_sell_side_bartering_brief.consumable_concentration = 10
        updated_plan_brief = executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert (updated_plan_brief.pair_buy_side_bartering_brief.consumable_concentration ==
                plan_brief.pair_buy_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_buy_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_plan_brief.pair_buy_side_bartering_brief.consumable_concentration}"
        assert (updated_plan_brief.pair_sell_side_bartering_brief.consumable_concentration ==
                plan_brief.pair_sell_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_sell_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_plan_brief.pair_sell_side_bartering_brief.consumable_concentration}"

        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = "blocked generated BUY chore, not enough consumable_concentration:"
        assert_fail_message = "Could not find any alert containing message to block chores due to less " \
                              "consumable concentration"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        # placing new non-systematic new_chore
        px = 92
        qty = 90
        check_str = "blocked generated SELL chore, not enough consumable_concentration:"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # Checking alert when consumable_concentration == 0
        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # since only one plan in current test
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_buy_side_bartering_brief.consumable_concentration = 0
        plan_brief.pair_sell_side_bartering_brief.consumable_concentration = 0
        updated_plan_brief = executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert (updated_plan_brief.pair_buy_side_bartering_brief.consumable_concentration ==
                plan_brief.pair_buy_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_buy_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_plan_brief.pair_buy_side_bartering_brief.consumable_concentration}"
        assert (updated_plan_brief.pair_sell_side_bartering_brief.consumable_concentration ==
                plan_brief.pair_sell_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_sell_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_plan_brief.pair_sell_side_bartering_brief.consumable_concentration}"

        _place_chore_n_check_consumable_concentration_is_0(
            buy_symbol, sell_symbol, active_pair_plan, executor_http_client, placed_chore_journal)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_with_symbol_overview_limit_dn_up_px(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                          pair_plan_, expected_plan_limits_,
                                                          expected_plan_status_, symbol_overview_obj_list,
                                                          last_barter_fixture_list, market_depth_basemodel_list,
                                                          buy_chore_, sell_chore_,
                                                          max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore validation against symbol overview limit up/down prices.

        This test verifies that chores are properly validated against the limit up and limit down
        prices defined in the symbol overview. It ensures chores outside these price bounds
        are blocked appropriately.

        Test Flow:
        1. Sets up bartering pair with limit up/down prices
        2. Attempts chores at various price levels:
           - Above limit up price
           - Below limit down price
           - Within valid price range
        3. Verifies proper blocking and alerts
        4. Validates successful chores within limits

        Key Validations:
        - Confirms chore blocking above limit up price
        - Verifies chore blocking below limit down price
        - Checks appropriate alert generation
        - Validates successful placement within limits
        - Ensures proper price bound enforcement
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_chore
        px = 160
        qty = 90
        check_str = "blocked generated BUY chore, px expected lower than limit-up px"
        assert_fail_message = "Could not find any alert containing message to block chores due to chore_px higher " \
                              "than symbol_overview's limit_up_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)

        # placing new non-systematic new_chore
        px = 40
        qty = 90
        check_str = "blocked generated SELL chore, px expected higher than limit-dn px"
        assert_fail_message = "Could not find any alert containing message to block chores due to chore_px higher " \
                              "than symbol_overview's limit_up_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_with_negative_consumable_participation_qty(static_data_, clean_and_set_limits,
                                                                 leg1_leg2_symbol_list, pair_plan_,
                                                                 expected_plan_limits_,
                                                                 expected_plan_status_, symbol_overview_obj_list,
                                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                                 buy_chore_, sell_chore_,
                                                                 max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore handling when consumable participation quantity becomes negative.

        This test validates system behavior when the consumable participation quantity
        drops below zero due to market activity. It ensures proper chore blocking and
        alert generation in such scenarios.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Creates scenario with negative consumable participation:
           - Modifies last barter quantity to force negative value
        3. Attempts chore placement
        4. Verifies proper blocking and alerts
        5. Validates system recovery

        Key Validations:
        - Confirms chore blocking with negative participation qty
        - Verifies appropriate alert generation
        - Checks correct calculation of participation values
        - Validates proper handling of market volume updates
        - Ensures system maintains stability
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    activate_pair_plan, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, keep_default_hedge_ratio=True))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activate_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, activate_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, activate_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        px = 98
        qty = 90
        # positive test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activate_pair_plan.cpp_port)

        # placing new non-systematic new_chore
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

        placed_new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                                  executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        # Negative Check
        # executor_http_client.delete_all_last_barter_client()
        # creating last buy last barter with hardcoded value in participation_period_last_barter_qty_sum which will
        # make consumable_participation_qty < 0
        buy_last_barter = last_barter_fixture_list[0]
        buy_last_barter["market_barter_volume"]["participation_period_last_barter_qty_sum"] = 1000
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activate_pair_plan.cpp_port, create_counts_per_side=1)

        check_str = ("blocked generated chore, not enough consumable_participation_qty available, "
                     "expected higher than chore qty: 90")
        assert_fail_message = "Could not find any alert containing message to block chores due to low " \
                              "consumable_participation_qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_plan,
                                                                      executor_http_client,
                                                                      last_chore_id=
                                                                      placed_new_chore_journal.chore.chore_id)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_with_0_consumable_participation_qty(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                          pair_plan_, expected_plan_limits_,
                                                          expected_plan_status_, symbol_overview_obj_list,
                                                          last_barter_fixture_list, market_depth_basemodel_list,
                                                          buy_chore_, sell_chore_,
                                                          max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore handling when consumable participation quantity is zero.

        This test validates that the system properly blocks chores when the consumable
        participation quantity reaches zero. It ensures proper handling of participation
        limits and market volume constraints.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Creates scenario with zero consumable participation:
           - Removes last barters
           - Sets participation values to zero
        3. Attempts chore placement
        4. Verifies proper blocking and alerts
        5. Tests system recovery with valid participation values

        Key Validations:
        - Confirms chore blocking with zero participation qty
        - Verifies appropriate alert generation
        - Checks participation calculation accuracy
        - Validates system recovery with valid values
        - Ensures proper market volume tracking
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # Creating Plan
    activate_pair_plan, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, keep_default_hedge_ratio=True))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activate_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Negative check
        # removing last_barter for negative check
        executor_http_client.delete_all_last_barter_client()

        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = "Received unusable consumable_participation_qty=0 from get_consumable_participation_qty_http"
        assert_fail_message = "Could not find any alert containing message to block chores due to 0 " \
                              "consumable_participation_qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_plan, executor_http_client)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, activate_pair_plan))

        # Positive Check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activate_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(activate_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_with_positive_low_consumable_participation_qty(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore handling with low but positive consumable participation quantity.

        This test validates system behavior when consumable participation quantity is
        positive but below required chore quantity. It ensures proper chore blocking
        and alert generation in such scenarios.

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Creates scenario with low participation quantity:
           - Sets participation values below chore quantity
        3. Attempts chore placement
        4. Verifies proper blocking and alerts
        5. Tests recovery with sufficient participation qty

        Key Validations:
        - Confirms chore blocking with insufficient participation qty
        - Verifies appropriate alert generation
        - Checks participation calculation accuracy
        - Validates successful chores with sufficient qty
        - Ensures proper volume tracking
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # Creating Plan
    activate_pair_plan, executor_http_client = (
        create_n_activate_plan(buy_symbol, sell_symbol, copy.deepcopy(pair_plan_),
                                copy.deepcopy(expected_plan_limits_),
                                copy.deepcopy(expected_plan_status_), symbol_overview_obj_list,
                                market_depth_basemodel_list, keep_default_hedge_ratio=True))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activate_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, activate_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, activate_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Negative check
        executor_http_client.delete_all_last_barter_client()
        buy_last_barter = last_barter_fixture_list[0]
        buy_last_barter["market_barter_volume"]["participation_period_last_barter_qty_sum"] = 50
        buy_last_barter = LastBarterBaseModel.from_dict(buy_last_barter)
        cpp_create_last_barter_client(activate_pair_plan.cpp_port, buy_last_barter)
        buy_last_barter.market_barter_volume.participation_period_last_barter_qty_sum = 100
        cpp_create_last_barter_client(activate_pair_plan.cpp_port, buy_last_barter)
        sell_last_barter = last_barter_fixture_list[1]
        sell_last_barter = LastBarterBaseModel.from_dict(sell_last_barter)
        cpp_create_last_barter_client(activate_pair_plan.cpp_port, sell_last_barter)
        cpp_create_last_barter_client(activate_pair_plan.cpp_port, sell_last_barter)

        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = ("blocked generated chore, not enough consumable_participation_qty available, "
                     "expected higher than chore qty: 90, found 20")
        assert_fail_message = "Could not find any alert containing message to block chores due to low " \
                              "consumable_participation_qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_plan, executor_http_client)

        # Positive Check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activate_pair_plan.cpp_port)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_done_after_exhausted_buy_consumable_notional(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_chore_limits_, refresh_sec_update_fixture):
    """
        Tests planegy completion handling when buy consumable notional is exhausted.

        This test validates that the planegy properly transitions to a done state
        when the buy side consumable notional is fully exhausted. It ensures proper
        handling of notional limits and planegy state management.

        Test Flow:
        1. Sets up planegy with specific notional limits:
           - Sets max_single_leg_notional to 18000
           - Sets min_chore_notional to 15000
        2. Places chores until notional exhaustion
        3. Verifies planegy state transition
        4. Validates proper alert generation

        Key Validations:
        - Confirms proper notional limit tracking
        - Verifies planegy state transition
        - Checks appropriate alert generation
        - Validates notional calculations
        - Ensures proper limit enforcement
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # setting plan_limits for this test
    expected_plan_limits_.max_single_leg_notional = 18000
    expected_plan_limits_.max_open_single_leg_notional = 18000
    expected_plan_limits_.max_net_filled_notional = 18000
    expected_plan_limits_.min_chore_notional = 15000
    plan_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list, refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_plan_done_after_exhausted_sell_consumable_notional(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_chore_limits_, refresh_sec_update_fixture):
    """
        Tests planegy completion handling when sell consumable notional is exhausted.

        This test validates that the planegy properly transitions to a done state
        when the sell side consumable notional is fully exhausted. It ensures proper
        handling of notional limits and planegy state management.

        Test Flow:
        1. Sets up planegy with specific notional limits:
           - Sets max_single_leg_notional to 18000
           - Sets min_chore_notional to 15000
        2. Places chores until notional exhaustion
        3. Verifies planegy state transition
        4. Validates proper alert generation

        Key Validations:
        - Confirms proper notional limit tracking
        - Verifies planegy state transition
        - Checks appropriate alert generation
        - Validates notional calculations
        - Ensures proper limit enforcement
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # setting plan_limits for this test
    expected_plan_limits_.max_single_leg_notional = 19000
    expected_plan_limits_.max_open_single_leg_notional = 19000
    expected_plan_limits_.max_net_filled_notional = 19000
    expected_plan_limits_.min_chore_notional = 15000
    plan_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list, refresh_sec_update_fixture, Side.SELL,
        leg_1_side=Side.SELL, leg_2_side=Side.BUY)


@pytest.mark.nightly
def test_max_open_single_leg_notional_updates_pre_buy_chore_placing(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests updates to max_open_single_leg_notional before buy chore placement.

        This test validates that changes to the maximum open single leg notional value
        properly affect chore placement capabilities for buy chores and that
        consumable open notional is accurately recalculated

        Test Flow:
        1. Sets up bartering pair with initial configurations
        2. Updates max_open_single_leg_notional values
        3. Attempts buy chore placement under various limit conditions
        4. Verifies proper blocking and alerts when limits are exceeded
        5. Validates system behavior with limit changes

        Key Validations:
        - Confirms proper update of notional limits
        - Verifies chore blocking when limits exceeded
        - Checks appropriate alert generation
        - Validates proper calculation of notional values
        - Ensures limit updates are immediately enforced
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    leg1_symbol, leg2_symbol, activated_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_plan.id)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 30
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        _check_max_open_single_leg_notional_updates_before_placing_chore(
            leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_plan, executor_http_client,
            residual_wait_sec, leg1_symbol, Side.BUY)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_consumable_open_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                               pair_plan_, expected_plan_limits_,
                                               expected_plan_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list,
                                               buy_chore_, sell_chore_,
                                               max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement validation against consumable open notional limits.

        This test validates that chores are properly blocked when they would exceed
        the available consumable open notional limits.

        Test Flow:
        1. Sets up initial notional limits
        2. Places initial successful chore
        3. Modifies planegy brief:
           - Sets buy side consumable open notional to 17000
           - Sets sell side consumable open notional to 16000
        4. Attempts to place chores exceeding limits:
           - Buy chore with notional > 17000
           - Sell chore with notional > 16000
        5. Verifies proper blocking and alerts

        Key Validations:
        - Confirms proper notional limit tracking
        - Verifies chore blocking at limits
        - Checks alert message generation
        - Validates notional calculations
        - Ensures proper limit enforcement
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        # Negative check
        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # since only one plan in current test
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_buy_side_bartering_brief.consumable_open_notional = 17000
        updated_plan_brief = \
            executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert (updated_plan_brief.pair_buy_side_bartering_brief.consumable_open_notional ==
                plan_brief.pair_buy_side_bartering_brief.consumable_open_notional), \
            ("Updated plan_brief.pair_buy_side_bartering_brief.consumable_open_notional to "
             f"{plan_brief.pair_buy_side_bartering_brief.consumable_open_notional} "
             "using http route call but received unexpected returned value {updated_plan_brief}")

        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = (f"blocked chore with symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%, "
                     "breaches available consumable open notional")
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)

        plan_brief_list = executor_http_client.get_all_plan_brief_client()
        # since only one plan in current test
        assert len(plan_brief_list) == 1, "Unexpected length of plan_briefs, expected exactly one plan_brief " \
                                           f"as only one plan exists for this test, received " \
                                           f"{len(plan_brief_list)}, plan_brief_list: {plan_brief_list}"
        plan_brief = plan_brief_list[0]
        plan_brief.pair_sell_side_bartering_brief.consumable_open_notional = 16000
        updated_plan_brief = \
            executor_http_client.put_plan_brief_client(plan_brief.to_dict(exclude_none=True))
        assert (updated_plan_brief.pair_sell_side_bartering_brief.consumable_open_notional ==
                plan_brief.pair_sell_side_bartering_brief.consumable_open_notional), \
            ("Updated plan_brief.pair_sell_side_bartering_brief.consumable_open_notional to "
             f"{plan_brief.pair_sell_side_bartering_brief.consumable_open_notional} "
             "using http route call but received unexpected returned value {updated_plan_brief}")

        # placing new non-systematic new_chore
        px = 92
        qty = 90
        check_str = (f"blocked chore with symbol_side_key: %%symbol-side={sell_symbol}-{Side.SELL.value}%%, "
                     "breaches available consumable open notional")
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_plan_limits_consumable_nett_filled_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                      pair_plan_, expected_plan_limits_,
                                                      expected_plan_status_, symbol_overview_obj_list,
                                                      last_barter_fixture_list, market_depth_basemodel_list,
                                                      buy_chore_, sell_chore_,
                                                      max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests enforcement of consumable net filled notional limits.

        This test validates that chores are properly blocked when they would exceed
        the available consumable net filled notional limits.

        Test Flow:
        1. Sets up initial notional limits and positions
        2. Places initial successful chore
        2. Modified net_filled_notional:
           - Updates max_net_filled_notional
           - Verifies consumable_net_filled_notional is recalculated
        3. Attempts chores with notional > consumable_net_filled_notional
        4. Verifies blocking and alerts
        5. Tests limit recovery scenarios

        Key Validations:
        - Confirms proper net notional tracking
        - Verifies chore blocking at limits
        - Checks appropriate alert generation
        - Validates net position calculations
        - Ensures proper limit recovery handling
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        px = 98
        qty = 90
        buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)

        # Negative check
        plan_limits = executor_http_client.get_plan_limits_client(active_pair_plan.id)
        last_max_net_filled_notional = plan_limits.max_net_filled_notional
        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        last_consumable_nett_filled_notional = plan_brief.consumable_nett_filled_notional
        # making max_nett_filled_notional such it makes consumable_nett_filled_notional 16000 which is less than
        # next chore's notional - will be blocked and raise alert for exhaustion of consumable_nett_filled_notional
        current_net_filled_notional = placed_chore_journal.chore.qty / 2    # since fill_percent in config is 50
        expected_consumable_nett_filled_notional = 1600
        # updated_max_net_filled_notional_delta = updated_max_net_filled_notional - stored_max_net_filled_notional
        # updated_consumable_nett_filled_notional = stored_consumable_nett_filled_notional - updated_max_net_filled_notional_delta
        # which can be written as:
        # updated_consumable_nett_filled_notional = (stored_consumable_nett_filled_notional -
        #                                            updated_max_net_filled_notional + stored_max_net_filled_notional)
        # updated_max_net_filled_notional = (updated_consumable_nett_filled_notional -
        #                                    stored_max_net_filled_notional + updated_max_net_filled_notional)
        plan_limits.max_net_filled_notional = (expected_consumable_nett_filled_notional -
                                                plan_brief.consumable_nett_filled_notional +
                                                plan_limits.max_net_filled_notional)
        updated_plan_limits = executor_http_client.put_plan_limits_client(plan_limits)
        assert updated_plan_limits.max_net_filled_notional == plan_limits.max_net_filled_notional, \
            (f"Mismatched max_net_filled_notional, Expected {plan_limits.max_net_filled_notional}, "
             f"updated {updated_plan_limits.max_net_filled_notional}")

        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        assert (plan_brief.consumable_nett_filled_notional == expected_consumable_nett_filled_notional), \
            (f"Mismatched consumable_nett_filled_notional, Expected {expected_consumable_nett_filled_notional}, "
             f"updated {plan_brief.consumable_nett_filled_notional}")

        # placing new non-systematic new_chore
        px = 98
        qty = 90
        check_str = "blocked Side.BUY generated chore, not enough consumable_nett_filled_notional available"
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)

        # placing new non-systematic new_chore
        px = 96
        qty = 90
        check_str = "blocked Side.SELL generated chore, not enough consumable_nett_filled_notional available"
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_plan, executor_http_client)

        # updating max_net_filled_notional back to what it was before update
        plan_limits.max_net_filled_notional = last_max_net_filled_notional
        updated_plan_limits = executor_http_client.put_plan_limits_client(plan_limits)
        assert updated_plan_limits.max_net_filled_notional == plan_limits.max_net_filled_notional, \
            (f"Mismatched max_net_filled_notional, Expected {plan_limits.max_net_filled_notional}, "
             f"updated {updated_plan_limits.max_net_filled_notional}")

        plan_brief = executor_http_client.get_plan_brief_client(active_pair_plan.id)
        assert (plan_brief.consumable_nett_filled_notional == last_consumable_nett_filled_notional), \
            (f"Mismatched consumable_nett_filled_notional, Expected {last_consumable_nett_filled_notional}, "
             f"updated {plan_brief.consumable_nett_filled_notional}")

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        px = 98
        qty = 90
        buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client,
                                                                              last_chore_id=placed_chore_journal.chore.chore_id)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def handle_place_both_side_chores_for_contact_limits_test(buy_symbol: str, sell_symbol: str,
                                                            pair_plan_,
                                                            expected_plan_limits_, expected_plan_status_,
                                                            symbol_overview_obj_list,
                                                            last_barter_fixture_list, market_depth_basemodel_list,
                                                            refresh_sec,
                                                            expect_no_chore=False):
    # making conditions suitable for this test
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 1000
    residual_wait_sec = 4 * refresh_sec

    created_pair_plan, executor_http_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_plan_status_))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, created_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, created_pair_plan)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        total_chore_count_for_each_side = 1
    else:
        total_chore_count_for_each_side = 2

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.barter_simulator_reload_config_query_client()

        # Placing buy chores
        last_buy_chore_id = None
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
            px = 98
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

            new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                               buy_symbol, executor_http_client,
                                                                               expect_no_chore=expect_no_chore,
                                                                               last_chore_id=last_buy_chore_id)
            last_buy_chore_id = new_chore_journal.chore.chore_id

        # Placing sell chores
        last_sell_chore_id = None
        if executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            for loop_count in range(total_chore_count_for_each_side):
                run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
                px = 92
                qty = 90
                place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

                new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                   sell_symbol, executor_http_client,
                                                                                   expect_no_chore=expect_no_chore,
                                                                                   last_chore_id=last_sell_chore_id)
                last_sell_chore_id = new_chore_journal.chore.chore_id

        return executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def handle_place_single_side_chores_for_contact_limits_test(leg_1_symbol: str, leg_2_symbol: str,
                                                              pair_plan_,
                                                              expected_plan_limits_, expected_plan_status_,
                                                              symbol_overview_obj_list,
                                                              last_barter_fixture_list, market_depth_basemodel_list,
                                                              refresh_sec, chore_side: Side,
                                                              leg1_side=Side.BUY, leg2_side=Side.SELL):
    # making conditions suitable for this test
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 1000
    residual_wait_sec = 4 * refresh_sec

    created_pair_plan, executor_http_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_plan_status_))
    if created_pair_plan.pair_plan_params.plan_leg1.side == Side.BUY:
        buy_symbol = leg_1_symbol
        sell_symbol = leg_2_symbol
    else:
        buy_symbol = leg_2_symbol
        sell_symbol = leg_1_symbol

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, created_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, created_pair_plan)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        total_chore_count_for_each_side = 1
    else:
        total_chore_count_for_each_side = 2

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 0
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.barter_simulator_reload_config_query_client()

        # Placing buy chores
        if chore_side == Side.BUY:
            last_chore_id = None
            for loop_count in range(total_chore_count_for_each_side):
                run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
                px = 98
                qty = 90
                place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)

                new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                   buy_symbol, executor_http_client,
                                                                                   last_chore_id=last_chore_id)
                last_chore_id = new_chore_journal.chore.chore_id

                # Checking if fills found
                time.sleep(10)
                get_latest_fill_journal_from_chore_id(last_chore_id, executor_http_client)

        else:
            # Placing sell chores
            last_chore_id = None
            for loop_count in range(total_chore_count_for_each_side):
                run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
                px = 96
                qty = 90
                place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)

                new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                   sell_symbol, executor_http_client,
                                                                                   last_chore_id=last_chore_id)
                last_chore_id = new_chore_journal.chore.chore_id
                time.sleep(10)
                get_latest_fill_journal_from_chore_id(last_chore_id, executor_http_client)

        if chore_side == Side.BUY:
            return executor_http_client, buy_symbol, sell_symbol, last_chore_id
        else:
            return executor_http_client, buy_symbol, sell_symbol, last_chore_id

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _plan_pause_on_chore_fulfill_post_dod(buy_symbol, sell_symbol, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec, pause_fulfill_post_chore_dod):

    # making conditions suitable for this test
    residual_wait_sec = refresh_sec * 4
    active_pair_plan, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
            config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1  # all chores - unsol_cxl
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

        symbol = buy_symbol
        print(f"Checking symbol: {symbol}")
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        time.sleep(2)  # delay for chore to get placed

        ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol,
                                                                           executor_http_client)
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_UNSOL_CXL,
                                                       symbol, executor_http_client)

        executor_http_client.barter_simulator_process_fill_query_client(
            ack_chore_journal.chore.chore_id, ack_chore_journal.chore.px,
            ack_chore_journal.chore.qty, ack_chore_journal.chore.side,
            ack_chore_journal.chore.security.sec_id, ack_chore_journal.chore.underlying_account)
        latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                    executor_http_client)

        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, executor_http_client)
        if not pause_fulfill_post_chore_dod:
            assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, "ChoreStatus mismatched: expected status " \
                                                                             f"ChoreStatusType.OE_FILLED received " \
                                                                             f"{chore_snapshot.chore_status}"
            assert chore_snapshot.filled_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatch chore_snapshot.filled_qty, expected {chore_snapshot.chore_brief.qty}, "
                 f"received {chore_snapshot.filled_qty}")
            assert chore_snapshot.cxled_qty == 0, \
                f"Mismatch chore_snapshot.cxled_qty: expected 0, received {chore_snapshot.cxled_qty}"
        else:
            assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, "ChoreStatus mismatched: expected status " \
                                                                          f"ChoreStatusType.OE_DOD received " \
                                                                          f"{chore_snapshot.chore_status}"
            assert chore_snapshot.filled_qty == 0, f"Mismatch chore_snapshot.filled_qty, expected 0, " \
                                                   f"received {chore_snapshot.filled_qty}"
            assert chore_snapshot.cxled_qty == chore_snapshot.chore_brief.qty, \
                f"Mismatch chore_snapshot.cxled_qty: expected {chore_snapshot.chore_brief.qty}, received " \
                f"{chore_snapshot.cxled_qty}"
        return active_pair_plan, executor_http_client
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_no_plan_pause_on_chore_fulfill_post_dod_if_config_is_false(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests planegy behavior for DOD chore fulfillment with pause disabled.

        This test validates that planegies continue normal operation when chores are
        fulfilled after being marked DOD with the pause configuration disabled.

        Test Flow:
        1. Configures system settings:
           - Sets pause_fulfill_post_chore_dod to false
        2. Creates test conditions:
           - Places chores that become DOD
           - Processes fills for DOD chores
        3. Verifies planegy continues operation
        4. Validates chore processing
        5. Checks system state

        Key Validations:
        - Confirms planegy remains active after DOD fills
        - Verifies proper chore status transitions
        - Checks fill processing behavior
        - Validates configuration handling
        - Ensures system stability
    """

    # Keeping pause_fulfill_post_chore_dod config in executor
    # configs False - fulfill after dod must not trigger plan pause
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["pause_fulfill_post_chore_dod"] = False
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))
    try:
        buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]
        created_pair_plan, executor_http_client = (
            _plan_pause_on_chore_fulfill_post_dod(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                                   expected_plan_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   refresh_sec_update_fixture,
                                                   pause_fulfill_post_chore_dod=False))

        # check plan must not get paused
        pair_plan_obj = email_book_service_native_web_client.get_pair_plan_client(created_pair_plan.id)
        assert pair_plan_obj.plan_state != PlanState.PlanState_PAUSED, \
            "Plan must not be PAUSED since 'pause_fulfill_post_chore_dod' is set False but found PAUSED"

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


@pytest.mark.nightly
def test_plan_pause_on_chore_fulfill_post_dod_if_config_is_true(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests planegy pause behavior for DOD chore fulfillment with pause enabled.

        This test validates that planegies properly pause when chores are fulfilled after
        being marked DOD with the pause configuration enabled.

        Test Flow:
        1. Configures system settings:
           - Sets pause_fulfill_post_chore_dod to true
        2. Creates test conditions:
           - Places chores that become DOD
           - Processes fills for DOD chores
        3. Verifies planegy pauses
        4. Validates system state
        5. Checks alert generation

        Key Validations:
        - Confirms planegy pauses after DOD fills
        - Verifies proper chore status transitions
        - Checks appropriate alert generation
        - Validates configuration handling
        - Ensures proper risk management
    """
    # Keeping pause_fulfill_post_chore_dod config in executor configs True - fulfill after dod must trigger plan pause
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["pause_fulfill_post_chore_dod"] = True
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))
    try:
        buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]
        created_pair_plan, executor_http_client = (
            _plan_pause_on_chore_fulfill_post_dod(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                                   expected_plan_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   refresh_sec_update_fixture,
                                                   pause_fulfill_post_chore_dod=True))
        # check plan must not get paused
        pair_plan_obj = email_book_service_native_web_client.get_pair_plan_client(created_pair_plan.id)
        assert pair_plan_obj.plan_state == PlanState.PlanState_PAUSED, \
            ("Plan must get PAUSED since 'pause_fulfill_post_chore_dod' is set True but not found PAUSED, "
             f"found state: {pair_plan_obj.plan_state}")

        check_str = "Unexpected: Received fill that makes chore_snapshot OE_FILLED which is already of state OE_DOD"
        assert_fail_message = f"Can't find any alert with string '{check_str}'"

        time.sleep(5)
        check_alert_str_in_plan_alerts_n_contact_alerts(created_pair_plan.id, check_str, assert_fail_message)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


# contact limits
@pytest.mark.nightly
def test_max_open_baskets(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                          expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                          last_barter_fixture_list, market_depth_basemodel_list,
                          buy_chore_, sell_chore_,
                          max_loop_count_per_side, expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests enforcement of maximum open basket limits across planegies.

        This test validates that the system enforces the maximum number of open chore
        baskets (max_open_baskets = 7) across all planegies, properly triggering
        system-wide pause when exceeded.

        Test Flow:
        1. Sets max_open_baskets to 7
        2. Creates and activates multiple planegies:
           - Creates 8 planegies if single chore per plan
           - Creates 2 planegies if multiple chores allowed
        3. Places chores until limit breach
        4. Attempts additional chore placement
        5. Verifies system-wide pause

        Key Validations:
        - Confirms accurate basket counting
        - Verifies proper system pause at limit
        - Checks alert generation
        - Validates contact status updates
        - Tests chore blocking post-pause
    """
    # > INFO:
    # Test sets max_open_baskets = 7,
    # - if multi open chores are allowed:
    # first triggers 2 street_books and places 2 chores each side from each executor,
    # these 8 chores must pass for positive check and 8th chore must breach max_open_baskets limits
    # and must trigger all-plan pause, then one more BUY chore is placed in
    # any one executor, so it must not be placed since plans are paused + alert must be created in contact_alerts
    # - if multi open chores are not allowed:
    # first triggers 8 street_books and places 1 chore BUY side from each executor,
    # these 8 chores must pass for positive check and 8th chore must breach max_open_baskets limits
    # and must trigger all-plan pause, then one more plan is created and BUY chore is placed,
    # so it must not be placed since plans are paused + alert must be created in contact_alerts

    # Updating contact limits
    expected_contact_limits_.max_open_baskets = 7
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:8]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

    # starting plans one by one
    pair_plan_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)

    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_chores_for_contact_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture, False)
                   for idx, buy_sell_symbol in enumerate(sliced_buy_sell_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id))

    # checking contact_status open_chores
    contact_status = email_book_service_native_web_client.get_contact_status_client(1)
    assert contact_status.open_chores == 8, \
        f"Mismatched contact_status.open_chores, expected: 8, received: {contact_status.open_chores=}"

    # Till this point since max_open_buckets limits must have breached and any new chore must not be placed,
    # checking that now...

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    created_pair_plan = create_plan(buy_symbol, sell_symbol, pair_plan_)
    handle_place_both_side_chores_for_contact_limits_test(
        buy_symbol, sell_symbol, created_pair_plan, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, expect_no_chore=True)

    # checking contact_status open_chores
    contact_status = email_book_service_native_web_client.get_contact_status_client(1)
    assert contact_status.open_chores == 8, \
        f"Mismatched contact_status.open_chores, expected: 8, received: {contact_status.open_chores=}"

    time.sleep(5)
    # checking if all plan pause warning is in last started plan
    check_str = "Putting Activated Plan to PAUSE, found contact_limits breached already"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    check_alert_str_in_plan_alerts_n_contact_alerts(created_pair_plan.id, check_str, assert_fail_message)

    # Checking alert in contact_alert
    check_str = "max_open_baskets breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    check_alert_str_in_contact_alert(check_str, assert_fail_message)

    # Checking all plan pause
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
            f"Unexpected, plan_state must be paused, received {pair_plan.plan_state}, pair_plan: {pair_plan}"


@pytest.mark.nightly
def test_max_open_notional_per_side_for_buy(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                                            expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                                            last_barter_fixture_list, market_depth_basemodel_list,
                                            buy_chore_, sell_chore_,
                                            max_loop_count_per_side, expected_contact_limits_,
                                            refresh_sec_update_fixture):
    """
        Tests enforcement of maximum open notional limits for buy chores.

        This test validates that the system enforces the maximum open notional limit
        (70,500) for buy chores across all planegies and triggers system-wide pause
        when exceeded.

        Test Flow:
        1. Sets max_open_notional_per_side to 70,500
        2. Creates multiple planegies:
           - 2 planegies if multiple chores allowed
           - 4 planegies if single chore per planegy
        3. Places buy chores until limit breach
        4. Verifies system-wide pause
        5. Validates alerts and blocking

        Key Validations:
        - Confirms notional limit tracking
        - Verifies system pause at limit
        - Checks alert generation
        - Validates buy-side notional calculations
        - Tests cross-planegy aggregation
    """
    # INFO:
    # Test sets max_open_notional_per_side = 70_500,

    # - if multi open chores are allowed:
    # triggers 2 street_books and places 2 chores BUY side from each executor
    # - if multi open chores are not allowed:
    # creates 4 plans and places each Buy Chore from each executor

    # these 4 must pass for positive check and fourth chore must breach limit and as a result
    # all-plan pause also should get triggered + alert must be created in contact_alerts

    # Updating contact limits
    expected_contact_limits_.max_open_notional_per_side = 70_500
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:4]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

    # starting plans one by one
    pair_plan_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)
    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_single_side_chores_for_contact_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture, Side.BUY,
                                   leg1_side=Side.BUY, leg2_side=Side.SELL)
                   for idx, buy_sell_symbol in enumerate(sliced_buy_sell_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, sell_symbol, last_buy_chore_id = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, buy_symbol, sell_symbol, last_buy_chore_id))

    # Checking alert in contact_alert
    check_str = "max_open_notional_per_side breached for BUY side"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_contact_alert(check_str, assert_fail_message)

    # Checking all plan pause
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
            (f"Unexpected, plan_state must be paused, received {pair_plan.plan_state}, "
             f"pair_plan: {pair_plan}")


@pytest.mark.nightly
def test_max_open_notional_per_side_for_sell(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                                             expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                                             last_barter_fixture_list, market_depth_basemodel_list,
                                             buy_chore_, sell_chore_,
                                             max_loop_count_per_side, expected_contact_limits_,
                                             refresh_sec_update_fixture):
    """
            Tests enforcement of maximum open notional limits for sell chores.

            This test validates that the system enforces the maximum open notional limit
            (69,000) for sell chores across all planegies and triggers system-wide pause
            when exceeded.

            Test Flow:
            1. Sets max_open_notional_per_side to 69,000
            2. Creates multiple planegies:
               - 2 planegies if multiple chores allowed
               - 4 planegies if single chore per planegy
            3. Places sell chores until limit breach
            4. Verifies system-wide pause
            5. Validates alerts and blocking

            Key Validations:
            - Confirms notional limit tracking
            - Verifies system pause at limit
            - Checks alert generation
            - Validates sell-side notional calculations
            - Tests cross-planegy aggregation
        """
    # INFO:
    # Test sets max_open_notional_per_side = 69_000,

    # - if multi open chores are allowed:
    # triggers 2 street_books and places 2 chores SELL side from each executor
    # - if multi open chores are not allowed:
    # creates 4 plans and places each SELL Chore from each executor

    # these 4 must pass for positive check and fourth chore must breach limit and as a result
    # all-plan pause also should get triggered + alert must be created in contact_alerts

    # Updating contact limits
    expected_contact_limits_.max_open_notional_per_side = 69_000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:4]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

    # starting plans one by one
    pair_plan_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)

    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_place_single_side_chores_for_contact_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture, Side.SELL,
                                   leg1_side=Side.SELL, leg2_side=Side.BUY)
                   for idx, buy_sell_symbol in enumerate(sliced_buy_sell_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, sell_symbol, last_sell_chore_id = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, buy_symbol, sell_symbol, last_sell_chore_id))

    # Checking alert in contact_alert
    check_str = "max_open_notional_per_side breached for SELL side"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_contact_alert(check_str, assert_fail_message)

    # Checking all plan pause
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
            f"Unexpected, plan_state must be paused, received {pair_plan.plan_state}, pair_plan: {pair_plan}"


@pytest.mark.nightly
def test_all_plan_pause_for_max_gross_n_open_notional_breach(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests system-wide pause when gross and open notional limits are breached.

        This test validates that all planegies pause when combined gross and open notional
        value exceeds max_gross_n_open_notional (136,000).

        Test Flow:
        1. Sets max_gross_n_open_notional to 136,000
        2. Creates planegies based on configuration:
           - 2 planegies with 2 chores each if multiple chores allowed
           - 8 planegies (4 buy, 4 sell) if single chore
        3. Places chores until breach
        4. Attempts additional chore
        5. Verifies system pause

        Key Validations:
        - Confirms notional aggregation
        - Verifies system-wide pause
        - Checks alert messages
        - Validates limit calculations
        - Tests post-breach chore blocking
    """
    # INFO:
    # Test sets max_gross_n_open_notional = 136_000

    # - if multi open chores are allowed:
    # triggers 2 street_books and places 2 chores each side from each executor
    # - if multi open chores are not allowed:
    # triggers 8 street_books out of which 4 places BUY chores each and rest 4 places SELL chores each

    # these 8 chores must pass for positive check, then one more BUY chore is placed in
    # any executor and this new chore journal must trigger all plan-pause + alert must be created in plan_alert

    # Updating contact limits
    expected_contact_limits_.max_gross_n_open_notional = 136_000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    if executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

        # starting plans one by one
        pair_plan_list = []
        for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
            stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
            pair_plan_list.append(stored_pair_plan_basemodel)
            time.sleep(2)

        executor_http_clients_n_last_chore_id_tuple_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
            results = [executor.submit(handle_place_both_side_chores_for_contact_limits_test,
                                       buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                       deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                       deepcopy(symbol_overview_obj_list),
                                       deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                       refresh_sec_update_fixture, False)
                       for idx, buy_sell_symbol in enumerate(sliced_buy_sell_symbol_list)]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

                executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id = future.result()
                executor_http_clients_n_last_chore_id_tuple_list.append(
                    (executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id))
    else:
        sliced_buy_symbol_list = leg1_leg2_symbol_list[:4]
        # starting plans one by one
        pair_plan_list = []
        for buy_symbol, sell_symbol in sliced_buy_symbol_list:
            stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
            pair_plan_list.append(stored_pair_plan_basemodel)
            time.sleep(2)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_symbol_list)) as executor:
            results = [
                executor.submit(handle_place_single_side_chores_for_contact_limits_test,
                                buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                deepcopy(symbol_overview_obj_list),
                                deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                refresh_sec_update_fixture, Side.BUY,
                                leg1_side=Side.BUY, leg2_side=Side.SELL)
                for idx, buy_sell_symbol in enumerate(sliced_buy_symbol_list)]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

        sliced_sell_symbol_list = leg1_leg2_symbol_list[4:8]
        # starting plans one by one
        pair_plan_list = []
        for buy_symbol, sell_symbol in sliced_sell_symbol_list:
            stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
            pair_plan_list.append(stored_pair_plan_basemodel)
            time.sleep(2)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_sell_symbol_list)) as executor:
            results = [
                executor.submit(handle_place_single_side_chores_for_contact_limits_test,
                                buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                deepcopy(symbol_overview_obj_list),
                                deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                refresh_sec_update_fixture, Side.SELL,
                                leg1_side=Side.BUY, leg2_side=Side.SELL)
                for idx, buy_sell_symbol in enumerate(sliced_sell_symbol_list)]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

    # Till this point since max_gross_n_open_notional_breach limits is breached in last chore, all chores
    # must have been placed but any new chore must not be placed, checking that now...

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    limit_breaching_pair_plan = create_plan(buy_symbol, sell_symbol, pair_plan_)
    handle_place_both_side_chores_for_contact_limits_test(
        buy_symbol, sell_symbol, limit_breaching_pair_plan, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, expect_no_chore=True)

    # Checking alert in contact_alert
    check_str = "max_gross_n_open_notional breached,"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_contact_alert(check_str, assert_fail_message)

    # Checking all plan pause
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
            f"Unexpected, plan_state must be paused, received {pair_plan.plan_state}, pair_plan: {pair_plan}"


def all_plan_pause_test_for_max_reject_limit_breach(
        buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
        expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec):
    # explicitly setting waived_initial_chores to 10 for this test case
    expected_plan_limits_.cancel_rate.waived_initial_chores = 10
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_plan, executor_http_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_start_status_))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_to_reject_chores"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 1
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 2
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # updating fixture values for this test-case
        max_loop_count_per_side = 2

        last_buy_rej_id, last_sell_rej_id = (
            handle_rej_chore_test(buy_symbol, sell_symbol, created_pair_plan, expected_plan_limits_,
                                  last_barter_fixture_list, max_loop_count_per_side,
                                  False, executor_http_client, config_dict, residual_wait_sec))
        return executor_http_client, created_pair_plan, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_last_n_sec_chore_counts(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
                                 expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                                 last_barter_fixture_list, market_depth_basemodel_list,
                                 buy_chore_, sell_chore_,
                                 max_loop_count_per_side, expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests tracking and enforcement of chore counts within configurable time windows.

        This test validates that the system accurately tracks chore counts within specified
        time periods and properly handles the rolling window of chore count tracking.

        Test Flow:
        1. Sets up rolling count configuration:
           - Sets rolling_tx_count_period_seconds to 10000
        2. Places multiple chores across different timeframes:
           - Places chores in rapid succession
           - Waits for time window expiration
        3. Verifies count tracking at various points
        4. Tests count expiration
        5. Validates time window handling

        Key Validations:
        - Confirms accurate chore count tracking
        - Verifies proper time window management
        - Checks expiration of old chores from count
        - Validates count updates in real-time
        - Ensures proper time window calculations
    """
    # Updating contact limits
    expected_contact_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds = 10000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    if executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    else:
        leg1_leg2_symbol_list = leg1_leg2_symbol_list[:8]
    executor_http_clients_n_last_chore_id_tuple_list = []

    # starting plans one by one
    pair_plan_list = []
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        stored_pair_plan_basemodel = create_plan(leg1_symbol, leg2_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_chores_for_contact_limits_test,
                                   leg1_leg2_symbol[0], leg1_leg2_symbol[1], pair_plan_list[idx],
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture, False)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id))

    chore_count_updated_chore_journals = (
        post_book_service_http_client.get_last_n_sec_chores_by_events_query_client(
            expected_contact_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds,
            [ChoreEventType.OE_NEW]))

    assert len(chore_count_updated_chore_journals) == 1, \
        ("Unexpected: Length of returned list by get_last_n_sec_chores_by_events_query_client must be 1, "
         f"received: {len(chore_count_updated_chore_journals)}, received list: {chore_count_updated_chore_journals}")

    assert 8 == chore_count_updated_chore_journals[0].current_period_chore_count, \
        (f"Mismatch: Expected last_n_sec new chore_counts: 8, received: "
         f"{chore_count_updated_chore_journals[0].current_period_chore_count}")

    # Updating contact limits
    expected_contact_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds = 2
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)
    time.sleep(3)   # wait to check after 2 sec to check no chore is found after it

    chore_count_updated_chore_journals = (
        post_book_service_http_client.get_last_n_sec_chores_by_events_query_client(
            expected_contact_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds,
            [ChoreEventType.OE_NEW]))

    assert len(chore_count_updated_chore_journals) == 0, \
        ("Unexpected: Length of returned list by get_last_n_sec_chores_by_events_query_client must be 1, "
         f"received: {len(chore_count_updated_chore_journals)}, received list: {chore_count_updated_chore_journals}")


@pytest.mark.nightly
def test_contact_limits_rolling_new_chore_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                   pair_plan_, expected_plan_limits_,
                                                   expected_plan_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   buy_chore_, sell_chore_,
                                                   max_loop_count_per_side,
                                                   expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests enforcement of rolling new chore limits at contact level.

        This test validates that the system properly enforces rolling new chore count
        limits across the entire contact. It ensures proper risk management when
        chore placement frequency exceeds configured thresholds.

        Test Flow:
        1. Configures contact limits:
           - Sets max_rolling_tx_count to 7
           - Sets rolling_tx_count_period_seconds to 10000
        2. Creates multiple planegies
        3. Places chores to approach and exceed limits
        4. Verifies system-wide pause
        5. Validates alert generation

        Key Validations:
        - Confirms proper chore count tracking
        - Verifies system-wide planegy pause
        - Checks appropriate alert generation
        - Validates rolling window calculations
        - Ensures proper limit enforcement
    """

    # INFO:
    # Test has rolling_max_chore_count.max_rolling_tx_count = 7 and
    # rolling_max_chore_count.rolling_tx_count_period_seconds = 10000 that means within 10000 secs 8th new chore
    # will trigger all plan-pause.

    # - if multi open chores are allowed:
    # Test will create 2 plans and will place 2 chore each side
    # - if multi open chores are not allowed:
    # Test will create 8 plans and will place BUY chore from each executor

    # 8th new chore must breach limit and trigger all plan-pause and any new chore must get ignored since plans
    # got paused + alert must be present in contact alerts

    # Updating contact limits
    expected_contact_limits_.rolling_max_chore_count.max_rolling_tx_count = 7
    expected_contact_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds = 10000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    if executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:8]

    # starting plans one by one
    pair_plan_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)
    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_chores_for_contact_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_plan_list[idx],
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture, False)
                   for idx, buy_sell_symbol in enumerate(sliced_buy_sell_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, buy_symbol, last_buy_chore_id, sell_symbol, last_sell_chore_id))

    time.sleep(2)

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    stored_pair_plan_basemodel = create_plan(buy_symbol, sell_symbol, pair_plan_)
    handle_place_both_side_chores_for_contact_limits_test(
        buy_symbol, sell_symbol, stored_pair_plan_basemodel, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, expect_no_chore=True)

    # Checking alert in contact_alert
    check_str = "rolling_max_chore_count breached:"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_contact_alert(check_str, assert_fail_message)

    # Checking all plan pause
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
            f"Unexpected, plan_state must be paused, received {pair_plan.plan_state}, pair_plan: {pair_plan}"


@pytest.mark.nightly
def test_all_plan_pause_for_max_reject_limit_breach(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        max_loop_count_per_side, expected_contact_limits_, refresh_sec_update_fixture):
    """
        Tests system-wide planegy pause when maximum rejection limit is breached.

        This test validates that all planegies are properly paused when the maximum
        rejection count limit is exceeded. It ensures proper system-wide risk management
        when rejection thresholds are breached.

        Test Flow:
        1. Configures test environment with specific rejection limits:
           - Sets max_rolling_tx_count to 4
           - Sets rolling_tx_count_period_seconds to 10000
        2. Creates multiple planegies and places chores
        3. Forces chore rejections to breach limit
        4. Verifies system-wide planegy pause
        5. Validates alert generation

        Key Validations:
        - Confirms proper rejection count tracking
        - Verifies system-wide planegy pause
        - Checks appropriate alert generation
        - Validates rejection threshold calculations
        - Ensures proper limit enforcement
    """
    # INFO:
    # Test has rolling_max_reject_count.max_rolling_tx_count = 4 and
    # rolling_max_reject_count.rolling_tx_count_period_seconds = 10000 that means within 10000 secs 5th rej
    # will trigger all plan-pause. Test will create 2 plans and will place 2 chore each to equal threshold of
    # 4 rej chores after which one more chore will also be trigger by either of plan and that must trigger
    # all plan-pause + alert must be present in contact alerts

    # Settings contact_limits for this test
    expected_contact_limits_.rolling_max_reject_count.max_rolling_tx_count = 4
    expected_contact_limits_.rolling_max_reject_count.rolling_tx_count_period_seconds = 10000
    email_book_service_native_web_client.put_contact_limits_client(expected_contact_limits_)

    # updating fixture values for this test-case
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    executor_http_clients_n_last_chore_id_tuple_list = []

    # starting plans one by one
    pair_plan_list = []
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        stored_pair_plan_basemodel = create_plan(leg1_symbol, leg2_symbol, pair_plan_)
        pair_plan_list.append(stored_pair_plan_basemodel)
        time.sleep(2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(all_plan_pause_test_for_max_reject_limit_breach,
                                   leg1_leg2_symbol[0], leg1_leg2_symbol[1], pair_plan_list[idx],
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            (executor_http_client, created_pair_plan, buy_symbol,
             sell_symbol, last_buy_rej_id, last_sell_rej_id) = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, created_pair_plan, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id))

    time.sleep(2)
    # Placing on more rej chore that must trigger auto-kill_switch
    # (Placed chore will be rej type by simulator because of continues_special_chore_count)
    executor_http_client, created_pair_plan, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id = (
        executor_http_clients_n_last_chore_id_tuple_list)[0]

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, created_pair_plan))
    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(created_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)

    latest_chore_journal = get_latest_chore_journal_with_events_and_symbol(
        [ChoreEventType.OE_BRK_REJ, ChoreEventType.OE_EXH_REJ], buy_symbol,
        executor_http_client, last_chore_id=last_buy_rej_id)

    # Checking alert in contact_alert
    check_str: str = "max_allowed_rejection_within_period breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_contact_alert(check_str, assert_fail_message)

    # Checking all plan pause
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
            f"Unexpected, plan_state must be paused, received {pair_plan.plan_state}, pair_plan: {pair_plan}"


def _place_chore_at_limit_up(
        leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list):
    buy_symbol, sell_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, []))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        last_barter_fixture_list[0]['px'] = 145
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)

        # create market_depths
        cpp_create_all_market_depth_client(active_pair_plan.cpp_port, market_depth_basemodel_list)

        place_new_chore(buy_symbol, Side.BUY, 150, 90, executor_http_client, buy_inst_type)

        # Internally checks if chore_journal is found with OE_ACK state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                              buy_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_place_chore_at_limit_up(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement behavior at limit up price levels.

        This test validates system behavior when attempting to place chores in limit up
        conditions, where bartering is restricted due to excessive upward price movement.
        Limit up occurs when a security's price increases to its maximum allowed level,
        typically triggered by significant upward price movement, causing suspension of
        ask-side quotes and preventing further upward price movement.

        Test Flow:
        1. Sets up market conditions:
           - Removes ask side depth (characteristic of limit up)
           - Sets reference prices near limit up
           - Creates last barter at px=145
        2. Attempts chore placement at limit up (px=150)
        3. Verifies proper chore handling
        4. Validates system behavior

        Key Validations:
        - Confirms proper chore handling at limit up
        - Verifies price validation logic
        - Checks market data handling
        - Validates system stability
        - Ensures proper risk controls
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # removing any ask side depth for Type1_Sec_1 - limit up don't have any ask side depth or quote
    market_depth_basemodel_list = market_depth_basemodel_list[:5] + market_depth_basemodel_list[10:]

    _place_chore_at_limit_up(
        leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list)


@pytest.mark.nightly
def test_place_chore_at_limit_up_with_partial_market_depth(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement at limit up with incomplete market depth data.

        This test validates system behavior during limit up conditions with partial market
        depth data. Limit up represents a market state where bartering is restricted due to
        significant upward price movement, characterized by absence of ask-side quotes and
        reaching maximum allowed price levels, often triggered by circuit breakers.

        Test Flow:
        1. Sets up market conditions:
           - Removes certain market depth levels
           - Configures partial depth data
           - Creates skewed market data typical of limit up
        2. Attempts chore placement at limit up
        3. Verifies proper chore handling
        4. Validates system behavior

        Key Validations:
        - Confirms proper chore handling with partial data
        - Verifies price validation logic
        - Checks market depth handling
        - Validates system stability
        - Ensures proper risk controls
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # removing any ask side depth for Type1_Sec_1 - limit up don't have any ask side depth or quote
    # Also removing last market depth of cb_sec's bid side
    last_cb_sec_bid_md = market_depth_basemodel_list[4]
    last_cb_sec_bid_md.position = 3
    market_depth_basemodel_list = (market_depth_basemodel_list[:3] + [last_cb_sec_bid_md] +     # cb_sec bid md only
                                   market_depth_basemodel_list[10:])    # eqt_sec bid and ask md

    _place_chore_at_limit_up(
        leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list)


def place_chore_at_limit_dn(
        leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list):
    sell_symbol, buy_symbol, active_pair_plan, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_,
                                                 expected_plan_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, [],
                                                 leg1_side=Side.SELL, leg2_side=Side.BUY))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_pair_plan.id)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Positive check
        last_barter_fixture_list[0]['px'] = 52
        run_last_barter(sell_symbol, buy_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)

        # create market_depths
        cpp_create_all_market_depth_client(active_pair_plan.cpp_port, market_depth_basemodel_list)

        place_new_chore(sell_symbol, Side.SELL, 50, 90, executor_http_client, sell_inst_type)

        # Internally checks if chore_journal is found with OE_ACK state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                              sell_symbol, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_place_chore_at_limit_dn(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement behavior at limit down price levels.

        This test validates system behavior when attempting to place chores in limit down
        conditions, where bartering is restricted due to severe downward price movement.
        Limit down occurs when a security's price decreases to its minimum allowed level,
        typically triggered by significant market stress, causing suspension of bid-side
        quotes and preventing further downward price movement.

        Test Flow:
        1. Sets up market conditions:
           - Removes bid side depth (characteristic of limit down)
           - Sets reference prices near limit down
           - Creates last barter at px=52
        2. Attempts chore placement at limit down (px=50)
        3. Verifies proper chore handling
        4. Validates system behavior

        Key Validations:
        - Confirms proper chore handling at limit down
        - Verifies price validation logic
        - Checks market data handling
        - Validates system stability
        - Ensures proper risk controls
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # removing any ask side depth for Type1_Sec_1 - limit dn don't have any bid side depth or quote
    market_depth_basemodel_list = market_depth_basemodel_list[5:]

    place_chore_at_limit_dn(
        leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list)


@pytest.mark.nightly
def test_place_chore_at_limit_dn_with_partial_market_depth(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    """
        Tests chore placement at limit down with incomplete market depth data.

        This test validates system behavior during limit down conditions with partial market
        depth data. Limit down represents a market state where bartering is restricted due to
        severe downward price movement, characterized by absence of bid-side quotes and
        reaching minimum allowed price levels, often occurring during market crashes or
        severe stress events.

        Test Flow:
        1. Sets up market conditions:
           - Removes certain market depth levels
           - Configures partial depth data
           - Creates skewed market data typical of limit down
        2. Attempts chore placement at limit down
        3. Verifies proper chore handling
        4. Validates system behavior

        Key Validations:
        - Confirms proper chore handling with partial data
        - Verifies price validation logic
        - Checks market depth handling
        - Validates system stability
        - Ensures proper risk controls
    """
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # removing any ask side depth for Type1_Sec_1 - limit dn don't have any bid side depth or quote
    last_cb_sec_ask_md = market_depth_basemodel_list[4]
    last_cb_sec_ask_md.position = 3
    market_depth_basemodel_list = (market_depth_basemodel_list[5:8] + [last_cb_sec_ask_md] +    # cb_sec bid md only
                                   market_depth_basemodel_list[10:])    # eqt_sec bid and ask md

    place_chore_at_limit_dn(
        leg1_leg2_symbol_list,
        pair_plan_, expected_plan_limits_,
        expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list)


# TODO: Add test for missing plan_limits
# > limit_up_down_volume_participation_rate
