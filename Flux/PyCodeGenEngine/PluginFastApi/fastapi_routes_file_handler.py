import os
import time
from abc import ABC
from typing import List, Dict, Tuple, Set
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    parse_string_to_original_types
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiRoutesFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.shared_lock_name_to_pydentic_class_dict: Dict[str, List[protogen.Message]] = {}
        self.shared_lock_name_message_list: List[protogen.Message] = []
        self.message_to_link_messages_dict: Dict[protogen.Message, List[protogen.Message]] = {}

    def _handle_routes_callback_import(self) -> str:
        routes_callback_path = self.import_path_from_os_path("OUTPUT_DIR", self.routes_callback_class_name)
        output_str = f"from {routes_callback_path} import {self.routes_callback_class_name_capital_camel_cased}\n"
        return output_str

    def _handle_routes_callback_instantiate(self):
        output_str = f"callback_class = {self.routes_callback_class_name_capital_camel_cased}.get_instance()\n\n\n"
        return output_str

    def _set_shared_lock_name_to_pydentic_class_dict(self):
        for message in self.root_message_list:
            # Setting lock for shared_lock option
            if FastapiRoutesFileHandler.flux_msg_crud_shared_lock in str(message.proto.options):
                shared_lock_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_crud_shared_lock)
                # removing quotation marks from lock_name
                shared_lock_name = shared_lock_name[1:-1]
                if shared_lock_name not in self.shared_lock_name_to_pydentic_class_dict:
                    self.shared_lock_name_to_pydentic_class_dict[shared_lock_name] = [message]
                else:
                    self.shared_lock_name_to_pydentic_class_dict[shared_lock_name].append(message)

                if message not in self.shared_lock_name_message_list:
                    self.shared_lock_name_message_list.append(message)
                # else not required: avoiding repetition
            # else not required: avoiding precess if message doesn't have shared_lock option set

            # setting shared lock for link messages
            linked_messages: List[protogen.Message] = self.message_to_link_messages_dict.get(message)
            if linked_messages is not None:
                linked_lock_name = f"{message.proto.name}_link_lock"
                self.shared_lock_name_to_pydentic_class_dict[linked_lock_name] = [message] + linked_messages

    def _get_messages_having_links(self) -> None:
        for message in self.root_message_list:
            linked_messages: Set = set()
            for field in message.fields:
                if FastapiRoutesFileHandler.flux_fld_collection_link in str(field.proto.options):
                    if field.message is not None:
                        linked_messages.add(field.message)
                    else:
                        err_str = f"Message can't be linked to non-root message, " \
                                  f"currently {message} is linked to {field.message}"
                        logging.exception(err_str)
                        raise Exception(err_str)
                # else not required: avoid if option not set

            if linked_messages:
                self.message_to_link_messages_dict[message] = list(linked_messages)

    def _get_list_of_shared_lock_for_message(self, message: protogen.Message) -> List[str]:
        shared_lock_name_list = []
        for shared_lock_name, message_list in self.shared_lock_name_to_pydentic_class_dict.items():
            if message in message_list:
                shared_lock_name_list.append(shared_lock_name)
        return shared_lock_name_list


    def _handle_model_imports(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import *\n"
        return output_str

    def _underlying_handle_generic_imports(self) -> str:
        generic_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_routes")
        output_str = f'from {generic_routes_file_path} import *\n'
        return output_str

    def _handle_underlying_mutex_str(self, message: protogen.Message, shared_lock_list: List[str]) -> Tuple[str, int]:
        output_str = ""
        if shared_lock_list:
            indent_times = 1
            for shared_lock in shared_lock_list:
                output_str += " " * (indent_times * 4) + f"async with {shared_lock}:\n"
                if shared_lock != shared_lock_list[-1]:
                    indent_times += 1
        else:
            indent_times = 0

        indent_count = indent_times*4
        if message not in self.reentrant_lock_non_required_msg:
            output_str += " "*indent_count + f"    async with {message.proto.name}.reentrant_lock:\n"
            indent_count = 4 + indent_count
        else:
            indent_count = 0 + indent_count

        return output_str, indent_count

    def handle_underlying_POST_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                                   id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += f"async def underlying_create_{message_name_snake_cased}_http({message_name_snake_cased}: " \
                      f"{message.proto.name}, filter_agg_pipeline: Any = None) -> {message.proto.name}:\n"
        output_str += f'    """\n'
        output_str += f'    Create route for {message.proto.name}\n'
        output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " " * indent_count + \
                      f"    await callback_class.create_{message_name_snake_cased}_pre({message_name_snake_cased})\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_post_http({message.proto.name}, " \
                      f"{message_name_snake_cased}, filter_agg_pipeline)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_post_http({message.proto.name}, " \
                              f"{message_name_snake_cased}, {self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_post_http({message.proto.name}, " \
                              f"{message_name_snake_cased}, update_agg_pipeline={update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_post_http({message.proto.name}, " \
                              f"{message_name_snake_cased}, {self._get_filter_configs_var_name(message)}, " \
                              f"{update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case other:
                output_str += " " * indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_post_http({message.proto.name}, " \
                              f"{message_name_snake_cased}, has_links={msg_has_links})\n"
        output_str += " " * indent_count + f"    await callback_class.create_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += " " * indent_count + f"    return {message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_POST_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                        id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_POST_gen(message, aggregation_type, id_field_type, shared_lock_list)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.post("/create-{message_name_snake_cased}' + \
                     f'", response_model={message.proto.name}, status_code=201)\n'
        output_str += f"async def create_{message_name_snake_cased}_http({message_name_snake_cased}: " \
                      f"{message.proto.name}) -> {message.proto.name}:\n"
        output_str += f"    return await underlying_create_{message_name_snake_cased}_http({message_name_snake_cased})\n"
        return output_str

    def handle_underlying_PUT_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                                  id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += f"async def underlying_update_{message_name_snake_cased}_http({message_name_snake_cased}_" \
                      f"updated: {message.proto.name}, filter_agg_pipeline: Any = None) -> {message.proto.name}:\n"
        output_str += f'    """\n'
        output_str += f'    Update route for {message.proto.name}\n'
        output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " "*indent_count + f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                      f"{message.proto.name}, {message_name_snake_cased}_updated.id, has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    {message_name_snake_cased}_updated = " \
                                         f"await callback_class.update_{message_name_snake_cased}_pre(" \
                      f"stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_obj = " \
                      f"await generic_put_http({message.proto.name}, " \
                      f"copy.deepcopy(stored_{message_name_snake_cased}_obj), {message_name_snake_cased}_updated, " \
                      f"filter_agg_pipeline)\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = await generic_put_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, {self._get_filter_configs_var_name(message)}, " \
                              f"has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = await generic_put_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, " \
                              f"update_agg_pipeline={update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = await generic_put_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, {self._get_filter_configs_var_name(message)}, " \
                              f"{update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case other:
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj = await generic_put_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    await callback_class.update_{message_name_snake_cased}_post(" \
                      f"stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
        output_str += " "*indent_count + f"    return updated_{message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_PUT_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                       id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PUT_gen(message, aggregation_type, id_field_type, shared_lock_list)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.put("/put-{message_name_snake_cased}' + \
                      f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}) -> {message.proto.name}:\n"
        output_str += f"    return await underlying_update_{message_name_snake_cased}_http(" \
                      f"{message_name_snake_cased}_updated)\n"
        return output_str

    def handle_underlying_PATCH_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                                    id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += f"async def underlying_partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}Optional, filter_agg_pipeline: Any = None) -> {message.proto.name}:\n"
        output_str += f'    """\n'
        output_str += f'    Partial Update route for {message.proto.name}\n'
        output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " "*indent_count + f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                      f"{message.proto.name}, {message_name_snake_cased}_updated.id, has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    {message_name_snake_cased}_updated = " \
                                         f"await callback_class.partial_update_{message_name_snake_cased}_pre(" \
                      f"stored_{message_name_snake_cased}_obj, {message_name_snake_cased}_updated)\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        updated_{message_name_snake_cased}_obj = await generic_patch_http(" \
                      f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                      f"{message_name_snake_cased}_updated, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj =  await generic_patch_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, {self._get_filter_configs_var_name(message)}, " \
                              f"has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj =  await generic_patch_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, " \
                              f"update_agg_pipeline={update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_both:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj =  await generic_patch_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, {self._get_filter_configs_var_name(message)}, " \
                              f"{update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case other:
                output_str += " "*indent_count + \
                              f"        updated_{message_name_snake_cased}_obj =  await generic_patch_http(" \
                              f"{message.proto.name}, copy.deepcopy(stored_{message_name_snake_cased}_obj), " \
                              f"{message_name_snake_cased}_updated, has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    await callback_class.partial_update_{message_name_snake_cased}_post(" \
                      f"stored_{message_name_snake_cased}_obj, updated_{message_name_snake_cased}_obj)\n"
        output_str += " "*indent_count + f"    return updated_{message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_PATCH_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                         id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_PATCH_gen(message, aggregation_type, id_field_type, shared_lock_list)
        output_str += f"\n"
        output_str += f'@{self.api_router_app_name}.patch("/patch-{message_name_snake_cased}' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        output_str += f"async def partial_update_{message_name_snake_cased}_http({message_name_snake_cased}_updated: " \
                      f"{message.proto.name}Optional) -> {message.proto.name}:\n"
        output_str += f'    return await underlying_partial_update_{message_name_snake_cased}_http(' \
                      f'{message_name_snake_cased}_updated)\n'
        return output_str

    def handle_underlying_DELETE_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                          id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        if id_field_type is not None:
            output_str += f"async def underlying_delete_{message_name_snake_cased}_http(" \
                         f"{message_name_snake_cased}_id: {id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def underlying_delete_{message_name_snake_cased}_http(" \
                         f"{message_name_snake_cased}_id: {BaseFastapiPlugin.default_id_type_var_name}" \
                         f") -> DefaultWebResponse:\n"
        output_str += f'    """\n'
        output_str += f'    Delete route for {message.proto.name}\n'
        output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " "*indent_count + f"    stored_{message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                      f"{message.proto.name}, {message_name_snake_cased}_id, has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    await callback_class.delete_{message_name_snake_cased}_pre(" \
                                         f"stored_{message_name_snake_cased}_obj)\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter | FastapiRoutesFileHandler.aggregation_type_both:
                err_str = "Filter Aggregation type is not supported in Delete operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case FastapiRoutesFileHandler.aggregation_type_update:
                update_agg_pipeline_var_name = \
                    self.get_non_repeated_valued_custom_option_value(message.proto.options,
                                                                     FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)
                output_str += " "*indent_count + \
                              f"    delete_web_resp = await generic_delete_http({message.proto.name}, " \
                              f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj, " \
                              f"{update_agg_pipeline_var_name[1:-1]}, has_links={msg_has_links})\n"
            case other:
                output_str += " "*indent_count + \
                              f"    delete_web_resp = await generic_delete_http({message.proto.name}, " \
                              f"{message.proto.name}BaseModel, stored_{message_name_snake_cased}_obj, " \
                              f"has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    await callback_class.delete_{message_name_snake_cased}_post(" \
                                         f"delete_web_resp)\n"
        output_str += " "*indent_count + f"    return delete_web_resp\n"
        output_str += "\n"
        return output_str

    def handle_DELETE_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                          id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_DELETE_gen(message, aggregation_type, id_field_type, shared_lock_list)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.delete("/delete-{message_name_snake_cased}/' + \
                      '{' + f'{message_name_snake_cased}_id' + '}' + \
                      f'", response_model=DefaultWebResponse, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id: {id_field_type}) -> DefaultWebResponse:\n"
        else:
            output_str += f"async def delete_{message_name_snake_cased}_http(" \
                          f"{message_name_snake_cased}_id: {BaseFastapiPlugin.default_id_type_var_name}) -> DefaultWebResponse:\n"
        output_str += f"    return await underlying_delete_{message_name_snake_cased}_http(" \
                      f"{message_name_snake_cased}_id)\n"
        return output_str

    def _get_filter_tuple_str(self, index_fields: List[protogen.Field]) -> str:
        filter_tuples_str = ""
        for field in index_fields:
            filter_tuples_str += f"('{field.proto.name}', {field.proto.name})"
            if field != index_fields[-1]:
                filter_tuples_str += ", "
        return filter_tuples_str

    def handle_underlying_index_req_gen(self, message: protogen.Message,
                                        shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index)]

        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])
        output_str = "@perf_benchmark\n"
        output_str += f"async def underlying_get_{message_name_snake_cased}_from_index_fields_http({field_params}, " \
                     f"filter_agg_pipeline: Any = None) -> List[{message.proto.name}]:\n"
        output_str += f'    """ Index route of {message.proto.name} """\n'
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " "*indent_count + f"    await callback_class.index_of_{message_name_snake_cased}_pre()\n"
        filter_configs_var_name = self._get_filter_configs_var_name(message)
        if filter_configs_var_name:
            output_str += " "*indent_count + f"    indexed_filter = copy.deepcopy({filter_configs_var_name})\n"
            output_str += " "*indent_count + \
                          f"    indexed_filter['match'] = [{self._get_filter_tuple_str(index_fields)}]\n"
        else:
            output_str += " "*indent_count + "    indexed_filter = {'match': " + \
                          f"[{self._get_filter_tuple_str(index_fields)}]" + "}\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_read_http({message.proto.name}, " \
                      f"filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        output_str += " "*indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_read_http({message.proto.name}, " \
                      f"indexed_filter, has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    await callback_class.index_of_{message_name_snake_cased}_post(" \
                      f"{message_name_snake_cased}_obj)\n"
        output_str += " "*indent_count + f"    return {message_name_snake_cased}_obj\n\n"
        return output_str

    def handle_index_req_gen(self, message: protogen.Message, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_index_req_gen(message, shared_lock_list)
        output_str += "\n"
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index)]

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

    def handle_underlying_index_ws_req_gen(self, message: protogen.Message,
                                        shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index)]

        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])
        output_str = f"async def underlying_get_{message_name_snake_cased}_from_index_fields_ws(websocket: WebSocket," \
                     f" {field_params}, filter_agg_pipeline: Any = None):\n"
        output_str += f'    """ Index route of {message.proto.name} """\n'
        output_str += f"    await callback_class.index_of_{message_name_snake_cased}_ws_pre()\n"
        filter_configs_var_name = self._get_filter_configs_var_name(message)
        if filter_configs_var_name:
            output_str += f"    indexed_filter = copy.deepcopy({filter_configs_var_name})\n"
            output_str += f"    indexed_filter['match'] = [{self._get_filter_tuple_str(index_fields)}]\n"
        else:
            output_str += "    indexed_filter = {'match': " + f"[{self._get_filter_tuple_str(index_fields)}]" + "}\n"
        output_str += f"    if filter_agg_pipeline is not None:\n"
        output_str += f"        await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                      f"{message.proto.name}, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += "    else:\n"
        output_str += f"        await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                      f"{message.proto.name}, indexed_filter, has_links={msg_has_links})\n"
        output_str += f"    await callback_class.index_of_{message_name_snake_cased}_ws_post()\n\n"
        return output_str

    def handle_index_ws_req_gen(self, message: protogen.Message, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_index_ws_req_gen(message, shared_lock_list)
        output_str += "\n"
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index)]

        field_query = "/".join(["{" + f"{field.proto.name}" + "}" for field in index_fields])
        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])

        output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}-from-index-fields-ws/' + \
                     f'{field_query}' + f'")\n'
        output_str += f"async def get_{message_name_snake_cased}_from_index_fields_ws(websocket: WebSocket, " \
                      f"{field_params}):\n"
        field_params = ", ".join([f"{field.proto.name}" for field in index_fields])
        output_str += \
            f"    await underlying_get_{message_name_snake_cased}_from_index_fields_ws(websocket, {field_params})\n\n\n"
        return output_str

    def handle_underlying_GET_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                       id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        if id_field_type is not None:
            output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                         f"{id_field_type}, filter_agg_pipeline: Any = None) -> {message.proto.name}:\n"
        else:
            output_str += f"async def underlying_read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                         f"{BaseFastapiPlugin.default_id_type_var_name}, " \
                         f"filter_agg_pipeline: Any = None) -> {message.proto.name}:\n"
        output_str += f'    """\n'
        output_str += f'    Read by id route for {message.proto.name}\n'
        output_str += f'    """\n'
        # else not required: avoiding if method desc not provided
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " "*indent_count + \
                      f"    await callback_class.read_by_id_{message_name_snake_cased}_pre({message_name_snake_cased}_id)\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        {message_name_snake_cased}_obj = await generic_read_by_id_http({message.proto.name}, " \
                      f"{message_name_snake_cased}_id, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += " "*indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                              f"{message.proto.name}, {message_name_snake_cased}_id, " \
                              f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update | FastapiRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in read by id operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " "*indent_count + \
                              f"        {message_name_snake_cased}_obj = await generic_read_by_id_http(" \
                              f"{message.proto.name}, {message_name_snake_cased}_id, has_links={msg_has_links})\n"

        output_str += " "*indent_count + f"    await callback_class.read_by_id_{message_name_snake_cased}_post({message_name_snake_cased}_obj)\n"
        output_str += " "*indent_count + f"    return {message_name_snake_cased}_obj\n"
        output_str += "\n"
        return output_str

    def handle_GET_gen(self, message: protogen.Message, aggregation_type: str | None = None,
                       id_field_type: str | None = None, shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_GET_gen(message, aggregation_type, id_field_type, shared_lock_list)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.get("/get-{message_name_snake_cased}/' + '{' + \
                     f'{message_name_snake_cased}_id' + '}' + \
                     f'", response_model={message.proto.name}, status_code=200)\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{id_field_type}) -> {message.proto.name}:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id: " \
                          f"{BaseFastapiPlugin.default_id_type_var_name}) -> {message.proto.name}:\n"
        output_str += \
            f"    return await underlying_read_{message_name_snake_cased}_by_id_http({message_name_snake_cased}_id)\n"
        return output_str

    def handle_underlying_GET_ws_gen(self, message: protogen.Message, aggregation_type: str,
                                     id_field_type, shared_lock_list: List[str] | None = None):
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        if id_field_type is not None:
            output_str = f"async def underlying_read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                         f"{message_name_snake_cased}_id: {id_field_type}, " \
                         f"filter_agg_pipeline: Any = None) -> None:\n"
        else:
            output_str = f"async def underlying_read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                         f"{message_name_snake_cased}_id: {BaseFastapiPlugin.default_id_type_var_name}, " \
                         f"filter_agg_pipeline: Any = None) -> None:\n"
        output_str += f'    """\n'
        output_str += f'    Read by id using websocket route for {message.proto.name}\n'
        output_str += f'    """\n'

        output_str += f"    await callback_class.read_by_id_ws_{message_name_snake_cased}_pre(" \
                      f"{message_name_snake_cased}_id)\n"
        output_str += f"    if filter_agg_pipeline is not None:\n"
        output_str += f"        await generic_read_by_id_ws(websocket, " \
                      f"{BaseFastapiPlugin.proto_package_var_name}, " \
                      f"{message_name}, {message_name_snake_cased}_id, filter_agg_pipeline, " \
                      f"has_links={msg_has_links})\n"
        output_str += "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += \
                              f"        await generic_read_by_id_ws(websocket, " \
                              f"{BaseFastapiPlugin.proto_package_var_name}, " \
                              f"{message_name}, {message_name_snake_cased}_id, " \
                              f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update | FastapiRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in read by id operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += \
                              f"        await generic_read_by_id_ws(websocket, " \
                              f"{BaseFastapiPlugin.proto_package_var_name}, " \
                              f"{message_name}, {message_name_snake_cased}_id, has_links={msg_has_links})\n"
        output_str += f"    await callback_class.read_by_id_ws_{message_name_snake_cased}_post()\n"
        output_str += "\n"
        return output_str

    def handle_GET_ws_gen(self, message: protogen.Message, aggregation_type: str, id_field_type,
                          shared_lock_list: List[str] | None = None):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = self.handle_underlying_GET_ws_gen(message, aggregation_type, id_field_type, shared_lock_list)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.websocket("/get-{message_name_snake_cased}-ws/' + \
                     '{' + f'{message_name_snake_cased}_id' + '}")\n'
        if id_field_type is not None:
            output_str += f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                          f"{message_name_snake_cased}_id: {id_field_type}) -> None:\n"
        else:
            output_str += f"async def read_{message_name_snake_cased}_by_id_ws(websocket: WebSocket, " \
                          f"{message_name_snake_cased}_id: {BaseFastapiPlugin.default_id_type_var_name}) -> None:\n"
        output_str += f"    await underlying_read_{message_name_snake_cased}_by_id_ws(websocket, " \
                      f"{message_name_snake_cased}_id)\n"
        return output_str

    def handle_underlying_GET_ALL_gen(self, message: protogen.Message, aggregation_type: str,
                                      shared_lock_list: List[str] | None = None) -> str:
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = "@perf_benchmark\n"
        output_str += f"async def underlying_read_{message_name_snake_cased}_http(" \
                     f"filter_agg_pipeline: Any = None) -> List[{message.proto.name}]:\n"
        output_str += f'    """\n'
        output_str += f'    Get All route for {message.proto.name}\n'
        output_str += f'    """\n'
        mutex_handling_str, indent_count = self._handle_underlying_mutex_str(message, shared_lock_list)

        output_str += mutex_handling_str
        output_str += " "*indent_count + f"    await callback_class.read_all_{message_name_snake_cased}_pre()\n"
        output_str += " " * indent_count + f"    if filter_agg_pipeline is not None:\n"
        output_str += " " * indent_count + \
                      f"        obj_list = await generic_read_http({message.proto.name}, filter_agg_pipeline, " \
                      f"has_links={msg_has_links})\n"
        output_str += " " * indent_count + "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += " "*indent_count + \
                              f"        obj_list = await generic_read_http({message.proto.name}, " \
                              f"{self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update | FastapiRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in real all operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += " "*indent_count + \
                              f"        obj_list = await generic_read_http({message.proto.name}, " \
                              f"has_links={msg_has_links})\n"
        output_str += " "*indent_count + f"    await callback_class.read_all_{message_name_snake_cased}_post(obj_list)\n"
        output_str += " "*indent_count + f"    return obj_list\n\n"
        return output_str

    def handle_GET_ALL_gen(self, message: protogen.Message, aggregation_type: str,
                           shared_lock_list: List[str] | None = None) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        output_str = self.handle_underlying_GET_ALL_gen(message, aggregation_type, shared_lock_list)
        output_str += "\n"
        output_str += f'@{self.api_router_app_name}.get("/get-all-{message_name_snake_cased}' + \
                      f'", response_model=List[{message.proto.name}], status_code=200)\n'
        output_str += f"async def read_{message_name_snake_cased}_http() -> List[{message.proto.name}]:\n"
        output_str += f"    return await underlying_read_{message_name_snake_cased}_http()\n\n\n"
        return output_str

    def handle_underlying_GET_ALL_ws_gen(self, message: protogen.Message, aggregation_type: str,
                                         shared_lock_list: List[str] | None = None):
        msg_has_links: bool = message in self.message_to_link_messages_dict
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f"async def underlying_read_{message_name_snake_cased}_ws(websocket: WebSocket, " \
                     f"filter_agg_pipeline: Any = None) -> None:\n"
        output_str += f'    """ Get All {message_name} using websocket """\n'

        output_str += f"    await callback_class.read_all_ws_{message_name_snake_cased}_pre()\n"
        output_str += f"    if filter_agg_pipeline is not None:\n"
        output_str += f"        await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                      f"{message_name}, filter_agg_pipeline, has_links={msg_has_links})\n"
        output_str += "    else:\n"
        match aggregation_type:
            case FastapiRoutesFileHandler.aggregation_type_filter:
                output_str += \
                              f"        await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                              f"{message_name}, {self._get_filter_configs_var_name(message)}, has_links={msg_has_links})\n"
            case FastapiRoutesFileHandler.aggregation_type_update | FastapiRoutesFileHandler.aggregation_type_both:
                err_str = "Update Aggregation type is not supported in real all websocket operations, " \
                          f"but aggregation type {aggregation_type} received in message {message.proto.name}"
                logging.exception(err_str)
                raise Exception(err_str)
            case other:
                output_str += \
                              f"        await generic_read_ws(websocket, {BaseFastapiPlugin.proto_package_var_name}, " \
                              f"{message_name}, has_links={msg_has_links})\n"
        output_str += f"    await callback_class.read_all_ws_{message_name_snake_cased}_post()\n\n"
        return output_str

    def handle_GET_ALL_ws_gen(self, message: protogen.Message, aggregation_type: str,
                              shared_lock_list: List[str] | None = None):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = self.handle_underlying_GET_ALL_ws_gen(message, aggregation_type, shared_lock_list)
        output_str += f"\n"
        output_str += f'@{self.api_router_app_name}.websocket("/get-all-{message_name_snake_cased}-ws")\n'
        output_str += f"async def read_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        output_str += f"    await underlying_read_{message_name_snake_cased}_ws(websocket)\n\n\n"
        return output_str

    def handle_update_WEBSOCKET_gen(self, message: protogen.Message, method_desc: str, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'@{self.api_router_app_name}.websocket("/update-{message_name_snake_cased}-ws/")\n'
        output_str += f"async def update_{message_name_snake_cased}_ws(websocket: WebSocket) -> None:\n"
        if method_desc:
            output_str += f'    """ {method_desc} """\n'
        output_str += f"    await generic_update_ws(websocket, {message_name})\n"
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
        output_str += f"    print({field_name})\n"
        output_str += f"    while True:\n"
        output_str += f"        data = await websocket.receive()\n"
        output_str += f"        await websocket.send(data)\n\n\n"
        return output_str

    def _get_filter_configs_var_name(self, message: protogen.Message) -> str:
        filter_option_val_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_nested_fld_val_filter_param)
        field_name_list = []
        for filter_option_dict in filter_option_val_list_of_dict:
            if "field_name" in filter_option_dict:
                field_name = filter_option_dict["field_name"]
                field_name_list.append(field_name)
        if field_name_list:
            return_str = "_n_".join(field_name_list)
            if BaseFastapiPlugin.flux_msg_main_crud_operations_agg in str(message.proto.options):
                additional_agg_option_val_list_of_dict = \
                    self.get_complex_option_values_as_list_of_dict(message,
                                                                   BaseFastapiPlugin.flux_msg_main_crud_operations_agg)
                additional_agg_name = additional_agg_option_val_list_of_dict[0]["agg_var_name"]
                return_str += f"_n_{additional_agg_name}"
            return_str += "_filter_config"
            return return_str
        elif BaseFastapiPlugin.flux_msg_main_crud_operations_agg in str(message.proto.options):
            return f"{message.proto.name}_limit_filter_config"
        else:
            return ""

    def _set_filter_config_vars(self, message: protogen.Message) -> str:
        filter_list = []
        filter_option_val_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_nested_fld_val_filter_param)
        for filter_option_dict in filter_option_val_list_of_dict:
            temp_list = []
            if "field_name" in filter_option_dict:
                field_name = filter_option_dict["field_name"]
                temp_list.append(field_name)
                if "bool_val_filters" in filter_option_dict:
                    if not isinstance(filter_option_dict["bool_val_filters"], list):
                        filter_option_dict["bool_val_filters"] = [filter_option_dict["bool_val_filters"]]
                    # else not required: if filter_option_dict["bool_val_filters"] already os list type then
                    # avoiding type-casting
                    temp_list.extend(filter_option_dict["bool_val_filters"])
                elif "string_val_filters" in filter_option_dict:
                    if not isinstance(filter_option_dict["string_val_filters"], list):
                        filter_option_dict["string_val_filters"] = [filter_option_dict["string_val_filters"]]
                    # else not required: if filter_option_dict["string_val_filters"] already os list type then
                    # avoiding type-casting
                    temp_list.extend(filter_option_dict["string_val_filters"])
                else:
                    err_str = f"No valid val_filter option field found in filter option for filter field: {field_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)

                filter_list.append(tuple(temp_list))

            else:
                err_str = f"No filter field_name key found in filter option: {filter_option_val_list_of_dict}"
                logging.exception(err_str)
                raise Exception(err_str)

        additional_agg_str = ""
        if self.flux_msg_main_crud_operations_agg in str(message.proto.options):
            additional_agg_option_val_list_of_dict = \
                self.get_complex_option_values_as_list_of_dict(message,
                                                               BaseFastapiPlugin.flux_msg_main_crud_operations_agg)[0]

            agg_params = additional_agg_option_val_list_of_dict["agg_params"]
            if isinstance(agg_params, list):
                type_casted_agg_params = [str(parse_string_to_original_types(param)) for param in agg_params]
                agg_params = ", ".join(type_casted_agg_params)
            else:
                agg_params = parse_string_to_original_types(agg_params)

            additional_agg_str = f"{additional_agg_option_val_list_of_dict['agg_var_name']}({agg_params})"
        # else not required: by-passing if option not used

        if filter_list:
            var_name = self._get_filter_configs_var_name(message)
            return_str = f"{var_name}: Final[Dict[str, Any]] = " + "{'redact': " + f"{filter_list}"
            if additional_agg_str:
                return_str += f", 'agg': {additional_agg_str}"
            return_str += "}\n"
            return return_str
        elif additional_agg_str:
            var_name = self._get_filter_configs_var_name(message)
            return_str = f"{var_name}: Final[Dict[str, Any]] = " + "{'agg': " + f"{additional_agg_str}" + "}\n"
            return return_str
        else:
            return ""

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
            case FastapiRoutesFileHandler.aggregation_type_both:
                if not ((FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name in str(message.proto.options) or
                         FastapiRoutesFileHandler.flux_msg_main_crud_operations_agg in str(message.proto.options)) and
                        FastapiRoutesFileHandler.flux_msg_nested_fld_val_filter_param in str(message.proto.options)):
                    err_str += f"{aggregation_type} but not has" \
                               f"both {FastapiRoutesFileHandler.flux_msg_nested_fld_val_filter_param} and " \
                               f"{FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name} options set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiRoutesFileHandler.aggregation_type_filter:
                if not (FastapiRoutesFileHandler.flux_msg_nested_fld_val_filter_param in str(message.proto.options) or
                        FastapiRoutesFileHandler.flux_msg_main_crud_operations_agg in str(message.proto.options)):
                    err_str += f"{aggregation_type} but not has" \
                               f"{FastapiRoutesFileHandler.flux_msg_nested_fld_val_filter_param} option set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiRoutesFileHandler.aggregation_type_update:
                if FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name not in str(message.proto.options):
                    err_str += f"{aggregation_type} but not has " \
                               f"{FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name} option set, " \
                               f"Please check if json_root fields are set to specified if no " \
                               f"{FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name} option is set"
                    logging.exception(err_str)
                    raise Exception(err_str)
            case FastapiRoutesFileHandler.aggregation_type_unspecified:
                pass
            case other:
                err_str = f"Unsupported option field {other} in json_root option"
                logging.exception(err_str)
                raise Exception(err_str)
        return aggregation_type

    def _handle_routes_methods(self, message: protogen.Message) -> str:
        output_str = ""
        crud_field_name_to_method_call_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: self.handle_POST_gen,
            BaseFastapiPlugin.flux_json_root_read_field: self.handle_GET_gen,
            BaseFastapiPlugin.flux_json_root_update_field: self.handle_PUT_gen,
            BaseFastapiPlugin.flux_json_root_patch_field: self.handle_PATCH_gen,
            BaseFastapiPlugin.flux_json_root_delete_field: self.handle_DELETE_gen,
            BaseFastapiPlugin.flux_json_root_read_websocket_field: self.handle_GET_ws_gen,
            BaseFastapiPlugin.flux_json_root_update_websocket_field: self.handle_update_WEBSOCKET_gen
        }

        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message, BaseFastapiPlugin.flux_msg_json_root)

        shared_mutex_list = self._get_list_of_shared_lock_for_message(message)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]
        if (aggregation_type := option_dict.get(BaseFastapiPlugin.flux_json_root_read_field)) is not None:
            output_str += self.handle_GET_ALL_gen(message, aggregation_type.strip(), shared_mutex_list)
        # else not required: avoiding find_all route for this message if read_field of json_root option is not set

        if (aggregation_type := option_dict.get(BaseFastapiPlugin.flux_json_root_read_websocket_field)) is not None:
            output_str += \
                self.handle_GET_ALL_ws_gen(message, aggregation_type.strip(), shared_mutex_list)
        # else not required: avoiding find_all route for this message if read_ws_field of json_root option is not set

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                aggregation_type: str = self._check_agg_info_availability(option_dict[crud_option_field_name].strip(),
                                                                          crud_option_field_name,
                                                                          message)
                output_str += crud_operation_method(message, aggregation_type, id_field_type, shared_mutex_list)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_web_socket):
                output_str += self.handle_field_web_socket_gen(message, field)
            # else not required: Avoiding field if websocket option is not enabled

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index):
                output_str += self.handle_index_req_gen(message, shared_mutex_list)
                output_str += self.handle_index_ws_req_gen(message, shared_mutex_list)
                break
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def _handle_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]

        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
        for aggregate_value in aggregate_value_list:
            aggregate_var_name = aggregate_value[FastapiRoutesFileHandler.aggregate_var_name_key]
            aggregate_params = aggregate_value[FastapiRoutesFileHandler.aggregate_params_key]
            aggregate_params_data_types = aggregate_value[FastapiRoutesFileHandler.aggregate_params_data_types_key]

            if aggregate_params:
                param_to_type_str_list = []
                list_type_params = []
                for param, param_type in zip(aggregate_params, aggregate_params_data_types):
                    if "List" not in param_type:
                        param_to_type_str_list.append(f"{param}: {param_type}")
                    else:
                        list_type_params.append((param, param_type))
                for param, param_type in list_type_params:
                    param_to_type_str_list.append(f"{param}: {param_type} = Query()")
                agg_params_with_type_str = ", ".join(param_to_type_str_list)
                agg_params_str = ", ".join(aggregate_params)

                output_str += "@perf_benchmark\n"
                output_str += f"async def underlying_{aggregate_var_name}_query_http({agg_params_with_type_str}) -> " \
                             f"List[{message.proto.name}]:\n"
                output_str += f"    {message_name_snake_cased}_obj = await " \
                              f"callback_class.{aggregate_var_name}_query_pre({message.proto.name}, {agg_params_str})\n"
                output_str += f"    {message_name_snake_cased}_obj = await " \
                              f"callback_class.{aggregate_var_name}_query_post({message_name_snake_cased}_obj)\n"
                output_str += f"    return {message_name_snake_cased}_obj\n\n\n"
                output_str += f'@{self.api_router_app_name}.get("/query-{aggregate_var_name}' + \
                              f'", response_model=List[{message.proto.name}], status_code=200)\n'
                output_str += f"async def {aggregate_var_name}_query_http({agg_params_with_type_str}) -> " \
                              f"List[{message.proto.name}]:\n"
                output_str += f'    """\n'
                output_str += f'    Query of {message.proto.name} with aggregate - {aggregate_var_name}\n'
                output_str += f'    """\n'
                output_str += f"    return await underlying_{aggregate_var_name}_query_http({agg_params_str})"
                output_str += "\n\n\n"
            else:
                output_str += "@perf_benchmark\n"
                output_str += f"async def underlying_{aggregate_var_name}_query_http() -> " \
                              f"List[{message.proto.name}]:\n"
                output_str += f"    {message_name_snake_cased}_obj = await callback_class.{aggregate_var_name}_" \
                              f"query_pre({message.proto.name})\n"
                output_str += f"    await callback_class.{aggregate_var_name}_query_post(" \
                              f"{message_name_snake_cased}_obj)\n"
                output_str += f"    return {message_name_snake_cased}_obj\n\n\n"
                output_str += f'@{self.api_router_app_name}.get("/query-{aggregate_var_name}' + \
                              f'", response_model=List[{message.proto.name}], status_code=200)\n'
                output_str += f"async def {aggregate_var_name}_query_http() -> " \
                              f"List[{message.proto.name}]:\n"
                output_str += f'    """\n'
                output_str += f'    Query of {message.proto.name} with aggregate - {aggregate_var_name}\n'
                output_str += f'    """\n'
                output_str += f'    return await underlying_{aggregate_var_name}_query_http()\n'

                output_str += "\n\n"

        return output_str

    def handle_CRUD_task(self) -> str:
        output_str = ""
        for message in self.root_message_list:
            if BaseFastapiPlugin.flux_msg_json_root in str(message.proto.options):
                output_str += self._handle_routes_methods(message)

        for message in self.root_message_list + self.non_root_message_list:
            if BaseFastapiPlugin.flux_msg_json_query in str(message.proto.options):
                output_str += self._handle_query_methods(message)

        return output_str

    def _get_aggregate_query_var_list(self) -> List[str]:
        agg_query_var_list = []
        for message in self.root_message_list:
            if FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name in str(message.proto.options):
                agg_query_var_list.append(
                    self.get_non_repeated_valued_custom_option_value(
                        message.proto.options,
                        FastapiRoutesFileHandler.flux_msg_aggregate_query_var_name)[1:-1])
        # else not required: if no message is found with agg_query option then returning empty list
        return agg_query_var_list

    def _handle_CRUD_shared_locks_declaration(self):
        output_str = ""
        for lock_name in self.shared_lock_name_to_pydentic_class_dict:
            output_str += f"{lock_name} = AsyncRLock()\n"
        return output_str

    def handle_routes_file_gen(self) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_pydentic_class_dict()

        output_str = "# python standard modules\n"
        output_str += "from typing import List, Any, Dict, Final\n"
        output_str += "import copy\n"
        output_str += "# third-party modules\n"
        output_str += "from fastapi import APIRouter, Request, WebSocket, Query\n"
        output_str += "from fastapi.templating import Jinja2Templates\n"
        output_str += "# project imports\n"
        output_str += self._handle_routes_callback_import()
        output_str += self._handle_model_imports()
        output_str += self._underlying_handle_generic_imports()
        incremental_id_basemodel_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                      "incremental_id_basemodel")
        if self.response_field_case_style.lower() == "camel":
            output_str += f'from {incremental_id_basemodel_path} import to_camel\n'
        # else not required: if response type is not camel type then avoid import
        default_web_response_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "default_web_response")
        output_str += f'from {default_web_response_file_path} import DefaultWebResponse\n'
        output_str += f"from FluxPythonUtils.scripts.utility_functions import perf_benchmark\n"
        output_str += f"from FluxPythonUtils.scripts.async_rlock import AsyncRLock\n"
        aggregate_file_path = self.import_path_from_os_path("PROJECT_DIR", "app.aggregate")
        output_str += f'from {aggregate_file_path} import *'

        output_str += f"\n\n"
        temp_list = []  # used to prevent code repetition
        for message in self.root_message_list:
            filter_config_var_declaration = self._set_filter_config_vars(message)
            if filter_config_var_declaration not in temp_list:
                output_str += filter_config_var_declaration
                temp_list.append(filter_config_var_declaration)
            # else not required: preventing if declaration already added
        output_str += self._handle_CRUD_shared_locks_declaration()
        output_str += f"{self.api_router_app_name} = APIRouter()\n"
        output_str += self._handle_routes_callback_instantiate()
        output_str += self.handle_CRUD_task()
        output_str += "\n\ntemplates = Jinja2Templates(directory='templates')\n\n"
        output_str += f"@{self.api_router_app_name}.get('/')\n"
        output_str += "async def serve_spa(request: Request):\n"
        output_str += "    return templates.TemplateResponse('index.html', {'request': request})\n"
        return output_str
