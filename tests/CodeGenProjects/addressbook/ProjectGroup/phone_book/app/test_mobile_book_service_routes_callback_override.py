# system imports
import pytest
import time
from pendulum import DateTime
import os

os.environ["DBType"] = "beanie"

# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.mobile_book.generated.Pydentic.mobile_book_service_model_imports import LastTradeBaseModel
from Flux.CodeGenProjects.addressbook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_client import \
    MobileBookServiceHttpClient
from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.utility_test_functions import *


def test_last_trade_total_qty_sum(last_trade_fixture_list):
    max_loop_count = 20
    sec_gap_btw_trades = 5

    for loop_count in range(max_loop_count):
        for last_trade_obj in last_trade_fixture_list:
            last_trade_obj = LastTradeBaseModel(**last_trade_obj)
            last_trade_obj.time = DateTime.utcnow()
            mobile_book_web_client.create_last_trade_client(last_trade_obj)

        if loop_count != (max_loop_count-1):
            time.sleep(sec_gap_btw_trades)

    for loop_count in range(max_loop_count):
        for last_trade_obj in last_trade_fixture_list:
            last_trade_obj = LastTradeBaseModel(**last_trade_obj)
            last_n_sec_market_trade_vol = \
                mobile_book_web_client.get_last_n_sec_total_qty_query_client(
                    [last_trade_obj.symbol, (sec_gap_btw_trades*(loop_count+1))])

            assert len(last_n_sec_market_trade_vol) == 1
            assert last_n_sec_market_trade_vol[-1].last_n_sec_trade_vol == last_trade_obj.qty * (loop_count+1), \
                f"last {sec_gap_btw_trades*(loop_count+1)} sec's trade order != {last_trade_obj.qty * (loop_count+1)}, " \
                f"received {last_n_sec_market_trade_vol[-1].last_n_sec_trade_vol}"
