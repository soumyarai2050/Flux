#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict
import protogen
# below main is imported to be accessible to derived classes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, convert_to_camel_case


class BaseJSLayoutPlugin(BaseProtoPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    """
    flux_msg_tree_layout_value: str = "UI_TREE"
    flux_msg_table_layout_value: str = "UI_TABLE"
    flux_msg_abbreviated_filter_layout_value: str = "UI_ABBREVIATED_FILTER"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_msg_list: List[protogen.Message] = []
        self.layout_msg_list: List[protogen.Message] = []
        self.tree_layout_msg_list: List[protogen.Message] = []
        self.repeated_tree_layout_msg_list: List[protogen.Message] = []
        self.table_layout_msg_list: List[protogen.Message] = []
        self.repeated_table_layout_msg_list: List[protogen.Message] = []
        self.abbreviated_filter_layout_msg_list: List[protogen.Message] = []
        self.abbreviated_msg_name_to_dependent_msg_name_dict: Dict[str, str] = {}
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None:
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'RESPONSE_FIELD_CASE_STYLE' " \
                      f"received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.case_style_convert_method: Callable[[str], str] | None = None

    def load_root_message_to_data_member(self, file: protogen.File):
        for message in file.messages:
            if BaseJSLayoutPlugin.flux_msg_json_root in (options_str := str(message.proto.options)):
                self.root_msg_list.append(message)
            # else not required: Avoiding non ORM root messages

            if BaseJSLayoutPlugin.flux_msg_widget_ui_data in options_str:
                widget_ui_data_option_list_of_dict = \
                    self.get_complex_option_values_as_list_of_dict(message,
                                                                   BaseJSLayoutPlugin.flux_msg_widget_ui_data)[0]
                if "layout" in widget_ui_data_option_list_of_dict:
                    self.layout_msg_list.append(message)
                    layout_type: str = widget_ui_data_option_list_of_dict["layout"].strip()
                    if BaseJSLayoutPlugin.flux_msg_tree_layout_value == layout_type:
                        is_repeated: bool = widget_ui_data_option_list_of_dict.get("is_repeated")
                        if is_repeated is not None and is_repeated:
                            self.repeated_tree_layout_msg_list.append(message)
                        # if is_repeated field is not present in option val or is false both signifies message is not
                        # repeated view of tree layout
                        else:
                            self.tree_layout_msg_list.append(message)
                    elif BaseJSLayoutPlugin.flux_msg_table_layout_value == layout_type:
                        is_repeated: bool = widget_ui_data_option_list_of_dict.get("is_repeated")
                        if is_repeated is not None and is_repeated:
                            self.repeated_table_layout_msg_list.append(message)
                        # if is_repeated field is not present in option val or is false both signifies message is not
                        # repeated view of tree layout
                        else:
                            self.table_layout_msg_list.append(message)
                    elif BaseJSLayoutPlugin.flux_msg_abbreviated_filter_layout_value == layout_type:
                        self.abbreviated_filter_layout_msg_list.append(message)
                        fld_abbreviated_option_value = None
                        for field in message.fields:
                            fld_abbreviated_option_value = \
                                self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                                 BaseJSLayoutPlugin.flux_fld_abbreviated)
                            if fld_abbreviated_option_value is not None:
                                break
                        else:
                            err_str = f"Could not find {BaseJSLayoutPlugin.flux_fld_abbreviated} in any of fields of " \
                                      f"abbreviated type message {message.proto.name}"
                            logging.exception(err_str)
                            raise Exception(err_str)
                        fld_abbreviated_option_value = fld_abbreviated_option_value[1:]
                        dependent_msg_name = fld_abbreviated_option_value.split(".")[0]
                        if ":" in dependent_msg_name:
                            dependent_msg_name = dependent_msg_name.split(":")[-1]
                        # else not required: if ":" not present then taking first '.' seperated name
                        self.abbreviated_msg_name_to_dependent_msg_name_dict[message.proto.name] = dependent_msg_name
                    else:
                        err_str = f"{layout_type} is not a valid layout option value found in proto message " \
                                  f"{message.proto.name}"
                        logging.exception(err_str)
                        raise Exception(err_str)
                # else not required: Avoiding if flx_msg_widget_ui_data doesn't have layout field
            # else not required: If msg doesn't have flx_msg_widget_ui_data then it will not have layout field

        if self.response_field_case_style.lower() == "snake":
            self.case_style_convert_method = convert_camel_case_to_specific_case
        elif self.response_field_case_style.lower() == "camel":
            self.case_style_convert_method = convert_to_camel_case
        else:
            err_str = f"{self.response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
