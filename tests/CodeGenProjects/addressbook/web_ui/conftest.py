import pytest
from pathlib import PurePath
import json
import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa

from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from tests.CodeGenProjects.addressbook.app.utility_test_functions import project_dir_path
from tests.CodeGenProjects.addressbook.web_ui.web_ui_models import *
from tests.CodeGenProjects.addressbook.web_ui.utility_test_functions import get_driver, wait, \
    get_web_project_url, test_config_file_path, create_pair_strat, override_default_limits


@pytest.fixture(scope="session")
def schema_dict() -> Dict[str, any]:
    schema_path: PurePath = project_dir_path / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "r") as f:
        schema_dict: Dict[str, any] = json.loads(f.read())
    yield schema_dict


@pytest.fixture()
def config_dict() -> Dict[str, any]:
    config_dict: Dict[str, any] = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
    yield config_dict


@pytest.fixture()
def driver_type(request):
    driver_type: DriverType = request.param
    yield driver_type


@pytest.fixture()
def driver(driver_type, config_dict) -> WebDriver:
    driver: WebDriver = get_driver(config_dict=config_dict, driver_type=driver_type)
    yield driver
    driver.quit()


@pytest.fixture()
def web_project(clean_and_set_limits, driver, pair_strat, expected_order_limits_, expected_portfolio_limits_):
    override_default_limits(expected_order_limits_, expected_portfolio_limits_)
    driver.maximize_window()
    time.sleep(Delay.SHORT.value)
    driver.get(get_web_project_url())
    # verify is portfolio status is created
    wait(driver).until(EC.presence_of_element_located((By.ID, "portfolio_status")))
    portfolio_status_widget = driver.find_element(By.ID, "portfolio_status")
    driver.execute_script('arguments[0].scrollIntoView(true)', portfolio_status_widget)
    wait(driver).until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    kill_switch_btn = portfolio_status_widget.find_element(By.NAME, "kill_switch")
    assert kill_switch_btn.is_displayed(), "failed to load web project, kill switch button not found"
    create_pair_strat(driver, pair_strat)


@pytest.fixture()
def pair_strat() -> Dict[str, any]:
    pair_strat = {
        "pair_strat_params": {
            "strat_leg1": {
                "sec": {
                    "sec_id": "CB_Sec_1"
                },
                "side": "BUY"
            },
            "strat_leg2": {
                "sec": {
                    "sec_id": "EQT_Sec_1"
                },
                "side": "SELL"
            },
            "common_premium": 3
        }
    }
    yield pair_strat


@pytest.fixture()
def pair_strat_edit() -> Dict[str, any]:
    pair_strat_edit = {
        "pair_strat_params": {

            "common_premium": 55,
            "hedge_ratio": 60
        }
    }
    yield pair_strat_edit


@pytest.fixture()
def strat_limits() -> Dict[str, any]:
    strat_limits = {
        "max_open_orders_per_side": 4,
        "max_cb_notional": 500,
        "max_open_cb_notional": 600,
        "max_net_filled_notional": 700,
        "max_concentration": 7,
        "limit_up_down_volume_participation_rate": 20,
        "cancel_rate": {
            "max_cancel_rate": 10,
            "applicable_period_seconds": 9,
            "waived_min_orders": 2
        },
        "market_trade_volume_participation": {
            "max_participation_rate": 15,
            "applicable_period_seconds": 25
        },
        "market_depth": {
            "participation_rate": 90,
            "depth_levels": 18
        },
        "residual_restriction": {
            "max_residual": 4000,
            "residual_mark_seconds": 1
        }
    }
    yield strat_limits

