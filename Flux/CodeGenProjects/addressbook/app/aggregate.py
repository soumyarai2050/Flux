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


def get_pair_strat_sec_filter_json(security_id: str):
    return {"aggregate": [
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
            },
        }
    ]}

def get_order_snapshot_order_id_filter_json(order_id: str):
    return {"aggregate": [
        {
            "$match": {
                "order_brief.order_id": order_id
            }
        }
    ]}
