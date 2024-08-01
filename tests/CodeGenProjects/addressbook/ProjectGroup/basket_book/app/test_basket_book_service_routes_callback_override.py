# standard imports
import time
import random
import orjson

import pytest

# project imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import basket_book_web_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *


@pytest.mark.nightly
def test_sanity_new_chores(static_data_, clean_and_set_limits,
                           pair_securities_with_sides_):
    # waiting for 30 sec for bucket_server to mark service up if not marked yet since it waits for USD px to be
    # available in pair_strat service and for USD px fx_symbol_overview is set by clean_and_set_limits
    time.sleep(30)

    new_chore_list = []
    for _ in range(5):
        sec_id = f"CB_Sec_{random.randint(1, 10)}"
        side = random.choice([Side.BUY, Side.SELL])
        px = random.randint(80, 100)
        qty = random.randint(70, 90)
        security = SecurityOptional(sec_id=sec_id, sec_id_source=SecurityIdSource.TICKER)
        new_chore_obj = NewChoreBaseModel(security=security, side=side, px=px, qty=qty)
        # new_chore_list.append(new_chore_obj.model_dump())
        new_chore_list.append(new_chore_obj)

    basket_chore = BasketChoreBaseModel(new_chores=new_chore_list)
    created_bucket_chore = basket_book_web_client.create_basket_chore_client(basket_chore)

    for new_chore in created_bucket_chore.new_chores:
        assert new_chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_PENDING, \
            (f"Mismatched: Expected chore_submit_state {ChoreSubmitType.ORDER_SUBMIT_PENDING}, "
             f"found: {new_chore.chore_submit_state}")

    # updating market data for this symbol
    symbol_list = set([new_chore.security.sec_id for new_chore in created_bucket_chore.new_chores])
    for symbol in symbol_list:
        tob = TopOfBookBaseModel(symbol=symbol)
        basket_book_web_client.create_top_of_book_client(tob)   # creating tob

        symbol_overview = SymbolOverviewBaseModel(symbol=symbol)
        basket_book_web_client.create_symbol_overview_client(symbol_overview)   # creating symbol overview

    try_attempts = 5
    try_wait = 10
    for _ in range(try_attempts):
        time.sleep(try_wait)

        basket_chore = basket_book_web_client.get_basket_chore_client(created_bucket_chore.id)
        for new_chore in basket_chore.new_chores:
            if new_chore.chore_submit_state != ChoreSubmitType.ORDER_SUBMIT_DONE:
                break
        else:
            break
    else:
        assert False, "some new_chores in basket chore has states not set to SUBMIT_DONE"
