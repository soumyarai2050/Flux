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

# Required for accessing custom options from schema
from Flux.PyCodeGenEngine.PluginPydentic import insertion_imports


class BasePydanticModelPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    default_id_type: str = "int"

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
        # Since output file name for this plugin will be created at runtime
        self.output_file_name_suffix: str = ""
        self.root_message_list: List[protogen.Message] = []
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.ordered_message_list: List[protogen.Message] = []
        self.enum_type_validator()
        self.proto_file_name: str = ""
        self.model_file_name: str = ""
        self.model_import_file_name: str = ""

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
                if BasePydanticModelPlugin.flux_fld_val_is_datetime in str(field.proto.options):
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
            option_str = str(message.proto.options)
            if BasePydanticModelPlugin.flux_msg_json_root in str(message.proto.options):
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

    def _underlying_handle_none_default_fields(self, message: protogen.Message, auto_gen_id: bool) -> str:
        output_str = ""
        for field in message.fields:
            if auto_gen_id and field.proto.name == BasePydanticModelPlugin.default_id_field_name:
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

    def handle_message_all_optional_field(self, message: protogen.Message, auto_gen_id: bool) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}Optional({message_name}):\n"
        output_str += self._underlying_handle_none_default_fields(message, auto_gen_id)
        if auto_gen_id:
            output_str += "\n"
            output_str += self._add_config_class()
        output_str += "\n\n"
        return output_str

    def handle_dummy_message_gen(self, message: protogen.Message, auto_gen_id: bool) -> str:
        message_name = message.proto.name
        output_str = f"class {message_name}BaseModel(BaseModel):\n"
        output_str += self._underlying_handle_none_default_fields(message, auto_gen_id)
        if auto_gen_id:
            output_str += "\n"
            output_str += self._add_config_class()
        output_str += "\n\n"
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
            self.get_complex_msg_option_values_as_list_of_dict(message,
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
                output_str += f"    _cache_obj_id_to_obj_dict: ClassVar[Dict[{self.default_id_type}, " \
                              f"'{message.proto.name}']] = " + "{}\n"
            output_str += self._handle_ws_connection_manager_data_members_override(message)
        # else not required: Avoid cache override if message is not root
        return output_str

    def _handle_config_class_and_other_root_class_versions(self, message: protogen.Message, auto_gen_id: bool) -> str:
        output_str = ""
        # Making class able to be populated with field name
        if auto_gen_id:
            output_str += "\n"
            output_str += self._add_config_class()
        output_str += "\n\n"

        # Adding other versions for root pydantic class
        if auto_gen_id:
            output_str += self.handle_message_all_optional_field(message, auto_gen_id)
            output_str += self.handle_dummy_message_gen(message, auto_gen_id)
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
        for enum in self.enum_list:
            output_str += self.handle_enum_output(enum, self.enum_type)
        for message in self.ordered_message_list:
            output_str += self.handle_message_output(message)

        return output_str

    def _import_current_models(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import "
        for message in self.root_message_list:
            output_str += message.proto.name
            output_str += ", "
            output_str += f"{message.proto.name}Optional"
            output_str += ", "
            output_str += f"{message.proto.name}BaseModel"
            if message != self.root_message_list[-1]:
                output_str += ", "
            else:
                output_str += "\n"
        return output_str

    def handle_model_import_file_gen(self) -> str:
        if (output_dir_path := os.getenv("OUTPUT_DIR")) is not None:
            model_import_file_name = self.model_import_file_name + ".py"
            model_import_file_path = PurePath(output_dir_path) / model_import_file_name
            current_import_statement = self._import_current_models()
            if not os.path.exists(model_import_file_path):
                # print(f"###### ----> Not exists {model_import_file_path}")
                return current_import_statement
            else:
                with open(model_import_file_path) as import_file:
                    imports_list: List[str] = import_file.readlines()

                    # Making all imports commented
                    imports_list_commented = [f"# {import_str}" for import_str in imports_list if import_str[0] != "#"]
                    imports_list = []

                    # Removing current import if already present
                    for import_str in imports_list_commented:
                        if f"# {current_import_statement}" != import_str:
                            imports_list.append(import_str)

                    # Adding current import statement
                    imports_list.append(current_import_statement)

                return "".join(imports_list)
        else:
            err_str = "Env var 'OUTPUT_DIR' received as None"
            logging.exception(err_str)
            raise Exception(err_str)

    def assign_required_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
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
