#!/usr/bin/env python
import os
from typing import List, Dict
import logging
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.fast_api_class_gen_plugin import FastApiClassGenPlugin, main


class BeanieFastApiClassGenPlugin(FastApiClassGenPlugin):
    """
    Plugin script to generate Beanie enabled fastapi app
    """
    # Below field name 'id' must only be used intentionally in beanie pydentic models to make custom type
    # of primary key in that model
    default_id_field_name: str = "id"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.app_is_router: bool = True
        self.custom_id_primary_key_messages: List[protogen.Message] = []

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if BeanieFastApiClassGenPlugin.flux_msg_json_root in str(message.proto.options):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                if BeanieFastApiClassGenPlugin.default_id_field_name in [field.proto.name for field in message.fields]:
                    self.custom_id_primary_key_messages.append(message)
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

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

    def _get_msg_id_field_type(self, message: protogen.Message) -> str:
        id_field_type: str = "PydanticObjectId"
        if message in self.custom_id_primary_key_messages:
            for field in message.fields:
                if field.proto.name == BeanieFastApiClassGenPlugin.default_id_field_name:
                    id_field_type = self.proto_to_py_datatype(field)
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

    def handle_CRUD_for_message(self, message: protogen.Message) -> str:
        options_list_of_dict = \
            self.get_complex_msg_option_values_as_list_of_dict(message, BeanieFastApiClassGenPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_method_call_dict = {
            BeanieFastApiClassGenPlugin.flux_json_root_create_field: self.handle_POST_gen,
            BeanieFastApiClassGenPlugin.flux_json_root_read_field: self.handle_GET_gen,
            BeanieFastApiClassGenPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            BeanieFastApiClassGenPlugin.flux_json_root_patch_field: self.handle_PATCH_gen,
            BeanieFastApiClassGenPlugin.flux_json_root_delete_field: self.handle_DELETE_gen,
            BeanieFastApiClassGenPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_gen,
            BeanieFastApiClassGenPlugin.flux_json_root_update_websocket_field: self.handle_update_WEBSOCKET_gen
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
            if BeanieFastApiClassGenPlugin.flux_fld_index in str(field.proto.options):
                output_str += self.handle_index_req_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

            if BeanieFastApiClassGenPlugin.flux_fld_web_socket in str(field.proto.options):
                output_str += self.handle_field_web_socket_gen(message, field)
            # else not required: Avoiding field if websocket option is not enabled

        return output_str

    def handle_init_db(self) -> str:
        root_msg_list = [message.proto.name for message in self.root_message_list]
        model_names = ", ".join(root_msg_list)
        output_str = "async def init_db():\n"
        output_str += '    mongo_server = "mongodb://localhost:27017" if (mongo_env := os.getenv("MONGO_SERVER")) ' \
                      'is not None else mongo_env\n'
        output_str += f'    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_server)\n'
        output_str += f'    await init_beanie(\n'
        output_str += f'              database=client.{self.proto_file_package},\n'
        output_str += f'              document_models=[{model_names}]\n'
        output_str += f'              )\n'
        return output_str

    def handle_database_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "from beanie import init_beanie\n"
        output_str += "import motor\n"
        output_str += "import motor.motor_asyncio\n"

        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f'from {model_file_path} import '
        for message in self.root_message_list:
            output_str += message.proto.name
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n\n\n"

        output_str += self.handle_init_db()

        return output_str

    def handle_main_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "from fastapi import FastAPI\n"
        routes_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_file_name)
        output_str += f"from {routes_file_path} import {self.api_router_app_name}\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import "
        for message in self.custom_id_primary_key_messages:
            output_str += message.proto.name
            if message != self.custom_id_primary_key_messages[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        database_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.database_file_name)
        output_str += f"from {database_file_path} import init_db\n\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n\n"
        output_str += f"async def init_max_id_handler(document):\n"
        output_str += f'    max_val = await document.find_all().max("_id")\n'
        output_str += f'    document.init_max_id(int(max_val) if max_val is not None else 0)\n\n\n'
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        output_str += f'    await init_db()\n'
        for message in self.custom_id_primary_key_messages:
            message_name = message.proto.name
            output_str += f"    await init_max_id_handler({message_name})\n"
        output_str += "\n\n"
        output_str += "if os.getenv('DEBUG'):\n"
        output_str += "    from fastapi.middleware.cors import CORSMiddleware\n\n"
        output_str += "    origins = ['*']\n"
        output_str += f"    {self.fastapi_app_name}.add_middleware(\n"
        output_str += f"        CORSMiddleware,\n"
        output_str += f"        allow_origins=origins,\n"
        output_str += f"        allow_credentials=True,\n"
        output_str += f"        allow_methods=['*'],\n"
        output_str += f"        allow_headers=['*'],\n"
        output_str += f"    )\n\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'
        output_str += f"from fastapi.staticfiles import StaticFiles\n\n"
        output_str += f"{self.fastapi_app_name}.mount('/static', StaticFiles(directory='static'), name='static')\n\n"
        return output_str

    def _underlying_handle_generic_imports(self) -> str:
        generic_beanie_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                        "generic_routes")
        output_str = f'from {generic_beanie_routes_file_path} import generic_read_http, ' + "\\\n" \
                     f'\tgeneric_post_http, generic_read_by_id_http, generic_put_http, ' \
                     f'generic_patch_http, \\\n\tgeneric_delete_http, generic_index_http, \\\n\t' \
                     f'generic_read_by_id_ws, generic_read_ws\n'
        return output_str

    def _handle_model_imports(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            output_str += ", "
            output_str += f"{message.proto.name}Optional, "
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
        output_str = f"from {callback_override_set_instance_file_path} import app_launch_pre, app_launch_post\n"
        output_str += "# below import is to set derived callback's instance if implemented in the script\n"
        callback_override_set_instance_file_path = ".".join(callback_override_set_instance_file_path.split(".")[:-1])
        output_str += f"from {callback_override_set_instance_file_path} import " \
                      f"{self.callback_override_set_instance_file_name}\n"
        return output_str

    def handle_run_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "import uvicorn\n"
        output_str += self._handle_callback_override_set_instance_import()
        output_str += f"from FluxPythonUtils.scripts.utility_functions import configure_logger\n\n"
        output_str += f'configure_logger(os.getenv("LOG_LEVEL"), log_file_name=os.getenv("LOG_FILE_PATH"))\n'
        output_str += "\n\n"
        output_str += f'def launch_{self.launch_file_name.split(".")[0]}():\n'
        output_str += f'    app_launch_pre()\n'
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
        output_str += f'                app="{self.main_file_name}:{self.fastapi_app_name}", \n'
        output_str += f'                log_level=20)\n'
        output_str += f'    app_launch_post()\n'
        return output_str

    def set_req_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.database_file_name = f"{self.proto_file_name}_beanie_database"
        self.main_file_name = f"{self.proto_file_name}_beanie_main"
        self.model_file_name = f'{self.proto_file_name}_beanie_model'
        self.routes_file_name = f'{self.proto_file_name}_beanie_routes'
        self.launch_file_name = self.proto_file_name + "_" + self.output_file_name_suffix
        self.client_file_name = f"{self.proto_file_name}_beanie_web_client"
        self.routes_callback_class_name = f"{self.proto_file_name}_beanie_routes_callback"
        routes_callback_class_name_camel_cased: str = self.convert_to_camel_case(self.routes_callback_class_name)
        self.routes_callback_class_name_capital_camel_cased: str = \
            routes_callback_class_name_camel_cased[0].upper() + routes_callback_class_name_camel_cased[1:]
        self.callback_override_set_instance_file_name = "beanie_callback_override_set_instance"

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.set_req_data_members(file)

        output_dict: Dict[str, str] = {
            # Adding project´s database.py
            self.database_file_name+".py": self.handle_database_file_gen(),

            # Adding project´s main.py
            self.main_file_name+".py": self.handle_main_file_gen(),

            # Adding route's callback class
            self.routes_callback_class_name + ".py": self.handle_callback_class_file_gen(),

            # Adding callback override set_instance file
            self.callback_override_set_instance_file_name + ".py":
                self.handle_callback_override_set_instance_file_gen(),

            # Adding callback override class file
            self.routes_callback_class_name + "_override.py": self.handle_callback_override_file_gen(),

            # Adding project's routes.py
            self.routes_file_name+".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.launch_file_name: self.handle_run_file_gen(),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen()
        }

        return output_dict


if __name__ == "__main__":
    main(BeanieFastApiClassGenPlugin)
