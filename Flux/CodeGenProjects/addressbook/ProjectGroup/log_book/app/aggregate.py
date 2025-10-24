# standard imports
from typing import Dict, Tuple, Type, List, Any
import os

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.ORMModel.log_book_service_model_imports import (
    ContactAlertBaseModel, PlanAlertBaseModel, Severity)
from FluxPythonUtils.scripts.general_utility_functions import get_version_from_mongodb_uri
from FluxPythonUtils.scripts.model_base_utils import MsgspecBaseModel
# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_model_to_dict_for_v5_limit_agg(model_obj_dict: Dict):
    for key, value in model_obj_dict.items():
        model_obj_dict[key] = {
            "$first": f"${key}"
        }


def get_model_to_dict_for_limit_agg(model_obj_dict: Dict):
    for key, value in model_obj_dict.items():
        if isinstance(value, dict):
            get_model_to_dict_for_limit_agg(value)
        else:
            model_obj_dict[key] = 1


def get_limit_n_sort_direction(limit: int) -> Tuple[int, int]:
    if limit < 0:
        limit = -limit  # to make it positive
        sort_direction = -1
    else:
        sort_direction = 1
    return limit, sort_direction


# def add_plan_alert_aggregated_severity_field_n_alert_count(projection_aggregate_dict: Dict):
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
#     projection_aggregate_dict["plan_alert_aggregated_severity"] = severity_field
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
# def get_limited_alerts_obj_v5(limit: int, model_type: Type[ContactAlertBaseModel] | Type[PlanAlertBaseModel]):
#     alert_obj_dict_for_grp_layer = model_type().model_dump()
#     get_model_model_to_dict_for_v5_limit_agg(alert_obj_dict_for_grp_layer)
#     alert_obj_dict_for_grp_layer["_id"] = "$_id"
#     # del model_obj_dict["id"]
#     alert_obj_dict_for_grp_layer["alerts"] = {
#         "$push": "$alerts"
#     }
#
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#     contact_alert_obj_dict_for_project_layer = model_type().model_dump()
#     get_model_model_to_dict_for_limit_agg(contact_alert_obj_dict_for_project_layer)
#     contact_alert_obj_dict_for_project_layer["alerts"] = {
#             "$slice": ["$alerts", limit]
#         }
#     contact_alert_obj_dict_for_project_layer["_id"] = 1
#
#     # adding additional field aggregate to update plan_alert_aggregated_severity and plan_alert_count - used
#     # in updating specific plan_view's fields
#     add_plan_alert_aggregated_severity_field_n_alert_count(contact_alert_obj_dict_for_project_layer)
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
#             '$project': contact_alert_obj_dict_for_project_layer
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
#                                       model_type: Type[ContactAlertBaseModel] | Type[PlanAlertBaseModel]):
#     model_type_obj = model_type().model_dump()
#     get_model_model_to_dict_for_limit_agg(model_type_obj)
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#
#     model_type_obj["alerts"] = {
#         "$slice": [
#             {"$sortArray": {
#                 "input": "$alerts",
#                 "sortBy": {
#                     "last_update_date_time": sort_direction
#                 }}},
#             limit],
#     }
#
#     # adding additional field aggregate to update plan_alert_aggregated_severity and plan_alert_count - used
#     # in updating specific plan_view's fields
#     add_plan_alert_aggregated_severity_field_n_alert_count(model_type_obj)
#
#     agg_pipeline = [
#         {
#             "$project": model_type_obj
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
#                                       model_type: Type[ContactAlertBaseModel] | Type[PlanAlertBaseModel],
#                                       plan_id: int | None = None):
#     model_type_obj = model_type().model_dump()
#     get_model_model_to_dict_for_limit_agg(model_type_obj)
#     limit, sort_direction = get_limit_n_sort_direction(limit)
#
#     model_type_obj["alerts"] = {
#         "$slice": [
#             {"$sortArray": {
#                 "input": "$alerts",
#                 "sortBy": {
#                     "last_update_date_time": sort_direction
#                 }}},
#             limit],
#     }
#
#     # adding additional field aggregate to update plan_alert_aggregated_severity and plan_alert_count - used
#     # in updating specific plan_view's fields
#     add_plan_alert_aggregated_severity_field_n_alert_count(model_type_obj)
#
#     agg_pipeline = [
#         {
#             "$project": model_type_obj
#         }
#     ]
#
#     # Extending agg_pipeline by including pipeline to sort alerts based on severity
#     extend_pipeline_to_sort_alerts_based_on_severity(agg_pipeline)
#
#     return agg_pipeline
#
# def get_limited_contact_alerts_obj(limit: int):
#     mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
#     mongo_version_start_num = mongo_version.split(".")[0]
#     if int(mongo_version_start_num) < 6:
#         return get_limited_alerts_obj_v5(limit, ContactAlertBaseModel)
#     else:
#         return get_limited_alerts_obj_v6_n_above(limit, ContactAlertBaseModel)
#
#
# def get_limited_plan_alerts_obj(model_obj, limit: int):
#     mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
#     mongo_version_start_num = mongo_version.split(".")[0]
#     if int(mongo_version_start_num) < 6:
#         return get_limited_alerts_obj_v5(limit, PlanAlertBaseModel)
#     else:
#         return get_limited_alerts_obj_v6_n_above(limit, PlanAlertBaseModel)


def get_plan_alerts_by_plan_id(plan_id: int):
    return {"aggregate": [
        {
            '$match': {
                'dismiss': False
            }
        },
        {
            "$match": {
                "plan_id": plan_id
            }
        }
    ]}


def get_total_plan_alert_count_n_highest_severity(plan_id: int):
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
                'plan_id': plan_id
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


def sort_alerts_based_on_severity_n_last_update_analyzer_time(
        plan_id_or_model_obj: int | MsgspecBaseModel | None = None, limit: int | None = None, **kwargs):
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
                'last_update_analyzer_time': -1
            }
        },
        {
            '$project': {
                'severityPriority': 0
            }
        }
    ]

    # if plan_id exists then adding match layer
    if plan_id_or_model_obj is not None:
        if isinstance(plan_id_or_model_obj, int):
            plan_id: int = plan_id_or_model_obj
            agg_pipeline[1]["$match"] = {
                'plan_id': plan_id
            }
        else:
            model_obj = plan_id_or_model_obj
            if hasattr(model_obj, "plan_id") and model_obj.plan_id is not None:
                agg_pipeline[1]["$match"] = {
                    'plan_id': model_obj.plan_id
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
        if limit > 0:
            agg_pipeline[3]["$sort"]["last_update_analyzer_time"] = 1

        agg_pipeline.append({
            "$limit": abs(limit)
        })
    return agg_pipeline


def get_plan_alert_from_plan_id_n_alert_brief_regex(plan_id: int, brief_regex: str):
    agg_pipeline = {"aggregate": [
        {
            '$match': {
                'dismiss': False
            }
        },
        {
            '$match': {
                'plan_id': plan_id
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


def get_projection_plan_alert_id_by_plan_id(plan_id: int):
    agg_pipeline = {"aggregate": [
        {
            '$match': {
                'plan_id': plan_id
            }
        }, {
            '$group': {
                '_id': 1,
                'plan_alert_ids': {
                    '$push': '$_id'
                }
            }
        }, {
            '$project': {
                '_id': 0,
                'plan_alert_ids': 1
            }
        }
    ]}
    return agg_pipeline


if __name__ == "__main__":
    import pprint
    # pprint.pprint(get_limited_alerts_obj_v5(5, PlanAlertBaseModel))
    # pprint.pprint(get_limited_alerts_obj_v6_n_above(5, PlanAlertBaseModel))
    # print(get_limited_plan_alerts_obj(5))
    # pprint.pprint(sort_alerts_based_on_severity_n_last_update_date_time(1, -100))
    pprint.pprint(get_total_plan_alert_count_n_highest_severity(1))

