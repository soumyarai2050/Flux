# standard imports
import asyncio
import math
import concurrent.futures
import time
from typing import Set

import numpy as np
import pytest
import random
import traceback

# project imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import get_strat_key_from_pair_strat
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import AlertOptional
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import *

email_book_service_beanie_web_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient.set_or_get_if_instance_exists(HOST, parse_to_int(PAIR_STRAT_BEANIE_PORT))
email_book_service_cache_web_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient.set_or_get_if_instance_exists(HOST, parse_to_int(PAIR_STRAT_CACHE_PORT))

if email_book_service_beanie_web_client.port == email_book_service_native_web_client.port:
    clients_list = [email_book_service_beanie_web_client]
else:
    clients_list = [email_book_service_beanie_web_client, email_book_service_cache_web_client]


# test cases requires phone_book and log_book database to be present
def test_deep_clean_database_n_logs():
    drop_all_databases()
    clean_project_logs()


def test_clean_database_n_logs():
    clean_all_collections_ignoring_ui_layout()
    clean_project_logs()


def _test_sanity_create_strat_parallel(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
                                       expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
                                       market_depth_basemodel_list):
    max_count = int(len(buy_sell_symbol_list)/2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_count) as executor:
        results = [executor.submit(create_n_activate_strat, buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_start_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), None, None)
                   for buy_symbol, sell_symbol in buy_sell_symbol_list[:max_count]]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


@pytest.mark.nightly
def test_clean_and_set_limits(clean_and_set_limits):
    pass


@pytest.mark.nightly
def test_patch_with_missing_id_param(get_missing_id_json):
    sample_json, sample_model_type = get_missing_id_json

    # removing all id fields
    del sample_json['_id']
    del sample_json['field1']['_id']
    del sample_json['field2'][0]['_id']
    del sample_json['field2'][1]['_id']
    del sample_json['field2'][2]['_id']
    del sample_json['field3']['_id']
    del sample_json['field4'][0]['_id']
    del sample_json['field4'][1]['_id']
    del sample_json['field4'][2]['_id']
    del sample_json['field6']['_id']

    assign_missing_ids_n_handle_date_time_type(sample_model_type, sample_json)

    print(sample_json)
    assert sample_json['field1'].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field1']['_id']"
    assert sample_json['field2'][0].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field2'][0]['_id']"
    assert sample_json['field2'][1].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field2'][1]['_id']"
    assert sample_json['field2'][2].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field2'][2]['_id']"
    assert sample_json['field3'].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field3']['_id']"
    assert sample_json['field4'][0].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field4'][0]['_id']"
    assert sample_json['field4'][1].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field4'][1]['_id']"
    assert sample_json['field4'][2].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field4'][2]['_id']"
    assert sample_json['field6'].get('_id') is not None, \
        "assign_missing_ids_n_handle_date_time_type failed to set sample_json['field6']['_id']"

@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_create_get_put_patch_delete_chore_limits_client(clean_and_set_limits, web_client):
    for index, return_type_param in enumerate([True, None, False]):
        chore_limits_obj = ChoreLimitsBaseModel(id=2 + index, max_px_deviation=2)
        # testing create_chore_limits_client()
        created_chore_limits_obj = web_client.create_chore_limits_client(chore_limits_obj,
                                                                         return_obj_copy=return_type_param)
        if return_type_param:
            assert created_chore_limits_obj == chore_limits_obj, \
                f"Created obj {created_chore_limits_obj} mismatched expected chore_limits_obj {chore_limits_obj}"
        else:
            assert created_chore_limits_obj

        # checking if created obj present in get_all objects
        fetched_chore_limits_list = web_client.get_all_chore_limits_client()
        assert chore_limits_obj in fetched_chore_limits_list, \
            f"Couldn't find expected chore_limits_obj {chore_limits_obj} in get-all fetched list of objects"

        # Checking get_by_id client
        fetched_chore_limits_obj = web_client.get_chore_limits_client(chore_limits_obj.id)
        assert fetched_chore_limits_obj == chore_limits_obj, \
            f"Mismatched expected chore_limits_obj {chore_limits_obj} from " \
            f"fetched_chore_limits obj fetched by get_by_id {fetched_chore_limits_obj}"

        # checking put operation client
        chore_limits_obj.max_basis_points = 2
        updated_chore_limits_obj = web_client.put_chore_limits_client(chore_limits_obj,
                                                                      return_obj_copy=return_type_param)
        if return_type_param:
            assert updated_chore_limits_obj == chore_limits_obj, \
                f"Mismatched expected chore_limits_obj: {chore_limits_obj} from updated obj: {updated_chore_limits_obj}"
        else:
            assert updated_chore_limits_obj

        # checking patch operation client
        patch_chore_limits_obj = ChoreLimitsBaseModel(id=chore_limits_obj.id, max_px_levels=2)
        # making changes to expected_obj
        chore_limits_obj.max_px_levels = patch_chore_limits_obj.max_px_levels

        patch_updated_chore_limits_obj = \
            web_client.patch_chore_limits_client(json.loads(patch_chore_limits_obj.model_dump_json(by_alias=True,
                                                                                                   exclude_none=True)),
                                                 return_obj_copy=return_type_param)
        if return_type_param:
            assert patch_updated_chore_limits_obj == chore_limits_obj, \
                f"Mismatched expected obj: {chore_limits_obj} from patch updated obj {patch_updated_chore_limits_obj}"
        else:
            assert patch_updated_chore_limits_obj

        # checking delete operation client
        delete_resp = web_client.delete_chore_limits_client(chore_limits_obj.id, return_obj_copy=return_type_param)
        if return_type_param:
            assert isinstance(delete_resp, dict), \
                f"Mismatched type of delete resp, expected dict received {type(delete_resp)}"
            assert delete_resp.get("id") == chore_limits_obj.id, \
                f"Mismatched delete resp id, expected {chore_limits_obj.id} received {delete_resp.get('id')}"
        else:
            assert delete_resp


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_post_all(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        chore_limits_objects_list = [
            ChoreLimitsBaseModel(id=2 + (index * 3), max_px_deviation=2),
            ChoreLimitsBaseModel(id=3 + (index * 3), max_px_deviation=3),
            ChoreLimitsBaseModel(id=4 + (index * 3), max_px_deviation=4)
        ]

        fetched_email_book_beanie = web_client.get_all_chore_limits_client()

        for obj in chore_limits_objects_list:
            assert obj not in fetched_email_book_beanie, f"Object {obj} must not be present in get-all list " \
                                                            f"{fetched_email_book_beanie} before post-all operation"

        return_value = web_client.create_all_chore_limits_client(chore_limits_objects_list,
                                                                 return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        fetched_email_book_beanie = web_client.get_all_chore_limits_client()

        for obj in chore_limits_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_put_all(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        chore_limits_objects_list = [
            ChoreLimitsBaseModel(id=2 + (index * 3), max_px_deviation=2),
            ChoreLimitsBaseModel(id=3 + (index * 3), max_px_deviation=3),
            ChoreLimitsBaseModel(id=4 + (index * 3), max_px_deviation=4)
        ]

        web_client.create_all_chore_limits_client(chore_limits_objects_list)

        fetched_email_book_beanie = web_client.get_all_chore_limits_client()

        for obj in chore_limits_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"

        # updating values
        for obj in chore_limits_objects_list:
            obj.max_contract_qty = obj.id

        return_value = web_client.put_all_chore_limits_client(chore_limits_objects_list,
                                                              return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        updated_chore_limits_list = web_client.get_all_chore_limits_client()

        for expected_obj in chore_limits_objects_list:
            assert expected_obj in updated_chore_limits_list, \
                f"expected obj {expected_obj} not found in updated list of objects: {updated_chore_limits_list}"


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_patch_all(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        portfolio_limits_objects_list = [
            PortfolioLimitsBaseModel(id=2 + (index * 3), max_open_baskets=20),
            PortfolioLimitsBaseModel(id=3 + (index * 3), max_open_baskets=30),
            PortfolioLimitsBaseModel(id=4 + (index * 3), max_open_baskets=45)
        ]

        web_client.create_all_portfolio_limits_client(portfolio_limits_objects_list)

        fetched_get_all_obj_list = web_client.get_all_portfolio_limits_client()

        for obj in portfolio_limits_objects_list:
            assert obj in fetched_get_all_obj_list, f"Couldn't find object {obj} in get-all list " \
                                                    f"{fetched_get_all_obj_list}"

        # updating values
        portfolio_limits_objects_json_list = []
        for obj in portfolio_limits_objects_list:
            obj.eligible_brokers = []
            for broker_obj_id in [1, 2]:
                broker = broker_fixture()
                broker.id = f"{broker_obj_id}"
                broker.bkr_priority = broker_obj_id
                obj.eligible_brokers.append(broker)
            portfolio_limits_objects_json_list.append(jsonable_encoder(obj, by_alias=True, exclude_none=True))

        return_value = web_client.patch_all_portfolio_limits_client(portfolio_limits_objects_json_list,
                                                                    return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        for expected_obj in portfolio_limits_objects_list:
            updated_portfolio_limits = web_client.get_portfolio_limits_client(portfolio_limits_id=expected_obj.id)
            assert expected_obj.model_dump() == updated_portfolio_limits.model_dump(), \
                f"Mismatched: expected obj {expected_obj} received {updated_portfolio_limits}"

        delete_broker = BrokerOptional()
        delete_broker.id = "1"

        delete_obj = PortfolioLimitsBaseModel(id=4 + (index * 3), eligible_brokers=[delete_broker])
        delete_obj_json = jsonable_encoder(delete_obj, by_alias=True, exclude_none=True)

        web_client.patch_all_portfolio_limits_client([delete_obj_json])

        updated_portfolio_limits = web_client.get_portfolio_limits_client(portfolio_limits_id=4)

        assert delete_broker.id not in [broker.id for broker in updated_portfolio_limits.eligible_brokers], \
            f"Deleted obj: {delete_obj} using patch still found in updated object: {updated_portfolio_limits}"


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_create_get_put_patch_delete_time_series_model(clean_and_set_limits, web_client):
    for index, return_type_param in enumerate([True, None, False]):
        formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        sample_ts_model_obj = SampleTSModelBaseModel(_id=index+1, sample=f"sample{index}",
                                                     date=pendulum.parse(formatted_dt_utc))
        # testing create_chore_limits_client()
        created_sample_ts_model_obj = web_client.create_sample_ts_model_client(sample_ts_model_obj,
                                                                               return_obj_copy=return_type_param)
        if return_type_param:
            assert created_sample_ts_model_obj == sample_ts_model_obj, \
                (f"Created obj {created_sample_ts_model_obj} mismatched expected "
                 f"sample_ts_model_obj {sample_ts_model_obj}")
        else:
            assert created_sample_ts_model_obj

        # checking if created obj present in get_all objects
        fetched_sample_ts_model_list = web_client.get_all_sample_ts_model_client()
        assert sample_ts_model_obj in fetched_sample_ts_model_list, \
            f"Couldn't find expected sample_ts_model_obj {sample_ts_model_obj} in get-all fetched list of objects"

        # Checking get_by_id client
        fetched_sample_ts_model_obj = web_client.get_sample_ts_model_client(sample_ts_model_obj.id)
        assert fetched_sample_ts_model_obj == sample_ts_model_obj, \
            f"Mismatched expected sample_ts_model_obj {sample_ts_model_obj} from " \
            f"fetched_sample_ts_model_obj fetched by get_by_id {fetched_sample_ts_model_obj}"

        # checking put operation client
        sample_ts_model_obj.sample = f"sample{index}{index}"
        formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        sample_ts_model_obj.date = pendulum.parse(formatted_dt_utc)
        updated_sample_ts_model_obj = web_client.put_sample_ts_model_client(sample_ts_model_obj,
                                                                            return_obj_copy=return_type_param)
        if return_type_param:
            assert updated_sample_ts_model_obj == sample_ts_model_obj, \
                (f"Mismatched expected sample_ts_model_obj: {sample_ts_model_obj} "
                 f"from updated obj: {updated_sample_ts_model_obj}")
        else:
            assert updated_sample_ts_model_obj

        # checking patch operation client
        patch_sample_ts_model_obj = SampleTSModelBaseModel(id=sample_ts_model_obj.id,
                                                           sample=f"sample{index}{index}")
        # making changes to expected_obj
        sample_ts_model_obj.sample = patch_sample_ts_model_obj.sample

        patch_updated_sample_ts_model_obj = \
            web_client.patch_sample_ts_model_client(json.loads(patch_sample_ts_model_obj.model_dump_json(
                by_alias=True, exclude_none=True)), return_obj_copy=return_type_param)
        if return_type_param:
            assert patch_updated_sample_ts_model_obj == sample_ts_model_obj, \
                (f"Mismatched expected obj: {sample_ts_model_obj} from patch "
                 f"updated obj {patch_updated_sample_ts_model_obj}")
        else:
            assert patch_updated_sample_ts_model_obj

        # checking delete operation client
        delete_resp = web_client.delete_sample_ts_model_client(
            sample_ts_model_obj.id, return_obj_copy=return_type_param)
        if return_type_param:
            assert isinstance(delete_resp, dict), \
                f"Mismatched type of delete resp, expected dict received {type(delete_resp)}"
            assert delete_resp.get("id") == sample_ts_model_obj.id, \
                f"Mismatched delete resp id, expected {sample_ts_model_obj.id} received {delete_resp.get('id')}"
        else:
            assert delete_resp


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_post_all_time_series_model(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        sample_ts_model_objects_list = [
            SampleTSModelBaseModel(_id=2 + (index * 3), sample=f"sample-{2 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc)),
            SampleTSModelBaseModel(_id=3 + (index * 3), sample=f"sample-{3 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc)),
            SampleTSModelBaseModel(_id=4 + (index * 3), sample=f"sample-{4 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc))
        ]

        fetched_email_book_beanie = web_client.get_all_sample_ts_model_client()

        for obj in sample_ts_model_objects_list:
            assert obj not in fetched_email_book_beanie, f"Object {obj} must not be present in get-all list " \
                                                            f"{fetched_email_book_beanie} before post-all operation"

        return_value = web_client.create_all_sample_ts_model_client(sample_ts_model_objects_list,
                                                                    return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        fetched_email_book_beanie = web_client.get_all_sample_ts_model_client()

        for obj in sample_ts_model_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_put_all_time_series_model(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        sample_ts_model_objects_list = [
            SampleTSModelBaseModel(_id=2 + (index * 3), sample=f"sample-{2 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc)),
            SampleTSModelBaseModel(_id=3 + (index * 3), sample=f"sample-{3 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc)),
            SampleTSModelBaseModel(_id=4 + (index * 3), sample=f"sample-{4 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc))
        ]

        web_client.create_all_sample_ts_model_client(sample_ts_model_objects_list)

        fetched_email_book_beanie = web_client.get_all_sample_ts_model_client()

        for obj in sample_ts_model_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"
        # updating values
        for obj in sample_ts_model_objects_list:
            obj.sample = f"sample_{obj.id}"
            formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            obj.date = pendulum.parse(formatted_dt_utc)

        return_value = web_client.put_all_sample_ts_model_client(sample_ts_model_objects_list,
                                                                 return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        updated_sample_ts_model_list = web_client.get_all_sample_ts_model_client()

        for expected_obj in sample_ts_model_objects_list:
            assert expected_obj in updated_sample_ts_model_list, \
                f"expected obj {expected_obj} not found in updated list of objects: {updated_sample_ts_model_list}"


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_patch_all_time_series_model(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        sample_ts_model_objects_list = [
            SampleTSModelBaseModel(_id=2 + (index * 3), sample=f"sample-{2 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc)),
            SampleTSModelBaseModel(_id=3 + (index * 3), sample=f"sample-{3 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc)),
            SampleTSModelBaseModel(_id=4 + (index * 3), sample=f"sample-{4 + (index * 3)}",
                                   date=pendulum.parse(formatted_dt_utc))
        ]

        web_client.create_all_sample_ts_model_client(sample_ts_model_objects_list)

        fetched_email_book_beanie = web_client.get_all_sample_ts_model_client()

        for obj in sample_ts_model_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"
        # updating values
        for obj in sample_ts_model_objects_list:
            obj.sample = f"sample_{obj.id}"
            formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            obj.date = pendulum.parse(formatted_dt_utc)

        sample_ts_model_objects_json_list = [jsonable_encoder(obj, by_alias=True, exclude_none=True)
                                             for obj in sample_ts_model_objects_list]
        return_value = web_client.patch_all_sample_ts_model_client(sample_ts_model_objects_json_list,
                                                                   return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        updated_sample_ts_model_list = web_client.get_all_sample_ts_model_client()

        for expected_obj in sample_ts_model_objects_list:
            assert expected_obj in updated_sample_ts_model_list, \
                f"expected obj {expected_obj} not found in updated list of objects: {updated_sample_ts_model_list}"


# todo: currently contains beanie http call of sample models, once cache http is implemented test that too
@pytest.mark.parametrize("pydantic_basemodel", [SampleModelBaseModel, SampleTSModel1BaseModel])
# checking both JsonRoot and TimeSeries
def test_update_agg_feature_in_post_put_patch_http_call(static_data_, clean_and_set_limits,
                                                        pydantic_basemodel: Type[BaseModel]):
    """
    This test case contains check of update aggregate feature available in beanie part, put and patch http calls.
    """
    counter = 0
    for index in range(5):
        sample_model = pydantic_basemodel(_id=index+1, sample="sample", date=DateTime.utcnow(), num=index+1)
        created_obj: pydantic_basemodel = (
            email_book_service_native_web_client.create_sample_model_client(sample_model))

        counter += index+1
        assert created_obj.cum_sum_of_num == counter, \
            (f"Mismatched: aggregated update must have updated created_obj.cum_sum_of_num: {created_obj.cum_sum_of_num} "
             f"to {counter} after post operation")

        if index > 0:
            last_obj = email_book_service_native_web_client.get_sample_model_client(index)
            last_obj.num += 1
            counter += 1    # updating counter for comparison

            last_index_updated_obj = email_book_service_native_web_client.put_sample_model_client(last_obj)
            assert last_index_updated_obj.cum_sum_of_num == last_obj.cum_sum_of_num+1, \
                (f"Mismatched: aggregated update must have updated created_obj.cum_sum_of_num: "
                 f"{last_index_updated_obj.cum_sum_of_num} to {last_obj.cum_sum_of_num+1} after put operation")

            current_index_updated_obj = email_book_service_native_web_client.get_sample_model_client(index+1)
            assert current_index_updated_obj.cum_sum_of_num == counter, \
                (f"Mismatched: aggregated update must have updated cum_sum_of_num: "
                 f"{current_index_updated_obj.cum_sum_of_num} to {counter} after put operation")


# sanity test to create and activate pair_strat
@pytest.mark.nightly
def test_create_pair_strat(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                           expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                           market_depth_basemodel_list):
    # creates and activates multiple pair_strats
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        create_n_activate_strat(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                expected_strat_status_, symbol_overview_obj_list,
                                market_depth_basemodel_list)


def _place_sanity_chores(buy_symbol, sell_symbol, pair_strat_,
                         expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                         last_barter_fixture_list, market_depth_basemodel_list,
                         max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 111360
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_web_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        # Placing buy chores
        buy_ack_chore_id = None
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)

            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(executor_web_client, bid_buy_top_market_depth,
                                                               ask_sell_top_market_depth)
            ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               buy_symbol, executor_web_client,
                                                                               last_chore_id=buy_ack_chore_id)
            buy_ack_chore_id = ack_chore_journal.chore.chore_id

            if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                # Sleeping to let the chore get cxlled
                time.sleep(residual_wait_sec)

        # Placing sell chores
        sell_ack_chore_id = None
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)
            # required to make buy side tob latest
            run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], executor_web_client)

            update_tob_through_market_depth_to_place_sell_chore(executor_web_client, ask_sell_top_market_depth,
                                                                bid_buy_top_market_depth)

            ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               sell_symbol, executor_web_client,
                                                                               last_chore_id=sell_ack_chore_id)
            sell_ack_chore_id = ack_chore_journal.chore.chore_id

            if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                # Sleeping to let the chore get cxlled
                time.sleep(residual_wait_sec)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# sanity test to create chores
@pytest.mark.nightly
def test_place_sanity_chores(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                             expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                             last_barter_fixture_list, market_depth_basemodel_list,
                             buy_chore_, sell_chore_,
                             max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    _place_sanity_chores(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
                         symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
                         max_loop_count_per_side, refresh_sec_update_fixture)


def test_place_sanity_parallel_chores(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                      expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                      last_barter_fixture_list, market_depth_basemodel_list,
                                      buy_chore_, sell_chore_,
                                      max_loop_count_per_side, refresh_sec_update_fixture):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_chores, leg1_symbol, leg2_symbol, copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side,
                                   refresh_sec_update_fixture)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _place_sanity_complete_buy_chores(buy_symbol, sell_symbol, pair_strat_,
                                      expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                      last_barter_fixture_list, market_depth_basemodel_list,
                                      max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 111360
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        px = 10
        qty = 90
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client,
                           create_counts_per_side=2)

            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client)

            # ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
            #                                                                    buy_symbol, executor_web_client,
            #                                                                    last_chore_id=buy_ack_chore_id)
            # buy_ack_chore_id = ack_chore_journal.chore.chore_id
            # fills_journal = get_latest_fill_journal_from_chore_id(buy_ack_chore_id, executor_web_client)
        return buy_symbol, sell_symbol, created_pair_strat, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _place_sanity_complete_sell_chores(buy_symbol, sell_symbol, created_pair_strat,
                                       last_barter_fixture_list, max_loop_count_per_side, executor_web_client):

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing sell chores
        sell_ack_chore_id = None
        px = 110
        qty = 7
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client,
                           create_counts_per_side=2)
            sell_chore: ChoreJournal = place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client)
            ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               sell_symbol, executor_web_client,
                                                                               last_chore_id=sell_ack_chore_id)
            strat_status: StratStatusBaseModel = executor_web_client.get_strat_status_client(created_pair_strat.id)
            # time.sleep(2)
            strat_view: StratViewBaseModel = photo_book_web_client.get_strat_view_client(created_pair_strat.id)
            assert strat_status.balance_notional == strat_view.balance_notional, \
                f"Mismatched {strat_status.balance_notional = }, {strat_view.balance_notional = }"

            # ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
            #                                                                    sell_symbol, executor_web_client,
            #                                                                    last_chore_id=sell_ack_chore_id)
            sell_ack_chore_id = ack_chore_journal.chore.chore_id
            # fills_journal = get_latest_fill_journal_from_chore_id(sell_ack_chore_id, executor_web_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def test_place_sanity_parallel_complete_chores(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_portfolio_limits_, refresh_sec_update_fixture):
    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    temp_list = []
    max_loop_count_per_side = 10
    leg1_leg2_symbol_list = []
    for i in range(1, 21):
        leg1_leg2_symbol_list.append((f"CB_Sec_{i}", f"EQT_Sec_{i}"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_chores, leg1_symbol, leg2_symbol,
                                   copy.deepcopy(pair_strat_), copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side, refresh_sec_update_fixture)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client = future.result()
            temp_list.append((buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client))

    px = 10
    qty = 90
    strats_count = len(leg1_leg2_symbol_list)
    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert portfolio_status.overall_buy_notional == strats_count * max_loop_count_per_side * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_buy_notional must be "
         f"{strats_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, found "
         f"{portfolio_status.overall_buy_notional}")
    assert (portfolio_status.overall_buy_fill_notional ==
            strats_count * max_loop_count_per_side * qty * get_px_in_usd(px)), \
        (f"Mismatched: overall_buy_fill_notional must be "
         f"{strats_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, "
         f"found {portfolio_status.overall_buy_fill_notional}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(temp_list)) as executor:
        results = [executor.submit(_place_sanity_complete_sell_chores, buy_symbol_, sell_symbol_,
                                   created_pair_strat, copy.deepcopy(last_barter_fixture_list),
                                   max_loop_count_per_side, executor_web_client)
                   for buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client in temp_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    px = 110
    qty = 7
    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert portfolio_status.overall_sell_notional == strats_count * max_loop_count_per_side * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_sell_notional must be "
         f"{strats_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, found "
         f"{portfolio_status.overall_sell_notional}")
    assert (portfolio_status.overall_sell_fill_notional ==
            strats_count * max_loop_count_per_side * qty * get_px_in_usd(px)), \
        (f"Mismatched: overall_sell_fill_notional must be "
         f"{strats_count * max_loop_count_per_side * qty * get_px_in_usd(px)}, "
         f"found {portfolio_status.overall_sell_fill_notional}")
    return created_pair_strat, executor_web_client


def _place_sanity_complete_buy_chores_with_pair_strat(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 111360
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_web_client = move_snoozed_pair_strat_to_ready_n_then_active(
        pair_strat_, market_depth_basemodel_list, symbol_overview_obj_list,
        expected_strat_limits_, expected_strat_status_)

    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        px = 10
        qty = 90
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client,
                           create_counts_per_side=2)

            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client)

            # ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
            #                                                                    buy_symbol, executor_web_client,
            #                                                                    last_chore_id=buy_ack_chore_id)
            # buy_ack_chore_id = ack_chore_journal.chore.chore_id
            # fills_journal = get_latest_fill_journal_from_chore_id(buy_ack_chore_id, executor_web_client)
        return buy_symbol, sell_symbol, active_pair_strat, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_place_sanity_parallel_complete_chores_to_check_strat_view(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_portfolio_limits_, refresh_sec_update_fixture):
    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
    expected_portfolio_limits_.max_open_baskets = 51
    expected_portfolio_limits_.max_gross_n_open_notional = 5_000_000
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    temp_list = []
    max_loop_count_per_side = 50
    leg1_leg2_symbol_list = []
    total_strats = 20
    pair_strat_list = []
    for i in range(1, total_strats+1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_chores_with_pair_strat, leg1_leg2_symbol_tuple[0],
                                   leg1_leg2_symbol_tuple[1], pair_strat_list[idx],
                                   copy.deepcopy(expected_strat_limits_), copy.deepcopy(expected_strat_status_),
                                   copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side, refresh_sec_update_fixture)
                   for idx, leg1_leg2_symbol_tuple in enumerate(leg1_leg2_symbol_list)]

        done, not_done = concurrent.futures.wait(
            results, return_when=concurrent.futures.FIRST_EXCEPTION
        )
        if not_done:
            # at least one future has raised - you can return here
            # or propagate the exception
            # list(not_done)[0].result()  # re-raises exception here
            if list(not_done)[0].exception() is not None:
                raise Exception(list(not_done)[0].exception())

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client = future.result()
            temp_list.append((buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client))

    px = 10
    qty = 90
    strats_count = len(leg1_leg2_symbol_list)
    strat_view_list = photo_book_web_client.get_all_strat_view_client()
    expected_balance_notional = (expected_strat_limits_.max_single_leg_notional -
                                 strats_count * max_loop_count_per_side * qty * get_px_in_usd(px))
    for strat_view in strat_view_list:
        assert (strat_view.balance_notional == expected_balance_notional,
           (f"Mismatched: overall_buy_notional must be "
            f"{expected_balance_notional}, found {strat_view.balance_notional}"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(temp_list)) as executor:
        results = [executor.submit(_place_sanity_complete_sell_chores, buy_symbol_, sell_symbol_,
                                   created_pair_strat, copy.deepcopy(last_barter_fixture_list),
                                   max_loop_count_per_side, executor_web_client)
                   for buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client in temp_list]

        if not_done:
            # at least one future has raised - you can return here
            # or propagate the exception
            # list(not_done)[0].result()  # re-raises exception here
            if list(not_done)[0].exception() is not None:
                raise Exception(list(not_done)[0].exception())

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    px = 110
    qty = 7
    strats_count = len(leg1_leg2_symbol_list)
    strat_view_list = photo_book_web_client.get_all_strat_view_client()
    expected_balance_notional = (expected_strat_limits_.max_single_leg_notional -
                                 strats_count * max_loop_count_per_side * qty * get_px_in_usd(px))
    for strat_view in strat_view_list:
        assert (strat_view.balance_notional == expected_balance_notional,
                (f"Mismatched: overall_buy_notional must be "
                 f"{expected_balance_notional}, found {strat_view.balance_notional}"))
    return created_pair_strat, executor_web_client


def _place_sanity_complete_buy_sell_pair_chores_with_pair_strat(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 111360
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list, market_depth_basemodel_list))

    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        # Placing buy chores
        buy_ack_chore_id = None
        sell_ack_chore_id = None
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client,
                           create_counts_per_side=2)

            buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, 10, 90, executor_web_client)

            buy_ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                                   buy_symbol, executor_web_client,
                                                                                   loop_wait_secs=1,
                                                                                   last_chore_id=buy_ack_chore_id)
            buy_ack_chore_id = buy_ack_chore_journal.chore.chore_id
            # fills_journal = get_latest_fill_journal_from_chore_id(buy_ack_chore_id, executor_web_client)
            time.sleep(1)
            sell_chore: NewChoreBaseModel = place_new_chore(sell_symbol, Side.SELL, 110, 7, executor_web_client)
            sell_ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                                    sell_symbol, executor_web_client,
                                                                                    loop_wait_secs=1,
                                                                                    last_chore_id=sell_ack_chore_id)
            strat_status: StratStatusBaseModel = executor_web_client.get_strat_status_client(active_pair_strat.id)
            strat_view: StratViewBaseModel = photo_book_web_client.get_strat_view_client(
                active_pair_strat.id)
            sell_ack_chore_id = sell_ack_chore_journal.chore.chore_id
            assert strat_status.balance_notional == strat_view.balance_notional, \
                f"Mismatched {strat_status.balance_notional = }, {strat_view.balance_notional = }"

        return buy_symbol, sell_symbol, active_pair_strat, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_place_sanity_parallel_buy_sell_pair_chores_to_check_strat_view(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, expected_portfolio_limits_, refresh_sec_update_fixture):
    # Updating portfolio limits
    expected_portfolio_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
    expected_portfolio_limits_.max_open_baskets = 51
    expected_portfolio_limits_.max_gross_n_open_notional = 5_000_000
    email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)

    max_loop_count_per_side = 50
    leg1_leg2_symbol_list = []
    total_strats = 20
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_sell_pair_chores_with_pair_strat,
                                   leg1_leg2_symbol_tuple[0], leg1_leg2_symbol_tuple[1], pair_strat_,
                                   copy.deepcopy(expected_strat_limits_), copy.deepcopy(expected_strat_status_),
                                   copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   max_loop_count_per_side, refresh_sec_update_fixture)
                   for idx, leg1_leg2_symbol_tuple in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            future.result()

    px = 10
    qty = 90
    strats_count = len(leg1_leg2_symbol_list)
    strat_view_list = photo_book_web_client.get_all_strat_view_client()
    expected_balance_notional = (expected_strat_limits_.max_single_leg_notional -
                                 strats_count * max_loop_count_per_side * qty * get_px_in_usd(px))
    for strat_view in strat_view_list:
        assert (strat_view.balance_notional == expected_balance_notional,
                (f"Mismatched: overall_buy_notional must be "
                 f"{expected_balance_notional}, found {strat_view.balance_notional}"))

    px = 110
    qty = 7
    strats_count = len(leg1_leg2_symbol_list)
    strat_view_list = photo_book_web_client.get_all_strat_view_client()
    expected_balance_notional = (expected_strat_limits_.max_single_leg_notional -
                                 strats_count * max_loop_count_per_side * qty * get_px_in_usd(px))
    for strat_view in strat_view_list:
        assert (strat_view.balance_notional == expected_balance_notional,
                (f"Mismatched: overall_buy_notional must be "
                 f"{expected_balance_notional}, found {strat_view.balance_notional}"))


# async def _submit_task_for_place_sanity_complete_buy_sell_pair_chores_with_pair_strat(
#         leg1_leg2_symbol_list, pair_strat_list, expected_strat_limits_, expected_strat_status_,
#         symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side,
#         refresh_sec_update_fixture):
#
#     tasks = []
#     for idx, leg1_leg2_symbol in leg1_leg2_symbol_list:
#         task = asyncio.create_task(_place_sanity_complete_buy_sell_pair_chores_with_pair_strat(
#             leg1_leg2_symbol[0], leg1_leg2_symbol[1], pair_strat_list[idx],
#             copy.deepcopy(expected_strat_limits_), copy.deepcopy(expected_strat_status_),
#             copy.deepcopy(symbol_overview_obj_list),
#             copy.deepcopy(last_barter_fixture_list), copy.deepcopy(market_depth_basemodel_list),
#             max_loop_count_per_side, refresh_sec_update_fixture
#         ))
#         tasks.append(task)
#
#     completed_tasks: Set | None = None
#     pending_tasks: Set | None = None
#     while True:
#         try:
#             completed_tasks, pending_tasks = \
#                 await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=60)
#         except Exception as e:
#             print(f"_place_sanity_complete_buy_sell_pair_chores_with_pair_strat "
#                               f"asyncio.wait failed with exception: {e}")
#         while completed_tasks:
#             completed_task = None
#             try:
#                 completed_task = completed_tasks.pop()
#                 completed_task.result()
#             except Exception as e:
#                 pair_strat_id = int(completed_task.get_name())
#                 print(f"_place_sanity_complete_buy_sell_pair_chores_with_pair_strat failed for "
#                                   f"pair_strat_id: {pair_strat_id}, exception: {e}")
#         if pending_tasks:
#             tasks = [*pending_tasks, ]
#         else:
#             break
#
#
# def _place_sanity_complete_buy_sell_pair_chores_with_pair_strat(
#         buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
#         last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side, refresh_sec_update_fixture):
#     expected_strat_limits_.max_open_chores_per_side = 10
#     expected_strat_limits_.residual_restriction.max_residual = 111360
#     expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
#     residual_wait_sec = 4 * refresh_sec_update_fixture
#
#     active_pair_strat, executor_web_client = move_snoozed_pair_strat_to_ready_n_then_active(
#         pair_strat_, market_depth_basemodel_list, symbol_overview_obj_list,
#         expected_strat_limits_, expected_strat_status_)
#
#     run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)
#
#     config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
#     config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
#     config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)
#
#     try:
#         # updating yaml_configs according to this test
#         for symbol in config_dict["symbol_configs"]:
#             config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
#             config_dict["symbol_configs"][symbol]["fill_percent"] = 100
#         YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))
#
#         executor_web_client.barter_simulator_reload_config_query_client()
#
#         total_chore_count_for_each_side = max_loop_count_per_side
#
#         # Placing buy chores
#         buy_ack_chore_id = None
#         sell_ack_chore_id = None
#         for loop_count in range(total_chore_count_for_each_side):
#             run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client,
#                            create_counts_per_side=2)
#
#             buy_chore: NewChoreBaseModel = place_new_chore(buy_symbol, Side.BUY, 10, 90, executor_web_client)
#
#             # ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
#             #                                                                    buy_symbol, executor_web_client,
#             #                                                                    last_chore_id=buy_ack_chore_id)
#             # buy_ack_chore_id = ack_chore_journal.chore.chore_id
#             # fills_journal = get_latest_fill_journal_from_chore_id(buy_ack_chore_id, executor_web_client)
#             time.sleep(1)
#             sell_chore: NewChoreBaseModel = place_new_chore(sell_symbol, Side.SELL, 110, 7, executor_web_client)
#             sell_ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
#                                                                                sell_symbol, executor_web_client,
#                                                                                last_chore_id=sell_ack_chore_id)
#             strat_status: StratStatusBaseModel = executor_web_client.get_strat_status_client(active_pair_strat.id)
#             strat_view: StratViewBaseModel = email_book_service_native_web_client.get_strat_view_client(
#                 active_pair_strat.id)
#             sell_ack_chore_id = sell_ack_chore_journal.chore.chore_id
#             assert strat_status.balance_notional == strat_view.balance_notional, \
#                 f"Mismatched {strat_status.balance_notional = }, {strat_view.balance_notional = }"
#
#         return buy_symbol, sell_symbol, active_pair_strat, executor_web_client
#
#     except AssertionError as e:
#         raise AssertionError(e)
#     except Exception as e:
#         print(f"Some Error Occurred: exception: {e}, "
#               f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
#         raise Exception(e)
#     finally:
#         YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
#
#
# @pytest.mark.nightly
# def test_place_sanity_parallel_buy_sell_pair_chores_to_check_strat_view(
#         static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
#         expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
#         last_barter_fixture_list, market_depth_basemodel_list,
#         buy_chore_, sell_chore_, expected_portfolio_limits_, refresh_sec_update_fixture):
#     # Updating portfolio limits
#     expected_portfolio_limits_.rolling_max_chore_count.max_rolling_tx_count = 51
#     expected_portfolio_limits_.max_open_baskets = 51
#     expected_portfolio_limits_.max_gross_n_open_notional = 5_000_000
#     email_book_service_native_web_client.put_portfolio_limits_client(expected_portfolio_limits_)
#
#     max_loop_count_per_side = 50
#     leg1_leg2_symbol_list = []
#     total_strats = 20
#     pair_strat_list = []
#     for i in range(1, total_strats + 1):
#         leg1_symbol = f"CB_Sec_{i}"
#         leg2_symbol = f"EQT_Sec_{i}"
#         leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))
#
#         stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
#         pair_strat_list.append(stored_pair_strat_basemodel)
#         time.sleep(2)
#
#     asyncio_loop = asyncio.new_event_loop()
#     run_coro = _submit_task_for_place_sanity_complete_buy_sell_pair_chores_with_pair_strat(
#         leg1_leg2_symbol_list, pair_strat_list, expected_strat_limits_, expected_strat_status_,
#         symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list, max_loop_count_per_side,
#         refresh_sec_update_fixture)
#     future = asyncio.run_coroutine_threadsafe(run_coro, asyncio_loop)
#     # block for task to finish
#     try:
#         future.result()
#     except Exception as e:
#         logging.exception(f"test_place_sanity_parallel_buy_sell_pair_chores_to_check_strat_view "
#                           f"failed with exception: {e}")
#     px = 10
#     qty = 90
#     strats_count = len(leg1_leg2_symbol_list)
#     strat_view_list = email_book_service_native_web_client.get_all_strat_view_client()
#     expected_balance_notional = (expected_strat_limits_.max_single_leg_notional -
#                                  strats_count * max_loop_count_per_side * qty * get_px_in_usd(px))
#     for strat_view in strat_view_list:
#         assert (strat_view.balance_notional == expected_balance_notional,
#                 (f"Mismatched: overall_buy_notional must be "
#                  f"{expected_balance_notional}, found {strat_view.balance_notional}"))
#
#     px = 110
#     qty = 7
#     strats_count = len(leg1_leg2_symbol_list)
#     strat_view_list = email_book_service_native_web_client.get_all_strat_view_client()
#     expected_balance_notional = (expected_strat_limits_.max_single_leg_notional -
#                                  strats_count * max_loop_count_per_side * qty * get_px_in_usd(px))
#     for strat_view in strat_view_list:
#         assert (strat_view.balance_notional == expected_balance_notional,
#                 (f"Mismatched: overall_buy_notional must be "
#                  f"{expected_balance_notional}, found {strat_view.balance_notional}"))


# Test for some manual check - not checking anything functionally
# def handle_test_buy_sell_with_sleep_delays(buy_symbol: str, sell_symbol: str, pair_strat_: PairStratBaseModel,
#                                            expected_strat_limits_: StratLimits,
#                                            expected_strat_status_: StratStatus,
#                                            last_barter_fixture_list: List[Dict],
#                                            symbol_overview_obj_list: List[SymbolOverviewBaseModel],
#                                            market_depth_basemodel_list: List[MarketDepthBaseModel]):
#     chore_counts = 10
#     active_strat, executor_web_client = (
#         create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
#                                            expected_strat_status_, symbol_overview_obj_list,
#                                            last_barter_fixture_list, market_depth_basemodel_list))
#
#     for chore_count in range(chore_counts):
#         # Buy Chore
#         run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)
#         print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
#         # Running TopOfBook (this triggers expected buy chore)
#         run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client[0], False)
#
#         # Sell Chore
#         run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_web_client)
#         print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
#         # Running TopOfBook (this triggers expected buy chore)
#         run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client[1], False)
#
#         time.sleep(10)
#
#
# def test_place_sanity_chores_with_sleep_delays(clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
#                                                expected_strat_limits_,
#                                                expected_strat_status_, last_barter_fixture_list,
#                                                symbol_overview_obj_list, market_depth_basemodel_list):
#     symbol_pair_counter = 1
#     with concurrent.futures.ThreadPoolExecutor(max_workers=len(buy_sell_symbol_list)) as executor:
#         results = [executor.submit(handle_test_buy_sell_with_sleep_delays, buy_symbol, sell_symbol,
#                                    pair_strat_, expected_strat_limits_, expected_strat_status_,
#                                    last_barter_fixture_list, symbol_overview_obj_list, market_depth_basemodel_list)
#                    for buy_symbol, sell_symbol in buy_sell_symbol_list]
#
#         for future in concurrent.futures.as_completed(results):
#             if future.exception() is not None:
#                 raise Exception(future.exception())


# def test_create_sanity_last_barter(static_data_, clean_and_set_limits, last_barter_fixture_list):
#     symbols = ["CB_Sec_1", "CB_Sec_2", "CB_Sec_3", "CB_Sec_4"]
#     px_portions = [(40, 55), (56, 70), (71, 85), (86, 100)]
#     total_loops = 600
#     loop_wait = 1   # sec
#
#     for _ in range(total_loops):
#         current_time = DateTime.utcnow()
#         for index, symbol in enumerate(symbols):
#             px_portion = px_portions[index]
#             qty = random.randint(1000, 2000)
#             qty = qty + 400
#
#             last_barter_obj = LastBarterBaseModel(**last_barter_fixture_list[0])
#             last_barter_obj.symbol_n_exch_id.symbol = symbol
#             last_barter_obj.arrival_time = current_time
#             last_barter_obj.px = random.randint(px_portion[0], px_portion[1])
#             last_barter_obj.qty = qty
#
#             mobile_book_web_client.create_last_barter_client(last_barter_obj)
#
#         time.sleep(loop_wait)
#
#
# def test_sanity_underlying_time_series(static_data_, clean_and_set_limits, dash_, dash_filter_, bar_data_):
#     dash_ids: List[str] = []
#     dash_by_id_dict: Dict[int, DashBaseModel] = {}
#     # create all dashes
#     for index in range(1000):
#         dash_obj: DashBaseModel = DashBaseModel(**dash_)
#         dash_obj.rt_dash.leg1.sec.sec_id = f"CB_Sec_{index + 1}"
#         stored_leg1_vwap = dash_obj.rt_dash.leg1.vwap
#         dash_obj.rt_dash.leg1.vwap = stored_leg1_vwap + random.randint(0, 30)
#         dash_obj.rt_dash.leg1.vwap_change = (dash_obj.rt_dash.leg1.vwap - stored_leg1_vwap ) * 100 / stored_leg1_vwap
#         dash_obj.rt_dash.leg2.sec.sec_id = f"EQT_Sec_{index + 1}"
#         stored_leg2_vwap = dash_obj.rt_dash.leg2.vwap
#         dash_obj.rt_dash.leg2.vwap = stored_leg2_vwap + random.randint(0, 10) / 10
#         dash_obj.rt_dash.leg2.vwap_change = (dash_obj.rt_dash.leg2.vwap - stored_leg2_vwap) * 100 / stored_leg2_vwap
#         stored_premium = dash_obj.rt_dash.mkt_premium
#         dash_obj.rt_dash.mkt_premium = stored_premium + random.randint(0, 10) * 0.1
#         dash_obj.rt_dash.mkt_premium_change = (dash_obj.rt_dash.mkt_premium - stored_premium) * 100 / stored_premium
#         stored_dash_obj: DashBaseModel = mobile_book_web_client.create_dash_client(dash_obj)
#         dash_by_id_dict[stored_dash_obj.id] = stored_dash_obj
#         dash_ids.append(str(stored_dash_obj.id))
#
#     # create dash filters and dept_book
#     dash_filters_ids: List[str] = []
#     for index in range(10):
#         dash_filters_obj: DashFiltersBaseModel = DashFiltersBaseModel(**dash_filter_)
#         dash_filters_obj.dash_name = f"Dashboard {index + 1}"
#         stored_dash_filters_obj = mobile_book_web_client.create_dash_filters_client(dash_filters_obj)
#         dash_filters_ids.append(str(stored_dash_filters_obj.id))
#         max_dashes: int = random.randint(100, 3_000)
#         dash_collection_obj = DashCollectionBaseModel(id=stored_dash_filters_obj.id,
#                                                       dash_name=stored_dash_filters_obj.dash_name,
#                                                       loaded_dashes=dash_ids[:max_dashes],
#                                                       buffered_dashes=[])
#         mobile_book_web_client.create_dash_collection_client(dash_collection_obj)
#     dash_filters_collection_obj = DashFiltersCollectionBaseModel(loaded_dash_filters=dash_filters_ids,
#                                                                  buffered_dash_filters=[])
#     mobile_book_web_client.create_dash_filters_collection_client(dash_filters_collection_obj)
#
#     total_loops = 600
#     loop_wait = 10  # sec
#     volume = 1_000
#
#     def gen_bar_data_by_leg(leg: DashLegOptional, start_time: pendulum.DateTime, is_eqt = False) -> BarDataBaseModel:
#         bar_data = BarDataBaseModel(**bar_data_)
#         bar_data.start_time = start_time
#         bar_data.end_time = start_time.add(seconds=1)
#         bar_data.symbol_n_exch_id.symbol = leg.sec.sec_id
#         bar_data.symbol_n_exch_id.exch_id = leg.exch_id
#         random_increment = random.randint(0, 10)
#         if is_eqt:
#             random_increment *= 0.1
#         bar_data.vwap = leg.vwap + random_increment
#         bar_data.vwap_change = (bar_data.vwap - leg.vwap) * 100 / leg.vwap
#         volume_change = random.randint(0, 1_000)
#         bar_data.volume = volume + volume_change
#         if not is_eqt:
#             bar_data.premium = 10 + random.randint(0, 10) * 0.1
#             bar_data.premium_change = (bar_data.premium - 10) * 100 / 10
#         return bar_data
#
#     for _ in range(total_loops):
#         current_time = DateTime.utcnow()
#         pending_bars = []
#         pending_dashes = []
#         for index, dash in enumerate(dash_by_id_dict.values()):
#             if index > 100:
#                 break
#             # create bars for leg1 and leg2
#             leg1_bar_data = gen_bar_data_by_leg(dash.rt_dash.leg1, current_time)
#             pending_bars.append(leg1_bar_data)
#             leg2_bar_data = gen_bar_data_by_leg(dash.rt_dash.leg2, current_time, True)
#             pending_bars.append(leg2_bar_data)
#
#             # dash updates
#             leg1 = DashLegOptional(vwap=leg1_bar_data.vwap, vwap_change=leg1_bar_data.vwap_change)
#             leg2 = DashLegOptional(vwap=leg2_bar_data.vwap, vwap_change=leg2_bar_data.vwap_change)
#             rt_dash = RTDashOptional(leg1=leg1, leg2=leg2, mkt_premium=leg1_bar_data.premium,
#                                      mkt_premium_change=leg1_bar_data.premium_change)
#             updated_dash = DashBaseModel(_id=dash.id, rt_dash=rt_dash)
#             pending_dashes.append(jsonable_encoder(updated_dash, by_alias=True, exclude_none=True))
#
#         mobile_book_web_client.create_all_bar_data_client(pending_bars)
#         mobile_book_web_client.patch_all_dash_client(pending_dashes)
#         time.sleep(loop_wait)


@pytest.mark.nightly
def test_add_brokers_to_portfolio_limits(clean_and_set_limits):
    """Adding Broker entries in portfolio limits"""
    broker = broker_fixture()

    portfolio_limits_basemodel = PortfolioLimitsBaseModel(_id=1, eligible_brokers=[broker])
    email_book_service_native_web_client.patch_portfolio_limits_client(
        jsonable_encoder(portfolio_limits_basemodel, by_alias=True, exclude_none=True))

    stored_portfolio_limits_ = email_book_service_native_web_client.get_portfolio_limits_client(1)
    for stored_broker in stored_portfolio_limits_.eligible_brokers:
        stored_broker.id = None
    broker.id = None
    assert broker in stored_portfolio_limits_.eligible_brokers, f"Couldn't find broker {broker} in " \
                                                                f"eligible_broker " \
                                                                f"{stored_portfolio_limits_.eligible_brokers}"


@pytest.mark.nightly
def test_buy_sell_chore_multi_pair_serialized(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                                              buy_chore_, sell_chore_, buy_fill_journal_,
                                              sell_fill_journal_, expected_buy_chore_snapshot_,
                                              expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
                                              pair_strat_, expected_strat_limits_, expected_strat_status_,
                                              expected_strat_brief_, expected_portfolio_status_,
                                              last_barter_fixture_list, symbol_overview_obj_list,
                                              market_depth_basemodel_list, expected_chore_limits_,
                                              expected_portfolio_limits_, max_loop_count_per_side,
                                              leg1_leg2_symbol_list, refresh_sec_update_fixture):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:int(len(leg1_leg2_symbol_list) / 2)]
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)

        strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = (
            handle_test_buy_sell_chore(leg1_symbol, leg2_symbol, max_loop_count_per_side,
                                       refresh_sec_update_fixture, buy_chore_, sell_chore_, buy_fill_journal_,
                                       sell_fill_journal_, expected_buy_chore_snapshot_, expected_sell_chore_snapshot_,
                                       expected_symbol_side_snapshot_, stored_pair_strat_basemodel,
                                       expected_strat_limits_, expected_strat_status_, expected_strat_brief_,
                                       last_barter_fixture_list, symbol_overview_obj_list,
                                       market_depth_basemodel_list))
        overall_buy_notional += strat_buy_notional
        overall_sell_notional += strat_sell_notional
        overall_buy_fill_notional += strat_buy_fill_notional
        overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_buy_sell_chore_multi_pair_parallel(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                                            buy_chore_, sell_chore_, buy_fill_journal_,
                                            sell_fill_journal_, expected_buy_chore_snapshot_,
                                            expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
                                            pair_strat_, expected_strat_limits_, expected_strat_status_,
                                            expected_strat_brief_, expected_portfolio_status_,
                                            last_barter_fixture_list, symbol_overview_obj_list,
                                            market_depth_basemodel_list, expected_chore_limits_,
                                            expected_portfolio_limits_, max_loop_count_per_side,
                                            leg1_leg2_symbol_list, refresh_sec_update_fixture):
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0

    leg1_leg2_symbol_list = []
    total_strats = 10
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_buy_sell_chore, leg1_leg2_symbol[0], leg1_leg2_symbol[1],
                                   max_loop_count_per_side, refresh_sec_update_fixture, copy.deepcopy(buy_chore_),
                                   copy.deepcopy(sell_chore_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_chore_snapshot_),
                                   copy.deepcopy(expected_sell_chore_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), pair_strat_list[idx],
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), False)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            else:
                strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = future.result()
                overall_buy_notional += strat_buy_notional
                overall_sell_notional += strat_sell_notional
                overall_buy_fill_notional += strat_buy_fill_notional
                overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_sell_buy_chore_multi_pair_parallel(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                                            buy_chore_, sell_chore_, buy_fill_journal_,
                                            sell_fill_journal_, expected_buy_chore_snapshot_,
                                            expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
                                            pair_strat_, expected_strat_limits_, expected_strat_status_,
                                            expected_strat_brief_, expected_portfolio_status_,
                                            last_barter_fixture_list, symbol_overview_obj_list,
                                            market_depth_basemodel_list, expected_chore_limits_,
                                            expected_portfolio_limits_, max_loop_count_per_side,
                                            leg1_leg2_symbol_list, refresh_sec_update_fixture):
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0

    leg1_leg2_symbol_list = []
    total_strats = 10
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_,
                                                   leg1_side=Side.SELL, leg2_side=Side.BUY)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_sell_buy_chore, leg1_leg2_symbol[0], leg1_leg2_symbol[1],
                                   max_loop_count_per_side, refresh_sec_update_fixture, copy.deepcopy(buy_chore_),
                                   copy.deepcopy(sell_chore_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_chore_snapshot_),
                                   copy.deepcopy(expected_sell_chore_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), pair_strat_list[idx],
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(expected_portfolio_status_),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), False)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            else:
                strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = future.result()
                overall_buy_notional += strat_buy_notional
                overall_sell_notional += strat_sell_notional
                overall_buy_fill_notional += strat_buy_fill_notional
                overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_buy_sell_non_systematic_chore_multi_pair_serialized(static_data_, clean_and_set_limits,
                                                             pair_securities_with_sides_,
                                                             buy_chore_, sell_chore_, buy_fill_journal_,
                                                             sell_fill_journal_, expected_buy_chore_snapshot_,
                                                             expected_sell_chore_snapshot_,
                                                             expected_symbol_side_snapshot_,
                                                             pair_strat_, expected_strat_limits_,
                                                             expected_strat_status_,
                                                             expected_strat_brief_, expected_portfolio_status_,
                                                             last_barter_fixture_list, symbol_overview_obj_list,
                                                             market_depth_basemodel_list, expected_chore_limits_,
                                                             expected_portfolio_limits_, max_loop_count_per_side,
                                                             leg1_leg2_symbol_list, refresh_sec_update_fixture):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:int(len(leg1_leg2_symbol_list) / 2)]
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)

        strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = (
            handle_test_buy_sell_chore(leg1_symbol, leg2_symbol, max_loop_count_per_side,
                                       refresh_sec_update_fixture, buy_chore_, sell_chore_, buy_fill_journal_,
                                       sell_fill_journal_, expected_buy_chore_snapshot_, expected_sell_chore_snapshot_,
                                       expected_symbol_side_snapshot_, stored_pair_strat_basemodel,
                                       expected_strat_limits_, expected_strat_status_, expected_strat_brief_,
                                       last_barter_fixture_list, symbol_overview_obj_list,
                                       market_depth_basemodel_list, is_non_systematic_run=True))
        overall_buy_notional += strat_buy_notional
        overall_sell_notional += strat_sell_notional
        overall_buy_fill_notional += strat_buy_fill_notional
        overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_buy_sell_non_systematic_chore_multi_pair_parallel(static_data_, clean_and_set_limits,
                                                           pair_securities_with_sides_,
                                                           buy_chore_, sell_chore_, buy_fill_journal_,
                                                           sell_fill_journal_, expected_buy_chore_snapshot_,
                                                           expected_sell_chore_snapshot_,
                                                           expected_symbol_side_snapshot_,
                                                           pair_strat_, expected_strat_limits_, expected_strat_status_,
                                                           expected_strat_brief_, expected_portfolio_status_,
                                                           last_barter_fixture_list, symbol_overview_obj_list,
                                                           market_depth_basemodel_list, expected_chore_limits_,
                                                           expected_portfolio_limits_, max_loop_count_per_side,
                                                           leg1_leg2_symbol_list, refresh_sec_update_fixture):
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0

    leg1_leg2_symbol_list = []
    total_strats = 10
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_buy_sell_chore, buy_sell_symbol[0], buy_sell_symbol[1],
                                   max_loop_count_per_side, refresh_sec_update_fixture, copy.deepcopy(buy_chore_),
                                   copy.deepcopy(sell_chore_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_chore_snapshot_),
                                   copy.deepcopy(expected_sell_chore_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), pair_strat_list[idx],
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), True)
                   for idx, buy_sell_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            else:
                strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = future.result()
                overall_buy_notional += strat_buy_notional
                overall_sell_notional += strat_sell_notional
                overall_buy_fill_notional += strat_buy_fill_notional
                overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_buy_sell_pair_chore(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    triggers buy & sell pair chore (single buy chore followed by single sell chore) for max_loop_count_per_side times
    """
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0

    leg1_leg2_symbol_list = []
    total_strats = 10
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_buy_sell_pair_chore, leg1_leg2_symbol[0], leg1_leg2_symbol[1],
                                   max_loop_count_per_side, refresh_sec_update_fixture, copy.deepcopy(buy_chore_),
                                   copy.deepcopy(sell_chore_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_chore_snapshot_),
                                   copy.deepcopy(expected_sell_chore_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), pair_strat_list[idx],
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), False)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            else:
                strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = future.result()
                overall_buy_notional += strat_buy_notional
                overall_sell_notional += strat_sell_notional
                overall_buy_fill_notional += strat_buy_fill_notional
                overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_sell_buy_pair_chore(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    triggers sell & buy pair chore (single sell chore followed by single buy chore) for max_loop_count_per_side times
    """
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0

    leg1_leg2_symbol_list = []
    total_strats = 10
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_,
                                                   leg1_side=Side.SELL, leg2_side=Side.BUY)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_sell_buy_pair_chore, leg1_leg2_symbol[0], leg1_leg2_symbol[1],
                                   max_loop_count_per_side, refresh_sec_update_fixture, copy.deepcopy(buy_chore_),
                                   copy.deepcopy(sell_chore_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_chore_snapshot_),
                                   copy.deepcopy(expected_sell_chore_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), pair_strat_list[idx],
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(last_barter_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), False)
                   for idx, leg1_leg2_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            else:
                strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = future.result()
                overall_buy_notional += strat_buy_notional
                overall_sell_notional += strat_sell_notional
                overall_buy_fill_notional += strat_buy_fill_notional
                overall_sell_fill_notional += strat_sell_fill_notional

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_trigger_kill_switch_systematic(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                        expected_strat_limits_, expected_strat_status_,
                                        symbol_overview_obj_list, last_barter_fixture_list,
                                        market_depth_basemodel_list, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list,
                                           market_depth_basemodel_list))

    bid_buy_top_market_depth = None
    ask_sell_top_market_depth = None
    stored_market_depth = executor_web_client.get_all_market_depth_client()
    for market_depth in stored_market_depth:
        if market_depth.symbol == leg1_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
            bid_buy_top_market_depth = market_depth
        if market_depth.symbol == leg2_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
            ask_sell_top_market_depth = market_depth

    # positive test
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(executor_web_client, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)

    # internally checks chore_journal existence
    chore_journal: ChoreJournal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                 leg1_symbol, executor_web_client)

    # negative test
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"

    # validating if bartering_link.trigger_kill_switch got called
    check_str = "Called BarteringLink.trigger_kill_switch"
    alert_fail_msg = f"Can't find portfolio alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, alert_fail_msg)

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(executor_web_client, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)
    # internally checking buy chore
    chore_journal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg1_symbol, executor_web_client,
                                                       last_chore_id=chore_journal.chore.chore_id,
                                                       expect_no_chore=True)

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    # required to make buy side tob latest
    run_last_barter(leg1_symbol, leg2_symbol, [last_barter_fixture_list[0]], executor_web_client)

    update_tob_through_market_depth_to_place_sell_chore(executor_web_client, ask_sell_top_market_depth,
                                                        bid_buy_top_market_depth)
    # internally checking sell chore
    chore_journal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client, expect_no_chore=True)


@pytest.mark.nightly
def test_trigger_kill_switch_non_systematic(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                            pair_strat_, expected_strat_limits_,
                                            expected_strat_status_, symbol_overview_obj_list,
                                            last_barter_fixture_list, market_depth_basemodel_list,
                                            buy_chore_, sell_chore_,
                                            refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list,
                                           market_depth_basemodel_list))
    # positive test
    # placing buy chore
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    place_new_chore(leg1_symbol, Side.BUY, buy_chore_.chore.px, buy_chore_.chore.qty, executor_web_client)
    time.sleep(2)
    # internally checking buy chore
    chore_journal: ChoreJournal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg1_symbol, executor_web_client)

    # negative test
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"

    # validating if bartering_link.trigger_kill_switch got called
    check_str = "Called BarteringLink.trigger_kill_switch"
    alert_fail_msg = f"Can't find portfolio alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, alert_fail_msg)

    # placing buy chore
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    place_new_chore(leg1_symbol, Side.BUY, buy_chore_.chore.px, buy_chore_.chore.qty, executor_web_client)
    time.sleep(2)
    # internally checking buy chore
    chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                   leg1_symbol, executor_web_client,
                                                                   last_chore_id=chore_journal.chore.chore_id,
                                                                   expect_no_chore=True)

    # placing sell chore
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    place_new_chore(leg2_symbol, Side.SELL, sell_chore_.chore.px, sell_chore_.chore.qty, executor_web_client)
    time.sleep(2)
    # internally checking sell chore
    chore_journal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client, expect_no_chore=True)


@pytest.mark.nightly
def test_revoke_kill_switch(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                            expected_strat_limits_, expected_strat_status_,
                            symbol_overview_obj_list, last_barter_fixture_list,
                            market_depth_basemodel_list, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list,
                                           market_depth_basemodel_list))

    # positive test
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"

    bid_buy_top_market_depth = None
    ask_sell_top_market_depth = None
    stored_market_depth = executor_web_client.get_all_market_depth_client()
    for market_depth in stored_market_depth:
        if market_depth.symbol == leg1_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
            bid_buy_top_market_depth = market_depth
        if market_depth.symbol == leg2_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
            ask_sell_top_market_depth = market_depth
    time.sleep(2)
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(executor_web_client, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)
    # internally checking buy chore
    chore_journal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg1_symbol, executor_web_client, expect_no_chore=True)

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    # required to make buy side tob latest
    run_last_barter(leg1_symbol, leg2_symbol, [last_barter_fixture_list[0]], executor_web_client)

    update_tob_through_market_depth_to_place_sell_chore(executor_web_client, ask_sell_top_market_depth,
                                                        bid_buy_top_market_depth)
    # internally checking sell chore
    chore_journal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client, expect_no_chore=True)

    # negative test
    system_control = SystemControlBaseModel(_id=1, kill_switch=False)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert not updated_system_control.kill_switch, "Unexpected: kill_switch is True, expected to be False"

    # validating if bartering_link.trigger_kill_switch got called
    check_str = "Called BarteringLink.revoke_kill_switch_n_resume_bartering"
    alert_fail_msg = f"Can't find portfolio alert saying '{check_str}'"
    time.sleep(5)
    check_alert_str_in_portfolio_alert(check_str, alert_fail_msg)

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(executor_web_client, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)

    # internally checks chore_journal existence
    chore_journal: ChoreJournal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                                 leg1_symbol, executor_web_client)
    time.sleep(residual_wait_sec)

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    # required to make buy side tob latest
    run_last_barter(leg1_symbol, leg2_symbol, [last_barter_fixture_list[0]], executor_web_client)

    update_tob_through_market_depth_to_place_sell_chore(executor_web_client, ask_sell_top_market_depth,
                                                        bid_buy_top_market_depth)
    # internally checking sell chore
    chore_journal = \
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client)


@pytest.mark.nightly
def test_trigger_switch_fail(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list):

    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        config_dict["trigger_kill_switch"] = False
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()

        try:
            system_control = SystemControlBaseModel(_id=1, kill_switch=True)
            email_book_service_native_web_client.patch_system_control_client(
                jsonable_encoder(system_control, by_alias=True, exclude_none=True))
        except Exception as e:
            if "bartering_link.trigger_kill_switch failed" not in str(e):
                raise Exception("Something went wrong while enabling kill_switch kill switch")
        else:
            assert False, ("Configured simulate config to return False from trigger_kill_switch to fail enable "
                           "kill switch, but patch went successful - check why simulate didn't work")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()


@pytest.mark.nightly
def test_revoke_switch_fail(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list):
    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"
    try:
        # updating yaml_configs according to this test
        config_dict["revoke_kill_switch_n_resume_bartering"] = False
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()

        try:
            system_control = SystemControlBaseModel(_id=1, kill_switch=False)
            email_book_service_native_web_client.patch_system_control_client(
                jsonable_encoder(system_control, by_alias=True, exclude_none=True))
        except Exception as e:
            if "bartering_link.revoke_kill_switch_n_resume_bartering failed" not in str(e):
                raise Exception("Something went wrong while disabling kill_switch kill switch")
        else:
            assert False, ("Configured simulate config to return False from revoke_kill_switch_n_resume_bartering to "
                           "fail disable kill switch, but patch went successful - check why simulate didn't work")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()


@pytest.mark.nightly
def test_simulated_partial_fills(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                 pair_strat_, expected_strat_limits_,
                                 expected_strat_status_, symbol_overview_obj_list,
                                 last_barter_fixture_list, market_depth_basemodel_list,
                                 buy_chore_, sell_chore_,
                                 max_loop_count_per_side, refresh_sec_update_fixture):
    partial_filled_qty: int | None = None
    unfilled_amount: int | None = None
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # updating fixture values for this test-case
    max_loop_count_per_side = 2
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            # buy fills check
            for check_symbol in [leg1_symbol, leg2_symbol]:
                chore_id = None
                total_partial_filled_qty = 0
                for loop_count in range(1, max_loop_count_per_side + 1):
                    chore_id, partial_filled_qty = \
                        underlying_handle_simulated_partial_fills_test(loop_count, check_symbol, leg1_symbol,
                                                                       leg2_symbol,
                                                                       last_barter_fixture_list,
                                                                       chore_id, config_dict, executor_http_client)
                    total_partial_filled_qty += partial_filled_qty
                    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                        # Sleeping to let the chore get cxlled
                        time.sleep(residual_wait_sec)
                time.sleep(5)
                strat_status: StratStatusBaseModel = executor_http_client.get_strat_status_client(created_pair_strat.id)
                if check_symbol == leg1_symbol:
                    assert total_partial_filled_qty == strat_status.total_fill_buy_qty, (
                        f"Unmatched total_fill_buy_qty: expected {total_partial_filled_qty} "
                        f"received {strat_status.total_fill_buy_qty}")
                else:
                    assert total_partial_filled_qty == strat_status.total_fill_sell_qty, (
                           f"Unmatched total_fill_sell_qty: expected {total_partial_filled_qty} "
                           f"received {strat_status.total_fill_sell_qty}")
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simulated_multi_partial_fills(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                       pair_strat_, expected_strat_limits_,
                                       expected_strat_status_, symbol_overview_obj_list,
                                       last_barter_fixture_list, market_depth_basemodel_list,
                                       buy_chore_, sell_chore_,
                                       max_loop_count_per_side, refresh_sec_update_fixture):

    partial_filled_qty: int | None = None
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # updating fixture values for this test-case
    max_loop_count_per_side = 2
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 10
                config_dict["symbol_configs"][symbol]["total_fill_count"] = 5
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            # buy fills check
            for check_symbol in [leg1_symbol, leg2_symbol]:
                chore_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    chore_id, partial_filled_qty = \
                        underlying_handle_simulated_multi_partial_fills_test(loop_count, check_symbol, leg1_symbol,
                                                                             leg2_symbol, last_barter_fixture_list,
                                                                             chore_id,
                                                                             executor_http_client, config_dict)
                    if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                        # Sleeping to let the chore get cxlled
                        time.sleep(residual_wait_sec)

                symbol_configs = get_symbol_configs(check_symbol, config_dict)
                strat_status: StratStatusBaseModel = executor_http_client.get_strat_status_client(created_pair_strat.id)

                total_fill_qty = strat_status.total_fill_buy_qty \
                    if check_symbol == leg1_symbol else strat_status.total_fill_sell_qty
                expected_total_fill_qty = \
                    partial_filled_qty * max_loop_count_per_side * symbol_configs.get("total_fill_count")
                assert expected_total_fill_qty == total_fill_qty, "total_fill_qty mismatched: expected " \
                                                                  f"{expected_total_fill_qty} received " \
                                                                  f"{total_fill_qty}"
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_filled_status(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                       pair_strat_, expected_strat_limits_,
                       expected_strat_status_, symbol_overview_obj_list,
                       last_barter_fixture_list, market_depth_basemodel_list,
                       buy_chore_, sell_chore_, refresh_sec_update_fixture):
        buy_symbol = leg1_leg2_symbol_list[0][0]
        sell_symbol = leg1_leg2_symbol_list[0][1]
        expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            bid_buy_top_market_depth = None
            ask_sell_top_market_depth = None
            stored_market_depth = executor_http_client.get_all_market_depth_client()
            for market_depth in stored_market_depth:
                if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                    bid_buy_top_market_depth = market_depth
                if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                    ask_sell_top_market_depth = market_depth

            # buy fills check
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

            px = 100
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)
            time.sleep(2)  # delay for chore to get placed

            ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol,
                                                                               executor_http_client)
            latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                        executor_http_client)
            last_fill_date_time = latest_fill_journal.fill_date_time
            filled_qty = get_partial_allowed_fill_qty(buy_symbol, config_dict, ack_chore_journal.chore.qty)
            assert latest_fill_journal.fill_qty == filled_qty, f"filled_qty mismatched: expected filled_qty {filled_qty} " \
                                                               f"received {latest_fill_journal.fill_qty}"
            chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_ACKED, "ChoreStatus mismatched: expected status " \
                                                                            f"ChoreStatusType.OE_ACKED received " \
                                                                            f"{chore_snapshot.chore_status}"

            # processing remaining 50% fills
            executor_http_client.barter_simulator_process_fill_query_client(
                ack_chore_journal.chore.chore_id, ack_chore_journal.chore.px,
                ack_chore_journal.chore.qty, ack_chore_journal.chore.side,
                ack_chore_journal.chore.security.sec_id, ack_chore_journal.chore.underlying_account)
            latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                        executor_http_client)
            assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                              f"expected {latest_fill_journal} " \
                                                                              f"received " \
                                                                              f"{latest_fill_journal.fill_date_time}"
            assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                               f"received {latest_fill_journal.fill_qty}"

            chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, "ChoreStatus mismatched: expected status " \
                                                                             f"ChoreStatusType.OE_FILLED received " \
                                                                             f"{chore_snapshot.chore_status}"
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _check_over_fill_computes(sell_symbol, created_pair_strat, executor_http_client, chore_journal,
                              latest_fill_journal, chore_snapshot_before_over_fill, expected_strat_limits_):
    # Checking if strat went to pause
    pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
    assert pair_strat.strat_state == StratState.StratState_PAUSED, \
        f"Expected Strat to be Paused, found state: {pair_strat.strat_state}, pair_strat: {pair_strat}"

    chore_snapshot = get_chore_snapshot_from_chore_id(chore_journal.chore.chore_id, executor_http_client)
    assert chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED, \
        f"ChoreStatus mismatched: expected status {ChoreStatusType.OE_OVER_FILLED} received " \
        f"{chore_snapshot.chore_status}"
    assert chore_snapshot.filled_qty == chore_snapshot_before_over_fill.filled_qty + latest_fill_journal.fill_qty, \
        ("chore_snapshot filled_qty mismatch: expected chore_snapshot filled_qty: "
         f"{chore_snapshot_before_over_fill.filled_qty + latest_fill_journal.fill_qty} "
         f"but found {chore_snapshot.filled_qty = }")
    assert chore_snapshot.fill_notional == chore_snapshot.filled_qty * get_px_in_usd(latest_fill_journal.fill_px), \
        ("chore_snapshot filled_qty mismatch: expected chore_snapshot fill_notional: "
         f"{chore_snapshot.filled_qty * get_px_in_usd(latest_fill_journal.fill_px)} "
         f"but found {chore_snapshot.fill_notional = }")

    symbol_side_snapshot_list = (
        executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
            chore_snapshot.chore_brief.security.sec_id, chore_snapshot.chore_brief.side))
    assert len(symbol_side_snapshot_list) == 1, \
        (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
         f"{chore_snapshot.chore_brief.security.sec_id, chore_snapshot.chore_brief.side}")

    symbol_side_snapshot = symbol_side_snapshot_list[0]
    assert symbol_side_snapshot.total_filled_qty == chore_snapshot.filled_qty, \
        (f"Mismatched: expected symbol_side_snapshot total_filled_qty: {chore_snapshot.filled_qty}, "
         f"found: {symbol_side_snapshot.total_filled_qty = }")

    strat_brief = executor_http_client.get_strat_brief_client(created_pair_strat.id)
    assert strat_brief.pair_buy_side_bartering_brief.open_qty == 0, \
        (f"Mismatched: expected buy_side_bartering_brief open_qty: 0, "
         f"found: {strat_brief.pair_buy_side_bartering_brief.open_qty = }")
    assert strat_brief.pair_buy_side_bartering_brief.open_notional == 0, \
        ("Mismatched: expected strat_brief.pair_buy_side_bartering_brief.open_notional: 0, "
         f"found: {strat_brief.pair_buy_side_bartering_brief.open_notional = }")
    consumable_notional = (expected_strat_limits_.max_single_leg_notional -
                           symbol_side_snapshot.total_fill_notional)
    assert strat_brief.pair_buy_side_bartering_brief.consumable_notional == consumable_notional, \
        (f"Mismatched: expected strat_brief.pair_buy_side_bartering_brief.consumable_notional: {consumable_notional}, "
         f"found: {strat_brief.pair_buy_side_bartering_brief.consumable_notional = }")
    total_security_size: int = \
        static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
    consumable_concentration = ((total_security_size / 100 * expected_strat_limits_.max_concentration) -
                                symbol_side_snapshot.total_filled_qty)
    assert strat_brief.pair_buy_side_bartering_brief.consumable_concentration == consumable_concentration, \
        (f"Mismatched: expected strat_brief.pair_buy_side_bartering_brief.consumable_concentration: "
         f"{consumable_concentration}, found: {strat_brief.pair_buy_side_bartering_brief.consumable_concentration = }")
    consumable_cxl_qty = \
        (((symbol_side_snapshot.total_filled_qty + symbol_side_snapshot.total_cxled_qty) / 100) *
         expected_strat_limits_.cancel_rate.max_cancel_rate) - symbol_side_snapshot.total_cxled_qty
    assert strat_brief.pair_buy_side_bartering_brief.consumable_cxl_qty == consumable_cxl_qty, \
        (f"Mismatched: expected strat_brief.pair_buy_side_bartering_brief.consumable_cxl_qty: "
         f"{consumable_cxl_qty}, found: {strat_brief.pair_buy_side_bartering_brief.consumable_cxl_qty = }")
    sell_symbol_side_snapshot_list = (
        executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(sell_symbol, Side.SELL))
    sell_symbol_side_snapshot = sell_symbol_side_snapshot_list[0]
    consumable_nett_filled_notional = (expected_strat_limits_.max_net_filled_notional -
                                       abs(symbol_side_snapshot.total_fill_notional -
                                           sell_symbol_side_snapshot.total_fill_notional))
    assert (strat_brief.consumable_nett_filled_notional ==
            consumable_nett_filled_notional), \
        (f"Mismatched: expected strat_brief.consumable_nett_filled_notional: "
         f"{consumable_nett_filled_notional}, found: "
         f"{strat_brief.consumable_nett_filled_notional = }")

    strat_status = executor_http_client.get_strat_status_client(created_pair_strat.id)
    assert strat_status.total_open_buy_qty == 0, \
        (f"Mismatched: expected strat_status.total_open_buy_qty: 0, "
         f"found: {strat_status.total_open_buy_qty = }")
    assert strat_status.total_open_buy_notional == 0, \
        (f"Mismatched: expected strat_status.total_open_buy_notional: 0, "
         f"found: {strat_status.total_open_buy_notional = }")
    assert strat_status.total_fill_buy_qty == chore_snapshot.filled_qty, \
        (f"Mismatched: expected strat_status.total_fill_buy_qty: {chore_snapshot.filled_qty}, "
         f"found: {strat_status.total_fill_buy_qty = }")
    assert (strat_status.total_fill_buy_notional ==
            chore_snapshot.filled_qty * get_px_in_usd(chore_snapshot.last_update_fill_px)), \
        (f"Mismatched: expected strat_status.total_fill_buy_notional: {chore_snapshot.filled_qty}, "
         f"found: {strat_status.total_fill_buy_notional = }")

    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert (portfolio_status.overall_buy_notional ==
            (chore_snapshot_before_over_fill.last_update_fill_qty *
             get_px_in_usd(chore_snapshot_before_over_fill.last_update_fill_px) +
             chore_snapshot.last_update_fill_qty * get_px_in_usd(chore_snapshot.last_update_fill_px)))


@pytest.mark.nightly
def test_over_fill(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                   expected_strat_status_, symbol_overview_obj_list,
                   last_barter_fixture_list, market_depth_basemodel_list,
                   buy_chore_, sell_chore_, refresh_sec_update_fixture):
    """
    Test case when chore_snapshot is in OE_ACKED and fill is triggered to make it over_filled
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    created_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 60
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_http_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        # buy fills check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        time.sleep(2)  # delay for chore to get placed

        ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol,
                                                                           executor_http_client)
        latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                    executor_http_client)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = get_partial_allowed_fill_qty(buy_symbol, config_dict, ack_chore_journal.chore.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        chore_snapshot_before_over_fill = (
            get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, executor_http_client))
        assert chore_snapshot_before_over_fill.chore_status == ChoreStatusType.OE_ACKED, \
            "ChoreStatus mismatched: expected status ChoreStatusType.OE_ACKED received " \
            f"{chore_snapshot_before_over_fill.chore_status}"

        # processing fill for over_fill
        executor_http_client.barter_simulator_process_fill_query_client(
            ack_chore_journal.chore.chore_id, ack_chore_journal.chore.px,
            ack_chore_journal.chore.qty, ack_chore_journal.chore.side,
            ack_chore_journal.chore.security.sec_id, ack_chore_journal.chore.underlying_account)
        latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                    executor_http_client)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                          f"expected {latest_fill_journal} " \
                                                                          f"received " \
                                                                          f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"

        _check_over_fill_computes(sell_symbol, created_pair_strat, executor_http_client, ack_chore_journal,
                                  latest_fill_journal, chore_snapshot_before_over_fill, expected_strat_limits_)

        time.sleep(5)
        check_str = "Unexpected: Received fill that will make chore_snapshot OVER_FILLED"
        assert_fail_msg = f"Couldn't find any alert saying: {check_str}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(created_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_over_fill_after_fulfill(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, refresh_sec_update_fixture):
    """
    Test case when chore_snapshot is in OE_FILLED and fill is triggered to make it over_filled - fill after FILLED
    must be ignored and strat must be PAUSED with alert
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    created_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_http_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        # buy fills check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        time.sleep(5)  # delay for chore to get placed

        ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol,
                                                                           executor_http_client)
        latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                    executor_http_client)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = get_partial_allowed_fill_qty(buy_symbol, config_dict, ack_chore_journal.chore.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        chore_snapshot_before_over_fill = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                           executor_http_client)
        assert chore_snapshot_before_over_fill.filled_qty == chore_snapshot_before_over_fill.chore_brief.qty, \
            ("chore_snapshot filled_qty mismatch: expected complete fill, i.e., "
             f"{chore_snapshot_before_over_fill.chore_brief.qty} received {chore_snapshot_before_over_fill.filled_qty}")
        assert chore_snapshot_before_over_fill.chore_status == ChoreStatusType.OE_FILLED, \
            (f"ChoreStatus mismatched: expected status ChoreStatusType.OE_FILLED received "
             f"{chore_snapshot_before_over_fill.chore_status = }")

        # processing fill for over_fill
        executor_http_client.barter_simulator_process_fill_query_client(
            ack_chore_journal.chore.chore_id, ack_chore_journal.chore.px,
            ack_chore_journal.chore.qty, ack_chore_journal.chore.side,
            ack_chore_journal.chore.security.sec_id, ack_chore_journal.chore.underlying_account)
        time.sleep(2)
        latest_fill_journal = get_latest_fill_journal_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                    executor_http_client)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, \
            "last_fill_date_time mismatched: expected {latest_fill_journal} received " \
            f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"

        chore_snapshot_after_over_fill = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id,
                                                                          executor_http_client)
        assert chore_snapshot_after_over_fill.chore_status == ChoreStatusType.OE_FILLED, \
            (f"ChoreStatus mismatched: expected status ChoreStatusType.OE_FILLED received "
             f"{chore_snapshot_after_over_fill.chore_status = }")

        # Checking if strat went to pause
        pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Expected Strat to be Paused, found state: {pair_strat.strat_state}, pair_strat: {pair_strat}"

        time.sleep(5)
        check_str = "Unsupported - Fill received for completely filled chore_snapshot"
        assert_fail_msg = f"Couldn't find any alert saying: {check_str}"
        check_alert_str_in_strat_alerts_n_portfolio_alerts(created_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_ack_to_rej_chores(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                           expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                           last_barter_fixture_list, market_depth_basemodel_list,
                           max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_chores to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_chores = 10
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_ack_to_reject_chores"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            handle_rej_chore_test(leg1_symbol, leg2_symbol, expected_strat_limits_,
                                  last_barter_fixture_list, max_loop_count_per_side,
                                  True, executor_http_client, config_dict, residual_wait_sec)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                       f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_unack_to_rej_chores(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                             expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                             last_barter_fixture_list, market_depth_basemodel_list,
                             max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_chores to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_chores = 10
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_new_to_reject_chores"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            handle_rej_chore_test(leg1_symbol, leg2_symbol, expected_strat_limits_,
                                  last_barter_fixture_list, max_loop_count_per_side,
                                  False, executor_http_client, config_dict, residual_wait_sec)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_cxl_rej_n_revert_to_acked(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                   pair_strat_, expected_strat_limits_,
                                   expected_strat_status_, symbol_overview_obj_list,
                                   last_barter_fixture_list, market_depth_basemodel_list,
                                   buy_chore_, sell_chore_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_ack_to_cxl_rej_chores"] = True
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            bid_buy_top_market_depth = None
            ask_sell_top_market_depth = None
            stored_market_depth = executor_http_client.get_all_market_depth_client()
            for market_depth in stored_market_depth:
                if market_depth.symbol == leg1_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                    bid_buy_top_market_depth = market_depth
                if market_depth.symbol == leg2_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                    ask_sell_top_market_depth = market_depth

            for check_symbol in [leg1_symbol, leg2_symbol]:
                continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(check_symbol,
                                                                                                    config_dict)
                chore_count = 0
                special_chore_count = 0
                last_cxl_chore_id = None
                last_cxl_rej_chore_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_http_client)
                    if check_symbol == leg1_symbol:
                        time.sleep(1)
                        update_tob_through_market_depth_to_place_buy_chore(executor_http_client,
                                                                           bid_buy_top_market_depth,
                                                                           ask_sell_top_market_depth)
                    else:
                        # required to make buy side tob latest
                        run_last_barter(leg1_symbol, leg2_symbol, [last_barter_fixture_list[0]], executor_http_client)

                        update_tob_through_market_depth_to_place_sell_chore(executor_http_client,
                                                                            ask_sell_top_market_depth,
                                                                            bid_buy_top_market_depth)
                    time.sleep(10)  # delay for chore to get placed and trigger cxl

                    if chore_count < continues_chore_count:
                        check_chore_event = ChoreEventType.OE_CXL_ACK
                        chore_count += 1
                    else:
                        if special_chore_count < continues_special_chore_count:
                            check_chore_event = "REJ"
                            special_chore_count += 1
                        else:
                            check_chore_event = ChoreEventType.OE_CXL_ACK
                            chore_count = 1
                            special_chore_count = 0

                    # internally contains assert statements
                    last_cxl_chore_id, last_cxl_rej_chore_id = verify_cxl_rej(last_cxl_chore_id, last_cxl_rej_chore_id,
                                                                              check_chore_event, check_symbol,
                                                                              executor_http_client,
                                                                              ChoreStatusType.OE_ACKED)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_cxl_rej_n_revert_to_unack(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                   pair_strat_, expected_strat_limits_,
                                   expected_strat_status_, symbol_overview_obj_list,
                                   last_barter_fixture_list, market_depth_basemodel_list,
                                   buy_chore_, sell_chore_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_new_to_cxl_rej_chores"] = True
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50

            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            bid_buy_top_market_depth = None
            ask_sell_top_market_depth = None
            stored_market_depth = executor_http_client.get_all_market_depth_client()
            for market_depth in stored_market_depth:
                if (market_depth.symbol == leg1_symbol and market_depth.position == 0 and
                        market_depth.side == TickType.BID):
                    bid_buy_top_market_depth = market_depth
                if (market_depth.symbol == leg2_symbol and market_depth.position == 0 and
                        market_depth.side == TickType.ASK):
                    ask_sell_top_market_depth = market_depth

            for check_symbol in [leg1_symbol, leg2_symbol]:
                continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(check_symbol,
                                                                                                    config_dict)
                chore_count = 0
                special_chore_count = 0
                last_cxl_chore_id = None
                last_cxl_rej_chore_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_http_client)
                    if check_symbol == leg1_symbol:
                        time.sleep(1)
                        update_tob_through_market_depth_to_place_buy_chore(executor_http_client,
                                                                           bid_buy_top_market_depth,
                                                                           ask_sell_top_market_depth)
                    else:
                        # required to make buy side tob latest
                        run_last_barter(leg1_symbol, leg2_symbol, [last_barter_fixture_list[0]], executor_http_client)

                        update_tob_through_market_depth_to_place_sell_chore(executor_http_client,
                                                                            ask_sell_top_market_depth,
                                                                            bid_buy_top_market_depth)
                    time.sleep(10)  # delay for chore to get placed and trigger cxl

                    if chore_count < continues_chore_count:
                        check_chore_event = ChoreEventType.OE_CXL_ACK
                        chore_count += 1
                    else:
                        if special_chore_count < continues_special_chore_count:
                            check_chore_event = "REJ"
                            special_chore_count += 1
                        else:
                            check_chore_event = ChoreEventType.OE_CXL_ACK
                            chore_count = 1
                            special_chore_count = 0

                    # internally contains assert statements
                    last_cxl_chore_id, last_cxl_rej_chore_id = verify_cxl_rej(last_cxl_chore_id, last_cxl_rej_chore_id,
                                                                              check_chore_event, check_symbol,
                                                                              executor_http_client,
                                                                              ChoreStatusType.OE_UNACK)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_cxl_rej_n_revert_to_filled(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                    pair_strat_, expected_strat_limits_,
                                    expected_strat_status_, symbol_overview_obj_list,
                                    last_barter_fixture_list, market_depth_basemodel_list,
                                    buy_chore_, sell_chore_,
                                    max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["force_fully_fill"] = True
                config_dict["symbol_configs"][symbol]["simulate_ack_to_cxl_rej_chores"] = True

            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            for check_symbol in [leg1_symbol, leg2_symbol]:
                continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(check_symbol,
                                                                                                    config_dict)
                chore_count = 0
                special_chore_count = 0
                last_cxl_chore_id = None
                last_cxl_rej_chore_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_http_client)
                    if check_symbol == leg1_symbol:
                        px = 100
                        qty = 90
                        place_new_chore(leg1_symbol, Side.BUY, px, qty, executor_http_client)
                    else:
                        px = 110
                        qty = 94
                        place_new_chore(leg2_symbol, Side.SELL, px, qty, executor_http_client)
                    time.sleep(10)  # delay for chore to get placed and trigger cxl

                    if chore_count < continues_chore_count:
                        check_chore_event = ChoreEventType.OE_CXL_ACK
                        chore_count += 1
                    else:
                        if special_chore_count < continues_special_chore_count:
                            check_chore_event = "REJ"
                            special_chore_count += 1
                        else:
                            check_chore_event = ChoreEventType.OE_CXL_ACK
                            chore_count = 1
                            special_chore_count = 0

                    # internally contains assert statements
                    if check_chore_event == "REJ":
                        # internally checks chore_journal is not None else raises assert exception internally
                        latest_cxl_rej_chore_journal = \
                            get_latest_chore_journal_with_events_and_symbol([ChoreEventType.OE_CXL_INT_REJ,
                                                                             ChoreEventType.OE_CXL_BRK_REJ,
                                                                             ChoreEventType.OE_CXL_EXH_REJ],
                                                                            check_symbol, executor_http_client,
                                                                            last_chore_id=last_cxl_rej_chore_id)
                        last_cxl_rej_chore_id = latest_cxl_rej_chore_journal.chore.chore_id

                        chore_snapshot = get_chore_snapshot_from_chore_id(latest_cxl_rej_chore_journal.chore.chore_id,
                                                                          executor_http_client)
                        assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
                            f"Unexpected chore_snapshot.chore_status: expected {ChoreStatusType.OE_FILLED}, " \
                            f"received {chore_snapshot.chore_status}"
                    else:
                        # checks chore_journal is not None else raises assert exception internally
                        latest_cxl_chore_journal = get_latest_chore_journal_with_event_and_symbol(
                            ChoreEventType.OE_CXL_ACK, check_symbol, executor_http_client,
                            last_chore_id=last_cxl_chore_id)
                        last_cxl_chore_id = latest_cxl_chore_journal.chore.chore_id

        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def test_no_cxl_req_from_residual_refresh_is_state_already_cxl_req(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
        pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, last_barter_fixture_list,
        refresh_sec_update_fixture):
    # creating strat
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    max_loop_count_per_side = 2
    residual_wait_sec = 4 * refresh_sec_update_fixture
    created_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["avoid_cxl_ack_after_cxl_req"] = True

        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_http_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)

        cxl_req_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL,
                                                                               buy_symbol, executor_http_client)
        time.sleep(residual_wait_sec)
        get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL,
                                                       buy_symbol, executor_http_client, expect_no_chore=True,
                                                       last_chore_id=cxl_req_chore_journal.chore.chore_id)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_alert_handling_for_pair_strat(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                       pair_strat_, expected_strat_limits_,
                                       expected_strat_status_, symbol_overview_obj_list,
                                       market_depth_basemodel_list):
    # creating strat
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    total_loop_count = 5
    active_pair_strat, executor_http_client = create_n_activate_strat(buy_symbol, sell_symbol, pair_strat_,
                                                                      expected_strat_limits_, expected_strat_status_,
                                                                      symbol_overview_obj_list,
                                                                      market_depth_basemodel_list)
    broker_id_list = []
    for loop_count in range(total_loop_count):
        broker = broker_fixture()
        strat_limits: StratLimitsBaseModel = StratLimitsBaseModel(_id=active_pair_strat.id,
                                                                  eligible_brokers=[broker])
        updated_strat_limits = executor_http_client.patch_strat_limits_client(
            jsonable_encoder(strat_limits, by_alias=True, exclude_none=True))

        assert broker in updated_strat_limits.eligible_brokers, f"couldn't find broker in " \
                                                                f"eligible_brokers list " \
                                                                f"{updated_strat_limits.eligible_brokers}"
        broker_id_list.append(broker.id)

    # deleting broker
    for broker_id in broker_id_list:
        delete_intended_broker = BrokerOptional(_id=broker_id)
        strat_limits: StratLimitsBaseModel = StratLimitsBaseModel(_id=active_pair_strat.id,
                                                                  eligible_brokers=[delete_intended_broker])
        updated_strat_limits = executor_http_client.patch_strat_limits_client(
            jsonable_encoder(strat_limits, by_alias=True, exclude_none=True))

        broker_id_list = [broker.id for broker in updated_strat_limits.eligible_brokers]
        assert broker_id not in broker_id_list, f"Unexpectedly found broker_id {broker_id} in broker_id list " \
                                                f"{broker_id_list}"


@pytest.mark.nightly
def test_underlying_account_cumulative_fill_qty_query(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                      pair_strat_, expected_strat_limits_,
                                                      expected_strat_status_, symbol_overview_obj_list,
                                                      last_barter_fixture_list, market_depth_basemodel_list,
                                                      refresh_sec_update_fixture):
    underlying_account_prefix: str = "Acc"
    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    buy_chore_id = None
    sell_chore_id = None
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        residual_wait_sec = 4 * refresh_sec_update_fixture
        active_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list))

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_http_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == leg1_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == leg2_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        # buy handling
        buy_tob_last_update_date_time_tracker, buy_chore_id = \
            create_fills_for_underlying_account_test(leg1_symbol, leg2_symbol,
                                                     buy_tob_last_update_date_time_tracker, buy_chore_id,
                                                     underlying_account_prefix, Side.BUY, executor_http_client,
                                                     bid_buy_top_market_depth, ask_sell_top_market_depth,
                                                     last_barter_fixture_list)

        time.sleep(residual_wait_sec)   #

        # sell handling
        sell_tob_last_update_date_time_tracker, sell_chore_id = \
            create_fills_for_underlying_account_test(leg1_symbol, leg2_symbol,
                                                     sell_tob_last_update_date_time_tracker, sell_chore_id,
                                                     underlying_account_prefix, Side.SELL, executor_http_client,
                                                     bid_buy_top_market_depth, ask_sell_top_market_depth,
                                                     last_barter_fixture_list)

        for symbol, side in [(leg1_symbol, "BUY"), (leg2_symbol, "SELL")]:
            underlying_account_cumulative_fill_qty_obj_list = \
                executor_http_client.get_underlying_account_cumulative_fill_qty_query_client(symbol, side)
            assert len(underlying_account_cumulative_fill_qty_obj_list) == 1, \
                "Expected exactly one obj from query get_underlying_account_cumulative_fill_qty_query_client," \
                f"received {len(underlying_account_cumulative_fill_qty_obj_list)}, received list " \
                f"{underlying_account_cumulative_fill_qty_obj_list}"
            assert len(
                underlying_account_cumulative_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty) == 2, \
                "length of list field underlying_account_n_cumulative_fill_qty of " \
                "underlying_account_cumulative_fill_qty_obj mismatched, expected 2 received " \
                f"{len(underlying_account_cumulative_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty)}"

            underlying_account_count = 2
            for loop_count in range(underlying_account_count):
                underlying_account_n_cum_fill_qty_obj = \
                    underlying_account_cumulative_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty[
                        loop_count]
                assert underlying_account_n_cum_fill_qty_obj.underlying_account == \
                       f"{underlying_account_prefix}_{underlying_account_count - loop_count}", \
                       "underlying_account string field of underlying_account_n_cum_fill_qty_obj mismatched: " \
                       f"expected {underlying_account_prefix}_{underlying_account_count - loop_count} " \
                       f"received {underlying_account_n_cum_fill_qty_obj.underlying_account}"
                assert underlying_account_n_cum_fill_qty_obj.cumulative_qty == 15, \
                    "Unexpected cumulative qty: expected 15 received " \
                    f"{underlying_account_n_cum_fill_qty_obj.cumulative_qty}"


@pytest.mark.nightly
def test_last_n_sec_chore_qty_sum(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                  pair_strat_, expected_strat_limits_,
                                  expected_strat_status_, symbol_overview_obj_list,
                                  last_barter_fixture_list, market_depth_basemodel_list,
                                  buy_fill_journal_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    total_chore_count_for_each_side = 5
    expected_strat_limits_ = copy.deepcopy(expected_strat_limits_)
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_http_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        # buy testing
        buy_new_chore_id = None
        chore_create_time_list = []
        chore_qty_list = []
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(executor_http_client, bid_buy_top_market_depth,
                                                               ask_sell_top_market_depth)

            ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                               buy_symbol, executor_http_client,
                                                                               last_chore_id=buy_new_chore_id)
            buy_new_chore_id = ack_chore_journal.chore.chore_id
            chore_create_time_list.append(ack_chore_journal.chore_event_date_time)
            chore_qty_list.append(ack_chore_journal.chore.qty)
            if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                time.sleep(residual_wait_sec)   # wait for this chore to get cancelled by residual
            else:
                time.sleep(2)

        chore_create_time_list.reverse()
        chore_qty_list.reverse()
        last_n_sec_qty = 0
        for loop_count in range(total_chore_count_for_each_side):
            delta = DateTime.utcnow() - chore_create_time_list[loop_count]
            last_n_sec = int(math.ceil(delta.total_seconds())) + 1
            last_n_sec_qty += chore_qty_list[loop_count]

            # making portfolio_limits_obj.rolling_max_chore_count.rolling_tx_count_period_seconds computed last_n_sec(s)
            # this is required as last_n_sec_chore_qty takes internally this limit as last_n_sec to provide chore_qty
            # in query
            rolling_max_chore_count = RollingMaxChoreCountOptional(rolling_tx_count_period_seconds=last_n_sec)
            portfolio_limits = PortfolioLimitsBaseModel(_id=1, rolling_max_chore_count=rolling_max_chore_count)
            updated_portfolio_limits = \
                email_book_service_native_web_client.patch_portfolio_limits_client(
                    portfolio_limits.model_dump(by_alias=True, exclude_none=True))
            assert updated_portfolio_limits.rolling_max_chore_count.rolling_tx_count_period_seconds == last_n_sec, \
                f"Unexpected last_n_sec value: expected {last_n_sec}, " \
                f"received {updated_portfolio_limits.rolling_max_chore_count.rolling_tx_count_period_seconds}"

            call_date_time = DateTime.utcnow()
            executor_check_snapshot_obj = \
                executor_http_client.get_executor_check_snapshot_query_client(buy_symbol, "BUY", last_n_sec)

            assert len(executor_check_snapshot_obj) == 1, \
                f"Received unexpected length of list of executor_check_snapshot_obj from query," \
                f"expected one obj received {len(executor_check_snapshot_obj)}"
            assert executor_check_snapshot_obj[0].last_n_sec_chore_qty == last_n_sec_qty, \
                f"Chore qty mismatched for last {last_n_sec} " \
                f"secs of {buy_symbol} from {call_date_time} for side {Side.BUY}"
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_acked_unsolicited_cxl(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                               expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                               last_barter_fixture_list, market_depth_basemodel_list,
                               buy_chore_, sell_chore_,
                               max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_chores to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_chores = 10
        active_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_chores"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            handle_unsolicited_cxl(leg1_symbol, leg2_symbol, last_barter_fixture_list, max_loop_count_per_side,
                                   executor_http_client, config_dict, residual_wait_sec)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_unacked_unsolicited_cxl(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                 expected_strat_status_, symbol_overview_obj_list,
                                 last_barter_fixture_list, market_depth_basemodel_list,
                                 buy_chore_, sell_chore_,
                                 max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_chores to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_chores = 10
        active_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_chores"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            handle_unsolicited_cxl(leg1_symbol, leg2_symbol, last_barter_fixture_list, max_loop_count_per_side,
                                   executor_http_client, config_dict, residual_wait_sec)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_pair_strat_related_models_update_counters(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                   pair_strat_, expected_strat_limits_, expected_strat_status_,
                                                   symbol_overview_obj_list, last_barter_fixture_list,
                                                   market_depth_basemodel_list,
                                                   refresh_sec_update_fixture):
    activated_strats = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    # creates and activates multiple pair_strats
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list:
        activated_strat, executor_http_client = (
            create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list, market_depth_basemodel_list))
        activated_strats.append((activated_strat, executor_http_client))

    for index, (activated_strat, executor_http_client) in enumerate(activated_strats):
        # updating pair_strat_params
        pair_strat = \
            PairStratBaseModel(_id=activated_strat.id,
                               pair_strat_params=PairStratParamsOptional(common_premium=index))
        updates_pair_strat = email_book_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
        assert updates_pair_strat.pair_strat_params_update_seq_num == \
               activated_strat.pair_strat_params_update_seq_num + 1, (
                f"Mismatched pair_strat_params_update_seq_num: expected "
                f"{activated_strat.pair_strat_params_update_seq_num + 1}, received "
                f"{updates_pair_strat.pair_strat_params_update_seq_num}")

    for index, (activated_strat, executor_http_client) in enumerate(activated_strats):
        strat_limits_obj = executor_http_client.get_strat_limits_client(activated_strat.id)

        # updating strat_limits
        strat_limits = StratLimitsBaseModel(_id=activated_strat.id, max_concentration=index)
        updates_strat_limits = executor_http_client.patch_strat_limits_client(
            jsonable_encoder(strat_limits, by_alias=True, exclude_none=True))
        assert updates_strat_limits.strat_limits_update_seq_num == \
               strat_limits_obj.strat_limits_update_seq_num + 1, (
                f"Mismatched strat_limits_update_seq_num: expected "
                f"{strat_limits_obj.strat_limits_update_seq_num + 1}, received "
                f"{updates_strat_limits.strat_limits_update_seq_num}")

    for index, (activated_strat, executor_http_client) in enumerate(activated_strats):
        strat_status_obj = executor_http_client.get_strat_status_client(activated_strat.id)

        # updating strat_status
        strat_status = StratStatusBaseModel(_id=activated_strat.id, average_premuim=index)
        updates_strat_status = executor_http_client.patch_strat_status_client(
            jsonable_encoder(strat_status, by_alias=True, exclude_none=True))
        assert updates_strat_status.strat_status_update_seq_num == \
               strat_status_obj.strat_status_update_seq_num + 1, (
                f"Mismatched strat_limits_update_seq_num: expected "
                f"{strat_status_obj.strat_status_update_seq_num + 1}, received "
                f"{updates_strat_status.strat_status_update_seq_num}")


# @@@ deprecated: Not applicable anymore after PortfolioAlert model changes
# @pytest.mark.nightly
# def test_portfolio_alert_updates(static_data_, clean_and_set_limits, sample_alert):
#     stored_portfolio_alert = log_book_web_client.get_portfolio_alert_client(portfolio_alert_id=1)
# 
#     alert = copy.deepcopy(sample_alert)
#     portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
#     updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(
#             jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True))
#     assert stored_portfolio_alert.alert_update_seq_num + 1 == updated_portfolio_alert.alert_update_seq_num, \
#         f"Mismatched alert_update_seq_num: expected {stored_portfolio_alert.alert_update_seq_num + 1}, " \
#         f"received {updated_portfolio_alert.alert_update_seq_num}"
# 
#     max_loop_count = 5
#     for loop_count in range(max_loop_count):
#         alert.alert_brief = f"Test update - {loop_count}"
#         portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
#         alert_updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(
#                 jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True))
#         assert updated_portfolio_alert.alert_update_seq_num + (loop_count + 1) == \
#                alert_updated_portfolio_alert.alert_update_seq_num, (
#                 f"Mismatched alert_update_seq_num: expected "
#                 f"{updated_portfolio_alert.alert_update_seq_num + (loop_count + 1)}, "
#                 f"received {alert_updated_portfolio_alert.alert_update_seq_num}")


@pytest.mark.nightly
def test_partial_ack(static_data_, clean_and_set_limits, pair_strat_,
                     expected_strat_limits_,
                     expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                     market_depth_basemodel_list, leg1_leg2_symbol_list, refresh_sec_update_fixture):
    partial_ack_qty: int | None = None

    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        active_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))
        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["ack_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.barter_simulator_reload_config_query_client()

            # buy fills check
            new_chore_id = None
            acked_chore_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_http_client)
                px = 100
                qty = 90
                place_new_chore(leg1_symbol, Side.BUY, px, qty, executor_http_client)
                time.sleep(2)  # delay for chore to get placed

                new_chore_id, acked_chore_id, partial_ack_qty = \
                    handle_partial_ack_checks(leg1_symbol, new_chore_id, acked_chore_id, executor_http_client,
                                              config_dict)

                if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                    time.sleep(residual_wait_sec)    # wait to make this open chore residual

            time.sleep(5)
            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            assert partial_ack_qty * max_loop_count_per_side == strat_status.total_fill_buy_qty, \
                f"Mismatched total_fill_buy_qty: Expected {partial_ack_qty * max_loop_count_per_side}, " \
                f"received {strat_status.total_fill_buy_qty}"

            # sell fills check
            new_chore_id = None
            acked_chore_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_http_client)
                px = 110
                qty = 95
                place_new_chore(leg2_symbol, Side.SELL, px, qty, executor_http_client)
                time.sleep(2)

                new_chore_id, acked_chore_id, partial_ack_qty = \
                    handle_partial_ack_checks(leg2_symbol, new_chore_id, acked_chore_id, executor_http_client,
                                              config_dict)

                if not executor_config_yaml_dict.get("allow_multiple_open_chores_per_strat"):
                    time.sleep(residual_wait_sec)    # wait to make this open chore residual

            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            assert partial_ack_qty * max_loop_count_per_side == strat_status.total_fill_sell_qty, \
                f"Mismatched total_fill_sell_qty: Expected {partial_ack_qty * max_loop_count_per_side}, " \
                f"received {strat_status.total_fill_sell_qty}"
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            err_str_ = (f"Some Error Occurred: exception: {e}, "
                        f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            print(err_str_)
            raise Exception(err_str_)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_update_residual_query(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                               expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                               last_barter_fixture_list, market_depth_basemodel_list,
                               refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_barter_fixture_list,
                                           market_depth_basemodel_list))
    total_loop_count = 5
    residual_qty = 5

    # Since both side have same last barter px in test cases
    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    buy_residual_qty = 0
    sell_residual_qty = 0
    buy_residual_notional = 0
    sell_residual_notional = 0
    for loop_count in range(total_loop_count):
        # buy side
        executor_http_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)
        buy_residual_qty += residual_qty
        strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
        strat_brief_list = executor_http_client.get_all_strat_brief_client()

        # since only one strat is created in this test
        strat_brief = strat_brief_list[0]

        buy_residual_notional = buy_residual_qty * get_px_in_usd(buy_last_barter_px)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        assert buy_residual_qty == strat_brief.pair_buy_side_bartering_brief.residual_qty, \
            f"Mismatch residual_qty: expected {buy_residual_qty} received " \
            f"{strat_brief.pair_buy_side_bartering_brief.residual_qty}"
        assert residual_notional == strat_status.residual.residual_notional, \
            f"Mismatch buy residual_notional, expected {residual_notional}, received " \
            f"{strat_status.residual.residual_notional}"

        # sell side
        executor_http_client.update_residuals_query_client(sell_symbol, Side.SELL, residual_qty)
        sell_residual_qty += residual_qty
        strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
        strat_brief_list = executor_http_client.get_all_strat_brief_client()

        # since only one strat is created in this test
        strat_brief = strat_brief_list[0]

        sell_residual_notional = sell_residual_qty * get_px_in_usd(sell_last_barter_px)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        assert sell_residual_qty == strat_brief.pair_sell_side_bartering_brief.residual_qty, \
            f"Mismatch residual_qty: expected {sell_residual_qty}, received " \
            f"{strat_brief.pair_sell_side_bartering_brief.residual_qty}"
        assert strat_status.residual.residual_notional == residual_notional, \
            (f"Mismatch sell residual_notional: expected {residual_notional} received "
             f"{strat_status.residual.residual_notional}")


@pytest.mark.nightly
def test_ack_post_unack_unsol_cxl(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                  expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                  last_barter_fixture_list, market_depth_basemodel_list,
                                  buy_chore_, sell_chore_,
                                  max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        bid_buy_top_market_depth = None
        ask_sell_top_market_depth = None
        stored_market_depth = executor_http_client.get_all_market_depth_client()
        for market_depth in stored_market_depth:
            if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
                bid_buy_top_market_depth = market_depth
            if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
                ask_sell_top_market_depth = market_depth

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                          executor_http_client)
        latest_cxl_ack_obj = get_latest_chore_journal_with_events_and_symbol([ChoreEventType.OE_CXL_ACK,
                                                                              ChoreEventType.OE_UNSOL_CXL], buy_symbol,
                                                                             executor_http_client)

        executor_http_client.barter_simulator_process_chore_ack_query_client(
            latest_unack_obj.chore.chore_id,
            latest_unack_obj.chore.px,
            latest_unack_obj.chore.qty,
            latest_unack_obj.chore.side,
            latest_unack_obj.chore.security.sec_id,
            latest_unack_obj.chore.underlying_account)

        chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                          executor_http_client)

        assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
            f"Mismatched: Chore status must be DOD but found: {chore_snapshot.chore_status = }"

        check_str = ("Unexpected: Received chore_journal of event: ChoreEventType.OE_ACK on chore of "
                     "chore_snapshot status: ChoreStatusType.OE_DOD")
        assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_fill_post_unack_unsol_cxl(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        buy_symbol_side_snapshot = None
        buy_qty = None
        buy_px = None
        buy_filled_qty = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            # buy test
            if side == Side.BUY:
                buy_qty = qty
                buy_px = px

            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, chore_symbol,
                                                                              executor_http_client)
            latest_cxl_ack_obj = get_latest_chore_journal_with_events_and_symbol([ChoreEventType.OE_CXL_ACK,
                                                                                  ChoreEventType.OE_UNSOL_CXL],
                                                                                 chore_symbol,
                                                                                 executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                              executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
                f"Mismatched: Chore status must be DOD but found: {chore_snapshot.chore_status = }"
            assert chore_snapshot.cxled_qty == latest_unack_obj.chore.qty, \
                (f"Mismatched: ChoreSnapshot cxled_qty must be {latest_unack_obj.chore.qty}, found "
                 f"{chore_snapshot.cxled_qty}")
            assert chore_snapshot.cxled_notional == qty * get_px_in_usd(px), \
                (f"Mismatched: ChoreSnapshot cxled_notional must be "
                 f"{qty * get_px_in_usd(px)}, found {chore_snapshot.cxled_notional}")
            assert chore_snapshot.avg_cxled_px == latest_unack_obj.chore.px, \
                (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
                 f"{latest_unack_obj.chore.px}, found {chore_snapshot.avg_cxled_px}")
            assert chore_snapshot.filled_qty == 0, \
                f"Mismatched: ChoreSnapshot avg_cxled_px must be 0, found {chore_snapshot.filled_qty}"
            assert chore_snapshot.fill_notional == 0, \
                f"Mismatched: ChoreSnapshot fill_notional must be 0, found {chore_snapshot.fill_notional}"
            assert chore_snapshot.avg_fill_px == 0, \
                f"Mismatched: ChoreSnapshot avg_fill_px must be 0, found {chore_snapshot.avg_fill_px}"

            symbol_side_snapshot_list = (
                executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                    latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side))
            assert len(symbol_side_snapshot_list) == 1, \
                (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
                 f"{latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side}")

            symbol_side_snapshot = symbol_side_snapshot_list[0]
            if side == Side.BUY:
                buy_symbol_side_snapshot = symbol_side_snapshot
            assert symbol_side_snapshot.total_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatched: expected symbol_side_snapshot.total_qty: {chore_snapshot.chore_brief.qty}, "
                 f"found {symbol_side_snapshot.total_qty = }")
            assert symbol_side_snapshot.avg_px == chore_snapshot.chore_brief.px, \
                (f"Mismatched: expected symbol_side_snapshot.avg_px: {chore_snapshot.chore_brief.px}, "
                 f"found {symbol_side_snapshot.avg_px = }")
            assert symbol_side_snapshot.total_filled_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.total_filled_qty must be 0, found "
                 f"{symbol_side_snapshot.total_filled_qty = }")
            assert symbol_side_snapshot.total_fill_notional == 0, \
                (f"Mismatched: symbol_side_snapshot.total_fill_notional must be 0, found "
                 f"{symbol_side_snapshot.total_fill_notional = }")
            assert symbol_side_snapshot.avg_fill_px == 0, \
                (f"Mismatched: symbol_side_snapshot.avg_fill_px must be 0, found "
                 f"{symbol_side_snapshot.avg_fill_px = }")
            assert symbol_side_snapshot.total_cxled_qty == latest_unack_obj.chore.qty, \
                (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be {latest_unack_obj.chore.qty}, found "
                 f"{symbol_side_snapshot.total_cxled_qty = }")
            assert (symbol_side_snapshot.total_cxled_notional ==
                    (latest_unack_obj.chore.qty * get_px_in_usd(latest_unack_obj.chore.px))), \
                (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
                 f"{latest_unack_obj.chore.qty * get_px_in_usd(latest_unack_obj.chore.px)}, found "
                 f"{symbol_side_snapshot.total_cxled_notional = }")
            assert symbol_side_snapshot.avg_cxled_px == latest_unack_obj.chore.px, \
                (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be {latest_unack_obj.chore.px}, found "
                 f"{symbol_side_snapshot.avg_cxled_px = }")
            assert symbol_side_snapshot.last_update_fill_px == 0, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be 0, found "
                 f"{symbol_side_snapshot.last_update_fill_px = }")
            assert symbol_side_snapshot.last_update_fill_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be 0, found "
                 f"{symbol_side_snapshot.last_update_fill_qty = }")

            buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
            strat_limits = executor_http_client.get_strat_limits_client(1)
            strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat.id)
            if side == Side.BUY:
                strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
            else:
                strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
            assert (strat_brief_bartering_brief.open_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
                 f"0, found {strat_brief_bartering_brief.open_qty = }")
            assert (strat_brief_bartering_brief.open_notional == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
                 f"0, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.residual_qty == chore_snapshot.cxled_qty), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
                 f"{chore_snapshot.cxled_qty}, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_chores == 5), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
                 f"5, found {strat_brief_bartering_brief.consumable_open_chores = }")
            assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == chore_snapshot.cxled_qty), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
                 f"{chore_snapshot.cxled_qty}, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
            assert (strat_brief_bartering_brief.consumable_notional == (
                    strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
                 f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_notional == strat_limits.max_open_single_leg_notional), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_open_notional = }")
            total_security_size: int = \
                static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
            assert (strat_brief_bartering_brief.consumable_concentration == (
                    (total_security_size / 100 * strat_limits.max_concentration) -
                    symbol_side_snapshot.total_filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
                 f"{(total_security_size / 100 * strat_limits.max_concentration) - symbol_side_snapshot.total_filled_qty}, "
                 f"found {strat_brief_bartering_brief.consumable_concentration = }")
            assert (strat_brief_bartering_brief.consumable_cxl_qty == (
                    (((symbol_side_snapshot.total_filled_qty +
                       symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
                    symbol_side_snapshot.total_cxled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
            if side == Side.BUY:
                other_side_residual_qty = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
            if side == Side.BUY:
                current_last_barter_px = buy_last_barter_px
                other_last_barter_px = sell_last_barter_px
            else:
                current_last_barter_px = sell_last_barter_px
                other_last_barter_px = buy_last_barter_px
            assert (strat_brief_bartering_brief.indicative_consumable_residual == (
                    strat_limits.residual_restriction.max_residual -
                    ((strat_brief_bartering_brief.residual_qty *
                      get_px_in_usd(current_last_barter_px)) - (
                             other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")

            if side == Side.BUY:
                other_side_fill_notional = 0
            else:
                other_side_fill_notional = buy_symbol_side_snapshot.total_fill_notional
            assert (strat_brief.consumable_nett_filled_notional == (
                    strat_limits.max_net_filled_notional -
                    abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            if side == Side.BUY:
                total_qty = strat_status.total_buy_qty
                total_open_qty = strat_status.total_open_buy_qty
                total_open_notional = strat_status.total_open_buy_notional
                avg_open_px = strat_status.avg_open_buy_px
                total_fill_qty = strat_status.total_fill_buy_qty
                total_fill_notional = strat_status.total_fill_buy_notional
                avg_fill_px = strat_status.avg_fill_buy_px
                total_cxl_qty = strat_status.total_cxl_buy_qty
                total_cxl_notional = strat_status.total_cxl_buy_notional
                avg_cxl_px = strat_status.avg_cxl_buy_px
            else:
                total_qty = strat_status.total_sell_qty
                total_open_qty = strat_status.total_open_sell_qty
                total_open_notional = strat_status.total_open_sell_notional
                avg_open_px = strat_status.avg_open_sell_px
                total_fill_qty = strat_status.total_fill_sell_qty
                total_fill_notional = strat_status.total_fill_sell_notional
                avg_fill_px = strat_status.avg_fill_sell_px
                total_cxl_qty = strat_status.total_cxl_sell_qty
                total_cxl_notional = strat_status.total_cxl_sell_notional
                avg_cxl_px = strat_status.avg_cxl_sell_px

            total_open_exposure = strat_status.total_open_exposure
            total_fill_exposure = strat_status.total_fill_exposure
            total_cxl_exposure = strat_status.total_cxl_exposure
            assert total_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
                 f"{chore_snapshot.chore_brief.qty}, found {total_qty = }")
            assert total_open_qty == 0, \
                (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
                 f"0, found {total_open_qty = }")
            assert (total_open_notional == 0), \
                (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
                 f"0, found {total_open_notional = }")
            assert (avg_open_px == 0), \
                (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
                 f"0, found {avg_open_px = }")
            assert (total_fill_qty == 0), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
                 f"0, found {total_fill_qty = }")
            assert (total_fill_notional == 0), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
                 f"0, found {total_fill_notional = }")
            assert (avg_fill_px == 0), \
                (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
                 f"0, found {avg_fill_px = }")
            assert (total_cxl_qty == qty), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
                 f"{qty}, found {total_cxl_qty = }")
            assert (total_cxl_notional == qty * get_px_in_usd(px)), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
                 f"{qty * get_px_in_usd(px)}, found {total_cxl_notional = }")
            assert (avg_cxl_px == px), \
                (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
                 f"{px}, found {avg_cxl_px = }")
            if side == Side.BUY:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"0, found {total_fill_exposure = }")
                assert (total_cxl_exposure == qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{qty * get_px_in_usd(px)}, found {total_cxl_exposure = }")
            else:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == buy_filled_qty * get_px_in_usd(buy_px)), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{buy_filled_qty * get_px_in_usd(buy_px)}, found {total_fill_exposure = }")
                assert (total_cxl_exposure == (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{(buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - qty * get_px_in_usd(px)}, "
                     f"found {total_cxl_exposure = }")

            portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
            if side == Side.BUY:
                overall_notional = portfolio_status.overall_buy_notional
            else:
                overall_notional = portfolio_status.overall_sell_notional
            assert (overall_notional == 0), \
                (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
                 f"0, found {overall_notional = }")

            # applying ack leading to overfill
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_unack_obj.chore.chore_id, latest_unack_obj.chore.px, latest_unack_obj.chore.qty,
                latest_unack_obj.chore.side, latest_unack_obj.chore.security.sec_id,
                latest_unack_obj.chore.underlying_account)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                              executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
                f"Mismatched: Chore status must be OE_DOD but found: {chore_snapshot.chore_status = }"
            assert chore_snapshot.cxled_qty == qty - filled_qty, \
                (f"Mismatched: ChoreSnapshot cxled_qty must be {qty - filled_qty}, found "
                 f"{chore_snapshot.cxled_qty}")
            assert chore_snapshot.cxled_notional == (qty - filled_qty) * get_px_in_usd(px), \
                (f"Mismatched: ChoreSnapshot cxled_notional must be "
                 f"{(qty - filled_qty) * get_px_in_usd(px)}, found {chore_snapshot.cxled_notional}")
            assert chore_snapshot.avg_cxled_px == px, \
                (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
                 f"{px}, found {chore_snapshot.avg_cxled_px}")
            assert chore_snapshot.filled_qty == filled_qty, \
                f"Mismatched: ChoreSnapshot avg_cxled_px must be {filled_qty}, found {chore_snapshot.filled_qty}"
            assert chore_snapshot.fill_notional == filled_qty * get_px_in_usd(px), \
                (f"Mismatched: ChoreSnapshot fill_notional must be {filled_qty * get_px_in_usd(px)}, "
                 f"found {chore_snapshot.fill_notional}")
            assert chore_snapshot.avg_fill_px == px, \
                f"Mismatched: ChoreSnapshot avg_fill_px must be {px}, found {chore_snapshot.avg_fill_px}"

            symbol_side_snapshot_list = (
                executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                    latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side))
            assert len(symbol_side_snapshot_list) == 1, \
                (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
                 f"{latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side}")

            symbol_side_snapshot = symbol_side_snapshot_list[0]
            if side == Side.BUY:
                buy_symbol_side_snapshot = symbol_side_snapshot
            assert symbol_side_snapshot.total_qty == qty, \
                (f"Mismatched: expected symbol_side_snapshot.total_qty: {qty}, "
                 f"found {symbol_side_snapshot.total_qty = }")
            assert symbol_side_snapshot.avg_px == px, \
                (f"Mismatched: expected symbol_side_snapshot.avg_px: {px}, "
                 f"found {symbol_side_snapshot.avg_px = }")
            assert symbol_side_snapshot.total_filled_qty == filled_qty, \
                (f"Mismatched: symbol_side_snapshot.total_filled_qty must be {filled_qty}, found "
                 f"{symbol_side_snapshot.total_filled_qty = }")
            assert symbol_side_snapshot.total_fill_notional == filled_qty * get_px_in_usd(px), \
                (f"Mismatched: symbol_side_snapshot.total_fill_notional must be {filled_qty * get_px_in_usd(px)}, "
                 f"found {symbol_side_snapshot.total_fill_notional = }")
            assert symbol_side_snapshot.avg_fill_px == px, \
                (f"Mismatched: symbol_side_snapshot.avg_fill_px must be {px}, found "
                 f"{symbol_side_snapshot.avg_fill_px = }")
            assert symbol_side_snapshot.total_cxled_qty == (qty - filled_qty), \
                (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be {qty - filled_qty}, found "
                 f"{symbol_side_snapshot.total_cxled_qty = }")
            assert (symbol_side_snapshot.total_cxled_notional == (qty - filled_qty) * get_px_in_usd(px)), \
                (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
                 f"{(qty - filled_qty) * get_px_in_usd(px)}, found {symbol_side_snapshot.total_cxled_notional = }")
            assert symbol_side_snapshot.avg_cxled_px == px, \
                (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be {px}, found "
                 f"{symbol_side_snapshot.avg_cxled_px = }")
            assert symbol_side_snapshot.last_update_fill_px == px, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be {px}, found "
                 f"{symbol_side_snapshot.last_update_fill_px = }")
            assert symbol_side_snapshot.last_update_fill_qty == filled_qty, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be {filled_qty}, found "
                 f"{symbol_side_snapshot.last_update_fill_qty = }")

            buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
            strat_limits = executor_http_client.get_strat_limits_client(1)
            strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat.id)
            if side == Side.BUY:
                strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
            else:
                strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
            assert (strat_brief_bartering_brief.open_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
                 f"0, found {strat_brief_bartering_brief.open_qty = }")
            assert (strat_brief_bartering_brief.open_notional == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
                 f"0, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.residual_qty == (qty - filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
                 f"{qty - filled_qty}, found {strat_brief_bartering_brief.residual_qty = }")
            assert (strat_brief_bartering_brief.consumable_open_chores == 5), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
                 f"5, found {strat_brief_bartering_brief.consumable_open_chores = }")
            assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == (qty - filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
                 f"{(qty - filled_qty)}, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
            assert (strat_brief_bartering_brief.consumable_notional == (
                    strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
                 f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_notional == strat_limits.max_open_single_leg_notional), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_open_notional = }")
            total_security_size: int = \
                static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
            assert (strat_brief_bartering_brief.consumable_concentration == (
                    (total_security_size / 100 * strat_limits.max_concentration) -
                    symbol_side_snapshot.total_filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
                 f"{(total_security_size / 100 * strat_limits.max_concentration) - symbol_side_snapshot.total_filled_qty}, "
                 f"found {strat_brief_bartering_brief.consumable_concentration = }")
            assert (strat_brief_bartering_brief.consumable_cxl_qty == (
                    (((symbol_side_snapshot.total_filled_qty +
                       symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
                    symbol_side_snapshot.total_cxled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
            if side == Side.BUY:
                other_side_residual_qty = 0
                current_last_barter_px = buy_last_barter_px
                other_last_barter_px = sell_last_barter_px
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                current_last_barter_px = sell_last_barter_px
                other_last_barter_px = buy_last_barter_px

            assert (strat_brief_bartering_brief.indicative_consumable_residual == (
                    strat_limits.residual_restriction.max_residual -
                    ((strat_brief_bartering_brief.residual_qty *
                      get_px_in_usd(current_last_barter_px)) - (
                             other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
                 f"{strat_limits.residual_restriction.max_residual - ((strat_brief_bartering_brief.residual_qty * get_px_in_usd(current_last_barter_px)) - (other_side_residual_qty * get_px_in_usd(other_last_barter_px)))}, "
                 f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")

            if side == Side.BUY:
                other_side_fill_notional = 0
            else:
                other_side_fill_notional = buy_symbol_side_snapshot.total_fill_notional
            assert (strat_brief.consumable_nett_filled_notional == (
                    strat_limits.max_net_filled_notional -
                    abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
                (
                    f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
                    f"{strat_limits.max_open_single_leg_notional}, "
                    f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            if side == Side.BUY:
                total_qty = strat_status.total_buy_qty
                total_open_qty = strat_status.total_open_buy_qty
                total_open_notional = strat_status.total_open_buy_notional
                avg_open_px = strat_status.avg_open_buy_px
                total_fill_qty = strat_status.total_fill_buy_qty
                total_fill_notional = strat_status.total_fill_buy_notional
                avg_fill_px = strat_status.avg_fill_buy_px
                total_cxl_qty = strat_status.total_cxl_buy_qty
                total_cxl_notional = strat_status.total_cxl_buy_notional
                avg_cxl_px = strat_status.avg_cxl_buy_px
            else:
                total_qty = strat_status.total_sell_qty
                total_open_qty = strat_status.total_open_sell_qty
                total_open_notional = strat_status.total_open_sell_notional
                avg_open_px = strat_status.avg_open_sell_px
                total_fill_qty = strat_status.total_fill_sell_qty
                total_fill_notional = strat_status.total_fill_sell_notional
                avg_fill_px = strat_status.avg_fill_sell_px
                total_cxl_qty = strat_status.total_cxl_sell_qty
                total_cxl_notional = strat_status.total_cxl_sell_notional
                avg_cxl_px = strat_status.avg_cxl_sell_px

            total_open_exposure = strat_status.total_open_exposure
            total_fill_exposure = strat_status.total_fill_exposure
            total_cxl_exposure = strat_status.total_cxl_exposure
            assert total_qty == qty, \
                (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
                 f"{qty}, found {total_qty = }")
            assert total_open_qty == 0, \
                (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
                 f"0, found {total_open_qty = }")
            assert (total_open_notional == 0), \
                (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
                 f"0, found {total_open_notional = }")
            assert (avg_open_px == 0), \
                (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
                 f"0, found {avg_open_px = }")
            assert (total_fill_qty == filled_qty), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
                 f"{filled_qty}, found {total_fill_qty = }")
            assert (total_fill_notional == filled_qty * get_px_in_usd(px)), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
                 f"{filled_qty * get_px_in_usd(px)}, found {total_fill_notional = }")
            assert (avg_fill_px == px), \
                (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
                 f"{px}, found {avg_fill_px = }")
            assert (total_cxl_qty == (qty - filled_qty)), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
                 f"{qty - filled_qty}, found {total_cxl_qty = }")
            assert (total_cxl_notional == (qty - filled_qty) * get_px_in_usd(px)), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
                 f"{(qty - filled_qty) * get_px_in_usd(px)}, found {total_cxl_notional = }")
            assert (avg_cxl_px == px), \
                (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
                 f"{px}, found {avg_cxl_px = }")
            if side == Side.BUY:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == filled_qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{filled_qty * get_px_in_usd(px)}, found {total_fill_exposure = }")
                assert (total_cxl_exposure == (qty - filled_qty) * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"0, found {total_cxl_exposure = }")
            else:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == (
                        buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px))), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)}, "
                     f"found {total_fill_exposure = }")
                assert (total_cxl_exposure == (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - (qty - filled_qty) * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{(buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - (qty - filled_qty) * get_px_in_usd(px)}, "
                     f"found {total_cxl_exposure = }")

            portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
            if side == Side.BUY:
                overall_notional = portfolio_status.overall_buy_notional
            else:
                overall_notional = portfolio_status.overall_sell_notional
            assert (overall_notional == filled_qty * get_px_in_usd(px)), \
                (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
                 f"{filled_qty * get_px_in_usd(px)}, found {overall_notional = }")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_fulfill_post_unack_unsol_cxl(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
        executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)

        buy_symbol_side_snapshot = None
        buy_px = None
        buy_qty = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            # buy test
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, chore_symbol,
                                                                              executor_http_client)
            latest_cxl_ack_obj = get_latest_chore_journal_with_events_and_symbol([ChoreEventType.OE_CXL_ACK,
                                                                                  ChoreEventType.OE_UNSOL_CXL],
                                                                                 chore_symbol,
                                                                                 executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                              executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
                f"Mismatched: Chore status must be DOD but found: {chore_snapshot.chore_status = }"
            assert chore_snapshot.cxled_qty == latest_unack_obj.chore.qty, \
                (f"Mismatched: ChoreSnapshot cxled_qty must be {latest_unack_obj.chore.qty}, found "
                 f"{chore_snapshot.cxled_qty}")
            assert chore_snapshot.cxled_notional == qty * get_px_in_usd(px), \
                (f"Mismatched: ChoreSnapshot cxled_notional must be "
                 f"{qty * get_px_in_usd(px)}, found {chore_snapshot.cxled_notional}")
            assert chore_snapshot.avg_cxled_px == latest_unack_obj.chore.px, \
                (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
                 f"{latest_unack_obj.chore.px}, found {chore_snapshot.avg_cxled_px}")
            assert chore_snapshot.filled_qty == 0, \
                f"Mismatched: ChoreSnapshot avg_cxled_px must be 0, found {chore_snapshot.filled_qty}"
            assert chore_snapshot.fill_notional == 0, \
                f"Mismatched: ChoreSnapshot fill_notional must be 0, found {chore_snapshot.fill_notional}"
            assert chore_snapshot.avg_fill_px == 0, \
                f"Mismatched: ChoreSnapshot avg_fill_px must be 0, found {chore_snapshot.avg_fill_px}"

            symbol_side_snapshot_list = (
                executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                    latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side))
            assert len(symbol_side_snapshot_list) == 1, \
                (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
                 f"{latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side}")

            symbol_side_snapshot = symbol_side_snapshot_list[0]
            if side == Side.BUY:
                buy_symbol_side_snapshot = symbol_side_snapshot
            assert symbol_side_snapshot.total_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatched: expected symbol_side_snapshot.total_qty: {chore_snapshot.chore_brief.qty}, "
                 f"found {symbol_side_snapshot.total_qty = }")
            assert symbol_side_snapshot.avg_px == chore_snapshot.chore_brief.px, \
                (f"Mismatched: expected symbol_side_snapshot.avg_px: {chore_snapshot.chore_brief.px}, "
                 f"found {symbol_side_snapshot.avg_px = }")
            assert symbol_side_snapshot.total_filled_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.total_filled_qty must be 0, found "
                 f"{symbol_side_snapshot.total_filled_qty = }")
            assert symbol_side_snapshot.total_fill_notional == 0, \
                (f"Mismatched: symbol_side_snapshot.total_fill_notional must be 0, found "
                 f"{symbol_side_snapshot.total_fill_notional = }")
            assert symbol_side_snapshot.avg_fill_px == 0, \
                (f"Mismatched: symbol_side_snapshot.avg_fill_px must be 0, found "
                 f"{symbol_side_snapshot.avg_fill_px = }")
            assert symbol_side_snapshot.total_cxled_qty == latest_unack_obj.chore.qty, \
                (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be {latest_unack_obj.chore.qty}, found "
                 f"{symbol_side_snapshot.total_cxled_qty = }")
            assert (symbol_side_snapshot.total_cxled_notional ==
                    (latest_unack_obj.chore.qty * get_px_in_usd(latest_unack_obj.chore.px))), \
                (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
                 f"{latest_unack_obj.chore.qty * get_px_in_usd(latest_unack_obj.chore.px)}, found "
                 f"{symbol_side_snapshot.total_cxled_notional = }")
            assert symbol_side_snapshot.avg_cxled_px == latest_unack_obj.chore.px, \
                (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be {latest_unack_obj.chore.px}, found "
                 f"{symbol_side_snapshot.avg_cxled_px = }")
            assert symbol_side_snapshot.last_update_fill_px == 0, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be 0, found "
                 f"{symbol_side_snapshot.last_update_fill_px = }")
            assert symbol_side_snapshot.last_update_fill_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be 0, found "
                 f"{symbol_side_snapshot.last_update_fill_qty = }")

            buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
            strat_limits = executor_http_client.get_strat_limits_client(1)
            strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat.id)
            if side == Side.BUY:
                strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
            else:
                strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
            assert (strat_brief_bartering_brief.open_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
                 f"0, found {strat_brief_bartering_brief.open_qty = }")
            assert (strat_brief_bartering_brief.open_notional == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
                 f"0, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.residual_qty == chore_snapshot.cxled_qty), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
                 f"{chore_snapshot.cxled_qty}, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_chores == 5), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
                 f"5, found {strat_brief_bartering_brief.consumable_open_chores = }")
            assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == chore_snapshot.cxled_qty), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
                 f"{chore_snapshot.cxled_qty}, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
            assert (strat_brief_bartering_brief.consumable_notional == (
                    strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
                 f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_notional == strat_limits.max_open_single_leg_notional), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_open_notional = }")
            total_security_size: int = \
                static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
            assert (strat_brief_bartering_brief.consumable_concentration == (
                    (total_security_size / 100 * strat_limits.max_concentration) -
                    symbol_side_snapshot.total_filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
                 f"{(total_security_size / 100 * strat_limits.max_concentration) - symbol_side_snapshot.total_filled_qty}, "
                 f"found {strat_brief_bartering_brief.consumable_concentration = }")
            assert (strat_brief_bartering_brief.consumable_cxl_qty == (
                    (((symbol_side_snapshot.total_filled_qty +
                       symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
                    symbol_side_snapshot.total_cxled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
            other_side_residual_qty = 0
            if side == Side.BUY:
                current_last_barter_px = buy_last_barter_px
                other_last_barter_px = sell_last_barter_px
            else:
                current_last_barter_px = sell_last_barter_px
                other_last_barter_px = buy_last_barter_px
            assert (strat_brief_bartering_brief.indicative_consumable_residual == (
                    strat_limits.residual_restriction.max_residual -
                    ((strat_brief_bartering_brief.residual_qty *
                      get_px_in_usd(current_last_barter_px)) - (
                             other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
                 f"{strat_limits.residual_restriction.max_residual - ((strat_brief_bartering_brief.residual_qty * get_px_in_usd(current_last_barter_px)) - (other_side_residual_qty * get_px_in_usd(other_last_barter_px)))}, "
                 f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")

            if side == Side.BUY:
                other_side_fill_notional = 0
            else:
                other_side_fill_notional = buy_symbol_side_snapshot.total_fill_notional
            assert (strat_brief.consumable_nett_filled_notional == (
                    strat_limits.max_net_filled_notional -
                    abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
                (
                    f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
                    f"{strat_limits.max_open_single_leg_notional}, "
                    f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            if side == Side.BUY:
                total_qty = strat_status.total_buy_qty
                total_open_qty = strat_status.total_open_buy_qty
                total_open_notional = strat_status.total_open_buy_notional
                avg_open_px = strat_status.avg_open_buy_px
                total_fill_qty = strat_status.total_fill_buy_qty
                total_fill_notional = strat_status.total_fill_buy_notional
                avg_fill_px = strat_status.avg_fill_buy_px
                total_cxl_qty = strat_status.total_cxl_buy_qty
                total_cxl_notional = strat_status.total_cxl_buy_notional
                avg_cxl_px = strat_status.avg_cxl_buy_px
            else:
                total_qty = strat_status.total_sell_qty
                total_open_qty = strat_status.total_open_sell_qty
                total_open_notional = strat_status.total_open_sell_notional
                avg_open_px = strat_status.avg_open_sell_px
                total_fill_qty = strat_status.total_fill_sell_qty
                total_fill_notional = strat_status.total_fill_sell_notional
                avg_fill_px = strat_status.avg_fill_sell_px
                total_cxl_qty = strat_status.total_cxl_sell_qty
                total_cxl_notional = strat_status.total_cxl_sell_notional
                avg_cxl_px = strat_status.avg_cxl_sell_px

            total_open_exposure = strat_status.total_open_exposure
            total_fill_exposure = strat_status.total_fill_exposure
            total_cxl_exposure = strat_status.total_cxl_exposure
            assert total_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
                 f"{chore_snapshot.chore_brief.qty}, found {total_qty = }")
            assert total_open_qty == 0, \
                (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
                 f"0, found {total_open_qty = }")
            assert (total_open_notional == 0), \
                (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
                 f"0, found {total_open_notional = }")
            assert (avg_open_px == 0), \
                (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
                 f"0, found {avg_open_px = }")
            assert (total_fill_qty == 0), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
                 f"0, found {total_fill_qty = }")
            assert (total_fill_notional == 0), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
                 f"0, found {total_fill_notional = }")
            assert (avg_fill_px == 0), \
                (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
                 f"0, found {avg_fill_px = }")
            assert (total_cxl_qty == qty), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
                 f"{qty}, found {total_cxl_qty = }")
            assert (total_cxl_notional == qty * get_px_in_usd(px)), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
                 f"{qty * get_px_in_usd(px)}, found {total_cxl_notional = }")
            assert (avg_cxl_px == px), \
                (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
                 f"{px}, found {avg_cxl_px = }")
            if side == Side.BUY:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"0, found {total_fill_exposure = }")
                assert (total_cxl_exposure == qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{qty * get_px_in_usd(px)}, found {total_cxl_exposure = }")
            else:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == buy_qty * get_px_in_usd(buy_px)), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{buy_qty * get_px_in_usd(px)}, found {total_fill_exposure = }")
                assert (total_cxl_exposure == - qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{- qty * get_px_in_usd(px)}, found {total_cxl_exposure = }")

            portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
            if side == Side.BUY:
                overall_notional = portfolio_status.overall_buy_notional
            else:
                overall_notional = portfolio_status.overall_sell_notional
            assert (overall_notional == 0), \
                (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
                 f"0, found {overall_notional = }")

            # applying ack leading to fulfill
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_unack_obj.chore.chore_id, latest_unack_obj.chore.px,
                latest_unack_obj.chore.qty, latest_unack_obj.chore.side, latest_unack_obj.chore.security.sec_id,
                latest_unack_obj.chore.underlying_account)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                              executor_http_client)

            if executor_config_dict.get("pause_fulfill_post_chore_dod"):
                assert chore_snapshot.filled_qty == 0, f"Mismatch chore_snapshot.filled_qty, expected 0, " \
                                                       f"received {chore_snapshot.filled_qty}"
                assert chore_snapshot.cxled_qty == chore_snapshot.chore_brief.qty, \
                    f"Mismatch chore_snapshot.cxled_qty: expected {chore_snapshot.chore_brief.qty}, received " \
                    f"{chore_snapshot.cxled_qty}"
                assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
                    f"Mismatch chore_snapshot.chore_status: expected ChoreStatusType.OE_DOD, " \
                    f"received {chore_snapshot.chore_status}"
            else:
                assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
                    f"Mismatched: Chore status must be OE_FILLED but found: {chore_snapshot.chore_status = }"
                assert chore_snapshot.cxled_qty == 0, \
                    (f"Mismatched: ChoreSnapshot cxled_qty must be 0, found "
                     f"{chore_snapshot.cxled_qty}")
                assert chore_snapshot.cxled_notional == 0, \
                    (f"Mismatched: ChoreSnapshot cxled_notional must be "
                     f"0, found {chore_snapshot.cxled_notional}")
                assert chore_snapshot.avg_cxled_px == 0, \
                    (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
                     f"0, found {chore_snapshot.avg_cxled_px}")
                assert chore_snapshot.filled_qty == qty, \
                    f"Mismatched: ChoreSnapshot avg_cxled_px must be {qty}, found {chore_snapshot.filled_qty}"
                assert chore_snapshot.fill_notional == qty * get_px_in_usd(px), \
                    (f"Mismatched: ChoreSnapshot fill_notional must be {qty * get_px_in_usd(px)}, "
                     f"found {chore_snapshot.fill_notional}")
                assert chore_snapshot.avg_fill_px == px, \
                    f"Mismatched: ChoreSnapshot avg_fill_px must be {px}, found {chore_snapshot.avg_fill_px}"

                symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side))
                assert len(symbol_side_snapshot_list) == 1, \
                    (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
                     f"{latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side}")

                symbol_side_snapshot = symbol_side_snapshot_list[0]
                if side == Side.BUY:
                    buy_symbol_side_snapshot = symbol_side_snapshot
                assert symbol_side_snapshot.total_qty == qty, \
                    (f"Mismatched: expected symbol_side_snapshot.total_qty: {qty}, "
                     f"found {symbol_side_snapshot.total_qty = }")
                assert symbol_side_snapshot.avg_px == px, \
                    (f"Mismatched: expected symbol_side_snapshot.avg_px: {px}, "
                     f"found {symbol_side_snapshot.avg_px = }")
                assert symbol_side_snapshot.total_filled_qty == qty, \
                    (f"Mismatched: symbol_side_snapshot.total_filled_qty must be {qty}, found "
                     f"{symbol_side_snapshot.total_filled_qty = }")
                assert symbol_side_snapshot.total_fill_notional == qty * get_px_in_usd(px), \
                    (f"Mismatched: symbol_side_snapshot.total_fill_notional must be {qty * get_px_in_usd(px)}, "
                     f"found {symbol_side_snapshot.total_fill_notional = }")
                assert symbol_side_snapshot.avg_fill_px == px, \
                    (f"Mismatched: symbol_side_snapshot.avg_fill_px must be {px}, found "
                     f"{symbol_side_snapshot.avg_fill_px = }")
                assert symbol_side_snapshot.total_cxled_qty == 0, \
                    (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be 0, found "
                     f"{symbol_side_snapshot.total_cxled_qty = }")
                assert (symbol_side_snapshot.total_cxled_notional == 0), \
                    (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
                     f"0, found {symbol_side_snapshot.total_cxled_notional = }")
                assert symbol_side_snapshot.avg_cxled_px == 0, \
                    (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be 0, found "
                     f"{symbol_side_snapshot.avg_cxled_px = }")
                assert symbol_side_snapshot.last_update_fill_px == px, \
                    (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be {px}, found "
                     f"{symbol_side_snapshot.last_update_fill_px = }")
                assert symbol_side_snapshot.last_update_fill_qty == qty, \
                    (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be {qty}, found "
                     f"{symbol_side_snapshot.last_update_fill_qty = }")

                buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
                strat_limits = executor_http_client.get_strat_limits_client(1)
                strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat.id)
                if side == Side.BUY:
                    strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
                else:
                    strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
                assert (strat_brief_bartering_brief.open_qty == 0), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
                     f"0, found {strat_brief_bartering_brief.open_qty = }")
                assert (strat_brief_bartering_brief.open_notional == 0), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
                     f"0, found {strat_brief_bartering_brief.open_notional = }")
                assert (strat_brief_bartering_brief.residual_qty == 0), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
                     f"0, found {strat_brief_bartering_brief.residual_qty = }")
                assert (strat_brief_bartering_brief.consumable_open_chores == 5), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
                     f"5, found {strat_brief_bartering_brief.consumable_open_chores = }")
                assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == 0), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
                     f"0, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
                assert (strat_brief_bartering_brief.consumable_notional == (
                        strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional)), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
                     f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional}, "
                     f"found {strat_brief_bartering_brief.consumable_notional = }")
                assert (strat_brief_bartering_brief.consumable_open_notional == strat_limits.max_open_single_leg_notional), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
                     f"{strat_limits.max_open_single_leg_notional}, "
                     f"found {strat_brief_bartering_brief.consumable_open_notional = }")
                total_security_size: int = \
                    static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
                assert (strat_brief_bartering_brief.consumable_concentration == (
                        (total_security_size / 100 * strat_limits.max_concentration) -
                        symbol_side_snapshot.total_filled_qty)), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
                     f"{(total_security_size / 100 * strat_limits.max_concentration) - symbol_side_snapshot.total_filled_qty}, "
                     f"found {strat_brief_bartering_brief.consumable_concentration = }")
                assert (strat_brief_bartering_brief.consumable_cxl_qty == (
                        (((symbol_side_snapshot.total_filled_qty +
                           symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
                        symbol_side_snapshot.total_cxled_qty)), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
                     f"{strat_limits.max_open_single_leg_notional}, "
                     f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
                other_side_residual_qty = 0
                assert (strat_brief_bartering_brief.indicative_consumable_residual == (
                        strat_limits.residual_restriction.max_residual -
                        ((strat_brief_bartering_brief.residual_qty *
                          get_px_in_usd(current_last_barter_px)) - (
                                 other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
                    (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
                     f"{strat_limits.residual_restriction.max_residual - ((strat_brief_bartering_brief.residual_qty * get_px_in_usd(current_last_barter_px)) - (other_side_residual_qty * get_px_in_usd(other_last_barter_px)))}, "
                     f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")

                if side == Side.BUY:
                    other_side_fill_notional = 0
                else:
                    other_side_fill_notional = buy_symbol_side_snapshot.total_fill_notional
                assert (strat_brief.consumable_nett_filled_notional == (
                        strat_limits.max_net_filled_notional -
                        abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
                    (
                        f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
                        f"{strat_limits.max_open_single_leg_notional}, "
                        f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

                strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
                if side == Side.BUY:
                    total_qty = strat_status.total_buy_qty
                    total_open_qty = strat_status.total_open_buy_qty
                    total_open_notional = strat_status.total_open_buy_notional
                    avg_open_px = strat_status.avg_open_buy_px
                    total_fill_qty = strat_status.total_fill_buy_qty
                    total_fill_notional = strat_status.total_fill_buy_notional
                    avg_fill_px = strat_status.avg_fill_buy_px
                    total_cxl_qty = strat_status.total_cxl_buy_qty
                    total_cxl_notional = strat_status.total_cxl_buy_notional
                    avg_cxl_px = strat_status.avg_cxl_buy_px
                else:
                    total_qty = strat_status.total_sell_qty
                    total_open_qty = strat_status.total_open_sell_qty
                    total_open_notional = strat_status.total_open_sell_notional
                    avg_open_px = strat_status.avg_open_sell_px
                    total_fill_qty = strat_status.total_fill_sell_qty
                    total_fill_notional = strat_status.total_fill_sell_notional
                    avg_fill_px = strat_status.avg_fill_sell_px
                    total_cxl_qty = strat_status.total_cxl_sell_qty
                    total_cxl_notional = strat_status.total_cxl_sell_notional
                    avg_cxl_px = strat_status.avg_cxl_sell_px

                total_open_exposure = strat_status.total_open_exposure
                total_fill_exposure = strat_status.total_fill_exposure
                total_cxl_exposure = strat_status.total_cxl_exposure
                assert total_qty == qty, \
                    (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
                     f"{qty}, found {total_qty = }")
                assert total_open_qty == 0, \
                    (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
                     f"0, found {total_open_qty = }")
                assert (total_open_notional == 0), \
                    (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
                     f"0, found {total_open_notional = }")
                assert (avg_open_px == 0), \
                    (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
                     f"0, found {avg_open_px = }")
                assert (total_fill_qty == qty), \
                    (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
                     f"{qty}, found {total_fill_qty = }")
                assert (total_fill_notional == qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
                     f"{qty * get_px_in_usd(px)}, found {total_fill_notional = }")
                assert (avg_fill_px == px), \
                    (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
                     f"{px}, found {avg_fill_px = }")
                assert (total_cxl_qty == 0), \
                    (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
                     f"0, found {total_cxl_qty = }")
                assert (total_cxl_notional == 0), \
                    (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
                     f"0, found {total_cxl_notional = }")
                assert (avg_cxl_px == 0), \
                    (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
                     f"0, found {avg_cxl_px = }")
                if side == Side.BUY:
                    assert (total_open_exposure == 0), \
                        (f"Mismatched: expected strat_status.total_open_exposure: "
                         f"0, found {total_open_exposure = }")
                    assert (total_fill_exposure == qty * get_px_in_usd(px)), \
                        (f"Mismatched: expected strat_status.total_fill_exposure: "
                         f"{qty * get_px_in_usd(px)}, found {total_fill_exposure = }")
                    assert (total_cxl_exposure == 0), \
                        (f"Mismatched: expected strat_status.total_cxl_exposure: "
                         f"0, found {total_cxl_exposure = }")
                else:
                    assert (total_open_exposure == 0), \
                        (f"Mismatched: expected strat_status.total_open_exposure: "
                         f"0, found {total_open_exposure = }")
                    assert (total_fill_exposure == (
                            buy_qty * get_px_in_usd(buy_px) - qty * get_px_in_usd(px))), \
                        (f"Mismatched: expected strat_status.total_fill_exposure: "
                         f"{buy_qty * get_px_in_usd(buy_px) - qty * get_px_in_usd(px)}, "
                         f"found {total_fill_exposure = }")
                    assert (total_cxl_exposure == 0), \
                        (f"Mismatched: expected strat_status.total_cxl_exposure: "
                         f"0, found {total_cxl_exposure = }")

                portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
                if side == Side.BUY:
                    overall_notional = portfolio_status.overall_buy_notional
                else:
                    overall_notional = portfolio_status.overall_sell_notional
                assert (overall_notional == qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
                     f"{qty * get_px_in_usd(px)}, found {overall_notional = }")

            # Checking alert in strat_alert
            time.sleep(2)
            if executor_config_dict.get("pause_fulfill_post_chore_dod"):
                check_str = ("Unexpected: Received fill that makes chore_snapshot OE_FILLED which is already of "
                             "state OE_DOD, ignoring this fill and putting this strat to PAUSE")
                time.sleep(2)

                pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
                assert pair_strat.strat_state == StratState.StratState_PAUSED, \
                    f"Mismatch: pair_strat must have strat_state PAUSED but found {pair_strat.strat_state = }"
            else:
                check_str = "Received fill that makes chore_snapshot OE_FILLED which is already of state OE_DOD"
                time.sleep(2)

            assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_overfill_post_unack_unsol_cxl(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        buy_symbol_side_snapshot = None
        buy_overfill_qty = None
        buy_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            # buy test
            overfill_qty = qty + 10  # extra to make overfill
            if side == Side.BUY:
                buy_overfill_qty = overfill_qty
                buy_px = px
            
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, chore_symbol,
                                                                              executor_http_client)
            latest_cxl_ack_obj = get_latest_chore_journal_with_events_and_symbol([ChoreEventType.OE_CXL_ACK,
                                                                                  ChoreEventType.OE_UNSOL_CXL], chore_symbol,
                                                                                 executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                              executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
                f"Mismatched: Chore status must be DOD but found: {chore_snapshot.chore_status = }"
            assert chore_snapshot.cxled_qty == latest_unack_obj.chore.qty, \
                (f"Mismatched: ChoreSnapshot cxled_qty must be {latest_unack_obj.chore.qty}, found "
                 f"{chore_snapshot.cxled_qty}")
            assert chore_snapshot.cxled_notional == qty * get_px_in_usd(px), \
                (f"Mismatched: ChoreSnapshot cxled_notional must be "
                 f"{qty * get_px_in_usd(px)}, found {chore_snapshot.cxled_notional}")
            assert chore_snapshot.avg_cxled_px == latest_unack_obj.chore.px, \
                (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
                 f"{latest_unack_obj.chore.px}, found {chore_snapshot.avg_cxled_px}")
            assert chore_snapshot.filled_qty == 0, \
                f"Mismatched: ChoreSnapshot avg_cxled_px must be 0, found {chore_snapshot.filled_qty}"
            assert chore_snapshot.fill_notional == 0, \
                f"Mismatched: ChoreSnapshot fill_notional must be 0, found {chore_snapshot.fill_notional}"
            assert chore_snapshot.avg_fill_px == 0, \
                f"Mismatched: ChoreSnapshot avg_fill_px must be 0, found {chore_snapshot.avg_fill_px}"

            symbol_side_snapshot_list = (
                executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                    latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side))
            assert len(symbol_side_snapshot_list) == 1, \
                (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
                 f"{latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side}")

            symbol_side_snapshot = symbol_side_snapshot_list[0]
            if side == Side.BUY:
                buy_symbol_side_snapshot = symbol_side_snapshot
            assert symbol_side_snapshot.total_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatched: expected symbol_side_snapshot.total_qty: {chore_snapshot.chore_brief.qty}, "
                 f"found {symbol_side_snapshot.total_qty = }")
            assert symbol_side_snapshot.avg_px == chore_snapshot.chore_brief.px, \
                (f"Mismatched: expected symbol_side_snapshot.avg_px: {chore_snapshot.chore_brief.px}, "
                 f"found {symbol_side_snapshot.avg_px = }")
            assert symbol_side_snapshot.total_filled_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.total_filled_qty must be 0, found "
                 f"{symbol_side_snapshot.total_filled_qty = }")
            assert symbol_side_snapshot.total_fill_notional == 0, \
                (f"Mismatched: symbol_side_snapshot.total_fill_notional must be 0, found "
                 f"{symbol_side_snapshot.total_fill_notional = }")
            assert symbol_side_snapshot.avg_fill_px == 0, \
                (f"Mismatched: symbol_side_snapshot.avg_fill_px must be 0, found "
                 f"{symbol_side_snapshot.avg_fill_px = }")
            assert symbol_side_snapshot.total_cxled_qty == latest_unack_obj.chore.qty, \
                (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be {latest_unack_obj.chore.qty}, found "
                 f"{symbol_side_snapshot.total_cxled_qty = }")
            assert (symbol_side_snapshot.total_cxled_notional ==
                    (latest_unack_obj.chore.qty * get_px_in_usd(latest_unack_obj.chore.px))), \
                (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
                 f"{latest_unack_obj.chore.qty * get_px_in_usd(latest_unack_obj.chore.px)}, found "
                 f"{symbol_side_snapshot.total_cxled_notional = }")
            assert symbol_side_snapshot.avg_cxled_px == latest_unack_obj.chore.px, \
                (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be {latest_unack_obj.chore.px}, found "
                 f"{symbol_side_snapshot.avg_cxled_px = }")
            assert symbol_side_snapshot.last_update_fill_px == 0, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be 0, found "
                 f"{symbol_side_snapshot.last_update_fill_px = }")
            assert symbol_side_snapshot.last_update_fill_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be 0, found "
                 f"{symbol_side_snapshot.last_update_fill_qty = }")

            buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
            strat_limits = executor_http_client.get_strat_limits_client(1)
            strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat.id)
            if side == Side.BUY:
                strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
            else:
                strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
            assert (strat_brief_bartering_brief.open_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
                 f"0, found {strat_brief_bartering_brief.open_qty = }")
            assert (strat_brief_bartering_brief.open_notional == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
                 f"0, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.residual_qty == chore_snapshot.cxled_qty), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
                 f"{chore_snapshot.cxled_qty}, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_chores == 5), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
                 f"5, found {strat_brief_bartering_brief.consumable_open_chores = }")
            assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == chore_snapshot.cxled_qty), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
                 f"{chore_snapshot.cxled_qty}, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
            assert (strat_brief_bartering_brief.consumable_notional == (
                    strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
                 f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_notional == strat_limits.max_open_single_leg_notional), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_open_notional = }")
            total_security_size: int = \
                static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
            assert (strat_brief_bartering_brief.consumable_concentration == (
                    (total_security_size / 100 * strat_limits.max_concentration) -
                    symbol_side_snapshot.total_filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
                 f"{(total_security_size / 100 * strat_limits.max_concentration) - symbol_side_snapshot.total_filled_qty}, "
                 f"found {strat_brief_bartering_brief.consumable_concentration = }")
            assert (strat_brief_bartering_brief.consumable_cxl_qty == (
                    (((symbol_side_snapshot.total_filled_qty +
                       symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
                    symbol_side_snapshot.total_cxled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
            other_side_residual_qty = 0
            if side == Side.BUY:
                current_last_barter_px = buy_last_barter_px
                other_last_barter_px = sell_last_barter_px
            else:
                current_last_barter_px = sell_last_barter_px
                other_last_barter_px = buy_last_barter_px
            assert (strat_brief_bartering_brief.indicative_consumable_residual == (
                    strat_limits.residual_restriction.max_residual -
                    ((strat_brief_bartering_brief.residual_qty *
                      get_px_in_usd(current_last_barter_px)) - (
                            other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
                 f"{strat_limits.residual_restriction.max_residual - ((strat_brief_bartering_brief.residual_qty * get_px_in_usd(current_last_barter_px)) - (other_side_residual_qty * get_px_in_usd(other_last_barter_px)))}, "
                 f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")

            if side == Side.BUY:
                other_side_fill_notional = 0
            else:
                other_side_fill_notional = buy_symbol_side_snapshot.total_fill_notional
            assert (strat_brief.consumable_nett_filled_notional == (
                    strat_limits.max_net_filled_notional -
                    abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            if side == Side.BUY:
                total_qty = strat_status.total_buy_qty
                total_open_qty = strat_status.total_open_buy_qty
                total_open_notional = strat_status.total_open_buy_notional
                avg_open_px = strat_status.avg_open_buy_px
                total_fill_qty = strat_status.total_fill_buy_qty
                total_fill_notional = strat_status.total_fill_buy_notional
                avg_fill_px = strat_status.avg_fill_buy_px
                total_cxl_qty = strat_status.total_cxl_buy_qty
                total_cxl_notional = strat_status.total_cxl_buy_notional
                avg_cxl_px = strat_status.avg_cxl_buy_px
            else:
                total_qty = strat_status.total_sell_qty
                total_open_qty = strat_status.total_open_sell_qty
                total_open_notional = strat_status.total_open_sell_notional
                avg_open_px = strat_status.avg_open_sell_px
                total_fill_qty = strat_status.total_fill_sell_qty
                total_fill_notional = strat_status.total_fill_sell_notional
                avg_fill_px = strat_status.avg_fill_sell_px
                total_cxl_qty = strat_status.total_cxl_sell_qty
                total_cxl_notional = strat_status.total_cxl_sell_notional
                avg_cxl_px = strat_status.avg_cxl_sell_px

            total_open_exposure = strat_status.total_open_exposure
            total_fill_exposure = strat_status.total_fill_exposure
            total_cxl_exposure = strat_status.total_cxl_exposure
            assert total_qty == chore_snapshot.chore_brief.qty, \
                (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
                 f"{chore_snapshot.chore_brief.qty}, found {total_qty = }")
            assert total_open_qty == 0, \
                (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
                 f"0, found {total_open_qty = }")
            assert (total_open_notional == 0), \
                (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
                 f"0, found {total_open_notional = }")
            assert (avg_open_px == 0), \
                (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
                 f"0, found {avg_open_px = }")
            assert (total_fill_qty == 0), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
                 f"0, found {total_fill_qty = }")
            assert (total_fill_notional == 0), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
                 f"0, found {total_fill_notional = }")
            assert (avg_fill_px == 0), \
                (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
                 f"0, found {avg_fill_px = }")
            assert (total_cxl_qty == qty), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
                 f"{qty}, found {total_cxl_qty = }")
            assert (total_cxl_notional == qty * get_px_in_usd(px)), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
                 f"{qty * get_px_in_usd(px)}, found {total_cxl_notional = }")
            assert (avg_cxl_px == px), \
                (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
                 f"{px}, found {avg_cxl_px = }")
            if side == Side.BUY:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"0, found {total_fill_exposure = }")
                assert (total_cxl_exposure == qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{qty * get_px_in_usd(px)}, found {total_cxl_exposure = }")
            else:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == buy_overfill_qty * get_px_in_usd(buy_px)), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{buy_overfill_qty * get_px_in_usd(px)}, found {total_fill_exposure = }")
                assert (total_cxl_exposure == - qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"{- qty * get_px_in_usd(px)}, found {total_cxl_exposure = }")

            portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
            if side == Side.BUY:
                overall_notional = portfolio_status.overall_buy_notional
            else:
                overall_notional = portfolio_status.overall_sell_notional
            assert (overall_notional == 0), \
                (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
                 f"0, found {overall_notional = }")

            # applying ack leading to overfill
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_unack_obj.chore.chore_id, latest_unack_obj.chore.px, overfill_qty,
                latest_unack_obj.chore.side, latest_unack_obj.chore.security.sec_id,
                latest_unack_obj.chore.underlying_account, use_exact_passed_qty=True)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                              executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED, \
                f"Mismatched: Chore status must be OE_OVER_FILLED but found: {chore_snapshot.chore_status = }"
            assert chore_snapshot.cxled_qty == 0, \
                (f"Mismatched: ChoreSnapshot cxled_qty must be 0, found "
                 f"{chore_snapshot.cxled_qty}")
            assert chore_snapshot.cxled_notional == 0, \
                (f"Mismatched: ChoreSnapshot cxled_notional must be "
                 f"0, found {chore_snapshot.cxled_notional}")
            assert chore_snapshot.avg_cxled_px == 0, \
                (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
                 f"0, found {chore_snapshot.avg_cxled_px}")
            assert chore_snapshot.filled_qty == overfill_qty, \
                f"Mismatched: ChoreSnapshot avg_cxled_px must be {overfill_qty}, found {chore_snapshot.filled_qty}"
            assert chore_snapshot.fill_notional == overfill_qty * get_px_in_usd(px), \
                (f"Mismatched: ChoreSnapshot fill_notional must be {overfill_qty * get_px_in_usd(px)}, "
                 f"found {chore_snapshot.fill_notional}")
            assert chore_snapshot.avg_fill_px == px, \
                f"Mismatched: ChoreSnapshot avg_fill_px must be {px}, found {chore_snapshot.avg_fill_px}"

            symbol_side_snapshot_list = (
                executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                    latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side))
            assert len(symbol_side_snapshot_list) == 1, \
                (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
                 f"{latest_unack_obj.chore.security.sec_id, latest_unack_obj.chore.side}")

            symbol_side_snapshot = symbol_side_snapshot_list[0]
            if side == Side.BUY:
                buy_symbol_side_snapshot = symbol_side_snapshot
            assert symbol_side_snapshot.total_qty == qty, \
                (f"Mismatched: expected symbol_side_snapshot.total_qty: {qty}, "
                 f"found {symbol_side_snapshot.total_qty = }")
            assert symbol_side_snapshot.avg_px == px, \
                (f"Mismatched: expected symbol_side_snapshot.avg_px: {px}, "
                 f"found {symbol_side_snapshot.avg_px = }")
            assert symbol_side_snapshot.total_filled_qty == overfill_qty, \
                (f"Mismatched: symbol_side_snapshot.total_filled_qty must be {overfill_qty}, found "
                 f"{symbol_side_snapshot.total_filled_qty = }")
            assert symbol_side_snapshot.total_fill_notional == overfill_qty * get_px_in_usd(px), \
                (f"Mismatched: symbol_side_snapshot.total_fill_notional must be {overfill_qty * get_px_in_usd(px)}, "
                 f"found {symbol_side_snapshot.total_fill_notional = }")
            assert symbol_side_snapshot.avg_fill_px == px, \
                (f"Mismatched: symbol_side_snapshot.avg_fill_px must be {px}, found "
                 f"{symbol_side_snapshot.avg_fill_px = }")
            assert symbol_side_snapshot.total_cxled_qty == 0, \
                (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be 0, found "
                 f"{symbol_side_snapshot.total_cxled_qty = }")
            assert (symbol_side_snapshot.total_cxled_notional == 0), \
                (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
                 f"0, found {symbol_side_snapshot.total_cxled_notional = }")
            assert symbol_side_snapshot.avg_cxled_px == 0, \
                (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be 0, found "
                 f"{symbol_side_snapshot.avg_cxled_px = }")
            assert symbol_side_snapshot.last_update_fill_px == px, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be {px}, found "
                 f"{symbol_side_snapshot.last_update_fill_px = }")
            assert symbol_side_snapshot.last_update_fill_qty == overfill_qty, \
                (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be {overfill_qty}, found "
                 f"{symbol_side_snapshot.last_update_fill_qty = }")

            buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
            strat_limits = executor_http_client.get_strat_limits_client(1)
            strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat.id)
            if side == Side.BUY:
                strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
            else:
                strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
            assert (strat_brief_bartering_brief.open_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
                 f"0, found {strat_brief_bartering_brief.open_qty = }")
            assert (strat_brief_bartering_brief.open_notional == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
                 f"0, found {strat_brief_bartering_brief.open_notional = }")
            assert (strat_brief_bartering_brief.residual_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
                 f"0, found {strat_brief_bartering_brief.residual_qty = }")
            assert (strat_brief_bartering_brief.consumable_open_chores == 5), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
                 f"5, found {strat_brief_bartering_brief.consumable_open_chores = }")
            assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == 0), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
                 f"0, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
            assert (strat_brief_bartering_brief.consumable_notional == (
                    strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
                 f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_notional = }")
            assert (strat_brief_bartering_brief.consumable_open_notional == strat_limits.max_open_single_leg_notional), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_open_notional = }")
            total_security_size: int = \
                static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
            assert (strat_brief_bartering_brief.consumable_concentration == (
                    (total_security_size / 100 * strat_limits.max_concentration) -
                    symbol_side_snapshot.total_filled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
                 f"{(total_security_size / 100 * strat_limits.max_concentration) - symbol_side_snapshot.total_filled_qty}, "
                 f"found {strat_brief_bartering_brief.consumable_concentration = }")
            assert (strat_brief_bartering_brief.consumable_cxl_qty == (
                    (((symbol_side_snapshot.total_filled_qty +
                       symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
                    symbol_side_snapshot.total_cxled_qty)), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
                 f"{strat_limits.max_open_single_leg_notional}, "
                 f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
            other_side_residual_qty = 0
            assert (strat_brief_bartering_brief.indicative_consumable_residual == (
                    strat_limits.residual_restriction.max_residual -
                    ((strat_brief_bartering_brief.residual_qty *
                      get_px_in_usd(current_last_barter_px)) - (
                             other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
                (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
                 f"{strat_limits.residual_restriction.max_residual - ((strat_brief_bartering_brief.residual_qty * get_px_in_usd(current_last_barter_px)) - (other_side_residual_qty * get_px_in_usd(other_last_barter_px)))}, "
                 f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")

            if side == Side.BUY:
                other_side_fill_notional = 0
            else:
                other_side_fill_notional = buy_symbol_side_snapshot.total_fill_notional
            assert (strat_brief.consumable_nett_filled_notional == (
                    strat_limits.max_net_filled_notional -
                    abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
                (
                    f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
                    f"{strat_limits.max_open_single_leg_notional}, "
                    f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            if side == Side.BUY:
                total_qty = strat_status.total_buy_qty
                total_open_qty = strat_status.total_open_buy_qty
                total_open_notional = strat_status.total_open_buy_notional
                avg_open_px = strat_status.avg_open_buy_px
                total_fill_qty = strat_status.total_fill_buy_qty
                total_fill_notional = strat_status.total_fill_buy_notional
                avg_fill_px = strat_status.avg_fill_buy_px
                total_cxl_qty = strat_status.total_cxl_buy_qty
                total_cxl_notional = strat_status.total_cxl_buy_notional
                avg_cxl_px = strat_status.avg_cxl_buy_px
            else:
                total_qty = strat_status.total_sell_qty
                total_open_qty = strat_status.total_open_sell_qty
                total_open_notional = strat_status.total_open_sell_notional
                avg_open_px = strat_status.avg_open_sell_px
                total_fill_qty = strat_status.total_fill_sell_qty
                total_fill_notional = strat_status.total_fill_sell_notional
                avg_fill_px = strat_status.avg_fill_sell_px
                total_cxl_qty = strat_status.total_cxl_sell_qty
                total_cxl_notional = strat_status.total_cxl_sell_notional
                avg_cxl_px = strat_status.avg_cxl_sell_px

            total_open_exposure = strat_status.total_open_exposure
            total_fill_exposure = strat_status.total_fill_exposure
            total_cxl_exposure = strat_status.total_cxl_exposure
            assert total_qty == qty, \
                (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
                 f"{qty}, found {total_qty = }")
            assert total_open_qty == 0, \
                (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
                 f"0, found {total_open_qty = }")
            assert (total_open_notional == 0), \
                (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
                 f"0, found {total_open_notional = }")
            assert (avg_open_px == 0), \
                (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
                 f"0, found {avg_open_px = }")
            assert (total_fill_qty == overfill_qty), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
                 f"{overfill_qty}, found {total_fill_qty = }")
            assert (total_fill_notional == overfill_qty * get_px_in_usd(px)), \
                (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
                 f"{overfill_qty * get_px_in_usd(px)}, found {total_fill_notional = }")
            assert (avg_fill_px == px), \
                (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
                 f"{px}, found {avg_fill_px = }")
            assert (total_cxl_qty == 0), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
                 f"0, found {total_cxl_qty = }")
            assert (total_cxl_notional == 0), \
                (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
                 f"0, found {total_cxl_notional = }")
            assert (avg_cxl_px == 0), \
                (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
                 f"0, found {avg_cxl_px = }")
            if side == Side.BUY:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == overfill_qty * get_px_in_usd(px)), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{overfill_qty * get_px_in_usd(px)}, found {total_fill_exposure = }")
                assert (total_cxl_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"0, found {total_cxl_exposure = }")
            else:
                assert (total_open_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_open_exposure: "
                     f"0, found {total_open_exposure = }")
                assert (total_fill_exposure == (
                        buy_overfill_qty * get_px_in_usd(buy_px) - overfill_qty * get_px_in_usd(px))), \
                    (f"Mismatched: expected strat_status.total_fill_exposure: "
                     f"{buy_overfill_qty * get_px_in_usd(buy_px) - overfill_qty * get_px_in_usd(px)}, "
                     f"found {total_fill_exposure = }")
                assert (total_cxl_exposure == 0), \
                    (f"Mismatched: expected strat_status.total_cxl_exposure: "
                     f"0, found {total_cxl_exposure = }")

            portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
            if side == Side.BUY:
                overall_notional = portfolio_status.overall_buy_notional
            else:
                overall_notional = portfolio_status.overall_sell_notional
            assert (overall_notional == overfill_qty * get_px_in_usd(px)), \
                (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
                 f"{overfill_qty * get_px_in_usd(px)}, found {overall_notional = }")

            # Checking alert in strat_alert
            check_str = "Unexpected: Received fill that will make chore_snapshot OVER_FILLED which is already OE_DOD"
            assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
            time.sleep(5)
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # forcefully turning strat to active again for checking sell chore
            if side == Side.BUY:
                pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
                pair_strat.strat_state = StratState.StratState_ACTIVE
                email_book_service_native_web_client.put_pair_strat_client(pair_strat)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_fill_pre_chore_ack(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_avoid_fill_after_ack"] = True
            config_dict["symbol_configs"][symbol]["simulate_fills_pre_chore_ack"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                          executor_http_client)

        check_str = ("Received fill for chore that has status: ChoreStatusType.OE_UNACK, "
                     "putting chore to ChoreStatusType.OE_ACKED status and applying fill")
        assert_fail_msg = f"can't find alert saying {check_str!r}"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        fills_journal_list: List[FillsJournalBaseModel] = (
            get_fill_journals_for_chore_id(latest_unack_obj.chore.chore_id, executor_http_client))
        chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                          executor_http_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_ACKED, \
            f"Mismatched: Chore status must be OE_ACKED but found: {chore_snapshot.chore_status = }"
        assert chore_snapshot.filled_qty == fills_journal_list[0].fill_qty, \
            (f"Mismatch chore_snapshot.filled_qty, expected {fills_journal_list[0].fill_qty}, "
             f"received {chore_snapshot.filled_qty}")

        # applying ack post fills received
        executor_http_client.barter_simulator_process_chore_ack_query_client(
            latest_unack_obj.chore.chore_id,
            latest_unack_obj.chore.px,
            latest_unack_obj.chore.qty,
            latest_unack_obj.chore.side,
            latest_unack_obj.chore.security.sec_id,
            latest_unack_obj.chore.underlying_account)

        check_str = ("Unexpected: Received chore_journal of event: ChoreEventType.OE_ACK on chore of "
                     "chore_snapshot status: ChoreStatusType.OE_ACKED")
        assert_fail_msg = f"can't find alert saying {check_str!r}"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_fulfill_pre_chore_ack(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_avoid_fill_after_ack"] = True
            config_dict["symbol_configs"][symbol]["simulate_fills_pre_chore_ack"] = True
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                          executor_http_client)

        check_str = ("Received fill for chore that has status: ChoreStatusType.OE_UNACK that makes chore fulfilled, "
                     "putting chore to ChoreStatusType.OE_FILLED status and applying fill")
        assert_fail_msg = f"can't find alert saying {check_str!r}"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        fills_journal_list: List[FillsJournalBaseModel] = (
            get_fill_journals_for_chore_id(latest_unack_obj.chore.chore_id, executor_http_client))
        chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                          executor_http_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
            f"Mismatched: Chore status must be OE_FILLED but found: {chore_snapshot.chore_status = }"
        assert chore_snapshot.filled_qty == fills_journal_list[0].fill_qty, \
            (f"Mismatch chore_snapshot.filled_qty, expected {fills_journal_list[0].fill_qty}, "
             f"received {chore_snapshot.filled_qty}")

        # applying ack post fills received
        executor_http_client.barter_simulator_process_chore_ack_query_client(
            latest_unack_obj.chore.chore_id,
            latest_unack_obj.chore.px,
            latest_unack_obj.chore.qty,
            latest_unack_obj.chore.side,
            latest_unack_obj.chore.security.sec_id,
            latest_unack_obj.chore.underlying_account)

        check_str = ("Unexpected: Received chore_journal of event: ChoreEventType.OE_ACK on chore of "
                     "chore_snapshot status: ChoreStatusType.OE_FILLED")
        assert_fail_msg = f"can't find alert saying {check_str!r}"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_overfill_pre_chore_ack(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = False

        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)

        latest_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                          executor_http_client)
        overfill_qty = qty + 10
        executor_http_client.barter_simulator_process_fill_query_client(
            latest_unack_obj.chore.chore_id, latest_unack_obj.chore.px, overfill_qty, Side.BUY, buy_symbol,
            latest_unack_obj.chore.underlying_account, use_exact_passed_qty=True)

        fills_journal_list: List[FillsJournalBaseModel] = (
            get_fill_journals_for_chore_id(latest_unack_obj.chore.chore_id, executor_http_client))
        chore_snapshot = get_chore_snapshot_from_chore_id(latest_unack_obj.chore.chore_id,
                                                          executor_http_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED, \
            f"Mismatched: Chore status must be OE_OVER_FILLED but found: {chore_snapshot.chore_status = }"
        assert chore_snapshot.filled_qty == overfill_qty, \
            (f"Mismatch chore_snapshot.filled_qty, expected {fills_journal_list[0].fill_qty}, "
             f"received {chore_snapshot.filled_qty}")

        pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Mismatched: pair_strat status must be PAUSED but found {pair_strat.strat_state}"

        check_str = ("Unexpected: Received fill that will make chore_snapshot OVER_FILLED to chore "
                     "which is still OE_UNACK")
        assert_fail_msg = f"can't find alert saying {check_str!r}"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

        # applying ack post fills received
        executor_http_client.barter_simulator_process_chore_ack_query_client(
            latest_unack_obj.chore.chore_id,
            latest_unack_obj.chore.px,
            latest_unack_obj.chore.qty,
            latest_unack_obj.chore.side,
            latest_unack_obj.chore.security.sec_id,
            latest_unack_obj.chore.underlying_account)

        check_str = ("Unexpected: Received chore_journal of event: ChoreEventType.OE_ACK on chore of chore_snapshot "
                     "status: ChoreStatusType.OE_OVER_FILLED")
        assert_fail_msg = f"can't find alert saying {check_str!r}"
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# strat pause tests
@pytest.mark.nightly
def test_strat_pause_on_residual_notional_breach(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                 pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                 buy_chore_, sell_chore_,
                                                 refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.max_residual = 0
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_barter_fixture_list, market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        residual_qty = 10
        executor_http_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)

        # placing new non-systematic new_chore
        px = 100
        qty = 90
        check_str = "residual_notional = .* > max_residual"
        assert_fail_message = "Could not find any alert containing message to block chores " \
                              "due to residual notional breach"
        # placing new non-systematic new_chore
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)
        print(f"symbol: {buy_symbol}, Created new_chore obj")

        new_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_NEW, buy_symbol,
                                                                           executor_http_client)
        time.sleep(5)
        check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_message)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_pause_on_less_buy_consumable_cxl_qty_without_fill(static_data_, clean_and_set_limits,
                                                                 leg1_leg2_symbol_list,
                                                                 pair_strat_, expected_strat_limits_,
                                                                 expected_strat_status_, symbol_overview_obj_list,
                                                                 last_barter_fixture_list, market_depth_basemodel_list,
                                                                 buy_chore_, sell_chore_,
                                                                 refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_chores to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_chores = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 1
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_barter_fixture_list,
            Side.BUY, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_pause_on_less_sell_consumable_cxl_qty_without_fill(static_data_, clean_and_set_limits,
                                                                  leg1_leg2_symbol_list,
                                                                  pair_strat_, expected_strat_limits_,
                                                                  expected_strat_status_, symbol_overview_obj_list,
                                                                  last_barter_fixture_list, market_depth_basemodel_list,
                                                                  buy_chore_, sell_chore_,
                                                                  refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_chores to 0 for this test case
    expected_strat_limits_.cancel_rate.waived_min_chores = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 1
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, leg1_side=Side.SELL,
                                           leg2_side=Side.BUY))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_chores"] = True
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_barter_fixture_list,
            Side.SELL, executor_http_client, leg1_side=Side.SELL, leg2_side=Side.BUY)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_pause_on_less_buy_consumable_cxl_qty_with_fill(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                                              pair_strat_, expected_strat_limits_,
                                                              expected_strat_status_, symbol_overview_obj_list,
                                                              last_barter_fixture_list, market_depth_basemodel_list,
                                                              buy_chore_, sell_chore_,
                                                              refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_chores to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_chores = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 19
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 80
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_barter_fixture_list,
            Side.BUY, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_strat_pause_on_less_sell_consumable_cxl_qty_with_fill(static_data_, clean_and_set_limits,
                                                               leg1_leg2_symbol_list,
                                                               pair_strat_, expected_strat_limits_,
                                                               expected_strat_status_, symbol_overview_obj_list,
                                                               last_barter_fixture_list, market_depth_basemodel_list,
                                                               buy_chore_, sell_chore_,
                                                               refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_chores to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_chores = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 19
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, leg1_side=Side.SELL,
                                           leg2_side=Side.BUY))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 80
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_barter_fixture_list,
            Side.SELL, executor_http_client, leg1_side=Side.SELL,
            leg2_side=Side.BUY)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_alert_agg_sequence(clean_and_set_limits, sample_alert):
    portfolio_alerts = log_book_web_client.get_all_portfolio_alert_client()

    sev = [Severity.Severity_CRITICAL, Severity.Severity_ERROR, Severity.Severity_WARNING,
           Severity.Severity_INFO, Severity.Severity_DEBUG]
    counter = 0
    for i in range(5):
        alert = PortfolioAlertBaseModel()
        alert.last_update_analyzer_time = DateTime.utcnow()
        alert.alert_brief = f"Sample Alert: {i + 1}"
        alert.severity = sev[counter]
        counter += 1
        if counter > 4:
            counter = 0

        portfolio_alerts.append(alert)
        log_book_web_client.handle_portfolio_alerts_from_tail_executor_query_client(
            [{"severity": alert.severity, "alert_brief": alert.alert_brief,
              "alert_details": alert.alert_details}])

    # sorting alert list for this test comparison
    portfolio_alerts.sort(key=lambda x: x.last_update_analyzer_time, reverse=False)

    sorted_alert_list: List[PortfolioAlertBaseModel] = []
    for sev in Severity:
        if sev.value != Severity.Severity_UNSPECIFIED:
            for alert in portfolio_alerts:
                if alert.severity == sev.value:
                    sorted_alert_list.append(alert)
    time.sleep(5)
    agg_sorted_alerts: List[PortfolioAlertBaseModel] = log_book_web_client.get_all_portfolio_alert_client()
    for alert in agg_sorted_alerts:
        alert.last_update_analyzer_time = pendulum.parse(str(alert.last_update_analyzer_time)).in_timezone("utc")
    for alert in portfolio_alerts:
        alert.last_update_analyzer_time = \
            alert.last_update_analyzer_time.replace(microsecond=
                                                int(str(alert.last_update_analyzer_time.microsecond)[:3] + "000"))

    for sorted_alert, expected_alert in zip(agg_sorted_alerts, sorted_alert_list):
        assert sorted_alert.alert_brief == expected_alert.alert_brief, \
            (f"Alert ID mismatch: expected alert_brief {expected_alert.alert_brief!r}, "
             f"received {sorted_alert.alert_brief!r}")


# def test_alert_id(clean_and_set_limits, sample_alert):
#     alert_list = []
#
#     for i in range(1000):
#         alert = copy.deepcopy(sample_alert)
#         alert.id = f"obj_{i}"
#         alert.last_update_date_time = DateTime.utcnow()
#
#         alert_list.append(alert)
#         portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
#         json_obj = jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True)
#         updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(json_obj)
#
#     portfolio_alert = log_book_web_client.get_portfolio_alert_client(portfolio_alert_id=1)
#     agg_sorted_alerts: List[Alert] = portfolio_alert.alerts
#     # for alert in agg_sorted_alerts:
#     #     alert.last_update_date_time = pendulum.parse(str(alert.last_update_date_time)).in_timezone("utc")
#     # for alert in alert_list:
#     #     alert.last_update_date_time = \
#     #         alert.last_update_date_time.replace(microsecond=
#     #                                             int(str(alert.last_update_date_time.microsecond)[:3] + "000"))
#     # for sorted_alert, expected_alert in zip(agg_sorted_alerts, list(reversed(sorted_alert_list))):
#     #     assert sorted_alert.id == expected_alert.id, \
#     #         f"Alert ID mismatch: expected Alert {expected_alert.id}, received {sorted_alert.id}"
#     #     assert sorted_alert.last_update_date_time == expected_alert.last_update_date_time, \
#     #         f"Alert Datetime mismatch: expected Alert {expected_alert}, received {sorted_alert}"
#
#     alert_id_dict = {}
#     for alert in agg_sorted_alerts:
#         if alert.id in alert_id_dict:
#             assert False, (f"alert id already exists in dict, existing obj: {alert_id_dict[alert.id]}, "
#                            f"new obj: {alert}")
#         alert_id_dict[alert.id] = alert



# @@@ Deprecated test function: Kept here for code sample for any future use-case
# def test_routes_performance():
#     latest_file_date_time_format = "YYYYMMDD"
#     older_file_date_time_format = "YYYYMMDD.HHmmss"
#     log_dir_path = PurePath(__file__).parent.parent.parent.parent.parent / "Flux" / \
#                    "CodeGenProjects" / "phone_book" / "log"
#     files_list = os.listdir(log_dir_path)
#
#     filtered_beanie_latest_log_file_list = []
#     filtered_beanie_older_log_file_list = []
#     for file in files_list:
#         if re.match(".*_beanie_logs_.*", file):
#             if re.match(".*log$", file):
#                 filtered_beanie_latest_log_file_list.append(file)
#             else:
#                 filtered_beanie_older_log_file_list.append(file)
#
#     # getting latest 2 logs
#     latest_file: str | None = None
#     sec_latest_file: str | None = None
#     for file in filtered_beanie_latest_log_file_list:
#         # First getting latest log
#         # Also setting last log other than latest as sec_latest_file
#         if latest_file is None:
#             latest_file = file
#         else:
#             latest_file_name = latest_file.split(".")[0]
#             latest_file_date_time = pendulum.from_format(
#                 latest_file_name[len(latest_file_name)-len(latest_file_date_time_format):],
#                 fmt=latest_file_date_time_format
#             )
#
#             current_file_name = file.split(".")[0]
#             current_file_date_time = pendulum.from_format(
#                 current_file_name[len(current_file_name) - len(latest_file_date_time_format):],
#                 fmt=latest_file_date_time_format
#             )
#
#             if current_file_date_time > latest_file_date_time:
#                 sec_latest_file = latest_file
#                 latest_file = file
#
#     # If other log is present having .log.YYYYMMDD.HHmmss format with same data then taking
#     # latest log in this category as sec_latest_file
#     if any(latest_file in older_file for older_file in filtered_beanie_older_log_file_list):
#         sec_latest_file = None
#         for file in filtered_beanie_older_log_file_list:
#             if sec_latest_file is None:
#                 sec_latest_file = file
#             else:
#                 sec_latest_file_date_time = pendulum.from_format(
#                     sec_latest_file[len(sec_latest_file) - len(older_file_date_time_format):],
#                     fmt=older_file_date_time_format
#                 )
#
#                 current_file_date_time = pendulum.from_format(
#                     file[len(file) - len(older_file_date_time_format):],
#                     fmt=older_file_date_time_format
#                 )
#
#                 if current_file_date_time > sec_latest_file_date_time:
#                     sec_latest_file = file
#
#     # taking all grep found statements in log matching pattern
#     pattern = "_Callable_"
#     latest_file_content_list: List[str] = []
#     # grep in latest file
#     if latest_file:
#         latest_file_path = log_dir_path / latest_file
#         grep_cmd = pexpect.spawn(f"grep {pattern} {latest_file_path}")
#         for line in grep_cmd:
#             latest_file_content_list.append(line.decode())
#
#     sec_latest_file_content_list: List[str] = []
#     # grep in sec_latest file if exists
#     if sec_latest_file:
#         sec_latest_file_path = log_dir_path / sec_latest_file
#         grep_cmd = pexpect.spawn(f"grep {pattern} {sec_latest_file_path}")
#         for line in grep_cmd:
#             sec_latest_file_content_list.append(line.decode())
#
#     # getting set of callables to be checked in latest and last log file
#     callable_name_set = set()
#     for line in latest_file_content_list:
#         line_space_separated = line.split(" ")
#         callable_name = line_space_separated[line_space_separated.index(pattern)+1]
#         callable_name_set.add(callable_name)
#
#     # processing statement found having particular callable and getting list of all callable
#     # durations and showing average of it in report
#     for callable_name in callable_name_set:
#         callable_time_delta_list = []
#         callable_pattern = f".*{pattern} {callable_name}.*"
#         for line in latest_file_content_list:
#             if re.match(callable_pattern, line):
#                 line_space_separated = line.split(" ")
#                 time_delta = line_space_separated[line_space_separated.index(pattern)+3]
#                 callable_time_delta_list.append(parse_to_float(time_delta))
#         latest_avg_delta = np.mean(callable_time_delta_list)
#         print(f"Avg duration of callable {callable_name} in latest run: {latest_avg_delta:.7f}")
#
#         # if sec_latest_file exists, processing statement found having particular callable and
#         # getting list of all callable durations and showing average of it in report and
#         # showing delta between latest and last callable duration average
#         callable_time_delta_list = []
#         for line in sec_latest_file_content_list:
#             if re.match(callable_pattern, line):
#                 line_space_separated = line.split(" ")
#                 time_delta = line_space_separated[line_space_separated.index(pattern) + 3]
#                 callable_time_delta_list.append(parse_to_float(time_delta))
#         if callable_time_delta_list:
#             sec_latest_avg_delta = np.mean(callable_time_delta_list)
#             print(f"Avg duration of callable {callable_name} in last run: {sec_latest_avg_delta:.7f}")
#             print(f"Delta between last run and latest run for callable {callable_name}: "
#                   f"{(sec_latest_avg_delta-latest_avg_delta):.7f}")


# @@@@ deprecated test: No use case for projection in street_book or phone_book
# def test_projection_http_query(clean_and_set_limits, bar_data_):
#     for index, symbol_n_exch_id_tuple in enumerate([("CB_Sec_1", "Exch1"), ("CB_Sec_2", "Exch2")]):
#         created_objs: List[BarDataBaseModel] = []
#         symbol, exch_id = symbol_n_exch_id_tuple
#         for i in range(5*index, 5*(index+1)):
#             bar_data = BarDataBaseModel(**bar_data_)
#             bar_data.symbol_n_exch_id.symbol = symbol
#             bar_data.symbol_n_exch_id.exch_id = exch_id
#             time.sleep(1)
#             bar_data.start_time = DateTime.utcnow()
#             bar_data.id = i
#
#             created_obj = mobile_book_web_client.create_bar_data_client(bar_data)
#             created_objs.append(created_obj)
#
#         # checking query with diff params
#         received_container_obj_list: List[BarDataProjectionContainerForVwap]
#
#         # when no start and end time
#         for start_time, end_time in [(None, None), (created_objs[0].start_time, None),
#                                      (None, created_objs[-1].start_time),
#                                      (created_objs[0].start_time, created_objs[-1].start_time)]:
#             received_container_obj_list = (
#                 mobile_book_web_client.get_vwap_projection_from_bar_data_query_client(symbol, exch_id,
#                                                                                       start_time, end_time))
#             container_obj = received_container_obj_list[0]
#
#             # meta data field
#             assert container_obj.symbol_n_exch_id.symbol == symbol, \
#                 (f"Mismatched: nested meta field value, expected: {symbol}, "
#                  f"original: {container_obj.symbol_n_exch_id.symbol}")
#             assert container_obj.symbol_n_exch_id.exch_id == exch_id, \
#                 (f"Mismatched: nested meta field value, expected: {exch_id}, "
#                  f"original: {container_obj.symbol_n_exch_id.exch_id}")
#
#             # projection models
#             if not start_time and not end_time:
#                 assert len(container_obj.projection_models) == len(created_objs), \
#                     (f"Mismatched: Expected len of projection_models in container mismatched from original, "
#                      f"expected: {len(created_objs)}, original: {len(received_container_obj_list)}")
#             elif start_time and end_time:
#                 assert len(container_obj.projection_models) == len(created_objs)-2, \
#                     (f"Mismatched: Expected len of projection_models in container mismatched from original, "
#                      f"expected: {len(created_objs)-2}, original: {len(received_container_obj_list)}")
#                 for projection_model in container_obj.projection_models:
#                     assert (projection_model.start_time > start_time)
#                     assert (projection_model.start_time < end_time)
#             else:
#                 assert len(container_obj.projection_models) == len(created_objs) - 1, \
#                     (f"Mismatched: Expected len of projection_models in container mismatched from original, "
#                      f"expected: {len(created_objs) - 1}, original: {len(received_container_obj_list)}")
#                 for projection_model in container_obj.projection_models:
#                     if start_time and not end_time:
#                         assert (projection_model.start_time > start_time)
#                     else:
#                         assert (projection_model.start_time < end_time)


@pytest.mark.nightly
def test_get_max_id_query(clean_and_set_limits):
    chore_limits_max_id = email_book_service_native_web_client.get_chore_limits_max_id_client()
    assert chore_limits_max_id.max_id_val == 1, f"max_id mismatch, expected 1 received {chore_limits_max_id.max_id_val}"

    chore_limits_basemodel = ChoreLimitsBaseModel(_id=2)
    created_chore_limits_obj = email_book_service_native_web_client.create_chore_limits_client(chore_limits_basemodel)

    chore_limits_max_id = email_book_service_native_web_client.get_chore_limits_max_id_client()
    assert chore_limits_max_id.max_id_val == created_chore_limits_obj.id, \
        f"max_id mismatch, expected {created_chore_limits_obj.id} received {chore_limits_max_id.max_id_val}"


@pytest.mark.nightly
def test_get_market_depths_query(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, last_barter_fixture_list, refresh_sec_update_fixture):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]

    pair_strat_n_http_client_tuple_list = []
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        activated_pair_start, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))

        pair_strat_n_http_client_tuple_list.append((activated_pair_start, executor_http_client))

    bid_pos_to_market_depth_dict = {}
    ask_pos_to_market_depth_dict = {}
    for market_depth_ in market_depth_basemodel_list:
        if market_depth_.side == TickType.BID:
            bid_pos_to_market_depth_dict[market_depth_.position] = market_depth_
        else:
            ask_pos_to_market_depth_dict[market_depth_.position] = market_depth_

    for market_depth_dict in [bid_pos_to_market_depth_dict, ask_pos_to_market_depth_dict]:
        cum_qty = 0
        cum_notional = 0
        cum_avg_px = 0
        for pos, market_depth_ in market_depth_dict.items():
            cum_qty += market_depth_.qty
            market_depth_.cumulative_qty = cum_qty

            cum_notional += (market_depth_.px * market_depth_.qty)
            market_depth_.cumulative_notional = cum_notional

            market_depth_.cumulative_avg_px = cum_notional / cum_qty

    for pair_strat_n_http_client_tuple in pair_strat_n_http_client_tuple_list:
        pair_strat, executor_http_client = pair_strat_n_http_client_tuple

        query_symbol_side_list = [(pair_strat.pair_strat_params.strat_leg1.sec.sec_id, TickType.BID),
                                  (pair_strat.pair_strat_params.strat_leg2.sec.sec_id, TickType.ASK)]

        market_depth_list: List[MarketDepthBaseModel] = (
            executor_http_client.get_market_depths_query_client(query_symbol_side_list))

        last_px = None
        for market_depth_obj in market_depth_list:
            # Checking symbol side
            for query_symbol_side in query_symbol_side_list:
                symbol, side = query_symbol_side
                if market_depth_obj.symbol == symbol and market_depth_obj.side == side:
                    break
            else:
                assert False, ("Unexpected: Found symbol or side not matching from any passed query symbol or side"
                               "in received market_depth list")

            # Checking Sort
            if last_px is None:
                last_px = market_depth_obj.px
            else:
                assert last_px > market_depth_obj.px, \
                    (f"Unexpected: market_depth_list must be sorted in terms of decreasing px, "
                     f"market_depth_list: {market_depth_list}")

            # checking cumulative fields
            if market_depth_obj.side == TickType.BID:
                expected_market_depth = bid_pos_to_market_depth_dict.get(market_depth_obj.position)
            else:
                expected_market_depth = ask_pos_to_market_depth_dict.get(market_depth_obj.position)

            assert expected_market_depth.cumulative_qty == market_depth_obj.cumulative_qty, \
                (f"Mismatched cumulative_qty: expected: {expected_market_depth.cumulative_qty} "
                 f"received: {market_depth_obj.cumulative_qty}")
            assert expected_market_depth.cumulative_notional == market_depth_obj.cumulative_notional, \
                (f"Mismatched cumulative_notional: expected: {expected_market_depth.cumulative_notional} "
                 f"received: {market_depth_obj.cumulative_notional}")
            assert expected_market_depth.cumulative_avg_px == market_depth_obj.cumulative_avg_px, \
                (f"Mismatched cumulative_avg_px: expected: {expected_market_depth.cumulative_avg_px} "
                 f"received: {market_depth_obj.cumulative_avg_px}")


@pytest.mark.nightly
def test_fills_after_cxl_request(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                 expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                 last_barter_fixture_list, market_depth_basemodel_list,
                                 buy_chore_, sell_chore_, max_loop_count_per_side,
                                 buy_fill_journal_, sell_fill_journal_, expected_strat_brief_,
                                 refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["avoid_cxl_ack_after_cxl_req"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.barter_simulator_reload_config_query_client()

        for symbol, side in [(buy_symbol, Side.BUY), (sell_symbol, Side.SELL)]:
            # Placing buy chores
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)
            if symbol == buy_symbol:
                px = 100
                qty = 90
                place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client)
            else:
                px = 110
                qty = 94
                place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client)

            ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               symbol, executor_http_client)
            ack_chore_id = ack_chore_journal.chore.chore_id

            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                ack_chore_id, side, symbol, symbol, ack_chore_journal.chore.underlying_account)
            time.sleep(2)

            executor_http_client.barter_simulator_process_fill_query_client(
                ack_chore_journal.chore.chore_id, ack_chore_journal.chore.px, ack_chore_journal.chore.qty,
                side, symbol, ack_chore_journal.chore.underlying_account)
            time.sleep(2)

            chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_id, executor_http_client)
            assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
                (f"Mismatched: ChoreStatus must be OE_FILLED, found: {chore_snapshot.chore_status}, "
                 f"chore_snapshot: {chore_snapshot}")

            # Sending CXL_ACk after chore is fully filled

            cxl_ack_chore_journal = ChoreJournalBaseModel(chore=ack_chore_journal.chore,
                                                          chore_event_date_time=DateTime.utcnow(),
                                                          chore_event=ChoreEventType.OE_CXL_ACK)
            executor_http_client.create_chore_journal_client(cxl_ack_chore_journal)
            time.sleep(2)

            # This must not impact any change in chore states, checking that
            chore_snapshot = get_chore_snapshot_from_chore_id(cxl_ack_chore_journal.chore.chore_id,
                                                              executor_http_client)

            assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
                (f"Mismatched: ChoreStatus must be OE_FILLED, found: {chore_snapshot.chore_status}, "
                 f"chore_snapshot: {chore_snapshot}")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_unload_reload_strat_from_collection(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = 1
        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
            residual_wait_sec, executor_web_client)

        # Unloading Strat
        # making this strat DONE
        email_book_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(PairStratBaseModel(_id=created_pair_strat.id, strat_state=StratState.StratState_DONE),
                             by_alias=True, exclude_none=True))

        strat_key = get_strat_key_from_pair_strat(created_pair_strat)

        strat_collection = email_book_service_native_web_client.get_strat_collection_client(1)
        strat_collection.loaded_strat_keys.remove(strat_key)
        strat_collection.buffered_strat_keys.append(strat_key)

        email_book_service_native_web_client.put_strat_collection_client(strat_collection)

        time.sleep(5)

        pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert not pair_strat.is_partially_running, \
            "Mismatch: is_partially_running must be False after strat unload"
        assert not pair_strat.is_executor_running, \
            "Mismatch: is_executor_running must be False after strat unload"

        # Reloading strat
        strat_collection = email_book_service_native_web_client.get_strat_collection_client(1)
        strat_collection.buffered_strat_keys.remove(strat_key)
        strat_collection.loaded_strat_keys.append(strat_key)
        email_book_service_native_web_client.put_strat_collection_client(strat_collection)

        time.sleep(residual_wait_sec)   # waiting for strat to get loaded completely

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    # Since config file is removed while unloading - no need to revert changes

    loaded_pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
    assert loaded_pair_strat.is_partially_running, \
        ("Unexpected: After strat is loaded by this point since all service up check is done is_partially_running "
         f"must be True, found False, pair_strat: {loaded_pair_strat}")

    executor_http_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(loaded_pair_strat.host,
                                                                                        loaded_pair_strat.port)
    symbol_overview_list = executor_http_client.get_all_symbol_overview_client()

    for symbol_overview in symbol_overview_list:
        executor_http_client.put_symbol_overview_client(symbol_overview)

    time.sleep(residual_wait_sec)   # waiting for strat to get loaded completely

    loaded_pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
    assert loaded_pair_strat.is_executor_running, \
        ("Unexpected: After strat is loaded by this point since all service up check is done is_partially_running "
         f"must be True, found False, pair_strat: {loaded_pair_strat}")
    assert loaded_pair_strat.strat_state == StratState.StratState_READY, \
        (f"Unexpected, StratState must be READY but found state: {loaded_pair_strat.strat_state}, "
         f"pair_strat: {pair_strat}")

    pair_strat = PairStratBaseModel(_id=created_pair_strat.id, strat_state=StratState.StratState_ACTIVE)
    activated_pair_strat = email_book_service_native_web_client.patch_pair_strat_client(jsonable_encoder(
        pair_strat, by_alias=True, exclude_none=True))
    assert activated_pair_strat.strat_state == StratState.StratState_ACTIVE, \
        (f"StratState Mismatched, expected StratState: {StratState.StratState_ACTIVE}, "
         f"received pair_strat's strat_state: {activated_pair_strat.strat_state}")
    print(f"StratStatus updated to Active state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.barter_simulator_reload_config_query_client()

        # updating market_depth to update cache in reloaded strat
        update_market_depth(executor_http_client)

        total_chore_count_for_each_side = 2
        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
            residual_wait_sec, executor_http_client, True)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_sequenced_active_strats_with_same_symbol_side_block_with_leg1_buy(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side,
        expected_chore_limits_, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    created_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    # First created strat is already active, checking if next strat, if tries to get activated with same symbol-side
    # gets exception

    try:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list))
    except Exception as e:
        err_str_ = ("Ongoing strat already exists with same symbol-side pair legs - can't activate this "
                    "strat till other strat is ongoing")
        assert err_str_ in str(e), \
            (f"Strat tring to be activated with same symbol-side must raise exception with description: "
             f"{err_str_} but can't find this description, exception: {e}")
    else:
        assert False, ("Strat with same symbol-side must raise exception while another strat is already ongoing, "
                       "but got activated likely because of some bug")


@pytest.mark.nightly
def test_sequenced_active_strats_with_same_symbol_side_block_with_leg1_sell(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side,
        expected_chore_limits_, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    created_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, leg1_side=Side.SELL,
                                           leg2_side=Side.BUY))

    # First created strat is already active, checking if next strat, if tries to get activated with same symbol-side
    # gets exception

    try:
        created_pair_strat, executor_http_client = (
            create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_barter_fixture_list,
                                               market_depth_basemodel_list, leg1_side=Side.SELL,
                                               leg2_side=Side.BUY))
    except Exception as e:
        err_str_ = ("Ongoing strat already exists with same symbol-side pair legs - can't activate this "
                    "strat till other strat is ongoing")
        assert err_str_ in str(e), \
            (f"Strat tring to be activated with same symbol-side must raise exception with description: "
             f"{err_str_} but can't find this description, exception: {e}")
    else:
        assert False, ("Strat with same symbol-side must raise exception while another strat is already ongoing, "
                       "but got activated likely because of some bug")


@pytest.mark.nightly
def test_sequenced_fully_consume_same_symbol_strats(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side,
        expected_chore_limits_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.max_single_leg_notional = 18000
    expected_strat_limits_.min_chore_notional = 15000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, Side.BUY)

    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_opp_symbol_strat_activate_block_in_single_day_with_buy_first(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, expected_chore_limits_,
        refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.max_single_leg_notional = 18000
    expected_strat_limits_.min_chore_notional = 15000
    strat_done_after_exhausted_consumable_notional(
        leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, Side.BUY)

    try:
        strat_done_after_exhausted_consumable_notional(
            leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
            symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
            refresh_sec_update_fixture, Side.BUY, leg_1_side=Side.SELL, leg_2_side=Side.BUY)
    except Exception as e:
        err_str_ = ("Found strat activated today with symbols of this strat being used in opposite sides - "
                    "can't activate this strat today")
        assert err_str_ in str(e), \
            (f"Strat created with opposite symbol-side must raise exception with description: {err_str_} but "
             f"can't find this description, exception: {e}")
    else:
        assert False, ("Strat with opposite symbol-side must raise exception while activating in same day of "
                       "other strat activated, but got activated likely because of some bug")


@pytest.mark.nightly
def test_opp_symbol_strat_activate_block_in_single_day_with_sell_first(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, expected_chore_limits_,
        refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.max_single_leg_notional = 21000
    expected_strat_limits_.min_chore_notional = 15000
    strat_done_after_exhausted_consumable_notional(
        leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, Side.SELL, leg_1_side=Side.SELL, leg_2_side=Side.BUY)

    try:
        strat_done_after_exhausted_consumable_notional(
            leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
            symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
            refresh_sec_update_fixture, Side.SELL)
    except Exception as e:
        err_str_ = ("Found strat activated today with symbols of this strat being used in opposite sides - "
                    "can't activate this strat today")
        assert err_str_ in str(e), \
            (f"Strat created with opposite symbol-side must raise exception with description: {err_str_} but "
             f"can't find this description, exception: {e}")
    else:
        assert False, ("Strat with opposite symbol-side must raise exception while activating in same day of "
                       "other strat activated, but got activated likely because of some bug")


@pytest.mark.nightly
def test_sequenced_fully_consume_diff_symbol_strats(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        buy_chore_, sell_chore_, max_loop_count_per_side, expected_chore_limits_,
        refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.max_single_leg_notional = 18000
    expected_strat_limits_.min_chore_notional = 15000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, Side.BUY)

    buy_symbol = leg1_leg2_symbol_list[1][0]
    sell_symbol = leg1_leg2_symbol_list[1][1]
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_reactivate_after_pause_strat(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, last_barter_fixture_list,
        refresh_sec_update_fixture):
    # creates and activates multiple pair_strats
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_strat, executor_http_client = (
        create_n_activate_strat(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                expected_strat_status_, symbol_overview_obj_list,
                                market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{activated_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_http_client.barter_simulator_reload_config_query_client()

        time.sleep(2)
        pause_pair_strat = PairStratBaseModel(_id=activated_pair_strat.id,
                                              strat_state=StratState.StratState_PAUSED)
        email_book_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(pause_pair_strat, by_alias=True, exclude_none=True))

        time.sleep(2)
        reactivate_pair_strat = PairStratBaseModel(_id=activated_pair_strat.id,
                                                   strat_state=StratState.StratState_ACTIVE)
        email_book_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(reactivate_pair_strat, by_alias=True, exclude_none=True))

        time.sleep(2)
        total_chore_count_for_each_side = 2
        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
            residual_wait_sec, executor_http_client)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_pause_done_n_unload_strat(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                   expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                   market_depth_basemodel_list, last_barter_fixture_list,
                                   refresh_sec_update_fixture):
    # making limits suitable for this test
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_strat_list: List[PairStratBaseModel] = []
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list[:2]:
        activated_pair_strat, executor_web_client = (
            create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                               market_depth_basemodel_list))
        active_strat_list.append(activated_pair_strat)

    email_book_service_native_web_client.patch_pair_strat_client(
        jsonable_encoder(PairStratBaseModel(_id=active_strat_list[-1].id, strat_state=StratState.StratState_READY),
                         by_alias=True, exclude_none=True))

    time.sleep(5)

    for active_strat in active_strat_list:

        if active_strat != active_strat_list[-1]:
            email_book_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(PairStratBaseModel(_id=active_strat.id, strat_state=StratState.StratState_PAUSED),
                                 by_alias=True, exclude_none=True))

            time.sleep(5)
            email_book_service_native_web_client.patch_pair_strat_client(
                jsonable_encoder(PairStratBaseModel(_id=active_strat.id, strat_state=StratState.StratState_DONE),
                                 by_alias=True, exclude_none=True))

            time.sleep(5)
        strat_key = get_strat_key_from_pair_strat(active_strat)
        strat_collection = email_book_service_native_web_client.get_strat_collection_client(1)
        strat_collection.loaded_strat_keys.remove(strat_key)
        strat_collection.buffered_strat_keys.append(strat_key)

        email_book_service_native_web_client.put_strat_collection_client(strat_collection)
        time.sleep(2)

        pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_strat.id)
        assert not pair_strat.is_partially_running, \
            "Mismatch: is_partially_running must be False after strat unload"
        assert not pair_strat.is_executor_running, \
            "Mismatch: is_executor_running must be False after strat unload"

    # loading strat to get it deleted by clean_n_set_limits of another tests
    for index, active_strat in enumerate(active_strat_list):
        strat_key = get_strat_key_from_pair_strat(active_strat)
        strat_collection = email_book_service_native_web_client.get_strat_collection_client(1)
        strat_collection.loaded_strat_keys.append(strat_key)
        strat_collection.buffered_strat_keys.remove(strat_key)

        email_book_service_native_web_client.put_strat_collection_client(strat_collection)
        time.sleep(residual_wait_sec)   # waiting for strat to get loaded completely

        pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_strat.id)
        executor_http_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
            pair_strat.host, pair_strat.port)
        buy_symbol = active_strat.pair_strat_params.strat_leg1.sec.sec_id
        sell_symbol = active_strat.pair_strat_params.strat_leg2.sec.sec_id
        run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list, executor_http_client)
    time.sleep(residual_wait_sec)


def _frequent_update_strat_view_in_strat(buy_symbol, sell_symbol, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec):
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_web_client = (
        move_snoozed_pair_strat_to_ready_n_then_active(pair_strat_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_strat_limits_,
                                                       expected_start_status_))

    loop_count = 2000
    for i in range(loop_count):
        if i % 2 == 0:
            strat_view_obj = StratViewBaseModel(_id=created_pair_strat.id, market_premium=i)
        else:
            strat_view_obj = StratViewBaseModel(_id=created_pair_strat.id, balance_notional=i)
        photo_book_web_client.patch_strat_view_client(jsonable_encoder(strat_view_obj, by_alias=True,
                                                                                         exclude_none=True))

    updated_strat_view = photo_book_web_client.get_strat_view_client(created_pair_strat.id)
    assert updated_strat_view.market_premium == loop_count-2, \
        (f"Mismatched: market_premium must be {loop_count-2} but found {updated_strat_view.market_premium}, "
         f"_id: {created_pair_strat.id}")
    assert updated_strat_view.balance_notional == loop_count-1, \
        (f"Mismatched: balance_notional must be {loop_count-1} but found {updated_strat_view.balance_notional}, "
         f"_id: {created_pair_strat.id}")


@pytest.mark.nightly
def test_log_book_frequent_pair_strat_updates(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, last_barter_fixture_list,
        refresh_sec_update_fixture):

    leg1_leg2_symbol_list = []
    total_strats = 10
    pair_strat_list = []
    for i in range(1, total_strats + 1):
        leg1_symbol = f"CB_Sec_{i}"
        leg2_symbol = f"EQT_Sec_{i}"
        leg1_leg2_symbol_list.append((leg1_symbol, leg2_symbol))

        stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)
        pair_strat_list.append(stored_pair_strat_basemodel)
        time.sleep(2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_frequent_update_strat_view_in_strat, buy_sell_symbol[0], buy_sell_symbol[1],
                                   pair_strat_list[idx],
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture)
                   for idx, buy_sell_symbol in enumerate(leg1_leg2_symbol_list)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def check_all_computes_for_amend(
        active_pair_strat_id, symbol, side, chore_id, executor_http_client,
        new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
        last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
        filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px, other_side_residual_qty,
        other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure, rej_check: bool | None = None, 
        residual_qty: int | None = None):
    chore_snapshot = get_chore_snapshot_from_chore_id(chore_id,
                                                      executor_http_client)
    assert chore_snapshot.chore_status == chore_status, \
        f"Mismatched: Chore status must be {chore_status} but found: {chore_snapshot.chore_status = }"
    assert chore_snapshot.chore_brief.qty == new_qty, \
        f"Mismatched: expected chore_snapshot qty: {new_qty} found: {chore_snapshot.chore_brief.qty = }"
    assert chore_snapshot.chore_brief.px == new_px, \
        f"Mismatched: expected chore_snapshot px: {new_px} found: {chore_snapshot.chore_brief.px = }"
    expected_chore_notional = new_qty * get_px_in_usd(new_px)
    assert chore_snapshot.chore_brief.chore_notional == expected_chore_notional, \
        (f"Mismatched: expected chore_snapshot expected_chore_notional: {expected_chore_notional} "
         f"found: {chore_snapshot.chore_brief.chore_notional = }")
    assert chore_snapshot.last_amend_qty == amend_qty, \
        f"Mismatched: expected chore_snapshot last_amend_qty: {amend_qty} found: {chore_snapshot.last_amend_qty = }"
    assert chore_snapshot.last_amend_px == amend_px, \
        f"Mismatched: expected chore_snapshot last_amend_px: {amend_px} found: {chore_snapshot.last_amend_px = }"
    assert chore_snapshot.last_original_qty == last_original_qty, \
        (f"Mismatched: expected chore_snapshot last_original_qty: {last_original_qty} "
         f"found: {chore_snapshot.last_original_qty = }")
    assert chore_snapshot.last_original_px == last_original_px, \
        (f"Mismatched: expected chore_snapshot last_original_px: {last_original_px} "
         f"found: {chore_snapshot.last_original_px= }")
    assert chore_snapshot.total_amend_dn_qty == total_amend_dn_qty, \
        (f"Mismatched: expected chore_snapshot total_amend_dn_qty: {total_amend_dn_qty} "
         f"found: {chore_snapshot.total_amend_dn_qty= }")
    assert chore_snapshot.total_amend_up_qty == total_amend_up_qty, \
        (f"Mismatched: expected chore_snapshot total_amend_up_qty: {total_amend_up_qty} "
         f"found: {chore_snapshot.total_amend_up_qty= }")
    assert chore_snapshot.cxled_qty == cxled_qty, \
        f"Mismatched: ChoreSnapshot cxled_qty must be {cxled_qty}, found {chore_snapshot.cxled_qty}"
    assert chore_snapshot.cxled_notional == cxled_notional, \
        (f"Mismatched: ChoreSnapshot cxled_notional must be {cxled_notional}, "
         f"found {chore_snapshot.cxled_notional}")
    assert chore_snapshot.avg_cxled_px == cxled_px, \
        (f"Mismatched: ChoreSnapshot avg_cxled_px must be "
         f"{cxled_px}, found {chore_snapshot.avg_cxled_px}")
    assert chore_snapshot.filled_qty == filled_qty, \
        f"Mismatched: ChoreSnapshot avg_cxled_px must be {filled_qty}, found {chore_snapshot.filled_qty}"
    assert chore_snapshot.fill_notional == filled_notional, \
        (f"Mismatched: ChoreSnapshot fill_notional must be {filled_notional}, "
         f"found {chore_snapshot.fill_notional}")
    assert chore_snapshot.avg_fill_px == filled_px, \
        f"Mismatched: ChoreSnapshot avg_fill_px must be {filled_px}, found {chore_snapshot.avg_fill_px}"

    symbol_side_snapshot_list = (
        executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(symbol, side))
    assert len(symbol_side_snapshot_list) == 1, \
        (f"found {len(symbol_side_snapshot_list) = }, must be exact 1 for symbol and side: "
         f"{symbol, side}")

    symbol_side_snapshot = symbol_side_snapshot_list[0]
    assert symbol_side_snapshot.total_qty == new_qty, \
        (f"Mismatched: expected symbol_side_snapshot.total_qty: {new_qty}, "
         f"found {symbol_side_snapshot.total_qty = }")
    assert symbol_side_snapshot.avg_px == new_px, \
        (f"Mismatched: expected symbol_side_snapshot.avg_px: {new_px}, "
         f"found {symbol_side_snapshot.avg_px = }")
    assert symbol_side_snapshot.total_filled_qty == filled_qty, \
        (f"Mismatched: symbol_side_snapshot.total_filled_qty must be {filled_qty}, found "
         f"{symbol_side_snapshot.total_filled_qty = }")
    assert symbol_side_snapshot.total_fill_notional == filled_notional, \
        (f"Mismatched: symbol_side_snapshot.total_fill_notional must be {filled_notional}, "
         f"found {symbol_side_snapshot.total_fill_notional = }")
    assert symbol_side_snapshot.avg_fill_px == filled_px, \
        (f"Mismatched: symbol_side_snapshot.avg_fill_px must be {filled_px}, found "
         f"{symbol_side_snapshot.avg_fill_px = }")
    assert symbol_side_snapshot.total_cxled_qty == cxled_qty, \
        (f"Mismatched: symbol_side_snapshot.total_cxled_qty must be {cxled_qty}, found "
         f"{symbol_side_snapshot.total_cxled_qty = }")
    assert (symbol_side_snapshot.total_cxled_notional == cxled_notional), \
        (f"Mismatched: symbol_side_snapshot.total_cxled_notional must be "
         f"{cxled_notional}, found {symbol_side_snapshot.total_cxled_notional = }")
    assert symbol_side_snapshot.avg_cxled_px == cxled_px, \
        (f"Mismatched: symbol_side_snapshot.avg_cxled_px must be {cxled_px}, found "
         f"{symbol_side_snapshot.avg_cxled_px = }")
    assert symbol_side_snapshot.last_update_fill_px == filled_px, \
        (f"Mismatched: symbol_side_snapshot.last_update_fill_px must be {filled_px}, found "
         f"{symbol_side_snapshot.last_update_fill_px = }")
    assert symbol_side_snapshot.last_update_fill_qty == last_filled_qty, \
        (f"Mismatched: symbol_side_snapshot.last_update_fill_qty must be {last_filled_qty}, found "
         f"{symbol_side_snapshot.last_update_fill_qty = }")

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
    strat_limits = executor_http_client.get_strat_limits_client(active_pair_strat_id)
    strat_brief = executor_http_client.get_strat_brief_client(active_pair_strat_id)
    if side == Side.BUY:
        strat_brief_bartering_brief = strat_brief.pair_buy_side_bartering_brief
    else:
        strat_brief_bartering_brief = strat_brief.pair_sell_side_bartering_brief
    assert (strat_brief_bartering_brief.open_qty == open_qty), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_qty: "
         f"{open_qty}, found {strat_brief_bartering_brief.open_qty = }")
    assert (strat_brief_bartering_brief.open_notional == open_notional), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.open_notional: "
         f"{open_notional}, found {strat_brief_bartering_brief.open_notional = }")
    if chore_status == ChoreStatusType.OE_DOD:
        if residual_qty is None:        
            if not rej_check and amend_qty is not None:
                residual_qty = amend_qty - filled_qty
            else:
                residual_qty = new_qty - filled_qty
        # else not required: taking passed param value
    else:
        residual_qty = 0
    assert (strat_brief_bartering_brief.residual_qty == residual_qty), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.residual_qty: "
         f"{residual_qty}, found {strat_brief_bartering_brief.residual_qty = }")
    if chore_status in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED, ChoreStatusType.OE_OVER_FILLED]:
        consumable_open_chores = 5
    else:
        consumable_open_chores = 4
    assert (strat_brief_bartering_brief.consumable_open_chores == consumable_open_chores), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_chores: "
         f"{consumable_open_chores}, found {strat_brief_bartering_brief.consumable_open_chores = }")
    assert (strat_brief_bartering_brief.all_bkr_cxlled_qty == cxled_qty), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.all_bkr_cxlled_qty: "
         f"{cxled_qty}, found {strat_brief_bartering_brief.all_bkr_cxlled_qty = }")
    assert (strat_brief_bartering_brief.consumable_notional == (
            strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional - open_notional)), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_notional: "
         f"{strat_limits.max_single_leg_notional - symbol_side_snapshot.total_fill_notional - open_notional}, "
         f"found {strat_brief_bartering_brief.consumable_notional = }")
    assert (strat_brief_bartering_brief.consumable_open_notional ==
            strat_limits.max_open_single_leg_notional - open_notional), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_open_notional: "
         f"{strat_limits.max_open_single_leg_notional - open_notional}, "
         f"found {strat_brief_bartering_brief.consumable_open_notional = }")
    total_security_size: int = \
        static_data.get_security_float_from_ticker(chore_snapshot.chore_brief.security.sec_id)
    assert (strat_brief_bartering_brief.consumable_concentration == (
            (total_security_size / 100 * strat_limits.max_concentration) -
            (open_qty + symbol_side_snapshot.total_filled_qty))), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_concentration: "
         f"{(total_security_size / 100 * strat_limits.max_concentration) - (open_qty + symbol_side_snapshot.total_filled_qty)}, "
         f"found {strat_brief_bartering_brief.consumable_concentration = }")
    assert (strat_brief_bartering_brief.consumable_cxl_qty == (
            (((open_qty + symbol_side_snapshot.total_filled_qty +
               symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) -
            symbol_side_snapshot.total_cxled_qty)), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_cxl_qty: "
         f"{(((open_qty + symbol_side_snapshot.total_filled_qty + symbol_side_snapshot.total_cxled_qty) / 100) * strat_limits.cancel_rate.max_cancel_rate) - symbol_side_snapshot.total_cxled_qty}, "
         f"found {strat_brief_bartering_brief.consumable_cxl_qty = }")
    if side == Side.BUY:
        current_last_barter_px = buy_last_barter_px
        other_last_barter_px = sell_last_barter_px
    else:
        current_last_barter_px = sell_last_barter_px
        other_last_barter_px = buy_last_barter_px

    assert (strat_brief_bartering_brief.indicative_consumable_residual == (
            strat_limits.residual_restriction.max_residual -
            ((strat_brief_bartering_brief.residual_qty *
              get_px_in_usd(current_last_barter_px)) - (
                     other_side_residual_qty * get_px_in_usd(other_last_barter_px))))), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.indicative_consumable_residual: "
         f"{strat_limits.residual_restriction.max_residual - ((strat_brief_bartering_brief.residual_qty * get_px_in_usd(current_last_barter_px)) - (other_side_residual_qty * get_px_in_usd(other_last_barter_px)))}, "
         f"found {strat_brief_bartering_brief.indicative_consumable_residual = }")
    assert (strat_brief.consumable_nett_filled_notional == (
            strat_limits.max_net_filled_notional -
            abs(symbol_side_snapshot.total_fill_notional - other_side_fill_notional))), \
        (f"Mismatched: expected strat_brief.pair_{side.lower()}_side_bartering_brief.consumable_nett_filled_notional: "
         f"{strat_limits.max_open_single_leg_notional}, "
         f"found {strat_brief_bartering_brief.consumable_nett_filled_notional = }")

    strat_status = executor_http_client.get_strat_status_client(active_pair_strat_id)
    if side == Side.BUY:
        total_qty = strat_status.total_buy_qty
        total_open_qty = strat_status.total_open_buy_qty
        total_open_notional = strat_status.total_open_buy_notional
        avg_open_px = strat_status.avg_open_buy_px
        total_fill_qty = strat_status.total_fill_buy_qty
        total_fill_notional = strat_status.total_fill_buy_notional
        avg_fill_px = strat_status.avg_fill_buy_px
        total_cxl_qty = strat_status.total_cxl_buy_qty
        total_cxl_notional = strat_status.total_cxl_buy_notional
        avg_cxl_px = strat_status.avg_cxl_buy_px
    else:
        total_qty = strat_status.total_sell_qty
        total_open_qty = strat_status.total_open_sell_qty
        total_open_notional = strat_status.total_open_sell_notional
        avg_open_px = strat_status.avg_open_sell_px
        total_fill_qty = strat_status.total_fill_sell_qty
        total_fill_notional = strat_status.total_fill_sell_notional
        avg_fill_px = strat_status.avg_fill_sell_px
        total_cxl_qty = strat_status.total_cxl_sell_qty
        total_cxl_notional = strat_status.total_cxl_sell_notional
        avg_cxl_px = strat_status.avg_cxl_sell_px

    total_open_exposure = strat_status.total_open_exposure
    total_fill_exposure = strat_status.total_fill_exposure
    total_cxl_exposure = strat_status.total_cxl_exposure
    assert total_qty == new_qty, \
        (f"Mismatched: expected strat_status.total_{side.lower()}_qty: "
         f"{new_qty}, found {total_qty = }")
    assert total_open_qty == open_qty, \
        (f"Mismatched: expected strat_status total_open_{side.lower()}_qty: "
         f"{open_qty}, found {total_open_qty = }")
    assert (total_open_notional == open_notional), \
        (f"Mismatched: expected strat_status.total_open_{side.lower()}_notional: "
         f"{open_notional}, found {total_open_notional = }")
    assert (avg_open_px == open_px), \
        (f"Mismatched: expected strat_status.avg_open_{side.lower()}_px: "
         f"{open_px}, found {avg_open_px = }")
    assert (total_fill_qty == filled_qty), \
        (f"Mismatched: expected strat_status.total_fill_{side.lower()}_qty: "
         f"{filled_qty}, found {total_fill_qty = }")
    assert (total_fill_notional == filled_notional), \
        (f"Mismatched: expected strat_status.total_fill_{side.lower()}_notional: "
         f"{filled_notional}, found {total_fill_notional = }")
    assert (avg_fill_px == filled_px), \
        (f"Mismatched: expected strat_status.avg_fill_{side.lower()}_px: "
         f"{filled_px}, found {avg_fill_px = }")
    assert (total_cxl_qty == cxled_qty), \
        (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_qty: "
         f"{cxled_qty}, found {total_cxl_qty = }")
    assert (total_cxl_notional == cxled_notional), \
        (f"Mismatched: expected strat_status.total_cxl_{side.lower()}_notional: "
         f"{cxled_notional}, found {total_cxl_notional = }")
    assert (avg_cxl_px == cxled_px), \
        (f"Mismatched: expected strat_status.avg_cxl_{side.lower()}_px: "
         f"{cxled_px}, found {avg_cxl_px = }")
    assert (total_open_exposure == open_exposure), \
        (f"Mismatched: expected strat_status.total_open_exposure: "
         f"{open_exposure}, found {total_open_exposure = }")
    assert (total_fill_exposure == filled_exposure), \
        (f"Mismatched: expected strat_status.total_fill_exposure: "
         f"{filled_exposure}, found {total_fill_exposure = }")
    assert (total_cxl_exposure == cxled_exposure), \
        (f"Mismatched: expected strat_status.total_cxl_exposure: "
         f"{cxled_exposure}, found {total_cxl_exposure = }")

    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    if side == Side.BUY:
        overall_notional = portfolio_status.overall_buy_notional
        overall_fill_notional = portfolio_status.overall_buy_fill_notional
    else:
        overall_notional = portfolio_status.overall_sell_notional
        overall_fill_notional = portfolio_status.overall_sell_fill_notional
    assert (overall_notional == open_notional + filled_notional), \
        (f"Mismatched: expected portfolio_status.overall_{side.lower()}_notional: "
         f"{open_notional + filled_notional}, found {overall_notional = }")
    assert (overall_fill_notional == filled_notional), \
        (f"Mismatched: expected portfolio_status.overall_{side.lower()}_fill_notional: "
         f"{filled_notional}, found {overall_fill_notional = }")

@pytest.mark.nightly
def test_simple_non_risky_amend_based_on_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_symbol_side_snapshot = None
        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_qty = qty
                buy_px = px

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
            else:
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK, chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simple_risky_amend_based_on_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_symbol_side_snapshot = None
        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_px)
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
            else:
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                new_qty = amend_qty
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                new_qty = amend_qty
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)

            if side == Side.BUY:
                cxled_qty = amend_qty - filled_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = amend_qty
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simple_non_risky_amend_based_on_px(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_qty = qty
                buy_px = px

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                buy_amend_px = amend_px
            else:
                amend_px = px + 1

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            amend_qty = None
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)

            new_px = amend_px
            amend_qty = None
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            cxled_qty = 0
            cxled_px = 0
            cxled_notional = 0
            new_qty = qty
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            new_px = amend_px
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_px = amend_px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simple_risky_amend_based_on_px(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_symbol_side_snapshot = None
        buy_filled_qty = None
        buy_qty = None
        buy_px = None
        buy_amend_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_qty = qty
                buy_px = px

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                buy_amend_px = amend_px
            else:
                amend_px = px - 1

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = amend_px
            amend_qty = None
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_px = px
            last_original_qty = qty
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_px = amend_px
            amend_qty = None
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            cxled_qty = 0
            cxled_px = 0
            cxled_notional = 0
            new_qty = qty
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            new_px = amend_px
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_px = amend_px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simple_non_risky_amend_based_on_qty_and_px(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px) + (amend_qty - filled_qty) * get_px_in_usd(
                    amend_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simple_risky_amend_based_on_px_and_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_amend_qty = None
        buy_amend_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty
            
            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px) + (amend_qty - filled_qty) * get_px_in_usd(
                    amend_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_simple_risky_amend_based_on_px_or_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_amend_qty = None
        buy_amend_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                # buy side: px is amending dn which is non-risky and qty is amended up which is risky so overall
                # it should be risky
                amend_px = px - 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                # sell side: px is amending dn which is risky and qty is amended up which is non-risky so overall
                # it should be risky
                amend_px = px - 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            total_amend_dn_qty = 0
            total_amend_up_qty = 10
            new_qty = amend_qty
            cxled_qty = 0
            cxled_px = 0
            cxled_notional = 0
            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px))
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            total_amend_dn_qty = 0
            total_amend_up_qty = 10
            new_qty = amend_qty
            cxled_qty = 0
            cxled_px = 0
            cxled_notional = 0
            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px))
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            total_amend_dn_qty = 0
            total_amend_up_qty = 10
            new_qty = amend_qty
            cxled_qty = amend_qty - filled_qty
            cxled_px = amend_px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            new_px = amend_px
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_qty_and_px_with_fill_before_amd_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 20
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing fills before receiving AMD_ACK
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account)

            filled_qty = filled_qty * 2
            if side == Side.BUY:
                buy_filled_qty = filled_qty
                
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px) + (amend_qty - filled_qty) * get_px_in_usd(
                    amend_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_qty_and_px_with_fulfill_before_amd_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing fills before receiving AMD_ACK - makes chore filled
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account)

            filled_qty = filled_qty * 2
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_FILLED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
                chore_status = ChoreStatusType.OE_OVER_FILLED
                open_qty = 0
                open_notional = 0
                open_px = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                chore_status = ChoreStatusType.OE_ACKED
                open_qty = amend_qty - filled_qty
                open_notional = open_qty * get_px_in_usd(amend_px)
                open_px = amend_px

            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            if side == Side.BUY:
                paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
                assert paused_pair_strat.strat_state == StratState.StratState_PAUSED, \
                    f"Mismatched: strat state must be PAUSED, found: {paused_pair_strat.strat_state}"

                # Checking alert in strat_alert
                time.sleep(5)
                check_str = "Received ChoreEventType.OE_AMD_ACK for amend qty which makes chore OVER_FILLED,"
                assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
                check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

                # forcefully turning strat to active again for checking sell chore
                pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
                pair_strat.strat_state = StratState.StratState_ACTIVE
                email_book_service_native_web_client.put_pair_strat_client(pair_strat)
            else:
                time.sleep(5)
                check_str = ("Received ChoreEventType.OE_AMD_ACK for amend qty which makes chore ACKED to chore "
                             "which was FILLED before amend")
                assert_fail_msg = f"Can't find alert: {check_str!r}"
                check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

                time.sleep(residual_wait_sec)

                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_px = amend_px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                chore_status = ChoreStatusType.OE_DOD
                open_qty = 0
                open_notional = 0
                open_px = 0
                new_px = amend_px
                filled_notional = filled_qty * get_px_in_usd(px)
                filled_px = px
                last_original_qty = qty
                last_original_px = px
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)) - cxled_notional

                try:
                    check_all_computes_for_amend(
                        active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                        new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                        last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                        filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                        other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                        cxled_exposure)
                except AssertionError as ass_e:
                    print("ASSERT", ass_e)
                    raise AssertionError(ass_e)
                except Exception as e:
                    print("Exception", e)
                    raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_qty_and_px_with_overfill_before_amd_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 60
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing fills before receiving AMD_ACK - makes chore filled
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account)

            filled_qty = filled_qty * 2
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_OVER_FILLED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_PAUSED, \
                f"Mismatched: strat state must be PAUSED, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = "Unexpected: Received fill that will make chore_snapshot OVER_FILLED"
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            open_qty = 0
            open_notional = 0
            open_px = 0
            chore_status = ChoreStatusType.OE_OVER_FILLED
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Checking alert in strat_alert
            time.sleep(5)
            check_str = ("Received ChoreEventType.OE_AMD_ACK for amend qty which makes chore OVER_FILLED to "
                         "chore which is already OVER_FILLED")
            assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            if side == Side.BUY:
                # forcefully turning strat to active again for checking sell chore
                pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
                pair_strat.strat_state = StratState.StratState_ACTIVE
                email_book_service_native_web_client.put_pair_strat_client(pair_strat)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_fill_before_amd_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 20
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px))
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing fills before receiving AMD_ACK
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account)

            filled_qty = filled_qty * 2
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px) + (amend_qty - filled_qty) * get_px_in_usd(
                    amend_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_fulfill_before_amd_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                open_qty = amend_qty - filled_qty
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
                open_qty = qty - filled_qty - cxled_qty
                open_notional = 0

            open_px = amend_px
            open_notional = open_qty * get_px_in_usd(amend_px)
            chore_status = ChoreStatusType.OE_AMD
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing fills before receiving AMD_ACK - makes chore filled
            last_filled_qty = open_qty
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, last_filled_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            filled_qty = amend_qty
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            open_qty = 0
            open_notional = 0
            open_px = 0
            chore_status = ChoreStatusType.OE_FILLED
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = - cxled_notional
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            open_qty = 0
            open_notional = 0
            open_px = 0
            chore_status = ChoreStatusType.OE_FILLED
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_overfill_before_amd_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 60
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                open_qty = amend_qty - filled_qty
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
                open_qty = qty - filled_qty - cxled_qty
                open_notional = 0

            open_px = amend_px
            open_notional = open_qty * get_px_in_usd(amend_px)
            chore_status = ChoreStatusType.OE_AMD
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing fills before receiving AMD_ACK - makes chore filled
            last_filled_qty = open_qty + 20
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, last_filled_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            filled_qty += last_filled_qty
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            open_qty = 0
            open_notional = 0
            open_px = 0
            chore_status = ChoreStatusType.OE_OVER_FILLED
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = - cxled_notional
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_PAUSED, \
                f"Mismatched: strat state must be PAUSED, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = "Unexpected: Received fill that will make chore_snapshot OVER_FILLED"
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            open_qty = 0
            open_notional = 0
            open_px = 0
            chore_status = ChoreStatusType.OE_OVER_FILLED
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = 0
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            if side == Side.BUY:
                # forcefully turning strat to active again for checking sell chore
                pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
                pair_strat.strat_state = StratState.StratState_ACTIVE
                email_book_service_native_web_client.put_pair_strat_client(pair_strat)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_px_and_qty_with_more_filled_qty_than_amend_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    # IMPO: amending dn to qty less than already filled qty in non-risky case can only be possible in buy side since,
    # amend dn is non-risky in buy, sell side if amend_dn is done then it will be risky and amending up is not for
    # this test

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 90
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = (qty - filled_qty) * get_px_in_usd(px)
            filled_exposure = filled_qty * get_px_in_usd(px)
            cxled_exposure = 0
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # not updating any value since this amend req should get rejected and values should stay unchanged
            amend_qty = None
            amend_px = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = "Unsupported: Amend qty is less than already filled qty - ignoring is amend request"
            assert_fail_msg = f"Couldn't find any alert saying: {check_str}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_more_filled_qty_than_amend_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    # IMPO: amending dn to qty less than already filled qty in risky case can only be possible in sell side since,
    # amend dn is risky in sell, buy side if amend_dn is done then it will be non-risky and amending up is not for
    # this test

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 95
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(110, 95, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
            filled_exposure = - filled_qty * get_px_in_usd(px)
            cxled_exposure = 0
            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # not updating any value since this amend req should get rejected and values should stay unchanged
            amend_qty = None
            amend_px = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = "Unsupported: Amend qty is less than already filled qty - ignoring is amend request"
            assert_fail_msg = f"Couldn't find any alert saying: {check_str}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_px_and_qty_with_amend_making_filled(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    # IMPO: amending dn to qty less than already filled qty in non-risky case can only be possible in buy side since,
    # amend dn is non-risky in buy, sell side if amend_dn is done then it will be risky and amending up is not for
    # this test

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = (qty - filled_qty) * get_px_in_usd(px)
            filled_exposure = filled_qty * get_px_in_usd(px)
            cxled_exposure = 0

            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = filled_qty

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = (qty - filled_qty) * get_px_in_usd(px)
            filled_exposure = filled_qty * get_px_in_usd(px)
            cxled_exposure = 0

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            cxled_qty = qty - amend_qty
            cxled_px = px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            new_qty = qty
            total_amend_dn_qty = open_qty   # removing whatever is open
            total_amend_up_qty = 0
            chore_status = ChoreStatusType.OE_FILLED
            open_qty = 0
            open_notional = 0
            open_px = 0
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = open_notional
            filled_exposure = filled_notional
            cxled_exposure = cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Checking alert in strat_alert
            time.sleep(5)
            check_str = "Received ChoreEventType.OE_AMD_ACK for amend qty which makes chore FILLED,"
            assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_amend_making_filled(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    # IMPO: amending dn to qty less than already filled qty in risky case can only be possible in sell side since,
    # amend dn is risky in sell, buy side if amend_dn is done then it will be non-risky and amending up is not for
    # this test

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(110, 95, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
            filled_exposure = - filled_qty * get_px_in_usd(px)
            cxled_exposure = 0

            last_original_px = None
            last_original_qty = None
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = filled_qty

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            cxled_qty = qty - amend_qty
            cxled_px = px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            new_qty = qty
            total_amend_dn_qty = open_qty  # removing whatever is open
            total_amend_up_qty = 0
            chore_status = ChoreStatusType.OE_FILLED
            open_qty = 0
            open_notional = 0
            open_px = 0
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Checking alert in strat_alert
            time.sleep(5)
            check_str = "Received ChoreEventType.OE_AMD_UNACK for amend qty which makes chore FILLED,"

            assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            cxled_qty = qty - amend_qty
            cxled_px = px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            new_qty = qty
            total_amend_up_qty = 0
            chore_status = ChoreStatusType.OE_FILLED
            open_qty = 0
            open_notional = 0
            open_px = 0
            new_px = amend_px
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_px_and_qty_with_cxl_req_n_cxl_ack_before_amend_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 20
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_amend_px)))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req and cxl ack
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = ((qty - amend_qty) * get_px_in_usd(amend_px) +
                                  (amend_qty - filled_qty) * get_px_in_usd(px))
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (((qty - filled_qty) * get_px_in_usd(px)) +
                                  ((amend_qty - qty) * get_px_in_usd(amend_px)))
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            new_px = amend_px
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_amend_px))) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = "Amending dn qty on chore which is already DOD"
            assert_fail_msg = f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        
        
@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_cxl_req_n_cxl_ack_before_amend_ack(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 20
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req and cxl ack
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px) + (amend_qty - filled_qty) * get_px_in_usd(
                    amend_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_based_on_px_and_qty_with_cxl_req_after_amend_req_n_cxl_ack_post_amend(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 20
            config_dict["symbol_configs"][symbol]["avoid_cxl_ack_after_cxl_req"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = (qty - amend_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
                cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                cxled_px = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_CXL_UNACK
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px)))

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing CXL ACK
            cxl_ack_chore_journal = copy.deepcopy(latest_ack_obj)
            cxl_ack_chore_journal.chore_event = ChoreEventType.OE_CXL_ACK
            cxl_ack_chore_journal.chore_event_date_time = DateTime.utcnow()
            cxl_ack_chore_journal.id = None
            executor_http_client.create_chore_journal_client(cxl_ack_chore_journal)

            if side == Side.BUY:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = ((qty - amend_qty) * get_px_in_usd(px) +
                                  (amend_qty - filled_qty) * get_px_in_usd(amend_px))
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = ((amend_qty - filled_qty) * get_px_in_usd(amend_px))
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            new_px = amend_px
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = (((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) +
                                  ((buy_qty - buy_amend_qty) * get_px_in_usd(buy_px))) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_based_on_px_and_qty_with_cxl_req_after_amend_req_n_cxl_ack_post_amend(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 20
            config_dict["symbol_configs"][symbol]["avoid_cxl_ack_after_cxl_req"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            last_filled_qty = filled_qty
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                cxled_px = 0
            else:
                cxled_qty = (qty - amend_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
                cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
                cxled_px = 0
            else:
                cxled_qty = (qty - amend_qty)
                cxled_notional = (qty - amend_qty) * get_px_in_usd(px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
                cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty

            new_px = amend_px
            chore_status = ChoreStatusType.OE_CXL_UNACK
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing CXL ACK
            cxl_ack_chore_journal = copy.deepcopy(latest_ack_obj)
            cxl_ack_chore_journal.chore_event = ChoreEventType.OE_CXL_ACK
            cxl_ack_chore_journal.chore_event_date_time = DateTime.utcnow()
            cxl_ack_chore_journal.id = None
            executor_http_client.create_chore_journal_client(cxl_ack_chore_journal)

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = ((amend_qty - filled_qty) * get_px_in_usd(amend_px))
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                cxled_qty = (qty - amend_qty) + (amend_qty - filled_qty)
                cxled_notional = ((qty - amend_qty) * get_px_in_usd(px) +
                                  (amend_qty - filled_qty) * get_px_in_usd(amend_px))
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            new_px = amend_px
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_amend_qty - buy_filled_qty) * get_px_in_usd(buy_amend_px)) - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_rej_based_on_px_and_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - filled_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ chore
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_DOD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_notional = cxled_qty * get_px_in_usd(px)
            cxled_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = ((buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_DOD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_notional = cxled_qty * get_px_in_usd(px)
            cxled_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        
        
@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_with_overfill_post_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    First buy chore is placed for 90 qty then amend req is placed for 100 qty since amend up is
    risky in buy side amend will be applied, then fulfill comes and then rej comes, removing
    amended up qty and making chore over filled
    """
        
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 0
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px + 1
            amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # placing fills before receiving AMD_ACK - makes chore filled
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, amend_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            new_qty = amend_qty
            filled_qty = amend_qty
            cxled_qty = 0
            cxled_px = 0
            cxled_notional = 0
            total_amend_dn_qty = 0
            total_amend_up_qty = 10
            new_px = amend_px
            chore_status = ChoreStatusType.OE_FILLED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = open_notional
            filled_exposure = filled_notional
            cxled_exposure = cxled_notional

            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_OVER_FILLED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(filled_px)
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = open_notional
            filled_exposure = filled_notional
            cxled_exposure = 0
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_PAUSED, \
                f"Mismatched: strat state must be PAUSED, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = ("Reverted amend changes post receiving OE_AMD_REJ on chore that had status .* "
                         "- putting strat to pause and applying amend rollback")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_with_filled_post_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    First buy chore is placed for 90 qty then amend req is placed for 100 qty since amend up is
    risky in buy side amend will be applied, then 90 fills come and then rej comes, removing
    amended up qty and making chore filled
    """

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 0
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px + 1
            amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # placing fills before receiving AMD_ACK
            filled_qty = qty
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, filled_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            new_qty = amend_qty
            cxled_qty = 0
            cxled_px = 0
            cxled_notional = 0
            total_amend_dn_qty = 0
            total_amend_up_qty = 10
            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = amend_qty - filled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = open_notional
            filled_exposure = filled_notional
            cxled_exposure = cxled_notional

            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_FILLED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(filled_px)
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = open_notional
            filled_exposure = filled_notional
            cxled_exposure = 0
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = ("Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                         "ChoreStatusType.OE_AMD before amend applied - reverted status: ChoreStatusType.OE_FILLED")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_with_overfill_post_amd_req_n_ack_post_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    First sell chore is placed for 110 qty then amend req is placed for 100 qty since amend dn is
    risky in sell side, amend will be applied, then overfill comes with 105 qty and
    then rej comes, removing amended up qty and making chore acked again
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 0
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(95, 110, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # placing fills before receiving AMD_ACK - makes chore filled
            filled_qty = amend_qty + 5
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, filled_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            new_qty = qty
            cxled_qty = qty - amend_qty
            cxled_px = px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            total_amend_dn_qty = 10
            total_amend_up_qty = 0
            new_px = amend_px
            chore_status = ChoreStatusType.OE_OVER_FILLED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_PAUSED, \
                f"Mismatched: strat state must be PAUSED, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = "Unexpected: Received fill that will make chore_snapshot OVER_FILLED"
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_ACTIVE, \
                f"Mismatched: strat state must be ACTIVE, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = ("Reverted amend changes post receiving OE_AMD_REJ on chore that had status .* "
                         "- UNPAUSING strat and applying amend rollback")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_DOD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_notional = cxled_qty * get_px_in_usd(px)
            cxled_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_with_overfill_post_amd_req_n_filled_post_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    First sell chore is placed for 110 qty then amend req is placed for 100 qty since amend dn is
    risky in sell side, amend will be applied, then overfill comes with 110 qty and
    then rej comes, removing amended up qty and checking chore state must be FILLED
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 0
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(95, 110, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # placing fills before receiving AMD_ACK - makes chore filled
            filled_qty = qty
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, filled_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            new_qty = qty
            cxled_qty = qty - amend_qty
            cxled_px = px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            total_amend_dn_qty = 10
            total_amend_up_qty = 0
            new_px = amend_px
            chore_status = ChoreStatusType.OE_OVER_FILLED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_PAUSED, \
                f"Mismatched: strat state must be PAUSED, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = "Unexpected: Received fill that will make chore_snapshot OVER_FILLED"
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_FILLED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            paused_pair_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat.id)
            assert paused_pair_strat.strat_state == StratState.StratState_ACTIVE, \
                f"Mismatched: strat state must be ACTIVE, found: {paused_pair_strat.strat_state}"

            time.sleep(5)
            check_str = ("Reverted amend changes post receiving OE_AMD_REJ on chore that had status .* "
                         "- UNPAUSING strat and applying amend rollback")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_with_filled_post_amd_req_n_acked_post_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    First sell chore is placed for 110 qty then amend req is placed for 100 qty since amend dn is
    risky in sell side, amend will be applied, then fill comes with 100 qty and
    then rej comes, removing amended up qty and checking chore state must be ACK
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 0
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(95, 110, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)

            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            amend_px = px - 1
            amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            # placing fills before receiving AMD_ACK - makes chore filled
            filled_qty = amend_qty
            executor_http_client.barter_simulator_process_fill_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.px, filled_qty, side, chore_symbol,
                latest_ack_obj.chore.underlying_account, use_exact_passed_qty=True)

            new_qty = qty
            cxled_qty = qty - amend_qty
            cxled_px = px
            cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
            total_amend_dn_qty = 10
            total_amend_up_qty = 0
            new_px = amend_px
            chore_status = ChoreStatusType.OE_FILLED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            last_original_qty = qty
            last_original_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = ("Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                         "ChoreStatusType.OE_FILLED before amend applied - reverted status: ChoreStatusType.OE_ACKED")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_DOD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_notional = cxled_qty * get_px_in_usd(px)
            cxled_px = px
            other_side_residual_qty = 0
            other_side_fill_notional = 0
            open_exposure = - open_notional
            filled_exposure = - filled_notional
            cxled_exposure = - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_rej_based_on_px_and_qty_with_cxl_unack_pre_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["avoid_cxl_ack_after_cxl_req"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_residual_qty = None
        buy_fill_notional = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                buy_fill_notional = filled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - filled_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            chore_status = ChoreStatusType.OE_CXL_UNACK
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ chore
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            chore_status = ChoreStatusType.OE_CXL_UNACK
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing CXL ACK
            cxl_ack_chore_journal = copy.deepcopy(latest_ack_obj)
            cxl_ack_chore_journal.chore_event = ChoreEventType.OE_CXL_ACK
            cxl_ack_chore_journal.chore_event_date_time = DateTime.utcnow()
            cxl_ack_chore_journal.id = None
            executor_http_client.create_chore_journal_client(cxl_ack_chore_journal)

            cxled_qty = open_qty
            cxled_notional = open_notional
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                buy_residual_qty = cxled_qty
                buy_cxled_notional = cxled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    residual_qty=cxled_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_with_cxl_unack_pre_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["avoid_cxl_ack_after_cxl_req"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_px = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = ((buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            chore_status = ChoreStatusType.OE_CXL_UNACK
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_CXL_UNACK
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px)
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # placing CXL ACK
            cxl_ack_chore_journal = copy.deepcopy(latest_ack_obj)
            cxl_ack_chore_journal.chore_event = ChoreEventType.OE_CXL_ACK
            cxl_ack_chore_journal.chore_event_date_time = DateTime.utcnow()
            cxl_ack_chore_journal.id = None
            executor_http_client.create_chore_journal_client(cxl_ack_chore_journal)
            
            new_qty = qty
            new_px = px
            # amend_qty = None
            # amend_px = None
            chore_status = ChoreStatusType.OE_DOD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            cxled_qty = qty - filled_qty
            cxled_notional = cxled_qty * get_px_in_usd(px)
            cxled_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = (buy_qty - buy_filled_qty) * get_px_in_usd(buy_px) - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    rej_check=True)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_non_risky_amend_rej_based_on_px_and_qty_cxl_ack_pre_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_residual_qty = None
        buy_fill_notional = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                buy_fill_notional = filled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - filled_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            cxled_qty = open_qty
            cxled_notional = open_notional
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                buy_residual_qty = cxled_qty
                buy_cxled_notional = cxled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    residual_qty=cxled_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ chore
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    residual_qty=cxled_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = (f"Received AMD_REJ post chore DOD on chore_id: "
                         f".* - ignoring this chore_journal and chore will stay unchanged")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        
        
@pytest.mark.nightly
def test_risky_amend_rej_based_on_px_and_qty_cxl_ack_pre_amd_rej(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_residual_qty = None
        buy_fill_notional = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
                buy_amend_qty = amend_qty
                buy_amend_px = amend_px
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10
            else:
                new_qty = qty
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 0

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                buy_fill_notional = filled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # applying cxl req
            executor_http_client.barter_simulator_place_cxl_chore_query_client(
                latest_ack_obj.chore.chore_id, latest_ack_obj.chore.side, latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.security.sec_id, latest_ack_obj.chore.underlying_account)

            if side == Side.BUY:
                cxled_qty = open_qty
                cxled_notional = open_notional
            else:
                cxled_qty += open_qty
                cxled_notional += open_notional
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            residual_qty = open_qty
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                buy_residual_qty = cxled_qty
                buy_cxled_notional = cxled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional

            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, last_filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    residual_qty=residual_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend REJ chore
            executor_http_client.barter_simulator_process_amend_rej_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_REJ,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure,
                    residual_qty=residual_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            time.sleep(5)
            check_str = (f"Received AMD_REJ post chore DOD on chore_id: "
                         f".* - ignoring this chore_journal and chore will stay unchanged")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _test_avoid_same_amend(
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        last_barter_fixture_list, symbol_overview_obj_list, market_depth_basemodel_list,
        leg1_leg2_symbol_list, refresh_sec_update_fixture, do_amend_px: bool = False, do_amend_qty: bool = False):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            chore_id = latest_ack_obj.chore.chore_id
            chore_snapshot_before_amend = get_chore_snapshot_from_chore_id(chore_id,
                                                              executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)

            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
            else:
                amend_px = px + 1
                amend_qty = qty + 10
            if do_amend_qty and not do_amend_px:
                amend_qty = qty
            elif do_amend_px and not do_amend_qty:
                amend_px = px
            elif do_amend_px and do_amend_qty:
                amend_px = px
                amend_qty = qty

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            chore_snapshot_after_amend = get_chore_snapshot_from_chore_id(chore_id,
                                                              executor_http_client)

            assert chore_snapshot_before_amend == chore_snapshot_after_amend, \
                ("Mismatched: chore_snapshot must be unchanged before and after amend req with same qty or px, "
                 f"found {chore_snapshot_before_amend = }, {chore_snapshot_after_amend = }")

            time.sleep(5)
            check_str = (f"Found amend request for chore_id: .*, with "
                         f"amend request for qty or px, same as existing qty or px - avoiding amend request")
            assert_fail_msg = f"Can't find alert: {check_str!r}"
            check_alert_str_in_strat_alerts_n_portfolio_alerts(active_pair_strat.id, check_str, assert_fail_msg)

            if side == Side.BUY:
                time.sleep(residual_wait_sec)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_avoid_same_amend_based_on_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    _test_avoid_same_amend(pair_strat_, expected_strat_limits_, expected_strat_status_, last_barter_fixture_list,
                           symbol_overview_obj_list, market_depth_basemodel_list, leg1_leg2_symbol_list,
                           refresh_sec_update_fixture, do_amend_qty=True)


@pytest.mark.nightly
def test_avoid_same_amend_based_on_px(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    _test_avoid_same_amend(pair_strat_, expected_strat_limits_, expected_strat_status_, last_barter_fixture_list,
                           symbol_overview_obj_list, market_depth_basemodel_list, leg1_leg2_symbol_list,
                           refresh_sec_update_fixture, do_amend_px=True)


@pytest.mark.nightly
def test_avoid_same_amend_based_on_px_n_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    _test_avoid_same_amend(pair_strat_, expected_strat_limits_, expected_strat_status_, last_barter_fixture_list,
                           symbol_overview_obj_list, market_depth_basemodel_list, leg1_leg2_symbol_list,
                           refresh_sec_update_fixture, do_amend_px=True, do_amend_qty=True)


@pytest.mark.nightly
def test_non_risky_multi_amend_based_on_qty_and_px(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_qty = None
        buy_amend_qty = None
        buy_amend_px = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
                buy_qty = qty

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            for i in range(3):
                print(f"{i+1}th amend for side {side}")
                if i == 0:
                    new_qty = qty
                    new_px = px
                    total_amend_dn_qty = 0
                    total_amend_up_qty = 0
                else:
                    if side == Side.BUY:
                        new_qty = qty
                        new_px = amend_px
                        total_amend_dn_qty = 10 * i
                        total_amend_up_qty = 0
                        # cxled_qty = 10 * i
                        # cxled_px = px - (1 * (i-1))
                        # cxled_notional += 10 * get_px_in_usd(cxled_px)
                    else:
                        new_qty = amend_qty
                        new_px = amend_px
                        total_amend_dn_qty = 0
                        total_amend_up_qty = 10 * i
                        # cxled_qty = 0
                        # cxled_notional = 0
                        # cxled_px = 0
                        
                # Placing Amend req chore and checking computes should stay same since it is non-risky amend
                if side == Side.BUY:
                    amend_px = px - (1 * (i+1))
                    amend_qty = qty - (10 * (i+1))
                    buy_amend_qty = amend_qty
                    buy_amend_px = amend_px
                else:
                    amend_px = px + (1 * (i+1))
                    amend_qty = qty + (10 * (i+1))

                executor_http_client.barter_simulator_process_amend_req_query_client(
                    latest_ack_obj.chore.chore_id,
                    latest_ack_obj.chore.side,
                    latest_ack_obj.chore.security.sec_id,
                    latest_ack_obj.chore.underlying_account,
                    qty=amend_qty, px=amend_px)

                latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                        chore_symbol, executor_http_client)

                chore_status = ChoreStatusType.OE_AMD
                filled_notional = filled_qty * get_px_in_usd(px)
                filled_px = px
                open_qty = new_qty - filled_qty - cxled_qty
                open_px = new_px
                open_notional = open_qty * get_px_in_usd(open_px)
                if side == Side.BUY:
                    other_side_residual_qty = 0
                    other_side_fill_notional = 0
                    open_exposure = open_notional
                    filled_exposure = filled_notional
                    cxled_exposure = cxled_notional
                else:
                    other_side_residual_qty = buy_amend_qty - buy_filled_qty
                    buy_symbol_side_snapshot_list = (
                        executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                            buy_symbol, Side.BUY))
                    other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                    open_exposure = - open_notional
                    filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                    cxled_exposure = buy_cxled_notional - cxled_notional
                last_filled_qty = filled_qty
                try:
                    check_all_computes_for_amend(
                        active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                        new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                        last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                        filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                        other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
                except AssertionError as ass_e:
                    print("ASSERT", ass_e)
                    raise AssertionError(ass_e)
                except Exception as e:
                    print("Exception", e)
                    raise Exception(e)

                # Placing Amend ACK chore and checking amend should be applied on ack
                executor_http_client.barter_simulator_process_amend_ack_query_client(
                    latest_ack_obj.chore.chore_id,
                    latest_ack_obj.chore.side,
                    latest_ack_obj.chore.security.sec_id,
                    latest_ack_obj.chore.underlying_account)

                latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                      chore_symbol,
                                                                                      executor_http_client)
                if side == Side.BUY:
                    cxled_qty = 10 * (i + 1)
                    cxled_notional += 10 * get_px_in_usd(new_px)
                    cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
                    total_amend_dn_qty = 10 * (i + 1)
                    total_amend_up_qty = 0
                    new_qty = qty
                    last_original_qty = qty
                    last_original_px = new_px
                else:
                    last_original_qty = new_qty
                    last_original_px = new_px
                    new_qty = amend_qty
                    cxled_qty = 0
                    cxled_px = 0
                    cxled_notional = 0
                    total_amend_dn_qty = 0
                    total_amend_up_qty = 10 * (i + 1)

                new_px = amend_px
                chore_status = ChoreStatusType.OE_ACKED
                filled_notional = filled_qty * get_px_in_usd(px)
                filled_px = px
                open_qty = new_qty - filled_qty - cxled_qty
                open_px = amend_px
                open_notional = open_qty * get_px_in_usd(open_px)
                if side == Side.BUY:
                    other_side_residual_qty = 0
                    other_side_fill_notional = 0
                    open_exposure = open_notional
                    filled_exposure = filled_notional
                    cxled_exposure = cxled_notional
                else:
                    other_side_residual_qty = buy_amend_qty - buy_filled_qty
                    buy_symbol_side_snapshot_list = (
                        executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                            buy_symbol, Side.BUY))
                    other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                    open_exposure = - open_notional
                    filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                    cxled_exposure = buy_cxled_notional - cxled_notional
                last_filled_qty = filled_qty
                try:
                    check_all_computes_for_amend(
                        active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                        new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                        last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                        filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                        other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
                except AssertionError as ass_e:
                    print("ASSERT", ass_e)
                    raise AssertionError(ass_e)
                except Exception as e:
                    print("Exception", e)
                    raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty += open_qty
                cxled_notional += open_notional
                buy_cxled_notional = cxled_notional
                new_qty = qty
            else:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_risky_multi_amend_based_on_px_and_qty(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # buy test
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_filled_qty = None
        buy_px = None
        buy_amend_qty = None
        buy_cxled_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:
            if side == Side.BUY:
                buy_px = px
            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)

            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            expected_chore_notional = qty * get_px_in_usd(px)
            chore_snapshot = get_chore_snapshot_from_chore_id(latest_ack_obj.chore.chore_id,
                                                              executor_http_client)

            new_qty = qty
            new_px = px
            amend_qty = None
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_qty * get_px_in_usd(px)
                cxled_exposure = buy_cxled_notional
            last_original_px = None
            last_original_qty = None
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            for i in range(3):
                print(f"{i+1}th amend for side {side}")
                # Placing Amend req chore and checking computes should stay same since it is non-risky amend
                if side == Side.BUY:
                    amend_px = px + (i+1)
                    amend_qty = qty + (10 * (i+1))
                    buy_amend_qty = amend_qty
                    buy_amend_px = amend_px
                else:
                    amend_px = px - (i+1)
                    amend_qty = qty - (10 * (i+1))

                executor_http_client.barter_simulator_process_amend_req_query_client(
                    latest_ack_obj.chore.chore_id,
                    latest_ack_obj.chore.side,
                    latest_ack_obj.chore.security.sec_id,
                    latest_ack_obj.chore.underlying_account,
                    qty=amend_qty, px=amend_px)

                latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                        chore_symbol, executor_http_client)

                if side == Side.BUY:
                    new_qty = amend_qty
                    cxled_qty = 0
                    cxled_px = 0
                    cxled_notional = 0
                    total_amend_dn_qty = 0
                    total_amend_up_qty += 10
                    last_original_qty = qty + (10 * i)
                    last_original_px = px + i
                else:
                    new_qty = qty
                    cxled_qty += 10
                    cxled_notional += 10 * get_px_in_usd(px - i)
                    cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
                    total_amend_dn_qty += 10
                    total_amend_up_qty = 0
                    last_original_qty = qty
                    last_original_px = px - i

                new_px = amend_px
                chore_status = ChoreStatusType.OE_AMD
                filled_notional = filled_qty * get_px_in_usd(px)
                filled_px = px
                open_qty = new_qty - filled_qty - cxled_qty
                open_notional = open_qty * get_px_in_usd(amend_px)
                open_px = amend_px
                if side == Side.BUY:
                    other_side_residual_qty = 0
                    other_side_fill_notional = 0
                    open_exposure = open_notional
                    filled_exposure = filled_notional
                    cxled_exposure = cxled_notional
                else:
                    other_side_residual_qty = buy_amend_qty - buy_filled_qty
                    buy_symbol_side_snapshot_list = (
                        executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                            buy_symbol, Side.BUY))
                    other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                    open_exposure = - open_notional
                    filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                    cxled_exposure = buy_cxled_notional - cxled_notional
                last_filled_qty = filled_qty
                try:
                    check_all_computes_for_amend(
                        active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                        new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                        last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                        filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                        other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
                except AssertionError as ass_e:
                    print("ASSERT", ass_e)
                    raise AssertionError(ass_e)
                except Exception as e:
                    print("Exception", e)
                    raise Exception(e)

                # Placing Amend ACK chore and checking amend should be applied on ack
                executor_http_client.barter_simulator_process_amend_ack_query_client(
                    latest_ack_obj.chore.chore_id,
                    latest_ack_obj.chore.side,
                    latest_ack_obj.chore.security.sec_id,
                    latest_ack_obj.chore.underlying_account)

                latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                      chore_symbol,
                                                                                      executor_http_client)
                chore_status = ChoreStatusType.OE_ACKED
                try:
                    check_all_computes_for_amend(
                        active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                        new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                        last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                        filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                        other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
                except AssertionError as ass_e:
                    print("ASSERT", ass_e)
                    raise AssertionError(ass_e)
                except Exception as e:
                    print("Exception", e)
                    raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty
                cxled_qty = amend_qty - filled_qty
                cxled_notional = (amend_qty - filled_qty) * get_px_in_usd(amend_px)
                buy_cxled_notional = cxled_notional
            else:
                new_qty = qty
                cxled_qty += open_qty
                cxled_notional += open_notional
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional) / cxled_qty
            chore_status = ChoreStatusType.OE_DOD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = 0
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_amend_qty - buy_filled_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_filled_qty * get_px_in_usd(buy_px) - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_multi_amends_based_on_qty_n_then_px_1(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    Does multi-amend test - first amends non-risky qty to +-10 based on side, then risky qty to +-10, 
    then non-risky +-1 based on px and at last risky +-1 based on px
    """
    
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_cxled_notional = None
        buy_residual_qty = None
        buy_fill_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # First Handling Non-Risky amend Case for qty
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
            else:
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_notional
                cxled_exposure = 0
                buy_fill_notional = filled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_fill_notional - filled_qty * get_px_in_usd(px)
                cxled_exposure = buy_cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Risky amend Case for qty
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            # qty = new_qty
            if side == Side.BUY:
                amend_qty = new_qty + 10
                buy_amend_qty = amend_qty
            else:
                amend_qty = new_qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            last_qty = new_qty
            if side == Side.BUY:
                new_qty = amend_qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 20
            else:
                new_qty = new_qty
                cxled_qty = new_qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 10

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_AMD
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = last_qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = last_qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Non-Risky amend Case for px
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = new_px - 1
                buy_amend_px = amend_px
            else:
                amend_px = new_px + 1

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(open_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_px = amend_px
            last_original_qty = new_qty
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_px = amend_px
            open_notional = open_qty * get_px_in_usd(open_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Risky amend Case for px
            if side == Side.BUY:
                amend_px = new_px + 1
                buy_amend_px = amend_px
            else:
                amend_px = new_px - 1

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            last_original_px = new_px
            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            open_qty = new_qty - filled_qty - cxled_qty
            open_px = amend_px
            open_notional = open_qty * get_px_in_usd(open_px)
            last_original_qty = new_qty
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            cxled_notional += open_qty * get_px_in_usd(new_px)
            cxled_qty += open_qty
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional / cxled_qty)
            residual_qty = open_qty
            chore_status = ChoreStatusType.OE_DOD
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
                buy_cxled_notional = cxled_notional
                buy_residual_qty = residual_qty
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure, residual_qty=residual_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_multi_amends_based_on_qty_n_then_px_2(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    Does multi-amend test - first amends non-risky qty to +-10 based on side, then risky qty to +-10,
    then non-risky +-1 based on px and at last risky +-1 based on px
    """

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_cxled_notional = None
        buy_residual_qty = None
        buy_fill_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # First Handling Non-Risky amend Case for qty
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_qty = qty - 20
                buy_amend_qty = amend_qty
            else:
                amend_qty = qty + 20

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)
            new_qty = qty
            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_notional
                cxled_exposure = 0
                buy_fill_notional = filled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = buy_fill_notional - filled_qty * get_px_in_usd(px)
                cxled_exposure = buy_cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol, executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 20
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 20

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Risky amend Case for qty
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            # qty = new_qty
            if side == Side.BUY:
                amend_qty = qty - 10
                buy_amend_qty = amend_qty
            else:
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            last_qty = new_qty
            if side == Side.BUY:
                new_qty = amend_qty
                total_amend_dn_qty = 20
                total_amend_up_qty = 10
            else:
                new_qty = new_qty
                cxled_qty = new_qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 10
                total_amend_up_qty = 20

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_AMD
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = last_qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                new_qty = amend_qty

            new_px = px
            amend_px = None
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            last_original_qty = last_qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Non-Risky amend Case for px
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = new_px - 1
                buy_amend_px = amend_px
            else:
                amend_px = new_px + 1

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(open_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_px = amend_px
            last_original_qty = new_qty
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_px = amend_px
            open_notional = open_qty * get_px_in_usd(open_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Risky amend Case for px
            if side == Side.BUY:
                amend_px = new_px + 1
                buy_amend_px = amend_px
            else:
                amend_px = new_px - 1

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            last_original_px = new_px
            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            open_qty = new_qty - filled_qty - cxled_qty
            open_px = amend_px
            open_notional = open_qty * get_px_in_usd(open_px)
            last_original_qty = new_qty
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            cxled_notional += open_qty * get_px_in_usd(new_px)
            cxled_qty += open_qty
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional / cxled_qty)
            residual_qty = open_qty
            chore_status = ChoreStatusType.OE_DOD
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
                buy_cxled_notional = cxled_notional
                buy_residual_qty = residual_qty
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, None, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure, residual_qty=residual_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_multi_amends_based_on_qty_n_px(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_chore_, sell_chore_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_chore_snapshot_,
        expected_sell_chore_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_,
        last_barter_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_chore_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    Does multi-amend test - first does non-risky amends on qty and px and then does risky amend
    """

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["continues_chore_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_chore_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, executor_http_client)

        buy_cxled_notional = None
        buy_residual_qty = None
        buy_fill_notional = None
        for px, qty, chore_symbol, side in [(100, 90, buy_symbol, Side.BUY), (95, 110, sell_symbol, Side.SELL)]:

            place_new_chore(chore_symbol, side, px, qty, executor_http_client)

            # checking ACK chore before amend
            latest_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_ACK, chore_symbol,
                                                                            executor_http_client)
            filled_qty = get_partial_allowed_fill_qty(chore_symbol, config_dict, qty)
            if side == Side.BUY:
                buy_filled_qty = filled_qty

            # First Handling Non-Risky amend Case for qty
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            if side == Side.BUY:
                amend_px = px - 1
                amend_qty = qty - 10
            else:
                amend_px = px + 1
                amend_qty = qty + 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol,
                                                                                    executor_http_client)
            new_qty = qty
            new_px = px
            chore_status = ChoreStatusType.OE_AMD
            total_amend_dn_qty = 0
            total_amend_up_qty = 0
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = qty - filled_qty
            open_notional = open_qty * get_px_in_usd(px)
            open_px = px
            cxled_qty = 0
            cxled_notional = 0
            cxled_px = 0
            last_original_qty = None
            last_original_px = None
            if side == Side.BUY:
                buy_fill_notional = filled_notional
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = (qty - filled_qty) * get_px_in_usd(px)
                filled_exposure = filled_qty * get_px_in_usd(px)
                cxled_exposure = 0
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            if side == Side.BUY:
                cxled_qty = qty - amend_qty
                cxled_px = px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                new_qty = qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 0
            else:
                new_qty = amend_qty
                cxled_qty = 0
                cxled_px = 0
                cxled_notional = 0
                total_amend_dn_qty = 0
                total_amend_up_qty = 10

            new_px = amend_px
            chore_status = ChoreStatusType.OE_ACKED
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            last_original_qty = qty
            last_original_px = px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Next, Handling Risky amend Case for qty
            # Placing Amend req chore and checking computes should stay same since it is non-risky amend
            # qty = new_qty

            last_original_qty = new_qty
            last_original_px = new_px

            if side == Side.BUY:
                amend_px = px + 1
                amend_qty = qty + 10
            else:
                amend_px = px - 1
                amend_qty = qty - 10

            executor_http_client.barter_simulator_process_amend_req_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account,
                qty=amend_qty, px=amend_px)

            latest_amend_unack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_UNACK,
                                                                                    chore_symbol, executor_http_client)

            if side == Side.BUY:
                new_qty = amend_qty
                total_amend_dn_qty = 10
                total_amend_up_qty = 20
            else:
                cxled_qty = new_qty - amend_qty
                cxled_px = new_px
                cxled_notional = cxled_qty * get_px_in_usd(cxled_px)
                total_amend_dn_qty = 20
                total_amend_up_qty = 10

            new_px = amend_px
            chore_status = ChoreStatusType.OE_AMD
            filled_notional = filled_qty * get_px_in_usd(px)
            filled_px = px
            open_qty = new_qty - filled_qty - cxled_qty
            open_notional = open_qty * get_px_in_usd(amend_px)
            open_px = amend_px
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # Placing Amend ACK chore and checking amend should be applied on ack
            executor_http_client.barter_simulator_process_amend_ack_query_client(
                latest_ack_obj.chore.chore_id,
                latest_ack_obj.chore.side,
                latest_ack_obj.chore.security.sec_id,
                latest_ack_obj.chore.underlying_account)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_AMD_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)

            chore_status = ChoreStatusType.OE_ACKED

            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = filled_notional
                cxled_exposure = cxled_notional
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = - open_notional
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure, cxled_exposure)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

            # waiting for chore to get cxled
            time.sleep(residual_wait_sec)

            latest_amend_ack_obj = get_latest_chore_journal_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                                  chore_symbol,
                                                                                  executor_http_client)
            cxled_notional += open_qty * get_px_in_usd(new_px)
            cxled_qty += open_qty
            cxled_px = get_usd_to_local_px_or_notional(cxled_notional / cxled_qty)
            residual_qty = open_qty
            chore_status = ChoreStatusType.OE_DOD
            open_qty = 0
            open_notional = 0
            open_px = 0
            if side == Side.BUY:
                other_side_residual_qty = 0
                other_side_fill_notional = 0
                open_exposure = open_notional
                filled_exposure = buy_fill_notional
                cxled_exposure = cxled_notional
                buy_cxled_notional = cxled_notional
                buy_residual_qty = residual_qty
            else:
                other_side_residual_qty = buy_residual_qty
                buy_symbol_side_snapshot_list = (
                    executor_http_client.get_symbol_side_snapshot_from_symbol_side_query_client(
                        buy_symbol, Side.BUY))
                other_side_fill_notional = buy_symbol_side_snapshot_list[0].total_fill_notional
                open_exposure = 0
                filled_exposure = buy_fill_notional - filled_notional
                cxled_exposure = buy_cxled_notional - cxled_notional
            last_filled_qty = filled_qty
            try:
                check_all_computes_for_amend(
                    active_pair_strat.id, chore_symbol, side, latest_ack_obj.chore.chore_id, executor_http_client,
                    new_qty, new_px, amend_qty, amend_px, chore_status, total_amend_dn_qty, total_amend_up_qty,
                    last_original_qty, last_original_px, open_qty, open_notional, open_px, filled_qty,
                    filled_notional, filled_px, filled_qty, cxled_qty, cxled_notional, cxled_px,
                    other_side_residual_qty, other_side_fill_notional, open_exposure, filled_exposure,
                    cxled_exposure, residual_qty=residual_qty)
            except AssertionError as ass_e:
                print("ASSERT", ass_e)
                raise AssertionError(ass_e)
            except Exception as e:
                print("Exception", e)
                raise Exception(e)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        err_str_ = (f"Some Error Occurred: exception: {e}, "
                    f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        print(err_str_)
        raise Exception(err_str_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# def test_log_barter_simulator_trigger_kill_switch_and_resume_bartering():
#     log_dir: PurePath = PurePath(
#         __file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "phone_book" / "log "
#     configure_logger("debug", str(log_dir), "test_log_barter_simulator.log")
#
#     LogBarterSimulator.trigger_kill_switch()
#     time.sleep(5)
#
#     portfolio_status_id = 1
#     portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(portfolio_status_id)
#     assert portfolio_status.kill_switch
#
#     LogBarterSimulator.revoke_kill_switch_n_resume_bartering()
#     time.sleep(5)
#
#     portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(portfolio_status_id)
#     assert not portfolio_status.kill_switch

