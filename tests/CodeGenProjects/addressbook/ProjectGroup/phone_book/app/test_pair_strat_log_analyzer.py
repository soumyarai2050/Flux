import random
import subprocess
import os
import time
from pathlib import PurePath, Path
import datetime
from typing import Dict, List

from fastapi.encoders import jsonable_encoder

# Project specific imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import (
    create_pre_order_test_requirements, PAIR_STRAT_ENGINE_DIR, log_analyzer_web_client, PortfolioAlertBaseModel,
    StratState, create_pre_order_test_requirements_for_log_analyzer, STRAT_EXECUTOR)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_analyzer.generated.Pydentic.log_analyzer_service_beanie_model import (
    Severity, AlertOptional, StratAlertBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_analyzer.app.phone_book_log_analyzer import StratLogDetail
from FluxPythonUtils.log_analyzer.log_analyzer import LogAnalyzer, LogDetail

PAIR_STRAT_ENGINE_LOG: PurePath = PAIR_STRAT_ENGINE_DIR / "log"
STRAT_ENGINE_LOG: PurePath = STRAT_EXECUTOR / "log"


# Function to generate a random log entry
def generate_log_entry(is_error: bool) -> str:
    # Get the current UTC time
    current_utc_time = datetime.datetime.utcnow()

    # Format the datetime as a string in the desired format
    timestamp = current_utc_time.strftime("%Y-%m-%d %H:%M:%S") + f",{current_utc_time.microsecond // 1000:03d}"

    log_level = random.choice(['ERROR'])
    file_name = "utility_functions.py"
    line_number = random.randint(1, 300)
    severity = random.choice(['Severity_CRITICAL', 'Severity_ERROR', 'Severity_WARNING', 'Severity_INFO',
                              'Severity_DEBUG'])
    alert_brief = "LogSimulator Log analyzer running in simulation mode"
    alert_details = "alert_details: ..."

    if is_error:
        host = "127.0.0.1"
        port = random.randint(50000, 59999)
        url = "/strat_executor/get-all-ui_layout"
        exception_msg = (f"HTTPConnectionPool(host='127.0.0.1', port={port}): Max retries exceeded with url: "
                         f"/strat_executor/get-all-ui_layout (Caused by NewConnectionError('<urllib3.connection."
                         f"HTTPConnection object at 0x7f1849013460>: Failed to establish a new connection: "
                         f"[Errno 111] Connection refused'))")

        log_entry = (f"{timestamp} : {log_level} : [utility_functions.py : {line_number}] : "
                     f"Client Error Occurred in function: generic_http_get_all_client;;;args: "
                     f"('{host}:{port}{url}', <class 'Flux.CodeGenProjects.strat_executor.generated.Pydentic."
                     f"strat_executor_service_beanie_model.UILayoutBaseModel'>, None), kwargs: {{}}, "
                     f"exception: {exception_msg}")
    else:
        log_entry = (f"{timestamp} : {log_level} : [utility_functions.py : {line_number}] : sending alert with severity: "
                     f"{severity}, alert_brief: {alert_brief}, {alert_details}")

    return log_entry


def generate_log(severity: Severity, file_name: str, alert: str, is_portfolio_alert: bool = True) -> str:
    # Get the current UTC time
    current_utc_time = datetime.datetime.utcnow()

    # Format the datetime as a string in the desired format
    timestamp = current_utc_time.strftime("%Y-%m-%d %H:%M:%S") + f",{current_utc_time.microsecond // 1000:03d}"

    log_level: str = get_log_level_from_severity(severity)

    if ";;;" in alert:
        alert_list: List[str] = alert.split(";;;")
        alert_brief: str = alert_list[0]
        alert_details: str = alert_list[1]
    else:
        alert_brief: str = alert
        alert_details: str = ""

    if is_portfolio_alert:
        log_entry = f"{timestamp} : {log_level} : [{file_name}] : {alert_brief}"
    else:
        log_entry = (f"{timestamp} : {log_level} : {file_name} : sending alert with severity: "
                     f"{severity}, alert_brief: {alert_brief}, {alert_details}")

    return log_entry


def get_log_level_from_severity(severity: Severity) -> str:
    severity_mapping = {
        Severity.Severity_ERROR: "ERROR",
        Severity.Severity_CRITICAL: "CRITICAL",
        Severity.Severity_WARNING: "WARNING",
        Severity.Severity_INFO: "INFO",
    }
    return severity_mapping.get(severity, "")


def test_portfolio_alert(clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                         expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                         market_depth_basemodel_list, top_of_book_list_, buy_order_, sell_order_,
                         max_loop_count_per_side):

    date = str(datetime.date.today())
    pair_start_log_file_name: str = "pair_start_engine_logs_" + date.replace("-", "") + ".log"
    print(pair_start_log_file_name)

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements_for_log_analyzer(buy_symbol, sell_symbol, pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list, last_trade_fixture_list,
                                                            market_depth_basemodel_list, top_of_book_list_,
                                                            StratState.StratState_ACTIVE))

    pair_start_engine_log_file: str = str(PAIR_STRAT_ENGINE_LOG / pair_start_log_file_name)
    # Generate a list of log entries
    log_entries = [generate_log_entry(True) for _ in range(10)]

    # print(pair_start_engine_log_file)
    subprocess.run(['bash', 'log_file_append.sh', pair_start_engine_log_file, *log_entries])

    time.sleep(10)

    portfolio_alert_list: List[PortfolioAlertBaseModel] = log_analyzer_web_client.get_all_portfolio_alert_client()

    alert_list: List[str] = []
    for portfolio_alert in portfolio_alert_list:
        for alert in portfolio_alert.alerts:
            log_level: str = get_log_level_from_severity(alert.severity)
            alert_brief: str = jsonable_encoder(alert.alert_brief, by_alias=True, exclude_none=True)
            alert_list.append(alert_brief.replace(":   :", f": {log_level} :"))

    assert log_entries[-1].split(";;;")[0] in alert_list, (f"log_entry: {log_entries[-1]} not found in "
                                                           f"{alert_list}")

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements_for_log_analyzer(buy_symbol, sell_symbol, pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list, last_trade_fixture_list,
                                                            market_depth_basemodel_list, top_of_book_list_,
                                                            StratState.StratState_READY))

    pair_start_engine_log_file: str = str(PAIR_STRAT_ENGINE_LOG / pair_start_log_file_name)

    print(pair_start_engine_log_file)
    for _ in range(10):
        log_entry: str = generate_log_entry(True)
        print(log_entry)
        os.system(f'echo "{log_entry}" >> "{pair_start_engine_log_file}"')
        # log_file.write(log_entry.encode('utf-8'))


def test_strat_alert(clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                     expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                     market_depth_basemodel_list, top_of_book_list_, buy_order_, sell_order_, max_loop_count_per_side):

    date = str(datetime.date.today())
    pair_start_log_file_name: str = "pair_start_engine_logs_" + date.replace("-", "") + ".log"
    print(pair_start_log_file_name)

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements_for_log_analyzer(buy_symbol, sell_symbol, pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list, last_trade_fixture_list,
                                                            market_depth_basemodel_list, top_of_book_list_,
                                                            StratState.StratState_ACTIVE))

    pair_start_engine_log_file: str = str(PAIR_STRAT_ENGINE_LOG / pair_start_log_file_name)
    # Generate a list of log entries
    file_name: str = "utility_functions.py : 6"
    alert: str = ("blocked generated BUY order, order px: 115.0 > allowed max_px 9.5, symbol_side_key: "
                  "%%symbol-side=EQT_Sec_1-BUY%%")
    log_entries = [generate_log(Severity.Severity_ERROR, file_name, alert)]

    # for log in log_entries:
    #     print(log)

    # print(pair_start_engine_log_file)
    subprocess.run(['bash', 'log_file_append.sh', pair_start_engine_log_file, *log_entries])

    time.sleep(10)

    strat_alert_list: List[StratAlertBaseModel] = log_analyzer_web_client.get_all_strat_alert_client()

    alert_list: List[str] = []
    for strat_alert in strat_alert_list:
        for alert in strat_alert.alerts:
            print(f"Alert: {alert}")
            log_level: str = get_log_level_from_severity(alert.severity)
            alert_brief: str = jsonable_encoder(alert.alert_brief, by_alias=True, exclude_none=True)
            alert_list.append(alert_brief.replace(":   :", f": {log_level} :"))

    assert log_entries[-1].split(";;;")[0].replace("%%", "") in alert_list, (f"log_entry: "
                                                                             f"{log_entries[-1]} not found in {alert}")


def test_strat_alert_patch_all(clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                               expected_strat_status_, symbol_overview_obj_list, last_trade_fixture_list,
                               market_depth_basemodel_list, top_of_book_list_, buy_order_, sell_order_,
                               max_loop_count_per_side):

    date = str(datetime.date.today())
    start_executor_log_file_name_list: List[str] = []

    for _ in range(3):
        start_executor_log_file_name: str = (
                "strat_executor_" + str(_ + 1) + "_logs_" + date.replace("-", "") + ".log")
        start_executor_log_file_name_list.append(str(STRAT_ENGINE_LOG / start_executor_log_file_name))
    print(f"-----------------------{start_executor_log_file_name_list}--------------")
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements_for_log_analyzer(buy_symbol, sell_symbol, pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list, last_trade_fixture_list,
                                                            market_depth_basemodel_list, top_of_book_list_,
                                                            StratState.StratState_DONE))

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements_for_log_analyzer(buy_symbol, sell_symbol, pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list, last_trade_fixture_list,
                                                            market_depth_basemodel_list, top_of_book_list_,
                                                            StratState.StratState_READY))

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements_for_log_analyzer(buy_symbol, sell_symbol, pair_strat_,
                                                            expected_strat_limits_, expected_strat_status_,
                                                            symbol_overview_obj_list, last_trade_fixture_list,
                                                            market_depth_basemodel_list, top_of_book_list_,
                                                            StratState.StratState_ACTIVE))

    log_analyzer_web_client.delete_strat_alert_client(strat_alert_id=3)

    log_entries: List[str] = []

    # Generate a list of log entries
    file_name: str = "utility_functions.py : 6"
    alert: str = ("blocked generated BUY order, order px: 115.0 > allowed max_px 9.5, symbol_side_key: "
                  "%%symbol-side=EQT_Sec_1-BUY%%")
    log_entries.append(generate_log(Severity.Severity_ERROR, file_name, alert))

    file_name: str = "utility_functions.py : 102"
    alert: str = ("blocked generated BUY order, order px: 120.0 > allowed max_px 0.5, symbol_side_key: "
                  "%%symbol-side=CB_Sec_1-BUY%%")
    log_entries.append(generate_log(Severity.Severity_ERROR, file_name, alert))

    file_name: str = "utility_functions.py : 271"
    alert: str = ("blocked generated BUY order, order px: 15.0 > allowed max_px 4.5, symbol_side_key: "
                  "%%symbol-side=EQT_Leg_1-BUY%%")
    log_entries.append(generate_log(Severity.Severity_ERROR, file_name, alert))

    file_name: str = "utility_functions.py : 71"
    alert: str = ("blocked generated BUY order, order px: 15.0 > allowed max_px 4.5, symbol_side_key: "
                  "%%symbol-side=EQT_Leg_1-SELL%%")
    log_entries.append(generate_log(Severity.Severity_ERROR, file_name, alert))

    for start_executor_log_file_name in start_executor_log_file_name_list:
        assert Path(start_executor_log_file_name).is_file(), (f"Error: file "
                                                              f"{start_executor_log_file_name} does not exists.")
        subprocess.run(['bash', 'log_file_append.sh', start_executor_log_file_name, *log_entries])

