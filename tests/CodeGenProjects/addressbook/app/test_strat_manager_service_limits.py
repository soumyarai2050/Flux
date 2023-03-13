from datetime import datetime
import time
import copy

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from tests.CodeGenProjects.addressbook.app.test_strat_manager_service_routes_callback_override import \
    create_n_validate_strat, create_if_not_exists_and_validate_strat_collection, run_top_of_book, TopOfBookSide


def util_create_pair_strat_n_strat_collection(pair_strat, strat_limits, strat_status):
    # Creating Strat
    active_pair_strat = create_n_validate_strat(pair_strat, strat_limits, strat_status)
    # Adding strat in strat_collection
    create_if_not_exists_and_validate_strat_collection(active_pair_strat)
    return active_pair_strat


def test_max_cancel_rate(strat_manager_service_web_client_, pair_strat_, expected_strat_limits_, expected_start_status_,
                         top_of_book_list_, buy_order_):
    active_pair_strat = util_create_pair_strat_n_strat_collection(pair_strat_, expected_strat_limits_,
                                                                  expected_start_status_)

    max_cancel_rate = active_pair_strat.strat_limits.cancel_rate.max_cancel_rate
    waived_min_orders = active_pair_strat.strat_limits.cancel_rate.waived_min_orders
    total_loop_count = waived_min_orders + 2

    for loop_count in range(1, total_loop_count):
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

        if loop_count > waived_min_orders:
            # cancel rate exceeded
            assert pair_strat.strat_status.strat_state == StratState.StratState_PAUSED
        else:
            assert pair_strat.strat_status.strat_state == StratState.StratState_ACTIVE


def test_max_open_orders_per_side(strat_manager_service_web_client_, pair_strat_, expected_strat_limits_,
                                  expected_start_status_, buy_order_, top_of_book_list_):
    active_pair_strat = util_create_pair_strat_n_strat_collection(pair_strat_, expected_strat_limits_,
                                                                  expected_start_status_)

    max_open_orders_per_side = active_pair_strat.strat_limits.max_open_orders_per_side
    total_loop_count = max_open_orders_per_side + 2

    for loop_count in range(1, total_loop_count):
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

        pair_strat = strat_manager_service_web_client_.get_pair_strat_client(active_pair_strat.id)

        if loop_count > max_open_orders_per_side:
            # max_order_per_side limit is crossed
            assert pair_strat.strat_status.strat_state == StratState.StratState_PAUSED
        else:
            assert pair_strat.strat_status.strat_state == StratState.StratState_ACTIVE


def test_consumable_cxl_qty(strat_manager_service_web_client_, pair_strat_, expected_start_status_,
                            expected_strat_limits_, buy_order_, top_of_book_list_,
                            pair_securities_with_sides_, expected_strat_brief_):
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
