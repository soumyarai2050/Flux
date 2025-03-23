import copy
import os
import random
import time
from typing import List

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
        dash_obj.rt_dash.indicative_summary = InventorySummary.from_kwargs(cum_qty=random.randint(50, 100),
                                                                           usd_notional=random.randint(50, 100))
        dash_obj.rt_dash.locate_summary = InventorySummary.from_kwargs(cum_qty=random.randint(50, 100),
                                                                           usd_notional=random.randint(50, 100))
        dash_obj.rt_dash.pth_summary = InventorySummary.from_kwargs(cum_qty=random.randint(50, 100),
                                                                           usd_notional=random.randint(50, 100))
        dash_obj.rt_dash.sod_summary = InventorySummary.from_kwargs(cum_qty=random.randint(50, 100),
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
    # 7. filters dash with having rt_dash.locate_summary and rt_dash.locate_summary.usd_notional >= dash_filters.optimizer_criteria.min_notional
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
    dash_filters_obj.optimizer_criteria = OptimizerCriteriaBaseModel.from_kwargs(pos_type=PositionType.LOCATE,
                                                                                 min_notional=70)
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
        assert filtered_dash.rt_dash.locate_summary.usd_notional >= dash_filters_obj.optimizer_criteria.min_notional, \
            f"Mismatched: {filtered_dash.rt_dash.locate_summary.usd_notional=} not >= {dash_filters_obj.optimizer_criteria.min_notional=}"

    # dash_filters that
    # 1. filters dash with required_leg_type = LegType_CB or LegType_EQT_A
    # 2. filters dash_filer.px_range.px_low < dash.rt_dash.leg < dash_filer.px_range.px_high
    # 3. filters dash_filters.premium_range.premium_low < dash.rt_dash.mkt_premium < dash_filters.premium_range.premium_high
    # 4. filters dash_filters.premium_change_range.premium_change_low < dash.rt_dash.mkt_premium_change < dash_filters.premium_change_range.premium_change_high
    # 5. filters dash with having positions with type any
    # 6. filters dash with having ashare_locate_requests if dash_filters.has_ashare_locate_request is True
    # 7. filters dash with having rt_dash.locate_summary and rt_dash.locate_summary.usd_notional >= dash_filters.optimizer_criteria.min_notional
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
    dash_filters_obj.optimizer_criteria = OptimizerCriteriaBaseModel.from_kwargs(pos_type=PositionType.LOCATE,
                                                                                 min_notional=70)
    dash_filters_obj.sort_criteria = SortCriteriaBaseModel.from_kwargs(level1="rt_dash.pth_summary.usd_notional",
                                                                       level1_chore=SortType.ASCENDING)
    stored_dash_filters_obj = dept_book_service_web_client.create_dash_filters_client(dash_filters_obj)
    dash_filters_ids.append(str(stored_dash_filters_obj.id))
    # checking filter with this dash_name
    filtered_dash_list = dept_book_service_web_client.filtered_dash_by_dash_filters_query_client(
        dash_filters_obj.dash_name)
    assert len(filtered_dash_list) > 0, \
        f"Mismatched: {len(filtered_dash_list)=} !> 0"
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
        for broker in filtered_dash.rt_dash.eligible_brokers:
            assert len(broker.sec_positions) > 0, \
                f"Mismatched: {len(broker.sec_positions)=} !> 0"
            for sec_pos in broker.sec_positions:
                assert len(sec_pos.positions) > 0, \
                    f"Mismatched: {len(sec_pos.positions)=} !> 0"
                for pos in sec_pos.positions:
                    expected_type = [PositionType.PTH, PositionType.LOCATE, PositionType.SOD,
                                     PositionType.INDICATIVE]
                    if pos.type not in expected_type:
                        assert False, f"Mismatched: {pos.type=} not in {expected_type=}"
        assert len(filtered_dash.rt_dash.ashare_locate_requests) > 0, \
            f"Mismatched: {len(filtered_dash.rt_dash.ashare_locate_requests)=} !> 0 when {dash_filters_obj.has_ashare_locate_request=}"
        assert filtered_dash.rt_dash.locate_summary.usd_notional >= dash_filters_obj.optimizer_criteria.min_notional, \
            f"Mismatched: {filtered_dash.rt_dash.locate_summary.usd_notional=} not >= {dash_filters_obj.optimizer_criteria.min_notional=}"

    pth_sum_usd_notional_list = []
    for filtered_dash in filtered_dash_list:
        pth_sum_usd_notional_list.append(filtered_dash.rt_dash.pth_summary.usd_notional)

    expected_sorted_list = copy.deepcopy(pth_sum_usd_notional_list)
    expected_sorted_list.sort()
    assert pth_sum_usd_notional_list == expected_sorted_list, \
        (f"Mismatched: filtered_dash not sorted based on pth_summary.usd_notional, {expected_sorted_list=}, "
         f"{pth_sum_usd_notional_list=}")
