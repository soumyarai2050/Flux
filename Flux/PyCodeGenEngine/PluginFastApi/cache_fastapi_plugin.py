#!/usr/bin/env python
import os
from typing import List, Dict
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin, main

# Required for accessing custom options from schema
from Flux.PyCodeGenEngine.PluginFastApi import insertion_imports


class CacheFastApiPlugin(BaseFastapiPlugin):
    """
    Plugin script to generate
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if CacheFastApiPlugin.flux_msg_json_root in str(message.proto.options):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                for field in message.fields:
                    if field.proto.name == CacheFastApiPlugin.default_id_field_name and \
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
                return CacheFastApiPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

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

    def _get_msg_id_field_type(self, message: protogen.Message) -> str:
        id_field_type: str = "int"
        if message in self.int_id_message_list:
            for field in message.fields:
                if field.proto.name == CacheFastApiPlugin.default_id_field_name and \
                        "int" != (field_type := self.proto_to_py_datatype(field)):
                    id_field_type = field_type
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

    def set_req_data_members(self, file: protogen.File):
        super().set_req_data_members(file)
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
    main(CacheFastApiPlugin)
