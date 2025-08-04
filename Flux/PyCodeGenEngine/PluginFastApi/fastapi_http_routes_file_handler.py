import os
import time
from abc import ABC
from typing import List, Dict, Tuple, Set
import logging

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.general_utility_functions import parse_string_to_original_types, convert_to_capitalized_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_base_routes_file_handler import FastapiBaseRoutesFileHandler, ModelType


class FastapiHttpRoutesFileHandler(FastapiBaseRoutesFileHandler, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.shared_lock_name_to_model_class_dict: Dict[str, List[protogen.Message]] = {}
        self.shared_lock_name_message_list: List[protogen.Message] = []
        self.message_to_link_messages_dict: Dict[protogen.Message, List[protogen.Message]] = {}
        self._msg_already_generated_str_formatted_int_fields_handler_list: List[protogen.Message] = []
        self._msg_already_generated_id_n_date_time_fields_handler_list: List[protogen.Message] = []

    def _get_list_of_shared_lock_for_message(self, message: protogen.Message) -> List[str]:
        shared_lock_name_list = []
        for shared_lock_name, message_list in self.shared_lock_name_to_model_class_dict.items():
            if message in message_list:
                shared_lock_name_list.append(shared_lock_name)
        return shared_lock_name_list

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

    def get_avoid_db_n_ws_update_var_name(self, message_name_snake_cased: str):
        return f"avoid_{message_name_snake_cased}_db_n_ws_update"

    def _handle_msgspec_common_underlying_post_gen(self, message: protogen.Message, aggregation_type, msg_has_links,
                                                   shared_lock_list) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_create_{message_name_snake_cased}_http("
                      f"{message_name_snake_cased}_msgspec_obj: msgspec.Struct, "
                      f"filter_agg_pipeline: Any = None, generic_callable: "
                      f"Callable[Any, Any] | None = None, return_obj_copy: bool | None = True"
                      f"):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += (" " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_pre("
                       f"{message_name_snake_cased}_msgspec_obj)\n")
        output_str += (" " * indent_count + f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}"
                                            f" = config_yaml_dict.get("
                       f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
        output_str += (" " * indent_count +
                       f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n")
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_json_obj = await generic_callable(" \
                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name_snake_cased}_msgspec_obj, filter_agg_pipeline)\n"
        output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj = "
                                            f"{message.proto.name}.from_dict({message_name_snake_cased}_json_obj)\n")
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message, message_name_snake_cased)
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj, {filter_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} is passed - "
                                                    f"returned dict will be aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj = "
                                                    f"{message.proto.name}.from_dict("
                                                    f"{message_name_snake_cased}_json_obj)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_obj = await "
                               f"generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {update_agg_pipeline_var_name} is passed - "
                                                    f"returned dict will be update "
                                                    f"aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj = "
                                                    f"{message.proto.name}.from_dict("
                                                    f"{message_name_snake_cased}_json_obj)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message, message_name_snake_cased)
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_obj = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj, {filter_agg_pipeline_var_name}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} and "
                                                    f"{update_agg_pipeline_var_name} are passed - "
                                                    f"returned dict will be aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj = "
                                                    f"{message.proto.name}.from_dict("
                                                    f"{message_name_snake_cased}_json_obj)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_obj = await "
                               f"generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj, has_links={msg_has_links})\n")
        output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_msgspec_obj)\n"
        output_str += " " * indent_count + f"else:\n"
        output_str += " " * indent_count + (f"    await callback_class.create_{message_name_snake_cased}_post("
                                            f"{message_name_snake_cased}_msgspec_obj)\n")
        indent_count -= 4
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return {message_name_snake_cased}_msgspec_obj\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n\n\n"
        return output_str

    def handle_underlying_POST_one_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)

        if model_type == ModelType.Msgspec:
            output_str = self._handle_msgspec_common_underlying_post_gen(message, aggregation_type, msg_has_links,
                                                                         shared_lock_list)
            # default version - takes json_str and returns json_dict
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_create_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj: msgspec.Struct, "
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                           f"):\n")
            output_str += f'    """\n'
            output_str += (f'    Create route for {message.proto.name} which takes msgspec_obj param and returns '
                           f' msgspec_obj\n')
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_http\n'
            output_str += (f"    return_obj = await _underlying_create_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj, filter_agg_pipeline, generic_callable, "
                           f"return_obj_copy)\n")
            output_str += f"    return return_obj\n\n\n"

            # version that takes json_dict and returns json_dict
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_create_{message_name_snake_cased}_http_json_dict("
                           f"{message_name_snake_cased}_json_dict: Dict[str, Any], "
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                           f"):\n")
            output_str += f'    """\n'
            output_str += (f'    Create route for {message.proto.name} which takes json_dict param and returns '
                           f' json_dict\n')
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_http\n'
            output_str += (f"    {message_name_snake_cased}_msgspec_obj = {message.proto.name}.from_dict("
                           f"{message_name_snake_cased}_json_dict)\n")
            output_str += (f"    return_obj = await _underlying_create_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj, filter_agg_pipeline, generic_callable, "
                           f"return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_dict = msgspec.to_builtins(return_obj, builtin_types=[DateTime])\n"
            output_str += f"        return return_obj_dict\n"
            output_str += f"    else:\n"
            output_str += f"        return return_obj\n\n\n"

            # default version - takes json_bytes and returns json_dict
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_create_{message_name_snake_cased}_http_bytes("
                           f"{message_name_snake_cased}_bytes: "
                           f"bytes, filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                           f"):\n")
            output_str += f'    """\n'
            output_str += (f'    Create route for {message.proto.name} which takes json_str param and returns '
                           f' json_dict\n')
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_http\n'
            output_str += (f"    {message_name_snake_cased}_msgspec_obj = msgspec.json.decode("
                           f"{message_name_snake_cased}_bytes, type={message.proto.name}, "
                           f"dec_hook={message.proto.name}.dec_hook)\n")
            output_str += (f"    return_obj = await _underlying_create_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj, filter_agg_pipeline, generic_callable, "
                           f"return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_bytes = msgspec.json.encode(return_obj, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"        return CustomFastapiResponse(content=return_obj_bytes, status_code=201)\n"
            output_str += f"    else:\n"
            output_str += (f"        return CustomFastapiResponse(content=str(return_obj).encode('utf-8'), "
                           f"status_code=201)\n")
        else:
            if model_type == ModelType.Dataclass:
                output_str = self._handle_missing_id_n_datetime_field_callable_generation(message, model_type)
                output_str += f"@perf_benchmark\n"
                output_str += (f"async def underlying_create_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_json_dict: "
                               f"Dict, filter_agg_pipeline: Any = None, generic_callable: "
                               f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                               f"):\n")
            else:
                output_str = f"@perf_benchmark\n"
                output_str += (
                    f"async def underlying_create_{message_name_snake_cased}_http({message_name_snake_cased}: "
                    f"{message.proto.name}, filter_agg_pipeline: Any = None, generic_callable: "
                    f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                    f") -> {message.proto.name} | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Create route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_http\n'

            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + (
                    f"    handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_"
                    f"json({message.proto.name}, {message_name_snake_cased}_json_dict, "
                    f"is_patch_call=False)\n")
                output_str += (" " * indent_count + f"    {message_name_snake_cased}_json_n_dataclass_handler.clear()    "
                                                    f"# Ideally ths should not be required since we clean handler "
                                                    f"after post call - keeping it to avoid any bug\n")
                output_str += (" " * indent_count +
                               f"    {message_name_snake_cased}_json_n_dataclass_handler.set_json_dict("
                               f"{message_name_snake_cased}_json_dict)\n")
                output_str += " " * indent_count + \
                              (f"    await callback_class.create_{message_name_snake_cased}_pre("
                               f"{message_name_snake_cased}_json_n_dataclass_handler)\n")
            else:
                output_str += " " * indent_count + \
                              f"    await callback_class.create_{message_name_snake_cased}_pre({message_name_snake_cased})\n"
            output_str += " " * indent_count + (
                f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = config_yaml_dict.get("
                f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
            output_str += " " * indent_count + f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
            indent_count += 4
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_json_obj = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_json_n_dataclass_handler, filter_agg_pipeline, " \
                              f"return_obj_copy=return_obj_copy)\n"
            else:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"{self._get_filter_configs_var_name(message, message_name_snake_cased)}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, {message_name_snake_cased}, "
                                       f"{self._get_filter_configs_var_name(message, message_name_snake_cased)}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_obj = await "
                                       f"generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, {message_name_snake_cased}, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_both:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_obj = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"{self._get_filter_configs_var_name(message, message_name_snake_cased)}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, {message_name_snake_cased}, "
                                       f"{self._get_filter_configs_var_name(message, message_name_snake_cased)}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_obj = await "
                                       f"generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_obj\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_obj\n"
            output_str += " " * indent_count + f"else:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_n_dataclass_handler.get_json_dict()\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased})\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"# Cleaning handler before returning and leaving r_lock\n"
                output_str += " " * indent_count + f"{message_name_snake_cased}_json_n_dataclass_handler.clear()\n"
            output_str += " " * indent_count + f"return return_obj\n"
        output_str += "\n"
        return output_str

    def _add_view_check_code_in_route(self):
        output_str = f"    if is_view_server:\n"
        output_str += (f'        raise HTTPException(detail="Operation doesn\'t supported in view server", '
                       f"status_code=400)\n")
        return output_str

    def handle_POST_gen(self, **kwargs) -> str:
        message, _, _, model_type = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_POST_one_gen(**kwargs)
        output_str += "\n"
        if model_type == ModelType.Dataclass:
            output_str += f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + \
                          f'", status_code=201)\n'
            output_str += (f"async def create_{message_name_snake_cased}_http({message_name_snake_cased}_json_req: "
                           f"Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_json_req.body()\n"
            output_str += f"        json_body = orjson.loads(data_body)\n"
            output_str += (f"        return await underlying_create_{message_name_snake_cased}_http("
                           f"json_body, return_obj_copy=return_obj_copy)\n")
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'create_{message_name_snake_cased}_http failed in client call "
                           "with exception: {e}')\n")
            output_str += f"        raise e\n"
        elif model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + \
                          f'", status_code=201)\n'
            output_str += (f"async def create_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_json_req: Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_json_req.body()\n"
            output_str += (f"        return await underlying_create_{message_name_snake_cased}_http_bytes("
                           f"data_body, return_obj_copy=return_obj_copy)\n")
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'create_{message_name_snake_cased}_http failed in client call "
                           "with exception: {e}')\n")
            output_str += f"        raise e\n"
        else:
            output_str += f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + \
                          f'", response_model={message.proto.name} | bool, status_code=201)\n'
            output_str += (f"async def create_{message_name_snake_cased}_http({message_name_snake_cased}: "
                           f"{message.proto.name}, return_obj_copy: bool | None = True) -> "
                           f"{message.proto.name} | bool:\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += (f"        return await underlying_create_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}, return_obj_copy=return_obj_copy)\n")
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'create_{message_name_snake_cased}_http failed in client call "
                           "with exception: {e}')\n")
            output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_post_all_gen(self, message: protogen.Message, aggregation_type, msg_has_links,
                                                       shared_lock_list) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_create_all_{message_name_snake_cased}_http("
                      f"{message_name_snake_cased}_msgspec_obj_list: List[msgspec.Struct], "
                      f"filter_agg_pipeline: Any = None, generic_callable: "
                      f"Callable[Any, Any] | None = None, return_obj_copy: bool | None = True"
                      f"):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + \
                      f"    await callback_class.create_all_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_msgspec_obj_list)\n"
        output_str += " " * indent_count + (f"    if not config_yaml_dict.get("
                                            f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}'):\n")
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      (f"        {message_name_snake_cased}_json_list = "
                       f"await generic_callable({message.proto.name}, "
                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name},"
                       f"{message_name_snake_cased}_msgspec_obj_list, filter_agg_pipeline)\n")
        output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj_list = "
                                            f"{message.proto.name}.from_dict_list("
                                            f"{message_name_snake_cased}_json_list)\n")
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_list')
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj_list, {filter_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} is passed - "
                                                    f"returned value will be aggregated output "
                                                    f"so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"{message_name_snake_cased}_json_list)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj_list, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {update_agg_pipeline_var_name} is passed - "
                                                    f"returned val will be update "
                                                    f"aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"{message_name_snake_cased}_json_list)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message,
                                                                                 f'{message_name_snake_cased}_list')
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj_list, {filter_agg_pipeline_var_name}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} and "
                                                    f"{update_agg_pipeline_var_name} are passed - "
                                                    f"returned dict will be aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"{message_name_snake_cased}_json_list)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_msgspec_obj_list, "
                               f"has_links={msg_has_links})\n")
                output_str += (" " * indent_count +
                               f"        # avoiding returned json dict to obj convertion since no filter or update "
                               f"aggregation was passed and hence whatever param passed was stored - will be using "
                               f"same value which was passed as param\n")
        output_str += " " * indent_count + (f"    await callback_class.create_all_{message_name_snake_cased}_post("
                                            f"{message_name_snake_cased}_msgspec_obj_list)\n")
        output_str += " " * indent_count + f"else:\n"
        output_str += " " * indent_count + (f"    await callback_class.create_all_{message_name_snake_cased}_post("
                                            f"{message_name_snake_cased}_msgspec_obj_list)\n")
        indent_count -= 4
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return {message_name_snake_cased}_msgspec_obj_list\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n\n\n"
        return output_str

    def handle_underlying_POST_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Msgspec:
            output_str = self._handle_msgspec_common_underlying_post_all_gen(message, aggregation_type,
                                                                             msg_has_links, shared_lock_list)
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_create_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj_list: List[msgspec.Struct], "
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Create All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_all_http\n'
            output_str += (f"    return_val = await _underlying_create_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj_list, "
                           f"filter_agg_pipeline, generic_callable, return_obj_copy)\n")
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_create_all_{message_name_snake_cased}_http_json_dict("
                           f"{message_name_snake_cased}_json_dict_list: List[Dict[str, Any]], "
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Create All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_all_http\n'
            output_str += (f"    {message_name_snake_cased}_msgspec_obj_list = {message.proto.name}."
                           f"from_dict_list({message_name_snake_cased}_json_dict_list)\n")
            output_str += (f"    return_val = await _underlying_create_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj_list, "
                           f"filter_agg_pipeline, generic_callable, return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_dict = msgspec.to_builtins(return_val, builtin_types=[DateTime])\n"
            output_str += f"        return return_obj_dict\n"
            output_str += f"    else:\n"
            output_str += f"        return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_create_all_{message_name_snake_cased}_http_bytes("
                           f"{message_name_snake_cased}_bytes: "
                           f"bytes, filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Create All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_all_http\n'
            output_str += (f"    {message_name_snake_cased}_msgspec_obj_list = msgspec.json.decode("
                           f"{message_name_snake_cased}_bytes, type=List[{message.proto.name}], "
                           f"dec_hook={message.proto.name}.dec_hook)\n")
            output_str += (f"    return_val = await _underlying_create_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_msgspec_obj_list, "
                           f"filter_agg_pipeline, generic_callable, return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"        return CustomFastapiResponse(content=return_obj_bytes, status_code=201)\n"
            output_str += f"    else:\n"
            output_str += (f"        return CustomFastapiResponse(content=str(return_val).encode('utf-8'), "
                           f"status_code=201)\n")
        else:
            if model_type == ModelType.Dataclass:
                output_str = self._handle_missing_id_n_datetime_field_callable_generation(message, model_type)
                output_str += f"@perf_benchmark\n"
                output_str += (f"async def underlying_create_all_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_json_dict_list: "
                               f"List[Dict], filter_agg_pipeline: Any = None, generic_callable: "
                               f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            else:
                output_str = f"@perf_benchmark\n"
                output_str += (
                    f"async def underlying_create_all_{message_name_snake_cased}_http({message_name_snake_cased}_list: "
                    f"List[{message.proto.name}], filter_agg_pipeline: Any = None, generic_callable: "
                    f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True) -> "
                    f"List[{message.proto.name}] | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Create All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_post_all_http\n'
            # else not required: avoiding if method desc not provided
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    for {message_name_snake_cased}_json_dict in " \
                                                   f"{message_name_snake_cased}_json_dict_list:\n"
                output_str += " " * indent_count + (
                    f"        handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_"
                    f"json({message.proto.name}, {message_name_snake_cased}_json_dict, "
                    f"is_patch_call=False)\n")
                output_str += (" " * indent_count + f"    {message_name_snake_cased}_json_n_dataclass_handler.clear()    "
                                                    f"# Ideally ths should not be required since we clean handler "
                                                    f"after post call - keeping it to avoid any bug\n")
                output_str += (" " * indent_count +
                               f"    {message_name_snake_cased}_json_n_dataclass_handler.set_json_dict_list("
                               f"{message_name_snake_cased}_json_dict_list)\n")
                output_str += " " * indent_count + \
                              f"    await callback_class.create_all_{message_name_snake_cased}_pre(" \
                              f"{message_name_snake_cased}_json_n_dataclass_handler)\n"
            else:
                output_str += " " * indent_count + \
                              f"    await callback_class.create_all_{message_name_snake_cased}_pre(" \
                              f"{message_name_snake_cased}_list)\n"
            output_str += " " * indent_count + (f"    if not config_yaml_dict.get("
                                                f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}'):\n")
            indent_count += 4
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_json_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name},"
                               f"{message_name_snake_cased}_json_n_dataclass_handler, "
                               f"filter_agg_pipeline, return_obj_copy=return_obj_copy)\n")
            else:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj_list = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}," \
                              f"{message_name_snake_cased}_list, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_list')}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_list, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_list')}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_list, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_both:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_list')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_list, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_list')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_json_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        {message_name_snake_cased}_obj_list = "
                                       f"await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_list, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.create_all_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_list\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.create_all_{message_name_snake_cased}_post({message_name_snake_cased}_obj_list)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_obj_list\n"
            output_str += " " * indent_count + f"else:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.create_all_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_n_dataclass_handler.get_json_dict_list()\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.create_all_{message_name_snake_cased}_post({message_name_snake_cased}_list)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_list\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"# Cleaning handler before returning and leaving r_lock\n"
                output_str += " " * indent_count + f"{message_name_snake_cased}_json_n_dataclass_handler.clear()\n"
            output_str += " " * indent_count + f"return return_obj\n"
        output_str += "\n"
        return output_str

    def handle_POST_all_gen(self, **kwargs) -> str:
        message, _, _, model_type = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_POST_all_gen(**kwargs)
        output_str += "\n"
        if model_type == ModelType.Dataclass:
            output_str += f'@{self.api_router_app_name}.post("/create-all-{message_name_snake_cased}' + \
                          f'", status_code=201)\n'
            output_str += (f"async def create_all_{message_name_snake_cased}_http({message_name_snake_cased}_req: "
                           f"Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_req.body()\n"
            output_str += f"        json_body = orjson.loads(data_body)\n"
            output_str += f"        return await underlying_create_all_{message_name_snake_cased}_http(" \
                          f"json_body, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'create_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        elif model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.post("/create-all-{message_name_snake_cased}' + \
                          f'", status_code=201)\n'
            output_str += (f"async def create_all_{message_name_snake_cased}_http({message_name_snake_cased}_req: "
                           f"Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_req.body()\n"
            output_str += f"        return await underlying_create_all_{message_name_snake_cased}_http_bytes(" \
                          f"data_body, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'create_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        else:
            output_str += f'@{self.api_router_app_name}.post("/create-all-{message_name_snake_cased}' + \
                          f'", response_model=List[{message.proto.name}] | bool, status_code=201)\n'
            output_str += (f"async def create_all_{message_name_snake_cased}_http({message_name_snake_cased}_list: "
                           f"List[{message.proto.name}], return_obj_copy: bool | None = True) -> "
                           f"List[{message.proto.name}] | bool:\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        return await underlying_create_all_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_list, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'create_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_put_gen(self, message: protogen.Message, aggregation_type, msg_has_links,
                                                  shared_lock_list, pass_stored_obj_to_pre_post_callback: bool) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (
            f"async def _underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
            f"update_msgspec_obj: msgspec.Struct, filter_agg_pipeline: Any = None, generic_callable: "
            f"Callable[Any, Any] | None = None, return_obj_copy: bool | None = True"
            f"):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str

        if pass_stored_obj_to_pre_post_callback:
            output_str += " " * indent_count + (f"    # Below stored obj code is added based on field "
                                                f"'PassStoredObjToUpdatePrePostCallback' set on plugin option\n\t\t"
                                                f"# 'MessageJsonRoot' on this model in proto file, this includes "
                                                f"extra dependency of fetching stored obj and\n\t\t#passing it to pre "
                                                f"and post callback calls, if not required in this model then update "
                                                f"proto file and regenerate\n")
            output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_json_dict = "
                                                f"await generic_read_by_id_http({message.proto.name}, "
                                                f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                                f"{message_name_snake_cased}_update_msgspec_obj.id, "
                                                f"has_links={msg_has_links})\n")
            output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_msgspec_obj = "
                                                f"{message.proto.name}.from_dict("
                                                f"stored_{message_name_snake_cased}_json_dict)\n")
            output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_msgspec_obj = "
                                                f"await callback_class.update_{message_name_snake_cased}_pre("
                                                f"stored_{message_name_snake_cased}_msgspec_obj, "
                                                f"{message_name_snake_cased}_update_msgspec_obj)\n")
        else:
            output_str += " " * indent_count + (f"    # Since field 'PassStoredObjToUpdatePrePostCallback' of plugin "
                                                f"option 'MessageJsonRoot' on this model\n\t\t# is not set in proto "
                                                f"file, stored obj will not be passed to pre and post callback calls - "
                                                f"if required then\n\t\t# 'PassStoredObjToUpdatePrePostCallback' field "
                                                f"must be set to True in option 'MessageJsonRoot',\n\t\t# but this "
                                                f"will add extra load since it requires fetching stored obj from db so "
                                                f"must\n\t\t# be noted before updating and regenerating\n")
            output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_msgspec_obj = "
                                                f"await callback_class.update_{message_name_snake_cased}_pre("
                                                f"{message_name_snake_cased}_update_msgspec_obj)\n")
        output_str += " " * indent_count + (
            f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = config_yaml_dict.get("
            f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
        output_str += " " * indent_count + f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_json_obj = " \
                      f"await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name_snake_cased}_update_msgspec_obj, " \
                      f"filter_agg_pipeline)\n"
        output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj = "
                                            f"{message.proto.name}.from_dict("
                                            f"updated_{message_name_snake_cased}_json_obj)\n")
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message,
                                                                                 f'{message_name_snake_cased}_updated')
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_json_obj = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_update_msgspec_obj, {filter_agg_pipeline_var_name}, " \
                              f"has_links={msg_has_links})\n"
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} is passed - "
                                                    f"returned dict will be aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj = "
                                                    f"{message.proto.name}.from_dict("
                                                    f"updated_{message_name_snake_cased}_json_obj)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_update_msgspec_obj, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {update_agg_pipeline_var_name} is passed - "
                                                    f"returned dict will be update "
                                                    f"aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj = "
                                                    f"{message.proto.name}.from_dict("
                                                    f"updated_{message_name_snake_cased}_json_obj)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message,
                                                                                 f'{message_name_snake_cased}_updated')
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_update_msgspec_obj, {filter_agg_pipeline_var_name}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} and "
                                                    f"{update_agg_pipeline_var_name} are passed - "
                                                    f"returned dict will be aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj = "
                                                    f"{message.proto.name}.from_dict("
                                                    f"updated_{message_name_snake_cased}_json_obj)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_update_msgspec_obj, has_links={msg_has_links})\n")
        if pass_stored_obj_to_pre_post_callback:
            output_str += " " * indent_count + (f"    await callback_class.update_{message_name_snake_cased}_post("
                                                f"stored_{message_name_snake_cased}_msgspec_obj, "
                                                f"{message_name_snake_cased}_update_msgspec_obj)\n")
            output_str += " " * indent_count + f"else:\n"
            output_str += " " * indent_count + (f"    await callback_class.update_{message_name_snake_cased}_post("
                                                f"stored_{message_name_snake_cased}_msgspec_obj, "
                                                f"{message_name_snake_cased}_update_msgspec_obj)\n")
        else:
            output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post({message_name_snake_cased}_update_msgspec_obj)\n"
            output_str += " " * indent_count + f"else:\n"
            output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post({message_name_snake_cased}_update_msgspec_obj)\n"
        indent_count -= 4
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return {message_name_snake_cased}_update_msgspec_obj\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n\n\n"
        return output_str

    def handle_underlying_PUT_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)

        if model_type == ModelType.Msgspec:
            pass_stored_obj_to_pre_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiHttpRoutesFileHandler.flux_json_root_pass_stored_obj_to_update_pre_post_callback, **kwargs)
            output_str = self._handle_msgspec_common_underlying_put_gen(message, aggregation_type,
                                                                        msg_has_links, shared_lock_list,
                                                                        pass_stored_obj_to_pre_post_callback)
            output_str += f"@perf_benchmark\n"
            output_str += (
                f"async def underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
                f"update_msgspec_obj: msgspec.Struct, filter_agg_pipeline: Any = None, generic_callable: "
                f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                f"):\n")
            output_str += f'    """\n'
            output_str += f'    Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_http\n'
            output_str += (
                f"    return_val = await _underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
                f"update_msgspec_obj, filter_agg_pipeline, generic_callable, return_obj_copy)\n")
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (
                f"async def underlying_update_{message_name_snake_cased}_http_json_dict({message_name_snake_cased}_"
                f"update_json_dict: Dict[str, Any], filter_agg_pipeline: Any = None, generic_callable: "
                f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                f"):\n")
            output_str += f'    """\n'
            output_str += f'    Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_http\n'
            output_str += (f"    {message_name_snake_cased}_update_msgspec_obj = {message.proto.name}.from_dict("
                           f"{message_name_snake_cased}_update_json_dict)\n")
            output_str += (
                f"    return_val = await _underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
                f"update_msgspec_obj, filter_agg_pipeline, generic_callable, return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_dict = msgspec.to_builtins(return_val, builtin_types=[DateTime])\n"
            output_str += f"        return return_obj_dict\n"
            output_str += f"    else:\n"
            output_str += f"        return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (
                f"async def underlying_update_{message_name_snake_cased}_http_bytes({message_name_snake_cased}_"
                f"update_bytes: bytes, filter_agg_pipeline: Any = None, generic_callable: "
                f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                f"):\n")
            output_str += f'    """\n'
            output_str += f'    Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_http\n'
            output_str += (f"    {message_name_snake_cased}_update_msgspec_obj = msgspec.json.decode("
                           f"{message_name_snake_cased}_update_bytes, type={message.proto.name}, "
                           f"dec_hook={message.proto.name}.dec_hook)\n")
            output_str += (
                f"    return_val = await _underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
                f"update_msgspec_obj, filter_agg_pipeline, generic_callable, return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"        return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"
            output_str += f"    else:\n"
            output_str += (f"        return CustomFastapiResponse(content=str(return_val).encode('utf-8'), "
                           f"status_code=200)\n\n")
        else:
            output_str = f"@perf_benchmark\n"
            if model_type == ModelType.Dataclass:
                output_str += (f"async def underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
                               f"update_json: Dict, filter_agg_pipeline: Any = None, generic_callable: "
                               f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                               f"):\n")
            else:
                output_str += (f"async def underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_"
                               f"updated: {message.proto.name}, filter_agg_pipeline: Any = None, generic_callable: "
                               f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                               f") -> {message.proto.name} | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_http\n'
            # else not required: avoiding if method desc not provided
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            if model_type == ModelType.Dataclass:
                output_str += (" " * indent_count + f"    {message_name_snake_cased}_json_n_dataclass_handler.clear()    "
                                                    f"# Ideally ths should not be required since we clean handler "
                                                    f"after post call - keeping it to avoid any bug\n")
                output_str += (" " * indent_count +
                               f"    {message_name_snake_cased}_json_n_dataclass_handler.set_json_dict("
                               f"{message_name_snake_cased}_update_json)\n")
                output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_pre(" \
                                                   f"{message_name_snake_cased}_json_n_dataclass_handler)\n"
            else:
                output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                                                   f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                                   f"{message_name_snake_cased}_updated.id, has_links={msg_has_links})\n"
                output_str += " " * indent_count + f"    {message_name_snake_cased}_updated = " \
                                                   f"await callback_class.update_{message_name_snake_cased}_pre(" \
                                                   f"stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
                output_str += " " * indent_count + f"    if {message_name_snake_cased}_updated is None:\n"
                output_str += " " * indent_count + (f"        raise HTTPException(status_code=503, detail="
                                                    f"'callback_class.partial_update_{message_name_snake_cased}_pre returned "
                                                    f"None instead of updated {message_name_snake_cased}_updated  ')\n")
            output_str += " " * indent_count + (
                f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = config_yaml_dict.get("
                f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
            output_str += " " * indent_count + (
                          f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n")
            indent_count += 4
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_json_obj = " \
                              f"await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_json_n_dataclass_handler, " \
                              f"filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
            else:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = " \
                              f"await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj), {message_name_snake_cased}_updated, " \
                              f"filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_json_obj = await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message_name_snake_cased}_json_n_dataclass_handler, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_obj = await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                                      f"{message_name_snake_cased}_updated, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                                       f"{message_name_snake_cased}_updated, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_both:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                                       f"{message_name_snake_cased}_updated, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                                       f"{message_name_snake_cased}_updated, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_json_obj\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_obj\n"
            output_str += " " * indent_count + f"else:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_n_dataclass_handler.get_json_dict()\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_updated\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"# Cleaning handler before returning and leaving r_lock\n"
                output_str += " " * indent_count + f"{message_name_snake_cased}_json_n_dataclass_handler.clear()\n"
            output_str += " " * indent_count + f"return return_obj\n\n"
        return output_str

    def handle_PUT_gen(self, **kwargs) -> str:
        message, _, _, model_type = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PUT_gen(**kwargs)
        output_str += "\n"
        if model_type == ModelType.Dataclass:
            output_str += f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                          f'", status_code=200)\n'
            output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_update_req: " \
                          f"Request, return_obj_copy: bool | None = True):\n"
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req.body()\n"
            output_str += f"        json_body = orjson.loads(data_body)\n"
            output_str += f"        return await underlying_update_{message_name_snake_cased}_http(" \
                          f"json_body, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'update_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        elif model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                          f'", status_code=200)\n'
            output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_update_req: " \
                          f"Request, return_obj_copy: bool | None = True):\n"
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req.body()\n"
            output_str += f"        return await underlying_update_{message_name_snake_cased}_http_bytes(" \
                          f"data_body, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'update_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        else:
            output_str += f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                          f'", response_model={message.proto.name} | bool, status_code=200)\n'
            output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                          f"{message.proto.name}, return_obj_copy: bool | None = True) -> {message.proto.name} | bool:\n"
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        return await underlying_update_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_updated, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'update_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_put_all_gen(
            self, message: protogen.Message, aggregation_type, msg_has_links,
            shared_lock_list, pass_stored_obj_to_pre_post_callback: bool) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                      f"update_msgspec_obj_list: List[msgspec.Struct], filter_agg_pipeline: Any = None, "
                      f"generic_callable: Callable[Any, Any] | None = None, return_obj_copy: bool | None = True):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)
        output_str += mutex_handling_str

        if pass_stored_obj_to_pre_post_callback:
            output_str += " " * indent_count + (f"    # Below stored obj code is added based on field "
                                                f"'PassStoredObjToUpdateAllPrePostCallback' set on plugin option\n\t\t"
                                                f"# 'MessageJsonRoot' on this model in proto file, this includes "
                                                f"extra dependency of fetching stored obj and\n\t\t#passing it to pre "
                                                f"and post callback calls, if not required in this model then update "
                                                f"proto file and regenerate\n")
            output_str += " " * indent_count + f"    obj_id_list = [model_obj.id for model_obj in " \
                                               f"{message_name_snake_cased}_update_msgspec_obj_list]\n"
            output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_json_dict_list = await "
                                                f"generic_read_http({message.proto.name}, "
                                                f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                                f"has_links={msg_has_links}, read_ids_list=obj_id_list)\n")
            output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_msgspec_obj_list = "
                                                f"{message.proto.name}.from_dict_list("
                                                f"stored_{message_name_snake_cased}_json_dict_list)\n")
            output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_msgspec_obj_list = "
                                                f"await callback_class.update_all_{message_name_snake_cased}_pre("
                                                f"stored_{message_name_snake_cased}_msgspec_obj_list, "
                                                f"{message_name_snake_cased}_update_msgspec_obj_list)\n")
        else:
            output_str += " " * indent_count + (f"    # Since field 'PassStoredObjToUpdateAllPrePostCallback' of plugin "
                                                f"option 'MessageJsonRoot' on this model\n\t\t# is not set in proto "
                                                f"file, stored obj will not be passed to pre and post callback calls - "
                                                f"if required then\n\t\t# 'PassStoredObjToUpdateAllPrePostCallback' "
                                                f"field must be set to True in option 'MessageJsonRoot',\n\t\t# but "
                                                f"this will add extra load since it requires fetching stored obj from "
                                                f"db so must\n\t\t# be noted before updating and regenerating\n")
            output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_msgspec_obj_list = "
                                                f"await callback_class.update_all_{message_name_snake_cased}_pre("
                                                f"{message_name_snake_cased}_update_msgspec_obj_list)\n")
        output_str += " " * indent_count + (f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = config_yaml_dict.get("
                                            f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
        output_str += " " * indent_count + f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_json_list, missing_ids_list = " \
                      f"await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name_snake_cased}_update_msgspec_obj_list, " \
                      f"filter_agg_pipeline)\n"
        output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj_list = "
                                            f"{message.proto.name}.from_dict_list("
                                            f"updated_{message_name_snake_cased}_json_list)\n")
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message,
                                                                                 f'{message_name_snake_cased}_updated_list')
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_json_list , " \
                              "missing_ids_list= await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_update_msgspec_obj_list, {filter_agg_pipeline_var_name}, " \
                              f"has_links={msg_has_links})\n"
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} is passed - "
                                                    f"returned value will be aggregated output "
                                                    f"so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"updated_{message_name_snake_cased}_json_list)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_list, missing_ids_list "
                               "= await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_update_msgspec_obj_list, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {update_agg_pipeline_var_name} is passed - "
                                                    f"returned val will be update "
                                                    f"aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"updated_{message_name_snake_cased}_json_list)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                filter_agg_pipeline_var_name = self._get_filter_configs_var_name(message,
                                                                                 f'{message_name_snake_cased}_updated_list')
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_list, missing_ids_list "
                               f"= await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_update_msgspec_obj_list, "
                               f"{filter_agg_pipeline_var_name}, {update_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
                output_str += " " * indent_count + (f"        # since {filter_agg_pipeline_var_name} and "
                                                    f"{update_agg_pipeline_var_name} are passed - "
                                                    f"returned dict will be aggregated output so can't use passed obj\n")
                output_str += " " * indent_count + (f"        {message_name_snake_cased}_update_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"updated_{message_name_snake_cased}_json_list)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_list, missing_ids_list "
                               f"= await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_update_msgspec_obj_list, "
                               f"has_links={msg_has_links})\n")
                output_str += (" " * indent_count +
                               f"        # if missing ids list is not empty then it returned list of updated objs will "
                               f"be having only stored objects so can't use same list that was passed to generic "
                               f"calable\n")
                output_str += (" " * indent_count + f"        if missing_ids_list:\n")
                output_str += " " * indent_count + (f"            {message_name_snake_cased}_update_msgspec_obj_list = "
                                                    f"{message.proto.name}.from_dict_list("
                                                    f"updated_{message_name_snake_cased}_json_list)\n")
                output_str += (" " * indent_count +
                               f"        # else not required: using same list of objects that was passed to "
                               f"generic callable since all objects will be updated with same data\n")

        if pass_stored_obj_to_pre_post_callback:
            output_str += " " * indent_count + (f"    await callback_class.update_all_{message_name_snake_cased}_post("
                                                f"stored_{message_name_snake_cased}_msgspec_obj_list, "
                                                f"{message_name_snake_cased}_update_msgspec_obj_list)\n")
            output_str += " " * indent_count + f"else:\n"
            output_str += " " * indent_count + (f"    await callback_class.update_all_{message_name_snake_cased}_post("
                                                f"stored_{message_name_snake_cased}_msgspec_obj_list, "
                                                f"{message_name_snake_cased}_update_msgspec_obj_list)\n")
        else:
            output_str += " " * indent_count + (f"    await callback_class.update_all_{message_name_snake_cased}_post("
                                                f"{message_name_snake_cased}_update_msgspec_obj_list)\n")
            output_str += " " * indent_count + f"    if missing_ids_list:\n"
            output_str += " " * indent_count + (f'        raise HTTPException(status_code=400, '
                                                'detail=f"Can\'t find document objects with ids: {missing_ids_list} '
                                                'to update - updated rest found objects;;; {'
                                                f'{message_name_snake_cased}_update_msgspec_obj_list'+'=}")\n')
            output_str += " " * indent_count + f"else:\n"
            output_str += " " * indent_count + (f"    await callback_class.update_all_{message_name_snake_cased}_post("
                                                f"{message_name_snake_cased}_update_msgspec_obj_list)\n")

        indent_count -= 4
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return {message_name_snake_cased}_update_msgspec_obj_list\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n\n\n"
        return output_str

    def handle_underlying_PUT_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Msgspec:
            pass_stored_obj_to_pre_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiHttpRoutesFileHandler.flux_json_root_pass_stored_obj_to_update_all_pre_post_callback, **kwargs)
            output_str = self._handle_msgspec_common_underlying_put_all_gen(message, aggregation_type,
                                                                            msg_has_links, shared_lock_list,
                                                                            pass_stored_obj_to_pre_post_callback)
            output_str += f"@perf_benchmark\n"
            output_str += (
                f"async def underlying_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                f"update_msgspec_obj_list: List[msgspec.Struct], filter_agg_pipeline: Any = None, generic_callable: "
                f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Update All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_all_http\n'
            output_str += (
                f"    return_val = await _underlying_update_all_{message_name_snake_cased}_http("
                f"{message_name_snake_cased}_update_msgspec_obj_list, filter_agg_pipeline, "
                f"generic_callable, return_obj_copy)\n")
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (
                f"async def underlying_update_all_{message_name_snake_cased}_http_json_dict({message_name_snake_cased}_"
                f"update_json_dict: Dict[str, Any], filter_agg_pipeline: Any = None, generic_callable: "
                f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Update All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_all_http\n'
            output_str += (f"    {message_name_snake_cased}_update_msgspec_obj_list = {message.proto.name}"
                           f".from_dict_list({message_name_snake_cased}_update_json_dict)\n")
            output_str += (
                f"    return_val = await _underlying_update_all_{message_name_snake_cased}_http("
                f"{message_name_snake_cased}_update_msgspec_obj_list, filter_agg_pipeline, generic_callable, "
                f"return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_dict = msgspec.to_builtins(return_val, builtin_types=[DateTime])\n"
            output_str += f"        return return_obj_dict\n"
            output_str += f"    else:\n"
            output_str += f"        return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (
                f"async def underlying_update_all_{message_name_snake_cased}_http_bytes({message_name_snake_cased}_"
                f"update_bytes: bytes, filter_agg_pipeline: Any = None, generic_callable: "
                f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Update All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_all_http\n'
            output_str += (f"    {message_name_snake_cased}_update_msgspec_obj_list = msgspec.json.decode("
                           f"{message_name_snake_cased}_update_bytes, type=List[{message.proto.name}], "
                           f"dec_hook={message.proto.name}.dec_hook)\n")
            output_str += (
                f"    return_val = await _underlying_update_all_{message_name_snake_cased}_http("
                f"{message_name_snake_cased}_update_msgspec_obj_list, filter_agg_pipeline, generic_callable, "
                f"return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"        return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"
            output_str += f"    else:\n"
            output_str += (f"        return CustomFastapiResponse(content=str(return_val).encode('utf-8'), "
                           f"status_code=200)\n\n")
        else:
            output_str = f"@perf_benchmark\n"
            if model_type == ModelType.Dataclass:
                output_str += (f"async def underlying_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                               f"update_json_list: List[Dict], filter_agg_pipeline: Any = None, generic_callable: "
                               f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            else:
                output_str += (
                    f"async def underlying_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                    f"updated_list: List[{message.proto.name}], filter_agg_pipeline: Any = None, generic_callable: "
                    f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True) -> "
                    f"List[{message.proto.name}] | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Update All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_put_all_http\n'
            # else not required: avoiding if method desc not provided
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            if model_type == ModelType.Dataclass:
                output_str += (" " * indent_count + f"    {message_name_snake_cased}_json_n_dataclass_handler.clear()    "
                                                    f"# Ideally ths should not be required since we clean handler "
                                                    f"after post call - keeping it to avoid any bug\n")
                output_str += (" " * indent_count +
                               f"    {message_name_snake_cased}_json_n_dataclass_handler.set_json_dict_list("
                               f"{message_name_snake_cased}_update_json_list)\n")
                output_str += " " * indent_count + f"    obj_id_list = [json_obj.get('_id') for json_obj in " \
                                                   f"{message_name_snake_cased}_update_json_list]\n"
                output_str += " " * indent_count + f"    await callback_class.update_all_{message_name_snake_cased}_pre(" \
                                                   f"{message_name_snake_cased}_json_n_dataclass_handler)\n"
            else:
                output_str += " " * indent_count + f"    obj_id_list = [model_obj.id for model_obj in " \
                                                   f"{message_name_snake_cased}_updated_list]\n"
                output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_obj_list = await " \
                                                   f"generic_read_http({message.proto.name}, " \
                                                   f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, has_links={msg_has_links}, " \
                                                   f"read_ids_list=obj_id_list)\n"
                output_str += " " * indent_count + f"    {message_name_snake_cased}_updated_list = " \
                                                   f"await callback_class.update_all_{message_name_snake_cased}_pre(" \
                                                   f"stored_{message_name_snake_cased}_obj_list, {message_name_snake_cased}_updated_list)\n"
                output_str += " " * indent_count + f"    if {message_name_snake_cased}_updated_list is None:\n"
                output_str += " " * indent_count + (f"        raise HTTPException(status_code=503, detail="
                                                    f"'callback_class.update_all_{message_name_snake_cased}_pre returned "
                                                    f"None instead of updated {message_name_snake_cased}_updated_list ')\n")
                output_str += " " * indent_count + f"    elif not {message_name_snake_cased}_updated_list:\n"
                output_str += " " * indent_count + (f"        raise HTTPException(status_code=503, detail="
                                                    f"'callback_class.update_all_{message_name_snake_cased}_pre returned "
                                                    f"empty list instead of updated "
                                                    f"{message_name_snake_cased}_updated_list ')\n")
            output_str += " " * indent_count + (f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = config_yaml_dict.get("
                                                f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
            output_str += " " * indent_count + f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
            indent_count += 4
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_json_list = " \
                              f"await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_json_n_dataclass_handler, " \
                              f"obj_id_list, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
            else:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj_list = " \
                              f"await generic_callable({message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), {message_name_snake_cased}_updated_list, " \
                              f"obj_id_list, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_json_list = await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated_list')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_obj_list = await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                                      f"{message_name_snake_cased}_updated_list, obj_id_list, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated_list')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                                       f"{message_name_snake_cased}_updated_list, obj_id_list, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_both:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated_list')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                                       f"{message_name_snake_cased}_updated_list, obj_id_list, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_updated_list')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                                       f"{message_name_snake_cased}_updated_list, obj_id_list, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.update_all_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_json_list\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.update_all_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj_list, updated_{message_name_snake_cased}_obj_list)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_obj_list\n"
            output_str += " " * indent_count + f"else:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.update_all_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_n_dataclass_handler.get_json_dict_list()\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.update_all_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj_list, {message_name_snake_cased}_updated_list)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_updated_list\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"# Cleaning handler before returning and leaving r_lock\n"
                output_str += " " * indent_count + f"{message_name_snake_cased}_json_n_dataclass_handler.clear()\n"
            output_str += " " * indent_count + f"return return_obj\n\n"
        return output_str

    def handle_PUT_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PUT_all_gen(**kwargs)
        output_str += "\n"
        if model_type == ModelType.Dataclass:
            output_str += f'@{self.api_router_app_name}.put("/put-all-{message_name_snake_cased}' + \
                          f'", status_code=200)\n'
            output_str += (f"async def update_all_{message_name_snake_cased}_http({message_name_snake_cased}_update_req: "
                           f"Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req.body()\n"
            output_str += f"        json_body = orjson.loads(data_body)\n"
            output_str += f"        return await underlying_update_all_{message_name_snake_cased}_http(" \
                          f"json_body, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'update_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        elif model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.put("/put-all-{message_name_snake_cased}' + \
                          f'", status_code=200)\n'
            output_str += (f"async def update_all_{message_name_snake_cased}_http({message_name_snake_cased}_update_req: "
                           f"Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req.body()\n"
            output_str += f"        return await underlying_update_all_{message_name_snake_cased}_http_bytes(" \
                          f"data_body, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'update_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        else:
            output_str += f'@{self.api_router_app_name}.put("/put-all-{message_name_snake_cased}' + \
                          f'", response_model=List[{message.proto.name}] | bool, status_code=200)\n'
            output_str += (
                f"async def update_all_{message_name_snake_cased}_http({message_name_snake_cased}_updated_list: "
                f"List[{message.proto.name}], return_obj_copy: bool | None = True"
                f") -> List[{message.proto.name}] | bool:\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        return await underlying_update_all_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_updated_list, return_obj_copy=return_obj_copy)\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'update_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_patch_gen(self, message: protogen.Message, aggregation_type, msg_has_links,
                                                    shared_lock_list, pass_stored_obj_to_post_callback: bool) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_partial_update_{message_name_snake_cased}_http("
                      f"{message_name_snake_cased}_update_json_dict: Dict[str, None], filter_agg_pipeline: Any = None, "
                      f"generic_callable: Callable[Any, Any] | None = None, return_obj_copy: bool | None = True):\n")
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + (f"    {message.proto.name}.convert_ts_fields_from_epoch_to_datetime_obj("
                                            f"{message_name_snake_cased}_update_json_dict)\n")
        output_str += " " * indent_count + (f"    handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_"
                                            f"json({message.proto.name}, {message_name_snake_cased}_update_json_dict, "
                                            f"is_patch_call=True)\n")
        output_str += " " * indent_count + f"    obj_id = {message_name_snake_cased}_update_json_dict.get('_id')\n"
        if pass_stored_obj_to_post_callback:
            output_str += " " * indent_count + (f"    # Since 'PassStoredObjToPartialUpdatePostCallback' field is "
                                                f"set on plugin option 'MessageJsonRoot'\n\t{' ' * indent_count}# on "
                                                f"this model in proto file, one more fetch is done from db for "
                                                f"stored obj that will be used in\n\t{' ' * indent_count}# "
                                                f"partial_update_{message_name_snake_cased}_post call - reason is, "
                                                f"in generic patch stored obj gets updated in\n\t{' ' * indent_count}# "
                                                f"compare_n_patch. Since this includes extra load of fetching "
                                                f"stored obj again, so if not required\n\t{' ' * indent_count}# in "
                                                f"this model then update proto file and regenerate\n")
            output_str += " " * indent_count + f"    fetched_{message_name_snake_cased}_json_dict = await generic_read_by_id_http(" \
                                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                               f"obj_id, has_links={msg_has_links})\n"
            fetch_json_dict_variable_name = f"fetched_{message_name_snake_cased}_json_dict"
        else:
            output_str += " " * indent_count + (f"    # Since field 'PassStoredObjToPartialUpdatePostCallback' "
                                                f"of plugin option 'MessageJsonRoot' on this model\n\t"
                                                f"{' ' * indent_count}# is not set in proto file, stored obj will "
                                                f"not be passed to post callback call. The reason is since\n\t"
                                                f"{' ' * indent_count}# stored obj is passed to generic "
                                                f"patch, it gets updated and becomes same as updated obj, to solve "
                                                f"this another\n\t{' ' * indent_count}# fetch is done from db and "
                                                f"that instance is passed to post callback call - if stored obj is "
                                                f"required in\n\t{' ' * indent_count}# post callback call then "
                                                f"'PassStoredObjToPartialUpdatePostCallback' field must be set to "
                                                f"True in\n\t{' ' * indent_count}# option 'MessageJsonRoot', but this "
                                                f"will add extra load since it requires fetching stored obj from db so "
                                                f"must\n\t{' ' * indent_count}# be noted before updating and regenerating\n")
            fetch_json_dict_variable_name = f"stored_{message_name_snake_cased}_json_dict"
        output_str += " " * indent_count + (f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = "
                                            f"config_yaml_dict.get('{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
        output_str += " " * indent_count + f"    if {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
        output_str += " " * indent_count + f"        stored_{message_name_snake_cased}_json_dict = "+"{}\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        stored_{message_name_snake_cased}_json_dict = await generic_read_by_id_http(" \
                                           f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                           f"obj_id, has_links={msg_has_links})\n"
        output_str += " " * indent_count + (
            f"    {message_name_snake_cased}_update_json_dict = "
            f"await callback_class.partial_update_{message_name_snake_cased}_pre("
            f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict)\n")
        output_str += " " * indent_count + f"    if not {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      (f"        updated_{message_name_snake_cased}_json_dict = await generic_callable("
                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                       f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict, "
                       f"filter_agg_pipeline, has_links={msg_has_links})\n")
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_json_dict =  await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict, " \
                              f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json')}, " \
                              f"has_links={msg_has_links})\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_dict = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_dict = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict, "
                               f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json')}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_dict = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict, "
                               f"has_links={msg_has_links})\n")
        if pass_stored_obj_to_post_callback:
            output_str += " " * indent_count + (f"    await callback_class.partial_update_{message_name_snake_cased}_post("
                                                f"stored_{message_name_snake_cased}_json_dict, "
                                                f"updated_{message_name_snake_cased}_json_dict)\n")
        else:
            output_str += " " * indent_count + (f"    await callback_class.partial_update_{message_name_snake_cased}_"
                                                f"post(updated_{message_name_snake_cased}_json_dict)\n")
        output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_json_dict\n"
        output_str += " " * indent_count + f"else:\n"
        if pass_stored_obj_to_post_callback:
            output_str += " " * indent_count + (
                f"    await callback_class.partial_update_{message_name_snake_cased}_post("
                f"stored_{message_name_snake_cased}_json_dict, {message_name_snake_cased}_update_json_dict)\n")
        else:
            output_str += " " * indent_count + (
                f"    await callback_class.partial_update_{message_name_snake_cased}_post("
                f"{message_name_snake_cased}_update_json_dict)\n")
        output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_update_json_dict\n"
        output_str += " " * indent_count + f"if return_obj_copy:\n"
        output_str += " " * indent_count + f"    return return_obj\n"
        output_str += " " * indent_count + f"else:\n"
        output_str += " " * indent_count + f"    return True\n\n\n"
        return output_str

    def handle_underlying_PATCH_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Msgspec:
            output_str = self._handle_missing_id_n_datetime_field_callable_generation(message, model_type)
            pass_stored_obj_to_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiHttpRoutesFileHandler.flux_json_root_pass_stored_obj_to_partial_update_pre_post_callback,
                **kwargs)
            output_str += self._handle_msgspec_common_underlying_patch_gen(message, aggregation_type, msg_has_links,
                                                                           shared_lock_list,
                                                                           pass_stored_obj_to_post_callback)
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_partial_update_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict: Dict[str, Any], "
                           f"filter_agg_pipeline: Any = None, generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_http\n'
            output_str += (f"    return_val = await _underlying_partial_update_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict, filter_agg_pipeline, "
                           f"generic_callable, return_obj_copy)\n")
            output_str += f"    if return_val:\n"
            output_str += f"        return_val = {message.proto.name}.from_dict(return_val)\n"
            output_str += f"    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_partial_update_{message_name_snake_cased}_http_json_dict("
                           f"{message_name_snake_cased}_update_json_dict: Dict[str, Any], "
                           f"filter_agg_pipeline: Any = None, generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_http\n'
            output_str += (f"    return_val = await _underlying_partial_update_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict, filter_agg_pipeline, "
                           f"generic_callable, return_obj_copy)\n")
            output_str += f"    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_partial_update_{message_name_snake_cased}_http_bytes("
                           f"{message_name_snake_cased}_update_bytes: bytes, filter_agg_pipeline: Any = None, "
                           f"generic_callable: Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_http\n'
            output_str += (f"    {message_name_snake_cased}_update_json_dict = orjson.loads("
                           f"{message_name_snake_cased}_update_bytes)\n")
            output_str += (f"    return_val = await _underlying_partial_update_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict, filter_agg_pipeline, "
                           f"generic_callable, return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"        return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"
            output_str += f"    else:\n"
            output_str += (f"        return CustomFastapiResponse(content=str(return_val).encode('utf-8'), "
                           f"status_code=200)\n\n")
        else:
            output_str = self._handle_missing_id_n_datetime_field_callable_generation(message, model_type)
            output_str += self._handle_str_int_val_callable_generation(message)
            output_str += "\n"
            output_str += f"@perf_benchmark\n"
            if model_type == ModelType.Dataclass:
                output_str += (f"async def underlying_partial_update_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_update_req_json: Dict, filter_agg_pipeline: Any = None, "
                               f"generic_callable: Callable[[...], Any] | None = None, return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_partial_update_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_update_req_json: Dict, filter_agg_pipeline: Any = None, "
                               f"generic_callable: Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                               f") -> {message.proto.name} | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_http\n'
            # else not required: avoiding if method desc not provided
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + (f"    handle_str_formatted_int_fields_in_{message_name_snake_cased}_"
                                                f"json({message_name_snake_cased}_update_req_json)\n")
            output_str += " " * indent_count + (f"    handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_"
                                                f"json({message.proto.name}, {message_name_snake_cased}_update_req_json, "
                                                f"is_patch_call=True)\n")
            if model_type == ModelType.Dataclass:
                output_str += (" " * indent_count + f"    {message_name_snake_cased}_json_n_dataclass_handler.clear()    "
                                                    f"# Ideally ths should not be required since we clean handler "
                                                    f"after post call - keeping it to avoid any bug\n")
                output_str += (" " * indent_count +
                               f"    {message_name_snake_cased}_json_n_dataclass_handler.set_json_dict("
                               f"{message_name_snake_cased}_update_req_json)\n")
                output_str += " " * indent_count + f"    obj_id = {message_name_snake_cased}_update_req_json.get('_id')\n"
                output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_json_obj = await generic_read_by_id_http(" \
                                                   f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                                   f"obj_id, has_links={msg_has_links})\n"
                output_str += " " * indent_count + (f"    {message_name_snake_cased}_json_n_dataclass_handler."
                                                    f"set_stored_json_dict(stored_{message_name_snake_cased}_json_obj)\n")
                output_str += " " * indent_count + (f"    await callback_class.partial_update_{message_name_snake_cased}_pre("
                                                    f"{message_name_snake_cased}_json_n_dataclass_handler)\n")
            else:
                output_str += " " * indent_count + f"    obj_id = {message_name_snake_cased}_update_req_json.get('_id')\n"
                output_str += " " * indent_count + f"    if obj_id is None:\n"
                output_str += " " * indent_count + f'        err_str_ = f"Can not find _id key in received response body for ' \
                                                   f'patch operation of {message.proto.name}, response body: ' + \
                                                   '{'+f'{message_name_snake_cased}_update_req_json'+'}"\n'
                output_str += " " * indent_count + f"        raise HTTPException(status_code=503, detail=err_str_)\n"
                output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                                                   f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                                   f"obj_id, has_links={msg_has_links})\n"
                output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_req_json = "
                                                    f"await callback_class.partial_update_{message_name_snake_cased}_pre("
                                                    f"stored_{message_name_snake_cased}_obj, "
                                                    f"{message_name_snake_cased}_update_req_json)\n")
                output_str += " " * indent_count + f"    if {message_name_snake_cased}_update_req_json is None:\n"
                output_str += " " * indent_count + (f"        raise HTTPException(status_code=503, detail="
                                                    f"'callback_class.partial_update_{message_name_snake_cased}_pre returned "
                                                    f"None instead of updated {message_name_snake_cased}_update_req_json ')\n")
            output_str += " " * indent_count + (f"    if not config_yaml_dict.get("
                                                f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}'):\n")
            indent_count += 4
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_json_n_dataclass_handler, filter_agg_pipeline, "
                               f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
            else:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                               f"{message_name_snake_cased}_update_req_json, filter_agg_pipeline, "
                               f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_json_obj =  await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message_name_snake_cased}_json_n_dataclass_handler, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_obj =  await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                                      f"{message_name_snake_cased}_update_req_json, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                                       f"{message_name_snake_cased}_update_req_json, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_both:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                                       f"{message_name_snake_cased}_update_req_json, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_json_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                                       f"{message_name_snake_cased}_update_req_json, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.partial_update_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_json_obj\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.partial_update_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_obj\n"
            output_str += " " * indent_count + f"else:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.partial_update_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_n_dataclass_handler.get_json_dict()\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.partial_update_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_update_req_json)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_update_req_json\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"# Cleaning handler before returning and leaving r_lock\n"
                output_str += " " * indent_count + f"{message_name_snake_cased}_json_n_dataclass_handler.clear()\n"
            output_str += " " * indent_count + f"return return_obj\n\n"
        return output_str

    def handle_PATCH_gen(self, **kwargs) -> str:
        message, _, _, model_type = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PATCH_gen(**kwargs)
        output_str += f"\n"
        if model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}' + \
                          f'", status_code=200)\n'
            output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_update_req_body: " \
                          f"Request, return_obj_copy: bool | None = True):\n"
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req_body.body()\n"
            output_str += (f'        return await underlying_partial_update_{message_name_snake_cased}_http_bytes('
                           f'data_body, return_obj_copy=return_obj_copy)\n')
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'partial_update_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        else:
            if model_type == ModelType.Dataclass:
                output_str += f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}' + \
                              f'", status_code=200)\n'
                output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_update_req_body: " \
                              f"Request, return_obj_copy: bool | None = True):\n"
            else:
                output_str += f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}' + \
                              f'", response_model={message.proto.name} | bool, status_code=200)\n'
                output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_update_req_body: " \
                              f"Request, return_obj_copy: bool | None = True) -> {message.proto.name} | bool:\n"
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req_body.body()\n"
            output_str += f"        json_body = orjson.loads(data_body)\n"
            output_str += (f'        return await underlying_partial_update_{message_name_snake_cased}_http(json_body, '
                           f'return_obj_copy=return_obj_copy)\n')
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'partial_update_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        return output_str

    def _get_int_field_list(self, message: protogen.Message, parent_field_names: str | None = None) -> List[str]:
        int_field_list = []
        for field in message.fields:
            if field.message is not None:
                if parent_field_names is not None:
                    if field.cardinality.name.lower() == "repeated":
                        parent_field_names_str = f"{parent_field_names}.[{field.proto.name}]"
                    else:
                        parent_field_names_str = f"{parent_field_names}.{field.proto.name}"
                else:
                    if field.cardinality.name.lower() == "repeated":
                        parent_field_names_str = f"[{field.proto.name}]"
                    else:
                        parent_field_names_str = field.proto.name
                int_field_list.extend(self._get_int_field_list(field.message, parent_field_names_str))
            elif (field.kind.name.lower() in ["int32", "int64"] and
                  not self.is_bool_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_val_is_datetime)):
                if parent_field_names is not None:
                    if field.cardinality.name.lower() == "repeated":
                        int_field_list.append(f"{parent_field_names}.[{field.proto.name}]")
                    else:
                        int_field_list.append(f"{parent_field_names}.{field.proto.name}")
                else:
                    if field.cardinality.name.lower() == "repeated":
                        int_field_list.append(f"[{field.proto.name}]")
                    else:
                        int_field_list.append(field.proto.name)
        return int_field_list

    def __handle_str_int_val_callable_variables_set(
            self, temp_field_name_dict: Dict, last_field_name: str,
            indent_count: int, is_recurr_call: bool = False):
        fields = temp_field_name_dict.keys()

        output_str = ""
        if fields and is_recurr_call:
            output_str += " " * (
                    indent_count * 4) + f'if {last_field_name} is not None:\n'
            indent_count += 1
        for field in fields:
            if not (field[0] == "[" and field[-1] == "]"):
                val = last_field_name + "__" + field
                output_str += " " * (
                        indent_count * 4) + f'{val} = {last_field_name}.get("{field}")\n'
                if not temp_field_name_dict[field]:     # if is last node
                    output_str += " " * (
                            indent_count * 4) + f'if {val} is not None and isinstance({val}, str):\n'
                    indent_count += 1
                    output_str += " " * (
                            indent_count * 4) + f'{last_field_name}["{field}"] = parse_to_int({val})\n'
                    indent_count -= 1
        if fields and is_recurr_call:
            indent_count -= 1

        for field in fields:
            if not (field[0] == "[" and field[-1] == "]"):
                last_field_name_ = last_field_name + "__" + field
                output_str += self.__handle_str_int_val_callable_variables_set(
                                temp_field_name_dict[field], last_field_name_, indent_count,
                                is_recurr_call=True)
        return output_str

    def _handle_str_int_val_callable_generation(self, message: protogen.Message) -> str:
        if message in self._msg_already_generated_str_formatted_int_fields_handler_list:
            # if handler function is already generated for this model for either patch or patch-all then
            # avoiding duplicate function creation
            return ""
        # else not required: generating if not generated for this model already

        message_name = message.proto.name
        message_name_camel_cased = convert_camel_case_to_specific_case(message_name)
        int_field_list: List[str] = self._get_int_field_list(message)

        output_str = ""
        if int_field_list:
            output_str += (f"def handle_str_formatted_int_fields_in_{message_name_camel_cased}_"
                           f"json({message_name_camel_cased}_update_req_json: Dict) -> None:\n")

            temp_field_name_dict: Dict = {}
            last_field_name = f"{message_name_camel_cased}_update_req_json"
            temp_field_name_dict[last_field_name] = {}
            for int_field in int_field_list:
                int_fields_dot_sep_list: List[str] = int_field.split(".")

                temp_dict = temp_field_name_dict[last_field_name]
                for index, field in enumerate(int_fields_dot_sep_list):
                    if field not in temp_dict:
                        temp_dict[field] = {}
                    temp_dict = temp_dict[field]

            output_str += "\n"

            indent_count = 1
            output_str += self.__handle_str_int_val_callable_variables_set(
                            temp_field_name_dict[last_field_name], last_field_name, indent_count)
            output_str += "\n"

            for int_field in int_field_list:
                int_fields_dot_sep_list: List[str] = int_field.split(".")
                indent_count = 1
                last_field_name = f"{message_name_camel_cased}_update_req_json"

                _has_repeated_fields: bool = False
                for field in int_fields_dot_sep_list:
                    if field.startswith("[") and field.endswith("]"):
                        _has_repeated_fields = True

                if _has_repeated_fields:
                    for index, field in enumerate(int_fields_dot_sep_list):
                        if field == int_fields_dot_sep_list[-1]:
                            output_str += " " * (
                                        indent_count * 4) + f'{field} = {last_field_name}.get("{field}")\n'
                            output_str += (" " * (indent_count*4) +
                                           f"if {field} is not None and isinstance({field}, str):\n")
                            indent_count += 1
                            output_str += (" " * (indent_count*4) +
                                           f'{last_field_name}["{field}"] = parse_to_int({field})\n')
                            output_str += "\n"
                        else:
                            if field[0] == "[" and field[-1] == "]":
                                field = field[1:-1]  # removing [] from field name added to identify as list type
                                output_str += " " * (
                                        indent_count * 4) + f'{field} = {last_field_name}.get("{field}")\n'
                                output_str += " " * (indent_count * 4) + f"if {field}:\n"
                                indent_count += 1
                                output_str += " " * (indent_count * 4) + f"for {field}_ in {field}:\n"
                                indent_count += 1
                                last_field_name = f"{field}_"
                            else:
                                output_str += " " * (
                                        indent_count * 4) + f'{field} = {last_field_name}.get("{field}")\n'
                                output_str += " " * (indent_count*4) + f"if {field} is not None:\n"
                                indent_count += 1
                                last_field_name = field

            # adding msg to cache to be checked for another call from patch or patch-all to avoid
            # duplicate function creation
            self._msg_already_generated_str_formatted_int_fields_handler_list.append(message)

        return output_str

    def _get_fields_having_id_field_in_dict(self, message: protogen.Message,
                                            fields_dict: Dict,
                                            indent_count: int = 0):
        output_str = ""
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        for field in message.fields:
            if field.proto.name == "id":
                fields_dict[field.proto.name] = "_id"
                continue
            if FastapiHttpRoutesFileHandler.is_option_enabled(field,
                                                              FastapiHttpRoutesFileHandler.flux_fld_val_is_datetime):
                fields_dict[field.proto.name] = "datetime"
            if field.message is not None:
                fields_dict[field.proto.name] = {"cardinality": field.cardinality.name.lower(),
                                                 "message": field.message}
                self._get_fields_having_id_field_in_dict(field.message, fields_dict[field.proto.name])
                if len(fields_dict[field.proto.name]) == 2:      # only contains cardinality an message
                    del fields_dict[field.proto.name]

    def _get_fields_having_id_or_date_time_field_str(self, field_dict: Dict, prefix_fields: str | None = None,
                                                     indent_count: int = 0):
        output_str = ""

        cardinality = field_dict.pop("cardinality")
        message = field_dict.pop("message")
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        loop_count = 0
        for field_name, value in field_dict.items():
            loop_count += 1
            output_str_ = ""
            last_prefix_fields = prefix_fields
            last_indent_count = indent_count
            if cardinality != "repeated":
                if field_name == "id":
                    output_str_ += " " * (indent_count*4) + f'    if {prefix_fields} is not None:\n'
                    output_str_ += " " * (indent_count*4) + f'        _id = {prefix_fields}.get("_id")\n'
                    output_str_ += " " * (indent_count*4) + f'        if _id is None:\n'
                    output_str_ += " " * (indent_count*4) + f'            {prefix_fields}["_id"] = {message_name}.next_id()\n'
                elif value == "datetime":
                    if not prefix_fields:
                        output_str_ += " " * (indent_count*4) + f'    date_time_field = {message_name_snake_cased}_json.get("{field_name}")\n'
                        output_str_ += (" " * (indent_count*4) +
                                        f'    if date_time_field is not None and isinstance(date_time_field, str):\n')
                        output_str_ += (" " * (indent_count*4) +
                                        f'        {message_name_snake_cased}_json["{field_name}"] = pendulum.parse(date_time_field)\n')

                    else:
                        output_str_ += " " * (indent_count*4) + f'    if {prefix_fields} is not None:\n'
                        output_str_ += (" " * (indent_count*4) +
                                        f'        date_time_field = {prefix_fields}.get("{field_name}")\n')
                        output_str_ += (" " * (indent_count*4) +
                                        f'        if date_time_field is not None and isinstance(date_time_field, str):\n')
                        output_str_ += (" " * (indent_count*4) +
                                        f'            {prefix_fields}["{field_name}"] = pendulum.parse(date_time_field)\n')

                else:
                    if not prefix_fields:
                        output_str_ += " " * (indent_count*4) + (f'    {message_name_snake_cased}__{field_name} '
                                      f'= {message_name_snake_cased}_json.get("{field_name}")\n')
                        prefix_fields += f"{message_name_snake_cased}__{field_name}"
                    else:
                        output_str_ += " " * (indent_count*4) + f"    {prefix_fields}__{field_name} = None\n"
                        output_str_ += " " * (indent_count*4) + f"    if {prefix_fields} is not None:\n"
                        output_str_ += " " * (indent_count*4) + (f'        {prefix_fields}__{field_name} '
                                       f'= {prefix_fields}.get("{field_name}")\n')
                        prefix_fields += f"__{field_name}"


                    output_str_ += self._get_fields_having_id_or_date_time_field_str(value, prefix_fields, indent_count)
            else:
                if loop_count == 1:
                    output_str_ += " " * (indent_count*4) + f"    if {prefix_fields} is not None:\n"
                    output_str_ += " " * (indent_count*4) + f"        for {prefix_fields}_ in {prefix_fields}:\n"
                    indent_count += 2
                # else not required: for loop block is already open if loop count is more than 1
                if field_name == "id":
                    # if message_name_snake_cased:
                    output_str_ += (" " * (indent_count*4) + f'    _id = {prefix_fields}_.get("_id")\n')
                    output_str_ += " " * (indent_count*4) + f'    if _id is None:\n'
                    output_str_ += (" " * (indent_count*4) +
                                   f'        {prefix_fields}_["_id"] = {message_name}.next_id()\n')

                elif value == "datetime":
                    output_str_ += (" " * (indent_count*4) +
                                    f'    date_time_field = {prefix_fields}_.get("{field_name}")\n')
                    output_str_ += (" " * (indent_count*4) +
                                    f'    if date_time_field is not None and isinstance(date_time_field, str):\n')
                    output_str_ += (" " * (indent_count*4) +
                                    f'        {prefix_fields}_["{field_name}"] = pendulum.parse(date_time_field)\n')

                else:
                    output_str_ += " " * (indent_count*4) + (f'    {prefix_fields}__{field_name} '
                                  f'= {prefix_fields}_.get("{field_name}")\n')

                    prefix_fields += f"__{field_name}"
                    # indent_count += 1
                    output_str_ += self._get_fields_having_id_or_date_time_field_str(value, prefix_fields, indent_count=indent_count)
            output_str += output_str_
            prefix_fields = last_prefix_fields
            # indent_count = last_indent_count
        return output_str

    def _handle_missing_id_n_datetime_field_callable_generation(self, message: protogen.Message,
                                                                model_type: bool) -> str:
        if message in self._msg_already_generated_id_n_date_time_fields_handler_list:
            # if handler function is already generated for this model for either create, create-all,
            # patch or patch-all then avoiding duplicate function creation
            return ""
        # else not required: generating if not generated for this model already

        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        # to avoid duplicate generation
        self._msg_already_generated_id_n_date_time_fields_handler_list.append(message)

        if model_type == ModelType.Dataclass:
            output_str = (f"def handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_json("
                          f"{message_name}: Type[dataclass], {message_name_snake_cased}_json: Dict, "
                          f"is_patch_call: bool):\n")
        else:
            output_str = (f"def handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_json("
                          f"{message_name}: Type[{message.proto.name}], {message_name_snake_cased}_json: Dict, "
                          f"is_patch_call: bool):\n")

        output_str += f"    _id = {message_name_snake_cased}_json.get(\"_id\")\n"
        output_str += f"    if _id is None:\n"
        output_str += f"        if is_patch_call:\n"
        output_str += (f'            err_str_ = f"Can not find _id key in received response body '
                       f'of {message_name} for patch, response body: '+'{'+f'{message_name_snake_cased}'+'_json}"\n')
        output_str += f'            raise HTTPException(status_code=503, detail=err_str_)\n'
        output_str += f'        else:\n'
        output_str += f'            {message_name_snake_cased}_json["_id"] = {message_name}.next_id()\n\n'
        temp_dict = {message_name: {}}
        self._get_fields_having_id_field_in_dict(message, temp_dict[message_name])

        temp_dict[message_name].pop("id")   # since id handling for root type is already done
        temp_dict[message_name]["cardinality"] = "required"
        temp_dict[message_name]["message"] = message
        output_str += self._get_fields_having_id_or_date_time_field_str(temp_dict[message_name], "")
        output_str += "\n\n"
        return output_str

    def _handle_msgspec_common_underlying_patch_all_gen(self, message: protogen.Message, aggregation_type,
                                                        msg_has_links, shared_lock_list,
                                                        pass_stored_obj_to_post_callback) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_partial_update_all_{message_name_snake_cased}_http("
                      f"{message_name_snake_cased}_update_json_dict_list: List[Dict[str, Any]], "
                      f"filter_agg_pipeline: Any = None, "
                      f"generic_callable: Callable[Any, Any] | None = None, "
                      f"return_obj_copy: bool | None = True):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)
        output_str += mutex_handling_str
        output_str += " " * indent_count + f"    obj_id_list = []\n"
        output_str += " " * indent_count + (f"    for {message_name_snake_cased}_update_json_dict in "
                                            f"{message_name_snake_cased}_update_json_dict_list:\n")
        output_str += " " * indent_count + f"        {message.proto.name}.convert_ts_fields_from_epoch_to_datetime_obj({message_name_snake_cased}_update_json_dict)\n"
        output_str += " " * indent_count + (
            f"        handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_"
            f"json({message.proto.name}, {message_name_snake_cased}_update_json_dict, "
            f"is_patch_call=True)\n")
        output_str += " " * indent_count + f"        obj_id_list.append({message_name_snake_cased}_update_json_dict.get('_id'))\n"
        if pass_stored_obj_to_post_callback:
            output_str += " " * indent_count + (f"    # Since 'PassStoredObjToPartialUpdateAllPostCallback' field is "
                                                f"set on plugin option 'MessageJsonRoot'\n\t{' ' * indent_count}# on "
                                                f"this model in proto file, one more fetch is done from db for "
                                                f"stored obj list that will be used in\n\t{' ' * indent_count}# "
                                                f"partial_update_all_{message_name_snake_cased}_post "
                                                f"call - reason is, in generic patch-all stored obj list gets updated "
                                                f"in\n\t{' ' * indent_count}# compare_n_patch. Since this includes "
                                                f"extra load of fetching stored obj list again, so if not "
                                                f"required\n\t{' ' * indent_count}# in this model then update "
                                                f"proto file and regenerate\n")
            output_str += " " * indent_count + (f"    fetched_{message_name_snake_cased}_json_dict_list = await "
                                                f"generic_read_http({message.proto.name}, "
                                                f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                                f"has_links={msg_has_links}, read_ids_list=obj_id_list)\n")
            fetch_json_dict_variable_name = f"fetched_{message_name_snake_cased}_json_dict_list"
        else:
            output_str += " " * indent_count + (f"    # Since field 'PassStoredObjToPartialUpdateAllPostCallback' "
                                                f"of plugin option 'MessageJsonRoot' on this model\n\t"
                                                f"{' ' * indent_count}# is not set in proto file, stored obj list will "
                                                f"not be passed to post callback call. The reason is since\n\t"
                                                f"{' ' * indent_count}# stored obj list is passed to generic patch, "
                                                f"it gets updated and becomes same as updated obj list, to solve "
                                                f"this another\n\t{' ' * indent_count}# fetch is done from db and "
                                                f"that instance is passed to post callback call - if stored obj is "
                                                f"required in\n\t{' ' * indent_count}# post callback call then "
                                                f"'PassStoredObjToPartialUpdateAllPostCallback' field must be set to "
                                                f"True in\n\t{' ' * indent_count}# option 'MessageJsonRoot', but this "
                                                f"will add extra load since it requires fetching stored obj list "
                                                f"from db so must\n\t{' ' * indent_count}# be noted before "
                                                f"updating and regenerating\n")
            fetch_json_dict_variable_name = f"stored_{message_name_snake_cased}_json_dict_list"
        output_str += " " * indent_count + (f"    {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)} = "
                                            f"config_yaml_dict.get('{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}')\n")
        output_str += " " * indent_count + f"    if {self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}:\n"
        output_str += " " * indent_count + f"        stored_{message_name_snake_cased}_json_dict_list = []\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + (f"        stored_{message_name_snake_cased}_json_dict_list = await "
                                            f"generic_read_http({message.proto.name}, "
                                            f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                            f"has_links={msg_has_links}, read_ids_list=obj_id_list)\n")
        output_str += " " * indent_count + (
            f"    {message_name_snake_cased}_update_json_dict_list = "
            f"await callback_class.partial_update_all_{message_name_snake_cased}_pre("
            f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict_list)\n")
        output_str += " " * indent_count + (f"    if not config_yaml_dict.get('{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}'):\n")
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable(" \
                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict_list, " \
                      f"obj_id_list, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_update_req_json_list =  await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict_list, obj_id_list, " \
                              f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json_list')}, " \
                              f"has_links={msg_has_links})\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict_list, "
                               f"obj_id_list, update_agg_pipeline={update_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links})\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{fetch_json_dict_variable_name}, {message_name_snake_cased}_update_json_dict_list, "
                               f"obj_id_list, {self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json_list')}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
            case other:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{fetch_json_dict_variable_name}, " \
                              f"{message_name_snake_cased}_update_json_dict_list, obj_id_list, " \
                              f"has_links={msg_has_links})\n"
        if pass_stored_obj_to_post_callback:
            output_str += " " * indent_count + (f"    await callback_class.partial_update_all_{message_name_snake_cased}"
                                                f"_post(stored_{message_name_snake_cased}_json_dict_list, "
                                                f"updated_{message_name_snake_cased}_update_req_json_list)\n")
        else:
            output_str += " " * indent_count + (f"    await callback_class.partial_update_all_{message_name_snake_cased}"
                                                f"_post(updated_{message_name_snake_cased}_update_req_json_list)\n")
        output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_update_req_json_list\n"
        output_str += " " * indent_count + f"else:\n"
        if pass_stored_obj_to_post_callback:
            output_str += " " * indent_count + (f"    await callback_class.partial_update_all_{message_name_snake_cased}"
                                                f"_post(stored_{message_name_snake_cased}_json_dict_list, "
                                                f"{message_name_snake_cased}_update_json_dict_list)\n")
        else:
            output_str += " " * indent_count + (f"    await callback_class.partial_update_all_{message_name_snake_cased}"
                                                f"_post({message_name_snake_cased}_update_json_dict_list)\n")
        output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_update_json_dict_list\n"
        output_str += " " * indent_count + f"if return_obj_copy:\n"
        output_str += " " * indent_count + f"    return return_obj\n"
        output_str += " " * indent_count + f"else:\n"
        output_str += " " * indent_count + f"    return True\n\n\n"
        return output_str

    def handle_underlying_PATCH_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)

        if model_type == ModelType.Msgspec:
            pass_stored_obj_to_post_callback = self._get_if_pass_stored_obj_to_pre_post_callback(
                FastapiHttpRoutesFileHandler.flux_json_root_pass_stored_obj_to_partial_update_all_pre_post_callback,
                **kwargs)
            output_str = self._handle_msgspec_common_underlying_patch_all_gen(message, aggregation_type,
                                                                              msg_has_links, shared_lock_list,
                                                                              pass_stored_obj_to_post_callback)
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_partial_update_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict_list: List[Dict[str, Any]], "
                           f"filter_agg_pipeline: Any = None, "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_all_http\n'
            output_str += (f"    return_val = await _underlying_partial_update_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict_list, filter_agg_pipeline, "
                           f"generic_callable, return_obj_copy)\n")
            output_str += "    if return_obj_copy:\n"
            output_str += f"        return_val = {message.proto.name}.from_dict_list(return_val)\n"
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_partial_update_all_{message_name_snake_cased}_http_json_dict("
                           f"{message_name_snake_cased}_update_json_dict_list: List[Dict[str, Any]], "
                           f"filter_agg_pipeline: Any = None, generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_all_http\n'
            output_str += (f"    return_val = await _underlying_partial_update_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict_list, filter_agg_pipeline, "
                           f"generic_callable, return_obj_copy)\n")
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_partial_update_all_{message_name_snake_cased}_http_bytes("
                           f"{message_name_snake_cased}_update_req_bytes: bytes, "
                           f"filter_agg_pipeline: Any = None, "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_all_http\n'
            output_str += (f"    {message_name_snake_cased}_update_json_dict_list = orjson.loads("
                           f"{message_name_snake_cased}_update_req_bytes)\n")
            output_str += (f"    return_val = await _underlying_partial_update_all_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_update_json_dict_list, filter_agg_pipeline, "
                           f"generic_callable, return_obj_copy)\n")
            output_str += f"    if return_obj_copy:\n"
            output_str += f"        return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"        return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"
            output_str += f"    else:\n"
            output_str += (f"        return CustomFastapiResponse(content=str(return_val).encode('utf-8'), "
                           f"status_code=200)\n\n")
        else:
            output_str = self._handle_missing_id_n_datetime_field_callable_generation(message, model_type)
            output_str += self._handle_str_int_val_callable_generation(message)
            output_str += "\n"
            output_str += f"@perf_benchmark\n"
            if model_type == ModelType.Dataclass:
                output_str += (f"async def underlying_partial_update_all_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_update_req_json_list: List[Dict], "
                               f"filter_agg_pipeline: Any = None, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_partial_update_all_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_update_req_json_list: List[Dict], "
                               f"filter_agg_pipeline: Any = None, "
                               f"generic_callable: Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                               f") -> List[{message.proto.name}] | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Partial Update route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_patch_all_http\n'
            # else not required: avoiding if method desc not provided
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + f"    obj_id_list = []\n"
            output_str += " " * indent_count + f"    for {message_name_snake_cased}_update_req_json in " \
                                               f"{message_name_snake_cased}_update_req_json_list:\n"
            output_str += " " * indent_count + (f"        handle_str_formatted_int_fields_in_{message_name_snake_cased}_"
                                                f"json({message_name_snake_cased}_update_req_json)\n")
            output_str += " " * indent_count + (f"        handle_missing_id_n_datetime_fields_in_{message_name_snake_cased}_"
                                                f"json({message.proto.name}, {message_name_snake_cased}_update_req_json, "
                                                f"is_patch_call=True)\n")
            output_str += " " * indent_count + f"        obj_id = {message_name_snake_cased}_update_req_json.get('_id')\n"
            output_str += " " * indent_count + f"        if obj_id is None:\n"
            output_str += " " * indent_count + f'            err_str_ = f"Can not find _id key in received response ' \
                                               f'body for patch all operation of {message.proto.name}, response body: ' + \
                          '{' + f'{message_name_snake_cased}_update_req_json_list' + '}"\n'
            output_str += " " * indent_count + f"            raise HTTPException(status_code=503, detail=err_str_)\n"
            output_str += " " * indent_count + f"        obj_id_list.append(obj_id)\n"
            if model_type == ModelType.Dataclass:
                output_str += (" " * indent_count + f"    {message_name_snake_cased}_json_n_dataclass_handler.clear()    "
                                                    f"# Ideally ths should not be required since we clean handler "
                                                    f"after post call - keeping it to avoid any bug\n")
                output_str += (" " * indent_count +
                               f"    {message_name_snake_cased}_json_n_dataclass_handler.set_json_dict_list("
                               f"{message_name_snake_cased}_update_req_json_list)\n")
                output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_json_list = await "
                                                    f"generic_read_http({message.proto.name}, "
                                                    f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                                    f"has_links={msg_has_links}, read_ids_list=obj_id_list)\n")
                output_str += " " * indent_count + (f'    {message_name_snake_cased}_json_n_dataclass_handler.'
                                                    f'set_stored_json_dict_list(stored_{message_name_snake_cased}_json_list)\n')
                output_str += " " * indent_count + (f"    await callback_class.partial_update_all_{message_name_snake_cased}_pre("
                                                    f"{message_name_snake_cased}_json_n_dataclass_handler)\n")
            else:
                output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_obj_list = await "
                                                    f"generic_read_http({message.proto.name}, "
                                                    f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                                    f"has_links={msg_has_links}, read_ids_list=obj_id_list)\n")
                output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_req_json_list = "
                                                    f"await callback_class.partial_update_all_{message_name_snake_cased}_pre("
                                                    f"stored_{message_name_snake_cased}_obj_list, "
                                                    f"{message_name_snake_cased}_update_req_json_list)\n")
                output_str += " " * indent_count + f"    if {message_name_snake_cased}_update_req_json_list is None:\n"
                output_str += " " * indent_count + (f"        raise HTTPException(status_code=503, detail="
                                                    f"'callback_class.partial_update_all_{message_name_snake_cased}_pre returned "
                                                    f"None instead of updated {message_name_snake_cased}_update_req_json_list ')\n")
                output_str += " " * indent_count + f"    elif not {message_name_snake_cased}_update_req_json_list:\n"
                output_str += " " * indent_count + (f"        raise HTTPException(status_code=503, detail="
                                                    f"'callback_class.partial_update_all_{message_name_snake_cased}_pre returned "
                                                    f"empty list instead of updated "
                                                    f"{message_name_snake_cased}_update_req_json_list ')\n")
            output_str += " " * indent_count + (f"    if not config_yaml_dict.get("
                                                f"'{self.get_avoid_db_n_ws_update_var_name(message_name_snake_cased)}'):\n")
            indent_count += 4
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, filter_agg_pipeline, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            else:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj_list = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                              f"{message_name_snake_cased}_update_req_json_list, obj_id_list, filter_agg_pipeline, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_update_req_json_list =  await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json_list')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_obj_list =  await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                                      f"{message_name_snake_cased}_update_req_json_list, obj_id_list, " \
                                      f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json_list')}, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                                       f"{message_name_snake_cased}_update_req_json_list, obj_id_list, "
                                       f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
                case FastapiHttpRoutesFileHandler.aggregation_type_both:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json_list')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                                       f"{message_name_snake_cased}_update_req_json_list, obj_id_list, "
                                       f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_update_req_json_list')}, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_update_req_json_list = await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message_name_snake_cased}_json_n_dataclass_handler, obj_id_list, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"        updated_{message_name_snake_cased}_obj_list = await generic_callable(" \
                                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                                      f"{message_name_snake_cased}_update_req_json_list, obj_id_list, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.partial_update_all_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_update_req_json_list\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.partial_update_all_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj_list, updated_{message_name_snake_cased}_obj_list)\n"
                output_str += " " * indent_count + f"    return_obj = updated_{message_name_snake_cased}_obj_list\n"
            output_str += " " * indent_count + f"else:\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"    await callback_class.partial_update_all_{message_name_snake_cased}_post({message_name_snake_cased}_json_n_dataclass_handler)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_json_n_dataclass_handler.get_json_dict_list()\n"
            else:
                output_str += " " * indent_count + f"    await callback_class.partial_update_all_{message_name_snake_cased}_post(stored_{message_name_snake_cased}_obj_list, {message_name_snake_cased}_update_req_json_list)\n"
                output_str += " " * indent_count + f"    return_obj = {message_name_snake_cased}_update_req_json_list\n"
            if model_type == ModelType.Dataclass:
                output_str += " " * indent_count + f"# Cleaning handler before returning and leaving r_lock\n"
                output_str += " " * indent_count + f"{message_name_snake_cased}_json_n_dataclass_handler.clear()\n"
            output_str += " " * indent_count + f"return return_obj\n\n"
        return output_str

    def handle_PATCH_all_gen(self, **kwargs) -> str:
        message, _, _, model_type = self._unpack_kwargs_without_id_field_type(**kwargs)

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PATCH_all_gen(**kwargs)
        output_str += f"\n"
        if model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.patch("/patch-all-{message_name_snake_cased}' + \
                          f'", status_code=200)\n'
            output_str += (f"async def partial_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                           f"update_req_body: Request, return_obj_copy: bool | None = True):\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req_body.body()\n"
            output_str += (f'        return await underlying_partial_update_all_{message_name_snake_cased}_http_bytes('
                           f'data_body, return_obj_copy=return_obj_copy)\n')
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'partial_update_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        else:
            if model_type == ModelType.Dataclass:
                output_str += f'@{self.api_router_app_name}.patch("/patch-all-{message_name_snake_cased}' + \
                              f'", status_code=200)\n'
                output_str += (f"async def partial_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                               f"update_req_body: Request, return_obj_copy: bool | None = True):\n")
            else:
                output_str += f'@{self.api_router_app_name}.patch("/patch-all-{message_name_snake_cased}' + \
                              f'", response_model=List[{message.proto.name}] | bool, status_code=200)\n'
                output_str += (f"async def partial_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                               f"update_req_body: Request, return_obj_copy: bool | None = True"
                               f") -> List[{message.proto.name}] | bool:\n")
            output_str += self._add_view_check_code_in_route()
            output_str += f"    try:\n"
            output_str += f"        data_body = await {message_name_snake_cased}_update_req_body.body()\n"
            output_str += f"        json_body = orjson.loads(data_body)\n"
            output_str += (f'        return await underlying_partial_update_all_{message_name_snake_cased}_http(json_body, '
                           f'return_obj_copy=return_obj_copy)\n')
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'partial_update_all_{message_name_snake_cased}_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_delete_gen(self, message: protogen.Message, aggregation_type,
                                                        msg_has_links, shared_lock_list, id_field_type) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = ""
        if id_field_type is not None:
            output_str += (f"async def _underlying_delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id: {id_field_type}, "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
        else:
            output_str += (f"async def _underlying_delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + f"    await callback_class.delete_{message_name_snake_cased}_pre(" \
                                           f"{message_name_snake_cased}_id)\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter | FastapiHttpRoutesFileHandler.aggregation_type_both:
                err_str = "Filter Aggregation type is not supported in Delete operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message.proto.name}BaseModel, {message_name_snake_cased}_id, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
            case other:
                output_str += " " * indent_count + \
                              f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message.proto.name}BaseModel, {message_name_snake_cased}_id, " \
                              f"has_links={msg_has_links})\n"
        output_str += " " * indent_count + f"    await callback_class.delete_{message_name_snake_cased}_post(" \
                                           f"delete_web_resp)\n"
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return delete_web_resp\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n\n\n"
        return output_str

    def handle_underlying_DELETE_gen(self, **kwargs) -> str:
        message, aggregation_type, id_field_type, shared_lock_list, model_type = (
            self._unpack_kwargs_with_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Msgspec:
            output_str = self._handle_msgspec_common_underlying_delete_gen(message, aggregation_type, msg_has_links,
                                                                           shared_lock_list, id_field_type)
            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += (f"async def underlying_delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {id_field_type}, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: "
                               f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Delete route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_http\n'
            output_str += (f"    return_val = await _underlying_delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id, generic_callable, return_obj_copy)\n")
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += (f"async def underlying_delete_{message_name_snake_cased}_http_bytes("
                               f"{message_name_snake_cased}_id: {id_field_type}, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_delete_{message_name_snake_cased}_http_bytes("
                               f"{message_name_snake_cased}_id: "
                               f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Delete route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_http\n'
            output_str += (f"    return_val = await _underlying_delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id, generic_callable, return_obj_copy)\n")
            output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += "    return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"
        else:
            output_str = f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += (f"async def underlying_delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {id_field_type}, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True)")
            else:
                output_str += (f"async def underlying_delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True)")
            output_str += " -> DefaultPydanticWebResponse | bool:\n"
            output_str += f'    """\n'
            output_str += f'    Delete route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_http\n'
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                               f"{message_name_snake_cased}_id, has_links={msg_has_links})\n"
            output_str += " " * indent_count + f"    await callback_class.delete_{message_name_snake_cased}_pre(" \
                                               f"stored_{message_name_snake_cased}_obj)\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter | FastapiHttpRoutesFileHandler.aggregation_type_both:
                    err_str = "Filter Aggregation type is not supported in Delete operations, " \
                              f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message.proto.name}BaseModel, {message_name_snake_cased}_id, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message.proto.name}BaseModel, {message_name_snake_cased}_id, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + f"    await callback_class.delete_{message_name_snake_cased}_post(" \
                                               f"delete_web_resp)\n"
            output_str += " " * indent_count + f"    return delete_web_resp\n"
        output_str += "\n"
        return output_str

    def handle_DELETE_gen(self, **kwargs) -> str:
        message, _, id_field_type, _, model_type = self._unpack_kwargs_with_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_DELETE_gen(**kwargs)
        output_str += "\n"
        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            output_str += f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                          '{' + f'{message_name_snake_cased}_id' + '}' + \
                          f'", status_code=200)\n'
            if id_field_type is not None:
                output_str += (f"async def delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {id_field_type}, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                               f"return_obj_copy: bool | None = True):\n")
        else:
            output_str += f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                          '{' + f'{message_name_snake_cased}_id' + '}' + \
                          f'", response_model=DefaultPydanticWebResponse | bool, status_code=200)\n'
            if id_field_type is not None:
                output_str += (f"async def delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {id_field_type}, "
                               f"return_obj_copy: bool | None = True) -> DefaultPydanticWebResponse | bool:\n")
            else:
                output_str += (f"async def delete_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                               f"return_obj_copy: bool | None = True) -> DefaultPydanticWebResponse | bool:\n")
        output_str += self._add_view_check_code_in_route()
        output_str += f"    try:\n"
        if model_type == ModelType.Msgspec:
            output_str += f"        return await underlying_delete_{message_name_snake_cased}_http_bytes(" \
                          f"{message_name_snake_cased}_id, return_obj_copy=return_obj_copy)\n"
        else:
            output_str += f"        return await underlying_delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id, return_obj_copy=return_obj_copy)\n"
        output_str += f"    except Exception as e:\n"
        output_str += (f"        logging.exception(f'delete_{message_name_snake_cased}_http failed in "
                       "client call with exception: {e}')\n")
        output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_delete_all_gen(self, message: protogen.Message, aggregation_type,
                                                         shared_lock_list) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_delete_all_{message_name_snake_cased}_http("
                      f"generic_callable: Callable[Any, Any] | None = None, "
                      f"return_obj_copy: bool | None = True):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + f"    await callback_class.delete_all_{message_name_snake_cased}_pre()\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter | (
            FastapiHttpRoutesFileHandler.aggregation_type_both) | FastapiHttpRoutesFileHandler.aggregation_type_update:
                err_str = "Filter Aggregation type is not supported in Delete All operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " " * indent_count + \
                              f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message.proto.name}BaseModel)\n"
        output_str += " " * indent_count + f"    await callback_class.delete_all_{message_name_snake_cased}_post(" \
                                           f"delete_web_resp)\n"
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return delete_web_resp\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n"
        output_str += "\n\n"
        return output_str


    def handle_underlying_DELETE_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list, model_type = (
            self._unpack_kwargs_without_id_field_type(**kwargs))
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Msgspec:
            output_str = self._handle_msgspec_common_underlying_delete_all_gen(message, aggregation_type,
                                                                               shared_lock_list)
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_delete_all_{message_name_snake_cased}_http("
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Delete All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_all_http\n'
            output_str += (f"    return_val = await _underlying_delete_all_{message_name_snake_cased}_http("
                           f"generic_callable, return_obj_copy)\n")
            output_str += f"    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_delete_all_{message_name_snake_cased}_http_bytes("
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Delete All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_all_http\n'
            output_str += (f"    return_val = await _underlying_delete_all_{message_name_snake_cased}_http("
                           f"generic_callable, return_obj_copy)\n")
            output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"    return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"

        else:
            output_str = f"@perf_benchmark\n"
            if model_type == ModelType.Dataclass:
                output_str += (f"async def underlying_delete_all_{message_name_snake_cased}_http("
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_delete_all_{message_name_snake_cased}_http("
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True) -> DefaultPydanticWebResponse | bool:\n")
            output_str += f'    """\n'
            output_str += f'    Delete All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_all_http\n'
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + f"    await callback_class.delete_all_{message_name_snake_cased}_pre()\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter | (
                        FastapiHttpRoutesFileHandler.aggregation_type_both) | FastapiHttpRoutesFileHandler.aggregation_type_update:
                    err_str = "Filter Aggregation type is not supported in Delete All operations, " \
                              f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                case other:
                    if model_type == ModelType.Msgspec:
                        output_str += " " * indent_count + \
                                      f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message.proto.name}BaseModel)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message.proto.name}BaseModel, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + f"    await callback_class.delete_all_{message_name_snake_cased}_post(" \
                                               f"delete_web_resp)\n"
            output_str += " " * indent_count + f"    return delete_web_resp\n"
        output_str += "\n"
        return output_str

    def handle_DELETE_all_gen(self, **kwargs) -> str:
        message, _, _, model_type = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_DELETE_all_gen(**kwargs)
        output_str += "\n"
        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            output_str += (f'@{self.api_router_app_name}.delete("/delete-all-{message_name_snake_cased}/", '
                           f'status_code=200)\n')
            output_str += (f"async def delete_{message_name_snake_cased}_all_http(return_obj_copy: bool | None = True"
                           f"):\n")
        else:
            output_str += (f'@{self.api_router_app_name}.delete("/delete-all-{message_name_snake_cased}/", '
                           f'response_model=DefaultPydanticWebResponse | bool, status_code=200)\n')
            output_str += (f"async def delete_{message_name_snake_cased}_all_http(return_obj_copy: bool | None = True"
                           f") -> DefaultPydanticWebResponse | bool:\n")
        output_str += self._add_view_check_code_in_route()
        output_str += f"    try:\n"
        if model_type == ModelType.Msgspec:
            output_str += (f"        return await underlying_delete_all_{message_name_snake_cased}_http_bytes("
                           f"return_obj_copy=return_obj_copy)\n")
        else:
            output_str += (f"        return await underlying_delete_all_{message_name_snake_cased}_http("
                           f"return_obj_copy=return_obj_copy)\n")
        output_str += f"    except Exception as e:\n"
        output_str += (f"        logging.exception(f'delete_{message_name_snake_cased}_all_http failed in "
                       "client call with exception: {e}')\n")
        output_str += f"        raise e\n"
        return output_str

    def _handle_msgspec_common_underlying_delete_by_id_list_gen(self, message: protogen.Message, aggregation_type,
                                                                msg_has_links, shared_lock_list, id_field_type) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = ""
        if id_field_type is not None:
            output_str += (f"async def _underlying_delete_by_id_list_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id_list: List[{id_field_type}], "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
        else:
            output_str += (f"async def _underlying_delete_by_id_list_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id_list: List["
                           f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}], "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + f"    await callback_class.delete_by_id_list_{message_name_snake_cased}_pre(" \
                                           f"{message_name_snake_cased}_id_list)\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter | FastapiHttpRoutesFileHandler.aggregation_type_both:
                err_str = "Filter Aggregation type is not supported in Delete operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message.proto.name}BaseModel, {message_name_snake_cased}_id_list, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links})\n")
            case other:
                output_str += " " * indent_count + \
                              f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message.proto.name}BaseModel, {message_name_snake_cased}_id_list, " \
                              f"has_links={msg_has_links})\n"
        output_str += " " * indent_count + f"    await callback_class.delete_by_id_list_{message_name_snake_cased}_post(" \
                                           f"delete_web_resp)\n"
        output_str += " " * indent_count + f"    if return_obj_copy:\n"
        output_str += " " * indent_count + f"        return delete_web_resp\n"
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        return True\n\n\n"
        return output_str

    def handle_underlying_DELETE_by_id_list_gen(self, **kwargs) -> str:
        message, aggregation_type, id_field_type, shared_lock_list, model_type = (
            self._unpack_kwargs_with_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type == ModelType.Msgspec:
            output_str = self._handle_msgspec_common_underlying_delete_by_id_list_gen(message, aggregation_type,
                                                                                      msg_has_links,
                                                                                      shared_lock_list, id_field_type)
            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += (f"async def underlying_delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list: List[{id_field_type}], "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list: List["
                               f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}], "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Delete by id list route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_by_id_list_http\n'
            output_str += (f"    return_val = await _underlying_delete_by_id_list_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id_list, generic_callable, return_obj_copy)\n")
            output_str += "    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += (f"async def underlying_delete_by_id_list_{message_name_snake_cased}_http_bytes("
                               f"{message_name_snake_cased}_id_list_bytes: bytes, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def underlying_delete_by_id_list_{message_name_snake_cased}_http_bytes("
                               f"{message_name_snake_cased}_id_list_bytes: bytes, "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True):\n")
            output_str += f'    """\n'
            output_str += f'    Delete by id list route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_by_id_list_http\n'
            output_str += (f'    {message_name_snake_cased}_id_list = orjson.loads('
                           f'{message_name_snake_cased}_id_list_bytes)\n')
            output_str += (f"    return_val = await _underlying_delete_by_id_list_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id_list, generic_callable, return_obj_copy)\n")
            output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += "    return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n"
        else:
            output_str = f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += (f"async def underlying_delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list: List[{id_field_type}], "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True)")
            else:
                output_str += (f"async def underlying_delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list: List["
                               f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}], "
                               f"generic_callable: Callable[[...], Any] | None = None, "
                               f"return_obj_copy: bool | None = True)")
            output_str += " -> DefaultPydanticWebResponse | bool:\n"
            output_str += f'    """\n'
            output_str += f'    Delete by id list route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_delete_by_id_list_http\n'
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_obj_list = await generic_read_http(" \
                                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                               f"{message_name_snake_cased}_id_list, has_links={msg_has_links})\n"
            output_str += " " * indent_count + f"    await callback_class.delete_by_id_list_{message_name_snake_cased}_pre(" \
                                               f"stored_{message_name_snake_cased}_obj_list)\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter | FastapiHttpRoutesFileHandler.aggregation_type_both:
                    err_str = "Filter Aggregation type is not supported in Delete operations, " \
                              f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                case FastapiHttpRoutesFileHandler.aggregation_type_update:
                    update_agg_pipeline_var_name = \
                        self.get_simple_option_value_from_proto(message,
                                                                FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message.proto.name}BaseModel, {message_name_snake_cased}_id_list, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                    else:
                        output_str += " " * indent_count + \
                                      (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                                       f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                       f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj_list, "
                                       f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                                       f"return_obj_copy=return_obj_copy)\n")
                case other:
                    if model_type == ModelType.Dataclass:
                        output_str += " " * indent_count + \
                                      f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message.proto.name}BaseModel, {message_name_snake_cased}_id_list, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
                    else:
                        output_str += " " * indent_count + \
                                      f"    delete_web_resp = await generic_callable({message.proto.name}, " \
                                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                      f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj_list, " \
                                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            output_str += " " * indent_count + f"    await callback_class.delete_by_id_list_{message_name_snake_cased}_post(" \
                                               f"delete_web_resp)\n"
            output_str += " " * indent_count + f"    return delete_web_resp\n"
        output_str += "\n"
        return output_str

    def handle_DELETE_by_id_list_gen(self, **kwargs) -> str:
        message, _, id_field_type, _, model_type = self._unpack_kwargs_with_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_DELETE_by_id_list_gen(**kwargs)
        output_str += "\n"
        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            output_str += (f'@{self.api_router_app_name}.delete("/delete-by-id-list-{message_name_snake_cased}", '
                           f'status_code=200)\n')
            if id_field_type is not None:
                output_str += (f"async def delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list_req_body: Request, "
                               f"return_obj_copy: bool | None = True):\n")
            else:
                output_str += (f"async def delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list_req_body: Request, "
                               f"return_obj_copy: bool | None = True):\n")
        else:
            output_str += f'@{self.api_router_app_name}.delete("/delete-by-id-list-{message_name_snake_cased}/' + \
                          '{' + f'{message_name_snake_cased}_id_list' + '}' + \
                          f'", response_model=DefaultPydanticWebResponse | bool, status_code=200)\n'
            if id_field_type is not None:
                output_str += (f"async def delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list: List[{id_field_type}], "
                               f"return_obj_copy: bool | None = True) -> DefaultPydanticWebResponse | bool:\n")
            else:
                output_str += (f"async def delete_by_id_list_{message_name_snake_cased}_http("
                               f"{message_name_snake_cased}_id_list: List["
                               f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}], "
                               f"return_obj_copy: bool | None = True) -> DefaultPydanticWebResponse | bool:\n")
        output_str += self._add_view_check_code_in_route()
        output_str += f"    try:\n"
        if model_type == ModelType.Msgspec:
            output_str += (f"        {message_name_snake_cased}_id_list_bytes = "
                           f"await {message_name_snake_cased}_id_list_req_body.body()\n")
            output_str += f"        return await underlying_delete_by_id_list_{message_name_snake_cased}_http_bytes(" \
                          f"{message_name_snake_cased}_id_list_bytes, return_obj_copy=return_obj_copy)\n"
        else:
            output_str += f"        return await underlying_delete_by_id_list_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id_list, return_obj_copy=return_obj_copy)\n"
        output_str += f"    except Exception as e:\n"
        output_str += (f"        logging.exception(f'delete_by_id_list_{message_name_snake_cased}_http failed in "
                       "client call with exception: {e}')\n")
        output_str += f"        raise e\n"
        return output_str

    def _get_filter_tuple_str(self, index_fields: List[protogen.Field]) -> str:
        filter_tuples_str = ""
        for field in index_fields:
            filter_tuples_str += f"('{field.proto.name}', [{field.proto.name}])"
            if field != index_fields[-1]:
                filter_tuples_str += ", "
        return filter_tuples_str

    def handle_underlying_index_req_gen(self, message: protogen.Message,
                                        shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_index)]

        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])
        output_str = "@perf_benchmark\n"
        output_str += f"async def underlying_get_{message_name_snake_cased}_from_index_fields_http({field_params}, " \
                      f"filter_agg_pipeline: Any = None, generic_callable: " \
                      f"Callable[[...], Any] | None = None) -> List[{message.proto.name}]:\n"
        output_str += f'    """ Index route of {message.proto.name} """\n'
        output_str += f'    if generic_callable is None:\n'
        output_str += f'        generic_callable = generic_read_http\n'
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + f"    await callback_class.index_of_{message_name_snake_cased}_pre()\n"
        filter_configs_var_name = self._get_filter_configs_var_name(message, None)
        if filter_configs_var_name:
            output_str += " " * indent_count + f"    indexed_filter = copy.deepcopy({filter_configs_var_name})\n"
            output_str += " " * indent_count + \
                          f"    indexed_filter['match'] = [{self._get_filter_tuple_str(index_fields)}]\n"
        else:
            output_str += " " * indent_count + "    indexed_filter = {'match': " + \
                          f"[{self._get_filter_tuple_str(index_fields)}]" + "}\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"indexed_filter, has_links={msg_has_links})\n"
        output_str += " " * indent_count + f"    await callback_class.index_of_{message_name_snake_cased}_post(" \
                                           f"{message_name_snake_cased}_obj)\n"
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_obj\n\n"
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, shared_lock_list: List[str] | None = None,
                             model_type: ModelType = ModelType.Msgspec) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_index_req_gen(message, shared_lock_list)
        output_str += "\n"
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_index)]

        field_query = "/".join(["{" + f"{field.proto.name}" + "}" for field in index_fields])
        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])

        if model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-index-fields/' + \
                          f'{field_query}' + f'", status_code=200)\n'
            output_str += f"async def get_{message_name_snake_cased}_from_index_fields_http({field_params}):\n"
        else:
            output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-index-fields/' + \
                          f'{field_query}' + f'", response_model=List[{message.proto.name}], status_code=200)\n'
            output_str += f"async def get_{message_name_snake_cased}_from_index_fields_http({field_params}) " \
                          f"-> List[{message.proto.name}]:\n"
        field_params = ", ".join([f"{field.proto.name}" for field in index_fields])
        output_str += \
            f"    return await underlying_get_{message_name_snake_cased}_from_index_fields_http({field_params})\n\n\n"
        return output_str

    def _handle_msgspec_common_underlying_get_gen(self, message: protogen.Message, aggregation_type, msg_has_links,
                                                  shared_lock_list, id_field_type) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if id_field_type is not None:
            output_str = f"async def _underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id: {id_field_type}, filter_agg_pipeline: Any = None, " \
                          f"generic_callable: Callable[Any, Any] | None = None):\n"
        else:
            output_str = f"async def _underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, " \
                          f"filter_agg_pipeline: Any = None, generic_callable: " \
                          f"Callable[[...], Any] | None = None):\n"
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + \
                      f"    await callback_class.read_by_id_{message_name_snake_cased}_pre({message_name_snake_cased}_id)\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        return_obj = f"{message_name_snake_cased}_json"
        output_str += " " * indent_count + \
                      f"        {return_obj} = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name_snake_cased}_id, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        {return_obj} = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_id, " \
                              f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_id')}, " \
                              f"has_links={msg_has_links})\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update | FastapiHttpRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in read by id operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " " * indent_count + \
                              f"        {return_obj} = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_id, has_links={msg_has_links})\n"
        output_str += " " * indent_count + (f"    {message_name_snake_cased}_msgspec_obj = "
                                            f"{message.proto.name}.from_dict({message_name_snake_cased}_json)\n")
        output_str += " " * indent_count + (f"    await callback_class.read_by_id_{message_name_snake_cased}_post("
                                            f"{message_name_snake_cased}_msgspec_obj)\n")
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_msgspec_obj\n\n\n"
        return output_str

    def handle_underlying_GET_gen(self, **kwargs) -> str:
        message, aggregation_type, id_field_type, shared_lock_list, model_type = (
            self._unpack_kwargs_with_id_field_type(**kwargs))
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)

        output_str = ""
        if model_type == ModelType.Msgspec:
            output_str += self._handle_msgspec_common_underlying_get_gen(message, aggregation_type, msg_has_links,
                                                                         shared_lock_list, id_field_type)
            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http(" \
                              f"{message_name_snake_cased}_id: {id_field_type}, filter_agg_pipeline: Any = None, " \
                              f"generic_callable: Callable[[...], Any] | None = None):\n"
            else:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http(" \
                              f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, " \
                              f"filter_agg_pipeline: Any = None, generic_callable: " \
                              f"Callable[[...], Any] | None = None):\n"
            output_str += f'    """\n'
            output_str += f'    Read by id route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_by_id_http\n'
            output_str += f"    return_val = await _underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id, filter_agg_pipeline, generic_callable)\n"
            output_str += f"    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http_json_dict(" \
                              f"{message_name_snake_cased}_id: {id_field_type}, filter_agg_pipeline: Any = None, " \
                              f"generic_callable: Callable[[...], Any] | None = None):\n"
            else:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http_json_dict(" \
                              f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, " \
                              f"filter_agg_pipeline: Any = None, generic_callable: " \
                              f"Callable[[...], Any] | None = None):\n"
            output_str += f'    """\n'
            output_str += f'    Read by id route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_by_id_http\n'
            output_str += f"    return_val = await _underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id, filter_agg_pipeline, generic_callable)\n"
            output_str += f"    return_val = msgspec.to_builtins(return_val, builtin_types=[DateTime])\n"
            output_str += f"    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http_bytes(" \
                              f"{message_name_snake_cased}_id: {id_field_type}, filter_agg_pipeline: Any = None, " \
                              f"generic_callable: Callable[[...], Any] | None = None):\n"
            else:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http_bytes(" \
                              f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, " \
                              f"filter_agg_pipeline: Any = None, generic_callable: " \
                              f"Callable[[...], Any] | None = None):\n"
            output_str += f'    """\n'
            output_str += f'    Read by id route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_by_id_http\n'
            output_str += f"    return_val = await _underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id, filter_agg_pipeline, generic_callable)\n"
            output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"    return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n\n"
        else:
            output_str += f"@perf_benchmark\n"
            if id_field_type is not None:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http(" \
                              f"{message_name_snake_cased}_id: {id_field_type}, filter_agg_pipeline: Any = None, " \
                              f"generic_callable: Callable[[...], Any] | None = None)"
            else:
                output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http(" \
                              f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, " \
                              f"filter_agg_pipeline: Any = None, generic_callable: " \
                              f"Callable[[...], Any] | None = None)"
            if model_type == ModelType.Dataclass:
                output_str += ":\n"
            else:
                output_str += f" -> {message.proto.name}:\n"
            output_str += f'    """\n'
            output_str += f'    Read by id route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_by_id_http\n'
            # else not required: avoiding if method desc not provided
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + \
                          f"    await callback_class.read_by_id_{message_name_snake_cased}_pre({message_name_snake_cased}_id)\n"
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            if model_type == ModelType.Dataclass:
                return_obj = f"{message_name_snake_cased}_json"
            else:
                return_obj = f"{message_name_snake_cased}_obj"
            output_str += " " * indent_count + \
                          f"        {return_obj} = await generic_callable({message.proto.name}, " \
                          f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                          f"{message_name_snake_cased}_id, filter_agg_pipeline, has_links={msg_has_links})\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    output_str += " " * indent_count + \
                                  f"        {return_obj} = await generic_callable(" \
                                  f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                  f"{message_name_snake_cased}_id, " \
                                  f"{self._get_filter_configs_var_name(message, f'{message_name_snake_cased}_id')}, " \
                                  f"has_links={msg_has_links})\n"
                case FastapiHttpRoutesFileHandler.aggregation_type_update | FastapiHttpRoutesFileHandler.aggregation_type_both:
                    err_str = "Update Aggregation type is not supported in read by id operations, " \
                              f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                case other:
                    output_str += " " * indent_count + \
                                  f"        {return_obj} = await generic_callable(" \
                                  f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                  f"{message_name_snake_cased}_id, has_links={msg_has_links})\n"

            output_str += " " * indent_count + f"    await callback_class.read_by_id_{message_name_snake_cased}_post({return_obj})\n"
            output_str += " " * indent_count + f"    return {return_obj}\n"
            output_str += "\n"
        return output_str

    def handle_GET_gen(self, **kwargs) -> str:
        message, _, id_field_type, _, model_type = self._unpack_kwargs_with_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_GET_gen(**kwargs)
        output_str += "\n"
        if model_type == ModelType.Dataclass or model_type == ModelType.Msgspec:
            output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                          f'{message_name_snake_cased}_id' + '}' + f'", status_code=200)\n'
        else:
            output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                          f'{message_name_snake_cased}_id' + '}' + \
                          f'", response_model={message.proto.name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{id_field_type})"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{FastapiHttpRoutesFileHandler.default_id_type_var_name})"
        if model_type == ModelType.Dataclass or model_type == ModelType.Msgspec:
            output_str += ":\n"
        else:
            output_str += f" -> {message.proto.name}:\n"
        output_str += f"    try:\n"
        if model_type == ModelType.Msgspec:
            output_str += \
                f"        return await underlying_read_{message_name_snake_cased}_by_id_http_bytes({message_name_snake_cased}_id)\n"
        else:
            output_str += \
                f"        return await underlying_read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id)\n"
        output_str += f"    except Exception as e:\n"
        output_str += (f"        logging.exception(f'read_{message_name_snake_cased}_by_id_http failed in "
                       "client call with exception: {e}')\n")
        output_str += f"        raise e\n"

        return output_str

    def _handle_msgspec_common_underlying_get_all_gen(self, message: protogen.Message, aggregation_type, msg_has_links,
                                                      shared_lock_list) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = (f"async def _underlying_read_{message_name_snake_cased}_http("
                      f"filter_agg_pipeline: Any = None, generic_callable: "
                      f"Callable[Any, Any] | None = None, projection_model=None, "
                      f"projection_filter: Dict | None = None, limit_obj_count: int | None = None):\n")
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        return_obj_str = "json_list"
        output_str += mutex_handling_str
        output_str += " " * indent_count + f"    await callback_class.read_all_{message_name_snake_cased}_pre()\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {return_obj_str} = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, filter_agg_pipeline, " \
                      f"has_links={msg_has_links}, projection_model=projection_model)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        {return_obj_str} = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{self._get_filter_configs_var_name(message, None, put_limit=True)}, " \
                              f"has_links={msg_has_links})\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update | FastapiHttpRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in real all operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " " * indent_count + \
                              f"        limit_filter_agg: Dict[str, Any] | None = None\n"
                output_str += " " * indent_count + \
                              f"        if limit_obj_count is not None:\n"
                output_str += " " * indent_count + \
                              f"            # if underlying is called with limit_obj_count directly\n"
                output_str += " " * indent_count + \
                              "            limit_filter_agg = {'agg': get_limited_objs(limit_obj_count)}\n"
                output_str += " " * indent_count + \
                              f"        {return_obj_str} = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"limit_filter_agg, has_links={msg_has_links})\n"
        output_str += " " * indent_count + f"    if json_list:\n"
        output_str += " " * indent_count + f"        if projection_model:\n"
        output_str += " " * indent_count + (f"            {message_name_snake_cased}_msgspec_obj_list = "
                                            f"projection_model.from_dict({return_obj_str})\n")
        output_str += " " * indent_count + f"        else:\n"
        output_str += " " * indent_count + (f"            {message_name_snake_cased}_msgspec_obj_list = "
                                            f"{message.proto.name}.from_dict_list({return_obj_str})\n")
        output_str += " " * indent_count + f"    else:\n"
        output_str += " " * indent_count + f"        {message_name_snake_cased}_msgspec_obj_list = []\n"
        output_str += " " * indent_count + (f"    await callback_class.read_all_{message_name_snake_cased}_post("
                                            f"{message_name_snake_cased}_msgspec_obj_list)\n")
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_msgspec_obj_list\n\n\n"
        return output_str

    def handle_underlying_GET_ALL_gen(self, message: protogen.Message, aggregation_type: str,
                                      shared_lock_list: List[str] | None = None,
                                      model_type: ModelType = ModelType.Beanie) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)

        if model_type == ModelType.Msgspec:
            output_str = self._handle_msgspec_common_underlying_get_all_gen(message, aggregation_type, msg_has_links,
                                                                            shared_lock_list)
            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_read_{message_name_snake_cased}_http("
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, projection_model=None, "
                           f"projection_filter: Dict | None = None, limit_obj_count: int | None = None"
                           f"):\n")
            output_str += f'    """\n'
            output_str += f'    Get All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_http\n'
            output_str += (f"    return_val = await _underlying_read_{message_name_snake_cased}_http("
                          f"filter_agg_pipeline, generic_callable, projection_model, projection_filter, "
                          f"limit_obj_count)\n")
            output_str += f"    return return_val\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_read_{message_name_snake_cased}_http_json_dict("
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, projection_model=None, "
                           f"projection_filter: Dict | None = None, limit_obj_count: int | None = None"
                           f"):\n")
            output_str += f'    """\n'
            output_str += f'    Get All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_http\n'
            output_str += (f"    return_val = await _underlying_read_{message_name_snake_cased}_http("
                          f"filter_agg_pipeline, generic_callable, projection_model, projection_filter, "
                          f"limit_obj_count)\n")
            output_str += f"    return_obj_dict = msgspec.to_builtins(return_val, builtin_types=[DateTime])\n"
            output_str += f"    return return_obj_dict\n\n\n"

            output_str += f"@perf_benchmark\n"
            output_str += (f"async def underlying_read_{message_name_snake_cased}_http_bytes("
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, projection_model=None, "
                           f"projection_filter: Dict | None = None, limit_obj_count: int | None = None"
                           f"):\n")
            output_str += f'    """\n'
            output_str += f'    Get All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_http\n'
            output_str += (f"    return_val = await _underlying_read_{message_name_snake_cased}_http("
                           f"filter_agg_pipeline, generic_callable, projection_model, projection_filter, "
                           f"limit_obj_count)\n")
            output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"    return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n\n"
        else:
            output_str = f"@perf_benchmark\n"
            output_str += (f"async def underlying_read_{message_name_snake_cased}_http("
                           f"filter_agg_pipeline: Any = None, generic_callable: "
                           f"Callable[[...], Any] | None = None, projection_model=None, "
                           f"projection_filter: Dict | None = None, limit_obj_count: int | None = None"
                           f")")
            if model_type == ModelType.Dataclass:
                output_str += ":\n"
                return_obj_str = "json_list"
            else:
                output_str += f" -> List[{message.proto.name}]:\n"
                return_obj_str = "obj_list"
            output_str += f'    """\n'
            output_str += f'    Get All route for {message.proto.name}\n'
            output_str += f'    """\n'
            output_str += f'    if generic_callable is None:\n'
            output_str += f'        generic_callable = generic_read_http\n'
            mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

            output_str += mutex_handling_str
            output_str += " " * indent_count + f"    await callback_class.read_all_{message_name_snake_cased}_pre()\n"
            output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
            output_str += " " * indent_count + \
                          f"        {return_obj_str} = await generic_callable({message.proto.name}, " \
                          f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, filter_agg_pipeline, " \
                          f"has_links={msg_has_links}, projection_model=projection_model)\n"
            output_str += " " * indent_count + "    else:\n"
            match aggregation_type:
                case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                    output_str += " " * indent_count + \
                                  f"        {return_obj_str} = await generic_callable({message.proto.name}, " \
                                  f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                  f"{self._get_filter_configs_var_name(message, None, put_limit=True)}, " \
                                  f"has_links={msg_has_links})\n"
                case FastapiHttpRoutesFileHandler.aggregation_type_update | FastapiHttpRoutesFileHandler.aggregation_type_both:
                    err_str = "Update Aggregation type is not supported in real all operations, " \
                              f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                case other:
                    output_str += " " * indent_count + \
                                  f"        limit_filter_agg: Dict[str, Any] | None = None\n"
                    output_str += " " * indent_count + \
                                  f"        if limit_obj_count is not None:\n"
                    output_str += " " * indent_count + \
                                  f"            # if underlying is called with limit_obj_count directly\n"
                    output_str += " " * indent_count + \
                                  "            limit_filter_agg = {'agg': get_limited_objs(limit_obj_count)}\n"
                    output_str += " " * indent_count + \
                                  f"        {return_obj_str} = await generic_callable({message.proto.name}, " \
                                  f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                                  f"limit_filter_agg, has_links={msg_has_links})\n"
            output_str += " " * indent_count + f"    await callback_class.read_all_{message_name_snake_cased}_post({return_obj_str})\n"
            output_str += " " * indent_count + f"    return {return_obj_str}\n\n"
        return output_str

    def handle_GET_ALL_gen(self, message: protogen.Message, aggregation_type: str,
                           shared_lock_list: List[str] | None = None, model_type: ModelType = ModelType.Beanie) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_GET_ALL_gen(message, aggregation_type, shared_lock_list, model_type)
        output_str += "\n"
        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            output_str += (f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}'
                           f'", status_code=200)\n')
            output_str += (f"async def read_{message_name_snake_cased}_http(limit_obj_count: int | None = None"
                           f"):\n")
        else:
            output_str += (f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}'
                           f'", response_model=List[{message.proto.name}], status_code=200)\n')
            output_str += (f"async def read_{message_name_snake_cased}_http(limit_obj_count: int | None = None"
                           f") -> List[{message.proto.name}]:\n")
        additional_agg_option_val_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     FastapiHttpRoutesFileHandler.flux_msg_main_crud_operations_agg)

        output_str += f"    try:\n"
        override_default_get_all_limit = additional_agg_option_val_dict.get("override_get_all_limit_handling")
        if not override_default_get_all_limit:
            output_str += f"        limit_filter_agg: Dict[str, Any] | None = None\n"
            output_str += f"        if limit_obj_count is not None:\n"
            output_str += "            limit_filter_agg = {'agg': get_limited_objs(limit_obj_count)}\n"
            if model_type == ModelType.Msgspec:
                output_str += (f"        return await underlying_read_{message_name_snake_cased}_http_bytes("
                               f"limit_filter_agg)\n")
            else:
                output_str += f"        return await underlying_read_{message_name_snake_cased}_http(limit_filter_agg)\n"
        else:
            if model_type == ModelType.Msgspec:
                output_str += (f"        return await underlying_read_{message_name_snake_cased}_http_bytes("
                               f"limit_obj_count=limit_obj_count)\n")
            else:
                output_str += (f"        return await underlying_read_{message_name_snake_cased}_http("
                               f"limit_obj_count=limit_obj_count)\n")
        output_str += f"    except Exception as e:\n"
        output_str += (f"        logging.exception(f'read_{message_name_snake_cased}_http failed in "
                       "client call with exception: {e}')\n")
        output_str += f"        raise e\n\n\n"
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
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                if not (self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name) or
                        self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_main_crud_operations_agg)) and \
                        self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_nested_fld_val_filter_param):
                    err_str += f"{aggregation_type} but not has " \
                               f"both {FastapiHttpRoutesFileHandler.flux_msg_nested_fld_val_filter_param} and " \
                               f"{FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name} options set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                if not (self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_nested_fld_val_filter_param)
                        or
                        self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_main_crud_operations_agg)):
                    err_str += f"{aggregation_type} but not has " \
                               f"{FastapiHttpRoutesFileHandler.flux_msg_nested_fld_val_filter_param} option set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                if not self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name):
                    err_str += f"{aggregation_type} but not has " \
                               f"{FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name} option set, " \
                               f"Please check if json_root fields are set to specified if no " \
                               f"{FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name} option is set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiHttpRoutesFileHandler.aggregation_type_unspecified:
                pass
            case other:
                err_str = f"Unsupported option field {other} in json_root option"
                logging.exception(err_str)
                raise Exception(err_str)
        return aggregation_type

    def _handle_routes_methods(self, message: protogen.Message, model_type: ModelType = ModelType.Beanie) -> str:

        if model_type == ModelType.Dataclass:
            msg_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            output_str = (f"{msg_name_snake_cased}_json_n_dataclass_handler = "
                          f"JsonNDataClassHandler({message.proto.name})\n\n")
        else:
            output_str = ""
        crud_field_name_to_method_call_dict = {
            FastapiHttpRoutesFileHandler.flux_json_root_create_field: self.handle_POST_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_create_all_field: self.handle_POST_all_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_read_field: self.handle_GET_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_update_field: self.handle_PUT_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_update_all_field: self.handle_PUT_all_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_patch_field: self.handle_PATCH_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_patch_all_field: self.handle_PATCH_all_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_delete_field: self.handle_DELETE_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_delete_all_field: self.handle_DELETE_all_gen,
            FastapiHttpRoutesFileHandler.flux_json_root_delete_by_id_list_field: self.handle_DELETE_by_id_list_gen
        }

        if self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root):
            option_val_dict = self.get_complex_option_value_from_proto(message, FastapiHttpRoutesFileHandler.flux_msg_json_root)
        else:
            option_val_dict = self.get_complex_option_value_from_proto(message,
                                                                       FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series)

        shared_mutex_list = self._get_list_of_shared_lock_for_message(message)

        if (aggregation_type := option_val_dict.get(FastapiHttpRoutesFileHandler.flux_json_root_read_field)) is not None:
            output_str += self.handle_GET_ALL_gen(message, aggregation_type.strip(),
                                                  shared_mutex_list, model_type)
        # else not required: avoiding find_all route for this message if read_field of json_root option is not set

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_val_dict:
                aggregation_type: str = self._check_agg_info_availability(option_val_dict[crud_option_field_name].strip(),
                                                                          crud_option_field_name,
                                                                          message)
                output_str += crud_operation_method(message=message, aggregation_type=aggregation_type,
                                                    id_field_type=id_field_type, shared_mutex_list=shared_mutex_list,
                                                    model_type=model_type, json_root_option_val=option_val_dict)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_index):
                output_str += self.handle_index_req_gen(message, shared_mutex_list)
                break
            # else not required: Avoiding field if index option is not enabled

        if id_field_type == "int":
            output_str += self._handle_get_max_id_query_generation(message, model_type)

        return output_str

    def _handle_http_query_str(self, message: protogen.Message, query_name: str, query_params_str: str,
                               query_params_with_type_str: str, route_type: str | None = None,
                               return_type_str: str | None = None, model_type: ModelType = ModelType.Beanie) -> str:
        # finding datetime params to get object created back
        query_params_with_type_str_split = query_params_with_type_str.split(", ")
        query_param_having_dt = []
        for query_params_with_type_str_ in query_params_with_type_str_split:
            if "DateTime" in query_params_with_type_str_:
                query_param_having_dt.append(query_params_with_type_str_.split(":")[0])

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if return_type_str is None:
            return_type_str = message.proto.name
        if route_type is None or route_type == FastapiHttpRoutesFileHandler.flux_json_query_route_get_type_field_val:
            output_str = f"@perf_benchmark\n"
            if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
                output_str += f"async def underlying_{query_name}_query_http({query_params_with_type_str}):\n"
            else:
                output_str += f"async def underlying_{query_name}_query_http({query_params_with_type_str}) -> " \
                              f"List[{return_type_str}]:\n"
            if query_params_str:
                output_str += f"    {message_name_snake_cased}_obj = await " \
                              f"callback_class.{query_name}_query_pre({message.proto.name}, {query_params_str})\n"
                output_str += f"    {message_name_snake_cased}_obj = await " \
                              f"callback_class.{query_name}_query_post({message_name_snake_cased}_obj)\n"
            else:
                output_str += f"    {message_name_snake_cased}_obj = await callback_class.{query_name}_" \
                              f"query_pre({message.proto.name})\n"
                output_str += f"    await callback_class.{query_name}_query_post(" \
                              f"{message_name_snake_cased}_obj)\n"
            output_str += f"    return {message_name_snake_cased}_obj\n\n\n"

            if model_type == ModelType.Msgspec:
                output_str += f"async def underlying_{query_name}_query_http_bytes({query_params_with_type_str}):\n"
                output_str += f"    return_val = await underlying_{query_name}_query_http({query_params_str})\n"
                output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
                output_str += f"    return CustomFastapiResponse(content=return_obj_bytes, status_code=200)\n\n"
            # else not required: if model_type is not Msgspec then no bytes type underlying variant is created

            # making Datetime type to str as it is not compatible in parsing with fastapi directly - will make
            # object back from str once receive value
            if "pendulum.DateTime" in query_params_with_type_str:
                query_params_with_type_str = query_params_with_type_str.replace("pendulum.DateTime", "str")
            if "DateTime" in query_params_with_type_str:
                query_params_with_type_str = query_params_with_type_str.replace("DateTime", "str")

            if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
                output_str += f'@{self.api_router_app_name}.get("/query-{query_name}' + \
                              f'", status_code=200)\n'
                output_str += f"async def {query_name}_query_http({query_params_with_type_str}):\n"
            else:
                output_str += f'@{self.api_router_app_name}.get("/query-{query_name}' + \
                              f'", response_model=List[{return_type_str}], status_code=200)\n'
                output_str += f"async def {query_name}_query_http({query_params_with_type_str}) -> " \
                              f"List[{return_type_str}]:\n"
            output_str += f'    """\n'
            output_str += f'    Get Query of {message.proto.name} with aggregate - {query_name}\n'
            output_str += f'    """\n'
            if query_param_having_dt:
                for param_having_dt in query_param_having_dt:
                    output_str += f'    if {param_having_dt} is not None:\n'
                    output_str += f'        {param_having_dt} = pendulum.parse({param_having_dt})\n'
            if model_type == ModelType.Msgspec:
                output_str += f"    return await underlying_{query_name}_query_http_bytes({query_params_str})"
            else:
                output_str += f"    return await underlying_{query_name}_query_http({query_params_str})"
            output_str += "\n\n\n"
        elif route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_type_field_val,
                            FastapiHttpRoutesFileHandler.flux_json_query_route_post_type_field_val,
                            FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val,
                            FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val]:
            if route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_type_field_val,
                              FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val]:
                status_code = 200
                route_type_str = "patch"
            else:
                status_code = 201
                route_type_str = "post"

            output_str = f"@perf_benchmark\n"
            if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
                if route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val,
                                  FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val]:
                    if query_params_str:
                        output_str += f"async def underlying_{query_name}_query_http(payload: List[Dict[str, Any]]):\n"
                    else:
                        output_str += f"async def underlying_{query_name}_query_http():\n"
                else:
                    if query_params_str:
                        output_str += f"async def underlying_{query_name}_query_http(payload: Dict[str, Any]):\n"
                    else:
                        output_str += f"async def underlying_{query_name}_query_http():\n"
            else:
                if route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val,
                                  FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val]:
                    if query_params_str:
                        output_str += f"async def underlying_{query_name}_query_http(payload: List[Dict[str, Any]]) -> " \
                                      f"List[{return_type_str}]:\n"
                    else:
                        output_str += f"async def underlying_{query_name}_query_http() -> List[{return_type_str}]:\n"
                else:
                    if query_params_str:
                        output_str += f"async def underlying_{query_name}_query_http(payload: Dict[str, Any]) -> " \
                                      f"List[{return_type_str}]:\n"
                    else:
                        output_str += f"async def underlying_{query_name}_query_http() -> List[{return_type_str}]:\n"
            output_str += self._add_view_check_code_in_route()
            if query_params_str:
                output_str += f"    {message_name_snake_cased}_obj_list = await " \
                              f"callback_class.{query_name}_query_pre({message.proto.name}, payload)\n"
                output_str += f"    {message_name_snake_cased}_obj_list = await " \
                              f"callback_class.{query_name}_query_post({message_name_snake_cased}_obj_list)\n"
            else:
                output_str += f"    {message_name_snake_cased}_obj_list = await " \
                              f"callback_class.{query_name}_query_pre({message.proto.name})\n"
                output_str += f"    {message_name_snake_cased}_obj_list = await " \
                              f"callback_class.{query_name}_query_post({message_name_snake_cased}_obj_list)\n"
            output_str += f"    return {message_name_snake_cased}_obj_list\n\n\n"

            if model_type == ModelType.Msgspec:
                if route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val,
                                  FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val]:
                    if query_params_str:
                        output_str += f"async def underlying_{query_name}_query_http_bytes(payload: List[Dict[str, Any]]):\n"
                        output_str += f"    return_val = await underlying_{query_name}_query_http(payload)\n"
                    else:
                        output_str += f"async def underlying_{query_name}_query_http_bytes():\n"
                        output_str += f"    return_val = await underlying_{query_name}_query_http()\n"
                else:
                    if query_params_str:
                        output_str += f"async def underlying_{query_name}_query_http_bytes(payload: Dict[str, Any]):\n"
                        output_str += f"    return_val = await underlying_{query_name}_query_http(payload)\n"
                    else:
                        output_str += f"async def underlying_{query_name}_query_http_bytes():\n"
                        output_str += f"    return_val = await underlying_{query_name}_query_http()\n"
                output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
                output_str += (f"    return CustomFastapiResponse(content=return_obj_bytes, "
                               f"status_code={status_code})\n\n\n")
            # else not required: if model_type is not Msgspec then no bytes type underlying variant is created

            if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
                output_str += f'@{self.api_router_app_name}.{route_type_str}("/query-{query_name}' + \
                              f'", status_code={status_code})\n'
                if route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val,
                                  FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val]:
                    if query_params_str:
                        output_str += f"async def {query_name}_query_http(payload: List[Dict[str, Any]]):\n"
                    else:
                        output_str += f"async def {query_name}_query_http():\n"
                else:
                    if query_params_str:
                        output_str += f"async def {query_name}_query_http(payload: Dict[str, Any]):\n"
                    else:
                        output_str += f"async def {query_name}_query_http():\n"
            else:
                output_str += f'@{self.api_router_app_name}.{route_type_str}("/query-{query_name}' + \
                              f'", response_model=List[{return_type_str}], status_code={status_code})\n'
                if route_type in [FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val,
                                  FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val]:
                    if query_params_str:
                        output_str += f"async def {query_name}_query_http(payload: List[Dict[str, Any]]) -> " \
                                      f"List[{return_type_str}]:\n"
                    else:
                        output_str += f"async def {query_name}_query_http() -> List[{return_type_str}]:\n"
                else:
                    if query_params_str:
                        output_str += f"async def {query_name}_query_http(payload: Dict[str, Any]) -> " \
                                      f"List[{return_type_str}]:\n"
                    else:
                        output_str += f"async def {query_name}_query_http() -> List[{return_type_str}]:\n"
            output_str += f'    """\n'
            output_str += f'    {route_type} Query of {message.proto.name} with aggregate - {query_name}\n'
            output_str += f'    """\n'
            output_str += self._add_view_check_code_in_route()

            output_str += f"    try:\n"
            if model_type == ModelType.Msgspec:
                if query_params_str:
                    output_str += f"        return await underlying_{query_name}_query_http_bytes(payload)\n"
                else:
                    output_str += f"        return await underlying_{query_name}_query_http_bytes()\n"
            else:
                if query_params_str:
                    output_str += f"        return await underlying_{query_name}_query_http(payload)\n"
                else:
                    output_str += f"        return await underlying_{query_name}_query_http()\n"
            output_str += f"    except Exception as e:\n"
            output_str += (f"        logging.exception(f'{query_name}_query_http failed in "
                           "client call with exception: {e}')\n")
            output_str += f"        raise e\n"
            output_str += "\n\n"
        else:
            err_str = f"Unexpected routes_type: {route_type}, str: {route_type}, type {type(route_type)}"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str

    def _handle_http_file_query_str(self, message: protogen.Message, query_name: str, query_params_str: str | None = None,
                                    query_params_with_type_str: str | None = None, return_type_str: str | None = None,
                                    model_type: ModelType = ModelType.Beanie) -> str:
        if return_type_str is None:
            return_type_str = message.proto.name
        output_str = f"@perf_benchmark\n"
        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            output_str += f"async def underlying_{query_name}_query_http(upload_file: UploadFile"
            if query_params_with_type_str:
                output_str += f", {query_params_with_type_str}"
            output_str += "):\n"
        else:
            output_str += f"async def underlying_{query_name}_query_http(upload_file: UploadFile"
            if query_params_with_type_str:
                output_str += f", {query_params_with_type_str}"
            output_str += f") -> List[{return_type_str}]:\n"
        if query_params_str:
            output_str += f"    return_val = await " \
                          f"callback_class.{query_name}_query_pre(upload_file, {query_params_str})\n"
            output_str += f"    return_val = await " \
                          f"callback_class.{query_name}_query_post(return_val)\n"
        else:
            output_str += f"    return_val = await callback_class.{query_name}_" \
                          f"query_pre(upload_file)\n"
            output_str += f"    await callback_class.{query_name}_query_post(return_val)\n"
        output_str += f"    return return_val\n\n\n"

        if model_type == ModelType.Msgspec:
            output_str += f"async def underlying_{query_name}_query_http_bytes(upload_file: UploadFile"
            if query_params_with_type_str:
                output_str += f", {query_params_with_type_str}"
            output_str += "):\n"
            output_str += (f"    return_val = await underlying_{query_name}_query_http("
                           f"upload_file")
            if query_params_str:
                output_str += f", {query_params_str}"
            output_str += f")\n"
            output_str += f"    return_obj_bytes = msgspec.json.encode(return_val, enc_hook={message.proto.name}.enc_hook)\n"
            output_str += f"    return CustomFastapiResponse(content=return_obj_bytes, status_code=201)\n\n\n"
        # else not required: if model_type is not Msgspec then no bytes type underlying variant is created

        if model_type in [ModelType.Dataclass, ModelType.Msgspec]:
            output_str += f'@{self.api_router_app_name}.post("/query-{query_name}' + \
                          f'", status_code=201)\n'
            output_str += f"async def {query_name}_query_http(upload_file: UploadFile"
            if query_params_with_type_str:
                output_str += f", {query_params_with_type_str}"
            output_str += "):\n"
        else:
            output_str += f'@{self.api_router_app_name}.post("/query-{query_name}' + \
                          f'", response_model=List[{return_type_str}], status_code=201)\n'
            output_str += f"async def {query_name}_query_http(upload_file: UploadFile"
            if query_params_with_type_str:
                output_str += f", {query_params_with_type_str}"
            output_str += f") -> List[{return_type_str}]:\n"
        output_str += f'    """\n'
        output_str += f'    File Upload Query of {message.proto.name} - {query_name}\n'
        output_str += f'    """\n'
        output_str += self._add_view_check_code_in_route()
        if model_type == ModelType.Msgspec:
            output_str += f"    return await underlying_{query_name}_query_http_bytes(upload_file"
            if query_params_str:
                output_str += f", {query_params_str}"
            output_str += f")"
        else:
            output_str += f"    return await underlying_{query_name}_query_http(upload_file"
            if query_params_str:
                output_str += f", {query_params_str}"
            output_str += f")"
        output_str += "\n\n\n"

        return output_str

    def _get_query_params_str_n_query_params_with_type_str(self, query_params_name_n_param_type_tuple_list: List[Tuple[str, str]],
                                                           route_type: str | None = None):
        query_params_str = ""
        query_params_with_type_str = ""
        if query_params_name_n_param_type_tuple_list:
            param_to_type_str_list = []
            list_type_params: List[Tuple[str, str]] = []
            params_name_list: List[str] = []
            for param_name, param_type in query_params_name_n_param_type_tuple_list:
                params_name_list.append(param_name)

                if "List" in param_type and route_type not in [FastapiHttpRoutesFileHandler.flux_json_query_route_post_type_field_val,
                                                                   FastapiHttpRoutesFileHandler.flux_json_query_route_post_all_type_field_val,
                                                                   FastapiHttpRoutesFileHandler.flux_json_query_route_patch_type_field_val,
                                                                   FastapiHttpRoutesFileHandler.flux_json_query_route_patch_all_type_field_val]:
                    list_type_params.append((param_name, param_type))
                else:
                    param_to_type_str_list.append(f"{param_name}: {param_type}")

            for param_name, param_type in list_type_params:
                if "= None" in param_type or "=None" in param_type:
                    param_type = param_type.replace("= None", "").replace("=None", "")
                # else using exiting one as it is fine

                param_to_type_str_list.append(f"{param_name}: {param_type} = Query()")
            query_params_with_type_str = ", ".join(param_to_type_str_list)

            for param_name in params_name_list:
                query_params_str += f"{param_name}={param_name}"
                if params_name_list.index(param_name) != len(params_name_list) - 1:
                    query_params_str += ", "

        return query_params_str, query_params_with_type_str

    def _handle_query_methods(self, message: protogen.Message, model_type: ModelType = ModelType.Beanie) -> str:
        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiHttpRoutesFileHandler.query_name_key]
            query_params_name_n_param_type_tuple_list = aggregate_value[FastapiHttpRoutesFileHandler.query_params_key]
            query_type_value = aggregate_value[FastapiHttpRoutesFileHandler.query_type_key]
            query_type = str(query_type_value).lower() if query_type_value is not None else None
            query_route_value = aggregate_value[FastapiHttpRoutesFileHandler.query_route_type_key]
            query_route_type = query_route_value if query_route_value is not None else None

            query_params_str, query_params_with_type_str = (
                self._get_query_params_str_n_query_params_with_type_str(query_params_name_n_param_type_tuple_list,
                                                                        route_type=query_route_type))

            if query_type is None or query_type == "http" or query_type == "both":
                output_str += self._handle_http_query_str(message, query_name, query_params_str,
                                                          query_params_with_type_str, query_route_type,
                                                          model_type=model_type)
            elif query_type == "http_file":
                output_str += self._handle_http_file_query_str(message, query_name, query_params_str,
                                                               query_params_with_type_str,
                                                               model_type=model_type)

        return output_str

    def _handle_get_max_id_query_generation(self, message: protogen.Message, model_type: ModelType):
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if model_type in [model_type.Dataclass, model_type.Msgspec]:
            output_str = f'@{self.api_router_app_name}.get("/query-get_{message_name_snake_cased}_max_id' + \
                         f'", status_code=200)\n'
            output_str += f"async def get_{message_name_snake_cased}_max_id_http():\n"
        else:
            output_str = f'@{self.api_router_app_name}.get("/query-get_{message_name_snake_cased}_max_id' + \
                         f'", response_model=MaxId, status_code=200)\n'
            output_str += f"async def get_{message_name_snake_cased}_max_id_http() -> MaxId:\n"
        output_str += f'    """\n'
        output_str += f'    Get Query of {message.proto.name} to get max int id\n'
        output_str += f'    """\n'
        output_str += f'    max_val = await get_max_val({message.proto.name})\n'
        if model_type == model_type.Dataclass:
            output_str += f"    return orjson.dumps(MaxId(max_id_val=max_val))\n"
        elif model_type == model_type.Msgspec:
            output_str += (f"    return CustomFastapiResponse(content=MaxId(max_id_val=max_val).to_json_str(), "
                           f"status_code=200)\n")
        else:
            output_str += f"    return MaxId(max_id_val=max_val)\n"
        output_str += "\n\n"
        return output_str

    def _handle_projection_query_methods(self, message, model_type: ModelType | None = None):
        output_str = ""
        for field in message.fields:
            if FastapiHttpRoutesFileHandler.is_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_projections):
                break
        else:
            # If no field is found having projection enabled
            return output_str

        meta_data_field_name_to_field_tuple_dict: Dict[str, Tuple[str, protogen.Field] |
                                                            Dict[str, Tuple[str, protogen.Field]]] = (
            self.get_meta_data_field_name_to_type_str_dict(message))
        projection_val_to_fields_dict = FastapiHttpRoutesFileHandler.get_projection_option_value_to_fields(message)
        projection_val_to_query_name_dict = (
            FastapiHttpRoutesFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
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
            query_param_with_type_str += ("start_date_time: int | None = None, "
                                          "end_date_time: int | None = None")

            # Http Filter Call
            output_str += self._handle_http_query_str(message, query_name, query_param_str, query_param_with_type_str,
                                                      return_type_str=container_model_name, model_type=model_type)

            query_param_dict_str = "{"
            for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                if isinstance(meta_field_info, dict):
                    for nested_meta_field_name, nested_meta_field_info in meta_field_info.items():
                        nested_meta_field_type, _ = nested_meta_field_info
                        query_param_dict_str += (f'"{nested_meta_field_name}": '
                                                 f'{nested_meta_field_type}, ')
                else:
                    meta_field_type, _ = meta_field_info
                    query_param_dict_str += f'"{meta_field_name}": {meta_field_name}, '
            query_param_dict_str += '"start_date_time": start_date_time, "end_date_time": end_date_time}'

        return output_str

    def handle_button_query_method(self, message: protogen.Message, query_data_dict: Dict,
                                   model_type: ModelType | None = None):
        output_str = ""
        query_data = query_data_dict.get("query_data")
        query_name = query_data.get(FastapiHttpRoutesFileHandler.flux_json_query_name_field)
        query_type_value = query_data.get(FastapiHttpRoutesFileHandler.flux_json_query_type_field)
        query_type = str(query_type_value).lower() if query_type_value is not None else None
        query_params = query_data.get(FastapiHttpRoutesFileHandler.flux_json_query_params_field)

        query_param_name_n_param_type_list = []
        if query_params:
            for query_param in query_params:
                query_param_name = query_param.get(FastapiHttpRoutesFileHandler.flux_json_query_params_name_field)
                query_param_type = query_param.get(FastapiHttpRoutesFileHandler.flux_json_query_params_data_type_field)
                query_param_name_n_param_type_list.append((query_param_name, query_param_type))
        query_params_str, query_params_with_type_str = (
            self._get_query_params_str_n_query_params_with_type_str(query_param_name_n_param_type_list))

        if query_type is None or query_type == "http" or query_type == "both":
            query_route_value = query_data.get(FastapiHttpRoutesFileHandler.flux_json_query_route_type_field)
            query_route_type = query_route_value if query_route_value is not None else None

            output_str += self._handle_http_query_str(message, query_name, query_params_str,
                                                      query_params_with_type_str, query_route_type, model_type=model_type)
        elif query_type == "http_file":
            file_upload_data = query_data_dict.get(
                FastapiHttpRoutesFileHandler.button_query_file_upload_options_key)
            disallow_duplicate_file_upload = False
            if file_upload_data:
                disallow_duplicate_file_upload = file_upload_data.get("disallow_duplicate_file_upload")

            if query_params_str:
                query_params_str += ', disallow_duplicate_file_upload=disallow_duplicate_file_upload'
            else:
                query_params_str = 'disallow_duplicate_file_upload=disallow_duplicate_file_upload'

            if query_params_with_type_str:
                if disallow_duplicate_file_upload:
                    query_params_with_type_str += ", disallow_duplicate_file_upload: bool = True"
                else:
                    query_params_with_type_str += ", disallow_duplicate_file_upload: bool = False"
            else:
                if disallow_duplicate_file_upload:
                    query_params_with_type_str = "disallow_duplicate_file_upload: bool = True"
                else:
                    query_params_with_type_str = "disallow_duplicate_file_upload: bool = False"
            output_str += self._handle_http_file_query_str(message, query_name, query_params_str,
                                                           query_params_with_type_str, model_type=model_type)
        return output_str

    def handle_pydantic_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root):
                output_str += self._handle_routes_methods(message)
            elif self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_routes_methods(message)

        for message in self.message_to_query_option_list_dict:
            output_str += self._handle_query_methods(message)

        query_data_dict_list: List[Dict]
        for message, query_data_dict_list in self.message_to_button_query_data_dict.items():
            for query_data_dict in query_data_dict_list:
                output_str += self.handle_button_query_method(message, query_data_dict)

        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_projection_query_methods(message)
        return output_str

    def handle_dataclass_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root):
                output_str += self._handle_routes_methods(message, model_type=ModelType.Dataclass)
            elif self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_routes_methods(message, model_type=ModelType.Dataclass)

        for message in self.message_to_query_option_list_dict:
            output_str += self._handle_query_methods(message, model_type=ModelType.Dataclass)

        query_data_dict_list: List[Dict]
        for message, query_data_dict_list in self.message_to_button_query_data_dict.items():
            for query_data_dict in query_data_dict_list:
                output_str += self.handle_button_query_method(message, query_data_dict, model_type=ModelType.Dataclass)

        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_projection_query_methods(message, model_type=ModelType.Dataclass)
        return output_str

    def handle_msgspec_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            # root_message_list includes both json root and time series messages
            output_str += self._handle_routes_methods(message, model_type=ModelType.Msgspec)

        for message in self.message_to_query_option_list_dict:
            output_str += self._handle_query_methods(message, model_type=ModelType.Msgspec)

        query_data_dict_list: List[Dict]
        for message, query_data_dict_list in self.message_to_button_query_data_dict.items():
            for query_data_dict in query_data_dict_list:
                output_str += self.handle_button_query_method(message, query_data_dict, model_type=ModelType.Msgspec)

        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                # returns empty str if message has no field suggesting projection query option set
                output_str += self._handle_projection_query_methods(message, model_type=ModelType.Msgspec)
        return output_str

    def _get_aggregate_query_var_list(self) -> List[str]:
        agg_query_var_list = []
        for message in self.root_message_list:
            if self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name):
                agg_query_var_list.append(
                    self.get_simple_option_value_from_proto(
                        message,
                        FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)[1:-1])
        # else not required: if no message is found with agg_query option then returning empty list
        return agg_query_var_list

    def _handle_ui_specific_code(self):
        output_str = 'host = os.environ.get("HOST")\n'
        output_str += 'if host is None or len(host) == 0:\n'
        output_str += '    err_str = "Couldn\'t find \'HOST\' key in data/config.yaml of current project"\n'
        output_str += '    logging.error(err_str)\n'
        output_str += '    raise Exception(err_str)\n'
        output_str += "\n\ntemplates = Jinja2Templates(directory=f'{host}/templates')\n\n"
        output_str += f"@{self.api_router_app_name}.get('/')\n"
        output_str += "async def serve_spa(request: Request):\n"
        output_str += "    return templates.TemplateResponse('index.html', {'request': request})\n"
        return output_str

    def handle_http_pydantic_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_model_class_dict()

        base_routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.base_routes_file_name)
        output_str = f"from {base_routes_file_path} import *\n\n"
        output_str += self.handle_pydantic_CRUD_task()
        output_str += self._handle_ui_specific_code()
        return output_str

    def handle_http_dataclass_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_model_class_dict()

        base_routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.base_routes_file_name)
        output_str = f"from dataclasses import dataclass\n\n"
        output_str += f"from {base_routes_file_path} import *\n\n"
        output_str += self.handle_dataclass_CRUD_task()
        output_str += self._handle_ui_specific_code()

        return output_str

    def handle_http_msgspec_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_model_class_dict()

        base_routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.base_routes_file_name)
        output_str = f"from {base_routes_file_path} import *\n\n"
        output_str += self.handle_msgspec_CRUD_task()
        output_str += self._handle_ui_specific_code()

        return output_str
