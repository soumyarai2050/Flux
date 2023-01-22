# system imports
import json
import os
from typing import List, Any, Tuple
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException
# other package imports
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
# project specific imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case

id_not_found = DefaultWebResponse(msg="Id not Found")
del_success = DefaultWebResponse(msg="Deletion Successful")
host_env_var = "127.0.0.1" if (env_host := os.getenv("HOST")) is None else env_host
port_env_var = 8000 if (env_port := os.getenv("PORT")) is None else int(env_port)


@http_except_n_log_error(status_code=500)
async def generic_post_http(pydantic_class_type, pydantic_obj):
    new_pydantic_obj: pydantic_class_type = await pydantic_obj.create()
    if pydantic_class_type.read_ws_path_ws_connection_manager is not None:
        json_data = jsonable_encoder(new_pydantic_obj, by_alias=True, exclude_unset=True, exclude_none=True)
        json_str = json.dumps(json_data)
        await pydantic_class_type.read_ws_path_ws_connection_manager.broadcast(json_str)
    return pydantic_obj


async def _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj, pydantic_obj_updated, request_obj,
                                  filter_var_val_list: List[Tuple] | None = None):
    await stored_pydantic_obj.update(request_obj)
    stored_obj = await get_obj(pydantic_class_type, pydantic_obj_updated.id, filter_var_val_list)
    if pydantic_class_type.read_ws_path_ws_connection_manager is not None:
        json_data = jsonable_encoder(stored_obj, by_alias=True, exclude_unset=True, exclude_none=True)
        json_str = json.dumps(json_data)
        await pydantic_class_type.read_ws_path_ws_connection_manager.broadcast(json_str)
        await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.broadcast(json_str,
                                                                                       pydantic_obj_updated.id)
    return stored_obj


@http_except_n_log_error(status_code=500)
async def generic_put_http(pydantic_class_type, stored_pydantic_obj, pydantic_obj_updated,
                           filter_var_val_list: List[Tuple] | None = None):
    request_obj = {'$set': pydantic_obj_updated.dict().items()}
    return await _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj,
                                         pydantic_obj_updated, request_obj, filter_var_val_list)


@http_except_n_log_error(status_code=500)
async def generic_patch_http(pydantic_class_type, stored_pydantic_obj, pydantic_obj_updated,
                             filter_var_val_list: List[Tuple] | None = None):
    req_dict_without_none_val = {k: v for k, v in
                                 pydantic_obj_updated.dict(exclude_unset=True, exclude_none=True).items()}
    request_obj = {'$set': req_dict_without_none_val.items()}
    return await _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj,
                                         pydantic_obj_updated, request_obj, filter_var_val_list)


@http_except_n_log_error(status_code=500)
async def generic_delete_http(pydantic_class_type, pydantic_dummy_model, pydantic_obj_id):
    stored_obj = await pydantic_class_type.get(pydantic_obj_id)
    if not stored_obj:
        logging.exception(id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__,
                                                                            pydantic_obj_id))
    else:
        await stored_obj.delete()
        try:
            pydantic_base_model: pydantic_dummy_model = pydantic_dummy_model(id=stored_obj.id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
        if pydantic_class_type.read_ws_path_ws_connection_manager is not None:
            json_data = jsonable_encoder(pydantic_base_model, by_alias=True, exclude_unset=True, exclude_none=True)
            json_str = json.dumps(json_data)
            await pydantic_class_type.read_ws_path_ws_connection_manager.broadcast(json_str)
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.broadcast(json_str, stored_obj.id)
        del_success.id = pydantic_obj_id
        return del_success


@http_except_n_log_error(status_code=500)
async def generic_index_http(pydantic_class_type, ref_value, index_value):
    try:
        fetched_ui_layout_list = await pydantic_class_type.find(ref_value == index_value).to_list()
        return fetched_ui_layout_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@http_except_n_log_error(status_code=500)
async def generic_read_http(pydantic_class_type, filter_var_val_list: List[Tuple] | None = None):
    pydantic_list: List[pydantic_class_type]
    pydantic_list = await get_obj_list(pydantic_class_type, filter_var_val_list)
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
                          pydantic_class_type, filter_var_val_list: List[Tuple] | None = None):
    is_new_ws: bool = await pydantic_class_type.read_ws_path_ws_connection_manager.\
        connect(ws)  # prevent duplicate addition

    logging.debug(f"websocket client requested to connect: {ws.client}")
    logging.debug(f"connected to websocket: "
                  f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}")
    need_disconnect = False
    try:
        pydantic_list = await get_obj_list(pydantic_class_type, filter_var_val_list)
        fetched_pydantic_list_json = jsonable_encoder(pydantic_list, by_alias=True)
        fetched_pydantic_list_json_str = json.dumps(fetched_pydantic_list_json)
        await pydantic_class_type.read_ws_path_ws_connection_manager.\
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
            pydantic_class_type.read_ws_path_ws_connection_manager.disconnect(ws)
            logging.debug(f"Disconnected to websocket: "
                          f"{get_all_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type)}")


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_http(pydantic_class_type, pydantic_obj_id,
                                  filter_var_val_list: List[Tuple] | None = None):
    fetched_pydantic_obj: pydantic_class_type = await get_obj(pydantic_class_type, pydantic_obj_id, filter_var_val_list)
    if not fetched_pydantic_obj:
        raise HTTPException(status_code=404,
                            detail=id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
    else:
        return fetched_pydantic_obj


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_ws(ws: WebSocket, proto_package_name: str, pydantic_class_type, pydantic_obj_id,
                                filter_var_val_list: List[Tuple] | None = None):
    # prevent duplicate addition
    is_new_ws: bool = await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.connect(ws, pydantic_obj_id)

    logging.debug(f"websocket client requested to connect: {ws.client}")
    logging.debug(f"connected to websocket: "
                  f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}")
    need_disconnect: bool = False
    try:
        fetched_pydantic_obj: pydantic_class_type = await get_obj(pydantic_class_type, pydantic_obj_id,
                                                                  filter_var_val_list)
        if fetched_pydantic_obj is None:
            raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__,
                                                                                pydantic_obj_id))
        else:
            fetched_pydantic_obj_json = jsonable_encoder(fetched_pydantic_obj, by_alias=True)
            fetched_pydantic_obj_json_str = json.dumps(fetched_pydantic_obj_json)
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.\
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
            pydantic_class_type.read_ws_path_with_id_ws_connection_manager.disconnect(ws, pydantic_obj_id)
            logging.debug(f"Disconnected to websocket: "
                          f"{get_by_id_ws_url(host_env_var, port_env_var, proto_package_name, pydantic_class_type, pydantic_obj_id)}")


async def get_obj(pydantic_class_type, pydantic_obj_id, filter_var_val_list: List[Tuple] | None = None):
    fetched_pydantic_obj: pydantic_class_type
    if filter_var_val_list is None:
        fetched_pydantic_obj = await pydantic_class_type.get(pydantic_obj_id)
    else:
        fetched_pydantic_obj = await get_filtered_obj(filter_var_val_list, pydantic_class_type, pydantic_obj_id)
    return fetched_pydantic_obj


async def get_obj_list(pydantic_class_type, filter_var_val_list: List[Tuple] | None = None):
    pydantic_list: List[pydantic_class_type]
    try:
        if filter_var_val_list is None:
            pydantic_list = await pydantic_class_type.find_all().to_list()
        else:
            pydantic_list = await get_filtered_obj_list(filter_var_val_list, pydantic_class_type)
        return pydantic_list
    except ValidationError as e:
        logging.error(f"Pydantic validation error: {e}")
        raise e


async def get_filtered_obj_list(filter_var_val_list, pydantic_class_type, pydantic_obj_id=None):
    pydantic_obj_id_field: str | None = None
    if pydantic_obj_id is not None:
        pydantic_obj_id_field = "_id"
    data_filter = get_data_filter(filter_var_val_list, pydantic_obj_id_field, pydantic_obj_id)
    find_all_resp = pydantic_class_type.find_all()
    pydantic_list = await find_all_resp.aggregate(
        aggregation_pipeline=data_filter,
        projection_model=pydantic_class_type,
        session=None,
        ignore_cache=False
    ).to_list()
    return pydantic_list


async def get_filtered_obj(filter_tuple_list, pydantic_class_type, pydantic_obj_id):
    pydantic_list = await get_filtered_obj_list(filter_tuple_list, pydantic_class_type, pydantic_obj_id)
    return pydantic_list[0]


def get_data_filter(filter_tuple_list: list[Tuple], match_variable_name: str | None = None,
                    match_variable_value: Any = None):
    match_data_filter = \
        [{"$match": {}}]

    if match_variable_name is not None:
        updated_match_variable_name = match_variable_name
        if match_variable_value is not None:
            match_data_filter[0]["$match"] = {updated_match_variable_name: match_variable_value}
        else:
            raise Exception(f"Error: match_variable_name passed as: {match_variable_name}, while match_variable_value "
                            f"was passed None - not supported")
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
        match_data_filter.append(redact_data_filter)
    return match_data_filter
