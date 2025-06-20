import pytest
from selenium.webdriver.support import expected_conditions as EC  # noqa

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_client import (
    EmailBookServiceHttpClient)
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import \
    fx_symbol_overview_obj
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.utility_test_functions import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.utility_test_functions import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.web_ui.web_ui_models import *


@pytest.fixture()
def market_depth_basemodel_fixture() -> List[MarketDepthBaseModel]:
    input_data = []

    for symbol in ["Type1_Sec_1", "Type2_Sec_1"]:
        for side, px, qty, dev in [("BID", 100, 90, -1), ("ASK", 110, 70, 1)]:
            for position in range(1, 6):
                id_value = len(input_data) + 1  # Using the length of input_data as id
                input_data.extend([
                    {
                        "id": id_value,
                        "symbol": symbol,
                        "exch_time":pendulum.DateTime.utcnow(),
                        "arrival_time":pendulum.DateTime.utcnow(),
                        "side": side,
                        "px": random.uniform(10.0, 10000.0),
                        "qty": random.randint(10, 1000),
                        "position": position,
                        "market_maker": "string",
                        "is_smart_depth": False,
                        "cumulative_notional": 2224.5,
                        "cumulative_qty": 555,
                        "cumulative_avg_px": 44.4

                    }
                ])

    market_depth_basemodel_list = [MarketDepthBaseModel(**market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def last_barter_basemodel_fixture() -> List[LastBarterBaseModel]:
    input_data = []
    id: int = 0

    for symbol in ["Type1_Sec_1", "Type2_Sec_1"]:
        id += 1
        symbol_n_exch_id = SymbolNExchIdBaseModel(symbol=symbol, exch_id="Exch")
        market_barter_volume = MarketBarterVolumeBaseModel(id=str(id),
            participation_period_last_barter_qty_sum=33,
            applicable_period_seconds=22
        )

        input_data.append(
            LastBarterBaseModel(
                id=id,
                symbol_n_exch_id=symbol_n_exch_id,
                exch_time=pendulum.DateTime.utcnow(),
                arrival_time=pendulum.DateTime.utcnow(),
                px=1.16,
                qty=150,
                premium=1.5,
                market_barter_volume=market_barter_volume
            )
        )

    yield input_data


@pytest.fixture()
def deals_ledger_basemodel_fixture() -> List[DealsLedgerBaseModel]:
    input_data: List[DealsLedgerBaseModel] = []
    id_counter: int = 0

    for symbol in ["Type1_Sec_1", "Type2_Sec_1"]:
        for _ in range(5):
            id_counter += 1
            input_data.append(
                DealsLedgerBaseModel(
                    id=id_counter,
                    chore_id=f"Chore_{str(id_counter)}",
                    fill_px=120.5 + id_counter,
                    fill_qty=100 + id_counter,
                    fill_notional=1.4 + id_counter,
                    fill_symbol=symbol,
                    fill_bartering_symbol=symbol,
                    fill_side=Side.BUY,
                    underlying_account=f"Account_{id_counter}",
                    fill_date_time=pendulum.DateTime.utcnow(),
                    fill_id=f"FillID_{id_counter}",
                    underlying_account_cumulative_fill_qty=500 + id_counter,
                    user_data="random"
                )
            )
    yield input_data

@pytest.fixture()
def symbol_side_snapshot_fixture():
    yield SymbolSideSnapshotBaseModel(
        id=1,
        security=None,
        side=Side.BUY,
        avg_px=12.6,
        total_qty=100,
        total_filled_qty=100,
        avg_fill_px= 7.5,
    total_fill_notional= 8.5,
    last_update_fill_qty= 10,
    last_update_fill_px= 10.5,
    total_cxled_qty= 100,
    avg_cxled_px= 1.1,
    total_cxled_notional= 56.6,
    last_update_date_time= pendulum.DateTime,
    chore_count= 1,
    )


@pytest.fixture()
def plan_limits_fixture(expected_brokers_) -> List[PlanLimitsBaseModel]:
    input_data: List[PlanLimitsBaseModel] = []
    # Create PlanLimitsBaseModel with eligible_brokers and append to input_data
    plan_limit_obj = PlanLimitsBaseModel(eligible_brokers=expected_brokers_)
    input_data.append(plan_limit_obj)
    yield input_data


@pytest.fixture()
def chore_ledger_basemodel_fixture() -> List[ChoreLedgerBaseModel]:
    input_data = []
    id_counter: int = 0

    for symbol in ["Type1_Sec_1", "Type2_Sec_1"]:
        for _ in range(5):  # Adjust the range as needed
            id_counter += 1
            input_data.append(
                ChoreLedgerBaseModel(
                    id=id_counter,
                    chore=ChoreBriefBaseModel(
                        chore_id=f"Chore_{id_counter}",
                        security=SecurityBaseModel(
                            sec_id=symbol, sec_id_source=SecurityIdSource.SEC_ID_SOURCE_UNSPECIFIED, inst_type=InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED),
                        bartering_security=SecurityBaseModel(
                            sec_id=symbol, sec_id_source=SecurityIdSource.SEC_ID_SOURCE_UNSPECIFIED, inst_type=InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED),
                        side=Side.BUY,
                        px=120.5 + id_counter,
                        qty=100 + id_counter,
                        chore_notional=12.5 + id_counter,
                        underlying_account=f"Account_{id_counter}",
                        exchange="Exchange123",
                        text=["Text1", "Text2"],
                        user_data="random"
                    ),
                    chore_event_date_time=pendulum.DateTime.utcnow(),
                    chore_event=ChoreEventType.OE_ACK,
                    current_period_chore_count=10
                )
            )

    yield input_data


@pytest.fixture()
def chore_snapshot_basemodel_fixture() -> list[ChoreSnapshotBaseModel]:
    input_data = []
    id_counter: int = 0
    for i in range(5):
        id_counter += 1
        input_data.append(
            ChoreSnapshotBaseModel(
                id=id_counter,
                chore_status=ChoreStatusType.OE_ACKED,
                chore_brief=ChoreBriefBaseModel(
                    chore_id=f"Chore_{id_counter}",
                    side=Side.BUY,
                    px=50.0,
                    qty=100,
                    chore_notional=15.0,
                    underlying_account="GlobalEquity_Account",
                    exchange="SELL",
                    text=["text1", "text2"],
                    user_data="none",
                    security=SecurityBaseModel(
                        sec_id=str(id_counter),
                        sec_id_source=SecurityIdSource.SEC_ID_SOURCE_UNSPECIFIED,
                        inst_type=InstrumentType.EQT),
                    bartering_security=SecurityBaseModel(
                            sec_id=str(id_counter),
                            sec_id_source=SecurityIdSource.RIC,
                            inst_type=InstrumentType.EQT)
                ),

                filled_qty=50,
                avg_fill_px=50.0,
                fill_notional=10,
                last_update_fill_qty=100,
                last_update_fill_px=10.0,
                pending_amend_dn_qty=150,
                pending_amend_up_qty=200,
                pending_amend_dn_px=20.0,
                pending_amend_up_px=25.0,
                total_amend_dn_qty=300,
                total_amend_up_qty=350,
                last_lapsed_qty=400,
                total_lapsed_qty=450,
                total_amd_rej_qty=500,
                cxled_qty=550,
                avg_cxled_px=60.0,
                cxled_notional=65.0,
                create_date_time=pendulum.DateTime.utcnow(),
                last_update_date_time=pendulum.DateTime.utcnow(),
                last_n_sec_total_qty=700
            )
        )

    yield input_data


@pytest.fixture()
def top_of_book_fixture() -> List:
    input_data = []
    id: int = 0
    for index, symbol in enumerate(["Type1_Sec_1", "Type2_Sec_1"]):
        id += 1
        input_data.extend([
            {
                "id": id,
                "symbol": symbol,
                "bid_quote": {
                    "px": 1.11,
                    "qty": 20,
                    "premium": 5.22,
                    "last_update_date_time": "2023-02-13T20:30:33.165Z"
                },
                "ask_quote": {
                    "px": 1.22,
                    "qty": 40,
                    "premium": 9.23,
                    "last_update_date_time": "2023-02-13T20:30:31.165Z"
                },
                "last_barter": {
                    "px": 1.16,
                    "qty": 150,
                    "premium": 44.23,
                    "last_update_date_time": "2023-02-13T20:30:35.165Z"
                },
                "total_bartering_security_size": 100,
                "market_barter_volume": [
                    {
                        "participation_period_last_barter_qty_sum": 90,
                        "applicable_period_seconds": 180
                    }
                ],
                "last_update_date_time": "2023-02-13T20:30:34.165Z"
            }

        ])

    yield input_data


@pytest.fixture()
def expected_chore_limits_() -> ChoreLimitsBaseModel:
    yield ChoreLimitsBaseModel(id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                               max_chore_qty=500, max_contract_qty=0, max_chore_notional=0.0, max_basis_points_algo=0,
                               max_px_deviation_algo=0.0,
                               max_chore_notional_algo=0.0, max_contract_qty_algo=0, max_chore_qty_algo=0)


@pytest.fixture()
def expected_contact_limits_(expected_brokers_) -> ContactLimitsBaseModel:
    rolling_max_chore_count = RollingMaxChoreCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxChoreCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    # max_accounts_nett_notional = ContactLimitsBaseModel(accounts_nett_notional=44.3)
    # max_accounts_nett_notional_list = [max_accounts_nett_notional]

    contact_limits_obj = ContactLimitsBaseModel(
        id=1,
        max_accounts_nett_notional=[
            AccountsNettNotionalBaseModel(
                accounts_nett_notional=44.6,
                chore_accounts=[ChoreAccountBaseModel(chore_account="chore_acc")]
            )
        ],
        max_open_baskets=20,
        max_open_notional_per_side=100_000,
        max_gross_n_open_notional=2_400_000,
        rolling_max_chore_count=rolling_max_chore_count,
        rolling_max_reject_count=rolling_max_reject_count,
        eligible_brokers=expected_brokers_,
    )

    yield contact_limits_obj


@pytest.fixture()
def expected_contact_status_() -> ContactStatusBaseModel:
    yield ContactStatusBaseModel(**{
        "overall_buy_notional": 0,
        "overall_sell_notional": 0,
        "overall_buy_fill_notional": 0,
        "overall_sell_fill_notional": 0,
        "open_chores": 0
    })


@pytest.fixture
def db_names_list(buy_sell_symbol_list) -> List:
    db_names_list = [
        f"phone_book_{PAIR_STRAT_BEANIE_PORT}",
        f"log_book_{LOG_ANALYZER_BEANIE_PORT}",
    ]

    for i in range(len(buy_sell_symbol_list)):
        db_names_list.append(f"street_book_{8040 + i + 1}")
    return db_names_list


@pytest.fixture()
def expected_brokers_(buy_sell_symbol_list) -> List[Broker]:
    sec_positions: List[SecPosition] = []
    for buy_symbol, sell_symbol in buy_sell_symbol_list:
        cb_sec_position: SecPosition = SecPosition(security=Security(sec_id=buy_symbol, sec_id_source=SecurityIdSource.SEDOL), figi="figi1")
        cb_positions: List[Position] = [Position(type=PositionType.SOD, priority=0, available_size=10_000,
                                                 allocated_size=10_000, consumed_size=0)]
        cb_sec_position.positions = cb_positions
        sec_positions.append(cb_sec_position)
        eqt_sec_position: SecPosition = SecPosition(security=Security(sec_id=f"{sell_symbol}.SS",
                                                                      sec_id_source=SecurityIdSource.RIC))
        eqt_positions: List[Position] = [
            Position(type=PositionType.SOD, priority=0, available_size=10_000, allocated_size=10_000, consumed_size=0),
            Position(type=PositionType.LOCATE, priority=1, available_size=10_000, allocated_size=10_000,
                     consumed_size=0),
            Position(type=PositionType.PTH, priority=2, available_size=10_000, allocated_size=10_000, consumed_size=0)
        ]
        eqt_sec_position.positions = eqt_positions
        sec_positions.append(eqt_sec_position)
    broker: Broker = Broker(broker="BKR", bkr_priority=10, sec_positions=sec_positions)
    yield [broker]


@pytest.fixture()
def buy_sell_symbol_list() -> List:
    return [
        ("Type1_Sec_1", "Type2_Sec_1"),
        ("Type1_Sec_2", "Type2_Sec_2"),
        ("Type1_Sec_3", "Type2_Sec_3"),
        ("Type1_Sec_4", "Type2_Sec_4"),
        ("Type1_Sec_5", "Type2_Sec_5"),
        ("Type1_Sec_6", "Type2_Sec_6"),
        ("Type1_Sec_7", "Type2_Sec_7"),
        ("Type1_Sec_8", "Type2_Sec_8"),
        ("Type1_Sec_9", "Type2_Sec_9"),
        ("Type1_Sec_10", "Type2_Sec_10")
    ]


@pytest.fixture
def clean_and_set_limits(expected_chore_limits_, expected_contact_limits_, expected_contact_status_,
                         db_names_list):

    # # deleting existing data available in existing executor client
    # delete_tob_md_ld_fj_os_oj()

    # deleting existing executors
    clean_executors_and_today_activated_symbol_side_lock_file()

    # cleaning all collections
    clean_all_collections_ignoring_ui_layout()
    clear_cache_in_model()

    # updating contact_alert
    clean_log_book_alerts()

    # setting limits
    set_n_verify_limits(expected_chore_limits_, expected_contact_limits_)

    # creating contact_status
    create_n_verify_contact_status(copy.deepcopy(expected_contact_status_))

    # creating fx_symbol_overview
    create_fx_symbol_overview()

    # time for override get refreshed
    min_refresh_interval = ps_config_yaml_dict.get("min_refresh_interval")
    if min_refresh_interval is None:
        min_refresh_interval = 30
    time.sleep(min_refresh_interval)


@pytest.fixture(scope="session")
def schema_dict():
    schema_path: PurePath = project_dir_path / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "r") as f:
        schema_dict: Dict[str, any] = json.loads(f.read())
    yield schema_dict


@pytest.fixture()
def config_dict() -> Dict[str, any]:
    config_dict: dict[str, any] = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
    yield config_dict


@pytest.fixture()
def driver_type(request):
    driver_type: DriverType = request.param
    yield driver_type


@pytest.fixture()
def driver(driver_type, config_dict: Dict[str, any]) -> WebDriver:
    driver: WebDriver = get_driver(config_dict=config_dict, driver_type=driver_type)
    yield driver
    driver.quit()


@pytest.fixture()
def web_project(driver: WebDriver, pair_plan: Dict, expected_chore_limits_: ChoreLimitsBaseModel,
                expected_contact_limits_: ContactLimitsBaseModel, top_of_book_fixture: List,
                market_depth_basemodel_fixture: List[MarketDepthBaseModel],
                last_barter_basemodel_fixture: List[LastBarterBaseModel],
                deals_ledger_basemodel_fixture: List[DealsLedgerBaseModel],
                chore_snapshot_basemodel_fixture: List[ChoreSnapshotBaseModel],
                chore_ledger_basemodel_fixture: List[ChoreLedgerBaseModel],
                symbol_side_snapshot_fixture: SymbolSideSnapshotBaseModel,
                plan_limits_fixture: PlanLimitsBaseModel, expected_pair_plan: Dict[str, any], basket_chore):

    host: str = "127.0.0.1"
    port: int = 8020
    email_book_service_http_client = EmailBookServiceHttpClient(host, port)
    fx_symbol_overview = fx_symbol_overview_obj()
    email_book_service_http_client.create_fx_symbol_overview_client(fx_symbol_overview)

    override_default_limits(expected_chore_limits_, expected_contact_limits_)
    driver.maximize_window()
    time.sleep(Delay.SHORT.value)
    driver.get(get_web_project_url())
    # verify is contact status is created
    time.sleep(Delay.DEFAULT.value)
    # wait(driver).until(EC.presence_of_element_located((By.ID, "contact_status")))
    # contact_status_widget = driver.find_element(By.ID, "contact_status")
    # scroll_into_view(driver=driver, element=contact_status_widget)
    # wait(driver).until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    # kill_switch_btn = contact_status_widget.find_element(By.NAME, "kill_switch")


    wait(driver, Delay.LONG.value).until(EC.presence_of_element_located((By.ID, "system_control")))
    widget = driver.find_element(By.ID, "system_control")
    scroll_into_view(driver=driver, element=widget)
    click_button_with_name(widget=widget, button_name="Create")
    wait(driver, Delay.LONG.value).until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    kill_switch_btn = widget.find_element(By.NAME, "kill_switch")
    assert kill_switch_btn.is_displayed(), "failed to load web project, kill switch button not found"
    create_pair_plan(driver=driver, pair_plan=pair_plan, expected_pair_plan=expected_pair_plan)
    create_tob_md_ld_fj_os_oj(driver=driver, top_of_book_fixture=top_of_book_fixture,
                              market_depth_basemodel_fixture=market_depth_basemodel_fixture,
                              last_barter_basemodel_fixture=last_barter_basemodel_fixture,
                              deals_ledger_basemodel_fixture=deals_ledger_basemodel_fixture,
                              chore_snapshot_basemodel_fixture=chore_snapshot_basemodel_fixture,
                              chore_ledger_basemodel_fixture=chore_ledger_basemodel_fixture,
                              plan_limits_fixture=plan_limits_fixture)

@pytest.fixture()
def pair_plan() -> Dict[str, any]:
    pair_plan = {
        "pair_plan_params": {
            "plan_leg1": {
                "sec": {
                    "sec_id": "Type1_Sec_1"
                },
                "side": "BUY"
            },
            "plan_leg2": {
                "sec": {
                    "sec_id": "Type2_Sec_1"
                }
            },
            "common_premium": 3
        }
    }
    return pair_plan



@pytest.fixture()
def expected_pair_plan(pair_plan) -> Dict[str, any]:
    pair_plan_params = pair_plan["pair_plan_params"]

    expected_pair_plan= {
        "pair_plan_params.plan_leg1.sec.sec_id": pair_plan_params["plan_leg1"]["sec"]["sec_id"],
        "pair_plan_params.plan_leg1.side": pair_plan_params["plan_leg1"]["side"],
        "pair_plan_params.plan_leg2.sec.sec_id": pair_plan_params["plan_leg2"]["sec"]["sec_id"],
        "pair_plan_params.common_premium": pair_plan_params["common_premium"]
    }
    return expected_pair_plan


@pytest.fixture()
def plan_brief_fixture() -> Dict[str, any]:
    pair_plan_edit = {
        "pair_plan_params": {
            "common_premium": 55,
            "hedge_ratio": 60
        }
    }
    yield pair_plan_edit


@pytest.fixture()
def pair_plan_edit() -> Dict[str, any]:
    pair_plan_edit = {
        "pair_plan_params": {
            "common_premium": 55,
            "hedge_ratio": 60
        }
    }
    yield pair_plan_edit


@pytest.fixture()
def plan_limits() -> Dict[str, any]:
    plan_limits = {
        "max_open_chores_per_side": 4,
        "max_single_leg_notional": 500,
        "max_open_single_leg_notional": 600,
        "max_net_filled_notional": 700,
        "max_concentration": 7,
        "min_chore_notional": 1000,
        "limit_up_down_volume_participation_rate": 20,
        "cancel_rate": {
            "max_cancel_rate": 10,
            "applicable_period_seconds": 9,
            "waived_initial_chores": 120,
            "waived_min_rolling_notional": 240,
            "waived_min_rolling_period_seconds": 360,
        },
        "market_barter_volume_participation": {
            "max_participation_rate": 15,
            "applicable_period_seconds": 25,
            "min_allowed_notional": 30
        },
        "market_depth": {
            "participation_rate": 90,
            "depth_levels": 18
        },
        "residual_restriction": {
            "max_residual": 4000,
            "residual_mark_seconds": 1,
        }
    }
    yield plan_limits


@pytest.fixture
def set_micro_seperator_and_clean(schema_dict: Dict[str, any]):
    update_schema_json(schema_dict=copy.deepcopy(schema_dict), project_name="phone_book",
                       update_widget_name="plan_collection", update_field_name="loaded_plan_keys",
                       extend_field_name="micro_separator", value="=")
    yield

    schema_path: PurePath = (code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" /
                             "phone_book" / "web-ui" / "public" / "schema.json")
    with open(str(schema_path), "w") as file:
        json.dump(schema_dict, file, indent=2)


@pytest.fixture
def ui_layout_list_(schema_dict) -> UILayoutBaseModel:
    # Create an instance of UILayoutBaseModel with required fields
    ui_layout: UILayoutBaseModel = UILayoutBaseModel(
        id=1,
        profile_id="test",
        theme=Theme.THEME_DARK,
        widget_ui_data_elements=[]
    )

    for widget_name, widget_schema in schema_dict.items():
        # Skip specific widget names
        if widget_name in ["definitions", "autocomplete", "ui_layout", "basket_chore"]:
            continue

        widget_ui_data_element = widget_schema.get("widget_ui_data_element")

        # Create a new WidgetUIDataElementBaseModel instance
        widget_ui_data_element = WidgetUIDataElementBaseModel(
            i=widget_name,
            x=widget_ui_data_element.get("x"), # Default to 0 if not found
            y = widget_ui_data_element.get("y"),
            w = widget_ui_data_element.get("w"),
            h = widget_ui_data_element.get("h"),
            is_repeated = widget_ui_data_element.get("is_repeated"),
            alert_bubble_source=widget_ui_data_element.get("alert_bubble_source"),
            alert_bubble_color=widget_ui_data_element.get("alert_bubble_color"),
            disable_ws_on_edit=widget_ui_data_element.get("disable_ws_on_edit"),
            bind_id_fld=widget_ui_data_element.get("bind_id_fld"),
            dynamic_widget_title_fld=widget_ui_data_element.get("dynamic_widget_title_fld"),
            widget_ui_data=widget_ui_data_element.get("widget_ui_data"),
            chart_data=widget_ui_data_element.get("chart_data"),
            filters=widget_ui_data_element.get("filters"),
            depending_proto_file_name=widget_ui_data_element.get("depending_proto_file_name"),
            depending_proto_model_name=widget_ui_data_element.get("depending_proto_model_name"),
            depends_on_other_model_for_id=widget_ui_data_element.get("depends_on_other_model_for_id"),
            depends_on_other_model_for_dynamic_url=widget_ui_data_element.get("depends_on_other_model_for_dynamic_url"),
            depends_on_model_name_for_port=widget_ui_data_element.get("depends_on_model_name_for_port"),
            override_default_crud=widget_ui_data_element.get("override_default_crud"),
            is_model_alert_type=widget_ui_data_element.get("is_model_alert_type"),
            join_sort=widget_ui_data_element.get("join_sort"),
            is_read_only=widget_ui_data_element.get("is_read_only"),
        )

        # Append the widget data element to the layout
        ui_layout.widget_ui_data_elements.append(widget_ui_data_element)

    yield ui_layout



@pytest.fixture
def set_disable_ws_on_edit_and_clean(schema_dict: Dict[str, any]):
    update_schema_json(schema_dict=copy.deepcopy(schema_dict), project_name="phone_book",
                       update_widget_name="top_of_book", update_field_name="widget_ui_data_element",
                       extend_field_name="disable_ws_on_edit", value=True)
    yield

    schema_path: PurePath = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup"/ "phone_book" / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "w") as file:
        json.dump(schema_dict, file, indent=2)


@pytest.fixture
def expected_chart():
    # Directly yield the list of expected chart fields
    yield ["_id", "symbol", "exch_time", "arrival_time", "side", "px", "qty", "position",
           "market_maker", "is_smart_depth", "cumulative_notional", "cumulative_qty", "cumulative_avg_px"]



@pytest.fixture
def ui_chart(expected_chart):
    ui_chart = {
        "chart_data":{
            "chart_name": "test",
        },
        "filters":{
            "fld_name": expected_chart,  # Use the list of expected fields directly
            "partition_fld": ["symbol", "market_maker"],
            "fld_value": ["123","4423"]
        },
        "series": {
            "type": ["bar", "line", "scatter"],
        },
        "encode":{
            "x": expected_chart,  # Use expected_chart list for x-axis
            "y": expected_chart,  # Use expected_chart list for y-axis
        }
    }
    yield ui_chart




@pytest.fixture
def basket_chore():
    new_chore_list: List[NewChoreBaseModel] = []
    for _ in range(5):
        sec_id = f"Type1_Sec_{random.randint(1, 10)}"
        side = random.choice([Side.BUY, Side.SELL])
        px = random.randint(90, 100)
        qty = random.randint(80, 90)
        security = SecurityOptional(sec_id=sec_id, sec_id_source=SecurityIdSource.TICKER)
        new_chore_obj = NewChoreBaseModel(security=security, side=side, px=px, qty=qty)
        new_chore_list.append(new_chore_obj)

    yield BasketChoreBaseModel(id = 1, new_chores=new_chore_list)


