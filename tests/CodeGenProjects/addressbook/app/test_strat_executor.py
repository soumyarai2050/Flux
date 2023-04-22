from tests.CodeGenProjects.addressbook.app.test_strat_manager_service_routes_callback_override import *

PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
test_config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"


# limit breach order blocks test-cases
def test_min_order_notional_breach(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                   expected_start_status_, symbol_overview_obj_list,
                                   last_trade_fixture_list, market_depth_basemodel_list,
                                   top_of_book_list_, buy_order_, sell_order_,
                                   max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 1
    qty = 1
    check_str = "blocked order_opportunity < min_order_notional limit"
    assert_fail_msg = "Could not find any alert containing message to block orders due to less " \
                      "than limit order_notional"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_msg)


def test_max_order_notional_breach(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                   expected_start_status_, symbol_overview_obj_list,
                                   last_trade_fixture_list, market_depth_basemodel_list,
                                   top_of_book_list_, buy_order_, sell_order_,
                                   max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 1000
    qty = 100
    check_str = "blocked generated order, breaches max_order_notional limit, expected less than"
    assert_fail_msg = "Could not find any alert containing message to block orders due to more " \
                      "than limit order_notional"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_msg)


def test_max_order_qty_breach(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, buy_order_, sell_order_,
                              max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 10
    qty = 600
    check_str = "blocked generated order, breaches max_order_qty limit, expected less than"
    assert_fail_msg = "Could not find any alert containing message to block orders due to excessive order qty"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_msg)


def test_breach_threshold_px_with_wrong_tob(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                            expected_start_status_, symbol_overview_obj_list,
                                            last_trade_fixture_list, market_depth_basemodel_list,
                                            top_of_book_list_, buy_order_, sell_order_,
                                            max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    tob_list = market_data_web_client.get_all_top_of_book_client()

    buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
    sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

    # checking last_trade as None in buy order
    buy_tob.last_trade = None
    market_data_web_client.put_top_of_book_client(buy_tob)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = f"blocked generated order, symbol: {buy_symbol}, side: {Side.BUY} as " \
                f"top_of_book.last_trade.px is none or 0"
    assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_msg)

    # checking last_trade px 0 in sell order
    sell_tob.last_trade.px = 0
    market_data_web_client.put_top_of_book_client(sell_tob)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = f"blocked generated order, symbol: {sell_symbol}, side: {Side.SELL} as " \
                f"top_of_book.last_trade.px is none or 0"
    assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_msg)


def test_breach_threshold_px_with_unsupported_side(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                   expected_start_status_, symbol_overview_obj_list,
                                                   last_trade_fixture_list, market_depth_basemodel_list,
                                                   top_of_book_list_, buy_order_, sell_order_,
                                                   max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "no ongoing pair strat matches this new_order_ key"
    assert_fail_msg = "Could not find any alert containing message to block orders due to unsupported side"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.SIDE_UNSPECIFIED, px, qty,
                                                                  check_str, assert_fail_msg)


def test_breach_threshold_px_with_0_depth_px(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_, buy_order_, sell_order_,
                                             max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    market_depth_list = market_data_web_client.get_all_market_depth_client()
    for market_depth in market_depth_list:
        if market_depth.symbol == buy_symbol:
            market_depth.px = 0
            market_data_web_client.put_market_depth_client(market_depth)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = f"blocked generated order, symbol: {buy_symbol}, side: {Side.BUY}, " \
                f"unable to find valid px based on max_px_levels"
    assert_fail_msg = "Could not find any alert containing message to block orders due to 0 market depth px"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_msg)


def test_breach_threshold_px_with_none_aggressive_quote(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                        expected_start_status_, symbol_overview_obj_list,
                                                        last_trade_fixture_list, market_depth_basemodel_list,
                                                        top_of_book_list_, buy_order_, sell_order_,
                                                        max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    tob_list = market_data_web_client.get_all_top_of_book_client()

    buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
    sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

    # checking last_trade as None in buy order
    buy_tob.ask_quote = None
    market_data_web_client.put_top_of_book_client(buy_tob)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = f"blocked generated BUY order, symbol: {buy_symbol}, side: {Side.BUY} as aggressive_quote" \
                f" is found None"
    assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_msg)

    # checking last_trade px 0 in sell order
    sell_tob.bid_quote = None
    market_data_web_client.put_top_of_book_client(sell_tob)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = f"blocked generated SELL order, symbol: {sell_symbol}, side: {Side.SELL} as aggressive_quote" \
                f" is found None"
    assert_fail_msg = "Could not find any alert containing message to block orders tob last trade as None"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_msg)


# todo: currently failing since executor not reaches limits check if tob is None
def test_px_check_if_tob_none(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, buy_order_, sell_order_,
                              max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    # delay to manually start addressbook_log_analyzer.py
    time.sleep(30)

    # reloading configs in TradeSimulator
    TradeSimulator.reload_configs()

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # explicitly setting waived_min_orders to 10 for this test case
    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list)

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "blocked generated order, unable to conduct px checks: top_of_book is sent None for strat"
    assert_fail_message = "Could not find any alert containing message to block orders due to no tob"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)


def test_breach_threshold_px_for_max_basis_points(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                  expected_start_status_, symbol_overview_obj_list,
                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                  top_of_book_list_, buy_order_, sell_order_,
                                                  max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    tob_list = market_data_web_client.get_all_top_of_book_client()

    buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
    sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

    buy_tob.ask_quote.px = 10
    market_data_web_client.put_top_of_book_client(buy_tob)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "blocked generated BUY order, order px: .* > allowed max_px"
    assert_fail_message = "Could not find any alert containing message to block orders wrong max basis points"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)
    sell_tob.bid_quote.px = 100
    market_data_web_client.put_top_of_book_client(sell_tob)

    # placing new non-systematic new_order
    px = 70
    qty = 90
    check_str = "blocked generated SELL order, order px: .* < allowed min_px"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_breach_threshold_px_for_max_px_by_deviation(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                     expected_start_status_, symbol_overview_obj_list,
                                                     last_trade_fixture_list, market_depth_basemodel_list,
                                                     top_of_book_list_, buy_order_, sell_order_,
                                                     max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    tob_list = market_data_web_client.get_all_top_of_book_client()

    buy_tob = tob_list[0] if tob_list[0].symbol == buy_symbol else tob_list[1]
    sell_tob = tob_list[0] if tob_list[0].symbol == sell_symbol else tob_list[1]

    buy_tob.last_trade.px = 10
    market_data_web_client.put_top_of_book_client(buy_tob)

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "blocked generated BUY order, order px: .* > allowed max_px"
    assert_fail_message = "Could not find any alert containing message to block orders tob last trade px as 0"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)

    sell_tob.last_trade.px = 100
    market_data_web_client.put_top_of_book_client(sell_tob)

    # placing new non-systematic new_order
    px = 70
    qty = 90
    check_str = "blocked generated SELL order, order px: .* < allowed min_px"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_breach_threshold_px_for_px_by_max_depth(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_, buy_order_, sell_order_,
                                                 max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    market_depth_list = market_data_web_client.get_all_market_depth_client()
    for market_depth in market_depth_list:
        if market_depth.symbol == buy_symbol:
            market_depth.px = 10
            market_data_web_client.put_market_depth_client(market_depth)

    # placing new non-systematic new_order
    px = 100
    qty = 90

    check_str = "blocked generated BUY order, order px: .* > allowed max_px"
    assert_fail_message = "Could not find any alert containing message to block orders due to less px of depth"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)
    for market_depth in market_depth_list:
        if market_depth.symbol == sell_symbol:
            market_depth.px = 100
            market_data_web_client.put_market_depth_client(market_depth)

    # placing new non-systematic new_order
    px = 70
    qty = 90
    check_str = "blocked generated SELL order, order px: .* < allowed min_px"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_strat_limits_with_none_symbol_overview(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                expected_start_status_, symbol_overview_obj_list,
                                                last_trade_fixture_list, market_depth_basemodel_list,
                                                top_of_book_list_, buy_order_, sell_order_,
                                                max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    # for symbol in config_dict["symbol_configs"]:
    #     config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
    #     config_dict["fill_percent"] = 50
    # update_yaml_configurations(config_dict, str(config_file_path))
    #
    # # delay to manually start addressbook_log_analyzer.py
    # time.sleep(30)
    #
    # # reloading configs in TradeSimulator
    # TradeSimulator.reload_configs()

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # Creating Strat
    active_pair_strat = create_n_validate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                                copy.deepcopy(expected_strat_limits_),
                                                copy.deepcopy(expected_start_status_))

    # running Last Trade
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)

    # creating market_depth
    create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)

    # Adding strat in strat_collection
    create_if_not_exists_and_validate_strat_collection(active_pair_strat)

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    loop_count = 1
    run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)

    # placing new non-systematic new_buy_order
    px = 100
    qty = 90
    check_str = "blocked generated BUY order, symbol_overview_tuple missing for symbol"
    assert_fail_message = "Could not find any alert containing message to block orders due to no symbol_overview"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)
    # placing new non-systematic new_sell_order
    px = 110
    qty = 70
    check_str = "blocked generated SELL order, symbol_overview_tuple missing for symbol"
    assert_fail_message = "Could not find any alert containing message to block orders due to no symbol_overview"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_strat_limits_with_0_consumable_open_orders(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                    expected_start_status_, symbol_overview_obj_list,
                                                    last_trade_fixture_list, market_depth_basemodel_list,
                                                    top_of_book_list_, buy_order_, sell_order_,
                                                    max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    strat_brief_list = strat_manager_service_web_client.get_all_strat_brief_client()
    # since only one strat in current test
    assert len(strat_brief_list) == 1
    strat_brief = strat_brief_list[0]
    strat_brief.pair_buy_side_trading_brief.consumable_open_orders = -1
    updated_strat_brief = strat_manager_service_web_client.put_strat_brief_client(strat_brief)
    assert updated_strat_brief.pair_buy_side_trading_brief.consumable_open_orders == -1

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "blocked generated BUY order, not enough consumable_open_orders"
    assert_fail_message = "Could not find any alert containing message to block orders due to 0 consumable open orders"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)
    strat_brief_list = strat_manager_service_web_client.get_all_strat_brief_client()
    # since only one strat in current test
    assert len(strat_brief_list) == 1
    strat_brief = strat_brief_list[0]
    strat_brief.pair_sell_side_trading_brief.consumable_open_orders = -1
    updated_strat_brief = strat_manager_service_web_client.put_strat_brief_client(strat_brief)
    assert updated_strat_brief.pair_sell_side_trading_brief.consumable_open_orders == -1

    # placing new non-systematic new_order
    px = 70
    qty = 90
    check_str = "blocked generated SELL order, not enough consumable_open_orders"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_strat_limits_with_high_consumable_notional(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                    expected_start_status_, symbol_overview_obj_list,
                                                    last_trade_fixture_list, market_depth_basemodel_list,
                                                    top_of_book_list_, buy_order_, sell_order_,
                                                    max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 1000
    qty = 900
    check_str = "blocked generated BUY order, breaches available consumable notional"
    assert_fail_message = "Could not find any alert containing message to block orders due to high consumable notional"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)
    # placing new non-systematic new_order
    px = 7000
    qty = 900
    check_str = "blocked generated SELL order, breaches available consumable notional"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_strat_limits_with_less_consumable_concentration(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                         expected_start_status_, symbol_overview_obj_list,
                                                         last_trade_fixture_list, market_depth_basemodel_list,
                                                         top_of_book_list_, buy_order_, sell_order_,
                                                         max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    strat_brief_list = strat_manager_service_web_client.get_all_strat_brief_client()
    # since only one strat in current test
    assert len(strat_brief_list) == 1
    strat_brief = strat_brief_list[0]
    strat_brief.pair_buy_side_trading_brief.consumable_concentration = 0
    strat_brief.pair_sell_side_trading_brief.consumable_concentration = 0
    updated_strat_brief = strat_manager_service_web_client.put_strat_brief_client(strat_brief)
    assert updated_strat_brief.pair_buy_side_trading_brief.consumable_concentration == 0
    assert updated_strat_brief.pair_sell_side_trading_brief.consumable_concentration == 0

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "blocked generated BUY order, not enough consumable_concentration:"
    assert_fail_message = "Could not find any alert containing message to block orders due to less " \
                          "consumable concentration"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)
    # placing new non-systematic new_order
    px = 70
    qty = 90
    check_str = "blocked generated SELL order, not enough consumable_concentration:"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_strat_limits_with_symbol_overview_limit_dn_up_px(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                          expected_start_status_, symbol_overview_obj_list,
                                                          last_trade_fixture_list, market_depth_basemodel_list,
                                                          top_of_book_list_, buy_order_, sell_order_,
                                                          max_loop_count_per_side, residual_wait_sec, config_dict):
    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 160
    qty = 90
    check_str = "blocked generated BUY order, limit up trading not allowed on day-1"
    assert_fail_message = "Could not find any alert containing message to block orders due to order_px higher " \
                          "than symbol_overview's limit_up_px"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)

    # placing new non-systematic new_order
    px = 40
    qty = 90
    check_str = "blocked generated SELL order, limit down trading not allowed on day-1"
    assert_fail_message = "Could not find any alert containing message to block orders due to order_px higher " \
                          "than symbol_overview's limit_up_px"
    handle_place_order_and_check_str_in_alert_for_executor_limits(sell_symbol, Side.SELL, px, qty,
                                                                  check_str, assert_fail_message)


def test_strat_limits_with_low_consumable_participation_qty(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                            expected_start_status_, symbol_overview_obj_list,
                                                            last_trade_fixture_list, market_depth_basemodel_list,
                                                            top_of_book_list_, buy_order_, sell_order_,
                                                            max_loop_count_per_side, residual_wait_sec, config_dict):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # Creating Strat
    active_pair_strat = create_n_validate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                                copy.deepcopy(expected_strat_limits_),
                                                copy.deepcopy(expected_start_status_))
    # running symbol_overview
    run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list)

    # creating market_depth
    create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)

    # Adding strat in strat_collection
    create_if_not_exists_and_validate_strat_collection(active_pair_strat)

    # buy test
    loop_count = 1
    run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # placing new non-systematic new_order
    px = 100
    qty = 90
    check_str = "blocked generated order, not enough consumable_participation_qty available"
    assert_fail_message = "Could not find any alert containing message to block orders due to low " \
                          "consumable_participation_qty"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message)


# portfolio limits checks
def test_portfolio_limits_rolling_new_order_breach(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                   expected_start_status_, symbol_overview_obj_list,
                                                   last_trade_fixture_list, market_depth_basemodel_list,
                                                   top_of_book_list_, buy_order_, sell_order_,
                                                   max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    # delay to manually start addressbook_log_analyzer.py
    time.sleep(30)

    # reloading configs in TradeSimulator
    TradeSimulator.reload_configs()

    underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_)

    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    rolling_max_order_count = RollingMaxOrderCountOptional(max_rolling_tx_count=1, rolling_tx_count_period_seconds=100)
    portfolio_limits_basemodel = PortfolioLimitsBaseModel(_id=1, rolling_max_order_count=rolling_max_order_count)
    updated_portfolio_limits = strat_manager_service_web_client.patch_portfolio_limits_client(
        portfolio_limits_basemodel)
    assert updated_portfolio_limits.rolling_max_order_count == rolling_max_order_count

    # placing new non-systematic new_order
    px = 100
    qty = 90
    # placing new non-systematic new_order
    place_new_order(buy_symbol, Side.BUY, px, qty)
    print(f"symbol: {buy_symbol}, Created new_order obj")

    new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, buy_symbol)
    new_order_id = new_order_journal.order.order_id

    check_str = "blocked generated order, breaches max_rolling_order_count limit, expected less than"
    assert_fail_message = "Could not find any alert containing message to block orders due to " \
                          "max_rolling_order_count limit breach"
    handle_place_order_and_check_str_in_alert_for_executor_limits(buy_symbol, Side.BUY, px, qty,
                                                                  check_str, assert_fail_message,
                                                                  last_order_id=new_order_id)
