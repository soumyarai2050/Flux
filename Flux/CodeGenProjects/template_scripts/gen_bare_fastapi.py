import sys
import os
from shutil import copy
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "bare_fastapi_plugin.py"
    env_var_dict["ModelType"] = "beanie"

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginFastApi", env_var_dict)

    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    generated_dir_path = os.getenv("OUTPUT_DIR")
    project_dir_path = os.getenv("PROJECT_DIR")
    for file_name in os.listdir(generated_dir_path):
        if file_name.startswith("dummy") and "callback_override" in file_name:
            file_path = PurePath(generated_dir_path) / file_name
            des_file_path = PurePath(project_dir_path) / "app" / file_name.removeprefix("dummy_")
            if not os.path.isfile(des_file_path):
                copy(file_path, des_file_path)
            # else not required: If file exists then avoiding override to that file to prevent code edition
        # else not required: if no file name starts with dummy then no copy operation is done
