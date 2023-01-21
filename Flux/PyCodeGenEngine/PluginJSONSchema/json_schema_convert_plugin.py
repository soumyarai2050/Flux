#!/usr/bin/env python
import json
import logging
import os
from typing import List, Callable, Dict, Tuple
import time
import re

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, convert_to_camel_case


class JsonSchemaConvertPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    # Used to be added as property
    flx_fld_simple_attribute_options: List[str] = [
        "FluxFldHelp",
        "FluxFldHide",
        "FluxFldValSortWeight",
        "FluxFldAbbreviated",
        "FluxFldSticky",
        "FluxFldSizeMax",
        "FluxFldOrmNoUpdate",
        "FluxFldSwitch",
        "FluxFldAutoComplete",
        "FluxFldServerPopulate",
        "FluxFldColor",
        "FluxFldAlertBubbleSource",
        "FluxFldAlertBubbleColor",
        "FluxFldDefaultValuePlaceholderString",
        "FluxFldUIPlaceholder",
        "FluxFldUIUpdateOnly",
        "FluxFldValMax",
        "FluxFldValMin",
        "FluxFldElaborateTitle",
        "FluxFldNameColor"
    ]
    # Used to be added as property
    flx_fld_complex_attribute_options: List[str] = [
        "FluxFldButton",
        "FluxFldProgressBar"
    ]
    options_having_msg_fld_names: List[str] = [
        "FluxFldAbbreviated",
        "FluxFldAlertBubbleSource",
        "FluxFldAlertBubbleColor",
        "FluxFldValMax"
    ]
    # Used to be added as property
    flx_msg_simple_attribute_options: List[str] = [
        "FluxMsgServerPopulate"
    ]

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.__json_output_handler
        ]
        response_field_case_style = None
        if (output_file_name_suffix := os.getenv("OUTPUT_FILE_NAME_SUFFIX")) is not None and \
                (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None:
            self.output_file_name_suffix = output_file_name_suffix
            self.__response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME_SUFFIX' and 'RESPONSE_FIELD_CASE_STYLE' " \
                      f"received as {output_file_name_suffix} and {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.__json_layout_message_list: List[protogen.Message] = []
        self.__json_non_layout_message_list: List[protogen.Message] = []
        self.__enum_list: List[protogen.Enum] = []
        self.__case_style_convert_method: Callable[[str], str] | None = None

    def __proto_data_type_to_json(self, field: protogen.Field) -> Tuple[str, str]:
        underlying_type = field.kind.name.lower()
        if field.cardinality.name.lower() == "repeated":
            json_type = "array"
        else:
            json_type = JsonSchemaConvertPlugin.proto_type_to_json_type_dict[underlying_type]
        return underlying_type, json_type

    def __load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.__enum_list:
                    self.__enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if JsonSchemaConvertPlugin.flx_msg_widget_ui_data in str(field.message.proto.options):
                    widget_ui_data_option_list_of_dict = \
                        self.get_complex_option_values_as_list_of_dict(field.message,
                                                                       JsonSchemaConvertPlugin.flx_msg_widget_ui_data)[0]
                    if "layout" in widget_ui_data_option_list_of_dict:
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

    def __load_json_layout_and_non_layout_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if JsonSchemaConvertPlugin.flx_msg_widget_ui_data in str(message.proto.options):
                widget_ui_data_option_list_of_dict = \
                    self.get_complex_option_values_as_list_of_dict(message,
                                                                   JsonSchemaConvertPlugin.flx_msg_widget_ui_data)[0]
                if "layout" in widget_ui_data_option_list_of_dict:
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

    def __parse_string_to_original_types(self, value: str) -> str | int | bool | float:
        """
        Returns int if value string contains only numbers, bool if value contains string parsed bool
        and returns same value if both cases are not matched
        """
        # bool check
        if value in ["True", "False", "true", "false"]:
            return "true" if value in ["True", "true"] else "false"
        # int check
        elif value.isdigit():
            return int(value)
        # float check
        elif re.match(r'^-?\d+(?:\.\d+)$', value) is not None:
            return float(value)
        # else str
        else:
            return '"' + value.strip() + '"'

    def __underlying_handle_options_value_having_msg_fld_name(self, option_val: str) -> str:
        temp_list = []
        option_value_dot_separated = option_val.split(".")
        for option_val_str in option_value_dot_separated:
            # checking id field
            if "id" == option_val_str:
                temp_list.append("_id")
            # checking field names
            elif "_" in option_val_str:
                temp_list.append(self.__case_style_convert_method(option_val_str))
            # checking message names
            else:
                if self.__response_field_case_style == "camel":
                    temp = self.__case_style_convert_method(option_val_str)
                    temp_list.append(temp[0].upper() + temp[1:])
                else:
                    temp_list.append(self.__case_style_convert_method(option_val_str))

        temp_str = ".".join(temp_list)
        return temp_str

    def __handle_options_value_case_having_msg_fld_name(self, option_value: str):
        # checking if option_value is not float type and is relevant to be used here
        if type(option_value).__name__ == "str" and \
                (("-" in option_value or "." in option_value) and any(char.isalpha() for char in option_value)):

            option_value_hyphen_separated = option_value[1:-1].split("-")
            temp_list_1 = []

            for option_val in option_value_hyphen_separated:
                if '$' in option_val:
                    option_val_dollar_separated = option_val.split('$')
                    temp_list_2 = []
                    for option_val in option_val_dollar_separated:
                        temp_str = self.__underlying_handle_options_value_having_msg_fld_name(option_val)
                        temp_list_2.append(temp_str)
                    temp_str_dollar_joined = "$".join(temp_list_2)
                    temp_list_1.append(temp_str_dollar_joined)
                else:
                    temp_str = self.__underlying_handle_options_value_having_msg_fld_name(option_val)
                    temp_list_1.append(temp_str)
            return '"' + "-".join(temp_list_1) + '"'
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
        json_msg_str = ""
        for option in options_list:
            if option in str(field_or_message_obj.proto.options):
                option_value = self.get_non_repeated_valued_custom_option_value(field_or_message_obj.proto.options,
                                                                                option)
                if '"' in option_value[-1]:
                    # stripping extra '"' in value
                    option_value = self.__parse_string_to_original_types(option_value[1:-1])
                # else not required: Avoiding if value is not of string type

                if option in JsonSchemaConvertPlugin.options_having_msg_fld_names:
                    option_value = self.__handle_options_value_case_having_msg_fld_name(option_value)
                # else not required: if option is not in options_having_msg_fld_names then avoid

                # converting flux_option into json attribute name
                flux_prefix_removed_option_name = self.__convert_option_name_to_json_attribute_name(option)
                flux_prefix_removed_option_name_case_styled = \
                    self.__case_style_convert_method(flux_prefix_removed_option_name)
                json_msg_str += ' ' * init_space_count + \
                                f'"{flux_prefix_removed_option_name_case_styled}": {option_value},\n'

        return json_msg_str

    def __handle_complex_proto_option_attributes(self, options_list: List[str],
                                                 field_or_message_obj: protogen.Field | protogen.Message,
                                                 init_space_count: int) -> str:
        json_msg_str = ""
        for option in options_list:
            if option in str(field_or_message_obj.proto.options):
                option_value_list_of_dict = \
                    self.get_complex_option_values_as_list_of_dict(field_or_message_obj, option)
                # converting flux_option into json attribute name
                flux_prefix_removed_option_name = self.__convert_option_name_to_json_attribute_name(option)
                flux_prefix_removed_option_name_case_styled = \
                    self.__case_style_convert_method(flux_prefix_removed_option_name)
                json_msg_str += ' ' * init_space_count + \
                                f'"{flux_prefix_removed_option_name_case_styled}": ' + '{\n'
                for key, value in option_value_list_of_dict[0].items():
                    if isinstance(value, str):
                        # stripping extra '"' in value
                        value = self.__parse_string_to_original_types(value)
                    elif isinstance(value, bool):
                        value = "true" if value else "false"
                    # else not required: Avoiding if value is not of string or bool type as other types can be
                    # used as usual

                    if option == JsonSchemaConvertPlugin.flux_fld_button and '"' not in value:
                        value = f'"{value}"'
                    # else not required: if option is not flux_fld_button then avoid as only this option
                    # has dependency to keep every option field as str
                    json_msg_str += ' ' * (init_space_count + 2) + \
                                    f'"{key}": {value}'
                    if key != list(option_value_list_of_dict[0])[-1]:
                        json_msg_str += ',\n'
                    else:
                        json_msg_str += '\n'
                json_msg_str += ' ' * init_space_count + '},\n'

        return json_msg_str

    def __handle_fld_default_value(self, field: protogen.Field, init_space_count: int) -> str:
        if default_value := field.proto.default_value:
            default_value = self.__parse_string_to_original_types(default_value)
            return ' ' * init_space_count + f'"default": {default_value},\n'
        else:
            return ""

    def __handle_fld_sequence_number_attribute(self, field: protogen.Field, init_space_count: int) -> str:
        sequence_number: int = field.proto.number
        sequence_number_option_name = JsonSchemaConvertPlugin.flux_fld_sequence_number
        if sequence_number_option_name in str(field.proto.options):
            sequence_number = \
                self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                 sequence_number_option_name)
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
            if JsonSchemaConvertPlugin.flux_fld_title in str(field_or_msg_obj.proto.options):
                title_option_value = \
                    self.get_non_repeated_valued_custom_option_value(field_or_msg_obj.proto.options,
                                                                     JsonSchemaConvertPlugin.flux_fld_title)
                return title_option_value
            else:
                return None
        elif isinstance(field_or_msg_obj, protogen.Message):
            if JsonSchemaConvertPlugin.flux_msg_title in str(field_or_msg_obj.proto.options):
                title_option_value = \
                    self.get_non_repeated_valued_custom_option_value(field_or_msg_obj.proto.options,
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
        # Adding simple type options as attributes
        json_msg_str += \
            self.__handle_simple_proto_option_attributes(JsonSchemaConvertPlugin.flx_fld_simple_attribute_options,
                                                         field, init_space_count + 2)
        # Adding complex type options as attributes
        json_msg_str += \
            self.__handle_complex_proto_option_attributes(JsonSchemaConvertPlugin.flx_fld_complex_attribute_options,
                                                          field, init_space_count + 2)
        # Adding default value as attribute if present
        json_msg_str += self.__handle_fld_default_value(field, init_space_count + 2)

        # Adding leading comment as FluxFldCmnt attribute
        json_msg_str += self.__handle_fld_leading_comment_as_attribute(field, init_space_count + 2)

        if (title_option_value := self.__underlying_handle_title_output(field)) is not None:
            json_msg_str += ' ' * (init_space_count + 2) + f'"title": {title_option_value},\n'
        else:
            field_name_spaced = str(field.proto.name).replace("_", " ")
            json_msg_str += ' ' * (init_space_count + 2) + f'"title": "{field_name_spaced}",\n'
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
            json_msg_str += ' ' * init_space_count + f'"title": {title_option_value},\n'
        else:
            # Space separated names
            message_name_spaced = convert_camel_case_to_specific_case(message.proto.name, " ", False)
            json_msg_str += ' ' * init_space_count + f'"title": "{message_name_spaced}",\n'
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

        json_msg_str += ' ' * init_space_count + '"required": [\n'
        json_msg_str += self.__handle_required_json_schema(init_space_count, required_field_names)
        json_msg_str += ' ' * init_space_count + ']\n'
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
        json_msg_str = self.__handle_simple_proto_option_attributes(JsonSchemaConvertPlugin.flx_msg_simple_attribute_options,
                                                                    message, indent_space_count)
        json_msg_str += self.__handle_msg_leading_comment_as_attribute(message, indent_space_count)
        # Handling json root attribute
        if JsonSchemaConvertPlugin.flux_msg_json_root in str(message.proto.options):
            json_root_prefix_stripped = \
                JsonSchemaConvertPlugin.flux_msg_json_root.lstrip(JsonSchemaConvertPlugin.msg_options_standard_prefix)
            json_root_prefix_stripped_case_styled = self.__case_style_convert_method(json_root_prefix_stripped)
            json_msg_str += " " * indent_space_count + f'"{json_root_prefix_stripped_case_styled}": true,\n'
        json_msg_str += self.__underlying_json_output_handler(message, indent_space_count)
        return json_msg_str

    def __handle_widget_ui_data_option_output(self, message: protogen.Message) -> str:
        widget_ui_data_prefix_stripped = \
            JsonSchemaConvertPlugin.flx_msg_widget_ui_data.lstrip(JsonSchemaConvertPlugin.msg_options_standard_prefix)
        json_msg_str = f'    "{self.__case_style_convert_method(widget_ui_data_prefix_stripped)}": '+'{\n'
        widget_ui_data_option_value = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           JsonSchemaConvertPlugin.flx_msg_widget_ui_data)[0]
        if 'i' in widget_ui_data_option_value:
            json_msg_str += f'        "i": {widget_ui_data_option_value["i"]},\n'
        else:
            json_msg_str += f'        "i": "{self.__case_style_convert_method(message.proto.name)}",\n'
        widget_ui_data_option_fields_list = ['x', 'y', 'w', 'h', 'layout', 'alert_bubble_source', 'alert_bubble_color']
        for option_fld in widget_ui_data_option_fields_list:
            if option_fld in widget_ui_data_option_value:
                if option_fld not in widget_ui_data_option_fields_list[-2:]:
                    json_msg_str += f'        "{option_fld}": ' \
                                    f'{self.__parse_string_to_original_types(widget_ui_data_option_value[option_fld].strip())}'
                else:
                    # handling option field value having msg name
                    json_msg_str += f'        "{option_fld}": ' \
                                    f'"{self.__underlying_handle_options_value_having_msg_fld_name(widget_ui_data_option_value[option_fld])}"'
            if option_fld != list(widget_ui_data_option_value)[-1]:
                json_msg_str += ", \n"
            else:
                json_msg_str += "\n    },\n"
                break
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
        json_msg_str = '  "autocomplete": {\n'
        for auto_title, auto_list in json_content["autocomplete"].items():
            json_msg_str += f'    "{auto_title}": [\n'
            for auto_value in auto_list:
                if auto_value != auto_list[-1]:
                    json_msg_str += f'      "{auto_value}",\n'
                else:
                    json_msg_str += f'      "{auto_value}"\n'
            if auto_title != list(json_content["autocomplete"])[-1]:
                json_msg_str += f'    ],\n'
            else:
                json_msg_str += f'    ]\n'
        json_msg_str += '  }\n'
        return json_msg_str

    def __json_output_handler(self, file: protogen.File) -> str:
        # Performing Recursion to messages (including nested type) to get json layout, non-layout and enums and
        # adding to their respective data-member
        self.__load_json_layout_and_non_layout_messages_in_dicts(file.messages)
        if self.__response_field_case_style.lower() == "snake":
            self.__case_style_convert_method = convert_camel_case_to_specific_case
        elif self.__response_field_case_style.lower() == "camel":
            self.__case_style_convert_method = convert_to_camel_case
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)

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
        if (autocomplete_file_path := os.getenv("AUTOCOMPLETE_FILE_PATH")) is not None:
            json_msg_str += '  },\n'

            with open(autocomplete_file_path) as json_fl:
                json_content = json.load(json_fl)

            json_msg_str += self.__handle_auto_complete_output(json_content)
        else:
            json_msg_str += '  }\n'

        json_msg_str += '}'

        return json_msg_str


if __name__ == "__main__":
    main(JsonSchemaConvertPlugin)
