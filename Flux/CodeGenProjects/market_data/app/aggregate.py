from pendulum import DateTime

# Market Depth cumulative average
cum_px_qty_aggregate_query = {"aggregate": [
    {
        "$setWindowFields": {
            "partitionBy": {"symbol": "$symbol", "side": "$side"},
            "sortBy": {
                "position": 1.0
            },
            "output": {
                "cumulative_notional": {
                    "$sum": {
                        "$multiply": [
                            "$px",
                            "$qty"
                        ]
                    },
                    "window": {
                        "documents": [
                            "unbounded",
                            "current"
                        ]
                    }
                },
                "cumulative_qty": {
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
    },
    {
        "$addFields": {
            "cumulative_avg_px": {
                "$divide": [
                    "$cumulative_notional",
                    "$cumulative_qty"
                ]
            }
        }
    }
]}


def get_pair_side_brief_from_side(symbol: str):
    return {"aggregate": [
        {
            "$unwind": {
                "path": "$pair_side_brief"
            }
        },
        {
            "$match": {
                "pair_side_brief.security.sec_id": symbol
            }
        },
        {
            "$sort": {
                "pair_side_brief.last_update_date_time": -1.0
            }
        }
    ]}


def get_max_market_depth_obj(symbol: str, side: str):
    return {"aggregate": [
        {
            "$match": {
                "$and": [
                    {
                        "symbol": symbol
                    },
                    {
                        "side": side
                    }
                ]
            }
        },
        {
            "$sort": {
                "position": -1.0
            }
        }
    ]}


def get_last_n_sec_total_qty(symbol: str, last_n_sec: float):
    # Model - LastTrade
    return {"aggregate": [
        {
            "$match": {
                "$expr": {
                    "$gte": [
                        "$time",
                        {"$dateSubtract": {"startDate": "$$NOW", "unit": "second", "amount": last_n_sec}}
                    ]
                }
            }
        },
        {
            "$match": {
                "symbol": symbol
            }
        },
        {
            # add match for time to reduce
            "$setWindowFields": {
                "sortBy": {
                    "time": 1.0
                },
                "output": {
                    "market_trade_volume.participation_period_last_trade_qty_sum": {
                        "$sum": "$qty",
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
        # Sorting in descending order since limit only takes first n objects
        {
            "$sort": {"time": -1}
        },
        {
            "$limit": 1
        }
    ]}


def get_objs_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


def get_bar_data_from_symbol_n_start_n_end_datetime(symbol: str, start_datetime: DateTime | None = None,
                                                    end_datetime: DateTime | None = None):
    agg_pipline = {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        },
        {
            "$match": {}
        }
    ]}

    if start_datetime is not None and end_datetime is None:
        agg_pipline["aggregate"][1]["$match"] = {
            '$expr': {
                '$gte': [
                    '$datetime', start_datetime
                ]
            }
        }
    elif end_datetime is not None and start_datetime is None:
        agg_pipline["aggregate"][1]["$match"] = {
            '$expr': {
                '$lte': [
                    '$datetime', end_datetime
                ]
            }
        }
    elif start_datetime is not None and end_datetime is not None:
        agg_pipline["aggregate"][1]["$match"] = {

            "$and": [
                {
                    '$expr': {
                        '$gte': [
                            '$datetime', start_datetime
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lte': [
                            '$datetime', end_datetime
                        ]
                    }
                }
        ]}

    return agg_pipline


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


def get_latest_bar_data_for_each_symbol():
    return {"aggregate": [
        {
            '$group': {
                '_id': '$symbol',
                'doc': {
                    '$max': {
                        '_id': '$_id',
                        'datetime': '$datetime',
                        'symbol': '$symbol'
                    }
                }
            }
        }, {
            '$replaceRoot': {
                'newRoot': '$doc'
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


if __name__ == "__main__":
    import pendulum

    print(get_bar_data_from_symbol_n_start_n_end_datetime("1A0.SI", pendulum.parse("2020-11-13T16:00:00.000+00:00")))
