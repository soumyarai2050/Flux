#!/usr/bin/env python
import logging
import os
import time
from typing import Tuple, List, Dict
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginORMModel.cached_pydantic_model_plugin import CachedORMModelPlugin, main, IdType
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class DataclassModelPlugin(CachedORMModelPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    default_id_type_var_name = "ObjectId"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.default_id_field_type: str = "ObjectId"

    def is_field_indexed_option_enabled(self, field: protogen.Field) -> bool:
        if self.is_bool_option_enabled(field, DataclassModelPlugin.flux_fld_index):
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
        match field.cardinality.name.lower():
            case "optional":
                output_str = f"{field.proto.name}: {field_type} | None"
            case "repeated":
                if self.is_option_enabled(field, DataclassModelPlugin.flux_fld_is_required):
                    output_str = f"{field.proto.name}: List[{field_type}]"
                else:
                    output_str = f"{field.proto.name}: List[{field_type}] | None"
            case "required":
                output_str = f"{field.proto.name}: {field_type}"
            case other:
                err_str = f"unsupported field cardinality {other}"
                logging.exception(err_str)
                raise Exception(err_str)

        return output_str

    def _handle_unique_id_required_fields(self, message: protogen.Message, auto_gen_id_type: IdType) -> str:
        if auto_gen_id_type == IdType.INT_ID:
            output_str = "    _max_id_val: ClassVar[int | None] = None\n"
            output_str += "    _max_update_id_val: ClassVar[int | None] = None\n"
            output_str += "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += f'    _id: int = field(default_factory=(lambda: {message.proto.name}.next_id()))\n'
            output_str += (f'    update_id: int = field(default_factory=(lambda: {message.proto.name}.'
                           f'next_update_id()))\n')
        elif auto_gen_id_type == IdType.STR_ID:
            output_str = "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += "    _max_update_id_val: ClassVar[int | None] = None\n"
            output_str += f'    _id: str = field(default_factory=(lambda: {message.proto.name}.next_id()))\n'
        else:
            output_str = ""

        return output_str

    def add_datetime_validator(self, datetime_field: protogen.Field) -> str:
        return ""

    def handle_field_output(self, field: protogen.Field) -> str:
        output_str = self._handle_field_cardinality(field)

        is_optional = False
        if field.cardinality.name.lower() == "optional":
            is_optional = True
        elif field.cardinality.name.lower() == "repeated":
            if not self.is_option_enabled(field, DataclassModelPlugin.flux_fld_is_required):
                is_optional = True
        # else not required: is_required = False

        has_alias: bool
        if field.proto.default_value:
            output_str += f' = field('
            output_str += f"default={DataclassModelPlugin.get_field_default_value(field)}"
            output_str += ')'
        elif is_optional:
            output_str += f' = field('
            output_str += f"default=None"
            output_str += ')'

        if leading_comments := field.location.leading_comments:
            # else not required: If double quotes not found then avoiding
            comments = ", ".join(leading_comments.split("\n"))
            output_str += f'    # "{comments}"'
        # else not required: If leading_comments are not present then avoiding text to be added
        output_str += "\n"

        return output_str

    def _check_id_int_field(self, message: protogen.Message) -> IdType:
        """ Checking if id is of auto-increment int type"""
        for field in message.fields:
            if DataclassModelPlugin.default_id_field_name == field.proto.name:
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
                not (DataclassModelPlugin.is_option_enabled(message, DataclassModelPlugin.flux_msg_json_root) or
                     DataclassModelPlugin.is_option_enabled(message, DataclassModelPlugin.flux_msg_json_root_time_series))):
            err_str = (f"Non-Db-Root models can't have int type ID field, found in model {message.proto.name}, "
                       f"use string type id instead")
            logging.exception(err_str)
            raise Exception(err_str)
        # else not required: if msg is not root or msg is root and id not int then proceeding further

        if message in self.root_message_list:
            is_msg_root = True
        else:
            is_msg_root = False
        output_str = "@dataclass(kw_only=True)\n"
        if self.response_field_case_style.lower() == "snake":
            if auto_gen_id_type == IdType.INT_ID:
                output_str += f"class {message.proto.name}(IncrementalIdDataClass):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                output_str += f"class {message.proto.name}(UniqueStrIdDataClass):\n"
            else:
                output_str += f"class {message.proto.name}(DataclassBaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if auto_gen_id_type == IdType.INT_ID:
                output_str += f"class {message.proto.name}(IncrementalIdCamelBaseModel):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                output_str += f"class {message.proto.name}(UniqueStrIdCamelBaseModel):\n"
            else:
                output_str += f"class {message.proto.name}(DataclassBaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root, auto_gen_id_type

    def _underlying_handle_none_default_fields(self, message: protogen.Message, has_id_field: bool) -> str:
        output_str = ""
        if message in self.root_message_list:
            if not has_id_field:
                output_str += f"    _id: {DataclassModelPlugin.default_id_type_var_name} | None = " \
                              f"field(default=None)\n"
            # else not required: if id field is present already then will be handled in next for loop

        for field in message.fields:
            if field.proto.name == DataclassModelPlugin.default_id_field_name:
                output_str += f"    _id: {self.proto_to_py_datatype(field)} | None = " \
                              f"field(default=None)\n"
                output_str += "    update_id: int | None = None\n"
                continue
            # else not required: If message is not root type then avoiding id field in optional version so that
            # it's id can be generated if not provided inside root message
            if field.message is not None:
                if field.cardinality.name.lower() == "repeated":
                    output_str += (f"    {field.proto.name}: List[{field.message.proto.name}BaseModel] | "
                                   f"List[{field.message.proto.name}] | None = None\n")
                else:
                    output_str += (f"    {field.proto.name}: {field.message.proto.name}BaseModel | "
                                   f"{field.message.proto.name} | None = None\n")
            else:
                field_type = self.proto_to_py_datatype(field)
                if field.cardinality.name.lower() == "repeated":
                    output_str += f"    {field.proto.name}: List[{field_type}] | None = None\n"
                else:
                    output_str += f"    {field.proto.name}: {field_type} | None = None\n"

        return output_str

    def handle_dummy_message_gen(self, message: protogen.Message, auto_gen_id_type: IdType, **kwargs) -> str:
        message_name = message.proto.name

        output_str = ""
        for suffix_ in ["BaseModel", "Optional"]:
            output_str += f"@dataclass(kw_only=True)\n"
            output_str += f"class {message_name}{suffix_}(DataclassBaseModel):\n"
            has_id_field = DataclassModelPlugin.default_id_field_name in [field.proto.name for field in message.fields]
            output_str += self._underlying_handle_none_default_fields(message, has_id_field)

            output_str_, _ = self._handle_post_init_handling(message, auto_gen_id_type)
            output_str += output_str_
            output_str += "\n"
        return output_str

    def _handle_post_init_handling(self, message: protogen.Message, auto_gen_id_type: IdType, **kwargs):
        output_str = ""

        datetime_field_list: List[protogen.Field] = []
        message_type_field_list: List[protogen.Field] = []
        repeated_message_type_field_list: List[protogen.Field] = []
        enum_type_field_list: List[protogen.Field] = []
        repeated_enum_type_field_list: List[protogen.Field] = []
        alias_to_field_dict: Dict[str, protogen.Field] = {}
        for field in message.fields:
            if self.is_option_enabled(field, DataclassModelPlugin.flux_fld_val_is_datetime):
                datetime_field_list.append(field)
            elif field.message is not None:
                if field.cardinality.name.lower() == "repeated":
                    repeated_message_type_field_list.append(field)
                else:
                    message_type_field_list.append(field)
            elif field.enum is not None:
                if field.cardinality.name.lower() == "repeated":
                    repeated_enum_type_field_list.append(field)
                else:
                    enum_type_field_list.append(field)

            if self.is_option_enabled(field, DataclassModelPlugin.flux_fld_alias):
                alias_name = self.get_simple_option_value_from_proto(field,
                                                                     DataclassModelPlugin.flux_fld_alias)
                alias_to_field_dict[alias_name] = field

        if auto_gen_id_type in [IdType.INT_ID, IdType.STR_ID]:
            output_str += "\n"
            output_str += ' ' * 4 + "@property\n"
            output_str += ' ' * 4 + "def id(self):\n"
            output_str += ' ' * 8 + "return self._id\n"

        for alias_name, alias_field in alias_to_field_dict.items():
            output_str += "\n"
            output_str += ' ' * 4 + "@property\n"
            output_str += ' ' * 4 + f"def {alias_name}(self):\n"
            output_str += ' ' * 8 + f"return self.{alias_field.proto.name}\n"

        if datetime_field_list + message_type_field_list + enum_type_field_list:
            output_str += "\n"
            output_str += ' ' * 4 + "def __post_init__(self):\n"
            for dt_field in datetime_field_list:
                output_str += ' ' * 8 + (f"self.{dt_field.proto.name} = "
                                         f"validate_pendulum_datetime(self.{dt_field.proto.name})\n")
            for msg_field in message_type_field_list:
                output_str += ' ' * 8 + f"if isinstance(self.{msg_field.proto.name}, dict):\n"
                output_str += ' ' * 12 + f"self.{msg_field.proto.name} = {msg_field.message.proto.name}(**self.{msg_field.proto.name})\n"
            for enum_field in enum_type_field_list:
                output_str += ' ' * 8 + f"if isinstance(self.{enum_field.proto.name}, str):\n"
                output_str += ' ' * 12 + f"self.{enum_field.proto.name} = {enum_field.enum.proto.name}(self.{enum_field.proto.name})\n"
            if repeated_message_type_field_list:
                for msg_field in repeated_message_type_field_list:
                    output_str += ' ' * 8 + f"if self.{msg_field.proto.name}:\n"
                    output_str += ' ' * 12 + f"for idx, {msg_field.proto.name} in enumerate(self.{msg_field.proto.name}):\n"
                    output_str += ' ' * 16 + f"if isinstance({msg_field.proto.name}, dict):\n"
                    output_str += ' ' * 20 + f"self.{msg_field.proto.name}[idx] = {msg_field.message.proto.name}(**{msg_field.proto.name})\n"
            if repeated_enum_type_field_list:
                for enum_field in repeated_enum_type_field_list:
                    output_str += ' ' * 8 + f"if self.{enum_field.proto.name}:\n"
                    output_str += ' ' * 12 + f"for idx, {enum_field.proto.name} in enumerate(self.{enum_field.proto.name}):\n"
                    output_str += ' ' * 16 + f"if isinstance({enum_field.proto.name}, str):\n"
                    output_str += ' ' * 20 + f"self.{enum_field.proto.name}[idx] = {enum_field.enum.proto.name}({enum_field.proto.name})\n"
        return output_str, datetime_field_list

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message,
                                                           auto_gen_id_type: IdType) -> str:
        output_str, datetime_field_list = self._handle_post_init_handling(message, auto_gen_id_type)
        output_str += "\n\n"

        # Adding other versions for root pydantic class
        output_str += self.handle_dummy_message_gen(message, auto_gen_id_type)

        return output_str

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str, is_msg_root, auto_gen_id_type = self._handle_ORM_class_declaration(message)

        output_str += self._handle_class_docstring(message)
        output_str += self._handle_reentrant_lock(message)

        output_str += self._handle_cache_n_ws_connection_manager_data_members_override(message, is_msg_root)
        if self.is_option_enabled(message, DataclassModelPlugin.flux_msg_json_root_time_series):
            output_str += "    is_time_series: ClassVar[bool] = True\n"
        else:
            output_str += "    is_time_series: ClassVar[bool] = False\n"

        for field in message.fields:
            if field.proto.name == DataclassModelPlugin.default_id_field_name:
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

    def list_model_content(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.root_message_list:
            if message in file.messages:
                output_str += f'@dataclass\n'
                output_str += f'class {message.proto.name}BaseModelList(ListModelBase):\n'
                output_str += f'    root: List[{message.proto.name}BaseModel]\n\n'
                output_str += f'    def __post_init__(self):\n'
                output_str += f'        for idx, dict_obj in enumerate(self.root):\n'
                output_str += f'            if isinstance(dict_obj, dict):\n'
                output_str += f'                self.root[idx] = {message.proto.name}BaseModel(**dict_obj)\n'
                output_str += f'\n\n'
        return output_str

    def handle_imports(self) -> str:
        output_str = "# standard imports\n"
        output_str += "from typing import List, ClassVar, Dict\n"
        output_str += "from dataclasses import dataclass, field\n"
        output_str += "from bson import ObjectId\n"
        output_str += "import datetime\n\n"
        output_str += "# 3rd party imports\n"
        output_str += "import pendulum\n"

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

    def _handle_max_id_model(self) -> str:
        output_str = f"@dataclass(kwargs_only=True)\n"
        output_str += f"class MaxId(DataclassBaseModel):\n"
        output_str += f"    max_id_val: int\n\n"
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        super().assign_required_data_members(file)
        self.model_file_suffix = "dataclass_model"
        self.model_file_name = f'{self.proto_file_name}_{self.model_file_suffix}'
        self.generic_routes_file_name = f'generic_dataclass_routes'


if __name__ == "__main__":
    main(DataclassModelPlugin)
