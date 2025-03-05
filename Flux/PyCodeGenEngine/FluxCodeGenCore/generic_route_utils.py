# standard imports
from typing import Dict
import timeit
import functools
import pendulum
import os
import logging

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int, parse_to_float
from Flux.PyCodeGenEngine.FluxCodeGenCore.perf_benchmark_decorators import get_time_it_log_pattern

log_generic_timings = parse_to_int(log_generic_timings_env_var) \
    if ((log_generic_timings_env_var := os.getenv("LogGenericTiming")) is not None and
        len(log_generic_timings_env_var)) else None


if log_generic_timings is not None and log_generic_timings == 1:
    # Decorator Function
    def generic_perf_benchmark(func_callable):
        @functools.wraps(func_callable)
        async def benchmarker(*args, **kwargs):
            call_date_time = pendulum.DateTime.utcnow()
            start_time = timeit.default_timer()
            return_val = await func_callable(*args, **kwargs)
            end_time = timeit.default_timer()
            delta = parse_to_float(f"{(end_time - start_time):.6f}")

            pattern_str = get_time_it_log_pattern(func_callable.__name__, call_date_time, delta)
            pattern_str += f" model_type: {args[0]}"
            logging.timing(pattern_str)
            return return_val
        return benchmarker
else:
    # Decorator Function
    def generic_perf_benchmark(func_callable):
        async def benchmarker(*args, **kwargs):
            return_val = await func_callable(*args, **kwargs)
            return return_val
        return benchmarker


def get_aggregate_pipeline(encap_agg_pipeline: Dict):
    filter_tuple_list = encap_agg_pipeline.get("redact")
    match_tuple_list = encap_agg_pipeline.get("match")  # [(key1: value1), (key2: value2)]
    additional_agg = encap_agg_pipeline.get("agg")
    agg_pipeline = []
    if match_tuple_list is not None:
        agg_pipeline.append({"$match": {}})
        for match_tuple in match_tuple_list:
            if len(match_tuple) != 2:
                raise Exception(f"Expected minimum 2 values (field-name, field-value) in tuple found match_tuple: "
                                f"{match_tuple} in match_tuple_list: {match_tuple_list}")
            match_variable_name, match_variable_value = match_tuple
            if match_variable_name is not None and len(match_variable_name) != 0:
                if match_variable_value is not None:
                    match_pipeline = agg_pipeline[0].get("$match")
                    if match_pipeline is None:
                        agg_pipeline[0]["$match"] = {match_variable_name: {"$in": match_variable_value}}
                    else:
                        match_pipeline[match_variable_name] = {"$in": match_variable_value}
                else:
                    raise Exception(
                        f"Error: match_variable_name passed as: {match_variable_name}, while match_variable_value "
                        f"was passed None - not supported")
    if filter_tuple_list is not None:
        for filter_tuple in filter_tuple_list:
            if len(filter_tuple) < 2:
                raise Exception(f"Expected minimum 2 values (field-name, field-value) in tuple found filter_tuple: "
                                f"{filter_tuple} in filter_tuple_list: {filter_tuple_list}")
            filter_list = list(filter_tuple)
            filtered_variable_name = filter_list[0]
            filter_list.remove(filter_list[0])
            # $in expects list with 1st entry as variable-name, and 2nd entry as list of variable-values
            redact_data_filter = \
                {
                    "$redact": {
                        "$cond": {
                            "if": {"$or": [{"$in": []}, {"$not": ""}]},
                            "then": "$$DESCEND",
                            "else": "$$PRUNE"
                        }
                    }
                }
            updated_filtered_variable_name = "$" + filtered_variable_name
            redact_data_filter["$redact"]["$cond"]["if"]["$or"][0]["$in"].append(updated_filtered_variable_name)
            redact_data_filter["$redact"]["$cond"]["if"]["$or"][0]["$in"].append(filter_list)
            redact_data_filter["$redact"]["$cond"]["if"]["$or"][1]["$not"] = updated_filtered_variable_name
            agg_pipeline.append(redact_data_filter)

    if additional_agg is not None:
        agg_pipeline.extend(additional_agg)
        return agg_pipeline
    elif len(agg_pipeline) != 0:
        return agg_pipeline
    else:
        return encap_agg_pipeline.get("aggregate")
