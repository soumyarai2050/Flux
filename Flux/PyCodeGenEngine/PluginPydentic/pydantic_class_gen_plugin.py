#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, Tuple
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main

# Required for accessing custom options from schema
from Flux.PyCodeGenEngine.PluginPydentic import insertion_imports


class PydanticClassGenPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_json_root_read_websocket_field: str = "ReadWebSocketDesc"
    flux_json_root_update_websocket_field: str = "UpdateWebSocketDesc"
    flux_fld_is_required: str = "FluxFldIsRequired"
    flux_fld_cmnt: str = "FluxFldCmnt"
    flux_msg_cmnt: str = "FluxMsgCmnt"
    flux_fld_index: str = "FluxFldIndex"
    flux_fld_val_is_datetime: str = "FluxFldValIsDateTime"
    default_id_field_name: str = "id"
    flux_fld_alias: str = "FluxFldAlias"
    proto_type_to_py_type_dict: Dict[str, str] = {
        "int32": "int",
        "int64": "int",
        "string": "str",
        "bool": "bool",
        "float": "float"
    }

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_pydantic_class_gen
        ]
        response_field_case_style = None
        output_file_name_suffix = None
        if (enum_type := os.getenv("ENUM_TYPE")) is not None and \
                (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None and \
                (output_file_name_suffix := os.getenv("OUTPUT_FILE_NAME_SUFFIX")) is not None:
            self.enum_type = enum_type
            self.output_file_name_suffix = output_file_name_suffix
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'ENUM_TYPE', 'OUTPUT_FILE_NAME_SUFFIX' and 'RESPONSE_FIELD_CASE_STYLE' " \
                      f"received as {enum_type}, {output_file_name_suffix} and {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.ordered_message_list: List[protogen.Message] = []
        self.enum_type_validator()

    def enum_type_validator(self):
        match self.enum_type:
            case "int_enum":
                pass
            case "str_enum":
                pass
            case other:
                err_str = f"{self.enum_type} is not proper enum_type, either it should be 'int_enum' or 'str_enum'"
                logging.exception(err_str)
                raise Exception(err_str)

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                if PydanticClassGenPlugin.flux_fld_val_is_datetime in str(field.proto.options):
                    return "pendulum.DateTime"
                else:
                    return PydanticClassGenPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if PydanticClassGenPlugin.flux_msg_json_root in str(field.message.proto.options):
                    if field.message not in self.root_message_list:
                        self.root_message_list.append(field.message)
                    # else not required: avoiding repetition
                else:
                    if field.message not in self.non_root_message_list:
                        self.non_root_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.load_dependency_messages_and_enums_in_dicts(field.message)
            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            option_str = str(message.proto.options)
            if PydanticClassGenPlugin.flux_msg_json_root in str(message.proto.options):
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

    def sort_message_order(self):
        combined_message_list = self.root_message_list + self.non_root_message_list

        # First adding simple field type messages
        for message in combined_message_list:
            for field in message.fields:
                if field.kind.name.lower() == "message":
                    break
            else:
                self.ordered_message_list.append(message)

        while len(combined_message_list) != len(self.ordered_message_list):
            for message in combined_message_list:
                if message not in self.ordered_message_list:
                    for field in message.fields:
                        if field.message is not None and field.message not in self.ordered_message_list:
                            break
                    else:
                        self.ordered_message_list.append(message)

    def _handle_field_cardinality(self, field: protogen.Field) -> str:
        field_type = self.proto_to_py_datatype(field)
        match field.cardinality.name.lower():
            case "optional":
                output_str = f"{field.proto.name}: {field_type} | None"
            case "repeated":
                output_str = f"{field.proto.name}: List[{field_type}]"
            case other:
                output_str = f"{field.proto.name}: {field_type}"
        return output_str

    def handle_field_output(self, field) -> str:

        output_str = self._handle_field_cardinality(field)
        if leading_comments := field.location.leading_comments:
            comments = ", ".join(leading_comments.split("\n"))
            output_str += f' = Field(description="{comments}")\n'
        else:
            output_str += "\n"

        return output_str

    def handle_enum_output(self, enum: protogen.Enum, enum_type: str) -> str:
        output_str = ""

        match enum_type:
            case "int_enum":
                output_str += f"class {enum.proto.name}(IntEnum):\n"
                for index, value in enumerate(enum.values):
                    output_str += ' '*4 + f"{value.proto.name} = {index+1}\n"
                output_str += "\n\n"
            case "str_enum":
                output_str += f"class {enum.proto.name}(StrEnum):\n"
                for value in enum.values:
                    output_str += ' ' * 4 + f"{value.proto.name} = auto()\n"
                output_str += "\n\n"
            case other:
                err_str = f"{enum_type} is not proper enum_type, either it should be 'int_enum' or 'str_enum'"
                logging.exception(err_str)
                raise Exception(err_str)

        return output_str

    def _underlying_handle_none_default_fields(self, message: protogen.Message, auto_gen_id: bool = False) -> str:
        output_str = ""
        for field in message.fields:
            if field.proto.name == PydanticClassGenPlugin.default_id_field_name:
                if auto_gen_id:
                    output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = " \
                                  f"Field(alias='_id')\n"
                else:
                    output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = None\n"
                continue
            if field.cardinality.name.lower() == "repeated":
                output_str += f"    {field.proto.name}: List[{self.proto_to_py_datatype(field)}] | None = None\n"
            else:
                output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = None\n"
        return output_str

    def handle_message_all_optional_field(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}Optional({message_name}):\n"
        output_str += self._underlying_handle_none_default_fields(message)
        output_str += "\n\n"
        return output_str

    def handle_dummy_message_gen(self, message: protogen.Message, auto_gen_id: bool = False) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}BaseModel(BaseModel):\n"
        output_str += self._underlying_handle_none_default_fields(message, auto_gen_id)
        if auto_gen_id:
            output_str += "\n"
            output_str += "    class Config:\n"
            output_str += "        allow_population_by_field_name = True\n"
        output_str += "\n\n"
        return output_str

    def _handle_incremental_id_protected_field_override(self, message: protogen.Message) -> str:
        output_str = "    _max_id_val: ClassVar[int | None] = None\n"
        output_str += "    _mutex: ClassVar[Lock] = Lock()\n"
        output_str += f'    id: int = Field(default_factory=(lambda: {message.proto.name}.next_id()), ' \
                      f'description="Server generated unique Id", alias="_id")\n'
        return output_str

    def _handle_ws_connection_manager_data_members_override(self, message: protogen.Message) -> str:
        output_str = "    read_ws_path_ws_connection_manager: " \
                      "ClassVar[PathWSConnectionManager] = PathWSConnectionManager()\n"
        options_list_of_dict = \
            self.get_complex_msg_option_values_as_list_of_dict(message,
                                                               PydanticClassGenPlugin.flux_msg_json_root)
        if options_list_of_dict and \
                PydanticClassGenPlugin.flux_json_root_read_websocket_field in options_list_of_dict[0]:
            output_str += "    read_ws_path_with_id_ws_connection_manager: " \
                          "ClassVar[PathWithIdWSConnectionManager] = PathWithIdWSConnectionManager()\n"
        # else not required: Avoid if websocket field in json root option not present
        return output_str

    def _handle_pydantic_class_declaration(self, message: protogen.Message) -> Tuple[str, bool]:
        is_msg_root = False
        if self.response_field_case_style.lower() == "snake":
            if message in self.root_message_list:
                is_msg_root = True
                output_str = f"class {message.proto.name}(IncrementalIdCacheBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(BaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if message in self.root_message_list:
                is_msg_root = True
                output_str = f"class {message.proto.name}(IncrementalIdCamelCacheBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(CamelCacheBaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root

    def _handle_class_docstring(self, message: protogen.Message) -> str:
        output_str = ""
        if leading_comments := message.location.leading_comments:
            output_str += '    """\n'
            if '"' in str(leading_comments):
                err_str = 'Leading comments can not contain "" (double quotes) to avoid error in generated output,' \
                          f' found in comment: {leading_comments}'
                logging.exception(err_str)
                raise Exception(err_str)
            # else not required: If double quotes not found then avoiding
            comments = ", ".join(leading_comments.split("\n"))
            comments_multiline = [comments[0 + i:100 + i] for i in range(0, len(comments), 100)]
            for comments_line in comments_multiline:
                output_str += f"        {comments_line}\n"
            output_str += '    """\n'
        # else not required: empty string will be sent
        return output_str

    def _handle_cache_n_ws_connection_manager_data_members_override(self, message: protogen.Message, is_msg_root: bool):
        output_str = ""
        if is_msg_root:
            for field in message.fields:
                if PydanticClassGenPlugin.default_id_field_name in field.proto.name:
                    output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[{self.proto_to_py_datatype(field)}, " \
                                  f"'{message.proto.name}']] = " + "{}\n"
                    break
                # else not required: If no field is id override then handling default id type in else of for loop
            else:
                output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[int, " \
                              f"'{message.proto.name}']] = " + "{}\n"
            output_str += self._handle_ws_connection_manager_data_members_override(message)
        # else not required: Avoid cache override if message is not root
        return output_str

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message, is_msg_root: bool) -> str:
        output_str = ""
        # Making class able to be populated with field name
        if is_msg_root:
            output_str += "\n"
            output_str += "    class Config:\n"
            output_str += "        allow_population_by_field_name = True\n"
        output_str += "\n\n"

        # Adding other versions for root pydantic class
        if is_msg_root:
            output_str += self.handle_message_all_optional_field(message)
            output_str += self.handle_dummy_message_gen(message, is_msg_root)
        # If message is not root then no need to add message with optional fields

        return output_str

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str, is_msg_root = self._handle_pydantic_class_declaration(message)

        # Adding docstring if message lvl comment available
        output_str += self._handle_class_docstring(message)

        output_str += self._handle_cache_n_ws_connection_manager_data_members_override(message, is_msg_root)

        # Handling Id field
        # If message contain id field of int type then overriding that id field with incremental id field
        for field in message.fields:
            if is_msg_root and field.proto.name == PydanticClassGenPlugin.default_id_field_name and \
                    "int" == self.proto_to_py_datatype(field):
                output_str += self._handle_incremental_id_protected_field_override(message)
                break
            # else not required: if message doesn't contain id field then else of this for loop will
            # handle id field creation for this pydantic class. If message contains id field but is not
            # of int type then override will be avoided
        else:
            if is_msg_root and PydanticClassGenPlugin.default_id_field_name not in \
                    [field.proto.name for field in message.fields]:
                output_str += self._handle_incremental_id_protected_field_override(message)
            # else not required: If id already exists and is not of int type then avoiding repetition of code

        # handling remaining fields
        for field in message.fields:
            if is_msg_root and field.proto.name == PydanticClassGenPlugin.default_id_field_name:
                continue
            # else not required: if message is not JsonRoot or field is not default id and is not int type
            # then allowing override on id field
            output_str += ' '*4 + self.handle_field_output(field)

        output_str += self._handle_config_class_and_other_root_class_versions(message, is_msg_root)

        return output_str

    def handle_imports(self) -> str:
        output_str = "from pydantic import Field, BaseModel\n"
        output_str += "import pendulum\n"
        output_str += "from typing import Dict, List, ClassVar, Any\n"
        output_str += "from threading import Lock\n"
        ws_connection_manager_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                   "ws_connection_manager")
        output_str += f"from {ws_connection_manager_path} import PathWSConnectionManager, " \
                      f"\\\n\tPathWithIdWSConnectionManager\n"
        if self.enum_list:
            if self.enum_type == "int_enum":
                output_str += "from enum import IntEnum\n"
            elif self.enum_type == "str_enum":
                output_str += "from enum import auto\n"
                output_str += "from fastapi_utils.enums import StrEnum\n"
            # else not required: if enum type is not proper then it would be already handled in init

        incremental_id_camel_base_model_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                             "incremental_id_basemodel")
        if self.response_field_case_style.lower() == "snake":
            output_str += f'from {incremental_id_camel_base_model_path} import IncrementalIdCacheBaseModel\n'
        elif self.response_field_case_style.lower() == "camel":
            output_str += f'from {incremental_id_camel_base_model_path} import IncrementalIdCamelCacheBaseModel, ' \
                          f'CamelCacheBaseModel\n'
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        output_str += "from typing import List\n\n\n"
        return output_str

    def handle_pydantic_class_gen(self, file: protogen.File) -> str:
        self.load_root_and_non_root_messages_in_dicts(file.messages)

        self.sort_message_order()

        output_str = self.handle_imports()

        for enum in self.enum_list:
            output_str += self.handle_enum_output(enum, self.enum_type)

        for message in self.ordered_message_list:
            output_str += self.handle_message_output(message)

        return output_str


if __name__ == "__main__":
    main(PydanticClassGenPlugin)
