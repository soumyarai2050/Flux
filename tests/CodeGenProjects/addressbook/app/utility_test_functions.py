import logging
import signal
import sys
import threading
import time
import copy
import re
import pexpect
from csv import writer
import os
import glob
import traceback
from datetime import timedelta
os.environ["PORT"] = "8081"
os.environ["DBType"] = "beanie"

# project imports
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_client import \
    StratManagerServiceHttpClient
from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_client import \
    MarketDataServiceHttpClient
from Flux.CodeGenProjects.addressbook.app.static_data import SecurityRecordManager
from FluxPythonUtils.scripts.utility_functions import clean_mongo_collections, YAMLConfigurationManager, parse_to_int, \
    get_mongo_db_list, drop_mongo_database
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_http_client import (
    LogAnalyzerServiceHttpClient)
from Flux.CodeGenProjects.post_trade_engine.app.post_trade_engine_service_helper import (
    post_trade_engine_service_http_client)
from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import get_symbol_side_key

code_gen_projects_dir_path = PurePath(__file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects"

PAIR_STRAT_ENGINE_DIR = code_gen_projects_dir_path / "addressbook"
ps_config_yaml_path: PurePath = PAIR_STRAT_ENGINE_DIR / "data" / "config.yaml"
ps_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(ps_config_yaml_path))

LOG_ANALYZER_DIR = code_gen_projects_dir_path / "log_analyzer"
la_config_yaml_path = LOG_ANALYZER_DIR / "data" / "config.yaml"
la_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(la_config_yaml_path))

MARKET_DATA_DIR = code_gen_projects_dir_path / "market_data"
md_config_yaml_path = MARKET_DATA_DIR / "data" / "config.yaml"
md_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(md_config_yaml_path))

STRAT_EXECUTOR = code_gen_projects_dir_path / "strat_executor"
executor_config_yaml_path: PurePath = STRAT_EXECUTOR / "data" / "config.yaml"
executor_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(executor_config_yaml_path))

HOST: Final[str] = "127.0.0.1"
PAIR_STRAT_CACHE_HOST: Final[str] = ps_config_yaml_dict.get("server_host")
PAIR_STRAT_BEANIE_HOST: Final[str] = ps_config_yaml_dict.get("server_host")
PAIR_STRAT_CACHE_PORT: Final[str] = ps_config_yaml_dict.get("main_server_cache_port")
PAIR_STRAT_BEANIE_PORT: Final[str] = ps_config_yaml_dict.get("main_server_beanie_port")

LOG_ANALYZER_CACHE_HOST: Final[str] = la_config_yaml_dict.get("server_host")
LOG_ANALYZER_BEANIE_HOST: Final[str] = la_config_yaml_dict.get("server_host")
LOG_ANALYZER_CACHE_PORT: Final[str] = la_config_yaml_dict.get("main_server_cache_port")
LOG_ANALYZER_BEANIE_PORT: Final[str] = la_config_yaml_dict.get("main_server_beanie_port")
os.environ["HOST"] = HOST
os.environ["PAIR_STRAT_BEANIE_PORT"] = PAIR_STRAT_BEANIE_PORT

strat_manager_service_native_web_client: StratManagerServiceHttpClient = \
    StratManagerServiceHttpClient(host=PAIR_STRAT_BEANIE_HOST, port=parse_to_int(PAIR_STRAT_BEANIE_PORT))
log_analyzer_web_client: LogAnalyzerServiceHttpClient = (
    LogAnalyzerServiceHttpClient.set_or_get_if_instance_exists(host=LOG_ANALYZER_BEANIE_HOST,
                                                               port=parse_to_int(LOG_ANALYZER_BEANIE_PORT)))

static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
project_dir_path = \
    PurePath(__file__).parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "addressbook"
project_app_dir_path = project_dir_path / "app"
test_project_dir_path = PurePath(__file__).parent.parent / 'data'
test_config_file_path: PurePath = test_project_dir_path / "config.yaml"
static_data_dir: PurePath = project_dir_path / "data"


def clean_all_collections_ignoring_ui_layout(db_names_list: List[str]) -> None:
    mongo_server_uri: str = get_mongo_server_uri()
    for db_name in get_mongo_db_list(mongo_server_uri):
        if "log_analyzer" == db_name:
            clean_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=db_name,
                                    ignore_collections=["UILayout", "PortfolioAlert",
                                                        "RawPerformanceData", "ProcessedPerformanceAnalysis"])
        elif "addressbook" == db_name or "post_trade_engine" == db_name:
            ignore_collections = ["UILayout"]
            if db_name == "addressbook":
                ignore_collections.append("StratCollection")
            clean_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=db_name,
                                    ignore_collections=ignore_collections)
        elif "strat_executor_" in db_name:
            drop_mongo_database(mongo_server_uri=mongo_server_uri, database_name=db_name)


def drop_all_databases() -> None:
    mongo_server_uri: str = get_mongo_server_uri()
    for db_name in get_mongo_db_list(mongo_server_uri):
        if "log_analyzer" == db_name or "addressbook" == db_name or "post_trade_engine" == db_name or \
                "strat_executor_" in db_name:
            drop_mongo_database(mongo_server_uri=mongo_server_uri, database_name=db_name)
        # else ignore drop database


def clean_project_logs():
    # clean all project log file, strat json.lock files, generated md, so scripts and script logs
    addressbook_dir: PurePath = code_gen_projects_path / "addressbook"
    log_analyzer_dir: PurePath = code_gen_projects_path / "log_analyzer"
    post_trade_engine_dir: PurePath = code_gen_projects_path / "post_trade_engine"
    strat_executor_dir: PurePath = code_gen_projects_path / "strat_executor"
    log_file: str
    # delete addressbook, log_analyzer, post_trade_engine, strat_executor log files
    projects: List[str] = ["addressbook", "log_analyzer", "post_trade_engine", "strat_executor"]
    for project in projects:
        log_files: List[str] = glob.glob(str(code_gen_projects_path / f"{project}" / "log" / "*.log*"))
        for log_file in log_files:
            os.remove(log_file)
    # delete fx_so script and script log
    fx_script_n_log_files: List[str] = glob.glob(str(addressbook_dir / "scripts" / "fx_so.sh*"))
    for log_file in fx_script_n_log_files:
        os.remove(log_file)
    lock_files: List[str] = glob.glob(str(addressbook_dir / "data" / "*.json.lock"))
    for lock_file in lock_files:
        os.remove(lock_file)
    # delete strat json.lock files, executor simulate config files, so/md scripts and script logs
    executor_config_files: List[str] = glob.glob(str(strat_executor_dir / "data" / "executor_*_simulate_config.yaml"))
    for executor_config_file in executor_config_files:
        os.remove(executor_config_file)
    ps_id_scripts_n_log_files: List[str] = glob.glob(str(strat_executor_dir / "scripts" / "*ps_id_*.sh*"))
    for ps_id_file in ps_id_scripts_n_log_files:
        os.remove(ps_id_file)

#
# def run_pair_strat_log_analyzer(executor_n_log_analyzer: 'ExecutorNLogAnalyzerManager'):
#     log_analyzer = pexpect.spawn("python addressbook_log_analyzer.py &",
#                                  cwd=project_app_dir_path)
#     log_analyzer.timeout = None
#     log_analyzer.logfile = sys.stdout.buffer
#     executor_n_log_analyzer.pair_strat_log_analyzer_pid = log_analyzer.pid
#     print(f"pair_strat_log_analyzer PID: {log_analyzer.pid}")
#     log_analyzer.expect("CRITICAL: log analyzer running in simulation mode...")
#     log_analyzer.interact()
#
#
# def run_executor(executor_n_log_analyzer: 'ExecutorNLogAnalyzerManager'):
#     executor = pexpect.spawn("python strat_executor.py &", cwd=project_app_dir_path)
#     executor.timeout = None
#     executor.logfile = sys.stdout.buffer
#     executor_n_log_analyzer.executor_pid = executor.pid
#     print(f"executor PID: {executor.pid}")
#     executor.expect(pexpect.EOF)
#     executor.interact()
#
#
# def kill_process(kill_pid: str | int | None):
#     if kill_pid is not None:
#         os.kill(kill_pid, signal.SIGINT)
#         try:
#             # raises OSError if pid still exists
#             os.kill(kill_pid, 0)
#         except OSError:
#             return False
#         else:
#             return True
#     else:
#         return False

#
# class ExecutorNLogAnalyzerManager:
#     """
#     Context manager to handle running of trade_executor and log_analyzer in threads and after test is completed,
#     handling killing of the both processes and cleaning the slate
#     """
#
#     def __init__(self):
#         # p_id(s) are getting populated by their respective thread target functions
#         self.executor_pid = None
#         self.pair_strat_log_analyzer_pid = None
#
#     def __enter__(self):
#         executor_thread = threading.Thread(target=run_executor, args=(self,))
#         pair_strat_log_analyzer_thread = threading.Thread(target=run_pair_strat_log_analyzer, args=(self,))
#         executor_thread.start()
#         pair_strat_log_analyzer_thread.start()
#         # delay for executor and log_analyzer to get started and ready
#         time.sleep(20)
#         return self
#
#     def __exit__(self, exc_type, exc_value, exc_traceback):
#         assert kill_process(self.executor_pid), \
#             f"Something went wrong while killing trade_executor process, pid: {self.executor_pid}"
#         assert kill_process(self.pair_strat_log_analyzer_pid), \
#             f"Something went wrong while killing pair_strat_log_analyzer process, " \
#             f"pid: {self.pair_strat_log_analyzer_pid}"
#
#         # Env var based post test cleaning
#         clean_env_var = os.environ.get("ENABLE_CLEAN_SLATE")
#         if clean_env_var is not None and len(clean_env_var) and parse_to_int(clean_env_var) == 1:
#             # cleaning db
#             clean_slate_post_test()
#
#         # Env var based delay in test
#         post_test_delay = os.environ.get("POST_TEST_DELAY")
#         if post_test_delay is not None and len(post_test_delay):
#             # cleaning db
#             time.sleep(parse_to_int(post_test_delay))


def get_continuous_order_configs(symbol: str, config_dict: Dict) -> Tuple[int | None, int | None]:
    symbol_configs = get_symbol_configs(symbol, config_dict)
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


def update_expected_strat_brief_for_buy(loop_count: int, total_loop_count: int,
                                        expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                        expected_strat_limits: StratLimits,
                                        expected_strat_brief_obj: StratBriefBaseModel,
                                        date_time_for_cmp: DateTime, is_buy_sell_pair: bool = False):
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
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_orders = 4
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
    sell_side_residual_qty = 40 * total_loop_count
    sell_side_net_filled_notional = 7_200 * total_loop_count
    if is_buy_sell_pair:
        sell_side_residual_qty = 40 * (loop_count - 1)  # single_sell_unfilled_qty is 40
        sell_side_net_filled_notional = 7_200 * (loop_count - 1)  # single_sell_net_filled_notional is 7_200
    expected_strat_brief_obj.pair_buy_side_trading_brief.indicative_consumable_residual = \
        expected_strat_limits.residual_restriction.max_residual - \
        ((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty *
          get_px_in_usd(current_leg_last_trade_px)) - (sell_side_residual_qty * get_px_in_usd(other_leg_last_trade_px)))
    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = date_time_for_cmp
    expected_strat_brief_obj.consumable_nett_filled_notional = (
            160_000 - abs(expected_symbol_side_snapshot.total_fill_notional - sell_side_net_filled_notional))


def update_expected_strat_brief_for_sell(loop_count: int, total_loop_count: int,
                                         expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                         expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                         expected_strat_limits: StratLimits,
                                         expected_strat_brief_obj: StratBriefBaseModel,
                                         date_time_for_cmp: DateTime, is_buy_sell_pair: bool = False):
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
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_orders = 4
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
    buy_side_residual_qty = 40 * total_loop_count
    buy_side_net_filled_notional = 9_000 * total_loop_count
    if is_buy_sell_pair:
        buy_side_residual_qty = 40 * (loop_count - 1)  # single_buy_unfilled_qty is 40
        buy_side_net_filled_notional = 9_000 * (loop_count - 1)  # single_buy_net_filled_notional is 9_000
    expected_strat_brief_obj.pair_sell_side_trading_brief.indicative_consumable_residual = \
        expected_strat_limits.residual_restriction.max_residual - \
        ((expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty *
          get_px_in_usd(current_leg_last_trade_px)) - (buy_side_residual_qty *
                                                       get_px_in_usd(other_leg_last_trade_px)))
    expected_strat_brief_obj.pair_sell_side_trading_brief.last_update_date_time = date_time_for_cmp
    expected_strat_brief_obj.consumable_nett_filled_notional = (160_000 -
                                                                abs(buy_side_net_filled_notional -
                                                                    expected_symbol_side_snapshot.total_fill_notional))


def check_placed_buy_order_computes_before_all_sells(loop_count: int, total_order_counts: int,
                                                     expected_order_id: str, symbol: str,
                                                     buy_placed_order_journal: OrderJournalBaseModel,
                                                     expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                                     expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                     expected_pair_strat: PairStratBaseModel,
                                                     expected_strat_limits: StratLimits,
                                                     expected_strat_status: StratStatus,
                                                     expected_strat_brief_obj: StratBriefBaseModel,
                                                     expected_portfolio_status: PortfolioStatusBaseModel,
                                    executor_web_client: StratExecutorServiceHttpClient,
                                    is_buy_sell_pair: bool = False):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after order is triggered
    """
    order_journal_obj_list = executor_web_client.get_all_order_journal_client(-100)
    assert buy_placed_order_journal in order_journal_obj_list, \
        f"Couldn't find {buy_placed_order_journal} in {order_journal_obj_list}"

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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"{expected_symbol_side_snapshot} not found in " \
                                                                       f"{symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, total_order_counts, expected_order_snapshot_obj,
                                        expected_symbol_side_snapshot, expected_strat_limits, expected_strat_brief_obj,
                                        buy_placed_order_journal.order_event_date_time, is_buy_sell_pair)

    print(f"@@@ fetching strat_brief for symbol: {symbol} at {DateTime.utcnow()}")
    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
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

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num

        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # Checking strat_status
    single_sell_order_px = 0
    single_sell_order_qty = 0
    single_sell_filled_px = 0
    single_sell_filled_qty = 0
    single_sell_unfilled_qty = 0
    if is_buy_sell_pair:
        single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty, \
            single_sell_unfilled_qty = get_sell_order_related_values()
        # handle sell side strat status update
        expected_strat_status.total_sell_qty = single_sell_order_qty * (loop_count - 1)
        expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) * (
                        loop_count - 1)
        expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) * (
                    loop_count - 1)
        expected_strat_status.avg_fill_sell_px = 0
        expected_strat_status.avg_cxl_sell_px = 0
        if loop_count > 1:
            expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * (loop_count - 1)) / (
                            single_sell_filled_qty * (loop_count - 1))
            expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * (loop_count - 1)) / (
                        single_sell_unfilled_qty * (loop_count - 1))

    expected_strat_status.total_buy_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_order_qty = single_buy_order_qty * loop_count + single_sell_order_qty * (loop_count - 1)
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
                    loop_count - 1) - single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) * (loop_count - 1)
        expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (
                    single_buy_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1) - single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) * (loop_count - 1)
        buy_residual_notional = expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
            current_leg_last_trade_px)
        sell_residual_notional = single_sell_unfilled_qty * get_px_in_usd(other_leg_last_trade_px) * (loop_count - 1)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        security = expected_strat_brief_obj.pair_buy_side_trading_brief.security if \
            buy_residual_notional > sell_residual_notional else \
            expected_strat_brief_obj.pair_sell_side_trading_brief.security
        expected_strat_status.residual = Residual(security=security,
                                                  residual_notional=residual_notional)

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def check_placed_buy_order_computes_after_sells(loop_count: int, total_order_count: int,
                                                expected_order_id: str, symbol: str,
                                                buy_placed_order_journal: OrderJournalBaseModel,
                                                expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                                expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                expected_pair_strat: PairStratBaseModel,
                                                expected_strat_limits: StratLimits,
                                                expected_strat_status: StratStatus,
                                                expected_strat_brief_obj: StratBriefBaseModel,
                                                expected_portfolio_status: PortfolioStatusBaseModel,
                                                executor_web_client: StratExecutorServiceHttpClient):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after order is triggered
    """
    order_journal_obj_list = executor_web_client.get_all_order_journal_client(-100)
    assert buy_placed_order_journal in order_journal_obj_list, \
        f"Couldn't find {buy_placed_order_journal} in {order_journal_obj_list}"

    (single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty,
        single_buy_unfilled_qty) = get_buy_order_related_values()
    (single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty,
     single_sell_unfilled_qty) = get_sell_order_related_values()
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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"{expected_symbol_side_snapshot} not found in " \
                                                                       f"{symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, total_order_count,
                                        expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                        expected_strat_limits, expected_strat_brief_obj,
                                        buy_placed_order_journal.order_event_date_time)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        strat_brief.pair_buy_side_trading_brief.indicative_consumable_participation_qty = None
        strat_brief.pair_buy_side_trading_brief.participation_period_order_qty_sum = None
        strat_brief.pair_buy_side_trading_brief.last_update_date_time = None
        # Since sell side of strat_brief is already checked
        strat_brief.pair_sell_side_trading_brief = expected_strat_brief_obj.pair_sell_side_trading_brief

    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = None
    for strat_brief in strat_brief_list:
        if strat_brief.pair_buy_side_trading_brief == expected_strat_brief_obj.pair_buy_side_trading_brief:
            assert (strat_brief.consumable_nett_filled_notional ==
                    expected_strat_brief_obj.consumable_nett_filled_notional), \
                (f"Mismatched consumable_nett_filled_notional in strat_breif: "
                 f"expected consumable_nett_filled_notional: "
                 f"{expected_strat_brief_obj.consumable_nett_filled_notional}, received: "
                 f"{strat_brief.consumable_nett_filled_notional}")
            break
    else:
        assert False, (f"expected pair_sell_buy_trading_brief {expected_strat_brief_obj.pair_sell_side_trading_brief} "
                       f"not found in pair_sell_buy_trading_brief of any strat_brif from list: {strat_brief_list}")

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num

        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # Checking strat_status
    expected_strat_status.total_buy_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_sell_qty = single_sell_order_qty * total_order_count
    expected_strat_status.total_order_qty = ((single_buy_order_qty * loop_count) +
                                             (single_sell_order_qty * total_order_count))
    expected_strat_status.total_open_buy_qty = single_buy_order_qty
    expected_strat_status.avg_open_buy_px = (single_buy_order_qty * single_buy_order_px) / single_buy_order_qty
    expected_strat_status.total_open_buy_notional = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_open_exposure = single_buy_order_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * total_order_count) / (
            single_sell_filled_qty * total_order_count)
    expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * total_order_count
    expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(
        single_sell_filled_px) * total_order_count

    residual_notional = abs((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
                                current_leg_last_trade_px)) -
                            ((single_sell_unfilled_qty * total_order_count) * get_px_in_usd(other_leg_last_trade_px)))
    if (expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
                                current_leg_last_trade_px)) > ((single_sell_unfilled_qty * total_order_count) *
                                                               get_px_in_usd(other_leg_last_trade_px)):
        residual_security = strat_brief.pair_buy_side_trading_brief.security
    else:
        residual_security = strat_brief.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=residual_security, residual_notional=residual_notional)
    expected_strat_status.total_fill_exposure = - (single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) *
                                                   total_order_count)
    expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * total_order_count) / (
                single_sell_unfilled_qty * total_order_count)
    expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * total_order_count
    expected_strat_status.total_cxl_sell_notional = (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) *
                                                     total_order_count)
    expected_strat_status.total_cxl_exposure = - (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) *
                                                  total_order_count)
    if loop_count > 1:
        expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * (loop_count - 1)) / (
                    single_buy_filled_qty * (loop_count - 1))
        expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * (
                    loop_count - 1)
        expected_strat_status.total_fill_exposure = (single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * (
                    loop_count - 1)) - (single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) *
                                        total_order_count)
        expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (
                    single_buy_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1) - (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) *
                                       total_order_count)

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def placed_buy_order_ack_receive(loop_count: int, expected_order_id: str, buy_order_placed_date_time: DateTime,
                                 expected_order_journal: OrderJournalBaseModel,
                                 expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                 executor_web_client: StratExecutorServiceHttpClient):
    """Checking after order's ACK status is received"""
    order_journal_obj_list = executor_web_client.get_all_order_journal_client(-100)

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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None

    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"


def check_fill_receive_for_placed_buy_order_before_sells(loop_count: int, total_order_count: int,
                                                         expected_order_id: str,
                                                         buy_order_placed_date_time: DateTime, symbol: str,
                                                         buy_fill_journal: FillsJournalBaseModel,
                                                         expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                                         expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                         expected_pair_strat: PairStratBaseModel,
                                                         expected_strat_limits: StratLimits,
                                                         expected_strat_status: StratStatus,
                                                         expected_strat_brief_obj: StratBriefBaseModel,
                                                         expected_portfolio_status: PortfolioStatusBaseModel,
                                            executor_web_client: StratExecutorServiceHttpClient,
                                            is_buy_sell_pair: bool = False):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after fill is received
    """
    fill_journal_obj_list = executor_web_client.get_all_fills_journal_client(-100)
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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, total_order_count, expected_order_snapshot_obj,
                                        expected_symbol_side_snapshot, expected_strat_limits,
                                        expected_strat_brief_obj, buy_fill_journal.fill_date_time, is_buy_sell_pair)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
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

    # Checking Strat_Limits

    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num
        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # checking strat_status
    single_sell_order_px = 0
    single_sell_order_qty = 0
    single_sell_filled_px = 0
    single_sell_filled_qty = 0
    single_sell_unfilled_qty = 0
    if is_buy_sell_pair:
        single_sell_order_px = 110
        single_sell_order_qty = 70
        single_sell_filled_px = 120
        single_sell_filled_qty = 30
        single_sell_unfilled_qty = 40
        # handle sell side strat status update
        expected_strat_status.total_sell_qty = single_sell_order_qty * (loop_count - 1)
        expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) * (
                        loop_count - 1)
        expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) * (
                    loop_count - 1)
        expected_strat_status.avg_fill_sell_px = 0
        expected_strat_status.avg_cxl_sell_px = 0
        if loop_count > 1:
            expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * (loop_count - 1)) / (
                            single_sell_filled_qty * (loop_count - 1))
            expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * (loop_count - 1)) / (
                        single_sell_unfilled_qty * (loop_count - 1))
    expected_strat_status.total_buy_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_order_qty = single_buy_order_qty * loop_count + single_sell_order_qty * (loop_count - 1)
    expected_strat_status.total_open_buy_qty = single_buy_unfilled_qty
    expected_strat_status.avg_open_buy_px = (single_buy_unfilled_qty * single_buy_order_px) / single_buy_unfilled_qty
    expected_strat_status.total_open_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_open_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * loop_count
    expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * loop_count) / (
                single_buy_filled_qty * loop_count)
    expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * loop_count
    expected_strat_status.total_fill_exposure = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * loop_count - (
            single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) * (loop_count - 1))
    expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg2.sec,
                                              residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (
                    single_buy_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1) - single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) * (loop_count - 1)
        buy_residual_notional = expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
            current_leg_last_trade_px)
        sell_residual_notional = single_sell_unfilled_qty * get_px_in_usd(other_leg_last_trade_px) * (loop_count - 1)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)

        security = expected_strat_brief_obj.pair_buy_side_trading_brief.security if \
            buy_residual_notional > sell_residual_notional else \
            expected_strat_brief_obj.pair_sell_side_trading_brief.security
        expected_strat_status.residual = Residual(security=security,
                                                  residual_notional=residual_notional)
    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def check_fill_receive_for_placed_buy_order_after_all_sells(loop_count: int, total_order_count: int,
                                                            expected_order_id: str,
                                                            buy_order_placed_date_time: DateTime, symbol: str,
                                                            buy_fill_journal: FillsJournalBaseModel,
                                                            expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                                            expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                            expected_pair_strat: PairStratBaseModel,
                                                            expected_strat_limits: StratLimits,
                                                            expected_strat_status: StratStatus,
                                                            expected_strat_brief_obj: StratBriefBaseModel,
                                                            expected_portfolio_status: PortfolioStatusBaseModel,
                                                            executor_web_client: StratExecutorServiceHttpClient):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after fill is received
    """
    fill_journal_obj_list = executor_web_client.get_all_fills_journal_client(-100)
    assert buy_fill_journal in fill_journal_obj_list, f"Couldn't find {buy_fill_journal} in {fill_journal_obj_list}"

    single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
    (single_sell_order_px, single_sell_order_qty, single_sell_filled_px, single_sell_filled_qty,
     single_sell_unfilled_qty) = get_sell_order_related_values()
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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, total_order_count,
                                        expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                        expected_strat_limits, expected_strat_brief_obj,
                                        buy_fill_journal.fill_date_time)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        strat_brief.pair_buy_side_trading_brief.indicative_consumable_participation_qty = None
        strat_brief.pair_buy_side_trading_brief.participation_period_order_qty_sum = None
        # Since sell side of strat_brief is already checked in buy check
        strat_brief.pair_sell_side_trading_brief = expected_strat_brief_obj.pair_sell_side_trading_brief
        strat_brief.pair_buy_side_trading_brief.last_update_date_time = None
    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = None
    for strat_brief in strat_brief_list:
        if strat_brief.pair_buy_side_trading_brief == expected_strat_brief_obj.pair_buy_side_trading_brief:
            assert (strat_brief.consumable_nett_filled_notional ==
                    expected_strat_brief_obj.consumable_nett_filled_notional), \
                (f"Mismatched consumable_nett_filled_notional in strat_breif: "
                 f"expected consumable_nett_filled_notional: "
                 f"{expected_strat_brief_obj.consumable_nett_filled_notional}, received: "
                 f"{strat_brief.consumable_nett_filled_notional}")
            break
    else:
        assert False, (f"expected pair_sell_buy_trading_brief {expected_strat_brief_obj.pair_sell_side_trading_brief} "
                       f"not found in pair_sell_buy_trading_brief of any strat_brif from list: {strat_brief_list}")

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num
        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # checking strat_status
    expected_strat_status.total_buy_qty = single_buy_order_qty * loop_count
    expected_strat_status.total_sell_qty = single_sell_order_qty * total_order_count
    expected_strat_status.total_order_qty = (single_buy_order_qty * loop_count +
                                             single_sell_order_qty * total_order_count)
    expected_strat_status.total_open_buy_qty = single_buy_unfilled_qty
    expected_strat_status.avg_open_buy_px = (single_buy_unfilled_qty * single_buy_order_px) / single_buy_unfilled_qty
    expected_strat_status.total_open_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_open_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px)
    expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * loop_count
    expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * loop_count) / (
                single_buy_filled_qty * loop_count)
    expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * total_order_count) / (
            single_sell_filled_qty * total_order_count)
    expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * total_order_count
    expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
        single_buy_filled_px) * loop_count
    expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(
        single_sell_filled_px) * total_order_count
    residual_notional = abs((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * get_px_in_usd(
        current_leg_last_trade_px)) -
                            ((single_sell_unfilled_qty * total_order_count) * get_px_in_usd(other_leg_last_trade_px)))
    if ((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty *
         get_px_in_usd(current_leg_last_trade_px)) >
            ((single_sell_unfilled_qty * total_order_count) * get_px_in_usd(other_leg_last_trade_px))):
        residual_security = strat_brief.pair_buy_side_trading_brief.security
    else:
        residual_security = strat_brief.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=residual_security, residual_notional=residual_notional)
    expected_strat_status.total_fill_exposure = (
            (single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * loop_count) -
            (single_sell_filled_qty * get_px_in_usd(single_sell_filled_px) * total_order_count))
    expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * total_order_count) / (
            single_sell_unfilled_qty * total_order_count)
    expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * total_order_count
    expected_strat_status.total_cxl_sell_notional = (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) *
                                                     total_order_count)
    expected_strat_status.total_cxl_exposure = - (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) *
                                                  total_order_count)
    if loop_count > 1:
        expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (loop_count - 1)) / (
                    single_buy_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (
                    loop_count - 1) - (single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px) *
                                       total_order_count)

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def check_placed_sell_order_computes_before_buys(loop_count: int, total_loop_count: int, expected_order_id: str,
                                                 symbol: str, sell_placed_order_journal: OrderJournalBaseModel,
                                                 expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                                 expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                 expected_pair_strat: PairStratBaseModel,
                                                 expected_strat_limits: StratLimits,
                                                 expected_strat_status: StratStatus,
                                                 expected_strat_brief_obj: StratBriefBaseModel,
                                                 executor_web_client: StratExecutorServiceHttpClient,
                                                 is_buy_sell_pair: bool = False):
    order_journal_obj_list = executor_web_client.get_all_order_journal_client(-100)

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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"Couldn't find {expected_symbol_side_snapshot} "

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, 0, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_placed_order_journal.order_event_date_time, is_buy_sell_pair)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
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
            assert (strat_brief.consumable_nett_filled_notional ==
                    expected_strat_brief_obj.consumable_nett_filled_notional), \
                (f"Mismatched consumable_nett_filled_notional in strat_breif: "
                 f"expected consumable_nett_filled_notional: "
                 f"{expected_strat_brief_obj.consumable_nett_filled_notional}, received: "
                 f"{strat_brief.consumable_nett_filled_notional}")
            break
    else:
        assert False, (f"expected pair_sell_side_trading_brief {expected_strat_brief_obj.pair_sell_side_trading_brief} "
                       f"not found in pair_sell_side_trading_brief of any strat_brif from list: {strat_brief_list}")

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num
        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # Checking strat_status
    single_buy_order_px = 0
    single_buy_order_qty = 0
    single_buy_filled_px = 0
    single_buy_filled_qty = 0
    single_buy_unfilled_qty = 0
    if is_buy_sell_pair:
        single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
        # handle sell side strat status update
        expected_strat_status.total_buy_qty = single_buy_order_qty * (loop_count - 1)
        expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
            single_buy_filled_px) * (
                                                                 loop_count - 1)
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(
            single_buy_order_px) * (
                                                                loop_count - 1)
        expected_strat_status.avg_fill_buy_px = 0
        expected_strat_status.avg_cxl_buy_px = 0
        if loop_count > 1:
            expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * (
                        loop_count - 1)) / (single_buy_filled_qty * (loop_count - 1))
            expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (
                        loop_count - 1)) / (single_buy_unfilled_qty * (loop_count - 1))
    expected_strat_status.total_sell_qty = single_sell_order_qty * loop_count
    expected_strat_status.total_order_qty = single_sell_order_qty * loop_count + single_buy_order_qty * (loop_count - 1)
    expected_strat_status.total_open_sell_qty = single_sell_order_qty
    expected_strat_status.avg_open_sell_px = (single_sell_order_qty * single_sell_order_px) / single_sell_order_qty
    expected_strat_status.total_open_sell_notional = single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_open_exposure = - single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    if expected_pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
        buy_sec = expected_pair_strat.pair_strat_params.strat_leg1.sec
        sell_sec = expected_pair_strat.pair_strat_params.strat_leg2.sec
    else:
        buy_sec = expected_pair_strat.pair_strat_params.strat_leg2.sec
        sell_sec = expected_pair_strat.pair_strat_params.strat_leg1.sec
    expected_strat_status.residual = Residual(security=buy_sec, residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * (loop_count - 1)) / (
                    single_sell_filled_qty * (loop_count - 1))
        expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(
            single_sell_filled_px) * (loop_count - 1)
        expected_strat_status.total_fill_exposure = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * (loop_count - 1) - (single_sell_filled_qty * get_px_in_usd(
            single_sell_filled_px) * (loop_count - 1))
        expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * (loop_count - 1)) / (
                    single_sell_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (loop_count - 1) - (single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1))
        buy_residual_notional = single_buy_unfilled_qty * get_px_in_usd(other_leg_last_trade_px) * (loop_count - 1)
        sell_residual_notional = expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(current_leg_last_trade_px)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        security = sell_sec if \
            sell_residual_notional > buy_residual_notional else \
            buy_sec
        expected_strat_status.residual = Residual(security=security, residual_notional=residual_notional)

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def check_placed_sell_order_computes_after_all_buys(loop_count: int, total_loop_count: int, expected_order_id: str,
                                                    symbol: str, sell_placed_order_journal: OrderJournalBaseModel,
                                                    expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                                    expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                    expected_pair_strat: PairStratBaseModel,
                                                    expected_strat_limits: StratLimits,
                                                    expected_strat_status: StratStatus,
                                                    expected_strat_brief_obj: StratBriefBaseModel,
                                                    expected_portfolio_status: PortfolioStatusBaseModel,
                                                    executor_web_client: StratExecutorServiceHttpClient):
    order_journal_obj_list = executor_web_client.get_all_order_journal_client(-100)

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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"Couldn't find {expected_symbol_side_snapshot} "

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, total_loop_count, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_placed_order_journal.order_event_date_time)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
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
            assert (strat_brief.consumable_nett_filled_notional ==
                    expected_strat_brief_obj.consumable_nett_filled_notional), \
                (f"Mismatched consumable_nett_filled_notional in strat_breif: "
                 f"expected consumable_nett_filled_notional: "
                 f"{expected_strat_brief_obj.consumable_nett_filled_notional}, received: "
                 f"{strat_brief.consumable_nett_filled_notional}")
            break
    else:
        assert False, f"{expected_strat_brief_obj.pair_sell_side_trading_brief} not found in {strat_brief_list}"

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num
        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # Checking pair_strat
    expected_strat_status.total_buy_qty = single_buy_order_qty * total_loop_count
    expected_strat_status.total_sell_qty = single_sell_order_qty * loop_count
    expected_strat_status.total_order_qty = (single_buy_order_qty * total_loop_count) + (
                single_sell_order_qty * loop_count)
    expected_strat_status.total_open_sell_qty = single_sell_order_qty
    expected_strat_status.avg_open_sell_px = (single_sell_order_qty * single_sell_order_px) / single_sell_order_qty
    expected_strat_status.total_open_sell_notional = single_sell_order_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_open_exposure = - single_sell_order_qty * get_px_in_usd(single_sell_order_px)
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
    if ((single_buy_unfilled_qty * total_loop_count) * get_px_in_usd(current_leg_last_trade_px)) > (
            expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty *
            get_px_in_usd(other_leg_last_trade_px)):
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

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def placed_sell_order_ack_receive(loop_count: int, expected_order_id: str, sell_order_placed_date_time: DateTime,
                                  total_loop_count: int, expected_order_journal: OrderJournalBaseModel,
                                  expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                  executor_web_client: StratExecutorServiceHttpClient):
    """Checking after order's ACK status is received"""
    order_journal_obj_list = executor_web_client.get_all_order_journal_client(-100)

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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None

    assert expected_order_snapshot_obj in order_snapshot_list, f"Couldn't find {expected_order_snapshot_obj} in " \
                                                               f"{order_snapshot_list}"


def check_fill_receive_for_placed_sell_order_before_buys(
        loop_count: int, total_loop_count: int, expected_order_id: str, sell_order_placed_date_time: DateTime,
        symbol: str, sell_fill_journal: FillsJournalBaseModel, expected_order_snapshot_obj: OrderSnapshotBaseModel,
        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel, expected_pair_strat: PairStratBaseModel,
        expected_strat_limits: StratLimits, expected_strat_status: StratStatus,
        expected_strat_brief_obj: StratBriefBaseModel, expected_portfolio_status: PortfolioStatusBaseModel,
        executor_web_client: StratExecutorServiceHttpClient, is_buy_sell_pair: bool = False):
    fill_journal_obj_list = executor_web_client.get_all_fills_journal_client(-100)
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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, 0, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_fill_journal.fill_date_time, is_buy_sell_pair)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
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
            assert (strat_brief.consumable_nett_filled_notional ==
                    expected_strat_brief_obj.consumable_nett_filled_notional), \
                (f"Mismatched consumable_nett_filled_notional in strat_breif: "
                 f"expected consumable_nett_filled_notional: "
                 f"{expected_strat_brief_obj.consumable_nett_filled_notional}, received: "
                 f"{strat_brief.consumable_nett_filled_notional}")
            break
    else:
        assert False, f"Couldn't find {expected_strat_brief_obj.pair_sell_side_trading_brief} in any strat_brief in " \
                      f"{strat_brief_list}"

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num
        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # Checking strat_status
    single_buy_order_px = 0
    single_buy_order_qty = 0
    single_buy_filled_px = 0
    single_buy_filled_qty = 0
    single_buy_unfilled_qty = 0
    if is_buy_sell_pair:
        single_buy_order_px, single_buy_order_qty, single_buy_filled_px, single_buy_filled_qty, \
        single_buy_unfilled_qty = get_buy_order_related_values()
        # handle sell side strat status update
        expected_strat_status.total_buy_qty = single_buy_order_qty * (loop_count - 1)
        expected_strat_status.total_fill_buy_qty = single_buy_filled_qty * (loop_count - 1)
        expected_strat_status.total_fill_buy_notional = single_buy_filled_qty * get_px_in_usd(
            single_buy_filled_px) * (
                                                                 loop_count - 1)
        expected_strat_status.total_cxl_buy_qty = single_buy_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = single_buy_unfilled_qty * get_px_in_usd(
            single_buy_order_px) * (
                                                                loop_count - 1)
        expected_strat_status.avg_fill_buy_px = 0
        expected_strat_status.avg_cxl_buy_px = 0
        if loop_count > 1:
            expected_strat_status.avg_fill_buy_px = (single_buy_filled_qty * single_buy_filled_px * (
                        loop_count - 1)) / (single_buy_filled_qty * (loop_count - 1))
            expected_strat_status.avg_cxl_buy_px = (single_buy_unfilled_qty * single_buy_order_px * (
                        loop_count - 1)) / (single_buy_unfilled_qty * (loop_count - 1))
    expected_strat_status.total_sell_qty = single_sell_order_qty * loop_count
    expected_strat_status.total_order_qty = single_sell_order_qty * loop_count + single_buy_order_qty * (loop_count - 1)
    expected_strat_status.avg_open_sell_px = ((single_sell_unfilled_qty * single_sell_order_px) /
                                              single_sell_unfilled_qty)
    expected_strat_status.total_open_sell_qty = single_sell_unfilled_qty
    expected_strat_status.total_open_sell_notional = single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_open_exposure = -single_sell_unfilled_qty * get_px_in_usd(single_sell_order_px)
    expected_strat_status.total_fill_sell_qty = single_sell_filled_qty * loop_count
    expected_strat_status.avg_fill_sell_px = (single_sell_filled_qty * single_sell_filled_px * loop_count) / (
                single_sell_filled_qty * loop_count)
    expected_strat_status.total_fill_sell_notional = single_sell_filled_qty * get_px_in_usd(
        single_sell_filled_px) * loop_count
    expected_strat_status.total_fill_exposure = single_buy_filled_qty * get_px_in_usd(single_buy_filled_px) * (loop_count - 1)  - (single_sell_filled_qty * get_px_in_usd(
                                                    single_sell_filled_px) * loop_count)
    current_leg_last_trade_px = 116
    other_leg_last_trade_px = 116

    buy_sec = expected_strat_brief_obj.pair_buy_side_trading_brief.security
    sell_sec = expected_strat_brief_obj.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=buy_sec, residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_cxl_sell_px = (single_sell_unfilled_qty * single_sell_order_px * (loop_count - 1)) / (
                    single_sell_unfilled_qty * (loop_count - 1))
        expected_strat_status.total_cxl_sell_qty = single_sell_unfilled_qty * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = single_buy_unfilled_qty * get_px_in_usd(single_buy_order_px) * (loop_count - 1) - (single_sell_unfilled_qty * get_px_in_usd(
            single_sell_order_px) * (loop_count - 1))
        buy_residual_notional = single_buy_unfilled_qty * get_px_in_usd(other_leg_last_trade_px) * (loop_count - 1)
        sell_residual_notional = expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * get_px_in_usd(
            current_leg_last_trade_px)
        residual_notional = abs(buy_residual_notional - sell_residual_notional)
        security = sell_sec if \
            sell_residual_notional > buy_residual_notional else \
            buy_sec
        expected_strat_status.residual = Residual(security=security, residual_notional=residual_notional)
    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")


def check_fill_receive_for_placed_sell_order_after_all_buys(
        loop_count: int, total_loop_count: int, expected_order_id: str, sell_order_placed_date_time: DateTime,
        symbol: str, sell_fill_journal: FillsJournalBaseModel, expected_order_snapshot_obj: OrderSnapshotBaseModel,
        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel, expected_pair_strat: PairStratBaseModel,
        expected_strat_limits: StratLimits, expected_strat_status: StratStatus,
        expected_strat_brief_obj: StratBriefBaseModel, expected_portfolio_status: PortfolioStatusBaseModel,
        executor_web_client: StratExecutorServiceHttpClient):
    fill_journal_obj_list = executor_web_client.get_all_fills_journal_client(-100)
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

    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
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

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking Strat_Limits
    strat_limits_obj_list = executor_web_client.get_all_strat_limits_client()
    if len(strat_limits_obj_list) == 1:
        strat_limits_obj = strat_limits_obj_list[0]
        expected_strat_limits.id = strat_limits_obj.id
        expected_strat_limits.eligible_brokers = strat_limits_obj.eligible_brokers
        expected_strat_limits.strat_limits_update_seq_num = strat_limits_obj.strat_limits_update_seq_num
        assert strat_limits_obj == expected_strat_limits, \
            f"Mismatched StratLimits: expected: {expected_strat_limits}, received: {strat_limits_obj}"
    else:
        assert False, (f"StratLimits' length must be exactly 1, found {len(strat_limits_obj_list)}, "
                       f"strat_limits_list: {strat_limits_obj_list}")

    # Checking pair_strat
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

    strat_status_obj_list = executor_web_client.get_all_strat_status_client()
    if len(strat_status_obj_list) == 1:
        strat_status_obj = strat_status_obj_list[0]
        expected_strat_status.id = strat_status_obj.id
        expected_strat_status.last_update_date_time = strat_status_obj.last_update_date_time
        expected_strat_status.strat_status_update_seq_num = strat_status_obj.strat_status_update_seq_num
        expected_strat_status.average_premium = strat_status_obj.average_premium
        assert strat_status_obj == expected_strat_status, \
            f"Mismatched StratStatus: expected: {expected_strat_status}, received: {strat_status_obj}"
    else:
        assert False, (f"StratStatus' length must be exactly 1, found {len(strat_status_obj_list)}, "
                       f"strat_status_list: {strat_status_obj_list}")

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, total_loop_count, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_fill_journal.fill_date_time)

    strat_brief_list = executor_web_client.get_strat_brief_from_symbol_query_client(symbol)
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
            assert (strat_brief.consumable_nett_filled_notional ==
                    expected_strat_brief_obj.consumable_nett_filled_notional), \
                (f"Mismatched consumable_nett_filled_notional in strat_breif: "
                 f"expected consumable_nett_filled_notional: "
                 f"{expected_strat_brief_obj.consumable_nett_filled_notional}, received: "
                 f"{strat_brief.consumable_nett_filled_notional}")
            break
    else:
        assert False, f"Couldn't find {expected_strat_brief_obj.pair_sell_side_trading_brief} in any strat_brief in " \
                      f"{strat_brief_list}"


class TopOfBookSide(StrEnum):
    Bid = auto()
    Ask = auto()


def create_tob(buy_symbol: str, sell_symbol: str, top_of_book_json_list: List[Dict],
               executor_web_client: StratExecutorServiceHttpClient,
               is_non_systematic_run: bool | None = None):

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
            executor_web_client.create_top_of_book_client(top_of_book_basemodel)
        top_of_book_basemodel.id = stored_top_of_book_basemodel.id
        top_of_book_basemodel.last_update_date_time = stored_top_of_book_basemodel.last_update_date_time
        for market_trade_vol in stored_top_of_book_basemodel.market_trade_volume:
            market_trade_vol.id = None
        for market_trade_vol in top_of_book_basemodel.market_trade_volume:
            market_trade_vol.id = None
        assert stored_top_of_book_basemodel == top_of_book_basemodel, \
            f"Mismatch TopOfBook, expected {top_of_book_basemodel}, received {stored_top_of_book_basemodel}"


def _update_tob(stored_obj: TopOfBookBaseModel, px: int | float, side: Side,
                executor_web_client: StratExecutorServiceHttpClient):
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
    updated_tob_obj = executor_web_client.patch_top_of_book_client(jsonable_encoder(tob_obj,
                                                                                    by_alias=True, exclude_none=True))

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


def run_buy_top_of_book(buy_symbol: str, sell_symbol: str, executor_web_client: StratExecutorServiceHttpClient,
                        tob_json_dict: Dict, avoid_order_trigger: bool | None = None):
    buy_stored_tob: TopOfBookBaseModel | None = None
    sell_stored_tob: TopOfBookBaseModel | None = None

    stored_tob_objs = executor_web_client.get_all_top_of_book_client()
    for tob_obj in stored_tob_objs:
        if tob_obj.symbol == buy_symbol:
            buy_stored_tob = tob_obj
        elif tob_obj.symbol == sell_symbol:
            sell_stored_tob = tob_obj

    # For place order non-triggered run
    sell_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
    executor_web_client.patch_top_of_book_client(jsonable_encoder(sell_stored_tob, by_alias=True, exclude_none=True))
    _update_tob(buy_stored_tob, tob_json_dict.get("bid_quote").get("px") - 10, Side.BUY, executor_web_client)
    if avoid_order_trigger:
        px = tob_json_dict.get("bid_quote").get("px") - 10
    else:
        # For place order trigger run
        px = tob_json_dict.get("bid_quote").get("px")

    time.sleep(1)
    sell_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
    executor_web_client.patch_top_of_book_client(jsonable_encoder(sell_stored_tob, by_alias=True, exclude_none=True))
    _update_tob(buy_stored_tob, px, Side.BUY, executor_web_client)


def run_sell_top_of_book(buy_symbol: str, sell_symbol: str, executor_web_client: StratExecutorServiceHttpClient,
                         tob_json_dict: Dict, avoid_order_trigger: bool | None = None):
    buy_stored_tob: TopOfBookBaseModel | None = None
    sell_stored_tob: TopOfBookBaseModel | None = None

    stored_tob_objs = executor_web_client.get_all_top_of_book_client()
    for tob_obj in stored_tob_objs:
        if tob_obj.symbol == buy_symbol:
            buy_stored_tob = tob_obj
        elif tob_obj.symbol == sell_symbol:
            sell_stored_tob = tob_obj

    # For place order non-triggered run
    buy_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
    executor_web_client.patch_top_of_book_client(jsonable_encoder(buy_stored_tob, by_alias=True, exclude_none=True))
    _update_tob(sell_stored_tob, sell_stored_tob.ask_quote.px - 10, Side.SELL, executor_web_client)

    if avoid_order_trigger:
        px = tob_json_dict.get("ask_quote").get("px") - 10

    else:
        # For place order trigger run
        px = tob_json_dict.get("ask_quote").get("px")

    time.sleep(1)

    buy_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
    executor_web_client.patch_top_of_book_client(jsonable_encoder(buy_stored_tob, by_alias=True, exclude_none=True))
    _update_tob(sell_stored_tob, px, Side.SELL, executor_web_client)


def run_last_trade(leg1_symbol: str, leg2_symbol: str, last_trade_json_list: List[Dict],
                   executor_web_client: StratExecutorServiceHttpClient,
                   create_counts_per_side: int | None = None):
    if create_counts_per_side is None:
        create_counts_per_side = 20
    symbol_list = [leg1_symbol, leg2_symbol]
    for index, last_trade_json in enumerate(last_trade_json_list):
        for _ in range(create_counts_per_side):
            last_trade_obj: LastTradeBaseModel = LastTradeBaseModel(**last_trade_json)
            last_trade_obj.symbol_n_exch_id.symbol = symbol_list[index]
            last_trade_obj.exch_time = DateTime.utcnow()
            created_last_trade_obj = executor_web_client.create_last_trade_client(last_trade_obj)
            created_last_trade_obj.id = None
            created_last_trade_obj.market_trade_volume.id = last_trade_obj.market_trade_volume.id
            created_last_trade_obj.exch_time = last_trade_obj.exch_time
            assert created_last_trade_obj == last_trade_obj, \
                f"Mismatch last_trade: expected {last_trade_obj}, received {created_last_trade_obj}"


# TODO: move it to web-ui
def symbol_overview_list() -> List[SymbolOverviewBaseModel]:
    symbol_overview_obj_list: List[SymbolOverviewBaseModel] = []

    symbols = ["CB_Sec_1", "EQT_Sec_1"]  # Add more symbols if needed

    id: int = 1
    for symbol in symbols:
        symbol_overview = {
            "_id": id,
            "symbol": symbol,
            "company": "string",
            "status": "string",
            "lot_size": 10,
            "limit_up_px": 110,
            "limit_dn_px": 12,
            "conv_px": 1.0,
            "closing_px": 11,
            "open_px": 11,
            "high": 100,
            "low": 10,
            "volume": 150,
            "last_update_date_time": "2023-10-18T21:35:15.728Z",
            "force_publish": True
        }

        id += 1

        symbol_overview_obj_list.append(SymbolOverviewBaseModel(**symbol_overview))

    return symbol_overview_obj_list


def create_n_activate_strat(leg1_symbol: str, leg2_symbol: str,
                            expected_pair_strat_obj: PairStratBaseModel,
                            expected_strat_limits: StratLimits,
                            expected_strat_status: StratStatus,
                            symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                            top_of_book_json_list: List[Dict],
                            market_depth_basemodel_list: List[MarketDepthBaseModel],
                            leg1_side: Side | None = None, leg2_side: Side | None = None
                            ) -> Tuple[PairStratBaseModel, StratExecutorServiceHttpClient]:
    expected_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id = leg1_symbol
    if leg1_side is None:
        expected_pair_strat_obj.pair_strat_params.strat_leg1.side = Side.BUY
    else:
        expected_pair_strat_obj.pair_strat_params.strat_leg1.side = leg1_side
    expected_pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id = leg2_symbol
    if leg2_side is None:
        expected_pair_strat_obj.pair_strat_params.strat_leg2.side = Side.SELL
    else:
        expected_pair_strat_obj.pair_strat_params.strat_leg2.side = leg2_side
    expected_pair_strat_obj.strat_state = StratState.StratState_SNOOZED
    stored_pair_strat_basemodel = \
        strat_manager_service_native_web_client.create_pair_strat_client(expected_pair_strat_obj)
    assert expected_pair_strat_obj.frequency == stored_pair_strat_basemodel.frequency, \
        f"Mismatch pair_strat_basemodel.frequency: expected {expected_pair_strat_obj.frequency}, " \
        f"received {stored_pair_strat_basemodel.frequency}"
    assert expected_pair_strat_obj.pair_strat_params == stored_pair_strat_basemodel.pair_strat_params, \
        f"Mismatch pair_strat_obj.pair_strat_params: expected {expected_pair_strat_obj.pair_strat_params}, " \
        f"received {stored_pair_strat_basemodel.pair_strat_params}"
    assert stored_pair_strat_basemodel.pair_strat_params_update_seq_num == 0, \
        f"Mismatch pair_strat.pair_strat_params_update_seq_num: expected 0 received " \
        f"{stored_pair_strat_basemodel.pair_strat_params_update_seq_num}"
    assert expected_pair_strat_obj.strat_state == stored_pair_strat_basemodel.strat_state, \
        f"Mismatch pair_strat_base_model.strat_state: expected {expected_pair_strat_obj.strat_state}, " \
        f"received {stored_pair_strat_basemodel.strat_state}"
    print(f"{leg1_symbol} - strat created, {stored_pair_strat_basemodel}")

    if stored_pair_strat_basemodel.pair_strat_params.strat_leg1.side == Side.BUY:
        buy_symbol = stored_pair_strat_basemodel.pair_strat_params.strat_leg1.sec.sec_id
        sell_symbol = stored_pair_strat_basemodel.pair_strat_params.strat_leg2.sec.sec_id
    else:
        buy_symbol = stored_pair_strat_basemodel.pair_strat_params.strat_leg2.sec.sec_id
        sell_symbol = stored_pair_strat_basemodel.pair_strat_params.strat_leg1.sec.sec_id

    for _ in range(30):
        # checking is_partially_running of executor
        try:
            updated_pair_strat = (
                strat_manager_service_native_web_client.get_pair_strat_client(stored_pair_strat_basemodel.id))
            if updated_pair_strat.is_partially_running:
                break
            time.sleep(1)
        except Exception as e:
            pass
    else:
        assert False, (f"is_partially_running state must be True, found false, "
                       f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    assert updated_pair_strat.port is not None, (
        "Once pair_strat is partially running it also must contain port, updated object has port field as None, "
        f"updated pair_strat: {updated_pair_strat}")

    executor_web_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_strat.host, updated_pair_strat.port)

    # creating market_depth
    create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list, executor_web_client)
    print(f"market_depth created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # running symbol_overview
    run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list, executor_web_client)
    print(f"SymbolOverview created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    create_tob(buy_symbol, sell_symbol, top_of_book_json_list, executor_web_client)
    print(f"TOB created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    wait_time = 20
    executor_check_loop_counts = 3
    for _ in range(executor_check_loop_counts):
        time.sleep(wait_time)
        strat_limits_list = executor_web_client.get_all_strat_limits_client()

        is_strat_limits_present = False
        is_strat_status_present = False

        if len(strat_limits_list) == 1:
            strat_limits = strat_limits_list[0]
            expected_strat_limits.id = strat_limits.id
            expected_strat_limits.eligible_brokers = strat_limits.eligible_brokers

            updated_strat_limits = executor_web_client.put_strat_limits_client(expected_strat_limits)
            expected_strat_limits.strat_limits_update_seq_num = updated_strat_limits.strat_limits_update_seq_num
            assert updated_strat_limits == expected_strat_limits, \
                (f"Mismatched StratLimits: expected strat_limits: {expected_strat_limits}, updated "
                 f"strat_limits: {updated_strat_limits}")

            is_strat_limits_present = True
            print(f"StratLimits updated for this test, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        else:
            if len(strat_limits_list) > 1:
                assert False, (f"StratLimits must exactly one in executor, found {len(strat_limits_list)}, "
                               f"strat_limits_list: {strat_limits_list}")

        strat_status_list = executor_web_client.get_all_strat_status_client()
        if len(strat_status_list) == 1:
            strat_status = strat_status_list[0]
            expected_strat_status.id = strat_status.id
            expected_strat_status.strat_status_update_seq_num = strat_status.strat_status_update_seq_num
            expected_strat_status.last_update_date_time = strat_status.last_update_date_time
            assert strat_status == expected_strat_status, \
                (f"StratStatus Mismatched: expected strat_status {expected_strat_status}, "
                 f"received strat_status: {strat_status}")
            is_strat_status_present = True
            print(f"StratStatus found in ready state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        else:
            if len(strat_status_list) > 1:
                assert False, (f"StratStatus must exactly one in executor, found {len(strat_status_list)}, "
                               f"strat_status_list: {strat_status_list}")

        if is_strat_status_present and is_strat_limits_present:
            break
    else:
        assert False, ("Could not find created strat_status or strat_limits in newly started executor, took "
                       f"{executor_check_loop_counts} loops of {wait_time} sec each, "
                       f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # checking is_running_state of executor
    updated_pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(stored_pair_strat_basemodel.id)
    assert updated_pair_strat.is_executor_running, \
        f"is_executor_running state must be True, found false, pair_strat: {updated_pair_strat}"
    print(f"is_executor_running is True, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
    assert updated_pair_strat.strat_state == StratState.StratState_READY, \
        (f"StratState Mismatched, expected StratState: {StratState.StratState_READY}, "
         f"received pair_strat's strat_state: {updated_pair_strat.strat_state}")
    print(f"StratStatus updated to READY state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # activating strat
    pair_strat = PairStratBaseModel(_id=stored_pair_strat_basemodel.id, strat_state=StratState.StratState_ACTIVE)
    activated_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
    assert activated_pair_strat.strat_state == StratState.StratState_ACTIVE, \
        (f"StratState Mismatched, expected StratState: {StratState.StratState_ACTIVE}, "
         f"received pair_strat's strat_state: {activated_pair_strat.strat_state}")
    print(f"StratStatus updated to Active state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return updated_pair_strat, executor_web_client


# @@@ deprecated: strat_collection is now handled by pair_strat override itself
# def create_if_not_exists_and_validate_strat_collection(pair_strat_: PairStratBaseModel):
#     strat_collection_obj_list = strat_manager_service_native_web_client.get_all_strat_collection_client()
#
#     strat_key = f"{pair_strat_.pair_strat_params.strat_leg2.sec.sec_id}-" \
#                 f"{pair_strat_.pair_strat_params.strat_leg1.sec.sec_id}-" \
#                 f"{pair_strat_.pair_strat_params.strat_leg1.side}-{pair_strat_.id}"
#     if len(strat_collection_obj_list) == 0:
#         strat_collection_basemodel = StratCollectionBaseModel(**{
#             "_id": 1,
#             "loaded_strat_keys": [
#                 strat_key
#             ],
#             "buffered_strat_keys": []
#         })
#         created_strat_collection = \
#             strat_manager_service_native_web_client.create_strat_collection_client(strat_collection_basemodel)
#
#         assert created_strat_collection == strat_collection_basemodel, \
#             f"Mismatch strat_collection: expected {strat_collection_basemodel} received {created_strat_collection}"
#
#     else:
#         strat_collection_obj = strat_collection_obj_list[0]
#         strat_collection_obj.loaded_strat_keys.append(strat_key)
#         updated_strat_collection_obj = \
#             strat_manager_service_native_web_client.put_strat_collection_client(jsonable_encoder(strat_collection_obj, by_alias=True, exclude_none=True))
#
#         assert updated_strat_collection_obj == strat_collection_obj, \
#             f"Mismatch strat_collection: expected {strat_collection_obj} received {updated_strat_collection_obj}"


def run_symbol_overview(buy_symbol: str, sell_symbol: str,
                        symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                        executor_web_client: StratExecutorServiceHttpClient):
    for index, symbol_overview_obj in enumerate(symbol_overview_obj_list):
        if index == 0:
            symbol_overview_obj.symbol = buy_symbol
        else:
            symbol_overview_obj.symbol = sell_symbol
        symbol_overview_obj.id = None
        created_symbol_overview = executor_web_client.create_symbol_overview_client(symbol_overview_obj)
        symbol_overview_obj.id = created_symbol_overview.id
        assert created_symbol_overview == symbol_overview_obj, f"Created symbol_overview {created_symbol_overview} not " \
                                                               f"equals to expected symbol_overview " \
                                                               f"{symbol_overview_obj}"


def create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list: List[MarketDepthBaseModel],
                        executor_web_client: StratExecutorServiceHttpClient):
    for index, market_depth_basemodel in enumerate(market_depth_basemodel_list):
        if index < 10:
            market_depth_basemodel.symbol = buy_symbol
        else:
            market_depth_basemodel.symbol = sell_symbol
        created_market_depth = executor_web_client.create_market_depth_client(market_depth_basemodel)
        created_market_depth.id = None
        created_market_depth.cumulative_avg_px = None
        created_market_depth.cumulative_notional = None
        created_market_depth.cumulative_qty = None
        assert created_market_depth == market_depth_basemodel, \
            f"Mismatch market_depth: expected {market_depth_basemodel} received {created_market_depth}"


def wait_for_get_new_order_placed_from_tob(wait_stop_px: int | float, symbol_to_check: str,
                                           last_update_date_time: DateTime | None, side: Side,
                                           executor_web_client: StratExecutorServiceHttpClient):
    loop_counter = 0
    loop_limit = 10
    while True:
        time.sleep(2)

        tob_obj_list = executor_web_client.get_all_top_of_book_client()

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


def renew_portfolio_alert():
    portfolio_alert_list = log_analyzer_web_client.get_all_portfolio_alert_client()
    if len(portfolio_alert_list) == 1:
        portfolio_alert = portfolio_alert_list[0]
    else:
        err_str_ = (f"PortfolioAlert must have exactly 1 object, received {len(portfolio_alert_list)}, "
                    f"portfolio_alert_list: {portfolio_alert_list}")
        logging.error(err_str_)
        raise Exception(err_str_)

    retaining_alerts = []
    for alert in portfolio_alert.alerts:
        if "Log analyzer running in simulation mode" in alert.alert_brief:
            retaining_alerts.append(alert)
    portfolio_alert_obj = PortfolioAlertBaseModel(_id=portfolio_alert.id,
                                                  alerts=retaining_alerts,
                                                  alert_update_seq_num=0)
    log_analyzer_web_client.put_portfolio_alert_client(portfolio_alert_obj)

def renew_strat_collection():
    strat_collection_list: List[StratCollectionBaseModel] = (
        strat_manager_service_native_web_client.get_all_strat_collection_client())
    if strat_collection_list:
        strat_collection = strat_collection_list[0]
        strat_collection.loaded_strat_keys.clear()
        strat_collection.buffered_strat_keys.clear()
        strat_manager_service_native_web_client.put_strat_collection_client(strat_collection)


def clean_executors_and_today_activated_symbol_side_lock_file():
    existing_pair_strat = strat_manager_service_native_web_client.get_all_pair_strat_client()
    for pair_strat in existing_pair_strat:
        if not pair_strat.is_executor_running:
            err_str_ = ("strat exists but is not running, can't delete strat when not running, "
                        "delete it manually")
            logging.error(err_str_)
            raise Exception(err_str_)

        pair_strat = PairStratBaseModel(_id=pair_strat.id, strat_state=StratState.StratState_DONE)
        strat_manager_service_native_web_client.patch_pair_strat_client(jsonable_encoder(pair_strat, by_alias=True,
                                                                        exclude_none=True))
        # removing today_activated_symbol_side_lock_file
        command_n_control_obj: CommandNControlBaseModel = CommandNControlBaseModel(command_type=CommandType.CLEAR_STRAT,
                                                                                   datetime=DateTime.utcnow())
        strat_manager_service_native_web_client.create_command_n_control_client(command_n_control_obj)

        strat_manager_service_native_web_client.delete_pair_strat_client(pair_strat.id)
        time.sleep(2)


def set_n_verify_limits(expected_order_limits_obj, expected_portfolio_limits_obj):
    created_order_limits_obj = (
        strat_manager_service_native_web_client.create_order_limits_client(expected_order_limits_obj))
    assert created_order_limits_obj == expected_order_limits_obj, \
        f"Mismatch order_limits: expected {expected_order_limits_obj} received {created_order_limits_obj}"

    created_portfolio_limits_obj = \
        strat_manager_service_native_web_client.create_portfolio_limits_client(expected_portfolio_limits_obj)
    assert created_portfolio_limits_obj == expected_portfolio_limits_obj, \
        f"Mismatch portfolio_limits: expected {expected_portfolio_limits_obj} received {created_portfolio_limits_obj}"


def create_n_verify_portfolio_status(portfolio_status_obj: PortfolioStatusBaseModel):
    portfolio_status_obj.id = 1
    created_portfolio_status = (
        strat_manager_service_native_web_client.create_portfolio_status_client(portfolio_status_obj))
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
    assert expected_portfolio_status in portfolio_status_list, f"Couldn't find {expected_portfolio_status} in " \
                                                               f"{portfolio_status_list}"


def get_latest_order_journal_with_event_and_symbol(expected_order_event, expected_symbol,
                                                   executor_web_client: StratExecutorServiceHttpClient,
                                                   expect_no_order: bool | None = None,
                                                   last_order_id: str | None = None,
                                                   max_loop_count: int | None = None,
                                                   loop_wait_secs: int | None = None,
                                                   assert_code: int = 0):
    start_time = DateTime.utcnow()
    placed_order_journal = None
    if max_loop_count is None:
        max_loop_count = 20
    if loop_wait_secs is None:
        loop_wait_secs = 2

    for loop_count in range(max_loop_count):
        stored_order_journal_list = executor_web_client.get_all_order_journal_client(-100)
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
                                             f"received {placed_order_journal} - assert_code: {assert_code}"
        placed_order_journal = OrderJournalBaseModel(order=OrderBriefOptional(order_id=last_order_id))
    else:
        assert placed_order_journal is not None, \
            f"Can't find any order_journal with symbol {expected_symbol} order_event {expected_order_event}, " \
            f"expect_no_order {expect_no_order} and last_order_id {last_order_id} - assert_code: {assert_code}"

    return placed_order_journal


# @@@ copy of get_latest_order_journal_with_event_and_symbol - contains code repetition
def get_latest_order_journal_with_events_and_symbol(expected_order_event_list, expected_symbol,
                                                    executor_web_client: StratExecutorServiceHttpClient,
                                                    expect_no_order: bool | None = None,
                                                    last_order_id: str | None = None,
                                                    max_loop_count: int | None = None,
                                                    loop_wait_secs: int | None = None,
                                                    assert_code: int = 0):
    start_time = DateTime.utcnow()
    placed_order_journal = None
    if max_loop_count is None:
        max_loop_count = 20
    if loop_wait_secs is None:
        loop_wait_secs = 2

    for loop_count in range(max_loop_count):
        stored_order_journal_list = executor_web_client.get_all_order_journal_client(-100)
        for stored_order_journal in stored_order_journal_list:
            if stored_order_journal.order_event in expected_order_event_list and \
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
          f"for symbol {expected_symbol}, order_events {expected_order_event_list}, "
          f"expect_no_order {expect_no_order} and last_order_id {last_order_id}")

    if expect_no_order:
        assert placed_order_journal is None, f"Expected no new order for symbol {expected_symbol}, " \
                                             f"received {placed_order_journal} - assert_code: {assert_code}"
        placed_order_journal = OrderJournalBaseModel(order=OrderBriefOptional(order_id=last_order_id))
    else:
        assert placed_order_journal is not None, \
            f"Can't find any order_journal with symbol {expected_symbol} order_events {expected_order_event_list}, " \
            f"expect_no_order {expect_no_order} and last_order_id {last_order_id} - assert_code: {assert_code}"

    return placed_order_journal


def get_latest_fill_journal_from_order_id(expected_order_id: str,
                                          executor_web_client: StratExecutorServiceHttpClient):
    found_fill_journal = None

    stored_fill_journals = executor_web_client.get_all_fills_journal_client(-100)
    for stored_fill_journal in stored_fill_journals:
        if stored_fill_journal.order_id == expected_order_id:
            # since fills_journal is having option to sort in descending, first occurrence will be latest
            found_fill_journal = stored_fill_journal
            break
    assert found_fill_journal is not None, f"Can't find any fill_journal with order_id {expected_order_id}"
    return found_fill_journal


def get_fill_journals_for_order_id(expected_order_id: str,
                                   executor_web_client: StratExecutorServiceHttpClient):
    found_fill_journals = []

    stored_fill_journals = executor_web_client.get_all_fills_journal_client(-100)
    for stored_fill_journal in stored_fill_journals:
        if stored_fill_journal.order_id == expected_order_id:
            found_fill_journals.append(stored_fill_journal)
    assert len(found_fill_journals) != 0, f"Can't find any fill_journal with order_id {expected_order_id}"
    return found_fill_journals


def place_new_order(sec_id: str, side: Side, px: float, qty: int,
                    executor_web_client: StratExecutorServiceHttpClient):
    security = Security(sec_id=sec_id, sec_type=SecurityType.TICKER)
    new_order_obj = NewOrderBaseModel(security=security, side=side, px=px, qty=qty)
    created_new_order_obj = executor_web_client.create_new_order_client(new_order_obj)

    new_order_obj.id = created_new_order_obj.id
    assert created_new_order_obj == new_order_obj, f"Mismatch new_order_obj: expected {new_order_obj}, " \
                                                   f"received {created_new_order_obj}"


def create_pre_order_test_requirements(leg1_symbol: str, leg2_symbol: str, pair_strat_: PairStratBaseModel,
                                       expected_strat_limits_: StratLimits, expected_start_status_: StratStatus,
                                       symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                       last_trade_fixture_list: List[Dict],
                                       market_depth_basemodel_list: List[MarketDepthBaseModel],
                                       top_of_book_json_list: List[Dict],
                                       leg1_side: Side | None = None, leg2_side: Side | None = None,
                                       strat_mode: StratMode | None = None) -> Tuple[PairStratBaseModel,
                                                                                     StratExecutorServiceHttpClient]:
    print(f"Test started, leg1_symbol: {leg1_symbol}, leg2_symbol: {leg2_symbol}")

    # Creating Strat

    if strat_mode is None:
        strat_mode = StratMode.StratMode_Normal
    pair_strat_.pair_strat_params.strat_mode = strat_mode
    active_pair_strat, executor_web_client = create_n_activate_strat(
        leg1_symbol, leg2_symbol, copy.deepcopy(pair_strat_), copy.deepcopy(expected_strat_limits_),
        copy.deepcopy(expected_start_status_), symbol_overview_obj_list, top_of_book_json_list,
        market_depth_basemodel_list, leg1_side, leg2_side)
    if active_pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
        buy_symbol = active_pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        sell_symbol = active_pair_strat.pair_strat_params.strat_leg2.sec.sec_id
    else:
        buy_symbol = active_pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        sell_symbol = active_pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    print(f"strat created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # running Last Trade
    run_last_trade(leg1_symbol, leg2_symbol, last_trade_fixture_list, executor_web_client)
    print(f"LastTrade created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return active_pair_strat, executor_web_client


def fx_symbol_overview_obj() -> FxSymbolOverviewBaseModel:
    return FxSymbolOverviewBaseModel(**{
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


def handle_test_buy_sell_order(buy_symbol: str, sell_symbol: str, total_loop_count: int,
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
    active_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))
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
        expected_pair_strat.pair_strat_params.strat_leg1.side = Side.BUY
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.side = Side.SELL

        expected_strat_status = copy.deepcopy(expected_start_status_)

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], is_non_systematic_run)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(110, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_order
            place_new_order(buy_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        order_id = placed_order_journal.order.order_id
        create_buy_order_date_time: DateTime = placed_order_journal.order_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_buy_order_computes_before_all_sells(loop_count, 0, order_id, buy_symbol,
                                                         placed_order_journal, expected_buy_order_snapshot,
                                                         expected_buy_symbol_side_snapshot, expected_pair_strat,
                                                         expected_strat_limits_, expected_strat_status,
                                                         expected_strat_brief_obj, expected_portfolio_status, executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_buy_order_journal_.order.px,
            current_itr_expected_buy_order_journal_.order.qty,
            current_itr_expected_buy_order_journal_.order.side,
            current_itr_expected_buy_order_journal_.order.security.sec_id,
            current_itr_expected_buy_order_journal_.order.underlying_account
        )

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_buy_order_ack_receive(loop_count, order_id, create_buy_order_date_time,
                                     placed_order_journal_obj_ack_response, expected_buy_order_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order ACK of order_id {order_id}")

        buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_buy_order_before_sells(loop_count, 0, order_id, create_buy_order_date_time,
                                                             buy_symbol, placed_fill_journal_obj,
                                                             expected_buy_order_snapshot, expected_buy_symbol_side_snapshot,
                                                             expected_pair_strat,
                                                             expected_strat_limits_, expected_strat_status,
                                                             expected_strat_brief_obj, expected_portfolio_status,
                                                             executor_web_client)
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

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)
        current_itr_expected_sell_order_journal_.order.security.sec_id = sell_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1], is_non_systematic_run)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_order
            place_new_order(sell_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        create_sell_order_date_time: DateTime = placed_order_journal.order_event_date_time
        order_id = placed_order_journal.order.order_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_sell_order_computes_after_all_buys(loop_count, total_loop_count, order_id,
                                                        sell_symbol, placed_order_journal, expected_sell_order_snapshot,
                                                        expected_sell_symbol_side_snapshot, expected_pair_strat,
                                                        expected_strat_limits_, expected_strat_status,
                                                        expected_strat_brief_obj, expected_portfolio_status, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_sell_order_journal_.order.px,
            current_itr_expected_sell_order_journal_.order.qty,
            current_itr_expected_sell_order_journal_.order.side,
            current_itr_expected_sell_order_journal_.order.security.sec_id,
            current_itr_expected_sell_order_journal_.order.underlying_account)

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_sell_order_ack_receive(loop_count, order_id, create_sell_order_date_time,
                                      total_loop_count, placed_order_journal_obj_ack_response,
                                      expected_sell_order_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed order ACK of order_id {order_id}")

        sell_fill_journal_obj = copy.deepcopy(sell_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, sell_fill_journal_obj.fill_px, sell_fill_journal_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_sell_order_after_all_buys(loop_count, total_loop_count, order_id,
                                                                create_sell_order_date_time, sell_symbol, placed_fill_journal_obj,
                                                                expected_sell_order_snapshot, expected_sell_symbol_side_snapshot,
                                                                expected_pair_strat, expected_strat_limits_,
                                                                expected_strat_status, expected_strat_brief_obj,
                                                                expected_portfolio_status, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order FILL")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")


def handle_test_sell_buy_order(leg1_symbol: str, leg2_symbol: str, total_loop_count: int,
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
    active_strat, executor_web_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
                                           leg1_side=Side.SELL, leg2_side=Side.BUY))
    print(f"Created Strat: {active_strat}")
    if active_strat.pair_strat_params.strat_leg1.side == Side.BUY:
        buy_symbol = active_strat.pair_strat_params.strat_leg1.sec.sec_id
        sell_symbol = active_strat.pair_strat_params.strat_leg2.sec.sec_id
    else:
        buy_symbol = active_strat.pair_strat_params.strat_leg2.sec.sec_id
        sell_symbol = active_strat.pair_strat_params.strat_leg1.sec.sec_id

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    order_id = None
    for loop_count in range(1, total_loop_count + 1):
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_order_snapshot = copy.deepcopy(expected_sell_order_snapshot_)
        expected_sell_order_snapshot.order_brief.security.sec_id = sell_symbol

        expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
        expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = leg1_symbol
        expected_pair_strat.pair_strat_params.strat_leg1.side = Side.SELL
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = leg2_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.side = Side.BUY

        expected_strat_status = copy.deepcopy(expected_start_status_)

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)
        current_itr_expected_sell_order_journal_.order.security.sec_id = sell_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1], is_non_systematic_run)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_order
            place_new_order(sell_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        create_sell_order_date_time: DateTime = placed_order_journal.order_event_date_time
        order_id = placed_order_journal.order.order_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_sell_order_computes_before_buys(loop_count, total_loop_count, order_id,
                                                     sell_symbol, placed_order_journal, expected_sell_order_snapshot,
                                                     expected_sell_symbol_side_snapshot, expected_pair_strat,
                                                     expected_strat_limits_, expected_strat_status,
                                                     expected_strat_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_sell_order_journal_.order.px,
            current_itr_expected_sell_order_journal_.order.qty,
            current_itr_expected_sell_order_journal_.order.side,
            current_itr_expected_sell_order_journal_.order.security.sec_id,
            current_itr_expected_sell_order_journal_.order.underlying_account)

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_sell_order_ack_receive(loop_count, order_id, create_sell_order_date_time,
                                      total_loop_count, placed_order_journal_obj_ack_response,
                                      expected_sell_order_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed order ACK of order_id {order_id}")

        sell_fill_journal_obj = copy.deepcopy(sell_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, sell_fill_journal_obj.fill_px, sell_fill_journal_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_sell_order_before_buys(
            loop_count, total_loop_count, order_id, create_sell_order_date_time, sell_symbol, placed_fill_journal_obj,
            expected_sell_order_snapshot, expected_sell_symbol_side_snapshot, expected_pair_strat,
            expected_strat_limits_, expected_strat_status, expected_strat_brief_obj,
            expected_portfolio_status, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order FILL")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")

    order_id = None
    for loop_count in range(1, total_loop_count + 1):
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_order_snapshot = copy.deepcopy(expected_buy_order_snapshot_)
        expected_buy_order_snapshot.order_brief.security.sec_id = buy_symbol

        expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
        expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = leg1_symbol
        expected_pair_strat.pair_strat_params.strat_leg1.side = Side.SELL
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = leg2_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.side = Side.BUY

        expected_strat_status = copy.deepcopy(expected_start_status_)

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {leg1_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], is_non_systematic_run)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(110, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_order
            place_new_order(buy_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        order_id = placed_order_journal.order.order_id
        create_buy_order_date_time: DateTime = placed_order_journal.order_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_buy_order_computes_after_sells(loop_count, total_loop_count, order_id, buy_symbol,
                                                    placed_order_journal, expected_buy_order_snapshot,
                                                    expected_buy_symbol_side_snapshot, expected_pair_strat,
                                                    expected_strat_limits_, expected_strat_status,
                                                    expected_strat_brief_obj, expected_portfolio_status,
                                                    executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_buy_order_journal_.order.px,
            current_itr_expected_buy_order_journal_.order.qty,
            current_itr_expected_buy_order_journal_.order.side,
            current_itr_expected_buy_order_journal_.order.security.sec_id,
            current_itr_expected_buy_order_journal_.order.underlying_account
        )

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_buy_order_ack_receive(loop_count, order_id, create_buy_order_date_time,
                                     placed_order_journal_obj_ack_response, expected_buy_order_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order ACK of order_id {order_id}")

        buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_buy_order_after_all_sells(loop_count, total_loop_count,
                                                                order_id, create_buy_order_date_time,
                                                                buy_symbol, placed_fill_journal_obj,
                                                                expected_buy_order_snapshot,
                                                                expected_buy_symbol_side_snapshot,
                                                                expected_pair_strat,
                                                                expected_strat_limits_, expected_strat_status,
                                                                expected_strat_brief_obj, expected_portfolio_status,
                                                                executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order FILL of order_id {order_id}")

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


def get_order_snapshot_from_order_id(order_id, executor_web_client: StratExecutorServiceHttpClient
                                     ) -> OrderSnapshotBaseModel | None:
    order_snapshot_list = executor_web_client.get_all_order_snapshot_client(-100)
    expected_order_snapshot: OrderSnapshotBaseModel | None = None
    for order_snapshot in order_snapshot_list:
        if order_snapshot.order_brief.order_id == order_id:
            expected_order_snapshot = order_snapshot
            break
    assert expected_order_snapshot is not None, "Expected order_snapshot as not None but received as None"
    return expected_order_snapshot


def create_fx_symbol_overview():
    fx_symbol_overview = fx_symbol_overview_obj()
    created_fx_symbol_overview = (
        strat_manager_service_native_web_client.create_fx_symbol_overview_client(fx_symbol_overview))
    fx_symbol_overview.id = created_fx_symbol_overview.id
    assert created_fx_symbol_overview == fx_symbol_overview, \
        f"Mismatch symbol_overview: expected {fx_symbol_overview}, received {created_fx_symbol_overview}"


def verify_rej_orders(check_ack_to_reject_orders: bool, last_order_id: int | None,
                      check_order_event: OrderEventType, symbol: str,
                      executor_web_client: StratExecutorServiceHttpClient) -> str:
    # internally checks order_journal is not None else raises assert exception internally
    latest_order_journal = get_latest_order_journal_with_event_and_symbol(check_order_event, symbol,
                                                                          executor_web_client,
                                                                          last_order_id=last_order_id)
    last_order_id = latest_order_journal.order.order_id

    if check_ack_to_reject_orders:
        if check_order_event not in [OrderEventType.OE_INT_REJ, OrderEventType.OE_BRK_REJ, OrderEventType.OE_EXH_REJ]:
            # internally checks fills_journal is not None else raises assert exception
            latest_fill_journal = get_latest_fill_journal_from_order_id(latest_order_journal.order.order_id,
                                                                        executor_web_client)

    order_snapshot = get_order_snapshot_from_order_id(last_order_id,
                                                      executor_web_client)
    assert order_snapshot.order_status == OrderStatusType.OE_DOD, \
        "Unexpected order_snapshot.order_status: expected OrderStatusType.OE_DOD, " \
        f"received {order_snapshot.order_status}"

    return last_order_id


def handle_rej_order_test(buy_symbol, sell_symbol, expected_strat_limits_,
                          last_trade_fixture_list, top_of_book_list_, max_loop_count_per_side,
                          check_ack_to_reject_orders: bool, executor_web_client: StratExecutorServiceHttpClient,
                          config_dict, residual_wait_secs):
    # explicitly setting waived_min_orders to 10 for this test case
    expected_strat_limits_.cancel_rate.waived_min_orders = 10

    # buy fills check
    continues_order_count, continues_special_order_count = get_continuous_order_configs(buy_symbol, config_dict)
    buy_order_count = 0
    buy_special_order_count = 0
    special_case_counter = 0
    last_id = None
    buy_rej_last_id = None
    for loop_count in range(1, max_loop_count_per_side + 1):
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])
        time.sleep(2)  # delay for order to get placed

        if buy_order_count < continues_order_count:
            check_order_event = OrderEventType.OE_CXL_ACK
            buy_order_count += 1
        else:
            if buy_special_order_count < continues_special_order_count:
                special_case_counter += 1
                if special_case_counter % 2 == 0:
                    check_order_event = OrderEventType.OE_BRK_REJ
                else:
                    check_order_event = OrderEventType.OE_EXH_REJ
                buy_special_order_count += 1
            else:
                check_order_event = OrderEventType.OE_CXL_ACK
                buy_order_count = 1
                buy_special_order_count = 0

        # internally contains assert checks
        last_id = verify_rej_orders(check_ack_to_reject_orders, last_id, check_order_event,
                                    buy_symbol, executor_web_client)

        if check_order_event in [OrderEventType.OE_BRK_REJ, OrderEventType.OE_EXH_REJ]:
            buy_rej_last_id = last_id

    if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
        time.sleep(residual_wait_secs)  # to start sell after buy is completely done

    # sell fills check
    continues_order_count, continues_special_order_count = get_continuous_order_configs(sell_symbol, config_dict)
    last_id = None
    sell_rej_last_id = None
    sell_order_count = 0
    sell_special_order_count = 0
    for loop_count in range(1, max_loop_count_per_side + 1):
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])
        time.sleep(2)  # delay for order to get placed

        if sell_order_count < continues_order_count:
            check_order_event = OrderEventType.OE_CXL_ACK
            sell_order_count += 1
        else:
            if sell_special_order_count < continues_special_order_count:
                special_case_counter += 1
                if special_case_counter % 2 == 0:
                    check_order_event = OrderEventType.OE_BRK_REJ
                else:
                    check_order_event = OrderEventType.OE_EXH_REJ
                sell_special_order_count += 1
            else:
                check_order_event = OrderEventType.OE_CXL_ACK
                sell_order_count = 1
                sell_special_order_count = 0

        # internally contains assert checks
        last_id = verify_rej_orders(check_ack_to_reject_orders, last_id, check_order_event,
                                    sell_symbol, executor_web_client)

        if check_order_event in [OrderEventType.OE_BRK_REJ, OrderEventType.OE_EXH_REJ]:
            sell_rej_last_id = last_id
    return buy_rej_last_id, sell_rej_last_id

def verify_cxl_rej(last_cxl_order_id: str | None, last_cxl_rej_order_id: str | None,
                   check_order_event: OrderEventType, symbol: str,
                   executor_web_client: StratExecutorServiceHttpClient) -> Tuple[str, str]:
    if check_order_event == OrderEventType.OE_CXL_REJ:
        # internally checks order_journal is not None else raises assert exception internally
        latest_cxl_rej_order_journal = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL_REJ, symbol,
                                                           executor_web_client,
                                                           last_order_id=last_cxl_rej_order_id)
        last_cxl_rej_order_id = latest_cxl_rej_order_journal.order.order_id

        order_snapshot = get_order_snapshot_from_order_id(latest_cxl_rej_order_journal.order.order_id,
                                                          executor_web_client)
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

    # checks order_journal is not None else raises assert exception internally
    latest_cxl_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL_ACK, symbol,
                                                                              executor_web_client,
                                                                              last_order_id=last_cxl_order_id)
    last_cxl_order_id = latest_cxl_order_journal.order.order_id

    return last_cxl_order_id, last_cxl_rej_order_id


def create_fills_for_underlying_account_test(buy_symbol: str, sell_symbol: str, top_of_book_list_: List[Dict],
                                             tob_last_update_date_time_tracker: DateTime | None,
                                             order_id: str | None, underlying_account_prefix: str, side: Side,
                                             executor_web_client: StratExecutorServiceHttpClient):
    loop_count = 1
    if side == Side.BUY:
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])
        symbol = buy_symbol
        wait_stop_px = 110
    else:
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])
        symbol = sell_symbol
        wait_stop_px = 120

    # Waiting for tob to trigger place order
    tob_last_update_date_time_tracker = \
        wait_for_get_new_order_placed_from_tob(wait_stop_px, symbol, tob_last_update_date_time_tracker,
                                               side, executor_web_client)

    placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                          symbol, executor_web_client,
                                                                          last_order_id=order_id)
    order_id = placed_order_journal.order.order_id

    executor_web_client.trade_simulator_process_order_ack_query_client(
        order_id, placed_order_journal.order.px,
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
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, fill_px, fill_qty,
            placed_order_journal.order.side,
            placed_order_journal.order.security.sec_id, underlying_account)
    return tob_last_update_date_time_tracker, order_id


def verify_unsolicited_cxl_orders(last_id: str | None,
                                  check_order_event: OrderEventType, symbol: str,
                                  executor_web_client: StratExecutorServiceHttpClient) -> str:
    # internally checks order_journal is not None else raises assert exception internally
    if check_order_event == OrderEventType.OE_CXL:
        latest_order_journal = get_latest_order_journal_with_event_and_symbol(check_order_event, symbol,
                                                                              executor_web_client,
                                                                              last_order_id=last_id)
    else:
        # checking no latest order with OE_CXL
        latest_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL, symbol,
                                                                              executor_web_client,
                                                                              expect_no_order=True,
                                                                              last_order_id=last_id)

    return latest_order_journal.order.order_id


def handle_unsolicited_cxl_for_sides(symbol: str, last_id: str, last_cxl_ack_id: str, order_count: int,
                                     continues_order_count: int, cxl_count: int, continues_unsolicited_cxl_count: int,
                                     executor_web_client: StratExecutorServiceHttpClient):
    if order_count < continues_order_count:
        check_order_event = OrderEventType.OE_CXL
        order_count += 1
        time.sleep(10)
    else:
        if cxl_count < continues_unsolicited_cxl_count:
            check_order_event = OrderEventType.OE_UNSOL_CXL
            cxl_count += 1
        else:
            check_order_event = OrderEventType.OE_CXL
            order_count = 1
            cxl_count = 0
            time.sleep(10)

    # internally contains assert checks
    last_id = verify_unsolicited_cxl_orders(last_id, check_order_event, symbol, executor_web_client)
    if check_order_event != OrderEventType.OE_UNSOL_CXL:
        latest_cxl_ack_obj = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL_ACK,
                                                                            symbol, executor_web_client,
                                                                            last_order_id=last_cxl_ack_id)
        last_cxl_ack_id = latest_cxl_ack_obj.order.order_id

    return last_id, last_cxl_ack_id, order_count, cxl_count


def handle_unsolicited_cxl(buy_symbol, sell_symbol, last_trade_fixture_list, max_loop_count_per_side, top_of_book_list_,
                           executor_web_client: StratExecutorServiceHttpClient, config_dict, residual_wait_sec):
        # buy fills check
        continues_order_count, continues_special_order_count = get_continuous_order_configs(buy_symbol, config_dict)
        buy_order_count = 0
        buy_cxl_order_count = 0
        last_id = None
        last_cxl_ack_id = None
        for loop_count in range(1, max_loop_count_per_side + 1):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])
            time.sleep(2)  # delay for order to get placed

            last_id, last_cxl_ack_id, buy_order_count, buy_cxl_order_count = \
                handle_unsolicited_cxl_for_sides(buy_symbol, last_id, last_cxl_ack_id,
                                                 buy_order_count, continues_order_count,
                                                 buy_cxl_order_count, continues_special_order_count,
                                                 executor_web_client)

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)   # to start sell after buy is completely done

        # sell fills check
        continues_order_count, continues_special_order_count = get_continuous_order_configs(sell_symbol, config_dict)
        sell_order_count = 0
        sell_cxl_order_count = 0
        last_id = None
        last_cxl_ack_id = None
        for loop_count in range(1, max_loop_count_per_side + 1):
            run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
            run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])
            time.sleep(2)  # delay for order to get placed

            last_id, last_cxl_ack_id, sell_order_count, sell_cxl_order_count = \
                handle_unsolicited_cxl_for_sides(sell_symbol, last_id, last_cxl_ack_id,
                                                 sell_order_count, continues_order_count,
                                                 sell_cxl_order_count, continues_special_order_count,
                                                 executor_web_client)


def get_partial_allowed_ack_qty(symbol: str, qty: int, config_dict: Dict):
    symbol_configs = get_symbol_configs(symbol, config_dict)

    if symbol_configs is not None:
        if (ack_percent := symbol_configs.get("ack_percent")) is not None:
            qty = int((ack_percent / 100) * qty)
    return qty


def handle_partial_ack_checks(symbol: str, new_order_id: str, acked_order_id: str,
                              executor_web_client: StratExecutorServiceHttpClient, config_dict):
    new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                       symbol, executor_web_client,
                                                                       last_order_id=new_order_id)
    new_order_id = new_order_journal.order.order_id
    partial_ack_qty = get_partial_allowed_ack_qty(symbol, new_order_journal.order.qty, config_dict)

    ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                       symbol, executor_web_client,
                                                                       last_order_id=acked_order_id)
    acked_order_id = ack_order_journal.order.order_id
    assert ack_order_journal.order.qty == partial_ack_qty, f"Mismatch partial_ack_qty: expected {partial_ack_qty}, " \
                                                           f"received {ack_order_journal.order.qty}"

    return new_order_id, acked_order_id, partial_ack_qty


def underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_strat_, expected_strat_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_trade_fixture_list, market_depth_basemodel_list,
                                             top_of_book_list_, strat_mode: StratMode | None = None):
    buy_symbol = buy_sell_symbol_list[0][0]
    sell_symbol = buy_sell_symbol_list[0][1]

    activated_strat, executor_http_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_, strat_mode=strat_mode))

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
    loop_count = 1
    run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0], avoid_order_trigger=True)
    return buy_symbol, sell_symbol, activated_strat, executor_http_client


def handle_place_order_and_check_str_in_alert_for_executor_limits(symbol: str, side: Side, px: float, qty: int,
                                                                  check_str: str, assert_fail_msg: str,
                                                                  activated_pair_strat_id: int,
                                                                  executor_web_client: StratExecutorServiceHttpClient,
                                                                  last_order_id: str | None = None):
    # placing new non-systematic new_order
    place_new_order(symbol, side, px, qty, executor_web_client)
    print(f"symbol: {symbol}, Created new_order obj")

    new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW, symbol,
                                                                       executor_web_client,
                                                                       expect_no_order=True,
                                                                       last_order_id=last_order_id)

    # Checking alert in strat_alert
    strat_alert = log_analyzer_web_client.get_strat_alert_client(activated_pair_strat_id)
    for alert in strat_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            return alert
    else:
        # Checking alert in portfolio_alert if reason failed to add in strat_alert
        portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
        for alert in portfolio_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                return alert
        else:
            assert False, assert_fail_msg


def handle_test_for_strat_pause_on_less_consumable_cxl_qty_without_fill(buy_symbol, sell_symbol, active_pair_strat_id,
                                                                        last_trade_fixture_list,
                                                                        top_of_book_list_, side: Side,
                                                                        executor_web_client:
                                                                        StratExecutorServiceHttpClient):

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
    loop_count = 1
    run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], avoid_order_trigger=True)

    check_symbol = buy_symbol if side == Side.BUY else sell_symbol

    px = 100
    qty = 90
    check_str = f"Consumable cxl qty can't be < 0, currently is .* for symbol {check_symbol}"
    assert_fail_message = "Could not find any alert containing message to block orders due to less buy consumable " \
                          "cxl qty"
    # placing new non-systematic new_order
    place_new_order(check_symbol, side, px, qty, executor_web_client)
    print(f"symbol: {check_symbol}, Created new_order obj")

    new_order_journal = get_latest_order_journal_with_events_and_symbol([OrderEventType.OE_CXL_ACK,
                                                                         OrderEventType.OE_UNSOL_CXL], check_symbol,
                                                                       executor_web_client)
    time.sleep(2)
    strat_alert = log_analyzer_web_client.get_strat_alert_client(active_pair_strat_id)

    for alert in strat_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        # Checking alert in portfolio_alert if reason failed to add in strat_alert
        portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
        for alert in portfolio_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            assert False, assert_fail_message
    assert True


def handle_test_for_strat_pause_on_less_consumable_cxl_qty_with_fill(
        buy_symbol, sell_symbol, active_pair_strat_id, last_trade_fixture_list,
        top_of_book_list_, side, executor_web_client: StratExecutorServiceHttpClient):

    # buy test
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
    loop_count = 1
    run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], avoid_order_trigger=True)

    check_symbol = buy_symbol if side == Side.BUY else sell_symbol

    px = 100
    qty = 90
    check_str = f"Consumable cxl qty can't be < 0, currently is .* for symbol {check_symbol}"
    assert_fail_message = "Could not find any alert containing message to block orders due to less buy consumable " \
                          "cxl qty"
    # placing new non-systematic new_order
    place_new_order(check_symbol, side, px, qty, executor_web_client)
    print(f"symbol: {check_symbol}, Created new_order obj")

    ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, check_symbol,
                                                                       executor_web_client)
    cxl_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_CXL_ACK, check_symbol,
                                                                       executor_web_client)

    strat_alert = log_analyzer_web_client.get_strat_alert_client(active_pair_strat_id)
    for alert in strat_alert.alerts:
        if re.search(check_str, alert.alert_brief):
            break
    else:
        # Checking alert in portfolio_alert if reason failed to add in strat_alert
        portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
        for alert in portfolio_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            assert False, assert_fail_message
    assert True


def get_symbol_configs(symbol: str, config_dict: Dict) -> Dict | None:
    """
    WARNING : This Function is duplicate test function of what we have in trade simulator to keep test
    disconnected from main code, keep it sync with original
    """
    symbol_configs: Dict | None = config_dict.get("symbol_configs") \
        if config_dict is not None else None
    if symbol_configs:
        symbol_configs: Dict = {re.compile(k, re.IGNORECASE): v for k, v in symbol_configs.items()}

        found_symbol_config_list: List = []
        if symbol_configs is not None:
            for k, v in symbol_configs.items():
                if k.match(symbol):
                    found_symbol_config_list.append(v)
            if found_symbol_config_list:
                if len(found_symbol_config_list) == 1:
                    return found_symbol_config_list[0]
                else:
                    logging.error(f"bad configuration : multiple symbol matches found for passed symbol: {symbol};;;"
                                  f"found_symbol_configurations: "
                                  f"{[str(found_symbol_config) for found_symbol_config in found_symbol_config_list]}")
    return None


def get_partial_allowed_fill_qty(check_symbol: str, config_dict: Dict, qty: int):
    """
    ATTENTION: This Function is dummy of original impl present in trade_executor, keep it sync with original
    """
    symbol_configs = get_symbol_configs(check_symbol, config_dict)
    partial_filled_qty: int | None = None
    if symbol_configs is not None:
        if (fill_percent := symbol_configs.get("fill_percent")) is not None:
            partial_filled_qty = int((fill_percent / 100) * qty)
    return partial_filled_qty


def underlying_handle_simulated_partial_fills_test(loop_count, check_symbol, buy_symbol,
                                                   sell_symbol, last_trade_fixture_list,
                                                   top_of_book_list_, last_order_id, config_dict,
                                                   executor_web_client: StratExecutorServiceHttpClient):
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
    if check_symbol == buy_symbol:
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])
    else:
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])

    order_ack_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                       check_symbol, executor_web_client,
                                                                       last_order_id=last_order_id)
    last_order_id = order_ack_journal.order.order_id
    time.sleep(5)

    # ATTENTION: Below code is dummy of original impl present in trade_executor, keep it sync with original
    partial_filled_qty = get_partial_allowed_fill_qty(check_symbol, config_dict, order_ack_journal.order.qty)

    latest_fill_journal = get_latest_fill_journal_from_order_id(last_order_id, executor_web_client)
    assert latest_fill_journal.fill_qty == partial_filled_qty, f"fill_qty mismatch: expected {partial_filled_qty}, " \
                                                               f"received {latest_fill_journal.fill_qty}"
    return last_order_id, partial_filled_qty


def underlying_handle_simulated_multi_partial_fills_test(loop_count, check_symbol, buy_symbol,
                                                         sell_symbol, last_trade_fixture_list,
                                                         top_of_book_list_, last_order_id,
                                                         executor_web_client: StratExecutorServiceHttpClient,
                                                         config_dict, fill_id: str | None = None):
    run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
    if check_symbol == buy_symbol:
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])
    else:
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])

    new_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                       check_symbol, executor_web_client,
                                                                       last_order_id=last_order_id)
    last_order_id = new_order_journal.order.order_id

    # ATTENTION: Below code is dummy of original impl present in trade_executor, keep it sync with original
    partial_filled_qty = get_partial_allowed_fill_qty(check_symbol, config_dict, new_order_journal.order.qty)

    fills_count = get_symbol_configs(check_symbol, config_dict).get("total_fill_count")
    time.sleep(5)
    time_out_loop_count = 5
    latest_fill_journals = []
    for _ in range(time_out_loop_count):
        latest_fill_journals = get_fill_journals_for_order_id(last_order_id, executor_web_client)
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


def strat_done_after_exhausted_consumable_notional(
        leg_1_symbol, leg_2_symbol, pair_strat_, expected_strat_limits_,
        expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list, market_depth_basemodel_list,
        top_of_book_list_, residual_wait_sec, side_to_check: Side, leg_1_side: Side | None = None,
        leg_2_side: Side | None = None):

    if leg_1_side is None or leg_2_side is None:
        leg_1_side = Side.BUY
        leg_2_side = Side.SELL

    created_pair_strat, executor_http_client = (
        create_pre_order_test_requirements(leg_1_symbol, leg_2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_, leg1_side=leg_1_side,
                                           leg2_side=leg_2_side))

    if leg_1_side == Side.BUY:
        buy_symbol = leg_1_symbol
        sell_symbol = leg_2_symbol
    else:
        buy_symbol = leg_2_symbol
        sell_symbol = leg_1_symbol

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path), load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 95
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.trade_simulator_reload_config_query_client()

        # Positive Check
        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        if side_to_check == Side.BUY:
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
            check_symbol = buy_symbol
        else:
            run_sell_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[1])
            check_symbol = sell_symbol
        time.sleep(2)  # delay for order to get placed

        ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, check_symbol,
                                                                           executor_http_client, assert_code=1)
        order_snapshot = get_order_snapshot_from_order_id(ack_order_journal.order.order_id, executor_http_client)
        assert order_snapshot.order_status == OrderStatusType.OE_ACKED, "OrderStatus mismatched: expected status " \
                                                                        f"OrderStatusType.OE_ACKED received " \
                                                                        f"{order_snapshot.order_status}"
        time.sleep(residual_wait_sec)  # wait to get buy order residual

        # Negative Check
        # Next placed order must not get placed, instead it should find consumable_notional as exhausted for further
        # orders and should come out of executor run and must set strat_state to StratState_DONE

        # buy fills check
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_http_client)
        if side_to_check == Side.BUY:
            run_buy_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[0])
        else:
            run_sell_top_of_book(buy_symbol, sell_symbol, executor_http_client, top_of_book_list_[1])
        time.sleep(2)  # delay for order to get placed
        ack_order_journal = (
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW, check_symbol, executor_http_client,
                                                           last_order_id=ack_order_journal.order.order_id,
                                                           expect_no_order=True, assert_code=3))
        pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat.strat_state == StratState.StratState_DONE, (
            f"Mismatched strat_state, expected {StratState.StratState_DONE}, received {pair_strat.strat_state}")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


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
    post_trade_engine_service_http_client.reload_cache_query_client()


def append_csv_file(file_name: str, records: List[List[any]]):
    with open(file_name, "a") as csv_file:
        list_writer = writer(csv_file)
        record: List[any]
        for record in records:
            list_writer.writerow(record)


def handle_test_buy_sell_pair_order(buy_symbol: str, sell_symbol: str, total_loop_count: int,
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
    active_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_))
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

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], is_non_systematic_run)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(110, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_order
            place_new_order(buy_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        order_id = placed_order_journal.order.order_id
        create_buy_order_date_time: DateTime = placed_order_journal.order_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_buy_order_computes_before_all_sells(loop_count, 0, order_id, buy_symbol,
                                        placed_order_journal, expected_buy_order_snapshot,
                                        expected_buy_symbol_side_snapshot, expected_pair_strat,
                                        expected_strat_limits_, expected_strat_status,
                                        expected_strat_brief_obj, expected_portfolio_status, executor_web_client, True)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_buy_order_journal_.order.px,
            current_itr_expected_buy_order_journal_.order.qty,
            current_itr_expected_buy_order_journal_.order.side,
            current_itr_expected_buy_order_journal_.order.security.sec_id,
            current_itr_expected_buy_order_journal_.order.underlying_account
        )

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_buy_order_ack_receive(loop_count, order_id, create_buy_order_date_time,
                                     placed_order_journal_obj_ack_response, expected_buy_order_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order ACK of order_id {order_id}")

        buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_buy_order_before_sells(loop_count, 0, order_id, create_buy_order_date_time,
                                                buy_symbol, placed_fill_journal_obj,
                                                expected_buy_order_snapshot, expected_buy_symbol_side_snapshot,
                                                expected_pair_strat,
                                                expected_strat_limits_, expected_strat_status,
                                                expected_strat_brief_obj, expected_portfolio_status,
                                                executor_web_client, True)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order FILL of order_id {order_id}")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")

        # handle sell order
        order_id = None

        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_order_snapshot = copy.deepcopy(expected_sell_order_snapshot_)
        expected_sell_order_snapshot.order_brief.security.sec_id = sell_symbol

        expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
        expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol

        expected_strat_status = copy.deepcopy(expected_start_status_)

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)
        current_itr_expected_sell_order_journal_.order.security.sec_id = sell_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1], is_non_systematic_run)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_order
            place_new_order(sell_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        create_sell_order_date_time: DateTime = placed_order_journal.order_event_date_time
        order_id = placed_order_journal.order.order_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_sell_order_computes_after_all_buys(loop_count, loop_count, order_id,
                                         sell_symbol, placed_order_journal, expected_sell_order_snapshot,
                                         expected_sell_symbol_side_snapshot, expected_pair_strat,
                                         expected_strat_limits_, expected_strat_status,
                                         expected_strat_brief_obj, expected_portfolio_status, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_sell_order_journal_.order.px,
            current_itr_expected_sell_order_journal_.order.qty,
            current_itr_expected_sell_order_journal_.order.side,
            current_itr_expected_sell_order_journal_.order.security.sec_id,
            current_itr_expected_sell_order_journal_.order.underlying_account)

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_sell_order_ack_receive(loop_count, order_id, create_sell_order_date_time,
                                      loop_count, placed_order_journal_obj_ack_response,
                                      expected_sell_order_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed order ACK of order_id {order_id}")

        sell_fill_journal_obj = copy.deepcopy(sell_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, sell_fill_journal_obj.fill_px, sell_fill_journal_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_sell_order_after_all_buys(loop_count, loop_count, order_id,
                                                 create_sell_order_date_time, sell_symbol, placed_fill_journal_obj,
                                                 expected_sell_order_snapshot, expected_sell_symbol_side_snapshot,
                                                 expected_pair_strat, expected_strat_limits_,
                                                 expected_strat_status, expected_strat_brief_obj,
                                                 expected_portfolio_status, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order FILL")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")


def handle_test_sell_buy_pair_order(leg1_symbol: str, leg2_symbol: str, total_loop_count: int,
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
    active_strat, executor_web_client = (
        create_pre_order_test_requirements(leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list,
                                           last_trade_fixture_list, market_depth_basemodel_list, top_of_book_list_,
                                           leg1_side=Side.SELL, leg2_side=Side.BUY))
    print(f"Created Strat: {active_strat}")
    if active_strat.pair_strat_params.strat_leg1.side == Side.BUY:
        buy_symbol = active_strat.pair_strat_params.strat_leg1.sec.sec_id
        sell_symbol = active_strat.pair_strat_params.strat_leg2.sec.sec_id
    else:
        buy_symbol = active_strat.pair_strat_params.strat_leg2.sec.sec_id
        sell_symbol = active_strat.pair_strat_params.strat_leg1.sec.sec_id

    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    order_id = None
    for loop_count in range(1, total_loop_count + 1):
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_order_snapshot = copy.deepcopy(expected_sell_order_snapshot_)
        expected_sell_order_snapshot.order_brief.security.sec_id = sell_symbol

        expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
        expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = leg1_symbol
        expected_pair_strat.pair_strat_params.strat_leg1.side = Side.SELL
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = leg2_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.side = Side.BUY

        expected_strat_status = copy.deepcopy(expected_start_status_)

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)
        current_itr_expected_sell_order_journal_.order.security.sec_id = sell_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1], is_non_systematic_run)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_order
            place_new_order(sell_symbol, Side.SELL, sell_order_.order.px, sell_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        create_sell_order_date_time: DateTime = placed_order_journal.order_event_date_time
        order_id = placed_order_journal.order.order_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_sell_order_computes_before_buys(loop_count, 0, order_id,
                                                     sell_symbol, placed_order_journal, expected_sell_order_snapshot,
                                                     expected_sell_symbol_side_snapshot, expected_pair_strat,
                                                     expected_strat_limits_, expected_strat_status,
                                                     expected_strat_brief_obj, executor_web_client, True)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_sell_order_journal_.order.px,
            current_itr_expected_sell_order_journal_.order.qty,
            current_itr_expected_sell_order_journal_.order.side,
            current_itr_expected_sell_order_journal_.order.security.sec_id,
            current_itr_expected_sell_order_journal_.order.underlying_account)

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_sell_order_ack_receive(loop_count, order_id, create_sell_order_date_time,
                                      total_loop_count, placed_order_journal_obj_ack_response,
                                      expected_sell_order_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed order ACK of order_id {order_id}")

        sell_fill_journal_obj = copy.deepcopy(sell_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, sell_fill_journal_obj.fill_px, sell_fill_journal_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_sell_order_before_buys(
            loop_count, 0, order_id, create_sell_order_date_time, sell_symbol, placed_fill_journal_obj,
            expected_sell_order_snapshot, expected_sell_symbol_side_snapshot, expected_pair_strat,
            expected_strat_limits_, expected_strat_status, expected_strat_brief_obj,
            expected_portfolio_status, executor_web_client, True)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed order FILL")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")

        order_id = None
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_order_snapshot = copy.deepcopy(expected_buy_order_snapshot_)
        expected_buy_order_snapshot.order_brief.security.sec_id = buy_symbol

        expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
        expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol

        expected_pair_strat = copy.deepcopy(pair_strat_)
        expected_pair_strat.pair_strat_params.strat_leg1.sec.sec_id = leg1_symbol
        expected_pair_strat.pair_strat_params.strat_leg1.side = Side.SELL
        expected_pair_strat.pair_strat_params.strat_leg2.sec.sec_id = leg2_symbol
        expected_pair_strat.pair_strat_params.strat_leg2.side = Side.BUY

        expected_strat_status = copy.deepcopy(expected_start_status_)

        expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
        expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
        expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

        expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

        # placing order
        current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
        current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol

        # running last trade once more before sell side
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        print(f"LastTrades created: buy_symbol: {leg1_symbol}, sell_symbol: {sell_symbol}")

        # Running TopOfBook (this triggers expected buy order)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0], is_non_systematic_run)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, created tob")

        if not is_non_systematic_run:
            # Waiting for tob to trigger place order
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed_from_tob(110, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_order
            place_new_order(buy_symbol, Side.BUY, buy_order_.order.px, buy_order_.order.qty, executor_web_client)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_order obj")
            time.sleep(2)

        placed_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_order_id=order_id)
        order_id = placed_order_journal.order.order_id
        create_buy_order_date_time: DateTime = placed_order_journal.order_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received order_journal with {order_id}")
        time.sleep(2)

        # Checking placed order computations
        check_placed_buy_order_computes_after_sells(loop_count, loop_count, order_id, buy_symbol,
                                                    placed_order_journal, expected_buy_order_snapshot,
                                                    expected_buy_symbol_side_snapshot, expected_pair_strat,
                                                    expected_strat_limits_, expected_strat_status,
                                                    expected_strat_brief_obj, expected_portfolio_status,
                                                    executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order of order_id {order_id}")

        executor_web_client.trade_simulator_process_order_ack_query_client(
            order_id, current_itr_expected_buy_order_journal_.order.px,
            current_itr_expected_buy_order_journal_.order.qty,
            current_itr_expected_buy_order_journal_.order.side,
            current_itr_expected_buy_order_journal_.order.security.sec_id,
            current_itr_expected_buy_order_journal_.order.underlying_account
        )

        placed_order_journal_obj_ack_response = \
            get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed order
        placed_buy_order_ack_receive(loop_count, order_id, create_buy_order_date_time,
                                     placed_order_journal_obj_ack_response, expected_buy_order_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order ACK of order_id {order_id}")

        buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
        executor_web_client.trade_simulator_process_fill_query_client(
            order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)

        placed_fill_journal_obj = get_latest_fill_journal_from_order_id(order_id, executor_web_client)

        # Checking Fill receive on placed order
        check_fill_receive_for_placed_buy_order_after_all_sells(loop_count, loop_count,
                                                                order_id, create_buy_order_date_time,
                                                                buy_symbol, placed_fill_journal_obj,
                                                                expected_buy_order_snapshot,
                                                                expected_buy_symbol_side_snapshot,
                                                                expected_pair_strat,
                                                                expected_strat_limits_, expected_strat_status,
                                                                expected_strat_brief_obj, expected_portfolio_status,
                                                                executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed order FILL of order_id {order_id}")

        # Sleeping to let the order get cxlled
        time.sleep(residual_test_wait)

        portfolio_status_list = strat_manager_service_native_web_client.get_all_portfolio_status_client()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, "
              f"loop completed portfolio_status {portfolio_status_list}")


def place_sanity_orders_for_executor(
        buy_symbol: str, sell_symbol: str, total_order_count_for_each_side, last_trade_fixture_list,
        top_of_book_list_, residual_wait_sec, executor_web_client, place_after_recovery: bool = False,
        expect_no_order: bool = False):

    # Placing buy orders
    buy_ack_order_id = None

    if place_after_recovery:
        order_journals = executor_web_client.get_all_order_journal_client(-100)
        max_id = 0
        for order_journal in order_journals:
            if order_journal.order.security.sec_id == buy_symbol and order_journal.order_event == OrderEventType.OE_ACK:
                if max_id < order_journal.id:
                    buy_ack_order_id = order_journal.order.order_id

    for loop_count in range(total_order_count_for_each_side):
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        run_buy_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[0])

        ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                           buy_symbol, executor_web_client,
                                                                           last_order_id=buy_ack_order_id,
                                                                           expect_no_order=expect_no_order)
        buy_ack_order_id = ack_order_journal.order.order_id

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)  # wait to make this open order residual

    # Placing sell orders
    sell_ack_order_id = None
    for loop_count in range(total_order_count_for_each_side):
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list, executor_web_client)
        run_sell_top_of_book(buy_symbol, sell_symbol, executor_web_client, top_of_book_list_[1])

        ack_order_journal = get_latest_order_journal_with_event_and_symbol(OrderEventType.OE_ACK,
                                                                           sell_symbol, executor_web_client,
                                                                           last_order_id=sell_ack_order_id,
                                                                           expect_no_order=expect_no_order)
        sell_ack_order_id = ack_order_journal.order.order_id

        if not executor_config_yaml_dict.get("allow_multiple_open_orders_per_strat"):
            time.sleep(residual_wait_sec)  # wait to make this open order residual
