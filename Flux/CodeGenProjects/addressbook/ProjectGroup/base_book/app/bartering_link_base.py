import asyncio
import logging
from abc import abstractmethod, ABC
from typing import List, ClassVar, final, Dict, Final, Callable, Any, Tuple
from pendulum import DateTime
import os

os.environ["ModelType"] = "msgspec"
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    Security, Side)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import (
    ChoreBrief, ChoreLedger, ChoreEventType, ChoreStatusType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    EmailBookServiceHttpClient, email_book_service_http_client)


def add_to_texts(chore_brief: ChoreBrief, msg: str):
    if chore_brief.text is None:
        chore_brief.text = [msg]
    else:
        chore_brief.text.append(msg)


def load_configs(config_path):
    return YAMLConfigurationManager.load_yaml_configurations(config_path)


class BarteringLinkBase(ABC):
    asyncio_loop: asyncio.AbstractEventLoop | None = None
    simulate_config_yaml_path: str | None = None    # must be set before StreetBook is provided to BarteringDataManager
    simulate_config_dict: Dict | None = None    # must be set before StreetBook is provided to BarteringDataManager
    executor_port: int | None = None    # must be set before StreetBook is provided to BarteringDataManager
    chore_create_async_callable: Callable[..., Any] | None = None
    fill_create_async_callable: Callable[..., Any] | None = None
    executor_host = host
    pair_plan_config_dict = pair_plan_config_yaml_dict
    pair_plan_web_client: ClassVar[EmailBookServiceHttpClient] = email_book_service_http_client
    contact_config_path: Final[PurePath] = (PurePath(__file__).parent.parent.parent / "street_book" / "data" /
                                              "kill_switch_simulate_config.yaml")
    contact_config_dict: ClassVar[Dict | None] = load_configs(str(contact_config_path))

    def __init__(self, inst_id: str | None = None):
        self.inst_id = inst_id
        self.log_key: str | None = None

    @classmethod
    @abstractmethod
    async def recover_cache(cls, **kwargs):
        """
        derived to implement recovering of any cache required for derived class
        """

    def subscribe(self, listener_id: str, asyncio_loop: asyncio.AbstractEventLoop,
                  ric_filters: List[str] | None, sedol_filters: List[str] | None,
                  block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]], mplan: str | None = None):
        logging.warning("Warning: BarteringLinkBase subscribe invoked - subscribe call has no effect")

    def unsubscribe(self):
        logging.warning("Warning: BarteringLinkBase unsubscribe invoked - unsubscribe call has no effect")

    @classmethod
    def reload_contact_configs(cls):
        # reloading executor configs
        cls.contact_config_dict = load_configs(str(cls.contact_config_path))

    @classmethod
    @final
    def reload_executor_configs(cls):
        cls.simulate_config_dict = load_configs(str(cls.simulate_config_yaml_path))

    @classmethod
    @abstractmethod
    async def is_kill_switch_enabled(cls) -> bool:
        """
        derived to implement connector to underlying link provider
        Raise Exception if send to underlying provider fails
        """

    @classmethod
    @abstractmethod
    async def trigger_kill_switch(cls) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    @abstractmethod
    async def revoke_kill_switch_n_resume_bartering(cls) -> bool:
        """
        derived to implement connector to underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """

    @classmethod
    @abstractmethod
    async def place_new_chore(cls, px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str,
                              bartering_sec_type: str, account: str, exchange: str | None = None, text: List[str] | None = None,
                              client_ord_id: str | None = None, **kwargs) -> Tuple[bool, str]:
        """
        derived to implement connector to underlying link provider, and
        return bool indicating success/fail and unique-id-str/err-description in second param
        """

    @classmethod
    @abstractmethod
    async def place_amend_chore(cls, chore_id: str, px: float | None = None, qty: int | None = None,
                                bartering_sec_id: str | None = None, system_sec_id: str | None = None,
                                bartering_sec_type: str | None = None) -> bool:
        """
        derived to implement connector to underlying link provider
        """

    @classmethod
    @abstractmethod
    async def place_cxl_chore(cls, chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = None) -> bool:
        """
        derived to implement connector to underlying link provider
        """

    @classmethod
    @abstractmethod
    async def is_chore_open(cls, chore_id: str) -> bool:
        """
        derived to implement connector to underlying link provider
        return True if chore found open
        """

    @classmethod
    @abstractmethod
    async def get_chore_status(cls, chore_id: str) -> Tuple[ChoreStatusType | None, str | None, int | None, float | None, int | None] | None:
        """
        derived to implement connector to underlying link provider
        returns chore_status (ChoreStatusType), any_chore_text, filled-Qty, chore-px and chore-qty as seen by bartering
        link, caller may use these for reconciliation
        return None [indicating no chore found for this chore_id]
        throws exception if found chore state is unsupported
        """

    @classmethod
    async def internal_chore_state_update(cls, chore_event: ChoreEventType, chore_id: str, side: Side | None = None,
                                          bartering_sec_id: str | None = None, system_sec_id: str | None = None,
                                          underlying_account: str | None = None, msg: str | None = None) -> bool:
        """use for rejects New / Cxl for now - maybe other use cases in future"""
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes_imports import (
            underlying_create_chore_ledger_http)

        security = Security(sec_id=system_sec_id)
        chore_brief = ChoreBrief(chore_id=chore_id, security=security, side=side,
                                 underlying_account=underlying_account)
        add_to_texts(chore_brief, msg)
        chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                     chore_event=chore_event)
        await underlying_create_chore_ledger_http(chore_ledger)
        return True

    @classmethod
    async def process_chore_ack(cls, chore_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                                text: List[str] | None = None) -> bool:
        """
        optional interface for sync bartering links - derived to implement as per underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """
        raise NotImplementedError

    @classmethod
    async def process_fill(cls, chore_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str) -> bool:
        """
        optional interface for sync bartering links - derived to implement as per underlying link provider
        return false for any synchronous error (including if send to underlying provider fails)
        """
        raise NotImplementedError
