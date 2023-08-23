from typing import Dict, Set, List, Any, ClassVar, Tuple, Callable
from fastapi import WebSocket, WebSocketDisconnect
import logging
import asyncio
from pydantic import BaseModel

# Project imports
from FluxPythonUtils.scripts.async_rlock import AsyncRLock


class WSData(BaseModel):
    ws_object: WebSocket
    filter_callable: Callable[..., Any] | None = None
    filter_callable_kwargs: Dict[Any, Any] | None = None
    projection_model: BaseModel | None = None

    class Config:
        arbitrary_types_allowed = True


class WSConnectionManager:
    """
    ws - WebSocket
    Solves 2 purposes:
    1. Avoid duplicate ws accepts and enable reuse of accepted ws across web-paths
    2. Allows web-path specific ws collection {with or without ID} to enable web-path specific broadcast
    """
    _master_ws_set: ClassVar[Set[WebSocket]] = set()
    _master_ws_set_rlock: ClassVar[AsyncRLock] = AsyncRLock()  # str may be called while holding the lock by same thread

    def __init__(self):
        self.rlock: AsyncRLock = AsyncRLock()  # subclass str may be called while holding the lock by same thread

    def __str__(self):
        ret_str = "_master_ws_set: "
        with WSConnectionManager._master_ws_set_rlock:
            for ws in WSConnectionManager._master_ws_set:
                ret_str += str(ws)
            return ret_str

    @classmethod
    async def add_to_master_ws_set(cls, ws: WebSocket) -> bool:
        """
        return True if this is a new websocket,
        return False if this os an existing websocket - may have been added for a different web-path request
        """
        async with cls._master_ws_set_rlock:
            if ws not in cls._master_ws_set:
                await ws.accept()  # throws exception if ws is in disconnected state
                cls._master_ws_set.add(ws)
                return True
            else:
                return False

    @classmethod
    async def remove_from_master_ws_set(cls, ws: WebSocket) -> bool:
        async with cls._master_ws_set_rlock:
            if ws in cls._master_ws_set:
                cls._master_ws_set.remove(ws)
                return True
            else:
                # must have been removed by other web-path cache holders upon discovering a disconnect
                return False

    @staticmethod
    async def send_json_to_websocket(json_str, websocket: WebSocket):
        await websocket.send_text(json_str)

    @classmethod
    async def add_ws_to_filter_dict(cls):
        pass

    def verify_n_cast_callable_kwargs(self, callable_kwargs: Dict[Any, Any]):
        for key, val in callable_kwargs.items():
            if isinstance(val, list):
                callable_kwargs[key] = tuple(val)

        callable_kwargs = tuple(callable_kwargs.items())
        for tuple_value in callable_kwargs:
            if (tup_len := len(tuple_value)) != 2:
                err_str = "callable kwargs when converted to tuple of key-value pair must be of " \
                          f"2 in length but has {tup_len}"
                logging.exception(err_str)
                raise Exception(err_str)
        return callable_kwargs


class PathWSConnectionManager(WSConnectionManager):
    def __init__(self):
        super().__init__()
        self.active_ws_data_list: List[WSData] = []

    def __str__(self):
        ret_str = "active_ws_set: "
        with self.rlock:
            for ws_data in self.active_ws_data_list:
                ret_str += str(ws_data.ws_object)
            return ret_str + "\n" + str(super)

    async def connect(self, ws: WebSocket, filter_callable: Callable[..., Any] | None = None,
                      callable_kwargs: Dict[Any, Any] | None = None, projection_model=None) -> bool:

        async with self.rlock:
            is_new_ws: bool = await WSConnectionManager.add_to_master_ws_set(ws)
            # if ws not in self.active_ws_n_callable_tuple_set:
            if not any(ws in active_ws_callable_tuple
                       for active_ws_callable_tuple in self.active_ws_data_list):
                # old or new ws does not matter - may have been added to master via a different path
                self.active_ws_data_list.append(WSData(ws_object=ws, filter_callable=filter_callable,
                                                       filter_callable_kwargs=callable_kwargs,
                                                       projection_model=projection_model))
                return True
            elif is_new_ws:
                raise Exception(f"Unexpected! ws: {ws} is in active_ws_n_callable_tuple_set "
                                f"while not in master: {str(self)}")
            else:
                # ws present in master (some other path may have added) and
                # present already in active_ws_n_callable_tuple_set
                logging.debug("connect called on a pre-added ws from active_ws_n_callable_tuple_set, "
                              "investigate: maybe ignorable bug")
                return False  # helps avoid starting a second recv call on this ws by caller
        return True

    async def disconnect(self, ws: WebSocket):
        async with self.rlock:
            for fetched_ws_data in self.active_ws_data_list:
                if fetched_ws_data.ws_object == ws:
                    self.active_ws_data_list.remove(fetched_ws_data)
                    break
            else:
                logging.error(f"Unexpected! likely bug, ws: {ws} not in active_ws_n_callable_tuple_set: {str(self)}")
            await WSConnectionManager.remove_from_master_ws_set(ws)

    async def broadcast(self, json_str: str, ws_data: WSData, task_list: List[asyncio.Task]):
        remove_websocket: WebSocket | None = None
        try:
            async with self.rlock:
                ws = ws_data.ws_object
                filter_callable = ws_data.filter_callable
                kwargs_tuple = ws_data.filter_callable_kwargs
                # somehow this was found as a string
                if filter_callable is None:
                    create_task = True
                else:
                    kwargs = {k: v for k, v in kwargs_tuple}
                    create_task = filter_callable(json_str, **kwargs)
                    # else not required: ignore task creation if callable not allows
                if create_task:
                    task = asyncio.create_task(ws.send_text(json_str), name=f"{len(task_list)}")
                    task_list.append(task)
        except WebSocketDisconnect as e:
            remove_websocket = ws_data.ws_object
            logging.exception(
                f"WebSocketDisconnect: encountered while broadcasting, exception: {e}, ws: {ws_data.ws_object}")
        except RuntimeError as e:
            remove_websocket = ws_data.ws_object
            logging.exception(f"RuntimeError: encountered while broadcasting, exception: {e}, ws: {ws_data.ws_object}")
        except Exception as e:
            remove_websocket = ws_data.ws_object
            logging.exception(f"Exception: {e}, ws: {ws_data.ws_object}")
        finally:
            if remove_websocket is not None:
                await self.disconnect(remove_websocket)

    def get_activ_ws_data_list(self) -> List[WSData]:
        return self.active_ws_data_list


class PathWithIdWSConnectionManager(WSConnectionManager):
    def __init__(self):
        super().__init__()
        self.id_to_active_ws_data_list_dict: Dict[Any, List[WSData]] = dict()

    def __str__(self):
        ret_str = "active_ws_set: "
        with self.rlock:
            for obj_id, active_ws_data_list in self.id_to_active_ws_data_list_dict.items():
                set_as_str = "".join([str(ws_data.ws_object) for ws_data in active_ws_data_list])
                ret_str += f"obj_id: {obj_id} set: {set_as_str}\n"
            return ret_str + "\n" + str(super)

    async def connect(self, ws: WebSocket, obj_id: Any, filter_callable: Callable[..., Any] | None = None,
                      callable_kwargs: Dict[Any, Any] | None = None, projection_model=None) -> bool:

        async with self.rlock:
            is_new_ws: bool = await WSConnectionManager.add_to_master_ws_set(ws)
            # new or not, if id is not in dict, it's new for this path
            if obj_id not in self.id_to_active_ws_data_list_dict:
                self.id_to_active_ws_data_list_dict[obj_id] = []
                self.id_to_active_ws_data_list_dict[obj_id].append(
                    WSData(ws_object=ws, filter_callable=filter_callable, filter_callable_kwargs=callable_kwargs,
                           projection_model=projection_model))
            elif is_new_ws:  # we have the obj_id in our dict but master did not have this websocket
                active_ws_n_filter_callable_tuple_list: List[WSData] = \
                    self.id_to_active_ws_data_list_dict[obj_id]
                if not (ws in [ws_data.ws_object for ws_data in active_ws_n_filter_callable_tuple_list]):
                    self.id_to_active_ws_data_list_dict[obj_id].append(
                        WSData(ws_object=ws, filter_callable=filter_callable, filter_callable_kwargs=callable_kwargs,
                               projection_model=projection_model))
                    logging.debug("new client web-socket connect called on a pre-added obj_id-web-path")
                else:
                    raise Exception(
                        f"Unexpected! ws: {ws} for id: {obj_id} found in active_ws_n_filter_callable_tuple_list "
                        f"but not in master: {str(self)}, likely a bug")
            else:
                pass
        return is_new_ws

    async def disconnect(self, ws: WebSocket, obj_id: Any):
        async with self.rlock:
            for fetched_ws_data in self.id_to_active_ws_data_list_dict[obj_id]:
                if fetched_ws_data.ws_object == ws:
                    self.id_to_active_ws_data_list_dict[obj_id].remove(fetched_ws_data)
                    break
            else:
                logging.error(f"Unexpected! likely bug, ws: {ws} not in active_ws_n_callable_tuple_set "
                              f"for obj_id {obj_id}: {str(self)}")
            if len(self.id_to_active_ws_data_list_dict[obj_id]) == 0:
                del self.id_to_active_ws_data_list_dict[obj_id]
            await WSConnectionManager.remove_from_master_ws_set(ws)

    # async def receive_in_json(self, websocket: WebSocket):
    #     cleaned_json_data_str = await websocket.receive_json()
    #     if type(cleaned_json_data_str).__name__ == 'str':
    #         return json.loads(cleaned_json_data_str)
    #     else:
    #         return cleaned_json_data_str

    def get_activ_ws_tuple_list_with_id(self, obj_id) -> Set[WSData] | None:
        return self.id_to_active_ws_data_list_dict.get(obj_id)

    async def broadcast(self, json_str, obj_id: Any, ws_data: WSData, task_list: List[asyncio.Task]):
        async with self.rlock:
            remove_websocket: WebSocket | None = None
            try:
                filter_callable = ws_data.filter_callable
                filter_callable_kwargs = ws_data.filter_callable_kwargs
                # somehow this was found as a string
                if filter_callable is None:
                    create_task = True
                else:
                    create_task = filter_callable(json_str, **filter_callable_kwargs)

                if create_task:
                    task = asyncio.create_task(ws_data.ws_object.send_text(json_str), name=f"{len(task_list)}")
                    task_list.append(task)
            except WebSocketDisconnect as e:
                remove_websocket = ws_data.ws_object
                logging.exception(
                    f"WebSocketDisconnect: encountered while broadcasting, exception: {e}, ws: {remove_websocket}")
            except RuntimeError as e:
                remove_websocket = ws_data.ws_object
                logging.exception(f"RuntimeError: encountered while broadcasting, exception: {e}, ws: {remove_websocket}")
            except Exception as e:
                remove_websocket = ws_data.ws_object
                logging.exception(f"Exception: {e}, ws: {remove_websocket}")
            finally:
                if remove_websocket is not None:
                    if remove_websocket in self.id_to_active_ws_data_list_dict[obj_id]:
                        await self.disconnect(remove_websocket, obj_id)

