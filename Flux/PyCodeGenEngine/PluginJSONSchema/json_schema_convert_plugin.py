#!/usr/bin/env python
import json
import logging
import os
from typing import List, Callable, Dict, Tuple, Any
import time
import re
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import (convert_camel_case_to_specific_case, convert_to_camel_case,
                                                       YAMLConfigurationManager)


root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class JsonSchemaConvertPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    # Used to be added as property
    flx_fld_simple_non_repeated_attribute_options: List[str] = [
        BaseProtoPlugin.flux_fld_help,
        BaseProtoPlugin.flux_fld_hide,
        BaseProtoPlugin.flux_fld_val_sort_weight,
        BaseProtoPlugin.flux_fld_abbreviated,
        BaseProtoPlugin.flux_fld_sticky,
        BaseProtoPlugin.flux_fld_size_max,
        BaseProtoPlugin.flux_fld_orm_no_update,
        BaseProtoPlugin.flux_fld_switch,
        BaseProtoPlugin.flux_fld_auto_complete,
        BaseProtoPlugin.flux_fld_server_populate,
        BaseProtoPlugin.flux_fld_color,
        BaseProtoPlugin.flux_fld_alert_bubble_source,
        BaseProtoPlugin.flux_fld_alert_bubble_color,
        BaseProtoPlugin.flux_fld_default_value_placeholder_string,
        BaseProtoPlugin.flux_fld_ui_placeholder,
        BaseProtoPlugin.flux_fld_ui_update_only,
        BaseProtoPlugin.flux_fld_val_max,
        BaseProtoPlugin.flux_fld_val_min,
        BaseProtoPlugin.flux_fld_elaborated_title,
        BaseProtoPlugin.flux_fld_name_color,
        BaseProtoPlugin.flux_fld_filter_enable,
        BaseProtoPlugin.flux_fld_no_common_key,
        BaseProtoPlugin.flux_fld_number_format,
        BaseProtoPlugin.flux_fld_display_type,
        BaseProtoPlugin.flux_fld_display_zero,
        BaseProtoPlugin.flux_fld_text_align,
        BaseProtoPlugin.flux_fld_column_size,
        BaseProtoPlugin.flux_fld_column_direction,
        BaseProtoPlugin.flux_fld_micro_separator,
        BaseProtoPlugin.flux_fld_val_time_field,
        BaseProtoPlugin.flux_fld_val_meta_field,
        BaseProtoPlugin.flux_fld_server_running_status,
        BaseProtoPlugin.flux_fld_server_ready_status,
        BaseProtoPlugin.flux_fld_diff_threshold
    ]
    flx_fld_simple_repeated_attribute_options: List[str] = [
        BaseProtoPlugin.flux_fld_mapping_underlying_meta_field,
        BaseProtoPlugin.flux_fld_mapping_src,
        BaseProtoPlugin.flux_fld_projections,
        BaseProtoPlugin.flux_fld_mapping_projection_query_field
    ]
    flx_fld_complex_non_repeated_attribute_options: List[str] = [
        BaseProtoPlugin.flux_fld_button,
        BaseProtoPlugin.flux_fld_progress_bar,
    ]
    flx_fld_complex_repeated_attribute_options: List[str] = [
        # put this category options here
    ]
    flx_msg_simple_non_repeated_attribute_options: List[str] = [
        BaseProtoPlugin.flux_msg_server_populate,
        BaseProtoPlugin.flux_msg_ui_get_all_limit
    ]
    flx_msg_simple_repeated_attribute_options: List[str] = [
        # put this category options here
    ]
    flx_msg_complex_non_repeated_attribute_options: List[str] = [
        # put this category options here
    ]
    flx_msg_complex_repeated_attribute_options: List[str] = [
        # put this category options here
    ]

    options_having_msg_fld_names: List[str] = [
        BaseProtoPlugin.flux_fld_abbreviated,
        BaseProtoPlugin.flux_fld_alert_bubble_color,
        BaseProtoPlugin.flux_fld_alert_bubble_source,
        BaseProtoPlugin.flux_fld_val_max,
        BaseProtoPlugin.flux_fld_val_min,
        BaseProtoPlugin.flux_fld_mapping_underlying_meta_field,
        BaseProtoPlugin.flux_fld_mapping_src
    ]
    # used to handle option fields having msg_n_field names in set value
    flux_msg_widget_ui_data_element_fields_having_msg_n_fld_names_in_val = ["alert_bubble_source", "alert_bubble_color", "bind_id_fld", "dynamic_widget_title_fld", "query_param_field_src", "query_src_model_name"]
    # @LOW todo: query_param_field_src should have same query_src_model_name as src model

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None and \
                len(response_field_case_style):
            self.__response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'RESPONSE_FIELD_CASE_STYLE' received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.__json_layout_message_list: List[protogen.Message] = []
        self.__json_non_layout_message_list: List[protogen.Message] = []
        self.__enum_list: List[protogen.Enum] = []
        self.__root_msg_list: List[protogen.Message] = []
        self.__case_style_convert_method: Callable[[str], str] | None = None
        self.__add_autocomplete_dict: bool = False
        self._proto_project_name_to_msg_list_dict: Dict[str, List[protogen.Message]] = {}
        self._current_project_name: str | None = None
        self.__main_file_message_name_list: List[str] = []
        self._current_project_model_file: protogen.File | None = None

    def __proto_data_type_to_json(self, field: protogen.Field) -> Tuple[str, str]:
        underlying_type = field.kind.name.lower()
        if field.cardinality.name.lower() == "repeated":
            json_type = "array"
        else:
            json_type = JsonSchemaConvertPlugin.proto_type_to_json_type_dict[underlying_type]
        return underlying_type, json_type

    def check_is_dependent_widget_field_name_snake_cased(self, field: protogen.Field) -> None:
        if field.message is not None:
            if self.is_option_enabled(field, JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element):
                if field.proto.name != convert_camel_case_to_specific_case(field.message.proto.name):
                    err_str = f"field {field.proto.name} is of dependent widget message type " \
                              f"{field.message.proto.name} but is not snake_case of dependent widget message," \
                              f"message containing field - {field.parent.proto.name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                # else not required: avoid if field_name is snake case of its dependent message type
            # else not required: avoid if field's message type is non-widget type
        # else not required: avoid if field is simple or enum type

    def __load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            self.check_is_dependent_widget_field_name_snake_cased(field)

            if field.kind.name.lower() == "enum":
                if field.enum not in self.__enum_list:
                    self.__enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if self.is_option_enabled(field.message, JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element):
                    widget_ui_data_option_value_dict = \
                        self.get_complex_option_value_from_proto(field.message,
                                                                 JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)
                    widget_ui_data_list = widget_ui_data_option_value_dict.get("widget_ui_data")
                    # since there will always be single widget_ui_data
                    if widget_ui_data_list and "view_layout" in widget_ui_data_list[0]:
                        if field.message not in self.__json_layout_message_list:
                            self.__json_layout_message_list.append(field.message)
                        # else not required: avoiding repetition
                    else:
                        if field.message not in self.__json_non_layout_message_list:
                            self.__json_non_layout_message_list.append(field.message)
                        # else not required: avoiding repetition
                else:
                    if field.message not in self.__json_non_layout_message_list:
                        self.__json_non_layout_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.__load_dependency_messages_and_enums_in_dicts(field.message)
            # else not required: avoiding other kinds than message or enum

            if self.is_option_enabled(field, JsonSchemaConvertPlugin.flux_fld_auto_complete):
                self.__add_autocomplete_dict = True
            # else not required: If AutoComplete option is not set then __add_autocomplete_dict's default
            # value will be used while generation check

    def __load_json_layout_and_non_layout_messages_in_dicts(self, file: protogen.File):
        message_list: List[protogen.Message] = file.messages

        # Adding messages from core proto files having json_root option
        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var DBType received as {project_dir}"
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
                    message_list.extend(dependency_file.messages)
                # else not required: if dependency file name not in core_or_util_files
                # config list, avoid messages from it
        # else not required: core_or_util_files key is not in yaml dict config

        for message in set(message_list):
            if self.is_option_enabled(message, JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_value_from_proto(message,
                                                             JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)
                widget_ui_data_list = widget_ui_data_option_value_dict.get("widget_ui_data")
                # since there will always be single widget_ui_data
                if widget_ui_data_list and "view_layout" in widget_ui_data_list[0]:
                    if message not in self.__json_layout_message_list:
                        self.__json_layout_message_list.append(message)
                    # else not required: avoiding repetition
                else:
                    if message not in self.__json_non_layout_message_list:
                        self.__json_non_layout_message_list.append(message)
                    # else not required: avoiding repetition
            else:
                if message not in self.__json_non_layout_message_list:
                    self.__json_non_layout_message_list.append(message)
                # else not required: avoiding repetition

            if (self.is_option_enabled(message, JsonSchemaConvertPlugin.flux_msg_json_root) or
                    self.is_option_enabled(message, JsonSchemaConvertPlugin.flux_msg_json_root_time_series)):
                self.__root_msg_list.append(message)

            self.__load_dependency_messages_and_enums_in_dicts(message)

    def __handle_message_or_enum_type_json_schema(self, data_type: str, init_space_count: int, data_type_name: str,
                                                  json_type: str,
                                                  msg_or_enum_obj: protogen.Message | protogen.Enum) -> str:
        """
            Parameters:
            -------
            data_type: 'e' for enum and 'm' for message, else raises exception
            init_space_count: number of spaces before each line
            data_type_name: name of message or enum
            json_type: json converted type of the message
            msg_or_enum_obj: message or Enum object of json handling is being done
        """
        json_msg_str = ''
        json_msg_str += ' ' * init_space_count + f'"type": "{json_type}",\n'
        json_msg_str += ' ' * init_space_count + f'"items": ' + '{\n'
        if data_type == 'm':
            if msg_or_enum_obj in self.__json_layout_message_list:
                json_msg_str += \
                    ' ' * (init_space_count + 2) + f'"$ref": "#/{data_type_name}"' + \
                    '\n' + ' ' * init_space_count + '}\n'
            else:
                json_msg_str += \
                    ' ' * (init_space_count + 2) + f'"$ref": "#/definitions/{data_type_name}"' + \
                    '\n' + ' ' * init_space_count + '}\n'
        elif data_type == 'e':
            json_msg_str += \
                ' ' * (init_space_count + 2) + f'"$ref": "#/definitions/{data_type_name}"' + \
                '\n' + ' ' * init_space_count + '}\n'
        else:
            err_msg = f"Parameter data_type must be only 'm' or 'e', provided {data_type}"
            logging.exception(err_msg)
            raise Exception(err_msg)
        return json_msg_str

    def __handle_required_json_schema(self, init_space_count: int, required_field_names: List[str]) -> str:
        json_msg_str = ""
        for field_name in required_field_names:
            if field_name != required_field_names[-1]:
                json_msg_str += ' ' * (init_space_count + 2) + f'"{field_name}",\n'
            else:
                json_msg_str += ' ' * (init_space_count + 2) + f'"{field_name}"\n'
        return json_msg_str

    def __add_required_field_names_to_list(self, required_field_names: List[str], field: protogen.Field) -> List[str]:
        if field.cardinality.name.lower() == "required":
            field_name_case_styled = self.__case_style_convert_method(field.proto.name)
            required_field_names.append(field_name_case_styled)
        elif field.cardinality.name.lower() == "repeated":
            if self.is_bool_option_enabled(field, JsonSchemaConvertPlugin.flux_fld_is_required):
                field_name_case_styled = self.__case_style_convert_method(field.proto.name)
                required_field_names.append(field_name_case_styled)
        # else not required: avoiding optional cardinality
        return required_field_names

    def __handle_field_json_type_schema(self, field: protogen.Field, init_space_count: int, json_type: str):
        json_msg_str = ""
        if field.kind.name.lower() == "message":
            field_msg_name_case_styled = self.__case_style_convert_method(field.message.proto.name)
            if self.__response_field_case_style == "camel":
                field_msg_name_case_styled = field_msg_name_case_styled[0].upper() + field_msg_name_case_styled[1:]
            json_msg_str += \
                self.__handle_message_or_enum_type_json_schema('m', init_space_count, field_msg_name_case_styled,
                                                               json_type, field.message)
        elif field.kind.name.lower() == "enum":
            field_enum_name_case_styled = self.__case_style_convert_method(field.enum.proto.name)
            if self.__response_field_case_style == "camel":
                field_enum_name_case_styled = field_enum_name_case_styled.capitalize()
            json_msg_str += \
                self.__handle_message_or_enum_type_json_schema('e', init_space_count, field_enum_name_case_styled,
                                                               json_type, field.enum)
        else:
            if self.is_bool_option_enabled(field, JsonSchemaConvertPlugin.flux_fld_val_is_datetime):
                json_msg_str += ' ' * init_space_count + f'"type": "date-time"\n'
            else:
                json_msg_str += ' ' * init_space_count + f'"type": "{json_type}"\n'
        return json_msg_str

    def __handle_fld_leading_comment_as_attribute(self, field: protogen.Field, init_space_count: int) -> str:
        json_msg_str = ""
        if comment_str := field.location.leading_comments:
            flux_fld_removed_option_name = \
                JsonSchemaConvertPlugin.flux_fld_cmnt.lstrip(JsonSchemaConvertPlugin.fld_options_standard_prefix)
            flux_fld_removed_option_name_case_styled = self.__case_style_convert_method(flux_fld_removed_option_name)

            # Attaching multiple leading comments in one comment
            comment_str = ", ".join(comment_str.split("\n"))
            json_msg_str += ' ' * (
                init_space_count) + f'"{flux_fld_removed_option_name_case_styled}": "{comment_str}",\n'

        return json_msg_str

    def _validate_if_msg_attrs_exist(self, msg_attr_str: str, option_name: str):
        # cleaning msg_str containing full attribute path to be checked
        if ":" in msg_attr_str:
            msg_attr_str = msg_attr_str.split(":")[1]

        message_list = self.__json_layout_message_list + self.__json_non_layout_message_list
        msg_attr_dot_seperated_list = msg_attr_str.split(".")
        for message in message_list:
            if message.proto.name == msg_attr_dot_seperated_list[0]:
                parent_attr = msg_attr_dot_seperated_list[0]
                for attr in msg_attr_dot_seperated_list[1:]:
                    for field in message.fields:
                        if attr == field.proto.name:
                            if attr != msg_attr_dot_seperated_list[-1]:
                                message = field.message
                            parent_attr = attr
                            break
                    else:
                        err_str = f"Couldn't find attribute/field: {attr} in parent_attribute {parent_attr} of " \
                                  f"type message: {message.proto.name}, while validating given fields " \
                                  f"existence in message in {option_name} option"
                        logging.exception(err_str)
                        raise Exception(err_str)
                else:
                    break
        else:
            err_str = f"Couldn't find any message with name: {msg_attr_dot_seperated_list[0]}, while validating " \
                      f"if all attributes exists mentioned in {option_name} options"
            logging.exception(err_str)
            raise Exception(err_str)

    def __underlying_handle_options_value_having_msg_fld_name(self, option_val: str, option_name: str) -> str:
        mapping_key_value = ""
        if ":" in option_val:
            option_value_colan_sep = option_val.split(":")
            if len(option_value_colan_sep) != 2:
                err_str = (f"Unsupported option value in {option_name} option, Option value having mapping "
                           f"syntax using ':' in value must have instance of ':' only once;;; option_val: {option_val}")
                logging.exception(err_str)
                raise Exception(err_str)

            mapping_key_value = option_value_colan_sep[0]
            option_value_with_message_names = option_value_colan_sep[-1]
        else:
            option_value_with_message_names = option_val

        option_value_with_message_names_dot_sep: List[str] = option_value_with_message_names.split(".")
        for index, option_value_with_message_name in enumerate(option_value_with_message_names_dot_sep):
            # checking id field
            if "id" == option_value_with_message_name:
                option_value_with_message_names_dot_sep[index] = "_id"
            else:
                if index == 0:
                    # handling message names
                    if self.__response_field_case_style == "camel":
                        temp = self.__case_style_convert_method(option_value_with_message_name)
                        option_value_with_message_name_case_styled = temp[0].upper() + temp[1:]
                    else:
                        option_value_with_message_name_case_styled = (
                            self.__case_style_convert_method(option_value_with_message_name))
                    option_value_with_message_names_dot_sep[index] = option_value_with_message_name_case_styled
                else:
                    # handling field names
                    option_value_with_message_name_case_styled = (
                        self.__case_style_convert_method(option_value_with_message_name))
                    option_value_with_message_names_dot_sep[index] = option_value_with_message_name_case_styled

        option_value_with_message_names = ".".join(option_value_with_message_names_dot_sep)
        if mapping_key_value:
            option_value = f"{mapping_key_value}:{option_value_with_message_names}"
            return option_value
        else:
            return option_value_with_message_names

    def __handle_options_value_case_having_msg_fld_name(self, option_value: str, option_name: str):
        """
        Converting all message names and field names to specific case style
        note: option_name is just used in logging
        """
        # checking if option_value is not float type and is relevant to be used here
        if type(option_value).__name__ == "str" and \
                (("-" in option_value or "." in option_value) and any(char.isalpha() for char in option_value)):

            option_value_caret_separated = option_value.split("^")
            temp_list_1 = []

            for option_val in option_value_caret_separated:
                if '-' in option_val:
                    option_val_hyphen_separated = option_val.split('-')
                    temp_list_2 = []
                    for option_val in option_val_hyphen_separated:
                        # Validating if attribute path that is dot seperated valid or not
                        self._validate_if_msg_attrs_exist(option_val, option_name)

                        temp_str = self.__underlying_handle_options_value_having_msg_fld_name(option_val, option_name)
                        temp_list_2.append(temp_str)
                    temp_str_dollar_joined = "-".join(temp_list_2)
                    temp_list_1.append(temp_str_dollar_joined)
                else:
                    # Validating if attribute path that is dot seperated valid or not
                    self._validate_if_msg_attrs_exist(option_val, option_name)

                    temp_str = self.__underlying_handle_options_value_having_msg_fld_name(option_val, option_name)
                    temp_list_1.append(temp_str)
            return "^".join(temp_list_1)

        else:
            return option_value

    def __convert_option_name_to_json_attribute_name(self, option_name) -> str:
        if (fld_standard_prefix := JsonSchemaConvertPlugin.fld_options_standard_prefix) in option_name:
            flux_prefix_removed_option_name = option_name.removeprefix(fld_standard_prefix)
        elif (msg_standard_prefix := JsonSchemaConvertPlugin.msg_options_standard_prefix) in option_name:
            flux_prefix_removed_option_name = option_name.removeprefix(msg_standard_prefix)
        else:
            err_str = f"No Standard option prefix found in option {option_name} from option_list"
            logging.exception(err_str)
            raise Exception(err_str)
        return flux_prefix_removed_option_name

    def __handle_simple_proto_option_attributes(self, options_list: List[str],
                                                field_or_message_obj: protogen.Field | protogen.Message,
                                                init_space_count: int) -> str:
        """
        Handles both repeated and non-repeated simple type of options
        """
        json_msg_str = ""
        for option in options_list:
            if self.is_option_enabled(field_or_message_obj, option):
                if option in (self.flx_fld_simple_non_repeated_attribute_options +
                              self.flx_msg_simple_non_repeated_attribute_options):
                    option_value: str | int | bool | float = (
                        self.get_simple_option_value_from_proto(field_or_message_obj, option))

                    if option == JsonSchemaConvertPlugin.flux_fld_help:
                        if "'" in option_value:
                            err_str = "FluxFldHelp must have string without singe quotation mark ('), found in " \
                                      f"{option_value} option value of field {field_or_message_obj} of message " \
                                      f"{field_or_message_obj.message}"
                            logging.exception(err_str)
                            raise Exception(err_str)
                        # else not required: If help option value contains string without "'" (single quotation mark),
                        # then proceeding for further processing, since "'" causes issues with json once generated

                        # Adding Max/min Val option value in help comment if present
                        if self.is_option_enabled(field_or_message_obj, JsonSchemaConvertPlugin.flux_fld_val_max):
                            max_val = \
                                self.get_simple_option_value_from_proto(field_or_message_obj,
                                                                        JsonSchemaConvertPlugin.flux_fld_val_max)
                            option_value = f'{option_value}, Max Value: {max_val}'
                        if self.is_option_enabled(field_or_message_obj, JsonSchemaConvertPlugin.flux_fld_val_min):
                            min_val = \
                                self.get_simple_option_value_from_proto(field_or_message_obj,
                                                                        JsonSchemaConvertPlugin.flux_fld_val_min)
                            option_value = f'{option_value}, Min Value: {min_val}'
                    # else not required: if option is not flux_fld_help then avoiding check

                    if option in JsonSchemaConvertPlugin.options_having_msg_fld_names:
                        option_value = self.__handle_options_value_case_having_msg_fld_name(option_value, option)
                    elif option == JsonSchemaConvertPlugin.flux_fld_auto_complete:
                        autocomplete_option_val = \
                            self.get_simple_option_value_from_proto(field_or_message_obj,
                                                                    JsonSchemaConvertPlugin.flux_fld_auto_complete)
                        if autocomplete_option_val.startswith("sec_id~"):
                            sec_id_val = autocomplete_option_val.split(",")[0].split("~")[-1]
                            msg_name_in_option_val = sec_id_val.split(".")[0]
                            msg_name_in_option_val_snake_cased = (
                                convert_camel_case_to_specific_case(msg_name_in_option_val))
                            option_value = autocomplete_option_val.replace(msg_name_in_option_val,
                                                                           msg_name_in_option_val_snake_cased)
                        # else not required: msg/fld name not in value of sec_id since ~ signifies use of
                        # msg/fld in auto_complete as sec_id value
                    # else not required: no handling required if option is not in options_having_msg_fld_names
                    # or option is not flux_fld_auto_complete with msg/fld name in value of sec_id

                    # converting flux_option into json attribute name
                    flux_prefix_removed_option_name = self.__convert_option_name_to_json_attribute_name(option)
                    flux_prefix_removed_option_name_case_styled = \
                        self.__case_style_convert_method(flux_prefix_removed_option_name)

                    if option in [JsonSchemaConvertPlugin.flux_fld_val_min, JsonSchemaConvertPlugin.flux_fld_val_max]:
                        option_value = BaseProtoPlugin.parse_string_to_original_types(option_value)
                    # else not required: # flux_fld_val_min and flux_fld_val_max needs special handling that
                    # if value is message path then it will be str but if is float as str then value must be float type

                    json_msg_str += ' ' * init_space_count + \
                                    (f'"{flux_prefix_removed_option_name_case_styled}": '
                                     f'{self.parse_python_type_to_json_type_str(option_value)},\n')
                elif option in (self.flx_fld_simple_repeated_attribute_options +
                                self.flx_msg_simple_repeated_attribute_options):
                    option_value_list: List = self.get_simple_option_value_from_proto(field_or_message_obj, option,
                                                                                      is_repeated=True)

                    if option in JsonSchemaConvertPlugin.options_having_msg_fld_names:
                        for index, option_value in enumerate(option_value_list):
                            option_value_list[index] = (
                                self.__handle_options_value_case_having_msg_fld_name(option_value, option))
                    # else not required: if option is not in options_having_msg_fld_names then avoid

                    if option == BaseProtoPlugin.flux_fld_projections:
                        projection_val_to_fields_dict = BaseProtoPlugin.get_projection_option_value_to_fields(
                            field_or_message_obj.parent)
                        projection_val_to_query_name_dict = (
                            JsonSchemaConvertPlugin.get_projection_temp_query_name_to_generated_query_name_dict(
                                field_or_message_obj.parent))
                        for index, option_value in enumerate(option_value_list):
                            if ":" in option_value:
                                option_val_colan_sep = option_value.split(":")
                                mapping_key = option_val_colan_sep[0]
                                query_name_replace_str = option_val_colan_sep[-1]
                                query_name = projection_val_to_query_name_dict.get(query_name_replace_str)
                                field_names = projection_val_to_fields_dict.get(query_name_replace_str)
                                field_name_list: List[str] = []
                                for field_name in field_names:
                                    if "." in field_name:
                                        field_name_list.append("_".join(field_name.split(".")))
                                    else:
                                        field_name_list.append(field_name)
                                field_names_str = "_n_".join(field_name_list)

                                if query_name is None:
                                    err_str = (f"Could not find query name for '{query_name_replace_str}' key in dict "
                                               f"provided by get_projection_field_query_name method, "
                                               f"{JsonSchemaConvertPlugin.flux_fld_projections} option val: "
                                               f"{option_value} set on field {field_or_message_obj.proto.name} of "
                                               f"message {field_or_message_obj.parent.proto.name}")
                                    logging.exception(err_str)
                                    raise Exception(err_str)

                                option_value_list[index] = \
                                    f"{field_names_str}:{query_name}"
                            else:
                                query_name = projection_val_to_query_name_dict.get(option_value)
                                field_names = projection_val_to_fields_dict.get(option_value)
                                field_name_list: List[str] = []
                                for field_name in field_names:
                                    if "." in field_name:
                                        field_name_list.append("_".join(field_name.split(".")))
                                    else:
                                        field_name_list.append(field_name)
                                field_names_str = "_n_".join(field_name_list)
                                if query_name is None:
                                    err_str = (f"Could not find query name in dict "
                                               f"provided by get_projection_field_query_name method, "
                                               f"{JsonSchemaConvertPlugin.flux_fld_projections} option val: "
                                               f"{option_value} set on field {field_or_message_obj.proto.name} of "
                                               f"message {field_or_message_obj.parent.proto.name}")
                                    logging.exception(err_str)
                                    raise Exception(err_str)
                                option_value_list[index] = f"{field_names_str}:{query_name}"
                    elif option == BaseProtoPlugin.flux_fld_mapping_projection_query_field:
                        projection_val_to_query_name_dict = (
                            JsonSchemaConvertPlugin.get_projection_temp_query_name_to_generated_query_name_dict(
                                field_or_message_obj.parent))
                        for index, option_value in enumerate(option_value_list):
                            field_path_str: str = ""
                            if ":" in option_value:
                                option_val_colan_sep = option_value.split(":")
                                temp_query_name = option_val_colan_sep[0]
                                field_path_str = option_val_colan_sep[-1]
                            else:
                                temp_query_name = option_value
                            query_name = projection_val_to_query_name_dict.get(temp_query_name)
                            if ":" in option_value:
                                option_value_list[index] = f"{query_name}:{field_path_str}"
                            else:
                                option_value_list[index] = f"{query_name}"
                    # else not required: this handlings are only required for
                    # BaseProtoPlugin.flux_fld_projections or BaseProtoPlugin.flux_fld_mapping_projection_query_field

                    # converting flux_option into json attribute name
                    flux_prefix_removed_option_name = self.__convert_option_name_to_json_attribute_name(option)
                    flux_prefix_removed_option_name_case_styled = \
                        self.__case_style_convert_method(flux_prefix_removed_option_name)
                    json_msg_str += ' ' * init_space_count + \
                                    f'"{flux_prefix_removed_option_name_case_styled}": [\n'
                    for option_value in option_value_list:
                        json_msg_str += (' ' * (init_space_count+2) +
                                         f'{self.parse_python_type_to_json_type_str(option_value)}')
                        if option_value == option_value_list[-1]:
                            json_msg_str += '\n'
                        else:
                            json_msg_str += ',\n'
                    json_msg_str += ' ' * init_space_count + "],\n"

        return json_msg_str

    def __handle_complex_proto_option_attributes(self, options_list: List[str],
                                                 field_or_message_obj: protogen.Field | protogen.Message,
                                                 init_space_count: int) -> str:
        json_msg_str = ""
        for option in options_list:

            if self.is_option_enabled(field_or_message_obj, option):
                if option in (self.flx_fld_complex_non_repeated_attribute_options +
                              self.flx_msg_complex_non_repeated_attribute_options):
                    option_value_dict: Dict = \
                        self.get_complex_option_value_from_proto(field_or_message_obj, option)
                    # converting flux_option into json attribute name
                    flux_prefix_removed_option_name = self.__convert_option_name_to_json_attribute_name(option)
                    flux_prefix_removed_option_name_case_styled = \
                        self.__case_style_convert_method(flux_prefix_removed_option_name)
                    json_msg_str += self._get_json_complex_key_value_str(flux_prefix_removed_option_name_case_styled,
                                                                         option_value_dict, int(init_space_count/2))

                    if option == JsonSchemaConvertPlugin.flux_fld_button:
                        json_msg_str_splitted_list = json_msg_str.split("\n")
                        for index, line in enumerate(json_msg_str_splitted_list):
                            if ':' in line and "{" not in line and "[" not in line:
                                if '"' not in line[line.index(":")+1:]:
                                    key_str: str
                                    val_str: str
                                    key_str, val_str = line.split(":")

                                    if val_str.endswith(","):
                                        val_str = f' "{val_str[:-1].strip()}",'
                                    else:
                                        val_str = f' "{val_str.strip()}"'

                                    json_msg_str_splitted_list[index] = f"{key_str}:{val_str}"
                        json_msg_str = "\n".join(json_msg_str_splitted_list)
                    # else not required: if option is not flux_fld_button then avoid as only this option
                    # has dependency to keep every option field as str, more specifically it has some fields
                    # which needs to have value 'true' or 'false' as string form but since in plugin handling
                    # if any field is found having value as string form of bool then it is type-cast to
                    # json bool, to avoid this explicitly value is turned into str bool
                elif option in (self.flx_fld_complex_repeated_attribute_options +
                                self.flx_msg_complex_repeated_attribute_options):
                    option_value_dict: List[Dict] = \
                        self.get_complex_option_value_from_proto(field_or_message_obj, option)
                    # converting flux_option into json attribute name
                    flux_prefix_removed_option_name = self.__convert_option_name_to_json_attribute_name(option)
                    flux_prefix_removed_option_name_case_styled = \
                        self.__case_style_convert_method(flux_prefix_removed_option_name)

                    json_msg_str += self._get_json_complex_key_value_str(flux_prefix_removed_option_name_case_styled,
                                                                         option_value_dict, int(init_space_count / 2))

        return json_msg_str

    def parse_python_type_to_json_type_str(self, value: str) -> str | int | bool | float:
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            return f'"{value}"'
        else:
            return value

    def __handle_fld_default_value(self, field: protogen.Field, init_space_count: int) -> str:
        """
        Sets pre-defined default values from model
        """
        if default_value := field.proto.default_value:
            default_value = self.parse_string_to_original_types(default_value)
            return ' ' * init_space_count + f'"default": {self.parse_python_type_to_json_type_str(default_value)},\n'
        else:
            return ""

    def __handle_fld_sequence_number_attribute(self, field: protogen.Field, init_space_count: int) -> str:
        sequence_number: int = field.proto.number
        sequence_number_option_name = JsonSchemaConvertPlugin.flux_fld_sequence_number
        if self.is_option_enabled(field, sequence_number_option_name):
            sequence_number = self.get_simple_option_value_from_proto(field, sequence_number_option_name)
        # else not required: if sequence_number not set using option then using default assigned value
        sequence_number_option_name_prefix_removed = \
            sequence_number_option_name.lstrip(JsonSchemaConvertPlugin.fld_options_standard_prefix)
        sequence_number_option_name_prefix_removed_case_styled = \
            self.__case_style_convert_method(sequence_number_option_name_prefix_removed)
        output_str = ' ' * init_space_count + f'"{sequence_number_option_name_prefix_removed_case_styled}": ' \
                                              f'{sequence_number},\n'
        return output_str

    def __underlying_handle_title_output(self, field_or_msg_obj: protogen.Field | protogen.Message) -> str | None:
        if isinstance(field_or_msg_obj, protogen.Field):
            if self.is_option_enabled(field_or_msg_obj, JsonSchemaConvertPlugin.flux_fld_title):
                title_option_value = \
                    self.get_simple_option_value_from_proto(field_or_msg_obj,
                                                            JsonSchemaConvertPlugin.flux_fld_title)
                return title_option_value
            else:
                return None
        elif isinstance(field_or_msg_obj, protogen.Message):
            if self.is_option_enabled(field_or_msg_obj, JsonSchemaConvertPlugin.flux_msg_title):
                title_option_value = \
                    self.get_simple_option_value_from_proto(field_or_msg_obj,
                                                            JsonSchemaConvertPlugin.flux_msg_title)
                return title_option_value
            else:
                return None
        else:
            err_str = f"Unexpected type instance received, must be either protogen.Field or protogen.Message, " \
                      f"got {type(field_or_msg_obj)}"
            logging.exception(err_str)
            raise Exception(err_str)

    def __underlying_fld_output_handler(self, field: protogen.Field, init_space_count: int) -> str:
        field_name: str = field.proto.name
        if field_name == JsonSchemaConvertPlugin.default_id_field_name:
            field_name = "_id"
        # else not required: if field name is not ´id´ then add it to json schema

        if self.__response_field_case_style.lower() == "camel":
            # Converting field name (snake cased) to camel_case
            field_name_case_styled = self.__case_style_convert_method(field_name)
        elif self.__response_field_case_style.lower() == "snake":
            field_name_case_styled = field_name
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)

        json_msg_str = ' ' * init_space_count + f'"{field_name_case_styled}": ' + '{\n'
        underlying_type, json_type = self.__proto_data_type_to_json(field)
        # Adding simple type non-repeated options as attributes
        json_msg_str += \
            self.__handle_simple_proto_option_attributes(
                JsonSchemaConvertPlugin.flx_fld_simple_non_repeated_attribute_options, field, init_space_count + 2)
        # Adding simple type repeated options as attributes
        json_msg_str += \
            self.__handle_simple_proto_option_attributes(
                JsonSchemaConvertPlugin.flx_fld_simple_repeated_attribute_options, field, init_space_count + 2)
        # Adding complex type non-repeated options as attributes
        json_msg_str += \
            self.__handle_complex_proto_option_attributes(
                JsonSchemaConvertPlugin.flx_fld_complex_non_repeated_attribute_options, field, init_space_count + 2)
        # Adding complex type repeated options as attributes
        json_msg_str += \
            self.__handle_complex_proto_option_attributes(
                JsonSchemaConvertPlugin.flx_fld_complex_repeated_attribute_options, field, init_space_count + 2)
        # Adding default value as attribute if present
        json_msg_str += self.__handle_fld_default_value(field, init_space_count + 2)

        # Adding leading comment as FluxFldCmnt attribute
        json_msg_str += self.__handle_fld_leading_comment_as_attribute(field, init_space_count + 2)

        if (title_option_value := self.__underlying_handle_title_output(field)) is not None:
            json_msg_str += (' ' * (init_space_count + 2) + f'"title": '
                             f'{self.parse_python_type_to_json_type_str(title_option_value)},\n')
        else:
            field_name_spaced = str(field.proto.name).replace("_", " ")
            json_msg_str += (' ' * (init_space_count + 2) + f'"title": '
                             f'"{field_name_spaced}",\n')
        json_msg_str += self.__handle_fld_sequence_number_attribute(field, init_space_count + 2)
        underlying_type_attr_case_styled = self.__case_style_convert_method("underlying_type")
        if underlying_type != json_type:
            json_msg_str += ' ' * (init_space_count + 2) + \
                            f'"{underlying_type_attr_case_styled}": "{underlying_type}",\n'
        # else not required: if underlying_type and json_type are same then avoiding underlying type
        json_msg_str += self.__handle_field_json_type_schema(field, init_space_count + 2, json_type)
        return json_msg_str

    def __underlying_json_output_handler(self, message: protogen.Message, init_space_count: int) -> str:
        json_msg_str = ""
        if (title_option_value := self.__underlying_handle_title_output(message)) is not None:
            json_msg_str += (' ' * init_space_count + f'"title": '
                             f'{self.parse_python_type_to_json_type_str(title_option_value)},\n')
        else:
            # Space separated names
            message_name_spaced = convert_camel_case_to_specific_case(message.proto.name, " ", False)
            json_msg_str += (' ' * init_space_count + f'"title": '
                             f'"{message_name_spaced}",\n')
        json_msg_str += ' ' * init_space_count + '"type": "object",\n'
        json_msg_str += ' ' * init_space_count + '"properties": {\n'

        required_field_names: List[str] = []
        for field in message.fields:
            required_field_names = self.__add_required_field_names_to_list(required_field_names, field)
            json_msg_str += self.__underlying_fld_output_handler(field, init_space_count + 2)
            if field == message.fields[-1]:
                json_msg_str += ' ' * (init_space_count + 2) + '}\n'
            else:
                json_msg_str += ' ' * (init_space_count + 2) + '},\n'
        json_msg_str += ' ' * init_space_count + '},\n'

        if required_field_names:
            json_msg_str += ' ' * init_space_count + '"required": [\n'
            json_msg_str += self.__handle_required_json_schema(init_space_count, required_field_names)
            json_msg_str += ' ' * init_space_count + ']\n'
        else:
            json_msg_str += ' ' * init_space_count + '"required": []\n'
        return json_msg_str

    def __handle_msg_leading_comment_as_attribute(self, message: protogen.Message, init_space_count: int) -> str:
        json_msg_str = ""
        if comment_str := message.location.leading_comments:
            flux_msg_prefix_removed_option_name = \
                JsonSchemaConvertPlugin.flux_msg_cmnt.lstrip(JsonSchemaConvertPlugin.msg_options_standard_prefix)
            flux_msg_removed_option_name_case_styled = \
                self.__case_style_convert_method(flux_msg_prefix_removed_option_name)

            # Attaching multiple leading comments in one comment
            comment_str = ", ".join(comment_str.split("\n"))
            json_msg_str += ' ' * init_space_count + f'"{flux_msg_removed_option_name_case_styled}": "{comment_str}",\n'
        return json_msg_str

    def __handle_underlying_message_part(self, message: protogen.Message, indent_space_count: int):
        json_msg_str = self.__handle_simple_proto_option_attributes(
            JsonSchemaConvertPlugin.flx_msg_simple_non_repeated_attribute_options, message, indent_space_count)
        json_msg_str += self.__handle_msg_leading_comment_as_attribute(message, indent_space_count)
        # Handling json root attribute
        if (self.is_option_enabled(message, JsonSchemaConvertPlugin.flux_msg_json_root) or
                self.is_option_enabled(message, JsonSchemaConvertPlugin.flux_msg_json_root_time_series)):
            json_root_prefix_stripped = \
                JsonSchemaConvertPlugin.flux_msg_json_root.lstrip(JsonSchemaConvertPlugin.msg_options_standard_prefix)
            json_root_prefix_stripped_case_styled = self.__case_style_convert_method(json_root_prefix_stripped)
            json_msg_str += " " * indent_space_count + f'"{json_root_prefix_stripped_case_styled}": true,\n'
        json_msg_str += self.__underlying_json_output_handler(message, indent_space_count)
        return json_msg_str

    def _get_json_formatted_value_str_for_list_n_dict(self, option_value: List | Dict, indent_count: int,
                                                      add_brackets: bool | None = None,
                                                      add_dict_key: str | None = None) -> str:
        output_str = ""
        if isinstance(option_value, list):
            if add_brackets:
                output_str += " " * (indent_count * 2) + "[\n"
                indent_count += 1
            for value in option_value:
                if isinstance(value, list) or isinstance(value, dict):
                    output_str += self._get_json_formatted_value_str_for_list_n_dict(value, indent_count,
                                                                                     True)
                elif isinstance(value, str):
                    output_str += (" " * (indent_count*2) +
                                   self.parse_python_type_to_json_type_str(self.parse_string_to_original_types(value)))
                elif isinstance(value, bool):
                    output_str += " " * (indent_count*2) + "true" if value else "false"
                else:
                    output_str += " " * (indent_count*2) + value

                if value != option_value[-1]:
                    output_str += ",\n"
                else:
                    output_str += "\n"

            if add_brackets:
                indent_count -= 1
                output_str += " " * (indent_count * 2) + "]"

            return output_str
        elif isinstance(option_value, dict):
            if add_brackets:
                output_str += " " * (indent_count * 2) + "{\n"
                indent_count += 1
            if add_dict_key:
                output_str += " " * (indent_count * 2) + f'"{add_dict_key}": ' + "{\n"
                indent_count += 1

            for key, value in option_value.items():
                if isinstance(value, list):
                    if key in JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element_fields_having_msg_n_fld_names_in_val:
                        for idx, v in enumerate(value):
                            v = f"{self.__underlying_handle_options_value_having_msg_fld_name(v, JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)}"
                            value[idx] = v
                    output_str += " " * (indent_count*2) + f'"{key}": [\n'
                    indent_count += 1
                    output_str += self._get_json_formatted_value_str_for_list_n_dict(value, indent_count)
                    indent_count -= 1
                    output_str += " " * (indent_count * 2) + f']'
                elif isinstance(value, dict):
                    output_str += self._get_json_formatted_value_str_for_list_n_dict(value, indent_count,
                                                                                     add_dict_key=key)
                elif isinstance(value, str):
                    if key in JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element_fields_having_msg_n_fld_names_in_val:
                        value = f"{self.__underlying_handle_options_value_having_msg_fld_name(value, JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)}"
                    output_str += (" " * (indent_count*2) + f'"{key}": '
                                   f'{self.parse_python_type_to_json_type_str(self.parse_string_to_original_types(value))}')
                elif isinstance(value, bool):
                    output_str += " " * (indent_count*2) + f'"{key}": {"true" if value else "false"}'
                else:
                    output_str += " " * (indent_count*2) + f'"{key}": {value}'

                if key != list(option_value.keys())[-1]:
                    output_str += ",\n"
                else:
                    output_str += "\n"

            if add_brackets or add_dict_key:
                indent_count -= 1
                output_str += " " * (indent_count * 2) + "}"

            return output_str
        else:
            err_str = f"Unexpected option_value type: {type(option_value)}, expected dict or list"
            logging.exception(err_str)
            raise Exception(err_str)

    def _get_json_complex_key_value_dict_str(self, option_value_dict: Dict, indent_count: int | None = None) -> str:
        output_str = "{\n"
        indent_count += 1
        for key, value in option_value_dict.items():
            if isinstance(value, list):
                output_str += " " * (indent_count * 2) + f'"{key}": [\n'
                indent_count += 1
                output_str += self._get_json_formatted_value_str_for_list_n_dict(value, indent_count)
                indent_count -= 1
                output_str += " " * (indent_count * 2) + f']'
            elif isinstance(value, dict):
                output_str += " " * (indent_count * 2) + f'"{key}": ' + '{\n'
                indent_count += 1
                output_str += self._get_json_formatted_value_str_for_list_n_dict(value, indent_count)
                indent_count -= 1
                output_str += " " * (indent_count * 2) + '}'
            elif isinstance(value, str):
                if key in JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element_fields_having_msg_n_fld_names_in_val:
                    value = f"{self.__underlying_handle_options_value_having_msg_fld_name(value, JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)}"
                output_str += " " * (indent_count * 2) + (f'"{key}": '
                              f'{self.parse_python_type_to_json_type_str(self.parse_string_to_original_types(value))}')
            elif isinstance(value, bool):
                output_str += " " * (indent_count * 2) + f'"{key}": {"true" if value else "false"}'
            else:
                output_str += " " * (indent_count * 2) + f'"{key}": {value}'

            if key != list(option_value_dict.keys())[-1]:
                output_str += ",\n"
            else:
                indent_count -= 1
                output_str += "\n"
                output_str += " " * (indent_count * 2) + "}"
        return output_str

    def _get_json_complex_key_value_str(self, option_name: str, option_value_dict_or_list: Dict | List[Dict],
                                        indent_count: int | None = None) -> str:
        if indent_count is None:
            indent_count = 0
        output_str = " " * (indent_count*2) + f'"{option_name}": '
        if isinstance(option_value_dict_or_list, dict):
            output_str += self._get_json_complex_key_value_dict_str(option_value_dict_or_list, indent_count)
        elif isinstance(option_value_dict_or_list, list):
            output_str += '[\n'
            for option_value in option_value_dict_or_list:
                output_str += (" " * ((indent_count*2) + 2) +
                               self._get_json_complex_key_value_dict_str(option_value, indent_count))
            output_str += " " * (indent_count*2) + f']'
        output_str += ",\n"
        return output_str

    def __handle_connection_details_output(self, message: protogen.Message, indent_count: int) -> str:
        widget_ui_data_option_value_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)

        # Also checking if msg is from another project used in this project
        is_not_from_this_project: bool = True
        other_project_name: str | None = None
        for project_name, message_list in self._proto_project_name_to_msg_list_dict.items():
            if project_name != self._current_project_name:
                if message in message_list and message.proto.name not in self.__main_file_message_name_list:
                    is_not_from_this_project: bool = False
                    other_project_name = project_name
                    break

        json_msg_str = ""
        if not is_not_from_this_project:
            proto_model_name = widget_ui_data_option_value_dict.get(
                JsonSchemaConvertPlugin.widget_ui_option_depending_proto_model_name_field)
            dynamic_url = widget_ui_data_option_value_dict.get(
                JsonSchemaConvertPlugin.widget_ui_option_depends_on_other_model_for_dynamic_url_field)
            indent_count += 2
            json_msg_str += (" " * indent_count) + '"connection_details": {\n'
            indent_count += 2
            if dynamic_url:
                proto_model_name_case_styled = self.__case_style_convert_method(proto_model_name)
                json_msg_str += (" " * indent_count) + f'"host": "{proto_model_name_case_styled}.host",\n'
                json_msg_str += (" " * indent_count) + f'"port": "{proto_model_name_case_styled}.port",\n'

                json_msg_str += (" " * indent_count) + f'"project_name": "{other_project_name}",\n'
                json_msg_str += (" " * indent_count) + f'"dynamic_url": true\n'
            else:
                # checking project name in project group
                # current_project_model_path = self._current_project_model_file.

                current_project_dir = os.getenv("PROJECT_DIR")
                if current_project_dir is None or not current_project_dir:
                    err_str = f"Env var PROJECT_DIR received as {current_project_dir}"
                    logging.exception(err_str)
                    raise Exception(err_str)

                other_project_config_file_path = (PurePath(current_project_dir).parent /
                                                  other_project_name / "data" / "config.yaml")
                other_project_config_yaml_dict = (
                    YAMLConfigurationManager.load_yaml_configurations(str(other_project_config_file_path)))
                host = other_project_config_yaml_dict.get("server_host")
                port = other_project_config_yaml_dict.get("main_server_beanie_port")

                json_msg_str += (" " * indent_count) + f'"host": "{host}",\n'
                json_msg_str += (" " * indent_count) + f'"port": {port},\n'
                json_msg_str += (" " * indent_count) + f'"project_name": "{other_project_name}",\n'
                json_msg_str += (" " * indent_count) + f'"dynamic_url": false\n'
            indent_count -= 2
            json_msg_str += (" " * indent_count) + '},\n'
        return json_msg_str

    def __handle_widget_ui_data_option_output(self, message: protogen.Message) -> str:
        widget_ui_data_prefix_stripped = \
            JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element.lstrip(
                JsonSchemaConvertPlugin.msg_options_standard_prefix)
        widget_ui_data_option_value_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     JsonSchemaConvertPlugin.flux_msg_widget_ui_data_element)

        widget_ui_data_key = self.__case_style_convert_method(widget_ui_data_prefix_stripped)

        if "i" not in widget_ui_data_option_value_dict:
            widget_ui_data_option_value_dict["i"] = f"{self.__case_style_convert_method(message.proto.name)}"

        indent_count = 2
        json_msg_str = self._get_json_complex_key_value_str(widget_ui_data_key, widget_ui_data_option_value_dict,
                                                            indent_count)
        return json_msg_str

    def __handle_json_layout_message_schema(self, message: protogen.Message) -> str:
        json_msg_str = ''
        if self.__response_field_case_style.lower() == "snake":
            message_name = self.__case_style_convert_method(message.proto.name)
        elif self.__response_field_case_style.lower() == "camel":
            message_name = message.proto.name
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
        json_msg_str += f'  "{message_name}": ' + '{\n'
        json_msg_str += '    "$schema": "http://json-schema.org/draft-04/schema#",\n'
        json_msg_str += self.__handle_widget_ui_data_option_output(message)
        if message in self.__root_msg_list:
            json_msg_str += self.__handle_connection_details_output(message, indent_count=2)
        json_msg_str += self.__handle_underlying_message_part(message, 4)
        if message != self.__json_layout_message_list[-1] or self.__enum_list:
            json_msg_str += '  },\n'
        else:
            json_msg_str += '  }\n'
        return json_msg_str

    def __handle_json_complex_type_schema(self, message: protogen.Message) -> str:
        json_msg_str = ''
        if self.__response_field_case_style.lower() == "snake":
            message_name = self.__case_style_convert_method(message.proto.name)
        elif self.__response_field_case_style.lower() == "camel":
            message_name = message.proto.name
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
        json_msg_str += f'    "{message_name}": ' + '{\n'
        if message in self.__root_msg_list:
            json_msg_str += self.__handle_connection_details_output(message, indent_count=4)
        json_msg_str += self.__handle_underlying_message_part(message, 6)
        if message != self.__json_non_layout_message_list[-1]:
            json_msg_str += '    },\n'
        else:
            if self.__enum_list:
                json_msg_str += '    },\n'
            else:
                json_msg_str += '    }\n'
        return json_msg_str

    def __handle_json_enum_type_schema(self, enum: protogen.Enum) -> str:
        json_msg_str = ''
        if self.__response_field_case_style.lower() == "snake":
            enum_name = self.__case_style_convert_method(enum.proto.name)
        elif self.__response_field_case_style.lower() == "camel":
            enum_name = enum.proto.name
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
        json_msg_str += f'    "{enum_name}": ' + '{\n'
        json_msg_str += f'      "enum": [\n'
        for value in enum.values:
            if value != enum.values[-1]:
                json_msg_str += f'        "{value.proto.name}",\n'
            else:
                json_msg_str += f'        "{value.proto.name}"\n'
        json_msg_str += f'      ]\n'

        if enum == self.__enum_list[-1]:
            json_msg_str += '    }\n'
        else:
            json_msg_str += '    },\n'
        return json_msg_str

    def __handle_auto_complete_output(self, json_content: Dict) -> str:
        json_msg_str = f'  "autocomplete": ' + f"{json.dumps(json_content['autocomplete'], indent=4)}\n"
        return json_msg_str

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        if isinstance(file, list):
            for f in file:
                self._proto_project_name_to_msg_list_dict[f.proto.package] = f.messages
                self.__load_json_layout_and_non_layout_messages_in_dicts(f)
            file = file[0]  # since first file will be this project's proto file
            self.__main_file_message_name_list = [p.proto.name for p in file.messages]
            self._current_project_name = file.proto.package
            self._current_project_model_file = file
        else:
            self.__load_json_layout_and_non_layout_messages_in_dicts(file)
        # Performing Recursion to messages (including nested type) to get json layout, non-layout and enums and
        # adding to their respective data-member
        if self.__response_field_case_style.lower() == "snake":
            self.__case_style_convert_method = convert_camel_case_to_specific_case
        elif self.__response_field_case_style.lower() == "camel":
            self.__case_style_convert_method = convert_to_camel_case
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)

        # sorting created message lists
        self.__json_layout_message_list.sort(key=lambda message_: message_.proto.name)
        self.__json_non_layout_message_list.sort(key=lambda message_: message_.proto.name)
        self.__enum_list.sort(key=lambda message_: message_.proto.name)

        json_msg_str = '{\n'

        # Handling json layout message schema
        for message in self.__json_layout_message_list:
            json_msg_str += self.__handle_json_layout_message_schema(message)

        # Handling json non-layout message and json enum schema
        if self.__json_non_layout_message_list or self.__enum_list:
            json_msg_str += '  "definitions": {\n'

            for message in self.__json_non_layout_message_list:
                json_msg_str += self.__handle_json_complex_type_schema(message)

            for enum in self.__enum_list:
                json_msg_str += self.__handle_json_enum_type_schema(enum)
        # else not required: Avoiding if non-root messages are not available

        # Handling autocomplete json list
        if self.__add_autocomplete_dict:
            if (autocomplete_file_path := os.getenv("AUTOCOMPLETE_FILE_PATH")) is not None and \
                    len(autocomplete_file_path):
                json_msg_str += '  },\n'

                with open(autocomplete_file_path) as json_fl:
                    json_content = json.load(json_fl)

                json_msg_str += self.__handle_auto_complete_output(json_content)
            else:
                err_str = f"Env var AUTOCOMPLETE_FILE_PATH received as {autocomplete_file_path}"
                logging.exception(err_str)
                raise Exception(err_str)
        else:
            json_msg_str += '  }\n'

        json_msg_str += '}'

        file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{file_name}_json_schema.json"
        return {
            output_file_name: json_msg_str
        }


if __name__ == "__main__":
    main(JsonSchemaConvertPlugin)
