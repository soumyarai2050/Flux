import os
import time
from abc import ABC
import logging
from typing import List, Tuple, Dict

# 3rd party imports
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin, ModelType
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import (
    project_dir, root_core_proto_files, project_grp_core_proto_files)

class FastapiCallbackFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def unpack_kwargs_for_callback_methods(self, **kwargs):
        message: protogen.Message | None = kwargs.get("message")
        id_field_type: str | None = kwargs.get("id_field_type")
        model_type: ModelType | None = kwargs.get("model_type")
        if message is None:
            err_str = (f"Can't find message in kwargs: "
                       f"{message.proto.name if message is not None else message}")
            logging.exception(err_str)
            raise Exception(err_str)
        return message, id_field_type, model_type

    def handle_POST_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Dataclass:
            output_str = f"    async def create_{message_name_snake_cased}_pre(self, " \
                         f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
            output_str += f"    async def create_{message_name_snake_cased}_post(self, " \
                          f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
        else:
            output_str = f"    async def create_{message_name_snake_cased}_pre(self, " \
                         f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
            output_str += "        pass\n\n"
            output_str += f"    async def create_{message_name_snake_cased}_post(self, " \
                          f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
            output_str += "        pass\n\n"
        return output_str

    def handle_POST_all_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Dataclass:
            output_str = f"    async def create_all_{message_name_snake_cased}_pre(self, " \
                         f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
            output_str += f"    async def create_all_{message_name_snake_cased}_post(self, " \
                          f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
        else:
            output_str = f"    async def create_all_{message_name_snake_cased}_pre(self, " \
                          f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
            output_str += "        pass\n\n"
            output_str += f"    async def create_all_{message_name_snake_cased}_post(self, " \
                          f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
            output_str += "        pass\n\n"
        return output_str

    def handle_GET_callback_methods_gen(self, **kwargs) -> str:
        message, id_field_type, _ = self.unpack_kwargs_for_callback_methods(**kwargs)

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if id_field_type is None:
            output_str = f"    async def read_by_id_{message_name_snake_cased}_pre(self, obj_id: int):\n"
        else:
            output_str = f"    async def read_by_id_{message_name_snake_cased}_pre(self, obj_id: {id_field_type}):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def read_by_id_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_PUT_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Dataclass:
            output_str = f"    async def update_{message_name_snake_cased}_pre(self, " \
                         f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        return {}\n\n"
            output_str += f"    async def update_{message_name_snake_cased}_post(self, " \
                          f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
        elif model_type == ModelType.Msgspec:
            pass_stored_obj_to_pre_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiCallbackFileHandler.flux_json_root_pass_stored_obj_to_update_pre_post_callback, **kwargs)
            if pass_stored_obj_to_pre_post_callback:
                output_str = (f"    async def update_{message_name_snake_cased}_pre(self, "
                              f"stored_{message_name_snake_cased}_obj: {message.proto.name}, "
                              f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n")
                output_str += f"        return updated_{message_name_snake_cased}_obj\n\n"
                output_str += (f"    async def update_{message_name_snake_cased}_post(self, "
                               f"stored_{message_name_snake_cased}_obj: {message.proto.name}, "
                               f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n")
                output_str += "        pass\n\n"
            else:
                output_str = f"    async def update_{message_name_snake_cased}_pre(self, " \
                             f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n"
                output_str += f"        return updated_{message_name_snake_cased}_obj\n\n"
                output_str += f"    async def update_{message_name_snake_cased}_post(self, " \
                              f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n"
                output_str += "        pass\n\n"
        else:
            output_str = f"    async def update_{message_name_snake_cased}_pre(self, " \
                         f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                         f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n"
            output_str += f"        return updated_{message_name_snake_cased}_obj\n\n"
            output_str += f"    async def update_{message_name_snake_cased}_post(self, " \
                          f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                          f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n"
            output_str += "        pass\n\n"
        return output_str

    def handle_PUT_all_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Dataclass:
            output_str = f"    async def update_all_{message_name_snake_cased}_pre(self, " \
                         f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += f"        return []\n\n"
            output_str += f"    async def update_all_{message_name_snake_cased}_post(self, " \
                          f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
        elif model_type == ModelType.Msgspec:
            pass_stored_obj_to_pre_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiCallbackFileHandler.flux_json_root_pass_stored_obj_to_update_all_pre_post_callback, **kwargs)
            if pass_stored_obj_to_pre_post_callback:
                output_str = (f"    async def update_all_{message_name_snake_cased}_pre(self, "
                              f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], "
                              f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n")
                output_str += f"        return updated_{message_name_snake_cased}_obj_list\n\n"
                output_str += (f"    async def update_all_{message_name_snake_cased}_post(self, "
                               f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], "
                               f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n")
                output_str += "        pass\n\n"
            else:
                output_str = f"    async def update_all_{message_name_snake_cased}_pre(self, " \
                             f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
                output_str += f"        return updated_{message_name_snake_cased}_obj_list\n\n"
                output_str += f"    async def update_all_{message_name_snake_cased}_post(self, " \
                              f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
                output_str += "        pass\n\n"
        else:
            output_str = f"    async def update_all_{message_name_snake_cased}_pre(self, " \
                         f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                         f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
            output_str += f"        return updated_{message_name_snake_cased}_obj_list\n\n"
            output_str += f"    async def update_all_{message_name_snake_cased}_post(self, " \
                          f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                          f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
            output_str += "        pass\n\n"
        return output_str

    def handle_PATCH_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Dataclass:
            output_str = f"    async def partial_update_{message_name_snake_cased}_pre(self, " \
                         f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        return {}\n\n"
            output_str += f"    async def partial_update_{message_name_snake_cased}_post(self, " \
                          f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
        elif model_type == ModelType.Msgspec:
            output_str = f"    async def partial_update_{message_name_snake_cased}_pre(self, " \
                         f"stored_{message_name_snake_cased}_obj_json: Dict[str, Any], " \
                         f"updated_{message_name_snake_cased}_obj_json: Dict[str, Any]):\n"
            output_str += f"        return updated_{message_name_snake_cased}_obj_json\n\n"
            pass_stored_obj_to_pre_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiCallbackFileHandler.flux_json_root_pass_stored_obj_to_partial_update_pre_post_callback, **kwargs)
            if pass_stored_obj_to_pre_post_callback:
                output_str += f"    async def partial_update_{message_name_snake_cased}_post(self, " \
                              f"stored_{message_name_snake_cased}_obj_json: Dict[str, Any], " \
                              f"updated_{message_name_snake_cased}_obj_json: Dict[str, Any]):\n"
            else:
                output_str += f"    async def partial_update_{message_name_snake_cased}_post(self, " \
                              f"updated_{message_name_snake_cased}_obj_json: Dict[str, Any]):\n"
            output_str += "        pass\n\n"
        else:
            output_str = f"    async def partial_update_{message_name_snake_cased}_pre(self, " \
                         f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                         f"updated_{message_name_snake_cased}_obj_json: Dict):\n"
            output_str += f"        return updated_{message_name_snake_cased}_obj_json\n\n"
            output_str += f"    async def partial_update_{message_name_snake_cased}_post(self, " \
                          f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                          f"updated_{message_name_snake_cased}_obj: {message.proto.name}Optional):\n"
            output_str += "        pass\n\n"
        return output_str

    def handle_PATCH_all_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Dataclass:
            output_str = f"    async def partial_update_all_{message_name_snake_cased}_pre(self, " \
                         f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += f"        return []\n\n"
            output_str += f"    async def partial_update_all_{message_name_snake_cased}_post(self, " \
                          f"json_n_dataclass_handler: JsonNDataClassHandler):\n"
            output_str += "        pass\n\n"
        elif model_type == ModelType.Msgspec:
            output_str = f"    async def partial_update_all_{message_name_snake_cased}_pre(self, " \
                         f"stored_{message_name_snake_cased}_dict_list: List[Dict[str, Any]], " \
                         f"updated_{message_name_snake_cased}_dict_list: List[Dict[str, Any]]):\n"
            output_str += f"        return updated_{message_name_snake_cased}_dict_list\n\n"
            pass_stored_obj_to_pre_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiCallbackFileHandler.flux_json_root_pass_stored_obj_to_partial_update_all_pre_post_callback, **kwargs)
            if pass_stored_obj_to_pre_post_callback:
                output_str += f"    async def partial_update_all_{message_name_snake_cased}_post(self, " \
                              f"stored_{message_name_snake_cased}_dict_list: List[Dict[str, Any]], " \
                              f"updated_{message_name_snake_cased}_dict_list: List[Dict[str, Any]]):\n"
            else:
                output_str += f"    async def partial_update_all_{message_name_snake_cased}_post(self, " \
                              f"updated_{message_name_snake_cased}_dict_list: List[Dict[str, Any]]):\n"
            output_str += "        pass\n\n"
        else:
            output_str = f"    async def partial_update_all_{message_name_snake_cased}_pre(self, " \
                         f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                         f"updated_{message_name_snake_cased}_obj_json_list: List[Dict]):\n"
            output_str += f"        return updated_{message_name_snake_cased}_obj_json_list\n\n"
            output_str += f"    async def partial_update_all_{message_name_snake_cased}_post(self, " \
                          f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                          f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}Optional]):\n"
            output_str += "        pass\n\n"
        return output_str

    def handle_DELETE_callback_methods_gen(self, **kwargs) -> str:
        message, id_field_type, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            if id_field_type is None:
                output_str = f"    async def delete_{message_name_snake_cased}_pre(self, db_obj_id: int):\n"
            else:
                output_str = (f"    async def delete_{message_name_snake_cased}_pre(self, obj_id: {id_field_type}):\n")
            output_str += "        pass\n\n"
        else:
            output_str = f"    async def delete_{message_name_snake_cased}_pre(self, pydantic_obj_to_be_deleted: " \
                         f"{message.proto.name}):\n"
            output_str += "        pass\n\n"
        output_str += f"    async def delete_{message_name_snake_cased}_post(self, " \
                      f"delete_web_response):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_DELETE_all_callback_methods_gen(self, **kwargs) -> str:
        message, _, model_type = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def delete_all_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def delete_all_{message_name_snake_cased}_post(self, " \
                      f"delete_web_response):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_callback_methods_gen(self, **kwargs) -> str:
        message, id_field_type, _ = self.unpack_kwargs_for_callback_methods(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if id_field_type is None:
            output_str = f"    async def read_by_id_ws_{message_name_snake_cased}_pre(self, obj_id: int):\n"
        else:
            output_str = f"    async def read_by_id_ws_{message_name_snake_cased}_pre(self, obj_id: {id_field_type}):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def read_by_id_ws_{message_name_snake_cased}_post(self):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_get_all_message_http_callback_methods(self, message: protogen.Message) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def read_all_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def read_all_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_index_callback_methods_gen(self, message: protogen.Message) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def index_of_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def index_of_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"

        output_str += f"    async def index_of_{message_name_snake_cased}_ws_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def index_of_{message_name_snake_cased}_ws_post(self):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_get_all_message_ws_callback_methods(self, message: protogen.Message) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def read_all_ws_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def read_all_ws_{message_name_snake_cased}_post(self):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_launch_pre_and_post_callback(self) -> str:
        output_str = "    @abstractmethod\n"
        output_str += "    def app_launch_pre(self):\n"
        output_str += '        logging.debug("Pre launch Fastapi app")\n\n'
        output_str += '        NotImplementedError("derived app_launch_pre not implemented to set self.port")\n\n'

        output_str += "    def app_launch_post(self):\n"
        output_str += '        logging.debug("Post launch Fastapi app")\n'
        return output_str

    def handle_get_set_instance(self) -> str:
        output_str = f"{self.routes_callback_class_name}DerivedType = " \
                      f"TypeVar('{self.routes_callback_class_name}DerivedType', " \
                      f"bound='{self.routes_callback_class_name}')\n\n\n"
        output_str += f"class {self.routes_callback_class_name}:\n"
        output_str += f"    get_instance_mutex: threading.Lock = threading.Lock()\n"
        output_str += f"    {self.routes_callback_file_name}_instance: " \
                      f"Optional['{self.routes_callback_class_name}'] = None\n\n"
        output_str += f"    def __init__(self):\n"
        output_str += f"        self.port: int | None = None    # must be set by overridden app_launch_pre\n\n"

        output_str += f"    @classmethod\n"
        output_str += f"    def get_instance(cls) -> '{self.routes_callback_class_name}':\n"
        output_str += f"        with cls.get_instance_mutex:\n"
        output_str += f"            if cls.{self.routes_callback_file_name}_instance is None:\n"
        output_str += f'                logging.exception("Error: get_instance invoked before any server creating ' \
                      f'instance via set_instance - "\n'
        output_str += f'                                  "instantiating default!")\n'
        output_str += f'                cls.{self.routes_callback_file_name}_instance = ' \
                      f'{self.routes_callback_class_name}()\n'
        output_str += f"            return cls.{self.routes_callback_file_name}_instance\n\n"

        output_str += f"    @classmethod\n"
        output_str += f"    def set_instance(cls, instance: {self.routes_callback_class_name}" \
                      f"DerivedType, delayed_override: bool = False) -> None:\n"
        output_str += f"        if not isinstance(instance, {self.routes_callback_class_name}):\n"
        output_str += f'            raise Exception("{self.routes_callback_class_name}.' \
                      f'set_instance must be invoked ' \
                      f'with a type that is "\n'
        output_str += f'                            "subclass of ' \
                      f'{self.routes_callback_class_name} ' \
                      f'- is-subclass test failed!")\n'
        output_str += f'        if instance == cls.{self.routes_callback_file_name}_instance:\n'
        output_str += f'            return  # multiple calls with same instance is not an error (though - should be ' \
                      f'avoided where possible)\n'
        output_str += f'        with cls.get_instance_mutex:\n'
        output_str += f'            if cls.{self.routes_callback_file_name}_instance is not None:\n'
        output_str += f'                if delayed_override:\n'
        output_str += f'                    cls.{self.routes_callback_file_name}_instance = instance\n'
        output_str += f'                else:\n'
        output_str += f'                    raise Exception("Multiple ' \
                      f'{self.routes_callback_class_name}.set_instance ' \
                      f'invocation detected with "\n'
        output_str += f'                                    "different instance objects. multiple calls allowed with ' \
                      f'the exact same object only"\n'
        output_str += f'                                    ", unless delayed_override is passed explicitly as True")\n'
        output_str += f'            cls.{self.routes_callback_file_name}_instance = instance\n\n'
        return output_str

    def handle_callback_methods_output(self, model_type: ModelType = ModelType.Beanie) -> str:
        output_str = ""
        for message in self.root_message_list:
            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message, FastapiCallbackFileHandler.flux_msg_json_root))
            else:
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message,
                                                             FastapiCallbackFileHandler.flux_msg_json_root_time_series))

            crud_field_name_to_method_call_dict = {
                FastapiCallbackFileHandler.flux_json_root_create_field: self.handle_POST_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_create_all_field: self.handle_POST_all_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_read_field: self.handle_GET_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_update_field: self.handle_PUT_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_update_all_field: self.handle_PUT_all_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_patch_field: self.handle_PATCH_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_patch_all_field: self.handle_PATCH_all_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_delete_field: self.handle_DELETE_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_delete_all_field: self.handle_DELETE_all_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_read_by_id_websocket_field:
                    self.handle_read_by_id_WEBSOCKET_callback_methods_gen
            }

            output_str += self.handle_get_all_message_http_callback_methods(message)
            output_str += self.handle_get_all_message_ws_callback_methods(message)

            id_field_type = self._get_msg_id_field_type(message)

            for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
                if crud_option_field_name in option_value_dict:
                    output_str += crud_operation_method(message=message, id_field_type=id_field_type,
                                                        model_type=model_type,
                                                        json_root_option_val=option_value_dict)
                # else not required: Avoiding method creation if desc not provided in option

            for field in message.fields:
                if self.is_bool_option_enabled(field, FastapiCallbackFileHandler.flux_fld_index):
                    output_str += self.handle_index_callback_methods_gen(message)
                    break
                # else not required: Avoiding field if index option is not enabled

        return output_str

    def _handle_callback_http_query_method_output(self, message: protogen.Message, query_name: str,
                                                  agg_params_with_type_str: str, route_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if route_type is None or route_type == FastapiCallbackFileHandler.flux_json_query_route_get_type_field_val:
            if agg_params_with_type_str is not None:
                output_str = f"    async def {query_name}_query_pre(self, " \
                              f"{message_name_snake_cased}_class_type: Type[{message.proto.name}], " \
                              f"{agg_params_with_type_str}):\n"
            else:
                output_str = f"    async def {query_name}_query_pre(self, " \
                              f"{message_name_snake_cased}_class_type: Type[{message.proto.name}]):\n"
        else:
            if agg_params_with_type_str is not None:
                output_str = f"    async def {query_name}_query_pre(self, " \
                              f"{message_name_snake_cased}_class_type: Type[{message.proto.name}], " \
                              f"payload_dict: Dict[str, Any]):\n"
            else:
                err_str = f"patch query can't be generated without payload query_param, query {query_name} in " \
                          f"message {message.proto.name} found without query params"
                logging.exception(err_str)
                raise Exception(err_str)
        output_str += "        return []\n\n"
        output_str += f"    async def {query_name}_query_post(self, " \
                      f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
        output_str += f"        return {message_name_snake_cased}_obj_list\n\n"
        return output_str

    def _handle_callback_http_file_query_method_output(
            self, message: protogen.Message, query_name: str,
            agg_params_with_type_str: str | None = None) -> str:
        if agg_params_with_type_str is not None:
            output_str = f"    async def {query_name}_query_pre(self, " \
                          f"upload_file: UploadFile, " \
                          f"{agg_params_with_type_str}):\n"
        else:
            output_str = f"    async def {query_name}_query_pre(self, upload_file: UploadFile):\n"
        output_str += "        return []\n\n"
        output_str += f"    async def {query_name}_query_post(self, " \
                      f"*args, **kwargs):\n"
        output_str += f"        return []\n\n"
        return output_str

    def _handle_callback_ws_query_method_output(self, query_name: str, is_projection_query: bool | None = None) -> str:
        output_str = f"    async def {query_name}_query_ws_pre(self, *args):\n"
        if not is_projection_query:
            output_str += f"        return {query_name}_filter_callable, None\n\n"
        else:
            output_str += f"        return {query_name}_filter_callable, []\n\n"
        output_str += f"    async def {query_name}_query_ws_post(self):\n"
        output_str += f"        return None\n\n"
        return output_str

    def handle_query_filter_func_output(self, msg_name_n_ws_query_name_tuple_list) -> str:
        output_str = ""
        for msg_name, query_name in msg_name_n_ws_query_name_tuple_list:
            msg_name_snake_cased = convert_camel_case_to_specific_case(msg_name)
            output_str += f"def {query_name}_filter_callable({msg_name_snake_cased}_obj_json_str: str, **args):\n"
            output_str += f"    logging.error('WS Query option found for message {msg_name} but filter callable " \
                          f"is not overridden/defined for query pre to be returned, currently using code generated " \
                          f"implementation')\n"
            output_str += f"    return {msg_name_snake_cased}_obj_json_str\n\n\n"
        return output_str

    def _handle_callback_query_methods_output(
            self, message: protogen.Message, query_name: str, query_route_type: str,
            agg_params_with_type_str: str | None = None, query_type: str | None = None,
            msg_name_n_ws_query_name_tuple_list: List[Tuple[str, str]] | None = None) -> str:
        output_str = ""

        if query_type is None or query_type == "http":
            output_str += self._handle_callback_http_query_method_output(message, query_name,
                                                                         agg_params_with_type_str,
                                                                         query_route_type)
        elif query_type == "ws":
            output_str += self._handle_callback_ws_query_method_output(query_name)
            msg_name_n_ws_query_name_tuple_list.append((message.proto.name, query_name))
        elif query_type == "both":
            output_str += self._handle_callback_http_query_method_output(message, query_name,
                                                                         agg_params_with_type_str,
                                                                         query_route_type)
            output_str += self._handle_callback_ws_query_method_output(query_name)
            msg_name_n_ws_query_name_tuple_list.append((message.proto.name, query_name))
        elif query_type == "http_file":
            output_str += self._handle_callback_http_file_query_method_output(message, query_name,
                                                                              agg_params_with_type_str)
        else:
            err_str = f"Unsupported Query type for query base callback code generation {query_type}"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str

    def handle_callback_query_methods_output(self, msg_name_n_ws_query_name_tuple_list: List[Tuple[str, str]]) -> str:
        output_str = ""

        for message in self.message_to_query_option_list_dict:
            aggregate_value_list = self.message_to_query_option_list_dict[message]

            for aggregate_value in aggregate_value_list:
                query_name = aggregate_value[FastapiCallbackFileHandler.query_name_key]
                query_params = aggregate_value[FastapiCallbackFileHandler.query_params_key]
                query_params_data_types = aggregate_value[FastapiCallbackFileHandler.query_params_data_types_key]
                query_type_value = aggregate_value[FastapiCallbackFileHandler.query_type_key]
                query_type = str(query_type_value).lower() if query_type_value is not None else None
                query_route_type_value = aggregate_value[FastapiCallbackFileHandler.query_route_type_key]
                query_route_type = str(query_route_type_value).lower() if query_route_type_value is not None else "GET"

                agg_params_with_type_str = None
                if query_params:
                    agg_params_with_type_str = ", ".join([f"{param}: {param_type}"
                                                          for param, param_type in zip(query_params,
                                                                                       query_params_data_types)])

                output_str += self._handle_callback_query_methods_output(
                    message, query_name, query_route_type, agg_params_with_type_str, query_type,
                    msg_name_n_ws_query_name_tuple_list)

        for message, query_data_dict_list in self.message_to_button_query_data_dict.items():
            for query_data_dict in query_data_dict_list:
                query_data = query_data_dict.get(FastapiCallbackFileHandler.button_query_data_key)
                query_name = query_data.get(FastapiCallbackFileHandler.flux_json_query_name_field)
                query_params = query_data.get(FastapiCallbackFileHandler.flux_json_query_params_field)
                query_params_data_types = query_data.get(
                    FastapiCallbackFileHandler.flux_json_query_params_data_type_field)
                query_type_value = query_data.get(FastapiCallbackFileHandler.flux_json_query_type_field)
                query_type = str(query_type_value).lower() if query_type_value is not None else None
                query_route_type_value = query_data.get(FastapiCallbackFileHandler.flux_json_query_route_type_field)
                query_route_type = str(query_route_type_value).lower() if query_route_type_value is not None else "GET"

                agg_params_with_type_str = None
                if query_params:
                    agg_params_with_type_str = ", ".join([f"{param}: {param_type}"
                                                          for param, param_type in zip(query_params,
                                                                                       query_params_data_types)])
                if query_type == "http_file":
                    file_upload_data = query_data_dict.get(
                        FastapiCallbackFileHandler.button_query_file_upload_options_key)
                    disallow_duplicate_file_upload = False
                    if file_upload_data:
                        disallow_duplicate_file_upload = file_upload_data.get("disallow_duplicate_file_upload")

                    if agg_params_with_type_str:
                        if disallow_duplicate_file_upload:
                            agg_params_with_type_str += ", disallow_duplicate_file_upload: bool = True"
                        else:
                            agg_params_with_type_str += ", disallow_duplicate_file_upload: bool = False"
                    else:
                        if disallow_duplicate_file_upload:
                            agg_params_with_type_str = "disallow_duplicate_file_upload: bool = True"
                        else:
                            agg_params_with_type_str = "disallow_duplicate_file_upload: bool = False"
                output_str += self._handle_callback_query_methods_output(
                    message, query_name, query_route_type, agg_params_with_type_str, query_type,
                    [])

        output_str += "\n"

        return output_str

    def handle_callback_projection_query_methods_output(self,
                                                        msg_name_n_ws_query_name_tuple_list: List[Tuple[str, str]]
                                                        ) -> str:
        output_str = ""

        for message in self.root_message_list:
            if FastapiCallbackFileHandler.is_option_enabled(message,
                                                            FastapiCallbackFileHandler.flux_msg_json_root_time_series):
                for field in message.fields:
                    if FastapiCallbackFileHandler.is_option_enabled(field,
                                                                    FastapiCallbackFileHandler.flux_fld_projections):
                        break
                else:
                    # If no field is found having projection enabled
                    continue

                meta_data_field_name_to_field_proto_dict: Dict[str, (protogen.Field | Dict[str, protogen.Field])] = (
                    self.get_meta_data_field_name_to_field_proto_dict(message))
                projection_val_to_query_name_dict = (
                    FastapiCallbackFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
                for projection_option_val, query_name in projection_val_to_query_name_dict.items():
                    query_param_with_type_str = ""
                    for meta_field_name, meta_field_value in meta_data_field_name_to_field_proto_dict.items():
                        if isinstance(meta_field_value, dict):
                            for nested_meta_field_name, nested_meta_field in meta_field_value.items():
                                query_param_with_type_str += (f"{nested_meta_field_name}: "
                                                              f"{self.proto_to_py_datatype(nested_meta_field)}, ")
                        else:
                            query_param_with_type_str += (f"{meta_field_name}: "
                                                          f"{self.proto_to_py_datatype(meta_field_value)}, ")
                    query_param_with_type_str += ("start_date_time: DateTime | None = None, "
                                                  "end_date_time: DateTime | None = None")
                    # http
                    output_str += self._handle_callback_http_query_method_output(message, query_name,
                                                                                 query_param_with_type_str)
                    # WS
                    output_str += self._handle_callback_ws_query_method_output(query_name, True)
                    msg_name_n_ws_query_name_tuple_list.append((message.proto.name, query_name))

        return output_str

    def handle_callback_class_file_gen(self) -> str:
        output_str = "import threading\n"
        output_str += "import logging\n"
        output_str += "from abc import abstractmethod\n"
        output_str += "from typing import Optional, TypeVar, List, Type\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"
        output_str += self.handle_get_set_instance()

        # Adding app pre- and post-launch methods
        output_str += self.handle_launch_pre_and_post_callback()
        output_str += "\n"

        output_str += self.handle_callback_methods_output()

        msg_name_n_ws_query_name_tuple_list: List = []      # to be populated in below calls
        output_str += self.handle_callback_query_methods_output(msg_name_n_ws_query_name_tuple_list)
        output_str += self.handle_callback_projection_query_methods_output(msg_name_n_ws_query_name_tuple_list)
        output_str += self.handle_query_filter_func_output(msg_name_n_ws_query_name_tuple_list)

        return output_str

    def handle_dataclass_callback_class_file_gen(self) -> str:
        output_str = "import threading\n"
        output_str += "import logging\n"
        output_str += "from abc import abstractmethod\n"
        output_str += "from typing import Optional, TypeVar, List, Type\n"
        output_str += f"from FluxPythonUtils.scripts.model_base_utils import JsonNDataClassHandler\n\n\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"
        output_str += self.handle_get_set_instance()

        # Adding app pre- and post-launch methods
        output_str += self.handle_launch_pre_and_post_callback()
        output_str += "\n"

        output_str += self.handle_callback_methods_output(model_type=ModelType.Dataclass)

        msg_name_n_ws_query_name_tuple_list: List = []      # to be populated in below calls
        output_str += self.handle_callback_query_methods_output(msg_name_n_ws_query_name_tuple_list)
        output_str += self.handle_callback_projection_query_methods_output(msg_name_n_ws_query_name_tuple_list)
        output_str += self.handle_query_filter_func_output(msg_name_n_ws_query_name_tuple_list)

        return output_str

    def handle_msgspec_callback_class_file_gen(self, file: protogen.File | None = None,
                                               model_file_suffix: str | None = None) -> str:
        output_str = "import threading\n"
        output_str += "import logging\n"
        output_str += "from abc import abstractmethod\n"
        output_str += "from fastapi import UploadFile\n"
        output_str += "from typing import Optional, TypeVar, List, Type\n"
        output_str += f'\n\n'
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"

        if file and model_file_suffix:
            project_grp_root_dir = PurePath(project_dir).parent.parent / "Pydantic"
            dependency_file_path_list = self.get_dependency_file_path_list(
                file, root_core_proto_files, project_grp_core_proto_files,
                model_file_suffix, str(project_grp_root_dir))

            project_name = file.proto.package
            for dependency_file_path in dependency_file_path_list:
                if f"_n_{project_name}" in dependency_file_path or f"{project_name}_n_" in dependency_file_path:
                    output_str += f'from {dependency_file_path} import *\n'
        output_str += self.handle_get_set_instance()

        # Adding app pre- and post-launch methods
        output_str += self.handle_launch_pre_and_post_callback()
        output_str += "\n"

        output_str += self.handle_callback_methods_output(model_type=ModelType.Msgspec)

        msg_name_n_ws_query_name_tuple_list: List = []      # to be populated in below calls
        output_str += self.handle_callback_query_methods_output(msg_name_n_ws_query_name_tuple_list)
        output_str += self.handle_callback_projection_query_methods_output(msg_name_n_ws_query_name_tuple_list)
        output_str += self.handle_query_filter_func_output(msg_name_n_ws_query_name_tuple_list)

        return output_str
