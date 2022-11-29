#!/usr/bin/env python
import os
from Flux.PyCodeGenEngine.PluginDBBinding.base_db_binding_plugin import BaseDbBindingPlugin
from typing import List, Callable


class DbBindingTemplatePlugin(BaseDbBindingPlugin):
    """
    Db Binding plugin, inherits from ``BaseDbBindingPlugin`` and overrides base data-members to be used
    by base class pipeline. Uses Template for output.
    """

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        self.output_file_name_suffix = self.config_yaml["output_file_name_suffix"]
        self.template_file_path = os.path.join(self.base_dir_path, "misc", self.config_yaml["template_file_name"])
        self.insertion_point_key_list: List[str] = [
            "import_pb2",
            "file_comment",
            "class_container_name",
            "msg_comment",
            "db_columns_without_id",
            "db_columns_with_id",
            "create_table_query",
            "insert_query_suffix",
            "insert_query",
            "select_all_query_prefix",
            "select_all_query",
            "get_from_db_row",
            "insert_params",
            "store_in_db",
            "data_members",
            "str_method_return"
        ]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_import_pb2,
            self.handle_file_comment,
            self.handle_class_container_name,
            self.handle_root_msg_comment,
            self.handle_db_columns_without_id,
            self.handle_db_columns_with_id,
            self.handle_create_table_query,
            self.handle_insert_query_suffix,
            self.handle_insert_query,
            self.handle_select_all_query_prefix,
            self.handle_select_all_query,
            self.handle_get_from_db_row,
            self.handle_insert_params,
            self.handle_store_in_db,
            self.handle_data_members,
            self.handle_str_method_return
        ]


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_PATH")
        config_path = os.getenv("CONFIG_PATH")
        proto_to_db_plugin = DbBindingTemplatePlugin(project_dir_path, config_path)
        proto_to_db_plugin.process()

    main()
