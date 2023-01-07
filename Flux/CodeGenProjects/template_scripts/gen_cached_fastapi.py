import sys
from pathlib import PurePath
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["OUTPUT_FILE_NAME_SUFFIX"] = "cache_fastapi.py"
    env_var_dict["PLUGIN_FILE_NAME"] = "cache_fastapi_plugin.py"

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginFastApi", env_var_dict)

    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()
