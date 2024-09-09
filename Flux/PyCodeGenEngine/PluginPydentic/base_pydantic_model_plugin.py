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
from fastapi_restful.enums import StrEnum

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int, YAMLConfigurationManager
if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_to_capitalized_camel_case

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = (
    YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path)))
root_core_proto_files: List[str] = []
option_files = root_flux_core_config_yaml_dict.get("options_files")
core_or_util_files = root_flux_core_config_yaml_dict.get("core_or_util_files")
if option_files is not None and option_files:
    root_core_proto_files.extend(option_files)
if core_or_util_files is not None and core_or_util_files:
    root_core_proto_files.extend(core_or_util_files)

project_dir = os.getenv("PROJECT_DIR")
if project_dir is None or not project_dir:
    err_str = f"env var PROJECT_DIR received as {project_dir}"
    logging.exception(err_str)
    raise Exception(err_str)

project_grp_core_proto_files = []
if "ProjectGroup" in project_dir:
    project_group_flux_core_config_yaml_path = PurePath(project_dir).parent.parent / "flux_core.yaml"
    project_group_flux_core_config_yaml_dict = (
        YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
    option_files = project_group_flux_core_config_yaml_dict.get("options_files")
    core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
    if option_files is not None and option_files:
        project_grp_core_proto_files.extend(option_files)
    if core_or_util_files is not None and core_or_util_files:
        project_grp_core_proto_files.extend(core_or_util_files)

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
        self.model_file_suffix: str = ""
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
        message_list.sort(key=lambda message_: message_.proto.name)     # sorting by name

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
                              f"Field(None, alias='_id')\n"
            # else not required: if id field is present already then will be handled in next for loop

        for field in message.fields:
            if field.proto.name == BasePydanticModelPlugin.default_id_field_name:
                if message in self.root_message_list:
                    output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = " \
                                  f"Field(None, alias='_id')\n"
                continue
            # else not required: If message is not root type then avoiding id field in optional version so that
            # it's id can be generated if not provided inside root message

            if field.message is not None:
                if self.is_option_enabled(field.message, BasePydanticModelPlugin.flux_msg_json_root):
                    field_type = f"{field.message.proto.name}BaseModel"
                else:
                    field_type = field.message.proto.name

                if field.cardinality.name.lower() == "repeated":
                    if self.is_option_enabled(field.message, BasePydanticModelPlugin.flux_msg_json_root):
                        output_str += f"    {field.proto.name}: List[{field_type}] | None = None\n"
                    else:
                        output_str += (f"    {field.proto.name}: List[{field.message.proto.name}Optional] | "
                                       f"List[{field_type}] | None = None\n")
                else:
                    if self.is_option_enabled(field.message, BasePydanticModelPlugin.flux_msg_json_root):
                        output_str += f"    {field.proto.name}: {field_type} | None = None\n"
                    else:
                        output_str += (f"    {field.proto.name}: {field.message.proto.name}Optional | "
                                       f"{field_type} | None = None\n")
            else:
                field_type = self.proto_to_py_datatype(field)
                if field.cardinality.name.lower() == "repeated":
                    output_str += f"    {field.proto.name}: List[{field_type}] | None = None\n"
                else:
                    output_str += f"    {field.proto.name}: {field_type} | None = None\n"

        return output_str

    def _add_config_attribute(self) -> str:
        output_str = "    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)\n"
        return output_str

    def handle_message_all_optional_field(self, message: protogen.Message,
                                          datetime_field_list: List[protogen.Field] | None = None) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}Optional({message_name}):\n"
        has_id_field = BasePydanticModelPlugin.default_id_field_name in [field.proto.name for field in message.fields]

        output_str += self._underlying_handle_none_default_fields(message, has_id_field)
        if has_id_field:
            output_str += self._add_config_attribute()
        for dt_field in datetime_field_list:
            datetime_validator_str = self.add_datetime_validator(dt_field)
            if datetime_validator_str:
                output_str += "\n"
                output_str += datetime_validator_str
        output_str += "\n\n"
        return output_str

    def handle_dummy_message_gen(self, message: protogen.Message,
                                 datetime_field_list: List[protogen.Field] | None = None, **kwargs) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}BaseModel(PydanticBaseModel):\n"
        has_id_field = BasePydanticModelPlugin.default_id_field_name in [field.proto.name for field in message.fields]
        output_str += self._underlying_handle_none_default_fields(message, has_id_field)
        output_str += self._add_config_attribute()
        output_str += "\n"
        for dt_field in datetime_field_list:
            datetime_validator_str = self.add_datetime_validator(dt_field)
            if datetime_validator_str:
                output_str += "\n"
                output_str += datetime_validator_str
        output_str += "\n"
        return output_str

    def _handle_unique_id_required_fields(self, message: protogen.Message, auto_gen_id_type: IdType) -> str:
        if auto_gen_id_type == IdType.INT_ID:
            output_str = "    _max_id_val: ClassVar[int | None] = None\n"
            output_str += "    _max_update_id_val: ClassVar[int | None] = None\n"
            output_str += "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += f'    id: int = Field(default_factory=(lambda: {message.proto.name}.next_id()), ' \
                          f'description="Server generated unique Id", alias="_id")\n'
            output_str += (f'    update_id: int = Field(default_factory=(lambda: {message.proto.name}.'
                           f'next_update_id()), description="Server generated unique Update Id")\n')
        elif auto_gen_id_type == IdType.STR_ID:
            output_str = "    _mutex: ClassVar[Lock] = Lock()\n"
            output_str += "    _max_update_id_val: ClassVar[int | None] = None\n"
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
        if BasePydanticModelPlugin.flux_json_root_read_by_id_websocket_field in options_value_dict:
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

                output_str += self._add_config_attribute()
                output_str += "\n"

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

                # List class of container class
                output_str += (f'class {message.proto.name}ProjectionContainerFor'
                               f'{field_names_str_camel_cased}List(RootModel):\n')
                output_str += (f'    root: List[{message.proto.name}ProjectionContainerFor'
                               f'{field_names_str_camel_cased}]\n\n\n')

        return output_str

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message,
                                                           auto_gen_id_type: IdType) -> str:
        output_str = ""
        # Making class able to be populated with field name
        output_str += self._add_config_attribute()

        if self.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root_time_series):
            time_field, meta_field, granularity, expire_after_sec = self.get_time_series_data_from_msg(message)

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
                output_str += f'            expire_after_seconds={expire_after_sec}'
            output_str += "\n"
            output_str += '        )\n'

        index_field_list: List[protogen.Field] = []
        datetime_field_list: List[protogen.Field] = []
        for field in message.fields:
            if self.is_option_enabled(field, BasePydanticModelPlugin.flux_fld_index):
                index_field_list.append(field)
            if self.is_option_enabled(field, BasePydanticModelPlugin.flux_fld_val_is_datetime):
                datetime_field_list.append(field)

        if index_field_list:
            if not self.is_option_enabled(message, BasePydanticModelPlugin.flux_msg_json_root_time_series):
                output_str += "\n"
                output_str += "    class Settings:\n"
            output_str += "        indexes = [\n"
            for fld in index_field_list:
                output_str += f'            "{fld.proto.name}"'
                if fld != index_field_list[-1]:
                    output_str += ',\n'
                else:
                    output_str += "\n"
                    output_str += "        ]\n"

        for dt_field in datetime_field_list:
            datetime_validator_str = self.add_datetime_validator(dt_field)
            if datetime_validator_str:
                output_str += "\n"
                output_str += datetime_validator_str

        output_str += "\n\n"

        # Adding other versions for root pydantic class
        output_str += self.handle_message_all_optional_field(message, datetime_field_list)
        if message in self.root_message_list+list(self.query_message_list):
            output_str += self.handle_dummy_message_gen(message, datetime_field_list)
        # If message is not root then no need to add message with optional fields

        # handling projections
        output_str += self.handle_projection_models_output(message)

        return output_str

    def add_datetime_validator(self, datetime_field: protogen.Field) -> str:
        output_str = ""
        output_str += f"    @field_validator('{datetime_field.proto.name}', mode='before')\n"
        output_str += "    @classmethod\n"
        output_str += f"    def handle_{datetime_field.proto.name}(cls, v):\n"
        date_time_format = None
        if self.is_option_enabled(datetime_field, BasePydanticModelPlugin.flux_fld_date_time_format):
            date_time_format = \
                self.get_simple_option_value_from_proto(datetime_field,
                                                        BasePydanticModelPlugin.flux_fld_date_time_format)
        if date_time_format:
            output_str += f"        return validate_pendulum_datetime(v, {date_time_format})\n"
        else:
            output_str += f"        return validate_pendulum_datetime(v)\n"
        return output_str

    @abstractmethod
    def handle_message_output(self, message: protogen.Message) -> str:
        raise NotImplementedError

    @abstractmethod
    def handle_imports(self) -> str:
        raise NotImplementedError

    def list_model_content(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.root_message_list:
            if message in file.messages:
                output_str += f'class {message.proto.name}BaseModelList(RootModel, ListModelBase):\n'
                output_str += f'    root: List[{message.proto.name}BaseModel]\n\n\n'
        return output_str

    def handle_pydantic_class_gen(self, file: protogen.File, is_main_file: bool | None = None) -> str:
        if is_main_file is None:
            is_main_file = False

        output_str = self.handle_imports()

        if file.dependencies:
            output_str += "# Project imports\n"
            for file_ in file.dependencies:
                if file_.proto.name != "flux_options.proto":
                    if file_.proto.name in root_core_proto_files:
                        gen_model_import_path = (
                            self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                          f"Pydantic.{file_.generated_filename_prefix}_{self.model_file_suffix}"))
                    elif file_.proto.name in project_grp_core_proto_files:
                        project_grp_root_dir = PurePath(project_dir).parent.parent / "Pydantic"
                        gen_model_import_path = (
                            self.import_path_from_path_str(str(project_grp_root_dir),
                                                           f"{file_.generated_filename_prefix}_{self.model_file_suffix}"))
                    else:
                        gen_model_import_path = (
                            self.import_path_from_os_path("PLUGIN_OUTPUT_DIR",
                                                          f"{file_.generated_filename_prefix}_{self.model_file_suffix}"))
                    output_str += f"from {gen_model_import_path} import *\n"
            output_str += "\n\n"

        output_str += f"{BasePydanticModelPlugin.default_id_type_var_name} = {self.default_id_field_type}\n"
        if is_main_file:
            output_str += f'{BasePydanticModelPlugin.proto_package_var_name} = "{self.proto_package_name}"\n\n'

        for enum in file.enums:
            output_str += self.handle_enum_output(enum, self.enum_type)

        for message in self.ordered_message_list:
            if message in file.messages:
                output_str += self.handle_message_output(message)

        output_str += self.list_model_content(file)

        # adding class to be used by query to get max_id of any model
        output_str += self._handle_max_id_model()

        return output_str

    @abstractmethod
    def _handle_max_id_model(self) -> str:
        raise NotImplementedError("Must handle MaxId model use for getting max_id set for any model in query")

    def _import_current_models(self) -> List[str]:
        import_statements: List[str] = []
        model_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.model_file_name)
        import_statements.append(f"            from {model_file_path} import *\n")
        generic_routes_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", self.generic_routes_file_name)
        import_statements.append(f"            from {generic_routes_file_path} import *\n")
        return import_statements

    def handle_model_import_file_gen(self) -> str:
        model_import_file_name = self.model_import_file_name + ".py"
        return self.handle_import_file_gen(model_import_file_name, self._import_current_models)

    def assign_required_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_package_name = str(file.proto.package)
        self.model_import_file_name = f'{self.proto_file_name}_model_imports'

    def get_dependency_protogen_files(self, file: protogen.File,
                                      all_dependency_protogen_file_list: List[protogen.File]) -> None:
        for file_ in file.dependencies:
            if file_.proto.name != "flux_options.proto" and file_ not in all_dependency_protogen_file_list:
                if file_.dependencies:
                    self.get_dependency_protogen_files(file_, all_dependency_protogen_file_list)
                all_dependency_protogen_file_list.append(file_)
                self.load_root_and_non_root_messages_in_dicts(file_.messages)

    def output_file_generate_handler(self, file: protogen.File):
        # time.sleep(10)
        self.assign_required_data_members(file)
        self.load_root_and_non_root_messages_in_dicts(file.messages)

        output_dict = {
            # Adding model import file
            self.model_import_file_name + ".py": self.handle_model_import_file_gen()
        }

        all_dependency_protogen_file_list: List[protogen.File] = []
        self.get_dependency_protogen_files(file, all_dependency_protogen_file_list)
        self.sort_message_order()

        # Adding pydantic model file
        output_dict[self.model_file_name + ".py"] = self.handle_pydantic_class_gen(file, is_main_file=True)
        for file_ in all_dependency_protogen_file_list:
            file_name = f"{file_.generated_filename_prefix}_{self.model_file_suffix}.py"
            output_dict[file_name] = self.handle_pydantic_class_gen(file_)

        return output_dict
