from typing import Dict, Set, List, Any, ClassVar
from fastapi import WebSocket, WebSocketDisconnect
from threading import RLock
import logging


class WSConnectionManager:
    """
    ws - WebSocket
    Solves 2 purposes:
    1. Avoid duplicate ws accepts and enable reuse of accepted ws across web-paths
    2. Allows web-path specific ws collection {with or without ID} to enable web-path specific broadcast
    """
    _master_ws_set: ClassVar[Set[WebSocket]] = set()
    _master_ws_set_rlock: ClassVar[RLock] = RLock()  # str may be called while holding the lock by same thread

    def __init__(self):
        self.rlock: RLock = RLock()  # subclass str may be called while holding the lock by same thread

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
        with cls._master_ws_set_rlock:
            if ws not in cls._master_ws_set:
                await ws.accept()  # throws exception if ws is in disconnected state
                cls._master_ws_set.add(ws)
                return True
            else:
                return False

    @classmethod
    def remove_from_master_ws_set(cls, ws: WebSocket) -> bool:
        with cls._master_ws_set_rlock:
            if ws in cls._master_ws_set:
                cls._master_ws_set.remove(ws)
                return True
            else:
                # must have been removed by other web-path cache holders upon discovering a disconnect
                return False

    @staticmethod
    async def send_json_to_websocket(json_str, websocket: WebSocket):
        await websocket.send_text(json_str)


class PathWSConnectionManager(WSConnectionManager):
    def __init__(self):
        super().__init__()
        self.active_ws_set: Set[WebSocket] = set()

    def __str__(self):
        ret_str = "active_ws_set: "
        with self.rlock:
            for ws in self.active_ws_set:
                ret_str += str(ws)
            return ret_str + "\n" + str(super)

    async def connect(self, ws: WebSocket) -> bool:
        with self.rlock:
            is_new_ws: bool = await WSConnectionManager.add_to_master_ws_set(ws)
            if ws not in self.active_ws_set:
                # old or new ws does not matter - may have been added to master via a different path
                self.active_ws_set.add(ws)
                return True
            elif is_new_ws:
                raise Exception(f"Unexpected! ws: {ws} is in active_ws_set while not in master: {str(self)}")
            else:  # ws present in master (some other path may have added) and present already in active_ws_set
                logging.debug("connect called on a pre-added ws from active_ws_set, investigate: maybe ignorable bug")
                return False  # helps avoid starting a second recv call on this ws by caller
        return True

    def disconnect(self, ws: WebSocket):
        with self.rlock:
            if ws in self.active_ws_set:
                self.active_ws_set.remove(ws)
            else:
                logging.error("Unexpected! likely bug, ws: {ws} not in active_ws_set: {str(self)}")
            WSConnectionManager.remove_from_master_ws_set(ws)

    async def broadcast(self, json_str):
        remove_websocket_list: List[WebSocket] = list()
        ws = None
        try:
            with self.rlock:
                for ws in self.active_ws_set:
                    await ws.send_text(json_str)  # somehow this was found as a string
        except WebSocketDisconnect as e:
            remove_websocket_list.append(ws)
            logging.exception(f"disconnected websocket encountered while broadcasting, exception: {e}")
        except Exception as e:
            remove_websocket_list.append(ws)
            logging.exception(f"ws.send_json while broadcasting sent non WebSocketDisconnect, exception: {e}")
        finally:
            for ws in remove_websocket_list:
                self.disconnect(ws)


class PathWithIdWSConnectionManager(WSConnectionManager):
    def __init__(self):
        super().__init__()
        self.id_to_active_ws_set_dict: Dict[Any, Set[WebSocket]] = dict()

    def __str__(self):
        ret_str = "active_ws_set: "
        with self.rlock:
            for obj_id, active_ws_set in self.id_to_active_ws_set_dict.items():
                set_as_str = "".join([str(ws) for ws in active_ws_set])
                ret_str += f"obj_id: {obj_id} set: {set_as_str}\n"
            return ret_str + "\n" + str(super)

    async def connect(self, ws: WebSocket, obj_id: Any) -> bool:
        with self.rlock:
            is_new_ws: bool = await WSConnectionManager.add_to_master_ws_set(ws)
            if obj_id not in self.id_to_active_ws_set_dict:  # new or not, if id is not in dict, it's new for this path
                self.id_to_active_ws_set_dict[obj_id] = set()
                self.id_to_active_ws_set_dict[obj_id].add(ws)
            elif is_new_ws:  # we have the obj_id in our dict but master did not have this websocket
                active_ws_set: Set[WebSocket] = self.id_to_active_ws_set_dict[obj_id]
                if ws not in active_ws_set:
                    self.id_to_active_ws_set_dict[obj_id].add(ws)
                    logging.debug("new client web-socket connect called on a pre-added obj_id-web-path")
                else:
                    raise Exception(
                        f"Unexpected! ws: {ws} for id: {obj_id} found in active_ws_set but not in master: {str(self)}, likely a bug")
            else:
                pass
        return is_new_ws

    def disconnect(self, ws: WebSocket, obj_id: Any):
        with self.rlock:
            self.id_to_active_ws_set_dict[obj_id].remove(ws)
            if len(self.id_to_active_ws_set_dict[obj_id]) == 0:
                del self.id_to_active_ws_set_dict[obj_id]
            WSConnectionManager.remove_from_master_ws_set(ws)

    # async def receive_in_json(self, websocket: WebSocket):
    #     cleaned_json_data_str = await websocket.receive_json()
    #     if type(cleaned_json_data_str).__name__ == 'str':
    #         return json.loads(cleaned_json_data_str)
    #     else:
    #         return cleaned_json_data_str

    async def broadcast(self, json_str, obj_id: Any):
        active_ws = None
        remove_websocket_list: List[WebSocket] = list()
        try:
            with self.rlock:
                if obj_id in self.id_to_active_ws_set_dict:
                    active_ws_set: Set[WebSocket] = self.id_to_active_ws_set_dict[obj_id]
                    for ws in active_ws_set:
                        active_ws = ws
                        await ws.send_text(json_str)  # somehow this was found as a string
                else:
                    logging.info(f"broadcast called on id: {obj_id} - no registered websocket found for this id")
        except WebSocketDisconnect as e:
            remove_websocket_list.append(ws)
            logging.exception(f"WebSocketDisconnect: encountered while broadcasting, exception: {e}, ws: {active_ws}")
        except RuntimeError as e:
            remove_websocket_list.append(active_ws)
            logging.exception(f"RuntimeError: encountered while broadcasting, exception: {e}, ws: {active_ws}")
        except Exception as e:
            remove_websocket_list.append(ws)
            logging.exception(f"Exception: {e}, ws: {active_ws}")
        finally:
            for ws in remove_websocket_list:
                if ws in self.id_to_active_ws_set_dict[obj_id]:
                    self.disconnect(ws, obj_id)
