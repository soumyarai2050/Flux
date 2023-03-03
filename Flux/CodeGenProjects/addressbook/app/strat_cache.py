from threading import RLock, Semaphore
from typing import Dict, Tuple, Optional

import pytz
from pendulum import DateTime

from Flux.CodeGenProjects.addressbook.app.ws_helper import *


class StratCache:
    @staticmethod
    def get_key_from_order_snapshot(order_snapshot: OrderSnapshotBaseModel):
        key: str | None = None
        if order_snapshot.order_brief.security.sec_id is not None and \
                order_snapshot.order_brief.side == Side.BUY:
            key = order_snapshot.order_brief.security.sec_id + "_BID"
        elif order_snapshot.order_brief.security.sec_id is not None and \
                order_snapshot.order_brief.side == Side.SELL:
            key = order_snapshot.order_brief.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_cancel_order(cancel_order: CancelOrderBaseModel):
        key: str | None = None
        if cancel_order.security.sec_id is not None and \
                cancel_order.side == Side.BUY:
            key = cancel_order.security.sec_id + "_BID"
        elif cancel_order.security.sec_id is not None and \
                cancel_order.side == Side.SELL:
            key = cancel_order.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_new_order(new_order: NewOrderBaseModel):
        key: str | None = None
        if new_order.security.sec_id is not None and \
                new_order.side == Side.BUY:
            key = new_order.security.sec_id + "_BID"
        elif new_order.security.sec_id is not None and \
                new_order.side == Side.SELL:
            key = new_order.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_order_journal(order_journal: OrderJournalBaseModel):
        key: str | None = None
        if order_journal.order.security.sec_id is not None and \
                order_journal.order.side == Side.BUY:
            key = order_journal.order.security.sec_id + "_BID"
        elif order_journal.order.security.sec_id is not None and \
                order_journal.order.side == Side.SELL:
            key = order_journal.order.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_strat_brief(strat_brief: StratBriefBaseModel):
        key1: str | None = None
        if strat_brief.pair_buy_side_trading_brief.security.sec_id is not None:
            key1 = strat_brief.pair_buy_side_trading_brief.security.sec_id + "_BID"
        else:
            raise Exception(f"get_key_from_strat_brief: did not find buy sec id;;; strat_brief: {strat_brief}")
        # else not required - returning None (default value of key)
        key2: str | None = None
        if strat_brief.pair_sell_side_trading_brief.security.sec_id is not None:
            key2 = strat_brief.pair_sell_side_trading_brief.security.sec_id + "_ASK"
        else:
            raise Exception(f"get_key_from_strat_brief: did not find sell sec id;;; strat_brief: {strat_brief}")
        # else not required - returning None (default value of key)
        return key1, key2

    @staticmethod
    def get_key_from_pair_strat(pair_strat: PairStratBaseModel):
        key1: str | None = None
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id is not None:
            if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
                key1 = pair_strat.pair_strat_params.strat_leg1.sec.sec_id + "_BID"
            elif pair_strat.pair_strat_params.strat_leg1.side == Side.SELL:
                key1 = pair_strat.pair_strat_params.strat_leg1.sec.sec_id + "_ASK"
        else:
            raise Exception(f"get_key_from_pair_strat: did not find leg1 sec id;;; pair_strat: {pair_strat}")
        key2: str | None = None
        if pair_strat.pair_strat_params.strat_leg2.sec.sec_id is not None:
            if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:
                key2 = pair_strat.pair_strat_params.strat_leg2.sec.sec_id + "_BID"
            elif pair_strat.pair_strat_params.strat_leg2.side == Side.SELL:
                key2 = pair_strat.pair_strat_params.strat_leg2.sec.sec_id + "_ASK"
        else:
            raise Exception(f"get_key_from_pair_strat: did not find leg2 sec id;;; pair_strat: {pair_strat}")
        return key1, key2

    @staticmethod
    def get_key_from_top_of_book(top_of_book: TopOfBookBaseModel) -> Tuple[str, str]:
        return (top_of_book.symbol + "_BID"), (top_of_book.symbol + "_ASK")

    def get_pair_strat(self, date_time: DateTime | None = None) -> Tuple[PairStratBaseModel, DateTime] | None:
        if date_time is None or date_time < self._pair_strat_update_date_time:
            return self._pair_strat, self._pair_strat_update_date_time
        else:
            return None

    # None to remove pair strat
    def set_pair_strat(self, pair_strat: PairStratBaseModel | None) -> DateTime:
        self._pair_strat = pair_strat
        self._pair_strat_update_date_time = DateTime.utcnow()
        return self._pair_strat_update_date_time

    def get_strat_brief(self, date_time: DateTime | None = None) -> Tuple[StratBriefBaseModel, DateTime] | None:
        if date_time is None or date_time < self._strat_brief_update_date_time:
            return self._strat_brief, self._strat_brief_update_date_time
        else:
            return None

    def set_strat_brief(self, strat_brief: StratBriefBaseModel) -> DateTime:
        self._strat_brief = strat_brief
        self._strat_brief_update_date_time = DateTime.utcnow()
        return self._strat_brief_update_date_time

    def get_order_snapshots(self, date_time: DateTime | None = None) -> Tuple[List[OrderSnapshotBaseModel], DateTime] | None:
        if date_time is None or date_time < self._order_snapshots_update_date_time:
            return self._order_snapshots, self._order_snapshots_update_date_time
        else:
            return None

    def set_order_snapshot(self, order_snapshot: OrderSnapshotBaseModel) -> DateTime:
        if self._order_snapshots is None:
            self._order_snapshots = list()
        self._order_snapshots.append(order_snapshot)
        self._order_snapshots_update_date_time = DateTime.utcnow()
        return self._order_snapshots_update_date_time

    def get_order_journals(self, date_time: DateTime | None = None) -> Tuple[List[OrderJournalBaseModel], DateTime] | None:
        if date_time is None or date_time < self._order_journals_update_date_time:
            return self._order_journals, self._order_journals_update_date_time
        else:
            return None

    def set_order_journal(self, order_journal: OrderJournalBaseModel) -> DateTime:
        if self._order_journals is None:
            self._order_journals = list()
        self._order_journals.append(order_journal)
        self._order_journals_update_date_time = DateTime.utcnow()
        return self._order_journals_update_date_time

    def get_fills_journals(self, date_time: DateTime | None = None) -> Tuple[List[FillsJournalBaseModel], DateTime] | None:
        if date_time is None or date_time < self._fills_journals_update_date_time:
            return self._fills_journals, self._fills_journals_update_date_time
        else:
            return None

    def set_fills_journal(self, fills_journal: FillsJournalBaseModel) -> DateTime:
        if self._fills_journals is None:
            self._fills_journals = list()
        self._fills_journals.append(fills_journal)
        self._fills_journals_update_date_time = DateTime.utcnow()
        return self._fills_journals_update_date_time

    def get_cancel_orders(self, date_time: DateTime | None = None) -> Tuple[List[CancelOrderBaseModel], DateTime] | None:
        if date_time is None or date_time < self._cancel_orders_update_date_time:
            return self._cancel_orders, self._cancel_orders_update_date_time
        else:
            return None

    def set_cancel_order(self, cancel_order: CancelOrderBaseModel) -> DateTime:
        if self._cancel_orders is None:
            self._cancel_orders = list()
        self._cancel_orders.append(cancel_order)
        self._cancel_orders_update_date_time = DateTime.utcnow()
        return self._cancel_orders_update_date_time

    def get_new_orders(self, date_time: DateTime | None = None) -> Tuple[List[NewOrderBaseModel], DateTime] | None:
        if date_time is None or date_time < self._new_orders_update_date_time:
            return self._new_orders, self._new_orders_update_date_time
        else:
            return None

    def set_new_order(self, new_order: NewOrderBaseModel) -> DateTime:
        if self._new_orders is None:
            self._new_orders = list()
        self._new_orders.append(new_order)
        self._new_orders_update_date_time = DateTime.utcnow()
        return self._new_orders_update_date_time

    def get_top_of_books(self, date_time: DateTime | None = None) -> Tuple[List[TopOfBookBaseModel], DateTime] | None:
        if date_time is None or date_time < self._top_of_books_update_date_time:
            return self._top_of_books, self._top_of_books_update_date_time
        else:
            return None

    def set_top_of_book(self, top_of_book: TopOfBookBaseModel) -> DateTime:
        if self._top_of_books is None:
            self._top_of_books = list()

        match len(self._top_of_books):
            case 0:
                self._top_of_books.append(top_of_book)
            case 1:
                if self._top_of_books[0].symbol != top_of_book.symbol:
                    self._top_of_books.append(top_of_book)
                else:
                    self._top_of_books[0] = top_of_book
            case 2:
                if self._top_of_books[0].symbol == top_of_book.symbol:
                    self._top_of_books[0] = top_of_book
                elif self._top_of_books[1].symbol == top_of_book.symbol:
                    self._top_of_books[1] = top_of_book
                else:
                    logging.error(f"Unexpected: ToB symbol: {top_of_book.symbol} not in strat symbols: "
                                  f"{self._top_of_books[0].symbol} {self._top_of_books[1].symbol};;; ToB: {top_of_book}, "
                                  f"pair_strat: {self.get_pair_strat()}")
            case unexpected_len_ToB:
                logging.error(f"Unexpected: expected <= 2 ToB, found: {unexpected_len_ToB} in strat TOB symbols: "
                              f"{[tob.symbol for tob in self._top_of_books]};;; ToB passed: {top_of_book}, ToB stored:"
                              f" {[str(tob) for tob in self._top_of_books]}, pair_strat: {self.get_pair_strat()}")
        # Adding tz awareness to make stored object's timezone comparable with initialized datetime in
        # get_top_of_books, else throws errors
        self._top_of_books_update_date_time = top_of_book.last_update_date_time.replace(tzinfo=pytz.UTC)
        return self._top_of_books_update_date_time

    @classmethod
    def notify_all(cls):
        for strat_cache in cls.strat_cache_list:
            strat_cache.notify_semaphore.release()

    @classmethod
    def add(cls, key: str, strat_cache: 'StratCache'):
        strat_idx: int | None = cls.strat_cache_dict.get(key)
        if strat_idx is None:
            cls.strat_cache_list.append(strat_cache)
            cls.strat_cache_dict[key] = len(cls.strat_cache_list) - 1
        else:
            raise Exception(f"Existing StratCache found for add StratCache request: {cls.strat_cache_list[strat_idx]}")

    @classmethod
    def get_by_key(cls, key) -> Optional['StratCache']:
        strat_idx: int = cls.strat_cache_dict.get(key)
        if strat_idx is not None:
            return cls.get_by_idx(strat_idx, key)
        else:
            return None

    @classmethod
    def get_by_idx(cls, strat_idx: int, key: str = "") -> 'StratCache':
        if len(cls.strat_cache_list) > strat_idx:
            return cls.strat_cache_list[strat_idx]
        else:
            raise Exception(f"StratCache not found for request: {strat_idx} {key}")

    @classmethod
    def guaranteed_get_by_key(cls, key1, key2) -> 'StratCache':
        strat_cache: StratCache = cls.get_by_key(key1)
        if strat_cache is None:
            strat_cache = StratCache()
            cls.add(key1, strat_cache)
            cls.add(key2, strat_cache)
            logging.info(f"Created strat cache for key: {key1} {key2}")
        return strat_cache

    strat_cache_list: List['StratCache'] = list()
    strat_cache_dict: Dict[str, int] = dict()

    def __init__(self):
        self.re_ent_lock: RLock = RLock()
        self.notify_semaphore = Semaphore()
        self.stopped = True  # used by consumer thread to stop processing

        self._cancel_orders: List[CancelOrderBaseModel] | None = None
        self._cancel_orders_update_date_time: DateTime = DateTime.utcnow()

        self._new_orders: List[NewOrderBaseModel] | None = None
        self._new_orders_update_date_time: DateTime = DateTime.utcnow()

        self._pair_strat: PairStratBaseModel | None = None
        self._pair_strat_update_date_time: DateTime = DateTime.utcnow()

        self._strat_brief: StratBriefBaseModel | None = None
        self._strat_brief_update_date_time: DateTime = DateTime.utcnow()

        self._order_snapshots: List[OrderSnapshotBaseModel] | None = None
        self._order_snapshots_update_date_time: DateTime = DateTime.utcnow()

        self._order_journals: List[OrderJournalBaseModel] | None = None
        self._order_journals_update_date_time: DateTime = DateTime.utcnow()

        self._fills_journals: List[FillsJournalBaseModel] | None = None
        self._fills_journals_update_date_time: DateTime = DateTime.utcnow()

        self._top_of_books: List[TopOfBookBaseModel] | None = None
        self._top_of_books_update_date_time: DateTime = DateTime.utcnow()

