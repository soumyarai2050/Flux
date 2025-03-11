import sys
import os
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_utils import selective_message_per_project_dict_to_env_var_str


def call_plugin_with_multiple_projects():
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


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "jsx_file_gen_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)

    data_dir = code_gen_engine_env_manager.project_dir / "data"
    config_file_path = data_dir / "config.yaml"
    config_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
    combine_project_names = config_dict.get("multi_project_plugin")
    call_plugin_with_multiple_projects()

    env_var_dict["PLUGIN_FILE_NAME"] = "selector_js_gen_plugin.py"
    env_var_dict["TEMPLATE_FILE_NAME"] = "selectors_js_temp.txt"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    call_plugin_with_multiple_projects()


    env_var_dict["PLUGIN_FILE_NAME"] = "config_js_gen_plugin.py"
    env_var_dict["TEMPLATE_FILE_NAME"] = "config_js_temp.txt"
    env_var_dict["UI_PORT"] = config_dict.get("ui_port")
    env_var_dict["PROXY_SERVER"] = "False" \
        if (proxy_server := config_dict.get("is_proxy_server")) is None else str(proxy_server)
    env_var_dict["HOST"] = config_dict.get("server_host")
    env_var_dict["BEANIE_PORT"] = config_dict.get("main_server_beanie_port")
    env_var_dict["CACHE_PORT"] = config_dict.get("main_server_cache_port")
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    env_var_dict["PLUGIN_FILE_NAME"] = "package_json_gen_plugin.py"
    env_var_dict["TEMPLATE_FILE_NAME"] = "package_json_temp.txt"
    env_var_dict["UI_PORT"] = config_dict.get("ui_port")
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    env_var_dict["PLUGIN_FILE_NAME"] = "js_slice_file_gen_plugin.py"
    env_var_dict["UILAYOUT_MESSAGE_NAME"] = "UILayout"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    call_plugin_with_multiple_projects()

    env_var_dict["PLUGIN_FILE_NAME"] = "js_store_file_gen_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    call_plugin_with_multiple_projects()

    env_var_dict["PLUGIN_FILE_NAME"] = "js_project_specific_utils_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    call_plugin_with_multiple_projects()

    env_var_dict["PLUGIN_FILE_NAME"] = "model_component_loader_gen_plugin.py"
    env_var_dict["TEMPLATE_FILE_NAME"] = "model_component_loder_temp.txt"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    call_plugin_with_multiple_projects()

