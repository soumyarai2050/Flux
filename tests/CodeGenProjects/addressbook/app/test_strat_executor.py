# standard imports
import traceback
import concurrent.futures

import pytest

# project imports
from tests.CodeGenProjects.addressbook.app.utility_test_functions import *
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager


PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
test_config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"


# limit breach order blocks test-cases
@pytest.mark.nightly
def test_min_order_notional_breach_in_normal_strat_mode(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list,
        last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_,
        max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative check
        # placing new non-systematic new_order
        px = 1
        qty = 1
        check_str = "blocked order_opportunity < min_order_notional limit"
        assert_fail_msg = "Could not find any alert containing message to block orders due to less " \
                          "than limit order_notional"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_min_order_notional_breach_in_relaxed_strat_mode(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list,
        last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_,
        max_loop_count_per_side, expected_order_limits_, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_, StratMode.StratMode_Relaxed))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative check
        # placing new non-systematic new_order
        px = 1
        qty = 1
        check_str = "blocked order_opportunity < min_order_notional_relaxed limit"
        assert_fail_msg = "Could not find any alert containing message to block orders due to less " \
                          "than limit order_notional"
        limit_alert = handle_place_order_and_check_str_in_alert_for_executor_limits(
            buy_symbol, Side.BUY, px, qty, check_str, assert_fail_msg, active_pair_strat.id, executor_http_client,
            last_order_id=placed_order_journal.order.order_id)

        # Using regex to extract the value after the '<' symbol
        value_pattern = re.compile(r'<\s*(\d+(?:\.\d+)?)')

        match = value_pattern.search(limit_alert.alert_brief)

        if match:
            extracted_value = match.group(1)
            assert extracted_value != expected_order_limits_.min_order_notional, \
                ("When strat_mode is relaxed, min_order_notional is replaced by random value between "
                 "min_order_notional and min_order_notional+min_order_notional_allowance but found value same as"
                 f"expected_order_limits_.min_order_notional, "
                 f"expected_order_limits_.min_order_notional: {expected_order_limits_.min_order_notional}, "
                 f"expected_order_limits_.min_order_notional_allowance: "
                 f"{expected_order_limits_.min_order_notional_allowance}, "
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
def test_max_order_notional_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                   pair_strat_, expected_strat_limits_,
                                   expected_start_status_, symbol_overview_obj_list,
                                   last_trade_fixture_list, market_depth_basemodel_list,
                                   top_of_book_list_, buy_order_, sell_order_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))
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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_order
        px = 1000
        qty = 100
        check_str = "blocked generated order, breaches max_order_notional limit, expected less than"
        assert_fail_msg = "Could not find any alert containing message to block orders due to more " \
                          "than limit order_notional"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_max_order_qty_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                              pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, buy_order_, sell_order_,
                              max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_order
        px = 10
        qty = 600
        check_str = "blocked generated order, breaches max_order_qty limit, expected less than"
        assert_fail_msg = "Could not find any alert containing message to block orders due to excessive order qty"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
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
                                            expected_start_status_, symbol_overview_obj_list,
                                            last_trade_fixture_list, market_depth_basemodel_list,
                                            top_of_book_list_, buy_order_, sell_order_,
                                            max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        tob_list = executor_http_client.get_all_top_of_book_client()

        buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
        sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

        # checking last_trade as None in buy order
        buy_tob.last_trade = None
        update_date_time = DateTime.utcnow()
        buy_tob.bid_quote.last_update_date_time = update_date_time
        buy_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(buy_tob.dict(), by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = f"blocked generated order, symbol: {buy_symbol}, side: {Side.BUY} as " \
                    f"top_of_book.last_trade.px is none or 0"
        assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        # checking last_trade px 0 in sell order
        sell_tob.last_trade.px = 0
        update_date_time = DateTime.utcnow()
        sell_tob.ask_quote.last_update_date_time = update_date_time
        sell_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(sell_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = f"blocked generated order, symbol: {sell_symbol}, side: {Side.SELL} as " \
                    f"top_of_book.last_trade.px is none or 0"
        assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
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
def test_breach_threshold_px_with_unsupported_side(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                   pair_strat_, expected_strat_limits_,
                                                   expected_start_status_, symbol_overview_obj_list,
                                                   last_trade_fixture_list, market_depth_basemodel_list,
                                                   top_of_book_list_, buy_order_, sell_order_,
                                                   max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))
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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated unsupported side order"
        assert_fail_msg = "Could not find any alert containing message to block orders due to unsupported side"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.SIDE_UNSPECIFIED, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

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
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_, buy_order_, sell_order_,
                                             max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        market_depth_list = executor_http_client.get_all_market_depth_client()
        for market_depth in market_depth_list:
            if market_depth.symbol == buy_symbol:
                market_depth.px = 0
                executor_http_client.put_market_depth_client(jsonable_encoder(market_depth,
                                                                              by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = f"blocked generated order, symbol: {buy_symbol}, side: {Side.BUY}, " \
                    f"unable to find valid px based on max_px_levels"
        assert_fail_msg = "Could not find any alert containing message to block orders due to 0 market depth px"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

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
                                                        expected_start_status_, symbol_overview_obj_list,
                                                        last_trade_fixture_list, market_depth_basemodel_list,
                                                        top_of_book_list_, buy_order_, sell_order_,
                                                        max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open order residual

        # Negative Check
        tob_list = executor_http_client.get_all_top_of_book_client()

        buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
        sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

        # checking last_trade as None in buy order
        buy_tob.ask_quote = None
        update_date_time = DateTime.utcnow()
        buy_tob.bid_quote.last_update_date_time = update_date_time
        buy_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(buy_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = f"blocked generated BUY order, symbol: {buy_symbol}, side: {Side.BUY} as aggressive_quote" \
                    f" is not found or has no px"
        assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

        # checking last_trade px 0 in sell order
        sell_tob.bid_quote = None
        update_date_time = DateTime.utcnow()
        sell_tob.ask_quote.last_update_date_time = update_date_time
        sell_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(sell_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = f"blocked generated SELL order, symbol: {sell_symbol}, side: {Side.SELL} as aggressive_quote" \
                    f" is found None"
        assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_msg,
                                                                      active_pair_strat.id, executor_http_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# FIXME: currently failing since executor not even starts without any tob
def _test_px_check_if_tob_none(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                               pair_strat_, expected_strat_limits_,
                               expected_start_status_, symbol_overview_obj_list,
                               last_trade_fixture_list, market_depth_basemodel_list,
                               top_of_book_list_, buy_order_, sell_order_,
                               max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # explicitly setting waived_min_orders to 10 for this test case
    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
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
        executor_http_client.trade_simulator_reload_config_query_client()

        # buy test
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)

        # Deleting all tobs
        tob_list = executor_http_client.get_all_top_of_book_client()
        for tob in tob_list:
            executor_http_client.delete_top_of_book_client(tob.id, return_obj_copy=False)

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated order, unable to conduct px checks: top_of_book is sent None for strat"
        assert_fail_message = "Could not find any alert containing message to block orders due to no tob"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
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
def test_breach_threshold_px_for_max_basis_points(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                  pair_strat_, expected_strat_limits_,
                                                  expected_start_status_, symbol_overview_obj_list,
                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                  top_of_book_list_, buy_order_, sell_order_,
                                                  max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        tob_list = executor_http_client.get_all_top_of_book_client()

        buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
        sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

        buy_tob.ask_quote.px = 10
        update_date_time = DateTime.utcnow()
        buy_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(buy_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated BUY order, order px: .* > allowed max_px"
        assert_fail_message = "Could not find any alert containing message to block orders wrong max basis points"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        sell_tob.bid_quote.px = 100
        update_date_time = DateTime.utcnow()
        sell_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(sell_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 70
        qty = 90
        check_str = "blocked generated SELL order, order px: .* < allowed min_px"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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


# FIXME: not implemented: supposed to fail
# order limits
def test_max_contract_qty(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                          buy_order_, sell_order_, buy_fill_journal_,
                          sell_fill_journal_, expected_buy_order_snapshot_,
                          expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
                          pair_strat_, expected_strat_limits_, expected_start_status_,
                          expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                          last_trade_fixture_list, symbol_overview_obj_list,
                          market_depth_basemodel_list, expected_order_limits_,
                          expected_portfolio_limits_, max_loop_count_per_side,
                          leg1_leg2_symbol_list, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        # Updating order_limits for Negative check
        expected_order_limits_.max_contract_qty = 80
        updated_order_limits = OrderLimitsBaseModel(id=1, max_contract_qty=80)
        updated_order_limits = strat_manager_service_native_web_client.patch_order_limits_client(
            jsonable_encoder(updated_order_limits, by_alias=True, exclude_none=True))
        assert updated_order_limits == expected_order_limits_

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "qty: .* > max contract qty"
        assert_fail_message = "Could not find any alert containing message to block orders " \
                              "due to contract qty breach"
        # placing new non-systematic new_order
        place_new_order(buy_symbol, Side.BUY, px, qty, executor_http_client)
        print(f"symbol: {buy_symbol}, Created new_order obj")

        new_order_journal = get_latest_order_journal_with_event_and_symbol(
            OrderEventType.OE_NEW, buy_symbol, executor_http_client, expect_no_order=True,
            last_order_id=placed_order_journal.order.order_id)

        time.sleep(2)
        strat_alert = log_analyzer_web_client.get_strat_alert_client(active_pair_strat.id)
        for alert in strat_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            # Checking alert in portfolio_alert if reason failed to add in strat_alert
            portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
            for alert in portfolio_alert.alerts:
                if re.search(check_str, alert.alert_brief):
                    break
            else:
                assert False, assert_fail_message
        assert True
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)


@pytest.mark.nightly
def test_breach_threshold_px_for_max_px_by_deviation(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                     pair_strat_, expected_strat_limits_,
                                                     expected_start_status_, symbol_overview_obj_list,
                                                     last_trade_fixture_list, market_depth_basemodel_list,
                                                     top_of_book_list_, buy_order_, sell_order_,
                                                     max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        tob_list = executor_http_client.get_all_top_of_book_client()

        buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
        sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

        buy_tob.last_trade.px = 10
        update_date_time = DateTime.utcnow()
        buy_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(buy_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated BUY order, order px: .* > allowed max_px"
        assert_fail_message = "Could not find any alert containing message to block orders tob last trade px as 0"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

        sell_tob.last_trade.px = 100
        update_date_time = DateTime.utcnow()
        sell_tob.last_update_date_time = update_date_time
        executor_http_client.put_top_of_book_client(jsonable_encoder(sell_tob, by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 70
        qty = 90
        check_str = "blocked generated SELL order, order px: .* < allowed min_px"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
def test_breach_threshold_px_for_px_by_max_depth(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                 pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_, buy_order_, sell_order_,
                                                 max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open order residual

        # Negative Check
        market_depth_list = executor_http_client.get_all_market_depth_client()
        for market_depth in market_depth_list:
            if market_depth.symbol == buy_symbol:
                market_depth.px = 10
                executor_http_client.put_market_depth_client(jsonable_encoder(market_depth,
                                                                              by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 100
        qty = 90

        check_str = "blocked generated BUY order, order px: .* > allowed max_px"
        assert_fail_message = "Could not find any alert containing message to block orders due to less px of depth"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        for market_depth in market_depth_list:
            if market_depth.symbol == sell_symbol:
                market_depth.px = 100
                executor_http_client.put_market_depth_client(jsonable_encoder(market_depth,
                                                                              by_alias=True, exclude_none=True))

        # placing new non-systematic new_order
        px = 70
        qty = 90
        check_str = "blocked generated SELL order, order px: .* < allowed min_px"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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


# @@@ deprecated: no strat_executor can be set to ready without symbol_overview
# def test_strat_limits_with_none_symbol_overview(static_data_, clean_and_set_limits, buy_sell_symbol_list,
#                                                 pair_strat_, expected_strat_limits_,
#                                                 expected_start_status_, symbol_overview_obj_list,
#                                                 last_trade_fixture_list, market_depth_basemodel_list,
#                                                 top_of_book_list_, buy_order_, sell_order_,
#                                                 max_loop_count_per_side, residual_wait_sec):
#     # Creating Strat
#     active_pair_strat = create_n_activate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
#                                                 copy.deepcopy(expected_strat_limits_),
#                                                 copy.deepcopy(expected_start_status_))
#
#     # running Last Trade
#     run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
#
#     # creating market_depth
#     create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)
#
#     # Adding strat in strat_collection
#     create_if_not_exists_and_validate_strat_collection(active_pair_strat)
#
#     # buy test
#     run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
#     loop_count = 1
#     run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)
#
#     # placing new non-systematic new_buy_order
#     px = 100
#     qty = 90
#     check_str = "blocked generated BUY order, symbol_overview_tuple missing for symbol"
#     assert_fail_message = "Could not find any alert containing message to block orders due to no symbol_overview"
#     handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
#                                                                   check_str, assert_fail_message)
#     # placing new non-systematic new_sell_order
#     px = 110
#     qty = 70
#     check_str = "blocked generated SELL order, symbol_overview_tuple missing for symbol"
#     assert_fail_message = "Could not find any alert containing message to block orders due to no symbol_overview"
#     handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
#                                                                   check_str, assert_fail_message)


@pytest.mark.nightly
def test_strat_limits_with_0_consumable_open_orders(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                    pair_strat_, expected_strat_limits_,
                                                    expected_start_status_, symbol_overview_obj_list,
                                                    last_trade_fixture_list, market_depth_basemodel_list,
                                                    top_of_book_list_, buy_order_, sell_order_,
                                                    max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_trading_brief.consumable_open_orders = -1
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_buy_side_trading_brief.consumable_open_orders == -1, \
            "Updated strat_brief.pair_buy_side_trading_brief.consumable_open_orders to -1 using http route call but " \
            f"received unexpected returned value {updated_strat_brief}"

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated BUY order, not enough consumable_open_orders"
        assert_fail_message = "Could not find any alert containing message to block " \
                              "BUY order due to 0 consumable open orders"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_sell_side_trading_brief.consumable_open_orders = -1
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_sell_side_trading_brief.consumable_open_orders == -1

        # placing new non-systematic new_order
        px = 70
        qty = 90
        check_str = "blocked generated SELL order, not enough consumable_open_orders"
        assert_fail_message = "Could not find any alert containing message to block " \
                              "SELL order due to 0 consumable open orders"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
                                                    expected_start_status_, symbol_overview_obj_list,
                                                    last_trade_fixture_list, market_depth_basemodel_list,
                                                    top_of_book_list_, buy_order_, sell_order_,
                                                    max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, activated_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open order residual

        # Negative check
        # placing new non-systematic new_order
        px = 1000
        qty = 900
        check_str = "blocked generated BUY order, breaches available consumable notional"
        assert_fail_message = "Could not find any alert containing message to block orders " \
                              "due to high consumable notional"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activated_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        # placing new non-systematic new_order
        px = 7000
        qty = 900
        check_str = "blocked generated SELL order, breaches available consumable notional"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
                                                         expected_start_status_, symbol_overview_obj_list,
                                                         last_trade_fixture_list, market_depth_basemodel_list,
                                                         top_of_book_list_, buy_order_, sell_order_,
                                                         max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check

        # Checking alert when consumable_concentration < order_qty
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_trading_brief.consumable_concentration = 10
        strat_brief.pair_sell_side_trading_brief.consumable_concentration = 10
        updated_strat_brief = executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True,
                                                                                           exclude_none=True))
        assert (updated_strat_brief.pair_buy_side_trading_brief.consumable_concentration ==
                strat_brief.pair_buy_side_trading_brief.consumable_concentration), \
            "Mismatch pair_buy_side_trading_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_buy_side_trading_brief.consumable_concentration}"
        assert (updated_strat_brief.pair_sell_side_trading_brief.consumable_concentration ==
                strat_brief.pair_sell_side_trading_brief.consumable_concentration), \
            "Mismatch pair_sell_side_trading_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_sell_side_trading_brief.consumable_concentration}"

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated BUY order, not enough consumable_concentration:"
        assert_fail_message = "Could not find any alert containing message to block orders due to less " \
                              "consumable concentration"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        # placing new non-systematic new_order
        px = 70
        qty = 90
        check_str = "blocked generated SELL order, not enough consumable_concentration:"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client)

        # Checking alert when consumable_concentration == 0
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_trading_brief.consumable_concentration = 0
        strat_brief.pair_sell_side_trading_brief.consumable_concentration = 0
        updated_strat_brief = executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True,
                                                                                           exclude_none=True))
        assert (updated_strat_brief.pair_buy_side_trading_brief.consumable_concentration ==
                strat_brief.pair_buy_side_trading_brief.consumable_concentration), \
            "Mismatch pair_buy_side_trading_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_buy_side_trading_brief.consumable_concentration}"
        assert (updated_strat_brief.pair_sell_side_trading_brief.consumable_concentration ==
                strat_brief.pair_sell_side_trading_brief.consumable_concentration), \
            "Mismatch pair_sell_side_trading_brief.consumable_concentration: expected 0, received " \
            f"{updated_strat_brief.pair_sell_side_trading_brief.consumable_concentration}"

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated BUY order, unexpected: consumable_concentration found 0!"
        assert_fail_message = "Could not find any alert containing message to block orders due to less " \
                              "consumable concentration"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
        # placing new non-systematic new_order
        px = 70
        qty = 90
        check_str = "blocked generated SELL order, unexpected: consumable_concentration found 0!"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
                                                          expected_start_status_, symbol_overview_obj_list,
                                                          last_trade_fixture_list, market_depth_basemodel_list,
                                                          top_of_book_list_, buy_order_, sell_order_,
                                                          max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)

        # Negative Check
        # placing new non-systematic new_order
        px = 160
        qty = 90
        check_str = "blocked generated BUY order, limit up trading not allowed on day-1"
        assert_fail_message = "Could not find any alert containing message to block orders due to order_px higher " \
                              "than symbol_overview's limit_up_px"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

        # placing new non-systematic new_order
        px = 40
        qty = 90
        check_str = "blocked generated SELL order, limit down trading not allowed on day-1"
        assert_fail_message = "Could not find any alert containing message to block orders due to order_px higher " \
                              "than symbol_overview's limit_up_px"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
                                                                 expected_start_status_, symbol_overview_obj_list,
                                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                                 top_of_book_list_, buy_order_, sell_order_,
                                                                 max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    activate_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive Check
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0], avoid_order_trigger=True)

        # placing new non-systematic new_order
        px = 100
        qty = 90
        place_new_order(buy_symbol, Side.BUY, px, qty, executor_http_client)

        placed_new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW, buy_symbol,
                                                                                  executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open order residual

        # Negative Check
        # making last trade unavailable to next order call to make consumable_participation_qty negative
        executor_http_client.delete_all_last_trade_client()

        check_str = "blocked generated order, not enough consumable_participation_qty available"
        assert_fail_message = "Could not find any alert containing message to block orders due to low " \
                              "consumable_participation_qty"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_strat.id,
                                                                      executor_http_client,
                                                                      last_order_id=
                                                                      placed_new_order_journal.order.order_id)
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
                                                          expected_start_status_, symbol_overview_obj_list,
                                                          last_trade_fixture_list, market_depth_basemodel_list,
                                                          top_of_book_list_, buy_order_, sell_order_,
                                                          max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # Creating Strat
    activate_pair_strat, executor_http_client = (
        create_n_activate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                copy.deepcopy(expected_strat_limits_),
                                copy.deepcopy(expected_start_status_), symbol_overview_obj_list, top_of_book_list_,
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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Negative check
        # removing last_trade for negative check
        executor_http_client.delete_all_last_trade_client()

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "Received unusable consumable_participation_qty"
        assert_fail_message = "Could not find any alert containing message to block orders due to 0 " \
                              "consumable_participation_qty"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_strat.id, executor_http_client)

        # Positive Check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
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
def test_strat_limits_with_low_consumable_participation_qty(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                            pair_strat_, expected_strat_limits_,
                                                            expected_start_status_, symbol_overview_obj_list,
                                                            last_trade_fixture_list, market_depth_basemodel_list,
                                                            top_of_book_list_, buy_order_, sell_order_,
                                                            max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # Creating Strat
    activate_pair_strat, executor_http_client = (
        create_n_activate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                copy.deepcopy(expected_strat_limits_),
                                copy.deepcopy(expected_start_status_), symbol_overview_obj_list, top_of_book_list_,
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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive Check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open order residual

        # Negative check
        # removing last_trade for negative check
        executor_http_client.delete_all_last_trade_client()

        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client, create_counts_per_side=1)

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "blocked generated order, not enough consumable_participation_qty available"
        assert_fail_message = "Could not find any alert containing message to block orders due to low " \
                              "consumable_participation_qty"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      activate_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)
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
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, expected_order_limits_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # updating order_limits
    expected_order_limits_.min_order_notional = 15000
    expected_order_limits_.id = 1
    strat_manager_service_native_web_client.put_order_limits_client(expected_order_limits_, return_obj_copy=False)

    # setting strat_limits for this test
    expected_strat_limits_.max_single_leg_notional = 18000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
        market_depth_basemodel_list, top_of_book_list_, refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_strat_done_after_exhausted_sell_consumable_notional(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, expected_order_limits_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # updating order_limits
    expected_order_limits_.min_order_notional = 15000
    expected_order_limits_.id = 1
    strat_manager_service_native_web_client.put_order_limits_client(expected_order_limits_, return_obj_copy=False)

    # setting strat_limits for this test
    expected_strat_limits_.max_single_leg_notional = 18000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
        market_depth_basemodel_list, top_of_book_list_, refresh_sec_update_fixture, Side.SELL)


@pytest.mark.nightly
def test_strat_limits_consumable_open_notional(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                               pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list, market_depth_basemodel_list,
                                               top_of_book_list_, buy_order_, sell_order_,
                                               max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # wait to get open order residual

        # Negative check
        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_buy_side_trading_brief.consumable_open_notional = 5000
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_buy_side_trading_brief.consumable_open_notional == 5000, \
            ("Updated strat_brief.pair_buy_side_trading_brief.consumable_open_notional to 5000 "
             "using http route call but received unexpected returned value {updated_strat_brief}")

        # placing new non-systematic new_order
        px = 1000
        qty = 90
        check_str = (f"blocked symbol_side_key: symbol-side={buy_symbol}-{Side.BUY} order, "
                     "breaches available consumable open notional")
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

        strat_brief_list = executor_http_client.get_all_strat_brief_client()
        # since only one strat in current test
        assert len(strat_brief_list) == 1, "Unexpected length of strat_briefs, expected exactly one strat_brief " \
                                           f"as only one strat exists for this test, received " \
                                           f"{len(strat_brief_list)}, strat_brief_list: {strat_brief_list}"
        strat_brief = strat_brief_list[0]
        strat_brief.pair_sell_side_trading_brief.consumable_open_notional = 5000
        updated_strat_brief = \
            executor_http_client.put_strat_brief_client(jsonable_encoder(strat_brief, by_alias=True, exclude_none=True))
        assert updated_strat_brief.pair_sell_side_trading_brief.consumable_open_notional == 5000, \
            ("Updated strat_brief.pair_sell_side_trading_brief.consumable_open_notional to 5000 "
             "using http route call but received unexpected returned value {updated_strat_brief}")

        # placing new non-systematic new_order
        px = 7000
        qty = 90
        check_str = (f"blocked symbol_side_key: symbol-side={sell_symbol}-{Side.SELL} order, "
                     "breaches available consumable open notional")
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
                                                      expected_start_status_, symbol_overview_obj_list,
                                                      last_trade_fixture_list, market_depth_basemodel_list,
                                                      top_of_book_list_, buy_order_, sell_order_,
                                                      max_loop_count_per_side, refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        # Internally checks if order_journal is found with OE_NEW state
        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_http_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
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
            ("Updated strat_brief.pair_buy_side_trading_brief.consumable_open_notional to 5000 "
             "using http route call but received unexpected returned value {updated_strat_brief}")

        # placing new non-systematic new_order
        px = 1000
        qty = 90
        check_str = "blocked generated order, not enough consumable_nett_filled_notional available"
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                      check_str, assert_fail_message,
                                                                      active_pair_strat.id, executor_http_client,
                                                                      last_order_id=placed_order_journal.order.order_id)

        # placing new non-systematic new_order
        px = 7000
        qty = 90
        check_str = "blocked generated order, not enough consumable_nett_filled_notional available"
        assert_fail_message = f"Could not find any alert saying '{check_str}'"
        handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
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
def handle_place_both_side_orders_for_portfolio_limits_test(buy_symbol: str, sell_symbol: str,
                                                            pair_strat_,
                                                            expected_strat_limits_, expected_start_status_,
                                                            symbol_overview_obj_list,
                                                            last_trade_fixture_list, market_depth_basemodel_list,
                                                            top_of_book_list_, refresh_sec,
                                                            expect_no_order=False):
    # making conditions suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 1000
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        total_order_count_for_each_side = 1
    else:
        total_order_count_for_each_side = 2

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.trade_simulator_reload_config_query_client()

        # Placing buy orders
        last_buy_order_id = None
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

            new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                               buy_symbol, executor_http_client,
                                                                               expect_no_order=expect_no_order,
                                                                               last_order_id=last_buy_order_id)
            last_buy_order_id = new_order_journal.order.order_id

        # Placing sell orders
        last_sell_order_id = None
        if executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            for loop_count in range(total_order_count_for_each_side):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
                run_sell_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[1])

                new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                                   sell_symbol, executor_http_client,
                                                                                   expect_no_order=expect_no_order,
                                                                                   last_order_id=last_sell_order_id)
                last_sell_order_id = new_order_journal.order.order_id

        return executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def handle_place_single_side_orders_for_portfolio_limits_test(buy_symbol: str, sell_symbol: str,
                                                              pair_strat_,
                                                              expected_strat_limits_, expected_start_status_,
                                                              symbol_overview_obj_list,
                                                              last_trade_fixture_list, market_depth_basemodel_list,
                                                              top_of_book_list_, refresh_sec, order_side: Side):
    # making conditions suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 1000
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        total_order_count_for_each_side = 1
    else:
        total_order_count_for_each_side = 2

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.trade_simulator_reload_config_query_client()

        # Placing buy orders
        if order_side == Side.BUY:
            last_order_id = None
            for loop_count in range(total_order_count_for_each_side):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
                run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

                new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                                   buy_symbol, executor_http_client,
                                                                                   last_order_id=last_order_id)
                last_order_id = new_order_journal.order.order_id

                # Checking if fills found
                time.sleep(10)
                get_latest_fill_journal_from_order_id(last_order_id, executor_http_client)

        else:
            # Placing sell orders
            last_order_id = None
            for loop_count in range(total_order_count_for_each_side):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
                run_sell_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[1])

                new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                                   sell_symbol, executor_http_client,
                                                                                   last_order_id=last_order_id)
                last_order_id = new_order_journal.order.order_id
                time.sleep(10)
                get_latest_fill_journal_from_order_id(last_order_id, executor_http_client)

        if order_side == Side.BUY:
            return executor_http_client, buy_symbol, sell_symbol, last_order_id
        else:
            return executor_http_client, buy_symbol, sell_symbol, last_order_id

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# portfolio limits
@pytest.mark.nightly
def test_max_open_baskets(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                          expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
                          last_trade_fixture_list, market_depth_basemodel_list,
                          top_of_book_list_, buy_order_, sell_order_,
                          max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # > INFO:
    # Test sets max_open_baskets = 7,
    # - if multi open orders are allowed:
    # first triggers 2 strat_executors and places 2 orders each side from each executor,
    # these 8 orders must pass for positive check and 8th order must breach max_open_baskets limits
    # and must trigger all-strat pause, then one more BUY order is placed in
    # any one executor, so it must not be placed since strats are paused + alert must be created in portfolio_alerts
    # - if multi open orders are not allowed:
    # first triggers 8 strat_executors and places 1 order BUY side from each executor,
    # these 8 orders must pass for positive check and 8th order must breach max_open_baskets limits
    # and must trigger all-strat pause, then one more strat is created and BUY order is placed,
    # so it must not be placed since strats are paused + alert must be created in portfolio_alerts

    # Updating portfolio limits
    expected_portfolio_limits_.max_open_baskets = 7
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:8]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
    executor_http_clients_n_last_order_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   deepcopy(top_of_book_list_), refresh_sec_update_fixture, False)
                   for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id = future.result()
            executor_http_clients_n_last_order_id_tuple_list.append(
                (executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id))

    # Till this point since max_open_buckets limits must have breached and any new order must not be placed,
    # checking that now...

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    handle_place_both_side_orders_for_portfolio_limits_test(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, expect_no_order=True)

    # Checking alert in portfolio_alert
    check_str = "max_open_baskets breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"

    portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def test_max_open_notional_per_side_for_buy(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                            expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
                                            last_trade_fixture_list, market_depth_basemodel_list,
                                            top_of_book_list_, buy_order_, sell_order_,
                                            max_loop_count_per_side, expected_portfolio_limits_,
                                            refresh_sec_update_fixture):
    # INFO:
    # Test sets max_open_notional_per_side = 45_000,

    # - if multi open orders are allowed:
    # triggers 2 strat_executors and places 2 orders BUY side from each executor
    # - if multi open orders are not allowed:
    # creates 4 strats and places each Buy Order from each executor

    # these 4 must pass for positive check and fourth order must breach limit and as a result
    # all-strat pause also should get triggered + alert must be created in portfolio_alerts

    # Updating portfolio limits
    expected_portfolio_limits_.max_open_notional_per_side = 36_000
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:4]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
    executor_http_clients_n_last_order_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_single_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   deepcopy(top_of_book_list_), refresh_sec_update_fixture, Side.BUY)
                   for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, sell_symbol, last_buy_order_id = future.result()
            executor_http_clients_n_last_order_id_tuple_list.append(
                (executor_http_client, buy_symbol, sell_symbol, last_buy_order_id))

    time.sleep(2)

    # Checking alert in portfolio_alert
    check_str = "max_open_notional_per_side breached for BUY side"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"

    portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            (f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, "
             f"pair_strat: {pair_strat}")

@pytest.mark.nightly
def test_max_open_notional_per_side_for_sell(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                             expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_, buy_order_, sell_order_,
                                             max_loop_count_per_side, expected_portfolio_limits_,
                                             refresh_sec_update_fixture):
    # INFO:
    # Test sets max_open_notional_per_side = 30_800,

    # - if multi open orders are allowed:
    # triggers 2 strat_executors and places 2 orders SELL side from each executor
    # - if multi open orders are not allowed:
    # creates 4 strats and places each SELL Order from each executor

    # these 4 must pass for positive check and fourth order must breach limit and as a result
    # all-strat pause also should get triggered + alert must be created in portfolio_alerts

    # Updating portfolio limits
    expected_portfolio_limits_.max_open_notional_per_side = 30_800
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:4]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
    executor_http_clients_n_last_order_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_place_single_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   deepcopy(top_of_book_list_), refresh_sec_update_fixture, Side.SELL)
                   for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, sell_symbol, last_sell_order_id = future.result()
            executor_http_clients_n_last_order_id_tuple_list.append(
                (executor_http_client, buy_symbol, sell_symbol, last_sell_order_id))

    # Checking alert in portfolio_alert
    check_str = "max_open_notional_per_side breached for SELL side"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"

    portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def test_all_strat_pause_for_max_gross_n_open_notional_breach(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_,
        max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # INFO:
    # Test sets max_gross_n_open_notional = 134_000

    # - if multi open orders are allowed:
    # triggers 2 strat_executors and places 2 orders each side from each executor
    # - if multi open orders are not allowed:
    # triggers 8 strat_executors out of which 4 places BUY orders each and rest 4 places SELL orders each

    # these 8 orders must pass for positive check, then one more BUY order is placed in
    # any executor and this new order journal must trigger all strat-pause + alert must be created in strat_alert

    # Updating portfolio limits
    expected_portfolio_limits_.max_gross_n_open_notional = 130_000
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
        executor_http_clients_n_last_order_id_tuple_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
            results = [executor.submit(handle_place_both_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                       deepcopy(pair_strat_),
                                       deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                       deepcopy(symbol_overview_obj_list),
                                       deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                       deepcopy(top_of_book_list_), refresh_sec_update_fixture, False)
                       for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

                executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id = future.result()
                executor_http_clients_n_last_order_id_tuple_list.append(
                    (executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id))
    else:
        sliced_buy_symbol_list = leg1_leg2_symbol_list[:4]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_symbol_list)) as executor:
            results = [
                executor.submit(handle_place_single_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                deepcopy(pair_strat_),
                                deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                deepcopy(symbol_overview_obj_list),
                                deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                deepcopy(top_of_book_list_), refresh_sec_update_fixture, Side.BUY)
                for buy_symbol, sell_symbol in sliced_buy_symbol_list]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

        sliced_sell_symbol_list = leg1_leg2_symbol_list[4:8]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_sell_symbol_list)) as executor:
            results = [
                executor.submit(handle_place_single_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                deepcopy(pair_strat_),
                                deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                deepcopy(symbol_overview_obj_list),
                                deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                deepcopy(top_of_book_list_), refresh_sec_update_fixture, Side.SELL)
                for buy_symbol, sell_symbol in sliced_sell_symbol_list]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

    # Till this point since max_open_buckets limits is breached in last order, all orders must have been
    # placed but any new order must not be placed, checking that now...

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    handle_place_both_side_orders_for_portfolio_limits_test(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, expect_no_order=True)

    # Checking alert in portfolio_alert
    check_str = "max_gross_n_open_notional breached,"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"
    time.sleep(2)
    portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def all_strat_pause_test_for_max_reject_limit_breach(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, refresh_sec):
    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_to_reject_orders"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_order_count"] = 1
            config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 2
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.trade_simulator_reload_config_query_client()

        # updating fixture values for this test-case
        max_loop_count_per_side = 2

        last_buy_rej_id, last_sell_rej_id = (
            handle_rej_order_test(buy_symbol, sell_symbol, expected_strat_limits_,
                                  last_trade_fixture_list, top_of_book_list_, max_loop_count_per_side,
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
def test_last_n_sec_order_counts(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                 expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
                                 max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_order_count.rolling_tx_count_period_seconds = 10000
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    else:
        leg1_leg2_symbol_list = leg1_leg2_symbol_list[:8]
    executor_http_clients_n_last_order_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_orders_for_portfolio_limits_test, leg1_symbol, leg2_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   deepcopy(top_of_book_list_), refresh_sec_update_fixture, False)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id = future.result()
            executor_http_clients_n_last_order_id_tuple_list.append(
                (executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id))

    order_count_updated_order_journals = (
        post_trade_engine_service_http_client.get_last_n_sec_orders_by_events_query_client(
            expected_portfolio_limits_.rolling_max_order_count.rolling_tx_count_period_seconds,
            [OrderEventType.OE_NEW]))

    assert len(order_count_updated_order_journals) == 1, \
        ("Unexpected: Length of returned list by get_last_n_sec_orders_by_events_query_client must be 1, "
         f"received: {len(order_count_updated_order_journals)}, received list: {order_count_updated_order_journals}")

    assert 8 == order_count_updated_order_journals[0].current_period_order_count, \
        (f"Mismatch: Expected last_n_sec new order_counts: 8, received: "
         f"{order_count_updated_order_journals[0].current_period_order_count}")

    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_order_count.rolling_tx_count_period_seconds = 2
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)
    time.sleep(3)   # wait to check after 2 sec to check no order is found after it

    order_count_updated_order_journals = (
        post_trade_engine_service_http_client.get_last_n_sec_orders_by_events_query_client(
            expected_portfolio_limits_.rolling_max_order_count.rolling_tx_count_period_seconds,
            [OrderEventType.OE_NEW]))

    assert len(order_count_updated_order_journals) == 0, \
        ("Unexpected: Length of returned list by get_last_n_sec_orders_by_events_query_client must be 1, "
         f"received: {len(order_count_updated_order_journals)}, received list: {order_count_updated_order_journals}")


@pytest.mark.nightly
def test_portfolio_limits_rolling_new_order_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                   pair_strat_, expected_strat_limits_,
                                                   expected_start_status_, symbol_overview_obj_list,
                                                   last_trade_fixture_list, market_depth_basemodel_list,
                                                   top_of_book_list_, buy_order_, sell_order_,
                                                   max_loop_count_per_side,
                                                   expected_portfolio_limits_, refresh_sec_update_fixture):
    # INFO:
    # Test has rolling_max_order_count.max_rolling_tx_count = 7 and
    # rolling_max_order_count.rolling_tx_count_period_seconds = 10000 that means within 10000 secs 8th new order
    # will trigger all strat-pause.

    # - if multi open orders are allowed:
    # Test will create 2 strats and will place 2 order each side
    # - if multi open orders are not allowed:
    # Test will create 8 strats and will place BUY order from each executor

    # 8th new order must breach limit and trigger all strat-pause and any new order must get ignored since strats
    # got paused + alert must be present in portfolio alerts

    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_order_count.max_rolling_tx_count = 7
    expected_portfolio_limits_.rolling_max_order_count.rolling_tx_count_period_seconds = 10000
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    if executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:2]
    else:
        sliced_buy_sell_symbol_list = leg1_leg2_symbol_list[:8]
    executor_http_clients_n_last_order_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sliced_buy_sell_symbol_list)) as executor:
        results = [executor.submit(handle_place_both_side_orders_for_portfolio_limits_test, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   deepcopy(top_of_book_list_), refresh_sec_update_fixture, False)
                   for buy_symbol, sell_symbol in sliced_buy_sell_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id = future.result()
            executor_http_clients_n_last_order_id_tuple_list.append(
                (executor_http_client, buy_symbol, last_buy_order_id, sell_symbol, last_sell_order_id))

    time.sleep(2)

    new_buy_sell_symbol_list = leg1_leg2_symbol_list[8]
    buy_symbol = new_buy_sell_symbol_list[0]
    sell_symbol = new_buy_sell_symbol_list[1]
    handle_place_both_side_orders_for_portfolio_limits_test(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, expect_no_order=True)

    # Checking alert in portfolio_alert
    check_str = "max_allowed_orders_within_period breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"

    portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"


@pytest.mark.nightly
def test_all_strat_pause_for_max_reject_limit_breach(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, max_loop_count_per_side, expected_portfolio_limits_, refresh_sec_update_fixture):
    # INFO:
    # Test has rolling_max_reject_count.max_rolling_tx_count = 4 and
    # rolling_max_reject_count.rolling_tx_count_period_seconds = 10000 that means within 10000 secs 5th rej
    # will trigger all strat-pause. Test will create 2 strats and will place 2 order each to equal threshold of
    # 4 rej orders after which one more order will also be trigger by either of strat and that must trigger
    # all strat-pause + alert must be present in portfolio alerts

    # Settings portfolio_limits for this test
    expected_portfolio_limits_.rolling_max_reject_count.max_rolling_tx_count = 4
    expected_portfolio_limits_.rolling_max_reject_count.rolling_tx_count_period_seconds = 10000
    strat_manager_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    # updating fixture values for this test-case
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    executor_http_clients_n_last_order_id_tuple_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(all_strat_pause_test_for_max_reject_limit_breach, leg1_symbol, leg2_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   deepcopy(top_of_book_list_), refresh_sec_update_fixture)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id = future.result()
            executor_http_clients_n_last_order_id_tuple_list.append(
                (executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id))

    # Placing on more rej order that must trigger auto-kill_switch
    # (Placed order will be rej type by simulator because of continues_special_order_count)
    executor_http_client, buy_symbol, sell_symbol, last_buy_rej_id, last_sell_rej_id = (
        executor_http_clients_n_last_order_id_tuple_list)[0]
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
    run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

    latest_order_journal = get_latest_order_journal_with_events_and_symbol(
        [OrderEventType.OE_BRK_REJ, OrderEventType.OE_EXH_REJ], buy_symbol,
        executor_http_client, last_order_id=last_buy_rej_id)

    time.sleep(10)
    # Checking alert in portfolio_alert
    check_str: str = "max_allowed_rejection_within_period breached"
    assert_fail_message = f"Could not find any alert saying '{check_str}'"

    portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message

    # Checking all strat pause
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Unexpected, strat_state must be paused, received {pair_strat.strat_state}, pair_strat: {pair_strat}"

# TODO: Add test for missing strat_limits
# > limit_up_down_volume_participation_rate
