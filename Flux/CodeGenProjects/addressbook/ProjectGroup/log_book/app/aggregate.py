# standard imports
from typing import Dict, Tuple, Type, List, Any
import os

# 3rd party imports
from pydantic import BaseModel

from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import (
    PortfolioAlertBaseModel, StratAlertBaseModel, Severity)
from FluxPythonUtils.scripts.utility_functions import get_version_from_mongodb_uri
# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


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


# def add_strat_alert_aggregated_severity_field_n_alert_count(projection_aggregate_dict: Dict):
#     severity_field: Dict = {
#         '$switch': {
#             'branches': [],
#             'default': 'Severity_UNSPECIFIED'
#         }
#     }
#     for sev in Severity:
#         if sev.value != "Severity_UNSPECIFIED":
#             severity_field["$switch"]['branches'].append(
#                 {
#                     'case': {
#                         '$in': [
#                             f'{sev.value}', '$alerts.severity'
#                         ]
#                     },
#                     'then': f'{sev.value}'
#                 }
#             )
#         # else not required: Severity_UNSPECIFIED is set as default
#
#     projection_aggregate_dict["strat_alert_aggregated_severity"] = severity_field
#     projection_aggregate_dict["alert_count"] = {
#         "$size": "$alerts"
#     }
#
#
# def extend_pipeline_to_sort_alerts_based_on_severity(agg_pipeline: List[Dict]):
#     extend_agg_pipeline: List[Dict] = [
#         {
#             '$addFields': {
#                 'alerts': {
#                     '$cond': {
#                         'if': {
#                             '$isArray': '$alerts'
#                         },
#                         'then': '$alerts',
#                         'else': []
#                     }
#                 }
#             }
#         },
#         {
#             '$unwind': {
#                 'path': '$alerts',
#                 'preserveNullAndEmptyArrays': True
#             }
#         }, {
#             '$addFields': {
#                 '_sortPriority': {
#                     '$ifNull': [
#                         {
#                             '$switch': {
#                                 'branches': [],
#                                 'default': None
#                             }
#                         }, None
#                     ]
#                 }
#             }
#         }, {
#             '$sort': {
#                 '_sortPriority': 1
#             }
#         }, {
#             '$group': {
#                 '_id': '$_id',
#                 'otherFields': {
#                     '$first': '$$ROOT'
#                 },
#                 'alerts': {
#                     '$push': '$alerts'
#                 }
#             }
#         }, {
#             '$unset': [
#                 '_sortPriority', 'otherFields._sortPriority'
#             ]
#         }, {
#             '$replaceRoot': {
#                 'newRoot': {
#                     '$mergeObjects': [
#                         '$otherFields', {
#                             'alerts': '$alerts'
#                         }
#                     ]
#                 }
#             }
#         }]
#
#     counter = 1
#     for sev in Severity:
#         if sev.value != "Severity_UNSPECIFIED":
#             extend_agg_pipeline[2]["$addFields"]['_sortPriority']['$ifNull'][0]['$switch']['branches'].append(
#                 {
#                     'case': {
#                         '$eq': [
#                             '$alerts.severity', f'{sev.value}'
#                         ]
#                     },
#                     'then': counter
#                 }
#             )
#             counter += 1
#
#     # extending passed agg_pipeline
#     agg_pipeline.extend(extend_agg_pipeline)
#
#
# def get_limited_alerts_obj_v5(limit: int, pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel]):
#     alert_obj_dict_for_grp_layer = pydantic_type().model_dump()
#     get_pydantic_model_to_dict_for_v5_limit_agg(alert_obj_dict_for_grp_layer)
#     alert_obj_dict_for_grp_layer["_id"] = "$_id"
#     # del pydentic_obj_dict["id"]
#     alert_obj_dict_for_grp_layer["alerts"] = {
#         "$push": "$alerts"
#     }
#
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#     portfolio_alert_obj_dict_for_project_layer = pydantic_type().model_dump()
#     get_pydantic_model_to_dict_for_limit_agg(portfolio_alert_obj_dict_for_project_layer)
#     portfolio_alert_obj_dict_for_project_layer["alerts"] = {
#             "$slice": ["$alerts", limit]
#         }
#     portfolio_alert_obj_dict_for_project_layer["_id"] = 1
#
#     # adding additional field aggregate to update strat_alert_aggregated_severity and strat_alert_count - used
#     # in updating specific strat_view's fields
#     add_strat_alert_aggregated_severity_field_n_alert_count(portfolio_alert_obj_dict_for_project_layer)
#
#     agg_list = [
#         {
#             '$unwind': {
#                 'path': '$alerts',
#                 "preserveNullAndEmptyArrays": True,
#             }
#         }, {
#             '$sort': {
#                 'alerts.last_update_date_time': sort_direction
#             }
#         }, {
#             '$group': alert_obj_dict_for_grp_layer
#         }, {
#             '$project': portfolio_alert_obj_dict_for_project_layer
#         }
#     ]
#
#     # Extending agg_pipeline by including pipeline to sort alerts based on severity
#     extend_pipeline_to_sort_alerts_based_on_severity(agg_list)
#
#     return agg_list
#
# # deprecated
# def _get_limited_alerts_obj_v6_n_above(limit: int,
#                                       pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel]):
#     pydantic_type_obj = pydantic_type().model_dump()
#     get_pydantic_model_to_dict_for_limit_agg(pydantic_type_obj)
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#
#     pydantic_type_obj["alerts"] = {
#         "$slice": [
#             {"$sortArray": {
#                 "input": "$alerts",
#                 "sortBy": {
#                     "last_update_date_time": sort_direction
#                 }}},
#             limit],
#     }
#
#     # adding additional field aggregate to update strat_alert_aggregated_severity and strat_alert_count - used
#     # in updating specific strat_view's fields
#     add_strat_alert_aggregated_severity_field_n_alert_count(pydantic_type_obj)
#
#     agg_pipeline = [
#         {
#             "$project": pydantic_type_obj
#         }
#     ]
#
#     # Extending agg_pipeline by including pipeline to sort alerts based on severity
#     extend_pipeline_to_sort_alerts_based_on_severity(agg_pipeline)
#
#     return agg_pipeline
#
#
# def get_limited_alerts_obj_v6_n_above(limit: int,
#                                       pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel],
#                                       strat_id: int | None = None):
#     pydantic_type_obj = pydantic_type().model_dump()
#     get_pydantic_model_to_dict_for_limit_agg(pydantic_type_obj)
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#
#     pydantic_type_obj["alerts"] = {
#         "$slice": [
#             {"$sortArray": {
#                 "input": "$alerts",
#                 "sortBy": {
#                     "last_update_date_time": sort_direction
#                 }}},
#             limit],
#     }
#
#     # adding additional field aggregate to update strat_alert_aggregated_severity and strat_alert_count - used
#     # in updating specific strat_view's fields
#     add_strat_alert_aggregated_severity_field_n_alert_count(pydantic_type_obj)
#
#     agg_pipeline = [
#         {
#             "$project": pydantic_type_obj
#         }
#     ]
#
#     # Extending agg_pipeline by including pipeline to sort alerts based on severity
#     extend_pipeline_to_sort_alerts_based_on_severity(agg_pipeline)
#
#     return agg_pipeline
#
# def get_limited_portfolio_alerts_obj(limit: int):
#     mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
#     mongo_version_start_num = mongo_version.split(".")[0]
#     if int(mongo_version_start_num) < 6:
#         return get_limited_alerts_obj_v5(limit, PortfolioAlertBaseModel)
#     else:
#         return get_limited_alerts_obj_v6_n_above(limit, PortfolioAlertBaseModel)
#
#
# def get_limited_strat_alerts_obj(pydantic_obj, limit: int):
#     mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
#     mongo_version_start_num = mongo_version.split(".")[0]
#     if int(mongo_version_start_num) < 6:
#         return get_limited_alerts_obj_v5(limit, StratAlertBaseModel)
#     else:
#         return get_limited_alerts_obj_v6_n_above(limit, StratAlertBaseModel)


def get_strat_alerts_by_strat_id(strat_id: int):
    return {"aggregate": [
        {
            '$match': {
                'dismiss': False
            }
        },
        {
            "$match": {
                "strat_id": strat_id
            }
        }
    ]}


def get_total_strat_alert_count_n_highest_severity(strat_id: int):
    """
    - $facet Stage: Executes two sub-pipelines:
        * total_objects: Counts the total number of documents in the collection.
        * highest_priority_severity: Finds the severity with the highest priority among all documents.

    - $unwind Stage: Deconstructs the array created by the $facet stage to prepare for further processing.

    - $project Stage: Shapes the output document, including existing fields and adding two new fields:
        * total_objects: The count of documents in the collection. Defaults to 0 if no data.
        * highest_priority_severity: The severity with the highest priority. Defaults to "No data" if no data.
    """
    agg_pipeline = {"aggregate": [
        {
            '$match': {
                'dismiss': False
            }
        },
        {
            '$match': {
                'strat_id': strat_id
            }
        }, {
            '$facet': {
                'total_objects': [
                    {
                        '$count': 'count'
                    }
                ],
                'highest_priority_severity': [
                    {
                        '$group': {
                            '_id': None,
                            'maxPriority': {
                                '$max': {
                                    '$switch': {
                                        'branches': [],
                                        'default': 0
                                    }
                                }
                            }
                        }
                    }, {
                        "$project": {
                            "highest_priority_severity": {}
                        }
                    }
                ]
            }
        }, {
            '$unwind': {
                'path': '$total_objects'
            }
        }, {
            '$unwind': {
                'path': '$highest_priority_severity'
            }
        }, {
            '$project': {
                'total_objects': '$total_objects.count',
                'highest_priority_severity': '$highest_priority_severity.highest_priority_severity'
            }
        }
    ]}

    counter = len(Severity) - 1     # removing UNSPECIFIED
    highest_priority_severity = agg_pipeline["aggregate"][2]["$facet"]['highest_priority_severity'][1]['$project'][
        "highest_priority_severity"]
    for sev in Severity:
        if sev.value != "Severity_UNSPECIFIED":
            agg_pipeline["aggregate"][2]["$facet"]['highest_priority_severity'][0]['$group']["maxPriority"]['$max']['$switch']["branches"].append(
                {
                    'case': {
                        '$eq': [
                            '$severity', f'{sev.value}'
                        ]
                    },
                    'then': counter
                }
            )

            if counter != 1:
                highest_priority_severity["$cond"] = {
                        "if": {"$eq": ["$maxPriority", counter]},
                        "then": f"{sev.value}",
                        "else": {}
                }
                if counter != 2:
                    highest_priority_severity = highest_priority_severity["$cond"]["else"]
            else:
                highest_priority_severity["$cond"]["else"] = sev.value
            counter -= 1
    return agg_pipeline


def sort_alerts_based_on_severity_n_last_update_analyzer_time(strat_id_or_pydantic_obj: int | BaseModel | None = None,
                                                              limit: int | None = None):
    """
    - $addFields: Adds a new field severityPriority based on the priority mapping defined using $switch.
    - $switch: Evaluates each case expression and returns the value associated with the first case expression that
    evaluates to true.
    - $sort: Sorts documents based on severityPriority in descending chore and then by last_update_analyzer_time in
    descending chore.
    - $project: Excludes the severityPriority field from the final output.
    """
    agg_pipeline = [
        {
            '$match': {
                'dismiss': False
            }
        },
        {
            '$match': {}
        },
        {
            '$addFields': {
                'severityPriority': {
                    '$switch': {
                        'branches': [],
                        'default': 0
                    }
                }
            }
        },
        {
            '$sort': {
                'severityPriority': -1,
                'last_update_analyzer_time': 1
            }
        },
        {
            '$project': {
                'severityPriority': 0
            }
        }
    ]

    # if strat_id exists then adding match layer
    if strat_id_or_pydantic_obj is not None:
        if isinstance(strat_id_or_pydantic_obj, int):
            strat_id: int = strat_id_or_pydantic_obj
            agg_pipeline[1]["$match"] = {
                'strat_id': strat_id
            }
        else:
            pydantic_obj = strat_id_or_pydantic_obj
            if hasattr(pydantic_obj, "strat_id") and pydantic_obj.strat_id is not None:
                agg_pipeline[1]["$match"] = {
                    'strat_id': pydantic_obj.strat_id
                }

    counter = len(Severity) - 1  # removing UNSPECIFIED
    for sev in Severity:
        if sev.value != "Severity_UNSPECIFIED":
            agg_pipeline[2]["$addFields"]['severityPriority']['$switch']["branches"].append(
                {
                    'case': {
                        '$eq': [
                            '$severity', f'{sev.value}'
                        ]
                    },
                    'then': counter
                }
            )
            counter -= 1

    if limit is not None:   # putting limit at last layer
        if limit < 0:
            limit = abs(limit)
            agg_pipeline[3]["$sort"]["last_update_analyzer_time"] = -1

        agg_pipeline.append({
            "$limit": limit
        })
    return agg_pipeline


def get_strat_alert_from_strat_id_n_alert_brief_regex(strat_id: int, brief_regex: str):
    agg_pipeline = {"aggregate": [
        {
            '$match': {
                'dismiss': False
            }
        },
        {
            '$match': {
                'strat_id': strat_id
            }
        },
        {
            '$match': {
                'alert_brief': {
                    '$regex': brief_regex
                }
            }
        }
    ]}
    return agg_pipeline


if __name__ == "__main__":
    import pprint
    # pprint.pprint(get_limited_alerts_obj_v5(5, StratAlertBaseModel))
    # pprint.pprint(get_limited_alerts_obj_v6_n_above(5, StratAlertBaseModel))
    # print(get_limited_strat_alerts_obj(5))
    # pprint.pprint(sort_alerts_based_on_severity_n_last_update_date_time(1, -100))
    pprint.pprint(get_total_strat_alert_count_n_highest_severity(1))

