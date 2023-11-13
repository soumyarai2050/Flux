import sys
from threading import Lock

from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_filter
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_client import \
    StratManagerServiceHttpClient
from FluxPythonUtils.scripts.utility_functions import (
    YAMLConfigurationManager, get_symbol_side_key, except_n_log_alert)

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
ps_host, ps_port = (config_yaml_dict.get("server_host"),
                    parse_to_int(config_yaml_dict.get("main_server_beanie_port")))

strat_manager_service_http_client = \
    StratManagerServiceHttpClient.set_or_get_if_instance_exists(ps_host, ps_port)

# loading strat_executor's project's config.yaml
ROOT_DIR = PurePath(__file__).parent.parent.parent
STRAT_EXECUTOR_DATA_DIR = ROOT_DIR / 'strat_executor' / 'data'

strat_executor_config_yaml_path: PurePath = STRAT_EXECUTOR_DATA_DIR / f"config.yaml"
strat_executor_config_yaml_dict = (
    YAMLConfigurationManager.load_yaml_configurations(str(strat_executor_config_yaml_path)))

update_portfolio_status_lock: Lock = Lock()


def patch_portfolio_status(overall_buy_notional: float | None, overall_sell_notional: float | None) -> None:
    """
    this function is generally invoked in extreme cases - best to not throw any further exceptions from here
    otherwise the program will terminate - log critical error and continue
    """
    try:
        kwargs = {}
        act = False
        if overall_buy_notional is not None:
            kwargs.update(overall_buy_notional=overall_buy_notional)
            act = True
        if overall_sell_notional is not None:
            kwargs.update(overall_sell_notional=overall_sell_notional)
            act = True
        if act:
            with update_portfolio_status_lock:
                portfolio_status_list: List[PortfolioStatusBaseModel] = \
                    strat_manager_service_http_client.get_all_portfolio_status_client()
                logging.debug(f"portfolio_status_list count: {len(portfolio_status_list)}")
                if 0 == len(portfolio_status_list):  # no portfolio status set yet
                    logging.error(f"patch_portfolio_status failed. no portfolio status obj found;;;"
                                  f"update request: {kwargs}")
                elif 1 == len(portfolio_status_list):
                    kwargs.update(_id=portfolio_status_list[0].id)
                    updated_portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
                    strat_manager_service_http_client.patch_portfolio_status_client(
                        jsonable_encoder(updated_portfolio_status, by_alias=True, exclude_none=True))
                else:
                    logging.critical(
                        "multiple portfolio status entries not supported at this time! "
                        "use swagger UI to delete redundant entries from DB and retry."
                        f"this blocks all update requests. update request being processed: {kwargs}")
        # else not action required - no action to take - ignore and continue
    except Exception as e:
        logging.critical(
            f"something serious is wrong: update_portfolio_status is throwing an exception!;;; exception: {e}",
            exc_info=True)


def is_service_up(ignore_error: bool = False, is_server: bool = False):
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            strat_manager_service_http_client.get_all_ui_layout_client())
        return True
    except Exception as e:
        if not ignore_error:
            logging.exception("service_up test failed - tried get_all_ui_layout_client (and maybe create);;;"
                              f"exception: {e}")
        # else not required - silently ignore error is true
        return False


@except_n_log_alert()
def create_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    portfolio_limits_obj: PortfolioLimits = get_new_portfolio_limits(eligible_brokers)
    portfolio_limits_base_model_obj: PortfolioLimitsBaseModel = \
        PortfolioLimitsBaseModel(**jsonable_encoder(portfolio_limits_obj, by_alias=True, exclude_none=True))
    created_portfolio_limits: PortfolioLimitsBaseModel = \
        strat_manager_service_http_client.create_portfolio_limits_client(portfolio_limits_base_model_obj)
    logging.info(f"created portfolio_limits;;;{created_portfolio_limits}")
    return created_portfolio_limits


@except_n_log_alert()
def get_portfolio_limits() -> PortfolioLimitsBaseModel | None:
    portfolio_limits_list: List[PortfolioLimitsBaseModel] = \
        strat_manager_service_http_client.get_all_portfolio_limits_client()
    if 0 == len(portfolio_limits_list):
        return None
    elif 1 < len(portfolio_limits_list):
        err_str_ = f"multiple: {len(portfolio_limits_list)} portfolio_limits entries not supported at this time! " \
                   f"use swagger UI to delete redundant entries: {portfolio_limits_list} from DB and retry"
        raise Exception(err_str_)
    else:
        return portfolio_limits_list[0]


@except_n_log_alert()
def get_order_limits() -> OrderLimitsBaseModel | None:
    order_limits_list: List[OrderLimitsBaseModel] = \
        strat_manager_service_http_client.get_all_order_limits_client()
    if 0 == len(order_limits_list):
        return None
    elif 1 < len(order_limits_list):
        err_str_ = f"multiple: {len(order_limits_list)} order_limits entries not supported at this time! " \
                   f"use swagger UI to delete redundant entries: {order_limits_list} from DB and retry"
        raise Exception(err_str_)
    else:
        return order_limits_list[0]


def get_new_portfolio_status() -> PortfolioStatus:
    portfolio_status: PortfolioStatus = PortfolioStatus(_id=1, kill_switch=False, overall_buy_notional=0,
                                                        overall_sell_notional=0,
                                                        overall_buy_fill_notional=0,
                                                        overall_sell_fill_notional=0)
    return portfolio_status


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimits:
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    rolling_max_order_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimits(_id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                           max_gross_n_open_notional=2_400_000,
                                           rolling_max_order_count=rolling_max_order_count,
                                           rolling_max_reject_count=rolling_max_reject_count,
                                           eligible_brokers=eligible_brokers,
                                           eligible_brokers_update_count=0)
    return portfolio_limits_obj


def get_new_order_limits() -> OrderLimits:
    order_limits_obj: OrderLimits = OrderLimits(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                                                max_order_qty=500, min_order_notional=100,
                                                max_order_notional=90_000)
    return order_limits_obj


def get_match_level(pair_strat: PairStrat, sec_id: str, side: Side) -> int:
    match_level: int = 6
    if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == sec_id:
        if pair_strat.pair_strat_params.strat_leg1.side == side:
            match_level = 1
        else:
            match_level = 2
    elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == sec_id:
        if pair_strat.pair_strat_params.strat_leg2.side == side:
            match_level = 1
        else:
            match_level = 2
    return match_level  # no match


# caller must take any locks as required for any read-write consistency - function operates without lock
async def get_strats_from_symbol_n_side(sec_id: str, side: Side) -> Tuple[List[PairStrat], List[PairStrat]]:
    from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_http_routes import \
        underlying_read_pair_strat_http
    read_pair_strat_filter = get_pair_strat_filter(sec_id)
    pair_strats: List[PairStrat] = await underlying_read_pair_strat_http(read_pair_strat_filter)

    match_level_1_pair_strats: List[PairStrat] = list()
    match_level_2_pair_strats: List[PairStrat] = list()
    for pair_strat in pair_strats:
        match_level: int = get_match_level(pair_strat, sec_id, side)
        if match_level == 1:
            match_level_1_pair_strats.append(pair_strat)
        elif match_level == 2:
            match_level_2_pair_strats.append(pair_strat)
        # else not a match ignore
    return match_level_1_pair_strats, match_level_2_pair_strats


async def get_single_exact_match_strat_from_symbol_n_side(sec_id: str, side: Side) -> PairStrat | None:
    match_level_1_pair_strats, match_level_2_pair_strats = await get_strats_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
        logging.error(f"error: No viable pair_strat for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
        return
    else:
        pair_strat: PairStrat | None = None
        if len(match_level_1_pair_strats) == 1:
            pair_strat = match_level_1_pair_strats[0]
        else:
            logging.error(f"error: processing {get_symbol_side_key([(sec_id, side)])} pair_strat should be "
                          f"found only one in match_lvl_1, found {match_level_1_pair_strats}")
        if pair_strat is None:
            if len(match_level_2_pair_strats) == 1:
                pair_strat = match_level_2_pair_strats[0]
                logging.error(f"error: pair_strat should be found in level 1 only, symbol_side_key: "
                              f"{get_symbol_side_key([(sec_id, side)])}")
            else:
                logging.error(
                    f"error: multiple ongoing pair strats matching symbol_side_key: "
                    f"{get_symbol_side_key([(sec_id, side)])} found, one "
                    f"match expected, found: {len(match_level_2_pair_strats)}")
        return pair_strat


class MDShellEnvData(BaseModel):
    subscription_data: List[Tuple[str, str]] | None = None
    host: str
    port: int
    db_name: str
    project_name: str
    exch_code: str | None


def create_md_shell_script(md_shell_env_data: MDShellEnvData, generation_start_file_path: str, mode: str):
    script_file_name = os.path.basename(generation_start_file_path)
    log_file_path = PurePath(generation_start_file_path).parent.parent / "log" / f"{script_file_name}.log"
    with open(generation_start_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write(f"LOG_FILE_PATH={log_file_path}\n")
        fl.write("echo Log_file_path: ${LOG_FILE_PATH}\n")
        fl.write("shopt -s expand_aliases >>${LOG_FILE_PATH} 2>&1\n")
        fl.write("source ${HOME}/.bashrc\n")
        # create this as alias in your bashrc to cd into market data run.sh script dir
        fl.write("cdm >>${LOG_FILE_PATH} 2>&1\n")
        fl.write("#export GDB_DEBUG=1  # uncomment if you want the process to start in GDB\n")
        fl.write(f"export PROJECT_NAME='{str(md_shell_env_data.project_name)}'\n")
        # for FX , exclude exch_code, SUBSCRIPTION_DATA instead export FX=1 with mode SO
        if md_shell_env_data.exch_code is not None and md_shell_env_data.subscription_data is not None:
            fl.write(f"export EXCHANGE_CODE={md_shell_env_data.exch_code}\n")
            fl.write(f'export SUBSCRIPTION_DATA="{jsonable_encoder(md_shell_env_data.subscription_data)}"\n')
        else:
            fl.write(f"export FX=1\n")
            mode = "SO"  # overriding mode since fx is SO mode
        fl.write(f"export HOST={str(md_shell_env_data.host)}\n")
        fl.write(f"export PORT={str(md_shell_env_data.port)}\n")
        fl.write(f"export DB_NAME={str(md_shell_env_data.db_name)}\n")
        fl.write(f"export MODE={str(mode)}\n")
        fl.write('echo GDB_DEBUG: "${GDB_DEBUG}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo PROJECT_NAME: "${PROJECT_NAME}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo EXCHANGE_CODE: "${EXCHANGE_CODE}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo SUBSCRIPTION_DATA: "${SUBSCRIPTION_DATA}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo HOST: "${HOST}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo PORT: "${PORT}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo DB_NAME: "${DB_NAME}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo MODE: "${MODE}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('echo triggering run from "${PWD}" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('if [ -z "$GDB_DEBUG" ] ; then\n')
        fl.write("        ./run.sh >>${LOG_FILE_PATH} 2>&1\n")
        fl.write("else\n")
        fl.write("        ./run.sh\n")
        fl.write("fi\n")
