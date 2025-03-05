# standard imports
import logging
from pathlib import PurePath
import time

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    CURRENT_PROJECT_DIR as PAIR_STRAT_ENGINE_DIR, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from FluxPythonUtils.scripts.general_utility_functions import YAMLConfigurationManager, add_logging_levels

PAIR_STRAT_ENGINE_DATA_DIR: PurePath = PAIR_STRAT_ENGINE_DIR / "data"
PAIR_STRAT_ENGINE_LOG_DIR: PurePath = PAIR_STRAT_ENGINE_DIR / "log"
config_yaml_path = PurePath(__file__).parent.parent / "data" / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
custom_log_lvls = config_yaml_dict.get("custom_logger_lvls")
add_logging_levels([] if custom_log_lvls is None else custom_log_lvls)


def unload_plan(plan_id: int, force: bool = False):
    pair_plan_obj: PairPlanBaseModel = email_book_service_http_client.get_pair_plan_client(plan_id)
    active_plan: bool = pair_plan_obj.plan_state not in [PlanState.PlanState_SNOOZED, PlanState.PlanState_READY]
    # pause all active plan and force it to DONE
    if pair_plan_obj.plan_state == PlanState.PlanState_ACTIVE:
        if not force:
            err_str_ = ("unload_plan failed, cannot unload plan in ACTIVE state. Force trigger script to unload "
                        "running plan")
            logging.error(err_str_)
            raise Exception(err_str_)

        pair_plan_obj = email_book_service_http_client.patch_pair_plan_client(
            {'_id': plan_id, 'plan_state': PlanState.PlanState_PAUSED})
        time.sleep(5)

    if pair_plan_obj.plan_state in [PlanState.PlanState_PAUSED, PlanState.PlanState_ERROR]:
        pair_plan_obj = email_book_service_http_client.patch_pair_plan_client(
            {'_id': plan_id, 'plan_state': PlanState.PlanState_DONE})
        time.sleep(5)

    email_book_service_http_client.unload_plan_from_plan_id_query_client(plan_id)
    market: Market = Market(MarketID.IN)
    if not market.is_test_run and not market.is_sanity_test_run:
        # remove plan lock files if no chores found
        delete_plan_lock_files_if_no_barters(plan_id, active_plan)


def recycle_plan(plan_id: int, force: bool = False):
    unload_plan(plan_id, force)
    time.sleep(2)
    email_book_service_http_client.reload_plan_from_plan_id_query_client(plan_id)


def delete_plan_lock_files_if_no_barters(plan_id: int, active_plan: bool = True):
    pass
