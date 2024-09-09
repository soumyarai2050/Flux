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
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import get_alert_cache_key
from FluxPythonUtils.scripts.utility_functions import delete_mongo_document, create_mongo_document


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

    return alert_brief


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


def check_alert_exists_in_portfolio_alert(
        expected_alert_brief: str, log_file_path: str,
        expected_alert_detail_first: str,
        expected_alert_detail_latest: str | None = None) -> PortfolioAlertBaseModel:
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    start_time = DateTime.utcnow()
    for i in range(10):
        time.sleep(1)
        portfolio_alerts: List[PortfolioAlertBaseModel] = log_book_web_client.get_all_portfolio_alert_client()
        for portfolio_alert in portfolio_alerts:
            if portfolio_alert.alert_brief == expected_alert_brief:
                if (portfolio_alert.alert_meta.first_detail == expected_alert_detail_first and
                        portfolio_alert.alert_meta.latest_detail == expected_alert_detail_latest):
                    print("-" * 100)
                    print(f"Result: Found portfolio alert in {(DateTime.utcnow() - start_time).total_seconds()} secs")
                    print("-" * 100)
                    return portfolio_alert
                else:
                    if portfolio_alert.alert_meta.first_detail == expected_alert_detail_first:
                        assert False, ("portfolio_alert found with correct brief but mismatched "
                                       f"portfolio_alert.alert_meta.first_detail, "
                                       f"expected {expected_alert_detail_first}, "
                                       f"found: {portfolio_alert.alert_meta.first_detail}")
                    else:
                        assert False, ("portfolio_alert found with correct brief but mismatched "
                                       f"portfolio_alert.alert_meta.latest_detail, "
                                       f"expected {expected_alert_detail_latest}, "
                                       f"found: {portfolio_alert.alert_meta.latest_detail}")
    else:
        assert False, f"Cant find any portfolio_alert with {expected_alert_brief=}, {log_file_path=}"


def check_alert_doesnt_exist_in_portfolio_alert(expected_alert_brief: str, log_file_path: str):
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    for i in range(10):
        time.sleep(1)
        portfolio_alerts: List[PortfolioAlertBaseModel] = log_book_web_client.get_all_portfolio_alert_client()
        for portfolio_alert in portfolio_alerts:
            if portfolio_alert.alert_brief == expected_alert_brief:
                assert False, (f"Unexpected: portfolio_alert must not exist with strat_brief: "
                               f"{expected_alert_brief}, found {portfolio_alert=}, {log_file_path=}")


def check_alert_exists_in_strat_alert(active_strat: PairStratBaseModel, expected_alert_brief: str,
                                      log_file_path: str, expected_alert_detail_first: str,
                                      expected_alert_detail_latest: str | None = None) -> StratAlertBaseModel:
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    start_time = DateTime.utcnow()
    for i in range(10):
        time.sleep(1)
        strat_alerts: List[StratAlertBaseModel] = (
            log_book_web_client.filtered_strat_alert_by_strat_id_query_client(strat_id=active_strat.id))
        for strat_alert in strat_alerts:
            if strat_alert.alert_brief == expected_alert_brief:
                if (strat_alert.alert_meta.first_detail == expected_alert_detail_first and
                        strat_alert.alert_meta.latest_detail == expected_alert_detail_latest):
                    print("-"*100)
                    print(f"Result: Found strat alert in {(DateTime.utcnow()-start_time).total_seconds()} secs")
                    print("-"*100)
                    return strat_alert
                else:
                    if strat_alert.alert_meta.first_detail == expected_alert_detail_first:
                        assert False, ("strat_alert found with correct brief but mismatched "
                                       f"strat_alert.alert_meta.first_detail, "
                                       f"expected {expected_alert_detail_first}, "
                                       f"found: {strat_alert.alert_meta.first_detail}")
                    else:
                        assert False, ("strat_alert found with correct brief but mismatched "
                                       f"strat_alert.alert_meta.latest_detail, "
                                       f"expected {expected_alert_detail_latest}, "
                                       f"found: {strat_alert.alert_meta.latest_detail}")
    else:
        assert False, f"Cant find any strat_alert with {expected_alert_brief=}, {log_file_path=}"


def check_alert_doesnt_exist_in_strat_alert(active_strat: PairStratBaseModel | None, expected_alert_brief: str,
                                            log_file_path: str):
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    for i in range(10):
        time.sleep(1)
        if active_strat is not None:
            strat_alerts: List[StratAlertBaseModel] = (
                log_book_web_client.filtered_strat_alert_by_strat_id_query_client(strat_id=active_strat.id))
        else:
            strat_alerts: List[StratAlertBaseModel] = (
                log_book_web_client.get_all_strat_alert_client())
        for strat_alert in strat_alerts:
            if strat_alert.alert_brief == expected_alert_brief:
                assert False, (f"Unexpected: strat_alert must not exist with alert_brief: {expected_alert_brief}, "
                               f"found strat_alert: {strat_alert}, {log_file_path=}")


@pytest.mark.log_book
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
        time.sleep(1)

        check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)

    # Negative test
    # creating random log file with id of which no strat running
    non_existing_strat_id = 100
    log_file_name = f"street_book_{non_existing_strat_id}_logs_{frmt_date}.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name
    try:
        # creating log file
        with open(log_file_path, "w"):
            pass

        strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
        time_wait = strat_alert_config.get("transaction_timeout_secs")

        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)

        sample_brief = f"Sample Log not to be created as strat_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_doesnt_exist_in_strat_alert(None, sample_brief, log_file_path)
    except Exception as e:
        raise e
    finally:
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

            # killing tail_executor for log_file_path
            log_book_web_client.log_book_force_kill_tail_executor_query_client(str(log_file_path))

            # clearing cache
            log_book_web_client.log_book_remove_file_from_created_cache_query_client([str(log_file_path)])


@pytest.mark.log_book
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
            time.sleep(1)

            check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)

        # Negative test
        non_existing_strat_log_key = get_symbol_side_key([("CB_Sec_100", Side.BUY)])

        sample_brief = f"Sample Log not to be created as strat_alert, key: {non_existing_strat_log_key}"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_doesnt_exist_in_strat_alert(active_strat, sample_brief, log_file_path)


@pytest.mark.log_book
def test_log_to_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs not having symbol-side key or strat_id are created as portfolio_alerts
    """
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)

    # Negative test
    sample_brief = f"Sample Log not to be created as portfolio_alert"
    sample_detail = "sample detail string"
    log_str = get_log_line_str("SAMPLE", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_doesnt_exist_in_portfolio_alert(sample_brief, log_file_path)


@pytest.mark.log_book
def test_log_to_update_db(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs having db pattern updates db
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

        # not checking sec=verity update since it gets updated very often from code and test fails - anyways
        # test checks update functionality so if it works for rest fields it is still good
        db_json_list = [
            {"strat_alert_count": random.randint(1, 100)},
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


@pytest.mark.log_book
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
        first_found_detail = None
        latest_found_detail = None
        for log_count in range(1, total_log_counts+1):
            sample_detail = f"sample detail string - {log_count}"
            if log_count == 1:
                first_found_detail = sample_detail
            else:
                latest_found_detail = sample_detail

            log_str = get_log_line_str(log_lvl, sample_file_name,
                                       line_no, f"{sample_brief};;;{sample_detail}")
            add_log_to_file(log_file_path, log_str)
            time.sleep(time_wait * 2 + 1)

            alert_count = 0
            strat_alerts: List[StratAlertBaseModel] = (
                log_book_web_client.filtered_strat_alert_by_strat_id_query_client(strat_id=active_strat.id))
            expected_alert_brief = get_expected_brief(sample_brief)
            for strat_alert in strat_alerts:
                if strat_alert.alert_brief == expected_alert_brief:
                    alert_count += 1

                    assert strat_alert.alert_meta.first_detail == first_found_detail, \
                        (f"Mismatched strat_alert.alert_meta.first_detail: expected: {first_found_detail}, "
                         f"found: {strat_alert.alert_meta.first_detail}")
                    assert strat_alert.alert_meta.latest_detail == latest_found_detail, \
                        (f"Mismatched strat_alert.alert_meta.latest_detail: expected: {latest_found_detail}, "
                         f"found: {strat_alert.alert_meta.latest_detail}")
                    assert strat_alert.alert_count == log_count, \
                        (f"Mismatched alert_count: expected: {total_log_counts}, "
                         f"found {strat_alert.alert_count=} ")
                    break
            else:
                assert False, \
                    (f"Can't Find any matching strat_alert for {active_strat.id=}, "
                     f"{expected_alert_brief=}, severity: {log_lvl}")

            assert alert_count == 1, f"Mismatched: alert count for alert_brief must be 1, found {alert_count}"


def verify_alert_in_strat_alert_cache(strat_alert: StratAlertBaseModel):
    strat_alert_id_to_obj_cache: List[StratAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_strat_alert_id_in_strat_alert_id_to_obj_cache_dict_query_client(strat_alert.id))
    assert len(strat_alert_id_to_obj_cache) == 1, \
        ("Received unexpected strat_alert_id_to_obj_cache - "
         "verify_strat_alert_id_in_strat_alert_id_to_obj_cache_dict_query_client failed, "
         f"{strat_alert_id_to_obj_cache=}")
    assert strat_alert_id_to_obj_cache[0].is_id_present, \
        f"{strat_alert.id=} must exist in strat_alert_id_to_obj_cache_dict in log analyzer"

    strat_alert_key = get_alert_cache_key(strat_alert.severity, strat_alert.alert_brief,
                                          strat_alert.alert_meta.component_file_path,
                                          strat_alert.alert_meta.source_file_name,
                                          strat_alert.alert_meta.line_num)
    container_obj_list: List[StratAlertCacheDictByStratIdDictBaseModel] = (
        log_book_web_client.verify_strat_alert_id_in_strat_alert_cache_dict_by_strat_id_dict_query_client(
            strat_alert.strat_id, strat_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - "
         "verify_strat_alert_id_in_strat_alert_cache_dict_by_strat_id_dict_query_client failed, "
         f"{container_obj_list=}")
    assert container_obj_list[0].is_key_present, \
        (f"{strat_alert.id=} must exist in strat_alert_cache_dict_by_strat_id_dict of "
         f"{strat_alert.strat_id} in log analyzer")


def verify_alert_not_in_strat_alert_cache(strat_alert: StratAlertBaseModel):
    strat_alert_id_to_obj_cache: List[StratAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_strat_alert_id_in_strat_alert_id_to_obj_cache_dict_query_client(strat_alert.id))
    assert len(strat_alert_id_to_obj_cache) == 1, \
        ("Received unexpected strat_alert_id_to_obj_cache - "
         "verify_strat_alert_id_in_strat_alert_id_to_obj_cache_dict_query_client failed, "
         f"{strat_alert_id_to_obj_cache=}")
    assert not strat_alert_id_to_obj_cache[0].is_id_present, \
        f"{strat_alert.id=} must not exist in strat_alert_id_to_obj_cache_dict in log analyzer after deletion"

    strat_alert_key = get_alert_cache_key(strat_alert.severity, strat_alert.alert_brief,
                                          strat_alert.alert_meta.component_file_path,
                                          strat_alert.alert_meta.source_file_name,
                                          strat_alert.alert_meta.line_num)
    container_obj_list: List[StratAlertCacheDictByStratIdDictBaseModel] = (
        log_book_web_client.verify_strat_alert_id_in_strat_alert_cache_dict_by_strat_id_dict_query_client(
            strat_alert.strat_id, strat_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - "
         "verify_strat_alert_id_in_strat_alert_cache_dict_by_strat_id_dict_query_client failed, "
         f"{container_obj_list=}")
    assert not container_obj_list[0].is_key_present, \
        (f"{strat_alert.id=} must not exist in strat_alert_cache_dict_by_strat_id_dict of {strat_alert.strat_id} "
         f"in log analyzer after deletion")


def verify_alert_in_portfolio_alert_cache(portfolio_alert: PortfolioAlertBaseModel):
    portfolio_alert_id_to_obj_cache: List[PortfolioAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_portfolio_alert_id_in_get_portfolio_alert_id_to_obj_cache_dict_query_client(portfolio_alert.id))
    assert len(portfolio_alert_id_to_obj_cache) == 1, \
        ("Received unexpected portfolio_alert_id_to_obj_cache - "
         "verify_portfolio_alert_id_in_get_portfolio_alert_id_to_obj_cache_dict_query_client failed, "
         f"{portfolio_alert_id_to_obj_cache=}")
    assert portfolio_alert_id_to_obj_cache[0].is_id_present, \
        f"{portfolio_alert.id=} must exist in portfolio_alert_id_to_obj_cache_dict in log analyzer"

    strat_alert_key = get_alert_cache_key(portfolio_alert.severity, portfolio_alert.alert_brief,
                                          portfolio_alert.alert_meta.component_file_path,
                                          portfolio_alert.alert_meta.source_file_name,
                                          portfolio_alert.alert_meta.line_num)
    container_obj_list: List[PortfolioAlertCacheDictBaseModel] = (
        log_book_web_client.verify_portfolio_alerts_cache_dict_query_client(strat_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - verify_portfolio_alerts_cache_dict_query_client failed, "
         f"{container_obj_list=}")
    assert container_obj_list[0].is_key_present, \
        f"{portfolio_alert.id=} must exist in portfolio_alerts_cache_dict in log analyzer"


def verify_alert_not_in_portfolio_alert_cache(portfolio_alert: PortfolioAlertBaseModel):
    portfolio_alert_id_to_obj_cache: List[PortfolioAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_portfolio_alert_id_in_get_portfolio_alert_id_to_obj_cache_dict_query_client(portfolio_alert.id))
    assert len(portfolio_alert_id_to_obj_cache) == 1, \
        ("Received unexpected portfolio_alert_id_to_obj_cache - "
         "verify_portfolio_alert_id_in_get_portfolio_alert_id_to_obj_cache_dict_query_client failed, "
         f"{portfolio_alert_id_to_obj_cache=}")
    assert not portfolio_alert_id_to_obj_cache[0].is_id_present, \
        f"{portfolio_alert.id=} must not exist in portfolio_alert_id_to_obj_cache_dict in log analyzer after deletion"

    strat_alert_key = get_alert_cache_key(portfolio_alert.severity, portfolio_alert.alert_brief,
                                          portfolio_alert.alert_meta.component_file_path,
                                          portfolio_alert.alert_meta.source_file_name,
                                          portfolio_alert.alert_meta.line_num)
    container_obj_list: List[PortfolioAlertCacheDictBaseModel] = (
        log_book_web_client.verify_portfolio_alerts_cache_dict_query_client(strat_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - verify_portfolio_alerts_cache_dict_query_client failed, "
         f"{container_obj_list=}")
    assert not container_obj_list[0].is_key_present, \
        f"{portfolio_alert.id=} must not exist in portfolio_alerts_cache_dict in log analyzer after deletion"


@pytest.mark.log_book
def test_to_verify_strat_alert_cache_is_cleared_in_delete_strat_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    created_strat_alert_list: List[StratAlertBaseModel] = []
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
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        created_strat_alert_list.append(strat_alert)

        # verifying that strat_alert was added in cache
        verify_alert_in_strat_alert_cache(strat_alert)

    # deleting 1 strat_alert using delete_strat_alert_client out of 3 strat_alerts to verifying and then calling
    # delete_all_strat_alert_client to verify remaining 2 also are removed from cache
    strat_alert = created_strat_alert_list.pop(0)
    log_book_web_client.delete_strat_alert_client(strat_alert.id)
    verify_alert_not_in_strat_alert_cache(strat_alert)

    log_book_web_client.delete_all_strat_alert_client()
    for strat_alert in created_strat_alert_list:
        verify_alert_not_in_strat_alert_cache(strat_alert)


@pytest.mark.log_book
def test_to_verify_remove_strat_alerts_for_strat_id_query(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    created_strat_alert_list: List[StratAlertBaseModel] = []
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
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        created_strat_alert_list.append(strat_alert)

        # verifying that strat_alert was added in cache
        verify_alert_in_strat_alert_cache(strat_alert)

    for strat_alert in created_strat_alert_list:
        log_book_web_client.remove_strat_alerts_for_strat_id_query_client(strat_alert.strat_id)

        # verifying if strat_id exists in strat_alert_cache_dict_by_strat_id_dict
        container_obj_list = (
            log_book_web_client.verify_strat_id_in_strat_alert_cache_dict_by_strat_id_dict_query_client(
                strat_alert.strat_id))
        assert len(container_obj_list) == 1, \
            ("Received unexpected container_obj_list - "
             "verify_strat_id_in_strat_alert_cache_dict_by_strat_id_dict_query_client failed, "
             f"{container_obj_list=}")
        assert not container_obj_list[0].is_id_present, \
            f"{strat_alert.strat_id=} must not exist in strat_alert_cache_dict_by_strat_id_dict in log analyzer"

        # verifying other cache also
        verify_alert_not_in_strat_alert_cache(strat_alert)


@pytest.mark.log_book
def test_to_verify_portfolio_alert_cache_is_cleared_in_delete_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    portfolio_alert = check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)
    # verifying that alert was added to cache
    verify_alert_in_portfolio_alert_cache(portfolio_alert)

    log_book_web_client.delete_portfolio_alert_client(portfolio_alert.id)
    # verifying that alert got cleared from cache
    verify_alert_not_in_portfolio_alert_cache(portfolio_alert)


# @ failing: internal cache in tail executor is not removed when deleted - when obj is again created
# it is expected to be created clean but has last obj data from tail executor
@pytest.mark.log_book
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
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)

        # deleting start_alert
        log_book_web_client.delete_strat_alert_client(strat_alert.id)
        check_alert_doesnt_exist_in_strat_alert(active_strat, sample_brief, log_file_path)

        # again adding same log - this time it must be again created
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)


# @ failing: internal cache in tail executor is not removed when deleted - when obj is again created
# it is expected to be created clean but has last obj data from tail executor
@pytest.mark.log_book
def test_portfolio_alert_with_same_severity_n_brief_is_created_again_if_is_deleted(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify portfolio_alert once created if alert is deleted and same log line is again added,
    then portfolio_alert is created inplace of updating - verifies deletion and caching is working for portfolio_alert
    """
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
    time.sleep(1)

    portfolio_alert = check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)

    # deleting start_alert
    log_book_web_client.delete_portfolio_alert_client(portfolio_alert.id)
    check_alert_doesnt_exist_in_portfolio_alert(sample_brief, log_file_path)

    # again adding same log - this time it must be again created
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)


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
        time.sleep(1)

        check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)

    except Exception as e:
        raise e
    finally:
        if os.path.exists(log_file_path):
            os.remove(log_file_path)    # removing file

        # killing tail_executor for log_file_path
        log_book_web_client.log_book_force_kill_tail_executor_query_client(str(log_file_path))

        # clearing cache
        log_book_web_client.log_book_remove_file_from_created_cache_query_client([str(log_file_path)])


@pytest.mark.log_book
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

    file_watcher_check_tail_executor_start(log_file_name, str(log_file_path), tail_process_grep_pattern)


@pytest.mark.log_book
def test_file_watcher_check_tail_executor_start_with_pattern_path(clean_and_set_limits):
    """
    Test to verify file_watcher to start tail_executor of log file which is registered to log_book with
    pattern based file path
    Note: this test uses log_detail for street_book to use pattern based tail executor start handling
    """
    log_file_name = f"sample_100_test.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name
    tail_process_grep_pattern = "tail_executor~test_street_book_with_pattern"

    file_watcher_check_tail_executor_start(log_file_name, str(log_file_path), tail_process_grep_pattern)


@pytest.mark.log_book
def test_log_with_suitable_log_lvl_are_added_to_alerts(clean_and_set_limits):
    """
    Test to verify in non-debug mode only logs with error related lvl are added as alerts
    """
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
        time.sleep(1)

        check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)

    # Negative test
    log_lvl = "SAMPLE"
    sample_brief = f"Sample Log not to be created as portfolio_alert"
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_doesnt_exist_in_portfolio_alert(sample_brief, log_file_path)


@pytest.mark.log_book
def test_strat_alert_unable_to_patch_are_created_as_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

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
    time.sleep(1)

    check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)


@pytest.mark.log_book
def test_restart_tail_executor(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify restart of tail executor
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

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
        time.sleep(1)

        check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)

        # restarting from latest line in log
        restart_date_time = get_log_date_time()
        log_book_web_client.log_book_restart_tail_query_client(str(log_file_path), restart_date_time)

        time.sleep(2)

        # checking if tail_executor is restarted
        sample_brief = "Sample Log to be created as strat_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        assert strat_alert.alert_count == 1, \
            f"Mismatched: expected strat_alert.alert_count: 1, found {strat_alert.alert_count=}"

        # restarting from before last-time restarted - also verifying if log is again executed
        log_book_web_client.log_book_restart_tail_query_client(str(log_file_path), restart_date_time)
        time.sleep(10)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path,
                                                        expected_alert_detail_first=sample_detail,
                                                        expected_alert_detail_latest=sample_detail)
        assert strat_alert.alert_count == 2, \
            f"Mismatched: expected strat_alert.alert_count: 2, found {strat_alert.alert_count=}"


@pytest.mark.log_book
def test_tail_executor_restarts_if_tail_error_occurs(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify if tail executor has error tail executor is restarted from last line it processed
    """
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)
    sample_brief = "Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    portfolio_alert = check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)
    assert portfolio_alert.alert_count == 1, \
        f"Mismatched: expected portfolio_alert.alert_count: 1, found {portfolio_alert.alert_count=}"

    # putting error log in file
    error_log_str = "tail: giving up on this name"
    add_log_to_file(log_file_path, error_log_str)
    time.sleep(1)

    # removing this error log before restart to tail executor to avoid cyclic restarts
    os.system(f"gsed -i '/{error_log_str}/d' {log_file_path}")

    time.sleep(10)

    portfolio_alert = check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail, sample_detail)
    assert portfolio_alert.alert_count == 2, \
        f"Mismatched: expected portfolio_alert.alert_count: 2, found {portfolio_alert.alert_count=}"


@pytest.mark.log_book
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
        time.sleep(1)

        check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)

        # restarting from latest line in log
        log_book_web_client.log_book_force_kill_tail_executor_query_client(str(log_file_path))

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
        log_book_web_client.log_book_remove_file_from_created_cache_query_client([str(log_file_path)])

        time.sleep(2)

        # checking if tail_executor is restarted
        sample_brief = "Sample Log to be created as strat_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        assert strat_alert.alert_count == 1, \
            f"Mismatched: expected strat_alert.alert_count: 1, found {strat_alert.alert_count=}"


@pytest.mark.log_book
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
        time.sleep(1)

        check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)

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
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        assert strat_alert.alert_count == 1, \
            f"Mismatched: expected strat_alert.alert_count: 1, found {strat_alert.alert_count=}"


@pytest.mark.log_book
def test_strat_alert_with_no_strat_with_symbol_side_is_sent_to_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    strat_alert_config: Dict = la_config_yaml_dict.get("strat_alert_config")
    time_wait = strat_alert_config.get("transaction_timeout_secs")

    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    non_existing_strat_log_key = get_symbol_side_key([("CB_Sec_100", Side.BUY)])

    sample_brief = f"Sample Log not to be created as strat_alert, key: {non_existing_strat_log_key}"
    sample_detail = "sample detail string"
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    time.sleep(time_wait * 2 + 1)
    # checking if any strat_alert contains this alert content
    strat_alert_list = log_book_web_client.get_all_strat_alert_client()

    for strat_alert in strat_alert_list:
        if strat_alert.alert_brief == sample_brief:
            assert False, \
                f"No start alert must exists with having alert_brief: {sample_brief}, found alert: {strat_alert}"

    portfolio_alert_list = log_book_web_client.get_all_portfolio_alert_client()
    for portfolio_alert in portfolio_alert_list:
        if portfolio_alert.alert_brief == sample_brief:
            break
    else:
        assert False, \
            ("Failed strat_alert must be created as portfolio_alert of same severity and brief, but couldn't find "
             "any portfolio_alert")


@pytest.mark.log_book
def test_strat_alert_with_no_strat_with_strat_id_is_sent_to_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Created street_book log file manually to start tail_executor with some random id and verify since strat
    doesn't exist alert is sent to portfolio alert
    """
    log_file_name = f"sample_test.log"
    executor_log_dir_path = STRAT_EXECUTOR / "log"
    log_file_path = executor_log_dir_path / log_file_name

    # crating log dir if not exists
    if not os.path.exists(executor_log_dir_path):
        os.mkdir(executor_log_dir_path)

    # creating log file
    with open(log_file_path, "w"):
        pass

    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log not to be created as strat_alert"
    sample_detail = "sample detail string"
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    for _ in range(10):
        time.sleep(1)
        # checking if any strat_alert contains this alert content
        strat_alert_list = log_book_web_client.get_all_strat_alert_client()

        for strat_alert in strat_alert_list:
            if strat_alert.alert_brief == sample_brief:
                assert False, \
                    f"No start alert must exists with having alert_brief: {sample_brief}, found alert: {strat_alert}"

        portfolio_alert_list = log_book_web_client.get_all_portfolio_alert_client()
        for portfolio_alert in portfolio_alert_list:
            if portfolio_alert.alert_brief == sample_brief:
                break
        else:
            continue
        break
    else:
        assert False, \
            ("Failed strat_alert must be created as portfolio_alert of same severity and brief, but couldn't find "
             "any portfolio_alert")


@pytest.mark.log_book
def test_strat_alert_put_all_failed_alerts_goes_to_portfolio_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    created_alerts_list = []
    for active_strat, executor_http_client in active_strat_n_executor_list:
        log_file_name = f"street_book_{active_strat.id}_logs_{frmt_date}.log"
        log_file_path = STRAT_EXECUTOR / "log" / log_file_name
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as strat_alert"
        sample_detail = "sample detail string"
        print(f"Checking file: {log_file_path!r}")

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        created_alerts_list.append(strat_alert)

        # manually deleting strat_alert - deleting through client will trigger cache update which will avoid
        # recreation of issue and will trigger create of alert next time instead of update
        mongo_uri = get_mongo_server_uri()
        db_name = "log_book"
        collection_name = "StratAlert"
        delete_filter = {"_id": strat_alert.id}
        res = delete_mongo_document(mongo_uri, db_name, collection_name, delete_filter)
        assert res, f"delete_mongo_document failed for {strat_alert.id=}"

        try:
            updated_sample_detail = "updated sample detail string"
            log_str = get_log_line_str("ERROR", sample_file_name,
                                       line_no, f"{sample_brief};;;{updated_sample_detail}")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

            # verifying strat_alert not exists
            check_alert_doesnt_exist_in_strat_alert(active_strat, sample_brief, log_file_path)

            # verifying portfolio alert contains failed strat alert
            check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail, updated_sample_detail)
        except Exception as e:
            raise e
        finally:
            if res:
                # creating document back to delete cache for that entry
                create_mongo_document(mongo_uri, db_name, collection_name, strat_alert.to_dict())


@pytest.mark.log_book
def test_portfolio_alert_put_all_failed_alerts_goes_to_portfolio_fail_alert_log(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    portfolio_alert = check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)

    # manually deleting portfolio_alert - deleting through client will trigger cache update which will avoid
    # recreation of issue and will trigger create of alert next time instead of update
    mongo_uri = get_mongo_server_uri()
    db_name = "log_book"
    delete_filter = {"_id": portfolio_alert.id}
    collection_name = "PortfolioAlert"
    res = delete_mongo_document(mongo_uri, db_name, collection_name, delete_filter)
    assert res, f"delete_mongo_document failed for {portfolio_alert.id=}"

    sample_detail = "updated sample detail string"

    try:
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)
        check_alert_doesnt_exist_in_portfolio_alert(sample_brief, log_file_path)

        # checking alert is present in portfolio_alert_fail_logs
        portfolio_alert_fail_logger_name = f"portfolio_alert_fail_logs_{frmt_date}.log"
        portfolio_alert_fail_logger_path = LOG_ANALYZER_DIR / "log" / portfolio_alert_fail_logger_name
        with open(portfolio_alert_fail_logger_path, "r") as fl:
            lines = fl.readlines()

            expected_strat_brief = get_expected_brief(sample_brief)
            for line in lines:
                if expected_strat_brief in line:
                    break
            else:
                assert False, ("Can't find info for portfolio_fail in portfolio_fail_log file, "
                               f"expected brief: {expected_strat_brief}, expected detail: {sample_detail}, "
                               f"expected severity: ERROR")
    except Exception as e:
        raise e
    finally:
        if res:
            # creating document back to delete cache for that entry
            create_mongo_document(mongo_uri, db_name, collection_name, portfolio_alert.to_dict())


def kill_perf_bench_server():
    for _ in range(10):
        p_id: int = get_pid_from_port(parse_to_int(PERF_BENCH_BEANIE_PORT))
        if p_id is not None:
            os.kill(p_id, signal.SIGKILL)
            print(f"Killed perf bench process: {p_id}, port: {PERF_BENCH_BEANIE_PORT}")
            return True
        else:
            print("get_pid_from_port return None instead of pid - "
                  "couldn't kill perf bench server, will leave it running")
        time.sleep(2)
    else:
        return False


@pytest.mark.log_book
def test_check_create_call_in_queue_handler_waits_if_server_is_down(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Kills perf benchmark server if already running, updates the config file for log analyzer with suitable
    values for perf_bench_client_connection_fail_retry_secs and perf benchmark transaction_timeout_secs,
    then starts new tail executor that will initiate with these values, then checks with closed server,
    it should first attempt to call perf benchmark client and then wait for
    perf_bench_client_connection_fail_retry_secs and then retry and repeat if still server is not up, then test
    starts perf_benchmark server and then checks if it calls client and now it doesn't wait again, kills
    perf_benchmark server at the end if server was not up before start else keeps it running
    """
    log_file_name = f"street_book_100_logs_{frmt_date}.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name

    tail_executor_log_file_name = \
        f"tail_executor~street_book~{log_file_name.removesuffix('.log')}_logs_{frmt_date}.log"
    tail_executor_log_file = LOG_ANALYZER_DIR / "log" / "tail_executors" / tail_executor_log_file_name

    config_file_path = LOG_ANALYZER_DIR / "data" / f"config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    is_perf_bench_server_up_already: bool
    try:
        perf_benchmark_web_client.get_all_ui_layout_client()
    except Exception as e:
        is_perf_bench_server_up_already = False
    else:
        is_perf_bench_server_up_already = True
        res = kill_perf_bench_server()
        assert res, (f"Unexpected: Can't kill perf bench server - "
                     f"Can't find any pid from port {PERF_BENCH_BEANIE_PORT}")

    try:
        # updating yaml_configs according to this test
        perf_bench_client_connection_fail_retry_secs = 60    # 60 secs
        transaction_timeout_secs = 10  # secs
        config_dict["perf_bench_client_connection_fail_retry_secs"] = perf_bench_client_connection_fail_retry_secs
        config_dict["raw_perf_data_config"]["transaction_timeout_secs"] = transaction_timeout_secs
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # creating log file
        if not os.path.exists(STRAT_EXECUTOR / "log"):
            os.mkdir(STRAT_EXECUTOR / "log")
        with open(log_file_path, "w"):
            pass

        time.sleep(2)
        assert os.path.exists(tail_executor_log_file), \
            f"tail executor must have started and created a log file {tail_executor_log_file} but can't find"

        log_str = (f"{get_log_date_time()} : TIMING : [sample_file.py : 575] : "
                   f"_timeit_sample_callable~2024-05-11 14:54:08.398837+00:00~0.008737_timeit_")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        time.sleep(transaction_timeout_secs+2)

        already_checked_logs = []
        expected_log_substr = ("Connection Error occurred while calling create_all_raw_performance_data_client, "
                               f"will stay on wait for {perf_bench_client_connection_fail_retry_secs} "
                               f"secs and again retry - ignoring all data for this call")
        with open(tail_executor_log_file, "r") as fl:
            lines = fl.readlines()

            for line in lines:
                if expected_log_substr in line:
                    already_checked_logs.append(line)
                    break
            else:
                assert False, ("Can't find substring for connection issue in any log line when server is "
                               f"down in {tail_executor_log_file}")

        log_str = (f"{get_log_date_time()} : TIMING : [sample_file.py : 575] : "
                   f"_timeit_sample_callable~2024-05-11 14:54:08.398837+00:00~0.008737_timeit_")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)
        # checking that queue handler will wait for perf_bench_client_connection_fail_retry_secs after fail client call
        total_iters = 5
        for _ in range(total_iters):
            with (open(tail_executor_log_file, "r") as fl):
                lines = fl.readlines()

                for line in lines:
                    if expected_log_substr in line and line not in already_checked_logs:
                        assert False, ("client call must not happen till perf_bench_client_connection_fail_retry_secs "
                                       "are breached but found call again")
            time.sleep(transaction_timeout_secs)

        # waiting more few secs to breach perf_bench_client_connection_fail_retry_secs and retry again
        time.sleep((perf_bench_client_connection_fail_retry_secs - total_iters * transaction_timeout_secs) +
                   transaction_timeout_secs + 2)

        with open(tail_executor_log_file, "r") as fl:
            lines = fl.readlines()

            for line in lines:
                if expected_log_substr in line and line not in already_checked_logs:
                    already_checked_logs.append(line)
                    break
            else:
                assert False, ("Can't find substring for connection issue in any log line when server is "
                               f"down in {tail_executor_log_file} after sleep wait")

        # restarting perf bench server
        perf_bench_server_scripts_dir = PERF_BENCH_DIR / "scripts"
        subprocess.Popen(["python", "launch_msgspec_fastapi.py"], cwd=perf_bench_server_scripts_dir)

        log_str = (f"{get_log_date_time()} : TIMING : [sample_file.py : 575] : "
                   f"_timeit_sample_callable~2024-05-11 14:54:08.398837+00:00~0.008737_timeit_")
        add_log_to_file(log_file_path, log_str)
        time.sleep(perf_bench_client_connection_fail_retry_secs + transaction_timeout_secs + 2)
        with (open(tail_executor_log_file, "r") as fl):
            lines = fl.readlines()

            for line in lines:
                if expected_log_substr in line and line not in already_checked_logs:
                    assert False, "client call must not fail since server has been started"

    except Exception as e:
        raise e
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

        if os.path.exists(log_file_path):
            os.remove(log_file_path)

            # killing tail_executor for log_file_path
            log_book_web_client.log_book_force_kill_tail_executor_query_client(str(log_file_path))

            # clearing cache
            log_book_web_client.log_book_remove_file_from_created_cache_query_client([str(log_file_path)])

        if not is_perf_bench_server_up_already:
            res = kill_perf_bench_server()
            if not res:
                print(f"Unexpected: Can't kill perf bench server - "
                      f"Can't find any pid from port {PERF_BENCH_BEANIE_PORT}")
        # else not required: if server was already running then keep it running


def check_log_info_fields_in_alert(alert_obj: StratAlertBaseModel | PortfolioAlertBaseModel,
                                   component_file_path: str, source_file_name: str, line_no: int):
    assert alert_obj.alert_meta.component_file_path == component_file_path, \
        (f"Mismatched: expected component_file_path: {component_file_path}, found "
         f"{alert_obj.alert_meta.component_file_path=}")
    assert alert_obj.alert_meta.source_file_name == source_file_name, \
        (f"Mismatched: expected source_file_name: {source_file_name}, found "
         f"{alert_obj.alert_meta.source_file_name=}")
    assert alert_obj.alert_meta.line_num == line_no, \
        (f"Mismatched: expected line_num: {line_no}, found "
         f"{alert_obj.alert_meta.line_num=}")
    assert alert_obj.alert_meta.alert_create_date_time is not None, \
        f"Mismatched: expected alert_create_date_time not None, found None"


def test_log_info_in_alerts(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_strat: PairStratBaseModel
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    # StratAlert test
    for active_strat, executor_http_client in active_strat_n_executor_list:
        line_no = random.randint(1, 100)
        log_key = get_symbol_side_key([(active_strat.pair_strat_params.strat_leg1.sec.sec_id,
                                        active_strat.pair_strat_params.strat_leg1.side)])

        sample_brief = f"Sample Log to be created as strat_alert key: {log_key}"
        sample_detail = "sample detail string for strat alert"

        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)
        strat_alert = check_alert_exists_in_strat_alert(active_strat, sample_brief, log_file_path, sample_detail)
        check_log_info_fields_in_alert(strat_alert, str(log_file_path), sample_file_name, line_no)

    # PortfolioAlert test
    sample_brief = f"Sample Log to be created as portfolio_alert"
    sample_detail = "sample detail string for portfolio alert"
    line_no = random.randint(1, 100)

    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)
    portfolio_alert = check_alert_exists_in_portfolio_alert(sample_brief, log_file_path, sample_detail)
    check_log_info_fields_in_alert(portfolio_alert, str(log_file_path), sample_file_name, line_no)


def test_check_background_logs_alert_handling(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_name = f"phone_book_background_logs.log"
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / log_file_name

    if not os.path.exists(log_file_path):
        with open(log_file_path, "w"):
            pass
    time.sleep(5)

    # verifying tail executor for background logs
    tail_process_grep_pattern = "tail_executor~phone_book_background_debug"
    res = get_process_info_for_tail_executor(tail_process_grep_pattern, log_file_name)
    if res is None:
        assert False, \
            f"tail executor process must exist for background logs"

    # Sample Exception
    log_str: List[str] = [
        "Traceback (most recent call last):",
        '  File "/home/scratches/scratch.py", line 1300, in <module>',
        '    raise Exception("SAMPLE EXCEPTION")',
        "Exception: SAMPLE EXCEPTION"
    ]
    for line in log_str:
        add_log_to_file(log_file_path, line)
        time.sleep(1)

    for _ in range(10):
        portfolio_alerts = log_book_web_client.get_all_portfolio_alert_client()
        for portfolio_alert in portfolio_alerts:
            if portfolio_alert.alert_brief == log_str[-1]:
                break
        else:
            time.sleep(1)
        break
    else:
        assert False, "Can't find alert containing error msg in brief"


def check_perf_of_alerts(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, alert_counts: int):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_strat, _ = active_strat_n_executor_list[0]

    log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    log_str = ""
    sample_detail = ""
    sample_brief = f"Sample Log to be created as strat_alert"
    log_lvl = "CRITICAL"
    for _ in range(10):
        for i in range(alert_counts):
            sample_detail = f"sample detail string {i}"

            # Positive test
            log_str = get_log_line_str(log_lvl, sample_file_name,
                                       line_no, f"{sample_brief};;;{sample_detail}")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

        start_time = DateTime.utcnow()
        expected_alert_brief = get_expected_brief(sample_brief)
        for i in range(10):
            strat_alerts: List[StratAlertBaseModel] = log_book_web_client.get_all_strat_alert_client()
            for strat_alert in strat_alerts:
                if strat_alert.alert_brief == expected_alert_brief:
                    if strat_alert.alert_meta.latest_detail == sample_detail:
                        print("-"*100)
                        print(f"Result: strat_alert created in "
                              f"{(DateTime.utcnow() - start_time).total_seconds()} secs")
                        print("-"*100)
                        break
            else:
                time.sleep(1)
                continue
            break
        else:
            assert False, (f"Can't find strat_alert with brief: {expected_alert_brief}, detail: {sample_detail}, "
                           f"severity: {log_lvl}")


@pytest.mark.log_book
def test_perf_of_alerts_based_on_transaction_counts(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    check_perf_of_alerts(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_, expected_strat_status_,
                         symbol_overview_obj_list, market_depth_basemodel_list, 200)


@pytest.mark.log_book
def test_perf_of_alerts_based_on_transaction_timeout(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    check_perf_of_alerts(leg1_leg2_symbol_list, pair_strat_, expected_strat_limits_, expected_strat_status_,
                         symbol_overview_obj_list, market_depth_basemodel_list, 50)


@pytest.mark.log_book1
def test_perf_of_db_updates(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

    active_strat_n_executor_list = start_strats_in_parallel(
        leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_strat, _ = active_strat_n_executor_list[0]

    log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_strat.id}_logs_{frmt_date}.log"
    total_updates = 10000
    for _ in range(10):
        for i in range(total_updates):
            log_str = (f"{get_log_date_time()} : DB : [sample_file.py : 575] : "
                       f"^^^StratViewBaseModel~~SNAPSHOT_TYPE~~patch_all_strat_view_client~~_id^^{active_strat.id}"
                       f"~~max_single_leg_notional^^{i+1}.0")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

        start_time = DateTime.utcnow()
        for i in range(10):
            strat_view: StratViewBaseModel = photo_book_web_client.get_strat_view_client(active_strat.id)
            if strat_view.max_single_leg_notional == total_updates:
                print("-"*100)
                print(f"Result: strat_view updated in "
                      f"{(DateTime.utcnow() - start_time).total_seconds()} secs")
                print("-"*100)
                break
            time.sleep(1)
        else:
            assert False, (f"Can't find strat_view update with max_single_leg_notional: {total_updates} "
                           f"after {(DateTime.utcnow() - start_time).total_seconds()} secs")
