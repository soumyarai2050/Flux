#!/usr/bin/env python
import logging
from typing import List, Callable
import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin

# Required for accessing custom options from schema
import insertion_imports


class BaseJSLayoutPlugin(BaseProtoPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    """
    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_msg_layout: str = "FluxMsgLayout"
    flux_msg_tree_layout_value: str = "Tree"
    flux_msg_table_layout_value: str = "Table"
    flux_msg_abbreviated_filter_layout_value: str = "AbbreviatedFilter"
    flux_fld_abbreviated: str = "FluxFldAbbreviated"

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.root_msg_list: List[protogen.Message] = []
        self.layout_msg_list: List[protogen.Message] = []
        self.tree_layout_msg_list: List[protogen.Message] = []
        self.table_layout_msg_list: List[protogen.Message] = []
        self.abbreviated_filter_layout_msg_list: List[protogen.Message] = []
        self.case_style: str = self.config_yaml["case_style"]
        self.case_style_convert_method: Callable[[str], str] | None = None

    def load_root_message_to_data_member(self, file: protogen.File):
        for message in file.messages:
            if BaseJSLayoutPlugin.flux_msg_json_root in (options_str := str(message.proto.options)):
                self.root_msg_list.append(message)
            # else not required: Avoiding non ORM root messages

            if BaseJSLayoutPlugin.flux_msg_layout in options_str:
                self.layout_msg_list.append(message)
                layout_type: str = self.get_non_repeated_valued_custom_option_value(
                            message.proto.options,
                            BaseJSLayoutPlugin.flux_msg_layout)[1:-1]
                if BaseJSLayoutPlugin.flux_msg_tree_layout_value == layout_type:
                    self.tree_layout_msg_list.append(message)
                elif BaseJSLayoutPlugin.flux_msg_table_layout_value == layout_type:
                    self.table_layout_msg_list.append(message)
                elif BaseJSLayoutPlugin.flux_msg_abbreviated_filter_layout_value == layout_type:
                    self.abbreviated_filter_layout_msg_list.append(message)
                else:
                    err_str = f"{layout_type} is not a valid layout option value found in proto message " \
                              f"{message.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
            # else not required: Avoiding manual layout type messages

        if self.case_style.lower() == "snake":
            self.case_style_convert_method = self.convert_camel_case_to_specific_case
        elif self.case_style.lower() == "camel":
            self.case_style_convert_method = self.convert_to_camel_case
        else:
            err_str = f"{self.case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
