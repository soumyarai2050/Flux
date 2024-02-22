# system imports
import json
import os
import asyncio
import types
from typing import List, Any, Dict, Final, Callable, Type, Tuple, TypeVar
import typing
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException
from copy import deepcopy
import timeit
from pathlib import PurePath
import functools
import datetime
from types import UnionType

# other package imports
from pydantic import ValidationError, BaseModel
from beanie.odm.bulk import BulkWriter
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from beanie import WriteRules, DeleteRules, Document
from beanie.odm.documents import InsertManyResult, PydanticObjectId
from pydantic.fields import FieldInfo
import pendulum
from beanie.operators import In
from beanie.odm.operators.update.general import Set as BeanieSet

# project specific imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from Flux.PyCodeGenEngine.FluxCodeGenCore.ws_connection_manager import WSData
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, compare_n_patch_dict, \
    parse_to_int, YAMLConfigurationManager, compare_n_patch_list, execute_tasks_list_with_all_completed, \
    get_time_it_log_pattern, parse_to_float, handle_ws

"""
1. FilterAggregate [only filters the returned value]
2. UpdateAggregate [ modifies data in DB based on aggregate query and returns updated data ]
3. Create : FilterAggregate for return param and UpdateAggregate for massaging data post insert
4. Read, ReadAll : FilterAggregate for return param
5. Delete : UpdateAggregate for massaging data post delete
"""

id_not_found: Final[DefaultWebResponse] = DefaultWebResponse(msg="Id not Found")
del_success: Final[DefaultWebResponse] = DefaultWebResponse(msg="Deletion Successful")
code_gen_projects_path = PurePath(__file__).parent.parent.parent / "CodeGenProjects"
log_generic_timings = parse_to_int(log_generic_timings_env_var) \
    if ((log_generic_timings_env_var := os.getenv("LogGenericTiming")) is not None and
        len(log_generic_timings_env_var)) else None
PydanticModel = TypeVar('PydanticModel', bound=BaseModel)
DocumentModel = TypeVar('DocumentModel', bound=Document)


# Decorator Function
def generic_perf_benchmark(func_callable):
    @functools.wraps(func_callable)
    async def benchmarker(*args, **kwargs):
        call_date_time = pendulum.DateTime.utcnow()
        start_time = timeit.default_timer()
        pydantic_model_type = None
        if args and issubclass(args[0], BaseModel):
            pydantic_model_type = args[0]
        return_val = await func_callable(*args, **kwargs)
        end_time = timeit.default_timer()
        delta = parse_to_float(f"{(end_time - start_time):.6f}")

        if log_generic_timings is not None and log_generic_timings == 1:
            pattern_str = get_time_it_log_pattern(func_callable.__name__, call_date_time, delta)
            pattern_str += f" pydantic_model: {pydantic_model_type}"
            logging.timing(pattern_str)
        return return_val
    return benchmarker


def validate_ws_connection_managers_in_pydantic_obj(pydantic_class_type: Type[DocumentModel]):
    if (not pydantic_class_type.read_ws_path_ws_connection_manager) or \
            (not pydantic_class_type.read_ws_path_with_id_ws_connection_manager):
        err: str = f"unexpected: publish_ws invoked on pydantic_class_type with missing either " \
                   f"read_ws_path_ws_connection_manager or read_ws_path_with_id_ws_connection_manager: " \
                   f"pydantic_class_type {pydantic_class_type}"
        logging.exception(err)
        raise Exception(err)


async def broadcast_all_from_active_ws_data_set(active_ws_data_set: List[WSData], 
                                                pydantic_class_type: Type[DocumentModel],
                                                pydantic_obj_id_list: List[Any],
                                                broadcast_callable: Callable,
                                                tasks_list: List[asyncio.Task],
                                                dummy_pydantic_model: Type[PydanticModel] | None = None,
                                                filter_agg_pipeline: Dict | None = None,
                                                has_links: bool | None = None):
    for ws_data in active_ws_data_set:
        projection_model = ws_data.projection_model
        projection_agg_params = ws_data.filter_callable_kwargs
        projection_agg_pipeline_callable = ws_data.projection_agg_pipeline_callable

        if projection_agg_pipeline_callable is not None:
            projection_agg_params["id_list"] = pydantic_obj_id_list
            filter_agg_pipeline = projection_agg_pipeline_callable(**projection_agg_params)

        if dummy_pydantic_model is not None:
            # if call is for delete operation
            pydantic_obj_list: List = []
            for pydantic_obj_id in pydantic_obj_id_list:
                pydantic_obj_list.append(dummy_pydantic_model(id=pydantic_obj_id))
        else:
            # if call is for update/create operation
            pydantic_obj_list = await get_obj_list(pydantic_class_type, pydantic_obj_id_list,
                                                   filter_agg_pipeline=filter_agg_pipeline,
                                                   has_links=has_links, projection_model=projection_model)
        if pydantic_obj_list:
            json_data = jsonable_encoder(pydantic_obj_list, by_alias=True)
            json_str = json.dumps(json_data)
            await broadcast_callable(json_str, ws_data, tasks_list)
        # else not required: not going to broadcast if not a valid update for this ws


async def broadcast_from_active_ws_data_set(active_ws_data_set: List[WSData], pydantic_class_type: Type[DocumentModel],
                                            pydantic_obj_id: Any,
                                            broadcast_callable: Callable,
                                            tasks_list: List[asyncio.Task],
                                            broadcast_with_id: bool | None = None,
                                            dummy_pydantic_model: Type[PydanticModel] | None = None,
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
            pydantic_obj: dummy_pydantic_model = dummy_pydantic_model(id=pydantic_obj_id)
        else:
            # if call is for update/create operation
            pydantic_obj = await get_obj(pydantic_class_type, pydantic_obj_id,
                                         filter_agg_pipeline=filter_agg_pipeline,
                                         has_links=has_links, projection_model=projection_model)

        if pydantic_obj is not None:
            if projection_agg_pipeline_callable is not None:
                pydantic_obj = [pydantic_obj]

            json_data = jsonable_encoder(pydantic_obj, by_alias=True)
            json_str = json.dumps(json_data)
            if broadcast_with_id:
                await broadcast_callable(json_str, pydantic_obj_id, ws_data, tasks_list)
            else:
                await broadcast_callable(json_str, ws_data, tasks_list)
        # else not required: not going to broadcast if not a valid update for this ws


async def publish_ws(pydantic_class_type: Type[DocumentModel], pydantic_obj_id: Any, filter_agg_pipeline: Dict | None = None,
                     has_links: bool | None = None, update_ws_with_id: bool | None = None,
                     dummy_pydantic_model: Type[PydanticModel] | None = None):
    """
    :param pydantic_class_type: Document SubClass Type
    :param pydantic_obj_id: pydantic_obj_id for create/update/delete
    :param filter_agg_pipeline: filter aggregation pipeline
    :param has_links: bool for has_links
    :param update_ws_with_id: [Optional] bool to update ws with id
    :param dummy_pydantic_model: [Optional] dummy pydantic basemodel type for delete case
    """
    validate_ws_connection_managers_in_pydantic_obj(pydantic_class_type)
    tasks_list: List[asyncio.Task] = []
    active_ws_data_list: List[WSData] = pydantic_class_type.read_ws_path_ws_connection_manager.get_activ_ws_data_list()
    if active_ws_data_list:
        async with pydantic_class_type.read_ws_path_ws_connection_manager.rlock:
            await broadcast_from_active_ws_data_set(active_ws_data_list, pydantic_class_type, pydantic_obj_id,
                                                    pydantic_class_type.read_ws_path_ws_connection_manager.broadcast,
                                                    tasks_list, dummy_pydantic_model=dummy_pydantic_model,
                                                    filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
    if update_ws_with_id:
        active_ws_data_list_for_id: List[WSData] = \
            pydantic_class_type.read_ws_path_with_id_ws_connection_manager.get_activ_ws_tuple_list_with_id(
                pydantic_obj_id)

        if active_ws_data_list_for_id:
            async with pydantic_class_type.read_ws_path_with_id_ws_connection_manager.rlock:
                await broadcast_from_active_ws_data_set(
                    active_ws_data_list_for_id, pydantic_class_type, pydantic_obj_id,
                    pydantic_class_type.read_ws_path_with_id_ws_connection_manager.broadcast,
                    tasks_list, broadcast_with_id=True, dummy_pydantic_model=dummy_pydantic_model,
                    filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
    if tasks_list:
        await execute_tasks_list_with_all_completed(tasks_list, pydantic_class_type)


async def publish_ws_all(pydantic_class_type: Type[DocumentModel], pydantic_obj_id_list: List[Any],
                         filter_agg_pipeline: Dict | None = None, has_links: bool | None = None,
                         update_ws_with_id: bool | None = None, dummy_pydantic_model: Type[PydanticModel] | None = None):
    """
    :param pydantic_class_type: Document SubClass Type
    :param pydantic_obj_id_list: List of pydantic_obj_ids for create/update/delete
    :param filter_agg_pipeline: filter aggregation pipeline
    :param has_links: bool for has_links
    :param update_ws_with_id: bool to update ws with id
    :param dummy_pydantic_model: [Optional] dummy pydantic basemodel type for delete case
    """
    validate_ws_connection_managers_in_pydantic_obj(pydantic_class_type)
    tasks_list: List[asyncio.Task] = []

    active_ws_data_list: List[WSData] = pydantic_class_type.read_ws_path_ws_connection_manager.get_activ_ws_data_list()
    if active_ws_data_list:
        async with pydantic_class_type.read_ws_path_ws_connection_manager.rlock:
            await broadcast_all_from_active_ws_data_set(active_ws_data_list, pydantic_class_type,
                                                        pydantic_obj_id_list,
                                                        pydantic_class_type.read_ws_path_ws_connection_manager.broadcast,
                                                        tasks_list, dummy_pydantic_model, filter_agg_pipeline,
                                                        has_links)
    # TODO: this can be optimized by sending array of messages to ws instead of sending one message at a time per ws
    #       in most use-case the consumer of one id is interested in all ids.
    if update_ws_with_id:
        for pydantic_obj_id in pydantic_obj_id_list:
            active_ws_data_list_for_id: List[WSData] = \
                pydantic_class_type.read_ws_path_with_id_ws_connection_manager.get_activ_ws_tuple_list_with_id(
                    pydantic_obj_id)

            if active_ws_data_list_for_id:
                async with pydantic_class_type.read_ws_path_with_id_ws_connection_manager.rlock:
                    await broadcast_from_active_ws_data_set(
                        active_ws_data_list_for_id, pydantic_class_type, pydantic_obj_id,
                        pydantic_class_type.read_ws_path_with_id_ws_connection_manager.broadcast,
                        tasks_list, broadcast_with_id=True, dummy_pydantic_model=dummy_pydantic_model,
                        filter_agg_pipeline=filter_agg_pipeline, has_links=has_links
                    )
    if tasks_list:
        await execute_tasks_list_with_all_completed(tasks_list, pydantic_class_type)


async def execute_update_agg_pipeline(pydantic_class_type: Type[DocumentModel],
                                      proto_package_name: str, update_agg_pipeline: Any = None):
    if update_agg_pipeline is not None:
        aggregated_pydantic_list: List[pydantic_class_type]
        aggregated_pydantic_list = await generic_read_http(pydantic_class_type, proto_package_name,
                                                           filter_agg_pipeline=update_agg_pipeline)

        id_list = []
        for aggregated_pydantic_obj in aggregated_pydantic_list:
            id_list.append(aggregated_pydantic_obj.id)

        if pydantic_class_type.is_time_series:
            # TimeSeries has limitations when it comes to update:
            # https://www.mongodb.com/docs/manual/core/timeseries/timeseries-limitations/#updates
            # We have implemented alternative way to avoid limitations
            logging.info("Warning: Update using aggregate pipeline is expensive in time_series - "
                         "time-series have limitations for which we have implemented alternative but expensive way")

            # first deleting all update objects
            pydantic_list: List[DocumentModel] = \
                await pydantic_class_type.find(In(pydantic_class_type.id, id_list)).to_list()
            for pydantic_obj in pydantic_list:
                await pydantic_obj.delete()

            # creating new objects with updated values
            await pydantic_class_type.insert_many(aggregated_pydantic_list)
        else:
            async with BulkWriter() as bulk_writer:
                for aggregated_pydantic_obj in aggregated_pydantic_list:
                    await aggregated_pydantic_obj.replace(bulk_writer)
        await publish_ws_all(pydantic_class_type, id_list, update_ws_with_id=True)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_http(pydantic_class_type: Type[DocumentModel],
                            proto_package_name: str, pydantic_obj: DocumentModel,
                            filter_agg_pipeline: Any = None,
                            update_agg_pipeline: Any = None, has_links: bool = False,
                            return_obj_copy: bool | None = True) -> DocumentModel | bool:
    if not has_links:
        new_pydantic_obj: pydantic_class_type = await pydantic_obj.create()
    else:
        new_pydantic_obj: pydantic_class_type = await pydantic_obj.save(link_rule=WriteRules.WRITE)
    await execute_update_agg_pipeline(pydantic_class_type, proto_package_name, update_agg_pipeline)

    await publish_ws(pydantic_class_type, new_pydantic_obj.id, filter_agg_pipeline, has_links)

    if return_obj_copy:
        fetched_obj = await get_obj(pydantic_class_type, new_pydantic_obj.id, filter_agg_pipeline, has_links)
        return fetched_obj
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_all_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                                pydantic_obj_list: List[DocumentModel],
                                filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                                has_links: bool = False, return_obj_copy: bool | None = True) -> List[DocumentModel] | bool:

    if not has_links:
        new_pydantic_obj_list: InsertManyResult = await pydantic_class_type.insert_many(pydantic_obj_list)
    else:
        new_pydantic_obj_list: InsertManyResult = await pydantic_class_type.insert_many(pydantic_obj_list,
                                                                                        link_rule=WriteRules.WRITE)
    await execute_update_agg_pipeline(pydantic_class_type, proto_package_name, update_agg_pipeline)

    await publish_ws_all(pydantic_class_type, new_pydantic_obj_list.inserted_ids, filter_agg_pipeline, has_links)

    if return_obj_copy:
        fetched_obj_list = await get_obj_list(pydantic_class_type, new_pydantic_obj_list.inserted_ids,
                                              filter_agg_pipeline, has_links)
        return fetched_obj_list
    else:
        return True


# def _get_beanie_formatted_update_request_json(updated_pydantic_obj_dict: Dict):
#     # creating new obj without id and _id key
#     request_obj = {'$set': updated_pydantic_obj_dict.items()}
#     return request_obj


async def _underlying_patch_n_put(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                                  stored_pydantic_obj: DocumentModel,
                                  updated_pydantic_obj_dict: Dict, filter_agg_pipeline: Any = None,
                                  update_agg_pipeline: Any = None, has_links: bool = False,
                                  return_obj_copy: bool | None = True) -> DocumentModel | bool:
    """
        Underlying interface for Single object Put & Patch
    """
    _id = updated_pydantic_obj_dict.get("_id")

    # todo: No has_link impl for tme series yet
    if pydantic_class_type.is_time_series:
        # TimeSeries has limitations when it comes to update:
        # https://www.mongodb.com/docs/manual/core/timeseries/timeseries-limitations/#updates
        # We have implemented alternative way to avoid limitations
        logging.info("Warning: Patch/Put operations are expensive in time_series - "
                     "time-series have limitations for which we have implemented alternative but expensive way")

        # First Deleting obj in time-series approach
        await stored_pydantic_obj.delete()

        # then creating update object
        new_created_obj: pydantic_class_type = pydantic_class_type(**updated_pydantic_obj_dict)
        await new_created_obj.create()

    else:
        if not has_links:
            # prepare for DB insert (DB update Obj format)
            if _id:
                del updated_pydantic_obj_dict["_id"]

            await stored_pydantic_obj.update(BeanieSet(updated_pydantic_obj_dict))
            # no need to revert removed _id from updated_pydantic_obj_dict since after here not being used

        else:
            tmp_obj = pydantic_class_type(**updated_pydantic_obj_dict)
            await tmp_obj.save(link_rule=WriteRules.WRITE)
    await execute_update_agg_pipeline(pydantic_class_type, proto_package_name, update_agg_pipeline)

    return_value: DocumentModel | bool
    if return_obj_copy:
        return_value = await get_obj(pydantic_class_type, _id,
                                     filter_agg_pipeline, has_links)
    else:
        return_value = True

    await publish_ws(pydantic_class_type, _id, filter_agg_pipeline, has_links, update_ws_with_id=True)
    return return_value


async def _underlying_patch_n_put_all(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                                      stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]],
                                      updated_obj_id_list: List[Any] | None = None,
                                      filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                                      has_links: bool = False, return_obj_copy: bool | None = True
                                      ) -> List[DocumentModel] | bool:
    """
    Underlying interface for Put-All & Patch-All
    """
    if pydantic_class_type.is_time_series:
        # TimeSeries has limitations when it comes to update:
        # https://www.mongodb.com/docs/manual/core/timeseries/timeseries-limitations/#updates
        # We have implemented alternative way to avoid limitations
        logging.info("Warning: PatchAll/PutALL operations are expensive in time_series - "
                     "time-series have limitations for which we have implemented alternative but expensive way")
        new_create_object_list: List[DocumentModel] = []
        for stored_pydantic_obj_, updated_pydantic_obj_dict in stored_pydantic_obj_n_updated_obj_dict_tuple_list:
            # First deleting all stored objects one by one
            await stored_pydantic_obj_.delete()
            new_create_object_list.append(pydantic_class_type(**updated_pydantic_obj_dict))

        # creating new objects with updated values
        await pydantic_class_type.insert_many(new_create_object_list)
    else:
        # todo: missing has_links currently
        async with BulkWriter() as bulk_writer:
            for stored_pydantic_obj_, updated_pydantic_obj_dict in stored_pydantic_obj_n_updated_obj_dict_tuple_list:
                _id = updated_pydantic_obj_dict.get("_id")
                # prepare for DB insert (DB update Obj format)
                if _id:
                    del updated_pydantic_obj_dict["_id"]
                # request_obj = _get_beanie_formatted_update_request_json(updated_pydantic_obj_dict)
                await stored_pydantic_obj_.update(BeanieSet(updated_pydantic_obj_dict), bulk_writer=bulk_writer)
                # await stored_pydantic_obj_.update_all(BeanieSet(updated_pydantic_obj_dict), bulk_writer=bulk_writer)
                # no need to revert removed _id from updated_pydantic_obj_dict since after here not being used

    await execute_update_agg_pipeline(pydantic_class_type, proto_package_name, update_agg_pipeline)

    await publish_ws_all(pydantic_class_type, updated_obj_id_list, filter_agg_pipeline, has_links, update_ws_with_id=True)

    if return_obj_copy:
        stored_obj_list = await get_obj_list(pydantic_class_type, updated_obj_id_list,
                                             filter_agg_pipeline, has_links)
        return stored_obj_list
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str, stored_pydantic_obj: DocumentModel,
                           pydantic_obj_updated: DocumentModel, filter_agg_pipeline: Any = None,
                           update_agg_pipeline: Any = None, has_links: bool = False,
                           return_obj_copy: bool | None = True) -> DocumentModel | bool:
    if stored_pydantic_obj.update_id == pydantic_obj_updated.update_id:
        # this is for cases where fetched object is passed as update object with slight changes. In these cases,
        # update id since is set as last stored value will not be increased automatically
        pydantic_obj_updated.update_id = pydantic_class_type.next_update_id()
    return await _underlying_patch_n_put(pydantic_class_type, proto_package_name, stored_pydantic_obj,
                                         pydantic_obj_updated.model_dump(by_alias=True),
                                         filter_agg_pipeline,
                                         update_agg_pipeline, has_links,
                                         return_obj_copy)


def get_stored_obj_id_to_obj_dict(stored_pydantic_obj_list: List[DocumentModel]
                                  ) -> Dict[int, DocumentModel] | Dict[str, DocumentModel] | Dict[PydanticObjectId, DocumentModel]:
    stored_obj_id_to_obj_dict: Dict[int, DocumentModel] | Dict[str, DocumentModel] | Dict[PydanticObjectId, DocumentModel] = {}
    for stored_pydantic_obj in stored_pydantic_obj_list:
        if stored_pydantic_obj.id not in stored_obj_id_to_obj_dict:
            stored_obj_id_to_obj_dict[stored_pydantic_obj.id] = stored_pydantic_obj
    return stored_obj_id_to_obj_dict


def _generic_put_all_http(stored_pydantic_obj_list: List[DocumentModel],
                          updated_pydantic_obj_list: List[DocumentModel]) -> List[Tuple[DocumentModel, Dict]]:
    stored_obj_id_to_obj_dict = get_stored_obj_id_to_obj_dict(stored_pydantic_obj_list)

    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = []
    for index in range(len(updated_pydantic_obj_list)):
        stored_pydantic_obj_n_updated_obj_dict_tuple_list.append(
            (stored_obj_id_to_obj_dict[updated_pydantic_obj_list[index].id],
             updated_pydantic_obj_list[index].model_dump(by_alias=True)))
    return stored_pydantic_obj_n_updated_obj_dict_tuple_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_all_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                               stored_pydantic_obj_list: List[DocumentModel],
                               updated_pydantic_obj_list: List[DocumentModel], updated_obj_id_list: List[Any],
                               filter_agg_pipeline: Any = None,
                               update_agg_pipeline: Any = None, has_links: bool = False,
                               return_obj_copy: bool | None = True) -> List[DocumentModel] | bool:
    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = \
        _generic_put_all_http(stored_pydantic_obj_list, updated_pydantic_obj_list)
    return await _underlying_patch_n_put_all(pydantic_class_type, proto_package_name,
                                             stored_pydantic_obj_n_updated_obj_dict_tuple_list,
                                             updated_obj_id_list, filter_agg_pipeline,
                                             update_agg_pipeline, has_links, return_obj_copy)


def _assign_missing_ids_n_handle_date_time_type(field_model_type: Type[Any],
                                                key: str,
                                                value: Any,
                                                pydantic_obj_update_json: Dict,
                                                ignore_handling_datetime: bool | None = False):
    if (isinstance(field_model_type, types.UnionType) or (type(field_model_type) == typing._UnionGenericAlias) or
            field_model_type.__name__ == "List"):
        if issubclass(field_model_type.__args__[0], BaseModel):
            for val in value:
                assign_missing_ids_n_handle_date_time_type(
                    field_model_type.__args__[0], val, ignore_root_id_check=False,
                    ignore_handling_datetime=ignore_handling_datetime)

                if field_model_type.__args__[0].model_fields.get("id") is not None:
                    if val.get("_id") is None:
                        val["_id"] = (
                            field_model_type.__args__[0].model_fields.get("id").default_factory())
        else:
            # since JSON has no support to Datetime when receiving pydantic_obj_update_json
            # all datetime type fields would be of str type
            if (not ignore_handling_datetime) and issubclass(field_model_type.__args__[0],
                                                             datetime.datetime):
                if isinstance(value, str):
                    # Setting values parsed as str back to Datetime type
                    pydantic_obj_update_json[key] = pendulum.parse(value)
    else:
        if issubclass(field_model_type, BaseModel):
            assign_missing_ids_n_handle_date_time_type(field_model_type, value,
                                                       ignore_root_id_check=False,
                                                       ignore_handling_datetime=
                                                       ignore_handling_datetime)

            if field_model_type.model_fields.get("id") is not None:
                if value.get("_id") is None:
                    value["_id"] = field_model_type.model_fields.get("id").default_factory()
        else:
            # since JSON has no support to Datetime when receiving pydantic_obj_update_json
            # all datetime type fields would be of str type
            if (not ignore_handling_datetime) and "DateTime" in field_model_type.__name__:
                if isinstance(value, str):
                    # Setting values parsed as str back to Datetime type
                    pydantic_obj_update_json[key] = pendulum.parse(value)


def assign_missing_ids_n_handle_date_time_type(pydantic_class_type: Type[DocumentModel] | Type[PydanticModel],
                                               pydantic_obj_update_json: Dict,
                                               ignore_root_id_check: bool | None = True,
                                               ignore_handling_datetime: bool | None = False):
    """
    Handling for patch if any model in json has id field as mandatory field but is not set, sets the id field
    with new id of same type
    Reason: Since patch web client takes json as parameter instead of particular model instance that's why
    id field is not autogenerated, and if there is some use-case that can't provide id (ex: Web UI), we have
    to add id explicitly before saving in db
    """
    for key, value in pydantic_obj_update_json.items():
        if value is not None:
            if ignore_root_id_check:
                if key == "_id":
                    ignore_root_id_check = False
                    continue
            field_model: FieldInfo
            if (field_model := pydantic_class_type.model_fields.get(key)) is not None:
                field_model_type = field_model.annotation
                if ((issubclass(type(field_model_type), UnionType)) or
                        (field_model_type.__name__ == "Optional")):
                    # entering here suggests that field contains None with main type
                    field_model_type_tuple: Tuple = field_model_type.__args__
                    type_other_than_none: Type[Any]
                    for field_model_type_ in field_model_type_tuple:
                        if field_model_type_.__name__ == "List" or not isinstance(None, field_model_type_):
                            type_other_than_none = field_model_type_
                            break
                    else:
                        raise Exception("Field type from annotation is Tuple signifying, field must be optional, "
                                        "nut couldn't find any Type other than NoneType in tuple annotation, "
                                        f"field_model_type: {field_model_type}, field_name: {key}, "
                                        f"pydantic_class_type: {pydantic_class_type.__name__}")

                    _assign_missing_ids_n_handle_date_time_type(type_other_than_none, key, value,
                                                                pydantic_obj_update_json,
                                                                ignore_handling_datetime)
                else:
                    _assign_missing_ids_n_handle_date_time_type(field_model_type, key, value, pydantic_obj_update_json,
                                                                ignore_handling_datetime)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                             stored_pydantic_obj: DocumentModel, pydantic_obj_update_json,
                             filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                             has_links: bool = False, return_obj_copy: bool | None = True
                             ) -> DocumentModel | bool:
    assign_missing_ids_n_handle_date_time_type(pydantic_class_type, pydantic_obj_update_json)
    # since patch not call's default_factory of update_id
    pydantic_obj_update_json["update_id"] = pydantic_class_type.next_update_id()

    try:
        updated_pydantic_obj_dict = compare_n_patch_dict(stored_pydantic_obj.model_dump(by_alias=True),
                                                         pydantic_obj_update_json)
    except Exception as e:
        err_str = f"compare_n_patch_dict failed: exception: {e}"
        logging.exception(err_str)
        raise HTTPException(detail=err_str, status_code=400)
    return await _underlying_patch_n_put(pydantic_class_type, proto_package_name, stored_pydantic_obj,
                                         updated_pydantic_obj_dict,
                                         filter_agg_pipeline, update_agg_pipeline, has_links, return_obj_copy)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_without_db_update_http(
        pydantic_class_type: Type[DocumentModel],
        stored_pydantic_obj: DocumentModel, pydantic_obj_update_json,
        return_obj_copy: bool | None = True) -> DocumentModel | bool:
    assign_missing_ids_n_handle_date_time_type(pydantic_class_type, pydantic_obj_update_json)
    try:
        updated_pydantic_obj_dict = compare_n_patch_dict(stored_pydantic_obj.model_dump(by_alias=True),
                                                         pydantic_obj_update_json)
    except Exception as e:
        err_str = f"compare_n_patch_dict failed: exception: {e}"
        logging.exception(err_str)
        raise HTTPException(detail=err_str, status_code=400)
    if return_obj_copy:
        return pydantic_class_type(**updated_pydantic_obj_dict)
    else:
        return True


def underlying_generic_patch_all_http(pydantic_class_type: Type[DocumentModel], stored_pydantic_obj_list: List[DocumentModel],
                                      pydantic_obj_update_json_list: List[Dict],
                                      ignore_datetime_handling: bool | None = None) -> List[Tuple[DocumentModel, Dict]]:
    stored_obj_id_to_obj_dict = get_stored_obj_id_to_obj_dict(stored_pydantic_obj_list)

    stored_pydantic_obj_json_list: List[Dict] = []
    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = []
    for index, pydantic_obj_update_json in enumerate(pydantic_obj_update_json_list):
        assign_missing_ids_n_handle_date_time_type(pydantic_class_type, pydantic_obj_update_json,
                                                   ignore_handling_datetime=ignore_datetime_handling)

        # converting stored objs to json
        stored_pydantic_obj_json = jsonable_encoder(stored_obj_id_to_obj_dict[pydantic_obj_update_json.get("_id")],
                                                    by_alias=True)
        stored_pydantic_obj_json_list.append(stored_pydantic_obj_json)

        # this list since contains container types (list of stored_pydantic_obj_json),
        # gets updated in compare_n_patch_list called below
        stored_pydantic_obj_n_updated_obj_dict_tuple_list.append((stored_obj_id_to_obj_dict[
                                                                      stored_pydantic_obj_json.get("_id")],
                                                                  stored_pydantic_obj_json))
    compare_n_patch_list(stored_pydantic_obj_json_list, pydantic_obj_update_json_list)

    return stored_pydantic_obj_n_updated_obj_dict_tuple_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_all_without_db_update_http(
        pydantic_class_type: Type[DocumentModel], stored_pydantic_obj_list: List[DocumentModel],
        pydantic_obj_update_json_list: List[Dict], return_obj_copy: bool | None = True) -> List[DocumentModel] | bool:
    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = \
        underlying_generic_patch_all_http(pydantic_class_type, stored_pydantic_obj_list, pydantic_obj_update_json_list)
    if return_obj_copy:
        updated_obj_list: List[DocumentModel] = []
        for stored_pydantic_obj_, updated_pydantic_obj_dict in stored_pydantic_obj_n_updated_obj_dict_tuple_list:
            updated_obj_list.append(pydantic_class_type(**updated_pydantic_obj_dict))
        return updated_obj_list
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_all_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                                 stored_pydantic_obj_list: List[DocumentModel],
                                 pydantic_obj_update_json_list: List[Dict], updated_obj_id_list: List[Any],
                                 filter_agg_pipeline: Any = None,
                                 update_agg_pipeline: Any = None, has_links: bool = False,
                                 return_obj_copy: bool | None = True) -> List[DocumentModel] | bool:
    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocumentModel, Dict]] = \
        underlying_generic_patch_all_http(pydantic_class_type, stored_pydantic_obj_list, pydantic_obj_update_json_list)
    return await _underlying_patch_n_put_all(pydantic_class_type, proto_package_name,
                                             stored_pydantic_obj_n_updated_obj_dict_tuple_list,
                                             updated_obj_id_list, filter_agg_pipeline, update_agg_pipeline,
                                             has_links, return_obj_copy)


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                              pydantic_dummy_model, pydantic_obj: DocumentModel,
                              update_agg_pipeline: Any = None, has_links: bool = False,
                              return_obj_copy: bool | None = True) -> DefaultWebResponse | bool:
    _id = pydantic_obj.id
    id_is_int_type = isinstance(_id, int)

    if has_links:
        await pydantic_obj.delete(link_rule=DeleteRules.DELETE_LINKS)
    else:
        await pydantic_obj.delete()
    await execute_update_agg_pipeline(pydantic_class_type, proto_package_name, update_agg_pipeline)
    await publish_ws(pydantic_class_type, _id, has_links=has_links, update_ws_with_id=True,
                     dummy_pydantic_model=pydantic_dummy_model)

    # Setting back incremental id to 0 if collection gets empty
    if id_is_int_type:
        pydantic_objs_count = await pydantic_class_type.count()
        if pydantic_objs_count == 0:
            max_id_val = 0
            max_update_id_vale = 0
            pydantic_class_type.init_max_id(max_id_val, max_update_id_vale)
        # else not required: all good
    # else not required: if id is not int then it must be of PydanticObjectId so no handling required

    if return_obj_copy:
        del_success.id = _id
        return del_success
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_all_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                                  pydantic_dummy_model: Type[PydanticModel], return_obj_copy: bool | None = True
                                  ) -> DefaultWebResponse | bool:
    id_is_int_type = (pydantic_class_type.model_fields.get("id").annotation == int)

    try:
        stored_pydantic_obj_list: List[pydantic_dummy_model] = await pydantic_class_type.find_all().to_list()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    # preparing success message
    del_success.id = []
    for pydantic_obj in stored_pydantic_obj_list:
        del_success.id.append(pydantic_obj.id)

    # deleting all
    await pydantic_class_type.delete_all()

    # Setting back incremental id to 0 if collection gets empty
    if id_is_int_type:
        pydantic_objs_count = await pydantic_class_type.count()
        if pydantic_objs_count == 0:
            max_id_val = 0
            max_update_id_vale = 0
            pydantic_class_type.init_max_id(max_id_val, max_update_id_vale)
        # else not required: all good
    # else not required: if id is not int then it must be of PydanticObjectId so no handling required

    await publish_ws_all(pydantic_class_type, del_success.id, update_ws_with_id=True,
                         dummy_pydantic_model=pydantic_dummy_model)
    if return_obj_copy:
        return del_success
    else:
        return True


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                            filter_agg_pipeline: Any = None, has_links: bool = False,
                            read_ids_list: List[Any] | None = None, projection_model=None):
    pydantic_list: List[pydantic_class_type]
    pydantic_list = \
        await get_obj_list(pydantic_class_type, read_ids_list,
                           filter_agg_pipeline=filter_agg_pipeline, has_links=has_links,
                           projection_model=projection_model)
    if read_ids_list and len(pydantic_list) != len(set(read_ids_list)):
        existing_ids = set()
        for pydantic_obj in pydantic_list:
            if pydantic_obj.id in read_ids_list:
                existing_ids.add(pydantic_obj.id)
        non_existing_ids = set(read_ids_list) - existing_ids
        # Attention: Below err_str is being used by log_analyzer inn regex pattern match,
        # avoid changing it or fix its use-case
        err_str: Final[str] = (f"Couldn't find {pydantic_class_type.__name__} objects with ids: {non_existing_ids} "
                               f"out of requested {read_ids_list}")
        logging.error(err_str)
        raise HTTPException(detail=err_str, status_code=500)

    return pydantic_list


@http_except_n_log_error(status_code=500)
async def generic_read_ws(ws: WebSocket, project_name: str, pydantic_class_type: Type[DocumentModel],
                          filter_agg_pipeline: Any = None, has_links: bool = False, need_initial_snapshot: bool = True):
    is_new_ws: bool = await pydantic_class_type.read_ws_path_ws_connection_manager.connect(ws)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    need_disconnect = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            pydantic_list = \
                await get_obj_list(pydantic_class_type, filter_agg_pipeline=filter_agg_pipeline, has_links=has_links)
            fetched_pydantic_list_json = jsonable_encoder(pydantic_list, by_alias=True)
            fetched_pydantic_list_json_str = json.dumps(fetched_pydantic_list_json)
            await pydantic_class_type.read_ws_path_ws_connection_manager. \
                send_json_to_websocket(fetched_pydantic_list_json_str, ws)
        # else not required: no initial snapshot is provided on this connection

        need_disconnect = await handle_ws(ws, is_new_ws)    # Blocking call
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
        logging.info(f"generic_beanie_get_ws - connection closed by client in ws {ws.client}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await pydantic_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: {ws.client}")


@http_except_n_log_error(status_code=500)
async def generic_query_ws(ws: WebSocket, project_name: str, pydantic_class_type: Type[DocumentModel],
                           filter_callable: Callable[..., Any] | None = None,
                           filter_callable_kwargs: Dict[Any, Any] | None = None,
                           projection_agg_pipeline_callable: Callable[..., Any] | None = None,
                           projection_model: Type[PydanticModel] | None = None,
                           need_initial_snapshot: bool = True):
    if filter_callable_kwargs is None:
        filter_callable_kwargs = {}

    is_new_ws: bool = \
        await pydantic_class_type.read_ws_path_ws_connection_manager.connect(ws, filter_callable,
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

            pydantic_obj_list = await get_obj_list(pydantic_class_type,
                                                   filter_agg_pipeline=projection_agg_pipeline,
                                                   projection_model=projection_model)
            json_data = jsonable_encoder(pydantic_obj_list, by_alias=True)
            json_str = json.dumps(json_data)
            await pydantic_class_type.read_ws_path_ws_connection_manager. \
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
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await pydantic_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: {ws.client}")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_by_id_http(pydantic_class_type: Type[DocumentModel], proto_package_name: str,
                                  pydantic_obj_id: Any, filter_agg_pipeline: Any = None, has_links: bool = False):
    fetched_pydantic_obj: pydantic_class_type = await get_obj(pydantic_class_type, pydantic_obj_id,
                                                              filter_agg_pipeline, has_links)
    if not fetched_pydantic_obj:
        raise HTTPException(status_code=404,
                            detail=id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
    else:
        return fetched_pydantic_obj


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_ws(ws: WebSocket, project_name: str, pydantic_class_type: Type[DocumentModel],
                                pydantic_obj_id: Any, filter_agg_pipeline: Any = None, has_links: bool = False,
                                need_initial_snapshot: bool | None = True):
    # prevent duplicate addition
    is_new_ws: bool = await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.connect(ws, pydantic_obj_id)

    logging.debug(f"websocket client requested to connect: {ws.client}")
    need_disconnect: bool = False
    try:
        if need_initial_snapshot is None or need_initial_snapshot:
            fetched_pydantic_obj: pydantic_class_type = await get_obj(pydantic_class_type, pydantic_obj_id,
                                                                      filter_agg_pipeline, has_links)
            if fetched_pydantic_obj is None:
                raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__,
                                                                                    pydantic_obj_id))
            else:
                fetched_pydantic_obj_json = jsonable_encoder(fetched_pydantic_obj, by_alias=True)
                fetched_pydantic_obj_json_str = json.dumps(fetched_pydantic_obj_json)
                await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.send_json_to_websocket(
                    fetched_pydantic_obj_json_str, ws)
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
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws {ws.client}:"
                          f" {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.disconnect(ws, pydantic_obj_id)
            logging.debug(f"Disconnected to websocket: {ws.client}")


async def get_obj(pydantic_class_type: Type[DocumentModel], pydantic_obj_id: Any,
                  filter_agg_pipeline: Any = None, has_links: bool = False,
                  projection_model: Type[PydanticModel] | None = None):
    fetched_pydantic_obj: pydantic_class_type
    if filter_agg_pipeline is None:
        fetched_pydantic_obj = await pydantic_class_type.get(pydantic_obj_id, fetch_links=has_links)
    else:
        fetched_pydantic_obj = await get_filtered_obj(filter_agg_pipeline, pydantic_class_type,
                                                      pydantic_obj_id, has_links, projection_model)
    return fetched_pydantic_obj


async def get_obj_list(pydantic_class_type: Type[DocumentModel], find_ids: List[Any] | None = None,
                       filter_agg_pipeline: Any = None, has_links: bool = False,
                       projection_model: Type[PydanticModel] | None = None):
    pydantic_list: List[pydantic_class_type]
    try:
        if filter_agg_pipeline is None:
            if find_ids is None:
                pydantic_list = await pydantic_class_type.find_all(fetch_links=has_links).to_list()
            else:
                pydantic_list = await pydantic_class_type.find(In(pydantic_class_type.id, find_ids),
                                                               fetch_links=has_links).to_list()
        else:
            # find_ids if none: will be handled inside get_filtered_obj_list implicitly
            pydantic_list = await get_filtered_obj_list(filter_agg_pipeline, pydantic_class_type, find_ids,
                                                        has_links=has_links, projection_model=projection_model)
        return pydantic_list
    except ValidationError as e:
        logging.exception(f"Pydantic validation error: {e}")
        raise Exception(e)


async def get_filtered_obj_list(filter_agg_pipeline: Dict, pydantic_class_type: Type[DocumentModel],
                                pydantic_obj_id_list: List | None = None,
                                has_links: bool = False, projection_model: Type[PydanticModel] | None = None):
    # prevent polluting caller provided filter_agg_pipeline
    filter_agg_pipeline_copy = deepcopy(filter_agg_pipeline)
    if pydantic_obj_id_list is not None:
        pydantic_obj_id_field: str = "_id"
        if (match := filter_agg_pipeline_copy.get("match")) is not None:
            match.append((pydantic_obj_id_field, pydantic_obj_id_list))
        else:
            filter_agg_pipeline_copy["match"] = [(pydantic_obj_id_field, pydantic_obj_id_list)]
    agg_pipeline = get_aggregate_pipeline(filter_agg_pipeline_copy)
    if projection_model is None:
        projection_model = pydantic_class_type
    else:
        agg_pipeline = filter_agg_pipeline["aggregate"]
    find_all_resp = pydantic_class_type.find(fetch_links=has_links)
    pydantic_list = await find_all_resp.aggregate(
        aggregation_pipeline=agg_pipeline,
        projection_model=projection_model,
        session=None,
        ignore_cache=False
    ).to_list()
    return pydantic_list


async def get_filtered_obj(filter_agg_pipeline: Dict, pydantic_class_type: Type[DocumentModel],
                           pydantic_obj_id: Any, has_links: bool = False,
                           projection_model: Type[PydanticModel] | None = None):
    pydantic_list = await get_filtered_obj_list(filter_agg_pipeline, pydantic_class_type,
                                                [pydantic_obj_id], has_links, projection_model)
    if pydantic_list:
        return pydantic_list[0]
    else:
        return None


def get_aggregate_pipeline(encap_agg_pipeline: Dict):
    filter_tuple_list = encap_agg_pipeline.get("redact")
    match_tuple_list = encap_agg_pipeline.get("match")  # [(key1: value1), (key2: value2)]
    additional_agg = encap_agg_pipeline.get("agg")
    agg_pipeline = []
    if match_tuple_list is not None:
        agg_pipeline.append({"$match": {}})
        for match_tuple in match_tuple_list:
            if len(match_tuple) != 2:
                raise Exception(f"Expected minimum 2 values (field-name, field-value) in tuple found match_tuple: "
                                f"{match_tuple} in match_tuple_list: {match_tuple_list}")
            match_variable_name, match_variable_value = match_tuple
            if match_variable_name is not None and len(match_variable_name) != 0:
                if match_variable_value is not None:
                    match_pipeline = agg_pipeline[0].get("$match")
                    if match_pipeline is None:
                        agg_pipeline[0]["$match"] = {match_variable_name: {"$in": match_variable_value}}
                    else:
                        match_pipeline[match_variable_name] = {"$in": match_variable_value}
                else:
                    raise Exception(
                        f"Error: match_variable_name passed as: {match_variable_name}, while match_variable_value "
                        f"was passed None - not supported")
    if filter_tuple_list is not None:
        for filter_tuple in filter_tuple_list:
            if len(filter_tuple) < 2:
                raise Exception(f"Expected minimum 2 values (field-name, field-value) in tuple found filter_tuple: "
                                f"{filter_tuple} in filter_tuple_list: {filter_tuple_list}")
            filter_list = list(filter_tuple)
            filtered_variable_name = filter_list[0]
            filter_list.remove(filter_list[0])
            # $in expects list with 1st entry as variable-name, and 2nd entry as list of variable-values
            redact_data_filter = \
                {
                    "$redact": {
                        "$cond": {
                            "if": {"$or": [{"$in": []}, {"$not": ""}]},
                            "then": "$$DESCEND",
                            "else": "$$PRUNE"
                        }
                    }
                }
            updated_filtered_variable_name = "$" + filtered_variable_name
            redact_data_filter["$redact"]["$cond"]["if"]["$or"][0]["$in"].append(updated_filtered_variable_name)
            redact_data_filter["$redact"]["$cond"]["if"]["$or"][0]["$in"].append(filter_list)
            redact_data_filter["$redact"]["$cond"]["if"]["$or"][1]["$not"] = updated_filtered_variable_name
            agg_pipeline.append(redact_data_filter)

    if additional_agg is not None:
        agg_pipeline.extend(additional_agg)
        return agg_pipeline
    elif len(agg_pipeline) != 0:
        return agg_pipeline
    else:
        return encap_agg_pipeline.get("aggregate")
