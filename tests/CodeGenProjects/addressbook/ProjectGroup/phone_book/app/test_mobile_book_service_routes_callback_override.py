# system imports
import pytest
import time
from pendulum import DateTime
import os

os.environ["DBType"] = "beanie"

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.Pydentic.mobile_book_service_model_imports import LastBarterBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_client import \
    MobileBookServiceHttpClient
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *


def test_last_barter_total_qty_sum(last_barter_fixture_list):
    max_loop_count = 20
    sec_gap_btw_barters = 5

    for loop_count in range(max_loop_count):
        for last_barter_obj in last_barter_fixture_list:
            last_barter_obj = LastBarterBaseModel(**last_barter_obj)
            last_barter_obj.time = DateTime.utcnow()
            mobile_book_web_client.create_last_barter_client(last_barter_obj)

        if loop_count != (max_loop_count-1):
            time.sleep(sec_gap_btw_barters)

    for loop_count in range(max_loop_count):
        for last_barter_obj in last_barter_fixture_list:
            last_barter_obj = LastBarterBaseModel(**last_barter_obj)
            last_n_sec_market_barter_vol = \
                mobile_book_web_client.get_last_n_sec_total_qty_query_client(
                    [last_barter_obj.symbol, (sec_gap_btw_barters*(loop_count+1))])

            assert len(last_n_sec_market_barter_vol) == 1
            assert last_n_sec_market_barter_vol[-1].last_n_sec_barter_vol == last_barter_obj.qty * (loop_count+1), \
                f"last {sec_gap_btw_barters*(loop_count+1)} sec's barter chore != {last_barter_obj.qty * (loop_count+1)}, " \
                f"received {last_n_sec_market_barter_vol[-1].last_n_sec_barter_vol}"
