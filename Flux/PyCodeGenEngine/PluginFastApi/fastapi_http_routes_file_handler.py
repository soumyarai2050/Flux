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
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_base_routes_file_handler import FastapiBaseRoutesFileHandler


class FastapiHttpRoutesFileHandler(FastapiBaseRoutesFileHandler, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.shared_lock_name_to_pydentic_class_dict: Dict[str, List[protogen.Message]] = {}
        self.shared_lock_name_message_list: List[protogen.Message] = []
        self.message_to_link_messages_dict: Dict[protogen.Message, List[protogen.Message]] = {}
        self._msg_already_generated_str_formatted_int_fields_handler_list: List[protogen.Message] = []

    def _get_list_of_shared_lock_for_message(self, message: protogen.Message) -> List[str]:
        shared_lock_name_list = []
        for shared_lock_name, message_list in self.shared_lock_name_to_pydentic_class_dict.items():
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

    def _unpack_kwargs_with_id_field_type(self, **kwargs) -> Tuple[protogen.Message, str, str, List[str]]:
        message: protogen.Message | None = kwargs.get("message")
        aggregation_type: str | None = kwargs.get("aggregation_type")
        id_field_type: str | None = kwargs.get("id_field_type")
        shared_lock_list: List[str] | None = kwargs.get("shared_lock_list")

        if message is None or aggregation_type is None or id_field_type is None:
            err_str = (f"Received kwargs having some None values out of message: "
                       f"{message.proto.name if message is not None else message}, "
                       f"aggregation_type: {aggregation_type}, id_field_type: {id_field_type}")
            logging.exception(err_str)
            raise Exception(err_str)
        return message, aggregation_type, id_field_type, shared_lock_list

    def _unpack_kwargs_without_id_field_type(self, **kwargs):
        message: protogen.Message | None = kwargs.get("message")
        aggregation_type: str | None = kwargs.get("aggregation_type")
        shared_lock_list: List[str] | None = kwargs.get("shared_lock_list")
        if message is None or aggregation_type is None:
            err_str = (f"Received kwargs having some None values out of message: "
                       f"{message.proto.name if message is not None else message}, "
                       f"aggregation_type: {aggregation_type}")
            logging.exception(err_str)
            raise Exception(err_str)
        return message, aggregation_type, shared_lock_list

    def handle_underlying_POST_one_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += (f"async def underlying_create_{message_name_snake_cased}_http({message_name_snake_cased}: "
                       f"{message.proto.name}, filter_agg_pipeline: Any = None, generic_callable: "
                       f"Callable[[...], Any] | None = None, return_obj_copy: bool | None = True"
                       f") -> {message.proto.name} | bool:\n")
        output_str += f'    """\n'
        output_str += f'    Create route for {message.proto.name}\n'
        output_str += f'    """\n'
        output_str += f'    if generic_callable is None:\n'
        output_str += f'        generic_callable = generic_post_http\n'
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + \
                      f"    await callback_class.create_{message_name_snake_cased}_pre({message_name_snake_cased})\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name_snake_cased}, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, {message_name_snake_cased}, "
                               f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, {message_name_snake_cased}, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}, {self._get_filter_configs_var_name(message)}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
        output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_POST_gen(self, **kwargs) -> str:
        message, _, _ = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_POST_one_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + \
                      f'", response_model={message.proto.name} | bool, status_code=201)\n'
        output_str += (f"async def create_{message_name_snake_cased}_http({message_name_snake_cased}: "
                       f"{message.proto.name}, return_obj_copy: bool | None = True) -> "
                       f"{message.proto.name} | bool:\n")
        output_str += (f"    return await underlying_create_{message_name_snake_cased}_http("
                       f"{message_name_snake_cased}, return_obj_copy=return_obj_copy)\n")
        return output_str

    def handle_underlying_POST_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += (f"async def underlying_create_all_{message_name_snake_cased}_http({message_name_snake_cased}_list: "
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
        output_str += " " * indent_count + \
                      f"    await callback_class.create_all_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_list)\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj_list = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}," \
                      f"{message_name_snake_cased}_list, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_list, "
                               f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
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
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_list, {self._get_filter_configs_var_name(message)}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        {message_name_snake_cased}_obj_list = "
                               f"await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message_name_snake_cased}_list, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
        output_str += " " * indent_count + f"    await callback_class.create_all_{message_name_snake_cased}_post({message_name_snake_cased}_obj_list)\n"
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_obj_list\n"
        output_str += "\n"
        return output_str

    def handle_POST_all_gen(self, **kwargs) -> str:
        message, _, _ = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_POST_all_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.post("/create_all-{message_name_snake_cased}' + \
                      f'", response_model=List[{message.proto.name}] | bool, status_code=201)\n'
        output_str += (f"async def create_all_{message_name_snake_cased}_http({message_name_snake_cased}_list: "
                       f"List[{message.proto.name}], return_obj_copy: bool | None = True) -> "
                       f"List[{message.proto.name}] | bool:\n")
        output_str += f"    return await underlying_create_all_{message_name_snake_cased}_http(" \
                      f"{message_name_snake_cased}_list, return_obj_copy=return_obj_copy)\n"
        return output_str

    def handle_underlying_PUT_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
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
        output_str += " " * indent_count + (f"    if not config_yaml_dict.get("
                                            f"'avoid_{message_name_snake_cased}_db_update'):\n")
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_obj = " \
                      f"await generic_callable({message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj), {message_name_snake_cased}_updated, " \
                      f"filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, {self._get_filter_configs_var_name(message)}, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
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
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                               f"{message_name_snake_cased}_updated, {self._get_filter_configs_var_name(message)}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                               f"{message_name_snake_cased}_updated, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
        output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post(" \
                                           f"stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
        output_str += " " * indent_count + f"    return updated_{message_name_snake_cased}_obj\n"
        indent_count -= 4
        output_str += " " * indent_count + f"    else:\n"
        indent_count += 4
        output_str += " " * indent_count + f"    await callback_class.update_{message_name_snake_cased}_post(" \
                                           f"stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
        output_str += " " * indent_count + f"    return True\n"
        output_str += "\n"
        return output_str

    def handle_PUT_gen(self, **kwargs) -> str:
        message, _, _ = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PUT_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                      f'", response_model={message.proto.name} | bool, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}, return_obj_copy: bool | None = True) -> {message.proto.name} | bool:\n"
        output_str += f"    return await underlying_update_{message_name_snake_cased}_http(" \
                      f"{message_name_snake_cased}_updated, return_obj_copy=return_obj_copy)\n"
        return output_str

    def handle_underlying_PUT_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += (f"async def underlying_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
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
        output_str += " " * indent_count + f"    obj_id_list = [pydantic_obj.id for pydantic_obj in " \
                                           f"{message_name_snake_cased}_updated_list]\n"
        output_str += " " * indent_count + f"    stored_{message_name_snake_cased}_obj_list = await " \
                                           f"generic_read_http({message.proto.name}, " \
                                           f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, has_links={msg_has_links}, " \
                                           f"read_ids_list=obj_id_list)\n"
        output_str += " " * indent_count + f"    {message_name_snake_cased}_updated_list = " \
                                           f"await callback_class.update_all_{message_name_snake_cased}_pre(" \
                                           f"stored_{message_name_snake_cased}_obj_list, {message_name_snake_cased}_updated_list)\n"
        output_str += " " * indent_count + (f"    if not config_yaml_dict.get("
                                            f"'avoid_{message_name_snake_cased}_db_update'):\n")
        indent_count += 4
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_obj_list = " \
                      f"await generic_callable({message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), {message_name_snake_cased}_updated_list, " \
                      f"obj_id_list, filter_agg_pipeline, return_obj_copy=return_obj_copy)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj_list = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                              f"{message_name_snake_cased}_updated_list, obj_id_list, " \
                              f"{self._get_filter_configs_var_name(message)}, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
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
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                               f"{message_name_snake_cased}_updated_list, obj_id_list, "
                               f"{self._get_filter_configs_var_name(message)}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj_list = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                               f"{message_name_snake_cased}_updated_list, obj_id_list, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
        output_str += " " * indent_count + f"    await callback_class.update_all_{message_name_snake_cased}_post(" \
                                           f"stored_{message_name_snake_cased}_obj_list, " \
                                           f"updated_{message_name_snake_cased}_obj_list)\n"
        output_str += " " * indent_count + f"    return updated_{message_name_snake_cased}_obj_list\n"
        indent_count -= 4
        output_str += " " * indent_count + f"    else:\n"
        indent_count += 4
        output_str += " " * indent_count + (f"    await callback_class.update_all_{message_name_snake_cased}_post("
                                            f"stored_{message_name_snake_cased}_obj_list, "
                                            f"{message_name_snake_cased}_updated_list)\n")
        output_str += " " * indent_count + f"    return True\n"
        output_str += "\n"
        return output_str

    def handle_PUT_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PUT_all_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.put("/put_all-{message_name_snake_cased}' + \
                      f'", response_model=List[{message.proto.name}] | bool, status_code=200)\n'
        output_str += (f"async def update_all_{message_name_snake_cased}_http({message_name_snake_cased}_updated_list: "
                       f"List[{message.proto.name}], return_obj_copy: bool | None = True"
                       f") -> List[{message.proto.name}] | bool:\n")
        output_str += f"    return await underlying_update_all_{message_name_snake_cased}_http(" \
                      f"{message_name_snake_cased}_updated_list, return_obj_copy=return_obj_copy)\n"
        return output_str

    def handle_underlying_PATCH_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self._handle_str_int_val_callable_generation(message)
        output_str += "\n"
        output_str += "@perf_benchmark\n"
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
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                       f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                       f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                       f"{message_name_snake_cased}_update_req_json, filter_agg_pipeline, "
                       f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj =  await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_update_req_json, {self._get_filter_configs_var_name(message)}, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
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
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                               f"{message_name_snake_cased}_update_req_json, {self._get_filter_configs_var_name(message)}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj), "
                               f"{message_name_snake_cased}_update_req_json, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
        output_str += " " * indent_count + f"    await callback_class.partial_update_{message_name_snake_cased}_post(" \
                                           f"stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
        output_str += " " * indent_count + f"    return updated_{message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_PATCH_gen(self, **kwargs) -> str:
        message, _, _ = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PATCH_gen(**kwargs)
        output_str += f"\n"
        output_str += f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}' + \
                      f'", response_model={message.proto.name} | bool, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_update_req_body: " \
                      f"Request, return_obj_copy: bool | None = True) -> {message.proto.name} | bool:\n"
        output_str += f"    json_body = await {message_name_snake_cased}_update_req_body.json()\n"
        output_str += (f'    return await underlying_partial_update_{message_name_snake_cased}_http(json_body, '
                       f'return_obj_copy=return_obj_copy)\n')
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

    def _handle_str_int_val_callable_generation(self, message: protogen.Message) -> str:
        if message in self._msg_already_generated_str_formatted_int_fields_handler_list:
            # if handler function is already generated for this model for either patch or patch_all then
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
            for int_field in int_field_list:
                int_fields_dot_sep_list: List[str] = int_field.split(".")
                indent_count = 1
                last_field_name = f"{message_name_camel_cased}_update_req_json"
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

            # adding msg to cache to be checked for another call from patch or patch_all to avoid
            # duplicate function creation
            self._msg_already_generated_str_formatted_int_fields_handler_list.append(message)

        return output_str

    def handle_underlying_PATCH_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self._handle_str_int_val_callable_generation(message)
        output_str += "\n"
        output_str += "@perf_benchmark\n"
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
        output_str += " " * indent_count + f"        obj_id = {message_name_snake_cased}_update_req_json.get('_id')\n"
        output_str += " " * indent_count + f"        if obj_id is None:\n"
        output_str += " " * indent_count + f'            err_str_ = f"Can not find _id key in received response ' \
                                           f'body for patch all operation of {message.proto.name}, response body: ' + \
                                           '{'+f'{message_name_snake_cased}_update_req_json_list'+'}"\n'
        output_str += " " * indent_count + f"            raise HTTPException(status_code=503, detail=err_str_)\n"
        output_str += " " * indent_count + f"        obj_id_list.append(obj_id)\n"
        output_str += " " * indent_count + (f"    stored_{message_name_snake_cased}_obj_list = await "
                                            f"generic_read_http({message.proto.name}, "
                                            f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                                            f"has_links={msg_has_links}, read_ids_list=obj_id_list)\n")
        output_str += " " * indent_count + (f"    {message_name_snake_cased}_update_req_json_list = "
                                            f"await callback_class.partial_update_all_{message_name_snake_cased}_pre("
                                            f"stored_{message_name_snake_cased}_obj_list, "
                                            f"{message_name_snake_cased}_update_req_json_list)\n")
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_obj = await generic_callable(" \
                      f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                      f"{message_name_snake_cased}_update_req_json_list, obj_id_list, filter_agg_pipeline, " \
                      f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj =  await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                              f"{message_name_snake_cased}_update_req_json_list, obj_id_list, " \
                              f"{self._get_filter_configs_var_name(message)}, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                               f"{message_name_snake_cased}_update_req_json_list, obj_id_list, "
                               f"update_agg_pipeline={update_agg_pipeline_var_name}, "
                               f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n")
            case FastapiHttpRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiHttpRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              (f"        updated_{message_name_snake_cased}_obj = await generic_callable("
                               f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), "
                               f"{message_name_snake_cased}_update_req_json_list, obj_id_list, "
                               f"{self._get_filter_configs_var_name(message)}, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
                output_str += " " * indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"copy.deepcopy(stored_{message_name_snake_cased}_obj_list), " \
                              f"{message_name_snake_cased}_update_req_json_list, obj_id_list, " \
                              f"has_links={msg_has_links}, return_obj_copy=return_obj_copy)\n"
        output_str += " " * indent_count + (f"    await callback_class.partial_update_all_"
                                            f"{message_name_snake_cased}_post("
                                            f"stored_{message_name_snake_cased}_obj_list, "
                                            f"updated_{message_name_snake_cased}_obj)\n")
        output_str += " " * indent_count + f"    return updated_{message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_PATCH_all_gen(self, **kwargs) -> str:
        message, _, _ = self._unpack_kwargs_without_id_field_type(**kwargs)

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PATCH_all_gen(**kwargs)
        output_str += f"\n"
        output_str += f'@{self.api_router_app_name}.patch("/patch_all-{message_name_snake_cased}' + \
                      f'", response_model=List[{message.proto.name}] | bool, status_code=200)\n'
        output_str += (f"async def partial_update_all_{message_name_snake_cased}_http({message_name_snake_cased}_"
                       f"update_req_body: Request, return_obj_copy: bool | None = True"
                       f") -> List[{message.proto.name}] | bool:\n")
        output_str += f"    json_body = await {message_name_snake_cased}_update_req_body.json()\n"
        output_str += (f'    return await underlying_partial_update_all_{message_name_snake_cased}_http(json_body, '
                       f'return_obj_copy=return_obj_copy)\n')
        return output_str

    def handle_underlying_DELETE_gen(self, **kwargs) -> str:
        message, aggregation_type, id_field_type, shared_lock_list = self._unpack_kwargs_with_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        if id_field_type is not None:
            output_str += (f"async def underlying_delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id: {id_field_type}, "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True) -> DefaultWebResponse | bool:\n")
        else:
            output_str += (f"async def underlying_delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                           f"generic_callable: Callable[[...], Any] | None = None, "
                           f"return_obj_copy: bool | None = True) -> DefaultWebResponse | bool:\n")
        output_str += f'    """\n'
        output_str += f'    Delete route for {message.proto.name}\n'
        output_str += f'    """\n'
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
                output_str += " " * indent_count + \
                              (f"    delete_web_resp = await generic_callable({message.proto.name}, "
                               f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, "
                               f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj, "
                               f"{update_agg_pipeline_var_name}, has_links={msg_has_links}, "
                               f"return_obj_copy=return_obj_copy)\n")
            case other:
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
        message, _, id_field_type, _ = self._unpack_kwargs_with_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_DELETE_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                      '{' + f'{message_name_snake_cased}_id' + '}' + \
                      f'", response_model=DefaultWebResponse | bool, status_code=200)\n'
        if id_field_type is not None:
            output_str += (f"async def delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id: {id_field_type}, "
                           f"return_obj_copy: bool | None = True) -> DefaultWebResponse | bool:\n")
        else:
            output_str += (f"async def delete_{message_name_snake_cased}_http("
                           f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, "
                           f"return_obj_copy: bool | None = True) -> DefaultWebResponse | bool:\n")
        output_str += f"    return await underlying_delete_{message_name_snake_cased}_http(" \
                      f"{message_name_snake_cased}_id, return_obj_copy=return_obj_copy)\n"
        return output_str

    def handle_underlying_DELETE_all_gen(self, **kwargs) -> str:
        message, aggregation_type, shared_lock_list = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += (f"async def underlying_delete_all_{message_name_snake_cased}_http("
                       f"generic_callable: Callable[[...], Any] | None = None, "
                       f"return_obj_copy: bool | None = True) -> DefaultWebResponse | bool:\n")
        output_str += f'    """\n'
        output_str += f'    Delete All route for {message.proto.name}\n'
        output_str += f'    """\n'
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
        message, _, _ = self._unpack_kwargs_without_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_DELETE_all_gen(**kwargs)
        output_str += "\n"
        output_str += (f'@{self.api_router_app_name}.delete("/delete_all-{message_name_snake_cased}/", '
                       f'response_model=DefaultWebResponse | bool, status_code=200)\n')
        output_str += (f"async def delete_{message_name_snake_cased}_all_http(return_obj_copy: bool | None = True"
                       f") -> DefaultWebResponse | bool:\n")
        output_str += (f"    return await underlying_delete_all_{message_name_snake_cased}_http("
                       f"return_obj_copy=return_obj_copy)\n")
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
        filter_configs_var_name = self._get_filter_configs_var_name(message)
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

    def handle_index_req_gen(self, message: protogen.Message, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_index_req_gen(message, shared_lock_list)
        output_str += "\n"
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_index)]

        field_query = "/".join(["{" + f"{field.proto.name}" + "}" for field in index_fields])
        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])

        output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-index-fields/' + \
                      f'{field_query}' + f'", response_model=List[{message.proto.name}], status_code=200)\n'
        output_str += f"async def get_{message_name_snake_cased}_from_index_fields_http({field_params}) " \
                      f"-> List[{message.proto.name}]:\n"
        field_params = ", ".join([f"{field.proto.name}" for field in index_fields])
        output_str += \
            f"    return await underlying_get_{message_name_snake_cased}_from_index_fields_http({field_params})\n\n\n"
        return output_str

    def handle_underlying_GET_gen(self, **kwargs) -> str:
        message, aggregation_type, id_field_type, shared_lock_list = self._unpack_kwargs_with_id_field_type(**kwargs)
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        if id_field_type is not None:
            output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id: {id_field_type}, filter_agg_pipeline: Any = None, " \
                          f"generic_callable: Callable[[...], Any] | None = None) -> {message.proto.name}:\n"
        else:
            output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http(" \
                          f"{message_name_snake_cased}_id: {FastapiHttpRoutesFileHandler.default_id_type_var_name}, " \
                          f"filter_agg_pipeline: Any = None, generic_callable: " \
                          f"Callable[[...], Any] | None = None) -> {message.proto.name}:\n"
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
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                      f"{message_name_snake_cased}_id, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_id, " \
                              f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update | FastapiHttpRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in read by id operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_callable(" \
                              f"{message.proto.name}, {FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{message_name_snake_cased}_id, has_links={msg_has_links})\n"

        output_str += " " * indent_count + f"    await callback_class.read_by_id_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_GET_gen(self, **kwargs) -> str:
        message, _, id_field_type, _ = self._unpack_kwargs_with_id_field_type(**kwargs)
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_GET_gen(**kwargs)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                      f'{message_name_snake_cased}_id' + '}' + \
                      f'", response_model={message.proto.name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> {message.proto.name}:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{FastapiHttpRoutesFileHandler.default_id_type_var_name}) -> {message.proto.name}:\n"
        output_str += \
            f"    return await underlying_read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id)\n"
        return output_str

    def handle_underlying_GET_ALL_gen(self, message: protogen.Message, aggregation_type: str,
                                      shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += (f"async def underlying_read_{message_name_snake_cased}_http("
                       f"filter_agg_pipeline: Any = None, generic_callable: "
                       f"Callable[[...], Any] | None = None, projection_model=None, "
                       f"projection_filter: Dict | None = None) -> List[{message.proto.name}]:\n")
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
                      f"        obj_list = await generic_callable({message.proto.name}, " \
                      f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, filter_agg_pipeline, " \
                      f"has_links={msg_has_links}, projection_model=projection_model)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiHttpRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        obj_list = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiHttpRoutesFileHandler.aggregation_type_update | FastapiHttpRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in real all operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " " * indent_count + \
                              f"        obj_list = await generic_callable({message.proto.name}, " \
                              f"{FastapiHttpRoutesFileHandler.proto_package_var_name}, " \
                              f"has_links={msg_has_links})\n"
        output_str += " " * indent_count + f"    await callback_class.read_all_{message_name_snake_cased}_post(obj_list)\n"
        output_str += " " * indent_count + f"    return obj_list\n\n"
        return output_str

    def handle_GET_ALL_gen(self, message: protogen.Message, aggregation_type: str,
                           shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_GET_ALL_gen(message, aggregation_type, shared_lock_list)
        output_str += "\n"
        output_str += (f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}'
                       f'", response_model=List[{message.proto.name}], status_code=200)\n')
        output_str += (f"async def read_{message_name_snake_cased}_http(limit_obj_count: int | None = None"
                       f") -> List[{message.proto.name}]:\n")
        output_str += f"    limit_filter_agg: Dict[str, Any] | None = None\n"
        output_str += f"    if limit_obj_count is not None:\n"
        output_str += "        limit_filter_agg = {'agg': get_limited_objs(limit_obj_count)}\n"
        output_str += f"    return await underlying_read_{message_name_snake_cased}_http(limit_filter_agg)\n\n\n"
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

    def _handle_routes_methods(self, message: protogen.Message) -> str:
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
            FastapiHttpRoutesFileHandler.flux_json_root_delete_all_field: self.handle_DELETE_all_gen
        }

        if self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root):
            option_val_dict = self.get_complex_option_value_from_proto(message, FastapiHttpRoutesFileHandler.flux_msg_json_root)
        else:
            option_val_dict = self.get_complex_option_value_from_proto(message,
                                                                       FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series)

        shared_mutex_list = self._get_list_of_shared_lock_for_message(message)

        if (aggregation_type := option_val_dict.get(FastapiHttpRoutesFileHandler.flux_json_root_read_field)) is not None:
            output_str += self.handle_GET_ALL_gen(message, aggregation_type.strip(), shared_mutex_list)
        # else not required: avoiding find_all route for this message if read_field of json_root option is not set

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_val_dict:
                aggregation_type: str = self._check_agg_info_availability(option_val_dict[crud_option_field_name].strip(),
                                                                          crud_option_field_name,
                                                                          message)
                output_str += crud_operation_method(message=message, aggregation_type=aggregation_type,
                                                    id_field_type=id_field_type, shared_mutex_list=shared_mutex_list)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_index):
                output_str += self.handle_index_req_gen(message, shared_mutex_list)
                break
            # else not required: Avoiding field if index option is not enabled

        if id_field_type == "int":
            output_str += self._handle_get_max_id_query_generation(message)

        return output_str

    def _handle_http_query_str(self, message: protogen.Message, query_name: str, query_params_str: str,
                               query_params_with_type_str: str, route_type: str | None = None,
                               return_type_str: str | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        if return_type_str is None:
            return_type_str = message.proto.name
        if route_type is None or route_type == FastapiHttpRoutesFileHandler.flux_json_query_route_get_type_field_val:
            output_str = "@perf_benchmark\n"
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
            output_str += f'@{self.api_router_app_name}.get("/query-{query_name}' + \
                          f'", response_model=List[{return_type_str}], status_code=200)\n'
            output_str += f"async def {query_name}_query_http({query_params_with_type_str}) -> " \
                          f"List[{return_type_str}]:\n"
            output_str += f'    """\n'
            output_str += f'    Get Query of {message.proto.name} with aggregate - {query_name}\n'
            output_str += f'    """\n'
            output_str += f"    return await underlying_{query_name}_query_http({query_params_str})"
            output_str += "\n\n\n"
        elif route_type == FastapiHttpRoutesFileHandler.flux_json_query_route_patch_type_field_val:
            output_str = "@perf_benchmark\n"
            output_str += f"async def underlying_{query_name}_query_http(payload_dict: Dict[str, Any]) -> " \
                          f"List[{return_type_str}]:\n"
            if query_params_str:
                output_str += f"    {message_name_snake_cased}_obj = await " \
                              f"callback_class.{query_name}_query_pre({message.proto.name}, payload_dict)\n"
                output_str += f"    {message_name_snake_cased}_obj = await " \
                              f"callback_class.{query_name}_query_post({message_name_snake_cased}_obj)\n"
            else:
                err_str = f"patch query can't be generated without payload query_param, query {query_name} in " \
                          f"message {message.proto.name} found without query params"
                logging.exception(err_str)
                raise Exception(err_str)
            output_str += f"    return {message_name_snake_cased}_obj\n\n\n"
            output_str += f'@{self.api_router_app_name}.patch("/query-{query_name}' + \
                          f'", response_model=List[{return_type_str}], status_code=201)\n'
            output_str += f"async def {query_name}_query_http(payload_dict: Dict[str, Any]) -> " \
                          f"List[{return_type_str}]:\n"
            output_str += f'    """\n'
            output_str += f'    Patch Query of {message.proto.name} with aggregate - {query_name}\n'
            output_str += f'    """\n'
            output_str += f"    return await underlying_{query_name}_query_http(payload_dict)"
            output_str += "\n\n\n"
        else:
            err_str = f"Unexpected routes_type: {route_type}, str: {route_type}, type {type(route_type)}"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str

    def _handle_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiHttpRoutesFileHandler.query_name_key]
            query_params = aggregate_value[FastapiHttpRoutesFileHandler.query_params_key]
            query_params_data_types = aggregate_value[FastapiHttpRoutesFileHandler.query_params_data_types_key]
            query_type_value = aggregate_value[FastapiHttpRoutesFileHandler.query_type_key]
            query_type = str(query_type_value).lower() if query_type_value is not None else None
            query_route_value = aggregate_value[FastapiHttpRoutesFileHandler.query_route_type_key]
            query_route_type = query_route_value if query_route_value is not None else None

            query_params_str = ""
            query_params_with_type_str = ""
            query_args_dict_str = ""
            if query_params:
                param_to_type_str_list = []
                list_type_params: List[Tuple[str, str]] = []
                for param, param_type in zip(query_params, query_params_data_types):
                    if "List" not in param_type:
                        param_to_type_str_list.append(f"{param}: {param_type}")
                    else:
                        list_type_params.append((param, param_type))
                for param, param_type in list_type_params:
                    param_to_type_str_list.append(f"{param}: {param_type} = Query()")
                query_params_with_type_str = ", ".join(param_to_type_str_list)
                query_params_str = ", ".join(query_params)
                query_args_str = ', '.join([f'"{param}": {param}' for param in query_params])
                query_args_dict_str = "{"+f"{query_args_str}"+"}"

            if query_type is None or query_type == "http" or query_type == "both":
                output_str += self._handle_http_query_str(message, query_name, query_params_str,
                                                         query_params_with_type_str, query_route_type)

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

    def _handle_projection_query_methods(self, message):
        output_str = ""
        for field in message.fields:
            if FastapiHttpRoutesFileHandler.is_option_enabled(field, FastapiHttpRoutesFileHandler.flux_fld_projections):
                break
        else:
            # If no field is found having projection enabled
            return output_str

        meta_data_field_name_to_field_proto_dict: Dict[str, (protogen.Field | Dict[str, protogen.Field])] = (
            self.get_meta_data_field_name_to_field_proto_dict(message))
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
            projection_model_name = f"{message.proto.name}ProjectionFor{field_names_str_camel_cased}"

            query_param_str = ""
            query_param_with_type_str = ""
            for meta_field_name, meta_field_value in meta_data_field_name_to_field_proto_dict.items():
                if isinstance(meta_field_value, dict):
                    for nested_meta_field_name, nested_meta_field in meta_field_value.items():
                        query_param_str += f"{nested_meta_field_name}, "
                        query_param_with_type_str += (f"{nested_meta_field_name}: "
                                                      f"{self.proto_to_py_datatype(nested_meta_field)}, ")
                else:
                    query_param_str += f"{meta_field_name}, "
                    query_param_with_type_str += f"{meta_field_name}: {self.proto_to_py_datatype(meta_field_value)}, "
            query_param_str += "start_date_time, end_date_time"
            query_param_with_type_str += ("start_date_time: DateTime | None = None, "
                                          "end_date_time: DateTime | None = None")

            # Http Filter Call
            output_str += self._handle_http_query_str(message, query_name, query_param_str, query_param_with_type_str,
                                                      return_type_str=container_model_name)

            query_param_dict_str = "{"
            for meta_field_name, meta_field_value in meta_data_field_name_to_field_proto_dict.items():
                if isinstance(meta_field_value, dict):
                    for nested_meta_field_name, nested_meta_field in meta_field_value.items():
                        query_param_dict_str += (f'"{nested_meta_field_name}": '
                                                 f'{nested_meta_field_name}, ')
                else:
                    query_param_dict_str += f'"{meta_field_name}": {meta_field_name}, '
            query_param_dict_str += '"start_date_time": start_date_time, "end_date_time": end_date_time}'

        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root):
                output_str += self._handle_routes_methods(message)
            elif self.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_routes_methods(message)

        for message in self.message_to_query_option_list_dict:
            # if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_query):
            output_str += self._handle_query_methods(message)

        for message in self.root_message_list:
            if FastapiHttpRoutesFileHandler.is_option_enabled(message, FastapiHttpRoutesFileHandler.flux_msg_json_root_time_series):
                output_str += self._handle_projection_query_methods(message)

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

    def handle_http_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_pydentic_class_dict()

        base_routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.base_routes_file_name)
        output_str = f"from {base_routes_file_path} import *\n\n"
        output_str += self.handle_CRUD_task()
        output_str += 'host = os.environ.get("HOST")\n'
        output_str += 'if host is None or len(host) == 0:\n'
        output_str += '    err_str = "Couldn\'t find \'HOST\' key in data/config.yaml of current project"\n'
        output_str += '    logging.error(err_str)\n'
        output_str += '    raise Exception(err_str)\n'
        output_str += "\n\ntemplates = Jinja2Templates(directory=f'{host}/templates')\n\n"
        output_str += f"@{self.api_router_app_name}.get('/')\n"
        output_str += "async def serve_spa(request: Request):\n"
        output_str += "    return templates.TemplateResponse('index.html', {'request': request})\n"
        return output_str
