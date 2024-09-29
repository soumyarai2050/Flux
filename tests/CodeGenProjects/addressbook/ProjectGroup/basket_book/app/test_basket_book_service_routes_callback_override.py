# standard imports
import time
import random
import orjson

import pytest

# project imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import basket_book_web_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.conftest import *
import timeit


@pytest.mark.nightly
def test_sanity_new_chores(static_data_, clean_and_set_limits,
                           pair_securities_with_sides_, expected_chore_limits_):
    # waiting for 30 sec for bucket_server to mark service up if not marked yet since it waits for USD px to be
    # available in pair_strat service and for USD px fx_symbol_overview is set by clean_and_set_limits
    time.sleep(30)

    new_chore_list: List[NewChoreBaseModel] = []
    for _ in range(5):
        sec_id = f"CB_Sec_{random.randint(1, 10)}"
        side = random.choice([Side.BUY, Side.SELL])
        px = random.randint(90, 100)
        qty = random.randint(80, 90)
        security = SecurityOptional(sec_id=sec_id, sec_id_source=SecurityIdSource.TICKER)
        new_chore_obj = NewChoreBaseModel(security=security, side=side, px=px, qty=qty)
        new_chore_list.append(new_chore_obj)

    basket_chore = BasketChoreBaseModel(new_chores=new_chore_list)
    created_basket_chore = basket_book_web_client.create_basket_chore_client(basket_chore)

    for new_chore in created_basket_chore.new_chores:
        assert new_chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_PENDING, \
            (f"Mismatched: Expected chore_submit_state {ChoreSubmitType.ORDER_SUBMIT_PENDING}, "
             f"found: {new_chore.chore_submit_state}")

    # updating market data for this symbol
    symbol_list = set([new_chore.security.sec_id for new_chore in created_basket_chore.new_chores])
    t1 = timeit.default_timer()
    for symbol in symbol_list:
        last_barter = QuoteBaseModel(px=100, qty=90)
        bid_quote = QuoteBaseModel(px=100, qty=90)
        ask_quote = QuoteBaseModel(px=100, qty=90)
        tob = TopOfBookBaseModel(symbol=symbol, last_barter=last_barter, bid_quote=bid_quote, ask_quote=ask_quote)
        basket_book_web_client.create_top_of_book_client(tob)   # creating tob

        symbol_overview = SymbolOverviewBaseModel(symbol=symbol)
        basket_book_web_client.create_symbol_overview_client(symbol_overview)   # creating symbol overview
    t2 = timeit.default_timer()
    print(f"MD: {t2-t1}")

    try_attempts = 5
    try_wait = 10
    for _ in range(try_attempts):
        time.sleep(try_wait)

        basket_chore = basket_book_web_client.get_basket_chore_client(created_basket_chore.id)
        for new_chore in basket_chore.new_chores:
            if new_chore.chore_submit_state != ChoreSubmitType.ORDER_SUBMIT_DONE and new_chore.chore_id:
                break
        else:
            break
    else:
        assert False, "some new_chores in basket chore has either states not set to SUBMIT_DONE or has no chore_id"

    time.sleep(10)
    datetime_str = datetime.datetime.now().strftime("%Y%m%d")
    basket_chore_simulator_log_file = BASKET_EXECUTOR_DIR / 'log' / f"log_simulator_basket_logs_{datetime_str}.log"
    with open(basket_chore_simulator_log_file, "r") as f:
        # content = f.read()
        # for new_chore in basket_chore.new_chores:
        #     check_str = f"~~internal_ord_id^^{new_chore.chore_id}"
        #     if check_str not in content:
        #         assert False, f"ChoreId: {new_chore.chore_id} not found in basket_book log file"
        lines = f.readlines()
        assert len(lines) == len(basket_chore.new_chores), \
            ("Mismatched: Len of log file lines must be equal to total new_chores in basket_chore, "
             f"log file length: {len(lines)}, new_chores count: {len(basket_chore.new_chores)}")

