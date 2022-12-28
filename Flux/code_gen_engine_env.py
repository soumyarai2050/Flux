import os
import sys
import threading
from pathlib import PurePath
from typing import Optional, List, Dict


class CodeGenEngineEnvManager:
    get_instance_mutex: threading.Lock = threading.Lock()
    code_gen_engine_env_manager: Optional['CodeGenEngineEnvManager'] = None

    default_gen_env_var_dict = {
        "ENUM_TYPE": "str_enum",  # Supported types: "str_enum", "int_enum"
        "OUTPUT_FILE_NAME_SUFFIX": "",
        "PLUGIN_FILE_NAME": "",
        "INSERTION_IMPORT_FILE_NAME": "insertion_imports.py",
        "PB2_IMPORT_GENERATOR_PATH": "",
        "RESPONSE_FIELD_CASE_STYLE": "snake",  # snake or camel supported
        "DEBUG_SLEEP_TIME": "0",
        "HOST": "127.0.0.1",
        "PORT": "8080",
        "MONGO_SERVER": "mongodb://localhost:27017",
        "LOG_LEVEL": "debug"
    }

    def __init__(self):
        self.code_gen_root: PurePath = PurePath(__file__).parent
        self.code_gen_projects_path: PurePath = self.code_gen_root / "CodeGenProjects"
        self.cpp_code_gen_engine_path: PurePath = self.code_gen_root / "CppCodeGenEngine"
        self.cpp_code_gen_core_path: PurePath = self.cpp_code_gen_engine_path / "FluxCodeGenCore"
        self.py_code_gen_engine_path: PurePath = self.code_gen_root / "PyCodeGenEngine"
        self.py_code_gen_core_path: PurePath = self.py_code_gen_engine_path / "FluxCodeGenCore"
        self.output_dir: PurePath = self.code_gen_projects_path
        self.project_dir: PurePath | None = None
        self.config_path_with_file_name: PurePath | None = None
        self.plugin_dir: PurePath | None = None
        self.python_path: str = os.getenv("PYTHONPATH") if os.getenv("PYTHONPATH") is not None else ""

        if self.code_gen_root.name != "Flux":
            raise Exception(f"Code Gen Env Constraint failed! Unable to proceed. "
                            f"Expected CodeGenEngineEnvManager class defined in Flux dir, "
                            f"found in: {str(self.code_gen_root)}")
        else:
            os.environ["PROJECT_ROOT"] = str(self.code_gen_root.parent)
            os.environ["FLUX_CODE_GEN_ENGINE_PATH"] = str(self.code_gen_root)
            os.environ["CODE_GEN_PROJECTS_PATH"] = str(self.code_gen_projects_path)
            os.environ["CPP_CODE_GEN_ENGINE_PATH"] = str(self.cpp_code_gen_engine_path)
            os.environ["CPP_CODE_GEN_CORE_PATH"] = str(self.cpp_code_gen_core_path)
            os.environ["PY_CODE_GEN_ENGINE_PATH"] = str(self.py_code_gen_engine_path)
            os.environ["PY_CODE_GEN_CORE_PATH"] = str(self.py_code_gen_core_path)

    def init_env_and_update_sys_path(self, project_name: str, config_file_name: str, plugin_name: str,
                                     custom_env_dict: Dict[str, str] | None = None):
        """
        parameters:
        -----------
        project_name: str: Name of project directory
        config_file_name: str: Name of config file
        plugin_name: str: Name of plugin directory
        custom_env_dict: Dict[str, str] | Optional: Dictionary to be used to set custom required env variables
        """

        self.project_dir = self.code_gen_projects_path / project_name
        os.environ["PROJECT_DIR"] = str(self.project_dir)

        self.config_path_with_file_name = self.project_dir / "misc" / config_file_name
        os.environ["CONFIG_PATH"] = str(self.config_path_with_file_name)

        self.plugin_dir = self.py_code_gen_engine_path / plugin_name
        os.environ["PLUGIN_DIR"] = str(self.plugin_dir)

        # update output dir to be within project output dir
        self.output_dir = self.project_dir / "generated"
        os.environ["OUTPUT_DIR"] = str(self.output_dir)

        # Add required path to sys.path & export them
        sys.path.append(str(self.py_code_gen_core_path))
        sys.path.append(str(self.output_dir))
        sys.path.append(str(self.plugin_dir))
        sys.path.append(str(self.code_gen_root.parent))

        # prepare & export PYTHONPATH
        self.python_path += ":" + str(self.py_code_gen_core_path) + ":" + str(self.output_dir) + ":" + \
                            str(self.plugin_dir / "PluginFastApi") + ":" + str(self.code_gen_root.parent)
        os.environ["PYTHONPATH"] = str(self.python_path)

        # Setting user provided env variables
        if custom_env_dict is not None:
            for env_name, env_path in custom_env_dict.items():
                os.environ[env_name] = env_path
        # else not required: Avoiding env set process if custom_env_dict is None

    @staticmethod
    def execute_python_script(file_path: str | PurePath, params: List[str] | None = None):
        if params is not None:
            params_str = " ".join(params)
            return os.system(f'python3 {file_path} {params_str}')
        else:
            return os.system(f'python3 {file_path}')

    @staticmethod
    def execute_shell_command(shell_cmd: str):
        return os.system(f'{shell_cmd }')

    @classmethod
    def get_instance(cls) -> 'CodeGenEngineEnvManager':
        with cls.get_instance_mutex:
            if cls.code_gen_engine_env_manager is None:
                cls.code_gen_engine_env_manager = CodeGenEngineEnvManager()
                return cls.code_gen_engine_env_manager
            else:
                #  Does exist - return cached
                return cls.code_gen_engine_env_manager
