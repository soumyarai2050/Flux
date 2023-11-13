import asyncio
import logging
import os.path
from typing import Any, List, Dict
from pathlib import PurePath

# 3rd party imports
from fastapi import APIRouter, Request, Query, WebSocket, HTTPException
from fastapi.encoders import jsonable_encoder

# project imports
from Flux.CodeGenProjects.ws_mux_demux_proxy.app.ws_mux_demux_proxy_server_manager import WSMuxDemuxProxyServerManager
from FluxPythonUtils.scripts.utility_functions import handle_ws, YAMLConfigurationManager, parse_to_int

ui_proxy_service_API_router = APIRouter()
root_dir_path = PurePath(__file__).parent.parent.parent
io_proxy_server_dir = PurePath(__file__).parent.parent
ui_proxy_server_data_dir = io_proxy_server_dir / "data"
config_yaml_path = ui_proxy_server_data_dir / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
ui_proxy_projects_list = config_yaml_dict.get("projects_names_for_ui_proxy_server")

if ui_proxy_projects_list is None or not isinstance(ui_proxy_projects_list, list) or not len(ui_proxy_projects_list):
    err_str = ("Couldn't find any 'ui_proxy_projects_list' key in data/config.yaml file of ui_proxy_server project"
               "or has incorrect value for loading ws route endpoints from generated config.yaml from projects")
    logging.error(err_str)
    raise Exception(err_str)

# loading and refactoring generated ui_proxy config files to be used in loading route endpoints
ui_uri_to_server_uri_dict_list: List[Dict[str, str]] = []
for project_name in ui_proxy_projects_list:
    project_dir_path = root_dir_path / project_name
    if os.path.exists(project_dir_path):
        project_config_file_path = project_dir_path / "data" / "config.yaml"
        if os.path.exists(project_config_file_path):
            project_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(project_config_file_path)
            project_host = project_config_yaml_dict.get("server_host")
            project_port = project_config_yaml_dict.get("main_server_beanie_port")
            if (project_host is None or len(project_host) < 1) or (project_port is None or len(project_port) < 1):
                err_str = (f"Either 'project_host' or 'project_port' not found in {project_config_file_path} file of "
                           f"project: {project_name}")
                logging.error(err_str)
                raise Exception(err_str)

            generated_ui_proxy_config_file_path = (project_dir_path / "generated" / "FastApi" /
                                                   "ui_uri_to_server_uri_config.yaml")
            if os.path.exists(generated_ui_proxy_config_file_path):
                ui_uri_to_server_uri_config_dict = (
                    YAMLConfigurationManager.load_yaml_configurations(generated_ui_proxy_config_file_path))
                ui_uri_to_server_uri_config_dict_list = ui_uri_to_server_uri_config_dict.get("ui_uri_to_server_uri")
                if ui_uri_to_server_uri_config_dict_list is not None:
                    for ui_uri_to_server_uri_dict in ui_uri_to_server_uri_config_dict_list:
                        temp_dict = {}
                        type = ui_uri_to_server_uri_dict.get("type")
                        temp_dict["type"] = type
                        if type == "GET_ALL" or type == "QUERY":
                            temp_dict["ui_uri"] = ui_uri_to_server_uri_dict.get("ws_uri_path")
                            temp_dict["server_uri"] = (f"ws://{project_host}:{project_port}/{project_name}"
                                                       f"{ui_uri_to_server_uri_dict.get('ws_uri_path')}")
                            temp_dict["server_http_uri"] = (f"http://{project_host}:{project_port}/{project_name}"
                                                            f"{ui_uri_to_server_uri_dict.get('get_http_path')}")
                        elif type == "GET_BY_ID":
                            ui_uri_path = ui_uri_to_server_uri_dict.get("ws_uri_path")
                            temp_dict["ui_uri"] = ui_uri_path
                            server_uri_path = ui_uri_path.split("/")[1]
                            temp_dict["server_uri"] = (f"ws://{project_host}:{project_port}/{project_name}/"
                                                       f"{server_uri_path}")
                            temp_dict["server_http_uri"] = (f"http://{project_host}:{project_port}/{project_name}"
                                                            f"{ui_uri_to_server_uri_dict.get('get_http_path')}")
                        else:
                            err_str = (f"Unsupported type: '{type}' in {generated_ui_proxy_config_file_path}, must be "
                                       f"one of ['GET_ALL', 'GET_BY_ID', 'QUERY']")
                            logging.error(err_str)
                            raise Exception(err_str)
                        ui_uri_to_server_uri_dict_list.append(temp_dict)
                else:
                    err_str = f"No key 'ui_uri_to_server_uri' found in {generated_ui_proxy_config_file_path}"
                    logging.error(err_str)
                    raise Exception(err_str)
            else:
                err_str = f"No file exists: {generated_ui_proxy_config_file_path}"
                logging.error(err_str)
                raise Exception(err_str)
        else:
            err_str = f"No file exists: {project_config_file_path}"
            logging.error(err_str)
            raise Exception(err_str)
    else:
        err_str = f"Project Dir path doesn't exist, project_dir_path: {project_dir_path}"
        logging.error(err_str)
        raise Exception(err_str)


async def handle_ui_get_all_ws(websocket: WebSocket) -> None:
    """ Get All websocket """
    if WSMuxDemuxProxyServerManager.async_loop is None:
        WSMuxDemuxProxyServerManager.async_loop = asyncio.get_running_loop()

    for ui_uri_to_server_uri_dict_ in ui_uri_to_server_uri_dict_list:
        if ui_uri_to_server_uri_dict_.get("ui_uri") in str(websocket.url):
            server_ws_uri = ui_uri_to_server_uri_dict_.get("server_uri")
            server_get_all_uri = ui_uri_to_server_uri_dict_.get("server_http_uri")
            break
    else:
        err_str_ = (f"Can't find any ui_uri present in ui_uri_to_server_uri_dict_list that matched "
                   f"path in uri {websocket.url}")
        logging.error(err_str_)
        raise HTTPException(status_code=500, detail=err_str_)

    server_ws_uri += f"?need_initial_snapshot=false"   # connecting for no initial snapshot ws uri
    is_new_ws = await WSMuxDemuxProxyServerManager.register_n_connect(server_ws_uri, server_get_all_uri, websocket)
    await handle_ws(websocket, is_new_ws)


async def handle_ui_get_by_id_ws(websocket: WebSocket) -> None:
    """ Get By Id websocket """
    if WSMuxDemuxProxyServerManager.async_loop is None:
        WSMuxDemuxProxyServerManager.async_loop = asyncio.get_running_loop()

    for ui_uri_to_server_uri_dict_ in ui_uri_to_server_uri_dict_list:
        ui_uri_path_ = ui_uri_to_server_uri_dict_.get("ui_uri").split("/")[1]
        if ui_uri_path_ in str(websocket.url):
            server_ws_uri = ui_uri_to_server_uri_dict_.get("server_uri")
            server_get_by_id_http_uri = ui_uri_to_server_uri_dict_.get("server_http_uri")
            obj_id: int = parse_to_int(str(websocket.url).split("/")[-1])  # since obj id is last param for ui_server
            break
    else:
        err_str_ = (f"Can't find any ui_uri present in ui_uri_to_server_uri_dict_list that matched "
                    f"path in uri {websocket.url}")
        logging.error(err_str_)
        raise HTTPException(status_code=500, detail=err_str_)

    server_ws_uri += f"/{obj_id}?need_initial_snapshot=false"   # adding current obj_id
    server_get_by_id_http_uri += f"/{obj_id}"
    is_new_ws = await WSMuxDemuxProxyServerManager.register_n_connect(server_ws_uri, server_get_by_id_http_uri,
                                                                      websocket)
    await handle_ws(websocket, is_new_ws)


async def handle_ui_query_ws(websocket: WebSocket) -> None:
    """ Query websocket """
    if WSMuxDemuxProxyServerManager.async_loop is None:
        WSMuxDemuxProxyServerManager.async_loop = asyncio.get_running_loop()

    for ui_uri_to_server_uri_dict_ in ui_uri_to_server_uri_dict_list:
        ui_uri_path_ = ui_uri_to_server_uri_dict_.get("ui_uri")
        ws_url = str(websocket.url)
        if ui_uri_path_ in ws_url:
            server_ws_uri = ui_uri_to_server_uri_dict_.get("server_uri")
            server_ws_uri += ws_url[ws_url.index("?"):] + "&need_initial_snapshot=false"    # Adding query params
            server_get_by_id_http_uri = ui_uri_to_server_uri_dict_.get("server_http_uri") + ws_url[ws_url.index("?"):]
            break
    else:
        err_str_ = (f"Can't find any ui_uri present in ui_uri_to_server_uri_dict_list that matched "
                    f"path in uri {websocket.url}")
        logging.error(err_str_)
        raise HTTPException(status_code=500, detail=err_str_)

    # server_ws_uri += f"/false"  # connecting for no initial snapshot ws uri
    is_new_ws = await WSMuxDemuxProxyServerManager.register_n_connect(server_ws_uri, server_get_by_id_http_uri,
                                                                      websocket)
    await handle_ws(websocket, is_new_ws)


# Loading all route endpoints
for ui_uri_to_server_uri_dict in ui_uri_to_server_uri_dict_list:
    if ui_uri_to_server_uri_dict.get("type") == "GET_ALL":
        ui_proxy_service_API_router.add_api_websocket_route(ui_uri_to_server_uri_dict.get("ui_uri"),
                                                            handle_ui_get_all_ws)
    elif ui_uri_to_server_uri_dict.get("type") == "GET_BY_ID":
        ui_proxy_service_API_router.add_api_websocket_route(ui_uri_to_server_uri_dict.get("ui_uri"),
                                                            handle_ui_get_by_id_ws)
    else:
        ui_proxy_service_API_router.add_api_websocket_route(ui_uri_to_server_uri_dict.get("ui_uri"),
                                                            handle_ui_query_ws)
