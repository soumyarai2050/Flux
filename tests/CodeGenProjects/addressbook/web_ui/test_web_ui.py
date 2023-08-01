import random
import time

import pytest

from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC  # noqa

from tests.CodeGenProjects.addressbook.web_ui.utility_test_functions import *

# to parameterize all tests. to add support for other browsers, add the DriverType here
pytestmark = pytest.mark.parametrize("driver_type", [DriverType.CHROME])


def test_create_pair_strat(driver_type, web_project):
    pass


def test_update_pair_strat_n_create_n_activate_strat_limits_using_tree_view(driver_type, web_project, driver,
                                                                          pair_strat_edit: Dict,
                                                                          pair_strat: Dict, strat_limits: Dict):

    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()
    time.sleep(Delay.SHORT.value)

    # pair_strat_params.common_premium
    xpath: str = "pair_strat_params.common_premium"
    value = pair_strat_edit["pair_strat_params"]["common_premium"]
    name: str = "common_premium"
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value)

    # pair_strat_params.hedge_ratio
    xpath: str = "pair_strat_params.hedge_ratio"
    value = pair_strat_edit["pair_strat_params"]["hedge_ratio"]
    name: str = "hedge_ratio"
    set_tree_input_field(widget=pair_strat_params_widget, xpath=xpath, name=name, value=value)

    # scroll into view
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_limits_widget)
    time.sleep(Delay.SHORT.value)

    switch_layout(widget=strat_limits_widget, layout=Layout.TREE)

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
    time.sleep(Delay.SHORT.value)
    confirm_save(driver=driver)
    edit_btn.click()
    switch_layout(widget=strat_limits_widget, layout=Layout.TREE)
    create_strat_limits_using_tree_view(driver=driver, strat_limits=strat_limits, layout=Layout.TREE)

    activate_strat(driver=driver)

    # validate_strat_limits
    switch_layout(widget=strat_limits_widget, layout=Layout.TREE)
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)
    driver.quit()


def test_update_strat_n_activate_using_table_view(driver_type, web_project, driver, pair_strat: Dict,
                                                  strat_limits: Dict):

    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")

    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()
    time.sleep(Delay.SHORT.value)

    # max_open_per_orders_side
    xpath = "strat_limits.max_open_orders_per_side"
    value = strat_limits["max_open_orders_per_side"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cb_notional
    xpath = "strat_limits.max_cb_notional"
    value = strat_limits["max_cb_notional"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_open_cb_notional
    xpath = "strat_limits.max_open_cb_notional"
    value = strat_limits["max_open_cb_notional"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_net_filled_notional
    xpath = "strat_limits.max_net_filled_notional"
    value = strat_limits["max_net_filled_notional"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_concentration
    xpath = "strat_limits.max_concentration"
    value = strat_limits["max_concentration"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # limit_up_down_volume_participation_rate
    xpath = "strat_limits.limit_up_down_volume_participation_rate"
    value = strat_limits["limit_up_down_volume_participation_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_cancel_rate
    xpath = "strat_limits.cancel_rate.max_cancel_rate"
    value = strat_limits["cancel_rate"]["max_cancel_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "strat_limits.cancel_rate.applicable_period_seconds"
    value = strat_limits["cancel_rate"]["applicable_period_seconds"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # waived_min_orders
    xpath = "strat_limits.cancel_rate.waived_min_orders"
    value = strat_limits["cancel_rate"]["waived_min_orders"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_participation_rate
    xpath = "strat_limits.market_trade_volume_participation.max_participation_rate"
    value = strat_limits["market_trade_volume_participation"]["max_participation_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # applicable_period_seconds
    xpath = "strat_limits.market_trade_volume_participation.applicable_period_seconds"
    value = strat_limits["market_trade_volume_participation"]["applicable_period_seconds"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # participation_rate
    xpath = "strat_limits.market_depth.participation_rate"
    value = strat_limits["market_depth"]["participation_rate"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # depth_levels
    xpath = "strat_limits.market_depth.depth_levels"
    value = strat_limits["market_depth"]["depth_levels"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # max_residual
    xpath = "strat_limits.residual_restriction.max_residual"
    value = strat_limits["residual_restriction"]["max_residual"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    # residual_mark_seconds
    xpath = "strat_limits.residual_restriction.residual_mark_seconds"
    value = strat_limits["residual_restriction"]["residual_mark_seconds"]
    enabled_or_not = validate_table_cell_enabled_or_not(widget=strat_collection_widget, xpath=xpath)
    if enabled_or_not:
        set_table_input_field(widget=strat_limits_widget, xpath=xpath, value=value)

    activate_strat(driver=driver)
    edit_btn.click()
    # validating the values
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TABLE)


def test_field_hide_n_show_in_common_key(driver_type, web_project, driver, pair_strat: Dict):

    pair_strat_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_widget, layout=Layout.TABLE)

    common_keys = get_common_keys(widget=pair_strat_widget)
    replaced_list_of_common_keys = get_replaced_common_keys(common_keys_list=common_keys)
    # select a random value
    inner_text: str = random.choice(replaced_list_of_common_keys)

    # searching the random key in setting and unselecting checkbox
    pair_strat_widget.find_element(By.NAME, "Settings").click()
    select_n_unselect_checkbox(widget=pair_strat_widget, inner_text=inner_text)

    # validating that unselected key is not visible on table view
    common_keys: List[str] = get_common_keys(widget=pair_strat_widget)
    replaced_list_of_common_keys = get_replaced_common_keys(common_keys_list=common_keys)
    assert inner_text not in replaced_list_of_common_keys, f"{inner_text} field is visible in common keys, expected to be hidden"

    #  searching the random key in setting and selecting checkbox
    pair_strat_widget.find_element(By.NAME, "Settings").click()
    select_n_unselect_checkbox(widget=pair_strat_widget, inner_text=inner_text)

    # validating that selected checkbox is visible on table view
    common_keys = get_common_keys(widget=pair_strat_widget)
    replaced_list_of_common_keys = get_replaced_common_keys(common_keys_list=common_keys)
    assert inner_text in replaced_list_of_common_keys, f"{inner_text} field is not visible in common keys, expected to be visible"


def test_hide_n_show_in_table_view(driver_type, web_project, driver, pair_strat: Dict):

    activate_strat(driver=driver)

    symbol_side_snapshot_widget = driver.find_element(By.ID, "symbol_side_snapshot")
    driver.execute_script('arguments[0].scrollIntoView(true)', symbol_side_snapshot_widget)

    # selecting random table text from table view
    table_headers = get_table_headers(widget=symbol_side_snapshot_widget)
    inner_text = random.choice(table_headers)

    #  searching the selected random table text in setting and unselecting checkbox
    symbol_side_snapshot_widget.find_element(By.NAME, "Settings").click()
    select_n_unselect_checkbox(widget=symbol_side_snapshot_widget, inner_text=inner_text)

    # validating that unselected text is not visible on table view
    table_headers: List[str] = get_table_headers(widget=symbol_side_snapshot_widget)
    assert inner_text not in table_headers

    # searching the random table text in setting and selecting checkbox
    symbol_side_snapshot_widget.find_element(By.NAME, "Settings").click()
    select_n_unselect_checkbox(widget=symbol_side_snapshot_widget, inner_text=inner_text,)

    # validating that selected check is visible on table view
    table_headers: List[str] = get_table_headers(widget=symbol_side_snapshot_widget)
    assert inner_text in table_headers


def test_nested_pair_strat_n_strats_limits(driver_type, web_project, driver, pair_strat: Dict,
                                           pair_strat_edit: Dict, strat_limits: Dict):

    strat_limits_widget = driver.find_element(By.ID, "strat_limits")
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")
    switch_layout(widget=pair_strat_params_widget, layout=Layout.TABLE)
    edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
    edit_btn.click()


    pair_strat_td_elements = pair_strat_params_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    # enabled_or_not = validate_table_cell_enabled_or_not
    # if enabled_or_not:
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

    strat_limits_td_elements = strat_limits_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    actions.double_click(strat_limits_td_elements[0]).perform()

    create_strat_limits_using_tree_view(driver=driver, strat_limits=strat_limits, layout=Layout.NESTED)
    save_nested_strat(driver=driver)

    # perform_double_click
    actions.double_click(strat_limits_td_elements[0]).perform()
    validate_strat_limits(widget=strat_limits_widget, strat_limits=strat_limits, layout=Layout.TREE)


def test_widget_type(driver_type, schema_dict: Dict[str, any]):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="default")
    print(result)
    # for widget_query in result[1]:
    #     widget_name = widget_query.widget_name
    #     for field_query in widget_query.fields:
    #         field_name: str = field_query.field_name
    #         field_type =  field_query.properties["type"]
    #         # number_format_txt: str = field_query.properties['number_format']
    #         xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
    #                                           field_name=field_name)
    #         print(xpath)






def test_flux_fld_val_max_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, WidgetType.INDEPENDENT, "val_max")
    assert result[0]

    # table_layout
    # for_valid_scenario_val_max
    field_name_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        widget.find_element(By.NAME, "Edit").click()
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                               field_name=field_name)
            field_name_list.append(field_name)
            val_max: int = int(field_query.properties['val_max'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TABLE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_max == get_field_value:
                val_max = val_max - 1
            enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_max))
            else:
                continue
        widget.find_element(By.NAME, "Save").click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        get_object_keys_txt_list.pop()
        for field_name_txt in field_name_list:
            assert field_name_txt in get_object_keys_txt_list
        confirm_save(driver=driver)
        field_name_list.clear()

    # order_limits_n_portfolio_limits_tree_layout_val_max_for_valid_scenario
    field_name_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        widget.find_element(By.NAME, "Edit").click()

        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            field_name_list.append(field_name)
            val_max: int = int(field_query.properties['val_max'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_max == get_field_value:
                val_max = val_max - 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))

        widget.find_element(By.NAME, "Save").click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for field_name_txt in field_name_list:
            assert field_name_txt in get_object_keys_txt_list
        confirm_save(driver=driver)
        field_name_list.clear()

    # order_limits_n_portfolio_limits_table_layout_above_val_max_for_invalid_scenario
    field_name_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        switch_layout(widget=widget, layout=Layout.TABLE)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        for field_query in widget_query.fields:
            field_name:str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            field_name_list.append(field_name)
            val_max: int = int(field_query.properties['val_max']) + 1
            enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_max))
            else:
                continue
        widget.find_element(By.NAME, "Save").click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for field_name_txt in field_name_list:
            assert field_name_txt in get_object_keys_txt_list
        discard_changes(widget=widget)
        field_name_list.clear()


    # order_limits_n_portfolio_limits_tree_layout_above_val_max_for_invalid_scenario
    field_name_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            field_name_list.append(field_name)
            val_max: int = int(field_query.properties['val_max']) + 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))
        widget.find_element(By.NAME, "Save").click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for field_name_txt in field_name_list:
            assert field_name_txt in get_object_keys_txt_list
        discard_changes(widget=widget)
        field_name_list.clear()


def test_flux_fld_val_max_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, WidgetType.DEPENDENT, "val_max")
    print(result)
    assert result[0]

    # tree_layout
    xpath: str = ''
    xpath_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        strat_collection_widget = driver.find_element(By.ID, 'strat_collection')
        edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            xpath_list.append(field_name)
            # TODO: val_max is returning xpath instead of value
            # val_max_is_empty_str
            val_max: int = int(field_query.properties['val_max'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_max == get_field_value:
                val_max = val_max - 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))
        save_btn = strat_collection_widget.find_element(By.NAME, "Save")
        save_btn.click()
        show_hidden_field_in_review_changes_popup(driver=driver)
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for xpath_text in xpath_list:
            assert xpath_text in get_object_keys_txt_list
            discard_changes(widget=widget)
            xpath_list.clear()


    # for_valid_scenario
    # tree_layout
    xpath_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            xpath_list.append(field_name)
            val_max = int(field_query.properties['val_max'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TABLE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_max == get_field_value:
                val_max = val_max - 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_max))
        save_btn = widget.find_element(By.NAME, "Save")
        save_btn.click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for xpath_text in xpath_list:
            assert xpath_text in get_object_keys_txt_list
        discard_changes(widget=widget)
        xpath_list.clear()


    # for_invalid_scenario_above_val_max
    # table_layout
    xpath_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        switch_layout(widget=widget, layout=Layout.TABLE)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            xpath_list.append(field_name)
            val_max: str = field_query.properties['val_max'] + '1'
            enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_max))
            else:
                continue
        save_btn = widget.find_element(By.NAME, "Save")
        save_btn.click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for xpath_text in xpath_list:
            assert xpath_text in get_object_keys_txt_list
        discard_changes(widget=widget)
        xpath_list.clear()

    # above_val_max_for_invalid_scenario
    # tree_layout
    xpath_list: List[str] = []
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            xpath_list.append(field_name)
            val_max: str = field_query.properties['val_max'] + '1'
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=val_max)
        save_btn = widget.find_element(By.NAME, "Save")
        save_btn.click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        for xpath_text in xpath_list:
            assert xpath_text in get_object_keys_txt_list
        discard_changes(widget=widget)
        xpath_list.clear()



def test_flux_fld_val_min_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="val_min")
    print(result)
    assert result[0]

    # order_limits_n_portfolio_limits_table_layout_val_min_for_valid_scenario
    field_name: str = ''
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
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
            enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_min))
            else:
                continue
            widget.find_element(By.NAME, "Save").click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in get_object_keys_txt_list
        discard_changes(widget=widget)

    # order_limits_n_portfolio_limits_tree_layout_val_min_for_valid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min'])
            get_field_value: str = get_default_field_value(widget=widget, layout=Layout.TREE, xpath=xpath)
            if get_field_value:
                get_field_value = get_field_value.replace(',', '')
                get_field_value: int = int(get_field_value)
            if val_min == get_field_value:
                val_min = val_min - 1
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_min))

        save_btn = widget.find_element(By.NAME, "Save")
        save_btn.click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in get_object_keys_txt_list
        discard_changes(widget=widget)


    # order_limits_n_portfolio_limits_table_layout_below_val_min_for_invalid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min']) - 5

            enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(val_min))
            else:
                continue
        save_btn = widget.find_element(By.NAME, "Save")
        save_btn.click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in get_object_keys_txt_list
        discard_changes(widget=widget)


    # order_limits_n_portfolio_limits_tree_layout_below_val_min_for_invalid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                              field_name=field_name)
            val_min = int(field_query.properties['val_min']) - 5
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(val_min))
        save_btn = widget.find_element(By.NAME, "Save")
        save_btn.click()
        get_object_keys_txt_list = get_object_keys_from_dialog_box(widget=widget)
        assert field_name in get_object_keys_txt_list
        discard_changes(widget=widget)



def test_flux_fld_val_min_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    # TODO:  val min property is not used in dependent widget yet
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="val_min")
    print(result)
    assert result[0]



def test_flux_fld_help_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="help")
    print(result)
    assert result[0]

    # order_limits_n_portfolio_limits_table_layout_help_for_valid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)

        for field_query in widget_query.fields:
            # scroll into view
            driver.execute_script('arguments[0].scrollIntoView(true)', widget)
            time.sleep(Delay.SHORT.value)
            help_txt: str = field_query.properties['help']
            widget.find_element(By.NAME, "Settings").click()
            setting_dropdown = widget.find_element(By.XPATH, "//ul[@role='listbox']")
            time.sleep(Delay.SHORT.value)
            contains_element = setting_dropdown.find_element(By.XPATH, f"//button[@aria-label='{help_txt}']")
            actions = ActionChains(driver)
            actions.move_to_element(contains_element).perform()
            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
            hovered_element_text = tooltip_element.text
            assert help_txt == hovered_element_text
            contains_element.click()
            time.sleep(Delay.DEFAULT.value)

    # order_limits_n_portfolio_limits_tree_layout_help_for_valid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        for field_query in widget_query.fields:
            driver.execute_script('arguments[0].scrollIntoView(true)', widget)
            switch_layout(widget=widget, layout=Layout.TREE)
            time.sleep(Delay.SHORT.value)
            help_txt: str = field_query.properties['help']
            contains_element = widget.find_element(By.XPATH, f"//button[@aria-label='{help_txt}']")
            actions = ActionChains(driver)
            actions.move_to_element(contains_element).perform()
            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
            hovered_element_text = tooltip_element.text
            assert hovered_element_text == help_txt
            contains_element.click()
            time.sleep(Delay.DEFAULT.value)




def test_flux_fld_help_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="help")
    print(result)
    assert result[0]

    # order_limits_n_portfolio_limits_table_layout_help_for_valid_scenario
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)

        for field_query in widget_query.fields:
            # scroll into view
            driver.execute_script('arguments[0].scrollIntoView(true)', widget)
            time.sleep(Delay.SHORT.value)
            help_txt: str = field_query.properties['help']
            widget.find_element(By.NAME, "Settings").click()
            setting_dropdown = widget.find_element(By.XPATH, "//ul[@role='listbox']")
            time.sleep(Delay.SHORT.value)
            contains_element = setting_dropdown.find_element(By.XPATH, f"//button[@aria-label='{help_txt}']")
            actions = ActionChains(driver)
            actions.move_to_element(contains_element).perform()
            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
            hovered_element_text = tooltip_element.text
            assert help_txt == hovered_element_text
            contains_element.click()
            time.sleep(Delay.DEFAULT.value)


    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        switch_layout(widget=widget, layout=Layout.TREE)
        show_hidden_fields_in_tree_layout(widget=widget, driver=driver)
        for field_query in widget_query.fields:
            time.sleep(Delay.SHORT.value)
            help_txt: str = field_query.properties['help']
            contains_element = widget.find_element(By.XPATH, f"//button[@aria-label='{help_txt}']")
            actions = ActionChains(driver)
            actions.move_to_element(contains_element).perform()
            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip-popper']")
            hovered_element_text = tooltip_element.text
            assert hovered_element_text == help_txt
            contains_element.click()
            time.sleep(Delay.DEFAULT.value)
            # tooltip not getting closed that's why switching layout
            switch_layout(widget=widget, layout=Layout.TREE)





def test_flux_fld_display_type_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
    print(result)
    assert result[0]

    # display_type_order_limits_portfolio_limits_portfolio_status
    # table_layout
    field_name: str = ""
    display_type: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            display_type: str = type(field_query.properties['display_type'])
            value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            enabled_or_not: bool= validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(value))
            else:
                continue
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        common_keys_dict = get_commonkey_item(widget=widget)
        input_value = int(common_keys_dict[field_name].replace(",", ""))
        assert type(input_value) == int


    # tree_layout
    field_name: str = ""
    display_type: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # order_notional_field_is_a_repetated_field_that's_why_continue
            if field_name == "order_notional" and widget_name == "portfolio_status":
                continue
            display_type: str = field_query.properties['display_type']
            value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict,widget_type=WidgetType.INDEPENDENT,
                                                                                 flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(value))
        widget.find_element(By.NAME, "Save").click()
        switch_layout(widget=widget, layout=Layout.TABLE)
        common_keys_dict = get_commonkey_item(widget=widget)
        input_value = int(common_keys_dict[field_name].replace(",", ""))
        assert type(input_value) == int


def test_flux_fld_display_type_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="display_type")
    print(result)
    assert result[0]
    
    # table_layout
    field_name: str = ""
    display_type: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            display_type: str = field_query.properties['display_type']
            value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict, widget_type=WidgetType.DEPENDENT,
                                                                                 flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(value))
            else:
                continue
        strat_collection_widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        common_keys_item: dict = get_commonkey_item(widget=widget)
        input_value = int(common_keys_item[field_name].replace(",", ""))
        assert type(input_value) == int

    # tree_layout
    field_name: str = ""
    display_type: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            # order_notional_field_is_a_repetated_field_that's_why_continue
            if field_name == "order_notional" and widget_name == "portfolio_status":
                continue
            display_type: str = field_query.properties['display_type']
            value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict,widget_type=WidgetType.INDEPENDENT,
                                                                                 flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=str(value))
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        switch_layout(widget=widget, layout=Layout.TABLE)
        common_keys_item: dict = get_commonkey_item(widget=widget)
        # input_value = int(common_keys_item[field_name].replace(",", ""))
        # assert type(input_value) == int


def test_flux_fld_number_format_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="number_format")
    print(result)
    assert result[0]

    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        widget.find_element(By.NAME, "Edit").click()
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            number_format_txt: str = field_query.properties['number_format']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            # TODO: scroll horizontally
            get_number_format = get_flux_flx_number_format_in_table_layout(widget=widget, xpath=xpath)
            assert number_format_txt == get_number_format


    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            number_format_txt: str = field_query.properties['number_format']
            get_number_format = get_flux_flx_number_format_in_tree_layout(widget=widget)
            assert number_format_txt == get_number_format

def test_flux_fld_number_format_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="number_format")
    print(result)
    assert result[0]

    # table_layout
    strat_collection_widget = driver.find_element(By.ID, "strat_collection")
    strat_collection_widget.find_element(By.NAME, "Edit").click()
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        if widget_name == "pair_strat_params":
            switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            number_format_txt: str = field_query.properties['number_format']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            get_number_format = get_flux_flx_number_format_in_table_layout(widget=widget, xpath=xpath)
            assert number_format_txt == get_number_format


def test_flux_flx_display_zero_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    # TODO: display_zero_property_has_not_used_yet_in_independent_widget
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="display_zero")
    print(result)
    assert result[0]


def test_flux_flx_display_zero_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="display_zero")
    print(result)
    assert result[0]
    # can write only in table layout bcz tree layout contains progress bar
    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        strat_collection_widget.find_element(By.NAME, "Edit").click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            value: str = "0"
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=value)
            strat_collection_widget.find_element(By.NAME, "Save").click()
            confirm_save(driver=driver)
            switch_layout(widget=widget, layout=Layout.TABLE)
            get_common_key_dict = get_commonkey_item(widget=widget)
            field_name = field_name.replace("_", " ")
            assert value == get_common_key_dict[field_name]


def test_flux_fld_server_populate_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,flux_property="server_populate")
    print(result)
    assert result[0]
    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        show_hidden_fields_btn = widget.find_element(By.NAME, "Show")
        show_hidden_fields_btn.click()
        widget.find_element(By.NAME, "Edit").click()
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            assert enabled_or_not == False


    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        show_hidden_fields_in_tree_layout(widget=widget, driver=driver)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            field_names: List[str] = count_fields_in_tree(widget=widget)
            # validate that server populate field name does not present in tree layout after clicking on edit btn
            assert field_name not in field_names



def test_flux_fld_server_populate_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT,flux_property="server_populate")
    print(result)
    assert result[0]

    # table_layout
    # TODO: exch_id field is not present in common_key in pair strat params widget
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TABLE)
        show_hidden_fields_btn = widget.find_element(By.NAME, "Show")
        show_hidden_fields_btn.click()
        if widget_name == "pair_strat_params":
            strat_collection_widget.find_element(By.NAME, "Edit").click()
        else:
            continue
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name == "exch_id":
                continue
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            assert enabled_or_not == False


    # tree_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        show_hidden_fields_in_tree_layout(widget=widget,driver=driver)
       # clicked on edit btn in table layout already so server populate field will disappear from tree layout
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name == "id":
                continue
            field_names: List[str] = count_fields_in_tree(widget=widget)
            # validate that server populate field name does not present in tree layout after clicking on edit btn
            assert field_name not in field_names
            # TODO: id is not present in strat status widget

def test_flux_fld_button_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,flux_property="button")
    print(result)
    assert result[0]

    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            unpressed_caption: str = field_query.properties['button']['unpressed_caption']
            pressed_caption: str = field_query.properties['button']['pressed_caption']
            xpath = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                              field_name=field_name)
            unpressed_button_text = get_button_text(widget=widget)
            # capitalize the letters to get expected result
            # unpressed_caption = unpressed_caption.upper()
            # assert unpressed_caption == unpressed_button_text
            click_on_button(widget=widget, xpath=xpath)
            confirm_save(driver=driver)
            pressed_button_text = get_button_text(widget=widget)
            # capitalize the letters to get expected result
            pressed_caption = pressed_caption.upper()
            assert pressed_button_text == pressed_caption

def test_flux_fld_button_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT,flux_property="button")
    print(result)
    assert result[0]

def test_flux_fld_orm_no_update_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    # TODO: only id fields are present in independent widget that's why skip this as of now
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,flux_property="name_color")
    print(result)
    assert result[0]


def test_flux_fld_orm_no_update_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT,flux_property="orm_no_update")
    print(result)
    assert result[0]
    # TODO: only id fields are present in dependent widget that's why skip this as of now
    # table_layout
    # field_name: str = ""
    # for widget_query in result[1]:
    #     widget_name = widget_query.widget_name
    #     widget = driver.find_element(By.ID, widget_name)
    #     driver.execute_script('arguments[0].scrollIntoView(true)', widget)
    #     time.sleep(Delay.SHORT.value)
    #     show_hidden_fields_btn = widget.find_element(By.NAME, "Show")
    #     show_hidden_fields_btn.click()
    #     edit_btn = widget.find_element(By.NAME, "Edit")
    #     edit_btn.click()
    #     for field_query in widget_query.fields:
    #         field_name: str = field_query.field_name
    #         value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict,widget_type=WidgetType.DEPENDENT,
    #                                                                              flux_property="orm_no_update")
    #         xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT,widget_name=widget_name,
    #                                                field_name=field_name)
    #         enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
    #         if enabled_or_not:
    #             set_table_input_field(widget=widget, xpath=xpath, value=str(value))




def test_flux_fld_comma_separated_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,flux_property="display_type")
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
    #         value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict,widget_type=WidgetType.INDEPENDENT,
    #                                                                              flux_property="display_type")
    #         xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
    #                                                field_name=field_name)
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
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        edit_btn = widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            value: str = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict,widget_type=WidgetType.INDEPENDENT,
                                                                                 flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            xpath_list.append(xpath)
            value_list.append(value)
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=value)
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        for xpath, value in zip(xpath_list, value_list):
            validate_comma_separated_values(widget=widget, xpath=xpath, value=value)


def test_flux_fld_comma_separated_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT,flux_property="display_type")
    print(result)
    assert result[0]

    # table_layout
    field_name: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            value = validate_property_that_it_contain_val_min_or_val_max_or_none(schema_dict,widget_type=WidgetType.DEPENDENT,
                                                                                 flux_property="display_type")
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            enabled_or_not: bool = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
            if enabled_or_not:
                set_table_input_field(widget=widget, xpath=xpath, value=str(value))
            else:
                continue
        strat_collection_widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        # TODO: add assert



def test_flux_fld_name_color_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT,flux_property="name_color")
    print(result)
    assert result[0]

    # table_layout
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            name_color: str = field_query.properties['name_color']
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            # TODO: make a method get get name color of table layout
            # get_name_color = get_fld_name_colour_in_tree(widget=widget, xpath=xpath)
            # assert name_color == get_name_color


    # tree_layout
    field_name: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        switch_layout(widget=widget, layout=Layout.TREE)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            name_color: str = field_query.properties['name_color']
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            get_name_color = get_fld_name_colour_in_tree(widget=widget, xpath=xpath)
            # assert name_color == Type.ColorType(ColorType.ERROR)
            # assert name_color == get_name_color

def test_flux_fld_progress_bar_in_independent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    # TODO: progress bar property is noT used yet in independent widget
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="progress_bar")
    print(result)
    assert result[0]


def test_flux_fld_progress_bar_in_dependent_widget(driver_type, web_project, driver, schema_dict, pair_strat: Dict):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property="progress_bar")
    print(result)
    assert result[0]
    # can't automate for table layout bcz it does not contains progressbar
    # tree_layout
    # for_val_min
    get_val_max: str = ""
    xpath: str = ""
    field_name: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        strat_collection_widget = driver.find_element(By.ID, "strat_collection")
        widget = driver.find_element(By.ID, widget_name)
        edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            val_min: str = field_query.properties['val_min']
            val_max = field_query.properties['val_max']
            get_val_max: str = get_str_value(value=val_max, driver=driver, widget_type=WidgetType.DEPENDENT, layout=Layout.TREE)

            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.DEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=val_min)
        strat_collection_widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        progress_level = get_progress_bar_level(widget=widget)
        assert progress_level == "100"

        # for_val_max
        edit_btn = strat_collection_widget.find_element(By.NAME, "Edit")
        edit_btn.click()
        set_tree_input_field(widget=widget, xpath=xpath, name=field_name, value=get_val_max)
        strat_collection_widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)
        progress_level = get_progress_bar_level(widget=widget)
        assert progress_level == "0"




class TestMultiTab:

    # def __init__(self):
    #     self.host: str = "localhost"
    #     self.port: int = 3020

    def switch_tab(self, driver, switch_tab_no: int):
        window_handles = driver.window_handles
        driver.switch_to.window(window_handles[switch_tab_no])


    def test_multi_tab_in_independent_widget(self, driver_type, web_project, driver, schema_dict, pair_strat: Dict):
        # no_active_local_changes
        # in_2n_tab
        # table_layout
        driver.execute_script("window.open('http://localhost:3020/','_blank');")
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "order_limits")
        widget.find_element(By.NAME, "Edit").click()
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
        widget.find_element(By.NAME, "Edit").click()
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
        widget.find_element(By.NAME, "Save").click()
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
        widget.find_element(By.NAME, "Edit").click()

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
        widget.find_element(By.NAME, "Save").click()
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
        driver.execute_script("window.open('http://localhost:3020/','_blank');")
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.DEFAULT.value)

        widget = driver.find_element(By.ID, "strat_collection")
        widget.find_element(By.NAME, "Edit").click()
        xpath: str = "strat_limits.max_open_orders_per_side"
        value: str = "4"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "strat_collection")
        widget.find_element(By.NAME, "Edit").click()
        xpath: str = "strat_limits.max_open_orders_per_side"
        value: str = "3"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "strat_limits.max_cb_notional"
        value: str = "555"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "strat_limits.max_open_cb_notional"
        value: str = "2"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.DEFAULT.value)

        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "strat_limits.max_open_orders_per_side"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

        # with_active_local_changes
        # table_layout
        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "strat_collection")
        widget.find_element(By.NAME, "Edit").click()
        xpath: str = "strat_limits.max_open_orders_per_side"
        value: str = "2"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)


        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "strat_collection")

        xpath: str = "strat_limits.max_open_orders_per_side"
        value: str = "1"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "strat_limits.max_cb_notional"
        value: str = "100"
        enabled_or_not = validate_table_cell_enabled_or_not(widget=widget, xpath=xpath)
        if enabled_or_not:
            set_table_input_field(widget=widget, xpath=xpath, value=value)

        xpath: str = "strat_limits.max_open_cb_notional"
        value: str = "150"
        set_table_input_field(widget=widget, xpath=xpath, value=value)
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)

        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "strat_limits.max_open_orders_per_side"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

    def test_multi_tab_in_repeated_fields(self, driver_type, web_project, driver, schema_dict, pair_strat: Dict):
        # no_active_local_changes
        # open_2n_tab
        # tree_layout
        driver.execute_script("window.open('http://localhost:3020/','_blank');")
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "portfolio_limits")
        widget.find_element(By.NAME, "Edit").click()
        switch_layout(widget=widget, layout=Layout.TREE)
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "255"
        name: str = "available_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "portfolio_limits")
        widget.find_element(By.NAME, "Edit").click()
        switch_layout(widget=widget, layout=Layout.TREE)
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
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        click_on_okay_button_unsaved_changes_popup(driver=driver)

        # with_active_local_changes
        # in_1st_tab
        # tree_layout
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "portfolio_limits")
        widget.find_element(By.NAME, "Edit").click()
        switch_layout(widget=widget, layout=Layout.TREE)
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "255"
        name: str = "available_size"
        set_tree_input_field(widget=widget, xpath=xpath, name=name, value=value)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "portfolio_limits")
        widget.find_element(By.NAME, "Edit").click()
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
        widget.find_element(By.NAME, "Save").click()
        confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        unsaved_changes_field_name = get_unsaved_changes_discarded_key(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        click_on_okay_button_unsaved_changes_popup(driver=driver)


def test_flux_fld_default_in_independent_widget(clean_and_set_limits,web_project, driver_type, schema_dict, driver):
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property="default")
    print(result)
    order_limits_obj = OrderLimitsBaseModel(id=55, max_px_deviation=44)
    # testing create_order_limits_client()
    deleted_order_limits_obj = strat_manager_service_native_web_client.delete_order_limits_client(order_limits_id=1)
    strat_manager_service_native_web_client.delete_portfolio_limits_client(portfolio_limits_id=1)
    strat_manager_service_native_web_client.delete_portfolio_status_client(portfolio_status_id=1)
    driver.refresh()
    time.sleep(Delay.SHORT.value)

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        driver.execute_script('arguments[0].scrollIntoView(true)', widget)
        time.sleep(Delay.SHORT.value)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            default_value: str = field_query.properties['default']
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,widget_name=widget_name,
                                                   field_name=field_name)
            create_btn = widget.find_element(By.NAME, "Create")
            create_btn.click()
            time.sleep(Delay.SHORT.value)
            field_value = get_value_from_input_field(widget=widget, xpath=xpath, layout=Layout.TABLE)
            assert field_value == default_value
















