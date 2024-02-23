from pathlib import PurePath

import pytest


@pytest.fixture(scope="session")
def root_dir():
    root_path: PurePath = PurePath(__file__).parent.parent.parent.parent.parent
    root_path: PurePath = root_path / "Flux"
    yield root_path


@pytest.fixture(scope="session")
def build_and_clean_web_project_path(root_dir: PurePath):
    build_and_clean_web_project_path: PurePath = root_dir / 'CodeGenProjects' / 'phone_book' / 'scripts'
    yield build_and_clean_web_project_path
