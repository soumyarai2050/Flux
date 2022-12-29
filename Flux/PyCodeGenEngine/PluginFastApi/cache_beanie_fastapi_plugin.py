#!/usr/bin/env python
import os
import logging
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.beanie_fastapi_plugin import \
    BeanieFastApiPlugin, main


# Todo: Might be broken due to changes made in cache and beanie fastapi


class CacheBeanieFastApiPlugin(BeanieFastApiPlugin):
    """
    Plugin script to generate Hybrid-Beanie enabled fastapi app
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_POST_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + f'", response_model={message_name}, status_code=201)\n'
        output_str += f"async def create_{message_name_snake_cased}({message_name_snake_cased}: {message_name}) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_cache_beanie_post({message_name}, {message_name_snake_cased})\n"
        return output_str

    def handle_GET_gen(self, message: protogen.Message, method_desc: str | None = None,
                       id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + \
                     '{' + f'{message_name_snake_cased}_id' + '}' + \
                     f'", response_model={message_name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> {message_name}:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"PydanticObjectId) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_cache_beanie_get({message_name}, {message_name_snake_cased}_id)\n"
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                     f'", response_model={message_name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}({message_name_snake_cased}_updated: " \
                      f"{message_name}) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_cache_beanie_put({message_name}, {message_name_snake_cased}_updated)\n"
        return output_str

    def handle_PATCH_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}' + \
                     f'", response_model={message_name}, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}({message_name_snake_cased}_updated: " \
                      f"{message_name}Optional) -> {message_name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_cache_beanie_patch({message_name}, {message_name_snake_cased}_updated)\n"
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None, id_field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                     '{'+f'{message_name_snake_cased}_id'+'}' + \
                     f'", response_model=DefaultWebResponse, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def delete_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def delete_{message_name_snake_cased}({message_name_snake_cased}_id: " \
                          f"PydanticObjectId) -> DefaultWebResponse:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    return await generic_cache_beanie_delete({message_name}, {message_name_snake_cased}_id)\n"
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, field: protogen.Field) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-{field_name}/' + \
                     '{' + f'{field_name}' + '}' + f'", response_model=List[{message_name}], status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_from_{field_name}({field_name}: {field_type}) -> " \
                      f"List[{message_name}]:\n"
        output_str += f'    """ Index for {field_name} field of {message.proto.name} """\n'
        output_str += f"    return await generic_cache_beanie_index({message_name}, '{field_name}', {field_name})\n"
        return output_str

    def handle_get_all_message_request(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}/' + \
                     f'", response_model=List[{message_name}], status_code=200)\n'
        output_str += f"async def get_all_{message_name_snake_cased}() -> List[{message_name}]:\n"
        output_str += f'    """\n'
        output_str += f'    Get All {message_name}\n'
        output_str += f'    """\n'
        output_str += f"    return await generic_cache_beanie_get_all({message_name})\n"
        output_str += f"\n\n"
        return output_str

    def handle_fastapi_initialize_file_gen(self) -> str:
        output_str = "import logging\n"
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
        output_str += f'    document.init_max_id(int(max_val) if max_val is not None else 0)\n'
        output_str += f'    all_objs = await document.find_all().to_list()\n'
        output_str += f'    for obj in all_objs:\n'
        output_str += f'        success = document.add_data_in_cache(obj.id, obj)\n'
        output_str += f'        if not success:\n'
        output_str += '            err_str = f"{obj.id} already found in cache dict while loading ' \
                      'in cache before connect"\n'
        output_str += f'            logging.exception(err_str)\n'
        output_str += f'            raise Exception(err_str)\n\n\n'
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        output_str += f'    await init_db()\n'
        for message in self.custom_id_primary_key_messages:
            message_name = message.proto.name
            output_str += f"    await init_max_id_handler({message_name})\n"
        output_str += "\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'

        return output_str

    def _underlying_handle_generic_imports(self) -> str:
        generic_beanie_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                        "generic_cache_beanie_routes")
        output_str = f'from {generic_beanie_routes_file_path} import generic_cache_beanie_get_all, ' + "\\\n" \
                     f'\tgeneric_cache_beanie_post, generic_cache_beanie_get, generic_cache_beanie_put, ' \
                     f'generic_cache_beanie_patch, \\\n\tgeneric_cache_beanie_delete, generic_cache_beanie_index\n'
        return output_str

    def set_req_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.database_file_name = f"{self.proto_file_name}_cached_beanie_database"
        self.main_file_name = f"{self.proto_file_name}_cached_beanie_main"
        self.model_file_name = f'{self.proto_file_name}_beanie_model'
        self.routes_file_name = f'{self.proto_file_name}_cached_beanie_routes'


if __name__ == "__main__":
    main(CacheBeanieFastApiPlugin)
