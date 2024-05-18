# standard imports
import copy
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
def test_min_chore_notional_breach_in_normal_strat_mode(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative check
        # placing new non-systematic new_chore
        px = 1
        qty = 1
        check_str = "blocked chore_opportunity < min_chore_notional limit"
        assert_fail_msg = "Could not find any alert containing message to block chores due to less " \
                          "than limit chore_notional"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
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
def test_min_chore_notional_breach_in_relaxed_strat_mode(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_chore_limits_, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 StratMode.StratMode_Relaxed))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative check
        # placing new non-systematic new_chore
        px = 1
        qty = 1
        check_str = "blocked chore_opportunity < min_chore_notional_relaxed limit"
        assert_fail_msg = "Could not find any alert containing message to block chores due to less " \
                          "than limit chore_notional"
        limit_alert = handle_place_chore_and_check_str_in_alert_for_executor_limits(
            buy_symbol, Side.BUY, px, qty, check_str, assert_fail_msg, active_pair_strat.id, executor_http_client,
            last_chore_id=placed_chore_journal.chore.chore_id)

        # Using regex to extract the value after the '<' symbol
        value_pattern = re.compile(r'<\s*(\d+(?:\.\d+)?)')

        match = value_pattern.search(limit_alert.alert_brief)

        if match:
            extracted_value = match.group(1)
            assert extracted_value != expected_strat_limits_.min_chore_notional, \
                ("When strat_mode is relaxed, min_chore_notional is replaced by random value between "
                 "min_chore_notional and min_chore_notional+min_chore_notional_allowance but found value same as"
                 f"expected_chore_limits_.min_chore_notional, "
                 f"expected_chore_limits_.min_chore_notional: {expected_strat_limits_.min_chore_notional}, "
                 f"expected_chore_limits_.min_chore_notional_allowance: "
                 f"{expected_strat_limits_.min_chore_notional_allowance}, "
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
def test_max_chore_notional_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                   pair_strat_, expected_strat_limits_,
                                   expected_strat_status_, symbol_overview_obj_list,
                                   last_barter_fixture_list, market_depth_basemodel_list,
                                   buy_chore_, sell_chore_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))
    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_chore
        px = 1000
        qty = 100
        check_str = "blocked generated chore, breaches max_chore_notional limit, expected less than"
        assert_fail_msg = "Could not find any alert containing message to block chores due to more " \
                          "than limit chore_notional"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
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
def test_max_chore_qty_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                              pair_strat_, expected_strat_limits_,
                              expected_strat_status_, symbol_overview_obj_list,
                              last_barter_fixture_list, market_depth_basemodel_list,
                              buy_chore_, sell_chore_,
                              max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_chore
        px = 10
        qty = 600
        check_str = "blocked generated chore, breaches max_chore_qty limit, expected less than"
        assert_fail_msg = "Could not find any alert containing message to block chores due to excessive chore qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
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
def test_breach_threshold_px_with_wrong_tob(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                            pair_strat_, expected_strat_limits_,
                                            expected_strat_status_, symbol_overview_obj_list,
                                            last_barter_fixture_list, market_depth_basemodel_list,
                                            buy_chore_, sell_chore_, max_loop_count_per_side,
                                            refresh_sec_update_fixture):
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 [], market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        sample_last_barter = copy.deepcopy(last_barter_fixture_list[0])
        sample_last_barter["px"] = 0
        run_last_barter(buy_symbol, sell_symbol, [sample_last_barter], executor_http_client)

        # Negative Check - since buy tob is missing last_barter and sell side last_barter.px is 0 both
        # chores must get blocked
        px = 100
        qty = 90
        check_str = f"blocked generated chore, symbol: {buy_symbol}, side = <Side.BUY: 'BUY'> as " \
                    f"top_of_book.last_barter.px is none or 0"
        assert_fail_msg = "Could not find any alert containing message to block chores tob last barter as None"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)

        check_str = ("blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                     f"symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        px = 100
        qty = 90
        check_str = f"blocked generated chore, symbol: {sell_symbol}, side = <Side.SELL: 'SELL'> as " \
                    f"top_of_book.last_barter.px is none or 0"
        assert_fail_msg = "Could not find any alert containing message to block chores tob last barter as None"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)

        check_str = ("blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                     f"symbol_side_key: %%symbol-side={sell_symbol}-{Side.SELL.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        # Positive check - if tob is fine then chores must get placed

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], executor_http_client)

        update_tob_through_market_depth_to_place_sell_chore(executor_http_client, ask_sell_top_market_depth,
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
                                                   pair_strat_, expected_strat_limits_,
                                                   expected_strat_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   buy_chore_, sell_chore_,
                                                   max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))
    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated unsupported side chore"
        assert_fail_msg = "Could not find any alert containing message to block chores due to unsupported side"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.SIDE_UNSPECIFIED, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        check_str = ("blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                     f"symbol_side_key: %%symbol-side={buy_symbol}")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

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
                                             pair_strat_, expected_strat_limits_,
                                             expected_strat_status_, symbol_overview_obj_list,
                                             last_barter_fixture_list, market_depth_basemodel_list,
                                             buy_chore_, sell_chore_,
                                             max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, []))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Negative Check: currently no market_depth exists so default px_by_max_level=0 will be used
        market_depth_list = executor_http_client.get_all_market_depth_client()
        for market_depth in market_depth_list:
            if market_depth.symbol == buy_symbol:
                market_depth.px = 0
                executor_http_client.put_market_depth_client(jsonable_encoder(market_depth,
                                                                              by_alias=True, exclude_none=True))

        # placing new non-systematic new_chore
        time.sleep(5)
        px = 100
        qty = 90
        check_str = f"blocked generated chore, system_symbol = '{buy_symbol}', side = <Side.BUY: 'BUY'>, " \
                    f"unable to find valid px based on chore_limits.max_px_levels"
        assert_fail_msg = "Could not find any alert containing message to block chores due to 0 market depth px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)

        check_str = ("blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                     f"symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        # positive test case: Putting valid market depth
        create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list, executor_http_client)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
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
                                                        pair_strat_, expected_strat_limits_,
                                                        expected_strat_status_, symbol_overview_obj_list,
                                                        last_barter_fixture_list, market_depth_basemodel_list,
                                                        buy_chore_, sell_chore_,
                                                        max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, []))

    # not creating sell symbol's 0th bid md and buy_symbol's 0th ask md
    buy_zeroth_ask_md = None
    sell_zeroth_bid_md = None
    for md in market_depth_basemodel_list:
        if md.symbol == buy_symbol:
            if md.side == TickType.ASK and md.position == 0:
                buy_zeroth_ask_md = md
            else:
                created_market_depth = executor_http_client.create_market_depth_client(md)
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
                created_market_depth = executor_http_client.create_market_depth_client(md)
                created_market_depth.id = None
                created_market_depth.cumulative_avg_px = None
                created_market_depth.cumulative_notional = None
                created_market_depth.cumulative_qty = None
                assert created_market_depth == md, \
                    f"Mismatch created market_depth: expected {md} received {created_market_depth}"

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
        check_str = (f"blocked generated BUY chore, tob.symbol = '{buy_symbol}', side = <Side.BUY: 'BUY'> as "
                     f"aggressive_quote is not found or has no px")
        assert_fail_msg = "Could not find any alert containing message to block chores tob last barter as None"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)
        check_str = ("blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                     f"symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = (f"blocked generated SELL chore, tob.symbol = '{sell_symbol}', side = <Side.SELL: 'SELL'> as "
                     f"aggressive_quote is not found or has no px")
        assert_fail_msg = "Could not find any alert containing message to block chores tob last barter as None"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)
        check_str = ("blocked generated chore, breach_px returned None from get_breach_threshold_px for "
                     f"symbol_side_key: %%symbol-side={sell_symbol}-{Side.SELL.value}%%")
        assert_fail_msg = f"Can't find alert saying: {check_str!r}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        # creating earlier skipped market depths also
        for md in [buy_zeroth_ask_md, sell_zeroth_bid_md]:
            created_market_depth = executor_http_client.create_market_depth_client(md)
            created_market_depth.id = None
            created_market_depth.cumulative_avg_px = None
            created_market_depth.cumulative_notional = None
            created_market_depth.cumulative_qty = None
            assert created_market_depth == md, \
                f"Mismatch created market_depth: expected {md} received {created_market_depth}"
            time.sleep(1)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))
        time.sleep(1)

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], executor_http_client)

        update_tob_through_market_depth_to_place_sell_chore(executor_http_client, ask_sell_top_market_depth,
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
                               pair_strat_, expected_strat_limits_,
                               expected_start_status_, symbol_overview_obj_list,
                               last_barter_fixture_list, market_depth_basemodel_list,
                               top_of_book_list_, refresh_sec_update_fixture):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # explicitly setting waived_min_chores to 10 for this test case
    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        # Deleting all tobs
        tob_list = executor_http_client.get_all_top_of_book_client()
        for tob in tob_list:
            executor_http_client.delete_top_of_book_client(tob.id, return_obj_copy=False)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated chore, unable to conduct px checks: top_of_book is sent None for strat"
        assert_fail_message = "Could not find any alert containing message to block chores due to no tob"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      )
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

@pytest.mark.nightly
def test_breach_threshold_px_for_max_buy_n_min_sell_px_by_basis_points(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
        stored_market_depths = executor_http_client.get_all_market_depth_client()
        for market_depth_basemodel in stored_market_depths:
            if market_depth_basemodel.symbol == buy_symbol:
                if market_depth_basemodel.side == "ASK":
                    market_depth_basemodel.px = sell_px + (5 * market_depth_basemodel.position)
                market_depth_basemodel.exch_time = get_utc_date_time()
                market_depth_basemodel.arrival_time = get_utc_date_time()

                executor_http_client.put_market_depth_client(market_depth_basemodel)
                time.sleep(1)

        # max_px_by_basis_point = 97.75
        # max_px_by_deviation = 139.2
        # px_by_max_level = 105
        # >>> min comes max_px_by_basis_point which is being tested in this test

        # Negative Check for buy chore - chore block since px > max_px_by_basis_point
        # placing new non-systematic new_chore
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        px = 98
        qty = 90
        check_str = "blocked generated BUY chore, chore px = .* > allowed max_px"
        assert_fail_message = f"cant find any alert with msg: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Positive check for buy chore - chore places since px < max_px_by_basis_point
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        px = 97
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # checking min_px_by_basis_point

        # updating last_barter for sell symbol
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        sample_last_barter_obj = LastBarterBaseModel(**last_barter_fixture_list[1])
        sample_last_barter_obj.px = 100
        sample_last_barter_obj.exch_time = get_utc_date_time()
        sample_last_barter_obj.arrival_time = get_utc_date_time()
        executor_http_client.create_last_barter_client(sample_last_barter_obj)

        # updating buy market depth to make its max depth px value less than calculated max_px_by_basis_point
        buy_px = 100
        stored_market_depths = executor_http_client.get_all_market_depth_client()
        for pos in range(4, -1, -1):
            for market_depth_basemodel in stored_market_depths:
                if market_depth_basemodel.symbol == sell_symbol:
                    if market_depth_basemodel.side == "BID" and market_depth_basemodel.position == pos:
                        market_depth_basemodel.px = buy_px - (5 * market_depth_basemodel.position)
                        market_depth_basemodel.exch_time = get_utc_date_time()
                        market_depth_basemodel.arrival_time = get_utc_date_time()

                        executor_http_client.put_market_depth_client(market_depth_basemodel)
                        time.sleep(1)
                        break

        # min_px_by_basis_point = 85
        # min_px_by_deviation = 80
        # px_by_max_level = 80
        # >>> max comes max_px_by_basis_point which is being tested in this test

        # Negative Check for sell chore - chore block since px < max_px_by_basis_point
        # placing new non-systematic new_chore
        # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        px = 84
        qty = 90
        check_str = "blocked generated SELL chore, chore px = .* < allowed min_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Positive check for sell chore - chore places since px > max_px_by_basis_point
        # run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        sample_last_barter_obj = LastBarterBaseModel(**last_barter_fixture_list[1])
        sample_last_barter_obj.px = 100
        sample_last_barter_obj.exch_time = get_utc_date_time()
        sample_last_barter_obj.arrival_time = get_utc_date_time()
        executor_http_client.create_last_barter_client(sample_last_barter_obj)

        px = 86
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client)

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


# FIXME: not implemented: supposed to fail
# chore limits
def test_max_contract_qty(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                          buy_chore_, sell_chore_, buy_fill_journal_,
                          sell_fill_journal_, expected_buy_chore_snapshot_,
                          expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
                          pair_strat_, expected_strat_limits_, expected_strat_status_,
                          expected_strat_brief_, expected_portfolio_status_, 
                          last_barter_fixture_list, symbol_overview_obj_list,
                          market_depth_basemodel_list, expected_chore_limits_,
                          expected_portfolio_limits_, max_loop_count_per_side,
                          leg1_leg2_symbol_list, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        # Updating chore_limits for Negative check
        expected_chore_limits_.max_contract_qty = 80
        updated_chore_limits = ChoreLimitsBaseModel(id=1, max_contract_qty=80)
        updated_chore_limits = email_book_service_native_web_client.patch_chore_limits_client(
            jsonable_encoder(updated_chore_limits, by_alias=True, exclude_none=True))
        assert updated_chore_limits == expected_chore_limits_

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "qty: .* > max contract qty"
        assert_fail_message = "Could not find any alert containing message to block chores " \
                              "due to contract qty breach"
        # placing new non-systematic new_chore
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)
        print(f"symbol: {buy_symbol}, Created new_chore obj")

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(
            ChoreEventType.OE_NEW, buy_symbol, executor_http_client, expect_no_chore=True,
            last_chore_id=placed_chore_journal.chore.chore_id)

        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_message)
        assert True
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)


@pytest.mark.nightly
def test_breach_threshold_px_for_buy_max_n_sell_min_px_by_deviation(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]

    # updating bid market depth to make its lowest depth px value greater than calculated max_px_by_basis_point
    buy_bid_px = 100
    sell_bid_px = 85
    sell_ask_px = 75
    for market_depth_basemodel in market_depth_basemodel_list:
        if market_depth_basemodel.symbol == buy_symbol and market_depth_basemodel.side == "BID":
            market_depth_basemodel.px = buy_bid_px
            buy_bid_px -= 1
        elif market_depth_basemodel.symbol == sell_symbol:
            if market_depth_basemodel.side == "ASK":
                market_depth_basemodel.px = sell_ask_px
                sell_ask_px += 1
            else:
                market_depth_basemodel.px = sell_bid_px
                sell_bid_px -= 1

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        buy_sample_last_barter = LastBarterBaseModel(**last_barter_fixture_list[0])
        buy_sample_last_barter.px = 80
        buy_sample_last_barter.exch_time = get_utc_date_time()
        buy_sample_last_barter.arrival_time = get_utc_date_time()
        executor_http_client.create_last_barter_client(buy_sample_last_barter)

        # max_px_by_basis_point = 139.15
        # max_px_by_deviation = 96
        # px_by_max_level = 125
        # >>> min comes max_px_by_deviation which is being tested in this test

        # Negative Check for buy chore - chore block since px > max_px_by_deviation
        # placing new non-systematic new_chore
        px = 97
        qty = 90
        check_str = "blocked generated BUY chore, chore px = .* > allowed max_px"
        assert_fail_message = "Could not find any alert containing message to block chores tob last barter px as 0"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Positive check for buy chore - chore places since px < max_px_by_deviation
        px = 95
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        sell_sample_last_barter = LastBarterBaseModel(**last_barter_fixture_list[1])
        sell_sample_last_barter.px = 110
        sell_sample_last_barter.exch_time = get_utc_date_time()
        sell_sample_last_barter.arrival_time = get_utc_date_time()
        executor_http_client.create_last_barter_client(sell_sample_last_barter)

        # min_px_by_basis_point = 85
        # min_px_by_deviation = 88
        # px_by_max_level = 81
        # >>> max comes max_px_by_basis_point which is being tested in this test

        # Negative Check for sell chore - chore block since px < min_px_by_deviation
        # placing new non-systematic new_chore
        px = 87
        qty = 90
        check_str = "blocked generated SELL chore, chore px = .* < allowed min_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Positive check for sell chore - chore places since px > min_px_by_deviation
        px = 89
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client)

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
                                                 pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 buy_chore_, sell_chore_,
                                                 max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # # Checking max_px_by_basis_point
        # buy_tob.last_barter.px = 80
        # update_date_time = DateTime.utcnow()
        # buy_tob.last_update_date_time = update_date_time
        # executor_http_client.put_top_of_book_client(jsonable_encoder(buy_tob, by_alias=True, exclude_none=True))

        # updating sell market depth to make its max depth px value lowest of all values
        sell_px = 91
        stored_market_depths = executor_http_client.get_all_market_depth_client()
        for market_depth_basemodel in stored_market_depths:
            if market_depth_basemodel.symbol == buy_symbol:
                if market_depth_basemodel.side == "ASK":
                    market_depth_basemodel.px = sell_px + market_depth_basemodel.position
                market_depth_basemodel.exch_time = get_utc_date_time()
                market_depth_basemodel.arrival_time = get_utc_date_time()

                executor_http_client.put_market_depth_client(market_depth_basemodel)
                time.sleep(1)

        # max_px_by_basis_point = 109.2
        # max_px_by_deviation = 139.2
        # px_by_max_level = 95
        # >>> min comes px_by_max_level which is being tested in this test

        # Negative Check for buy chore - chore block since px > px_by_max_level
        # placing new non-systematic new_chore
        px = 96
        qty = 90
        check_str = "blocked generated BUY chore, chore px = .* > allowed max_px"
        assert_fail_message = "Could not find any alert containing message to block chores tob last barter px as 0"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Positive check for buy chore - chore places since px < px_by_max_level

        px = 94
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # checking min_px_by_basis_point
        sell_sample_last_barter = LastBarterBaseModel(**last_barter_fixture_list[1])
        sell_sample_last_barter.px = 110
        sell_sample_last_barter.exch_time = get_utc_date_time()
        sell_sample_last_barter.arrival_time = get_utc_date_time()
        executor_http_client.create_last_barter_client(sell_sample_last_barter)

        # updating buy market depth to make its max depth px value less than calculated max_px_by_basis_point
        buy_px = 100
        stored_market_depths = executor_http_client.get_all_market_depth_client()
        for pos in range(4, -1, -1):
            for market_depth_basemodel in stored_market_depths:
                if market_depth_basemodel.symbol == sell_symbol:
                    if market_depth_basemodel.side == "BID" and market_depth_basemodel.position == pos:
                        market_depth_basemodel.px = buy_px - pos
                        market_depth_basemodel.exch_time = get_utc_date_time()
                        market_depth_basemodel.arrival_time = get_utc_date_time()

                        executor_http_client.put_market_depth_client(market_depth_basemodel)
                        time.sleep(1)
                        break

        # min_px_by_basis_point = 85
        # min_px_by_deviation = 88
        # px_by_max_level = 95
        # >>> max comes px_by_max_level which is being tested in this test

        # Negative Check for sell chore - chore block since px < px_by_max_level
        # placing new non-systematic new_chore
        px = 94
        qty = 90
        check_str = "blocked generated SELL chore, chore px = .* < allowed min_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Positive check for sell chore - chore places since px > px_by_max_level

        px = 96
        qty = 90
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client)

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


# @@@ deprecated: no street_book can be set to ready without symbol_overview
# def test_strat_limits_with_none_symbol_overview(static_data_, clean_and_set_limits, buy_sell_symbol_list,
#                                                 pair_strat_, expected_strat_limits_,
#                                                 expected_start_status_, symbol_overview_obj_list,
#                                                 last_barter_fixture_list, market_depth_basemodel_list,
#                                                 buy_chore_, sell_chore_,
#                                                 max_loop_count_per_side, residual_wait_sec):
#     # Creating Strat
#     active_pair_strat = create_n_activate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
#                                                 copy.deepcopy(expected_strat_limits_),
#                                                 copy.deepcopy(expected_start_status_))
#
#     # running Last Barter
#     run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list)
#
#     # creating market_depth
#     create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)
#
#     # Adding strat in strat_collection
#     create_if_not_exists_and_validate_strat_collection(active_pair_strat)
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
def test_strat_limits_with_none_or_o_limit_up_down_px(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    limit_up_px = None
    limit_dn_px = 0
    # removing symbol_overview's limit_up/limit_down px
    for symbol_overview in symbol_overview_obj_list:
        limit_up_px = symbol_overview.limit_up_px
        symbol_overview.limit_up_px = None
        limit_dn_px = symbol_overview.limit_dn_px
        symbol_overview.limit_dn_px = None

    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
        px = 90
        qty = 95
        check_str = "limit up/down px not available limit-dn px"
        assert_fail_msg = f"couldn't find alert saying: {check_str!r}"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)

        updated_symbol_overview_json_list = []
        symbol_overview_list_ = executor_http_client.get_all_symbol_overview_client()
        for symbol_overview_ in symbol_overview_list_:
            symbol_overview_.limit_up_px = limit_up_px
            symbol_overview_.limit_dn_px = limit_dn_px
            updated_symbol_overview_json_list.append(jsonable_encoder(symbol_overview_, by_alias=True,
                                                                      exclude_none=True))
        # updating symbol_overview's limit_up/dn_px
        executor_http_client.patch_all_symbol_overview_client(updated_symbol_overview_json_list)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
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
def test_strat_limits_with_0_consumable_open_chores(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                    pair_strat_, expected_strat_limits_,
                                                    expected_strat_status_, symbol_overview_obj_list,
                                                    last_barter_fixture_list, market_depth_basemodel_list,
                                                    buy_chore_, sell_chore_,
                                                    max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_bartering_brief.consumable_open_chores = -1
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_buy_side_bartering_brief.consumable_open_chores == -1, \
            "Updated strat_brief.pair_buy_side_bartering_brief.consumable_open_chores to -1 using http route call but " \
            f"received unexpected returned value {updated_strat_brief}"

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated BUY chore, not enough consumable_open_chores"
        assert_fail_message = "Could not find any alert containing message to block " \
                              "BUY chore due to 0 consumable open chores"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_sell_side_bartering_brief.consumable_open_chores = -1
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_sell_side_bartering_brief.consumable_open_chores == -1

        # placing new non-systematic new_chore
        px = 70
        qty = 90
        check_str = "blocked generated SELL chore, not enough consumable_open_chores"
        assert_fail_message = "Could not find any alert containing message to block " \
                              "SELL chore due to 0 consumable open chores"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_limits_with_high_consumable_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                    pair_strat_, expected_strat_limits_,
                                                    expected_strat_status_, symbol_overview_obj_list,
                                                    last_barter_fixture_list, market_depth_basemodel_list,
                                                    buy_chore_, sell_chore_,
                                                    max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, activated_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{activated_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 30
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        # Negative check
        # placing new non-systematic new_chore
        px = 1000
        qty = 900
        check_str = "blocked generated BUY chore, breaches available consumable notional"
        assert_fail_message = "Could not find any alert containing message to block chores " \
                              "due to high consumable notional"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activated_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        # placing new non-systematic new_chore
        px = 7000
        qty = 900
        check_str = "blocked generated SELL chore, breaches available consumable notional"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activated_strat.id, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_limits_with_less_consumable_concentration(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                         pair_strat_, expected_strat_limits_,
                                                         expected_strat_status_, symbol_overview_obj_list,
                                                         last_barter_fixture_list, market_depth_basemodel_list,
                                                         buy_chore_, sell_chore_,
                                                         max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check

        # Checking alert when consumable_concentration < chore_qty
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_bartering_brief.consumable_concentration = 10
        strat_brief.pair_sell_side_bartering_brief.consumable_concentration = 10
        updated_strat_brief = executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True,
                                                                                           exclude_none=True))
        assert (updated_strat_brief.pair_buy_side_bartering_brief.consumable_concentration ==
                strat_brief.pair_buy_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_buy_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_buy_side_bartering_brief.consumable_concentration}"
        assert (updated_strat_brief.pair_sell_side_bartering_brief.consumable_concentration ==
                strat_brief.pair_sell_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_sell_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_sell_side_bartering_brief.consumable_concentration}"

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated BUY chore, not enough consumable_concentration:"
        assert_fail_message = "Could not find any alert containing message to block chores due to less " \
                              "consumable concentration"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        # placing new non-systematic new_chore
        px = 70
        qty = 90
        check_str = "blocked generated SELL chore, not enough consumable_concentration:"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Checking alert when consumable_concentration == 0
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_bartering_brief.consumable_concentration = 0
        strat_brief.pair_sell_side_bartering_brief.consumable_concentration = 0
        updated_strat_brief = executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True,
                                                                                           exclude_none=True))
        assert (updated_strat_brief.pair_buy_side_bartering_brief.consumable_concentration ==
                strat_brief.pair_buy_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_buy_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_buy_side_bartering_brief.consumable_concentration}"
        assert (updated_strat_brief.pair_sell_side_bartering_brief.consumable_concentration ==
                strat_brief.pair_sell_side_bartering_brief.consumable_concentration), \
            "Mismatch pair_sell_side_bartering_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_sell_side_bartering_brief.consumable_concentration}"

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "blocked generated BUY chore, unexpected: consumable_concentration found 0!"
        assert_fail_message = "Could not find any alert containing message to block chores due to less " \
                              "consumable concentration"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)
        # placing new non-systematic new_chore
        px = 70
        qty = 90
        check_str = "blocked generated SELL chore, unexpected: consumable_concentration found 0!"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_limits_with_symbol_overview_limit_dn_up_px(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                          pair_strat_, expected_strat_limits_,
                                                          expected_strat_status_, symbol_overview_obj_list,
                                                          last_barter_fixture_list, market_depth_basemodel_list,
                                                          buy_chore_, sell_chore_,
                                                          max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_chore
        px = 160
        qty = 90
        check_str = "blocked generated BUY chore, limit up bartering not allowed on day-1"
        assert_fail_message = "Could not find any alert containing message to block chores due to chore_px higher " \
                              "than symbol_overview's limit_up_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)

        # placing new non-systematic new_chore
        px = 40
        qty = 90
        check_str = "blocked generated SELL chore, limit down bartering not allowed on day-1"
        assert_fail_message = "Could not find any alert containing message to block chores due to chore_px higher " \
                              "than symbol_overview's limit_up_px"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_limits_with_negative_consumable_participation_qty(static_data_, clean_and_set_limits,
                                                                 leg1_leg2_symbol_list, pair_strat_,
                                                                 expected_strat_limits_,
                                                                 expected_strat_status_, symbol_overview_obj_list,
                                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                                 buy_chore_, sell_chore_,
                                                                 max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    activate_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{activate_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        px = 100
        qty = 90
        # positive test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        # placing new non-systematic new_chore
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        placed_new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                                  executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        # Negative Check
        executor_http_client.delete_all_last_barter_client()
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client, create_counts_per_side=1)

        check_str = ("blocked generated chore, not enough consumable_participation_qty available, "
                     "expected higher than chore qty = 90, found consumable_participation_qty = -30")
        assert_fail_message = "Could not find any alert containing message to block chores due to low " \
                              "consumable_participation_qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_strat.id,
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
def test_strat_limits_with_0_consumable_participation_qty(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                          pair_strat_, expected_strat_limits_,
                                                          expected_strat_status_, symbol_overview_obj_list,
                                                          last_barter_fixture_list, market_depth_basemodel_list,
                                                          buy_chore_, sell_chore_,
                                                          max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # Creating Strat
    activate_pair_strat, executor_http_client = (
        create_n_activate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                copy.deepcopy(expected_strat_limits_),
                                copy.deepcopy(expected_strat_status_), symbol_overview_obj_list, 
                                market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{activate_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
        px = 100
        qty = 90
        check_str = "Received unusable consumable_participation_qty"
        assert_fail_message = "Could not find any alert containing message to block chores due to 0 " \
                              "consumable_participation_qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_strat.id, executor_http_client)

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive Check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
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
def test_strat_limits_with_positive_low_consumable_participation_qty(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # Creating Strat
    activate_pair_strat, executor_http_client = (
        create_n_activate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                copy.deepcopy(expected_strat_limits_),
                                copy.deepcopy(expected_strat_status_), symbol_overview_obj_list, 
                                market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{activate_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client, create_counts_per_side=1)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = ("blocked generated chore, not enough consumable_participation_qty available, "
                     "expected higher than chore qty = 90, found consumable_participation_qty = 60")
        assert_fail_message = "Could not find any alert containing message to block chores due to low " \
                              "consumable_participation_qty"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_strat.id, executor_http_client)

        # Positive Check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

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
def test_strat_done_after_exhausted_buy_consumable_notional(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_chore_limits_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # setting strat_limits for this test
    expected_strat_limits_.max_single_leg_notional = 18000
    expected_strat_limits_.min_chore_notional = 15000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list, refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_strat_done_after_exhausted_sell_consumable_notional(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_chore_limits_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # setting strat_limits for this test
    expected_strat_limits_.max_single_leg_notional = 21000
    expected_strat_limits_.min_chore_notional = 15000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list, refresh_sec_update_fixture, Side.SELL,
        leg_1_side=Side.SELL, leg_2_side=Side.BUY)


@pytest.mark.nightly
def test_strat_limits_consumable_open_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                               pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list,
                                               buy_chore_, sell_chore_,
                                               max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open chore residual

        # Negative check
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_bartering_brief.consumable_open_notional = 5000
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_buy_side_bartering_brief.consumable_open_notional == 5000, \
            ("Updated strat_brief.pair_buy_side_bartering_brief.consumable_open_notional to 5000 "
             "using http route call but received unexpected returned value {updated_strat_brief}")

        # placing new non-systematic new_chore
        px = 1000
        qty = 90
        check_str = (f"blocked symbol_side_key: %%symbol-side={buy_symbol}-{Side.BUY.value}%% chore, "
                     "breaches available consumable open notional")
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)

        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_sell_side_bartering_brief.consumable_open_notional = 5000
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_sell_side_bartering_brief.consumable_open_notional == 5000, \
            ("Updated strat_brief.pair_sell_side_bartering_brief.consumable_open_notional to 5000 "
             "using http route call but received unexpected returned value {updated_strat_brief}")

        # placing new non-systematic new_chore
        px = 7000
        qty = 90
        check_str = (f"blocked symbol_side_key: %%symbol-side={sell_symbol}-{Side.SELL.value}%% chore, "
                     "breaches available consumable open notional")
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_limits_consumable_nett_filled_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                      pair_strat_, expected_strat_limits_,
                                                      expected_strat_status_, symbol_overview_obj_list,
                                                      last_barter_fixture_list, market_depth_basemodel_list,
                                                      buy_chore_, sell_chore_,
                                                      max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        # Positive check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        # Internally checks if chore_journal is found with OE_NEW state
        placed_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative check
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.consumable_nett_filled_notional = 5000
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.consumable_nett_filled_notional == 5000, \
            ("Updated strat_brief.pair_buy_side_bartering_brief.consumable_open_notional to 5000 "
             "using http route call but received unexpected returned value {updated_strat_brief}")

        # placing new non-systematic new_chore
        px = 1000
        qty = 90
        check_str = "blocked generated chore, not enough consumable_nett_filled_notional available"
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_chore_id=placed_chore_journal.chore.chore_id)

        # placing new non-systematic new_chore
        px = 7000
        qty = 90
        check_str = "blocked generated chore, not enough consumable_nett_filled_notional available"
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_chore_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def handle_place_both_side_chores_for_portfolio_limits_test(buy_symbol: str, sell_symbol: str,
                                                            pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list,
                                                            last_barter_fixture_list, market_depth_basemodel_list,
                                                            refresh_sec,
                                                            expect_no_chore=False):
    # making conditions suitable for this test
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 1000
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_http_client = (
        move_snoozed_pair_strat_to_ready_n_then_active(pair_strat_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_strat_limits_,
                                                       expected_strat_status_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
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
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
            px = 100
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

            new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                               buy_symbol, executor_http_client,
                                                                               expect_no_chore=expect_no_chore,
                                                                               last_chore_id=last_buy_chore_id)
            last_buy_chore_id = new_chore_journal.chore.chore_id

        # Placing sell chores
        last_sell_chore_id = None
        if executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
            for loop_count in range(total_chore_count_for_each_side):
                run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
                px = 110
                qty = 70
                place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client)

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


@pytest.mark.nightly
def handle_place_single_side_chores_for_portfolio_limits_test(leg_1_symbol: str, leg_2_symbol: str,
                                                              pair_strat_,
                                                              expected_strat_limits_, expected_strat_status_,
                                                              symbol_overview_obj_list,
                                                              last_barter_fixture_list, market_depth_basemodel_list,
                                                              refresh_sec, chore_side: Side,
                                                              leg1_side=Side.BUY, leg2_side=Side.SELL):
    # making conditions suitable for this test
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 1000
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_http_client = (
        move_snoozed_pair_strat_to_ready_n_then_active(pair_strat_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_strat_limits_,
                                                       expected_strat_status_))
    if created_pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
        buy_symbol = leg_1_symbol
        sell_symbol = leg_2_symbol
    else:
        buy_symbol = leg_2_symbol
        sell_symbol = leg_1_symbol

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
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
                run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
                px = 100
                qty = 90
                place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

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
                run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
                px = 110
                qty = 70
                place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client)

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


def _strat_pause_on_chore_fulfill_post_dod(buy_symbol, sell_symbol, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec, pause_fulfill_post_chore_dod):

    # making conditions suitable for this test
    residual_wait_sec = refresh_sec * 4
    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
            get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))

        symbol = buy_symbol
        print(f"Checking symbol: {symbol}")
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
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
        return active_pair_strat, executor_http_client
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_no_strat_pause_on_chore_fulfill_post_dod_if_config_is_false(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):

    # Keeping pause_fulfill_post_chore_dod config in executor
    # configs False - fulfill after dod must not trigger strat pause
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["pause_fulfill_post_chore_dod"] = False
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))
    try:
        buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]
        created_pair_strat, executor_http_client = (
            _strat_pause_on_chore_fulfill_post_dod(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                                   expected_strat_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   refresh_sec_update_fixture,
                                                   pause_fulfill_post_chore_dod=False))

        # check strat must not get paused
        pair_strat_obj = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat_obj.strat_state != StratState.StratState_PAUSED, \
            "Strat must not be PAUSED since 'pause_fulfill_post_chore_dod' is set False but found PAUSED"

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


@pytest.mark.nightly
def test_strat_pause_on_chore_fulfill_post_dod_if_config_is_true(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):

    # Keeping pause_fulfill_post_chore_dod config in executor configs True - fulfill after dod must trigger strat pause
    executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
    executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)
    executor_config_dict_str = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path,
                                                                                 load_as_str=True)
    executor_config_dict["pause_fulfill_post_chore_dod"] = True
    YAMLConfigurationManager.update_yaml_configurations(executor_config_dict, str(executor_config_file_path))
    try:
        buy_symbol, sell_symbol = leg1_leg2_symbol_list[0][0], leg1_leg2_symbol_list[0][1]
        created_pair_strat, executor_http_client = (
            _strat_pause_on_chore_fulfill_post_dod(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                                   expected_strat_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   refresh_sec_update_fixture,
                                                   pause_fulfill_post_chore_dod=True))
        # check strat must not get paused
        pair_strat_obj = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat_obj.strat_state == StratState.StratState_PAUSED, \
            ("Strat must get PAUSED since 'pause_fulfill_post_chore_dod' is set True but not found PAUSED, "
             f"found state: {pair_strat_obj.strat_state}")

        check_str = "Unexpected: Received fill that makes chore_snapshot OE_FILLED which is already of state OE_DOD"
        assert_fail_message = f"Can't find any alert with string '{check_str}'"

        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(created_pair_strat.id, check_str, assert_fail_message)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(executor_config_dict_str, str(executor_config_file_path))


# portfolio limits
@pytest.mark.nightly
def test_max_open_baskets(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                          expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                          last_barter_fixture_list, market_depth_basemodel_list,
                          buy_chore_, sell_chore_,
                          max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # > INFO:
    # Test sets max_open_baskets = 7,
    # - if multi open chores are allowed:
    # first triggers 2 street_books and places 2 chores each side from each executor,
    # these 8 chores must pass for positive check and 8th chore must breach max_open_baskets limits
    # and must trigger all-strat pause, then one more BUY chore is placed in
    # any one executor, so it must not be placed since strats are paused + alert must be created in portfolio_alerts
    # - if multi open chores are not allowed:
    # first triggers 8 street_books and places 1 chore BUY side from each executor,
    # these 8 chores must pass for positive check and 8th chore must breach max_open_baskets limits
    # and must trigger all-strat pause, then one more strat is created and BUY chore is placed,
    # so it must not be placed since strats are paused + alert must be created in portfolio_alerts

    # Updating portfolio limits
    expected_portfolio_limits_.max_open_baskets = 7
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:8]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

    # starting strats one by one
    pair_strat_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_chores_for_portfolio_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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

    # checking portfolio_status open_chores
    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert portfolio_status.open_chores == 8, \
        f"Mismatched portfolio_status.open_chores, expected: 8, received: {portfolio_status.open_chores=}"

    # Till this point since max_open_buckets limits must have breached and any new chore must not be placed,
    # checking that now...

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    created_pair_strat = create_strat(buy_symbol, sell_symbol, pair_strat_)
    handle_place_both_side_chores_for_portfolio_limits_test(
        buy_symbol, sell_symbol, created_pair_strat, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list, 
        refresh_sec_update_fixture, expect_no_chore=True)

    # checking portfolio_status open_chores
    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert portfolio_status.open_chores == 8, \
        f"Mismatched portfolio_status.open_chores, expected: 8, received: {portfolio_status.open_chores=}"

    time.sleep(5)
    # checking if all strat pause warning is in last started strat
    check_str = "Putting Activated Strat to PAUSE, found portfolio_limits breached already"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    check_alert_str_in_strat_alerts_n_portfolio_alerts(created_pair_strat.id, check_str, assert_fail_message)

    # Checking alert in portfolio_alert
    check_str = "max_open_baskets breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    check_alert_str_in_portfolio_alert(check_str, assert_fail_message)

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = email_book_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def test_max_open_notional_per_side_for_buy(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                            expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                            last_barter_fixture_list, market_depth_basemodel_list,
                                            buy_chore_, sell_chore_,
                                            max_loop_count_per_side, expected_portfolio_limits_,
                                            refresh_sec_update_fixture):
    # INFO:
    # Test sets max_open_notional_per_side = 71_999,

    # - if multi open chores are allowed:
    # triggers 2 street_books and places 2 chores BUY side from each executor
    # - if multi open chores are not allowed:
    # creates 4 strats and places each Buy Chore from each executor

    # these 4 must pass for positive check and fourth chore must breach limit and as a result
    # all-strat pause also should get triggered + alert must be created in portfolio_alerts

    # Updating portfolio limits
    expected_portfolio_limits_.max_open_notional_per_side = 71_999
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:4]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

    # starting strats one by one
    pair_strat_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)
    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_single_side_chores_for_portfolio_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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

    # Checking alert in portfolio_alert
    check_str = "max_open_notional_per_side breached for BUY side"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, assert_fail_message)

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = email_book_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            (f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, "
             f"pair_strat: {pair_strat}")


@pytest.mark.nightly
def test_max_open_notional_per_side_for_sell(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                             expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                             last_barter_fixture_list, market_depth_basemodel_list,
                                             buy_chore_, sell_chore_,
                                             max_loop_count_per_side, expected_portfolio_limits_,
                                             refresh_sec_update_fixture):
    # INFO:
    # Test sets max_open_notional_per_side = 61_599,

    # - if multi open chores are allowed:
    # triggers 2 street_books and places 2 chores SELL side from each executor
    # - if multi open chores are not allowed:
    # creates 4 strats and places each SELL Chore from each executor

    # these 4 must pass for positive check and fourth chore must breach limit and as a result
    # all-strat pause also should get triggered + alert must be created in portfolio_alerts

    # Updating portfolio limits
    expected_portfolio_limits_.max_open_notional_per_side = 61_599
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:4]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

    # starting strats one by one
    pair_strat_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_place_single_side_chores_for_portfolio_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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

    # Checking alert in portfolio_alert
    check_str = "max_open_notional_per_side breached for SELL side"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, assert_fail_message)

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = email_book_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def test_all_strat_pause_for_max_gross_n_open_notional_breach(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_,
        max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # INFO:
    # Test sets max_gross_n_open_notional = 134_000

    # - if multi open chores are allowed:
    # triggers 2 street_books and places 2 chores each side from each executor
    # - if multi open chores are not allowed:
    # triggers 8 street_books out of which 4 places BUY chores each and rest 4 places SELL chores each

    # these 8 chores must pass for positive check, then one more BUY chore is placed in
    # any executor and this new chore journal must trigger all strat-pause + alert must be created in strat_alert

    # Updating portfolio limits
    expected_portfolio_limits_.max_gross_n_open_notional = 130_000
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]

        # starting strats one by one
        pair_strat_list = []
        for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
            stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
            pair_strat_list.append(stored_pair_strat_basemodel)
            time.sleep(2)

        executor_http_clients_n_last_chore_id_tuple_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
            results = [executor.submit(handle_place_both_side_chores_for_portfolio_limits_test,
                                       buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                       deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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
        # starting strats one by one
        pair_strat_list = []
        for buy_symbol, sell_symbol in sliced_buy_symbol_list:
            stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
            pair_strat_list.append(stored_pair_strat_basemodel)
            time.sleep(2)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_symbol_list)) as executor:
            results = [
                executor.submit(handle_place_single_side_chores_for_portfolio_limits_test,
                                buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
                                deepcopy(symbol_overview_obj_list),
                                deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                refresh_sec_update_fixture, Side.BUY,
                                leg1_side=Side.BUY, leg2_side=Side.SELL)
                for idx, buy_sell_symbol in enumerate(sliced_buy_symbol_list)]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

        sliced_sell_symbol_list = leg1_leg2_symbol_list[4:8]
        # starting strats one by one
        pair_strat_list = []
        for buy_symbol, sell_symbol in sliced_sell_symbol_list:
            stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
            pair_strat_list.append(stored_pair_strat_basemodel)
            time.sleep(2)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_sell_symbol_list)) as executor:
            results = [
                executor.submit(handle_place_single_side_chores_for_portfolio_limits_test,
                                buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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
    limit_breaching_pair_strat = create_strat(buy_symbol, sell_symbol, pair_strat_)
    handle_place_both_side_chores_for_portfolio_limits_test(
        buy_symbol, sell_symbol, limit_breaching_pair_strat, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list, 
        refresh_sec_update_fixture, expect_no_chore=True)

    # Checking alert in portfolio_alert
    check_str = "max_gross_n_open_notional breached,"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, assert_fail_message)

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = email_book_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


def all_strat_pause_test_for_max_reject_limit_breach(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec):
    # explicitly setting waived_min_chores to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_chores = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_http_client = (
        move_snoozed_pair_strat_to_ready_n_then_active(pair_strat_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_strat_limits_,
                                                       expected_start_status_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

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
            handle_rej_chore_test(buy_symbol, sell_symbol, expected_strat_limits_,
                                  last_barter_fixture_list, max_loop_count_per_side,
                                  False, executor_http_client, config_dict, residual_wait_sec))
        return executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id
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
def test_last_n_sec_chore_counts(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                 expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                 last_barter_fixture_list, market_depth_basemodel_list,
                                 buy_chore_, sell_chore_,
                                 max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds = 10000
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
        leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    else:
        leg1_leg2_symbol_list = leg1_leg2_symbol_list[:8]
    executor_http_clients_n_last_chore_id_tuple_list = []

    # starting strats one by one
    pair_strat_list = []
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_chores_for_portfolio_limits_test,
                                   leg1_leg2_symbol[0], leg1_leg2_symbol[1], pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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
            expected_portfolio_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds,
            [ChoreEventType.OE_NEW]))

    assert len(chore_count_updated_chore_journals) == 1, \
        ("Unexpected: Length of returned list by get_last_n_sec_chores_by_events_query_client must be 1, "
         f"received: {len(chore_count_updated_chore_journals)}, received list: {chore_count_updated_chore_journals}")

    assert 8 == chore_count_updated_chore_journals[0].current_period_chore_count, \
        (f"Mismatch: Expected last_n_sec new chore_counts: 8, received: "
         f"{chore_count_updated_chore_journals[0].current_period_chore_count}")

    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds = 2
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)
    time.sleep(3)   # wait to check after 2 sec to check no chore is found after it

    chore_count_updated_chore_journals = (
        post_book_service_http_client.get_last_n_sec_chores_by_events_query_client(
            expected_portfolio_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds,
            [ChoreEventType.OE_NEW]))

    assert len(chore_count_updated_chore_journals) == 0, \
        ("Unexpected: Length of returned list by get_last_n_sec_chores_by_events_query_client must be 1, "
         f"received: {len(chore_count_updated_chore_journals)}, received list: {chore_count_updated_chore_journals}")


@pytest.mark.nightly
def test_portfolio_limits_rolling_new_chore_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                   pair_strat_, expected_strat_limits_,
                                                   expected_strat_status_, symbol_overview_obj_list,
                                                   last_barter_fixture_list, market_depth_basemodel_list,
                                                   buy_chore_, sell_chore_,
                                                   max_loop_count_per_side,
                                                   expected_portfolio_limits_, refresh_sec_update_fixture):
    # INFO:
    # Test has rolling_max_chore_count.max_rolling_tx_count = 7 and
    # rolling_max_chore_count.rolling_tx_count_period_seconds = 10000 that means within 10000 secs 8th new chore
    # will trigger all strat-pause.

    # - if multi open chores are allowed:
    # Test will create 2 strats and will place 2 chore each side
    # - if multi open chores are not allowed:
    # Test will create 8 strats and will place BUY chore from each executor

    # 8th new chore must breach limit and trigger all strat-pause and any new chore must get ignored since strats
    # got paused + alert must be present in portfolio alerts

    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_chore_count.max_rolling_tx_count = 7
    expected_portfolio_limits_.rolling_max_chore_count.rolling_tx_count_period_seconds = 10000
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:8]

    # starting strats one by one
    pair_strat_list = []
    for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list:
        stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)
    executor_http_clients_n_last_chore_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_chores_for_portfolio_limits_test,
                                   buy_sell_symbol[0], buy_sell_symbol[1], pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
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
    stored_pair_strat_basemodel = create_strat(buy_symbol, sell_symbol, pair_strat_)
    handle_place_both_side_chores_for_portfolio_limits_test(
        buy_symbol, sell_symbol, stored_pair_strat_basemodel, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list, 
        refresh_sec_update_fixture, expect_no_chore=True)

    # Checking alert in portfolio_alert
    check_str = "max_allowed_chores_within_period breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, assert_fail_message)

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = email_book_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def test_all_strat_pause_for_max_reject_limit_breach(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # INFO:
    # Test has rolling_max_reject_count.max_rolling_tx_count = 4 and
    # rolling_max_reject_count.rolling_tx_count_period_seconds = 10000 that means within 10000 secs 5th rej
    # will trigger all strat-pause. Test will create 2 strats and will place 2 chore each to equal threshold of
    # 4 rej chores after which one more chore will also be trigger by either of strat and that must trigger
    # all strat-pause + alert must be present in portfolio alerts

    # Settings portfolio_limits for this test
    expected_portfolio_limits_.rolling_max_reject_count.max_rolling_tx_count = 4
    expected_portfolio_limits_.rolling_max_reject_count.rolling_tx_count_period_seconds = 10000
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    # updating fixture values for this test-case
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    executor_http_clients_n_last_chore_id_tuple_list = []

    # starting strats one by one
    pair_strat_list = []
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(all_strat_pause_test_for_max_reject_limit_breach,
                                   leg1_leg2_symbol[0], leg1_leg2_symbol[1], pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id = future.result()
            executor_http_clients_n_last_chore_id_tuple_list.append(
                (executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id))

    time.sleep(2)
    # Placing on more rej chore that must trigger auto-kill_switch
    # (Placed chore will be rej type by simulator because of continues_special_chore_count)
    executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id = (
        executor_http_clients_n_last_chore_id_tuple_list)[0]

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_bid_buy_n_ask_sell_last_barter(executor_http_client, buy_symbol, sell_symbol))
    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)

    latest_chore_journal = get_latest_chore_journal_with_events_and_symbol(
        [ChoreEventType.OE_BRK_REJ, ChoreEventType.OE_EXH_REJ], buy_symbol,
        executor_http_client, last_chore_id=last_buy_rej_id)

    # Checking alert in portfolio_alert
    check_str: str = "max_allowed_rejection_within_period breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, assert_fail_message)

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = email_book_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"

# TODO: Add test for missing strat_limits
# > limit_up_down_volume_participation_rate
