# standard imports
from abc import ABC
from typing import List, Dict, Tuple

# 3rd party imports
import protogen
from pathlib import PurePath

# project imports
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin
from FluxPythonUtils.scripts.utility_functions import (convert_camel_case_to_specific_case,
                                                       convert_to_capitalized_camel_case)
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import (
    project_dir, root_core_proto_files, project_grp_core_proto_files)


class FastapiWSClientFileHandler(BaseFastapiPlugin, ABC):
    orm_model_dir_name = "ORMModel"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_imports_output(self, file: protogen.File | None = None,
                              model_file_suffix: str| None = None) -> str:
        output_str = "# standard imports\n"
        output_str += "\n"
        output_str += "# project imports\n"
        output_str += "from FluxPythonUtils.scripts.ws_reader import WSReader\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"

        if file and model_file_suffix:
            project_grp_root_dir = PurePath(project_dir).parent.parent / "ORMModel"
            dependency_file_path_list = self.get_dependency_file_path_list(
                file, root_core_proto_files, project_grp_core_proto_files,
                model_file_suffix, str(project_grp_root_dir))

            project_name = file.proto.package
            for dependency_file_path in dependency_file_path_list:
                if f"_n_{project_name}" in dependency_file_path or f"{project_name}_n_" in dependency_file_path:
                    output_str += f'from {dependency_file_path} import *\n'
        output_str += "\n\n"
        return output_str

    def _handle_client_query_ws_url(self, file: protogen.File, message: protogen.Message):
        output_str = ""

        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiWSClientFileHandler.query_name_key]
            query_type = str(aggregate_value[FastapiWSClientFileHandler.query_type_key]).lower() \
                if aggregate_value[FastapiWSClientFileHandler.query_type_key] is not None else None

            if query_type == "ws" or query_type == "both":
                url = (f"self.ws_query_{query_name}_url: str = " + "f'{self." + f'{file.proto.package}' +
                       '_base_url}' + f"/ws-query-{query_name}'")
                output_str += f"\t\t{url}\n"
        return output_str

    def _handle_client_projection_query_ws_url(self, file: protogen.File, message: protogen.Message) -> str:
        output_str = ""
        if FastapiWSClientFileHandler.is_option_enabled(message,
                                                        FastapiWSClientFileHandler.flux_msg_json_root_time_series):
            for field in message.fields:
                if FastapiWSClientFileHandler.is_option_enabled(
                        field, FastapiWSClientFileHandler.flux_fld_projections):
                    break
            else:
                # If no field is found having projection enabled
                return output_str

            projection_val_to_query_name_dict = (
                FastapiWSClientFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
            for temp_query_name, query_name in projection_val_to_query_name_dict.items():
                url = (f"self.{query_name}_ws_query_url: str = " + "f'{self." + f'{file.proto.package}' +
                       '_base_url}' + f"/ws-query-{query_name}'")
                output_str += f"\t\t{url}\n"

        return output_str

    def ws_uri_handler(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.root_message_list:
            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            output_str += f'\t\tself.{message_name_snake_cased}_ws_get_all_uri: str = f"' + \
                          '{self.' + f'{file.proto.package}' + '_base_url}' + \
                          f'/get-all-{message_name_snake_cased}-ws"\n'

            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message, FastapiWSClientFileHandler.flux_msg_json_root))
            else:
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message,
                                                             FastapiWSClientFileHandler.flux_msg_json_root_time_series))

            if BaseFastapiPlugin.flux_json_root_read_by_id_websocket_field in  option_value_dict:
                output_str += (f"\t\tself.{message_name_snake_cased}_" + f"ws_get_by_id_uri: " +
                               "str = f'{self." + f'{file.proto.package}' + '_base_url}' +
                               f"/get-" + f"{message_name_snake_cased}-ws'\n")

            output_str += self._handle_client_projection_query_ws_url(file, message)

        for message in set(self.root_message_list+list(self.message_to_query_option_list_dict)):
            if message in self.message_to_query_option_list_dict:
                output_str += self._handle_client_query_ws_url(file, message)

        return output_str

    def _projection_query_ws_client_methods_generation(self, message: protogen.Message):
        output_str = ""
        if FastapiWSClientFileHandler.is_option_enabled(message,
                                                        FastapiWSClientFileHandler.flux_msg_json_root_time_series):
            for field in message.fields:
                if FastapiWSClientFileHandler.is_option_enabled(
                        field, FastapiWSClientFileHandler.flux_fld_projections):
                    break
            else:
                # If no field is found having projection enabled
                return output_str

            projection_val_to_query_name_dict = (
                FastapiWSClientFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
            meta_data_field_name_to_field_tuple_dict: Dict[str, Tuple[str, protogen.Field] |
                                                                Dict[str, Tuple[str, protogen.Field]]] = (
                self.get_meta_data_field_name_to_type_str_dict(message))
            for temp_query_name, query_name in projection_val_to_query_name_dict.items():
                projection_val_to_fields_dict = (
                    FastapiWSClientFileHandler.get_projection_option_value_to_fields(message))

                field_name_list: List[str] = []
                field_name_set = projection_val_to_fields_dict[temp_query_name]
                for field_name in field_name_set:
                    if "." in field_name:
                        field_name_list.append("_".join(field_name.split(".")))
                    else:
                        field_name_list.append(field_name)
                field_names_str = "_n_".join(field_name_list)
                field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)

                container_model_name = f"{message.proto.name}ProjectionContainerFor{field_names_str_camel_cased}"

                query_params_dict = "{"
                query_params_str = ""
                for meta_field_name, meta_field_info in meta_data_field_name_to_field_tuple_dict.items():
                    if isinstance(meta_field_info, dict):
                        for nested_meta_field_name, nested_meta_field_info in meta_field_info.items():
                            nested_meta_field_type, _ = nested_meta_field_info
                            query_params_dict += f'"{nested_meta_field_name}": {nested_meta_field_name}, '
                            query_params_str += (f"{nested_meta_field_name}: "
                                                 f"{nested_meta_field_type}, ")
                    else:
                        meta_field_type, _ = meta_field_info
                        query_params_dict += f'"{meta_field_name}": {meta_field_name}, '
                        query_params_str += f"{meta_field_name}: {meta_field_type}, "
                query_params_dict += '"start_date_time": start_date_time, "end_date_time": end_date_time}'
                query_params_str += "start_date_time: DateTime | None = None, end_date_time: DateTime | None = None"
                output_str += (f'\tdef {query_name}_ws_client(self, notify: bool, {query_params_str}, '
                               f'need_initial_snapshot: bool | None = True) -> WSReader:\n')
                output_str += f"\t\tquery_kwargs = {query_params_dict}\n"
                output_str += f'\t\tif need_initial_snapshot is not None:\n'
                output_str += f'\t\t\tquery_kwargs["need_initial_snapshot"] = str(need_initial_snapshot).lower()\n'
                output_str += ("\t\tquery_kwargs = jsonable_encoder(query_kwargs, exclude_none=True)   "
                               "# removes none values from dict\n")
                output_str += (f'\t\tws_reader_obj = WSReader(self.{query_name}_ws_query_url, {container_model_name}, '
                               f'{container_model_name}List, self.handle_{query_name}_ws, '
                               f'query_kwargs, notify=notify)\n')
                output_str += f"\t\treturn ws_reader_obj\n\n"
        return output_str

    def _projection_query_ws_handler_method_generation(self, message: protogen.Message):
        output_str = ""
        if FastapiWSClientFileHandler.is_option_enabled(message,
                                                        FastapiWSClientFileHandler.flux_msg_json_root_time_series):
            for field in message.fields:
                if FastapiWSClientFileHandler.is_option_enabled(
                        field, FastapiWSClientFileHandler.flux_fld_projections):
                    break
            else:
                # If no field is found having projection enabled
                return output_str

            projection_val_to_query_name_dict = (
                FastapiWSClientFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
            for temp_query_name, query_name in projection_val_to_query_name_dict.items():
                projection_val_to_fields_dict = (
                    FastapiWSClientFileHandler.get_projection_option_value_to_fields(message))

                field_name_list: List[str] = []
                field_name_set = projection_val_to_fields_dict[temp_query_name]
                for field_name in field_name_set:
                    if "." in field_name:
                        field_name_list.append("_".join(field_name.split(".")))
                    else:
                        field_name_list.append(field_name)
                field_names_str = "_n_".join(field_name_list)
                field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)

                container_model_name = f"{message.proto.name}ProjectionContainerFor{field_names_str_camel_cased}"
                container_model_name_snake_cased = convert_camel_case_to_specific_case(container_model_name)

                output_str += (f'\tdef handle_{query_name}_ws(self, '
                               f'{container_model_name_snake_cased}_: {container_model_name}, **kwargs):\n')
                output_str += f"\t\tprint({container_model_name_snake_cased}_)\n\n"
        return output_str

    def _client_query_ws_client_methods_generation(self, message: protogen.Message):
        output_str = ""

        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiWSClientFileHandler.query_name_key]
            query_params = aggregate_value[FastapiWSClientFileHandler.query_params_key]
            query_type = str(aggregate_value[FastapiWSClientFileHandler.query_type_key]).lower() \
                if aggregate_value[FastapiWSClientFileHandler.query_type_key] is not None else None

            # query_param_name_n_param_type_list = []
            query_params_name_list = []
            if query_params:
                for query_param_name, _ in query_params:
                    query_params_name_list.append(query_param_name)

            params_str = ", ".join([f"{aggregate_param}: {aggregate_params_type}"
                                    for aggregate_param, aggregate_params_type in query_params])
            if query_type == "ws" or query_type == "both":
                output_str += (f'\tdef query_{query_name}_ws_client(self, notify: bool, {params_str}, '
                               f'need_initial_snapshot: bool | None = True) -> WSReader:\n')
                params_dict_str = \
                    ', '.join([f'"{aggregate_param}": {aggregate_param}' for aggregate_param in query_params_name_list])
                output_str += "\t\tquery_kwargs = {" + f"{params_dict_str}" + "}\n"
                output_str += f'\t\tif need_initial_snapshot is not None:\n'
                output_str += f'\t\t\tquery_kwargs["need_initial_snapshot"] = str(need_initial_snapshot).lower()\n'
                output_str += ("\t\tquery_kwargs = jsonable_encoder(query_kwargs, exclude_none=True)   "
                               "# removes none values from dict\n")
                output_str += (f'\t\tws_reader_obj = WSReader(self.ws_query_{query_name}_url, '
                               f'{message.proto.name}BaseModel, {message.proto.name}BaseModelList, '
                               f'self.handle_query_{query_name}_ws, query_kwargs, notify=notify)\n')
                output_str += f"\t\treturn ws_reader_obj\n\n"
        return output_str

    def ws_reader_client_methods_generation(self):
        output_str = ""
        for message in self.root_message_list:
            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            output_str += (f'\tdef {message_name_snake_cased}_ws_get_all_client(self, notify: bool, '
                           f'need_initial_snapshot: bool | None = True, '
                           f'limit_obj_count: int | None = None) -> WSReader:\n')
            output_str += f'\t\tif need_initial_snapshot is not None:\n'
            output_str += (f'\t\t\tself.{message_name_snake_cased}_ws_get_all_uri += '
                           f'"?need_initial_snapshot=" + str(need_initial_snapshot).lower()\n')
            output_str += f'\t\tif limit_obj_count is not None:\n'
            output_str += f'\t\t\tif need_initial_snapshot is not None:\n'
            output_str += (f'\t\t\t\tself.{message_name_snake_cased}_ws_get_all_uri += '
                           f'"&limit_obj_count=" + '+'str(limit_obj_count)\n')
            output_str += f'\t\t\telse:\n'
            output_str += (f'\t\t\t\tself.{message_name_snake_cased}_ws_get_all_uri += '
                           f'"?limit_obj_count=" + ' + 'str(limit_obj_count)\n')
            output_str += (f'\t\tws_reader_obj = WSReader(self.{message_name_snake_cased}_ws_get_all_uri, '
                           f'{message.proto.name}BaseModel, {message.proto.name}BaseModelList, '
                           f'self.handle_{message_name_snake_cased}_get_all_ws, notify=notify)\n')
            output_str += f"\t\treturn ws_reader_obj\n\n"

            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message, FastapiWSClientFileHandler.flux_msg_json_root))
            else:
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message,
                                                             FastapiWSClientFileHandler.flux_msg_json_root_time_series))

            if BaseFastapiPlugin.flux_json_root_read_by_id_websocket_field in option_value_dict:
                output_str += (f'\tdef {message_name_snake_cased}_ws_get_by_id_client(self, notify: bool, '
                               f'{message_name_snake_cased}_id: Any, need_initial_snapshot: bool | None = True'
                               f') -> WSReader:\n')
                output_str += f'\t\tif self.{message_name_snake_cased}_ws_get_by_id_uri.endswith("/"):\n'
                output_str += (f'\t\t\tself.{message_name_snake_cased}_ws_get_by_id_uri += '
                               f'str({message_name_snake_cased}_id)\n')
                output_str += f'\t\telse:\n'
                output_str += (f'\t\t\tself.{message_name_snake_cased}_ws_get_by_id_uri += '
                               f'"/" + str({message_name_snake_cased}_id)\n')
                output_str += f'\t\tif need_initial_snapshot is not None:\n'
                output_str += (f'\t\t\tself.{message_name_snake_cased}_ws_get_by_id_uri += '
                               f'"?need_initial_snapshot=" + str(need_initial_snapshot).lower()\n')
                output_str += (f'\t\tws_reader_obj = WSReader(self.{message_name_snake_cased}_ws_get_by_id_uri, '
                               f'{message.proto.name}BaseModel, {message.proto.name}BaseModelList, '
                               f'self.handle_{message_name_snake_cased}_get_by_id_ws, notify=notify)\n')
            output_str += f"\t\treturn ws_reader_obj\n\n"

            output_str += self._projection_query_ws_client_methods_generation(message)

        for message in set(self.root_message_list+list(self.message_to_query_option_list_dict)):
            if message in self.message_to_query_option_list_dict:
                output_str += self._client_query_ws_client_methods_generation(message)

        return output_str

    def _client_query_ws_handler_method_generation(self, message: protogen.Message):
        output_str = ""

        aggregate_value_list = self.message_to_query_option_list_dict[message]
        message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiWSClientFileHandler.query_name_key]
            query_type = str(aggregate_value[FastapiWSClientFileHandler.query_type_key]).lower() \
                if aggregate_value[FastapiWSClientFileHandler.query_type_key] is not None else None

            if query_type == "ws" or query_type == "both":
                output_str += (f'\tdef handle_query_{query_name}_ws(self, '
                               f'{message_name_snake_cased}_: {message.proto.name}BaseModel, **kwargs):\n')
                output_str += f"\t\tprint({message_name_snake_cased}_)\n\n"
        return output_str

    def ws_handlers(self):
        output_str = ""
        for message in self.root_message_list:
            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            output_str += (f'\tdef handle_{message_name_snake_cased}_get_all_ws(self, '
                           f'{message_name_snake_cased}_: {message.proto.name}BaseModel, **kwargs):\n')
            output_str += f"\t\tprint({message_name_snake_cased}_)\n\n"

            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message, FastapiWSClientFileHandler.flux_msg_json_root))
            else:
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message,
                                                             FastapiWSClientFileHandler.flux_msg_json_root_time_series))

            if BaseFastapiPlugin.flux_json_root_read_by_id_websocket_field in option_value_dict:
                output_str += (f'\tdef handle_{message_name_snake_cased}_get_by_id_ws(self, '
                               f'{message_name_snake_cased}_: {message.proto.name}BaseModel, **kwargs):\n')
                output_str += f"\t\tprint({message_name_snake_cased}_)\n\n"

            output_str += self._projection_query_ws_handler_method_generation(message)

        for message in set(self.root_message_list+list(self.message_to_query_option_list_dict)):
            if message in self.message_to_query_option_list_dict:
                output_str += self._client_query_ws_handler_method_generation(message)

        return output_str

    def handle_ws_client_file_gen(self, file: protogen.File,
                                  model_file_suffix: str | None = None) -> str:
        output_str = ""
        output_str += self.handle_imports_output(file, model_file_suffix)
        file_name = str(file.proto.name).split(".")[0]
        file_name_camel_cased = convert_to_capitalized_camel_case(file_name)
        output_str += f"class {file_name_camel_cased}WSClient:\n"
        output_str += f"\tdef __init__(self, host: str, port: int):\n"
        output_str += \
            f'\t\tself.{file.proto.package}_base_url: str = f"ws://' + '{host}:{port}' + f'/{file.proto.package}"\n'
        output_str += self.ws_uri_handler(file)
        output_str += "\n"
        output_str += self.ws_handlers()
        output_str += self.ws_reader_client_methods_generation()

        return output_str

