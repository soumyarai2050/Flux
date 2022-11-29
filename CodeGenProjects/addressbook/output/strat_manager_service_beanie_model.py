from beanie import Indexed, Document
from pydantic import BaseModel, Field
import datetime
from threading import Lock
from Flux.PyCodeGenEngine.FluxCodeGenCore.incremental_id_basemodel import IncrementalIdCacheBaseModel
from enum import auto
from fastapi_utils.enums import StrEnum
from typing import List, ClassVar


class SecurityType(StrEnum):
    SEC_TYPE_UNSPECIFIED = auto()
    RIC = auto()
    SEDOL = auto()
    EXCHANGE = auto()


class ReferencePxType(StrEnum):
    OPEN_PX = auto()
    CLOSE_PX = auto()
    LAST_PX = auto()
    BB_PX = auto()
    BO_PX = auto()
    FILL_PX = auto()


class Side(StrEnum):
    SIDE_UNSPECIFIED = auto()
    BUY = auto()
    SELL = auto()
    BTC = auto()
    SS = auto()


class PositionType(StrEnum):
    POS_TYPE_UNSPECIFIED = auto()
    PTH = auto()
    LOCATE = auto()
    LONG = auto()


class Severity(StrEnum):
    Severity_UNSPECIFIED = auto()
    Severity_CRITICAL = auto()
    Severity_ERROR = auto()
    Severity_WARNING = auto()
    Severity_INFO = auto()
    Severity_DEBUG = auto()


class StratState(StrEnum):
    UNSPECIFIED = auto()
    READY = auto()
    ACTIVE = auto()
    PAUSED = auto()
    ERROR = auto()
    DONE = auto()


class Theme(StrEnum):
    THEME_UNSPECIFIED = auto()
    DARK = auto()
    LIGHT = auto()


class OrderLimits(Document, IncrementalIdCacheBaseModel):
    """
        Widget - 5
    """
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    id: int = Field(default_factory=(lambda: OrderLimits.next_id()), description='Server generated unique Id')
    max_price_levels: int
    max_basis_points: int
    max_cb_order_notional: int
    max_px_deviation: float


class StratCollection(Document, IncrementalIdCacheBaseModel):
    """
        Widget - 1
    """
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    id: int = Field(default_factory=(lambda: StratCollection.next_id()), description='Server generated unique Id')
    loaded_strat_keys: List[str] = Field(description="leg1_sec_id-leg2_sec_id-leg1_side-uid")
    buffered_strat_keys: List[str] = Field(description="show 9 most recently used (weight:2) & 9 most frequently used (weight: 1), Sort by type, merge by weight, FILTER OUT loaded")


class Security(BaseModel):
    """
        Don't rename fields - if you must , update loaded_strat_keys abbreviation accordingly
    """
    sec_id: str
    sec_type: SecurityType | None


class ReferencePx(BaseModel):
    price: float
    reference_price_type: ReferencePxType


class Position(BaseModel):
    """
        stores all position types from all sources for optimal selection, usage and clearance, one can desig
        n to make entry with cheapest option first and clear the most expensive used position first
    """
    position_type: PositionType
    available_position_size: int = Field(description="available size for consumption")
    allocated_position_size: int = Field(description="committed but not consumed (portfolio to strat; day-2: maybe strat to open order)")
    consumed_position_size: int = Field(description="actual consumption")
    carry_cost: float | None


class ResidualRestriction(BaseModel):
    max_residual: float
    residual_mark_seconds: int


class MarketParticipation(BaseModel):
    participation_rate: float
    applicable_period_seconds: int


class CancelRate(BaseModel):
    allowed_order_rate: int
    allowed_size_rate: int
    applicable_period_seconds: int


class WidgetUIData(BaseModel):
    i: str = Field(description="key string connects Widget with Model - future better name via: [(FluxFldAlias) = 'i']")
    x: int | None = Field(description="X coordinate magnitude (left most is 0)")
    y: int | None = Field(description="Y coordinate magnitude (top most is 0)")
    w: int | None = Field(description="width")
    h: int | None = Field(description="height")


class UILayout(Document, IncrementalIdCacheBaseModel):
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    id: int = Field(default_factory=(lambda: UILayout.next_id()), description='Server generated unique Id')
    profile_id: Indexed(str)
    widget_ui_data: List[WidgetUIData]
    theme: Theme | None


class SecPosition(BaseModel):
    security: Security
    reference_px: ReferencePx | None = Field(description="Open price OR Close Price OR Last Price")
    positions: List[Position] = Field(description="per position type (PTH, LOCATE, LONG)")


class OrderBrief(BaseModel):
    order_brief_id: str
    security: Security
    side: Side
    px: float
    qty: int
    underlying_broker: str


class CumulativeOrderBrief(BaseModel):
    order_brief: List[OrderBrief]
    overall_buy_notional: float | None
    overall_sell_notional: float | None


class Residual(BaseModel):
    security: Security
    notional: float


class StratLimits(BaseModel):
    """
        Widget - 4
    """
    max_cb_notional: float
    max_open_cb_notional: float
    max_open_baskets: int
    market_participation: MarketParticipation | None
    max_concentration: float | None


class Broker(BaseModel):
    enabled: bool
    sec_positions: List[SecPosition] = Field(description="per security positions")


class Alert(BaseModel):
    severity: Severity
    alert_brief: str
    alert_details: str | None = Field(description="must prefix strat:<strat-name> for strat alerts")
    impacted_order: List[OrderBrief] = Field(description="populated only if this alert is for one or more orders")


class PortfolioLimits(Document, IncrementalIdCacheBaseModel):
    """
        Widget - 6
    """
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    id: int = Field(default_factory=(lambda: PortfolioLimits.next_id()), description='Server generated unique Id')
    eligible_brokers: List[Broker] = Field(description="auto update symbol's availability when allocated/consumed by strat(block strat creation if not enough availability), this has both limit and status in Position")
    max_cb_notional: float
    cancel_rate: CancelRate


class PortfolioStatus(Document, IncrementalIdCacheBaseModel):
    """
        Widget - 7
    """
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    id: int = Field(default_factory=(lambda: PortfolioStatus.next_id()), description='Server generated unique Id')
    kill_switch: bool = Field(description="The big RED button")
    portfolio_alerts: List[Alert] = Field(description="One or more alerts")
    overall_buy_notional: float | None = Field(description="Open + Executed")
    overall_sell_notional: float | None = Field(description="Open + Executed")


class PairStratParams(BaseModel):
    """
        Widget-2, BOILER PLATE - don't add fields by changing sequence numbers in model: even in dev, if you
         must , update loaded_strat_keys abbreviation accordingly
    """
    exch_id: str | None
    leg1_sec: Security = Field(description="server provided via security auto complete list (if available)")
    leg1_sec_reference_px: ReferencePx | None = Field(description="server provided via security auto complete list (if available). Open price OR Close Price OR Last Price")
    leg2_sec: Security
    leg2_sec_reference_px: ReferencePx | None = Field(description="server provided via security auto complete list (if available). Open price OR Close Price OR Last Price")
    leg1_side: Side
    eligible_brokers: List[Broker] = Field(description="default: same as portfolio eligible_brokers except filtered by symbol + allow mod down, reduce portfolio lvl & save")
    residual_restriction: ResidualRestriction | None
    exch_response_max_seconds: int | None
    trigger_premium_percentage: float = Field(description="these are specific to CB-EQT strat - move to derived later")
    hedge_ratio: float | None


class StratStatus(BaseModel):
    """
        Widget - 3
    """
    strat_alerts: List[Alert] = Field(description="One or more alerts")
    strat_state: StratState
    average_premium: float | None = Field(description="these are specific to CB-EQT strat - move to derived later")
    fills_brief: List[CumulativeOrderBrief]
    open_orders_brief: List[CumulativeOrderBrief]
    balance_notional: float | None
    residual: Residual | None


class PairStrat(Document, IncrementalIdCacheBaseModel):
    """
        Don't rename fields - if you must , update loaded_strat_keys abbreviation accordingly
    """
    _max_id_val: ClassVar[int | None] = None
    _mutex: ClassVar[Lock] = Lock()
    id: int = Field(default_factory=(lambda: PairStrat.next_id()), description='Server generated unique Id')
    last_active_date_time: datetime.datetime | None = Field(description="An int64 may or may-not be date time. A datetime field must have FluxFldValDateTime option set, CodeGen to handle appropriate datetime generation if the FluxFldValIsDateTime option is set")
    frequency: int | None
    pair_strat_params: PairStratParams
    strat_status: StratStatus | None
    strat_limits: StratLimits


