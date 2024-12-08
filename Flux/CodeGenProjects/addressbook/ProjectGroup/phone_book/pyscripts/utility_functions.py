# standard imports
import logging
from pathlib import PurePath
import time

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    CURRENT_PROJECT_DIR as PAIR_STRAT_ENGINE_DIR, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, add_logging_levels

PAIR_STRAT_ENGINE_DATA_DIR: PurePath = PAIR_STRAT_ENGINE_DIR / "data"
PAIR_STRAT_ENGINE_LOG_DIR: PurePath = PAIR_STRAT_ENGINE_DIR / "log"
config_yaml_path = PurePath(__file__).parent.parent / "data" / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
custom_log_lvls = config_yaml_dict.get("custom_logger_lvls")
add_logging_levels([] if custom_log_lvls is None else custom_log_lvls)


def unload_strat(strat_id: int, force: bool = False):
    pair_strat_obj: PairStratBaseModel = email_book_service_http_client.get_pair_strat_client(strat_id)
    active_strat: bool = pair_strat_obj.strat_state not in [StratState.StratState_SNOOZED, StratState.StratState_READY]
    # pause all active strat and force it to DONE
    if pair_strat_obj.strat_state == StratState.StratState_ACTIVE:
        if not force:
            err_str_ = ("unload_strat failed, cannot unload strat in ACTIVE state. Force trigger script to unload "
                        "running strat")
            logging.error(err_str_)
            raise Exception(err_str_)

        pair_strat_obj = email_book_service_http_client.patch_pair_strat_client(
            {'_id': strat_id, 'strat_state': StratState.StratState_PAUSED})
        time.sleep(5)

    if pair_strat_obj.strat_state in [StratState.StratState_PAUSED, StratState.StratState_ERROR]:
        pair_strat_obj = email_book_service_http_client.patch_pair_strat_client(
            {'_id': strat_id, 'strat_state': StratState.StratState_DONE})
        time.sleep(5)

    email_book_service_http_client.unload_strat_from_strat_id_query_client(strat_id)
    market: Market = Market(MarketID.IN)
    if not market.is_test_run and not market.is_sanity_test_run:
        # remove strat lock files if no chores found
        delete_strat_lock_files_if_no_barters(strat_id, active_strat)


def recycle_strat(strat_id: int, force: bool = False):
    unload_strat(strat_id, force)
    time.sleep(2)
    email_book_service_http_client.reload_strat_from_strat_id_query_client(strat_id)


def delete_strat_lock_files_if_no_barters(strat_id: int, active_strat: bool = True):
    pass
