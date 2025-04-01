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
