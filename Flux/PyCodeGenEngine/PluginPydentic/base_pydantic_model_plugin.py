#!/usr/bin/env python
import copy
import logging
import os
from typing import List, Callable, Dict, Tuple, final
import time
from abc import abstractmethod
from pathlib import PurePath
from enum import auto

# 3rd party imports
import protogen
from fastapi_utils.enums import StrEnum

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int, YAMLConfigurationManager
if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_to_capitalized_camel_case


flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(flux_core_config_yaml_path))


class IdType(StrEnum):
    NO_ID = auto()
    DEFAULT = auto()
    INT_ID = auto()
    STR_ID = auto()


class BasePydanticModelPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        response_field_case_style = None
        if ((enum_type := os.getenv("ENUM_TYPE")) is not None and len(enum_type)) and \
                ((response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None and \
                 len(response_field_case_style)):
            self.enum_type = enum_type
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'ENUM_TYPE' and 'RESPONSE_FIELD_CASE_STYLE' " \
                      f"received as {enum_type} and {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.default_id_field_type: str | None = None
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.query_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.ordered_message_list: List[protogen.Message] = []
        self.enum_type_validator()
        self.proto_file_name: str = ""
        self.proto_package_name: str = ""
        self.model_file_name: str = ""
        self.generic_routes_file_name: str = ""
        self.model_import_file_name: str = ""
        self.reentrant_lock_non_required_msg: List[protogen.Message] = []

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

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if (self.is_option_enabled(field.message, BasePydanticModelPlugin.flux_msg_json_root) or
                        self.is_option_enabled(field.message, BasePydanticModelPlugin.flux_msg_json_root_time_series)):
                    if field.message not in self.root_message_list:
                        self.root_message_list.append(field.message)
                    # else not required: avoiding repetition
                else:
                    if field.message not in self.non_root_message_list:
                        self.non_root_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.load_dependency_messages_and_enums_in_dicts(field.message)

                if self.is_option_enabled(field.message, BasePydanticModelPlugin.flux_msg_json_query):
                    if field.message not in self.query_message_list:
                        self.query_message_list.append(field.message)
                    # else not required: avoiding repetition

            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message],
                                                 avoid_non_roots: bool | None = None):
        for message in message_list:
            if ((is_json_root := self.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root)) or
                    self.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root_time_series)):
                if is_json_root:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, BasePydanticModelPlugin.flux_msg_json_root)
                else:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message,
                                                                 BasePydanticModelPlugin.flux_msg_json_root_time_series)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict.get(
                        BasePydanticModelPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list
                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition
            else:
                if not avoid_non_roots:
                    if message not in self.non_root_message_list:
                        self.non_root_message_list.append(message)
                    # else not required: avoiding repetition

            if self.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_query):
                if message not in self.query_message_list:
                    self.query_message_list.append(message)
                # else not required: avoiding repetition

            self.load_dependency_messages_and_enums_in_dicts(message)

    def sort_message_order(self):
        combined_message_list = list(set(self.root_message_list + self.non_root_message_list + self.query_message_list))

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

    @abstractmethod
    def _handle_field_cardinality(self, field: protogen.Field) -> str:
        raise NotImplementedError

    @abstractmethod
    def handle_field_output(self, field) -> str:
        raise NotImplementedError

    def handle_enum_output(self, enum: protogen.Enum, enum_type: str) -> str:
        output_str = ""

        match enum_type:
            case "int_enum":
                output_str += f"class {enum.proto.name}(IntEnum):\n"
                for index, value in enumerate(enum.values):
                    output_str += ' ' * 4 + f"{value.proto.name} = {index + 1}\n"
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

    def _underlying_handle_none_default_fields(self, message: protogen.Message, has_id_field: bool) -> str:
        output_str = ""
        if message in self.root_message_list:
            if not has_id_field:
                output_str += f"    {BasePydanticModelPlugin.default_id_field_name}: " \
                              f"{BasePydanticModelPlugin.default_id_type_var_name} | None = " \
                              f"Field(alias='_id')\n"
            # else not required: if id field is present already then will be handled in next for loop

        for field in message.fields:
            if field.proto.name == BasePydanticModelPlugin.default_id_field_name:
                if message in self.root_message_list:
                    output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = " \
                                  f"Field(alias='_id')\n"
                continue
            # else not required: If message is not root type then avoiding id field in optional version so that
            # it's id can be generated if not provided inside root message
            if field.message is not None:
                field_type = f"{field.message.proto.name}Optional"
            else:
                field_type = self.proto_to_py_datatype(field)
            if field.cardinality.name.lower() == "repeated":
                output_str += f"    {field.proto.name}: List[{field_type}] | None = None\n"
            else:
                output_str += f"    {field.proto.name}: {field_type} | None = None\n"

        return output_str

    def _add_config_class(self) -> str:
        output_str = "    class Config:\n"
        output_str += "        allow_population_by_field_name = True\n"
        return output_str

    def handle_message_all_optional_field(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}Optional({message_name}):\n"
        has_id_field = BasePydanticModelPlugin.default_id_field_name in [field.proto.name for field in message.fields]

        output_str += self._underlying_handle_none_default_fields(message, has_id_field)
        if has_id_field:
            output_str += "\n"
            output_str += self._add_config_class()
        output_str += "\n\n"
        return output_str

    def handle_dummy_message_gen(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}BaseModel(BaseModel):\n"
        has_id_field = BasePydanticModelPlugin.default_id_field_name in [field.proto.name for field in message.fields]
        output_str += self._underlying_handle_none_default_fields(message, has_id_field)
        output_str += "\n"
        output_str += self._add_config_class()
        output_str += "\n"
        output_str += self._add_datetime_validator(message)
        output_str += "\n"
        return output_str

    def _handle_unique_id_required_fields(self, message: protogen.Message, auto_gen_id_type: IdType) -> str:
        if auto_gen_id_type == IdType.INT_ID:
            output_str = "    _max_id_val: ClassVar[int | None] = None\n"
            output_str += "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += f'    id: int = Field(default_factory=(lambda: {message.proto.name}.next_id()), ' \
                          f'description="Server generated unique Id", alias="_id")\n'
        elif auto_gen_id_type == IdType.STR_ID:
            output_str = "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += f'    id: str = Field(default_factory=(lambda: {message.proto.name}.next_id()), ' \
                          f'description="Server generated unique Id", alias="_id")\n'
        else:
            output_str = ""

        return output_str

    def _handle_ws_connection_manager_data_members_override(self, message: protogen.Message) -> str:
        output_str = "    read_ws_path_ws_connection_manager: " \
                     "ClassVar[PathWSConnectionManager] = PathWSConnectionManager()\n"
        if BasePydanticModelPlugin.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root):
            options_value_dict = \
                self.get_complex_option_value_from_proto(message,
                                                         BasePydanticModelPlugin.flux_msg_json_root)
        else:
            options_value_dict = \
                self.get_complex_option_value_from_proto(message,
                                                         BasePydanticModelPlugin.flux_msg_json_root_time_series)
        if BasePydanticModelPlugin.flux_json_root_read_websocket_field in options_value_dict:
            output_str += "    read_ws_path_with_id_ws_connection_manager: " \
                          "ClassVar[PathWithIdWSConnectionManager] = PathWithIdWSConnectionManager()\n"
        # else not required: Avoid if websocket field in json root option not present
        return output_str

    @abstractmethod
    def _handle_pydantic_class_declaration(self, message: protogen.Message) -> Tuple[str, bool]:
        raise NotImplementedError

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

    def _handle_reentrant_lock(self, message: protogen.Message) -> str:
        # taking first obj since json root is of non-repeated option
        if message in self.root_message_list and message not in self.reentrant_lock_non_required_msg:
            return "    reentrant_lock: ClassVar[AsyncRLock] = AsyncRLock()\n"
        else:
            return ""

    def _handle_cache_n_ws_connection_manager_data_members_override(self, message: protogen.Message, is_msg_root: bool):
        output_str = ""
        if is_msg_root:
            for field in message.fields:
                if BasePydanticModelPlugin.default_id_field_name == field.proto.name:
                    output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[{self.proto_to_py_datatype(field)}, " \
                                  f"'{message.proto.name}']] = " + "{}\n"
                    break
                # else not required: If no field is id override then handling default id type in else of for loop
            else:
                output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[{BasePydanticModelPlugin.default_id_type_var_name}, " \
                              f"'{message.proto.name}']] = " + "{}\n"
            output_str += self._handle_ws_connection_manager_data_members_override(message)
        # else not required: Avoid cache override if message is not root
        return output_str

    def _add_datetime_validator(self, message: protogen.Message) -> str:
        output_str = ""
        for field in message.fields:
            if self.is_option_enabled(field, BasePydanticModelPlugin.flux_fld_date_time_format):
                output_str += "    @validator('date', pre=True)\n"
                output_str += "    def time_validate(cls, v):\n"
                date_time_format = \
                    self.get_simple_option_value_from_proto(field,
                                                            BasePydanticModelPlugin.flux_fld_date_time_format)
                output_str += f"        return validate_pendulum_datetime(v, {date_time_format})\n"
                break
            # else not required: if date_time option is not set to any field of message then
            # avoiding datetime validation
        return output_str

    def handle_projection_models_output(self, message: protogen.Message):
        output_str = ""
        if BasePydanticModelPlugin.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root_time_series):
            for field in message.fields:
                if BasePydanticModelPlugin.is_option_enabled(field, BasePydanticModelPlugin.flux_fld_projections):
                    break
            else:
                # If no field is found having projection enabled
                return output_str

            for field in message.fields:
                if self.is_bool_option_enabled(field, BasePydanticModelPlugin.flux_fld_val_time_field):
                    time_field_name = field.proto.name
                    break
            else:
                err_str = (f"Could not find any time field in {message.proto.name} message having "
                           f"{BasePydanticModelPlugin.flux_msg_json_root_time_series} option")
                logging.exception(err_str)
                raise Exception(err_str)

            for field in message.fields:
                if self.is_bool_option_enabled(field, BasePydanticModelPlugin.flux_fld_val_meta_field):
                    meta_field_name = field.proto.name
                    meta_field = field
                    meta_field_type = self.proto_to_py_datatype(field)
                    break
            else:
                err_str = (f"Could not find any time field in {message.proto.name} message having "
                           f"{BasePydanticModelPlugin.flux_msg_json_root_time_series} option")
                logging.exception(err_str)
                raise Exception(err_str)

            projection_val_to_fields_dict = BaseProtoPlugin.get_projection_option_value_to_fields(message)

            for projection_option_val, field_names in projection_val_to_fields_dict.items():
                field_name_list: List[str] = []
                for field_name in field_names:
                    if "." in field_name:
                        field_name_list.append("_".join(field_name.split(".")))
                    else:
                        field_name_list.append(field_name)
                field_names_str = "_n_".join(field_name_list)
                field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)
                output_str += f"class {message.proto.name}ProjectionFor{field_names_str_camel_cased}(BaseModel):\n"
                output_str += " " * 4 + f"{time_field_name}: pendulum.DateTime\n"

                field_name_to_type_dict: Dict = {}
                for field_name in field_names:
                    if "." in field_name:
                        field_type = self.get_nested_field_proto_to_py_datatype(field, field_name)
                        field_name_to_type_dict[field_name] = field_type
                    else:
                        for field in message.fields:
                            if field.proto.name == field_name:
                                field_type = self.proto_to_py_datatype(field)
                                field_name_to_type_dict[field_name] = field_type

                has_nested_field = False
                for field_name in field_names:
                    field_type = field_name_to_type_dict.get(field_name)
                    if field_type is None:
                        err_str = ("Could not find type for field_name from field_name_to_type_dict, "
                                   "probably bug in field_name_to_type_dict generation/population")
                        logging.exception(err_str)
                        raise Exception(err_str)

                    if "." in field_name:
                        has_nested_field = True
                        output_str += " "*4 + f"{field_name.split('.')[0]}: {field_type}\n"
                    else:
                        output_str += " "*4 + f"{field_name}: {field_type}\n"

                if has_nested_field:
                    output_str += "\n"
                    output_str += " " * 4 + f"class Settings:\n"
                    projection_dict = {}
                    for index, field_name in enumerate(field_names):
                        if "." in field_name:
                            projection_dict[field_name.split('.')[0]] = f"${field_name}"
                        else:
                            projection_dict[field_name] = index + 1
                    output_str += " "*8 + f"projection = {projection_dict}\n"
                output_str += "\n\n"

                # container class for projection model
                output_str += (f"class {message.proto.name}ProjectionContainerFor"
                               f"{field_names_str_camel_cased}(BaseModel):\n")
                output_str += f"    {meta_field_name}: {meta_field_type}\n"
                output_str += (f"    projection_models: List[{message.proto.name}ProjectionFor"
                               f"{field_names_str_camel_cased}]\n\n\n")

        return output_str

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message,
                                                           auto_gen_id_type: IdType) -> str:
        output_str = ""
        # Making class able to be populated with field name
        if auto_gen_id_type not in ["NO_ID", "DEFAULT"]:
            output_str += "\n"
            output_str += self._add_config_class()
        datetime_validator_str = self._add_datetime_validator(message)
        if datetime_validator_str:
            output_str += "\n"
            output_str += datetime_validator_str

        if self.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root_time_series):
            option_value_dict = (
                self.get_complex_option_value_from_proto(message, BasePydanticModelPlugin.flux_msg_json_root_time_series))
            time_series_version = option_value_dict.get(BasePydanticModelPlugin.flux_json_root_ts_mongo_version_field)
            if time_series_version != 5.0:
                err_str = (f"Time Series is supported with mongo version 5.0 only, received version: "
                           f"{time_series_version} in {BasePydanticModelPlugin.flux_msg_json_root_time_series} "
                           f"option for message {message.proto.name}")
                logging.exception(err_str)
                raise Exception(err_str)

            # getting time_field
            for field in message.fields:
                if BasePydanticModelPlugin.is_option_enabled(field, BasePydanticModelPlugin.flux_fld_val_time_field):
                    time_field = field.proto.name
                    break
            else:
                err_str = (f"Couldn't find any field with {BasePydanticModelPlugin.flux_fld_val_time_field} option "
                           f"set for message {message.proto.name} having "
                           f"{BasePydanticModelPlugin.flux_msg_json_root_time_series} option")
                logging.exception(err_str)
                raise Exception(err_str)

            # getting meta_field
            meta_field: str | None = None
            for field in message.fields:
                if BasePydanticModelPlugin.is_option_enabled(field,
                                                             BasePydanticModelPlugin.flux_fld_val_meta_field):
                    meta_field = field.proto.name
                    break

            granularity = option_value_dict.get(BasePydanticModelPlugin.flux_json_root_ts_granularity_field)
            match granularity:
                case "Sec":
                    granularity_str = "Granularity.seconds"
                case "Min":
                    granularity_str = "Granularity.minutes"
                case "Hrs":
                    granularity_str = "Granularity.hours"
                case other:
                    err_str = (f"Unsupported granularity type: {other} in TimeSeries option value in "
                               f"message {message.proto.name}")
                    logging.exception(err_str)
                    raise Exception(err_str)
            expire_after_sec = option_value_dict.get(BasePydanticModelPlugin.flux_json_root_ts_expire_after_sec_field)

            output_str += "\n"
            output_str += "    class Settings:\n"
            output_str += "        timeseries = TimeSeriesConfig(\n"
            output_str += f'            time_field="{time_field}"'
            if meta_field:
                output_str += ",\n"
                output_str += f'            meta_field="{meta_field}"'
            if granularity:
                output_str += ",\n"
                output_str += f'            granularity={granularity_str}'
            if expire_after_sec:
                output_str += ",\n"
                output_str += f'            expire_after_seconds={expire_after_sec}\n'
            output_str += '        )\n'

        output_str += "\n\n"

        # Adding other versions for root pydantic class
        output_str += self.handle_message_all_optional_field(message)
        if message in self.root_message_list+list(self.query_message_list):
            output_str += self.handle_dummy_message_gen(message)
        # If message is not root then no need to add message with optional fields

        # handling projections
        output_str += self.handle_projection_models_output(message)

        return output_str

    @abstractmethod
    def handle_message_output(self, message: protogen.Message) -> str:
        raise NotImplementedError

    @abstractmethod
    def handle_imports(self) -> str:
        raise NotImplementedError

    def handle_pydantic_class_gen(self) -> str:
        output_str = self.handle_imports()
        output_str += f"{BasePydanticModelPlugin.default_id_type_var_name} = {self.default_id_field_type}\n"
        output_str += f'{BasePydanticModelPlugin.proto_package_var_name} = "{self.proto_package_name}"\n\n'
        for enum in self.enum_list:
            output_str += self.handle_enum_output(enum, self.enum_type)
        for message in self.ordered_message_list:
            output_str += self.handle_message_output(message)

        # adding class to be used by max if query for models having int type of id
        output_str += f"class MaxId(BaseModel):\n"
        output_str += f"    max_id_val: int\n\n"

        return output_str

    def _import_current_models(self) -> List[str]:
        import_statements: List[str] = []
        model_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.model_file_name)
        import_statements.append(f"            from {model_file_path} import *\n")
        generic_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", self.generic_routes_file_name)
        import_statements.append(f"            from {generic_routes_file_path} import *\n")
        return import_statements

    def handle_model_import_file_gen(self) -> str:
        if (output_dir_path := os.getenv("PLUGIN_OUTPUT_DIR")) is not None and len(output_dir_path):
            model_import_file_name = self.model_import_file_name + ".py"
            model_import_file_path = PurePath(output_dir_path) / model_import_file_name
            current_import_statements = self._import_current_models()
            if (db_type_env_name := os.getenv("DBType")) is None or len(db_type_env_name) == 0:
                err_str = f"env var DBType received as {db_type_env_name}"
                logging.exception(err_str)
                raise Exception(err_str)
            if not os.path.exists(model_import_file_path):
                output_str = "import logging\n"
                output_str += "import os\n\n"
                output_str += 'if (db_type := os.getenv("DBType")) is None or len(db_type) == 0:\n'
                output_str += '    err_str = f"env var DBType must not be {db_type}"\n'
                output_str += '    logging.exception(err_str)\n'
                output_str += '    raise Exception(err_str)\n'
                output_str += 'else:\n'
                output_str += '    match db_type.lower():\n'
                output_str += f'        case "{db_type_env_name}":\n'
                for import_statement in current_import_statements:
                    output_str += import_statement
                output_str += f'        case other:\n'
                output_str += '            err_str = f"unsupported db type {db_type}"\n'
                output_str += f'            logging.exception(err_str)\n'
                output_str += f'            raise Exception(err_str)\n'
                return output_str
            else:
                with open(model_import_file_path) as import_file:
                    imports_file_content: List[str] = import_file.readlines()
                    imports_file_content_copy: List[str] = copy.deepcopy(imports_file_content)
                    match_str_index = imports_file_content.index("    match db_type.lower():\n")

                    # checking if already imported
                    for content in imports_file_content[match_str_index:]:
                        if "case" in content and db_type_env_name in content:
                            # getting ending import line for current db_type_env_name
                            for line in imports_file_content[imports_file_content.index(content)+1:]:
                                if "case" in line:
                                    next_db_type_imports_index = imports_file_content.index(line)
                                    break
                            counter = 0
                            for index in range(imports_file_content.index(content), next_db_type_imports_index):
                                # if current db_type already exists in match statement then removing old import
                                del imports_file_content_copy[index-counter]
                                counter += 1
                            break
                        # else not required: if current db_type already not in match statement then no need
                        # to remove it
                    imports_file_content_copy.insert(match_str_index+1, f'        case "{db_type_env_name}":\n')
                    for index, import_statement in enumerate(current_import_statements):
                        imports_file_content_copy.insert(match_str_index+1+(index+1), import_statement)

                return "".join(imports_file_content_copy)
        else:
            err_str = f"Env var 'PLUGIN_OUTPUT_DIR' received as {output_dir_path}"
            logging.exception(err_str)
            raise Exception(err_str)

    def assign_required_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_package_name = str(file.proto.package)
        self.model_import_file_name = f'{self.proto_file_name}_model_imports'

    def output_file_generate_handler(self, file: protogen.File):
        self.assign_required_data_members(file)
        self.load_root_and_non_root_messages_in_dicts(file.messages)

        core_or_util_files = flux_core_config_yaml_dict.get("core_or_util_files")
        if core_or_util_files is not None:
            for dependency_file in file.dependencies:
                if dependency_file.proto.name in core_or_util_files:
                    self.load_root_and_non_root_messages_in_dicts(dependency_file.messages, avoid_non_roots=True)
                # else not required: if dependency file name not in core_or_util_files
                # config list, avoid messages from it
        # else not required: core_or_util_files key is not in yaml dict config

        self.sort_message_order()

        output_dict = {
            # Adding pydantic model file
            self.model_file_name + ".py": self.handle_pydantic_class_gen(),

            # Adding model import file
            self.model_import_file_name + ".py": self.handle_model_import_file_gen()
        }

        return output_dict
