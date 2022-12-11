import requests
from pydantic import BaseModel
from typing import Dict, Any, Callable
import logging
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, ConnectionClosed
import asyncio
from asyncio.exceptions import TimeoutError
import json


def log_n_except(original_function):
    def wrapper_function(*args, **kwargs):
        try:
            result = original_function(*args, **kwargs)
            return result
        except Exception as e:
            err_str = f"Client Error Occurred: {e}"
            logging.exception(err_str)
            raise Exception(err_str)
    return wrapper_function


@log_n_except
def generic_http_get_all_client(url: str, pydantic_type):
    result = requests.get(url)
    result_json = result.json()
    for json_obj in result_json:
        try:
            json_obj["id"] = json_obj["_id"]
            del json_obj["_id"]
        except KeyError as e:
            err_str = f"Key _id not found in received response body: {result_json}, url: {url}, error: {e}"
            logging.exception(err_str)
            raise Exception(err_str)
    pydantic_obj_list = [pydantic_type(**json_obj) for json_obj in result_json]
    return pydantic_obj_list


@log_n_except
def generic_http_post_client(url: str, json_response: Dict, pydantic_type):
    result = requests.post(url, json=json_response)
    result_json = result.json()
    try:
        result_json["id"] = result_json["_id"]
        del result_json["_id"]
    except KeyError as e:
        err_str = f"Key _id not found in received response body: {result_json}, url: {url}, error: {e}"
        logging.exception(err_str)
        raise Exception(err_str)
    return pydantic_type(**result_json)


@log_n_except
def generic_http_get_client(url: str, query_param: Any, pydantic_type):
    if url.endswith("/"):
        url = f"{url}{query_param}"
    else:
        url = f"{url}/{query_param}"
    result = requests.get(url)
    result_json = result.json()
    try:
        result_json["id"] = result_json["_id"]
        del result_json["_id"]
    except KeyError as e:
        err_str = f"Key _id not found in received response body: {result_json}, url: {url}, error: {e}"
        logging.exception(err_str)
        raise Exception(err_str)
    return pydantic_type(**result_json)


@log_n_except
def generic_http_put_client(url: str, json_response: Dict, pydantic_type):
    result = requests.put(url, json=json_response)
    result_json = result.json()
    try:
        result_json["id"] = result_json["_id"]
        del result_json["_id"]
    except KeyError as e:
        err_str = f"Key _id not found in received response body: {result_json}, url: {url}, error: {e}"
        logging.exception(err_str)
        raise Exception(err_str)
    return pydantic_type(**result_json)


@log_n_except
def generic_http_patch_client(url: str, json_response: Dict, pydantic_type):
    result = requests.patch(url, json=json_response)
    result_json = result.json()
    try:
        result_json["id"] = result_json["_id"]
        del result_json["_id"]
    except KeyError as e:
        err_str = f"Key _id not found in received response body: {result_json}, url: {url}, error: {e}"
        logging.exception(err_str)
        raise Exception(err_str)
    return pydantic_type(**result_json)


@log_n_except
def generic_http_delete_client(url: str, query_param: Any):
    if url.endswith("/"):
        url = f"{url}{query_param}"
    else:
        url = f"{url}/{query_param}"
    result = requests.delete(url)
    result_json = result.json()
    return result_json


async def generic_ws_get_client(url: str, query_param: Any, pydantic_type, user_callback: Callable):
    if url.endswith("/"):
        url = f"{url}{query_param}"
    else:
        url = f"{url}/{query_param}"
    async with websockets.connect(url, ping_timeout=None) as ws:
        while True:
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=10.0)
                user_callback(data)
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
                data = None
                try:
                    print('\n', "Update: ", pydantic_type_obj)
                except KeyError:
                    continue


# class OrderLimitsOptional(BaseModel):
#     """
#         Widget - 5
#     """
#     id: int
#     max_price_levels: int
#     max_basis_points: int
#     max_cb_order_notional: int
#     max_px_deviation: float


# js = {'id': 1, 'max_price_levels': 40, 'max_basis_points': 0, 'max_cb_order_notional': 1, 'max_px_deviation': 0.0}
# print(OrderLimitsOptional(**js).json())

# Get All
# URL = "http://127.0.0.1:8000/pair_strat_engine/get-all-order_limits/"
# print(generic_http_get_all_client(URL, OrderLimitsOptional))


# Post
# js = {'id': 3, 'max_price_levels': 40, 'max_basis_points': 0, 'max_cb_order_notional': 1, 'max_px_deviation': 0.0}
# URL = "http://127.0.0.1:8000/pair_strat_engine/create-order_limits"
# print(generic_http_post_client(URL, js, OrderLimitsOptional))


# Get
# URL = "http://127.0.0.1:8000/pair_strat_engine/get-order_limits"
# print(generic_http_get_client(URL, 1, OrderLimitsOptional))


# Put
# js = {'id': 1, 'max_price_levels': 10, 'max_basis_points': 0, 'max_cb_order_notional': 1, 'max_px_deviation': 0.0}
# URL = "http://127.0.0.1:8000/pair_strat_engine/put-order_limits/"
# print(generic_http_put_client(URL, js, OrderLimitsOptional))

# Patch
# js = {'id': 2, 'max_price_levels': 10}
# URL = "http://127.0.0.1:8000/pair_strat_engine/patch-order_limits/"
# print(generic_http_patch_client(URL, js, OrderLimitsOptional))

# Delete
# URL = "http://127.0.0.1:8000/pair_strat_engine/delete-order_limits/"
# print(generic_http_delete_client(URL, 3, OrderLimitsOptional))

# Get -ws
# URL = "ws://127.0.0.1:8000/pair_strat_engine/get-order_limits-ws"
# try:
#     new_loop = asyncio.new_event_loop()
#     test = "testing"
#     new_loop.run_until_complete(generic_ws_get_client(URL, 1, OrderLimitsOptional))
# except KeyboardInterrupt:
#     pass
# finally:
#     asyncio.get_event_loop().stop()
