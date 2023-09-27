import logging
from abc import abstractmethod, ABC
from typing import List, ClassVar, final
from pendulum import DateTime
import os

from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import \
    Security, Side
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import \
    OrderBrief, OrderJournalBaseModel, OrderEventType, FillsJournalBaseModel
from Flux.CodeGenProjects.strat_executor.app.get_pair_strat_n_executor_client import *


def add_to_texts(order_brief: OrderBrief, msg: str):
    if order_brief.text is None:
        order_brief.text = [msg]
    else:
        order_brief.text.append(msg)


def load_configs(config_path):
    return YAMLConfigurationManager.load_yaml_configurations(config_path)


class TradingLinkBase(ABC):
    executor_config_dict = load_configs(str(executor_config_yaml_path))
    executor_host, executor_port = get_native_host_n_port_from_config_dict(executor_config_dict)
    strat_executor_web_client: ClassVar[StratExecutorServiceHttpClient] = \
        StratExecutorServiceHttpClient.set_or_get_if_instance_exists(executor_host, executor_port)
    pair_strat_config_dict = load_configs(str(pair_strat_port_config_yaml_path))
    pair_strat_host, pair_strat_port = get_native_host_n_port_from_config_dict(pair_strat_config_dict)
    pair_strat_web_client: ClassVar[StratManagerServiceHttpClient] = \
        StratManagerServiceHttpClient.set_or_get_if_instance_exists(pair_strat_host, pair_strat_port)

    @classmethod
    @final
    def reload_executor_configs(cls):
        cls.executor_config_dict = load_configs(str(executor_config_yaml_path))

    @classmethod
    @final
    def reload_pair_strat_configs(cls):
        cls.pair_strat_config_dict = load_configs(str(pair_strat_config_yaml_path))

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
        cls.strat_executor_web_client.create_order_journal_client(order_journal)
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
