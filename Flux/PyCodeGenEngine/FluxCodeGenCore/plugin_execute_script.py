import logging
from typing import List
from Flux.PyCodeGenEngine.FluxCodeGenCore.execute import Execute
import os


class PluginExecuteScript:
    """
    Script containing pipeline to create output using plugins
    1. Compiles all proto models present in model directory to pb2 files
    2. Adds import of created pb2 file in insertion_imports.py
    3. Runs the plugin to create output file
    4. Removes insertion point comment from the output files
    5. Clears added and used imports in this run from insertion_imports file
    """

    ignore_files_list: List[str] = [
        ".db",
        "__pycache__"
    ]
    igmore_import_string_list: List[str] = [
        "flux_option",
        "insertion_point",
        "ui_core_pb2"
    ]

    def __init__(self, base_dir_path: str):
        self.base_dir_path: str = base_dir_path
        self.current_script_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        plugin_file_name = None
        if (plugin_dir := os.getenv("PLUGIN_DIR")) is not None and \
                (plugin_file_name := os.getenv("PLUGIN_FILE_NAME")) is not None:
            self.plugin_path = \
                os.path.abspath(os.path.join(plugin_dir, plugin_file_name))
        else:
            err_str = f"Env var 'PROJECT_DIR' and 'PLUGIN_FILE_NAME' received as {plugin_dir} and {plugin_file_name}"
            logging.exception(err_str)
            raise Exception(err_str)

    def compile_protoc_models(self, proto_file_path_list: List[str], proto_files_dir_paths_list: List[str],
                              out_dir: str):
        execute_success = Execute.compile_proto_file(proto_file_path_list, proto_files_dir_paths_list, out_dir)

        if execute_success:
            logging.debug(f"Protoc successfully executed Plugin {self.plugin_path}, output at {out_dir}")
        else:
            logging.exception(f"Something went wrong while executing protoc plugin {self.plugin_path}")

    def import_pb2_scripts(self, proto_file_path_list: List[str], proto_files_dir_paths_list: List[str], out_dir: str):
        pb2_import_generator_path = None
        if (plugin_dir := os.getenv("PLUGIN_DIR")) is not None and \
                (pb2_import_generator_path := os.getenv("PB2_IMPORT_GENERATOR_PATH")) is not None:
            pb2_import_generator_path = os.path.join(plugin_dir, pb2_import_generator_path)
        else:
            err_str = f"Env var 'PROJECT_DIR' and 'PLUGIN_FILE_NAME' received as " \
                      f"{plugin_dir} and {pb2_import_generator_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        execute_success = Execute.run_plugin_proto(proto_file_path_list, proto_files_dir_paths_list,
                                                   pb2_import_generator_path, out_dir)

        if execute_success:
            logging.debug(f"Protoc successfully executed Plugin {self.plugin_path}, output at {out_dir}")
        else:
            logging.exception(f"Something went wrong while executing protoc plugin {self.plugin_path}")

    def execute_plugin_cmd(self, proto_file_path_list: List[str], proto_files_dir_paths_list: List[str], out_dir: str):
        execute_success = Execute.run_plugin_proto(proto_file_path_list, proto_files_dir_paths_list,
                                                   self.plugin_path, out_dir)

        if execute_success:
            logging.debug(f"Protoc successfully executed Plugin {self.plugin_path}, output at {out_dir}")
        else:
            logging.exception(f"Something went wrong while executing protoc plugin {self.plugin_path}")

    def remove_insertion_point_from_output(self, out_dir: str):
        for file_name in os.listdir(out_dir):
            file_path = os.path.join(out_dir, file_name)
            if (not file_name.startswith(".")) and \
                    not any(ign_file_name_str in file_name for ign_file_name_str in PluginExecuteScript.ignore_files_list) \
                    and os.path.isfile(file_path):
                with open(file_path) as fl:
                    file_content = fl.readlines()
                for file_line in file_content:
                    if "@@protoc_insertion_point" in file_line:
                        file_content.remove(file_line)
                    # else not required: Avoiding files line without insertion point comment

                with open(file_path, "w") as fl:
                    fl.write("".join(file_content))
            # else not required: Avoiding hidden files

    def clear_used_imports_from_file(self):
        insertion_import_file_name = None
        if (plugin_dir := os.getenv("PLUGIN_DIR")) is not None and \
                (insertion_import_file_name := os.getenv("INSERTION_IMPORT_FILE_NAME")) is not None:
            with open(os.path.join(plugin_dir, insertion_import_file_name)) as fl:
                line_sep_content = fl.readlines()
                remove_line_index = []

                for index, line in enumerate(line_sep_content):
                    if "import" in line and not any(ignore_string in line for ignore_string in
                                                    PluginExecuteScript.igmore_import_string_list):
                        remove_line_index.append(index)
                    # else not required: avoiding if import is of flux_option

            with open(os.path.join(plugin_dir, insertion_import_file_name), "w") as fl:
                fl.write(
                    "".join([line for index, line in enumerate(line_sep_content) if index not in remove_line_index]))
        else:
            err_str = f"Env var 'PROJECT_DIR' and 'INSERTION_IMPORT_FILE_NAME' received as " \
                      f"{plugin_dir} and {insertion_import_file_name}"
            logging.exception(err_str)
            raise Exception(err_str)

    def get_required_param_values(self):
        # List of full paths of proto models in model directory
        all_proto_file_path_list = [os.path.join(self.base_dir_path, "model", proto_file)
                                    for proto_file in os.listdir(os.path.join(self.base_dir_path, "model"))]
        proto_file_path_list = [os.path.join(self.base_dir_path, "model", proto_file)
                                for proto_file in os.listdir(os.path.join(self.base_dir_path, "model"))
                                if "options" not in proto_file]
        if (project_dir := os.getenv("PROJECT_DIR")) is not None:
            out_dir = os.path.join(project_dir, "generated")
        else:
            err_str = "Env var 'PROJECT_DIR' received as None"
            logging.exception(err_str)
            raise Exception(err_str)
        proto_files_dir_paths_list: List[str] = [
            os.path.join(self.base_dir_path, "model"),
            os.path.abspath(os.path.join(self.base_dir_path, "..", ".."))
        ]
        insertion_imports_dir_path = self.current_script_dir_path

        return all_proto_file_path_list, proto_file_path_list, out_dir, proto_files_dir_paths_list, \
               insertion_imports_dir_path

    def execute(self):
        all_proto_file_path_list, proto_file_path_list, out_dir, proto_files_dir_paths_list, \
            insertion_imports_dir_path = self.get_required_param_values()

        # Creating pb2 files of all proto models
        self.compile_protoc_models(all_proto_file_path_list, proto_files_dir_paths_list, out_dir)

        # Adding import of pb2 file in insertion_imports.py
        self.import_pb2_scripts(proto_file_path_list, proto_files_dir_paths_list, insertion_imports_dir_path)

        # Running plugin for insertion of new db schema in script
        self.execute_plugin_cmd(proto_file_path_list, proto_files_dir_paths_list, out_dir)

        # Removing plugin comment from output json files if present
        self.remove_insertion_point_from_output(out_dir)

        # Removing used imports from insertion_imports file
        self.clear_used_imports_from_file()
