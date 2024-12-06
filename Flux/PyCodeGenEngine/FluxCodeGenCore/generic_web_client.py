# standard imports
import os

import msgspec
import requests
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
from FluxPythonUtils.scripts.utility_functions import (
    log_n_except, http_response_as_class_type, HTTPRequestType, ClientError)


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
def generic_http_get_all_client(url: str, pydantic_type, limit_obj_count: int | None = None):
    params = None
    if limit_obj_count:
        params = {"limit_obj_count": limit_obj_count}
    response: requests.Response = requests.get(url, timeout=120, params=params)     # TIMEOUT for get-all set to 60 sec
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.GET)


@log_n_except
def generic_http_post_client(url: str, pydantic_obj, pydantic_type, return_copy_obj: bool | None = True):
    # When used for routes
    if pydantic_obj is not None:
        # create don't need to delete any field: model default should handle that,
        # so: exclude_unset=True, exclude_none=True
        json_data = generic_encoder(pydantic_obj, pydantic_type.enc_hook, by_alias=True, exclude_none=True)

    # When used for queries like get last date query, as there is no pydantic obj in case of query
    else:
        json_data = None
    response: requests.Response = requests.post(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 201, pydantic_type, HTTPRequestType.POST)


@log_n_except
def generic_http_file_query_client(url: str, file_path: str | PurePath, query_params_dict: Dict[str, Any],
                                   pydantic_type):
    # When used for routes
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            files = {"upload_file": (str(file_path), file, "multipart/form-data")}
            response: requests.Response = requests.post(url, files=files, params=query_params_dict)
            return http_response_as_class_type(url, response, 201, pydantic_type, HTTPRequestType.POST)
    else:
        raise ClientError(f"Can't find file path: {file_path}")


@log_n_except
def generic_http_post_all_client(url: str, pydantic_obj_list, pydantic_type, return_copy_obj: bool | None = True):
    # When used for routes
    if pydantic_obj_list is not None:
        json_data = generic_encoder(pydantic_obj_list, pydantic_type.enc_hook, by_alias=True, exclude_none=True)

    # When used for queries like get last date query, as there is no pydantic obj in case of query
    else:
        json_data = None
    response: requests.Response = requests.post(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 201, pydantic_type, HTTPRequestType.POST)


@log_n_except
def generic_http_get_client(url: str, query_param: Any, pydantic_type):
    # When used for routes
    if query_param is not None:
        if url.endswith("/"):
            url = f"{url}{query_param}"
        else:
            url = f"{url}/{query_param}"

    # else not required: When used for queries, like get last date query, there is no query_param in case of query
    response: requests.Response = requests.get(url)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.GET)


@log_n_except
def generic_http_put_client(url: str, pydantic_obj, pydantic_type, return_copy_obj: bool | None = True):
    if pydantic_obj is not None:
        # When used for routes
        json_data = generic_encoder(pydantic_obj, pydantic_type.enc_hook, by_alias=True)
    else:
        # When used for queries like get last date query, as there is no pydantic obj in case of query
        json_data = None
    response: requests.Response = requests.put(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PUT)


@log_n_except
def generic_http_put_all_client(url: str, pydantic_obj_list, pydantic_type, return_copy_obj: bool | None = True):
    if pydantic_obj_list is not None:
        # When used for routes
        json_data = generic_encoder(pydantic_obj_list, pydantic_type.enc_hook, by_alias=True)
    else:
        # When used for queries like get last date query, as there is no pydantic obj in case of query
        json_data = None
    response: requests.Response = requests.put(url, json=json_data, params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PUT)


@log_n_except
def generic_http_patch_client(url: str, pydantic_obj_json, pydantic_type, return_copy_obj: bool | None = True):
    pydantic_obj_json = generic_encoder(pydantic_obj_json, pydantic_type.enc_hook, by_alias=True)
    response: requests.Response = requests.patch(url, json=pydantic_obj_json,
                                                 params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PATCH)


@log_n_except
def generic_http_patch_all_client(url: str, pydantic_obj_json_list, pydantic_type, return_copy_obj: bool | None = True):
    pydantic_obj_json_list = generic_encoder(pydantic_obj_json_list, pydantic_type.enc_hook, by_alias=True)
    response: requests.Response = requests.patch(url, json=pydantic_obj_json_list,
                                                 params={"return_obj_copy": return_copy_obj})
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PATCH)


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
    response_json = response.json()
    return response_json


@log_n_except
def generic_http_delete_all_client(url: str, return_copy_obj: bool | None = True):
    response: requests.Response = requests.delete(url, params={"return_obj_copy": return_copy_obj})
    response_json = response.json()
    return response_json


async def generic_ws_get_all_client(url: str, pydantic_type, user_callback: Callable, query_args: Dict | None = None):

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
                pydantic_obj_list: List[pydantic_type] = pydantic_type.from_dict_list(data)
                user_callback(pydantic_obj_list)
                data = None
                try:
                    for pydantic_obj in pydantic_obj_list:
                        # print(pydantic_obj)
                        logging.debug(pydantic_obj)
                except KeyError:
                    continue


async def generic_ws_get_client(url: str, query_param: Any, pydantic_type, user_callback: Callable):
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
                pydantic_type_obj = pydantic_type(**data)
                user_callback(pydantic_type_obj)
                data = None
                try:
                    # print('\n', "Update: ", pydantic_type_obj)
                    logging.debug(f"Update: {pydantic_type_obj}")
                except KeyError:
                    continue

@log_n_except
def generic_http_index_client(url: str, query_params: List[Any], pydantic_type):
    query_params = "/".join(query_params)
    if url.endswith("/"):
        url = f"{url}{query_params}"
    else:
        url = f"{url}/{query_params}"
    response: requests.Response = requests.get(url)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.GET)


@log_n_except
def generic_http_get_query_client(url: str, query_params_dict: Dict[str, Any], pydantic_type):
    response: requests.Response = requests.get(url, params=query_params_dict)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.GET)


@log_n_except
def generic_http_patch_query_client(url: str, query_payload_dict: Dict[str, Any], pydantic_type):
    response: requests.Response = requests.patch(url, json=query_payload_dict)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PATCH)


@log_n_except
def generic_http_post_query_client(url: str, query_payload_dict: Dict[str, Any], pydantic_type):
    response: requests.Response = requests.post(url, json=query_payload_dict)
    return http_response_as_class_type(url, response, 201, pydantic_type, HTTPRequestType.POST)
