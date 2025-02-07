# third par
from logging import raiseExceptions
from operator import index, indexOf
from typing import Optional, Union
import pyperclip
from selenium import webdriver
from selenium.webdriver import ChromeOptions, EdgeOptions, FirefoxOptions
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC  # noqa

from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.conftest import expected_pair_plan
# project import
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.web_ui_models import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import \
    test_config_file_path, \
    email_book_service_native_web_client, create_tob
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.web_ui_models import WidgetName

SIMPLE_DATA_TYPE_LIST: Final[List[DataType]] = \
    [DataType.STRING, DataType.BOOLEAN, DataType.NUMBER, DataType.DATE_TIME, DataType.ENUM]
COMPLEX_DATA_TYPE_LIST: Final[List[DataType]] = [DataType.OBJECT, DataType.ARRAY]


def get_driver(config_dict: Dict, driver_type: DriverType) -> WebDriver:
    driver_path: str | None = config_dict["driver"].get(driver_type)
    assert driver_path is not None, f"unsupported driver_type: {driver_type}"
    driver: Optional[WebDriver] = None
    match driver_type:
        case DriverType.CHROME:
            options = ChromeOptions()
            # options.add_argument("--headless=new")
            driver: webdriver.Chrome = webdriver.Chrome(driver_path, chrome_options=options)
        case DriverType.EDGE:
            options = EdgeOptions()
            options.add_argument("--headless=new")
            driver: webdriver.Edge = webdriver.Edge(driver_path)
        case DriverType.FIREFOX:
            options = FirefoxOptions()
            options.add_argument("--headless=new")
            driver: webdriver.Firefox = webdriver.Firefox(driver_path)
        case DriverType.SAFARI:
            # SAFARI browser not supports headless mode
            driver: webdriver.Safari = webdriver.Safari(driver_path)
    assert driver is not None, f"failed to initialize webdriver for driver_type: {driver_type}"
    return driver


def wait(driver: WebDriver, delay: Delay) -> WebDriverWait:
    # noinspection PyTypeChecker
    return WebDriverWait(driver, delay)

def click_more_all_inside_setting(driver: WebDriver, widget_name: str):
    widget = get_setting_tooltip_widget(driver, widget_name)
    click_button_with_name(widget, "MoreLessAll")


def get_web_project_url():
    web_project_url: str = "http://localhost:3020"
    if os.path.isfile(str(test_config_file_path)):
        test_config = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
        web_project_url = url if (url := test_config.get("web_project_url")) is not None else web_project_url
    return web_project_url


def create_pair_plan(driver: WebDriver, pair_plan: Dict[str, any], expected_pair_plan) -> None:
    plan_collection_widget = driver.find_element(By.ID, "plan_collection")
    scroll_into_view(driver=driver, element=plan_collection_widget)
    click_button_with_name(widget=plan_collection_widget, button_name="Create")

    widget = driver.find_element(By.ID, "pair_plan_params")

    # select plan_leg1.sec.sec_id
    # xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
    #                                        widget_name=widget_name, field_name=field_name)
    # TODO: GET XPATH FROM THE METHOD
    xpath = "pair_plan_params.plan_leg1.sec.sec_id"
    value = pair_plan["pair_plan_params"]["plan_leg1"]["sec"]["sec_id"]
    name = "sec_id"
    autocomplete_attribute_value= f"{value}-option-0"
    set_autocomplete_field(driver=driver, widget=widget, xpath=xpath, name=name, search_type=SearchType.ID,
                           value=value)

    # select plan_leg1.side
    xpath = "pair_plan_params.plan_leg1.side"
    value = pair_plan["pair_plan_params"]["plan_leg1"]["side"]
    name = "side"
    set_dropdown_field(widget=widget, xpath=xpath, name=name, value=value)

    xpath = "pair_plan_params.plan_leg2"
    show_nested_fld_in_tree_layout(widget=widget, driver=driver)

    # select plan_leg2.sec.sec_id
    xpath = "pair_plan_params.plan_leg2.sec.sec_id"
    value = pair_plan["pair_plan_params"]["plan_leg2"]["sec"]["sec_id"]
    name = "sec_id"
    # autocomplete_attribute_value = f"{value}-option-0"
    set_autocomplete_field(driver=driver, widget=widget, xpath=xpath, name=name, search_type=SearchType.ID,
                           value=value)

    plan_status_widget = driver.find_element(By.ID, "plan_status")
    scroll_into_view(driver=driver, element=plan_status_widget)

    # select pair_plan_params.common_premium
    xpath = "pair_plan_params.common_premium"
    value = pair_plan["pair_plan_params"]["common_premium"]
    name = "common_premium"
    set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

    click_save_n_click_confirm_save_btn(driver, plan_collection_widget)
    time.sleep(Delay.SHORT.value)
    click_id_fld_inside_plan_collection(plan_collection_widget)
    validate_pair_plan_params(widget=widget, pair_plan=pair_plan, layout=Layout.TREE, expected_pair_plan=expected_pair_plan)

    host: str = "127.0.0.1"
    port: int = 8020
    email_book_service_http_client = EmailBookServiceHttpClient(host, port)
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_http_client.get_all_pair_plan_client()
    pair_plan: PairPlanBaseModel = pair_plan_list[-1]

    while not pair_plan.is_partially_running:
        pair_plan_list = email_book_service_http_client.get_all_pair_plan_client()
        pair_plan = pair_plan_list[-1]
        time.sleep(Delay.DEFAULT.value)

    assert pair_plan.is_partially_running

    executor_web_client = StreetBookServiceHttpClient(pair_plan.host, pair_plan.port)
    symbol_overview_obj_list: List[SymbolOverviewBaseModel] = symbol_overview_list()
    for symbol_overview in symbol_overview_obj_list:
        executor_web_client.create_symbol_overview_client(symbol_overview)

    while not pair_plan.is_executor_running:
        pair_plan_list = email_book_service_http_client.get_all_pair_plan_client()
        pair_plan = pair_plan_list[-1]
        time.sleep(Delay.DEFAULT.value)

    assert pair_plan.is_executor_running
    # fetch plan limits and plan status from executor client by pair plan id
    # plan_limits: PlanLimitsBaseModel = executor_web_client.get_plan_limits_client(pair_plan.id)
    # plan_status: PlanStatusBaseModel = executor_web_client.get_plan_status_client(pair_plan.id)
    override_plan_limit(executor_web_client)
    # TODO LAZY: plan limits, plan status and plan alert is present in ui
    time.sleep(Delay.MEDIUM.value)


def generate_xpath(data: dict, search_key: str, base_xpath: str = "") -> str:
    for key, value in data.items():
        current_xpath = f"{base_xpath}.{key}" if base_xpath else key
        if key == search_key:
            return current_xpath
        elif isinstance(value, dict):
            # Recurse into the nested dictionary
            result = generate_xpath(value, search_key, current_xpath)
            if result:
                return result
    return ""  # Return an empty string if the key is not found


def verify_supported_search_type(search_type: SearchType = SearchType.NAME) -> bool:
    if not hasattr(By, search_type):
        raise Exception(f"unsupported search type: {search_type}")
    else:
        return True


def click_id_fld_inside_plan_collection(widget: WebElement):
    # TODO LAZY: in pair plan widget not showing the created pair plan fields after saving, we have to click inside plan collection widget
    # widget.find_element(By.XPATH, get_table_input_field_xpath("_id")).click()
    xpath = get_table_input_field_xpath("total_fill_sell_notional")
    widget.find_element(By.XPATH, xpath).click()



def get_tree_input_field_xpath(xpath: str, data_add: bool = False) -> str:
    if data_add:
        return f"//button[@data-add='{xpath}']"
    return f"//div[@data-xpath='{xpath}']"


def get_xpath_with_attribute(tag_name: str, attribute_name: str, attribute_value: str) -> str:
    """
    Generates an XPath for a given tag name with a specified attribute and value.

    Args:
        tag_name (str): The HTML tag name (e.g., 'button', 'div', '*').
        attribute (str): The attribute to match (e.g., 'aria-label', 'id', 'class').
        attribute_value (str): The value of the attribute to match.

    Returns:
        str: The generated XPath string.
    """
    return f"//{tag_name}[@{attribute_name}='{attribute_value}']"


# Example usage
xpath = get_xpath_with_attribute("button", "aria-label", "More Options")
print(xpath)  # Output: //button[@aria-label='More Options']


def set_tree_input_field(driver, widget: WebElement, xpath: str, name: str, value: str="",
                         search_type: SearchType = SearchType.NAME, autocomplete: bool = False) -> None:
    if verify_supported_search_type(search_type):
        xpath_element = get_tree_layout_xpath_element(widget, xpath)
        input_element = xpath_element.find_element(getattr(By, search_type), name)
        input_element.click()
        delete_data_from_input_fld(driver, input_element=input_element)
        input_element.send_keys(value)
        if autocomplete:
            input_element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
        # else not required
    # else not required



def get_data_value_xpath(tag_name: str):
    return f"//{tag_name}[@attribute_name='data-value']"


def get_autocomplete_value_xpath(autocomplete_attribute_value: str):
      return f"//li[@data-value='{autocomplete_attribute_value}']"


def click_save_n_short_delay(widget: WebElement) -> None:
    widget.find_element(By.NAME, "Save").click()
    time.sleep(Delay.SHORT.value)


call_counter = 0

def set_ui_chart_fields(driver: WebDriver, nested_fld_widget: WebElement, ui_chart: Dict[str, any]):
    global call_counter
    index_num = 0
    if call_counter == 2:
        index_num = 1

    # chart_name
    chart_name_value = ui_chart["chart_data"]["chart_name"]
    set_tree_input_field(driver=driver, widget=nested_fld_widget, xpath="chart_name", name="chart_name",
                         value=chart_name_value)

    # fld_name
    fld_name_value = ui_chart["filters"]["fld_name"][index_num]
    xpath = "filters[0].fld_name"
    name = "fld_name"
    set_autocomplete_field(driver=driver, widget=nested_fld_widget, xpath=xpath, name=name, value=fld_name_value)

    # fld_value
    fld_value_value = ui_chart["filters"]["fld_value"][index_num]
    xpath = "filters[0].fld_value"
    name = "fld_value"
    set_autocomplete_field(driver=driver, widget=nested_fld_widget, xpath=xpath, name=name, value=fld_value_value)

    # partition_fld field
    partition_fld_value = ui_chart["filters"]["partition_fld"][index_num]
    xpath = "partition_fld"
    set_autocomplete_field(driver=driver, widget=nested_fld_widget, xpath=xpath, name=xpath, value=partition_fld_value)

    # type field
    type_value = ui_chart["series"]["type"][index_num]
    xpath = "series[0].type"
    name = "type"
    set_dropdown_field(widget=nested_fld_widget, xpath=xpath, name=name, value=type_value)

    # x field
    x_value = ui_chart["encode"]["x"][index_num]
    xpath = "series[0].encode.x"
    name = "x"
    set_autocomplete_field(driver=driver, widget=nested_fld_widget, xpath=xpath, name=name,
                           value=x_value)

    # y field
    y_value = ui_chart["encode"]["y"][index_num]
    xpath = "series[0].encode.y"
    name = "y"
    set_autocomplete_field(driver=driver, widget=nested_fld_widget, xpath=xpath, name=name,
                           value=y_value)

    # If you want to reset the counter after two calls, reset it here
    if call_counter >= 2:
        call_counter = 0


def validate_ui_chart(chart_n_layout_name: str, chart_name_txt: str, ui_chart):
    assert chart_n_layout_name == chart_name_txt

    ui_layout: UILayoutBaseModel = (
        email_book_service_native_web_client.
        get_ui_layout_from_index_client(profile_id=chart_n_layout_name)[-1])

    print(f"ui_layout: {ui_layout}")
    assert ui_layout.profile_id == chart_n_layout_name

    widget_ui_data_elements: List[WidgetUIDataElementOptional] = ui_layout.widget_ui_data_elements

    for widget_ui_data_element in widget_ui_data_elements:
        if widget_ui_data_element.i == "market_depth":
            assert widget_ui_data_element.i == "market_depth"
            # use the expected chart data dict to verify
            assert widget_ui_data_element.chart_data[-1].chart_name == chart_n_layout_name
            assert widget_ui_data_element.chart_data[-1].partition_fld == ui_chart["symbol"]
            assert widget_ui_data_element.chart_data[-1].series[-1].type == ui_chart["bar"]


def get_tree_layout_xpath_element(widget: WebElement, xpath: str) -> WebElement:
    xpath: str = get_tree_input_field_xpath(xpath=xpath)
    xpath_element = widget.find_element(By.XPATH, xpath)
    return xpath_element


def set_table_input_field(driver: WebDriver, widget: webdriver, xpath: str, value: str,
                          search_type: SearchType = SearchType.TAG_NAME, field_type: FieldType=None) -> None:
    input_element: List[bool, WebElement] = is_table_cell_enabled_n_get_input_element(widget=widget, xpath=xpath)
    if input_element[0]:
        if verify_supported_search_type(search_type):
            delete_data_from_input_fld(driver, input_element[1], field_type)
            input_element[1].send_keys(value)


def click_n_get_xpath_element_for_layout(widget: WebElement, layout: Layout, xpath: str) -> WebElement:
    xpath_element = get_xpath_element_for_layout(widget, xpath, layout)
    xpath_element.click()
    time.sleep(Delay.SHORT.value)
    return xpath_element


def delete_data_from_input_fld(driver: WebDriver, input_element: WebElement, field_type: FieldType=None) -> None:
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    time.sleep(Delay.SHORT.value)


def get_xpath_element_for_layout(widget: WebElement, xpath: str, layout: Layout) -> WebElement:
    if layout == Layout.TABLE:
        xpath: str = get_table_input_field_xpath(xpath=xpath)
    else:
        xpath: str = get_tree_input_field_xpath(xpath=xpath)
    xpath_element: WebElement = widget.find_element(By.XPATH, xpath)
    return xpath_element


def set_input_field_on_layout(driver: WebDriver, widget, layout, xpath, field_name, value):
    """Set input field based on layout."""
    if layout == Layout.TABLE:
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)
    else:
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=field_name, value=value)


def get_table_input_field_xpath(xpath: str) -> str:
    return f"//td[@data-xpath='{xpath}']"


def set_autocomplete_field(driver, widget: WebElement, xpath: str, name: str,
                           search_type: SearchType = SearchType.NAME, value: str="") -> None:

    autocomplete_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    autocomplete_element = widget.find_element(By.XPATH, autocomplete_xpath)
    assert autocomplete_element is not None, f"autocomplete element not found for xpath: {xpath}, name: {name}"
    set_tree_input_field(driver, widget=autocomplete_element, xpath=xpath, name=name, value=value, search_type=search_type,
                         autocomplete=True)


def set_dropdown_field(widget: WebElement, xpath: str, name: str, value: str) -> None:
    xpath_element = get_dropdown_xpath_element(widget, xpath)
    dropdown = xpath_element.find_element(By.ID, name)
    dropdown.click()
    dropdown.find_element(By.XPATH, f"//li[contains(text(), '{value}')]").click()


def get_dropdown_xpath_element(widget: WebElement, xpath: str) -> WebElement:
    dropdown_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    dropdown_element = widget.find_element(By.XPATH, dropdown_xpath)
    return dropdown_element



# Function to generate XPaths from the fixture
def generate_xpath_from_fixture(data_dict: Dict[str, any], base_path: str = "") -> List[str]:
    xpaths = []
    for key, value in data_dict.items():
        # Build the current XPath by appending the current key
        current_xpath = f"{base_path}.{key}" if base_path else key

        # If the value is a nested dictionary, recursively call the function
        if isinstance(value, dict):
            xpaths.extend(generate_xpath_from_fixture(data_dict=value, base_path=current_xpath))
        else:
            # Append the final path
            xpaths.append(current_xpath)

    return xpaths


def validate_pair_plan_params(widget: WebElement, pair_plan: Dict[str, any], layout: Layout,
                               expected_pair_plan: Dict[str, any]) -> None:
    xpaths = generate_xpath_from_fixture(pair_plan)

    for xpath in xpaths:
        xpath_element = get_xpath_element_for_layout(widget=widget, xpath=xpath, layout=layout)
        created_value = get_value_frm_input_fld_with_input_tag(xpath_element, layout)

        # Get the expected value based on the current xpath
        expected_value = expected_pair_plan.get(xpath)

        # Assert that the created value matches the expected value
        assert created_value == str(expected_value), \
            f"Mismatch in value for {xpath}: expected {expected_value}, but got {created_value}"


def update_max_value_field_plan_limits(widget: WebElement, xpath: str, name: str, input_value: int) -> None:
    input_div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    div_xpath = widget.find_element(By.XPATH, input_div_xpath)
    input_element = div_xpath.find_element(By.ID, name)
    input_element.click()
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    input_element.send_keys(input_value)


def create_plan_limits_using_tree_view(driver: WebDriver, plan_limits: Dict, layout: Layout) -> None:
    plan_limit_widget = driver.find_element(By.ID, "plan_limits")

    fields_xpath_n_value = {
        "max_open_chores_per_side": plan_limits["max_open_chores_per_side"],
        "max_single_leg_notional": plan_limits["max_single_leg_notional"],
        "max_open_single_leg_notional": plan_limits["max_open_single_leg_notional"],
        "max_net_filled_notional": plan_limits["max_net_filled_notional"],
        "max_concentration": plan_limits["max_concentration"],
        "min_chore_notional": plan_limits["min_chore_notional"],
        "limit_up_down_volume_participation_rate": plan_limits["limit_up_down_volume_participation_rate"],
        "cancel_rate.max_cancel_rate": plan_limits["cancel_rate"]["max_cancel_rate"],
        "cancel_rate.applicable_period_seconds": plan_limits["cancel_rate"]["applicable_period_seconds"],
        "cancel_rate.waived_initial_chores": plan_limits["cancel_rate"]["waived_initial_chores"],
        "cancel_rate.waived_min_rolling_notional": plan_limits["cancel_rate"]["waived_min_rolling_notional"],
        "cancel_rate.waived_min_rolling_period_seconds": plan_limits["cancel_rate"][
            "waived_min_rolling_period_seconds"],
        "market_barter_volume_participation.max_participation_rate": plan_limits["market_barter_volume_participation"][
            "max_participation_rate"],
        "market_barter_volume_participation.applicable_period_seconds":
            plan_limits["market_barter_volume_participation"]["applicable_period_seconds"],
        "market_barter_volume_participation.min_allowed_notional": plan_limits["market_barter_volume_participation"][
            "min_allowed_notional"],
        "market_depth.participation_rate": plan_limits["market_depth"]["participation_rate"],
        "market_depth.depth_levels": plan_limits["market_depth"]["depth_levels"],
        "residual_restriction.max_residual": plan_limits["residual_restriction"]["max_residual"],
        "residual_restriction.residual_mark_seconds": plan_limits["residual_restriction"]["residual_mark_seconds"],
    }

    for xpath, value in fields_xpath_n_value.items():
        if layout == Layout.NESTED:
            nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
            field_element = nested_tree_dialog.find_element(By.ID, "residual_mark_seconds")
        else:
            field_element = plan_limit_widget.find_element(By.ID, "residual_mark_seconds")
        if layout != Layout.NESTED:
            scroll_into_view(driver=driver, element=field_element)
        name = xpath.split('.')[-1]
        set_tree_input_field(driver= driver, widget=plan_limit_widget, xpath=xpath, name=name, value=value)


def validate_plan_limits(widget: WebElement, plan_limits: Dict, layout: Layout) -> None:
    fields_to_validate = {
        "max_open_chores_per_side": ["max_open_chores_per_side"],
        "max_single_leg_notional": ["max_single_leg_notional"],
        "max_open_single_leg_notional": ["max_open_single_leg_notional"],
        "max_net_filled_notional": ["max_net_filled_notional"],
        "max_concentration": ["max_concentration"],
        "min_chore_notional": ["min_chore_notional"],
        "limit_up_down_volume_participation_rate": ["limit_up_down_volume_participation_rate"],
        "cancel_rate.max_cancel_rate": ["cancel_rate", "max_cancel_rate"],
        "cancel_rate.applicable_period_seconds": ["cancel_rate", "applicable_period_seconds"],
        "cancel_rate.waived_initial_chores": ["cancel_rate", "waived_initial_chores"],
        "cancel_rate.waived_min_rolling_notional": ["cancel_rate", "waived_min_rolling_notional"],
        "cancel_rate.waived_min_rolling_period_seconds": ["cancel_rate", "waived_min_rolling_period_seconds"],
        "market_barter_volume_participation.max_participation_rate": ["market_barter_volume_participation",
                                                                     "max_participation_rate"],
        "market_barter_volume_participation.applicable_period_seconds": ["market_barter_volume_participation",
                                                                        "applicable_period_seconds"],
        "market_barter_volume_participation.min_allowed_notional": ["market_barter_volume_participation",
                                                                   "min_allowed_notional"],
        "market_depth.participation_rate": ["market_depth", "participation_rate"],
        "market_depth.depth_levels": ["market_depth", "depth_levels"],
        "residual_restriction.max_residual": ["residual_restriction", "max_residual"],
        "residual_restriction.residual_mark_seconds": ["residual_restriction", "residual_mark_seconds"]
    }

    for xpath, keys in fields_to_validate.items():
        created_plan_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
        if "," in created_plan_value:
            created_plan_value = created_plan_value.replace(",", "")
        expected_value = plan_limits
        for key in keys:
            expected_value = expected_value[key]
            if "notional" in key:
                expected_value = created_plan_value
        assert created_plan_value == str(
            expected_value), f"Assertion failed for {xpath}: expected_value {expected_value}, got {created_plan_value}"


def get_value_from_input_field(widget: WebElement, xpath: str, layout: Layout) -> str:
    parent_tag: str = ""
    if layout == Layout.TREE:
        parent_tag = "div"
    elif layout == Layout.TABLE:
        parent_tag = "td"
    parent_xpath: str = f"//{parent_tag}[@data-xpath='{xpath}']"

    xpath_element = widget.find_element(By.XPATH, parent_xpath)
    if layout == Layout.TABLE:
        click_element_n_short_delay(xpath_element)
    value = get_value_frm_input_fld_with_input_tag(xpath_element=xpath_element, layout=layout)
    return value


def get_dropdown_value_frm_layout(driver: WebDriver, widget: WebElement, fld_id: str, xpath: str, layout: Layout) -> \
List[str]:
    dropdwn_element = get_xpath_element_for_layout(widget=widget, xpath=xpath, layout=layout)
    if layout == Layout.TREE:
        dropdwn_element = dropdwn_element.find_element(By.ID, fld_id)
    dropdwn_element.click()
    time.sleep(Delay.SHORT.value)
    dropdown_txt_lst = []
    ul_element = driver.find_element(By.TAG_NAME, "ul")
    li_elements = ul_element.find_elements(By.TAG_NAME, "li")
    for li_element in li_elements:
        dropdwn_txt = li_element.text
        dropdown_txt_lst.append(dropdwn_txt)
    widget.click()
    return dropdown_txt_lst


def click_element_n_short_delay(element: WebElement):
    element.click()
    time.sleep(Delay.SHORT.value)


def get_value_frm_input_fld_with_input_tag(xpath_element: WebElement, layout: Layout) -> str:
    input_element = xpath_element.find_element(By.TAG_NAME, "input")
    value = input_element.get_attribute("value")
    if layout == Layout.TABLE:
        input_element.send_keys(Keys.ENTER)
    return value


def get_widget_type(widget_schema: Dict) -> WidgetType | None:
    layout_list = widget_schema['widget_ui_data_element']["widget_ui_data"][0]
    is_repeated: bool = True if widget_schema["widget_ui_data_element"].get("is_repeated") else False
    is_json_root: bool = True if widget_schema.get("json_root") else False

    for widget_type, layout in layout_list.items():
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
        elif layout in ["UI_ABBREVIATED_FILTER"] and is_json_root:
            return WidgetType.ABBREVIATED
        return None


def get_widgets_by_flux_property(schema_dict: Dict[str, any], widget_type: WidgetType,
                                 flux_property: FluxPropertyType):
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
            if field_properties["type"] in SIMPLE_DATA_TYPE_LIST:
                if flux_property in field_properties:
                    field_queries.append(FieldQuery(field_name=field, properties=field_properties))
            elif field_properties["type"] in COMPLEX_DATA_TYPE_LIST:
                if field_properties.get("underlying_type") is not None and \
                        field_properties["underlying_type"] in SIMPLE_DATA_TYPE_LIST:
                    if flux_property in field_properties:
                        field_queries.append(FieldQuery(field_name=field, properties=field_properties))
                    continue

                ref_path: str = field_properties["items"]["$ref"]
                ref_list: List[str] = ref_path.split("/")[1:]
                child_schema: Dict[str, any] = schema_dict[ref_list[0]][ref_list[1]] if len(ref_list) == 2 \
                    else schema_dict[ref_list[0]]

                # Check if flux_property is enabled in the complex type
                if flux_property in field_properties:
                    # If enabled, apply it to all fields within the complex type
                    for child_field, child_field_properties in child_schema["properties"].items():
                        parent_title: str | None = field_properties.get("parent_title")
                        if (flux_property not in child_field_properties or
                                parent_title != field_properties["title"].replace(" ", "_")):
                            if parent_title is None:
                                child_field_properties["parent_title"] = field_properties["title"].replace(" ", "_")
                            else:
                                parent_title = parent_title.replace(" ", "_")
                                child_parent_title: str = field_properties["title"]
                                child_parent_title = child_parent_title.replace(" ", "_")
                                child_field_properties["parent_title"] = parent_title + "." + child_parent_title
                            child_field_properties[flux_property] = field_properties[flux_property]

                # Recursively search the child schema
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
            schema_copy = copy.deepcopy(widget_schema)  # Create a deep copy of the schema
            search_schema_for_flux_property(schema_copy)
            if field_queries:
                widget_query: WidgetQuery = WidgetQuery(widget_name=widget_name, fields=field_queries)
                widget_queries.append(widget_query)

    if widget_queries:
        return True, widget_queries
    return False, None


def get_xpath_from_field_name(schema_dict: Dict[str, any], widget_type: WidgetType, widget_name: str, field_name: str):
    def search_schema_for_field(current_schema: Dict[str, any]) -> str | None:
        properties: Dict[str, any] = current_schema["properties"]
        field_key: str
        field_properties: Dict[str, any]
        for field_key, field_properties in properties.items():
            if field_properties["type"] in SIMPLE_DATA_TYPE_LIST:
                if field_name == field_key:
                    return field_name
            elif field_properties["type"] in COMPLEX_DATA_TYPE_LIST:
                if field_properties["underlying_type"] in SIMPLE_DATA_TYPE_LIST:
                    continue
                ref_path: str = field_properties["items"]["$ref"]
                ref_list: List[str] = ref_path.split("/")[1:]
                child_schema: Dict[str, any] = schema_dict[ref_list[0]][ref_list[1]] if len(ref_list) == 2 \
                    else schema_dict[ref_list[0]]
                ret = search_schema_for_field(child_schema)
                if ret:
                    if field_properties["type"] == DataType.ARRAY:
                        return f"{field_key}[0].{ret}"
                    else:
                        return f"{field_key}.{ret}"

    xpath: str = ""
    if widget_type == WidgetType.DEPENDENT:
        xpath = f"{widget_name}."

    widget_schema: Dict[str, any] = schema_dict[widget_name]
    result = search_schema_for_field(widget_schema)
    if result:
        return xpath + result
    return None



def override_default_limits(chore_limits: ChoreLimitsBaseModel, contact_limits: ContactLimitsBaseModel) -> None:
    updated_chore_limits: ChoreLimitsBaseModel = ChoreLimitsBaseModel(id=chore_limits.id, max_basis_points=150,
                                                                      max_px_deviation=2,
                                                                      max_px_levels=0, max_chore_qty=0,
                                                                      max_contract_qty=0, max_chore_notional=0,
                                                                      max_basis_points_algo=0, max_px_deviation_algo=0,
                                                                      max_chore_notional_algo=0,
                                                                      max_contract_qty_algo=0, max_chore_qty_algo=0)
    email_book_service_native_web_client.patch_chore_limits_client(jsonable_encoder(
        updated_chore_limits.to_dict(by_alias=True, exclude_none=True)))

    updated_contact_limits: ContactLimitsBaseModel = \
        ContactLimitsBaseModel(id=contact_limits.id, max_open_baskets=200)
    email_book_service_native_web_client.patch_contact_limits_client(jsonable_encoder(
        updated_contact_limits.to_dict(by_alias=True, exclude_none=True)))


def override_plan_limit(street_book_service_http_client: StreetBookServiceHttpClient) -> None:
    plan_limit_list: List[PlanLimitsBaseModel] = street_book_service_http_client.get_all_plan_limits_client()

    for plan_limit in plan_limit_list:
        cancel_rate: CancelRateOptional = CancelRateOptional(max_cancel_rate=20)
        market_barter_volume_participation: MarketBarterVolumeParticipationOptional = \
            MarketBarterVolumeParticipationOptional(max_participation_rate=20)
        updated_plan_limit: PlanLimitsBaseModel = \
            PlanLimitsBaseModel(id=plan_limit.id, cancel_rate=cancel_rate,
                                 market_barter_volume_participation=market_barter_volume_participation)

        updated_plan_limit.min_chore_notional = 1000
        street_book_service_http_client.patch_plan_limits_client(jsonable_encoder(
            updated_plan_limit.to_dict(by_alias=True, exclude_none=True)))


def switch_layout(widget: WebElement, layout: Layout) -> None:
    # TODO: verify the current layout of ui and match with layout arg then try:
    btn_name: str = ""
    if layout == Layout.TREE:
        btn_name = "UI_TREE"
    elif layout == Layout.TABLE:
        btn_name = "UI_TABLE"
    elif layout == Layout.CHART:
        btn_name = "UI_CHART"
    try:
        widget.find_element(By.NAME, "Layout").click()
        time.sleep(Delay.SHORT.value)
        widget.find_element(By.NAME, btn_name).click()
        time.sleep(Delay.SHORT.value)
    except NoSuchElementException as e:
        print(f"failed to switch to layout: {layout};;; exception: {e}")


def activate_plan(widget: WebElement, driver: WebDriver) -> None:
    css_selector = get_css_selector_with_partial_class_name("MuiTableContainer-root")
    tr_element = widget.find_element(By.CSS_SELECTOR, css_selector)

    activate_btn_elements = tr_element.find_elements(By.TAG_NAME, "td")
    activate_btn = activate_btn_elements[5].find_element(By.TAG_NAME, "button")

    btn_caption = activate_btn.text
    assert btn_caption in ["Activate", "ERROR", "Pause"], "Unknown button state."

    if btn_caption == "Activate":
        activate_btn.click()
        time.sleep(Delay.SHORT.value)
        click_confirm_save(driver=driver)

        # Verify if the plan is in active state
        css_selector = get_css_selector_with_partial_class_name("MuiTableContainer-root")
        tr_element = widget.find_element(By.CSS_SELECTOR, css_selector)

        activate_btn_element = tr_element.find_elements(By.TAG_NAME, "td")
        btn_caption = activate_btn_element[5].find_element(By.TAG_NAME, "button").text
        assert btn_caption == "Pause", "Failed to activate plan."

    elif btn_caption in ["ERROR", "Pause"]:
        print(f"Plan is in {btn_caption} state. Cannot activate.")


def click_confirm_save(driver: WebDriver) -> None:
    click_confirm_save_dialog = get_dialog_element(driver)
    try:
        confirm_btn = click_confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
        confirm_btn.click()
    except Exception as e:
        print(f"Failed to confirm save it might because form validation error: {e}")
    time.sleep(Delay.SHORT.value)


def get_dialog_element(driver: WebDriver) -> WebElement:
    dialog_element = driver.find_element(By.XPATH, "//div[@role='dialog']")
    return dialog_element


def hide_n_show_inside_setting(widget: WebElement, driver: WebDriver, common_keys_fields: List[str], button_state: ButtonState):
    click_button_with_name(widget=widget, button_name="Settings")
    while True:
        # select a random key
        selected_fld: str = random.choice(common_keys_fields)
        settings_dropdown_widget: WebElement = driver.find_element(By.CLASS_NAME, "MuiPopover-paper")
        try:
            hide_or_show_btn_element = settings_dropdown_widget.find_element(By.NAME, selected_fld)
        except NoSuchElementException:
            selected_fld = f"security.{selected_fld}"
            try:
                hide_or_show_btn_element = settings_dropdown_widget.find_element(By.NAME, selected_fld)
            except NoSuchElementException:
                logging.error(f"Element with name '{selected_fld}' not found even after modifying the locator name.")
                continue  # Skip this iteration and retry with a field

        btn_caption = hide_or_show_btn_element.text
        if btn_caption == button_state.value:
            hide_or_show_btn_element.click()
            close_setting(driver)
        return selected_fld


def click_show_btn_inside_setting(driver: WebDriver, common_keys_fields: List[str]):
    while True:
        # select a random key
        selected_fld: str = random.choice(common_keys_fields)
        settings_dropdown_widget: WebElement = driver.find_element(By.CLASS_NAME, "MuiPopover-paper")
        hide_or_show_btn_element = settings_dropdown_widget.find_element(By.NAME, selected_fld)
        btn_caption = hide_or_show_btn_element.text
        if btn_caption == "HIDE":
            hide_or_show_btn_element.click()
            break


def show_hidden_fields_in_tree_layout(widget: WebElement, driver: WebDriver, layout: Layout) -> None:
    switch_layout(widget=widget, layout=layout)
    click_button_with_name(widget=widget, button_name="Show")
    list_element = driver.find_element(By.XPATH, "//ul[@role='listbox']")
    li_elements = list_element.find_elements(By.TAG_NAME, "li")
    li_elements[0].click()


def show_hidden_field_in_review_changes_popup(driver: WebDriver) -> None:
    review_changes_widget = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")
    expand_buttons = review_changes_widget.find_elements(By.CLASS_NAME, "node-ellipsis")
    for expand_button in expand_buttons:
        expand_button.click()


def is_table_cell_enabled_n_get_input_element(widget: WebElement, xpath: str) -> [bool, WebElement]:
    input_td_xpath: str = get_table_input_field_xpath(xpath=xpath)
    try:
        input_td_element = widget.find_element(By.XPATH, input_td_xpath)
        click_element_n_short_delay(input_td_element)
        input_element = input_td_element.find_element(By.TAG_NAME, "input")
        return [True, input_element]
    except Exception as e:
        print(f"With this xpath '{xpath}', the field is not enabled.{e}")
        return [False, None]


def wait_until_input_field_value_is_not_blank(driver, locator):
    wait_ = WebDriverWait(driver, Delay.SHORT.value)
    wait_.until(EC.text_to_be_present_in_element_value(locator, ""))


def click_save_n_click_confirm_save_btn(driver, widget: WebElement):
    try:
        click_button_with_name(widget=widget, button_name="Save")
        click_confirm_save(driver=driver)
    except Exception as e:
        print(f"Failed to confirm save it might because form validation error: {e}")


def count_fields_in_tree(widget: WebElement) -> List[str]:
    field_elements = widget.find_elements(By.CLASS_NAME, "Node_node__sh0RD")
    field_names = []
    for field_element in field_elements:
        field_names.append(field_element.text)
    return field_names


def get_commonkey_items(widget: WebElement) -> Dict[str, any]:
    common_key_widget = widget.find_element(By.XPATH, "//div")
    common_key_item_elements = common_key_widget.find_elements(By.CLASS_NAME, "CommonKeyWidget_item")
    common_key_items: Dict[str, any] = {}
    for common_key_item_element in common_key_item_elements:
        common_key_item_txt = common_key_item_element.text.split(":")
        key = common_key_item_txt[0].replace(" ", "_")
        value = common_key_item_txt[1]
        common_key_items[key] = value
    return common_key_items


def click_edit_btn(driver: WebDriver, widget: WebElement):
    try:
        click_button_with_name(widget=widget, button_name="Edit")
    except NoSuchElementException:
        click_button_with_name(driver.find_element(By.ID, WidgetName.PlanCollection.value), button_name="Edit")
    except Exception as e:
        print(f"edit btn not found inside {widget}: {e}")


def get_flux_fld_number_format(driver: WebDriver, widget: WebElement, xpath: str,
                               layout: Layout, widget_name: str, widget_type: WidgetType) -> str:
    element: WebElement
    is_visible_without_click: bool = True

    is_showing: bool = is_num_format_field_showing(widget, xpath, layout)
    if not is_showing:
        show_hidden_fields_for_layout(driver, widget, layout, widget_name)
    if layout == Layout.TABLE:
        is_visible_without_click: bool = is_num_format_visible_without_click_in_table_layout(widget, xpath, widget_type=widget_type)
    if is_visible_without_click:
        element: WebElement = get_num_format_element_for_layout(widget=widget, xpath=xpath, layout=layout)
    else:
        # if num format not visible without click
        element: WebElement = click_n_get_xpath_element_for_layout(widget, layout, xpath)

    if element:
        if not is_visible_without_click and layout == Layout.TABLE:
            tag_name = "p"
        elif is_visible_without_click and layout == Layout.TABLE:
            tag_name = "span"
        else:
            # for tree layout
            tag_name = "p"
        num_format: str = get_fld_text_with_tag_name(xpath_element=element, tag_name=tag_name)
        num_format = get_only_num_format_frm_string(num_format=num_format)
        return num_format


def get_num_format_frm_common_keys(widget: WebElement, driver: WebDriver, fld_name: str):
    common_keys: Dict[str, str] = get_common_keys_items(widget=widget, driver=driver)
    fld_value = common_keys.get(fld_name)
    num_format = fld_value.replace("[", "").replace("]", "")
    num_format = get_only_num_format_frm_string(num_format=num_format)
    return num_format


def get_only_num_format_frm_string(num_format: str) -> str:
    if num_format:
        if ".3" in num_format:
            return ".3"
        elif "bps" in num_format:
            return "bps"
            # get only % or $ from str
        return num_format[-1]


def is_num_format_visible_without_click_in_table_layout(widget: WebElement, xpath: str, widget_type: WidgetType) -> bool:
    try:
        if widget_type != WidgetType.REPEATED_INDEPENDENT:
            xpath_element: WebElement = get_table_layout_xpath_element(widget=widget, xpath=xpath)
        else:
            xpath_element: WebElement = get_table_layout_xpath_element_based_on_index(widget=widget, xpath=xpath)
        num_format_element = xpath_element.find_element(By.TAG_NAME, "span")
        num_format = num_format_element.text
        if num_format:
            return True
        else:
            return False
    except Exception as e:
        print(f"Unexpected error for fld{xpath}: Exception:- {e}")


def get_table_layout_xpath_element(widget: WebElement, xpath: str):
    xpath = get_table_input_field_xpath(xpath=xpath)
    xpath_element = widget.find_element(By.XPATH, xpath)
    return xpath_element


def get_table_layout_xpath_element_based_on_index(widget: WebElement, xpath: str, index_no: str="0"):
    xpath = get_table_layout_xpath_based_on_index(xpath=xpath, index_no=index_no)
    xpath_element = widget.find_element(By.XPATH, xpath)
    return xpath_element


def get_table_layout_xpath_based_on_index(xpath: str, index_no: str):
    return f"//td[@data-xpath='[{index_no}].{xpath}']"


def is_num_format_field_showing(widget: WebElement, xpath: str, layout: Layout) -> bool:
    try:
        element: WebElement = get_num_format_element_for_layout(widget=widget, xpath=xpath, layout=layout)
        if element:
            return True
    except Exception as e:
        print(
            f"The number format field with xpath '{xpath}' is not found in the specified layout: {layout}. Exception: {e}")


def show_hidden_fields_for_layout(driver: WebDriver, widget: WebElement, layout: Layout, widget_name: str):
    if layout == Layout.TABLE:
        show_hidden_fields_in_table_layout(driver, widget, widget_name, layout=layout)
    else:
        show_hidden_fields_in_tree_layout(widget, driver, layout=layout)


def get_num_format_element_for_layout(widget: WebElement, xpath: str, layout: Layout) -> WebElement:
    element = get_xpath_element_for_layout(widget=widget, xpath=xpath, layout=layout)
    return element


def scroll_into_widget_with_widget_name(widget: WebElement, driver: WebDriver, widget_name: str):
    if widget_name == WidgetName.PairPlanParams.value:
        scroll_into_view(driver, driver.find_element(By.ID, WidgetName.PlanCollection.value))
    else:
        scroll_into_view(driver, widget)


def click_show_all_btn_inside_setting(driver: WebDriver, widget: WebElement, widget_name: str):
    click_button_with_name(widget=widget, button_name="Settings")
    table_setting_id = get_table_setting_id_with_widget_name(widget_name=widget_name)

    try:
        # Try finding the element by the primary ID
        setting_widget_ele = driver.find_element(By.ID, table_setting_id)
        # Click "HideShowAll" if the element is found
        click_button_with_name(widget=setting_widget_ele, button_name="HideShowAll")

    except NoSuchElementException:
        # Handle the case where '_params' might be in the ID
        if "_params" in table_setting_id:
            table_setting_id_parts = table_setting_id.split("_params")
            if len(table_setting_id_parts) == 2:
                alternative_id = f"definitions.{table_setting_id_parts[0]}{table_setting_id_parts[1]}"
            else:
                raise ValueError(f"Unexpected format for table_setting_id: '{table_setting_id}'")

            try:
                # Try finding the element by the alternative ID
                setting_widget_ele = driver.find_element(By.ID, alternative_id)
                # Click "HideShowAll" if the alternative element is found
                click_button_with_name(widget=setting_widget_ele, button_name="HideShowAll")

            except Exception as e:
                raise Exception(
                    f"Failed to locate settings widget. Tried IDs: '{table_setting_id}' and '{alternative_id}'. Error: {str(e)}")

    # Wait for the "HideShowAll" button to update its value
    wait(driver, Delay.MEDIUM.value).until(
        EC.text_to_be_present_in_element_value((By.NAME, "HideShowAll"), "Show Default"))


def get_text_from_element_with_name(widget: WebElement, name: str) -> str:
    text_element = widget.find_element(By.NAME, name)
    text_element = text_element.text
    return text_element


def get_table_setting_id_with_widget_name(widget_name: str):
    return widget_name + "_table_settings"


def show_hidden_fields_in_table_layout(driver: WebDriver, widget: WebElement, widget_name: str, layout: Layout):
    switch_layout(widget, layout)
    click_show_all_btn_inside_setting(driver, widget, widget_name)
    close_setting(driver)


def close_setting(driver: WebDriver):
    action = get_action_chain_instance(driver)
    try:
        action.send_keys(Keys.ESCAPE).perform()
    except Exception as e:
        raise Exception(f"Unexpected error: {e}")


def wait_until_tooltip_not_closed(driver, widget_name):
     tooltip_element = get_setting_tooltip_widget(driver, widget_name)
     # Wait until the tooltip is visible
     wait(driver, Delay.MEDIUM.value).until(
         EC.visibility_of(tooltip_element)
     )


def get_action_chain_instance(driver: WebDriver) -> ActionChains:
    action = ActionChains(driver)
    return action


def get_fld_text_with_tag_name(xpath_element: WebElement, tag_name: str) -> str:
    # First, try to find the element with the specified tag name
    num_format_element = xpath_element.find_element(By.TAG_NAME, tag_name)
    number_format = num_format_element.text
    if number_format:
        return number_format


def get_table_layout_field_name(widget: WebElement):
    thead_elements = widget.find_elements(By.CLASS_NAME, "MuiTableCell-root")
    field_name_texts = []
    for thead_element in thead_elements:
        field_name_texts.append(thead_element.text)
    return field_name_texts


def validate_comma_separated_values(driver: WebDriver, widget: WebElement, layout: Layout,
                                    field_name_n_input_value: dict, widget_name: str):
    click_button_with_name(widget=widget, button_name="Save")
    input_value: str
    if layout == Layout.TABLE:
        click_confirm_save(driver=driver)
        common_keys = get_replaced_underscore_common_key(widget, driver)
        replaced_symbol_with_notional = get_replaced_dollar_symbol_with_notional_common_key(common_keys)
        value_without_num_format = get_replaced_value_without_num_format_common_key(
            common_key_items=replaced_symbol_with_notional)
        for field_name, input_value in field_name_n_input_value.items():
            try:
                value_from_ui: str = value_without_num_format[field_name]
                # getting common key value without comma and dot to validate, if value= "1,230.0" get "1230" only
                assert (value_from_ui.replace(",", "") ==
                        input_value.split(".")[0].replace(",", "")), \
                    f"Value mismatch field_name: {field_name} value_from_ui: {value_from_ui} input_value: {input_value}"
            except Exception as e:
                print(e)


    elif layout == Layout.TREE:
        if widget_name in ["plan_status", "contact_status"]:
            click_confirm_save(driver)
            time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        for xpath, input_value in field_name_n_input_value.items():
            value_from_ui: str = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
            assert value_from_ui.replace(",", "") == input_value.split(".")[0].replace(",", "")
    field_name_n_input_value.clear()


def get_fld_name_colour_in_tree(widget: WebElement, xpath: str):
    div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    div_xpath_element = widget.find_element(By.XPATH, div_xpath)
    element = div_xpath_element.find_element(By.CLASS_NAME, "Node_node__sh0RD")
    span_element = element.find_element(By.TAG_NAME, "span")

    color = span_element.value_of_css_property("color")
    return color


def get_progress_bar_level(widget: WebElement) -> str:
    box_root_element = widget.find_element(By.CLASS_NAME, "MuiBox-root")
    span_element = box_root_element.find_element(By.CLASS_NAME, "MuiLinearProgress-root")
    progress_level = span_element.get_attribute("aria-valuenow")
    return progress_level


def get_val_max_from_input_fld(val_max: str, driver: WebDriver, widget_type: WidgetType, layout: Layout):
    widget: WebElement
    xpath: str = ""
    widget_name: str = ""
    field_value: str = ""
    if isinstance(val_max, str):
        splitted_list = val_max.split(".")
        if widget_type == widget_type.INDEPENDENT:
            xpath = splitted_list[1]
            widget_name = splitted_list[0]
        if widget_type == widget_type.DEPENDENT:
            xpath = splitted_list[1]
            widget_name = splitted_list[0]
    widget = driver.find_element(By.ID, widget_name)
    if layout == layout.TREE:
        switch_layout(widget=widget, layout=Layout.TREE)
        field_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=Layout.TREE)
    return field_value, widget_name


def get_nested_tree_dialog_widget_element(driver: WebDriver) -> WebElement:
    dialog_element = get_dialog_element(driver)
    xpath = get_nested_tree_layout_dialog_xpath(attribute_value="presentation")
    nested_fld_widget = dialog_element.find_element(By.XPATH, xpath)
    return nested_fld_widget


def get_fld_name_frm_unsaved_changes_dialog(driver: WebDriver) -> str:
    popup_widget = driver.find_element(By.XPATH, "//div[@role='dialog']")
    span_element = popup_widget.find_element(By.CLASS_NAME, "object-key")
    unsaved_changes_field_name = span_element.text
    return unsaved_changes_field_name.replace('"', '')


def click_okay_btn_inside_unsaved_changes_dialog(driver: webdriver) -> None:
    popup_widget = driver.find_element(By.XPATH, "//div[@role='dialog']")
    button_element = popup_widget.find_element(By.XPATH, "//button[normalize-space()='Okay']")
    button_element.click()
    time.sleep(Delay.SHORT.value)


def discard_changes(widget: WebElement) -> None:
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    discard_changes_btn = form_validation_dialog.find_element(By.XPATH, "//button[normalize-space()='Discard Changes']")
    discard_changes_btn.click()


def get_object_keys_from_dialog_box(widget: WebElement) -> List[str]:
    form_validation_dialog: WebElement = widget.find_element(By.XPATH, "//div[@role='dialog']")
    form_validation_elements: List[WebElement] = form_validation_dialog.find_elements(By.CLASS_NAME, "object-key")
    object_keys: List[str] = []
    for form_validation_element in form_validation_elements:
        object_keys.append(form_validation_element.text[1:-1])
    return object_keys


def get_common_keys_fld_names(widget) -> List[str]:
    common_key_container = widget.find_element(By.CSS_SELECTOR, "[class*='CommonKeyWidget_container']")
    common_key_items = common_key_container.find_elements(By.CSS_SELECTOR, "[class*=CommonKeyWidget_item")

    common_keys_fields = []
    for item in common_key_items:
        fld_name_element = item.find_element(By.TAG_NAME, "span")
        fld_name = fld_name_element.text.split(":")[0].split("[")[0]
        if fld_name == "plan_leg1" or fld_name == "plan_leg2":
            fld_name = fld_name.replace(fld_name, f"{fld_name}.side")
        if " " in fld_name:
            fld_name = fld_name.replace(" ", "_")
        common_keys_fields.append(fld_name)
    return common_keys_fields


def get_common_keys_items_value(widget: WebElement) -> List[str]:
    common_key_value = []
    common_key_items_elements = get_common_key_items_elements(widget)
    for common_key_items_element in common_key_items_elements:
        span_elements = common_key_items_element.find_elements(By.TAG_NAME, "span")
        value = span_elements[1].text
        common_key_value.append(value)
    return common_key_value


def get_common_keys_items(widget: WebElement, driver: WebDriver) -> Dict[str, str]:
    common_key_items = {}
    common_key_items_elements = get_common_key_items_elements(widget)
    is_abbreviated_present = is_abbreviated_json_txt_present_in_common_keys(widget)
    if is_abbreviated_present:
        abbreviated_fld_n_value: Dict[str, str] = get_abbreviated_fld_name_n_value(driver, widget)
        # Store key-value pairs from abbreviated_fld_n_value into common_key_items
        common_key_items.update(abbreviated_fld_n_value)
    for common_key_items_element in common_key_items_elements:
        item = common_key_items_element.text
        fld_name = item.split(":")[0]
        fld_value = item.split(":")[1]
        common_key_items[fld_name] = fld_value
    return common_key_items


def get_abbreviated_fld_name_n_value(driver: WebDriver, widget: WebElement) -> Dict[str, str]:
    abbreviated_elements_list: List[WebElement] = get_abbreviated_json_txt_element(widget)
    abbreviated_fld_n_values: Dict[str, str] = {}

    for abbreviated_element in abbreviated_elements_list:
        abbreviated_element.click()
        time.sleep(Delay.SHORT.value)

        json_container_element = get_abbreviated_container_element(driver)
        fld_n_value_elements = json_container_element.find_elements(By.CLASS_NAME, "copy-icon")
        # Click to get value on clipboard
        fld_n_value_elements[1].click()
        # Get the clipboard content in var
        copied_text = pyperclip.paste()
        close_popover(driver)

        # Parse the copied JSON string and extract the field name and value
        try:
            data = json.loads(copied_text)  # Convert the JSON string to a dictionary

            # Iterate through the keys in the data dictionary
            for key, value in data.items():
                # If the value is a string, store it directly
                if isinstance(value, str):
                    abbreviated_fld_n_values[key] = value
                # If the value is a list, extract relevant information as needed
                elif isinstance(value, list):
                    # For simplicity, you could join the list into a string, or handle it based on your requirement
                    abbreviated_fld_n_values[key] = str(value)  # Convert the list to a string representation

                # Handle other types as needed (e.g., dict)
                elif isinstance(value, dict):
                    # Optionally handle nested dictionaries if necessary
                    abbreviated_fld_n_values[key] = str(value)  # Convert the dict to a string representation
                else:
                    abbreviated_fld_n_values[key] = str(value)  # Fallback to string conversion for other types

        except json.JSONDecodeError:
            print("Error decoding JSON from clipboard.")

    return abbreviated_fld_n_values


def replace_currency_symbol(value: str):
    value = value.replace(" $", "")
    return value


def get_abbreviated_container_element(driver: WebDriver) -> WebElement:
    css_selector = get_css_selector_with_partial_class_name("pretty-json-container")
    json_container_element = driver.find_element(By.CSS_SELECTOR, css_selector)
    return json_container_element


def is_abbreviated_json_txt_present_in_common_keys(widget: WebElement) -> bool:
    try:
        abbreviated_elements: List[WebElement] = get_abbreviated_json_txt_element(widget)
        if abbreviated_elements:
            return True
    except NoSuchElementException:
        # If element is not found, just return False
        return False
    except Exception as e:
        # Raise any unexpected error with a more descriptive message
        raise Exception(f"An unexpected error occurred: {str(e)}")

    # Return False if no element is found or exception is raised
    return False


def get_abbreviated_json_txt_element(widget: WebElement) -> List[WebElement] | bool:
    common_key_items_elements = get_common_key_items_elements(widget)
    css_selector = get_css_selector_with_partial_class_name_n_tag_name(
        "CommonKeyWidget_abbreviated", "span")
    abbreviated_json_elements = []

    for common_key_element in common_key_items_elements:
        try:
            abbreviated_element = common_key_element.find_element(By.CSS_SELECTOR, css_selector)
            abbreviated_json_elements.append(abbreviated_element)
        except NoSuchElementException:
            # Element not found, continue to the next common key element
            continue
        except Exception as e:
            # Raise an exception for any error other than NoSuchElementException
            raise Exception(f"An unexpected error occurred while finding abbreviated elements: {e}")

    # If no abbreviated elements were found, return False
    if not abbreviated_json_elements:
        return False

    return abbreviated_json_elements



def get_common_key_items_elements(widget: WebElement) -> List[WebElement]:
    common_key_container_element = get_common_key_widget_container_element(widget)
    common_key_elements = get_common_key_item_element(common_key_container_element)
    return common_key_elements


def get_common_key_item_element(common_key_container_element: WebElement) -> List[WebElement]:
    common_key_elements = get_css_selector_with_partial_class_name("CommonKeyWidget_item")
    common_key_elements = common_key_container_element.find_elements(By.CSS_SELECTOR, common_key_elements)
    return common_key_elements


def get_common_key_widget_container_element(widget: WebElement) -> WebElement:
    common_key_container = get_css_selector_with_partial_class_name("CommonKeyWidget_container")
    common_key_container = widget.find_element(By.CSS_SELECTOR, common_key_container)
    return common_key_container


def get_common_fields_from_list(widget: WebElement):
    common_key_items_elements = get_common_key_items_elements(widget)
    common_fields_frm_list = []
    for common_key_element in common_key_items_elements:
        fld_name_elements = common_key_element.find_elements(By.TAG_NAME, "span")
        common_fields_frm_list.append(fld_name_elements[1].text.replace("[", "").replace("]", "").replace(":", ""))
    return common_fields_frm_list


def get_all_keys_from_table(table: WebElement) -> List[str]:
    # Assuming the heading cells are in the first row of the table
    heading_row: WebElement = table.find_element(By.TAG_NAME, "tr")

    # Assuming the heading values are present in the cells of the heading row
    heading_cells: List[WebElement] = heading_row.find_elements(By.TAG_NAME, "th")

    headings = [cell.text.replace(" ", "_") for cell in heading_cells]

    return headings


def get_replaced_common_keys(common_keys_fields: List) -> List[str]:
    list_of_common_keys = []
    for common_key in common_keys_fields:
        list_of_common_keys.append(common_key.replace("common premium", "common_premium")
                                   .replace("hedge ratio", "hedge_ratio").replace("plan mode", "plan_mode").
                                   replace("plan type", "plan_type"))
    return list_of_common_keys


def get_css_selector_with_partial_class_name_n_tag_name(partial_class_name: str, tag_name: str):
    return f"{tag_name}[class*={partial_class_name}]"


def get_table_headers(widget: WebElement) -> List[str]:
    # row fld names
    css_selector = get_css_selector_with_partial_class_name_n_tag_name(partial_class_name="MuiButtonBase-root",
                                                                       tag_name="span")
    span_elements: List[WebElement] = widget.find_elements(By.CSS_SELECTOR, css_selector)
    table_headers: List[str] = [span_element.text.replace(" ", "_") for span_element in span_elements]
    return table_headers


def save_nested_plan(driver: WebDriver):
    nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    save_plan = nested_tree_dialog.find_element(By.NAME, "Save")
    save_plan.click()

def get_nested_tree_layout_dialog_xpath(attribute_value: str):
    return f"//div[@role='{attribute_value}']"


def expand_all_nested_fld_name_frm_review_changes_dialog(driver: WebDriver) -> None:
    dialog_widget = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")
    try:
        plus_btn_elements = dialog_widget.find_elements(By.CLASS_NAME, "collapsed-icon")
        for plus_btn in plus_btn_elements:
            plus_btn.click()
            time.sleep(Delay.SHORT.value)
    except NoSuchElementException:
        logging.info("No nested expandable fields found inside review changes dialog.")
        pass


def create_tob_md_ld_fj_os_oj(driver: WebDriver, top_of_book_fixture: List,
                              market_depth_basemodel_fixture: List[MarketDepthBaseModel],
                              last_barter_basemodel_fixture: List[LastBarterBaseModel],
                              fills_journal_basemodel_fixture: List[FillsJournalBaseModel],
                              chore_snapshot_basemodel_fixture: List[ChoreSnapshotBaseModel],
                              chore_journal_basemodel_fixture: List[ChoreJournalBaseModel],
                              plan_limits_fixture: PlanLimitsBaseModel) -> None:
    """

    Function for creating top_of_book, market_depth, last_barter,
    fills_journal, chore_snapshot, chore_journal, using the web client.

    The function sets up and executes a series of tests to ensure the proper
    creation and functionality of various components related to data
    and performance analysis.

    :return: None
    """
    widget_name: str = WidgetName.PlanCollection.value
    widget: WebElement = driver.find_element(By.ID, widget_name)
    activate_plan(widget, driver)
    time.sleep(Delay.SHORT.value)

    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()
    pair_plan: PairPlanBaseModel = pair_plan_list[-1]

    while not pair_plan.is_executor_running:
        pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()
        pair_plan: PairPlanBaseModel = pair_plan_list[-1]
        time.sleep(Delay.SHORT.value)
    assert pair_plan.is_executor_running

    # top of book
    executor_web_client = StreetBookServiceHttpClient(pair_plan.host, pair_plan.port)
    created_top_of_book_list = create_tob("Type1_Sec_1", "Type2_Sec_1", top_of_book_fixture, executor_web_client)

    # assert created_top_of_book_list == top_of_book_fixture, f"Top of book mismatch: Expected {top_of_book_fixture}, but got {created_top_of_book_list}"

    # Market Depth
    created_market_depth_list: List[MarketDepthBaseModel] = executor_web_client.create_all_market_depth_client(
        market_depth_basemodel_fixture)
    assert created_market_depth_list == market_depth_basemodel_fixture, f"MarketDepth mismatch: Expected {market_depth_basemodel_fixture}, but got {created_market_depth_list}"

   # # Plan Limits
   #  created_plan_limits_list: PlanLimitsBaseModel = executor_web_client.create_plan_limits_client(plan_limits_fixture)
   #  assert created_plan_limits_list == plan_limits_fixture, f"Expected{plan_limits_fixture}, but got {created_plan_limits_list}"

    # Last Barter
    created_last_barter_list: List[LastBarterBaseModel] = executor_web_client.create_all_last_barter_client(
        last_barter_basemodel_fixture)
    assert created_last_barter_list == last_barter_basemodel_fixture, f"LastBarter mismatch: Expected {last_barter_basemodel_fixture}, but got {created_last_barter_list}"

    # Fills Journal
    for expected_fills_journal in fills_journal_basemodel_fixture:
        created_fills_journal: FillsJournalBaseModel = executor_web_client.create_fills_journal_client(
            expected_fills_journal)
        expected_fills_journal.fill_notional = created_fills_journal.fill_notional
        assert created_fills_journal == expected_fills_journal, f"FillsJournal mismatch: Expected {expected_fills_journal}, but got {created_fills_journal}"

    # Chore Snapshot
    for expected_chore_snapshot in chore_snapshot_basemodel_fixture:
        created_chore_snapshot: ChoreSnapshotBaseModel = executor_web_client.create_chore_snapshot_client(
            expected_chore_snapshot)
        assert created_chore_snapshot == expected_chore_snapshot, f"ChoreSnapshot mismatch: Expected {expected_chore_snapshot}, but got {created_chore_snapshot}"

    # Chore Journal
    for expected_chore_journal in chore_journal_basemodel_fixture:
        created_chore_journal: ChoreJournalBaseModel = executor_web_client.create_chore_journal_client(
            expected_chore_journal)
        expected_chore_journal.chore.chore_notional = created_chore_journal.chore.chore_notional
        assert expected_chore_journal == created_chore_journal, f"ChoreJournal mismatch: Expected {expected_chore_journal}, but got {created_chore_journal}"


def delete_tob_md_ld_fj_os_oj() -> None:
    """

        Function for deleting top_of_book, market_depth, last_barter,
        fills_journal, chore_snapshot, chore_journal, using the web client.

        The function sets up and executes a series of tests to ensure the proper
        creation and functionality of various components related to data
        and performance analysis.

        :return: None
    """
    pair_plan_list: List[PairPlanBaseModel] = email_book_service_native_web_client.get_all_pair_plan_client()

    for pair_plan in pair_plan_list:
        if not pair_plan.is_executor_running:
            err_str_ = ("plan exists but is not running, can't delete top_of_book, market_depth, last_barter, "
                        "fills_journal, chore_snapshot, chore_journal when not running, delete it manually")
            logging.error(err_str_)
            raise Exception(err_str_)
        assert pair_plan.is_executor_running

        executor_web_client = StreetBookServiceHttpClient(pair_plan.host, pair_plan.port)

        for _ in range(1, 3):
            assert executor_web_client.delete_top_of_book_client(top_of_book_id=_, return_obj_copy=False)

        for _ in range(1, 21):
            assert executor_web_client.delete_market_depth_client(market_depth_id=_, return_obj_copy=False)

        assert executor_web_client.delete_all_last_barter_client(return_obj_copy=False)

        for _ in range(1, 11):
            assert executor_web_client.delete_fills_journal_client(fills_journal_id=_, return_obj_copy=False)

        for _ in range(1, 11):
            assert executor_web_client.delete_chore_snapshot_client(chore_snapshot_id=_, return_obj_copy=False)

        for _ in range(1, 11):
            assert executor_web_client.delete_chore_journal_client(chore_journal_id=_, return_obj_copy=False)


def scroll_into_view(driver: WebDriver, element: WebElement):
    driver.execute_script('arguments[0].scrollIntoView(true)', element)
    time.sleep(Delay.SHORT.value)


def click_button_with_name(widget: WebElement, button_name: str):
    btn_element = widget.find_element(By.NAME, button_name)
    btn_element.click()
    time.sleep(Delay.SHORT.value)


def click_save_with_widget_name(driver: WebDriver, widget: WebElement, widget_name: str):
    if widget_name in [WidgetName.PairPlanParams.value]:
        widget = driver.find_element(By.ID, WidgetName.PlanCollection.value)
    click_button_with_name(widget, "Save")


def refresh_page_n_short_delay(driver: WebDriver):
    driver.refresh()
    time.sleep(Delay.SHORT.value)


def refresh_page_n_default_delay(driver: WebDriver):
    driver.refresh()
    time.sleep(Delay.DEFAULT.value)


def delete_ol_pl_ps_client(driver: WebDriver):
    # chore_limits_obj = ChoreLimitsBaseModel(id=55, max_px_deviation=44)
    # email_book_service_native_web_client.delete_pair_plan_client(pair_plan_id=1)
    email_book_service_native_web_client.delete_chore_limits_client(chore_limits_id=1)
    email_book_service_native_web_client.delete_contact_limits_client(contact_limits_id=1)
    email_book_service_native_web_client.delete_contact_status_client(contact_status_id=1)
    refresh_page_n_default_delay(driver)


def flux_fld_default_widget(schema_dict: Dict, widget: WebElement, widget_type: WidgetType,
                            widget_name: str,
                            layout: Layout, field_query):
    try:
        field_name: str = field_query.field_name
        schema_default_value: str = field_query.properties['default']
        if field_name not in ["exch_response_max_seconds", "fallback_broker", "sec_id_source", "dismiss"]:
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=widget_type,
                                                   widget_name=widget_name, field_name=field_name)
            field_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
            assert field_value == str(schema_default_value), \
                (f"Field {field_name} value mismatch with schema default value {schema_default_value} "
                 f"but got field_value_frm_ui {field_value} for widget {widget_name}")
    except Exception as e:
        print(e)


def get_select_box_value(select_box: WebElement) -> str:
    try:
        # Find the div element containing the selected value
        value_div = select_box.find_element(By.CLASS_NAME, "MuiInputBase-input")
        # Get the text content of the div element
        selected_value = value_div.text
        return selected_value
    except Exception as e:
        print(f"Error: {e}")
        return ""


def get_field_name_from_setting(driver: WebDriver, widget_name: str):
    fld_elements: List[WebElement] = get_fld_name_elements_from_setting(driver, widget_name)
    fld_names_list = []
    for fld_element in fld_elements:
        fld_names_list.append(fld_element.text)
    return fld_names_list


def get_fld_name_elements_from_setting(driver: WebDriver, widget_name: str) -> List[WebElement]:
    tooltip_widget = get_setting_tooltip_widget(driver, widget_name)
    try:
        css_selector = get_css_selector_with_partial_class_name_n_tag_name("MuiFormControlLabel-root", "label")
        label_elements = tooltip_widget.find_elements(By.CSS_SELECTOR, css_selector)
        fld_elements = []
        for label_element in label_elements:
            try:
                css_selector = get_css_selector_with_partial_class_name_n_tag_name("MuiTypography-root", "span")
                span_element = label_element.find_element(By.CSS_SELECTOR, css_selector)
                fld_elements.append(span_element)
            except NoSuchElementException:
                continue
        return fld_elements
    except Exception as e:
        print("Exception", e)



def get_setting_tooltip_widget(driver: WebDriver, widget_name: str):
    tooltip_id = get_table_setting_id_with_widget_name(widget_name)
    tooltip_widget = driver.find_element(By.ID, tooltip_id)
    return tooltip_widget


def get_fld_sequence_number_from_setting(driver: WebDriver, widget_name: str) -> Dict[str, int]:
    sequence_num_element_list = get_table_setting_sequence_element(driver, widget_name)

    # Get sequence numbers
    sequence_num_list = [
        seq_num.text
        for seq_num in sequence_num_element_list]

    # Get field names
    fld_names: List[str] = get_field_name_from_setting(driver, widget_name)

    # Create a dictionary using zip
    field_sequence_dict = {fld_name: int(seq_num) for fld_name, seq_num in zip(fld_names, sequence_num_list)}

    return field_sequence_dict


def get_table_setting_sequence_element(driver: WebDriver, widget_name: str) -> List[WebElement]:
      tooltip_widget = get_setting_tooltip_widget(driver, widget_name)
      li_css_selector = get_css_selector_with_partial_class_name_n_tag_name("MuiButtonBase-root", "li")
      li_elements = tooltip_widget.find_elements(By.CSS_SELECTOR, li_css_selector)
      sequence_num_element_list = []
      for li_element in li_elements:
          try:
              sequence_num_element = li_element.find_element(By.TAG_NAME, "div")
              sequence_num_element_list.append(sequence_num_element)
          except NoSuchElementException:
              continue
      return sequence_num_element_list



def get_placeholder_from_element(widget: WebElement, id: str) -> str:
    input_element = widget.find_element(By.ID, id)
    return input_element.get_attribute('placeholder')


def get_n_validate_flux_fld_sequence_number_in_widget(schema_dict, driver: WebDriver, widget_type: WidgetType):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=widget_type,
                                          flux_property=FluxPropertyType.FluxFldSequenceNumber)
    assert result[0]


    for widget_query in result[1]:
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        i: int = 1
        sequence_number: int = 0
        previous_field_sequence_value: int = 0
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)

        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TABLE)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Settings")

        for field_query in widget_query.fields:
            field_name = field_query.field_name
            if field_name == "kill_switch" or field_name == "plan_state":
                continue
            i += 1
            sequence_number += 1
            if widget_type == WidgetType.INDEPENDENT or widget_type == WidgetType.REPEATED_INDEPENDENT:
                field_sequence_value_element: WebElement = widget.find_element(
                    By.XPATH, f'//*[@id="{widget_name}_table_settings"]/div[3]/li[{i}]/div[1]')
            else:
                if widget_name == "pair_plan_params":
                    widget_name = "pair_plan"
                field_sequence_value_element: WebElement = widget.find_element(
                    By.XPATH, f'//*[@id="definitions.{widget_name}_table_settings"]/div[3]/li[{i}]/div[1]')
            field_sequence_value: int = int(get_select_box_value(field_sequence_value_element))
            if (field_sequence_value - previous_field_sequence_value) > 1:
                sequence_number += ((field_sequence_value - previous_field_sequence_value) - 1)
            previous_field_sequence_value = field_sequence_value
            assert sequence_number == field_sequence_value


def flux_fld_ui_place_holder_in_widget(schema_dict, driver: WebDriver, widget_type: WidgetType):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=widget_type,
                                          flux_property=FluxPropertyType.FluxFldUIPlaceholder)
    print(result)
    assert result[0]

    for widget_query in result[1]:
        refresh_page_n_default_delay(driver)
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        if widget_type != WidgetType.REPEATED_INDEPENDENT:
            switch_layout(widget=widget, layout=Layout.TREE)
        if widget_name in ["basket_chore"]:
            continue

        if widget_name == "pair_plan_params":
            click_button_with_name(driver.find_element(By.ID, "plan_collection"), button_name="Create")
        else:
            click_button_with_name(widget=widget, button_name="Create")
        show_nested_fld_in_tree_layout(widget=widget, driver=driver)

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            placeholder: str = get_placeholder_from_element(widget=widget, id=field_name)
            default_placeholder: str = field_query.properties['ui_placeholder']
            assert default_placeholder == placeholder


def get_element_text_list_from_filter_popup(driver: WebDriver) -> List[str]:
    # content_element = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")
    # menu_filters = driver.find_elements(By.CLASS_NAME, "DynamicMenu_filter__5r8Ey")
    menu_filters = driver.find_elements(By.CLASS_NAME, "DynamicMenu_filter__yvGMZ")
    element_texts: List[str] = []
    for menu_filter in menu_filters:
        span_element = menu_filter.find_element(By.TAG_NAME, "span")
        element_texts.append(span_element.text.replace(" ", "_"))
        # element_texts: List[str] = [element.text.replace(" ", "_") for element in span_element]
    return element_texts


def flux_fld_title_in_widgets(result: List[WidgetQuery], widget_type: WidgetType, driver: WebDriver) -> None:
    for widget_query in result:
        widget_name: str = widget_query.widget_name
        # fixme: `contact_status` and `plan_alert` is not been created
        #  (`plan_status`: most of the field is not present )
        if widget_name in ["contact_status", "plan_alert", "plan_status", "system_control", "basket_chore",
                           "chore_limits"]:
            continue
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=Layout.TABLE)
        show_hidden_fields_in_table_layout(driver, widget, widget_name)
        # common_keys_dict: Dict[str, str] = get_replaced_underscore_common_key(widget, driver)
        for field_query in widget_query.fields:
            if widget_type == WidgetType.INDEPENDENT:
                field_title: str = field_query.properties["title"].replace(" ", "_")
                if field_title not in ["max_contract_qty", "security", "positions", "eligible_brokers_update_count",
                                       "min_chore_notional_allowance", "alerts", "max_px_levels", "max_chore_qty", "figi", "chore_account", "eqt_sod_disable"]:
                    validate_flx_fld_title(field_title=field_title, widget=widget,
                                           driver=driver)


            elif widget_type == WidgetType.DEPENDENT:
                field_name: str = field_query.field_name
                field_title: str | None = field_query.properties.get("parent_title")
                if field_title is not None:
                    field_title = field_title + "." + field_name
                else:
                    field_title = field_query.properties["title"].replace(" ", "_")
                if field_name not in ["company", "side", "sec_id"]:
                    validate_flx_fld_title(field_title=field_title, widget=widget, driver=driver)


def close_popover(driver: WebDriver) -> None:
    close_setting(driver)


def validate_flx_fld_title(field_title: str, widget: WebElement, driver: WebDriver) -> None:
    # keep function call of common key here,
    # when replace n get last fld name from dict all then all the fld replaced so need to fetch common key again n again
    common_keys_dict: Dict[str, str] = get_replaced_underscore_common_key(widget, driver)
    try:
        assert field_title in common_keys_dict, f"'{field_title}' not found in common_keys_dict"
    except AssertionError:
        if "eligible_brokers" in field_title:
            common_keys_dict = replace_array_n_its_zero_with_empty_from_dict_key(common_keys_dict)
            assert field_title in common_keys_dict, f"'{field_title}' not found in field_title_dict"
        else:
            try:
                common_keys_dict = replace_n_get_last_fld_name_from_dict(common_keys_dict)
                assert field_title in common_keys_dict, f"'{field_title}' not found in field_title_dict"
            except AssertionError as e:
                print(f"Exception after retry: {e}")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")



def replace_array_n_its_zero_with_empty_from_dict_key(string: Dict[str, str]) -> Dict[str, str]:
    common_keys_dict = {}
    for key, value in string.items():
        if "[0]" in key:
            key = key.replace("[0]", "")
            common_keys_dict[key] = value
    return common_keys_dict


def replace_n_get_last_fld_name_from_dict(string: Dict[str, str]) -> Dict[str, str]:
    field_title_dict = {key.split(".")[-1]: value for key, value in string.items()}
    return field_title_dict






def get_current_ui_layout_name(widget: WebElement):
    button: WebElement = widget.find_element(By.NAME, "Layout")
    ui_view_layout: str = button.get_attribute('aria-label').split(":")[-1].replace(" ", "")
    return ui_view_layout


def flux_fld_autocomplete_in_widgets(result: List[WidgetQuery], auto_complete_dict: Dict[str, any]):
    for widget_query in result:
        for field_query in widget_query.fields:
            auto_complete_value_list = [field_auto_complete_property.split(":")[1]
                                        if ":" in field_auto_complete_property
                                        else field_auto_complete_property.split("=")[1]
            if "=" in field_auto_complete_property else field_auto_complete_property for
                                        field_auto_complete_property
                                        in field_query.properties.get("auto_complete").split(",")]
            for auto_complete_value in auto_complete_value_list:
                assert (auto_complete_value in auto_complete_dict or
                        (auto_complete_value in values for values in auto_complete_dict.values()))


def get_btn_caption(widget: WebElement, index_no: int):
    btn_td_elements: [WebElement] = widget.find_elements(By.CLASS_NAME, "MuiToggleButton-sizeMedium")
    btn_caption = btn_td_elements[index_no].text
    return btn_caption


def get_btn_caption_class_elements(widget: WebElement):
    btn_td_elements: [WebElement] = widget.find_elements(By.CLASS_NAME, "MuiToggleButton-sizeMedium")
    return btn_td_elements


def validate_unpressed_n_pressed_btn_txt(ui_unpressed_n_pressed_captions, schema_pressed_n_pressed_captions):
    assert schema_pressed_n_pressed_captions == ui_unpressed_n_pressed_captions, f"Expected unpressed btn txt '{schema_pressed_n_pressed_captions}', but got '{ui_unpressed_n_pressed_captions}'"



def validate_hide_n_show_in_common_key(widget, hide_n_show_fld: str, button_state: ButtonState):
    try:
        common_keys_fields: List[str] = get_common_keys_fld_names(widget=widget)
    except NoSuchElementException:
        common_keys_fields: List[str] = get_table_headers(widget=widget)

    if hide_n_show_fld == "sec_id":
        for common_key_fld in common_keys_fields:
            if common_key_fld == "sec_id":
                fld_locator = common_key_fld.replace("sec_id", "security.sec_id")
                common_keys_fields.append(fld_locator)
                break

    if button_state == button_state.HIDE:
        assert hide_n_show_fld not in common_keys_fields, f"{hide_n_show_fld} is showing inside common key but it must be hidden"
    else:
        assert hide_n_show_fld in common_keys_fields, f"{hide_n_show_fld} is hidden inside common key but it must be show"


def validate_val_max_fields_in_widget(driver: WebDriver, widget: WebElement, widget_name: str, input_type: InputType,
                                      xpath_n_field_names: Dict):
    expand_all_nested_fld_name_frm_review_changes_dialog(driver=driver)
    object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
    for field_name, xpath in xpath_n_field_names.items():
        if widget_name == WidgetName.PlanLimits.value and input_type == InputType.INVALID_VALUE:
            assert xpath in object_keys, f"Field '{field_name}' was expected but is missing in {object_keys} inside widget:- {widget_name}. (XPath used: {xpath})"
        else:
            assert field_name in object_keys, f"Field '{field_name}' was expected but is missing in {object_keys} inside widget:-{widget_name}. (XPath used: {xpath})"
    if input_type == InputType.MAX_VALID_VALUE:
        click_confirm_save(driver=driver)
    else:
        discard_changes(widget=widget)
    # deleting all the data of dict to again reuse for validating for others widget again
    xpath_n_field_names.clear()


def validate_flux_fld_val_min_in_widget(widget: WebElement, field_name: str):
    click_button_with_name(widget=widget, button_name="Save")
    object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
    assert field_name in object_keys
    discard_changes(widget=widget)


def get_val_min_n_val_max_of_fld(field_query: Any) -> Tuple[str, str]:
    val_min: str = (field_query.properties.get("val_min"))
    val_max: str = (field_query.properties.get("val_max"))
    return val_min, val_max


def is_property_contain_val_min_val_max_or_none(val_max: str, val_min: str) -> str:
    try:
        if val_min:
            val_min = int(val_min) + 1
            return str(val_min)
        elif val_max:
            val_max = int(val_max) - 1
            return str(val_max)
    except ValueError:
        print("Invalid input: must be a numeric value or empty.")
    return str(1000.5)


def get_random_num_according_to_val_min_n_val_max(field_query):
    get_val_min_n_val_max_of_fld(field_query=field_query)
    pass


def get_replaced_underscore_common_key(widget: WebElement, driver: WebDriver) -> Dict[str, str]:
    common_key_items = get_common_keys_items(widget=widget, driver=driver)
    under_score_fld_names = {}
    for field_name, value in common_key_items.items():
        under_score_fld_name = field_name.replace(" ", "_")
        under_score_fld_names[under_score_fld_name] = value
    return under_score_fld_names


def get_replaced_dollar_symbol_with_notional_common_key(common_key_items: Dict[str, str]) -> Dict[str, str]:
    under_score_fld_names = {}
    for field_name, value in common_key_items.items():
        under_score_fld_name = field_name.replace("$", "notional")
        under_score_fld_names[under_score_fld_name] = value
    return under_score_fld_names


def get_replaced_value_without_num_format_common_key(common_key_items):
    value_without_num_format = {}
    for field_name, value in common_key_items.items():
        # Replace unwanted characters in the value
        value = value.replace(" $", "").replace(" bps", "").replace(" %", "")
        # Use field_name as the key in the new dictionary
        value_without_num_format[field_name] = value
    return value_without_num_format


def get_common_key_value_without_num_format(widget: WebElement, driver: WebDriver) -> Dict[str, str]:
    under_score_common_keys = get_replaced_underscore_common_key(widget, driver)
    replaced_dollar_symbol = get_replaced_dollar_symbol_with_notional_common_key(under_score_common_keys)
    value_without_num_format = get_replaced_value_without_num_format_common_key(replaced_dollar_symbol)
    return value_without_num_format


def validate_flux_fld_display_type_in_widget(widget: WebElement, field_name_n_xpath: Union[Dict[str, str], str, List], layout: Layout, driver: WebDriver):
    if layout == Layout.TREE:
        switch_layout(widget=widget, layout=Layout.TABLE)
    value_without_num_format = get_common_key_value_without_num_format(widget=widget, driver=driver)
    for field_name, xpath in field_name_n_xpath.items():
        try:
            input_value = int(value_without_num_format[xpath].replace(",", ""))
            assert isinstance(input_value, int), f"The input value '{input_value}' for '{xpath}' is not an integer."
        except KeyError:
            try:
                input_value = int(value_without_num_format[field_name].replace(",", ""))
                assert isinstance(input_value, int), f"The input value '{input_value}' for '{xpath}' is not an integer."
            except Exception as e:
                print(f"Exception:-- {e}")


def validate_flux_fld_number_format_in_widget(number_format_txt: str, number_format: str):
    # number_format: str = get_flux_fld_number_format(widget=widget, xpath=xpath, layout=layout)
    assert number_format_txt == number_format


def validate_flux_flx_display_zero_in_widget(driver: WebDriver, widget: WebElement, field_name: str, value: str):
    click_button_with_name(widget=widget, button_name="Save")
    click_confirm_save(driver=driver)
    switch_layout(widget=widget, layout=Layout.TABLE)
    get_common_key_dict: Dict[str, any] = get_commonkey_items(widget=widget)
    assert value == get_common_key_dict[field_name]


def is_schema_n_default_fld_value_equal(widget, value: int, layout: Layout, xpath: str) -> bool:
    """function to validate the ui val_max and schema val_max is equals or not"""
    default_field_value: str = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    if default_field_value:
        # if str contain comma so we need to replace that then we can typecast into int
        # TODO: Lazy create a function for this
        return True if value == int(default_field_value.replace(",", "")) else False


def is_val_min_n_default_fld_value_equal(widget, val_min: int, layout: Layout, xpath: str) -> bool:
    """function to validate the ui val_max and schema val_max is equals or not"""
    default_field_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    if default_field_value:
        return val_min == int(default_field_value)


def show_nested_fld_in_tree_layout(driver: WebDriver, widget: WebElement):
    xpath = get_xpath_with_attribute(tag_name="button", attribute_name="aria-label", attribute_value="More Options")
    more_options = widget.find_elements(By.XPATH, xpath)
    for i in range(len(more_options)):
        # Re-locate 'more_options' to get the current element in the DOM
        more_option = widget.find_elements(By.XPATH, xpath)[i]
        more_option.click()
        time.sleep(Delay.SHORT.value)
        # plus btn
        css_selector = get_css_selector_with_partial_class_name("HeaderField_menu")
        css_element = widget.find_element(By.CSS_SELECTOR, css_selector)
        options_btn = css_element.find_element(By.TAG_NAME, "button")
        options_btn.click()
        time.sleep(Delay.SHORT.value)
        close_setting(driver)


def get_css_selector_with_partial_class_name(partial_class_name: str) -> str:
    """
    Generate a CSS selector that matches elements with a class name containing a specified substring.

    Args:
        partial_class_name (str): The substring to match within class names.

    Returns:
        str: A CSS selector that selects elements with class names containing the specified substring.
    """
    return f"[class*={partial_class_name}]"


def get_css_selector_of_dynamic_class_name_with_initial_class_name(initial_class_name: str):
    return f"[class^='{initial_class_name}']"


def get_val_of_fld_from_schema(field_query: Any, val_max: FluxPropertyType) -> int:
    """Function to retrieve either val_min or val_max from field_query properties."""
    if val_max not in {"val_min", "val_max"}:
        raise ValueError("val_type must be 'val_min' or 'val_max'")

    return field_query.properties.get(val_max)


def convert_schema_dict_to_widget_query(schema_dict: Dict[str, Any]) -> List[WidgetQuery]:
    widget_queries = []

    for widget_name, widget_data in schema_dict.items():
        fields = []
        if "properties" in widget_data:
            for field_name, field_data in widget_data["properties"].items():
                field_query = FieldQuery(field_name=field_name, properties=field_data)  # Renamed 'field' to 'field_query'
                fields.append(field_query)

        widget_query = WidgetQuery(
            widget_name=widget_name,
            widget_data=widget_data,
            fields=fields,
        )
        widget_queries.append(widget_query)

    return widget_queries



def update_schema_json(schema_dict: Dict[str, any], update_widget_name: str, update_field_name: str,
                       extend_field_name: str, value: any, project_name: str) -> None:
    project_path: PurePath = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / project_name

    schema_path: PurePath = project_path / "web-ui" / "public" / "schema.json"

    for widget_name, widget_data in schema_dict.items():
        update_field_name_properties = widget_data.get(update_field_name)
        widget_properties = widget_data.get("properties")
        if (widget_name == update_widget_name and widget_properties is not
                None and update_field_name_properties is None):
            widget_properties[update_field_name][extend_field_name] = value
        elif widget_name == update_widget_name and update_field_name_properties is not None:
            widget_data[update_field_name][extend_field_name] = value

    with open(str(schema_path), "w") as f:
        json.dump(schema_dict, f, indent=2)


def save_layout(driver: WebDriver, layout_name: str) -> None:
    driver.find_element(By.NAME, "SaveLayout").click()
    time.sleep(Delay.SHORT.value)
    layout_dialog_ele = get_dialog_element(driver)
    input_element = layout_dialog_ele.find_element(By.TAG_NAME, "input")
    click_element_n_short_delay(input_element)
    delete_data_from_input_fld(driver, input_element)
    input_element.send_keys(layout_name)
    # save the layout
    click_save_or_load_layout(driver, is_load=False)


def load_layout(driver: WebDriver, layout_name: str) -> None:
    # change the layout
    element = driver.find_element(By.NAME, "LoadLayout")
    click_element_n_short_delay(element)
    layout_dialog_ele = get_dialog_element(driver)
    input_ele = layout_dialog_ele.find_element(By.TAG_NAME, "input")
    click_element_n_short_delay(input_ele)
    input_ele.send_keys(layout_name)
    click_element_n_short_delay(input_ele)
    input_ele.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
    # load btn
    click_save_or_load_layout(driver, is_load=True)


def click_unload_btn(widget: WebElement):
    css_selector = get_css_selector_of_dynamic_class_name_with_initial_class_name("MuiTableContainer-root")
    table_row = widget.find_element(By.CSS_SELECTOR, css_selector)
    xpath = get_xpath_with_attribute(tag_name="button", attribute_name="value", attribute_value="Unload Plan")
    unload_btn = table_row.find_element(By.XPATH, xpath)
    click_element_n_short_delay(unload_btn)


def click_n_get_input_element_of_buffer_plan_keys_in_plan_collection(widget: WebElement) -> WebElement:
    container_element = get_buffer_plan_dropdown_container_element(widget)
    input_element = container_element.find_element(By.TAG_NAME, "input")
    click_element_n_short_delay(input_element)
    return input_element


def load_plan(widget: WebElement):
    select_buffer_plan_key_from_dropdown(widget)
    container_element = get_buffer_plan_dropdown_container_element(widget)
    container_elements = container_element.find_elements(By.TAG_NAME, "button")
    click_element_n_short_delay(container_elements[1])


def select_buffer_plan_key_from_dropdown(widget: WebElement):
    input_element = click_n_get_input_element_of_buffer_plan_keys_in_plan_collection(widget)
    input_element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
    time.sleep(Delay.SHORT.value)


def get_buffer_plan_dropdown_container_element(widget: WebElement) -> WebElement:
    css_selector = get_css_selector_of_dynamic_class_name_with_initial_class_name(
        "AbbreviatedFilterWidget_dropdown_container")
    container_element = widget.find_element(By.CSS_SELECTOR, css_selector)
    return container_element


def get_xpath_with_attribute(tag_name: str, attribute_name: str, attribute_value: str):
    return f"//{tag_name}[@{attribute_name}='{attribute_value}']"


def unload_plan(widget: WebElement, driver: WebDriver):
    click_unload_btn(widget)
    click_confirm_save(driver)


def get_input_fld_for_save_n_load_layout(driver: WebDriver):
    mui_btn_base_element = get_mui_btn_base_root_class_element_on_global_search(driver)
    return mui_btn_base_element


def click_save_or_load_layout(driver: WebDriver, is_load: bool):
    layout_dialog_element = get_dialog_element(driver)
    css_selector = get_css_selector_with_partial_class_name("MuiDialogActions-root")
    load_btn = layout_dialog_element.find_element(By.CSS_SELECTOR, css_selector)
    buttons_elements = load_btn.find_elements(By.TAG_NAME, "button")
    if is_load:
        buttons_element = buttons_elements[1]
    else:
        buttons_element = buttons_elements[0]
    click_element_n_short_delay(buttons_element)


def get_mui_btn_base_root_class_element_on_global_search(driver: WebDriver, single: bool = True) -> Union[
    WebElement, List[WebElement]]:
    """
    Retrieves a web element or a list of web elements based on the given CSS selector.

    :param driver: The WebDriver instance to interact with the browser.
    :param : The CSS selector to find the elements.
    :param single: If True, return a single WebElement; if False, return a list of WebElements.
    :return: A WebElement or a list of WebElements.
    """
    css_selector = get_css_selector_with_partial_class_name("MuiInputBase-root")
    elements = driver.find_elements(By.CSS_SELECTOR, css_selector)
    if single:
        if elements:
            return elements[0]
    return elements


def double_click(driver: WebDriver, element: WebElement):
    actions = ActionChains(driver)
    actions.double_click(element).perform()


def hover_over_on_element(driver: WebDriver, element: WebElement):
    actions = ActionChains(driver)
    actions.move_to_element(element).perform()


def verify_dialog_type_n_save_or_discard_changes(widget: WebElement, driver: WebDriver) -> None:
    dialog_element = widget.find_element(By.XPATH, "//div[@role='dialog']")
    text_element = dialog_element.find_element(By.TAG_NAME, "p")
    dialog_text = text_element.text
    if dialog_text == "Review changes:":
        click_confirm_save(driver=driver)
    elif dialog_text == "Form validation failed due to following errors:":
        discard_changes(widget)


def get_pressed_n_unpressed_btn_txt(widget: WebElement) -> str:
    button_widget = widget.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    button_text = button_widget.text
    return button_text


def validate_server_populate_fld(widget: WebElement, xpath: str, field_name: str, layout: Layout):
    if layout == Layout.TABLE:
        is_enabled, _ = is_table_cell_enabled_n_get_input_element(widget=widget, xpath=xpath)
        assert not is_enabled
    else:
        field_names: List[str] = count_fields_in_tree(widget=widget)
        # validate that server populates field name does not present in tree layout after clicking on edit btn
        assert field_name not in field_names


def input_n_validate_progress_bar(driver: WebDriver, widget: WebElement, field_name: str, value: str,
                                  input_value_type: str):
    switch_layout(widget=widget, layout=Layout.TREE)
    click_button_with_name(widget=widget, button_name="Edit")
    set_tree_input_field(driver=driver, widget=widget, xpath="balance_notional", name=field_name, value=value)
    click_button_with_name(widget=widget, button_name="Save")
    click_confirm_save(driver)
    progress_level: str = get_progress_bar_level(widget)
    if input_value_type == "val_min":
        # if input value is 0 then progress level should be 100
        assert progress_level == "100"
    else:
        # for val max
        assert progress_level == "0"


def get_chart_name(widget: WebElement) -> str:
    chart_widget = widget.find_element(By.CLASS_NAME, "MuiListItem-root")
    text_element = chart_widget.find_element(By.CLASS_NAME, "MuiTypography-body1")
    text = text_element.text
    return text

def set_val_max_input_fld(schema_dict: Dict[str, any], driver: WebDriver, widget_type: WidgetType, layout: Layout,
                          input_type: InputType, flux_property: FluxPropertyType):
    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=widget_type,
                                          flux_property=flux_property)

    assert result[0]
    print(result)

    xpath_n_field_names: Dict[str, str] = {}
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = get_widget_element_n_scroll_into_view(driver=driver, widget_name=widget_name)
        click_edit_n_switch_layout(driver=driver, widget=widget, layout=layout)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            val_max: int = get_val_of_fld_from_schema(field_query=field_query, val_max=flux_property)
            xpath = get_xpath_from_field_name(schema_dict=schema_dict,
                                              widget_type=widget_type, widget_name=widget_name, field_name=field_name)
            xpath_n_field_names[field_name] = xpath

            input_value: int = get_valid_n_invalid_value_for_input(widget, layout, val_max, input_type, xpath)

            set_input_field_on_layout(driver=driver,widget=widget, layout=layout, xpath=xpath, field_name=field_name,
                                      value=str(input_value))
        click_save_with_widget_name(driver, widget, widget_name)
        validate_val_max_fields_in_widget(driver=driver, widget=widget, widget_name=widget_name, input_type=input_type,
                                          xpath_n_field_names=xpath_n_field_names)


def get_widget_element_n_scroll_into_view(driver: WebDriver, widget_name: str) -> WebElement:
    widget: WebElement = driver.find_element(By.ID, widget_name)
    scroll_into_view(driver, element=widget)
    return widget


def get_valid_n_invalid_value_for_input(widget: WebElement, layout: Layout, schema_value: int, input_type: InputType,
                                        xpath: str) -> int:
    is_equal = is_schema_n_default_fld_value_equal(widget, schema_value, layout, xpath)
    time.sleep(Delay.SHORT.value)

    fld_value = int(get_value_from_input_field(widget=widget, xpath=xpath, layout=layout).replace(",", ""))

    if input_type == InputType.MAX_VALID_VALUE:
        if is_equal:
            # If schema and default value are equal, return schema - 1
            return schema_value - 1
        else:
            # If they are not equal, fetch the value from UI, subtract 1, and return
            return fld_value - 1

    elif input_type == InputType.INVALID_VALUE:
        if is_equal:
            # If schema and default value are equal, return schema + 1 for invalid scenario
            return schema_value + 1
        else:
            # If they are not equal, fetch the value from UI, add 1, and return
            return schema_value + 1


def get_valid_n_invalid_value_for_val_min(widget: WebElement, layout: Layout, schema_value: int, input_type: InputType,
                                          xpath: str):
    is_equal = is_schema_n_default_fld_value_equal(widget, schema_value, layout, xpath)

    fld_value = int(get_value_from_input_field(widget=widget, xpath=xpath, layout=layout).replace(",", ""))

    if input_type == InputType.MIN_VALID_VALUE:
        if is_equal:
            # If schema and default value are equal, return schema - 1
            return schema_value + 10
        else:
            # If they are not equal, fetch the value from UI, subtract 1, and return
            return fld_value - 1

    elif input_type == InputType.MIN_INVALID_VALUE:
        if is_equal:
            # If schema and default value are equal, return schema + 1 for invalid scenario
            return schema_value - 20
        else:
            # If they are not equal, fetch the value from UI, add 1, and return
            return fld_value + 20


def click_edit_n_switch_layout(driver: WebDriver, widget: WebElement, layout: Layout):
    click_edit_btn(driver=driver, widget=widget)
    switch_layout(widget=widget, layout=layout)


def set_n_validate_val_min_input_fld(driver: WebDriver, flux_property: FluxPropertyType, widget_type: WidgetType,
                                     layout: Layout, input_type: InputType, schema_dict: Dict[str, any]):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=widget_type,
                                          flux_property=flux_property)

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = get_widget_element_n_scroll_into_view(driver=driver, widget_name=widget_name)
        click_edit_n_switch_layout(driver=driver, widget=widget, layout=layout)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name in ["accounts_nett_notional"]:
                continue
            xpath = get_xpath_from_field_name(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                              widget_name=widget_name,
                                              field_name=field_name)
            val_min: int = get_val_of_fld_from_schema(field_query=field_query, val_max=flux_property)
            input_value: int = get_valid_n_invalid_value_for_val_min(widget, layout, val_min, input_type, xpath)

            set_input_field_on_layout(driver=driver, widget=widget, layout=layout, xpath=xpath, field_name=field_name,
                                      value=str(input_value))

            validate_flux_fld_val_min_in_widget(widget=widget, field_name=field_name)


def get_n_validate_server_populate_fld(driver: WebDriver, schema_dict, layout: Layout, widget_type: WidgetType):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict),
                                          widget_type=widget_type,
                                          flux_property=FluxPropertyType.FluxFldServerPopulate)
    assert result[0]

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        # SYSTEM CONTROL WIDGET IS ALREADY IN CREATE MODE SO EDIT BTN GeT invisible,
        # chore limits switch layout btn is not visible
        if widget_name in ["system_control", "basket_chore", "chore_limits"]:
            continue
        show_hidden_fields_for_layout(widget=widget, driver=driver, layout=layout, widget_name=widget_name)
        if layout == Layout.TABLE:
            if widget_type != WidgetType.DEPENDENT:
                click_button_with_name(widget=widget, button_name="Edit")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=widget_type,
                                              widget_name=widget_name,
                                              field_name=field_name)

            validate_server_populate_fld(widget=widget, xpath=xpath, field_name=field_name,
                                         layout=layout)


def set_n_validate_input_value_for_comma_seperated(driver: WebDriver, schema_dict, layout: Layout):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert result[0]
    try:
        # TABLE LAYOUT
        field_name_n_input_value: Dict[str, any] = {}
        for widget_query in result[1]:
            widget_name = widget_query.widget_name
            widget = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            click_button_with_name(widget=widget, button_name="Edit")
            if widget_name == "plan_status":
                continue
            if widget_name == "chore_limits" and layout == Layout.TABLE:
                switch_layout(widget=widget, layout=Layout.TABLE)
            elif layout == Layout.TREE and widget_name == "chore_limits":
                pass
            elif layout == Layout.TREE:
                switch_layout(widget=widget, layout=Layout.TREE)
            # switch_layout(widget, layout)

            for field_query in widget_query.fields:
                xpath: str
                field_name: str = field_query.field_name
                # in plan status widget residual notional and balance notional fld disabled in table layout only
                if (field_name == "residual_notional" or field_name == "balance_notional") and layout == Layout.TABLE:
                    continue
                val_min, val_max = get_val_min_n_val_max_of_fld(field_query)
                input_value: str = is_property_contain_val_min_val_max_or_none(val_max=val_max,
                                                                               val_min=val_min)
                xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                       widget_name=widget_name, field_name=field_name)

                set_input_field_on_layout(driver=driver, widget=widget, xpath=xpath, field_name=field_name, value=input_value,
                                          layout=layout)
                field_name_n_input_value[field_name] = input_value
            validate_comma_separated_values(driver=driver, widget=widget, layout=layout,
                                            field_name_n_input_value=field_name_n_input_value, widget_name=widget_name)
    except Exception as e:
        print(e)


def get_n_validate_number_format_from_input_fld(schema_dict: Dict[str, any], widget_type: WidgetType, driver: WebDriver,
                                                flux_property: FluxPropertyType, layout: Layout):
    try:
        result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=widget_type,
                                              flux_property=flux_property)
        assert result[0]
        print(result)

        for widget_query in result[1]:
            # chore limits widget has hidden layout btn
            widget_name = widget_query.widget_name
            if widget_name in [WidgetName.BasketChore.value, WidgetName.SymbolOverview.value,
                               WidgetName.PlanBrief.value,
                               WidgetName.SymbolSideSnapShot.value, WidgetName.ChoreLimits.value]:
                continue
            widget: WebElement = driver.find_element(By.ID, widget_name)
            scroll_into_widget_with_widget_name(widget=widget, driver=driver, widget_name=widget_name)
            switch_layout(widget, layout)
            if not widget_type == WidgetType.REPEATED_INDEPENDENT:
                click_edit_btn(driver, widget)
            for field_query in widget_query.fields:
                field_name: str = field_query.field_name
                if field_name == "accounts_nett_notional":
                    continue
                number_format_frm_schema: str = field_query.properties.get(FluxPropertyType.FluxFldNumberFormat)
                xpath = get_xpath_from_field_name(schema_dict, widget_type=widget_type, widget_name=widget_name,
                                                  field_name=field_name)
                number_format: str = get_flux_fld_number_format(driver, widget, xpath, layout, widget_name, widget_type=widget_type)
                assert number_format_frm_schema == number_format, f"expected {number_format_frm_schema} but got {number_format} for fld {field_name} inside {widget_name}:- widget"
                # repetated independent fld does not have any save btn
                if not widget_type == WidgetType.REPEATED_INDEPENDENT:
                    click_save_with_widget_name(driver, widget, widget_name)

    except Exception as e:
        pass


def reload_n_click_edit_btn_in_widget(widget: WebElement):
    click_button_with_name(widget=widget, button_name="Reload")
    click_button_with_name(widget=widget, button_name="Edit")


def get_n_validate_fld_fld_display_type(schema_dict: Dict[str, any], widget_type: WidgetType, driver: WebDriver,
                                        flux_property: FluxPropertyType, layout: Layout):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=widget_type,
                                          flux_property=flux_property)
    print(result)
    assert result[0]
    # contact limits, chore limits and contact status
    # TABLE LAYOUT

    field_name: str = ""
    for widget_query in result[1]:
        field_name_list = []
        widget, widget_name = get_widget_element_n_widget_name_with_fld_name(driver, widget_query)
        scroll_into_view(driver=driver, element=widget)
        click_edit_n_switch_layout(driver, widget, layout)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # display_type: str = field_query.properties.get(FluxPropertyType.FluxFldDisplayType)
            val_min, val_max = get_val_of_fld_from_schema(field_query=field_query, val_max=flux_property)
            value: str = is_property_contain_val_min_val_max_or_none(val_max=val_max, val_min=val_min)
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            field_name_list.append(field_name)

            # in plan status residual notional fld is disabled
            set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=str(value))
        validate_flux_fld_display_type_in_widget(driver=driver, widget=widget, field_name_n_xpath=field_name,
                                                 layout=Layout.TABLE)

    # tree_layout
    # for widget_query in result[1]:
    #     widget_name = widget_query.widget_name
    #     widget = driver.find_element(By.ID, widget_name)
    #     scroll_into_view(driver=driver, element=widget)
    #     click_button_with_name(widget=widget, button_name="Edit")
    #     switch_layout(widget=widget, layout=Layout.TREE)
    #     # if widget_name == "plan_status":
    #     #     show_nested_fld_in_tree_layout(widget=widget)
    #     for field_query in widget_query.fields:
    #         field_name: str = field_query.field_name
    #         val_min, val_max = get_val_min_n_val_max_of_fld(field_query=field_query)
    #         display_type: str = field_query.properties['display_type']
    #         value = is_property_contain_val_min_val_max_or_none(val_max=val_max, val_min=val_min)
    #         xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
    #                                                widget_name=widget_name, field_name=field_name)
    #         set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(value))
    #     # in plan status widget nested sec id fld is not showing any dropdown list for selecting security
    #     # in plan status widget residual_notional is not working
    #     validate_flux_fld_display_type_in_widget(driver=driver, widget=widget, field_name=field_name, layout=Layout.TREE)
    #


def get_widget_element_n_widget_name_with_fld_name(driver: WebDriver, widget_query) -> [WebElement, str]:
    widget_name = widget_query.widget_name
    widget = driver.find_element(By.ID, widget_name)
    return [widget, widget_name]


def get_n_validate_flx_fld_display_zero(driver: WebDriver, schema_dict: Dict[str, any],
                                        widget_type: WidgetType, ):
    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=widget_type,
                                          flux_property=FluxPropertyType.FluxFldDisplayZero)
    print(result)
    assert result[0]
    # can write only in table layout bcz tree layout contains progress bar
    # TREE LAYOUT
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = get_widget_element_n_scroll_into_view(driver, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            value: str = "0"
            set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=field_name, value=value)
            validate_flux_flx_display_zero_in_widget(driver=driver, widget=widget, field_name=field_name, value=value)


def get_n_validate_fld_fld_elaborate_title(schema_dict, driver: WebDriver, widget_type: WidgetType):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=widget_type,
                                          flux_property=FluxPropertyType.FluxFldElaborateTitle)

    for widget_query in result[1]:
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=Layout.TABLE)
        if widget_type == WidgetType.REPEATED_INDEPENDENT:
            click_button_with_name(widget=widget, button_name="Reload")
        show_hidden_fields_in_table_layout(driver, widget, widget_name, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # not showing in pair plan common keys(company)
            # not showing the fld in tob(in table header) widget after creating from executor(premium, px)
            if field_name in ["company", "premium", "px"]:
                continue
            default_field: str = field_query.properties["parent_title"]
            default_field = default_field + "." + field_name
            validate_elaborate_title_for_widget_type(widget, widget_type, default_field)


def validate_elaborate_title_for_widget_type(widget: WebElement, widget_type: WidgetType, default_field: str):
    common_key_fld: List[str] = get_common_keys_fld_names(widget)
    common_fields_frm_list: List[str] = get_common_fields_from_list(widget)
    if widget_type == WidgetType.INDEPENDENT:
        try:
            assert default_field in common_key_fld, f"'{default_field}' is not a value in common_key_fld"
        except AssertionError:
            try:
                assert default_field in common_fields_frm_list, f"'{default_field}' is not a key in common_fields_frm_list"
            except AssertionError as e:
                print(f"Assertion failed: {e}")

    elif widget_type == WidgetType.REPEATED_INDEPENDENT:
        try:
            table_headers = get_table_headers(widget)
            assert default_field in table_headers, f"'{default_field}' is not a value in table_headers"
        except Exception as e:
            print("Error while validating the elaborate title", e)


def reload_widget_open_n_close_setting(driver: WebDriver, widget: WebElement, widget_name: str):
    click_button_with_name(widget=widget, button_name="Reload")
    click_show_all_btn_inside_setting(driver, widget, widget_name)
    close_setting(driver)


def get_n_validate_fld_btn(schema_dict, driver: WebDriver, widget_type: WidgetType):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict),
                                          widget_type=widget_type,
                                          flux_property=FluxPropertyType.FluxFldButton)
    print(result)
    assert result[0]

    # TABLE LAYOUT
    for widget_query in result[1]:
        ui_unpressed_n_pressed_captions = {}
        schema_pressed_n_pressed_captions = {}
        index_no = 0
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        for field_query in widget_query.fields:
            unpressed_schema_caption: str = field_query.properties['button']['unpressed_caption']
            pressed_schema_caption: str = field_query.properties['button']['pressed_caption']
            if widget_name in ["system_control", "basket_chore", "contact_alert", "plan_alert"]:
                continue
            if widget_name == "plan_limits":
                click_button_with_name(widget=widget, button_name="Edit")

            unpressed_ui_txt = get_btn_caption(widget, index_no)
            btn_td_elements = get_btn_caption_class_elements(widget)
            btn_td_elements[index_no].click()
            time.sleep(Delay.SHORT.value)
            click_confirm_save(driver)
            time.sleep(Delay.SHORT.value)
            pressed_ui_txt = get_btn_caption(widget, index_no)

            ui_unpressed_n_pressed_captions[unpressed_ui_txt] = pressed_ui_txt
            schema_pressed_n_pressed_captions[unpressed_schema_caption] = pressed_schema_caption
            index_no += 1

        validate_unpressed_n_pressed_btn_txt(ui_unpressed_n_pressed_captions, schema_pressed_n_pressed_captions)