import copy
import logging
import os
import sys
import stat
import math
from threading import Lock
import inspect
from typing import Set

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.aggregate import (
    get_ongoing_or_all_pair_plans_by_sec_id, get_ongoing_pair_plan_filter)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_client import (
    EmailBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    get_field_seperator_pattern, get_key_val_seperator_pattern, get_pattern_for_pair_plan_db_updates, UpdateType)
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, except_n_log_alert, parse_to_int)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import (
    PlanViewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.model_extensions import BrokerUtil
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecord, SecType
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_key)

if os.getenv("DASH_MODE"):
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.dept_book_service_helper import (
        dept_book_service_http_client, DeptBookServiceHttpClient)
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

update_contact_status_lock: Lock = Lock()
force_clear_positions_priority: int = 9
force_clear_brokers = ["zerodha"]  # comparison is always lower cased


def patch_contact_status(overall_buy_notional: float | None, overall_sell_notional: float | None) -> None:
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
            with update_contact_status_lock:
                contact_status_list: List[ContactStatusBaseModel] = \
                    email_book_service_http_client.get_all_contact_status_client()
                logging.debug(f"contact_status_list count: {len(contact_status_list)}")
                if 0 == len(contact_status_list):  # no contact status set yet
                    logging.error(f"patch_contact_status failed. no contact status obj found;;;"
                                  f"update request: {kwargs}")
                elif 1 == len(contact_status_list):
                    kwargs.update(_id=contact_status_list[0].id)
                    updated_contact_status: ContactStatusBaseModel = ContactStatusBaseModel(**kwargs)
                    email_book_service_http_client.patch_contact_status_client(updated_contact_status.to_json_dict(exclude_none=True))
                else:
                    logging.critical(
                        "multiple contact status entries not supported at this time! "
                        "use swagger UI to delete redundant entries from DB and retry."
                        f"this blocks all update requests. update request being processed: {kwargs}")
        # else not action required - no action to take - ignore and continue
    except Exception as e:
        logging.critical(f"something serious is wrong: patch_contact_status is throwing an exception!;;; "
                         f"exception: {e}", exc_info=True)


def write_md_subscribe_cmd_header(open_script_file, exch_code: str, debug_cn_cb_pair: Tuple[str, str] | None,
                                  debug_cn_a_eqt: str | None):
    # generate header
    open_script_file.write("#!/bin/bash -li\n")  # alias requires interactive shell (li)
    open_script_file.write("#shopt -s expand_aliases\n")  # allows cdm alias to work
    open_script_file.write("echo $PWD\n")  # pre-cdm dir
    open_script_file.write("cdm\n")  # cdm assumed alias in external shell that takes to MD executable dir
    open_script_file.write("echo $PWD\n")  # post-cdm dir
    open_script_file.write(f"export EXCHANGE_CODE={exch_code}\n")
    # generate debug run function
    open_script_file.write("_debug_run(){\n")
    is_cn_cb_pair_good: bool = False
    if debug_cn_cb_pair:
        cn_cb_ticker, cn_a_eqt_ticker = debug_cn_cb_pair
        if cn_cb_ticker and cn_a_eqt_ticker:
            open_script_file.write(f"  export SYMBOL_PAIRS={cn_cb_ticker}:{cn_a_eqt_ticker},\n")
            is_cn_cb_pair_good = True
    is_cn_a_eqt_good: bool = False
    if debug_cn_a_eqt:
        open_script_file.write(f"  export CN_EQT={debug_cn_a_eqt},\n")
        is_cn_a_eqt_good = True
    if (not is_cn_cb_pair_good) or (not is_cn_a_eqt_good):
        raise Exception(f"cn_cb_pair or cn_a_eqt must be passed with valid values; found {debug_cn_cb_pair=}, "
                        f"{debug_cn_a_eqt=}")
    open_script_file.write("  ./run.sh &\n")
    open_script_file.write("  #./run_md_native_replay.sh &\n")
    open_script_file.write("  exit 0\n}\n")
    # generate run function
    open_script_file.write("_run(){\n")
    open_script_file.write("  if [ -z \"$GDB_DEBUG\" ] && [ -z \"$LIMITED_RUN\" ] ; then\n")
    open_script_file.write("    ./run.sh &\n")
    open_script_file.write("    #./run_md_native_replay.sh &\n")
    open_script_file.write("  else\n")
    open_script_file.write("    _debug_run\n")
    open_script_file.write("  fi\n}\n")
    # return generated run function name
    md_run_cmd: str = "\n_run\n"
    return md_run_cmd


def write_md_subscribe_cmd_footer(open_script_file):
    open_script_file.write("cd -\n")  # cd - takes back to mobile_book scripts dir
    open_script_file.write("echo $PWD\n")  # reverted: pre-cdm dir
    # TODO urgent: post with (file closed):
    #  1. update generated file mode : chmod +x
    #  2. Execute generated file as script


# currently only supports CB-A pairs - extend to add A-H support
def create_md_subscription_script(static_data, exch_code: str,
                                  debug_cn_cb_pair: Tuple[str, str] | None, debug_eqt_symbol: str | None = None,
                                  bucket_size: int = 20) -> None:
    # "SYMBOL_PAIRS=127069:000928,128111:002738,113025:601677,113534:603876"
    # Write/Read ('w+'): opens file for both reading/writing. Any existing text is overwritten/deleted from file
    md_run_script: str = f"md-dash-{exch_code.lower()}.sh"
    with open(md_run_script, "w+") as md_subscription_trigger_script:
        md_run_cmd = write_md_subscribe_cmd_header(md_subscription_trigger_script, exch_code, debug_cn_cb_pair,
                                                   debug_eqt_symbol)
        matched_pair_count: int = 0
        for cb_ticker, eqt_ticker in static_data.barter_ready_eqt_ticker_by_cb_ticker.items():
            if matched_pair_count % bucket_size == 0:
                if matched_pair_count != 0:
                    md_subscription_trigger_script.write(export_sym_pairs_cmd)
                    md_subscription_trigger_script.write(md_run_cmd)
                    matched_pair_count = 0
                export_sym_pairs_cmd = f"\nexport SYMBOL_PAIRS="
            ticker_exch_code: str = static_data.get_ric_suffix_from_ticker(eqt_ticker)
            if ticker_exch_code == exch_code:
                matched_pair_count += 1
                export_sym_pairs_cmd += f"{cb_ticker}:{eqt_ticker},"
        if matched_pair_count % bucket_size != 0:
            md_subscription_trigger_script.write(export_sym_pairs_cmd)
            md_subscription_trigger_script.write(md_run_cmd)
        write_md_subscribe_cmd_footer(md_subscription_trigger_script)
    os.chmod(md_run_script, stat.S_IRWXU)


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


def is_ongoing_plan(pair_plan: PairPlan | PairPlanBaseModel | None) -> bool:
    if not pair_plan:
        logging.error(f"is_ongoing_plan invoked with {pair_plan=}, returning False")
        return False
    return pair_plan.plan_state not in [PlanState.PlanState_UNSPECIFIED,
                                          PlanState.PlanState_READY,
                                          PlanState.PlanState_DONE,
                                          PlanState.PlanState_SNOOZED]


@except_n_log_alert()
def create_contact_limits(eligible_brokers: List[BrokerBaseModel] | None = None) -> ContactLimitsBaseModel:
    contact_limits_obj: ContactLimitsBaseModel = get_new_contact_limits(eligible_brokers, external_source=True)
    web_client_internal = get_internal_web_client()
    created_contact_limits: ContactLimitsBaseModel = (
        web_client_internal.create_contact_limits_client(contact_limits_obj))
    logging.info(f"{created_contact_limits=}")
    return created_contact_limits


@except_n_log_alert()
def get_contact_limits() -> ContactLimitsBaseModel | None:
    web_client = get_internal_web_client()
    contact_limits_list: List[ContactLimitsBaseModel] = web_client.get_all_contact_limits_client()
    if 0 == len(contact_limits_list):
        return None
    elif 1 < len(contact_limits_list):
        err_str_ = (f"multiple: {len(contact_limits_list)} contact_limits entries not supported at this time! "
                    f"use swagger UI to delete redundant entries: {contact_limits_list} from DB and retry")
        raise Exception(err_str_)
    else:
        return contact_limits_list[0]


@except_n_log_alert()
def get_chore_limits() -> ChoreLimitsBaseModel | None:
    chore_limits_list: List[ChoreLimitsBaseModel] = email_book_service_http_client.get_all_chore_limits_client()
    if 0 == len(chore_limits_list):
        return None
    elif 1 < len(chore_limits_list):
        err_str_ = (f"multiple: {len(chore_limits_list)} chore_limits entries not supported at this time! "
                    f"use swagger UI to delete redundant entries: {chore_limits_list} from DB and retry")
        raise Exception(err_str_)
    else:
        return chore_limits_list[0]


def get_new_contact_status() -> ContactStatus:
    contact_status: ContactStatus = ContactStatus(id=1, overall_buy_notional=0,
                                                        overall_sell_notional=0,
                                                        overall_buy_fill_notional=0,
                                                        overall_sell_fill_notional=0,
                                                        open_chores=0)
    return contact_status


def get_new_contact_limits(eligible_brokers: List[Broker] | None = None,
                             external_source: bool = False) -> ContactLimits | ContactLimitsBaseModel:
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value
    model_class_type = ContactLimits
    if external_source:
        model_class_type = ContactLimitsBaseModel

    rolling_max_chore_count = RollingMaxChoreCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxChoreCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    contact_limits_obj = model_class_type(id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                            max_gross_n_open_notional=2_400_000,
                                            rolling_max_chore_count=rolling_max_chore_count,
                                            rolling_max_reject_count=rolling_max_reject_count,
                                            eligible_brokers=eligible_brokers,
                                            eligible_brokers_update_count=0)
    return contact_limits_obj


def get_new_chore_limits() -> ChoreLimits:
    ord_limit_obj: ChoreLimits = ChoreLimits(id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                                             max_chore_qty=500, max_chore_notional=90_000, max_basis_points_algo=1500,
                                             max_px_deviation_algo=20, max_chore_qty_algo=500,
                                             max_chore_notional_algo=90_000)
    return ord_limit_obj


def get_new_plan_view_obj(obj_id: int) -> PlanViewBaseModel:
    plan_view_obj: PlanViewBaseModel = PlanViewBaseModel(id=obj_id, plan_alert_count=0)
    return plan_view_obj


def get_match_level(pair_plan: PairPlan, sec_id: str, side: Side) -> int:
    match_level: int = 6  # no match
    if pair_plan.pair_plan_params.plan_leg1.sec.sec_id == sec_id:
        if pair_plan.pair_plan_params.plan_leg1.side == side:
            match_level = 1  # symbol side match
        else:
            match_level = 2  # symbol match side mismatch
    elif pair_plan.pair_plan_params.plan_leg2.sec.sec_id == sec_id:
        if pair_plan.pair_plan_params.plan_leg2.side == side:
            match_level = 1
        else:
            match_level = 2
    return match_level


# caller must take any locks as required for any read-write consistency - function operates without lock
async def get_ongoing_plans_from_symbol_n_side(sec_id: str, side: Side) -> Tuple[List[PairPlan], List[PairPlan]]:
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_msgspec_routes import \
        underlying_read_pair_plan_http
    read_pair_plan_filter = get_ongoing_pair_plan_filter(sec_id)
    pair_plans: List[PairPlan] = await underlying_read_pair_plan_http(read_pair_plan_filter)

    match_level_1_pair_plans: List[PairPlan] = []
    match_level_2_pair_plans: List[PairPlan] = []
    for pair_plan in pair_plans:
        match_level: int = get_match_level(pair_plan, sec_id, side)
        if match_level == 1:  # symbol side match
            match_level_1_pair_plans.append(pair_plan)
        elif match_level == 2:  # symbol match side mismatch
            match_level_2_pair_plans.append(pair_plan)
        # else not a match ignore
    return match_level_1_pair_plans, match_level_2_pair_plans


async def get_single_exact_match_plan_from_symbol_n_side(sec_id: str, side: Side) -> PairPlan | None:
    match_level_1_pair_plans, match_level_2_pair_plans = await get_ongoing_plans_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_plans) == 0 and len(match_level_2_pair_plans) == 0:
        logging.info(f"No viable pair_plan for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
        return None
    else:
        pair_plan: PairPlan | None = None
        if len(match_level_1_pair_plans) == 1:
            pair_plan = match_level_1_pair_plans[0]
        else:
            logging.error(f"error: processing {get_symbol_side_key([(sec_id, side)])} pair_plan should be "
                          f"found only one in match_lvl_1, found {match_level_1_pair_plans}")
        if pair_plan is None:
            if len(match_level_2_pair_plans) == 1:  # symbol match side mismatch
                pair_plan = match_level_2_pair_plans[0]
                logging.error(f"error: pair_plan should be found in level 1 only, symbol_side_key: "
                              f"{get_symbol_side_key([(sec_id, side)])}")
            else:
                logging.error(
                    f"error: multiple ongoing pair plans matching symbol_side_key: "
                    f"{get_symbol_side_key([(sec_id, side)])} found, one "
                    f"match expected, found: {len(match_level_2_pair_plans)}")
        return pair_plan


async def get_matching_plan_from_symbol_n_side(sec_id: str, side: Side,
                                                no_ongoing_ok: bool = False) -> List[PairPlan] | None:
    """TODO: Use flexible [if passed True by caller] to handle multi plans where non-active side is perfect match"""
    match_level_1_pair_plans: List[PairPlan]
    match_level_2_pair_plans: List[PairPlan]
    match_level_1_pair_plans, match_level_2_pair_plans = await get_ongoing_plans_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_plans) == 0 and len(match_level_2_pair_plans) == 0:
        logging.info(f"No viable pair_plan for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
        return
    else:
        pair_plans: List[PairPlan] | None = None
        if len(match_level_1_pair_plans) == 1:  # single plan found with both symbol side match
            pair_plans = [match_level_1_pair_plans[0]]
        else:
            if len(match_level_1_pair_plans) == 0 and len(match_level_2_pair_plans) == 1:
                logging.info(f"No viable pair_plan for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                return
            else:
                logging.error(f"error: processing {get_symbol_side_key([(sec_id, side)])} same symbol side pair_plan "
                              f"should be found only 1, found {len(match_level_1_pair_plans)};;;"
                              f"{match_level_1_pair_plans}")
        if not pair_plans:  # both symbol-side match not found, try "symbol match side mismatch" - i.e. level 2
            if len(match_level_2_pair_plans) == 1:  # symbol match side mismatch
                found_plan: PairPlan = match_level_2_pair_plans[0]
                logging.warning(f"No ongoing pair_plan for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}; "
                                f"found {found_plan.id=} with same symbol but different side;;;{found_plan=}")
                return
            elif len(match_level_2_pair_plans) == 2:  # symbol match side mismatch for 2 exact pair plans
                # this is okay for roundtrip or intraday tradable symbols
                pair_plans = match_level_2_pair_plans
            else:
                logging.error(
                    f"error: multiple ongoing pair plans matching symbol_side_key: "
                    f"{get_symbol_side_key([(sec_id, side)])} found, one match expected, found: "
                    f"{len(match_level_2_pair_plans)}")
        return pair_plans


def get_plan_key_from_pair_plan(pair_plan: PairPlan | PairPlanBaseModel):
    plan_key = f"{pair_plan.id}"
    return plan_key


def get_id_from_plan_key(unloaded_plan_key: str) -> int:
    parts: List[str] = (unloaded_plan_key.split("-"))
    return parse_to_int(parts[-1])


def pair_plan_client_call_log_str(basemodel_type: Type | None, client_callable: Callable,
                                   update_type: UpdateType | None = None, **kwargs) -> str:
    if update_type is None:
        update_type = UpdateType.JOURNAL_TYPE

    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    pair_plan_db_pattern: str = get_pattern_for_pair_plan_db_updates()
    log_str = (f"{pair_plan_db_pattern}"
               f"{basemodel_type.__name__ if basemodel_type is not None else 'basemodel_type is None'}{fld_sep}{update_type.value}"
               f"{fld_sep}{client_callable.__name__}{fld_sep}")
    for k, v in kwargs.items():
        log_str += f"{k}{val_sep}{v}"
        if k != list(kwargs)[-1]:
            log_str += fld_sep

    return log_str


def guaranteed_call_pair_plan_client(basemodel_type: MsgspecModel | None, client_callable: Callable,
                                      **kwargs):
    """
    Call phone_book client call but if call fails for connection error or server not ready error logs it
    with specific pattern which is matched by pair_plan_log_book and the call is call from there in loop till
    it is successfully done
    :param basemodel_type: BaseModel of Document type need to update/create,
                                    pass None if callable is query method
    :param client_callable: client callable to be called
    :param kwargs: params to be set in passed basemodel_type to pass in `client_callable` or directly
                   passed to `client_callable` in case client_callable is query type
    :return:
    """
    try:
        if basemodel_type is not None:
            # Handling for DB operations: create/update/partial_update

            basemodel_type_obj = basemodel_type.from_dict(kwargs)

            if str(client_callable.__name__).startswith("patch_"):
                client_callable(basemodel_type_obj.to_json_dict(exclude_none=True))
            else:
                client_callable(basemodel_type_obj)
        else:
            # Handling for query operations - queries doesn't take model_obj as param
            client_callable(**kwargs)
    except Exception as e:
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        if "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
            logging.exception("Connection Error in phone_book server call, likely server is "
                              "down, putting pair_plan client call as log for pair_plan_log "
                              f"analyzer handling - caller: {calframe[1][3]}")
        elif "service is not initialized yet" in str(e):
            logging.exception("phone_book service not up yet, likely server restarted, but is "
                              "not ready yet, putting pair_plan client call as log for pair_plan_log "
                              f"analyzer handling - caller: {calframe[1][3]}")
        elif "('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))" in str(e):
            logging.exception("phone_book service connection error, putting pair_plan client call "
                              f"as log for pair_plan_log analyzer handling - caller: {calframe[1][3]}")
        elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
              "it from responding to requests" in str(e) and "status_code: 503" in str(e)):
            logging.exception("phone_book service connection error")
        else:
            raise Exception(f"guaranteed_call_pair_plan_client called from {calframe[1][3]} failed "
                            f"with exception: {e}")
        log_str = pair_plan_client_call_log_str(basemodel_type, client_callable, **kwargs)
        logging.db(log_str)


class MDShellEnvData(MsgspecBaseModel, kw_only=True):
    subscription_data: List[Tuple[str, str]] | None = None
    host: str
    port: int
    db_name: str
    project_name: str
    exch_code: str | None = None
    so_continue: bool = False  # used by basket executor to continue getting market data while in SO mode


def create_start_cpp_md_shell_script(generation_start_file_path: str, config_file_path: str, instance_id: str):
    script_file_name = os.path.basename(generation_start_file_path)
    env_file_name = f"env_{script_file_name}"
    env_file_path = f"{os.path.dirname(generation_start_file_path)}/{env_file_name}"
    log_dir_path = PurePath(generation_start_file_path).parent.parent / "log"
    script_log_file_path = log_dir_path / f"{script_file_name}.log"
    with open(env_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write(f"SCRIPT_LOG_FILE_PATH={script_log_file_path}\n")
        fl.write("echo SCRIPT_LOG_FILE_PATH: ${SCRIPT_LOG_FILE_PATH}\n")
        fl.write(f"export LOG_DIR_PATH={log_dir_path}\n")
        fl.write('echo LOG_DIR_PATH: "${LOG_DIR_PATH}" >>${SCRIPT_LOG_FILE_PATH} 2>&1\n')
        fl.write("shopt -s expand_aliases >>${SCRIPT_LOG_FILE_PATH} 2>&1\n")
        fl.write("source ${HOME}/.bashrc\n")
        fl.write("#export GDB_DEBUG=1  # uncomment if you want the process to start in GDB\n")
        fl.write(f'export INSTANCE_ID={instance_id}\n')
        executor_static_config_file_path = PurePath(__file__).parent.parent.parent / "street_book" / "data" / "config.yaml"
        fl.write(f'export CONFIG_FILE={executor_static_config_file_path}\n')
        fl.write('echo CONFIG_FILE: "${CONFIG_FILE}" >>${SCRIPT_LOG_FILE_PATH} 2>&1\n')
        fl.write('echo GDB_DEBUG: "${GDB_DEBUG}" >>${SCRIPT_LOG_FILE_PATH} 2>&1\n')
        fl.write('echo triggering run from "${PWD}" >>${SCRIPT_LOG_FILE_PATH} 2>&1\n')
    os.chmod(env_file_path, stat.S_IRWXU)

    md_exec_file_path = PurePath(__file__).parent.parent.parent / "base_book" / "app" / "mobile_book_executable"
    with open(generation_start_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write(f"source {env_file_path}\n")
        fl.write('if [ -z "$GDB_DEBUG" ] ; then\n')
        fl.write(f"        {md_exec_file_path} {config_file_path} "+" >>${SCRIPT_LOG_FILE_PATH} 2>&1\n")
        fl.write("else\n")
        fl.write(f"        {md_exec_file_path} {config_file_path}\n")
        fl.write("fi\n")


def create_stop_cpp_md_shell_script(running_process_name: str, generation_stop_file_path: str, config_file_path: str):
    script_file_name = os.path.basename(generation_stop_file_path)
    log_file_path = PurePath(generation_stop_file_path).parent.parent / "log" / f"{script_file_name}.log"
    # stop file generator
    with open(generation_stop_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write(f"LOG_FILE_PATH={log_file_path}\n")
        fl.write("echo Log_file_path: ${LOG_FILE_PATH}\n")

        fl.write(f"PROCESS_COUNT=`pgrep -f {running_process_name} | wc -l`\n")
        fl.write('if [ "$PROCESS_COUNT" -eq 0 ]; then\n')
        fl.write('  echo "nothing to kill" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('else\n')
        fl.write('  echo "PC: $PROCESS_COUNT" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write(f'  pgrep -f {running_process_name} | xargs kill\n')
        fl.write('fi\n')
        fl.write(f"pgrep -f 'mobile_book_executable {config_file_path}' | xargs kill\n")


def create_md_shell_script(md_shell_env_data: MDShellEnvData, generation_start_file_path: str, mode: str,
                           instance_id: str = ""):
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
        fl.write(f'export INSTANCE_ID={instance_id}\n')
        # for FX , exclude exch_code, SUBSCRIPTION_DATA instead export FX=1 with mode SO
        if md_shell_env_data.exch_code is not None:
            fl.write(f"export EXCHANGE_CODE={md_shell_env_data.exch_code}\n")
        else:  # we are in FX mode
            fl.write(f"export FX=1\n")
            mode = "SO"  # overriding mode since fx is SO mode
        if md_shell_env_data.subscription_data is not None:
            if len(md_shell_env_data.subscription_data) == 1:
                # ',' separated list of ':' separated pairs of CB, followed by EQT; either can be blank but not both
                fl.write(f'export CN_CB_EQ={md_shell_env_data.subscription_data[0][0]}:,\n')
            else:
                fl.write(f'export SUBSCRIPTION_DATA="{jsonable_encoder(md_shell_env_data.subscription_data)}"\n')

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


def create_stop_md_script(running_process_name: str, generation_stop_file_path: str):
    script_file_name = os.path.basename(generation_stop_file_path)
    log_file_path = PurePath(generation_stop_file_path).parent.parent / "log" / f"{script_file_name}.log"
    # stop file generator
    with open(generation_stop_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write(f"LOG_FILE_PATH={log_file_path}\n")
        fl.write("echo Log_file_path: ${LOG_FILE_PATH}\n")
        fl.write("shopt -s expand_aliases >>${LOG_FILE_PATH} 2>&1\n")
        fl.write("source ${HOME}/.bashrc\n")
        # create this as alias in your bashrc to cd into market data run.sh script dir
        fl.write("cdm >>${LOG_FILE_PATH} 2>&1\n")
        fl.write(f"PROCESS_COUNT=`pgrep -f {running_process_name} | wc -l`\n")
        fl.write('if [ "$PROCESS_COUNT" -eq 0 ]; then\n')
        fl.write('  echo "nothing to kill" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('else\n')
        fl.write('  echo "PC: $PROCESS_COUNT" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write(f'  pids=$(pgrep -f {running_process_name})\n')
        fl.write('  for pid in $pids; do\n')
        fl.write('    ./kill_passthrough_service_by_pid.sh PID="$pid" >>${LOG_FILE_PATH} 2>&1\n')
        fl.write('  done\n')
        fl.write('fi\n')


@except_n_log_alert()
def get_internal_web_client():
    web_client: EmailBookServiceHttpClient | DeptBookServiceHttpClient
    if os.environ.get("DASH_MODE"):
        web_client = dept_book_service_http_client
    else:
        web_client = email_book_service_http_client
    return web_client


async def get_dismiss_filter_brokers(underlying_http_callable, static_data, security_id1: str, security_id2: str):
    ric1, ric2 = static_data.get_connect_n_qfii_rics_from_ticker(security_id1)
    ric3, ric4 = static_data.get_connect_n_qfii_rics_from_ticker(security_id2)
    sedol = static_data.get_sedol_from_ticker(security_id1)
    # get security name from : pair_plan_params.plan_legs and then redact pattern
    # security.sec_id (a pattern in positions) where there is a value match
    dismiss_filter_agg_pipeline = {'redact': [("security.sec_id", ric1, ric2, ric3, ric4, sedol)]}
    filtered_brokers: List[ShadowBrokers] = await underlying_http_callable(dismiss_filter_agg_pipeline)

    eligible_brokers = []
    for broker in filtered_brokers:
        if broker.sec_positions:
            eligible_brokers.append(broker)
    return eligible_brokers


async def handle_shadow_broker_creates(contact_limits_objs: ContactLimits,
                                       underlying_create_all_shadow_brokers_http):
    broker_list: List[ShadowBrokers] = []
    for eligible_broker in contact_limits_objs.eligible_brokers:
        broker_dict = eligible_broker.to_dict()
        del broker_dict["_id"]
        broker_list.append(ShadowBrokers.from_dict(broker_dict))

    if broker_list:
        await underlying_create_all_shadow_brokers_http(broker_list)


async def handle_shadow_broker_updates(
        updated_contact_limits_obj: ContactLimits | Dict,
        underlying_read_shadow_brokers_http, underlying_create_all_shadow_brokers_http,
        underlying_update_all_shadow_brokers_http, underlying_delete_by_id_list_shadow_brokers_http):
    create_broker_list: List[ShadowBrokers] = []
    update_broker_list: List[ShadowBrokers] = []

    shadow_brokers: List[ShadowBrokers] = await underlying_read_shadow_brokers_http()
    shadow_broker_name_to_obj_dict = {}
    shadow_broker_names_list = []
    for shadow_brokers_obj in shadow_brokers:
        shadow_broker_name_to_obj_dict[shadow_brokers_obj.broker] = shadow_brokers_obj
        shadow_broker_names_list.append(shadow_brokers_obj.broker)

    if isinstance(updated_contact_limits_obj, dict):
        for eligible_broker in updated_contact_limits_obj.get("eligible_brokers"):
            eligible_broker_id = eligible_broker["_id"]
            del eligible_broker["_id"]

            broker_name = eligible_broker.get("broker")
            shadow_broker = shadow_broker_name_to_obj_dict.get(broker_name)
            if shadow_broker is not None:
                eligible_broker["_id"] = shadow_broker.id
                update_broker_list.append(ShadowBrokers.from_dict(eligible_broker))

                # removing broker which exists
                shadow_broker_names_list.remove(broker_name)
            else:
                # since this broker doesn't exist in db - creating it in shadow_brokers
                create_broker_list.append(ShadowBrokers.from_dict(eligible_broker))

            # setting eligible_broker.id back
            eligible_broker["_id"] = eligible_broker_id
    else:
        for eligible_broker in updated_contact_limits_obj.eligible_brokers:
            broker_dict = eligible_broker.to_dict()
            del broker_dict["_id"]
            broker_name = eligible_broker.broker
            shadow_broker = shadow_broker_name_to_obj_dict.get(broker_name)
            if shadow_broker is not None:
                broker_dict["_id"] = shadow_broker.id
                update_broker_list.append(ShadowBrokers.from_dict(broker_dict))

                # removing broker which exists
                shadow_broker_names_list.remove(broker_name)
            else:
                # since this broker doesn't exist in db - creating it in shadow_brokers
                create_broker_list.append(ShadowBrokers.from_dict(broker_dict))

            # No need to set eligible_broker.id back since id of generated dict is deleted and not of obj

    if create_broker_list:
        await underlying_create_all_shadow_brokers_http(create_broker_list)
    if update_broker_list:
        await underlying_update_all_shadow_brokers_http(update_broker_list)

    # if shadow_broker_names_list still have any value left after full contact_limits' brokers loop then
    # it must have been removed - removing it from shadow brokers also
    delete_id_list = []
    for broker_name in shadow_broker_names_list:
        shadow_brokers_obj = shadow_broker_name_to_obj_dict.get(broker_name)
        delete_id_list.append(shadow_brokers_obj.id)

    if delete_id_list:
        await underlying_delete_by_id_list_shadow_brokers_http(delete_id_list)


def update_ticker_to_positions_list(ticker: str, position: Position,
                                    ticker_to_positions: Dict[str, List[Position]]):
    if positions_list := ticker_to_positions.get(ticker):
        positions_list.append(position)
    else:
        ticker_to_positions[ticker] = [position]
    if not position.acquire_cost:
        position.acquire_cost = 1000  # default acquire cost if no acquire cost is found


def prioritize_by_cost(compressed_eligible_broker_list: List[Broker]):
    ticker_to_sod_positions: Dict[str, List[Position]] = {}
    ticker_to_pth_locate_positions: Dict[str, List[Position]] = {}

    def get_ticker_from_ric(ric_code: str) -> str:
        return (ric_code.split(".", 2))[0]

    compressed_eligible_broker: Broker
    for compressed_eligible_broker in compressed_eligible_broker_list:
        for sec_position in compressed_eligible_broker.sec_positions:
            ticker_or_sedol: str = sec_position.security.sec_id if (sec_position.security.sec_id_source ==
                                                                    SecurityIdSource.SEDOL) else (
                get_ticker_from_ric(sec_position.security.sec_id))  # TODO Call static data TICKER FROM RIC HERE
            position: Position
            for position in sec_position.positions:
                if position.type == PositionType.SOD:
                    # prioritize force clear broker positions with pre-fixed priority
                    if compressed_eligible_broker.broker.lower() in force_clear_brokers:
                        position.priority = force_clear_positions_priority
                    # store
                    update_ticker_to_positions_list(ticker_or_sedol, position, ticker_to_sod_positions)
                elif position.type == PositionType.LOCATE or position.type == PositionType.PTH:
                    update_ticker_to_positions_list(ticker_or_sedol, position, ticker_to_pth_locate_positions)
    for ticker_or_sedol, sod_positions in ticker_to_sod_positions.items():
        # sort the highest cost to the lowest cost [we ought to clear highest cost SOD first]
        try:
            sod_positions.sort(key=lambda x: x.acquire_cost, reverse=True)
        except TypeError as te:
            logging.exception(f"TypeError: {te}")
        # start prioritize from 10 to allow room for easy user overrides below 10 [higher priority]
        cur_highest_priority_even_number: int = 10
        for sod_position in sod_positions:
            # avoid re-prioritizing force_clear_broker_positions
            if not (sod_position.priority is not None and sod_position.priority == force_clear_positions_priority):
                sod_position.priority = cur_highest_priority_even_number
                cur_highest_priority_even_number += 2
    # all SODs are prioritized, now prioritize PTH and Locates
    for ticker_or_sedol, pth_locate_positions in ticker_to_pth_locate_positions.items():
        sod_positions = ticker_to_sod_positions.get(ticker_or_sedol)
        cur_highest_priority_number: int
        if sod_positions:
            # start priority at after last SOD priority
            cur_highest_priority_number = sod_positions[-1].priority + 2
        else:
            cur_highest_priority_number = 20  # if no SOD found - start at 20
            # sort by lowest cost to the highest cost [if no SOD, we ought to consume the lowest cost locate/pth first]
        pth_locate_positions.sort(key=lambda x: x.acquire_cost)
        for pth_locate_position in pth_locate_positions:
            pth_locate_position.priority = cur_highest_priority_number
            cur_highest_priority_number += 2


def compress_eligible_broker_positions(eligible_broker_list: List[BrokerBaseModel]):
    if eligible_broker_list is None:
        return None
    compressed_eligible_broker_list: List[Broker] = [BrokerUtil.compress(broker) for broker in eligible_broker_list]
    # make this by configuration - default fixed priority done internally
    prioritize_by_cost(compressed_eligible_broker_list)
    return compressed_eligible_broker_list


def get_percentage_change(new_val: float, old_val: float):
    return (old_val - new_val) / old_val * 100


def get_premium(conv_px: float, eqt_px: float, cb_px: float) -> float:
    conv_ratio: Final[float] = 100 / conv_px
    parity: Final[float] = eqt_px * conv_ratio
    premium: Final[float] = ((cb_px / parity) - 1) * 100
    return premium


def compute_max_single_leg_notional(static_data, brokers: List[Broker | BrokerOptional], cb_symbol: str,
                                    eqt_symbol: str, side: Side, usd_fx: float, cb_close_px_: float | None,
                                    eqt_close_px_: float | None,
                                    orig_intra_day_bot: int | None = None,
                                    orig_intra_day_sld: int | None = None) -> Tuple[int, int, int]:
    """
    TOH: returns computed max_single_leg_notional + computed bot and sld if passed None in last two return params, else
    passed orig_intra_day_bot and orig_intra_day_sld are returned as-is
    """
    if cb_close_px_ is None or eqt_close_px_ is None:
        error_: str = (f"invalid close px for {cb_symbol=}, {eqt_symbol=}, {cb_close_px_=}, {eqt_close_px_=};;;"
                       f"{get_symbol_side_key([(cb_symbol, side)])}")
        logging.critical(error_)
        raise HTTPException(status_code=400, detail=error_)

    cb_eqt_ratio: float
    if math.isclose(eqt_close_px_, 0):
        cb_eqt_ratio = 0
    else:
        cb_eqt_ratio = cb_close_px_ / eqt_close_px_
    if not brokers:
        logging.warning(
            f"compute_max_single_leg_notional: no brokers found for cb/eqt pair: {cb_symbol}/{eqt_symbol} side: {side}"
            f";;;{get_symbol_side_key([(cb_symbol, side)])}")
        return 0, orig_intra_day_bot, orig_intra_day_sld  # send max cb notional as 0
    max_cb_size, orig_intra_day_bot, orig_intra_day_sld = compute_max_cb_size(static_data, brokers, side, cb_eqt_ratio,
                                                                              orig_intra_day_bot, orig_intra_day_sld)
    max_single_leg_notional: float = max_cb_size * get_usd_px(cb_close_px_, usd_fx)
    return int(max_single_leg_notional), orig_intra_day_bot, orig_intra_day_sld


def get_usd_px(px: float, usd_fx: float):
    """
    assumes single currency plan for now - may extend to accept symbol and send revised px according to
    underlying bartering currency
    """
    return px / usd_fx


def get_sod_borrow_intraday(sec_rec_by_sec_id_dict: Dict[str, SecurityRecord], leg_sec_type: SecType,
                            brokers: List[Broker], leg_side: Side = Side.SELL,
                            non_systematic_brokers: Set[str] | None = None) -> Tuple[int, int, int, int]:
    """
    Done
    Helps compute how much are we allowed to SELL by computing and returning: sod_sum, borrow_sum, intraday_bot
     1. sod_sum: SOD Longs [settled prior BUYs]
     2. borrow_sum: Any borrows if available [PTHs and Locates]
     3. intraday_bot: Intraday Longs or None for Locate / PTH only
     4. intraday_sld: Intraday Shorts [short is sent -ive] or None for Locate / PTH
    """

    sod_sum: int = 0
    borrow_sum: int = 0
    intraday_bot: int = 0
    intraday_sld: int = 0

    for broker in brokers:
        if broker.bkr_disable:
            continue
        for sec_position in broker.sec_positions:
            sec_rec: SecurityRecord | None
            if not (sec_rec := sec_rec_by_sec_id_dict.get(sec_position.security.sec_id)):
                continue  # process only tradable sec_rec found in sec_rec_by_sec_id_dict
            elif sec_rec.sec_type != leg_sec_type:
                logging.error(f"Unexpected: get_sod_borrow_intraday found non-matching {sec_rec.sec_type=} and "
                              f"{leg_sec_type=}; for {sec_position.security.sec_id} only happens if bug in system, "
                              f"ignoring the sec_position and continuing;;;{sec_position=} found {sec_rec=}")
                continue
            ticker = sec_rec.ticker
            for position in sec_position.positions:
                if position.pos_disable:  # ignore disabled positions
                    continue
                # ignore any non-systematic-brokers
                if non_systematic_brokers and (broker.broker.lower() in non_systematic_brokers):
                    logging.warning(f"ignoring non_systematic_broker {broker.broker} {position.type=} for {ticker=};;;"
                                    # since CB is SELL, EQT is BUY
                                    f"{position=}; {get_symbol_side_key([(ticker, Side.BUY)])}")
                    continue

                if position.type == PositionType.SOD:

                    # 1. Handle SOD [only long affects the outcome]
                    if position.available_size > 0:  # only long SODs can be used for intraday shorts
                        if not sec_rec.settled_tradable:
                            logging.warning(f"ignoring SOD: {position.available_size} for {ticker=}, found not "
                                            f"settled_tradable")
                            # only settled_tradable position's SOD(s) are party to compute [the line may have intraday
                            # (position.consumed_size) - don't continue the loop - carry on to apply intraday]
                        else:  # this is settled_tradable and +ive - add to SOD sum
                            sod_sum += position.available_size
                    # else no action, plan is adding more short on this leg; just ignore prior day SOD available_size
                    # not to be confused with "intraday short" (i.e. position.consumed_size) handled below

                    # 2. Handle Intraday [both long and short affect the outcome]
                    # explicit check bot and sld sizes [they may have settled barterd and cancelled in consumed_size]
                    if (position.bot_size is None or position.bot_size == 0) and (
                            position.sld_size is None or position.sld_size == 0):
                        continue  # no intraday bot or sld on this position yet
                    if not sec_rec.executed_tradable:
                        # not executed_tradable intraday bot or sld, we warn and ignore long side - but we apply sell
                        # side [prior or current run consumption on sell side eats from what we are allowed to sell
                        # max allowed is always computed by remaining allowed to sell]
                        intraday_sld += position.sld_size if position.sld_size else 0
                        bot_str = "" if position.bot_size == 0 else f"{position.bot_size=}"
                        logging.warning(f"ignoring intraday: {bot_str} for {ticker=}, found not "
                                        f"executed_tradable")
                        continue
                    else:  # since executed_tradable Intraday positions: update bot/sld compute
                        intraday_bot += position.bot_size if position.bot_size else 0
                        intraday_sld += position.sld_size if position.sld_size else 0

                elif position.type == PositionType.LOCATE or position.type == PositionType.PTH:
                    if position.available_size < 0:  # PTHs / LOCATE(s) are always positive
                        ticker = sec_rec.ticker
                        logging.error(f"Unexpected: -ive position found on {ticker} {leg_sec_type=} {leg_side=} plan "
                                      f"from: {broker.broker}, for {str(position.type)}, sending 0 "
                                      f"max_single_leg_notional for the plan;;;{position=}; "
                                      f"{get_symbol_side_key([(ticker, leg_side)])}")
                        return 0, 0, 0, 0
                    else:
                        borrow_sum += position.available_size
    return sod_sum, borrow_sum, intraday_bot, intraday_sld


def compute_max_cb_size_(sod_sum: int, borrow_sum: int, intraday_bot: int, intraday_sld: int, sec_type: SecType,
                         sec_rec_by_sec_id_dict: Dict, divide_ratio_: float,
                         orig_intra_day_bot: int | None, orig_intra_day_sld: int | None) -> Tuple[int, int, int]:
    def none_to_0(val):
        return val if val else 0

    # handle borrow
    max_size: int = borrow_sum

    # handle SOD
    if sod_sum > 0:
        max_size += sod_sum
    # else not required: sec_type sod is negative, plan is going further short - ignore prior SOD short

    # handle intraday
    pre_intraday_max_size = max_size
    if intraday_bot != 0:
        # intraday long control is via static data intraday eligibility - code won't end up here unless eligible
        # log warning and proceed
        if (not orig_intra_day_bot) and (not orig_intra_day_sld):  # we're in process's starting up case
            # intraday BUY adds to max-size we can sell and intraday_sld depletes max_size
            max_size += intraday_bot + intraday_sld
        else:
            # the plan is ongoing - use orig sld, new sld don't deplete max-size, they are likely from this plan
            # sell plan Found intraday_sld represents prior run consumption if any + current run
            # prior run consumption is valid depletion so apply orig sld
            # found intraday BUY is from some other plan thus adds to max-size we can sell
            max_size += intraday_bot + (orig_intra_day_sld if orig_intra_day_sld else 0)
        orig_intra_day_bot = none_to_0(intraday_bot)
        orig_intra_day_sld = none_to_0(intraday_sld)
        logging.warning(f"found intraday eligible long {intraday_bot} {sec_type} position while plan is to short "
                        f"{sec_type}, positively affecting {pre_intraday_max_size=} to: {max_size=};;;prevent intraday "
                        f"based max_size change via static data intraday eligibility; check get_sod_borrow_intraday")
        # sec_type intraday blocked via static data executed_tradable [as of today]
    elif intraday_sld != 0:
        # we have intraday short position on sec_type (-ive value) adding to max_size will reduce the max_size
        # do this only if plan is not ongoing - enables recovering consumption at executor start [for ongoing see else]
        # 0 is valid start position
        if orig_intra_day_bot is None and orig_intra_day_sld is None:
            max_size += intraday_sld
            orig_intra_day_bot = none_to_0(intraday_bot)
            orig_intra_day_sld = none_to_0(intraday_sld)
            logging.warning(f"found short {intraday_sld} {sec_type} position while plan is to short {sec_type}, this "
                            f"will negatively affect {pre_intraday_max_size=} to make it: {max_size=}")
        else:
            # the plan is ongoing - use orig_intra_day(s) and ignore found intraday_sld (its current run
            # consumption + prior run consumption if any)
            max_size += none_to_0(orig_intra_day_bot) + none_to_0(orig_intra_day_sld)
    else:
        # intraday bot/sld both == 0 if we're here, so no intraday yet, make startup done by setting orig bot/sld to 0
        orig_intra_day_bot = none_to_0(intraday_bot)
        orig_intra_day_sld = none_to_0(intraday_sld)
    if math.isclose(divide_ratio_, 0):
        max_size = 0
    else:
        max_size = int(max_size / divide_ratio_)
    return int(max_size), orig_intra_day_bot, orig_intra_day_sld


def compute_max_cb_size(static_data, brokers: List[Broker], cb_side: Side, cb_eqt_ratio_: float,
                        orig_intra_day_bot: int | None = None,
                        orig_intra_day_sld: int | None = None) -> Tuple[int, int, int]:
    """
    # TODO: Generalize this function get_max_size by sending short leg symbol based sec_rec_by_short_leg_symbol dict
    if EQT on BUY side, CB can only be sold limited to SOD available otherwise PTH + LOCATE + positive-SOD
    (negative SOD is assumed to have been located/PTH before)
    """
    if not brokers:
        logging.warning("compute_max_cb_size: no brokers found")

    max_size: int = 0

    intraday_bot: int
    intraday_sld: int
    sod_sum: int
    borrow_sum: int
    if cb_side == Side.BUY:
        # implies EQT is Sell [intraday longs contributes in max_size, intraday shorts are to be ignored]
        # only interested in EQT SOD/Borrow/Intraday - rest are ignored if not found in sec_rec_by_sec_id_dict
        sec_rec_by_sec_id_dict: Dict[str, SecurityRecord] = static_data.barter_ready_eqt_records_by_ric
        sod_sum, borrow_sum, intraday_bot, intraday_sld = get_sod_borrow_intraday(sec_rec_by_sec_id_dict, SecType.EQT,
                                                                                  brokers)
        max_size, orig_intra_day_bot, orig_intra_day_sld = (
            compute_max_cb_size_(sod_sum, borrow_sum, intraday_bot, intraday_sld, SecType.EQT, sec_rec_by_sec_id_dict,
                                 cb_eqt_ratio_, orig_intra_day_bot, orig_intra_day_sld))
    else:  # CB is Sell and EQT is Buy
        # only interested in CB SOD/Borrow/Intraday - rest are ignored if not found in sec_rec_by_sec_id_dict
        sec_rec_by_sec_id_dict: Dict[str, SecurityRecord] = static_data.barter_ready_cb_records_by_sedol
        sod_sum, borrow_sum, intraday_bot, intraday_sld = get_sod_borrow_intraday(sec_rec_by_sec_id_dict, SecType.CB,
                                                                                  brokers, Side.SELL)

        max_size, orig_intra_day_bot, orig_intra_day_sld = (
            compute_max_cb_size_(sod_sum, borrow_sum, intraday_bot, intraday_sld, SecType.CB, sec_rec_by_sec_id_dict,
                                 1, orig_intra_day_bot, orig_intra_day_sld))
    if not orig_intra_day_bot:
        orig_intra_day_bot = 0  # we started with no intraday bot
    if not orig_intra_day_sld:
        orig_intra_day_sld = 0  # we started with no intraday sld
    return int(max_size), orig_intra_day_bot, orig_intra_day_sld


def get_filtered_brokers_by_sec_id_list(brokers: List[Broker | BrokerBaseModel], sec_id_list: List[str],
                                        broker_sec_pos_dict: Dict[str, Dict[str, SecPosition | SecPositionBaseModel]]) \
        -> List[BrokerBaseModel]:
    filtered_brokers: List[BrokerBaseModel] = []
    for broker in brokers:
        sec_positions: List[SecPositionBaseModel] = []
        sec_pos_dict: Dict[str, SecPositionBaseModel] = broker_sec_pos_dict[broker.broker]
        for sec_id in sec_id_list:
            if sec_position := sec_pos_dict.get(sec_id):
                sec_positions.append(copy.deepcopy(sec_position))
        if sec_positions:
            updated_broker = BrokerBaseModel(bkr_disable=broker.bkr_disable, broker=broker.broker,
                                             sec_positions=sec_positions)
            filtered_brokers.append(updated_broker)
    return filtered_brokers


def get_both_sym_side_key_from_pair_plan(pair_plan: PairPlan | PairPlanBaseModel | PairPlanOptional) -> str | None:
    key: str | None = None
    if (pair_plan and pair_plan.pair_plan_params and pair_plan.pair_plan_params.plan_leg1 and
            pair_plan.pair_plan_params.plan_leg1.sec and pair_plan.pair_plan_params.plan_leg2 and
            pair_plan.pair_plan_params.plan_leg2.sec):
        key = (f"{pair_plan.pair_plan_params.plan_leg1.sec.sec_id}"
               f"-{pair_plan.pair_plan_params.plan_leg1.side}"
               f"-{pair_plan.pair_plan_params.plan_leg2.sec.sec_id}"
               f"-{pair_plan.pair_plan_params.plan_leg2.side}")
    # else not required - returning None (default value of key)
    return key


def get_reset_log_book_cache_wrapper_pattern():
    return "-~-"
