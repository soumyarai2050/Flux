from typing import Final, Optional, Tuple
import os
import time

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fastapi.encoders import jsonable_encoder

from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from tests.CodeGenProjects.addressbook.web_ui.web_ui_models import *
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
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_collection_widget)
    create_strat_btn = strat_collection_widget.find_element(By.XPATH, "//button[@name='Create']")
    create_strat_btn.click()
    time.sleep(Delay.SHORT.value)

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
    override_pair_strat()


def set_tree_input_field(widget: WebElement, xpath: str, name: str, value: str,
                         search_type: SearchType = SearchType.NAME,  autocomplete: bool = False) -> None:
    if not hasattr(By, search_type):
        raise Exception(f"unsupported search type: {search_type}")
    input_div_xpath: str = f"//div[@data-xpath='{xpath}']"
    input_div_element = widget.find_element(By.XPATH, input_div_xpath)
    input_element = input_div_element.find_element(getattr(By, search_type), name)
    input_element.click()
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    input_element.send_keys(value)
    if autocomplete:
        input_element.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
    # else not required


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
    input_div_xpath: str = f"//div[@data-xpath='{xpath}']"
    div_xpath = widget.find_element(By.XPATH, input_div_xpath)
    input_element = div_xpath.find_element(By.ID, name)
    input_element.click()
    input_element.send_keys(Keys.CONTROL + "a")
    input_element.send_keys(Keys.BACK_SPACE)
    input_element.send_keys(input_value)


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
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

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
    set_tree_input_field(widget=strat_limits_widget, xpath=xpath, name=name, value=value)

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
        time.sleep(Delay.SHORT.value)

    else:
        strats_limits_widget = driver.find_element(By.ID, "strat_limits")
        input_residual_mark_second_element = strats_limits_widget.find_element(By.ID, "residual_mark_seconds")
        driver.execute_script('arguments[0].scrollIntoView(true)', input_residual_mark_second_element)
        time.sleep(Delay.SHORT.value)

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
    value = get_value_from_input_field(widget=widget, xpath=xpath, layout=layout)
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
    time.sleep(Delay.SHORT.value)


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


def override_default_limits(order_limits, portfolio_limits):
    updated_order_limits: OrderLimitsBaseModel = OrderLimitsBaseModel(_id=order_limits.id, max_basis_points=150,
                                                                      max_px_deviation=2, min_order_notional=1_000)
    strat_manager_service_native_web_client.patch_order_limits_client(jsonable_encoder(updated_order_limits, by_alias=True,
                                                                                       exclude_none=True))

    updated_portfolio_limits: PortfolioLimitsBaseModel = \
        PortfolioLimitsBaseModel(_id=portfolio_limits.id, max_open_baskets=200)
    strat_manager_service_native_web_client.patch_portfolio_limits_client(jsonable_encoder(updated_portfolio_limits,
                                                                                           by_alias=True, exclude_none=True))


def override_pair_strat():
    pair_strat_list: List[PairStratBaseModel] = strat_manager_service_native_web_client.get_all_pair_strat_client()
    pair_strat: PairStratBaseModel
    for pair_strat in pair_strat_list:
        cancel_rate: CancelRateOptional = CancelRateOptional(max_cancel_rate=20)
        market_trade_volume_participation: MarketTradeVolumeParticipationOptional = \
            MarketTradeVolumeParticipationOptional(max_participation_rate=20)
        updated_pair_strat: PairStratBaseModel = \
            PairStratBaseModel(_id=pair_strat.id, strat_limits=StratLimitsOptional(
                cancel_rate=cancel_rate, market_trade_volume_participation=market_trade_volume_participation))
        strat_manager_service_native_web_client.patch_pair_strat_client(jsonable_encoder(
            updated_pair_strat, by_alias=True, exclude_none=True))

def switch_layout(widget: WebElement, layout: Layout) -> None:
    button_name: str = ""
    if layout == Layout.TREE:
        button_name = "UI_TREE"
    elif layout == Layout.TABLE:
        button_name = "UI_TABLE"
    try:
        layout_btn = widget.find_element(By.NAME, "Layout")
        layout_btn.click()
        time.sleep(Delay.SHORT.value)
        button_name_element = widget.find_element(By.NAME, button_name)
        button_name_element.click()
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
        time.sleep(Delay.SHORT.value)

        # Confirm the activation
        confirm_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
        confirm_btn.click()
        time.sleep(Delay.SHORT.value)

        # Verify if the strat is in active state
        pause_strat = driver.find_element(By.XPATH,
                                          "//tbody//button[@value='Pause'][normalize-space()='Pause']")
        btn_text = pause_strat.text
        assert btn_text == "PAUSE", "Failed to activate strat."

    elif button_text in ["ERROR", "PAUSE"]:
        print(f"Strat is in {button_text} state. Cannot activate.")

def confirm_save(driver: WebDriver) -> None:
    confirm_save_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    confirm_btn = confirm_save_dialog.find_element(By.XPATH, "//button[normalize-space()='Confirm Save']")
    confirm_btn.click()
    time.sleep(Delay.SHORT.value)

def select_n_unselect_checkbox(widget: WebElement, inner_text: str) -> None:
    settings_dropdown: WebElement = widget.find_element(By.XPATH, "//ul[@role='listbox']")
    dropdown_labels: List[WebElement] = settings_dropdown.find_elements(By.CSS_SELECTOR, "span[class^='MuiTypography-root']")
    span_element: WebElement
    for span_element in dropdown_labels:
        if span_element.text == inner_text:
            span_element.click()
            time.sleep(Delay.DEFAULT.value)
            break


def get_default_field_value(widget: WebElement, layout: Layout, xpath: str):
    if layout == Layout.TABLE:
        input_td_xpath: str = f"//td[@data-xpath='{xpath}']"
        input_td_xpath_element = widget.find_element(By.XPATH, input_td_xpath)
        input_td_xpath_element.click()
        get_field_value = input_td_xpath_element.find_element(By.TAG_NAME, "input").get_attribute('value')
        widget.click()
    else:
        input_div_xpath: str = f"//div[@data-xpath='{xpath}']"
        input_div_xpath_element = widget.find_element(By.XPATH, input_div_xpath)
        get_field_value = input_div_xpath_element.find_element(By.TAG_NAME, "input").get_attribute('value')
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



def validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict, widget_type: WidgetType, flux_property: str) -> str:
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


def validate_table_cell_enabled_or_not(widget: WebElement, xpath: str)-> bool:
    try:
        input_td_xpath: str = f"//td[@data-xpath='{xpath}']"
        input_td_xpath_element = widget.find_element(By.XPATH, input_td_xpath)
        input_td_xpath_element.click()
        widget.click()
        return True
    except NoSuchElementException:
        return False


def count_fields_in_tree(widget: WebElement) -> List[str]:
    field_elements = widget.find_elements(By.CLASS_NAME, "Node_node__sh0RD")
    field_names = []
    for field_element in field_elements:
        field_names.append(field_element.text)
    return field_names



def get_commonkey_item(widget: WebElement)-> dict:
    common_key_widget = widget.find_element(By.CLASS_NAME, "CommonKeyWidget_container__hOXaW")
    common_key_item_elements = common_key_widget.find_elements(By.CLASS_NAME, "CommonKeyWidget_item__QEVHl")
    common_key_item_txt_dict = {}
    for common_key_item_element in common_key_item_elements:
        common_key_item_txt = common_key_item_element.text.split(":")
        key = common_key_item_txt[0].replace(" ", "_")
        value = common_key_item_txt[1]
        common_key_item_txt_dict[key] = value
    return common_key_item_txt_dict


def get_flux_flx_number_format_in_tree_layout(widget: WebElement) -> str:
    div_element = widget.find_element(By.CLASS_NAME, "MuiInputAdornment-root")
    number_format = div_element.find_element(By.TAG_NAME, "p")
    number_format_txt = number_format.text
    return number_format_txt


def get_flux_flx_number_format_in_table_layout(widget: WebElement, xpath: str) -> str:
    td_xpath: str = f"//td[@data-xpath='{xpath}']"
    td_element = widget.find_element(By.XPATH, td_xpath)
    td_element.click()
    div_element = widget.find_element(By.CLASS_NAME, "MuiInputAdornment-root")
    number_format = div_element.find_element(By.TAG_NAME, "p")
    number_format_txt = number_format.text
    return number_format_txt



def get_button_text(widget: WebElement) -> str:
    button_widget = widget.find_element(By.CLASS_NAME, "MuiTableBody-root")
    button_element = button_widget.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    button_text = button_element.text
    return button_text

def click_on_button(widget: WebElement, xpath: str) -> None:
    # td_xpath = f"//td[@data-xpath='{xpath}']"
    # td_element = widget.find_element(By.XPATH, td_xpath)
    # button_element = td_element.find_element(By.TAG_NAME, "button")
    # button_element.click()
    td_element = widget.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    button_element = td_element.find_element(By.CLASS_NAME, "MuiButtonBase-root")
    button_element.click()



def get_table_layout_field_name(widget: WebElement):
    thead_elements = widget.find_elements(By.CLASS_NAME, "MuiTableCell-root")
    field_name_texts = []
    for thead_element in thead_elements:
        field_name_texts.append(thead_element.text)
    return field_name_texts


def validate_comma_separated_values(widget: WebElement, xpath: str, value: str):
    entered_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=Layout.TREE)
    value = value.replace(".55", "")
    assert entered_value == value


def get_fld_name_colour_in_tree(widget: WebElement, xpath: str):
    div_xpath: str = f"//div[@data-xpath='{xpath}']"
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
    if type(value) == str:
        splitted_list = value.split(".")
        if widget_type.DEPENDENT:
            xpath = splitted_list[1] + '.' + splitted_list[2]
            widget_name = splitted_list[1]
        elif widget_type.INDEPENDENT:
            xpath = splitted_list[0] + '.' + splitted_list[1] + '.' + splitted_list[2]
            widget_name = splitted_list[0]
        widget = driver.find_element(By.ID, widget_name)
        if layout.TREE:
            switch_layout(widget=widget, layout=Layout.TREE)
    div_xpath: str = f"//div[@data-xpath='{xpath}']"
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
    form_validation_dialog_elements: List[WebElement] = \
        form_validation_dialog.find_elements(By.CLASS_NAME, "object-key")
    form_validation_text_list: [str] = []
    for form_validation_dialog_element in form_validation_dialog_elements:
        form_validation_text_list.append(form_validation_dialog_element.text[1:-1])
    return form_validation_text_list

def click_on_continue_editing_btn(widget: WebElement) -> None:
    form_validation_dialog = widget.find_element(By.XPATH, "//div[@role='dialog']")
    continue_editing_btn = form_validation_dialog.find_element(
        By.XPATH, "//button[normalize-space()='Continue Editing']")
    continue_editing_btn.click()


def get_common_keys(widget: WebElement) -> List[str]:
    name: str = "span[class^='CommonKeyWidget_key']"
    common_key_elements: List[WebElement] = widget.find_elements(By.CSS_SELECTOR, name)
    key_element: WebElement
    common_keys_text = []
    for key_element in common_key_elements:
        common_keys_text.append(key_element.text)
    return common_keys_text


def get_replaced_common_keys(common_keys_list: List) -> List:
    list_of_common_keys = []
    for common_key in common_keys_list:
        list_of_common_keys.append(common_key.replace("common premium", "common_premium")
                                   .replace("hedge ratio","hedge_ratio").replace(":", ""))
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

def get_deafult_value(schema_dict, driver):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="default")
    print(result)
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            default_value: str = field_query.properties['default']