# standard imports
import os

# 3rd party imports
from dataclasses import dataclass, field
from pendulum import DateTime
from pydantic.dataclasses import dataclass as pydantic_dataclass
# from dataclass_wizard import JSONWizard
# from dataclasses_json import dataclass_json
from pydantic import field_validator, Field

# Project imports
os.environ["ModelType"] = "dataclass"
from Flux.CodeGenProjects.TradeEngine.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *


class SecurityP(BaseModel):
    sec_id: str


class StratLegP(BaseModel):
    sec: SecurityP
    side: Side


class PairStratParamsP(BaseModel):
    strat_leg1: StratLegP
    strat_leg2: StratLegP
    hedge_ratio: float
    exch_response_max_seconds: int


class PairStratPydantic(BaseModel):
    id: int = Field(alias="_id")
    pair_strat_params: PairStratParamsP
    last_active_date_time: DateTime
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    @field_validator('last_active_date_time', mode='before')
    @classmethod
    def handle_last_active_date_time(cls, v):
        return validate_pendulum_datetime(v)

@dataclass
class SecurityDC:
    sec_id: str


@dataclass
class StratLegDC:
    sec: SecurityDC
    side: Side

    def __post_init__(self):
        if isinstance(self.sec, dict):
            self.sec = SecurityDC(**self.sec)
        if isinstance(self.side, str):
            self.side = Side(self.side)


@dataclass
class PairStratParamsDC:
    strat_leg1: StratLegDC
    strat_leg2: StratLegDC
    hedge_ratio: float
    exch_response_max_seconds: int

    def __post_init__(self):
        if isinstance(self.strat_leg1, dict):
            self.strat_leg1 = StratLegDC(**self.strat_leg1)
        if isinstance(self.strat_leg2, dict):
            self.strat_leg2 = StratLegDC(**self.strat_leg2)


# @dataclass_json
@dataclass
class PairStratDataClass:
    _id: int
    pair_strat_params: PairStratParamsDC
    last_active_date_time: DateTime

    def __post_init__(self):
        if isinstance(self.last_active_date_time, str):
            self.last_active_date_time = pendulum.parse(self.last_active_date_time)
        if isinstance(self.pair_strat_params, dict):
            self.pair_strat_params = PairStratParamsDC(**self.pair_strat_params)


@dataclass(slots=True)
class SecurityDCS:
    sec_id: str


@dataclass(slots=True)
class StratLegDCS:
    sec: SecurityDCS
    side: Side

    def __post_init__(self):
        if isinstance(self.sec, dict):
            self.sec = SecurityDCS(**self.sec)
        if isinstance(self.side, str):
            self.side = Side(self.side)


@dataclass(slots=True)
class PairStratParamsDCS:
    strat_leg1: StratLegDCS
    strat_leg2: StratLegDCS
    hedge_ratio: float
    exch_response_max_seconds: int

    def __post_init__(self):
        if isinstance(self.strat_leg1, dict):
            self.strat_leg1 = StratLegDCS(**self.strat_leg1)
        if isinstance(self.strat_leg2, dict):
            self.strat_leg2 = StratLegDCS(**self.strat_leg2)


# @dataclass_json
@dataclass(slots=True)
class PairStratDataClassSlots:
    pair_strat_params: PairStratParamsDCS
    last_active_date_time: DateTime

    def __post_init__(self):
        if isinstance(self.last_active_date_time, str):
            self.last_active_date_time = pendulum.parse(self.last_active_date_time)
        if isinstance(self.pair_strat_params, dict):
            self.pair_strat_params = PairStratParamsDCS(**self.pair_strat_params)


@pydantic_dataclass
class SecurityPDC:
    sec_id: str


@pydantic_dataclass
class StratLegPDC:
    sec: SecurityPDC
    side: Side


@pydantic_dataclass
class PairStratParamsPDC:
    strat_leg1: StratLegPDC
    strat_leg2: StratLegPDC
    hedge_ratio: float
    exch_response_max_seconds: int


@pydantic_dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class PairStratPydanticDataClass:
    pair_strat_params: PairStratParamsPDC
    last_active_date_time: DateTime
    id: int | None = None

    # def __post_init__(self):
    #     if isinstance(self.last_active_date_time, str):
    #         self.last_active_date_time = pendulum.parse(self.last_active_date_time)

    # @field_validator('last_active_date_time', mode='before')
    @classmethod
    def handle_last_active_date_time(cls, v):
        return validate_pendulum_datetime(v)


class SecurityMS(msgspec.Struct, kw_only=True):
    sec_id: str


class StratLegMS(msgspec.Struct, kw_only=True):
    sec: SecurityMS
    side: Side


class PairStratParamsMS(msgspec.Struct, kw_only=True):
    strat_leg1: StratLegMS
    strat_leg2: StratLegMS
    hedge_ratio: float
    exch_response_max_seconds: int


class PairStratMS(msgspec.Struct, kw_only=True):
    _id: int
    pair_strat_params: PairStratParamsMS
    last_active_date_time: DateTime
