import sys
import os
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "json_schema_convert_plugin.py"
    env_var_dict["AUTOCOMPLETE_FILE_PATH"] = str(PurePath(__file__).parent.parent / "misc" / "autocomplete.json")
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "PluginJSONSchema", env_var_dict)

    data_dir = code_gen_engine_env_manager.project_dir / "data"
    config_file_path = data_dir / "config.yaml"
    config_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
    combine_project_names = config_dict.get("multi_project_plugin")

    if combine_project_names is not None:
        project_dir_list = [str(code_gen_engine_env_manager.project_dir)]
        for project_name in combine_project_names:
            combine_project_dir = os.path.abspath(code_gen_engine_env_manager.project_dir / ".." / project_name)
            project_dir_list.append(combine_project_dir)
        plugin_execute_script = PluginExecuteScript(project_dir_list, "service.proto")
    else:
        plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()
