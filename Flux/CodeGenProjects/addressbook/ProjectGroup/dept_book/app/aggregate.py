from pendulum import DateTime
from typing import List

# below import is required in routes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


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

