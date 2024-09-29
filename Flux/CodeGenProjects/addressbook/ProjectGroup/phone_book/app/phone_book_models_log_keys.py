# standard imports
from typing import List, Tuple, Dict, Any

# project imports
from FluxPythonUtils.scripts.utility_functions import get_symbol_side_pattern
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import (
    PairStrat, PairStratBaseModel, PairStratOptional, Side)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_key_handler import (
    EmailBookServiceKeyHandler)


def get_symbol_side_key(symbol_side_tuple_list: List[Tuple[str, Side]]) -> str:
    symbol_side_pattern: str = get_symbol_side_pattern()
    key_str = ",".join([f"symbol-side={symbol}-{side.value}" for symbol, side in symbol_side_tuple_list])
    return f"{symbol_side_pattern}{key_str}{symbol_side_pattern}"


pair_strat_id_key: Dict[int, str] = {}  # Used below - in future - consider moving in class static


def get_pair_strat_log_key(pair_strat: PairStrat | PairStratBaseModel | PairStratOptional):
    if pair_strat_key := pair_strat_id_key.get(pair_strat.id):
        return pair_strat_key
    else:
        leg_1_sec_id = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        leg_1_side = pair_strat.pair_strat_params.strat_leg1.side
        if pair_strat.pair_strat_params.strat_leg2 is not None:
            leg_2_sec_id = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            leg_2_side = pair_strat.pair_strat_params.strat_leg2.side
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side)),
                                                   (leg_2_sec_id, Side(leg_2_side))])
        else:
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side))])
        base_pair_strat_key = EmailBookServiceKeyHandler.get_log_key_from_pair_strat(pair_strat)
        pair_strat_key = f"{symbol_side_key}-{base_pair_strat_key}"
        pair_strat_id_key[pair_strat.id] = pair_strat_key
        return pair_strat_key


def get_pair_strat_dict_log_key(pair_strat_dict: Dict[str, Any]):
    pair_strat_id = pair_strat_dict.get("_id")
    if pair_strat_key := pair_strat_id_key.get(pair_strat_id):
        return pair_strat_key
    else:
        leg_1_sec_id = pair_strat_dict["pair_strat_params"]["strat_leg1"]["sec"]["sec_id"]
        leg_1_side = pair_strat_dict["pair_strat_params"]["strat_leg1"]["side"]
        leg_2_sec_id = None
        if (strat_leg2 := pair_strat_dict["pair_strat_params"].get("strat_leg2")) is not None:
            leg_2_sec_id = strat_leg2["sec"]["sec_id"]
            leg_2_side = strat_leg2.get("side")
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side)), (leg_2_sec_id, Side(leg_2_side))])
        else:
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side))])
        base_pair_strat_key = f'{leg_1_sec_id}' + '_' + f'{leg_2_sec_id}' + '_' + f'{pair_strat_id}'
        pair_strat_key = f"{symbol_side_key}-{base_pair_strat_key}"
        pair_strat_id_key[pair_strat_id] = pair_strat_key
        return f"{symbol_side_key}"
