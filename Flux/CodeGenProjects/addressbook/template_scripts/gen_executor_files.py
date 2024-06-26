import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.CodeGenProjects.AddressBook.bartering_gen_engine_env import BarteringGenEngineEnv

if __name__ == "__main__":
    code_gen_engine_env_manager = BarteringGenEngineEnv.get_instance()
    env_var_dict = BarteringGenEngineEnv.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "street_book_plugin.py"

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "PluginStreetBook",
                                                             env_var_dict, use_project_group_template_script=True)

    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()
