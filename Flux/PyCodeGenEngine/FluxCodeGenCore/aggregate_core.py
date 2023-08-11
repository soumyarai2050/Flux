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
