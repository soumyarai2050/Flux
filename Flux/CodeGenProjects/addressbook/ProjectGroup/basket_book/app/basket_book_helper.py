import logging
from pathlib import PurePath
import polars as pl

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_client import (
    BasketBookServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager, SecurityRecord

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.mobile_book_n_street_book_n_basket_book_core_msgspec_model import *


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

be_host, be_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

basket_book_service_http_client = \
    BasketBookServiceHttpClient.set_or_get_if_instance_exists(be_host, be_port)


def is_all_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            email_book_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            basket_book_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of phone_book and basket executor;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def get_figi_to_sec_rec_dict(static_data: SecurityRecordManager) -> Dict[str, SecurityRecord]:
    figi_sec_rec_dict: Dict[str, SecurityRecord] = {}
    for sec_rec in static_data.barter_ready_records_by_ticker.values():
        if sec_rec.figi is not None and 0 != len(sec_rec.figi):
            figi_sec_rec_dict[sec_rec.figi] = sec_rec
        if sec_rec.secondary_figi is not None and 0 != len(sec_rec.secondary_figi):
            figi_sec_rec_dict[sec_rec.secondary_figi] = sec_rec
    return figi_sec_rec_dict


def read_n_create_parquet_chores(basket_chore_parquet_file_path: str, static_data: SecurityRecordManager):
    figi_to_sec_rec_dict: Dict[str, SecurityRecord] = get_figi_to_sec_rec_dict(static_data)

    pl_df = pl.read_parquet(basket_chore_parquet_file_path)
    pl_df = pl_df.filter(pl.col("create_time") == pl.col("create_time").max())
    new_chore_list = []

    for row_df in pl_df.rows(named=True):
        pl.Config.set_tbl_hide_dataframe_shape(True)
        pl.Config.set_tbl_formatting("NOTHING")
        pl.Config.set_tbl_hide_column_data_types(True)
        if figi := row_df.get("figi"):
            if sec_id := figi_to_sec_rec_dict[figi].ticker:
                if barter_qty := row_df.get("barter_qty"):
                    qty = int(barter_qty)
                    abs_qty = abs(qty)
                    side = Side.BUY if qty > 0 else Side.SELL
                    security: SecurityBaseModel = SecurityBaseModel(sec_id=sec_id, sec_id_source=SecurityIdSource.TICKER)
                    participation_ratio = row_df.get("participation_ratio")
                    pov = int(participation_ratio * 100) if participation_ratio else None
                    algo = row_df.get("chore_type")
                    new_chore_obj = NewChoreBaseModel(security=security, side=side, qty=abs_qty, pov=pov, algo=algo)
                    new_chore_list.append(new_chore_obj)
    if 0 < len(new_chore_list):
        basket_chore = BasketChoreBaseModel(new_chores=new_chore_list)
        # assumes basket executor server is running and service is ready before this test is started
        created_basket_chore = basket_book_service_http_client.create_basket_chore_client(basket_chore)
        logging.info(f"{created_basket_chore=}")
