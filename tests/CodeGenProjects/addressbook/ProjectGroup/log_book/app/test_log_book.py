# standard imports
import concurrent.futures
import copy
import os.path
import random
import subprocess
import time

# project imports
from tests.CodeGenProjects.AddressBook.ProjectGroup.conftest import *
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import STRAT_EXECUTOR
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key, pair_strat_client_call_log_str, UpdateType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import *


frmt_date = datetime.datetime.now().strftime("%Y%m%d")


def add_log_to_file(log_file_path: str, log_str: str) -> None:
    echo_cmd = f'echo "{log_str}" >> {log_file_path}'
    os.system(echo_cmd)


def get_log_date_time():
    log_time = DateTime.now(tz=pendulum.local_timezone()).format("YYYY-MM-DD HH:mm:ss,SSS")
    return log_time


def get_log_line_str(log_lvl: str, file_name: str, line_no: int, log_str: str) -> str:
    log_time = get_log_date_time()
    return f"{log_time} : {log_lvl} : [{file_name} : {line_no}] : {log_str}"


def get_expected_brief(alert_brief: str):
    # clearing symbol_side_key pattern
    symbol_side_pattern = get_symbol_side_pattern()
    alert_brief = alert_brief.replace(symbol_side_pattern, "")

    split_str: List[str] = alert_brief.split(" : ")
    split_str[1] = " "
    return " : ".join(split_str)


def start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list) -> List:
    active_strat_n_executor_list: List[PairStratBaseModel, StreetBookServiceHttpClient] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(create_n_activate_strat,
                                   leg1_symbol, leg2_symbol, copy.deepcopy(pair_strat_),
                                   copy.deepcopy(expected_strat_limits_), copy.deepcopy(expected_strat_status_),
                                   copy.deepcopy(symbol_overview_obj_list), copy.deepcopy(market_depth_basemodel_list),
                                   None, None)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            active_strat_n_executor_list.append(future.result())
    return active_strat_n_executor_list


def check_alert_exists_in_portfolio_alert(log_str: str, expected_alert_detail: str,
                                          log_file_path: str) -> PortfolioAlertBaseModel:
    portfolio_alerts: List[PortfolioAlertBaseModel] = log_book_web_client.get_all_portfolio_alert_client()
    expected_alert_brief = get_expected_brief(log_str.split(";;;")[0])
    for portfolio_alert in portfolio_alerts:
        if portfolio_alert.alert_brief == expected_alert_brief:
            if portfolio_alert.alert_details == expected_alert_detail:
                return portfolio_alert
            else:
                assert False, ("portfolio_alert found with correct brief but mismatched alert_details, "
                               f"expected {expected_alert_detail}, found: {portfolio_alert.alert_detail}")
    else:
        assert False, f"Cant find any portfolio_alert with {expected_alert_brief=}, {log_file_path=}"


def check_alert_doesnt_exist_in_portfolio_alert(log_str: str, expected_alert_detail: str, log_file_path: str):
    portfolio_alerts: List[PortfolioAlertBaseModel] = log_book_web_client.get_all_portfolio_alert_client()
    expected_alert_brief = get_expected_brief(log_str.split(";;;")[0])
    for portfolio_alert in portfolio_alerts:
        if portfolio_alert.alert_brief == expected_alert_brief:
            if portfolio_alert.alert_details == expected_alert_detail:
                assert False, (f"Unexpected: portfolio_alert must not exist with strat_brief: {expected_alert_brief}, "
                               f"found {portfolio_alert=}, {log_file_path=}")


def check_alert_exists_in_strat_alert(active_strat: PairStratBaseModel, log_str: str,
                                      expected_alert_detail: str, log_file_path: str) -> StratAlertBaseModel:
    strat_alerts: List[StratAlertBaseModel] = (
        log_book_web_client.filtered_strat_alert_by_strat_id_query_client(strat_id=active_strat.id))
    expected_alert_brief = get_expected_brief(log_str.split(";;;")[0])
    for strat_alert in strat_alerts:
        if strat_alert.alert_brief == expected_alert_brief:
            if strat_alert.alert_details == expected_alert_detail:
                return strat_alert
            else:
                assert False, ("strat_alert found with correct brief but mismatched alert_details, "
                               f"expected {expected_alert_detail}, found: {strat_alert.alert_detail}")
    else:
        assert False, f"Cant find any strat_alert with {expected_alert_brief=}, {log_file_path=}"


def check_alert_doesnt_exist_in_strat_alert(active_strat: PairStratBaseModel, log_str: str,
                                            expected_alert_detail: str, log_file_path: str):
    strat_alerts: List[StratAlertBaseModel] = (
        log_book_web_client.filtered_strat_alert_by_strat_id_query_client(strat_id=active_strat.id))
    expected_alert_brief = get_expected_brief(log_str.split(";;;")[0])
    for strat_alert in strat_alerts:
        if strat_alert.alert_brief == expected_alert_brief:
            if strat_alert.alert_details == expected_alert_detail:
                assert False, (f"Unexpected: strat_alert must not exist with strat_brief: {expected_alert_brief}, "
                               f"found strat_alert: {strat_alert}, {log_file_path=}")


def test_log_to_start_alert_through_strat_id(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs are created as strat_alerts for tail executor registered based on strat_id
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # Negative test
        sample_brief = "Sample Log not to be created as strat_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("DEBUG", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_doesnt_exist_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)


def test_log_to_start_alert_through_symbol_n_side_key(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs are created as strat_alerts having symbol_n_side key, covers leg_1, leg_2 and both legs
    symbol_n_side key verification
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_strat: PairStratBaseModel
    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        leg_1_symbol_n_side_key = get_symbol_side_key([(active_strat.pair_strat_params.strat_leg1.sec.sec_id,
                                                        active_strat.pair_strat_params.strat_leg1.side)])
        leg_2_symbol_n_side_key = get_symbol_side_key([(active_strat.pair_strat_params.strat_leg2.sec.sec_id,
                                                        active_strat.pair_strat_params.strat_leg2.side)])
        both_legs_symbol_n_side_key = get_symbol_side_key([(active_strat.pair_strat_params.strat_leg1.sec.sec_id,
                                                            active_strat.pair_strat_params.strat_leg1.side),
                                                           (active_strat.pair_strat_params.strat_leg2.sec.sec_id,
                                                            active_strat.pair_strat_params.strat_leg2.side)])

        for log_key in [leg_1_symbol_n_side_key, leg_2_symbol_n_side_key, both_legs_symbol_n_side_key]:
            sample_brief = f"Sample Log to be created as strat_alert key: {log_key}"
            sample_detail = "sample detail string"

            # Positive test
            log_str = get_log_line_str("ERROR", sample_file_name,
                                       line_no, f"{sample_brief};;;{sample_detail}")
            add_log_to_file(log_file_path, log_str)

            time.sleep(time_wait * 2 + 1)
            check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # Negative test
        non_existing_strat_log_key = get_symbol_side_key([("CB_Sec_100", Side.BUY)])

        sample_brief = f"Sample Log not to be created as strat_alert, key: {non_existing_strat_log_key}"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_doesnt_exist_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)


def test_log_to_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs not having symbol-side key or strat_id are created as portfolio_alerts
    """
    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)

    time.sleep(time_wait * 2 + 1)
    check_alert_exists_in_portfolio_alert(log_str, sample_detail, log_file_path)

    # Negative test
    sample_brief = f"Sample Log not to be created as portfolio_alert"
    sample_detail = "sample detail string"
    log_str = get_log_line_str("DEBUG", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)

    time.sleep(time_wait * 2 + 1)
    check_alert_doesnt_exist_in_portfolio_alert(log_str, sample_detail, log_file_path)


def test_log_to_update_db(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs having specific patterns updates db
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"

        # Positive test

        db_json_list = [
            {"strat_alert_count": random.randint(1, 100)},
            {"strat_alert_aggregated_severity": random.choice([Severity.Severity_DEBUG.value,
                                                               Severity.Severity_INFO.value,
                                                               Severity.Severity_WARNING.value,
                                                               Severity.Severity_ERROR.value,
                                                               Severity.Severity_CRITICAL.value])},
            {"average_premium": random.randint(1, 100)},
            {"market_premium": random.randint(1, 100)},
            {"balance_notional": random.randint(1, 100)},
            {"max_single_leg_notional": random.randint(100, 1000)}
            ]

        for db_json in db_json_list:
            db_pattern_str = pair_strat_client_call_log_str(
                StratViewBaseModel, photo_book_web_client.patch_all_strat_view_client,
                UpdateType.SNAPSHOT_TYPE, _id=active_strat.id, **db_json)
            log_str = get_log_line_str("DB", sample_file_name, line_no, db_pattern_str)

            add_log_to_file(log_file_path, log_str)

            time.sleep(1)

            strat_view = photo_book_web_client.get_strat_view_client(active_strat.id)
            stored_val = getattr(strat_view, list(db_json.keys())[0])
            expected_val = list(db_json.values())[0]
            assert stored_val == expected_val, \
                (f"Mismatched {list(db_json.keys())[0]} field of strat view, expected: {expected_val}, "
                 f"received: {stored_val}, active_strat: {active_strat}")


def test_alert_with_same_severity_n_brief_is_always_updated(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs are created as strat_alerts for tail executor registered based on strat_id
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

        # Positive test
        total_log_counts = 5
        for log_count in range(1, total_log_counts+1):
            sample_detail = f"sample detail string - {log_count}"
            log_str = get_log_line_str(log_lvl, sample_file_name,
                                       line_no, f"{sample_brief};;;{sample_detail}")
            add_log_to_file(log_file_path, log_str)

            time.sleep(time_wait * 2 + 1)

            alert_count = 0
            strat_alerts: List[StratAlertBaseModel] = (
                log_book_web_client.filtered_strat_alert_by_strat_id_query_client(strat_id=active_strat.id))
            expected_alert_brief = get_expected_brief(log_str.split(";;;")[0])
            for strat_alert in strat_alerts:
                if strat_alert.alert_brief == expected_alert_brief:
                    alert_count += 1
                    if strat_alert.alert_details == sample_detail:
                        assert strat_alert.alert_count == log_count, \
                            (f"Mismatched alert_count: expected: {total_log_counts}, "
                             f"found {strat_alert.alert_count=} ")
                        continue
                    else:
                        if alert_count == 1:
                            assert False, ("strat_alert found with correct brief but mismatched alert_details, "
                                           f"expected {sample_detail}, found: {strat_alert.alert_detail}")
                        else:
                            assert False, ("multiple strat_alerts found with same brief but mismatched alert_details - "
                                           "only single strat_alert is expected, "
                                           f"expected {sample_detail}, found: {strat_alert.alert_detail}")

            assert alert_count == 1, f"Mismatched: alert count for alert_brief must be 1, found {alert_count}"


def test_start_alert_with_same_severity_n_brief_is_created_again_if_is_deleted(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify strat_alert once created if alert is deleted and same log line is again added,
    then strat_alert is created inplace of updating - verifies deletion and caching is working for strat_alert
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

        # first time creating alert
        sample_detail = f"sample detail string"
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        strat_alert = check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # deleting start_alert
        log_book_web_client.delete_strat_alert_client(strat_alert.id)
        check_alert_doesnt_exist_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # again adding same log - this time it must be again created
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)


def test_portfolio_alert_with_same_severity_n_brief_is_created_again_if_is_deleted(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify portfolio_alert once created if alert is deleted and same log line is again added,
    then portfolio_alert is created inplace of updating - verifies deletion and caching is working for portfolio_alert
    """
    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)
    sample_brief = "Sample Log to be created as portfolio_alert"
    log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

    # first time creating alert
    sample_detail = f"sample detail string"
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)

    time.sleep(time_wait * 2 + 1)
    portfolio_alert = check_alert_exists_in_portfolio_alert(log_str, sample_detail, log_file_path)

    # deleting start_alert
    log_book_web_client.delete_portfolio_alert_client(portfolio_alert.id)
    check_alert_doesnt_exist_in_portfolio_alert(log_str, sample_detail, log_file_path)

    # again adding same log - this time it must be again created
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)

    time.sleep(time_wait * 2 + 1)
    check_alert_exists_in_portfolio_alert(log_str, sample_detail, log_file_path)


def get_process_info_for_tail_executor(grep_pattern: str, log_file_name: str) -> str | None:
    res = subprocess.Popen(f"ps -ef | grep {grep_pattern}",
                           shell=True, stdout=subprocess.PIPE)
    lines = res.stdout.readlines()

    for line in lines:
        if log_file_name.removesuffix(".log") in line.decode("utf-8"):
            return line.decode("utf-8")
    return None


def file_watcher_check_tail_executor_start(log_file_name: str, log_file_path: str, grep_pattern: str):
    try:
        strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
        time_wait = strat_alert_config.get("transaction_timeout_secs")

        assert not os.path.exists(log_file_path), \
            f"sample log file must already not exists, but found at {log_file_path!r}"

        res = get_process_info_for_tail_executor(grep_pattern, log_file_name)
        if res is not None:
            assert False, \
                f"tail executor process must not already exist, found process info: {res}"

        # positive test
        if not os.path.exists(STRAT_EXECUTOR / "log"):
            os.mkdir(STRAT_EXECUTOR / "log")
        with open(log_file_path, "w"):
            pass

        time.sleep(2)
        assert os.path.exists(log_file_path), \
            f"Can't find sample log file: {log_file_path!r}"

        res = get_process_info_for_tail_executor(grep_pattern, log_file_name)
        if res is None:
            assert False, \
                f"Can't find tail executor process for sample log file: {log_file_path!r}"

        # checking if tail executor is functional for this log file
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name, line_no, f"{sample_brief};;; {sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_exists_in_portfolio_alert(log_str, sample_detail, log_file_path)

    except Exception as e:
        raise e
    finally:
        if os.path.exists(log_file_path):
            os.remove(log_file_path)    # removing file

        # killing tail_executor for log_file_path
        log_book_web_client.log_book_force_kill_tail_executor_query_client(log_file_path)

        # clearing cache
        log_book_web_client.log_book_remove_file_from_created_cache_query_client([log_file_path])


def test_file_watcher_check_tail_executor_start_with_complete_path(clean_and_set_limits):
    """
    Test to verify file_watcher to start tail_executor of log file which is registered to log_book with
    log_file_path - log_file at log_file_path is created dynamically and tail_executor is checked for it
    Note: In log_book, tail_executor register list contains one log_detail that is only meant to be used
    for this test which will be used to test
    """
    log_file_name = "sample_test.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name
    tail_process_grep_pattern = "tail_executor~test_street_book_with_full_path"

    file_watcher_check_tail_executor_start(log_file_name, log_file_path, tail_process_grep_pattern)


def test_file_watcher_check_tail_executor_start_with_pattern_path(clean_and_set_limits):
    """
    Test to verify file_watcher to start tail_executor of log file which is registered to log_book with
    pattern based file path
    Note: this test uses log_detail for street_book to use pattern based tail executor start handling
    """
    log_file_name = f"sample_100_test.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name
    tail_process_grep_pattern = "tail_executor~test_street_book_with_pattern"

    file_watcher_check_tail_executor_start(log_file_name, log_file_path, tail_process_grep_pattern)


def test_log_with_suitable_log_lvl_are_added_to_alerts(clean_and_set_limits):
    """
    Test to verify in non-debug mode only logs with error related lvl are added as alerts
    """
    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string"

    # Positive test
    for log_lvl in ["WARNING", "ERROR", "CRITICAL"]:
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2)
        check_alert_exists_in_portfolio_alert(log_str, sample_detail, log_file_path)

    # Negative test
    for log_lvl in ["DEBUG", "INFO", "SAMPLE"]:
        sample_brief = f"Sample Log not to be created as portfolio_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2)
        check_alert_doesnt_exist_in_portfolio_alert(log_str, sample_detail, log_file_path)


def test_strat_alert_unable_to_patch_are_created_as_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    # since only single strat is used in this test
    active_strat, executor_http_client = active_strat_n_executor_list[0]

    log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)
    sample_brief = "Sample Log to be created as strat_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)

    time.sleep(time_wait * 2 + 1)
    check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)


def test_restart_tail_executor(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify restart of tail executor - checks both restart with and without restart_date_time
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # restarting from latest line in log
        log_book_web_client.log_book_restart_tail_query_client(log_file_path)

        time.sleep(1)

        # checking if tail_executor is restarted
        sample_brief = "Sample Log to be created as strat_alert again"
        log_time = get_log_date_time()
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        strat_alert = check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)
        assert strat_alert.alert_count == 1, \
            f"Mismatched: expected strat_alert.alert_count: 1, found {strat_alert.alert_count=}"

        # restarting from before last-time restarted - also verifying if log is again executor
        log_book_web_client.log_book_restart_tail_query_client(log_file_path, str(log_time))
        time.sleep(1)

        time.sleep(time_wait * 2 + 1)
        strat_alert = check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)
        assert strat_alert.alert_count == 2, \
            f"Mismatched: expected strat_alert.alert_count: 2, found {strat_alert.alert_count=}"
        print(f"- Completed strat: {active_strat}")


def test_kill_tail_executor_n_clear_cache_(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify kill and cache clear queries work for tail executor - starts tail_executor, kills it and
    clears cache to check if tail executor is restarted for same file
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_name = f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        log_file_path = STRAT_EXECUTOR / "log" / log_file_name
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # restarting from latest line in log
        log_book_web_client.log_book_force_kill_tail_executor_query_client(log_file_path)

        time.sleep(1)

        # checking if tail_executor exists
        tail_process_grep_pattern = "tail_executor~street_book"
        res = get_process_info_for_tail_executor(tail_process_grep_pattern, log_file_name)
        if res is not None:
            assert False, \
                (f"tail executor process for sample log file: {log_file_path!r} must not exist after kill, "
                 f"found process info: {res}")

        # tail executor will not be restarted even if file still exists since file entry still exists in cache
        # removing file from cache to see if tail executor for file is started
        log_book_web_client.log_book_remove_file_from_created_cache_query_client(log_file_path)

        time.sleep(2)

        # checking if tail_executor is restarted
        sample_brief = "Sample Log to be created as strat_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        strat_alert = check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)
        assert strat_alert.alert_count == 1, \
            f"Mismatched: expected strat_alert.alert_count: 1, found {strat_alert.alert_count=}"


def test_delete_log_file_n_again_create_to_verify_tail(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify if tail is again started to file which is recreated again after deleting
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_name = f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        log_file_path = STRAT_EXECUTOR / "log" / log_file_name
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)

        # removing log file
        os.remove(log_file_path)

        # checking tail executor is still running
        tail_process_grep_pattern = "tail_executor~street_book"
        get_process_info_for_tail_executor(tail_process_grep_pattern, log_file_name)

        # again creating log file and checking is tail is restarted with new file
        with open(log_file_path, "w"):
            pass

        time.sleep(2)

        # checking if tail_executor is restarted
        sample_brief = "Sample Log to be created as strat_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)

        time.sleep(time_wait * 2 + 1)
        strat_alert = check_alert_exists_in_strat_alert(active_strat, log_str, sample_detail, log_file_path)
        assert strat_alert.alert_count == 1, \
            f"Mismatched: expected strat_alert.alert_count: 1, found {strat_alert.alert_count=}"

