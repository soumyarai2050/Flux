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
    FluxFldValMin = "val_min"
    FluxFldValMax = "val_max"
    FluxFldServerPopulate = "server_populate"
    FluxFldDisplayType = "display_type"
    FluxFldNumberFormat = "number_format"
    FluxFldDisplayZero = "display_zero"
    FluxFldButton = "button"
    FluxFldHelp = "help"
    FluxFldProgressBar = "progress_bar"
    FluxFldDefault = "default"
    FluxFldNoCommonKey = "no_common_key"
    FluxFldElaborateTitle = "elaborate_title"
    FluxFldUiUpdateOnly = "ui_update_only"
    FluxFldSequenceNumber = "sequence_number"
    FluxFldFilterEnabled = "filter_enable"
    FluxFldTitle = "title"
    FluxFldAutoComplete = "auto_complete"
    FluxFldAbbreviate = "abbreviate"
    FluxFldNameColor = "name_color"
    FluxFldOrmNoUpdate = "orm_no_update"
    FluxFldUIPlaceholder = "ui_placeholder"


class InputType(StrEnum):
    MAX_VALID_VALUE = auto()
    INVALID_VALUE = auto()
    MIN_VALID_VALUE = auto()
    MIN_INVALID_VALUE = auto()


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
    MEDIUM = 10
    LONG = 20


class WidgetName(StrEnum):
    PairPlanParams = "pair_plan_params"
    PlanLimits = "plan_limits"
    PlanCollection = "plan_collection"
    PortFolioLimits = "contact_limits"
    ChoreLimits = "chore_limits"
    PortFolioStatus = "contact_status"
    PlanStatus = "plan_status"
    ContactAlert = "contact_alert"
    FxSymbolOverview = "fx_symbol_overview"
    BasketChore = "basket_chore"
    SymbolSideSnapShot = "symbol_side_snapshot"
    PlanBrief = "plan_brief"
    SymbolOverview = "symbol_overview"


class ColorType(StrEnum):
    # ERROR = (156, 0, 6)
    WARNING = auto()
    CRITICAL = auto()


class ButtonState(StrEnum):
    HIDE = "Hide"
    SHOW = "Show"


class FieldType(StrEnum):
    Autocomplete = auto()


class AutoCompleteType:
    AutocompleteOff = auto()
