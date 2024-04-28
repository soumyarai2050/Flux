import logging
from pathlib import PurePath
from fastapi.encoders import jsonable_encoder
import time

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_strat_key_from_pair_strat)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    CURRENT_PROJECT_DIR as PAIR_STRAT_ENGINE_DIR, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import *

PAIR_STRAT_ENGINE_DATA_DIR: PurePath = PAIR_STRAT_ENGINE_DIR / "data"
PAIR_STRAT_ENGINE_LOG_DIR: PurePath = PAIR_STRAT_ENGINE_DIR / "log"


def get_strat_collection() -> StratCollectionBaseModel:
    try:
        strat_collection_list: List[StratCollectionBaseModel] = (
            email_book_service_http_client.get_all_strat_collection_client())
        if strat_collection_list:
            if len(strat_collection_list) > 1:
                err_str_ = (f"Unexpected: multiple strat collection obj found, expected 1;;;"
                            f"{strat_collection_list=}")
                raise Exception(err_str_)
            else:
                strat_collection_obj: StratCollectionBaseModel = strat_collection_list[0]
                return strat_collection_obj
        else:
            err_str_ = f"No strat collection obj found"
            raise Exception(err_str_)
    except Exception as e:
        logging.error(e)
        raise e


def unload_strat(strat_id: int, force: bool = False):
    pair_strat_obj: PairStratBaseModel = email_book_service_http_client.get_pair_strat_client(strat_id)
    strat_key: str = get_strat_key_from_pair_strat(pair_strat_obj)
    # pause all active strat and force it to DONE
    if pair_strat_obj.strat_state == StratState.StratState_ACTIVE:
        if not force:
            err_str_ = ("unload_strat failed, cannot unload strat in ACTIVE state. Force trigger script to unload "
                        "running strat")
            logging.error(err_str_)
            raise Exception(err_str_)

        pair_strat_obj = email_book_service_http_client.patch_pair_strat_client(
            jsonable_encoder(PairStratBaseModel(id=strat_id, strat_state=StratState.StratState_PAUSED),
                             by_alias=True, exclude_none=True))
        time.sleep(5)

    if pair_strat_obj.strat_state in [StratState.StratState_PAUSED, StratState.StratState_ERROR]:
        pair_strat_obj = email_book_service_http_client.patch_pair_strat_client(
            jsonable_encoder(PairStratBaseModel(id=strat_id, strat_state=StratState.StratState_DONE),
                             by_alias=True, exclude_none=True))
        time.sleep(5)

    strat_collection_obj: StratCollectionBaseModel = get_strat_collection()
    loaded_strat_key: str
    for loaded_strat_key in strat_collection_obj.loaded_strat_keys:
        if loaded_strat_key == strat_key:
            # strat found to unload
            updated_strat_collection_obj: StratCollectionBaseModel = deepcopy(strat_collection_obj)
            updated_strat_collection_obj.loaded_strat_keys.remove(strat_key)
            updated_strat_collection_obj.buffered_strat_keys.append(strat_key)
            email_book_service_http_client.put_strat_collection_client(updated_strat_collection_obj)
            break
    else:
        err_str_ = f"No loaded strat found with {strat_id=} in strat_collection;;;{strat_collection_obj=}"
        logging.error(err_str_)
        raise Exception(err_str_)


def recycle_strat(strat_id: int, force: bool = False):
    pair_strat_obj: PairStratBaseModel = email_book_service_http_client.get_pair_strat_client(strat_id)
    strat_key: str = get_strat_key_from_pair_strat(pair_strat_obj)
    unload_strat(strat_id, force)
    time.sleep(5)

    strat_collection_obj: StratCollectionBaseModel = get_strat_collection()
    updated_strat_collection_obj: StratCollectionBaseModel = deepcopy(strat_collection_obj)
    updated_strat_collection_obj.loaded_strat_keys.append(strat_key)
    updated_strat_collection_obj.buffered_strat_keys.remove(strat_key)
    email_book_service_http_client.put_strat_collection_client(updated_strat_collection_obj)
