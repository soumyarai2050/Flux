# standard imports
import json
from typing import Set, Dict, List
import threading
import asyncio
import traceback
import logging
import requests

# 3rd party imports
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

# project imports
from FluxPythonUtils.scripts.ws_reader_lite import WSReaderLite
from FluxPythonUtils.scripts.async_rlock import AsyncRLock
from FluxPythonUtils.scripts.utility_functions import execute_tasks_list_with_all_completed
from Flux.PyCodeGenEngine.FluxCodeGenCore.ws_connection_manager import PathWSConnectionManager


class UIProxyServerManager:
    async_loop: asyncio.AbstractEventLoop | None = None
    ui_proxy_class_rlock: AsyncRLock = AsyncRLock()
    uri_to_ui_proxy_manager_data_dict: Dict[str, 'WSContainer'] = {}

    @classmethod
    async def register_n_connect(cls, server_ws_uri: str, server_get_all_http_uri: str, ws: WebSocket):
        async with cls.ui_proxy_class_rlock:
            ui_proxy_manager_data: WSContainer = cls.uri_to_ui_proxy_manager_data_dict.get(server_ws_uri)

            if ui_proxy_manager_data is None:
                ws_connection_manager = PathWSConnectionManager()
                is_new_ws = await ws_connection_manager.connect(ws)

                if is_new_ws:
                    ui_proxy_manager = cls(server_ws_uri)
                    ui_proxy_manager_data = WSContainer(ui_proxy_manager=ui_proxy_manager,
                                                        ws_connection_manager=ws_connection_manager)
                    cls.uri_to_ui_proxy_manager_data_dict[server_ws_uri] = ui_proxy_manager_data
                else:
                    return False
            else:
                is_new_ws = await ui_proxy_manager_data.ws_connection_manager.connect(ws)
                if not is_new_ws:
                    return False

            # sending get_all initial snapshot to ws client
            response = requests.get(server_get_all_http_uri)
            if response.ok:
                status_code, content = response.status_code, response.content
                await ui_proxy_manager_data.ws_connection_manager.send_json_to_websocket(content.decode('utf-8'), ws)
            else:
                err_str = f"Unexpected http response from uri: {server_get_all_http_uri}, response: {response}"
                logging.exception(err_str)
                raise HTTPException(detail=err_str, status_code=500)
            return True

    def __init__(self, uri):
        self.uri = uri
        self.ws_reader = WSReaderLite(uri, self.ui_callable)
        WSReaderLite.register_to_run(self.ws_reader)
        threading.Thread(target=self.ws_reader.current_start, daemon=True).start()

    async def _ui_callable(self, json_str):
        async with UIProxyServerManager.ui_proxy_class_rlock:
            ui_proxy_manager_data = UIProxyServerManager.uri_to_ui_proxy_manager_data_dict.get(self.uri)
            task_list: List[asyncio.Task] = []
            for ws_data in ui_proxy_manager_data.ws_connection_manager.active_ws_data_list:
                await ui_proxy_manager_data.ws_connection_manager.broadcast(json_str, ws_data, task_list)
            await execute_tasks_list_with_all_completed(task_list)

    def ui_callable(self, json_str: str):
        run_existing_executors_coro = self._ui_callable(json_str)
        future = asyncio.run_coroutine_threadsafe(run_existing_executors_coro,
                                                  UIProxyServerManager.async_loop)
        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"_ui_callable failed with exception: {e}, "
                              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")


# Putting it here since ui_proxy_manager field type is available here
class WSContainer(BaseModel):
    ui_proxy_manager: UIProxyServerManager  # reader
    ws_connection_manager: PathWSConnectionManager  # writer
    # max_update_id: int

    class Config:
        arbitrary_types_allowed = True  # required to use WebSocket as field type since it is arbitrary type

