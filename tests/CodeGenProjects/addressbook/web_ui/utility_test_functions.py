from typing import Optional

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from tests.CodeGenProjects.addressbook.web_ui.web_ui_models import *
from tests.CodeGenProjects.addressbook.app.utility_test_functions import *
from tests.CodeGenProjects.addressbook.app.utility_test_functions import test_config_file_path, \
    strat_manager_service_native_web_client


SIMPLE_DATA_TYPE_LIST: Final[List[DataType]] = \
    [DataType.STRING, DataType.BOOLEAN, DataType.NUMBER, DataType.DATE_TIME, DataType.ENUM]
COMPLEX_DATA_TYPE_LIST: Final[List[DataType]] = [DataType.OBJECT, DataType.ARRAY]


def get_driver(config_dict: Dict, driver_type: DriverType) -> WebDriver:
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
    time.sleep(Delay.SHORT.value)
    strat_collection_widget.find_element(By.NAME, "Create").click()
    time.sleep(Delay.SHORT.value)

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

    more_options_btn = pair_strat_params_widget.find_element(By.XPATH, "//button[@aria-label='options']")
    more_options_btn.click()
    time.sleep(2)
    plus_icon = pair_strat_params_widget.find_element(By.CSS_SELECTOR, "div[class^='HeaderField_menu']")
    plus_icon.click()
    time.sleep(2)

    # select strat_leg2.sec.sec_id
    xpath = "pair_strat_params.strat_leg2.sec.sec_id"
    value = pair_strat["pair_strat_params"]["strat_leg2"]["sec"]["sec_id"]
    set_autocomplete_field(widget=pair_strat_params_widget, xpath=xpath, name="sec_id", search_type=SearchType.NAME,
                           value=value)

    strat_status_widget = driver.find_element(By.ID, "strat_status")
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_status_widget)
    time.sleep(Delay.SHORT.value)

    # select pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat["pair_strat_params"]["common_premium"]
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name="common_premium", value=value,
                         search_type=SearchType.ID)

    # save strat collection
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    time.sleep(Delay.SHORT.value)
    confirm_save(driver=driver)
    # verify pair strat
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

    # verifying the values of pair_strat
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

    # strat_limits.max_cb_notional
    xpath = "max_cb_notional"
    value = strat_limits["max_cb_notional"]
    name = "max_cb_notional"
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

    # strat_limits.max_open_cb_notional
    xpath = "max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    name = "max_open_cb_notional"
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

    driver.execute_script('arguments[0].scrollIntoView(true)', input_residual_mark_second_element)
    time.sleep(Delay.SHORT.value)

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
    xpath = "max_open_orders_per_side"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    assert value == str(strat_limits["max_open_orders_per_side"])

    # max_cb_notional
    xpath = "max_cb_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_cb_notional"])

    # max_open_cb_notional
    xpath = "max_open_cb_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_open_cb_notional"])

    # max_net_filled_notional
    xpath = "max_net_filled_notional"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    value = value.replace(",", '')
    assert value == str(strat_limits["max_net_filled_notional"])

    # max_concentration
    xpath = "max_concentration"
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
    print(type(value))
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
    time.sleep(Delay.SHORT.value)


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
            if field_properties["type"] in SIMPLE_DATA_TYPE_LIST:
                if flux_property in field_properties:
                    field_queries.append(FieldQuery(field_name=field, properties=field_properties))
            elif field_properties["type"] in COMPLEX_DATA_TYPE_LIST:
                if field_properties.get("underlying_type") is not None and \
                        field_properties["underlying_type"] in SIMPLE_DATA_TYPE_LIST:
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
            search_schema_for_flux_property(widget_schema)
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


def override_default_limits(order_limits: OrderLimitsBaseModel, portfolio_limits: PortfolioLimitsBaseModel):
    updated_order_limits: OrderLimitsBaseModel = OrderLimitsBaseModel(_id=order_limits.id, max_basis_points=150,
                                                                      max_px_deviation=2, min_order_notional=1_000,
                                                                      max_order_notional=400000)
    strat_manager_service_native_web_client.patch_order_limits_client(jsonable_encoder(
        updated_order_limits, by_alias=True, exclude_none=True))

    updated_portfolio_limits: PortfolioLimitsBaseModel = \
        PortfolioLimitsBaseModel(_id=portfolio_limits.id, max_open_baskets=200)
    strat_manager_service_native_web_client.patch_portfolio_limits_client(jsonable_encoder(
        updated_portfolio_limits, by_alias=True, exclude_none=True))


def override_strat_limit(strat_executor_service_http_client: StratExecutorServiceHttpClient):
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
    try:
        layout_btn = widget.find_element(By.NAME, "Layout")
        layout_btn.click()
        time.sleep(Delay.SHORT.value)
        btn_name_element = widget.find_element(By.NAME, btn_name)
        btn_name_element.click()
    except NoSuchElementException as e:
        raise Exception(f"failed to switch to layout: {layout};;; exception: {e}")


def activate_strat(widget: WebElement, driver: WebDriver) -> None:
    # Find the button with the name 'strat_state'
    activate_btn = widget.find_element(By.NAME, "strat_state")

    # Get the button text
    button_text = activate_btn.text

    # Check if the button text is ACTIVATE, ERROR, or PAUSED
    assert button_text in ["ACTIVATE", "ERROR", "PAUSE"], "Unknown button state."

    if button_text == "ACTIVATE":
        # Activate the strat
        activate_btn.click()
        time.sleep(Delay.SHORT.value)

        # Confirm the activation
        confirm_save(driver=driver)
        time.sleep(Delay.SHORT.value)

        # Verify if the strat is in active state
        pause_strat = widget.find_element(By.XPATH, '//*[@id="strat_collection"]/h6/div/div/button[1]')

        btn_text = pause_strat.text
        assert btn_text == "PAUSE", "Failed to activate strat."

    elif button_text in ["ERROR", "PAUSE"]:
        print(f"Strat is in {button_text} state. Cannot activate.")


def confirm_save(driver: WebDriver) -> None:
    confirm_save_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    confirm_btn = confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
    confirm_btn.click()
    time.sleep(Delay.SHORT.value)


def select_n_unselect_checkbox(driver: WebDriver, inner_text: str) -> None:
    settings_dropdown: WebElement = driver.find_element(By.CLASS_NAME, "MuiPopover-paper")
    dropdown_elements = settings_dropdown.find_elements(By.TAG_NAME, "li")

    span_element: WebElement
    for dropdown_element in dropdown_elements:
        dropdown_label = dropdown_element.find_element(By.CSS_SELECTOR, "label")
        if dropdown_label.text == inner_text:
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


def verify_popup_type_n_save_or_discard_changes(widget: WebElement, driver: WebDriver) -> None:
    dialog_element = widget.find_element(By.XPATH, "//div[@role='dialog']")
    text_element = dialog_element.find_element(By.TAG_NAME, "p")
    dialog_text = text_element.text
    if dialog_text == "Review changes:":
        confirm_save(driver=driver)
    elif dialog_text == "Form validation failed due to following errors:":
        discard_changes(widget=widget)


def show_hidden_fields_in_tree_layout(widget: WebElement, driver: WebDriver) -> None:
    show_element = widget.find_element(By.NAME, "Show")
    show_element.click()
    list_element = driver.find_element(By.XPATH, "//ul[@role='listbox']")
    li_element = list_element.find_element(By.TAG_NAME, "li")
    span_element = li_element.find_element(By.TAG_NAME, "span")
    span_element.click()


def show_hidden_field_in_review_changes_popup(driver: WebDriver) -> None:
    review_changes_widget = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")
    expand_buttons = review_changes_widget.find_elements(By.CLASS_NAME, "node-ellipsis")
    for expand_button in expand_buttons:
        expand_button.click()


def validate_property_that_it_contain_val_min_val_max_or_none(schema_dict, widget_type: WidgetType,
                                                              flux_property: str) -> str:
    result = get_widgets_by_flux_property(schema_dict, widget_type=widget_type, flux_property=flux_property)
    for widget_query in result[1]:
        for field_query in widget_query.fields:
            val_min: str = (field_query.properties.get("val_min"))
            val_max: str = (field_query.properties.get("val_max"))
            if val_min is not None:
                val_min: float = int(val_min) + 1.55
                return str(val_min)
            elif val_max is not None:
                val_max: float = int(val_max) - 1.55
                return str(val_max)
            else:
                return str(1000.5)

def validate_table_cell_enabled_or_not(widget: WebElement, xpath: str) -> bool:
    try:
        input_td_xpath: str = get_table_input_field_xpath(xpath=xpath)
        input_td_element = widget.find_element(By.XPATH, input_td_xpath)
        # input_td_element.click()
        # input_td_element.send_keys(Keys.ENTER)
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

    common_key_widget = widget.find_element(By.CLASS_NAME, "CommonKeyWidget_container__Ek2YA")
    common_key_item_elements = common_key_widget.find_elements(By.CLASS_NAME, "CommonKeyWidget_item__ny8Fj")
    common_key_items: Dict[str] = {}
    for common_key_item_element in common_key_item_elements:
        common_key_item_txt = common_key_item_element.text.split(":")
        key = common_key_item_txt[0].replace(" ", "_")
        value = common_key_item_txt[1]
        common_key_items[key] = value
    return common_key_items


def get_flux_fld_number_format(widget: WebElement, xpath: str, layout: Layout) -> str:
    if layout == Layout.TREE:
        tag: str = "div"
    else:
        tag: str = "td"
    layout_xpath: str = f"//{tag}[@data-xpath='{xpath}']"
    td_element = widget.find_element(By.XPATH, layout_xpath)
    td_element.click()
    time.sleep(2)
    div_element = widget.find_element(By.CLASS_NAME, "MuiInputAdornment-root")
    number_format_element = div_element.find_element(By.TAG_NAME, "p")
    number_format = number_format_element.text
    return number_format


def get_pressed_n_unpressed_btn_txt(widget: WebElement) -> str:
    button_widget = widget.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    button_text = button_widget.text
    return button_text


def click_on_button(widget: WebElement) -> None:
    btn_element = widget.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    btn_element.click()


def get_table_layout_field_name(widget: WebElement):
    thead_elements = widget.find_elements(By.CLASS_NAME, "MuiTableCell-root")
    field_name_texts = []
    for thead_element in thead_elements:
        field_name_texts.append(thead_element.text)
    return field_name_texts


def validate_comma_separated_values(widget: WebElement, xpath: str, value: str):
    entered_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=Layout.TREE)
    entered_value = entered_value.split(".")[0]
    entered_value = entered_value.replace(",", "")
    value = value.split(".")[0]
    assert entered_value == value


def get_fld_name_colour_in_tree(widget: WebElement, xpath: str):
    div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    div_xpath_element = widget.find_element(By.XPATH, div_xpath)
    span_element = div_xpath_element.find_element(By.CLASS_NAME, "Node_error__Vi-Uc")
    color = span_element.value_of_css_property("color")
    return color


def get_fld_name_colour_in_table(widget: WebElement, xpath: str):
    common_keys = get_common_keys(widget=widget)


def get_progress_bar_level(widget: WebElement) -> str:
    box_root_element = widget.find_element(By.CLASS_NAME, "MuiBox-root")
    span_element = box_root_element.find_element(By.CLASS_NAME, "MuiLinearProgress-root")
    progress_level = span_element.get_attribute("aria-valuenow")
    return progress_level


def get_str_value(value: str, driver: WebDriver, widget_type: WidgetType, layout: Layout):
    widget: WebElement
    xpath: str = ""
    widget_name: str = ""
    if isinstance(value, str):
        splitted_list = value.split(".")
        if widget_type.DEPENDENT:
            xpath = splitted_list[0] + '.' + splitted_list[1]
            widget_name = splitted_list[0]
        elif widget_type.INDEPENDENT:
            xpath = splitted_list[0] + '.' + splitted_list[1] + '.' + splitted_list[2]
            widget_name = splitted_list[0]
        widget = driver.find_element(By.ID, widget_name)
        if layout.TREE:
            switch_layout(widget=widget, layout=Layout.TREE)
    div_xpath: str = get_tree_input_field_xpath(xpath=xpath)
    div_element_xpath = widget.find_element(By.XPATH, div_xpath)
    input_element = div_element_xpath.find_element(By.TAG_NAME, "input")
    field_value = input_element.get_attribute('value')
    return field_value


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


def click_on_continue_editing_btn(widget: WebElement) -> None:
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(
        By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()


def get_common_keys(widget: WebElement) -> List[str]:

    common_key_widget = widget.find_element(By.CLASS_NAME, "CommonKeyWidget_container__Ek2YA")
    name: str = "CommonKeyWidget_item__ny8Fj"
    common_key_elements: List[WebElement] = common_key_widget.find_elements(By.CLASS_NAME, name)
    key_element: WebElement
    common_keys_text = []
    for key_element in common_key_elements:
        span_element = key_element.find_element(By.TAG_NAME, "span")
        common_keys_text.append(span_element.text.split(":")[0])
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


def get_table_headers(widget: WebElement) -> list:
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
    result = get_widgets_by_flux_property(schema_dict, widget_type=widget_type, flux_property=flux_property)
    assert result[0]
    name_lst: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        name_lst.append(widget_name)
    return name_lst


def get_fld_name_frm_schema(schema_dict, widget_type: WidgetType, flux_property: str) -> List[str]:
    result = get_widgets_by_flux_property(schema_dict, widget_type=widget_type, flux_property=flux_property)
    assert result[0]
    name_lst: List[str] = []
    for widget_query in result[1]:
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            name_lst.append(field_name)
    return name_lst


def get_property_value_frm_schema(schema_dict, widget_type: WidgetType, flux_property: str):
    result = get_widgets_by_flux_property(schema_dict, widget_type=widget_type, flux_property=flux_property)
    assert result[0]
    name_lst: List[str] = []
    for widget_query in result[1]:
        for field_query in widget_query.fields:
            val_max = field_query.properties['val_max']
            name_lst.append(val_max)
    return name_lst


def replace_default_value(default_field_value) -> int:
    default_field_value = default_field_value.replace(',', '')
    default_field_value: int = int(default_field_value)
    return default_field_value


def create_tob_md_ld_fj_os_oj(driver: WebDriver, top_of_book_list: List[TopOfBookBaseModel],
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

    expected_top_of_book_list: List[TopOfBookBaseModel] = (
        executor_web_client.create_all_top_of_book_client(top_of_book_list))
    assert top_of_book_list == expected_top_of_book_list

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
            field_name != "exch_response_max_seconds"):
        xpath: str = get_xpath_from_field_name(schema_dict, widget_type=widget_type,
                                               widget_name=widget_name, field_name=field_name)

        field_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
        assert field_value == default_value


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


def get_placeholder_from_element(widget: WebElement, id: str):
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
            time.sleep(Delay.SHORT.value)
            widget.find_element(By.XPATH, '//*[@id="strat_status"]/div/div/div/ul/div[27]/div[2]/button').click()
            widget.find_element(By.XPATH, '//*[@id="strat_status"]/div/div/div/ul/div[27]/div[2]').click()
        elif widget_name == "pair_strat_params":

            strat_collection_widget = driver.find_element(By.ID, "strat_collection")
            click_button_with_name(widget=strat_collection_widget, button_name="Create")
            scroll_into_view(driver=driver, element=widget)
            switch_layout(widget=widget, layout=Layout.TREE)
            time.sleep(Delay.SHORT.value)
            widget.find_element(By.XPATH, '//*[@id="pair_strat_params"]/div/div/div/ul/ul/div[2]/div[2]/button').click()
            widget.find_element(By.XPATH, '//*[@id="pair_strat_params"]/div/div/div/ul/ul/div[2]/div[2]').click()
        else:
            scroll_into_view(driver=driver, element=widget)
            click_button_with_name(widget=widget, button_name="Create")
            switch_layout(widget=widget, layout=Layout.TREE)
            time.sleep(Delay.SHORT.value)

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            placeholder: str = get_placeholder_from_element(widget=widget, id=field_name)
            default_placeholder: str = field_query.properties['ui_placeholder']

            assert default_placeholder == placeholder


def get_element_text_list_from_filter_popup(driver: WebDriver) -> List[str]:
    container: WebElement = driver.find_element(By.CLASS_NAME, "MuiDialogContent-root")

    # Find all <span> elements within the container
    elements = container.find_elements(By.CLASS_NAME, "DynamicMenu_filter_name__OdQVe")

    # Get the text of each element and store in a list
    element_texts: List[str] = [element.text.replace(" ", "_") for element in elements]

    return element_texts
