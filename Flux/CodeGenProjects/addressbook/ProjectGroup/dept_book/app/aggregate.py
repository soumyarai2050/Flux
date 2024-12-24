from pendulum import DateTime
from typing import List, Dict

# below import is required in routes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_msgspec_model import *


def get_dict_list_for_bar_meta_data_match(symbol: str, exch_id: str, bar_type: BarType) -> List[Dict[str, Any]]:
    return [
        {
            'bar_meta_data.symbol': symbol
        },
        {
            'bar_meta_data.exch_id': exch_id
        },
        {
            'bar_meta_data.bar_type': bar_type.value
        }
    ]

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
