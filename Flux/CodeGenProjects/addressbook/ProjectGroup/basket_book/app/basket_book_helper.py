import logging
from pathlib import PurePath
import polars as pl

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_client import (
    BasketBookServiceHttpClient)
from FluxPythonUtils.scripts.general_utility_functions import YAMLConfigurationManager, parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager, SecurityRecord

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

be_host, be_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))
be_view_port = parse_to_int(config_yaml_dict.get("view_port"))

basket_book_service_http_view_client = \
    BasketBookServiceHttpClient.set_or_get_if_instance_exists(be_host, be_port, view_port=be_view_port)
basket_book_service_http_main_client = \
    BasketBookServiceHttpClient.set_or_get_if_instance_exists(be_host, be_port)

if config_yaml_dict.get("use_view_clients"):
    basket_book_service_http_client = basket_book_service_http_view_client
else:
    basket_book_service_http_client = basket_book_service_http_main_client

def is_all_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            email_book_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            basket_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of phone_book and basket executor;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def is_all_view_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            email_book_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            basket_book_service_http_view_client.get_all_ui_layout_client())

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
    new_chore_list: List[NewChore] = get_new_chores_from_pl_df(pl_df, figi_to_sec_rec_dict)

    if 0 < len(new_chore_list):
        basket_chore_dict: Dict = BasketChore.from_kwargs(new_chores=new_chore_list).to_dict()
        # additional conversion as get_new_chores_from_pl_df returns NewChore and BasketChoreBaseModel requires
        # NewChoreBaseModel (read_n_create_parquet_chores is used by external utility - should be okay)
        basket_chore: BasketChoreBaseModel = BasketChoreBaseModel.from_dict(basket_chore_dict)
        # assumes basket executor server is running and service is ready before this test is started
        created_basket_chore = basket_book_service_http_client.create_basket_chore_client(basket_chore)
        logging.info(f"{created_basket_chore=}")


def get_new_chores_from_pl_df(pl_df: pl.DataFrame, figi_to_sec_rec_dict: Dict[str, SecurityRecord]) -> List[NewChore]:
    new_chore_list: List[NewChore] = []
    for row_df in pl_df.rows(named=True):
        pl.Config.set_tbl_hide_dataframe_shape(True)
        pl.Config.set_tbl_formatting("NOTHING")
        pl.Config.set_tbl_hide_column_data_types(True)
        if figi_or_ticker := row_df.get("figi_or_ticker"):
            mplan = row_df.get("mplan")
            px = row_df.get("limit_price")
            # don't let chores without barter qty through
            if (barter_qty := row_df.get("barter_qty")) and 0 != int(barter_qty):
                qty: int = int(barter_qty)
                abs_qty: int = abs(qty)
                side: Side = Side.BUY if qty > 0 else Side.SELL
                participation_ratio: float = row_df.get("participation_ratio")
                pov: int | None = int(participation_ratio * 100) if participation_ratio else None
                if 0 >= pov:
                    logging.error(f"dropping df chore {row_df=} mandatory field {participation_ratio=} invalid")
                    continue

                algo: str = row_df.get("chore_type_or_algo")
                new_chore_obj: NewChore
                if figi_to_sec_rec_dict.get(figi_or_ticker) is not None:  # figi is set
                    security: Security = (
                        Security.from_kwargs(sec_id=figi_or_ticker, sec_id_source=SecurityIdSource.FIGI))
                    new_chore_obj = NewChore.from_kwargs(security=security, side=side, qty=abs_qty, pov=pov, algo=algo)
                else:  # ticker is set
                    new_chore_obj = NewChore.from_kwargs(ticker=figi_or_ticker, side=side, qty=abs_qty,
                                                         pov=pov, algo=algo)
                if px is not None:
                    new_chore_obj.px = float(px)
                if mplan is not None:
                    new_chore_obj.mplan = str(mplan).upper()
                new_chore_list.append(new_chore_obj)
            else:
                logging.error(f"dropping df chore {row_df=} mandatory field {barter_qty=} invalid")
        else:
            logging.error(f"dropping df chore {row_df=} mandatory field {figi_or_ticker=} invalid")
    return new_chore_list


def capped_by_size_text(text_: str) -> str:
    truncated_text = text_
    text_len: int = len(text_)
    if text_len > 2048:
        truncated_text = text_[:2048]
        truncated_text = (f"Truncated text len from {len(text_)} to 2048, truncated text in detail;;;"
                          f"{truncated_text=}")
    return truncated_text