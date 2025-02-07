import os.path
import subprocess
import concurrent.futures
import time

import pytest
import signal

from FluxPythonUtils.scripts.utility_functions import get_pid_from_port
from tests.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.utility_test_functions import *


frmt_date = datetime.datetime.now().strftime("%Y%m%d")


def restart_phone_book():
    pair_plan_process = subprocess.Popen(["python", "launch_msgspec_fastapi.py"],
                                          cwd=PAIR_STRAT_ENGINE_DIR / "scripts")


def _verify_server_ready_state_in_recovered_plan(plan_state_to_handle: PlanState, pair_plan_id: int):
    for _ in range(30):
        # checking server_ready_state of executor
        try:
            updated_pair_plan = (
                email_book_service_native_web_client.get_pair_plan_client(pair_plan_id))
            if plan_state_to_handle != PlanState.PlanState_SNOOZED:
                if plan_state_to_handle in [PlanState.PlanState_ACTIVE, PlanState.PlanState_PAUSED,
                                             PlanState.PlanState_ERROR]:
                    if updated_pair_plan.server_ready_state == 3:
                        break
                else:
                    if updated_pair_plan.server_ready_state == 2:
                        break
            else:
                # if plan_state to check is SNOOZED then after recovery server_ready_state will not get
                # set to more than 1 since it is set only if SNOOZED is converted to READY
                if updated_pair_plan.server_ready_state == 1:
                    break
            time.sleep(1)
        except:  # no handling required: if error occurs retry
            pass
    else:
        pair_plan = (
            email_book_service_native_web_client.get_pair_plan_client(pair_plan_id))
        assert False, f"mismatched server_ready_state state, {plan_state_to_handle=}, {pair_plan=}"
    return updated_pair_plan


def _handle_process_kill(port: int):
    for _ in range(10):
        p_id: int = get_pid_from_port(port)
        if p_id is not None:
            os.kill(p_id, signal.SIGKILL)
            print(f"Killed process: {p_id}, port: {port}")
            break
        else:
            print("get_pid_from_port return None instead of pid")
        time.sleep(2)
    else:
        assert False, f"Unexpected: Can't kill process - Can't find any pid from port {port}"


def _check_new_executor_has_new_port(old_port: int, pair_plan_id: int):
    for _ in range(10):
        pair_plan = email_book_service_native_web_client.get_pair_plan_client(pair_plan_id)
        if pair_plan.port is not None and pair_plan.port != old_port:
            return pair_plan
        time.sleep(1)
    else:
        assert False, (f"PairPlan not found with updated port of recovered executor: "
                       f"pair_plan_id: {pair_plan_id}, old_port: {old_port}")


def _test_executor_crash_recovery(
        buy_symbol, sell_symbol, pair_plan_,
        expected_plan_limits_, expected_start_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        plan_state_to_handle, refresh_sec):
    # making limits suitable for this test
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 105000
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_plan, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))
    print(f"Executor crash test for plan with state: {plan_state_to_handle}, {buy_symbol=}, {sell_symbol=}, {created_pair_plan.id=}")

    if plan_state_to_handle != PlanState.PlanState_ACTIVE:
        update_pair_plan_dict = PairPlanBaseModel.from_kwargs(_id=created_pair_plan.id,
                                                                plan_state=plan_state_to_handle
                                                                ).to_dict(exclude_none=True)
        created_pair_plan = email_book_service_native_web_client.patch_pair_plan_client(update_pair_plan_dict)
        if plan_state_to_handle == PlanState.PlanState_SNOOZED:
            # deleting all symbol_overview in plan which needs to check PlanState_SNOOZED - now after recovery
            # plan will not convert to READY
            symbol_overview_list = executor_web_client.get_all_symbol_overview_client()
            for symbol_overview in symbol_overview_list:
                executor_web_client.delete_symbol_overview_client(symbol_overview.id)

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        if plan_state_to_handle == PlanState.PlanState_ACTIVE:
            total_chore_count_for_each_side = 1
            place_sanity_chores_for_executor(
                buy_symbol, sell_symbol, created_pair_plan, total_chore_count_for_each_side, last_barter_fixture_list,
                residual_wait_sec, executor_web_client)
        port: int = created_pair_plan.port
        _handle_process_kill(port)      # asserts implicitly

        time.sleep(residual_wait_sec)

        _check_new_executor_has_new_port(old_port=port, pair_plan_id=created_pair_plan.id)
        time.sleep(residual_wait_sec)

        # checking server_ready_state in recovered_plan
        updated_pair_plan = _verify_server_ready_state_in_recovered_plan(plan_state_to_handle, created_pair_plan.id)

        # checking if state stays same as before recovery
        pair_plan = email_book_service_native_web_client.get_pair_plan_client(created_pair_plan.id)
        assert pair_plan.plan_state == created_pair_plan.plan_state, \
            (f"Mismatched: plan_state before crash was {created_pair_plan.plan_state}, but after recovery "
             f"plan_state is {pair_plan.plan_state}")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

    new_pair_plan = email_book_service_native_web_client.get_pair_plan_client(created_pair_plan.id)
    if plan_state_to_handle == PlanState.PlanState_ACTIVE:
        new_executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
            updated_pair_plan.host, updated_pair_plan.port)
        try:
            time.sleep(10)
            config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
            config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            new_executor_web_client.barter_simulator_reload_config_query_client()

            update_market_depth(new_pair_plan.cpp_port)

            total_chore_count_for_each_side = 1
            place_sanity_chores_for_executor(
                buy_symbol, sell_symbol, new_pair_plan, total_chore_count_for_each_side, last_barter_fixture_list,
                residual_wait_sec, new_executor_web_client, place_after_recovery=True)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.recovery
def test_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    symbols_n_plan_state_list = []
    plan_state_list = [PlanState.PlanState_ACTIVE, PlanState.PlanState_READY, PlanState.PlanState_PAUSED,
                        PlanState.PlanState_SNOOZED, PlanState.PlanState_ERROR, PlanState.PlanState_DONE]
    # plan_state_list = [PlanState.PlanState_ERROR]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(plan_state_list)]):
        symbols_n_plan_state_list.append((symbol_tuple[0], symbol_tuple[1], plan_state_list[index]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_plan_state_list)) as executor:
        results = [executor.submit(_test_executor_crash_recovery, buy_symbol, sell_symbol,
                                   deepcopy(pair_plan_),
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   handle_plan_state, refresh_sec_update_fixture)
                   for buy_symbol, sell_symbol, handle_plan_state in symbols_n_plan_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _activate_pair_plan_n_place_sanity_chores(
        buy_symbol, sell_symbol, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        plan_state_to_handle, refresh_sec, total_chore_count_for_each_side_=1):
    # making limits suitable for this test
    expected_plan_limits_.max_open_chores_per_side = 10
    expected_plan_limits_.residual_restriction.max_residual = 105000
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_plan, executor_web_client = (
    create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_,
                                       expected_plan_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                       market_depth_basemodel_list))

    if plan_state_to_handle != PlanState.PlanState_ACTIVE:
        created_pair_plan = email_book_service_native_web_client.patch_pair_plan_client(
            PairPlanBaseModel.from_kwargs(_id=created_pair_plan.id,
                                           plan_state=plan_state_to_handle).to_dict(exclude_none=True))
        if plan_state_to_handle == PlanState.PlanState_SNOOZED:
            # deleting all symbol_overview in plan which needs to check PlanState_SNOOZED - now after recovery
            # plan will not convert to READY
            symbol_overview_list = executor_web_client.get_all_symbol_overview_client()
            for symbol_overview in symbol_overview_list:
                executor_web_client.delete_symbol_overview_client(symbol_overview.id)

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(created_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol_ in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol_]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol_]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        if plan_state_to_handle == PlanState.PlanState_ACTIVE:
            place_sanity_chores_for_executor(
                buy_symbol, sell_symbol, created_pair_plan, total_chore_count_for_each_side_, last_barter_fixture_list,
                residual_wait_sec, executor_web_client)
    except AssertionError as e_:
        raise AssertionError(e_)
    except Exception as e_:
        print(f"Some Error Occurred: exception: {e_}, "
              f"traceback: {''.join(traceback.format_exception(None, e_, e_.__traceback__))}")
        raise Exception(e_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

    return created_pair_plan, executor_web_client, plan_state_to_handle


def _check_place_chores_post_pair_plan_n_executor_recovery(
        updated_pair_plan: PairPlanBaseModel,
        last_barter_fixture_list, refresh_sec, total_chore_count_for_each_side=2):
    residual_wait_sec = 4 * refresh_sec
    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(updated_pair_plan.id)

    buy_symbol = updated_pair_plan.pair_plan_params.plan_leg1.sec.sec_id
    sell_symbol = updated_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
    new_executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_plan.host, updated_pair_plan.port)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        new_executor_web_client.barter_simulator_reload_config_query_client()

        update_market_depth(updated_pair_plan.cpp_port)

        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, updated_pair_plan, total_chore_count_for_each_side, last_barter_fixture_list,
            residual_wait_sec, new_executor_web_client, place_after_recovery=True)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.recovery
def test_pair_plan_n_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    pair_plan_n_plan_state_tuple_list: List[Tuple[PairPlanBaseModel, PlanState]] = []
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_plan_state_list = []
    plan_state_list = [PlanState.PlanState_ACTIVE, PlanState.PlanState_READY, PlanState.PlanState_PAUSED,
                        PlanState.PlanState_SNOOZED, PlanState.PlanState_ERROR, PlanState.PlanState_DONE]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(plan_state_list)]):
        symbols_n_plan_state_list.append((symbol_tuple[0], symbol_tuple[1], plan_state_list[index]))

    total_chore_count_for_each_side_ = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_plan_state_list)) as executor:
        results = [executor.submit(_activate_pair_plan_n_place_sanity_chores, buy_symbol, sell_symbol,
                                   deepcopy(pair_plan_),
                                   deepcopy(expected_plan_limits_), deepcopy(expected_plan_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   plan_state_to_handle, refresh_sec_update_fixture, total_chore_count_for_each_side_)
                   for buy_symbol, sell_symbol, plan_state_to_handle in symbols_n_plan_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            pair_plan, _, plan_state_to_handle = future.result()
            pair_plan_n_plan_state_tuple_list.append((pair_plan, plan_state_to_handle))

    pair_plan_n_plan_state_tuple_list = (
        _kill_executors_n_phone_book(pair_plan_n_plan_state_tuple_list, residual_wait_sec))

    active_pair_plan_id = None
    for pair_plan, plan_state_to_handle in pair_plan_n_plan_state_tuple_list:
        if plan_state_to_handle == PlanState.PlanState_ACTIVE:
            active_pair_plan_id = pair_plan.id
    recovered_active_plan = email_book_service_native_web_client.get_pair_plan_client(active_pair_plan_id)
    total_chore_count_for_each_side = 1
    time.sleep(10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = [executor.submit(_check_place_chores_post_pair_plan_n_executor_recovery, recovered_active_plan,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _kill_executors_n_phone_book(activated_plan_n_plan_state_tuple_list, residual_wait_sec):
    port_list = [email_book_service_native_web_client.port]  # included phone_book port
    pair_plan_n_plan_state_list = []

    for activated_plan, plan_state_to_handle in activated_plan_n_plan_state_tuple_list:
        port_list.append(activated_plan.port)
        pair_plan_n_plan_state_list.append((activated_plan, plan_state_to_handle))

    for port in port_list:
        _handle_process_kill(port)  # asserts implicitly

    restart_phone_book()
    time.sleep(residual_wait_sec * 2)

    updated_pair_plan_n_plan_state_list: List[Tuple[PairPlanBaseModel, PlanState]] = []
    for old_pair_plan_, plan_state_to_handle in pair_plan_n_plan_state_list:
        for _ in range(20):
            pair_plan = email_book_service_native_web_client.get_pair_plan_client(old_pair_plan_.id)
            if pair_plan.port is not None and pair_plan.port != old_pair_plan_.port:
                break
            time.sleep(1)
        else:
            assert False, (f"PairPlan not found with updated port of recovered executor, {old_pair_plan_.port=}, "
                           f"{old_pair_plan_.id=}")

        # checking server_ready_state in recovered_plan
        updated_pair_plan = _verify_server_ready_state_in_recovered_plan(plan_state_to_handle, pair_plan.id)

        updated_pair_plan_n_plan_state_list.append((updated_pair_plan, plan_state_to_handle))
    time.sleep(residual_wait_sec)
    return updated_pair_plan_n_plan_state_list


def check_all_cache(pair_plan_n_plan_state_tuple_list: List[Tuple[PairPlanBaseModel, PlanState]]):
    for pair_plan, plan_state in pair_plan_n_plan_state_tuple_list:
        if plan_state not in [PlanState.PlanState_READY, PlanState.PlanState_SNOOZED,
                               PlanState.PlanState_DONE]:

            executor_http_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(pair_plan.host,
                                                                                                pair_plan.port)
            # checking plan_status
            plan_status_list: List[PlanStatusBaseModel] = executor_http_client.get_all_plan_status_client()
            cached_plan_status_list: List[PlanStatusBaseModel] = (
                executor_http_client.get_plan_status_from_cache_query_client())
            assert plan_status_list == cached_plan_status_list, \
                ("Mismatched: cached plan status is not same as stored plan status, "
                 f"cached plan status: {cached_plan_status_list}, "
                 f"stored plan status: {plan_status_list}")

            # checking plan_brief
            plan_brief_list: List[PlanBriefBaseModel] = executor_http_client.get_all_plan_brief_client()
            cached_plan_brief_list: List[PlanBriefBaseModel] = (
                executor_http_client.get_plan_brief_from_cache_query_client())
            assert plan_brief_list == cached_plan_brief_list, \
                ("Mismatched: cached plan_brief is not same as stored plan_brief, "
                 f"cached plan_brief: {cached_plan_brief_list}, "
                 f"stored plan_brief: {plan_brief_list}")

            # checking plan_limits
            plan_limits_list: List[PlanLimitsBaseModel] = executor_http_client.get_all_plan_limits_client()
            cached_plan_limits_list: List[PlanLimitsBaseModel] = (
                executor_http_client.get_plan_limits_from_cache_query_client())
            assert plan_limits_list == cached_plan_limits_list, \
                ("Mismatched: cached plan_limits is not same as stored plan_limits, "
                 f"cached plan_limits: {cached_plan_limits_list}, "
                 f"stored plan_limits: {plan_limits_list}")

            # checking symbol_side_snapshot
            symbol_side_snapshot_list: List[SymbolSideSnapshotBaseModel] = (
                executor_http_client.get_all_symbol_side_snapshot_client())
            cached_symbol_side_snapshot_list: List[SymbolSideSnapshotBaseModel] = (
                executor_http_client.get_symbol_side_snapshots_from_cache_query_client())
            assert symbol_side_snapshot_list == cached_symbol_side_snapshot_list, \
                ("Mismatched: cached symbol_side_snapshot is not same as stored symbol_side_snapshot, "
                 f"cached symbol_side_snapshot: {cached_symbol_side_snapshot_list}, "
                 f"stored symbol_side_snapshot: {symbol_side_snapshot_list}")

            # checking chore_journal
            chore_journal_list: List[ChoreJournalBaseModel] = (
                executor_http_client.get_all_chore_journal_client())
            cached_chore_journal_list: List[ChoreJournalBaseModel] = (
                executor_http_client.get_chore_journals_from_cache_query_client())
            assert chore_journal_list == cached_chore_journal_list, \
                ("Mismatched: cached chore_journal is not same as stored chore_journal, "
                 f"cached chore_journal: {cached_chore_journal_list}, "
                 f"stored chore_journal: {chore_journal_list}")

            # checking chore_snapshot
            chore_snapshot_list: List[ChoreSnapshotBaseModel] = (
                executor_http_client.get_all_chore_snapshot_client())
            cached_chore_snapshot_list: List[ChoreSnapshotBaseModel] = (
                executor_http_client.get_chore_snapshots_from_cache_query_client())
            assert chore_snapshot_list == cached_chore_snapshot_list, \
                ("Mismatched: cached chore_snapshot is not same as stored chore_snapshot, "
                 f"cached chore_snapshot: {cached_chore_snapshot_list}, "
                 f"stored chore_snapshot: {chore_snapshot_list}")


@pytest.mark.recovery
def test_recover_active_n_ready_plans_pair_n_active_all_after_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    """
    Creates 8 plans, activates and places one chore each side, then converts pair of plans
    to PAUSE, ERROR and READY, then kills pair plan and executors then recovers all and activates all again
    and places 2 chores each side per plan and kills pair plan and executors again and again recovers and places
    1 chore each side per plan again
    """
    pair_plan_n_plan_state_tuple_list: List[Tuple[PairPlanBaseModel, PlanState]] = []
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_plan_state_list = []

    # Starting 8 plans - all active and places 1 chore each side
    plan_state_list = [PlanState.PlanState_ACTIVE]*6 + [PlanState.PlanState_READY]*2
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(plan_state_list)]):
        symbols_n_plan_state_list.append((symbol_tuple[0], symbol_tuple[1], plan_state_list[index]))

    total_chore_count_for_each_side_ = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_plan_state_list)) as executor:
        results = [executor.submit(_activate_pair_plan_n_place_sanity_chores, buy_symbol, sell_symbol,
                                   deepcopy(pair_plan_), deepcopy(expected_plan_limits_),
                                   deepcopy(expected_plan_status_), deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   plan_state_to_handle, refresh_sec_update_fixture,
                                   total_chore_count_for_each_side_)
                   for buy_symbol, sell_symbol, plan_state_to_handle in symbols_n_plan_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            pair_plan, executor_http_client, plan_state_to_handle = future.result()
            pair_plan_n_plan_state_tuple_list.append((pair_plan, plan_state_to_handle))

    active_plan_n_plan_state_tuple_list: List[Tuple[PairPlanBaseModel, PlanState]] = \
        [(pair_plan, plan_state) for pair_plan, plan_state in pair_plan_n_plan_state_tuple_list
         if pair_plan.plan_state != PlanState.PlanState_READY]
    pair_plan_n_plan_state_tuple_list = \
        [(pair_plan, plan_state) for pair_plan, plan_state in pair_plan_n_plan_state_tuple_list
         if pair_plan.plan_state == PlanState.PlanState_READY]

    # Converting some active plans to PAUSE and ERROR states before killing processes
    update_plan_state_list = [
        PlanState.PlanState_PAUSED, PlanState.PlanState_PAUSED,
        PlanState.PlanState_ERROR, PlanState.PlanState_ERROR,
        PlanState.PlanState_ACTIVE, PlanState.PlanState_ACTIVE]
    for index, plan_state_ in enumerate(update_plan_state_list):
        activate_plan, _ = active_plan_n_plan_state_tuple_list[index]
        if plan_state_ != PlanState.PlanState_ACTIVE:
            email_book_service_native_web_client.patch_pair_plan_client(
                PairPlanBaseModel.from_kwargs(_id=activate_plan.id,
                                               plan_state=plan_state_).to_dict(exclude_none=True))
        pair_plan_n_plan_state_tuple_list.append((activate_plan, plan_state_))

    pair_plan_n_plan_state_tuple_list = (
        _kill_executors_n_phone_book(pair_plan_n_plan_state_tuple_list, residual_wait_sec))

    # checking all cache computes
    check_all_cache(pair_plan_n_plan_state_tuple_list)

    # activating all plans
    recovered_active_plan_list: List = []
    activated_pair_plan_n_plan_state_tuple_list = []
    for pair_plan, plan_state_to_handle in pair_plan_n_plan_state_tuple_list:
        if plan_state_to_handle != PlanState.PlanState_ACTIVE:
            active_pair_plan = email_book_service_native_web_client.patch_pair_plan_client(
                PairPlanBaseModel.from_kwargs(_id=pair_plan.id,
                                               plan_state=PlanState.PlanState_ACTIVE).to_dict(exclude_none=True))
            pair_plan = active_pair_plan
        # else all are already active
        recovered_active_plan = email_book_service_native_web_client.get_pair_plan_client(pair_plan.id)
        recovered_active_plan_list.append(recovered_active_plan)
        activated_pair_plan_n_plan_state_tuple_list.append((recovered_active_plan, PlanState.PlanState_ACTIVE))

    total_chore_count_for_each_side = 1
    time.sleep(10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(recovered_active_plan_list)) as executor:
        results = [executor.submit(_check_place_chores_post_pair_plan_n_executor_recovery, recovered_pair_plan,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)
                   for recovered_pair_plan in recovered_active_plan_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    pair_plan_n_plan_state_tuple_list = (
        _kill_executors_n_phone_book(activated_pair_plan_n_plan_state_tuple_list, residual_wait_sec))

    # checking all cache computes
    check_all_cache(pair_plan_n_plan_state_tuple_list)

    time.sleep(10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(pair_plan_n_plan_state_tuple_list)) as executor:
        results = [executor.submit(_check_place_chores_post_pair_plan_n_executor_recovery, recovered_pair_plan,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)
                   for recovered_pair_plan, _ in pair_plan_n_plan_state_tuple_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise future.exception()


@pytest.mark.recovery
def test_recover_snoozed_n_activate_plan_after_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]
    stored_pair_plan_basemodel = create_plan(leg1_symbol, leg2_symbol, pair_plan_)

    # killing executor with partial name - port is not allocated for this plan yet
    os.system(f'kill $(pgrep -f "launch_msgspec_fastapi.py 1 &")')
    pair_plan_n_plan_state_tuple_list = (
        _kill_executors_n_phone_book([], residual_wait_sec))

    active_plan, executor_web_client = move_snoozed_pair_plan_to_ready_n_then_active(
        stored_pair_plan_basemodel, market_depth_basemodel_list,
        symbol_overview_obj_list, expected_plan_limits_, expected_plan_status_)

    # running Last Barter
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, active_plan.cpp_port)
    print(f"LastBarter created: buy_symbol: {leg1_symbol}, sell_symbol: {leg2_symbol}")

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(active_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol_ in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol_]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol_]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side_ = 1
        place_sanity_chores_for_executor(
            leg1_symbol, leg2_symbol, active_plan, total_chore_count_for_each_side_, last_barter_fixture_list,
            residual_wait_sec, executor_web_client)
    except AssertionError as e_:
        raise AssertionError(e_)
    except Exception as e_:
        print(f"Some Error Occurred: exception: {e_}, "
              f"traceback: {''.join(traceback.format_exception(None, e_, e_.__traceback__))}")
        raise Exception(e_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _test_post_pair_plan_crash_recovery(updated_pair_plan: PairPlanBaseModel, executor_web_client,
                                         last_barter_fixture_list, refresh_sec):
    residual_wait_sec = 4 * refresh_sec

    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(updated_pair_plan.id)

    buy_symbol = updated_pair_plan.pair_plan_params.plan_leg1.sec.sec_id
    sell_symbol = updated_pair_plan.pair_plan_params.plan_leg2.sec.sec_id
    recovered_contact_status: ContactStatusBaseModel = (
        email_book_service_native_web_client.get_contact_status_client(1))

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = 2
        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, updated_pair_plan, total_chore_count_for_each_side, last_barter_fixture_list,
            residual_wait_sec, executor_web_client, place_after_recovery=True)

        new_contact_status: ContactStatusBaseModel = (
            email_book_service_native_web_client.get_contact_status_client(1))

        assert recovered_contact_status != new_contact_status, \
            ("Unexpected: contact must have got updated after pair_plan recover, "
             f"old_contact_status {recovered_contact_status}, "
             f"new_contact_status {new_contact_status}")

        done_pair_plan = email_book_service_native_web_client.patch_pair_plan_client(
            PairPlanBaseModel.from_kwargs(_id=updated_pair_plan.id,
                                           plan_state=PlanState.PlanState_DONE).to_dict(exclude_none=True))

        try:
            email_book_service_native_web_client.delete_pair_plan_client(done_pair_plan.id)
        except Exception as e:
            raise Exception(f"PairPlan delete failed, exception: {e}")

        time.sleep(2)
        try:
            executor_web_client.get_all_ui_layout_client()
        except Exception as e:
            if "Failed to establish a new connection: [Errno 111] Connection refused" not in str(e):
                raise Exception(f"Expected Exception is connection refused error but got exception: {e}")
        else:
            assert False, ("Since plan is deleted corresponding executor must also get terminated but "
                           f"still functioning, port: {updated_pair_plan.port}")
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)


@pytest.mark.recovery
def test_pair_plan_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    activated_plan_n_executor_http_client_tuple_list: List[Tuple[PairPlan, StreetBookServiceHttpClient]] = []
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_plan_state_list = []
    plan_state_list = [PlanState.PlanState_ACTIVE, PlanState.PlanState_READY, PlanState.PlanState_PAUSED,
                        PlanState.PlanState_SNOOZED, PlanState.PlanState_ERROR, PlanState.PlanState_DONE]

    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(plan_state_list)]):
        symbols_n_plan_state_list.append((symbol_tuple[0], symbol_tuple[1], plan_state_list[index]))

    total_chore_count_for_each_side_ = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_plan_state_list)) as executor:
        results = [executor.submit(_activate_pair_plan_n_place_sanity_chores, buy_symbol, sell_symbol,
                                   deepcopy(pair_plan_), deepcopy(expected_plan_limits_),
                                   deepcopy(expected_plan_status_), deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   plan_state_to_handle, refresh_sec_update_fixture,
                                   total_chore_count_for_each_side_)
                   for buy_symbol, sell_symbol, plan_state_to_handle in symbols_n_plan_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            activated_plan_n_executor_http_client_tuple_list.append(future.result())

    pair_plan_n_plan_state_list = []

    for activated_plan, _, plan_state_to_handle in activated_plan_n_executor_http_client_tuple_list:
        pair_plan_n_plan_state_list.append((activated_plan, plan_state_to_handle))

    pair_plan_port: int = email_book_service_native_web_client.port
    _handle_process_kill(pair_plan_port)  # asserts implicitly

    restart_phone_book()
    time.sleep(residual_wait_sec * 2)

    for old_pair_plan, plan_state_to_handle in pair_plan_n_plan_state_list:
        for _ in range(20):
            pair_plan = email_book_service_native_web_client.get_pair_plan_client(old_pair_plan.id)
            if pair_plan.port is not None and pair_plan.port == old_pair_plan.port:
                break
        else:
            assert False, f"PairPlan not found with existing port after recovered pair_plan"

        # checking server_ready_state - since plans are converted to specific states after activating and executors
        # are not killed only phone_book is killed, plans will still have server_ready_state = 3
        expected_server_ready_state = 3
        assert pair_plan.server_ready_state == expected_server_ready_state, \
            (f"Mismatched server_ready_state in pair_plan, {expected_server_ready_state=}, "
             f"received {pair_plan.server_ready_state}")

    time.sleep(residual_wait_sec)

    active_pair_plan_id = None
    for pair_plan, plan_state_to_handle in pair_plan_n_plan_state_list:
        if plan_state_to_handle == PlanState.PlanState_ACTIVE:
            active_pair_plan_id = pair_plan.id
    recovered_active_plan = email_book_service_native_web_client.get_pair_plan_client(active_pair_plan_id)
    total_chore_count_for_each_side = 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = [executor.submit(_check_place_chores_post_pair_plan_n_executor_recovery, recovered_active_plan,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


# todo: Currently broken - DB updates from log analyzer currently only updates plan_view
@pytest.mark.recovery1
def _test_update_pair_plan_from_pair_plan_log_book(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, last_barter_fixture_list,
        expected_chore_limits_, refresh_sec_update_fixture):
    """
    INFO: created plan and activates it with low max_single_leg_notional so consumable_notional becomes low and
    plan_limits.min_chore_notional is made higher than consumable_notional intentionally.
    After this pair_plan engine process is killed and since executor service is still up, triggers place chore
    which results in getting rejected as plan is found as Done because of
    consumable_notional < plan_limits.min_chore_notional and pair_start is tried to be updated as PAUSED but
    pair_plan engine is down so executor logs this as log to be handled by pair_plan log analyzer once
    pair_plan is up. pair_plan is restarted and then test checks state must be Done
    """

    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # create pair_plan
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_plan, executor_web_client = create_n_activate_plan(
        leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, market_depth_basemodel_list)

    time.sleep(5)

    _handle_process_kill(email_book_service_native_web_client.port)  # asserts implicitly

    # updating pair_buy_side_bartering_brief.consumable_notional to be lower than min_tradable_notional
    plan_brief_ = executor_web_client.get_plan_brief_client(activated_pair_plan.id)
    plan_brief_.pair_buy_side_bartering_brief.consumable_notional = 10
    updated_plan_brief = executor_web_client.put_plan_brief_client(plan_brief_)
    assert updated_plan_brief == plan_brief_, \
        f"Mismatched plan_brief: expected: {plan_brief_}, updated: {updated_plan_brief}"

    total_chore_count_for_each_side = 1
    place_sanity_chores_for_executor(
        leg1_symbol, leg2_symbol, activated_pair_plan, total_chore_count_for_each_side, last_barter_fixture_list,
        residual_wait_sec, executor_web_client, place_after_recovery=True,
        expect_no_chore=True)

    time.sleep(5)
    restart_phone_book()
    time.sleep(residual_wait_sec * 2)

    updated_pair_plan = email_book_service_native_web_client.get_pair_plan_client(activated_pair_plan.id)
    assert updated_pair_plan.plan_state == PlanState.PlanState_PAUSED, \
        (f"Mismatched: PlanState must be PAUSE after update when phone_book was down, "
         f"found: {updated_pair_plan.plan_state}")


def _place_chore_n_kill_executor_n_verify_post_recovery(
        leg1_symbol, leg2_symbol, activated_pair_plan, last_barter_fixture_list,
        executor_web_client, residual_wait_sec, expected_chore_event, check_fulfilled: bool = False):
    bid_buy_top_market_depth, ask_sell_top_market_depth = (
        get_buy_bid_n_ask_sell_market_depth(leg1_symbol, leg2_symbol, activated_pair_plan))

    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, activated_pair_plan.cpp_port)
    time.sleep(1)
    update_tob_through_market_depth_to_place_buy_chore(activated_pair_plan.cpp_port, bid_buy_top_market_depth,
                                                       ask_sell_top_market_depth)

    ack_chore_journal = get_latest_chore_journal_with_event_and_symbol(expected_chore_event,
                                                                       leg1_symbol, executor_web_client)

    if check_fulfilled:
        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, executor_web_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
            f"Mismatched chore_status: expected {ChoreStatusType.OE_FILLED}, found: {chore_snapshot.chore_status}"
        assert chore_snapshot.cxled_qty == 0, \
            f"Mismatched cxled_qty: expected 0, received {chore_snapshot.cxled_qty}"
        assert chore_snapshot.filled_qty == ack_chore_journal.chore.qty, \
            f"Mismatched filled_qty: expected {ack_chore_journal.chore.qty}, received {chore_snapshot.cxled_qty}"

    port: int = activated_pair_plan.port
    _handle_process_kill(port)  # asserts implicitly
    time.sleep(residual_wait_sec)

    _check_new_executor_has_new_port(old_port=port, pair_plan_id=activated_pair_plan.id)
    time.sleep(residual_wait_sec)

    # checking server_ready_state in recovered_plan
    updated_pair_plan = _verify_server_ready_state_in_recovered_plan(PlanState.PlanState_ACTIVE,
                                                                       activated_pair_plan.id)

    new_executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_plan.host, updated_pair_plan.port)

    cxl_chore_journal = get_latest_chore_journal_with_event_and_symbol(
        ChoreEventType.OE_CXL_ACK, leg1_symbol, new_executor_web_client,
        expect_no_chore=True if check_fulfilled else False)
    return ack_chore_journal, new_executor_web_client


def test_verify_placed_chores_get_cxled_after_recovery1(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    """
    checks if chores that got placed before crash gets cxled after recovery for being residual
    Places chore with 50% fill and just after that kills executor to verify if recovered executor
    cxl chore for residual
    """
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # create pair_plan
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_plan, executor_web_client = create_n_activate_plan(
        leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, market_depth_basemodel_list)

    time.sleep(5)
    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        ack_chore_journal, new_executor_web_client = _place_chore_n_kill_executor_n_verify_post_recovery(
            leg1_symbol, leg2_symbol, activated_pair_plan, last_barter_fixture_list,
            executor_web_client, residual_wait_sec, ChoreEventType.OE_ACK)
        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, new_executor_web_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
            f"Mismatched chore_status: expected {ChoreStatusType.OE_DOD}, found: {chore_snapshot.chore_status}"
        # below logic is required for handling odd chore qty: expected_cxled_qty = chore_qty - filled_qty
        expected_cxled_qty = ack_chore_journal.chore.qty - int(ack_chore_journal.chore.qty / 2)
        assert chore_snapshot.cxled_qty == expected_cxled_qty, \
            f"Mismatched cxled_qty: expected {expected_cxled_qty}, received {chore_snapshot.cxled_qty}"
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def test_verify_placed_chores_get_cxled_after_recovery2(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    """
    checks if chores that got placed before crash gets cxled after recovery for being residual
    Places acked chore with no fill and just after that kills executor to verify if recovered executor
    cxl chore for residual
    """
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # create pair_plan
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_plan, executor_web_client = create_n_activate_plan(
        leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, market_depth_basemodel_list)

    time.sleep(5)
    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["simulate_avoid_fill_after_ack"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        ack_chore_journal, new_executor_web_client = _place_chore_n_kill_executor_n_verify_post_recovery(
            leg1_symbol, leg2_symbol, activated_pair_plan, last_barter_fixture_list,
            executor_web_client, residual_wait_sec, ChoreEventType.OE_ACK)
        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, new_executor_web_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
            f"Mismatched chore_status: expected {ChoreStatusType.OE_DOD}, found: {chore_snapshot.chore_status}"
        assert chore_snapshot.cxled_qty == ack_chore_journal.chore.qty, \
            f"Mismatched cxled_qty: expected {ack_chore_journal.chore.qty}, received {chore_snapshot.cxled_qty}"
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def test_verify_placed_chores_get_cxled_after_recovery3(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    """
    checks if chores that got placed before crash gets cxled after recovery for being residual
    Places un-acked chore and just after that kills executor to verify if recovered executor
    cxl chore for residual
    """
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # create pair_plan
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_plan, executor_web_client = create_n_activate_plan(
        leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, market_depth_basemodel_list)

    try:
        ack_chore_journal, new_executor_web_client = _place_chore_n_kill_executor_n_verify_post_recovery(
            leg1_symbol, leg2_symbol, activated_pair_plan, last_barter_fixture_list,
            executor_web_client, residual_wait_sec, ChoreEventType.OE_NEW)
        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, new_executor_web_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_DOD, \
            f"Mismatched chore_status: expected {ChoreStatusType.OE_DOD}, found: {chore_snapshot.chore_status}"
        assert chore_snapshot.cxled_qty == ack_chore_journal.chore.qty, \
            f"Mismatched cxled_qty: expected {ack_chore_journal.chore.qty}, received {chore_snapshot.cxled_qty}"
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)


def test_verify_placed_chores_get_cxled_after_recovery4(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    """
    checks if chores that got placed before crash gets cxled after recovery for being residual
    Places un-acked chore and just after that kills executor to verify if recovered executor
    cxl chore for residual
    """
    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # create pair_plan
    expected_plan_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_plan, executor_web_client = create_n_activate_plan(
        leg1_symbol, leg2_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, market_depth_basemodel_list)

    time.sleep(5)
    config_file_path, config_dict, config_dict_str = get_config_file_path_n_config_dict(activated_pair_plan.id)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 100
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        ack_chore_journal, new_executor_web_client = _place_chore_n_kill_executor_n_verify_post_recovery(
            leg1_symbol, leg2_symbol, activated_pair_plan, last_barter_fixture_list,
            executor_web_client, residual_wait_sec, ChoreEventType.OE_ACK, check_fulfilled=True)
        chore_snapshot = get_chore_snapshot_from_chore_id(ack_chore_journal.chore.chore_id, new_executor_web_client)
        assert chore_snapshot.chore_status == ChoreStatusType.OE_FILLED, \
            f"Mismatched chore_status: expected {ChoreStatusType.OE_FILLED}, found: {chore_snapshot.chore_status}"
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.recovery
def test_recover_kill_switch_when_bartering_server_has_enabled(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list, refresh_sec_update_fixture):

    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    residual_wait_sec = 4 * refresh_sec_update_fixture
    try:
        # updating yaml_configs according to this test
        config_dict["is_kill_switch_enabled"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()

        pair_plan_port: int = email_book_service_native_web_client.port
        _handle_process_kill(pair_plan_port)  # asserts implicitly

        restart_phone_book()
        time.sleep(residual_wait_sec * 2)

        system_control = email_book_service_native_web_client.get_system_control_client(1)
        assert system_control.kill_switch, \
            ("Kill Switch must be triggered and enabled after restart according to test configuration but "
             "kill switch found False")

        # validating if bartering_link.trigger_kill_switch got called
        check_str = "Called BarteringLink.BarteringLink.trigger_kill_switch"
        contact_alerts = log_book_web_client.get_all_contact_alert_client()
        for alert in contact_alerts:
            if re.search(check_str, alert.alert_brief):
                assert False, \
                    ("BarteringLink.trigger_kill_switch must not have been triggered when kill switch is enabled in"
                     "db by start-up check")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()


@pytest.mark.recovery
def test_recover_kill_switch_when_bartering_server_has_disabled(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, last_barter_fixture_list,
        market_depth_basemodel_list, refresh_sec_update_fixture):

    residual_wait_sec = 4 * refresh_sec_update_fixture
    system_control = SystemControlBaseModel.from_kwargs(_id=1, kill_switch=True)
    email_book_service_native_web_client.patch_system_control_client(system_control.to_dict(exclude_none=True))

    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        config_dict["is_kill_switch_enabled"] = False
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()

        pair_plan_port: int = email_book_service_native_web_client.port
        _handle_process_kill(pair_plan_port)  # asserts implicitly

        restart_phone_book()
        time.sleep(residual_wait_sec * 2)

        system_control = email_book_service_native_web_client.get_system_control_client(1)
        assert system_control.kill_switch, \
            "Kill Switch must be unchanged after restart but found changed, kill_switch found as False"

        # validating if bartering_link.trigger_kill_switch got called
        check_str = "Called BarteringLink.trigger_kill_switch"
        alert_fail_message = f"Can't find contact alert saying '{check_str}'"
        time.sleep(5)
        check_alert_str_in_contact_alert(check_str, alert_fail_message)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        # updating simulator's configs
        email_book_service_native_web_client.log_simulator_reload_config_query_client()


@pytest.mark.recovery
def test_cpp_app_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_plan_,
        expected_plan_limits_, expected_plan_status_,
        symbol_overview_obj_list, last_barter_fixture_list, max_loop_count_per_side,
        market_depth_basemodel_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    max_loop_count_per_side = 1

    buy_symbol, sell_symbol, created_pair_plan, executor_web_client = (
        place_sanity_chores(buy_symbol, sell_symbol, pair_plan_, expected_plan_limits_, expected_plan_status_,
                            symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
                            max_loop_count_per_side, refresh_sec_update_fixture))

    log_file_path = str(STRAT_EXECUTOR / "log" / f"street_book_{created_pair_plan.id}_logs_{frmt_date}.log")
    test_log = "Log added by test_cpp_app_recovery: ignore it"
    # putting this log line in executor log to use it later in test as a point from which new cpp_app's
    # released semaphore's log will get logged
    echo_cmd = f'echo "{test_log}" >> {log_file_path}'
    os.system(echo_cmd)

    # killing cpp app
    result = subprocess.run(
        [f'pgrep', '-f', f'mobile_book_executable.*executor_{created_pair_plan.id}_simulate_config'],
        text=True,  # Capture text output
        stdout=subprocess.PIPE,  # Capture standard output
        stderr=subprocess.PIPE,  # Capture standard error
    )
    if result.stdout:
        process_id = parse_to_int(result.stdout.strip())
        os.kill(parse_to_int(process_id), signal.SIGKILL)
        print(f"Killed cpp process - {process_id=}")
        time.sleep(2)
    else:
        assert False, \
            (f"Can't find cpp process with plan_id: {created_pair_plan.id} running, "
             f"process check output: {result.stdout}")

    scripts_dir = STRAT_EXECUTOR / "scripts"
    # start file generator
    start_sh_file_path = scripts_dir / f"start_ps_id_{created_pair_plan.id}_md.sh"
    subprocess.Popen([f"{start_sh_file_path}"])

    time.sleep(10)

    # counting all 'Couldn't find matching shm signature' logs after log which we added in this test for reference
    expected_log_line = "Couldn't find matching shm signature, ignoring this internal run cycle"
    count = 0
    found_start = False
    with open(log_file_path, 'r') as file:
        for line in file:
            # Check if we've reached the start line
            if not found_start and test_log in line:
                found_start = True
                continue  # Move to the next line after finding the start line

            # If start line has been found, count occurrences of the target line
            if found_start and expected_log_line in line:
                count += 1

    # since cpp when restarts does semaphore release 5 times to notify python for restart +
    # once when cpp app sets shm with empty data
    assert count == 6, \
        f"Mismatched number of times log msg must exists, expected 6, found {count}"

    _check_place_chores_post_pair_plan_n_executor_recovery(
        created_pair_plan, last_barter_fixture_list, refresh_sec_update_fixture, total_chore_count_for_each_side=2)
