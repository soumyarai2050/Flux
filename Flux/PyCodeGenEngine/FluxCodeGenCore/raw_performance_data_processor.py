# standard imports
import time
from typing import Type, List, Dict, Any
import pandas
import asyncio

# 3rd part imports
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.aggregate_core import (
    get_raw_perf_data_callable_names_pipeline, get_raw_performance_data_from_callable_name_agg_pipeline)
from FluxPythonUtils.scripts.utility_functions import (read_mongo_collection_as_dataframe,
                                                       execute_tasks_list_with_all_completed)


class MongoConnectionReqs(BaseModel):
    db: str
    collection: str
    host: str | None = 'localhost'
    port: int | None = 27017
    username: str | None = None
    password: str | None = None


class RawPerformanceDataProcessor:

    def __init__(self, web_client_object,
                 processed_performance_analysis_model_type: Type[BaseModel],
                 mongo_connection_reqs: MongoConnectionReqs,
                 config_yaml_dict: Dict):
        self.web_client_object = web_client_object
        self.processed_performance_analysis_model_type: Type[BaseModel] = processed_performance_analysis_model_type
        self.mongo_connection_reqs: MongoConnectionReqs = mongo_connection_reqs
        self.loaded_processed_performance_analysis_obj_from_db: List[processed_performance_analysis_model_type] = (
            self.web_client_object.get_all_processed_performance_analysis_client())
        self.callable_names_having_entry_to_id_in_db_dict: Dict[str, Any] = {}
        for obj in self.loaded_processed_performance_analysis_obj_from_db:
            self.callable_names_having_entry_to_id_in_db_dict[obj.callable_name] = obj.id
        self.wait_time = config_yaml_dict.get("raw_performance_data_processor_loop_wait")
        if self.wait_time is None:
            self.wait_time = 2  # default

    def get_callable_names_list(self) -> pandas.DataFrame:
        return read_mongo_collection_as_dataframe(self.mongo_connection_reqs.db,
                                                  self.mongo_connection_reqs.collection,
                                                  get_raw_perf_data_callable_names_pipeline().get("aggregate"),
                                                  self.mongo_connection_reqs.host,
                                                  self.mongo_connection_reqs.port,
                                                  self.mongo_connection_reqs.username,
                                                  self.mongo_connection_reqs.password,
                                                  no_id=False)

    async def create_update_processed_performance_analysis_for_callable(self, callable_name: str) -> None:
        raw_perf_data_df = (
            read_mongo_collection_as_dataframe(self.mongo_connection_reqs.db,
                                               self.mongo_connection_reqs.collection,
                                               get_raw_performance_data_from_callable_name_agg_pipeline(
                                                   callable_name).get("aggregate"),
                                               self.mongo_connection_reqs.host,
                                               self.mongo_connection_reqs.port,
                                               self.mongo_connection_reqs.username,
                                               self.mongo_connection_reqs.password,
                                               no_id=False))

        raw_perf_data_delta_series: pandas.Series = raw_perf_data_df["delta"]
        min_val = raw_perf_data_delta_series.min().round(6)
        max_val = raw_perf_data_delta_series.max().round(6)
        avg_val = raw_perf_data_delta_series.mean().round(6)
        std_dev = raw_perf_data_delta_series.std(ddof=0).round(6)   # use ddof to return 0 if std_dev is not calculable
        percentiles: pandas.Series = (
            raw_perf_data_delta_series.quantile([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]).round(6))

        processed_perf_analysis = self.processed_performance_analysis_model_type(callable_name=callable_name,
                                                                                 min=min_val, max=max_val,
                                                                                 avg=avg_val, std_dev=std_dev,
                                                                                 per_10=percentiles[0.1],
                                                                                 per_20=percentiles[0.2],
                                                                                 per_30=percentiles[0.3],
                                                                                 per_40=percentiles[0.4],
                                                                                 per_50=percentiles[0.5],
                                                                                 per_60=percentiles[0.6],
                                                                                 per_70=percentiles[0.7],
                                                                                 per_80=percentiles[0.8],
                                                                                 per_90=percentiles[0.9])

        if callable_name in self.callable_names_having_entry_to_id_in_db_dict:
            processed_perf_analysis_json = jsonable_encoder(processed_perf_analysis, by_alias=True, exclude_none=True)
            processed_perf_analysis_json["_id"] = self.callable_names_having_entry_to_id_in_db_dict[callable_name]
            self.web_client_object.patch_processed_performance_analysis_client(processed_perf_analysis_json)
        else:
            created_obj = self.web_client_object.create_processed_performance_analysis_client(processed_perf_analysis)
            self.callable_names_having_entry_to_id_in_db_dict[callable_name] = created_obj.id

    async def handle_create_update_processed_performance_analysis(self):
        while True:
            callable_names_n_total_calls_df: pandas.DataFrame = self.get_callable_names_list()

            task_list: List[asyncio.Task] = []
            for _, callable_name_n_total_calls in callable_names_n_total_calls_df.iterrows():
                callable_name = callable_name_n_total_calls["callable_name"]
                task: asyncio.Task = asyncio.create_task(
                    self.create_update_processed_performance_analysis_for_callable(callable_name),
                    name=callable_name
                )
                task_list.append(task)

                await execute_tasks_list_with_all_completed(task_list, self.processed_performance_analysis_model_type)
                task_list.clear()

            time.sleep(self.wait_time)

    def run(self):
        asyncio.run(self.handle_create_update_processed_performance_analysis())
