#!/usr/bin/env python
import logging
import os
from typing import List, Dict
import time
from pathlib import PurePath

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import main
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_file_handler import FastapiCallbackFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_client_file_handler import FastapiClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_launcher_file_handler import FastapiLauncherFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_routes_file_handler import FastapiRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_file_handler import FastapiCallbackOverrideFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_set_instance_handler import \
    FastapiCallbackOverrideSetInstanceHandler


class CacheFastApiPlugin(FastapiCallbackFileHandler,
                         FastapiCallbackOverrideSetInstanceHandler,
                         FastapiClientFileHandler,
                         FastapiRoutesFileHandler,
                         FastapiLauncherFileHandler,
                         FastapiCallbackOverrideFileHandler):
    """
    Plugin script to generate
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if CacheFastApiPlugin.flux_msg_json_root in str(message.proto.options):
                json_root_msg_option_val_dict = \
                    self.get_complex_option_values_as_list_of_dict(message, CacheFastApiPlugin.flux_msg_json_root)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict[0].get(
                        CacheFastApiPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list

                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                for field in message.fields:
                    if field.proto.name == CacheFastApiPlugin.default_id_field_name:
                        if "int" == self.proto_to_py_datatype(field):
                            self.int_id_message_list.append(message)
                            break
                        else:
                            err_str = "Id field other than int not supported for cached pydantic model"
                            logging.exception(err_str)
                            raise Exception(err_str)
                # else not required : If no id field exists then adding id field using int
                # auto-increment in next for loop
                else:
                    self.int_id_message_list.append(message)
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            if CacheFastApiPlugin.flux_msg_json_query in str(message.proto.options):
                if message in self.root_message_list:
                    if message not in self.query_message_dict:
                        self.query_message_dict[message] = self.get_query_option_message_values(message)
                    # else not required: avoiding repetition
                else:
                    err_str = "Query type message should be root message also to perform db queries, " \
                              f"message {message.proto.name} is not JsonRoot"
                    logging.exception(err_str)
                    raise Exception(err_str)
            # else not required: avoiding list append if msg is not having option for query

            self.load_dependency_messages_and_enums_in_dicts(message)

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                return CacheFastApiPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def handle_fastapi_initialize_file_gen(self):
        output_str = "from fastapi import FastAPI\n"
        routes_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_file_name)
        output_str += f"from {routes_file_path} import {self.api_router_app_name}\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import "
        if self.int_id_message_list:
            for message in self.int_id_message_list:
                output_str += message.proto.name
                if message != self.int_id_message_list[-1]:
                    output_str += ", "
                else:
                    output_str += "\n\n\n"
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

    def set_req_data_members(self, file: protogen.File):
        super().set_req_data_members(file)
        self.fastapi_file_name = f"{self.proto_file_name}_cache_fastapi"

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

            # Adding dummy callback override class file
            "dummy_" + self.routes_callback_class_name_override + ".py": self.handle_callback_override_file_gen(),

            # Adding project's routes.py
            self.routes_file_name + ".py": self.handle_routes_file_gen(),

            # Adding project's run file
            self.launch_file_name + ".py": self.handle_launch_file_gen(file),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen(file)
        }

        return output_dict


if __name__ == "__main__":
    main(CacheFastApiPlugin)
