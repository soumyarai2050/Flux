#!/usr/bin/env python
import json
import logging
from typing import List, Callable, Tuple, Dict
import protogen
import os
from FluxCodeGenEngine.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin
from random import randint, choices, getrandbits, choice, random
import string
import time

# to access options
import insertion_imports

# Contains bugs - needs to be resolved #######

class JsonSampleGenPlugin(BaseProtoPlugin):
    """
    Plugin to generate json sample from proto schema
    """
    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_fld_auto_complete: str = "FluxFldAutoComplete"
    random_int_range: Tuple[int, int] = (1, 10)
    random_str_length: int = 10

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.__proto_type_to_json_type_dict = self.config_yaml["proto_type_to_json_type_dict"]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.__json_sample_gen_handler
        ]
        self.output_file_name_suffix = self.config_yaml["output_file_name_suffix"]
        self.__auto_complete_data_cache: List[Tuple[protogen.Field, str]] = []
        self.__case_style: str = self.config_yaml["case_style"]
        self.__case_style_convert_method: Callable[[str], str] | None = None
        self.auto_complete_data: Dict | None = None

    def __json_non_repeated_field_sample_gen(self, field: protogen.Field, indent_space_count: int) -> str:
        json_sample_output = ""

        field_name = field.proto.name
        if self.__case_style == 'camel':
            field_name_case_styled = self.__case_style_convert_method(field_name)
        else:
            field_name_case_styled = field_name
        match field.kind.name.lower():
            case "int32" | "int64":
                random_int = randint(*JsonSampleGenPlugin.random_int_range)
                json_sample_output += " "*indent_space_count + f'"{field_name_case_styled}": {random_int}'
            case "float":
                random_int_or_float = choice([randint(*JsonSampleGenPlugin.random_int_range),
                                              round(random(), 2)])
                json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": {random_int_or_float}'
            case "string":
                random_str = ''.join(choices(string.ascii_letters, k=JsonSampleGenPlugin.random_str_length))
                json_sample_output += " "*indent_space_count + f'"{field_name_case_styled}": "{random_str}"'
            case "bool":
                random_bool = bool(getrandbits(1))
                json_sample_output += " "*indent_space_count + f'"{field_name_case_styled}": {str(random_bool).lower()}'
            case "enum":
                random_enum_value = choice([enum_val.proto.name for enum_val in field.enum.values])
                json_sample_output += " "*indent_space_count + f'"{field_name_case_styled}": "{random_enum_value}"'
            case "message":
                json_sample_output += " "*indent_space_count + \
                                      f'"{field_name_case_styled}": {self.__handle_fld_json_gen(field.message, indent_space_count)}'
        return json_sample_output

    def __json_repeated_field_sample_gen(self, field: protogen.Field, indent_space_count: int) -> str:
        json_sample_output = ""

        field_name = field.proto.name
        if self.__case_style == 'camel':
            field_name_case_styled = self.__case_style_convert_method(field_name)
        else:
            field_name_case_styled = field_name
        match field.kind.name.lower():
            case "int32" | "int64" | "float":
                random_int = randint(*JsonSampleGenPlugin.random_int_range)
                json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": [{random_int}\n' + \
                                      " " * indent_space_count + ']'
            case "float":
                random_int_or_float = choice([randint(*JsonSampleGenPlugin.random_int_range),
                                             random()])
                json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": [{random_int_or_float}\n' + \
                                      " " * indent_space_count + ']'
            case "string":
                random_str = ''.join(choices(string.ascii_letters, k=JsonSampleGenPlugin.random_str_length))
                json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": ["{random_str}"\n' + \
                                      " " * indent_space_count + ']'
            case "bool":
                random_bool = bool(getrandbits(1))
                json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": [{str(random_bool).lower()}\n' + \
                                      " " * indent_space_count + ']'
            case "enum":
                random_enum_value = choice([enum_val.proto.name for enum_val in field.enum.values])
                json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": ["{random_enum_value}"\n' + \
                                      " " * indent_space_count + ']'
            case "message":
                json_sample_output += " " * indent_space_count + \
                                      f'"{field_name_case_styled}": [{self.__handle_fld_json_gen(field.message, indent_space_count+2)}\n' + \
                                      " " * indent_space_count + ']'
        return json_sample_output

    def __handle_json_last_values(self, current_value, complete_list) -> str:
        if current_value == complete_list[-1]:
            return "\n"
        else:
            return ",\n"

    def __handle_autocomplete_value_task(self, option_value: str, indent_space_count: int):
        # handling accessing and replacing list name to the value in option_value
        new_option_value = self.__handle_replacement_of_autocomplete_list_wth_value(option_value)
        output_str = ""
        # print("####", new_option_value)
        for field_value_pair in new_option_value[1:-1].split(","):
            field_name, value = field_value_pair.split("=")
            if self.__case_style == "camel":
                field_name_case_styled = self.convert_to_camel_case(field_name)
            else:
                field_name_case_styled = field_name
            output_str += " " * (indent_space_count + 2) + f'"{field_name_case_styled}": "{value}"'
            if field_value_pair != new_option_value[1:-1].split(",")[-1]:
                output_str += ",\n"
            else:
                output_str += "\n"

        return output_str

    def __handle_fld_json_gen(self, message: protogen.Message, indent_space_count: int) -> str:
        json_sample_output = '{\n'

        for field in message.fields:

            if JsonSampleGenPlugin.flux_fld_auto_complete in str(field.proto.options):
                option_value = \
                    self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                     JsonSampleGenPlugin.flux_fld_auto_complete)
                if self.__case_style == "camel":
                    field_name_case_styled = self.convert_to_camel_case(field.proto.name)
                else:
                    field_name_case_styled = field.proto.name
                json_sample_output += " "*(indent_space_count+2) + f'"{field_name_case_styled}":'
                if field.kind.name.lower() == "message":
                    json_sample_output += " {\n"
                else:
                    json_sample_output += " "
                json_sample_output += self.__handle_autocomplete_value_task(option_value, indent_space_count+2)
                if field.kind.name.lower() == "message":
                    if field != message.fields[-1]:
                        json_sample_output += " "*(indent_space_count+2) + "},\n"
                    else:
                        json_sample_output += " "*(indent_space_count+2) + "}\n"
                else:
                    if field != message.fields[-1]:
                        json_sample_output += ",\n"
                    else:
                        json_sample_output += "\n"
                continue

            match field.cardinality.name.lower():
                case "optional" | "required":
                    json_sample_output += self.__json_non_repeated_field_sample_gen(field, indent_space_count + 2)
                    json_sample_output += self.__handle_json_last_values(field, message.fields)
                case "repeated":
                    json_sample_output += self.__json_repeated_field_sample_gen(field, indent_space_count + 2)
                    json_sample_output += self.__handle_json_last_values(field, message.fields)

        json_sample_output += ' ' * indent_space_count + '}'

        return json_sample_output

    def __handle_root_msg_json_gen(self, message: protogen.Message, indent_space_count: int) -> str:
        message_name: str = message.proto.name
        message_name_case_styled = self.__case_style_convert_method(message_name)
        json_sample_output = " "*indent_space_count + f'"{message_name_case_styled}": '
        json_sample_output += self.__handle_fld_json_gen(message, indent_space_count)
        return json_sample_output

    def __load_auto_complete_json(self) -> Dict:
        if (autocomplete_file_path := os.getenv("AUTOCOMPLETE_FILE_PATH")) is not None:
            with open(autocomplete_file_path) as fl:
                auto_complete_data = json.load(fl)
                return auto_complete_data
        else:
            err_str = "Could not find env variable AUTOCOMPLETE_FILE_PATH"
            logging.exception(err_str)
            raise Exception(err_str)

    def __handle_replacement_of_autocomplete_list_wth_value(self, option_value: str) -> str:
        option_fields = option_value.split(",")
        new_option_value = ""
        for index, option_field in enumerate(option_fields):
            if ":" in option_field:
                field_name, list_name = option_field.strip().split(":")

                if list_name in self.auto_complete_data["autocomplete"]:
                    list_name_data: List[str] = self.auto_complete_data["autocomplete"][list_name]
                    random_value = choice(list_name_data)
                    new_option_value += f"{field_name}={random_value}"
                else:
                    err_str = f"autocomplete file has no key {list_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
            else:
                new_option_value += option_field.strip()

            if option_field != option_fields[-1]:
                new_option_value += ","
            # else not required: If option_field is last in option_fields then avoiding comma
        return new_option_value

    def __json_sample_gen_handler(self, file: protogen.File) -> str:
        self.auto_complete_data = self.__load_auto_complete_json()
        if self.__case_style.lower() == "snake":
            self.__case_style_convert_method = self.convert_camel_case_to_specific_case
        elif self.__case_style.lower() == "camel":
            self.__case_style_convert_method = self.convert_to_camel_case
        else:
            err_str = f"{self.__case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)

        json_sample_output = "{\n"

        for message in file.messages:
            if JsonSampleGenPlugin.flux_msg_json_root in str(message.proto.options):
                json_sample_output += self.__handle_root_msg_json_gen(message, 2)
            # else not required: avoid if message not of json root

                json_sample_output += self.__handle_json_last_values(message, file.messages)

        json_sample_output += "}"

        return json_sample_output


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_DIR")
        config_path = os.getenv("CONFIG_PATH")
        if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
                isinstance(debug_sleep_time := int(debug_sleep_time), int):
            time.sleep(debug_sleep_time)
        # else not required: Avoid if env var is not set or if value cant be type-cased to int
        json_schema_convert_plugin = JsonSampleGenPlugin(project_dir_path, config_path)
        json_schema_convert_plugin.process()

    main()
