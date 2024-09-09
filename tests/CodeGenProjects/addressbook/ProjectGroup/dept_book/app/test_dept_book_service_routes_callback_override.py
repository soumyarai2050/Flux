import os
import random
import time
from typing import List

from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.Pydentic.dept_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_http_client import (
    DeptBookServiceHttpClient)

dept_book_service_web_client: DeptBookServiceHttpClient = \
    DeptBookServiceHttpClient.set_or_get_if_instance_exists("127.0.0.1", 8010)


def test_sanity_underlying_time_series(dash_, dash_filter_, bar_data_):
    dash_ids: List[str] = []
    dash_by_id_dict: Dict[int, DashBaseModel] = {}
    # create all dashes
    for index in range(1000):
        dash_obj: DashBaseModel = DashBaseModel(**dash_)
        dash_obj.rt_dash.leg1.sec.sec_id = f"CB_Sec_{index + 1}"
        stored_leg1_vwap = dash_obj.rt_dash.leg1.vwap
        dash_obj.rt_dash.leg1.vwap = stored_leg1_vwap + random.randint(0, 30)
        dash_obj.rt_dash.leg1.vwap_change = (dash_obj.rt_dash.leg1.vwap - stored_leg1_vwap) * 100 / stored_leg1_vwap
        dash_obj.rt_dash.leg2.sec.sec_id = f"EQT_Sec_{index + 1}"
        stored_leg2_vwap = dash_obj.rt_dash.leg2.vwap
        dash_obj.rt_dash.leg2.vwap = stored_leg2_vwap + random.randint(0, 10) / 10
        dash_obj.rt_dash.leg2.vwap_change = (dash_obj.rt_dash.leg2.vwap - stored_leg2_vwap) * 100 / stored_leg2_vwap
        stored_premium = dash_obj.rt_dash.mkt_premium
        dash_obj.rt_dash.mkt_premium = stored_premium + random.randint(0, 10) * 0.1
        dash_obj.rt_dash.mkt_premium_change = (dash_obj.rt_dash.mkt_premium - stored_premium) * 100 / stored_premium
        stored_dash_obj: DashBaseModel = dept_book_service_web_client.create_dash_client(dash_obj)
        dash_by_id_dict[stored_dash_obj.id] = stored_dash_obj
        dash_ids.append(str(stored_dash_obj.id))

    # create dash filters and dept_book
    dash_filters_ids: List[str] = []
    for index in range(10):
        dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel(**dash_filter_)
        dash_filters_obj.dash_name = f"Dashboard {index + 1}"
        stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
        dash_filters_ids.append(str(stored_dash_filters_obj.id))
        max_dashes: int = random.randint(100, 3_000)
        dash_collection_obj = DashCollectionBaseModel(id=stored_dash_filters_obj.id,
                                                      dash_name=stored_dash_filters_obj.dash_name,
                                                      loaded_dashes=dash_ids[:max_dashes],
                                                      buffered_dashes=[])
        dept_book_service_web_client.create_dash_collection_client(dash_collection_obj)
    dash_filters_collection_obj = DashFiltersCollectionBaseModel(loaded_dash_filters=dash_filters_ids,
                                                                 buffered_dash_filters=[])
    dept_book_service_web_client.create_dash_filters_collection_client(dash_filters_collection_obj)

    total_loops = 600
    loop_wait = 10  # sec
    volume = 1_000

    def gen_bar_data_by_leg(leg: DashLegOptional, start_time: pendulum.DateTime, is_eqt = False) -> BarDataBaseModel:
        bar_data = BarDataBaseModel(**bar_data_)
        bar_data.start_time = start_time
        bar_data.end_time = start_time.add(seconds=1)
        bar_data.symbol_n_exch_id.symbol = leg.sec.sec_id
        bar_data.symbol_n_exch_id.exch_id = leg.exch_id
        random_increment = random.randint(0, 10)
        if is_eqt:
            random_increment *= 0.1
        bar_data.vwap = leg.vwap + random_increment
        bar_data.vwap_change = (bar_data.vwap - leg.vwap) * 100 / leg.vwap
        volume_change = random.randint(0, 1_000)
        bar_data.volume = volume + volume_change
        if not is_eqt:
            bar_data.premium = 10 + random.randint(0, 10) * 0.1
            bar_data.premium_change = (bar_data.premium - 10) * 100 / 10
        return bar_data

    for _ in range(total_loops):
        current_time = DateTime.utcnow()
        pending_bars = []
        pending_dashes = []
        for index, dash in enumerate(dash_by_id_dict.values()):
            if index > 100:
                break
            # create bars for leg1 and leg2
            leg1_bar_data = gen_bar_data_by_leg(dash.rt_dash.leg1, current_time)
            pending_bars.append(leg1_bar_data)
            leg2_bar_data = gen_bar_data_by_leg(dash.rt_dash.leg2, current_time, True)
            pending_bars.append(leg2_bar_data)

            # dash updates
            leg1 = DashLegOptional(vwap=leg1_bar_data.vwap, vwap_change=leg1_bar_data.vwap_change)
            leg2 = DashLegOptional(vwap=leg2_bar_data.vwap, vwap_change=leg2_bar_data.vwap_change)
            rt_dash = RTDashOptional(leg1=leg1, leg2=leg2, mkt_premium=leg1_bar_data.premium,
                                     mkt_premium_change=leg1_bar_data.premium_change)
            updated_dash = DashBaseModel(id=dash.id, rt_dash=rt_dash)
            pending_dashes.append(jsonable_encoder(updated_dash, by_alias=True, exclude_none=True))

        dept_book_service_web_client.create_all_bar_data_client(pending_bars)
        dept_book_service_web_client.patch_all_dash_client(pending_dashes)
        time.sleep(loop_wait)
