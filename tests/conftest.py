# system imports
import os
from datetime import datetime
from pathlib import PurePath
import pytest

# project imports
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


@pytest.fixture(scope="session")
def code_gen_engine_env_manager() -> CodeGenEngineEnvManager:
    code_gen_engine_env_manager = CodeGenEngineEnvManager()
    yield code_gen_engine_env_manager


@pytest.fixture(scope="session")
def root_dir() -> PurePath:
    code_gen_root: PurePath = PurePath(__file__).parent.parent
    code_gen_root = code_gen_root / "Flux"
    yield code_gen_root


@pytest.fixture
def random_created_python_file(root_dir: PurePath):
    file_name: str = "data.py"
    local_file_path: PurePath = root_dir / file_name

    with open(local_file_path, "w") as f:
        f.write('data = [{}]'.format(21))
        f.close()

    yield file_name

    os.remove(local_file_path)
