#!/usr/bin/env python
import logging
import os
import time
from typing import Tuple

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginPydentic.cached_pydantic_model_plugin import CachedPydanticModelPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class BeanieModelPlugin(CachedPydanticModelPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.default_id_field_type: str = "PydanticObjectId"

    def _handle_field_cardinality(self, field: protogen.Field) -> str:
        field_type = self.proto_to_py_datatype(field)

        match field.cardinality.name.lower():
            case "optional":
                if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_index):
                    output_str = f"{field.proto.name}: Indexed({field_type} | None)"
                else:
                    output_str = f"{field.proto.name}: {field_type} | None"
            case "repeated":
                if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_index):
                    output_str = f"{field.proto.name}: Indexed(List[{field_type}])"
                else:
                    if self.flux_fld_is_required in str(field.proto.options):
                        output_str = f"{field.proto.name}: List[{field_type}]"
                    else:
                        output_str = f"{field.proto.name}: List[{field_type}] | None"
            case other:
                if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_index):
                    output_str = f"{field.proto.name}: Indexed({field_type})"
                else:
                    output_str = f"{field.proto.name}: {field_type}"
        return output_str

    def handle_field_output(self, field: protogen.Field) -> str:
        output_str = self._handle_field_cardinality(field)
        has_alias = False
        if (is_id_field := (field.proto.name == BeanieModelPlugin.default_id_field_name)) or \
                (has_alias := (BeanieModelPlugin.flux_fld_alias in str(field.proto.options))) or \
                field.location.leading_comments:
            output_str += f' = Field('

            if is_id_field:
                parent_message_name = field.parent.proto.name
                parent_message_name_snake_cased = convert_camel_case_to_specific_case(parent_message_name)
                output_str += f"default_factory={parent_message_name_snake_cased}_id_auto_increment"
            # else not required: If not is_id_field then avoiding text to be added

            if has_alias:
                if is_id_field:
                    output_str += ", "
                # else not required: If default_factory attribute not set in field then avoid
                alias_name = self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                              BeanieModelPlugin.flux_fld_alias)
                output_str += f'alias={alias_name}'

            if leading_comments := field.location.leading_comments:
                if is_id_field or has_alias:
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

    def _check_id_int_field(self, message: protogen.Message) -> bool:
        """ Checking if id is of auto-increment int type"""
        auto_gen_id: bool = False
        # If int id field is present in message that means auto generation configurations is required
        for field in message.fields:
            if message in self.root_message_list and BeanieModelPlugin.default_id_field_name == field.proto.name:
                if 'int' != field.proto.name:
                    auto_gen_id = True
                    break
                else:
                    err_str = "id field must be of int type, any other implementation is not supported yet"
                    logging.exception(err_str)
                    raise Exception(err_str)
        # else not required: if msg is non-root and if int id field doesn't exist in message then using default
        # PydanticObjectId id implementation
        return auto_gen_id

    def _handle_pydantic_class_declaration(self, message: protogen.Message) -> Tuple[str, bool]:
        # auto_gen_id=True: If int id field is present in message that means auto generation configurations is required
        # auto_gen_id=False: If int id field doesn't exist in message then using default
        #                    PydanticObjectId id implementation
        auto_gen_id: bool = self._check_id_int_field(message)
        is_msg_root = False
        if self.response_field_case_style.lower() == "snake":
            if auto_gen_id:
                is_msg_root = True
                output_str = f"class {message.proto.name}(Document, IncrementalIdBaseModel):\n"
            else:
                if message in self.root_message_list:
                    is_msg_root = True
                    output_str = f"class {message.proto.name}(Document):\n"
                else:
                    output_str = f"class {message.proto.name}(BaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if auto_gen_id:
                is_msg_root = True
                output_str = f"class {message.proto.name}(Document, IncrementalIdCamelBaseModel):\n"
            else:
                if message in self.root_message_list:
                    is_msg_root = True
                    output_str = f"class {message.proto.name}(Document, CamelBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(BaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root

    def handle_message_output(self, message: protogen.Message) -> str:
        # auto_gen_id=True: If int id field is present in message that means auto generation configurations is required
        # auto_gen_id=False: If int id field doesn't exist in message then using default
        #                    PydanticObjectId id implementation
        auto_gen_id: bool = self._check_id_int_field(message)
        output_str, is_msg_root = self._handle_pydantic_class_declaration(message)

        output_str += self._handle_class_docstring(message)

        output_str += self._handle_cache_n_ws_connection_manager_data_members_override(message, is_msg_root)

        for field in message.fields:
            if auto_gen_id and field.proto.name == CachedPydanticModelPlugin.default_id_field_name:
                output_str += self._handle_incremental_id_protected_field_override(message)
                continue
            # else not required: If auto_gen_id is false, then skip adding it to output
            output_str += ' '*4 + self.handle_field_output(field)
        output_str += self._handle_config_class_and_other_root_class_versions(message, auto_gen_id)

        return output_str

    def handle_imports(self) -> str:
        output_str = "from beanie import Indexed, Document, PydanticObjectId\n"
        output_str += "from pydantic import BaseModel, Field, validator\n"
        output_str += "import pendulum\n"
        output_str += "from threading import Lock\n"
        output_str += "from typing import List, ClassVar, Dict\n"
        ws_connection_manager_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                   "ws_connection_manager")
        output_str += f"from {ws_connection_manager_path} import PathWSConnectionManager, " \
                      f"\\\n\tPathWithIdWSConnectionManager\n"
        incremental_id_camel_base_model_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                             "incremental_id_basemodel")
        if self.response_field_case_style.lower() == "snake":
            output_str += f'from {incremental_id_camel_base_model_path} import IncrementalIdBaseModel\n'
        elif self.response_field_case_style.lower() == "camel":
            output_str += f'from {incremental_id_camel_base_model_path} import IncrementalIdCamelBaseModel, ' \
                          f'CamelBaseModel\n'
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
        generic_utils_import_path= self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_utils")
        output_str += f"from {generic_utils_import_path} import validate_pendulum_datetime"

        output_str += "\n\n"
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        super().assign_required_data_members(file)
        self.model_file_name = f'{self.proto_file_name}_beanie_model'


if __name__ == "__main__":
    main(BeanieModelPlugin)
