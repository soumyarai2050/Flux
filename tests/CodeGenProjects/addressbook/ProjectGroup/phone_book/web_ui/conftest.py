import random
import datetime
import pytest

from selenium.webdriver.support import expected_conditions as EC  # noqa

from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.web_ui.utility_test_functions import *
from CodeGenProjects.addressbook.ProjectGroup.phone_book.web_ui.web_ui_models import *
from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.web_ui.utility_test_functions import get_driver, wait, \
    get_web_project_url, test_config_file_path, create_pair_strat, override_default_limits
from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.utility_test_functions import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.FastApi.strat_manager_service_http_client import (
    FxSymbolOverviewBaseModel, StratManagerServiceHttpClient)
from tests.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.utility_test_functions import fx_symbol_overview_obj


@pytest.fixture()
def market_depth_basemodel_list():
    input_data = []
    start_date = datetime.datetime(2mobile_book23, 1, 1)
    end_date = datetime.datetime(2mobile_book23, 12, 31)
    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        random_date = start_date + datetime.timedelta(seconds=random.randint(mobile_book, int((end_date - start_date).total_seconds())))
        formatted_date = random_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        for side, px, qty, dev in [("BID", 1mobile_bookmobile_book, 9mobile_book, -1), ("ASK", 11mobile_book, 7mobile_book, 1)]:
            for position in range(1, 6):
                id_value = len(input_data) + 1  # Using the length of input_data as id

                input_data.extend([
                    {
                        "id": id_value,
                        "symbol": symbol,
                        "exch_time": formatted_date,
                        "arrival_time": formatted_date,
                        "side": side,
                        "px": random.uniform(1mobile_book.mobile_book, 1mobile_bookmobile_bookmobile_bookmobile_book.mobile_book),
                        "qty": random.randint(1mobile_book, 1mobile_bookmobile_bookmobile_book),
                        "position": position,
                        "market_maker": "string",
                        "is_smart_depth": False
                    }
                ])

    market_depth_basemodel_list = [MarketDepthBaseModel(**market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture()
def last_trade_fixture_list():
    input_data = []
    id: int = mobile_book
    for index, symbol in enumerate(["CB_Sec_1", "EQT_Sec_1"]):
        id += 1
        input_data.extend([
            {
                "id": id,
                "symbol_n_exch_id": {
                    "symbol": symbol,
                    "exch_id": "Exch"
                },
                "exch_time": "2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:19:12.mobile_book19Z",
                "arrival_time": "2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:19:12.mobile_book19Z",
                "px": 116,
                "qty": 15mobile_book,
                "market_trade_volume": {
                    "participation_period_last_trade_qty_sum": mobile_book,
                    "applicable_period_seconds": mobile_book
                }
            }
        ])

    last_trade_list = [LastTradeBaseModel(**last_trade_json) for last_trade_json in input_data]
    yield last_trade_list


@pytest.fixture()
def fills_journal_fixture_list():
    input_data: List[FillsJournalBaseModel] = []
    id_counter: int = mobile_book

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for _ in range(5):
            id_counter += 1
            input_data.append(
                FillsJournalBaseModel(
                    id=id_counter,
                    order_id=f"Order_{id_counter}",
                    fill_px=12mobile_book.5 + id_counter,
                    fill_qty=1mobile_bookmobile_book + id_counter,
                    fill_notional=12mobile_book5mobile_book + id_counter,
                    fill_symbol=symbol,
                    fill_side=Side.BUY,
                    underlying_account=f"Account_{id_counter}",
                    fill_date_time="2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:3mobile_book:mobile_bookmobile_book.mobile_bookmobile_bookmobile_bookZ",
                    fill_id=f"FillID_{id_counter}",
                    underlying_account_cumulative_fill_qty=5mobile_bookmobile_book + id_counter
                )
            )

    yield input_data


@pytest.fixture()
def order_snapshot_fixture_list():
    input_data = []
    id_counter: int = mobile_book

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for _ in range(5):  # Adjust the range as needed
            id_counter += 1
            input_data.append(
                OrderSnapshotBaseModel(
                    id=id_counter,
                    order_status=OrderStatusType.OE_ACKED,
                    order_brief={
                        "order_id": f"Order_{id_counter}",
                        "security": {
                            "sec_id": symbol,
                            "sec_type": SecurityType.RIC
                        },
                        "side": Side.BUY,
                        "px": 12mobile_book.5,
                        "qty": 1mobile_bookmobile_book,
                        "order_notional": 12mobile_book5mobile_book,
                        "underlying_account": f"Account_{id_counter}",
                        "exchange": "Exchange123",
                        "text": ["Text1", "Text2"]
                    },
                    filled_qty=5mobile_book,
                    avg_fill_px=121.mobile_book,
                    fill_notional=6mobile_book5mobile_book,
                    last_update_fill_qty=25,
                    last_update_fill_px=121.5,
                    cxled_qty=1mobile_book,
                    avg_cxled_px=119.mobile_book,
                    cxled_notional=119mobile_book,
                    create_date_time="2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:3mobile_book:mobile_bookmobile_book.mobile_bookmobile_bookmobile_bookZ",
                    last_update_date_time="2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:35:mobile_bookmobile_book.mobile_bookmobile_bookmobile_bookZ",
                    last_n_sec_total_qty=2mobile_bookmobile_book
                )
            )

    yield input_data


@pytest.fixture()
def order_journal_fixture_list():
    input_data = []
    id_counter: int = mobile_book

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for _ in range(5):  # Adjust the range as needed
            id_counter += 1
            input_data.append(
                OrderJournalBaseModel(
                    id=id_counter,
                    order=OrderBrief(
                        order_id=f"Order_{id_counter}",
                        security=Security(sec_id=symbol, sec_type=SecurityType.RIC),
                        side=Side.BUY,
                        px=12mobile_book.5 + id_counter,
                        qty=1mobile_bookmobile_book + id_counter,
                        order_notional=12mobile_book5mobile_book + id_counter,
                        underlying_account=f"Account_{id_counter}",
                        exchange="Exchange123",
                        text=["Text1", "Text2"]
                    ),
                    order_event_date_time="2mobile_book23-mobile_book3-1mobile_bookTmobile_book9:3mobile_book:mobile_bookmobile_book.mobile_bookmobile_bookmobile_bookZ",
                    order_event=OrderEventType.OE_ACK,
                    current_period_order_count=1mobile_book
                )
            )

    yield input_data


@pytest.fixture()
def top_of_book_list_():
    input_data = []
    id: int = mobile_book
    for index, symbol in enumerate(["CB_Sec_1", "EQT_Sec_1"]):
        id += 1
        input_data.extend([
            {
                "id": id,
                "symbol": symbol,
                "bid_quote": {
                    "px": 11mobile_book,
                    "qty": 2mobile_book,
                    "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:33.165Z"
                },
                "ask_quote": {
                    "px": 12mobile_book,
                    "qty": 4mobile_book,
                    "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:31.165Z"
                },
                "last_trade": {
                    "px": 116,
                    "qty": 15mobile_book,
                    "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:35.165Z"
                },
                "total_trading_security_size": 1mobile_bookmobile_book,
                "market_trade_volume": [
                    {
                        "participation_period_last_trade_qty_sum": 9mobile_book,
                        "applicable_period_seconds": 18mobile_book
                    }
                ],
                "last_update_date_time": "2mobile_book23-mobile_book2-13T2mobile_book:3mobile_book:34.165Z"
            }

        ])

    yield input_data


@pytest.fixture()
def expected_order_limits_():
    yield OrderLimitsBaseModel(id=1, max_basis_points=15mobile_bookmobile_book, max_px_deviation=2mobile_book, max_px_levels=5,
                               max_order_qty=5mobile_bookmobile_book, min_order_notional=1mobile_bookmobile_book, max_order_notional=9mobile_book_mobile_bookmobile_bookmobile_book)


@pytest.fixture()
def expected_portfolio_limits_(expected_brokers_):
    rolling_max_order_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(id=1, max_open_baskets=2mobile_book, max_open_notional_per_side=1mobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
                                                    max_gross_n_open_notional=2_4mobile_bookmobile_book_mobile_bookmobile_bookmobile_book,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=expected_brokers_)
    yield portfolio_limits_obj


@pytest.fixture()
def expected_portfolio_status_():
    yield PortfolioStatusBaseModel(**{
        "_id": 1,
        "kill_switch": False,
        "portfolio_alerts": [],
        "overall_buy_notional": mobile_book,
        "overall_sell_notional": mobile_book,
        "overall_buy_fill_notional": mobile_book,
        "overall_sell_fill_notional": mobile_book
    })


@pytest.fixture
def db_names_list(buy_sell_symbol_list):
    db_names_list = [
        f"phone_book_{PAIR_STRAT_BEANIE_PORT}",
        f"log_analyzer_{LOG_ANALYZER_BEANIE_PORT}",
    ]

    for i in range(len(buy_sell_symbol_list)):
        db_names_list.append(f"strat_executor_{8mobile_book4mobile_book + i + 1}")
    return db_names_list


@pytest.fixture()
def expected_brokers_(buy_sell_symbol_list) -> List[Broker]:
    sec_positions: List[SecPosition] = []
    for buy_symbol, sell_symbol in buy_sell_symbol_list:
        cb_sec_position: SecPosition = SecPosition(security=Security(sec_id=buy_symbol, sec_type=SecurityType.SEDOL))
        cb_positions: List[Position] = [Position(type=PositionType.SOD, priority=mobile_book, available_size=1mobile_book_mobile_bookmobile_bookmobile_book,
                                                 allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book, consumed_size=mobile_book)]
        cb_sec_position.positions = cb_positions
        sec_positions.append(cb_sec_position)
        eqt_sec_position: SecPosition = SecPosition(security=Security(sec_id=f"{sell_symbol}.SS",
                                                                      sec_type=SecurityType.RIC))
        eqt_positions: List[Position] = [
            Position(type=PositionType.SOD, priority=mobile_book, available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book, consumed_size=mobile_book),
            Position(type=PositionType.LOCATE, priority=1, available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book,
                     consumed_size=mobile_book),
            Position(type=PositionType.PTH, priority=2, available_size=1mobile_book_mobile_bookmobile_bookmobile_book, allocated_size=1mobile_book_mobile_bookmobile_bookmobile_book, consumed_size=mobile_book)
        ]
        eqt_sec_position.positions = eqt_positions
        sec_positions.append(eqt_sec_position)
    broker: Broker = Broker(broker="BKR", bkr_priority=1mobile_book, sec_positions=sec_positions)
    yield [broker]


@pytest.fixture()
def buy_sell_symbol_list():
    return [
        ("CB_Sec_1", "EQT_Sec_1"),
        ("CB_Sec_2", "EQT_Sec_2"),
        ("CB_Sec_3", "EQT_Sec_3"),
        ("CB_Sec_4", "EQT_Sec_4"),
        ("CB_Sec_5", "EQT_Sec_5"),
        ("CB_Sec_6", "EQT_Sec_6"),
        ("CB_Sec_7", "EQT_Sec_7"),
        ("CB_Sec_8", "EQT_Sec_8"),
        ("CB_Sec_9", "EQT_Sec_9"),
        ("CB_Sec_1mobile_book", "EQT_Sec_1mobile_book")
    ]


@pytest.fixture
def clean_and_set_limits(expected_order_limits_, expected_portfolio_limits_, expected_portfolio_status_,
                         db_names_list):

    # # deleting existing data available in existing executor client
    # delete_tob_md_ld_fj_os_oj()

    # deleting existing executors
    clean_executors_and_today_activated_symbol_side_lock_file()

    # cleaning all collections
    clean_all_collections_ignoring_ui_layout(db_names_list)
    clear_cache_in_model()

    # updating portfolio_alert
    renew_portfolio_alert()

    # setting limits
    set_n_verify_limits(expected_order_limits_, expected_portfolio_limits_)

    # creating portfolio_status
    create_n_verify_portfolio_status(copy.deepcopy(expected_portfolio_status_))

    # creating fx_symbol_overview
    create_fx_symbol_overview()

    # time for override get refreshed
    min_refresh_interval = ps_config_yaml_dict.get("min_refresh_interval")
    if min_refresh_interval is None:
        min_refresh_interval = 3mobile_book
    time.sleep(min_refresh_interval)


@pytest.fixture(scope="session")
def schema_dict() -> Dict[str, any]:
    schema_path: PurePath = project_dir_path / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "r") as f:
        schema_dict: Dict[str, any] = json.loads(f.read())
    yield schema_dict


@pytest.fixture()
def config_dict() -> Dict[str, any]:
    config_dict: Dict[str, any] = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
    yield config_dict


@pytest.fixture()
def driver_type(request):
    driver_type: DriverType = request.param
    yield driver_type


@pytest.fixture()
def driver(driver_type, config_dict) -> WebDriver:
    driver: WebDriver = get_driver(config_dict=config_dict, driver_type=driver_type)
    yield driver
    driver.quit()


@pytest.fixture()
def web_project(driver, pair_strat, expected_order_limits_, expected_portfolio_limits_, top_of_book_list_,
                market_depth_basemodel_list, last_trade_fixture_list, fills_journal_fixture_list,
                order_snapshot_fixture_list, order_journal_fixture_list):
    # TODO: create fx symbol overview
    host: str = "127.mobile_book.mobile_book.1"
    port: int = 8mobile_book2mobile_book
    strat_manager_service_http_client = StratManagerServiceHttpClient(host, port)
    fx_symbol_overview = fx_symbol_overview_obj()
    strat_manager_service_http_client.create_fx_symbol_overview_client(fx_symbol_overview)

    override_default_limits(expected_order_limits_, expected_portfolio_limits_)
    driver.maximize_window()
    time.sleep(Delay.SHORT.value)
    driver.get(get_web_project_url())
    # verify is portfolio status is created
    time.sleep(5)
    # wait(driver).until(EC.presence_of_element_located((By.ID, "portfolio_status")))
    # portfolio_status_widget = driver.find_element(By.ID, "portfolio_status")
    # scroll_into_view(driver=driver, element=portfolio_status_widget)
    # wait(driver).until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    # kill_switch_btn = portfolio_status_widget.find_element(By.NAME, "kill_switch")


    wait(driver).until(EC.presence_of_element_located((By.ID, "system_control")))
    system_control_widget = driver.find_element(By.ID, "system_control")
    scroll_into_view(driver=driver, element=system_control_widget)
    click_button_with_name(system_control_widget, "Create")
    wait(driver).until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    kill_switch_btn = system_control_widget.find_element(By.NAME, "kill_switch")

    assert kill_switch_btn.is_displayed(), "failed to load web project, kill switch button not found"
    create_pair_strat(driver=driver, pair_strat=pair_strat)
    create_tob_md_ld_fj_os_oj(driver=driver, top_of_book_list=top_of_book_list_,
                              market_depth_list=market_depth_basemodel_list, last_trade_list=last_trade_fixture_list,
                              fills_journal_list=fills_journal_fixture_list,
                              order_snapshot_list=order_snapshot_fixture_list,
                              order_journal_list=order_journal_fixture_list)


@pytest.fixture()
def pair_strat() -> Dict[str, any]:
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


@pytest.fixture()
def pair_strat_edit() -> Dict[str, any]:
    pair_strat_edit = {
        "pair_strat_params": {

            "common_premium": 55,
            "hedge_ratio": 6mobile_book
        }
    }
    yield pair_strat_edit


@pytest.fixture()
def strat_limits() -> Dict[str, any]:
    strat_limits = {
        "max_open_orders_per_side": 4,
        "max_single_leg_notional": 5mobile_bookmobile_book,
        "max_open_single_leg_notional": 6mobile_bookmobile_book,
        "max_net_filled_notional": 7mobile_bookmobile_book,
        "max_concentration": 7,
        "limit_up_down_volume_participation_rate": 2mobile_book,
        "cancel_rate": {
            "max_cancel_rate": 1mobile_book,
            "applicable_period_seconds": 9,
            "waived_min_orders": 2
        },
        "market_trade_volume_participation": {
            "max_participation_rate": 15,
            "applicable_period_seconds": 25
        },
        "market_depth": {
            "participation_rate": 9mobile_book,
            "depth_levels": 18
        },
        "residual_restriction": {
            "max_residual": 4mobile_bookmobile_bookmobile_book,
            "residual_mark_seconds": 1
        }
    }
    yield strat_limits


@pytest.fixture
def set_micro_seperator_and_clean(schema_dict: Dict[str, any]):
    update_schema_json(schema_dict=copy.deepcopy(schema_dict), project_name="phone_book",
                       update_widget_name="strat_collection", update_field_name="loaded_strat_keys",
                       extend_field_name="micro_separator", value="=")
    yield

    schema_path: PurePath = (code_gen_projects_dir_path / "addressbook" / "ProjectGroup" /
                             "phone_book" / "web-ui" / "public" / "schema.json")
    with open(str(schema_path), "w") as file:
        json.dump(schema_dict, file, indent=2)


@pytest.fixture
def ui_layout_list_(schema_dict):
    ui_layout: UILayoutBaseModel = UILayoutBaseModel()
    ui_layout.id = 1
    ui_layout.profile_id = "test"
    widget_ui_data_elements: List[WidgetUIDataElementOptional] = []

    x: int = 1mobile_book
    y: int = 7
    w: int = 4
    h: int = 3
    for widget_name, widget_schema in schema_dict.items():
        x += 5
        y += 3
        w += 6
        h += 2
        if widget_name in ["definitions", "autocomplete", "ui_layout", "widget_ui_data_element"]:
            continue
        widget_ui_data_element: WidgetUIDataElementOptional = WidgetUIDataElementOptional()
        widget_ui_data_element.i = widget_name
        widget_ui_data_element.x = x
        widget_ui_data_element.y = y
        widget_ui_data_element.w = w
        widget_ui_data_element.h = h

        widget_ui_data = widget_schema.get("widget_ui_data_element").get("widget_ui_data")
        ui_data_list: List[WidgetUIDataOptional] = []
        ui_data: WidgetUIDataOptional = WidgetUIDataOptional()
        ui_data_list.append(ui_data)
    #     ui_data.
    #     if widget_ui_data is not None:
    #         ui_data: List[WidgetUIDataOptional] = []
    #         for _ in widget_ui_data:
    #             ui_data.append(WidgetUIDataOptional(**_))
    #         widget_ui_data_element.widget_ui_data = ui_data
    #
    #     widget_ui_data_elements.append(widget_ui_data_element)
    # ui_layout.widget_ui_data_elements = widget_ui_data_elements

    yield ui_layout


@pytest.fixture
def set_disable_ws_on_edit_and_clean(schema_dict: Dict[str, any]):
    update_schema_json(schema_dict=copy.deepcopy(schema_dict), project_name="phone_book",
                       update_widget_name="top_of_book", update_field_name="widget_ui_data_element",
                       extend_field_name="disable_ws_on_edit", value=True)
    yield

    schema_path: PurePath = code_gen_projects_dir_path / "phone_book" / "web-ui" / "public" / "schema.json"
    with open(str(schema_path), "w") as file:
        json.dump(schema_dict, file, indent=2)
