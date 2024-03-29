# standard imports
import logging
import os
from typing import List
from pathlib import PurePath
from enum import auto

# 3rd party imports
from fastapi_restful.enums import StrEnum


class ProtoGenOutputTypes(StrEnum):
    Proto_Gen_Py = auto()
    Proto_Gen_Cc = auto()
    Proto_Gen_Both = auto()


class Execute:

    def __init__(self):
        pass

    @staticmethod
    def compile_proto_file(proto_file_paths_list: List[str], proto_import_path_list: List[str],
                           out_dir: str = ".", output_type: ProtoGenOutputTypes | None = None):
        """
        Args:
            proto_file_paths_list: [List[str]]
                List of paths of proto files to be compiled

            proto_import_path_list: List[str]
                List of path of directories containing proto model files

            out_dir: [optional] Output Directory path.
                Outputs in script's directory as default.

            output_type: [optional] Type of output to be generated, currently supports python and cpp type.
        Returns:
            Bool for success

        """
        if output_type is None:
            output_type = ProtoGenOutputTypes.Proto_Gen_Both

        dir_names = ["ProtoGenPy", "ProtoGenCc"]
        for dir_name in dir_names:
            out_dir_path = PurePath(out_dir) / dir_name
            if not os.path.exists(out_dir_path):
                os.mkdir(out_dir_path)
        try:
            proto_path_str = ""
            for proto_import_path in proto_import_path_list:
                # Avoiding extra space after last proto_path in proto_path_str
                proto_path_str += f"--proto_path={proto_import_path} "
                if proto_import_path != proto_import_path_list[-1]:
                    proto_path_str += " "

            proto_files_str = " ".join(proto_file_paths_list)

            if output_type == ProtoGenOutputTypes.Proto_Gen_Py or output_type == ProtoGenOutputTypes.Proto_Gen_Both:
                # executing cmd for python output
                protoc_cmd = \
                    f"protoc {proto_path_str} --python_out={PurePath(out_dir) / dir_names[0]} {proto_files_str}"
                os.system(protoc_cmd)

            if output_type == ProtoGenOutputTypes.Proto_Gen_Cc or output_type == ProtoGenOutputTypes.Proto_Gen_Both:
                # executing cmd for CPP output
                protoc_cmd = f"protoc {proto_path_str} --cpp_out={PurePath(out_dir) / dir_names[1]} {proto_files_str}"
                os.system(protoc_cmd)

            if output_type == ProtoGenOutputTypes.Proto_Gen_Py or output_type == ProtoGenOutputTypes.Proto_Gen_Both:
                # Adding python generated dir in PYTHONPATH
                python_path_env = python_path if ((python_path := os.getenv("PYTHONPATH")) is not None and
                                                  len(python_path)) else ""
                os.environ["PYTHONPATH"] = python_path_env + ":" + str(PurePath(out_dir) / dir_names[0])

        except Exception as e:
            err_str = f"Exception occurred while compiling proto model files in proto classes: exception: {e}"
            logging.exception(err_str)
            raise Exception(err_str)

    @staticmethod
    def run_plugin_proto(proto_file_paths_list: List[str], proto_import_path_list: List[str], plugin_path: str,
                         out_dir: str | None = ".", run_only_once: bool | None = None) -> bool:
        """
        Args:
            proto_file_paths_list: [List[str]]
                List of paths of proto files to be compiled

            proto_import_path_list: List[str] List of path of directories containing proto model files

            plugin_path: [str] Plugin file path.

            out_dir: [optional] Output Directory path.
                Outputs in script's directory as default.

            run_only_once: [Optional] Flag to indicate to run script only once with all proto models

        Returns:
            Bool for success

        """

        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        try:
            if not run_only_once:
                for proto_file_path in proto_file_paths_list:
                    proto_path_str = ""
                    for proto_import_path in proto_import_path_list:
                        proto_path_str += f"--proto_path={proto_import_path} "

                    protoc_cmd = (f"protoc {proto_path_str}--plugin=protoc-gen-plugin={plugin_path} "
                                  f"--plugin_out={out_dir} {proto_file_path}")
                    os.system(protoc_cmd)
            else:
                proto_file_path_str = " ".join(proto_file_paths_list)
                proto_path_str = ""
                for proto_import_path in proto_import_path_list:
                    # Avoiding extra space after last proto_path in proto_path_str
                    if proto_import_path != proto_import_path_list[-1]:
                        proto_path_str += f"--proto_path={proto_import_path} "
                    else:
                        proto_path_str += f"--proto_path={proto_import_path}"

                protoc_cmd = (f"protoc {proto_path_str} --plugin=protoc-gen-plugin={plugin_path} "
                              f"--plugin_out={out_dir} {proto_file_path_str}")
                os.system(protoc_cmd)
            return True
        except Exception as e:
            err_str = f"Exception occurred while running proto plugins: exception: {e}"
            logging.exception(err_str)
            raise Exception(err_str)

    @staticmethod
    def make_plugin_executable(plugin_path: str):
        cmd = f"chmod +x {plugin_path}"
        os.system(cmd)
