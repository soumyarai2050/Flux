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
        self.api_router_app_name = ""
        self.app_is_router: bool = True
        self.proto_file_name: str = ""
        self.proto_file_package: str = ""
        self.database_file_name: str = ""
        self.main_file_name: str = ""
        self.model_file_name: str = ""
        self.routes_file_name: str = ""
        self.custom_id_primary_key_messages: List[protogen.Message] = []
        self.response_field_case_style: str = os.getenv("RESPONSE_FIELD_CASE_STYLE")
        self.websocket_client_file_name: str = ""

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

    def handle_POST_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
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
        output_str += f"    return await generic_beanie_post_http({message.proto.name}, {message_name_snake_cased})\n"
        return output_str

    def handle_GET_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
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
        output_str += f"    return await generic_beanie_read_by_id_http({message.proto.name}, {message_name_snake_cased}_id)\n"
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}/' + f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: {message.proto.name}) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_beanie_put_http({message.proto.name}, {message_name_snake_cased}_updated)\n"
        return output_str

    def handle_PATCH_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}/' + f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: {message.proto.name}Optional) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_beanie_patch_http({message.proto.name}, {message_name_snake_cased}_updated)\n"
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + '{'+f'{message_name_snake_cased}_id'+'}' + f'", response_model=DefaultWebResponse, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def delete_{message_name_snake_cased}_http({message_name_snake_cased}_id: {id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def delete_{message_name_snake_cased}_http({message_name_snake_cased}_id: PydanticObjectId) -> DefaultWebResponse:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_beanie_delete_http({message.proto.name}, " \
                      f"{message.proto.name}BaseModel, {message_name_snake_cased}_id)\n"
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message.proto.name)
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-{field_name}/' + \
                     '{' + f'{field_name}' + '}' + f'", response_model=List[{message.proto.name}], status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_from_{field_name}_http({field_name}: {field_type}) -> " \
                      f"List[{message.proto.name}]:\n"
        output_str += f'    """ Index for {field_name} field of {message.proto.name} """\n'
        output_str += f"    return await generic_beanie_index_http({message.proto.name}, " \
                      f"{message.proto.name}.{field_name}, {field_name})\n"
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
        output_str += f"    await generic_beanie_read_by_id_ws(websocket, " \
                      f"{message_name}, {message_name_snake_cased}_id)\n"
        return output_str

    def handle_read_all_WEBSOCKET_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/get-all-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def read_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        output_str += f'    """ Get All {message_name} using websocket """\n'
        output_str += f"    await generic_beanie_read_ws(websocket, {message_name})\n\n\n"
        return output_str

    def handle_update_WEBSOCKET_gen(self, message: protogen.Message, method_desc: str, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/update-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def update_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc } """\n'
        output_str += f"    await generic_beanie_update_ws(websocket, {message_name})\n"
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
        output_str += f"    return await generic_beanie_read_http({message.proto.name})\n\n\n"
        return output_str

    def handle_CRUD_for_message(self, message: protogen.Message) -> str:
        options_list_of_dict = self.get_complex_msg_option_values_as_list_of_dict(message, BeanieFastApiClassGenPlugin.flux_msg_json_root)

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

        id_field_type: str | None = None
        if message in self.custom_id_primary_key_messages:
            for field in message.fields:
                if field.proto.name == BeanieFastApiClassGenPlugin.default_id_field_name:
                    id_field_type = self.proto_to_py_datatype(field)
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field

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
        output_str += f'    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")\n'
        output_str += f'    await init_beanie(\n'
        output_str += f'              database=client.{self.proto_file_package},\n'
        output_str += f'              document_models=[{model_names}]\n'
        output_str += f'              )\n'
        return output_str

    def handle_database_file_gen(self) -> str:
        output_str = "from beanie import init_beanie\n"
        output_str += "import motor\n"
        output_str += "import motor.motor_asyncio\n"

        output_str += f'from {self.model_file_name} import '
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
        output_str += f"from {self.routes_file_name} import {self.api_router_app_name}\n"
        output_str += f"from {self.model_file_name} import "
        for message in self.custom_id_primary_key_messages:
            output_str += message.proto.name
            if message != self.custom_id_primary_key_messages[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        output_str += f"from {self.database_file_name} import init_db\n\n\n"
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
        generic_beanie_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_beanie_routes")
        output_str = f'from {generic_beanie_routes_file_path} import generic_beanie_read_http, ' + "\\\n" \
                     f'\tgeneric_beanie_post_http, generic_beanie_read_by_id_http, generic_beanie_put_http, ' \
                     f'generic_beanie_patch_http, \\\n\tgeneric_beanie_delete_http, generic_beanie_index_http, \\\n\t' \
                     f'generic_beanie_read_by_id_ws, generic_beanie_read_ws\n'
        return output_str

    def handle_routes_file_gen(self) -> str:
        output_str = "from fastapi import APIRouter, Request, WebSocket\n"
        output_str += "from fastapi.templating import Jinja2Templates\n"
        output_str += "from typing import List\n"
        output_str += f"from {self.model_file_name} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            output_str += ", "
            output_str += f"{message.proto.name}Optional, "
            output_str += f"{message.proto.name}BaseModel"
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        output_str += self._underlying_handle_generic_imports()
        incremental_id_basemodel_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                      "incremental_id_basemodel")
        if self.response_field_case_style.lower() == "camel":
            output_str += f'from {incremental_id_basemodel_path} import to_camel\n'
        # else not required: if response type is not camel type then avoid import
        default_web_response_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "default_web_response")
        output_str += f'from {default_web_response_file_path} import DefaultWebResponse\n'
        output_str += f"from beanie import PydanticObjectId\n\n\n"
        output_str += f"{self.api_router_app_name} = APIRouter()\n\n\n"
        output_str += self.handle_CRUD_task()
        output_str += "\n\ntemplates = Jinja2Templates(directory='templates')\n\n"
        output_str += f"@{self.api_router_app_name}.get('/')\n"
        output_str += "async def serve_spa(request: Request):\n"
        output_str += "    return templates.TemplateResponse('index.html', {'request': request})\n"
        return output_str

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

        id_field_type: str | None = None
        if message in self.custom_id_primary_key_messages:
            for field in message.fields:
                if field.proto.name == BeanieFastApiClassGenPlugin.default_id_field_name:
                    id_field_type = self.proto_to_py_datatype(field)
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field

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

    def handle_client_file_gen(self) -> str:
        generic_web_client_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_web_client")
        output_str = f'from {generic_web_client_path} import generic_http_get_all_client, ' + "\\\n" \
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
        output_str += f'from typing import Dict, List, Callable\n'
        output_str += "\n\n"
        for message in self.root_message_list:
            output_str += self.handle_client_methods(message)
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
        self.websocket_client_file_name = f'{self.proto_file_name}_websocket_client'
        self.client_file_name = f"{self.proto_file_name}_pydantic_web_client"

    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.set_req_data_members(file)

        output_dict: Dict[str, str] = {
            # Adding project´s database.py
            self.database_file_name+".py": self.handle_database_file_gen(),

            # Adding project´s main.py
            self.main_file_name+".py": self.handle_main_file_gen(),

            # Adding project's routes.py
            self.routes_file_name+".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.proto_file_name+"_"+self.output_file_name_suffix: self.handle_run_file_gen(),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen()
        }

        return output_dict


if __name__ == "__main__":
    main(BeanieFastApiClassGenPlugin)
