# standard imports
from typing import List, Dict, Any, Callable
from queue import Queue
import os
import logging
import asyncio

os.environ["ModelType"] = "msgspec"
# project imports
from Flux.CodeGenProjects.performance_benchmark.generated.ORMModel.performance_benchmark_service_model_imports import (
    ProcessedPerformanceAnalysis)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import performance_benchmark_service_http_client


class RawPerformanceDataProcessor:
    underlying_read_processed_performance_analysis_http: Callable[..., Any] | None = None

    asyncio_loop = None
    new_raw_performance_data_queue: Queue = Queue()
    callable_names_having_entry_to_id_in_db_dict: Dict[str, Any] = {}

    def __init__(self):
        pass

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_http_routes import (
            underlying_read_processed_performance_analysis_http)
        cls.underlying_read_processed_performance_analysis_http = underlying_read_processed_performance_analysis_http

    @classmethod
    async def load_existing_processed_performance_analysis(cls):
        loaded_processed_performance_analysis_obj_from_db: List[ProcessedPerformanceAnalysis] = (
            await cls.underlying_read_processed_performance_analysis_http())

        for obj in loaded_processed_performance_analysis_obj_from_db:
            cls.callable_names_having_entry_to_id_in_db_dict[obj.callable_name] = obj.id

    @classmethod
    def run(cls):
        if cls.asyncio_loop is None:
            logging.exception("asyncio_loop class data member found as None, must be set by caller before calling "
                              "run - exiting RawPerformanceDataProcessor.run()")
            return None

        cls.initialize_underlying_http_callables()

        run_coro = cls.load_existing_processed_performance_analysis()
        future = asyncio.run_coroutine_threadsafe(run_coro, cls.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e:
            err_str_ = (f"load_existing_processed_performance_analysis failed with exception: {e} - "
                        f"exiting RawPerformanceDataProcessor.run()")
            logging.exception(err_str_)
            return None

        while 1:
            new_raw_performance_data = cls.new_raw_performance_data_queue.get()

        # import pandas as pd
        # raw_perf_data = performance_benchmark_service_http_client.get_all_raw_performance_data_client()
        # df = pd.DataFrame([r.__dict__ for r in raw_perf_data])
        # print(type(df))
        # print(df)


RawPerformanceDataProcessor.run()
