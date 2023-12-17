import random
import subprocess
import os
from pathlib import PurePath
import datetime
from typing import Dict

# Project specific imports
from tests.CodeGenProjects.addressbook.app.utility_test_functions import (
    create_pre_order_test_requirements, PAIR_STRAT_ENGINE_DIR)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager

PAIR_STRAT_ENGINE_LOG: PurePath = PAIR_STRAT_ENGINE_DIR / "log"


# Function to generate a random log entry
def generate_log_entry(is_error: bool) -> str:
    # Get the current UTC time
    current_utc_time = datetime.datetime.utcnow()

    # Format the datetime as a string in the desired format
    timestamp = current_utc_time.strftime("%Y-%m-%d %H:%M:%S") + f",{current_utc_time.microsecond // 1000:03d}"

    log_level = random.choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
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


def test_portfolio_alert(clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_,
                         expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                         market_depth_basemodel_list, top_of_book_list_, buy_order_, sell_order_,
                         max_loop_count_per_side, residual_wait_sec):

    date = str(datetime.date.today())
    pair_start_log_file_name: str = "pair_start_engine_logs_" + date.replace("-", "") + ".log"
    print(pair_start_log_file_name)

    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    pair_start_engine_log_file: str = str(PAIR_STRAT_ENGINE_LOG / pair_start_log_file_name)

    print(pair_start_engine_log_file)
    for _ in range(10):
        log_entry: str = generate_log_entry(True)
        print(log_entry)
        os.system(f'echo "{log_entry}" >> "{pair_start_engine_log_file}"')
        # log_file.write(log_entry.encode('utf-8'))