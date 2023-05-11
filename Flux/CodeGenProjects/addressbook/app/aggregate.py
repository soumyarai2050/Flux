import asyncio
import os
from typing import Tuple

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_beanie_database import get_mongo_server_uri
from FluxPythonUtils.scripts.utility_functions import get_version_from_mongodb_uri

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


def get_order_by_order_id_filter(order_id: str):
    return {"aggregate": [
        {
            "$match": {
                "order_id": order_id
            }
        }
    ]}


def get_open_order_snapshots_by_order_status(order_status_list: List[str]):
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


def get_last_n_sec_orders_by_event(symbol: str | None, last_n_sec: int, order_event: str):
    # Model - order journal
    # Below match aggregation stages are based on max filtering first (stage that filters most gets precedence)
    # since this aggregate is used to count
    # Note: if you change sequence of match stages, don't forget to change hardcoded index number below to add
    # symbol based match aggregation layer
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
    if symbol is not None:
        match_agg = {
            "order.security.sec_id": symbol
        }
        agg_query["aggregate"][1]["$match"] = match_agg
    return agg_query


def get_pydantic_model_to_dict_for_limit_agg(pydentic_obj_dict: Dict):
    for key, value in pydentic_obj_dict.items():
        if isinstance(value, dict):
            get_pydantic_model_to_dict_for_limit_agg(value)
        else:
            pydentic_obj_dict[key] = 1


def get_pydantic_model_to_dict_for_v5_limit_agg(pydentic_obj_dict: Dict):
    for key, value in pydentic_obj_dict.items():
        pydentic_obj_dict[key] = {
            "$first": f"${key}"
        }


def get_limit_n_sort_direction(limit: int) -> Tuple[int, int]:
    if limit < 0:
        limit = -limit  # to make it positive
        sort_direction = -1
    else:
        sort_direction = 1
    return limit, sort_direction


def get_limited_portfolio_alerts_obj_v5(limit: int):
    portfolio_status_obj_dict = PortfolioStatusBaseModel().dict()
    get_pydantic_model_to_dict_for_v5_limit_agg(portfolio_status_obj_dict)
    portfolio_status_obj_dict["_id"] = "$_id"
    # del pydentic_obj_dict["id"]
    portfolio_status_obj_dict["portfolio_alerts"] = {
        "$push": "$portfolio_alerts"
    }

    limit, sort_direction = get_limit_n_sort_direction(limit)
    agg_list = [
        {
            '$unwind': {
                'path': '$portfolio_alerts',
                "preserveNullAndEmptyArrays": True,
            }
        }, {
            '$sort': {
                'portfolio_alerts.last_update_date_time': sort_direction
            }
        }, {
            '$limit': limit
        }, {
            '$group': portfolio_status_obj_dict
        }
    ]
    return agg_list


def get_limited_portfolio_alerts_obj_v6(limit: int):
    portfolio_status_obj = PortfolioStatusBaseModel().dict()
    get_pydantic_model_to_dict_for_limit_agg(portfolio_status_obj)
    limit, sort_direction = get_limit_n_sort_direction(limit)

    portfolio_status_obj["portfolio_alerts"] = {
        "$slice": [
            {"$sortArray": {
                "input": "$portfolio_alerts",
                "sortBy": {
                    "last_update_date_time": sort_direction
                }}},
            limit],
    }
    return [
        {
            "$project": portfolio_status_obj
        }
    ]


def get_limited_portfolio_alerts_obj(limit: int):
    mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
    mongo_version_start_num = mongo_version.split(".")[0]
    if int(mongo_version_start_num) < 6:
        return get_limited_portfolio_alerts_obj_v5(limit)
    else:
        return get_limited_portfolio_alerts_obj_v6(limit)


def get_limited_strat_alerts_obj_v5(limit: int):
    limit, sort_direction = get_limit_n_sort_direction(limit)
    pair_strat_obj_dict_for_grp_agg = PairStratBaseModel().dict()
    pair_strat_obj_dict_for_project_agg = PairStratBaseModel().dict()
    get_pydantic_model_to_dict_for_v5_limit_agg(pair_strat_obj_dict_for_grp_agg)
    pair_strat_obj_dict_for_grp_agg["_id"] = "$_id"
    # del pydentic_obj_dict["id"]
    pair_strat_obj_dict_for_grp_agg["temp_strat_alerts"] = {
        "$push": '$strat_status.strat_alerts'
    }

    get_pydantic_model_to_dict_for_limit_agg(pair_strat_obj_dict_for_project_agg)
    strat_status_dict = StratStatusOptional().dict()
    get_pydantic_model_to_dict_for_limit_agg(strat_status_dict)
    pair_strat_obj_dict_for_project_agg["strat_status"] = strat_status_dict
    pair_strat_obj_dict_for_project_agg["strat_status"]["strat_alerts"] = {
                                            '$slice': [
                                                '$temp_strat_alerts', limit
                                            ]
                                        }

    agg_list = [
        {
            '$unwind': {
                'path': '$strat_status.strat_alerts',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$sort': {
                'strat_status.strat_alerts.last_update_date_time': sort_direction
            }
        }, {
            '$group': pair_strat_obj_dict_for_grp_agg
        }, {
            '$project': pair_strat_obj_dict_for_project_agg
        }
    ]
    return agg_list


def get_limited_strat_alerts_obj_v6(limit: int):
    pair_strat_dict = PairStratBaseModel().dict()
    get_pydantic_model_to_dict_for_limit_agg(pair_strat_dict)
    limit, sort_direction = get_limit_n_sort_direction(limit)

    strat_status_dict = StratStatusOptional().dict()
    get_pydantic_model_to_dict_for_limit_agg(strat_status_dict)
    pair_strat_dict["strat_status"] = strat_status_dict

    pair_strat_dict["strat_status"]["strat_alerts"] = {
        "$slice": [
            {"$sortArray": {
                "input": "$strat_status.strat_alerts",
                "sortBy": {
                    "last_update_date_time": sort_direction
                }}},
            limit],
    }
    return_agg = [
        {
            "$project": pair_strat_dict
        }
    ]
    return return_agg


def get_limited_strat_alerts_obj(limit: int):
    mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
    mongo_version_start_num = mongo_version.split(".")[0]
    if int(mongo_version_start_num) < 6:
        return get_limited_strat_alerts_obj_v5(limit)
    else:
        return get_limited_strat_alerts_obj_v6(limit)


def get_limited_objs(limit: int):
    # used in limit model option
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
                "$limit": -limit  # limit becomes positive (limit agg always accepts +ive argument)
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


if __name__ == '__main__':
    # with_symbol_agg_query = get_last_n_sec_orders_by_event("sym-1", 5, "OE_NEW")
    # print(with_symbol_agg_query)
    # without_symbol_agg_query = get_last_n_sec_orders_by_event(None, 5, "OE_NEW")
    # print(without_symbol_agg_query)

    # print(get_limited_portfolio_alerts_obj(5))
    print(get_limited_strat_alerts_obj(5))
