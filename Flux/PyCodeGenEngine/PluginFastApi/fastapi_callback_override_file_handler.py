import os
import time
from typing import List, Dict
import json
from abc import ABC
import logging
from pathlib import PurePath

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiCallbackOverrideFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def _handle_field_data_manipulation(self, json_content: Dict, message: protogen.Message, id_str: str | None = None,
                                        single_field: bool | None = False):
        if not single_field:
            temp_str = ""
            for field in message.fields:
                if BaseFastapiPlugin.default_id_field_name == field.proto.name:
                    temp_str += f"{field.proto.name}={id_str}"
                else:
                    message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
                    field_val = json_content[message_name_snake_cased][field.proto.name]
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
                            if BaseFastapiPlugin.flux_fld_val_is_datetime in str(field.proto.options):
                                return f'{field.proto.name} = DateTime.utcnow()'
                            else:
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
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.client_file_name}")
        web_client_name_caps_camel_cased = convert_to_capitalized_camel_case(self.client_file_name)
        output_str += f"from {web_client_path} import {web_client_name_caps_camel_cased}\n"
        model_path = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_file_name}")
        output_str += f"from {model_path} import *\n"
        routes_callback = \
            self.import_path_from_os_path("OUTPUT_DIR", f"{self.routes_callback_class_name}")
        callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {routes_callback} import " \
                      f"{callback_class_name_camel_cased}\n\n\n"
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
                      f'{self._handle_field_data_manipulation(json_sample_content, required_root_msg[0], single_field=True)}\n'
        output_str += f'        logging.debug(f"{first_msg_name} pre test: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n\n'
        output_str += f'    async def create_{first_msg_name_snake_cased}_post(self, ' \
                      f'{first_msg_name_snake_cased}_obj: {first_msg_name}):\n'
        output_str += f'        logging.debug(f"{first_msg_name} from DB: ' + '{' + \
                      f'{first_msg_name_snake_cased}_obj' + '}' + '")\n'
        output_str += f'        {first_msg_name_snake_cased}_obj.' \
                      f'{self._handle_field_data_manipulation(json_sample_content, required_root_msg[0], single_field=True)}\n'
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
                      f'{self._handle_field_data_manipulation(json_sample_content, main_msg, single_field=True)}\n'
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
                      f'{self._handle_field_data_manipulation(json_sample_content, main_msg, single_field=True)}\n'
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
            output_str += f"\n"
        for message in self.message_to_query_option_list_dict:
            msg_name = message.proto.name
            msg_name_snake_cased = convert_camel_case_to_specific_case(msg_name)

            aggregate_value_list = self.message_to_query_option_list_dict[message]

            for aggregate_value in aggregate_value_list:
                aggregate_var_name = aggregate_value[FastapiCallbackOverrideFileHandler.aggregate_var_name_key]
                aggregate_params = aggregate_value[FastapiCallbackOverrideFileHandler.aggregate_params_key]
                aggregate_params_data_types = aggregate_value[
                    FastapiCallbackOverrideFileHandler.aggregate_params_data_types_key]

                routes_import_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_file_name)
                aggregate_file_path = self.import_path_from_os_path("PROJECT_DIR", "app.aggregate")

                if aggregate_params:
                    agg_params_with_type_str = ", ".join([f"{param}: {param_type}"
                                                          for param, param_type in zip(aggregate_params,
                                                                                       aggregate_params_data_types)])
                    agg_params_str = ", ".join(aggregate_params)

                    output_str += f"    async def {aggregate_var_name}_query_pre(self, {msg_name_snake_cased}_class_type: " \
                                  f"Type[{msg_name}], {agg_params_with_type_str}):\n"
                    output_str += f"        from {routes_import_path} import " \
                                  f"underlying_read_{msg_name_snake_cased}_http\n"
                    output_str += f"        from {aggregate_file_path} import {aggregate_var_name}\n"
                    output_str += f"        return await underlying_read_{msg_name_snake_cased}_http(" \
                                  f"{aggregate_var_name}({agg_params_str}))\n"
                    output_str += "\n\n"
                else:
                    output_str += f"    async def {aggregate_var_name}_query_pre(self, {msg_name_snake_cased}_class_type: " \
                                  f"Type[{msg_name}]):\n"
                    output_str += f"        from {routes_import_path} import " \
                                  f"underlying_read_{msg_name_snake_cased}_http\n"
                    output_str += f"        from {aggregate_file_path} import {aggregate_var_name}\n"
                    output_str += f"        return await underlying_read_{msg_name_snake_cased}_http(" \
                                  f"{aggregate_var_name})\n"
                    output_str += "\n\n"

        return output_str

    def handle_callback_override_file_gen(self) -> str:
        if (output_dir_path := os.getenv("OUTPUT_DIR")) is not None:
            json_sample_file_path = PurePath(output_dir_path) / f"{self.proto_file_name}_json_sample.json"
        else:
            err_str = "Env var 'OUTPUT_DIR' received as None"
            logging.exception(err_str)
            raise Exception(err_str)
        with open(json_sample_file_path) as json_sample:
            json_sample_content = json.load(json_sample)
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
            convert_to_capitalized_camel_case(self.routes_callback_class_name_override)
        # example 0 of 5
        output_str += self._handle_callback_example_0(callback_class_name_camel_cased,
                                                      callback_override_class_name_camel_cased)

        first_msg_name = required_root_msg[0].proto.name
        first_msg_name_snake_cased = convert_camel_case_to_specific_case(first_msg_name)
        # example 1 of 5
        if len(required_root_msg) >= 1:
            output_str += self._handle_callback_example_1(first_msg_name, first_msg_name_snake_cased,
                                                          json_sample_content, required_root_msg)
        # example 2 of 5
        if len(required_root_msg) >= 2:
            output_str += self._handle_callback_example_2(first_msg_name, first_msg_name_snake_cased,
                                                          json_sample_content, required_root_msg)

        # example 3 of 5
        if len(required_root_msg) >= 3:
            output_str += self._handle_callback_example_3(first_msg_name, first_msg_name_snake_cased,
                                                          json_sample_content, required_root_msg)

        if len(required_root_msg) >= 4:
            # example 4 of 5
            output_str += self._handle_callback_example_4(first_msg_name, first_msg_name_snake_cased, required_root_msg)
            # example 5 of 5
            output_str += self._handle_callback_example_5(first_msg_name, first_msg_name_snake_cased, required_root_msg)

        output_str += self._handle_callback_query_example()

        return output_str
