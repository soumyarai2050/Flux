import time
import copy
from pathlib import PurePath
import pytest
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient

from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from tests.CodeGenProjects.addressbook.app.test_strat_manager_service_routes_callback_override import \
    create_n_validate_strat, create_if_not_exists_and_validate_strat_collection, run_buy_top_of_book, \
    run_sell_top_of_book, TopOfBookSide, run_symbol_overview, run_last_trade, create_market_depth, \
    wait_for_get_new_order_placed_from_tob

PAIR_STRAT_DATA_DIR = (
        PurePath(
            __file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "addressbook" / "data"
)


@pytest.fixture
def config_dict():
    config_file_path: PurePath = PAIR_STRAT_DATA_DIR / "config.yaml"
    config_dict = load_yaml_configurations(str(config_file_path))
    config_dict["simulate_reverse_path"] = True
    yield config_dict


def set_trade_simulator(config_dict):
    TradeSimulator.simulate_reverse_path = config_dict["simulate_reverse_path"]


def create_pair_strat_n_strat_collection(pair_strat, strat_limits, strat_status):
    # Creating Strat
    active_pair_strat = create_n_validate_strat(pair_strat, strat_limits, strat_status)
    # Adding strat in strat_collection
    create_if_not_exists_and_validate_strat_collection(active_pair_strat)
    return active_pair_strat


def place_buy_order(buy_order, loop_count, top_of_book_list):
    current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order)
    current_itr_expected_buy_order_journal_.order.order_id = f"O{loop_count}"
    # Running TopOfBook (this triggers expected buy order)
    run_buy_top_of_book(loop_count, top_of_book_list)


def place_sell_order(sell_order, loop_count):
    current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order)
    current_itr_expected_sell_order_journal_.order.order_id = f"O{loop_count}"
    # Running TopOfBook (this triggers expected sell order)
    run_sell_top_of_book()


def override_strat_limits(strat_limits):
    return strat_limits


def override_pair_strat(pair_strat):
    return pair_strat


def override_order_limits(strat_manager_service_web_client: StratManagerServiceWebClient):
    pass


def override_sell_order(sell_order):
    return sell_order


def test_place_order_and_check_fill(strat_manager_service_web_client_, pair_strat_, expected_start_status_,
                                    expected_strat_limits_, top_of_book_list_, buy_order_, sell_order_,
                                    symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                                    config_dict):
    """
    Send order and verify that it is fully filled using TradeSimulator by setting simulate_reverse_path as True
    """
    set_trade_simulator(config_dict)
    # running symbol overview
    run_symbol_overview(symbol_overview_obj_list)
    # run last trade
    run_last_trade(last_trade_fixture_list)
    # create market depth
    create_market_depth(market_depth_basemodel_list)
    # override order limits
    override_order_limits(strat_manager_service_web_client_)

    pair_strat_ = override_pair_strat(pair_strat_)
    expected_strat_limits_ = override_strat_limits(expected_strat_limits_)
    create_pair_strat_n_strat_collection(pair_strat_, expected_strat_limits_, expected_start_status_)

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    total_loop_count = 30
    # sending buy sell orders
    for loop_count in range(1, total_loop_count + 1):
        order_count = 2 * loop_count - 1
        order_id = f"O{order_count}"
        place_buy_order(buy_order_, order_count, top_of_book_list_)

        # Waiting for tob to trigger place order
        buy_tob_last_update_date_time_tracker = \
            wait_for_get_new_order_placed_from_tob(110, buy_tob_last_update_date_time_tracker, Side.BUY)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_NEW and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal = stored_order_journal
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_NEW}, order_id: {order_id}"
        assert placed_order_journal.order_event == OrderEventType.OE_NEW
        assert placed_order_journal.order.order_id == order_id

        time.sleep(2)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_ack = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_ACK and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal_ack = stored_order_journal
        assert placed_order_journal_ack is not None, f"Can't find any order_journal with order_event: " \
                                                     f"{OrderEventType.OE_ACK}, order_id: {order_id}"
        assert placed_order_journal_ack.order.order_id == order_id

        placed_fill_journal = strat_manager_service_web_client_.get_all_fills_journal_client()[-1]
        assert placed_fill_journal.order_id == order_id
        assert placed_fill_journal.fill_px == buy_order_.order.px
        assert placed_fill_journal.fill_qty == buy_order_.order.qty  # fully filled

        # sell order
        order_count += 1
        order_id = f"O{order_count}"
        place_sell_order(sell_order_, order_count)

        # Waiting for tob to trigger place order
        sell_tob_last_update_date_time_tracker = \
            wait_for_get_new_order_placed_from_tob(120, sell_tob_last_update_date_time_tracker, Side.SELL)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_NEW and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal = stored_order_journal
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_NEW}, order_id: {order_id}"
        assert placed_order_journal.order_event == OrderEventType.OE_NEW
        assert placed_order_journal.order.order_id == order_id

        time.sleep(2)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_ack = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_ACK and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal_ack = stored_order_journal
        assert placed_order_journal_ack is not None, f"Can't find any order_journal with order_event: " \
                                                     f"{OrderEventType.OE_ACK}, order_id: {order_id}"
        assert placed_order_journal_ack.order.order_id == order_id

        placed_fill_journal = strat_manager_service_web_client_.get_all_fills_journal_client()[-1]
        assert placed_fill_journal.order_id == order_id
        assert placed_fill_journal.fill_px == sell_order_.order.px
        assert placed_fill_journal.fill_qty == sell_order_.order.qty  # fully filled

        if loop_count % 5 == 0:
            # run last trade
            run_last_trade(last_trade_fixture_list)


def test_max_cancel_rate(strat_manager_service_web_client_, pair_strat_, expected_start_status_,
                         expected_strat_limits_, top_of_book_list_, buy_order_, sell_order_,
                         symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list):
    # running symbol overview
    run_symbol_overview(symbol_overview_obj_list)
    # run last trade
    run_last_trade(last_trade_fixture_list)
    # create market depth
    create_market_depth(market_depth_basemodel_list)
    # override order limits
    override_order_limits(strat_manager_service_web_client_)

    pair_strat_ = override_pair_strat(pair_strat_)
    expected_strat_limits_ = override_strat_limits(expected_strat_limits_)
    active_pair_strat = create_pair_strat_n_strat_collection(pair_strat_, expected_strat_limits_,
                                                             expected_start_status_)

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None

    max_cancel_rate = active_pair_strat.strat_limits.cancel_rate.max_cancel_rate
    waived_min_orders = active_pair_strat.strat_limits.cancel_rate.waived_min_orders

    total_loop_count = waived_min_orders + 1
    for loop_count in range(1, total_loop_count + 1):
        order_count = loop_count
        order_id = f"O{order_count}"
        place_buy_order(buy_order_, order_count, top_of_book_list_)

        # Waiting for tob to trigger place order
        buy_tob_last_update_date_time_tracker = \
            wait_for_get_new_order_placed_from_tob(110, buy_tob_last_update_date_time_tracker, Side.BUY)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_NEW and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal = stored_order_journal
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_NEW}, order_id: {order_id}"
        assert placed_order_journal.order_event == OrderEventType.OE_NEW
        assert placed_order_journal.order.order_id == order_id

        TradeSimulator.process_order_ack(order_id, buy_order_.order.px, buy_order_.order.qty,
                                         buy_order_.order.side, buy_order_.order.security.sec_id,
                                         buy_order_.order.underlying_account)

        time.sleep(2)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_ack = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_ACK and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal_ack = stored_order_journal
        assert placed_order_journal_ack is not None, f"Can't find any order_journal with order_event: " \
                                                     f"{OrderEventType.OE_ACK}, order_id: {order_id}"
        assert placed_order_journal_ack.order_event == OrderEventType.OE_ACK
        assert placed_order_journal_ack.order.order_id == order_id

        # cancel the order
        TradeSimulator.place_cxl_order(order_id, buy_order_.order.side, buy_order_.order.security.sec_id,
                                       buy_order_.order.underlying_account)

        time.sleep(2)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_cxl = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_CXL_ACK and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal_cxl = stored_order_journal
        assert placed_order_journal_cxl is not None, f"Can't find any order_journal with order_event: " \
                                                     f"{OrderEventType.OE_CXL_ACK}, order_id: {order_id}"
        assert placed_order_journal_cxl.order_event == OrderEventType.OE_CXL_ACK
        assert placed_order_journal_cxl.order.order_id == order_id

        pair_strat = strat_manager_service_web_client_.get_pair_strat_client(active_pair_strat.id)
        if loop_count > waived_min_orders:
            # cancel rate exceeded
            assert pair_strat.strat_status.strat_state == StratState.StratState_PAUSED
        else:
            assert pair_strat.strat_status.strat_state == StratState.StratState_ACTIVE


def test_max_open_orders_per_side(strat_manager_service_web_client_, pair_strat_, expected_start_status_,
                                  expected_strat_limits_, top_of_book_list_, buy_order_, sell_order_,
                                  symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list):
    # running symbol overview
    run_symbol_overview(symbol_overview_obj_list)
    # run last trade
    run_last_trade(last_trade_fixture_list)
    # create market depth
    create_market_depth(market_depth_basemodel_list)
    # override order limits
    override_order_limits(strat_manager_service_web_client_)

    pair_strat_ = override_pair_strat(pair_strat_)
    expected_strat_limits_ = override_strat_limits(expected_strat_limits_)
    active_pair_strat = create_pair_strat_n_strat_collection(pair_strat_, expected_strat_limits_,
                                                             expected_start_status_)

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    max_open_orders_per_side = active_pair_strat.strat_limits.max_open_orders_per_side
    total_loop_count = max_open_orders_per_side + 1

    for loop_count in range(1, total_loop_count + 1):
        order_count = loop_count
        order_id = f"O{order_count}"
        place_buy_order(buy_order_, order_count, top_of_book_list_)

        # Waiting for tob to trigger place order
        buy_tob_last_update_date_time_tracker = \
            wait_for_get_new_order_placed_from_tob(110, buy_tob_last_update_date_time_tracker, Side.BUY)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_NEW and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal = stored_order_journal
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_NEW}, order_id: {order_id}"
        assert placed_order_journal.order_event == OrderEventType.OE_NEW
        assert placed_order_journal.order.order_id == order_id

        TradeSimulator.process_order_ack(order_id, buy_order_.order.px, buy_order_.order.qty,
                                         buy_order_.order.side, buy_order_.order.security.sec_id,
                                         buy_order_.order.underlying_account)

        time.sleep(2)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_ack = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_ACK and \
                    stored_order_journal.order.order_id == order_id:
                placed_order_journal_ack = stored_order_journal
        assert placed_order_journal_ack is not None, f"Can't find any order_journal with order_event: " \
                                                     f"{OrderEventType.OE_ACK}, order_id: {order_id}"
        assert placed_order_journal_ack.order_event == OrderEventType.OE_ACK
        assert placed_order_journal_ack.order.order_id == order_id

        time.sleep(5)

        pair_strat = strat_manager_service_web_client_.get_pair_strat_client(active_pair_strat.id)
        if loop_count > max_open_orders_per_side:
            # max_order_per_side limit is crossed
            assert pair_strat.strat_status.strat_state == StratState.StratState_PAUSED
        else:
            assert pair_strat.strat_status.strat_state == StratState.StratState_ACTIVE


def test_consumable_cxl_qty(strat_manager_service_web_client_, pair_strat_, expected_start_status_,
                            expected_strat_limits_, buy_order_, top_of_book_list_,
                            pair_securities_with_sides_, expected_strat_brief_, buy_fill_journal_):
    active_pair_strat = util_create_pair_strat_n_strat_collection(pair_strat_, expected_strat_limits_,
                                                                  expected_start_status_)

    buy_symbol = pair_securities_with_sides_["security1"]["sec_id"]
    total_loop_count = 10
    cxl_threshold = 2

    for loop_count in range(1, total_loop_count + 1):
        # placing order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.order_id = f"O{loop_count}"

        # Running TopOfBook (this triggers expected buy order)
        run_top_of_book(loop_count, top_of_book_list_, TopOfBookSide.Bid)

        time.sleep(1)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_NEW:
                placed_order_journal = stored_order_journal
        assert placed_order_journal is not None, "Can't find any order_journal with order_event OE_NEW"
        assert placed_order_journal.order_event == OrderEventType.OE_NEW

        order_id: str = f"O{loop_count}"
        TradeSimulator.process_order_ack(order_id, current_itr_expected_buy_order_journal_.order.px,
                                         current_itr_expected_buy_order_journal_.order.qty,
                                         current_itr_expected_buy_order_journal_.order.side,
                                         current_itr_expected_buy_order_journal_.order.security.sec_id,
                                         current_itr_expected_buy_order_journal_.order.underlying_account)

        time.sleep(1)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_ack = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_ACK:
                placed_order_journal_ack = stored_order_journal

        assert placed_order_journal_ack is not None, "Can't find any order_journal with order_event OE_ACK"
        assert placed_order_journal_ack.order.order_id == order_id

        if loop_count <= cxl_threshold:
            buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
            TradeSimulator.process_fill(order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
                                        Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)
        else:
            # cancel the order
            TradeSimulator.place_cxl_order(order_id, current_itr_expected_buy_order_journal_.order.side,
                                           current_itr_expected_buy_order_journal_.order.security.sec_id,
                                           current_itr_expected_buy_order_journal_.order.underlying_account)
        # cancel the order
        TradeSimulator.place_cxl_order(order_id, current_itr_expected_buy_order_journal_.order.side,
                                       current_itr_expected_buy_order_journal_.order.security.sec_id,
                                       current_itr_expected_buy_order_journal_.order.underlying_account)

        time.sleep(1)

        stored_order_journal_list = strat_manager_service_web_client_.get_all_order_journal_client()
        placed_order_journal_cxl = None
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == OrderEventType.OE_CXL_ACK:
                placed_order_journal_cxl = stored_order_journal
        assert placed_order_journal_cxl is not None, "Can't find any order_journal with order_event OE_CXL_ACK"
        assert placed_order_journal_cxl.order.order_id == order_id

        pair_strat = strat_manager_service_web_client_.get_pair_strat_client(active_pair_strat.id)
        expected_strat_brief = copy.deepcopy(expected_strat_brief_)

        if expected_strat_brief.pair_buy_side_trading_brief.consumable_cxl_qty < 0:
            assert pair_strat.strat_status.strat_state == StratState.StratState_PAUSED
        else:
            assert pair_strat.strat_status.strat_state == StratState.StratState_ACTIVE
