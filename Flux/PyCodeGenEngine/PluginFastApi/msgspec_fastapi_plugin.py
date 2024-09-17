#!/usr/bin/env python
import os
from typing import List, Dict, Tuple, Type
import time
import logging
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_file_handler import FastapiCallbackFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_file_handler import FastapiCallbackOverrideFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_set_instance_handler import \
    FastapiCallbackOverrideSetInstanceHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_http_routes_file_handler import FastapiHttpRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_ws_routes_file_handler import FastapiWsRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_launcher_file_handler import FastapiLauncherFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_http_client_file_handler import FastapiHttpClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_ws_client_file_handler import FastapiWSClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_ui_proxy_config_handler import FastapiUIProxyConfigHandler
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import main
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, convert_camel_case_to_specific_case


root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class MsgspecFastApiPlugin(FastapiCallbackFileHandler,
                           FastapiCallbackOverrideSetInstanceHandler,
                           FastapiHttpClientFileHandler,
                           FastapiWSClientFileHandler,
                           FastapiHttpRoutesFileHandler,
                           FastapiWsRoutesFileHandler,
                           FastapiLauncherFileHandler,
                           FastapiCallbackOverrideFileHandler,
                           FastapiUIProxyConfigHandler):
    """
    Plugin script to generate Beanie enabled fastapi app
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.app_is_router: bool = True
        self.custom_id_primary_key_messages: List[protogen.Message] = []
        self.msg_type_to_nested_root_type_field_name_n_type_dict: Dict[protogen.Message, List[Tuple[str, str]]] = {}

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message],
                                                 avoid_non_roots: bool | None = None):
        message_list.sort(key=lambda message_: message_.proto.name)     # sorting by name

        for message in message_list:
            # Adding Json-Root messages
            if ((is_json_root := self.is_option_enabled(message, MsgspecFastApiPlugin.flux_msg_json_root)) or
                    self.is_option_enabled(message, MsgspecFastApiPlugin.flux_msg_json_root_time_series)):
                if is_json_root:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, MsgspecFastApiPlugin.flux_msg_json_root)
                else:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, MsgspecFastApiPlugin.flux_msg_json_root_time_series)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict.get(
                        MsgspecFastApiPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list

                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                if MsgspecFastApiPlugin.default_id_field_name in [field.proto.name for field in message.fields]:
                    self.custom_id_primary_key_messages.append(message)
            else:
                if not avoid_non_roots:
                    if message not in self.non_root_message_list:
                        self.non_root_message_list.append(message)
                    # else not required: avoiding repetition

            # Adding query messages
            if self.is_option_enabled(message, MsgspecFastApiPlugin.flux_msg_json_query):
                if message not in self.message_to_query_option_list_dict:
                    self.message_to_query_option_list_dict[message] = self.get_query_option_message_values(message)
                # else not required: avoiding repetition
            # else not required: avoiding list append if msg is not having option for query

            self.load_dependency_messages_and_enums_in_dicts(message)

            # checking if any field or nested field in message is of root type
            res_list = self._get_root_type_nested_fields_path_n_type_list(message)
            if res_list:
                self.msg_type_to_nested_root_type_field_name_n_type_dict[message] = res_list

    def _get_root_type_nested_fields_path_n_type_list(self, message: protogen.Message,
                                                      result_list: List[Tuple[str, str]] | None = None,
                                                      field_prefix: str | None = None) -> List[Tuple[str, str]]:
        if result_list is None:
            result_list = []
        if field_prefix is None:
            field_prefix = ""
        for field in message.fields:
            if field.message is not None:
                if MsgspecFastApiPlugin.is_option_enabled(field.message, MsgspecFastApiPlugin.flux_msg_json_root):
                    if field_prefix:
                        if field.cardinality.name.lower() == "repeated":
                            result_list.append((f"{field_prefix}.{field.proto.name}", field.message.proto.name))
                        # else not required: if field is not repeated then id will not affect to be same with root model
                        self._get_root_type_nested_fields_path_n_type_list(field.message, result_list,
                                                                           f"{field_prefix}.{field.proto.name}")
                    else:
                        if field.cardinality.name.lower() == "repeated":
                            result_list.append((f"{field.proto.name}", field.message.proto.name))
                        # else not required: if field is not repeated then id will not affect to be same with root model
                        self._get_root_type_nested_fields_path_n_type_list(field.message, result_list,
                                                                           f"{field.proto.name}")
                else:
                    self._get_root_type_nested_fields_path_n_type_list(field.message, result_list,
                                                                       f"{field.proto.name}")
            # else not required: ignore if not msg type
        return result_list


    def _get_msg_id_field_type(self, message: protogen.Message) -> str:
        id_field_type: str = MsgspecFastApiPlugin.default_id_type_var_name
        if message in self.custom_id_primary_key_messages:
            for field in message.fields:
                if field.proto.name == MsgspecFastApiPlugin.default_id_field_name:
                    id_field_type = self.proto_to_py_datatype(field)
                    break
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

    def handle_init_db(self) -> str:
        root_msg_list = [message.proto.name for message in self.root_message_list]
        output_str = "def get_mongo_server_uri():\n"
        output_str += '    config_yaml_path = PurePath(__file__).parent.parent.parent / "data" / f"config.yaml"\n'
        output_str += '    if os.path.exists(config_yaml_path):\n'
        output_str += '        config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))\n'
        output_str += '    else:\n'
        output_str += '        err_str = f"data/config.yaml does not exist"\n'
        output_str += '        logging.exception(err_str)\n'
        output_str += '        raise Exception(err_str)\n\n'
        output_str += '    mongo_server = "mongodb://localhost:27017" if (mongo_env := ' \
                      'config_yaml_dict.get("mongo_server")) is None else mongo_env\n'
        output_str += '    if config_yaml_dict.get("log_mongo_uri", True):\n'
        output_str += '        logging.debug(f"mongo_server: {mongo_server}")\n'
        output_str += '    if (db_name := os.getenv("DB_NAME")) is not None and len(db_name):\n'
        output_str += '        mongo_server += f"/{db_name}?authSource=admin"\n'
        output_str += '    return mongo_server\n\n\n'

        output_str += 'class MongoDBInit:\n'
        output_str += '    __slots__ = "mongo_client", "db_name", "db_instance"\n'
        output_str += '    instance_object = None\n\n'
        output_str += '    def __init__(self, mongo_client_: motor.motor_asyncio.AsyncIOMotorClient, db_name: str):\n'
        output_str += '        self.mongo_client = mongo_client_\n'
        output_str += '        self.db_name = db_name\n'
        output_str += '        self.db_instance = self.mongo_client.get_database(self.db_name)\n\n'
        output_str += '    @classmethod\n'
        output_str += '    async def init_db(cls):\n'
        output_str += '        collection_list = await cls.instance_object.db_instance.list_collection_names()\n\n'

        for msg in self.root_message_list:
            output_str += f'        if "{msg.proto.name}" not in collection_list:\n'
            if self.is_option_enabled(msg, MsgspecFastApiPlugin.flux_msg_json_root_time_series):
                time_field, meta_field, granularity, expire_after_sec = self.get_time_series_data_from_msg(msg)
                output_str += "            time_series_config = {\n"
                output_str += f"                'timeField': '{time_field}'"
                if meta_field:
                    output_str += f",\n"
                    output_str += f"                'metaField': '{meta_field}'"
                if granularity:
                    output_str += f",\n"
                    match granularity:
                        case "Sec":
                            output_str += f"                'granularity': 'seconds'"
                        case "Min":
                            output_str += f"                'granularity': 'minutes'"
                        case "Hrs":
                            output_str += f"                'granularity': 'hours'"
                output_str += "\n"
                output_str += "            }\n"

                output_str += (f'            {msg.proto.name}.collection_obj = '
                               f'await cls.instance_object.db_instance.create_collection("{msg.proto.name}", '
                               f'timeseries=time_series_config')
                if expire_after_sec:
                    output_str += f', expireAfterSeconds={expire_after_sec}'
                output_str += ")\n"
            else:
                output_str += (f'            {msg.proto.name}.collection_obj = '
                               f'await cls.instance_object.db_instance.create_collection("{msg.proto.name}")\n')

            # Adding index field initialization with created collection object
            index_field_name_list = []
            for field in msg.fields:
                if self.is_option_enabled(field, MsgspecFastApiPlugin.flux_fld_index):
                    index_field_name_list.append(field.proto.name)

            if index_field_name_list:
                output_str += (f'            await {msg.proto.name}.collection_obj.create_index('
                               f'{index_field_name_list})\n')
            output_str += f'        else:\n'
            output_str += (f'            {msg.proto.name}.collection_obj = '
                           f'cls.instance_object.db_instance.get_collection("{msg.proto.name}")\n\n')
        output_str += f"    @classmethod\n"
        output_str += (f"    async def set_instance(cls, mongo_client_: motor.motor_asyncio.AsyncIOMotorClient, "
                       f"db_name: str):\n")
        output_str += f"        if cls.instance_object is not None:\n"
        output_str += (f'            logging.warning("ServerDataBaseInit object already exists, '
                       f'returning existing instance")\n')
        output_str += f'            return cls.instance_object\n'
        output_str += f'        else:\n'
        output_str += f'            cls.instance_object = MongoDBInit(mongo_client_, db_name)\n'
        output_str += f'            # creating collections for collection list if doesn\'t exist\n'
        output_str += f'            await cls.init_db()\n'
        output_str += f'            return cls.instance_object\n\n'
        output_str += f'    @classmethod\n'
        output_str += f'    def get_instance(cls):\n'
        output_str += f'        if cls.instance_object is not None:\n'
        output_str += f'            return cls.instance_object\n'
        output_str += f'        logging.warning("ServerDataBaseInit object doesn\'t already exist")\n'
        output_str += f'        return None\n\n\n'

        model_names = ", ".join(root_msg_list)
        output_str += f'document_models=[{model_names}]\n\n\n'
        output_str += "async def init_db():\n"
        output_str += '    mongo_server = get_mongo_server_uri()\n'
        output_str += '    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_server, tz_aware=True)\n'
        output_str += f'    if (db_name := os.getenv("DB_NAME")) is not None and len(db_name):\n'
        output_str += f'        db = client.get_default_database()\n'
        output_str += f'    else:\n'
        output_str += f'        db = client.{self.proto_file_package}\n'
        output_str += '    logging.debug(f"db_name: {db.name}")\n'
        output_str += f'    db_handler = await MongoDBInit.set_instance(client, db.name)\n'
        output_str += f'    return db_handler\n'
        return output_str

    def handle_database_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "import motor\n"
        output_str += "import motor.motor_asyncio\n"
        output_str += "from pathlib import PurePath\n"
        output_str += "import logging\n"

        output_str += f"from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager\n"
        output_str += f'\n\n'
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f'from {model_file_path} import *\n\n\n'
        output_str += self.handle_init_db()

        return output_str

    def handle_fastapi_initialize_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "from msgspec import Struct\n"
        output_str += "from fastapi import FastAPI\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"
        # else not required: if no message with custom id is found then avoiding import statement
        database_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.database_file_name)
        output_str += f"from {database_file_path} import init_db\n"
        generic_utils_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_utils")
        output_str += f"from {generic_utils_path} import init_max_id_handler, init_nested_max_id_handler\n\n"
        output_str += "# Below imports are to initialize routes before launching server\n"
        routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.http_routes_file_name)
        output_str += f"from {routes_file_path} import *\n"
        routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.ws_routes_file_name)
        output_str += f"from {routes_file_path} import *\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n\n"
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        output_str += f'    await init_db()\n'
        for message in self.custom_id_primary_key_messages:
            if "int" == self._get_msg_id_field_type(message):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                if message in self.msg_type_to_nested_root_type_field_name_n_type_dict:
                    # max_id to be used to check before nested call - if no obj is there for parent model ,i.e.,
                    # max_id=0 then since no obj is parent model is present, no nested obj id needs to be checked
                    # and initialized
                    output_str += f"    {message_name_snake_cased}_max_id = await init_max_id_handler({message_name})\n"
                else:
                    output_str += f"    await init_max_id_handler({message_name})\n"
        for message, nested_root_type_field_n_type_list in self.msg_type_to_nested_root_type_field_name_n_type_dict.items():
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if MsgspecFastApiPlugin.is_option_enabled(message, MsgspecFastApiPlugin.flux_msg_json_root):
                for nested_field_path, nested_field_type in nested_root_type_field_n_type_list:
                    output_str += f"    if {message_name_snake_cased}_max_id != 0:\n"
                    output_str += (f"        await init_nested_max_id_handler({message_name}, '{nested_field_path}', "
                                   f"{nested_field_type})\n")
                    output_str += (f"    # else not required: {message_name} itself has no data so nested fields type "
                                   f"don't need initialization\n")
            # else not required: if top lvl msg is not root type then it will not be persisted and hence
            # nested root types will not be conflicted to any persisted obj

        output_str += '    port = os.getenv("PORT")\n'
        output_str += '    if port is None or len(port) == 0:\n'
        output_str += '        err_str = "Can not find PORT env var for fastapi db init"\n'
        output_str += '        logging.exception(err_str)\n'
        output_str += '        raise Exception(err_str)\n'
        output_str += (f'    os.environ[f"{self.proto_file_package}' + '_{port}"] = "1"  # indicator flag to tell '
                       'callback override that service is up\n')
        output_str += "\n\n"
        output_str += 'host = os.environ.get("HOST")\n'
        output_str += 'if host is None or len(host) == 0:\n'
        output_str += '    err_str = "Couldn\'t find \'HOST\' key in data/config.yaml of current project"\n'
        output_str += '    logging.error(err_str)\n'
        output_str += '    raise Exception(err_str)\n\n'
        output_str += "from fastapi.middleware.cors import CORSMiddleware\n"
        output_str += f"from fastapi.staticfiles import StaticFiles\n\n"
        output_str += "cors_dict: Dict[str, Any] = dict()\n"
        output_str += 'cors_dict["allow_methods"] = ["*"]\n'
        output_str += 'cors_dict["allow_headers"] = ["*"]\n'
        output_str += "if os.getenv('DEBUG'):\n"
        output_str += '    cors_dict["allow_origins"] = ["*"]\n'
        output_str += '    cors_dict["allow_credentials"] = True\n'
        output_str += "else:\n"
        temp = r"\\."
        output_str += f'    host_pattern = host.replace(".", "{temp}")\n'
        temp = r":\d+"
        output_str += '    allow_origin_pattern = rf"https?://{host_pattern}'+f'({temp})?"\n'
        output_str += '    cors_dict["allow_origin_regex"] = allow_origin_pattern\n'
        output_str += f"{self.fastapi_app_name}.add_middleware(\n"
        output_str += f"    CORSMiddleware,\n"
        output_str += f"    **cors_dict\n"
        output_str += f")\n\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'


        output_str += (f"{self.fastapi_app_name}.mount('/static', "
                       "StaticFiles(directory=f'{host}/static'), name='static')\n\n")
        return output_str

    def set_req_data_members(self, file: protogen.File):
        super().set_req_data_members(file)
        self.database_file_name = f"{self.proto_file_name}_msgspec_database"
        self.fastapi_file_name = f"{self.proto_file_name}_msgspec_fastapi"
        self.http_routes_file_name = f'{self.proto_file_name}_http_msgspec_routes'
        self.routes_callback_file_name = f"{self.proto_file_name}_routes_msgspec_callback"
        self.base_routes_file_name = f'{self.proto_file_name}_base_msgspec_routes'
        self.callback_override_set_instance_file_name = f"{self.proto_file_name}_msgspec_callback_override_set_instance"
        self.launch_file_name = self.proto_file_name + "_launch_msgspec_server"
        self.api_router_app_name = f"{self.proto_file_name}_API_router_msgspec"
        self.ws_routes_file_name = f'{self.proto_file_name}_ws_msgspec_routes'

    def output_file_generate_handler(self, file: protogen.File):
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)

        # Adding messages from core proto files having json_root option
        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var PROJECT_DIR received as {project_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

        core_or_util_files: List[str] = root_flux_core_config_yaml_dict.get("core_or_util_files")

        if "ProjectGroup" in project_dir:
            project_group_flux_core_config_yaml_path = PurePath(project_dir).parent.parent / "flux_core.yaml"
            project_group_flux_core_config_yaml_dict = (
                YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
            project_grp_core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
            if project_grp_core_or_util_files:
                core_or_util_files.extend(project_grp_core_or_util_files)

        if core_or_util_files is not None:
            for dependency_file in file.dependencies:
                if dependency_file.proto.name in core_or_util_files:
                    self.load_root_and_non_root_messages_in_dicts(dependency_file.messages, avoid_non_roots=True)
                # else not required: if dependency file name not in core_or_util_files
                # config list, avoid messages from it
        # else not required: core_or_util_files key is not in yaml dict config

        self.set_req_data_members(file)

        # sorting created message lists
        self.root_message_list.sort(key=lambda message_: message_.proto.name)
        self.non_root_message_list.sort(key=lambda message_: message_.proto.name)
        self.enum_list.sort(key=lambda message_: message_.proto.name)

        output_dict: Dict[str, str] = {
            # # Adding project´s database.py
            self.database_file_name+".py": self.handle_database_file_gen(),
            #
            # # Adding project´s fastapi.py
            self.fastapi_file_name + ".py": self.handle_fastapi_initialize_file_gen(),
            #
            # # Adding route's callback class
            self.routes_callback_file_name + ".py": self.handle_msgspec_callback_class_file_gen(),
            #
            # Adding callback override set_instance file
            self.callback_override_set_instance_file_name + ".py":
                self.handle_msgspec_callback_override_set_instance_file_gen(),

            # Adding dummy callback override class file
            # "dummy_" + self.beanie_native_override_routes_callback_class_name + ".py":
            #     self.handle_callback_override_file_gen(),

            # Adding callback import file
            self.routes_callback_import_file_name + ".py": self.handle_routes_callback_import_file_gen(),

            # Adding base routes.py
            self.base_routes_file_name + ".py": self.handle_base_routes_file_gen(),

            # Adding project's http routes.py
            self.http_routes_file_name + ".py": self.handle_http_msgspec_routes_file_gen(),

            # adding http routes import file
            self.http_routes_import_file_name + ".py": self.handle_http_routes_import_file_gen(),

            # # Adding project's ws routes.py
            self.ws_routes_file_name + ".py": self.handle_ws_msgspec_routes_file_gen(),

            # # Adding project's launch file
            self.launch_file_name + ".py": self.handle_launch_file_gen(file),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen(file),

            # Adding WS client file
            self.ws_client_file_name + ".py": self.handle_ws_client_file_gen(file),

            self.ws_ui_proxy_config_file_name: self.handle_ui_proxy_config_file_gen(file)
        }

        return output_dict


if __name__ == "__main__":
    main(MsgspecFastApiPlugin)
