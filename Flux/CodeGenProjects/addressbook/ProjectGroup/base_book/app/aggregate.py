from typing import List, Tuple
from pendulum import DateTime
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import *


def get_symbol_side_underlying_account_cumulative_fill_qty(symbol: str, side: str):
    return {"aggregate": [
        {
            '$match': {
                '$and': [
                    {
                        'fill_symbol': symbol
                    },
                    {
                        'fill_side': side
                    }
                ]
            }
        },
        {
            '$setWindowFields': {
                'partitionBy': {
                    'underlying_account': '$underlying_account'
                },
                'sortBy': {
                    'fill_date_time': 1.0
                },
                'output': {
                    'underlying_account_cumulative_fill_qty': {
                        '$sum': '$fill_qty',
                        'window': {
                            'documents': [
                                'unbounded', 'current'
                            ]
                        }
                    }
                }
            }
        },
        {
            "$sort": {"fill_date_time": -1},
        }
    ]}


def get_last_n_chore_ledgers_from_chore_id(chore_id: str, ledger_count: int):
    return {"aggregate": [
        {
            "$match": {
                "chore.chore_id": chore_id
            },
        },
        {
            "$sort": {"_id": -1},
        },
        {
            "$limit": ledger_count
        }
    ]}


def get_objs_from_symbol(symbol: str):
    return {"aggregate": [
        {
            "$match": {
                "symbol": symbol
            }
        }
    ]}

