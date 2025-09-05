#!/usr/bin/env python
import logging
import os
from typing import Tuple
import time
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginORMModel.base_ORM_model_plugin import BaseORMModelPlugin, main, IdType


class CachedORMModelPlugin(BaseORMModelPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.default_id_field_type: str = "int"

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
        is_optional = False
        if field.cardinality.name.lower() == "optional":
            is_optional = True
        elif field.cardinality.name.lower() == "repeated":
            if not self.is_option_enabled(field, CachedORMModelPlugin.flux_fld_is_required):
                is_optional = True
        # else not required: is_required = False
        if leading_comments := field.location.leading_comments:
            comments = ", ".join(leading_comments.split("\n"))
            output_str += f' = Field(description="{comments}"'
            if is_optional:
                output_str += "default=None"
            output_str += ")\n"
        else:
            if is_optional:
                output_str += " = None"
            output_str += "\n"

        return output_str

    def _check_id_int_field(self, message: protogen.Message) -> IdType:
        """ Checking if id is of auto-increment int type"""
        for field in message.fields:
            if field.proto.name == CachedORMModelPlugin.default_id_field_name:
                if "int" == self.proto_to_py_datatype(field):
                    return IdType.INT_ID
                elif "str" == self.proto_to_py_datatype(field):
                    return IdType.STR_ID
                break
            # else not required: if message doesn't contain id field then else of this for loop will
            # handle int id field creation for this pydantic class as default id type.
            # If message contains id field but is not of int type then override will be avoided
        else:
            if message in self.root_message_list:
                # Default case for cached impl
                return IdType.INT_ID
            else:
                return IdType.NO_ID

    def _handle_ORM_class_declaration(self, message: protogen.Message) -> Tuple[str, bool, IdType]:
        # auto_gen_id_type = DEFAULT | INT_ID: If int id field is present in message or
        #                   If id field doesn't exist in message
        #                   then using default int auto-increment id implementation
        # auto_gen_id_type = STR_ID: If id field exists but of str type in message
        # auto_gen_id_type = NO_ID: If no id field exists then no handling for id
        auto_gen_id_type: IdType = self._check_id_int_field(message)
        if message in self.root_message_list:
            is_msg_root = True
        else:
            is_msg_root = False
        if self.response_field_case_style.lower() == "snake":
            if auto_gen_id_type == IdType.INT_ID or auto_gen_id_type == IdType.DEFAULT:
                output_str = f"class {message.proto.name}(IncrementalIdCacheBaseModel):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                output_str = f"class {message.proto.name}(UniqueStrIdBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(BaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if auto_gen_id_type == IdType.INT_ID or auto_gen_id_type == IdType.DEFAULT:
                output_str = f"class {message.proto.name}(IncrementalIdCamelCacheBaseModel):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                output_str = f"class {message.proto.name}(UniqueStrIdCamelBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(CamelCacheBaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root, auto_gen_id_type

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str, is_msg_root, auto_gen_id_type = self._handle_ORM_class_declaration(message)

        # Adding docstring if message lvl comment available
        output_str += self._handle_class_docstring(message)
        output_str += self._handle_reentrant_lock(message)

        output_str += self._handle_cache_n_ws_connection_manager_data_members_override(message, is_msg_root)

        # Handling Id field
        output_str += self._handle_unique_id_required_fields(message, auto_gen_id_type)

        # handling remaining fields
        for field in message.fields:
            if field.proto.name == CachedORMModelPlugin.default_id_field_name:
                continue
            output_str += ' '*4 + self.handle_field_output(field)

        output_str += self._handle_config_class_and_other_root_class_versions(message, auto_gen_id_type)

        return output_str

    def _handle_max_id_model(self) -> str:
        output_str = f"class MaxId(PydanticBaseModel):\n"
        output_str += f"    max_id_val: int\n\n"
        return output_str

    def handle_imports(self) -> str:
        output_str = ("from pydantic import Field, BaseModel, field_validator, RootModel, "
                      "TimeSeriesConfig, Granularity\n")
        output_str += "import pendulum\n"
        output_str += "import datetime\n"
        output_str += "from typing import Dict, List, ClassVar, Any\n"
        ws_connection_manager_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                   "ws_connection_manager")
        output_str += f"from {ws_connection_manager_path} import PathWSConnectionManager, " \
                      f"\\\n\tPathWithIdWSConnectionManager\n"
        if self.enum_list:
            if self.enum_type == "int_enum":
                output_str += "from enum import IntEnum\n"
            elif self.enum_type == "str_enum":
                output_str += "from enum import auto\n"
                output_str += "from fastapi_restful.enums import StrEnum\n"
            # else not required: if enum type is not proper then it would be already handled in init

        output_str += f"from FluxPythonUtils.scripts.model_base_utils import *\n"
        generic_utils_import_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_utils")
        output_str += f"from {generic_utils_import_path} import validate_pendulum_datetime\n"
        output_str += f"from FluxPythonUtils.scripts.async_rlock import AsyncRLock\n\n\n"
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        super().assign_required_data_members(file)
        self.model_file_suffix = "beanie_model"
        self.model_file_name = f'{self.proto_file_name}_{self.model_file_suffix}'
        self.generic_routes_file_name = f'generic_cache_routes'


if __name__ == "__main__":
    main(CachedORMModelPlugin)
