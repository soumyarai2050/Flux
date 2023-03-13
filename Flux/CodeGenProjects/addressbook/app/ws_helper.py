import logging
from typing import List
from pydantic import BaseModel

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import TopOfBookBaseModel, \
    MarketDepthBaseModel, SymbolOverviewBaseModel, TickTypeEnum


# needed for list parsing - for now

class CancelOrderBaseModelList(BaseModel):
    __root__: List[CancelOrderBaseModel]


class NewOrderBaseModelList(BaseModel):
    __root__: List[NewOrderBaseModel]


class TopOfBookBaseModelList(BaseModel):
    __root__: List[TopOfBookBaseModel]


class SymbolOverviewBaseModelList(BaseModel):
    __root__: List[SymbolOverviewBaseModel]


class PortfolioStatusBaseModelList(BaseModel):
    __root__: List[PortfolioStatusBaseModel]


class PortfolioLimitsBaseModelList(BaseModel):
    __root__: List[PortfolioLimitsBaseModel]


class OrderLimitsBaseModelList(BaseModel):
    __root__: List[OrderLimitsBaseModel]


class PairStratBaseModelList(BaseModel):
    __root__: List[PairStratBaseModel]


class OrderJournalBaseModelList(BaseModel):
    __root__: List[OrderJournalBaseModel]


class FillsJournalBaseModelList(BaseModel):
    __root__: List[FillsJournalBaseModel]


class StratBriefBaseModelList(BaseModel):
    __root__: List[StratBriefBaseModel]


class MarketDepthBaseModelList(BaseModel):
    __root__: List[MarketDepthBaseModel]


