from pendulum import DateTime
from typing import List


def get_pair_side_brief_from_side(symbol: str):
    return {"aggregate": [
        {
            "$unwind": {
                "path": "$pair_side_brief"
            }
        },
        {
            "$match": {
                "pair_side_brief.security.sec_id": symbol
            }
        },
        {
            "$sort": {
                "pair_side_brief.last_update_date_time": -1.0
            }
        }
    ]}


def get_bar_data_from_symbol_n_start_n_end_datetime(symbol: str, start_datetime: DateTime | None = None,
                                                    end_datetime: DateTime | None = None):
    agg_pipline = {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        },
        {
            "$match": {}
        }
    ]}

    if start_datetime is not None and end_datetime is None:
        agg_pipline["aggregate"][1]["$match"] = {
            '$expr': {
                '$gte': [
                    '$datetime', start_datetime
                ]
            }
        }
    elif end_datetime is not None and start_datetime is None:
        agg_pipline["aggregate"][1]["$match"] = {
            '$expr': {
                '$lte': [
                    '$datetime', end_datetime
                ]
            }
        }
    elif start_datetime is not None and end_datetime is not None:
        agg_pipline["aggregate"][1]["$match"] = {

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

    return agg_pipline


def get_symbol_overview_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}


def get_limited_objs(limit: int):
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
                "$limit": -limit
            }
        ]
    else:
        return []


def get_latest_bar_data_for_each_symbol():
    return {"aggregate": [
        {
            '$group': {
                '_id': '$symbol_n_exch_id.symbol',
                'max_start_time': {
                    '$max': '$start_time'
                },
                'id': {
                    '$max': '$_id'
                }
            }
        }, {
            '$project': {
                '_id': '$id',
                'symbol_n_exch_id': {
                    'symbol': '$_id',
                    'exch_id': 'NA'
                },
                'start_time': '$max_start_time',
                'end_time': '$max_start_time'
            }
        }
    ]}


def get_vwap_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': [
                    {
                        'symbol_n_exch_id.symbol': symbol
                    },
                    {
                        'symbol_n_exch_id.exch_id': exch_id
                    }
                ]
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'vwap': '$vwap'
                }
            },
        },
        {
            '$group': {
                '_id': '$symbol_n_exch_id',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': '$_id',
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


def get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': [
                    {
                        'symbol_n_exch_id.symbol': symbol
                    },
                    {
                        'symbol_n_exch_id.exch_id': exch_id
                    }
                ]
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'vwap': '$vwap',
                    'vwap_change': '$vwap_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$symbol_n_exch_id',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': '$_id',
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


def get_vwap_change_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # Code generated function
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': [
                    {
                        'symbol_n_exch_id.symbol': symbol
                    },
                    {
                        'symbol_n_exch_id.exch_id': exch_id
                    }
                ]
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'vwap_change': '$vwap_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$symbol_n_exch_id',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': '$_id',
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


# {
#     "$merge": {
#         "into": "MarketDepth",
#         "on": "_id",
#         "whenMatched": "replace",
#         "whenNotMatched": "insert"
#     }
# }
# {
#     "$out": {
#         "db": "mobile_book_tech_new_test",
#         "coll": "MarketDepth"
#     }
# }

def get_premium_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': [
                    {
                        'symbol_n_exch_id.symbol': symbol
                    },
                    {
                        'symbol_n_exch_id.exch_id': exch_id
                    }
                ]
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'premium': '$premium'
                }
            },
        },
        {
            '$group': {
                '_id': '$symbol_n_exch_id',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': '$_id',
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


def get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': [
                    {
                        'symbol_n_exch_id.symbol': symbol
                    },
                    {
                        'symbol_n_exch_id.exch_id': exch_id
                    }
                ]
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'premium': '$premium',
                    'premium_change': '$premium_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$symbol_n_exch_id',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': '$_id',
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


def get_premium_change_projection_from_bar_data_agg_pipeline(symbol: str, exch_id: str, start_date_time: DateTime | None = None, end_date_time: DateTime | None = None, id_list: List[int] | None = None):
    # shift this function to aggregate.py file of project and remove this comment afterward
    agg_pipeline = [
        {
            '$match': {},
        },
        {
            '$match': {
                '$and': [
                    {
                        'symbol_n_exch_id.symbol': symbol
                    },
                    {
                        'symbol_n_exch_id.exch_id': exch_id
                    }
                ]
            }
        },
        {
            '$match': {},
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': 1,
                'projection_models': {
                    'start_time': '$start_time',
                    'premium_change': '$premium_change'
                }
            },
        },
        {
            '$group': {
                '_id': '$symbol_n_exch_id',
                'projection_models': {
                    '$push': '$projection_models'
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'symbol_n_exch_id': '$_id',
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


if __name__ == "__main__":
    import pendulum

    print(get_bar_data_from_symbol_n_start_n_end_datetime("1A0.SI", pendulum.parse("2020-11-13T16:00:00.000+00:00")))
