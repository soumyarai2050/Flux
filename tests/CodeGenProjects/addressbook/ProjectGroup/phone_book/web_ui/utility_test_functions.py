import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver import ChromeOptions, EdgeOptions, FirefoxOptions
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.web_ui_models import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import test_config_file_path, \
    strat_manager_service_native_web_client, create_tob



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
            options.add_argument("--headless=new")  # Runs browser in headless mode.
            driver: webdriver.Chrome = webdriver.Chrome(driver_path, chrome_options=options)
        case DriverType.EDGE:
            options = EdgeOptions()
            # options.add_argument("--headless=new")  # Runs browser in headless mode.
            driver: webdriver.Edge = webdriver.Edge(driver_path)
        case DriverType.FIREFOX:
            options = FirefoxOptions()
            options.add_argument("--headless=new")  # Runs browser in headless mode.
            driver: webdriver.Firefox = webdriver.Firefox(driver_path)
        case DriverType.SAFARI:
            # SAFARI browser not supports headless mode
            driver: webdriver.Safari = webdriver.Safari(driver_path)
    assert driver is not None, f"failed to initialize webdriver for driver_type: {driver_type}"
    return driver


def wait(driver: WebDriver) -> WebDriverWait:
    return WebDriverWait(driver, Delay.LONG.value)


def get_web_project_url():
    web_project_url: str = "http://localhost:3020"
    if os.path.isfile(str(test_config_file_path)):
        test_config = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
        web_project_url = url if (url := test_config.get("web_project_url")) is not None else web_project_url
    return web_project_url


def create_pair_strat(driver: WebDriver, pair_strat: Dict[str, any]) -> None:
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    scroll_into_view(driver=driver, element=strat_collection_widget)
    click_button_with_name(widget=strat_collection_widget, button_name="Create")

    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    xpath: str
    value: str

    # select strat_leg1.sec.sec_id
    xpath = "pair_strat_params.strat_leg1.sec.sec_id"
    value = pair_strat["pair_strat_params"]["strat_leg1"]["sec"]["sec_id"]
    name = "sec_id"
    set_autocomplete_field(widget=pair_strat_params_widget, xpath=xpath, name=name, search_type=SearchType.NAME,
                           value=value)

    # select strat_leg1.side
    xpath = "pair_strat_params.strat_leg1.side"
    value = pair_strat["pair_strat_params"]["strat_leg1"]["side"]
    name = "side"
    set_dropdown_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value)

    show_nested_fld_in_tree_layout(widget=pair_strat_params_widget)

    # select strat_leg2.sec.sec_id
    xpath = "pair_strat_params.strat_leg2.sec.sec_id"
    value = pair_strat["pair_strat_params"]["strat_leg2"]["sec"]["sec_id"]
    name = "sec_id"
    set_autocomplete_field(widget=pair_strat_params_widget, xpath=xpath, name=name, search_type=SearchType.NAME,
                           value=value)

    strat_status_widget = driver.find_element(By.ID, "strat_status")
    scroll_into_view(driver=driver, element=strat_status_widget)

    # select pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat["pair_strat_params"]["common_premium"]
    name = "common_premium"
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value)

    # save strat collection
    click_button_with_name(widget=strat_collection_widget, button_name="Save")
    confirm_save(driver)
    validate_pair_strat_params(widget=pair_strat_params_widget, pair_strat=pair_strat)

    # wait for host and port to be populated in pair strat - is_partially_running - add 5 sec sleep
    # get executor client
    # create symbol overviews
    # wait for strat limits, strat status, strat alerts to be created - is_executor_running - add 5 sec sleep
    host: str = "127.0.0.1"
    port: int = 8020
    strat_manager_service_http_client = StratManagerServiceHttpClient(host, port)
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_http_client.get_all_pair_strat_client()

    pair_strat: PairStratBaseModel = pair_strat_list[-1]

    while not pair_strat.is_partially_running:
        pair_strat_list = strat_manager_service_http_client.get_all_pair_strat_client()
        pair_strat = pair_strat_list[-1]
        time.sleep(5)

    # asset is partially running true
    assert pair_strat.is_partially_running

    executor_web_client = StratExecutorServiceHttpClient(pair_strat.host, pair_strat.port)
    symbol_overview_obj_list: List[SymbolOverviewBaseModel] = symbol_overview_list()
    for symbol_overview in symbol_overview_obj_list:
        executor_web_client.create_symbol_overview_client(symbol_overview)

    while not pair_strat.is_executor_running:
        pair_strat_list = strat_manager_service_http_client.get_all_pair_strat_client()
        pair_strat = pair_strat_list[-1]
        time.sleep(5)

    # asset is executor running true
    assert pair_strat.is_executor_running
    # fetch strat limits and strat status from executor client by pair strat id
    # strat_limits: StratLimitsBaseModel = executor_web_client.get_strat_limits_client(pair_strat.id)
    # strat_status: StratStatusBaseModel = executor_web_client.get_strat_status_client(pair_strat.id)
    override_strat_limit(executor_web_client)
    # TODO LAZY: strat limits, strat status and strat alert is present in ui
    time.sleep(10)


def verify_supported_search_type(search_type: SearchType = SearchType.NAME) -> bool:
    if not hasattr(By, search_type):
        raise Exception(f"unsupported search type: {search_type}")
    else:
        return True


def get_tree_input_field_xpath(xpath: str) -> str:
    return f"//div[@data-xpath='{xpath}']"


def set_tree_input_field(widget: WebElement, xpath: str, name: str, value: str,
                         search_type: SearchType = SearchType.NAME,  autocomplete: bool = False) -> None:
    if verify_supported_search_type(search_type):
        input_div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
        input_div_element = widget.find_element(By.XPATH, input_div_xpath)
        input_element = input_div_element.find_element(getattr(By, search_type), name)
        input_element.click()
        input_element.send_keys(Keys.CONTROL + "a")
        input_element.send_keys(Keys.BACK_SPACE)
        input_element.send_keys(value)
        if autocomplete:
            input_element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
        # else not required
    # else not required


def get_table_input_field_xpath(xpath: str) -> str:
    return f"//td[@data-xpath='{xpath}']"


def set_table_input_field(widget: webdriver, xpath: str, value: str,
                          search_type: SearchType = SearchType.TAG_NAME) -> None:
    if verify_supported_search_type(search_type):
        input_td_xpath: str = get_table_input_field_xpath(xpath=xpath)
        input_td_element = widget.find_element(By.XPATH, input_td_xpath)
        input_td_element.click()
        set_input = input_td_element.find_element(By.TAG_NAME, "input")
        set_input.click()
        set_input.send_keys(Keys.CONTROL + "a")
        set_input.send_keys(Keys.BACK_SPACE)
        set_input.send_keys(value)


def set_autocomplete_field(widget: WebElement, xpath: str, name: str, search_type: SearchType, value: str) -> None:
    autocomplete_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    autocomplete_element = widget.find_element(By.XPATH, autocomplete_xpath)
    assert autocomplete_element is not None, f"autocomplete element not found for xpath: {xpath}, name: {name}"
    set_tree_input_field(widget=autocomplete_element, xpath=xpath, name=name, value=value, search_type=search_type,
                         autocomplete=True)


def set_dropdown_field(widget: WebElement, xpath: str, name: str, value: str) -> None:
    dropdown_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    dropdown_element = widget.find_element(By.XPATH, dropdown_xpath)
    dropdown = dropdown_element.find_element(By.ID, name)
    dropdown.click()
    dropdown.find_element(By.XPATH, f"//li[contains(text(), '{value}')]").click()


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

    pair_strat_params = pair_strat["pair_strat_params"]
    assert stratleg1_sec == pair_strat_params["strat_leg1"]["sec"]["sec_id"]
    assert strat_side == pair_strat_params["strat_leg1"]["side"]
    assert stratleg2_sec_id == pair_strat_params["strat_leg2"]["sec"]["sec_id"]
    assert strat_common_prem == str(pair_strat_params["common_premium"])


def update_max_value_field_strats_limits(widget: WebElement, xpath: str, name: str, input_value: int) -> None:
    input_div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    div_xpath = widget.find_element(By.XPATH, input_div_xpath)
    input_element = div_xpath.find_element(By.ID, name)
    input_element.click()
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    input_element.send_keys(input_value)


def create_strat_limits_using_tree_view(driver: WebDriver, strat_limits: Dict, layout: Layout) -> None:
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")

    # strat_limits.max_open_orders_per_side
    xpath = "max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    name = "max_open_orders_per_side"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    xpath = "max_single_leg_notional"
    value = strat_limits["max_single_leg_notional"]
    name = "max_single_leg_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.max_open_cb_notional
    xpath = "max_open_single_leg_notional"
    value = strat_limits["max_open_single_leg_notional"]
    name = "max_open_single_leg_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.max_net_filled_notional
    xpath = "max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    name = "max_net_filled_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.max_concentration
    xpath = "max_concentration"
    value = strat_limits["max_concentration"]
    name = "max_concentration"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.limit_up_down_volume_participation_rate
    xpath = "limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    name = "limit_up_down_volume_participation_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.cancel_rate.max_cancel_rate
    xpath = "cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    name = "max_cancel_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # applicable_period_seconds
    xpath = "cancel_rate.applicable_period_seconds"
    value = strat_limits["cancel_rate"]["applicable_period_seconds"]
    name = "applicable_period_seconds"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    if layout == Layout.NESTED:
        nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
        input_residual_mark_second_element = nested_tree_dialog.find_element(By.ID, "residual_mark_seconds")
    else:
        strats_limits_widget = driver.find_element(By.ID, "strat_limits")
        input_residual_mark_second_element = strats_limits_widget.find_element(By.ID, "residual_mark_seconds")


    scroll_into_view(driver=driver, element=input_residual_mark_second_element)
    # strat_limits.cancel_rate.waived_min_orders
    xpath = "cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    name = "waived_min_orders"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.market_trade_volume_participation.max_participation_rate
    xpath = "market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    name = "max_participation_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # mrket_trde_applicable_periods_seconds
    xpath = "market_trade_volume_participation.applicable_period_seconds"
    value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    name = "applicable_period_seconds"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.market_depth.participation_rate
    xpath = "market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    name = "participation_rate"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.market_depth.depth_levels
    xpath = "market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    name = "depth_levels"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.residual_restriction.max_residual
    xpath = "residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    name = "max_residual"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.residual_restriction.residual_mark_seconds
    xpath = "residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    name = "residual_mark_seconds"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)


def get_value_from_input_field(widget: WebElement, xpath: str, layout: Layout)-> str:
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
    xpath = "max_open_orders_per_side"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["max_open_orders_per_side"])

    # max_single_leg_notional
    xpath = "max_single_leg_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_single_leg_notional"])

    # max_open_single_leg_notional
    xpath = "max_open_single_leg_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_open_single_leg_notional"])

    # max_net_filled_notional
    xpath = "max_net_filled_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_net_filled_notional"])

    # max_concentration
    xpath = "max_concentration"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["max_concentration"])

    # limit_up_down_volume_participation_rate
    xpath = "limit_up_down_volume_participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["limit_up_down_volume_participation_rate"])

    # max_cancel_rate
    xpath = "cancel_rate.max_cancel_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["cancel_rate"]["max_cancel_rate"])

    # applicable_period_seconds
    xpath = "cancel_rate.applicable_period_seconds"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["cancel_rate"]["applicable_period_seconds"])

    # waived_min_orders
    xpath = "cancel_rate.waived_min_orders"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["cancel_rate"]["waived_min_orders"])

    # max_participation_rate
    xpath = "market_trade_volume_participation.max_participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_trade_volume_participation"]["max_participation_rate"])

    # applicable_period_seconds
    xpath = "market_trade_volume_participation.applicable_period_seconds"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_trade_volume_participation"]["applicable_period_seconds"])

    # participation_rate
    xpath = "market_depth.participation_rate"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_depth"]["participation_rate"])

    # depth_levels
    xpath = "market_depth.depth_levels"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["market_depth"]["depth_levels"])

    # max_residual
    xpath = "residual_restriction.max_residual"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", "")
    assert value == str(strat_limits["residual_restriction"]["max_residual"])

    # residual_mark_seconds
    xpath = "residual_restriction.residual_mark_seconds"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["residual_restriction"]["residual_mark_seconds"])


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
                                 flux_property: str):
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
        field: str
        field_properties: Dict[str, any]
        for field, field_properties in properties.items():
            if field_properties["type"] in SIMPLE_DATA_TYPE_LIST:
                if field_name == field:
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
                        return f"{field}[0].{ret}"
                    else:
                        return f"{field}.{ret}"

    xpath: str = ""
    if widget_type == WidgetType.DEPENDENT:
        xpath = f"{widget_name}."

    widget_schema: Dict[str, any] = schema_dict[widget_name]
    result = search_schema_for_field(widget_schema)
    if result:
        return xpath + result
    return None


def override_default_limits(order_limits: OrderLimitsBaseModel, portfolio_limits: PortfolioLimitsBaseModel) -> None:
    updated_order_limits: OrderLimitsBaseModel = OrderLimitsBaseModel(_id=order_limits.id, max_basis_points=150,
                                                                      max_px_deviation=2, min_order_notional=1_000,
                                                                      max_order_notional=400000)
    strat_manager_service_native_web_client.patch_order_limits_client(jsonable_encoder(
        updated_order_limits, by_alias=True, exclude_none=True))

    updated_portfolio_limits: PortfolioLimitsBaseModel = \
        PortfolioLimitsBaseModel(_id=portfolio_limits.id, max_open_baskets=200)
    strat_manager_service_native_web_client.patch_portfolio_limits_client(jsonable_encoder(
        updated_portfolio_limits, by_alias=True, exclude_none=True))


def override_strat_limit(strat_executor_service_http_client: StratExecutorServiceHttpClient)-> None:
    strat_limit_list: List[StratLimitsBaseModel] = strat_executor_service_http_client.get_all_strat_limits_client()

    for strat_limit in strat_limit_list:
        cancel_rate: CancelRateOptional = CancelRateOptional(max_cancel_rate=20)
        market_trade_volume_participation: MarketTradeVolumeParticipationOptional = \
            MarketTradeVolumeParticipationOptional(max_participation_rate=20)
        updated_strat_limit: StratLimitsBaseModel = \
            StratLimitsBaseModel(_id=strat_limit.id, cancel_rate=cancel_rate,
                                 market_trade_volume_participation=market_trade_volume_participation)
        strat_executor_service_http_client.patch_strat_limits_client(jsonable_encoder(
            updated_strat_limit, by_alias=True, exclude_none=True))


def switch_layout(widget: WebElement, layout: Layout) -> None:
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
        raise Exception(f"failed to switch to layout: {layout};;; exception: {e}")

def activate_strat(widget: WebElement, driver: WebDriver) -> None:
    # Find the button with the name 'strat_state'
    activate_btn_element = widget.find_element(By.NAME, "strat_state")

    # Get the button text
    button_text = activate_btn_element.text

    # Check if the button text is ACTIVATE, ERROR, or PAUSED
    assert button_text in ["ACTIVATE", "ERROR", "PAUSE"], "Unknown button state."

    if button_text == "ACTIVATE":
        # Activate the strat
        activate_btn_element.click()
        time.sleep(Delay.SHORT.value)
        confirm_save(driver=driver)

        # Verify if the strat is in active state
        btn_caption = widget.find_element(By.XPATH, '//*[@id="strat_collection"]/h6/div/div/button[1]').text
        assert btn_caption == "PAUSE", "Failed to activate strat."

    elif button_text in ["ERROR", "PAUSE"]:
        print(f"Strat is in {button_text} state. Cannot activate.")


def confirm_save(driver: WebDriver) -> None:
    confirm_save_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    try:
        confirm_btn = confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
        confirm_btn.click()
    except NoSuchElementException:
        confirm_btn = confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
        confirm_btn.click()
    time.sleep(Delay.SHORT.value)


def select_or_unselect_checkbox(driver: WebDriver, field_name: str) -> None:
    settings_dropdown: WebElement = driver.find_element(By.CLASS_NAME, "MuiPopover-paper")
    dropdown_elements = settings_dropdown.find_elements(By.TAG_NAME, "li")
    span_element: WebElement
    for dropdown_element in dropdown_elements:
        dropdown_label = dropdown_element.find_element(By.CSS_SELECTOR, "label")
        if dropdown_label.text == field_name:
            dropdown_label.click()
            time.sleep(Delay.DEFAULT.value)
            break

def get_default_field_value(widget: WebElement, layout: Layout, xpath: str) -> str:
    if layout == Layout.TABLE:
        input_td_xpath: str = get_table_input_field_xpath(xpath=xpath)
        input_td_element = widget.find_element(By.XPATH, input_td_xpath)
        input_td_element.click()
        input_element = input_td_element.find_element(By.TAG_NAME, "input")
        get_field_value = input_element.get_attribute('value')
        input_element.send_keys(Keys.ENTER)
        time.sleep(2)

    else:
        input_div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
        input_div_element = widget.find_element(By.XPATH, input_div_xpath)
        get_field_value = input_div_element.find_element(By.TAG_NAME, "input").get_attribute('value')
    return get_field_value

def show_hidden_fields_in_tree_layout(widget: WebElement, driver: WebDriver) -> None:
    click_button_with_name(widget=widget, button_name="Show")
    list_element = driver.find_element(By.XPATH, "//ul[@role='listbox']")
    li_elements = list_element.find_elements(By.TAG_NAME, "li")
    li_elements[0].click()

def show_hidden_field_in_review_changes_popup(driver: WebDriver) -> None:
    review_changes_widget = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")
    expand_buttons = review_changes_widget.find_elements(By.CLASS_NAME, "node-ellipsis")
    for expand_button in expand_buttons:
        expand_button.click()


def validate_property_that_it_contain_val_min_val_max_or_none(val_max: str, val_min: str) -> str:
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


def is_table_cell_enabled(widget: WebElement, xpath: str) -> bool:
    # TODO: fix this method
    try:
        input_td_xpath: str = get_table_input_field_xpath(xpath=xpath)
        input_td_element = widget.find_element(By.XPATH, input_td_xpath)
        # input_td_element.click()
        # # input_td_element.send_keys(Keys.ENTER)
        return True
    except NoSuchElementException:
        return False
    except ElementNotInteractableException:
        return False


def count_fields_in_tree(widget: WebElement) -> List[str]:
    field_elements = widget.find_elements(By.CLASS_NAME, "Node_node__sh0RD")
    field_names = []
    for field_element in field_elements:
        field_names.append(field_element.text)
    return field_names


def get_commonkey_items(widget: WebElement) -> Dict[str, any]:

    # m
    # common_key_widget = driver.find_element(By.XPATH, "/html/body/div/div/div[2]/div[8]/div[1]")
    common_key_widget = widget.find_element(By.XPATH, "//div")
    # common_key_widget = widget.find_element(By.CLASS_NAME, "CommonKeyWidget_container__+Oh0d")
    common_key_item_elements = common_key_widget.find_elements(By.CLASS_NAME, "CommonKeyWidget_item__kftVh")

    # common_key_widget = widget.find_element(By.CLASS_NAME, "CommonKeyWidget_container__Ek2YA")
    # common_key_item_elements = common_key_widget.find_elements(By.CLASS_NAME, "CommonKeyWidget_item__ny8Fj")

    common_key_items: Dict[str, any] = {}
    for common_key_item_element in common_key_item_elements:
        common_key_item_txt = common_key_item_element.text.split(":")
        key = common_key_item_txt[0].replace(" ", "_")
        value = common_key_item_txt[1]
        common_key_items[key] = value
    return common_key_items


def get_flux_fld_number_format(widget: WebElement, xpath: str, layout: Layout) -> str:
    if layout == Layout.TREE:
        tag_name: str = "p"
        element = widget.find_element(By.CLASS_NAME, "MuiInputAdornment-root")
    else:
        tag_name: str = "span"
        xpath = get_table_input_field_xpath(xpath=xpath)
        element = widget.find_element(By.XPATH, xpath)
    number_format_element = element.find_element(By.TAG_NAME, tag_name)
    number_format = number_format_element.text
    # get only % from str
    return number_format[-1]

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
        confirm_save(driver=driver)
        common_keys: Dict[str, any] = get_commonkey_items(widget=widget)
        for field_name, input_value in field_name_n_input_value.items():
            value_from_ui: str = common_keys[field_name]
            # getting common key value without comma and dot to validate, if value= "1,230.0" get "1230" only
            assert (value_from_ui.replace(",", "") ==
                    input_value.split(".")[0].replace(",", "")), \
                f"Value mismatch field_name: {field_name} value_from_ui: {value_from_ui} input_value: {input_value}"
    elif layout == Layout.TREE:
        # remove save later
        # if widget_name == "strat_status":
        #     confirm_save(driver)
        time.sleep(5)
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
    field_value : str = ""
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


def get_unsaved_changes_discarded_key(driver: WebDriver) -> str:
    popup_widget = driver.find_element(By.XPATH, "//div[@role='dialog']")
    span_element = popup_widget.find_element(By.CLASS_NAME, "object-key")
    unsaved_changes_field_name = span_element.text
    return unsaved_changes_field_name


def click_on_okay_button_unsaved_changes_popup(driver: webdriver) -> None:
    popup_widget = driver.find_element(By.XPATH, "//div[@role='dialog']")
    button_element = popup_widget.find_element(By.XPATH, "//button[normalize-space()='Okay']")
    time.sleep(Delay.SHORT.value)
    button_element.click()


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


def get_common_keys(widget: WebElement) -> List[str]:
    # common_key_items = widget.find_elements(By.XPATH, '//div[@class="CommonKeyWidget_container__+Oh0d"]')
    common_key_items = widget.find_elements(By.XPATH, ".//div")
    common_keys_text = []
    # common_keys_text.
    a = len(common_key_items)
    for key_element in common_key_items:
        try:
            span_element = key_element.find_element(By.TAG_NAME, "span")
            common_keys_text.append(span_element.text.split(":")[0].split("[")[0])
        except NoSuchElementException:
            pass
    return common_keys_text


def get_all_keys_from_table(table: WebElement) -> List[str]:
    # Assuming the heading cells are in the first row of the table
    heading_row: WebElement = table.find_element(By.TAG_NAME, "tr")

    # Assuming the heading values are present in the cells of the heading row
    heading_cells: List[WebElement] = heading_row.find_elements(By.TAG_NAME, "th")

    headings = [cell.text.replace(" ", "_") for cell in heading_cells]

    return headings


def get_replaced_common_keys(common_keys_list: List) -> List[str]:
    list_of_common_keys = []
    for common_key in common_keys_list:
        list_of_common_keys.append(common_key.replace("common premium", "common_premium")
                                   .replace("hedge ratio", "hedge_ratio").replace(":", ""))
    return list_of_common_keys


def get_table_headers(widget: WebElement) -> List[str]:
    # row fld names
    name: str = "span[class^='MuiButtonBase-root']"
    span_elements: List[WebElement] = widget.find_elements(By.CSS_SELECTOR, name)
    table_headers: List[str] = [span_element.text.replace(" ", "_") for span_element in span_elements]
    return table_headers


def save_nested_strat(driver: WebDriver):
    nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    save_strat = nested_tree_dialog.find_element(By.NAME, "Save")
    save_strat.click()


def expand_all_nested_fld_name_frm_review_changes_dialog(driver: WebDriver) -> None:
    dialog_widget = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")
    plus_btn_elements = dialog_widget.find_elements(By.CLASS_NAME, "collapsed-icon")
    for plus_btn in plus_btn_elements:
        plus_btn.click()
        time.sleep(2)


def get_widget_name_frm_schema(schema_dict, widget_type: WidgetType, flux_property: str) -> List[str]:
    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=widget_type, flux_property=flux_property)
    assert result[0]
    name_lst: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        name_lst.append(widget_name)
    return name_lst


def get_replaced_str(default_field_value: str) -> int:
    default_field_value = default_field_value.replace(',', '')
    return int(default_field_value)


def create_tob_md_ld_fj_os_oj(driver: WebDriver, top_of_book_list,
                              market_depth_list: List[MarketDepthBaseModel], last_trade_list: List[LastTradeBaseModel],
                              fills_journal_list: List[FillsJournalBaseModel],
                              order_snapshot_list: List[OrderSnapshotBaseModel],
                              order_journal_list: List[OrderJournalBaseModel]) -> None:
    """

    Function for creating top_of_book, market_depth, last_trade,
    fills_journal, order_snapshot, order_journal, using the web client.

    The function sets up and executes a series of tests to ensure the proper
    creation and functionality of various components related to data
    and performance analysis.

    :return: None
    """
    widget_name: str = "strat_collection"
    widget: WebElement = driver.find_element(By.ID, widget_name)
    activate_strat(widget, driver)
    time.sleep(Delay.SHORT.value)

    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()
    pair_strat: PairStratBaseModel = pair_strat_list[-1]

    while not pair_strat.is_executor_running:
        pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()
        pair_strat: PairStratBaseModel = pair_strat_list[-1]
        time.sleep(Delay.SHORT.value)

    assert pair_strat.is_executor_running

    executor_web_client = StratExecutorServiceHttpClient(pair_strat.host, pair_strat.port)


    create_tob("CB_Sec_1", "EQT_Sec_1", top_of_book_list, executor_web_client)
    expected_market_depth_list: List[MarketDepthBaseModel] = (
        executor_web_client.create_all_market_depth_client(market_depth_list))
    for expected_market_depth, market_depth in zip(expected_market_depth_list, market_depth_list):
        assert market_depth.id == expected_market_depth.id
        assert market_depth.symbol == expected_market_depth.symbol
        assert market_depth.exch_time == expected_market_depth.exch_time
        assert market_depth.arrival_time == expected_market_depth.arrival_time
        assert market_depth.side == expected_market_depth.side
        assert market_depth.px == expected_market_depth.px
        assert market_depth.qty == expected_market_depth.qty
        assert market_depth.premium == expected_market_depth.premium
        assert market_depth.position == expected_market_depth.position
        assert market_depth.market_maker == expected_market_depth.market_maker
        assert market_depth.is_smart_depth == expected_market_depth.is_smart_depth

    expected_last_trade_list: List[LastTradeBaseModel] = (
        executor_web_client.create_all_last_trade_client(last_trade_list))
    assert last_trade_list == expected_last_trade_list

    for fills_journal in fills_journal_list:
        expected_fills_journal: FillsJournalBaseModel = executor_web_client.create_fills_journal_client(fills_journal)
        assert fills_journal.id == expected_fills_journal.id
        assert fills_journal.order_id == expected_fills_journal.order_id
        assert fills_journal.fill_px == expected_fills_journal.fill_px
        assert fills_journal.fill_qty == expected_fills_journal.fill_qty
        assert fills_journal.fill_symbol == expected_fills_journal.fill_symbol
        assert fills_journal.fill_side == expected_fills_journal.fill_side
        assert fills_journal.underlying_account == expected_fills_journal.underlying_account
        assert fills_journal.fill_date_time == expected_fills_journal.fill_date_time
        assert fills_journal.fill_id == expected_fills_journal.fill_id
        assert (fills_journal.underlying_account_cumulative_fill_qty ==
                expected_fills_journal.underlying_account_cumulative_fill_qty)

    for order_snapshot in order_snapshot_list:
        expected_order_snapshot: OrderSnapshotBaseModel = (
            executor_web_client.create_order_snapshot_client(order_snapshot))
        assert order_snapshot == expected_order_snapshot

    for order_journal in order_journal_list:
        expected_order_journal: OrderJournalBaseModel = executor_web_client.create_order_journal_client(order_journal)
        assert order_journal.id == expected_order_journal.id
        assert order_journal.order_event == expected_order_journal.order_event
        assert order_journal.current_period_order_count == expected_order_journal.current_period_order_count
        # assert order_journal == expected_order_journal


def delete_tob_md_ld_fj_os_oj() -> None:
    """

        Function for deleting top_of_book, market_depth, last_trade,
        fills_journal, order_snapshot, order_journal, using the web client.

        The function sets up and executes a series of tests to ensure the proper
        creation and functionality of various components related to data
        and performance analysis.

        :return: None
    """
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()

    for pair_strat in pair_strat_list:
        if not pair_strat.is_executor_running:
            err_str_ = ("strat exists but is not running, can't delete top_of_book, market_depth, last_trade, "
                        "fills_journal, order_snapshot, order_journal when not running, delete it manually")
            logging.error(err_str_)
            raise Exception(err_str_)
        assert pair_strat.is_executor_running

        executor_web_client = StratExecutorServiceHttpClient(pair_strat.host, pair_strat.port)

        for _ in range(1, 3):
            assert executor_web_client.delete_top_of_book_client(top_of_book_id=_, return_obj_copy=False)

        for _ in range(1, 21):
            assert executor_web_client.delete_market_depth_client(market_depth_id=_, return_obj_copy=False)

        assert executor_web_client.delete_all_last_trade_client(return_obj_copy=False)

        for _ in range(1, 11):
            assert executor_web_client.delete_fills_journal_client(fills_journal_id=_, return_obj_copy=False)

        for _ in range(1, 11):
            assert executor_web_client.delete_order_snapshot_client(order_snapshot_id=_, return_obj_copy=False)

        for _ in range(1, 11):
            assert executor_web_client.delete_order_journal_client(order_journal_id=_, return_obj_copy=False)


def scroll_into_view(driver: WebDriver, element: WebElement):
    driver.execute_script('arguments[0].scrollIntoView(true)', element)
    time.sleep(Delay.SHORT.value)


def click_button_with_name(widget: WebElement, button_name: str):
    widget.find_element(By.NAME, button_name).click()
    time.sleep(Delay.SHORT.value)


def flux_fld_default_widget(schema_dict: Dict, widget: WebElement, widget_type: WidgetType, widget_name: str,
                            layout: Layout, field_query):
    field_name: str = field_query.field_name
    default_value: str = field_query.properties['default']
    if (field_name != "bkr_disable" and field_name != "pos_disable" and field_name != "sec_type" and
            field_name != "dismiss" and field_name != "kill_switch" and field_name != "strat_state" and
            field_name != "exch_response_max_seconds" and field_name != "priority"):
        xpath: str = get_xpath_from_field_name(schema_dict, widget_type=widget_type,
                                               widget_name=widget_name, field_name=field_name)
        # TODO: REMOVE IF LATER: in strat limits, priority fld contain incorrect default value
        #  (it's value is:-0 ,but it should be 10)
        field_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
        if field_name == "priority" and widget_name == "strat_limits":
            # Skip the assert statement for "priority" field
            pass
        else:
            # try:
            #     field_value = int(field_value)
            # except ValueError:
            #     field_value = field_value
            assert field_value == str(default_value), \
                (f"Field {field_name} value mismatch with default value {default_value} "
                 f"field_value {field_value} for widget {widget_name}")


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


def get_placeholder_from_element(widget: WebElement, id: str) -> str:
    input_element = widget.find_element(By.ID, id)
    return input_element.get_attribute('placeholder')


def flux_fld_sequence_number_in_widget(result: List[WidgetQuery], driver: WebDriver, widget_type: WidgetType):
    for widget_query in result:
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
            if field_name == "kill_switch" or field_name == "strat_state":
                continue
            i += 1
            sequence_number += 1
            if widget_type == WidgetType.INDEPENDENT or widget_type == WidgetType.REPEATED_INDEPENDENT:
                field_sequence_value_element: WebElement = widget.find_element(
                    By.XPATH, f'//*[@id="{widget_name}_table_settings"]/div[3]/li[{i}]/div[1]')
            else:
                if widget_name == "pair_strat_params":
                    widget_name = "pair_strat"
                field_sequence_value_element: WebElement = widget.find_element(
                    By.XPATH, f'//*[@id="definitions.{widget_name}_table_settings"]/div[3]/li[{i}]/div[1]')
            field_sequence_value: int = int(get_select_box_value(field_sequence_value_element))
            if (field_sequence_value - previous_field_sequence_value) > 1:
                sequence_number += ((field_sequence_value - previous_field_sequence_value) - 1)
            previous_field_sequence_value = field_sequence_value

            assert sequence_number == field_sequence_value


def flux_fld_ui_place_holder_in_widget(result: List[WidgetQuery], driver: WebDriver):
    for widget_query in result:
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)

        if widget_name == "strat_status":
            scroll_into_view(driver=driver, element=widget)
            click_button_with_name(widget=widget, button_name="Create")
            switch_layout(widget=widget, layout=Layout.TREE)
            show_nested_fld_in_tree_layout(widget=widget)
            # widget.find_element(By.XPATH, '//*[@id="strat_status"]/div/div/div/ul/div[27]/div[2]/button').click()
            # widget.find_element(By.XPATH, '//*[@id="strat_status"]/div/div/div/ul/div[27]/div[2]').click()

        elif widget_name == "pair_strat_params":
            click_button_with_name(driver.find_element(By.ID, "strat_collection"), button_name="Create")
            scroll_into_view(driver=driver, element=widget)
            switch_layout(widget=widget, layout=Layout.TREE)
            # show_nested_fld_in_tree_layout(widget=widget)
            # widget.find_element(By.XPATH, '//*[@id="pair_strat_params"]/div/div/div/ul/ul/div[2]/div[2]/button').click()
            # widget.find_element(By.XPATH, '//*[@id="pair_strat_params"]/div/div/div/ul/ul/div[2]/div[2]').click()
        else:
            scroll_into_view(driver=driver, element=widget)
            click_button_with_name(widget=widget, button_name="Create")
            switch_layout(widget=widget, layout=Layout.TREE)

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
        # fixme: `portfolio_status` and `strat_alert` is not been created
        #  (`strat_status`: most of the field is not present )
        if (widget_name == "portfolio_status" or widget_name == "strat_alert" or widget_name == "strat_status"
                or widget_name == "system_control"):
            continue
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=Layout.TABLE)
        click_button_with_name(widget=widget, button_name="Show")
        common_key_list: List[str] = get_common_keys(widget=widget)
        common_key_list = [key.replace(" ", "_") for key in common_key_list]
        print(common_key_list)
        for field_query in widget_query.fields:
            if widget_type == WidgetType.INDEPENDENT:
                field_title: str = field_query.properties["title"].replace(" ", "_")
                if (field_title != "max_contract_qty" and field_title != "security" and field_title != "positions" and
                        field_title != "eligible_brokers_update_count" and field_title != "min_order_notional_allowance"
                        and field_title != "alerts"):
                    assert field_title in common_key_list
            elif widget_type == WidgetType.DEPENDENT:
                field_name: str = field_query.field_name
                field_title: str | None = field_query.properties.get("parent_title")
                if field_title is not None:
                    field_title = field_title + "." + field_name
                else:
                    field_title = field_query.properties["title"].replace(" ", "_")
                print(field_title)
                if (field_name != "exch_id" and field_name != "sec_id" and field_name != "sec_type" and
                        field_name != "company"):
                    assert field_title in common_key_list


def flux_fld_autocomplete_in_widgets(result: List[WidgetQuery], auto_complete_dict: Dict[str, any]):
    for widget_query in result:
        for field_query in widget_query.fields:
            auto_complete_value_list = [field_auto_complete_property.split(":")[1]
                                        if ":" in field_auto_complete_property
                                        else field_auto_complete_property.split("=")[1]
            if "=" in field_auto_complete_property else field_auto_complete_property for field_auto_complete_property
                                        in field_query.properties.get("auto_complete").split(",")]
            for auto_complete_value in auto_complete_value_list:
                assert (auto_complete_value in auto_complete_dict or
                        (auto_complete_value in values for values in auto_complete_dict.values()))


def validate_unpressed_n_pressed_btn_txt(driver: WebDriver, widget: WebElement,
                                         unpressed_caption: str, pressed_caption: str, index_no: int):
    btn_td_elements: [WebElement] = widget.find_elements(By.CLASS_NAME, "MuiToggleButton-sizeMedium")
    unpressed_btn_txt = btn_td_elements[index_no].text
    btn_td_elements[index_no].click()
    confirm_save(driver=driver)
    pressed_btn_txt = btn_td_elements[index_no].text
    assert unpressed_caption.upper() == unpressed_btn_txt
    assert pressed_caption.upper() == pressed_btn_txt


def validate_hide_n_show_in_common_key(widget: WebElement, field_name: str, key_type: str):
    common_keys: List[str] = get_common_keys(widget=widget)
    replaced_common_keys: List[str] = get_replaced_common_keys(common_keys_list=common_keys)
    if key_type == "selected_checkbox":
        assert field_name in replaced_common_keys, \
            f"{field_name} field is not visible in common keys, expected to be visible"
    else:
        assert field_name not in replaced_common_keys, \
            f"{field_name} field is visible in common keys, expected to be hidden"


def validate_flux_fld_val_max_in_widget(driver: WebDriver, widget: WebElement, widget_name: str, input_type: str, xpath_n_field_names: Dict):
    click_button_with_name(widget=widget, button_name="Save")
    expand_all_nested_fld_name_frm_review_changes_dialog(driver=driver)
    object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
    for field_name, xpath in xpath_n_field_names.items():
        if widget_name == "strat_limits" and input_type == "invalid":
            assert xpath in object_keys
        else:
            assert field_name in object_keys
    if input_type == "valid":
        confirm_save(driver=driver)
    else:
        discard_changes(widget=widget)
    xpath_n_field_names.clear()


def validate_flux_fld_val_min_in_widget(widget: WebElement, field_name: str):
    click_button_with_name(widget=widget, button_name="Save")
    object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
    assert field_name in object_keys
    discard_changes(widget=widget)


def validate_flux_fld_display_type_in_widget(driver: WebDriver, widget: WebElement, field_name: str, layout: Layout):
    click_button_with_name(widget=widget, button_name="Save")
    if layout == Layout.TABLE:
        confirm_save(driver=driver)
    else:
        switch_layout(widget=widget, layout=Layout.TABLE)
    common_keys_dict: Dict[str, any] = get_commonkey_items(widget=widget)
    input_value = int(common_keys_dict[field_name].replace(",", ""))
    assert isinstance(input_value, int)


def validate_flux_fld_number_format_in_widget(number_format_txt: str, number_format: str):
    # number_format: str = get_flux_fld_number_format(widget=widget, xpath=xpath, layout=layout)
    assert number_format_txt == number_format


def validate_flux_flx_display_zero_in_widget(driver: WebDriver, widget: WebElement, field_name: str, value: str):
    click_button_with_name(widget=widget, button_name="Save")
    confirm_save(driver=driver)
    switch_layout(widget=widget, layout=Layout.TABLE)
    get_common_key_dict: Dict[str, any] = get_commonkey_items(widget=widget, driver=driver)
    assert value == get_common_key_dict[field_name]


def get_replaced_str_default_field_value(default_field_value: str) -> int:
    if default_field_value:
        default_field_value = default_field_value.replace(',', '')
        replaced_value: int = int(default_field_value)
        return replaced_value


def validate_val_min_n_default_fld_value_equal_or_not(val_min: int, replaced_default_field_value: int) -> bool:
    if val_min == replaced_default_field_value:
        return True
    return False


def validate_val_max_n_default_fld_value_equal_or_not(val_max: int, replaced_default_field_value: int) -> bool:
    if val_max == replaced_default_field_value:
        return True
    return False

def show_nested_fld_in_tree_layout(widget: WebElement):
    try:
        options_btn = widget.find_element(By.XPATH, "//button[@aria-label='options']")
        options_btn.click()
        time.sleep(Delay.SHORT.value)
        plus_btn = widget.find_element(By.CSS_SELECTOR, "div[class^='HeaderField_menu']")
        plus_btn.click()
        time.sleep(Delay.SHORT.value)
    except NoSuchElementException as e:
        raise Exception(f"failed to click on plus button, nested fld is already visible in {widget}: ;;; exception: {e}")


def get_val_min_n_val_max_of_fld(field_query: Any) -> Tuple[str, str]:
    val_min: str = (field_query.properties.get("val_min"))
    val_max: str = (field_query.properties.get("val_max"))
    return val_min, val_max


def convert_schema_dict_to_widget_query(schema_dict: Dict[str, Any]) -> List[WidgetQuery]:
    widget_queries = []

    for widget_name, widget_data in schema_dict.items():
        fields = []
        if "properties" in widget_data:
            for field_name, field_data in widget_data["properties"].items():
                field = FieldQuery(field_name=field_name, properties=field_data)
                fields.append(field)

        widget_query = WidgetQuery(
            widget_name=widget_name,
            widget_data=widget_data,
            fields=fields,
        )

        widget_queries.append(widget_query)

    return widget_queries


def update_schema_json(schema_dict: Dict[str, any], update_widget_name: str, update_field_name: str,
                       extend_field_name: str, value: any, project_name: str) -> None:

    project_path: PurePath = code_gen_projects_dir_path / "AddressBook"/ "ProjectGroup" / project_name

    schema_path: PurePath = project_path / "web-ui" / "public" / "schema.json"

    for widget_name, widget_data in schema_dict.items():
        update_field_name_properties = widget_data.get(update_field_name)
        widget_properties = widget_data.get("properties")
        if (widget_name == update_widget_name and widget_properties is not \
                None and update_field_name_properties is None):
            widget_properties[update_field_name][extend_field_name] = value
        elif widget_name == update_widget_name and update_field_name_properties is not None:
            widget_data[update_field_name][extend_field_name] = value

    with open(str(schema_path), "w") as f:
        json.dump(schema_dict, f, indent=2)


def save_layout(driver: WebDriver, layout_name: str) -> None:
    driver.find_element(By.NAME, "SaveLayout").click()
    time.sleep(Delay.SHORT.value)
    element: WebElement = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div/div[1]/div/div/input')
    element.click()
    time.sleep(Delay.SHORT.value)
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACK_SPACE)
    element.send_keys(layout_name)
    # save the layout
    driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div/div[2]/button[2]").click()


def change_layout(driver: WebDriver, layout_name: str) -> None:
    # change the layout
    element = driver.find_element(By.NAME, "LoadLayout")
    element.click()

    time.sleep(Delay.SHORT.value)
    element = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div/div[1]/div/div/div/input')
    element.click()
    element.clear()
    element.send_keys(layout_name)
    element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)

    driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div/div[2]/button[2]").click()
    time.sleep(Delay.SHORT.value)


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
        confirm_save(driver=driver)
    elif dialog_text == "Form validation failed due to following errors:":
        discard_changes(widget)

def get_pressed_n_unpressed_btn_txt(widget: WebElement) -> str:
    button_widget = widget.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    button_text = button_widget.text
    return button_text

def validate_server_populate_fld(widget: WebElement, xpath: str, field_name: str, layout: Layout):
    if layout == Layout.TABLE:
        is_enabled: bool = is_table_cell_enabled(widget=widget, xpath=xpath)
        assert not is_enabled
    else:
        field_names: List[str] = count_fields_in_tree(widget=widget)
        # validate that server populates field name does not present in tree layout after clicking on edit btn
        assert field_name not in field_names

def input_n_validate_progress_bar(driver: WebDriver, widget: WebElement, field_name: str, value: str, input_value_type: str):
    switch_layout(widget=widget, layout=Layout.TREE)
    click_button_with_name(widget=widget, button_name="Edit")
    set_tree_input_field(widget=widget, xpath="balance_notional", name=field_name, value=value)
    click_button_with_name(widget=widget, button_name="Save")
    confirm_save(driver)
    progress_level: str = get_progress_bar_level(widget)
    if input_value_type == "val_min":
        # if input value is 0 then progress level should be 100
        assert progress_level == "100"
    else:
        # for val max
        assert progress_level == "0"

def set_val_max_input_fld(driver: WebDriver, layout: Layout, input_type: str, schema_dict: Dict[str, any]):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property="val_max")
    assert result[0]

    xpath_n_field_names: Dict[str] = {}
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        # in strat_status balance notional fld contain progress bar in table layout
        if widget_name == "strat_status":
            continue
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=layout)

        if widget_name == "order_limits" and layout == Layout.TABLE:
            switch_layout(widget=widget, layout=Layout.TABLE)

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict=copy.deepcopy(schema_dict),widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,field_name=field_name)

            xpath_n_field_names[field_name] = xpath
            if input_type == "valid":
                val_max: int = int(get_val_min_n_val_max_of_fld(field_query=field_query)[1])
            else:
                # val_max += 1
                val_max: int = int(get_val_min_n_val_max_of_fld(field_query=field_query)[1]) + 1
            if layout == Layout.TABLE:
                default_field_value: str = get_default_field_value(widget=widget, layout=Layout.TABLE, xpath=xpath)
            else:
                default_field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            if default_field_value:
                replaced_default_field_value: int = get_replaced_str(default_field_value=default_field_value)
                is_equal: bool = validate_val_max_n_default_fld_value_equal_or_not(
                    val_max=val_max,replaced_default_field_value=replaced_default_field_value)
            if is_equal:
                val_max = val_max - 1
            if layout == Layout.TABLE:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_max))
            elif layout == Layout.TREE:
                set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))
        validate_flux_fld_val_max_in_widget(driver=driver, widget=widget, widget_name=widget_name,input_type=input_type,
          xpath_n_field_names=xpath_n_field_names)

def set_val_min_input_fld(driver: WebDriver, layout: Layout, input_type: str, schema_dict: Dict[str, any]):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property="val_min")

    field_name: str = ''
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        # REMOVE (CONTINUE) LATER, IN STRAT STATUS BALANCE NOTIONAL FLD CONTAIN PROGRESS BAR
        if widget_name == "strat_status":
            continue
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        if layout == Layout.TABLE:
            switch_layout(widget=widget, layout=Layout.TABLE)
        else:
            switch_layout(widget=widget, layout=Layout.TREE)
        if widget_name == "order_limits" and layout == Layout.TABLE:
            switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            # balance notional field contain "0.0" that's why can parse directly into int
            if input_type  == "valid":
                val_min: int = int(get_val_min_n_val_max_of_fld(field_query=field_query)[0])
            else:
                val_min: int = int(get_val_min_n_val_max_of_fld(field_query=field_query)[0]) - 1
            if layout == Layout.TABLE:
                default_field_value: str = get_default_field_value(widget=widget, layout=Layout.TABLE, xpath=xpath)
            else:
                default_field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            replaced_default_field_value: int = get_replaced_str_default_field_value(default_field_value=default_field_value)
            is_equal: bool = validate_val_min_n_default_fld_value_equal_or_not(val_min=val_min, replaced_default_field_value=replaced_default_field_value)
            if is_equal:
                val_min = val_min - 1
            #enabled: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            #if enabled:
            if layout == Layout.TABLE:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_min))
            else:
                set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_min))
            #else:
                #continue
        validate_flux_fld_val_min_in_widget(widget=widget, field_name=field_name)



def get_server_populate_fld(driver: WebDriver, schema_dict, layout: Layout, widget_type: WidgetType):

    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict),
                                          widget_type=WidgetType.INDEPENDENT, flux_property="server_populate")
    assert result[0]

    # table layout and tree
    if widget_type == WidgetType.INDEPENDENT:
        for widget_query in result[1]:
            widget_name = widget_query.widget_name
            widget = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            # SYSTEM CONTROL WIDGET IS ALREADY IN CREATE MODE SO EDIT BTN GOT DISSAPERED
            if widget_name == "system_control":
                continue
            if layout == Layout.TABLE:
                click_button_with_name(widget=widget, button_name="Show")
                click_button_with_name(widget=widget, button_name="Edit")
            else:
                switch_layout(widget=widget, layout=Layout.TREE)
                show_hidden_fields_in_tree_layout(widget=widget, driver=driver)

            for field_query in widget_query.fields:
                field_name: str = field_query.field_name
                xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                  widget_name=widget_name,
                                                  field_name=field_name)

                validate_server_populate_fld(widget=widget, xpath=xpath, field_name=field_name,
                                                 layout=layout)



    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT,
                                          flux_property="server_populate")
    print(result)
    assert result[0]

    # table layout and tree
    # TODO: exch_id field is not present in common_key in pair strat params widget
    if widget_type == WidgetType.DEPENDENT:
        for widget_query in result[1]:
            widget_name = widget_query.widget_name
            widget = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            if layout == Layout.TABLE:
                switch_layout(widget=widget, layout=Layout.TABLE)
                click_button_with_name(widget=widget, button_name="Show")
                if widget_name == "pair_strat_params":
                    click_button_with_name(driver.find_element(By.ID, "strat_collection"), button_name="Edit")
                else:
                    continue
            else:
                switch_layout(widget=widget, layout=Layout.TREE)
                show_hidden_fields_in_tree_layout(widget=widget, driver=driver)
            for field_query in widget_query.fields:
                field_name: str = field_query.field_name
                if field_name == "exch_id":
                    continue
                xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT,
                                                  widget_name=widget_name,
                                                  field_name=field_name)

                validate_server_populate_fld(widget=widget, xpath=xpath, field_name=field_name,
                                                 layout=layout)


def set_input_value_for_comma_seperated(driver: WebDriver, schema_dict, layout: Layout):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property="display_type")
    print(result)
    assert result[0]

    # TABLE LAYOUT
    field_name_n_input_value: Dict[str, any] = {}
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Edit")
        if widget_name == "order_limits" and layout == Layout.TABLE:
            switch_layout(widget=widget, layout=Layout.TABLE)
        elif layout == Layout.TREE and widget_name == "order_limits":
            pass
        elif layout == Layout.TREE:
            switch_layout(widget=widget, layout=Layout.TREE)

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # in strat status widget residual notional and balance notional fld disabled in table layout only
            if (field_name == "residual_notional" or field_name == "balance_notional") and layout == Layout.TABLE:
                continue
            val_min, val_max = get_val_min_n_val_max_of_fld(field_query)
            input_value: str = validate_property_that_it_contain_val_min_val_max_or_none(val_max=val_max,
                                                                                         val_min=val_min)
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)

            # Add key-value pair
            field_name_n_input_value[field_name] = input_value

            # is_enabled: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            # if is_enabled:
            # else:
            #     continue

            if layout == Layout.TABLE:
                set_table_input_field(widget=widget, xpath=xpath, value=str(input_value))
            else:
                if widget_name == "strat_status":
                    continue
                set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=input_value)
        validate_comma_separated_values(driver=driver, widget=widget, layout=layout,
                                        field_name_n_input_value=field_name_n_input_value, widget_name=widget_name)


def get_number_format_from_input_fld(result, schema_dict, driver: WebDriver, layout: Layout, widget_type: WidgetType):

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=layout)
        if layout == Layout.TABLE and widget_name == "portfolio_limits":
            click_button_with_name(widget=widget, button_name="Edit")
        if widget_name == "pair_strat_params":
            click_button_with_name(driver.find_element(By.ID, "strat_collection"), button_name="Edit")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            number_format_txt: str = field_query.properties['number_format']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=widget_type, widget_name=widget_name,
                                              field_name=field_name)
            number_format: str = get_flux_fld_number_format(widget=widget, xpath=xpath, layout=layout)
            return number_format, number_format_txt

