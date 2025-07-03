# standard imports
import logging
from typing import Dict, Callable, Any

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_shared_memory_consumer import SymbolCache
from FluxPythonUtils.scripts.general_utility_functions import parse_to_float


class AlgoHandler:
    # todo: refactor when adding more algo(s)

    @classmethod
    def handle_sniper_algo(cls, new_chore_obj: NewChore, symbol_cache: SymbolCache, algo_params: Dict[str, str]):
        target_px = algo_params.get("target_px")
        if target_px is None:
            logging.error("Can't find target_px in algo_params")
            return False
        else:
            target_px = parse_to_float(target_px)

        # if aggressive side has matching px
        if new_chore_obj.side == Side.BUY:
            if symbol_cache.top_of_book.ask_quote.px == target_px:
                return True
            # else not required: returning False if not suitable market status
        else:
            if symbol_cache.top_of_book.bid_quote.px == target_px:
                return True
            # else not required: returning False if not suitable market status
        return False

    @classmethod
    def get_algo_handler_by_name(cls, algo_name: str) -> Callable[..., Any] | None:
        if algo_name == "sniper":
            return cls.handle_sniper_algo
        return None

    @classmethod
    def should_tigger_chore(cls, new_chore_obj: NewChore, symbol_cache: SymbolCache) -> bool:
        algo_handler = cls.get_algo_handler_by_name(new_chore_obj.algo.lower())
        if algo_handler is None:
            logging.error(f"Unsupported algo name: {new_chore_obj.algo}")
            return False
        else:
            try:
                algo_params: Dict[str, str] = {}
                for alo_param in new_chore_obj.algo_params:
                    algo_params[alo_param.param_name] = alo_param.param_val

                if algo_handler(new_chore_obj, symbol_cache, algo_params):
                    return True
                else:
                    return False
            except Exception as e:
                logging.exception(f"algo_handler failed with exception;;; {new_chore_obj=}, {symbol_cache=}, {e=}")
                return False

    def __init__(self):
        pass
