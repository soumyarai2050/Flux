import json
from fastapi.encoders import jsonable_encoder
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error


id_not_found = DefaultWebResponse(msg="Id not Found")
del_success = DefaultWebResponse(msg="Deletion Successful")


@http_except_n_log_error(status_code=500)
async def generic_post_http(pydantic_class_type, pydantic_obj):
    new_pydantic_obj: pydantic_class_type = await pydantic_obj.create()
    if pydantic_class_type.read_ws_path_ws_connection_manager is not None:
        json_data = jsonable_encoder(new_pydantic_obj, by_alias=True, exclude_unset=True, exclude_none=True)
        json_str = json.dumps(json_data)
        await pydantic_class_type.read_ws_path_ws_connection_manager.broadcast(json_str)
    return pydantic_obj


async def _underlying_patch_n_put(pydantic_class_type, pydantic_obj_updated, request_obj):
    stored_obj = await pydantic_class_type.get(pydantic_obj_updated.id)
    if stored_obj is None:
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__,
                                                                            pydantic_obj_updated.id))
    else:
        await stored_obj.update(request_obj)

        if pydantic_class_type.read_ws_path_ws_connection_manager is not None:
            json_data = jsonable_encoder(stored_obj, by_alias=True, exclude_unset=True, exclude_none=True)
            json_str = json.dumps(json_data)
            await pydantic_class_type.read_ws_path_ws_connection_manager.broadcast(json_str)
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.broadcast(json_str, pydantic_obj_updated.id)
        return stored_obj


@http_except_n_log_error(status_code=500)
async def generic_put_http(pydantic_class_type, pydantic_obj_updated):
    request_obj = {'$set': pydantic_obj_updated.dict().items()}
    return await _underlying_patch_n_put(pydantic_class_type, pydantic_obj_updated, request_obj)


@http_except_n_log_error(status_code=500)
async def generic_patch_http(pydantic_class_type, pydantic_obj_updated):
    req_dict_without_none_val = {k: v for k, v in
                                 pydantic_obj_updated.dict(exclude_unset=True, exclude_none=True).items()}
    request_obj = {'$set': req_dict_without_none_val.items()}
    return await _underlying_patch_n_put(pydantic_class_type, pydantic_obj_updated, request_obj)


@http_except_n_log_error(status_code=500)
async def generic_delete_http(pydantic_class_type, pydantic_dummy_model, pydantic_obj_id):
    stored_obj = await pydantic_class_type.get(pydantic_obj_id)
    if not stored_obj:
        logging.exception(id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
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
async def generic_read_http(pydantic_class_type):
    pydantic_list = await pydantic_class_type.find_all().to_list()
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


@http_except_n_log_error(status_code=500)
async def generic_read_ws(ws: WebSocket, pydantic_class_type):
    is_new_ws: bool = await pydantic_class_type.read_ws_path_ws_connection_manager.connect(ws)  # prevent duplicate addition
    need_disconnect = False
    try:
        pydantic_list = await pydantic_class_type.find_all().to_list()
        fetched_pydantic_list_json = jsonable_encoder(pydantic_list, by_alias=True)
        fetched_pydantic_list_json_str = json.dumps(fetched_pydantic_list_json)
        await pydantic_class_type.read_ws_path_ws_connection_manager.send_json_to_websocket(fetched_pydantic_list_json_str, ws)
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully within while loop: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: eb socket connection closed with error within while loop: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            pydantic_class_type.read_ws_path_ws_connection_manager.disconnect(ws)


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_http(pydantic_class_type, pydantic_obj_id):
    fetched_pydantic_obj = await pydantic_class_type.get(pydantic_obj_id)
    if not fetched_pydantic_obj:
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__, pydantic_obj_id))
    else:
        return fetched_pydantic_obj


@http_except_n_log_error(status_code=500)
async def generic_read_by_id_ws(ws: WebSocket, pydantic_class_type, obj_id):
    # prevent duplicate addition
    is_new_ws: bool = await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.connect(ws, obj_id)
    need_disconnect: bool = False
    try:
        fetched_pydantic_obj = await pydantic_class_type.get(obj_id)
        if fetched_pydantic_obj is None:
            raise HTTPException(status_code=404, detail=id_not_found.format_msg(pydantic_class_type.__name__, obj_id))
        else:
            fetched_pydantic_obj_json = jsonable_encoder(fetched_pydantic_obj, by_alias=True)
            fetched_pydantic_obj_json_str = json.dumps(fetched_pydantic_obj_json)
            await pydantic_class_type.read_ws_path_with_id_ws_connection_manager.send_json_to_websocket(fetched_pydantic_obj_json_str, ws)
        need_disconnect = await handle_ws(ws, is_new_ws)
    except WebSocketException as e:
        need_disconnect = True
        logging.info(f"WebSocketException: {e}")
    except ConnectionClosedOK as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedOK: web socket connection closed gracefully within while loop: {e}")
    except ConnectionClosedError as e:
        need_disconnect = True
        logging.info(f"ConnectionClosedError: eb socket connection closed with error within while loop: {e}")
    except websockets.ConnectionClosed as e:
        need_disconnect = True
        logging.info(f"generic_beanie_get_ws - connection closed by client: {e}")
    except WebSocketDisconnect as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        need_disconnect = True
        logging.info(f"RuntimeError: web socket raised runtime error within while loop: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        need_disconnect = True
        logging.exception(f"generic_beanie_get_ws - unexpected connection close: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        if need_disconnect:
            pydantic_class_type.read_ws_path_with_id_ws_connection_manager.disconnect(ws, obj_id)

