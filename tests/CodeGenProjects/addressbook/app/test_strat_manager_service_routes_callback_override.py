# standard imports
import math
import concurrent.futures
import re
import numpy as np
import pendulum
import pexpect
import pytest
import random

# project imports
from tests.CodeGenProjects.addressbook.app.utility_test_functions import *
from Flux.CodeGenProjects.addressbook.app.trading_link_base import config_file_path
from FluxPythonUtils.scripts.utility_functions import drop_mongo_collections, parse_to_float


strat_manager_service_beanie_web_client: StratManagerServiceWebClient = \
    StratManagerServiceWebClient.set_or_get_if_instance_exists(HOST, parse_to_int(PAIR_STRAT_BEANIE_PORT))
strat_manager_service_cache_web_client: StratManagerServiceWebClient = \
    StratManagerServiceWebClient.set_or_get_if_instance_exists(HOST, parse_to_int(PAIR_STRAT_CACHE_PORT))

if strat_manager_service_beanie_web_client.port == strat_manager_service_native_web_client.port:
    clients_list = [strat_manager_service_beanie_web_client]
else:
    clients_list = [strat_manager_service_beanie_web_client, strat_manager_service_cache_web_client]


def test_clean_and_set_limits(clean_and_set_limits):
    pass


@pytest.mark.parametrize("web_client", clients_list)
def test_create_get_put_patch_delete_order_limits_client(clean_and_set_limits, web_client):
    order_limits_obj = OrderLimitsBaseModel(id=2, max_px_deviation=2)
    # testing create_order_limits_client()
    created_order_limits_obj = web_client.create_order_limits_client(order_limits_obj)
    assert created_order_limits_obj == order_limits_obj, \
        f"Created obj {created_order_limits_obj} mismatched expected order_limits_obj {order_limits_obj}"

    # checking if created obj present in get_all objects
    fetched_order_limits_list = web_client.get_all_order_limits_client()
    assert order_limits_obj in fetched_order_limits_list, \
        f"Couldn't find expected order_limits_obj {order_limits_obj} in get-all fetched list of objects"

    # Checking get_by_id client
    fetched_order_limits_obj = web_client.get_order_limits_client(order_limits_obj.id)
    assert fetched_order_limits_obj == order_limits_obj, \
        f"Mismatched expected order_limits_obj {order_limits_obj} from " \
        f"fetched_order_limits obj fetched by get_by_id {fetched_order_limits_obj}"

    # checking put operation client
    order_limits_obj.max_basis_points = 2
    updated_order_limits_obj = web_client.put_order_limits_client(order_limits_obj)
    assert updated_order_limits_obj == order_limits_obj, \
        f"Mismatched expected order_limits_obj: {order_limits_obj} from updated obj: {updated_order_limits_obj}"

    # checking patch operation client
    patch_order_limits_obj = OrderLimitsBaseModel(id=order_limits_obj.id, max_px_levels=2)
    # making changes to expected_obj
    order_limits_obj.max_px_levels = patch_order_limits_obj.max_px_levels

    patch_updated_order_limits_obj = \
        web_client.patch_order_limits_client(json.loads(patch_order_limits_obj.json(by_alias=True, exclude_none=True)))
    assert patch_updated_order_limits_obj == order_limits_obj, \
        f"Mismatched expected obj: {order_limits_obj} from patch updated obj {patch_updated_order_limits_obj}"

    # checking delete operation client
    delete_resp = web_client.delete_order_limits_client(order_limits_obj.id)
    assert isinstance(delete_resp, dict), \
        f"Mismatched type of delete resp, expected dict received {type(delete_resp)}"
    assert delete_resp.get("id") == order_limits_obj.id, \
        f"Mismatched delete resp id, expected {order_limits_obj.id} received {delete_resp.get('id')}"


@pytest.mark.parametrize("web_client", clients_list)
def test_post_all(clean_and_set_limits, web_client):
    order_limits_objects_list = [
        OrderLimitsBaseModel(id=2, max_px_deviation=2),
        OrderLimitsBaseModel(id=3, max_px_deviation=3),
        OrderLimitsBaseModel(id=4, max_px_deviation=4)
    ]

    fetched_strat_manager_beanie = web_client.get_all_order_limits_client()

    for obj in order_limits_objects_list:
        assert obj not in fetched_strat_manager_beanie, f"Object {obj} must not be present in get-all list " \
                                                        f"{fetched_strat_manager_beanie} before post-all operation"

    web_client.create_all_order_limits_client(order_limits_objects_list)

    fetched_strat_manager_beanie = web_client.get_all_order_limits_client()

    for obj in order_limits_objects_list:
        assert obj in fetched_strat_manager_beanie, f"Couldn't find object {obj} in get-all list " \
                                                    f"{fetched_strat_manager_beanie}"


@pytest.mark.parametrize("web_client", clients_list)
def test_put_all(clean_and_set_limits, web_client):
    order_limits_objects_list = [
        OrderLimitsBaseModel(id=2, max_px_deviation=2),
        OrderLimitsBaseModel(id=3, max_px_deviation=3),
        OrderLimitsBaseModel(id=4, max_px_deviation=4)
    ]

    web_client.create_all_order_limits_client(order_limits_objects_list)

    fetched_strat_manager_beanie = web_client.get_all_order_limits_client()

    for obj in order_limits_objects_list:
        assert obj in fetched_strat_manager_beanie, f"Couldn't find object {obj} in get-all list " \
                                                    f"{fetched_strat_manager_beanie}"

    # updating values
    for obj in order_limits_objects_list:
        obj.max_contract_qty = obj.id

    web_client.put_all_order_limits_client(order_limits_objects_list)

    updated_order_limits_list = web_client.get_all_order_limits_client()

    for expected_obj in order_limits_objects_list:
        assert expected_obj in updated_order_limits_list, \
            f"expected obj {expected_obj} not found in updated list of objects: {updated_order_limits_list}"


@pytest.mark.parametrize("web_client", clients_list)
def test_patch_all(clean_and_set_limits, web_client):

    portfolio_limits_objects_list = [
        PortfolioLimitsBaseModel(id=2, max_open_baskets=20),
        PortfolioLimitsBaseModel(id=3, max_open_baskets=30),
        PortfolioLimitsBaseModel(id=4, max_open_baskets=45)
    ]

    web_client.create_all_portfolio_limits_client(portfolio_limits_objects_list)

    fetched_get_all_obj_list = web_client.get_all_portfolio_limits_client()

    for obj in portfolio_limits_objects_list:
        assert obj in fetched_get_all_obj_list, f"Couldn't find object {obj} in get-all list " \
                                                f"{fetched_get_all_obj_list}"

    # updating values
    portfolio_limits_objects_json_list = []
    for obj in portfolio_limits_objects_list:
        obj.eligible_brokers = []
        for broker_obj_id in [1, 2]:
            broker = broker_fixture()
            broker.id = f"{broker_obj_id}"
            broker.bkr_priority = broker_obj_id
            obj.eligible_brokers.append(broker)
        portfolio_limits_objects_json_list.append(jsonable_encoder(obj, by_alias=True, exclude_none=True))

    web_client.patch_all_portfolio_limits_client(portfolio_limits_objects_json_list)

    updated_portfolio_limits_list = web_client.get_all_portfolio_limits_client()

    for expected_obj in portfolio_limits_objects_list:
        assert expected_obj in updated_portfolio_limits_list, \
            f"expected obj {expected_obj} not found in updated list of objects: {updated_portfolio_limits_list}"

    delete_broker = BrokerOptional()
    delete_broker.id = "1"

    delete_obj = PortfolioLimitsBaseModel(id=4, eligible_brokers=[delete_broker])
    delete_obj_json = jsonable_encoder(delete_obj, by_alias=True, exclude_none=True)

    web_client.patch_all_portfolio_limits_client([delete_obj_json])

    updated_portfolio_limits = web_client.get_portfolio_limits_client(portfolio_limits_id=4)

    assert delete_broker.id not in [broker.id for broker in updated_portfolio_limits.eligible_brokers], \
        f"Deleted obj: {delete_obj} using patch still found in updated object: {updated_portfolio_limits}"


# sanity test to create and activate pair_strat
def test_create_pair_strat(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
                           expected_strat_limits_, expected_start_status_, symbol_overview_obj_list):
    with ExecutorNLogAnalyzerManager():
        # creates and activates multiple pair_strats
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list)
            create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                    expected_start_status_)


# sanity test to create orders
def test_place_sanity_orders(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                             expected_start_status_, symbol_overview_obj_list,
                             last_trade_fixture_list, market_depth_basemodel_list,
                             top_of_book_list_, buy_order_, sell_order_,
                             max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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


def test_create_sanity_last_trade(clean_and_set_limits, last_trade_fixture_list):
    symbols = ["CB_Sec_1", "CB_Sec_2", "CB_Sec_3", "CB_Sec_4"]
    px_portions = [(40, 55), (56, 70), (71, 85), (86, 100)]
    total_loops = 600
    loop_wait = 1   # sec

    for _ in range(total_loops):
        current_time = DateTime.utcnow()
        for index, symbol in enumerate(symbols):
            px_portion = px_portions[index]
            qty = random.randint(1000, 2000)
            qty = qty + 400

            last_trade_obj = LastTradeBaseModel(**last_trade_fixture_list[0])
            last_trade_obj.time = current_time
            last_trade_obj.symbol = symbol
            last_trade_obj.px = random.randint(px_portion[0], px_portion[1])
            last_trade_obj.qty = qty

            market_data_web_client.create_last_trade_client(last_trade_obj)

        time.sleep(loop_wait)


def test_add_brokers_to_portfolio_limits(clean_and_set_limits):
    """Adding Broker entries in portfolio limits"""

    with ExecutorNLogAnalyzerManager():
        broker = broker_fixture()

        portfolio_limits_basemodel = PortfolioLimitsBaseModel(_id=1, eligible_brokers=[broker])
        strat_manager_service_native_web_client.patch_portfolio_limits_client(
            jsonable_encoder(portfolio_limits_basemodel, by_alias=True, exclude_none=True))

        stored_portfolio_limits_ = strat_manager_service_native_web_client.get_portfolio_limits_client(1)
        for stored_broker in stored_portfolio_limits_.eligible_brokers:
            stored_broker.id = None
        broker.id = None
        assert broker in stored_portfolio_limits_.eligible_brokers, f"Couldn't find broker {broker} in " \
                                                                    f"eligible_broker " \
                                                                    f"{stored_portfolio_limits_.eligible_brokers}"


def test_buy_sell_order_multi_pair_serialized(static_data_, clean_and_set_limits, pair_securities_with_sides_,
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


def test_buy_sell_order_multi_pair_parallel(static_data_, clean_and_set_limits, pair_securities_with_sides_,
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


def test_buy_sell_non_systematic_order_multi_pair_serialized(static_data_, clean_and_set_limits, pair_securities_with_sides_,
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


def test_buy_sell_non_systematic_order_multi_pair_parallel(static_data_, clean_and_set_limits, pair_securities_with_sides_,
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


def test_validate_kill_switch_systematic(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
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
            updated_portfolio_status = strat_manager_service_native_web_client.patch_portfolio_status_client(
                jsonable_encoder(portfolio_status, by_alias=True, exclude_none=True))
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


def test_validate_kill_switch_non_systematic(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
            updated_portfolio_status = strat_manager_service_native_web_client.patch_portfolio_status_client(
                jsonable_encoder(portfolio_status, by_alias=True, exclude_none=True))
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


def test_simulated_partial_fills(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                 pair_strat_, expected_strat_limits_,
                                 expected_start_status_, symbol_overview_obj_list,
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
                                 max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        partial_filled_qty: int | None = None
        unfilled_amount: int | None = None

        # updating fixture values for this test-case
        max_loop_count_per_side = 2
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


def test_simulated_multi_partial_fills(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        partial_filled_qty: int | None = None

        # updating fixture values for this test-case
        max_loop_count_per_side = 2
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


def test_filled_status(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                       pair_strat_, expected_strat_limits_,
                       expected_start_status_, symbol_overview_obj_list,
                       last_trade_fixture_list, market_depth_basemodel_list,
                       top_of_book_list_, buy_order_, sell_order_, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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


def test_over_fill_case_1(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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
        pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
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


def test_over_fill_case_2(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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
        pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
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


def test_ack_to_rej_orders(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                           expected_start_status_, symbol_overview_obj_list,
                           last_trade_fixture_list, market_depth_basemodel_list,
                           top_of_book_list_, max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_ack_to_reject_orders"] = True
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        # updating fixture values for this test-case
        max_loop_count_per_side = 5
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        handle_rej_order_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, max_loop_count_per_side, True)


def test_unack_to_rej_orders(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                             expected_start_status_, symbol_overview_obj_list,
                             last_trade_fixture_list, market_depth_basemodel_list,
                             top_of_book_list_, max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_new_to_reject_orders"] = True

    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        # updating fixture values for this test-case
        max_loop_count_per_side = 2
        buy_sell_symbol_list = buy_sell_symbol_list[:2]

        handle_rej_order_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                              expected_start_status_, symbol_overview_obj_list,
                              last_trade_fixture_list, market_depth_basemodel_list,
                              top_of_book_list_, max_loop_count_per_side, False)


def test_cxl_rej(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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


def test_alert_handling_for_pair_strat(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                       pair_strat_, expected_strat_limits_,
                                       expected_start_status_, sample_alert, symbol_overview_obj_list):
    with ExecutorNLogAnalyzerManager():

        # creating strat
        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]
        total_loop_count = 5
        run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list)
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

            updated_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(update_pair_strat, by_alias=True, exclude_none=True))
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
            updated_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(update_pair_strat, by_alias=True, exclude_none=True))

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
            updated_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(update_pair_strat, by_alias=True, exclude_none=True))
            alert_id_list = [alert.id for alert in updated_pair_strat.strat_status.strat_alerts]
            assert alert_id not in alert_id_list, f"Unexpectedly found alert_id {alert_id} " \
                                                  f"in alert_id list {alert_id_list}"

        # deleting broker
        for broker_id in broker_id_list:
            delete_intended_broker = BrokerOptional(_id=broker_id)
            update_pair_strat = \
                PairStratBaseModel(_id=active_pair_strat.id,
                                   strat_limits=StratLimitsOptional(eligible_brokers=[delete_intended_broker]))
            updated_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(update_pair_strat, by_alias=True, exclude_none=True))
            broker_id_list = [broker.id for broker in updated_pair_strat.strat_limits.eligible_brokers]
            assert broker_id not in broker_id_list, f"Unexpectedly found broker_id {broker_id} in broker_id list " \
                                                    f"{broker_id_list}"


def test_underlying_account_cumulative_fill_qty_query(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
                    strat_manager_service_native_web_client.get_underlying_account_cumulative_fill_qty_query_client(symbol,
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


def test_last_n_sec_order_qty_sum_and_order_count(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                                  pair_strat_, expected_strat_limits_,
                                                  expected_start_status_, symbol_overview_obj_list,
                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                  top_of_book_list_, buy_fill_journal_, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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
            updated_portfolio_limits = \
                strat_manager_service_native_web_client.patch_portfolio_limits_client(portfolio_limits.dict(by_alias=True,
                                                                                                            exclude_none=True))
            assert updated_portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds == last_n_sec, \
                f"Unexpected last_n_sec value: expected {last_n_sec}, " \
                f"received {updated_portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds}"

            call_date_time = DateTime.utcnow()
            executor_check_snapshot_obj = \
                strat_manager_service_native_web_client.get_executor_check_snapshot_query_client(
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


def test_acked_unsolicited_cxl(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                               expected_start_status_, symbol_overview_obj_list,
                               last_trade_fixture_list, market_depth_basemodel_list,
                               top_of_book_list_, buy_order_, sell_order_,
                               max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_unsolicited_cxl(buy_sell_symbol_list, expected_strat_limits_, expected_start_status_, pair_strat_,
                               symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                               max_loop_count_per_side, top_of_book_list_)


def test_unacked_unsolicited_cxl(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                 expected_start_status_, symbol_overview_obj_list,
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
                                 max_loop_count_per_side, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_orders"] = True
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_unsolicited_cxl(buy_sell_symbol_list, expected_strat_limits_, expected_start_status_, pair_strat_,
                               symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                               max_loop_count_per_side, top_of_book_list_)


def test_pair_strat_update_counters(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
            updates_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
            assert updates_pair_strat.pair_strat_params_update_seq_num == \
                   activated_strat.pair_strat_params_update_seq_num + 1, \
                f"Mismatched pair_strat_params_update_seq_num: expected " \
                f"{activated_strat.pair_strat_params_update_seq_num + 1}, received " \
                f"{updates_pair_strat.pair_strat_params_update_seq_num}"

        for index, activated_strat in enumerate(activated_strats):
            # updating pair_strat_params
            pair_strat = \
                PairStratBaseModel(_id=activated_strat.id, strat_limits=StratLimitsOptional(max_concentration=index))
            updates_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
            assert updates_pair_strat.strat_limits_update_seq_num == \
                   activated_strat.strat_limits_update_seq_num + 1, \
                f"Mismatched strat_limits_update_seq_num: expected " \
                f"{activated_strat.strat_limits_update_seq_num + 1}, received " \
                f"{updates_pair_strat.strat_limits_update_seq_num}"


def test_portfolio_status_alert_updates(static_data_, clean_and_set_limits, sample_alert):
    with ExecutorNLogAnalyzerManager():
        stored_portfolio_status = strat_manager_service_native_web_client.get_portfolio_status_client(portfolio_status_id=1)

        alert = copy.deepcopy(sample_alert)
        portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1, portfolio_alerts=[alert])
        updated_portfolio_status = \
            strat_manager_service_native_web_client.patch_portfolio_status_client(
                jsonable_encoder(portfolio_status_basemodel, by_alias=True, exclude_none=True))
        assert stored_portfolio_status.alert_update_seq_num + 1 == updated_portfolio_status.alert_update_seq_num, \
            f"Mismatched alert_update_seq_num: expected {stored_portfolio_status.alert_update_seq_num + 1}, " \
            f"received {updated_portfolio_status.alert_update_seq_num}"

        max_loop_count = 5
        for loop_count in range(max_loop_count):
            alert.alert_brief = f"Test update - {loop_count}"
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1, portfolio_alerts=[alert])
            alert_updated_portfolio_status = \
                strat_manager_service_native_web_client.patch_portfolio_status_client(
                    jsonable_encoder(portfolio_status_basemodel, by_alias=True, exclude_none=True))
            assert updated_portfolio_status.alert_update_seq_num + (loop_count + 1) == \
                   alert_updated_portfolio_status.alert_update_seq_num, \
                f"Mismatched alert_update_seq_num: expected " \
                f"{updated_portfolio_status.alert_update_seq_num + (loop_count + 1)}, " \
                f"received {alert_updated_portfolio_status.alert_update_seq_num}"


def test_cxl_order_cxl_confirmed_status(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                        pair_strat_, expected_strat_limits_,
                                        expected_start_status_, symbol_overview_obj_list,
                                        last_trade_fixture_list, market_depth_basemodel_list,
                                        top_of_book_list_, buy_order_, sell_order_,
                                        max_loop_count_per_side, residual_wait_sec, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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
                cxl_order_obj_list = strat_manager_service_native_web_client.get_all_cancel_order_client()
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
                cxl_order_obj_list = strat_manager_service_native_web_client.get_all_cancel_order_client()
                for cxl_order_obj in cxl_order_obj_list:
                    if cxl_order_obj.order_id == cxl_order_id:
                        cxl_order_list.append(cxl_order_obj)

                assert len(cxl_order_list) == 1, f"Unexpected length of cxl_order_list: expected 1, " \
                                                 f"received {len(cxl_order_list)}"
                assert cxl_order_list[0].cxl_confirmed, f"Unexpected cxl_confirmed field value, expected True, " \
                                                        f"received False"


def test_partial_ack(static_data_, clean_and_set_limits, config_dict, pair_strat_,
                     expected_strat_limits_, top_of_book_list_,
                     expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                     market_depth_basemodel_list, buy_sell_symbol_list):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["ack_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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


def test_update_residual_query(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
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
            strat_manager_service_native_web_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)
            pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
            strat_brief_list = strat_manager_service_native_web_client.get_all_strat_brief_client()

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
            strat_manager_service_native_web_client.update_residuals_query_client(sell_symbol, Side.SELL, residual_qty)
            pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
            strat_brief_list = strat_manager_service_native_web_client.get_all_strat_brief_client()

            # since only one strat is created in this test
            pair_strat = pair_strat_list[0]
            strat_brief = strat_brief_list[0]

            assert residual_qty * (loop_count + 1) == strat_brief.pair_sell_side_trading_brief.residual_qty, \
                f"Mismatch residual_qty: expected {residual_qty * (loop_count + 1)}, received " \
                f"{strat_brief.pair_sell_side_trading_brief.residual_qty}"
            assert pair_strat.strat_status.residual.residual_notional == 0, \
                f"Mismatch residual_notional: expected 0 received {pair_strat.strat_status.residual.residual_notional}"


def test_post_unack_unsol_cxl(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

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

        pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
        assert len(pair_strat_list) == 1, "Expected exactly one pair_strat as only one start exists for this test, " \
                                          f"received {len(pair_strat_list)}, pair_strat_list: {pair_strat_list}"
        # since only one strat in this test
        pair_strat_list = pair_strat_list[0]
        assert len(pair_strat_list.strat_status.strat_alerts) == 0, \
            "Unexpected alerts found in pair_strat.strat_status, expected no alert for this test"


def test_get_ongoing_strat_from_symbol_side_query(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                                  pair_strat_, expected_strat_limits_,
                                                  expected_start_status_, symbol_overview_obj_list,
                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                  top_of_book_list_, buy_order_, sell_order_, config_dict):
    with ExecutorNLogAnalyzerManager():
        for buy_symbol, sell_symbol in buy_sell_symbol_list:
            run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list)
            activated_strat = create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_,
                                                      expected_strat_limits_, expected_start_status_)
            # buy check
            ongoing_strat_list = \
                strat_manager_service_native_web_client.get_ongoing_strat_from_symbol_side_query_client(buy_symbol, Side.BUY)
            assert len(ongoing_strat_list) == 1, \
                f"Expected exact one ongoing strat since only single strat got created in this test, " \
                f"received {len(ongoing_strat_list)}, ongoing_strat_list: {ongoing_strat_list}"
            assert ongoing_strat_list[0] == activated_strat, f"Mismatch ongoing Strat: expected {activated_strat}, " \
                                                             f"received {ongoing_strat_list[0]}"

            # sell check
            ongoing_strat_list = strat_manager_service_native_web_client.get_ongoing_strat_from_symbol_side_query_client(
                sell_symbol,
                Side.SELL)
            assert len(ongoing_strat_list) == 1, \
                f"Expected exact one ongoing strat since only single strat got created in this test, " \
                f"received {len(ongoing_strat_list)}, ongoing_strat_list: {ongoing_strat_list}"
            assert ongoing_strat_list[0] == activated_strat, f"Mismatch ongoing Strat: expected {activated_strat}, " \
                                                             f"received {ongoing_strat_list[0]}"


# strat pause tests
def test_strat_pause_on_residual_notional_breach(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                                 pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_, buy_order_, sell_order_, config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 50
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():

        expected_strat_limits_.residual_restriction.max_residual = 0
        underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_start_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_)

        buy_symbol = buy_sell_symbol_list[0][0]
        sell_symbol = buy_sell_symbol_list[0][1]

        residual_qty = 10
        strat_manager_service_native_web_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)

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
        pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
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


def test_strat_pause_on_less_buy_consumable_cxl_qty_without_fill(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.BUY)


def test_strat_pause_on_less_sell_consumable_cxl_qty_without_fill(static_data_, clean_and_set_limits, buy_sell_symbol_list,
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
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.SELL)


def test_strat_pause_on_less_buy_consumable_cxl_qty_with_fill(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                                              pair_strat_, expected_strat_limits_,
                                                              expected_start_status_, symbol_overview_obj_list,
                                                              last_trade_fixture_list, market_depth_basemodel_list,
                                                              top_of_book_list_, buy_order_, sell_order_,
                                                              config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 80
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.BUY)


def test_strat_pause_on_less_sell_consumable_cxl_qty_with_fill(static_data_, clean_and_set_limits, buy_sell_symbol_list,
                                                               pair_strat_, expected_strat_limits_,
                                                               expected_start_status_, symbol_overview_obj_list,
                                                               last_trade_fixture_list, market_depth_basemodel_list,
                                                               top_of_book_list_, buy_order_, sell_order_,
                                                               config_dict):
    # updating yaml_configs according to this test
    for symbol in config_dict["symbol_configs"]:
        config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
        config_dict["symbol_configs"][symbol]["fill_percent"] = 80
    YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

    with ExecutorNLogAnalyzerManager():
        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
            top_of_book_list_, Side.SELL)


def test_alert_agg_sequence(clean_and_set_limits, sample_alert):
    # Checking for alerts in portfolio_status
    with ExecutorNLogAnalyzerManager():
        stored_portfolio_status = \
            strat_manager_service_native_web_client.get_portfolio_status_client(portfolio_status_id=1)

        alert_list = []
        for _ in range(10):
            alert = copy.deepcopy(sample_alert)
            alert.id = Alert.__fields__.get("id").default_factory()
            alert.last_update_date_time = DateTime.utcnow()
            alert_list.append(alert)
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1, portfolio_alerts=[alert])
            json_obj = jsonable_encoder(portfolio_status_basemodel, by_alias=True, exclude_none=True)
            updated_portfolio_status = strat_manager_service_native_web_client.patch_portfolio_status_client(json_obj)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        agg_sorted_alerts: List[Alert] = portfolio_status_list[0].portfolio_alerts[:10]
        for alert in agg_sorted_alerts:
            alert.last_update_date_time = pendulum.parse(str(alert.last_update_date_time)).in_timezone("utc")
        for alert in alert_list:
            alert.last_update_date_time = \
                alert.last_update_date_time.replace(microsecond=
                                                    int(str(alert.last_update_date_time.microsecond)[:3] + "000"))
        for sorted_alert, expected_alert in zip(agg_sorted_alerts, list(reversed(alert_list))):
            assert sorted_alert.id == expected_alert.id, \
                f"Alert ID mismatch: expected Alert {expected_alert.id}, received {sorted_alert.id}"
            assert sorted_alert.last_update_date_time == expected_alert.last_update_date_time, \
                f"Alert Datetime mismatch: expected Alert {expected_alert}, received {sorted_alert}"


def test_routes_performance():
    latest_file_date_time_format = "YYYYMMDD"
    older_file_date_time_format = "YYYYMMDD.HHmmss"
    log_dir_path = PurePath(__file__).parent.parent.parent.parent.parent / "Flux" / \
                   "CodeGenProjects" / "addressbook" / "log"
    files_list = os.listdir(log_dir_path)

    filtered_beanie_latest_log_file_list = []
    filtered_beanie_older_log_file_list = []
    for file in files_list:
        if re.match(".*_beanie_logs_.*", file):
            if re.match(".*log$", file):
                filtered_beanie_latest_log_file_list.append(file)
            else:
                filtered_beanie_older_log_file_list.append(file)

    # getting latest 2 logs
    latest_file: str | None = None
    sec_latest_file: str | None = None
    for file in filtered_beanie_latest_log_file_list:
        # First getting latest log
        # Also setting last log other than latest as sec_latest_file
        if latest_file is None:
            latest_file = file
        else:
            latest_file_name = latest_file.split(".")[0]
            latest_file_date_time = pendulum.from_format(
                latest_file_name[len(latest_file_name)-len(latest_file_date_time_format):],
                fmt=latest_file_date_time_format
            )

            current_file_name = file.split(".")[0]
            current_file_date_time = pendulum.from_format(
                current_file_name[len(current_file_name) - len(latest_file_date_time_format):],
                fmt=latest_file_date_time_format
            )

            if current_file_date_time > latest_file_date_time:
                sec_latest_file = latest_file
                latest_file = file

    # If other log is present having .log.YYYYMMDD.HHmmss format with same data then taking
    # latest log in this category as sec_latest_file
    if any(latest_file in older_file for older_file in filtered_beanie_older_log_file_list):
        sec_latest_file = None
        for file in filtered_beanie_older_log_file_list:
            if sec_latest_file is None:
                sec_latest_file = file
            else:
                sec_latest_file_date_time = pendulum.from_format(
                    sec_latest_file[len(sec_latest_file) - len(older_file_date_time_format):],
                    fmt=older_file_date_time_format
                )

                current_file_date_time = pendulum.from_format(
                    file[len(file) - len(older_file_date_time_format):],
                    fmt=older_file_date_time_format
                )

                if current_file_date_time > sec_latest_file_date_time:
                    sec_latest_file = file

    # taking all grep found statements in log matching pattern
    pattern = "_Callable_"
    latest_file_content_list: List[str] = []
    # grep in latest file
    if latest_file:
        latest_file_path = log_dir_path / latest_file
        grep_cmd = pexpect.spawn(f"grep {pattern} {latest_file_path}")
        for line in grep_cmd:
            latest_file_content_list.append(line.decode())

    sec_latest_file_content_list: List[str] = []
    # grep in sec_latest file if exists
    if sec_latest_file:
        sec_latest_file_path = log_dir_path / sec_latest_file
        grep_cmd = pexpect.spawn(f"grep {pattern} {sec_latest_file_path}")
        for line in grep_cmd:
            sec_latest_file_content_list.append(line.decode())

    # getting set of callables to be checked in latest and last log file
    callable_name_set = set()
    for line in latest_file_content_list:
        line_space_separated = line.split(" ")
        callable_name = line_space_separated[line_space_separated.index(pattern)+1]
        callable_name_set.add(callable_name)

    # processing statement found having particular callable and getting list of all callable
    # durations and showing average of it in report
    for callable_name in callable_name_set:
        callable_time_delta_list = []
        callable_pattern = f".*{pattern} {callable_name}.*"
        for line in latest_file_content_list:
            if re.match(callable_pattern, line):
                line_space_separated = line.split(" ")
                time_delta = line_space_separated[line_space_separated.index(pattern)+3]
                callable_time_delta_list.append(parse_to_float(time_delta))
        latest_avg_delta = np.mean(callable_time_delta_list)
        print(f"Avg duration of callable {callable_name} in latest run: {latest_avg_delta:.7f}")

        # if sec_latest_file exists, processing statement found having particular callable and
        # getting list of all callable durations and showing average of it in report and
        # showing delta between latest and last callable duration average
        callable_time_delta_list = []
        for line in sec_latest_file_content_list:
            if re.match(callable_pattern, line):
                line_space_separated = line.split(" ")
                time_delta = line_space_separated[line_space_separated.index(pattern) + 3]
                callable_time_delta_list.append(parse_to_float(time_delta))
        if callable_time_delta_list:
            sec_latest_avg_delta = np.mean(callable_time_delta_list)
            print(f"Avg duration of callable {callable_name} in last run: {sec_latest_avg_delta:.7f}")
            print(f"Delta between last run and latest run for callable {callable_name}: "
                  f"{(sec_latest_avg_delta-latest_avg_delta):.7f}")


# todo: currently contains beanie http call of market data, once cache http is implemented test that too
def test_update_agg_feature_in_post_put_patch_http_call(clean_and_set_limits):
    """
    This test case contains check of update aggregate feature available in beanie port, put and patch http calls.
    Note: since post, put and patch all uses same method call for this feature and currently only
          underlying_create_market_depth_http contains this call, testing it to assume this feature is working
    """
    for side in [TickTypeEnum.BID, TickTypeEnum.ASK]:
        expected_cum_notional = 0
        expected_cum_qty = 0
        for position in range(1, 6):
            market_depth_obj = MarketDepthBaseModel()
            market_depth_obj.symbol = "CB_Sec_1"
            market_depth_obj.time = DateTime.utcnow()
            market_depth_obj.side = side
            market_depth_obj.px = position
            market_depth_obj.qty = position
            market_depth_obj.position = position

            created_market_depth_obj = market_data_web_client.create_market_depth_client(market_depth_obj)

            expected_cum_notional += (market_depth_obj.qty * market_depth_obj.px)
            assert expected_cum_notional == created_market_depth_obj.cumulative_notional, \
                f"Cumulative notional Mismatched: expected {expected_cum_notional}, " \
                f"received {created_market_depth_obj.cumulative_notional}"

            expected_cum_qty += market_depth_obj.qty
            assert expected_cum_qty == created_market_depth_obj.cumulative_qty, \
                f"Cumulative qty Mismatched: expected {expected_cum_qty}, " \
                f"received {created_market_depth_obj.cumulative_qty}"

            expected_cum_avg_px = (expected_cum_notional / expected_cum_qty)
            assert expected_cum_avg_px == created_market_depth_obj.cumulative_avg_px, \
                f"Cumulative avg px Mismatched: expected {expected_cum_avg_px}, " \
                f"received {created_market_depth_obj.cumulative_avg_px}"


def test_get_max_id_query(clean_and_set_limits):
    order_limits_max_id = strat_manager_service_native_web_client.get_order_limits_max_id_client()
    assert order_limits_max_id.max_id_val == 1, f"max_id mismatch, expected 1 received {order_limits_max_id.max_id_val}"

    order_limits_basemodel = OrderLimitsBaseModel()
    created_order_limits_obj = strat_manager_service_native_web_client.create_order_limits_client(order_limits_basemodel)

    order_limits_max_id = strat_manager_service_native_web_client.get_order_limits_max_id_client()
    assert order_limits_max_id.max_id_val == created_order_limits_obj.id, \
        f"max_id mismatch, expected {created_order_limits_obj.id} received {order_limits_max_id.max_id_val}"


def test_drop_test_environment():
    ps_db_name, md_db_name = get_ps_n_md_db_names(test_config_file_path)
    mongo_server_uri: str = get_mongo_server_uri()
    drop_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=ps_db_name,
                           ignore_collections=["UILayout"])
    drop_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=md_db_name,
                           ignore_collections=["UILayout"])


def test_clear_test_environment():
    ps_db_name, md_db_name = get_ps_n_md_db_names(test_config_file_path)
    clean_all_collections_ignoring_ui_layout(ps_db_name, md_db_name)

