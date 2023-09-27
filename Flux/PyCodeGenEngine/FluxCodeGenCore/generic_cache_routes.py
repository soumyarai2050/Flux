# system imports
import os
from typing import Any, Final, Type, List, Tuple, Dict
import logging

# other package imports
from fastapi import HTTPException
from beanie.odm.documents import DocType, InsertManyResult
from fastapi.encoders import jsonable_encoder

# project specific imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error
from FluxPythonUtils.scripts.utility_functions import compare_n_patch_dict, convert_camel_case_to_specific_case, \
    compare_n_patch_list
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_beanie_routes import generic_perf_benchmark, \
    assign_missing_ids_n_handle_date_time_type
from Flux.CodeGenProjects.pair_strat_engine.generated.FastApi.strat_manager_service_http_client import \
    StratManagerServiceHttpClient
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_beanie_routes import get_beanie_host_n_port, \
    underlying_generic_patch_all_http, _generic_put_all_http


"""
1. FilterAggregate [only filters the returned value]
2. UpdateAggregate [ modifies data in DB based on aggregate query and returns updated data ]
3. Create : FilterAggregate for return param and UpdateAggregate for massaging data post insert
4. Read, ReadAll : FilterAggregate for return param
5. Delete : UpdateAggregate for massaging data post delete
"""

id_not_found: Final[DefaultWebResponse] = DefaultWebResponse(msg="Id not Found")
del_success: Final[DefaultWebResponse] = DefaultWebResponse(msg="Deletion Successful")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_http(pydantic_class_type, project_name: str, pydantic_obj,
                            filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None,
                            has_links: bool = False):
    with pydantic_class_type._mutex:
        if pydantic_obj.id not in pydantic_class_type._cache_obj_id_to_obj_dict:
            pydantic_class_type._cache_obj_id_to_obj_dict[pydantic_obj.id] = pydantic_obj

            # saving to db
            host, port = get_beanie_host_n_port(project_name)
            beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
            pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
            beanie_web_client_post = getattr(beanie_web_client, f"create_{pydantic_class_name_snake_cased}_client")
            beanie_web_client_post(pydantic_obj)
            return pydantic_obj
        else:
            raise HTTPException(status_code=400,
                                detail=f"Id {pydantic_obj.id} already exists for model {pydantic_class_type}")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_post_all_http(pydantic_class_type: Type[DocType], project_name: str,
                                pydantic_obj_list: List[DocType], filter_agg_pipeline: Any = None,
                                update_agg_pipeline: Any = None, has_links: bool = False):
    with pydantic_class_type._mutex:
        if any(pydantic_obj.id not in pydantic_class_type._cache_obj_id_to_obj_dict
               for pydantic_obj in pydantic_obj_list):
            for pydantic_obj in pydantic_obj_list:
                pydantic_class_type._cache_obj_id_to_obj_dict[pydantic_obj.id] = pydantic_obj

            # saving to db
            host, port = get_beanie_host_n_port(project_name)
            beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
            pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
            beanie_web_client_post_all = getattr(beanie_web_client, f"create_all_{pydantic_class_name_snake_cased}_client")
            beanie_web_client_post_all(pydantic_obj_list)
            return pydantic_obj_list
        else:
            already_existing_id = \
                list(set([pydantic_obj.id for pydantic_obj in pydantic_obj_list]) -
                     set(pydantic_class_type._cache_obj_id_to_obj_dict.keys()))
            raise HTTPException(status_code=400,
                                detail=f"Ids {already_existing_id} already exist for model {pydantic_class_type}")


async def _underlying_patch_n_put_all(pydantic_class_type,
                                      stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocType, Dict]],
                                      filter_agg_pipeline: Any = None,
                                      update_agg_pipeline: Any = None, has_links: bool = False):
    with pydantic_class_type._mutex:
        updated_obj_list = []
        for _, updated_pydantic_obj_dict in stored_pydantic_obj_n_updated_obj_dict_tuple_list:
            if (obj_id := updated_pydantic_obj_dict.get(
                    "_id")) in pydantic_class_type._cache_obj_id_to_obj_dict:
                pydantic_class_type._cache_obj_id_to_obj_dict[obj_id] = \
                    pydantic_class_type(**updated_pydantic_obj_dict)
                updated_obj_list.append(pydantic_class_type._cache_obj_id_to_obj_dict[obj_id])
            else:
                raise HTTPException(status_code=400,
                                    detail=f"Id {obj_id} doesn't exist already for model {pydantic_class_type}")
        return updated_obj_list


async def _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj, pydantic_obj_updated,
                                  updated_pydantic_obj_dict, filter_agg_pipeline: Any = None,
                                  update_agg_pipeline: Any = None, has_links: bool = False):
    with pydantic_class_type._mutex:
        if (obj_id := updated_pydantic_obj_dict.get("_id")) in pydantic_class_type._cache_obj_id_to_obj_dict:
            pydantic_class_type._cache_obj_id_to_obj_dict[obj_id] = pydantic_class_type(**updated_pydantic_obj_dict)
            return pydantic_class_type._cache_obj_id_to_obj_dict[obj_id]
        else:
            raise HTTPException(status_code=400,
                                detail=f"Id {obj_id} doesn't exist already for model {pydantic_class_type}")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_http(pydantic_class_type, project_name: str, stored_pydantic_obj, pydantic_obj_updated,
                           filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None, has_links: bool = False):
    updated_obj = await _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj,
                                                pydantic_obj_updated, pydantic_obj_updated.dict(by_alias=True),
                                                filter_agg_pipeline,
                                                update_agg_pipeline, has_links)
    # saving to db
    host, port = get_beanie_host_n_port(project_name)
    beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
    pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
    beanie_web_client_put = getattr(beanie_web_client, f"put_{pydantic_class_name_snake_cased}_client")
    beanie_web_client_put(updated_obj)

    return updated_obj


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_put_all_http(pydantic_class_type, project_name: str, stored_pydantic_obj_list,
                               pydantic_obj_updated_list, filter_agg_pipeline: Any = None,
                               update_agg_pipeline: Any = None, has_links: bool = False):
    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocType, Dict]] = \
        _generic_put_all_http(stored_pydantic_obj_list, pydantic_obj_updated_list)
    updated_obj_list = await _underlying_patch_n_put_all(pydantic_class_type,
                                                         stored_pydantic_obj_n_updated_obj_dict_tuple_list,
                                                         filter_agg_pipeline,
                                                         update_agg_pipeline, has_links)
    # saving to db
    host, port = get_beanie_host_n_port(project_name)
    beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
    pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
    beanie_web_client_put_all = getattr(beanie_web_client, f"put_all_{pydantic_class_name_snake_cased}_client")
    beanie_web_client_put_all(updated_obj_list)
    return updated_obj_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_http(pydantic_class_type, project_name: str, stored_pydantic_obj, pydantic_obj_update_json,
                             filter_agg_pipeline: Any = None, update_agg_pipeline: Any = None, has_links: bool = False):
    assign_missing_ids_n_handle_date_time_type(pydantic_class_type, pydantic_obj_update_json,
                                               ignore_handling_datetime=True)
    updated_pydantic_obj_dict = compare_n_patch_dict(stored_pydantic_obj.dict(by_alias=True),
                                                     pydantic_obj_update_json)
    updated_obj = await _underlying_patch_n_put(pydantic_class_type, stored_pydantic_obj,
                                                pydantic_obj_update_json, updated_pydantic_obj_dict,
                                                filter_agg_pipeline, update_agg_pipeline, has_links)
    # saving to db
    host, port = get_beanie_host_n_port(project_name)
    beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
    pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
    beanie_web_client_patch = getattr(beanie_web_client, f"patch_{pydantic_class_name_snake_cased}_client")
    beanie_web_client_patch(pydantic_obj_update_json)

    return updated_obj


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_patch_all_http(pydantic_class_type, project_name: str, stored_pydantic_obj_list,
                                 pydantic_obj_update_json_list, filter_agg_pipeline: Any = None,
                                 update_agg_pipeline: Any = None, has_links: bool = False):
    stored_pydantic_obj_n_updated_obj_dict_tuple_list: List[Tuple[DocType, Dict]] = \
        underlying_generic_patch_all_http(pydantic_class_type, stored_pydantic_obj_list,
                                          pydantic_obj_update_json_list, ignore_datetime_handling=True)

    updated_obj = await _underlying_patch_n_put_all(pydantic_class_type,
                                                    stored_pydantic_obj_n_updated_obj_dict_tuple_list,
                                                    filter_agg_pipeline, update_agg_pipeline, has_links)
    # saving to db
    host, port = get_beanie_host_n_port(project_name)
    beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
    pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
    beanie_web_client_patch = getattr(beanie_web_client, f"patch_all_{pydantic_class_name_snake_cased}_client")
    beanie_web_client_patch(pydantic_obj_update_json_list)

    return updated_obj


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_delete_http(pydantic_class_type, project_name: str, pydantic_dummy_model,
                              pydantic_obj, update_agg_pipeline: Any = None, has_links: bool = False):
    with pydantic_class_type._mutex:
        if (obj_id := pydantic_obj.id) in pydantic_class_type._cache_obj_id_to_obj_dict:
            del pydantic_class_type._cache_obj_id_to_obj_dict[obj_id]
            del_success.id = pydantic_obj.id

            # saving in db
            host, port = get_beanie_host_n_port(project_name)
            beanie_web_client = StratManagerServiceHttpClient.set_or_get_if_instance_exists(host, port)
            pydantic_class_name_snake_cased = convert_camel_case_to_specific_case(pydantic_class_type.__name__)
            beanie_web_client_delete = getattr(beanie_web_client, f"delete_{pydantic_class_name_snake_cased}_client")
            beanie_web_client_delete(pydantic_obj.id)

            return del_success
        else:
            raise HTTPException(status_code=400,
                                detail=f"Id {obj_id} doesn't exist already for model {pydantic_class_type}")


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_http(pydantic_class_type, project_name: str, filter_agg_pipeline: Any = None,
                            has_links: bool = False, read_ids_list: List[Any] | None = None, projection_model=None,
                            projection_filter: Dict | None = None):
    # todo: projection handling in cache
    with pydantic_class_type._mutex:
        if read_ids_list is None:
            obj_list = list(pydantic_class_type._cache_obj_id_to_obj_dict.values())
            return list(reversed(obj_list))
        else:
            obj_list = []
            for obj_id in read_ids_list:
                fetched_obj = pydantic_class_type._cache_obj_id_to_obj_dict.get(obj_id)
                if fetched_obj is not None:
                    obj_list.append(fetched_obj)
                else:
                    raise HTTPException(status_code=400,
                                        detail=f"Id {obj_id} doesn't exist already for model {pydantic_class_type}")
            return obj_list


@http_except_n_log_error(status_code=500)
@generic_perf_benchmark
async def generic_read_by_id_http(pydantic_class_type, project_name: str, pydantic_obj_id,
                                  filter_agg_pipeline: Any = None, has_links: bool = False):
    with pydantic_class_type._mutex:
        if pydantic_obj_id in pydantic_class_type._cache_obj_id_to_obj_dict:
            return pydantic_class_type._cache_obj_id_to_obj_dict[pydantic_obj_id]
        else:
            raise HTTPException(status_code=400,
                                detail=f"Id {pydantic_obj_id} doesn't exist for model {pydantic_class_type}")
