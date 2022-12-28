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

    def handle_fastapi_initialize_file_gen(self) -> str:
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

    def set_req_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.database_file_name = f"{self.proto_file_name}_beanie_database"
        self.fastapi_file_name = f"{self.proto_file_name}_beanie_fastapi"
        self.model_file_name = f'{self.proto_file_name}_beanie_model'
        self.routes_file_name = f'{self.proto_file_name}_beanie_routes'
        self.launch_file_name = self.proto_file_name + "_beanie_launch_server"
        self.client_file_name = f"{self.proto_file_name}_beanie_web_client"
        self.routes_callback_class_name = f"{self.proto_file_name}_beanie_routes_callback"
        self.routes_callback_class_name_override = f"{self.proto_file_name}_beanie_routes_callback_override"
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

            # Adding project´s fastapi.py
            self.fastapi_file_name + ".py": self.handle_fastapi_initialize_file_gen(),

            # Adding route's callback class
            self.routes_callback_class_name + ".py": self.handle_callback_class_file_gen(),

            # Adding callback override set_instance file
            self.callback_override_set_instance_file_name + ".py":
                self.handle_callback_override_set_instance_file_gen(),

            # Adding callback override class file
            self.routes_callback_class_name + "_override.py": self.handle_callback_override_file_gen(),

            # Adding project's routes.py
            self.routes_file_name+".py": self.handle_routes_file_gen(),

            # Adding project's launch file
            self.launch_file_name + ".py": self.handle_launch_file_gen(),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen()
        }

        return output_dict


if __name__ == "__main__":
    main(BeanieFastApiClassGenPlugin)
