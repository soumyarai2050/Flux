#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict
import protogen
from pathlib import PurePath
from abc import ABC
from FluxPythonUtils.scripts.utility_functions import (convert_camel_case_to_specific_case, convert_to_camel_case,
                                                       YAMLConfigurationManager)
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

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.project_name: str | None = None
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
                widget_ui_data_list = (
                    widget_ui_data_option_value_dict.get(
                        BaseJSLayoutPlugin.flux_msg_widget_ui_data_element_widget_ui_data_field))
                if widget_ui_data_list is not None and widget_ui_data_list:
                    widget_ui_data_dict = widget_ui_data_list[0]
                    if "view_layout" in widget_ui_data_dict:
                        self.layout_msg_list.append(message)
                        layout_type: str = widget_ui_data_dict["view_layout"].strip()
                        if BaseJSLayoutPlugin.flux_msg_tree_layout_value == layout_type:
                            is_repeated: bool = widget_ui_data_option_value_dict.get("is_repeated")
                            if is_repeated is not None and is_repeated:
                                self.repeated_tree_layout_msg_list.append(message)
                            # if is_repeated field is not present in option val or is false both signifies
                            # message is not repeated view of tree layout
                            else:
                                self.tree_layout_msg_list.append(message)
                        elif BaseJSLayoutPlugin.flux_msg_table_layout_value == layout_type:
                            is_repeated: bool = widget_ui_data_option_value_dict.get("is_repeated")
                            if is_repeated is not None and is_repeated:
                                self.repeated_table_layout_msg_list.append(message)
                            # if is_repeated field is not present in option val or is false both signifies
                            # message is not repeated view of tree layout
                            else:
                                self.table_layout_msg_list.append(message)
                        elif BaseJSLayoutPlugin.flux_msg_abbreviated_filter_layout_value == layout_type:
                            self.simple_abbreviated_filter_layout_msg_list.append(message)
                            fld_abbreviated_option_value = None
                            for field in message.fields:
                                fld_abbreviated_option_value = \
                                    self.get_simple_option_value_from_proto(field,
                                                                            BaseJSLayoutPlugin.flux_fld_abbreviated)
                                if fld_abbreviated_option_value is not None:
                                    break
                            else:
                                err_str = (f"Could not find {BaseJSLayoutPlugin.flux_fld_abbreviated} in any "
                                           f"of fields of abbreviated type message {message.proto.name}")
                                logging.exception(err_str)
                                raise Exception(err_str)
                            dependent_msg_name = fld_abbreviated_option_value.split(".")[0]
                            if ":" in dependent_msg_name:
                                dependent_msg_name = dependent_msg_name.split(":")[-1]
                            # else not required: if ":" not present then taking first '.' seperated name
                            self.abbreviated_msg_name_to_dependent_msg_name_dict[message.proto.name] = (
                                dependent_msg_name)
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
                for msg in message_list:
                    found_msg = False
                    if abb_dependent_msg_name == msg.proto.name:
                        found_msg = True
                        for field in msg.fields:
                            if self.is_option_enabled(field, BaseJSLayoutPlugin.flux_fld_abbreviated_link):
                                abb_link_option_val = \
                                    self.get_simple_option_value_from_proto(field,
                                                                            BaseJSLayoutPlugin.flux_fld_abbreviated_link)
                                dependent_abb_msg_name = abb_link_option_val.split(".")[0]
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

    def is_model_from_another_project(self, message: protogen.Message) -> bool:
        if self.proto_file_name_to_message_list_dict:
            for file_name, message_list in self.proto_file_name_to_message_list_dict.items():
                if (file_name != self.current_proto_file_name and
                        file_name not in self.file_name_to_dependency_file_names_dict[self.current_proto_file_name]):
                    if message in message_list:
                        return True
        # message if not from another project for all other cases
        return False

    def _get_ui_msg_dependent_msg_name_from_another_proto(self, message: protogen.Message) -> str | None:
        """
        :param message: msg type to check
        :return: None if not dependent on msg from another proto file else returns
                 msg name on which it depends from another proto file and if msg is from another
                 proto file but is not dependent on any other message then returns empty str ''
        """
        if self.is_model_from_another_project(message):
            if BaseJSLayoutPlugin.is_option_enabled(message,
                                                    BaseJSLayoutPlugin.flux_msg_widget_ui_data_element):
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                dependent_model_name = (
                    option_dict.get(BaseJSLayoutPlugin.widget_ui_option_depending_proto_model_name_field))
                if dependent_model_name is None:
                    return ""
                else:
                    return dependent_model_name
            elif BaseJSLayoutPlugin.is_option_enabled(message,
                                                      BaseJSLayoutPlugin.flux_msg_widget_ui_option):
                return ""
        return None

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

    def _get_override_default_get_all_crud(self, widget_ui_option_value: Dict):
        override_default_crud_option_fld_val_list = (
            widget_ui_option_value.get(BaseJSLayoutPlugin.widget_ui_option_override_default_crud_field))
        get_all_override_default_crud = None
        if override_default_crud_option_fld_val_list:
            for override_default_crud_option_fld_val in override_default_crud_option_fld_val_list:
                ui_crud_type = (
                    override_default_crud_option_fld_val.get(
                        BaseJSLayoutPlugin.widget_ui_option_override_default_crud_ui_crud_type_field))
                if ui_crud_type == "GET_ALL":
                    get_all_override_default_crud = override_default_crud_option_fld_val
        return get_all_override_default_crud

    def _get_msg_name_from_another_file_n_used_in_abb_text(
            self, message: protogen.Message, abbreviated_dependent_message_name: str) -> List[str]:
        """
        :param message: abb type message
        :param abbreviated_dependent_message_name:
        :return:
        """
        msg_list = []
        msg_used_in_abb_option_list = self._get_msg_names_list_used_in_abb_option_val(message)
        if abbreviated_dependent_message_name in msg_used_in_abb_option_list:
            msg_used_in_abb_option_list.remove(abbreviated_dependent_message_name)
        for msg_name_used_in_abb_option in msg_used_in_abb_option_list:
            for file_name, message_list in self.proto_file_name_to_message_list_dict.items():
                if (file_name != self.current_proto_file_name and
                        file_name not in self.file_name_to_dependency_file_names_dict[
                            self.current_proto_file_name]):
                    for msg in message_list:
                        if msg.proto.name == msg_name_used_in_abb_option:
                            msg_list.append(msg_name_used_in_abb_option)
        return msg_list
