from typing import Dict, List
import random
import time

import pytest

# third party imports
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa

# project specific imports
from tests.CodeGenProjects.addressbook.web_ui.utility_test_functions import (
    click_button_with_name, set_tree_input_field, confirm_save, create_strat_limits_using_tree_view, switch_layout,
    activate_strat, validate_strat_limits, validate_table_cell_enabled_or_not, set_table_input_field,
    get_commonkey_items, get_common_keys, get_replaced_common_keys, select_n_unselect_checkbox, get_table_headers,
    save_nested_strat, get_widgets_by_flux_property, get_xpath_from_field_name, replace_default_value,
    get_default_field_value, expand_all_nested_fld_name_frm_review_changes_dialog, get_object_keys_from_dialog_box,
    discard_changes, scroll_into_view, validate_property_that_it_contain_val_min_val_max_or_none,
    get_flux_fld_number_format, show_hidden_fields_in_tree_layout, count_fields_in_tree,
    validate_comma_separated_values, get_fld_name_colour_in_tree, get_unsaved_changes_discarded_key,
    click_on_okay_button_unsaved_changes_popup, set_autocomplete_field, strat_manager_service_native_web_client,
    flux_fld_default_widget, get_select_box_value, get_placeholder_from_element, get_web_project_url,
    flux_fld_sequence_number_in_widget)
from tests.CodeGenProjects.addressbook.web_ui.web_ui_models import (
    DriverType, Delay, Layout, WidgetType, SearchType)

# to parameterize all tests. to add support for other browsers, add the DriverType here
# pytestmark = pytest.mark.parametrize("driver_type", [DriverType.CHROME])
pytestmark = pytest.mark.parametrize("driver_type", [DriverType.EDGE])


def test_create_pair_strat(clean_and_set_limits, driver_type, web_project):
    # Test the creation of pair_strat and validate it
    # You may need to interact with the web project to verify that pair_strat is created successfully
    # For example:
    #   - Locate the pair_strat widget
    #   - Verify relevant information or behavior
    pass


def test_update_pair_strat_n_create_n_activate_strat_limits_using_tree_view(clean_and_set_limits, driver_type,
                                                                            web_project, driver: WebDriver,
                                                                            pair_strat_edit: Dict,
                                                                            pair_strat: Dict, strat_limits: Dict):

    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    click_button_with_name(widget=strat_collection_widget, button_name="Edit")
    time.sleep(Delay.SHORT.value)

    # # pair_strat_params.common_premium
    xpath: str = "pair_strat_params.common_premium"
    value = pair_strat_edit["pair_strat_params"]["common_premium"]
    name: str = "common_premium"
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value)

    # pair_strat_params.hedge_ratio
    xpath: str = "pair_strat_params.hedge_ratio"
    value = pair_strat_edit["pair_strat_params"]["hedge_ratio"]
    name: str = "hedge_ratio"
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value)

    click_button_with_name(widget=strat_collection_widget, button_name="Save")
    confirm_save(driver=driver)
    time.sleep(2)

    # scroll into view
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_limits_widget)
    time.sleep(Delay.SHORT.value)
    click_button_with_name(widget=strat_limits_widget, button_name="Edit")

    switch_layout(widget=strat_limits_widget, layout=Layout.TREE)

    create_strat_limits_using_tree_view(driver=driver, strat_limits=strat_limits, layout=Layout.TREE)
    click_button_with_name(strat_limits_widget, "Save")
    time.sleep(Delay.SHORT.value)
    confirm_save(driver=driver)

    activate_strat(widget=strat_collection_widget, driver=driver)

    # validate_strat_limits
    switch_layout(widget=strat_limits_widget, layout=Layout.TREE)
    click_button_with_name(widget=strat_collection_widget, button_name="Edit")
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)
    driver.quit()


def test_update_strat_limits_n_activate_using_table_view(clean_and_set_limits, driver_type, web_project, driver,
                                                         pair_strat: Dict, strat_limits: Dict):

    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")

    click_button_with_name(widget=strat_limits_widget, button_name="Edit")

    # max_open_per_orders_side
    xpath = "max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cb_notional
    xpath = "max_cb_notional"
    value = strat_limits["max_cb_notional"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_open_cb_notional
    xpath = "max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_net_filled_notional
    xpath = "max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_concentration
    xpath = "max_concentration"
    value = strat_limits["max_concentration"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # limit_up_down_volume_participation_rate
    xpath = "limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cancel_rate
    xpath = "cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "cancel_rate.applicable_period_seconds"
    value = strat_limits["cancel_rate"]["applicable_period_seconds"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # waived_min_orders
    xpath = "cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_participation_rate
    xpath = "market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "market_trade_volume_participation.applicable_period_seconds"
    value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # participation_rate
    xpath = "market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # depth_levels
    xpath = "market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_residual
    xpath = "residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # residual_mark_seconds
    xpath = "residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_limits_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    click_button_with_name(strat_limits_widget, "Save")
    time.sleep(2)
    confirm_save(driver=driver)

    activate_strat(widget=strat_collection_widget, driver=driver)

    click_button_with_name(widget=strat_limits_widget, button_name="Edit")

    # validating the values
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TABLE)


def test_field_hide_n_show_in_common_key(clean_and_set_limits, driver_type, web_project, driver, pair_strat: Dict):

    pair_strat_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_widget, layout=Layout.TABLE)

    common_keys: List[str] = get_common_keys(widget=pair_strat_widget)
    replaced_str_common_keys: List[str] = get_replaced_common_keys(common_keys_list=common_keys)
    # select a random key
    inner_text: str = random.choice(replaced_str_common_keys)

    # searching the random key in setting and unselecting checkbox
    setting_btn = pair_strat_widget.find_element(By.NAME, "Settings")
    setting_btn.click()
    select_n_unselect_checkbox(driver=driver, inner_text=inner_text)

    # validating that unselected key is not visible on table view
    common_keys: List[str] = get_common_keys(widget=pair_strat_widget)
    replaced_str_common_keys: List[str] = get_replaced_common_keys(common_keys_list=common_keys)
    assert inner_text not in replaced_str_common_keys, \
        f"{inner_text} field is visible in common keys, expected to be hidden"

    #  searching the random key in setting and selecting checkbox
    select_n_unselect_checkbox(driver=driver, inner_text=inner_text)

    # validating that selected checkbox is visible on table view
    common_keys: List[str] = get_common_keys(widget=pair_strat_widget)
    replaced_str_common_keys: List[str] = get_replaced_common_keys(common_keys_list=common_keys)
    assert inner_text in replaced_str_common_keys, \
        f"{inner_text} field is not visible in common keys, expected to be visible"


def test_hide_n_show_in_table_view(clean_and_set_limits, driver_type, web_project, driver, pair_strat: Dict):

    # TODO: ui bug symbol side snapshot is not present
    # activate_strat(driver=driver)
    # no data is present in symbol side snapshot widget
    symbol_side_snapshot_widget = driver.find_element(By.ID, "symbol_side_snapshot")
    driver.execute_script('arguments[0].scrollIntoView(true)', symbol_side_snapshot_widget)

    # selecting random table text from table view
    table_headers = get_table_headers(widget=symbol_side_snapshot_widget)
    inner_text = random.choice(table_headers)

    #  searching the selected random table text in setting and unselecting checkbox
    symbol_side_snapshot_widget.find_element(By.NAME, "Settings").click()
    select_n_unselect_checkbox(driver=driver, inner_text=inner_text)

    # validating that unselected text is not visible on table view
    table_headers: List[str] = get_table_headers(widget=symbol_side_snapshot_widget)
    assert inner_text not in table_headers

    # searching the random table text in setting and selecting checkbox
    # symbol_side_snapshot_widget.find_element(By.NAME, "Settings").click()
    select_n_unselect_checkbox(driver=driver, inner_text=inner_text,)

    # validating that selected check is visible on table view
    table_headers: List[str] = get_table_headers(widget=symbol_side_snapshot_widget)
    assert inner_text in table_headers


def test_nested_pair_strat_n_strats_limits(clean_and_set_limits, driver_type, web_project, driver, pair_strat: Dict,
                                           pair_strat_edit: Dict, strat_limits: Dict):
    # bug in the ui
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_params_widget, layout=Layout.TABLE)
    click_button_with_name(widget=strat_collection_widget, button_name="Edit")

    pair_strat_td_elements = pair_strat_params_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    enabled_or_not = validate_table_cell_enabled_or_not
    if enabled_or_not:
        actions = ActionChains(driver)
        actions.double_click(pair_strat_td_elements[4]).perform()

    nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    # update_value_in_nested_tree_layout
    # select pair_strat_params.common_premium
    xpath = "pair_strat_params.common_premium"
    value = pair_strat["pair_strat_params"]["common_premium"]
    name: str = "common_premium"
    set_tree_input_field(widget=nested_tree_dialog, xpath=xpath, name=name, value=value)

    # pair_strat_params.hedge_ratio
    xpath = "pair_strat_params.hedge_ratio"
    value = pair_strat_edit["pair_strat_params"]["hedge_ratio"]
    name: str = "hedge_ratio"
    set_tree_input_field(widget=nested_tree_dialog, xpath=xpath, name=name, value=value)

    save_nested_strat(driver=driver)

    # open nested tree layout in strat limit
    click_button_with_name(widget=strat_limits_widget, button_name="Edit")
    strat_limits_td_elements = strat_limits_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    enabled_or_not = validate_table_cell_enabled_or_not
    if enabled_or_not:
        actions = ActionChains(driver)
        actions.double_click(strat_limits_td_elements[0]).perform()

    create_strat_limits_using_tree_view(driver=driver, strat_limits=strat_limits, layout=Layout.NESTED)
    save_nested_strat(driver=driver)

    actions = ActionChains(driver)
    actions.double_click(strat_limits_td_elements[0]).perform()
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)


def test_widget_type(driver_type, schema_dict: Dict[str, any]):
    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.DEPENDENT,
                                          flux_property="button")
    print(result)


def test_flux_fld_val_max_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                    schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, WidgetType.INDEPENDENT, "val_max")
    assert result[0]
    print(result)

    # order_limits_n_portfolio_limits_table_layout_val_max_for_valid_scenario
    field_name_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "strat_status":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")

        switch_layout(widget=widget, layout=Layout.TABLE)

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)

            field_name_list.append(field_name)
            val_max: int = int(field_query.properties['val_max'])

            field_value: str = get_default_field_value(widget=widget, layout=Layout.TABLE, xpath=xpath)
            if field_value:
                field_value: int = replace_default_value(default_field_value=field_value)
            if val_max == field_value:
                val_max = val_max - 1

            set_table_input_field(widget=widget, xpath=xpath, value=str(val_max))

        if widget_name == "strat_status":
            break
        if widget_name == "order_limits":
            set_table_input_field(widget=widget, xpath="min_order_notional", value="1000")
        if widget_name == "portfolio_limits":
            set_table_input_field(widget=widget, xpath="max_open_baskets", value="1000")

        click_button_with_name(widget=widget, button_name="Save")
        expand_all_nested_fld_name_frm_review_changes_dialog(driver=driver)
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        # object_keys.pop()
        for field_name in field_name_list:
            assert field_name in object_keys
        confirm_save(driver=driver)
        field_name_list.clear()

    # order_limits_n_portfolio_limits_tree_layout_val_max_for_valid_scenario
    field_name_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "strat_status":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            field_name_list.append(field_name)
            val_max: int = int(field_query.properties['val_max'])
            field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            if field_value:
                field_value: int = replace_default_value(default_field_value=field_value)
            if val_max == field_value:
                val_max = val_max - 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))

        if widget_name == "strat_status":
            break
        if widget_name == "order_limits":
            set_tree_input_field(widget=widget, xpath="min_order_notional", name="min_order_notional", value="1000")
        if widget_name == "portfolio_limits":
            set_tree_input_field(widget=widget, xpath="max_open_baskets", name="max_open_baskets", value="1000")
        click_button_with_name(widget=widget, button_name="Save")
        expand_all_nested_fld_name_frm_review_changes_dialog(driver=driver)
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        for field_name in field_name_list:
            assert field_name in object_keys
        confirm_save(driver=driver)
        field_name_list.clear()

    # order_limits_n_portfolio_limits_table_layout_above_val_max_for_invalid_scenario
    xpath_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "strat_status":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TABLE)

        if widget_name == "order_limits":
            switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            xpath_list.append(xpath)
            val_max: int = int(field_query.properties['val_max']) + 1
            enabled: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            # if enabled:
            set_table_input_field(widget=widget, xpath=xpath, value=str(val_max))
            # else:
            #     continue
        if widget_name == "strat_status":
            break
        if widget_name == "order_limits":
            set_table_input_field(widget=widget, xpath="min_order_notional", value="1000")
        if widget_name == "portfolio_limits":
            set_table_input_field(widget=widget, xpath="max_open_baskets", value="1000")
        click_button_with_name(widget=widget, button_name="Save")
        expand_all_nested_fld_name_frm_review_changes_dialog(driver=driver)
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        for xpath in xpath_list:
            assert xpath in object_keys
        discard_changes(widget=widget)
        xpath_list.clear()

    # order_limits_n_portfolio_limits_tree_layout_above_val_max_for_invalid_scenario
    xpath_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "strat_status":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            xpath_list.append(xpath)
            val_max: int = int(field_query.properties['val_max']) + 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))

        if widget_name == "strat_status":
            break
        if widget_name == "portfolio_limits":
            set_tree_input_field(widget=widget, xpath="max_open_baskets", name="max_open_baskets", value="1000")
        if widget_name == "order_limits":
            set_tree_input_field(widget=widget, xpath="min_order_notional", name="min_order_notional", value="1000")
        click_button_with_name(widget=widget, button_name="Save")
        expand_all_nested_fld_name_frm_review_changes_dialog(driver=driver)
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        for xpath in xpath_list:
            assert xpath in object_keys
        discard_changes(widget=widget)
        xpath_list.clear()

    result = get_widgets_by_flux_property(schema_dict, WidgetType.DEPENDENT, "val_max")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="val_max")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="val_max")
    print(result)
    assert not result[0]


def test_flux_fld_val_min_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                    schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="val_min")
    print(result)
    assert result[0]

    # order_limits_n_portfolio_limits_table_layout_val_min_for_valid_scenario
    field_name: str = ''
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget, Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name

            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TABLE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_min == get_field_value:
                val_min = val_min - 1
            enabled: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_min))
            else:
                continue
            click_button_with_name(widget=widget, button_name="Save")
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in object_keys
        discard_changes(widget=widget)

    # order_limits_n_portfolio_limits_tree_layout_val_min_for_valid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_min == get_field_value:
                val_min = val_min - 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_min))

        click_button_with_name(widget=widget, button_name="Save")
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in object_keys
        discard_changes(widget=widget)

    # order_limits_n_portfolio_limits_table_layout_below_val_min_for_invalid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min']) - 5

            enabled = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_min))
            else:
                continue
        click_button_with_name(widget=widget, button_name="Save")
        object_keys: List[str] = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in object_keys
        discard_changes(widget=widget)

    # order_limits_n_portfolio_limits_tree_layout_below_val_min_for_invalid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min']) - 5
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_min))
        click_button_with_name(widget=widget, button_name="Save")
        object_keys = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in object_keys
        discard_changes(widget=widget)

    # TODO:  val min property is not used in dependent widget yet
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="val_min")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="val_min")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="val_min")
    print(result)
    assert not result[0]


def test_flux_fld_help_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                 schema_dict, pair_strat: Dict):
    # TODO: need to fix schema.json
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="help")
    print(result)
    assert result[0]
    # ui bug in table layout

    # order_limits_n_portfolio_limits_table_layout_help_for_valid_scenario
    for widget_query in result[1]:
        for field_query in widget_query.fields:
            # scroll into view
            widget_name = widget_query.widget_name
            widget = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            time.sleep(Delay.SHORT.value)
            help_txt: str = field_query.properties['help']
            widget.find_element(By.NAME, "Settings").click()
            setting_dropdown = widget.find_element(By.XPATH, f'//*[@id="{widget_name}_table_settings"]/div[3]')
            time.sleep(Delay.SHORT.value)
            contains_element = setting_dropdown.find_element(By.XPATH, f"//button[@aria-label='{help_txt}']")
            actions = ActionChains(driver)

            actions.move_to_element(contains_element).perform()
            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
            hovered_element_text = tooltip_element.text
            assert help_txt == hovered_element_text
            contains_element.click()
            time.sleep(Delay.DEFAULT.value)
            driver.refresh()
            time.sleep(Delay.DEFAULT.value)

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="help")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="help")

    # order_limits_n_portfolio_limits_table_layout_help_for_valid_scenario
    for widget_query in result[1]:
        for field_query in widget_query.fields:
            # scroll into view
            widget_name = widget_query.widget_name
            widget = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            time.sleep(Delay.SHORT.value)
            help_txt: str = field_query.properties['help']
            widget.find_element(By.NAME, "Settings").click()
            setting_dropdown = widget.find_element(By.XPATH, f'//*[@id="{widget_name}_table_settings"]/div[3]')
            time.sleep(Delay.SHORT.value)
            contains_element = setting_dropdown.find_element(By.XPATH, f"//button[@aria-label='{help_txt}']")
            actions = ActionChains(driver)
            actions.move_to_element(contains_element).perform()
            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
            hovered_element_text = tooltip_element.text
            assert help_txt == hovered_element_text
            contains_element.click()
            time.sleep(Delay.DEFAULT.value)
            driver.refresh()
            time.sleep(Delay.DEFAULT.value)

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="help")
    print(result)
    assert not result[0]


def test_flux_fld_display_type_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                         schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
    print(result)
    assert result[0]

    # portfolio limits, order limits and portfolio status
    # table_layout
    field_name: str = ""
    display_type: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            display_type: str = type(field_query.properties['display_type'])
            value = validate_property_that_it_contain_val_min_val_max_or_none(
                schema_dict=schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(value))
            else:
                continue
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)
        common_keys_dict = get_commonkey_items(widget=widget)
        input_value = int(common_keys_dict[field_name].replace(",", ""))
        assert isinstance(input_value, int)

    # tree_layout
    field_name: str = ""
    display_type: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # order_notional_field_is_a_repetated_field_that's_why_continue
            if field_name == "order_notional" and widget_name == "portfolio_status":
                continue
            display_type: str = field_query.properties['display_type']
            value = validate_property_that_it_contain_val_min_val_max_or_none(
                schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(value))
        click_button_with_name(widget=widget, button_name="Save")
        switch_layout(widget=widget, layout=Layout.TABLE)
        common_keys_dict = get_commonkey_items(widget=widget)
        input_value = int(common_keys_dict[field_name].replace(",", ""))
        assert isinstance(input_value, int)

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="display_type")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="display_type")
    print(result)
    assert result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="display_type")
    print(result)
    assert not result[0]


def test_flux_fld_number_format_in_independent_widget(clean_and_set_limits, driver_type, web_project, driver,
                                                      schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                          flux_property="number_format")
    print(result)
    assert result[0]

    # table_layout
    # in strats limits premium percentage not fetching with MuiInputAdornment-root
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Edit")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # TODO: REMOVE CONTINUE LATER,for premium % field in order limits and portfolio
            #  limits widget contain same xapth
            if field_name == "premium_percentage" and widget_name == "strat_limits":
                continue
            number_format_txt: str = field_query.properties['number_format']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            # TODO: scroll horizontally
            number_format: str = get_flux_fld_number_format(widget=widget, xpath=xpath, layout=Layout.TABLE)
            assert number_format_txt == number_format

    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        time.sleep(10)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name == "premium_percentage" and widget_name == "strat_limits":
                continue
            number_format_txt: str = field_query.properties['number_format']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            get_number_format: str = get_flux_fld_number_format(widget=widget, xpath=xpath, layout=Layout.TREE)
            assert number_format_txt == get_number_format


def test_flux_fld_number_format_in_dependent_widget(clean_and_set_limits, driver_type, web_project, driver,
                                                    schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="number_format")
    print(result)
    assert result[0]

    # pair_start_params
    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        click_button_with_name(widget=strat_collection_widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TABLE)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            number_format_txt: str = field_query.properties['number_format']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            # TODO: UNABLE TO FIND (MuiInputAdornment-root) CLASS NAME IN PAIR STRAT BUT IN OTHER WIDGET WORKING FINE
            number_format: str = get_flux_fld_number_format(widget=widget, xpath=xpath, layout=Layout.TABLE)
            assert number_format_txt == number_format


def test_flux_flx_display_zero_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                         schema_dict, pair_strat: Dict):
    # TODO: display_zero_property_has_not_used_yet_in_independent_widget
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_zero")
    print(result)
    assert result[0]
    # can write only in table layout bcz tree layout contains progress bar
    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            value: str = "0"
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=value)
            click_button_with_name(widget=widget, button_name="Save")
            confirm_save(driver=driver)
            switch_layout(widget=widget, layout=Layout.TABLE)
            get_common_key_dict = get_commonkey_items(widget=widget)
            assert value == get_common_key_dict[field_name]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="display_zero")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="display_zero")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="display_zero")
    print(result)
    assert not result[0]


def test_flux_fld_server_populate_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                            schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(
        schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="server_populate")
    print(result)
    assert result[0]
    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Show")
        click_button_with_name(widget=widget, button_name="Edit")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            assert not enabled_or_not

    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        show_hidden_fields_in_tree_layout(widget=widget, driver=driver)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            field_names: List[str] = count_fields_in_tree(widget=widget)
            # validate that server populates field name does not present in tree layout after clicking on edit btn
            assert field_name not in field_names

    driver.refresh()
    time.sleep(Delay.SHORT.value)

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT,
                                          flux_property="server_populate")
    print(result)
    assert result[0]

    # table_layout
    # TODO: exch_id field is not present in common_key in pair strat params widget
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TABLE)
        show_hidden_fields_btn = widget.find_element(By.NAME, "Show")
        show_hidden_fields_btn.click()
        if widget_name == "pair_strat_params":
            click_button_with_name(widget=strat_collection_widget, button_name="Edit")
        else:
            continue
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name == "exch_id":
                continue
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            assert not enabled_or_not

    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        show_hidden_fields_in_tree_layout(widget=widget, driver=driver)
        # clicked on edit btn in table layout already so server populate field will disappear from tree layout
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name == "id":
                continue
            field_names: List[str] = count_fields_in_tree(widget=widget)
            # validate that server populates field name does not present in tree layout after clicking on edit btn
            assert field_name not in field_names
            # TODO: id is not present in strat status widget

    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode and only in `id` field is present
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="server_populate")
    print(result)
    assert result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="server_populate")
    print(result)
    assert not result[0]


def test_flux_fld_button_in_independent_widget(clean_and_set_limits, driver_type, web_project, driver,
                                               schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="button")
    print(result)
    assert result[0]

    # table_layout
    pressed_btn_txt: str = ""
    unpressed_btn_txt: str = ""
    for widget_query in result[1]:
        i = 0
        # TODO: BUG IN UI, STRAT STATE UNPRESSED CAPTION SHOULD BE ACTIVATE BUT IT IS PAUSE, REMOVE CONTINUE LATER
        widget_name = widget_query.widget_name
        if widget_name == "strat_status" or widget_name == "strat_limits":
            continue
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        if widget_name == "strat_limits":
            click_button_with_name(widget=widget, button_name="Edit")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # verify unpressed btn txt
            if widget_name == "strat_status" or widget_name == "portfolio_status":
                btn_element = widget.find_element(By.NAME, field_name)
                unpressed_btn_txt: str = btn_element.text
                btn_element.click()
                confirm_save(driver=driver)
                pressed_btn_txt = btn_element.text
            else:
                btn_td_elements: [WebElement] = widget.find_elements(By.CLASS_NAME, "Cell_cell_no_padding__hW0I5")
                unpressed_btn_txt = btn_td_elements[i].text
                btn_td_elements[i].click()
                confirm_save(driver=driver)

                pressed_btn_txt = btn_td_elements[i].text

            # capitalize the letters to get expected result
            unpressed_caption: str = field_query.properties['button']['unpressed_caption']
            pressed_caption: str = field_query.properties['button']['pressed_caption']
            assert unpressed_caption.upper() == unpressed_btn_txt
            if widget_name == "portfolio_alert" or widget_name == "strat_alert":
                continue
            assert pressed_caption.upper() == pressed_btn_txt
            i += 1


def test_flux_fld_button_in_dependent_widget(clean_and_set_limits, driver_type, web_project, driver,
                                             schema_dict, pair_strat: Dict):
    # TODO: fluxfldbtn is not used yet in dependent widget
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="button")
    print(result)
    assert not result[0]


def test_flux_fld_orm_no_update_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                          schema_dict, pair_strat: Dict):
    # TODO: only id fields are present in independent widget that's why skip this as of now
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                          flux_property="orm_no_update")
    print(result)
    assert result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="orm_no_update")
    print(result)
    assert not result[0]
    # TODO: only id fields are present in dependent widget that's why skip this as of now

    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="orm_no_update")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="orm_no_update")
    print(result)
    assert not result[0]


def test_flux_fld_comma_separated_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                            schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
    print(result)
    assert result[0]

    # table_layout
    # field_name: str = ""
    # display_type: str = ""
    # for widget_query in result[1]:
    #     widget_name = widget_query.widget_name
    #     widget = driver.find_element(By.ID, widget_name)
    #     edit_btn = widget.find_element(By.NAME, "Edit")
    #     edit_btn.click()
    #     driver.execute_script('arguments[0].scrollIntoView(true)', widget)
    #     time.sleep(Delay.SHORT.value)
    #     for field_query in widget_query.fields:
    #         field_name: str = field_query.field_name
    #         value = validate_property_that_it_contain_val_min_or_val_max_or_none(
    #             schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
    #         xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
    #                                                widget_name=widget_name, field_name=field_name)
    #         enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
    #         if enabled_or_not:
    #             set_table_input_field(widget=widget, xpath=xpath, value=str(value))
    #         else:
    #             continue
    #     widget.find_element(By.NAME, "Save").click()
    #     confirm_save(driver=driver)
    #     common_keys_dict = get_commonkey_item(widget=widget)
    #     input_value = int(common_keys_dict[field_name].replace(",", ""))

    # tree_layout
    xpath: str = ""
    value: str = ""
    xpath_list: List[str] = []
    value_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "order_limits":
            break
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            value = validate_property_that_it_contain_val_min_val_max_or_none(schema_dict=schema_dict,
                                                                              widget_type=WidgetType.INDEPENDENT,
                                                                              flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            xpath_list.append(xpath)
            value_list.append(value)
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)
        for xpath, value in zip(xpath_list, value_list):
            switch_layout(widget=widget, layout=Layout.TREE)
            validate_comma_separated_values(widget=widget, xpath=xpath, value=value)

    # WidgetType: DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="display_type")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="display_type")
    print(result)
    assert result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="display_type")
    print(result)
    assert not result[0]


def test_flux_fld_name_color_in_independent_widget(clean_and_set_limits, driver_type, web_project, driver,
                                                   schema_dict, pair_strat: Dict):
    # TODO: Need help get_fld_name_colour_in_tree line: 1291
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="name_color")
    print(result)
    assert result[0]

    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            name_color: str = field_query.properties['name_color']
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            # TODO: make a method get get name color of table layout
            click_button_with_name(widget=widget, button_name="Edit")
            switch_layout(widget=widget, layout=Layout.TREE)
            get_name_color = get_fld_name_colour_in_tree(widget=widget, xpath=xpath)
            assert name_color == get_name_color

    # tree_layout
    field_name: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        switch_layout(widget=widget, layout=Layout.TREE)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            name_color: str = field_query.properties['name_color']
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            get_name_color = get_fld_name_colour_in_tree(widget=widget, xpath=xpath)
            # assert name_color == Type.ColorType(ColorType.ERROR)
            # assert name_color == get_name_color


def test_flux_fld_progress_bar_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                         schema_dict, pair_strat: Dict):
    # TODO: progress bar property is not used yet in independent widget
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="progress_bar")
    print(result)
    assert result[0]

    # TODO: progress bar property is not used yet in dependent widget
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="progress_bar")
    print(result)
    assert not result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="progress_bar")
    print(result)
    assert not result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="progress_bar")
    print(result)
    assert not result[0]

    # can't automate for table layout bcz it does not contains progressbar
    # tree_layout
    # for_val_min
    # get_val_max: str = ""
    # xpath: str = ""
    # field_name: str = ""
    # for widget_query in result[1]:
    #     widget_name = widget_query.widget_name
    #     strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    #     widget = driver.find_element(By.ID, widget_name)
    #     edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    #     edit_btn.click()
    #     driver.execute_script('arguments[0].scrollIntoView(true)', widget)
    #     time.sleep(Delay.SHORT.value)
    #     switch_layout(widget=widget, layout=Layout.TREE)
    #     for field_query in widget_query.fields:
    #         field_name: str = field_query.field_name
    #         val_min: str = field_query.properties['val_min']
    #         val_max = field_query.properties['val_max']
    #         get_val_max: str = get_str_value(value=val_max, driver=driver, widget_type=WidgetType.DEPENDENT,
    #                                          layout=Layout.TREE)
    #
    #         xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT,
    #                                                widget_name=widget_name, field_name=field_name)
    #         set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=val_min)
    #     strat_collection_widget.find_element(By.NAME, "Save").click()
    #     confirm_save(driver=driver)
    #     progress_level = get_progress_bar_level(widget=widget)
    #     assert progress_level == "100"
    #
    #     # for_val_max
    #     edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    #     edit_btn.click()
    #     set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=get_val_max)
    #     strat_collection_widget.find_element(By.NAME, "Save").click()
    #     confirm_save(driver=driver)
    #     progress_level = get_progress_bar_level(widget=widget)
    #     assert progress_level == "0"


class TestMultiTab:

    def __init__(self):
        self.url: str = "window.open('http://localhost:3020/','_blank');"

    def switch_tab(self, driver, switch_tab_no: int):
        window_handles = driver.window_handles
        driver.switch_to.window(window_handles[switch_tab_no])

    def test_multi_tab_in_independent_widget(self, driver_type, web_project, driver, schema_dict, pair_strat: Dict):
        # no_active_local_changes
        # in_2n_tab
        # table_layout
        driver.execute_script(self.url)
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "order_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        time.sleep(Delay.SHORT.value)

        xpath: str = "max_basis_points"
        value: str = "750"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "order_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        xpath: str = "max_basis_points"
        value: str = "400"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "max_px_deviation"
        value: str = "1"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "min_order_notional"
        value: str = "10000"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "max_basis_points"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

        # active_local_changes
        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "order_limits")
        click_button_with_name(widget=widget, button_name="Edit")

        xpath: str = "max_basis_points"
        value: str = "75"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "order_limits")

        xpath: str = "max_basis_points"
        value: str = "40"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "max_px_deviation"
        value: str = "1"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "min_order_notional"
        value: str = "1200"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "max_basis_points"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

    def test_multi_tab_in_dependent_widget(self, driver_type, web_project, driver, schema_dict, pair_strat: Dict):
        # no_active_local_changes
        # open_2n_tab
        # table_layout
        driver.execute_script(self.url)
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.DEFAULT.value)

        widget = driver.find_element(By.ID, "strat_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)

        xpath: str = "max_open_orders_per_side"
        value: str = "4"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "strat_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)

        xpath: str = "max_open_orders_per_side"
        value: str = "3"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "max_cb_notional"
        value: str = "555"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "max_open_cb_notional"
        value: str = "2"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "cancel_rate.max_cancel_rate"
        value: str = "10"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "market_trade_volume_participation.max_participation_rate"
        value: str = "20"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.DEFAULT.value)

        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "max_open_orders_per_side"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

        # with_active_local_changes
        # table_layout
        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "strat_limits")
        # widget.find_element(By.NAME, "Edit").click()
        xpath: str = "max_open_orders_per_side"
        value: str = "2"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "strat_limits")

        xpath: str = "max_open_orders_per_side"
        value: str = "1"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "max_cb_notional"
        value: str = "100"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "max_open_cb_notional"
        value: str = "150"
        set_table_input_field(widget=widget, xpath=xpath, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)

    def test_multi_tab_in_repeated_fields(self, driver_type, web_project, driver, schema_dict, pair_strat: Dict):
        # no_active_local_changes
        # open_2n_tab
        # tree_layout
        driver.execute_script(self.url)
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "portfolio_limits")
        click_button_with_name(widget=widget, button_name="Edit")

        switch_layout(widget=widget, layout=Layout.TREE)
        widget.find_element(By.XPATH,
                            "//body[1]/div[1]/div[1]/div[2]/div[11]/div[1]/div[1]/div[1]/ul[1]/"
                            "div[6]/div[2]/button[1]").click()
        widget.find_element(By.XPATH, "//div[6]//div[2]//*[name()='svg']").click()
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "255"
        name: str = "available_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "portfolio_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        widget.find_element(By.XPATH,
                            "//body[1]/div[1]/div[1]/div[2]/div[11]/div[1]/div[1]/div[1]/ul[1]/div[6]/div[2]"
                            "/button[1]").click()
        widget.find_element(By.XPATH, "//div[6]//div[2]//*[name()='svg']").click()
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "25"
        name: str = "available_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].allocated_size"
        value: str = "5"
        name: str = "allocated_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].consumed_size"
        value: str = "7"
        name: str = "consumed_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "max_open_baskets"
        value: str = "51"
        name: str = "max_open_baskets"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].security.sec_id"
        value: str = "EQT_Sec_1"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_autocomplete_field(widget=widget, xpath=xpath, name="sec_id", search_type=SearchType.NAME, value=value)
            # set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].type"
        input_xpath = f"//div[@data-xpath='{xpath}']"
        widget.find_element(By.XPATH, input_xpath).click()
        value: str = "PTH"
        option = driver.find_element(By.XPATH, f"//li[text()='{value}']")
        option.click()

        # set_autocomplete_field(widget=widget, xpath=xpath, name="type", search_type=SearchType.NAME, value=value)

        # set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "eligible_brokers[0].broker"
        value: str = "AAPL"
        name: str = "broker"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        # with_active_local_changes
        # in_1st_tab
        # tree_layout
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "portfolio_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "255"
        name: str = "available_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

        widget = driver.find_element(By.ID, "portfolio_limits")
        # widget.find_element(By.NAME, "Edit").click()
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "25"
        name: str = "available_size"
        switch_layout(widget=widget, layout=Layout.TREE)
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].allocated_size"
        value: str = "5"
        name: str = "allocated_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].consumed_size"
        value: str = "7"
        name: str = "consumed_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)


def test_flux_fld_default_widget(clean_and_set_limits, web_project, driver_type, schema_dict, driver):

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="default")
    print(result)
    # order_limits_obj = OrderLimitsBaseModel(id=55, max_px_deviation=44)
    # strat_manager_service_native_web_client.delete_pair_strat_client(pair_strat_id=1)
    strat_manager_service_native_web_client.delete_order_limits_client(order_limits_id=1)
    strat_manager_service_native_web_client.delete_portfolio_limits_client(portfolio_limits_id=1)
    strat_manager_service_native_web_client.delete_portfolio_status_client(portfolio_status_id=1)

    driver.refresh()
    time.sleep(Delay.SHORT.value)

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)

        if (widget_name == "portfolio_alert" or widget_name == "strat_limits" or widget_name == "strat_status" or
                widget_name == "strat_alert"):
            click_button_with_name(widget=widget, button_name="Edit")
        else:
            click_button_with_name(widget=widget, button_name="Create")

        time.sleep(Delay.SHORT.value)

        switch_layout(widget, Layout.TABLE)
        time.sleep(Delay.SHORT.value)

        for field_query in widget_query.fields:
            flux_fld_default_widget(schema_dict=schema_dict, widget=widget,
                                    widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                    layout=Layout.TABLE, field_query=field_query)

    # WidgetType: dependent
    driver.refresh()
    time.sleep(Delay.SHORT.value)

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="default")
    print(result)
    # order_limits_obj = OrderLimitsBaseModel(id=55, max_px_deviation=44)
    strat_manager_service_native_web_client.delete_order_limits_client(order_limits_id=1)
    strat_manager_service_native_web_client.delete_portfolio_limits_client(portfolio_limits_id=1)
    strat_manager_service_native_web_client.delete_portfolio_status_client(portfolio_status_id=1)
    driver.refresh()
    time.sleep(Delay.SHORT.value)

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == "pair_strat_params":
            widget = driver.find_element(By.ID, "strat_collection")
            click_button_with_name(widget=widget, button_name="Create")
            time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, widget_name)
        widget.find_element(By.XPATH, "//button[@aria-label='Show']").click()
        widget.find_element(By.XPATH, "//span[normalize-space()='Show hidden fields']").click()
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)

        for field_query in widget_query.fields:
            flux_fld_default_widget(schema_dict=schema_dict, widget=widget,
                                    widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                    layout=Layout.TREE, field_query=field_query)

    # WidgetType: REPEATED_INDEPENDENT
    driver.refresh()
    time.sleep(Delay.DEFAULT.value)
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="default")
    print(result)
    assert result[0]

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        time.sleep(Delay.SHORT.value)
        scroll_into_view(driver=driver, element=widget)
        time.sleep(Delay.SHORT.value)
        click_button_with_name(widget=widget, button_name="Show")
        print(widget_query.widget_name)

        for field_query in widget_query.fields:
            flux_fld_default_widget(schema_dict=schema_dict, widget=widget,
                                    widget_type=WidgetType.REPEATED_INDEPENDENT, widget_name=widget_name,
                                    layout=Layout.TABLE, field_query=field_query)

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="default")
    print(result)

    assert not result[0]


def test_flux_fld_ui_update_only(clean_and_set_limits, web_project, driver_type: DriverType,
                                 schema_dict: Dict, driver: WebDriver):

    # WidgetType: INDEPENDENT
    # Note: only enabled in dismiss field
    result = get_widgets_by_flux_property(schema_dict, WidgetType.INDEPENDENT, "ui_update_only")
    print(result)
    assert result[0]

    # WidgetType: DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, WidgetType.DEPENDENT, "ui_update_only")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, WidgetType.REPEATED_INDEPENDENT, "ui_update_only")
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, WidgetType.REPEATED_INDEPENDENT, "ui_update_only")
    print(result)
    assert not result[0]


def test_flux_fld_ui_place_holder_in_widget(clean_and_set_limits, driver_type: DriverType,
                                            schema_dict: Dict, driver: WebDriver):

    driver.maximize_window()
    driver.get(get_web_project_url())
    time.sleep(Delay.SHORT.value)

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.INDEPENDENT,
                                          flux_property="ui_placeholder")
    print(result)

    strat_manager_service_native_web_client.delete_portfolio_limits_client(portfolio_limits_id=1)
    # strat_manager_service_native_web_client.delete_stra
    for widget_query in result[1]:
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Create")
        switch_layout(widget=widget, layout=Layout.TREE)
        time.sleep(Delay.SHORT.value)
        if widget_name == "strat_status":
            widget.find_element(By.XPATH, '//*[@id="strat_status"]/div/div/div/ul/div[27]/div[2]/button').click()
            # // *[ @ id = "pair_strat_params"] / div / div / div / ul / ul / div[2] / div[2] / button
            widget.find_element(By.XPATH, '//*[@id="strat_status"]/div/div/div/ul/div[27]/div[2]').click()
            # click_on_button(widget=widget)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            placeholder: str = get_placeholder_from_element(widget=widget, id=field_name)
            # // *[ @ id = "strat_status"] / div / div / div / ul / div[27] / div[2] / button
            default_placeholder: str = field_query.properties['ui_placeholder']

            assert default_placeholder == placeholder

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.DEPENDENT,
                                          flux_property="ui_placeholder")
    print(result)

    for widget_query in result[1]:
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        if widget_name == "pair_strat_params":
            strat_collection_widget = driver.find_element(By.ID, "strat_collection")
            click_button_with_name(widget=strat_collection_widget, button_name="Create")
            scroll_into_view(driver=driver, element=widget)
            switch_layout(widget=widget, layout=Layout.TREE)
            time.sleep(Delay.SHORT.value)
            widget.find_element(By.XPATH, '//*[@id="pair_strat_params"]/div/div/div/ul/ul/div[2]/div[2]/button').click()
            widget.find_element(By.XPATH, '//*[@id="pair_strat_params"]/div/div/div/ul/ul/div[2]/div[2]').click()
            # click_on_button(widget=widget)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            placeholder: str = get_placeholder_from_element(widget=widget, id=field_name)
            # // *[ @ id = "strat_status"] / div / div / div / ul / div[27] / div[2] / button
            default_placeholder: str = field_query.properties['ui_placeholder']

            assert default_placeholder == placeholder

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="ui_placeholder")
    print(result)


def test_flux_fld_sequence_number_in_widget(clean_and_set_limits, web_project, driver_type: DriverType,
                                            schema_dict: Dict, driver: WebDriver):

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.INDEPENDENT,
                                          flux_property="sequence_number")
    assert result[0]

    flux_fld_sequence_number_in_widget(result[1], driver, WidgetType.INDEPENDENT)

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.DEPENDENT,
                                          flux_property="sequence_number")
    print(result)
    assert result[0]
    flux_fld_sequence_number_in_widget(result[1], driver, WidgetType.DEPENDENT)

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property="sequence_number")
    print(result)
    assert result[0]
    flux_fld_sequence_number_in_widget(result[1], driver, WidgetType.REPEATED_INDEPENDENT)

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property="sequence_number")
    print(result)
    assert not result[0]
