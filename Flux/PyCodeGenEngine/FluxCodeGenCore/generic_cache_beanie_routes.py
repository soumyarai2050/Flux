import logging
from fastapi import HTTPException
from Flux.PyCodeGenEngine.FluxCodeGenCore.default_web_response import DefaultWebResponse
from FluxPythonUtils.scripts.http_except_n_log_error import http_except_n_log_error


id_not_found = DefaultWebResponse(msg="Id not Found")
del_success = DefaultWebResponse(msg="Deletion Successful")


def log_n_except(err_str: str, status_code: int = 500):
    logging.exception(err_str)
    raise HTTPException(status_code=status_code, detail=err_str)


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_get_all(document):
    document_list = list(document.get_all_cached_obj().values())
    return document_list


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_post(document, document_obj):
    try:
        await document_obj.create()
    except Exception as e:
        log_n_except(str(e))
    success = document.add_data_in_cache(document_obj.id, document_obj)
    if not success:
        err_str = f'{document_obj.id} already exists in {document.__name__} cache dict'
        log_n_except(err_str, 404)
    return document_obj


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_get(document, document_obj_id):
    cached_document_dict = document.get_all_cached_obj()
    if document_obj_id in cached_document_dict:
        fetched_document_obj = cached_document_dict[document_obj_id]
    else:
        fetched_document_obj = await document.get(document_obj_id)
    if not fetched_document_obj:
        err_str = id_not_found.format_msg(document.__name__, document_obj_id)
        log_n_except(err_str, 404)
    else:
        if document_obj_id not in cached_document_dict:
            document.add_data_in_cache(document_obj_id, fetched_document_obj)
        return fetched_document_obj


async def _underlying_beanie_patch_n_put(document, document_obj_updated, request_obj, is_put: bool = True):
    response_obj = await document.get(document_obj_updated.id)
    if response_obj is None:
        err_str = id_not_found.format_msg(document.__name__, document_obj_updated.id)
        log_n_except(err_str)
    else:
        try:
            await response_obj.update(request_obj)
        except Exception as e:
            log_n_except(str(e))
        if is_put:
            success = document.replace_data_in_cache(response_obj.id, document_obj_updated)
        else:
            success = document.patch_data_in_cache(response_obj.id, document_obj_updated)
        if not success:
            err_str = f'{document_obj_updated.id} not exists in {document.__name__} cache dict'
            log_n_except(err_str, 404)
        return response_obj


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_put(document, document_obj_updated):
    request_obj = {'$set': document_obj_updated.model_dump().items()}
    return await _underlying_beanie_patch_n_put(document, document_obj_updated, request_obj, True)


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_patch(document, document_obj_updated):
    req_dict_without_none_val = {k: v for k, v in document_obj_updated.model_dump(exclude_unset=True,
                                                                                  exclude_none=True).items()}
    request_obj = {'$set': req_dict_without_none_val.items()}
    return await _underlying_beanie_patch_n_put(document, document_obj_updated, request_obj, False)


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_delete(document, document_obj_id):
    record = await document.get(document_obj_id)
    if not record:
        err_str = id_not_found.format_msg(document.__name__, document_obj_id)
        log_n_except(err_str, 404)
    else:
        try:
            await record.delete()
        except Exception as e:
            log_n_except(str(e))
        success = document.delete_data_in_cache(document_obj_id)
        if not success:
            err_str = f'{document_obj_id} not exists in {document.__name__} cache dict'
            log_n_except(err_str, 404)
        del_success.id = document_obj_id
        return del_success


@http_except_n_log_error(status_code=500)
async def generic_cache_beanie_index(document, field_name: str, index_value):
    fetched_document_obj_list = [obj for obj in list(document.get_all_cached_obj().values())
                                 if obj.model_dump()[field_name] == index_value]
    return fetched_document_obj_list
