from typing import List, Dict, Any
from enum import auto, Enum
from fastapi_restful.enums import StrEnum
from pydantic import BaseModel


class FieldQuery(BaseModel):
    field_name: str
    properties: Dict[str, Any]


class WidgetQuery(BaseModel):
    widget_name: str
    widget_data: Dict[str, Any] | None = None
    fields: List[FieldQuery]


class DataType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    DATE_TIME = "date_time"
    ENUM = "enum"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    INT32 = "int32"
    INT64 = "int64"
    OBJECT = "object"
    ARRAY = "array"


class FluxPropertyType(StrEnum):
    FluxFldValMax = "val_max"


class DriverType(StrEnum):
    CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"
    SAFARI = "safari"


class SearchType(StrEnum):
    ID = auto()
    NAME = auto()
    TAG_NAME = auto()
    CLASS_NAME = auto()


class Layout(StrEnum):
    TABLE = auto()
    TREE = auto()
    NESTED = auto()
    CHART = auto()


class WidgetType(StrEnum):
    INDEPENDENT = auto()
    DEPENDENT = auto()
    REPEATED_INDEPENDENT = auto()
    REPEATED_DEPENDENT = auto()
    ABBREVIATED = auto()
    LINKED_ABBREVIATED = auto()
    PARENT_ABBREVIATED = auto()


class Delay(Enum):
    SHORT = 2
    DEFAULT = 5
    LONG = 20


class ColorType(StrEnum):
    # ERROR = (156, 0, 6)
    WARNING = auto()
    CRITICAL = auto()
