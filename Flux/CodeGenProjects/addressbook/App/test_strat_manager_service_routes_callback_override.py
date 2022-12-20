import pytest
import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


@pytest.fixture(scope="session")
def set_instance_and_env_manager_instance():
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0"
    }
    code_gen_engine_env_manager.init_env_and_update_sys_path("pair_strat_engine", "_", "_", env_dict)

    yield code_gen_engine_env_manager


def test_object_manipulation(set_instance_and_env_manager_instance):
    project_dir: PurePath = PurePath(__file__).parent.parent
    script_path = project_dir / "output" / "strat_manager_service_beanie_fastapi.py"
    set_instance_and_env_manager_instance.execute_python_script(str(script_path))

