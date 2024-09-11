# standard imports
from typing import List


# Aggregates required in all projects

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


def get_non_stored_ids(ids_to_check: List[int]):
    pipeline = [
        # Step 1: Match documents with _id in the ids_to_check list
        {"$match": {"_id": {"$in": ids_to_check}}},

        # Step 2: Group the found _id values into an array
        {"$group": {"_id": None, "found_ids": {"$addToSet": "$_id"}}},

        # Step 3: Use facet to handle the case when no documents match
        {"$facet": {
            "results": [
                {"$project": {
                    "found_ids": "$found_ids",
                    "missing_ids": {"$setDifference": [ids_to_check, "$found_ids"]}
                }}
            ],
            "empty": [
                {"$count": "count"}
            ]
        }},

        # Step 4: Handle empty results by merging the facets
        {"$project": {
            "found_ids": {
                "$cond": [{"$eq": [{"$size": "$results"}, 0]}, [], {"$arrayElemAt": ["$results.found_ids", 0]}]},
            "missing_ids": {"$cond": [{"$eq": [{"$size": "$results"}, 0]}, ids_to_check,
                                      {"$arrayElemAt": ["$results.missing_ids", 0]}]}
        }}
    ]
    return pipeline


def get_nested_field_max_id(nested_field_name):
    pipeline = [
        {"$unwind": f"${nested_field_name}"},  # Unwind the "nested_field_name" array
        {"$group": {"_id": None, "max_id": {"$max": f"${nested_field_name}._id"}}}  # Get the max id
    ]
    return pipeline


def get_raw_perf_data_callable_names_pipeline():
    agg_pipeline = {"aggregate": [
        {
            '$group': {
                '_id': '$callable_name',
                'count': {
                    '$count': {}
                }
            }
        }, {
            '$project': {
                '_id': 0,
                'callable_name': '$_id',
                'total_calls': '$count'
            }
        }
    ]}
    return agg_pipeline


def get_raw_performance_data_from_callable_name_agg_pipeline(callable_name: str):
    return {"aggregate": [
        {
            "$match": {
                "callable_name": callable_name
            }
        }
    ]}
