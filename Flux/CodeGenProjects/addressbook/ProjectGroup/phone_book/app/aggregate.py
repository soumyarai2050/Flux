import os

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
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

# used to test update_aggregate feature
sample_cum_aggregate_pipeline = {"aggregate": [
    {
        "$setWindowFields": {
            "sortBy": {
                "_id": 1.0
            },
            "output": {
                "cum_sum_of_num": {
                    "$sum": "$num",
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


def get_ongoing_or_all_pair_strats_by_sec_id(sec_id: str, side: str):
    """
    pipeline to return all pair_strats that are ongoing or if no ongoing is found then return all pair_strats with
    sec_id of any leg as passed value
    """
    agg_pipeline = {
        "aggregate": [
            {
                '$match': {
                    '$or': [
                        {
                            '$and': [
                                {
                                    'pair_strat_params.strat_leg1.sec.sec_id': {
                                        '$eq': sec_id
                                    }
                                }, {
                                    'pair_strat_params.strat_leg1.side': {
                                        '$eq': side
                                    }
                                }
                            ]
                        }, {
                            '$and': [
                                {
                                    'pair_strat_params.strat_leg2.sec.sec_id': {
                                        '$eq': sec_id
                                    }
                                }, {
                                    'pair_strat_params.strat_leg2.side': {
                                        '$eq': side
                                    }
                                }
                            ]
                        }
                    ]
                }
            }, {
                '$facet': {
                    'matchedDocs': [
                        {
                            '$match': {
                                '$or': [
                                    {
                                        'strat_state': {
                                            '$eq': 'StratState_ACTIVE'
                                        }
                                    }, {
                                        'strat_state': {
                                            '$eq': 'StratState_PAUSED'
                                        }
                                    }, {
                                        'strat_state': {
                                            '$eq': 'StratState_ERROR'
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    'allDocs': [
                        {
                            '$match': {}
                        }
                    ]
                }
            }, {
                '$addFields': {
                    'finalDocs': {
                        '$cond': {
                            'if': {
                                '$gt': [
                                    {
                                        '$size': '$matchedDocs'
                                    }, 0
                                ]
                            },
                            'then': '$matchedDocs',
                            'else': '$allDocs'
                        }
                    }
                }
            }, {
                '$unwind': {
                    'path': '$finalDocs'
                }
            }, {
                '$group': {
                    '_id': '$finalDocs'
                }
            }, {
                '$replaceRoot': {
                    'newRoot': '$_id'
                }
            }
        ]
    }
    return agg_pipeline


def get_ongoing_pair_strat_filter(security_id: str | None = None):
    agg_pipeline = {"aggregate": [
        {
            "$match": {}
        },
        {
            "$match": {
                "$or": [
                    {
                        "strat_state": {
                            "$eq": "StratState_ACTIVE"
                        }
                    },
                    {
                        "strat_state": {
                            "$eq": "StratState_PAUSED"
                        }
                    },
                    {
                        "strat_state": {
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


def get_all_pair_strat_from_symbol_n_side(sec_id: str, side: Side):
    agg_pipeline = {
        "aggregate": [
            {
                "$match": {
                    "$and": [
                        {
                            "$or": [
                                {
                                    "$and": [
                                        {
                                            "pair_strat_params.strat_leg1.sec.sec_id": {
                                                "$eq": sec_id
                                            }
                                        },
                                        {
                                            "pair_strat_params.strat_leg1.side": {
                                                "$eq": side
                                            }
                                        }
                                    ]
                                },
                                {
                                    "$and": [
                                        {
                                            "pair_strat_params.strat_leg2.sec.sec_id": {
                                                "$eq": sec_id
                                            }
                                        },
                                        {
                                            "pair_strat_params.strat_leg2.side": {
                                                "$eq": side
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "is_executor_running": {
                                "$eq": True
                            }
                        }
                    ]
                }
            }
        ]
    }
    return agg_pipeline


# if __name__ == '__main__':
    # with_symbol_agg_query = get_last_n_sec_chores_by_event("sym-1", 5, "OE_NEW")
    # print(with_symbol_agg_query)
    # without_symbol_agg_query = get_last_n_sec_chores_by_event(None, 5, "OE_NEW")
    # print(without_symbol_agg_query)

    # print(get_limited_portfolio_alerts_obj(5))
    # print(get_limited_strat_alerts_obj(5))
