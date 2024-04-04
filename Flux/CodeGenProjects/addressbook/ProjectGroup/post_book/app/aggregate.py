from typing import List, Dict, Any
import os

os.environ["DBType"] = "beanie"
# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_open_chore_counts():
    return {"aggregate": [
        {
            "$match": {
                "$or": [
                    {
                        "chore_status": "OE_ACKED"
                    },
                    {
                        "chore_status": "OE_UNACK"
                    }
                ]
            },
        }]}


def get_last_n_sec_chores_by_events(last_n_sec: int, chore_event_list: List[str]):
    agg_query: Dict[str, Any] = {"aggregate": [
        {
            "$match": {
                "$expr": {
                    "$gte": [
                        "$chore_event_date_time",
                        {"$dateSubtract": {"startDate": "$$NOW", "unit": "second", "amount": last_n_sec}}
                    ]
                }
            }
        },
        {
            "$match": {},
        },
        {
            "$match": {},
        },

        {
            "$setWindowFields": {
                "sortBy": {
                    "chore_event_date_time": 1.0
                },
                "output": {
                    "current_period_chore_count": {
                        "$count": {},
                        "window": {
                            "range": [
                                -last_n_sec,
                                "current"
                            ],
                            "unit": "second"
                        }
                    }
                }
            }
        },
        # Sorting in descending chore since limit only takes first n objects
        {
            "$sort": {"chore_event_date_time": -1}
        },
        {
            "$limit": 1
        }
    ]}

    if len(chore_event_list) == 1:
        agg_query["aggregate"][2]["$match"] = {"chore_event": chore_event_list[0]}
    else:
        agg_query["aggregate"][2]["$match"] = {"$or": []}
        for chore_event in chore_event_list:
            agg_query["aggregate"][2]["$match"]["$or"].append({"chore_event": chore_event})
    return agg_query


def get_last_n_sec_chores_by_event_n_symbol(symbol: str | None, last_n_sec: int, chore_event: str):
    # Model - chore journal
    # Below match aggregation stages are based on max filtering first (stage that filters most gets precedence)
    # since this aggregate is used to count
    # Note: if you change sequence of match stages, don't forget to change hardcoded index number below to add
    # symbol based match aggregation layer
    agg_query = get_last_n_sec_chores_by_events(last_n_sec, [chore_event])
    if symbol is not None:
        match_agg = {
            "chore.security.sec_id": symbol
        }
        agg_query["aggregate"][1]["$match"] = match_agg
    return agg_query
