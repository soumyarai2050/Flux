#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, Tuple, final
import time
from abc import abstractmethod
from pathlib import PurePath

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class BasePydanticModelPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_output_gen
        ]
        response_field_case_style = None
        if (enum_type := os.getenv("ENUM_TYPE")) is not None and \
                (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None:
            self.enum_type = enum_type
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'ENUM_TYPE' and 'RESPONSE_FIELD_CASE_STYLE' " \
                      f"received as {enum_type} and {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.default_id_field_type: str | None = None
        # Since output file name for this plugin will be created at runtime
        self.output_file_name_suffix: str = ""
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.ordered_message_list: List[protogen.Message] = []
        self.enum_type_validator()
        self.proto_file_name: str = ""
        self.proto_package_name: str = ""
        self.model_file_name: str = ""
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

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                if self.is_bool_option_enabled(field, BasePydanticModelPlugin.flux_fld_val_is_datetime):
                    return "pendulum.DateTime"
                else:
                    return BasePydanticModelPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if BasePydanticModelPlugin.flux_msg_json_root in str(field.message.proto.options):
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
            if BasePydanticModelPlugin.flux_msg_json_root in str(message.proto.options):
                json_root_msg_option_val_dict = \
                    self.get_complex_option_values_as_list_of_dict(message, BasePydanticModelPlugin.flux_msg_json_root)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict[0].get(
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
        if not has_id_field:
            output_str += f"    {BasePydanticModelPlugin.default_id_field_name}: " \
                          f"{BasePydanticModelPlugin.default_id_type_var_name} = " \
                          f"Field(alias='_id')\n"
        # else not required: if id field is present already then will be handled in next for loop

        for field in message.fields:
            if field.proto.name == BasePydanticModelPlugin.default_id_field_name:
                output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = " \
                              f"Field(alias='_id')\n"
            else:
                if field.cardinality.name.lower() == "repeated":
                    output_str += f"    {field.proto.name}: List[{self.proto_to_py_datatype(field)}] | None = None\n"
                else:
                    output_str += f"    {field.proto.name}: {self.proto_to_py_datatype(field)} | None = None\n"
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
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BasePydanticModelPlugin.flux_msg_json_root)
        if options_list_of_dict and \
                BasePydanticModelPlugin.flux_json_root_read_websocket_field in options_list_of_dict[0]:
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
            return "    reentrant_lock: ClassVar[Lock] = RLock()\n"
        else:
            return ""

    def _handle_cache_n_ws_connection_manager_data_members_override(self, message: protogen.Message, is_msg_root: bool):
        output_str = ""
        if is_msg_root:
            for field in message.fields:
                if BasePydanticModelPlugin.default_id_field_name in field.proto.name:
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
            if BasePydanticModelPlugin.flux_fld_date_time_format in str(field.proto.options):
                output_str += "    @validator('date', pre=True)\n"
                output_str += "    def time_validate(cls, v):\n"
                date_time_format = \
                    self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                     BasePydanticModelPlugin.flux_fld_date_time_format)
                output_str += f"        return validate_pendulum_datetime(v, {date_time_format})\n"
                break
            # else not required: if date_time option is not set to any field of message then
            # avoiding datetime validation
        return output_str

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message, auto_gen_id: bool) -> str:
        output_str = ""
        # Making class able to be populated with field name
        if auto_gen_id:
            output_str += "\n"
            output_str += self._add_config_class()
        output_str += "\n"
        output_str += self._add_datetime_validator(message)

        output_str += "\n\n"

        # Adding other versions for root pydantic class
        if message in self.root_message_list:
            output_str += self.handle_message_all_optional_field(message)
            output_str += self.handle_dummy_message_gen(message)
        # If message is not root then no need to add message with optional fields

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

        return output_str

    def _import_current_models(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import {BasePydanticModelPlugin.default_id_type_var_name}, " \
                     f"{BasePydanticModelPlugin.proto_package_var_name}, "
        # importing enums
        for enum in self.enum_list:
            output_str += enum.proto.name + ", "

        for message in self.ordered_message_list:
            output_str += message.proto.name
            if message in self.root_message_list:
                output_str += ", "
                output_str += f"{message.proto.name}Optional"
                output_str += ", "
                output_str += f"{message.proto.name}BaseModel"
            # else not required: if message is not of root type then optional abd basemodel version doesn't exist
            if message != self.ordered_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        return output_str

    def handle_model_import_file_gen(self) -> str:
        if (output_dir_path := os.getenv("OUTPUT_DIR")) is not None:
            model_import_file_name = self.model_import_file_name + ".py"
            model_import_file_path = PurePath(output_dir_path) / model_import_file_name
            current_import_statement = self._import_current_models()
            if (db_type_env_name := os.getenv("DBType")) is None:
                err_str = "env var DBType received as None"
                logging.exception(err_str)
                raise Exception(err_str)
            if not os.path.exists(model_import_file_path):
                output_str = "import logging\n"
                output_str += "import os\n\n"
                output_str += 'if (db_type := os.getenv("DBType")) is None:\n'
                output_str += '    err_str = f"env var DBType must not be None"\n'
                output_str += '    logging.exception(err_str)\n'
                output_str += '    raise Exception(err_str)\n'
                output_str += 'else:\n'
                output_str += '    match db_type.lower():\n'
                output_str += f'        case "{db_type_env_name}":\n'
                output_str += f'            {current_import_statement}\n'
                output_str += f'        case other:\n'
                output_str += '            err_str = f"unsupported db type {db_type}"\n'
                output_str += f'            logging.exception(err_str)\n'
                output_str += f'            raise Exception(err_str)\n'
                return output_str
            else:
                with open(model_import_file_path) as import_file:
                    imports_file_content: List[str] = import_file.readlines()

                    match_str_index = imports_file_content.index("    match db_type.lower():\n")

                    # checking if already imported
                    for content in imports_file_content[match_str_index:]:
                        if "case" in content and db_type_env_name in content:
                            # if current db_type already exists in match statement then removing old import
                            del imports_file_content[imports_file_content.index(content)+2]  # empty space
                            del imports_file_content[imports_file_content.index(content)+1]  # import statement
                            del imports_file_content[imports_file_content.index(content)]    # match case check
                            break
                        # else not required: if current db_type already not in match statement then no need
                        # to remove it
                    imports_file_content.insert(match_str_index+1, f'        case "{db_type_env_name}":\n')
                    imports_file_content.insert(match_str_index+2, f'            {current_import_statement}\n')

                return "".join(imports_file_content)
        else:
            err_str = "Env var 'OUTPUT_DIR' received as None"
            logging.exception(err_str)
            raise Exception(err_str)

    def assign_required_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_package_name = str(file.proto.package)
        self.model_import_file_name = f'{self.proto_file_name}_model_imports'

    @final
    def handle_output_gen(self, file: protogen.File) -> Dict[str, str]:
        self.assign_required_data_members(file)
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.sort_message_order()

        output_dict = {
            # Adding pydantic model file
            self.model_file_name + ".py": self.handle_pydantic_class_gen(),

            # Adding model import file
            self.model_import_file_name + ".py": self.handle_model_import_file_gen()
        }

        return output_dict
