# standard imports
from typing import Dict, Tuple, Type
import os

# 3rd party imports
from pendulum import DateTime

# Below unused import is used by generated beanie file
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_callable_delta_list_from_datetime(start_datetime: DateTime | None = None, end_datetime: DateTime | None = None):
    agg_pipeline = {"agg": [
            {
                '$match': {}
            }, {
            '$group': {
                '_id': '$callable_name',
                'delta_list': {
                    '$push': '$delta'
                }
            }
        }
    ]}

    if start_datetime is not None and end_datetime is None:
        agg_pipeline["agg"][0]["$match"] = {
            '$expr': {
                '$gte': [
                    '$datetime', start_datetime
                ]
            }
        }
    elif end_datetime is not None and start_datetime is None:
        agg_pipeline["agg"][0]["$match"] = {
            '$expr': {
                '$lte': [
                    '$datetime', end_datetime
                ]
            }
        }
    elif start_datetime is not None and end_datetime is not None:
        agg_pipeline["agg"][0]["$match"] = {

            "$and": [
                {
                    '$expr': {
                        '$gte': [
                            '$datetime', start_datetime
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lte': [
                            '$datetime', end_datetime
                        ]
                    }
                }
        ]}

    return agg_pipeline
