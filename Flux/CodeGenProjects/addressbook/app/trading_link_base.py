from abc import abstractmethod, ABC
from typing import List, ClassVar, final
from pendulum import DateTime
import os

from FluxPythonUtils.scripts.utility_functions import get_host_port_from_env
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel
from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_web_client import \
    StratManagerServiceWebClient

from pathlib import PurePath
from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations

PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"
market_data_int_port: int = 8040 if (port_env := (os.getenv("MARKET_DATA_PORT"))) is None or len(port_env) == 0 else \
    int(port_env)


def add_to_texts(order_brief: OrderBrief, msg: str):
    if order_brief.text is None:
        order_brief.text = [msg]
    else:
        order_brief.text.append(msg)


def load_configs():
    return load_yaml_configurations(str(config_file_path))


class TradingLinkBase(ABC):
    host, port = get_host_port_from_env()
    strat_manager_service_web_client: ClassVar[StratManagerServiceWebClient] = StratManagerServiceWebClient(host, port)
    market_data_service_web_client: ClassVar[MarketDataServiceWebClient] = \
        MarketDataServiceWebClient(host, market_data_int_port)
    config_dict = load_configs()

    @classmethod
    @final
    def reload_configs(cls):
        cls.config_dict = load_configs()

    @classmethod
    @abstractmethod
    def trigger_kill_switch(cls) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    @abstractmethod
    def revoke_kill_switch_n_resume_trading(cls) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    @abstractmethod
    def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                        account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    @abstractmethod
    def place_cxl_order(cls, order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
                        system_sec_id: str | None = None, underlying_account: str | None = None) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    def internal_order_state_update(cls, order_event: OrderEventType, order_id: str, side: Side | None = None,
                                    trading_sec_id: str | None = None, system_sec_id: str | None = None,
                                    underlying_account: str | None = None, msg: str | None = None) -> bool:
        """use for rejects New / Cxl for now - maybe other use cases in future"""
        security = Security(sec_id=system_sec_id)
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        add_to_texts(order_brief, msg)
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=order_event)
        cls.strat_manager_service_web_client.create_order_journal_client(order_journal)
        return True

    @classmethod
    def process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                          text: List[str] | None = None) -> bool:
        """
        optional interface for sync trading links - derived to implement as per underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """
        raise NotImplementedError

    @classmethod
    def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str) -> bool:
        """
        optional interface for sync trading links - derived to implement as per underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """
        raise NotImplementedError
