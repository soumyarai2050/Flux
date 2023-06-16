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
        self.simple_abbreviated_filter_layout_msg_list: List[protogen.Message] = []
        self.parent_abbreviated_filter_layout_msg_list: List[protogen.Message] = []
        self.abbreviated_msg_name_to_dependent_msg_name_dict: Dict[str, str] = {}
        self.parent_abb_msg_name_to_linked_abb_msg_name_dict: Dict[str, str] = {}
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
            if self.is_option_enabled(message, BaseJSLayoutPlugin.flux_msg_json_root):
                self.root_msg_list.append(message)
            # else not required: Avoiding non ORM root messages

            if self.is_option_enabled(message, BaseJSLayoutPlugin.flux_msg_widget_ui_data):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_set_values(message,
                                                       BaseJSLayoutPlugin.flux_msg_widget_ui_data)
                if "layout" in widget_ui_data_option_value_dict:
                    self.layout_msg_list.append(message)
                    layout_type: str = widget_ui_data_option_value_dict["layout"].strip()
                    if BaseJSLayoutPlugin.flux_msg_tree_layout_value == layout_type:
                        is_repeated: bool = widget_ui_data_option_value_dict.get("is_repeated")
                        if is_repeated is not None and is_repeated:
                            self.repeated_tree_layout_msg_list.append(message)
                        # if is_repeated field is not present in option val or is false both signifies message is not
                        # repeated view of tree layout
                        else:
                            self.tree_layout_msg_list.append(message)
                    elif BaseJSLayoutPlugin.flux_msg_table_layout_value == layout_type:
                        is_repeated: bool = widget_ui_data_option_value_dict.get("is_repeated")
                        if is_repeated is not None and is_repeated:
                            self.repeated_table_layout_msg_list.append(message)
                        # if is_repeated field is not present in option val or is false both signifies message is not
                        # repeated view of tree layout
                        else:
                            self.table_layout_msg_list.append(message)
                    elif BaseJSLayoutPlugin.flux_msg_abbreviated_filter_layout_value == layout_type:
                        self.simple_abbreviated_filter_layout_msg_list.append(message)
                        fld_abbreviated_option_value = None
                        for field in message.fields:
                            fld_abbreviated_option_value = \
                                self.get_non_repeated_valued_custom_option_value(field,
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

            # Collecting all parent_abbreviated_type message from simple_abbreviated_type list
            parent_abb_msg_name_list = []
            for abb_msg_name, abb_dependent_msg_name in self.abbreviated_msg_name_to_dependent_msg_name_dict.items():
                for msg in file.messages:
                    found_msg = False
                    if abb_dependent_msg_name == msg.proto.name:
                        found_msg = True
                        for field in msg.fields:
                            if self.is_option_enabled(field, BaseJSLayoutPlugin.flux_fld_abbreviated_link):
                                abb_link_option_val = \
                                    self.get_non_repeated_valued_custom_option_value(field,
                                                                                     BaseJSLayoutPlugin.flux_fld_abbreviated_link)
                                dependent_abb_msg_name = abb_link_option_val.split(".")[0][1:]
                                self.parent_abb_msg_name_to_linked_abb_msg_name_dict[abb_msg_name] = dependent_abb_msg_name
                                parent_abb_msg_name_list.append(abb_msg_name)
                                break
                    if found_msg:
                        break
                else:
                    err_str = f"Could not find any message in proto files with name {abb_dependent_msg_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)

            for simple_abb_msg in self.simple_abbreviated_filter_layout_msg_list:
                if simple_abb_msg.proto.name in parent_abb_msg_name_list:
                    # adding parent abb type message in parent_abbreviated_filter_layout_msg_list and
                    # removing it from simple abb type list
                    self.parent_abbreviated_filter_layout_msg_list.append(simple_abb_msg)
                    self.simple_abbreviated_filter_layout_msg_list.remove(simple_abb_msg)

        if self.response_field_case_style.lower() == "snake":
            self.case_style_convert_method = convert_camel_case_to_specific_case
        elif self.response_field_case_style.lower() == "camel":
            self.case_style_convert_method = convert_to_camel_case
        else:
            err_str = f"{self.response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
