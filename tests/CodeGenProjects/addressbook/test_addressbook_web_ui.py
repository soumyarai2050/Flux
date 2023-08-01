import json
import time
import random
import pytest
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC  # noqa
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from pathlib import PurePath
from typing import Final, Dict, Optional, List, Tuple
from enum import auto
from fastapi_utils.enums import StrEnum
from pydantic import BaseModel

from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, store_json_or_dict_to_file
from tests.CodeGenProjects.addressbook.app.utility_test_functions import project_dir_path

tests_data_dir = PurePath(__file__).parent / "data"
short_delay: Final[int] = 2
delay: Final[int] = 5
long_delay: Final[int] = 20
simple_data_type_list: Final[List[str]] = ["string", "number", "date_time", "enum", "boolean"]


class DriverType(StrEnum):
    CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"
    SAFARI = "safari"


class SearchType(StrEnum):
    ID = auto()
    NAME = auto()
    TAG_NAME = auto()
    CLASS_NAME = auto()


class Layout(StrEnum):
    TABLE = auto()
    TREE = auto()
    NESTED = auto()


class WidgetType(StrEnum):
    INDEPENDENT = auto()
    DEPENDENT = auto()
    REPEATED_INDEPENDENT = auto()
    REPEATED_DEPENDENT = auto()


class FieldQuery(BaseModel):
    field_name: str
    properties: Dict[str, str | Dict[str, str]]


class WidgetQuery(BaseModel):
    widget_name: str
    fields: List[FieldQuery]


@pytest.fixture(scope="session")
def schema_dict() -> Dict[str, any]:
    schema_path: PurePath = project_dir_path / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "r") as f:
        schema_dict: Dict[str, any] = json.loads(f.read())
    yield schema_dict


@pytest.fixture()
def config_dict_() -> Dict[str, any]:
    config_file_path: PurePath = tests_data_dir / "config.yaml"
    config_dict: Dict[str, any] = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
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



def set_tree_input_field(widget: WebElement, xpath: str, name: str, value: str, search_type: SearchType = SearchType.NAME,
                    autocomplete: bool = False) -> None:
    if not hasattr(By, search_type):
        raise Exception(f"unsupported search type: {search_type}")
    input_div_xpath: str = f"//div[@data-xpath='{xpath}']"
    input_div_element = widget.find_element(By.XPATH, input_div_xpath)
    input_element = input_div_element.find_element(getattr(By, search_type), name)  # ..
    input_element.click()
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    input_element.send_keys(value)
    if autocomplete:
        input_element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
    # else not required


def set_autocomplete_field(widget: WebElement, xpath: str, name: str, search_type: SearchType, value: str) -> None:
    autocomplete_xpath: str = f"//div[@data-xpath='{xpath}']"
    autocomplete_element = widget.find_element(By.XPATH, autocomplete_xpath)
    assert autocomplete_element is not None, f"autocomplete element not found for xpath: {xpath}, name: {name}"
    set_tree_input_field(widget=autocomplete_element, xpath=xpath, name=name, value=value, search_type=search_type,
                    autocomplete=True)


def set_dropdown_field(widget: WebElement, xpath: str, name: str, value: str) -> None:
    dropdown_xpath: str = f"//div[@data-xpath='{xpath}']"
    dropdown_element = widget.find_element(By.XPATH, dropdown_xpath)
    dropdown = dropdown_element.find_element(By.ID, name)
    dropdown.click()
    dropdown.find_element(By.XPATH, f"//li[contains(text(), '{value}')]").click()


def confirm_save(driver: WebDriver) -> None:
    confirm_save_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    confirm_btn = confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
    confirm_btn.click()
    time.sleep(short_delay)


def create_pair_strat(driver: WebDriver, pair_strat: Dict) -> None:
    load_web_project(driver)

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

    more_options_btn = pair_strat_params_widget.find_element(By.XPATH, "//button[@aria-label='options']")
    more_options_btn.click()
    plus_icon = pair_strat_params_widget.find_element(By.CSS_SELECTOR, "div[class^='HeaderField_menu']")
    plus_icon.click()

    # select strat_leg1.side
    xpath = "pair_strat_params.strat_leg1.side"
    value = pair_strat["pair_strat_params"]["strat_leg1"]["side"]
    set_dropdown_field(widget=pair_strat_params_widget, xpath=xpath, name="side", value=value)

    # select strat_leg2.sec.sec_id
    xpath = "pair_strat_params.strat_leg2.sec.sec_id"
    value = pair_strat["pair_strat_params"]["strat_leg2"]["sec"]["sec_id"]
    set_autocomplete_field(widget=pair_strat_params_widget, xpath=xpath, name="sec_id", search_type=SearchType.NAME,
                           value=value)

    strat_status_widget = driver.find_element(By.ID, "strat_status")
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_status_widget)
    time.sleep(short_delay)

    # select pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat["pair_strat_params"]["common_premium"]
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name="common_premium", value=value,
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


def test_create_pair_strat(config_dict_, pair_strat):
    # load driver
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)

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


def activate_strat(driver: webdriver) -> None:
    # Find the button with the name 'strat_state'
    activate_btn = driver.find_element(By.XPATH, "//tbody//button[@value='Activate'][normalize-space()='Activate']")

    # Get the button text
    button_text = activate_btn.text

    # Check if the button text is ACTIVATE, ERROR, or PAUSED
    assert button_text in ["ACTIVATE", "ERROR", "PAUSE"], "Unknown button state."

    if button_text == "ACTIVATE":
        # Activate the strat
        activate_btn.click()
        time.sleep(short_delay)

        # Confirm the activation
        confirm_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
        confirm_btn.click()
        time.sleep(short_delay)

        # Verify if the strat is in active state
        pause_strat = driver.find_element(By.XPATH,
                                          "//tbody//button[@value='Pause'][normalize-space()='Pause']")
        btn_text = pause_strat.text
        assert btn_text == "PAUSE", "Failed to activate strat."

    elif button_text in ["ERROR", "PAUSE"]:
        print(f"Strat is in {button_text} state. Cannot activate.")


def update_max_value_field_strats_limits(widget: WebElement, xpath: str, name: str, input_value: int) -> None:
    input_div_xpath: str = f"//div[@data-xpath='{xpath}']"
    div_xpath = widget.find_element(By.XPATH, input_div_xpath)
    input_element = div_xpath.find_element(By.ID, name)
    input_element.click()
    input_element.send_keys(Keys.CONTROL+ "a")
    input_element.send_keys(Keys.BACK_SPACE)
    input_element.send_keys(input_value)


def test_update_pair_strat_create_n_activate_strat_limits_using_tree_view(config_dict_, pair_strat_edit: Dict, pair_strat: Dict,
                                                                          strat_limits:Dict):

    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)

    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()
    time.sleep(short_delay)

    # pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat_edit["pair_strat_params"]["common_premium"]
    name = "common_premium"
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value,
                    search_type=SearchType.ID)

    # pair_strat_params.hedge_ratio
    xpath = "pair_strat_params.hedge_ratio"
    value = pair_strat_edit["pair_strat_params"]["hedge_ratio"]
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name="hedge_ratio", value=value,
                    search_type=SearchType.ID)

    # scroll into view
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_limits_widget)
    time.sleep(short_delay)

    switch_layout(widget=strat_limits_widget, widget_name="strat_limits", layout=Layout.TREE)


    #
    xpath: str = "strat_limits.cancel_rate.max_cancel_rate"
    input_value: int = 20
    name: str = "max_cancel_rate"
    update_max_value_field_strats_limits(widget=strat_limits_widget, xpath=xpath, name=name, input_value=input_value)


    xpath: str = "strat_limits.market_trade_volume_participation.max_participation_rate"
    input_value: int = 30
    name: str = "max_participation_rate"
    update_max_value_field_strats_limits(widget=strat_limits_widget, xpath=xpath, name=name, input_value=input_value)

    # save
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    time.sleep(short_delay)
    confirm_save(driver=driver)
    edit_btn.click()
    create_strat_limits_using_tree_view(driver=driver, strat_limits=strat_limits, layout=Layout.TREE)

    # activate_strat
    activate_strat(driver=driver)

    # validate_strat_limits
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)
    driver.quit()



def create_strat_limits_using_tree_view(driver: WebDriver, strat_limits: Dict, layout: Layout) -> None:


    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    # creating_strat_of_strat_limits_in_tree_view
    # strat_limits.max_open_orders_per_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    name = "max_open_orders_per_side"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = strat_limits["max_cb_notional"]
    name = "max_cb_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)


    # strat_limits.max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    name = "max_open_cb_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name= name, value=value)

    # strat_limits.max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    name = "max_net_filled_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.max_concentration
    xpath = "strat_limits.max_concentration"
    value = strat_limits["max_concentration"]
    name = "max_concentration"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    name = "limit_up_down_volume_participation_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name,value=value)

    # strat_limits.cancel_rate.max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    name = "max_cancel_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)



    # applicable_period_seconds
    # xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    # value = strat_limits["cancel_rate"]["applicable_period_seconds"]
    if layout == Layout.NESTED:
        nested_tree_dialog = driver.find_element(By.XPATH, "//div[contains(@role,'dialog')]")
        input_residual_mark_second_element = nested_tree_dialog.find_element(By.ID, "residual_mark_seconds")
        driver.execute_script('arguments[0].scrollIntoView(true)', input_residual_mark_second_element)
        time.sleep(short_delay)

    else:
        strats_limits_widget = driver.find_element(By.ID, "strat_limits")
        input_residual_mark_second_element = strats_limits_widget.find_element(By.ID, "residual_mark_seconds")
        driver.execute_script('arguments[0].scrollIntoView(true)', input_residual_mark_second_element)
        time.sleep(short_delay)


    # strat_limits.cancel_rate.waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    name = "waived_min_orders"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.market_trade_volume_participation.max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    name = "max_participation_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # mrket_trde_applicable_periods_seconds
    # xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    # value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    # mrket_trde_applicable_periods_seconds = strat_limits_widget. \
    #     find_element(By.XPATH, "//div[@data-xpath='strat_limits."
    #                            "market_trade_volume_participation.applicable_period_seconds")
    # mrket_trde_applicable_periods_seconds.click()
    # set_input_field(widget=mrket_trde_applicable_periods_seconds, xpath=xpath, name="input", value=value,
    #                 search_type=SearchType.TAG_NAME)

    # strat_limits.market_depth.participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    name = "participation_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.market_depth.depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    name = "depth_levels"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.residual_restriction.max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    name = "max_residual"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.residual_restriction.residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    name = "residual_mark_seconds"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)




def get_value_from_input_field(widget: WebElement, xpath: str, layout: Layout):
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


def validate_strat_limits(widget: WebElement, strat_limits: Dict,  layout: Layout) -> None:
    # max_open_orders_per_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["max_open_orders_per_side"])

    # max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_cb_notional"])

    # max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_open_cb_notional"])

    # max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_net_filled_notional"])

    # max_concentration
    xpath = "strat_limits.max_concentration"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["max_concentration"])

    # limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath,layout=layout)
    assert value == str(strat_limits["limit_up_down_volume_participation_rate"])

    # max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["cancel_rate"]["max_cancel_rate"])

     # applicable_period_seconds
    # xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    # value = get_value_from_input_field(widget=widget, xpath=xpath, name="applicable_period_seconds", layout=layout)

    # waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["cancel_rate"]["waived_min_orders"])

    # max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_trade_volume_participation"]["max_participation_rate"])

    # applicable_period_seconds
    # xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    # value = get_value_from_input_field(widget=widget, xpath=xpath, name="applicable_period_seconds", layout=layout)

    # participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_depth"]["participation_rate"])

    # depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_depth"]["depth_levels"])

    # max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", "")
    assert value == str(strat_limits["residual_restriction"]["max_residual"])

    # residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["residual_restriction"]["residual_mark_seconds"])
    time.sleep(short_delay)


def set_table_input_field(widget: webdriver, xpath: str, value: str,
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



def test_update_strat_n_activate_using_table_view(config_dict_, pair_strat: Dict, strat_limits: Dict) -> None:
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)

    # strat_limits_widget
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")

    strat_collection_widget = driver.find_element(By.ID, "strat_collection")

    # edit_btn
    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()
    time.sleep(short_delay)

    # max_open_per_orders_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = strat_limits["max_cb_notional"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_concentration
    xpath = "strat_limits.max_concentration"
    value = strat_limits["max_concentration"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    value = strat_limits["cancel_rate"]["applicable_period_seconds"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)
    time.sleep(short_delay)

    # activate_n_confirm_btn
    activate_strat(driver=driver)
    # edit_btn
    edit_btn.click()

    # validating the values
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout= Layout.TABLE)



def open_setting(widget: WebElement, widget_name: str) -> None:
    xpath: str = f"//div[@id='{widget_name}']//button[@name='Settings']"
    setting_element = widget.find_element(By.XPATH, xpath)
    setting_element.click()
    time.sleep(short_delay)


def get_common_keys(widget: WebElement) -> List[str]:
    name: str = "span[class^='CommonKeyWidget_key']"
    common_key_elements: List[WebElement] = widget.find_elements(By.CSS_SELECTOR,name)
    key_element: WebElement
    common_keys: List[str] = [
        key_element.text.replace("common premium", "common_premium").replace("hedge ratio", "hedge_ratio")
        .replace(":", "")for key_element in common_key_elements]
    return common_keys


def select_n_unselect_checkbox(widget: webdriver, inner_text: str, partial_class_name: str) -> None:
    settings_dropdown: WebElement = widget.find_element(By.XPATH, "//ul[@role='listbox']")
    dropdown_labels: List[WebElement] = settings_dropdown.find_elements(By.CSS_SELECTOR,f"span[{partial_class_name}]")
    span_element: WebElement
    for span_element in dropdown_labels:
        if span_element.text == inner_text:
            span_element.click()
            time.sleep(delay)
            break



def test_field_hide_n_show_in_common_key(config_dict_, pair_strat: Dict):
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    pair_strat_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_widget, widget_name="pair_strat_params", layout=Layout.TABLE)


    common_keys: List[str] = get_common_keys(widget=pair_strat_widget)
    # select a random value
    inner_text: str = random.choice(common_keys)


    # searching the random key in setting and unselecting checkbox
    open_setting(widget=pair_strat_widget, widget_name="pair_strat_params")
    partial_class_name = "class^='MuiTypography-root'"
    select_n_unselect_checkbox(widget=pair_strat_widget, inner_text=inner_text, partial_class_name=partial_class_name)


     # validating that unselected key is not visible on table view
    common_keys: List[str] = get_common_keys(widget=pair_strat_widget)
    assert inner_text not in common_keys, f"{inner_text} field is visible in common keys, expected to be hidden"


    #  searching the random key in setting and selecting checkbox
    open_setting(widget=pair_strat_widget, widget_name="pair_strat_params")
    partial_class_name = "class^='MuiTypography-root'"
    select_n_unselect_checkbox(widget=pair_strat_widget, inner_text=inner_text, partial_class_name=partial_class_name)


    # validating that selected checkbox is visible on table view
    common_keys = get_common_keys(widget=pair_strat_widget)
    assert inner_text in common_keys, f"{inner_text} field is not visible in common keys, expected to be visible"



def get_table_headers(widget: WebElement) -> list:
    name: str = "span[class^='MuiButtonBase-root']"
    span_elements: List[WebElement] = widget.find_elements(By.CSS_SELECTOR, name)
    table_headers: List[str] = [span_element.text.replace(" ", "_") for span_element in span_elements]
    return table_headers



def test_hide_n_show_in_table_view(config_dict_, pair_strat: Dict):
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    activate_strat(driver=driver)

    symbol_side_snapshot_widget = driver.find_element(By.ID, "symbol_side_snapshot")
    driver.execute_script('arguments[0].scrollIntoView(true)', symbol_side_snapshot_widget)


    # selecting random table text from table view
    table_headers = get_table_headers(widget=symbol_side_snapshot_widget)
    inner_text = random.choice(table_headers)


    #  searching the selected random table text in setting and unselecting checkbox
    open_setting(widget=symbol_side_snapshot_widget, widget_name="symbol_side_snapshot")
    partial_class_name = "class^='MuiTypography-root'"
    select_n_unselect_checkbox(widget=symbol_side_snapshot_widget, inner_text=inner_text, partial_class_name=partial_class_name)


    # validating that unselected text is not visible on table view
    table_headers: List[str] = get_table_headers(widget=symbol_side_snapshot_widget)
    assert inner_text not in table_headers

    # searching the random table text in setting and selecting checkbox
    open_setting(widget=symbol_side_snapshot_widget, widget_name="symbol_side_snapshot")
    partial_class_name = "class^='MuiTypography-root'"
    select_n_unselect_checkbox(widget=symbol_side_snapshot_widget, inner_text=inner_text, partial_class_name=partial_class_name)


    # validating that selected check is visible on table view
    table_headers: List[str] = get_table_headers(widget=symbol_side_snapshot_widget)
    assert inner_text in table_headers


def verify_whether_field_is_enabled_or_not_in_table_layout(widget: WebElement, parital_class_name: str)-> None:
    partial_css_selector: str = f"td[class^='{parital_class_name}']"
    td_elements = widget.find_elements(By.CSS_SELECTOR, partial_css_selector)
    for td_element in td_elements:
        td_element = td_element.is_enabled()
        assert td_element == True, "NOT ENABLED"




def test_nested_pair_strat_n_strats_limits(config_dict_, pair_strat: Dict, pair_strat_edit: Dict, strat_limits: Dict):
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)


    create_pair_strat(driver=driver, pair_strat=pair_strat)


    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_params_widget, widget_name="pair_strat_params", layout=Layout.TABLE)

    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()

    # check_whether_input_field_is_enabled_or_not_in_pair_strat_params
    pair_strat_td_elements = pair_strat_params_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    verify_whether_field_is_enabled_or_not_in_table_layout(widget=pair_strat_params_widget, parital_class_name="MuiTableCell-root")


    # perform_double_click
    actions = ActionChains(driver)
    actions.double_click(pair_strat_td_elements[9]).perform()

    # dialog
    nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")

    # update_value_in_nested_tree_layout
    # select pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat["pair_strat_params"]["common_premium"]
    set_tree_input_field(widget=nested_tree_dialog, xpath=xpath, name="common_premium", value=value,search_type=SearchType.ID)
    # pair_strat_params.hedge_ratio
    xpath = "pair_strat_params.hedge_ratio"
    value = pair_strat_edit["pair_strat_params"]["hedge_ratio"]
    set_tree_input_field(widget=nested_tree_dialog, xpath=xpath, name="hedge_ratio", value=value,search_type=SearchType.ID)

    # save strat
    save_strat = nested_tree_dialog.find_element(By.NAME, "Save")
    save_strat.click()

    strat_limits_td_elements = strat_limits_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    # perform_double_click
    actions.double_click(strat_limits_td_elements[0]).perform()

    create_strat_limits_using_tree_view(driver=driver, strat_limits=strat_limits, layout=Layout.NESTED)

    # save_nested_strat
    nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    save_strat = nested_tree_dialog.find_element(By.NAME, "Save")
    save_strat.click()

    # perform_double_click
    actions.double_click(strat_limits_td_elements[0]).perform()

    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)


def get_widget_type(widget_schema: Dict) -> WidgetType | None:
    layout: str = widget_schema['widget_ui_data']["layout"]
    is_repeated: bool = True if widget_schema["widget_ui_data"].get("is_repeated") else False
    is_json_root: bool = True if widget_schema.get("json_root") else False

    if layout in ["UI_TREE", "UI_TABLE"] and is_json_root:
        if is_repeated:
            return WidgetType.REPEATED_INDEPENDENT
        else:
            return WidgetType.INDEPENDENT
    elif layout in ["UI_TREE", "UI_TABLE"] and not is_json_root:
        if is_repeated:
            return WidgetType.REPEATED_DEPENDENT
        else:
            return WidgetType.DEPENDENT
    return None


def get_widgets_by_flux_property(schema_dict: Dict[str, any], widget_type: WidgetType,
                                 flux_property: str) -> Tuple[bool, List[WidgetQuery] | None]:
    """
    Method to find widgets and fields containing the flux_property
    schema_dict: JSON schema dict
    widget_type: type of widget to search
    flux_property: property or attribute to search in fields
    """

    def search_schema_for_flux_property(current_schema: Dict[str, any]) -> None:
        properties: Dict[str, any] = current_schema["properties"]
        field: str
        field_properties: Dict[str, any]
        for field, field_properties in properties.items():
            if field_properties["type"] in simple_data_type_list:
                if flux_property in field_properties:
                    field_queries.append(FieldQuery(field_name=field, properties=field_properties))
            elif field_properties["type"] in ["object", "array"]:
                if field_properties.get("underlying_type") is not None and \
                        field_properties["underlying_type"] in simple_data_type_list:
                    continue
                ref_path: str = field_properties["items"]["$ref"]
                ref_list: List[str] = ref_path.split("/")[1:]
                child_schema: Dict[str, any] = schema_dict[ref_list[0]][ref_list[1]] if len(ref_list) == 2 \
                    else schema_dict[ref_list[0]]
                search_schema_for_flux_property(child_schema)

    widget_queries: List[WidgetQuery] = []
    widget_name: str
    widget_schema: Dict[str, any]
    for widget_name, widget_schema in schema_dict.items():
        # ignore the schema definitions and autocomplete list. remaining all top level keys are widgets
        if widget_name in ["definitions", "autocomplete"]:
            continue

        current_schema_widget_type: WidgetType = get_widget_type(widget_schema)
        if current_schema_widget_type == widget_type:
            field_queries: List[FieldQuery] = []
            search_schema_for_flux_property(widget_schema)
            if field_queries:
                widget_query: WidgetQuery = WidgetQuery(widget_name=widget_name, fields=field_queries)
                widget_queries.append(widget_query)

    if widget_queries:
        return True, widget_queries
    return False, None


def test_widget_type(schema_dict: Dict[str, any]):
    result = get_widgets_by_flux_property(schema_dict, WidgetType.INDEPENDENT, "no_common_key")
    print(result)


def get_form_validation_dialog_n_text(widget: WebElement) -> List:
    form_validation_dialog: WebElement = widget.find_element(By.XPATH, "//div[@role='dialog']")
    form_validation_dialog_elements: List[WebElement] = form_validation_dialog.find_elements(By.CLASS_NAME, "object-key")
    form_validation_text_list: [str] = []
    for form_validation_dialog_element in form_validation_dialog_elements:
            form_validation_text_list.append(form_validation_dialog_element.text[1:-1])
    return form_validation_text_list


def get_xpath_from_field_name(schema, widget_type: WidgetType, widget_name: str, field_name: str):

    properties: Dict[str, any] = schema[widget_name]["properties"]
    field: str
    field_properties: Dict[str, any]
    for field, field_properties in properties.items():
        if field_properties["type"] in ["string", "number", "date_time", "enum", "boolean"]:
            if field_name == field and widget_type == WidgetType.INDEPENDENT:
                return field
            if field_name == field and widget_type == WidgetType.DEPENDENT:
                return f"{widget_name}.{field_name}"
        elif field_properties["type"] in ["object", "array"]:
            ref_path: str = field_properties["items"]["$ref"]
            ref_list: List[str] = ref_path.split("/")[1:]
            child_schema: Dict[str, any] = schema[ref_list[0]][ref_list[1]] if len(ref_list) == 2 \
                else schema[ref_list[0]]
            return get_xpath_from_field_name(schema, widget_type, ref_list[-1], field_name)


def get_schema_file():
    schema_path: PurePath = PurePath(
        __file__).parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "addressbook" / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "r") as f:
        schema_dict: Dict[str, any] = json.loads(f.read())
        return schema_dict


def test_demo():
    result = get_widget_by_flux_property(WidgetType.DEPENDENT, "number_format")

    schema_path: PurePath = PurePath(
        __file__).parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "addressbook" / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "r") as f:
        schema_dict: Dict[str, any] = json.loads(f.read())


    widget_name: str = result[1]
    field_name: str = result[2]
    xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                      field_name=field_name)
    print(xpath)


def test_flux_fld_val_max_in_independent_widget(config_dict_, pair_strat: Dict):
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    # TODO: fix order limits, portfolio limits and pair strat such that default values does not fail validation
    result = get_widget_by_flux_property(WidgetType.INDEPENDENT, "val_max")
    print(result)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True


    widget_name: str = result[1]
    field_name: str = result[2]
    xpath =get_xpath_from_field_name(widget_type=WidgetType.INDEPENDENT,widget_name=widget_name, field_name=field_name)


    widget = driver.find_element(By.ID, widget_name)
    edit_btn = widget.find_element(By.NAME, "Edit")
    edit_btn.click()

    # TODO: do not make assumptions that layout if table by default.

    # table_layout_above_val_max
    val_max: int = result[3]['val_max'] + 50
    set_table_input_field(widget=widget, xpath=field_name, value=val_max, search_type=SearchType.TAG_NAME)
    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name in form_validation_text_list

    # table_layout_val_max
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()
    val_max: int = result[3]['val_max']
    set_table_input_field(widget=widget, xpath=field_name, value=val_max, search_type=SearchType.TAG_NAME)

    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    # TODO: form validation should not fail
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name not in form_validation_text_list

    # tree_layout_above_val_max
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()
    val_max: int = result[3]['val_max'] + 50
    switch_layout(widget=widget, widget_name="order_limits", layout=Layout.TREE)
    set_tree_input_field(widget=widget, xpath=field_name, name="max_basis_points", value=val_max)
    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name in form_validation_text_list

    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()


    # tree_layout_val_max
    val_max: int = result[3]['val_max']
    set_tree_input_field(widget=widget, xpath=field_name, name="max_basis_points", value=val_max)
    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name not in form_validation_text_list



def test_flux_fld_val_max_in_dependent_widget(config_dict_, pair_strat: Dict):
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    result = get_widget_by_flux_property(WidgetType.DEPENDENT, "number_format")
    print(result)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True

    widget_name: str = result[1]
    field_name: str = result[2]
    xpath = get_xpath_from_field_name(widget_type=WidgetType.DEPENDENT, flux_property="val_max")

    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    widget = driver.find_element(By.ID, widget_name)
    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()

  # table_layout_above_val_max
    val_max: int = result[3]['val_max'] + 5
    set_table_input_field(widget=widget, xpath=xpath, value=val_max, search_type=SearchType.TAG_NAME)
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert xpath in form_validation_text_list

    # table_layout_val_max
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()
    val_max: int = result[3]['val_max']
    set_table_input_field(widget=widget, xpath=xpath, value=val_max, search_type=SearchType.TAG_NAME)

    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert xpath not in form_validation_text_list

    # tree_layout_above_val_max
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()
    val_max: int = result[3]['val_max'] + 5
    switch_layout(widget=widget, widget_name="strat_limits", layout=Layout.TREE)
    set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=val_max)
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert xpath in form_validation_text_list

    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()


    # tree_layout_val_max
    val_max: int = result[3]['val_max']
    set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=val_max)
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert xpath not in form_validation_text_list




def test_flux_fld_val_min_in_independent_widget(config_dict_, pair_strat: Dict):
    result = get_widget_by_flux_property(widget_type=WidgetType.INDEPENDENT, flux_property="val_min")
    print(result)
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True

    widget_name: str = result[1]
    field_name: str = result[2]
    xpath: str = get_xpath_from_field_name(widget_type=WidgetType.INDEPENDENT, flux_property="val_min")

    widget = driver.find_element(By.ID, widget_name)
    edit_btn = widget.find_element(By.NAME, "Edit")
    edit_btn.click()

    # table_layout_above_val_min
    val_min: int = result[3]['val_min'] - 500
    set_table_input_field(widget=widget, xpath=field_name, value=val_min, search_type=SearchType.TAG_NAME)
    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name in form_validation_text_list

    # table_layout_val_min
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH,
                                                               "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()
    val_min: int = result[3]['val_min']
    set_table_input_field(widget=widget, xpath=field_name, value=val_min, search_type=SearchType.TAG_NAME)

    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name not in form_validation_text_list

    # tree_layout_above_val_min
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH,
                                                               "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()
    val_min: int = result[3]['val_min'] - 500
    switch_layout(widget=widget, widget_name="order_limits", layout=Layout.TREE)
    set_tree_input_field(widget=widget, xpath=field_name, name=field_name, value=val_min)
    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name in form_validation_text_list

    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(By.XPATH,
                                                               "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()

    # tree_layout_val_min
    val_min: int = result[3]['val_min']
    set_tree_input_field(widget=widget, xpath=field_name, name=field_name, value=val_min)
    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    form_validation_text_list = get_form_validation_dialog_n_text(widget=widget)
    assert field_name not in form_validation_text_list


def test_flux_fld_help_in_independent_widget(config_dict_, pair_strat: Dict):
    result = get_widget_by_flux_property(widget_type=WidgetType.INDEPENDENT, flux_property="help")
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True

    widget_name: str = result[1]
    help_text : str = result[3]['help']

    # table_layout
    widget = driver.find_element(By.ID, widget_name)
    setting_btn = widget.find_element(By.NAME, "Settings")
    setting_btn.click()

    setting_dropdown = widget.find_element(By.XPATH, "//ul[@role='listbox']")
    button_element = setting_dropdown.find_element(By.TAG_NAME, "button")
    actions = ActionChains(driver)

    # Move the mouse to the element
    actions.move_to_element(button_element).perform()
    tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")

    hovered_element_text = tooltip_element.text
    assert hovered_element_text == help_text

    # tree_layout
    tooltip_element.click()
    time.sleep(short_delay)
    switch_layout(widget=widget, widget_name="order_limits", layout=Layout.TREE)
    field_element = widget.find_element(By.CLASS_NAME, "Node_container__tbTZ3")
    button_element = field_element.find_element(By.TAG_NAME, "button")
    actions.move_to_element(button_element).perform()

    tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
    hovered_element_text = tooltip_element.text
    time.sleep(short_delay)
    assert hovered_element_text == help_text



def test_flux_fld_help_in_dependent_widget(config_dict_, pair_strat: Dict):
    result = get_widget_by_flux_property(widget_type=WidgetType.DEPENDENT, flux_property="help")
    print(result)
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True

    widget_name: str = result[1]
    help_text : str = result[3]['help']

    widget = driver.find_element(By.ID, widget_name)
    # table_layout
    widget = driver.find_element(By.ID, widget_name)
    setting_btn = widget.find_element(By.NAME, "Settings")
    setting_btn.click()

    setting_dropdown = widget.find_element(By.XPATH, "//ul[@role='listbox']")
    button_element = setting_dropdown.find_elements(By.TAG_NAME, "button")
    actions = ActionChains(driver)

    # Move the mouse to the element
    actions.move_to_element(button_element[0]).perform()
    tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")

    hovered_element_text = tooltip_element.text
    assert hovered_element_text == help_text

    # tree_layout
    # tooltip_element.click()
    # time.sleep(short_delay)






def test_flux_fld_display_type_in_independent_widget(config_dict_, pair_strat: Dict):
    result = get_widget_by_flux_property(widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
    print(result)
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True

    widget_name: str = result[1]
    field_name: str = result[2]
    display_type : int = result[3]['display_type']

     # table_layout
    widget = driver.find_element(By.ID, widget_name)
    edit_btn = widget.find_element(By.NAME, "Edit")
    edit_btn.click()

    # TODO: first two field should be remove later in both layout which contains value int type
    #max_basis_points
    xpath: str = "max_basis_points"
    value: int = 1000
    set_table_input_field(widget=widget, xpath=xpath, value=value)

    # max_px_deviation
    xpath: str = "max_px_deviation"
    value: int = 2
    set_table_input_field(widget=widget, xpath=xpath, value=value)

    # min_order_notinal
    value: int = 1000.33
    set_table_input_field(widget=widget, xpath=field_name, value=value)

    save_btn = widget.find_element(By.NAME, "Save")
    save_btn.click()
    confirm_save(driver=driver)

    common_key_elements = widget.find_elements(By.CLASS_NAME, "CommonKeyWidget_item__QEVHl")
    common_key_txt = common_key_elements[-2].text.split(":")
    common_key_txt.append(common_key_txt[-1].replace(",", ""))
    display_type_txt = type(int(common_key_txt[-1]))


    assert common_key_txt[0].replace(" ", "_") == field_name
    # assert display_type_txt.replace("<class ", "").replace(">", "") == display_type
    # assert display_type_txt == "<class 'int'>"

    # tree_layout
    switch_layout(widget=widget, widget_name="order_limits", layout=Layout.TREE)
    # max_basis_points
    xpath: str = "max_basis_points"
    value: int = 1000
    name: str = "max_px_deviation"
    set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)
    # max_px_deviation
    xpath: str = "max_px_deviation"
    value: int = 2
    name: str = "max_px_deviation"
    set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)
    # min_order_notinal
    value: int = 1000.33
    set_tree_input_field(widget=widget, xpath=field_name, name=field_name, value=value)
    save_btn.click()
    activate_strat(driver=driver)

    edit_btn.click()
    min_order_notinal_val = widget.find_element(By.ID, "max_order_notional").get_attribute('value')
    min_order_notinal_val = int(min_order_notinal_val)

    # assert type(min_order_notinal_val) ==  "<class 'int'>"



def test_flux_fld_display_type_in_dependent_widget(config_dict_, pair_strat: Dict):
    result = get_widget_by_flux_property(widget_type=WidgetType.DEPENDENT, flux_property="display_type")
    print(result)
    driver_type: DriverType = DriverType.CHROME
    driver: webdriver.Chrome = get_driver(config_dict=config_dict_, driver_type=driver_type)
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    assert result[0] == True

    widget_name: str = result[1]
    field_name: str = result[2]
    display_type : int = result[3]['display_type']



















































































