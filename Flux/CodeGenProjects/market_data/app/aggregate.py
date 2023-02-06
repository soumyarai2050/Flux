# Market Depth cumulative average
cum_px_qty_aggregate_query = {"aggregate": [
    {
        "$setWindowFields": {
            "partitionBy": {"symbol": "$symbol", "side": "$side"},
            "sortBy": {
                "position": 1.0
            },
            "output": {
                "cumulative_avg_px": {
                    "$avg": {"$multiply": ["$px", "$qty"]},
                    "window": {
                        "documents": [
                            "unbounded",
                            "current"
                        ]
                    }
                },
                "cumulative_total_qty": {
                    "$sum": "$qty",
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


# Last n sec average px and total size (last n sec from every document)
last_n_sec_tick_by_tick_all_last_agg_query = {"aggregate": [
    {
        "$setWindowFields": {
            "partitionBy": {
                "symbol": "$symbol",
                "tick_type": "$tick_type"
            },
            "sortBy": {
                "time": 1.0
            },
            "output": {
                "last_n_sec_avg_px": {
                    "$avg": {"$multiply": ["$px", "$qty"]},
                    "window": {
                        "range": [
                            -10.0,
                            "current"
                        ],
                        "unit": "second"
                    }
                },
                "last_n_sec_total_qty": {
                    "$sum": "$qty",
                    "window": {
                        "range": [
                            -10.0,
                            "current"
                        ],
                        "unit": "second"
                    }
                }
            }
        }
    }
]}

# {
#     "$merge": {
#         "into": "MarketDepth",
#         "on": "_id",
#         "whenMatched": "replace",
#         "whenNotMatched": "insert"
#     }
# }
# {
#     "$out": {
#         "db": "market_data_tech_new_test",
#         "coll": "MarketDepth"
#     }
# }