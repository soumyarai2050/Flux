#!/usr/bin/env python
import os
from typing import List, Dict
import time
import logging
from pathlib import PurePath

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_file_handler import FastapiCallbackFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_file_handler import FastapiCallbackOverrideFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_set_instance_handler import \
    FastapiCallbackOverrideSetInstanceHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_routes_file_handler import FastapiRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_launcher_file_handler import FastapiLauncherFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_client_file_handler import FastapiClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import main


class BeanieFastApiPlugin(FastapiCallbackFileHandler,
                          FastapiCallbackOverrideSetInstanceHandler,
                          FastapiClientFileHandler,
                          FastapiRoutesFileHandler,
                          FastapiLauncherFileHandler,
                          FastapiCallbackOverrideFileHandler):
    """
    Plugin script to generate Beanie enabled fastapi app
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.app_is_router: bool = True
        self.custom_id_primary_key_messages: List[protogen.Message] = []

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if self.is_option_enabled(message, BeanieFastApiPlugin.flux_msg_json_root):
                json_root_msg_option_val_dict = \
                    self.get_complex_option_set_values(message, BeanieFastApiPlugin.flux_msg_json_root)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict.get(
                        BeanieFastApiPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list

                if (is_reentrant_on_top := json_root_msg_option_val_dict.get(
                        BeanieFastApiPlugin.flux_json_root_set_reentrant_lock_to_top_field)) is not None:
                    if is_reentrant_required is not None and not is_reentrant_required:
                        err_str = "Field SetReentrantLock is set to true, avoiding adding model's reentrant lock " \
                                  "to generated route for this model therefor no use can be made of " \
                                  "SetReentrantLockToTop field set to true, make changes to proto file for it"
                        logging.error(err_str)
                        raise Exception(err_str)
                    else:
                        if is_reentrant_on_top:
                            self.reentrant_lock_on_top_required_msg.append(message)
                        # else not required: if not set or is false then lock will be created on default position
                # else not required: If not set then avoiding any processing for it

                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                if BeanieFastApiPlugin.default_id_field_name in [field.proto.name for field in message.fields]:
                    self.custom_id_primary_key_messages.append(message)
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            if self.is_option_enabled(message, BeanieFastApiPlugin.flux_msg_json_query):
                if message not in self.message_to_query_option_list_dict:
                    self.message_to_query_option_list_dict[message] = self.get_query_option_message_values(message)
                # else not required: avoiding repetition
            # else not required: avoiding list append if msg is not having option for query

            self.load_dependency_messages_and_enums_in_dicts(message)

    def _get_msg_id_field_type(self, message: protogen.Message) -> str:
        id_field_type: str = BeanieFastApiPlugin.default_id_type_var_name
        if message in self.custom_id_primary_key_messages:
            for field in message.fields:
                if field.proto.name == BeanieFastApiPlugin.default_id_field_name:
                    id_field_type = self.proto_to_py_datatype(field)
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

    def handle_init_db(self) -> str:
        root_msg_list = [message.proto.name for message in self.root_message_list]
        output_str = "def get_mongo_server_uri():\n"
        output_str += '    config_file_path: PurePath = PurePath(__file__).parent.parent.parent / "data" / "config.yaml"\n'
        output_str += '    config_dict = load_yaml_configurations(str(config_file_path))\n'
        output_str += '    mongo_server = "mongodb://localhost:27017" if (mongo_env := ' \
                      'config_dict.get("mongo_server")) is None else mongo_env\n'
        output_str += '    if config_dict.get("log_mongo_uri", True):\n'
        output_str += '        logging.debug(f"mongo_server: {mongo_server}")\n'
        output_str += '    if (db_name := os.getenv("DB_NAME")) is not None:\n'
        output_str += '        mongo_server += f"/{db_name}?authSource=admin"\n'
        output_str += '    return mongo_server\n\n'
        output_str += "\n"
        model_names = ", ".join(root_msg_list)
        output_str += "async def init_db():\n"
        output_str += '    mongo_server = get_mongo_server_uri()\n'
        output_str += '    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_server, tz_aware=True)\n'
        output_str += f'    if (db_name := os.getenv("DB_NAME")) is not None:\n'
        output_str += f'        db = client.get_default_database()\n'
        output_str += f'    else:\n'
        output_str += f'        db = client.{self.proto_file_package}\n'
        output_str += '    logging.debug(f"db_name: {db_name}")\n'
        output_str += f'    await init_beanie(\n'
        output_str += f'        database=db,\n'
        output_str += f'        document_models=[{model_names}]\n'
        output_str += f'        )\n'
        return output_str

    def handle_database_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "from beanie import init_beanie\n"
        output_str += "import motor\n"
        output_str += "import motor.motor_asyncio\n"
        output_str += "from pathlib import PurePath\n"
        output_str += "import logging\n"

        output_str += f"from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f'from {model_file_path} import *\n\n\n'
        output_str += self.handle_init_db()

        return output_str

    def handle_fastapi_initialize_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "from fastapi import FastAPI\n"
        routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.routes_file_name)
        output_str += f"from {routes_file_path} import {self.api_router_app_name}\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"
        # else not required: if no message with custom id is found then avoiding import statement
        database_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.database_file_name)
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
        super().set_req_data_members(file)
        self.database_file_name = f"{self.proto_file_name}_beanie_database"
        self.fastapi_file_name = f"{self.proto_file_name}_beanie_fastapi"

    def output_file_generate_handler(self, file: protogen.File):
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

            # Adding dummy callback override class file
            "dummy_" + self.routes_callback_class_name_override + ".py": self.handle_callback_override_file_gen(),

            # Adding project's routes.py
            self.routes_file_name+".py": self.handle_routes_file_gen(),

            # Adding project's launch file
            self.launch_file_name + ".py": self.handle_launch_file_gen(file),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen(file)
        }

        return output_dict


if __name__ == "__main__":
    main(BeanieFastApiPlugin)
