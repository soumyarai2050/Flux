import os.path
import subprocess

from FluxPythonUtils.scripts.utility_functions import get_pid_from_port
from tests.CodeGenProjects.addressbook.app.utility_test_functions import *


def test_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list, residual_wait_sec):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000

    created_pair_strat, executor_web_client = (
        create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                           expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                           market_depth_basemodel_list, top_of_book_list_))

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

        total_order_count_for_each_side = 2
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
                print("get_pid_n_status_from_port return None instead of Tuple")
            time.sleep(2)
        else:
            assert False, f"Unexpected: Can't kill executor - Can't find any pid from port {port}"

        time.sleep(residual_wait_sec)

        old_port = port
        for _ in range(10):
            pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
            if pair_strat.port is not None and pair_strat.port != old_port:
                break
        else:
            assert False, f"PairStrat not found with updated port of recovered executor"

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    strat_manager_service_native_web_client.get_pair_strat_client(pair_strat.id))
                if updated_pair_strat.is_executor_running:
                    break
                time.sleep(1)
            except:  # no handling required: if error occurs retry
                pass
        else:
            assert False, (f"is_executor_running state must be True, found false, "
                           f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
        time.sleep(residual_wait_sec)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

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


def test_pair_strat_n_executor_crash_recovery(
        static_data_, clean_and_set_limits, leg1_leg2_symbol_list, pair_strat_,
        expected_strat_limits_, expected_start_status_, symbol_overview_obj_list,
        top_of_book_list_, last_trade_fixture_list, market_depth_basemodel_list, residual_wait_sec):
    buy_symbol = leg1_leg2_symbol_list[0][0]
    sell_symbol = leg1_leg2_symbol_list[0][1]
    # making limits suitable for this test
    expected_strat_limits_.max_open_orders_per_side = 10
    expected_strat_limits_.residual_restriction.max_residual = 105000

    created_pair_strat, executor_web_client = (
    create_pre_order_test_requirements(buy_symbol, sell_symbol, pair_strat_, expected_strat_limits_,
                                       expected_start_status_, symbol_overview_obj_list, last_trade_fixture_list,
                                       market_depth_basemodel_list, top_of_book_list_))

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

        total_order_count_for_each_side = 1
        place_sanity_orders_for_executor(
            buy_symbol, sell_symbol, total_order_count_for_each_side, last_trade_fixture_list,
            top_of_book_list_, residual_wait_sec, executor_web_client)

        old_executor_port: int = executor_web_client.port
        pair_strat_port: int = strat_manager_service_native_web_client.port

        for port in [pair_strat_port, old_executor_port]:
            for _ in range(10):
                p_id: int = get_pid_from_port(port)
                if p_id is not None:
                    os.kill(p_id, signal.SIGKILL)
                    print(f"Killed process: {p_id}, port: {port}")
                    break
                else:
                    print("get_pid_n_status_from_port return None instead of Tuple")
                time.sleep(2)
            else:
                assert False, f"Unexpected: Can't kill process - Can't find any pid from port {port}"

        pair_strat_scripts_dir = (PurePath(__file__).parent.parent.parent.parent.parent / "Flux" /
                                  "CodeGenProjects" / "addressbook" / "scripts")
        pair_strat_process = subprocess.Popen(["python", "launch_beanie_fastapi.py"],
                                              cwd=pair_strat_scripts_dir)
        time.sleep(residual_wait_sec * 2)

        for _ in range(20):
            pair_strat = strat_manager_service_native_web_client.get_pair_strat_client(created_pair_strat.id)
            if pair_strat.port is not None and pair_strat.port != old_executor_port:
                break
        else:
            assert False, f"PairStrat not found with updated port of recovered executor"

        for _ in range(30):
            # checking is_executor_running of executor
            try:
                updated_pair_strat = (
                    strat_manager_service_native_web_client.get_pair_strat_client(pair_strat.id))
                if updated_pair_strat.is_executor_running:
                    break
                time.sleep(1)
            except:  # no handling required: if error occurs retry
                pass
        else:
            assert False, (f"is_executor_running state must be True, found false, "
                           f"buy_symbol: {buy_symbol}, sell_symbol: {sell_symbol}")
        time.sleep(residual_wait_sec)

    except AssertionError as e:
        raise AssertionError(e)
    except Exception as e:
        print(f"Some Error Occurred: exception: {e}, "
              f"traceback: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
        raise Exception(e)
    finally:
        YAMLConfigurationManager.update_yaml_configurations(config_dict_str, str(config_file_path))

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

