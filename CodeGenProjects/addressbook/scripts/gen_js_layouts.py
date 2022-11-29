import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
custom_env_dict = {
    "JSX_FILE_CONFIG_PATH": str(PurePath(__file__).parent.parent / "misc" / "jsx_file_gen_config.yaml"),
    "JSX_LAYOUT_CONFIG_PATH": str(PurePath(__file__).parent.parent / "misc" / "jsx_layout_gen_config.yaml"),
    "JS_SLICE_CONFIG_PATH": str(PurePath(__file__).parent.parent / "misc" / "js_slice_gen_config.yaml"),
    "JS_STORE_CONFIG_PATH": str(PurePath(__file__).parent.parent / "misc" / "js_store_gen_config.yaml"),
    "DEBUG_SLEEP_TIME": "0",
    "UILAYOUT_MESSSAGE_NAME": "UILayout"
}
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "jsx_file_gen_config.yaml",
                                                         "PluginJsLayout", custom_env_dict)

project_dir_path = str(code_gen_engine_env_manager.project_dir)

code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir / "jsx_file_trigger_script.py"),
                                                  [project_dir_path, custom_env_dict["JSX_FILE_CONFIG_PATH"]])
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir / "jsx_layout_trigger_script.py"),
                                                  [project_dir_path, custom_env_dict["JSX_LAYOUT_CONFIG_PATH"]])
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir / "js_slice_trigger_script.py"),
                                                  [project_dir_path, custom_env_dict["JS_SLICE_CONFIG_PATH"]])
code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir / "js_store_trigger_script.py"),
                                                  [project_dir_path, custom_env_dict["JS_STORE_CONFIG_PATH"]])
