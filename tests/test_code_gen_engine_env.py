# system imports
import os
from pathlib import PurePath
import pytest

# Projects imports
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


def test_execute_python_script(code_gen_engine_env_manager: CodeGenEngineEnvManager, root_dir: PurePath,
                               random_created_python_file: str):

    # Full path of random created python script
    file_path: PurePath = root_dir / random_created_python_file

    # testing code_gen_engine_env_manager.execute_python_script()
    assert code_gen_engine_env_manager.execute_python_script(str(file_path)) == 0, \
        f"code_gen_engine_env_manager.execute_python_script() failed: file_path: {file_path}"


def test_init_env_and_update_sys_path(code_gen_engine_env_manager: CodeGenEngineEnvManager, root_dir: PurePath):

    project_name: str = "pair_strat_engine"
    config_file_name: str = "_"
    plugin_name: str = "PluginFastApi"
    project_dir_name: str = "CodeGenProjects"
    config_dir: str = "misc"
    py_code_gen_engine_dir: str = "PyCodeGenEngine"
    output_dir: str = "generated"

    # setting environment variable.
    code_gen_engine_env_manager.init_env_and_update_sys_path(project_name, config_file_name,
                                                             plugin_name)

    project_dir: PurePath = root_dir / project_dir_name / project_name
    config_path_with_file_name: PurePath = root_dir / project_dir_name / project_name / config_dir / config_file_name
    plugin_dir: PurePath = root_dir / py_code_gen_engine_dir / plugin_name
    output_dir: PurePath = root_dir / project_dir_name / project_name / output_dir

    # asserting environment variables.
    assert os.getenv("PROJECT_DIR") == str(project_dir), f"test_init_env_and_update_sys_path() test failed: " \
                                                         f"os.getenv('PROJECT_DIR') failed: {str(project_dir)}"
    assert os.getenv("CONFIG_PATH") == str(config_path_with_file_name), f"test_init_env_and_update_sys_path() " \
                                                                        f"test failed: os.getenv('CONFIG_PATH') " \
                                                                        f"failed: {str(config_path_with_file_name)}"
    assert os.getenv("PLUGIN_DIR") == str(plugin_dir), f"test_init_env_and_update_sys_path() failed: " \
                                                       f"os.getenv('PLUGIN_DIR') failed: {str(project_dir)}"
    assert os.getenv("OUTPUT_DIR") == str(output_dir), f"test_init_env_and_update_sys_path() test failed: " \
                                                       f"os.getenv('OUTPUT_DIR') failed: {str(output_dir)}"

    # Removing environment variable.
    os.environ.pop("PROJECT_DIR")
    os.environ.pop("CONFIG_PATH")
    os.environ.pop("PLUGIN_DIR")
    os.environ.pop("OUTPUT_DIR")

    list_of_environment_variables = ["PROJECT_DIR", "CONFIG_PATH", "PLUGIN_PATH", "OUTPUT_DIR"]
    available_environment_variable: list = []

    # Checking environment variable deleted or not.
    for i in list_of_environment_variables:
        if i in os.environ:
            available_environment_variable.append(i)
        # else not required: if environment not exists, no need to append in list.

    if len(available_environment_variable) == 0:
        assert True, f"expected none, found: {available_environment_variable}"
    else:
        assert False, f"Environment variable deletion failed: {available_environment_variable}"


@pytest.mark.parametrize("shell_cmd,expected_return_code", [("pwd", 0), ("ls", 0), ], ids=["pwd-test", "ls-test"])
def test_execute_shell_command(code_gen_engine_env_manager: CodeGenEngineEnvManager, shell_cmd: str,
                               expected_return_code: int):

    assert code_gen_engine_env_manager.execute_shell_command(shell_cmd) == expected_return_code, \
        f"code_gen_engine_env_manager.execute_shell_command() failed: shell_cmd: {shell_cmd}"


def test_get_instance(code_gen_engine_env_manager: CodeGenEngineEnvManager):
    assert code_gen_engine_env_manager.get_instance() == CodeGenEngineEnvManager().get_instance(), \
        f"code_gen_engine_env_manager.get_instance() failed: {code_gen_engine_env_manager.get_instance()}"
