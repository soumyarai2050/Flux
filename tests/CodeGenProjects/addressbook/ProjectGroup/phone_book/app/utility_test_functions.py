import logging
import random
import signal
import sys
import threading
import time
import copy
import re
from typing import Dict
import requests
import pendulum
import pexpect
from csv import writer
import os
import glob
import traceback
from datetime import timedelta

# os.environ["PORT"] = "8081"
os.environ["ModelType"] = "msgspec"

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.ORMModel.log_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_client import \
    EmailBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from FluxPythonUtils.scripts.general_utility_functions import clean_mongo_collections, parse_to_int, \
    get_mongo_db_list, drop_mongo_database, avg_of_new_val_sum_to_avg, run_gbd_terminal_with_pid, get_pid_from_port, \
    ClientError, HTTPRequestType, handle_http_response
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_client import (
    LogBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_helper import (
    post_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_http_client import PhotoBookServiceHttpClient
from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_http_client import PerformanceBenchmarkServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_client import BasketBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_client import MobileBookServiceHttpClient

code_gen_projects_dir_path = (PurePath(__file__).parent.parent.parent.parent.parent.parent.parent
                              / "Flux" / "CodeGenProjects")

PERF_BENCH_DIR = code_gen_projects_dir_path / "performance_benchmark"
pb_config_yaml_path: PurePath = PERF_BENCH_DIR / "data" / "config.yaml"
pb_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(pb_config_yaml_path))

PAIR_STRAT_ENGINE_DIR = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / "phone_book"
ps_config_yaml_path: PurePath = PAIR_STRAT_ENGINE_DIR / "data" / "config.yaml"
ps_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(ps_config_yaml_path))

LOG_ANALYZER_DIR = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / "log_book"
la_config_yaml_path = LOG_ANALYZER_DIR / "data" / "config.yaml"
la_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(la_config_yaml_path))

STRAT_EXECUTOR = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / "street_book"
executor_config_yaml_path: PurePath = STRAT_EXECUTOR / "data" / "config.yaml"
executor_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(executor_config_yaml_path))

STRAT_VIEW_ENGINE_DIR = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / "photo_book"
plan_view_config_yaml_path: PurePath = STRAT_VIEW_ENGINE_DIR / "data" / "config.yaml"
plan_view_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(plan_view_config_yaml_path))

BASKET_EXECUTOR_DIR = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / "basket_book"
basket_book_config_yaml_path: PurePath = BASKET_EXECUTOR_DIR / "data" / "config.yaml"
basket_book_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(basket_book_config_yaml_path))

MARKET_DATA_DIR = code_gen_projects_dir_path / "AddressBook" / "ProjectGroup" / "mobile_book"
mobile_book_config_yaml_path: PurePath = MARKET_DATA_DIR / "data" / "config.yaml"
mobile_book_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(mobile_book_config_yaml_path))

HOST: Final[str] = "127.0.0.1"

PERF_BENCH_CACHE_HOST: Final[str] = pb_config_yaml_dict.get("server_host")
PERF_BENCH_BEANIE_HOST: Final[str] = pb_config_yaml_dict.get("server_host")
PERF_BENCH_CACHE_PORT: Final[str] = pb_config_yaml_dict.get("main_server_cache_port")
PERF_BENCH_BEANIE_PORT: Final[str] = pb_config_yaml_dict.get("main_server_beanie_port")

PAIR_STRAT_CACHE_HOST: Final[str] = ps_config_yaml_dict.get("server_host")
PAIR_STRAT_BEANIE_HOST: Final[str] = ps_config_yaml_dict.get("server_host")
PAIR_STRAT_CACHE_PORT: Final[str] = ps_config_yaml_dict.get("main_server_cache_port")
PAIR_STRAT_BEANIE_PORT: Final[str] = ps_config_yaml_dict.get("main_server_beanie_port")
PAIR_STRAT_VIEW_PORT: Final[str] = ps_config_yaml_dict.get("view_port")

LOG_ANALYZER_CACHE_HOST: Final[str] = la_config_yaml_dict.get("server_host")
LOG_ANALYZER_BEANIE_HOST: Final[str] = la_config_yaml_dict.get("server_host")
LOG_ANALYZER_CACHE_PORT: Final[str] = la_config_yaml_dict.get("main_server_cache_port")
LOG_ANALYZER_BEANIE_PORT: Final[str] = la_config_yaml_dict.get("main_server_beanie_port")
os.environ["HOST"] = HOST
os.environ["PAIR_STRAT_BEANIE_PORT"] = PAIR_STRAT_BEANIE_PORT

STRAT_VIEW_CACHE_HOST: Final[str] = plan_view_config_yaml_dict.get("server_host")
STRAT_VIEW_BEANIE_HOST: Final[str] = plan_view_config_yaml_dict.get("server_host")
STRAT_VIEW_CACHE_PORT: Final[str] = plan_view_config_yaml_dict.get("main_server_cache_port")
STRAT_VIEW_BEANIE_PORT: Final[str] = plan_view_config_yaml_dict.get("main_server_beanie_port")

BASKET_EXECUTOR_CACHE_HOST: Final[str] = basket_book_config_yaml_dict.get("server_host")
BASKET_EXECUTOR_BEANIE_HOST: Final[str] = basket_book_config_yaml_dict.get("server_host")
BASKET_EXECUTOR_CACHE_PORT: Final[str] = basket_book_config_yaml_dict.get("main_server_cache_port")
BASKET_EXECUTOR_BEANIE_PORT: Final[str] = basket_book_config_yaml_dict.get("main_server_beanie_port")

MARKET_DATA_CACHE_HOST: Final[str] = mobile_book_config_yaml_dict.get("server_host")
MARKET_DATA_BEANIE_HOST: Final[str] = mobile_book_config_yaml_dict.get("server_host")
MARKET_DATA_CACHE_PORT: Final[str] = mobile_book_config_yaml_dict.get("main_server_cache_port")
MARKET_DATA_BEANIE_PORT: Final[str] = mobile_book_config_yaml_dict.get("main_server_beanie_port")

perf_benchmark_web_client: PerformanceBenchmarkServiceHttpClient = (
    PerformanceBenchmarkServiceHttpClient(host=PERF_BENCH_BEANIE_HOST, port=parse_to_int(PERF_BENCH_BEANIE_PORT)))
email_book_service_native_web_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient(host=PAIR_STRAT_BEANIE_HOST, port=parse_to_int(PAIR_STRAT_BEANIE_PORT))
email_book_service_native_view_web_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient.set_or_get_if_instance_exists(host=PAIR_STRAT_BEANIE_HOST,
                                                                port=parse_to_int(PAIR_STRAT_BEANIE_PORT),
                                                                view_port=parse_to_int(PAIR_STRAT_VIEW_PORT))
log_book_web_client: LogBookServiceHttpClient = (
    LogBookServiceHttpClient.set_or_get_if_instance_exists(host=LOG_ANALYZER_BEANIE_HOST,
                                                               port=parse_to_int(LOG_ANALYZER_BEANIE_PORT)))
photo_book_web_client: PhotoBookServiceHttpClient = (
    PhotoBookServiceHttpClient.set_or_get_if_instance_exists(host=STRAT_VIEW_BEANIE_HOST,
                                                                   port=parse_to_int(STRAT_VIEW_BEANIE_PORT)))
basket_book_web_client: BasketBookServiceHttpClient = (
    BasketBookServiceHttpClient.set_or_get_if_instance_exists(host=BASKET_EXECUTOR_BEANIE_HOST,
                                                                   port=parse_to_int(BASKET_EXECUTOR_BEANIE_PORT)))
mobile_book_web_client: MobileBookServiceHttpClient = (
    MobileBookServiceHttpClient.set_or_get_if_instance_exists(host=MARKET_DATA_BEANIE_HOST,
                                                              port=parse_to_int(MARKET_DATA_BEANIE_PORT)))

static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
project_dir_path = (PurePath(__file__).parent.parent.parent.parent.parent.parent.parent / "Flux" / "CodeGenProjects" / "AddressBook" / "ProjectGroup" / "phone_book")
project_app_dir_path = project_dir_path / "app"
test_project_dir_path = PurePath(__file__).parent.parent / 'data'
test_config_file_path: PurePath = test_project_dir_path / "config.yaml"
static_data_dir: PurePath = project_dir_path / "data"


def get_utc_date_time() -> pendulum.DateTime:
    # used wherever datetime needs to be set to any model field, required to make it symmetric with the
    # format of datetime fields of models fetched from db
    # mongo strips micro secs from stored datetime
    formatted_dt_utc = pendulum.DateTime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return pendulum.parse(formatted_dt_utc)


def clean_all_collections_ignoring_ui_layout() -> None:
    mongo_server_uri: str = get_mongo_server_uri()
    for db_name in get_mongo_db_list(mongo_server_uri):
        if "log_book" == db_name:
            clean_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=db_name,
                                    ignore_collections=["UILayout", "ContactAlert", "PlanAlert",
                                                        "RawPerformanceData", "ProcessedPerformanceAnalysis"])
        elif "phone_book" == db_name or "post_book" == db_name or "photo_book" == db_name:
            ignore_collections = ["UILayout"]
            if db_name == "phone_book":
                ignore_collections.append("PlanCollection")
            clean_mongo_collections(mongo_server_uri=mongo_server_uri, database_name=db_name,
                                    ignore_collections=ignore_collections)
        elif "street_book_" in db_name or db_name == "basket_book":
            drop_mongo_database(mongo_server_uri=mongo_server_uri, database_name=db_name)


def drop_all_databases() -> None:
    mongo_server_uri: str = get_mongo_server_uri()
    for db_name in get_mongo_db_list(mongo_server_uri):
        if "log_book" == db_name or "phone_book" == db_name or "post_book" == db_name or \
                "photo_book" == db_name or "street_book_" in db_name:
            drop_mongo_database(mongo_server_uri=mongo_server_uri, database_name=db_name)
        # else ignore drop database


def clean_project_logs():
    # clean all project log file, plan json.lock files, generated md, so scripts and script logs
    barter_engine_dir: PurePath = code_gen_projects_path / "AddressBook" / "ProjectGroup"
    phone_book_dir: PurePath = barter_engine_dir / "phone_book"
    post_book_dir: PurePath = barter_engine_dir / "post_book"
    log_book_dir: PurePath = barter_engine_dir / "log_book"
    street_book_dir: PurePath = barter_engine_dir / "street_book"
    photo_book_dir: PurePath = barter_engine_dir / "photo_book"

    delete_file_glob_pattens: List[str] = [
        str(phone_book_dir / "log" / "*.log*"),
        str(post_book_dir / "log" / "*.log*"),
        str(log_book_dir / "log" / "*.log*"),
        str(street_book_dir / "log" / "*.log*"),
        str(photo_book_dir / "log" / "*.log*"),
        str(phone_book_dir / "scripts" / "fx_so.sh*"),
        str(phone_book_dir / "data" / "*.json.lock"),
        str(log_book_dir / "log" / "tail_executors" / "*.log*"),
        str(street_book_dir / "data" / "executor_*_simulate_config.yaml"),
        str(street_book_dir / "scripts" / "*ps_id_*.sh*")
    ]

    files_to_delete: List[str] = []
    pattern: str
    for pattern in delete_file_glob_pattens:
        files: List[str] = glob.glob(pattern)
        files_to_delete.extend(files)

    for matched_file in files_to_delete:
        os.remove(matched_file)

#
# def run_pair_plan_log_book(executor_n_log_book: 'ExecutorNLogBookManager'):
#     log_book = pexpect.spawn("python phone_book_log_book.py &",
#                                  cwd=project_app_dir_path)
#     log_book.timeout = None
#     log_book.logfile = sys.stdout.buffer
#     executor_n_log_book.pair_plan_log_book_pid = log_book.pid
#     print(f"pair_plan_log_book PID: {log_book.pid}")
#     log_book.expect("CRITICAL: log analyzer running in simulation mode...")
#     log_book.interact()
#
#
# def run_executor(executor_n_log_book: 'ExecutorNLogBookManager'):
#     executor = pexpect.spawn("python street_book.py &", cwd=project_app_dir_path)
#     executor.timeout = None
#     executor.logfile = sys.stdout.buffer
#     executor_n_log_book.executor_pid = executor.pid
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
# class ExecutorNLogBookManager:
#     """
#     Context manager to handle running of barter_executor and log_book in threads and after test is completed,
#     handling killing of the both processes and cleaning the slate
#     """
#
#     def __init__(self):
#         # p_id(s) are getting populated by their respective thread target functions
#         self.executor_pid = None
#         self.pair_plan_log_book_pid = None
#
#     def __enter__(self):
#         executor_thread = threading.Thread(target=run_executor, args=(self,))
#         pair_plan_log_book_thread = threading.Thread(target=run_pair_plan_log_book, args=(self,))
#         executor_thread.start()
#         pair_plan_log_book_thread.start()
#         # delay for executor and log_book to get started and ready
#         time.sleep(20)
#         return self
#
#     def __exit__(self, exc_type, exc_value, exc_traceback):
#         assert kill_process(self.executor_pid), \
#             f"Something went wrong while killing barter_executor process, pid: {self.executor_pid}"
#         assert kill_process(self.pair_plan_log_book_pid), \
#             f"Something went wrong while killing pair_plan_log_book process, " \
#             f"pid: {self.pair_plan_log_book_pid}"
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


def get_continuous_chore_configs(symbol: str, config_dict: Dict) -> Tuple[int | None, int | None]:
    symbol_configs = get_symbol_configs(symbol, config_dict)
    return symbol_configs.get("continues_chore_count"), symbol_configs.get("continues_special_chore_count")


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
    position = PositionBaseModel.from_dict(position_json)
    return position


def sec_position_fixture(sec_id: str, sec_id_source: SecurityIdSource):
    sec_position_json = {
        "_id": SecPosition.next_id(),
        "security": {
            "sec_id": sec_id,
            "sec_id_source": sec_id_source
        },
        "positions": [
            position_fixture(),
            position_fixture()
        ]
    }
    sec_position = SecPositionBaseModel.from_dict(sec_position_json)
    return sec_position


def broker_fixture():
    sec_position_1 = sec_position_fixture("Type1_Sec_1", SecurityIdSource.SEDOL)
    sec_position_2 = sec_position_fixture("Type2_Sec_1.SS", SecurityIdSource.RIC)

    broker_json = {
        "bkr_disable": False,
        "sec_positions": [
            sec_position_1,
            sec_position_2
        ],
        "broker": "Bkr1",
        "bkr_priority": 5
    }
    broker1 = BrokerBaseModel.from_dict(broker_json)
    return broker1


# def get_buy_chore_related_values():
#     single_buy_chore_px = 100
#     single_buy_chore_qty = 90
#     single_buy_filled_px = 90
#     single_buy_filled_qty = 50
#     single_buy_unfilled_qty = single_buy_chore_qty - single_buy_filled_qty
#     return single_buy_chore_px, single_buy_chore_qty, single_buy_filled_px, single_buy_filled_qty, \
#         single_buy_unfilled_qty
#
#
# def get_sell_chore_related_values():
#     single_sell_chore_px = 110
#     single_sell_chore_qty = 95
#     single_sell_filled_px = 120
#     single_sell_filled_qty = 30
#     single_sell_unfilled_qty = single_sell_chore_qty - single_sell_filled_qty
#     return single_sell_chore_px, single_sell_chore_qty, single_sell_filled_px, single_sell_filled_qty, \
#         single_sell_unfilled_qty


def get_both_side_last_barter_px():
    buy_side_last_barter_px = 116
    sell_side_last_barter_px = 117
    return buy_side_last_barter_px, sell_side_last_barter_px


def update_expected_plan_brief_for_buy(expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                        expected_other_leg_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                        expected_plan_limits: PlanLimits,
                                        expected_plan_brief_obj: PlanBriefBaseModel,
                                        date_time_for_cmp: DateTime, buy_last_barter_px, sell_last_barter_px,
                                        executor_http_client: StreetBookServiceHttpClient,
                                        fill_update_after_dod: bool = False,
                                        hedge_ratio: float = 1.0):
    max_net_filled_notional = expected_plan_limits.max_net_filled_notional

    symbol_side_snapshot_list = executor_http_client.get_all_symbol_side_snapshot_client()
    all_brk_cxled_qty = 0
    for symbol_side_snapshot in symbol_side_snapshot_list:
        if symbol_side_snapshot.side == Side.BUY:
            all_brk_cxled_qty += symbol_side_snapshot.total_cxled_qty

    if expected_chore_snapshot_obj.chore_status == ChoreStatusType.OE_UNACK:
        expected_plan_brief_obj.pair_buy_side_bartering_brief.open_qty += expected_chore_snapshot_obj.chore_brief.qty
        expected_plan_brief_obj.pair_buy_side_bartering_brief.open_notional += (
                expected_chore_snapshot_obj.chore_brief.qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
        expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_open_chores = 4
    elif expected_chore_snapshot_obj.chore_status == ChoreStatusType.OE_ACKED:
        expected_plan_brief_obj.pair_buy_side_bartering_brief.open_qty -= expected_chore_snapshot_obj.last_update_fill_qty
        expected_plan_brief_obj.pair_buy_side_bartering_brief.open_notional -= (
                expected_chore_snapshot_obj.last_update_fill_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
        expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_open_chores = 4
    elif expected_chore_snapshot_obj.chore_status == ChoreStatusType.OE_DOD:
        # cxl chore
        if not fill_update_after_dod:
            unfilled_qty = expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty
            expected_plan_brief_obj.pair_buy_side_bartering_brief.open_qty -= unfilled_qty
            expected_plan_brief_obj.pair_buy_side_bartering_brief.open_notional -= (
                    unfilled_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
            expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty += (
                    expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty)
            expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_open_chores = 5
        else:
            expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty -= (
                expected_chore_snapshot_obj.last_update_fill_qty)
            expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_open_chores = 5

    open_qty = expected_plan_brief_obj.pair_buy_side_bartering_brief.open_qty
    open_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.open_notional
    expected_plan_brief_obj.pair_buy_side_bartering_brief.all_bkr_cxlled_qty = all_brk_cxled_qty
    expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_notional = \
        ((expected_plan_limits.max_single_leg_notional * hedge_ratio) -
         expected_symbol_side_snapshot.total_fill_notional - open_notional)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_open_notional = \
        expected_plan_limits.max_open_single_leg_notional - open_notional
    total_security_size: int = \
        static_data.get_security_float_from_ticker(expected_chore_snapshot_obj.chore_brief.security.sec_id)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_concentration = \
        (total_security_size / 100 * expected_plan_limits.max_concentration) - (
                open_qty + expected_symbol_side_snapshot.total_filled_qty)
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_plan_brief_obj.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
    expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_cxl_qty = \
        (((open_qty + expected_symbol_side_snapshot.total_filled_qty +
           expected_symbol_side_snapshot.total_cxled_qty) / 100) * expected_plan_limits.cancel_rate.max_cancel_rate) - \
        expected_symbol_side_snapshot.total_cxled_qty
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_plan_brief_obj.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
    sell_side_residual_qty = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty
    expected_plan_brief_obj.pair_buy_side_bartering_brief.indicative_consumable_residual = \
        expected_plan_limits.residual_restriction.max_residual - \
        ((expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty *
          get_px_in_usd(buy_last_barter_px)) - (sell_side_residual_qty * get_px_in_usd(sell_last_barter_px)))
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = date_time_for_cmp
    expected_plan_brief_obj.consumable_nett_filled_notional = (
            max_net_filled_notional - abs(expected_symbol_side_snapshot.total_fill_notional -
                                          expected_other_leg_symbol_side_snapshot.total_fill_notional))


def update_expected_plan_brief_for_sell(expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                         expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                         expected_other_leg_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                         expected_plan_limits: PlanLimits,
                                         expected_plan_brief_obj: PlanBriefBaseModel,
                                         date_time_for_cmp: DateTime, buy_last_barter_px, sell_last_barter_px,
                                         executor_http_client: StreetBookServiceHttpClient,
                                         fill_update_after_dod: bool = False,
                                         hedge_ratio: float = 1.0):
    max_net_filled_notional = expected_plan_limits.max_net_filled_notional

    symbol_side_snapshot_list = executor_http_client.get_all_symbol_side_snapshot_client()
    all_brk_cxled_qty = 0
    for symbol_side_snapshot in symbol_side_snapshot_list:
        if symbol_side_snapshot.side == Side.SELL:
            all_brk_cxled_qty += symbol_side_snapshot.total_cxled_qty

    if expected_chore_snapshot_obj.chore_status == ChoreStatusType.OE_UNACK:
        expected_plan_brief_obj.pair_sell_side_bartering_brief.open_qty += expected_chore_snapshot_obj.chore_brief.qty
        expected_plan_brief_obj.pair_sell_side_bartering_brief.open_notional += (
                expected_chore_snapshot_obj.chore_brief.qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
        expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_open_chores = 4
    elif expected_chore_snapshot_obj.chore_status == ChoreStatusType.OE_ACKED:
        expected_plan_brief_obj.pair_sell_side_bartering_brief.open_qty -= expected_chore_snapshot_obj.last_update_fill_qty
        expected_plan_brief_obj.pair_sell_side_bartering_brief.open_notional -= (
                expected_chore_snapshot_obj.last_update_fill_qty * get_px_in_usd(
                expected_chore_snapshot_obj.chore_brief.px))
        expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_open_chores = 4
    elif expected_chore_snapshot_obj.chore_status == ChoreStatusType.OE_DOD:
        # cxl chore
        if not fill_update_after_dod:
            unfilled_qty = expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty
            expected_plan_brief_obj.pair_sell_side_bartering_brief.open_qty -= unfilled_qty
            expected_plan_brief_obj.pair_sell_side_bartering_brief.open_notional -= (
                    unfilled_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
            expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty += (
                    expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty)
            expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_open_chores = 5
        else:
            expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty -= (
                expected_chore_snapshot_obj.last_update_fill_qty)
            expected_plan_brief_obj.pair_buy_side_bartering_brief.consumable_open_chores = 5
    open_qty = expected_plan_brief_obj.pair_sell_side_bartering_brief.open_qty
    open_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.open_notional
    expected_plan_brief_obj.pair_sell_side_bartering_brief.all_bkr_cxlled_qty = all_brk_cxled_qty
    expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_notional = \
        ((expected_plan_limits.max_single_leg_notional * hedge_ratio) -
         expected_symbol_side_snapshot.total_fill_notional - open_notional)
    expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_open_notional = \
        expected_plan_limits.max_open_single_leg_notional - open_notional
    total_security_size: int = \
        static_data.get_security_float_from_ticker(expected_chore_snapshot_obj.chore_brief.security.sec_id)
    expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_concentration = \
        (total_security_size / 100 * expected_plan_limits.max_concentration) - (
                open_qty + expected_symbol_side_snapshot.total_filled_qty)
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_plan_brief_obj.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
    expected_plan_brief_obj.pair_sell_side_bartering_brief.consumable_cxl_qty = \
        (((open_qty + expected_symbol_side_snapshot.total_filled_qty +
           expected_symbol_side_snapshot.total_cxled_qty) / 100) * expected_plan_limits.cancel_rate.max_cancel_rate) - \
        expected_symbol_side_snapshot.total_cxled_qty
    # covered in separate test, here we supress comparison as val may be not easy to predict in a long-running test
    expected_plan_brief_obj.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
    buy_side_residual_qty = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty
    expected_plan_brief_obj.pair_sell_side_bartering_brief.indicative_consumable_residual = \
        expected_plan_limits.residual_restriction.max_residual - \
        ((expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(sell_last_barter_px)) -
         (buy_side_residual_qty * get_px_in_usd(buy_last_barter_px)))
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = date_time_for_cmp
    expected_plan_brief_obj.consumable_nett_filled_notional = (
            max_net_filled_notional - abs(expected_symbol_side_snapshot.total_fill_notional -
                                          expected_other_leg_symbol_side_snapshot.total_fill_notional))


def check_plan_view_computes(plan_view_id: int, executor_http_client) -> None:
    start_time = DateTime.utcnow()
    for i in range(60):
        plan_view = photo_book_web_client.get_plan_view_client(plan_view_id)
        plan_status_obj = get_plan_status(executor_http_client)
        plan_limits_obj = get_plan_limits(executor_http_client)
        both_checks_passed = 0
        if plan_view.balance_notional == plan_status_obj.balance_notional:
            both_checks_passed += 1
        if plan_view.max_single_leg_notional == plan_limits_obj.max_open_single_leg_notional:
            both_checks_passed += 1
        if both_checks_passed == 2:
            delta_sec = (DateTime.utcnow() - start_time).total_seconds()
            print(f"RESULT: Took {delta_sec} seconds to match both balance_notional and max_single_leg_notional in "
                  f"plan view")
            break
        time.sleep(1)
    else:
        plan_view = photo_book_web_client.get_plan_view_client(plan_view_id)
        plan_status_obj = get_plan_status(executor_http_client)
        plan_limits_obj = get_plan_limits(executor_http_client)
        delta_sec = (DateTime.utcnow() - start_time).total_seconds()
        assert plan_view.balance_notional == plan_status_obj.balance_notional, \
            (f"Mismatched PlanView.balance_notional: expected: {plan_status_obj.balance_notional}, "
             f"received: {plan_view.balance_notional} in {delta_sec} seconds")
        assert plan_view.max_single_leg_notional == plan_limits_obj.max_open_single_leg_notional, \
            (f"Mismatched PlanView.max_single_leg_notional: expected: {plan_limits_obj.max_open_single_leg_notional}, "
             f"received: {plan_view.max_single_leg_notional} in {delta_sec} seconds")


def get_plan_status(executor_web_client):
    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        return plan_status_obj
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")


def get_plan_limits(executor_web_client):
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        return plan_limits_obj
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")


def check_placed_buy_chore_computes_before_all_sells(loop_count: int,
                                                     expected_chore_id: str, symbol: str,
                                                     buy_placed_chore_ledger: ChoreLedgerBaseModel,
                                                     expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                     expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                     other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                     pair_plan_: PairPlanBaseModel,
                                                     expected_plan_limits: PlanLimits,
                                                     expected_plan_status: PlanStatus,
                                                     expected_plan_brief_obj: PlanBriefBaseModel,
                                                     executor_web_client: StreetBookServiceHttpClient):
    """
    Checking resulted changes in ChoreLedger, ChoreSnapshot, SymbolSideSnapshot, PairPlan,
    PlanBrief and ContactStatus after chore is triggered
    """
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)
    assert buy_placed_chore_ledger in chore_ledger_obj_list, \
        f"Couldn't find {buy_placed_chore_ledger} in {chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, pair_plan_)

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_brief.chore_id = expected_chore_id
    expected_chore_snapshot_obj.chore_brief.px = buy_placed_chore_ledger.chore.px
    expected_chore_snapshot_obj.chore_brief.qty = buy_placed_chore_ledger.chore.qty
    expected_chore_snapshot_obj.chore_brief.chore_notional = (buy_placed_chore_ledger.chore.qty *
                                                              get_px_in_usd(buy_placed_chore_ledger.chore.px))
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_UNACK
    expected_chore_snapshot_obj.last_update_date_time = buy_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.create_date_time = buy_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.chore_brief.text.extend(buy_placed_chore_ledger.chore.text)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # updating below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    for chore_snapshot in chore_snapshot_list:
        if chore_snapshot == expected_chore_snapshot_obj:
            break
    else:
        assert False, f"Couldn't find expected_chore_snapshot {expected_chore_snapshot_obj} in {chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.chore_count = loop_count
    expected_symbol_side_snapshot.avg_px = (
        avg_of_new_val_sum_to_avg(expected_symbol_side_snapshot.avg_px,
                                  buy_placed_chore_ledger.chore.px,
                                  expected_symbol_side_snapshot.chore_count))
    expected_symbol_side_snapshot.total_qty += buy_placed_chore_ledger.chore.qty
    expected_symbol_side_snapshot.last_update_date_time = buy_placed_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.security.inst_type = buy_inst_type

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Mismatched SymbolSideSnapshot: {expected_symbol_side_snapshot} not found in {symbol_side_snapshot_list}"


    # Checking start_brief
    expected_plan_brief_obj.id = pair_plan_.id  # since plan's id is synced with plan_brief
    update_expected_plan_brief_for_buy(expected_chore_snapshot_obj,
                                        expected_symbol_side_snapshot,
                                        other_leg_expected_symbol_side_snapshot,
                                        expected_plan_limits, expected_plan_brief_obj,
                                        buy_placed_chore_ledger.chore_event_date_time,
                                        buy_last_barter_px, sell_last_barter_px, executor_web_client)

    print(f"@@@ fetching plan_brief for symbol: {symbol} at {DateTime.utcnow()}")
    plan_brief = executor_web_client.get_plan_brief_client(pair_plan_.id)

    plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
    plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
    plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
    # Since sell side of plan_brief is not updated till sell cycle
    expected_plan_brief_obj.pair_sell_side_bartering_brief = plan_brief.pair_sell_side_bartering_brief
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_buy_side_bartering_brief.security.inst_type = buy_inst_type
    assert expected_plan_brief_obj == plan_brief, \
        (f"Mismatched plan_brief in placed BUY chore check: "
         f"expected plan_brief {expected_plan_brief_obj}, received plan_brief {plan_brief}")

    # Checking Plan_Limits
    plan_limits_obj = get_plan_limits(executor_web_client)
    expected_plan_limits.id = plan_limits_obj.id
    expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
    expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num

    assert plan_limits_obj == expected_plan_limits, \
        f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"

    expected_plan_status.total_buy_qty += expected_chore_snapshot_obj.chore_brief.qty
    expected_plan_status.total_chore_qty += expected_chore_snapshot_obj.chore_brief.qty
    expected_plan_status.total_open_buy_qty = expected_chore_snapshot_obj.chore_brief.qty
    expected_plan_status.total_open_buy_notional = (expected_chore_snapshot_obj.chore_brief.qty *
                                                     get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_open_buy_px = (
        get_usd_to_local_px_or_notional(expected_plan_status.total_open_buy_notional) /
        expected_plan_status.total_open_buy_qty)
    expected_plan_status.total_open_exposure = expected_plan_status.total_open_buy_notional
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)
    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj = get_plan_status(executor_web_client)
    expected_plan_status.id = plan_status_obj.id
    expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
    expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
    expected_plan_status.average_premium = plan_status_obj.average_premium
    assert plan_status_obj == expected_plan_status, \
        f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"

    # checking plan_view
    check_plan_view_computes(pair_plan_.id, executor_web_client)


def check_placed_buy_chore_computes_after_sells(loop_count: int, expected_chore_id: str, symbol: str,
                                                buy_placed_chore_ledger: ChoreLedgerBaseModel,
                                                expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                expected_pair_plan: PairPlanBaseModel,
                                                expected_plan_limits: PlanLimits,
                                                expected_plan_status: PlanStatus,
                                                expected_plan_brief_obj: PlanBriefBaseModel,
                                                executor_web_client: StreetBookServiceHttpClient):
    """
    Checking resulted changes in ChoreLedger, ChoreSnapshot, SymbolSideSnapshot, PairPlan,
    PlanBrief and ContactStatus after chore is triggered
    """
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)
    assert buy_placed_chore_ledger in chore_ledger_obj_list, \
        f"Couldn't find {buy_placed_chore_ledger} in {chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, expected_pair_plan)

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_brief.chore_id = expected_chore_id
    expected_chore_snapshot_obj.chore_brief.px = buy_placed_chore_ledger.chore.px
    expected_chore_snapshot_obj.chore_brief.qty = buy_placed_chore_ledger.chore.qty
    expected_chore_snapshot_obj.chore_brief.chore_notional = (buy_placed_chore_ledger.chore.qty *
                                                              get_px_in_usd(buy_placed_chore_ledger.chore.px))
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_UNACK
    expected_chore_snapshot_obj.last_update_date_time = buy_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.create_date_time = buy_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.chore_brief.text.extend(buy_placed_chore_ledger.chore.text)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # updating below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    found_count = 0
    for chore_snapshot in chore_snapshot_list:
        if chore_snapshot == expected_chore_snapshot_obj:
            found_count += 1
    print(expected_chore_snapshot_obj, "in", chore_snapshot_list)
    assert found_count == 1, f"Couldn't find expected_chore_snapshot {expected_chore_snapshot_obj} in " \
                             f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.chore_count = loop_count
    expected_symbol_side_snapshot.avg_px = (
        avg_of_new_val_sum_to_avg(expected_symbol_side_snapshot.avg_px,
                                  buy_placed_chore_ledger.chore.px,
                                  expected_symbol_side_snapshot.chore_count))
    expected_symbol_side_snapshot.total_qty += buy_placed_chore_ledger.chore.qty
    expected_symbol_side_snapshot.last_update_date_time = buy_placed_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.security.inst_type = buy_inst_type

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"{expected_symbol_side_snapshot} not found in " \
                                                                       f"{symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_plan_brief_for_buy(expected_chore_snapshot_obj, expected_symbol_side_snapshot,
                                        other_leg_expected_symbol_side_snapshot,
                                        expected_plan_limits, expected_plan_brief_obj,
                                        buy_placed_chore_ledger.chore_event_date_time,
                                        buy_last_barter_px, sell_last_barter_px, executor_web_client,
                                        hedge_ratio=expected_pair_plan.pair_plan_params.hedge_ratio)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_buy_side_bartering_brief.security.inst_type = buy_inst_type
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, \
        f"Mismatched: {expected_plan_brief_obj} not found in {plan_brief_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num

        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking plan_status
    expected_plan_status.total_buy_qty += buy_placed_chore_ledger.chore.qty
    expected_plan_status.total_chore_qty = expected_plan_status.total_buy_qty + expected_plan_status.total_sell_qty
    expected_plan_status.total_open_buy_qty += buy_placed_chore_ledger.chore.qty
    expected_plan_status.total_open_buy_notional += (get_px_in_usd(buy_placed_chore_ledger.chore.px) *
                                                       buy_placed_chore_ledger.chore.qty)
    expected_plan_status.avg_open_buy_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_open_buy_notional) /
            expected_plan_status.total_open_buy_qty)
    expected_plan_status.total_open_exposure = expected_plan_status.total_open_buy_notional
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)
    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = expected_pair_plan.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def placed_buy_chore_ack_receive(expected_chore_ledger: ChoreLedgerBaseModel,
                                 expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                 executor_web_client: StreetBookServiceHttpClient):
    """Checking after chore's ACK status is received"""
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)

    assert expected_chore_ledger in chore_ledger_obj_list, f"Couldn't find {expected_chore_ledger} in list " \
                                                             f"{chore_ledger_obj_list}"

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_ACKED
    expected_chore_snapshot_obj.last_update_date_time = expected_chore_ledger.chore_event_date_time

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # updating below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None

    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"


def check_fill_receive_for_placed_buy_chore_before_sells(symbol: str,
                                                         buy_fill_ledger: DealsLedgerBaseModel,
                                                         expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                         expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                         other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                         expected_pair_plan: PairPlanBaseModel,
                                                         expected_plan_limits: PlanLimits,
                                                         expected_plan_status: PlanStatus,
                                                         expected_plan_brief_obj: PlanBriefBaseModel,
                                                         executor_web_client: StreetBookServiceHttpClient):
    """
    Checking resulted changes in ChoreLedger, ChoreSnapshot, SymbolSideSnapshot, PairPlan,
    PlanBrief and ContactStatus after fill is received
    """
    fill_ledger_obj_list = executor_web_client.get_all_deals_ledger_client(-100)
    assert buy_fill_ledger in fill_ledger_obj_list, f"Couldn't find {buy_fill_ledger} in {fill_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    expected_chore_snapshot_obj.filled_qty = buy_fill_ledger.fill_qty
    expected_chore_snapshot_obj.avg_fill_px = buy_fill_ledger.fill_px
    expected_chore_snapshot_obj.fill_notional = buy_fill_ledger.fill_qty * get_px_in_usd(buy_fill_ledger.fill_px)
    expected_chore_snapshot_obj.last_update_fill_qty = buy_fill_ledger.fill_qty
    expected_chore_snapshot_obj.last_update_fill_px = buy_fill_ledger.fill_px
    expected_chore_snapshot_obj.last_update_date_time = buy_fill_ledger.fill_date_time

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = buy_fill_ledger.fill_date_time
    expected_symbol_side_snapshot.total_filled_qty += buy_fill_ledger.fill_qty
    expected_symbol_side_snapshot.total_fill_notional += (buy_fill_ledger.fill_qty *
                                                          get_px_in_usd(buy_fill_ledger.fill_px))
    expected_symbol_side_snapshot.avg_fill_px = \
        (get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_fill_notional) /
         expected_symbol_side_snapshot.total_filled_qty)
    expected_symbol_side_snapshot.last_update_fill_qty = buy_fill_ledger.fill_qty
    expected_symbol_side_snapshot.last_update_fill_px = buy_fill_ledger.fill_px

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_plan_brief_for_buy(expected_chore_snapshot_obj,
                                        expected_symbol_side_snapshot,
                                        other_leg_expected_symbol_side_snapshot,
                                        expected_plan_limits, expected_plan_brief_obj,
                                        buy_fill_ledger.fill_date_time,
                                        buy_last_barter_px, sell_last_barter_px, executor_web_client)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, f"Couldn't find {expected_plan_brief_obj} in " \
                                                         f"{plan_brief_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    expected_plan_status.total_open_buy_qty -= buy_fill_ledger.fill_qty
    expected_plan_status.total_open_buy_notional -= (buy_fill_ledger.fill_qty *
                                                      get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_open_buy_px = (
        get_usd_to_local_px_or_notional(expected_plan_status.total_open_buy_notional) /
        expected_plan_status.total_open_buy_qty)
    expected_plan_status.total_open_exposure = expected_plan_status.total_open_buy_notional
    expected_plan_status.total_fill_buy_qty += buy_fill_ledger.fill_qty
    expected_plan_status.total_fill_buy_notional += (
        get_px_in_usd(buy_fill_ledger.fill_px) * buy_fill_ledger.fill_qty)
    expected_plan_status.avg_fill_buy_px = (
        (get_usd_to_local_px_or_notional(expected_plan_status.total_fill_buy_notional) /
         expected_plan_status.total_fill_buy_qty))
    expected_plan_status.total_fill_exposure = (expected_plan_status.total_fill_buy_notional -
                                                 expected_plan_status.total_fill_sell_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = plan_status_obj.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_cxl_receive_for_placed_buy_chore_before_sells(symbol: str,
                                                        buy_cxl_chore_ledger: ChoreLedgerBaseModel,
                                                        expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                        other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                        expected_pair_plan: PairPlanBaseModel,
                                                        expected_plan_limits: PlanLimits,
                                                        expected_plan_status: PlanStatus,
                                                        expected_plan_brief_obj: PlanBriefBaseModel,
                                                        executor_web_client: StreetBookServiceHttpClient,):
    """
    Checking resulted changes in ChoreLedger, ChoreSnapshot, SymbolSideSnapshot, PairPlan,
    PlanBrief and ContactStatus after fill is received
    """
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)
    assert buy_cxl_chore_ledger in chore_ledger_obj_list, f"Couldn't find {buy_cxl_chore_ledger} in list " \
                                                            f"{chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    unfilled_qty = expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_DOD
    expected_chore_snapshot_obj.last_update_date_time = buy_cxl_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.cxled_qty = unfilled_qty
    expected_chore_snapshot_obj.cxled_notional = (unfilled_qty *
                                                  get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_chore_snapshot_obj.avg_cxled_px = (
        get_usd_to_local_px_or_notional(expected_chore_snapshot_obj.cxled_notional) /
        expected_chore_snapshot_obj.cxled_qty)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.text = []
        chore_snapshot.chore_brief.user_data = None
    expected_chore_snapshot_obj.chore_brief.text = []
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = buy_cxl_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.total_cxled_qty += unfilled_qty
    expected_symbol_side_snapshot.total_cxled_notional += (
            unfilled_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_symbol_side_snapshot.avg_cxled_px = (
        get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_cxled_notional) /
        expected_symbol_side_snapshot.total_cxled_qty)

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_plan_brief_for_buy(expected_chore_snapshot_obj,
                                        expected_symbol_side_snapshot,
                                        other_leg_expected_symbol_side_snapshot,
                                        expected_plan_limits, expected_plan_brief_obj,
                                        buy_cxl_chore_ledger.chore_event_date_time,
                                        buy_last_barter_px, sell_last_barter_px, executor_web_client)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, f"Couldn't find {expected_plan_brief_obj} in " \
                                                         f"{plan_brief_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    expected_plan_status.total_cxl_buy_qty += unfilled_qty
    expected_plan_status.total_cxl_buy_notional += (unfilled_qty *
                                                     get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_cxl_buy_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_cxl_buy_notional) /
            expected_plan_status.total_cxl_buy_qty)
    expected_plan_status.total_open_buy_qty -= unfilled_qty
    expected_plan_status.total_open_buy_notional -= (
        get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px) * unfilled_qty)
    if expected_plan_status.total_open_buy_qty != 0:
        expected_plan_status.avg_open_buy_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_open_buy_notional) /
            expected_plan_status.total_open_buy_qty)
    else:
        expected_plan_status.avg_open_buy_px = 0
    expected_plan_status.total_open_exposure = expected_plan_status.total_open_buy_notional
    expected_plan_status.total_cxl_exposure = (expected_plan_status.total_cxl_buy_notional -
                                                expected_plan_status.total_cxl_sell_notional)
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)

    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = expected_pair_plan.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_cxl_receive_for_placed_sell_chore_before_buy(symbol: str,
                                                       sell_cxl_chore_ledger: ChoreLedgerBaseModel,
                                                       expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                       expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                       other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                       expected_pair_plan: PairPlanBaseModel,
                                                       expected_plan_limits: PlanLimits,
                                                       expected_plan_status: PlanStatus,
                                                       expected_plan_brief_obj: PlanBriefBaseModel,
                                                       executor_web_client: StreetBookServiceHttpClient):
    """
    Checking resulted changes in ChoreLedger, ChoreSnapshot, SymbolSideSnapshot, PairPlan,
    PlanBrief and ContactStatus after fill is received
    """
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)
    assert sell_cxl_chore_ledger in chore_ledger_obj_list, f"Couldn't find {sell_cxl_chore_ledger} in list " \
                                                            f"{chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    unfilled_qty = expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_DOD
    expected_chore_snapshot_obj.last_update_date_time = sell_cxl_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.cxled_qty = unfilled_qty
    expected_chore_snapshot_obj.cxled_notional = (unfilled_qty *
                                                  get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_chore_snapshot_obj.avg_cxled_px = (
        get_usd_to_local_px_or_notional(expected_chore_snapshot_obj.cxled_notional) /
        expected_chore_snapshot_obj.cxled_qty)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.text = []
        chore_snapshot.chore_brief.user_data = None
    expected_chore_snapshot_obj.chore_brief.text = []
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = sell_cxl_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.total_cxled_qty += unfilled_qty
    expected_symbol_side_snapshot.total_cxled_notional += (
            unfilled_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_symbol_side_snapshot.avg_cxled_px = (
        get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_cxled_notional) /
        expected_symbol_side_snapshot.total_cxled_qty)

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_plan_brief_for_sell(expected_chore_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         other_leg_expected_symbol_side_snapshot,
                                         expected_plan_limits, expected_plan_brief_obj,
                                         sell_cxl_chore_ledger.chore_event_date_time,
                                         buy_last_barter_px, sell_last_barter_px, executor_web_client)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, f"Couldn't find {expected_plan_brief_obj} in " \
                                                         f"{plan_brief_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    expected_plan_status.total_cxl_sell_qty += unfilled_qty
    expected_plan_status.total_cxl_sell_notional += (unfilled_qty *
                                                      get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_cxl_sell_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_cxl_sell_notional) /
            expected_plan_status.total_cxl_sell_qty)
    expected_plan_status.total_open_sell_qty -= unfilled_qty
    expected_plan_status.total_open_sell_notional -= (
        get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px) * unfilled_qty)
    if expected_plan_status.total_open_sell_qty != 0:
        expected_plan_status.avg_open_sell_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_open_sell_notional) /
            expected_plan_status.total_open_sell_qty)
    else:
        expected_plan_status.avg_open_sell_px = 0
    expected_plan_status.total_open_exposure = 0
    expected_plan_status.total_cxl_exposure = (expected_plan_status.total_cxl_buy_notional -
                                                expected_plan_status.total_cxl_sell_notional)
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)

    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = expected_pair_plan.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_fill_receive_for_placed_buy_chore_after_all_sells(loop_count: int, expected_chore_id: str, symbol: str,
                                                            buy_fill_ledger: DealsLedgerBaseModel,
                                                            expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                            expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                            other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                            expected_pair_plan: PairPlanBaseModel,
                                                            expected_plan_limits: PlanLimits,
                                                            expected_plan_status: PlanStatus,
                                                            expected_plan_brief_obj: PlanBriefBaseModel,
                                                            executor_web_client: StreetBookServiceHttpClient):
    """
    Checking resulted changes in ChoreLedger, ChoreSnapshot, SymbolSideSnapshot, PairPlan,
    PlanBrief and ContactStatus after fill is received
    """
    fill_ledger_obj_list = executor_web_client.get_all_deals_ledger_client(-100)
    assert buy_fill_ledger in fill_ledger_obj_list, f"Couldn't find {buy_fill_ledger} in {fill_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_brief.chore_id = expected_chore_id
    expected_chore_snapshot_obj.filled_qty += buy_fill_ledger.fill_qty
    expected_chore_snapshot_obj.fill_notional = buy_fill_ledger.fill_qty * get_px_in_usd(buy_fill_ledger.fill_px)
    expected_chore_snapshot_obj.avg_fill_px = (
            get_usd_to_local_px_or_notional(expected_chore_snapshot_obj.fill_notional) /
            expected_chore_snapshot_obj.filled_qty)
    expected_chore_snapshot_obj.last_update_fill_qty = buy_fill_ledger.fill_qty
    expected_chore_snapshot_obj.last_update_fill_px = buy_fill_ledger.fill_px
    expected_chore_snapshot_obj.last_update_date_time = buy_fill_ledger.fill_date_time

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = expected_chore_snapshot_obj.last_update_date_time
    expected_symbol_side_snapshot.chore_count = loop_count
    expected_symbol_side_snapshot.total_filled_qty += buy_fill_ledger.fill_qty
    expected_symbol_side_snapshot.total_fill_notional += (buy_fill_ledger.fill_qty *
                                                          get_px_in_usd(buy_fill_ledger.fill_px))
    expected_symbol_side_snapshot.avg_fill_px = (
            get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_fill_notional) /
            expected_symbol_side_snapshot.total_filled_qty)
    expected_symbol_side_snapshot.last_update_fill_qty = buy_fill_ledger.fill_qty
    expected_symbol_side_snapshot.last_update_fill_px = buy_fill_ledger.fill_px

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_plan_brief_for_buy(expected_chore_snapshot_obj, expected_symbol_side_snapshot,
                                        other_leg_expected_symbol_side_snapshot,
                                        expected_plan_limits, expected_plan_brief_obj,
                                        buy_fill_ledger.fill_date_time,
                                        buy_last_barter_px, sell_last_barter_px, executor_web_client,
                                        hedge_ratio=expected_pair_plan.pair_plan_params.hedge_ratio)
    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = None
    for plan_brief in plan_brief_list:
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, \
        f"Mismatched: Couldn't find {expected_plan_brief_obj} in any plan_brief in {plan_brief_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking start_status
    expected_plan_status.total_open_buy_qty -= buy_fill_ledger.fill_qty
    expected_plan_status.total_open_buy_notional -= (buy_fill_ledger.fill_qty *
                                                       get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_open_buy_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_open_buy_notional) /
            expected_plan_status.total_open_buy_qty)
    expected_plan_status.total_open_exposure = expected_plan_status.total_open_buy_notional
    expected_plan_status.total_fill_buy_qty += buy_fill_ledger.fill_qty
    expected_plan_status.total_fill_buy_notional += (buy_fill_ledger.fill_qty *
                                                       get_px_in_usd(buy_fill_ledger.fill_px))
    expected_plan_status.avg_fill_buy_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_fill_buy_notional) /
            expected_plan_status.total_fill_buy_qty)
    expected_plan_status.total_fill_exposure = (expected_plan_status.total_fill_buy_notional -
                                                 expected_plan_status.total_fill_sell_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_placed_sell_chore_computes_before_buys(loop_count: int, expected_chore_id: str,
                                                 symbol: str, sell_placed_chore_ledger: ChoreLedgerBaseModel,
                                                 expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                 expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                 other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                 pair_plan_: PairPlanBaseModel,
                                                 expected_plan_limits: PlanLimits,
                                                 expected_plan_status: PlanStatus,
                                                 expected_plan_brief_obj: PlanBriefBaseModel,
                                                 executor_web_client: StreetBookServiceHttpClient):
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)

    assert sell_placed_chore_ledger in chore_ledger_obj_list, f"Couldn't find {sell_placed_chore_ledger} in " \
                                                                f"{chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
    sell_inst_type: InstrumentType = InstrumentType.EQT if (
            pair_plan_.pair_plan_params.plan_leg1.side == Side.BUY) else InstrumentType.CB

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_brief.chore_id = expected_chore_id
    expected_chore_snapshot_obj.chore_brief.px = sell_placed_chore_ledger.chore.px
    expected_chore_snapshot_obj.chore_brief.qty = sell_placed_chore_ledger.chore.qty
    expected_chore_snapshot_obj.chore_brief.chore_notional = (sell_placed_chore_ledger.chore.qty *
                                                              get_px_in_usd(sell_placed_chore_ledger.chore.px))
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_UNACK
    expected_chore_snapshot_obj.last_update_date_time = sell_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.create_date_time = sell_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.chore_brief.text.extend(sell_placed_chore_ledger.chore.text)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # updating below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.chore_count = loop_count
    expected_symbol_side_snapshot.avg_px = (
        avg_of_new_val_sum_to_avg(expected_symbol_side_snapshot.avg_px,
                                  sell_placed_chore_ledger.chore.px,
                                  expected_symbol_side_snapshot.chore_count))
    expected_symbol_side_snapshot.total_qty += sell_placed_chore_ledger.chore.qty
    expected_symbol_side_snapshot.last_update_date_time = sell_placed_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.security.inst_type = sell_inst_type

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"Couldn't find {expected_symbol_side_snapshot} "

    # Checking start_brief
    expected_plan_brief_obj.id = pair_plan_.id  # since plan's id is synced with plan_brief
    update_expected_plan_brief_for_sell(expected_chore_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         other_leg_expected_symbol_side_snapshot,
                                         expected_plan_limits, expected_plan_brief_obj,
                                         sell_placed_chore_ledger.chore_event_date_time,
                                         buy_last_barter_px, sell_last_barter_px, executor_web_client)

    print(f"@@@ fetching plan_brief for symbol: {symbol} at {DateTime.utcnow()}")
    plan_brief = executor_web_client.get_plan_brief_client(pair_plan_.id)

    plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
    plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
    plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    # Since sell side of plan_brief is not updated till sell cycle
    expected_plan_brief_obj.pair_buy_side_bartering_brief = plan_brief.pair_buy_side_bartering_brief
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_sell_side_bartering_brief.security.inst_type = sell_inst_type
    assert expected_plan_brief_obj == plan_brief, \
        f"Mismatched: expected plan_brief {expected_plan_brief_obj}, received plan_brief {plan_brief}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")
    expected_plan_status.total_sell_qty += expected_chore_snapshot_obj.chore_brief.qty
    expected_plan_status.total_chore_qty += expected_chore_snapshot_obj.chore_brief.qty
    expected_plan_status.total_open_sell_qty = expected_chore_snapshot_obj.chore_brief.qty
    expected_plan_status.total_open_sell_notional = (expected_chore_snapshot_obj.chore_brief.qty *
                                                      get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_open_sell_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_open_sell_notional) /
            expected_plan_status.total_open_sell_qty)
    expected_plan_status.total_open_exposure = - expected_plan_status.total_open_sell_notional
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)
    security = expected_plan_brief_obj.pair_sell_side_bartering_brief.security if \
        sell_residual_notional > buy_residual_notional else \
        expected_plan_brief_obj.pair_buy_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = plan_status_obj.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(pair_plan_.id, executor_web_client)


def check_placed_sell_chore_computes_after_all_buys(loop_count: int, expected_chore_id: str,
                                                    symbol: str, sell_placed_chore_ledger: ChoreLedgerBaseModel,
                                                    expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                                    expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                    other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                                    expected_pair_plan: PairPlanBaseModel,
                                                    expected_plan_limits: PlanLimits,
                                                    expected_plan_status: PlanStatus,
                                                    expected_plan_brief_obj: PlanBriefBaseModel,
                                                    executor_web_client: StreetBookServiceHttpClient):
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)

    assert sell_placed_chore_ledger in chore_ledger_obj_list, f"Couldn't find {sell_placed_chore_ledger} in " \
                                                                f"{chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()
    sell_inst_type: InstrumentType = InstrumentType.EQT if (
            expected_pair_plan.pair_plan_params.plan_leg1.side == Side.BUY) else InstrumentType.CB

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_brief.chore_id = expected_chore_id
    expected_chore_snapshot_obj.chore_brief.px = sell_placed_chore_ledger.chore.px
    expected_chore_snapshot_obj.chore_brief.qty = sell_placed_chore_ledger.chore.qty
    expected_chore_snapshot_obj.chore_brief.chore_notional = (sell_placed_chore_ledger.chore.qty *
                                                              get_px_in_usd(sell_placed_chore_ledger.chore.px))
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_UNACK
    expected_chore_snapshot_obj.last_update_date_time = sell_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.create_date_time = sell_placed_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.chore_brief.text.extend(sell_placed_chore_ledger.chore.text)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # updating below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.chore_count = loop_count
    expected_symbol_side_snapshot.avg_px = (
        avg_of_new_val_sum_to_avg(expected_symbol_side_snapshot.avg_px,
                                  sell_placed_chore_ledger.chore.px,
                                  expected_symbol_side_snapshot.chore_count))
    expected_symbol_side_snapshot.total_qty += sell_placed_chore_ledger.chore.qty
    expected_symbol_side_snapshot.last_update_date_time = sell_placed_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.security.inst_type = sell_inst_type

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"Couldn't find {expected_symbol_side_snapshot} "

    # Checking start_brief
    update_expected_plan_brief_for_sell(expected_chore_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         other_leg_expected_symbol_side_snapshot,
                                         expected_plan_limits, expected_plan_brief_obj,
                                         sell_placed_chore_ledger.chore_event_date_time,
                                         buy_last_barter_px, sell_last_barter_px, executor_web_client,
                                         hedge_ratio=expected_pair_plan.pair_plan_params.hedge_ratio)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_sell_side_bartering_brief.security.inst_type = sell_inst_type
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, \
        f"Mismatched: {expected_plan_brief_obj} not found in {plan_brief_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking plan_status
    expected_plan_status.total_sell_qty += sell_placed_chore_ledger.chore.qty
    expected_plan_status.total_chore_qty = expected_plan_status.total_buy_qty + expected_plan_status.total_sell_qty
    expected_plan_status.total_open_sell_qty += sell_placed_chore_ledger.chore.qty
    expected_plan_status.total_open_sell_notional += (get_px_in_usd(sell_placed_chore_ledger.chore.px) *
                                                       sell_placed_chore_ledger.chore.qty)
    expected_plan_status.avg_open_sell_px = (
        get_usd_to_local_px_or_notional(expected_plan_status.total_open_sell_notional) /
        expected_plan_status.total_open_sell_qty)
    expected_plan_status.total_open_exposure = - expected_plan_status.total_open_sell_notional
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)
    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                 residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = expected_pair_plan.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def placed_sell_chore_ack_receive(expected_chore_ledger: ChoreLedgerBaseModel,
                                  expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
                                  executor_web_client: StreetBookServiceHttpClient):
    """Checking after chore's ACK status is received"""
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)

    assert expected_chore_ledger in chore_ledger_obj_list, f"Couldn't find {expected_chore_ledger} in " \
                                                             f"{chore_ledger_obj_list}"

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_ACKED
    expected_chore_snapshot_obj.last_update_date_time = expected_chore_ledger.chore_event_date_time

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # updating below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None

    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"


def check_fill_receive_for_placed_sell_chore_before_buys(
        symbol: str, sell_fill_ledger: DealsLedgerBaseModel, expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        expected_pair_plan: PairPlanBaseModel,
        expected_plan_limits: PlanLimits, expected_plan_status: PlanStatus,
        expected_plan_brief_obj: PlanBriefBaseModel,
        executor_web_client: StreetBookServiceHttpClient):
    fill_ledger_obj_list = executor_web_client.get_all_deals_ledger_client(-100)
    assert sell_fill_ledger in fill_ledger_obj_list, f"Couldn't find {sell_fill_ledger} in {fill_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    expected_chore_snapshot_obj.filled_qty = sell_fill_ledger.fill_qty
    expected_chore_snapshot_obj.avg_fill_px = sell_fill_ledger.fill_px
    expected_chore_snapshot_obj.fill_notional = sell_fill_ledger.fill_qty * get_px_in_usd(sell_fill_ledger.fill_px)
    expected_chore_snapshot_obj.last_update_fill_qty = sell_fill_ledger.fill_qty
    expected_chore_snapshot_obj.last_update_fill_px = sell_fill_ledger.fill_px
    expected_chore_snapshot_obj.last_update_date_time = sell_fill_ledger.fill_date_time

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = sell_fill_ledger.fill_date_time
    expected_symbol_side_snapshot.total_filled_qty += sell_fill_ledger.fill_qty
    expected_symbol_side_snapshot.total_fill_notional += (sell_fill_ledger.fill_qty *
                                                          get_px_in_usd(sell_fill_ledger.fill_px))
    expected_symbol_side_snapshot.avg_fill_px = \
        (get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_fill_notional) /
         expected_symbol_side_snapshot.total_filled_qty)
    expected_symbol_side_snapshot.last_update_fill_qty = sell_fill_ledger.fill_qty
    expected_symbol_side_snapshot.last_update_fill_px = sell_fill_ledger.fill_px

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_plan_brief_for_sell(expected_chore_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         other_leg_expected_symbol_side_snapshot,
                                         expected_plan_limits, expected_plan_brief_obj,
                                         sell_fill_ledger.fill_date_time,
                                         buy_last_barter_px, sell_last_barter_px, executor_web_client)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, f"Couldn't find {expected_plan_brief_obj} in " \
                                                         f"{plan_brief_list}"
    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking plan_status
    expected_plan_status.total_open_sell_qty -= sell_fill_ledger.fill_qty
    expected_plan_status.total_open_sell_notional -= (sell_fill_ledger.fill_qty *
                                                       get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_open_sell_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_open_sell_notional) /
            expected_plan_status.total_open_sell_qty)
    expected_plan_status.total_open_exposure = - expected_plan_status.total_open_sell_notional
    expected_plan_status.total_fill_sell_qty += sell_fill_ledger.fill_qty
    expected_plan_status.total_fill_sell_notional += (
            get_px_in_usd(sell_fill_ledger.fill_px) * sell_fill_ledger.fill_qty)
    expected_plan_status.avg_fill_sell_px = (
        (get_usd_to_local_px_or_notional(expected_plan_status.total_fill_sell_notional) /
         expected_plan_status.total_fill_sell_qty))
    expected_plan_status.total_fill_exposure = (expected_plan_status.total_fill_buy_notional -
                                                 expected_plan_status.total_fill_sell_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = plan_status_obj.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_fill_receive_for_placed_sell_chore_after_all_buys(
        loop_count: int, expected_chore_id: str,
        symbol: str, sell_fill_ledger: DealsLedgerBaseModel, expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        expected_pair_plan: PairPlanBaseModel,
        expected_plan_limits: PlanLimits, expected_plan_status: PlanStatus,
        expected_plan_brief_obj: PlanBriefBaseModel, executor_web_client: StreetBookServiceHttpClient):
    fill_ledger_obj_list = executor_web_client.get_all_deals_ledger_client(-100)
    assert sell_fill_ledger in fill_ledger_obj_list, f"Couldn't find {sell_fill_ledger} in {fill_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    expected_chore_snapshot_obj.chore_brief.chore_id = expected_chore_id
    expected_chore_snapshot_obj.filled_qty += sell_fill_ledger.fill_qty
    expected_chore_snapshot_obj.fill_notional = sell_fill_ledger.fill_qty * get_px_in_usd(sell_fill_ledger.fill_px)
    expected_chore_snapshot_obj.avg_fill_px = (
            get_usd_to_local_px_or_notional(expected_chore_snapshot_obj.fill_notional) /
            expected_chore_snapshot_obj.filled_qty)
    expected_chore_snapshot_obj.last_update_fill_qty = sell_fill_ledger.fill_qty
    expected_chore_snapshot_obj.last_update_fill_px = sell_fill_ledger.fill_px
    expected_chore_snapshot_obj.last_update_date_time = sell_fill_ledger.fill_date_time

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.user_data = None
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = expected_chore_snapshot_obj.last_update_date_time
    expected_symbol_side_snapshot.chore_count = loop_count
    expected_symbol_side_snapshot.total_filled_qty += sell_fill_ledger.fill_qty
    expected_symbol_side_snapshot.total_fill_notional += (sell_fill_ledger.fill_qty *
                                                          get_px_in_usd(sell_fill_ledger.fill_px))
    expected_symbol_side_snapshot.avg_fill_px = (
        get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_fill_notional) /
        expected_symbol_side_snapshot.total_filled_qty)
    expected_symbol_side_snapshot.last_update_fill_qty = sell_fill_ledger.fill_qty
    expected_symbol_side_snapshot.last_update_fill_px = sell_fill_ledger.fill_px

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking start_brief
    update_expected_plan_brief_for_sell(expected_chore_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         other_leg_expected_symbol_side_snapshot,
                                         expected_plan_limits, expected_plan_brief_obj,
                                         sell_fill_ledger.fill_date_time,
                                         buy_last_barter_px, sell_last_barter_px, executor_web_client,
                                         hedge_ratio=expected_pair_plan.pair_plan_params.hedge_ratio)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = None
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        # plan_brief.id = None
        # Since buy side of plan_brief is already checked
        # plan_brief.pair_buy_side_bartering_brief = expected_plan_brief_obj.pair_buy_side_bartering_brief
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None
    assert expected_plan_brief_obj in plan_brief_list, \
        f"Mismatched: Couldn't find {expected_plan_brief_obj} in any plan_brief in {plan_brief_list}"

    # Checking start_status
    expected_plan_status.total_open_sell_qty -= sell_fill_ledger.fill_qty
    expected_plan_status.total_open_sell_notional -= (sell_fill_ledger.fill_qty *
                                                       get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_open_sell_px = (
        get_usd_to_local_px_or_notional(expected_plan_status.total_open_sell_notional) /
        expected_plan_status.total_open_sell_qty)
    expected_plan_status.total_open_exposure = - expected_plan_status.total_open_sell_notional
    expected_plan_status.total_fill_sell_qty += sell_fill_ledger.fill_qty
    expected_plan_status.total_fill_sell_notional += (sell_fill_ledger.fill_qty *
                                                       get_px_in_usd(sell_fill_ledger.fill_px))
    expected_plan_status.avg_fill_sell_px = (
        get_usd_to_local_px_or_notional(expected_plan_status.total_fill_sell_notional) /
        expected_plan_status.total_fill_sell_qty)
    expected_plan_status.total_fill_exposure = (expected_plan_status.total_fill_buy_notional -
                                                 expected_plan_status.total_fill_sell_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_cxl_receive_for_placed_sell_chore_after_all_buys(
        symbol: str, sell_cxl_chore_ledger: ChoreLedgerBaseModel, expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        expected_pair_plan: PairPlanBaseModel,
        expected_plan_limits: PlanLimits, expected_plan_status: PlanStatus,
        expected_plan_brief_obj: PlanBriefBaseModel, executor_web_client: StreetBookServiceHttpClient):
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)
    assert sell_cxl_chore_ledger in chore_ledger_obj_list, f"Couldn't find {sell_cxl_chore_ledger} in list " \
                                                             f"{chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    unfilled_qty = expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_DOD
    expected_chore_snapshot_obj.last_update_date_time = sell_cxl_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.cxled_qty = unfilled_qty
    expected_chore_snapshot_obj.cxled_notional = (unfilled_qty *
                                                  get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_chore_snapshot_obj.avg_cxled_px = (
            get_usd_to_local_px_or_notional(expected_chore_snapshot_obj.cxled_notional) /
            expected_chore_snapshot_obj.cxled_qty)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.text = []
        chore_snapshot.chore_brief.user_data = None
    expected_chore_snapshot_obj.chore_brief.text = []
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"
    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = expected_chore_snapshot_obj.last_update_date_time
    expected_symbol_side_snapshot.last_update_date_time = sell_cxl_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.total_cxled_qty += unfilled_qty
    expected_symbol_side_snapshot.total_cxled_notional += (
            unfilled_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_symbol_side_snapshot.avg_cxled_px = (
        get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_cxled_notional) /
        expected_symbol_side_snapshot.total_cxled_qty)

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking start_brief
    update_expected_plan_brief_for_sell(expected_chore_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         other_leg_expected_symbol_side_snapshot,
                                         expected_plan_limits, expected_plan_brief_obj,
                                         sell_cxl_chore_ledger.chore_event_date_time,
                                         buy_last_barter_px, sell_last_barter_px, executor_web_client,
                                         hedge_ratio=expected_pair_plan.pair_plan_params.hedge_ratio)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    expected_plan_brief_obj.pair_sell_side_bartering_brief.last_update_date_time = None
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        # plan_brief.id = None
        # Since buy side of plan_brief is already checked
        # plan_brief.pair_buy_side_bartering_brief = expected_plan_brief_obj.pair_buy_side_bartering_brief
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None

    assert expected_plan_brief_obj in plan_brief_list, \
        f"Mismatched: Couldn't find {expected_plan_brief_obj} in any plan_brief in {plan_brief_list}"

    # Checking plan_status
    expected_plan_status.total_cxl_sell_qty += unfilled_qty
    expected_plan_status.total_cxl_sell_notional += (unfilled_qty *
                                                      get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_cxl_sell_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_cxl_sell_notional) /
            expected_plan_status.total_cxl_sell_qty)
    expected_plan_status.total_open_sell_qty -= unfilled_qty
    expected_plan_status.total_open_sell_notional -= (
            get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px) * unfilled_qty)
    if expected_plan_status.total_open_sell_qty != 0:
        expected_plan_status.avg_open_sell_px = (
                get_usd_to_local_px_or_notional(expected_plan_status.total_open_sell_notional) /
                expected_plan_status.total_open_sell_qty)
    else:
        expected_plan_status.avg_open_sell_px = 0
    expected_plan_status.total_open_exposure = - expected_plan_status.total_open_sell_notional
    expected_plan_status.total_cxl_exposure = (expected_plan_status.total_cxl_buy_notional -
                                                expected_plan_status.total_cxl_sell_notional)
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)

    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = expected_pair_plan.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


def check_cxl_receive_for_placed_buy_chore_after_all_sells(
        symbol: str, buy_cxl_chore_ledger: ChoreLedgerBaseModel, expected_chore_snapshot_obj: ChoreSnapshotBaseModel,
        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        other_leg_expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
        expected_pair_plan: PairPlanBaseModel,
        expected_plan_limits: PlanLimits, expected_plan_status: PlanStatus,
        expected_plan_brief_obj: PlanBriefBaseModel, executor_web_client: StreetBookServiceHttpClient):
    chore_ledger_obj_list = executor_web_client.get_all_chore_ledger_client(-100)
    assert buy_cxl_chore_ledger in chore_ledger_obj_list, f"Couldn't find {buy_cxl_chore_ledger} in list " \
                                                            f"{chore_ledger_obj_list}"

    buy_last_barter_px, sell_last_barter_px = get_both_side_last_barter_px()

    # Checking chore_snapshot
    unfilled_qty = expected_chore_snapshot_obj.chore_brief.qty - expected_chore_snapshot_obj.filled_qty
    expected_chore_snapshot_obj.chore_status = ChoreStatusType.OE_DOD
    expected_chore_snapshot_obj.last_update_date_time = buy_cxl_chore_ledger.chore_event_date_time
    expected_chore_snapshot_obj.cxled_qty = unfilled_qty
    expected_chore_snapshot_obj.cxled_notional = (unfilled_qty *
                                                  get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_chore_snapshot_obj.avg_cxled_px = (
            get_usd_to_local_px_or_notional(expected_chore_snapshot_obj.cxled_notional) /
            expected_chore_snapshot_obj.cxled_qty)

    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    # removing below field from received_chore_snapshot_list for comparison
    for chore_snapshot in chore_snapshot_list:
        chore_snapshot.id = None
        chore_snapshot.chore_brief.text = []
        chore_snapshot.chore_brief.user_data = None
    expected_chore_snapshot_obj.chore_brief.text = []
    assert expected_chore_snapshot_obj in chore_snapshot_list, f"Couldn't find {expected_chore_snapshot_obj} in " \
                                                               f"{chore_snapshot_list}"
    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.last_update_date_time = expected_chore_snapshot_obj.last_update_date_time
    expected_symbol_side_snapshot.last_update_date_time = buy_cxl_chore_ledger.chore_event_date_time
    expected_symbol_side_snapshot.total_cxled_qty += unfilled_qty
    expected_symbol_side_snapshot.total_cxled_notional += (
            unfilled_qty * get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_symbol_side_snapshot.avg_cxled_px = (
        get_usd_to_local_px_or_notional(expected_symbol_side_snapshot.total_cxled_notional) /
        expected_symbol_side_snapshot.total_cxled_qty)

    symbol_side_snapshot_list = executor_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, \
        f"Couldn't find {expected_symbol_side_snapshot} in {symbol_side_snapshot_list}"

    # Checking Plan_Limits
    plan_limits_obj_list = executor_web_client.get_all_plan_limits_client()
    if len(plan_limits_obj_list) == 1:
        plan_limits_obj = plan_limits_obj_list[0]
        expected_plan_limits.id = plan_limits_obj.id
        expected_plan_limits.eligible_brokers = plan_limits_obj.eligible_brokers
        expected_plan_limits.plan_limits_update_seq_num = plan_limits_obj.plan_limits_update_seq_num
        assert plan_limits_obj == expected_plan_limits, \
            f"Mismatched PlanLimits: expected: {expected_plan_limits}, received: {plan_limits_obj}"
    else:
        assert False, (f"PlanLimits' length must be exactly 1, found {len(plan_limits_obj_list)}, "
                       f"plan_limits_list: {plan_limits_obj_list}")

    # Checking start_brief
    update_expected_plan_brief_for_buy(expected_chore_snapshot_obj,
                                        expected_symbol_side_snapshot,
                                        other_leg_expected_symbol_side_snapshot,
                                        expected_plan_limits, expected_plan_brief_obj,
                                        buy_cxl_chore_ledger.chore_event_date_time,
                                        buy_last_barter_px, sell_last_barter_px, executor_web_client,
                                        hedge_ratio=expected_pair_plan.pair_plan_params.hedge_ratio)

    plan_brief_list = executor_web_client.get_plan_brief_from_symbol_query_client(symbol)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.last_update_date_time = None
    # removing id field from received obj list for comparison
    for plan_brief in plan_brief_list:
        plan_brief.pair_buy_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_buy_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_buy_side_bartering_brief.last_update_date_time = None
        plan_brief.pair_sell_side_bartering_brief.indicative_consumable_participation_qty = None
        plan_brief.pair_sell_side_bartering_brief.participation_period_chore_qty_sum = None
        plan_brief.pair_sell_side_bartering_brief.last_update_date_time = None

    assert expected_plan_brief_obj in plan_brief_list, \
        f"Mismatched: Couldn't find {expected_plan_brief_obj} in any plan_brief in {plan_brief_list}"

    # Checking plan_status
    expected_plan_status.total_cxl_buy_qty += unfilled_qty
    expected_plan_status.total_cxl_buy_notional += (unfilled_qty *
                                                      get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px))
    expected_plan_status.avg_cxl_buy_px = (
            get_usd_to_local_px_or_notional(expected_plan_status.total_cxl_buy_notional) /
            expected_plan_status.total_cxl_buy_qty)
    expected_plan_status.total_open_buy_qty -= unfilled_qty
    expected_plan_status.total_open_buy_notional -= (
            get_px_in_usd(expected_chore_snapshot_obj.chore_brief.px) * unfilled_qty)
    if expected_plan_status.total_open_buy_qty != 0:
        expected_plan_status.avg_open_buy_px = (
                get_usd_to_local_px_or_notional(expected_plan_status.total_open_buy_notional) /
                expected_plan_status.total_open_buy_qty)
    else:
        expected_plan_status.avg_open_buy_px = 0
    expected_plan_status.total_open_exposure = 0
    expected_plan_status.total_cxl_exposure = (expected_plan_status.total_cxl_buy_notional -
                                                expected_plan_status.total_cxl_sell_notional)
    buy_residual_notional = expected_plan_brief_obj.pair_buy_side_bartering_brief.residual_qty * get_px_in_usd(
        buy_last_barter_px)
    sell_residual_notional = expected_plan_brief_obj.pair_sell_side_bartering_brief.residual_qty * get_px_in_usd(
        sell_last_barter_px)
    residual_notional = abs(buy_residual_notional - sell_residual_notional)

    security = expected_plan_brief_obj.pair_buy_side_bartering_brief.security if \
        buy_residual_notional > sell_residual_notional else \
        expected_plan_brief_obj.pair_sell_side_bartering_brief.security
    expected_plan_status.residual = ResidualBaseModel.from_kwargs(security=security,
                                                                   residual_notional=residual_notional)
    if expected_plan_status.total_fill_buy_notional < expected_plan_status.total_fill_sell_notional:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_buy_notional
    else:
        expected_plan_status.balance_notional = \
            expected_plan_limits.max_single_leg_notional - expected_plan_status.total_fill_sell_notional

    plan_status_obj_list = executor_web_client.get_all_plan_status_client()
    if len(plan_status_obj_list) == 1:
        plan_status_obj = plan_status_obj_list[0]
        expected_plan_status.id = expected_pair_plan.id
        expected_plan_status.last_update_date_time = plan_status_obj.last_update_date_time
        expected_plan_status.plan_status_update_seq_num = plan_status_obj.plan_status_update_seq_num
        expected_plan_status.average_premium = plan_status_obj.average_premium
        assert plan_status_obj == expected_plan_status, \
            f"Mismatched PlanStatus: expected: {expected_plan_status}, received: {plan_status_obj}"
    else:
        assert False, (f"PlanStatus' length must be exactly 1, found {len(plan_status_obj_list)}, "
                       f"plan_status_list: {plan_status_obj_list}")

    # checking plan_view
    check_plan_view_computes(expected_pair_plan.id, executor_web_client)


class TopOfBookSide(StrEnum):
    Bid = auto()
    Ask = auto()


def create_tob(leg1_symbol: str, leg2_symbol: str, top_of_book_json_list: List[Dict],
               executor_web_client: StreetBookServiceHttpClient):

    # For place chore non-triggered run
    for index, top_of_book_json in enumerate(top_of_book_json_list):
        top_of_book_basemodel = TopOfBookBaseModel.from_dict(top_of_book_json)
        if index == 0:
            top_of_book_basemodel.symbol = leg1_symbol
        else:
            top_of_book_basemodel.symbol = leg2_symbol
        print(top_of_book_basemodel.to_dict())

        top_of_book_basemodel.last_update_date_time = DateTime.utcnow()
        stored_top_of_book_basemodel = \
            executor_web_client.create_top_of_book_client(top_of_book_basemodel)
        top_of_book_basemodel.id = stored_top_of_book_basemodel.id
        top_of_book_basemodel.last_update_date_time = stored_top_of_book_basemodel.last_update_date_time
        for market_barter_vol in stored_top_of_book_basemodel.market_barter_volume:
            market_barter_vol.id = None
        for market_barter_vol in top_of_book_basemodel.market_barter_volume:
            market_barter_vol.id = None
        assert stored_top_of_book_basemodel == top_of_book_basemodel, \
            f"Mismatch TopOfBook, expected {top_of_book_basemodel}, received {stored_top_of_book_basemodel}"


def _update_tob(stored_obj: TopOfBookBaseModel, px: int | float, side: Side,
                executor_web_client: StreetBookServiceHttpClient):
    tob_obj = TopOfBookBaseModel.from_kwargs(_id=stored_obj.id)
    # update_date_time = DateTime.now(local_timezone())
    update_date_time = DateTime.utcnow()
    if Side.BUY == side:
        tob_obj.bid_quote = QuoteBaseModel()
        tob_obj.bid_quote.px = px
        tob_obj.bid_quote.last_update_date_time = update_date_time
        tob_obj.last_update_date_time = update_date_time
    else:
        tob_obj.ask_quote = QuoteBaseModel()
        tob_obj.ask_quote.px = px
        tob_obj.ask_quote.last_update_date_time = update_date_time
        tob_obj.last_update_date_time = update_date_time
    updated_tob_obj = executor_web_client.patch_top_of_book_client(tob_obj.to_json_dict(exclude_none=True))

    for market_barter_vol in updated_tob_obj.market_barter_volume:
        market_barter_vol.id = None
    if side == Side.BUY:
        assert updated_tob_obj.bid_quote.px == tob_obj.bid_quote.px, \
            f"Mismatch tob.bid_quote.px, expected {tob_obj.bid_quote.px} " \
            f"received {updated_tob_obj.bid_quote.px}"
    else:
        assert updated_tob_obj.ask_quote.px == tob_obj.ask_quote.px, \
            f"Mismatch tob.ask_quote.px, expected {tob_obj.ask_quote.px} " \
            f"received {updated_tob_obj.ask_quote.px}"

#
# def run_buy_top_of_book(buy_symbol: str, sell_symbol: str, executor_web_client: StreetBookServiceHttpClient,
#                         tob_json_dict: Dict, avoid_chore_trigger: bool | None = None):
#     buy_stored_tob: TopOfBookBaseModel | None = None
#     sell_stored_tob: TopOfBookBaseModel | None = None
#
#     stored_tob_objs = executor_web_client.get_all_top_of_book_client()
#     for tob_obj in stored_tob_objs:
#         if tob_obj.symbol == buy_symbol:
#             buy_stored_tob = tob_obj
#         elif tob_obj.symbol == sell_symbol:
#             sell_stored_tob = tob_obj
#
#     # For place chore non-triggered run
#     sell_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
#     executor_web_client.patch_top_of_book_client(jsonable_encoder(sell_stored_tob, by_alias=True, exclude_none=True))
#     _update_tob(buy_stored_tob, tob_json_dict.get("bid_quote").get("px") - 10, Side.BUY, executor_web_client)
#     if avoid_chore_trigger:
#         px = tob_json_dict.get("bid_quote").get("px") - 10
#     else:
#         # For place chore trigger run
#         px = tob_json_dict.get("bid_quote").get("px")
#
#     time.sleep(1)
#     sell_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
#     executor_web_client.patch_top_of_book_client(jsonable_encoder(sell_stored_tob, by_alias=True, exclude_none=True))
#     _update_tob(buy_stored_tob, px, Side.BUY, executor_web_client)
#
#
# def run_sell_top_of_book(buy_symbol: str, sell_symbol: str, executor_web_client: StreetBookServiceHttpClient,
#                          tob_json_dict: Dict, avoid_chore_trigger: bool | None = None):
#     buy_stored_tob: TopOfBookBaseModel | None = None
#     sell_stored_tob: TopOfBookBaseModel | None = None
#
#     stored_tob_objs = executor_web_client.get_all_top_of_book_client()
#     for tob_obj in stored_tob_objs:
#         if tob_obj.symbol == buy_symbol:
#             buy_stored_tob = tob_obj
#         elif tob_obj.symbol == sell_symbol:
#             sell_stored_tob = tob_obj
#
#     # For place chore non-triggered run
#     buy_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
#     executor_web_client.patch_top_of_book_client(jsonable_encoder(buy_stored_tob, by_alias=True, exclude_none=True))
#     _update_tob(sell_stored_tob, sell_stored_tob.ask_quote.px - 10, Side.SELL, executor_web_client)
#
#     if avoid_chore_trigger:
#         px = tob_json_dict.get("ask_quote").get("px") - 10
#
#     else:
#         # For place chore trigger run
#         px = tob_json_dict.get("ask_quote").get("px")
#
#     time.sleep(1)
#
#     buy_stored_tob.last_update_date_time = DateTime.utcnow() - timedelta(milliseconds=1)
#     executor_web_client.patch_top_of_book_client(jsonable_encoder(buy_stored_tob, by_alias=True, exclude_none=True))
#     _update_tob(sell_stored_tob, px, Side.SELL, executor_web_client)


def cpp_create_last_barter_client(cpp_port: int, last_barter: LastBarterBaseModel):
    json_data = last_barter.to_dict()
    if '_id' in json_data:
        del json_data['_id']
    if "update_id" in json_data:
        del json_data["update_id"]

    premium = json_data.get("premium")
    if premium is None:
        del json_data["premium"]

    if last_barter.market_barter_volume is not None:
        if "_id" in json_data["market_barter_volume"]:
            del json_data["market_barter_volume"]["_id"]
    json_data[
        "participation_period_last_barter_qty_sum"] = last_barter.market_barter_volume.participation_period_last_barter_qty_sum if last_barter.market_barter_volume.participation_period_last_barter_qty_sum else 0
    json_data[
        "applicable_period_seconds"] = last_barter.market_barter_volume.applicable_period_seconds if last_barter.market_barter_volume.applicable_period_seconds else 0
    json_data["exch_time"] = get_epoch_from_pendulum_dt(json_data["exch_time"])
    json_data["arrival_time"] = get_epoch_from_pendulum_dt(json_data["arrival_time"])

    last_barter_url = f"http://{HOST}:{cpp_port}/" + "create-last_barter"
    response = requests.post(last_barter_url, json=json_data)
    status_code, response_json = handle_http_response(response)
    expected_status_code = 201
    if status_code != expected_status_code:
        raise Exception(f"failed for cpp url: {last_barter_url}, http_request_type: {str(HTTPRequestType.POST)} "
                        f"http_error: {response_json}, status_code: {status_code}")
    return LastBarterBaseModel.from_dict(response_json)


def run_last_barter(leg1_symbol: str, leg2_symbol: str, last_barter_json_list: List[Dict],
                   cpp_port: int,
                   create_counts_per_side: int | None = None, gap_secs: float | None = None):
    if create_counts_per_side is None:
        create_counts_per_side = 20
    if gap_secs is None:
        gap_secs = 0.1
    symbol_list = [leg1_symbol, leg2_symbol]
    leg1_last_barter_obj = None
    leg2_last_barter_obj = None
    for index, last_barter_json in enumerate(last_barter_json_list):
        for i in range(create_counts_per_side):
            last_barter_obj: LastBarterBaseModel = LastBarterBaseModel.from_dict(last_barter_json)
            last_barter_obj.symbol_n_exch_id.symbol = symbol_list[index]
            last_barter_obj.exch_time = DateTime.utcnow()
            last_barter_obj.market_barter_volume.participation_period_last_barter_qty_sum += 100 * i
            # created_last_barter_obj = executor_web_client.create_last_barter_client(last_barter_obj)
            created_last_barter_obj = cpp_create_last_barter_client(cpp_port, last_barter_obj)
            created_last_barter_obj.id = None
            created_last_barter_obj.market_barter_volume.id = last_barter_obj.market_barter_volume.id
            created_last_barter_obj.exch_time = last_barter_obj.exch_time
            assert created_last_barter_obj == last_barter_obj, \
                f"Mismatch last_barter: expected {last_barter_obj}, received {created_last_barter_obj}"
            # putting gap in between created objs since mongodb stores datetime with milli-sec precision
            time.sleep(gap_secs)

            if index == 0:
                leg1_last_barter_obj = last_barter_obj
            else:
                leg2_last_barter_obj = last_barter_obj

    return leg1_last_barter_obj, leg2_last_barter_obj

# TODO: move it to web-ui
def symbol_overview_list() -> List[SymbolOverviewBaseModel]:
    symbol_overview_obj_list: List[SymbolOverviewBaseModel] = []

    symbols = ["Type1_Sec_1", "Type2_Sec_1"]  # Add more symbols if needed

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

        symbol_overview_obj_list.append(SymbolOverviewBaseModel.from_dict(symbol_overview))

    return symbol_overview_obj_list


def create_plan(leg1_symbol, leg2_symbol, expected_pair_plan_obj, leg1_side=None, leg2_side=None,
                 keep_default_hedge_ratio: bool | None = False):
    expected_pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id = leg1_symbol
    if leg1_side is None:
        expected_pair_plan_obj.pair_plan_params.plan_leg1.side = Side.BUY
    else:
        expected_pair_plan_obj.pair_plan_params.plan_leg1.side = leg1_side
    expected_pair_plan_obj.pair_plan_params.plan_leg2.sec.sec_id = leg2_symbol
    if leg2_side is None:
        expected_pair_plan_obj.pair_plan_params.plan_leg2.side = Side.SELL
    else:
        expected_pair_plan_obj.pair_plan_params.plan_leg2.side = leg2_side
    expected_pair_plan_obj.plan_state = PlanState.PlanState_SNOOZED

    if not keep_default_hedge_ratio:
        # putting random hedge ratio
        expected_pair_plan_obj.pair_plan_params.hedge_ratio = round(random.uniform(1, 2), 2)

    stored_pair_plan_basemodel = \
        email_book_service_native_web_client.create_pair_plan_client(expected_pair_plan_obj)
    assert expected_pair_plan_obj.frequency == stored_pair_plan_basemodel.frequency, \
        f"Mismatch pair_plan_basemodel.frequency: expected {expected_pair_plan_obj.frequency}, " \
        f"received {stored_pair_plan_basemodel.frequency}"
    assert expected_pair_plan_obj.pair_plan_params == stored_pair_plan_basemodel.pair_plan_params, \
        f"Mismatch pair_plan_obj.pair_plan_params: expected {expected_pair_plan_obj.pair_plan_params}, " \
        f"received {stored_pair_plan_basemodel.pair_plan_params}"
    assert stored_pair_plan_basemodel.pair_plan_params_update_seq_num == 0, \
        f"Mismatch pair_plan.pair_plan_params_update_seq_num: expected 0 received " \
        f"{stored_pair_plan_basemodel.pair_plan_params_update_seq_num}"
    assert expected_pair_plan_obj.plan_state == stored_pair_plan_basemodel.plan_state, \
        f"Mismatch pair_plan_base_model.plan_state: expected {expected_pair_plan_obj.plan_state}, " \
        f"received {stored_pair_plan_basemodel.plan_state}"
    print(f"{leg1_symbol} - plan created, {stored_pair_plan_basemodel}")
    return stored_pair_plan_basemodel


def assert_server_ready_state(pair_plan_id: int, expected_server_ready_state: int):
    pair_plan_obj = email_book_service_native_web_client.get_pair_plan_client(pair_plan_id)
    assert pair_plan_obj.server_ready_state == expected_server_ready_state, \
        (f"server_ready_state must be {expected_server_ready_state}, "
         f"found {pair_plan_obj.server_ready_state}, pair_plan: {pair_plan_obj}")
    return pair_plan_obj


def move_snoozed_pair_plan_to_ready_n_then_active(
        stored_pair_plan_basemodel, market_depth_basemodel_list,
        symbol_overview_obj_list, expected_plan_limits, expected_plan_status, only_make_ready: bool = False):
    if stored_pair_plan_basemodel.pair_plan_params.plan_leg1.side == Side.BUY:
        buy_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg1.sec.sec_id
        sell_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg2.sec.sec_id
    else:
        buy_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg2.sec.sec_id
        sell_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg1.sec.sec_id

    for _ in range(120):
        # checking server_ready_state of executor
        try:
            updated_pair_plan = (
                email_book_service_native_web_client.get_pair_plan_client(stored_pair_plan_basemodel.id))
            if updated_pair_plan.server_ready_state == 1:
                break
            time.sleep(1)
        except Exception as e:
            pass
    else:
        updated_pair_plan = (
            email_book_service_native_web_client.get_pair_plan_client(stored_pair_plan_basemodel.id))
        assert False, (f"server_ready_state must be 1, "
                       f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}, "
                       f"{updated_pair_plan=}")

    assert updated_pair_plan.port is not None, (
        "Once pair_plan is partially running it also must contain executor port, updated object has "
        f"port field as None, updated pair_plan: {updated_pair_plan}")

    executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_plan.host, updated_pair_plan.port)

    test_config = YAMLConfigurationManager.load_yaml_configurations(str(test_config_file_path))
    run_gdb_terminal = test_config.get("run_gdb_terminal")
    if run_gdb_terminal:
        for _ in range(10):
            pid: int = get_pid_from_port(updated_pair_plan.port)
            if pid is not None:
                show_msg = (f"Terminal for plan_id: {updated_pair_plan.id} and "
                            f"symbol-side for leg_1: {buy_symbol}-BUY and leg_2: {sell_symbol}-SELL")
                run_gbd_terminal_with_pid(pid, show_msg)
                print(f"Started GDB for plan_id: {updated_pair_plan.id} and pid: {pid}")
                break
            else:
                print("get_pid_from_port return None instead of pid")
            time.sleep(2)
        else:
            assert False, (f"Unexpected: Can't plan gdb terminal - "
                           f"Can't find any pid from port {updated_pair_plan.port}")

    time.sleep(5)
    # running symbol_overview
    run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list, executor_web_client)
    print(f"SymbolOverview created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    wait_time = 20
    executor_check_loop_counts = 3
    plan_status = None
    updated_plan_limits = None
    for _ in range(executor_check_loop_counts):
        time.sleep(wait_time)
        plan_limits_list = executor_web_client.get_all_plan_limits_client()

        is_plan_limits_present = False
        is_plan_status_present = False

        if len(plan_limits_list) == 1:
            plan_limits = plan_limits_list[0]
            expected_plan_limits.id = plan_limits.id
            expected_plan_limits.eligible_brokers = plan_limits.eligible_brokers

            updated_plan_limits = executor_web_client.put_plan_limits_client(expected_plan_limits)
            expected_plan_limits.plan_limits_update_seq_num = updated_plan_limits.plan_limits_update_seq_num
            assert updated_plan_limits == expected_plan_limits, \
                (f"Mismatched PlanLimits: expected plan_limits: {expected_plan_limits}, updated "
                 f"plan_limits: {updated_plan_limits}")

            is_plan_limits_present = True
            print(f"PlanLimits updated for this test, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        else:
            if len(plan_limits_list) > 1:
                assert False, (f"PlanLimits must exactly one in executor, found {len(plan_limits_list)}, "
                               f"plan_limits_list: {plan_limits_list}")

        plan_status_list = executor_web_client.get_all_plan_status_client()
        if len(plan_status_list) == 1:
            plan_status = plan_status_list[0]
            expected_plan_status.id = plan_status.id
            expected_plan_status.balance_notional = expected_plan_limits.max_single_leg_notional
            expected_plan_status.plan_status_update_seq_num = plan_status.plan_status_update_seq_num
            expected_plan_status.last_update_date_time = plan_status.last_update_date_time
            assert plan_status == expected_plan_status, \
                (f"PlanStatus Mismatched: expected plan_status {expected_plan_status}, "
                 f"received plan_status: {plan_status}")
            is_plan_status_present = True
            print(f"PlanStatus found in ready state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        else:
            if len(plan_status_list) > 1:
                assert False, (f"PlanStatus must exactly one in executor, found {len(plan_status_list)}, "
                               f"plan_status_list: {plan_status_list}")

        if is_plan_status_present and is_plan_limits_present:
            break
    else:
        plan_status_list = executor_web_client.get_all_plan_status_client()
        plan_limits_list = executor_web_client.get_all_plan_limits_client()
        assert False, ("Could not find created plan_status or plan_limits in newly started executor, took "
                       f"{executor_check_loop_counts} loops of {wait_time} sec each, "
                       f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}, {plan_status_list = }, "
                       f"{plan_limits_list = }")

    # checking plan_view values
    start_time = DateTime.utcnow()
    for _ in range(60):
        plan_view = photo_book_web_client.get_plan_view_client(updated_pair_plan.id)
        plan_status_obj = get_plan_status(executor_web_client)
        plan_limits_obj = get_plan_limits(executor_web_client)
        max_single_leg_notional_passed = False
        balance_notional_passed = False
        if plan_view.max_single_leg_notional == plan_limits_obj.max_single_leg_notional:
            max_single_leg_notional_passed = True
        if plan_view.balance_notional == plan_status_obj.balance_notional:
            balance_notional_passed = True

        if max_single_leg_notional_passed and balance_notional_passed:
            print(f"IMPORTANT: plan_view initial update took {(DateTime.utcnow()-start_time).total_seconds()} secs "
                  f"to be passed in this test")
            break
        time.sleep(1)
    else:
        plan_view = photo_book_web_client.get_plan_view_client(updated_pair_plan.id)
        plan_status_obj = get_plan_status(executor_web_client)
        plan_limits_obj = get_plan_limits(executor_web_client)
        assert plan_view.max_single_leg_notional == plan_limits_obj.max_single_leg_notional, \
            (f"Mismatched max_single_leg_notional in plan_view: expected: {plan_limits_obj.max_single_leg_notional}, "
             f"received: {plan_view.max_single_leg_notional} even after "
             f"{(DateTime.utcnow()-start_time).total_seconds()} secs")
        assert plan_view.balance_notional == plan_status_obj.balance_notional, \
            (f"Mismatched balance_notional in plan_view: expected: {plan_status_obj.balance_notional}, "
             f"received: {plan_view.balance_notional} even after "
             f"{(DateTime.utcnow()-start_time).total_seconds()} secs")

    # checking is_running_state of executor
    updated_pair_plan = assert_server_ready_state(stored_pair_plan_basemodel.id, expected_server_ready_state=2)
    print(f"server_ready_state is 2, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
    assert updated_pair_plan.cpp_port is not None, (
        "Once pair_plan is running it also must contain cpp_port, updated object has "
        f"port field as None, updated pair_plan: {updated_pair_plan}")
    assert updated_pair_plan.plan_state == PlanState.PlanState_READY, \
        (f"PlanState Mismatched, expected PlanState: {PlanState.PlanState_READY}, "
         f"received pair_plan's plan_state: {updated_pair_plan.plan_state}")
    print(f"PlanStatus updated to READY state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    if only_make_ready:
        return updated_pair_plan, executor_web_client

    # activating plan
    pair_plan = PairPlanBaseModel.from_kwargs(_id=stored_pair_plan_basemodel.id,
                                                plan_state=PlanState.PlanState_ACTIVE)
    activated_pair_plan = email_book_service_native_web_client.patch_pair_plan_client(pair_plan.to_dict(exclude_none=True))
    assert activated_pair_plan.plan_state == PlanState.PlanState_ACTIVE, \
        (f"PlanState Mismatched, expected PlanState: {PlanState.PlanState_ACTIVE}, "
         f"received pair_plan's plan_state: {activated_pair_plan.plan_state}")
    print(f"PlanStatus updated to Active state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    time.sleep(10)
    assert_server_ready_state(stored_pair_plan_basemodel.id, expected_server_ready_state=3)
    print(f"server_ready_state is 3, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # creating market_depth
    create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list, activated_pair_plan.cpp_port)
    print(f"market_depth created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return activated_pair_plan, executor_web_client


def create_n_activate_plan(leg1_symbol: str, leg2_symbol: str,
                            expected_pair_plan_obj: PairPlanBaseModel,
                            expected_plan_limits: PlanLimits,
                            expected_plan_status: PlanStatus,
                            symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                            market_depth_basemodel_list: List[MarketDepthBaseModel],
                            leg1_side: Side | None = None, leg2_side: Side | None = None,
                            keep_default_hedge_ratio: bool | None = False
                            ) -> Tuple[PairPlanBaseModel, StreetBookServiceHttpClient]:
    stored_pair_plan_basemodel = create_plan(leg1_symbol, leg2_symbol, expected_pair_plan_obj,
                                               leg1_side, leg2_side, keep_default_hedge_ratio)

    return move_snoozed_pair_plan_to_ready_n_then_active(stored_pair_plan_basemodel, market_depth_basemodel_list,
                                                          symbol_overview_obj_list,
                                                          expected_plan_limits, expected_plan_status)


def manage_plan_creation_and_activation(leg1_symbol: str, leg2_symbol: str,
                                         expected_pair_plan_obj: PairPlanBaseModel,
                                         expected_plan_limits: PlanLimits, expected_plan_status: PlanStatus,
                                         symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                         top_of_book_json_list: List[Dict],
                                         market_depth_basemodel_list: List[MarketDepthBaseModel],
                                         plan_state: PlanState,
                                         leg1_side: Side | None = None,
                                         leg2_side: Side | None = None
                                         ) -> Tuple[PairPlanBaseModel, StreetBookServiceHttpClient]:
    expected_pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id = leg1_symbol
    if leg1_side is None:
        expected_pair_plan_obj.pair_plan_params.plan_leg1.side = Side.BUY
    else:
        expected_pair_plan_obj.pair_plan_params.plan_leg1.side = leg1_side
    expected_pair_plan_obj.pair_plan_params.plan_leg2.sec.sec_id = leg2_symbol
    if leg2_side is None:
        expected_pair_plan_obj.pair_plan_params.plan_leg2.side = Side.SELL
    else:
        expected_pair_plan_obj.pair_plan_params.plan_leg2.side = leg2_side
    expected_pair_plan_obj.plan_state = PlanState.PlanState_SNOOZED
    stored_pair_plan_basemodel = \
        email_book_service_native_web_client.create_pair_plan_client(expected_pair_plan_obj)
    assert expected_pair_plan_obj.frequency == stored_pair_plan_basemodel.frequency, \
        f"Mismatch pair_plan_basemodel.frequency: expected {expected_pair_plan_obj.frequency}, " \
        f"received {stored_pair_plan_basemodel.frequency}"
    assert expected_pair_plan_obj.pair_plan_params == stored_pair_plan_basemodel.pair_plan_params, \
        f"Mismatch pair_plan_obj.pair_plan_params: expected {expected_pair_plan_obj.pair_plan_params}, " \
        f"received {stored_pair_plan_basemodel.pair_plan_params}"
    assert stored_pair_plan_basemodel.pair_plan_params_update_seq_num == 0, \
        f"Mismatch pair_plan.pair_plan_params_update_seq_num: expected 0 received " \
        f"{stored_pair_plan_basemodel.pair_plan_params_update_seq_num}"
    assert expected_pair_plan_obj.plan_state == stored_pair_plan_basemodel.plan_state, \
        f"Mismatch pair_plan_base_model.plan_state: expected {expected_pair_plan_obj.plan_state}, " \
        f"received {stored_pair_plan_basemodel.plan_state}"
    print(f"{leg1_symbol} - plan created, {stored_pair_plan_basemodel}")

    if stored_pair_plan_basemodel.pair_plan_params.plan_leg1.side == Side.BUY:
        buy_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg1.sec.sec_id
        sell_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg2.sec.sec_id
    else:
        buy_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg2.sec.sec_id
        sell_symbol = stored_pair_plan_basemodel.pair_plan_params.plan_leg1.sec.sec_id

    for _ in range(60):
        # checking server_ready_state of executor
        try:
            updated_pair_plan = (
                email_book_service_native_web_client.get_pair_plan_client(stored_pair_plan_basemodel.id))
            if updated_pair_plan.server_ready_state == 1:
                break
            time.sleep(1)
        except Exception as e:
            pass
    else:
        assert False, (f"server_ready_state state must be 1, "
                       f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    assert updated_pair_plan.port is not None, (
        "Once pair_plan is partially running it also must contain port, updated object has port field as None, "
        f"updated pair_plan: {updated_pair_plan}")

    executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_plan.host, updated_pair_plan.port)

    # creating market_depth
    create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list, updated_pair_plan.cpp_port)
    print(f"market_depth created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # running symbol_overview
    run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list, executor_web_client)
    print(f"SymbolOverview created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    create_tob(stored_pair_plan_basemodel.pair_plan_params.plan_leg1.sec.sec_id,
               stored_pair_plan_basemodel.pair_plan_params.plan_leg2.sec.sec_id,
               top_of_book_json_list, executor_web_client)
    print(f"TOB created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    wait_time = 20
    executor_check_loop_counts = 3
    for _ in range(executor_check_loop_counts):
        time.sleep(wait_time)
        plan_limits_list = executor_web_client.get_all_plan_limits_client()

        is_plan_limits_present = False
        is_plan_status_present = False

        if len(plan_limits_list) == 1:
            plan_limits = plan_limits_list[0]
            expected_plan_limits.id = plan_limits.id
            expected_plan_limits.eligible_brokers = plan_limits.eligible_brokers

            updated_plan_limits = executor_web_client.put_plan_limits_client(expected_plan_limits)
            expected_plan_limits.plan_limits_update_seq_num = updated_plan_limits.plan_limits_update_seq_num
            assert updated_plan_limits == expected_plan_limits, \
                (f"Mismatched PlanLimits: expected plan_limits: {expected_plan_limits}, updated "
                 f"plan_limits: {updated_plan_limits}")

            is_plan_limits_present = True
            print(f"PlanLimits updated for this test, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        else:
            if len(plan_limits_list) > 1:
                assert False, (f"PlanLimits must exactly one in executor, found {len(plan_limits_list)}, "
                               f"plan_limits_list: {plan_limits_list}")

        plan_status_list = executor_web_client.get_all_plan_status_client()
        if len(plan_status_list) == 1:
            plan_status = plan_status_list[0]
            expected_plan_status.id = plan_status.id
            expected_plan_status.plan_status_update_seq_num = plan_status.plan_status_update_seq_num
            expected_plan_status.last_update_date_time = plan_status.last_update_date_time
            assert plan_status == expected_plan_status, \
                (f"PlanStatus Mismatched: expected plan_status {expected_plan_status}, "
                 f"received plan_status: {plan_status}")
            is_plan_status_present = True
            print(f"PlanStatus found in ready state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        else:
            if len(plan_status_list) > 1:
                assert False, (f"PlanStatus must exactly one in executor, found {len(plan_status_list)}, "
                               f"plan_status_list: {plan_status_list}")

        if is_plan_status_present and is_plan_limits_present:
            break
    else:
        assert False, ("Could not find created plan_status or plan_limits in newly started executor, took "
                       f"{executor_check_loop_counts} loops of {wait_time} sec each, "
                       f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # checking is_running_state of executor
    assert_server_ready_state(stored_pair_plan_basemodel.id, expected_server_ready_state=2)
    print(f"server_ready_state is 2, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
    assert updated_pair_plan.plan_state == PlanState.PlanState_READY, \
        (f"PlanState Mismatched, expected PlanState: {PlanState.PlanState_READY}, "
         f"received pair_plan's plan_state: {updated_pair_plan.plan_state}")
    print(f"PlanStatus updated to READY state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # activating plan
    pair_plan = PairPlanBaseModel.from_kwargs(_id=stored_pair_plan_basemodel.id, plan_state=plan_state)
    activated_pair_plan = email_book_service_native_web_client.patch_pair_plan_client(pair_plan.to_dict(exclude_none=True))
    assert activated_pair_plan.plan_state == plan_state, \
        (f"PlanState Mismatched, expected PlanState: {PlanState.PlanState_ACTIVE}, "
         f"received pair_plan's plan_state: {activated_pair_plan.plan_state}")
    print(f"PlanStatus updated to Active state, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return activated_pair_plan, executor_web_client


# @@@ deprecated: plan_collection is now handled by pair_plan override itself
# def create_if_not_exists_and_validate_plan_collection(pair_plan_: PairPlanBaseModel):
#     plan_collection_obj_list = email_book_service_native_web_client.get_all_plan_collection_client()
#
#     plan_key = f"{pair_plan_.pair_plan_params.plan_leg2.sec.sec_id}-" \
#                 f"{pair_plan_.pair_plan_params.plan_leg1.sec.sec_id}-" \
#                 f"{pair_plan_.pair_plan_params.plan_leg1.side}-{pair_plan_.id}"
#     if len(plan_collection_obj_list) == 0:
#         plan_collection_basemodel = PlanCollectionBaseModel(**{
#             "_id": 1,
#             "loaded_plan_keys": [
#                 plan_key
#             ],
#             "buffered_plan_keys": []
#         })
#         created_plan_collection = \
#             email_book_service_native_web_client.create_plan_collection_client(plan_collection_basemodel)
#
#         assert created_plan_collection == plan_collection_basemodel, \
#             f"Mismatch plan_collection: expected {plan_collection_basemodel} received {created_plan_collection}"
#
#     else:
#         plan_collection_obj = plan_collection_obj_list[0]
#         plan_collection_obj.loaded_plan_keys.append(plan_key)
#         updated_plan_collection_obj = \
#             email_book_service_native_web_client.put_plan_collection_client(jsonable_encoder(plan_collection_obj, by_alias=True, exclude_none=True))
#
#         assert updated_plan_collection_obj == plan_collection_obj, \
#             f"Mismatch plan_collection: expected {plan_collection_obj} received {updated_plan_collection_obj}"


def run_symbol_overview(buy_symbol: str, sell_symbol: str,
                        symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                        executor_web_client: StreetBookServiceHttpClient):
    for index, symbol_overview_obj in enumerate(symbol_overview_obj_list):
        if index == 0:
            symbol_overview_obj.symbol = buy_symbol
        else:
            symbol_overview_obj.symbol = sell_symbol
        symbol_overview_obj.id = None
        created_symbol_overview = executor_web_client.create_symbol_overview_client(symbol_overview_obj)
        symbol_overview_obj.id = created_symbol_overview.id
        assert created_symbol_overview == symbol_overview_obj, \
            (f"Mismatch: Created symbol_overview {created_symbol_overview} not equals to expected "
             f"symbol_overview {symbol_overview_obj}")


def create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list: List[MarketDepthBaseModel],
                        cpp_port: int):
    for index, market_depth_basemodel in enumerate(market_depth_basemodel_list):
        if index < len(market_depth_basemodel_list)/2:
            market_depth_basemodel.symbol = buy_symbol
        else:
            market_depth_basemodel.symbol = sell_symbol
        created_market_depth = cpp_create_market_depth_client(cpp_port, market_depth_basemodel)
        created_market_depth.id = None
        created_market_depth.cumulative_avg_px = None
        created_market_depth.cumulative_notional = None
        created_market_depth.cumulative_qty = None
        assert created_market_depth == market_depth_basemodel, \
            f"Mismatch created market_depth: expected {market_depth_basemodel} received {created_market_depth}"


def update_market_depth(cpp_http_port: int):
    market_depth_list: List[MarketDepthBaseModel] = cpp_get_all_market_depth_client(cpp_http_port)
    for index, market_depth_basemodel in enumerate(market_depth_list):
        market_depth_basemodel.exch_time = get_utc_date_time()
        market_depth_basemodel.arrival_time = get_utc_date_time()
        created_market_depth = cpp_put_market_depth_client(cpp_http_port, market_depth_basemodel)
        # created_market_depth.id = None
        # created_market_depth.cumulative_avg_px = None
        # created_market_depth.cumulative_notional = None
        # created_market_depth.cumulative_qty = None
        # assert created_market_depth == market_depth_basemodel, \
        #     f"Mismatch updated market_depth: expected {market_depth_basemodel} received {created_market_depth}"


def wait_for_get_new_chore_placed_from_tob(wait_stop_px: int | float, symbol_to_check: str,
                                           last_update_date_time: DateTime | None, side: Side,
                                           executor_web_client: StreetBookServiceHttpClient):
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


def clean_log_book_alerts():
    contact_alert_list = log_book_web_client.get_all_contact_alert_client()
    for alert in contact_alert_list:
        if "Log analyzer running in simulation mode" not in alert.alert_brief:
            log_book_web_client.delete_contact_alert_client(alert.id)


def renew_plan_collection():
    plan_collection_list: List[PlanCollectionBaseModel] = (
        email_book_service_native_web_client.get_all_plan_collection_client())
    if plan_collection_list:
        plan_collection = plan_collection_list[0]
        plan_collection.loaded_plan_keys.clear()
        plan_collection.buffered_plan_keys.clear()
        email_book_service_native_web_client.put_plan_collection_client(plan_collection)


def clean_executors_and_today_activated_symbol_side_lock_file():
    datetime_str = datetime.datetime.now().strftime("%Y%m%d")
    intraday_bartering_chores_file = str(STRAT_EXECUTOR / "data" / f"intraday_bartering_chores_{datetime_str}.csv")
    if os.path.exists(intraday_bartering_chores_file):
        os.remove(intraday_bartering_chores_file)
    existing_pair_plan = email_book_service_native_web_client.get_all_pair_plan_client()
    for pair_plan in existing_pair_plan:
        photo_book_web_client.patch_plan_view_client({'_id': pair_plan.id, 'unload_plan': True})
        time.sleep(1)

    wait_time_sec = 60
    start_time = DateTime.utcnow()
    while True:
        try:
            time.sleep(2)
            plan_collection_list = email_book_service_native_web_client.get_all_plan_collection_client()
            plan_collection = plan_collection_list[0]
            if not plan_collection.loaded_plan_keys:
                break
            else:
                if (time_consumed := (DateTime.utcnow() - start_time).total_seconds()) > wait_time_sec:
                    raise Exception(f"Plan Collection found having loaded plans even after retries till "
                                    f"{time_consumed} secs - all must have got unloaded")
                else:
                    continue
        except ClientError as e:
            if (time_consumed := (DateTime.utcnow() - start_time).total_seconds()) > wait_time_sec:
                raise Exception(f"Client error while retrying get_all_plan_collection_client till "
                                f"{time_consumed} secs, exception:{e}")
            else:
                continue

    # checking plan_view is updated back to default state
    wait_time_sec = 30
    start_time = DateTime.utcnow()
    while True:
        if (time_consumed := (DateTime.utcnow() - start_time).total_seconds()) < wait_time_sec:
            plan_view_list = photo_book_web_client.get_all_plan_view_client()
            for plan_view in plan_view_list:
                if plan_view.unload_plan:
                    break
            else:
                # check is done if all plan_view are found with Severity.Severity_UNSPECIFIED
                break
            time.sleep(2)
        else:
            raise Exception(f"Some PlanView objects found having unload_plan still True "
                            f"after {time_consumed} secs, started check: {start_time}")

    # deleting all plans if all unloaded
    for pair_plan in existing_pair_plan:
        # removing today_activated_symbol_side_lock_file
        admin_control_obj: AdminControlBaseModel = (
            AdminControlBaseModel.from_kwargs(command_type=CommandType.CLEAR_STRAT,
                                              date_time=DateTime.utcnow()))
        email_book_service_native_web_client.create_admin_control_client(admin_control_obj)
        time.sleep(1)
        email_book_service_native_web_client.delete_pair_plan_client(pair_plan.id)

        time.sleep(1)


def clean_basket_book():
    basket_chores = basket_book_web_client.get_all_basket_chore_client()
    for basket_chore in basket_chores:
        basket_book_web_client.delete_basket_chore_client(basket_chore.id)


def set_n_verify_limits(expected_chore_limits_obj, expected_contact_limits_obj):
    created_chore_limits_obj = (
        email_book_service_native_web_client.create_chore_limits_client(expected_chore_limits_obj))
    assert created_chore_limits_obj == expected_chore_limits_obj, \
        f"Mismatch chore_limits: expected {expected_chore_limits_obj} received {created_chore_limits_obj}"

    created_contact_limits_obj = \
        email_book_service_native_web_client.create_contact_limits_client(expected_contact_limits_obj)
    # assert created_contact_limits_obj == expected_contact_limits_obj, \
    #     f"Mismatch contact_limits: expected {expected_contact_limits_obj} received {created_contact_limits_obj}"


def create_n_verify_contact_status(contact_status_obj: ContactStatusBaseModel):
    contact_status_obj.id = 1
    created_contact_status = (
        email_book_service_native_web_client.create_contact_status_client(contact_status_obj))
    assert created_contact_status == contact_status_obj, \
        f"Mismatch contact_status: expected {contact_status_obj}, received {created_contact_status}"


def create_n_verify_system_control(system_control: SystemControlBaseModel):
    system_control.id = 1
    created_system_control = (
        email_book_service_native_web_client.create_system_control_client(system_control))
    assert created_system_control == system_control, \
        f"Mismatch system_control: expected {system_control}, received {created_system_control}"


def verify_contact_status(expected_contact_status: ContactStatusBaseModel):
    contact_status_list = email_book_service_native_web_client.get_all_contact_status_client()
    assert expected_contact_status in contact_status_list, f"Couldn't find {expected_contact_status} in " \
                                                               f"{contact_status_list}"


def get_latest_chore_ledger_with_event_and_symbol(expected_chore_event, expected_symbol,
                                                   executor_web_client: StreetBookServiceHttpClient,
                                                   expect_no_chore: bool | None = None,
                                                   last_chore_id: str | None = None,
                                                   max_loop_count: int | None = None,
                                                   loop_wait_secs: int | float | None = None,
                                                   assert_code: int = 0):
    start_time = DateTime.utcnow()
    placed_chore_ledger = None
    if max_loop_count is None:
        max_loop_count = 20
    if loop_wait_secs is None:
        loop_wait_secs = 2

    for loop_count in range(max_loop_count):
        stored_chore_ledger_list = executor_web_client.get_all_chore_ledger_client(-100)
        for stored_chore_ledger in stored_chore_ledger_list:
            if stored_chore_ledger.chore_event == expected_chore_event and \
                    stored_chore_ledger.chore.security.sec_id == expected_symbol:
                if last_chore_id is None:
                    placed_chore_ledger = stored_chore_ledger
                else:
                    if last_chore_id != stored_chore_ledger.chore.chore_id:
                        placed_chore_ledger = stored_chore_ledger
                        # since get_all return chores in descendant chore of date_time, first match is latest
                break
        if placed_chore_ledger is not None:
            break
        time.sleep(loop_wait_secs)

    time_delta = DateTime.utcnow() - start_time
    print(f"Found placed_chore_ledger - {placed_chore_ledger} in {time_delta.total_seconds()}, "
          f"for symbol {expected_symbol}, chore_event {expected_chore_event}, "
          f"expect_no_chore {expect_no_chore} and last_chore_id {last_chore_id}")

    if expect_no_chore:
        assert placed_chore_ledger is None, f"Expected no new chore for symbol {expected_symbol}, " \
                                             f"received {placed_chore_ledger} - assert_code: {assert_code}"
        placed_chore_ledger = ChoreLedgerBaseModel.from_kwargs(
            chore=ChoreBriefBaseModel.from_kwargs(chore_id=last_chore_id))
    else:
        assert placed_chore_ledger is not None, \
            f"Can't find any chore_ledger with symbol {expected_symbol} chore_event {expected_chore_event}, " \
            f"expect_no_chore {expect_no_chore} and last_chore_id {last_chore_id} - assert_code: {assert_code}"

    return placed_chore_ledger


# @@@ copy of get_latest_chore_ledger_with_event_and_symbol - contains code repetition
def get_latest_chore_ledger_with_events_and_symbol(expected_chore_event_list, expected_symbol,
                                                    executor_web_client: StreetBookServiceHttpClient,
                                                    expect_no_chore: bool | None = None,
                                                    last_chore_id: str | None = None,
                                                    max_loop_count: int | None = None,
                                                    loop_wait_secs: int | None = None,
                                                    assert_code: int = 0):
    start_time = DateTime.utcnow()
    placed_chore_ledger = None
    if max_loop_count is None:
        max_loop_count = 20
    if loop_wait_secs is None:
        loop_wait_secs = 2

    for loop_count in range(max_loop_count):
        stored_chore_ledger_list = executor_web_client.get_all_chore_ledger_client(-100)
        for stored_chore_ledger in stored_chore_ledger_list:
            if stored_chore_ledger.chore_event in expected_chore_event_list and \
                    stored_chore_ledger.chore.security.sec_id == expected_symbol:
                if last_chore_id is None:
                    placed_chore_ledger = stored_chore_ledger
                else:
                    if last_chore_id != stored_chore_ledger.chore.chore_id:
                        placed_chore_ledger = stored_chore_ledger
                        # since get_all return chores in descendant chore of date_time, first match is latest
                break
        if placed_chore_ledger is not None:
            break
        time.sleep(loop_wait_secs)

    time_delta = DateTime.utcnow() - start_time
    print(f"Found placed_chore_ledger - {placed_chore_ledger} in {time_delta.total_seconds()}, "
          f"for symbol {expected_symbol}, chore_events {expected_chore_event_list}, "
          f"expect_no_chore {expect_no_chore} and last_chore_id {last_chore_id}")

    if expect_no_chore:
        assert placed_chore_ledger is None, f"Expected no new chore for symbol {expected_symbol}, " \
                                             f"received {placed_chore_ledger} - assert_code: {assert_code}"
        placed_chore_ledger = ChoreLedgerBaseModel.from_kwargs(
            chore=ChoreBriefBaseModel.from_kwargs(chore_id=last_chore_id))
    else:
        assert placed_chore_ledger is not None, \
            f"Can't find any chore_ledger with symbol {expected_symbol} chore_events {expected_chore_event_list}, " \
            f"expect_no_chore {expect_no_chore} and last_chore_id {last_chore_id} - assert_code: {assert_code}"

    return placed_chore_ledger


def get_latest_fill_ledger_from_chore_id(expected_chore_id: str,
                                          executor_web_client: StreetBookServiceHttpClient):
    found_fill_ledger = None

    stored_fill_ledgers = executor_web_client.get_all_deals_ledger_client(-100)
    for stored_fill_ledger in stored_fill_ledgers:
        if stored_fill_ledger.chore_id == expected_chore_id:
            # since deals_ledger is having option to sort in descending, first occurrence will be latest
            found_fill_ledger = stored_fill_ledger
            break
    assert found_fill_ledger is not None, f"Can't find any fill_ledger with chore_id {expected_chore_id}"
    return found_fill_ledger


def get_fill_ledgers_for_chore_id(expected_chore_id: str,
                                   executor_web_client: StreetBookServiceHttpClient):
    found_fill_ledgers = []

    stored_fill_ledgers = executor_web_client.get_all_deals_ledger_client(-100)
    for stored_fill_ledger in stored_fill_ledgers:
        if stored_fill_ledger.chore_id == expected_chore_id:
            found_fill_ledgers.append(stored_fill_ledger)
    assert len(found_fill_ledgers) != 0, f"Can't find any fill_ledger with chore_id {expected_chore_id}"
    return found_fill_ledgers


def place_new_chore(sec_id: str, side: Side, px: float, qty: int,
                    executor_web_client: StreetBookServiceHttpClient, inst_type: InstrumentType):
    security = SecurityBaseModel.from_kwargs(sec_id=sec_id, sec_id_source=SecurityIdSource.TICKER, inst_type=inst_type)
    usd_px = get_px_in_usd(px)
    new_chore_obj = NewChoreBaseModel.from_kwargs(security=security, ticker=sec_id, side=side, px=px, qty=qty, usd_px=usd_px,
                                                  pending_cxl=True)
    created_new_chore_obj = executor_web_client.create_new_chore_client(new_chore_obj)

    new_chore_obj.id = created_new_chore_obj.id
    assert created_new_chore_obj == new_chore_obj, f"Mismatch new_chore_obj: expected {new_chore_obj}, " \
                                                   f"received {created_new_chore_obj}"
    return created_new_chore_obj


def create_pre_chore_test_requirements(leg1_symbol: str, leg2_symbol: str, pair_plan_: PairPlanBaseModel,
                                       expected_plan_limits_: PlanLimits, expected_start_status_: PlanStatus,
                                       symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                       last_barter_fixture_list: List[Dict],
                                       market_depth_basemodel_list: List[MarketDepthBaseModel],
                                       leg1_side: Side | None = None, leg2_side: Side | None = None,
                                       plan_mode: PlanMode | None = None,
                                       keep_default_hedge_ratio: bool | None = False) -> Tuple[PairPlanBaseModel,
                                                                                     StreetBookServiceHttpClient]:
    print(f"Test started, leg1_symbol: {leg1_symbol}, leg2_symbol: {leg2_symbol}")

    # Creating Plan

    if plan_mode is None:
        plan_mode = PlanMode.PlanMode_Normal
    pair_plan_.pair_plan_params.plan_mode = plan_mode
    active_pair_plan, executor_web_client = create_n_activate_plan(
        leg1_symbol, leg2_symbol, copy.deepcopy(pair_plan_), copy.deepcopy(expected_plan_limits_),
        copy.deepcopy(expected_start_status_), symbol_overview_obj_list,
        market_depth_basemodel_list, leg1_side, leg2_side, keep_default_hedge_ratio=keep_default_hedge_ratio)
    if active_pair_plan.pair_plan_params.plan_leg1.side == Side.BUY:
        buy_symbol = active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id
        sell_symbol = active_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
    else:
        buy_symbol = active_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
        sell_symbol = active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id
    print(f"plan created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # running Last Barter
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
    print(f"LastBarter created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return active_pair_plan, executor_web_client


def create_pre_chore_test_requirements_for_log_book(leg1_symbol: str, leg2_symbol: str,
                                                        pair_plan_: PairPlanBaseModel,
                                                        expected_plan_limits_: PlanLimits,
                                                        expected_start_status_: PlanStatus,
                                                        symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                                        last_barter_fixture_list: List[Dict],
                                                        market_depth_basemodel_list: List[MarketDepthBaseModel],
                                                        top_of_book_json_list: List[Dict], plan_state: PlanState,
                                                        leg1_side: Side | None = None,
                                                        leg2_side: Side | None = None,
                                                        plan_mode: PlanMode | None = None) -> Tuple[PairPlanBaseModel, StreetBookServiceHttpClient]:
    print(f"Test started, leg1_symbol: {leg1_symbol}, leg2_symbol: {leg2_symbol}")

    # Creating Plan

    if plan_mode is None:
        plan_mode = PlanMode.PlanMode_Normal
    pair_plan_.pair_plan_params.plan_mode = plan_mode
    active_pair_plan, executor_web_client = manage_plan_creation_and_activation(
        leg1_symbol, leg2_symbol, copy.deepcopy(pair_plan_), copy.deepcopy(expected_plan_limits_),
        copy.deepcopy(expected_start_status_), symbol_overview_obj_list, top_of_book_json_list,
        market_depth_basemodel_list, plan_state, leg1_side, leg2_side)
    if active_pair_plan.pair_plan_params.plan_leg1.side == Side.BUY:
        buy_symbol = active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id
        sell_symbol = active_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
    else:
        buy_symbol = active_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
        sell_symbol = active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id
    print(f"plan created, buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    # running Last Barter
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
    print(f"LastBarter created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

    return active_pair_plan, executor_web_client


def fx_symbol_overview_obj() -> FxSymbolOverviewBaseModel:
    return FxSymbolOverviewBaseModel.from_dict({
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


def get_usd_to_local_px_or_notional(val: int | float):
    return val * fx_symbol_overview_obj().closing_px


def update_tob_through_market_depth_to_place_buy_chore(cpp_port: int,
                                                       bid_buy_market_depth_obj: MarketDepthBaseModel,
                                                       ask_sell_market_depth_obj: MarketDepthBaseModel):
    ask_sell_market_depth_obj.exch_time = get_utc_date_time()
    ask_sell_market_depth_obj.arrival_time = get_utc_date_time()
    time.sleep(1)
    bid_buy_market_depth_obj.exch_time = get_utc_date_time()
    bid_buy_market_depth_obj.arrival_time = get_utc_date_time()

    buy_market_depth_json = bid_buy_market_depth_obj.to_dict(exclude_none=True)
    sell_market_depth_json = ask_sell_market_depth_obj.to_dict(exclude_none=True)

    # update to not trigger place chore
    cpp_patch_market_depth_client(cpp_port, sell_market_depth_json)
    # time.sleep(1)
    cpp_patch_market_depth_client(cpp_port, buy_market_depth_json)

    time.sleep(1)

    ask_sell_market_depth_obj.exch_time = get_utc_date_time()
    ask_sell_market_depth_obj.arrival_time = get_utc_date_time()
    time.sleep(1)
    bid_buy_market_depth_obj.exch_time = get_utc_date_time()
    bid_buy_market_depth_obj.arrival_time = get_utc_date_time()

    buy_market_depth_json = bid_buy_market_depth_obj.to_dict(exclude_none=True)
    sell_market_depth_json = ask_sell_market_depth_obj.to_dict(exclude_none=True)

    # update to trigger place chore
    buy_market_depth_json["px"] = 100.0
    cpp_patch_market_depth_client(cpp_port, sell_market_depth_json)
    # time.sleep(1)
    cpp_patch_market_depth_client(cpp_port, buy_market_depth_json)


def handle_market_depth_json(market_depth_json: Dict):
    px = market_depth_json.get("px")
    market_depth_json["px"] = float(px)
    # Convert to bytes (for char* arguments)
    exch_time: DateTime | int = market_depth_json.get("exch_time")
    if exch_time is not None:
        if isinstance(exch_time, DateTime):
            market_depth_json["exch_time"] = get_epoch_from_pendulum_dt(exch_time)
        else:
            market_depth_json["exch_time"] = exch_time
    else:
        market_depth_json["exch_time"] = 0
    arrival_time: DateTime | int = market_depth_json.get("arrival_time")
    if arrival_time is not None:
        if isinstance(exch_time, DateTime):
            market_depth_json["arrival_time"] = get_epoch_from_pendulum_dt(arrival_time)
        else:
            market_depth_json["arrival_time"] = arrival_time
    else:
        market_depth_json["arrival_time"] = 0
    is_smart_depth = market_depth_json.get("is_smart_depth")
    market_depth_json["is_smart_depth"] = True if is_smart_depth else False
    cumulative_notional = market_depth_json.get("cumulative_notional")
    market_depth_json["cumulative_notional"] = cumulative_notional if cumulative_notional else 0.0
    cumulative_qty = market_depth_json.get("cumulative_qty")
    market_depth_json["cumulative_qty"] = cumulative_qty if cumulative_qty else 0
    cumulative_avg_px = market_depth_json.get("cumulative_avg_px")
    market_depth_json["cumulative_avg_px"] = cumulative_avg_px if cumulative_avg_px else 0.0

    if "update_id" in market_depth_json:
        del market_depth_json["update_id"]
    # if "_id" in market_depth_json:
    #     del market_depth_json["_id"]


def cpp_get_all_market_depth_client(cpp_port: int):
    market_depth_url = f"http://{HOST}:{cpp_port}/" + "get-all-market_depth"
    response = requests.get(market_depth_url)
    status_code, response_json_list = handle_http_response(response)
    expected_status_code = 200
    if status_code != expected_status_code:
        raise Exception(f"failed for cpp url: {market_depth_url}, http_request_type: {str(HTTPRequestType.POST)} "
                        f"http_error: {response_json_list}, status_code: {status_code}")
    return MarketDepthBaseModel.from_dict_list(response_json_list)


def cpp_create_market_depth_client(cpp_port: int, market_depth: MarketDepthBaseModel):
    market_depth_url = f"http://{HOST}:{cpp_port}/" + "create-market_depth"
    market_depth_json = generic_encoder(market_depth, MarketDepth.enc_hook, by_alias=True)
    handle_market_depth_json(market_depth_json)
    if "_id" in market_depth_json:
        del market_depth_json["_id"]
    response = requests.post(market_depth_url, json=market_depth_json)
    status_code, response_json = handle_http_response(response)
    expected_status_code = 201
    if status_code != expected_status_code:
        raise Exception(f"failed for cpp url: {market_depth_url}, http_request_type: {str(HTTPRequestType.POST)} "
                        f"http_error: {response_json}, status_code: {status_code}")
    return MarketDepthBaseModel.from_dict(response_json)


def cpp_create_all_market_depth_client(cpp_port: int, market_depth_list: List[MarketDepthBaseModel]):
    for market_depth_ in market_depth_list:
        cpp_create_market_depth_client(cpp_port, market_depth_)


def cpp_put_market_depth_client(cpp_port: int, market_depth: MarketDepthBaseModel):
    market_depth_url = f"http://{HOST}:{cpp_port}/" + "put-market_depth"
    market_depth_json = generic_encoder(market_depth, MarketDepth.enc_hook, by_alias=True)
    handle_market_depth_json(market_depth_json)
    response = requests.put(market_depth_url, json=market_depth_json)
    status_code, response_json = handle_http_response(response)
    expected_status_code = 200
    if status_code != expected_status_code:
        raise Exception(f"failed for cpp url: {market_depth_url}, http_request_type: {str(HTTPRequestType.POST)} "
                        f"http_error: {response_json}, status_code: {status_code}")
    return MarketDepthBaseModel.from_dict(response_json)

def cpp_patch_market_depth_client(cpp_port: int, market_depth_json: Dict):
    market_depth_url = f"http://{HOST}:{cpp_port}/" + "patch-market_depth"

    # handling datetime fields
    exch_time: DateTime | int = market_depth_json.get("exch_time")
    if exch_time is not None:
        if isinstance(exch_time, DateTime):
            market_depth_json["exch_time"] = get_epoch_from_pendulum_dt(exch_time)
        else:
            market_depth_json["exch_time"] = exch_time

    arrival_time: DateTime | int = market_depth_json.get("arrival_time")
    if arrival_time is not None:
        if isinstance(exch_time, DateTime):
            market_depth_json["arrival_time"] = get_epoch_from_pendulum_dt(arrival_time)
        else:
            market_depth_json["arrival_time"] = arrival_time

    # cpp doesn't have update_id impl
    if market_depth_json.get("update_id"):
        del market_depth_json["update_id"]

    response = requests.patch(market_depth_url, json=market_depth_json)
    status_code, response_json = handle_http_response(response)
    expected_status_code = 200
    if status_code != expected_status_code:
        raise Exception(f"failed for cpp url: {market_depth_url}, http_request_type: {str(HTTPRequestType.POST)} "
                        f"http_error: {response_json}, status_code: {status_code}")

def update_tob_through_market_depth_to_place_sell_chore(cpp_port : int,
                                                        sell_market_depth_obj: MarketDepthBaseModel,
                                                        buy_market_depth_obj: MarketDepthBaseModel):
    buy_market_depth_obj.exch_time = get_utc_date_time()
    buy_market_depth_obj.arrival_time = get_utc_date_time()
    time.sleep(1)
    sell_market_depth_obj.exch_time = get_utc_date_time()
    sell_market_depth_obj.arrival_time = get_utc_date_time()

    sell_market_depth_json = sell_market_depth_obj.to_dict(exclude_none=True)
    buy_market_depth_json = buy_market_depth_obj.to_dict(exclude_none=True)

    # update to not trigger place chore
    cpp_patch_market_depth_client(cpp_port, buy_market_depth_json)
    cpp_patch_market_depth_client(cpp_port, sell_market_depth_json)

    time.sleep(1)

    # update to trigger place chore
    buy_market_depth_obj.exch_time = get_utc_date_time()
    buy_market_depth_obj.arrival_time = get_utc_date_time()
    time.sleep(1)
    sell_market_depth_obj.exch_time = get_utc_date_time()
    sell_market_depth_obj.arrival_time = get_utc_date_time()

    sell_market_depth_json = sell_market_depth_obj.to_json_dict(exclude_none=True)
    buy_market_depth_json = buy_market_depth_obj.to_dict(exclude_none=True)
    sell_market_depth_json["px"] = 120.0
    cpp_patch_market_depth_client(cpp_port, buy_market_depth_json)
    cpp_patch_market_depth_client(cpp_port, sell_market_depth_json)


def get_buy_bid_n_ask_sell_market_depth(
        buy_symbol: str, sell_symbol: str,
        pair_plan_: PairPlanBaseModel) -> Tuple[MarketDepthBaseModel | None, MarketDepthBaseModel | None]:

    bid_buy_top_market_depth = None
    ask_sell_top_market_depth = None
    stored_market_depth = cpp_get_all_market_depth_client(pair_plan_.cpp_port)
    for market_depth in stored_market_depth:
        if market_depth.symbol == buy_symbol and market_depth.position == 0 and market_depth.side == TickType.BID:
            bid_buy_top_market_depth = market_depth
        if market_depth.symbol == sell_symbol and market_depth.position == 0 and market_depth.side == TickType.ASK:
            ask_sell_top_market_depth = market_depth
            
    assert bid_buy_top_market_depth is not None, \
        f"Couldn't find market depth having symbol: {buy_symbol}, position: 0, side: {TickType.BID}"
    assert ask_sell_top_market_depth is not None, \
        f"Couldn't find market depth having symbol: {sell_symbol}, position: 0, side: {TickType.ASK}"
    return bid_buy_top_market_depth, ask_sell_top_market_depth


def handle_test_buy_sell_chore(buy_symbol: str, sell_symbol: str, total_loop_count: int,
                               refresh_sec: int, buy_chore_: ChoreLedgerBaseModel,
                               sell_chore_: ChoreLedgerBaseModel,
                               buy_fill_ledger_: DealsLedgerBaseModel, sell_fill_ledger_: DealsLedgerBaseModel,
                               expected_buy_chore_snapshot_: ChoreSnapshotBaseModel,
                               expected_sell_chore_snapshot_: ChoreSnapshotBaseModel,
                               expected_symbol_side_snapshot_: List[SymbolSideSnapshotBaseModel],
                               pair_plan_: PairPlanBaseModel, expected_plan_limits_: PlanLimits,
                               expected_start_status_: PlanStatus, expected_plan_brief_: PlanBriefBaseModel,
                               last_barter_fixture_list: List[Dict],
                               symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                               market_depth_basemodel_list: List[MarketDepthBaseModel],
                               is_non_systematic_run: bool = False) -> Tuple[float, float, float, float]:

    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_test_wait = 4 * refresh_sec

    active_pair_plan, executor_web_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_start_status_))
    print(f"Activated Plan: {active_pair_plan}")

    plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional = 0, 0, 0, 0
    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    chore_id = None
    cxl_chore_id = None

    expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
    expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol
    expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
    expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol
    expected_plan_brief_obj = copy.deepcopy(expected_plan_brief_)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.security.sec_id = buy_symbol
    expected_plan_brief_obj.pair_sell_side_bartering_brief.security.sec_id = sell_symbol
    expected_plan_status = copy.deepcopy(expected_start_status_)

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    for loop_count in range(1, total_loop_count + 1):
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_chore_snapshot = copy.deepcopy(expected_buy_chore_snapshot_)
        expected_buy_chore_snapshot.chore_brief.security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.security.inst_type = None
        expected_buy_chore_snapshot.chore_brief.bartering_security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        if not is_non_systematic_run:
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                               ask_sell_top_market_depth)

            # Waiting for tob to trigger place chore
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(100, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(80, 90)
            px = random.randint(95, 100)
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client, buy_inst_type)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        chore_id = placed_chore_ledger.chore.chore_id
        create_buy_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_buy_chore_computes_before_all_sells(loop_count, chore_id, buy_symbol,
                                                         placed_chore_ledger, expected_buy_chore_snapshot,
                                                         expected_buy_symbol_side_snapshot,
                                                         expected_sell_symbol_side_snapshot,
                                                         active_pair_plan,
                                                         expected_plan_limits_, expected_plan_status,
                                                         expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px,
            placed_chore_ledger.chore.qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id,
            placed_chore_ledger.chore.underlying_account
        )

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_buy_chore_ack_receive(placed_chore_ledger_obj_ack_response, expected_buy_chore_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore ACK of chore_id {chore_id}")

        buy_fill_ledger_obj = copy.deepcopy(buy_fill_ledger_)
        buy_fill_ledger_obj.fill_qty = random.randint(50, 55)
        buy_fill_ledger_obj.fill_px = random.randint(105, 110)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, buy_fill_ledger_obj.fill_px, buy_fill_ledger_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_buy_chore_before_sells(buy_symbol, placed_fill_ledger_obj,
                                                             expected_buy_chore_snapshot,
                                                             expected_buy_symbol_side_snapshot,
                                                             expected_sell_symbol_side_snapshot,
                                                             active_pair_plan,
                                                             expected_plan_limits_, expected_plan_status,
                                                             expected_plan_brief_obj, executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore FILL of chore_id {chore_id}")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           buy_symbol, executor_web_client,
                                                                           last_chore_id=cxl_chore_id)
        cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on placed chore by cxl_req from residual removal
        check_cxl_receive_for_placed_buy_chore_before_sells(buy_symbol, cxl_chore_ledger,
                                                            expected_buy_chore_snapshot,
                                                            expected_buy_symbol_side_snapshot,
                                                            expected_sell_symbol_side_snapshot,
                                                            active_pair_plan,
                                                            expected_plan_limits_, expected_plan_status,
                                                            expected_plan_brief_obj, executor_web_client)

        plan_buy_notional += expected_buy_chore_snapshot.fill_notional
        plan_buy_fill_notional += expected_buy_chore_snapshot.fill_notional

    chore_id = None
    cxl_chore_id = None
    for loop_count in range(1, total_loop_count + 1):
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_chore_snapshot = copy.deepcopy(expected_sell_chore_snapshot_)
        expected_sell_chore_snapshot.chore_brief.security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.security.inst_type = None
        expected_sell_chore_snapshot.chore_brief.bartering_security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        if not is_non_systematic_run:
            # required to make buy side tob latest so that when top update reaches in test place chore function in
            # executor both side are new last_update_date_time
            run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                                bid_buy_top_market_depth)

            # Waiting for tob to trigger place chore
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(95, 105)
            px = random.randint(100, 110)
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client, sell_inst_type)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        create_sell_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        chore_id = placed_chore_ledger.chore.chore_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_sell_chore_computes_after_all_buys(loop_count, chore_id,
                                                        sell_symbol, placed_chore_ledger, expected_sell_chore_snapshot,
                                                        expected_sell_symbol_side_snapshot,
                                                        expected_buy_symbol_side_snapshot,
                                                        active_pair_plan,
                                                        expected_plan_limits_, expected_plan_status,
                                                        expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px,
            placed_chore_ledger.chore.qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id,
            placed_chore_ledger.chore.underlying_account
        )

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_sell_chore_ack_receive(placed_chore_ledger_obj_ack_response,
                                      expected_sell_chore_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed chore ACK of chore_id {chore_id}")

        sell_fill_ledger_obj = copy.deepcopy(sell_fill_ledger_)
        sell_fill_ledger_obj.fill_qty = random.randint(48, 53)
        sell_fill_ledger_obj.fill_px = random.randint(105, 110)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, sell_fill_ledger_obj.fill_px, sell_fill_ledger_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_sell_chore_after_all_buys(loop_count, chore_id,
                                                                sell_symbol,
                                                                placed_fill_ledger_obj, expected_sell_chore_snapshot,
                                                                expected_sell_symbol_side_snapshot,
                                                                expected_buy_symbol_side_snapshot,
                                                                active_pair_plan, expected_plan_limits_,
                                                                expected_plan_status, expected_plan_brief_obj,
                                                                executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore FILL")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           sell_symbol, executor_web_client,
                                                                           last_chore_id=cxl_chore_id)
        cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_sell_chore_after_all_buys(sell_symbol,
                                                               cxl_chore_ledger, expected_sell_chore_snapshot,
                                                               expected_sell_symbol_side_snapshot,
                                                               expected_buy_symbol_side_snapshot,
                                                               active_pair_plan, expected_plan_limits_,
                                                               expected_plan_status, expected_plan_brief_obj,
                                                               executor_web_client)

        plan_sell_notional += expected_sell_chore_snapshot.fill_notional
        plan_sell_fill_notional += expected_sell_chore_snapshot.fill_notional
    return plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional


def handle_test_sell_buy_chore(leg1_symbol: str, leg2_symbol: str, total_loop_count: int,
                               refresh_sec: int, buy_chore_: ChoreLedgerBaseModel,
                               sell_chore_: ChoreLedgerBaseModel,
                               buy_fill_ledger_: DealsLedgerBaseModel, sell_fill_ledger_: DealsLedgerBaseModel,
                               expected_buy_chore_snapshot_: ChoreSnapshotBaseModel,
                               expected_sell_chore_snapshot_: ChoreSnapshotBaseModel,
                               expected_symbol_side_snapshot_: List[SymbolSideSnapshotBaseModel],
                               pair_plan_: PairPlanBaseModel, expected_plan_limits_: PlanLimits,
                               expected_start_status_: PlanStatus, expected_plan_brief_: PlanBriefBaseModel,
                               last_barter_fixture_list: List[Dict],
                               symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                               market_depth_basemodel_list: List[MarketDepthBaseModel],
                               is_non_systematic_run: bool = False):
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_test_wait = 4 * refresh_sec
    active_pair_plan, executor_web_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_start_status_))
    print(f"Activated Plan: {active_pair_plan}")
    buy_symbol = active_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
    sell_symbol = active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id

    plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional = 0, 0, 0, 0
    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    chore_id = None
    cxl_chore_id = None
    expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
    expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol
    expected_plan_brief_obj = copy.deepcopy(expected_plan_brief_)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.security.sec_id = buy_symbol
    expected_plan_brief_obj.pair_sell_side_bartering_brief.security.sec_id = sell_symbol
    expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
    expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol
    expected_plan_status = copy.deepcopy(expected_start_status_)

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

    for loop_count in range(1, total_loop_count + 1):
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_chore_snapshot = copy.deepcopy(expected_sell_chore_snapshot_)
        expected_sell_chore_snapshot.chore_brief.security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.security.inst_type = None
        expected_sell_chore_snapshot.chore_brief.bartering_security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        # required to make buy side tob latest so that when top update reaches both side are new last_update_date_time
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)
        # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)

        if not is_non_systematic_run:
            # Waiting for tob to trigger place chore
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(120, sell_symbol,
                                                       sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(95, 105)
            px = random.randint(100, 110)
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client, sell_inst_type)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        create_sell_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        chore_id = placed_chore_ledger.chore.chore_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_sell_chore_computes_before_buys(loop_count, chore_id,
                                                     sell_symbol, placed_chore_ledger, expected_sell_chore_snapshot,
                                                     expected_sell_symbol_side_snapshot,
                                                     expected_buy_symbol_side_snapshot,
                                                     active_pair_plan,
                                                     expected_plan_limits_, expected_plan_status,
                                                     expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px, placed_chore_ledger.chore.qty, placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id, placed_chore_ledger.chore.underlying_account)

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_sell_chore_ack_receive(placed_chore_ledger_obj_ack_response,
                                      expected_sell_chore_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed chore ACK of chore_id {chore_id}")

        sell_fill_ledger_obj = copy.deepcopy(sell_fill_ledger_)
        sell_fill_ledger_obj.fill_qty = random.randint(48, 53)
        sell_fill_ledger_obj.fill_px = random.randint(100, 110)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, sell_fill_ledger_obj.fill_px, sell_fill_ledger_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_sell_chore_before_buys(
            sell_symbol, placed_fill_ledger_obj,
            expected_sell_chore_snapshot, expected_sell_symbol_side_snapshot,
            expected_buy_symbol_side_snapshot, active_pair_plan,
            expected_plan_limits_, expected_plan_status, expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore FILL")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           sell_symbol, executor_web_client,
                                                                           last_chore_id=cxl_chore_id)
        cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on placed chore by cxl_req from residual removal
        check_cxl_receive_for_placed_sell_chore_before_buy(sell_symbol, cxl_chore_ledger,
                                                           expected_sell_chore_snapshot,
                                                           expected_sell_symbol_side_snapshot,
                                                           expected_buy_symbol_side_snapshot,
                                                           active_pair_plan,
                                                           expected_plan_limits_, expected_plan_status,
                                                           expected_plan_brief_obj, executor_web_client)

        plan_sell_notional += expected_sell_chore_snapshot.fill_notional
        plan_sell_fill_notional += expected_sell_chore_snapshot.fill_notional

    chore_id = None
    cxl_chore_id = None
    for loop_count in range(1, total_loop_count + 1):
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_chore_snapshot = copy.deepcopy(expected_buy_chore_snapshot_)
        expected_buy_chore_snapshot.chore_brief.security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.security.inst_type = None
        expected_buy_chore_snapshot.chore_brief.bartering_security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {leg1_symbol}, sell_symbol: {sell_symbol}")

        # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)

        if not is_non_systematic_run:
            # Waiting for tob to trigger place chore
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(100, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(85, 95)
            px = random.randint(95, 100)
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client, buy_inst_type)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        chore_id = placed_chore_ledger.chore.chore_id
        create_buy_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_buy_chore_computes_after_sells(loop_count, chore_id, buy_symbol,
                                                    placed_chore_ledger, expected_buy_chore_snapshot,
                                                    expected_buy_symbol_side_snapshot,
                                                    expected_sell_symbol_side_snapshot, active_pair_plan,
                                                    expected_plan_limits_, expected_plan_status,
                                                    expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px, placed_chore_ledger.chore.qty, placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id, placed_chore_ledger.chore.underlying_account)

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_buy_chore_ack_receive(placed_chore_ledger_obj_ack_response, expected_buy_chore_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore ACK of chore_id {chore_id}")

        buy_fill_ledger_obj = copy.deepcopy(buy_fill_ledger_)
        buy_fill_ledger_obj.fill_qty = random.randint(50, 55)
        buy_fill_ledger_obj.fill_px = random.randint(95, 100)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, buy_fill_ledger_obj.fill_px, buy_fill_ledger_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_buy_chore_after_all_sells(loop_count, chore_id, buy_symbol,
                                                                placed_fill_ledger_obj,
                                                                expected_buy_chore_snapshot,
                                                                expected_buy_symbol_side_snapshot,
                                                                expected_sell_symbol_side_snapshot,
                                                                active_pair_plan, expected_plan_limits_,
                                                                expected_plan_status, expected_plan_brief_obj,
                                                                executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore FILL of chore_id {chore_id}")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           buy_symbol, executor_web_client,
                                                                           last_chore_id=cxl_chore_id)
        cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_buy_chore_after_all_sells(buy_symbol,
                                                               cxl_chore_ledger, expected_buy_chore_snapshot,
                                                               expected_buy_symbol_side_snapshot,
                                                               expected_sell_symbol_side_snapshot,
                                                               active_pair_plan, expected_plan_limits_,
                                                               expected_plan_status, expected_plan_brief_obj,
                                                               executor_web_client)

        plan_buy_notional += expected_buy_chore_snapshot.fill_notional
        plan_buy_fill_notional += expected_buy_chore_snapshot.fill_notional
    return plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional


def get_pair_plan_from_symbol(symbol: str):
    pair_plan_obj_list = email_book_service_native_web_client.get_all_pair_plan_client()
    for pair_plan_obj in pair_plan_obj_list:
        if pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id == symbol or \
                pair_plan_obj.pair_plan_params.plan_leg2.sec.sec_id == symbol:
            return pair_plan_obj


def get_chore_snapshot_from_chore_id(chore_id, executor_web_client: StreetBookServiceHttpClient
                                     ) -> ChoreSnapshotBaseModel | None:
    chore_snapshot_list = executor_web_client.get_all_chore_snapshot_client(-100)
    expected_chore_snapshot: ChoreSnapshotBaseModel | None = None
    for chore_snapshot in chore_snapshot_list:
        if chore_snapshot.chore_brief.chore_id == chore_id:
            expected_chore_snapshot = chore_snapshot
            break
    assert expected_chore_snapshot is not None, "Expected chore_snapshot as not None but received as None"
    return expected_chore_snapshot


def create_fx_symbol_overview():
    fx_symbol_overview = fx_symbol_overview_obj()
    created_fx_symbol_overview = (
        email_book_service_native_web_client.create_fx_symbol_overview_client(fx_symbol_overview))
    fx_symbol_overview.id = created_fx_symbol_overview.id
    fx_symbol_overview.last_update_date_time = created_fx_symbol_overview.last_update_date_time
    assert created_fx_symbol_overview == fx_symbol_overview, \
        f"Mismatch symbol_overview: expected {fx_symbol_overview}, received {created_fx_symbol_overview}"


def verify_rej_chores(check_ack_to_reject_chores: bool, last_chore_id: int | None,
                      check_chore_event: ChoreEventType, symbol: str,
                      executor_web_client: StreetBookServiceHttpClient) -> str:
    # internally checks chore_ledger is not None else raises assert exception internally
    latest_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(check_chore_event, symbol,
                                                                          executor_web_client,
                                                                          last_chore_id=last_chore_id)
    last_chore_id = latest_chore_ledger.chore.chore_id

    if check_ack_to_reject_chores:
        if check_chore_event not in [ChoreEventType.OE_INT_REJ, ChoreEventType.OE_BRK_REJ, ChoreEventType.OE_EXH_REJ]:
            # internally checks deals_ledger is not None else raises assert exception
            latest_fill_ledger = get_latest_fill_ledger_from_chore_id(latest_chore_ledger.chore.chore_id,
                                                                        executor_web_client)

    chore_snapshot = get_chore_snapshot_from_chore_id(last_chore_id,
                                                      executor_web_client)
    assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
        "Unexpected chore_snapshot.chore_status: expected ChoreStatusType.OE_DOD, " \
        f"received {chore_snapshot.chore_status}"

    return last_chore_id


def handle_rej_chore_test(buy_symbol, sell_symbol, created_pair_plan, expected_plan_limits_,
                          last_barter_fixture_list, max_loop_count_per_side,
                          check_ack_to_reject_chores: bool, executor_web_client: StreetBookServiceHttpClient,
                          config_dict, residual_wait_secs):
    # explicitly setting waived_initial_chores to 10 for this test case
    expected_plan_limits_.cancel_rate.waived_initial_chores = 10

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, created_pair_plan))

    # buy deals check
    continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(buy_symbol, config_dict)
    buy_chore_count = 0
    buy_special_chore_count = 0
    special_case_counter = 0
    last_id = None
    buy_rej_last_id = None
    for loop_count in range(1, max_loop_count_per_side + 1):
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(created_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        time.sleep(2)  # delay for chore to get placed

        if buy_chore_count < continues_chore_count:
            check_chore_event = ChoreEventType.OE_CXL_ACK
            buy_chore_count += 1
        else:
            if buy_special_chore_count < continues_special_chore_count:
                special_case_counter += 1
                if special_case_counter % 2 == 0:
                    check_chore_event = ChoreEventType.OE_BRK_REJ
                else:
                    check_chore_event = ChoreEventType.OE_EXH_REJ
                buy_special_chore_count += 1
            else:
                check_chore_event = ChoreEventType.OE_CXL_ACK
                buy_chore_count = 1
                buy_special_chore_count = 0

        # internally contains assert checks
        last_id = verify_rej_chores(check_ack_to_reject_chores, last_id, check_chore_event,
                                    buy_symbol, executor_web_client)

        if check_chore_event in [ChoreEventType.OE_BRK_REJ, ChoreEventType.OE_EXH_REJ]:
            buy_rej_last_id = last_id

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        time.sleep(residual_wait_secs)  # to start sell after buy is completely done

    # sell deals check
    continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(sell_symbol, config_dict)
    last_id = None
    sell_rej_last_id = None
    sell_chore_count = 0
    sell_special_chore_count = 0
    for loop_count in range(1, max_loop_count_per_side + 1):
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], created_pair_plan.cpp_port)
        update_tob_through_market_depth_to_place_sell_chore(created_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)
        time.sleep(2)  # delay for chore to get placed

        if sell_chore_count < continues_chore_count:
            check_chore_event = ChoreEventType.OE_CXL_ACK
            sell_chore_count += 1
        else:
            if sell_special_chore_count < continues_special_chore_count:
                special_case_counter += 1
                if special_case_counter % 2 == 0:
                    check_chore_event = ChoreEventType.OE_BRK_REJ
                else:
                    check_chore_event = ChoreEventType.OE_EXH_REJ
                sell_special_chore_count += 1
            else:
                check_chore_event = ChoreEventType.OE_CXL_ACK
                sell_chore_count = 1
                sell_special_chore_count = 0

        # internally contains assert checks
        last_id = verify_rej_chores(check_ack_to_reject_chores, last_id, check_chore_event,
                                    sell_symbol, executor_web_client)

        if check_chore_event in [ChoreEventType.OE_BRK_REJ, ChoreEventType.OE_EXH_REJ]:
            sell_rej_last_id = last_id
    return buy_rej_last_id, sell_rej_last_id


def verify_cxl_rej(last_cxl_chore_id: str | None, last_cxl_rej_chore_id: str | None,
                   check_chore_event: ChoreEventType, symbol: str,
                   executor_web_client: StreetBookServiceHttpClient,
                   expected_reverted_chore_status: ChoreStatusType) -> Tuple[str, str]:
    if check_chore_event == "REJ":
        # internally checks chore_ledger is not None else raises assert exception internally
        latest_cxl_rej_chore_ledger = \
            get_latest_chore_ledger_with_events_and_symbol([ChoreEventType.OE_CXL_INT_REJ,
                                                             ChoreEventType.OE_CXL_BRK_REJ,
                                                             ChoreEventType.OE_CXL_EXH_REJ], symbol,
                                                            executor_web_client,
                                                            last_chore_id=last_cxl_rej_chore_id)
        last_cxl_rej_chore_id = latest_cxl_rej_chore_ledger.chore.chore_id

        chore_snapshot = get_chore_snapshot_from_chore_id(latest_cxl_rej_chore_ledger.chore.chore_id,
                                                          executor_web_client)
        assert chore_snapshot.chore_status == expected_reverted_chore_status, \
            f"Unexpected chore_snapshot.chore_status: expected {expected_reverted_chore_status}, " \
            f"received {chore_snapshot.chore_status}"

    # checks chore_ledger is not None else raises assert exception internally
    latest_cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK, symbol,
                                                                              executor_web_client,
                                                                              last_chore_id=last_cxl_chore_id)
    last_cxl_chore_id = latest_cxl_chore_ledger.chore.chore_id

    return last_cxl_chore_id, last_cxl_rej_chore_id


def create_deals_for_underlying_account_test(buy_symbol: str, sell_symbol: str, active_pair_plan: PairPlanBaseModel,
                                             tob_last_update_date_time_tracker: DateTime | None,
                                             chore_id: str | None, underlying_account_prefix: str, side: Side,
                                             executor_web_client: StreetBookServiceHttpClient,
                                             bid_buy_top_market_depth: MarketDepthBaseModel,
                                             ask_sell_top_market_depth: MarketDepthBaseModel,
                                             last_barter_fixture_list: List[Dict]):
    loop_count = 1
    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
    if side == Side.BUY:
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        symbol = buy_symbol
        wait_stop_px = 100
    else:
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)

        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)
        symbol = sell_symbol
        wait_stop_px = 120

    # Waiting for tob to trigger place chore
    tob_last_update_date_time_tracker = \
        wait_for_get_new_chore_placed_from_tob(wait_stop_px, symbol, tob_last_update_date_time_tracker,
                                               side, executor_web_client)

    placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                          symbol, executor_web_client,
                                                                          last_chore_id=chore_id)
    chore_id = placed_chore_ledger.chore.chore_id

    executor_web_client.barter_simulator_process_chore_ack_query_client(
        chore_id, placed_chore_ledger.chore.px,
        placed_chore_ledger.chore.qty,
        placed_chore_ledger.chore.side,
        placed_chore_ledger.chore.security.sec_id,
        placed_chore_ledger.chore.underlying_account)

    deals_count = 6
    fill_px = 100
    fill_qty = 5
    for loop_count in range(deals_count):
        if loop_count + 1 <= (deals_count / 2):
            underlying_account = f"{underlying_account_prefix}_1"
        else:
            underlying_account = f"{underlying_account_prefix}_2"
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, fill_px, fill_qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id, underlying_account)
    return tob_last_update_date_time_tracker, chore_id


def verify_unsolicited_cxl_chores(last_id: str | None,
                                  check_chore_event: ChoreEventType, symbol: str,
                                  executor_web_client: StreetBookServiceHttpClient) -> str:
    # internally checks chore_ledger is not None else raises assert exception internally
    if check_chore_event == ChoreEventType.OE_CXL:
        latest_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(check_chore_event, symbol,
                                                                              executor_web_client,
                                                                              last_chore_id=last_id)
    else:
        # checking no latest chore with OE_CXL
        latest_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL, symbol,
                                                                              executor_web_client,
                                                                              expect_no_chore=True,
                                                                              last_chore_id=last_id)

    return latest_chore_ledger.chore.chore_id


def handle_unsolicited_cxl_for_sides(symbol: str, last_id: str, last_cxl_ack_id: str, chore_count: int,
                                     continues_chore_count: int, cxl_count: int, continues_unsolicited_cxl_count: int,
                                     executor_web_client: StreetBookServiceHttpClient):
    if chore_count < continues_chore_count:
        check_chore_event = ChoreEventType.OE_CXL
        chore_count += 1
        time.sleep(10)
    else:
        if cxl_count < continues_unsolicited_cxl_count:
            check_chore_event = ChoreEventType.OE_UNSOL_CXL
            cxl_count += 1
        else:
            check_chore_event = ChoreEventType.OE_CXL
            chore_count = 1
            cxl_count = 0
            time.sleep(10)

    # internally contains assert checks
    last_id = verify_unsolicited_cxl_chores(last_id, check_chore_event, symbol, executor_web_client)
    if check_chore_event != ChoreEventType.OE_UNSOL_CXL:
        latest_cxl_ack_obj = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                            symbol, executor_web_client,
                                                                            last_chore_id=last_cxl_ack_id)
        last_cxl_ack_id = latest_cxl_ack_obj.chore.chore_id

    return last_id, last_cxl_ack_id, chore_count, cxl_count


def handle_unsolicited_cxl(buy_symbol, sell_symbol, active_pair_plan, last_barter_fixture_list, max_loop_count_per_side,
                           executor_web_client: StreetBookServiceHttpClient, config_dict, residual_wait_sec):
    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

    # buy deals check
    continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(buy_symbol, config_dict)
    buy_chore_count = 0
    buy_cxl_chore_count = 0
    last_id = None
    last_cxl_ack_id = None
    for loop_count in range(1, max_loop_count_per_side + 1):
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
        time.sleep(2)  # delay for chore to get placed

        last_id, last_cxl_ack_id, buy_chore_count, buy_cxl_chore_count = \
            handle_unsolicited_cxl_for_sides(buy_symbol, last_id, last_cxl_ack_id,
                                             buy_chore_count, continues_chore_count,
                                             buy_cxl_chore_count, continues_special_chore_count,
                                             executor_web_client)

    if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
        time.sleep(residual_wait_sec)   # to start sell after buy is completely done

    # sell deals check
    continues_chore_count, continues_special_chore_count = get_continuous_chore_configs(sell_symbol, config_dict)
    sell_chore_count = 0
    sell_cxl_chore_count = 0
    last_id = None
    last_cxl_ack_id = None
    for loop_count in range(1, max_loop_count_per_side + 1):
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)

        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)
        time.sleep(2)  # delay for chore to get placed

        last_id, last_cxl_ack_id, sell_chore_count, sell_cxl_chore_count = \
            handle_unsolicited_cxl_for_sides(sell_symbol, last_id, last_cxl_ack_id,
                                             sell_chore_count, continues_chore_count,
                                             sell_cxl_chore_count, continues_special_chore_count,
                                             executor_web_client)


def get_partial_allowed_ack_qty(symbol: str, qty: int, config_dict: Dict):
    symbol_configs = get_symbol_configs(symbol, config_dict)

    if symbol_configs is not None:
        if (ack_percent := symbol_configs.get("ack_percent")) is not None:
            qty = int((ack_percent / 100) * qty)
    return qty


def handle_partial_ack_checks(symbol: str, new_chore_id: str, acked_chore_id: str,
                              executor_web_client: StreetBookServiceHttpClient, config_dict):
    new_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                       symbol, executor_web_client,
                                                                       last_chore_id=new_chore_id)
    new_chore_id = new_chore_ledger.chore.chore_id
    partial_ack_qty = get_partial_allowed_ack_qty(symbol, new_chore_ledger.chore.qty, config_dict)

    ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                       symbol, executor_web_client,
                                                                       last_chore_id=acked_chore_id)
    acked_chore_id = ack_chore_ledger.chore.chore_id
    assert ack_chore_ledger.chore.qty == partial_ack_qty, f"Mismatch partial_ack_qty: expected {partial_ack_qty}, " \
                                                           f"received {ack_chore_ledger.chore.qty}"

    return new_chore_id, acked_chore_id, partial_ack_qty


def underlying_pre_requisites_for_limit_test(buy_sell_symbol_list, pair_plan_, expected_plan_limits_,
                                             expected_start_status_, symbol_overview_obj_list,
                                             last_barter_fixture_list, market_depth_basemodel_list,
                                             plan_mode: PlanMode | None = None,
                                             leg1_side: Side | None = None, leg2_side: Side | None = None):
    leg1_symbol = buy_sell_symbol_list[0][0]
    leg2_symbol = buy_sell_symbol_list[0][1]
    buy_symbol = leg1_symbol
    sell_symbol = leg2_symbol
    if leg1_side and leg2_side and leg1_side == Side.SELL:
        buy_symbol = leg2_symbol
        sell_symbol = leg1_symbol

    activated_plan, executor_http_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, plan_mode=plan_mode,
                                           leg1_side=leg1_side, leg2_side=leg2_side))

    # buy test
    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, activated_plan.cpp_port)
    loop_count = 1
    return leg1_symbol, leg2_symbol, activated_plan, executor_http_client


def check_alert_str_in_contact_alert(check_str: str, assert_fail_msg: str):
    contact_alerts = log_book_web_client.get_all_contact_alert_client()
    for alert in contact_alerts:
        if re.search(check_str, alert.alert_brief):
            return alert
    else:
        print(f"Can't find {check_str=!r} in {contact_alerts=}")
        assert False, assert_fail_msg


def check_alert_str_in_plan_alerts_n_contact_alerts(activated_pair_plan_id: int, check_str: str,
                                                       assert_fail_msg: str):
    # Checking alert in plan_alert
    plan_alerts = log_book_web_client.filtered_plan_alert_by_plan_id_query_client(activated_pair_plan_id)
    for alert in plan_alerts:
        if re.search(check_str, alert.alert_brief):
            return alert
    else:
        # Checking alert in contact_alert if reason failed to add in plan_alert
        print(f"Can't find {check_str=!r} in {plan_alerts=}")
        return check_alert_str_in_contact_alert(check_str, assert_fail_msg)


def get_inst_type(side: Side, pair_plan: PairPlanBaseModel):
    buy_inst_type: InstrumentType = InstrumentType.CB if (
            pair_plan.pair_plan_params.plan_leg1.side == Side.BUY) else InstrumentType.EQT
    sell_inst_type: InstrumentType = InstrumentType.EQT if buy_inst_type == InstrumentType.CB else InstrumentType.CB
    inst_type: InstrumentType = buy_inst_type if side == Side.BUY else sell_inst_type
    return inst_type


def handle_place_chore_and_check_str_in_alert_for_executor_limits(symbol: str, side: Side, px: float, qty: int,
                                                                  check_str: str, assert_fail_msg: str,
                                                                  active_pair_plan: PairPlanBaseModel,
                                                                  executor_web_client: StreetBookServiceHttpClient,
                                                                  last_chore_id: str | None = None):
    activated_pair_plan_id = active_pair_plan.id
    inst_type: InstrumentType = get_inst_type(side, active_pair_plan)
    # placing new non-systematic new_chore
    place_new_chore(symbol, side, px, qty, executor_web_client, inst_type)
    print(f"symbol: {symbol}, Created new_chore obj")

    new_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW, symbol,
                                                                       executor_web_client,
                                                                       expect_no_chore=True,
                                                                       last_chore_id=last_chore_id)
    time.sleep(5)
    return check_alert_str_in_plan_alerts_n_contact_alerts(activated_pair_plan_id, check_str, assert_fail_msg)


def handle_test_for_plan_pause_on_less_consumable_cxl_qty_without_fill(buy_symbol, sell_symbol, active_pair_plan,
                                                                        last_barter_fixture_list, side: Side,
                                                                        executor_web_client:
                                                                        StreetBookServiceHttpClient,
                                                                        last_cxl_chore_id=None):

    active_pair_plan_id = active_pair_plan.id
    inst_type: InstrumentType = get_inst_type(side, active_pair_plan)

    # buy test
    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

    check_symbol = buy_symbol if side == Side.BUY else sell_symbol

    px = 100
    qty = 90
    check_str = f"Consumable cxl qty can't be < 0, currently is .* for symbol {check_symbol}"
    assert_fail_message = f"Could not find any alert with {check_str=!r} in plan or contact alerts"
    # placing new non-systematic new_chore
    place_new_chore(check_symbol, side, px, qty, executor_web_client, inst_type)
    print(f"symbol: {check_symbol}, Created new_chore obj")

    new_chore_ledger = get_latest_chore_ledger_with_events_and_symbol([ChoreEventType.OE_CXL_ACK,
                                                                         ChoreEventType.OE_UNSOL_CXL], check_symbol,
                                                                        executor_web_client,
                                                                        last_chore_id=last_cxl_chore_id)
    time.sleep(5)
    check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan_id, check_str, assert_fail_message)

    # checking plan pause
    pair_plan = email_book_service_native_web_client.get_pair_plan_client(active_pair_plan_id)
    assert pair_plan.plan_state == PlanState.PlanState_PAUSED, \
        f"Mismatched plan state, expected: PAUSED, found {pair_plan.plan_state}"


def handle_test_for_plan_pause_on_less_consumable_cxl_qty_with_fill(
        buy_symbol, sell_symbol, active_pair_plan, last_barter_fixture_list,
        side, executor_web_client: StreetBookServiceHttpClient,
        last_cxl_chore_id=None):

    active_pair_plan_id = active_pair_plan.id
    inst_type: InstrumentType = get_inst_type(side, active_pair_plan)

    # buy test
    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)

    check_symbol = buy_symbol if side == Side.BUY else sell_symbol

    px = 100
    qty = 90
    check_str = f"Consumable cxl qty can't be < 0, currently is .* for symbol {check_symbol}"
    assert_fail_message = f"Could not find any alert containing: {check_str}"
    # placing new non-systematic new_chore
    place_new_chore(check_symbol, side, px, qty, executor_web_client, inst_type)
    print(f"symbol: {check_symbol}, Created new_chore obj")

    ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, check_symbol,
                                                                       executor_web_client)
    cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK, check_symbol,
                                                                       executor_web_client,
                                                                       last_chore_id=last_cxl_chore_id)

    time.sleep(5)
    check_alert_str_in_plan_alerts_n_contact_alerts(active_pair_plan_id, check_str, assert_fail_message)


def get_symbol_configs(symbol: str, config_dict: Dict) -> Dict | None:
    """
    WARNING : This Function is duplicate test function of what we have in barter simulator to keep test
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
    ATTENTION: This Function is dummy of original impl present in barter_executor, keep it sync with original
    """
    symbol_configs = get_symbol_configs(check_symbol, config_dict)
    partial_filled_qty: int | None = None
    if symbol_configs is not None:
        if (fill_percent := symbol_configs.get("fill_percent")) is not None:
            partial_filled_qty = int((fill_percent / 100) * qty)
    return partial_filled_qty


def underlying_handle_simulated_partial_deals_test(loop_count, check_symbol, buy_symbol,
                                                   sell_symbol, last_barter_fixture_list,
                                                   last_chore_id, config_dict, active_pair_plan,
                                                   executor_web_client: StreetBookServiceHttpClient):
    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
    if check_symbol == buy_symbol:
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)
    else:
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)

        update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)

    chore_ack_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                       check_symbol, executor_web_client,
                                                                       last_chore_id=last_chore_id)
    last_chore_id = chore_ack_ledger.chore.chore_id
    time.sleep(5)

    # ATTENTION: Below code is dummy of original impl present in barter_executor, keep it sync with original
    partial_filled_qty = get_partial_allowed_fill_qty(check_symbol, config_dict, chore_ack_ledger.chore.qty)

    latest_fill_ledger = get_latest_fill_ledger_from_chore_id(last_chore_id, executor_web_client)
    assert latest_fill_ledger.fill_qty == partial_filled_qty, f"fill_qty mismatch: expected {partial_filled_qty}, " \
                                                               f"received {latest_fill_ledger.fill_qty}"
    return last_chore_id, partial_filled_qty


def underlying_handle_simulated_multi_partial_deals_test(loop_count, check_symbol, buy_symbol,
                                                         sell_symbol, active_pair_plan, last_barter_fixture_list,
                                                         last_chore_id,
                                                         executor_web_client: StreetBookServiceHttpClient,
                                                         config_dict, fill_id: str | None = None):
    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
    if check_symbol == buy_symbol:
        px = 100
        qty = 90
        place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client, buy_inst_type)
    else:
        px = 110
        qty = 95
        place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client, sell_inst_type)

    new_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                       check_symbol, executor_web_client,
                                                                       last_chore_id=last_chore_id)
    last_chore_id = new_chore_ledger.chore.chore_id

    # ATTENTION: Below code is dummy of original impl present in barter_executor, keep it sync with original
    partial_filled_qty = get_partial_allowed_fill_qty(check_symbol, config_dict, new_chore_ledger.chore.qty)

    deals_count = get_symbol_configs(check_symbol, config_dict).get("total_fill_count")
    time.sleep(5)
    time_out_loop_count = 5
    latest_fill_ledgers = []
    for _ in range(time_out_loop_count):
        latest_fill_ledgers = get_fill_ledgers_for_chore_id(last_chore_id, executor_web_client)
        if loop_count == deals_count:
            break
        time.sleep(2)

    assert deals_count == len(latest_fill_ledgers), f"Mismatch numbers of fill for chore_id {last_chore_id}, " \
                                                     f"expected {deals_count} received {len(latest_fill_ledgers)}"

    for latest_fill_ledger in latest_fill_ledgers:
        assert latest_fill_ledger.fill_qty == partial_filled_qty, f"Mismatch partial_filled_qty: " \
                                                                   f"expected {partial_filled_qty}, received " \
                                                                   f"{latest_fill_ledger.fill_px}"
    return last_chore_id, partial_filled_qty


def plan_done_after_exhausted_consumable_notional(
        leg_1_symbol, leg_2_symbol, pair_plan_, expected_plan_limits_,
        expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
        refresh_sec, side_to_check: Side, leg_1_side: Side | None = None, leg_2_side: Side | None = None):

    if leg_1_side is None or leg_2_side is None:
        leg_1_side = Side.BUY
        leg_2_side = Side.SELL

    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec
    created_pair_plan, executor_http_client = (
        create_pre_chore_test_requirements(leg_1_symbol, leg_2_symbol, pair_plan_, expected_plan_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, leg1_side=leg_1_side,
                                           leg2_side=leg_2_side))

    if leg_1_side == Side.BUY:
        buy_symbol = leg_1_symbol
        sell_symbol = leg_2_symbol
        buy_inst_type = InstrumentType.CB
        sell_inst_type = InstrumentType.EQT
    else:
        buy_symbol = leg_2_symbol
        sell_symbol = leg_1_symbol
        buy_inst_type = InstrumentType.EQT
        sell_inst_type = InstrumentType.CB

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 95
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        executor_http_client.barter_simulator_reload_config_query_client()

        # Positive Check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
        if side_to_check == Side.BUY:
            px = 98
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
            check_symbol = buy_symbol
        else:
            px = 96
            qty = 95
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)
            check_symbol = sell_symbol
        time.sleep(2)  # delay for chore to get placed

        ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, check_symbol,
                                                                           executor_http_client, assert_code=1)
        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_ledger.chore.chore_id, executor_http_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_ACKED, "ChoreStatus mismatched: expected status " \
                                                                        f"ChoreStatusType.OE_ACKED received " \
                                                                        f"{chore_snapshot.chore_status}"
        time.sleep(residual_wait_sec)  # wait to get buy chore residual

        # Negative Check
        # Next placed chore must not get placed, instead it should find consumable_notional as exhausted for further
        # chores and should come out of executor run and must set plan_state to PlanState_DONE

        # buy deals check
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
        if side_to_check == Side.BUY:
            px = 98
            qty = 90
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_http_client, buy_inst_type)
        else:
            px = 92
            qty = 95
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_http_client, sell_inst_type)
        time.sleep(2)  # delay for chore to get placed
        ack_chore_ledger = (
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW, check_symbol, executor_http_client,
                                                           last_chore_id=ack_chore_ledger.chore.chore_id,
                                                           expect_no_chore=True, assert_code=3))
        pair_plan = email_book_service_native_web_client.get_pair_plan_client(created_pair_plan.id)
        assert pair_plan.plan_state == PlanState.PlanState_PAUSED, (
            f"Mismatched plan_state, expected {PlanState.PlanState_PAUSED}, received {pair_plan.plan_state}")

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
    admin_control_obj: AdminControlBaseModel = AdminControlBaseModel.from_kwargs(
        command_type=CommandType.CLEAR_STRAT, datetime=DateTime.utcnow())
    email_book_service_native_web_client.create_admin_control_client(admin_control_obj)


def clear_cache_in_model():
    admin_control_obj: AdminControlBaseModel = AdminControlBaseModel.from_kwargs(
        command_type=CommandType.RESET_STATE, datetime=DateTime.utcnow())
    email_book_service_native_web_client.create_admin_control_client(admin_control_obj)
    post_book_service_http_client.reload_cache_query_client()


def append_csv_file(file_name: str, records: List[List[any]]):
    with open(file_name, "a") as csv_file:
        list_writer = writer(csv_file)
        record: List[any]
        for record in records:
            list_writer.writerow(record)


def handle_test_buy_sell_pair_chore(buy_symbol: str, sell_symbol: str, total_loop_count: int,
                                    refresh_sec: int, buy_chore_: ChoreLedgerBaseModel,
                                    sell_chore_: ChoreLedgerBaseModel,
                                    buy_fill_ledger_: DealsLedgerBaseModel, sell_fill_ledger_: DealsLedgerBaseModel,
                                    expected_buy_chore_snapshot_: ChoreSnapshotBaseModel,
                                    expected_sell_chore_snapshot_: ChoreSnapshotBaseModel,
                                    expected_symbol_side_snapshot_: List[SymbolSideSnapshotBaseModel],
                                    pair_plan_: PairPlanBaseModel, expected_plan_limits_: PlanLimits,
                                    expected_start_status_: PlanStatus, expected_plan_brief_: PlanBriefBaseModel,
                                    last_barter_fixture_list: List[Dict],
                                    symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                    market_depth_basemodel_list: List[MarketDepthBaseModel],
                                    is_non_systematic_run: bool = False):
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_test_wait = 4 * refresh_sec
    active_pair_plan, executor_web_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_start_status_))
    print(f"Created Plan: {active_pair_plan}")

    plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional = 0, 0, 0, 0
    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    chore_id = None
    cxl_chore_id = None
    expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
    expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol
    expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
    expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol
    expected_plan_status = copy.deepcopy(expected_start_status_)
    expected_plan_brief_obj = copy.deepcopy(expected_plan_brief_)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.security.sec_id = buy_symbol
    expected_plan_brief_obj.pair_sell_side_bartering_brief.security.sec_id = sell_symbol

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    for loop_count in range(1, total_loop_count + 1):
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_chore_snapshot = copy.deepcopy(expected_buy_chore_snapshot_)
        expected_buy_chore_snapshot.chore_brief.security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.security.inst_type = None
        expected_buy_chore_snapshot.chore_brief.bartering_security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        if not is_non_systematic_run:
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                               ask_sell_top_market_depth)

            # Waiting for tob to trigger place chore
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(100, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(85, 95)
            px = random.randint(95, 100)
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client, buy_inst_type)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        chore_id = placed_chore_ledger.chore.chore_id
        create_buy_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_buy_chore_computes_before_all_sells(
            loop_count, chore_id, buy_symbol,
            placed_chore_ledger, expected_buy_chore_snapshot,
            expected_buy_symbol_side_snapshot,
            expected_sell_symbol_side_snapshot,
            active_pair_plan,
            expected_plan_limits_, expected_plan_status,
            expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px,
            placed_chore_ledger.chore.qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id,
            placed_chore_ledger.chore.underlying_account
        )

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_buy_chore_ack_receive(placed_chore_ledger_obj_ack_response, expected_buy_chore_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore ACK of chore_id {chore_id}")

        buy_fill_ledger_obj = copy.deepcopy(buy_fill_ledger_)
        buy_fill_ledger_obj.fill_qty = random.randint(50, 55)
        buy_fill_ledger_obj.fill_px = random.randint(95, 100)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, buy_fill_ledger_obj.fill_px, buy_fill_ledger_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_buy_chore_before_sells(
            buy_symbol, placed_fill_ledger_obj,
            expected_buy_chore_snapshot, expected_buy_symbol_side_snapshot,
            expected_sell_symbol_side_snapshot,
            active_pair_plan,
            expected_plan_limits_, expected_plan_status,
            expected_plan_brief_obj,
            executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore FILL of chore_id {chore_id}")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           buy_symbol, executor_web_client,
                                                                           last_chore_id=cxl_chore_id)
        cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on placed chore by cxl_req from residual removal
        check_cxl_receive_for_placed_buy_chore_before_sells(buy_symbol, cxl_chore_ledger,
                                                            expected_buy_chore_snapshot,
                                                            expected_buy_symbol_side_snapshot,
                                                            expected_sell_symbol_side_snapshot,
                                                            active_pair_plan,
                                                            expected_plan_limits_, expected_plan_status,
                                                            expected_plan_brief_obj, executor_web_client)

        plan_buy_notional += expected_buy_chore_snapshot.fill_notional
        plan_buy_fill_notional += expected_buy_chore_snapshot.fill_notional

        # handle sell chore
        chore_id = None
        cxl_chore_id = None

        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_chore_snapshot = copy.deepcopy(expected_sell_chore_snapshot_)
        expected_sell_chore_snapshot.chore_brief.security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.security.inst_type = None
        expected_sell_chore_snapshot.chore_brief.bartering_security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        if not is_non_systematic_run:
            # required to make buy side tob latest so that when top update reaches in test place chore function in
            # executor both side are new last_update_date_time
            run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                                bid_buy_top_market_depth)

            # Waiting for tob to trigger place chore
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(95, 105)
            px = random.randint(100, 110)
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client, sell_inst_type)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        create_sell_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        chore_id = placed_chore_ledger.chore.chore_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_sell_chore_computes_after_all_buys(
            loop_count, chore_id, sell_symbol, placed_chore_ledger, expected_sell_chore_snapshot,
            expected_sell_symbol_side_snapshot, expected_buy_symbol_side_snapshot, active_pair_plan,
            expected_plan_limits_, expected_plan_status,
            expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px,
            placed_chore_ledger.chore.qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id,
            placed_chore_ledger.chore.underlying_account)

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_sell_chore_ack_receive(placed_chore_ledger_obj_ack_response,
                                      expected_sell_chore_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed chore ACK of chore_id {chore_id}")

        sell_fill_ledger_obj = copy.deepcopy(sell_fill_ledger_)
        sell_fill_ledger_obj.fill_qty = random.randint(48, 53)
        sell_fill_ledger_obj.fill_px = random.randint(100, 110)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, sell_fill_ledger_obj.fill_px, sell_fill_ledger_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_sell_chore_after_all_buys(
            loop_count, chore_id, sell_symbol, placed_fill_ledger_obj,
            expected_sell_chore_snapshot, expected_sell_symbol_side_snapshot,
            expected_buy_symbol_side_snapshot, active_pair_plan, expected_plan_limits_,
            expected_plan_status, expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore FILL")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           sell_symbol, executor_web_client,
                                                                           last_chore_id=cxl_chore_id)
        cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_sell_chore_after_all_buys(sell_symbol,
                                                               cxl_chore_ledger, expected_sell_chore_snapshot,
                                                               expected_sell_symbol_side_snapshot,
                                                               expected_buy_symbol_side_snapshot,
                                                               active_pair_plan, expected_plan_limits_,
                                                               expected_plan_status, expected_plan_brief_obj,
                                                               executor_web_client)

        plan_sell_notional += expected_sell_chore_snapshot.fill_notional
        plan_sell_fill_notional += expected_sell_chore_snapshot.fill_notional
    return plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional


def handle_test_sell_buy_pair_chore(leg1_symbol: str, leg2_symbol: str, total_loop_count: int,
                                    refresh_sec: int, buy_chore_: ChoreLedgerBaseModel,
                                    sell_chore_: ChoreLedgerBaseModel,
                                    buy_fill_ledger_: DealsLedgerBaseModel, sell_fill_ledger_: DealsLedgerBaseModel,
                                    expected_buy_chore_snapshot_: ChoreSnapshotBaseModel,
                                    expected_sell_chore_snapshot_: ChoreSnapshotBaseModel,
                                    expected_symbol_side_snapshot_: List[SymbolSideSnapshotBaseModel],
                                    pair_plan_: PairPlanBaseModel, expected_plan_limits_: PlanLimits,
                                    expected_start_status_: PlanStatus, expected_plan_brief_: PlanBriefBaseModel,
                                    last_barter_fixture_list: List[Dict],
                                    symbol_overview_obj_list: List[SymbolOverviewBaseModel],
                                    market_depth_basemodel_list: List[MarketDepthBaseModel],
                                    is_non_systematic_run: bool = False):
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_test_wait = 4 * refresh_sec
    active_pair_plan, executor_web_client = (
        move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                       symbol_overview_obj_list, expected_plan_limits_,
                                                       expected_start_status_))
    print(f"Created Plan: {active_pair_plan}")
    buy_symbol = active_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
    sell_symbol = active_pair_plan.pair_plan_params.plan_leg1.sec.sec_id

    plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional = 0, 0, 0, 0
    buy_tob_last_update_date_time_tracker: DateTime | None = None
    sell_tob_last_update_date_time_tracker: DateTime | None = None
    chore_id = None
    sell_cxl_chore_id = None
    expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
    expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol
    expected_plan_status = copy.deepcopy(expected_start_status_)
    expected_plan_brief_obj = copy.deepcopy(expected_plan_brief_)
    expected_plan_brief_obj.pair_buy_side_bartering_brief.security.sec_id = buy_symbol
    expected_plan_brief_obj.pair_sell_side_bartering_brief.security.sec_id = sell_symbol
    expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
    expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, active_pair_plan))

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    for loop_count in range(1, total_loop_count + 1):
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Loop started")
        expected_sell_chore_snapshot = copy.deepcopy(expected_sell_chore_snapshot_)
        expected_sell_chore_snapshot.chore_brief.security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.security.inst_type = None
        expected_sell_chore_snapshot.chore_brief.bartering_security.sec_id = sell_symbol
        expected_sell_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        if not is_non_systematic_run:
            # required to make buy side tob latest so that when top update reaches in test place chore function in
            # executor both side are new last_update_date_time
            run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], active_pair_plan.cpp_port)
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            update_tob_through_market_depth_to_place_sell_chore(active_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                                bid_buy_top_market_depth)

            # Waiting for tob to trigger place chore
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(120, sell_symbol, sell_tob_last_update_date_time_tracker,
                                                       Side.SELL, executor_web_client)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received buy TOB")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(95, 105)
            px = random.randint(100, 110)
            place_new_chore(sell_symbol, Side.SELL, px, qty, executor_web_client, sell_inst_type)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        create_sell_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        chore_id = placed_chore_ledger.chore.chore_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_sell_chore_computes_before_buys(loop_count, chore_id, sell_symbol,
                                                     placed_chore_ledger, expected_sell_chore_snapshot,
                                                     expected_sell_symbol_side_snapshot,
                                                     expected_buy_symbol_side_snapshot, active_pair_plan,
                                                     expected_plan_limits_, expected_plan_status,
                                                     expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, placed_chore_ledger.chore.px, placed_chore_ledger.chore.qty, placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id, placed_chore_ledger.chore.underlying_account)

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, sell_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_sell_chore_ack_receive(placed_chore_ledger_obj_ack_response,
                                      expected_sell_chore_snapshot, executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, "
              f"Checked sell placed chore ACK of chore_id {chore_id}")

        sell_fill_ledger_obj = copy.deepcopy(sell_fill_ledger_)
        sell_fill_ledger_obj.fill_qty = random.randint(48, 53)
        sell_fill_ledger_obj.fill_px = random.randint(100, 110)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, sell_fill_ledger_obj.fill_px, sell_fill_ledger_obj.fill_qty,
            Side.SELL, sell_symbol, sell_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_sell_chore_before_buys(
            sell_symbol, placed_fill_ledger_obj,
            expected_sell_chore_snapshot, expected_sell_symbol_side_snapshot,
            expected_buy_symbol_side_snapshot, active_pair_plan,
            expected_plan_limits_, expected_plan_status, expected_plan_brief_obj,
            executor_web_client)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol}, Checked sell placed chore FILL")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           sell_symbol, executor_web_client,
                                                                           last_chore_id=sell_cxl_chore_id)
        sell_cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_sell_chore_before_buy(sell_symbol,
                                                           cxl_chore_ledger, expected_sell_chore_snapshot,
                                                           expected_sell_symbol_side_snapshot,
                                                           expected_buy_symbol_side_snapshot,
                                                           active_pair_plan, expected_plan_limits_,
                                                           expected_plan_status, expected_plan_brief_obj,
                                                           executor_web_client)

        plan_sell_notional += expected_sell_chore_snapshot.fill_notional
        plan_sell_fill_notional += expected_sell_chore_snapshot.fill_notional

        chore_id = None
        buy_cxl_chore_id = None
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Loop started at {start_time}")
        expected_buy_chore_snapshot = copy.deepcopy(expected_buy_chore_snapshot_)
        expected_buy_chore_snapshot.chore_brief.security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.security.inst_type = None
        expected_buy_chore_snapshot.chore_brief.bartering_security.sec_id = buy_symbol
        expected_buy_chore_snapshot.chore_brief.bartering_security.inst_type = None

        # placing chore
        current_itr_expected_buy_chore_ledger_ = copy.deepcopy(buy_chore_)
        current_itr_expected_buy_chore_ledger_.chore.security.sec_id = buy_symbol

        # running last barter once more before sell side
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, active_pair_plan.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")

        if not is_non_systematic_run:
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(active_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                               ask_sell_top_market_depth)

            # Waiting for tob to trigger place chore
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(100, buy_symbol,
                                                       buy_tob_last_update_date_time_tracker, Side.BUY,
                                                       executor_web_client)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(85, 95)
            px = random.randint(95, 100)
            place_new_chore(buy_symbol, Side.BUY, px, qty, executor_web_client, buy_inst_type)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol, executor_web_client,
                                                                              last_chore_id=chore_id)
        chore_id = placed_chore_ledger.chore.chore_id
        create_buy_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Received chore_ledger with {chore_id}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_buy_chore_computes_after_sells(loop_count, chore_id, buy_symbol,
                                                    placed_chore_ledger, expected_buy_chore_snapshot,
                                                    expected_buy_symbol_side_snapshot,
                                                    expected_sell_symbol_side_snapshot, active_pair_plan,
                                                    expected_plan_limits_, expected_plan_status,
                                                    expected_plan_brief_obj, executor_web_client)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore of chore_id {chore_id}")

        executor_web_client.barter_simulator_process_chore_ack_query_client(
            chore_id, current_itr_expected_buy_chore_ledger_.chore.px,
            current_itr_expected_buy_chore_ledger_.chore.qty,
            current_itr_expected_buy_chore_ledger_.chore.side,
            current_itr_expected_buy_chore_ledger_.chore.security.sec_id,
            current_itr_expected_buy_chore_ledger_.chore.underlying_account
        )

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol, executor_web_client)

        # Checking Ack response on placed chore
        placed_buy_chore_ack_receive(placed_chore_ledger_obj_ack_response, expected_buy_chore_snapshot,
                                     executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore ACK of chore_id {chore_id}")

        buy_fill_ledger_obj = copy.deepcopy(buy_fill_ledger_)
        buy_fill_ledger_obj.fill_qty = random.randint(50, 55)
        buy_fill_ledger_obj.fill_px = random.randint(95, 100)
        executor_web_client.barter_simulator_process_fill_query_client(
            chore_id, buy_fill_ledger_obj.fill_px, buy_fill_ledger_obj.fill_qty,
            Side.BUY, buy_symbol, buy_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(chore_id, executor_web_client)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_buy_chore_after_all_sells(loop_count, chore_id,
                                                                buy_symbol, placed_fill_ledger_obj,
                                                                expected_buy_chore_snapshot,
                                                                expected_buy_symbol_side_snapshot,
                                                                expected_sell_symbol_side_snapshot, active_pair_plan,
                                                                expected_plan_limits_, expected_plan_status,
                                                                expected_plan_brief_obj, executor_web_client)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol}, Checked buy placed chore FILL of chore_id {chore_id}")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           buy_symbol, executor_web_client,
                                                                           last_chore_id=buy_cxl_chore_id)
        buy_cxl_chore_id = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_buy_chore_after_all_sells(buy_symbol,
                                                               cxl_chore_ledger, expected_buy_chore_snapshot,
                                                               expected_buy_symbol_side_snapshot,
                                                               expected_sell_symbol_side_snapshot,
                                                               active_pair_plan, expected_plan_limits_,
                                                               expected_plan_status, expected_plan_brief_obj,
                                                               executor_web_client)

        plan_buy_notional += expected_buy_chore_snapshot.fill_notional
        plan_buy_fill_notional += expected_buy_chore_snapshot.fill_notional
    return plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional


def handle_test_buy_sell_n_sell_buy_pair_chore(
        total_loop_count: int,
        refresh_sec: int, buy_chore_: ChoreLedgerBaseModel,
        sell_chore_: ChoreLedgerBaseModel,
        buy_fill_ledger_: DealsLedgerBaseModel, sell_fill_ledger_: DealsLedgerBaseModel,
        expected_buy_chore_snapshot_: ChoreSnapshotBaseModel,
        expected_sell_chore_snapshot_: ChoreSnapshotBaseModel,
        expected_symbol_side_snapshot_: List[SymbolSideSnapshotBaseModel],
        pair_plan_list: List[PairPlanBaseModel], expected_plan_limits_list: List[PlanLimits],
        expected_start_status_: PlanStatus, expected_plan_brief_: PlanBriefBaseModel,
        last_barter_fixture_list: List[Dict],
        symbol_overview_obj_list: List[SymbolOverviewBaseModel],
        market_depth_basemodel_list: List[MarketDepthBaseModel],
        is_non_systematic_run: bool = False):
    residual_test_wait = 4 * refresh_sec

    active_pair_plan_list = []
    executor_web_client_list = []
    for idx, pair_plan_ in enumerate(pair_plan_list):
        expected_plan_limits_list[idx].residual_restriction.residual_mark_seconds = 2 * refresh_sec
        active_pair_plan, executor_web_client = (
            move_snoozed_pair_plan_to_ready_n_then_active(pair_plan_, market_depth_basemodel_list,
                                                           symbol_overview_obj_list, expected_plan_limits_list[idx],
                                                           expected_start_status_))
        active_pair_plan_list.append(active_pair_plan)
        executor_web_client_list.append(executor_web_client)
        print(f"Created Plan: {active_pair_plan}")

    active_pair_plan1 = active_pair_plan_list[0]
    expected_plan_limits1 = expected_plan_limits_list[0]
    buy_symbol1 = active_pair_plan_list[0].pair_plan_params.plan_leg1.sec.sec_id
    sell_symbol1 = active_pair_plan_list[0].pair_plan_params.plan_leg2.sec.sec_id
    buy1_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan_list[0])
    sell1_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan_list[0])

    active_pair_plan2 = active_pair_plan_list[1]
    expected_plan_limits2 = expected_plan_limits_list[1]
    buy_symbol2 = active_pair_plan_list[1].pair_plan_params.plan_leg2.sec.sec_id
    sell_symbol2 = active_pair_plan_list[1].pair_plan_params.plan_leg1.sec.sec_id
    buy2_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan_list[1])
    sell2_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan_list[1])

    plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional = 0, 0, 0, 0
    buy_tob_last_update_date_time_tracker1: DateTime | None = None
    buy_tob_last_update_date_time_tracker2: DateTime | None = None
    sell_tob_last_update_date_time_tracker1: DateTime | None = None
    sell_tob_last_update_date_time_tracker2: DateTime | None = None
    buy_chore_id1 = None
    sell_chore_id1 = None
    buy_chore_id2 = None
    sell_chore_id2 = None
    buy_cxl_chore_id1 = None
    sell_cxl_chore_id1 = None
    buy_cxl_chore_id2 = None
    sell_cxl_chore_id2 = None
    expected_buy_symbol_side_snapshot1 = copy.deepcopy(expected_symbol_side_snapshot_[0])
    expected_buy_symbol_side_snapshot1.security.sec_id = buy_symbol1
    expected_buy_symbol_side_snapshot2 = copy.deepcopy(expected_symbol_side_snapshot_[0])
    expected_buy_symbol_side_snapshot2.security.sec_id = buy_symbol2
    expected_sell_symbol_side_snapshot1 = copy.deepcopy(expected_symbol_side_snapshot_[1])
    expected_sell_symbol_side_snapshot1.security.sec_id = sell_symbol1
    expected_sell_symbol_side_snapshot2 = copy.deepcopy(expected_symbol_side_snapshot_[1])
    expected_sell_symbol_side_snapshot2.security.sec_id = sell_symbol2
    expected_plan_status1 = copy.deepcopy(expected_start_status_)
    expected_plan_status2 = copy.deepcopy(expected_start_status_)
    expected_plan_brief_obj1 = copy.deepcopy(expected_plan_brief_)
    expected_plan_brief_obj1.pair_buy_side_bartering_brief.security.sec_id = buy_symbol1
    expected_plan_brief_obj1.pair_sell_side_bartering_brief.security.sec_id = sell_symbol1
    expected_plan_brief_obj2 = copy.deepcopy(expected_plan_brief_)
    expected_plan_brief_obj2.pair_buy_side_bartering_brief.security.sec_id = buy_symbol2
    expected_plan_brief_obj2.pair_sell_side_bartering_brief.security.sec_id = sell_symbol2

    bid_buy_top_market_depth1, ask_sell_top_market_depth1 = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol1, sell_symbol1, active_pair_plan1))
    executor_web_client1 = executor_web_client_list[0]

    bid_buy_top_market_depth2, ask_sell_top_market_depth2 = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol2, sell_symbol2, active_pair_plan2))
    executor_web_client2 = executor_web_client_list[1]

    for loop_count in range(1, total_loop_count + 1):

        # first handling plan with BUY-SELL pair
        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Loop started at {start_time}")
        expected_buy_chore_snapshot1 = copy.deepcopy(expected_buy_chore_snapshot_)
        expected_buy_chore_snapshot1.chore_brief.security.sec_id = buy_symbol1
        expected_buy_chore_snapshot1.chore_brief.security.inst_type = None
        expected_buy_chore_snapshot1.chore_brief.bartering_security.sec_id = buy_symbol1
        expected_buy_chore_snapshot1.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol1, sell_symbol1, last_barter_fixture_list, active_pair_plan1.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol1}, sell_symbol: {sell_symbol1}")

        if not is_non_systematic_run:
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(active_pair_plan1.cpp_port,
                                                               bid_buy_top_market_depth1,
                                                               ask_sell_top_market_depth1)

            # Waiting for tob to trigger place chore
            buy_tob_last_update_date_time_tracker1 = \
                wait_for_get_new_chore_placed_from_tob(100, buy_symbol1,
                                                       buy_tob_last_update_date_time_tracker1, Side.BUY,
                                                       executor_web_client1)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker1}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(85, 95)
            px = random.randint(95, 100)
            place_new_chore(buy_symbol1, Side.BUY, px, qty, executor_web_client1, buy1_inst_type)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol1, executor_web_client1,
                                                                              last_chore_id=buy_chore_id1)
        buy_chore_id1 = placed_chore_ledger.chore.chore_id
        create_buy_chore_date_time1: DateTime = placed_chore_ledger.chore_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Received chore_ledger with {buy_chore_id1}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_buy_chore_computes_before_all_sells(
            loop_count, buy_chore_id1, buy_symbol1,
            placed_chore_ledger, expected_buy_chore_snapshot1,
            expected_buy_symbol_side_snapshot1,
            expected_sell_symbol_side_snapshot1,
            active_pair_plan1,
            expected_plan_limits1, expected_plan_status1,
            expected_plan_brief_obj1, executor_web_client1)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Checked buy placed chore of chore_id {buy_chore_id1}")

        executor_web_client1.barter_simulator_process_chore_ack_query_client(
            buy_chore_id1, placed_chore_ledger.chore.px,
            placed_chore_ledger.chore.qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id,
            placed_chore_ledger.chore.underlying_account
        )

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol1, executor_web_client1)

        # Checking Ack response on placed chore
        placed_buy_chore_ack_receive(placed_chore_ledger_obj_ack_response, expected_buy_chore_snapshot1,
                                     executor_web_client1)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Checked buy placed chore ACK of chore_id {buy_chore_id1}")

        buy_fill_ledger_obj = copy.deepcopy(buy_fill_ledger_)
        buy_fill_ledger_obj.fill_qty = random.randint(50, 55)
        buy_fill_ledger_obj.fill_px = random.randint(95, 100)
        executor_web_client1.barter_simulator_process_fill_query_client(
            buy_chore_id1, buy_fill_ledger_obj.fill_px, buy_fill_ledger_obj.fill_qty,
            Side.BUY, buy_symbol1, buy_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(buy_chore_id1, executor_web_client1)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_buy_chore_before_sells(
            buy_symbol1, placed_fill_ledger_obj,
            expected_buy_chore_snapshot1, expected_buy_symbol_side_snapshot1,
            expected_sell_symbol_side_snapshot1,
            active_pair_plan1,
            expected_plan_limits1, expected_plan_status1,
            expected_plan_brief_obj1,
            executor_web_client1)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol1}, Checked buy placed chore FILL of chore_id {buy_chore_id1}")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           buy_symbol1, executor_web_client1,
                                                                           last_chore_id=buy_cxl_chore_id1)
        buy_cxl_chore_id1 = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on placed chore by cxl_req from residual removal
        check_cxl_receive_for_placed_buy_chore_before_sells(buy_symbol1, cxl_chore_ledger,
                                                            expected_buy_chore_snapshot1,
                                                            expected_buy_symbol_side_snapshot1,
                                                            expected_sell_symbol_side_snapshot1,
                                                            active_pair_plan1,
                                                            expected_plan_limits1, expected_plan_status1,
                                                            expected_plan_brief_obj1, executor_web_client1)

        plan_buy_notional += expected_buy_chore_snapshot1.fill_notional
        plan_buy_fill_notional += expected_buy_chore_snapshot1.fill_notional

        # handle sell chore
        chore_id = None
        cxl_chore_id = None

        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, Loop started")
        expected_sell_chore_snapshot1 = copy.deepcopy(expected_sell_chore_snapshot_)
        expected_sell_chore_snapshot1.chore_brief.security.sec_id = sell_symbol1
        expected_sell_chore_snapshot1.chore_brief.security.inst_type = None
        expected_sell_chore_snapshot1.chore_brief.bartering_security.sec_id = sell_symbol1
        expected_sell_chore_snapshot1.chore_brief.bartering_security.inst_type = None

        # running last barter once more before sell side
        run_last_barter(buy_symbol1, sell_symbol1, last_barter_fixture_list, active_pair_plan1.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol1}, sell_symbol: {sell_symbol1}")

        if not is_non_systematic_run:
            # required to make buy side tob latest so that when top update reaches in test place chore function in
            # executor both side are new last_update_date_time
            run_last_barter(buy_symbol1, sell_symbol1, [last_barter_fixture_list[0]], active_pair_plan1.cpp_port)
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            update_tob_through_market_depth_to_place_sell_chore(active_pair_plan1.cpp_port,
                                                                ask_sell_top_market_depth1,
                                                                bid_buy_top_market_depth1)

            # Waiting for tob to trigger place chore
            sell_tob_last_update_date_time_tracker1 = \
                wait_for_get_new_chore_placed_from_tob(120, sell_symbol1, sell_tob_last_update_date_time_tracker1,
                                                       Side.SELL, executor_web_client1)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, Received buy TOB")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(95, 105)
            px = random.randint(100, 110)
            place_new_chore(sell_symbol1, Side.SELL, px, qty, executor_web_client1, sell1_inst_type)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol1, executor_web_client1,
                                                                              last_chore_id=sell_chore_id1)
        create_sell_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        sell_chore_id1 = placed_chore_ledger.chore.chore_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, Received chore_ledger with {sell_chore_id1}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_sell_chore_computes_after_all_buys(
            loop_count, sell_chore_id1, sell_symbol1, placed_chore_ledger, expected_sell_chore_snapshot1,
            expected_sell_symbol_side_snapshot1, expected_buy_symbol_side_snapshot1, active_pair_plan1,
            expected_plan_limits1, expected_plan_status1,
            expected_plan_brief_obj1, executor_web_client1)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, Checked sell placed chore of chore_id {sell_chore_id1}")

        executor_web_client1.barter_simulator_process_chore_ack_query_client(
            sell_chore_id1, placed_chore_ledger.chore.px,
            placed_chore_ledger.chore.qty,
            placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id,
            placed_chore_ledger.chore.underlying_account)

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, sell_symbol1, executor_web_client1)

        # Checking Ack response on placed chore
        placed_sell_chore_ack_receive(placed_chore_ledger_obj_ack_response,
                                      expected_sell_chore_snapshot1, executor_web_client1)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, "
              f"Checked sell placed chore ACK of chore_id {sell_chore_id1}")

        sell_fill_ledger_obj = copy.deepcopy(sell_fill_ledger_)
        sell_fill_ledger_obj.fill_qty = random.randint(48, 53)
        sell_fill_ledger_obj.fill_px = random.randint(100, 110)
        executor_web_client1.barter_simulator_process_fill_query_client(
            sell_chore_id1, sell_fill_ledger_obj.fill_px, sell_fill_ledger_obj.fill_qty,
            Side.SELL, sell_symbol1, sell_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(sell_chore_id1, executor_web_client1)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_sell_chore_after_all_buys(
            loop_count, sell_chore_id1, sell_symbol1, placed_fill_ledger_obj,
            expected_sell_chore_snapshot1, expected_sell_symbol_side_snapshot1,
            expected_buy_symbol_side_snapshot1, active_pair_plan1, expected_plan_limits1,
            expected_plan_status1, expected_plan_brief_obj1, executor_web_client1)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol1}, Checked sell placed chore FILL")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           sell_symbol1, executor_web_client1,
                                                                           last_chore_id=sell_cxl_chore_id1)
        sell_cxl_chore_id1 = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_sell_chore_after_all_buys(sell_symbol1,
                                                               cxl_chore_ledger, expected_sell_chore_snapshot1,
                                                               expected_sell_symbol_side_snapshot1,
                                                               expected_buy_symbol_side_snapshot1,
                                                               active_pair_plan1, expected_plan_limits1,
                                                               expected_plan_status1, expected_plan_brief_obj1,
                                                               executor_web_client1)

        plan_sell_notional += expected_sell_chore_snapshot1.fill_notional
        plan_sell_fill_notional += expected_sell_chore_snapshot1.fill_notional

        ################################################################################################################
        # Now handling SELL-BUY plan's chore
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, Loop started")
        expected_sell_chore_snapshot2 = copy.deepcopy(expected_sell_chore_snapshot_)
        expected_sell_chore_snapshot2.chore_brief.security.sec_id = sell_symbol2
        expected_sell_chore_snapshot2.chore_brief.security.inst_type = None
        expected_sell_chore_snapshot2.chore_brief.bartering_security.sec_id = sell_symbol2
        expected_sell_chore_snapshot2.chore_brief.bartering_security.inst_type = None
        
        # running last barter once more before sell side
        run_last_barter(buy_symbol2, sell_symbol2, last_barter_fixture_list, active_pair_plan2.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol2}, sell_symbol: {sell_symbol2}")

        if not is_non_systematic_run:
            # required to make buy side tob latest so that when top update reaches in test place chore function in
            # executor both side are new last_update_date_time
            run_last_barter(buy_symbol2, sell_symbol2, [last_barter_fixture_list[0]], active_pair_plan2.cpp_port)
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            update_tob_through_market_depth_to_place_sell_chore(active_pair_plan2.cpp_port,
                                                                ask_sell_top_market_depth2,
                                                                bid_buy_top_market_depth2)

            # Waiting for tob to trigger place chore
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(120, sell_symbol2,
                                                       sell_tob_last_update_date_time_tracker2,
                                                       Side.SELL, executor_web_client2)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, Received buy TOB")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(95, 105)
            px = random.randint(100, 110)
            place_new_chore(sell_symbol2, Side.SELL, px, qty, executor_web_client2, sell2_inst_type)
            print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              sell_symbol2, executor_web_client2,
                                                                              last_chore_id=sell_chore_id2)
        create_sell_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        sell_chore_id2 = placed_chore_ledger.chore.chore_id
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, Received chore_ledger with {sell_chore_id2}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_sell_chore_computes_before_buys(loop_count, sell_chore_id2, sell_symbol2,
                                                     placed_chore_ledger, expected_sell_chore_snapshot2,
                                                     expected_sell_symbol_side_snapshot2,
                                                     expected_buy_symbol_side_snapshot2, active_pair_plan2,
                                                     expected_plan_limits2, expected_plan_status2,
                                                     expected_plan_brief_obj2, executor_web_client2)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, Checked sell placed chore of chore_id {sell_chore_id2}")

        executor_web_client2.barter_simulator_process_chore_ack_query_client(
            sell_chore_id2, placed_chore_ledger.chore.px, placed_chore_ledger.chore.qty, placed_chore_ledger.chore.side,
            placed_chore_ledger.chore.security.sec_id, placed_chore_ledger.chore.underlying_account)

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, sell_symbol2, executor_web_client2)

        # Checking Ack response on placed chore
        placed_sell_chore_ack_receive(placed_chore_ledger_obj_ack_response,
                                      expected_sell_chore_snapshot2, executor_web_client2)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, "
              f"Checked sell placed chore ACK of chore_id {sell_chore_id2}")

        sell_fill_ledger_obj = copy.deepcopy(sell_fill_ledger_)
        sell_fill_ledger_obj.fill_qty = random.randint(48, 53)
        sell_fill_ledger_obj.fill_px = random.randint(100, 110)
        executor_web_client2.barter_simulator_process_fill_query_client(
            sell_chore_id2, sell_fill_ledger_obj.fill_px, sell_fill_ledger_obj.fill_qty,
            Side.SELL, sell_symbol2, sell_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(sell_chore_id2, executor_web_client2)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_sell_chore_before_buys(
            sell_symbol2, placed_fill_ledger_obj,
            expected_sell_chore_snapshot2, expected_sell_symbol_side_snapshot2,
            expected_buy_symbol_side_snapshot2, active_pair_plan2,
            expected_plan_limits2, expected_plan_status2, expected_plan_brief_obj2,
            executor_web_client2)
        print(f"Loop count: {loop_count}, sell_symbol: {sell_symbol2}, Checked sell placed chore FILL")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           sell_symbol2, executor_web_client2,
                                                                           last_chore_id=sell_cxl_chore_id2)
        sell_cxl_chore_id2 = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_sell_chore_before_buy(sell_symbol2,
                                                           cxl_chore_ledger, expected_sell_chore_snapshot2,
                                                           expected_sell_symbol_side_snapshot2,
                                                           expected_buy_symbol_side_snapshot2,
                                                           active_pair_plan2, expected_plan_limits2,
                                                           expected_plan_status2, expected_plan_brief_obj2,
                                                           executor_web_client2)

        plan_sell_notional += expected_sell_chore_snapshot2.fill_notional
        plan_sell_fill_notional += expected_sell_chore_snapshot2.fill_notional

        start_time = DateTime.utcnow()
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Loop started at {start_time}")
        expected_buy_chore_snapshot2 = copy.deepcopy(expected_buy_chore_snapshot_)
        expected_buy_chore_snapshot2.chore_brief.security.sec_id = buy_symbol2
        expected_buy_chore_snapshot2.chore_brief.security.sec_id = buy_symbol2
        expected_buy_chore_snapshot2.chore_brief.security.inst_type = None
        expected_buy_chore_snapshot2.chore_brief.bartering_security.sec_id = buy_symbol2
        expected_buy_chore_snapshot2.chore_brief.bartering_security.inst_type = None

        # placing chore
        current_itr_expected_buy_chore_ledger_ = copy.deepcopy(buy_chore_)
        current_itr_expected_buy_chore_ledger_.chore.security.sec_id = buy_symbol2

        # running last barter once more before sell side
        run_last_barter(buy_symbol2, sell_symbol2, last_barter_fixture_list, active_pair_plan2.cpp_port)
        print(f"LastBarters created: buy_symbol: {buy_symbol2}, sell_symbol: {sell_symbol2}")

        if not is_non_systematic_run:
            # Updating TopOfBook by updating 0th position market depth (this triggers expected buy chore)
            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(active_pair_plan2.cpp_port,
                                                               bid_buy_top_market_depth2,
                                                               ask_sell_top_market_depth2)

            # Waiting for tob to trigger place chore
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_chore_placed_from_tob(100, buy_symbol2,
                                                       buy_tob_last_update_date_time_tracker2, Side.BUY,
                                                       executor_web_client2)
            time_delta = DateTime.utcnow() - start_time
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Received buy TOB of last_update_date_time "
                  f"{buy_tob_last_update_date_time_tracker}, time delta {time_delta.total_seconds()}")
        else:
            # placing new non-systematic new_chore
            qty = random.randint(85, 95)
            px = random.randint(95, 100)
            place_new_chore(buy_symbol2, Side.BUY, px, qty, executor_web_client2, buy2_inst_type)
            print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Created new_chore obj")
            time.sleep(2)

        placed_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_NEW,
                                                                              buy_symbol2, executor_web_client2,
                                                                              last_chore_id=buy_chore_id2)
        buy_chore_id2 = placed_chore_ledger.chore.chore_id
        create_buy_chore_date_time: DateTime = placed_chore_ledger.chore_event_date_time
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Received chore_ledger with {buy_chore_id2}")
        time.sleep(2)

        # Checking placed chore computations
        check_placed_buy_chore_computes_after_sells(loop_count, buy_chore_id2, buy_symbol2,
                                                    placed_chore_ledger, expected_buy_chore_snapshot2,
                                                    expected_buy_symbol_side_snapshot2,
                                                    expected_sell_symbol_side_snapshot2, active_pair_plan2,
                                                    expected_plan_limits2, expected_plan_status2,
                                                    expected_plan_brief_obj2, executor_web_client2)
        print(f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Checked buy placed chore of chore_id {buy_chore_id2}")

        executor_web_client2.barter_simulator_process_chore_ack_query_client(
            buy_chore_id2, current_itr_expected_buy_chore_ledger_.chore.px,
            current_itr_expected_buy_chore_ledger_.chore.qty,
            current_itr_expected_buy_chore_ledger_.chore.side,
            current_itr_expected_buy_chore_ledger_.chore.security.sec_id,
            current_itr_expected_buy_chore_ledger_.chore.underlying_account
        )

        placed_chore_ledger_obj_ack_response = \
            get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK, buy_symbol2, executor_web_client2)

        # Checking Ack response on placed chore
        placed_buy_chore_ack_receive(placed_chore_ledger_obj_ack_response, expected_buy_chore_snapshot2,
                                     executor_web_client2)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Checked buy placed chore ACK of chore_id {buy_chore_id2}")

        buy_fill_ledger_obj = copy.deepcopy(buy_fill_ledger_)
        buy_fill_ledger_obj.fill_qty = random.randint(50, 55)
        buy_fill_ledger_obj.fill_px = random.randint(95, 100)
        executor_web_client2.barter_simulator_process_fill_query_client(
            buy_chore_id2, buy_fill_ledger_obj.fill_px, buy_fill_ledger_obj.fill_qty,
            Side.BUY, buy_symbol2, buy_fill_ledger_obj.underlying_account)

        placed_fill_ledger_obj = get_latest_fill_ledger_from_chore_id(buy_chore_id2, executor_web_client2)

        # Checking Fill receive on placed chore
        check_fill_receive_for_placed_buy_chore_after_all_sells(loop_count, buy_chore_id2,
                                                                buy_symbol2, placed_fill_ledger_obj,
                                                                expected_buy_chore_snapshot2,
                                                                expected_buy_symbol_side_snapshot2,
                                                                expected_sell_symbol_side_snapshot2, active_pair_plan2,
                                                                expected_plan_limits2, expected_plan_status2,
                                                                expected_plan_brief_obj2, executor_web_client2)
        print(
            f"Loop count: {loop_count}, buy_symbol: {buy_symbol2}, Checked buy placed chore FILL of chore_id {chore_id}")

        # Sleeping to let the chore get cxlled
        time.sleep(residual_test_wait)

        cxl_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_CXL_ACK,
                                                                           buy_symbol2, executor_web_client2,
                                                                           last_chore_id=buy_cxl_chore_id2)
        buy_cxl_chore_id2 = cxl_chore_ledger.chore.chore_id

        # Checking CXL_ACK receive on cxl req by residual handler
        check_cxl_receive_for_placed_buy_chore_after_all_sells(buy_symbol2,
                                                               cxl_chore_ledger, expected_buy_chore_snapshot2,
                                                               expected_buy_symbol_side_snapshot2,
                                                               expected_sell_symbol_side_snapshot2,
                                                               active_pair_plan2, expected_plan_limits2,
                                                               expected_plan_status2, expected_plan_brief_obj2,
                                                               executor_web_client2)

        plan_buy_notional += expected_buy_chore_snapshot2.fill_notional
        plan_buy_fill_notional += expected_buy_chore_snapshot2.fill_notional

        # Any additional compute post each plan's single chore comes here ...

    return plan_buy_notional, plan_sell_notional, plan_buy_fill_notional, plan_sell_fill_notional


def place_sanity_chores_for_executor(
        buy_symbol: str, sell_symbol: str, created_pair_plan,
        total_chore_count_for_each_side, last_barter_fixture_list,
        residual_wait_sec, executor_web_client, place_after_recovery: bool = False,
        expect_no_chore: bool = False):

    # Placing buy chores
    buy_ack_chore_id = None

    if place_after_recovery:
        chore_ledgers = executor_web_client.get_all_chore_ledger_client(-100)
        max_id = 0
        for chore_ledger in chore_ledgers:
            if chore_ledger.chore.security.sec_id == buy_symbol and chore_ledger.chore_event == ChoreEventType.OE_ACK:
                if max_id < chore_ledger.id:
                    buy_ack_chore_id = chore_ledger.chore.chore_id

    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, created_pair_plan))

    for loop_count in range(total_chore_count_for_each_side):
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
        time.sleep(1)
        update_tob_through_market_depth_to_place_buy_chore(created_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                           ask_sell_top_market_depth)

        ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                           buy_symbol, executor_web_client,
                                                                           last_chore_id=buy_ack_chore_id,
                                                                           expect_no_chore=expect_no_chore)
        buy_ack_chore_id = ack_chore_ledger.chore.chore_id

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)  # wait to make this open chore residual

    # Placing sell chores
    sell_ack_chore_id = None
    for loop_count in range(total_chore_count_for_each_side):
        run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
        # required to make buy side tob latest
        run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], created_pair_plan.cpp_port)

        update_tob_through_market_depth_to_place_sell_chore(created_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                            bid_buy_top_market_depth)

        ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                           sell_symbol, executor_web_client,
                                                                           last_chore_id=sell_ack_chore_id,
                                                                           expect_no_chore=expect_no_chore)
        sell_ack_chore_id = ack_chore_ledger.chore.chore_id

        if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
            time.sleep(residual_wait_sec)  # wait to make this open chore residual


def debug_callable_handler(debug_max_wait_sec: int | None, test_callable: Callable[..., Any], callable_params_kwargs: Dict):
    start_time = DateTime.utcnow()
    while True:
        try:
            res = test_callable(**callable_params_kwargs)
            return res
        except AssertionError as assert_err:
            latest_time = DateTime.utcnow()
            if debug_max_wait_sec:
                if (latest_time - start_time).total_seconds() < debug_max_wait_sec:
                    raise assert_err
                # else continue to keep running test_callable till it passes or debug_max_wait_sec are consumed
            else:
                raise assert_err


def place_sanity_chores(buy_symbol, sell_symbol, pair_plan_,
                        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
                        last_barter_fixture_list, market_depth_basemodel_list,
                        max_loop_count_per_side, refresh_sec_update_fixture):
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 111360
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    created_pair_plan, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = max_loop_count_per_side

        bid_buy_top_market_depth, ask_sell_top_market_depth = (
            get_buy_bid_n_ask_sell_market_depth(buy_symbol, sell_symbol, created_pair_plan))

        # Placing buy chores
        buy_ack_chore_id = None
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)

            time.sleep(1)
            update_tob_through_market_depth_to_place_buy_chore(created_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                               ask_sell_top_market_depth)
            ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               buy_symbol, executor_web_client,
                                                                               last_chore_id=buy_ack_chore_id)
            buy_ack_chore_id = ack_chore_ledger.chore.chore_id

            if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
                # Sleeping to let the chore get cxled
                time.sleep(residual_wait_sec)

        # Placing sell chores
        sell_ack_chore_id = None
        for loop_count in range(total_chore_count_for_each_side):
            run_last_barter(buy_symbol, sell_symbol, last_barter_fixture_list, created_pair_plan.cpp_port)
            # required to make buy side tob latest
            run_last_barter(buy_symbol, sell_symbol, [last_barter_fixture_list[0]], created_pair_plan.cpp_port)

            update_tob_through_market_depth_to_place_sell_chore(created_pair_plan.cpp_port, ask_sell_top_market_depth,
                                                                bid_buy_top_market_depth)

            ack_chore_ledger = get_latest_chore_ledger_with_event_and_symbol(ChoreEventType.OE_ACK,
                                                                               sell_symbol, executor_web_client,
                                                                               last_chore_id=sell_ack_chore_id)
            sell_ack_chore_id = ack_chore_ledger.chore.chore_id

            if not executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan"):
                # Sleeping to let the chore get cxled
                time.sleep(residual_wait_sec)
        return buy_symbol, sell_symbol, created_pair_plan, executor_web_client

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def handle_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_,
                                       expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                       market_depth_basemodel_list, leg1_side=Side.BUY, leg2_side=Side.SELL,
                                       get_config_data=True):
    active_pair_plan, executor_http_client = (
        create_pre_chore_test_requirements(leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_,
                                           expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list, leg1_side=leg1_side, leg2_side=leg2_side))

    buy_inst_type: InstrumentType = get_inst_type(Side.BUY, active_pair_plan)
    sell_inst_type: InstrumentType = get_inst_type(Side.SELL, active_pair_plan)

    config_file_path: str | None
    config_dict: Dict | None
    config_dict_str: str | None
    if get_config_data:
        config_file_path = str(STRAT_EXECUTOR / "data" / f"executor_{active_pair_plan.id}_simulate_config.yaml")
        config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
        config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)
    else:
        config_file_path = None
        config_dict = None
        config_dict_str = None

    return (active_pair_plan, executor_http_client, buy_inst_type, sell_inst_type,
            config_file_path, config_dict, config_dict_str)


def get_config_file_path_n_config_dict(plan_id: int):
    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{plan_id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path), load_as_str=True)
    return config_file_path, config_dict, config_dict_str
