import os
import time
from typing import List, Dict, Tuple
import json
from abc import ABC
import logging
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiCallbackOverrideFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.json_sample_loaded_json: Dict | None = None

    def _handle_field_data_manipulation(self, json_content: Dict, message: protogen.Message, id_str: str | None = None,
                                        get_all_fields: bool | None = None, specify_message_name: str | None = None,
                                        is_repeated: bool | None = None):
        if get_all_fields is not None and get_all_fields:
            temp_str = ""
            for field in message.fields:
                if BaseFastapiPlugin.default_id_field_name == field.proto.name:
                    temp_str += f"{field.proto.name}={id_str}"
                else:
                    if specify_message_name is None:
                        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
                        field_val = json_content[message_name_snake_cased][field.proto.name]
                    else:
                        # message_name_snake_cased = convert_camel_case_to_specific_case(specify_message_name)
                        if is_repeated:
                            field_val = json_content[0][field.proto.name]
                        else:
                            field_val = json_content[field.proto.name]
                    if isinstance(field_val, str):
                        field_val = f'"{field_val}"'
                    elif field_val == 'true' or field_val == 'false':
                        field_val = True if field_val == 'true' else False
                    # else not required: else using value as is
                    if field == message.fields[0]:
                        temp_str += f"{field.proto.name}={field_val}"
                    else:
                        temp_str += f", {field.proto.name}={field_val}"
            return temp_str
        else:
            for field in message.fields:
                if BaseFastapiPlugin.default_id_field_name != field.proto.name:
                    match field.kind.name.lower():
                        case "int32" | "int64" | "float":
                            if self.is_option_enabled(field, BaseFastapiPlugin.flux_fld_val_is_datetime):
                                return f'{field.proto.name} = DateTime.utcnow()'
                            else:
                                return f"{field.proto.name} += 10"
                        case "string":
                            return f'{field.proto.name} = "test_str"'
                        case "bool":
                            return f"{field.proto.name} = True"
                        case "message":
                            message_name_case_styled = convert_camel_case_to_specific_case(message.proto.name)
                            is_repeated = field.cardinality.name.lower() == "repeated"
                            return f"{field.proto.name} = {field.message.proto.name}(" \
                                   f"{self._handle_field_data_manipulation(json_content.get(message_name_case_styled).get(field.proto.name), field.message, get_all_fields=True, specify_message_name=field.proto.name, is_repeated=is_repeated)})"
                # else not required: field must not be id to be manipulated in this method's use case
            else:
                err_str = f"Can't find any non-complex type field in this message: {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)

    def _handle_import_n_pre_exec_code_str(self, required_root_msg_list: List[protogen.Message]) -> str:
        output_str = "from typing import List, Type\n"
        output_str += "import threading\n"
        output_str += "import logging\n"
        output_str += "import asyncio\n"
        output_str += "from pendulum import DateTime\n"
        output_str += "from fastapi import HTTPException\n"
        output_str += "\n"
        output_str += "# project imports\n"
        web_client_path = \
            self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", f"{self.client_file_name}")
        web_client_name_caps_camel_cased = convert_to_capitalized_camel_case(self.client_file_name)
        output_str += f"from {web_client_path} import {web_client_name_caps_camel_cased}\n"
        model_path = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_path} import *\n"
        routes_callback = \
            self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", f"{self.routes_callback_class_name}")
        callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {routes_callback} import " \
                      f"{callback_class_name_camel_cased}\n\n"
        output_str += "# Example uses 2 webclients of same service working on different port numbers to show "
        output_str += "# in some examples how can one service communicate to other (Practically other client must "
        output_str += "# be of another service not of same)\n"
        output_str += f"{self.proto_file_name}_web_client_internal = " \
                      f"{web_client_name_caps_camel_cased}()\n"
        output_str += f"{self.proto_file_name}_web_client_external = " \
                      f"{web_client_name_caps_camel_cased}(port=8080)\n\n\n"
        output_str += f"class WsGet{required_root_msg_list[0].proto.name}ByIdCallback:\n"
        output_str += f"    def __call__(self, " \
                      f"{convert_camel_case_to_specific_case(required_root_msg_list[0].proto.name)}_base_model: " \
                      f"{required_root_msg_list[0].proto.name}BaseModel):\n"
        output_str += f'        logging.debug(f"callback function: {required_root_msg_list[0].proto.name} from DB: ' + '{' + \
                      f'{convert_camel_case_to_specific_case(required_root_msg_list[0].proto.name)}_base_model' + \
                      '}")\n\n\n'
        output_str += f"class WsGet{required_root_msg_list[0].proto.name}Callback:\n"
        output_str += f"    def __call__(self, " \
                      f"{convert_camel_case_to_specific_case(required_root_msg_list[0].proto.name)}_base_model_list: " \
                      f"List[{required_root_msg_list[0].proto.name}BaseModel]):\n"
        output_str += f'        logging.debug(f"callback function: {required_root_msg_list[0].proto.name} List from DB: ' \
                      + '{' + f'{convert_camel_case_to_specific_case(required_root_msg_list[0].proto.name)}_base_model_list'\
                      + '}")\n\n\n'
        return output_str

    def _handle_callback_example_0(self, callback_class_name_camel_cased,
                                   callback_override_class_name_camel_cased) -> str:
        output_str = f"class {callback_override_class_name_camel_cased}(" \
                      f"{callback_class_name_camel_cased}):\n\n"
        output_str += f"    def __init__(self):\n"
        output_str += f"        super().__init__()\n\n"
        output_str += f"    # Example 0 of 5: pre- and post-launch server\n"
        output_str += f"    def app_launch_pre(self):\n"
        output_str += f'        logging.debug("Triggered server launch pre override")\n\n'
        output_str += f"    def app_launch_post(self):\n"
        output_str += f'        logging.debug("Triggered server launch post override")\n\n'
        return output_str

    def _handle_callback_example_1(self, first_msg_name: str, first_msg_name_snake_cased: str,
                                   json_sample_content, required_root_msg: List[protogen.Message]) -> str:
        output_str = f"    # Example 1 of 5: intercept web calls via callback example\n"
        output_str += f"    async def create_{first_msg_name_snake_cased}_pre(self, " \
                      f"{first_msg_name_snake_cased}_obj: {first_msg_name}):\n"
        output_str += f'        logging.debug(f"{first_msg_name} From Ui: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n'
        output_str += f'        {first_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, required_root_msg[0])}\n'
        output_str += f'        logging.debug(f"{first_msg_name} pre test: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        output_str += f'    async def create_{first_msg_name_snake_cased}_post(self, ' \
                      f'{first_msg_name_snake_cased}_obj: {first_msg_name}):\n'
        output_str += f'        logging.debug(f"{first_msg_name} from DB: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n'
        output_str += f'        {first_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, required_root_msg[0])}\n'
        output_str += f'        logging.debug(f"{first_msg_name} Post test: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        return output_str

    def _handle_callback_example_2(self, first_msg_name: str, first_msg_name_snake_cased: str,
                                   json_sample_content, required_root_msg: List[protogen.Message]) -> str:
        output_str = f'    # Example 2 of 5: intercept web calls via callback and invoke another ' \
                      f'service on this very web server example\n'
        output_str += f'    def _http_create_{first_msg_name_snake_cased}_thread_func(self, obj):\n'
        field_str = self._handle_field_data_manipulation(json_sample_content, required_root_msg[0], "obj.id")
        output_str += f'        {first_msg_name_snake_cased}_obj = {first_msg_name}BaseModel({field_str})\n'
        output_str += f'        {first_msg_name_snake_cased}_obj = {self.proto_file_name}_web_client' \
                      f'_internal.create_{first_msg_name_snake_cased}_client({first_msg_name_snake_cased}_obj)\n'
        output_str += f'        logging.debug(f"Created {first_msg_name} obj from Another Document: ' + \
                      '{' + f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        main_msg = required_root_msg[1]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = convert_camel_case_to_specific_case(main_msg_name)
        output_str += f'    async def create_{main_msg_name_snake_cased}_pre(self, ' \
                      f'{main_msg_name_snake_cased}: {main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} from UI: ' + '{' + f'{main_msg_name_snake_cased}' + '}' + '")\n'
        output_str += f'        # To avoid deadlock triggering another thread to execute another document creation\n'
        output_str += f'        # This same implementation is required even in post\n'
        output_str += f'        new_thread = threading.Thread(target=self._http_create_{first_msg_name_snake_cased}' \
                      f'_thread_func, args=({main_msg_name_snake_cased},), daemon=True)\n'
        output_str += f'        new_thread.start()\n\n'
        output_str += f'    async def create_{main_msg_name_snake_cased}_post(self, {main_msg_name_snake_cased}: ' \
                      f'{main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} From Db: ' + '{' + f'{main_msg_name_snake_cased}' + '}' + '")\n'
        output_str += f'        {main_msg_name_snake_cased}.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, main_msg)}\n'
        output_str += f'        logging.debug(f"{main_msg_name} Post test: ' + \
                      '{' + f'{main_msg_name_snake_cased}' + '}' + '")\n\n'
        return output_str

    def _handle_callback_example_3(self, first_msg_name: str, first_msg_name_snake_cased: str,
                                   json_sample_content, required_root_msg: List[protogen.Message]) -> str:
        main_msg = required_root_msg[2]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = convert_camel_case_to_specific_case(main_msg_name)
        output_str = f'    # Example 3 of 5: intercept web calls via callback and invoke ' \
                      f'another service on different web server example\n'
        output_str += f'    async def create_{main_msg_name_snake_cased}_pre(self, ' \
                      f'{main_msg_name_snake_cased}_obj: {main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} from UI: ' + \
                      '{' + f'{main_msg_name_snake_cased}_obj' + '}' + '")\n'
        field_str = \
            self._handle_field_data_manipulation(json_sample_content, required_root_msg[0],
                                                 f"{main_msg_name_snake_cased}_obj.id")
        output_str += f'        {first_msg_name_snake_cased}_obj = {first_msg_name}BaseModel({field_str})\n'
        output_str += f'        {first_msg_name_snake_cased}_obj = {self.proto_file_name}_web_client_external.' \
                      f'create_{first_msg_name_snake_cased}_client({first_msg_name_snake_cased}_obj)\n'
        output_str += f'        logging.debug(f"Created {first_msg_name} obj from Another Document: ' + \
                      '{' + f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        output_str += f'    async def create_{main_msg_name_snake_cased}_post(self, ' \
                      f'{main_msg_name_snake_cased}_obj: {main_msg_name}):\n'
        output_str += f'        logging.debug(f"{main_msg_name} From Db: ' + \
                      '{' + f'{main_msg_name_snake_cased}_obj' + '}' + '")\n'
        output_str += f'        {main_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, main_msg)}\n'
        output_str += f'        logging.debug(f"{main_msg_name} Post test: ' + \
                      '{' + f'{main_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        return output_str

    def _handle_callback_example_4(self, first_msg_name: str, first_msg_name_snake_cased: str,
                                   required_root_msg: List[protogen.Message]) -> str:
        output_str = f'    # Example 4 of 5: intercept ws web calls via callback and ' \
                      f'invoke another service on this very web server example\n'
        output_str += f'    async def _ws_get_{first_msg_name_snake_cased}_by_id_thread_func(self, ' \
                      f'obj_id: int, ws_get_{first_msg_name_snake_cased}_by_id_callback):\n'
        output_str += f'        logging.debug("_ws_get_{first_msg_name_snake_cased}_by_id_thread_func: ' \
                      f'Connecting {first_msg_name_snake_cased} get_by_id ws:")\n'
        output_str += f'        await {self.proto_file_name}_web_client_internal.get_' \
                      f'{first_msg_name_snake_cased}_client_ws(obj_id, ws_get_{first_msg_name_snake_cased}' \
                      f'_by_id_callback)\n\n'
        main_msg = required_root_msg[3]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = convert_camel_case_to_specific_case(main_msg_name)
        output_str += f'    async def read_by_id_ws_{main_msg_name_snake_cased}_pre(self, obj_id: int):\n'
        output_str += f'        logging.debug(f"read_by_id_ws_{main_msg_name_snake_cased}_pre:' \
                      f' {main_msg_name} id from UI: ' + '{' + 'obj_id' + '}' + '")\n'
        output_str += f'        ws_get_{first_msg_name_snake_cased}_by_id_callback: ' \
                      f'WsGet{first_msg_name}ByIdCallback = WsGet{first_msg_name}ByIdCallback()\n'
        output_str += f'        # running await function is different from running normal function in threading\n'
        output_str += f'        new_thread = threading.Thread(target=asyncio.run, args=(self._ws_get_' \
                      f'{first_msg_name_snake_cased}_by_id_thread_func(obj_id, ws_get_{first_msg_name_snake_cased}' \
                      f'_by_id_callback),), daemon=True)\n'
        output_str += f'        new_thread.start()\n'
        output_str += f'    async def read_by_id_ws_{main_msg_name_snake_cased}_post(self):\n'
        output_str += f'        logging.debug(f"closing {main_msg_name_snake_cased} read ws ' \
                      f'in read_by_id_ws_{main_msg_name_snake_cased}_post")\n\n'
        return output_str

    def _handle_callback_example_5(self, first_msg_name: str, first_msg_name_snake_cased: str,
                                   required_root_msg: List[protogen.Message]) -> str:
        main_msg = required_root_msg[3]
        main_msg_name = main_msg.proto.name
        main_msg_name_snake_cased = convert_camel_case_to_specific_case(main_msg_name)
        output_str = f'    # Example 5 of 5: intercept ws web calls via callback and ' \
                      f'invoke another service on different web server example\n'
        output_str += f'    async def _ws_get_all_{first_msg_name_snake_cased}_thread_func(' \
                      f'self, ws_get_{first_msg_name_snake_cased}_callback):\n'
        output_str += f'        logging.debug("_ws_get_{first_msg_name_snake_cased}_by_id_thread_func: ' \
                      f'Connecting another server {first_msg_name_snake_cased} get_all ws:")\n'
        output_str += f'        await {self.proto_file_name}_web_client_external.get_all_' \
                      f'{first_msg_name_snake_cased}_client_ws(ws_get_{first_msg_name_snake_cased}_callback)\n\n'
        output_str += f'    async def read_all_ws_{main_msg_name_snake_cased}_pre(self):\n'
        output_str += f'        logging.debug(f"triggered read_all_ws_{main_msg_name_snake_cased}_pre")\n'
        output_str += f'        ws_get_{first_msg_name_snake_cased}_callback: WsGet{first_msg_name}Callback ' \
                      f'= WsGet{first_msg_name}Callback()\n'
        output_str += f'        # running await function is different from running normal function in threading\n'
        output_str += f'        new_thread = threading.Thread(target=asyncio.run, args=(self._ws_get_all_' \
                      f'{first_msg_name_snake_cased}_thread_func(ws_get_{first_msg_name_snake_cased}_callback),),' \
                      f' daemon=True)\n'
        output_str += f'        new_thread.start()\n\n'
        output_str += f'    async def read_all_ws_{main_msg_name_snake_cased}_post(self):\n'
        output_str += f'        logging.debug(f"closing {main_msg_name_snake_cased} read all ws in ' \
                      f'read_all_ws_{main_msg_name_snake_cased}_post")\n'
        return output_str

    def _handle_callback_query_example(self) -> str:
        output_str = ""
        if self.message_to_query_option_list_dict:
            output_str += f"\n"
            output_str += "    # Example: Soft API Query Interfaces\n"
            output_str += "    # Note: Some Queries may have import errors this is because not all queries have \n"
            output_str += "    # models in db, some are used to get processed data from db, so specific impl must \n"
            output_str += "    # be implemented in main callback override file present in app dir of project\n"
            output_str += f"\n"

        for message in self.message_to_query_option_list_dict:
            msg_name = message.proto.name
            msg_name_snake_cased = convert_camel_case_to_specific_case(msg_name)

            aggregate_value_list = self.message_to_query_option_list_dict[message]

            for aggregate_value in aggregate_value_list:
                query_name = aggregate_value[FastapiCallbackOverrideFileHandler.query_name_key]
                aggregate_var_name = aggregate_value[FastapiCallbackOverrideFileHandler.query_aggregate_var_name_key]
                query_params = aggregate_value[FastapiCallbackOverrideFileHandler.query_params_key]
                query_route_path = aggregate_value.get(FastapiCallbackOverrideFileHandler.query_route_type_key)
                if query_route_path is None:
                    query_route_path = "GET"

                routes_import_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.http_routes_file_name)
                aggregate_file_path = self.import_path_from_os_path("PROJECT_DIR", "app.aggregate")

                query_params_name_list = []
                if query_params:
                    for query_param_name, _ in query_params:
                        query_params_name_list.append(query_param_name)

                if query_route_path == FastapiCallbackOverrideFileHandler.flux_json_query_route_get_type_field_val:
                    if query_params:
                        agg_params_with_type_str = ", ".join([f"{param}: {param_type}"
                                                              for param, param_type in query_params])
                        agg_params_str = ", ".join(query_params_name_list)

                        output_str += f"    async def {query_name}_query_pre(self, {msg_name_snake_cased}_class_type: " \
                                      f"Type[{msg_name}], {agg_params_with_type_str}):\n"
                        if aggregate_var_name is not None:
                            output_str += f"        from {routes_import_path} import " \
                                          f"underlying_read_{msg_name_snake_cased}_http\n"
                            output_str += f"        from {aggregate_file_path} import {aggregate_var_name}\n"
                            output_str += f"        return await underlying_read_{msg_name_snake_cased}_http(" \
                                          f"{aggregate_var_name}({agg_params_str}))\n"
                        else:
                            output_str += f"        # To be implemented in main callback override file\n"
                            output_str += f"        return []\n"

                        output_str += "\n\n"
                    else:
                        output_str += f"    async def {query_name}_query_pre(self, {msg_name_snake_cased}_class_type: " \
                                      f"Type[{msg_name}]):\n"
                        if aggregate_var_name is not None:
                            output_str += f"        from {routes_import_path} import " \
                                          f"underlying_read_{msg_name_snake_cased}_http\n"
                            output_str += f"        from {aggregate_file_path} import {aggregate_var_name}\n"
                            output_str += f"        return await underlying_read_{msg_name_snake_cased}_http(" \
                                          f"{aggregate_var_name})\n"
                        else:
                            output_str += f"        # To be implemented in main callback override file\n"
                            output_str += f"        return []\n"
                        output_str += "\n"
                else:
                    if query_params:
                        output_str += f"    async def {query_name}_query_pre(self, {msg_name_snake_cased}_class_type: " \
                                      f"Type[{msg_name}], payload_dict: Dict[str, Any]):\n"
                        output_str += f"        # To be implemented in main callback override file\n"
                        output_str += f"        # payload_dict will contain all whole payload with key as set in " \
                                      f"proto model\n"
                        output_str += f"        return []\n"
                        output_str += "\n\n"
                    else:
                        err_str = f"patch query can't be generated without payload query_param, query {query_name} in " \
                                  f"message {message.proto.name} found without query params"
                        logging.exception(err_str)
                        raise Exception(err_str)

        # Projection handling
        projection_query_filter_func_req_query_name_n_message: List[Tuple[str, protogen.Message,
                                                                    Dict[str, Tuple[str, protogen.Field] |
                                                                              Dict[str, Tuple[str, protogen.Field]]]]] = []
        query_name_to_field_path_str_list_dict: Dict[str, List[str]] = {}
        for message in self.root_message_list:
            if FastapiCallbackOverrideFileHandler.is_option_enabled(
                    message, FastapiCallbackOverrideFileHandler.flux_msg_json_root_time_series):
                for field in message.fields:
                    if FastapiCallbackOverrideFileHandler.is_option_enabled(
                            field, FastapiCallbackOverrideFileHandler.flux_fld_projections):
                        break
                else:
                    # If no field is found having projection enabled
                    continue

                projection_val_to_fields_dict = (
                    FastapiCallbackOverrideFileHandler.get_projection_option_value_to_fields(message))
                projection_val_to_query_name_dict = (
                    FastapiCallbackOverrideFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(
                        message))
                meta_data_field_name_to_field_tuple_dict: Dict[str, Tuple[str, protogen.Field] |
                                                                    Dict[str, Tuple[str, protogen.Field]]] = (
                    self.get_meta_data_field_name_to_type_str_dict(message))
                for projection_option_val, query_name in projection_val_to_query_name_dict.items():
                    msg_name = message.proto.name
                    msg_name_snake_cased = convert_camel_case_to_specific_case(msg_name)
                    field_name_list: List[str] = []
                    field_name_set = projection_val_to_fields_dict[projection_option_val]
                    query_name_to_field_path_str_list_dict[query_name] = list(field_name_set)
                    for field_name in field_name_set:
                        if "." in field_name:
                            field_name_list.append("_".join(field_name.split(".")))
                        else:
                            field_name_list.append(field_name)
                    field_names_str = "_n_".join(field_name_list)
                    field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)

                    query_param_with_type_str = ""
                    for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                        if isinstance(meta_field_info, dict):
                            for nested_meta_field_name, nested_meta_field_info in meta_field_info.items():
                                meta_field_type_str, _ = nested_meta_field_info
                                query_param_with_type_str += (f"{nested_meta_field_name}: "
                                                              f"{meta_field_type_str}, ")
                        else:
                            meta_field_type_str, _ = meta_field_info
                            query_param_with_type_str += (f"{meta_field_name}: "
                                                          f"{meta_field_type_str}, ")
                    query_param_with_type_str += ("start_date_time: DateTime | None = None, "
                                                  "end_date_time: DateTime | None = None")

                    # handling projection http query
                    output_str += (
                        f"    async def {query_name}_query_pre(self, {msg_name_snake_cased}_class_type: "
                        f"Type[{msg_name}], {query_param_with_type_str}):\n")
                    routes_import_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR",
                                                                       self.http_routes_file_name)
                    output_str += f"        from {routes_import_path} import " \
                                  f"underlying_read_{msg_name_snake_cased}_http\n"
                    output_str += (f"        # once aggregate function used below is shifted to aggregate.py "
                                   f"of project, import aggregate here for use\n")
                    query_param_dict_str = ""
                    for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                        if isinstance(meta_field_info, dict):
                            for nested_meta_field_name, nested_meta_field_info in meta_field_info.items():
                                _, nested_meta_field = nested_meta_field_info
                                query_param_dict_str += (f'"{meta_field_name}.{nested_meta_field_name}": '
                                                         f'{nested_meta_field.proto.name}')
                                if nested_meta_field_name != list(meta_data_field_name_to_field_tuple_dict)[-1]:
                                    query_param_dict_str += ", "
                        else:
                            _, meta_field = meta_field_info
                            query_param_dict_str += f'"{meta_field_name}": {meta_field.proto.name}'

                    agg_params_str = ""
                    for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                        if isinstance(meta_field_info, dict):
                            for nested_meta_field_name, _ in meta_field_info.items():
                                agg_params_str += f"{nested_meta_field_name}, "
                        else:
                            agg_params_str += f"{meta_field_name}, "
                    agg_params_str += "start_date_time, end_date_time"
                    container_model_name = f"{message.proto.name}ProjectionContainerFor{field_names_str_camel_cased}"

                    projection_agg_pipeline_name = f"{query_name}_agg_pipeline"
                    output_str += (f"        {msg_name_snake_cased}_projection_list = await underlying_read_"
                                   f"{msg_name_snake_cased}_http({projection_agg_pipeline_name}({agg_params_str}), "
                                   f"projection_model={container_model_name})\n")
                    output_str += f"        return {msg_name_snake_cased}_projection_list\n\n"

                    # handling projection ws query
                    output_str += f"    async def {query_name}_query_ws_pre(self):\n"
                    output_str += f"        return {query_name}_filter_callable, {projection_agg_pipeline_name}\n\n"
                    projection_query_filter_func_req_query_name_n_message.append(
                        (query_name, message, meta_data_field_name_to_field_tuple_dict))

        # handling aggregation pipelines for projection query
        for query_name, message, meta_data_field_name_to_field_tuple_dict in (
                projection_query_filter_func_req_query_name_n_message):
            output_str += "\n"
            for field in message.fields:
                if self.is_bool_option_enabled(field,
                                               FastapiCallbackOverrideFileHandler.flux_fld_val_time_field):
                    time_field_name = field.proto.name
                    break
            else:
                err_str = (f"Could not find any time field in {message.proto.name} message having "
                           f"{FastapiCallbackOverrideFileHandler.flux_msg_json_root_time_series} option")
                logging.exception(err_str)
                raise Exception(err_str)

            for field in message.fields:
                if self.is_bool_option_enabled(field, FastapiCallbackOverrideFileHandler.flux_fld_val_meta_field):
                    meta_field = field
                    break
            else:
                err_str = (f"Could not find any time field in {message.proto.name} message having "
                           f"{FastapiCallbackOverrideFileHandler.flux_msg_json_root_time_series} option")
                logging.exception(err_str)
                raise Exception(err_str)

            output_str += f"def {query_name}_agg_pipeline("
            for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                if isinstance(meta_field_info, dict):
                    for nested_meta_field_name, nested_meta_field_info in meta_field_info.items():
                        nested_meta_field_type_str, _ = nested_meta_field_info
                        output_str += (f'{nested_meta_field_name}: '
                                       f'{nested_meta_field_type_str}, ')
                else:
                    meta_field_type_str, _ = meta_field_info
                    output_str += f'{meta_field_name}: {meta_field_type_str}, '
            output_str += ("start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, "
                           "id_list: List[int] | None = None):\n")
            output_str += ("    # shift this function to aggregate.py file of project and remove this comment "
                           "afterward\n")
            output_str += "    agg_pipeline = [\n"
            output_str += "        {\n"
            output_str += "            '$match': {},\n"
            output_str += "        },\n"
            output_str += "        {\n"
            output_str += "            '$match': {\n"
            for meta_field_name, meta_field_proto_or_val in meta_data_field_name_to_field_tuple_dict.items():
                if isinstance(meta_field_proto_or_val, dict):
                    output_str += "                '$and': [\n"
                    for nested_meta_field_name, _ in meta_field_proto_or_val.items():
                        output_str += "                    {\n"
                        output_str += (f"                        '{meta_field_name}.{nested_meta_field_name}': "
                                       f"{nested_meta_field_name}\n")
                        if nested_meta_field_name != list(meta_field_proto_or_val)[-1]:
                            output_str += "                    },\n"
                        else:
                            output_str += "                    }\n"
                    output_str += "                ]\n"
                else:
                    output_str += f"                '{meta_field_name}': {meta_field_name}\n"
            output_str += "            }\n"
            output_str += "        },\n"
            output_str += "        {\n"
            output_str += "            '$match': {},\n"
            output_str += "        },\n"
            output_str += "        {\n"
            output_str += "            '$project': {\n"
            output_str += "                '_id': 0,\n"
            output_str += f"                '{meta_field.proto.name}': 1,\n"
            output_str += "                'projection_models': {\n"
            output_str += f"                    '{time_field_name}': '${time_field_name}',\n"
            field_str_list = query_name_to_field_path_str_list_dict.get(query_name)
            for field_str in field_str_list:
                if "." in field_str:
                    field_str_ = field_str.split(".")[-1]
                    output_str += f"                    '{field_str_}': '${field_str}'"
                else:
                    output_str += f"                    '{field_str}': '${field_str}'"
                if field_str != field_str_list[-1]:
                    output_str += ", \n"
                else:
                    output_str += "\n"
            output_str += "                }\n"
            output_str += "            },\n"
            output_str += "        },\n"
            output_str += "        {\n"
            output_str += "            '$group': {\n"
            output_str += f"                '_id': '${meta_field.proto.name}',\n"
            output_str += "                'projection_models': {\n"
            output_str += "                    '$push': '$projection_models'\n"
            output_str += "                }\n"
            output_str += "            }\n"
            output_str += "        },\n"
            output_str += "        {\n"
            output_str += "            '$project': {\n"
            output_str += "                '_id': 0,\n"
            output_str += f"                '{meta_field.proto.name}': '$_id',\n"
            output_str += f"                'projection_models': 1\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    ]\n"
            output_str += "    if id_list is not None:\n"
            output_str += "        agg_pipeline[0]['$match'] = {\n"
            output_str += "            '_id': {\n"
            output_str += "                '$in': id_list\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    if start_date_time and not end_date_time:\n"
            output_str += "        agg_pipeline[2]['$match'] = {\n"
            output_str += "            '$expr': {\n"
            output_str += "                '$gt': [\n"
            output_str += f"                    '${time_field_name}', start_date_time\n"
            output_str += "                ]\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    elif not start_date_time and end_date_time:\n"
            output_str += "        agg_pipeline[2]['$match'] = {\n"
            output_str += "            '$expr': {\n"
            output_str += "                '$lt': [\n"
            output_str += f"                    '${time_field_name}', end_date_time\n"
            output_str += "                ]\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    elif start_date_time and end_date_time:\n"
            output_str += "        agg_pipeline[2]['$match'] = {\n"
            output_str += "            '$and': [\n"
            output_str += "                {\n"
            output_str += "                    '$expr': {\n"
            output_str += "                        '$gt': [\n"
            output_str += f"                            '${time_field_name}', start_date_time\n"
            output_str += "                        ]\n"
            output_str += "                    }\n"
            output_str += "                },\n"
            output_str += "                {\n"
            output_str += "                    '$expr': {\n"
            output_str += "                        '$lt': [\n"
            output_str += f"                            '${time_field_name}', end_date_time\n"
            output_str += "                        ]\n"
            output_str += "                    }\n"
            output_str += "                }\n"
            output_str += "            ]\n"
            output_str += "        }\n"

            output_str += "    return {'aggregate': agg_pipeline}\n\n"

        # handling projection ws query filter functions
        for query_name, message, meta_data_field_name_to_field_proto_dict in (
                projection_query_filter_func_req_query_name_n_message):
            for field in message.fields:
                if self.is_bool_option_enabled(field,
                                               FastapiCallbackOverrideFileHandler.flux_fld_val_time_field):
                    time_field_name = field.proto.name
                    break
            else:
                err_str = (f"Could not find any time field in {message.proto.name} message having "
                           f"{FastapiCallbackOverrideFileHandler.flux_msg_json_root_time_series} option")
                logging.exception(err_str)
                raise Exception(err_str)

            output_str += "\n"
            message_name = message.proto.name
            msg_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            output_str += f"def {query_name}_filter_callable({msg_name_snake_cased}_obj_json_str: str, **kwargs):\n"
            output_str += f'    return True\n\n'

        return output_str

    def handle_callback_override_file_gen(self) -> str:
        if (output_dir_path := os.getenv("OUTPUT_DIR")) is not None and len(output_dir_path):
            json_sample_file_path = \
                PurePath(output_dir_path) / "JSONSample" / f"{self.proto_file_name}_json_sample.json"
        else:
            err_str = f"Env var 'PLUGIN_OUTPUT_DIR' received as {output_dir_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        with open(json_sample_file_path) as json_sample:
            self.json_sample_loaded_json = json.load(json_sample)
        if (total_root_msg := len(self.root_message_list)) >= 4:
            required_root_msg: List[protogen.Message] = self.root_message_list[:4]
        else:
            required_root_msg: List[protogen.Message] = self.root_message_list

            err_str = f"Model file might have less then 4 root models, complete generation " \
                      f"requires at least 4 models, received {total_root_msg}, generating limited callback " \
                      f"override examples with available messages"
            logging.exception(err_str)

        output_str = self._handle_import_n_pre_exec_code_str(required_root_msg)

        callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        callback_override_class_name_camel_cased = \
            convert_to_capitalized_camel_case(self.beanie_native_override_routes_callback_class_name)
        # example 0 of 5
        output_str += self._handle_callback_example_0(callback_class_name_camel_cased,
                                                      callback_override_class_name_camel_cased)

        first_msg_name = required_root_msg[0].proto.name
        first_msg_name_snake_cased = convert_camel_case_to_specific_case(first_msg_name)
        # example 1 of 5
        if len(required_root_msg) >= 1:
            output_str += self._handle_callback_example_1(first_msg_name, first_msg_name_snake_cased,
                                                          self.json_sample_loaded_json, required_root_msg)
        # example 2 of 5
        if len(required_root_msg) >= 2:
            output_str += self._handle_callback_example_2(first_msg_name, first_msg_name_snake_cased,
                                                          self.json_sample_loaded_json, required_root_msg)

        # example 3 of 5
        if len(required_root_msg) >= 3:
            output_str += self._handle_callback_example_3(first_msg_name, first_msg_name_snake_cased,
                                                          self.json_sample_loaded_json, required_root_msg)

        if len(required_root_msg) >= 4:
            # example 4 of 5
            output_str += self._handle_callback_example_4(first_msg_name, first_msg_name_snake_cased, required_root_msg)
            # example 5 of 5
            output_str += self._handle_callback_example_5(first_msg_name, first_msg_name_snake_cased, required_root_msg)

        output_str += self._handle_callback_query_example()

        return output_str
