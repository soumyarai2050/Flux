# standard imports
from pymongo import MongoClient
import pandas as pd
from pathlib import PurePath
import os
from datetime import datetime

# 3rd party imports
import pendulum


if __name__ == '__main__':

    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['performance_benchmark']
    collection = db['RawPerformanceData']

    # Define the specific date
    start_date = pendulum.parse("2024-04-22T21:42:39.397+00:00")
    last_time = pendulum.parse("2024-04-22T21:58:39.397+00:00")
    # last_time = None

    pipeline = [
        {
            '$match': {
                'start_time': {}
            }
        },
        {
            '$group': {
                '_id': '$callable_name',
                'min': {
                    '$min': '$delta'
                },
                'max': {
                    '$max': '$delta'
                },
                'median': {
                    '$median': {
                        'input': '$delta',
                        'method': 'approximate'
                    }
                },
                'perc_25': {
                    '$percentile': {
                        'p': [
                            0.25
                        ],
                        'input': '$delta',
                        'method': 'approximate'
                    }
                },
                'perc_50': {
                    '$percentile': {
                        'p': [
                            0.5
                        ],
                        'input': '$delta',
                        'method': 'approximate'
                    }
                },
                'perc_75': {
                    '$percentile': {
                        'p': [
                            0.75
                        ],
                        'input': '$delta',
                        'method': 'approximate'
                    }
                },
                'perc_90': {
                    '$percentile': {
                        'p': [
                            0.9
                        ],
                        'input': '$delta',
                        'method': 'approximate'
                    }
                },
                'perc_95': {
                    '$percentile': {
                        'p': [
                            0.95
                        ],
                        'input': '$delta',
                        'method': 'approximate'
                    }
                },
                'count': {
                    '$count': {}
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'callable_name': '$_id',
                'min': 1,
                'max': 1,
                'median': 1,
                'count': 1,
                'perc_25': {
                    '$arrayElemAt': [
                        '$perc_25', 0
                    ]
                },
                'perc_50': {
                    '$arrayElemAt': [
                        '$perc_50', 0
                    ]
                },
                'perc_75': {
                    '$arrayElemAt': [
                        '$perc_75', 0
                    ]
                },
                'perc_90': {
                    '$arrayElemAt': [
                        '$perc_90', 0
                    ]
                },
                'perc_95': {
                    '$arrayElemAt': [
                        '$perc_95', 0
                    ]
                }
            }
        }
    ]

    if start_date:
        pipeline[0]['$match']['start_time']['$gte'] = start_date
    if last_time:
        pipeline[0]['$match']['start_time']['$lte'] = last_time

    result = list(collection.aggregate(pipeline))
    data = pd.DataFrame(result)
    print(data)

    test_report_dir = (PurePath(__file__).parent.parent.parent.parent.parent /
                       "tests" / "CodeGenProjects" / "TradeEngine" / "ProjectGroup" / "test_reports")
    perf_data_dir = test_report_dir / "performance_data"
    if not os.path.exists(perf_data_dir):
        os.makedirs(perf_data_dir)

    datetime_str: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f'performance_data_{datetime_str}.csv'
    data.to_csv(perf_data_dir / file_name, columns=['callable_name', 'count', 'min', 'max', 'median', 'perc_25',
                                                    'perc_50', 'perc_75', 'perc_90', 'perc_95'])

