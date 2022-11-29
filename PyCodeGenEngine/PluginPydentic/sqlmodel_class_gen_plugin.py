#!/usr/bin/env python
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginPydentic.pydantic_class_gen_plugin import PydanticClassGenPlugin


class SQLModelClassGenPlugin(PydanticClassGenPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    flux_fld_primary: str = "FluxFldPk"

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.db_file_name: str | None = None

    def handle_field_output(self, field: protogen.Field) -> str:
        field_type = self.proto_to_py_datatype(field)

        match field.cardinality.name.lower():
            case "optional":
                output_str = f"{field.proto.name}: {field_type} | None"
            case "repeated":
                output_str = f"{field.proto.name}: List[{field_type}]"
            case other:
                output_str = f"{field.proto.name}: {field_type}"

        if leading_comments := field.location.leading_comments:
            comments = ", ".join(leading_comments.split("\n"))
            output_str += f' = Field(description="{comments}"'
        # else not required: Avoid if comment is not present

        if is_primary := (SQLModelClassGenPlugin.flux_fld_primary in str(field.proto.options)):
            if leading_comments:
                output_str += f', default=None, primary_key=True'
            else:
                output_str += f' = Field(default=None, primary_key=True)\n'
        # else not required: Avoid if primary option in not set

        if SQLModelClassGenPlugin.flux_fld_index in str(field.proto.options):
            if leading_comments or is_primary:
                output_str += f', index=True)\n'
            else:
                output_str += f' = Field(index=True)\n'
        # else not required: Avoid if index option in not set

        return output_str

    def handle_message_table_output(self, message: protogen.Message) -> str:
        output_str = ""

        if message in self.root_message_list:
            output_str += f"class {message.proto.name}(SQLModel, table=True):\n"
        else:
            output_str += f"class {message.proto.name}(SQLModel):\n"

        # Adding docstring if message lvl comment available
        if leading_comments := message.location.leading_comments:
            output_str += '    """\n'
            comments = ", ".join(leading_comments.split("\n"))
            comments_multiline = [comments[0+i:100+i] for i in range(0, len(comments), 100)]
            for comments_line in comments_multiline:
                output_str += f"        {comments_line}\n"

            output_str += '    """\n\n'

        for field in message.fields:
            output_str += ' '*4 + self.handle_field_output(field)
        output_str += "\n\n"

        return output_str

    def handle_imports(self) -> str:
        output_str = "from sqlmodel import SQLModel, Field\n"
        if self.enum_list:
            if self.enum_type == "int_enum":
                output_str += "from enum import IntEnum\n"
            elif self.enum_type == "str_enum":
                output_str += "from enum import auto\n"
                output_str += "from fastapi_utils.enums import StrEnum\n"
            # else not required: if enum type is not proper then it would be already handled in init
        output_str += "from typing import List\n\n\n"
        return output_str

    def handle_pydantic_class_gen(self, file: protogen.File) -> str:
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.sort_message_order()
        self.db_file_name = f"{str(file.proto.name).split('.')[0]}_db.db"

        output_str = self.handle_imports()

        for enum in self.enum_list:
            output_str += self.handle_enum_output(enum, self.enum_type)

        for message in self.ordered_message_list:
            output_str += self.handle_message_table_output(message)

        return output_str


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_PATH")
        config_path = os.getenv("CONFIG_PATH")
        sqlmodel_class_gen_plugin = SQLModelClassGenPlugin(project_dir_path, config_path)
        sqlmodel_class_gen_plugin.process()

    main()
