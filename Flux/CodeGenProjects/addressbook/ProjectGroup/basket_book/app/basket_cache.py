import logging
from pendulum import DateTime
from typing import Dict, Set
from functools import lru_cache
from queue import Queue
import math

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_base_plan_cache import (
    BasketBookServiceBasePlanCache)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_plan_cache import (
    EmailBookServiceBasePlanCache)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_plan_cache import BasePlanCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_key_handler import BasketBookServiceKeyHandler
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.data import security
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    ShadowBrokersBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import get_bartering_link

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecord, SecType


class BasketCache(BasePlanCache, BasketBookServiceBasePlanCache, EmailBookServiceBasePlanCache):
    KeyHandler: Type[BasketBookServiceKeyHandler] = BasketBookServiceKeyHandler

    def __init__(self):
        BasePlanCache.__init__(self)
        BasketBookServiceBasePlanCache.__init__(self)
        EmailBookServiceBasePlanCache.__init__(self)
        self.unack_state_set: Set[str] = set()
        self.id_to_new_chore_dict: Dict[int, NewChore] = {}
        self.non_cached_basket_chore_queue: Queue[BasketChore | BasketChoreOptional] = Queue()
        self.figi_to_sec_rec_dict: Dict[str, SecurityRecord] = {}
        self.chores: List[NewChore] | None = None  # remains None until first init - which may make it empty list if no chores in DB
        self.basket_id: int | None = None
        self.is_recovered_n_reconciled: bool = False

    @staticmethod
    @lru_cache(maxsize=None)
    def get_symbol_side_cache_key(system_symbol: str, side: Side):
        return f"{system_symbol}-{side.value}"

    def check_unack(self, system_symbol: str, side: Side):
        symbol_side_key = BasketCache.get_symbol_side_cache_key(system_symbol, side)
        if symbol_side_key not in self.unack_state_set:
            return False
        return True

    def set_unack(self, has_unack: bool, system_symbol: str, side: Side):
        symbol_side_key = BasketCache.get_symbol_side_cache_key(system_symbol, side)
        if has_unack:
            self.unack_state_set.add(symbol_side_key)
        else:
            self.unack_state_set.discard(symbol_side_key)

    def set_chore_snapshot(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot) -> DateTime:
        """
        override to enrich _chore_id_to_open_chore_snapshot_dict [invoke base first and then act here]
        """
        _chore_snapshots_update_date_time = super().set_chore_snapshot(chore_snapshot)
        overfill_log_str = f"Chore found overfilled for symbol_side_key: ;;;{chore_snapshot=}"
        self.handle_set_chore_snapshot(chore_snapshot, overfill_log_str)
        return _chore_snapshots_update_date_time  # ignore - helps with debug

    def set_basket_chore(self, basket_chore: BasketChoreBaseModel | BasketChore) -> DateTime:
        self._basket_chore = basket_chore
        self._basket_chore_update_date_time = DateTime.utcnow()

        if self.basket_id is None:
            self.basket_id = self._basket_chore.id

        if hasattr(self._basket_chore, "update_id") and self._basket_chore.update_id == -1:
            return self._basket_chore_update_date_time  # update_id=-1 implies NO-OP in self.handle_basket_chore_get_all_ws_ call
        elif self._basket_chore.processing_level == 3:
            # internal/recovery run; no more processing needed; we just needed persistence in DB, that's done: return
            return self._basket_chore_update_date_time
        # else continue as normal

        non_cached_new_chore_list: List[NewChore] = []
        new_chore_obj: NewChore
        for new_chore_obj in basket_chore.new_chores:
            if new_chore_obj.chore_submit_state in [ChoreSubmitType.ORDER_SUBMIT_NA,
                                                    ChoreSubmitType.ORDER_SUBMIT_FAILED]:
                continue  # ignore - prior closed chores
            if stored_chore_obj := self.id_to_new_chore_dict.get(new_chore_obj.id):
                # Add to amend if the chore is with change [current only px / qty amends are checked]
                if amend_tuple := self.is_amend(stored_chore_obj, new_chore_obj):
                    amd_qty, amd_px = amend_tuple
                    if amd_qty is not None:
                        new_chore_obj.pending_amd_qty = amd_qty  # pending amend qty
                        new_chore_obj.qty = stored_chore_obj.qty  # orig qty
                    if amd_px is not None:
                        new_chore_obj.pending_amd_px = amd_px  # pending amend px
                        new_chore_obj.px = stored_chore_obj.px  # orig px
                    non_cached_new_chore_list.append(new_chore_obj)
                    self.update_chore_sec_details(new_chore_obj)  # Fix sec if not as expected
                elif new_chore_obj.pending_cxl and stored_chore_obj.pending_cxl != new_chore_obj.pending_cxl:
                    # this is cxl request
                    non_cached_new_chore_list.append(new_chore_obj)
                    self.update_chore_sec_details(new_chore_obj)  # Fix sec if not as expected
                else:
                    # this is non-amend, likely state update - just ignore
                    logging.info(f"ignoring non-amend update: {new_chore_obj} orig: {stored_chore_obj}")
            else:
                # this is new / recovered chore entry - add to non_cached_new_chore_list
                self.update_chore_sec_details(new_chore_obj)  # we may have gone down with sec update in DB
                non_cached_new_chore_list.append(new_chore_obj)
                self.id_to_new_chore_dict[new_chore_obj.id] = new_chore_obj
                logging.info(f"Added to non_cached_new_chore_list chore: {new_chore_obj.ticker} "
                             f"{new_chore_obj.side} {new_chore_obj.chore_id};;;{new_chore_obj}")

        if non_cached_new_chore_list:
            non_cached_basket_chore_: BasketChore = BasketChore(id=self.basket_id,
                                                                new_chores=non_cached_new_chore_list)
            self.non_cached_basket_chore_queue.put(non_cached_basket_chore_)
        return self._basket_chore_update_date_time

    def set_primary_ric_n_sedol_from_ticker_in_new_chore(self, new_chore_obj: NewChore,
                                                         sec_rec: SecurityRecord = None) -> bool:
        if new_chore_obj.ticker is None:
            return False
        # force New Chore to Primary RIC [EQT] / Primary SEDOL [CB] when ticker is supplied
        if sec_rec is None:
            sec_rec = self.static_data.get_security_record_from_ticker(new_chore_obj.ticker)
        if sec_rec is None:
            raise Exception(f"Unexpected: unable to find SecurityRecord for {new_chore_obj.ticker=};;;{new_chore_obj}")
        if sec_rec.sec_type == SecType.EQT:
            security: Security = Security(inst_type=InstrumentType.EQT, sec_id=sec_rec.ric,
                                          sec_id_source=SecurityIdSource.RIC)
            new_chore_obj.security = security
        elif sec_rec.sec_type == SecType.CB:
            security: Security = Security(inst_type=InstrumentType.CB, sec_id=sec_rec.sedol,
                                          sec_id_source=SecurityIdSource.SEDOL)
            new_chore_obj.security = security
        else:
            raise Exception(f"Unsupported {sec_rec.sec_type=} found in {sec_rec=} for {new_chore_obj=}")

    def update_chore_sec_details(self, new_chore_obj: NewChore):
        if new_chore_obj.security is None:
            if new_chore_obj.ticker is None:
                err_ = (f"Invalid {new_chore_obj.ticker=} and {new_chore_obj.security=} found in {new_chore_obj} of "
                        f"update_chore_sec_details, either should be valid")
                logging.error(err_)
                raise HTTPException(status_code=500, detail=err_)
            else:
                self.set_primary_ric_n_sedol_from_ticker_in_new_chore(new_chore_obj)
        elif (new_chore_obj.security.sec_id_source == SecurityIdSource.SEDOL or
              new_chore_obj.security.sec_id_source.RIC) and new_chore_obj.ticker is not None:
            pass  # pre-set

        elif new_chore_obj.security.sec_id_source == SecurityIdSource.SEC_ID_SOURCE_UNSPECIFIED:
            err_ = (f"unexpected {new_chore_obj.security.sec_id_source=} found in {new_chore_obj} of "
                    f"update_chore_sec_details")
            logging.error(err_)
            raise HTTPException(status_code=500, detail=err_)

        elif new_chore_obj.security.sec_id_source == SecurityIdSource.TICKER:
            if new_chore_obj.ticker is not None:
                if new_chore_obj.ticker != new_chore_obj.security.sec_id:
                    err_ = (f"unexpected {new_chore_obj.security.sec_id_source=} is TICKER but "
                            f"{new_chore_obj.security.sec_id=} and {new_chore_obj.ticker} do not match found in "
                            f"{new_chore_obj} of update_chore_sec_details")
                    logging.error(err_)
                    raise HTTPException(status_code=500, detail=err_)
                else:
                    self.set_primary_ric_n_sedol_from_ticker_in_new_chore(new_chore_obj)
            else:
                new_chore_obj.ticker = new_chore_obj.security.sec_id
                self.set_primary_ric_n_sedol_from_ticker_in_new_chore(new_chore_obj)

        elif new_chore_obj.security.sec_id_source == SecurityIdSource.FIGI:
            figi = new_chore_obj.security.sec_id
            sec_rec: SecurityRecord
            if sec_rec := self.figi_to_sec_rec_dict.get(figi):
                if new_chore_obj.ticker is None:
                    new_chore_obj.ticker = sec_rec.ticker
                elif new_chore_obj.ticker != sec_rec.ticker:
                    err_ = (
                        f"unexpected {new_chore_obj.ticker=} does not match {new_chore_obj.security.sec_id=} based "
                        f"static data found: {sec_rec.ticker=};;;{sec_rec=}, {new_chore_obj=}")
                    logging.error(err_)
                    raise HTTPException(status_code=500, detail=err_)
                # else all good for ticker
                found: bool = True
                if sec_rec.sec_type == SecType.CB:
                    new_chore_obj.security.inst_type = InstrumentType.CB
                    new_chore_obj.security.sec_id_source = SecurityIdSource.SEDOL
                    if figi == sec_rec.figi:
                        new_chore_obj.security.sec_id = sec_rec.sedol
                    elif figi == sec_rec.secondary_figi:
                        new_chore_obj.security.sec_id = sec_rec.secondary_sedol
                    else:
                        found = False
                elif sec_rec.sec_type == SecType.EQT:
                    new_chore_obj.security.inst_type = InstrumentType.EQT
                    new_chore_obj.security.sec_id_source = SecurityIdSource.RIC
                    if figi == sec_rec.figi:
                        new_chore_obj.security.sec_id = sec_rec.ric
                    elif figi == sec_rec.secondary_figi:
                        new_chore_obj.security.sec_id = sec_rec.secondary_ric
                    else:
                        found = False
                else:
                    found = False
                if not found:
                    err_ = (f"Error: new chore's {figi=} matches record in figi_to_sec_rec_dict, but either "
                            f"{sec_rec.sec_type=} not EQT/CB or the matched sec_rec's figi(s): {sec_rec.figi=}, "
                            f"{sec_rec.secondary_figi=}; dont match found {figi=} on new chore;;;{new_chore_obj=};"
                            f"\nfigi_to_sec_rec_dict:\n"
                            f"{[f'{figi}:{sec_rec};;' for figi, sec_rec in self.figi_to_sec_rec_dict.items()]}")
                    raise HTTPException(status_code=500, detail=err_)
            else:
                err_ = (f"Unsupported figi: {new_chore_obj.security.sec_id}; not found in figi_to_sec_rec_dict;;;"
                        f"{[f'{figi}:{sec_rec};;' for figi, sec_rec in self.figi_to_sec_rec_dict.items()]}")
                raise HTTPException(status_code=500, detail=err_)

        elif new_chore_obj.security.sec_id_source == SecurityIdSource.RIC:
            ric = new_chore_obj.security.sec_id
            sec_rec: SecurityRecord
            ticker = self.static_data.get_ticker_from_ric(ric)
            if sec_rec := self.static_data.get_security_record_from_ticker(ticker):
                # self._update_chore_sec_id_n_ticker()
                if new_chore_obj.ticker is None:
                    new_chore_obj.ticker = sec_rec.ticker
                elif new_chore_obj.ticker != sec_rec.ticker:
                    err_ = (
                        f"unexpected {new_chore_obj.ticker=} does not match {new_chore_obj.security.sec_id=} based "
                        f"static data found: {sec_rec.ticker=};;;{sec_rec=}, {new_chore_obj=}")
                    logging.error(err_)
                    raise HTTPException(status_code=500, detail=err_)
                # else all good for ticker
                found: bool = True
                if sec_rec.sec_type == SecType.CB:
                    new_chore_obj.security.inst_type = InstrumentType.CB
                    new_chore_obj.security.sec_id_source = SecurityIdSource.SEDOL
                    if ric == sec_rec.ric:
                        new_chore_obj.security.sec_id = sec_rec.sedol
                    elif ric == sec_rec.secondary_ric:
                        new_chore_obj.security.sec_id = sec_rec.secondary_sedol
                    else:
                        found = False
                elif sec_rec.sec_type == SecType.EQT:
                    new_chore_obj.security.inst_type = InstrumentType.EQT
                    new_chore_obj.security.sec_id_source = SecurityIdSource.RIC
                    if ric == sec_rec.ric:
                        new_chore_obj.security.sec_id = sec_rec.ric
                    elif ric == sec_rec.secondary_ric:
                        new_chore_obj.security.sec_id = sec_rec.secondary_ric
                    else:
                        found = False
                else:
                    found = False
                if not found:
                    err_ = (f"Error: new chore's {ric=} matches record in figi_to_sec_rec_dict, but either "
                            f"{sec_rec.sec_type=} not EQT/CB or the matched sec_rec's ric(s): {sec_rec.ric=}, "
                            f"{sec_rec.secondary_ric=}; dont match found {ric=} on new chore;;;{new_chore_obj=}")
                    raise HTTPException(status_code=500, detail=err_)
            else:
                err_ = (f"Unsupported ric: {new_chore_obj.security.sec_id}; not found in "
                        f"static_data.get_security_record_from_ticker")
                raise HTTPException(status_code=500, detail=err_)

        else:
            err_ = f"Unsupported ric: {new_chore_obj.security.sec_id}; found on {new_chore_obj=}"
            raise HTTPException(status_code=500, detail=err_)
        # else not required = chore sec_id is RIC

    @staticmethod
    def has_qty_amend(stored_chore_obj: NewChore | Dict | None,
                      updated_chore_obj: NewChore | Dict) -> Tuple[bool, int | None]:
        updated_qty: int | None = None
        is_amend: bool = False
        if isinstance(stored_chore_obj, Dict):
            updated_qty: int | None = updated_chore_obj.get("qty")
            if stored_chore_obj is not None and stored_chore_obj.get("qty") != updated_qty:
                is_amend = True
        else:
            if stored_chore_obj.qty != updated_chore_obj.qty:
                updated_qty = updated_chore_obj.qty
                is_amend = True
        return is_amend, updated_qty

    @staticmethod
    def has_px_amend(stored_chore_obj: NewChore | Dict | None,
                     updated_chore_obj: NewChore | Dict) -> Tuple[bool, int | None]:
        updated_px: float | None = None
        is_amend: bool = False
        if isinstance(stored_chore_obj, Dict):
            updated_px: float | None = updated_chore_obj.get("px")
            stored_px: float | None = stored_chore_obj.get("px")
            if stored_px is not None and updated_px is not None:
                if not math.isclose(stored_px, updated_px):
                    is_amend = True
            elif stored_px != updated_px and updated_px is not None:
                is_amend = True
        else:
            if updated_chore_obj.qty is not None and (not math.isclose(stored_chore_obj.px, updated_chore_obj.px)):
                updated_px = updated_chore_obj.px
                is_amend = True
        return is_amend, updated_px

    def is_amend(self, stored_chore_obj, new_chore_obj) -> Tuple[int | None, float | None] | None:
        is_qty_amend: bool
        amd_qty: int | None
        is_px_amend: bool
        amd_px: float | None
        is_qty_amend, amd_qty = self.has_qty_amend(stored_chore_obj, new_chore_obj)
        is_px_amend, amd_px = self.has_px_amend(stored_chore_obj, new_chore_obj)
        if is_qty_amend or is_px_amend:
            return amd_qty, amd_px
        else:
            return None

    @staticmethod
    def get_meta(ticker: str, side: Side) -> Tuple[Dict[str, Side], Dict[str, Side], Dict[str, str]]:
        # helps prevent reverse bartering on intraday positions where security level constraints exists
        meta_no_executed_tradable_symbol_replenishing_side_dict: Dict[str, Side] = {}
        # current plan bartering symbol and side dict - helps block intraday non recovery position updates
        meta_bartering_symbol_side_dict: Dict[str, Side] = {}
        meta_symbols_n_sec_id_source_dict: Dict[str, str] = {}  # stores symbol and symbol type [RIC, SEDOL, etc.]

        sec_rec: SecurityRecord = BasketCache.static_data.get_security_record_from_ticker(ticker)
        if BasketCache.static_data.is_cb_ticker(ticker):
            bartering_symbol: str = sec_rec.sedol
            meta_bartering_symbol_side_dict[bartering_symbol] = side
            if not sec_rec.executed_tradable:
                replenishing_side: Side = Side.SELL if side == Side.BUY else Side.BUY
                meta_no_executed_tradable_symbol_replenishing_side_dict[ticker] = replenishing_side
                meta_no_executed_tradable_symbol_replenishing_side_dict[bartering_symbol] = replenishing_side
            meta_symbols_n_sec_id_source_dict[bartering_symbol] = SecurityIdSource.SEDOL

        elif BasketCache.static_data.is_eqt_ticker(ticker):
            qfii_ric, connect_ric = sec_rec.ric, sec_rec.secondary_ric
            if qfii_ric:
                meta_bartering_symbol_side_dict[qfii_ric] = side
                meta_symbols_n_sec_id_source_dict[qfii_ric] = SecurityIdSource.RIC
            if connect_ric:
                meta_bartering_symbol_side_dict[connect_ric] = side
                meta_symbols_n_sec_id_source_dict[connect_ric] = SecurityIdSource.RIC
            if not sec_rec.executed_tradable:
                replenishing_side: Side = Side.SELL if side == Side.BUY else Side.BUY
                meta_no_executed_tradable_symbol_replenishing_side_dict[ticker] = replenishing_side
                meta_no_executed_tradable_symbol_replenishing_side_dict[qfii_ric] = replenishing_side
                meta_no_executed_tradable_symbol_replenishing_side_dict[connect_ric] = replenishing_side
        else:
            logging.error(f"Unsupported {ticker=}, neither cb or eqt")

        return (meta_no_executed_tradable_symbol_replenishing_side_dict, meta_bartering_symbol_side_dict,
                meta_symbols_n_sec_id_source_dict)

    def get_pos_cache(self, system_symbol: str, side: Side) -> PosCache:
        (meta_no_executed_tradable_symbol_replenishing_side_dict, meta_bartering_symbol_side_dict,
         meta_symbols_n_sec_id_source_dict) = self.get_meta(system_symbol, side)

        shadow_brokers: List[ShadowBrokersBaseModel] = (
            email_book_service_http_client.get_dismiss_filter_contact_limit_brokers_query_client(
                system_symbol, system_symbol))
        if not shadow_brokers:
            err_str_ = (f"Http Query get_dismiss_filter_contact_limit_brokers_query_client returned empty list, "
                        f"expected shadow_brokers list")
            logging.warning(err_str_)
        logging.debug(f"shadow brokers for {system_symbol=} - {shadow_brokers=}")
        eligible_brokers: List[BrokerBaseModel] = []
        for shadow_broker in shadow_brokers:
            shadow_broker_dict = shadow_broker.to_dict()
            del shadow_broker_dict["_id"]
            eligible_brokers.append(Broker.from_dict(shadow_broker_dict))

        bartering_link = get_bartering_link()
        sod_n_intraday_pos_dict: Dict[str, Dict[str, List[Position]]] | None = None
        if hasattr(bartering_link, "load_positions_by_symbols_dict"):
            sod_n_intraday_pos_dict = (
                bartering_link.load_positions_by_symbols_dict(meta_symbols_n_sec_id_source_dict))

        pos_cache: PosCache = PosCache(BasketCache.static_data)
        pos_cache.start(eligible_brokers, sod_n_intraday_pos_dict, meta_bartering_symbol_side_dict,
                        meta_symbols_n_sec_id_source_dict, meta_no_executed_tradable_symbol_replenishing_side_dict,
                        config_dict={})
        return pos_cache