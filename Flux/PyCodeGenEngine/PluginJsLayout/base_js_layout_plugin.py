#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict
import protogen
from pathlib import PurePath
from abc import ABC
from FluxPythonUtils.scripts.general_utility_functions import convert_to_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager, convert_camel_case_to_specific_case
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_utils import selective_message_per_project_env_var_val_to_dict

# below main is imported to be accessible to derived classes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main  # required import

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = (
    YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path)))


class BaseJSLayoutPlugin(BaseProtoPlugin, ABC):
    """
    Plugin script to generate jsx file for ORM root messages
    """
    flux_msg_tree_layout_value: str = "UI_TREE"
    flux_msg_table_layout_value: str = "UI_TABLE"
    flux_msg_abbreviated_filter_layout_value: str = "UI_ABBREVIATED_FILTER"
    root_type: str = 'root'
    repeated_root_type: str = 'repeated_root'
    non_root_type: str = 'non_root'
    abbreviated_merge_type: str = 'abbreviation_merge'

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.project_name: str | None = None
        self.root_msg_list: List[protogen.Message] = []
        self.layout_msg_list: List[protogen.Message] = []
        self.repeated_msg_list: List[protogen.Message] = []
        self.abbreviated_merge_layout_msg_list: List[protogen.Message] = []
        self.alert_type_message_list: List[protogen.Message] = []
        self.msg_name_to_dependent_msg_name_list_dict: Dict[str, List[str]] = {}
        self.current_proto_file_name: str | None = None
        self.proto_file_name_to_message_list_dict: Dict[str, List[protogen.Message]] = {}
        self.file_name_to_dependency_file_names_dict: Dict[str, List[str]] = {}
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None and \
                len(response_field_case_style):
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'RESPONSE_FIELD_CASE_STYLE' " \
                      f"received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.case_style_convert_method: Callable[[str], str] | None = None

    def handle_dependency_files(self, file: protogen.File, message_list: List[protogen.Message],
                                is_multi_project: bool | None = None, selective_msg_name_list: List[str] = None):
        # Adding messages from core proto files having json_root option
        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var PROJECT_DIR received as {project_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

        core_or_util_files: List[str] = root_flux_core_config_yaml_dict.get("core_or_util_files")

        if "ProjectGroup" in project_dir:
            project_group_flux_core_config_yaml_path = PurePath(project_dir).parent.parent / "flux_core.yaml"
            project_group_flux_core_config_yaml_dict = (
                YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
            project_grp_core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
            if project_grp_core_or_util_files:
                core_or_util_files.extend(project_grp_core_or_util_files)

        if core_or_util_files is not None:
            for dependency_file in file.dependencies:
                if dependency_file.proto.name in core_or_util_files:
                    if is_multi_project:
                        file_name = dependency_file.proto.name
                        self.proto_file_name_to_message_list_dict[file_name.split(os.sep)[-1]] = (
                            dependency_file.messages)
                    for msg in dependency_file.messages:
                        if msg not in message_list:
                            if selective_msg_name_list:
                                # selective_msg_name_list is passed when selective msg are going to be added for
                                # this project
                                if msg.proto.name in selective_msg_name_list:
                                    message_list.append(msg)
                                # else not required: ignoring if not present in selective_msg_name_list
                            else:
                                # normal case: putting all msg in list
                                message_list.append(msg)

                # else not required: if dependency file name not in core_or_util_files
                # config list, avoid messages from it
        # else not required: core_or_util_files key is not in yaml dict config

    def load_root_message_to_data_member(self, file_or_file_list: protogen.File | List[protogen.File]):
        message_list: List[protogen.Message]
        if isinstance(file_or_file_list, list):
            file_list: List[protogen.File] = file_or_file_list
            selective_msg_per_project = os.getenv("SELECTIVE_MSG_PER_PROJECT")
            if selective_msg_per_project is not None:
                project_name_to_msg_list_dict: Dict[str, List[str]] = (
                    selective_message_per_project_env_var_val_to_dict(
                        selective_msg_per_project))
            else:
                project_name_to_msg_list_dict = {}

            message_list = []
            current_full_file_name: str = file_list[0].proto.name   # since first file in list is current proto file
            self.project_name = file_list[0].proto.package
            self.current_proto_file_name = current_full_file_name.split(os.sep)[-1]
            for f in file_list:
                project_name = f.proto.package
                msg_list = project_name_to_msg_list_dict.get(project_name)
                if msg_list:
                    file_name = f.proto.name
                    self.proto_file_name_to_message_list_dict[file_name.split(os.sep)[-1]] = []
                    for msg in f.messages:
                        if msg.proto.name in msg_list:
                            message_list.append(msg)

                            self.proto_file_name_to_message_list_dict[file_name.split(os.sep)[-1]].append(msg)
                            self.handle_dependency_files(f, message_list, True, msg_list)
                else:
                    message_list.extend(f.messages)
                    file_name = f.proto.name
                    self.proto_file_name_to_message_list_dict[file_name.split(os.sep)[-1]] = f.messages
                    self.handle_dependency_files(f, message_list, True)
                self.file_name_to_dependency_file_names_dict[f.proto.name] = \
                    [file.proto.name for file in f.dependencies]
        else:
            file: protogen.File = file_or_file_list
            message_list = file.messages
            self.handle_dependency_files(file, message_list)
            self.project_name = file.proto.package

        message_list.sort(key=lambda message_: message_.proto.name)
        message_name_list = [message_.proto.name for message_ in message_list]

        # handling current file
        for message in set(message_list):
            if (BaseJSLayoutPlugin.is_option_enabled(message, BaseJSLayoutPlugin.flux_msg_json_root) or
                    BaseJSLayoutPlugin.is_option_enabled(message, BaseJSLayoutPlugin.flux_msg_json_root_time_series)):
                self.root_msg_list.append(message)
            # else not required: Avoiding non ORM root messages

            if self.is_option_enabled(message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_value_from_proto(message,
                                                             BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)

                # updating alert list if is alert type
                if widget_ui_data_option_value_dict.get(BaseJSLayoutPlugin.flux_msg_widget_ui_data_element_is_model_alert_type_field):
                    self.alert_type_message_list.append(message)

                widget_ui_data_list = (
                    widget_ui_data_option_value_dict.get(
                        BaseJSLayoutPlugin.flux_msg_widget_ui_data_element_widget_ui_data_field))
                if widget_ui_data_list is not None and widget_ui_data_list:
                    widget_ui_data_dict = widget_ui_data_list[0]
                    if "view_layout" in widget_ui_data_dict:
                        self.layout_msg_list.append(message)
                        layout_type: str = widget_ui_data_dict["view_layout"].strip()
                        if BaseJSLayoutPlugin.flux_msg_tree_layout_value == layout_type or BaseJSLayoutPlugin.flux_msg_table_layout_value == layout_type:
                            is_repeated: bool = widget_ui_data_option_value_dict.get("is_repeated")
                            if is_repeated is not None and is_repeated:
                                self.repeated_msg_list.append(message)

                            # checking if this message has dependency on any model - if it has then updating msg_name_to_dependent_msg_name_list_dict
                            dependent_msg_name = widget_ui_data_option_value_dict.get(BaseJSLayoutPlugin.widget_ui_option_depending_proto_model_name_field)
                            if dependent_msg_name is not None and dependent_msg_name in message_name_list:
                                self.msg_name_to_dependent_msg_name_list_dict[message.proto.name] = [dependent_msg_name]
                            # else not required: if no dependency then no need to update msg_name_to_dependent_msg_name_list_dict
                            crud_override_option_list = widget_ui_data_option_value_dict.get(BaseJSLayoutPlugin.widget_ui_option_override_default_crud_field)
                            if crud_override_option_list:
                                crud_override_option_dict = crud_override_option_list[0]
                                if crud_override_option_dict:
                                    crud_dependent_msg_name = crud_override_option_dict.get(BaseJSLayoutPlugin.widget_ui_option_override_default_crud_query_src_model_name_field)
                                    if dependent_msg_name is not None and dependent_msg_name != crud_dependent_msg_name:
                                        raise Exception(f"multiple dependents found for non-filter model "
                                                        f"{message.proto.name}, {dependent_msg_name=}, "
                                                        f"{crud_dependent_msg_name=}")
                                    if crud_dependent_msg_name is not None and crud_dependent_msg_name in message_name_list:
                                        self.msg_name_to_dependent_msg_name_list_dict[message.proto.name] = [crud_dependent_msg_name]
                                    # else not required: if no dependency then no need to update msg_name_to_dependent_msg_name_list_dict
                            # else not required: no crud override set
                        elif BaseJSLayoutPlugin.flux_msg_abbreviated_filter_layout_value == layout_type:
                            self.abbreviated_merge_layout_msg_list.append(message)
                            dependent_msg_name_list = self._get_msg_names_list_used_in_abb_option_val(message)
                            self.msg_name_to_dependent_msg_name_list_dict[message.proto.name] = dependent_msg_name_list
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

    def is_model_from_another_project(self, message: protogen.Message) -> bool:
        if self.proto_file_name_to_message_list_dict:
            for file_name, message_list in self.proto_file_name_to_message_list_dict.items():
                if (file_name != self.current_proto_file_name and
                        file_name not in self.file_name_to_dependency_file_names_dict[self.current_proto_file_name]):
                    if message in message_list:
                        return True
        # message if not from another project for all other cases
        return False

    def _get_abb_option_vals_cleaned_message_n_field_list(self, field: protogen.Field) -> List[str]:
        abbreviated_option_val = (
            BaseJSLayoutPlugin.get_simple_option_value_from_proto(field, BaseJSLayoutPlugin.flux_fld_abbreviated))
        abbreviated_option_val_check_str_list: List[str] = []
        if abbreviated_option_val and "^" in abbreviated_option_val:
            abbreviated_option_val_caret_sep = abbreviated_option_val.split("^")
            for abbreviated_option_val_caret_sep_line in abbreviated_option_val_caret_sep:
                if "-" in abbreviated_option_val_caret_sep:
                    abbreviated_option_val_caret_sep_hyphen_sep = (
                        abbreviated_option_val_caret_sep_line.split("-"))
                    for abbreviated_option_val_caret_sep_hyphen_sep_line in (
                            abbreviated_option_val_caret_sep_hyphen_sep):
                        if ":" in abbreviated_option_val_caret_sep_hyphen_sep_line:
                            mapping_key, mapping_value = (
                                abbreviated_option_val_caret_sep_hyphen_sep_line.split(":"))
                            abbreviated_option_val_check_str_list.append(mapping_value)
                        else:
                            abbreviated_option_val_check_str_list.append(
                                abbreviated_option_val_caret_sep_hyphen_sep_line)
                else:
                    if ":" in abbreviated_option_val_caret_sep_line:
                        mapping_key, mapping_value = abbreviated_option_val_caret_sep_line.split(":")
                        abbreviated_option_val_check_str_list.append(mapping_value)
                    else:
                        abbreviated_option_val_check_str_list.append(
                            abbreviated_option_val_caret_sep_line)

        alert_bubble_source_option_val = (
            BaseJSLayoutPlugin.get_simple_option_value_from_proto(field, BaseJSLayoutPlugin.flux_fld_alert_bubble_source))
        if alert_bubble_source_option_val:
            abbreviated_option_val_check_str_list.append(alert_bubble_source_option_val)

        alert_bubble_color_option_val = (
            BaseJSLayoutPlugin.get_simple_option_value_from_proto(field, BaseJSLayoutPlugin.flux_fld_alert_bubble_color))
        if alert_bubble_color_option_val:
            abbreviated_option_val_check_str_list.append(alert_bubble_color_option_val)

        return abbreviated_option_val_check_str_list

    def _get_msg_names_list_used_in_abb_option_val(self, message: protogen.Message) -> List[str]:
        msg_list = []
        for field in message.fields:
            if (self.is_option_enabled(field, BaseJSLayoutPlugin.flux_fld_abbreviated) or
                    self.is_option_enabled(field, BaseJSLayoutPlugin.flux_fld_alert_bubble_source),
                    self.is_option_enabled(field, BaseJSLayoutPlugin.flux_fld_alert_bubble_color)):
                msg_n_field_list: List[str] = self._get_abb_option_vals_cleaned_message_n_field_list(field)

                for msg_n_field_str in msg_n_field_list:
                    msg_name = msg_n_field_str.split(".")[0]
                    if msg_name not in msg_list:
                        msg_list.append(msg_name)

        return msg_list

