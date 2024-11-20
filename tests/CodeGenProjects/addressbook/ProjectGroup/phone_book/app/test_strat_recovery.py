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
    pair_strat_process = subprocess.Popen(["python", "launch_msgspec_fastapi.py"],
                                          cwd=PAIR_STRAT_ENGINE_DIR / "scripts")


def _test_executor_crash_recovery(
        buy_symbol, sell_symbol, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        strat_state_to_handle, refresh_sec):
    # making limits suitable for this test
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_web_client = (
        create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                           market_depth_basemodel_list))

    if strat_state_to_handle != StratState.StratState_ACTIVE:
        created_pair_strat = email_book_service_native_web_client.patch_pair_strat_client(
            PairStratBaseModel.from_kwargs(_id=created_pair_strat.id,
                                           strat_state=strat_state_to_handle).to_dict(exclude_none=True))
        if strat_state_to_handle == StratState.StratState_SNOOZED:
            # deleting all symbol_overview in strat which needs to check StratState_SNOOZED - now after recovery
            # strat will not convert to READY
            symbol_overview_list = executor_web_client.get_all_symbol_overview_client()
            for symbol_overview in symbol_overview_list:
                executor_web_client.delete_symbol_overview_client(symbol_overview.id)

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        if strat_state_to_handle == StratState.StratState_ACTIVE:
            total_chore_count_for_each_side = 1
            place_sanity_chores_for_executor(
                buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
                residual_wait_sec, executor_web_client)
        port: int = created_pair_strat.port

        for _ in range(10):
            p_id: int = get_pid_from_port(port)
            if p_id is not None:
                os.kill(p_id, signal.SIGKILL)
                print(f"Killed executor process: {p_id}, port: {port}")
                break
            else:
                print("get_pid_from_port return None instead of pid")
            time.sleep(2)
        else:
            assert False, f"Unexpected: Can't kill executor - Can't find any pid from port {port}"

        time.sleep(residual_wait_sec)

        old_port = port
        for _ in range(10):
            pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
            if pair_strat.port is not None and pair_strat.port != old_port:
                break
            time.sleep(1)
        else:
            assert False, (f"PairStrat not found with updated port of recovered executor: "
                           f"pair_strat_id: {created_pair_strat.id}, old_port: {old_port}")

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    email_book_service_native_web_client.get_pair_strat_client(pair_strat.id))
                if strat_state_to_handle != StratState.StratState_SNOOZED:
                    if updated_pair_strat.is_partially_running and updated_pair_strat.is_executor_running:
                        break
                else:
                    # if strat_state to check is SNOOZED then after recovery is_executor_running will not get
                    # set since it is set only if SNOOZED is converted to READY
                    if updated_pair_strat.is_partially_running:
                        break
                time.sleep(1)
            except:  # no handling required: if error occurs retry
                pass
        else:
            assert False, (f"is_executor_running state must be True, found false, "
                           f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
        time.sleep(residual_wait_sec)

        # checking if state stays same as before recovery
        pair_strat = email_book_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
        assert pair_strat.strat_state == created_pair_strat.strat_state, \
            (f"Mismatched: strat_state before crash was {created_pair_strat.strat_state}, but after recovery "
             f"strat_state is {pair_strat.strat_state}")

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

    if strat_state_to_handle == StratState.StratState_ACTIVE:
        new_executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
            updated_pair_strat.host, updated_pair_strat.port)
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

            update_market_depth(new_executor_web_client)

            total_chore_count_for_each_side = 1
            place_sanity_chores_for_executor(
                buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
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
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    symbols_n_strat_state_list = []
    strat_state_list = [StratState.StratState_ACTIVE, StratState.StratState_READY, StratState.StratState_PAUSED,
                        StratState.StratState_SNOOZED, StratState.StratState_ERROR, StratState.StratState_DONE]
    # strat_state_list = [StratState.StratState_READY]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_test_executor_crash_recovery, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   handle_strat_state, refresh_sec_update_fixture)
                   for buy_symbol, sell_symbol, handle_strat_state in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _activate_pair_strat_n_place_sanity_chores(
        buy_symbol, sell_symbol, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list,
        strat_state_to_handle, refresh_sec, total_chore_count_for_each_side_=1):
    # making limits suitable for this test
    expected_strat_limits_.max_open_chores_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_web_client = (
    create_pre_chore_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_strat_status_, symbol_overview_obj_list, last_barter_fixture_list,
                                       market_depth_basemodel_list))

    if strat_state_to_handle != StratState.StratState_ACTIVE:
        created_pair_strat = email_book_service_native_web_client.patch_pair_strat_client(
            PairStratBaseModel.from_kwargs(_id=created_pair_strat.id,
                                           strat_state=strat_state_to_handle).to_dict(exclude_none=True))
        if strat_state_to_handle == StratState.StratState_SNOOZED:
            # deleting all symbol_overview in strat which needs to check StratState_SNOOZED - now after recovery
            # strat will not convert to READY
            symbol_overview_list = executor_web_client.get_all_symbol_overview_client()
            for symbol_overview in symbol_overview_list:
                executor_web_client.delete_symbol_overview_client(symbol_overview.id)

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{created_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol_ in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol_]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol_]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        if strat_state_to_handle == StratState.StratState_ACTIVE:
            place_sanity_chores_for_executor(
                buy_symbol, sell_symbol, total_chore_count_for_each_side_, last_barter_fixture_list,
                residual_wait_sec, executor_web_client)
    except AssertionError as e_:
        raise AssertionError(e_)
    except Exception as e_:
        print(f"Some Error Occurred: exception: {e_}, "
              f"traceback: {''.join(traceback.format_exception(None, e_, e_.__traceback__))}")
        raise Exception(e_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

    return created_pair_strat, executor_web_client, strat_state_to_handle


def _check_place_chores_post_pair_strat_n_executor_recovery(
        updated_pair_strat: PairStratBaseModel,
        last_barter_fixture_list, refresh_sec, total_chore_count_for_each_side=2):
    residual_wait_sec = 4 * refresh_sec
    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{updated_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    buy_symbol = updated_pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    sell_symbol = updated_pair_strat.pair_strat_params.strat_leg2.sec.sec_id
    new_executor_web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_strat.host, updated_pair_strat.port)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        new_executor_web_client.barter_simulator_reload_config_query_client()

        update_market_depth(new_executor_web_client)

        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
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
def test_pair_strat_n_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    pair_strat_n_strat_state_tuple_list: List[Tuple[PairStratBaseModel, StratState]] = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_strat_state_list = []
    strat_state_list = [StratState.StratState_ACTIVE, StratState.StratState_READY, StratState.StratState_PAUSED,
                        StratState.StratState_SNOOZED, StratState.StratState_ERROR, StratState.StratState_DONE]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    total_chore_count_for_each_side_ = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_activate_pair_strat_n_place_sanity_chores, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_strat_status_),
                                   deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   strat_state_to_handle, refresh_sec_update_fixture, total_chore_count_for_each_side_)
                   for buy_symbol, sell_symbol, strat_state_to_handle in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            pair_strat, _, strat_state_to_handle = future.result()
            pair_strat_n_strat_state_tuple_list.append((pair_strat, strat_state_to_handle))

    pair_strat_n_strat_state_tuple_list = (
        _kill_executors_n_phone_book(pair_strat_n_strat_state_tuple_list, residual_wait_sec))

    active_pair_strat_id = None
    for pair_strat, strat_state_to_handle in pair_strat_n_strat_state_tuple_list:
        if strat_state_to_handle == StratState.StratState_ACTIVE:
            active_pair_strat_id = pair_strat.id
    recovered_active_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat_id)
    total_chore_count_for_each_side = 1
    time.sleep(10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = [executor.submit(_check_place_chores_post_pair_strat_n_executor_recovery, recovered_active_strat,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _kill_executors_n_phone_book(activated_strat_n_strat_state_tuple_list, residual_wait_sec):
    port_list = [email_book_service_native_web_client.port]  # included phone_book port
    pair_strat_n_strat_state_list = []

    for activated_strat, strat_state_to_handle in activated_strat_n_strat_state_tuple_list:
        port_list.append(activated_strat.port)
        pair_strat_n_strat_state_list.append((activated_strat, strat_state_to_handle))

    for port in port_list:
        for _ in range(10):
            p_id: int = get_pid_from_port(port)
            print(f"{port} -- {p_id}")
            if p_id is not None:
                os.kill(p_id, signal.SIGKILL)
                print(f"Killed process: {p_id}, port: {port}")
                break
            else:
                print("get_pid_from_port return None instead of pid")
            time.sleep(2)
        else:
            assert False, f"Unexpected: Can't kill process - Can't find any pid from port {port}"

    restart_phone_book()
    time.sleep(residual_wait_sec * 2)

    updated_pair_strat_n_strat_state_list: List[Tuple[PairStratBaseModel, StratState]] = []
    for old_pair_strat_, strat_state_to_handle in pair_strat_n_strat_state_list:
        for _ in range(20):
            pair_strat = email_book_service_native_web_client.get_pair_strat_client(old_pair_strat_.id)
            if pair_strat.port is not None and pair_strat.port != old_pair_strat_.port:
                break
            time.sleep(1)
        else:
            assert False, (f"PairStrat not found with updated port of recovered executor, {old_pair_strat_.port=}, "
                           f"{old_pair_strat_.id=}")

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    email_book_service_native_web_client.get_pair_strat_client(pair_strat.id))
                if strat_state_to_handle != StratState.StratState_SNOOZED:
                    if updated_pair_strat.is_partially_running and updated_pair_strat.is_executor_running:
                        break
                else:
                    # if strat_state to check is SNOOZED then after recovery is_executor_running will not get
                    # set since it is set only if SNOOZED is converted to READY
                    if updated_pair_strat.is_partially_running:
                        break
            except:  # no handling required: if error occurs retry
                pass
        else:
            assert False, (f"is_executor_running state must be True, found false, "
                           f"pair_strat_params: {old_pair_strat_.pair_strat_params}")
        updated_pair_strat_n_strat_state_list.append((updated_pair_strat, strat_state_to_handle))
    time.sleep(residual_wait_sec)
    return updated_pair_strat_n_strat_state_list


def check_all_cache(pair_strat_n_strat_state_tuple_list: List[Tuple[PairStratBaseModel, StratState]]):
    for pair_strat, strat_state in pair_strat_n_strat_state_tuple_list:
        if strat_state not in [StratState.StratState_READY, StratState.StratState_SNOOZED,
                               StratState.StratState_DONE]:

            executor_http_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(pair_strat.host,
                                                                                                pair_strat.port)
            # checking strat_status
            strat_status_list: List[StratStatusBaseModel] = executor_http_client.get_all_strat_status_client()
            cached_strat_status_list: List[StratStatusBaseModel] = (
                executor_http_client.get_strat_status_from_cache_query_client())
            assert strat_status_list == cached_strat_status_list, \
                ("Mismatched: cached strat status is not same as stored strat status, "
                 f"cached strat status: {cached_strat_status_list}, "
                 f"stored strat status: {strat_status_list}")

            # checking strat_brief
            strat_brief_list: List[StratBriefBaseModel] = executor_http_client.get_all_strat_brief_client()
            cached_strat_brief_list: List[StratBriefBaseModel] = (
                executor_http_client.get_strat_brief_from_cache_query_client())
            assert strat_brief_list == cached_strat_brief_list, \
                ("Mismatched: cached strat_brief is not same as stored strat_brief, "
                 f"cached strat_brief: {cached_strat_brief_list}, "
                 f"stored strat_brief: {strat_brief_list}")

            # checking strat_limits
            strat_limits_list: List[StratLimitsBaseModel] = executor_http_client.get_all_strat_limits_client()
            cached_strat_limits_list: List[StratLimitsBaseModel] = (
                executor_http_client.get_strat_limits_from_cache_query_client())
            assert strat_limits_list == cached_strat_limits_list, \
                ("Mismatched: cached strat_limits is not same as stored strat_limits, "
                 f"cached strat_limits: {cached_strat_limits_list}, "
                 f"stored strat_limits: {strat_limits_list}")

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
def test_recover_active_n_ready_strats_pair_n_active_all_after_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    """
    Creates 8 strats, activates and places one chore each side, then converts pair of strats
    to PAUSE, ERROR and READY, then kills pair strat and executors then recovers all and activates all again
    and places 2 chores each side per strat and kills pair strat and executors again and again recovers and places
    1 chore each side per strat again
    """
    pair_strat_n_strat_state_tuple_list: List[Tuple[PairStratBaseModel, StratState]] = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_strat_state_list = []

    # Starting 8 strats - all active and places 1 chore each side
    strat_state_list = [StratState.StratState_ACTIVE]*6 + [StratState.StratState_READY]*2
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    total_chore_count_for_each_side_ = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_activate_pair_strat_n_place_sanity_chores, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_), deepcopy(expected_strat_limits_),
                                   deepcopy(expected_strat_status_), deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   strat_state_to_handle, refresh_sec_update_fixture,
                                   total_chore_count_for_each_side_)
                   for buy_symbol, sell_symbol, strat_state_to_handle in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            pair_strat, executor_http_client, strat_state_to_handle = future.result()
            pair_strat_n_strat_state_tuple_list.append((pair_strat, strat_state_to_handle))

    active_strat_n_strat_state_tuple_list: List[Tuple[PairStratBaseModel, StratState]] = \
        [(pair_strat, strat_state) for pair_strat, strat_state in pair_strat_n_strat_state_tuple_list
         if pair_strat.strat_state != StratState.StratState_READY]
    pair_strat_n_strat_state_tuple_list = \
        [(pair_strat, strat_state) for pair_strat, strat_state in pair_strat_n_strat_state_tuple_list
         if pair_strat.strat_state == StratState.StratState_READY]

    # Converting some active strats to PAUSE and ERROR states before killing processes
    update_strat_state_list = [
        StratState.StratState_PAUSED, StratState.StratState_PAUSED,
        StratState.StratState_ERROR, StratState.StratState_ERROR,
        StratState.StratState_ACTIVE, StratState.StratState_ACTIVE]
    for index, strat_state_ in enumerate(update_strat_state_list):
        activate_strat, _ = active_strat_n_strat_state_tuple_list[index]
        if strat_state_ != StratState.StratState_ACTIVE:
            email_book_service_native_web_client.patch_pair_strat_client(
                PairStratBaseModel.from_kwargs(_id=activate_strat.id,
                                               strat_state=strat_state_).to_dict(exclude_none=True))
        pair_strat_n_strat_state_tuple_list.append((activate_strat, strat_state_))

    pair_strat_n_strat_state_tuple_list = (
        _kill_executors_n_phone_book(pair_strat_n_strat_state_tuple_list, residual_wait_sec))

    # checking all cache computes
    check_all_cache(pair_strat_n_strat_state_tuple_list)

    # activating all strats
    recovered_active_strat_list: List = []
    for pair_strat, strat_state_to_handle in pair_strat_n_strat_state_tuple_list:
        if strat_state_to_handle != StratState.StratState_ACTIVE:
            active_pair_strat = email_book_service_native_web_client.patch_pair_strat_client(
                PairStratBaseModel.from_kwargs(_id=pair_strat.id,
                                               strat_state=StratState.StratState_ACTIVE).to_dict(exclude_none=True))
            pair_strat = active_pair_strat
        # else all are already active
        recovered_active_strat = email_book_service_native_web_client.get_pair_strat_client(pair_strat.id)
        recovered_active_strat_list.append(recovered_active_strat)

    total_chore_count_for_each_side = 1
    time.sleep(10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(recovered_active_strat_list)) as executor:
        results = [executor.submit(_check_place_chores_post_pair_strat_n_executor_recovery, recovered_pair_strat,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)
                   for recovered_pair_strat in recovered_active_strat_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

    pair_strat_n_strat_state_tuple_list = (
        _kill_executors_n_phone_book(pair_strat_n_strat_state_tuple_list, residual_wait_sec))

    # checking all cache computes
    check_all_cache(pair_strat_n_strat_state_tuple_list)

    time.sleep(10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(pair_strat_n_strat_state_tuple_list)) as executor:
        results = [executor.submit(_check_place_chores_post_pair_strat_n_executor_recovery, recovered_pair_strat,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)
                   for recovered_pair_strat, _ in pair_strat_n_strat_state_tuple_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


@pytest.mark.recovery
def test_recover_snoozed_n_activate_strat_after_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]
    stored_pair_strat_basemodel = create_strat(leg1_symbol, leg2_symbol, pair_strat_)

    # killing executor with partial name - port is not allocated for this port yet
    os.system(f'kill $(pgrep -f "launch_msgspec_fastapi.py 1 &")')
    pair_strat_n_strat_state_tuple_list = (
        _kill_executors_n_phone_book([], residual_wait_sec))

    active_strat, executor_web_client = move_snoozed_pair_strat_to_ready_n_then_active(
        stored_pair_strat_basemodel, market_depth_basemodel_list,
        symbol_overview_obj_list, expected_strat_limits_, expected_strat_status_)

    # running Last Barter
    run_last_barter(leg1_symbol, leg2_symbol, last_barter_fixture_list, executor_web_client)
    print(f"LastBarter created: buy_symbol: {leg1_symbol}, sell_symbol: {leg2_symbol}")

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{active_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        for symbol_ in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol_]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol_]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side_ = 1
        place_sanity_chores_for_executor(
            leg1_symbol, leg2_symbol, total_chore_count_for_each_side_, last_barter_fixture_list,
            residual_wait_sec, executor_web_client)
    except AssertionError as e_:
        raise AssertionError(e_)
    except Exception as e_:
        print(f"Some Error Occurred: exception: {e_}, "
              f"traceback: {''.join(traceback.format_exception(None, e_, e_.__traceback__))}")
        raise Exception(e_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


def _test_post_pair_strat_crash_recovery(updated_pair_strat: PairStratBaseModel, executor_web_client,
                                         last_barter_fixture_list, refresh_sec):
    residual_wait_sec = 4 * refresh_sec

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{updated_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    buy_symbol = updated_pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    sell_symbol = updated_pair_strat.pair_strat_params.strat_leg2.sec.sec_id
    recovered_portfolio_status: PortfolioStatusBaseModel = (
        email_book_service_native_web_client.get_portfolio_status_client(1))

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.barter_simulator_reload_config_query_client()

        total_chore_count_for_each_side = 2
        place_sanity_chores_for_executor(
            buy_symbol, sell_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
            residual_wait_sec, executor_web_client, place_after_recovery=True)

        new_portfolio_status: PortfolioStatusBaseModel = (
            email_book_service_native_web_client.get_portfolio_status_client(1))

        assert recovered_portfolio_status != new_portfolio_status, \
            ("Unexpected: portfolio must have got updated after pair_strat recover, "
             f"old_portfolio_status {recovered_portfolio_status}, "
             f"new_portfolio_status {new_portfolio_status}")

        done_pair_strat = email_book_service_native_web_client.patch_pair_strat_client(
            PairStratBaseModel.from_kwargs(_id=updated_pair_strat.id,
                                           strat_state=StratState.StratState_DONE).to_dict(exclude_none=True))

        try:
            email_book_service_native_web_client.delete_pair_strat_client(done_pair_strat.id)
        except Exception as e:
            raise Exception(f"PairStrat delete failed, exception: {e}")

        time.sleep(2)
        try:
            executor_web_client.get_all_ui_layout_client()
        except Exception as e:
            if "Failed to establish a new connection: [Errno 111] Connection refused" not in str(e):
                raise Exception(f"Expected Exception is connection refused error but got exception: {e}")
        else:
            assert False, ("Since strat is deleted corresponding executor must also get terminated but "
                           f"still functioning, port: {updated_pair_strat.port}")
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)


@pytest.mark.recovery
def test_pair_strat_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        last_barter_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    activated_strat_n_executor_http_client_tuple_list: List[Tuple[PairStrat, StreetBookServiceHttpClient]] = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_strat_state_list = []
    strat_state_list = [StratState.StratState_ACTIVE, StratState.StratState_READY, StratState.StratState_PAUSED,
                        StratState.StratState_SNOOZED, StratState.StratState_ERROR, StratState.StratState_DONE]

    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    total_chore_count_for_each_side_ = 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_activate_pair_strat_n_place_sanity_chores, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_), deepcopy(expected_strat_limits_),
                                   deepcopy(expected_strat_status_), deepcopy(symbol_overview_obj_list),
                                   deepcopy(last_barter_fixture_list), deepcopy(market_depth_basemodel_list),
                                   strat_state_to_handle, refresh_sec_update_fixture,
                                   total_chore_count_for_each_side_)
                   for buy_symbol, sell_symbol, strat_state_to_handle in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            activated_strat_n_executor_http_client_tuple_list.append(future.result())

    pair_strat_n_strat_state_list = []

    for activated_strat, _, strat_state_to_handle in activated_strat_n_executor_http_client_tuple_list:
        pair_strat_n_strat_state_list.append((activated_strat, strat_state_to_handle))

    pair_strat_port: int = email_book_service_native_web_client.port

    for _ in range(10):
        p_id: int = get_pid_from_port(pair_strat_port)
        if p_id is not None:
            os.kill(p_id, signal.SIGKILL)
            print(f"Killed process: {p_id}, port: {pair_strat_port}")
            break
        else:
            print("get_pid_from_port return None instead of pid")
        time.sleep(2)
    else:
        assert False, f"Unexpected: Can't kill process - Can't find any pid from port {pair_strat_port}"

    restart_phone_book()
    time.sleep(residual_wait_sec * 2)

    for old_pair_strat, strat_state_to_handle in pair_strat_n_strat_state_list:
        for _ in range(20):
            pair_strat = email_book_service_native_web_client.get_pair_strat_client(old_pair_strat.id)
            if pair_strat.port is not None and pair_strat.port == old_pair_strat.port:
                break
        else:
            assert False, f"PairStrat not found with existing port after recovered pair_strat"

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    email_book_service_native_web_client.get_pair_strat_client(pair_strat.id))
                if strat_state_to_handle != StratState.StratState_SNOOZED:
                    if updated_pair_strat.is_partially_running and updated_pair_strat.is_executor_running:
                        break
                else:
                    # if strat_state to check is SNOOZED then after recovery is_executor_running will not get
                    # set since it is set only if SNOOZED is converted to READY
                    if updated_pair_strat.is_partially_running:
                        break
                time.sleep(1)
            except:  # no handling required: if error occurs retry
                pass
        else:
            assert False, (f"is_executor_running state must be True, found false, "
                           f"pair_strat_params: {old_pair_strat.pair_strat_params}")
    time.sleep(residual_wait_sec)

    active_pair_strat_id = None
    for pair_strat, strat_state_to_handle in pair_strat_n_strat_state_list:
        if strat_state_to_handle == StratState.StratState_ACTIVE:
            active_pair_strat_id = pair_strat.id
    recovered_active_strat = email_book_service_native_web_client.get_pair_strat_client(active_pair_strat_id)
    total_chore_count_for_each_side = 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = [executor.submit(_check_place_chores_post_pair_strat_n_executor_recovery, recovered_active_strat,
                                   deepcopy(last_barter_fixture_list), residual_wait_sec,
                                   total_chore_count_for_each_side)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


# todo: Currently broken - DB updates from log analyzer currently only updates strat_view
@pytest.mark.recovery1
def test_update_pair_strat_from_pair_strat_log_book(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_, symbol_overview_obj_list,
        market_depth_basemodel_list, last_barter_fixture_list,
        expected_chore_limits_, refresh_sec_update_fixture):
    """
    INFO: created strat and activates it with low max_single_leg_notional so consumable_notional becomes low and
    strat_limits.min_chore_notional is made higher than consumable_notional intentionally.
    After this pair_strat engine process is killed and since executor service is still up, triggers place chore
    which results in getting rejected as strat is found as Done because of
    consumable_notional < strat_limits.min_chore_notional and pair_start is tried to be updated as PAUSED but
    pair_strat engine is down so executor logs this as log to be handled by pair_strat log analyzer once
    pair_strat is up. pair_strat is restarted and then test checks state must be Done
    """

    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    # create pair_strat
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_strat, executor_web_client = create_n_activate_strat(
        leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, market_depth_basemodel_list)

    time.sleep(5)

    for _ in range(10):
        p_id: int = get_pid_from_port(email_book_service_native_web_client.port)
        if p_id is not None:
            os.kill(p_id, signal.SIGKILL)
            print(f"Killed process: {p_id}, port: {email_book_service_native_web_client.port}")
            break
        else:
            print("get_pid_from_port return None instead pid")
        time.sleep(2)
    else:
        assert False, f"Unexpected: Can't kill process - Can't find any pid from port {activated_pair_strat.port}"

    # updating pair_buy_side_bartering_brief.consumable_notional to be lower than min_tradable_notional
    strat_brief_ = executor_web_client.get_strat_brief_client(activated_pair_strat.id)
    strat_brief_.pair_buy_side_bartering_brief.consumable_notional = 10
    updated_strat_brief = executor_web_client.put_strat_brief_client(strat_brief_)
    assert updated_strat_brief == strat_brief_, \
        f"Mismatched strat_brief: expected: {strat_brief_}, updated: {updated_strat_brief}"

    total_chore_count_for_each_side = 1
    place_sanity_chores_for_executor(
        leg1_symbol, leg2_symbol, total_chore_count_for_each_side, last_barter_fixture_list,
        residual_wait_sec, executor_web_client, place_after_recovery=True,
        expect_no_chore=True)

    time.sleep(5)
    restart_phone_book()
    time.sleep(residual_wait_sec * 2)

    updated_pair_strat = email_book_service_native_web_client.get_pair_strat_client(activated_pair_strat.id)
    assert updated_pair_strat.strat_state == StratState.StratState_PAUSED, \
        (f"Mismatched: StratState must be PAUSE after update when phone_book was down, "
         f"found: {updated_pair_strat.strat_state}")


@pytest.mark.recovery
def test_recover_kill_switch_when_bartering_server_has_enabled(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_,
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

        pair_strat_port: int = email_book_service_native_web_client.port

        for _ in range(10):
            p_id: int = get_pid_from_port(pair_strat_port)
            if p_id is not None:
                os.kill(p_id, signal.SIGKILL)
                print(f"Killed process: {p_id}, port: {pair_strat_port}")
                break
            else:
                print("get_pid_from_port return None instead of pid")
            time.sleep(2)
        else:
            assert False, f"Unexpected: Can't kill process - Can't find any pid from port {pair_strat_port}"

        restart_phone_book()
        time.sleep(residual_wait_sec * 2)

        system_control = email_book_service_native_web_client.get_system_control_client(1)
        assert system_control.kill_switch, \
            ("Kill Switch must be triggered and enabled after restart according to test configuration but "
             "kill switch found False")

        # validating if bartering_link.trigger_kill_switch got called
        check_str = "Called BarteringLink.BarteringLink.trigger_kill_switch"
        portfolio_alerts = log_book_web_client.get_all_portfolio_alert_client()
        for alert in portfolio_alerts:
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
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_,
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

        pair_strat_port: int = email_book_service_native_web_client.port

        for _ in range(10):
            p_id: int = get_pid_from_port(pair_strat_port)
            if p_id is not None:
                os.kill(p_id, signal.SIGKILL)
                print(f"Killed process: {p_id}, port: {pair_strat_port}")
                break
            else:
                print("get_pid_from_port return None instead of pid")
            time.sleep(2)
        else:
            assert False, f"Unexpected: Can't kill process - Can't find any pid from port {pair_strat_port}"

        restart_phone_book()
        time.sleep(residual_wait_sec * 2)

        system_control = email_book_service_native_web_client.get_system_control_client(1)
        assert system_control.kill_switch, \
            "Kill Switch must be unchanged after restart but found changed, kill_switch found as False"

        # validating if bartering_link.trigger_kill_switch got called
        check_str = "Called BarteringLink.trigger_kill_switch"
        alert_fail_message = f"Can't find portfolio alert saying '{check_str}'"
        time.sleep(5)
        check_alert_str_in_portfolio_alert(check_str, alert_fail_message)

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
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_strat_status_,
        symbol_overview_obj_list, last_barter_fixture_list, max_loop_count_per_side,
        market_depth_basemodel_list, refresh_sec_update_fixture):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    max_loop_count_per_side = 1

    buy_symbol, sell_symbol, created_pair_strat, executor_web_client = (
        place_sanity_chores(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_, expected_strat_status_,
                            symbol_overview_obj_list, last_barter_fixture_list, market_depth_basemodel_list,
                            max_loop_count_per_side, refresh_sec_update_fixture))

    log_file_path = str(STRAT_EXECUTOR / "log" / f"street_book_{created_pair_strat.id}_logs_{frmt_date}.log")
    test_log = "Log added by test_cpp_app_recovery: ignore it"
    # putting this log line in executor log to use it later in test as a point from which new cpp_app's
    # released semaphore's log will get logged
    echo_cmd = f'echo "{test_log}" >> {log_file_path}'
    os.system(echo_cmd)

    # killing cpp app
    result = subprocess.run(
        [f'pgrep', '-f', f'mobile_book_executable.*executor_{created_pair_strat.id}_simulate_config'],
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
            (f"Can't find cpp process with strat_id: {created_pair_strat.id} running, "
             f"process check output: {result.stdout}")

    scripts_dir = STRAT_EXECUTOR / "scripts"
    # start file generator
    start_sh_file_path = scripts_dir / f"start_ps_id_{created_pair_strat.id}_md.sh"
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

    _check_place_chores_post_pair_strat_n_executor_recovery(
        created_pair_strat, last_barter_fixture_list, refresh_sec_update_fixture, total_chore_count_for_each_side=2)
