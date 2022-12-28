import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
env_var_dict["OUTPUT_FILE_NAME"] = "file.jsx"
env_var_dict["PLUGIN_FILE_NAME"] = "jsx_file_gen_plugin.py"
env_var_dict["PB2_IMPORT_GENERATOR_PATH"] = "jsx_pb2_import_generator.py"
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_",
                                                         "PluginJsLayout", env_var_dict)
project_dir_path = str(code_gen_engine_env_manager.project_dir)
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir /
                                                      "jsx_file_trigger_script.py"), [project_dir_path])

env_var_dict["OUTPUT_FILE_NAME"] = "Layout.jsx"
env_var_dict["PLUGIN_FILE_NAME"] = "jsx_layout_gen_plugin.py"
env_var_dict["PB2_IMPORT_GENERATOR_PATH"] = "jsx_pb2_import_generator.py"
env_var_dict["TEMPLATE_FILE_NAME"] = "jsx_layout_temp.txt"
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_",
                                                         "PluginJsLayout", env_var_dict)
project_dir_path = str(code_gen_engine_env_manager.project_dir)
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir /
                                                      "jsx_layout_trigger_script.py"), [project_dir_path])

env_var_dict["OUTPUT_FILE_NAME"] = "file.jsx"
env_var_dict["PLUGIN_FILE_NAME"] = "js_slice_file_gen_plugin.py"
env_var_dict["PB2_IMPORT_GENERATOR_PATH"] = "jsx_pb2_import_generator.py"
env_var_dict["UILAYOUT_MESSAGE_NAME"] = "UILayout"
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_",
                                                         "PluginJsLayout", env_var_dict)
project_dir_path = str(code_gen_engine_env_manager.project_dir)
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir /
                                                      "js_slice_trigger_script.py"), [project_dir_path])

env_var_dict["OUTPUT_FILE_NAME"] = "store.js"
env_var_dict["PLUGIN_FILE_NAME"] = "js_store_file_gen_plugin.py"
env_var_dict["PB2_IMPORT_GENERATOR_PATH"] = "jsx_pb2_import_generator.py"
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_",
                                                         "PluginJsLayout", env_var_dict)
project_dir_path = str(code_gen_engine_env_manager.project_dir)
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir /
                                                      "js_store_trigger_script.py"), [project_dir_path])

env_var_dict["OUTPUT_FILE_NAME"] = "projectSpecificUtils.js"
env_var_dict["PLUGIN_FILE_NAME"] = "js_project_specific_utils_plugin.py"
env_var_dict["PB2_IMPORT_GENERATOR_PATH"] = "jsx_pb2_import_generator.py"
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_",
                                                         "PluginJsLayout", env_var_dict)
project_dir_path = str(code_gen_engine_env_manager.project_dir)
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir /
                                                      "js_project_specific_utils_trigger_script.py"),
                                                  [project_dir_path])
