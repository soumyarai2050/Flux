import os.path
import subprocess
import concurrent.futures
import pytest

from FluxPythonUtils.scripts.utility_functions import get_pid_from_port
from tests.CodeGenProjects.addressbook.app.utility_test_functions import *


def _test_executor_crash_recovery(
        buy_symbol, sell_symbol, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list,
        strat_state_to_handle, refresh_sec):
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

    if strat_state_to_handle != StratState.StratState_ACTIVE:
        created_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(PairStratBaseModel(_id=created_pair_strat.id, strat_state=strat_state_to_handle),
                             by_alias=True, exclude_none=True))
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

        executor_web_client.trade_simulator_reload_config_query_client()

        if strat_state_to_handle == StratState.StratState_ACTIVE:
            total_order_count_for_each_side = 1
            place_sanity_orders_for_executor(
                buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
                top_of_book_list_, residual_wait_sec, executor_web_client)
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
            pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
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
                    strat_manager_service_native_web_client.get_pair_strat_client(pair_strat.id))
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
        pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
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
        new_executor_web_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(
            updated_pair_strat.host, updated_pair_strat.port)
        try:
            # updating yaml_configs according to this test
            for symbol in config_dict["symbol_configs"]:
                config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
                config_dict["symbol_configs"][symbol]["fill_percent"] = 50
            YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

            new_executor_web_client.trade_simulator_reload_config_query_client()

            # To update tob without triggering any order
            run_buy_top_of_book(buy_symbol, sell_symbol, new_executor_web_client,
                                top_of_book_list_[0], avoid_order_trigger=True)

            total_order_count_for_each_side = 1
            place_sanity_orders_for_executor(
                buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
                top_of_book_list_, residual_wait_sec, new_executor_web_client, place_after_recovery=True)
        except AssertionError as e:
            raise AssertionError(e)
        except Exception as e:
            print(f"Some Error Occurred: exception: {e}, "
                  f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
            raise Exception(e)
        finally:
            YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    symbols_n_strat_state_list = []
    strat_state_list = [StratState.StratState_ACTIVE, StratState.StratState_READY, StratState.StratState_PAUSED,
                        StratState.StratState_SNOOZED, StratState.StratState_ERROR, StratState.StratState_DONE]
    # strat_state_list = [StratState.StratState_READY]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_test_executor_crash_recovery, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list), deepcopy(top_of_book_list_),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   handle_strat_state, refresh_sec_update_fixture)
                   for buy_symbol, sell_symbol, handle_strat_state in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _activate_pair_strat_n_place_sanity_orders(
        buy_symbol, sell_symbol, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list,
        strat_state_to_handle, refresh_sec):
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec
    residual_wait_sec = 4 * refresh_sec

    created_pair_strat, executor_web_client = (
    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list, top_of_book_list_))

    if strat_state_to_handle != StratState.StratState_ACTIVE:
        created_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(PairStratBaseModel(_id=created_pair_strat.id, strat_state=strat_state_to_handle),
                             by_alias=True, exclude_none=True))
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

        executor_web_client.trade_simulator_reload_config_query_client()

        if strat_state_to_handle == StratState.StratState_ACTIVE:
            total_order_count_for_each_side_ = 1
            place_sanity_orders_for_executor(
                buy_symbol, sell_symbol, total_order_count_for_each_side_, last_trade_fixture_list,
                top_of_book_list_, residual_wait_sec, executor_web_client)
    except AssertionError as e_:
        raise AssertionError(e_)
    except Exception as e_:
        print(f"Some Error Occurred: exception: {e_}, "
              f"traceback: {''.join(traceback.format_exception(None, e_, e_.__traceback__))}")
        raise Exception(e_)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

    return created_pair_strat, executor_web_client, strat_state_to_handle


def _check_place_orders_post_pair_strat_n_executor_recovery(
        updated_pair_strat: PairStratBaseModel,
        top_of_book_list_, last_trade_fixture_list, refresh_sec):
    residual_wait_sec = 4 * refresh_sec
    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{updated_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    buy_symbol = updated_pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    sell_symbol = updated_pair_strat.pair_strat_params.strat_leg2.sec.sec_id
    new_executor_web_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(
        updated_pair_strat.host, updated_pair_strat.port)
    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        new_executor_web_client.trade_simulator_reload_config_query_client()

        # To update tob without triggering any order
        run_buy_top_of_book(buy_symbol, sell_symbol, new_executor_web_client,
                            top_of_book_list_[0], avoid_order_trigger=True)

        total_order_count_for_each_side = 2
        place_sanity_orders_for_executor(
            buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
            top_of_book_list_, residual_wait_sec, new_executor_web_client, place_after_recovery=True)
    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))


@pytest.mark.nightly
def test_pair_strat_n_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    activated_strat_n_executor_http_client_tuple_list: List[Tuple[PairStrat, StratExecutorServiceHttpClient]] = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_strat_state_list = []
    strat_state_list = [StratState.StratState_ACTIVE, StratState.StratState_READY, StratState.StratState_PAUSED,
                        StratState.StratState_SNOOZED, StratState.StratState_ERROR, StratState.StratState_DONE]
    # strat_state_list = [StratState.StratState_READY]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_activate_pair_strat_n_place_sanity_orders, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list), deepcopy(top_of_book_list_),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   strat_state_to_handle, refresh_sec_update_fixture)
                   for buy_symbol, sell_symbol, strat_state_to_handle in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            activated_strat_n_executor_http_client_tuple_list.append(future.result())

    port_list = [strat_manager_service_native_web_client.port]
    pair_strat_n_strat_state_list = []

    for activated_strat, _, strat_state_to_handle in activated_strat_n_executor_http_client_tuple_list:
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

    pair_strat_scripts_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "Flux" /
                              "CodeGenProjects" / "addressbook" / "scripts")
    pair_strat_process = subprocess.Popen(["python", "launch_beanie_fastapi.py"],
                                          cwd=pair_strat_scripts_dir)
    time.sleep(residual_wait_sec * 2)

    updated_pair_strat_list: List[PairStratBaseModel] = []
    for old_pair_strat_, strat_state_to_handle in pair_strat_n_strat_state_list:
        for _ in range(20):
            pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(old_pair_strat_.id)
            if pair_strat.port is not None and pair_strat.port != old_pair_strat_.port:
                break
            time.sleep(1)
        else:
            assert False, f"PairStrat not found with updated port of recovered executor"

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    strat_manager_service_native_web_client.get_pair_strat_client(pair_strat.id))
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
        updated_pair_strat_list.append(updated_pair_strat)
    time.sleep(residual_wait_sec)

    active_pair_strat_id = None
    for pair_strat, strat_state_to_handle in pair_strat_n_strat_state_list:
        if strat_state_to_handle == StratState.StratState_ACTIVE:
            active_pair_strat_id = pair_strat.id
    recovered_active_strat = strat_manager_service_native_web_client.get_pair_strat_client(active_pair_strat_id)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = [executor.submit(_check_place_orders_post_pair_strat_n_executor_recovery, recovered_active_strat,
                                   deepcopy(top_of_book_list_),
                                   deepcopy(last_trade_fixture_list), residual_wait_sec)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


def _test_post_pair_strat_crash_recovery(updated_pair_strat: PairStratBaseModel, executor_web_client,
        top_of_book_list_, last_trade_fixture_list, refresh_sec):
    residual_wait_sec = 4 * refresh_sec

    config_file_path = STRAT_EXECUTOR / "data" / f"executor_{updated_pair_strat.id}_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    buy_symbol = updated_pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    sell_symbol = updated_pair_strat.pair_strat_params.strat_leg2.sec.sec_id
    recovered_portfolio_status: PortfolioStatusBaseModel = (
        strat_manager_service_native_web_client.get_portfolio_status_client(1))

    try:
        # updating yaml_configs according to this test
        for symbol in config_dict["symbol_configs"]:
            config_dict["symbol_configs"][symbol]["simulate_reverse_path"] = True
            config_dict["symbol_configs"][symbol]["fill_percent"] = 50
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        executor_web_client.trade_simulator_reload_config_query_client()

        total_order_count_for_each_side = 2
        place_sanity_orders_for_executor(
            buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
            top_of_book_list_, residual_wait_sec, executor_web_client, place_after_recovery=True)

        new_portfolio_status: PortfolioStatusBaseModel = (
            strat_manager_service_native_web_client.get_portfolio_status_client(1))

        assert recovered_portfolio_status != new_portfolio_status, \
            ("Unexpected: portfolio must have got updated after pair_strat recover, "
             f"old_portfolio_status {recovered_portfolio_status}, "
             f"new_portfolio_status {new_portfolio_status}")

        done_pair_strat = strat_manager_service_native_web_client.patch_pair_strat_client(
            jsonable_encoder(PairStratBaseModel(_id=updated_pair_strat.id, strat_state=StratState.StratState_DONE),
                             by_alias=True, exclude_none=True))

        try:
            strat_manager_service_native_web_client.delete_pair_strat_client(done_pair_strat.id)
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


@pytest.mark.nightly
def test_pair_strat_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list, refresh_sec_update_fixture):
    activated_strat_n_executor_http_client_tuple_list: List[Tuple[PairStrat, StratExecutorServiceHttpClient]] = []
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture
    symbols_n_strat_state_list = []
    strat_state_list = [StratState.StratState_ACTIVE, StratState.StratState_READY, StratState.StratState_PAUSED,
                        StratState.StratState_SNOOZED, StratState.StratState_ERROR, StratState.StratState_DONE]
    # strat_state_list = [StratState.StratState_READY]
    for index, symbol_tuple in enumerate(leg1_leg2_symbol_list[:len(strat_state_list)]):
        symbols_n_strat_state_list.append((symbol_tuple[0], symbol_tuple[1], strat_state_list[index]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols_n_strat_state_list)) as executor:
        results = [executor.submit(_activate_pair_strat_n_place_sanity_orders, buy_symbol, sell_symbol,
                                   deepcopy(pair_strat_),
                                   deepcopy(expected_strat_limits_), deepcopy(expected_start_status_),
                                   deepcopy(symbol_overview_obj_list), deepcopy(top_of_book_list_),
                                   deepcopy(last_trade_fixture_list), deepcopy(market_depth_basemodel_list),
                                   strat_state_to_handle, refresh_sec_update_fixture)
                   for buy_symbol, sell_symbol, strat_state_to_handle in symbols_n_strat_state_list]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())

            activated_strat_n_executor_http_client_tuple_list.append(future.result())

    pair_strat_n_strat_state_list = []

    for activated_strat, _, strat_state_to_handle in activated_strat_n_executor_http_client_tuple_list:
        pair_strat_n_strat_state_list.append((activated_strat, strat_state_to_handle))

    pair_strat_port: int = strat_manager_service_native_web_client.port

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

    pair_strat_scripts_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "Flux" /
                              "CodeGenProjects" / "addressbook" / "scripts")
    pair_strat_process = subprocess.Popen(["python", "launch_beanie_fastapi.py"],
                                          cwd=pair_strat_scripts_dir)
    time.sleep(residual_wait_sec * 2)

    for old_pair_strat, strat_state_to_handle in pair_strat_n_strat_state_list:
        for _ in range(20):
            pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(old_pair_strat.id)
            if pair_strat.port is not None and pair_strat.port == old_pair_strat.port:
                break
        else:
            assert False, f"PairStrat not found with existing port after recovered pair_strat"

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    strat_manager_service_native_web_client.get_pair_strat_client(pair_strat.id))
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
    recovered_active_strat = strat_manager_service_native_web_client.get_pair_strat_client(active_pair_strat_id)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = [executor.submit(_check_place_orders_post_pair_strat_n_executor_recovery, recovered_active_strat,
                                   deepcopy(top_of_book_list_),
                                   deepcopy(last_trade_fixture_list), residual_wait_sec)]

        for future in concurrent.futures.as_completed(results):
            if future.exception() is not None:
                raise Exception(future.exception())


@pytest.mark.nightly
def test_update_pair_strat_from_pair_strat_log_analyzer(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, market_depth_basemodel_list, last_trade_fixture_list,
        expected_order_limits_, refresh_sec_update_fixture):
    """
    INFO: created strat and activates it with low max_single_leg_notional so consumable_notional becomes low and
    order_limits.min_order_notional is made higher than consumable_notional intentionally.
    After this pair_strat engine process is killed and since executor service is still up, triggers place order
    which results in getting rejected as strat is found as Done because of consumable_notional < ol.min_order_notional
    and pair_start is tried to be updated as Done but pair_strat engine is down so executor logs this
    as log to be handled by pair_strat log analyzer once pair_strat is up. pair_strat is restarted and
    then test checks state must be Done
    """

    leg1_symbol = leg1_leg2_symbol_list[0][0]
    leg2_symbol = leg1_leg2_symbol_list[0][1]

    expected_order_limits_.min_order_notional = 1000
    expected_order_limits_.id = 1
    strat_manager_service_native_web_client.put_order_limits_client(expected_order_limits_)

    # create pair_strat
    expected_strat_limits_.max_single_leg_notional = 100
    expected_strat_limits_.residual_restriction.residual_mark_seconds = 2 * refresh_sec_update_fixture
    residual_wait_sec = 4 * refresh_sec_update_fixture

    activated_pair_strat, executor_web_client = create_n_activate_strat(
        leg1_symbol, leg2_symbol, pair_strat_, expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, top_of_book_list_, market_depth_basemodel_list)

    time.sleep(5)

    for _ in range(10):
        p_id: int = get_pid_from_port(strat_manager_service_native_web_client.port)
        if p_id is not None:
            os.kill(p_id, signal.SIGKILL)
            print(f"Killed process: {p_id}, port: {activated_pair_strat.port}")
            break
        else:
            print("get_pid_from_port return None instead pid")
        time.sleep(2)
    else:
        assert False, f"Unexpected: Can't kill process - Can't find any pid from port {activated_pair_strat.port}"

    total_order_count_for_each_side = 1
    place_sanity_orders_for_executor(
        leg1_symbol, leg2_symbol, total_order_count_for_each_side, last_trade_fixture_list,
        top_of_book_list_, residual_wait_sec, executor_web_client, place_after_recovery=True,
        expect_no_order=True)

    time.sleep(5)
    pair_strat_scripts_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "Flux" /
                              "CodeGenProjects" / "addressbook" / "scripts")
    pair_strat_process = subprocess.Popen(["python", "launch_beanie_fastapi.py"],
                                          cwd=pair_strat_scripts_dir)
    time.sleep(residual_wait_sec * 2)

    updated_pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(activated_pair_strat.id)
    assert updated_pair_strat.strat_state == StratState.StratState_DONE, \
        (f"Mismatched: StratState must be Done after update when addressbook was down, "
         f"found: {updated_pair_strat.strat_state}")


@pytest.mark.nightly
def test_recover_kill_switch_when_trading_server_has_enabled(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, last_trade_fixture_list,
        market_depth_basemodel_list, top_of_book_list_, refresh_sec_update_fixture):

    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    residual_wait_sec = 4 * refresh_sec_update_fixture
    try:
        # updating yaml_configs according to this test
        config_dict["is_kill_switch_enabled"] = True
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        strat_manager_service_native_web_client.log_simulator_reload_config_query_client()

        pair_strat_port: int = strat_manager_service_native_web_client.port

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

        pair_strat_scripts_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "Flux" /
                                  "CodeGenProjects" / "addressbook" / "scripts")
        pair_strat_process = subprocess.Popen(["python", "launch_beanie_fastapi.py"],
                                              cwd=pair_strat_scripts_dir)
        time.sleep(residual_wait_sec * 2)

        system_control = strat_manager_service_native_web_client.get_system_control_client(1)
        assert system_control.kill_switch, \
            ("Kill Switch must be triggered and enabled after restart according to test configuration but "
             "kill switch found False")

        # validating if trading_link.trigger_kill_switch got called
        check_str = "Called TradingLink.TradingLink.trigger_kill_switch"
        portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
        for alert in portfolio_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                assert False, \
                    ("TradingLink.trigger_kill_switch must not have been triggered when kill switch is enabled in"
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
        strat_manager_service_native_web_client.log_simulator_reload_config_query_client()


@pytest.mark.nightly
def test_recover_kill_switch_when_trading_server_has_disabled(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_,
        symbol_overview_obj_list, last_trade_fixture_list,
        market_depth_basemodel_list, top_of_book_list_, refresh_sec_update_fixture):

    residual_wait_sec = 4 * refresh_sec_update_fixture
    system_control = SystemControlBaseModel(_id=1, kill_switch=True)
    strat_manager_service_native_web_client.patch_system_control_client(
        jsonable_encoder(system_control, by_alias=True, exclude_none=True))

    config_file_path = STRAT_EXECUTOR / "data" / f"kill_switch_simulate_config.yaml"
    config_dict: Dict = YAMLConfigurationManager.load_yaml_configurations(config_file_path)
    config_dict_str = YAMLConfigurationManager.load_yaml_configurations(config_file_path, load_as_str=True)

    try:
        # updating yaml_configs according to this test
        config_dict["is_kill_switch_enabled"] = False
        YAMLConfigurationManager.update_yaml_configurations(config_dict, str(config_file_path))

        # updating simulator's configs
        strat_manager_service_native_web_client.log_simulator_reload_config_query_client()

        pair_strat_port: int = strat_manager_service_native_web_client.port

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

        pair_strat_scripts_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "Flux" /
                                  "CodeGenProjects" / "addressbook" / "scripts")
        pair_strat_process = subprocess.Popen(["python", "launch_beanie_fastapi.py"],
                                              cwd=pair_strat_scripts_dir)
        time.sleep(residual_wait_sec * 2)

        system_control = strat_manager_service_native_web_client.get_system_control_client(1)
        assert system_control.kill_switch, \
            "Kill Switch must be unchanged after restart but found changed, kill_switch found as False"

        # validating if trading_link.trigger_kill_switch got called
        check_str = "Called TradingLink.trigger_kill_switch"
        portfolio_alert = log_analyzer_web_client.get_portfolio_alert_client(1)
        for alert in portfolio_alert.alerts:
            if re.search(check_str, alert.alert_brief):
                break
        else:
            assert False, f"Can't find portfolio alert saying '{check_str}'"

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))
        # updating simulator's configs
        strat_manager_service_native_web_client.log_simulator_reload_config_query_client()
