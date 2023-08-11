import os
import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript, ProtoGenOutputTypes
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


if __name__ == "__main__":
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_var_dict = CodeGenEngineEnvManager.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "cpp_proto2_model_plugin.py"
    # Add any custom env variable required in plugin like above

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "PluginCppProto2", env_var_dict)

    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), ".proto")
    plugin_execute_script.execute()

    project_dir = PurePath(code_gen_engine_env_manager.project_dir)
    model_dir = project_dir / "generated" / "CppProto2"
    output_dir = str(project_dir / "generated")

    all_proto_file_path_list = os.listdir(model_dir)
    proto_files_dir_paths_list = [str(model_dir)]
    plugin_execute_script.compile_protoc_models(all_proto_file_path_list, proto_files_dir_paths_list,
                                                output_dir, ProtoGenOutputTypes.Proto_Gen_Cc)
