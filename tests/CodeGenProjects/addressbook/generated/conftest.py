# system imports
import os
import time
from pathlib import PurePath
from threading import Thread
import pytest
from datetime import datetime

os.environ["DBType"] = "beanie"

# project imports
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_launch_server import \
    strat_manager_service_launch_server
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


@pytest.fixture(scope="session")
def web_clients():
    strat_manager_service_web_client = StratManagerServiceWebClient()
    yield strat_manager_service_web_client


@pytest.fixture(scope="session")
def root_dir():
    root_path: PurePath = PurePath(__file__).parent.parent.parent.parent.parent
    root_path: PurePath = root_path / "Flux"
    yield root_path


@pytest.fixture(scope="session")
def order_limit():
    order_limits_json = {
        "id": 10,
        "max_basis_points": 5,
        "max_px_deviation": 0.8,
        "max_px_levels": 6,
        "max_order_qty": 8,
        "max_order_notional": 9
        }
    yield order_limits_json


@pytest.fixture(scope="session")
def order_limit_received():
    order_limits_json_recieved = {
        "id": 10,
        "max_basis_points": 5,
        "max_px_deviation": 0.8,
        "max_px_levels": 6,
        "max_order_qty": 8,
        "max_order_notional": 9
    }
    yield order_limits_json_recieved


@pytest.fixture(scope="session")
def order_limits_updated():
    order_limits_json_updated = {
        "id": 10,
        "max_basis_points": 15,
        "max_px_deviation": 0.8,
        "max_px_levels": 6,
        "max_order_qty": 8,
        "max_order_notional": 9
    }
    yield order_limits_json_updated


@pytest.fixture(scope="session")
def partial_updated_order_limits():
    partial_updated_order_limits = {
        "id": 10,
        "max_px_deviation": 0.8,
    }
    yield partial_updated_order_limits


@pytest.fixture(scope="session")
def partial_updated_order_limits_complete():
    partial_updated_order_limits = {
        "id": 10,
        "max_basis_points": 25,
        "max_px_deviation": 0.8,
        "max_px_levels": 21,
        "max_order_qty": 8,
        "max_order_notional": 9
    }
    yield partial_updated_order_limits


@pytest.fixture(scope="session")
def updated_order_limit():
    updated_order_limit = {
        "id": 10,
        "max_basis_points": 25,
        "max_px_deviation": 0.8,
        "max_px_levels": 21,
        "max_order_qty": 8,
        "max_order_notional": 9
    }
    yield updated_order_limit


@pytest.fixture(scope="session")
def delete_response():
    delete_response = {
        'msg': 'Deletion Successful', 'id': 10
    }
    yield delete_response


def launch_mongo_server(mongo_log_file_path: str, db_data_dir: str):
    os.system(f"mongod --logpath={mongo_log_file_path} --dbpath={db_data_dir} &")


def launch_beanie_fastapi(root_dir):
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    project_dir = root_dir / 'CodeGenProjects' / 'addressbook'
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_DIR_PATH": f"{project_dir / 'log' }",
        "LOG_FILE_NAME": f"beanie_logs_{datetime_str}.log",
        "LOG_LEVEL": "debug",
        "FASTAPI_FILE_NAME": "strat_manager_service_beanie_fastapi",
        "DBType": "beanie"
    }
    code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_", "_", env_dict)
    strat_manager_service_launch_server()


def launch_cache_fastapi(root_dir):
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    project_dir = root_dir / 'CodeGenProjects' / 'addressbook'
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_DIR_PATH": f"{project_dir / 'log' }",
        "LOG_FILE_NAME": f"cache_logs_{datetime_str}.log",
        "LOG_LEVEL": "debug",
        "FASTAPI_FILE_NAME": "strat_manager_service_cache_fastapi",
        "DBType": "cache"
    }
    code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_", "_", env_dict)
    strat_manager_service_launch_server()


@pytest.fixture(scope="session")
def launch_cache(root_dir: PurePath):
    launch_cache_fastapi_path = root_dir / 'CodeGenProjects' / 'addressbook' / 'scripts'
    os.chdir(launch_cache_fastapi_path)
    launch_cache_fastapi_thread = Thread(target=launch_cache_fastapi, args=(root_dir,), daemon=True)
    launch_cache_fastapi_thread.start()
    time.sleep(5)
    yield


@pytest.fixture(scope="session")
def launch_mongo_and_beanie_fastapi(root_dir: PurePath):
    # By default, MongoDB runs using the mongodb user account. If you change the user that runs the MongoDB process,
    # you must also modify the permission to the data and log directories to give this user access to these directories.
    # for more info visit:
    # https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/#run-mongodb-community-edition

    # Before running the server need to create the mongo.log file to the path below so that mongo server
    # can be run from any directory.
    mongo_log_path = "mongo-dir/logs/mongo.log"
    mongo_db_path = "mongo-dir/data"
    launch_mongo_thread = Thread(target=launch_mongo_server, args=(mongo_log_path, mongo_db_path,), daemon=True)
    launch_mongo_thread.start()
    time.sleep(5)

    launch_beanie_fastapi_path = root_dir / 'CodeGenProjects' / 'addressbook' / 'scripts'
    os.chdir(launch_beanie_fastapi_path)
    launch_beanie_fastapi_thread = Thread(target=launch_beanie_fastapi, args=(root_dir,), daemon=True)
    launch_beanie_fastapi_thread.start()
    time.sleep(5)
    yield
