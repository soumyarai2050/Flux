import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["OUTPUT_FILE_NAME"] = "file.jsx"
    env_var_dict["PLUGIN_FILE_NAME"] = "jsx_file_gen_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    env_var_dict["OUTPUT_FILE_NAME"] = "Layout.jsx"
    env_var_dict["PLUGIN_FILE_NAME"] = "jsx_layout_gen_plugin.py"
    env_var_dict["TEMPLATE_FILE_NAME"] = "jsx_layout_temp.txt"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    env_var_dict["OUTPUT_FILE_NAME"] = "file.jsx"
    env_var_dict["PLUGIN_FILE_NAME"] = "js_slice_file_gen_plugin.py"
    env_var_dict["UILAYOUT_MESSAGE_NAME"] = "UILayout"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    env_var_dict["OUTPUT_FILE_NAME"] = "store.js"
    env_var_dict["PLUGIN_FILE_NAME"] = "js_store_file_gen_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    env_var_dict["OUTPUT_FILE_NAME"] = "projectSpecificUtils.js"
    env_var_dict["PLUGIN_FILE_NAME"] = "js_project_specific_utils_plugin.py"
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_",
                                                             "PluginJsLayout", env_var_dict)
    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()
