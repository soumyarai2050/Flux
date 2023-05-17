import logging
import os
from typing import List


class Execute:

    def __init__(self):
        pass

    @staticmethod
    def compile_proto_file(proto_file_paths_list: List[str], proto_import_path_list: List[str],
                           out_dir: str = ".") -> bool:
        """
        Args:
            proto_file_paths_list: [List[str]]
                List of paths of proto files to be compiled

            proto_import_path_list: List[str]
                List of path of directories containing proto model files

            out_dir: [optional] Output Directory path.
                Outputs in script's directory as default.

        Returns:
            Bool for success

        """

        if os.path.exists(out_dir):
            try:
                proto_path_str = ""
                for proto_import_path in proto_import_path_list:
                    # Avoiding extra space after last proto_path in proto_path_str
                    if proto_import_path != proto_import_path_list[-1]:
                        proto_path_str += f"--proto_path={proto_import_path} "
                    else:
                        proto_path_str += f"--proto_path={proto_import_path}"

                proto_files_str = " ".join(proto_file_paths_list)

                # executing cmd for python output
                protoc_cmd = f"protoc {proto_path_str} --python_out={out_dir} {proto_files_str}"
                os.system(protoc_cmd)
                return True
            except Exception as e:
                err_str = f"{e}"
                logging.exception(err_str)
                return False
        else:
            return False

    @staticmethod
    def run_plugin_proto(proto_file_paths_list: List[str], proto_import_path_list: List[str], plugin_path: str,
                         out_dir: str | None = ".") -> bool:
        """
        Args:
            proto_file_paths_list: [List[str]]
                List of paths of proto files to be compiled

            proto_import_path_list: List[str] List of path of directories containing proto model files

            plugin_path: [str] Plugin file path.

            out_dir: [optional] Output Directory path.
                Outputs in script's directory as default.

        Returns:
            Bool for success

        """

        if os.path.exists(out_dir):
            try:
                for proto_file_path in proto_file_paths_list:
                    proto_path_str = ""
                    for proto_import_path in proto_import_path_list:
                        # Avoiding extra space after last proto_path in proto_path_str
                        if proto_import_path != proto_import_path_list[-1]:
                            proto_path_str += f"--proto_path={proto_import_path} "
                        else:
                            proto_path_str += f"--proto_path={proto_import_path}"

                    protoc_cmd = f"protoc {proto_path_str} --plugin=protoc-gen-plugin={plugin_path} --plugin_out={out_dir} {proto_file_path}"
                    os.system(protoc_cmd)
                return True
            except Exception as e:
                err_str = f"{e}"
                logging.exception(err_str)
                return False
        else:
            return False

    @staticmethod
    def make_plugin_executable(plugin_path: str):
        cmd = f"chmod +x {plugin_path}"
        os.system(cmd)
