import logging
import os, signal
import sys
import threading
import time
import copy
from typing import Tuple, Final
import re
import pexpect
from pathlib import PurePath
from fastapi.encoders import jsonable_encoder
from csv import writer

# project imports
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.market_data.generated.Pydentic.market_data_service_model_imports import TopOfBookBaseModel, \
    QuoteOptional, LastTradeBaseModel, MarketDepthBaseModel, SymbolOverviewBaseModel, TickTypeEnum
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_web_client import \
    MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase
from Flux.CodeGenProjects.addressbook.app.static_data import SecurityRecordManager
from FluxPythonUtils.scripts.utility_functions import clean_mongo_collections, YAMLConfigurationManager, parse_to_int, \
    get_native_host_n_port_from_config_dict


code_gen_projects_dir_path = PurePath(__file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects"

PAIR_STRAT_ENGINE_DIR = code_gen_projects_dir_path / "addressbook"
ps_config_yaml_path: PurePath = PAIR_STRAT_ENGINE_DIR / "data" / "config.yaml"
ps_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(ps_config_yaml_path))

MARKET_DATA_DIR = code_gen_projects_dir_path / "market_data"
md_config_yaml_path = MARKET_DATA_DIR / "data" / "config.yaml"
md_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(md_config_yaml_path))

HOST: Final[str] = "127.0.0.1"
PAIR_STRAT_CACHE_PORT: Final[str] = ps_config_yaml_dict.get("cache_port")
PAIR_STRAT_BEANIE_PORT: Final[str] = ps_config_yaml_dict.get("beanie_port")
MARKET_DATA_BEANIE_PORT: Final[str] = md_config_yaml_dict.get("beanie_port")
os.environ["HOST"] = HOST
os.environ["PAIR_STRAT_BEANIE_PORT"] = PAIR_STRAT_BEANIE_PORT
os.environ["MARKET_DATA_BEANIE_PORT"] = MARKET_DATA_BEANIE_PORT

host, port = get_native_host_n_port_from_config_dict(ps_config_yaml_dict)
strat_manager_service_native_web_client: StratManagerServiceWebClient = \
    StratManagerServiceWebClient(host=host, port=parse_to_int(port))
market_data_web_client: MarketDataServiceWebClient = \
    MarketDataServiceWebClient(host=HOST, port=int(MARKET_DATA_BEANIE_PORT))

static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
project_dir_path = \
    PurePath(__file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "addressbook"
project_app_dir_path = project_dir_path / "app"
test_project_dir_path = PurePath(__file__).parent.parent / 'data'
test_config_file_path: PurePath = test_project_dir_path / "config.yaml"
static_data_dir: PurePath = project_dir_path / "data"


def clean_all_collections_ignoring_ui_layout(ps_db_name: str, md_db_name: str) -> None:
    mongo_server_uri: str = get_mongo_server_uri()
    clean_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=ps_db_name,
                            ignore_collections=["UILayout"])
    clean_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=md_db_name,
                            ignore_collections=["UILayout"])


def get_ps_n_md_db_names(test_config_file_path: str | PurePath):
    if os.path.isfile(str(test_config_file_path)):
        test_config = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
        ps_db_name = \
            fetched_ps_db_name if (fetched_ps_db_name := test_config.get(
                "ps_db_name")) is not None else "addressbook"
        md_db_name = \
            fetched_md_db_name if (fetched_md_db_name := test_config.get("md_db_name")) is not None else "market_data"
    else:
        ps_db_name = "addressbook"
        md_db_name = "market_data"
    return ps_db_name, md_db_name


def clean_slate_post_test():
    ps_db_name, md_db_name = get_ps_n_md_db_names(test_config_file_path)
    clean_all_collections_ignoring_ui_layout(ps_db_name, md_db_name)


def run_pair_strat_log_analyzer(executor_n_log_analyzer: 'ExecutorNLogAnalyzerManager'):
    log_analyzer = pexpect.spawn("python addressbook_log_analyzer.py &",
                                 cwd=project_app_dir_path)
    log_analyzer.timeout = None
    log_analyzer.logfile = sys.stdout.buffer
    executor_n_log_analyzer.pair_strat_log_analyzer_pid = log_analyzer.pid
    print(f"pair_strat_log_analyzer PID: {log_analyzer.pid}")
    log_analyzer.expect("CRITICAL: log analyzer running in simulation mode...")
    log_analyzer.interact()


def run_executor(executor_n_log_analyzer: 'ExecutorNLogAnalyzerManager'):
    executor = pexpect.spawn("python strat_executor.py &", cwd=project_app_dir_path)
    executor.timeout = None
    executor.logfile = sys.stdout.buffer
    executor_n_log_analyzer.executor_pid = executor.pid
    print(f"executor PID: {executor.pid}")
    executor.expect(pexpect.EOF)
    executor.interact()


def kill_process(kill_pid: str | int | None):
    if kill_pid is not None:
        os.kill(kill_pid, signal.SIGINT)
        try:
            # raises OSError if pid still exists
            os.kill(kill_pid, 0)
        except OSError:
            return False
        else:
            return True
    else:
        return False


class ExecutorNLogAnalyzerManager:
    """
    Context manager to handle running of trade_executor and log_analyzer in threads and after test is completed,
    handling killing of the both processes and cleaning the slate
    """

    def __init__(self):
        # p_id(s) are getting populated by their respective thread target functions
        self.executor_pid = None
        self.pair_strat_log_analyzer_pid = None

    def __enter__(self):
        executor_thread = threading.Thread(target=run_executor, args=(self,))
        pair_strat_log_analyzer_thread = threading.Thread(target=run_pair_strat_log_analyzer, args=(self,))
        executor_thread.start()
        pair_strat_log_analyzer_thread.start()

        # delay for log_analyzer and executor to get started
        time.sleep(20)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        assert kill_process(self.executor_pid), \
            f"Something went wrong while killing trade_executor process, pid: {self.executor_pid}"
        assert kill_process(self.pair_strat_log_analyzer_pid), \
            f"Something went wrong while killing pair_strat_log_analyzer process, " \
            f"pid: {self.pair_strat_log_analyzer_pid}"

        # Env var based post test cleaning
        clean_env_var = os.environ.get("ENABLE_CLEAN_SLATE")
        if clean_env_var is not None and len(clean_env_var) and parse_to_int(clean_env_var) == 1:
            # cleaning db
            clean_slate_post_test()

        # Env var based delay in test
        post_test_delay = os.environ.get("POST_TEST_DELAY")
        if post_test_delay is not None and len(post_test_delay):
            # cleaning db
            time.sleep(parse_to_int(post_test_delay))


def get_continuous_order_configs(symbol: str) -> Tuple[int | None, int | None]:
    symbol_configs = TradeSimulator.get_symbol_configs(symbol)
    return symbol_configs.get("continues_order_count"), symbol_configs.get("continues_special_order_count")


def position_fixture():
    position_json = {
        "_id": Position.next_id(),
        "pos_disable": False,
        "type": PositionType.PTH,
        "available_size": 100,
        "allocated_size": 90,
        "consumed_size": 60,
        "acquire_cost": 160,
        "incurred_cost": 140,
        "carry_cost": 120,
        "priority": 60,
        "premium_percentage": 20
    }
    position = Position(**position_json)
    return position


def sec_position_fixture(sec_id: str, sec_type: SecurityType):
    sec_position_json = {
        "_id": SecPosition.next_id(),
        "security": {
            "sec_id": sec_id,
            "sec_type": sec_type
        },
        "positions": [
            position_fixture(),
            position_fixture()
        ]
    }
    sec_position = SecPosition(**sec_position_json)
    return sec_position


def broker_fixture():
    sec_position_1 = sec_position_fixture("CB_Sec_1", SecurityType.SEDOL)
    sec_position_2 = sec_position_fixture("EQT_Sec_1.SS", SecurityType.RIC)

    broker_json = {
        "bkr_disable": False,
        "sec_positions": [
            sec_position_1,
            sec_position_2
        ],
        "broker": "Bkr1",
        "bkr_priority": 5
    }
    broker1 = BrokerOptional(**broker_json)
    return broker1


def get_buy_order_related_values():
    single_buy_order_px = 100
    single_buy_order_qty = 90
    single_buy_filled_px = 90
    single_buy_filled_qty = 50
    single_buy_unfilled_qty = single_buy_order_qty - single_buy_filled_qty
    return single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty


def get_sell_order_related_values():
    single_sell_order_px = 110
    single_sell_order_qty = 70
    single_sell_filled_px = 120
    single_sell_filled_qty = 30
    single_sell_unfilled_qty = single_sell_order_qty - single_sell_filled_qty
    return single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
        single_sell_unfilled_qty


def get_both_leg_last_trade_px():
    current_leg_last_trade_px = 116
    other_leg_last_trade_px = 116
    return current_leg_last_trade_px, other_leg_last_trade_px


def update_expected_strat_brief_for_buy(loop_count: int, expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                        expected_strat_limits: StratLimits,
                                        expected_strat_brief_obj: StratBriefBaseModel,
                                        date_time_for_cmp: DateTime):
    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    current_leg_last_trade_px, other_leg_last_trade_px = get_both_leg_last_trade_px()
    max_participation_rate = expected_strat_limits.market_trade_volume_participation.max_participation_rate

    open_qty = expected_symbol_side_snapshot.total_qty - expected_symbol_side_snapshot.total_filled_qty - \
               expected_symbol_side_snapshot.total_cxled_qty
    open_notional = open_qty * get_px_in_usd(expected_order_snapshot_obj.order_brief.px)
    expected_strat_brief_obj.pair_buy_side_trading_brief.open_qty = open_qty
    expected_strat_brief_obj.pair_buy_side_trading_brief.open_notional = open_notional
    expected_strat_brief_obj.pair_buy_side_trading_brief.all_bkr_cxlled_qty = \
        expected_symbol_side_snapshot.total_cxled_qty
    if expected_order_snapshot_obj.order_status == OrderStatusType.OE_ACKED:
        expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_orders = 4
    else:
        expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_orders = 5
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_notional = \
        expected_strat_limits.max_cb_notional - expected_symbol_side_snapshot.total_fill_notional - open_notional
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_notional = \
        expected_strat_limits.max_open_cb_notional - open_notional
    total_security_size: int = \
        static_data.get_security_float_from_ticker(expected_order_snapshot_obj.order_brief.security.sec_id)
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_concentration = \
        (total_security_size / 100 * expected_strat_limits.max_concentration) - (
                open_qty + expected_symbol_side_snapshot.total_filled_qty)
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_strat_brief_obj.pair_buy_side_trading_brief.participation_period_order_qty_sum = None
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_cxl_qty = \
        (((open_qty + expected_symbol_side_snapshot.total_filled_qty +
           expected_symbol_side_snapshot.total_cxled_qty) / 100) * expected_strat_limits.cancel_rate.max_cancel_rate) - \
        expected_symbol_side_snapshot.total_cxled_qty
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_strat_brief_obj.pair_buy_side_trading_brief.indicative_consumable_participation_qty = None
    expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty = single_buy_unfilled_qty * (loop_count - 1)
    expected_strat_brief_obj.pair_buy_side_trading_brief.indicative_consumable_residual = \
        expected_strat_limits.residual_restriction.max_residual - \
        ((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * current_leg_last_trade_px) -
         (0 * other_leg_last_trade_px))
    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = date_time_for_cmp


def update_expected_strat_brief_for_sell(loop_count: int, total_loop_count: int,
                                         expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                         expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                         expected_strat_limits: StratLimits,
                                         expected_strat_brief_obj: StratBriefBaseModel,
                                         date_time_for_cmp: DateTime):
    single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
        single_sell_unfilled_qty = get_sell_order_related_values()
    current_leg_last_trade_px, other_leg_last_trade_px = get_both_leg_last_trade_px()
    max_participation_rate = expected_strat_limits.market_trade_volume_participation.max_participation_rate

    open_qty = expected_symbol_side_snapshot.total_qty - expected_symbol_side_snapshot.total_filled_qty - \
               expected_symbol_side_snapshot.total_cxled_qty
    open_notional = open_qty * get_px_in_usd(expected_order_snapshot_obj.order_brief.px)
    expected_strat_brief_obj.pair_sell_side_trading_brief.open_qty = open_qty
    expected_strat_brief_obj.pair_sell_side_trading_brief.open_notional = open_notional
    expected_strat_brief_obj.pair_sell_side_trading_brief.all_bkr_cxlled_qty = \
        expected_symbol_side_snapshot.total_cxled_qty
    if expected_order_snapshot_obj.order_status == OrderStatusType.OE_ACKED:
        expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_orders = 4
    else:
        expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_orders = 5
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_notional = \
        expected_strat_limits.max_cb_notional - expected_symbol_side_snapshot.total_fill_notional - open_notional
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_notional = \
        expected_strat_limits.max_open_cb_notional - open_notional
    total_security_size: int = \
        static_data.get_security_float_from_ticker(expected_order_snapshot_obj.order_brief.security.sec_id)
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_concentration = \
        (total_security_size / 100 * expected_strat_limits.max_concentration) - (
                open_qty + expected_symbol_side_snapshot.total_filled_qty)
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_strat_brief_obj.pair_sell_side_trading_brief.participation_period_order_qty_sum = None
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_cxl_qty = \
        (((open_qty + expected_symbol_side_snapshot.total_filled_qty +
           expected_symbol_side_snapshot.total_cxled_qty) / 100) * expected_strat_limits.cancel_rate.max_cancel_rate) - \
        expected_symbol_side_snapshot.total_cxled_qty
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_strat_brief_obj.pair_sell_side_trading_brief.indicative_consumable_participation_qty = None
    expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty = single_sell_unfilled_qty * (loop_count - 1)
    expected_strat_brief_obj.pair_sell_side_trading_brief.indicative_consumable_residual = \
        expected_strat_limits.residual_restriction.max_residual - \
        ((expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * current_leg_last_trade_px) -
         ((40 * total_loop_count) * other_leg_last_trade_px))
    expected_strat_brief_obj.pair_sell_side_trading_brief.last_update_date_time = date_time_for_cmp


def check_placed_buy_order_computes(loop_count: int, expected_order_id: str, symbol: str,
                                    buy_placed_order_journal: OrderJournalBaseModel,
                                    expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                    expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                    expected_pair_strat: PairStratBaseModel,
                                    expected_strat_limits: StratLimits,
                                    expected_strat_status: StratStatus,
                                    expected_strat_brief_obj: StratBriefBaseModel,
                                    expected_portfolio_status: PortfolioStatusBaseModel):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after order is triggered
    """
    order_journal_obj_list = strat_manager_service_native_web_client.get_all_order_journal_client()
    assert buy_placed_order_journal in order_journal_obj_list, f"Couldn't find {buy_placed_order_journal} in " \
                                                               f"{order_journal_obj_list}"

    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    current_leg_last_trade_px, other_leg_last_trade_px = get_both_leg_last_trade_px()

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = single_buy_order_px
    expected_order_snapshot_obj.order_brief.qty = single_buy_order_qty
    expected_order_snapshot_obj.order_brief.order_notional = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_order_snapshot_obj.order_status = "OE_UNACK"
    expected_order_snapshot_obj.last_update_date_time = buy_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = buy_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.order_brief.text.extend(buy_placed_order_journal.order.text)

    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None
    found_count = 0
    for order_snapshot in order_snapshot_list:
        if order_snapshot == expected_order_snapshot_obj:
            found_count += 1
    print(expected_order_snapshot_obj, "in", order_snapshot_list)
    assert found_count == 1, f"Couldn't find expected_order_snapshot {expected_order_snapshot_obj} in " \
                             f"{order_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = single_buy_order_px
    expected_symbol_side_snapshot.total_qty = single_buy_order_qty * loop_count
    expected_symbol_side_snapshot.last_update_date_time = buy_placed_order_journal.order_event_date_time
    expected_symbol_side_snapshot.order_count = loop_count
    if loop_count > 1:
        expected_symbol_side_snapshot.total_filled_qty = single_buy_filled_qty * (loop_count - 1)
        expected_symbol_side_snapshot.total_fill_notional = single_buy_filled_qty * get_px_in_usd(
            single_buy_filled_px) * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1) * single_buy_unfilled_qty
        expected_symbol_side_snapshot.avg_fill_px = (single_buy_filled_qty * single_buy_filled_px * (
                    loop_count - 1)) / (single_buy_filled_qty * (loop_count - 1))
        expected_symbol_side_snapshot.last_update_fill_qty = single_buy_filled_qty
        expected_symbol_side_snapshot.last_update_fill_px = single_buy_filled_px
        expected_symbol_side_snapshot.avg_cxled_px = (single_buy_unfilled_qty * single_buy_order_px * (
                    loop_count - 1)) / (single_buy_unfilled_qty * (loop_count - 1))

    symbol_side_snapshot_list = strat_manager_service_native_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"{expected_symbol_side_snapshot} not found in " \
                                                                       f"{symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                        expected_strat_limits, expected_strat_brief_obj,
                                        buy_placed_order_journal.order_event_date_time)

    print(f"@@@ fetching strat_brief for symbol: {symbol} at {DateTime.utcnow()}")
    strat_brief_list = strat_manager_service_native_web_client.get_strat_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        strat_brief.pair_buy_side_trading_brief.indicative_consumable_participation_qty = None
        strat_brief.pair_buy_side_trading_brief.participation_period_order_qty_sum = None
        strat_brief.pair_buy_side_trading_brief.last_update_date_time = None
        # Since sell side of strat_brief is not updated till sell cycle
        strat_brief.pair_sell_side_trading_brief = expected_strat_brief_obj.pair_sell_side_trading_brief

    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = None
    assert expected_strat_brief_obj in strat_brief_list, f"Couldn't find expected strat_brief {expected_strat_brief_obj} in " \
                                                         f"list {strat_brief_list} at {DateTime.utcnow()}"

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_strat_limits.eligible_brokers = []
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_order_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_open_buy_qty = single_buy_order_qty
    expected_strat_status.avg_open_buy_px = (single_buy_order_qty * single_buy_order_px) / single_buy_order_qty
    expected_strat_status.total_open_buy_notional = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_open_exposure = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg2.sec,
                                              residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * (loop_count - 1)) / (
                    single_buy_filled_qty * (loop_count - 1))
        expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * (
                    loop_count - 1)
        expected_strat_status.total_fill_exposure = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * (
                    loop_count - 1)
        expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (
                    single_buy_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        residual_notional = abs((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
            current_leg_last_trade_px)) - \
                                (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
                                    other_leg_last_trade_px)))
        expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg1.sec,
                                                  residual_notional=residual_notional)

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.last_active_date_time = None
        pair_strat.frequency = None
        pair_strat.strat_limits.eligible_brokers = []
        pair_strat.strat_status_update_seq_num = 0
        pair_strat.strat_limits_update_seq_num = 0
        pair_strat.pair_strat_params_update_seq_num = 0
    assert expected_pair_strat in pair_strat_list, f"{expected_pair_strat} not found in {pair_strat_list}"

    # # expected portfolio_status
    # expected_portfolio_status.overall_buy_notional = \
    #     ((9000 * loop_count) - (500*(loop_count-1)) - (4000*(loop_count-1))) * symbol_pair_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 0
    # if loop_count > 1:
    #     expected_portfolio_status.overall_buy_fill_notional = (4500 * (loop_count-1)) * symbol_pair_count
    #
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #
    # assert expected_portfolio_status in portfolio_status_list


def placed_buy_order_ack_receive(loop_count: int, expected_order_id: str, buy_order_placed_date_time: DateTime,
                                 expected_order_journal: OrderJournalBaseModel,
                                 expected_order_snapshot_obj: OrderSnapshotBaseModel):
    """Checking after order's ACK status is received"""
    order_journal_obj_list = strat_manager_service_native_web_client.get_all_order_journal_client()

    assert expected_order_journal in order_journal_obj_list, f"Couldn't find {expected_order_journal} in list " \
                                                             f"{order_journal_obj_list}"

    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()

    # Checking order_snapshot
    expected_order_snapshot_obj.order_status = "OE_ACKED"
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = single_buy_order_px
    expected_order_snapshot_obj.order_brief.qty = single_buy_order_qty
    expected_order_snapshot_obj.order_brief.order_notional = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_order_snapshot_obj.last_update_date_time = expected_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = buy_order_placed_date_time

    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None

    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"


def check_fill_receive_for_placed_buy_order(loop_count: int, expected_order_id: str,
                                            buy_order_placed_date_time: DateTime, symbol: str,
                                            buy_fill_journal: FillsJournalBaseModel,
                                            expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                            expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                            expected_pair_strat: PairStratBaseModel,
                                            expected_strat_limits: StratLimits,
                                            expected_strat_status: StratStatus,
                                            expected_strat_brief_obj: StratBriefBaseModel,
                                            expected_portfolio_status: PortfolioStatusBaseModel):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after fill is received
    """
    fill_journal_obj_list = strat_manager_service_native_web_client.get_all_fills_journal_client()
    assert buy_fill_journal in fill_journal_obj_list, f"Couldn't find {buy_fill_journal} in {fill_journal_obj_list}"

    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    current_leg_last_trade_px, other_leg_last_trade_px = get_both_leg_last_trade_px()

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = single_buy_order_px
    expected_order_snapshot_obj.order_brief.qty = single_buy_order_qty
    expected_order_snapshot_obj.order_brief.order_notional = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_order_snapshot_obj.filled_qty = single_buy_filled_qty
    expected_order_snapshot_obj.avg_fill_px = (single_buy_filled_qty * single_buy_filled_px) / single_buy_filled_qty
    expected_order_snapshot_obj.fill_notional = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px)
    expected_order_snapshot_obj.last_update_fill_qty = single_buy_filled_qty
    expected_order_snapshot_obj.last_update_fill_px = single_buy_filled_px
    expected_order_snapshot_obj.last_update_date_time = buy_fill_journal.fill_date_time
    expected_order_snapshot_obj.create_date_time = buy_order_placed_date_time
    expected_order_snapshot_obj.order_status = "OE_ACKED"

    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    # removing below field from received_order_snapshot_list for comparison
    for symbol_side_snapshot in order_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = single_buy_order_px
    expected_symbol_side_snapshot.total_qty = single_buy_order_qty * loop_count
    expected_symbol_side_snapshot.last_update_date_time = buy_fill_journal.fill_date_time
    expected_symbol_side_snapshot.order_count = 1 * loop_count
    expected_symbol_side_snapshot.total_filled_qty = single_buy_filled_qty * loop_count
    expected_symbol_side_snapshot.avg_fill_px = \
        (single_buy_filled_qty * single_buy_filled_px * loop_count) / (single_buy_filled_qty * loop_count)
    expected_symbol_side_snapshot.total_fill_notional = \
        single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * loop_count
    expected_symbol_side_snapshot.last_update_fill_qty = single_buy_filled_qty
    expected_symbol_side_snapshot.last_update_fill_px = single_buy_filled_px
    if loop_count > 1:
        expected_symbol_side_snapshot.total_cxled_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = \
            single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (loop_count - 1)
        expected_symbol_side_snapshot.avg_cxled_px = \
            (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (single_buy_unfilled_qty *
                                                                                  (loop_count - 1))

    symbol_side_snapshot_list = strat_manager_service_native_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                        expected_strat_limits, expected_strat_brief_obj,
                                        buy_fill_journal.fill_date_time)

    strat_brief_list = strat_manager_service_native_web_client.get_strat_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        strat_brief.pair_buy_side_trading_brief.indicative_consumable_participation_qty = None
        strat_brief.pair_buy_side_trading_brief.participation_period_order_qty_sum = None
        # Since sell side of strat_brief is not updated till sell cycle
        strat_brief.pair_sell_side_trading_brief = expected_strat_brief_obj.pair_sell_side_trading_brief
        strat_brief.pair_buy_side_trading_brief.last_update_date_time = None
    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = None
    assert expected_strat_brief_obj in strat_brief_list, f"Couldn't find {expected_strat_brief_obj} in " \
                                                         f"{strat_brief_list}"

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_strat_limits.eligible_brokers = []
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_order_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_open_buy_qty = single_buy_unfilled_qty
    expected_strat_status.avg_open_buy_px = (single_buy_unfilled_qty * single_buy_order_px) / single_buy_unfilled_qty
    expected_strat_status.total_open_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_open_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * loop_count
    expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * loop_count) / (
                single_buy_filled_qty * loop_count)
    expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * loop_count
    expected_strat_status.total_fill_exposure = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * loop_count
    expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg2.sec,
                                              residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (
                    single_buy_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        residual_notional = abs((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
            current_leg_last_trade_px)) - \
                                (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
                                    other_leg_last_trade_px)))
        expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg1.sec,
                                                  residual_notional=residual_notional)
    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional
    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.frequency = None
        pair_strat.last_active_date_time = None
        pair_strat.strat_limits.eligible_brokers = []
        pair_strat.strat_status_update_seq_num = 0
        pair_strat.strat_limits_update_seq_num = 0
        pair_strat.pair_strat_params_update_seq_num = 0
    assert expected_pair_strat in pair_strat_list, f"Couldn't find {expected_pair_strat} in {pair_strat_list}"

    # expected portfolio_status
    # expected_portfolio_status.overall_buy_notional = (9000 * loop_count) - (500*loop_count) - (4000*(loop_count-1))
    # expected_portfolio_status.overall_buy_fill_notional = 4500 * loop_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 0
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #     # portfolio_status.current_period_available_buy_order_count = 0
    #     # portfolio_status.current_period_available_sell_order_count = 0
    # assert expected_portfolio_status in portfolio_status_list


def check_placed_sell_order_computes(loop_count: int, total_loop_count: int, expected_order_id: str,
                                     symbol: str, sell_placed_order_journal: OrderJournalBaseModel,
                                     expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                     expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                     expected_pair_strat: PairStratBaseModel,
                                     expected_strat_limits: StratLimits,
                                     expected_strat_status: StratStatus,
                                     expected_strat_brief_obj: StratBriefBaseModel,
                                     expected_portfolio_status: PortfolioStatusBaseModel):
    order_journal_obj_list = strat_manager_service_native_web_client.get_all_order_journal_client()

    assert sell_placed_order_journal in order_journal_obj_list, f"Couldn't find {sell_placed_order_journal} in " \
                                                                f"{order_journal_obj_list}"

    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
        single_sell_unfilled_qty = get_sell_order_related_values()
    current_leg_last_trade_px, other_leg_last_trade_px = get_both_leg_last_trade_px()

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = single_sell_order_px
    expected_order_snapshot_obj.order_brief.qty = single_sell_order_qty
    expected_order_snapshot_obj.order_brief.order_notional = single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_order_snapshot_obj.order_status = "OE_UNACK"
    expected_order_snapshot_obj.last_update_date_time = sell_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = sell_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.order_brief.text.extend(sell_placed_order_journal.order.text)

    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None
    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = single_sell_order_px
    expected_symbol_side_snapshot.total_qty = single_sell_order_qty * loop_count
    expected_symbol_side_snapshot.last_update_date_time = sell_placed_order_journal.order_event_date_time
    expected_symbol_side_snapshot.order_count = loop_count
    if loop_count > 1:
        expected_symbol_side_snapshot.total_filled_qty = single_sell_filled_qty * (loop_count - 1)
        expected_symbol_side_snapshot.total_fill_notional = single_sell_filled_qty * get_px_in_usd(
            single_sell_filled_px) * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1)
        expected_symbol_side_snapshot.avg_fill_px = (single_sell_filled_qty * single_sell_filled_px * (
                    loop_count - 1)) / (single_sell_filled_qty * (loop_count - 1))
        expected_symbol_side_snapshot.last_update_fill_qty = single_sell_filled_qty
        expected_symbol_side_snapshot.last_update_fill_px = single_sell_filled_px
        expected_symbol_side_snapshot.avg_cxled_px = (single_sell_unfilled_qty * single_sell_order_px * (
                    loop_count - 1)) / (single_sell_unfilled_qty * (loop_count - 1))

    symbol_side_snapshot_list = strat_manager_service_native_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"Couldn't find {expected_symbol_side_snapshot} "

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, total_loop_count, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_placed_order_journal.order_event_date_time)

    strat_brief_list = strat_manager_service_native_web_client.get_strat_brief_from_symbol_query_client(symbol)
    expected_strat_brief_obj.pair_sell_side_trading_brief.last_update_date_time = None
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        # Since buy side of strat_brief is already checked
        strat_brief.pair_buy_side_trading_brief = expected_strat_brief_obj.pair_buy_side_trading_brief
        strat_brief.pair_sell_side_trading_brief.indicative_consumable_participation_qty = None
        strat_brief.pair_sell_side_trading_brief.participation_period_order_qty_sum = None
        strat_brief.pair_sell_side_trading_brief.last_update_date_time = None
    for strat_brief in strat_brief_list:
        if strat_brief.pair_sell_side_trading_brief == expected_strat_brief_obj.pair_sell_side_trading_brief:
            assert True
            break
    else:
        assert False, f"{expected_strat_brief_obj.pair_sell_side_trading_brief} not found in {strat_brief_list}"

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_strat_limits.eligible_brokers = []
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = single_buy_order_qty * total_loop_count
    expected_strat_status.total_sell_qty = single_sell_order_qty * loop_count
    expected_strat_status.total_order_qty = (single_buy_order_qty * total_loop_count) + (
                single_sell_order_qty * loop_count)
    expected_strat_status.total_open_sell_qty = single_sell_order_qty
    expected_strat_status.avg_open_sell_px = (single_sell_order_qty * single_sell_order_px) / single_sell_order_qty
    expected_strat_status.total_open_sell_notional = single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_open_exposure = -single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * total_loop_count) / (
                single_buy_filled_qty * total_loop_count)
    expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * total_loop_count
    expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * total_loop_count
    expected_strat_status.total_fill_exposure = single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * total_loop_count
    expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * total_loop_count) / (
                single_buy_unfilled_qty * total_loop_count)
    expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * total_loop_count
    expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(
        single_buy_order_px) * total_loop_count
    expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(
        single_buy_order_px) * total_loop_count
    residual_notional = abs(((single_buy_unfilled_qty * total_loop_count) * get_px_in_usd(current_leg_last_trade_px)) -
                            (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
                                other_leg_last_trade_px)))
    if ((single_buy_unfilled_qty * total_loop_count) * current_leg_last_trade_px) > (
            expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * other_leg_last_trade_px):
        residual_security = strat_brief.pair_buy_side_trading_brief.security
    else:
        residual_security = strat_brief.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=residual_security, residual_notional=residual_notional)
    if loop_count > 1:
        expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * (loop_count - 1)) / (
                    single_sell_filled_qty * (loop_count - 1))
        expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(
            single_sell_filled_px) * (loop_count - 1)
        expected_strat_status.total_fill_exposure = (single_buy_filled_qty * get_px_in_usd(
            single_buy_filled_px) * total_loop_count) - (single_sell_filled_qty * get_px_in_usd(
            single_sell_filled_px) * (loop_count - 1))
        expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * (loop_count - 1)) / (
                    single_sell_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = (single_buy_unfilled_qty * get_px_in_usd(
            single_buy_order_px) * total_loop_count) - (single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1))

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.last_active_date_time = None
        pair_strat.frequency = None
        pair_strat.strat_status.average_premium = 0.0
        pair_strat.strat_limits.eligible_brokers = []
        pair_strat.strat_status_update_seq_num = 0
        pair_strat.strat_limits_update_seq_num = 0
        pair_strat.pair_strat_params_update_seq_num = 0
    assert expected_pair_strat in pair_strat_list, f"Couldn't find {expected_pair_strat} in {pair_strat_list}"

    # expected portfolio_status
    # expected_portfolio_status.overall_sell_notional = \
    #     (7700 * loop_count) + (300*(loop_count-1)) - (4400 * (loop_count-1))
    # expected_portfolio_status.overall_sell_fill_notional = 3600 * (loop_count - 1)
    # expected_portfolio_status.overall_buy_notional = \
    #     (9000 * total_loop_count) - (500*total_loop_count) - (4000*total_loop_count)
    # expected_portfolio_status.overall_buy_fill_notional = 4500 * total_loop_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 4
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #     # portfolio_status.current_period_available_buy_order_count = 4
    #     # portfolio_status.current_period_available_sell_order_count = 4
    # assert expected_portfolio_status in portfolio_status_list


def placed_sell_order_ack_receive(loop_count: int, expected_order_id: str, sell_order_placed_date_time: DateTime,
                                  total_loop_count: int, expected_order_journal: OrderJournalBaseModel,
                                  expected_order_snapshot_obj: OrderSnapshotBaseModel):
    """Checking after order's ACK status is received"""
    order_journal_obj_list = strat_manager_service_native_web_client.get_all_order_journal_client()

    assert expected_order_journal in order_journal_obj_list, f"Couldn't find {expected_order_journal} in " \
                                                             f"{order_journal_obj_list}"

    single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
        single_sell_unfilled_qty = get_sell_order_related_values()

    # Checking order_snapshot
    expected_order_snapshot_obj.order_status = "OE_ACKED"
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = single_sell_order_px
    expected_order_snapshot_obj.order_brief.qty = single_sell_order_qty
    expected_order_snapshot_obj.order_brief.order_notional = single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_order_snapshot_obj.last_update_date_time = expected_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = sell_order_placed_date_time

    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None

    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"


def check_fill_receive_for_placed_sell_order(loop_count: int, total_loop_count: int, expected_order_id: str,
                                             sell_order_placed_date_time: DateTime, symbol: str,
                                             sell_fill_journal: FillsJournalBaseModel,
                                             expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                             expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                             expected_pair_strat: PairStratBaseModel,
                                             expected_strat_limits: StratLimits,
                                             expected_strat_status: StratStatus,
                                             expected_strat_brief_obj: StratBriefBaseModel,
                                             expected_portfolio_status: PortfolioStatusBaseModel):
    fill_journal_obj_list = strat_manager_service_native_web_client.get_all_fills_journal_client()
    assert sell_fill_journal in fill_journal_obj_list, f"Couldn't find {sell_fill_journal} in {fill_journal_obj_list}"

    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
        single_sell_unfilled_qty = get_sell_order_related_values()
    current_leg_last_trade_px, other_leg_last_trade_px = get_both_leg_last_trade_px()

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = single_sell_order_px
    expected_order_snapshot_obj.order_brief.qty = single_sell_order_qty
    expected_order_snapshot_obj.order_brief.order_notional = single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_order_snapshot_obj.filled_qty = single_sell_filled_qty
    expected_order_snapshot_obj.avg_fill_px = (single_sell_filled_qty * single_sell_filled_px) / single_sell_filled_qty
    expected_order_snapshot_obj.fill_notional = single_sell_filled_qty * get_px_in_usd(single_sell_filled_px)
    expected_order_snapshot_obj.last_update_fill_qty = single_sell_filled_qty
    expected_order_snapshot_obj.last_update_fill_px = single_sell_filled_px
    expected_order_snapshot_obj.last_update_date_time = sell_fill_journal.fill_date_time
    expected_order_snapshot_obj.create_date_time = sell_order_placed_date_time
    expected_order_snapshot_obj.order_status = "OE_ACKED"

    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    # removing below field from received_order_snapshot_list for comparison
    for symbol_side_snapshot in order_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = single_sell_order_px
    expected_symbol_side_snapshot.total_qty = single_sell_order_qty * loop_count
    expected_symbol_side_snapshot.last_update_date_time = expected_order_snapshot_obj.last_update_date_time
    expected_symbol_side_snapshot.order_count = 1 * loop_count
    expected_symbol_side_snapshot.total_filled_qty = single_sell_filled_qty * loop_count
    expected_symbol_side_snapshot.avg_fill_px = (single_sell_filled_qty * single_sell_filled_px * loop_count) / (
                single_sell_filled_qty * loop_count)
    expected_symbol_side_snapshot.total_fill_notional = single_sell_filled_qty * get_px_in_usd(
        single_sell_filled_px) * loop_count
    expected_symbol_side_snapshot.last_update_fill_qty = single_sell_filled_qty
    expected_symbol_side_snapshot.last_update_fill_px = single_sell_filled_px
    if loop_count > 1:
        expected_symbol_side_snapshot.total_cxled_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1)
        expected_symbol_side_snapshot.avg_cxled_px = (single_sell_unfilled_qty * single_sell_order_px * (
                    loop_count - 1)) / (single_sell_unfilled_qty * (loop_count - 1))

    symbol_side_snapshot_list = strat_manager_service_native_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_strat_limits.eligible_brokers = []
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = single_buy_order_qty * total_loop_count
    expected_strat_status.total_sell_qty = single_sell_order_qty * loop_count
    expected_strat_status.total_order_qty = (single_buy_order_qty * total_loop_count) + (
                single_sell_order_qty * loop_count)
    expected_strat_status.avg_open_sell_px = (
                                                         single_sell_unfilled_qty * single_sell_order_px) / single_sell_unfilled_qty
    expected_strat_status.total_open_sell_qty = single_sell_unfilled_qty
    expected_strat_status.total_open_sell_notional = single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_open_exposure = -single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * total_loop_count
    expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * loop_count
    expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * total_loop_count) / (
                single_buy_filled_qty * total_loop_count)
    expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * loop_count) / (
                single_sell_filled_qty * loop_count)
    expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * total_loop_count
    expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(
        single_sell_filled_px) * loop_count
    expected_strat_status.total_fill_exposure = (single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * total_loop_count) - \
                                                (single_sell_filled_qty * get_px_in_usd(
                                                    single_sell_filled_px) * loop_count)
    expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * total_loop_count) / (
                single_buy_unfilled_qty * total_loop_count)
    expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * total_loop_count
    expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(
        single_buy_order_px) * total_loop_count
    expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(
        single_buy_order_px) * total_loop_count
    current_leg_last_trade_px = 116
    other_leg_last_trade_px = 116
    residual_notional = abs(
        ((40 * total_loop_count) * get_px_in_usd(current_leg_last_trade_px)) - (
                    expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
                current_leg_last_trade_px)))
    if ((40 * total_loop_count) * get_px_in_usd(other_leg_last_trade_px)) > (
            expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
            other_leg_last_trade_px)):
        residual_security = expected_strat_brief_obj.pair_buy_side_trading_brief.security
    else:
        residual_security = expected_strat_brief_obj.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=residual_security, residual_notional=residual_notional)
    if loop_count > 1:
        expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * (loop_count - 1)) / (
                    single_sell_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = (single_buy_unfilled_qty * get_px_in_usd(
            single_buy_order_px) * total_loop_count) - (single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1))
    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional
    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.frequency = None
        pair_strat.last_active_date_time = None
        pair_strat.strat_status.average_premium = 0.0
        pair_strat.strat_limits.eligible_brokers = []
        pair_strat.strat_status_update_seq_num = 0
        pair_strat.strat_limits_update_seq_num = 0
        pair_strat.pair_strat_params_update_seq_num = 0
    assert expected_pair_strat in pair_strat_list, f"Couldn't find {expected_pair_strat} in {pair_strat_list}"

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, total_loop_count, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_fill_journal.fill_date_time)

    strat_brief_list = strat_manager_service_native_web_client.get_strat_brief_from_symbol_query_client(symbol)
    expected_strat_brief_obj.pair_sell_side_trading_brief.last_update_date_time = None
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        # Since buy side of strat_brief is already checked
        strat_brief.pair_buy_side_trading_brief = expected_strat_brief_obj.pair_buy_side_trading_brief
        strat_brief.pair_sell_side_trading_brief.indicative_consumable_participation_qty = None
        strat_brief.pair_sell_side_trading_brief.participation_period_order_qty_sum = None
        strat_brief.pair_sell_side_trading_brief.last_update_date_time = None
    for strat_brief in strat_brief_list:
        if strat_brief.pair_sell_side_trading_brief == expected_strat_brief_obj.pair_sell_side_trading_brief:
            assert True
            break
    else:
        assert False, f"Couldn't find {expected_strat_brief_obj.pair_sell_side_trading_brief} in any strat_brief in " \
                      f"{strat_brief_list}"

    # # expected portfolio_status
    # expected_portfolio_status.overall_sell_notional = (7700 * loop_count) + (300*loop_count) - (4400 * (loop_count-1))
    # expected_portfolio_status.overall_sell_fill_notional = 3600 * loop_count
    # # computes from last buy test execution
    # expected_portfolio_status.overall_buy_notional = \
    #     (9000 * total_loop_count) - (500 * total_loop_count) - (4000 * total_loop_count)
    # expected_portfolio_status.overall_buy_fill_notional = 4500 * total_loop_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 4
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #     # portfolio_status.current_period_available_buy_order_count = 0
    #     # portfolio_status.current_period_available_sell_order_count = 0
    # assert expected_portfolio_status in portfolio_status_list


class TopOfBookSide(StrEnum):
    Bid = auto()
    Ask = auto()


def _create_tob(buy_symbol: str, sell_symbol: str, top_of_book_json_list: List[Dict],
                is_non_systematic_run: bool | None = None):
    buy_stored_tob: TopOfBookBaseModel | None = None

    # For place order non-triggered run
    for index, top_of_book_json in enumerate(top_of_book_json_list):
        top_of_book_basemodel = TopOfBookBaseModel(**top_of_book_json)
        if index == 0:
            top_of_book_basemodel.symbol = buy_symbol
        else:
            top_of_book_basemodel.symbol = sell_symbol
        top_of_book_basemodel.bid_quote.px -= 10
        top_of_book_basemodel.last_update_date_time = DateTime.utcnow()
        stored_top_of_book_basemodel = \
            market_data_web_client.create_top_of_book_client(top_of_book_basemodel)
        top_of_book_basemodel.id = stored_top_of_book_basemodel.id
        top_of_book_basemodel.last_update_date_time = stored_top_of_book_basemodel.last_update_date_time
        for market_trade_vol in stored_top_of_book_basemodel.market_trade_volume:
            market_trade_vol.id = None
        for market_trade_vol in top_of_book_basemodel.market_trade_volume:
            market_trade_vol.id = None
        assert stored_top_of_book_basemodel == top_of_book_basemodel, \
            f"Mismatch TopOfBook, expected {top_of_book_basemodel}, received {stored_top_of_book_basemodel}"
        if stored_top_of_book_basemodel.symbol == buy_symbol:
            buy_stored_tob = stored_top_of_book_basemodel

    # For place order trigger run
    buy_top_of_book_basemodel = TopOfBookBaseModel(_id=buy_stored_tob.id)
    buy_top_of_book_basemodel.symbol = buy_symbol
    buy_top_of_book_basemodel.bid_quote = QuoteOptional()
    if not is_non_systematic_run:
        buy_top_of_book_basemodel.bid_quote.px = buy_stored_tob.bid_quote.px + 10
    else:
        buy_top_of_book_basemodel.bid_quote.px = buy_stored_tob.bid_quote.px
    update_date_time = DateTime.utcnow()
    buy_top_of_book_basemodel.bid_quote.last_update_date_time = update_date_time
    buy_top_of_book_basemodel.last_update_date_time = update_date_time
    updated_tob = market_data_web_client.patch_top_of_book_client(jsonable_encoder(buy_top_of_book_basemodel, by_alias=True, exclude_none=True))
    for market_trade_vol in updated_tob.market_trade_volume:
        market_trade_vol.id = None
    assert updated_tob.bid_quote.px == buy_top_of_book_basemodel.bid_quote.px, \
        f"Mismatch tob.bid_quote.px, expected {buy_top_of_book_basemodel.bid_quote.px} " \
        f"received {updated_tob.bid_quote.px}"


def _update_tob(stored_obj: TopOfBookBaseModel, px: int | float, side: Side):
    tob_obj = TopOfBookBaseModel(_id=stored_obj.id)
    # update_date_time = DateTime.now(local_timezone())
    update_date_time = DateTime.utcnow()
    if Side.BUY == side:
        tob_obj.bid_quote = QuoteOptional()
        tob_obj.bid_quote.px = px
        tob_obj.bid_quote.last_update_date_time = update_date_time
        tob_obj.last_update_date_time = update_date_time
    else:
        tob_obj.ask_quote = QuoteOptional()
        tob_obj.ask_quote.px = px
        tob_obj.ask_quote.last_update_date_time = update_date_time
        tob_obj.last_update_date_time = update_date_time
    updated_tob_obj = market_data_web_client.patch_top_of_book_client(jsonable_encoder(tob_obj, by_alias=True, exclude_none=True))

    for market_trade_vol in updated_tob_obj.market_trade_volume:
        market_trade_vol.id = None
    if side == Side.BUY:
        assert updated_tob_obj.bid_quote.px == tob_obj.bid_quote.px, \
            f"Mismatch tob.bid_quote.px, expected {tob_obj.bid_quote.px} " \
            f"received {updated_tob_obj.bid_quote.px}"
    else:
        assert updated_tob_obj.ask_quote.px == tob_obj.ask_quote.px, \
            f"Mismatch tob.ask_quote.px, expected {tob_obj.ask_quote.px} " \
            f"received {updated_tob_obj.ask_quote.px}"


def _update_buy_tob(buy_symbol: str, is_non_systematic_run: bool | None = None):
    buy_stored_tob: TopOfBookBaseModel | None = None

    stored_tob_objs = market_data_web_client.get_all_top_of_book_client()
    for tob_obj in stored_tob_objs:
        if tob_obj.symbol == buy_symbol:
            buy_stored_tob = tob_obj

    # For place order non-triggered run
    _update_tob(buy_stored_tob, buy_stored_tob.bid_quote.px - 10, Side.BUY)
    if is_non_systematic_run:
        px = buy_stored_tob.bid_quote.px - 10
    else:
        # For place order trigger run
        px = buy_stored_tob.bid_quote.px
    _update_tob(buy_stored_tob, px, Side.BUY)


def run_buy_top_of_book(loop_count: int, buy_symbol: str, sell_symbol: str,
                        top_of_book_json_list: List[Dict], is_non_systematic_run: bool | None = None):
    if loop_count == 1:
        _create_tob(buy_symbol, sell_symbol, top_of_book_json_list, is_non_systematic_run)
    else:
        _update_buy_tob(buy_symbol, is_non_systematic_run)


def run_sell_top_of_book(sell_symbol: str, is_non_systematic_run: bool | None = None):
    sell_stored_tob: TopOfBookBaseModel | None = None

    stored_tob_objs = market_data_web_client.get_all_top_of_book_client()
    for tob_obj in stored_tob_objs:
        if tob_obj.symbol == sell_symbol:
            sell_stored_tob = tob_obj

    # For place order non-triggered run
    _update_tob(sell_stored_tob, sell_stored_tob.ask_quote.px - 10, Side.SELL)

    if is_non_systematic_run:
        px = sell_stored_tob.ask_quote.px - 10
    else:
        # For place order trigger run
        px = sell_stored_tob.ask_quote.px
    _update_tob(sell_stored_tob, px, Side.SELL)


def run_last_trade(buy_symbol: str, sell_symbol: str, last_trade_json_list: List[Dict],
                   create_counts_per_side: int | None = None):
    if create_counts_per_side is None:
        create_counts_per_side = 20
    symbol_list = [buy_symbol, sell_symbol]
    for index, last_trade_json in enumerate(last_trade_json_list):
        for _ in range(create_counts_per_side):
            last_trade_obj = LastTradeBaseModel(**last_trade_json)
            last_trade_obj.symbol = symbol_list[index]
            last_trade_obj.time = DateTime.utcnow()
            created_last_trade_obj = market_data_web_client.create_last_trade_client(last_trade_obj)
            created_last_trade_obj.id = None
            created_last_trade_obj.market_trade_volume.id = last_trade_obj.market_trade_volume.id
            created_last_trade_obj.time = last_trade_obj.time
            assert created_last_trade_obj == last_trade_obj, \
                f"Mismatch last_trade: expected {last_trade_obj}, received {created_last_trade_obj}"


def create_n_validate_strat(buy_symbol: str, sell_symbol: str, pair_strat_obj: PairStratBaseModel,
                            expected_strat_limits: StratLimits,
                            expected_strat_status: StratStatus) -> PairStratBaseModel:
    pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
    pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol
    stored_pair_strat_basemodel = \
        strat_manager_service_native_web_client.create_pair_strat_client(pair_strat_obj)
    assert pair_strat_obj.frequency == stored_pair_strat_basemodel.frequency, \
        f"Mismatch pair_strat_basemodel.frequency: expected {pair_strat_obj.frequency}, " \
        f"received {stored_pair_strat_basemodel.frequency}"
    assert pair_strat_obj.pair_strat_params == stored_pair_strat_basemodel.pair_strat_params, \
        f"Mismatch pair_strat_obj.pair_strat_params: expected {pair_strat_obj.pair_strat_params}, " \
        f"received {stored_pair_strat_basemodel.pair_strat_params}"
    assert stored_pair_strat_basemodel.strat_status_update_seq_num == 0, \
        f"Mismatch pair_strat.strat_status_update_seq_num: expected 0 received " \
        f"{stored_pair_strat_basemodel.strat_status_update_seq_num}"
    assert stored_pair_strat_basemodel.strat_limits_update_seq_num == 0, \
        f"Mismatch pair_strat.strat_limits_update_seq_num: expected 0 received " \
        f"{stored_pair_strat_basemodel.strat_limits_update_seq_num}"
    assert stored_pair_strat_basemodel.pair_strat_params_update_seq_num == 0, \
        f"Mismatch pair_strat.pair_strat_params_update_seq_num: expected 0 received " \
        f"{stored_pair_strat_basemodel.pair_strat_params_update_seq_num}"
    print(f"{buy_symbol} - strat created, {stored_pair_strat_basemodel}")

    # updating pair_strat for this test-case
    expected_strat_limits.eligible_brokers = stored_pair_strat_basemodel.strat_limits.eligible_brokers
    pair_strat_base_model = PairStratBaseModel(_id=stored_pair_strat_basemodel.id,
                                               strat_limits=expected_strat_limits)

    updated_pair_strat_basemodel = strat_manager_service_native_web_client.patch_pair_strat_client(jsonable_encoder(pair_strat_base_model, by_alias=True, exclude_none=True))
    # clean strat alerts after updating strat limits
    strat_alerts: List[AlertOptional] = [AlertOptional(_id=alert.id) for alert in updated_pair_strat_basemodel.strat_status.strat_alerts]
    pair_strat_base_model = \
        PairStratBaseModel(_id=updated_pair_strat_basemodel.id,
                           strat_status=StratStatusOptional(strat_alerts=strat_alerts))

    updated_pair_strat_basemodel = strat_manager_service_native_web_client.patch_pair_strat_client(
        jsonable_encoder(pair_strat_base_model, by_alias=True, exclude_none=True))
    assert stored_pair_strat_basemodel.frequency + 2 == updated_pair_strat_basemodel.frequency, \
        f"Mismatch pair_strat_basemodel.frequency: expected {stored_pair_strat_basemodel.frequency + 1}, " \
        f"received {updated_pair_strat_basemodel.frequency}"
    assert stored_pair_strat_basemodel.strat_status_update_seq_num + 1 == \
           updated_pair_strat_basemodel.strat_status_update_seq_num, \
        f"Mismatch pair_strat.strat_status_update_seq_num: expected " \
        f"{stored_pair_strat_basemodel.strat_status_update_seq_num} received " \
        f"{updated_pair_strat_basemodel.strat_status_update_seq_num}"
    assert stored_pair_strat_basemodel.strat_limits_update_seq_num + 1 == \
           updated_pair_strat_basemodel.strat_limits_update_seq_num, \
        f"Mismatch pair_strat.strat_limits_update_seq_num: expected " \
        f"{stored_pair_strat_basemodel.strat_limits_update_seq_num} received " \
        f"{updated_pair_strat_basemodel.strat_limits_update_seq_num}"
    assert stored_pair_strat_basemodel.pair_strat_params_update_seq_num == \
           updated_pair_strat_basemodel.pair_strat_params_update_seq_num, \
        f"Mismatch pair_strat.pair_strat_params_update_seq_num: expected " \
        f"{stored_pair_strat_basemodel.pair_strat_params_update_seq_num} received " \
        f"{updated_pair_strat_basemodel.pair_strat_params_update_seq_num}"
    assert expected_strat_status == updated_pair_strat_basemodel.strat_status, \
        f"Mismatch pair_strat.strat_status: expected {expected_strat_status}, " \
        f"received {updated_pair_strat_basemodel.strat_status}"
    assert expected_strat_limits == updated_pair_strat_basemodel.strat_limits, \
        f"Mismatch pair_strat.strat_limits: expected {expected_strat_limits}, " \
        f"received {updated_pair_strat_basemodel.strat_limits}"
    print(f"strat updated, {updated_pair_strat_basemodel}")

    # Setting pair_strat to active state
    pair_strat_active_obj = PairStratBaseModel(_id=stored_pair_strat_basemodel.id)
    pair_strat_active_obj.strat_status = StratStatus(strat_state=StratState.StratState_ACTIVE)
    activated_pair_strat_basemodel = \
        strat_manager_service_native_web_client.patch_pair_strat_client(jsonable_encoder(pair_strat_active_obj, by_alias=True, exclude_none=True))

    assert updated_pair_strat_basemodel.frequency + 1 == activated_pair_strat_basemodel.frequency, \
        f"Mismatch pair_strat_basemodel.frequency: expected {updated_pair_strat_basemodel.frequency + 1}, " \
        f"received {activated_pair_strat_basemodel.frequency}"
    assert updated_pair_strat_basemodel.strat_status_update_seq_num + 1 == \
           activated_pair_strat_basemodel.strat_status_update_seq_num, \
        f"Mismatch pair_strat.strat_status_update_seq_num: expected " \
        f"{updated_pair_strat_basemodel.strat_status_update_seq_num + 1}, received " \
        f"{activated_pair_strat_basemodel.strat_status_update_seq_num}"
    assert updated_pair_strat_basemodel.strat_limits_update_seq_num == \
           activated_pair_strat_basemodel.strat_limits_update_seq_num, \
        f"Mismatch pair_strat.strat_limits_update_seq_num: expected " \
        f"{updated_pair_strat_basemodel.strat_limits_update_seq_num}, received " \
        f"{activated_pair_strat_basemodel.strat_limits_update_seq_num}"
    assert updated_pair_strat_basemodel.pair_strat_params_update_seq_num == \
           activated_pair_strat_basemodel.pair_strat_params_update_seq_num, \
        f"Mismatch pair_strat.pair_strat_params_update_seq_num: expected " \
        f"{updated_pair_strat_basemodel.pair_strat_params_update_seq_num}, received " \
        f"{activated_pair_strat_basemodel.pair_strat_params_update_seq_num}"
    assert activated_pair_strat_basemodel.pair_strat_params == stored_pair_strat_basemodel.pair_strat_params, \
        f"Mismatch pair_strat.pair_strat_params: expected " \
        f"{stored_pair_strat_basemodel.pair_strat_params_update_seq_num}, received " \
        f"{activated_pair_strat_basemodel.pair_strat_params_update_seq_num}"
    assert StratState.StratState_ACTIVE == \
           activated_pair_strat_basemodel.strat_status.strat_state, \
        f"Mismatch pair_strat.strat_status.strat_state: expected " \
        f"StratState.StratState_ACTIVE received " \
        f"{activated_pair_strat_basemodel.strat_status.strat_state}"
    assert activated_pair_strat_basemodel.strat_limits == expected_strat_limits, \
        f"Mismatch pair_strat.strat_limits: expected {expected_strat_limits}, " \
        f"received {activated_pair_strat_basemodel.strat_limits}"
    print(f"strat activated, {activated_pair_strat_basemodel}")

    return activated_pair_strat_basemodel


def create_if_not_exists_and_validate_strat_collection(pair_strat_: PairStratBaseModel):
    strat_collection_obj_list = strat_manager_service_native_web_client.get_all_strat_collection_client()

    strat_key = f"{pair_strat_.pair_strat_params.strat_leg2.sec.sec_id}-" \
                f"{pair_strat_.pair_strat_params.strat_leg1.sec.sec_id}-" \
                f"{pair_strat_.pair_strat_params.strat_leg1.side}-{pair_strat_.id}"
    if len(strat_collection_obj_list) == 0:
        strat_collection_basemodel = StratCollectionBaseModel(**{
            "_id": 1,
            "loaded_strat_keys": [
                strat_key
            ],
            "buffered_strat_keys": []
        })
        created_strat_collection = \
            strat_manager_service_native_web_client.create_strat_collection_client(strat_collection_basemodel)

        assert created_strat_collection == strat_collection_basemodel, \
            f"Mismatch strat_collection: expected {strat_collection_basemodel} received {created_strat_collection}"

    else:
        strat_collection_obj = strat_collection_obj_list[0]
        strat_collection_obj.loaded_strat_keys.append(strat_key)
        updated_strat_collection_obj = \
            strat_manager_service_native_web_client.put_strat_collection_client(jsonable_encoder(strat_collection_obj, by_alias=True, exclude_none=True))

        assert updated_strat_collection_obj == strat_collection_obj, \
            f"Mismatch strat_collection: expected {strat_collection_obj} received {updated_strat_collection_obj}"


def run_symbol_overview(buy_symbol: str, sell_symbol: str,
                        symbol_overview_obj_list: List[SymbolOverviewBaseModel]):
    for index, symbol_overview_obj in enumerate(symbol_overview_obj_list):
        if index == 0:
            symbol_overview_obj.symbol = buy_symbol
        else:
            symbol_overview_obj.symbol = sell_symbol
        symbol_overview_obj.id = None
        created_symbol_overview = market_data_web_client.create_symbol_overview_client(symbol_overview_obj)
        symbol_overview_obj.id = created_symbol_overview.id
        assert created_symbol_overview == symbol_overview_obj, f"Created symbol_overview {symbol_overview_obj} not " \
                                                               f"equals to expected symbol_overview " \
                                                               f"{created_symbol_overview}"


def create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list: List[MarketDepthBaseModel]):
    for index, market_depth_basemodel in enumerate(market_depth_basemodel_list):
        if index < 10:
            market_depth_basemodel.symbol = buy_symbol
        else:
            market_depth_basemodel.symbol = sell_symbol
        created_market_depth = market_data_web_client.create_market_depth_client(market_depth_basemodel)
        created_market_depth.id = None
        created_market_depth.cumulative_avg_px = None
        created_market_depth.cumulative_notional = None
        created_market_depth.cumulative_qty = None
        assert created_market_depth == market_depth_basemodel, \
            f"Mismatch market_depth: expected {market_depth_basemodel} received {created_market_depth}"


def wait_for_get_new_order_placed_from_tob(wait_stop_px: int | float, symbol_to_check: str,
                                           last_update_date_time: DateTime | None, side: Side):
    loop_counter = 0
    loop_limit = 10
    while True:
        time.sleep(2)

        tob_obj_list = market_data_web_client.get_all_top_of_book_client()

        for tob_obj in tob_obj_list:
            if tob_obj.symbol == symbol_to_check:
                if side == Side.BUY:
                    if tob_obj.bid_quote.px == wait_stop_px:
                        return tob_obj.last_update_date_time
                else:
                    if tob_obj.ask_quote.px == wait_stop_px:
                        return tob_obj.last_update_date_time

        loop_counter += 1
        if loop_counter == loop_limit:
            assert False, f"Could not find any update after {last_update_date_time} in tob_list {tob_obj_list}, " \
                          f"symbol - {symbol_to_check} and wait_stop_px - {wait_stop_px}"


def set_n_verify_limits(expected_order_limits_obj, expected_portfolio_limits_obj):
    created_order_limits_obj = strat_manager_service_native_web_client.create_order_limits_client(expected_order_limits_obj)
    assert created_order_limits_obj == expected_order_limits_obj, \
        f"Mismatch order_limits: expected {expected_order_limits_obj} received {created_order_limits_obj}"

    created_portfolio_limits_obj = \
        strat_manager_service_native_web_client.create_portfolio_limits_client(expected_portfolio_limits_obj)
    assert created_portfolio_limits_obj == expected_portfolio_limits_obj, \
        f"Mismatch portfolio_limits: expected {expected_portfolio_limits_obj} received {created_portfolio_limits_obj}"


def create_n_verify_portfolio_status(portfolio_status_obj: PortfolioStatusBaseModel):
    portfolio_status_obj.id = 1
    created_portfolio_status = strat_manager_service_native_web_client.create_portfolio_status_client(portfolio_status_obj)
    assert created_portfolio_status == portfolio_status_obj, \
        f"Mismatch portfolio_status: expected {portfolio_status_obj}, received {created_portfolio_status}"


def verify_portfolio_status(total_loop_count: int, symbol_pair_count: int,
                            expected_portfolio_status: PortfolioStatusBaseModel):
    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
        single_sell_unfilled_qty = get_sell_order_related_values()

    expected_portfolio_status.overall_buy_notional = \
        ((single_buy_order_qty * get_px_in_usd(single_buy_order_px)) +
         (single_buy_filled_qty * get_px_in_usd(single_buy_filled_px - single_buy_order_px)) -
         (single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px))) * total_loop_count * symbol_pair_count
    expected_portfolio_status.overall_buy_fill_notional = \
        single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * total_loop_count * symbol_pair_count
    expected_portfolio_status.overall_sell_notional = \
        ((single_sell_order_qty * get_px_in_usd(single_sell_order_px)) +
         (single_sell_filled_qty * get_px_in_usd(single_sell_filled_px - single_sell_order_px)) -
         (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px))) * total_loop_count * symbol_pair_count
    expected_portfolio_status.overall_sell_fill_notional = \
        single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) * total_loop_count * symbol_pair_count

    portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
    for portfolio_status in portfolio_status_list:
        portfolio_status.portfolio_alerts = []
        portfolio_status.alert_update_seq_num = 0
    assert expected_portfolio_status in portfolio_status_list, f"Couldn't find {expected_portfolio_status} in " \
                                                               f"{portfolio_status_list}"


def get_latest_order_journal_with_status_and_symbol(expected_order_event, expected_symbol,
                                                    expect_no_order: bool | None = None,
                                                    last_order_id: str | None = None,
                                                    max_loop_count: int | None = None,
                                                    loop_wait_secs: int | None = None):
    start_time = DateTime.utcnow()
    placed_order_journal = None
    if max_loop_count is None:
        max_loop_count = 40
    if loop_wait_secs is None:
        loop_wait_secs = 2

    for loop_count in range(max_loop_count):
        stored_order_journal_list = strat_manager_service_native_web_client.get_all_order_journal_client()
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event == expected_order_event and \
                    stored_order_journal.order.security.sec_id == expected_symbol:
                if last_order_id is None:
                    placed_order_journal = stored_order_journal
                else:
                    if last_order_id != stored_order_journal.order.order_id:
                        placed_order_journal = stored_order_journal
                        # since get_all return orders in descendant order of date_time, first match is latest
                break
        if placed_order_journal is not None:
            break
        time.sleep(loop_wait_secs)

    time_delta = DateTime.utcnow() - start_time
    print(f"Found placed_order_journal - {placed_order_journal} in {time_delta.total_seconds()}, "
          f"for symbol {expected_symbol}, order_event {expected_order_event}, "
          f"expect_no_order {expect_no_order} and last_order_id {last_order_id}")

    if expect_no_order:
        assert placed_order_journal is None, f"Expected no new order for symbol {expected_symbol}, " \
                                             f"received {placed_order_journal}"
        placed_order_journal = OrderJournalBaseModel(order=OrderBriefOptional(order_id=last_order_id))
    else:
        assert placed_order_journal is not None, \
            f"Can't find any order_journal with symbol {expected_symbol} order_event {expected_order_event}, " \
            f"expect_no_order {expect_no_order} and last_order_id {last_order_id}"

    return placed_order_journal


def get_latest_fill_journal_from_order_id(expected_order_id: str):
    found_fill_journal = None

    stored_fill_journals = strat_manager_service_native_web_client.get_all_fills_journal_client()
    for stored_fill_journal in stored_fill_journals:
        if stored_fill_journal.order_id == expected_order_id:
            # since fills_journal is having option to sort in descending, first occurrence will be latest
            found_fill_journal = stored_fill_journal
            break
    assert found_fill_journal is not None, f"Can't find any fill_journal with order_id {expected_order_id}"
    return found_fill_journal


def get_fill_journals_for_order_id(expected_order_id: str):
    found_fill_journals = []

    stored_fill_journals = strat_manager_service_native_web_client.get_all_fills_journal_client()
    for stored_fill_journal in stored_fill_journals:
        if stored_fill_journal.order_id == expected_order_id:
            found_fill_journals.append(stored_fill_journal)
    assert len(found_fill_journals) != 0, f"Can't find any fill_journal with order_id {expected_order_id}"
    return found_fill_journals


def place_new_order(sec_id: str, side: Side, px: float, qty: int):
    security = Security(sec_id=sec_id, sec_type=SecurityType.TICKER)
    new_order_obj = NewOrderBaseModel(security=security, side=side, px=px, qty=qty)
    created_new_order_obj = strat_manager_service_native_web_client.create_new_order_client(new_order_obj)

    new_order_obj.id = created_new_order_obj.id
    assert created_new_order_obj == new_order_obj, f"Mismatch new_order_obj: expected {new_order_obj}, " \
                                                   f"received {created_new_order_obj}"


def create_pre_order_test_requirements(buy_symbol: str, sell_symbol: str, pair_strat_: PairStratBaseModel,
                                       expected_strat_limits_: StratLimits, expected_start_status_: StratStatus,
                                       symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                       last_trade_fixture_list: List[Dict],
                                       market_depth_basemodel_list: List[MarketDepthBaseModel]) -> PairStratBaseModel:
    print(f"Test started, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
    # running symbol_overview
    run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list)
    print(f"SymbolOverview created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
    # Creating Strat
    active_pair_strat = create_n_validate_strat(buy_symbol, sell_symbol, copy.deepcopy(pair_strat_),
                                                copy.deepcopy(expected_strat_limits_),
                                                copy.deepcopy(expected_start_status_))
    print(f"strat created, buy_symbol: {buy_symbol}, sell symbol: {sell_symbol}")

    # running Last Trade
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    print(f"LastTrade created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # creating market_depth
    create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)
    print(f"market_depth created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # time.sleep(100)
    # Adding strat in strat_collection
    create_if_not_exists_and_validate_strat_collection(active_pair_strat)
    print(f"Added to strat_collection, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return active_pair_strat


def fx_symbol_overview_obj() -> SymbolOverviewBaseModel:
    return SymbolOverviewBaseModel(**{
        "symbol": "USD|SGD",
        "limit_up_px": 150,
        "limit_dn_px": 50,
        "conv_px": 90,
        "closing_px": 0.5,
        "open_px": 0.5,
        "last_update_date_time": "2023-03-12T13:11:22.329Z",
        "force_publish": False
    })


def get_px_in_usd(px: float):
    return px / fx_symbol_overview_obj().closing_px


def handle_test_buy_sell_order(buy_symbol: str, sell_symbol: str, total_loop_count: int, symbol_pair_counter: int,
                               residual_test_wait: int, buy_order_: OrderJournalBaseModel,
                               sell_order_: OrderJournalBaseModel,
                               buy_fill_journal_: FillsJournalBaseModel, sell_fill_journal_: FillsJournalBaseModel,
                               expected_buy_order_snapshot_: OrderSnapshotBaseModel,
                               expected_sell_order_snapshot_: OrderSnapshotBaseModel,
                               expected_symbol_side_snapshot_: List[SymbolSideSnapshotBaseModel],
                               pair_strat_: PairStratBaseModel, expected_strat_limits_: StratLimits,
                               expected_start_status_: StratStatus, expected_strat_brief_: StratBriefBaseModel,
                               expected_portfolio_status_: PortfolioStatusBaseModel, top_of_book_list_: List[Dict],
                               last_trade_fixture_list: List[Dict],
                               symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                               market_depth_basemodel_list: List[MarketDepthBaseModel],
                               is_non_systematic_run: bool = False):
    active_strat = create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                                      expected_start_status_, symbol_overview_obj_list,
                                                      last_trade_fixture_list, market_depth_basemodel_list)
    print(f"Created Strat: {active_strat}")

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    order_id = None
    for loop_count in range(1, total_loop_count + 1):
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_order_snapshot = copy.deepcopy(expected_buy_order_snapshot_)
        expected_buy_order_snapshot.order_brief.security.sec_id = buy_symbol

        expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
        expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol

        expected_strat_status = copy.deepcopy(expected_start_status_)
        expected_strat_status.strat_state = StratState.StratState_ACTIVE

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, copy.deepcopy(top_of_book_list_),
                            is_non_systematic_run)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(110, buy_symbol, buy_tob_last_update_date_time_tracker, Side.BUY)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_order
            place_new_order(buy_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                               buy_symbol, last_order_id=order_id)
        order_id = placed_order_journal.order.order_id
        create_buy_order_date_time: DateTime = placed_order_journal.order_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_buy_order_computes(loop_count, order_id, buy_symbol,
                                        placed_order_journal, expected_buy_order_snapshot,
                                        expected_buy_symbol_side_snapshot, expected_pair_strat,
                                        expected_strat_limits_, expected_strat_status,
                                        expected_strat_brief_obj, expected_portfolio_status)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order of order_id {order_id}")

        TradeSimulator.process_order_ack(order_id, current_itr_expected_buy_order_journal_.order.px,
                                         current_itr_expected_buy_order_journal_.order.qty,
                                         current_itr_expected_buy_order_journal_.order.side,
                                         current_itr_expected_buy_order_journal_.order.security.sec_id,
                                         current_itr_expected_buy_order_journal_.order.underlying_account)

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, buy_symbol)

        # Checking Ack response on placed order
        placed_buy_order_ack_receive(loop_count, order_id, create_buy_order_date_time,
                                     placed_order_journal_obj_ack_response, expected_buy_order_snapshot)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order ACK of order_id {order_id}")

        buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
        TradeSimulator.process_fill(order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
                                    Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_buy_order(loop_count, order_id, create_buy_order_date_time,
                                                buy_symbol, placed_fill_journal_obj,
                                                expected_buy_order_snapshot, expected_buy_symbol_side_snapshot,
                                                expected_pair_strat,
                                                expected_strat_limits_, expected_strat_status,
                                                expected_strat_brief_obj, expected_portfolio_status)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order FILL of order_id {order_id}")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")

    order_id = None
    for loop_count in range(1, total_loop_count + 1):
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_order_snapshot = copy.deepcopy(expected_sell_order_snapshot_)
        expected_sell_order_snapshot.order_brief.security.sec_id = sell_symbol

        expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
        expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol

        expected_strat_status = copy.deepcopy(expected_start_status_)
        expected_strat_status.strat_state = StratState.StratState_ACTIVE

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)
        current_itr_expected_sell_order_journal_.order.security.sec_id = sell_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_sell_top_of_book(sell_symbol, is_non_systematic_run)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_order
            place_new_order(sell_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                               sell_symbol, last_order_id=order_id)
        create_sell_order_date_time: DateTime = placed_order_journal.order_event_date_time
        order_id = placed_order_journal.order.order_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_sell_order_computes(loop_count, total_loop_count, order_id,
                                         sell_symbol, placed_order_journal, expected_sell_order_snapshot,
                                         expected_sell_symbol_side_snapshot, expected_pair_strat,
                                         expected_strat_limits_, expected_strat_status,
                                         expected_strat_brief_obj, expected_portfolio_status)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order of order_id {order_id}")

        TradeSimulator.process_order_ack(order_id, current_itr_expected_sell_order_journal_.order.px,
                                         current_itr_expected_sell_order_journal_.order.qty,
                                         current_itr_expected_sell_order_journal_.order.side,
                                         current_itr_expected_sell_order_journal_.order.security.sec_id,
                                         current_itr_expected_sell_order_journal_.order.underlying_account)

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, sell_symbol)

        # Checking Ack response on placed order
        placed_sell_order_ack_receive(loop_count, order_id, create_sell_order_date_time,
                                      total_loop_count, placed_order_journal_obj_ack_response,
                                      expected_sell_order_snapshot)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed order ACK of order_id {order_id}")

        sell_fill_journal_obj = copy.deepcopy(sell_fill_journal_)
        TradeSimulator.process_fill(order_id, sell_fill_journal_obj.fill_px, sell_fill_journal_obj.fill_qty,
                                    Side.SELL, sell_symbol, sell_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_sell_order(loop_count, total_loop_count, order_id,
                                                 create_sell_order_date_time, sell_symbol, placed_fill_journal_obj,
                                                 expected_sell_order_snapshot, expected_sell_symbol_side_snapshot,
                                                 expected_pair_strat, expected_strat_limits_,
                                                 expected_strat_status, expected_strat_brief_obj,
                                                 expected_portfolio_status)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order FILL")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")


def get_pair_strat_from_symbol(symbol: str):
    pair_strat_obj_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    for pair_strat_obj in pair_strat_obj_list:
        if pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id == symbol or \
                pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id == symbol:
            return pair_strat_obj


def get_order_snapshot_from_order_id(order_id) -> OrderSnapshotBaseModel | None:
    order_snapshot_list = strat_manager_service_native_web_client.get_all_order_snapshot_client()
    expected_order_snapshot: OrderSnapshotBaseModel | None = None
    for order_snapshot in order_snapshot_list:
        if order_snapshot.order_brief.order_id == order_id:
            expected_order_snapshot = order_snapshot
            break
    assert expected_order_snapshot is not None, "Expected order_snapshot as not None but received as None"
    return expected_order_snapshot


def create_fx_symbol_overview():
    symbol_overview = fx_symbol_overview_obj()
    created_symbol_overview = market_data_web_client.create_symbol_overview_client(symbol_overview)
    symbol_overview.id = created_symbol_overview.id
    assert created_symbol_overview == symbol_overview, f"Mismatch symbol_overview: expected {symbol_overview}, " \
                                                       f"received {created_symbol_overview}"


def verify_rej_orders(check_ack_to_reject_orders: bool, last_order_id: int | None,
                      check_order_event: OrderEventType, symbol: str) -> str:
    # internally checks order_journal is not None else raises assert exception internally
    latest_order_journal = get_latest_order_journal_with_status_and_symbol(check_order_event, symbol,
                                                                           last_order_id=last_order_id)
    last_order_id = latest_order_journal.order.order_id

    if check_ack_to_reject_orders:
        if check_order_event != OrderEventType.OE_REJ:
            # internally checks fills_journal is not None else raises assert exception internally
            latest_fill_journal = get_latest_fill_journal_from_order_id(latest_order_journal.order.order_id)

    order_snapshot = get_order_snapshot_from_order_id(last_order_id)
    assert order_snapshot.order_status == OrderStatusType.OE_DOD, \
        "Unexpected order_snapshot.order_status: expected OrderStatusType.OE_DOD, " \
        f"received {order_snapshot.order_status}"

    return last_order_id


def handle_rej_order_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                          expected_start_status_, symbol_overview_obj_list,
                          last_trade_fixture_list, market_depth_basemodel_list,
                          top_of_book_list_, max_loop_count_per_side, check_ack_to_reject_orders: bool):
    for buy_symbol, sell_symbol in buy_sell_symbol_list:
        # explicitly setting waived_min_orders to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_orders = 10
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)

        # buy fills check
        continues_order_count, continues_special_order_count = get_continuous_order_configs(buy_symbol)
        buy_order_count = 0
        buy_special_order_count = 0
        last_id = None
        for loop_count in range(1, max_loop_count_per_side + 1):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
            time.sleep(2)  # delay for order to get placed

            if buy_order_count < continues_order_count:
                check_order_event = OrderEventType.OE_CXL_ACK
                buy_order_count += 1
            else:
                if buy_special_order_count < continues_special_order_count:
                    check_order_event = OrderEventType.OE_REJ
                    buy_special_order_count += 1
                else:
                    check_order_event = OrderEventType.OE_CXL_ACK
                    buy_order_count = 1
                    buy_special_order_count = 0

            # internally contains assert checks
            last_id = verify_rej_orders(check_ack_to_reject_orders, last_id, check_order_event, buy_symbol)

        # sell fills check
        continues_order_count, continues_special_order_count = get_continuous_order_configs(sell_symbol)
        last_id = None
        sell_order_count = 0
        sell_special_order_count = 0
        for loop_count in range(1, max_loop_count_per_side + 1):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_sell_top_of_book(sell_symbol)
            time.sleep(2)  # delay for order to get placed

            if sell_order_count < continues_order_count:
                check_order_event = OrderEventType.OE_CXL_ACK
                sell_order_count += 1
            else:
                if sell_special_order_count < continues_special_order_count:
                    check_order_event = OrderEventType.OE_REJ
                    sell_special_order_count += 1
                else:
                    check_order_event = OrderEventType.OE_CXL_ACK
                    sell_order_count = 1
                    sell_special_order_count = 0

            # internally contains assert checks
            last_id = verify_rej_orders(check_ack_to_reject_orders, last_id, check_order_event, sell_symbol)


def verify_cxl_rej(last_cxl_order_id: str | None, last_cxl_rej_order_id: str | None,
                   check_order_event: OrderEventType, symbol: str) -> Tuple[str, str]:
    if check_order_event == OrderEventType.OE_CXL_REJ:
        # internally checks order_journal is not None else raises assert exception internally
        latest_cxl_rej_order_journal = \
            get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_REJ, symbol,
                                                            last_order_id=last_cxl_rej_order_id)
        last_cxl_rej_order_id = latest_cxl_rej_order_journal.order.order_id

        order_snapshot = get_order_snapshot_from_order_id(latest_cxl_rej_order_journal.order.order_id)
        if order_snapshot.order_brief.qty > order_snapshot.filled_qty:
            assert order_snapshot.order_status == OrderStatusType.OE_ACKED, \
                "Unexpected order_snapshot.order_status: expected OrderStatusType.OE_ACKED, " \
                f"received {order_snapshot.order_status}"
        elif order_snapshot.order_brief.qty < order_snapshot.filled_qty:
            assert order_snapshot.order_status == OrderStatusType.OE_OVER_FILLED, \
                "Unexpected order_snapshot.order_status: expected OrderStatusType.OE_OVER_FILLED, " \
                f"received {order_snapshot.order_status}"
        else:
            assert order_snapshot.order_status == OrderStatusType.OE_FILLED, \
                "Unexpected order_snapshot.order_status: expected OrderStatusType.OE_FILLED, " \
                f"received {order_snapshot.order_status}"

    # internally checks order_journal is not None else raises assert exception internally
    latest_cxl_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK, symbol,
                                                                               last_order_id=last_cxl_order_id)
    last_cxl_order_id = latest_cxl_order_journal.order.order_id

    return last_cxl_order_id, last_cxl_rej_order_id


def create_fills_for_underlying_account_test(buy_symbol: str, sell_symbol: str, top_of_book_list_: List[Dict],
                                             tob_last_update_date_time_tracker: DateTime | None,
                                             order_id: str | None, underlying_account_prefix: str, side: Side):
    loop_count = 1
    if side == Side.BUY:
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
        symbol = buy_symbol
        wait_stop_px = 110
    else:
        run_sell_top_of_book(sell_symbol)
        symbol = sell_symbol
        wait_stop_px = 120

    # Waiting for tob to trigger place order
    tob_last_update_date_time_tracker = \
        wait_for_get_new_order_placed_from_tob(wait_stop_px, symbol, tob_last_update_date_time_tracker, side)

    placed_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                           symbol, last_order_id=order_id)
    order_id = placed_order_journal.order.order_id

    TradeSimulator.process_order_ack(order_id, placed_order_journal.order.px,
                                     placed_order_journal.order.qty,
                                     placed_order_journal.order.side,
                                     placed_order_journal.order.security.sec_id,
                                     placed_order_journal.order.underlying_account)
    fills_count = 6
    fill_px = 100
    fill_qty = 5
    for loop_count in range(fills_count):
        if loop_count + 1 <= (fills_count / 2):
            underlying_account = f"{underlying_account_prefix}_1"
        else:
            underlying_account = f"{underlying_account_prefix}_2"
        TradeSimulator.process_fill(order_id, fill_px, fill_qty,
                                    placed_order_journal.order.side,
                                    placed_order_journal.order.security.sec_id, underlying_account)
    return tob_last_update_date_time_tracker, order_id


def verify_unsolicited_cxl_orders(last_id: str | None,
                                  check_order_event: OrderEventType, symbol: str) -> str:
    # internally checks order_journal is not None else raises assert exception internally
    if check_order_event == OrderEventType.OE_CXL:
        latest_order_journal = get_latest_order_journal_with_status_and_symbol(check_order_event, symbol,
                                                                               last_order_id=last_id)
    else:
        # checking no latest order with OE_CXL
        latest_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL, symbol,
                                                                               expect_no_order=True,
                                                                               last_order_id=last_id)

    return latest_order_journal.order.order_id


def handle_unsolicited_cxl_for_sides(symbol: str, last_id: str, last_cxl_ack_id: str, order_count: int,
                                     continues_order_count: int, cxl_count: int, continues_unsolicited_cxl_count: int):
    if order_count < continues_order_count:
        check_order_event = OrderEventType.OE_CXL
        order_count += 1
        time.sleep(10)
    else:
        if cxl_count < continues_unsolicited_cxl_count:
            check_order_event = OrderEventType.OE_CXL_ACK
            cxl_count += 1
        else:
            check_order_event = OrderEventType.OE_CXL
            order_count = 1
            cxl_count = 0
            time.sleep(10)

    # internally contains assert checks
    last_id = verify_unsolicited_cxl_orders(last_id, check_order_event, symbol)
    latest_cxl_ack_obj = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK,
                                                                         symbol, last_order_id=last_cxl_ack_id)
    last_cxl_ack_id = latest_cxl_ack_obj.order.order_id

    return last_id, last_cxl_ack_id, order_count, cxl_count


def handle_unsolicited_cxl(buy_sell_symbol_list, expected_strat_limits_, expected_start_status_, pair_strat_,
                           symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
                           max_loop_count_per_side, top_of_book_list_):
    # updating fixture values for this test-case
    max_loop_count_per_side = 5
    buy_sell_symbol_list = buy_sell_symbol_list[:2]

    for buy_symbol, sell_symbol in buy_sell_symbol_list:
        # explicitly setting waived_min_orders to 10 for this test case
        expected_strat_limits_.cancel_rate.waived_min_orders = 10
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list)
        # buy fills check
        continues_order_count, continues_special_order_count = get_continuous_order_configs(buy_symbol)
        buy_order_count = 0
        buy_cxl_order_count = 0
        last_id = None
        last_cxl_ack_id = None
        for loop_count in range(1, max_loop_count_per_side + 1):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
            time.sleep(2)  # delay for order to get placed

            last_id, last_cxl_ack_id, buy_order_count, buy_cxl_order_count = \
                handle_unsolicited_cxl_for_sides(buy_symbol, last_id, last_cxl_ack_id,
                                                 buy_order_count, continues_order_count,
                                                 buy_cxl_order_count, continues_special_order_count)

        # sell fills check
        continues_order_count, continues_special_order_count = get_continuous_order_configs(sell_symbol)
        sell_order_count = 0
        sell_cxl_order_count = 0
        last_id = None
        last_cxl_ack_id = None
        for loop_count in range(1, max_loop_count_per_side + 1):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
            run_sell_top_of_book(sell_symbol)
            time.sleep(2)  # delay for order to get placed

            last_id, last_cxl_ack_id, sell_order_count, sell_cxl_order_count = \
                handle_unsolicited_cxl_for_sides(sell_symbol, last_id, last_cxl_ack_id,
                                                 sell_order_count, continues_order_count,
                                                 sell_cxl_order_count, continues_special_order_count)


def handle_partial_ack_checks(symbol: str, new_order_id: str, acked_order_id: str):
    new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW,
                                                                        symbol, last_order_id=new_order_id)
    new_order_id = new_order_journal.order.order_id
    partial_ack_qty = TradeSimulator.get_partial_allowed_ack_qty(symbol, new_order_journal.order.qty)

    ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK,
                                                                        symbol, last_order_id=acked_order_id)
    acked_order_id = ack_order_journal.order.order_id
    assert ack_order_journal.order.qty == partial_ack_qty, f"Mismatch partial_ack_qty: expected {partial_ack_qty}, " \
                                                           f"received {ack_order_journal.order.qty}"

    return new_order_id, acked_order_id, partial_ack_qty


def underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list)

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    loop_count = 1
    run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)


def handle_place_order_for_portfolio_lvl_limit_test(symbol: str, side: Side, px: float, qty: int,
                                                    check_str: str, assert_fail_msg: str):
    # placing new non-systematic new_order
    place_new_order(symbol, side, px, qty)
    print(f"symbol: {symbol}, Created new_order obj")

    new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW, symbol,
                                                                        expect_no_order=True)

    portfolio_status = strat_manager_service_native_web_client.get_portfolio_status_client(1)
    portfolio_alerts = portfolio_status.portfolio_alerts

    for alert in portfolio_alerts:
        if check_str in alert.alert_brief:
            break
    else:
        assert False, assert_fail_msg
    assert True


def handle_place_order_and_check_str_in_alert_for_executor_limits(symbol: str, side: Side, px: float, qty: int,
                                                                  check_str: str, assert_fail_msg: str,
                                                                  last_order_id: str | None = None):
    # placing new non-systematic new_order
    place_new_order(symbol, side, px, qty)
    print(f"symbol: {symbol}, Created new_order obj")

    new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_NEW, symbol,
                                                                        expect_no_order=True,
                                                                        last_order_id=last_order_id)

    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # assuming only one strat exists
    strat_alerts = pair_strat_list[0].strat_status.strat_alerts

    for alert in strat_alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_msg
    assert True


def handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(buy_sell_symbol_list, pair_strat_,
                                                                        expected_strat_limits_,
                                                                        expected_start_status_,
                                                                        symbol_overview_obj_list,
                                                                        last_trade_fixture_list,
                                                                        market_depth_basemodel_list,
                                                                        top_of_book_list_, side: Side):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 1
    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list)

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    loop_count = 1
    run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)

    check_symbol = buy_symbol if side == Side.BUY else sell_symbol

    px = 100
    qty = 90
    check_str = f"Consumable cxl qty can't be < 0, currently is .* for symbol {check_symbol}"
    assert_fail_message = "Could not find any alert containing message to block orders due to less buy consumable " \
                          "cxl qty"
    # placing new non-systematic new_order
    place_new_order(check_symbol, side, px, qty)
    print(f"symbol: {check_symbol}, Created new_order obj")

    new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK, check_symbol)
    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # since only one strat exists for current test
    assert len(pair_strat_list) == 1
    pair_strat_obj = pair_strat_list[0]

    for alert in pair_strat_obj.strat_status.strat_alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message
    assert True


def handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
        buy_sell_symbol_list, pair_strat_, expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, side):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 0
    expected_strat_limits_.cancel_rate.max_cancel_rate = 19
    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list)

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    loop_count = 1
    run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_, is_non_systematic_run=True)

    check_symbol = buy_symbol if side == Side.BUY else sell_symbol

    px = 100
    qty = 90
    check_str = f"Consumable cxl qty can't be < 0, currently is .* for symbol {check_symbol}"
    assert_fail_message = "Could not find any alert containing message to block orders due to less buy consumable " \
                          "cxl qty"
    # placing new non-systematic new_order
    place_new_order(check_symbol, side, px, qty)
    print(f"symbol: {check_symbol}, Created new_order obj")

    ack_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK, check_symbol)
    cxl_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_CXL_ACK, check_symbol)
    pair_strat_list = strat_manager_service_native_web_client.get_all_pair_strat_client()
    # since only one strat exists for current test
    assert len(pair_strat_list) == 1
    pair_strat_obj = pair_strat_list[0]

    for alert in pair_strat_obj.strat_status.strat_alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        assert False, assert_fail_message
    assert True


def underlying_handle_simulated_partial_fills_test(loop_count, check_symbol, buy_symbol,
                                                   sell_symbol, last_trade_fixture_list,
                                                   top_of_book_list_, last_order_id):
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    if check_symbol == buy_symbol:
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
    else:
        run_sell_top_of_book(sell_symbol)

    order_ack_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK,
                                                                        check_symbol, last_order_id=last_order_id)
    last_order_id = order_ack_journal.order.order_id

    # TradeSimulator.reload_configs()
    partial_filled_qty = TradeSimulator.get_partial_allowed_fill_qty(check_symbol, order_ack_journal.order.qty)

    latest_fill_journal = get_latest_fill_journal_from_order_id(last_order_id)
    assert latest_fill_journal.fill_qty == partial_filled_qty, f"fill_qty mismatch: expected {partial_filled_qty}, " \
                                                               f"received {latest_fill_journal.fill_qty}"
    return last_order_id, partial_filled_qty


def underlying_handle_simulated_multi_partial_fills_test(loop_count, check_symbol, buy_symbol,
                                                         sell_symbol, last_trade_fixture_list,
                                                         top_of_book_list_, last_order_id,
                                                         fill_id: str | None = None):
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)
    if check_symbol == buy_symbol:
        run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)
    else:
        run_sell_top_of_book(sell_symbol)

    new_order_journal = get_latest_order_journal_with_status_and_symbol(OrderEventType.OE_ACK,
                                                                        check_symbol, last_order_id=last_order_id)
    last_order_id = new_order_journal.order.order_id
    partial_filled_qty = TradeSimulator.get_partial_allowed_fill_qty(check_symbol, new_order_journal.order.qty)

    fills_count = TradeSimulator.get_symbol_configs(check_symbol).get("total_fill_count")
    time.sleep(5)
    time_out_loop_count = 5
    latest_fill_journals = []
    for _ in range(time_out_loop_count):
        latest_fill_journals = get_fill_journals_for_order_id(last_order_id)
        if loop_count == fills_count:
            break
        time.sleep(2)

    assert fills_count == len(latest_fill_journals), f"Mismatch numbers of fill for order_id {last_order_id}, " \
                                                     f"expected {fills_count} received {len(latest_fill_journals)}"

    for latest_fill_journal in latest_fill_journals:
        assert latest_fill_journal.fill_qty == partial_filled_qty, f"Mismatch partial_filled_qty: " \
                                                                   f"expected {partial_filled_qty}, received " \
                                                                   f"{latest_fill_journal.fill_px}"
    return last_order_id, partial_filled_qty


def get_mongo_server_uri():
    mongo_server_uri: str = "mongodb://localhost:27017"
    if os.path.isfile(str(test_config_file_path)):
        test_config = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
        mongo_server_uri = fetched_mongo_server_uri if \
            (fetched_mongo_server_uri := test_config.get("mongo_server_uri")) is not None else mongo_server_uri
    return mongo_server_uri


def clean_today_activated_ticker_dict():
    command_n_control_obj: CommandNControlBaseModel = CommandNControlBaseModel(command_type=CommandType.CLEAR_STRAT, datetime=DateTime.utcnow())
    strat_manager_service_native_web_client.create_command_n_control_client(command_n_control_obj)


def clear_cache_in_model():
    command_n_control_obj: CommandNControlBaseModel = CommandNControlBaseModel(command_type=CommandType.RESET_STATE,
                                                                               datetime=DateTime.utcnow())
    strat_manager_service_native_web_client.create_command_n_control_client(command_n_control_obj)


def append_csv_file(file_name: str, records: List[List[any]]):
    with open(file_name, "a") as csv_file:
        list_writer = writer(csv_file)
        record: List[any]
        for record in records:
            list_writer.writerow(record)