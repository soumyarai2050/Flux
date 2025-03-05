#!/usr/bin/env python
import logging
import os
import time
from typing import Tuple
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginORMModel.cached_pydantic_model_plugin import CachedORMModelPlugin, main, IdType
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class BeanieModelPlugin(CachedORMModelPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.default_id_field_type: str = "PydanticObjectId"

    def is_field_indexed_option_enabled(self, field: protogen.Field) -> bool:
        if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_index):
            if field.enum is not None:
                err_str_ = f"Not supported: Enum type fields cannot be indexed, field {field.proto.name} of message " \
                           f"{field.parent.proto.name} has index option eneabled"
                logging.error(err_str_)
                raise Exception(err_str_)
            else:
                return True
        else:
            return False

    def _handle_field_cardinality(self, field: protogen.Field) -> str:
        field_type = self.proto_to_py_datatype(field)

        is_pendulum_datetime: bool = False
        if field_type == BeanieModelPlugin.pendulum_datetime_type:
            # Putting SkipJsonSchema in pendulum.dateTime field: swagger ui raises error due to issue
            # while calling model_json_schema interface implicitly if Class contains any field of
            # pendulum.DateTime type (arbitrary attribute)
            # - Putting SkipJsonSchema[None] with all pendulum_datetime fields (repeated, required and optional)
            # - putting it on required also otherwise putting like SkipJsonSchema[pendulum.DateTime] completely removes
            #   field from swagger ui (and could potentially raise some exception while using some
            #   json_schema interface)
            is_pendulum_datetime = True

        match field.cardinality.name.lower():
            case "optional":
                if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_collection_link):
                    output_str = f"{field.proto.name}: Link[{field_type}]"
                else:
                    output_str = f"{field.proto.name}: {field_type}"

                if is_pendulum_datetime:
                    output_str += f" | SkipJsonSchema[None]"
                else:
                    output_str += f" | None"
            case "repeated":
                if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_collection_link):
                    if self.is_option_enabled(field, BeanieModelPlugin.flux_fld_is_required):
                        output_str = f"{field.proto.name}: List[Link[{field_type}]]"

                        if is_pendulum_datetime:
                            output_str += f" | SkipJsonSchema[None]"
                    else:
                        output_str = f"{field.proto.name}: List[Link[{field_type}]]"

                        if is_pendulum_datetime:
                            output_str += f" | SkipJsonSchema[None]"
                        else:
                            output_str += f" | None"
                else:
                    if self.is_option_enabled(field, BeanieModelPlugin.flux_fld_is_required):
                        output_str = f"{field.proto.name}: List[{field_type}]"

                        if is_pendulum_datetime:
                            output_str += f" | SkipJsonSchema[None]"
                    else:
                        output_str = f"{field.proto.name}: List[{field_type}]"

                        if is_pendulum_datetime:
                            output_str += f" | SkipJsonSchema[None]"
                        else:
                            output_str += f" | None"
            case "required":
                if self.is_bool_option_enabled(field, BeanieModelPlugin.flux_fld_collection_link):
                    output_str = f"{field.proto.name}: Link[{field_type}]"
                else:
                    output_str = f"{field.proto.name}: {field_type}"

                if is_pendulum_datetime:
                    output_str += f" | SkipJsonSchema[None]"
            case other:
                err_str = f"unsupported field cardinality {other}"
                logging.exception(err_str)
                raise Exception(err_str)

        return output_str

    def handle_field_output(self, field: protogen.Field) -> str:
        output_str = self._handle_field_cardinality(field)

        is_optional = False
        if field.cardinality.name.lower() == "optional":
            is_optional = True
        elif field.cardinality.name.lower() == "repeated":
            if not self.is_option_enabled(field, BeanieModelPlugin.flux_fld_is_required):
                is_optional = True
        # else not required: is_required = False

        has_alias: bool
        if (has_alias := self.is_option_enabled(field, BeanieModelPlugin.flux_fld_alias)) or \
                field.location.leading_comments or field.proto.default_value:
            output_str += f' = Field('

            if has_alias:
                alias_name = self.get_simple_option_value_from_proto(field,
                                                                     BeanieModelPlugin.flux_fld_alias)
                output_str += f'alias={alias_name}'

            if leading_comments := field.location.leading_comments:
                if has_alias:
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

            if field.proto.default_value:
                if has_alias or leading_comments:
                    output_str += ", "
                output_str += f"default={BeanieModelPlugin.get_field_default_value(field)}"
            elif is_optional:
                if has_alias or leading_comments:
                    output_str += ", "
                output_str += f"default=None"

            output_str += ')\n'
        else:
            if is_optional:
                output_str += " = None"
            output_str += "\n"

        return output_str

    def _check_id_int_field(self, message: protogen.Message) -> IdType:
        """ Checking if id is of auto-increment int type"""
        for field in message.fields:
            if BeanieModelPlugin.default_id_field_name == field.proto.name:
                if field.kind.name.lower() in ["int32", "int64"]:
                    auto_gen_id = IdType.INT_ID
                    break
                elif field.kind.name.lower() in ["string"]:
                    auto_gen_id = IdType.STR_ID
                    break
                else:
                    err_str = "id field must be of int type, any other implementation is not supported yet"
                    logging.exception(err_str)
                    raise Exception(err_str)
        else:
            if message in self.root_message_list:
                auto_gen_id = IdType.DEFAULT
            else:
                auto_gen_id = IdType.NO_ID
        # else not required: if msg is non-root and if int id field doesn't exist in message then using default
        # PydanticObjectId id implementation
        return auto_gen_id

    def _handle_ORM_class_declaration(self, message: protogen.Message) -> Tuple[str, bool, IdType]:
        # auto_gen_id=INT_ID: If int type id field is present in message then adding int autoincrement impl
        # auto_gen_id=STR_ID: If str type id field is present in message then adding unique str impl
        # auto_gen_id=DEFAULT: If id field doesn't exist but msg is root type using default
        #                    PydanticObjectId id implementation
        # auto_gen_id=NO_ID: If id field doesn't exist and msg is non-root type then avoiding any id handling
        auto_gen_id_type: IdType = self._check_id_int_field(message)

        # raising exception if there is some model that is not db root but has int id since int id is
        # only available for db root models
        if (auto_gen_id_type == IdType.INT_ID and
                not (BeanieModelPlugin.is_option_enabled(message, BeanieModelPlugin.flux_msg_json_root) or
                     BeanieModelPlugin.is_option_enabled(message, BeanieModelPlugin.flux_msg_json_root_time_series))):
            err_str = (f"Non-Db-Root models can't have int type ID field, found in model {message.proto.name}, "
                       f"use string type id instead")
            logging.exception(err_str)
            raise Exception(err_str)
        # else not required: if msg is not root or msg is root and id not int then proceeding further

        if message in self.root_message_list:
            is_msg_root = True
        else:
            is_msg_root = False
        if self.response_field_case_style.lower() == "snake":
            if auto_gen_id_type == IdType.INT_ID:
                if is_msg_root:
                    output_str = f"class {message.proto.name}(Document, IncrementalIdBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(IncrementalIdBaseModel):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                if is_msg_root:
                    output_str = f"class {message.proto.name}(Document, UniqueStrIdBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(UniqueStrIdBaseModel):\n"
            else:
                if is_msg_root:
                    output_str = f"class {message.proto.name}(Document):\n"
                else:
                    output_str = f"class {message.proto.name}(PydanticBaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if auto_gen_id_type == IdType.INT_ID:
                if is_msg_root:
                    output_str = f"class {message.proto.name}(Document, IncrementalIdCamelBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(IncrementalIdCamelBaseModel):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                if is_msg_root:
                    output_str = f"class {message.proto.name}(Document, UniqueStrIdCamelBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(UniqueStrIdCamelBaseModel):\n"
            else:
                if is_msg_root:
                    output_str = f"class {message.proto.name}(Document, CamelBaseModel):\n"
                else:
                    output_str = f"class {message.proto.name}(PydanticBaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root, auto_gen_id_type

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str, is_msg_root, auto_gen_id_type = self._handle_ORM_class_declaration(message)

        output_str += self._handle_class_docstring(message)
        output_str += self._handle_reentrant_lock(message)

        output_str += self._handle_cache_n_ws_connection_manager_data_members_override(message, is_msg_root)
        if self.is_option_enabled(message, BeanieModelPlugin.flux_msg_json_root_time_series):
            output_str += "    is_time_series: ClassVar[bool] = True\n"
        else:
            output_str += "    is_time_series: ClassVar[bool] = False\n"

        for field in message.fields:
            if field.proto.name == CachedORMModelPlugin.default_id_field_name:
                output_str += self._handle_unique_id_required_fields(message, auto_gen_id_type)
            else:
                output_str += ' '*4 + self.handle_field_output(field)
        output_str += self._handle_config_class_and_other_root_class_versions(message, auto_gen_id_type)

        return output_str

    def _handle_reentrant_lock(self, message: protogen.Message) -> str:
        # taking first obj since json root is of non-repeated option
        if message in self.root_message_list and message not in self.reentrant_lock_non_required_msg:
            return "    reentrant_lock: ClassVar[AsyncRLock] = AsyncRLock()\n"
        else:
            return ""

    def _handle_max_id_model(self) -> str:
        output_str = f"class MaxId(PydanticBaseModel):\n"
        output_str += f"    max_id_val: int\n\n"
        return output_str

    def handle_imports(self) -> str:
        output_str = "# standard imports\n"
        output_str += "from typing import List, ClassVar, Dict\n"
        output_str += "import datetime\n\n"
        output_str += "# 3rd party imports\n"
        output_str += "from beanie import Indexed, Document, PydanticObjectId, Link, TimeSeriesConfig, Granularity\n"
        output_str += "from pydantic import BaseModel, Field, field_validator, RootModel\n"
        output_str += "import pendulum\n"
        output_str += "from pydantic.json_schema import SkipJsonSchema\n"

        if self.enum_list:
            if self.enum_type == "int_enum":
                output_str += "from enum import IntEnum\n"
            elif self.enum_type == "str_enum":
                output_str += "from enum import auto\n"
                output_str += "from fastapi_restful.enums import StrEnum\n"
            # else not required: if enum type is not proper then it would be already handled in init

        ws_connection_manager_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                   "ws_connection_manager")
        output_str += f"from {ws_connection_manager_path} import PathWSConnectionManager, " \
                      f"\\\n\tPathWithIdWSConnectionManager\n"
        output_str += f"from FluxPythonUtils.scripts.model_base_utils import *\n"
        generic_utils_import_path= self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_utils")
        output_str += f"from {generic_utils_import_path} import validate_pendulum_datetime\n"
        output_str += f"from FluxPythonUtils.scripts.async_rlock import AsyncRLock\n"

        output_str += "\n\n"
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        super().assign_required_data_members(file)
        self.model_file_suffix = "beanie_model"
        self.model_file_name = f'{self.proto_file_name}_{self.model_file_suffix}'
        self.generic_routes_file_name = f'generic_beanie_routes'


if __name__ == "__main__":
    main(BeanieModelPlugin)
