# system imports
import copy
import json
import os
import asyncio
from typing import List, Any, Dict, Final, Callable, Set
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException, ConnectionClosed
from copy import deepcopy

# other package imports
from pydantic import ValidationError
from beanie.odm.bulk import BulkWriter
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from beanie import WriteRules, DeleteRules, PydanticObjectId
from pydantic.fields import SHAPE_LIST
from pydantic.main import ModelMetaclass
from FluxPythonUtils.scripts.utility_functions import perf_benchmark

# project specific imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, compare_n_patch_dict

"""
1. FilterAggregate [only filters the returned value]
2. UpdateAggregate [ modifies data in DB based on aggregate query and returns updated data ]
3. Create : FilterAggregate for return param and UpdateAggregate for massaging data post insert
4. Read, ReadAll : FilterAggregate for return param
5. Delete : UpdateAggregate for massaging data post delete
"""

id_not_found: Final[DefaultWebResponse] = DefaultWebResponse(msg="Id not Found")
del_success: Final[DefaultWebResponse] = DefaultWebResponse(msg="Deletion Successful")
host_env_var: Final[str] = "127.0.0.1" if (env_host := os.getenv("HOST")) is None else env_host
port_env_var: Final[int] = 8000 if (env_port := os.getenv("PORT")) is None else int(env_port)


async def publish_ws(pydantic_class_type, stored_obj, stored_obj_id=None):
    if pydantic_class_type.read_ws_path_ws_connection_manager is not None:
        json_data = jsonable_encoder(stored_obj, by_alias=True)
        json_str = json.dumps(json_data)
        tasks_list: List[asyncio.Task] = []
        await pydantic_class_type.read_ws_path_ws_connection_manager.broadcast(json_str, tasks_list)
        if stored_obj_id is not None:
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.broadcast(json_str, stored_obj.id,
                                                                                           tasks_list)
        pending_tasks: Set[asyncio.Task] | None = None
        completed_tasks: Set[asyncio.Task] | None = None
        if tasks_list:
            try:
                # wait doesn't raise TimeoutError! Futures that aren't done when timeout occurs are returned in 2nd set
                completed_tasks, pending_tasks = await asyncio.wait(tasks_list, return_when=asyncio.ALL_COMPLETED,
                                                                    timeout=20.0)
            except Exception as e:
                logging.error(f"await asyncio.wait raised exception: {e}")
        else:
            logging.debug("Called publish_ws with no active ws registrations for both with and without id "
                          f"of model {pydantic_class_type.__name__}")

        while completed_tasks:
            completed_task = None
            try:
                completed_task = completed_tasks.pop()
            except Exception as e:
                idx = int(completed_task.get_name())
                logging.exception(f"publish_ws failed for task {tasks_list[idx]} with exception: {e}")

        if pending_tasks:
            logging.error("Received timed out pending tasks in publish_ws, dropping them. "
                          f"PendingTasks: {[pending_task for pending_task in pending_tasks]}")


async def execute_update_agg_pipeline(pydantic_class_type, update_agg_pipeline: Any = None):
    if update_agg_pipeline is not None:
        aggregated_pydantic_list: List[pydantic_class_type]
        aggregated_pydantic_list = await generic_read_http(pydantic_class_type, update_agg_pipeline)
        async with BulkWriter() as bulk_writer:
            for aggregated_pydantic_obj in aggregated_pydantic_list:
                request_obj = {'$set': aggregated_pydantic_obj.dict().items()}
                await aggregated_pydantic_obj.update(request_obj, bulk_writer=bulk_writer)
        for aggregated_pydantic_obj in aggregated_pydantic_list:
            await publish_ws(pydantic_class_type, aggregated_pydantic_obj)


@http_except_n_log_error(status_code=500)
async def generic_post_http(pydantic_class_type, pydantic_obj, filter_agg_pipeline: Any = None,
                            update_agg_pipeline: Any = None, has_links: bool = False):
    if not has_links:
        new_pydantic_obj: pydantic_class_type = await pydantic_obj.create()
    else:
        new_pydantic_obj: pydantic_class_type = await pydantic_obj.save(link_rule=WriteRules.WRITE)
    await execute_update_agg_pipeline(pydantic_class_type, update_agg_pipeline)
    stored_obj = await get_obj(pydantic_class_type, new_pydantic_obj.id, filter_agg_pipeline, has_links)
    await publish_ws(pydantic_class_type, stored_obj)
    return stored_obj


async def _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj, pydantic_obj_updated,
                                  updated_pydantic_obj_dict, filter_agg_pipeline: Any = None,
                                  update_agg_pipeline: Any = None, has_links: bool = False):
    if not has_links:
        if pydantic_class_type.__fields__.get("id").type_ == PydanticObjectId:
            # Handling to prevent below error caused due to some cases using PydanticObjectId as id type
            # in beanie model, as PydanticObjectId id type is default type in beanie and can't be updated
            # Error: pymongo.errors.WriteError: Performing an update on the path '_id' would modify the immutable
            #        field '_id'
            # Just replacing '_id' with 'id' in request json as handling
            request_dict = copy.deepcopy(updated_pydantic_obj_dict)
            request_dict["id"] = request_dict["_id"]
            del request_dict["_id"]
            request_obj = {'$set': request_dict.items()}
        else:
            request_obj = {'$set': updated_pydantic_obj_dict.items()}
        await stored_pydantic_obj.update(request_obj)
    else:
        tmp_obj = pydantic_class_type(**updated_pydantic_obj_dict)
        await tmp_obj.save(link_rule=WriteRules.WRITE)
    await execute_update_agg_pipeline(pydantic_class_type, update_agg_pipeline)
    stored_obj = await get_obj(pydantic_class_type, updated_pydantic_obj_dict.get("_id"), filter_agg_pipeline, has_links)
    await publish_ws(pydantic_class_type, stored_obj, stored_obj.id)
    return stored_obj


@http_except_n_log_error(status_code=500)
async def generic_put_http(pydantic_class_type, stored_pydantic_obj, pydantic_obj_updated,
                           filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None, has_links: bool = False):
    return await _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj,
                                         pydantic_obj_updated, pydantic_obj_updated.dict(by_alias=True),
                                         filter_agg_pipeline,
                                         update_agg_pipeline, has_links)


def assign_missing_ids(pydantic_class_type, pydantic_obj_update_json: Dict, ignore_root_id_check: bool | None = True):
    for key, value in pydantic_obj_update_json.items():
        if value is not None:
            if ignore_root_id_check:
                if key == "_id":
                    continue
            if (field_model := pydantic_class_type.__fields__.get(key)) is not None:
                field_model_type = field_model.type_
                if isinstance(field_model_type, ModelMetaclass):
                    if field_model.shape == SHAPE_LIST:
                        for val in value:
                            assign_missing_ids(field_model_type, val, ignore_root_id_check=False)
                    else:
                        assign_missing_ids(field_model_type, value, ignore_root_id_check=False)
                    if field_model_type.__fields__.get("id") is not None:
                        if field_model.shape == SHAPE_LIST:
                            for obj in value:
                                if obj.get("_id") is None:
                                    obj["_id"] = field_model_type.__fields__.get("id").default_factory()
                        else:
                            if value.get("_id") is None:
                                value["_id"] = field_model_type.__fields__.get("id").default_factory()


@http_except_n_log_error(status_code=500)
async def generic_patch_http(pydantic_class_type, stored_pydantic_obj, pydantic_obj_update_json,
                             filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None, has_links: bool = False):
    assign_missing_ids(pydantic_class_type, pydantic_obj_update_json)
    updated_pydantic_obj_dict = compare_n_patch_dict(stored_pydantic_obj.dict(by_alias=True),
                                                     pydantic_obj_update_json)
    return await _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj,
                                         pydantic_obj_update_json, updated_pydantic_obj_dict, filter_agg_pipeline,
                                         update_agg_pipeline, has_links)


@http_except_n_log_error(status_code=500)
async def generic_delete_http(pydantic_class_type, pydantic_dummy_model, pydantic_obj,
                              update_agg_pipeline: Any = None, has_links: bool = False):
    id_is_int_type = isinstance(pydantic_obj.id, int)

    if has_links:
        await pydantic_obj.delete(link_rule=DeleteRules.DELETE_LINKS)
    else:
        await pydantic_obj.delete()
    await execute_update_agg_pipeline(pydantic_class_type, update_agg_pipeline)
    try:
        pydantic_base_model: pydantic_dummy_model = pydantic_dummy_model(id=pydantic_obj.id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    await publish_ws(pydantic_class_type, pydantic_base_model, pydantic_base_model.id)
    del_success.id = pydantic_obj.id

    # Setting back incremental is to 0 if collection gets empty
    if id_is_int_type:
        pydantic_objs_count = await pydantic_class_type.count()
        if pydantic_objs_count == 0:
            pydantic_class_type.init_max_id(0)
        # else not required: all good
    # else not required: if id is not int then it must be of PydanticObjectId so no handling required

    return del_success


@http_except_n_log_error(status_code=500)
async def generic_read_http(pydantic_class_type, filter_agg_pipeline: Any = None, has_links: bool = False):
    pydantic_list: List[pydantic_class_type]
    pydantic_list = await get_obj_list(pydantic_class_type, filter_agg_pipeline, has_links)
    return pydantic_list


async def handle_ws(ws: WebSocket, is_new_ws: bool):
    need_disconnect = False
    if is_new_ws:
        while True:
            json_data = await ws.receive()  # {"type": "websocket.disconnect", "code": exc.code}
            if json_data["type"] == "websocket.disconnect":
                need_disconnect = True
                break
            else:
                logging.error(
                    f"Unexpected! WS client send data to server (ignoring) where none is expected, data: {json_data}")
                continue
    # else not required - some other path has invoked the websocket.receive(), we can ignore
    return need_disconnect


def get_all_ws_url(host: str, port: int, proto_package_name: str, pydantic_class_type) -> str:
    return f"http://{host}:{port}/{proto_package_name}/" \
           f"get-all-{convert_camel_case_to_specific_case(pydantic_class_type.__name__)}-ws/"


def get_by_id_ws_url(host: str, port: int, proto_package_name: str, pydantic_class_type,
                     pydantic_obj_id: Any) -> str:
    return f"http://{host}:{port}/{proto_package_name}/" \
           f"get-{convert_camel_case_to_specific_case(pydantic_class_type.__name__)}-ws/{pydantic_obj_id}"


@http_except_n_log_error(status_code=500)
async def generic_read_ws(ws: WebSocket, proto_package_name: str,
                          pydantic_class_type, filter_agg_pipeline: Any = None, has_links: bool = False):
    is_new_ws: bool = await pydantic_class_type.read_ws_path_ws_connection_manager.connect(ws)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    logging.debug(f"connected to websocket: "
                  f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}")
    need_disconnect = False
    try:
        pydantic_list = await get_obj_list(pydantic_class_type, filter_agg_pipeline, has_links)
        fetched_pydantic_list_json = jsonable_encoder(pydantic_list, by_alias=True)
        fetched_pydantic_list_json_str = json.dumps(fetched_pydantic_list_json)
        await pydantic_class_type.read_ws_path_ws_connection_manager. \
            send_json_to_websocket(fetched_pydantic_list_json_str, ws)
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException in url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully "
                     f"within while loop in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: web socket connection closed with error "
                     f"within while loop in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws url "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws url "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await pydantic_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}")


@http_except_n_log_error(status_code=500)
async def generic_query_ws(ws: WebSocket, proto_package_name: str, pydantic_class_type,
                           filter_callable: Callable[..., Any] | None = None, call_kwargs: Dict[Any, Any] | None = None):
    if call_kwargs is None:
        call_kwargs = {}
    is_new_ws: bool = await pydantic_class_type.read_ws_path_ws_connection_manager.connect(ws, filter_callable,
                                                                                           call_kwargs)
    logging.debug(f"websocket client requested to connect: {ws.client}")
    logging.debug(f"connected to websocket: "
                  f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}")
    need_disconnect = False
    try:
        await pydantic_class_type.read_ws_path_ws_connection_manager. \
            send_json_to_websocket("[]", ws)
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException in url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully "
                     f"within while loop in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: web socket connection closed with error "
                     f"within while loop in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws url "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws url "
                     f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws url "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await pydantic_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}")


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_http(pydantic_class_type, pydantic_obj_id,
                                  filter_agg_pipeline: Any = None, has_links: bool = False):
    fetched_pydantic_obj: pydantic_class_type = await get_obj(pydantic_class_type, pydantic_obj_id,
                                                              filter_agg_pipeline, has_links)
    if not fetched_pydantic_obj:
        raise HTTPException(status_code=404,
                            detail=id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
    else:
        return fetched_pydantic_obj


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_ws(ws: WebSocket, proto_package_name: str, pydantic_class_type, pydantic_obj_id,
                                filter_agg_pipeline: Any = None, has_links: bool = False):
    # prevent duplicate addition
    is_new_ws: bool = await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.connect(ws, pydantic_obj_id)

    logging.debug(f"websocket client requested to connect: {ws.client}")
    logging.debug(f"connected to websocket: "
                  f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}")
    need_disconnect: bool = False
    try:
        fetched_pydantic_obj: pydantic_class_type = await get_obj(pydantic_class_type, pydantic_obj_id,
                                                                  filter_agg_pipeline, has_links)
        if fetched_pydantic_obj is None:
            raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__,
                                                                                pydantic_obj_id))
        else:
            fetched_pydantic_obj_json = jsonable_encoder(fetched_pydantic_obj, by_alias=True)
            fetched_pydantic_obj_json_str = json.dumps(fetched_pydantic_obj_json)
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager. \
                send_json_to_websocket(fetched_pydantic_obj_json_str, ws)
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException in ws url "
                     f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully "
                     f"within while loop in ws url "
                     f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: web socket connection closed with error "
                     f"within while loop in ws url "
                     f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client in ws url "
                     f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws url "
                          f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}:"
                          f" {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop in ws url "
                     f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close in ws url "
                          f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}:"
                          f" {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.disconnect(ws, pydantic_obj_id)
            logging.debug(f"Disconnected to websocket: "
                          f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}")


async def get_obj(pydantic_class_type, pydantic_obj_id, filter_agg_pipeline: Any = None, has_links: bool = False):
    fetched_pydantic_obj: pydantic_class_type
    if filter_agg_pipeline is None:
        fetched_pydantic_obj = await pydantic_class_type.get(pydantic_obj_id, fetch_links=has_links)
    else:
        fetched_pydantic_obj = await get_filtered_obj(filter_agg_pipeline, pydantic_class_type,
                                                      pydantic_obj_id, has_links)
    return fetched_pydantic_obj


async def get_obj_list(pydantic_class_type, filter_agg_pipeline: Any = None, has_links: bool = False):
    pydantic_list: List[pydantic_class_type]
    try:
        if filter_agg_pipeline is None:
            pydantic_list = await pydantic_class_type.find_all(fetch_links=has_links).to_list()
        else:
            pydantic_list = await get_filtered_obj_list(filter_agg_pipeline, pydantic_class_type, has_links=has_links)
        return pydantic_list
    except ValidationError as e:
        logging.error(f"Pydantic validation error: {e}")
        raise e


async def get_filtered_obj_list(filter_agg_pipeline, pydantic_class_type, pydantic_obj_id=None,
                                has_links: bool = False):
    # prevent polluting caller provided filter_agg_pipeline
    filter_agg_pipeline_copy = deepcopy(filter_agg_pipeline)
    if pydantic_obj_id is not None:
        pydantic_obj_id_field: str = "_id"
        if (match := filter_agg_pipeline_copy.get("match")) is not None:
            match.append((pydantic_obj_id_field, pydantic_obj_id))
        else:
            filter_agg_pipeline_copy["match"] = [(pydantic_obj_id_field, pydantic_obj_id)]
    agg_pipeline = get_aggregate_pipeline(filter_agg_pipeline_copy)
    find_all_resp = pydantic_class_type.find(fetch_links=has_links)
    pydantic_list = await find_all_resp.aggregate(
        aggregation_pipeline=agg_pipeline,
        projection_model=pydantic_class_type,
        session=None,
        ignore_cache=False
    ).to_list()
    return pydantic_list


async def get_filtered_obj(filter_agg_pipeline, pydantic_class_type, pydantic_obj_id, has_links: bool = False):
    pydantic_list = await get_filtered_obj_list(filter_agg_pipeline, pydantic_class_type, pydantic_obj_id, has_links)
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
                        agg_pipeline[0]["$match"] = {match_variable_name: match_variable_value}
                    else:
                        match_pipeline[match_variable_name] = match_variable_value
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
