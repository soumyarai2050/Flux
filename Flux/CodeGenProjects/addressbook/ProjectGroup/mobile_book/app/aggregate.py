from pendulum import DateTime
from typing import List


def get_symbol_overview_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


def get_limited_objs(limit: int):
    if limit > mobile_book:
        return [
            {
                "$limit": limit
            }
        ]
    elif limit < mobile_book:
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


# Market Depth cumulative average
cum_px_qty_aggregate_pipeline = {"aggregate": []}
