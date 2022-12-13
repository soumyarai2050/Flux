import logging
from fastapi import HTTPException, WebSocketDisconnect, WebSocket
import json
import sys
from pathlib import PurePath
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
repo_dir = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(repo_dir))
from FluxPythonUtils.FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error

id_not_found = DefaultWebResponse(msg="Id not Found")
del_success = DefaultWebResponse(msg="Deletion Successful")


@http_except_n_log_error(status_code=500)
def generic_cache_get_all(basemodel):
    basemodel_list = list(basemodel.get_all_cached_obj().values())
    return basemodel_list


@http_except_n_log_error(status_code=500)
def generic_cache_post(basemodel, basemodel_obj):
    basemodel.add_data_in_cache(basemodel_obj.id, basemodel_obj)
    return basemodel.get_data_from_cache(basemodel_obj.id)


@http_except_n_log_error(status_code=500)
def generic_cache_get(basemodel, basemodel_obj_id):
    basemodel_obj_fetched = basemodel.get_data_from_cache(basemodel_obj_id)
    if basemodel_obj_fetched is None:
        logging.exception(id_not_found.format_msg(basemodel.__name__, basemodel_obj_id))
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(basemodel.__name__, basemodel_obj_id))
    else:
        return basemodel_obj_fetched


def _underlying_beanie_patch_n_put(basemodel, basemodel_obj, is_put: bool = True):
    if is_put:
        success = basemodel.replace_data_in_cache(basemodel_obj.id, basemodel_obj)
    else:
        success = basemodel.patch_data_in_cache(basemodel_obj.id, basemodel_obj)
    if not success:
        logging.exception(id_not_found.format_msg(basemodel.__name__, basemodel_obj.id))
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(basemodel.__name__, basemodel_obj.id))
    else:
        return basemodel.get_data_from_cache(basemodel_obj.id)


@http_except_n_log_error(status_code=500)
def generic_cache_put(basemodel, basemodel_obj):
    return _underlying_beanie_patch_n_put(basemodel, basemodel_obj)


@http_except_n_log_error(status_code=500)
def generic_cache_patch(basemodel, basemodel_obj):
    return _underlying_beanie_patch_n_put(basemodel, basemodel_obj, False)


@http_except_n_log_error(status_code=500)
def generic_cache_delete(basemodel, basemodel_obj_id):
    delete_success = basemodel.delete_data_in_cache(basemodel_obj_id)
    if not delete_success:
        logging.exception(id_not_found.format_msg(basemodel.__name__, basemodel_obj_id))
        raise HTTPException(status_code=404, detail=id_not_found.format_msg(basemodel.__name__, basemodel_obj_id))
    else:
        del_success.id = basemodel_obj_id
        return del_success


@http_except_n_log_error(status_code=500)
def generic_cache_index(basemodel, basemodel_field_name: str, index_value):
    fetched_ui_layout_list = []
    basemodel_dict = basemodel.get_all_cached_obj()
    for fetched_basemodel in basemodel_dict.values():
        if fetched_basemodel.dict()[basemodel_field_name] == index_value:
            fetched_ui_layout_list.append(fetched_basemodel)
    return fetched_ui_layout_list


@http_except_n_log_error(status_code=500)
async def generic_cache_get_ws(websocket: WebSocket, Basemodel, obj_id):
    await Basemodel.connection_manager().connect(websocket, obj_id)  # prevent duplicate addition
    try:
        fetched_basemodel_obj = await Basemodel.get_data_from_cache(obj_id)
        if not fetched_basemodel_obj:
            raise HTTPException(status_code=404, detail=id_not_found.format_msg(Basemodel.__name__, obj_id))
        else:
            # model_obj.json() returns string converted json
            fetched_basemodel_obj_json = json.loads(fetched_basemodel_obj.json())
            await Basemodel.connection_manager().send_json_to_websocket(fetched_basemodel_obj_json, websocket)
        await websocket.receive()
    except WebSocketDisconnect as e:
        logging.exception(f"generic_beanie_get_ws - unexpected connection close: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        Basemodel.connection_manager().disconnect(websocket, obj_id)
