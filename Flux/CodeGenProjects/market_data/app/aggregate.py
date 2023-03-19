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


def get_pair_side_brief_from_side(symbol: str):  # NOQA
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


def get_max_market_depth_obj(symbol: str, side: str):  # NOQA
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


def get_last_n_sec_total_qty(symbol: str, last_n_sec: float):  # NOQA
    return {"aggregate": [
        {
            "$setWindowFields": {
                "partitionBy": {
                    "symbol": f"$symbol"
                },
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
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


def get_top_of_book_from_symbol(symbol: str):  # NOQA
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


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
