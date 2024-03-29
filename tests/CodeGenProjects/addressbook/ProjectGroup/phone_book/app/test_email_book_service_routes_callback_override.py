# standard imports
import math
import concurrent.futures
import time

import numpy as np
import pytest
import random
import traceback

# project imports
from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.phone_book_service_helper import get_strat_key_from_pair_strat
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import AlertOptional
from Flux.CodeGenProjects.addressbook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *

email_book_service_beanie_web_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient.set_or_get_if_instance_exists(HOST, parse_to_int(PAIR_STRAT_BEANIE_PORT))
email_book_service_cache_web_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient.set_or_get_if_instance_exists(HOST, parse_to_int(PAIR_STRAT_CACHE_PORT))

if email_book_service_beanie_web_client.port == email_book_service_native_web_client.port:
    clients_list = [email_book_service_beanie_web_client]
else:
    clients_list = [email_book_service_beanie_web_client, email_book_service_cache_web_client]


# test cases requires phone_book and log_book database to be present
def _test_deep_clean_database_n_logs():
    drop_all_databases()
    clean_project_logs()


def _test_clean_database_n_logs():
    clean_all_collections_ignoring_ui_layout([])
    clean_project_logs()


def _test_sanity_create_strat_parallel(static_data_, clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
                                       expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
                                       top_of_book_list_, market_depth_basemodel_list):
    max_count = int(len(buy_sell_symbol_list)/2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_count) as executor:
        results = [executor.submit(create_n_activate_strat, buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_start_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(top_of_book_list_), copy.deepcopy(market_depth_basemodel_list))
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
def test_create_get_put_patch_delete_order_limits_client(clean_and_set_limits, web_client):
    for index, return_type_param in enumerate([True, None, False]):
        order_limits_obj = OrderLimitsBaseModel(id=2 + index, max_px_deviation=2)
        # testing create_order_limits_client()
        created_order_limits_obj = web_client.create_order_limits_client(order_limits_obj,
                                                                         return_obj_copy=return_type_param)
        if return_type_param:
            assert created_order_limits_obj == order_limits_obj, \
                f"Created obj {created_order_limits_obj} mismatched expected order_limits_obj {order_limits_obj}"
        else:
            assert created_order_limits_obj

        # checking if created obj present in get_all objects
        fetched_order_limits_list = web_client.get_all_order_limits_client()
        assert order_limits_obj in fetched_order_limits_list, \
            f"Couldn't find expected order_limits_obj {order_limits_obj} in get-all fetched list of objects"

        # Checking get_by_id client
        fetched_order_limits_obj = web_client.get_order_limits_client(order_limits_obj.id)
        assert fetched_order_limits_obj == order_limits_obj, \
            f"Mismatched expected order_limits_obj {order_limits_obj} from " \
            f"fetched_order_limits obj fetched by get_by_id {fetched_order_limits_obj}"

        # checking put operation client
        order_limits_obj.max_basis_points = 2
        updated_order_limits_obj = web_client.put_order_limits_client(order_limits_obj,
                                                                      return_obj_copy=return_type_param)
        if return_type_param:
            assert updated_order_limits_obj == order_limits_obj, \
                f"Mismatched expected order_limits_obj: {order_limits_obj} from updated obj: {updated_order_limits_obj}"
        else:
            assert updated_order_limits_obj

        # checking patch operation client
        patch_order_limits_obj = OrderLimitsBaseModel(id=order_limits_obj.id, max_px_levels=2)
        # making changes to expected_obj
        order_limits_obj.max_px_levels = patch_order_limits_obj.max_px_levels

        patch_updated_order_limits_obj = \
            web_client.patch_order_limits_client(json.loads(patch_order_limits_obj.model_dump_json(by_alias=True,
                                                                                                   exclude_none=True)),
                                                 return_obj_copy=return_type_param)
        if return_type_param:
            assert patch_updated_order_limits_obj == order_limits_obj, \
                f"Mismatched expected obj: {order_limits_obj} from patch updated obj {patch_updated_order_limits_obj}"
        else:
            assert patch_updated_order_limits_obj

        # checking delete operation client
        delete_resp = web_client.delete_order_limits_client(order_limits_obj.id, return_obj_copy=return_type_param)
        if return_type_param:
            assert isinstance(delete_resp, dict), \
                f"Mismatched type of delete resp, expected dict received {type(delete_resp)}"
            assert delete_resp.get("id") == order_limits_obj.id, \
                f"Mismatched delete resp id, expected {order_limits_obj.id} received {delete_resp.get('id')}"
        else:
            assert delete_resp


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_post_all(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        order_limits_objects_list = [
            OrderLimitsBaseModel(id=2 + (index * 3), max_px_deviation=2),
            OrderLimitsBaseModel(id=3 + (index * 3), max_px_deviation=3),
            OrderLimitsBaseModel(id=4 + (index * 3), max_px_deviation=4)
        ]

        fetched_email_book_beanie = web_client.get_all_order_limits_client()

        for obj in order_limits_objects_list:
            assert obj not in fetched_email_book_beanie, f"Object {obj} must not be present in get-all list " \
                                                            f"{fetched_email_book_beanie} before post-all operation"

        return_value = web_client.create_all_order_limits_client(order_limits_objects_list,
                                                                 return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        fetched_email_book_beanie = web_client.get_all_order_limits_client()

        for obj in order_limits_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"


@pytest.mark.nightly
@pytest.mark.parametrize("web_client", clients_list)
def test_put_all(clean_and_set_limits, web_client):
    for index, return_value_type in enumerate([True, None, False]):
        order_limits_objects_list = [
            OrderLimitsBaseModel(id=2 + (index * 3), max_px_deviation=2),
            OrderLimitsBaseModel(id=3 + (index * 3), max_px_deviation=3),
            OrderLimitsBaseModel(id=4 + (index * 3), max_px_deviation=4)
        ]

        web_client.create_all_order_limits_client(order_limits_objects_list)

        fetched_email_book_beanie = web_client.get_all_order_limits_client()

        for obj in order_limits_objects_list:
            assert obj in fetched_email_book_beanie, f"Couldn't find object {obj} in get-all list " \
                                                        f"{fetched_email_book_beanie}"

        # updating values
        for obj in order_limits_objects_list:
            obj.max_contract_qty = obj.id

        return_value = web_client.put_all_order_limits_client(order_limits_objects_list,
                                                              return_obj_copy=return_value_type)
        if return_value_type:
            assert isinstance(return_value, List), ("Mismatched: returned value from client must be list, "
                                                    f"received type: {type(return_value)}")
        else:
            assert return_value

        updated_order_limits_list = web_client.get_all_order_limits_client()

        for expected_obj in order_limits_objects_list:
            assert expected_obj in updated_order_limits_list, \
                f"expected obj {expected_obj} not found in updated list of objects: {updated_order_limits_list}"


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
        # testing create_order_limits_client()
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
                           top_of_book_list_, market_depth_basemodel_list):
    # creates and activates multiple pair_strats
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        create_n_activate_strat(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                expected_strat_status_, symbol_overview_obj_list, top_of_book_list_,
                                market_depth_basemodel_list)


def _place_sanity_orders(buy_symbol, sell_symbol, pair_strat_,
                         expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                         last_trade_fixture_list, market_depth_basemodel_list,
                         top_of_book_list_, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 111360
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.trade_simulator_reload_config_query_client()

        total_order_count_for_each_side = max_loop_count_per_side

        # Placing buy orders
        buy_ack_order_id = None
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                               buy_symbol, executor_web_client,
                                                                               last_order_id=buy_ack_order_id)
            buy_ack_order_id = ack_order_journal.order.order_id

            if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                # Sleeping to let the order get cxlled
                time.sleep(residual_wait_sec)

        # Placing sell orders
        sell_ack_order_id = None
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
            run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                               sell_symbol, executor_web_client,
                                                                               last_order_id=sell_ack_order_id)
            sell_ack_order_id = ack_order_journal.order.order_id

            if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                # Sleeping to let the order get cxlled
                time.sleep(residual_wait_sec)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


# sanity test to create orders
@pytest.mark.nightly
def test_place_sanity_orders(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                             expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                             last_trade_fixture_list, market_depth_basemodel_list,
                             top_of_book_list_, buy_order_, sell_order_,
                             max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    _place_sanity_orders(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
                         symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                         top_of_book_list_, max_loop_count_per_side, refresh_sec_update_fixture)


def test_place_sanity_parallel_orders(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                      expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                      last_trade_fixture_list, market_depth_basemodel_list,
                                      top_of_book_list_, buy_order_, sell_order_,
                                      max_loop_count_per_side, refresh_sec_update_fixture):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_orders, leg1_symbol, leg2_symbol, copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_trade_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   copy.deepcopy(top_of_book_list_), max_loop_count_per_side,
                                   refresh_sec_update_fixture)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _place_sanity_complete_buy_orders(buy_symbol, sell_symbol, pair_strat_,
                                      expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                      last_trade_fixture_list, market_depth_basemodel_list,
                                      top_of_book_list_, max_loop_count_per_side, refresh_sec_update_fixture):
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 111360
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.trade_simulator_reload_config_query_client()

        total_order_count_for_each_side = max_loop_count_per_side

        # Placing buy orders
        buy_ack_order_id = None
        px = 10
        qty = 90
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
            # run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])

            buy_order: NewOrderBaseModel = place_new_order(buy_symbol, Side.BUY, px, qty, executor_web_client)

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                               buy_symbol, executor_web_client,
                                                                               last_order_id=buy_ack_order_id)
            buy_ack_order_id = ack_order_journal.order.order_id
            # fills_journal = get_latest_fill_journal_from_order_id(buy_ack_order_id, executor_web_client)
        return buy_symbol, sell_symbol, created_pair_strat, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _place_sanity_complete_sell_orders(buy_symbol, sell_symbol, created_pair_strat,
                                       last_trade_fixture_list, max_loop_count_per_side, executor_web_client):

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.trade_simulator_reload_config_query_client()

        total_order_count_for_each_side = max_loop_count_per_side

        # Placing sell orders
        sell_ack_order_id = None
        px = 110
        qty = 7
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
            sell_order: OrderJournal = place_new_order(sell_symbol, Side.SELL, px, qty, executor_web_client)

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                               sell_symbol, executor_web_client,
                                                                               last_order_id=sell_ack_order_id)
            sell_ack_order_id = ack_order_journal.order.order_id
            # fills_journal = get_latest_fill_journal_from_order_id(sell_ack_order_id, executor_web_client)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_place_sanity_parallel_complete_orders(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_,
        max_loop_count_per_side, refresh_sec_update_fixture):
    temp_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(_place_sanity_complete_buy_orders, leg1_symbol, leg2_symbol, copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(last_trade_fixture_list), copy.deepcopy(market_depth_basemodel_list),
                                   copy.deepcopy(top_of_book_list_), max_loop_count_per_side,
                                   refresh_sec_update_fixture)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client = future.result()
            temp_list.append((buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client))

    px = 10
    qty = 90
    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert portfolio_status.overall_buy_notional == 10 * 10 * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_buy_notional must be {10 * 10 * qty * get_px_in_usd(px)}, found "
         f"{portfolio_status.overall_buy_notional}")
    assert portfolio_status.overall_buy_fill_notional == 10 * 10 * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_buy_fill_notional must be {10 * 10 * qty * get_px_in_usd(px)}, "
         f"found {portfolio_status.overall_buy_fill_notional}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(temp_list)) as executor:
        results = [executor.submit(_place_sanity_complete_sell_orders, buy_symbol_, sell_symbol_,
                                   created_pair_strat, copy.deepcopy(last_trade_fixture_list),
                                   max_loop_count_per_side, executor_web_client)
                   for buy_symbol_, sell_symbol_, created_pair_strat, executor_web_client in temp_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    px = 110
    qty = 7
    portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(1)
    assert portfolio_status.overall_sell_notional == 10 * 10 * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_sell_notional must be {10 * 10 * qty * get_px_in_usd(px)}, found "
         f"{portfolio_status.overall_sell_notional}")
    assert portfolio_status.overall_sell_fill_notional == 10 * 10 * qty * get_px_in_usd(px), \
        (f"Mismatched: overall_sell_fill_notional must be {10 * 10 * qty * get_px_in_usd(px)}, "
         f"found {portfolio_status.overall_sell_fill_notional}")
    return created_pair_strat, executor_web_client



# Test for some manual check - not checking anything functionally
# def handle_test_buy_sell_with_sleep_delays(buy_symbol: str, sell_symbol: str, pair_strat_: PairStratBaseModel,
#                                            expected_strat_limits_: StratLimits,
#                                            expected_strat_status_: StratStatus,
#                                            last_trade_fixture_list: List[Dict],
#                                            symbol_overview_obj_list: List[SymbolOverviewBaseModel],
#                                            market_depth_basemodel_list: List[MarketDepthBaseModel],
#                                            top_of_book_list_: List[Dict]):
#     order_counts = 10
#     active_strat, executor_web_client = (
#         create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
#                                            expected_strat_status_, symbol_overview_obj_list,
#                                            last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))
#
#     for order_count in range(order_counts):
#         # Buy Order
#         run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
#         print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
#         # Running TopOfBook (this triggers expected buy order)
#         run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], False)
#
#         # Sell Order
#         run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
#         print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
#         # Running TopOfBook (this triggers expected buy order)
#         run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1], False)
#
#         time.sleep(10)
#
#
# def test_place_sanity_orders_with_sleep_delays(clean_and_set_limits, buy_sell_symbol_list, pair_strat_,
#                                                expected_strat_limits_,
#                                                expected_strat_status_, last_trade_fixture_list,
#                                                symbol_overview_obj_list, market_depth_basemodel_list,
#                                                top_of_book_list_):
#     symbol_pair_counter = 1
#     with concurrent.futures.ThreadPoolExecutor(max_workers=len(buy_sell_symbol_list)) as executor:
#         results = [executor.submit(handle_test_buy_sell_with_sleep_delays, buy_symbol, sell_symbol,
#                                    pair_strat_, expected_strat_limits_, expected_strat_status_,
#                                    last_trade_fixture_list, symbol_overview_obj_list, market_depth_basemodel_list,
#                                    top_of_book_list_)
#                    for buy_symbol, sell_symbol in buy_sell_symbol_list]
#
#         for future in concurrent.futures.as_completed(results):
#             if future.exception() is not None:
#                 raise Exception(future.exception())


# def test_create_sanity_last_trade(static_data_, clean_and_set_limits, last_trade_fixture_list):
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
#             last_trade_obj = LastTradeBaseModel(**last_trade_fixture_list[0])
#             last_trade_obj.symbol_n_exch_id.symbol = symbol
#             last_trade_obj.arrival_time = current_time
#             last_trade_obj.px = random.randint(px_portion[0], px_portion[1])
#             last_trade_obj.qty = qty
#
#             mobile_book_web_client.create_last_trade_client(last_trade_obj)
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
def test_buy_sell_order_multi_pair_serialized(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                                              buy_order_, sell_order_, buy_fill_journal_,
                                              sell_fill_journal_, expected_buy_order_snapshot_,
                                              expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
                                              pair_strat_, expected_strat_limits_, expected_strat_status_,
                                              expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                                              last_trade_fixture_list, symbol_overview_obj_list,
                                              market_depth_basemodel_list, expected_order_limits_,
                                              expected_portfolio_limits_, max_loop_count_per_side,
                                              leg1_leg2_symbol_list, refresh_sec_update_fixture):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:int(len(leg1_leg2_symbol_list) / 2)]
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = (
            handle_test_buy_sell_order(leg1_symbol, leg2_symbol, max_loop_count_per_side,
                                       refresh_sec_update_fixture, buy_order_, sell_order_, buy_fill_journal_,
                                       sell_fill_journal_, expected_buy_order_snapshot_, expected_sell_order_snapshot_,
                                       expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_,
                                       expected_strat_status_, expected_strat_brief_,
                                       top_of_book_list_, last_trade_fixture_list, symbol_overview_obj_list,
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
def test_buy_sell_order_multi_pair_parallel(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                                            buy_order_, sell_order_, buy_fill_journal_,
                                            sell_fill_journal_, expected_buy_order_snapshot_,
                                            expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
                                            pair_strat_, expected_strat_limits_, expected_strat_status_,
                                            expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                                            last_trade_fixture_list, symbol_overview_obj_list,
                                            market_depth_basemodel_list, expected_order_limits_,
                                            expected_portfolio_limits_, max_loop_count_per_side,
                                            leg1_leg2_symbol_list, refresh_sec_update_fixture):
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_buy_sell_order, leg1_symbol, leg2_symbol, max_loop_count_per_side,
                                   refresh_sec_update_fixture, copy.deepcopy(buy_order_),
                                   copy.deepcopy(sell_order_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_order_snapshot_),
                                   copy.deepcopy(expected_sell_order_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(top_of_book_list_),
                                   copy.deepcopy(last_trade_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), False)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

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
def test_sell_buy_order_multi_pair_parallel(static_data_, clean_and_set_limits, pair_securities_with_sides_,
                                            buy_order_, sell_order_, buy_fill_journal_,
                                            sell_fill_journal_, expected_buy_order_snapshot_,
                                            expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
                                            pair_strat_, expected_strat_limits_, expected_strat_status_,
                                            expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                                            last_trade_fixture_list, symbol_overview_obj_list,
                                            market_depth_basemodel_list, expected_order_limits_,
                                            expected_portfolio_limits_, max_loop_count_per_side,
                                            leg1_leg2_symbol_list, refresh_sec_update_fixture):
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_sell_buy_order, leg1_symbol, leg2_symbol, max_loop_count_per_side,
                                   refresh_sec_update_fixture, copy.deepcopy(buy_order_),
                                   copy.deepcopy(sell_order_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_order_snapshot_),
                                   copy.deepcopy(expected_sell_order_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(expected_portfolio_status_), copy.deepcopy(top_of_book_list_),
                                   copy.deepcopy(last_trade_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), False)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

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
def test_buy_sell_non_systematic_order_multi_pair_serialized(static_data_, clean_and_set_limits,
                                                             pair_securities_with_sides_,
                                                             buy_order_, sell_order_, buy_fill_journal_,
                                                             sell_fill_journal_, expected_buy_order_snapshot_,
                                                             expected_sell_order_snapshot_,
                                                             expected_symbol_side_snapshot_,
                                                             pair_strat_, expected_strat_limits_,
                                                             expected_strat_status_,
                                                             expected_strat_brief_, expected_portfolio_status_,
                                                             top_of_book_list_,
                                                             last_trade_fixture_list, symbol_overview_obj_list,
                                                             market_depth_basemodel_list, expected_order_limits_,
                                                             expected_portfolio_limits_, max_loop_count_per_side,
                                                             leg1_leg2_symbol_list, refresh_sec_update_fixture):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:int(len(leg1_leg2_symbol_list) / 2)]
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        strat_buy_notional, strat_sell_notional, strat_buy_fill_notional, strat_sell_fill_notional = (
            handle_test_buy_sell_order(leg1_symbol, leg2_symbol, max_loop_count_per_side,
                                       refresh_sec_update_fixture, buy_order_, sell_order_, buy_fill_journal_,
                                       sell_fill_journal_, expected_buy_order_snapshot_, expected_sell_order_snapshot_,
                                       expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_,
                                       expected_strat_status_, expected_strat_brief_,
                                       top_of_book_list_, last_trade_fixture_list, symbol_overview_obj_list,
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
def test_buy_sell_non_systematic_order_multi_pair_parallel(static_data_, clean_and_set_limits,
                                                           pair_securities_with_sides_,
                                                           buy_order_, sell_order_, buy_fill_journal_,
                                                           sell_fill_journal_, expected_buy_order_snapshot_,
                                                           expected_sell_order_snapshot_,
                                                           expected_symbol_side_snapshot_,
                                                           pair_strat_, expected_strat_limits_, expected_strat_status_,
                                                           expected_strat_brief_, expected_portfolio_status_,
                                                           top_of_book_list_,
                                                           last_trade_fixture_list, symbol_overview_obj_list,
                                                           market_depth_basemodel_list, expected_order_limits_,
                                                           expected_portfolio_limits_, max_loop_count_per_side,
                                                           leg1_leg2_symbol_list, refresh_sec_update_fixture):
    overall_buy_notional = 0
    overall_sell_notional = 0
    overall_buy_fill_notional = 0
    overall_sell_fill_notional = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(handle_test_buy_sell_order, buy_symbol, sell_symbol, max_loop_count_per_side,
                                   refresh_sec_update_fixture, copy.deepcopy(buy_order_),
                                   copy.deepcopy(sell_order_), copy.deepcopy(buy_fill_journal_),
                                   copy.deepcopy(sell_fill_journal_), copy.deepcopy(expected_buy_order_snapshot_),
                                   copy.deepcopy(expected_sell_order_snapshot_),
                                   copy.deepcopy(expected_symbol_side_snapshot_), copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_),
                                   copy.deepcopy(expected_strat_status_), copy.deepcopy(expected_strat_brief_),
                                   copy.deepcopy(top_of_book_list_),
                                   copy.deepcopy(last_trade_fixture_list), copy.deepcopy(symbol_overview_obj_list),
                                   copy.deepcopy(market_depth_basemodel_list), True)
                   for buy_symbol, sell_symbol in leg1_leg2_symbol_list]

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
def test_buy_sell_pair_order(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_order_, sell_order_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_order_snapshot_,
        expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
        last_trade_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_order_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    triggers buy & sell pair order (single buy order followed by single sell order) for max_loop_count_per_side times
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]
    leg1_symbol, leg2_symbol = leg1_leg2_symbol_list[0]
    overall_buy_notional, overall_sell_notional, overall_buy_fill_notional, overall_sell_fill_notional = (
        handle_test_buy_sell_pair_order(
            leg1_symbol, leg2_symbol, max_loop_count_per_side,
            refresh_sec_update_fixture, buy_order_, sell_order_, buy_fill_journal_,
            sell_fill_journal_, expected_buy_order_snapshot_, expected_sell_order_snapshot_,
            expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_,
            expected_strat_status_, expected_strat_brief_,
            top_of_book_list_, last_trade_fixture_list, symbol_overview_obj_list,
            market_depth_basemodel_list))

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_sell_buy_pair_order(
        static_data_, clean_and_set_limits, pair_securities_with_sides_,
        buy_order_, sell_order_, buy_fill_journal_,
        sell_fill_journal_, expected_buy_order_snapshot_,
        expected_sell_order_snapshot_, expected_symbol_side_snapshot_,
        pair_strat_, expected_strat_limits_, expected_strat_status_,
        expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
        last_trade_fixture_list, symbol_overview_obj_list,
        market_depth_basemodel_list, expected_order_limits_,
        expected_portfolio_limits_, max_loop_count_per_side,
        leg1_leg2_symbol_list, refresh_sec_update_fixture):
    """
    triggers buy & sell pair order (single buy order followed by single sell order) for max_loop_count_per_side times
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]
    leg1_symbol, leg2_symbol = leg1_leg2_symbol_list[0]
    overall_buy_notional, overall_sell_notional, overall_buy_fill_notional, overall_sell_fill_notional = (
        handle_test_sell_buy_pair_order(
            leg1_symbol, leg2_symbol, max_loop_count_per_side,
            refresh_sec_update_fixture, buy_order_, sell_order_, buy_fill_journal_,
            sell_fill_journal_, expected_buy_order_snapshot_, expected_sell_order_snapshot_,
            expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_,
            expected_strat_status_, expected_strat_brief_,
            top_of_book_list_, last_trade_fixture_list, symbol_overview_obj_list,
            market_depth_basemodel_list))

    expected_portfolio_status_.overall_buy_notional = overall_buy_notional
    expected_portfolio_status_.overall_sell_notional = overall_sell_notional
    expected_portfolio_status_.overall_buy_fill_notional = overall_buy_fill_notional
    expected_portfolio_status_.overall_sell_fill_notional = overall_sell_fill_notional
    verify_portfolio_status(expected_portfolio_status_)


@pytest.mark.nightly
def test_trigger_kill_switch_systematic(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                        expected_strat_limits_, expected_strat_status_,
                                        symbol_overview_obj_list, last_trade_fixture_list,
                                        market_depth_basemodel_list, top_of_book_list_, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    # positive test
    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[0])

    # internally checks order_journal existence
    order_journal: OrderJournal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                                 leg1_symbol, executor_web_client)

    # negative test
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"

    time.sleep(2)
    # validating if trading_link.trigger_kill_switch got called
    check_str = "Called TradingLink.trigger_kill_switch"
    portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, f"Can't find portfolio alert saying '{check_str}'"

    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[0])
    # internally checking buy order
    order_journal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg1_symbol, executor_web_client,
                                                       last_order_id=order_journal.order.order_id,
                                                       expect_no_order=True)

    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[1])
    # internally checking sell order
    order_journal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client, expect_no_order=True)


@pytest.mark.nightly
def test_trigger_kill_switch_non_systematic(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                            pair_strat_, expected_strat_limits_,
                                            expected_strat_status_, symbol_overview_obj_list,
                                            last_trade_fixture_list, market_depth_basemodel_list,
                                            top_of_book_list_, buy_order_, sell_order_,
                                            refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))
    # positive test
    # placing buy order
    place_new_order(leg1_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty, executor_web_client)
    time.sleep(2)
    # internally checking buy order
    order_journal: OrderJournal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg1_symbol, executor_web_client)

    # negative test
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"

    time.sleep(5)
    # validating if trading_link.trigger_kill_switch got called
    check_str = "Called TradingLink.trigger_kill_switch"
    portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, f"Can't find portfolio alert saying '{check_str}'"

    # placing buy order
    place_new_order(leg1_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty, executor_web_client)
    time.sleep(2)
    # internally checking buy order
    order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                   leg1_symbol, executor_web_client,
                                                                   last_order_id=order_journal.order.order_id,
                                                                   expect_no_order=True)

    # placing sell order
    place_new_order(leg2_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty, executor_web_client)
    time.sleep(2)
    # internally checking sell order
    order_journal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client, expect_no_order=True)


@pytest.mark.nightly
def test_revoke_kill_switch(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                            expected_strat_limits_, expected_strat_status_,
                            symbol_overview_obj_list, last_trade_fixture_list,
                            market_depth_basemodel_list, top_of_book_list_, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    # positive test
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"

    time.sleep(2)
    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[0])
    # internally checking buy order
    order_journal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg1_symbol, executor_web_client, expect_no_order=True)

    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[1])
    # internally checking sell order
    order_journal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client, expect_no_order=True)

    # negative test
    system_control = SystemControlBaseModel(_id=1, kill_switch=False)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert not updated_system_control.kill_switch, "Unexpected: kill_switch is True, expected to be False"

    time.sleep(2)
    # validating if trading_link.trigger_kill_switch got called
    check_str = "Called TradingLink.revoke_kill_switch_n_resume_trading"
    portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
    for alert in portfolio_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, f"Can't find portfolio alert saying '{check_str}'"

    # empty sell tob to align tob pattern - self._top_of_books_update_date_time in street_book doesn't get updated
    # when kill switch is enabled, to make is aligned with last_update_time placing non-order triggering tob once
    # kill switch revoked
    run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[0], avoid_order_trigger=True)

    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[0])

    # internally checks order_journal existence
    order_journal: OrderJournal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                                 leg1_symbol, executor_web_client)
    time.sleep(residual_wait_sec)

    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_web_client, top_of_book_list_[1])
    # internally checking sell order
    order_journal = \
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                       leg2_symbol, executor_web_client)


@pytest.mark.nightly
def test_trigger_switch_fail(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list,
        market_depth_basemodel_list, top_of_book_list_):

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
            if "trading_link.trigger_kill_switch failed" not in str(e):
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
        symbol_overview_obj_list, last_trade_fixture_list,
        market_depth_basemodel_list, top_of_book_list_):
    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    updated_system_control = email_book_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))
    assert updated_system_control.kill_switch, "Unexpected: kill_switch is False, expected to be True"
    try:
        # updating yaml_configs according to this test
        config_dict["revoke_kill_switch_n_resume_trading"] = False
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()

        try:
            system_control = SystemControlBaseModel(_id=1, kill_switch=False)
            email_book_service_native_web_client.patch_system_control_client(
                jsonable_encoder(system_control, by_alias=True, exclude_none=True))
        except Exception as e:
            if "trading_link.revoke_kill_switch_n_resume_trading failed" not in str(e):
                raise Exception("Something went wrong while disabling kill_switch kill switch")
        else:
            assert False, ("Configured simulate config to return False from revoke_kill_switch_n_resume_trading to "
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
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
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
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

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
            executor_http_client.trade_simulator_reload_config_query_client()

            # buy fills check
            for check_symbol in [leg1_symbol, leg2_symbol]:
                order_id = None
                total_partial_filled_qty = 0
                for loop_count in range(1, max_loop_count_per_side + 1):
                    order_id, partial_filled_qty = \
                        underlying_handle_simulated_partial_fills_test(loop_count, check_symbol, leg1_symbol,
                                                                       leg2_symbol,
                                                                       last_trade_fixture_list, top_of_book_list_,
                                                                       order_id, config_dict, executor_http_client)
                    total_partial_filled_qty += partial_filled_qty
                    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                        # Sleeping to let the order get cxlled
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
                                       last_trade_fixture_list, market_depth_basemodel_list,
                                       top_of_book_list_, buy_order_, sell_order_,
                                       max_loop_count_per_side, refresh_sec_update_fixture):

    partial_filled_qty: int | None = None
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    # updating fixture values for this test-case
    max_loop_count_per_side = 2
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))

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
            executor_http_client.trade_simulator_reload_config_query_client()

            # buy fills check
            for check_symbol in [leg1_symbol, leg2_symbol]:
                order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    order_id, partial_filled_qty = \
                        underlying_handle_simulated_multi_partial_fills_test(loop_count, check_symbol, leg1_symbol,
                                                                             leg2_symbol, last_trade_fixture_list,
                                                                             top_of_book_list_, order_id,
                                                                             executor_http_client, config_dict)
                    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                        # Sleeping to let the order get cxlled
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
                       last_trade_fixture_list, market_depth_basemodel_list,
                       top_of_book_list_, buy_order_, sell_order_, refresh_sec_update_fixture):
        buy_symbol = leg1_leg2_symbol_list[0][0]
        sell_symbol = leg1_leg2_symbol_list[0][1]
        expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

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
            executor_http_client.trade_simulator_reload_config_query_client()

            # buy fills check
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
            loop_count = 1
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0],
                                avoid_order_trigger=True)
            px = 100
            qty = 90
            place_new_order(buy_symbol, Side.BUY, px, qty, executor_http_client)
            time.sleep(2)  # delay for order to get placed

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol,
                                                                               executor_http_client)
            latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id,
                                                                        executor_http_client)
            last_fill_date_time = latest_fill_journal.fill_date_time
            filled_qty = get_partial_allowed_fill_qty(buy_symbol, config_dict, ack_order_journal.order.qty)
            assert latest_fill_journal.fill_qty == filled_qty, f"filled_qty mismatched: expected filled_qty {filled_qty} " \
                                                               f"received {latest_fill_journal.fill_qty}"
            order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id, executor_http_client)
            assert order_snapshot.order_status == OrderStatusType.OE_ACKED, "OrderStatus mismatched: expected status " \
                                                                            f"OrderStatusType.OE_ACKED received " \
                                                                            f"{order_snapshot.order_status}"

            # processing remaining 50% fills
            executor_http_client.trade_simulator_process_fill_query_client(
                ack_order_journal.order.order_id, ack_order_journal.order.px,
                ack_order_journal.order.qty, ack_order_journal.order.side,
                ack_order_journal.order.security.sec_id, ack_order_journal.order.underlying_account)
            latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id,
                                                                        executor_http_client)
            assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                              f"expected {latest_fill_journal} " \
                                                                              f"received " \
                                                                              f"{latest_fill_journal.fill_date_time}"
            assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                               f"received {latest_fill_journal.fill_qty}"

            order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id, executor_http_client)
            assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                             f"OrderStatusType.OE_FILLED received " \
                                                                             f"{order_snapshot.order_status}"
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_over_fill_case_1(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                          expected_strat_status_, symbol_overview_obj_list,
                          last_trade_fixture_list, market_depth_basemodel_list,
                          top_of_book_list_, buy_order_, sell_order_, refresh_sec_update_fixture):
    """
    Test case when order_snapshot is in OE_ACKED and fill is triggered to make it over_filled
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        loop_count = 1
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        time.sleep(2)  # delay for order to get placed

        ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol,
                                                                           executor_http_client)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id,
                                                                    executor_http_client)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = get_partial_allowed_fill_qty(buy_symbol, config_dict, ack_order_journal.order.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot_before_over_fill = (
            get_order_snapshot_from_order_id(ack_order_journal.order.order_id, executor_http_client))
        assert order_snapshot_before_over_fill.order_status == OrderStatusType.OE_ACKED, \
            "OrderStatus mismatched: expected status OrderStatusType.OE_ACKED received " \
            f"{order_snapshot_before_over_fill.order_status}"

        # processing fill for over_fill
        executor_http_client.trade_simulator_process_fill_query_client(
            ack_order_journal.order.order_id, ack_order_journal.order.px,
            ack_order_journal.order.qty, ack_order_journal.order.side,
            ack_order_journal.order.security.sec_id, ack_order_journal.order.underlying_account)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id,
                                                                    executor_http_client)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                          f"expected {latest_fill_journal} " \
                                                                          f"received " \
                                                                          f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"

        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id, executor_http_client)
        assert order_snapshot.filled_qty == order_snapshot_before_over_fill.filled_qty, \
            "order_snapshot filled_qty mismatch: expected unchanged fill as before fill to trigger over-fill, i.e.," \
            f"{order_snapshot_before_over_fill.filled_qty} but received {order_snapshot.filled_qty}"
        assert order_snapshot.order_status == order_snapshot_before_over_fill.order_status, \
            f"OrderStatus mismatched: expected status {order_snapshot_before_over_fill.order_status} received " \
            f"{order_snapshot.order_status}"

        time.sleep(15)
        strat_alerts: StratAlertBaseModel = log_book_web_client.get_strat_alert_client(created_pair_strat.id)

        check_str = "Unexpected: Received fill that will make order_snapshot OVER_FILLED"
        for alert in strat_alerts.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            # Checking alert in portfolio_alert if reason failed to add in strat_alert
            portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
            for alert in portfolio_alert.alerts:
                if re.search(check_str, alert.alert_brief):
                    break
            else:
                assert False, f"Couldn't find any alert saying: {check_str}"
        assert True

        # Checking if strat went to pause
        pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Expected Strat to be Paused, found state: {pair_strat.strat_state}, pair_strat: {pair_strat}"

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_over_fill_case_2(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                          expected_strat_status_, symbol_overview_obj_list,
                          last_trade_fixture_list, market_depth_basemodel_list,
                          top_of_book_list_, buy_order_, sell_order_, refresh_sec_update_fixture):
    """
    Test case when order_snapshot is in OE_FILLED and fill is triggered to make it over_filled
    """
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        loop_count = 1
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        time.sleep(5)  # delay for order to get placed

        ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol,
                                                                           executor_http_client)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id,
                                                                    executor_http_client)
        last_fill_date_time = latest_fill_journal.fill_date_time
        filled_qty = get_partial_allowed_fill_qty(buy_symbol, config_dict, ack_order_journal.order.qty)
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id, executor_http_client)
        assert order_snapshot.filled_qty == order_snapshot.order_brief.qty, "order_snapshot filled_qty mismatch: " \
                                                                            f"expected complete fill, i.e.," \
                                                                            f"{order_snapshot.order_brief.qty} " \
                                                                            f"received {order_snapshot.filled_qty}"
        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                         f"OrderStatusType.OE_FILLED received " \
                                                                         f"{order_snapshot.order_status}"

        # processing fill for over_fill
        executor_http_client.trade_simulator_process_fill_query_client(
            ack_order_journal.order.order_id, ack_order_journal.order.px,
            ack_order_journal.order.qty, ack_order_journal.order.side,
            ack_order_journal.order.security.sec_id, ack_order_journal.order.underlying_account)
        time.sleep(2)
        latest_fill_journal = get_latest_fill_journal_from_order_id(ack_order_journal.order.order_id,
                                                                    executor_http_client)
        assert latest_fill_journal.fill_date_time != last_fill_date_time, "last_fill_date_time mismatched: " \
                                                                          f"expected {latest_fill_journal} " \
                                                                          f"received " \
                                                                          f"{latest_fill_journal.fill_date_time}"
        assert latest_fill_journal.fill_qty == filled_qty, f"fill_qty mismatched: expected {filled_qty} " \
                                                           f"received {latest_fill_journal.fill_qty}"
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id,
                                                          executor_http_client)
        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, "OrderStatus mismatched: expected status " \
                                                                         f"OrderStatusType.OE_FILLED received " \
                                                                         f"{order_snapshot.order_status}"

        time.sleep(15)
        strat_alerts: StratAlertBaseModel = log_book_web_client.get_strat_alert_client(created_pair_strat.id)

        check_str = "Unsupported - Fill received for completely filled order_snapshot"
        for alert in strat_alerts.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            # Checking alert in portfolio_alert if reason failed to add in strat_alert
            portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
            for alert in portfolio_alert.alerts:
                if re.search(check_str, alert.alert_brief):
                    break
            else:
                assert False, f"Couldn't find any alert saying: {check_str}, received strat_alert: {strat_alerts}"
        assert True

        # Checking if strat went to pause
        pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat.strat_state == StratState.StratState_PAUSED, \
            f"Expected Strat to be Paused, found state: {pair_strat.strat_state}, pair_strat: {pair_strat}"

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_ack_to_rej_orders(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                           expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                           last_trade_fixture_list, market_depth_basemodel_list,
                           top_of_book_list_, max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_orders to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_orders = 10
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_ack_to_reject_orders"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            handle_rej_order_test(leg1_symbol, leg2_symbol, expected_strat_limits_,
                                  last_trade_fixture_list, top_of_book_list_, max_loop_count_per_side,
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
def test_unack_to_rej_orders(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                             expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                             last_trade_fixture_list, market_depth_basemodel_list,
                             top_of_book_list_, max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_orders to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_orders = 10
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_new_to_reject_orders"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            handle_rej_order_test(leg1_symbol, leg2_symbol, expected_strat_limits_,
                                  last_trade_fixture_list, top_of_book_list_, max_loop_count_per_side,
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
                                   last_trade_fixture_list, market_depth_basemodel_list,
                                   top_of_book_list_, buy_order_, sell_order_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_ack_to_cxl_rej_orders"] = True
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            for check_symbol in [leg1_symbol, leg2_symbol]:
                continues_order_count, continues_special_order_count = get_continuous_order_configs(check_symbol,
                                                                                                    config_dict)
                order_count = 0
                special_order_count = 0
                last_cxl_order_id = None
                last_cxl_rej_order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_http_client)
                    if check_symbol == leg1_symbol:
                        run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[0])
                    else:
                        run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[1])
                    time.sleep(10)  # delay for order to get placed and trigger cxl

                    if order_count < continues_order_count:
                        check_order_event = OrderEventType.OE_CXL_ACK
                        order_count += 1
                    else:
                        if special_order_count < continues_special_order_count:
                            check_order_event = "REJ"
                            special_order_count += 1
                        else:
                            check_order_event = OrderEventType.OE_CXL_ACK
                            order_count = 1
                            special_order_count = 0

                    # internally contains assert statements
                    last_cxl_order_id, last_cxl_rej_order_id = verify_cxl_rej(last_cxl_order_id, last_cxl_rej_order_id,
                                                                              check_order_event, check_symbol,
                                                                              executor_http_client,
                                                                              OrderStatusType.OE_ACKED)
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
                                   last_trade_fixture_list, market_depth_basemodel_list,
                                   top_of_book_list_, buy_order_, sell_order_,
                                   max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_new_to_cxl_rej_orders"] = True
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50

            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            for check_symbol in [leg1_symbol, leg2_symbol]:
                continues_order_count, continues_special_order_count = get_continuous_order_configs(check_symbol,
                                                                                                    config_dict)
                order_count = 0
                special_order_count = 0
                last_cxl_order_id = None
                last_cxl_rej_order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_http_client)
                    if check_symbol == leg1_symbol:
                        run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[0])
                    else:
                        run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[1])
                    time.sleep(10)  # delay for order to get placed and trigger cxl

                    if order_count < continues_order_count:
                        check_order_event = OrderEventType.OE_CXL_ACK
                        order_count += 1
                    else:
                        if special_order_count < continues_special_order_count:
                            check_order_event = "REJ"
                            special_order_count += 1
                        else:
                            check_order_event = OrderEventType.OE_CXL_ACK
                            order_count = 1
                            special_order_count = 0

                    # internally contains assert statements
                    last_cxl_order_id, last_cxl_rej_order_id = verify_cxl_rej(last_cxl_order_id, last_cxl_rej_order_id,
                                                                              check_order_event, check_symbol,
                                                                              executor_http_client,
                                                                              OrderStatusType.OE_UNACK)
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
                                    last_trade_fixture_list, market_depth_basemodel_list,
                                    top_of_book_list_, buy_order_, sell_order_,
                                    max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["force_fully_fill"] = True
                config_dict["symbol_configs"][symbol]["simulate_ack_to_cxl_rej_orders"] = True

            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            for check_symbol in [leg1_symbol, leg2_symbol]:
                continues_order_count, continues_special_order_count = get_continuous_order_configs(check_symbol,
                                                                                                    config_dict)
                order_count = 0
                special_order_count = 0
                last_cxl_order_id = None
                last_cxl_rej_order_id = None
                for loop_count in range(1, max_loop_count_per_side + 1):
                    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_http_client)
                    if check_symbol == leg1_symbol:
                        run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[0],
                                            avoid_order_trigger=True)
                        px = 100
                        qty = 90
                        place_new_order(leg1_symbol, Side.BUY, px, qty, executor_http_client)
                    else:
                        run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[1],
                                             avoid_order_trigger=True)
                        px = 110
                        qty = 70
                        place_new_order(leg2_symbol, Side.SELL, px, qty, executor_http_client)
                    time.sleep(10)  # delay for order to get placed and trigger cxl

                    if order_count < continues_order_count:
                        check_order_event = OrderEventType.OE_CXL_ACK
                        order_count += 1
                    else:
                        if special_order_count < continues_special_order_count:
                            check_order_event = "REJ"
                            special_order_count += 1
                        else:
                            check_order_event = OrderEventType.OE_CXL_ACK
                            order_count = 1
                            special_order_count = 0

                    # internally contains assert statements
                    if check_order_event == "REJ":
                        # internally checks order_journal is not None else raises assert exception internally
                        latest_cxl_rej_order_journal = \
                            get_latest_order_journal_with_events_and_symbol([OrderEventType.OE_CXL_INT_REJ,
                                                                             OrderEventType.OE_CXL_BRK_REJ,
                                                                             OrderEventType.OE_CXL_EXH_REJ],
                                                                            check_symbol, executor_http_client,
                                                                            last_order_id=last_cxl_rej_order_id)
                        last_cxl_rej_order_id = latest_cxl_rej_order_journal.order.order_id

                        order_snapshot = get_order_snapshot_from_order_id(latest_cxl_rej_order_journal.order.order_id,
                                                                          executor_http_client)
                        assert order_snapshot.order_status == OrderStatusType.OE_FILLED, \
                            f"Unexpected order_snapshot.order_status: expected {OrderStatusType.OE_FILLED}, " \
                            f"received {order_snapshot.order_status}"
                    else:
                        # checks order_journal is not None else raises assert exception internally
                        latest_cxl_order_journal = get_latest_order_journal_with_event_and_symbol(
                            OrderEventType.OE_CXL_ACK, check_symbol, executor_http_client,
                            last_order_id=last_cxl_order_id)
                        last_cxl_order_id = latest_cxl_order_journal.order.order_id

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
        top_of_book_list_, market_depth_basemodel_list, last_trade_fixture_list,
        refresh_sec_update_fixture):
    # creating strat
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    max_loop_count_per_side = 2
    residual_wait_sec = 4 * refresh_sec_update_fixture
    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

        cxl_req_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL,
                                                                               buy_symbol, executor_http_client)
        time.sleep(residual_wait_sec)
        get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL,
                                                       buy_symbol, executor_http_client, expect_no_order=True,
                                                       last_order_id=cxl_req_order_journal.order.order_id)
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
                                       expected_strat_status_, sample_alert, symbol_overview_obj_list,
                                       top_of_book_list_, market_depth_basemodel_list):
    # creating strat
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    total_loop_count = 5
    active_pair_strat, executor_http_client = create_n_activate_strat(buy_symbol, sell_symbol, pair_strat_,
                                                                      expected_strat_limits_, expected_strat_status_,
                                                                      symbol_overview_obj_list, top_of_book_list_,
                                                                      market_depth_basemodel_list)
    alert_id_list = []
    broker_id_list = []
    for loop_count in range(total_loop_count):
        # check to add alert
        alert = copy.deepcopy(sample_alert)
        alert.id = f"test_id_{loop_count}"
        broker = broker_fixture()
        strat_alerts: StratAlertBaseModel = StratAlertBaseModel(_id=active_pair_strat.id,
                                                                alerts=[alert])
        strat_limits: StratLimitsBaseModel = StratLimitsBaseModel(_id=active_pair_strat.id,
                                                                  eligible_brokers=[broker])
        updated_strat_alerts = log_book_web_client.patch_strat_alert_client(
            jsonable_encoder(strat_alerts, by_alias=True, exclude_none=True))
        updated_strat_limits = executor_http_client.patch_strat_limits_client(
            jsonable_encoder(strat_limits, by_alias=True, exclude_none=True))

        assert alert in updated_strat_alerts.alerts, f"Couldn't find alert {alert} in " \
                                                     f"strat_alerts list" \
                                                     f"{updated_strat_alerts.alerts}"
        assert broker in updated_strat_limits.eligible_brokers, f"couldn't find broker in " \
                                                                f"eligible_brokers list " \
                                                                f"{updated_strat_limits.eligible_brokers}"
        alert_id_list.append(alert.id)
        broker_id_list.append(broker.id)

        # check to add more impacted orders and update alert
        updated_alert = copy.deepcopy(alert)
        updated_alert.alert_brief = "Updated alert"
        strat_alerts: StratAlertBaseModel = StratAlertBaseModel(_id=active_pair_strat.id,
                                                                alerts=[updated_alert])
        updated_strat_alerts = log_book_web_client.patch_strat_alert_client(
            jsonable_encoder(strat_alerts, by_alias=True, exclude_none=True))

        alert.alert_brief = updated_alert.alert_brief
        assert alert in updated_strat_alerts.alerts, (f"Couldn't find alert {alert} in strat_alerts list "
                                                      f"{updated_strat_alerts.alerts}")

    # Deleting alerts
    for alert_id in alert_id_list:
        delete_intended_alert = AlertOptional(_id=alert_id)
        strat_alerts: StratAlertBaseModel = StratAlertBaseModel(_id=active_pair_strat.id,
                                                                alerts=[delete_intended_alert])
        updated_strat_alerts = log_book_web_client.patch_strat_alert_client(
            jsonable_encoder(strat_alerts, by_alias=True, exclude_none=True))

        alert_id_list = [alert.id for alert in updated_strat_alerts.alerts]
        assert alert_id not in alert_id_list, f"Unexpectedly found alert_id {alert_id} " \
                                              f"in alert_id list {alert_id_list}"

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
                                                      last_trade_fixture_list, market_depth_basemodel_list,
                                                      top_of_book_list_, refresh_sec_update_fixture):
    underlying_account_prefix: str = "Acc"
    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    buy_order_id = None
    sell_order_id = None
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        residual_wait_sec = 4 * refresh_sec_update_fixture
        active_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))
        # buy handling
        buy_tob_last_update_date_time_tracker, buy_order_id = \
            create_fills_for_underlying_account_test(leg1_symbol, leg2_symbol, top_of_book_list_,
                                                     buy_tob_last_update_date_time_tracker, buy_order_id,
                                                     underlying_account_prefix, Side.BUY, executor_http_client)

        time.sleep(residual_wait_sec)   #

        # sell handling
        sell_tob_last_update_date_time_tracker, sell_order_id = \
            create_fills_for_underlying_account_test(leg1_symbol, leg2_symbol, top_of_book_list_,
                                                     sell_tob_last_update_date_time_tracker, sell_order_id,
                                                     underlying_account_prefix, Side.SELL, executor_http_client)

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
def test_last_n_sec_order_qty_sum(static_data_, clean_and_set_limits, leg1_leg2_symbol_list,
                                  pair_strat_, expected_strat_limits_,
                                  expected_strat_status_, symbol_overview_obj_list,
                                  last_trade_fixture_list, market_depth_basemodel_list,
                                  top_of_book_list_, buy_fill_journal_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    total_order_count_for_each_side = 5
    expected_strat_limits_ = copy.deepcopy(expected_strat_limits_)
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        # buy testing
        buy_new_order_id = None
        order_create_time_list = []
        order_qty_list = []
        for loop_count in range(total_order_count_for_each_side):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                               buy_symbol, executor_http_client,
                                                                               last_order_id=buy_new_order_id)
            buy_new_order_id = ack_order_journal.order.order_id
            order_create_time_list.append(ack_order_journal.order_event_date_time)
            order_qty_list.append(ack_order_journal.order.qty)
            if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                time.sleep(residual_wait_sec)   # wait for this order to get cancelled by residual
            else:
                time.sleep(2)

        order_create_time_list.reverse()
        order_qty_list.reverse()
        last_n_sec_qty = 0
        for loop_count in range(total_order_count_for_each_side):
            delta = DateTime.utcnow() - order_create_time_list[loop_count]
            last_n_sec = int(math.ceil(delta.total_seconds())) + 1
            last_n_sec_qty += order_qty_list[loop_count]

            # making portfolio_limits_obj.rolling_max_order_count.rolling_tx_count_period_seconds computed last_n_sec(s)
            # this is required as last_n_sec_order_qty takes internally this limit as last_n_sec to provide order_qty
            # in query
            rolling_max_order_count = RollingMaxOrderCountOptional(rolling_tx_count_period_seconds=last_n_sec)
            portfolio_limits = PortfolioLimitsBaseModel(_id=1, rolling_max_order_count=rolling_max_order_count)
            updated_portfolio_limits = \
                email_book_service_native_web_client.patch_portfolio_limits_client(
                    portfolio_limits.model_dump(by_alias=True, exclude_none=True))
            assert updated_portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds == last_n_sec, \
                f"Unexpected last_n_sec value: expected {last_n_sec}, " \
                f"received {updated_portfolio_limits.rolling_max_order_count.rolling_tx_count_period_seconds}"

            call_date_time = DateTime.utcnow()
            executor_check_snapshot_obj = \
                executor_http_client.get_executor_check_snapshot_query_client(buy_symbol, "BUY", last_n_sec)

            assert len(executor_check_snapshot_obj) == 1, \
                f"Received unexpected length of list of executor_check_snapshot_obj from query," \
                f"expected one obj received {len(executor_check_snapshot_obj)}"
            assert executor_check_snapshot_obj[0].last_n_sec_order_qty == last_n_sec_qty, \
                f"Order qty mismatched for last {last_n_sec} " \
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
                               last_trade_fixture_list, market_depth_basemodel_list,
                               top_of_book_list_, buy_order_, sell_order_,
                               max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_orders to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_orders = 10
        active_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            handle_unsolicited_cxl(leg1_symbol, leg2_symbol, last_trade_fixture_list, max_loop_count_per_side,
                                   top_of_book_list_, executor_http_client, config_dict, residual_wait_sec)
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
                                 last_trade_fixture_list, market_depth_basemodel_list,
                                 top_of_book_list_, buy_order_, sell_order_,
                                 max_loop_count_per_side, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        # explicitly setting waived_min_orders to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_orders = 10
        active_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

        config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
                config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_orders"] = True
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            # updating simulator's configs
            executor_http_client.trade_simulator_reload_config_query_client()

            handle_unsolicited_cxl(leg1_symbol, leg2_symbol, last_trade_fixture_list, max_loop_count_per_side,
                                   top_of_book_list_, executor_http_client, config_dict, residual_wait_sec)
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
                                                   symbol_overview_obj_list, last_trade_fixture_list,
                                                   market_depth_basemodel_list, top_of_book_list_,
                                                   refresh_sec_update_fixture):
    activated_strats = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    # creates and activates multiple pair_strats
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list:
        activated_strat, executor_http_client = (
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))
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


@pytest.mark.nightly
def test_portfolio_alert_updates(static_data_, clean_and_set_limits, sample_alert):
    stored_portfolio_alert = log_book_web_client.get_portfolio_alert_client(portfolio_alert_id=1)

    alert = copy.deepcopy(sample_alert)
    portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
    updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(
            jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True))
    assert stored_portfolio_alert.alert_update_seq_num + 1 == updated_portfolio_alert.alert_update_seq_num, \
        f"Mismatched alert_update_seq_num: expected {stored_portfolio_alert.alert_update_seq_num + 1}, " \
        f"received {updated_portfolio_alert.alert_update_seq_num}"

    max_loop_count = 5
    for loop_count in range(max_loop_count):
        alert.alert_brief = f"Test update - {loop_count}"
        portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
        alert_updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(
                jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True))
        assert updated_portfolio_alert.alert_update_seq_num + (loop_count + 1) == \
               alert_updated_portfolio_alert.alert_update_seq_num, (
                f"Mismatched alert_update_seq_num: expected "
                f"{updated_portfolio_alert.alert_update_seq_num + (loop_count + 1)}, "
                f"received {alert_updated_portfolio_alert.alert_update_seq_num}")


@pytest.mark.nightly
def test_partial_ack(static_data_, clean_and_set_limits, pair_strat_,
                     expected_strat_limits_, top_of_book_list_,
                     expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                     market_depth_basemodel_list, leg1_leg2_symbol_list, refresh_sec_update_fixture):
    partial_ack_qty: int | None = None

    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        active_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))
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
            executor_http_client.trade_simulator_reload_config_query_client()

            # buy fills check
            new_order_id = None
            acked_order_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_http_client)
                run_buy_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[0],
                                    avoid_order_trigger=True)
                px = 100
                qty = 90
                place_new_order(leg1_symbol, Side.BUY, px, qty, executor_http_client)
                time.sleep(2)  # delay for order to get placed

                new_order_id, acked_order_id, partial_ack_qty = \
                    handle_partial_ack_checks(leg1_symbol, new_order_id, acked_order_id, executor_http_client,
                                              config_dict)

                if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                    time.sleep(residual_wait_sec)    # wait to make this open order residual

            time.sleep(5)
            strat_status = executor_http_client.get_strat_status_client(active_pair_strat.id)
            assert partial_ack_qty * max_loop_count_per_side == strat_status.total_fill_buy_qty, \
                f"Mismatched total_fill_buy_qty: Expected {partial_ack_qty * max_loop_count_per_side}, " \
                f"received {strat_status.total_fill_buy_qty}"

            # sell fills check
            new_order_id = None
            acked_order_id = None
            for loop_count in range(1, max_loop_count_per_side + 1):
                run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_http_client)
                run_sell_top_of_book(leg1_symbol, leg2_symbol, executor_http_client, top_of_book_list_[1],
                                     avoid_order_trigger=True)
                px = 110
                qty = 70
                place_new_order(leg2_symbol, Side.SELL, px, qty, executor_http_client)
                time.sleep(2)

                new_order_id, acked_order_id, partial_ack_qty = \
                    handle_partial_ack_checks(leg2_symbol, new_order_id, acked_order_id, executor_http_client,
                                              config_dict)

                if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
                    time.sleep(residual_wait_sec)    # wait to make this open order residual

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
                               last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
                               refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))
    total_loop_count = 5
    residual_qty = 5

    # creating tobs
    run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0], avoid_order_trigger=True)

    # Since both side have same last trade px in test cases
    buy_last_trade_px = top_of_book_list_[0].get("last_trade").get("px")
    sell_last_trade_px = top_of_book_list_[1].get("last_trade").get("px")

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

        buy_residual_notional = buy_residual_qty * get_px_in_usd(buy_last_trade_px)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        assert buy_residual_qty == strat_brief.pair_buy_side_trading_brief.residual_qty, \
            f"Mismatch residual_qty: expected {buy_residual_qty} received " \
            f"{strat_brief.pair_buy_side_trading_brief.residual_qty}"
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

        sell_residual_notional = sell_residual_qty * get_px_in_usd(sell_last_trade_px)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        assert sell_residual_qty == strat_brief.pair_sell_side_trading_brief.residual_qty, \
            f"Mismatch residual_qty: expected {sell_residual_qty}, received " \
            f"{strat_brief.pair_sell_side_trading_brief.residual_qty}"
        assert strat_status.residual.residual_notional == residual_notional, \
            (f"Mismatch sell residual_notional: expected {residual_notional} received "
             f"{strat_status.residual.residual_notional}")


@pytest.mark.nightly
def test_ack_post_unack_unsol_cxl(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                  expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                  last_trade_fixture_list, market_depth_basemodel_list,
                                  top_of_book_list_, buy_order_, sell_order_,
                                  max_loop_count_per_side, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_new_unsolicited_cxl_orders"] = True
            config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.trade_simulator_reload_config_query_client()

        # buy test
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        loop_count = 1
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])

        latest_unack_obj = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW, buy_symbol,
                                                                          executor_http_client)
        latest_cxl_ack_obj = get_latest_order_journal_with_events_and_symbol([OrderEventType.OE_CXL_ACK,
                                                                              OrderEventType.OE_UNSOL_CXL], buy_symbol,
                                                                             executor_http_client)

        executor_http_client.trade_simulator_process_order_ack_query_client(
            latest_unack_obj.order.order_id,
            latest_unack_obj.order.px,
            latest_unack_obj.order.qty,
            latest_unack_obj.order.side,
            latest_unack_obj.order.security.sec_id,
            latest_unack_obj.order.underlying_account)

        order_snapshot = get_order_snapshot_from_order_id(latest_unack_obj.order.order_id,
                                                          executor_http_client)
        executor_config_file_path = STRAT_EXECUTOR / "data" / f"config.yaml"
        executor_config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(executor_config_file_path)

        if executor_config_dict.get("pause_fulfill_post_order_dod"):
            assert order_snapshot.filled_qty == 0, f"Mismatch order_snapshot.filled_qty, expected 0, " \
                                                   f"received {order_snapshot.filled_qty}"
            assert order_snapshot.cxled_qty == order_snapshot.order_brief.qty, \
                f"Mismatch order_snapshot.cxled_qty: expected {order_snapshot.order_brief.qty}, received " \
                f"{order_snapshot.cxled_qty}"
            assert order_snapshot.order_status == OrderStatusType.OE_DOD, \
                f"Mismatch order_snapshot.order_status: expected OrderStatusType.OE_DOD, " \
                f"received {order_snapshot.order_status}"
        else:
            assert order_snapshot.filled_qty == order_snapshot.order_brief.qty, \
                (f"Mismatch order_snapshot.filled_qty, expected {order_snapshot.order_brief.qty}, "
                 f"received {order_snapshot.filled_qty}")
            assert order_snapshot.cxled_qty == 0, \
                f"Mismatch order_snapshot.cxled_qty: expected 0, received {order_snapshot.cxled_qty}"
            assert order_snapshot.order_status == OrderStatusType.OE_FILLED, \
                f"Mismatch order_snapshot.order_status: expected OrderStatusType.OE_FILLED, " \
                f"received {order_snapshot.order_status}"

        time.sleep(2)
        check_str = "_check_state_and_get_order_snapshot_obj: order_journal of key:"
        # Checking alert in strat_alert
        strat_alert = log_book_web_client.get_strat_alert_client(active_pair_strat.id)
        for alert in strat_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            # Checking alert in portfolio_alert if reason failed to add in strat_alert
            portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
            for alert in portfolio_alert.alerts:
                if re.search(check_str, alert.alert_brief):
                    break
            else:
                assert False, f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"

        if executor_config_dict.get("pause_fulfill_post_order_dod"):
            check_str = ("Unexpected: Received fill that makes order_snapshot OE_FILLED which is already of "
                         "state OE_DOD, ignoring this fill and putting this strat to PAUSE")
            time.sleep(2)
            # Checking alert in strat_alert
            strat_alert = log_book_web_client.get_strat_alert_client(active_pair_strat.id)
            for alert in strat_alert.alerts:
                if re.search(check_str, alert.alert_brief):
                    break
            else:
                # Checking alert in portfolio_alert if reason failed to add in strat_alert
                portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
                for alert in portfolio_alert.alerts:
                    if re.search(check_str, alert.alert_brief):
                        break
                else:
                    assert False, f"Can't find alert of {check_str} in neither strat_alert nor portfolio_alert"

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
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_, buy_order_, sell_order_,
                                                 refresh_sec_update_fixture):

    expected_strat_limits_.residual_restriction.max_residual = 0
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    buy_symbol, sell_symbol, active_pair_strat, executor_http_client = (
        underlying_pre_requisites_for_limit_test(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                                                 expected_strat_status_, symbol_overview_obj_list,
                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                 top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        residual_qty = 10
        executor_http_client.update_residuals_query_client(buy_symbol, Side.BUY, residual_qty)

        # placing new non-systematic new_order
        px = 100
        qty = 90
        check_str = "residual notional: .* > max residual"
        assert_fail_message = "Could not find any alert containing message to block orders " \
                              "due to residual notional breach"
        # placing new non-systematic new_order
        place_new_order(buy_symbol, Side.BUY, px, qty, executor_http_client)
        print(f"symbol: {buy_symbol}, Created new_order obj")

        new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW, buy_symbol,
                                                                           executor_http_client)

        time.sleep(2)
        strat_alert = log_book_web_client.get_strat_alert_client(active_pair_strat.id)
        for alert in strat_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            # Checking alert in portfolio_alert if reason failed to add in strat_alert
            portfolio_alert = log_book_web_client.get_portfolio_alert_client(1)
            for alert in portfolio_alert.alerts:
                if re.search(check_str, alert.alert_brief):
                    break
            else:
                assert False, assert_fail_message
        assert True
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
                                                                 last_trade_fixture_list, market_depth_basemodel_list,
                                                                 top_of_book_list_, buy_order_, sell_order_,
                                                                 refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 1
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
            config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.trade_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_trade_fixture_list,
            top_of_book_list_, Side.BUY, executor_http_client)
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
                                                                  last_trade_fixture_list, market_depth_basemodel_list,
                                                                  top_of_book_list_, buy_order_, sell_order_,
                                                                  refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_orders to 0 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 1
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_, leg1_side=Side.SELL,
                                           leg2_side=Side.BUY))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
            config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.trade_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_trade_fixture_list,
            top_of_book_list_, Side.SELL, executor_http_client, leg1_side=Side.SELL, leg2_side=Side.BUY)
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
                                                              last_trade_fixture_list, market_depth_basemodel_list,
                                                              top_of_book_list_, buy_order_, sell_order_,
                                                              refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 19
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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
        executor_http_client.trade_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_trade_fixture_list,
            top_of_book_list_, Side.BUY, executor_http_client)
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
                                                               last_trade_fixture_list, market_depth_basemodel_list,
                                                               top_of_book_list_, buy_order_, sell_order_,
                                                               refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 19
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_, leg1_side=Side.SELL,
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
        executor_http_client.trade_simulator_reload_config_query_client()

        handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
            buy_symbol, sell_symbol, active_pair_strat.id, last_trade_fixture_list,
            top_of_book_list_, Side.SELL, executor_http_client, leg1_side=Side.SELL,
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
    alert_list = []

    portfolio_alert = log_book_web_client.get_portfolio_alert_client(portfolio_alert_id=1)
    alert_list.extend(portfolio_alert.alerts)

    sev = [Severity.Severity_CRITICAL, Severity.Severity_ERROR, Severity.Severity_WARNING,
           Severity.Severity_INFO, Severity.Severity_DEBUG]
    counter = 0
    for i in range(10):
        alert = copy.deepcopy(sample_alert)
        alert.id = f"obj_{i}"
        alert.last_update_date_time = DateTime.utcnow()

        alert.severity = sev[counter]
        counter += 1
        if counter > 4:
            counter = 0

        alert_list.append(alert)
        portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
        json_obj = jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True)
        updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(json_obj)

    # sorting alert list for this test comparison
    alert_list.sort(key=lambda x: x.last_update_date_time, reverse=True)

    sorted_alert_list = []
    for sev in Severity:
        if sev.value != Severity.Severity_UNSPECIFIED:
            for alert in alert_list:
                if alert.severity == sev.value:
                    sorted_alert_list.append(alert)

    portfolio_alert = log_book_web_client.get_portfolio_alert_client(portfolio_alert_id=1)
    agg_sorted_alerts: List[Alert] = portfolio_alert.alerts
    for alert in agg_sorted_alerts:
        alert.last_update_date_time = pendulum.parse(str(alert.last_update_date_time)).in_timezone("utc")
    for alert in alert_list:
        alert.last_update_date_time = \
            alert.last_update_date_time.replace(microsecond=
                                                int(str(alert.last_update_date_time.microsecond)[:3] + "000"))

    for sorted_alert, expected_alert in zip(agg_sorted_alerts, sorted_alert_list):
        assert sorted_alert.id == expected_alert.id, \
            f"Alert ID mismatch: expected Alert {expected_alert.id}, received {sorted_alert.id}"
        assert sorted_alert.last_update_date_time == expected_alert.last_update_date_time, \
            f"Alert Datetime mismatch: expected Alert {expected_alert}, received {sorted_alert}"


def test_alert_id(clean_and_set_limits, sample_alert):
    alert_list = []

    for i in range(1000):
        alert = copy.deepcopy(sample_alert)
        alert.id = f"obj_{i}"
        alert.last_update_date_time = DateTime.utcnow()

        alert_list.append(alert)
        portfolio_alert_basemodel = PortfolioAlertBaseModel(_id=1, alerts=[alert])
        json_obj = jsonable_encoder(portfolio_alert_basemodel, by_alias=True, exclude_none=True)
        updated_portfolio_alert = log_book_web_client.patch_portfolio_alert_client(json_obj)

    portfolio_alert = log_book_web_client.get_portfolio_alert_client(portfolio_alert_id=1)
    agg_sorted_alerts: List[Alert] = portfolio_alert.alerts
    # for alert in agg_sorted_alerts:
    #     alert.last_update_date_time = pendulum.parse(str(alert.last_update_date_time)).in_timezone("utc")
    # for alert in alert_list:
    #     alert.last_update_date_time = \
    #         alert.last_update_date_time.replace(microsecond=
    #                                             int(str(alert.last_update_date_time.microsecond)[:3] + "000"))
    # for sorted_alert, expected_alert in zip(agg_sorted_alerts, list(reversed(sorted_alert_list))):
    #     assert sorted_alert.id == expected_alert.id, \
    #         f"Alert ID mismatch: expected Alert {expected_alert.id}, received {sorted_alert.id}"
    #     assert sorted_alert.last_update_date_time == expected_alert.last_update_date_time, \
    #         f"Alert Datetime mismatch: expected Alert {expected_alert}, received {sorted_alert}"

    alert_id_dict = {}
    for alert in agg_sorted_alerts:
        if alert.id in alert_id_dict:
            assert False, (f"alert id already exists in dict, existing obj: {alert_id_dict[alert.id]}, "
                           f"new obj: {alert}")
        alert_id_dict[alert.id] = alert



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
    order_limits_max_id = email_book_service_native_web_client.get_order_limits_max_id_client()
    assert order_limits_max_id.max_id_val == 1, f"max_id mismatch, expected 1 received {order_limits_max_id.max_id_val}"

    order_limits_basemodel = OrderLimitsBaseModel(_id=2)
    created_order_limits_obj = email_book_service_native_web_client.create_order_limits_client(order_limits_basemodel)

    order_limits_max_id = email_book_service_native_web_client.get_order_limits_max_id_client()
    assert order_limits_max_id.max_id_val == created_order_limits_obj.id, \
        f"max_id mismatch, expected {created_order_limits_obj.id} received {order_limits_max_id.max_id_val}"


@pytest.mark.nightly
def test_get_market_depths_query(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list, top_of_book_list_,
        market_depth_basemodel_list, last_trade_fixture_list, refresh_sec_update_fixture):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:2]

    pair_strat_n_http_client_tuple_list = []
    for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list:
        expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
        activated_pair_start, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))

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
                                 last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
                                 buy_order_, sell_order_, max_loop_count_per_side,
                                 buy_fill_journal_, sell_fill_journal_, expected_strat_brief_,
                                 refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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

        executor_http_client.trade_simulator_reload_config_query_client()

        for symbol, side in [(buy_symbol, Side.BUY), (sell_symbol, Side.SELL)]:
            # Placing buy orders
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
            if symbol == buy_symbol:
                run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0],
                                    avoid_order_trigger=True)
                px = 100
                qty = 90
                place_new_order(buy_symbol, Side.BUY, px, qty, executor_http_client)
            else:
                run_sell_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[1],
                                     avoid_order_trigger=True)
                px = 110
                qty = 70
                place_new_order(sell_symbol, Side.SELL, px, qty, executor_http_client)

            ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                               symbol, executor_http_client)
            ack_order_id = ack_order_journal.order.order_id

            executor_http_client.trade_simulator_place_cxl_order_query_client(
                ack_order_id, side, symbol, symbol, ack_order_journal.order.underlying_account)
            time.sleep(2)

            executor_http_client.trade_simulator_process_fill_query_client(
                ack_order_journal.order.order_id, ack_order_journal.order.px, ack_order_journal.order.qty,
                side, symbol, ack_order_journal.order.underlying_account)
            time.sleep(2)

            order_snapshot = get_order_snapshot_from_order_id(ack_order_id, executor_http_client)
            assert order_snapshot.order_status == OrderStatusType.OE_FILLED, \
                (f"Mismatched: OrderStatus must be OE_FILLED, found: {order_snapshot.order_status}, "
                 f"order_snapshot: {order_snapshot}")

            # Sending CXL_ACk after order is fully filled

            cxl_ack_order_journal = OrderJournalBaseModel(order=ack_order_journal.order,
                                                          order_event_date_time=DateTime.utcnow(),
                                                          order_event=OrderEventType.OE_CXL_ACK)
            executor_http_client.create_order_journal_client(cxl_ack_order_journal)
            time.sleep(2)

            # This must not impact any change in order states, checking that
            order_snapshot = get_order_snapshot_from_order_id(cxl_ack_order_journal.order.order_id,
                                                              executor_http_client)

            assert order_snapshot.order_status == OrderStatusType.OE_FILLED, \
                (f"Mismatched: OrderStatus must be OE_FILLED, found: {order_snapshot.order_status}, "
                 f"order_snapshot: {order_snapshot}")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_fills_after_unsolicited_cxl(static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
                                     expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
                                     last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
                                     buy_order_, sell_order_, max_loop_count_per_side,
                                     buy_fill_journal_, sell_fill_journal_,
                                     expected_strat_brief_, refresh_sec_update_fixture):
    # updating fixture values for this test-case
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    leg1_last_trade_px, leg2_last_trade_px = get_both_leg_last_trade_px()

    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 10
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture

    active_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            config_dict["symbol_configs"][symbol]["simulate_ack_unsolicited_cxl_orders"] = True
            config_dict["symbol_configs"][symbol]["continues_order_count"] = 0
            config_dict["symbol_configs"][symbol]["continues_special_order_count"] = 1  # all orders - unsol_cxl
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.trade_simulator_reload_config_query_client()

        for symbol in [buy_symbol, sell_symbol]:

            print(f"Checking symbol: {symbol}")
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
            if symbol == buy_symbol:
                run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
            else:
                run_sell_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[1])
            time.sleep(2)  # delay for order to get placed

            latest_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_UNSOL_CXL,
                                                                                  symbol, executor_http_client)
            order_snapshot_list = executor_http_client.get_all_order_snapshot_client(-100)
            for order_snapshot in order_snapshot_list:
                if order_snapshot.order_brief.order_id == latest_order_journal.order.order_id:
                    order_snapshot_before_fill = order_snapshot
                    break
            else:
                assert False, \
                    ("Unexpected: Can't find order_snapshot having order_id in "
                     f"order_snapshot list, order_id: {latest_order_journal.order.order_id}, "
                     f"order_snapshot_list: {order_snapshot_list}")

            symbol_side_snapshot_list = executor_http_client.get_all_symbol_side_snapshot_client()
            for symbol_side_snapshot in symbol_side_snapshot_list:
                if symbol_side_snapshot.security.sec_id == latest_order_journal.order.security.sec_id:
                    symbol_side_snapshot_before_fill = symbol_side_snapshot
                    break
            else:
                assert False, \
                    ("Unexpected: Can't find symbol_side_snapshot having symbol: "
                     f"{latest_order_journal.order.security.sec_id}, "
                     f"order_snapshot_list: {order_snapshot_list}")

            strat_brief_list = executor_http_client.get_all_strat_brief_client()
            assert len(strat_brief_list) == 1, \
                ("Unexpected: This test created single strat so expected single strat_brief in "
                 f"strat_brief_list , received length: {len(strat_brief_list)}, "
                 f"strat_brief_list: {strat_brief_list}")
            strat_brief_before_fill = strat_brief_list[0]

            strat_status_before_fill = executor_http_client.get_strat_status_client(active_pair_strat.id)

            portfolio_status_before_fill = email_book_service_native_web_client.get_portfolio_status_client(1)

            # Placing Fill after order_snapshot is OE_DOD
            if buy_fill_journal_.fill_symbol == symbol:
                fill_journal_obj = copy.deepcopy(buy_fill_journal_)
            else:
                fill_journal_obj = copy.deepcopy(sell_fill_journal_)

            fill_journal_obj.fill_qty = 20
            if symbol == buy_symbol:
                executor_http_client.trade_simulator_process_fill_query_client(
                    latest_order_journal.order.order_id, fill_journal_obj.fill_px, fill_journal_obj.fill_qty,
                    Side.BUY, symbol, fill_journal_obj.underlying_account)
            else:
                executor_http_client.trade_simulator_process_fill_query_client(
                    latest_order_journal.order.order_id, fill_journal_obj.fill_px, fill_journal_obj.fill_qty,
                    Side.SELL, symbol, fill_journal_obj.underlying_account)

            placed_fill_journal_obj = get_latest_fill_journal_from_order_id(latest_order_journal.order.order_id,
                                                                            executor_http_client)
            # OrderSnapshot check
            order_snapshot_list = executor_http_client.get_all_order_snapshot_client(-100)
            for order_snapshot in order_snapshot_list:
                if order_snapshot.order_brief.order_id == placed_fill_journal_obj.order_id:
                    order_snapshot_after_fill = order_snapshot_list[0]
                    break
            else:
                assert False, \
                    ("Unexpected: Can't find order_snapshot having order_id in "
                     f"order_snapshot list, order_id: {placed_fill_journal_obj.order_id}, "
                     f"order_snapshot_list: {order_snapshot_list}")
            assert order_snapshot_after_fill.order_status == OrderStatusType.OE_DOD, \
                (f"Unexpected: OrderStatus mismatched, expected order_status: {OrderStatusType.OE_DOD}, "
                 f"received order_status: {order_snapshot_after_fill.order_status}")
            filled_qty = get_partial_allowed_fill_qty(symbol, config_dict, fill_journal_obj.fill_qty)
            assert order_snapshot_after_fill.filled_qty == order_snapshot_before_fill.filled_qty + filled_qty, \
                (f"Unexpected: OrderSnapshot's filled_qty mismatched, "
                 f"expected: {order_snapshot_before_fill.filled_qty + filled_qty}, "
                 f"received {order_snapshot_after_fill.filled_qty}")
            assert order_snapshot_after_fill.fill_notional == (
                    order_snapshot_before_fill.fill_notional +
                    (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))), \
                (f"Unexpected: OrderSnapshot's fill_notional mismatched, "
                 f"expected: {order_snapshot_before_fill.fill_notional + (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))}, "
                 f"received {order_snapshot_after_fill.fill_notional}")
            assert order_snapshot_after_fill.cxled_qty == order_snapshot_before_fill.cxled_qty - filled_qty, \
                (f"Unexpected: OrderSnapshot's cxled_qty mismatched, "
                 f"expected: {order_snapshot_before_fill.cxled_qty - filled_qty}, "
                 f"received {order_snapshot_after_fill.cxled_qty}")
            assert order_snapshot_after_fill.cxled_notional == (
                    order_snapshot_before_fill.cxled_notional -
                    (get_px_in_usd(order_snapshot_after_fill.order_brief.px)*filled_qty)), \
                (f"Unexpected: OrderSnapshot's cxled_notional mismatched, "
                 f"expected: {order_snapshot_before_fill.cxled_notional - (get_px_in_usd(order_snapshot_after_fill.order_brief.px)*filled_qty)}, "
                 f"received {order_snapshot_after_fill.cxled_notional}")

            # SymbolSideSnapshot check
            symbol_side_snapshot_list = executor_http_client.get_all_symbol_side_snapshot_client()
            for symbol_side_snapshot in symbol_side_snapshot_list:
                if symbol_side_snapshot.security.sec_id == latest_order_journal.order.security.sec_id:
                    symbol_side_snapshot_after_fill = symbol_side_snapshot
                    break
            else:
                assert False, \
                    ("Unexpected: Can't find symbol_side_snapshot having symbol: "
                     f"{latest_order_journal.order.security.sec_id}, "
                     f"order_snapshot_list: {order_snapshot_list}")
            assert (symbol_side_snapshot_after_fill.total_filled_qty ==
                    symbol_side_snapshot_before_fill.total_filled_qty + filled_qty), \
                (f"Unexpected: SymbolSideSnapshot's total_filled_qty mismatched, "
                 f"expected: {symbol_side_snapshot_before_fill.total_filled_qty + filled_qty}, "
                 f"received {symbol_side_snapshot_after_fill.total_filled_qty}")
            assert (symbol_side_snapshot_after_fill.total_fill_notional ==
                    symbol_side_snapshot_before_fill.total_fill_notional +
                    (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))), \
                (f"Unexpected: SymbolSideSnapshot's total_fill_notional mismatched, "
                 f"expected: {symbol_side_snapshot_before_fill.total_fill_notional + (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))}, "
                 f"received {symbol_side_snapshot_after_fill.total_fill_notional}")
            assert symbol_side_snapshot_after_fill.total_cxled_qty == (
                    symbol_side_snapshot_before_fill.total_cxled_qty - filled_qty), \
                (f"Unexpected: SymbolSideSnapshot's total_cxled_qty mismatched, "
                 f"expected: {symbol_side_snapshot_before_fill.total_cxled_qty - filled_qty}, "
                 f"received {symbol_side_snapshot_after_fill.total_cxled_qty}")
            assert symbol_side_snapshot_after_fill.total_cxled_notional == (
                    symbol_side_snapshot_before_fill.total_cxled_notional -
                    (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)), \
                (f"Unexpected: SymbolSideSnapshot's total_cxled_notional mismatched, "
                 f"expected: {symbol_side_snapshot_before_fill.total_cxled_notional - (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)}, "
                 f"received {symbol_side_snapshot_after_fill.total_cxled_notional}")

            # StratBrief Check
            strat_brief_list = executor_http_client.get_all_strat_brief_client()
            assert len(strat_brief_list) == 1, \
                ("Unexpected: This test created single strat so expected single strat_brief in "
                 f"strat_brief_list , received length: {len(strat_brief_list)}, "
                 f"strat_brief_list: {strat_brief_list}")
            strat_brief_after_fill = strat_brief_list[0]

            if symbol == buy_symbol:
                for symbol_side_snapshot in symbol_side_snapshot_list:
                    if symbol_side_snapshot.security.sec_id == sell_symbol:
                        other_leg_symbol_side_snapshot_after_fill = symbol_side_snapshot
                        break
                else:
                    assert False, \
                        ("Unexpected: Can't find symbol_side_snapshot having symbol: "
                         f"{latest_order_journal.order.security.sec_id}, "
                         f"order_snapshot_list: {order_snapshot_list}")
                update_expected_strat_brief_for_buy(order_snapshot_after_fill,
                                                    symbol_side_snapshot_after_fill,
                                                    other_leg_symbol_side_snapshot_after_fill,
                                                    expected_strat_limits_, expected_strat_brief_,
                                                    order_snapshot_after_fill.last_update_date_time,
                                                    leg1_last_trade_px, leg2_last_trade_px, True)
                strat_brief_after_fill.pair_buy_side_trading_brief.indicative_consumable_participation_qty = None
                strat_brief_after_fill.pair_buy_side_trading_brief.participation_period_order_qty_sum = None
                # Since sell side of strat_brief is not updated in this test
                strat_brief_after_fill.pair_sell_side_trading_brief = expected_strat_brief_.pair_sell_side_trading_brief
                strat_brief_after_fill.pair_buy_side_trading_brief.last_update_date_time = None
                expected_strat_brief_.pair_buy_side_trading_brief.last_update_date_time = None
                expected_strat_brief_.id = active_pair_strat.id

                # Updating residual_qty and indicative_consumable_residual since handling in
                # update_expected_strat_brief_for_buy is not for this case
                expected_strat_brief_.pair_buy_side_trading_brief.residual_qty = (
                        strat_brief_before_fill.pair_buy_side_trading_brief.residual_qty - filled_qty)
                leg1_last_trade_px, leg2_last_trade_px = get_both_leg_last_trade_px()
                if active_pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
                    buy_last_trade_px = leg1_last_trade_px
                    sell_last_trade_px = leg2_last_trade_px
                else:
                    sell_last_trade_px = leg1_last_trade_px
                    buy_last_trade_px = leg2_last_trade_px
                expected_strat_brief_.pair_buy_side_trading_brief.indicative_consumable_residual = \
                    expected_strat_limits_.residual_restriction.max_residual - \
                    ((expected_strat_brief_.pair_buy_side_trading_brief.residual_qty *
                      get_px_in_usd(buy_last_trade_px)) - (0 * get_px_in_usd(sell_last_trade_px)))
                expected_strat_brief_.pair_buy_side_trading_brief.consumable_open_orders = 5
                assert expected_strat_brief_ == strat_brief_after_fill, \
                    f"Unexpected: Mismatched strat_brief, expected {expected_strat_brief_}, received {strat_brief_list}"
            else:
                for symbol_side_snapshot in symbol_side_snapshot_list:
                    if symbol_side_snapshot.security.sec_id == buy_symbol:
                        other_leg_symbol_side_snapshot_after_fill = symbol_side_snapshot
                        break
                else:
                    assert False, \
                        ("Unexpected: Can't find symbol_side_snapshot having symbol: "
                         f"{latest_order_journal.order.security.sec_id}, "
                         f"order_snapshot_list: {order_snapshot_list}")
                update_expected_strat_brief_for_sell(order_snapshot_after_fill,
                                                     symbol_side_snapshot_after_fill,
                                                     other_leg_symbol_side_snapshot_after_fill,
                                                     expected_strat_limits_, expected_strat_brief_,
                                                     order_snapshot_after_fill.last_update_date_time,
                                                     leg1_last_trade_px, leg2_last_trade_px, True)
                expected_strat_brief_.id = active_pair_strat.id
                # Since buy side of strat_brief is already checked
                strat_brief_after_fill.pair_sell_side_trading_brief.indicative_consumable_participation_qty = None
                strat_brief_after_fill.pair_sell_side_trading_brief.participation_period_order_qty_sum = None
                strat_brief_after_fill.pair_sell_side_trading_brief.last_update_date_time = None
                expected_strat_brief_.pair_sell_side_trading_brief.last_update_date_time = None

                # Updating residual_qty and indicative_consumable_residual since handling in
                # update_expected_strat_brief_for_buy is not for this case
                expected_strat_brief_.pair_sell_side_trading_brief.residual_qty = (
                        strat_brief_before_fill.pair_sell_side_trading_brief.residual_qty - filled_qty)
                leg1_last_trade_px, leg2_last_trade_px = get_both_leg_last_trade_px()
                if active_pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
                    buy_last_trade_px = leg1_last_trade_px
                    sell_last_trade_px = leg2_last_trade_px
                else:
                    sell_last_trade_px = leg1_last_trade_px
                    buy_last_trade_px = leg2_last_trade_px
                expected_strat_brief_.pair_sell_side_trading_brief.indicative_consumable_residual = \
                    expected_strat_limits_.residual_restriction.max_residual - \
                    ((expected_strat_brief_.pair_sell_side_trading_brief.residual_qty *
                      get_px_in_usd(sell_last_trade_px)) -
                     (strat_brief_after_fill.pair_buy_side_trading_brief.residual_qty *
                      get_px_in_usd(buy_last_trade_px)))
                expected_strat_brief_.pair_sell_side_trading_brief.consumable_open_orders = 5

                assert (expected_strat_brief_.pair_sell_side_trading_brief ==
                        strat_brief_after_fill.pair_sell_side_trading_brief), \
                    f"Unexpected: Mismatched strat_brief, expected {expected_strat_brief_}, received {strat_brief_list}"

            # StratStatus Check
            strat_status_after_fill = executor_http_client.get_strat_status_client(active_pair_strat.id)
            if symbol == buy_symbol:
                assert (strat_status_after_fill.total_fill_buy_qty ==
                        strat_status_before_fill.total_fill_buy_qty + filled_qty), \
                    (f"Unexpected: Mismatched strat_status's total_fill_buy_qty, "
                     f"expected {strat_status_before_fill.total_fill_buy_qty + filled_qty}, "
                     f"received {strat_status_after_fill.total_fill_buy_qty}")
                assert strat_status_after_fill.total_fill_buy_notional == (
                        strat_status_before_fill.total_fill_buy_notional +
                        (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))), \
                    (f"Unexpected: Mismatched strat_status's total_fill_buy_notional, "
                     f"expected {strat_status_before_fill.total_fill_buy_notional + (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))}, "
                     f"received {strat_status_after_fill.total_fill_buy_notional}")
                assert strat_status_after_fill.total_fill_exposure == strat_status_after_fill.total_fill_buy_notional, \
                    (f"Unexpected: Mismatched strat_status's total_fill_exposure, "
                     f"expected {strat_status_after_fill.total_fill_buy_notional}, "
                     f"received {strat_status_after_fill.total_fill_exposure}")
                assert strat_status_after_fill.total_cxl_buy_qty == strat_status_before_fill.total_cxl_buy_qty - filled_qty, \
                    (f"Unexpected: Mismatched strat_status's total_cxl_buy_qty, "
                     f"expected {strat_status_before_fill.total_cxl_buy_qty - filled_qty}, "
                     f"received {strat_status_after_fill.total_cxl_buy_qty}")
                assert strat_status_after_fill.total_cxl_buy_notional == (
                        strat_status_before_fill.total_cxl_buy_notional -
                        (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)), \
                    (f"Unexpected: Mismatched strat_status's total_cxl_buy_notional, "
                     f"expected {strat_status_before_fill.total_cxl_buy_notional - (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)}, "
                     f"received {strat_status_after_fill.total_cxl_buy_notional}")
                assert (strat_status_after_fill.total_cxl_exposure ==
                        strat_status_before_fill.total_cxl_exposure -
                        (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)), \
                    (f"Unexpected: Mismatched strat_status's total_cxl_exposure, "
                     f"expected {strat_status_before_fill.total_cxl_exposure - (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)}, "
                     f"received {strat_status_after_fill.total_cxl_exposure}")
                residual_notional = abs((strat_brief_after_fill.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
                    buy_last_trade_px)) -
                                        (strat_brief_after_fill.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
                                            sell_last_trade_px)))
                residual = ResidualOptional(security=active_pair_strat.pair_strat_params.strat_leg1.sec,
                                    residual_notional=residual_notional)
                assert strat_status_after_fill.residual == residual, \
                    (f"Unexpected: Mismatched strat_status's residual, "
                     f"expected {residual}, received {strat_status_after_fill.residual}")
                balance_notional = \
                    expected_strat_limits_.max_single_leg_notional - strat_status_after_fill.total_fill_sell_notional
                assert strat_status_after_fill.balance_notional == balance_notional, \
                    (f"Unexpected: Mismatched strat_status's balance_notional, "
                     f"expected {balance_notional}, received {strat_status_after_fill.balance_notional}")
            else:
                assert (strat_status_after_fill.total_fill_sell_qty ==
                        strat_status_before_fill.total_fill_sell_qty + filled_qty), \
                    (f"Unexpected: Mismatched strat_status's total_fill_sell_qty, "
                     f"expected {strat_status_before_fill.total_fill_sell_qty + filled_qty}, "
                     f"received {strat_status_after_fill.total_fill_sell_qty}")
                assert strat_status_after_fill.total_fill_sell_notional == (
                        strat_status_before_fill.total_fill_sell_notional +
                        (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))), \
                    (f"Unexpected: Mismatched strat_status's total_fill_sell_notional, "
                     f"expected {strat_status_before_fill.total_fill_sell_notional + (filled_qty * get_px_in_usd(fill_journal_obj.fill_px))}, "
                     f"received {strat_status_after_fill.total_fill_sell_notional}")
                assert strat_status_after_fill.total_fill_exposure == (
                        strat_status_after_fill.total_fill_buy_notional -
                        strat_status_after_fill.total_fill_sell_notional), \
                    (f"Unexpected: Mismatched strat_status's total_fill_exposure, "
                     f"expected {strat_status_after_fill.total_fill_buy_notional - strat_status_after_fill.total_fill_sell_notional}, "
                     f"received {strat_status_after_fill.total_fill_exposure}")
                assert strat_status_after_fill.total_cxl_sell_qty == strat_status_before_fill.total_cxl_sell_qty - filled_qty, \
                    (f"Unexpected: Mismatched strat_status's total_cxl_sell_qty, "
                     f"expected {strat_status_before_fill.total_cxl_sell_qty - filled_qty}, "
                     f"received {strat_status_after_fill.total_cxl_sell_qty}")
                assert strat_status_after_fill.total_cxl_sell_notional == (
                        strat_status_before_fill.total_cxl_sell_notional -
                        (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)), \
                    (f"Unexpected: Mismatched strat_status's total_cxl_sell_notional, "
                     f"expected {strat_status_before_fill.total_cxl_sell_notional - (get_px_in_usd(order_snapshot_after_fill.order_brief.px) * filled_qty)}, "
                     f"received {strat_status_after_fill.total_cxl_sell_notional}")
                assert (strat_status_after_fill.total_cxl_exposure ==
                        strat_status_after_fill.total_cxl_buy_notional - strat_status_after_fill.total_cxl_sell_notional), \
                    (f"Unexpected: Mismatched strat_status's total_cxl_exposure, "
                     f"expected {strat_status_after_fill.total_cxl_buy_notional - (strat_status_after_fill.total_fill_sell_notional + (filled_qty * get_px_in_usd(fill_journal_obj.fill_px)))}, "
                     f"received {strat_status_after_fill.total_cxl_exposure}")
                residual_notional = abs(
                    (strat_brief_after_fill.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
                        buy_last_trade_px)) -
                    (strat_brief_after_fill.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
                        sell_last_trade_px)))
                residual = ResidualOptional(
                    security=active_pair_strat.pair_strat_params.strat_leg1.sec,
                    residual_notional=residual_notional)
                assert strat_status_after_fill.residual == residual, \
                    (f"Unexpected: Mismatched strat_status's residual, "
                     f"expected {residual}, received {strat_status_after_fill.residual}")
                balance_notional = \
                    expected_strat_limits_.max_single_leg_notional - strat_status_after_fill.total_fill_buy_notional
                assert strat_status_after_fill.balance_notional == balance_notional, \
                    (f"Unexpected: Mismatched strat_status's balance_notional, "
                     f"expected {balance_notional}, received {strat_status_after_fill.balance_notional}")

            # Checking portfolio_status
            portfolio_status_after_fill = email_book_service_native_web_client.get_portfolio_status_client(1)
            if symbol == buy_symbol:
                assert portfolio_status_after_fill.overall_buy_notional == (
                        portfolio_status_before_fill.overall_buy_notional + placed_fill_journal_obj.fill_notional), \
                    (f"Unexpected: Mismatched portfolio_status's overall_buy_notional, "
                     f"expected {portfolio_status_before_fill.overall_buy_notional + placed_fill_journal_obj.fill_notional}, "
                     f"received {portfolio_status_after_fill.overall_buy_notional}")
                assert portfolio_status_after_fill.overall_buy_fill_notional == (
                        portfolio_status_before_fill.overall_buy_fill_notional + placed_fill_journal_obj.fill_notional), \
                    (f"Unexpected: Mismatched portfolio_status's overall_buy_fill_notional, "
                     f"expected {portfolio_status_before_fill.overall_buy_fill_notional + placed_fill_journal_obj.fill_notional}, "
                     f"received {portfolio_status_after_fill.overall_buy_fill_notional}")
            else:
                assert portfolio_status_after_fill.overall_sell_notional == (
                        portfolio_status_before_fill.overall_sell_notional + placed_fill_journal_obj.fill_notional), \
                    (f"Unexpected: Mismatched portfolio_status's overall_buy_notional, "
                     f"expected {portfolio_status_before_fill.overall_sell_notional + placed_fill_journal_obj.fill_notional}, "
                     f"received {portfolio_status_after_fill.overall_sell_notional}")
                assert portfolio_status_after_fill.overall_sell_fill_notional == (
                        portfolio_status_before_fill.overall_sell_fill_notional + placed_fill_journal_obj.fill_notional), \
                    (f"Unexpected: Mismatched portfolio_status's overall_buy_fill_notional, "
                     f"expected {portfolio_status_before_fill.overall_sell_fill_notional + placed_fill_journal_obj.fill_notional}, "
                     f"received {portfolio_status_after_fill.overall_sell_fill_notional}")

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
def test_unload_reload_strat_from_collection(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.trade_simulator_reload_config_query_client()

        total_order_count_for_each_side = 2
        place_sanity_orders_for_executor(
            buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
            top_of_book_list_, residual_wait_sec, executor_web_client)

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

        executor_http_client.trade_simulator_reload_config_query_client()

        # To update tob without triggering any order
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0], avoid_order_trigger=True)

        total_order_count_for_each_side = 2
        place_sanity_orders_for_executor(
            buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
            top_of_book_list_, residual_wait_sec, executor_http_client, True)

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
        expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side,
        expected_order_limits_, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    # First created strat is already active, checking if next strat, if tries to get activated with same symbol-side
    # gets exception

    try:
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))
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
        expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side,
        expected_order_limits_, refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_, leg1_side=Side.SELL,
                                           leg2_side=Side.BUY))

    # First created strat is already active, checking if next strat, if tries to get activated with same symbol-side
    # gets exception

    try:
        created_pair_strat, executor_http_client = (
            create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list,
                                               last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_, leg1_side=Side.SELL,
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
        expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side,
        expected_order_limits_, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # updating order_limits
    expected_order_limits_.min_order_notional = 15000
    expected_order_limits_.id = 1
    email_book_service_native_web_client.put_order_limits_client(expected_order_limits_, return_obj_copy=False)

    expected_strat_limits_.max_single_leg_notional = 18000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, Side.BUY)

    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_opp_symbol_strat_activate_block_in_single_day_with_buy_first(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
        expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side, expected_order_limits_,
        refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # updating order_limits
    expected_order_limits_.min_order_notional = 15000
    expected_order_limits_.id = 1
    email_book_service_native_web_client.put_order_limits_client(expected_order_limits_, return_obj_copy=False)

    expected_strat_limits_.max_single_leg_notional = 18000
    strat_done_after_exhausted_consumable_notional(
        leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, Side.BUY)

    try:
        strat_done_after_exhausted_consumable_notional(
            leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
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
        expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side, expected_order_limits_,
        refresh_sec_update_fixture):
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # updating order_limits
    expected_order_limits_.min_order_notional = 15000
    expected_order_limits_.id = 1
    email_book_service_native_web_client.put_order_limits_client(expected_order_limits_, return_obj_copy=False)

    expected_strat_limits_.max_single_leg_notional = 18000
    strat_done_after_exhausted_consumable_notional(
        leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, Side.SELL, leg_1_side=Side.SELL, leg_2_side=Side.BUY)

    try:
        strat_done_after_exhausted_consumable_notional(
            leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
            symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
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
        expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side, expected_order_limits_,
        refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]

    # updating order_limits
    expected_order_limits_.min_order_notional = 15000
    expected_order_limits_.id = 1
    email_book_service_native_web_client.put_order_limits_client(expected_order_limits_, return_obj_copy=False)

    expected_strat_limits_.max_single_leg_notional = 18000
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, Side.BUY)

    buy_symbol = leg1_leg2_symbol_list[1][0]
    sell_symbol = leg1_leg2_symbol_list[1][1]
    strat_done_after_exhausted_consumable_notional(
        buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
        refresh_sec_update_fixture, Side.BUY)


@pytest.mark.nightly
def test_reactivate_after_pause_strat(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        top_of_book_list_, market_depth_basemodel_list, last_trade_fixture_list,
        refresh_sec_update_fixture):
    # creates and activates multiple pair_strats
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_strat, executor_http_client = (
        create_n_activate_strat(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                expected_strat_status_, symbol_overview_obj_list, top_of_book_list_,
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

        executor_http_client.trade_simulator_reload_config_query_client()

        time.sleep(2)
        pause_pair_strat = PairStratBaseModel(_id=activated_pair_strat.id, strat_state=StratState.StratState_PAUSED)
        email_book_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(pause_pair_strat, by_alias=True, exclude_none=True))

        time.sleep(2)
        reactivate_pair_strat = PairStratBaseModel(_id=activated_pair_strat.id, strat_state=StratState.StratState_ACTIVE)
        email_book_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(reactivate_pair_strat, by_alias=True, exclude_none=True))

        time.sleep(2)
        total_order_count_for_each_side = 2
        place_sanity_orders_for_executor(
            buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
            top_of_book_list_, residual_wait_sec, executor_http_client)
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
                                   top_of_book_list_, market_depth_basemodel_list, last_trade_fixture_list,
                                   refresh_sec_update_fixture):
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    active_strat_list: List[PairStratBaseModel] = []
    for buy_symbol, sell_symbol in leg1_leg2_symbol_list[:2]:
        activated_pair_strat, executor_web_client = (
            create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                               expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                               market_depth_basemodel_list, top_of_book_list_))
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
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list,
        refresh_sec):
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    loop_count = 2000
    for i in range(loop_count):
        if i % 2 == 0:
            strat_view_obj = StratViewBaseModel(_id=created_pair_strat.id, market_premium=i)
        else:
            strat_view_obj = StratViewBaseModel(_id=created_pair_strat.id, balance_notional=i)
        email_book_service_native_web_client.patch_strat_view_client(jsonable_encoder(strat_view_obj, by_alias=True,
                                                                                         exclude_none=True))

    updated_strat_view = email_book_service_native_web_client.get_strat_view_client(created_pair_strat.id)
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
        top_of_book_list_, market_depth_basemodel_list, last_trade_fixture_list,
        refresh_sec_update_fixture):
    symbols_n_strat_state_list = leg1_leg2_symbol_list
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_frequent_update_strat_view_in_strat, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
                                   deepcopy(symbol_overview_obj_list), deepcopy(top_of_book_list_),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   refresh_sec_update_fixture)
                   for buy_symbol, sell_symbol in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


# def test_log_trade_simulator_trigger_kill_switch_and_resume_trading():
#     log_dir: PurePath = PurePath(
#         __file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "phone_book" / "log "
#     configure_logger("debug", str(log_dir), "test_log_trade_simulator.log")
#
#     LogTradeSimulator.trigger_kill_switch()
#     time.sleep(5)
#
#     portfolio_status_id = 1
#     portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(portfolio_status_id)
#     assert portfolio_status.kill_switch
#
#     LogTradeSimulator.revoke_kill_switch_n_resume_trading()
#     time.sleep(5)
#
#     portfolio_status = email_book_service_native_web_client.get_portfolio_status_client(portfolio_status_id)
#     assert not portfolio_status.kill_switch

