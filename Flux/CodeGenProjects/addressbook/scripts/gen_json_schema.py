import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
env_var_dict["OUTPUT_FILE_NAME_SUFFIX"] = "json_schema.json"
env_var_dict["PLUGIN_FILE_NAME"] = "json_schema_convert_plugin.py"
env_var_dict["PB2_IMPORT_GENERATOR_PATH"] = "json_pb2_import_generator.py"
env_var_dict["AUTOCOMPLETE_FILE_PATH"] = str(PurePath(__file__).parent.parent / "misc" / "autocomplete.json")
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_", "PluginJSONSchema", env_var_dict)

params_list = [
    str(code_gen_engine_env_manager.project_dir),
]

code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir / "trigger_script.py"),
                                                  params_list)
