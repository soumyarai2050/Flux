import pendulum
from pendulum import DateTime
from typing import List, Dict

# below import is required in routes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_msgspec_model import *


def get_dict_list_for_bar_meta_data_match(symbol: str, exch_id: str, bar_type: str | None = None,
                                          symbol_type: str | None = None,
                                          ticker: str | None = None) -> List[Dict[str, Any]]:
    agg_list = [
            {
                'bar_meta_data.symbol': symbol
            },
            {
                'bar_meta_data.exch_id': exch_id
            }
        ]
    if bar_type is not None:
        agg_list.append(
            {
                'bar_meta_data.bar_type': bar_type
            }
        )
    if symbol_type is not None:
        agg_list.append(
            {
                'bar_meta_data.symbol_type': symbol_type
            }
        )
    if ticker is not None:
        agg_list.append(
            {
                'bar_meta_data.ticker': ticker
            }
        )

    return agg_list


def get_vwap_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, bar_type: str,
                                                   symbol_type: str, ticker: str,
                                                   start_date_time: DateTime | None = None,
                                                   end_date_time: DateTime | None = None,
                                                   id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type, symbol_type, ticker)
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
    return {'agg': agg_pipeline}


def get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: str, symbol_type: str, ticker: str,
        start_date_time: DateTime | None = None,
        end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type, symbol_type, ticker)
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
    return {'agg': agg_pipeline}


def get_vwap_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: str, symbol_type: str, ticker: str,
        start_date_time: DateTime | None = None,
        end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type, symbol_type, ticker)
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
    return {'agg': agg_pipeline}


def get_premium_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: str, symbol_type: str, ticker: str,
        start_date_time: DateTime | None = None,
        end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type, symbol_type, ticker)
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
    return {'agg': agg_pipeline}


def get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: str, symbol_type: str, ticker: str,
        start_date_time: DateTime | None = None,
        end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type, symbol_type, ticker)
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
    return {'agg': agg_pipeline}


def get_premium_change_projection_from_bar_data_agg_pipeline(
        symbol: str, exch_id: str, bar_type: str, symbol_type: str, ticker: str,
        start_date_time: DateTime | None = None,
        end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': get_dict_list_for_bar_meta_data_match(symbol, exch_id, bar_type, symbol_type, ticker)
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
    return {'agg': agg_pipeline}


def get_bar_data_from_symbol_n_start_n_end_datetime(
        symbol: str, exch_id: str, bar_type: str, start_datetime: DateTime, end_datetime: DateTime):
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
    return {'agg': agg_pipeline}

# --- Add these constants at the beginning of your aggregate.py ---
NUMBER_WORD_MAP = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5,
    "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10,
    "Eleven": 11, "Twelve": 12, "Thirteen": 13, "Fourteen": 14, "Fifteen": 15,
    "Sixteen": 16, "Seventeen": 17, "Eighteen": 18, "Nineteen": 19, "Twenty": 20,
    "Thirty": 30, "Forty": 40, "Fifty": 50, "Sixty": 60
    # Add more common number words as needed, or rely on digit parsing
}

# Maps various unit string suffixes (case-insensitive for flexibility if desired, but strict for now)
# to (MongoDB $dateTrunc unit, Pendulum duration kwarg name)
UNIT_SUFFIX_TO_STANDARD_MAP = {
    # Suffix (as it appears in input string): (date_trunc_unit, pendulum_kwarg_unit)
    "Sec": ("second", "seconds"), "sec": ("second", "seconds"), "Second": ("second", "seconds"), "Seconds": ("second", "seconds"),
    "Min": ("minute", "minutes"), "min": ("minute", "minutes"), "Minute": ("minute", "minutes"), "Minutes": ("minute", "minutes"),
    "Hour": ("hour", "hours"), "hour": ("hour", "hours"), "Hours": ("hour", "hours"),
    "Day": ("day", "days"), "day": ("day", "days"), "Days": ("day", "days"),
    "Week": ("week", "weeks"), "week": ("week", "weeks"), "Weeks": ("week", "weeks"),
    "Month": ("month", "months"), "month": ("month", "months"), "Months": ("month", "months")
}
# Sort known suffixes by length descending to match longest first (e.g., "Minutes" before "Min")
SORTED_UNIT_SUFFIXES = sorted(UNIT_SUFFIX_TO_STANDARD_MAP.keys(), key=len, reverse=True)


def _parse_dynamic_target_bar_type(dynamic_bar_type_str: str) -> tuple[int, str, str]:
    """
    Parses a dynamic target_bar_type string like "OneHour", "SixMin", "15Day", "Onehour".

    Returns:
        A tuple: (multiplier, date_trunc_unit, pendulum_kwarg_unit_name)
    Raises:
        ValueError: if the format is invalid or parts are unrecognized.
    """
    if not dynamic_bar_type_str:
        raise ValueError("Dynamic target_bar_type cannot be empty.")

    number_part_str = ""
    unit_suffix_matched = ""
    date_trunc_unit = ""
    pendulum_kwarg_unit_name = ""

    # Iterate through known unit suffixes (longest first) to find a match at the end of the string
    for known_suffix in SORTED_UNIT_SUFFIXES:
        if dynamic_bar_type_str.endswith(known_suffix):
            # Extract the part of the string before the matched suffix as the number part
            number_part_str = dynamic_bar_type_str[:-len(known_suffix)]
            unit_suffix_matched = known_suffix  # The actual suffix string that matched
            date_trunc_unit, pendulum_kwarg_unit_name = UNIT_SUFFIX_TO_STANDARD_MAP[known_suffix]
            break  # Found the longest possible unit match

    if not unit_suffix_matched:  # No known unit suffix was found at the end
        raise ValueError(f"Could not parse unit from dynamic target_bar_type: '{dynamic_bar_type_str}'. "
                         f"Supported unit variations: {list(UNIT_SUFFIX_TO_STANDARD_MAP.keys())}")

    multiplier: int
    if not number_part_str:  # If the number part is empty, it implies a multiplier of 1 (e.g., "Hour" -> 1 Hour)
        multiplier = 1
    elif number_part_str.isdigit():  # Check if the number part is purely digits (e.g., "15Day")
        multiplier = int(number_part_str)
        if multiplier <= 0:
            raise ValueError(f"Numeric multiplier '{number_part_str}' in '{dynamic_bar_type_str}' must be positive.")
    else:  # Assume it's a number word (e.g., "OneHour", "SeventeenMin")
        multiplier = NUMBER_WORD_MAP.get(number_part_str)
        if multiplier is None:
            raise ValueError(f"Unrecognized number prefix '{number_part_str}' in '{dynamic_bar_type_str}'. "
                             f"Supported words: {list(NUMBER_WORD_MAP.keys())} or digits.")

    return multiplier, date_trunc_unit, pendulum_kwarg_unit_name


def get_date_trunc_params(dynamic_target_bar_type: str) -> Dict[str, Any]:
    """
    Maps a dynamic target bar type string (e.g., "FiveMin", "OneHour") to
    the required parameters for MongoDB's $dateTrunc operator.

    Args:
        dynamic_target_bar_type: The desired output bar granularity string.

    Returns:
        A dictionary for $dateTrunc parameters.

    Raises:
        ValueError: If the dynamic_target_bar_type is invalid.
    """
    # Parse the dynamic string to get multiplier and standardized unit
    multiplier, date_trunc_unit, _ = _parse_dynamic_target_bar_type(dynamic_target_bar_type)

    params: Dict[str, Any] = {"timezone": "UTC", "unit": date_trunc_unit}

    # Apply binSize only if the multiplier is greater than 1.
    # $dateTrunc defaults to a binSize of 1 if not specified.
    if multiplier > 1:
        params["binSize"] = multiplier

    # Add startOfWeek for "week" unit, as it's often required/desired.
    if date_trunc_unit == "week":
        params["startOfWeek"] = "Monday"  # This can be made configurable if needed.

    return params


def get_interval_duration(dynamic_target_bar_type: str) -> pendulum.Duration | None:
    """
    Gets an approximate Pendulum Duration for the given dynamic bar type string.
    Used for estimating lookback periods.

    Args:
        dynamic_target_bar_type: The target bar granularity string (e.g., "SixMin").

    Returns:
        A pendulum.Duration object or None if parsing fails or type is unknown.
    """
    # Parse the dynamic string to get multiplier and standardized Pendulum unit keyword
    multiplier, _, pendulum_kwarg_unit_name = _parse_dynamic_target_bar_type(dynamic_target_bar_type)

    # Create keyword arguments for pendulum.duration()
    # e.g., if pendulum_kwarg_unit_name is "minutes" and multiplier is 5, this becomes {"minutes": 5}
    duration_kwargs = {pendulum_kwarg_unit_name: multiplier}
    return pendulum.duration(**duration_kwargs)

def _build_non_time_match_conditions(
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Builds the common (non-time related) match conditions for the aggregation pipeline.
    Includes filtering for source bar type (hardcoded to "OneMin"),
    and optional exchange and symbol lists.

    Args:
        exch_id_list: Optional list of exchange IDs to filter by.
        symbol_list: Optional list of symbols to filter by.

    Returns:
        A list of match condition dictionaries.
    """
    conditions = []
    # Mandatory: Ensures aggregation is performed on 1-minute source data.
    # todo: make this configurable from wrapper if base granularity can change.
    conditions.append({"bar_meta_data.bar_type": "OneMin"})
    # Optional: Filter by a list of exchange IDs if provided.
    if exch_id_list:
        conditions.append({"bar_meta_data.exch_id": {"$in": exch_id_list}})
    # Optional: Filter by a list of symbols if provided.
    if symbol_list:
        conditions.append({"bar_meta_data.symbol": {"$in": symbol_list}})
    return conditions


def _build_core_aggregation_stages(
    target_bar_type: str,
    date_trunc_params: Dict[str, Any] # Result from get_date_trunc_params
) -> List[Dict[str, Any]]:
    """
    Builds the common core aggregation stages:
    1. Pre-group sort (by exch, symbol, start_time ascending).
    2. Grouping stage ($group):
        - Creates time buckets using $dateTrunc.
        - Accumulates OHLCV, bar_count.
        - Collects unique source strings for later processing.
    3. $addFields stage: Calculates the 'source' field based on unique sources
       (single, "Mixed: A + B + C" sorted, or null).
    4. $project stage: Shapes the final output document structure.
       (Requires MongoDB 5.2+ for $sortArray expression used in source calculation).

    Args:
        target_bar_type: The target bar type string (e.g., "FiveMin").
        date_trunc_params: Parameters for the $dateTrunc operator.

    Returns:
        A list of core aggregation stage dictionaries.
    """
    stages = []

    # Stage 1: Pre-Group Sorting ($sort)
    # Ensures $first and $last accumulators in $group work correctly.
    stages.append({
        "$sort": {
            "bar_meta_data.exch_id": 1,
            "bar_meta_data.symbol": 1,
            "start_time": 1 # Ascending time chore is crucial
        }
    })

    # Stage 2: Grouping and Aggregation ($group)
    # This stage groups the 1-minute bars into the target intervals.
    stages.append({
        "$group": {
            "_id": { # Composite group key
                "exch_id": "$bar_meta_data.exch_id",
                "symbol": "$bar_meta_data.symbol",
                "interval_start_time": { # Time bucket for the aggregation
                    "$dateTrunc": {"date": "$start_time", **date_trunc_params}
                }
            },
            # Accumulators for standard bar data fields
            "first_bar_meta_data": { "$first": "$bar_meta_data" }, # Temp field for metadata
            "start_time": { "$first": "$start_time" }, # Actual start of the first 1-min bar
            "end_time": { "$last": "$end_time" },     # Actual end of the last 1-min bar
            "open": { "$first": "$open" },
            "high": { "$max": "$high" },
            "low": { "$min": "$low" },
            "close": { "$last": "$close" },
            "volume": { "$sum": { "$ifNull": ["$volume", 0] } }, # Sum volumes, treat nulls as 0
            # Numerator and denominator for VWAP calculation
            "vwap_numerator": { "$sum": { "$multiply": [ { "$ifNull": ["$vwap", 0] }, { "$ifNull": ["$volume", 0] } ] } },
            "vwap_denominator": { "$sum": { "$ifNull": ["$volume", 0] } },
            "cum_volume": { "$last": "$cum_volume" }, # Last cumulative volume
            "bar_count": { "$sum": 1 },             # Count of 1-min bars in this aggregate
            "unique_sources": { "$addToSet": "$source" } # Collect all unique source strings
        }
    })

    # Stage 3: $addFields to calculate the 'source' field based on 'unique_sources'
    # This handles single source, mixed sources (sorted), or null/unknown.
    stages.append({
        "$addFields": {
            "calculated_source": {
                "$let": {
                    "vars": {
                        "filtered_sources_array": { # Remove any explicit nulls from the set
                            "$filter": {
                                "input": "$unique_sources", "as": "s", "cond": { "$ne": ["$$s", None] }
                            }
                        }
                    },
                    "in": {
                        "$let": { # Nested let for clarity, to use the filtered array
                            "vars": {
                                "sorted_sources_array": { # Sort the non-null source strings (MongoDB 5.2+)
                                    "$cond": { # Only sort if array has elements
                                        "if": { "$gt": [{"$size": "$$filtered_sources_array"}, 0] },
                                        "then": {
                                            "$sortArray": { "input": "$$filtered_sources_array", "sortBy": 1 }
                                        },
                                        "else": []
                                    }
                                }
                            },
                            "in": { # Construct the final source string
                                "$switch": {
                                    "branches": [
                                        { # Case: No non-null sources found
                                            "case": { "$eq": [{ "$size": "$$sorted_sources_array" }, 0] },
                                            "then": None # Or a default string like "Unknown"
                                        },
                                        { # Case: Exactly one unique source
                                            "case": { "$eq": [{ "$size": "$$sorted_sources_array" }, 1] },
                                            "then": { "$arrayElemAt": ["$$sorted_sources_array", 0] }
                                        },
                                        { # Case: Multiple unique sources
                                            "case": { "$gt": [{ "$size": "$$sorted_sources_array" }, 1] },
                                            "then": {
                                                "$concat": [
                                                    "Mixed: ",
                                                    { # Join sorted sources with " + "
                                                        "$reduce": {
                                                            "input": "$$sorted_sources_array",
                                                            "initialValue": "",
                                                            "in": {
                                                                "$cond": { # Avoid leading " + "
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
                                    "default": None # Fallback, though covered by size 0
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    # Stage 4: $project to shape the final output document
    # Explicitly includes desired fields; others (like intermediate ones) are dropped.
    stages.append({
        "$project": {
            "_id": 0, # Exclude the default _id from the $group stage
            "bar_meta_data": {
                "symbol": "$_id.symbol",
                "exch_id": "$_id.exch_id",
                "bar_type": target_bar_type # Set to the target aggregation type
            },
            "start_time": "$start_time",
            "end_time": "$end_time",
            "open": "$open",
            "high": "$high",
            "low": "$low",
            "close": "$close",
            "volume": "$volume",
            "vwap": { # Final VWAP calculation, handling division by zero
                "$cond": {
                    "if": { "$eq": ["$vwap_denominator", 0] },
                    "then": None, # Or 0, depending on desired output for zero volume
                    "else": { "$divide": ["$vwap_numerator", "$vwap_denominator"] }
                }
            },
            "cum_volume": "$cum_volume",
            "bar_count": "$bar_count",
            "source": "$calculated_source" # Use the processed source string
            # Fields like unique_sources, vwap_numerator, vwap_denominator, first_bar_meta_data
            # are implicitly excluded as they are not listed here.
        }
    })
    return stages

# --- Internal Pipeline Generation Functions ---

def _generate_latest_n_bar_pipeline(
    target_bar_type: str,
    end_time_param: pendulum.DateTime, # Wrapper ensures this is a Pendulum DateTime
    target_bar_counts: int,         # Wrapper ensures this is > 0
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
    start_time_buffer_factor: float = 1.5 # Internal buffer factor
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates an optimized pipeline for fetching the latest N aggregated bars
    ending at or before 'end_time_param'.
    It estimates an initial start time for efficiency, aggregates the data,
    and then applies a precise limit to get the N most recent bars.
    (Internal use function).

    Args:
        target_bar_type: The target granularity (e.g., "FiveMin").
        end_time_param: The latest possible end time for consideration (Pendulum DateTime, UTC).
        target_bar_counts: The number of latest aggregated bars to retrieve.
        exch_id_list: Optional list of exchange IDs.
        symbol_list: Optional list of symbols.
        start_time_buffer_factor: Factor to multiply with target_bar_counts and interval
                                  duration to estimate a buffered lookback start time.
    Returns:
        The MongoDB aggregation pipeline definition.
    """
    pipeline: List[Dict[str, Any]] = []

    # Get parameters for $dateTrunc (unit, binSize, etc.)
    date_trunc_params = get_date_trunc_params(target_bar_type)

    # Calculate an estimated start time to narrow down the initial data scan.
    # This is an optimization to avoid processing too much historical data.
    estimated_start_time: pendulum.DateTime | None = None
    interval_duration = get_interval_duration(target_bar_type)
    if interval_duration and interval_duration.total_seconds() > 0:
        # Calculate how many intervals to look back, including a buffer.
        lookback_intervals = int(target_bar_counts * start_time_buffer_factor) + 1
        total_lookback_seconds = interval_duration.total_seconds() * lookback_intervals
        # Subtract the total lookback duration from the end time.
        estimated_start_time = end_time_param.subtract(seconds=total_lookback_seconds)

    # --- Construct Pipeline Stages ---
    # Stage 1: Initial Filtering ($match)
    # Filters source 1-min bars based on time, type, and optional exch/symbol.
    time_match_condition = {"$lte": end_time_param} # Source bar's start must be before/at end_time_param
    if estimated_start_time:
        time_match_condition["$gte"] = estimated_start_time # Use estimated start if calculated

    non_time_conditions = _build_non_time_match_conditions(exch_id_list, symbol_list)
    all_match_conditions = [{"start_time": time_match_condition}] + non_time_conditions
    pipeline.append({"$match": {"$and": all_match_conditions}})

    # Add core aggregation stages (pre-sort, group, addFields for source, project)
    core_stages = _build_core_aggregation_stages(target_bar_type, date_trunc_params)
    pipeline.extend(core_stages)

    # Final stages specific to "latest N" mode:
    # 1. Sort aggregated bars descending by start_time to get the latest first.
    # 2. Limit to the requested number of bars.
    # 3. Sort the limited set back to ascending chronological chore for final output.
    pipeline.append({"$sort": {"start_time": -1, "bar_meta_data.exch_id": 1, "bar_meta_data.symbol": 1}})
    pipeline.append({"$limit": target_bar_counts})
    pipeline.append({"$sort": {"bar_meta_data.exch_id": 1, "bar_meta_data.symbol": 1, "start_time": 1}})

    return {"agg": pipeline}


def _generate_time_range_bar_pipeline(
    target_bar_type: str,
    actual_start_time: pendulum.DateTime, # Wrapper ensures this is a Pendulum DateTime
    actual_end_time: pendulum.DateTime,   # Wrapper ensures this is a Pendulum DateTime
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates a pipeline for aggregating bars strictly within a given
    start_time_param and end_time_param. No limit is applied other than the time range.
    (Internal use function).

    Args:
        target_bar_type: The target granularity (e.g., "OneHour").
        actual_start_time: The exact start of the time window (Pendulum DateTime, UTC).
        actual_end_time: The exact end of the time window (Pendulum DateTime, UTC).
        exch_id_list: Optional list of exchange IDs.
        symbol_list: Optional list of symbols.

    Returns:
        The MongoDB aggregation pipeline definition.
    """
    pipeline: List[Dict[str, Any]] = []

    # Get parameters for $dateTrunc
    date_trunc_params = get_date_trunc_params(target_bar_type)

    # --- Construct Pipeline Stages ---
    # Stage 1: Initial Filtering ($match)
    # Filters source 1-min bars using the EXACT start and end times provided.
    time_match_condition = {
        "$gte": actual_start_time,
        "$lte": actual_end_time
    }
    non_time_conditions = _build_non_time_match_conditions(exch_id_list, symbol_list)
    all_match_conditions = [{"start_time": time_match_condition}] + non_time_conditions
    pipeline.append({"$match": {"$and": all_match_conditions}})

    # Add core aggregation stages (pre-sort, group, addFields for source, project)
    core_stages = _build_core_aggregation_stages(target_bar_type, date_trunc_params)
    pipeline.extend(core_stages)

    # Final stage: Sort the results chronologically. No $limit is applied.
    pipeline.append({"$sort": {"bar_meta_data.exch_id": 1, "bar_meta_data.symbol": 1, "start_time": 1}})

    return {"agg": pipeline}


# --- Wrapper Function ---
def get_bar_aggregation_pipeline(
    target_bar_type: str,
    end_time_param: str | datetime.datetime | pendulum.DateTime | None = None,
    start_time_param: str | datetime.datetime | pendulum.DateTime | None = None,
    target_bar_counts: int | None = None,
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    User-facing wrapper function to generate a bar aggregation pipeline.
    It delegates to specific internal functions based on whether 'start_time_param'
    or 'target_bar_counts' is provided, ensuring one and only one is used.

    Args:
        target_bar_type: Desired output bar granularity string (e.g., "FiveMin").
        end_time_param: Optional. The latest end time for bars. Defaults to current UTC time.
                        Used in both modes.
        start_time_param: Optional. If provided, all bars between start_time_param and
                          end_time_param are aggregated. Mutually exclusive with target_bar_counts.
                          If provided, '_generate_time_range_bar_pipeline' is called.
        target_bar_counts: Optional. If provided, the N most recent aggregated bars ending at or
                           before end_time_param are returned. Must be > 0 if provided.
                           Mutually exclusive with start_time_param.
                           If provided, '_generate_latest_n_bar_pipeline' is called.
        exch_id_list: Optional list of exchange IDs to filter source data.
        symbol_list: Optional list of symbols to filter source data.

    Returns:
        A dictionary containing the MongoDB aggregation pipeline list under the key "agg".

    Raises:
        ValueError: If input parameters are invalid (e.g., both/neither range params,
                    invalid count, unparsable dates, unsupported target_bar_type).
    """
    # --- Input Validation: Ensure one mode is chosen ---
    if start_time_param is not None and target_bar_counts is not None:
        raise ValueError("Provide EITHER 'start_time_param' OR 'target_bar_counts', not both.")
    if start_time_param is None and target_bar_counts is None:
        # Defaulting to one mode or raising an error are options. Current raises.
        raise ValueError("Provide EITHER 'start_time_param' OR 'target_bar_counts'.")

    # --- Process common end_time_param (used by both modes) ---
    # Default to current UTC time if not provided.
    # Ensure it's a Pendulum DateTime object in UTC for internal consistency.
    processed_end_time_param: pendulum.DateTime
    if end_time_param is None:
        processed_end_time_param = pendulum.now('UTC') # Use pendulum.now() for consistency
    else:
        try:
            # pendulum.instance handles str, datetime.datetime, and pendulum.DateTime
            if not isinstance(end_time_param, pendulum.DateTime): # Check if already Pendulum
                end_time_param = pendulum.instance(end_time_param)
            processed_end_time_param = end_time_param.in_timezone('UTC')
        except Exception as e:
            raise ValueError(f"Could not parse end_time_param: {end_time_param}. Error: {e}") from e

    # --- Determine Mode and Call Appropriate Internal Function ---
    if start_time_param is not None:
        # == Time Range Mode ==
        # This mode is selected if 'start_time_param' is provided.
        # It generates a pipeline to aggregate all bars strictly within the
        # [start_time_param, end_time_param] window.
        processed_start_time_param: pendulum.DateTime
        try:
            if not isinstance(start_time_param, pendulum.DateTime): # Check if already Pendulum
                start_time_param = pendulum.instance(start_time_param)
            processed_start_time_param = start_time_param.in_timezone('UTC')
        except Exception as e:
            raise ValueError(f"Could not parse start_time_param: {start_time_param}. Error: {e}") from e

        if processed_start_time_param >= processed_end_time_param:
             # Log a warning or raise an error if start is not before end.
             # Current implementation proceeds, likely yielding an empty result from DB.
             print(f"Warning: start_time_param ({processed_start_time_param}) is not before "
                   f"end_time_param ({processed_end_time_param}).")

        return _generate_time_range_bar_pipeline(
            target_bar_type=target_bar_type,
            actual_start_time=processed_start_time_param,
            actual_end_time=processed_end_time_param,
            exch_id_list=exch_id_list,
            symbol_list=symbol_list
        )
    elif target_bar_counts is not None:
        # == Latest N Bars Mode ==
        # This mode is selected if 'target_bar_counts' is provided.
        # It generates an optimized pipeline to fetch the 'target_bar_counts'
        # most recent aggregated bars ending at or before 'end_time_param'.
        if not isinstance(target_bar_counts, int) or target_bar_counts <= 0:
             raise ValueError("target_bar_counts must be a positive integer.")

        return _generate_latest_n_bar_pipeline(
             target_bar_type=target_bar_type,
             end_time_param=processed_end_time_param, # Pass the defaulted/parsed end_time
             target_bar_counts=target_bar_counts,
             exch_id_list=exch_id_list,
             symbol_list=symbol_list
             # start_time_buffer_factor uses its default in _generate_latest_n_bar_pipeline
        )
    else:
         # This case should be unreachable due to the initial validation.
         raise ValueError("Internal logic error: No valid mode determined.")

def get_latest_bar_data_agg(
    exch_id_list: List[str] | None = None,
    bar_type_list: List[str] | None = None,
    start_time_param: pendulum.DateTime | None = None,
    end_time_param: pendulum.DateTime | None = None):
    """
    Generates a MongoDB aggregation pipeline to find the latest BarData
    for each unique combination of exchange ID and symbol within a given
    time range, optionally filtered by lists of exchange IDs and bar types.

    Args:
        exch_id_list: A list of exchange IDs to filter by. If None or empty, includes all exchanges.
        bar_type_list: A list of BarType str to filter by. If None or empty, includes all bar types.
        start_time_param: The beginning of the time window (inclusive).
                          Defaults to 20 days before the current UTC time if None.
        end_time_param: The end of the time window (inclusive).
                        Defaults to the current UTC time if None.

    Returns:
        A dictionary containing the aggregation pipeline list under the key "agg".
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
        match_query["bar_meta_data.bar_type"] = {"$in": bar_type_list}

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
    return {"agg": pipeline}

def filter_one_min_bar_data_agg(
    exch_id_list: List[str] | None = None,
    symbol_list: List[str] | None = None,
    start_time_param: pendulum.DateTime | None = None,
    end_time_param: pendulum.DateTime | None = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates a MongoDB aggregation pipeline to filter 'OneMin' bar data.

    This function specifically targets documents where 'bar_meta_data.bar_type' is 'OneMin'.
    It filters these documents based on optional criteria including exchange IDs,
    symbols, and a time window. Time-based filtering is only applied if start_time_param
    and/or end_time_param are provided.

    Args:
        exch_id_list: An optional list of exchange IDs to filter by. If None or empty,
                      documents from all exchanges are included.
        symbol_list: An optional list of symbols to filter by. If None or empty,
                     documents for all symbols are included.
        start_time_param: Optional. If provided, includes only bars with a start_time
                          greater than or equal to this value.
        end_time_param: Optional. If provided, includes only bars with a start_time
                        less than or equal to this value.

    Returns:
        A dictionary containing the aggregation pipeline under the key "agg".
    """
    pipeline: List[Dict[str, Any]] = []
    match_conditions: List[Dict[str, Any]] = []

    # --- Build Filter Conditions ---

    # 1. Hardcoded filter for 'OneMin' bar type.
    match_conditions.append({"bar_meta_data.bar_type": "OneMin"})

    # 2. Add optional filter for the list of exchange IDs.
    if exch_id_list:
        match_conditions.append({"bar_meta_data.exch_id": {"$in": exch_id_list}})

    # 3. Add optional filter for the list of symbols.
    if symbol_list:
        match_conditions.append({"bar_meta_data.symbol": {"$in": symbol_list}})

    # 4. Conditionally build and add the time range filter.
    time_filter = {}
    if start_time_param:
        # Ensure the parameter is a timezone-aware pendulum.DateTime object in UTC
        effective_start_time = pendulum.instance(start_time_param).in_timezone('UTC')
        time_filter["$gte"] = effective_start_time

    if end_time_param:
        # Ensure the parameter is a timezone-aware pendulum.DateTime object in UTC
        effective_end_time = pendulum.instance(end_time_param).in_timezone('UTC')
        time_filter["$lte"] = effective_end_time

    # Only add the time filter to the match conditions if it's not empty.
    if time_filter:
        match_conditions.append({"start_time": time_filter})

    # --- Construct Pipeline Stages ---

    # 1. Combine all conditions into a single $match stage.
    # The $and operator is used for clarity and correctness with multiple conditions.
    pipeline.append({"$match": {"$and": match_conditions}})

    # 2. Add a final sort stage for predictable, chronological output.
    pipeline.append({"$sort": {
        "bar_meta_data.exch_id": 1,
        "bar_meta_data.symbol": 1,
        "start_time": 1  # Sort by time in ascending (chronological) chore.
    }})

    return {"agg": pipeline}
