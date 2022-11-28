#!/usr/bin/env python
import json
import logging
import os
from typing import List, Callable, Dict
import protogen
from FluxCodeGenEngine.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin
import time

# Required for accessing custom options from schema
import insertion_imports


class JsonSchemaConvertPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    msg_options_standard_prefix = "FluxMsg"
    fld_options_standard_prefix = "FluxFld"
    flux_msg_json_layout: str = "FluxMsgLayout"
    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_fld_is_required: str = "FluxFldIsRequired"
    flx_fld_attribute_options: List[str] = [
        "FluxFldHelp",
        "FluxFldValMax",
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
        "FluxFldAlertBubbleColor"
    ]
    options_having_msg_fld_names: List[str] = [
        "FluxFldAbbreviated",
        "FluxFldAlertBubbleSource",
        "FluxFldAlertBubbleColor"
    ]
    flx_msg_attribute_options: List[str] = [
        "FluxMsgLayout",
        "FluxMsgServerPopulate"
    ]
    flux_fld_cmnt: str = "FluxFldCmnt"
    flux_msg_cmnt: str = "FluxMsgCmnt"
    flux_fld_sequence_number: str = "FluxFldSequenceNumber"
    flux_fld_val_is_datetime: str = "FluxFldValIsDateTime"
    # Below field name 'id' must only be used intentionally in beanie pydentic models to make custom type
    # of primary key in that model
    default_id_field_name: str = "id"

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.__proto_type_to_json_type_dict = self.config_yaml["proto_type_to_json_type_dict"]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.__json_output_handler
        ]
        self.output_file_name_suffix = self.config_yaml["output_file_name_suffix"]
        self.__json_layout_message_list: List[protogen.Message] = []
        self.__json_non_layout_message_list: List[protogen.Message] = []
        self.__enum_list: List[protogen.Enum] = []
        self.__case_style: str = self.config_yaml["case_style"]
        self.__case_style_convert_method: Callable[[str], str] | None = None

    def __proto_data_type_to_json(self, field: protogen.Field) -> str:
        if field.cardinality.name.lower() == "repeated":
            return "array"
        else:
            if field.kind.name.lower() == "message":
                return "object"
            else:
                return self.__proto_type_to_json_type_dict[field.kind.name.lower()]

    def __load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.__enum_list:
                    self.__enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if JsonSchemaConvertPlugin.flux_msg_json_layout in str(field.message.proto.options):
                    if field.message not in self.__json_layout_message_list:
                        self.__json_layout_message_list.append(field.message)
                    # else not required: avoiding repetition
                else:
                    if field.message not in self.__json_non_layout_message_list:
                        self.__json_non_layout_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.__load_dependency_messages_and_enums_in_dicts(field.message)
            # else not required: avoiding other kinds than message or enum

    def __load_json_layout_and_non_layout_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            if JsonSchemaConvertPlugin.flux_msg_json_layout in str(message.proto.options):
                if message not in self.__json_layout_message_list:
                    self.__json_layout_message_list.append(message)
                # else not required: avoiding repetition
            else:
                if message not in self.__json_non_layout_message_list:
                    self.__json_non_layout_message_list.append(message)
                # else not required: avoiding repetition

            self.__load_dependency_messages_and_enums_in_dicts(message)

    def __handle_message_or_enum_type_json_schema(self, data_type: str, init_space_count: int, data_type_name: str,
                                                  json_type: str, msg_or_enum_obj: protogen.Message | protogen.Enum) -> str:
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
        json_msg_str += ' '*init_space_count + f'"type": "{json_type}",\n'
        json_msg_str += ' '*init_space_count + f'"items": ' + '{\n'
        if data_type == 'm':
            if msg_or_enum_obj in self.__json_layout_message_list:
                json_msg_str += \
                    ' ' * (init_space_count + 2) + f'"$ref": "#/{data_type_name}"' + \
                    '\n' + ' '*init_space_count + '}\n'
            else:
                json_msg_str += \
                    ' ' * (init_space_count + 2) + f'"$ref": "#/definitions/{data_type_name}"' + \
                    '\n' + ' '*init_space_count + '}\n'
        elif data_type == 'e':
            json_msg_str += \
                ' ' * (init_space_count + 2) + f'"$ref": "#/definitions/{data_type_name}"' + \
                '\n' + ' '*init_space_count + '}\n'
        else:
            err_msg = f"Parameter data_type must be only 'm' or 'e', provided {data_type}"
            logging.exception(err_msg)
            raise Exception(err_msg)
        return json_msg_str

    def __handle_required_json_schema(self, init_space_count: int, required_field_names: List[str]) -> str:
        json_msg_str = ""
        for field_name in required_field_names:
            if field_name != required_field_names[-1]:
                json_msg_str += ' '*(init_space_count+2) + f'"{field_name}",\n'
            else:
                json_msg_str += ' '*(init_space_count+2) + f'"{field_name}"\n'
        return json_msg_str

    def __add_required_field_names_to_list(self, required_field_names: List[str], field: protogen.Field) -> List[str]:
        if field.cardinality.name.lower() == "required":
            field_name_case_styled = self.__case_style_convert_method(field.proto.name)
            required_field_names.append(field_name_case_styled)
        elif field.cardinality.name.lower() == "repeated":
            if self.flux_fld_is_required in str(field.proto.options):
                field_name_case_styled = self.__case_style_convert_method(field.proto.name)
                required_field_names.append(field_name_case_styled)
        # else not required: avoiding optional cardinality
        return required_field_names

    def __handle_field_json_type_schema(self, field: protogen.Field, init_space_count: int, json_type: str):
        json_msg_str = ""
        if field.kind.name.lower() == "message":
            field_msg_name_case_styled = self.__case_style_convert_method(field.message.proto.name)
            if self.__case_style == "camel":
                field_msg_name_case_styled = field_msg_name_case_styled[0].upper() + field_msg_name_case_styled[1:]
            json_msg_str += \
                self.__handle_message_or_enum_type_json_schema('m', init_space_count, field_msg_name_case_styled,
                                                               json_type, field.message)
        elif field.kind.name.lower() == "enum":
            field_enum_name_case_styled = self.__case_style_convert_method(field.enum.proto.name)
            if self.__case_style == "camel":
                field_enum_name_case_styled = field_enum_name_case_styled.capitalize()
            json_msg_str += \
                self.__handle_message_or_enum_type_json_schema('e', init_space_count, field_enum_name_case_styled,
                                                               json_type, field.enum)
        else:
            if JsonSchemaConvertPlugin.flux_fld_val_is_datetime in str(field.proto.options):
                json_msg_str += ' '*init_space_count + f'"type": "date-time"\n'
            else:
                json_msg_str += ' '*init_space_count + f'"type": "{json_type}"\n'
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

    def __parse_other_than_string_value(self, value: str) -> str | int | bool:
        """
        Returns int if value string contains only numbers, bool if value contains string parsed bool
        and returns same value if both cases are not matched
        """
        if value in ["True", "False", "true", "false"]:
            return "true" if value in ["True", "true"] else "false"
        elif value.isdigit():
            return int(value)
        else:
            return '"' + value + '"'

    def __handle_options_value_case_having_msg_fld_name(self, option_value: str):
        if "-" in option_value or "." in option_value:
            option_value_hyphen_separated = option_value[1:-1].split("-")
            temp_list_1 = []

            for option_val in option_value_hyphen_separated:
                temp_list_2 = []
                option_value_dot_separated = option_val.split(".")
                for option_val_str in option_value_dot_separated:
                    if "id" == option_val_str:
                        temp_list_2.append("_id")
                    elif "_" in option_val_str:
                        temp_list_2.append(self.__case_style_convert_method(option_val_str))
                    else:
                        if self.__case_style == "camel":
                            temp = self.__case_style_convert_method(option_val_str)
                            temp_list_2.append(temp[0].upper() + temp[1:])
                        else:
                            temp_list_2.append(self.__case_style_convert_method(option_val_str))

                temp_str = ".".join(temp_list_2)
                temp_list_1.append(temp_str)
            return '"' + "-".join(temp_list_1) + '"'
        else:
            return option_value

    def __handle_proto_option_attributes(self, options_list: List[str],
                                         field_or_message_obj: protogen.Field | protogen.Message,
                                         init_space_count: int) -> str:
        json_msg_str = ""
        # Checking any option from flx_fld_attribute_options
        for option in options_list:
            if option in str(field_or_message_obj.proto.options):
                option_value = self.get_non_repeated_valued_custom_option_value(field_or_message_obj.proto.options,
                                                                                option)

                if '"' in option_value[-1]:
                    # stripping extra '"' in value
                    option_value = self.__parse_other_than_string_value(option_value[1:-1])
                # else not required: Avoiding if value is not of string type

                if option in JsonSchemaConvertPlugin.options_having_msg_fld_names:
                    option_value = self.__handle_options_value_case_having_msg_fld_name(option_value)
                # else not required: if option is not in options_having_msg_fld_names then avoid

                # converting flux_option into json attribute name
                if (fld_standard_prefix := JsonSchemaConvertPlugin.fld_options_standard_prefix) in option:
                    flux_prefix_removed_option_name = option.lstrip(fld_standard_prefix)
                elif (msg_standard_prefix := JsonSchemaConvertPlugin.msg_options_standard_prefix) in option:
                    flux_prefix_removed_option_name = option.lstrip(msg_standard_prefix)
                else:
                    err_str = f"No Standard option prefix found in option {option} from option_list"
                    logging.exception(err_str)
                    raise Exception(err_str)
                flux_prefix_removed_option_name_case_styled = \
                    self.__case_style_convert_method(flux_prefix_removed_option_name)
                json_msg_str += ' '*init_space_count + f'"{flux_prefix_removed_option_name_case_styled}": {option_value},\n'

        return json_msg_str

    def __handle_fld_default_value(self, field: protogen.Field, init_space_count: int) -> str:
        if default_value := field.proto.default_value:
            default_value = self.__parse_other_than_string_value(default_value)
            return ' '*init_space_count + f'"default": {default_value},\n'
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
        output_str = ' '*init_space_count + f'"{sequence_number_option_name_prefix_removed_case_styled}": ' \
                                            f'{sequence_number},\n'
        return output_str

    def __underlying_fld_output_handler(self, field: protogen.Field, init_space_count: int) -> str:
        field_name: str = field.proto.name
        if self.__case_style.lower() == "camel":
            # Converting field name (snake cased) to camel_case
            field_name_case_styled = self.__case_style_convert_method(field_name)
        elif self.__case_style.lower() == "snake":
            field_name_case_styled = field_name
        else:
            err_str = f"{self.__case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)

        json_msg_str = ' '*init_space_count + f'"{field_name_case_styled}": ' + '{\n'
        json_type = self.__proto_data_type_to_json(field)
        json_msg_str += self.__handle_proto_option_attributes(JsonSchemaConvertPlugin.flx_fld_attribute_options,
                                                              field, init_space_count + 2)
        # Adding default value as attribute if present
        json_msg_str += self.__handle_fld_default_value(field, init_space_count + 2)

        # Adding leading comment as FluxFldCmnt attribute
        json_msg_str += self.__handle_fld_leading_comment_as_attribute(field, init_space_count + 2)

        field_name_spaced = str(field.proto.name).replace("_", " ")
        json_msg_str += ' ' * (init_space_count + 2) + f'"title": "{field_name_spaced}",\n'
        json_msg_str += self.__handle_fld_sequence_number_attribute(field, init_space_count + 2)
        json_msg_str += self.__handle_field_json_type_schema(field, init_space_count + 2, json_type)
        return json_msg_str

    def __underlying_json_output_handler(self, message: protogen.Message, init_space_count: int) -> str:
        json_msg_str = ""
        # Space separated names
        message_name_spaced = self.convert_camel_case_to_specific_case(message.proto.name, " ", False)
        json_msg_str += ' '*init_space_count + f'"title": "{message_name_spaced}",\n'
        json_msg_str += ' '*init_space_count + '"type": "object",\n'
        json_msg_str += ' '*init_space_count + '"properties": {\n'

        required_field_names: List[str] = []
        for field in message.fields:
            if field.proto.name == JsonSchemaConvertPlugin.default_id_field_name:
                continue
            # else not required: if field name is not ´id´ then add it to json schema
            required_field_names = self.__add_required_field_names_to_list(required_field_names, field)
            json_msg_str += self.__underlying_fld_output_handler(field, init_space_count+2)
            if field == message.fields[-1]:
                json_msg_str += ' '*(init_space_count+2) + '}\n'
            else:
                json_msg_str += ' '*(init_space_count+2) + '},\n'
        json_msg_str += ' '*init_space_count + '},\n'

        json_msg_str += ' '*init_space_count + '"required": [\n'
        json_msg_str += self.__handle_required_json_schema(init_space_count, required_field_names)
        json_msg_str += ' '*init_space_count + ']\n'
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
            json_msg_str += ' '*init_space_count + f'"{flux_msg_removed_option_name_case_styled}": "{comment_str}",\n'
        return json_msg_str

    def __handle_underlying_message_part(self, message: protogen.Message, indent_space_count: int):
        json_msg_str = self.__handle_proto_option_attributes(JsonSchemaConvertPlugin.flx_msg_attribute_options,
                                                             message, indent_space_count)
        json_msg_str += self.__handle_msg_leading_comment_as_attribute(message, indent_space_count)
        # Handling json root attribute
        if JsonSchemaConvertPlugin.flux_msg_json_root in str(message.proto.options):
            json_root_prefix_stripped = \
                JsonSchemaConvertPlugin.flux_msg_json_root.lstrip(JsonSchemaConvertPlugin.msg_options_standard_prefix)
            json_root_prefix_stripped_case_styled = self.__case_style_convert_method(json_root_prefix_stripped)
            json_msg_str += " "*indent_space_count + f'"{json_root_prefix_stripped_case_styled}": true,\n'
        json_msg_str += self.__underlying_json_output_handler(message, indent_space_count)
        return json_msg_str

    def __handle_json_layout_message_schema(self, message: protogen.Message) -> str:
        json_msg_str = ''
        if self.__case_style.lower() == "snake":
            message_name = self.__case_style_convert_method(message.proto.name)
        elif self.__case_style.lower() == "camel":
            message_name = message.proto.name
        else:
            err_str = f"{self.__case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)
        json_msg_str += f'  "{message_name}": ' + '{\n'
        json_msg_str += '    "$schema": "http://json-schema.org/draft-04/schema#",\n'
        json_msg_str += self.__handle_underlying_message_part(message, 4)
        if message != self.__json_layout_message_list[-1] or self.__enum_list:
            json_msg_str += '  },\n'
        else:
            json_msg_str += '  }\n'
        return json_msg_str

    def __handle_json_complex_type_schema(self, message: protogen.Message) -> str:
        json_msg_str = ''
        if self.__case_style.lower() == "snake":
            message_name = self.__case_style_convert_method(message.proto.name)
        elif self.__case_style.lower() == "camel":
            message_name = message.proto.name
        else:
            err_str = f"{self.__case_style} is not supported case style"
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
        if self.__case_style.lower() == "snake":
            enum_name = self.__case_style_convert_method(enum.proto.name)
        elif self.__case_style.lower() == "camel":
            enum_name = enum.proto.name
        else:
            err_str = f"{self.__case_style} is not supported case style"
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
        if self.__case_style.lower() == "snake":
            self.__case_style_convert_method = self.convert_camel_case_to_specific_case
        elif self.__case_style.lower() == "camel":
            self.__case_style_convert_method = self.convert_to_camel_case
        else:
            err_str = f"{self.__case_style} is not supported case style"
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
    def main():
        project_dir_path = os.getenv("PROJECT_DIR")
        config_path = os.getenv("CONFIG_PATH")
        if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
                isinstance(debug_sleep_time := int(debug_sleep_time), int):
            time.sleep(debug_sleep_time)
        # else not required: Avoid if env var is not set or if value cant be type-cased to int
        json_schema_convert_plugin = JsonSchemaConvertPlugin(project_dir_path, config_path)
        json_schema_convert_plugin.process()

    main()
