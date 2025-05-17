import copy
import os
import random
import time
from typing import List

import pendulum

os.environ['ModelType'] = "msgspec"
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_http_client import (
    DeptBookServiceHttpClient)
from tests.CodeGenProjects.AddressBook.ProjectGroup.dept_book.conftest import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.conftest import *

dept_book_service_web_client: DeptBookServiceHttpClient = \
    DeptBookServiceHttpClient.set_or_get_if_instance_exists("127.0.0.1", 8010)


def test_sanity_underlying_time_series(dash_, dash_filter_, bar_data_):
    dash_ids: List[str] = []
    dash_by_id_dict: Dict[int, DashBaseModel] = {}
    # create all dashes
    for index in range(1000):
        dash_obj: DashBaseModel = DashBaseModel.from_kwargs(**dash_)
        dash_obj.rt_dash.leg1.sec.sec_id = f"Type1_Sec_{index + 1}"
        stored_leg1_vwap = dash_obj.rt_dash.leg1.vwap
        dash_obj.rt_dash.leg1.vwap = stored_leg1_vwap + random.randint(0, 30)
        dash_obj.rt_dash.leg1.vwap_change = (dash_obj.rt_dash.leg1.vwap - stored_leg1_vwap) * 100 / stored_leg1_vwap
        dash_obj.rt_dash.leg2.sec.sec_id = f"Type2_Sec_{index + 1}"
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
        dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
        dash_filters_obj.dash_name = f"Dashboard {index + 1}"
        stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
        dash_filters_ids.append(str(stored_dash_filters_obj.id))
        max_dashes: int = random.randint(100, 3_000)
        dash_collection_obj = DashCollectionBaseModel.from_kwargs(_id=stored_dash_filters_obj.id,
                                                                  dash_name=stored_dash_filters_obj.dash_name,
                                                                  loaded_dashes=dash_ids[:max_dashes],
                                                                  buffered_dashes=[])
        dept_book_service_web_client.create_dash_collection_client(dash_collection_obj)
    dash_filters_collection_obj = DashFiltersCollectionBaseModel.from_kwargs(loaded_dash_filters=dash_filters_ids,
                                                                             buffered_dash_filters=[])
    dept_book_service_web_client.create_dash_filters_collection_client(dash_filters_collection_obj)

    total_loops = 600
    loop_wait = 10  # sec
    volume = 1_000

    def gen_bar_data_by_leg(leg: DashLegBaseModel, start_time: pendulum.DateTime, is_eqt = False) -> BarDataBaseModel:
        bar_data = BarDataBaseModel.from_kwargs(**bar_data_)
        bar_data.start_time = start_time
        bar_data.end_time = start_time.add(seconds=1)
        bar_data.bar_meta_data = BarMetaDataBaseModel()
        bar_data.bar_meta_data.symbol = leg.sec.sec_id
        bar_data.bar_meta_data.exch_id = leg.exch_id
        bar_data.bar_meta_data.bar_type = BarType.OneDay
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
            leg1 = DashLegBaseModel.from_kwargs(vwap=leg1_bar_data.vwap, vwap_change=leg1_bar_data.vwap_change)
            leg2 = DashLegBaseModel.from_kwargs(vwap=leg2_bar_data.vwap, vwap_change=leg2_bar_data.vwap_change)
            rt_dash = RTDashBaseModel.from_kwargs(leg1=leg1, leg2=leg2, mkt_premium=leg1_bar_data.premium,
                                                  mkt_premium_change=leg1_bar_data.premium_change)
            updated_dash = DashBaseModel.from_kwargs(_id=dash.id, rt_dash=rt_dash)
            pending_dashes.append(updated_dash.to_dict(by_alias=True, exclude_none=True))

        dept_book_service_web_client.create_all_bar_data_client(pending_bars)
        dept_book_service_web_client.patch_all_dash_client(pending_dashes)
        time.sleep(loop_wait)

def test_filter_dash_based_on_dash_filter_by_dash_name(dash_, dash_filter_, expected_brokers_):
    # cleaning all dash
    dept_book_service_web_client.delete_all_dash_client()
    dept_book_service_web_client.delete_all_dash_filters_client()
    dept_book_service_web_client.delete_all_dash_collection_client()

    dash_ids: List[str] = []
    dash_by_id_dict: Dict[int, DashBaseModel] = {}
    # create all dashes
    for index in range(1000):
        dash_obj: DashBaseModel = DashBaseModel.from_kwargs(**dash_)
        if random.choice([True, False]):
            dash_obj.rt_dash.leg1.sec.sec_id = f"Type1_Sec_1"
            stored_leg1_vwap = dash_obj.rt_dash.leg1.vwap
            dash_obj.rt_dash.leg1.vwap = stored_leg1_vwap + random.randint(0, 30)
            dash_obj.rt_dash.leg1.vwap_change = (dash_obj.rt_dash.leg1.vwap - stored_leg1_vwap) * 100 / stored_leg1_vwap
        else:
            dash_obj.rt_dash.leg1 = None
        if random.choice([True, False]):
            dash_obj.rt_dash.leg2.sec.sec_id = f"Type2_Sec_1"
            stored_leg2_vwap = dash_obj.rt_dash.leg2.vwap
            dash_obj.rt_dash.leg2.vwap = stored_leg2_vwap + random.randint(0, 10) / 10
            dash_obj.rt_dash.leg2.vwap_change = (dash_obj.rt_dash.leg2.vwap - stored_leg2_vwap) * 100 / stored_leg2_vwap
        else:
            dash_obj.rt_dash.leg2 = None
        stored_premium = dash_obj.rt_dash.mkt_premium
        dash_obj.rt_dash.mkt_premium = stored_premium + random.randint(0, 10) * 0.1
        dash_obj.rt_dash.mkt_premium_change = ((dash_obj.rt_dash.mkt_premium - stored_premium) * 100) / stored_premium
        if random.choice([True, False]):
            dash_obj.rt_dash.ashare_locate_requests = [InventoryRequestBaseModel.from_kwargs(requestor="sample_requestor")]
        else:
            dash_obj.rt_dash.ashare_locate_requests = []
        # else not required: leaving it as None
        dash_obj.rt_dash.pth_summary = InventorySummary.from_kwargs(cum_qty=random.randint(50, 100),
                                                                    usd_notional=random.randint(50, 100))
        dash_obj.rt_dash.eligible_brokers = expected_brokers_

        stored_dash_obj: DashBaseModel = dept_book_service_web_client.create_dash_client(dash_obj)
        dash_by_id_dict[stored_dash_obj.id] = stored_dash_obj
        dash_ids.append(str(stored_dash_obj.id))

    # create dash filters and dept_book
    dash_filters_ids: List[str] = []

    # dash_filters that filters dash with required_leg_type = LegType_CB
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 1"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB)]
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(dash_filters_obj.dash_name)
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None, \
            f"Mismatched: found dash having leg1 as None when filter expected it to be Non-None: {filtered_dash.rt_dash.leg1}"

    # dash_filters that filters dash with required_leg_type = LegType_EQT_A
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 2"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(dash_filters_obj.dash_name)
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg2 is not None, \
            f"Mismatched: found dash having leg2 as None when filter expected it to be Non-None: {filtered_dash.rt_dash.leg2}"

    # dash_filters that filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 3"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(dash_filters_obj.dash_name)
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 4"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) > 0, \
        f"Mismatched: {len(filtered_dash_list)=} !> 0"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 5"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0, premium_change_high=7.0)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) > 0, \
        f"Mismatched: {len(filtered_dash_list)=} !> 0"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        assert dash_filters_obj.premium_range.premium_low <= filtered_dash.rt_dash.mkt_premium <= dash_filters_obj.premium_range.premium_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium=} must be from {dash_filters_obj.premium_range.premium_low=} to "
             f"{dash_filters_obj.premium_range.premium_high=}")
        assert dash_filters_obj.premium_change_range.premium_change_low <= filtered_dash.rt_dash.mkt_premium_change <= dash_filters_obj.premium_change_range.premium_change_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium_change=} must be from {dash_filters_obj.premium_change_range.premium_change_low=} to "
             f"{dash_filters_obj.premium_change_range.premium_change_high=}")

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with type any
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 6"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0,
                                                                                    premium_change_high=7.0)
    dash_filters_obj.inventory = InventoryBaseModel.from_kwargs(any=True)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) > 0, \
        f"Mismatched: {len(filtered_dash_list)=} !> 0"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        assert dash_filters_obj.premium_range.premium_low <= filtered_dash.rt_dash.mkt_premium <= dash_filters_obj.premium_range.premium_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium=} must be from {dash_filters_obj.premium_range.premium_low=} to "
             f"{dash_filters_obj.premium_range.premium_high=}")
        assert dash_filters_obj.premium_change_range.premium_change_low <= filtered_dash.rt_dash.mkt_premium_change <= dash_filters_obj.premium_change_range.premium_change_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium_change=} must be from {dash_filters_obj.premium_change_range.premium_change_low=} to "
             f"{dash_filters_obj.premium_change_range.premium_change_high=}")
        assert len(filtered_dash.rt_dash.eligible_brokers) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.eligible_brokers)=} !> 0"
        for broker in filtered_dash.rt_dash.eligible_brokers:
            assert len(broker.sec_positions) > 0, \
                f"Mismatched: {len(broker.sec_positions)=} !> 0"
            for sec_pos in broker.sec_positions:
                assert len(sec_pos.positions) > 0, \
                    f"Mismatched: {len(sec_pos.positions)=} !> 0"
                for pos in sec_pos.positions:
                    expected_type = [PositionType.PTH, PositionType.LOCATE, PositionType.SOD, PositionType.INDICATIVE]
                    if pos.type not in expected_type:
                        assert False, f"Mismatched: {pos.type=} not in {expected_type=}"

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with either type SOD or PTH
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 7"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0,
                                                                                    premium_change_high=7.0)
    dash_filters_obj.inventory = InventoryBaseModel.from_kwargs(pth=True, sod=True)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) > 0, \
        f"Mismatched: {len(filtered_dash_list)=} !> 0"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        assert dash_filters_obj.premium_range.premium_low <= filtered_dash.rt_dash.mkt_premium <= dash_filters_obj.premium_range.premium_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium=} must be from {dash_filters_obj.premium_range.premium_low=} to "
             f"{dash_filters_obj.premium_range.premium_high=}")
        assert dash_filters_obj.premium_change_range.premium_change_low <= filtered_dash.rt_dash.mkt_premium_change <= dash_filters_obj.premium_change_range.premium_change_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium_change=} must be from {dash_filters_obj.premium_change_range.premium_change_low=} to "
             f"{dash_filters_obj.premium_change_range.premium_change_high=}")
        assert len(filtered_dash.rt_dash.eligible_brokers) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.eligible_brokers)=} !> 0"
        expected_type = [PositionType.PTH, PositionType.SOD]
        for broker in filtered_dash.rt_dash.eligible_brokers:
            assert len(broker.sec_positions) > 0, \
                f"Mismatched: {len(broker.sec_positions)=} !> 0"
            for sec_pos in broker.sec_positions:
                assert len(sec_pos.positions) > 0, \
                    f"Mismatched: {len(sec_pos.positions)=} !> 0"
                for pos in sec_pos.positions:
                    if pos.type in expected_type:
                        break
                else:
                    assert False, f"Mismatched: no position with type in {expected_type=}"

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with type INDICATIVE - no obj is created with this type so no data must be found
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 8"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0,
                                                                                    premium_change_high=7.0)
    dash_filters_obj.inventory = InventoryBaseModel.from_kwargs(indicative=True)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) == 0, \
        f"Mismatched: Since no dash contains position of type INDICATIVE no dash must be filtered but found {filtered_dash_list=}"

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with type any
    # 6. filters dash with having ashare_locate_requests if dash_filters.has_ashare_locate_request is True
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 9"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0,
                                                                                    premium_change_high=7.0)
    dash_filters_obj.inventory = InventoryBaseModel.from_kwargs(any=True)
    dash_filters_obj.has_ashare_locate_request = True
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) > 0, \
        f"Mismatched: {len(filtered_dash_list)=} !> 0"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        assert dash_filters_obj.premium_range.premium_low <= filtered_dash.rt_dash.mkt_premium <= dash_filters_obj.premium_range.premium_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium=} must be from {dash_filters_obj.premium_range.premium_low=} to "
             f"{dash_filters_obj.premium_range.premium_high=}")
        assert dash_filters_obj.premium_change_range.premium_change_low <= filtered_dash.rt_dash.mkt_premium_change <= dash_filters_obj.premium_change_range.premium_change_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium_change=} must be from {dash_filters_obj.premium_change_range.premium_change_low=} to "
             f"{dash_filters_obj.premium_change_range.premium_change_high=}")
        assert len(filtered_dash.rt_dash.eligible_brokers) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.eligible_brokers)=} !> 0"
        for broker in filtered_dash.rt_dash.eligible_brokers:
            assert len(broker.sec_positions) > 0, \
                f"Mismatched: {len(broker.sec_positions)=} !> 0"
            for sec_pos in broker.sec_positions:
                assert len(sec_pos.positions) > 0, \
                    f"Mismatched: {len(sec_pos.positions)=} !> 0"
                for pos in sec_pos.positions:
                    expected_type = [PositionType.PTH, PositionType.LOCATE, PositionType.SOD, PositionType.INDICATIVE]
                    if pos.type not in expected_type:
                        assert False, f"Mismatched: {pos.type=} not in {expected_type=}"
        assert len(filtered_dash.rt_dash.ashare_locate_requests) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.ashare_locate_requests)=} !> 0 when {dash_filters_obj.has_ashare_locate_request=}"

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with type any
    # 6. filters dash with having ashare_locate_requests if dash_filters.has_ashare_locate_request is True
    # 7. filters dash with having any pos having optimization opportunity when dash_filters.optimizer_criteria.pos_type == PTH

    for index, filtered_dash_obj in enumerate(filtered_dash_list):
        if index < 5:
            # reducing LOCATE type position's acquire_cost to make it filterable based on optimizer_criteria with type PTH
            for position in filtered_dash_obj.rt_dash.eligible_brokers[0].sec_positions[1].positions:
                if position.type == PositionType.LOCATE:
                    position.acquire_cost -= 10000
                    break
            dept_book_service_web_client.put_dash_client(filtered_dash_obj)
            continue
        break

    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 10"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0,
                                                                                    premium_change_high=7.0)
    dash_filters_obj.inventory = InventoryBaseModel.from_kwargs(any=True)
    dash_filters_obj.has_ashare_locate_request = True
    dash_filters_obj.optimizer_criteria = OptimizerCriteriaBaseModel.from_kwargs(pos_type=PositionType.PTH,
                                                                                 min_notional=70)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    # below assert is enough to verify optimization_criteria since only 5 obj are created with positions other than
    # PTH having less acquire_cost than max of acquire_cost with type PTH
    assert len(filtered_dash_list) == 5, \
        f"Mismatched: {len(filtered_dash_list)=} != 5"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
             f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                 f"{dash_filters_obj.px_range.px_high=}")
        assert dash_filters_obj.premium_range.premium_low <= filtered_dash.rt_dash.mkt_premium <= dash_filters_obj.premium_range.premium_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium=} must be from {dash_filters_obj.premium_range.premium_low=} to "
             f"{dash_filters_obj.premium_range.premium_high=}")
        assert dash_filters_obj.premium_change_range.premium_change_low <= filtered_dash.rt_dash.mkt_premium_change <= dash_filters_obj.premium_change_range.premium_change_high, \
            (f"Mismatched: {filtered_dash.rt_dash.mkt_premium_change=} must be from {dash_filters_obj.premium_change_range.premium_change_low=} to "
             f"{dash_filters_obj.premium_change_range.premium_change_high=}")
        assert len(filtered_dash.rt_dash.eligible_brokers) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.eligible_brokers)=} !> 0"
        for broker in filtered_dash.rt_dash.eligible_brokers:
            assert len(broker.sec_positions) > 0, \
                f"Mismatched: {len(broker.sec_positions)=} !> 0"
            for sec_pos in broker.sec_positions:
                assert len(sec_pos.positions) > 0, \
                    f"Mismatched: {len(sec_pos.positions)=} !> 0"
                for pos in sec_pos.positions:
                    expected_type = [PositionType.PTH, PositionType.LOCATE, PositionType.SOD, PositionType.INDICATIVE]
                    if pos.type not in expected_type:
                        assert False, f"Mismatched: {pos.type=} not in {expected_type=}"
        assert len(filtered_dash.rt_dash.ashare_locate_requests) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.ashare_locate_requests)=} !> 0 when {dash_filters_obj.has_ashare_locate_request=}"

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with type any
    # 6. filters dash with having ashare_locate_requests if dash_filters.has_ashare_locate_request is True
    # 7. filters dash with having any pos having optimization opportunity when dash_filters.optimizer_criteria.pos_type == PTH
    # 8. filters dash sorted based on rt_dash.pth_summary.usd_notional
    dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel.from_kwargs(**dash_filter_)
    dash_filters_obj.dash_name = f"Dashboard 11"
    dash_filters_obj.required_legs = [LegBaseModel(leg_type=LegType.LegType_CB),
                                      LegBaseModel(leg_type=LegType.LegType_EQT_A)]
    dash_filters_obj.px_range = PxRange.from_kwargs(px_low=160, px_high=170)
    dash_filters_obj.premium_range = PremiumRangeBaseModel.from_kwargs(premium_low=10.2, premium_high=10.7)
    dash_filters_obj.premium_change_range = PremiumChangeRangeBaseModel.from_kwargs(premium_change_low=2.0,
                                                                                    premium_change_high=7.0)
    dash_filters_obj.inventory = InventoryBaseModel.from_kwargs(any=True)
    dash_filters_obj.has_ashare_locate_request = True
    dash_filters_obj.optimizer_criteria = OptimizerCriteriaBaseModel.from_kwargs(pos_type=PositionType.PTH,
                                                                                 min_notional=70)
    dash_filters_obj.sort_criteria = SortCriteriaBaseModel.from_kwargs(level1="rt_dash.pth_summary.usd_notional",
                                                                       level1_chore=SortType.ASCENDING)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    # below assert is enough to verify optimization_criteria since only 5 obj are created with positions other than
    # PTH having less acquire_cost than max of acquire_cost with type PTH
    assert len(filtered_dash_list) == 5, \
        f"Mismatched: {len(filtered_dash_list)=} != 5"
    for filtered_dash in filtered_dash_list:
        assert filtered_dash.rt_dash.leg1 is not None or filtered_dash.rt_dash.leg2 is not None, \
            (
                f"Mismatched: found dash having leg1 as None or leg2 as None when filter expected them to be Non-None: "
                f"{filtered_dash.rt_dash.leg1=}, {filtered_dash.rt_dash.leg2=}")
        if filtered_dash.rt_dash.leg2 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high, \
                (
                    f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                    f"{dash_filters_obj.px_range.px_high=}")
        elif filtered_dash.rt_dash.leg1 is None:
            assert dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high, \
                (
                    f"Mismatched: {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                    f"{dash_filters_obj.px_range.px_high=}")
        else:
            assert ((
                                dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg1.vwap <= dash_filters_obj.px_range.px_high) or
                    (
                                dash_filters_obj.px_range.px_low <= filtered_dash.rt_dash.leg2.vwap <= dash_filters_obj.px_range.px_high)), \
                (
                    f"Mismatched: {filtered_dash.rt_dash.leg1.vwap=} or {filtered_dash.rt_dash.leg2.vwap=} must be from {dash_filters_obj.px_range.px_low=} to "
                    f"{dash_filters_obj.px_range.px_high=}")
        assert dash_filters_obj.premium_range.premium_low <= filtered_dash.rt_dash.mkt_premium <= dash_filters_obj.premium_range.premium_high, \
            (
                f"Mismatched: {filtered_dash.rt_dash.mkt_premium=} must be from {dash_filters_obj.premium_range.premium_low=} to "
                f"{dash_filters_obj.premium_range.premium_high=}")
        assert dash_filters_obj.premium_change_range.premium_change_low <= filtered_dash.rt_dash.mkt_premium_change <= dash_filters_obj.premium_change_range.premium_change_high, \
            (
                f"Mismatched: {filtered_dash.rt_dash.mkt_premium_change=} must be from {dash_filters_obj.premium_change_range.premium_change_low=} to "
                f"{dash_filters_obj.premium_change_range.premium_change_high=}")
        assert len(filtered_dash.rt_dash.eligible_brokers) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.eligible_brokers)=} !> 0"
        assert len(filtered_dash.rt_dash.ashare_locate_requests) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.ashare_locate_requests)=} !> 0 when {dash_filters_obj.has_ashare_locate_request=}"

    pth_sum_usd_notional_list = []
    for filtered_dash in filtered_dash_list:
        pth_sum_usd_notional_list.append(filtered_dash.rt_dash.pth_summary.usd_notional)

    expected_sorted_list = copy.deepcopy(pth_sum_usd_notional_list)
    expected_sorted_list.sort()
    assert pth_sum_usd_notional_list == expected_sorted_list, \
        (f"Mismatched: filtered_dash not sorted based on pth_summary.usd_notional, {expected_sorted_list=}, "
         f"{pth_sum_usd_notional_list=}")


# Sample data covering various scenarios
SAMPLE_BAR_DATA1 = BarDataBaseModel.from_dict_list([
    # EXCH1 Data
    {
        "_id": 1, "update_id": 10, "bar_meta_data": {"symbol": "AAPL", "exch_id": "EXCH1", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=2), "end_time": get_utc_date_time().subtract(days=2), "close": 150.0 # Recent, latest OneDay
    },
    {
        "_id": 2, "update_id": 9, "bar_meta_data": {"symbol": "AAPL", "exch_id": "EXCH1", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=3), "end_time": get_utc_date_time().subtract(days=3), "close": 148.0 # Recent, older OneDay
    },
    {
        "_id": 3, "update_id": 11, "bar_meta_data": {"symbol": "AAPL", "exch_id": "EXCH1", "bar_type": "OneHour"},
        "start_time": get_utc_date_time().subtract(days=1), "end_time": get_utc_date_time().subtract(days=1), "close": 151.0 # Recent, latest OneHour
    },
    {
        "_id": 4, "update_id": 15, "bar_meta_data": {"symbol": "MSFT", "exch_id": "EXCH1", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=5), "end_time": get_utc_date_time().subtract(days=5), "close": 300.0 # Recent, latest OneDay
    },
     { # Outside default time window
        "_id": 5, "update_id": 5, "bar_meta_data": {"symbol": "MSFT", "exch_id": "EXCH1", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=10), "end_time": get_utc_date_time().subtract(days=10), "close": 290.0 # Too old for default
    },
    # EXCH2 Data
    {
        "_id": 6, "update_id": 20, "bar_meta_data": {"symbol": "AAPL", "exch_id": "EXCH2", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=1), "end_time": get_utc_date_time().subtract(days=1), "close": 155.0 # Recent, latest OneDay
    },
     {
        "_id": 7, "update_id": 25, "bar_meta_data": {"symbol": "GOOG", "exch_id": "EXCH2", "bar_type": "OneHour"},
        "start_time": get_utc_date_time().subtract(days=19), "end_time": get_utc_date_time().subtract(days=19), "close": 2800.0 # Recent, latest OneHour
    },
     { # Outside default time window
        "_id": 8, "update_id": 26, "bar_meta_data": {"symbol": "GOOG", "exch_id": "EXCH2", "bar_type": "OneHour"},
        "start_time": get_utc_date_time().subtract(days=35), "end_time": get_utc_date_time().subtract(days=35), "close": 2750.0 # Too old for default
    },
    # Specific date for custom time tests
     {
        "_id": 9, "update_id": 30, "bar_meta_data": {"symbol": "TSLA", "exch_id": "EXCH1", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=15), "end_time": get_utc_date_time().subtract(days=15), "close": 700.0 # Specific date
    },
      {
        "_id": 10, "update_id": 31, "bar_meta_data": {"symbol": "TSLA", "exch_id": "EXCH1", "bar_type": "OneDay"},
        "start_time": get_utc_date_time().subtract(days=16), "end_time": get_utc_date_time().subtract(days=16), "close": 690.0 # Specific date, older
    },
])

@pytest.fixture
def sample_bar_data_1_set_up():
    """ Pytest fixture to set up with sample data. """
    dept_book_service_web_client.delete_all_bar_data_client() # Clean up before test

    bar_data_list = BarDataBaseModel.from_dict_list(SAMPLE_BAR_DATA1)
    dept_book_service_web_client.create_all_bar_data_client(bar_data_list)
    yield


# Helper to sort results for comparison (since chore isn't guaranteed before final sort)
def sort_results(results):
    return sorted(results, key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol))


def test_aggregation_defaults(sample_bar_data_1_set_up):
    """ Test with no filters, using default time window (last 20 days from MOCK_NOW). """
    results = dept_book_service_web_client.get_latest_bar_data_query_client()

    # Expected: Latest bar for each exch/symbol within the last 20 days
    # AAPL@EXCH1: id=1 (OneDay is latest type overall), id=3 (latest OneHour) -> depends on bartype filter... wait, the function finds latest *regardless* of type if no type specified.
    # The grouping is by exch/symbol, latest start_time wins.
    # AAPL@EXCH1: id=3 (start_time: -1 days) is later than id=1 (-2 days)
    # MSFT@EXCH1: id=4 (latest is -5 days). id=5 is too old.
    # TSLA@EXCH1: id=9 (latest is -15 days). id=10 is older. Both within 20 days.
    # AAPL@EXCH2: id=6 (latest is -1 day).
    # GOOG@EXCH2: id=7 (latest is -19 days). id=8 is too old.
    expected_ids = {3, 4, 9, 6, 7}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)


def test_aggregation_single_exch_id_only(sample_bar_data_1_set_up):
    """ Test filtering by single exch_id only. """
    results = dept_book_service_web_client.get_latest_bar_data_query_client(exch_id_list=["EXCH1"])

    # Expected: Latest for each symbol on EXCH1 within default time window
    # AAPL@EXCH1: id=3
    # MSFT@EXCH1: id=4
    # TSLA@EXCH1: id=9
    expected_ids = {3, 4, 9}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)

def test_aggregation_multiple_exch_id_only(sample_bar_data_1_set_up):
    """ Test filtering by multiple exch_id. """
    results = dept_book_service_web_client.get_latest_bar_data_query_client(exch_id_list=["EXCH1", "EXCH2"])

    # Expected: Latest for each symbol on EXCH1 and EXCH2 within default time window
    # AAPL@EXCH1: id=3
    # MSFT@EXCH1: id=4
    # TSLA@EXCH1: id=9
    # AAPL@EXCH2: id=6
    # GOOG@EXCH2: id=7
    expected_ids = {3, 4, 9, 6, 7}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)

def test_aggregation_bar_type_only(sample_bar_data_1_set_up):
    """ Test filtering by bar_type only. """
    results = dept_book_service_web_client.get_latest_bar_data_query_client(bar_type_list=[BarType.OneDay])

    # Expected: Latest OneDay bar for each exch/symbol within default time window
    # AAPL@EXCH1: id=1 (latest OneDay is -2 days). id=3 is OneHour.
    # MSFT@EXCH1: id=4 (latest OneDay is -5 days). id=5 is too old.
    # TSLA@EXCH1: id=9 (latest OneDay is -15 days).
    # AAPL@EXCH2: id=6 (latest OneDay is -1 days).
    # GOOG@EXCH2: No OneDay bars in sample.
    expected_ids = {1, 4, 9, 6}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)

def test_aggregation_exch_id_and_bar_type(sample_bar_data_1_set_up):
    """ Test filtering by both exch_id and bar_type. """
    results = dept_book_service_web_client.get_latest_bar_data_query_client(exch_id_list=["EXCH1"],
                                                                             bar_type_list=[BarType.OneDay])

    # Expected: Latest OneDay bar for each symbol on EXCH1 within default time window
    # AAPL@EXCH1: id=1
    # MSFT@EXCH1: id=4
    # TSLA@EXCH1: id=9
    expected_ids = {1, 4, 9}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)

def test_aggregation_custom_time_range(sample_bar_data_1_set_up):
    """ Test filtering with a specific start and end time. """
    start = pendulum.DateTime.utcnow().subtract(days=20)
    end = pendulum.DateTime.utcnow().subtract(days=5)
    results = dept_book_service_web_client.get_latest_bar_data_query_client(start_time=start, end_time=end)

    # Expected: Latest bar for each exch/symbol with start_time between May 1 and May 16 (inclusive)
    # AAPL@EXCH1: None (id=1,3 are too late, id=2 too early)
    # MSFT@EXCH1: id=4 (start_time -5 days) - id=5 is always too old
    # TSLA@EXCH1: id=9 (start_time -15 days) - id=10 is older but also in range, so 9 wins
    # AAPL@EXCH2: None (id=6 too late)
    # GOOG@EXCH2: id=7 (start_time -19 days) - id=8 is always too old
    expected_ids = {4, 9, 7}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)

def test_aggregation_custom_time_range_exclusive(sample_bar_data_1_set_up):
    """ Test a time range that excludes the otherwise latest record. """
    start = pendulum.DateTime.utcnow().subtract(days=20)
    end = pendulum.DateTime.utcnow().subtract(days=3)
    results = dept_book_service_web_client.get_latest_bar_data_query_client(exch_id_list=["EXCH1"],
                                                                             bar_type_list=[BarType.OneDay],
                                                                             start_time=start, end_time=end)
    # Expected: Latest OneDay on EXCH1 between last 20 and 3 days
    # AAPL@EXCH1: id=1 (start -2 days) is excluded. id=2 (start -3 days) is included and latest.
    # MSFT@EXCH1: id=4 (start -5 days) is included and latest.
    # TSLA@EXCH1: id=9 (start -15 days) is included and latest.
    expected_ids = {2, 4, 9}
    expected_docs = [doc for doc in SAMPLE_BAR_DATA1 if doc.id in expected_ids]

    assert len(results) == len(expected_docs)
    assert sort_results(results) == sort_results(expected_docs)


def test_aggregation_no_matches(sample_bar_data_1_set_up):
    """ Test a filter combination that yields no results. """
    start = DateTime.utcnow().add(days=5) # Future date

    results = dept_book_service_web_client.get_latest_bar_data_query_client(start_time=start)

    assert len(results) == 0


# --- Sample Data ---

# Carefully crafted sample data covering different scenarios
# Timestamps are UTC
# Includes data for multiple symbols/exchanges, nulls, and points crossing intervals
SAMPLE_BAR_DATA2 = BarDataBaseModel.from_dict_list([
    # --- Symbol A, Exch X ---
    # 5-Min Interval 1 (09:00 - 09:04)
    {
        "_id": 1, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 0, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 0, 59, tzinfo=datetime.timezone.utc),
        "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5, "volume": 1000, "vwap": 100.2, "cum_volume": 1000, "bar_count": 10, "source": "SRC1"
    },
    {
        "_id": 2, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 1, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 1, 59, tzinfo=datetime.timezone.utc),
        "open": 100.5, "high": 101.5, "low": 100.0, "close": 101.0, "volume": 1200, "vwap": 100.8, "cum_volume": 2200, "bar_count": 12, "source": "SRC1_XYZ"
    },
    # 5-Min Interval 2 (09:05 - 09:09) -> only one bar
     {
        "_id": 3, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 5, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 5, 59, tzinfo=datetime.timezone.utc),
        "open": 101.0, "high": 101.2, "low": 100.8, "close": 101.1, "volume": 500, "vwap": 101.0, "cum_volume": 2700, "bar_count": 5, "source": "SRC1"
    },
     # Hour Interval 1 (09:00 - 09:59) -> Add another bar later in the hour
     {
        "_id": 4, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 58, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 58, 59, tzinfo=datetime.timezone.utc),
        "open": 102.0, "high": 102.5, "low": 101.8, "close": 102.2, "volume": 800, "vwap": 102.1, "cum_volume": 3500, "bar_count": 8, "source": "SRC1"
    },
    # Hour Interval 2 (10:00 - 10:59)
    {
        "_id": 5, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 10, 0, 59, tzinfo=datetime.timezone.utc),
        "open": 102.2, "high": 103.0, "low": 102.0, "close": 102.8, "volume": 1500, "vwap": 102.5, "cum_volume": 5000, "bar_count": 15, "source": "SRC1"
    },

    # --- Symbol B, Exch Y (with Nulls) ---
    # 5-Min Interval 1 (09:00 - 09:04)
     {
        "_id": 6, "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 2, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 2, 59, tzinfo=datetime.timezone.utc),
        "open": 50.0, "high": 50.5, "low": 49.8, "close": 50.1, "volume": 300, "vwap": 50.2, "cum_volume": 300, "bar_count": 3, "source": "SRC2"
    },
     {
        "_id": 7, "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 3, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 3, 59, tzinfo=datetime.timezone.utc),
        "open": 50.1, "high": 50.8, "low": 49.9, "close": 50.7, "volume": None, "vwap": None, "cum_volume": 300, "bar_count": 4, "source": "SRC2" # Null volume/vwap
    },

     # --- Symbol C, Exch X (Zero Volume Group) ---
     {
        "_id": 8, "bar_meta_data": {"symbol": "C", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 0, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 0, 59, tzinfo=datetime.timezone.utc),
        "open": 20.0, "high": 20.1, "low": 19.9, "close": 20.0, "volume": 0, "vwap": None, "cum_volume": 0, "bar_count": 1, "source": "SRC3" # Zero volume
    },
    {
        "_id": 9, "bar_meta_data": {"symbol": "C", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 26, 9, 1, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 9, 1, 59, tzinfo=datetime.timezone.utc),
        "open": 20.0, "high": 20.1, "low": 19.9, "close": 20.0, "volume": 0, "vwap": 19.95, "cum_volume": 0, "bar_count": 1, "source": "SRC3" # Zero volume, non-null vwap
    },

    # --- Data Outside Typical Query Range (for filtering tests) ---
    {
        "_id": 10, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneMin"},
        "start_time": datetime.datetime(2023, 10, 25, 9, 0, 0, tzinfo=datetime.timezone.utc), # Previous day
        "end_time": datetime.datetime(2023, 10, 25, 9, 0, 59, tzinfo=datetime.timezone.utc),
        "open": 95.0, "high": 96.0, "low": 94.0, "close": 95.5, "volume": 500, "vwap": 95.2, "cum_volume": 500, "bar_count": 5, "source": "SRC1"
    },
     # --- Data with different source bar_type (should be filtered out) ---
     {
        "_id": 11, "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneHour"}, # Incorrect source type
        "start_time": datetime.datetime(2023, 10, 26, 11, 0, 0, tzinfo=datetime.timezone.utc),
        "end_time": datetime.datetime(2023, 10, 26, 11, 59, 59, tzinfo=datetime.timezone.utc),
        "open": 110.0, "high": 111.0, "low": 109.0, "close": 110.5, "volume": 5000, "vwap": 110.2, "cum_volume": 10000, "bar_count": 60, "source": "SRC1"
    }
])

# --- Helper to convert result for comparison ---
def clean_result(result_list: List[Dict]) -> List[Dict]:
    """ Converts datetimes to ISO strings and handles potential None values for easier comparison. """
    cleaned = []
    for doc in result_list:
        new_doc = {}
        for key, value in doc.items():
            if isinstance(value, datetime.datetime):
                # Ensure consistent timezone representation (UTC 'Z')
                dt_aware = value.replace(tzinfo=datetime.timezone.utc) if value.tzinfo is None else value.astimezone(datetime.timezone.utc)
                new_doc[key] = dt_aware.isoformat().replace('+00:00', 'Z')
            # Recursively clean nested dicts like bar_meta_data
            elif isinstance(value, dict):
                 new_doc[key] = clean_result([value])[0] if value else {}
            else:
                new_doc[key] = value
        cleaned.append(new_doc)
    # Sort results by exchange, symbol, start_time for deterministic comparison
    cleaned.sort(key=lambda x: (x.get('bar_meta_data',{}).get('exch_id',''),
                                x.get('bar_meta_data',{}).get('symbol',''),
                                x.get('start_time', '')))
    return cleaned


@pytest.fixture
def sample_bar_data_2_set_up():
    """ Pytest fixture to set up with sample data. """
    dept_book_service_web_client.delete_all_bar_data_client() # Clean up before test

    bar_data_list = BarDataBaseModel.from_dict_list(SAMPLE_BAR_DATA2)
    dept_book_service_web_client.create_all_bar_data_client(bar_data_list)
    yield


def test_aggregation_five_min(sample_bar_data_2_set_up):
    """ Verify aggregation to 5-minute intervals. """
    target_bar_type = "FiveMin"
    start_time = pendulum.datetime(2023, 10, 26, 9, 0, 0, tz="UTC")
    end_time = pendulum.datetime(2023, 10, 26, 9, 10, 0, tz="UTC") # Covers first two 5-min intervals

    # cleaned_result = clean_result(result)
    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(target_bar_type, start_time=start_time,
                                                                                end_time=end_time)

    # --- Expected Output (Calculated Manually) ---
    # Bar A/X (09:00 - 09:04): Docs 1, 2
    vwap_ax_1 = ((100.2 * 1000) + (100.8 * 1200)) / (1000 + 1200) # ~100.527
    # Bar A/X (09:05 - 09:09): Doc 3
    vwap_ax_2 = 101.0
    # Bar B/Y (09:00 - 09:04): Docs 6, 7 (Doc 7 has null volume/vwap)
    vwap_by_1 = (50.2 * 300) / 300 # = 50.2 (nulls ignored in sum)
    # Bar C/X (09:00 - 09:04): Docs 8, 9 (Zero volume)
    vwap_cx_1 = None # Division by zero

    expected_output = BarDataBaseModel.from_dict_list([
        {
            "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "FiveMin"},
            "start_time": "2023-10-26T09:00:00Z", # Doc 1 start
            "end_time": "2023-10-26T09:01:59Z",   # Doc 2 end
            "open": 100.0, # Doc 1 open
            "high": 101.5, # Doc 2 high
            "low": 99.5,   # Doc 1 low
            "close": 101.0, # Doc 2 close
            "volume": 2200, # 1000 + 1200
            "vwap": vwap_ax_1,
            "cum_volume": 2200, # Doc 2 cum_volume
            "bar_count": 2,
            "source": "Mixed: SRC1 + SRC1_XYZ"
        },
        {
            "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "FiveMin"},
            "start_time": "2023-10-26T09:05:00Z", # Doc 3 start
            "end_time": "2023-10-26T09:05:59Z",   # Doc 3 end
            "open": 101.0, "high": 101.2, "low": 100.8, "close": 101.1,
            "volume": 500,
            "vwap": vwap_ax_2,
            "cum_volume": 2700,
            "bar_count": 1,
            "source": "SRC1"
        },
         {
            "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "FiveMin"},
            "start_time": "2023-10-26T09:02:00Z", # Doc 6 start
            "end_time": "2023-10-26T09:03:59Z",   # Doc 7 end
            "open": 50.0,  # Doc 6 open
            "high": 50.8,  # Doc 7 high
            "low": 49.8,   # Doc 6 low
            "close": 50.7, # Doc 7 close
            "volume": 300, # 300 + 0 (from null)
            "vwap": vwap_by_1,
            "cum_volume": 300, # Doc 7 cum_volume
            "bar_count": 2,
            "source": "SRC2" # Doc 6 source
        },
        {
            "bar_meta_data": {"symbol": "C", "exch_id": "X", "bar_type": "FiveMin"},
            "start_time": "2023-10-26T09:00:00Z", # Doc 8 start
            "end_time": "2023-10-26T09:01:59Z",   # Doc 9 end
            "open": 20.0, # Doc 8 open
            "high": 20.1, # Max of Doc 8/9 high
            "low": 19.9,  # Min of Doc 8/9 low
            "close": 20.0, # Doc 9 close
            "volume": 0,   # 0 + 0
            "vwap": vwap_cx_1, # Should be None due to zero volume
            "cum_volume": 0,  # Doc 9 cum_volume
            "bar_count": 2,
            "source": "SRC3" # Doc 8 source
        },
    ])
    expected_output.sort(key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol, x.start_time))

    # removing id field from results from query
    for obj in result:
        obj.id = None

    assert result == expected_output


def test_aggregation_one_hour(sample_bar_data_2_set_up):
    """ Verify aggregation to 1-hour intervals. """

    target_bar_type = "OneHour"
    start_time = pendulum.datetime(2023, 10, 26, 9, 0, 0, tz="UTC")
    end_time = pendulum.datetime(2023, 10, 26, 10, 30, 0, tz="UTC") # Covers 9:xx and 10:xx hour

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(target_bar_type, start_time=start_time,
                                                                                end_time=end_time)

    # --- Expected Output (Calculated Manually) ---
    # Bar A/X (09:00 - 09:59): Docs 1, 2, 3, 4
    vol_ax_h1 = 1000 + 1200 + 500 + 800 # = 3500
    vwap_num_ax_h1 = (100.2*1000) + (100.8*1200) + (101.0*500) + (102.1*800) # = 100200 + 120960 + 50500 + 81680 = 353340
    vwap_ax_h1 = vwap_num_ax_h1 / vol_ax_h1 # ~100.954
    # Bar A/X (10:00 - 10:59): Doc 5
    vol_ax_h2 = 1500
    vwap_ax_h2 = 102.5
    # Bar B/Y (09:00 - 09:59): Docs 6, 7
    vol_by_h1 = 300 # 300 + 0 (from null)
    vwap_by_h1 = (50.2*300) / 300 # = 50.2
    # Bar C/X (09:00 - 09:59): Docs 8, 9
    vol_cx_h1 = 0
    vwap_cx_h1 = None

    expected_output = BarDataBaseModel.from_dict_list([
         {
            "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneHour"},
            "start_time": "2023-10-26T09:00:00Z", # Doc 1 start
            "end_time": "2023-10-26T09:58:59Z",   # Doc 4 end
            "open": 100.0, # Doc 1 open
            "high": 102.5, # Doc 4 high
            "low": 99.5,   # Doc 1 low
            "close": 102.2, # Doc 4 close
            "volume": vol_ax_h1,
            "vwap": vwap_ax_h1,
            "cum_volume": 3500, # Doc 4 cum_volume
            "bar_count": 4,
            "source": "Mixed: SRC1 + SRC1_XYZ"
        },
         {
            "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneHour"},
            "start_time": "2023-10-26T10:00:00Z", # Doc 5 start
            "end_time": "2023-10-26T10:00:59Z",   # Doc 5 end
            "open": 102.2, "high": 103.0, "low": 102.0, "close": 102.8,
            "volume": vol_ax_h2,
            "vwap": vwap_ax_h2,
            "cum_volume": 5000, # Doc 5 cum_volume
            "bar_count": 1,
            "source": "SRC1"
        },
        {
            "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneHour"},
            "start_time": "2023-10-26T09:02:00Z", # Doc 6 start
            "end_time": "2023-10-26T09:03:59Z",   # Doc 7 end
            "open": 50.0, "high": 50.8, "low": 49.8, "close": 50.7,
            "volume": vol_by_h1,
            "vwap": vwap_by_h1,
            "cum_volume": 300, # Doc 7 cum_volume
            "bar_count": 2,
            "source": "SRC2"
        },
         {
            "bar_meta_data": {"symbol": "C", "exch_id": "X", "bar_type": "OneHour"},
            "start_time": "2023-10-26T09:00:00Z", # Doc 8 start
            "end_time": "2023-10-26T09:01:59Z",   # Doc 9 end
            "open": 20.0, "high": 20.1, "low": 19.9, "close": 20.0,
            "volume": vol_cx_h1,
            "vwap": vwap_cx_h1,
            "cum_volume": 0, # Doc 9 cum_volume
            "bar_count": 2,
            "source": "SRC3"
        },
    ])
    expected_output.sort(key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol, x.start_time))

    # removing id field from results from query
    for obj in result:
        obj.id = None
    assert result == expected_output


def test_aggregation_filtering_exchange(sample_bar_data_2_set_up):
    """ Verify filtering by exchange ID works. """
    target_bar_type = "OneHour"
    start_time = pendulum.datetime(2023, 10, 26, 9, 0, 0, tz="UTC")
    end_time = pendulum.datetime(2023, 10, 26, 9, 59, 59, tz="UTC")
    exch_list = ["Y"] # Only select data for exchange Y

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(target_bar_type, end_time, start_time,
                                                                                exch_id_list=exch_list)

    # Expected: Only the B/Y bar from the 9:xx hour
    vol_by_h1 = 300
    vwap_by_h1 = 50.2
    expected_output = BarDataBaseModel.from_dict_list([
        {
            "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneHour"},
            "start_time": "2023-10-26T09:02:00Z",
            "end_time": "2023-10-26T09:03:59Z",
            "open": 50.0, "high": 50.8, "low": 49.8, "close": 50.7,
            "volume": vol_by_h1,
            "vwap": vwap_by_h1,
            "cum_volume": 300,
            "bar_count": 2,
            "source": "SRC2"
        }
    ])

    # removing id field from results from query
    for obj in result:
        obj.id = None
    assert result == expected_output

def test_aggregation_filtering_time(sample_bar_data_2_set_up):
    """ Verify time filtering excludes data outside the range. """
    target_bar_type = "OneDay"
    # Time range only covers part of 9:xx hour, excludes doc 10 (prev day) and doc 5 (10:xx)
    start_time = pendulum.datetime(2023, 10, 26, 9, 1, 0, tz="UTC") # Starts *after* first bar
    end_time = pendulum.datetime(2023, 10, 26, 9, 59, 0, tz="UTC")   # Ends *before* 10:00 bar

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(target_bar_type,
                                                                                start_time=start_time,
                                                                                end_time=end_time)

    # --- Expected Output (Calculated Manually) ---
    # Only documents within the specified time AND having bar_type "OneMin"
    # Day aggregation for 2023-10-26:
    # Bar A/X: Docs 2, 3, 4 (Doc 1 is before start_time)
    vol_ax_d1 = 1200 + 500 + 800 # = 2500
    vwap_num_ax_d1 = (100.8*1200) + (101.0*500) + (102.1*800) # = 120960 + 50500 + 81680 = 253140
    vwap_ax_d1 = vwap_num_ax_d1 / vol_ax_d1 # ~101.256
    # Bar B/Y: Docs 6, 7
    vol_by_d1 = 300
    vwap_by_d1 = 50.2
    # Bar C/X: Doc 9 (Doc 8 is before start_time)
    vol_cx_d1 = 0
    vwap_cx_d1 = None

    expected_output = BarDataBaseModel.from_dict_list([
        {   # Bar A/X for 2023-10-26
            "bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneDay"},
            "start_time": "2023-10-26T09:01:00Z", # Doc 2 start
            "end_time": "2023-10-26T09:58:59Z",   # Doc 4 end
            "open": 100.5, # Doc 2 open
            "high": 102.5, # Doc 4 high
            "low": 100.0,  # Doc 2 low
            "close": 102.2, # Doc 4 close
            "volume": vol_ax_d1,
            "vwap": vwap_ax_d1,
            "cum_volume": 3500, # Doc 4 cum_volume
            "bar_count": 3,
            "source": "Mixed: SRC1 + SRC1_XYZ"
        },
        {   # Bar B/Y for 2023-10-26
            "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneDay"},
            "start_time": "2023-10-26T09:02:00Z",
            "end_time": "2023-10-26T09:03:59Z",
            "open": 50.0, "high": 50.8, "low": 49.8, "close": 50.7,
            "volume": vol_by_d1,
            "vwap": vwap_by_d1,
            "cum_volume": 300,
            "bar_count": 2,
            "source": "SRC2"
        },
         {   # Bar C/X for 2023-10-26
            "bar_meta_data": {"symbol": "C", "exch_id": "X", "bar_type": "OneDay"},
            "start_time": "2023-10-26T09:01:00Z", # Doc 9 start
            "end_time": "2023-10-26T09:01:59Z",   # Doc 9 end
            "open": 20.0, "high": 20.1, "low": 19.9, "close": 20.0,
            "volume": vol_cx_d1,
            "vwap": vwap_cx_d1,
            "cum_volume": 0,
            "bar_count": 1,
            "source": "SRC3"
        },
    ])
    expected_output.sort(key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol, x.start_time))
    # removing id field from results from query
    for obj in result:
        obj.id = None
    assert result == expected_output


def test_aggregation_no_matching_data(sample_bar_data_2_set_up):
    """ Verify returns empty list when no source data matches filters. """

    target_bar_type = "OneHour"
    start_time = pendulum.datetime(2023, 10, 27, 9, 0, 0, tz="UTC") # Future date
    end_time = pendulum.datetime(2023, 10, 27, 10, 0, 0, tz="UTC")

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(target_bar_type,
                                                                                start_time=start_time,
                                                                                end_time=end_time)

    assert result == []


def test_aggregation_latest_n_basic(sample_bar_data_2_set_up):
    """ Verify fetching the latest N bars using target_bar_counts. """
    target_bar_type = "OneHour"
    target_counts = 2 # Request latest 2 hourly bars
    # Set end time such that both 9:xx and 10:xx bars for A/X exist before it
    end_time = pendulum.datetime(2023, 10, 26, 10, 30, 0, tz="UTC")

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(
        target_bar_type=target_bar_type,
        target_bar_counts=target_counts, # Use target_bar_counts
        end_time=end_time
    )

    # Expected Output: The last 2 hourly bars from the sample data before end_time
    # 1. A/X 10:00 bar (latest)
    # 2. C/X 09:00 bar (next latest - using start_time as primary sort for latest)
    #    OR A/X 09:00 bar (depending on secondary sort if start times are identical,
    #                      which isn't the case here, but important if data changes)
    #    Let's assume sort is stable or start_time is unique enough.
    #    Based on sample data start times: 10:00 (A/X), 09:02 (B/Y), 09:00 (A/X), 09:00 (C/X)
    #    The two latest start times before 10:30 are 10:00 (A/X) and 09:02 (B/Y)

    # Expected bar A/X 10:00-10:59 (Doc 5)
    vol_ax_h2 = 1500; vwap_ax_h2 = 102.5
    # Expected bar B/Y 09:00-09:59 (Docs 6, 7)
    vol_by_h1 = 300; vwap_by_h1 = 50.2

    expected_output = BarDataBaseModel.from_dict_list([
         # Bar A/X @ 10:00 is latest
         {"bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "OneHour"}, "start_time": "2023-10-26T10:00:00Z", "end_time": "2023-10-26T10:00:59Z", "open": 102.2, "high": 103.0, "low": 102.0, "close": 102.8, "volume": vol_ax_h2, "vwap": vwap_ax_h2, "cum_volume": 5000, "bar_count": 1, "source": "SRC1"},
         # Bar B/Y @ 09:02 is second latest start_time overall
         {"bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneHour"}, "start_time": "2023-10-26T09:02:00Z", "end_time": "2023-10-26T09:03:59Z", "open": 50.0, "high": 50.8, "low": 49.8, "close": 50.7, "volume": vol_by_h1, "vwap": vwap_by_h1, "cum_volume": 300, "bar_count": 2, "source": "SRC2"},
    ])
    # The result should already be sorted ascending by the pipeline's last stage
    expected_output.sort(key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol, x.start_time))

    assert len(result) == target_counts
    for obj in result: obj.id = None
    assert result == expected_output


def test_aggregation_latest_n_with_filter(sample_bar_data_2_set_up):
    """ Verify fetching latest N bars with symbol filter. """
    target_bar_type = "FiveMin"
    target_counts = 2
    symbol_list = ["A"] # Only symbol A
    end_time = pendulum.datetime(2023, 10, 26, 9, 10, 0, tz="UTC")

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(
        target_bar_type=target_bar_type,
        target_bar_counts=target_counts, # Use target_bar_counts
        symbol_list=symbol_list,          # Apply filter
        end_time=end_time
    )

    # Expected: Latest 2 FiveMin bars for Symbol A before 9:10
    # 1. Bar A/X 09:05 (start_time 09:05)
    # 2. Bar A/X 09:00 (start_time 09:00)
    vwap_ax_1 = ((100.2 * 1000) + (100.8 * 1200)) / (1000 + 1200)
    vwap_ax_2 = 101.0
    expected_output = BarDataBaseModel.from_dict_list([
        {"bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "FiveMin"}, "start_time": "2023-10-26T09:00:00Z", "end_time": "2023-10-26T09:01:59Z", "open": 100.0, "high": 101.5, "low": 99.5, "close": 101.0, "volume": 2200, "vwap": vwap_ax_1, "cum_volume": 2200, "bar_count": 2, "source": "Mixed: SRC1 + SRC1_XYZ"},
        {"bar_meta_data": {"symbol": "A", "exch_id": "X", "bar_type": "FiveMin"}, "start_time": "2023-10-26T09:05:00Z", "end_time": "2023-10-26T09:05:59Z", "open": 101.0, "high": 101.2, "low": 100.8, "close": 101.1, "volume": 500, "vwap": vwap_ax_2, "cum_volume": 2700, "bar_count": 1, "source": "SRC1"},
    ])
    expected_output.sort(key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol, x.start_time))

    assert len(result) == target_counts
    for obj in result: obj.id = None
    assert result == expected_output

def test_aggregation_latest_n_exceeds_available(sample_bar_data_2_set_up):
    """ Verify fetching N bars when fewer than N are available. """
    target_bar_type = "OneHour"
    target_counts = 10 # Request 10 bars
    symbol_list = ["B"]  # Only Symbol B
     # End time only allows the one 9:xx bar for B/Y
    end_time = pendulum.datetime(2023, 10, 26, 9, 30, 0, tz="UTC")

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(
        target_bar_type=target_bar_type,
        target_bar_counts=target_counts,
        symbol_list=symbol_list,
        end_time=end_time
    )

    # Expected: Only the single B/Y bar from the 9:xx hour should be returned
    vol_by_h1 = 300
    vwap_by_h1 = 50.2
    expected_output = BarDataBaseModel.from_dict_list([
        {"bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "OneHour"}, "start_time": "2023-10-26T09:02:00Z", "end_time": "2023-10-26T09:03:59Z", "open": 50.0, "high": 50.8, "low": 49.8, "close": 50.7, "volume": vol_by_h1, "vwap": vwap_by_h1, "cum_volume": 300, "bar_count": 2, "source": "SRC2"}
    ])

    assert len(result) == 1 # Should return only the 1 available bar
    for obj in result: obj.id = None
    assert result == expected_output


def test_aggregation_volume_null_handling(sample_bar_data_2_set_up):
    """
    Verify that volume aggregation correctly handles null values by treating them as 0.
    Uses specific documents from SAMPLE_BAR_DATA2 (docs 6 and 7 for B/Y).
    """
    target_bar_type = "FiveMin" # Or any interval that groups docs 6 & 7

    # Define a time range that specifically captures docs 6 and 7 (symbol B, exch Y)
    # Doc 6 start_time: 2023-10-26 09:02:00 UTC
    # Doc 7 start_time: 2023-10-26 09:03:00 UTC
    # Both fall within the 09:00-09:04 (FiveMin) interval if interval starts at 09:00.
    # More precisely, they fall into the FiveMin bucket starting at 09:00:00.
    start_time = pendulum.datetime(2023, 10, 26, 9, 0, 0, tz="UTC")
    end_time = pendulum.datetime(2023, 10, 26, 9, 4, 59, tz="UTC") # Ensure only this 5-min interval

    exch_list = ["Y"]
    symbol_list = ["B"]

    result = dept_book_service_web_client.get_aggregated_bar_data_query_client(
        target_bar_type=target_bar_type,
        start_time=start_time,
        end_time=end_time,
        exch_id_list=exch_list,
        symbol_list=symbol_list
    )

    # SAMPLE_BAR_DATA2 relevant entries:
    # Doc 6 (Symbol B, Exch Y): volume = 300
    # Doc 7 (Symbol B, Exch Y): volume = None

    # Expected volume sum: 300 (from Doc 6) + 0 (from Doc 7, as null is treated as 0) = 300
    expected_volume_sum = 300
    vwap_by_1 = (50.2 * 300) / 300 # Doc 6 vwap * Doc 6 volume / Doc 6 volume

    # Construct the full expected output for this specific aggregated bar
    expected_output_list = BarDataBaseModel.from_dict_list([
        {
            "bar_meta_data": {"symbol": "B", "exch_id": "Y", "bar_type": "FiveMin"},
            "start_time": "2023-10-26T09:02:00Z", # First doc in group (Doc 6)
            "end_time": "2023-10-26T09:03:59Z",   # Last doc in group (Doc 7)
            "open": 50.0,  # Doc 6 open
            "high": 50.8,  # Doc 7 high
            "low": 49.8,   # Doc 6 low
            "close": 50.7, # Doc 7 close
            "volume": expected_volume_sum, # Key assertion here
            "vwap": vwap_by_1,
            "cum_volume": 300, # Doc 7 cum_volume (last value)
            "bar_count": 2,    # Two 1-min bars aggregated
            "source": "SRC2"   # Doc 6 source
        }
    ])
    # Ensure the sort chore matches what the client/pipeline would produce
    expected_output_list.sort(key=lambda x: (x.bar_meta_data.exch_id, x.bar_meta_data.symbol, x.start_time))


    assert len(result) == 1, "Expected exactly one aggregated bar for B/Y in this narrow time frame"

    # Clean result (remove db-generated id if present and sort if multiple results were possible)
    # Since we expect 1, sorting isn't strictly needed for comparison if the list has 1 item.
    for obj in result:
        obj.id = None # Assuming BarDataBaseModel might have an 'id' or '_id'

    # Direct comparison of the single expected item with the single result item
    assert result == expected_output_list, "Aggregated bar data does not match expected output for null volume handling."
    assert result[0].volume == expected_volume_sum, f"Aggregated volume incorrect. Expected {expected_volume_sum}, got {result[0].volume}"
