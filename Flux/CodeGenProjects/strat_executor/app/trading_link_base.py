import logging
from abc import abstractmethod, ABC
from typing import List, ClassVar, final, Dict
from pendulum import DateTime
import os

from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import \
    Security, Side
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import \
    OrderBrief, OrderJournal, OrderEventType
from Flux.CodeGenProjects.strat_executor.app.get_pair_strat_n_executor_client import *

def add_to_texts(order_brief: OrderBrief, msg: str):
    if order_brief.text is None:
        order_brief.text = [msg]
    else:
        order_brief.text.append(msg)


def load_configs(config_path):
    return YAMLConfigurationManager.load_yaml_configurations(config_path)


class TradingLinkBase(ABC):
    simulate_config_yaml_path: str | None = None    # must be set before StratExecutor is provided to TradingDataManager
    simulate_config_dict: Dict | None = None    # must be set before StratExecutor is provided to TradingDataManager
    executor_port: int | None = None    # must be set before StratExecutor is provided to TradingDataManager
    executor_host = host
    pair_strat_config_dict = pair_strat_config_yaml_dict
    pair_strat_web_client: ClassVar[StratManagerServiceHttpClient] = strat_manager_service_http_client

    @classmethod
    @final
    def reload_executor_configs(cls):
        cls.simulate_config_dict = load_configs(str(cls.simulate_config_yaml_path))

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
    async def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                              account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    @abstractmethod
    async def place_cxl_order(cls, order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = None) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    async def internal_order_state_update(cls, order_event: OrderEventType, order_id: str, side: Side | None = None,
                                          trading_sec_id: str | None = None, system_sec_id: str | None = None,
                                          underlying_account: str | None = None, msg: str | None = None) -> bool:
        """use for rejects New / Cxl for now - maybe other use cases in future"""
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)

        security = Security(sec_id=system_sec_id)
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        add_to_texts(order_brief, msg)
        order_journal = OrderJournal(order=order_brief, order_event_date_time=DateTime.utcnow(),
                                     order_event=order_event)
        await underlying_create_order_journal_http(order_journal)
        return True

    @classmethod
    async def process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                                text: List[str] | None = None) -> bool:
        """
        optional interface for sync trading links - derived to implement as per underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """
        raise NotImplementedError

    @classmethod
    async def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str) -> bool:
        """
        optional interface for sync trading links - derived to implement as per underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """
        raise NotImplementedError
