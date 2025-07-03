from pendulum import DateTime
from typing import List
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_symbol_overview_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


def get_limited_objs(limit: int):
    if limit > 0:
        return [
            {
                "$limit": limit
            }
        ]
    elif limit < 0:
        return [
            {
                "$sort": {"_id": -1},
            },
            {
                "$limit": -limit
            }
        ]
    else:
        return []


def get_symbol_interest_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


# Market Depth cumulative average
cum_px_qty_aggregate_pipeline = {"aggregate": []}
