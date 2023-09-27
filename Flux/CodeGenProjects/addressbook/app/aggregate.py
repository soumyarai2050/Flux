import asyncio
import os
from typing import Tuple

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_beanie_database import \
    get_mongo_server_uri
from FluxPythonUtils.scripts.utility_functions import get_version_from_mongodb_uri
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

#
# def get_limited_portfolio_alerts_obj_v5(limit: int):
#     portfolio_status_obj_dict = PortfolioStatusBaseModel().dict()
#     get_pydantic_model_to_dict_for_v5_limit_agg(portfolio_status_obj_dict)
#     portfolio_status_obj_dict["_id"] = "$_id"
#     # del pydentic_obj_dict["id"]
#     portfolio_status_obj_dict["portfolio_alerts"] = {
#         "$push": "$portfolio_alerts"
#     }
#
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#     agg_list = [
#         {
#             '$unwind': {
#                 'path': '$portfolio_alerts',
#                 "preserveNullAndEmptyArrays": True,
#             }
#         }, {
#             '$sort': {
#                 'portfolio_alerts.last_update_date_time': sort_direction
#             }
#         }, {
#             '$limit': limit
#         }, {
#             '$group': portfolio_status_obj_dict
#         }
#     ]
#     return agg_list
#
#
# def get_limited_portfolio_alerts_obj_v6(limit: int):
#     portfolio_status_obj = PortfolioStatusBaseModel().dict()
#     get_pydantic_model_to_dict_for_limit_agg(portfolio_status_obj)
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#
#     portfolio_status_obj["portfolio_alerts"] = {
#         "$slice": [
#             {"$sortArray": {
#                 "input": "$portfolio_alerts",
#                 "sortBy": {
#                     "last_update_date_time": sort_direction
#                 }}},
#             limit],
#     }
#     return [
#         {
#             "$project": portfolio_status_obj
#         }
#     ]
#
#
# def get_limited_portfolio_alerts_obj(limit: int):
#     mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
#     mongo_version_start_num = mongo_version.split(".")[0]
#     if int(mongo_version_start_num) < 6:
#         return get_limited_portfolio_alerts_obj_v5(limit)
#     else:
#         return get_limited_portfolio_alerts_obj_v6(limit)
#
#
# def get_limited_strat_alerts_obj_v5(limit: int):
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#     pair_strat_obj_dict_for_grp_agg = PairStratBaseModel().dict()
#     pair_strat_obj_dict_for_project_agg = PairStratBaseModel().dict()
#     get_pydantic_model_to_dict_for_v5_limit_agg(pair_strat_obj_dict_for_grp_agg)
#     pair_strat_obj_dict_for_grp_agg["_id"] = "$_id"
#     # del pydentic_obj_dict["id"]
#     pair_strat_obj_dict_for_grp_agg["temp_strat_alerts"] = {
#         "$push": '$strat_status.strat_alerts'
#     }
#
#     get_pydantic_model_to_dict_for_limit_agg(pair_strat_obj_dict_for_project_agg)
#     strat_status_dict = StratStatusOptional().dict()
#     get_pydantic_model_to_dict_for_limit_agg(strat_status_dict)
#     pair_strat_obj_dict_for_project_agg["strat_status"] = strat_status_dict
#     pair_strat_obj_dict_for_project_agg["strat_status"]["strat_alerts"] = {
#                                             '$slice': [
#                                                 '$temp_strat_alerts', limit
#                                             ]
#                                         }
#
#     agg_list = [
#         {
#             '$unwind': {
#                 'path': '$strat_status.strat_alerts',
#                 'preserveNullAndEmptyArrays': True
#             }
#         }, {
#             '$sort': {
#                 'strat_status.strat_alerts.last_update_date_time': sort_direction
#             }
#         }, {
#             '$group': pair_strat_obj_dict_for_grp_agg
#         }, {
#             '$project': pair_strat_obj_dict_for_project_agg
#         }
#     ]
#     return agg_list
#
#
# def get_limited_strat_alerts_obj_v6(limit: int):
#     pair_strat_dict = PairStratBaseModel().dict()
#     get_pydantic_model_to_dict_for_limit_agg(pair_strat_dict)
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#
#     strat_status_dict = StratStatusOptional().dict()
#     get_pydantic_model_to_dict_for_limit_agg(strat_status_dict)
#     pair_strat_dict["strat_status"] = strat_status_dict
#
#     pair_strat_dict["strat_status"]["strat_alerts"] = {
#         "$slice": [
#             {"$sortArray": {
#                 "input": "$strat_status.strat_alerts",
#                 "sortBy": {
#                     "last_update_date_time": sort_direction
#                 }}},
#             limit],
#     }
#     return_agg = [
#         {
#             "$project": pair_strat_dict
#         }
#     ]
#     return return_agg
#
#
# def get_limited_strat_alerts_obj(limit: int):
#     mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
#     mongo_version_start_num = mongo_version.split(".")[0]
#     if int(mongo_version_start_num) < 6:
#         return get_limited_strat_alerts_obj_v5(limit)
#     else:
#         return get_limited_strat_alerts_obj_v6(limit)


# if __name__ == '__main__':
    # with_symbol_agg_query = get_last_n_sec_orders_by_event("sym-1", 5, "OE_NEW")
    # print(with_symbol_agg_query)
    # without_symbol_agg_query = get_last_n_sec_orders_by_event(None, 5, "OE_NEW")
    # print(without_symbol_agg_query)

    # print(get_limited_portfolio_alerts_obj(5))
    # print(get_limited_strat_alerts_obj(5))
