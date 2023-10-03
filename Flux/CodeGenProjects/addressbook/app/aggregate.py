import asyncio
import os
from typing import Tuple

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *

cum_price_size_aggregate_json = {"aggregate": [
    {
        "$setWindowFields": {
            "partitionBy": "$side",
            "sortBy": {
                "_id": 1.0
            },
            "output": {
                "cumulative_avg_price": {
                    "$avg": "$price",
                    "window": {
                        "documents": [
                            "unbounded",
                            "current"
                        ]
                    }
                },
                "cumulative_total_size": {
                    "$sum": "$size",
                    "window": {
                        "documents": [
                            "unbounded",
                            "current"
                        ]
                    }
                }
            }
        }
    }
]}


def get_pair_strat_filter(security_id: str | None = None):
    agg_pipeline = {"aggregate": [
        {
            "$match": {
                "$or": [
                    {
                        "pair_strat_params.strat_leg1.sec.sec_id": {
                            "$eq": security_id
                        }
                    },
                    {
                        "pair_strat_params.strat_leg2.sec.sec_id": {
                            "$eq": security_id
                        }
                    }
                ]
            }
        }
    ]}

    return agg_pipeline


# if __name__ == '__main__':
    # with_symbol_agg_query = get_last_n_sec_orders_by_event("sym-1", 5, "OE_NEW")
    # print(with_symbol_agg_query)
    # without_symbol_agg_query = get_last_n_sec_orders_by_event(None, 5, "OE_NEW")
    # print(without_symbol_agg_query)

    # print(get_limited_portfolio_alerts_obj(5))
    # print(get_limited_strat_alerts_obj(5))
