#!/usr/bin/env python
import logging
import os
from typing import List, Callable
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin

# Required for accessing custom options from schema
import insertion_imports


class PydanticClassGenPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    flux_msg_json_root: str = "FluxMsgJsonRoot"
    flux_fld_is_required: str = "FluxFldIsRequired"
    flx_fld_attribute_options: List[str] = [
        "FluxFldHelp",
        "FluxFldValMax",
        "FluxFldHide",
        "FluxFldValSortWeight",
        "FluxFldAbbreviated",
        "FluxFldSticky",
        "FluxFldSizeMax"
    ]
    flux_fld_cmnt: str = "FluxFldCmnt"
    flux_msg_cmnt: str = "FluxMsgCmnt"
    flux_fld_index: str = "FluxFldIndex"
    flux_fld_val_is_datetime: str = "FluxFldValIsDateTime"
    default_id_field_name: str = "id"

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.proto_type_to_py_type_dict = self.config_yaml["proto_type_to_py_type_dict"]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_pydantic_class_gen
        ]
        self.output_file_name_suffix = self.config_yaml["output_file_name_suffix"]
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.ordered_message_list: List[protogen.Message] = []
        self.enum_type = self.config_yaml["enum_type"]
        self.enum_type_validator()
        self.response_type: str = self.config_yaml["response_type"]

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
                    return "datetime.datetime"
                else:
                    return self.proto_type_to_py_type_dict[field.kind.name.lower()]

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

    def handle_field_output(self, field) -> str:
        field_type = self.proto_to_py_datatype(field)

        match field.cardinality.name.lower():
            case "optional":
                output_str = f"{field.proto.name}: {field_type} | None"
            case "repeated":
                output_str = f"{field.proto.name}: List[{field_type}]"
            case other:
                output_str = f"{field.proto.name}: {field_type}"

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

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str = ""
        is_msg_root = False

        if self.response_type.lower() == "snake":
            if message in self.root_message_list:
                is_msg_root = True
                output_str = f"class {message.proto.name}(IncrementalIdCacheBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(BaseModel):\n"
        elif self.response_type.lower() == "camel":
            if message in self.root_message_list:
                is_msg_root = True
                output_str = f"class {message.proto.name}(IncrementalIdCamelCacheBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(CamelCacheBaseModel):\n"
        else:
            err_str = f"{self.response_type} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)

        # Adding docstring if message lvl comment available
        if leading_comments := message.location.leading_comments:
            output_str += '    """\n'
            comments = ", ".join(leading_comments.split("\n"))
            comments_multiline = [comments[0+i:100+i] for i in range(0, len(comments), 100)]
            for comments_line in comments_multiline:
                output_str += f"        {comments_line}\n"

            output_str += '    """\n'
        if is_msg_root:
            output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[Any, '{message.proto.name}']] = " + "{}\n"
        # else not required: Avoid cache override if message is not root
        for field in message.fields:
            if is_msg_root and field.proto.name == PydanticClassGenPlugin.default_id_field_name and \
                    "int" == self.proto_to_py_datatype(field):
                output_str += "    _max_id_val: ClassVar[int | None] = None\n"
                output_str += "    _mutex: ClassVar[Lock] = Lock()\n"
                output_str += f'    id: int = Field(default_factory=(lambda: {message.proto.name}.next_id()), description="Server generated unique Id")\n'
                continue
            # else not required: if message is not JsonRoot or field is not default id and is not int type
            # then allowing override on id field
            output_str += ' '*4 + self.handle_field_output(field)
        output_str += "\n\n"

        return output_str

    def handle_imports(self) -> str:
        output_str = "from pydantic import Field, BaseModel\n"
        output_str += "import datetime\n"
        output_str += "from typing import Dict, List, ClassVar, Any\n"
        output_str += "from threading import Lock\n"
        if self.enum_list:
            if self.enum_type == "int_enum":
                output_str += "from enum import IntEnum\n"
            elif self.enum_type == "str_enum":
                output_str += "from enum import auto\n"
                output_str += "from fastapi_utils.enums import StrEnum\n"
            # else not required: if enum type is not proper then it would be already handled in init

        incremental_id_camel_base_model_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                             "incremental_id_basemodel")
        if self.response_type.lower() == "snake":
            output_str += f'from {incremental_id_camel_base_model_path} import IncrementalIdCacheBaseModel\n'
        elif self.response_type.lower() == "camel":
            output_str += f'from {incremental_id_camel_base_model_path} import IncrementalIdCamelCacheBaseModel, ' \
                          f'CamelCacheBaseModel\n'
        else:
            err_str = f"{self.response_type} is not supported response type"
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
    def main():
        project_dir_path = os.getenv("PROJECT_PATH")
        config_path = os.getenv("CONFIG_PATH")
        pydantic_class_gen_plugin = PydanticClassGenPlugin(project_dir_path, config_path)
        pydantic_class_gen_plugin.process()

    main()
