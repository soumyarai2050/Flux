# standard imports
from typing import Dict, Tuple, Type, List, Any
import os

os.environ["DBType"] = "beanie"
# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import (
    PortfolioAlertBaseModel, StratAlertBaseModel, Severity)
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_book.generated.FastApi.log_book_service_beanie_database import \
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


def add_strat_alert_aggregated_severity_field_n_alert_count(projection_aggregate_dict: Dict):
    severity_field: Dict = {
        '$switch': {
            'branches': [],
            'default': 'Severity_UNSPECIFIED'
        }
    }
    for sev in Severity:
        if sev.value != "Severity_UNSPECIFIED":
            severity_field["$switch"]['branches'].append(
                {
                    'case': {
                        '$in': [
                            f'{sev.value}', '$alerts.severity'
                        ]
                    },
                    'then': f'{sev.value}'
                }
            )
        # else not required: Severity_UNSPECIFIED is set as default

    projection_aggregate_dict["strat_alert_aggregated_severity"] = severity_field
    projection_aggregate_dict["alert_count"] = {
        "$size": "$alerts"
    }


def extend_pipeline_to_sort_alerts_based_on_severity(agg_pipeline: List[Dict]):
    extend_agg_pipeline: List[Dict] = [
        {
            '$addFields': {
                'alerts': {
                    '$cond': {
                        'if': {
                            '$isArray': '$alerts'
                        },
                        'then': '$alerts',
                        'else': []
                    }
                }
            }
        },
        {
            '$unwind': {
                'path': '$alerts',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$addFields': {
                '_sortPriority': {
                    '$ifNull': [
                        {
                            '$switch': {
                                'branches': [],
                                'default': None
                            }
                        }, None
                    ]
                }
            }
        }, {
            '$sort': {
                '_sortPriority': 1
            }
        }, {
            '$group': {
                '_id': '$_id',
                'otherFields': {
                    '$first': '$$ROOT'
                },
                'alerts': {
                    '$push': '$alerts'
                }
            }
        }, {
            '$unset': [
                '_sortPriority', 'otherFields._sortPriority'
            ]
        }, {
            '$replaceRoot': {
                'newRoot': {
                    '$mergeObjects': [
                        '$otherFields', {
                            'alerts': '$alerts'
                        }
                    ]
                }
            }
        }]

    counter = 1
    for sev in Severity:
        if sev.value != "Severity_UNSPECIFIED":
            extend_agg_pipeline[2]["$addFields"]['_sortPriority']['$ifNull'][0]['$switch']['branches'].append(
                {
                    'case': {
                        '$eq': [
                            '$alerts.severity', f'{sev.value}'
                        ]
                    },
                    'then': counter
                }
            )
            counter += 1

    # extending passed agg_pipeline
    agg_pipeline.extend(extend_agg_pipeline)


def get_limited_alerts_obj_v5(limit: int, pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel]):
    alert_obj_dict_for_grp_layer = pydantic_type().model_dump()
    get_pydantic_model_to_dict_for_v5_limit_agg(alert_obj_dict_for_grp_layer)
    alert_obj_dict_for_grp_layer["_id"] = "$_id"
    # del pydentic_obj_dict["id"]
    alert_obj_dict_for_grp_layer["alerts"] = {
        "$push": "$alerts"
    }

    limit, sort_direction = get_limit_n_sort_direction(limit)
    portfolio_alert_obj_dict_for_project_layer = pydantic_type().model_dump()
    get_pydantic_model_to_dict_for_limit_agg(portfolio_alert_obj_dict_for_project_layer)
    portfolio_alert_obj_dict_for_project_layer["alerts"] = {
            "$slice": ["$alerts", limit]
        }
    portfolio_alert_obj_dict_for_project_layer["_id"] = 1

    # adding additional field aggregate to update strat_alert_aggregated_severity and strat_alert_count - used
    # in updating specific strat_view's fields
    add_strat_alert_aggregated_severity_field_n_alert_count(portfolio_alert_obj_dict_for_project_layer)

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

    # Extending agg_pipeline by including pipeline to sort alerts based on severity
    extend_pipeline_to_sort_alerts_based_on_severity(agg_list)

    return agg_list


def get_limited_alerts_obj_v6_n_above(limit: int,
                                      pydantic_type: Type[PortfolioAlertBaseModel] | Type[StratAlertBaseModel]):
    pydantic_type_obj = pydantic_type().model_dump()
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

    # adding additional field aggregate to update strat_alert_aggregated_severity and strat_alert_count - used
    # in updating specific strat_view's fields
    add_strat_alert_aggregated_severity_field_n_alert_count(pydantic_type_obj)

    agg_pipeline = [
        {
            "$project": pydantic_type_obj
        }
    ]

    # Extending agg_pipeline by including pipeline to sort alerts based on severity
    extend_pipeline_to_sort_alerts_based_on_severity(agg_pipeline)

    return agg_pipeline


def get_limited_portfolio_alerts_obj(limit: int):
    mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
    mongo_version_start_num = mongo_version.split(".")[0]
    if int(mongo_version_start_num) < 6:
        return get_limited_alerts_obj_v5(limit, PortfolioAlertBaseModel)
    else:
        return get_limited_alerts_obj_v6_n_above(limit, PortfolioAlertBaseModel)


def get_limited_strat_alerts_obj(limit: int):
    mongo_version = get_version_from_mongodb_uri(get_mongo_server_uri())
    mongo_version_start_num = mongo_version.split(".")[0]
    if int(mongo_version_start_num) < 6:
        return get_limited_alerts_obj_v5(limit, StratAlertBaseModel)
    else:
        return get_limited_alerts_obj_v6_n_above(limit, StratAlertBaseModel)


if __name__ == "__main__":
    import pprint
    pprint.pprint(get_limited_alerts_obj_v5(5, StratAlertBaseModel))
    pprint.pprint(get_limited_alerts_obj_v6_n_above(5, StratAlertBaseModel))
    # print(get_limited_strat_alerts_obj(5))

