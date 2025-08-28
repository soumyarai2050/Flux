# standard imports
from functools import lru_cache
from typing import List, Tuple, Dict, Any

# project imports
from FluxPythonUtils.scripts.general_utility_functions import get_symbol_side_pattern
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    PairPlan, PairPlanBaseModel, Side)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_key_handler import (
    EmailBookServiceKeyHandler)


@lru_cache(maxsize=None)
def get_symbol_side_key_from_pair(symbol, side):
    symbol_side_pattern: str = get_symbol_side_pattern()
    key_str = f"symbol-side={symbol}-{Side(side).value}"
    return f"{symbol_side_pattern}{key_str}{symbol_side_pattern}"

def symbol_side_key(symbol: str, side: Side | str) -> str:
    return f"{symbol}-{Side(side).value}"

# @lru_cache(maxsize=None)  # not supported: unhashable type: 'list'
def get_symbol_side_key(symbol_side_tuple_list: List[Tuple[str, Side | str]]) -> str:
    if len(symbol_side_tuple_list) == 1:
        symbol, side = symbol_side_tuple_list[0]
        return get_symbol_side_key_from_pair(symbol, side)
    symbol_side_pattern: str = get_symbol_side_pattern()
    key_str = ",".join([f"symbol-side={symbol_side_key(symbol, side)}" for symbol, side in symbol_side_tuple_list])
    return f"{symbol_side_pattern}{key_str}{symbol_side_pattern}"


pair_plan_id_key: Dict[int, str] = {}  # Used below - in future - consider moving in class static


def get_pair_plan_log_key(pair_plan: PairPlan | PairPlanBaseModel):
    if pair_plan_key := pair_plan_id_key.get(pair_plan.id):
        return pair_plan_key
    else:
        leg_1_sec_id = pair_plan.pair_plan_params.plan_leg1.sec.sec_id
        leg_1_side = pair_plan.pair_plan_params.plan_leg1.side
        if pair_plan.pair_plan_params.plan_leg2 is not None:
            leg_2_sec_id = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
            leg_2_side = pair_plan.pair_plan_params.plan_leg2.side
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side)),
                                                   (leg_2_sec_id, Side(leg_2_side))])
        else:
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side))])
        base_pair_plan_key = EmailBookServiceKeyHandler.get_log_key_from_pair_plan(pair_plan)
        pair_plan_key = f"{symbol_side_key}-{base_pair_plan_key}"
        pair_plan_id_key[pair_plan.id] = pair_plan_key
        return pair_plan_key


def get_pair_plan_dict_log_key(pair_plan_dict: Dict[str, Any]):
    pair_plan_id = pair_plan_dict.get("_id")
    if pair_plan_key := pair_plan_id_key.get(pair_plan_id):
        return pair_plan_key
    else:
        leg_1_sec_id = pair_plan_dict["pair_plan_params"]["plan_leg1"]["sec"]["sec_id"]
        leg_1_side = pair_plan_dict["pair_plan_params"]["plan_leg1"]["side"]
        leg_2_sec_id = None
        if (plan_leg2 := pair_plan_dict["pair_plan_params"].get("plan_leg2")) is not None:
            leg_2_sec_id = plan_leg2["sec"]["sec_id"]
            leg_2_side = plan_leg2.get("side")
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side)), (leg_2_sec_id, Side(leg_2_side))])
        else:
            symbol_side_key = get_symbol_side_key([(leg_1_sec_id, Side(leg_1_side))])
        base_pair_plan_key = f'{leg_1_sec_id}' + '_' + f'{leg_2_sec_id}' + '_' + f'{pair_plan_id}'
        pair_plan_key = f"{symbol_side_key}-{base_pair_plan_key}"
        pair_plan_id_key[pair_plan_id] = pair_plan_key
        return f"{symbol_side_key}"
