import os
import time
from abc import ABC
from typing import List, Dict, Tuple, Set
import logging

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    parse_string_to_original_types, convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_base_routes_file_handler import FastapiBaseRoutesFileHandler, ModelType


class FastapiWsRoutesFileHandler(FastapiBaseRoutesFileHandler, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.shared_lock_name_to_model_class_dict: Dict[str, List[protogen.Message]] = {}
        self.shared_lock_name_message_list: List[protogen.Message] = []
        self.message_to_link_messages_dict: Dict[protogen.Message, List[protogen.Message]] = {}

    def _get_list_of_shared_lock_for_message(self, message: protogen.Message) -> List[str]:
        shared_lock_name_list = []
        for shared_lock_name, message_list in self.shared_lock_name_to_model_class_dict.items():
            if message in message_list:
                shared_lock_name_list.append(shared_lock_name)
        return shared_lock_name_list

    def _underlying_handle_generic_imports(self) -> str:
        generic_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_routes")
        output_str = f'from {generic_routes_file_path} import *\n'
        return output_str

    def _handle_underlying_mutex_str(self, message: protogen.Message, shared_lock_list: List[str]) -> Tuple[str, int]:
        output_str = ""
        indent_times = 0

        if shared_lock_list:
            for shared_lock in shared_lock_list:
                output_str += " " * (indent_times * 4) + f"    async with {shared_lock}:\n"
                indent_times += 1
        else:
            if message not in self.reentrant_lock_non_required_msg:
                output_str += " " * (indent_times * 4) + f"    async with {message.proto.name}.reentrant_lock:\n"
                indent_times += 1

        indent_count = indent_times * 4
        return output_str, indent_count

    def _get_filter_tuple_str(self, index_fields: List[protogen.Field]) -> str:
        filter_tuples_str = ""
        for field in index_fields:
            filter_tuples_str += f"('{field.proto.name}', [{field.proto.name}])"
            if field != index_fields[-1]:
                filter_tuples_str += ", "
        return filter_tuples_str

    def handle_underlying_index_ws_req_gen(self, message: protogen.Message,
                                           shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, FastapiWsRoutesFileHandler.flux_fld_index)]

        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])
        output_str = f"async def underlying_get_{message_name_snake_cased}_from_index_fields_ws(websocket: WebSocket," \
                     f" {field_params}, filter_agg_pipeline: Any = None):\n"
        output_str += f'    """ Index route of {message.proto.name} """\n'
        output_str += f"    await callback_class.index_of_{message_name_snake_cased}_ws_pre()\n"
        filter_configs_var_name = self._get_filter_configs_var_name(message, None)
        if filter_configs_var_name:
            output_str += f"    indexed_filter = copy.deepcopy({filter_configs_var_name})\n"
            output_str += f"    indexed_filter['match'] = [{self._get_filter_tuple_str(index_fields)}]\n"
        else:
            output_str += "    indexed_filter = {'match': " + f"[{self._get_filter_tuple_str(index_fields)}]" + "}\n"
        output_str += f"    if filter_agg_pipeline is not None:\n"
        output_str += f"        await generic_read_ws(websocket, {FastapiWsRoutesFileHandler.proto_package_var_name}, " \
                      f"{message.proto.name}, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += "    else:\n"
        output_str += f"        await generic_read_ws(websocket, {FastapiWsRoutesFileHandler.proto_package_var_name}, " \
                      f"{message.proto.name}, indexed_filter, has_links={msg_has_links})\n"
        output_str += f"    await callback_class.index_of_{message_name_snake_cased}_ws_post()\n\n"
        return output_str

    def handle_index_ws_req_gen(self, message: protogen.Message, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_index_ws_req_gen(message, shared_lock_list)
        output_str += "\n"
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, FastapiWsRoutesFileHandler.flux_fld_index)]

        field_query = "/".join(["{" + f"{field.proto.name}" + "}" for field in index_fields])
        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])

        output_str += f'@{self.api_router_app_name}.websocket("/get-{message_name_snake_cased}-from-index-fields-ws/' + \
                      f'{field_query}' + f'")\n'
        output_str += f"async def get_{message_name_snake_cased}_from_index_fields_ws(websocket: WebSocket, " \
                      f"{field_params}):\n"
        field_params = ", ".join([f"{field.proto.name}" for field in index_fields])
        output_str += \
            f"    await underlying_get_{message_name_snake_cased}_from_index_fields_ws(websocket, {field_params})\n\n\n"
        return output_str

    def handle_underlying_GET_ws_gen(self, **kwargs):
        message, aggregation_type, id_field_type, shared_lock_list, _ = self._unpack_kwargs_with_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        if id_field_type is not None:
            output_str = f"async def underlying_read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                         f"{message_name_snake_cased}_id: {id_field_type}, " \
                         f"filter_agg_pipeline: Any = None, need_initial_snapshot: bool | None = True) -> None:\n"
        else:
            output_str = f"async def underlying_read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                         f"{message_name_snake_cased}_id: {FastapiWsRoutesFileHandler.default_id_type_var_name}, " \
                         f"filter_agg_pipeline: Any = None) -> None:\n"
        output_str += f'    """\n'
        output_str += f'    Read by id using websocket route for {message.proto.name}\n'
        output_str += f'    """\n'

        output_str += f"    await callback_class.read_by_id_ws_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_id)\n"
        output_str += f"    if filter_agg_pipeline is not None:\n"
        output_str += f"        await generic_read_by_id_ws(websocket, " \
                      f"{FastapiWsRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name}, {message_name_snake_cased}_id, filter_agg_pipeline, " \
                      f"has_links={msg_has_links}, need_initial_snapshot=need_initial_snapshot)\n"
        output_str += "    else:\n"
        match aggregation_type:
            case FastapiWsRoutesFileHandler.aggregation_type_filter:
                output_str += \
                    (f"        await generic_read_by_id_ws(websocket, "
                     f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                     f"{message_name}, {message_name_snake_cased}_id, "
                     f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_id')}, "
                     f"has_links={msg_has_links}, "
                     f"need_initial_snapshot=need_initial_snapshot)\n")
            case FastapiWsRoutesFileHandler.aggregation_type_update | FastapiWsRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in read by id operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += \
                    (f"        await generic_read_by_id_ws(websocket, "
                     f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                     f"{message_name}, {message_name_snake_cased}_id, has_links={msg_has_links}, "
                     f"need_initial_snapshot=need_initial_snapshot)\n")
        output_str += f"    await callback_class.read_by_id_ws_{message_name_snake_cased}_post()\n"
        output_str += "\n"
        return output_str

    def handle_GET_ws_gen(self, **kwargs):
        message, _, id_field_type, _, _ = self._unpack_kwargs_with_id_field_type(**kwargs)
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = self.handle_underlying_GET_ws_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.websocket("/get-{message_name_snake_cased}-ws/' + \
                      '{' + f'{message_name_snake_cased}_id' + '}")\n'
        if id_field_type is not None:
            output_str += (f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, "
                           f"{message_name_snake_cased}_id: {id_field_type}, "
                           f"need_initial_snapshot: bool | None = True) -> None:\n")
        else:
            output_str += (f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, "
                           f"{message_name_snake_cased}_id: {FastapiWsRoutesFileHandler.default_id_type_var_name},"
                           f"need_initial_snapshot: bool | None = True) -> None:\n")
        output_str += f"    await underlying_read_{message_name_snake_cased}_by_id_ws(websocket, " \
                      f"{message_name_snake_cased}_id, need_initial_snapshot=need_initial_snapshot)\n"
        return output_str

    def handle_underlying_GET_ALL_ws_gen(self, message: protogen.Message, aggregation_type: str,
                                         shared_lock_list: List[str] | None = None):
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = (f"async def underlying_read_{message_name_snake_cased}_ws(websocket: WebSocket, "
                      f"filter_agg_pipeline: Any = None, need_initial_snapshot: bool | None = True, "
                      f"limit_obj_count: int | None = None) -> None:\n")
        output_str += f'    """ Get All {message_name} using websocket """\n'

        output_str += f"    await callback_class.read_all_ws_{message_name_snake_cased}_pre()\n"
        output_str += f"    if filter_agg_pipeline is not None:\n"
        output_str += (f"        await generic_read_ws(websocket, "
                       f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                       f"{message_name}, filter_agg_pipeline, has_links={msg_has_links}, "
                       f"need_initial_snapshot=need_initial_snapshot)\n")
        output_str += "    else:\n"
        match aggregation_type:
            case FastapiWsRoutesFileHandler.aggregation_type_filter:
                output_str += \
                    (f"        await generic_read_ws(websocket, {FastapiWsRoutesFileHandler.proto_package_var_name}, "
                     f"{message_name}, {self._get_filter_configs_var_name(message, None, put_limit=True)}, "
                     f"has_links={msg_has_links}, need_initial_snapshot=need_initial_snapshot)\n")
            case FastapiWsRoutesFileHandler.aggregation_type_update | FastapiWsRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in real all websocket operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += "        limit_filter_agg: Dict[str, Any] | None = None\n"
                output_str += "        if limit_obj_count is not None:\n"
                output_str += "            limit_filter_agg = {'agg': get_limited_objs(limit_obj_count)}\n"
                output_str += \
                    (f"        await generic_read_ws(websocket, {FastapiWsRoutesFileHandler.proto_package_var_name}, "
                     f"{message_name}, limit_filter_agg, has_links={msg_has_links}, "
                     f"need_initial_snapshot=need_initial_snapshot)\n")
        output_str += f"    await callback_class.read_all_ws_{message_name_snake_cased}_post()\n\n"
        return output_str

    def handle_GET_ALL_ws_gen(self, message: protogen.Message, aggregation_type: str,
                              shared_lock_list: List[str] | None = None):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = self.handle_underlying_GET_ALL_ws_gen(message, aggregation_type, shared_lock_list)
        output_str += f"\n"
        output_str += (f'@{self.api_router_app_name}.websocket("/get-all-{message_name_snake_cased}-ws")\n')
        output_str += (f"async def read_{message_name_snake_cased}_ws(websocket: WebSocket, "
                       f"need_initial_snapshot: bool | None = True, limit_obj_count: int | None = None) -> None:\n")
        additional_agg_option_val_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     FastapiWsRoutesFileHandler.flux_msg_main_crud_operations_agg)
        override_default_get_all_limit = additional_agg_option_val_dict.get("override_get_all_limit_handling")
        if not override_default_get_all_limit:
            output_str += "    limit_filter_agg: Dict[str, Any] | None = None\n"
            output_str += "    if limit_obj_count is not None:\n"
            output_str += "        limit_filter_agg = {'agg': get_limited_objs(limit_obj_count)}\n"
            output_str += (f"    await underlying_read_{message_name_snake_cased}_ws(websocket, "
                           f"limit_filter_agg, need_initial_snapshot)\n\n\n")
        else:
            output_str += (f"    await underlying_read_{message_name_snake_cased}_ws(websocket, "
                           f"need_initial_snapshot=need_initial_snapshot, "
                           f"limit_obj_count=limit_obj_count)\n\n\n")
        return output_str

    def handle_field_web_socket_gen(self, message: protogen.Message, field: protogen.Field):
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        field_name = field.proto.name
        field_type = self.proto_to_py_datatype(field)
        output_str = f'@{self.api_router_app_name}.websocket("/ws-read-{message_name_snake_cased}-for-{field_name}/")\n'
        output_str += f"async def ws_read_{message_name_snake_cased}_for_{field_name}(websocket: WebSocket, " \
                      f"{field_name}: {field_type}) -> None:\n"
        output_str += f'    """ websocket for {field_name} field of {message.proto.name} """\n'
        output_str += f"    await websocket.accept()\n"
        output_str += f"    while True:\n"
        output_str += f"        data = await websocket.receive()\n"
        output_str += f"        await websocket.send(data)\n\n\n"
        return output_str

    def _check_agg_info_availability(self, aggregation_type: str, crud_option_field_name: str,
                                     message: protogen.Message) -> str:
        """
        Checks if message having json_root option field for specific crud method generation has
        dependent options set or not
        :returns:
            returns same aggregation_type if check passes
        """
        err_str = f"Message {message.proto.name} has json root option field" \
                  f"{crud_option_field_name} of enum type "
        match aggregation_type:
            case FastapiWsRoutesFileHandler.aggregation_type_both:
                if not (self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name) or
                        self.is_option_enabled(message,
                                               FastapiWsRoutesFileHandler.flux_msg_main_crud_operations_agg)) and \
                        self.is_option_enabled(message,
                                               FastapiWsRoutesFileHandler.flux_msg_nested_fld_val_filter_param):
                    err_str += f"{aggregation_type} but not has " \
                               f"both {FastapiWsRoutesFileHandler.flux_msg_nested_fld_val_filter_param} and " \
                               f"{FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name} options set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiWsRoutesFileHandler.aggregation_type_filter:
                if not (self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_nested_fld_val_filter_param)
                        or
                        self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_main_crud_operations_agg)):
                    err_str += f"{aggregation_type} but not has " \
                               f"{FastapiWsRoutesFileHandler.flux_msg_nested_fld_val_filter_param} option set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiWsRoutesFileHandler.aggregation_type_update:
                if not self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name):
                    err_str += f"{aggregation_type} but not has " \
                               f"{FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name} option set, " \
                               f"Please check if json_root fields are set to specified if no " \
                               f"{FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name} option is set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiWsRoutesFileHandler.aggregation_type_unspecified:
                pass
            case other:
                err_str = f"Unsupported option field {other} in json_root option"
                logging.exception(err_str)
                raise Exception(err_str)
        return aggregation_type

    def _handle_ws_routes_methods(self, message: protogen.Message) -> str:
        output_str = ""

        if self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_json_root):
            option_val_dict = self.get_complex_option_value_from_proto(message, FastapiWsRoutesFileHandler.flux_msg_json_root)
        else:
            option_val_dict = self.get_complex_option_value_from_proto(message,
                                                                       FastapiWsRoutesFileHandler.flux_msg_json_root_time_series)

        shared_mutex_list = self._get_list_of_shared_lock_for_message(message)

        if (aggregation_type := option_val_dict.get(
                FastapiWsRoutesFileHandler.flux_json_root_read_field)) is not None:
            output_str += \
                self.handle_GET_ALL_ws_gen(message, aggregation_type.strip(), shared_mutex_list)
        # else not required: avoiding find_all route for this message if read_ws_field of json_root option is not set

        id_field_type: str = self._get_msg_id_field_type(message)

        if FastapiWsRoutesFileHandler.flux_json_root_read_by_id_websocket_field in option_val_dict:
            aggregation_type: str = (
                self._check_agg_info_availability(
                    option_val_dict[FastapiWsRoutesFileHandler.flux_json_root_read_by_id_websocket_field].strip(),
                    FastapiWsRoutesFileHandler.flux_json_root_read_by_id_websocket_field, message))
            output_str += self.handle_GET_ws_gen(message=message, aggregation_type=aggregation_type,
                                                 id_field_type=id_field_type, shared_mutex_list=shared_mutex_list)
            output_str += "\n\n"

        for field in message.fields:
            if self.is_bool_option_enabled(field, FastapiWsRoutesFileHandler.flux_fld_web_socket):
                output_str += self.handle_field_web_socket_gen(message, field)
            # else not required: Avoiding field if websocket option is not enabled

        for field in message.fields:
            if self.is_bool_option_enabled(field, FastapiWsRoutesFileHandler.flux_fld_index):
                output_str += self.handle_index_ws_req_gen(message, shared_mutex_list)
                break
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def _handle_ws_query_str(self, message: protogen.Message, query_name: str, query_params_str: str,
                             query_params_with_type_str: str, query_args_dict_str: str) -> str:
        output_str = f"@perf_benchmark\n"
        output_str += (f"async def underlying_{query_name}_query_ws(websocket: WebSocket, "
                       f"{query_params_with_type_str}, need_initial_snapshot: bool | None = True):\n")
        output_str += (f"    filter_callable, filter_agg_pipeline_list = "
                       f"await callback_class.{query_name}_query_ws_pre({query_params_str})\n")
        output_str += "    filter_agg_pipeline_dict = {'agg': filter_agg_pipeline_list}\n"
        output_str += f'    params_json = {query_args_dict_str}\n'
        output_str += (f"    await generic_query_ws(websocket, "
                       f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                       f"{message.proto.name}, filter_callable, params_json, "
                       f"filter_agg_pipeline=filter_agg_pipeline_dict")
        output_str += ", need_initial_snapshot=need_initial_snapshot)\n"
        output_str += f"    await callback_class.{query_name}_query_ws_post()\n"
        output_str += f"\n\n"
        output_str += f'@{self.api_router_app_name}.websocket("/ws-query-{query_name}")\n'
        output_str += (f"async def {query_name}_query_ws(websocket: WebSocket, {query_params_with_type_str}, "
                       f"need_initial_snapshot: bool | None = True):\n")
        output_str += f'    """\n'
        output_str += f'    WS Query of {message.proto.name} with aggregate - {query_name}\n'
        output_str += f'    """\n'
        output_str += (f"    await underlying_{query_name}_query_ws(websocket, {query_params_str}, "
                       f"need_initial_snapshot)")
        output_str += "\n\n\n"
        return output_str

    def _handle_projection_ws_query_str(self, message: protogen.Message, query_name: str, query_params_str: str,
                                        query_params_with_type_str: str, query_args_dict_str: str,
                                        projection_model_name: str | None = None,
                                        model_type: ModelType | None = None) -> str:
        output_str = f"@perf_benchmark\n"
        output_str += (f"async def underlying_{query_name}_query_ws(websocket: WebSocket, "
                       f"{query_params_with_type_str}, need_initial_snapshot: bool | None = True):\n")
        if projection_model_name:
            if model_type  != ModelType.Msgspec:
                output_str += (f"    filter_callable, projection_agg_pipeline_callable = "
                               f"await callback_class.{query_name}_query_ws_pre()\n")
                output_str += f"    agg_params = {query_args_dict_str}\n"
                output_str += (f"    await generic_projection_query_ws(websocket, "
                               f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                               f"{message.proto.name}, filter_callable, agg_params")
                output_str += (f", projection_agg_pipeline_callable=projection_agg_pipeline_callable, "
                               f"projection_model={projection_model_name}, need_initial_snapshot=need_initial_snapshot)\n")
            else:
                output_str += (f"    filter_callable, projection_agg_pipeline_callable = "
                               f"await callback_class.{query_name}_query_ws_pre()\n")
                output_str += f"    agg_params = {query_args_dict_str}\n"
                output_str += (f"    await generic_projection_query_ws(websocket, "
                               f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                               f"{message.proto.name}, filter_callable, agg_params")
                output_str += (f", projection_agg_pipeline_callable=projection_agg_pipeline_callable, "
                               f"need_initial_snapshot=need_initial_snapshot)\n")
        else:
            output_str += f"    filter_callable = await callback_class.{query_name}_query_ws_pre()\n"
            output_str += f'    params_json = {query_args_dict_str}\n'
            output_str += (f"    await generic_projection_query_ws(websocket, "
                           f"{FastapiWsRoutesFileHandler.proto_package_var_name}, "
                           f"{message.proto.name}, filter_callable, params_json")
            output_str += ", need_initial_snapshot=need_initial_snapshot)\n"
        output_str += f"    await callback_class.{query_name}_query_ws_post()\n"
        output_str += f"\n\n"
        output_str += f'@{self.api_router_app_name}.websocket("/ws-query-{query_name}")\n'
        output_str += (f"async def {query_name}_query_ws(websocket: WebSocket, {query_params_with_type_str}, "
                       f"need_initial_snapshot: bool | None = True):\n")
        output_str += f'    """\n'
        output_str += f'    WS Query of {message.proto.name} with aggregate - {query_name}\n'
        output_str += f'    """\n'
        output_str += (f"    await underlying_{query_name}_query_ws(websocket, {query_params_str}, "
                       f"need_initial_snapshot)")
        output_str += "\n\n\n"
        return output_str

    def _handle_ws_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiWsRoutesFileHandler.query_name_key]
            query_params = aggregate_value[FastapiWsRoutesFileHandler.query_params_key]
            query_type_value = aggregate_value[FastapiWsRoutesFileHandler.query_type_key]
            query_type = str(query_type_value).lower() if query_type_value is not None else None
            query_route_value = aggregate_value[FastapiWsRoutesFileHandler.query_route_type_key]
            query_route_type = query_route_value if query_route_value is not None else None

            query_params_str = ""
            query_params_with_type_str = ""
            query_args_dict_str = ""
            if query_params:
                param_to_type_str_list = []
                list_type_params = []
                query_params_name_list = []
                for param, param_type in query_params:
                    query_params_name_list.append(param)
                    if "List" not in param_type:
                        param_to_type_str_list.append(f"{param}: {param_type}")
                    else:
                        list_type_params.append((param, param_type))
                for param, param_type in list_type_params:
                    param_to_type_str_list.append(f"{param}: {param_type} = Query()")
                query_params_with_type_str = ", ".join(param_to_type_str_list)
                query_params_str = ", ".join(query_params_name_list)
                query_args_str = ', '.join([f'"{param}": {param}' for param in query_params_name_list])
                query_args_dict_str = "{" + f"{query_args_str}" + "}"
            if query_type == "ws" or query_type == "both":
                output_str += self._handle_ws_query_str(message, query_name, query_params_str,
                                                        query_params_with_type_str, query_args_dict_str)

        return output_str

    def _handle_get_max_id_query_generation(self, message: protogen.Message):
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = f'@{self.api_router_app_name}.get("/query-get_{message_name_snake_cased}_max_id' + \
                     f'", response_model=MaxId, status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_max_id_http() -> MaxId:\n"
        output_str += f'    """\n'
        output_str += f'    Get Query of {message.proto.name} to get max int id\n'
        output_str += f'    """\n'
        output_str += f'    max_val = await {message.proto.name}.find_all().max("_id")\n'
        output_str += f'    max_val = int(max_val) if max_val is not None else 0\n'
        output_str += f"    return MaxId(max_id_val=max_val)\n"
        output_str += "\n\n"
        return output_str

    def _handle_projection_ws_query_methods(self, message, model_type: ModelType):
        output_str = ""
        for field in message.fields:
            if FastapiWsRoutesFileHandler.is_option_enabled(field, FastapiWsRoutesFileHandler.flux_fld_projections):
                break
        else:
            # If no field is found having projection enabled
            return output_str

        meta_data_field_name_to_field_tuple_dict: Dict[str, Tuple[str, protogen.Field] |
                                                            Dict[str, Tuple[str, protogen.Field]]] = (
            self.get_meta_data_field_name_to_type_str_dict(message))
        projection_val_to_fields_dict = FastapiWsRoutesFileHandler.get_projection_option_value_to_fields(message)
        projection_val_to_query_name_dict = (
            FastapiWsRoutesFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
        for projection_option_val, query_name in projection_val_to_query_name_dict.items():
            field_name_list: List[str] = []
            field_names = projection_val_to_fields_dict[projection_option_val]
            for field_name in field_names:
                if "." in field_name:
                    field_name_list.append("_".join(field_name.split(".")))
                else:
                    field_name_list.append(field_name)
            field_names_str = "_n_".join(field_name_list)
            field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)
            container_model_name = f"{message.proto.name}ProjectionContainerFor{field_names_str_camel_cased}"

            query_param_str = ""
            query_param_with_type_str = ""
            for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                if isinstance(meta_field_info, dict):
                    for nested_meta_field_name, nested_meta_field_info in meta_field_info.items():
                        nested_meta_field_type, _ = nested_meta_field_info
                        query_param_str += f"{nested_meta_field_name}, "
                        query_param_with_type_str += (f"{nested_meta_field_name}: "
                                                      f"{nested_meta_field_type}, ")
                else:
                    meta_field_type, _ = meta_field_info
                    query_param_str += f"{meta_field_name}, "
                    query_param_with_type_str += f"{meta_field_name}: {meta_field_type}, "
            query_param_str += "start_date_time, end_date_time"
            if model_type == ModelType.Msgspec:
                query_param_with_type_str += ("start_date_time: Any | None = None, "
                                              "end_date_time: Any | None = None")
            else:
                query_param_with_type_str += ("start_date_time: DateTime | None = None, "
                                              "end_date_time: DateTime | None = None")

            query_param_dict_str = "{"
            for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                if isinstance(meta_field_info, dict):
                    for nested_meta_field_name, _ in meta_field_info.items():
                        query_param_dict_str += (f'"{nested_meta_field_name}": '
                                                 f'{nested_meta_field_name}, ')
                else:
                    query_param_dict_str += f'"{meta_field_name}": {meta_field_name}, '
            query_param_dict_str += '"start_date_time": start_date_time, "end_date_time": end_date_time}'

            # WS method
            output_str += self._handle_projection_ws_query_str(message, query_name, query_param_str,
                                                               query_param_with_type_str, query_param_dict_str,
                                                               container_model_name, model_type)
        return output_str

    def handle_ws_CRUD_task(self, model_type: ModelType) -> str:
        output_str = ""
        for message in self.root_message_list:
            if FastapiWsRoutesFileHandler.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_json_root):
                output_str += self._handle_ws_routes_methods(message)
            elif self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_ws_routes_methods(message)

        for message in self.root_message_list + self.non_root_message_list:
            if FastapiWsRoutesFileHandler.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_json_query):
                output_str += self._handle_ws_query_methods(message)

        for message in self.root_message_list:
            if FastapiWsRoutesFileHandler.is_option_enabled(message,
                                                            FastapiWsRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_projection_ws_query_methods(message, model_type)

        return output_str

    def _get_aggregate_query_var_list(self) -> List[str]:
        agg_query_var_list = []
        for message in self.root_message_list:
            if self.is_option_enabled(message, FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name):
                agg_query_var_list.append(
                    self.get_simple_option_value_from_proto(
                        message,
                        FastapiWsRoutesFileHandler.flux_msg_aggregate_query_var_name)[1:-1])
        # else not required: if no message is found with agg_query option then returning empty list
        return agg_query_var_list

    def handle_ws_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_model_class_dict()

        base_routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.base_routes_file_name)
        output_str = f"from {base_routes_file_path} import *\n\n"
        output_str += self.handle_ws_CRUD_task(ModelType.Beanie)
        return output_str

    def handle_ws_msgspec_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_model_class_dict()

        base_routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.base_routes_file_name)
        output_str = f"from {base_routes_file_path} import *\n\n"
        output_str += self.handle_ws_CRUD_task(ModelType.Msgspec)
        return output_str
