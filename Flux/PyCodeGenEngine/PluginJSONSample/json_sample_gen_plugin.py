#!/usr/bin/env python
import json
import logging
from typing import List, Callable, Tuple, Dict
import os
from random import randint, choices, getrandbits, choice, random
import string
import time
from pendulum import DateTime
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


class JsonSampleGenPlugin(BaseProtoPlugin):
    """
    Plugin to generate json sample from proto schema
    """
    random_int_range: Tuple[int, int] = (1, 10)
    random_str_length: int = 10

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None and \
                len(response_field_case_style):
            self.__response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'RESPONSE_FIELD_CASE_STYLE' received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.__auto_complete_data_cache: List[Tuple[protogen.Field, str]] = []
        self.__case_style_convert_method: Callable[[str], str] | None = None
        self.auto_complete_data: Dict | None = None
        self.message_list: List[protogen.Message] = []
        self.root_msg_list: List[protogen.Message] = []
        self.__is_req_autocomplete: bool = False

    def __check_is_autocomplete_req(self, message: protogen.Message):
        for field in message.fields:
            if field.message is not None:
                self.__check_is_autocomplete_req(field.message)
            if self.is_option_enabled(field, JsonSampleGenPlugin.flux_fld_auto_complete):
                self.__is_req_autocomplete = True
                break
        # else not required: If no field of any message has autocomplete option then using default
        # value of __is_req_autocomplete data member where required

    def __load_root_json_msg(self, file: protogen.File):
        message_list: List[protogen.Message] = file.messages
        message_list.sort(key=lambda message_: message_.proto.name)     # sorting by name

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

        self.message_list.extend(message_list)
        for message in set(message_list):
            if (self.is_option_enabled(message, JsonSampleGenPlugin.flux_msg_json_root) or
                    self.is_option_enabled(message, JsonSampleGenPlugin.flux_msg_json_root_time_series)):
                self.root_msg_list.append(message)
            # else not required: avoiding non-json msg append to list

            if not self.__is_req_autocomplete:
                self.__check_is_autocomplete_req(message)
            # else not required: if __is_req_autocomplete got already updated to true by any field having
            # autocomplete option then avoiding unnecessary code execution

    def __json_non_repeated_field_sample_gen(self, field: protogen.Field, indent_space_count: int) -> str:
        json_sample_output = ""

        field_name = field.proto.name
        if self.__response_field_case_style == 'camel':
            field_name_case_styled = self.__case_style_convert_method(field_name)
        else:
            field_name_case_styled = field_name
        match field.kind.name.lower():
            case "int32" | "int64":
                if self.is_option_enabled(field, JsonSampleGenPlugin.flux_fld_val_is_datetime):
                    json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": "{DateTime.utcnow()}"'
                else:
                    random_int = randint(*JsonSampleGenPlugin.random_int_range)
                    json_sample_output += " "*indent_space_count + f'"{field_name_case_styled}": {random_int}'
            case "float" | "double":
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
        if self.__response_field_case_style == 'camel':
            field_name_case_styled = self.__case_style_convert_method(field_name)
        else:
            field_name_case_styled = field_name
        match field.kind.name.lower():
            case "int32" | "int64":
                if self.is_option_enabled(field, JsonSampleGenPlugin.flux_fld_val_is_datetime):
                    json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": ' \
                                          f'["{DateTime.utcnow()}"\n' + " " * indent_space_count + ']'
                else:
                    random_int = randint(*JsonSampleGenPlugin.random_int_range)
                    json_sample_output += " " * indent_space_count + f'"{field_name_case_styled}": [{random_int}\n' + \
                                          " " * indent_space_count + ']'
            case "float" | "double":
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

    def __handle_autocomplete_value_task(self, option_value: str, field_type: protogen.Message | None,
                                         indent_space_count: int):
        # handling accessing and replacing list name to the value in option_value
        new_option_value = self.__handle_replacement_of_autocomplete_list_wth_value(option_value)
        output_str = ""
        field_name_list = []
        for field_value_pair in new_option_value.split(","):
            field_name, value = field_value_pair.split("=")
            field_name_list.append(field_name)
            if self.__response_field_case_style == "camel":
                field_name_case_styled = convert_to_camel_case(field_name)
            else:
                field_name_case_styled = field_name
            output_str += " " * (indent_space_count + 2) + f'"{field_name_case_styled}": "{value}"'
            if field_value_pair != new_option_value.split(",")[-1]:
                output_str += ",\n"
            else:
                # handling pending fields if field_type is message type
                if field_type:
                    output_str += ",\n"
                    for f in field_type.fields:
                        if f.proto.name not in field_name_list:
                            match f.cardinality.name.lower():
                                case "optional" | "required":
                                    output_str += self.__json_non_repeated_field_sample_gen(f, indent_space_count + 2)
                                    output_str += self.__handle_json_last_values(f, field_type.fields)
                                case "repeated":
                                    output_str += self.__json_repeated_field_sample_gen(f, indent_space_count + 2)
                                    output_str += self.__handle_json_last_values(f, field_type.fields)
                else:
                    output_str += "\n"

        return output_str

    def __handle_fld_json_gen(self, message: protogen.Message, indent_space_count: int) -> str:
        json_sample_output = '{\n'

        for field in message.fields:

            indent_count = 2
            if self.is_option_enabled(field, JsonSampleGenPlugin.flux_fld_auto_complete):
                option_value = \
                    self.get_simple_option_value_from_proto(field, JsonSampleGenPlugin.flux_fld_auto_complete)
                if self.__response_field_case_style == "camel":
                    field_name_case_styled = convert_to_camel_case(field.proto.name)
                else:
                    field_name_case_styled = field.proto.name
                json_sample_output += " "*(indent_space_count+indent_count) + f'"{field_name_case_styled}":'

                if field.kind.name.lower() == "message":
                    if field.cardinality.name.lower() == "repeated":
                        json_sample_output += " [\n"
                        indent_count += 2
                        json_sample_output += " "*(indent_space_count+indent_count) + "{\n"
                    else:
                        json_sample_output += " {\n"
                else:
                    json_sample_output += " "
                json_sample_output += self.__handle_autocomplete_value_task(option_value, field.message,
                                                                            indent_space_count+2)
                if field.kind.name.lower() == "message":
                    if field != message.fields[-1]:
                        json_sample_output += " "*(indent_space_count+indent_count) + "},\n"
                    else:
                        if field.cardinality.name.lower() == "repeated":
                            json_sample_output += " "*(indent_space_count+indent_count) + "}\n"
                            indent_count -= 2
                            json_sample_output += " "*(indent_space_count+indent_count) + "]\n"
                        else:
                            json_sample_output += " "*(indent_space_count+indent_count) + "}\n"
                else:
                    if field != message.fields[-1]:
                        json_sample_output += ",\n"
                    else:
                        if field.cardinality.name.lower() == "repeated":
                            json_sample_output += "]\n"
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
        if self.__is_req_autocomplete:
            project_path = os.getenv("PROJECT_DIR")

            if project_path is not None and len(project_path):

                autocomplete_file_path = PurePath(project_path) / "misc" / "autocomplete.json"
                with open(autocomplete_file_path) as fl:
                    auto_complete_data = json.load(fl)
                    return auto_complete_data
            else:
                err_str = f"Env variable PROJECT_DIR received as {project_path}"
                logging.exception(err_str)
                raise Exception(err_str)
        # else not required: If no field of any message has autocomplete option then avoiding file's content load

    def _get_random_value_from_auto_complete_list(self, list_name: str):
        if list_name in self.auto_complete_data["autocomplete"]:
            list_name_data: List[str] = self.auto_complete_data["autocomplete"][list_name]
            random_value = choice(list_name_data)
            return random_value
        else:
            err_str = f"autocomplete file has no key {list_name}"
            logging.exception(err_str)
            raise Exception(err_str)

    def __handle_replacement_of_autocomplete_list_wth_value(self, option_value: str) -> str:
        option_fields = option_value.split(",")
        new_option_value = ""
        for index, option_field in enumerate(option_fields):
            if ":" in option_field:
                field_name, list_name = option_field.strip().split(":")
                list_name = list_name.replace('"', '').strip()

                random_value = self._get_random_value_from_auto_complete_list(list_name)
                new_option_value += f"{field_name}={random_value}"
            if "~" in option_field:
                # print(f"option_field: {option_field.strip('~')}")
                field_name, msg_fld_ref = option_field.strip().split("~")
                for msg in self.message_list:
                    if msg.proto.name == msg_fld_ref.split(".")[0]:
                        break
                else:
                    raise Exception(f"message with name {msg_fld_ref.split('.')[0]} not found in list of all messages")

                found_enum: protogen.Enum | None = None
                for fld_name in msg_fld_ref.split(".")[1:]:
                    for fld in msg.fields:
                        if fld.proto.name == fld_name:
                            msg = fld.message
                            break
                    else:
                        raise Exception(
                            f"field with name {fld_name} not found in list of field of message {msg.proto.name}")

                    if fld.enum is not None:
                        found_enum = fld.enum
                        break

                if found_enum is not None:
                    random_val = choice(found_enum.values)
                else:
                    raise Exception("can't find enum in any msg's fld mentioned in ref value in sec_id key in "
                                    "autocorrect option value")
                new_option_value += f"{field_name}={random_val.proto.name}"
                pass
            else:
                new_option_value += option_field.strip()

            if option_field != option_fields[-1]:
                new_option_value += ","
            # else not required: If option_field is last in option_fields then avoiding comma
        return new_option_value

    def output_file_generate_handler(self, file: protogen.File):
        self.__load_root_json_msg(file)
        self.auto_complete_data = self.__load_auto_complete_json()
        if self.__response_field_case_style.lower() == "snake":
            self.__case_style_convert_method = convert_camel_case_to_specific_case
        elif self.__response_field_case_style.lower() == "camel":
            self.__case_style_convert_method = convert_to_camel_case
        else:
            err_str = f"{self.__response_field_case_style} is not supported case style"
            logging.exception(err_str)
            raise Exception(err_str)

        json_sample_output = "{\n"

        for message in self.root_msg_list:
            json_sample_output += self.__handle_root_msg_json_gen(message, 2)
            json_sample_output += self.__handle_json_last_values(message, self.root_msg_list)

        json_sample_output += "}"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{proto_file_name}_json_sample.json"
        return {
            output_file_name: json_sample_output
        }


if __name__ == "__main__":
    main(JsonSampleGenPlugin)
