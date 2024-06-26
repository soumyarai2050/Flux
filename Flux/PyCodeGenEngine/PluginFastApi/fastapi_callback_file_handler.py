import os
import time
from abc import ABC
import logging
from typing import List, Tuple, Dict

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
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

    def handle_POST_all_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def create_all_{message_name_snake_cased}_pre(self, " \
                      f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def create_all_{message_name_snake_cased}_post(self, " \
                      f"{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
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

    def handle_PUT_all_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def update_all_{message_name_snake_cased}_pre(self, " \
                     f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                     f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
        output_str += f"        return updated_{message_name_snake_cased}_obj_list\n\n"
        output_str += f"    async def update_all_{message_name_snake_cased}_post(self, " \
                      f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                      f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}]):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_PATCH_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def partial_update_{message_name_snake_cased}_pre(self, " \
                     f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                     f"updated_{message_name_snake_cased}_obj_json: Dict):\n"
        output_str += f"        return updated_{message_name_snake_cased}_obj_json\n\n"
        output_str += f"    async def partial_update_{message_name_snake_cased}_post(self, " \
                      f"stored_{message_name_snake_cased}_obj: {message.proto.name}, " \
                      f"updated_{message_name_snake_cased}_obj: {message.proto.name}Optional):\n"
        output_str += "        pass\n\n"
        return output_str

    def handle_PATCH_all_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def partial_update_all_{message_name_snake_cased}_pre(self, " \
                     f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                     f"updated_{message_name_snake_cased}_obj_json_list: List[Dict]):\n"
        output_str += f"        return updated_{message_name_snake_cased}_obj_json_list\n\n"
        output_str += f"    async def partial_update_all_{message_name_snake_cased}_post(self, " \
                      f"stored_{message_name_snake_cased}_obj_list: List[{message.proto.name}], " \
                      f"updated_{message_name_snake_cased}_obj_list: List[{message.proto.name}Optional]):\n"
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

    def handle_DELETE_all_callback_methods_gen(self, message: protogen.Message, id_field_type: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f"    async def delete_all_{message_name_snake_cased}_pre(self):\n"
        output_str += "        pass\n\n"
        output_str += f"    async def delete_all_{message_name_snake_cased}_post(self, " \
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
        output_str = "    @abstractmethod\n"
        output_str += "    def app_launch_pre(self):\n"
        output_str += '        logging.debug("Pre launch Fastapi app")\n\n'
        output_str += '        NotImplementedError("derived app_launch_pre not implemented to set self.port")\n\n'

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
        output_str += f"        self.port: int | None = None    # must be set by overridden app_launch_pre\n\n"

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
                    output_str += crud_operation_method(message, id_field_type)
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
                else:
                    err_str = f"Unsupported Query type for query base callback code generation {query_type}"
                    logging.exception(err_str)
                    raise Exception(err_str)

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
