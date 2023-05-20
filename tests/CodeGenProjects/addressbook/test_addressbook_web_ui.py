import time
import pytest
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC  # noqa
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from pathlib import PurePath
from typing import Final, Dict, Optional
from enum import auto
from fastapi_utils.enums import StrEnum

from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations

TESTS_DATA_DIR = PurePath(__file__).parent / "data"

short_delay: Final[int] = 2
delay: Final[int] = 5
long_delay: Final[int] = 20


class DriverType(StrEnum):
    CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"
    SAFARI = "safari"


class SearchType(StrEnum):
    ID = auto()
    NAME = auto()
    TAG_NAME = auto()


class Layout(StrEnum):
    TABLE = auto()
    TREE = auto()


@pytest.fixture(scope="session")
def config_dict() -> Dict:
    config_file_path = TESTS_DATA_DIR / "config.yaml"
    config_dict: Dict = load_yaml_configurations(str(config_file_path))
    yield config_dict


@pytest.fixture(scope="session")
def pair_strat() -> Dict:
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


@pytest.fixture(scope="session")
def pair_strat_edit() -> Dict:
    pair_strat_edit = {
        "pair_strat_params": {

            "common_premium": 55,
            "hedge_ratio": 60
        }
    }
    yield pair_strat_edit


@pytest.fixture(scope="session")
def strat_limits() -> Dict:
    strat_limits = {
        "max_open_orders_per_side": 4,
        "max_cb_notional": 1000,
        "max_open_cb_notional": 2000,
        "max_net_filled_notional": 3000,
        "max_concentration": 4,
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


def get_driver(config_dict: Dict, driver_type: DriverType) -> Optional[WebDriver]:
    driver_path: str | None = config_dict["driver"].get(driver_type)
    assert driver_path is not None, f"unsupported driver_type: {driver_type}"
    driver: Optional[WebDriver] = None
    match driver_type:
        case DriverType.CHROME:
            driver: webdriver.Chrome = webdriver.Chrome(driver_path)
        case DriverType.EDGE:
            driver: webdriver.Edge = webdriver.Edge(driver_path)
        case DriverType.FIREFOX:
            driver: webdriver.Firefox = webdriver.Firefox(driver_path)
        case DriverType.SAFARI:
            driver: webdriver.Safari = webdriver.Safari(driver_path)
    assert driver is not None, f"failed to initialize webdriver for driver_type: {driver_type}"
    return driver


def wait(driver: WebDriver) -> WebDriverWait:
    return WebDriverWait(driver, long_delay)


def load_web_project(driver: WebDriver) -> None:
    driver.maximize_window()
    time.sleep(short_delay)
    driver.get("http://localhost:3020/")
    # verify is portfolio status is created
    wait(driver).until(EC.presence_of_element_located((By.ID, "portfolio_status")))
    portfolio_status_widget = driver.find_element(By.ID, "portfolio_status")
    driver.execute_script('arguments[0].scrollIntoView(true)', portfolio_status_widget)
    wait(driver).until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    kill_switch_btn = portfolio_status_widget.find_element(By.NAME, "kill_switch")
    assert kill_switch_btn.is_displayed(), "failed to load web project, kill switch button not found"


def set_input_field(widget: WebElement, xpath: str, name: str, value: str,
                    search_type: SearchType = SearchType.NAME,
                    autocomplete: bool = False) -> None:
    if not hasattr(By, search_type):  # ..
        raise Exception(f"unsupported search type: {search_type}")  # ..
    input_div_xpath: str = f"//div[@data-xpath='{xpath}']"
    input_div_element = widget.find_element(By.XPATH, input_div_xpath)
    input_element = input_div_element.find_element(getattr(By, search_type), name)  # ..
    input_element.click()
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    # set input field
    input_element.send_keys(value)
    if autocomplete:
        input_element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
    # else not required


def set_autocomplete_field(widget: WebElement, xpath: str, name: str, search_type: SearchType, value: str) -> None:
    autocomplete_xpath: str = f"//div[@data-xpath='{xpath}']"
    autocomplete_element = widget.find_element(By.XPATH, autocomplete_xpath)
    assert autocomplete_element is not None, f"autocomplete element not found for xpath: {xpath}, name: {name}"
    set_input_field(widget=autocomplete_element, xpath=xpath, name=name, value=value, search_type=search_type,
                    autocomplete=True)


def set_dropdown_field(widget: WebElement, xpath: str, name: str, value: str) -> None:
    dropdown_xpath: str = f"//div[@data-xpath='{xpath}']"
    dropdown_element = widget.find_element(By.XPATH, dropdown_xpath)
    dropdown = dropdown_element.find_element(By.ID, name)
    dropdown.click()
    dropdown.find_element(By.XPATH, f"//li[contains(text(), '{value}')]").click()


def confirm_save(driver: WebDriver) -> None:
    confirm_save_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    confirm_btn = confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm']")
    confirm_btn.click()
    time.sleep(short_delay)


def create_pair_strat(driver: WebDriver, pair_strat: Dict) -> None:
    load_web_project(driver=driver)

    # create a new strat from strat collection
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_collection_widget)
    create_strat_btn = strat_collection_widget.find_element(By.XPATH, "//button[@name='Create']")
    create_strat_btn.click()
    time.sleep(short_delay)

    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    xpath: str
    value: str

    # select strat_leg1.sec.sec_id
    xpath = "pair_strat_params.strat_leg1.sec.sec_id"
    value = pair_strat["pair_strat_params"]["strat_leg1"]["sec"]["sec_id"]
    set_autocomplete_field(widget=pair_strat_params_widget, xpath=xpath, name="sec_id", search_type=SearchType.NAME,
                           value=value)

    # select strat_leg1.side
    xpath = "pair_strat_params.strat_leg1.side"
    value = pair_strat["pair_strat_params"]["strat_leg1"]["side"]
    set_dropdown_field(widget=pair_strat_params_widget, xpath=xpath, name="side", value=value)

    # select strat_leg2.sec.sec_id
    xpath = "pair_strat_params.strat_leg2.sec.sec_id"
    value = pair_strat["pair_strat_params"]["strat_leg2"]["sec"]["sec_id"]
    set_autocomplete_field(widget=pair_strat_params_widget, xpath=xpath, name="sec_id", search_type=SearchType.NAME,
                           value=value)

    # select pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat["pair_strat_params"]["common_premium"]
    set_input_field(widget=pair_strat_params_widget, xpath=xpath, name="common_premium", value=value,
                    search_type=SearchType.ID)

    # save strat collection
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    time.sleep(short_delay)
    confirm_save(driver=driver)
    # verify pair strat
    validate_pair_strat_params(widget=pair_strat_params_widget, pair_strat=pair_strat)


def validate_pair_strat_params(widget: WebElement, pair_strat: Dict) -> None:
    # strat_leg1.sec.sec_id
    value_stratleg1_sec = widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params.strat_leg1.sec.sec_id']")
    stratleg1_sec = value_stratleg1_sec.find_element(By.TAG_NAME, "input").get_attribute('value')

    # strat_leg1.side
    value_strat_leg1_side = widget.find_element(By.XPATH,
                                                "//div[@data-xpath='pair_strat_params.strat_leg1.side']")
    strat_side = value_strat_leg1_side.find_element(By.TAG_NAME, "input").get_attribute('value')

    # strat_leg2.sec.sec_id
    value_stratleg2_sec = widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params."
                                                        "strat_leg2.""sec.sec_id']")
    stratleg2_sec_id = value_stratleg2_sec.find_element(By.TAG_NAME, "input").get_attribute(
        'value')

    # pair_strat_params.common_premium
    value_of_strat_common_prem = widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params.common_premium']")
    strat_common_prem = value_of_strat_common_prem.find_element(By.NAME, 'common_premium') \
        .get_attribute('value')

    # verifying the values of pair_strat
    pair_strat_params = pair_strat["pair_strat_params"]
    assert stratleg1_sec == pair_strat_params["strat_leg1"]["sec"]["sec_id"]
    assert strat_side == pair_strat_params["strat_leg1"]["side"]
    assert stratleg2_sec_id == pair_strat_params["strat_leg2"]["sec"]["sec_id"]
    assert strat_common_prem == str(pair_strat_params["common_premium"])


def test_create_pair_strat(config_dict, pair_strat):
    # load driver
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict, driver_type=driver_type)

    create_pair_strat(driver=driver, pair_strat=pair_strat)
    time.sleep(short_delay)
    driver.quit()


def switch_layout(widget: WebElement, widget_name: str, layout: Layout) -> None:
    button_name: str = ""
    if layout == Layout.TREE:
        button_name = "Tree"
    elif layout == Layout.TABLE:
        button_name = "Table"
    try:
        layout_btn = widget.find_element(By.XPATH, f"//div[@id='{widget_name}']//button[@name='{button_name}']")
        layout_btn.click()
        time.sleep(short_delay)
    except NoSuchElementException as e:
        raise Exception(f"failed to switch to layout: {layout};;; exception: {e}")


def activate_strat(driver) -> None:
    # Find the button with the name 'strat_state'
    strat_state_btn = driver.find_element(By.XPATH, "//button[contains(@name,'strat_state')]")

    # Get the button text
    button_text = strat_state_btn.text

    # Check if the button text is ACTIVATE, ERROR, or PAUSED
    assert button_text in ["ACTIVATE", "ERROR", "PAUSE"], "Unknown button state."

    if button_text == "ACTIVATE":
        # Activate the strat
        strat_state_btn.click()
        time.sleep(short_delay)

        # Confirm the activation
        confirm_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Confirm']")
        confirm_btn.click()
        time.sleep(short_delay)

        # Verify if the strat is in active state
        pause_strat = driver.find_element(By.XPATH,
                                          "//tbody//button[@value='Pause'][normalize-space()='Pause']")
        btn_text = pause_strat.text
        assert btn_text == "PAUSE", "Failed to activate strat."
        print("Strat is active.")

    elif button_text in ["ERROR", "PAUSE"]:
        print(f"Strat is in {button_text} state. Cannot activate.")


def test_update_strat_n_activate_using_tree_view(config_dict: Dict, pair_strat: Dict, pair_strat_edit: Dict,
                                                 strat_limits: Dict) -> None:
    # load driver
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)

    # edit_btn, first take out strat collection
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()
    time.sleep(short_delay)

    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")

    # pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat_edit["pair_strat_params"]["common_premium"]
    set_input_field(widget=pair_strat_params_widget, xpath=xpath, name="common_premium", value=value,
                    search_type=SearchType.ID)

    # pair_strat_params.hedge_ratio
    xpath = "pair_strat_params.hedge_ratio"
    value = pair_strat_edit["pair_strat_params"]["hedge_ratio"]
    set_input_field(widget=pair_strat_params_widget, xpath=xpath, name="hedge_ratio", value=value,
                    search_type=SearchType.ID)

    # strat_limits_widget
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")

    # scroll into view
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_limits_widget)
    time.sleep(short_delay)
    # save
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    time.sleep(short_delay)
    confirm_save(driver=driver)

    # tree_view_btn
    switch_layout(widget=strat_limits_widget, widget_name="strat_limits", layout=Layout.TREE)

    # creating_strat_of_strat_limits_in_tree_view
    # strat_limits.max_open_orders_per_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_open_orders_per_side", value=value, search_type=SearchType.ID)

    # strat_limits.max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = strat_limits["max_cb_notional"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_cb_notional", value=value,
                    search_type=SearchType.ID)

    # strat_limits.max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_open_cb_notional", value=value,
                    search_type=SearchType.ID)

    # strat_limits.max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_net_filled_notional", value=value,
                    search_type=SearchType.ID)

    # strat_limits.max_concentration
    xpath = "strat_limits.max_concentration"
    value = strat_limits["max_concentration"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_concentration", value=value,
                    search_type=SearchType.ID)

    # strat_limits.limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="limit_up_down_volume_participation_rate",
                    value=value,
                    search_type=SearchType.ID)

    # strat_limits.cancel_rate.max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_cancel_rate", value=value,
                    search_type=SearchType.ID)

    # applicable_period_seconds
    # xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    # value = strat_limits["cancel_rate"]["applicable_period_seconds"]

    # strat_limits.cancel_rate.waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="waived_min_orders", value=value,
                    search_type=SearchType.ID)

    # strat_limits.market_trade_volume_participation.max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_participation_rate", value=value,
                    search_type=SearchType.ID)

    # mrket_trde_applicable_periods_seconds
    xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    mrket_trde_applicable_periods_seconds = strat_limits_widget. \
        find_element(By.XPATH, "//div[@data-xpath='strat_limits."
                               "market_trade_volume_participation.applicable_period_seconds']")
    mrket_trde_applicable_periods_seconds.click()
    set_input_field(widget=mrket_trde_applicable_periods_seconds, xpath=xpath, name="input", value=value,
                    search_type=SearchType.TAG_NAME)

    # strat_limits.market_depth.participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="participation_rate", value=value,
                    search_type=SearchType.ID)

    # strat_limits.market_depth.depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="depth_levels", value=value,
                    search_type=SearchType.ID)

    # strat_limits.residual_restriction.max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="max_residual", value=value,
                    search_type=SearchType.ID)

    # strat_limits.residual_restriction.residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    set_input_field(widget=strat_limits_widget, xpath=xpath, name="residual_mark_seconds", value=value,
                    search_type=SearchType.ID)

    # activate_strat
    activate_strat(driver)

    # validate_strat_limits
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)
    driver.quit()


def get_value_from_input_field(widget: WebElement, name: str, xpath: str, layout: Layout):
    parent_tag: str = ""
    if layout == Layout.TREE:
        parent_tag = "div"
    elif layout == Layout.TABLE:
        parent_tag = "td"
    parent_xpath: str = f"//{parent_tag}[@data-xpath='{xpath}']"
    parent_element = widget.find_element(By.XPATH, parent_xpath)
    if layout == Layout.TABLE:
        parent_element.click()
    input_element = parent_element.find_element(By.TAG_NAME, "input")
    value = input_element.get_attribute("value")
    return value


def validate_strat_limits(widget: WebElement, strat_limits: Dict, layout: Layout) -> None:
    # max_open_orders_per_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_open_orders_per_side", layout=layout)
    assert value == str(strat_limits["max_open_orders_per_side"])

    # max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_cb_notional", layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_cb_notional"])

    # max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_open_cb_notional", layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_open_cb_notional"])

    # max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_net_filled_notional", layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_net_filled_notional"])

    # max_concentration
    xpath = "strat_limits.max_concentration"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_concentration", layout=layout)
    assert value == str(strat_limits["max_concentration"])

    # limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="limit_up_down_volume_participation_rate",
                                       layout=layout)
    assert value == str(strat_limits["limit_up_down_volume_participation_rate"])

    # max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_cancel_rate", layout=layout)
    assert value == str(strat_limits["cancel_rate"]["max_cancel_rate"])

    # applicable_period_seconds
    # xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    # value = get_value_from_input_field(widget=widget, xpath=xpath, name="applicable_period_seconds", layout=layout)

    # waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="waived_min_orders", layout=layout)
    assert value == str(strat_limits["cancel_rate"]["waived_min_orders"])

    # max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_participation_rate", layout=layout)
    assert value == str(strat_limits["market_trade_volume_participation"]["max_participation_rate"])

    # applicable_period_seconds
    # xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    # value = get_value_from_input_field(widget=widget, xpath=xpath, name="applicable_period_seconds", layout=layout)

    # participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="participation_rate", layout=layout)
    assert value == str(strat_limits["market_depth"]["participation_rate"])

    # depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="depth_levels", layout=layout)
    assert value == str(strat_limits["market_depth"]["depth_levels"])

    # max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="max_residual", layout=layout)
    value = value.replace(",", "")
    assert value == str(strat_limits["residual_restriction"]["max_residual"])

    # residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = get_value_from_input_field(widget=widget, xpath=xpath, name="residual_mark_seconds", layout=layout)
    assert value == str(strat_limits["residual_restriction"]["residual_mark_seconds"])


def set_table_view_input(widget: webdriver, xpath: str, value: str,
                         search_type: SearchType = SearchType.TAG_NAME) -> None:
    if not hasattr(By, search_type):
        raise Exception(f"unsupported search type: {search_type}")
    input_td_xpath: str = f"//td[@data-xpath='{xpath}']"
    input_td_xpath_element = widget.find_element(By.XPATH, input_td_xpath)
    input_td_xpath_element.click()
    set_input = input_td_xpath_element.find_element(By.TAG_NAME, "input")
    set_input.click()
    set_input.send_keys(Keys.CONTROL + "a")
    set_input.send_keys(Keys.BACK_SPACE)
    set_input.send_keys(value)


def test_update_strat_n_activate_using_table_view(config_dict: Dict, pair_strat: Dict, strat_limits: Dict) -> None:
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)

    # strat_limits_widget
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    time.sleep(short_delay)

    # strat_collection_widget
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")

    # edit_btn
    strat_collection_widget.find_element(By.NAME, "Edit").click()

    # max_open_per_orders_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = strat_limits["max_cb_notional"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_concentration
    xpath = "strat_limits.max_concentration"
    value = strat_limits["max_concentration"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    value = strat_limits["cancel_rate"]["applicable_period_seconds"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    # value = value.replace(",", "")
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    set_table_view_input(widget=strat_limits_widget, xpath=xpath, value=value)

    # activate_n_confirm_btn
    activate_strat(driver)
    # edit_btn
    strat_collection_widget.find_element(By.NAME, "Edit").click()

    strat_limits_widget = driver.find_element(By.ID, "strat_limits")

    # validating the values
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TABLE)

def open_setting(widget: WebElement, widget_name: str) -> None:
    xpath: str = f"//div[@id='{widget_name}']//button[@name='Settings']"
    setting_xpath = widget.find_element(By.XPATH, xpath)
    setting_xpath.click()


def select_checkbox(widget: WebElement, xpath: str, use_type: str) -> WebElement:
    open_setting(widget=widget, widget_name="pair_strat_params")
    xpath: str = f"//li[{xpath}]"
    xpath_element = widget.find_element(By.XPATH, xpath)
    input_element = xpath_element.find_element(By.TAG_NAME, "input")
    if use_type == "validate":
        return input_element
    input_element.click()
    time.sleep(short_delay)


def test_field_hide_n_show_in_common_key(config_dict: Dict, pair_strat: Dict, strat_limits: Dict):
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)

    pair_strat_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_widget, widget_name="pair_strat_params", layout=Layout.TABLE)


    # strat_leg1.sec.sec_id
    xpath = "3"
    select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="")

    # muilist = pair_strat_widget.find_element(By.XPATH, "//ul[@role='listbox']")
    # sec_id = muilist.find_element(By.TAG_NAME, "input")
    # sec_id.click()
    # time.sleep(short_delay)


    # strat_leg1.side
    xpath = "5"
    select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="")

    # strat_leg2.sec.sec_id
    xpath = "8"
    select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="")

    # strat_leg2.side
    xpath = "10"
    select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="")

    # common premium
    xpath = "13"
    select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="")

    # hedge ratio
    xpath = "14"
    select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="")
    # verifying
    validate_pair_strat_table_view_checkbox(driver=driver)


def validate_pair_strat_table_view_checkbox(driver: WebDriver):
    pair_strat_widget = driver.find_element(By.ID, "pair_strat_params")

    xpath = "3"
    input_element = select_checkbox(widget=pair_strat_widget, xpath=xpath, use_type="validate")
    assert not input_element.is_selected()






