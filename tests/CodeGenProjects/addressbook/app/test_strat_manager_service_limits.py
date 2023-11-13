from FluxPythonUtils.scripts.utility_functions import configure_logger
from tests.CodeGenProjects.addressbook.app.test_strat_manager_service_routes_callback_override import *
from CodeGenProjects.strat_executor.app.log_trade_simulator import LogTradeSimulator


def test_place_order_and_check_fill(pair_strat_, expected_start_status_,
                                    expected_strat_limits_, top_of_book_list_, buy_order_, sell_order_,
                                    symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list):
    """
    Send order and verify that it is fully filled using TradeSimulator by setting simulate_reverse_path as True
    """
    buy_symbol: str = "CB_Sec_1"
    sell_symbol: str = "EQT_Sec_1"
    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list)

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    total_loop_count = 15
    residual_wait_time = 2
    order_id = None

    # sending buy sell orders
    for loop_count in range(1, total_loop_count + 1):
        # placing buy order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, False)

        # Waiting for tob to trigger place order
        buy_tob_last_update_date_time_tracker = \
            wait_for_get_new_order_placed_from_tob(110, buy_symbol, buy_tob_last_update_date_time_tracker, Side.BUY)

        placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                               buy_symbol, last_order_id=order_id)
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_NEW}, order_id: {order_id}"
        order_id = placed_order_journal.order.order_id
        time.sleep(residual_wait_time)

        placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, buy_symbol)
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_ACK}, order_id: {order_id}"
        assert placed_order_journal.order.order_id == order_id

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id)
        assert placed_fill_journal_obj is not None
        assert placed_fill_journal_obj.order_id == order_id
        assert placed_fill_journal_obj.fill_px == buy_order_.order.px
        assert placed_fill_journal_obj.fill_qty == buy_order_.order.qty  # fully filled

        # sell order
        order_id = None

        # placing sell order
        current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)
        current_itr_expected_sell_order_journal_.order.security.sec_id = sell_symbol
        run_sell_top_of_book(buy_symbol, sell_symbol, False)

        # Waiting for tob to trigger place order
        sell_tob_last_update_date_time_tracker = \
            wait_for_get_new_order_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker, Side.SELL)

        placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                               sell_symbol, last_order_id=order_id)
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_NEW}, order_id: {order_id}"
        order_id = placed_order_journal.order.order_id
        time.sleep(residual_wait_time)

        placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, sell_symbol)
        assert placed_order_journal is not None, f"Can't find any order_journal with order_event: " \
                                                 f"{OrderEventType.OE_ACK}, order_id: {order_id}"
        assert placed_order_journal.order.order_id == order_id

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id)
        assert placed_fill_journal_obj is not None
        assert placed_fill_journal_obj.order_id == order_id
        assert placed_fill_journal_obj.fill_px == sell_order_.order.px
        assert placed_fill_journal_obj.fill_qty == sell_order_.order.qty  # fully filled

        if loop_count % 5 == 0:
            # run last trade
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)


def test_add_fake_data_to_tob(buy_sell_symbol_list, top_of_book_list_):
    # taking only one pair
    # buy_symbol, sell_symbol = buy_sell_symbol_list[0]
    id_list = []

    for loop_count in range(1000000):
        if loop_count == 0:
            for tob_json in top_of_book_list_:
                tob_obj = TopOfBookBaseModel(**tob_json)
                tob_obj.bid_quote.px = loop_count + 1
                tob_obj.bid_quote.qty = loop_count + 1
                tob_obj.ask_quote.px = loop_count + 1
                tob_obj.ask_quote.qty = loop_count + 1
                tob_obj.last_trade.px = loop_count + 1
                tob_obj.last_trade.qty = loop_count + 1

                created_tob = market_data_web_client.create_top_of_book_client(tob_obj)
                id_list.append(created_tob.id)
        else:
            for tob_id in id_list:
                quote = Quote()
                tob_obj = TopOfBookBaseModel(_id=tob_id)
                tob_obj.bid_quote = quote
                tob_obj.ask_quote = quote
                tob_obj.last_trade = quote
                tob_obj.bid_quote.px = loop_count + 1
                tob_obj.bid_quote.qty = loop_count + 1
                tob_obj.ask_quote.px = loop_count + 1
                tob_obj.ask_quote.qty = loop_count + 1
                tob_obj.last_trade.px = loop_count + 1
                tob_obj.last_trade.qty = loop_count + 1
                market_data_web_client.patch_top_of_book_client(tob_obj)


def test_log_trade_simulator_trigger_kill_switch_and_resume_trading():
    log_dir: PurePath = PurePath(
        __file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "addressbook" / "log "
    configure_logger("debug", str(log_dir), "test_log_trade_simulator.log")

    LogTradeSimulator.trigger_kill_switch()
    time.sleep(5)

    portfolio_status_id = 1
    portfolio_status = strat_manager_service_native_web_client.get_portfolio_status_client(portfolio_status_id)
    assert portfolio_status.kill_switch

    LogTradeSimulator.revoke_kill_switch_n_resume_trading()
    time.sleep(5)

    portfolio_status = strat_manager_service_native_web_client.get_portfolio_status_client(portfolio_status_id)
    assert not portfolio_status.kill_switch
