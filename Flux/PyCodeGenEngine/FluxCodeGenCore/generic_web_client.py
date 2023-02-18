import requests
from pydantic import BaseModel
from typing import Any, Callable, List
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, ConnectionClosed
import asyncio
from asyncio.exceptions import TimeoutError
import json
from fastapi.encoders import jsonable_encoder

from FluxPythonUtils.scripts.utility_functions import log_n_except, http_response_as_class_type, HTTPRequestType


@log_n_except
def generic_http_get_all_client(url: str, pydantic_type):
    response: requests.Response = requests.get(url)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.GET)


@log_n_except
def generic_http_post_client(url: str, pydantic_obj, pydantic_type):
    # When used for routes
    if pydantic_obj is not None:
        # create don't need to delete any field: model default should handle that,
        # so: exclude_unset=True, exclude_none=True
        json_data = jsonable_encoder(pydantic_obj, by_alias=True, exclude_unset=True, exclude_none=True)

    # When used for queries like get last date query, as there is no pydantic obj in case of query
    else:
        json_data = None
    response: requests.Response = requests.post(url, json=json_data)
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
def generic_http_put_client(url: str, pydantic_obj, pydantic_type):
    if pydantic_obj is not None:
        # When used for routes
        json_data = jsonable_encoder(pydantic_obj, by_alias=True)
    else:
        # When used for queries like get last date query, as there is no pydantic obj in case of query
        json_data = None
    response: requests.Response = requests.put(url, json=json_data)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PUT)


@log_n_except
def generic_http_patch_client(url: str, pydantic_obj, pydantic_type):
    # When used for routes
    if pydantic_obj is not None:
        # When used for routes
        json_data = jsonable_encoder(pydantic_obj, by_alias=True, exclude_unset=True, exclude_none=True)
    else:
        # When used for queries like get last date query, as there is no pydantic obj in case of query
        json_data = None
    response: requests.Response = requests.patch(url, json=json_data)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.PATCH)


@log_n_except
def generic_http_delete_client(url: str, query_param: Any):
    # When used for routes
    if query_param is not None:
        if url.endswith("/"):
            url = f"{url}{query_param}"
        else:
            url = f"{url}/{query_param}"
    # else not required: When used for queries like get last date query, as there is no query_param in case of query
    response: requests.Response = requests.delete(url)
    response_json = response.json()
    return response_json


async def generic_ws_get_all_client(url: str, pydantic_type, user_callback: Callable):
    class PydanticClassTypeList(BaseModel):
        __root__: List[pydantic_type]

    async with websockets.connect(url, ping_timeout=None) as ws:
        while True:
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=10.0)
            except TimeoutError:
                logging.debug('timeout!')
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
                pydantic_obj_list: PydanticClassTypeList = PydanticClassTypeList(__root__=data)
                user_callback(pydantic_obj_list)
                data = None
                try:
                    for pydantic_obj in pydantic_obj_list.__root__:
                        print(pydantic_obj)
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
        data = None
        while True:
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=10.0)
            except TimeoutError:
                logging.debug('timeout!')
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
                    print('\n', "Update: ", pydantic_type_obj)
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
def generic_http_query_client(url: str, query_params: List[Any], pydantic_type):
    query_params = "/".join(query_params)
    if url.endswith("/"):
        url = f"{url}{query_params}"
    else:
        url = f"{url}/{query_params}"

    response: requests.Response = requests.get(url)
    return http_response_as_class_type(url, response, 200, pydantic_type, HTTPRequestType.GET)
