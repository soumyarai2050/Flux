# standard imports
from typing import Dict, Tuple, Type
import os

os.environ["DBType"] = "beanie"
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import (
    PortfolioAlertBaseModel, StratAlertBaseModel)
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_beanie_database import \
    get_mongo_server_uri
from FluxPythonUtils.scripts.utility_functions import get_version_from_mongodb_uri


def get_pydantic_model_to_dict_for_v5_limit_agg(pydentic_obj_dict: Dict):
    for key, value in pydentic_obj_dict.items():
        pydentic_obj_dict[key] = {
            "$first": f"${key}"
        }


def get_pydantic_model_to_dict_for_limit_agg(pydentic_obj_dict: Dict):
    for key, value in pydentic_obj_dict.items():
        if isinstance(value, dict):
            get_pydantic_model_to_dict_for_limit_agg(value)
        else:
            pydentic_obj_dict[key] = 1


def get_limit_n_sort_direction(limit: int) -> Tuple[int, int]:
    if limit < 0:
        limit = -limit  # to make it positive
        sort_direction = -1
    else:
        sort_direction = 1
    return limit, sort_direction


def get_limited_alerts_obj_v5(limit: int, pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel]):
    alert_obj_dict_for_grp_layer = pydantic_type().dict()
    get_pydantic_model_to_dict_for_v5_limit_agg(alert_obj_dict_for_grp_layer)
    alert_obj_dict_for_grp_layer["_id"] = "$_id"
    # del pydentic_obj_dict["id"]
    alert_obj_dict_for_grp_layer["alerts"] = {
        "$push": "$alerts"
    }

    limit, sort_direction = get_limit_n_sort_direction(limit)
    portfolio_alert_obj_dict_for_project_layer = pydantic_type().dict()
    get_pydantic_model_to_dict_for_limit_agg(portfolio_alert_obj_dict_for_project_layer)
    portfolio_alert_obj_dict_for_project_layer["alerts"] = {
            "$slice": ["$alerts", limit]
        }
    portfolio_alert_obj_dict_for_project_layer["_id"] = 1

    agg_list = [
        {
            '$unwind': {
                'path': '$alerts',
                "preserveNullAndEmptyArrays": True,
            }
        }, {
            '$sort': {
                'alerts.last_update_date_time': sort_direction
            }
        }, {
            '$group': alert_obj_dict_for_grp_layer
        }, {
            '$project': portfolio_alert_obj_dict_for_project_layer
        }
    ]
    return agg_list


def get_limited_alerts_obj_v6(limit: int, pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel]):
    # todo: might have bugs: not tested for v6 after multi-executor change
    pydantic_type_obj = pydantic_type().dict()
    get_pydantic_model_to_dict_for_limit_agg(pydantic_type_obj)
    limit, sort_direction = get_limit_n_sort_direction(limit)

    pydantic_type_obj["alerts"] = {
        "$slice": [
            {"$sortArray": {
                "input": "$alerts",
                "sortBy": {
                    "last_update_date_time": sort_direction
                }}},
            limit],
    }
    return [
        {
            "$project": pydantic_type_obj
        }
    ]


def get_limited_portfolio_alerts_obj(limit: int):
    mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
    mongo_version_start_num = mongo_version.split(".")[0]
    if int(mongo_version_start_num) < 6:
        return get_limited_alerts_obj_v5(limit, PortfolioAlertBaseModel)
    else:
        return get_limited_alerts_obj_v6(limit, PortfolioAlertBaseModel)


def get_limited_strat_alerts_obj(limit: int):
    mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
    mongo_version_start_num = mongo_version.split(".")[0]
    if int(mongo_version_start_num) < 6:
        return get_limited_alerts_obj_v5(limit, StratAlertBaseModel)
    else:
        return get_limited_alerts_obj_v6(limit, StratAlertBaseModel)

# def get_limited_strat_alerts_obj_v5(limit: int):
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#     pair_strat_obj_dict_for_grp_agg = PairStratBaseModel().dict()
#     pair_strat_obj_dict_for_project_agg = PairStratBaseModel().dict()
#     get_pydantic_model_to_dict_for_v5_limit_agg(pair_strat_obj_dict_for_grp_agg)
#     pair_strat_obj_dict_for_grp_agg["_id"] = "$_id"
#     # del pydentic_obj_dict["id"]
#     pair_strat_obj_dict_for_grp_agg["temp_strat_alerts"] = {
#         "$push": '$strat_status.alerts'
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


if __name__ == "__main__":
    print(get_limited_portfolio_alerts_obj(5))

