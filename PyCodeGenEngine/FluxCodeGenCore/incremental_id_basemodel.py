import logging
from typing import ClassVar, Dict, Any, List
from threading import Lock
from re import sub
from pydantic import BaseModel


def to_camel(value):
    value = sub(r"(_|-)+", " ", value).title().replace(" ", "")
    return "".join([value[0].lower(), value[1:]])


class CacheBaseModel(BaseModel):
    _cache_obj_id_to_obj_dict: ClassVar[Dict[Any, Any]] = {}
    _mutex: ClassVar[Lock] = Lock()

    @classmethod
    def get_all_cached_obj(cls) -> Dict[Any, Any]:
        return cls._cache_obj_id_to_obj_dict

    @classmethod
    def add_data_in_cache(cls, obj_id: Any, obj: Any) -> bool:
        with cls._mutex:
            if obj_id in cls._cache_obj_id_to_obj_dict:
                return False
            else:
                cls._cache_obj_id_to_obj_dict[obj_id] = obj
                return True

    @classmethod
    def get_data_from_cache(cls, obj_id: Any) -> Any | None:
        with cls._mutex:
            if obj_id not in cls._cache_obj_id_to_obj_dict:
                return None
            else:
                return cls._cache_obj_id_to_obj_dict[obj_id]

    @classmethod
    def replace_data_in_cache(cls, obj_id: Any, obj: Any) -> bool:
        with cls._mutex:
            if obj_id not in cls._cache_obj_id_to_obj_dict:
                return False
            else:
                cls._cache_obj_id_to_obj_dict[obj_id] = obj
                return True

    @classmethod
    def delete_data_in_cache(cls, obj_id: Any) -> bool:
        with cls._mutex:
            if obj_id not in cls._cache_obj_id_to_obj_dict:
                return False
            else:
                del cls._cache_obj_id_to_obj_dict[obj_id]
                return True


class CamelCacheBaseModel(CacheBaseModel):

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name =  True


class IncrementalIdCacheBaseModel(CacheBaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()

    @classmethod
    def init_max_id(cls, max_val: int) -> None:
        """
        This method must be called just after db is initialized, and it must be
        passed with current max id (if recovering) or 0 (if starting fresh)
        """
        cls._max_id_val = max_val

    @classmethod
    def next_id(cls) -> int:
        with cls._mutex:
            if cls._max_id_val is not None:
                cls._max_id_val += 1
                return cls._max_id_val
            else:
                err_str = "init_max_id needs to be called to initialize max_id before calling get_auto_increment_id, " \
                          f"occurred in model: {cls.__name__}"
                logging.exception(err_str)
                raise Exception(err_str)


class IncrementalIdCamelCacheBaseModel(CamelCacheBaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()

    @classmethod
    def init_max_id(cls, max_val: int) -> None:
        """
        This method must be called just after db is initialized, and it must be
        passed with current max id (if recovering) or 0 (if starting fresh)
        """
        cls._max_id_val = max_val

    @classmethod
    def next_id(cls) -> int:
        with cls._mutex:
            if cls._max_id_val is not None:
                cls._max_id_val += 1
                return cls._max_id_val
            else:
                err_str = "init_max_id needs to be called to initialize max_id before calling get_auto_increment_id, " \
                          f"occurred in model: {cls.__name__}"
                logging.exception(err_str)
                raise Exception(err_str)

