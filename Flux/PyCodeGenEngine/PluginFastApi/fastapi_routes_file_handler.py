import os
import time
from abc import ABC
from typing import List, Tuple
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiRoutesFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def _handle_routes_callback_import(self) -> str:
        routes_callback_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_callback_class_name)
        output_str = f"from {routes_callback_path} import {self.routes_callback_class_name_capital_camel_cased}\n"
        return output_str

    def _handle_routes_callback_instantiate(self):
        output_str = f"callback_class = {self.routes_callback_class_name_capital_camel_cased}.get_instance()\n\n\n"
        return output_str

    def _handle_model_imports(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import {BaseFastapiPlugin.default_id_type_var_name}, " \
                     f"{BaseFastapiPlugin.proto_package_var_name}, "
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

    def _underlying_handle_generic_imports(self) -> str:
        generic_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_routes")
        output_str = f'from {generic_routes_file_path} import generic_post_http, ' + "\\\n"\
                     f'\tgeneric_put_http, generic_patch_http, generic_delete_http, ' \
                     f'generic_index_http, \\\n\tgeneric_read_http, generic_read_ws, ' \
                     f'generic_read_by_id_http, generic_read_by_id_ws\n'
        return output_str

    def handle_POST_gen(self, message: protogen.Message, method_desc: str | None = None,
                        id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
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
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                     f'{message_name_snake_cased}_id' + '}' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> {message.proto.name}:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{BaseFastapiPlugin.default_id_type_var_name}) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    callback_class.read_by_id_{message_name_snake_cased}_pre({message_name_snake_cased}_id)\n"
        filter_list = self._get_list_from_filter_option(message)
        if filter_list:
            output_str += f"    {message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                          f"{message.proto.name}, {message_name_snake_cased}_id, {filter_list})\n"
        else:
            output_str += f"    {message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                          f"{message.proto.name}, {message_name_snake_cased}_id)\n"

        output_str += f"    callback_class.read_by_id_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, method_desc: str | None = None,
                       id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                      f"{message.proto.name}, {message_name_snake_cased}_updated.id)\n"
        output_str += f"    callback_class.update_{message_name_snake_cased}_pre(" \
                      f"stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
        filter_list = self._get_list_from_filter_option(message)
        if filter_list:
            output_str += f"    updated_{message_name_snake_cased}_obj = await generic_put_http(" \
                          f"{message.proto.name}, stored_{message_name_snake_cased}_obj, " \
                          f"{message_name_snake_cased}_updated, {filter_list})\n"
        else:
            output_str += f"    updated_{message_name_snake_cased}_obj = await generic_put_http(" \
                          f"{message.proto.name}, stored_{message_name_snake_cased}_obj, " \
                          f"{message_name_snake_cased}_updated)\n"
        output_str += f"    callback_class.update_{message_name_snake_cased}_post(" \
                      f"stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
        output_str += f"    return updated_{message_name_snake_cased}_obj\n"
        return output_str

    def handle_PATCH_gen(self, message: protogen.Message, method_desc: str | None = None,
                         id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}Optional) -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                      f"{message.proto.name}, {message_name_snake_cased}_updated.id)\n"
        output_str += f"    callback_class.partial_update_{message_name_snake_cased}_pre(" \
                      f"stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
        filter_list = self._get_list_from_filter_option(message)
        if filter_list:
            output_str += f"    updated_{message_name_snake_cased}_obj =  await generic_patch_http(" \
                          f"{message.proto.name}, stored_{message_name_snake_cased}_obj, " \
                          f"{message_name_snake_cased}_updated, {filter_list})\n"
        else:
            output_str += f"    updated_{message_name_snake_cased}_obj =  await generic_patch_http(" \
                          f"{message.proto.name}, stored_{message_name_snake_cased}_obj, " \
                          f"{message_name_snake_cased}_updated)\n"

        output_str += f"    callback_class.partial_update_{message_name_snake_cased}_post(" \
                      f"stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
        output_str += f"    return updated_{message_name_snake_cased}_obj\n"
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, method_desc: str | None = None,
                          id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                     '{'+f'{message_name_snake_cased}_id'+'}' + \
                     f'", response_model=DefaultWebResponse, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id: {id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id: {BaseFastapiPlugin.default_id_type_var_name}) -> DefaultWebResponse:\n"
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
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
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
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/get-{message_name_snake_cased}-ws/' + \
                     '{' + f'{message_name_snake_cased}_id' + '}")\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                          f"{message_name_snake_cased}_id: {id_field_type}) -> None:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                          f"{message_name_snake_cased}_id: {BaseFastapiPlugin.default_id_type_var_name}) -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc } """\n'
        output_str += f"    callback_class.read_by_id_ws_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_id)\n"
        filter_list = self._get_list_from_filter_option(message)
        if filter_list:
            output_str += f"    await generic_read_by_id_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                          f"{message_name}, {message_name_snake_cased}_id, {filter_list})\n"
        else:
            output_str += f"    await generic_read_by_id_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                          f"{message_name}, {message_name_snake_cased}_id)\n"
        output_str += f"    callback_class.read_by_id_ws_{message_name_snake_cased}_post()\n"
        return output_str

    def handle_read_all_WEBSOCKET_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/get-all-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def read_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        output_str += f'    """ Get All {message_name} using websocket """\n'
        output_str += f"    callback_class.read_all_ws_{message_name_snake_cased}_pre()\n"
        filter_list = self._get_list_from_filter_option(message)
        if filter_list:
            output_str += f"    await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                          f"{message_name}, {filter_list})\n"
        else:
            output_str += f"    await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                          f"{message_name})\n"
        output_str += f"    callback_class.read_all_ws_{message_name_snake_cased}_post()\n\n\n"
        return output_str

    def handle_update_WEBSOCKET_gen(self, message: protogen.Message, method_desc: str, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/update-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def update_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc } """\n'
        output_str += f"    await generic_update_ws(websocket, {message_name})\n"
        return output_str

    def handle_field_web_socket_gen(self, message: protogen.Message, field: protogen.Field):
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
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
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}/' + \
                     f'", response_model=List[{message.proto.name}], status_code=200)\n'
        output_str += f"async def read_{message_name_snake_cased}_http() -> List[{message.proto.name}]:\n"
        output_str += f'    """\n'
        output_str += f'    Get All {message.proto.name}\n'
        output_str += f'    """\n'
        output_str += f"    callback_class.read_all_{message_name_snake_cased}_pre()\n"
        filter_list = self._get_list_from_filter_option(message)
        if filter_list:
            output_str += f"    obj_list = await generic_read_http({message.proto.name}, {filter_list})\n"
        else:
            output_str += f"    obj_list = await generic_read_http({message.proto.name})\n"
        output_str += f"    callback_class.read_all_{message_name_snake_cased}_post(obj_list)\n"
        output_str += f"    return obj_list\n\n\n"
        return output_str

    def _get_list_from_filter_option(self, message: protogen.Message) -> List[Tuple[str | bool, ...]]:
        filter_list = []
        filter_option_val_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_nested_fld_val_filter_param)
        for filter_option_dict in filter_option_val_list_of_dict:
            temp_list = []
            if "field_name" in filter_option_dict:
                field_name = filter_option_dict["field_name"]
                temp_list.append(field_name)
                if "bool_val_filters" in filter_option_dict:
                    if not isinstance(filter_option_dict["bool_val_filters"], list):
                        filter_option_dict["bool_val_filters"] = [filter_option_dict["bool_val_filters"]]
                    # else not required: if filter_option_dict["bool_val_filters"] already os list type then
                    # avoiding type-casting
                    temp_list.extend(filter_option_dict["bool_val_filters"])
                elif "string_val_filters" in filter_option_dict:
                    if not isinstance(filter_option_dict["string_val_filters"], list):
                        filter_option_dict["string_val_filters"] = [filter_option_dict["string_val_filters"]]
                    # else not required: if filter_option_dict["string_val_filters"] already os list type then
                    # avoiding type-casting
                    temp_list.extend(filter_option_dict["string_val_filters"])
                else:
                    err_str = f"No valid val_filter option field found in filter option for filter field: {field_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)

                filter_list.append(tuple(temp_list))

            else:
                err_str = f"No filter field_name key found in filter option: {filter_option_val_list_of_dict}"
                logging.exception(err_str)
                raise Exception(err_str)

        return filter_list

    def handle_POST_query_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.post("/query-create-{message_name_snake_cased}' + \
                     f'", response_model={message.proto.name}, status_code=201)\n'
        output_str += f"async def create_{message_name_snake_cased}_query_http() -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    {message_name_snake_cased}_obj = await callback_class.create_{message_name_snake_cased}_query_pre({message.proto.name})\n"
        output_str += f"    await callback_class.create_{message_name_snake_cased}_query_post({message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_GET_query_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.get("/query-get-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def read_{message_name_snake_cased}_by_id_query_http() -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    {message_name_snake_cased}_obj = await callback_class.read_by_id_{message_name_snake_cased}_" \
                      f"query_pre({message.proto.name})\n"
        output_str += f"    await callback_class.read_by_id_{message_name_snake_cased}_query_post(" \
                      f"{message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_PUT_query_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.put("/query-put-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}_query_http() -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    {message_name_snake_cased}_obj = await callback_class.update_{message_name_snake_cased}_query_pre" \
                      f"({message.proto.name})\n"
        output_str += f"    await callback_class.update_{message_name_snake_cased}_query_post({message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_PATCH_query_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.patch("/query-patch-{message_name_snake_cased}/' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}_query_http() -> {message.proto.name}:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    {message_name_snake_cased}_obj = await callback_class.partial_update_" \
                      f"{message_name_snake_cased}_query_pre({message.proto.name})\n"
        output_str += f"    await callback_class.partial_update_{message_name_snake_cased}_query_post(" \
                      f"{message_name_snake_cased}_obj)\n"
        output_str += f"    return {message_name_snake_cased}_obj\n"
        return output_str

    def handle_DELETE_query_gen(self, message: protogen.Message, method_desc: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.delete("/query-delete-{message_name_snake_cased}/' + \
                     '{'+f'{message_name_snake_cased}_id'+'}' + \
                     f'", response_model=DefaultWebResponse, status_code=200)\n'
        output_str += f"async def delete_{message_name_snake_cased}_query_http() -> DefaultWebResponse:\n"
        if method_desc:
            output_str += f'    """\n'
            output_str += f'    {method_desc}\n'
            output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        output_str += f"    delete_web_resp = await callback_class.delete_{message_name_snake_cased}_query_pre(" \
                      f"{message.proto.name})\n"
        output_str += f"    await callback_class.delete_{message_name_snake_cased}_query_post(delete_web_resp)\n"
        output_str += f"    return delete_web_resp\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_query_gen(self, message: protogen.Message, method_desc: str):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/query-get-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def read_{message_name_snake_cased}_by_id_query_ws() -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc } """\n'
        output_str += f"    callback_class.read_by_id_ws_{message_name_snake_cased}_pre({message_name})\n"
        output_str += f"    callback_class.read_by_id_ws_{message_name_snake_cased}_post()\n"
        return output_str

    def _handle_routes_methods(self, message: protogen.Message) -> str:
        output_str = ""
        crud_field_name_to_method_call_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: self.handle_POST_gen,
            BaseFastapiPlugin.flux_json_root_read_field: self.handle_GET_gen,
            BaseFastapiPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            BaseFastapiPlugin.flux_json_root_patch_field: self.handle_PATCH_gen,
            BaseFastapiPlugin.flux_json_root_delete_field: self.handle_DELETE_gen,
            BaseFastapiPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_gen,
            BaseFastapiPlugin.flux_json_root_update_websocket_field: self.handle_update_WEBSOCKET_gen
        }

        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message, BaseFastapiPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        output_str += self.handle_get_all_message_request(message)
        output_str += self.handle_read_all_WEBSOCKET_gen(message)

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                method_desc: str = option_dict[crud_option_field_name]
                output_str += crud_operation_method(message, method_desc, id_field_type)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index):
                output_str += self.handle_index_req_gen(message, field)
            # else not required: Avoiding field if index option is not enabled

            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_web_socket):
                output_str += self.handle_field_web_socket_gen(message, field)
            # else not required: Avoiding field if websocket option is not enabled
        return output_str

    def _handle_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        crud_field_name_to_method_call_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: self.handle_POST_query_gen,
            BaseFastapiPlugin.flux_json_root_read_field: self.handle_GET_query_gen,
            BaseFastapiPlugin.flux_json_root_update_field: self.handle_PUT_query_gen,
            BaseFastapiPlugin.flux_json_root_patch_field: self.handle_PATCH_query_gen,
            BaseFastapiPlugin.flux_json_root_delete_field: self.handle_DELETE_query_gen,
            BaseFastapiPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_query_gen,
        }

        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message, BaseFastapiPlugin.flux_msg_json_query)

        # Since json_query option is of non-repeated type
        option_dict = options_list_of_dict[0]

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                method_desc: str = option_dict[crud_option_field_name]
                output_str += crud_operation_method(message, method_desc)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option
        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            if BaseFastapiPlugin.flux_msg_json_root in str(message.proto.options):
                output_str += self._handle_routes_methods(message)

            if BaseFastapiPlugin.flux_msg_json_query in str(message.proto.options):
                output_str += self._handle_query_methods(message)

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
