# system imports
import json
import asyncio
from typing import List, Any, Dict, Final, Callable, Type
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException
from copy import deepcopy
from pathlib import PurePath
from dataclasses import dataclass
import copy

# 3rd party packages
import motor.motor_asyncio
from pymongo import UpdateOne
import pymongo.results
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
import orjson

# project specific imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultDataclassWebResponse
from Flux.PyCodeGenEngine.FluxCodeGenCore.ws_connection_manager import WSData
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error
from FluxPythonUtils.scripts.general_utility_functions import (
    execute_tasks_list_with_all_completed, handle_ws, compare_n_patch_dict, compare_n_patch_list)
from FluxPythonUtils.scripts.model_base_utils import JsonNDataClassHandler
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_route_utils import get_aggregate_pipeline, generic_perf_benchmark

"""
1. FilterAggregate [only filters the returned value]
2. UpdateAggregate [ modifies data in DB based on aggregate query and returns updated data ]
3. Create : FilterAggregate for return param and UpdateAggregate for massaging data post insert
4. Read, ReadAll : FilterAggregate for return param
5. Delete : UpdateAggregate for massaging data post delete
"""

# Todo: Direct mongo handling for db doesn't support Links yet

id_not_found: Final[DefaultDataclassWebResponse] = DefaultDataclassWebResponse(msg="Id not Found")
del_success: Final[DefaultDataclassWebResponse] = DefaultDataclassWebResponse(msg="Deletion Successful")
code_gen_projects_path = PurePath(__file__).parent.parent.parent / "CodeGenProjects"


def validate_ws_connection_managers_in_pydantic_obj(pydantic_class_type: Type[dataclass]):
    if (not pydantic_class_type.read_ws_path_ws_connection_manager) or \
            (not pydantic_class_type.read_ws_path_with_id_ws_connection_manager):
        err: str = f"unexpected: publish_ws invoked on pydantic_class_type with missing either " \
                   f"read_ws_path_ws_connection_manager or read_ws_path_with_id_ws_connection_manager: " \
                   f"pydantic_class_type {pydantic_class_type}"
        logging.exception(err)
        raise Exception(err)


async def broadcast_all_from_active_ws_data_set(active_ws_data_set: List[WSData],
                                                dataclass_class_type: Type[dataclass],
                                                db_obj_id_list: List[Any],
                                                broadcast_callable: Callable,
                                                tasks_list: List[asyncio.Task],
                                                dummy_dataclass_model: Type[dataclass] | None = None,
                                                filter_agg_pipeline: Dict | None = None,
                                                has_links: bool | None = None):
    for ws_data in active_ws_data_set:
        projection_model = ws_data.projection_model
        projection_agg_params = ws_data.filter_callable_kwargs
        projection_agg_pipeline_callable = ws_data.projection_agg_pipeline_callable

        if projection_agg_pipeline_callable is not None:
            projection_agg_params["id_list"] = db_obj_id_list
            filter_agg_pipeline = projection_agg_pipeline_callable(**projection_agg_params)

        if dummy_dataclass_model is not None:
            # if call is for delete operation
            json_obj_list: List = []
            for pydantic_obj_id in db_obj_id_list:
                json_obj_list.append({'_id': pydantic_obj_id})
        else:
            # if call is for update/create operation
            json_obj_list = await get_obj_list(dataclass_class_type, db_obj_id_list,
                                               filter_agg_pipeline=filter_agg_pipeline,
                                               has_links=has_links, projection_model=projection_model)
        if json_obj_list:
            json_str = orjson.dumps(json_obj_list, default=str)
            await broadcast_callable(json_str, ws_data, tasks_list)
        # else not required: not going to broadcast if not a valid update for this ws


async def broadcast_from_active_ws_data_set(active_ws_data_set: List[WSData], pydantic_class_type: Type[dataclass],
                                            pydantic_obj_id: Any,
                                            broadcast_callable: Callable,
                                            tasks_list: List[asyncio.Task],
                                            broadcast_with_id: bool | None = None,
                                            dummy_pydantic_model: Type[dataclass] | None = None,
                                            filter_agg_pipeline: Dict | None = None,
                                            has_links: bool | None = None):
    for ws_data in active_ws_data_set:
        projection_model = ws_data.projection_model
        projection_agg_params = ws_data.filter_callable_kwargs
        projection_agg_pipeline_callable = ws_data.projection_agg_pipeline_callable

        if projection_agg_pipeline_callable is not None:
            projection_agg_params["id_list"] = [pydantic_obj_id]
            filter_agg_pipeline = projection_agg_pipeline_callable(**projection_agg_params)

        if dummy_pydantic_model is not None:
            # if call is for delete operation
            json_obj: Dict = {'_id': pydantic_obj_id}
        else:
            # if call is for update/create operation
            json_obj = await get_obj(pydantic_class_type, pydantic_obj_id,
                                     filter_agg_pipeline=filter_agg_pipeline,
                                     has_links=has_links, projection_model=projection_model)

        if json_obj is not None:
            json_str = json.dumps(json_obj, default=str)
            if broadcast_with_id:
                await broadcast_callable(json_str, pydantic_obj_id, ws_data, tasks_list)
            else:
                await broadcast_callable(json_str, ws_data, tasks_list)
        # else not required: not going to broadcast if not a valid update for this ws


async def publish_ws(dataclass_class_type: Type[dataclass], db_obj_id: Any,
                     filter_agg_pipeline: Dict | None = None, has_links: bool | None = None,
                     update_ws_with_id: bool | None = None, dummy_dataclass_model: Type[dataclass] | None = None):
    """
    :param dataclass_class_type: Dataclass SubClass Type
    :param db_obj_id: db_obj_id for create/update/delete
    :param filter_agg_pipeline: filter aggregation pipeline
    :param has_links: bool for has_links
    :param update_ws_with_id: [Optional] bool to update ws with id
    :param dummy_dataclass_model: [Optional] dummy pydantic basemodel type for delete case
    """
    validate_ws_connection_managers_in_pydantic_obj(dataclass_class_type)
    tasks_list: List[asyncio.Task] = []
    active_ws_data_list: List[WSData] = dataclass_class_type.read_ws_path_ws_connection_manager.get_activ_ws_data_list()
    if active_ws_data_list:
        async with dataclass_class_type.read_ws_path_ws_connection_manager.rlock:
            await broadcast_from_active_ws_data_set(active_ws_data_list, dataclass_class_type, db_obj_id,
                                                    dataclass_class_type.read_ws_path_ws_connection_manager.broadcast,
                                                    tasks_list, dummy_pydantic_model=dummy_dataclass_model,
                                                    filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
    if update_ws_with_id:
        active_ws_data_list_for_id: List[WSData] = \
            dataclass_class_type.read_ws_path_with_id_ws_connection_manager.get_activ_ws_tuple_list_with_id(
                db_obj_id)

        if active_ws_data_list_for_id:
            async with dataclass_class_type.read_ws_path_with_id_ws_connection_manager.rlock:
                await broadcast_from_active_ws_data_set(
                    active_ws_data_list_for_id, dataclass_class_type, db_obj_id,
                    dataclass_class_type.read_ws_path_with_id_ws_connection_manager.broadcast,
                    tasks_list, broadcast_with_id=True, dummy_pydantic_model=dummy_dataclass_model,
                    filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
    if tasks_list:
        await execute_tasks_list_with_all_completed(tasks_list, dataclass_class_type)


async def publish_ws_all(dataclass_class_type: Type[dataclass], db_obj_id_list: List[Any],
                         filter_agg_pipeline: Dict | None = None, has_links: bool | None = None,
                         update_ws_with_id: bool | None = None, dummy_dataclass_model: Type[dataclass] | None = None):
    """
    :param dataclass_class_type: dataclass SubClass Type
    :param db_obj_id_list: List of db_obj_ids for create/update/delete
    :param filter_agg_pipeline: filter aggregation pipeline
    :param has_links: bool for has_links
    :param update_ws_with_id: bool to update ws with id
    :param dummy_dataclass_model: [Optional] dummy pydantic basemodel type for delete case
    """
    validate_ws_connection_managers_in_pydantic_obj(dataclass_class_type)
    tasks_list: List[asyncio.Task] = []

    active_ws_data_list: List[WSData] = dataclass_class_type.read_ws_path_ws_connection_manager.get_activ_ws_data_list()
    if active_ws_data_list:
        async with dataclass_class_type.read_ws_path_ws_connection_manager.rlock:
            await broadcast_all_from_active_ws_data_set(active_ws_data_list, dataclass_class_type,
                                                        db_obj_id_list,
                                                        dataclass_class_type.read_ws_path_ws_connection_manager.broadcast,
                                                        tasks_list, dummy_dataclass_model, filter_agg_pipeline,
                                                        has_links)
    # TODO: this can be optimized by sending array of messages to ws instead of sending one message at a time per ws
    #       in most use-case the consumer of one id is interested in all ids.
    if update_ws_with_id:
        for pydantic_obj_id in db_obj_id_list:
            active_ws_data_list_for_id: List[WSData] = \
                dataclass_class_type.read_ws_path_with_id_ws_connection_manager.get_activ_ws_tuple_list_with_id(
                    pydantic_obj_id)

            if active_ws_data_list_for_id:
                async with dataclass_class_type.read_ws_path_with_id_ws_connection_manager.rlock:
                    await broadcast_from_active_ws_data_set(
                        active_ws_data_list_for_id, dataclass_class_type, pydantic_obj_id,
                        dataclass_class_type.read_ws_path_with_id_ws_connection_manager.broadcast,
                        tasks_list, broadcast_with_id=True, dummy_pydantic_model=dummy_dataclass_model,
                        filter_agg_pipeline=filter_agg_pipeline, has_links=has_links
                    )
    if tasks_list:
        await execute_tasks_list_with_all_completed(tasks_list, dataclass_class_type)


async def _update_time_series(
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection, id_list: List[str | int | Any],
        new_json_obj_list: List[Dict[str, Any]]):
    # TimeSeries has limitations when it comes to update:
    # https://www.mongodb.com/docs/manual/core/timeseries/timeseries-limitations/#updates
    # We have implemented alternative way to avoid limitations
    logging.info("Warning: Update using aggregate pipeline is expensive in time_series - "
                 "time-series have limitations for which we have implemented alternative but expensive way")

    # first deleting all update objects
    delete_result = await collection_obj.delete_many({"_id": {'$in': id_list}})

    # creating new objects with updated values
    await collection_obj.insert_many(new_json_obj_list)


async def execute_update_agg_pipeline(dataclass_class_type: Type[dataclass],
                                      proto_package_name: str, update_agg_pipeline: Any = None):
    if update_agg_pipeline is not None:
        aggregated_dict_list: List[Dict]
        aggregated_dict_list = await generic_read_http(dataclass_class_type, proto_package_name,
                                                       filter_agg_pipeline=update_agg_pipeline)

        id_list = []
        update_req_list = []
        for aggregated_dict in aggregated_dict_list:
            db_id = aggregated_dict.get('_id')
            id_list.append(db_id)

            if not dataclass_class_type.is_time_series:
                update_req_list.append(UpdateOne({"_id": db_id}, {"$set": aggregated_dict}))
            # else not required: if model is time series then delete and new insert is done due to unsupported
            # updates in time-series (check below)

        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj

        if dataclass_class_type.is_time_series:
            await _update_time_series(collection_obj, id_list, aggregated_dict_list)
        else:
            await collection_obj.bulk_write(update_req_list)
        await publish_ws_all(dataclass_class_type, id_list, update_ws_with_id=True)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_http(dataclass_class_type: Type[dataclass],
                            proto_package_name: str, json_n_dataclass_handler: JsonNDataClassHandler,
                            filter_agg_pipeline: Any = None,
                            update_agg_pipeline: Any = None, has_links: bool = False,
                            return_obj_copy: bool | None = True) -> Dict[str, Any] | bool:
    if json_n_dataclass_handler.dataclass_obj is None:
        obj_json = json_n_dataclass_handler.json_dict
    else:
        # obj_json = jsonable_encoder(json_n_dataclass_handler.dataclass_obj)
        obj_json_str = orjson.dumps(json_n_dataclass_handler.dataclass_obj.__dict__, default=str)
        obj_json = orjson.loads(obj_json_str)
        # obj_json = json_n_dataclass_handler.dataclass_obj.__dict__
        json_n_dataclass_handler.set_json_dict(obj_json)    # updated json obj

    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj
    insert_one_result: pymongo.results.InsertOneResult = await collection_obj.insert_one(obj_json)

    await execute_update_agg_pipeline(dataclass_class_type, proto_package_name, update_agg_pipeline)

    await publish_ws(dataclass_class_type, insert_one_result.inserted_id, filter_agg_pipeline, has_links)

    if return_obj_copy:
        fetched_obj = await get_obj(dataclass_class_type, insert_one_result.inserted_id,
                                    filter_agg_pipeline, has_links)
        return fetched_obj
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_all_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                                json_n_dataclass_handler: JsonNDataClassHandler,
                                filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                                has_links: bool = False, return_obj_copy: bool | None = True) -> List[dataclass] | bool:
    if json_n_dataclass_handler.dataclass_obj is None:
        obj_json_list = json_n_dataclass_handler.json_dict_list
    else:
        # obj_json_list = jsonable_encoder(json_n_dataclass_handler.dataclass_obj, exclude_none=True)
        # obj_json_list_str = orjson.dumps([obj.__dict__ for obj in json_n_dataclass_handler.dataclass_obj_list], default=str)
        # obj_json_list = orjson.loads(obj_json_list_str)
        obj_json_list = [obj.__dict__ for obj in json_n_dataclass_handler.dataclass_obj_list]
        json_n_dataclass_handler.set_json_dict_list(obj_json_list)    # updated json obj

    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj
    insert_many_result: pymongo.results.InsertManyResult = await collection_obj.insert_many(obj_json_list)

    await execute_update_agg_pipeline(dataclass_class_type, proto_package_name, update_agg_pipeline)
    await publish_ws_all(dataclass_class_type, insert_many_result.inserted_ids, filter_agg_pipeline, has_links)

    if return_obj_copy:
        fetched_obj_list = await get_obj_list(dataclass_class_type, insert_many_result.inserted_ids,
                                              filter_agg_pipeline, has_links)
        return fetched_obj_list
    else:
        return True


# def _get_beanie_formatted_update_request_json(updated_pydantic_obj_dict: Dict):
#     # creating new obj without id and _id key
#     request_obj = {'$set': updated_pydantic_obj_dict.items()}
#     return request_obj


async def _underlying_patch_n_put(dataclass_class_type: Type[dataclass], proto_package_name: str,
                                  updated_json_obj_dict: Dict, filter_agg_pipeline: Any = None,
                                  update_agg_pipeline: Any = None, has_links: bool = False,
                                  return_obj_copy: bool | None = True) -> Dict[str, Any] | bool:
    """
        Underlying interface for Single object Put & Patch
    """
    _id = updated_json_obj_dict.get("_id")

    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj

    # todo: No has_link impl for tme series yet
    if dataclass_class_type.is_time_series:
        await _update_time_series(collection_obj, [_id], [updated_json_obj_dict])

    else:
        update_one_result: pymongo.results.UpdateResult = \
            await collection_obj.update_one({"_id": _id}, {"$set": updated_json_obj_dict})
    await execute_update_agg_pipeline(dataclass_class_type, proto_package_name, update_agg_pipeline)

    return_value: Dict[str, Any] | bool
    if return_obj_copy:
        return_value = await get_obj(dataclass_class_type, _id,
                                     filter_agg_pipeline, has_links)
    else:
        return_value = True

    await publish_ws(dataclass_class_type, _id, filter_agg_pipeline, has_links, update_ws_with_id=True)
    return return_value


async def _underlying_patch_n_put_all(dataclass_class_type: Type[dataclass], proto_package_name: str,
                                      updated_json_obj_dict_list: List[Dict[str, Any]],
                                      updated_obj_id_list: List[Any] | None = None,
                                      filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                                      has_links: bool = False, return_obj_copy: bool | None = True
                                      ) -> List[Dict[str, Any]] | bool:
    """
    Underlying interface for Put-All & Patch-All
    """
    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj

    if dataclass_class_type.is_time_series:
        await _update_time_series(collection_obj, updated_obj_id_list, updated_json_obj_dict_list)
    else:
        update_req_list: List[UpdateOne] = []
        for updated_json_obj_dict in updated_json_obj_dict_list:
            _id = updated_json_obj_dict.get("_id")
            update_req_list.append(UpdateOne({"_id": _id}, {"$set": updated_json_obj_dict}))
        await collection_obj.bulk_write(update_req_list)

    await execute_update_agg_pipeline(dataclass_class_type, proto_package_name, update_agg_pipeline)
    await publish_ws_all(dataclass_class_type, updated_obj_id_list, filter_agg_pipeline, has_links, update_ws_with_id=True)

    if return_obj_copy:
        stored_obj_list = await get_obj_list(dataclass_class_type, updated_obj_id_list,
                                             filter_agg_pipeline, has_links)
        return stored_obj_list
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_http(pydantic_class_type: Type[dataclass], proto_package_name: str,
                           json_n_data_class_handler: JsonNDataClassHandler, filter_agg_pipeline: Any = None,
                           update_agg_pipeline: Any = None, has_links: bool = False,
                           return_obj_copy: bool | None = True) -> Dict[str, Any] | bool:
    if json_n_data_class_handler.dataclass_obj is None:
        obj_json = json_n_data_class_handler.json_dict
    else:
        # obj_json = jsonable_encoder(json_n_data_class_handler.dataclass_obj, exclude_none=True)
        # obj_json_str = orjson.dumps(json_n_data_class_handler.dataclass_obj.__dict__, default=str)
        # obj_json = orjson.loads(obj_json_str)
        obj_json = json_n_data_class_handler.dataclass_obj.__dict__
        json_n_data_class_handler.set_json_dict(obj_json)  # updated json obj

    # stored_update_id_val = stored_json_obj.get("updated_id")
    # new_updated_id_val = obj_json.get("updated_id")
    # if stored_update_id_val is not None and stored_update_id_val == new_updated_id_val:
        # this is for cases where fetched object is passed as update object with slight changes. In these cases,
        # update id since is set as last stored value will not be increased automatically
    obj_json["update_id"] = pydantic_class_type.next_update_id()

    updated_stored_json_obj = \
        await _underlying_patch_n_put(pydantic_class_type, proto_package_name,
                                      obj_json, filter_agg_pipeline, update_agg_pipeline, has_links,
                                      return_obj_copy)
    return updated_stored_json_obj


# def get_stored_obj_id_to_obj_dict(stored_pydantic_obj_list: List[dataclass]) -> Dict[int, str]:
#     stored_obj_id_to_obj_dict: Dict[int, str] = {}
#     for stored_pydantic_obj in stored_pydantic_obj_list:
#         if stored_pydantic_obj.id not in stored_obj_id_to_obj_dict:
#             stored_obj_id_to_obj_dict[stored_pydantic_obj.id] = stored_pydantic_obj
#     return stored_obj_id_to_obj_dict
#
#
# def _generic_put_all_http(stored_pydantic_obj_list: List[DocumentModel],
#                           updated_pydantic_obj_list: List[DocumentModel]) -> List[Tuple[DocumentModel, Dict]]:
#     stored_obj_id_to_obj_dict = get_stored_obj_id_to_obj_dict(stored_pydantic_obj_list)
#
#     stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = []
#     for index in range(len(updated_pydantic_obj_list)):
#         stored_pydantic_obj_n_updated_obj_dict_tuple_list.append(
#             (stored_obj_id_to_obj_dict[updated_pydantic_obj_list[index].id],
#              updated_pydantic_obj_list[index].model_dump(by_alias=True)))
#     return stored_pydantic_obj_n_updated_obj_dict_tuple_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_all_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                               json_n_data_class_handler: JsonNDataClassHandler, updated_obj_id_list: List[Any],
                               filter_agg_pipeline: Any = None,
                               update_agg_pipeline: Any = None, has_links: bool = False,
                               return_obj_copy: bool | None = True) -> List[Dict[str, Any]] | bool:
    if json_n_data_class_handler.dataclass_obj_list is None:
        obj_json_list = json_n_data_class_handler.json_dict_list
    else:
        # obj_json_list = jsonable_encoder(json_n_data_class_handler.dataclass_obj_list, exclude_none=True)
        # obj_json_list_str = orjson.dumps([obj.__dict__ for obj in json_n_data_class_handler.dataclass_obj_list], default=str)
        # obj_json_list = orjson.loads(obj_json_list_str)
        obj_json_list = [obj.__dict__ for obj in json_n_data_class_handler.dataclass_obj_list]
        json_n_data_class_handler.set_json_dict(obj_json_list)  # updated json obj
    return await _underlying_patch_n_put_all(dataclass_class_type, proto_package_name,
                                             obj_json_list,
                                             updated_obj_id_list, filter_agg_pipeline,
                                             update_agg_pipeline, has_links, return_obj_copy)

#
# def _assign_missing_ids_n_handle_date_time_type(field_model_type: Type[Any],
#                                                 key: str,
#                                                 value: Any,
#                                                 pydantic_obj_update_json: Dict,
#                                                 ignore_handling_datetime: bool | None = False):
#     if (isinstance(field_model_type, types.UnionType) or (type(field_model_type) == typing._UnionGenericAlias) or
#             field_model_type.__name__ == "List"):
#         if issubclass(field_model_type.__args__[0], BaseModel):
#             for val in value:
#                 assign_missing_ids_n_handle_date_time_type(
#                     field_model_type.__args__[0], val, ignore_root_id_check=False,
#                     ignore_handling_datetime=ignore_handling_datetime)
#
#                 if field_model_type.__args__[0].model_fields.get("id") is not None:
#                     if val.get("_id") is None:
#                         val["_id"] = (
#                             field_model_type.__args__[0].model_fields.get("id").default_factory())
#         else:
#             # since JSON has no support to Datetime when receiving pydantic_obj_update_json
#             # all datetime type fields would be of str type
#             if (not ignore_handling_datetime) and issubclass(field_model_type.__args__[0],
#                                                              datetime.datetime):
#                 if isinstance(value, str):
#                     # Setting values parsed as str back to Datetime type
#                     pydantic_obj_update_json[key] = pendulum.parse(value)
#     else:
#         if issubclass(field_model_type, BaseModel):
#             assign_missing_ids_n_handle_date_time_type(field_model_type, value,
#                                                        ignore_root_id_check=False,
#                                                        ignore_handling_datetime=
#                                                        ignore_handling_datetime)
#
#             if field_model_type.model_fields.get("id") is not None:
#                 if value.get("_id") is None:
#                     value["_id"] = field_model_type.model_fields.get("id").default_factory()
#         else:
#             # since JSON has no support to Datetime when receiving pydantic_obj_update_json
#             # all datetime type fields would be of str type
#             if (not ignore_handling_datetime) and "DateTime" in field_model_type.__name__:
#                 if isinstance(value, str):
#                     # Setting values parsed as str back to Datetime type
#                     pydantic_obj_update_json[key] = pendulum.parse(value)
#
#
# def assign_missing_ids_n_handle_date_time_type(pydantic_class_type: Type[DocumentModel] | Type[PydanticModel],
#                                                pydantic_obj_update_json: Dict,
#                                                ignore_root_id_check: bool | None = True,
#                                                ignore_handling_datetime: bool | None = False):
#     """
#     Handling for patch if any model in json has id field as mandatory field but is not set, sets the id field
#     with new id of same type
#     Reason: Since patch web client takes json as parameter instead of particular model instance that's why
#     id field is not autogenerated, and if there is some use-case that can't provide id (ex: Web UI), we have
#     to add id explicitly before saving in db
#     """
#     for key, value in pydantic_obj_update_json.items():
#         if value is not None:
#             if ignore_root_id_check:
#                 if key == "_id":
#                     ignore_root_id_check = False
#                     continue
#             field_model: FieldInfo
#             if (field_model := pydantic_class_type.model_fields.get(key)) is not None:
#                 field_model_type = field_model.annotation
#                 if ((issubclass(type(field_model_type), UnionType)) or
#                         (field_model_type.__name__ == "Optional")):
#                     # entering here suggests that field contains None with main type
#                     field_model_type_tuple: Tuple = field_model_type.__args__
#                     type_other_than_none: Type[Any]
#                     for field_model_type_ in field_model_type_tuple:
#                         if field_model_type_.__name__ == "List" or not isinstance(None, field_model_type_):
#                             type_other_than_none = field_model_type_
#                             break
#                     else:
#                         raise Exception("Field type from annotation is Tuple signifying, field must be optional, "
#                                         "nut couldn't find any Type other than NoneType in tuple annotation, "
#                                         f"field_model_type: {field_model_type}, field_name: {key}, "
#                                         f"pydantic_class_type: {pydantic_class_type.__name__}")
#
#                     _assign_missing_ids_n_handle_date_time_type(type_other_than_none, key, value,
#                                                                 pydantic_obj_update_json,
#                                                                 ignore_handling_datetime)
#                 else:
#                     _assign_missing_ids_n_handle_date_time_type(field_model_type, key, value, pydantic_obj_update_json,
#                                                                 ignore_handling_datetime)
#

@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                             json_n_data_class_handler: JsonNDataClassHandler,
                             filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                             has_links: bool = False, return_obj_copy: bool | None = True
                             ) -> Dict[str, Any] | bool:
    if json_n_data_class_handler.dataclass_obj is None:
        obj_json = json_n_data_class_handler.json_dict
    else:
        # obj_json = jsonable_encoder(json_n_data_class_handler.dataclass_obj, exclude_none=True)
        # obj_json_str = orjson.dumps(json_n_data_class_handler.dataclass_obj.__dict__, default=str)
        # obj_json = orjson.loads(obj_json_str)
        obj_json = json_n_data_class_handler.dataclass_obj.__dict__
        json_n_data_class_handler.set_json_dict(obj_json)  # updated json obj

    # since patch not call's default_factory of update_id
    obj_json["update_id"] = dataclass_class_type.next_update_id()
    # assign_missing_ids_n_handle_date_time_type(dataclass_class_type, obj_json)

    stored_json_obj = json_n_data_class_handler.stored_json_dict
    try:
        updated_json_dict = compare_n_patch_dict(copy.deepcopy(stored_json_obj), obj_json)
    except Exception as e:
        err_str = f"compare_n_patch_dict failed: exception: {e}"
        logging.exception(err_str)
        raise HTTPException(detail=err_str, status_code=400)

    updated_stored_json_obj = \
        await _underlying_patch_n_put(dataclass_class_type, proto_package_name,
                                      updated_json_dict, filter_agg_pipeline, update_agg_pipeline,
                                      has_links, return_obj_copy)
    return updated_stored_json_obj


# @http_except_n_log_error(status_code=500)
# @generic_perf_benchmark
# async def generic_patch_without_db_update_http(
#         pydantic_class_type: Type[dataclass],
#         stored_pydantic_obj: dataclass, json_n_data_class_handler: JsonNDataClassHandler,
#         return_obj_copy: bool | None = True) -> Dict[str, Any] | bool:
#     if json_n_data_class_handler.dataclass_obj is None:
#         obj_json = json_n_data_class_handler.json_dict
#     else:
#         obj_json = jsonable_encoder(json_n_data_class_handler.dataclass_obj, exclude_none=True)
#         json_n_data_class_handler.set_json_dict(obj_json)  # updated json obj
#
#     # assign_missing_ids_n_handle_date_time_type(pydantic_class_type, obj_json)
#     # try:
#     #     updated_pydantic_obj_dict = compare_n_patch_dict(stored_pydantic_obj.model_dump(by_alias=True),
#     #                                                      pydantic_obj_update_json)
#     # except Exception as e:
#     #     err_str = f"compare_n_patch_dict failed: exception: {e}"
#     #     logging.exception(err_str)
#     #     raise HTTPException(detail=err_str, status_code=400)
#     if return_obj_copy:
#         return obj_json
#         # return pydantic_class_type(**updated_pydantic_obj_dict)
#     else:
#         return True


# def underlying_generic_patch_all_http(pydantic_class_type: Type[dataclass], stored_pydantic_obj_list: List[DocumentModel],
#                                       pydantic_obj_update_json_list: List[Dict],
#                                       ignore_datetime_handling: bool | None = None) -> List[Tuple[DocumentModel, Dict]]:
#     stored_obj_id_to_obj_dict = get_stored_obj_id_to_obj_dict(stored_pydantic_obj_list)
#
#     stored_pydantic_obj_json_list: List[Dict] = []
#     stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = []
#     for index, pydantic_obj_update_json in enumerate(pydantic_obj_update_json_list):
#         assign_missing_ids_n_handle_date_time_type(pydantic_class_type, pydantic_obj_update_json,
#                                                    ignore_handling_datetime=ignore_datetime_handling)
#
#         # converting stored objs to json
#         stored_pydantic_obj_json = jsonable_encoder(stored_obj_id_to_obj_dict[pydantic_obj_update_json.get("_id")],
#                                                     by_alias=True)
#         stored_pydantic_obj_json_list.append(stored_pydantic_obj_json)
#
#         # this list since contains container types (list of stored_pydantic_obj_json),
#         # gets updated in compare_n_patch_list called below
#         stored_pydantic_obj_n_updated_obj_dict_tuple_list.append((stored_obj_id_to_obj_dict[
#                                                                       stored_pydantic_obj_json.get("_id")],
#                                                                   stored_pydantic_obj_json))
#     compare_n_patch_list(stored_pydantic_obj_json_list, pydantic_obj_update_json_list)
#
#     return stored_pydantic_obj_n_updated_obj_dict_tuple_list


# @http_except_n_log_error(status_code=500)
# @generic_perf_benchmark
# async def generic_patch_all_without_db_update_http(
#         dataclass_class_type: Type[dataclass], stored_pydantic_obj_list: List[dataclass],
#         json_n_data_class_handler: JsonNDataClassHandler,
#         return_obj_copy: bool | None = True) -> List[Dict[str, Any]] | bool:
#     if json_n_data_class_handler.dataclass_obj_list is None:
#         obj_json_list = json_n_data_class_handler.json_dict_list
#     else:
#         obj_json_list = jsonable_encoder(json_n_data_class_handler.dataclass_obj_list, exclude_none=True)
#         json_n_data_class_handler.set_json_dict_list(obj_json_list)  # updated json obj
#
#     # for obj_json in obj_json_list:
#     #     assign_missing_ids_n_handle_date_time_type(dataclass_class_type, obj_json)
#
#     # stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = \
#     #     underlying_generic_patch_all_http(dataclass_class_type, stored_pydantic_obj_list, pydantic_obj_update_json_list)
#     if return_obj_copy:
#         # updated_obj_list: List[DocumentModel] = []
#         # for stored_pydantic_obj_, updated_pydantic_obj_dict in stored_pydantic_obj_n_updated_obj_dict_tuple_list:
#         #     updated_obj_list.append(dataclass_class_type(**updated_pydantic_obj_dict))
#         return obj_json_list
#     else:
#         return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_all_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                                 json_n_data_class_handler: JsonNDataClassHandler, updated_obj_id_list: List[Any],
                                 filter_agg_pipeline: Any = None,
                                 update_agg_pipeline: Any = None, has_links: bool = False,
                                 return_obj_copy: bool | None = True) -> List[Dict[str, Any]] | bool:
    if json_n_data_class_handler.dataclass_obj_list is None:
        obj_json_list = json_n_data_class_handler.json_dict_list
    else:
        # obj_json_list = jsonable_encoder(json_n_data_class_handler.dataclass_obj_list, exclude_none=True)
        # obj_json_list_str = orjson.dumps([obj.__dict__ for obj in json_n_data_class_handler.dataclass_obj_list], default=str)
        # obj_json_list = orjson.loads(obj_json_list_str)
        obj_json_list = [obj.__dict__ for obj in json_n_data_class_handler.dataclass_obj_list]
        json_n_data_class_handler.set_json_dict_list(obj_json_list)  # updated json obj

    # for obj_json in obj_json_list:
    #     assign_missing_ids_n_handle_date_time_type(dataclass_class_type, obj_json)
    stored_pydantic_obj_json_list = json_n_data_class_handler.stored_json_dict_list
    compare_n_patch_list(stored_pydantic_obj_json_list, obj_json_list)
    # stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = \
    #     underlying_generic_patch_all_http(pydantic_class_type, stored_pydantic_obj_list, pydantic_obj_update_json_list)
    return await _underlying_patch_n_put_all(dataclass_class_type, proto_package_name,
                                             stored_pydantic_obj_json_list,
                                             updated_obj_id_list, filter_agg_pipeline, update_agg_pipeline,
                                             has_links, return_obj_copy)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                              pydantic_dummy_model, db_obj_id: int | str | Any,
                              update_agg_pipeline: Any = None, has_links: bool = False,
                              return_obj_copy: bool | None = True) -> DefaultDataclassWebResponse | bool:
    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj

    id_is_int_type = isinstance(db_obj_id, int)
    deleted_obj_json: Dict[str, Any] = await collection_obj.find_one_and_delete({"_id": db_obj_id})
    await execute_update_agg_pipeline(dataclass_class_type, proto_package_name, update_agg_pipeline)
    await publish_ws(dataclass_class_type, db_obj_id, has_links=has_links, update_ws_with_id=True,
                     dummy_dataclass_model=pydantic_dummy_model)

    # Setting back incremental id to 0 if collection gets empty
    if id_is_int_type:
        pydantic_objs_count = await collection_obj.count_documents({})
        if pydantic_objs_count == 0:
            max_id_val = 0
            max_update_id_vale = 0
            dataclass_class_type.init_max_id(max_id_val, max_update_id_vale)
        # else not required: all good
    # else not required: if id is not int then it must be of PydanticObjectId so no handling required

    if return_obj_copy:
        del_success.id = db_obj_id
        return del_success
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_all_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                                  dataclass_dummy_model: Type[dataclass], return_obj_copy: bool | None = True
                                  ) -> DefaultDataclassWebResponse | bool:
    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj

    id_is_int_type = (dataclass_class_type.__annotations__.get("_id") == int)

    motor_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find({}, {"_id": 1})
    stored_id_dict_list = await motor_cursor.to_list(None)

    # preparing success message
    del_success.id = []
    for stored_id_dict in stored_id_dict_list:
        del_success.id.append(stored_id_dict.get("_id"))

    # deleting all
    delete_result: pymongo.results.DeleteResult = await collection_obj.delete_many({})

    # Setting back incremental id to 0 if collection gets empty
    if id_is_int_type:
        pydantic_objs_count = await collection_obj.count_documents({})
        if pydantic_objs_count == 0:
            max_id_val = 0
            max_update_id_vale = 0
            dataclass_class_type.init_max_id(max_id_val, max_update_id_vale)
        # else not required: all good
    # else not required: if id is not int then it must be of PydanticObjectId so no handling required

    await publish_ws_all(dataclass_class_type, del_success.id, update_ws_with_id=True,
                         dummy_dataclass_model=dataclass_dummy_model)
    if return_obj_copy:
        return del_success
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                            filter_agg_pipeline: Any = None, has_links: bool = False,
                            read_ids_list: List[Any] | None = None, projection_model=None):
    json_obj_list: List[dataclass_class_type]
    json_obj_list = \
        await get_obj_list(dataclass_class_type, read_ids_list,
                           filter_agg_pipeline=filter_agg_pipeline, has_links=has_links,
                           projection_model=projection_model)
    if read_ids_list and len(json_obj_list) != len(set(read_ids_list)):
        existing_ids = set()
        for json_obj in json_obj_list:
            _id = json_obj.get("_id")
            if _id in read_ids_list:
                existing_ids.add(_id)
        non_existing_ids = set(read_ids_list) - existing_ids
        # Attention: Below err_str is being used by log_analyzer inn regex pattern match,
        # avoid changing it or fix its use-case
        err_str: Final[str] = (f"Couldn't find {dataclass_class_type.__name__} objects with ids: {non_existing_ids} "
                               f"out of requested {read_ids_list}")
        logging.error(err_str)
        raise HTTPException(detail=err_str, status_code=500)
    return json_obj_list


async def _generic_read_ws(dataclass_class_type: Type[dataclass], ws: WebSocket,
                           filter_agg_pipeline, need_initial_snapshot: bool,
                           is_new_ws: bool, has_links: bool):
    need_disconnect = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            json_obj_list = \
                await get_obj_list(dataclass_class_type, filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
            json_obj_list_str = json.dumps(json_obj_list, default=str)
            await dataclass_class_type.read_ws_path_ws_connection_manager. \
                send_json_to_websocket(json_obj_list_str, ws)
        # else not required: no initial snapshot is provided on this connection

        need_disconnect = await handle_ws(ws, is_new_ws)  # Blocking call
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException in ws: {ws.client}: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully "
                     f"within while loop in ws {ws.client}: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: web socket connection closed with error "
                     f"within while loop in ws {ws.client}: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_dataclass_get_ws - connection closed by client in ws {ws.client}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"v - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_e:
        need_disconnect = True
        logging.exception(f"generic_dataclass_get_ws - unexpected connection close in ws {ws.client}: {http_e}")
        raise HTTPException(status_code=404, detail=str(http_e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_dataclass_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await dataclass_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: {ws.client}")


@http_except_n_log_error(status_code=500)
async def generic_read_ws(ws: WebSocket, project_name: str, dataclass_class_type: Type[dataclass],
                          filter_agg_pipeline: Any = None, has_links: bool = False, need_initial_snapshot: bool = True):
    is_new_ws: bool = await dataclass_class_type.read_ws_path_ws_connection_manager.connect(ws)
    logging.debug(f"websocket client requested to connect: {ws.client}")

    await _generic_read_ws(dataclass_class_type, ws, filter_agg_pipeline, need_initial_snapshot, is_new_ws, has_links)


@http_except_n_log_error(status_code=500)
async def generic_query_ws(ws: WebSocket, project_name: str, dataclass_class_type: Type[dataclass],
                           ws_filter_callable: Callable[..., Any] | None = None,
                           ws_filter_callable_kwargs: Dict[Any, Any] | None = None,
                           filter_agg_pipeline: Any = None, has_links: bool = False,
                           need_initial_snapshot: bool = True):
    is_new_ws: bool = await dataclass_class_type.read_ws_path_ws_connection_manager.connect(ws, ws_filter_callable,
                                                                                            ws_filter_callable_kwargs)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    await _generic_read_ws(dataclass_class_type, ws, filter_agg_pipeline, need_initial_snapshot, is_new_ws, has_links)


@http_except_n_log_error(status_code=500)
async def generic_projection_query_ws(ws: WebSocket, project_name: str, dataclass_class_type: Type[dataclass],
                                      filter_callable: Callable[..., Any] | None = None,
                                      filter_callable_kwargs: Dict[Any, Any] | None = None,
                                      projection_agg_pipeline_callable: Callable[..., Any] | None = None,
                                      projection_model: Type[dataclass] | None = None,
                                      need_initial_snapshot: bool = True):
    if filter_callable_kwargs is None:
        filter_callable_kwargs = {}

    is_new_ws: bool = \
        await dataclass_class_type.read_ws_path_ws_connection_manager.connect(ws, filter_callable,
                                                                              filter_callable_kwargs,
                                                                              projection_agg_pipeline_callable,
                                                                              projection_model)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    need_disconnect = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            projection_agg_pipeline = None
            if projection_agg_pipeline_callable:
                projection_agg_pipeline = projection_agg_pipeline_callable(**filter_callable_kwargs)

            json_obj_list = await get_obj_list(dataclass_class_type,
                                               filter_agg_pipeline=projection_agg_pipeline,
                                               projection_model=projection_model)
            json_str = json.dumps(json_obj_list, default=str)
            await dataclass_class_type.read_ws_path_ws_connection_manager. \
                send_json_to_websocket(json_str, ws)
        # else not required: no initial snapshot is provided on this connection
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException in ws {ws.client}: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully "
                     f"within while loop in ws {ws.client}: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: web socket connection closed with error "
                     f"within while loop in ws {ws.client}: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client in ws {ws.client}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {http_e}")
        raise HTTPException(status_code=404, detail=str(http_e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await dataclass_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: {ws.client}")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_by_id_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                                  db_obj_id: Any, filter_agg_pipeline: Any = None, has_links: bool = False):
    fetched_json_obj: Dict = await get_obj(dataclass_class_type, db_obj_id,
                                           filter_agg_pipeline, has_links)
    if not fetched_json_obj:
        raise HTTPException(status_code=404,
                            detail=id_not_found.format_msg(dataclass_class_type.__name__, db_obj_id))
    else:
        return fetched_json_obj


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_ws(ws: WebSocket, project_name: str, dataclass_class_type: Type[dataclass],
                                db_obj_id: Any, filter_agg_pipeline: Any = None, has_links: bool = False,
                                need_initial_snapshot: bool | None = True):
    # prevent duplicate addition
    is_new_ws: bool = await dataclass_class_type.read_ws_path_with_id_ws_connection_manager.connect(ws, db_obj_id)

    logging.debug(f"websocket client requested to connect: {ws.client}")
    need_disconnect: bool = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            fetched_json_obj: Dict = await get_obj(dataclass_class_type, db_obj_id,
                                                   filter_agg_pipeline, has_links)
            if fetched_json_obj is None:
                raise HTTPException(status_code=404, detail=id_not_found.format_msg(dataclass_class_type.__name__,
                                                                                    db_obj_id))
            else:
                fetched_obj_json_str = json.dumps(fetched_json_obj, default=str)
                await dataclass_class_type.read_ws_path_with_id_ws_connection_manager.send_json_to_websocket(
                    fetched_obj_json_str, ws)
        # else not required: no initial snapshot is provided on this connection
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException in ws {ws.client}: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully "
                     f"within while loop in ws {ws.client}: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: web socket connection closed with error "
                     f"within while loop in ws url {ws.client}: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client in ws {ws.client}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}:"
                          f" {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {http_e}")
        raise HTTPException(status_code=404, detail=str(http_e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}:"
                          f" {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await dataclass_class_type.read_ws_path_with_id_ws_connection_manager.disconnect(ws, db_obj_id)
            logging.debug(f"Disconnected to websocket: {ws.client}")


async def get_obj(dataclass_class_type: Type[dataclass], db_obj_id: Any,
                  filter_agg_pipeline: Any = None, has_links: bool = False,
                  projection_model: Type[dataclass] | None = None):
    if filter_agg_pipeline is None:
        collection_cursor: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj
        fetched_json_obj = await collection_cursor.find_one({"_id": db_obj_id})
    else:
        fetched_json_obj = await get_filtered_obj(filter_agg_pipeline, dataclass_class_type,
                                                  db_obj_id, has_links, projection_model)
    return fetched_json_obj


async def get_obj_list(dataclass_class_type: Type[dataclass], find_ids: List[Any] | None = None,
                       filter_agg_pipeline: Any = None, has_links: bool = False,
                       projection_model: Type[dataclass] | None = None) -> List[Dict[str, Any]]:
    if filter_agg_pipeline is None:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj
        if find_ids is None:
            fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find()
        else:
            fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find({"_id": {'$in': find_ids}})
        fetched_json_list = await fetched_objs_cursor.to_list(None)
        return fetched_json_list
    else:
        # find_ids if none: will be handled inside get_filtered_obj_list implicitly
        json_list = await get_filtered_obj_list(filter_agg_pipeline, dataclass_class_type, find_ids,
                                                has_links=has_links, projection_model=projection_model)
        return json_list


# {'aggregate': }
@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def projection_read_http(dataclass_class_type: Type[dataclass], proto_package_name: str,
                               filter_agg_pipeline: Any, has_links: bool = False, projection_model = None):
    if not projection_model:
        logging.error(f"projection_read_http called for: {dataclass_class_type=} with no projection_model;;;"
                      f"{filter_agg_pipeline=}")
        return None
    # prevent polluting caller provided filter_agg_pipeline
    filter_agg_pipeline_copy = deepcopy(filter_agg_pipeline)
    agg_pipeline = get_aggregate_pipeline(filter_agg_pipeline_copy)
    if projection_model is None:
        projection_model = dataclass_class_type
    else:
        agg_pipeline = filter_agg_pipeline["aggregate"]
    try:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj
        fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = collection_obj.aggregate(agg_pipeline)
        fetched_json_list = await fetched_objs_cursor.to_list(None)
        return fetched_json_list

    except Exception as e:
        logging.error(f"projection failed with exception: {e}")
        return None


async def get_filtered_obj_list(filter_agg_pipeline: Dict, dataclass_class_type: Type[dataclass],
                                db_obj_id_list: List | None = None,
                                has_links: bool = False, projection_model: Type[dataclass] | None = None):
    # prevent polluting caller provided filter_agg_pipeline
    filter_agg_pipeline_copy = deepcopy(filter_agg_pipeline)
    if db_obj_id_list is not None:
        pydantic_obj_id_field: str = "_id"
        if (match := filter_agg_pipeline_copy.get("match")) is not None:
            match.append((pydantic_obj_id_field, db_obj_id_list))
        else:
            filter_agg_pipeline_copy["match"] = [(pydantic_obj_id_field, db_obj_id_list)]
    agg_pipeline = get_aggregate_pipeline(filter_agg_pipeline_copy)
    if projection_model is None:
        projection_model = dataclass_class_type
    else:
        agg_pipeline = filter_agg_pipeline["aggregate"]

    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = dataclass_class_type.collection_obj

    fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = collection_obj.aggregate(agg_pipeline)
    fetched_json_list = await fetched_objs_cursor.to_list(None)
    return fetched_json_list


async def get_filtered_obj(filter_agg_pipeline: Dict, dataclass_class_type: Type[dataclass],
                           pydantic_obj_id: Any, has_links: bool = False,
                           projection_model: Type[dataclass] | None = None) -> Dict[str, Any] | None:
    json_obj_list = await get_filtered_obj_list(filter_agg_pipeline, dataclass_class_type,
                                                [pydantic_obj_id], has_links, projection_model)
    if json_obj_list:
        return json_obj_list[0]
    else:
        return None


async def get_max_val(model_class_type: Type[dataclass]):
    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = model_class_type.collection_obj
    latest_obj = await collection_obj.find_one(sort=[("_id", -1)])
    if latest_obj is not None:
        max_val = latest_obj.get("_id")
    else:
        max_val = 0
    return max_val


def generic_encoder(obj_to_encode: Any, exclude_none: bool = False, by_alias: bool = False) -> Any:
    return jsonable_encoder(obj_to_encode, exclude_none=exclude_none, by_alias=by_alias)
