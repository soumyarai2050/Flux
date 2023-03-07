from abc import abstractmethod
from typing import List, ClassVar

from FluxPythonUtils.scripts.utility_functions import get_host_port_from_env
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient


class TradingLinkBase:
    host, port = get_host_port_from_env()
    strat_manager_service_web_client: ClassVar[StratManagerServiceWebClient] = StratManagerServiceWebClient(host, port)
    market_data_service_web_client: ClassVar[MarketDataServiceWebClient] = MarketDataServiceWebClient(host, 8040)

    @classmethod
    @abstractmethod
    def trigger_kill_switch(cls):
        """derived to implement connector to underlying link provider"""

    @classmethod
    @abstractmethod
    def revoke_kill_switch_n_resume_trading(cls):
        """derived to implement connector to underlying link provider"""

    @classmethod
    @abstractmethod
    def place_new_order(cls, px: float, qty: int, side: Side, sec_id: str, system_sec_id: str,
                        account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        """derived to implement connector to underlying link provider, return True if place order is successful"""
        return False

    @classmethod
    @abstractmethod
    def place_cxl_order(cls, order_id: str, side: Side | None = None, sec_id: str | None = None,
                        underlying_account: str | None = None):
        """derived to implement connector to underlying link provider"""

    @classmethod
    @abstractmethod
    def process_order_ack(cls, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                          text: List[str] | None = None):
        """derived to implement connector to underlying link provider"""

    @classmethod
    @abstractmethod
    def process_fill(cls, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        """derived to implement connector to underlying link provider"""
