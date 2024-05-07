# standard imports
from typing import List, Tuple

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import PairStrat, \
    PairStratBaseModel, PairStratOptional
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_key_handler import \
    EmailBookServiceKeyHandler
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import Side


def get_symbol_side_pattern():
    return "%%"


def get_symbol_side_key(symbol_side_tuple_list: List[Tuple[str, Side]]) -> str:
    symbol_side_pattern: str = get_symbol_side_pattern()
    key_str = ",".join([f"symbol-side={symbol}-{side.value}" for symbol, side in symbol_side_tuple_list])
    return f"{symbol_side_pattern}{key_str}{symbol_side_pattern}"


def get_pair_strat_log_key(pair_strat: PairStrat | PairStratBaseModel | PairStratOptional):
    leg_1_sec_id = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    leg_1_side = pair_strat.pair_strat_params.strat_leg1.side
    if pair_strat.pair_strat_params.strat_leg2 is not None:
        leg_2_sec_id = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        leg_2_side = pair_strat.pair_strat_params.strat_leg2.side
        symbol_side_key = get_symbol_side_key([(leg_1_sec_id, leg_1_side), (leg_2_sec_id, leg_2_side)])
    else:
        symbol_side_key = get_symbol_side_key([(leg_1_sec_id, leg_1_side)])
    base_pair_strat_key = EmailBookServiceKeyHandler.get_log_key_from_pair_strat(pair_strat)
    return f"{symbol_side_key}-{base_pair_strat_key}"
