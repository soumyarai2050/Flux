import os
import time
from abc import ABC

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiCallbackFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_POST_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def create_{message_name_snake_cased}_pre(self, " \
                     f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def create_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_GET_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
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

    def handle_PUT_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def update_{message_name_snake_cased}_pre(self, " \
                     f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                     f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += f"        return updated_{message_name_snake_cased}_obj\n\n"
        output_str += f"    async def update_{message_name_snake_cased}_post(self, " \
                      f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                      f"updated_{message_name_snake_cased}_obj: {message.proto.name}):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_PATCH_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def partial_update_{message_name_snake_cased}_pre(self, " \
                     f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                     f"updated_{message_name_snake_cased}_obj: {message.proto.name}Optional):\n"
        output_str += f"        return updated_{message_name_snake_cased}_obj\n\n"
        output_str += f"    async def partial_update_{message_name_snake_cased}_post(self, " \
                      f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                      f"updated_{message_name_snake_cased}_obj: {message.proto.name}Optional):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_DELETE_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def delete_{message_name_snake_cased}_pre(self, pydantic_obj_to_be_deleted: " \
                     f"{message.proto.name}):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def delete_{message_name_snake_cased}_post(self, " \
                      f"delete_web_response):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_callback_methods_gen(self, message: protogen.Message,
                                                         id_field_type: str | None = None) -> str:
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
        output_str = "    def app_launch_pre(self):\n"
        output_str += '        logging.debug("Pre launch Fastapi app")\n\n'
        output_str += "    def app_launch_post(self):\n"
        output_str += '        logging.debug("Post launch Fastapi app")\n'
        return output_str

    def handle_get_set_instance(self) -> str:
        output_str = f"{self.routes_callback_class_name_capital_camel_cased}DerivedType = " \
                      f"TypeVar('{self.routes_callback_class_name_capital_camel_cased}DerivedType', " \
                      f"bound='{self.routes_callback_class_name_capital_camel_cased}')\n\n\n"
        output_str += f"class {self.routes_callback_class_name_capital_camel_cased}:\n"
        output_str += f"    get_instance_mutex: threading.Lock = threading.Lock()\n"
        output_str += f"    {self.routes_callback_class_name}_instance: " \
                      f"Optional['{self.routes_callback_class_name_capital_camel_cased}'] = None\n\n"
        output_str += f"    def __init__(self):\n"
        output_str += f"        pass\n\n"

        output_str += f"    @classmethod\n"
        output_str += f"    def get_instance(cls) -> '{self.routes_callback_class_name_capital_camel_cased}':\n"
        output_str += f"        with cls.get_instance_mutex:\n"
        output_str += f"            if cls.{self.routes_callback_class_name}_instance is None:\n"
        output_str += f'                logging.exception("Error: get_instance invoked before any server creating ' \
                      f'instance via set_instance - "\n'
        output_str += f'                                  "instantiating default!")\n'
        output_str += f'                cls.{self.routes_callback_class_name}_instance = ' \
                      f'{self.routes_callback_class_name_capital_camel_cased}()\n'
        output_str += f"            return cls.{self.routes_callback_class_name}_instance\n\n"

        output_str += f"    @classmethod\n"
        output_str += f"    def set_instance(cls, instance: {self.routes_callback_class_name_capital_camel_cased}" \
                      f"DerivedType, delayed_override: bool = False) -> None:\n"
        output_str += f"        if not isinstance(instance, {self.routes_callback_class_name_capital_camel_cased}):\n"
        output_str += f'            raise Exception("{self.routes_callback_class_name_capital_camel_cased}.' \
                      f'set_instance must be invoked ' \
                      f'with a type that is "\n'
        output_str += f'                            "subclass of ' \
                      f'{self.routes_callback_class_name_capital_camel_cased} ' \
                      f'- is-subclass test failed!")\n'
        output_str += f'        if instance == cls.{self.routes_callback_class_name}_instance:\n'
        output_str += f'            return  # multiple calls with same instance is not an error (though - should be ' \
                      f'avoided where possible)\n'
        output_str += f'        with cls.get_instance_mutex:\n'
        output_str += f'            if cls.{self.routes_callback_class_name}_instance is not None:\n'
        output_str += f'                if delayed_override:\n'
        output_str += f'                    cls.{self.routes_callback_class_name}_instance = instance\n'
        output_str += f'                else:\n'
        output_str += f'                    raise Exception("Multiple ' \
                      f'{self.routes_callback_class_name_capital_camel_cased}.set_instance ' \
                      f'invocation detected with "\n'
        output_str += f'                                    "different instance objects. multiple calls allowed with ' \
                      f'the exact same object only"\n'
        output_str += f'                                    ", unless delayed_override is passed explicitly as True")\n'
        output_str += f'            cls.{self.routes_callback_class_name}_instance = instance\n\n'
        return output_str

    def handle_callback_methods_output(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            options_list_of_dict = \
                self.get_complex_option_values_as_list_of_dict(message,
                                                               FastapiCallbackFileHandler.flux_msg_json_root)

            # Since json_root option is of non-repeated type
            option_dict = options_list_of_dict[0]

            crud_field_name_to_method_call_dict = {
                FastapiCallbackFileHandler.flux_json_root_create_field: self.handle_POST_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_read_field: self.handle_GET_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_update_field: self.handle_PUT_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_patch_field: self.handle_PATCH_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_delete_field: self.handle_DELETE_callback_methods_gen,
                FastapiCallbackFileHandler.flux_json_root_read_websocket_field:
                    self.handle_read_by_id_WEBSOCKET_callback_methods_gen
            }

            output_str += self.handle_get_all_message_http_callback_methods(message)
            output_str += self.handle_get_all_message_ws_callback_methods(message)

            id_field_type = self._get_msg_id_field_type(message)

            for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
                if crud_option_field_name in option_dict:
                    output_str += crud_operation_method(message, id_field_type)
                # else not required: Avoiding method creation if desc not provided in option

            for field in message.fields:
                if self.is_bool_option_enabled(field, FastapiCallbackFileHandler.flux_fld_index):
                    output_str += self.handle_index_callback_methods_gen(message)
                    break
                # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_callback_query_methods_output(self) -> str:
        output_str = ""

        for message in self.message_to_query_option_list_dict:
            aggregate_value_list = self.message_to_query_option_list_dict[message]

            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            for aggregate_value in aggregate_value_list:
                aggregate_var_name = aggregate_value[FastapiCallbackFileHandler.aggregate_var_name_key]
                aggregate_params = aggregate_value[FastapiCallbackFileHandler.aggregate_params_key]
                aggregate_params_data_types = aggregate_value[FastapiCallbackFileHandler.aggregate_params_data_types_key]

                if aggregate_params:
                    agg_params_with_type_str = ", ".join([f"{param}: {param_type}"
                                                          for param, param_type in zip(aggregate_params,
                                                                                       aggregate_params_data_types)])
                    output_str += f"    async def {aggregate_var_name}_query_pre(self, " \
                                  f"{message_name_snake_cased}_class_type: Type[{message.proto.name}], " \
                                  f"{agg_params_with_type_str}):\n"
                    output_str += "        return []\n\n"
                    output_str += f"    async def {aggregate_var_name}_query_post(self, " \
                                  f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
                    output_str += f"        return {message_name_snake_cased}_obj_list\n\n"
                else:
                    output_str += f"    async def {aggregate_var_name}_query_pre(self, " \
                                  f"{message_name_snake_cased}_class_type: Type[{message.proto.name}]):\n"
                    output_str += "        return []\n\n"
                    output_str += f"    async def {aggregate_var_name}_query_post(self, " \
                                  f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
                    output_str += f"        return {message_name_snake_cased}_obj_list\n\n"

        return output_str

    def handle_callback_class_file_gen(self) -> str:
        output_str = "import threading\n"
        output_str += "import logging\n"
        output_str += "from typing import Optional, TypeVar, List, Type\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str += f"from {model_file_path} import *\n"
        output_str += self.handle_get_set_instance()

        # Adding app pre- and post-launch methods
        output_str += self.handle_launch_pre_and_post_callback()
        output_str += "\n"

        output_str += self.handle_callback_methods_output()
        output_str += self.handle_callback_query_methods_output()

        return output_str
