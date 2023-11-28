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


def get_order_total_sum_of_last_n_sec(symbol: str, n: int):
    # Model - OrderSnapshot
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
                "order_brief.security.sec_id": symbol
            }
        },
        {
            "$setWindowFields": {
                "sortBy": {
                    "create_date_time": 1.0
                },
                "output": {
                    "last_n_sec_total_qty": {
                        "$sum": "$order_brief.qty",
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
        # Sorting in descending order since limit only takes first n objects
        {
            "$sort": {"create_date_time": -1}
        },
        {
            "$limit": 1
        }
    ]}


def get_order_by_order_id_filter(order_id: str):
    return {"aggregate": [
        {
            "$match": {
                "order_id": order_id
            }
        }
    ]}


# careful with special chars on regex match !!
def get_order_of_matching_suffix_order_id_filter(order_id_suffix: str, sort: int = 0, limit: int = 0):
    """
    Note: careful with special chars on regex match !!
    :param order_id_suffix:
    :param sort: 0: no sort, 1 or -1: passed as is to sort param of aggregation, any other number treated as 0 (no sort)
    :param limit: val <= 0: no limit, else number passed as is to aggregate limit parameter
    :return:formatted mongo aggregate query
    """
    regex_order_id_suffix: str = f".*{order_id_suffix}$"
    agg_pipeline = {"aggregate": [{
        "$match": {
            "order.order_id": {"$regex": regex_order_id_suffix}
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
                        "pair_buy_side_trading_brief.security.sec_id": {
                            "$eq": security_id
                        }
                    },
                    {
                        "pair_sell_side_trading_brief.security.sec_id": {
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


def get_last_n_sec_total_trade_qty(symbol: str, last_n_sec: float):
    # Model - LastTrade
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


def get_last_trade_with_symbol_n_start_n_end_time(symbol: str, start_datetime: DateTime, end_datetime: DateTime):
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

def get_order_snapshot_order_id_filter_json(order_id: str):
    return {"aggregate": [
        {
            "$match": {
                "order_brief.order_id": order_id
            }
        }
    ]}


def get_order_snapshot_from_sec_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "order_brief.security.sec_id": symbol
            }
        }
    ]}


def get_order_snapshots_by_order_status_list(order_status_list: List[str]):
    order_status_match = []
    for order_status in order_status_list:
        order_status_match.append({"order_status": order_status})
    return {"aggregate": [
        {
            "$match": {
                '$or': order_status_match
            }
        }
    ]}


def get_last_n_order_journals_from_order_id(order_id: str, journal_count: int):
    return {"aggregate": [
        {
            "$match": {
                "order.order_id": order_id
            },
        },
        {
            "$sort": {"_id": -1},
        },
        {
            "$limit": journal_count
        }
    ]}


def get_last_n_sec_orders_by_event(last_n_sec: int, order_event: str):
    agg_query = {"aggregate": [
        {
            "$match": {
                "$expr": {
                    "$gte": [
                        "$order_event_date_time",
                        {"$dateSubtract": {"startDate": "$$NOW", "unit": "second", "amount": last_n_sec}}
                    ]
                }
            }
        },
        {
            "$match": {},
        },
        {
            "$match": {
                "order_event": order_event
            }
        },

        {
            "$setWindowFields": {
                "sortBy": {
                    "order_event_date_time": 1.0
                },
                "output": {
                    "current_period_order_count": {
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
        # Sorting in descending order since limit only takes first n objects
        {
            "$sort": {"order_event_date_time": -1}
        },
        {
            "$limit": 1
        }
    ]}
    return agg_query


def get_last_n_sec_orders_by_event_n_symbol(symbol: str | None, last_n_sec: int, order_event: str):
    # Model - order journal
    # Below match aggregation stages are based on max filtering first (stage that filters most gets precedence)
    # since this aggregate is used to count
    # Note: if you change sequence of match stages, don't forget to change hardcoded index number below to add
    # symbol based match aggregation layer
    agg_query = get_last_n_sec_orders_by_event(last_n_sec, order_event)
    if symbol is not None:
        match_agg = {
            "order.security.sec_id": symbol
        }
        agg_query["aggregate"][1]["$match"] = match_agg
    return agg_query


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


def get_open_order_snapshots_for_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "$or": [
                    {
                        "$and": [
                            {
                                "order_brief.security.sec_id": symbol
                            },
                            {
                                "order_status": "OE_UNACK"
                            }
                        ]
                    },
                    {
                        "$and": [
                            {
                                "order_brief.security.sec_id": symbol
                            },
                            {
                                "order_status": "OE_ACKED"
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
