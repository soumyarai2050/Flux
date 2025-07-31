# system imports
import json
import asyncio
from typing import List, Any, Dict, Final, Callable, Type, Tuple, TypeVar
import logging

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException
from copy import deepcopy
from pathlib import PurePath
import msgspec

# 3rd party packages
import motor.motor_asyncio
from pymongo import UpdateOne
import pymongo.results
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
import orjson
from pendulum import DateTime
import gridfs

# project specific imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultMsgspecWebResponse
from Flux.PyCodeGenEngine.FluxCodeGenCore.ws_connection_manager import WSData
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error
from FluxPythonUtils.scripts.general_utility_functions import (
    execute_tasks_list_with_all_completed, handle_ws, compare_n_patch_dict,
    compare_n_patch_list, non_jsonable_types_handler)
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_route_utils import get_aggregate_pipeline, generic_perf_benchmark
from FluxPythonUtils.scripts.model_base_utils import MsgspecBaseModel, remove_none_values
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import get_non_stored_ids

"""
1. FilterAggregate [only filters the returned value]
2. UpdateAggregate [ modifies data in DB based on aggregate query and returns updated data ]
3. Create : FilterAggregate for return param and UpdateAggregate for massaging data post insert
4. Read, ReadAll : FilterAggregate for return param
5. Delete : UpdateAggregate for massaging data post delete
"""

# Todo: Direct mongo handling for db doesn't support Links yet

MsgspecModel = TypeVar('MsgspecModel', bound=MsgspecBaseModel)
id_not_found: Final[DefaultMsgspecWebResponse] = DefaultMsgspecWebResponse(msg="Id not Found")
del_success: Final[DefaultMsgspecWebResponse] = DefaultMsgspecWebResponse(msg="Deletion Successful")
code_gen_projects_path = PurePath(__file__).parent.parent.parent / "CodeGenProjects"


def validate_ws_connection_managers_in_model_obj(model_class_type: Type[MsgspecModel]):
    if (not model_class_type.read_ws_path_ws_connection_manager) or \
            (not model_class_type.read_ws_path_with_id_ws_connection_manager):
        err: str = f"unexpected: publish_ws invoked on model_class_type with missing either " \
                   f"read_ws_path_ws_connection_manager or read_ws_path_with_id_ws_connection_manager: " \
                   f"model_class_type {model_class_type}"
        logging.exception(err)
        raise Exception(err)


async def broadcast_all_from_active_ws_data_set(active_ws_data_set: List[WSData],
                                                msgspec_class_type: Type[MsgspecModel],
                                                db_obj_id_list: List[Any], db_obj_dict_list: List[Dict[str, Any]],
                                                broadcast_callable: Callable,
                                                tasks_list: List[asyncio.Task],
                                                has_links: bool | None = None):
    for ws_data in active_ws_data_set:
        projection_agg_params = ws_data.filter_callable_kwargs
        projection_agg_pipeline_callable = ws_data.projection_agg_pipeline_callable

        if projection_agg_pipeline_callable is not None:
            projection_agg_params["id_list"] = db_obj_id_list
            filter_agg_pipeline = projection_agg_pipeline_callable(**projection_agg_params)

            db_obj_dict_list = await get_obj_list(msgspec_class_type, db_obj_id_list,
                                                  filter_agg_pipeline=filter_agg_pipeline,
                                                  has_links=has_links, is_projection_type=True)
            if not db_obj_dict_list:
                # if this projection filter has some filter param that filters out all available db objs, in that case
                # db_obj_dict_list will be empty so no ws update is required
                continue
            # else not required: all good if fetched projection applied object list - will publish this now

            for obj_json in db_obj_dict_list:
                # handling all datetime fields - converting to epoch int values before passing to ws network
                msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)
        # else not required: passing provided db_obj_dict_list if ws_data is not of projection type to avoid
        # multiple look-ups as fetched db_obj_dict_list will also be exact same unless some projection is required on it

        json_str = orjson.dumps(db_obj_dict_list, default=non_jsonable_types_handler).decode('utf-8')
        await broadcast_callable(json_str, db_obj_id_list, ws_data, tasks_list)


async def broadcast_from_active_ws_data_set(active_ws_data_set: List[WSData], msgspec_class_type: Type[MsgspecModel],
                                            db_obj_id: Any, db_obj_dict: Dict[str, Any],
                                            broadcast_callable: Callable,
                                            tasks_list: List[asyncio.Task],
                                            broadcast_with_id: bool | None = None,
                                            has_links: bool | None = None):
    for ws_data in active_ws_data_set:
        projection_agg_params = ws_data.filter_callable_kwargs
        projection_agg_pipeline_callable = ws_data.projection_agg_pipeline_callable

        if projection_agg_pipeline_callable is not None:
            projection_agg_params["id_list"] = [db_obj_id]
            filter_agg_pipeline = projection_agg_pipeline_callable(**projection_agg_params)

            db_obj_dict = await get_obj(msgspec_class_type, db_obj_id,
                                        filter_agg_pipeline=filter_agg_pipeline,
                                        has_links=has_links, is_projection_type=True)
            if db_obj_dict is None:
                # if this projection filter has some filter param that mismatches to this update, in that case
                # db_obj_dict will be None so no ws update is required
                continue
            # else not required: all good if fetched projection applied object - will publish this now

            # handling all datetime fields - converting to epoch int values before passing to ws network
            msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(db_obj_dict)

        # else not required: passing provided db_obj_dict if ws_data is not of projection type to avoid
        # multiple look-ups as fetched object will also be exact same unless some projection is required on it

        json_str = orjson.dumps(db_obj_dict, default=non_jsonable_types_handler).decode("utf-8")
        await broadcast_callable(json_str, db_obj_id, ws_data, tasks_list)


async def publish_ws(msgspec_class_type: Type[MsgspecModel], db_obj_id: Any, db_obj_dict: Dict[str, Any],
                     has_links: bool | None = None, update_ws_with_id: bool | None = None):
    """
    :param msgspec_class_type: Dataclass SubClass Type
    :param db_obj_id: db_obj_id for create/update/delete
    :param db_obj_dict: db_obj_dict for create/update/delete
    :param has_links: bool for has_links
    :param update_ws_with_id: [Optional] bool to update ws with id
    """
    validate_ws_connection_managers_in_model_obj(msgspec_class_type)
    tasks_list: List[asyncio.Task] = []
    active_ws_data_list: List[WSData] = msgspec_class_type.read_ws_path_ws_connection_manager.get_activ_ws_data_list()
    if active_ws_data_list:
        async with msgspec_class_type.read_ws_path_ws_connection_manager.rlock:
            await broadcast_from_active_ws_data_set(active_ws_data_list, msgspec_class_type, db_obj_id, db_obj_dict,
                                                    msgspec_class_type.read_ws_path_ws_connection_manager.broadcast,
                                                    tasks_list, has_links=has_links)
    if update_ws_with_id:
        active_ws_data_list_for_id: List[WSData] = \
            msgspec_class_type.read_ws_path_with_id_ws_connection_manager.get_activ_ws_tuple_list_with_id(
                db_obj_id)

        if active_ws_data_list_for_id:
            async with msgspec_class_type.read_ws_path_with_id_ws_connection_manager.rlock:
                await broadcast_from_active_ws_data_set(
                    active_ws_data_list_for_id, msgspec_class_type, db_obj_id, db_obj_dict,
                    msgspec_class_type.read_ws_path_with_id_ws_connection_manager.broadcast,
                    tasks_list, broadcast_with_id=True, has_links=has_links)
    if tasks_list:
        await execute_tasks_list_with_all_completed(tasks_list, msgspec_class_type)


async def publish_ws_all(msgspec_class_type: Type[MsgspecModel], db_obj_id_list: List[Any],
                         db_obj_dict_list: List[Dict[str, Any]],
                         has_links: bool | None = None, update_ws_with_id: bool | None = None):
    """
    :param msgspec_class_type: MsgspecModel SubClass Type
    :param db_obj_id_list: List of db_obj_ids for create/update/delete
    :param db_obj_dict_list: List of db_obj_dicts for create/update/delete
    :param has_links: bool for has_links
    :param update_ws_with_id: bool to update ws with id
    """
    validate_ws_connection_managers_in_model_obj(msgspec_class_type)
    tasks_list: List[asyncio.Task] = []

    active_ws_data_list: List[WSData] = msgspec_class_type.read_ws_path_ws_connection_manager.get_activ_ws_data_list()
    if active_ws_data_list:
        async with msgspec_class_type.read_ws_path_ws_connection_manager.rlock:
            await broadcast_all_from_active_ws_data_set(active_ws_data_list, msgspec_class_type,
                                                        db_obj_id_list, db_obj_dict_list,
                                                        msgspec_class_type.read_ws_path_ws_connection_manager.broadcast,
                                                        tasks_list, has_links)
    # TODO: this can be optimized by sending array of messages to ws instead of sending one message at a time per ws
    #       in most use-case the consumer of one id is interested in all ids.
    if update_ws_with_id:
        for db_obj_dict in db_obj_dict_list:
            db_obj_id = db_obj_dict.get("_id")
            active_ws_data_list_for_id: List[WSData] = \
                msgspec_class_type.read_ws_path_with_id_ws_connection_manager.get_activ_ws_tuple_list_with_id(
                    db_obj_id)

            if active_ws_data_list_for_id:
                async with msgspec_class_type.read_ws_path_with_id_ws_connection_manager.rlock:
                    await broadcast_from_active_ws_data_set(
                        active_ws_data_list_for_id, msgspec_class_type, db_obj_id, db_obj_dict,
                        msgspec_class_type.read_ws_path_with_id_ws_connection_manager.broadcast,
                        tasks_list, broadcast_with_id=True, has_links=has_links)
    if tasks_list:
        await execute_tasks_list_with_all_completed(tasks_list, msgspec_class_type)


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


async def execute_update_agg_pipeline(msgspec_class_type: Type[MsgspecModel],
                                      proto_package_name: str, update_agg_pipeline: Any = None):
    if update_agg_pipeline is not None:
        aggregated_dict_list: List[Dict]
        aggregated_dict_list = await generic_read_http(msgspec_class_type, proto_package_name,
                                                       filter_agg_pipeline=update_agg_pipeline)

        id_list = []
        update_req_list = []
        for aggregated_dict in aggregated_dict_list:
            db_id = aggregated_dict.get('_id')
            id_list.append(db_id)

            if not msgspec_class_type.is_time_series:
                update_req_list.append(UpdateOne({"_id": db_id}, {"$set": aggregated_dict}))
            # else not required: if model is time series then delete and new insert is done due to unsupported
            # updates in time-series (check below)

        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

        if aggregated_dict_list:
            if msgspec_class_type.is_time_series:
                await _update_time_series(collection_obj, id_list, aggregated_dict_list)
            else:
                await collection_obj.bulk_write(update_req_list)
        # else not required: avoiding db calls if collection is empty

        for obj_json in aggregated_dict_list:
            # handling all datetime fields - converting to epoch int values before passing to ws network
            msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)
        await publish_ws_all(msgspec_class_type, id_list, aggregated_dict_list, update_ws_with_id=True)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_http(msgspec_class_type: Type[MsgspecModel],
                            proto_package_name: str, create_obj: MsgspecModel,
                            filter_agg_pipeline: Any = None,
                            update_agg_pipeline: Any = None, has_links: bool = False) -> Dict[str, Any] | bool:
    obj_json = create_obj.to_dict()
    obj_id = create_obj.id
    if obj_id is not None:
        msgspec_class_type.init_max_id(obj_id, None)    # updates max_id to this id if is > than existing max_id

    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        await gridfs_bucket_obj.upload_from_stream_with_id(
            file_id=obj_id,
            filename=str(obj_id),
            source=create_obj.to_json_str(),
        )
    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj
        insert_one_result: pymongo.results.InsertOneResult = await collection_obj.insert_one(obj_json)

        await execute_update_agg_pipeline(msgspec_class_type, proto_package_name, update_agg_pipeline)

        if update_agg_pipeline or filter_agg_pipeline:
            obj_json = await get_obj(msgspec_class_type, insert_one_result.inserted_id, filter_agg_pipeline, has_links)

    # handling all datetime fields - converting to epoch int values - caller of this function will handle
    # these fields back if required
    msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)

    await publish_ws(msgspec_class_type, obj_id, obj_json, has_links)
    return obj_json


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_all_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                                create_obj_list: List[MsgspecModel],
                                filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                                has_links: bool = False) -> List[Dict[str, Any]] | bool:
    obj_id_list = []
    for create_obj in create_obj_list:
        obj_id = create_obj.id
        obj_id_list.append(obj_id)
        if obj_id is not None:
            msgspec_class_type.init_max_id(obj_id, None)  # updates max_id to this id if is > than existing max_id
    obj_json_list = msgspec.to_builtins(create_obj_list, builtin_types=[DateTime])
    if msgspec_class_type.enable_large_db_object:
        for create_obj in create_obj_list:
            gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
            await gridfs_bucket_obj.upload_from_stream_with_id(
                file_id=create_obj.id,
                filename=str(create_obj.id),
                source=create_obj.to_json_str(),
            )
    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj
        insert_many_result: pymongo.results.InsertManyResult = await collection_obj.insert_many(obj_json_list)

        await execute_update_agg_pipeline(msgspec_class_type, proto_package_name, update_agg_pipeline)

        if update_agg_pipeline or filter_agg_pipeline:
            obj_json_list = await get_obj_list(msgspec_class_type, obj_id_list, filter_agg_pipeline, has_links)

        for obj_json in obj_json_list:
            # handling all datetime fields - converting to epoch int values - caller of this function will handle
            # these fields back if required
            msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)
    await publish_ws_all(msgspec_class_type, obj_id_list, obj_json_list, has_links)
    return obj_json_list


# def _get_beanie_formatted_update_request_json(updated_model_obj_dict: Dict):
#     # creating new obj without id and _id key
#     request_obj = {'$set': updated_model_obj_dict.items()}
#     return request_obj


async def _underlying_patch_n_put(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                                  updated_json_obj_dict: Dict, filter_agg_pipeline: Any = None,
                                  update_agg_pipeline: Any = None, has_links: bool = False) -> Dict[str, Any] | bool:
    """
        Underlying interface for Single object Put & Patch
    """
    _id = updated_json_obj_dict.get("_id")

    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        # first deleting the existing object
        await gridfs_bucket_obj.delete(_id)

        # now creating updated object
        await gridfs_bucket_obj.upload_from_stream_with_id(
            file_id=_id,
            filename=str(_id),
            source=orjson.dumps(updated_json_obj_dict, default=non_jsonable_types_handler),
        )

    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

        if msgspec_class_type.is_time_series:
            await _update_time_series(collection_obj, [_id], [updated_json_obj_dict])

        else:
            update_one_result: pymongo.results.UpdateResult = \
                await collection_obj.update_one({"_id": _id}, {"$set": updated_json_obj_dict})
        await execute_update_agg_pipeline(msgspec_class_type, proto_package_name, update_agg_pipeline)

        if update_agg_pipeline or filter_agg_pipeline:
            updated_json_obj_dict = await get_obj(msgspec_class_type, _id, filter_agg_pipeline, has_links)

    # handling all datetime fields - converting to epoch int values - caller of this function will handle
    # these fields back if required
    msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(updated_json_obj_dict)

    await publish_ws(msgspec_class_type, _id, updated_json_obj_dict, has_links, update_ws_with_id=True)
    return updated_json_obj_dict


async def _underlying_patch_n_put_all(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                                      updated_json_obj_dict_list: List[Dict[str, Any]],
                                      updated_obj_id_list: List[Any] | None = None,
                                      filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                                      has_links: bool = False) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Underlying interface for Put-All & Patch-All
    """
    missing_ids: List[int] = []
    if msgspec_class_type.enable_large_db_object:
        for updated_json_obj_dict in updated_json_obj_dict_list:
            _id = updated_json_obj_dict.get("_id")
            gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
            # first deleting the existing object
            try:
                await gridfs_bucket_obj.delete(_id)
            except gridfs.errors.NoFile:
                missing_ids.append(_id)
                continue

            # now creating updated object
            await gridfs_bucket_obj.upload_from_stream_with_id(
                file_id=_id,
                filename=str(_id),
                source=orjson.dumps(updated_json_obj_dict, default=non_jsonable_types_handler),
            )
    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

        if msgspec_class_type.is_time_series:
            await _update_time_series(collection_obj, updated_obj_id_list, updated_json_obj_dict_list)
        else:
            update_req_list: List[UpdateOne] = []
            for updated_json_obj_dict in updated_json_obj_dict_list:
                _id = updated_json_obj_dict.get("_id")
                update_req_list.append(UpdateOne({"_id": _id}, {"$set": updated_json_obj_dict}))
            bulk_write_result: pymongo.results.BulkWriteResult = await collection_obj.bulk_write(update_req_list)

            if bulk_write_result.matched_count != len(updated_obj_id_list):
                # Run the aggregation pipeline
                agg_cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = (
                    collection_obj.aggregate(get_non_stored_ids(updated_obj_id_list)))
                agg_cursor_list = await agg_cursor.to_list(None)

                if len(agg_cursor_list) == 1:
                    updated_obj_id_list = agg_cursor_list[0].get("found_ids")
                    missing_ids.extend(agg_cursor_list[0].get("missing_ids"))
                else:
                    raise HTTPException(detail=f"Found unsupported output from get_stored_ids aggregation, "
                                               f"Can't find stored and missing ids in db for "
                                               f"{msgspec_class_type.__name__} ;;;"
                                               f"{agg_cursor_list=}, {updated_json_obj_dict_list=}", status_code=400)

        await execute_update_agg_pipeline(msgspec_class_type, proto_package_name, update_agg_pipeline)
        if update_agg_pipeline or filter_agg_pipeline:
            updated_json_obj_dict_list = await get_obj_list(msgspec_class_type, updated_obj_id_list, filter_agg_pipeline, has_links)

    for obj_json in updated_json_obj_dict_list:
        # handling all datetime fields - converting to epoch int values - caller of this function will handle
        # these fields back if required
        msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)
    await publish_ws_all(msgspec_class_type, updated_obj_id_list, updated_json_obj_dict_list,
                         has_links, update_ws_with_id=True)
    return updated_json_obj_dict_list, missing_ids


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_http(model_class_type: Type[MsgspecModel], proto_package_name: str,
                           update_msgspec_obj: MsgspecModel, filter_agg_pipeline: Any = None,
                           update_agg_pipeline: Any = None, has_links: bool = False) -> Dict[str, Any] | bool:

    # stored_update_id_val = stored_json_obj.get("updated_id")
    # new_updated_id_val = obj_json.get("updated_id")
    # if stored_update_id_val is not None and stored_update_id_val == new_updated_id_val:
        # this is for cases where fetched object is passed as update object with slight changes. In these cases,
        # update id since is set as last stored value will not be increased automatically

    update_json_dict = update_msgspec_obj.to_dict()
    updated_stored_json_obj = \
        await _underlying_patch_n_put(model_class_type, proto_package_name,
                                      update_json_dict, filter_agg_pipeline, update_agg_pipeline, has_links)
    return updated_stored_json_obj


# def get_stored_obj_id_to_obj_dict(stored_model_obj_list: List[MsgspecModel]) -> Dict[int, str]:
#     stored_obj_id_to_obj_dict: Dict[int, str] = {}
#     for stored_model_obj in stored_model_obj_list:
#         if stored_model_obj.id not in stored_obj_id_to_obj_dict:
#             stored_obj_id_to_obj_dict[stored_model_obj.id] = stored_model_obj
#     return stored_obj_id_to_obj_dict
#
#
# def _generic_put_all_http(stored_model_obj_list: List[DocumentModel],
#                           updated_model_obj_list: List[DocumentModel]) -> List[Tuple[DocumentModel, Dict]]:
#     stored_obj_id_to_obj_dict = get_stored_obj_id_to_obj_dict(stored_model_obj_list)
#
#     stored_model_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = []
#     for index in range(len(updated_model_obj_list)):
#         stored_model_obj_n_updated_obj_dict_tuple_list.append(
#             (stored_obj_id_to_obj_dict[updated_model_obj_list[index].id],
#              updated_model_obj_list[index].model_dump(by_alias=True)))
#     return stored_model_obj_n_updated_obj_dict_tuple_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_all_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                               update_obj_list: List[MsgspecModel], filter_agg_pipeline: Any = None,
                               update_agg_pipeline: Any = None,
                               has_links: bool = False) -> Tuple[List[Dict[str, Any]], List[int]]:
    updated_obj_id_list = [update_obj.id for update_obj in update_obj_list]
    obj_json_list = msgspec.to_builtins(update_obj_list, builtin_types=[DateTime])
    return await _underlying_patch_n_put_all(msgspec_class_type, proto_package_name,
                                             obj_json_list, updated_obj_id_list, filter_agg_pipeline,
                                             update_agg_pipeline, has_links)

#
# def _assign_missing_ids_n_handle_date_time_type(field_model_type: Type[Any],
#                                                 key: str,
#                                                 value: Any,
#                                                 model_obj_update_json: Dict,
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
#             # since JSON has no support to Datetime when receiving model_obj_update_json
#             # all datetime type fields would be of str type
#             if (not ignore_handling_datetime) and issubclass(field_model_type.__args__[0],
#                                                              datetime.datetime):
#                 if isinstance(value, str):
#                     # Setting values parsed as str back to Datetime type
#                     model_obj_update_json[key] = pendulum.parse(value)
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
#             # since JSON has no support to Datetime when receiving model_obj_update_json
#             # all datetime type fields would be of str type
#             if (not ignore_handling_datetime) and "DateTime" in field_model_type.__name__:
#                 if isinstance(value, str):
#                     # Setting values parsed as str back to Datetime type
#                     model_obj_update_json[key] = pendulum.parse(value)
#
#
# def assign_missing_ids_n_handle_date_time_type(model_class_type: Type[DocumentModel] | Type[modelModel],
#                                                model_obj_update_json: Dict,
#                                                ignore_root_id_check: bool | None = True,
#                                                ignore_handling_datetime: bool | None = False):
#     """
#     Handling for patch if any model in json has id field as mandatory field but is not set, sets the id field
#     with new id of same type
#     Reason: Since patch web client takes json as parameter instead of particular model instance that's why
#     id field is not autogenerated, and if there is some use-case that can't provide id (ex: Web UI), we have
#     to add id explicitly before saving in db
#     """
#     for key, value in model_obj_update_json.items():
#         if value is not None:
#             if ignore_root_id_check:
#                 if key == "_id":
#                     ignore_root_id_check = False
#                     continue
#             field_model: FieldInfo
#             if (field_model := model_class_type.model_fields.get(key)) is not None:
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
#                                         f"model_class_type: {model_class_type.__name__}")
#
#                     _assign_missing_ids_n_handle_date_time_type(type_other_than_none, key, value,
#                                                                 model_obj_update_json,
#                                                                 ignore_handling_datetime)
#                 else:
#                     _assign_missing_ids_n_handle_date_time_type(field_model_type, key, value, model_obj_update_json,
#                                                                 ignore_handling_datetime)
#

@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                             stored_obj_dict: Dict[str, Any], partial_update_dict: Dict[str, Any],
                             filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                             has_links: bool = False) -> Dict[str, Any] | bool:

    # since patch not call's default_factory of update_id
    partial_update_dict["update_id"] = msgspec_class_type.next_update_id()
    # assign_missing_ids_n_handle_date_time_type(msgspec_class_type, obj_json)

    try:
        updated_json_dict = compare_n_patch_dict(stored_obj_dict, partial_update_dict)
    except Exception as e:
        err_str = f"compare_n_patch_dict failed: exception: {e}"
        logging.exception(err_str)
        raise HTTPException(detail=err_str, status_code=400)

    updated_stored_json_obj = \
        await _underlying_patch_n_put(msgspec_class_type, proto_package_name,
                                      updated_json_dict, filter_agg_pipeline, update_agg_pipeline,
                                      has_links)
    return updated_stored_json_obj


# @http_except_n_log_error(status_code=500)
# @generic_perf_benchmark
# async def generic_patch_without_db_update_http(
#         model_class_type: Type[MsgspecModel],
#         stored_model_obj: MsgspecModel, json_n_data_class_handler: JsonNMsgspecHandler,
#         return_obj_copy: bool | None = True) -> Dict[str, Any] | bool:
#     if json_n_data_class_handler.dataclass_obj is None:
#         obj_json = json_n_data_class_handler.json_dict
#     else:
#         obj_json = jsonable_encoder(json_n_data_class_handler.dataclass_obj, exclude_none=True)
#         json_n_data_class_handler.set_json_dict(obj_json)  # updated json obj
#
#     # assign_missing_ids_n_handle_date_time_type(model_class_type, obj_json)
#     # try:
#     #     updated_model_obj_dict = compare_n_patch_dict(stored_model_obj.model_dump(by_alias=True),
#     #                                                      model_obj_update_json)
#     # except Exception as e:
#     #     err_str = f"compare_n_patch_dict failed: exception: {e}"
#     #     logging.exception(err_str)
#     #     raise HTTPException(detail=err_str, status_code=400)
#     if return_obj_copy:
#         return obj_json
#         # return model_class_type(**updated_model_obj_dict)
#     else:
#         return True


# def underlying_generic_patch_all_http(model_class_type: Type[MsgspecModel], stored_model_obj_list: List[DocumentModel],
#                                       model_obj_update_json_list: List[Dict],
#                                       ignore_datetime_handling: bool | None = None) -> List[Tuple[DocumentModel, Dict]]:
#     stored_obj_id_to_obj_dict = get_stored_obj_id_to_obj_dict(stored_model_obj_list)
#
#     stored_model_obj_json_list: List[Dict] = []
#     stored_model_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = []
#     for index, model_obj_update_json in enumerate(model_obj_update_json_list):
#         assign_missing_ids_n_handle_date_time_type(model_class_type, model_obj_update_json,
#                                                    ignore_handling_datetime=ignore_datetime_handling)
#
#         # converting stored objs to json
#         stored_model_obj_json = jsonable_encoder(stored_obj_id_to_obj_dict[model_obj_update_json.get("_id")],
#                                                     by_alias=True)
#         stored_model_obj_json_list.append(stored_model_obj_json)
#
#         # this list since contains container types (list of stored_model_obj_json),
#         # gets updated in compare_n_patch_list called below
#         stored_model_obj_n_updated_obj_dict_tuple_list.append((stored_obj_id_to_obj_dict[
#                                                                       stored_model_obj_json.get("_id")],
#                                                                   stored_model_obj_json))
#     compare_n_patch_list(stored_model_obj_json_list, model_obj_update_json_list)
#
#     return stored_model_obj_n_updated_obj_dict_tuple_list


# @http_except_n_log_error(status_code=500)
# @generic_perf_benchmark
# async def generic_patch_all_without_db_update_http(
#         msgspec_class_type: Type[MsgspecModel], stored_model_obj_list: List[MsgspecModel],
#         json_n_data_class_handler: JsonNMsgspecHandler,
#         return_obj_copy: bool | None = True) -> List[Dict[str, Any]] | bool:
#     if json_n_data_class_handler.dataclass_obj_list is None:
#         obj_json_list = json_n_data_class_handler.json_dict_list
#     else:
#         obj_json_list = jsonable_encoder(json_n_data_class_handler.dataclass_obj_list, exclude_none=True)
#         json_n_data_class_handler.set_json_dict_list(obj_json_list)  # updated json obj
#
#     # for obj_json in obj_json_list:
#     #     assign_missing_ids_n_handle_date_time_type(msgspec_class_type, obj_json)
#
#     # stored_model_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = \
#     #     underlying_generic_patch_all_http(msgspec_class_type, stored_model_obj_list, model_obj_update_json_list)
#     if return_obj_copy:
#         # updated_obj_list: List[DocumentModel] = []
#         # for stored_model_obj_, updated_model_obj_dict in stored_model_obj_n_updated_obj_dict_tuple_list:
#         #     updated_obj_list.append(msgspec_class_type(**updated_model_obj_dict))
#         return obj_json_list
#     else:
#         return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_all_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                                 stored_obj_dict_list: List[Dict[str, Any]],
                                 partial_update_dict_list: List[Dict[str, Any]],
                                 updated_obj_id_list: List[Any], filter_agg_pipeline: Any = None,
                                 update_agg_pipeline: Any = None, has_links: bool = False) -> List[Dict[str, Any]]:
    if (stored_len := len(stored_obj_dict_list)) != (update_len := len(partial_update_dict_list)):
        err_str = ("Unexpected: len of stored_obj_dict_list must be equal to len of partial_update_dict_list, "
                   f"len(stored_obj_dict_list)={stored_len}, len(partial_update_dict_list)={update_len};;; "
                   f"{stored_obj_dict_list=}, {partial_update_dict_list=}")
        logging.error(err_str)
        raise HTTPException(detail=err_str, status_code=400)

    compare_n_patch_list(stored_obj_dict_list, partial_update_dict_list)
    update_obj_dict_list, _ = await _underlying_patch_n_put_all(msgspec_class_type, proto_package_name,
                                                                stored_obj_dict_list, updated_obj_id_list,
                                                                filter_agg_pipeline, update_agg_pipeline, has_links)
    return update_obj_dict_list


async def handle_reset_int_id(collection_obj: motor.motor_asyncio.AsyncIOMotorCollection,
                              msgspec_class_type: Type[MsgspecModel]):
    model_objs_count = await collection_obj.count_documents({})
    if model_objs_count == 0:
        max_id_val = 0
        max_update_id_vale = 0
        msgspec_class_type.init_max_id(max_id_val, max_update_id_vale, force_set=True)
    # else not required: all good


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                              model_dummy_model, db_obj_id: int | str | Any,
                              update_agg_pipeline: Any = None, has_links: bool = False) -> DefaultMsgspecWebResponse | bool:
    id_is_int_type = isinstance(db_obj_id, int)
    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        try:
            await gridfs_bucket_obj.delete(db_obj_id)
        except gridfs.errors.NoFile:
            err_str = f"Unexpected: Obj with {db_obj_id=} doesn't exist - Can't be deleted"
            logging.error(err_str)
            raise HTTPException(status_code=404, detail=err_str)
    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj
        delete_res = await collection_obj.delete_one({"_id": db_obj_id})
        if delete_res.deleted_count == 1:
            await execute_update_agg_pipeline(msgspec_class_type, proto_package_name, update_agg_pipeline)

            empty_obj_dict = {'_id': db_obj_id}
            await publish_ws(msgspec_class_type, db_obj_id, empty_obj_dict, has_links=has_links, update_ws_with_id=True)

            # Setting back incremental id to 0 if collection gets empty
            if id_is_int_type:
                await handle_reset_int_id(collection_obj, msgspec_class_type)
            # else not required: if id is not int then it must be of modelObjectId so no handling required
            del_success.id = db_obj_id
            return del_success
        else:
            # delete_res.deleted_count for delete_one will always be either 1 or 0 - The delete_one method is
            # implemented to stop after deleting a single matching document, so it will never delete more than
            # one document, even if multiple documents match the query filter.
            err_str = f"Unexpected: Obj with {db_obj_id=} doesn't exist - Can't be deleted"
            logging.error(err_str)
            raise HTTPException(status_code=404, detail=err_str)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_all_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                                  msgspec_dummy_model: Type[MsgspecModel]) -> DefaultMsgspecWebResponse | bool:
    id_is_int_type = (msgspec_class_type.__annotations__.get("_id") == int)

    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.gridfs_files_collection_obj

        data_cursor = gridfs_bucket_obj.find()

        del_success.id = []
        empty_obj_dict_list: List[Dict[str, Any]] = []
        async for grid_out in data_cursor:
            # Read the file's content
            data_bytes = await grid_out.read()

            data_json = orjson.loads(data_bytes)
            _id = data_json.get("_id")
            del_success.id.append(_id)
            empty_obj_dict_list.append({'_id': _id})

            try:
                await gridfs_bucket_obj.delete(_id)
            except gridfs.errors.NoFile:
                err_str = f"Unexpected: Obj with {_id=} doesn't exist - Can't be deleted"
                logging.error(err_str)
                raise HTTPException(status_code=404, detail=err_str)
    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

        motor_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find({}, {"_id": 1})
        stored_id_dict_list = await motor_cursor.to_list(None)

        # deleting all
        delete_result: pymongo.results.DeleteResult = await collection_obj.delete_many({})

        # preparing success message
        del_success.id = []
        empty_obj_dict_list: List[Dict[str, Any]] = []
        for stored_id_dict in stored_id_dict_list:
            _id = stored_id_dict.get("_id")
            del_success.id.append(_id)
            empty_obj_dict_list.append({'_id': _id})

    # Setting back incremental id to 0 if collection gets empty
    if id_is_int_type:
        await handle_reset_int_id(collection_obj, msgspec_class_type)
    # else not required: if id is not int then it must be of ObjectId so no handling required

    await publish_ws_all(msgspec_class_type, del_success.id, empty_obj_dict_list, update_ws_with_id=True)
    return del_success


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_by_id_list_http(
        msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
        model_dummy_model, db_obj_id_list: List[int | str | Any], update_agg_pipeline: Any = None,
        has_links: bool = False) -> DefaultMsgspecWebResponse | bool:
    id_is_int_type = isinstance(db_obj_id_list[0], int)  # checking only first obj type assuming all will have same
    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.gridfs_files_collection_obj

        del_success.id = []
        empty_obj_dict_list: List[Dict[str, Any]] = []
        non_existing_ids: List[int] = []
        for _id in db_obj_id_list:
            try:
                await gridfs_bucket_obj.delete(_id)
            except gridfs.errors.NoFile:
                # obj with ids doesn't exist
                non_existing_ids.append(_id)
            else:
                del_success.id.append(_id)
                empty_obj_dict_list.append({'_id': _id})

        if non_existing_ids:
            # setting only existing id list to db_obj_id_list variable to handle only those further
            db_obj_id_list = del_success.id
            logging.error(f"Exception: Can't find ids {non_existing_ids} in db, only deleted existing ids "
                          f"{del_success.id} out of requested id list")
    else:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

        # fetching document objs based using requested id list to verify if all ids exist
        motor_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find({'_id': {'$in': db_obj_id_list}})
        documents_to_delete = await motor_cursor.to_list(None)
        delete_res = await collection_obj.delete_many({'_id': {'$in': db_obj_id_list}})

        if delete_res.deleted_count:
            if delete_res.deleted_count != len(db_obj_id_list):
                deleted_ids: List[int | str | Any] = []
                empty_obj_dict_list: List[Dict[str, Any]] = []
                for doc in documents_to_delete:
                    _id = doc.get('_id')
                    deleted_ids.append(_id)
                    empty_obj_dict_list.append({'_id': _id})

                deleted_ids = [doc['_id'] for doc in documents_to_delete]
                non_existing_ids = list(set(db_obj_id_list) - set(deleted_ids))

                logging.error(f"Exception: Can't find ids {non_existing_ids} in db, only deleted existing ids "
                              f"{deleted_ids} out of requested id list")
                # setting only existing id list to db_obj_id_list variable to handle only those further
                db_obj_id_list = deleted_ids
            else:
                empty_obj_dict_list: List[Dict[str, Any]] = [{"_id": _id} for _id in db_obj_id_list]

            await execute_update_agg_pipeline(msgspec_class_type, proto_package_name, update_agg_pipeline)
        else:
            err_str = f"Unexpected: No obj found with ids in provided list {db_obj_id_list=}, No obj deleted"
            logging.error(err_str)
            raise HTTPException(status_code=404, detail=err_str)

    await publish_ws_all(msgspec_class_type, db_obj_id_list, empty_obj_dict_list,
                         has_links=has_links, update_ws_with_id=True)
    # Setting back incremental id to 0 if collection gets empty
    if id_is_int_type:
        await handle_reset_int_id(collection_obj, msgspec_class_type)
    # else not required: if id is not int then it must be of modelObjectId so no handling required
    del_success.id = db_obj_id_list
    return del_success


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                            filter_agg_pipeline: Any = None, has_links: bool = False,
                            read_ids_list: List[Any] | None = None, projection_model=None):
    json_obj_list: List[msgspec_class_type]
    json_obj_list = \
        await get_obj_list(msgspec_class_type, read_ids_list,
                           filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
    if read_ids_list and len(json_obj_list) != len(set(read_ids_list)):
        existing_ids = set()
        for json_obj in json_obj_list:
            _id = json_obj.get("_id")
            if _id in read_ids_list:
                existing_ids.add(_id)
        non_existing_ids = set(read_ids_list) - existing_ids
        # Attention: Below err_str is being used by log_analyzer inn regex pattern match,
        # avoid changing it or fix its use-case
        err_str: Final[str] = (f"Couldn't find {msgspec_class_type.__name__} objects with ids: {non_existing_ids} "
                               f"out of requested {read_ids_list}")
        logging.error(err_str)
        raise HTTPException(detail=err_str, status_code=400)
    return json_obj_list


async def _generic_read_ws(msgspec_class_type: Type[MsgspecModel], ws: WebSocket,
                           filter_agg_pipeline, need_initial_snapshot: bool,
                           is_new_ws: bool, has_links: bool):
    need_disconnect = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            json_obj_list = \
                await get_obj_list(msgspec_class_type, filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
            for obj_json in json_obj_list:
                # handling all datetime fields - converting to epoch int values - caller of this function will handle
                # these fields back if required
                msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)
            json_obj_list_str = json.dumps(json_obj_list, default=non_jsonable_types_handler)
            await msgspec_class_type.read_ws_path_ws_connection_manager. \
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
            await msgspec_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: {ws.client}")


@http_except_n_log_error(status_code=500)
async def generic_read_ws(ws: WebSocket, project_name: str, msgspec_class_type: Type[MsgspecModel],
                          filter_agg_pipeline: Any = None, has_links: bool = False, need_initial_snapshot: bool = True):
    is_new_ws: bool = await msgspec_class_type.read_ws_path_ws_connection_manager.connect(ws)
    logging.debug(f"websocket client requested to connect: {ws.client}")

    await _generic_read_ws(msgspec_class_type, ws, filter_agg_pipeline, need_initial_snapshot, is_new_ws, has_links)


@http_except_n_log_error(status_code=500)
async def generic_query_ws(ws: WebSocket, project_name: str, msgspec_class_type: Type[MsgspecModel],
                           ws_filter_callable: Callable[..., Any] | None = None,
                           ws_filter_callable_kwargs: Dict[Any, Any] | None = None,
                           filter_agg_pipeline: Any = None, has_links: bool = False,
                           need_initial_snapshot: bool = True):
    is_new_ws: bool = await msgspec_class_type.read_ws_path_ws_connection_manager.connect(ws, ws_filter_callable,
                                                                                            ws_filter_callable_kwargs)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    await _generic_read_ws(msgspec_class_type, ws, filter_agg_pipeline, need_initial_snapshot, is_new_ws, has_links)


@http_except_n_log_error(status_code=500)
async def generic_projection_query_ws(ws: WebSocket, project_name: str, msgspec_class_type: Type[MsgspecModel],
                                      filter_callable: Callable[..., Any] | None = None,
                                      filter_callable_kwargs: Dict[Any, Any] | None = None,
                                      projection_agg_pipeline_callable: Callable[..., Any] | None = None,
                                      need_initial_snapshot: bool = True):
    if filter_callable_kwargs is None:
        filter_callable_kwargs = {}

    is_new_ws: bool = \
        await msgspec_class_type.read_ws_path_ws_connection_manager.connect(ws, filter_callable,
                                                                            filter_callable_kwargs,
                                                                            projection_agg_pipeline_callable)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    need_disconnect = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            projection_agg_pipeline = None
            if projection_agg_pipeline_callable:
                projection_agg_pipeline = projection_agg_pipeline_callable(**filter_callable_kwargs)

            json_obj_list = await get_obj_list(msgspec_class_type,
                                               filter_agg_pipeline=projection_agg_pipeline)
            for obj_json in json_obj_list:
                # handling all datetime fields - converting to epoch int values - caller of this function will handle
                # these fields back if required
                msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(obj_json)
            json_str = json.dumps(json_obj_list, default=non_jsonable_types_handler)
            await msgspec_class_type.read_ws_path_ws_connection_manager. \
                send_json_to_websocket(json_str, ws)
        # else not required: no initial snapshot is provided on this connection
        need_disconnect = await handle_ws(ws, is_new_ws)
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
    except WebSocketException as e:
        need_disconnect = True
        logging.exception(f"WebSocketException in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.exception(f"RuntimeError: web socket raised runtime error within while loop in ws {ws.client}: {e}")
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
            await msgspec_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: {ws.client}")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_by_id_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                                  db_obj_id: Any, filter_agg_pipeline: Any = None, has_links: bool = False):
    fetched_json_obj: Dict = await get_obj(msgspec_class_type, db_obj_id,
                                           filter_agg_pipeline, has_links)
    if not fetched_json_obj:
        raise HTTPException(status_code=404,
                            detail=id_not_found.format_msg(msgspec_class_type.__name__, db_obj_id))
    else:
        return fetched_json_obj


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_ws(ws: WebSocket, project_name: str, msgspec_class_type: Type[MsgspecModel],
                                db_obj_id: Any, filter_agg_pipeline: Any = None, has_links: bool = False,
                                need_initial_snapshot: bool | None = True):
    # prevent duplicate addition
    is_new_ws: bool = await msgspec_class_type.read_ws_path_with_id_ws_connection_manager.connect(ws, db_obj_id)

    logging.debug(f"websocket client requested to connect: {ws.client}")
    need_disconnect: bool = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            fetched_json_obj: Dict = await get_obj(msgspec_class_type, db_obj_id,
                                                   filter_agg_pipeline, has_links)
            if fetched_json_obj is None:
                raise HTTPException(status_code=404, detail=id_not_found.format_msg(msgspec_class_type.__name__,
                                                                                    db_obj_id))
            else:
                # handling all datetime fields - converting to epoch int values - caller of this function will handle
                # these fields back if required
                msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(fetched_json_obj)
                fetched_obj_json_str = json.dumps(fetched_json_obj, default=non_jsonable_types_handler)
                await msgspec_class_type.read_ws_path_with_id_ws_connection_manager.send_json_to_websocket(
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
            await msgspec_class_type.read_ws_path_with_id_ws_connection_manager.disconnect(ws, db_obj_id)
            logging.debug(f"Disconnected to websocket: {ws.client}")


async def get_obj(msgspec_class_type: Type[MsgspecModel], db_obj_id: Any,
                  filter_agg_pipeline: Any = None, has_links: bool = False,
                  is_projection_type: bool | None = False):
    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        # Open a download stream using the custom _id
        download_stream = await gridfs_bucket_obj.open_download_stream(db_obj_id)
        file_data = await download_stream.read()
        fetched_json_obj = orjson.loads(file_data)

    else:
        if filter_agg_pipeline is None:
            collection_cursor: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj
            fetched_json_obj = await collection_cursor.find_one({"_id": db_obj_id})
        else:
            fetched_json_obj = await get_filtered_obj(filter_agg_pipeline, msgspec_class_type,
                                                      db_obj_id, has_links, is_projection_type=is_projection_type)
    return fetched_json_obj


async def get_obj_list(msgspec_class_type: Type[MsgspecModel], find_ids: List[Any] | None = None,
                       filter_agg_pipeline: Any = None, has_links: bool = False,
                       is_projection_type: bool | None = False) -> List[Dict[str, Any]]:
    if msgspec_class_type.enable_large_db_object:
        gridfs_bucket_obj: motor.motor_asyncio.AsyncIOMotorGridFSBucket = msgspec_class_type.gridfs_bucket_obj
        data_cursor = gridfs_bucket_obj.find()
        json_data_list = []
        async for grid_out in data_cursor:
            # Read the file's content
            data_bytes = grid_out.read()
            data_json = orjson.loads(data_bytes)
            if find_ids:
                if data_json.get("_id") in find_ids:
                    json_data_list.append(data_json)
                #else not required: avoiding passing any value that doesn't exist in find_ids if find_ids is passed
            else:
                json_data_list.append(data_json)
        return json_data_list
    else:
        if filter_agg_pipeline is None:
            collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj
            if find_ids is None:
                fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find()
            else:
                fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCursor = collection_obj.find({"_id": {'$in': find_ids}})
            fetched_json_list = await fetched_objs_cursor.to_list(None)
            return fetched_json_list
        else:
            # find_ids if none: will be handled inside get_filtered_obj_list implicitly
            json_list = await get_filtered_obj_list(filter_agg_pipeline, msgspec_class_type, find_ids,
                                                    has_links=has_links, is_projection_type=is_projection_type)
            return json_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def projection_read_http(msgspec_class_type: Type[MsgspecModel], proto_package_name: str,
                               filter_agg_pipeline: Any, has_links: bool = False, projection_model = None):
    if not projection_model:
        logging.error(f"projection_read_http called for: {msgspec_class_type=} with no projection_model;;;"
                      f"{filter_agg_pipeline=}")
        return None
    # prevent polluting caller provided filter_agg_pipeline
    filter_agg_pipeline_copy = deepcopy(filter_agg_pipeline)
    agg_pipeline = get_aggregate_pipeline(filter_agg_pipeline_copy)
    if projection_model is None:
        projection_model = msgspec_class_type
    else:
        agg_pipeline = filter_agg_pipeline["aggregate"]
    try:
        collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj
        fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = collection_obj.aggregate(agg_pipeline)
        agg_query_resp_list = await fetched_objs_cursor.to_list(None)
    except Exception as e:
        logging.error(f"projection failed with exception: {e}")
        return None
    else:
        projection_model_obj = None
        if agg_query_resp_list:
            projection_model_obj = projection_model.from_dict(agg_query_resp_list[0])
        else:
            logging.error(f"projection failed - no data returned")
        return projection_model_obj


async def get_filtered_obj_list(filter_agg_pipeline: Dict, msgspec_class_type: Type[MsgspecModel],
                                db_obj_id_list: List | None = None,
                                has_links: bool = False, is_projection_type: bool | None = False):
    # prevent polluting caller provided filter_agg_pipeline
    filter_agg_pipeline_copy = deepcopy(filter_agg_pipeline)
    if db_obj_id_list is not None:
        model_obj_id_field: str = "_id"
        if (match := filter_agg_pipeline_copy.get("match")) is not None:
            match.append((model_obj_id_field, db_obj_id_list))
        else:
            filter_agg_pipeline_copy["match"] = [(model_obj_id_field, db_obj_id_list)]
    if not is_projection_type:
        agg_pipeline = get_aggregate_pipeline(filter_agg_pipeline_copy)
    else:
        agg_pipeline = filter_agg_pipeline["aggregate"]

    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

    fetched_objs_cursor: motor.motor_asyncio.AsyncIOMotorCommandCursor = collection_obj.aggregate(agg_pipeline)
    fetched_json_list = await fetched_objs_cursor.to_list(None)
    return fetched_json_list


async def get_filtered_obj(filter_agg_pipeline: Dict, msgspec_class_type: Type[MsgspecModel],
                           model_obj_id: Any, has_links: bool = False,
                           is_projection_type: bool | None = False) -> Dict[str, Any] | None:
    json_obj_list = await get_filtered_obj_list(filter_agg_pipeline, msgspec_class_type,
                                                [model_obj_id], has_links, is_projection_type)
    if json_obj_list:
        return json_obj_list[0]
    else:
        return None


async def get_max_val(model_class_type: Type[MsgspecModel]):
    collection_obj: motor.motor_asyncio.AsyncIOMotorCollection = model_class_type.collection_obj
    latest_obj = await collection_obj.find_one(sort=[("_id", -1)])
    if latest_obj is not None:
        max_val = latest_obj.get("_id")
    else:
        max_val = 0
    return max_val


def generic_encoder(obj_to_encode: Any, enc_hook: Callable, exclude_none: bool = False, by_alias: bool = False) -> Any:
    # IMPO: using enc_hook to convert DateTime to str since generic_encoder is used in converting msg_obj to python
    # dict which needs to be passed to request's json parameter and DateTime is not json serializable
    updated_dict = msgspec.to_builtins(obj_to_encode, enc_hook=enc_hook)
    if exclude_none:
        updated_dict = remove_none_values(updated_dict)
    return updated_dict


async def watch_specific_collection_with_stream(msgspec_class_type: Type[MsgspecModel],
                                                filter_ws_updates_callable: Callable | None = None,
                                                filter_agg_pipeline_callable_for_create_obj: Callable | None = None,
                                                filter_agg_pipeline_callable_for_update_obj: Callable | None = None):
    """Watches a specific collection for changes."""

    collection_cursor: motor.motor_asyncio.AsyncIOMotorCollection = msgspec_class_type.collection_obj

    logging.info(f"[STREAM - {msgspec_class_type.__name__}] Starting to watch for changes...")
    try:
        async with collection_cursor.watch(full_document='updateLookup') as stream:
            async for change in stream:
                document_id = change['documentKey']['_id']
                if 'fullDocument' in change and change['fullDocument']:
                    updated_or_created_obj = change['fullDocument']
                    logging.debug(f"STREAM - Full document: {updated_or_created_obj}")
                    if filter_ws_updates_callable is not None:
                        if not filter_ws_updates_callable(updated_or_created_obj):
                            # if filter check fails for obj then avoiding ws update
                            continue
                        # else not required: if passes check allowing it for ws update
                    # else not required: if no filter_ws_updates_callable passed - no need for any handling
                    if change['operationType'] == 'insert' and filter_agg_pipeline_callable_for_create_obj is not None:
                        filter_agg_pipeline = filter_agg_pipeline_callable_for_create_obj(updated_or_created_obj)
                        fetched_obj: Dict | None = await get_obj(msgspec_class_type, document_id, filter_agg_pipeline)

                        # handling all datetime fields - converting to epoch int values - caller of this function will handle
                        # these fields back if required
                        msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(fetched_obj)
                        await publish_ws(msgspec_class_type, document_id, fetched_obj,
                                         update_ws_with_id=True)
                    elif change['operationType'] == 'update' and filter_agg_pipeline_callable_for_update_obj is not None:
                        filter_agg_pipeline = filter_agg_pipeline_callable_for_create_obj(updated_or_created_obj)
                        fetched_obj: Dict | None = await get_obj(msgspec_class_type, document_id, filter_agg_pipeline)

                        # handling all datetime fields - converting to epoch int values - caller of this function will handle
                        # these fields back if required
                        msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(fetched_obj)
                        await publish_ws(msgspec_class_type, document_id, fetched_obj,
                                         update_ws_with_id=True)
                    else:
                        # handling all datetime fields - converting to epoch int values - caller of this function will handle
                        # these fields back if required
                        msgspec_class_type.convert_ts_fields_from_datetime_to_epoch_int(updated_or_created_obj)
                        await publish_ws(msgspec_class_type, document_id, updated_or_created_obj, update_ws_with_id=True)
                elif change['operationType'] == 'delete':
                    logging.debug(f"STREAM - Document with _id '{document_id}' was deleted.")
                    empty_obj_dict = {'_id': document_id}
                    await publish_ws(msgspec_class_type, document_id, empty_obj_dict, update_ws_with_id=True)
                else:
                    logging.error(f"Mongo Stream Unhandled change detected: {change}")
    except Exception as e:
        logging.exception(f"[STREAM - {msgspec_class_type.__name__}] Error: {e}")
    finally:
        logging.info(f"[STREAM - {msgspec_class_type.__name__}] Stopped watching changes.")

