import json
from fastapi.encoders import jsonable_encoder
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, WebSocketException
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
import sys
from pathlib import PurePath
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
repo_dir = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(repo_dir))
from FluxPythonUtils.FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error


id_not_found = DefaultWebResponse(msg="Id not Found")
del_success = DefaultWebResponse(msg="Deletion Successful")


@http_except_n_log_error(status_code=500)
async def generic_beanie_post_http(Document, document_obj):
    new_document_obj: Document = await document_obj.create()
    if Document.read_ws_path_ws_connection_manager is not None:
        json_data = jsonable_encoder(new_document_obj, by_alias=True, exclude_unset=True, exclude_none=True)
        json_str = json.dumps(json_data)
        await Document.read_ws_path_ws_connection_manager.broadcast(json_str)
    return document_obj


async def _underlying_beanie_patch_n_put(Document, document_obj_updated, request_obj):
    stored_obj = await Document.get(document_obj_updated.id)
    if stored_obj is None:
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(Document.__name__,
                                                                            document_obj_updated.id))
    else:
        await stored_obj.update(request_obj)

        if Document.read_ws_path_ws_connection_manager is not None:
            json_data = jsonable_encoder(stored_obj, by_alias=True, exclude_unset=True, exclude_none=True)
            json_str = json.dumps(json_data)
            await Document.read_ws_path_ws_connection_manager.broadcast(json_str)
            await Document.read_ws_path_with_id_ws_connection_manager.broadcast(json_str, document_obj_updated.id)
        return stored_obj


@http_except_n_log_error(status_code=500)
async def generic_beanie_put_http(Document, document_obj_updated):
    request_obj = {'$set': document_obj_updated.dict().items()}
    return await _underlying_beanie_patch_n_put(Document, document_obj_updated, request_obj)


@http_except_n_log_error(status_code=500)
async def generic_beanie_patch_http(Document, document_obj_updated):
    req_dict_without_none_val = {k: v for k, v in
                                 document_obj_updated.dict(exclude_unset=True, exclude_none=True).items()}
    request_obj = {'$set': req_dict_without_none_val.items()}
    return await _underlying_beanie_patch_n_put(Document, document_obj_updated, request_obj)


@http_except_n_log_error(status_code=500)
async def generic_beanie_delete_http(Document, DocumentBaseModel, document_obj_id):
    stored_obj = await Document.get(document_obj_id)
    if not stored_obj:
        logging.exception(id_not_found.format_msg(Document.__name__, document_obj_id))
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(Document.__name__, document_obj_id))
    else:
        await stored_obj.delete()
        try:
            document_base_model: DocumentBaseModel = DocumentBaseModel(_id=stored_obj.id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
        if Document.read_ws_path_ws_connection_manager is not None:
            json_data = jsonable_encoder(document_base_model, by_alias=True, exclude_unset=True, exclude_none=True)
            json_str = json.dumps(json_data)
            await Document.read_ws_path_ws_connection_manager.broadcast(json_str)
            await Document.read_ws_path_with_id_ws_connection_manager.broadcast(json_str, stored_obj.id)
        del_success.id = document_obj_id
        return del_success


@http_except_n_log_error(status_code=500)
async def generic_beanie_index_http(Document, ref_value, index_value):
    try:
        fetched_ui_layout_list = await Document.find(ref_value == index_value).to_list()
        return fetched_ui_layout_list
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=404, detail=str(e))


@http_except_n_log_error(status_code=500)
async def generic_beanie_read_http(Document):
    document_list = await Document.find_all().to_list()
    return document_list


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
async def generic_beanie_read_ws(ws: WebSocket, Document):
    is_new_ws: bool = await Document.read_ws_path_ws_connection_manager.connect(ws)  # prevent duplicate addition
    need_disconnect = False
    try:
        document_list = await Document.find_all().to_list()
        fetched_document_list_json = jsonable_encoder(document_list, by_alias=True)
        fetched_document_list_json_str = json.dumps(fetched_document_list_json)
        await Document.read_ws_path_ws_connection_manager.send_json_to_websocket(fetched_document_list_json_str, ws)
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
            Document.read_ws_path_ws_connection_manager.disconnect(ws)


@http_except_n_log_error(status_code=500)
async def generic_beanie_read_by_id_http(Document, document_obj_id):
    fetched_document_obj = await Document.get(document_obj_id)
    if not fetched_document_obj:
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(Document.__name__, document_obj_id))
    else:
        return fetched_document_obj


@http_except_n_log_error(status_code=500)
async def generic_beanie_read_by_id_ws(ws: WebSocket, Document, obj_id):
    # prevent duplicate addition
    is_new_ws: bool = await Document.read_ws_path_with_id_ws_connection_manager.connect(ws, obj_id)
    need_disconnect: bool = False
    try:
        fetched_document_obj = await Document.get(obj_id)
        if fetched_document_obj is None:
            raise HTTPException(status_code=404, detail=id_not_found.format_msg(Document.__name__, obj_id))
        else:
            fetched_document_obj_json = jsonable_encoder(fetched_document_obj, by_alias=True)
            fetched_document_obj_json_str = json.dumps(fetched_document_obj_json)
            await Document.read_ws_path_with_id_ws_connection_manager.send_json_to_websocket(fetched_document_obj_json_str, ws)
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
            Document.read_ws_path_with_id_ws_connection_manager.disconnect(ws, obj_id)

