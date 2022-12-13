#!/usr/bin/env python
import logging
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginPydentic.pydantic_class_gen_plugin import PydanticClassGenPlugin, main


class BeanieClassGenPlugin(PydanticClassGenPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    # Below field name 'id' must only be used intentionally in beanie pydentic models to generate incremental id value
    # instead of random id value generated by default
    default_id_field_name: str = "id"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_field_output(self, field: protogen.Field) -> str:
        field_type = self.proto_to_py_datatype(field)

        match field.cardinality.name.lower():
            case "optional":
                if BeanieClassGenPlugin.flux_fld_index in str(field.proto.options):
                    output_str = f"{field.proto.name}: Indexed({field_type} | None)"
                else:
                    output_str = f"{field.proto.name}: {field_type} | None"
            case "repeated":
                if BeanieClassGenPlugin.flux_fld_index in str(field.proto.options):
                    output_str = f"{field.proto.name}: Indexed(List[{field_type}])"
                else:
                    if self.flux_fld_is_required in str(field.proto.options):
                        output_str = f"{field.proto.name}: List[{field_type}]"
                    else:
                        output_str = f"{field.proto.name}: List[{field_type}] | None"
            case other:
                if BeanieClassGenPlugin.flux_fld_index in str(field.proto.options):
                    output_str = f"{field.proto.name}: Indexed({field_type})"
                else:
                    output_str = f"{field.proto.name}: {field_type}"

        if (is_id_field := (field.proto.name == BeanieClassGenPlugin.default_id_field_name)) or \
                field.location.leading_comments:
            output_str += f' = Field('

            if is_id_field:
                parent_message_name = field.parent.proto.name
                parent_message_name_snake_cased = self.convert_camel_case_to_specific_case(parent_message_name)
                output_str += f"default_factory={parent_message_name_snake_cased}_id_auto_increment"
            # else not required: If not is_id_field then avoiding text to be added

            if leading_comments := field.location.leading_comments:
                if is_id_field:
                    output_str += ", "
                # else not required: If already not id related text not added then no need to append comma
                if '"' in str(leading_comments):
                    err_str = 'Leading comments can not contain "" (double quotes) to avoid error in generated output,'\
                              f' found in comment: {leading_comments}'
                    logging.exception(err_str)
                    raise Exception(err_str)
                # else not required: If double quotes not found then avoiding
                comments = ", ".join(leading_comments.split("\n"))
                output_str += f'description="{comments}"'
            # else not required: If leading_comments are not present then avoiding text to be added

            output_str += ')\n'
        else:
            output_str += "\n"

        return output_str

    def _handle_incremental_id_protected_field_override(self, message: protogen.Message, field: protogen.Field) -> str:
        output_str = "    _max_id_val: ClassVar[int | None] = None\n"
        output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[{self.proto_to_py_datatype(field)}, " \
                      f"'{message.proto.name}']] = " + "{}\n"
        output_str += "    _mutex: ClassVar[Lock] = Lock()\n"
        output_str += f"    id: int = Field(default_factory=(lambda: {message.proto.name}.next_id())," \
                      " description='Server generated unique Id')\n"
        return output_str

    def _handle_ws_connection_manager_data_members_override(self, message: protogen.Message) -> str:
        output_str = "    read_ws_path_ws_connection_manager: " \
                      "ClassVar[PathWSConnectionManager] = PathWSConnectionManager()\n"
        options_list_of_dict = \
            self.get_complex_msg_option_values_as_list_of_dict(message,
                                                               BeanieClassGenPlugin.flux_msg_json_root)
        if options_list_of_dict and \
                BeanieClassGenPlugin.flux_json_root_read_websocket_field in options_list_of_dict[0]:
            output_str += "    read_ws_path_with_id_ws_connection_manager: " \
                          "ClassVar[PathWithIdWSConnectionManager] = PathWithIdWSConnectionManager()\n"
        # else not required: Avoid if websocket field in json root option not present
        return output_str

    def handle_message_output(self, message: protogen.Message, auto_gen_id: bool = False) -> str:
        is_msg_root = False

        if self.response_field_case_style.lower() == "snake":
            if auto_gen_id:
                is_msg_root = True
                output_str = f"class {message.proto.name}(Document, IncrementalIdCacheBaseModel):\n"
            else:
                if message in self.root_message_list:
                    is_msg_root = True
                    output_str = f"class {message.proto.name}(Document):\n"
                else:
                    output_str = f"class {message.proto.name}(BaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if auto_gen_id:
                is_msg_root = True
                output_str = f"class {message.proto.name}(Document, IncrementalIdCamelCacheBaseModel):\n"
            else:
                if message in self.root_message_list:
                    is_msg_root = True
                    output_str = f"class {message.proto.name}(Document, CamelCacheBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(BaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)

        # Adding docstring if message lvl comment available
        if leading_comments := message.location.leading_comments:
            output_str += '    """\n'
            if '"' in str(leading_comments):
                err_str = 'Leading comments can not contain "" (double quotes) to avoid error in generated output,' \
                          f' found in comment: {leading_comments}'
                logging.exception(err_str)
                raise Exception(err_str)
            # else not required: If double quotes not found then avoiding
            comments = ", ".join(leading_comments.split("\n"))
            comments_multiline = [comments[0+i:100+i] for i in range(0, len(comments), 100)]
            for comments_line in comments_multiline:
                output_str += f"        {comments_line}\n"

            output_str += '    """\n'

        for field in message.fields:
            if auto_gen_id and field.proto.name == BeanieClassGenPlugin.default_id_field_name:
                output_str += self._handle_incremental_id_protected_field_override(message, field)
                continue
            # else not required: If auto_gen_id is true and field is named other than id, then skip adding it to output
            output_str += ' '*4 + self.handle_field_output(field)

        if is_msg_root:
            output_str += self._handle_ws_connection_manager_data_members_override(message)
            output_str += "\n\n"
            output_str += self.handle_message_all_optional_field(message)
            output_str += self.handle_dummy_message_gen(message, auto_gen_id)
        # If message is not root then no need to add optional and dummy version of model
        else:
            output_str += "\n\n"

        return output_str

    def handle_imports(self) -> str:
        output_str = "from beanie import Indexed, Document\n"
        output_str += "from pydantic import BaseModel, Field\n"
        output_str += "import datetime\n"
        output_str += "from threading import Lock\n"
        ws_connection_manager_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                   "ws_connection_manager")
        output_str += f"from {ws_connection_manager_path} import PathWSConnectionManager, " \
                      f"\\\n\tPathWithIdWSConnectionManager\n"
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

        if self.enum_list:
            if self.enum_type == "int_enum":
                output_str += "from enum import IntEnum\n"
            elif self.enum_type == "str_enum":
                output_str += "from enum import auto\n"
                output_str += "from fastapi_utils.enums import StrEnum\n"
            # else not required: if enum type is not proper then it would be already handled in init
        output_str += "from typing import List, ClassVar, Dict\n\n\n"
        return output_str

    def handle_pydantic_class_gen(self, file: protogen.File) -> str:
        self.load_root_and_non_root_messages_in_dicts(file.messages)

        self.sort_message_order()

        output_str = self.handle_imports()

        for enum in self.enum_list:
            output_str += self.handle_enum_output(enum, self.enum_type)

        for message in self.ordered_message_list:
            is_int_id_type: bool = False
            if BeanieClassGenPlugin.default_id_field_name in [field.proto.name for field in message.fields]:
                is_int_id_type = True
            output_str += self.handle_message_output(message, is_int_id_type)

        return output_str


if __name__ == "__main__":
    main(BeanieClassGenPlugin)
