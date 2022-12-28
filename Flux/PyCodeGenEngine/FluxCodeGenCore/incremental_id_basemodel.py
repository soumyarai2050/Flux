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
    async def get(cls, obj_id: Any):
        with cls._mutex:
            if obj_id not in cls._cache_obj_id_to_obj_dict:
                return None
            else:
                return cls._cache_obj_id_to_obj_dict[obj_id]

    @classmethod
    def find_all(cls):
        return cls

    @classmethod
    async def to_list(cls):
        return list(cls._cache_obj_id_to_obj_dict.values())

    async def create(self):
        with self._mutex:
            if self.id in self._cache_obj_id_to_obj_dict:
                err_str = f"Id: {self.id} already exists"
                raise Exception(err_str)
            else:
                self._cache_obj_id_to_obj_dict[self.id] = self
                return self

    async def update(self, request_obj: Dict):
        update_data = dict(request_obj)["$set"]
        self.__dict__.update(dict(update_data))

    async def delete(self):
        with self._mutex:
            if self.id not in self._cache_obj_id_to_obj_dict:
                err_str = f"Id: {self.id} Doesn't exists"
                raise Exception(err_str)
            else:
                del self._cache_obj_id_to_obj_dict[self.id]


class CamelBaseModel(BaseModel):
    class Config:
        alias_generator = to_camel
        allow_population_by_field_name =  True


class CamelCacheBaseModel(CacheBaseModel, CamelBaseModel):
    ...


class IncrementalIdBaseModel(BaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    read_ws_path_ws_connection_manager: ClassVar[Any] = None
    read_ws_path_with_id_ws_connection_manager: ClassVar[Any] = None

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


class IncrementalIdCamelBaseModel(IncrementalIdBaseModel, CamelBaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    read_ws_path_ws_connection_manager: ClassVar[Any] = None
    read_ws_path_with_id_ws_connection_manager: ClassVar[Any] = None


class IncrementalIdCacheBaseModel(CacheBaseModel, IncrementalIdBaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    read_ws_path_ws_connection_manager: ClassVar[Any] = None
    read_ws_path_with_id_ws_connection_manager: ClassVar[Any] = None


class IncrementalIdCamelCacheBaseModel(CamelCacheBaseModel, IncrementalIdBaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    read_ws_path_ws_connection_manager: ClassVar[Any] = None
    read_ws_path_with_id_ws_connection_manager: ClassVar[Any] = None
