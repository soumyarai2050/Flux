#!/usr/bin/env python
import logging
from typing import Tuple

# third party modules
import protogen

# project imports
from Flux.PyCodeGenEngine.PluginPydentic.base_pydantic_model_plugin import BasePydanticModelPlugin, main


class PydanticModelPlugin(BasePydanticModelPlugin):

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
        if leading_comments := field.location.leading_comments:
            comments = ", ".join(leading_comments.split("\n"))
            output_str += f' = Field(description="{comments}")\n'
        else:
            output_str += "\n"
        return output_str

    def _handle_pydantic_class_declaration(self, message: protogen.Message) -> Tuple[str, bool]:
        is_msg_root = False
        if self.response_field_case_style.lower() == "snake":
            if message in self.root_message_list:
                is_msg_root = True
                output_str = f"class {message.proto.name}(BareBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(BaseModel):\n"
        elif self.response_field_case_style.lower() == "camel":
            if message in self.root_message_list:
                is_msg_root = True
                output_str = f"class {message.proto.name}(BareCamelBaseModel):\n"
            else:
                output_str = f"class {message.proto.name}(CamelCacheBaseModel):\n"
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str, is_msg_root

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

    def handle_message_output(self, message: protogen.Message) -> str:
        output_str, is_msg_root = self._handle_pydantic_class_declaration(message)

        # Adding docstring if message lvl comment available
        output_str += self._handle_class_docstring(message)

        if is_msg_root:
            output_str += self._handle_ws_connection_manager_data_members_override(message)

        # handling remaining fields
        for field in message.fields:
            output_str += ' '*4 + self.handle_field_output(field)

        output_str += "\n\n"

        if is_msg_root:
            output_str += self.handle_message_all_optional_field(message)
            output_str += self.handle_dummy_message_gen(message)
        # If message is not root then no need to add message with optional fields

        return output_str

    def handle_imports(self) -> str:
        output_str = "from pydantic import Field, BaseModel, field_validator\n"
        output_str += "import pendulum\n"
        output_str += "from typing import Dict, List, ClassVar, Any\n"
        output_str += "from threading import Lock, RLock\n"
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

        if self.response_field_case_style.lower() == "snake":
            output_str += f"from FluxPythonUtils.scripts.model_base_utils import BareBaseModel\n"
        elif self.response_field_case_style.lower() == "camel":
            output_str += (f"from FluxPythonUtils.scripts.model_base_utils import BareCamelBaseModel, "
                           f"CamelCacheBaseModel\n")
        else:
            err_str = f"{self.response_field_case_style} is not supported response type"
            logging.exception(err_str)
            raise Exception(err_str)
        generic_utils_import_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_utils")
        output_str += f"from {generic_utils_import_path} import validate_pendulum_datetime\n"
        output_str += "\n\n\n"
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        super().assign_required_data_members(file)
        self.model_file_name = f'{self.proto_file_name}_bare_pydantic_model'


if __name__ == "__main__":
    main(PydanticModelPlugin)