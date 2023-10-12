import sys

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



# update_portfolio_status_lock: asyncio.Lock = asyncio.Lock()
# def update_portfolio_status(overall_buy_notional: float | None, overall_sell_notional: float | None,
#                             portfolio_alerts: List[Alert] | None = None):
#     """
#     this function is generally invoked in extreme cases - best to not throw any further exceptions from here
#     otherwise the program will terminate - log critical error and continue
#     """
#     try:
#         kwargs = {}
#         act = False
#         if overall_buy_notional is not None:
#             kwargs.update(overall_buy_notional=overall_buy_notional)
#             act = True
#         if overall_sell_notional is not None:
#             kwargs.update(overall_sell_notional=overall_sell_notional)
#             act = True
#         if portfolio_alerts is not None:
#             act = True
#         if act:
#             with update_portfolio_status_lock:
#                 portfolio_status_list: List[
#                     PortfolioStatusBaseModel] = strat_manager_service_web_client_internal.get_all_portfolio_status_client()
#                 logging.debug(f"portfolio_status_list count: {len(portfolio_status_list)}")
#                 if 0 == len(portfolio_status_list):  # no portfolio status set yet - create one
#                     kwargs.update(kill_switch=False)
#                     kwargs.update(portfolio_alerts=portfolio_alerts)
#                     portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
#                     portfolio_status: PortfolioStatusBaseModel = \
#                         strat_manager_service_web_client_internal.create_portfolio_status_client(portfolio_status)
#                     logging.debug(f"created: portfolio_status: {portfolio_status}")
#                 elif 1 == len(portfolio_status_list):
#                     # TODO: we may need to copy non-updated fields form original model
#                     # (we should just update original model with new data (patch) and send)
#                     kwargs.update(kill_switch=portfolio_status_list[0].kill_switch)
#                     kwargs.update(_id=portfolio_status_list[0].id)
#                     if 'overall_buy_notional' not in kwargs:
#                         kwargs.update(overall_buy_notional=portfolio_status_list[0].overall_buy_notional)
#                     if 'overall_sell_notional' not in kwargs:
#                         kwargs.update(overall_sell_notional=portfolio_status_list[0].overall_sell_notional)
#                     if portfolio_status_list[0].portfolio_alerts is not None \
#                             and len(portfolio_status_list[0].portfolio_alerts) > 0:
#                         # TODO LAZY : maybe deep copy instead
#                         if portfolio_alerts is not None:
#                             portfolio_alerts += portfolio_status_list[0].portfolio_alerts
#                         else:
#                             portfolio_alerts = portfolio_status_list[0].portfolio_alerts
#                     kwargs.update(portfolio_alerts=portfolio_alerts)
#                     portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
#                     strat_manager_service_web_client_internal.put_portfolio_status_client(portfolio_status)
#                 else:
#                     logging.critical(
#                         "multiple portfolio limits entries not supported at this time! "
#                         "use swagger UI to delete redundant entries from DB and retry - "
#                         f"this blocks all alert form reaching UI!! alert being processed: {portfolio_alerts}")
#         # else not action required - no action to take - ignore and continue
#     except Exception as e:
#         logging.critical(
#             f"something serious is wrong: update_portfolio_status is throwing an exception!;;; exception: {e}",
#             exc_info=True)


def is_service_up(ignore_error: bool = False):
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            strat_manager_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as e:
        if not ignore_error:
            logging.exception("service_up test failed - tried get_all_portfolio_status_client (and maybe create);;;"
                              f"exception: {e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    rolling_max_order_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                                    max_gross_n_open_notional=2_400_000,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=eligible_brokers)
    return portfolio_limits_obj


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
    with open(generation_start_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write("shopt -s expand_aliases\n")
        fl.write("source ${HOME}/.bashrc\n")
        fl.write("cdm\n")  # create this as alias in your bashrc to cd into market data run.sh script dir
        fl.write("#export GDB_DEBUG=1  # uncomment if you want to run in debugger\n")
        fl.write(f"export PROJECT_NAME='{str(md_shell_env_data.project_name)}'\n")
        # for FX , exclude exch_code, SUBSCRIPTION_DATA instead export FX=1 with mode SO
        if md_shell_env_data.exch_code is not None and md_shell_env_data.subscription_data is not None:
            fl.write(f"export EXCHANGE_CODE={md_shell_env_data.exch_code}\n")
            fl.write(f'export SUBSCRIPTION_DATA="{jsonable_encoder(md_shell_env_data.subscription_data)}"\n')
        else:
            fl.write(f"export FX='1'\n")
            mode = "SO"     # overriding mode since fx is SO mode
        fl.write(f"export HOST='{str(md_shell_env_data.host)}'\n")
        fl.write(f"export PORT='{str(md_shell_env_data.port)}'\n")
        fl.write(f"export DB_NAME='{str(md_shell_env_data.db_name)}'\n")
        fl.write(f"export MODE='{str(mode)}'\n")
        fl.write("./run.sh\n")

