# standard imports
from abc import ABC
from typing import List, Dict

import protogen

# project imports
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin
from FluxPythonUtils.scripts.general_utility_functions import  convert_to_capitalized_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class FastapiUIProxyConfigHandler(BaseFastapiPlugin, ABC):
    """
    Currently Only includes WS Get-All and WS Get-By-Id uri(s).
    """
    beanie_pydantic_model_dir_name = "ORMModel"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_ui_proxy_config_file_gen(self, file) -> str:
        output_str = "ui_uri_to_server_uri:\n"
        for message in self.root_message_list:
            message_name_snake_cased = convert_camel_case_to_specific_case(message.proto.name)
            output_str += f'  - type: "GET_ALL"\n'
            output_str += f'    ws_uri_path: "/get-all-{message_name_snake_cased}-ws"\n'
            output_str += f'    get_http_path: "/get-all-{message_name_snake_cased}"\n'

            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
                option_value_dict = (
                    self.get_complex_option_value_from_proto(message, FastapiUIProxyConfigHandler.flux_msg_json_root))
            else:
                option_value_dict = (
                    self.get_complex_option_value_from_proto(
                        message, FastapiUIProxyConfigHandler.flux_msg_json_root_time_series))

            if BaseFastapiPlugin.flux_json_root_read_by_id_websocket_field in option_value_dict:
                output_str += f'  - type: "GET_BY_ID"\n'
                output_str += (f'    ws_uri_path: "/get-{message_name_snake_cased}-ws/' +
                               '{'+f'{message_name_snake_cased}_id'+'}"\n')
                output_str += f'    get_http_path: "/get-{message_name_snake_cased}"\n'

            if FastapiUIProxyConfigHandler.is_option_enabled(
                    message, FastapiUIProxyConfigHandler.flux_msg_json_root_time_series):
                projection_val_to_query_name_dict = (
                    FastapiUIProxyConfigHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
                for _, query_name in projection_val_to_query_name_dict.items():
                    output_str += f'  - type: "QUERY"\n'
                    output_str += f'    ws_uri_path: "/ws-query-{query_name}"\n'
                    output_str += f'    get_http_path: "/query-{query_name}"\n'

            if FastapiUIProxyConfigHandler.is_option_enabled(message, FastapiUIProxyConfigHandler.flux_msg_json_query):
                aggregate_value_list = self.message_to_query_option_list_dict[message]
                for aggregate_value in aggregate_value_list:
                    query_name = aggregate_value[FastapiUIProxyConfigHandler.query_name_key]
                    output_str += f'  - type: "QUERY"\n'
                    output_str += f'    ws_uri_path: "/ws-query-{query_name}"\n'
                    output_str += f'    get_http_path: "/query-{query_name}"\n'

        # Since Queries can also be in non-root messages
        for message in self.non_root_message_list:
            if FastapiUIProxyConfigHandler.is_option_enabled(message, FastapiUIProxyConfigHandler.flux_msg_json_query):
                aggregate_value_list = self.message_to_query_option_list_dict[message]
                for aggregate_value in aggregate_value_list:
                    query_name = aggregate_value[FastapiUIProxyConfigHandler.query_name_key]
                    output_str += f'  - type: "QUERY"\n'
                    output_str += f'    ws_uri_path: "/ws-query-{query_name}"\n'
                    output_str += f'    get_http_path: "/query-{query_name}"\n'

        return output_str

