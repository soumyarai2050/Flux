from typing import List, Tuple
from pendulum import DateTime
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_symbol_side_snapshot_from_symbol_side(security_id: str, side: str):
    return {"aggregate": [
        {
            "$match": {
                "$and": [
                    {
                        "security.sec_id": security_id
                    },
                    {
                        "side": side
                    }
                ]
            },
        }
    ]}


def get_chore_total_sum_of_last_n_sec(symbol: str, n: int):
    # Model - ChoreSnapshot
    return {"aggregate": [
        {
            "$match": {
                "$expr": {
                    "$gte": [
                        "$create_date_time",
                        {"$dateSubtract": {"startDate": "$$NOW", "unit": "second", "amount": n}}
                    ]
                }
            }
        },
        {
            "$match": {
                "chore_brief.security.sec_id": symbol
            }
        },
        {
            "$setWindowFields": {
                "sortBy": {
                    "create_date_time": 1.0
                },
                "output": {
                    "last_n_sec_total_qty": {
                        "$sum": "$chore_brief.qty",
                        "window": {
                            "range": [
                                -n,
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
            "$sort": {"create_date_time": -1}
        },
        {
            "$limit": 1
        }
    ]}


def get_chore_by_chore_id_filter(chore_id: str):
    return {"aggregate": [
        {
            "$match": {
                "chore_id": chore_id
            }
        }
    ]}


# careful with special chars on regex match !!
def get_chore_of_matching_suffix_chore_id_filter(chore_id_suffix: str, sort: int = 0, limit: int = 0):
    """
    Note: careful with special chars on regex match !!
    :param chore_id_suffix:
    :param sort: 0: no sort, 1 or -1: passed as is to sort param of aggregation, any other number treated as 0 (no sort)
    :param limit: val <= 0: no limit, else number passed as is to aggregate limit parameter
    :return:formatted mongo aggregate query
    """
    regex_chore_id_suffix: str = f".*{chore_id_suffix}$"
    agg_pipeline = {"aggregate": [{
        "$match": {
            "chore.chore_id": {"$regex": regex_chore_id_suffix}
        }
    }
    ]}
    if sort == -1 or sort == 1:
        sort_expr = {
            "$sort": {"_id": sort},
        }
        agg_pipeline["aggregate"].append(sort_expr)
    if limit > 0:
        limit_expr = {
            "$limit": limit
        }
        agg_pipeline["aggregate"].append(limit_expr)
    return agg_pipeline


def get_strat_brief_from_symbol(security_id: str):
    return {"aggregate": [
        {
            "$match": {
                "$or": [
                    {
                        "pair_buy_side_bartering_brief.security.sec_id": {
                            "$eq": security_id
                        }
                    },
                    {
                        "pair_sell_side_bartering_brief.security.sec_id": {
                            "$eq": security_id
                        }
                    }
                ]
            },
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


def get_last_n_sec_first_n_last_barter(symbol: str, last_n_sec: float):
    # Model - LastBarter
    return {"aggregate": [
        {
            "$match": {
                "$expr": {
                    "$gte": [
                        "$exch_time",
                        {"$dateSubtract": {"startDate": "$$NOW", "unit": "second", "amount": last_n_sec}}
                    ]
                }
            }
        },
        {
            "$match": {"symbol_n_exch_id.symbol": symbol}
        },
        {
            "$sort": {"exch_time": -1}
        },
        {
            "$group": {
                "_id": None,
                "first": {"$first": "$$ROOT"},
                "last": {"$last": "$$ROOT"}
            }
        }
    ]}


def get_last_n_sec_total_barter_qty(symbol: str, last_n_sec: float):
    # Model - LastBarter
    return {"aggregate": [
        {
            "$match": {
                "$expr": {
                    "$gte": [
                        "$exch_time",
                        {"$dateSubtract": {"startDate": "$$NOW", "unit": "second", "amount": last_n_sec}}
                    ]
                }
            }
        },
        {
            "$match": {
                "symbol_n_exch_id.symbol": symbol
            }
        },
        {
            # add match for time to reduce
            "$setWindowFields": {
                "sortBy": {
                    "exch_time": 1.0
                },
                "output": {
                    "market_barter_volume.participation_period_last_barter_qty_sum": {
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
        # Sorting in descending chore since limit only takes first n objects
        {
            "$sort": {"exch_time": -1}
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


def get_symbol_overview_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


def get_last_barter_with_symbol_n_start_n_end_time(symbol: str, start_datetime: DateTime, end_datetime: DateTime):
    agg_pipline = {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        },
        {
            "$match": {
                "$and": [
                    {
                        '$expr': {
                            '$gte': [
                                '$time', start_datetime
                            ]
                        }
                    },
                    {
                        '$expr': {
                            '$lte': [
                                '$time', end_datetime
                            ]
                        }
                    }
                ]
            }
        }
    ]}
    return agg_pipline


def get_chore_snapshot_chore_id_filter_json(chore_id: str):
    return {"aggregate": [
        {
            "$match": {
                "chore_brief.chore_id": chore_id
            }
        }
    ]}


def get_chore_snapshot_from_sec_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "chore_brief.security.sec_id": symbol
            }
        }
    ]}


def get_chore_snapshots_by_chore_status_list(chore_status_list: List[str]):
    chore_status_match = []
    for chore_status in chore_status_list:
        chore_status_match.append({"chore_status": chore_status})
    return {"aggregate": [
        {
            "$match": {
                '$or': chore_status_match
            }
        }
    ]}


def get_last_n_chore_journals_from_chore_id(chore_id: str, journal_count: int):
    return {"aggregate": [
        {
            "$match": {
                "chore.chore_id": chore_id
            },
        },
        {
            "$sort": {"_id": -1},
        },
        {
            "$limit": journal_count
        }
    ]}


def get_symbol_side_underlying_account_cumulative_fill_qty(symbol: str, side: str):
    return {"aggregate": [
        {
            '$match': {
                '$and': [
                    {
                        'fill_symbol': symbol
                    },
                    {
                        'fill_side': side
                    }
                ]
            }
        },
        {
            '$setWindowFields': {
                'partitionBy': {
                    'underlying_account': '$underlying_account'
                },
                'sortBy': {
                    'fill_date_time': 1.0
                },
                'output': {
                    'underlying_account_cumulative_fill_qty': {
                        '$sum': '$fill_qty',
                        'window': {
                            'documents': [
                                'unbounded', 'current'
                            ]
                        }
                    }
                }
            }
        },
        {
            "$sort": {"fill_date_time": -1},
        }
    ]}


def get_open_chore_snapshots_for_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "$or": [
                    {
                        "$and": [
                            {
                                "chore_brief.security.sec_id": symbol
                            },
                            {
                                "chore_status": "OE_UNACK"
                            }
                        ]
                    },
                    {
                        "$and": [
                            {
                                "chore_brief.security.sec_id": symbol
                            },
                            {
                                "chore_status": "OE_ACKED"
                            }
                        ]
                    },
                    {
                        "$and": [
                            {
                                "chore_brief.security.sec_id": symbol
                            },
                            {
                                "chore_status": "OE_CXL_UNACK"
                            }
                        ]
                    },
                    {
                        "$and": [
                            {
                                "chore_brief.security.sec_id": symbol
                            },
                            {
                                "chore_status": "OE_AMD_DN_UNACKED"
                            }
                        ]
                    },
                    {
                        "$and": [
                            {
                                "chore_brief.security.sec_id": symbol
                            },
                            {
                                "chore_status": "OE_AMD_UP_UNACKED"
                            }
                        ]
                    }
                ]
            },
        }]}


def get_market_depths(symbol_side_tuple_list: List[Tuple[str, str]]):
    agg_pipeline = {
        "aggregate": [
            {
                '$match': {
                    '$or': [
                        # To be updated based on provided symbol_side_tuple_list
                    ]
                }
            },
            {
                '$match': {
                    '$or': [
                        # To be updated based on provided symbol_side_tuple_list
                    ]
                }
            },
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
                        "$cond": {
                            "if": {"$ne": ["$cumulative_qty", 0]},
                            "then": {"$divide": ["$cumulative_notional", "$cumulative_qty"]},
                            "else": 0
                        }
                    }
                    # "cumulative_avg_px": {
                    #     "$divide": [
                    #         "$cumulative_notional",
                    #         "$cumulative_qty"
                    #     ]
                    # }
                }
            },
            {
                '$sort': {
                    'px': -1
                }
            }
        ]
    }

    symbol_set = set()
    for symbol_side_tuple in symbol_side_tuple_list:
        symbol, side = symbol_side_tuple

        # Adding first match by symbol
        if symbol not in symbol_set:
            agg_pipeline["aggregate"][0]["$match"]["$or"].append({
                "symbol": symbol
            })
        symbol_set.add(symbol)

        # Adding second match with symbol n side
        agg_pipeline["aggregate"][1]["$match"]["$or"].append({
            '$and': [
                {
                    'symbol': symbol
                }, {
                    'side': side
                }
            ]
        })

    return agg_pipeline


# Market Depth cumulative average
cum_px_qty_aggregate_pipeline = {"aggregate": [
    # {
    #     "$setWindowFields": {
    #         "partitionBy": {"symbol": "$symbol", "side": "$side"},
    #         "sortBy": {
    #             "position": 1.0
    #         },
    #         "output": {
    #             "cumulative_notional": {
    #                 "$sum": {
    #                     "$multiply": [
    #                         "$px",
    #                         "$qty"
    #                     ]
    #                 },
    #                 "window": {
    #                     "documents": [
    #                         "unbounded",
    #                         "current"
    #                     ]
    #                 }
    #             },
    #             "cumulative_qty": {
    #                 "$sum": "$qty",
    #                 "window": {
    #                     "documents": [
    #                         "unbounded",
    #                         "current"
    #                     ]
    #                 }
    #             }
    #         }
    #     }
    # },
    # {
    #     "$addFields": {
    #         "cumulative_avg_px": {
    #             "$divide": [
    #                 "$cumulative_notional",
    #                 "$cumulative_qty"
    #             ]
    #         }
    #     }
    # }
]}
