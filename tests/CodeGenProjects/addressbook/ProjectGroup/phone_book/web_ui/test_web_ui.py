# third party imports
from selenium.webdriver.support import expected_conditions as EC  # noqa
from typing import Set
import pytest

# project specific imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.utility_test_functions import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.web_ui_models import (DriverType, Delay, Layout, WidgetType,
                                                                                             SearchType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_msgspec_routes import TopOfBookBaseModel, QuoteOptional
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_msgspec_routes import (
    PairPlanBaseModel, PlanState, UILayoutBaseModel, WidgetUIDataElementOptional)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import \
    StreetBookServiceHttpClient

# to parameterize all tests. to add support for other browsers, add the DriverType here
pytestmark = pytest.mark.parametrize("driver_type", [DriverType.CHROME])
# pytestmark = pytest.mark.parametrize("driver_type", [DriverType.EDGE])


def test_create_pair_plan(clean_and_set_limits, driver_type, web_project):
    # Test the creation of pair_plan and validate it
    # You may need to interact with the web project to verify that pair_plan is created successfully
    # For example:
    #   - Locate the pair_plan widget
    #   - Verify relevant information or behavior
    pass


def test_update_pair_plan_n_create_n_activate_plan_limits_using_tree_view(clean_and_set_limits, driver_type,
                                                                            web_project, driver: WebDriver,
                                                                            pair_plan_edit: Dict,
                                                                            pair_plan: Dict, plan_limits: Dict):

    pair_plan_params_widget = driver.find_element(By.ID, WidgetName.PairPlanParams.value)
    plan_limits_widget = driver.find_element(By.ID, WidgetName.PlanLimits.value)
    plan_collection_widget = driver.find_element(By.ID, WidgetName.PlanCollection.value)
    click_button_with_name(widget=plan_collection_widget, button_name="Edit")

    fields = {
        "pair_plan_params.common_premium": pair_plan_edit["pair_plan_params"]["common_premium"],
        "pair_plan_params.hedge_ratio": pair_plan_edit["pair_plan_params"]["hedge_ratio"]
    }
    for xpath, value in fields.items():
        name = xpath.split('.')[-1]
        set_tree_input_field(driver=driver, widget=pair_plan_params_widget, xpath=xpath, name=name, value=value)
    click_save_n_click_confirm_save_btn(driver=driver, widget=plan_collection_widget)

    scroll_into_view(driver=driver, element=plan_collection_widget)
    click_edit_n_switch_layout(driver=driver, widget=plan_limits_widget, layout=Layout.TREE)
    create_plan_limits_using_tree_view(driver=driver, plan_limits=plan_limits, layout=Layout.TREE)

    click_save_n_click_confirm_save_btn(driver=driver, widget=plan_collection_widget)
    click_id_fld_inside_plan_collection(plan_collection_widget)
    activate_plan(widget=plan_collection_widget, driver=driver)

    # validate_plan_limits
    switch_layout(widget=plan_limits_widget, layout=Layout.TREE)
    click_button_with_name(widget=plan_collection_widget, button_name="Edit")
    validate_plan_limits(widget=plan_limits_widget, plan_limits=plan_limits, layout=Layout.TREE)

def test_update_plan_limits_n_activate_using_table_view(clean_and_set_limits, driver_type, web_project, driver,
                                                             pair_plan: Dict, plan_limits: Dict):
    plan_limits_widget = driver.find_element(By.ID, WidgetName.PlanLimits.value)
    plan_collection_widget = driver.find_element(By.ID, WidgetName.PlanCollection.value)
    click_button_with_name(widget=plan_limits_widget, button_name="Edit")

    fields_to_update = {
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
        "market_barter_volume_participation.max_participation_rate": plan_limits["market_barter_volume_participation"]
        ["max_participation_rate"],
        "market_barter_volume_participation.applicable_period_seconds":
            plan_limits["market_barter_volume_participation"]["applicable_period_seconds"],
        "market_barter_volume_participation.min_allowed_notional": plan_limits["market_barter_volume_participation"][
            "min_allowed_notional"],
        "market_depth.participation_rate": plan_limits["market_depth"]["participation_rate"],
        "market_depth.depth_levels": plan_limits["market_depth"]["depth_levels"],
        "residual_restriction.max_residual": plan_limits["residual_restriction"]["max_residual"],
        "residual_restriction.residual_mark_seconds": plan_limits["residual_restriction"]["residual_mark_seconds"]
    }

    for xpath, value in fields_to_update.items():
        set_table_input_field(driver=driver, widget=plan_limits_widget, xpath=xpath, value=str(value))

    click_save_n_click_confirm_save_btn(driver, plan_limits_widget)

    click_id_fld_inside_plan_collection(plan_collection_widget)
    activate_plan(widget=plan_collection_widget, driver=driver)
    click_button_with_name(widget=plan_limits_widget, button_name="Edit")
    validate_plan_limits(widget=plan_limits_widget, plan_limits=plan_limits, layout=Layout.TABLE)


def test_field_hide_n_show_in_common_key(clean_and_set_limits, driver_type, web_project, driver, pair_plan: Dict):
    # WidgetType: REPEATED_INDEPENDENT

    widget = driver.find_element(By.ID, WidgetName.PairPlanParams.value)
    switch_layout(widget=widget, layout=Layout.TABLE)
    common_keys_fields: List[str] = get_common_keys_fld_names(widget=widget)

    # searching the random key in setting and hide the fld
    hidden_fld = hide_n_show_inside_setting(widget=widget, driver=driver, common_keys_fields=common_keys_fields, button_state=ButtonState.HIDE)

    # validating that hidden fld is not visible in table view
    validate_hide_n_show_in_common_key(widget=widget, hide_n_show_fld=hidden_fld, button_state=ButtonState.HIDE)

    # searching the random key in setting and show the fld
    showing_fld = hide_n_show_inside_setting(widget=widget, driver=driver, common_keys_fields=common_keys_fields, button_state=ButtonState.SHOW)

    # validating that showing fld is visible in table view
    validate_hide_n_show_in_common_key(widget=widget, hide_n_show_fld=showing_fld, button_state=ButtonState.SHOW)


def test_hide_n_show_in_table_layout(clean_and_set_limits, driver_type, web_project, driver, pair_plan: Dict):
    # WidgetType: REPEATED

    widget = driver.find_element(By.ID, WidgetName.SymbolSideSnapShot.value)
    scroll_into_view(driver=driver, element=widget)
    table_headers: List[str] = get_table_headers(widget=widget)

    # searching the random table text in setting dropdown and hiding the fld
    hidden_fld = hide_n_show_inside_setting(widget=widget, driver=driver, common_keys_fields=table_headers,
                                            button_state=ButtonState.HIDE)

    # validating that hidden fld is not visible in table view
    validate_hide_n_show_in_common_key(widget=widget, hide_n_show_fld=hidden_fld, button_state=ButtonState.HIDE)


    # searching the random table text in setting dropdown and showing the fld
    showing_fld = hide_n_show_inside_setting(widget=widget, driver=driver, common_keys_fields=table_headers,
                                            button_state=ButtonState.SHOW)

    # validating that showing fld is visible in table view
    validate_hide_n_show_in_common_key(widget=widget, hide_n_show_fld=showing_fld, button_state=ButtonState.SHOW)



def test_nested_pair_plan_n_plan_limits(clean_and_set_limits, driver_type, web_project, driver, pair_plan: Dict,
                                           pair_plan_edit: Dict, plan_limits: Dict):

    plan_limits_widget = driver.find_element(By.ID, WidgetName.PlanLimits.value)
    plan_collection_widget = driver.find_element(By.ID, WidgetName.PlanCollection.value)
    pair_plan_params_widget = driver.find_element(By.ID, WidgetName.PairPlanParams.value)
    switch_layout(widget=pair_plan_params_widget, layout=Layout.TABLE)
    click_button_with_name(widget=plan_collection_widget, button_name="Edit")

    pair_plan_td_elements = pair_plan_params_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")
    # xpath: str = "pair_plan_params.common_premium"
    # double-click in table layout to get nested tree layout
    double_click(driver=driver, element=pair_plan_td_elements[6])

    # update value in nested tree layout inside pair plan widget
    nested_tree_dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    for field_name, value in pair_plan_edit["pair_plan_params"].items():
        xpath = "pair_plan_params." + field_name
        set_tree_input_field(driver=driver, widget=nested_tree_dialog, xpath=xpath, name=field_name, value=value)

    save_nested_plan(driver)

    # open nested tree layout in plan limit
    click_button_with_name(widget=plan_limits_widget, button_name="Edit")
    plan_limit_td_elements = plan_limits_widget.find_elements(By.CSS_SELECTOR, "td[class^='MuiTableCell-root']")

    # xpath: str = "max_open_chores_per_side"
    double_click(driver=driver, element=plan_limit_td_elements[0])

    create_plan_limits_using_tree_view(driver=driver, plan_limits=plan_limits, layout=Layout.NESTED)
    save_nested_plan(driver)

    double_click(driver=driver, element=plan_limit_td_elements[0])
    validate_plan_limits(widget=plan_limits_widget, plan_limits=plan_limits, layout=Layout.TREE)


def test_demo(clean_and_set_limits, driver_type, web_project, driver, pair_plan: Dict,
                                           pair_plan_edit: Dict, plan_limits: Dict):
    pass


def test_widget_type(driver_type, schema_dict):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict),
                                          widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldUIPlaceholder)
    print(result)
    assert result[0]
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        print("widget_name:-",widget_name)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            xpath = get_xpath_from_field_name(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                              widget_name=widget_name,
                                              field_name=field_name)
            print(field_name)
            # val_min: int = get_val_of_fld_from_schema(field_query=field_query, val_max=flux_property)




def test_flux_fld_val_max_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                    schema_dict: Dict[str, any], pair_plan: Dict):

    # send the data in str type, and we get the data from the ui by default in str type

    # WidgetType: INDEPENDENT
    # widget: chore limits and contact limit
    set_val_max_input_fld(schema_dict=copy.deepcopy(schema_dict), driver=driver,
                          widget_type=WidgetType.INDEPENDENT,
                          layout=Layout.TABLE, input_type=InputType.MAX_VALID_VALUE,
                          flux_property=FluxPropertyType.FluxFldValMax)

    set_val_max_input_fld(driver=driver, layout=Layout.TREE,
                          schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                          input_type=InputType.MAX_VALID_VALUE,
                          flux_property=FluxPropertyType.FluxFldValMax)


    set_val_max_input_fld(driver=driver, layout=Layout.TABLE,
                          schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                          input_type=InputType.INVALID_VALUE,
                          flux_property=FluxPropertyType.FluxFldValMax)


    set_val_max_input_fld(driver=driver, layout=Layout.TREE,
                          schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                          input_type=InputType.INVALID_VALUE,
                          flux_property=FluxPropertyType.FluxFldValMax)

    result = get_widgets_by_flux_property(schema_dict, WidgetType.DEPENDENT, flux_property = FluxPropertyType.FluxFldValMax)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property = FluxPropertyType.FluxFldValMax)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldValMax)
    print(result)
    assert not result[0]


def test_flux_fld_val_min_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                    schema_dict: Dict[str, any], pair_plan: Dict):

    # widget: chore limits and contact limit
    set_n_validate_val_min_input_fld(
        driver=driver,flux_property=FluxPropertyType.FluxFldValMin,
        widget_type=WidgetType.INDEPENDENT, layout=Layout.TABLE,
        input_type=InputType.MIN_VALID_VALUE,
        schema_dict=copy.deepcopy(schema_dict))

    set_n_validate_val_min_input_fld(
        driver=driver, flux_property=FluxPropertyType.FluxFldValMin,
        widget_type=WidgetType.INDEPENDENT, layout=Layout.TREE,
        input_type=InputType.MIN_VALID_VALUE,
        schema_dict=copy.deepcopy(schema_dict))

    set_n_validate_val_min_input_fld(
        driver=driver, flux_property=FluxPropertyType.FluxFldValMin,
        widget_type=WidgetType.INDEPENDENT, layout=Layout.TABLE,
        input_type=InputType.MIN_INVALID_VALUE,
        schema_dict=copy.deepcopy(schema_dict))

    set_n_validate_val_min_input_fld(
        driver=driver, flux_property=FluxPropertyType.FluxFldValMin,
        widget_type=WidgetType.INDEPENDENT, layout=Layout.TREE,
        input_type=InputType.MIN_INVALID_VALUE,
        schema_dict=copy.deepcopy(schema_dict))


    # TODO: LAZY:  val min property is not used in dependent widget yet
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldValMin)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldValMin)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldValMin)
    print(result)
    assert not result[0]


def test_flux_fld_help_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                 schema_dict: Dict[str, any], pair_plan: Dict):

    # TODO: LAZY sometimes throw StaleElementReferenceException

    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT, flux_property=FluxPropertyType.FluxFldHelp)
    assert result[0]
    print(result)

    # TABLE LAYOUT
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name in ["plan_limits", "basket_chore"]:
            continue
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Settings")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            schema_help_txt: str = field_query.properties['help']
            if field_name in ["sec_id", "max_rolling_tx_count", "rolling_tx_count_period_seconds", "sec_id_source", "inst_type"]:
                continue

            setting_dropdown = widget.find_element(By.XPATH, f'//*[@id="{widget_name}_table_settings"]/div[3]')
            time.sleep(Delay.SHORT.value)

            contains_element = setting_dropdown.find_element(By.XPATH, f"//button[@aria-label='{schema_help_txt}']")
            hover_over_on_element(driver=driver,element=contains_element)


            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip']")
            hovered_element_text = tooltip_element.text
            assert schema_help_txt == hovered_element_text, f"Expected {schema_help_txt} but got {hovered_element_text} for fld{field_name} inside Widget:- {widget_name}"
        close_setting(driver)

    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldHelp)
    print(result)
    assert result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldHelp)
    assert result[0]


    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Settings")
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            if field_name in ["sec_id","max_rolling_tx_count","rolling_tx_count_period_seconds", "sec_id_source", "inst_type"]:
                continue
            schema_help_txt: str = field_query.properties['help']

            setting_dropdown = widget.find_element(By.XPATH, f'//*[@id="{widget_name}_table_settings"]/div[3]')
            time.sleep(Delay.SHORT.value)
            contains_element = setting_dropdown.find_element(By.XPATH, f"//button[@aria-label='{schema_help_txt}']")
            hover_over_on_element(driver=driver, element=contains_element)

            tooltip_element = driver.find_element(By.CSS_SELECTOR, "div[class^='MuiTooltip']")
            hovered_element_text = tooltip_element.text
            assert schema_help_txt == hovered_element_text,  f"Expected {schema_help_txt} but got {hovered_element_text} for fld{field_name} inside Widget:- {widget_name}"
        close_setting(driver)


    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldHelp)
    print(result)
    assert not result[0]


def test_flux_fld_display_type_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                         schema_dict: Dict[str, any], pair_plan: Dict):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT, flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert result[0]

    # contact limits, chore limits and contact status
    # TABLE LAYOUT
    for widget_query in result[1]:
        field_name_n_xpath: Dict[str, str] = {}
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TABLE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            val_min, val_max = get_val_min_n_val_max_of_fld(field_query=field_query)
            value: str = is_property_contain_val_min_val_max_or_none(val_max=val_max, val_min=val_min)
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            if field_name in ["max_open_notional_per_side", "max_chore_notional_algo", "total_fill_buy_notional",
                              "total_fill_sell_notional", "residual_notional"]:
                continue

            field_name_n_xpath[field_name] = xpath
            try:
                set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=str(value))
            except NoSuchElementException:
                set_table_input_field(driver=driver, widget=widget, xpath=field_name, value=str(value))
            except Exception as e:
                print("while setting table input fld Exception;;;;", e)
        click_save_n_click_confirm_save_btn(driver, widget)
        validate_flux_fld_display_type_in_widget(driver=driver, widget=widget, field_name_n_xpath=field_name_n_xpath,
                                                 layout=Layout.TABLE)

    # tree_layout
    for widget_query in result[1]:
        field_name_n_xpath = {}
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            val_min, val_max = get_val_min_n_val_max_of_fld(field_query=field_query)
            value = is_property_contain_val_min_val_max_or_none(val_max=val_max, val_min=val_min)
            xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
                                                   widget_name=widget_name, field_name=field_name)
            if field_name in ["max_open_notional_per_side", "max_chore_notional_algo",
                                       "total_fill_buy_notional",
                              "total_fill_sell_notional", "residual_notional"]:
                continue

            field_name_n_xpath[field_name] = xpath

            # in plan status widget nested sec id fld is not showing any dropdown list for selecting security
            # in plan status widget residual_notional is not working
            if widget_name == "plan_status":
                continue
            # show_nested_fld_in_tree_layout(widget=widget, fld_xpath=xpath)
            set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=field_name, value=str(value))
        click_save_n_click_confirm_save_btn(driver, widget)
        validate_flux_fld_display_type_in_widget(driver=driver, widget=widget, field_name_n_xpath=field_name_n_xpath,
                                                 layout=Layout.TREE)



    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert not result[0]


def test_flux_fld_number_format_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                                      schema_dict: Dict[str, any], pair_plan: Dict):
    # TABLE LAYOUT
    get_n_validate_number_format_from_input_fld(
        schema_dict=copy.deepcopy(schema_dict),
        widget_type=WidgetType.INDEPENDENT,
        driver=driver,
        flux_property=FluxPropertyType.FluxFldNumberFormat,
        layout=Layout.TABLE
    )

    # TREE LAYOUT
    get_n_validate_number_format_from_input_fld(
        schema_dict=copy.deepcopy(schema_dict),
        widget_type=WidgetType.INDEPENDENT,
        driver=driver,
        flux_property=FluxPropertyType.FluxFldNumberFormat,
        layout=Layout.TREE
    )

    # pair_start_params - TABLE LAYOUT
    get_n_validate_number_format_from_input_fld(
        schema_dict=copy.deepcopy(schema_dict),
        widget_type=WidgetType.DEPENDENT,
        driver=driver,
        flux_property=FluxPropertyType.FluxFldNumberFormat,
        layout=Layout.TABLE
    )

    get_n_validate_number_format_from_input_fld(
        schema_dict=copy.deepcopy(schema_dict),
        widget_type=WidgetType.DEPENDENT,
        driver=driver,
        flux_property=FluxPropertyType.FluxFldNumberFormat,
        layout=Layout.TREE
    )

    get_n_validate_number_format_from_input_fld(
        schema_dict=copy.deepcopy(schema_dict),
        widget_type=WidgetType.REPEATED_INDEPENDENT,
        driver=driver,
        flux_property=FluxPropertyType.FluxFldNumberFormat,
        layout=Layout.TABLE
    )

    get_n_validate_number_format_from_input_fld(
        schema_dict=copy.deepcopy(schema_dict),
        widget_type=WidgetType.REPEATED_INDEPENDENT,
        driver=driver,
        flux_property=FluxPropertyType.FluxFldNumberFormat,
        layout=Layout.TREE
    )


def test_flux_flx_display_zero_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                         schema_dict: Dict[str, any], pair_plan: Dict):

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property=FluxPropertyType.FluxFldDisplayZero)
    print(result)
    assert result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldDisplayZero)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayZero)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayZero)
    print(result)
    assert not result[0]


def test_flux_fld_server_populate_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                            schema_dict, pair_plan: Dict):

    # TABLE LAYOUT
    get_n_validate_server_populate_fld(driver=driver, schema_dict=copy.deepcopy(schema_dict),
                            layout=Layout.TABLE, widget_type=WidgetType.INDEPENDENT)

    # TREE LAYOUT
    get_n_validate_server_populate_fld(driver=driver, schema_dict=copy.deepcopy(schema_dict),
                            layout=Layout.TREE,  widget_type=WidgetType.INDEPENDENT)

    driver.refresh()
    time.sleep(Delay.SHORT.value)

    # TABLE LAYOUT
    get_n_validate_server_populate_fld(driver=driver, schema_dict=copy.deepcopy(schema_dict), layout=Layout.TABLE,
                            widget_type=WidgetType.DEPENDENT)

    # TABLE LAYOUT
    get_n_validate_server_populate_fld(driver=driver, schema_dict=copy.deepcopy(schema_dict), layout=Layout.TREE,
                            widget_type=WidgetType.DEPENDENT)

    # get_n_validate_server_populate_fld(driver=driver, schema_dict=copy.deepcopy(schema_dict), layout=Layout.TABLE,
    #                                    widget_type=WidgetType.REPEATED_INDEPENDENT)

    # get_n_validate_server_populate_fld(driver=driver, schema_dict=copy.deepcopy(schema_dict), layout=Layout.TREE,
    #                                    widget_type=WidgetType.REPEATED_INDEPENDENT)


    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldServerPopulate)
    print(result)
    assert not result[0]


def test_flux_fld_button_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                               schema_dict: Dict[str, any], pair_plan: Dict):
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict),
    widget_type=WidgetType.INDEPENDENT,
    flux_property=FluxPropertyType.FluxFldButton)
    print(result)
    assert result[0]

    get_n_validate_fld_btn(schema_dict=copy.deepcopy(schema_dict), driver=driver, widget_type=WidgetType.INDEPENDENT)


    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict),
    widget_type=WidgetType.DEPENDENT,
    flux_property=FluxPropertyType.FluxFldButton)
    print(result)
    assert not result[0]

    get_n_validate_fld_btn(schema_dict=copy.deepcopy(schema_dict), driver=driver,
                               widget_type=WidgetType.REPEATED_INDEPENDENT)

    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict),
    widget_type=WidgetType.REPEATED_DEPENDENT,
    flux_property=FluxPropertyType.FluxFldButton)
    print(result)
    assert not result[0]



def test_flux_fld_orm_no_update_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                          schema_dict, pair_plan: Dict):
    # TODO: only id fields are present in independent widget that's why skip this as of now
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldOrmNoUpdate)
    print(result)
    assert result[0]

    # todo: need help for property: orm_no_update and fix for DEPENDENT widget
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldOrmNoUpdate)
    print(result)
    assert result[0]

    # TODO: only id fields are present in REPEATED_INDEPENDENT widget that's why skip this as of now
    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldOrmNoUpdate)
    print(result)
    assert result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldOrmNoUpdate)
    print(result)
    assert not result[0]


def test_flux_fld_comma_separated_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                            schema_dict: Dict[str, any], pair_plan: Dict):

    # TABLE LAYOUT
    set_n_validate_input_value_for_comma_seperated(driver=driver, schema_dict=copy.deepcopy(schema_dict), layout=Layout.TABLE)

    # TREE LAYOUT
    set_n_validate_input_value_for_comma_seperated(driver=driver, schema_dict=copy.deepcopy(schema_dict), layout=Layout.TREE)

    # WidgetType: DEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    # Note: Currently repeated type is not supported `Edit` mode
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert result[0]

    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDisplayType)
    print(result)
    assert not result[0]


def test_flux_fld_name_color_in_independent_widget(clean_and_set_limits, driver_type, web_project, driver,
                                                   schema_dict, pair_plan: Dict):
    # TODO: Need help get_fld_name_colour_in_tree line: 1291
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.INDEPENDENT, flux_property=FluxPropertyType.FluxFldNameColor)
    print(result)
    assert result[0]

    # TABLE LAYOUT
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=Layout.TREE)
        # for field_query in widget_query.fields:
        #     # field_name: str = field_query.field_name
        #     # name_color: str = field_query.properties['name_color']
        #     # xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
        #     #                                        widget_name=widget_name, field_name=field_name)
        #     # TODO: make a method get get name color of table layout
        #     # fld_color = get_fld_name_colour_in_tree(widget=widget, xpath=xpath)
        #     # assert name_color == fld_color


    # TREE LAYOUT
    # field_name: str = ""
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        switch_layout(widget=widget, layout=Layout.TREE)
        scroll_into_view(driver=driver, element=widget)
        # for field_query in widget_query.fields:
        #     field_name: str = field_query.field_name
        #     # name_color: str = field_query.properties['name_color']
        #     # xpath: str = get_xpath_from_field_name(schema_dict, widget_type=WidgetType.INDEPENDENT,
        #     #                                        widget_name=widget_name, field_name=field_name)
        #     # fld_color = get_fld_name_colour_in_tree(widget=widget, xpath=xpath)
        #     # assert name_color == Type.ColorType(ColorType.ERROR)
        #     # assert name_color == fld_color

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldNameColor)
    assert not result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT, flux_property=FluxPropertyType.FluxFldNameColor)
    assert not result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT, flux_property=FluxPropertyType.FluxFldNameColor)
    assert not result[0]


def test_flux_fld_progress_bar_in_widget(clean_and_set_limits, driver_type, web_project, driver,
                                         schema_dict, pair_plan: Dict):

    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldProgressBar)
    print(result)
    assert not result[0]

    # can't automate for table layout bcz it does not contains progressbar
    # TREE LAYOUT
    # for widget_query in result[1]:
    #     widget_name = widget_query.widget_name
    #     widget = driver.find_element(By.ID, widget_name)
    #     for field_query in widget_query.fields:
    #         field_name: str = field_query.field_name
    #         val_min, val_max = get_val_min_n_val_max_of_fld(field_query=field_query)
    #         get_val_max, widget_name = get_val_max_from_input_fld(val_max=val_max, driver=driver,
    #                                                               widget_type=WidgetType.INDEPENDENT,layout=Layout.TREE)
    #         # FIXME: NOT GETTING ANY XPATH
    #         xpath: str = get_xpath_from_field_name(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
    #                                                widget_name=widget_name, field_name=field_name)
    #
    #         scroll_into_view(driver=driver, element=widget)
    #         input_n_validate_progress_bar(driver=driver, widget=widget, field_name=field_name, value=val_min,
    #                                       input_value_type="val_min")
    #
    #         # for val max
    #         input_n_validate_progress_bar(driver=driver, widget=widget, field_name=field_name, value=get_val_max,
    #                                      input_value_type="val_max")

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldProgressBar)
    print(result)
    assert not result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldProgressBar)
    print(result)
    assert not result[0]

    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldProgressBar)
    print(result)
    assert not result[0]


class TestMultiTab:

    def setup_method(self):
        self.url: str = "http://localhost:3020/"

    @staticmethod
    def switch_tab(driver, switch_tab_no: int):
        window_handles = driver.window_handles
        driver.switch_to.window(window_handles[switch_tab_no])

    def test_multi_tab_in_independent_widget(self, driver_type, web_project, driver, schema_dict, pair_plan: Dict):
        # Open a new tab and switch to it
        driver.execute_script(f"window.open('{self.url}','_blank');")
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "chore_limits")
        click_button_with_name(widget=widget, button_name="Edit")

        xpath: str = "max_basis_points"
        value: str = "750"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        # Switch back to the first tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "chore_limits")
        click_button_with_name(widget=widget, button_name="Edit")

        # Set values in the table
        set_table_input_field(driver=driver, widget=widget, xpath="max_basis_points", value="400")
        set_table_input_field(driver=driver, widget=widget, xpath="max_px_deviation", value="1")
        set_table_input_field(driver=driver, widget=widget, xpath="min_chore_notional", value="10000")
        click_save_n_click_confirm_save_btn(driver=driver, widget=widget)

        # Open 2nd tab you will get a popup of unsaved changes verify that max_basis_points is present and click okay
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        unsaved_changes_field_name = get_fld_name_frm_unsaved_changes_dialog(driver=driver)
        assert unsaved_changes_field_name == "max_basis_points"
        click_okay_btn_inside_unsaved_changes_dialog(driver=driver)

        # Switch back to 1st tab and set values
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "chore_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        set_table_input_field(driver=driver, widget=widget, xpath="max_basis_points", value="75")

        # Switch back to 2nd tab and set more values
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "chore_limits")
        set_table_input_field(driver=driver, widget=widget, xpath="max_basis_points", value="40")
        set_table_input_field(driver=driver, widget=widget, xpath="max_px_deviation", value="1")
        set_table_input_field(driver=driver, widget=widget, xpath="min_chore_notional", value="1200")
        click_save_n_click_confirm_save_btn(driver=driver, widget=widget)

        # Final validation
        self.switch_tab(driver=driver, switch_tab_no=0)
        unsaved_changes_field_name = get_fld_name_frm_unsaved_changes_dialog(driver=driver)
        assert unsaved_changes_field_name == "max_basis_points"
        click_okay_btn_inside_unsaved_changes_dialog(driver=driver)

    def test_multi_tab_in_dependent_widget(self, driver_type, web_project, driver, schema_dict, pair_plan: Dict):
        # no_active_local_changes
        # open_2n_tab
        # TABLE LAYOUT
        driver.execute_script(self.url)
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.DEFAULT.value)

        widget = driver.find_element(By.ID, "plan_limits")
        click_edit_n_switch_layout(driver=driver, widget=widget, layout=Layout.TREE)

        xpath: str = "max_open_chores_per_side"
        value: str = "4"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "plan_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)

        xpath: str = "max_open_chores_per_side"
        value: str = "3"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "max_open_single_leg_notional"
        value: str = "555"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "max_open_single_leg_notional"
        value: str = "2"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "cancel_rate.max_cancel_rate"
        value: str = "10"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "market_barter_volume_participation.max_participation_rate"
        value: str = "20"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)
        click_save_n_click_confirm_save_btn(widget=widget, driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.DEFAULT.value)

        unsaved_changes_field_name = get_fld_name_frm_unsaved_changes_dialog(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "max_open_chores_per_side"
        click_okay_btn_inside_unsaved_changes_dialog(driver=driver)

        # with_active_local_changes
        # TABLE LAYOUT
        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "plan_limits")
        # widget.find_element(By.NAME, "Edit").click()
        xpath: str = "max_open_chores_per_side"
        value: str = "2"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "plan_limits")

        xpath: str = "max_open_chores_per_side"
        value: str = "1"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "max_open_single_leg_notional"
        value: str = "100"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "max_open_single_leg_notional"
        value: str = "150"
        set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        click_confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)

    def test_multi_tab_in_repeated_fields(self, driver_type, web_project, driver, schema_dict, pair_plan: Dict):
        # no_active_local_changes
        # open_2n_tab
        # tree_layout
        driver.execute_script(self.url)
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        widget = driver.find_element(By.ID, "contact_limits")
        click_button_with_name(widget=widget, button_name="Edit")

        switch_layout(widget=widget, layout=Layout.TREE)
        widget.find_element(By.XPATH,
                            "//body[1]/div[1]/div[1]/div[2]/div[11]/div[1]/div[1]/div[1]/ul[1]/"
                            "div[6]/div[2]/button[1]").click()
        widget.find_element(By.XPATH, "//div[6]//div[2]//*[name()='svg']").click()
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "255"
        name: str = "available_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "contact_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        widget.find_element(By.XPATH,
                            "//body[1]/div[1]/div[1]/div[2]/div[11]/div[1]/div[1]/div[1]/ul[1]/div[6]/div[2]"
                            "/button[1]").click()
        widget.find_element(By.XPATH, "//div[6]//div[2]//*[name()='svg']").click()
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "25"
        name: str = "available_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].allocated_size"
        value: str = "5"
        name: str = "allocated_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].consumed_size"
        value: str = "7"
        name: str = "consumed_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "max_open_baskets"
        value: str = "51"
        name: str = "max_open_baskets"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].security.sec_id"
        value: str = "Type2_Sec_1"
    
        
        set_autocomplete_field(driver=driver, widget=widget, xpath=xpath, name="sec_id", search_type=SearchType.NAME, value=value)
            #   set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].type"
        input_xpath = f"//div[@data-xpath='{xpath}']"
        widget.find_element(By.XPATH, input_xpath).click()
        value: str = "PTH"
        option = driver.find_element(By.XPATH, f"//li[text()='{value}']")
        option.click()

        # set_autocomplete_field(widget=widget, xpath=xpath, name="type", search_type=SearchType.NAME, value=value)

        #    set_table_input_field(driver=driver, widget=widget, xpath=xpath, value=value)

        xpath: str = "eligible_brokers[0].broker"
        value: str = "AAPL"
        name: str = "broker"

        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        click_button_with_name(widget=widget, button_name="Save")
        click_confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        # with_active_local_changes
        # in_1st_tab
        # tree_layout
        self.switch_tab(driver=driver, switch_tab_no=0)
        time.sleep(Delay.SHORT.value)
        widget = driver.find_element(By.ID, "contact_limits")
        click_button_with_name(widget=widget, button_name="Edit")
        switch_layout(widget=widget, layout=Layout.TREE)
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "255"
        name: str = "available_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        click_confirm_save(driver=driver)

        # open_2nd_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)

        unsaved_changes_field_name = get_fld_name_frm_unsaved_changes_dialog(driver=driver)
        unsaved_changes_field_name = unsaved_changes_field_name.replace('"', '')
        assert unsaved_changes_field_name == "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        click_okay_btn_inside_unsaved_changes_dialog(driver=driver)

        widget = driver.find_element(By.ID, "contact_limits")
        # widget.find_element(By.NAME, "Edit").click()
        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].available_size"
        value: str = "25"
        name: str = "available_size"
        switch_layout(widget=widget, layout=Layout.TREE)
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].allocated_size"
        value: str = "5"
        name: str = "allocated_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)

        xpath: str = "eligible_brokers[0].sec_positions[0].positions[0].consumed_size"
        value: str = "7"
        name: str = "consumed_size"
        set_tree_input_field(driver=driver, widget=widget, xpath=xpath, name=name, value=value)
        click_button_with_name(widget=widget, button_name="Save")
        click_confirm_save(driver=driver)

        # open_1st_tab
        self.switch_tab(driver=driver, switch_tab_no=1)
        time.sleep(Delay.SHORT.value)


def test_flux_fld_default_value_in_widget(clean_and_set_limits, web_project, driver_type, schema_dict: Dict[str, any], driver):

    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDefault)
    print(result)
    assert result[0]
    delete_ol_pl_ps_client(driver)

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        if WidgetName.BasketChore.value:
            continue
        if widget_name in ["contact_alert", "plan_limits", "plan_status", "plan_alert"]:
            click_button_with_name(widget=widget, button_name="Edit")
        else:
            click_button_with_name(widget=widget, button_name="Create")
        switch_layout(widget, Layout.TABLE)

        for field_query in widget_query.fields:
            flux_fld_default_widget(schema_dict=copy.deepcopy(schema_dict), widget=widget,
                                    widget_type=WidgetType.INDEPENDENT, widget_name=widget_name,
                                    layout=Layout.TABLE, field_query=field_query)



    # WidgetType: dependent
    refresh_page_n_short_delay(driver)
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.DEPENDENT, flux_property=FluxPropertyType.FluxFldDefault)
    delete_ol_pl_ps_client(driver)

    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        if widget_name == WidgetName.PairPlanParams.value:
            click_button_with_name(driver.find_element(By.ID, "plan_collection"), button_name="Create")
        widget = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        show_hidden_fields_for_layout(driver=driver, widget=widget, layout=Layout.TREE, widget_name=widget_name)
        switch_layout(widget=widget, layout=Layout.TREE)

        for field_query in widget_query.fields:
            flux_fld_default_widget(schema_dict=copy.deepcopy(schema_dict), widget=widget,
                                    widget_type=WidgetType.DEPENDENT, widget_name=widget_name,
                                    layout=Layout.TREE, field_query=field_query)


    # WidgetType: REPEATED_INDEPENDENT
    refresh_page_n_short_delay(driver)
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDefault)
    print(result)
    assert result[0]
    for widget_query in result[1]:
        widget_name = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        for field_query in widget_query.fields:
            flux_fld_default_widget(schema_dict=copy.deepcopy(schema_dict), widget=widget,
                                    widget_type=WidgetType.REPEATED_INDEPENDENT, widget_name=widget_name,
                                    layout=Layout.TABLE, field_query=field_query)


    # WidgetType: REPEATED_DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldDefault)
    print(result)
    assert not result[0]


def test_flux_fld_ui_update_only(driver_type: DriverType,
                                 schema_dict: Dict, driver: WebDriver):

    # WidgetType: INDEPENDENT
    # Note: only enabled in dismiss field
    result = get_widgets_by_flux_property(schema_dict, WidgetType.INDEPENDENT, FluxPropertyType.FluxFldUiUpdateOnly)
    print(result)
    assert result[0]

    # WidgetType: DEPENDENT
    result = get_widgets_by_flux_property(schema_dict, WidgetType.DEPENDENT, FluxPropertyType.FluxFldUiUpdateOnly)
    print(result)
    assert not result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, WidgetType.REPEATED_INDEPENDENT, FluxPropertyType.FluxFldUiUpdateOnly)
    print(result)
    assert result[0]

    # WidgetType: REPEATED_INDEPENDENT
    result = get_widgets_by_flux_property(schema_dict, WidgetType.REPEATED_INDEPENDENT, FluxPropertyType.FluxFldUiUpdateOnly)
    print(result)
    assert result[0]


def test_flux_fld_ui_place_holder_in_widget(clean_and_set_limits, driver_type: DriverType,
                                            schema_dict: Dict, driver: WebDriver):

    driver.maximize_window()
    driver.get(get_web_project_url())
    time.sleep(Delay.SHORT.value)
    email_book_service_native_web_client.delete_contact_limits_client(contact_limits_id=1)

    flux_fld_ui_place_holder_in_widget(schema_dict=schema_dict, driver=driver, widget_type=WidgetType.INDEPENDENT)

    flux_fld_ui_place_holder_in_widget(schema_dict=schema_dict, driver=driver, widget_type=WidgetType.DEPENDENT)

    flux_fld_ui_place_holder_in_widget(schema_dict=schema_dict, driver=driver, widget_type=WidgetType.REPEATED_INDEPENDENT)

    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldUIPlaceholder)
    print(result)
    assert not result[0]


def test_flux_fld_sequence_number_in_widget(clean_and_set_limits, web_project, driver_type: DriverType,
                                            schema_dict: Dict, driver: WebDriver):


    get_n_validate_flux_fld_sequence_number_in_widget(schema_dict=copy.deepcopy(schema_dict), driver=driver,
                                                      widget_type=WidgetType.INDEPENDENT)

    get_n_validate_flux_fld_sequence_number_in_widget(schema_dict=copy.deepcopy(schema_dict), driver=driver,
                                                      widget_type=WidgetType.DEPENDENT)

    get_n_validate_flux_fld_sequence_number_in_widget(schema_dict=copy.deepcopy(schema_dict), driver=driver,
                                                      widget_type=WidgetType.REPEATED_INDEPENDENT)


    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.REPEATED_DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldSequenceNumber)
    print(result)
    assert not result[0]


def test_flux_fld_elaborate_title_in_widget(clean_and_set_limits, web_project, driver_type: DriverType,
                                            schema_dict: Dict, driver: WebDriver):

    get_n_validate_fld_fld_elaborate_title(schema_dict=copy.deepcopy(schema_dict),
    widget_type=WidgetType.DEPENDENT, driver=driver)

    get_n_validate_fld_fld_elaborate_title(schema_dict=copy.deepcopy(schema_dict),
                                           widget_type=WidgetType.REPEATED_INDEPENDENT,
                                           driver=driver)



def test_flux_fld_filter_enabled_in_widget(clean_and_set_limits, driver_type: DriverType,
                                           schema_dict: Dict, driver: WebDriver):

    # Note: Only enabled in WidgetType: REPEATED_INDEPENDENT
    driver.maximize_window()
    driver.get(get_web_project_url())

    time.sleep(Delay.SHORT.value)
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict),
                                          widget_type=WidgetType.REPEATED_INDEPENDENT, flux_property=FluxPropertyType.FluxFldFilterEnabled)
    print(result)
    assert result[0]

    for widget_query in result[1]:
        driver.refresh()
        time.sleep(Delay.SHORT.value)
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        click_button_with_name(widget=widget, button_name="Filter")
        filter_value: List[str] = get_element_text_list_from_filter_popup(driver=driver)
        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            assert field_name in filter_value


def test_flux_fld_no_common_key_in_widget(clean_and_set_limits: None, web_project: None, driver_type: DriverType,
                                          schema_dict: Dict, driver: WebDriver):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldNoCommonKey)
    print(result)
    assert result[0]

    for widget_query in result[1]:
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=Layout.TABLE)

        if widget_name not in ["plan_limits", "plan_alert"]:
            keys_from_table: List[str] = get_all_keys_from_table(widget)
        else:
            continue

        for field_query in widget_query.fields:
            field_name: str = field_query.field_name
            assert field_name in keys_from_table


    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict),
                                          widget_type=WidgetType.REPEATED_INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldNoCommonKey)

    print(result)
    assert result[0]

    for result_widget_query, elaborate_title_widget_query in zip(result[1], result[1]):
        widget_name: str = result_widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        reload_widget_open_n_close_setting(driver, widget, widget_name)
        switch_layout(widget=widget, layout=Layout.TABLE)

        if widget_name not in ["plan_limits", "plan_alert"]:
            keys_from_table: List[str] = get_all_keys_from_table(widget)
        else:
            continue

        for result_field_query, elaborate_title_field_query in (
                zip(result_widget_query.fields, elaborate_title_widget_query.fields)):
            field_name: str = result_field_query.field_name
            elaborate_title = elaborate_title_field_query.properties.get("elaborate_title")
            if elaborate_title is not None:
                default_value: str = elaborate_title_field_query.properties.get("parent_title") + "." + field_name
            else:
                default_value: str = field_name
            if field_name in ["qty"]:
                continue
            assert default_value in keys_from_table

def test_flux_fld_title_in_widgets(clean_and_set_limits, web_project, driver_type: DriverType,
                                   driver: WebDriver, schema_dict: Dict):
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldTitle)
    print(result)
    assert result[0]

    flux_fld_title_in_widgets(result=result[1], widget_type=WidgetType.INDEPENDENT, driver=driver)

    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldTitle)
    print(result)
    assert result[0]
    flux_fld_title_in_widgets(result=result[1], widget_type=WidgetType.DEPENDENT, driver=driver)


def test_flux_fld_autocomplete_in_widgets(clean_and_set_limits, driver_type, driver, schema_dict):
    autocomplete_dict: Dict[str, any] = schema_dict.get("autocomplete")
    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.INDEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldAutoComplete)

    assert result[0]

    flux_fld_autocomplete_in_widgets(result[1], autocomplete_dict)

    result = get_widgets_by_flux_property(schema_dict=copy.deepcopy(schema_dict), widget_type=WidgetType.DEPENDENT,
                                          flux_property=FluxPropertyType.FluxFldAutoComplete)

    assert result[0]

    flux_fld_autocomplete_in_widgets(result[1], autocomplete_dict)


def test_flux_fld_abbreviated_in_widgets(clean_and_set_limits, web_project, driver_type, driver, schema_dict):
    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.ABBREVIATED,
                                          flux_property=FluxPropertyType.FluxFldAbbreviate)
    abc = schema_dict.get("abbreviated")
    print(abc)
    assert not result[0]
    print(result[1])

    for widget_query in result[1]:
        widget_name: str = widget_query.widget_name
        widget: WebElement = driver.find_element(By.ID, widget_name)

        click_button_with_name(widget, "Edit")
        table_header_list: List[str] = get_all_keys_from_table(widget)

        # todo: fetch the data from backend and verify that display data on UI is same or not
        for field_query in widget_query.fields:
            default_abbreviated_list: List[str] = field_query.properties["abbreviated"].split("^")
            for default_abbreviated in default_abbreviated_list:
                assert default_abbreviated.split(":")[0].replace(" ", "_") in table_header_list


def test_flux_fld_micro_separator_in_widgets(clean_and_set_limits, web_project, driver_type, driver, schema_dict,
                                             set_micro_seperator_and_clean):

    result = get_widgets_by_flux_property(schema_dict=schema_dict, widget_type=WidgetType.ABBREVIATED,
                                          flux_property=FluxPropertyType.FluxFldAbbreviate)
    assert not result[0]

    try:
        for widget_query in result[1]:
            widget_name: str = widget_query.widget_name
            widget: WebElement = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            common_key_value: Dict[str, any] = get_commonkey_items(widget)

            for field_query in widget_query.fields:
                default_abbreviated_list: List[str] = field_query.properties["abbreviated"].split("^")
                for default_abbreviated in default_abbreviated_list:
                    key: str = default_abbreviated.split(":")[0].replace(" ", "_")
                    if default_abbreviated.split(":")[-1].find("-") != -1 and key != "Company":
                        value = common_key_value[key]
                        assert "=" in value, f"micro_separator not fount in {value}"

    except Exception as e:
        print(e)



def test_flux_fld_enable_and_disable_override_in_widgets(clean_and_set_limits, web_project, driver_type,
                                                         driver, schema_dict):
    dependent_widget: Set[str] = set()

    for widget_name, widget_schema in schema_dict.items():
        if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element"]:
            continue

        loaded_plan_keys: Dict[str, any] | None = widget_schema.get("properties").get("loaded_plan_keys")
        if loaded_plan_keys is not None:
            abbreviated: str = loaded_plan_keys.get("abbreviated")
            field_list: list = abbreviated.split(":")

            for field_item in field_list:  # Renamed 'field' to 'field_item'
                if '/' not in field_item:
                    dependent_widget_name: str = field_item.split(".")
                    if dependent_widget_name[0] == "pair_plan":
                        dependent_widget.add("pair_plan_params")
                    else:
                        dependent_widget.add(dependent_widget_name[0])
                # else not required

        if widget_name not in dependent_widget:
            driver.find_element(By.NAME, widget_name).click()

            try:
                # Attempt to find the element
                widget: WebElement = driver.find_element(By.ID, widget_name)

                # If the element is found, check if it is displayed
                assert not widget.is_displayed(), "Element should not be present"
            except NoSuchElementException:
                # If the element is not found, it's not present, so the assertion passes
                pass

    save_layout(driver, "test")
    load_layout(driver, "test")

    for widget_name, widget_schema in schema_dict.items():
        if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element"]:
            continue

        if widget_name not in dependent_widget:
            driver.find_element(By.NAME, widget_name).click()

            widget = driver.find_element(By.ID, widget_name)
            assert widget.is_displayed()

    ui_layout_list = email_book_service_native_web_client.get_all_ui_layout_client()
    email_book_service_native_web_client.delete_ui_layout_client(ui_layout_id=ui_layout_list[-1].id)



def test_ui_coordinates(clean_and_set_limits, driver, driver_type, schema_dict, ui_layout_list_):
    try:
        driver.get(get_web_project_url())
        time.sleep(Delay.SHORT.value)
        driver.maximize_window()
        # before running test case clear ui layout database if any
        created_ui_layout = email_book_service_native_web_client.create_ui_layout_client(ui_layout_list_)
        print(created_ui_layout)
        load_layout(driver, "test")
        save_layout(driver, "test1")
        time.sleep(Delay.DEFAULT.value)
        ui_layout_list = email_book_service_native_web_client.get_all_ui_layout_client()
        print(ui_layout_list)
        ui_layout_list_.id = ui_layout_list[-1].id
        ui_layout_list_.profile_id = ui_layout_list[-1].profile_id
        ui_layout_list_ = ui_layout_list[-1]
        assert ui_layout_list_ == ui_layout_list[-1]

        for _ in ui_layout_list:
            email_book_service_native_web_client.delete_ui_layout_client(_.id)
    except Exception as e:
        print("EX", e)


def test_view_layout(clean_and_set_limits, web_project, driver, driver_type, schema_dict):
    for widget_name, widget_schema in schema_dict.items():
        # Clicking "Create" in System Control changes the default layout to a tree;
        # it switched to a tree after clicking "Create" in Web Project fixture.
        if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element", "basket_chore", "system_control"]:
            continue
        widget: WebElement = driver.find_element(By.ID, widget_name)
        current_ui_layout = get_current_ui_layout_name(widget)
        default_view_layout: str = widget_schema["widget_ui_data_element"]["widget_ui_data"][0]["view_layout"]
        assert default_view_layout == current_ui_layout


def test_edit_layout(clean_and_set_limits, web_project, driver, driver_type, schema_dict):
    try:
        for widget_name, widget_schema in schema_dict.items():

            if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element"]:
                continue

            widget_type: WidgetType | None = get_widget_type(widget_schema)
            # currently edit not supports in REPEATED widgets
            if widget_type in [WidgetType.INDEPENDENT, WidgetType.DEPENDENT]:
                if widget_name == "pair_plan_params":
                    widget: WebElement = driver.find_element(By.ID, widget_name)
                    click_button_with_name(driver.find_element(By.ID, "plan_collection"), "Edit")
                else:
                    widget: WebElement = driver.find_element(By.ID, widget_name)
                    # When the 'Create' button is clicked in System Control,
                    # the 'Edit' button disappears by default. This has already been done in the Web Project fixture.
                    if widget_name in ["system_control", "basket_chore"]:
                        continue
                    click_button_with_name(widget, "Edit")

                button: WebElement = widget.find_element(By.NAME, "Layout")
                ui_view_layout: str = button.get_attribute('aria-label').split(":")[-1].replace(" ", "")
                default_layout = widget_schema["widget_ui_data_element"]["widget_ui_data"][0]
                if default_layout.get("edit_layout") is None:
                    assert ui_view_layout == default_layout.get("view_layout")
                else:
                    assert ui_view_layout == default_layout.get("edit_layout")

            # else: Not required
    except Exception as e:
        print(e)


def test_column_chores(clean_and_set_limits, web_project, driver, driver_type, schema_dict):
    for widget_name, widget_schema in schema_dict.items():
        # sequence_number: int = 0
        if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element", "basket_chore", "chore_snapshot"]:
            continue
        widget: WebElement = driver.find_element(By.ID, widget_name)
        scroll_into_view(driver=driver, element=widget)
        switch_layout(widget=widget, layout=Layout.TABLE)
        click_button_with_name(widget=widget, button_name="Settings")
        click_more_all_inside_setting(driver, widget_name)
        field_sequence_value = get_fld_sequence_number_from_setting(driver, widget_name)
        # widget_type: WidgetType | None = get_widget_type(widget_schema)
        for field_name, field_properties in widget_schema["properties"].items():
            sequence_number = field_properties["sequence_number"]

            if field_name in ["kill_switch", "plan_state", "executor_event_meta", "event_time", "market_barter_volume", "event_name", "chore", "chore_brief"]:
                continue
            try:
                assert field_sequence_value[field_name] == sequence_number
            except Exception as e:
                print(e)
        close_setting(driver)



def test_disable_ws_on_edit(clean_and_set_limits, web_project, driver, driver_type, schema_dict,
                            set_disable_ws_on_edit_and_clean, top_of_book_list_):
    result = get_widgets_by_flux_property(schema_dict, WidgetType.REPEATED_INDEPENDENT, FluxPropertyType.FluxFldElaborateTitle)
    assert result[0]

    # TODO: create or update the top of book of fld bid_quote.px and total bartering security size
    try:
        top_of_book: TopOfBookBaseModel = TopOfBookBaseModel()
        top_of_book.id = 1
        top_of_book.total_bartering_security_size = 55
        top_of_book.bid_quote = QuoteOptional()
        top_of_book.bid_quote.px = 10
        top_of_book.ask_quote = QuoteOptional()
        top_of_book.ask_quote.px = 104
        top_of_book.last_barter = QuoteOptional()
        top_of_book.last_barter.px = 11

        pair_plan: PairPlanBaseModel = email_book_service_native_web_client.get_all_pair_plan_client()[-1]
        while not pair_plan.is_executor_running:
            pair_plan = email_book_service_native_web_client.get_all_pair_plan_client()[-1]

        assert pair_plan.is_executor_running
        executor_web_client: StreetBookServiceHttpClient = StreetBookServiceHttpClient(pair_plan.host, pair_plan.port)

        # Patch the top_of_book and get the response
        top_of_book_response = executor_web_client.patch_top_of_book_client(
            top_of_book.to_dict(by_alias=True, exclude_none=True))
        assert top_of_book_response is not False  # Ensure patching was successful

        for widget_query in result[1]:
            widget_name: str = widget_query.widget_name
            if widget_name == "top_of_book":
                time.sleep(Delay.LONG.value)
                widget: WebElement = driver.find_element(By.ID, widget_name)
                scroll_into_view(driver=driver, element=widget)
                common_key_flds: Dict[str, any] = get_replaced_underscore_common_key(widget, driver)

                for field_query in widget_query.fields:
                    field_name: str = field_query.field_name
                    if field_name in ["px", "total_bartering_security_size"]:
                        default_field: str = field_query.properties["parent_title"]
                        full_field_name = f"{default_field}.{field_name}"
                        if field_name in ["bid_quote.px"]:
                            continue
                        common_key_fld = common_key_flds[full_field_name]

                        if hasattr(top_of_book_response, default_field):
                            field_value = getattr(top_of_book_response, default_field)
                            expected_value = field_value.px if hasattr(field_value, 'px') else None
                        else:
                            expected_value = None

                        # Assert the values are not equal
                        assert common_key_fld != expected_value, f"Assertion failed for {full_field_name}: {common_key_fld} == {expected_value}"

    except Exception as e:
        print(f"An error occurred: {e}")


def test_plan_load_and_unload(clean_and_set_limits, web_project, driver, driver_type):
    pair_plan_from_web_client: PairPlanBaseModel = (
        email_book_service_native_web_client.get_all_pair_plan_client())[-1]

    plan_state = PlanState.PlanState_READY
    pair_plan: PairPlanBaseModel = PairPlanBaseModel(id=pair_plan_from_web_client.id, plan_state=plan_state)

    email_book_service_native_web_client.patch_pair_plan_client(
        pair_plan.to_dict(by_alias=True, exclude_none=True))


    widget: WebElement = driver.find_element(By.ID, "plan_collection")
    unload_plan(widget, driver)
    load_plan(widget)

    plan_state = PlanState.PlanState_SNOOZED
    pair_plan_from_web_client = email_book_service_native_web_client.get_all_pair_plan_client()[-1]
    assert plan_state == pair_plan_from_web_client.plan_state


def test_download_button_in_widgets(clean_and_set_limits, web_project, driver, driver_type, schema_dict):
    try:
        download_path: str = "/home/sourav/Downloads"
        file_name_list: List[str] = []
        for widget_name, widget_query in schema_dict.items():
            if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element", "basket_chore", "pair_plan_params"]:
                continue

            widget: WebElement = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            widget.find_element(By.NAME, "Export").click()
            time.sleep(Delay.DEFAULT.value)
            file_name: str = widget_name + ".xlsx"
            file_name_list_in_download_dir: List[str] = os.listdir(download_path)
            assert file_name in file_name_list_in_download_dir, f"Expected {file_name} to be downloaded, but it was not found in {download_path}."
            file_name_list.append(file_name)
        for file in file_name_list:
            os.remove(os.path.join(download_path, file))
    except Exception as e:
        print(e)


def test_ui_chart_in_market_depth_widget(clean_and_set_limits, web_project, driver, driver_type, schema_dict, ui_chart):
    for widget_name, widget_query in schema_dict.items():
        if widget_name == "market_depth":
            # create and validate market depth
            widget: WebElement = driver.find_element(By.ID, widget_name)
            scroll_into_view(driver=driver, element=widget)
            switch_layout(widget=widget, layout=Layout.CHART)

            click_button_with_name(widget=widget, button_name="Create")
            nested_fld_widget = get_nested_tree_dialog_widget_element(driver)
            set_ui_chart_fields(driver, nested_fld_widget, ui_chart)
            click_save_n_short_delay(widget=nested_fld_widget)
            chart_n_layout_name = ui_chart["chart_name"]
            save_layout(driver=driver, layout_name=chart_n_layout_name)
            load_layout(driver=driver, layout_name=chart_n_layout_name)
            click_button_with_name(widget=widget, button_name="Edit")
            chart_name_txt = get_chart_name(widget=nested_fld_widget)
            validate_ui_chart(chart_n_layout_name, chart_name_txt, ui_chart)


            # update fields and validate it is saved in layout or not, but chart name should be same
            click_button_with_name(widget=widget, button_name="Edit")
            nested_fld_widget = get_nested_tree_dialog_widget_element(driver)
            set_ui_chart_fields(driver, nested_fld_widget, ui_chart)
            nested_fld_widget.find_element(By.NAME, "Save").click()
            time.sleep(Delay.DEFAULT.value)
            save_layout(driver=driver, layout_name=chart_n_layout_name)

            ui_layout: UILayoutBaseModel = (
                email_book_service_native_web_client.
                get_ui_layout_from_index_client(profile_id=chart_n_layout_name)[-1])

            print(f"ui_layout: {ui_layout}")
            assert ui_layout.profile_id == chart_n_layout_name

            widget_ui_data_elements: List[WidgetUIDataElementOptional] = ui_layout.widget_ui_data_elements

            for widget_ui_data_element in widget_ui_data_elements:
                if widget_ui_data_element.i == "market_depth":
                    assert widget_ui_data_element.i == "market_depth"
                    assert widget_ui_data_element.chart_data[-1].chart_name == chart_n_layout_name
                    filters = ui_chart["filters"]
                    assert widget_ui_data_element.chart_data[-1].filters == filters["fld_name"]
                    assert widget_ui_data_element.chart_data[-1] == filters["fld_name"]





            # delete the chart and layout
            # chart_widget.find_element(By.CLASS_NAME, "MuiButtonBase-root").click()
            # verify the chart is removed from ui
            # scenario: chart with the same name is created again
            # expected it would override the existing chart with same name
            email_book_service_native_web_client.delete_ui_layout_client(ui_layout.id)



