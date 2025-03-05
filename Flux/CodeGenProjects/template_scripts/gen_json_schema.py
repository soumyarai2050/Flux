import sys
import os
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_utils import selective_message_per_project_dict_to_env_var_str


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "json_schema_convert_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "PluginJSONSchema", env_var_dict)

    data_dir = code_gen_engine_env_manager.project_dir / "data"
    config_file_path = data_dir / "config.yaml"
    config_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
    combine_project_names = config_dict.get("multi_project_plugin")

    if combine_project_names is not None:
        project_dir_list = [str(code_gen_engine_env_manager.project_dir)]
        project_name_to_msg_list_dict = {}
        for project_name_ in combine_project_names:
            if isinstance(project_name_, dict):     # when project name is key and selective msg names list is value
                project_name = list(project_name_.keys())[0]
                msg_name_list = list(project_name_.values())[0]
                project_name_to_msg_list_dict[project_name] = msg_name_list
            else:
                project_name = project_name_
            combine_project_dir = os.path.abspath(code_gen_engine_env_manager.project_dir / ".." / project_name)
            project_dir_list.append(combine_project_dir)
        plugin_execute_script = PluginExecuteScript(project_dir_list, "service.proto")

        # if any project is found that requires only specific models then setting env var to be used in plugin
        if project_name_to_msg_list_dict:
            os.environ["SELECTIVE_MSG_PER_PROJECT"] = (
                selective_message_per_project_dict_to_env_var_str(project_name_to_msg_list_dict))
    else:
        plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()
