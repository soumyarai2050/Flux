# standard import
import logging
import timeit
import functools

# 3rd party imports
from pendulum import DateTime

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_float


def get_timeit_pattern() -> str:
    return "_timeit_"


def get_timeit_field_separator() -> str:
    return "~"


def get_time_it_log_pattern(callable_name: str, start_time: DateTime, delta: float):
    time_it_pattern: str = get_timeit_pattern()
    field_separator: str = get_timeit_field_separator()
    pattern_str = (f"{time_it_pattern}{callable_name}{field_separator}{start_time}"
                   f"{field_separator}{delta}{time_it_pattern}")
    return pattern_str


# Decorator Function
lvl_names_mapping = logging.getLevelNamesMapping()
is_timing_logging_enabled = False
if "TIMING" in lvl_names_mapping:
    logger = logging.getLogger()
    if logger.getEffectiveLevel() <= logging.TIMING:
        is_timing_logging_enabled = True

if is_timing_logging_enabled:
    def perf_benchmark(func_callable):
        @functools.wraps(func_callable)
        async def benchmarker(*args, **kwargs):
            call_date_time = DateTime.utcnow()
            start_time = timeit.default_timer()
            return_val = await func_callable(*args, **kwargs)
            end_time = timeit.default_timer()
            delta = parse_to_float(f"{(end_time - start_time):.6f}")

            pattern_str = get_time_it_log_pattern(func_callable.__name__, call_date_time, delta)
            logging.timing(pattern_str)
            return return_val
        return benchmarker
else:
    def perf_benchmark(func_callable):
        async def benchmarker(*args, **kwargs):
            return_val = await func_callable(*args, **kwargs)
            return return_val

        return benchmarker


if is_timing_logging_enabled:
    def perf_benchmark_sync_callable(func_callable):
        def benchmarker(*args, **kwargs):
            call_date_time = DateTime.utcnow()
            start_time = timeit.default_timer()
            return_val = func_callable(*args, **kwargs)
            end_time = timeit.default_timer()
            delta = parse_to_float(f"{(end_time - start_time):.6f}")

            pattern_str = get_time_it_log_pattern(func_callable.__name__, call_date_time, delta)
            logging.timing(pattern_str)
            return return_val
        return benchmarker
else:
    def perf_benchmark_sync_callable(func_callable):
        def benchmarker(*args, **kwargs):
            return_val = func_callable(*args, **kwargs)
            return return_val
        return benchmarker