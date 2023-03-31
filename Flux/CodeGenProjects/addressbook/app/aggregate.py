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


def get_ongoing_pair_strat_filter(security_id: str | None = None):
    agg_pipeline = {"aggregate": [
        {
            "$match": {}
        },
        {
            "$match": {
                "$or": [
                    {
                        "strat_status.strat_state": {
                            "$eq": "StratState_ACTIVE"
                        }
                    },
                    {
                        "strat_status.strat_state": {
                            "$eq": "StratState_PAUSED"
                        }
                    },
                    {
                        "strat_status.strat_state": {
                            "$eq": "StratState_ERROR"
                        }
                    }
                ]
            },
        }
    ]}

    if security_id is not None:
        agg_pipeline["aggregate"][0]["$match"] = {
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
    return {"aggregate": [
        {
            "$match": {
                "order_brief.security.sec_id": symbol
            }
        },
        {
            "$setWindowFields": {
                "sortBy": {
                    "last_update_date_time": 1.0
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
        }
    ]}


# careful with special chars on regex match !!
def get_order_of_matching_suffix_order_id_filter(order_id_suffix: str):
    regex_order_id_suffix: str = f".*{order_id_suffix}$"
    return {"aggregate": [{
        "$match": {
            "order.order_id": {"$regex": regex_order_id_suffix}
        }
    }
    ]}


def get_cancel_order_by_order_id_filter(order_id: str):
    return {"aggregate": [
        {
            "$match": {
                "order_id": order_id
            }
        }
    ]}


def get_open_order_snapshots_by_order_status(order_status: str):
    return {"aggregate": [
        {
            "$match": {
                "order_status": order_status
            }
        }
    ]}


def get_last_n_sec_orders_by_event(symbol: str | None, last_n_sec: int, order_event: str):
    agg_query = {"aggregate": [
        {
            "$match": {},
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
        }
    ]}
    if symbol is not None:
        match_agg = {
            "$and": [
                {
                    "order.security.sec_id": symbol
                },
                {
                    "order_event": order_event
                }
            ]
        }
    else:
        match_agg = {"order_event": order_event}
    agg_query["aggregate"][0]["$match"] = match_agg
    return agg_query


def get_limited_portfolio_alerts_obj(limit: int):
    return [
        {
            "$project": {
                "kill_switch": 1,
                "portfolio_alerts": {
                    "$reverseArray": {"$slice": ["$portfolio_alerts", limit]},
                },
                "overall_buy_notional": 1,
                "overall_sell_notional": 1,
                "overall_buy_fill_notional": 1,
                "overall_sell_fill_notional": 1,
                "current_period_available_buy_order_count": 1,
                "current_period_available_sell_order_count": 1,
                "id": 1
            }
        }
    ]


def get_limited_strat_alerts_obj(limit: int):
    return [
        {
            "$project": {
                "last_active_date_time": 1,
                "frequency": 1,
                "pair_strat_params": 1,
                "strat_status": {
                    "strat_state": 1,
                    "total_buy_qty": 1,
                    "total_sell_qty": 1,
                    "total_order_qty": 1,
                    "total_open_buy_qty": 1,
                    "total_open_sell_qty": 1,
                    "avg_open_buy_px": 1,
                    "avg_open_sell_px": 1,
                    "total_open_buy_notional": 1,
                    "total_open_sell_notional": 1,
                    "total_open_exposure": 1,
                    "total_fill_buy_qty": 1,
                    "total_fill_sell_qty": 1,
                    "avg_fill_buy_px": 1,
                    "avg_fill_sell_px": 1,
                    "total_fill_buy_notional": 1,
                    "total_fill_sell_notional": 1,
                    "total_fill_exposure": 1,
                    "total_cxl_buy_qty": 1,
                    "total_cxl_sell_qty": 1,
                    "avg_cxl_buy_px": 1,
                    "avg_cxl_sell_px": 1,
                    "total_cxl_buy_notional": 1,
                    "total_cxl_sell_notional": 1,
                    "total_cxl_exposure": 1,
                    "average_premium": 1,
                    "residual": 1,
                    "balance_notional": 1,
                    "strat_alerts": {
                        "$reverseArray": {"$slice": ["$strat_status.strat_alerts", -limit]},
                    }
                },
                "strat_limits": 1,
                "id": 1
            }
        }
    ]


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


def get_open_order_snapshots_for_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "$and": [
                    {
                        "order_brief.security.sec_id": symbol
                    },
                    {
                        "order_status": "OE_ACKED"
                    }
                ]
            },
        }]}


def get_last_3_order_journals_from_order_id(order_id: str):
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
            "$limit": 3
        }
    ]}


def get_symbol_side_underlying_account_cumulative_fill_qty(symbol: str, side: str):
    return {"aggregate": [
        {
            '$match': {
                '$and': [
                    {
                        'fill_symbol': symbol
                    }, {
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


if __name__ == '__main__':
    with_symbol_agg_query = get_last_n_sec_orders_by_event("sym-1", 5, "OE_NEW")
    print(with_symbol_agg_query)
    without_symbol_agg_query = get_last_n_sec_orders_by_event(None, 5, "OE_NEW")
    print(without_symbol_agg_query)
