# standard imports
import os

import msgspec
from typing import Any, Callable, List, Dict
from pathlib import PurePath
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, ConnectionClosed
import asyncio
from asyncio.exceptions import TimeoutError
import json
import urllib.parse

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.httpx_client import default_httpx_client as requests
from FluxPythonUtils.scripts.utility_functions import (
    log_n_except, http_response_as_class_type, HTTPRequestType, ClientError, http_response_as_json)

if (model_type := os.getenv("ModelType")) is None or len(model_type) == 0:
    err_str = f"env var ModelType must not be {model_type}"
    logging.exception(err_str)
    raise Exception(err_str)
else:
    if model_type.lower() == "beanie":
        from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_beanie_routes import generic_encoder
    elif model_type.lower() == "msgspec":
        from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_msgspec_routes import generic_encoder
    elif model_type.lower() == "dataclass":
        from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_dataclass_routes import generic_encoder
    else:
        err_str = f"env var ModelType not supported {model_type=}"
        logging.exception(err_str)
        raise Exception(err_str)

@log_n_except
def generic_http_get_all_client(url: str, model_type, limit_obj_count: int | None = None):
    params = None
    if limit_obj_count:
        params = {"limit_obj_count": limit_obj_count}
    response: requests.Response = requests.get(url, timeout=120, params=params)  # TIMEOUT for get-all set to 60 sec
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.GET)


@log_n_except
def generic_http_post_client(url: str, model_obj, model_type,
                             return_copy_obj: bool | None = True):
    # When used for routes
    if model_obj is not None:
        # create don't need to delete any field: model default should handle that,
        # so: exclude_unset=True, exclude_none=True
        json_data = generic_encoder(model_obj, model_type.enc_hook, by_alias=True, exclude_none=True)

    # When used for queries like get last date query, as there is no model obj in case of query
    else:
        json_data = None
    response: requests.Response = requests.post(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 201, model_type, HTTPRequestType.POST)


@log_n_except
def generic_http_file_query_client(url: str, file_path: str | PurePath, query_params_dict: Dict[str, Any],
                                   model_type):
    # When used for routes
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            files = {"upload_file": (str(file_path), file, "multipart/form-data")}
            response: requests.Response = requests.post(url, files=files, params=query_params_dict)
            return http_response_as_class_type(url, response, 201, model_type, HTTPRequestType.POST)
    else:
        raise ClientError(f"Can't find file path: {file_path}")


@log_n_except
def generic_http_post_all_client(url: str, model_obj_list, model_type,
                                 return_copy_obj: bool | None = True):
    # When used for routes
    if model_obj_list is not None:
        json_data = generic_encoder(model_obj_list, model_type.enc_hook, by_alias=True, exclude_none=True)

    # When used for queries like get last date query, as there is no model obj in case of query
    else:
        json_data = None
    response: requests.Response = requests.post(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 201, model_type, HTTPRequestType.POST)


@log_n_except
def generic_http_get_client(url: str, query_param: Any, model_type):
    # When used for routes
    if query_param is not None:
        if url.endswith("/"):
            url = f"{url}{query_param}"
        else:
            url = f"{url}/{query_param}"

    # else not required: When used for queries, like get last date query, there is no query_param in case of query
    response: requests.Response = requests.get(url)
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.GET)


@log_n_except
def generic_http_put_client(url: str, model_obj, model_type,
                            return_copy_obj: bool | None = True):
    if model_obj is not None:
        # When used for routes
        json_data = generic_encoder(model_obj, model_type.enc_hook, by_alias=True)
    else:
        # When used for queries like get last date query, as there is no model obj in case of query
        json_data = None
    response: requests.Response = requests.put(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.PUT)


@log_n_except
def generic_http_put_all_client(url: str, model_obj_list, model_type,
                                return_copy_obj: bool | None = True):
    if model_obj_list is not None:
        # When used for routes
        json_data = generic_encoder(model_obj_list, model_type.enc_hook, by_alias=True)
    else:
        # When used for queries like get last date query, as there is no model obj in case of query
        json_data = None
    response: requests.Response = requests.put(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.PUT)


@log_n_except
def generic_http_patch_client(url: str, model_obj_json: Dict, model_type,
                              return_copy_obj: bool | None = True):
    model_obj_json = generic_encoder(model_obj_json, model_type.enc_hook, by_alias=True)
    response: requests.Response = requests.patch(url, json=model_obj_json,
                                                 params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.PATCH)


@log_n_except
def generic_http_patch_all_client(url: str, model_obj_json_list: List[Dict], model_type,
                                  return_copy_obj: bool | None = True):
    model_obj_json_list = generic_encoder(model_obj_json_list, model_type.enc_hook, by_alias=True)
    response: requests.Response = requests.patch(url, json=model_obj_json_list,
                                                 params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.PATCH)


@log_n_except
def generic_http_delete_client(url: str, query_param: Any, return_copy_obj: bool | None = True):
    # When used for routes
    if query_param is not None:
        if url.endswith("/"):
            url = f"{url}{query_param}"
        else:
            url = f"{url}/{query_param}"
    # else not required: When used for queries like get last date query, as there is no query_param in case of query
    response: requests.Response = requests.delete(url, params={"return_obj_copy": return_copy_obj})
    expected_status_code = 200
    return http_response_as_json(url, response, expected_status_code, HTTPRequestType.DELETE)


@log_n_except
def generic_http_delete_by_id_list_client(url: str, delete_id_list: List[Any], model_type,
                                          return_copy_obj: bool | None = True):
    delete_id_list_json = generic_encoder(delete_id_list, model_type.enc_hook, by_alias=True)
    response: requests.Response = requests.delete(url, json=delete_id_list_json,
                                                  params={"return_obj_copy": return_copy_obj})
    expected_status_code = 200
    return http_response_as_json(url, response, expected_status_code, HTTPRequestType.DELETE)


@log_n_except
def generic_http_delete_all_client(url: str, return_copy_obj: bool | None = True):
    response: requests.Response = requests.delete(url, params={"return_obj_copy": return_copy_obj})
    expected_status_code = 200
    return http_response_as_json(url, response, expected_status_code, HTTPRequestType.DELETE)


async def generic_ws_get_all_client(url: str, model_type,
                                    user_callback: Callable, query_args: Dict | None = None):

    if query_args:
        url = url + "?" + urllib.parse.urlencode(query_args)

    async with websockets.connect(url, ping_timeout=None) as ws:
        while True:
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=10.0)
            except TimeoutError:
                logging.debug('timeout!')
                continue
            except ConnectionClosedOK as e:
                logging.info(f"web socket connection closed gracefully within while loop: {e}")
                break
            except ConnectionClosedError as e:
                logging.exception(f"web socket connection closed with error within while loop: {e}")
                break
            except ConnectionClosed as e:
                logging.exception('\n', f"web socket connection closed within while loop: {e}")
                break
            except RuntimeError as e:
                logging.exception(f"web socket raised runtime error within while loop: {e}")
                break
            except Exception as e:
                logging.exception(f"web socket raised runtime error within while loop: {e}")
                break
            if data is not None:
                data = json.loads(data)
                model_obj_list: List[model_type] = model_type.from_dict_list(data)
                user_callback(model_obj_list)
                data = None
                try:
                    for model_obj in model_obj_list:
                        logging.debug(model_obj)
                except KeyError:
                    continue


async def generic_ws_get_client(url: str, query_param: Any, model_type,
                                user_callback: Callable):
    if query_param is not None:
        if url.endswith("/"):
            url = f"{url}{query_param}"
        else:
            url = f"{url}/{query_param}"
    # else not required: if param not required then using url as is

    async with websockets.connect(url, ping_timeout=None) as ws:
        while True:
            data = None
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=10.0)
            except TimeoutError:
                logging.debug('timeout!')
                continue
            except ConnectionClosedOK as e:
                logging.info(f"web socket connection closed gracefully within while loop: {e}")
                break
            except ConnectionClosedError as e:
                logging.exception(f"web socket connection closed with error within while loop: {e}")
                break
            except ConnectionClosed as e:
                logging.exception('\n', f"web socket connection closed within while loop: {e}")
                break
            except RuntimeError as e:
                logging.exception(f"web socket raised runtime error within while loop: {e}")
                break
            except Exception as e:
                logging.exception(f"web socket raised runtime error within while loop: {e}")
                break
            if data is not None:
                data = json.loads(data)
                model_type_obj = model_type(**data)
                user_callback(model_type_obj)
                data = None
                try:
                    logging.debug(f"Update: {model_type_obj}")
                except KeyError:
                    continue

@log_n_except
def generic_http_index_client(url: str, query_params: List[Any], model_type):
    query_params = "/".join(query_params)
    if url.endswith("/"):
        url = f"{url}{query_params}"
    else:
        url = f"{url}/{query_params}"
    response: requests.Response = requests.get(url)
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.GET)


@log_n_except
def generic_http_get_query_client(url: str, query_params_dict: Dict[str, Any], model_type):
    response: requests.Response = requests.get(url, params=query_params_dict)
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.GET)


@log_n_except
def generic_http_patch_query_client(url: str, query_payload_dict: Dict[str, Any], model_type):
    response: requests.Response = requests.patch(url, json=query_payload_dict)
    return http_response_as_class_type(url, response, 200, model_type, HTTPRequestType.PATCH)


@log_n_except
def generic_http_post_query_client(url: str, query_payload_dict: Dict[str, Any], model_type):
    response: requests.Response = requests.post(url, json=query_payload_dict)
    return http_response_as_class_type(url, response, 201, model_type, HTTPRequestType.POST)
