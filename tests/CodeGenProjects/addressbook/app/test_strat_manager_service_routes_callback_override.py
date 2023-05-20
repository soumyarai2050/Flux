import math
from tests.CodeGenProjects.addressbook.app.utility_test_functions import *
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase, config_file_path
from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations, update_yaml_configurations
from FluxPythonUtils.scripts.utility_functions import drop_mongo_collections, clean_mongo_collections
import concurrent.futures
import re


def test_clean_and_set_limits(clean_and_set_limits):
    pass


# sanity test to create and activate pair_strat
def test_create_pair_strat(clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
                           expected_strat_limits_, expected_start_status_):
    with ExecutorNLogAnalyzerManager():
        # creates and activates multiple pair_strats
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                    expected_start_status_)


# sanity test to create orders
def test_place_sanity_orders(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                             expected_start_status_, symbol_overview_obj_list,
                             last_trade_fixture_list, market_depth_basemodel_list,
                             top_of_book_list_, buy_order_, sell_order_,
                             max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]
        total_order_count_for_each_side = max_loop_count_per_side

        # making limits suitable for this test
        expected_strat_limits_.max_open_orders_per_side = 10
        expected_strat_limits_.residual_restriction.max_residual = 105000
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # Placing buy orders
        buy_ack_order_id = None
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_buy_top_of_book(loop_count + 1, buy_symbol, sell_symbol, top_of_book_list_)

            ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK,
                                                                                buy_symbol,
                                                                                last_order_id=buy_ack_order_id)
            buy_ack_order_id = ack_order_journal.order.order_id

        # Placing sell orders
        sell_ack_order_id = None
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_sell_top_of_book(sell_symbol)

            ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK,
                                                                                sell_symbol,
                                                                                last_order_id=sell_ack_order_id)
            sell_ack_order_id = ack_order_journal.order.order_id


def test_add_brokers_to_portfolio_limits(clean_and_set_limits):
    """Adding Broker entries in portfolio limits"""

    with ExecutorNLogAnalyzerManager():
        broker = broker_fixture()

        portfolio_limits_basemodel = PortfolioLimitsBaseModel(_id=1, eligible_brokers=[broker])
        strat_manager_service_web_client.patch_portfolio_limits_client(portfolio_limits_basemodel)

        stored_portfolio_limits_ = strat_manager_service_web_client.get_portfolio_limits_client(1)
        for stored_broker in stored_portfolio_limits_.eligible_brokers:
            stored_broker.id = None
        broker.id = None
        assert broker in stored_portfolio_limits_.eligible_brokers, f"Couldn't find broker {broker} in " \
                                                                    f"eligible_broker " \
                                                                    f"{stored_portfolio_limits_.eligible_brokers}"


def test_buy_sell_order_multi_pair_serialized(clean_and_set_limits, pair_securities_with_sides_,
                                              buy_order_, sell_order_, buy_fill_journal_,
                                              sell_fill_journal_, expected_buy_order_snapshot_,
                                              expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
                                              pair_strat_, expected_strat_limits_, expected_start_status_,
                                              expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                                              last_trade_fixture_list, symbol_overview_obj_list,
                                              market_depth_basemodel_list, expected_order_limits_,
                                              expected_portfolio_limits_, max_loop_count_per_side,
                                              buy_sell_symbol_list, residual_wait_sec):
    with ExecutorNLogAnalyzerManager():
        symbol_pair_counter = 0
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            symbol_pair_counter += 1
            handle_test_buy_sell_order(buy_symbol, sell_symbol, max_loop_count_per_side, symbol_pair_counter,
                                       residual_wait_sec, buy_order_, sell_order_, buy_fill_journal_,
                                       sell_fill_journal_, expected_buy_order_snapshot_, expected_sell_order_snapshot_,
                                       expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, expected_strat_brief_, expected_portfolio_status_,
                                       top_of_book_list_, last_trade_fixture_list, symbol_overview_obj_list,
                                       market_depth_basemodel_list)

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)
        total_symbol_pairs = len(buy_sell_symbol_list)
        verify_portfolio_status(max_loop_count_per_side, total_symbol_pairs, expected_portfolio_status)


def test_buy_sell_order_multi_pair_parallel(clean_and_set_limits, pair_securities_with_sides_,
                                            buy_order_, sell_order_, buy_fill_journal_,
                                            sell_fill_journal_, expected_buy_order_snapshot_,
                                            expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
                                            pair_strat_, expected_strat_limits_, expected_start_status_,
                                            expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                                            last_trade_fixture_list, symbol_overview_obj_list,
                                            market_depth_basemodel_list, expected_order_limits_,
                                            expected_portfolio_limits_, max_loop_count_per_side,
                                            buy_sell_symbol_list, config_dict, residual_wait_sec):
    with ExecutorNLogAnalyzerManager():
        symbol_pair_counter = 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = [executor.submit(handle_test_buy_sell_order, buy_symbol, sell_symbol, max_loop_count_per_side,
                                       symbol_pair_counter, residual_wait_sec, copy.deepcopy(buy_order_),
                                       copy.deepcopy(sell_order_), copy.deepcopy(buy_fill_journal_),
                                       copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_order_snapshot_),
                                       copy.deepcopy(expected_sell_order_snapshot_),
                                       copy.deepcopy(expected_symbol_side_snapshot_), copy.deepcopy(pair_strat_),
                                       copy.deepcopy(expected_strat_limits_),
                                       copy.deepcopy(expected_start_status_), copy.deepcopy(expected_strat_brief_),
                                       copy.deepcopy(expected_portfolio_status_), copy.deepcopy(top_of_book_list_),
                                       copy.deepcopy(last_trade_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                       copy.deepcopy(market_depth_basemodel_list))
                       for buy_symbol, sell_symbol in buy_sell_symbol_list]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)
        total_symbol_pairs = len(buy_sell_symbol_list)
        verify_portfolio_status(max_loop_count_per_side, total_symbol_pairs, expected_portfolio_status)


def test_buy_sell_non_systematic_order_multi_pair_serialized(clean_and_set_limits, pair_securities_with_sides_,
                                                             buy_order_, sell_order_, buy_fill_journal_,
                                                             sell_fill_journal_, expected_buy_order_snapshot_,
                                                             expected_sell_order_snapshot_,
                                                             expected_symbol_side_snapshot_,
                                                             pair_strat_, expected_strat_limits_,
                                                             expected_start_status_,
                                                             expected_strat_brief_, expected_portfolio_status_,
                                                             top_of_book_list_,
                                                             last_trade_fixture_list, symbol_overview_obj_list,
                                                             market_depth_basemodel_list, expected_order_limits_,
                                                             expected_portfolio_limits_, max_loop_count_per_side,
                                                             buy_sell_symbol_list, residual_wait_sec):
    with ExecutorNLogAnalyzerManager():
        symbol_pair_counter = 0
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            symbol_pair_counter += 1
            handle_test_buy_sell_order(buy_symbol, sell_symbol, max_loop_count_per_side, symbol_pair_counter,
                                       residual_wait_sec, buy_order_, sell_order_, buy_fill_journal_,
                                       sell_fill_journal_,
                                       expected_buy_order_snapshot_, expected_sell_order_snapshot_,
                                       expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, expected_strat_brief_, expected_portfolio_status_,
                                       top_of_book_list_, last_trade_fixture_list, symbol_overview_obj_list,
                                       market_depth_basemodel_list, is_non_systematic_run=True)

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)
        total_symbol_pairs = len(buy_sell_symbol_list)
        verify_portfolio_status(max_loop_count_per_side, total_symbol_pairs, expected_portfolio_status)


def test_buy_sell_non_systematic_order_multi_pair_parallel(clean_and_set_limits, pair_securities_with_sides_,
                                                           buy_order_, sell_order_, buy_fill_journal_,
                                                           sell_fill_journal_, expected_buy_order_snapshot_,
                                                           expected_sell_order_snapshot_,
                                                           expected_symbol_side_snapshot_,
                                                           pair_strat_, expected_strat_limits_, expected_start_status_,
                                                           expected_strat_brief_, expected_portfolio_status_,
                                                           top_of_book_list_,
                                                           last_trade_fixture_list, symbol_overview_obj_list,
                                                           market_depth_basemodel_list, expected_order_limits_,
                                                           expected_portfolio_limits_, max_loop_count_per_side,
                                                           buy_sell_symbol_list, residual_wait_sec):
    with ExecutorNLogAnalyzerManager():

        symbol_pair_counter = 1
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = [executor.submit(handle_test_buy_sell_order, buy_symbol, sell_symbol, max_loop_count_per_side,
                                       symbol_pair_counter, residual_wait_sec, copy.deepcopy(buy_order_),
                                       copy.deepcopy(sell_order_), copy.deepcopy(buy_fill_journal_),
                                       copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_order_snapshot_),
                                       copy.deepcopy(expected_sell_order_snapshot_),
                                       copy.deepcopy(expected_symbol_side_snapshot_), copy.deepcopy(pair_strat_),
                                       copy.deepcopy(expected_strat_limits_),
                                       copy.deepcopy(expected_start_status_), copy.deepcopy(expected_strat_brief_),
                                       copy.deepcopy(expected_portfolio_status_), copy.deepcopy(top_of_book_list_),
                                       copy.deepcopy(last_trade_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                       copy.deepcopy(market_depth_basemodel_list), True)
                       for buy_symbol, sell_symbol in buy_sell_symbol_list]

            for future in concurrent.futures.as_completed(results):
                if future.exception() is not None:
                    raise Exception(future.exception())

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)
        total_symbol_pairs = len(buy_sell_symbol_list)
        verify_portfolio_status(max_loop_count_per_side, total_symbol_pairs, expected_portfolio_status)


def test_validate_kill_switch_systematic(clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
                                         expected_strat_limits_, expected_start_status_,
                                         symbol_overview_obj_list, last_trade_fixture_list,
                                         market_depth_basemodel_list, top_of_book_list_):
    with ExecutorNLogAnalyzerManager():
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            portfolio_status = PortfolioStatusBaseModel(_id=1, kill_switch=True)
            updated_portfolio_status = strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status)
            assert updated_portfolio_status.kill_switch, "Unexpected: Portfolio_status kill_switch is False, " \
                                                         "expected to be True"

            run_buy_top_of_book(1, buy_symbol, sell_symbol, top_of_book_list_)
            # internally checking buy order
            order_journal = \
                get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                buy_symbol, expect_no_order=True)

            run_sell_top_of_book(sell_symbol)
            # internally checking sell order
            order_journal = \
                get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                sell_symbol, expect_no_order=True)


def test_validate_kill_switch_non_systematic(clean_and_set_limits, buy_sell_symbol_list,
                                             pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_, buy_order_, sell_order_):
    with ExecutorNLogAnalyzerManager():
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            portfolio_status = PortfolioStatusBaseModel(_id=1, kill_switch=True)
            updated_portfolio_status = strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status)
            assert updated_portfolio_status.kill_switch, "Unexpected: Portfolio_status kill_switch is False, " \
                                                         "expected to be True"

            # placing buy order
            place_new_order(buy_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty)
            time.sleep(2)
            # internally checking buy order
            order_journal = \
                get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                buy_symbol, expect_no_order=True)

            # placing sell order
            place_new_order(sell_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty)
            time.sleep(2)
            # internally checking sell order
            order_journal = \
                get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                sell_symbol, expect_no_order=True)


def test_simulated_partial_fills(clean_and_set_limits, buy_sell_symbol_list,
                                 pair_strat_, expected_strat_limits_,
                                 expected_start_status_, symbol_overview_obj_list,
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
                                 max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        partial_filled_qty: int | None = None
        unfilled_amount: int | None = None

        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            # buy fills check
            for check_symbol in [buy_symbol, sell_symbol]:
                order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    order_id, partial_filled_qty = \
                        underlying_handle_simulated_partial_fills_test(loop_count, check_symbol, buy_symbol,
                                                                       sell_symbol,
                                                                       last_trade_fixture_list, top_of_book_list_,
                                                                       order_id)
                time.sleep(5)
                pair_strat_obj = get_pair_strat_from_symbol(check_symbol)
                if check_symbol == buy_symbol:
                    assert partial_filled_qty * max_loop_count_per_side == \
                           pair_strat_obj.strat_status.total_fill_buy_qty, \
                        f"Unmatched total_fill_buy_qty: expected {partial_filled_qty * max_loop_count_per_side} " \
                        f"received {pair_strat_obj.strat_status.total_fill_buy_qty}"
                else:
                    assert partial_filled_qty * max_loop_count_per_side == \
                           pair_strat_obj.strat_status.total_fill_sell_qty, \
                        f"Unmatched total_fill_sell_qty: expected {partial_filled_qty * max_loop_count_per_side} " \
                        f"received {pair_strat_obj.strat_status.total_fill_sell_qty}"


def test_simulated_multi_partial_fills(clean_and_set_limits, buy_sell_symbol_list,
                                       pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list,
                                       last_trade_fixture_list, market_depth_basemodel_list,
                                       top_of_book_list_, buy_order_, sell_order_,
                                       max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 10
        config_dict["symbol_configs"][symbol]["total_fill_count"] = 5
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        partial_filled_qty: int | None = None

        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            # buy fills check
            for check_symbol in [buy_symbol, sell_symbol]:
                order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    order_id, partial_filled_qty = \
                        underlying_handle_simulated_multi_partial_fills_test(loop_count, check_symbol, buy_symbol,
                                                                             sell_symbol, last_trade_fixture_list,
                                                                             top_of_book_list_, order_id)

                pair_strat_obj = get_pair_strat_from_symbol(check_symbol)
                symbol_configs = TradeSimulator.get_symbol_configs(check_symbol)
                total_fill_qty = pair_strat_obj.strat_status.total_fill_buy_qty \
                    if check_symbol == buy_symbol else pair_strat_obj.strat_status.total_fill_sell_qty
                expected_total_fill_qty = \
                    partial_filled_qty * max_loop_count_per_side * symbol_configs.get("total_fill_count")
                assert expected_total_fill_qty == total_fill_qty, "total_fill_qty mismatched: expected " \
                                                                  f"{expected_total_fill_qty} received " \
                                                                  f"{total_fill_qty}"


def test_filled_status(clean_and_set_limits, buy_sell_symbol_list,
                       pair_strat_, expected_strat_limits_,
                       expected_start_status_, symbol_overview_obj_list,
                       last_trade_fixture_list, market_depth_basemodel_list,
                       top_of_book_list_, buy_order_, sell_order_, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]

        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
        loop_count = 1
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
        time.sleep(2)  # delay for order to get placed

        ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, buy_symbol)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = TradeSimulator.get_partial_allowed_fill_qty(buy_symbol, ack_order_journal.order.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"filled_qty mismatched: expected filled_qty {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id)
        assert order_snapshot.order_status == OrderStatusType.OE_ACKED, "OrderStatus mismatched: expected status " \
                                                                        f"OrderStatusType.OE_ACKED received " \
                                                                        f"{order_snapshot.order_status}"

        # processing remaining 50% fills
        TradeSimulator.process_fill(ack_order_journal.order.order_id, ack_order_journal.order.px,
                                    ack_order_journal.order.qty, ack_order_journal.order.side,
                                    ack_order_journal.order.security.sec_id, ack_order_journal.order.underlying_account)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                          f"expected {latest_fill_journal} " \
                                                                          f"received " \
                                                                          f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"

        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id)
        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                         f"OrderStatusType.OE_FILLED received " \
                                                                         f"{order_snapshot.order_status}"


def test_over_fill_case_1(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                          expected_start_status_, symbol_overview_obj_list,
                          last_trade_fixture_list, market_depth_basemodel_list,
                          top_of_book_list_, buy_order_, sell_order_, config_dict):
    """
    Test case when order_snapshot is in OE_ACKED and fill is triggered to make it over_filled
    """

    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 60
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]

        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
        loop_count = 1
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
        time.sleep(2)  # delay for order to get placed

        ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, buy_symbol)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = TradeSimulator.get_partial_allowed_fill_qty(buy_symbol, ack_order_journal.order.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id)
        assert order_snapshot.order_status == OrderStatusType.OE_ACKED, "OrderStatus mismatched: expected status " \
                                                                        f"OrderStatusType.OE_ACKED received " \
                                                                        f"{order_snapshot.order_status}"

        # processing fill for over_fill
        TradeSimulator.process_fill(ack_order_journal.order.order_id, ack_order_journal.order.px,
                                    ack_order_journal.order.qty, ack_order_journal.order.side,
                                    ack_order_journal.order.security.sec_id, ack_order_journal.order.underlying_account)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                          f"expected {latest_fill_journal} " \
                                                                          f"received " \
                                                                          f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"

        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id)
        assert order_snapshot.filled_qty == order_snapshot.order_brief.qty, "order_snapshot filled_qty mismatch: " \
                                                                            f"expected complete fill, i.e.," \
                                                                            f"{order_snapshot.order_brief.qty} " \
                                                                            f"received {order_snapshot.filled_qty}"
        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                         f"OrderStatusType.OE_FILLED received " \
                                                                         f"{order_snapshot.order_status}"

        time.sleep(15)
        pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
        # since only one strat exists for this test
        assert len(pair_strat_list) == 1, "Expected only one pair_strat since this test only created single strategy " \
                                          f"received {len(pair_strat_list)}, pair_strat_list: {pair_strat_list}"
        pair_strat = pair_strat_list[0]

        check_str = "Unexpected: Received fill that makes order_snapshot OVER_FILLED"
        for alert in pair_strat.strat_status.strat_alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            assert False, f"Couldn't find any alert saying: {check_str}"
        assert True


def test_over_fill_case_2(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                          expected_start_status_, symbol_overview_obj_list,
                          last_trade_fixture_list, market_depth_basemodel_list,
                          top_of_book_list_, buy_order_, sell_order_, config_dict):
    """
    Test case when order_snapshot is in OE_FILLED and fill is triggered to make it over_filled
    """

    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 100
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]

        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
        loop_count = 1
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
        time.sleep(5)  # delay for order to get placed

        ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, buy_symbol)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = TradeSimulator.get_partial_allowed_fill_qty(buy_symbol, ack_order_journal.order.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id)
        assert order_snapshot.filled_qty == order_snapshot.order_brief.qty, "order_snapshot filled_qty mismatch: " \
                                                                            f"expected complete fill, i.e.," \
                                                                            f"{order_snapshot.order_brief.qty} " \
                                                                            f"received {order_snapshot.filled_qty}"
        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                         f"OrderStatusType.OE_FILLED received " \
                                                                         f"{order_snapshot.order_status}"

        # processing fill for over_fill
        TradeSimulator.process_fill(ack_order_journal.order.order_id, ack_order_journal.order.px,
                                    ack_order_journal.order.qty, ack_order_journal.order.side,
                                    ack_order_journal.order.security.sec_id, ack_order_journal.order.underlying_account)
        time.sleep(2)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                          f"expected {latest_fill_journal} " \
                                                                          f"received " \
                                                                          f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id)
        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                         f"OrderStatusType.OE_FILLED received " \
                                                                         f"{order_snapshot.order_status}"

        time.sleep(15)
        pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
        # since only one strat exists for this test
        assert len(pair_strat_list) == 1, "Expected only one pair_strat since this test only created single strategy " \
                                          f"received {len(pair_strat_list)}, pair_strat_list: {pair_strat_list}"
        pair_strat = pair_strat_list[0]

        check_str = "Unsupported - Fill received for completely filled order_snapshot"
        for alert in pair_strat.strat_status.strat_alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            assert False, f"Couldn't find any alert saying: {check_str}, received pair_strat: {pair_strat}"
        assert True


def test_ack_to_rej_orders(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                           expected_start_status_, symbol_overview_obj_list,
                           last_trade_fixture_list, market_depth_basemodel_list,
                           top_of_book_list_, max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_ack_to_reject_orders"] = True
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        handle_rej_order_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, max_loop_count_per_side, True)


def test_unack_to_rej_orders(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                             expected_start_status_, symbol_overview_obj_list,
                             last_trade_fixture_list, market_depth_basemodel_list,
                             top_of_book_list_, max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_new_to_reject_orders"] = True

    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        handle_rej_order_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, max_loop_count_per_side, False)


def test_cxl_rej(clean_and_set_limits, buy_sell_symbol_list,
                 pair_strat_, expected_strat_limits_,
                 expected_start_status_, symbol_overview_obj_list,
                 last_trade_fixture_list, market_depth_basemodel_list,
                 top_of_book_list_, buy_order_, sell_order_,
                 max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_cxl_rej_orders"] = True
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)
            for check_symbol in [buy_symbol, sell_symbol]:
                continues_order_count, continues_special_order_count = get_continuous_order_configs(check_symbol)
                order_count = 0
                special_order_count = 0
                last_cxl_order_id = None
                last_cxl_rej_order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
                    if check_symbol == buy_symbol:
                        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
                    else:
                        run_sell_top_of_book(sell_symbol)
                    time.sleep(10)  # delay for order to get placed and trigger cxl

                    if order_count < continues_order_count:
                        check_order_event = OrderEventType.OE_CXL_ACK
                        order_count += 1
                    else:
                        if special_order_count < continues_special_order_count:
                            check_order_event = OrderEventType.OE_CXL_REJ
                            special_order_count += 1
                        else:
                            check_order_event = OrderEventType.OE_CXL_ACK
                            order_count = 1
                            special_order_count = 0

                    # internally contains assert statements
                    last_cxl_order_id, last_cxl_rej_order_id = verify_cxl_rej(last_cxl_order_id, last_cxl_rej_order_id,
                                                                              check_order_event, check_symbol)


def test_alert_handling_for_pair_strat(clean_and_set_limits, buy_sell_symbol_list,
                                       pair_strat_, expected_strat_limits_,
                                       expected_start_status_, sample_alert):
    with ExecutorNLogAnalyzerManager():

        # creating strat
        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]
        total_loop_count = 5
        active_pair_strat = create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_,
                                                    expected_strat_limits_, expected_start_status_)

        alert_id_list = []
        broker_id_list = []
        for loop_count in range(total_loop_count):
            # check to add alert
            alert = copy.deepcopy(sample_alert)
            alert.id = f"test_id_{loop_count}"
            broker = broker_fixture()
            update_pair_strat = \
                PairStratBaseModel(_id=active_pair_strat.id,
                                   strat_status=StratStatusOptional(strat_alerts=[alert]),
                                   strat_limits=StratLimitsOptional(eligible_brokers=[broker]))

            updated_pair_strat = strat_manager_service_web_client.patch_pair_strat_client(update_pair_strat)
            assert alert in updated_pair_strat.strat_status.strat_alerts, f"Couldn't find alert {alert} in " \
                                                                          f"strat_alerts list" \
                                                                          f"{updated_pair_strat.strat_status.strat_alerts}"
            assert broker in updated_pair_strat.strat_limits.eligible_brokers, f"couldn't find broker in " \
                                                                               f"eligible_brokers list " \
                                                                               f"{updated_pair_strat.strat_limits.eligible_brokers}"
            alert_id_list.append(alert.id)
            broker_id_list.append(broker.id)

            # check to add more impacted orders and update alert
            updated_alert = copy.deepcopy(alert)
            updated_alert.alert_brief = "Updated alert"
            updated_alert.impacted_order[0].order_id = "O2"
            updated_alert.impacted_order[0].security.sec_id = sell_symbol
            update_pair_strat = \
                PairStratBaseModel(_id=active_pair_strat.id,
                                   strat_status=StratStatusOptional(strat_alerts=[updated_alert]))
            updated_pair_strat = strat_manager_service_web_client.patch_pair_strat_client(update_pair_strat)

            alert.impacted_order.extend(updated_alert.impacted_order)
            alert.alert_brief = updated_alert.alert_brief
            assert alert in updated_pair_strat.strat_status.strat_alerts, f"Couldn't find alert {alert} in " \
                                                                          f"strat_alerts list " \
                                                                          f"{updated_pair_strat.strat_status.strat_alerts}"

        # Deleting alerts
        for alert_id in alert_id_list:
            delete_intended_alert = AlertOptional(_id=alert_id)
            update_pair_strat = \
                PairStratBaseModel(_id=active_pair_strat.id,
                                   strat_status=StratStatusOptional(strat_alerts=[delete_intended_alert]))
            updated_pair_strat = strat_manager_service_web_client.patch_pair_strat_client(update_pair_strat)
            alert_id_list = [alert.id for alert in updated_pair_strat.strat_status.strat_alerts]
            assert alert_id not in alert_id_list, f"Unexpectedly found alert_id {alert_id} " \
                                                  f"in alert_id list {alert_id_list}"

        # deleting broker
        for broker_id in broker_id_list:
            delete_intended_broker = BrokerOptional(_id=broker_id)
            update_pair_strat = \
                PairStratBaseModel(_id=active_pair_strat.id,
                                   strat_limits=StratLimitsOptional(eligible_brokers=[delete_intended_broker]))
            updated_pair_strat = strat_manager_service_web_client.patch_pair_strat_client(update_pair_strat)
            broker_id_list = [broker.id for broker in updated_pair_strat.strat_limits.eligible_brokers]
            assert broker_id not in broker_id_list, f"Unexpectedly found broker_id {broker_id} in broker_id list " \
                                                    f"{broker_id_list}"


def test_underlying_account_cumulative_fill_qty_query(clean_and_set_limits, buy_sell_symbol_list,
                                                      pair_strat_, expected_strat_limits_,
                                                      expected_start_status_, symbol_overview_obj_list,
                                                      last_trade_fixture_list, market_depth_basemodel_list,
                                                      top_of_book_list_):
    with ExecutorNLogAnalyzerManager():

        underlying_account_prefix: str = "Acc"
        buy_tob_last_update_date_time_tracker: DateTime | None = None
        sell_tob_last_update_date_time_tracker: DateTime | None = None
        buy_order_id = None
        sell_order_id = None
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            # buy handling
            buy_tob_last_update_date_time_tracker, buy_order_id = \
                create_fills_for_underlying_account_test(buy_symbol, sell_symbol, top_of_book_list_,
                                                         buy_tob_last_update_date_time_tracker, buy_order_id,
                                                         underlying_account_prefix, Side.BUY)

            # sell handling
            sell_tob_last_update_date_time_tracker, sell_order_id = \
                create_fills_for_underlying_account_test(buy_symbol, sell_symbol, top_of_book_list_,
                                                         sell_tob_last_update_date_time_tracker, sell_order_id,
                                                         underlying_account_prefix, Side.SELL)

            for symbol, side in [(buy_symbol, "BUY"), (sell_symbol, "SELL")]:
                underlying_account_cumulative_fill_qty_obj_list = \
                    strat_manager_service_web_client.get_underlying_account_cumulative_fill_qty_query_client(symbol,
                                                                                                             side)
                assert len(underlying_account_cumulative_fill_qty_obj_list) == 1, \
                    "Expected exactly one obj from query get_underlying_account_cumulative_fill_qty_query_client," \
                    f"received {len(underlying_account_cumulative_fill_qty_obj_list)}, received list " \
                    f"{underlying_account_cumulative_fill_qty_obj_list}"
                assert len(
                    underlying_account_cumulative_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty) == 2, \
                    "length of list field underlying_account_n_cumulative_fill_qty of " \
                    "underlying_account_cumulative_fill_qty_obj mismatched, expected 2 received " \
                    f"{len(underlying_account_cumulative_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty)}"

                underlying_account_count = 2
                for loop_count in range(underlying_account_count):
                    underlying_account_n_cum_fill_qty_obj = \
                        underlying_account_cumulative_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty[
                            loop_count]
                    assert underlying_account_n_cum_fill_qty_obj.underlying_account == \
                           f"{underlying_account_prefix}_{underlying_account_count - loop_count}", \
                        "underlying_account string field of underlying_account_n_cum_fill_qty_obj mismatched: " \
                        f"expected {underlying_account_prefix}_{underlying_account_count - loop_count} " \
                        f"received {underlying_account_n_cum_fill_qty_obj.underlying_account}"
                    assert underlying_account_n_cum_fill_qty_obj.cumulative_qty == 15, \
                        "Unexpected cumulative qty: expected 15 received " \
                        f"{underlying_account_n_cum_fill_qty_obj.cumulative_qty}"


def test_last_n_sec_order_qty_sum_and_order_count(clean_and_set_limits, buy_sell_symbol_list,
                                                  pair_strat_, expected_strat_limits_,
                                                  expected_start_status_, symbol_overview_obj_list,
                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                  top_of_book_list_, buy_fill_journal_, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]
        total_order_count_for_each_side = 10
        _, single_buy_order_qty, _, _, _ = get_buy_order_related_values()

        expected_strat_limits_ = copy.deepcopy(expected_strat_limits_)
        expected_strat_limits_.residual_restriction.max_residual = 105000
        expected_strat_limits_.max_open_orders_per_side = 10
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # buy testing
        buy_new_order_id = None
        order_create_time_list = []
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_buy_top_of_book(loop_count + 1, buy_symbol, sell_symbol, top_of_book_list_)

            ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                                buy_symbol,
                                                                                last_order_id=buy_new_order_id)
            buy_new_order_id = ack_order_journal.order.order_id
            order_create_time_list.append(ack_order_journal.order_event_date_time)
            time.sleep(2)

        order_create_time_list.reverse()
        for loop_count in range(total_order_count_for_each_side):
            delta = DateTime.utcnow() - order_create_time_list[loop_count]
            last_n_sec = int(math.ceil(delta.total_seconds())) + 1

            # making portfolio_limits_obj.rolling_max_order_count.rolling_tx_count_period_seconds computed last_n_sec(s)
            # this is required as rolling_new_order_count takes internally this limit as last_n_sec to provide counts
            # in query
            rolling_max_order_count = RollingMaxOrderCountOptional(rolling_tx_count_period_seconds=last_n_sec)
            portfolio_limits = PortfolioLimitsBaseModel(_id=1, rolling_max_order_count=rolling_max_order_count)
            updated_portfolio_limits = strat_manager_service_web_client.patch_portfolio_limits_client(portfolio_limits)
            assert updated_portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds == last_n_sec, \
                f"Unexpected last_n_sec value: expected {last_n_sec}, " \
                f"received {updated_portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds}"

            call_date_time = DateTime.utcnow()
            executor_check_snapshot_obj = \
                strat_manager_service_web_client.get_executor_check_snapshot_query_client(
                    buy_symbol, "BUY", last_n_sec)

            assert len(executor_check_snapshot_obj) == 1, \
                f"Received unexpected length of list of executor_check_snapshot_obj from query," \
                f"expected one obj received {len(executor_check_snapshot_obj)}"
            assert executor_check_snapshot_obj[0].last_n_sec_order_qty == single_buy_order_qty * (loop_count + 1), \
                f"Order qty mismatched for last {last_n_sec} " \
                f"secs of {buy_symbol} from {call_date_time} for side {Side.BUY}"
            assert executor_check_snapshot_obj[0].rolling_new_order_count == loop_count + 1, \
                f"New Order count mismatched for last {last_n_sec} " \
                f"secs from {call_date_time} of {buy_symbol} for side {Side.BUY}"


def test_acked_unsolicited_cxl(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                               expected_start_status_, symbol_overview_obj_list,
                               last_trade_fixture_list, market_depth_basemodel_list,
                               top_of_book_list_, buy_order_, sell_order_,
                               max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_unsolicited_cxl(buy_sell_symbol_list, expected_strat_limits_, expected_start_status_, pair_strat_,
                               symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                               max_loop_count_per_side, top_of_book_list_)


def test_unacked_unsolicited_cxl(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                 expected_start_status_, symbol_overview_obj_list,
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
                                 max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_orders"] = True
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_unsolicited_cxl(buy_sell_symbol_list, expected_strat_limits_, expected_start_status_, pair_strat_,
                               symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                               max_loop_count_per_side, top_of_book_list_)


def test_pair_strat_update_counters(clean_and_set_limits, buy_sell_symbol_list,
                                    pair_strat_, expected_strat_limits_, expected_start_status_):
    with ExecutorNLogAnalyzerManager():
        activated_strats = []

        # creates and activates multiple pair_strats
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            activated_strat = create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                                      expected_start_status_)
            activated_strats.append(activated_strat)

        for index, activated_strat in enumerate(activated_strats):
            # updating pair_strat_params
            pair_strat = \
                PairStratBaseModel(_id=activated_strat.id,
                                   pair_strat_params=PairStratParamsOptional(common_premium=index))
            updates_pair_strat = strat_manager_service_web_client.patch_pair_strat_client(pair_strat)
            assert updates_pair_strat.pair_strat_params_update_seq_num == \
                   activated_strat.pair_strat_params_update_seq_num + 1, \
                f"Mismatched pair_strat_params_update_seq_num: expected " \
                f"{activated_strat.pair_strat_params_update_seq_num + 1}, received " \
                f"{updates_pair_strat.pair_strat_params_update_seq_num}"

        for index, activated_strat in enumerate(activated_strats):
            # updating pair_strat_params
            pair_strat = \
                PairStratBaseModel(_id=activated_strat.id, strat_limits=StratLimitsOptional(max_concentration=index))
            updates_pair_strat = strat_manager_service_web_client.patch_pair_strat_client(pair_strat)
            assert updates_pair_strat.strat_limits_update_seq_num == \
                   activated_strat.strat_limits_update_seq_num + 1, \
                f"Mismatched strat_limits_update_seq_num: expected " \
                f"{activated_strat.strat_limits_update_seq_num + 1}, received " \
                f"{updates_pair_strat.strat_limits_update_seq_num}"


def test_portfolio_status_alert_updates(clean_and_set_limits, sample_alert):
    with ExecutorNLogAnalyzerManager():
        stored_portfolio_status = strat_manager_service_web_client.get_portfolio_status_client(portfolio_status_id=1)

        alert = copy.deepcopy(sample_alert)
        portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1, portfolio_alerts=[alert])
        updated_portfolio_status = \
            strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_basemodel)
        assert stored_portfolio_status.alert_update_seq_num + 1 == updated_portfolio_status.alert_update_seq_num, \
            f"Mismatched alert_update_seq_num: expected {stored_portfolio_status.alert_update_seq_num + 1}, " \
            f"received {updated_portfolio_status.alert_update_seq_num}"

        max_loop_count = 5
        for loop_count in range(max_loop_count):
            alert.alert_brief = f"Test update - {loop_count}"
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1, portfolio_alerts=[alert])
            alert_updated_portfolio_status = \
                strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_basemodel)
            assert updated_portfolio_status.alert_update_seq_num + (loop_count + 1) == \
                   alert_updated_portfolio_status.alert_update_seq_num, \
                f"Mismatched alert_update_seq_num: expected " \
                f"{updated_portfolio_status.alert_update_seq_num + (loop_count + 1)}, " \
                f"received {alert_updated_portfolio_status.alert_update_seq_num}"


def test_cxl_order_cxl_confirmed_status(clean_and_set_limits, buy_sell_symbol_list,
                                        pair_strat_, expected_strat_limits_,
                                        expected_start_status_, symbol_overview_obj_list,
                                        last_trade_fixture_list, market_depth_basemodel_list,
                                        top_of_book_list_, buy_order_, sell_order_,
                                        max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            # buy fills check
            order_id = None
            cxl_order_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
                run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
                time.sleep(2)  # delay for order to get placed

                new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                                    buy_symbol, last_order_id=order_id)
                order_id = new_order_journal.order.order_id

                # wait to get unfilled order qty cancelled
                time.sleep(residual_wait_sec)

                cxl_ack_order_journal = \
                    get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK, buy_symbol,
                                                                    last_order_id=cxl_order_id, loop_wait_secs=1,
                                                                    max_loop_count=1)
                cxl_order_id = cxl_ack_order_journal.order.order_id
                assert new_order_journal.order.order_id == cxl_ack_order_journal.order.order_id, \
                    "Mismatch order_id, Must have received cxl_ack of same order_journal obj that got created since " \
                    "no new order created in this test"

                cxl_order_list = []
                cxl_order_obj_list = strat_manager_service_web_client.get_all_cancel_order_client()
                for cxl_order_obj in cxl_order_obj_list:
                    if cxl_order_obj.order_id == cxl_order_id:
                        cxl_order_list.append(cxl_order_obj)

                assert len(cxl_order_list) == 1, f"Unexpected length of cxl_order_list: expected 1, " \
                                                 f"received {len(cxl_order_list)}"
                assert cxl_order_list[0].cxl_confirmed, f"Unexpected cxl_confirmed field value, expected True, " \
                                                        f"received False"

            # sell fills check
            order_id = None
            cxl_order_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
                run_sell_top_of_book(sell_symbol)
                time.sleep(2)  # delay for order to get placed

                new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                                    sell_symbol, last_order_id=order_id)
                order_id = new_order_journal.order.order_id

                # wait to get unfilled order qty cancelled
                time.sleep(residual_wait_sec)

                cxl_ack_order_journal = \
                    get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK, sell_symbol,
                                                                    last_order_id=cxl_order_id, loop_wait_secs=1,
                                                                    max_loop_count=1)
                cxl_order_id = cxl_ack_order_journal.order.order_id
                assert new_order_journal.order.order_id == cxl_ack_order_journal.order.order_id, \
                    "Mismatch order_id, Must have received cxl_ack of same order_journal obj that got created since " \
                    "no new order created in this test"

                cxl_order_list = []
                cxl_order_obj_list = strat_manager_service_web_client.get_all_cancel_order_client()
                for cxl_order_obj in cxl_order_obj_list:
                    if cxl_order_obj.order_id == cxl_order_id:
                        cxl_order_list.append(cxl_order_obj)

                assert len(cxl_order_list) == 1, f"Unexpected length of cxl_order_list: expected 1, " \
                                                 f"received {len(cxl_order_list)}"
                assert cxl_order_list[0].cxl_confirmed, f"Unexpected cxl_confirmed field value, expected True, " \
                                                        f"received False"


def test_partial_ack(clean_and_set_limits, config_dict, pair_strat_,
                     expected_strat_limits_, top_of_book_list_,
                     expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                     market_depth_basemodel_list, buy_sell_symbol_list):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["ack_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        partial_ack_qty: int | None = None

        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_start_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list)

            # buy fills check
            new_order_id = None
            acked_order_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
                run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
                time.sleep(2)  # delay for order to get placed

                new_order_id, acked_order_id, partial_ack_qty = \
                    handle_partial_ack_checks(buy_symbol, new_order_id, acked_order_id)

            time.sleep(5)
            pair_strat_obj = get_pair_strat_from_symbol(buy_symbol)
            assert partial_ack_qty * max_loop_count_per_side == pair_strat_obj.strat_status.total_fill_buy_qty, \
                f"Mismatched total_fill_buy_qty: Expected {partial_ack_qty * max_loop_count_per_side}, " \
                f"received {pair_strat_obj.strat_status.total_fill_buy_qty}"

            # sell fills check
            new_order_id = None
            acked_order_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
                run_sell_top_of_book(sell_symbol)
                time.sleep(2)

                new_order_id, acked_order_id, partial_ack_qty = \
                    handle_partial_ack_checks(sell_symbol, new_order_id, acked_order_id)

            time.sleep(5)
            pair_strat_obj = get_pair_strat_from_symbol(sell_symbol)
            assert partial_ack_qty * max_loop_count_per_side == pair_strat_obj.strat_status.total_fill_sell_qty, \
                f"Mismatched total_fill_sell_qty: Expected {partial_ack_qty * max_loop_count_per_side}, " \
                f"received {pair_strat_obj.strat_status.total_fill_sell_qty}"


def test_update_residual_query(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                               expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                               market_depth_basemodel_list, top_of_book_list_):
    with ExecutorNLogAnalyzerManager():
        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list, market_depth_basemodel_list)

        total_loop_count = 5
        residual_qty = 5

        # creating tobs
        run_buy_top_of_book(1, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)

        # Since both side have same last trade px in test cases
        last_trade_px = top_of_book_list_[0].get("last_trade").get("px")

        for loop_count in range(total_loop_count):
            # buy side
            strat_manager_service_web_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)
            pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
            strat_brief_list = strat_manager_service_web_client.get_all_strat_brief_client()

            # since only one strat is created in this test
            pair_strat = pair_strat_list[0]
            strat_brief = strat_brief_list[0]

            residual_notional = residual_qty * get_px_in_usd(last_trade_px)
            assert residual_qty * (loop_count + 1) == strat_brief.pair_buy_side_trading_brief.residual_qty, \
                f"Mismatch residual_qty: expected {residual_qty * (loop_count + 1)} received " \
                f"{strat_brief.pair_buy_side_trading_brief.residual_qty}"
            assert residual_notional == pair_strat.strat_status.residual.residual_notional, \
                f"Mismatch residual_notional, expected {residual_notional}, received " \
                f"{pair_strat.strat_status.residual.residual_notional}"

            # sell side
            strat_manager_service_web_client.update_residuals_query_client(sell_symbol, Side.SELL, residual_qty)
            pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
            strat_brief_list = strat_manager_service_web_client.get_all_strat_brief_client()

            # since only one strat is created in this test
            pair_strat = pair_strat_list[0]
            strat_brief = strat_brief_list[0]

            assert residual_qty * (loop_count + 1) == strat_brief.pair_sell_side_trading_brief.residual_qty, \
                f"Mismatch residual_qty: expected {residual_qty * (loop_count + 1)}, received " \
                f"{strat_brief.pair_sell_side_trading_brief.residual_qty}"
            assert pair_strat.strat_status.residual.residual_notional == 0, \
                f"Mismatch residual_notional: expected 0 received {pair_strat.strat_status.residual.residual_notional}"


def test_post_unack_unsol_cxl(clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, buy_order_, sell_order_,
                              max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_orders"] = True
        config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
        config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]

        # explicitly setting waived_min_orders to 10 for this test case
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # buy test
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
        loop_count = 1
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)

        latest_unack_obj = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW, buy_symbol)
        latest_cxl_ack_obj = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK, buy_symbol)

        TradeSimulator.process_order_ack(latest_unack_obj.order.order_id,
                                         latest_unack_obj.order.px,
                                         latest_unack_obj.order.qty,
                                         latest_unack_obj.order.side,
                                         latest_unack_obj.order.security.sec_id,
                                         latest_unack_obj.order.underlying_account)

        order_snapshot = get_order_snapshot_from_order_id(latest_unack_obj.order.order_id)
        assert order_snapshot.filled_qty == 0, f"Mismatch order_snapshot.filled_qty, expected 0, " \
                                               f"received {order_snapshot.filled_qty}"
        assert order_snapshot.cxled_qty == order_snapshot.order_brief.qty, \
            f"Mismatch order_snapshot.cxled_qty: expected {order_snapshot.order_brief.qty}, received " \
            f"{order_snapshot.cxled_qty}"
        assert order_snapshot.order_status == OrderStatusType.OE_DOD, \
            f"Mismatch order_snapshot.order_status: expected OrderStatusType.OE_DOD, " \
            f"received {order_snapshot.order_status}"

        pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
        assert len(pair_strat_list) == 1, "Expected exactly one pair_strat as only one start exists for this test, " \
                                          f"received {len(pair_strat_list)}, pair_strat_list: {pair_strat_list}"
        # since only one strat in this test
        pair_strat_list = pair_strat_list[0]
        assert len(pair_strat_list.strat_status.strat_alerts) == 0, \
            "Unexpected alerts found in pair_strat.strat_status, expected no alert for this test"


def test_get_ongoing_strat_from_symbol_side_query(clean_and_set_limits, buy_sell_symbol_list,
                                                  pair_strat_, expected_strat_limits_,
                                                  expected_start_status_, symbol_overview_obj_list,
                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                  top_of_book_list_, buy_order_, sell_order_, config_dict):
    with ExecutorNLogAnalyzerManager():
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            activated_strat = create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_,
                                                      expected_strat_limits_, expected_start_status_)
            # buy check
            ongoing_strat_list = \
                strat_manager_service_web_client.get_ongoing_strat_from_symbol_side_query_client(buy_symbol, Side.BUY)
            assert len(ongoing_strat_list) == 1, \
                f"Expected exact one ongoing strat since only single strat got created in this test, " \
                f"received {len(ongoing_strat_list)}, ongoing_strat_list: {ongoing_strat_list}"
            assert ongoing_strat_list[0] == activated_strat, f"Mismatch ongoing Strat: expected {activated_strat}, " \
                                                             f"received {ongoing_strat_list[0]}"

            # sell check
            ongoing_strat_list = strat_manager_service_web_client.get_ongoing_strat_from_symbol_side_query_client(sell_symbol,
                                                                                                            Side.SELL)
            assert len(ongoing_strat_list) == 1, \
                f"Expected exact one ongoing strat since only single strat got created in this test, " \
                f"received {len(ongoing_strat_list)}, ongoing_strat_list: {ongoing_strat_list}"
            assert ongoing_strat_list[0] == activated_strat, f"Mismatch ongoing Strat: expected {activated_strat}, " \
                                                             f"received {ongoing_strat_list[0]}"


# strat pause tests
def test_strat_pause_on_residual_notional_breach(clean_and_set_limits, buy_sell_symbol_list,
                                                 pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_, buy_order_, sell_order_, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        expected_strat_limits_.residual_restriction.max_residual = 0
        underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_)

        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]

        residual_qty = 10
        strat_manager_service_web_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "residual notional: .* > max residual"
        assert_fail_message = "Could not find any alert containing message to block orders " \
                              "due to residual notional breach"
        # placing new non-systematic new_order
        place_new_order(buy_symbol, Side.BUY, px, qty)
        print(f"symbol: {buy_symbol}, Created new_order obj")

        new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW, buy_symbol)
        pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
        # since only one strat exists for current test
        assert len(pair_strat_list) == 1, "Expected single strat since only single strat got created in this test, " \
                                          f"received {pair_strat_list}"
        pair_strat_obj = pair_strat_list[0]

        for alert in pair_strat_obj.strat_status.strat_alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            assert False, assert_fail_message
        assert True


def test_strat_pause_on_less_buy_consumable_cxl_qty_without_fill(clean_and_set_limits, buy_sell_symbol_list,
                                                                 pair_strat_, expected_strat_limits_,
                                                                 expected_start_status_, symbol_overview_obj_list,
                                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                                 top_of_book_list_, buy_order_, sell_order_,
                                                                 config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
        config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
        config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
             top_of_book_list_, Side.BUY)


def test_strat_pause_on_less_sell_consumable_cxl_qty_without_fill(clean_and_set_limits, buy_sell_symbol_list,
                                                                  pair_strat_, expected_strat_limits_,
                                                                  expected_start_status_, symbol_overview_obj_list,
                                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                                  top_of_book_list_, buy_order_, sell_order_,
                                                                  config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
        config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
        config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.SELL)


def test_strat_pause_on_less_buy_consumable_cxl_qty_with_fill(clean_and_set_limits, buy_sell_symbol_list,
                                                              pair_strat_, expected_strat_limits_,
                                                              expected_start_status_, symbol_overview_obj_list,
                                                              last_trade_fixture_list, market_depth_basemodel_list,
                                                              top_of_book_list_, buy_order_, sell_order_,
                                                              config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 80
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.BUY)


def test_strat_pause_on_less_sell_consumable_cxl_qty_with_fill(clean_and_set_limits, buy_sell_symbol_list,
                                                               pair_strat_, expected_strat_limits_,
                                                               expected_start_status_, symbol_overview_obj_list,
                                                               last_trade_fixture_list, market_depth_basemodel_list,
                                                               top_of_book_list_, buy_order_, sell_order_,
                                                               config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 80
    update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.SELL)


def test_drop_test_environment():
    drop_mongo_collections(mongo_server_uri="mongodb://localhost:27017", database_name="addressbook_test",
                           ignore_collections=["UILayout"])
    drop_mongo_collections(mongo_server_uri="mongodb://localhost:27017", database_name="market_data_test_fixture",
                           ignore_collections=["UILayout"])


def test_clear_test_environment():
    clean_mongo_collections(mongo_server_uri="mongodb://localhost:27017", database_name="addressbook_test",
                            ignore_collections=["UILayout"])
    clean_mongo_collections(mongo_server_uri="mongodb://localhost:27017", database_name="market_data_test_fixture",
                            ignore_collections=["UILayout"])
