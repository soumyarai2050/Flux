from abc import abstractmethod
from typing import List, ClassVar
from pendulum import DateTime

from FluxPythonUtils.scripts.utility_functions import get_host_port_from_env
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient

from pathlib import PurePath
from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations

PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"


def add_to_texts(order_brief: OrderBrief, msg: str):
    if order_brief.text is None:
        order_brief.text = [msg]
    else:
        order_brief.text.append(msg)


class TradingLinkBase:
    host, port = get_host_port_from_env()
    strat_manager_service_web_client: ClassVar[StratManagerServiceWebClient] = StratManagerServiceWebClient(host, port)
    market_data_service_web_client: ClassVar[MarketDataServiceWebClient] = MarketDataServiceWebClient(host, 8040)
    config_dict = load_yaml_configurations(str(config_file_path))

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
    def internal_order_state_update(cls, order_event: OrderEventType, order_id: str, side: Side | None = None,
                                    sec_id: str | None = None, underlying_account: str | None = None,
                                    msg: str | None = None):
        """use for rejects New / Cxl for now - maybe other use cases in future"""
        security = Security(sec_id=sec_id)
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        add_to_texts(order_brief, msg)
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=order_event)
        cls.strat_manager_service_web_client.create_order_journal_client(order_journal)

    @classmethod
    @abstractmethod
    def process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                          text: List[str] | None = None):
        """derived to implement connector to underlying link provider"""

    @classmethod
    @abstractmethod
    def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        """derived to implement connector to underlying link provider"""
