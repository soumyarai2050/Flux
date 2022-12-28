#!/usr/bin/env python
import json
import logging
import os
from pathlib import PurePath
from typing import List, Callable, Dict
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main

# Required for accessing custom options from schema
from Flux.PyCodeGenEngine.PluginFastApi import insertion_imports


class FastApiClassGenPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_json_root_create_field: str = "CreateDesc"
    flux_json_root_read_field: str = "ReadDesc"
    flux_json_root_update_field: str = "UpdateDesc"
    flux_json_root_patch_field: str = "PatchDesc"
    flux_json_root_delete_field: str = "DeleteDesc"
    flux_json_root_read_websocket_field: str = "ReadWebSocketDesc"
    flux_json_root_update_websocket_field: str = "UpdateWebSocketDesc"
    flux_fld_is_required: str = "FluxFldIsRequired"
    flux_fld_cmnt: str = "FluxFldCmnt"
    flux_msg_cmnt: str = "FluxMsgCmnt"
    flux_fld_index: str = "FluxFldIndex"
    flux_fld_web_socket: str = "FluxFldWebSocket"
    default_id_field_name: str = "id"
    proto_type_to_py_type_dict: Dict[str, str] = {
        "int32": "int",
        "int64": "int",
        "string": "str",
        "bool": "bool",
        "float": "float"
    }

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_fastapi_class_gen
        ]
        response_field_case_style = None
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None:
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME_SUFFIX' received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        # Since output file name for this plugin will be created at runtime
        self.output_file_name_suffix = ""
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.fastapi_app_name: str = ""
        self.proto_file_name: str = ""
        self.proto_file_package: str = ""
        self.api_router_app_name: str = ""
        self.database_file_name: str = ""
        self.fastapi_file_name: str = ""
        self.model_file_name: str = ""
        self.routes_file_name: str = ""
        self.client_file_name: str = ""
        self.launch_file_name: str = ""
        self.routes_callback_class_name: str = ""
        self.routes_callback_class_name_override: str = ""
        self.routes_callback_class_name_capital_camel_cased: str = ""
        self.int_id_message_list: List[protogen.Message] = []
        self.callback_override_set_instance_file_name: str = ""

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if FastApiClassGenPlugin.flux_msg_json_root in str(field.message.proto.options):
                    if field.message not in self.root_message_list:
                        self.root_message_list.append(field.message)
                    # else not required: avoiding repetition
                else:
                    if field.message not in self.non_root_message_list:
                        self.non_root_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.load_dependency_messages_and_enums_in_dicts(field.message)
            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if FastApiClassGenPlugin.flux_msg_json_root in str(message.proto.options):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                for field in message.fields:
                    if field.proto.name == FastApiClassGenPlugin.default_id_field_name and \
                            "int" == self.proto_to_py_datatype(field):
                        self.int_id_message_list.append(message)
                    # else enot required: If field is not id or is not type int then avoiding append
                    # in int_id_message_list
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                return FastApiClassGenPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def handle_POST_gen(self, message: protogen.Message, method_desc: str | None = None,
                        id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + \
                     f'", response_model={message.proto.name}, status_code=201)\n'
        output_str += f"async def create_{message_name_snake_cased}_http({message_name_snake_cased}: " \
                      f"{message.proto.name}) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    callback_class.create_{message_name_snake_cased}_pre({message_name_snake_cased})\n"
        output_str += f"    {message_name_snake_cased}_obj = await generic_post_http({message.proto.name}, " \
                      f"{message_name_snake_cased})\n"
        output_str += f"    callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_GET_gen(self, message: protogen.Message, method_desc: str | None = None,
                       id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                     f'{message_name_snake_cased}_id' + '}' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> {message.proto.name}:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"PydanticObjectId) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    callback_class.read_by_id_{message_name_snake_cased}_pre({message_name_snake_cased}_id)\n"
        output_str += f"    {message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                      f"{message.proto.name}, {message_name_snake_cased}_id)\n"
        output_str += f"    callback_class.read_by_id_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None,
                       id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    callback_class.update_{message_name_snake_cased}_pre({message_name_snake_cased}_updated)\n"
        output_str += f"    {message_name_snake_cased}_obj = await generic_put_http({message.proto.name}, " \
                      f"{message_name_snake_cased}_updated)\n"
        output_str += f"    callback_class.update_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_PATCH_gen(self, message: protogen.Message, method_desc: str | None = None,
                         id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}Optional) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    callback_class.partial_update_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_updated)\n"
        output_str += f"    {message_name_snake_cased}_obj =  await generic_patch_http({message.proto.name}, " \
                      f"{message_name_snake_cased}_updated)\n"
        output_str += f"    callback_class.partial_update_{message_name_snake_cased}_post(" \
                      f"{message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None,
                          id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                     '{'+f'{message_name_snake_cased}_id'+'}' + \
                     f'", response_model=DefaultWebResponse, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id: {id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id: PydanticObjectId) -> DefaultWebResponse:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    callback_class.delete_{message_name_snake_cased}_pre({message_name_snake_cased}_id)\n"
        output_str += f"    delete_web_resp = await generic_delete_http({message.proto.name}, " \
                      f"{message.proto.name}BaseModel, {message_name_snake_cased}_id)\n"
        output_str += f"    callback_class.delete_{message_name_snake_cased}_post(delete_web_resp)\n"
        output_str += f"    return delete_web_resp\n"
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-{field_name}/' + \
                     '{' + f'{field_name}' + '}' + f'", response_model=List[{message.proto.name}], status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_from_{field_name}_http({field_name}: " \
                      f"{field_type}) -> List[{message.proto.name}]:\n"
        output_str += f'    """ Index for {field_name} field of {message.proto.name} """\n'
        output_str += f"    callback_class.index_of_{field_name}_{message_name_snake_cased}_pre()\n"
        output_str += f"    {message_name_snake_cased}_obj = await generic_index_http({message.proto.name}, " \
                      f"{message.proto.name}.{field_name}, {field_name})\n"
        output_str += f"    callback_class.index_of_{field_name}_{message_name_snake_cased}_post(" \
                      f"{message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_gen(self, message: protogen.Message, method_desc: str, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/get-{message_name_snake_cased}-ws/' + \
                     '{' + f'{message_name_snake_cased}_id' + '}")\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                          f"{message_name_snake_cased}_id: {id_field_type}) -> None:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                          f"{message_name_snake_cased}_id: PydanticObjectId) -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc } """\n'
        output_str += f"    callback_class.read_by_id_ws_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_id)\n"
        output_str += f"    await generic_read_by_id_ws(websocket, " \
                      f"{message_name}, {message_name_snake_cased}_id)\n"
        output_str += f"    callback_class.read_by_id_ws_{message_name_snake_cased}_post()\n"
        return output_str

    def handle_read_all_WEBSOCKET_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/get-all-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def read_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        output_str += f'    """ Get All {message_name} using websocket """\n'
        output_str += f"    callback_class.read_all_ws_{message_name_snake_cased}_pre()\n"
        output_str += f"    await generic_read_ws(websocket, {message_name})\n"
        output_str += f"    callback_class.read_all_ws_{message_name_snake_cased}_post()\n\n\n"
        return output_str

    def handle_update_WEBSOCKET_gen(self, message: protogen.Message, method_desc: str, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/update-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def update_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc } """\n'
        output_str += f"    await generic_update_ws(websocket, {message_name})\n"
        return output_str

    def handle_field_web_socket_gen(self, message: protogen.Message, field: protogen.Field):
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        output_str = f'@{self.api_router_app_name}.websocket("/ws-read-{message_name_snake_cased}-for-{field_name}/")\n'
        output_str += f"async def ws_read_{message_name_snake_cased}_for_{field_name}(websocket: WebSocket, " \
                      f"{field_name}: {field_type}) -> None:\n"
        output_str += f'    """ websocket for {field_name} field of {message.proto.name} """\n'
        output_str += f"    await websocket.accept()\n"
        output_str += f"    print({field_name})\n"
        output_str += f"    while True:\n"
        output_str += f"        data = await websocket.receive()\n"
        output_str += f"        await websocket.send(data)\n\n\n"
        return output_str

    def handle_get_all_message_request(self, message: protogen.Message) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}/' + \
                     f'", response_model=List[{message.proto.name}], status_code=200)\n'
        output_str += f"async def read_{message_name_snake_cased}_http() -> List[{message.proto.name}]:\n"
        output_str += f'    """\n'
        output_str += f'    Get All {message.proto.name}\n'
        output_str += f'    """\n'
        output_str += f"    callback_class.read_all_{message_name_snake_cased}_pre()\n"
        output_str += f"    obj_list = await generic_read_http({message.proto.name})\n"
        output_str += f"    callback_class.read_all_{message_name_snake_cased}_post(obj_list)\n"
        output_str += f"    return obj_list\n\n\n"
        return output_str

    def handle_CRUD_for_message(self, message: protogen.Message) -> str:
        options_list_of_dict = \
            self.get_complex_msg_option_values_as_list_of_dict(message, FastApiClassGenPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_method_call_dict = {
            FastApiClassGenPlugin.flux_json_root_create_field: self.handle_POST_gen,
            FastApiClassGenPlugin.flux_json_root_read_field: self.handle_GET_gen,
            FastApiClassGenPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            FastApiClassGenPlugin.flux_json_root_patch_field: self.handle_PATCH_gen,
            FastApiClassGenPlugin.flux_json_root_delete_field: self.handle_DELETE_gen,
            FastApiClassGenPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_gen,
            FastApiClassGenPlugin.flux_json_root_update_websocket_field: self.handle_update_WEBSOCKET_gen
        }

        output_str = self.handle_get_all_message_request(message)
        output_str += self.handle_read_all_WEBSOCKET_gen(message)

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                method_desc: str = option_dict[crud_option_field_name]
                output_str += crud_operation_method(message, method_desc, id_field_type)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if FastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                output_str += self.handle_index_req_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

            if FastApiClassGenPlugin.flux_fld_web_socket in str(field.proto.options):
                output_str += self.handle_field_web_socket_gen(message, field)
            # else not required: Avoiding field if websocket option is not enabled

        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            output_str += self.handle_CRUD_for_message(message)

        return output_str

    def handle_fastapi_initialize_file_gen(self):
        output_str = "from fastapi import FastAPI\n"
        routes_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_file_name)
        output_str += f"from {routes_file_path} import {self.api_router_app_name}\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import "
        for message in self.int_id_message_list:
            output_str += message.proto.name
            if message != self.int_id_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n\n"
        output_str += f"async def init_max_id_handler(root_base_model):\n"
        output_str += f'    root_base_model.init_max_id(0)\n\n\n'
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        for message in self.int_id_message_list:
            message_name = message.proto.name
            output_str += f"    await init_max_id_handler({message_name})\n"
        output_str += "\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'

        return output_str

    def _underlying_handle_generic_imports(self) -> str:
        generic_cache_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_routes")
        output_str = f'from {generic_cache_routes_file_path} import generic_post_http, ' + "\\\n"\
                     f'\tgeneric_put_http, generic_patch_http, generic_delete_http, ' \
                     f'generic_index_http, \\\n\tgeneric_read_http, generic_read_ws, ' \
                     f'generic_read_by_id_http, generic_read_by_id_ws\n'
        return output_str

    def _handle_model_imports(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            output_str += ", "
            output_str += f"{message.proto.name}Optional"
            output_str += ", "
            output_str += f"{message.proto.name}BaseModel"

            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        return output_str

    def _handle_routes_callback_import(self) -> str:
        routes_callback_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_callback_class_name)
        output_str = f"from {routes_callback_path} import {self.routes_callback_class_name_capital_camel_cased}\n"
        return output_str

    def _handle_routes_callback_instantiate(self):
        output_str = f"callback_class = {self.routes_callback_class_name_capital_camel_cased}.get_instance()\n\n\n"
        return output_str

    def _handle_callback_override_set_instance_import(self) -> str:
        callback_override_set_instance_file_path = \
            self.import_path_from_os_path("OUTPUT_DIR", self.callback_override_set_instance_file_name)
        output_str = "# below import is to set derived callback's instance if implemented in the script\n"
        callback_override_set_instance_file_path = ".".join(callback_override_set_instance_file_path.split(".")[:-1])
        output_str += f"from {callback_override_set_instance_file_path} import " \
                      f"{self.callback_override_set_instance_file_name}\n"
        callback_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.routes_callback_class_name}")
        routes_callback_class_name_camel_cased = self.convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {callback_file_path} import {routes_callback_class_name_camel_cased}\n\n\n"

        return output_str

    def handle_routes_file_gen(self) -> str:
        output_str = "from fastapi import APIRouter, Request, WebSocket\n"
        output_str += "from fastapi.templating import Jinja2Templates\n"
        output_str += "from typing import List\n"
        output_str += self._handle_routes_callback_import()
        output_str += self._handle_model_imports()
        output_str += self._underlying_handle_generic_imports()
        incremental_id_basemodel_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                      "incremental_id_basemodel")
        if self.response_field_case_style.lower() == "camel":
            output_str += f'from {incremental_id_basemodel_path} import to_camel\n'
        # else not required: if response type is not camel type then avoid import
        default_web_response_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "default_web_response")
        output_str += f'from {default_web_response_file_path} import DefaultWebResponse\n'
        output_str += f"\n\n"
        output_str += f"{self.api_router_app_name} = APIRouter()\n"
        output_str += self._handle_routes_callback_instantiate()
        output_str += self.handle_CRUD_task()
        output_str += "\n\ntemplates = Jinja2Templates(directory='templates')\n\n"
        output_str += f"@{self.api_router_app_name}.get('/')\n"
        output_str += "async def serve_spa(request: Request):\n"
        output_str += "    return templates.TemplateResponse('index.html', {'request': request})\n"
        return output_str

    def handle_POST_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def create_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}:\n"
        output_str += " "*8 + f"return generic_http_post_client(self.create_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_GET_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_{message_name_snake_cased}_client(self, {message_name_snake_cased}_id: " \
                     f"{field_type}) -> {message_name}:\n"
        output_str += " "*8 + f"return generic_http_get_client(self.get_{message_name_snake_cased}_client_url, " \
                      f"{message_name_snake_cased}_id, {message_name}BaseModel)"
        return output_str

    def handle_PUT_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def put_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_put_client(self.put_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_PATCH_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def patch_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_patch_client(self.patch_{message_name_snake_cased}" \
                      f"_client_url, pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_DELETE_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def delete_{message_name_snake_cased}_client(self, {message_name_snake_cased}_id: " \
                     f"{field_type}) -> Dict:\n"
        output_str += " "*4 + f"    return generic_http_delete_client(self.delete_{message_name_snake_cased}" \
                      f"_client_url, {message_name_snake_cased}_id)"
        return output_str

    def handle_index_client_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        message_name = message.proto.name
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_{message_name_snake_cased}_from_{field_name}_client(self, {field_name}: " \
                     f"{field_type}) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_get_client(" \
                      f"self.get_{message_name_snake_cased}_from_{field_name}_client_url, " \
                      f"{field_name}, {message_name}BaseModel)"
        return output_str

    def handle_get_all_message_http_client(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_all_{message_name_snake_cased}_client(self) -> List[{message_name}]:\n"
        output_str += " "*4 + f"    return generic_http_get_all_client(self.get_all_" \
                      f"{message_name_snake_cased}_client_url, {message_name}BaseModel)\n\n"
        return output_str

    def handle_get_all_message_ws_client(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"async def get_all_{message_name_snake_cased}_client_ws(self, user_callable: Callable):\n"
        output_str += " "*4 + f"    await generic_ws_get_all_client(self.get_all_{message_name_snake_cased}" \
                      f"_client_ws_url, {message_name}BaseModel, user_callable)\n\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_client_gen(self, message: protogen.Message, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"async def get_{message_name_snake_cased}_client_ws(self, " \
                     f"{message_name_snake_cased}_id: {id_field_type}, user_callable: Callable):\n"
        output_str += " "*4 + f"    await generic_ws_get_client(self.get_{message_name_snake_cased}_client_ws_url, " \
                      f"{message_name_snake_cased}_id, {message_name}BaseModel, user_callable)"
        return output_str

    def _get_msg_id_field_type(self, message: protogen.Message) -> str:
        id_field_type: str = "int"
        if message in self.int_id_message_list:
            for field in message.fields:
                if field.proto.name == FastApiClassGenPlugin.default_id_field_name and \
                        "int" != (field_type := self.proto_to_py_datatype(field)):
                    id_field_type = field_type
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

    def handle_client_methods(self, message: protogen.Message) -> str:
        options_list_of_dict = \
            self.get_complex_msg_option_values_as_list_of_dict(message,
                                                               FastApiClassGenPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_method_call_dict = {
            FastApiClassGenPlugin.flux_json_root_create_field: self.handle_POST_client_gen,
            FastApiClassGenPlugin.flux_json_root_read_field: self.handle_GET_client_gen,
            FastApiClassGenPlugin.flux_json_root_update_field: self.handle_PUT_client_gen,
            FastApiClassGenPlugin.flux_json_root_patch_field: self.handle_PATCH_client_gen,
            FastApiClassGenPlugin.flux_json_root_delete_field: self.handle_DELETE_client_gen,
            FastApiClassGenPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_client_gen
        }

        output_str = self.handle_get_all_message_http_client(message)
        output_str += self.handle_get_all_message_ws_client(message)

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                output_str += crud_operation_method(message, id_field_type)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if FastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                output_str += self.handle_index_client_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def _handle_client_url_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        options_list_of_dict = \
            self.get_complex_msg_option_values_as_list_of_dict(message,
                                                               FastApiClassGenPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_url_dict = {
            FastApiClassGenPlugin.flux_json_root_create_field: f"self.create_{message_name_snake_cased}_client_url: "
                                                               "str = f'http://{self.host}:{self.port}/" +
                                                               f"{self.proto_file_package}/"
                                                               f"create-{message_name_snake_cased}/'",
            FastApiClassGenPlugin.flux_json_root_read_field: f"self.get_{message_name_snake_cased}_client_url: str = "
                                                             "f'http://{self.host}:{self.port}/" +
                                                             f"{self.proto_file_package}/"
                                                             f"get-{message_name_snake_cased}/'",
            FastApiClassGenPlugin.flux_json_root_update_field: f"self.put_{message_name_snake_cased}_client_url: str = "
                                                               "f'http://{self.host}:{self.port}/" +
                                                               f"{self.proto_file_package}/"
                                                               f"put-{message_name_snake_cased}/'",
            FastApiClassGenPlugin.flux_json_root_patch_field: f"self.patch_{message_name_snake_cased}_client_url: "
                                                              "str = f'http://{self.host}:{self.port}/" +
                                                              f"{self.proto_file_package}/"
                                                              f"patch-{message_name_snake_cased}/'",
            FastApiClassGenPlugin.flux_json_root_delete_field: f"self.delete_{message_name_snake_cased}_client_url: "
                                                               "str = f'http://{self.host}:{self.port}/" +
                                                               f"{self.proto_file_package}/"
                                                               f"delete-{message_name_snake_cased}/'",
            FastApiClassGenPlugin.flux_json_root_read_websocket_field: f"self.get_{message_name_snake_cased}_"
                                                                       f"client_ws_url: "
                                                                       "str = f'ws://{self.host}:{self.port}/" +
                                                                       f"{self.proto_file_package}/get-"
                                                                       f"{message_name_snake_cased}-ws/'"
        }
        output_str = " "*8 + "self.get_all_"+f"{message_name_snake_cased}" + \
                     "_client_url: str = f'http://{self.host}:{self.port}/" + \
                     f"{self.proto_file_package}/get-all-{message_name_snake_cased}/'\n"
        output_str += " "*8 + "self.get_all_"+f"{message_name_snake_cased}" + \
                      "_client_ws_url: str = f'ws://{self.host}:{self.port}/" \
                      + f"{self.proto_file_package}/get-all-{message_name_snake_cased}-ws/'\n"

        for crud_option_field_name, url in crud_field_name_to_url_dict.items():
            if crud_option_field_name in option_dict:
                output_str += " "*8 + f"{url}"
                output_str += "\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if FastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                output_str += " "*8 + f"self.get_{message_name_snake_cased}_from_{field.proto.name}_client_url: " \
                              f"str = f'http://" + "{self.host}:{self.port}/" + \
                              f"{self.proto_file_package}/get-{message_name_snake_cased}-from-{field.proto.name}/'\n"
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_client_file_gen(self) -> str:
        output_str = f'from typing import Dict, List, Callable\n'
        generic_web_client_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_web_client")
        output_str += f'from {generic_web_client_path} import generic_http_get_all_client, ' + "\\\n" \
                      f'\tgeneric_http_post_client, generic_http_get_client, generic_http_put_client, ' \
                      f'generic_http_patch_client, \\\n\tgeneric_http_delete_client, generic_ws_get_client, ' \
                      f'generic_ws_get_all_client\n'
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            output_str += ", "
            output_str += f"{message.proto.name}BaseModel"
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        output_str += "\n\n"
        output_str += f"class {self.convert_to_capitalized_camel_case(self.client_file_name)}:\n\n"
        output_str += "    def __init__(self, host: str | None = None, port: int | None = None):\n"
        output_str += " "*4 + "    # host and port\n"
        output_str += " "*4 + f'    self.host = "127.0.0.1" if host is None else host\n'
        output_str += " "*4 + f'    self.port = 8000 if port is None else port\n\n'
        output_str += " "*4 + f'    # urls\n'
        for message in self.root_message_list:
            output_str += self._handle_client_url_gen(message)
            output_str += "\n"
        output_str += f'    # interfaces\n'
        for message in self.root_message_list:
            output_str += self.handle_client_methods(message)
        return output_str

    def handle_launch_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "import uvicorn\n"
        output_str += self._handle_callback_override_set_instance_import()
        routes_callback_class_name_camel_cased = self.convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from FluxPythonUtils.scripts.utility_functions import configure_logger\n\n"
        output_str += f'configure_logger(os.getenv("LOG_LEVEL"), log_file_name=os.getenv("LOG_FILE_PATH"))\n'
        output_str += "\n\n"
        output_str += f'def {self.launch_file_name}():\n'
        output_str += f'    callback_instance = {routes_callback_class_name_camel_cased}().get_instance()\n'
        output_str += f'    callback_instance.app_launch_pre()\n'
        output_str += f'    if reload_env := os.getenv("RELOAD"):\n'
        output_str += f'        reload_status: bool = True if reload_env.lower() == "true" else False\n'
        output_str += f'    else:\n'
        output_str += f'        reload_status: bool = False\n'
        output_str += f'    # Log Levels\n'
        output_str += f'    # NOTSET: 0\n'
        output_str += f'    # DEBUG: 10\n'
        output_str += f'    # INFO: 20\n'
        output_str += f'    # WARNING: 30\n'
        output_str += f'    # ERROR: 40\n'
        output_str += f'    # CRITICAL: 50\n'
        output_str += f'    host = "127.0.0.1" if (env_host := os.getenv("HOST")) is None else env_host\n'
        output_str += f'    port = 8000 if (env_port := os.getenv("PORT")) is None else int(env_port)\n'
        output_str += f'    uvicorn.run(reload=reload_status, \n'
        output_str += f'                host=host, \n'
        output_str += f'                port=port, \n'
        output_str += f'                app="{self.fastapi_file_name}:{self.fastapi_app_name}", \n'
        output_str += f'                log_level=20)\n'
        output_str += f'    callback_instance.app_launch_post()\n'
        return output_str

    def handle_POST_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    def create_{message_name_snake_cased}_pre(self, " \
                     f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        output_str += f"    def create_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_GET_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        if id_field_type is None:
            output_str = f"    def read_by_id_{message_name_snake_cased}_pre(self, obj_id: int):\n"
        else:
            output_str = f"    def read_by_id_{message_name_snake_cased}_pre(self, obj_id: {id_field_type}):\n"
        output_str += "        pass\n\n"
        output_str += f"    def read_by_id_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_PUT_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    def update_{message_name_snake_cased}_pre(self, " \
                     f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        output_str += f"    def update_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_PATCH_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    def partial_update_{message_name_snake_cased}_pre(self, " \
                     f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        output_str += f"    def partial_update_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_DELETE_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        if id_field_type is None:
            output_str = f"    def delete_{message_name_snake_cased}_pre(self, obj_id: int):\n"
        else:
            output_str = f"    def delete_{message_name_snake_cased}_pre(self, obj_id: {id_field_type}):\n"
        output_str += "        pass\n\n"
        output_str += f"    def delete_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_callback_methods_gen(self, message: protogen.Message,
                                                         id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        if id_field_type is None:
            output_str = f"    def read_by_id_ws_{message_name_snake_cased}_pre(self, obj_id: int):\n"
        else:
            output_str = f"    def read_by_id_ws_{message_name_snake_cased}_pre(self, obj_id: {id_field_type}):\n"
        output_str += "        pass\n\n"
        output_str += f"    def read_by_id_ws_{message_name_snake_cased}_post(self):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_get_all_message_http_callback_methods(self, message: protogen.Message) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    def read_all_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    def read_all_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_get_all_message_ws_callback_methods(self, message: protogen.Message) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    def read_all_ws_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    def read_all_ws_{message_name_snake_cased}_post(self):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_index_callback_methods_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    def index_of_{field.proto.name}_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    def index_of_{field.proto.name}_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_launch_pre_and_post_callback(self) -> str:
        output_str = "    def app_launch_pre(self):\n"
        output_str += '        logging.debug("Pre launch Fastapi app")\n\n'
        output_str += "    def app_launch_post(self):\n"
        output_str += '        logging.debug("Post launch Fastapi app")\n'
        return output_str

    def handle_callback_class_file_gen(self) -> str:
        output_str = "import threading\n"
        output_str += "import logging\n"
        output_str += "from typing import Optional, TypeVar, List\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n\n\n"
        output_str += f"{self.routes_callback_class_name_capital_camel_cased}DerivedType = " \
                      f"TypeVar('{self.routes_callback_class_name_capital_camel_cased}DerivedType', " \
                      f"bound='{self.routes_callback_class_name_capital_camel_cased}')\n\n\n"
        output_str += f"class {self.routes_callback_class_name_capital_camel_cased}:\n"
        output_str += f"    get_instance_mutex: threading.Lock = threading.Lock()\n"
        output_str += f"    {self.routes_callback_class_name}_instance: " \
                      f"Optional['{self.routes_callback_class_name_capital_camel_cased}'] = None\n\n"
        output_str += f"    def __init__(self):\n"
        output_str += f"        pass\n\n"

        output_str += f"    @classmethod\n"
        output_str += f"    def get_instance(cls) -> '{self.routes_callback_class_name_capital_camel_cased}':\n"
        output_str += f"        with cls.get_instance_mutex:\n"
        output_str += f"            if cls.{self.routes_callback_class_name}_instance is None:\n"
        output_str += f'                logging.exception("Error: get_instance invoked before any server creating ' \
                      f'instance via set_instance - "\n'
        output_str += f'                                  "instantiating default!")\n'
        output_str += f'                cls.{self.routes_callback_class_name}_instance = ' \
                      f'{self.routes_callback_class_name_capital_camel_cased}()\n'
        output_str += f"            return cls.{self.routes_callback_class_name}_instance\n\n"

        output_str += f"    @classmethod\n"
        output_str += f"    def set_instance(cls, instance: {self.routes_callback_class_name_capital_camel_cased}" \
                      f"DerivedType, delayed_override: bool = False) -> None:\n"
        output_str += f"        if not isinstance(instance, {self.routes_callback_class_name_capital_camel_cased}):\n"
        output_str += f'            raise Exception("{self.routes_callback_class_name_capital_camel_cased}.' \
                      f'set_instance must be invoked ' \
                      f'with a type that is "\n'
        output_str += f'                            "subclass of ' \
                      f'{self.routes_callback_class_name_capital_camel_cased} ' \
                      f'- is-subclass test failed!")\n'
        output_str += f'        if instance == cls.{self.routes_callback_class_name}_instance:\n'
        output_str += f'            return  # multiple calls with same instance is not an error (though - should be ' \
                      f'avoided where possible)\n'
        output_str += f'        with cls.get_instance_mutex:\n'
        output_str += f'            if cls.{self.routes_callback_class_name}_instance is not None:\n'
        output_str += f'                if delayed_override:\n'
        output_str += f'                    cls.{self.routes_callback_class_name}_instance = instance\n'
        output_str += f'                else:\n'
        output_str += f'                    raise Exception("Multiple ' \
                      f'{self.routes_callback_class_name_capital_camel_cased}.set_instance ' \
                      f'invocation detected with "\n'
        output_str += f'                                    "different instance objects. multiple calls allowed with ' \
                      f'the exact same object only"\n'
        output_str += f'                                    ", unless delayed_override is passed explicitly as True")\n'
        output_str += f'            cls.{self.routes_callback_class_name}_instance = instance\n\n'

        # Adding app pre- and post-launch methods
        output_str += self.handle_launch_pre_and_post_callback()
        output_str += "\n"

        for message in self.root_message_list:
            options_list_of_dict = \
                self.get_complex_msg_option_values_as_list_of_dict(message,
                                                                   FastApiClassGenPlugin.flux_msg_json_root)

            # Since json_root option is of non-repeated type
            option_dict = options_list_of_dict[0]

            crud_field_name_to_method_call_dict = {
                FastApiClassGenPlugin.flux_json_root_create_field: self.handle_POST_callback_methods_gen,
                FastApiClassGenPlugin.flux_json_root_read_field: self.handle_GET_callback_methods_gen,
                FastApiClassGenPlugin.flux_json_root_update_field: self.handle_PUT_callback_methods_gen,
                FastApiClassGenPlugin.flux_json_root_patch_field: self.handle_PATCH_callback_methods_gen,
                FastApiClassGenPlugin.flux_json_root_delete_field: self.handle_DELETE_callback_methods_gen,
                FastApiClassGenPlugin.flux_json_root_read_websocket_field:
                    self.handle_read_by_id_WEBSOCKET_callback_methods_gen
            }

            output_str += self.handle_get_all_message_http_callback_methods(message)
            output_str += self.handle_get_all_message_ws_callback_methods(message)

            id_field_type = self._get_msg_id_field_type(message)

            for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
                if crud_option_field_name in option_dict:
                    output_str += crud_operation_method(message, id_field_type)
                # else not required: Avoiding method creation if desc not provided in option

            for field in message.fields:
                if FastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                    output_str += self.handle_index_callback_methods_gen(message, field)
                # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_callback_override_set_instance_file_gen(self) -> str:
        output_str = "# File to contain injection of override callback instance using set instance\n\n"
        output_str += "import logging\n"

        callback_override_path = self.import_path_from_os_path("OUTPUT_DIR",
                                                               f"{self.routes_callback_class_name_override}")
        routes_callback_class_name_override_camel_cased = \
            self.convert_to_capitalized_camel_case(self.routes_callback_class_name_override)
        output_str += f"from {callback_override_path} import {routes_callback_class_name_override_camel_cased}\n\n\n"

        callback_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.routes_callback_class_name}")
        routes_callback_class_name_camel_cased = self.convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {callback_file_path} import {routes_callback_class_name_camel_cased}\n\n\n"

        output_str += \
            f"if {routes_callback_class_name_camel_cased}." \
            f"{self.routes_callback_class_name}_instance is None:\n"
        output_str += f"    callback_override = {routes_callback_class_name_override_camel_cased}()\n"
        output_str += f"    {routes_callback_class_name_camel_cased}.set_instance(callback_override)\n"
        output_str += "else:\n"
        output_str += '    err_str = f"set instance called more than once in one session"\n'
        output_str += '    logging.exception(err_str)\n'
        output_str += '    raise Exception(err_str)\n'
        return output_str

    def _handle_field_data_manipulation(self, json_content: Dict, message: protogen.Message, id_str: str | None = None,
                                        single_field: bool | None = False):
        if not single_field:
            temp_str = ""
            for field in message.fields:
                if FastApiClassGenPlugin.default_id_field_name == field.proto.name:
                    temp_str += f"{field.proto.name}={id_str}"
                else:
                    message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
                    if field == message.fields[0]:
                        temp_str += f"{field.proto.name}={json_content[message_name_snake_cased][field.proto.name]}"
                    else:
                        temp_str += f", {field.proto.name}={json_content[message_name_snake_cased][field.proto.name]}"
            return temp_str
        else:
            for field in message.fields:
                if FastApiClassGenPlugin.default_id_field_name != field.proto.name:
                    match field.kind.name.lower():
                        case "int32" | "int64" | "float":
                            return f"{field.proto.name} += 10"
                        case "string":
                            return f'{field.proto.name} = "test_str"'
                        case "bool":
                            return f"{field.proto.name} = True"
                # else not required: field must not be id to be manipulated in this method's use case
            else:
                err_str = f"Can't find any non-complex type field in this message: {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)

    def handle_callback_override_file_gen(self) -> str:
        if (output_dir_path := os.getenv("OUTPUT_DIR")) is not None:
            json_sample_file_path = PurePath(output_dir_path) / f"{self.proto_file_name}_json_sample.json"
        else:
            err_str = "Env var 'OUTPUT_DIR' received as None"
            logging.exception(err_str)
            raise Exception(err_str)
        with open(json_sample_file_path) as json_sample:
            json_sample_content = json.load(json_sample)
        try:
            required_root_msg: List[protogen.Message] = self.root_message_list[:4]
        except IndexError as e:
            err_str = f"Model might has less then 4 models, current implementation " \
                      f"requires at least 4 models, error: {e}"
            logging.exception(err_str)
            raise Exception(err_str)
        proto_file_name_capitalize_camel_cased = self.convert_to_capitalized_camel_case(self.proto_file_name)
        output_str = "from typing import List\n"
        output_str += "import threading\n"
        output_str += "import logging\n"
        output_str += "import asyncio\n\n"
        output_str += "# project imports\n"
        beanie_web_client_path = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.proto_file_name}_beanie_web_client")
        output_str += f"from {beanie_web_client_path} import " \
                      f"{proto_file_name_capitalize_camel_cased}BeanieWebClient\n"
        cache_web_client_path = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.proto_file_name}_cache_web_client")
        output_str += f"from {cache_web_client_path} import " \
                      f"{proto_file_name_capitalize_camel_cased}CacheWebClient\n"
        beanie_model_path = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.proto_file_name}_beanie_model")
        pydantic_models_comma_sep = ", ".join([msg.proto.name for msg in required_root_msg])
        output_str += f"from {beanie_model_path} import " \
                      f"{required_root_msg[0].proto.name}BaseModel, {pydantic_models_comma_sep}\n"
        beanie_routes_callback = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.routes_callback_class_name}")
        callback_class_name_camel_cased = self.convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {beanie_routes_callback} import " \
                      f"{callback_class_name_camel_cased}\n\n\n"
        output_str += f"{self.proto_file_name}_beanie_web_client_internal = " \
                     f"{proto_file_name_capitalize_camel_cased}BeanieWebClient()\n"
        output_str += f"{self.proto_file_name}_cache_web_client_external = " \
                      f"{proto_file_name_capitalize_camel_cased}CacheWebClient(port=8080)\n\n\n"
        output_str += f"class WsGet{required_root_msg[0].proto.name}ByIdCallback:\n"
        output_str += f"    def __call__(self, " \
                      f"{self.convert_camel_case_to_specific_case(required_root_msg[0].proto.name)}_base_model: " \
                      f"{required_root_msg[0].proto.name}BaseModel):\n"
        output_str += f'        logging.debug(f"callback function: {required_root_msg[0].proto.name} from DB: '+'{' + \
                      f'{self.convert_camel_case_to_specific_case(required_root_msg[0].proto.name)}_base_model' + \
                      '}")\n\n\n'
        output_str += f"class WsGet{required_root_msg[0].proto.name}Callback:\n"
        output_str += f"    def __call__(self, " \
                      f"{self.convert_camel_case_to_specific_case(required_root_msg[0].proto.name)}_base_model_list: " \
                      f"List[{required_root_msg[0].proto.name}BaseModel]):\n"
        output_str += f'        logging.debug(f"callback function: {required_root_msg[0].proto.name} List from DB: '+'{' + \
                      f'{self.convert_camel_case_to_specific_case(required_root_msg[0].proto.name)}_base_model_list' + \
                      '}")\n\n\n'
        callback_override_class_name_camel_cased = \
            self.convert_to_capitalized_camel_case(self.routes_callback_class_name_override)
        output_str += f"class {callback_override_class_name_camel_cased}(" \
                      f"{callback_class_name_camel_cased}):\n\n"
        output_str += f"    def __init__(self):\n"
        output_str += f"        super().__init__()\n\n"
        first_msg_name = required_root_msg[0].proto.name
        first_msg_name_snake_cased = self.convert_camel_case_to_specific_case(first_msg_name)
        output_str += f"    # Example 1 of 5: intercept web calls via callback example\n"
        output_str += f"    def create_{first_msg_name_snake_cased}_pre(self, " \
                      f"{first_msg_name_snake_cased}_obj: {first_msg_name}):\n"
        output_str += f'        logging.debug(f"{first_msg_name} From Ui: '+'{' + \
                      f'{first_msg_name_snake_cased}_obj'+'}'+'")\n'
        output_str += f'        {first_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, required_root_msg[0], single_field=True)}\n'
        output_str += f'        logging.debug(f"{first_msg_name} pre test: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        output_str += f'    def create_{first_msg_name_snake_cased}_post(self, ' \
                      f'{first_msg_name_snake_cased}_obj: {first_msg_name}):\n'
        output_str += f'        logging.debug(f"{first_msg_name} from DB: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n'
        output_str += f'        {first_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, required_root_msg[0], single_field=True)}\n'
        output_str += f'        logging.debug(f"{first_msg_name} Post test: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        output_str += f'    # Example 2 of 5: intercept web calls via callback and invoke another ' \
                      f'service on this very web server example\n'
        output_str += f'    def _http_create_{first_msg_name_snake_cased}_thread_func(self, obj):\n'
        field_str = self._handle_field_data_manipulation(json_sample_content, required_root_msg[0], "obj.id")
        output_str += f'        {first_msg_name_snake_cased}_obj = {first_msg_name}BaseModel({field_str})\n'
        output_str += f'        {first_msg_name_snake_cased}_obj = {self.proto_file_name}_beanie_web_client' \
                      f'_internal.create_{first_msg_name_snake_cased}_client({first_msg_name_snake_cased}_obj)\n'
        output_str += f'        logging.debug(f"Created {first_msg_name} obj from Another Document: ' + \
                      '{'+f'{first_msg_name_snake_cased}_obj'+'}'+'")\n\n'
        main_msg = required_root_msg[1]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = self.convert_camel_case_to_specific_case(main_msg_name)
        output_str += f'    def create_{main_msg_name_snake_cased}_pre(self, ' \
                      f'{main_msg_name_snake_cased}: {main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} from UI: '+'{'+f'{main_msg_name_snake_cased}'+'}'+'")\n'
        output_str += f'        # To avoid deadlock triggering another thread to execute another document creation\n'
        output_str += f'        # This same implementation is required even in post\n'
        output_str += f'        new_thread = threading.Thread(target=self._http_create_{first_msg_name_snake_cased}' \
                      f'_thread_func, args=({main_msg_name_snake_cased},), daemon=True)\n'
        output_str += f'        new_thread.start()\n\n'
        output_str += f'    def create_{main_msg_name_snake_cased}_post(self, {main_msg_name_snake_cased}: ' \
                      f'{main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} From Db: '+'{'+f'{main_msg_name_snake_cased}'+'}'+'")\n'
        output_str += f'        {main_msg_name_snake_cased}.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, main_msg, single_field=True)}\n'
        output_str += f'        logging.debug(f"{main_msg_name} Post test: ' + \
                      '{'+f'{main_msg_name_snake_cased}'+'}'+'")\n\n'
        main_msg = required_root_msg[2]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = self.convert_camel_case_to_specific_case(main_msg_name)
        output_str += f'    # Example 3 of 5: intercept web calls via callback and invoke ' \
                      f'another service on different web server example\n'
        output_str += f'    def create_{main_msg_name_snake_cased}_pre(self, ' \
                      f'{main_msg_name_snake_cased}_obj: {main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} from UI: ' + \
                      '{'+f'{main_msg_name_snake_cased}_obj'+'}'+'")\n'
        field_str = \
            self._handle_field_data_manipulation(json_sample_content, required_root_msg[0],
                                                 f"{main_msg_name_snake_cased}_obj.id")
        output_str += f'        {first_msg_name_snake_cased}_obj = {first_msg_name}BaseModel({field_str})\n'
        output_str += f'        {first_msg_name_snake_cased}_obj = {self.proto_file_name}_cache_web_client_external.' \
                      f'create_{first_msg_name_snake_cased}_client({first_msg_name_snake_cased}_obj)\n'
        output_str += f'        logging.debug(f"Created {first_msg_name} obj from Another Document: ' + \
                      '{'+f'{first_msg_name_snake_cased}_obj'+'}'+'")\n\n'
        output_str += f'    def create_{main_msg_name_snake_cased}_post(self, ' \
                      f'{main_msg_name_snake_cased}_obj: {main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} From Db: ' + \
                      '{'+f'{main_msg_name_snake_cased}_obj'+'}'+'")\n'
        output_str += f'        {main_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, main_msg, single_field=True)}\n'
        output_str += f'        logging.debug(f"{main_msg_name} Post test: ' + \
                      '{'+f'{main_msg_name_snake_cased}_obj'+'}'+'")\n\n'
        output_str += f'    # Example 4 of 5: intercept ws web calls via callback and ' \
                      f'invoke another service on this very web server example\n'
        output_str += f'    async def _ws_get_{first_msg_name_snake_cased}_by_id_thread_func(self, ' \
                      f'obj_id: int, ws_get_{first_msg_name_snake_cased}_by_id_callback):\n'
        output_str += f'        logging.debug("_ws_get_{first_msg_name_snake_cased}_by_id_thread_func: ' \
                      f'Connecting {first_msg_name_snake_cased} get_by_id ws:")\n'
        output_str += f'        await {self.proto_file_name}_beanie_web_client_internal.get_' \
                      f'{first_msg_name_snake_cased}_client_ws(obj_id, ws_get_{first_msg_name_snake_cased}' \
                      f'_by_id_callback)\n\n'
        main_msg = required_root_msg[3]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = self.convert_camel_case_to_specific_case(main_msg_name)
        output_str += f'    def read_by_id_ws_{main_msg_name_snake_cased}_pre(self, obj_id: int):\n'
        output_str += f'        logging.debug(f"read_by_id_ws_{main_msg_name_snake_cased}_pre:' \
                      f' {main_msg_name} id from UI: '+'{'+'obj_id'+'}'+'")\n'
        output_str += f'        ws_get_{first_msg_name_snake_cased}_by_id_callback: ' \
                      f'WsGet{first_msg_name}ByIdCallback = WsGet{first_msg_name}ByIdCallback()\n'
        output_str += f'        # running await function is different from running normal function in threading\n'
        output_str += f'        new_thread = threading.Thread(target=asyncio.run, args=(self._ws_get_' \
                      f'{first_msg_name_snake_cased}_by_id_thread_func(obj_id, ws_get_{first_msg_name_snake_cased}' \
                      f'_by_id_callback),), daemon=True)\n'
        output_str += f'        new_thread.start()\n'
        output_str += f'    def read_by_id_ws_{main_msg_name_snake_cased}_post(self):\n'
        output_str += f'        logging.debug(f"closing {main_msg_name_snake_cased} read ws ' \
                      f'in read_by_id_ws_{main_msg_name_snake_cased}_post")\n\n'
        output_str += f'    # Example 5 of 5: intercept ws web calls via callback and ' \
                      f'invoke another service on different web server example\n'
        output_str += f'    async def _ws_get_all_{first_msg_name_snake_cased}_thread_func(' \
                      f'self, ws_get_{first_msg_name_snake_cased}_callback):\n'
        output_str += f'        logging.debug("_ws_get_{first_msg_name_snake_cased}_by_id_thread_func: ' \
                      f'Connecting another server {first_msg_name_snake_cased} get_all ws:")\n'
        output_str += f'        await {self.proto_file_name}_cache_web_client_external.get_all_' \
                      f'{first_msg_name_snake_cased}_client_ws(ws_get_{first_msg_name_snake_cased}_callback)\n\n'
        output_str += f'    def read_all_ws_{main_msg_name_snake_cased}_pre(self):\n'
        output_str += f'        logging.debug(f"triggered read_all_ws_{main_msg_name_snake_cased}_pre")\n'
        output_str += f'        ws_get_{first_msg_name_snake_cased}_callback: WsGet{first_msg_name}Callback ' \
                      f'= WsGet{first_msg_name}Callback()\n'
        output_str += f'        # running await function is different from running normal function in threading\n'
        output_str += f'        new_thread = threading.Thread(target=asyncio.run, args=(self._ws_get_all_' \
                      f'{first_msg_name_snake_cased}_thread_func(ws_get_{first_msg_name_snake_cased}_callback),),' \
                      f' daemon=True)\n'
        output_str += f'        new_thread.start()\n\n'
        output_str += f'    def read_all_ws_{main_msg_name_snake_cased}_post(self):\n'
        output_str += f'        logging.debug(f"closing {main_msg_name_snake_cased} read all ws in ' \
                      f'read_all_ws_{main_msg_name_snake_cased}_post")\n'
        return output_str

    def set_req_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.database_file_name = f"{self.proto_file_name}_cache_database"
        self.fastapi_file_name = f"{self.proto_file_name}_cache_fastapi"
        self.model_file_name = f'{self.proto_file_name}_cache_model'
        self.routes_file_name = f'{self.proto_file_name}_cache_routes'
        self.launch_file_name = self.proto_file_name + "_cache_launch_server"
        self.client_file_name = f"{self.proto_file_name}_cache_web_client"
        self.routes_callback_class_name = f"{self.proto_file_name}_cache_routes_callback"
        self.routes_callback_class_name_override = f"{self.proto_file_name}_cache_routes_callback_override"
        routes_callback_class_name_camel_cased: str = self.convert_to_camel_case(self.routes_callback_class_name)
        self.routes_callback_class_name_capital_camel_cased: str = \
            routes_callback_class_name_camel_cased[0].upper() + routes_callback_class_name_camel_cased[1:]
        self.callback_override_set_instance_file_name = "cache_callback_override_set_instance"

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.set_req_data_members(file)

        output_dict: Dict[str, str] = {
            # Adding project´s main.py
            self.fastapi_file_name + ".py": self.handle_fastapi_initialize_file_gen(),

            # Adding route's callback class
            self.routes_callback_class_name + ".py": self.handle_callback_class_file_gen(),

            # Adding callback override set_instance file
            self.callback_override_set_instance_file_name + ".py":
                self.handle_callback_override_set_instance_file_gen(),

            # Adding callback override class file
            self.routes_callback_class_name_override + ".py": self.handle_callback_override_file_gen(),

            # Adding project's routes.py
            self.routes_file_name + ".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.launch_file_name + ".py": self.handle_launch_file_gen(),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen()
        }

        return output_dict


if __name__ == "__main__":
    main(FastApiClassGenPlugin)
