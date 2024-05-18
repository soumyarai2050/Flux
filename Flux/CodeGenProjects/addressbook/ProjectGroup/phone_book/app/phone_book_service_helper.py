import inspect

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.aggregate import (
    get_ongoing_or_all_pair_strats_by_sec_id, get_ongoing_pair_strat_filter)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_client import \
    EmailBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    get_field_seperator_pattern, get_key_val_seperator_pattern, get_pattern_for_pair_strat_db_updates, UpdateType)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import StratViewBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_key)

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
ps_host, ps_port = (config_yaml_dict.get("server_host"),
                    parse_to_int(config_yaml_dict.get("main_server_beanie_port")))

email_book_service_http_client: EmailBookServiceHttpClient = \
    EmailBookServiceHttpClient.set_or_get_if_instance_exists(ps_host, ps_port)

# loading street_book's project's config.yaml
ROOT_DIR = PurePath(__file__).parent.parent.parent
STRAT_EXECUTOR_DATA_DIR = ROOT_DIR / 'street_book' / 'data'

street_book_config_yaml_path: PurePath = STRAT_EXECUTOR_DATA_DIR / f"config.yaml"
street_book_config_yaml_dict = (
    YAMLConfigurationManager.load_yaml_configurations(str(street_book_config_yaml_path)))

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
                    email_book_service_http_client.get_all_portfolio_status_client()
                logging.debug(f"portfolio_status_list count: {len(portfolio_status_list)}")
                if 0 == len(portfolio_status_list):  # no portfolio status set yet
                    logging.error(f"patch_portfolio_status failed. no portfolio status obj found;;;"
                                  f"update request: {kwargs}")
                elif 1 == len(portfolio_status_list):
                    kwargs.update(_id=portfolio_status_list[0].id)
                    updated_portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
                    email_book_service_http_client.patch_portfolio_status_client(
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
            email_book_service_http_client.get_all_ui_layout_client())
        return True
    except Exception as e:
        if not ignore_error:
            logging.exception("service_up test failed - tried get_all_ui_layout_client (and maybe create);;;"
                              f"exception: {e}")
        # else not required - silently ignore error is true
        return False


def is_ongoing_strat(pair_strat: PairStrat | PairStratBaseModel) -> bool:
    return pair_strat.strat_state not in [StratState.StratState_UNSPECIFIED,
                                          StratState.StratState_READY,
                                          StratState.StratState_DONE,
                                          StratState.StratState_SNOOZED]


def get_new_portfolio_status() -> PortfolioStatus:
    portfolio_status: PortfolioStatus = PortfolioStatus(_id=1, overall_buy_notional=0,
                                                        overall_sell_notional=0,
                                                        overall_buy_fill_notional=0,
                                                        overall_sell_fill_notional=0,
                                                        open_chores=0)
    return portfolio_status


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimits:
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    rolling_max_chore_count = RollingMaxChoreCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxChoreCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimits(_id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                           max_gross_n_open_notional=2_400_000,
                                           rolling_max_chore_count=rolling_max_chore_count,
                                           rolling_max_reject_count=rolling_max_reject_count,
                                           eligible_brokers=eligible_brokers,
                                           eligible_brokers_update_count=0)
    return portfolio_limits_obj


def get_new_chore_limits() -> ChoreLimits:
    ord_limit_obj: ChoreLimits = ChoreLimits(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                                             max_chore_qty=500, max_chore_notional=90_000)
    return ord_limit_obj


def get_new_strat_view_obj(obj_id: int) -> StratViewBaseModel:
    strat_view_obj: StratViewBaseModel = StratViewBaseModel(_id=obj_id, strat_alert_count=0)
    return strat_view_obj


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
async def get_ongoing_strats_from_symbol_n_side(sec_id: str, side: Side) -> Tuple[List[PairStrat], List[PairStrat]]:
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_routes import \
        underlying_read_pair_strat_http
    read_pair_strat_filter = get_ongoing_pair_strat_filter(sec_id)
    pair_strats: List[PairStrat] = await underlying_read_pair_strat_http(read_pair_strat_filter)

    match_level_1_pair_strats: List[PairStrat] = []
    match_level_2_pair_strats: List[PairStrat] = []
    for pair_strat in pair_strats:
        match_level: int = get_match_level(pair_strat, sec_id, side)
        if match_level == 1:
            match_level_1_pair_strats.append(pair_strat)
        elif match_level == 2:
            match_level_2_pair_strats.append(pair_strat)
        # else not a match ignore
    return match_level_1_pair_strats, match_level_2_pair_strats


async def get_single_exact_match_strat_from_symbol_n_side(sec_id: str, side: Side) -> PairStrat | None:
    match_level_1_pair_strats, match_level_2_pair_strats = await get_ongoing_strats_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
        logging.info(f"No viable pair_strat for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
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


def get_strat_key_from_pair_strat(pair_strat: PairStrat | PairStratBaseModel):
    strat_key = f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id}-" \
                f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}-" \
                f"{pair_strat.pair_strat_params.strat_leg1.side.value}-{pair_strat.id}"
    return strat_key


def get_id_from_strat_key(unloaded_strat_key: str) -> int:
    parts: List[str] = (unloaded_strat_key.split("-"))
    return parse_to_int(parts[-1])


def pair_strat_client_call_log_str(pydantic_basemodel_type: Type | None, client_callable: Callable,
                                   update_type: UpdateType | None = None, **kwargs) -> str:
    if update_type is None:
        update_type = UpdateType.JOURNAL_TYPE

    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    pair_strat_db_pattern: str = get_pattern_for_pair_strat_db_updates()
    log_str = (f"{pair_strat_db_pattern}{pydantic_basemodel_type.__name__}{fld_sep}{update_type.value}"
               f"{fld_sep}{client_callable.__name__}{fld_sep}")
    for k, v in kwargs.items():
        log_str += f"{k}{val_sep}{v}"
        if k != list(kwargs)[-1]:
            log_str += fld_sep

    return log_str


def guaranteed_call_pair_strat_client(pydantic_basemodel_type: Type | None, client_callable: Callable,
                                      **kwargs):
    """
    Call phone_book client call but if call fails for connection error or server not ready error logs it
    with specific pattern which is matched by pair_strat_log_book and the call is call from there in loop till
    it is successfully done
    :param pydantic_basemodel_type: BaseModel of Document type need to update/create,
                                    pass None if callable is query method
    :param client_callable: client callable to be called
    :param kwargs: params to be set in passed pydantic_basemodel_type to pass in `client_callable` or directly
                   passed to `client_callable` in case client_callable is query type
    :return:
    """
    try:
        if pydantic_basemodel_type is not None:
            # Handling for DB operations: create/update/partial_update

            pydantic_basemodel_type_obj = pydantic_basemodel_type(**kwargs)

            if str(client_callable.__name__).startswith("patch_"):
                client_callable(jsonable_encoder(pydantic_basemodel_type_obj, by_alias=True, exclude_none=True))
            else:
                client_callable(pydantic_basemodel_type_obj)
        else:
            # Handling for query operations - queries doesn't take pydantic_obj as param
            client_callable(**kwargs)
    except Exception as e:
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        if "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
            logging.exception("Connection Error in phone_book server call, likely server is "
                              "down, putting pair_strat client call as log for pair_strat_log "
                              f"analyzer handling - caller: {calframe[1][3]}")
        elif "service is not initialized yet" in str(e):
            logging.exception("phone_book service not up yet, likely server restarted, but is "
                              "not ready yet, putting pair_strat client call as log for pair_strat_log "
                              f"analyzer handling - caller: {calframe[1][3]}")
        elif "('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))" in str(e):
            logging.exception("phone_book service connection error, putting pair_strat client call "
                              f"as log for pair_strat_log analyzer handling - caller: {calframe[1][3]}")
        elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
              "it from responding to requests" in str(e) and "status_code: 503" in str(e)):
            logging.exception("phone_book service connection error")
        else:
            raise Exception(f"guaranteed_call_pair_strat_client called from {calframe[1][3]} failed "
                            f"with exception: {e}")
        log_str = pair_strat_client_call_log_str(pydantic_basemodel_type, client_callable, **kwargs)
        logging.db(log_str)


class MDShellEnvData(BaseModel):
    subscription_data: List[Tuple[str, str]] | None = None
    host: str
    port: int
    db_name: str
    project_name: str
    exch_code: str | None = None


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


def get_reset_log_book_cache_wrapper_pattern():
    return "-~-"
