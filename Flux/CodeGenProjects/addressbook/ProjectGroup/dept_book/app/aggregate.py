import pendulum
from pendulum import DateTime
from typing import List, Dict

# below import is required in routes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_msgspec_model import *


def get_dict_list_for_bar_meta_data_match(symbol: str, exch_id: str, bar_type: BarType | None = None) -> List[Dict[str, Any]]:
    agg_list = [
            {
                'bar_meta_data.symbol': symbol
            },
            {
                'bar_meta_data.exch_id': exch_id
            }
        ]
    if bar_type is None:
        return agg_list
    else:
        agg_list.append(
            {
                'bar_meta_data.bar_type': bar_type.value
            }
        )
        return agg_list


def get_vwap_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, bar_type: BarType,
                                                   start_date_time: int | None = None,
                                                   end_date_time: int | None = None,
                                                   id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'vwap': '$vwap'
                }
            },
        },
        {
            '$group': {
                '_id': '$bar_meta_data',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': '$_id',
                'projection_models': 1
            }
        }
    ]
    if id_list is not None:
        agg_pipeline[0]['$match'] = {
            '_id': {
                '$in': id_list
            }
        }
    if start_date_time and not end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_date_time
                ]
            }
        }
    elif not start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$lt': [
                    '$end_time', end_date_time
                ]
            }
        }
    elif start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_date_time
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$end_time', end_date_time
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}


def get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: BarType, start_date_time: int | None = None,
        end_date_time: int | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'vwap': '$vwap',
                    'vwap_change': '$vwap_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$bar_meta_data',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': '$_id',
                'projection_models': 1
            }
        }
    ]
    if id_list is not None:
        agg_pipeline[0]['$match'] = {
            '_id': {
                '$in': id_list
            }
        }
    if start_date_time and not end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_date_time
                ]
            }
        }
    elif not start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$lt': [
                    '$start_time', end_date_time
                ]
            }
        }
    elif start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_date_time
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$start_time', end_date_time
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}


def get_vwap_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: BarType, start_date_time: int | None = None,
        end_date_time: int | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'vwap_change': '$vwap_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$bar_meta_data',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': '$_id',
                'projection_models': 1
            }
        }
    ]
    if id_list is not None:
        agg_pipeline[0]['$match'] = {
            '_id': {
                '$in': id_list
            }
        }
    if start_date_time and not end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_date_time
                ]
            }
        }
    elif not start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$lt': [
                    '$start_time', end_date_time
                ]
            }
        }
    elif start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_date_time
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$start_time', end_date_time
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}


def get_premium_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: BarType, start_date_time: int | None = None,
        end_date_time: int | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'premium': '$premium'
                }
            },
        },
        {
            '$group': {
                '_id': '$bar_meta_data',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': '$_id',
                'projection_models': 1
            }
        }
    ]
    if id_list is not None:
        agg_pipeline[0]['$match'] = {
            '_id': {
                '$in': id_list
            }
        }
    if start_date_time and not end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_date_time
                ]
            }
        }
    elif not start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$lt': [
                    '$start_time', end_date_time
                ]
            }
        }
    elif start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_date_time
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$start_time', end_date_time
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}


def get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: BarType, start_date_time: int | None = None,
        end_date_time: int | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'premium': '$premium',
                    'premium_change': '$premium_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$bar_meta_data',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': '$_id',
                'projection_models': 1
            }
        }
    ]
    if id_list is not None:
        agg_pipeline[0]['$match'] = {
            '_id': {
                '$in': id_list
            }
        }
    if start_date_time and not end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_date_time
                ]
            }
        }
    elif not start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$lt': [
                    '$start_time', end_date_time
                ]
            }
        }
    elif start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_date_time
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$start_time', end_date_time
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}


def get_premium_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: BarType, start_date_time: int | None = None,
        end_date_time: int | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'premium_change': '$premium_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$bar_meta_data',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'bar_meta_data': '$_id',
                'projection_models': 1
            }
        }
    ]
    if id_list is not None:
        agg_pipeline[0]['$match'] = {
            '_id': {
                '$in': id_list
            }
        }
    if start_date_time and not end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_date_time
                ]
            }
        }
    elif not start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$expr': {
                '$lt': [
                    '$start_time', end_date_time
                ]
            }
        }
    elif start_date_time and end_date_time:
        agg_pipeline[2]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_date_time
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$start_time', end_date_time
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}


def get_bar_data_from_symbol_n_start_n_end_datetime(
        symbol: str, exch_id: str, bar_type: BarType, start_datetime: DateTime, end_datetime: DateTime):
    agg_pipeline: List[Dict] = [
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type)
            }
        },
        {
            '$match': {},
        }
    ]
    if start_datetime and not end_datetime:
        agg_pipeline[1]['$match'] = {
            '$expr': {
                '$gt': [
                    '$start_time', start_datetime
                ]
            }
        }
    elif not start_datetime and end_datetime:
        agg_pipeline[1]['$match'] = {
            '$expr': {
                '$lt': [
                    '$start_time', end_datetime
                ]
            }
        }
    elif start_datetime and end_datetime:
        agg_pipeline[1]['$match'] = {
            '$and': [
                {
                    '$expr': {
                        '$gt': [
                            '$start_time', start_datetime
                        ]
                    }
                },
                {
                    '$expr': {
                        '$lt': [
                            '$start_time', end_datetime
                        ]
                    }
                }
            ]
        }
    return {'aggregate': agg_pipeline}

# Helper function to determine $dateTrunc parameters
def get_date_trunc_params(target_bar_type: str) -> Dict[str, Any]:
    """
    Maps a target bar type string to the required parameters for MongoDB's
    $dateTrunc aggregation operator (unit, binSize, startOfWeek, timezone).

    Args:
        target_bar_type: The desired output bar granularity string
                         (e.g., "FiveMin", "OneHour", "OneDay", "OneWeek").

    Returns:
        A dictionary containing 'unit' and potentially 'binSize',
        'startOfWeek', plus 'timezone' (always 'UTC').

    Raises:
        ValueError: If the target_bar_type is not recognized or supported.
    """
    params: Dict[str, Any] = {"timezone": "UTC"} # Always include timezone

    match target_bar_type:
        case "OneMin":
            params.update({"unit": "minute"})
        case "FiveMin":
            params.update({"unit": "minute", "binSize": 5})
        case "FifteenMin":
            params.update({"unit": "minute", "binSize": 15})
        case "ThirtyMin":
            params.update({"unit": "minute", "binSize": 30})
        case "OneHour":
            params.update({"unit": "hour"})
        case "FiveHour":
            params.update({"unit": "hour", "binSize": 5})
        case "OneDay":
            params.update({"unit": "day"})
        case "OneWeek":
            params.update({"unit": "week", "startOfWeek": "Monday"}) # Default Monday
        case "OneMonth":
            params.update({"unit": "month"})
        case _: # Default case for unsupported types
            raise ValueError(f"Unsupported target_bar_type: {target_bar_type}")

    return params

def get_interval_duration(target_bar_type: str) -> pendulum.Duration | None:
    """ Gets an approximate Pendulum Duration for the bar type. """
    match target_bar_type:
        case "OneMin": return pendulum.duration(minutes=1)
        case "FiveMin": return pendulum.duration(minutes=5)
        case "FifteenMin": return pendulum.duration(minutes=15)
        case "ThirtyMin": return pendulum.duration(minutes=30)
        case "OneHour": return pendulum.duration(hours=1)
        case "FiveHour": return pendulum.duration(hours=5)
        case "OneDay": return pendulum.duration(days=1)
        case "OneWeek": return pendulum.duration(weeks=1)
        case "OneMonth": return pendulum.duration(months=1) # Approximate
        case _: return None

def _build_non_time_match_conditions(
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Builds the common (non-time) match conditions."""
    conditions = []
    # Mandatory source bar type filter
    conditions.append({"bar_meta_data.bar_type": "OneMin"})
    # Optional exchange filter
    if exch_id_list:
        conditions.append({"bar_meta_data.exch_id": {"$in": exch_id_list}})
    # Optional symbol filter
    if symbol_list:
        conditions.append({"bar_meta_data.symbol": {"$in": symbol_list}})
    return conditions


def _build_core_aggregation_stages(
    target_bar_type: str,
    date_trunc_params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Builds the common core aggregation stages: pre-sort, group, project,
    and handles complex source field aggregation with sorted mixed sources.
    (Requires MongoDB 5.2+ for $sortArray expression)
    """
    stages = []

    # Stage: Pre-Group Sorting ($sort)
    stages.append({
        "$sort": {
            "bar_meta_data.exch_id": 1,
            "bar_meta_data.symbol": 1,
            "start_time": 1
        }
    })

    # Stage: Grouping and Aggregation ($group)
    stages.append({
        "$group": {
            "_id": {
                "exch_id": "$bar_meta_data.exch_id",
                "symbol": "$bar_meta_data.symbol",
                "interval_start_time": {
                    "$dateTrunc": {"date": "$start_time", **date_trunc_params}
                }
            },
            # Accumulators
            "first_bar_meta_data": { "$first": "$bar_meta_data" },
            "start_time": { "$first": "$start_time" }, "end_time": { "$last": "$end_time" },
            "open": { "$first": "$open" }, "high": { "$max": "$high" }, "low": { "$min": "$low" }, "close": { "$last": "$close" },
            "volume": { "$sum": { "$ifNull": ["$volume", 0] } },
            "vwap_numerator": { "$sum": { "$multiply": [ { "$ifNull": ["$vwap", 0] }, { "$ifNull": ["$volume", 0] } ] } },
            "vwap_denominator": { "$sum": { "$ifNull": ["$volume", 0] } },
            "cum_volume": { "$last": "$cum_volume" }, "bar_count": { "$sum": 1 },
            "unique_sources": { "$addToSet": "$source" }
        }
    })

    # Stage: Output Shaping ($addFields for the source, then $project)
    stages.append({
        "$addFields": {
            "calculated_source": {
                "$let": {
                    "vars": {
                        "filtered_sources_array": { # Filter out nulls first
                            "$filter": {
                                "input": "$unique_sources",
                                "as": "s",
                                "cond": { "$ne": ["$$s", None] }
                            }
                        }
                    },
                    "in": {
                        "$let": { # Nested let to use the filtered array for sorting
                            "vars": {
                                "sorted_sources_array": { # *** Sort the filtered array ***
                                    "$cond": { # Only sort if array is not empty
                                        "if": { "$gt": [{"$size": "$$filtered_sources_array"}, 0] },
                                        "then": {
                                            "$sortArray": {
                                                "input": "$$filtered_sources_array",
                                                "sortBy": 1 # Sorts strings alphabetically
                                            }
                                        },
                                        "else": [] # Empty array if no non-null sources
                                    }
                                }
                            },
                            "in": {
                                "$switch": {
                                    "branches": [
                                        {
                                            "case": { "$eq": [{ "$size": "$$sorted_sources_array" }, 0] },
                                            "then": None # Or "Unknown"
                                        },
                                        {
                                            "case": { "$eq": [{ "$size": "$$sorted_sources_array" }, 1] },
                                            "then": { "$arrayElemAt": ["$$sorted_sources_array", 0] }
                                        },
                                        {
                                            "case": { "$gt": [{ "$size": "$$sorted_sources_array" }, 1] },
                                            "then": {
                                                "$concat": [
                                                    "Mixed: ",
                                                    { # Use the sorted array for reduction
                                                        "$reduce": {
                                                            "input": "$$sorted_sources_array",
                                                            "initialValue": "",
                                                            "in": {
                                                                "$cond": {
                                                                    "if": { "$eq": ["$$value", ""] },
                                                                    "then": "$$this",
                                                                    "else": { "$concat": ["$$value", " + ", "$$this"] }
                                                                }
                                                            }
                                                        }
                                                    }
                                                ]
                                            }
                                        }
                                    ],
                                    "default": None
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    # $project stage (remains the same as the corrected version from before)
    stages.append({
        "$project": {
            "_id": 0,
            "bar_meta_data": {"symbol": "$_id.symbol", "exch_id": "$_id.exch_id", "bar_type": target_bar_type},
            "start_time": "$start_time", "end_time": "$end_time",
            "open": "$open", "high": "$high", "low": "$low", "close": "$close",
            "volume": "$volume",
            "vwap": { "$cond": { "if": { "$eq": ["$vwap_denominator", 0] }, "then": None, "else": { "$divide": ["$vwap_numerator", "$vwap_denominator"] } } },
            "cum_volume": "$cum_volume", "bar_count": "$bar_count",
            "source": "$calculated_source"
            # Intermediate fields like unique_sources, vwap_numerator, etc., are implicitly dropped
        }
    })

    return stages

def _generate_latest_n_bar_pipeline(
    target_bar_type: str,
    end_time_param: str | datetime.datetime | pendulum.DateTime | None,
    target_bar_counts: int,
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
    start_time_buffer_factor: float = 1.5
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates optimized pipeline for fetching the latest N aggregated bars.
    (Internal use - assumes target_bar_counts > 0)
    """
    pipeline: List[Dict[str, Any]] = []

    # --- Parameter Processing ---
    now_utc = pendulum.DateTime.utcnow()
    if end_time_param is None: effective_end_time_pendulum = now_utc
    else:
        try:
            if not isinstance(end_time_param, pendulum.DateTime):
                end_time_param = pendulum.instance(end_time_param).in_timezone('UTC')
        except Exception as e: raise ValueError(f"Could not parse end_time_param: {end_time_param}. Error: {e}") from e

    date_trunc_params = get_date_trunc_params(target_bar_type)

    # Calculate Estimated Start Time
    estimated_start_time: pendulum.DateTime | None = None
    interval_duration = get_interval_duration(target_bar_type)
    if interval_duration and interval_duration.total_seconds() > 0:
        lookback_intervals = int(target_bar_counts * start_time_buffer_factor) + 1
        total_lookback_seconds = interval_duration.total_seconds() * lookback_intervals
        estimated_start_time = end_time_param.subtract(seconds=total_lookback_seconds)

    # --- Construct Pipeline Stages ---
    # Build initial match stage
    time_match_condition = {"$lte": end_time_param}
    if estimated_start_time:
        time_match_condition["$gte"] = estimated_start_time # Use estimate

    non_time_conditions = _build_non_time_match_conditions(exch_id_list, symbol_list)
    all_match_conditions = [{"start_time": time_match_condition}] + non_time_conditions
    pipeline.append({"$match": {"$and": all_match_conditions}})

    # Build core aggregation stages
    core_stages = _build_core_aggregation_stages(target_bar_type, date_trunc_params)
    pipeline.extend(core_stages)

    # Add final sorting and limiting stages specific to this mode
    pipeline.append({"$sort": {"start_time": -1, "bar_meta_data.exch_id": 1, "bar_meta_data.symbol": 1}})
    pipeline.append({"$limit": target_bar_counts})
    pipeline.append({"$sort": {"bar_meta_data.exch_id": 1, "bar_meta_data.symbol": 1, "start_time": 1}})

    return {"aggregate": pipeline}


def _generate_time_range_bar_pipeline(
    target_bar_type: str,
    actual_start_time: DateTime,
    actual_end_time: DateTime,
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates pipeline for aggregating bars strictly within a given time range.
    (Internal use)
    """
    pipeline: List[Dict[str, Any]] = []

    # --- Parameter Processing ---
    date_trunc_params = get_date_trunc_params(target_bar_type)

    # --- Construct Pipeline Stages ---
    # Build initial match stage
    time_match_condition = { # Use EXACT start/end times
        "$gte": actual_start_time,
        "$lte": actual_end_time
    }
    non_time_conditions = _build_non_time_match_conditions(exch_id_list, symbol_list)
    all_match_conditions = [{"start_time": time_match_condition}] + non_time_conditions
    pipeline.append({"$match": {"$and": all_match_conditions}})

    # Build core aggregation stages
    core_stages = _build_core_aggregation_stages(target_bar_type, date_trunc_params)
    pipeline.extend(core_stages)

    # Add final sorting stage specific to this mode (no limit)
    pipeline.append({"$sort": {"bar_meta_data.exch_id": 1, "bar_meta_data.symbol": 1, "start_time": 1}})

    return {"aggregate": pipeline}


# --- Wrapper Function ---
# (Handles User Input and Calls Correct Pipeline Generator)
def get_bar_aggregation_pipeline(
    target_bar_type: str,
    end_time_param: str | datetime.datetime | pendulum.DateTime | None = None,
    start_time_param: str | datetime.datetime | pendulum.DateTime | None = None,
    target_bar_counts: int | None = None,
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Wrapper function to generate bar aggregation pipeline. Accepts either
    a start_time_param OR target_bar_counts to define the data query mode.
    # todo: make least bar type configurable and keep default as 1-minute
    Args:
        target_bar_type: Desired output bar granularity string.
        end_time_param: Optional end datetime (inclusive). Defaults to now (UTC).
                        Required for both modes (explicitly or via default).
        start_time_param: Optional start datetime (inclusive). If provided, fetches
                          all bars within the [start_time, end_time] range.
                          Mutually exclusive with target_bar_counts.
        target_bar_counts: Optional number of latest bars to return ending at or
                           before end_time_param. Must be > 0 if provided.
                           Mutually exclusive with start_time_param.
        exch_id_list: Optional list of exchange IDs to filter.
        symbol_list: Optional list of symbols to filter.

    Returns:
        Dict containing the 'aggregate' pipeline definition.

    Raises:
        ValueError: If validation fails (e.g., both/neither range params provided,
                    invalid count, invalid times, invalid target_bar_type).
    """
    # --- Input Validation ---
    if start_time_param is not None and target_bar_counts is not None:
        raise ValueError("Provide EITHER 'start_time_param' OR 'target_bar_counts', not both.")
    if start_time_param is None and target_bar_counts is None:
        raise ValueError("Provide EITHER 'start_time_param' OR 'target_bar_counts'.")

    # --- Determine Mode and Call Appropriate Function ---
    if start_time_param is not None:
        # == Time Range Mode ==
        now_utc = pendulum.DateTime.utcnow()
        if end_time_param is None:
            end_time_param = now_utc
        else:
            try:
                if not isinstance(end_time_param, pendulum.DateTime):
                    end_time_param = pendulum.instance(end_time_param).in_timezone('UTC')
            except Exception as e: raise ValueError(f"Could not parse end_time_param: {end_time_param}. Error: {e}") from e
        try:
            if not isinstance(start_time_param, pendulum.DateTime):
                start_time_param = pendulum.instance(start_time_param).in_timezone('UTC')
        except Exception as e: raise ValueError(f"Could not parse start_time_param: {start_time_param}. Error: {e}") from e
        if start_time_param >= end_time_param:
             print(f"Warning: start_time_param ({start_time_param}) is not before end_time_param ({end_time_param}).")

        return _generate_time_range_bar_pipeline(
            target_bar_type=target_bar_type,
            actual_start_time=start_time_param,
            actual_end_time=end_time_param,
            exch_id_list=exch_id_list,
            symbol_list=symbol_list
        )
    elif target_bar_counts is not None:
        # == Latest N Mode ==
        if not isinstance(target_bar_counts, int) or target_bar_counts <= 0:
             raise ValueError("target_bar_counts must be a positive integer.")
        return _generate_latest_n_bar_pipeline(
             target_bar_type=target_bar_type,
             end_time_param=end_time_param,
             target_bar_counts=target_bar_counts,
             exch_id_list=exch_id_list,
             symbol_list=symbol_list
        )
    else:
         raise ValueError("Internal logic error: No valid mode determined.") # Should be unreachable

def get_latest_bar_data_agg(
    exch_id_list: List[str] | None = None,
    bar_type_list: List[BarType] | None = None,
    start_time_param: pendulum.DateTime | None = None,
    end_time_param: pendulum.DateTime | None = None):
    """
    Generates a MongoDB aggregation pipeline to find the latest BarData
    for each unique combination of exchange ID and symbol within a given
    time range, optionally filtered by lists of exchange IDs and bar types.

    Args:
        exch_id_list: A list of exchange IDs to filter by. If None or empty, includes all exchanges.
        bar_type_list: A list of BarType enum members to filter by. If None or empty, includes all bar types.
        start_time_param: The beginning of the time window (inclusive).
                          Defaults to 20 days before the current UTC time if None.
        end_time_param: The end of the time window (inclusive).
                        Defaults to the current UTC time if None.

    Returns:
        A dictionary containing the aggregation pipeline list under the key "aggregate".
    """
    pipeline: List[Dict[str, Any]] = []

    # --- Determine Time Filter Boundaries ---
    # Set default end time to now (UTC) if not provided
    effective_end_time = end_time_param if end_time_param is not None else pendulum.DateTime.utcnow()
    # Set default start time to 20 days before end time if not provided
    effective_start_time = start_time_param if start_time_param is not None else effective_end_time.subtract(days=20)

    # Ensure they are pendulum DateTime objects for consistency downstream
    # (though pymongo/motor usually handle standard datetimes too)
    if not isinstance(effective_start_time, pendulum.DateTime):
         # Attempt conversion if a standard datetime was passed
         effective_start_time = pendulum.instance(effective_start_time, tz='utc')
    if not isinstance(effective_end_time, pendulum.DateTime):
         effective_end_time = pendulum.instance(effective_end_time, tz='utc')


    # 1. Initial Match Stage (Filter based on ALL inputs)
    match_query: Dict[str, Any] = {}

    # Add optional filters
    if exch_id_list:
        match_query["bar_meta_data.exch_id"] = {"$in": exch_id_list}
    if bar_type_list:
        # Convert enums to their string values for the query
        bar_type_values = [bt.value for bt in bar_type_list]
        match_query["bar_meta_data.bar_type"] = {"$in": bar_type_values}

    # Add mandatory time range filter
    # Assumes 'start_time' field in MongoDB is stored as a BSON Date (ISODate)
    # Pymongo/Motor handle Python datetime/pendulum objects correctly for querying BSON Dates
    match_query["start_time"] = {
        "$gte": effective_start_time, # Greater than or equal to start time
        "$lte": effective_end_time    # Less than or equal to end time
    }

    pipeline.append({"$match": match_query})

    # 2. Sort Stage (Chore by group key fields + time)
    # Sort needed to pick the latest using $first in the group stage
    pipeline.append({"$sort": {
        "bar_meta_data.exch_id": 1,  # Sort by exchange first
        "bar_meta_data.symbol": 1,   # Then by symbol within the exchange
        "start_time": -1            # Latest start time first within each filtered group
    }})

    # 3. Group Stage (Group by composite key: exch_id, symbol)
    pipeline.append({"$group": {
        "_id": { # Composite group key
            "exch_id": "$bar_meta_data.exch_id",
            "symbol": "$bar_meta_data.symbol"
        },
        "latest_doc": {"$first": "$$ROOT"} # Get the entire latest document for this combo
    }})

    # 4. Replace Root Stage (Promote the found document)
    pipeline.append({"$replaceRoot": {
        "newRoot": "$latest_doc"
    }})

    # 5. Optional: Final Sort Stage (Sort final results meaningfully)
    pipeline.append({"$sort": {
        "bar_meta_data.exch_id": 1,
        "bar_meta_data.symbol": 1
    }})
    return {"aggregate": pipeline}

def get_dash_filter_by_dash_name(dash_name: str):
    agg_pipeline: List[Dict] = [
        {"$match": {
            "dash_name": dash_name
        }},
    ]
    return {'aggregate': agg_pipeline}

def filter_dash_from_dash_filters_agg(dash_filters: DashFilters, obj_id_list: List[int] | None = None):
    agg_pipeline: List[Dict] = []

    # if obj_id_list is passed matching with these id(s) to avoid any non-updated ws notification
    if obj_id_list:
        agg_pipeline.append({
            "$match": {
                "_id": {
                    "$in": obj_id_list
                }
            }
        })

    # matching if leg exists based on dash_filters.required_legs
    # also checking leg.vwap ranges within min to max of px_range
    leg_match_list = []
    for required_legs in dash_filters.required_legs:
        if required_legs.leg_type == LegType.LegType_CB:
            leg_match = {"$and": [
                {"rt_dash.leg1": {"$exists": True}},
                {"rt_dash.leg1": {"$ne": None}}
            ]}
            if dash_filters.px_range:
                leg_match["rt_dash.leg1.vwap"] = {}
                if dash_filters.px_range.px_low is not None:
                    leg_match["rt_dash.leg1.vwap"]["$gte"] = dash_filters.px_range.px_low
                if dash_filters.px_range.px_high is not None:
                    leg_match["rt_dash.leg1.vwap"]["$lte"] = dash_filters.px_range.px_high
            leg_match_list.append(leg_match)
        if required_legs.leg_type == LegType.LegType_EQT_A:
            leg_match = {"$and": [
                {"rt_dash.leg2": {"$exists": True}},
                {"rt_dash.leg2": {"$ne": None}}
            ]}
            if dash_filters.px_range:
                leg_match["rt_dash.leg2.vwap"] = {}
                if dash_filters.px_range.px_low is not None:
                    leg_match["rt_dash.leg2.vwap"]["$gte"] = dash_filters.px_range.px_low
                if dash_filters.px_range.px_high is not None:
                    leg_match["rt_dash.leg2.vwap"]["$lte"] = dash_filters.px_range.px_high
            leg_match_list.append(leg_match)
        if required_legs.leg_type == LegType.LegType_EQT_H:
            leg_match = {"$and": [
                {"rt_dash.leg3": {"$exists": True}},
                {"rt_dash.leg3": {"$ne": None}}
            ]}
            if dash_filters.px_range:
                leg_match["rt_dash.leg3.vwap"] = {}
                if dash_filters.px_range.px_low is not None:
                    leg_match["rt_dash.leg3.vwap"]["$gte"] = dash_filters.px_range.px_low
                if dash_filters.px_range.px_high is not None:
                    leg_match["rt_dash.leg3.vwap"]["$lte"] = dash_filters.px_range.px_high
            leg_match_list.append(leg_match)
    agg_pipeline.append({
        "$match": {
            "$or": leg_match_list
        }
    })

    # if premium_range exists matching mkt_premium
    if dash_filters.premium_range:
        match_agg = {}
        if dash_filters.premium_range.premium_low is not None:
            match_agg["$gte"] = dash_filters.premium_range.premium_low
        if dash_filters.premium_range.premium_high is not None:
            match_agg["$lte"] = dash_filters.premium_range.premium_high
        agg_pipeline.append({
            "$match": {
                "rt_dash.mkt_premium": match_agg
            }
        })

    # if premium_change_range exists matching mkt_premium_change
    if dash_filters.premium_change_range:
        match_agg = {}
        if dash_filters.premium_change_range.premium_change_low is not None:
            match_agg["$gte"] = dash_filters.premium_change_range.premium_change_low
        if dash_filters.premium_change_range.premium_change_high is not None:
            match_agg["$lte"] = dash_filters.premium_change_range.premium_change_high
        agg_pipeline.append({
            "$match": {
                "rt_dash.mkt_premium_change": match_agg
            }
        })

    # if inventory exists matching inventory's position type bools with position_type in positions of sec_positions of eligible_brokers
    if dash_filters.inventory:
        if dash_filters.inventory.any:
            agg_pipeline.append({
                "$match": {
                    "rt_dash.eligible_brokers.sec_positions.positions": {
                        "$elemMatch": {
                            "type": {
                                "$in": [
                                    PositionType.PTH,
                                    PositionType.LOCATE,
                                    PositionType.SOD,
                                    PositionType.INDICATIVE
                                ]
                            }
                        }
                    }
                }
            })
        else:
            position_type_list: List[PositionType] = []
            if dash_filters.inventory.pth:
                position_type_list.append(PositionType.PTH)
            if dash_filters.inventory.locate:
                position_type_list.append(PositionType.LOCATE)
            if dash_filters.inventory.sod:
                position_type_list.append(PositionType.SOD)
            if dash_filters.inventory.indicative:
                position_type_list.append(PositionType.INDICATIVE)

            if position_type_list:
                agg_pipeline.append({
                    "$match": {
                        "rt_dash.eligible_brokers.sec_positions.positions": {
                            "$elemMatch": {
                                "type": {
                                    "$in": position_type_list
                                }
                            }
                        }
                    }
                })

    # if has_ashare_locate_request exists matching rt_dash.ashare_locate_requests
    if dash_filters.has_ashare_locate_request:
        agg_pipeline.append({
            "$match": {
                "$and": [
                  { "rt_dash.ashare_locate_requests": { "$exists": True } },
                  { "rt_dash.ashare_locate_requests": { "$ne": [] } }
                ]
            }
        })

    # if optimizer_criteria exists matching rt_dash.ashare_locate_requests
    if dash_filters.optimizer_criteria:
        ignore_pos_type_list: List[PositionType] = [
            PositionType.SOD,   # always ignored
            dash_filters.optimizer_criteria.pos_type    # avoiding same pos_type
        ]
        if dash_filters.optimizer_criteria.pos_type == PositionType.LOCATE:
            ignore_pos_type_list.append(PositionType.PTH)

        agg_pipeline.extend([
            {
                # Step 1: Filter out documents with no eligible brokers
                '$match': {
                    'rt_dash.eligible_brokers': {
                        '$exists': True,
                        '$ne': []
                    }
                }
            }, {
                # Step 2: Unwind eligible_brokers to process each broker individually
                '$unwind': '$rt_dash.eligible_brokers'
            }, {
                # Step 3: Unwind sec_positions within each broker
                '$unwind': '$rt_dash.eligible_brokers.sec_positions'
            }, {
                # Step 4: Unwind positions within each sec_position
                '$unwind': '$rt_dash.eligible_brokers.sec_positions.positions'
            }, {
                # Step 5: Group positions by document _id
                '$group': {
                    '_id': '$_id',
                    'all_positions': {
                        '$push': {
                            'type': '$rt_dash.eligible_brokers.sec_positions.positions.type',
                            'acquire_cost': '$rt_dash.eligible_brokers.sec_positions.positions.acquire_cost',
                            'broker': '$rt_dash.eligible_brokers.broker'
                        }
                    }
                }
            }, {
                # Step 6: Compute optimize_pos_cost
                '$project': {
                    '_id': 1,
                    'all_positions': 1,
                    'optimize_pos_cost': {
                        '$max': {
                            '$map': {
                                'input': {
                                    '$filter': {
                                        'input': '$all_positions',
                                        'cond': {
                                            '$and': [
                                                {
                                                    '$eq': [
                                                        '$$this.type', dash_filters.optimizer_criteria.pos_type
                                                    ]
                                                }, {
                                                    '$ne': [
                                                        '$$this.acquire_cost', None
                                                    ]
                                                }, {
                                                    '$ne': [
                                                        '$$this.acquire_cost', 0
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                },
                                'as': 'filtered_position',
                                'in': '$$filtered_position.acquire_cost'
                            }
                        }
                    }
                }
            }, {
                # Step 7: Compute has_opportunity using the resolved optimize_pos_cost
                '$project': {
                    '_id': 1,
                    'optimize_pos_cost': 1,
                    'has_opportunity': {
                        '$gt': [
                            {
                                '$size': {
                                    '$filter': {
                                        'input': '$all_positions',
                                        'cond': {
                                            '$and': [
                                                {
                                                    '$not': {
                                                        '$in': [
                                                            '$$this.type', ignore_pos_type_list
                                                        ]
                                                    }
                                                }, {
                                                    '$ne': [
                                                        '$$this.acquire_cost', None
                                                    ]
                                                }, {
                                                    '$ne': [
                                                        '$$this.acquire_cost', 0
                                                    ]
                                                }, {
                                                    '$lt': [
                                                        '$$this.acquire_cost', '$optimize_pos_cost'
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                }
                            }, 0
                        ]
                    }
                }
            }, {
                # Step 8: Filter documents where has_opportunity is true
                '$match': {
                    'has_opportunity': True
                }
            },
            # Step 9: Reconstruct the original document structure (optional)
            {
                '$lookup': {
                    'from': 'Dash',
                    'localField': '_id',
                    'foreignField': '_id',
                    'as': 'original_doc'
                }
            }, {
                '$unwind': '$original_doc'
            }, {
                '$replaceRoot': {
                    'newRoot': '$original_doc'
                }
            }
        ])

    # if sort_criteria exists adding sorts
    if dash_filters.sort_criteria:
        for lvl, lvl_chore in [(dash_filters.sort_criteria.level1, dash_filters.sort_criteria.level1_chore),
                               (dash_filters.sort_criteria.level2, dash_filters.sort_criteria.level2_chore),
                               (dash_filters.sort_criteria.level3, dash_filters.sort_criteria.level3_chore)]:
            if lvl:
                if lvl_chore == SortType.ASCENDING:
                    sort_type = 1
                else:
                    sort_type = -1
                agg_pipeline.append({
                    "$sort": {lvl: sort_type},
                })
    return agg_pipeline
