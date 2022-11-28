#!/usr/bin/env python
import os
import textwrap
import protogen
from FluxCodeGenEngine.PyCodeGenEngine.PluginDBBinding.base_db_binding_plugin import BaseDbBindingPlugin
from typing import List, Callable
import time


class DbBindingPlugin(BaseDbBindingPlugin):
    """
    Db Binding plugin, inherits from ``BaseDbBindingPlugin`` and overrides base data-members to be used
    by base class pipeline without template file.
    """

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        # overriden data members
        self.output_file_name_suffix = self.config_yaml["output_file_name_suffix"]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.__handle_output_creation
        ]

    def __handle_output_creation(self, file: protogen.File):
        # Todo: Find way to get custom imports
        output_str = f"""from datetime import datetime\nfrom typing import Final

{self.handle_import_pb2(file)}
{self.handle_file_comment(file)}

{self.handle_class_container_name(file)}
{textwrap.indent(self.handle_root_msg_comment(file), "    ")}
{textwrap.indent(self.handle_db_columns_without_id(file), "    ")}
    
{textwrap.indent(self.handle_db_columns_with_id(file), "    ")}
{textwrap.indent(self.handle_create_table_query(file), "    ")}
    
{textwrap.indent(self.handle_insert_query_suffix(file), "    ")}
    
{textwrap.indent(self.handle_insert_query(file), "    ")}
    
{textwrap.indent(self.handle_select_all_query_prefix(file), "    ")}
    
{textwrap.indent(self.handle_select_all_query(file), "    ")}
    
{textwrap.indent(self.handle_get_from_db_row(file), "    ")}
    
{textwrap.indent(self.handle_insert_params(file), "    ")}
    
{textwrap.indent(self.handle_store_in_db(file), "    ")}
    
{textwrap.indent(self.handle_data_members(file), "    ")}
{textwrap.indent(self.handle_str_method_return(file), "    ")}
"""
        return output_str


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_DIR")
        config_path = os.getenv("CONFIG_PATH")
        if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
                isinstance(debug_sleep_time := int(debug_sleep_time), int):
            time.sleep(debug_sleep_time)
        # else not required: Avoid if env var is not set or if value cant be type-cased to int
        db_binding_plugin = DbBindingPlugin(project_dir_path, config_path)
        db_binding_plugin.process()

    main()
