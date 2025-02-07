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
    get_symbol_side_key, pair_plan_client_call_log_str, UpdateType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import *
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


def start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list) -> List:
    active_plan_n_executor_list: List[PairPlanBaseModel, StreetBookServiceHttpClient] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(leg1_leg2_symbol_list)) as executor:
        results = [executor.submit(create_n_activate_plan,
                                   leg1_symbol, leg2_symbol, copy.deepcopy(pair_plan_),
                                   copy.deepcopy(expected_plan_limits_), copy.deepcopy(expected_plan_status_),
                                   copy.deepcopy(symbol_overview_obj_list), copy.deepcopy(market_depth_basemodel_list),
                                   None, None, False)
                   for leg1_symbol, leg2_symbol in leg1_leg2_symbol_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())
            active_plan_n_executor_list.append(future.result())
    return active_plan_n_executor_list


def check_alert_exists_in_contact_alert(
        expected_alert_brief: str, log_file_path: str,
        expected_alert_detail_first: str,
        expected_alert_detail_latest: str | None = None) -> ContactAlertBaseModel:
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    start_time = DateTime.utcnow()
    for i in range(10):
        time.sleep(1)
        contact_alerts: List[ContactAlertBaseModel] = log_book_web_client.get_all_contact_alert_client()
        for contact_alert in contact_alerts:
            if contact_alert.alert_brief == expected_alert_brief:
                if (contact_alert.alert_meta.first_detail == expected_alert_detail_first and
                        contact_alert.alert_meta.latest_detail == expected_alert_detail_latest):
                    print("-" * 100)
                    print(f"Result: Found contact alert in {(DateTime.utcnow() - start_time).total_seconds()} secs")
                    print("-" * 100)
                    return contact_alert
                else:
                    if contact_alert.alert_meta.first_detail == expected_alert_detail_first:
                        assert False, ("contact_alert found with correct brief but mismatched "
                                       f"contact_alert.alert_meta.latest_detail, "
                                       f"expected: {expected_alert_detail_latest}, "
                                       f"found: {contact_alert.alert_meta.latest_detail}")
                    else:
                        assert False, ("contact_alert found with correct brief but mismatched "
                                       f"contact_alert.alert_meta.first_detail, "
                                       f"expected: {expected_alert_detail_first}, "
                                       f"found: {contact_alert.alert_meta.first_detail}")
    else:
        assert False, f"Cant find any contact_alert with {expected_alert_brief=}, {log_file_path=}"


def check_alert_doesnt_exist_in_contact_alert(expected_alert_brief: str, log_file_path: str):
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    for i in range(10):
        time.sleep(1)
        contact_alerts: List[ContactAlertBaseModel] = log_book_web_client.get_all_contact_alert_client()
        for contact_alert in contact_alerts:
            if contact_alert.alert_brief == expected_alert_brief:
                assert False, (f"Unexpected: contact_alert must not exist with plan_brief: "
                               f"{expected_alert_brief}, found {contact_alert=}, {log_file_path=}")


@pytest.mark.log_book
def test_filtered_plan_alert_by_plan_id_query_covers_all_plans(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list[:5], pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    # manually creating multiple plan_alerts with random id(s)
    plan_alert_dict: Dict = {}
    all_plan_alert_list: List = []
    counter = 0
    for i in range(1, 6):
        for sev in list(Severity):
            plan_alert = {"plan_id": i, "severity": sev, "alert_brief": f"Sample-{counter}"}

            if plan_alert_dict.get(plan_alert.get("plan_id")) is None:
                plan_alert_dict[plan_alert.get("plan_id")] = [plan_alert]
            else:
                plan_alert_dict[plan_alert.get("plan_id")].append(plan_alert)
            all_plan_alert_list.append(plan_alert)
            counter += 1

    log_book_web_client.handle_plan_alerts_from_tail_executor_query_client(all_plan_alert_list)
    time.sleep(2)

    # adding those alerts those got added with plan creation
    stored_plan_alerts = log_book_web_client.get_all_plan_alert_client()
    for stored_plan_alert in stored_plan_alerts:
        if not stored_plan_alert.alert_brief.startswith("Sample-"):
            plan_alert_dict[stored_plan_alert.plan_id].append({"plan_id": stored_plan_alert.plan_id,
                                                                  "severity": stored_plan_alert.severity,
                                                                  "alert_brief": stored_plan_alert.alert_brief})

    for plan_id, plan_alerts_dict_list in plan_alert_dict.items():
        filtered_plan_alerts = log_book_web_client.filtered_plan_alert_by_plan_id_query_client(plan_id)

        assert len(filtered_plan_alerts) == len(plan_alerts_dict_list), \
            f"Mismatched: {len(filtered_plan_alerts)=} != {len(plan_alerts_dict_list)=}"
        for plan_alert_ in plan_alerts_dict_list:
            for fetched_plan_alert in filtered_plan_alerts:
                if fetched_plan_alert.alert_brief == plan_alert_.get("alert_brief"):
                    break
            else:
                assert False, (f"Unexpected: Can't find plan_alert with {plan_alert_.get("alert_brief")=} in "
                               f"filtered_plan_alerts: {filtered_plan_alerts}")


def check_alert_exists_in_plan_alert(active_plan: PairPlanBaseModel, expected_alert_brief: str,
                                      log_file_path: str, expected_alert_detail_first: str,
                                      expected_alert_detail_latest: str | None = None) -> PlanAlertBaseModel:
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    start_time = DateTime.utcnow()
    for i in range(10):
        time.sleep(1)
        plan_alerts: List[PlanAlertBaseModel] = (
            log_book_web_client.filtered_plan_alert_by_plan_id_query_client(plan_id=active_plan.id))
        for plan_alert in plan_alerts:
            if plan_alert.alert_brief == expected_alert_brief:
                if (plan_alert.alert_meta.first_detail == expected_alert_detail_first and
                        plan_alert.alert_meta.latest_detail == expected_alert_detail_latest):
                    print("-"*100)
                    print(f"Result: Found plan alert in {(DateTime.utcnow()-start_time).total_seconds()} secs")
                    print("-"*100)
                    return plan_alert
                else:
                    if plan_alert.alert_meta.first_detail == expected_alert_detail_first:
                        assert False, ("plan_alert found with correct brief but mismatched "
                                       f"plan_alert.alert_meta.first_detail, "
                                       f"expected {expected_alert_detail_first}, "
                                       f"found: {plan_alert.alert_meta.first_detail}")
                    else:
                        assert False, ("plan_alert found with correct brief but mismatched "
                                       f"plan_alert.alert_meta.latest_detail, "
                                       f"expected {expected_alert_detail_latest}, "
                                       f"found: {plan_alert.alert_meta.latest_detail}")
    else:
        assert False, f"Cant find any plan_alert with {expected_alert_brief=}, {log_file_path=}"


def check_alert_doesnt_exist_in_plan_alert(active_plan: PairPlanBaseModel | None, expected_alert_brief: str,
                                            log_file_path: str):
    expected_alert_brief = get_expected_brief(expected_alert_brief)
    for i in range(10):
        time.sleep(1)
        if active_plan is not None:
            plan_alerts: List[PlanAlertBaseModel] = (
                log_book_web_client.filtered_plan_alert_by_plan_id_query_client(plan_id=active_plan.id))
        else:
            plan_alerts: List[PlanAlertBaseModel] = (
                log_book_web_client.get_all_plan_alert_client())
        for plan_alert in plan_alerts:
            if plan_alert.alert_brief == expected_alert_brief:
                assert False, (f"Unexpected: plan_alert must not exist with alert_brief: {expected_alert_brief}, "
                               f"found plan_alert: {plan_alert}, {log_file_path=}")


@pytest.mark.log_book
def test_log_to_start_alert_through_plan_id(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs are created as plan_alerts for tail executor registered based on plan_id
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)

    # Negative test
    # creating random log file with id of which no plan running
    non_existing_plan_id = 100
    log_file_name = f"street_book_{non_existing_plan_id}_logs_{frmt_date}.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name
    try:
        # creating log file
        with open(log_file_path, "w"):
            pass

        plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
        time_wait = plan_alert_config.get("transaction_timeout_secs")

        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)

        sample_brief = f"Sample Log not to be created as plan_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_doesnt_exist_in_plan_alert(None, sample_brief, log_file_path)
    except Exception as e:
        raise e
    finally:
        handle_tail_executor_terminate_n_clear_cache_for_log_file(str(log_file_path))


@pytest.mark.log_book
def test_log_to_start_alert_through_symbol_n_side_key(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs are created as plan_alerts having symbol_n_side key, covers leg_1, leg_2 and both legs
    symbol_n_side key verification
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_plan: PairPlanBaseModel
    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        leg_1_symbol_n_side_key = get_symbol_side_key([(active_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                        active_plan.pair_plan_params.plan_leg1.side)])
        leg_2_symbol_n_side_key = get_symbol_side_key([(active_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                        active_plan.pair_plan_params.plan_leg2.side)])
        both_legs_symbol_n_side_key = get_symbol_side_key([(active_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                            active_plan.pair_plan_params.plan_leg1.side),
                                                           (active_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                            active_plan.pair_plan_params.plan_leg2.side)])

        for log_key in [leg_1_symbol_n_side_key, leg_2_symbol_n_side_key, both_legs_symbol_n_side_key]:
            sample_brief = f"Sample Log to be created as plan_alert key: {log_key}"
            sample_detail = "sample detail string"

            # Positive test
            log_str = get_log_line_str("ERROR", sample_file_name,
                                       line_no, f"{sample_brief};;;{sample_detail}")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

            check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)

        # Negative test
        non_existing_plan_log_key = get_symbol_side_key([("Type1_Sec_100", Side.BUY)])

        sample_brief = f"Sample Log not to be created as plan_alert, key: {non_existing_plan_log_key}"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_doesnt_exist_in_plan_alert(active_plan, sample_brief, log_file_path)


@pytest.mark.log_book
def test_log_to_contact_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs not having symbol-side key or plan_id are created as contact_alerts
    """
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as contact_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)

    # Negative test
    sample_brief = f"Sample Log not to be created as contact_alert"
    sample_detail = "sample detail string"
    log_str = get_log_line_str("SAMPLE", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_doesnt_exist_in_contact_alert(sample_brief, log_file_path)


@pytest.mark.log_book
def test_log_to_update_db(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs having db pattern updates db
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"

        # not checking severity and plan_alert_count update since it gets updated very often from code and
        # test fails - anyway test checks update functionality so if it works for rest fields it is still good
        db_json_list = [
            {"average_premium": random.randint(1, 100)},
            {"market_premium": random.randint(1, 100)},
            {"balance_notional": random.randint(1, 100)},
            {"max_single_leg_notional": random.randint(100, 1000)}
            ]

        for db_json in db_json_list:
            db_pattern_str = pair_plan_client_call_log_str(
                PlanViewBaseModel, photo_book_web_client.patch_all_plan_view_client,
                UpdateType.SNAPSHOT_TYPE, _id=active_plan.id, **db_json)
            log_str = get_log_line_str("DB", sample_file_name, line_no, db_pattern_str)

            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

            plan_view = photo_book_web_client.get_plan_view_client(active_plan.id)
            stored_val = getattr(plan_view, list(db_json.keys())[0])
            expected_val = list(db_json.values())[0]
            assert stored_val == expected_val, \
                (f"Mismatched {list(db_json.keys())[0]} field of plan view, expected: {expected_val}, "
                 f"received: {stored_val}, active_plan: {active_plan}")


# @@@ temp test - not working
@pytest.mark.log_book1
def test_to_verify_data_is_not_lost_update_db_client_fails(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify if any db update got exception then next successful call consists filing update data - basically
    checking no data is lost even if client call fails
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"

        # not checking severity and plan_alert_count update since it gets updated very often from code and
        # test fails - anyway test checks update functionality so if it works for rest fields it is still good
        db_json_list = [
            {"average_premium": "Wrong_data",
             "market_premium": random.randint(1, 100),
             "balance_notional": random.randint(1, 100),
             "max_single_leg_notional": random.randint(100, 1000)},
            {"average_premium": random.randint(1, 100)}
            ]

        for db_json in db_json_list:
            db_pattern_str = pair_plan_client_call_log_str(
                PlanViewBaseModel, photo_book_web_client.patch_all_plan_view_client,
                UpdateType.SNAPSHOT_TYPE, _id=active_plan.id, **db_json)
            log_str = get_log_line_str("DB", sample_file_name, line_no, db_pattern_str)

            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

        expected_plan_view = PlanViewBaseModel.from_kwargs(
            _id=active_plan.id,
            market_premium=db_json_list[0].get("market_premium"),
            balance_notional=db_json_list[0].get("balance_notional"),
            max_single_leg_notional=db_json_list[0].get("max_single_leg_notional"),
            average_premium=db_json_list[1].get("average_premium")
        )

        plan_view = photo_book_web_client.get_plan_view_client(active_plan.id)
        # updating non checking fields
        expected_plan_view.plan_alert_count = plan_view.plan_alert_count
        expected_plan_view.plan_alert_aggregated_severity = plan_view.plan_alert_aggregated_severity
        expected_plan_view.total_fill_buy_notional = plan_view.total_fill_buy_notional
        expected_plan_view.total_fill_sell_notional = plan_view.total_fill_sell_notional
        expected_plan_view.unload_plan = plan_view.unload_plan
        expected_plan_view.recycle_plan = plan_view.recycle_plan
        assert plan_view == expected_plan_view, \
            (f"Mismatched plan view, expected: {expected_plan_view}, "
             f"received: {plan_view}, active_plan: {active_plan}")


@pytest.mark.log_book
def test_alert_with_same_severity_n_brief_is_always_updated(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify logs are created as plan_alerts for tail executor registered based on plan_id
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
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
            plan_alerts: List[PlanAlertBaseModel] = (
                log_book_web_client.filtered_plan_alert_by_plan_id_query_client(plan_id=active_plan.id))
            expected_alert_brief = get_expected_brief(sample_brief)
            for plan_alert in plan_alerts:
                if plan_alert.alert_brief == expected_alert_brief:
                    alert_count += 1

                    assert plan_alert.alert_meta.first_detail == first_found_detail, \
                        (f"Mismatched plan_alert.alert_meta.first_detail: expected: {first_found_detail}, "
                         f"found: {plan_alert.alert_meta.first_detail}")
                    assert plan_alert.alert_meta.latest_detail == latest_found_detail, \
                        (f"Mismatched plan_alert.alert_meta.latest_detail: expected: {latest_found_detail}, "
                         f"found: {plan_alert.alert_meta.latest_detail}")
                    assert plan_alert.alert_count == log_count, \
                        (f"Mismatched alert_count: expected: {total_log_counts}, "
                         f"found {plan_alert.alert_count=} ")
                    break
            else:
                assert False, \
                    (f"Can't Find any matching plan_alert for {active_plan.id=}, "
                     f"{expected_alert_brief=}, severity: {log_lvl}")

            assert alert_count == 1, f"Mismatched: alert count for alert_brief must be 1, found {alert_count}"


def verify_alert_in_plan_alert_cache(plan_alert: PlanAlertBaseModel):
    plan_alert_id_to_obj_cache: List[PlanAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_plan_alert_id_in_plan_alert_id_to_obj_cache_dict_query_client(plan_alert.id))
    assert len(plan_alert_id_to_obj_cache) == 1, \
        ("Received unexpected plan_alert_id_to_obj_cache - "
         "verify_plan_alert_id_in_plan_alert_id_to_obj_cache_dict_query_client failed, "
         f"{plan_alert_id_to_obj_cache=}")
    assert plan_alert_id_to_obj_cache[0].is_id_present, \
        f"{plan_alert.id=} must exist in plan_alert_id_to_obj_cache_dict in log analyzer"

    plan_alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                          plan_alert.alert_meta.component_file_path,
                                          plan_alert.alert_meta.source_file_name,
                                          plan_alert.alert_meta.line_num)
    container_obj_list: List[PlanAlertCacheDictByPlanIdDictBaseModel] = (
        log_book_web_client.verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_client(
            plan_alert.plan_id, plan_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - "
         "verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_client failed, "
         f"{container_obj_list=}")
    assert container_obj_list[0].is_key_present, \
        (f"{plan_alert.id=} must exist in plan_alert_cache_dict_by_plan_id_dict of "
         f"{plan_alert.plan_id} in log analyzer")


def verify_alert_not_in_plan_alert_cache(plan_alert: PlanAlertBaseModel):
    plan_alert_id_to_obj_cache: List[PlanAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_plan_alert_id_in_plan_alert_id_to_obj_cache_dict_query_client(plan_alert.id))
    assert len(plan_alert_id_to_obj_cache) == 1, \
        ("Received unexpected plan_alert_id_to_obj_cache - "
         "verify_plan_alert_id_in_plan_alert_id_to_obj_cache_dict_query_client failed, "
         f"{plan_alert_id_to_obj_cache=}")
    assert not plan_alert_id_to_obj_cache[0].is_id_present, \
        f"{plan_alert.id=} must not exist in plan_alert_id_to_obj_cache_dict in log analyzer after deletion"

    plan_alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                          plan_alert.alert_meta.component_file_path,
                                          plan_alert.alert_meta.source_file_name,
                                          plan_alert.alert_meta.line_num)
    container_obj_list: List[PlanAlertCacheDictByPlanIdDictBaseModel] = (
        log_book_web_client.verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_client(
            plan_alert.plan_id, plan_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - "
         "verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_client failed, "
         f"{container_obj_list=}")
    assert not container_obj_list[0].is_key_present, \
        (f"{plan_alert.id=} must not exist in plan_alert_cache_dict_by_plan_id_dict of {plan_alert.plan_id} "
         f"in log analyzer after deletion")


def verify_alert_in_contact_alert_cache(contact_alert: ContactAlertBaseModel):
    contact_alert_id_to_obj_cache: List[ContactAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_client(contact_alert.id))
    assert len(contact_alert_id_to_obj_cache) == 1, \
        ("Received unexpected contact_alert_id_to_obj_cache - "
         "verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_client failed, "
         f"{contact_alert_id_to_obj_cache=}")
    assert contact_alert_id_to_obj_cache[0].is_id_present, \
        f"{contact_alert.id=} must exist in contact_alert_id_to_obj_cache_dict in log analyzer"

    plan_alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                          contact_alert.alert_meta.component_file_path,
                                          contact_alert.alert_meta.source_file_name,
                                          contact_alert.alert_meta.line_num)
    container_obj_list: List[ContactAlertCacheDictBaseModel] = (
        log_book_web_client.verify_contact_alerts_cache_dict_query_client(plan_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - verify_contact_alerts_cache_dict_query_client failed, "
         f"{container_obj_list=}")
    assert container_obj_list[0].is_key_present, \
        f"{contact_alert.id=} must exist in contact_alerts_cache_dict in log analyzer"


def verify_alert_not_in_contact_alert_cache(contact_alert: ContactAlertBaseModel):
    contact_alert_id_to_obj_cache: List[ContactAlertIdToObjCacheBaseModel] = (
        log_book_web_client.verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_client(contact_alert.id))
    assert len(contact_alert_id_to_obj_cache) == 1, \
        ("Received unexpected contact_alert_id_to_obj_cache - "
         "verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_client failed, "
         f"{contact_alert_id_to_obj_cache=}")
    assert not contact_alert_id_to_obj_cache[0].is_id_present, \
        f"{contact_alert.id=} must not exist in contact_alert_id_to_obj_cache_dict in log analyzer after deletion"

    plan_alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                          contact_alert.alert_meta.component_file_path,
                                          contact_alert.alert_meta.source_file_name,
                                          contact_alert.alert_meta.line_num)
    container_obj_list: List[ContactAlertCacheDictBaseModel] = (
        log_book_web_client.verify_contact_alerts_cache_dict_query_client(plan_alert_key))
    assert len(container_obj_list) == 1, \
        ("Received unexpected container_obj_list - verify_contact_alerts_cache_dict_query_client failed, "
         f"{container_obj_list=}")
    assert not container_obj_list[0].is_key_present, \
        f"{contact_alert.id=} must not exist in contact_alerts_cache_dict in log analyzer after deletion"


@pytest.mark.log_book
def test_to_verify_plan_alert_cache_is_cleared_in_delete_plan_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    created_plan_alert_list: List[PlanAlertBaseModel] = []
    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

        # first time creating alert
        sample_detail = f"sample detail string"
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        created_plan_alert_list.append(plan_alert)

        # verifying that plan_alert was added in cache
        verify_alert_in_plan_alert_cache(plan_alert)

    # deleting 1 plan_alert using delete_plan_alert_client out of 3 plan_alerts to verifying and then calling
    # delete_all_plan_alert_client to verify remaining 2 also are removed from cache
    plan_alert = created_plan_alert_list.pop(0)
    log_book_web_client.delete_plan_alert_client(plan_alert.id)
    verify_alert_not_in_plan_alert_cache(plan_alert)

    log_book_web_client.delete_all_plan_alert_client()
    for plan_alert in created_plan_alert_list:
        verify_alert_not_in_plan_alert_cache(plan_alert)


@pytest.mark.log_book
def test_to_verify_remove_plan_alerts_for_plan_id_query(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    created_plan_alert_list: List[PlanAlertBaseModel] = []
    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

        # first time creating alert
        sample_detail = f"sample detail string"
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        created_plan_alert_list.append(plan_alert)

        # verifying that plan_alert was added in cache
        verify_alert_in_plan_alert_cache(plan_alert)

    for plan_alert in created_plan_alert_list:
        log_book_web_client.remove_plan_alerts_for_plan_id_query_client(plan_alert.plan_id)

        # verifying if plan_id exists in plan_alert_cache_dict_by_plan_id_dict
        container_obj_list = (
            log_book_web_client.verify_plan_id_in_plan_alert_cache_dict_by_plan_id_dict_query_client(
                plan_alert.plan_id))
        assert len(container_obj_list) == 1, \
            ("Received unexpected container_obj_list - "
             "verify_plan_id_in_plan_alert_cache_dict_by_plan_id_dict_query_client failed, "
             f"{container_obj_list=}")
        assert not container_obj_list[0].is_id_present, \
            f"{plan_alert.plan_id=} must not exist in plan_alert_cache_dict_by_plan_id_dict in log analyzer"

        # verifying other cache also
        verify_alert_not_in_plan_alert_cache(plan_alert)


@pytest.mark.log_book
def test_to_verify_contact_alert_cache_is_cleared_in_delete_contact_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as contact_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)
    # verifying that alert was added to cache
    verify_alert_in_contact_alert_cache(contact_alert)

    log_book_web_client.delete_contact_alert_client(contact_alert.id)
    # verifying that alert got cleared from cache
    verify_alert_not_in_contact_alert_cache(contact_alert)


# @ failing: internal cache in tail executor is not removed when deleted - when obj is again created
# it is expected to be created clean but has last obj data from tail executor
@pytest.mark.log_book
def test_start_alert_with_same_severity_n_brief_is_created_again_if_is_deleted(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify plan_alert once created if alert is deleted and same log line is again added,
    then plan_alert is created inplace of updating - verifies deletion and caching is working for plan_alert
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

        # first time creating alert
        sample_detail = f"sample detail string"
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)

        # deleting start_alert
        log_book_web_client.delete_plan_alert_client(plan_alert.id)
        check_alert_doesnt_exist_in_plan_alert(active_plan, sample_brief, log_file_path)

        # again adding same log - this time it must be again created
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)


# @ failing: internal cache in tail executor is not removed when deleted - when obj is again created
# it is expected to be created clean but has last obj data from tail executor
@pytest.mark.log_book
def test_contact_alert_with_same_severity_n_brief_is_created_again_if_is_deleted(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify contact_alert once created if alert is deleted and same log line is again added,
    then contact_alert is created inplace of updating - verifies deletion and caching is working for contact_alert
    """
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)
    sample_brief = "Sample Log to be created as contact_alert"
    log_lvl = random.choice(["ERROR", "WARNING", "CRITICAL"])

    # first time creating alert
    sample_detail = f"sample detail string"
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)

    # deleting start_alert
    log_book_web_client.delete_contact_alert_client(contact_alert.id)
    check_alert_doesnt_exist_in_contact_alert(sample_brief, log_file_path)

    # again adding same log - this time it must be again created
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)


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
        sample_brief = "Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name, line_no, f"{sample_brief};;; {sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)
    except Exception as e:
        raise e
    finally:
        handle_tail_executor_terminate_n_clear_cache_for_log_file(str(log_file_path))


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

    sample_brief = f"Sample Log to be created as contact_alert"
    sample_detail = "sample detail string"

    # Positive test
    for log_lvl in ["WARNING", "ERROR", "CRITICAL"]:
        log_str = get_log_line_str(log_lvl, sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)

    # Negative test
    log_lvl = "SAMPLE"
    sample_brief = f"Sample Log not to be created as contact_alert"
    log_str = get_log_line_str(log_lvl, sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_doesnt_exist_in_contact_alert(sample_brief, log_file_path)


@pytest.mark.log_book
def test_plan_alert_unable_to_patch_are_created_as_contact_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    # since only single plan is used in this test
    active_plan, executor_http_client = active_plan_n_executor_list[0]

    log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)
    sample_brief = "Sample Log to be created as plan_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)


@pytest.mark.log_book
def test_restart_tail_executor(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify restart of tail executor
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)

        # restarting from latest line in log
        restart_date_time = get_log_date_time()
        log_book_web_client.log_book_restart_tail_query_client(str(log_file_path), restart_date_time)

        time.sleep(2)

        # checking if tail_executor is restarted
        sample_brief = "Sample Log to be created as plan_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        assert plan_alert.alert_count == 1, \
            f"Mismatched: expected plan_alert.alert_count: 1, found {plan_alert.alert_count=}"

        # restarting from before last-time restarted - also verifying if log is again executed
        log_book_web_client.log_book_restart_tail_query_client(str(log_file_path), restart_date_time)
        time.sleep(10)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path,
                                                        expected_alert_detail_first=sample_detail,
                                                        expected_alert_detail_latest=sample_detail)
        assert plan_alert.alert_count == 2, \
            f"Mismatched: expected plan_alert.alert_count: 2, found {plan_alert.alert_count=}"


@pytest.mark.log_book
def test_tail_executor_restarts_if_tail_error_occurs(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify if tail executor has error tail executor is restarted from last line it processed
    """
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)
    sample_brief = "Sample Log to be created as contact_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)
    assert contact_alert.alert_count == 1, \
        f"Mismatched: expected contact_alert.alert_count: 1, found {contact_alert.alert_count=}"

    # putting error log in file
    error_log_str = "tail: giving up on this name"
    add_log_to_file(log_file_path, error_log_str)
    time.sleep(1)

    # removing this error log before restart to tail executor to avoid cyclic restarts
    os.system(f"gsed -i '/{error_log_str}/d' {log_file_path}")

    time.sleep(10)

    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)
    # expecting alert is not updated since restart must happen from latest line and should't reread existing log
    assert contact_alert.alert_count == 1, \
        f"Mismatched: expected contact_alert.alert_count: 2, found {contact_alert.alert_count=}"

    # updating alert by creating one more log with same file_name, line_num and severity
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)
    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail, sample_detail)
    assert contact_alert.alert_count == 2, \
        f"Mismatched: expected contact_alert.alert_count: 2, found {contact_alert.alert_count=}"

@pytest.mark.log_book
def test_kill_tail_executor_n_clear_cache_(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify kill and cache clear queries work for tail executor - starts tail_executor, kills it and
    clears cache to check if tail executor is restarted for same file
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_name = f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        log_file_path = STRAT_EXECUTOR / "log" / log_file_name
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)

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
        sample_brief = "Sample Log to be created as plan_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        assert plan_alert.alert_count == 1, \
            f"Mismatched: expected plan_alert.alert_count: 1, found {plan_alert.alert_count=}"


@pytest.mark.log_book
def test_delete_log_file_n_again_create_to_verify_tail(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Test to verify if tail is again started to file which is recreated again after deleting
    """
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_name = f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        log_file_path = STRAT_EXECUTOR / "log" / log_file_name
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)

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
        sample_brief = "Sample Log to be created as plan_alert again"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        assert plan_alert.alert_count == 1, \
            f"Mismatched: expected plan_alert.alert_count: 1, found {plan_alert.alert_count=}"


@pytest.mark.log_book
def test_plan_alert_with_no_plan_with_symbol_side_is_sent_to_contact_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    plan_alert_config: Dict = la_config_yaml_dict.get("plan_alert_config")
    time_wait = plan_alert_config.get("transaction_timeout_secs")

    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    non_existing_plan_log_key = get_symbol_side_key([("Type1_Sec_100", Side.BUY)])

    sample_brief = f"Sample Log not to be created as plan_alert, key: {non_existing_plan_log_key}"
    sample_detail = "sample detail string"
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    time.sleep(time_wait * 2 + 1)
    # checking if any plan_alert contains this alert content
    plan_alert_list = log_book_web_client.get_all_plan_alert_client()

    for plan_alert in plan_alert_list:
        if plan_alert.alert_brief == sample_brief:
            assert False, \
                f"No start alert must exists with having alert_brief: {sample_brief}, found alert: {plan_alert}"

    contact_alert_list = log_book_web_client.get_all_contact_alert_client()
    for contact_alert in contact_alert_list:
        if contact_alert.alert_brief == sample_brief:
            break
    else:
        assert False, \
            ("Failed plan_alert must be created as contact_alert of same severity and brief, but couldn't find "
             "any contact_alert")


@pytest.mark.log_book
def test_plan_alert_with_no_plan_with_plan_id_is_sent_to_contact_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    """
    Created sample log file manually to start tail_executor and verify since no plan log key
    exists, alert is sent to contact alert
    """
    log_file_name = f"sample_test.log"
    executor_log_dir_path = STRAT_EXECUTOR / "log"
    log_file_path = executor_log_dir_path / log_file_name

    # creating log dir if not exists
    if not os.path.exists(executor_log_dir_path):
        os.mkdir(executor_log_dir_path)

    # creating log file
    with open(log_file_path, "w"):
        pass

    try:
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)

        sample_brief = f"Sample Log not to be created as plan_alert"
        sample_detail = "sample detail string"
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        for _ in range(10):
            time.sleep(1)
            # checking if any plan_alert contains this alert content
            plan_alert_list = log_book_web_client.get_all_plan_alert_client()

            for plan_alert in plan_alert_list:
                if plan_alert.alert_brief == sample_brief:
                    assert False, \
                        f"No start alert must exists with having alert_brief: {sample_brief}, found alert: {plan_alert}"

            contact_alert_list = log_book_web_client.get_all_contact_alert_client()
            for contact_alert in contact_alert_list:
                if contact_alert.alert_brief == sample_brief:
                    break
            else:
                continue
            break
        else:
            assert False, \
                ("Failed plan_alert must be created as contact_alert of same severity and brief, but couldn't find "
                 "any contact_alert")
    except Exception as e:
        raise e
    finally:
        handle_tail_executor_terminate_n_clear_cache_for_log_file(str(log_file_path))


@pytest.mark.log_book
def test_plan_alert_put_all_failed_alerts_goes_to_contact_alert(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    created_alerts_list = []
    for active_plan, executor_http_client in active_plan_n_executor_list:
        log_file_name = f"street_book_{active_plan.id}_logs_{frmt_date}.log"
        log_file_path = STRAT_EXECUTOR / "log" / log_file_name
        sample_file_name = "sample_file.py"
        line_no = random.randint(1, 100)
        sample_brief = "Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"
        print(f"Checking file: {log_file_path!r}")

        # Positive test
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)

        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        created_alerts_list.append(plan_alert)

        # manually deleting plan_alert - deleting through client will trigger cache update which will avoid
        # recreation of issue and will trigger create of alert next time instead of update
        mongo_uri = get_mongo_server_uri()
        db_name = "log_book"
        collection_name = "PlanAlert"
        delete_filter = {"_id": plan_alert.id}
        res = delete_mongo_document(mongo_uri, db_name, collection_name, delete_filter)
        assert res, f"delete_mongo_document failed for {plan_alert.id=}"

        try:
            updated_sample_detail = "updated sample detail string"
            log_str = get_log_line_str("ERROR", sample_file_name,
                                       line_no, f"{sample_brief};;;{updated_sample_detail}")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

            # verifying plan_alert not exists
            check_alert_doesnt_exist_in_plan_alert(active_plan, sample_brief, log_file_path)

            # verifying contact alert contains failed plan alert
            check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail, updated_sample_detail)
        except Exception as e:
            raise e
        finally:
            if res:
                # creating document back to delete cache for that entry
                create_mongo_document(mongo_uri, db_name, collection_name, plan_alert.to_dict())


@pytest.mark.log_book
def test_contact_alert_put_all_failed_alerts_goes_to_contact_fail_alert_log(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    sample_brief = f"Sample Log to be created as contact_alert"
    sample_detail = "sample detail string"

    # Positive test
    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)

    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)

    # manually deleting contact_alert - deleting through client will trigger cache update which will avoid
    # recreation of issue and will trigger create of alert next time instead of update
    mongo_uri = get_mongo_server_uri()
    db_name = "log_book"
    delete_filter = {"_id": contact_alert.id}
    collection_name = "ContactAlert"
    res = delete_mongo_document(mongo_uri, db_name, collection_name, delete_filter)
    assert res, f"delete_mongo_document failed for {contact_alert.id=}"

    sample_detail = "updated sample detail string"

    try:
        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)
        check_alert_doesnt_exist_in_contact_alert(sample_brief, log_file_path)

        # checking alert is present in contact_alert_fail_logs
        contact_alert_fail_logger_name = f"contact_alert_fail_logs_{frmt_date}.log"
        contact_alert_fail_logger_path = LOG_ANALYZER_DIR / "log" / contact_alert_fail_logger_name
        with open(contact_alert_fail_logger_path, "r") as fl:
            lines = fl.readlines()

            expected_plan_brief = get_expected_brief(sample_brief)
            for line in lines:
                if expected_plan_brief in line:
                    break
            else:
                assert False, ("Can't find info for contact_fail in contact_fail_log file, "
                               f"expected brief: {expected_plan_brief}, expected detail: {sample_detail}, "
                               f"expected severity: ERROR")
    except Exception as e:
        raise e
    finally:
        if res:
            # creating document back to delete cache for that entry
            create_mongo_document(mongo_uri, db_name, collection_name, contact_alert.to_dict())


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
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
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

        handle_tail_executor_terminate_n_clear_cache_for_log_file(str(log_file_path))

        if not is_perf_bench_server_up_already:
            res = kill_perf_bench_server()
            if not res:
                print(f"Unexpected: Can't kill perf bench server - "
                      f"Can't find any pid from port {PERF_BENCH_BEANIE_PORT}")
        # else not required: if server was already running then keep it running


def check_log_info_fields_in_alert(alert_obj: PlanAlertBaseModel | ContactAlertBaseModel,
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
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:3]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_plan: PairPlanBaseModel
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / f"phone_book_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    # PlanAlert test
    for active_plan, executor_http_client in active_plan_n_executor_list:
        line_no = random.randint(1, 100)
        log_key = get_symbol_side_key([(active_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                        active_plan.pair_plan_params.plan_leg1.side)])

        sample_brief = f"Sample Log to be created as plan_alert key: {log_key}"
        sample_detail = "sample detail string for plan alert"

        log_str = get_log_line_str("ERROR", sample_file_name,
                                   line_no, f"{sample_brief};;;{sample_detail}")
        add_log_to_file(log_file_path, log_str)
        time.sleep(1)
        plan_alert = check_alert_exists_in_plan_alert(active_plan, sample_brief, log_file_path, sample_detail)
        check_log_info_fields_in_alert(plan_alert, str(log_file_path), sample_file_name, line_no)

    # ContactAlert test
    sample_brief = f"Sample Log to be created as contact_alert"
    sample_detail = "sample detail string for contact alert"
    line_no = random.randint(1, 100)

    log_str = get_log_line_str("ERROR", sample_file_name,
                               line_no, f"{sample_brief};;;{sample_detail}")
    add_log_to_file(log_file_path, log_str)
    time.sleep(1)
    contact_alert = check_alert_exists_in_contact_alert(sample_brief, log_file_path, sample_detail)
    check_log_info_fields_in_alert(contact_alert, str(log_file_path), sample_file_name, line_no)


def test_check_background_logs_alert_handling(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_name = f"phone_book_background_logs.log"
    log_file_path = PAIR_STRAT_ENGINE_DIR / "log" / log_file_name

    if not os.path.exists(log_file_path):
        with open(log_file_path, "w"):
            pass
    time.sleep(5)

    try:
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
            contact_alerts = log_book_web_client.get_all_contact_alert_client()
            for contact_alert in contact_alerts:
                if contact_alert.alert_brief == log_str[-1]:
                    break
            else:
                time.sleep(1)
            break
        else:
            assert False, "Can't find alert containing error msg in brief"
    except Exception as e:
        raise e
    finally:
        handle_tail_executor_terminate_n_clear_cache_for_log_file(str(log_file_path))


def check_perf_of_alerts(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, alert_counts: int):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_plan, _ = active_plan_n_executor_list[0]

    log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
    sample_file_name = "sample_file.py"
    line_no = random.randint(1, 100)

    log_str = ""
    sample_detail = ""
    sample_brief = f"Sample Log to be created as plan_alert"
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
            plan_alerts: List[PlanAlertBaseModel] = log_book_web_client.get_all_plan_alert_client()
            for plan_alert in plan_alerts:
                if plan_alert.alert_brief == expected_alert_brief:
                    if plan_alert.alert_meta.latest_detail == sample_detail:
                        print("-"*100)
                        print(f"Result: plan_alert created in "
                              f"{(DateTime.utcnow() - start_time).total_seconds()} secs")
                        print("-"*100)
                        break
            else:
                time.sleep(1)
                continue
            break
        else:
            assert False, (f"Can't find plan_alert with brief: {expected_alert_brief}, detail: {sample_detail}, "
                           f"severity: {log_lvl}")


@pytest.mark.log_book
def test_perf_of_alerts_based_on_transaction_counts(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    check_perf_of_alerts(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_, expected_plan_status_,
                         symbol_overview_obj_list, market_depth_basemodel_list, 200)


@pytest.mark.log_book
def test_perf_of_alerts_based_on_transaction_timeout(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    check_perf_of_alerts(leg1_leg2_symbol_list, pair_plan_, expected_plan_limits_, expected_plan_status_,
                         symbol_overview_obj_list, market_depth_basemodel_list, 50)


@pytest.mark.log_book1
def test_perf_of_db_updates(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    leg1_leg2_symbol_list = leg1_leg2_symbol_list[:1]

    active_plan_n_executor_list = start_plans_in_parallel(
        leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list)

    active_plan, _ = active_plan_n_executor_list[0]

    log_file_path = STRAT_EXECUTOR / "log" / f"street_book_{active_plan.id}_logs_{frmt_date}.log"
    total_updates = 10000
    for _ in range(10):
        for i in range(total_updates):
            log_str = (f"{get_log_date_time()} : DB : [sample_file.py : 575] : "
                       f"^^^PlanViewBaseModel~~SNAPSHOT_TYPE~~patch_all_plan_view_client~~_id^^{active_plan.id}"
                       f"~~max_single_leg_notional^^{i+1}.0")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

        start_time = DateTime.utcnow()
        for i in range(10):
            plan_view: PlanViewBaseModel = photo_book_web_client.get_plan_view_client(active_plan.id)
            if plan_view.max_single_leg_notional == total_updates:
                print("-"*100)
                print(f"Result: plan_view updated in "
                      f"{(DateTime.utcnow() - start_time).total_seconds()} secs")
                print("-"*100)
                break
            time.sleep(1)
        else:
            assert False, (f"Can't find plan_view update with max_single_leg_notional: {total_updates} "
                           f"after {(DateTime.utcnow() - start_time).total_seconds()} secs")


@pytest.mark.log_book
def test_tail_executor_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list):
    log_file_name = f"sample_100_test.log"
    log_file_path = STRAT_EXECUTOR / "log" / log_file_name
    tail_process_grep_pattern = "tail_executor~test_street_book_with_pattern"

    if not os.path.exists(STRAT_EXECUTOR / "log"):
        os.mkdir(STRAT_EXECUTOR / "log")
    with open(log_file_path, "w"):
        pass

    try:
        time.sleep(2)
        assert os.path.exists(log_file_path), \
            f"Can't find sample log file: {log_file_path!r}"

        time.sleep(2)
        res = get_process_info_for_tail_executor(tail_process_grep_pattern, log_file_name)
        if res is None:
            assert False, \
                f"Can't find tail executor process for sample log file: {log_file_path!r}"

        # checking if tail executor is functional for this log file
        sample_file_name = "sample_file.py"
        sample_brief = f"Sample Log to be created as plan_alert"
        sample_detail = "sample detail string"
        line_no = random.randint(1, 100)
        for i in range(5):
            log_str = get_log_line_str("ERROR", sample_file_name, line_no, f"{sample_brief}-{i};;; {sample_detail}")
            add_log_to_file(log_file_path, log_str)
            time.sleep(1)

        # killing cpp app
        result = subprocess.run(
            [f'pgrep', '-f', tail_process_grep_pattern],
            text=True,  # Capture text output
            stdout=subprocess.PIPE,  # Capture standard output
            stderr=subprocess.PIPE,  # Capture standard error
        )
        if result.stdout:
            process_id = parse_to_int(result.stdout.strip())
            os.kill(parse_to_int(process_id), signal.SIGKILL)
            print(f"Killed tail executor process - {process_id=}")
        else:
            assert False, \
                (f"Can't find tail executor process for {tail_process_grep_pattern=}, "
                 f"process check output: {result.stdout}")

        for i in range(5, 10):
            log_str = get_log_line_str("ERROR", sample_file_name, line_no, f"{sample_brief}-{i};;; {sample_detail}")
            add_log_to_file(log_file_path, log_str)

        time.sleep(30)      # log analyzer refresh wait

        res = get_process_info_for_tail_executor(tail_process_grep_pattern, log_file_name)
        if res is None:
            assert False, \
                f"Can't find tail executor process for sample log file: {log_file_path!r} post process kill"

        contact_alerts = log_book_web_client.get_all_contact_alert_client()
        expected_alert_counts = 10
        for contact_alert in contact_alerts:
            if sample_brief in contact_alert.alert_brief:
                assert contact_alert.alert_count == expected_alert_counts, \
                    f"Mismatched alert count: {contact_alert.alert_count=}, {expected_alert_counts=}, {contact_alert}"
                break
    except Exception as e:
        raise e
    finally:
        handle_tail_executor_terminate_n_clear_cache_for_log_file(str(log_file_path))
