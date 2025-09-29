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
from Flux.PyCodeGenEngine.PluginORMModel.dataclass_model_plugin import DataclassModelPlugin, main, IdType
from FluxPythonUtils.scripts.general_utility_functions import convert_to_capitalized_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class MsgspecModelPlugin(DataclassModelPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    default_id_type_var_name = "ObjectId"
    datetime_to_epoch: str = "DateTimeToEpoch"
    epoch_to_datetime: str = "EpochToDateTime"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.default_id_field_type: str = "ObjectId"

    def is_field_indexed_option_enabled(self, field: protogen.Field) -> bool:
        if self.is_bool_option_enabled(field, MsgspecModelPlugin.flux_fld_index):
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
                if self.is_option_enabled(field, MsgspecModelPlugin.flux_fld_is_required):
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
            output_str += f'    id: int | None = field(default_factory=(lambda: {message.proto.name}.next_id()), name="_id")\n'
            output_str += (f'    update_id: int = field(default_factory=(lambda: {message.proto.name}.'
                           f'next_update_id()))\n')
        elif auto_gen_id_type == IdType.STR_ID:
            output_str = "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += "    _max_update_id_val: ClassVar[int | None] = None\n"
            output_str += f'    id: str | None = field(default_factory=(lambda: {message.proto.name}.next_id()), name="_id")\n'
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
            if not self.is_option_enabled(field, MsgspecModelPlugin.flux_fld_is_required):
                is_optional = True
        # else not required: is_required = False

        has_alias: bool = self.is_option_enabled(field, MsgspecModelPlugin.flux_fld_alias)
        if field.proto.default_value:
            output_str += f' = field('
            output_str += f"default={MsgspecModelPlugin.get_field_default_value(field)}"
            if has_alias:
                alias_name = self.get_simple_option_value_from_proto(field,
                                                                     MsgspecModelPlugin.flux_fld_alias)
                output_str += f", name='{alias_name}'"
            output_str += ')'
        elif is_optional:
            output_str += f' = field('
            output_str += f"default=None"
            if has_alias:
                alias_name = self.get_simple_option_value_from_proto(field,
                                                                     MsgspecModelPlugin.flux_fld_alias)
                output_str += f", name='{alias_name}'"
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
            if MsgspecModelPlugin.default_id_field_name == field.proto.name:
                if field.kind.name.lower() in ["int32", "int64"]:
                    auto_gen_id = IdType.INT_ID
                    break
                elif field.kind.name.lower() in ["string"]:
                    auto_gen_id = IdType.STR_ID
                    break
                else:
                    err_str = "id field must be of int or string type, any other implementation is not supported yet"
                    logging.exception(err_str)
                    raise Exception(err_str)
        else:
            if message in self.root_message_list:
                auto_gen_id = IdType.DEFAULT
            else:
                auto_gen_id = IdType.NO_ID
        # else not required: if msg is non-root and if int id field doesn't exist in message then using default
        # ObjectId id implementation
        return auto_gen_id

    def _handle_ORM_class_declaration(self, message: protogen.Message) -> Tuple[str, bool, IdType]:
        # auto_gen_id=INT_ID: If int type id field is present in message then adding int autoincrement impl
        # auto_gen_id=STR_ID: If str type id field is present in message then adding unique str impl
        # auto_gen_id=DEFAULT: If id field doesn't exist but msg is root type using default
        #                    ObjectId id implementation
        # auto_gen_id=NO_ID: If id field doesn't exist and msg is non-root type then avoiding any id handling
        auto_gen_id_type: IdType = self._check_id_int_field(message)

        # raising exception if there is some model that is not db root but has int id since int id is
        # only available for db root models
        if (auto_gen_id_type == IdType.INT_ID and
                not (MsgspecModelPlugin.is_option_enabled(message, MsgspecModelPlugin.flux_msg_json_root) or
                     MsgspecModelPlugin.is_option_enabled(message, MsgspecModelPlugin.flux_msg_json_root_time_series))):
            err_str = (f"Non-Db-Root models can't have int type ID field, found in model {message.proto.name}, "
                       f"use string type id instead")
            logging.exception(err_str)
            raise Exception(err_str)
        # else not required: if msg is not root or msg is root and id not int then proceeding further

        if message in self.root_message_list:
            is_msg_root = True
        else:
            is_msg_root = False
        output_str = ""
        if self.response_field_case_style.lower() == "snake":
            if auto_gen_id_type == IdType.INT_ID:
                output_str += f"class {message.proto.name}(IncrementalIdMsgspec, kw_only=True):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                output_str += f"class {message.proto.name}(UniqueStrIdMsgspec, kw_only=True):\n"
            else:
                output_str += f"class {message.proto.name}(MsgspecBaseModel, kw_only=True):\n"
        elif self.response_field_case_style.lower() == "camel":
            if auto_gen_id_type == IdType.INT_ID:
                output_str += f"class {message.proto.name}(IncrementalIdCamelBaseModel):\n"
            elif auto_gen_id_type == IdType.STR_ID:
                output_str += f"class {message.proto.name}(UniqueStrIdCamelBaseModel):\n"
            else:
                output_str += f"class {message.proto.name}(MsgspecBaseModel, kw_only=True):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root, auto_gen_id_type

    def _underlying_handle_none_default_fields(self, message: protogen.Message, has_id_field: bool) -> str:
        output_str = ""
        if message in self.root_message_list:
            if not has_id_field:
                output_str += f"    id: {MsgspecModelPlugin.default_id_type_var_name} | None = " \
                              f"field(default=None, name='_id')\n"
            # else not required: if id field is present already then will be handled in next for loop

        for field in message.fields:
            if field.proto.name == MsgspecModelPlugin.default_id_field_name:
                output_str += f"    id: {self.proto_to_py_datatype(field)} | None = " \
                              f"field(default=None, name='_id')\n"
                continue
            # else not required: If message is not root type then avoiding id field in optional version so that
            # it's id can be generated if not provided inside root message
            if field.message is not None:
                if field.cardinality.name.lower() == "repeated":
                    output_str += f"    {field.proto.name}: List[{field.message.proto.name}BaseModel] | None = None\n"
                else:
                    output_str += f"    {field.proto.name}: {field.message.proto.name}BaseModel | None = None\n"
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
        output_str += f"class {message_name}BaseModel(MsgspecBaseModel, kw_only=True):\n"
        has_id_field = MsgspecModelPlugin.default_id_field_name in [field.proto.name for field in message.fields]
        output_str += self._underlying_handle_none_default_fields(message, has_id_field)

        output_str += (
            self._handle_post_init_in_basemodel_versions(message, auto_gen_id_type,
                                                         alias_name_dict=kwargs.get("alias_name_dict", {})))
        output_str += "\n\n"
        return output_str

    def _handle_alias_setattr_output_in_model(self, alias_name_dict: Dict) -> str:
        output_str = ''
        output_str += ' ' * 4 + f"def __setattr__(self, name, value):\n"
        output_str += ' ' * 4 + f"    if name == '_id':\n"
        output_str += ' ' * 4 + f"        name = 'id'\n"
        for field_name, alias in alias_name_dict.items():
            output_str += ' ' * 4 + f"    if name == '{alias}':\n"
            output_str += ' ' * 4 + f"        name = '{field_name}'\n"
        output_str += ' ' * 4 + f"    super().__setattr__(name, value)\n"
        return output_str

    def _handle_dt_fields_to_be_int(self, message: protogen.Message, indent_count: int,
                                    dict_name: str, epoch_to_dt_or_dt_to_epoch: str) -> str:
        output_str = ''
        for field in message.fields:
            field_name = field.proto.name
            if field.message is not None:
                for field_ in field.message.fields:
                    if self.is_bool_option_enabled(field_, MsgspecModelPlugin.flux_fld_val_is_datetime):
                        break
                else:
                    # else not required: ignoring messages not having any date_time field
                    continue

                # reaches here only if msg has any datetime field
                output_str += ' ' * indent_count + f"    {dict_name}_{field_name} = {dict_name}.get('{field_name}')\n"
                output_str += ' ' * indent_count + f"    if {dict_name}_{field_name} is not None:\n"
                is_repeated = field.cardinality.name.lower() == "repeated"

                if is_repeated:
                    output_str += ' ' * (indent_count+4) + f"    for {dict_name}_{field_name}_ in {dict_name}_{field_name}:\n"
                    output_str += self._handle_dt_fields_to_be_int(field.message, indent_count + 8,
                                                               f"{dict_name}_{field_name}_",
                                                                   epoch_to_dt_or_dt_to_epoch)
                else:
                    output_str += self._handle_dt_fields_to_be_int(field.message, indent_count + 4,
                                                                   f"{dict_name}_{field_name}",
                                                                   epoch_to_dt_or_dt_to_epoch)

            elif self.is_bool_option_enabled(field, MsgspecModelPlugin.flux_fld_val_is_datetime):
                output_str += ' ' * indent_count + f"    {field_name} = {dict_name}.get('{field_name}')\n"
                output_str += ' ' * indent_count + f"    if {field_name} is not None:\n"
                if epoch_to_dt_or_dt_to_epoch == MsgspecModelPlugin.datetime_to_epoch:
                    output_str += ' ' * indent_count + f"        if isinstance({field_name}, DateTime):\n"
                    output_str += ' ' * indent_count + f"            {dict_name}['{field_name}'] = get_epoch_from_pendulum_dt({field_name})\n"
                    output_str += ' ' * indent_count + f"        elif isinstance({field_name}, datetime.datetime):\n"
                    output_str += ' ' * indent_count + f"            {dict_name}['{field_name}'] = get_epoch_from_standard_dt({field_name})\n"
                else:
                    output_str += ' ' * indent_count + f"        if isinstance({field_name}, int):\n"
                    output_str += ' ' * indent_count + f"            {dict_name}['{field_name}'] = get_pendulum_dt_from_epoch({field_name})\n"

        return output_str

    def _handle_override_enc_n_dec_hook_in_(self, indent_count: int):
        output_str = ' ' * indent_count + f"@classmethod\n"
        output_str += ' ' * indent_count + f"def dec_hook(cls, type: Type, obj: Any):\n"
        output_str += ' ' * indent_count + f"    if type == DateTime and isinstance(obj, int):\n"
        output_str += ' ' * indent_count + f"        return get_pendulum_dt_from_epoch(obj)\n"
        output_str += ' ' * indent_count + f"    else:\n"
        output_str += ' ' * indent_count + f"        return super().dec_hook(type, obj)\n\n"
        output_str += ' ' * indent_count + f"@classmethod\n"
        output_str += ' ' * indent_count + f"def enc_hook(cls, obj: Any):\n"
        output_str += ' ' * indent_count + f"    if isinstance(obj, DateTime):\n"
        output_str += ' ' * indent_count + f"        return get_epoch_from_pendulum_dt(obj)\n"
        output_str += ' ' * indent_count + f"    elif isinstance(obj, datetime.datetime):\n"
        output_str += ' ' * indent_count + f"        return get_epoch_from_standard_dt(obj)\n"
        output_str += ' ' * indent_count + f"    elif isinstance(obj, Timestamp):\n"
        output_str += ' ' * indent_count + f"        return get_epoch_from_pandas_timestamp(obj)\n"
        return output_str

    def _handle_convert_to_dict_for_db_op(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        indent_count = 4
        output_str = ' ' * indent_count + "@staticmethod\n"
        output_str += ' ' * indent_count + (f"def convert_ts_fields_from_datetime_to_epoch_int("
                                            f"{message_name_snake_cased}_dict_obj: Dict):\n")
        output_str_ = self._handle_dt_fields_to_be_int(message, indent_count,
                                                       f"{message_name_snake_cased}_dict_obj",
                                                       MsgspecModelPlugin.datetime_to_epoch)
        if output_str_:
            output_str += output_str_ + "\n"
        else:
            output_str += ' ' * indent_count + "    pass\n\n"

        output_str += ' ' * indent_count + "@staticmethod\n"
        output_str += ' ' * indent_count + (f"def convert_ts_fields_from_epoch_to_datetime_obj("
                                            f"{message_name_snake_cased}_dict_obj: Dict):\n")
        output_str_ = self._handle_dt_fields_to_be_int(message, indent_count,
                                                       f"{message_name_snake_cased}_dict_obj",
                                                       MsgspecModelPlugin.epoch_to_datetime)
        if output_str_:
            output_str += output_str_ + "\n"
        else:
            output_str += ' ' * indent_count + "    pass\n\n"

        output_str += self._handle_override_enc_n_dec_hook_in_(indent_count)

        return output_str

    def _handle_post_init_handling(self, message: protogen.Message, auto_gen_id_type: IdType, **kwargs):
        output_str = ""

        alias_name_dict = kwargs.get("alias_name_dict", {})

        if auto_gen_id_type in [IdType.INT_ID, IdType.STR_ID]:
            output_str += "\n"
            output_str += ' ' * 4 + "def __post_init__(self):\n"
            output_str += ' ' * 4 + "    if self.id is None:\n"
            output_str += ' ' * 4 + f"        self.id = {message.proto.name}.next_id()\n\n"

            output_str += self._handle_alias_setattr_output_in_model(alias_name_dict)

        output_str += "\n"
        output_str += self._handle_convert_to_dict_for_db_op(message)

        return output_str, ""

    def _handle_post_init_in_basemodel_versions(self, message: protogen.Message, auto_gen_id_type: IdType, **kwargs):
        output_str = ""

        alias_name_dict = kwargs.get("alias_name_dict", {})

        if auto_gen_id_type in [IdType.INT_ID, IdType.STR_ID]:
            output_str += "\n"
            output_str += self._handle_alias_setattr_output_in_model(alias_name_dict)

        output_str += "\n"
        output_str += self._handle_convert_to_dict_for_db_op(message)

        return output_str

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message,
                                                           auto_gen_id_type: IdType) -> str:
        alias_name_dict: Dict[str, str] = {}
        for field in message.fields:
            alias_name = self.get_simple_option_value_from_proto(field,
                                                                 MsgspecModelPlugin.flux_fld_alias)
            if alias_name:
                alias_name_dict[field.proto.name] = alias_name

        output_str, _ = self._handle_post_init_handling(message, auto_gen_id_type,
                                                        alias_name_dict=alias_name_dict)
        output_str += "\n\n"

        # Adding other versions for root model class
        output_str += self.handle_dummy_message_gen(message, auto_gen_id_type, alias_name_dict=alias_name_dict)

        # handling projections
        output_str += self.handle_projection_models_output(message)

        return output_str

    def _handle_projection_model_output(self, message: protogen.Message, projection_val_to_fields_dict,
                                         time_field_name: str, meta_field_name: str, meta_field_type: str) -> str:
        output_str = ""
        for projection_option_val, field_names in projection_val_to_fields_dict.items():
            field_name_list: List[str] = []
            for field_name in field_names:
                if "." in field_name:
                    field_name_list.append("_".join(field_name.split(".")))
                else:
                    field_name_list.append(field_name)
            field_names_str = "_n_".join(field_name_list)
            field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)
            output_str += (f"class {message.proto.name}ProjectionFor{field_names_str_camel_cased}(MsgspecBaseModel, "
                           f"kw_only=True):\n")
            output_str += " " * 4 + f"{time_field_name}: pendulum.DateTime\n"

            field_name_to_type_dict: Dict = {}
            for field_name in field_names:
                if "." in field_name:
                    for field in message.fields:
                        if field.proto.name == field_name:
                            field_type = self.get_nested_field_proto_to_py_datatype(field, field_name)
                            field_name_to_type_dict[field_name] = field_type
                else:
                    for field in message.fields:
                        if field.proto.name == field_name:
                            field_type = self.proto_to_py_datatype(field)
                            field_name_to_type_dict[field_name] = field_type

            for field_name in field_names:
                field_type = field_name_to_type_dict.get(field_name)
                if field_type is None:
                    err_str = ("Could not find type for field_name from field_name_to_type_dict, "
                               "probably bug in field_name_to_type_dict generation/population")
                    logging.exception(err_str)
                    raise Exception(err_str)

                if "." in field_name:
                    output_str += " " * 4 + f"{field_name.split('.')[0]}: {field_type}\n"
                else:
                    output_str += " " * 4 + f"{field_name}: {field_type}\n"
            output_str += "\n\n"

            # container class for projection model
            output_str += (f"class {message.proto.name}ProjectionContainerFor"
                           f"{field_names_str_camel_cased}(MsgspecBaseModel, kw_only=True):\n")
            output_str += f"    {meta_field_name}: {meta_field_type}\n"
            output_str += (f"    projection_models: List[{message.proto.name}ProjectionFor"
                           f"{field_names_str_camel_cased}]\n\n\n")

            # List class of container class
            output_str += (f'class {message.proto.name}ProjectionContainerFor'
                           f'{field_names_str_camel_cased}List(ListModelMsgspec):\n')
            output_str += (f'    root: List[{message.proto.name}ProjectionContainerFor'
                           f'{field_names_str_camel_cased}]\n\n\n')
        return output_str

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str, is_msg_root, auto_gen_id_type = self._handle_ORM_class_declaration(message)

        output_str += self._handle_class_docstring(message)
        output_str += self._handle_reentrant_lock(message)

        output_str += self._handle_cache_n_ws_connection_manager_data_members_override(message, is_msg_root)
        if self.is_option_enabled(message, MsgspecModelPlugin.flux_msg_json_root_time_series):
            output_str += "    is_time_series: ClassVar[bool] = True\n"
            output_str += "    enable_large_db_object: ClassVar[bool] = False\n"
        else:
            output_str += "    is_time_series: ClassVar[bool] = False\n"
            option_val = self.get_complex_option_value_from_proto(message, MsgspecModelPlugin.flux_msg_json_root)
            if option_val.get(MsgspecModelPlugin.flux_json_root_enable_large_db_object_field):
                output_str += "    enable_large_db_object: ClassVar[bool] = True\n"
            else:
                output_str += "    enable_large_db_object: ClassVar[bool] = False\n"

        for field in message.fields:
            if field.proto.name == MsgspecModelPlugin.default_id_field_name:
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
        for message in self.root_message_list+self.query_message_list:
            if message in file.messages:
                output_str += f'class {message.proto.name}BaseModelList(ListModelMsgspec):\n'
                output_str += f'    root: List[{message.proto.name}BaseModel]\n\n'
                output_str += self._handle_override_enc_n_dec_hook_in_(indent_count=4)
                output_str += f'\n\n'
        return output_str

    def _handle_max_id_model(self) -> str:
        output_str = f"class MaxId(MsgspecBaseModel):\n"
        output_str += f"    max_id_val: int\n\n"
        return output_str

    def _handle_filtered_doc_count_model(self) -> str:
        output_str = f"class FilteredDocCount(MsgspecBaseModel):\n"
        output_str += f"    filtered_count: int\n\n"
        return output_str

    def handle_imports(self) -> str:
        output_str = "# standard imports\n"
        output_str += "from typing import List, ClassVar, Dict\n"
        output_str += "from msgspec import Struct, field\n"
        output_str += "from bson import ObjectId\n"
        output_str += "import datetime\n\n"
        output_str += "# 3rd party imports\n"
        output_str += "import pendulum\n"
        output_str += "from pendulum import DateTime\n"
        output_str += "from pandas import Timestamp\n"

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
        generic_utils_import_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_utils")
        output_str += f"from {generic_utils_import_path} import validate_pendulum_datetime\n"
        output_str += f"from FluxPythonUtils.scripts.async_rlock import AsyncRLock\n"
        output_str += f"from FluxPythonUtils.scripts.model_base_utils import *\n"
        base_strat_cache_import_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR",
                                                                     f"{self.proto_file_name}_ts_utils")
        output_str += f"from {base_strat_cache_import_path} import *\n"

        output_str += "\n\n"
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        super().assign_required_data_members(file)
        self.model_file_suffix = "msgspec_model"
        self.model_file_name = f'{self.proto_file_name}_{self.model_file_suffix}'
        self.generic_routes_file_name = f'generic_msgspec_routes'


if __name__ == "__main__":
    main(MsgspecModelPlugin)
