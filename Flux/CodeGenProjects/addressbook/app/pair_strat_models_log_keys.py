from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import PairStrat, \
    PairStratBaseModel, PairStratOptional
from Flux.CodeGenProjects.addressbook.generated.StratExecutor.strat_manager_service_key_handler import \
    StratManagerServiceKeyHandler
from FluxPythonUtils.scripts.utility_functions import get_symbol_side_key


def get_pair_strat_log_key(pair_strat: PairStrat | PairStratBaseModel | PairStratOptional):
    leg_1_sec_id = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    leg_1_side = pair_strat.pair_strat_params.strat_leg1.side
    if pair_strat.pair_strat_params.strat_leg2 is not None:
        leg_2_sec_id = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        leg_2_side = pair_strat.pair_strat_params.strat_leg2.side
        symbol_side_key = get_symbol_side_key([(leg_1_sec_id, leg_1_side), (leg_2_sec_id, leg_2_side)])
    else:
        symbol_side_key = get_symbol_side_key([(leg_1_sec_id, leg_1_side)])
    base_pair_strat_key = StratManagerServiceKeyHandler.get_log_key_from_pair_strat(pair_strat)
    return f"{symbol_side_key}-{base_pair_strat_key}"
