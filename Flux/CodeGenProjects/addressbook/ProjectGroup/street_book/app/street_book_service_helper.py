# standard imports
import ctypes
import logging
import sys
import threading

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_key_handler import (
    StreetBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.phone_book_n_street_book_client import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key)

update_strat_status_lock: threading.Lock = threading.Lock()


def all_service_up_check(executor_client: StreetBookServiceHttpClient, ignore_error: bool = False):
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            email_book_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            post_barter_engine_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            log_book_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            executor_client.get_all_ui_layout_client())
        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("all_service_up_check test failed - tried "
                              "get_all_ui_layout_client of phone_book, street_book and log_book ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


# def update_strat_alert_by_sec_and_side_async(sec_id: str, side: Side, alert_brief: str,
#                                              alert_details: str | None = None,
#                                              severity: Severity = Severity.Severity_ERROR,
#                                              impacted_chores: List[ChoreBrief] | None = None):
#     impacted_chores = [] if impacted_chores is None else impacted_chores
#     alert: Alert = create_alert(alert_brief, alert_details, impacted_chores, severity)
#     with update_strat_status_lock:
#         pair_strat: PairStratBaseModel = \
#             email_book_service_http_client.get_ongoing_strat_from_symbol_side_query_client(sec_id, side)
#         updated_strat_status: StratStatus = pair_strat.strat_status
#         updated_strat_status.strat_state = pair_strat.strat_status.strat_state
#         updated_strat_status.strat_alerts.append(alert)
#         pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=updated_strat_status)
#         email_book_service_http_client.patch_pair_strat_client(pair_strat_updated.dict(by_alias=True,
#                                                                                           exclude_none=True),
#                                                                   return_obj_copy=False)

#
# def update_strat_alert_async(strat_id: int, alert_brief: str, alert_details: str | None = None,
#                              impacted_chores: List[ChoreBrief] | None = None,
#                              severity: Severity = Severity.Severity_ERROR):
#     alert: Alert = create_alert(alert_brief, alert_details, impacted_chores, severity)
#     with update_strat_status_lock:
#         pair_strat: PairStrat = email_book_service_http_client.get_pair_strat_client(strat_id)
#         strat_status: StratStatus = StratStatus(strat_state=pair_strat.strat_status.strat_state,
#                                                 strat_alerts=(pair_strat.strat_status.strat_alerts.append(alert)))
#         pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=strat_status)
#     email_book_service_http_client.patch_pair_strat_client(pair_strat_updated.dict(by_alias=True,
#                                                                                       exclude_none=True),
#                                                               return_obj_copy=False)


def get_chore_journal_log_key(chore_journal: ChoreJournal | ChoreJournalBaseModel | ChoreJournalOptional):
    sec_id = chore_journal.chore.security.sec_id
    side = chore_journal.chore.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_chore_journal_key = StreetBookServiceKeyHandler.get_log_key_from_chore_journal(chore_journal)
    return f"{symbol_side_key}-{base_chore_journal_key}"


def get_fills_journal_log_key(fills_journal: FillsJournal | FillsJournalBaseModel | FillsJournalOptional):
    sec_id = fills_journal.fill_symbol
    side = fills_journal.fill_side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_fill_journal_key = StreetBookServiceKeyHandler.get_log_key_from_fills_journal(fills_journal)
    return f"{symbol_side_key}-{base_fill_journal_key}"


def get_chore_snapshot_log_key(chore_snapshot: ChoreSnapshot | ChoreSnapshotBaseModel | ChoreSnapshotOptional):
    sec_id = chore_snapshot.chore_brief.security.sec_id
    side = chore_snapshot.chore_brief.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_chore_snapshot_key = StreetBookServiceKeyHandler.get_log_key_from_chore_snapshot(chore_snapshot)
    return f"{symbol_side_key}-{base_chore_snapshot_key}"


def get_symbol_side_snapshot_log_key(
        symbol_side_snapshot: SymbolSideSnapshot | SymbolSideSnapshotBaseModel | SymbolSideSnapshotOptional):
    sec_id = symbol_side_snapshot.security.sec_id
    side = symbol_side_snapshot.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_symbol_side_snapshot_key = \
        StreetBookServiceKeyHandler.get_log_key_from_symbol_side_snapshot(symbol_side_snapshot)
    return f"{symbol_side_key}-{base_symbol_side_snapshot_key}"


def get_strat_brief_log_key(strat_brief: StratBrief | StratBriefBaseModel | StratBriefOptional):
    buy_sec_id = strat_brief.pair_buy_side_bartering_brief.security.sec_id
    buy_side = strat_brief.pair_buy_side_bartering_brief.side
    sell_sec_id = strat_brief.pair_sell_side_bartering_brief.security.sec_id
    sell_side = strat_brief.pair_sell_side_bartering_brief.side
    symbol_side_key = get_symbol_side_key([(buy_sec_id, buy_side), (sell_sec_id, sell_side)])
    base_strat_brief_key = StreetBookServiceKeyHandler.get_log_key_from_strat_brief(strat_brief)
    return f"{symbol_side_key}-{base_strat_brief_key}"


def get_consumable_participation_qty(
        executor_check_snapshot_obj_list: List[ExecutorCheckSnapshot],
        max_participation_rate: float) -> int | None:
    if len(executor_check_snapshot_obj_list) == 1:
        executor_check_snapshot_obj = executor_check_snapshot_obj_list[0]
        participation_period_chore_qty_sum = executor_check_snapshot_obj.last_n_sec_chore_qty
        participation_period_last_barter_qty_sum = executor_check_snapshot_obj.last_n_sec_barter_qty

        return int(((participation_period_last_barter_qty_sum / 100) *
                    max_participation_rate) - participation_period_chore_qty_sum)
    else:
        logging.error(f"Received executor_check_snapshot_obj_list with length {len(executor_check_snapshot_obj_list)}"
                      f" expected 1")
        return None


def get_consumable_participation_qty_http(symbol: str, side: Side, applicable_period_seconds: int,
                                          max_participation_rate: float, asyncio_loop) -> int | None:
    run_coro = get_consumable_participation_qty_underlying_http(symbol, side, applicable_period_seconds,
                                                                max_participation_rate)
    future = asyncio.run_coroutine_threadsafe(run_coro, asyncio_loop)

    # block for task to finish
    try:
        result = future.result()
        return result
    except Exception as e_:
        logging.exception(f"get_consumable_participation_qty_underlying_http failed with exception: {e_}")


async def get_consumable_participation_qty_underlying_http(symbol: str, side: Side, applicable_period_seconds: int,
                                                           max_participation_rate: float) -> int | None:
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes import (
        underlying_get_executor_check_snapshot_query_http)

    executor_check_snapshot_list: List[ExecutorCheckSnapshot] = \
        await underlying_get_executor_check_snapshot_query_http(symbol, side, applicable_period_seconds)

    if len(executor_check_snapshot_list) == 1:
        return get_consumable_participation_qty(executor_check_snapshot_list, max_participation_rate)
    else:
        logging.error("Received unexpected length of executor_check_snapshot_list from query "
                      f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                      f"{get_symbol_side_key([(symbol, side)])}, applicable_period_seconds: {applicable_period_seconds}"
                      f", max_participation_rate: {max_participation_rate}, likely bug in "
                      f"get_executor_check_snapshot_query pre implementation")
        return


def get_new_strat_limits(eligible_brokers: List[Broker] | None = None) -> StratLimits:
    cancel_rate: CancelRate = CancelRate(max_cancel_rate=60, applicable_period_seconds=0, waived_min_chores=5)
    market_barter_volume_participation: MarketBarterVolumeParticipation = \
        MarketBarterVolumeParticipation(max_participation_rate=40,
                                       applicable_period_seconds=180)
    market_depth: OpenInterestParticipation = OpenInterestParticipation(participation_rate=10, depth_levels=3)
    residual_restriction: ResidualRestriction = ResidualRestriction(max_residual=30_000, residual_mark_seconds=4)
    strat_limits: StratLimits = StratLimits(max_open_chores_per_side=5,
                                            max_single_leg_notional=get_default_max_notional(),
                                            max_open_single_leg_notional=30_000,
                                            max_net_filled_notional=160_000,
                                            max_concentration=10,
                                            limit_up_down_volume_participation_rate=1,
                                            eligible_brokers=eligible_brokers,
                                            cancel_rate=cancel_rate,
                                            market_barter_volume_participation=market_barter_volume_participation,
                                            market_depth=market_depth,
                                            residual_restriction=residual_restriction,
                                            min_chore_notional=100
                                            )
    return strat_limits


def get_new_strat_status(strat_limits_obj: StratLimits) -> StratStatus:
    strat_status = StratStatus(fills_brief=[], open_chores_brief=[], total_buy_qty=0,
                               total_sell_qty=0, total_chore_qty=0, total_open_buy_qty=0,
                               total_open_sell_qty=0, avg_open_buy_px=0.0, avg_open_sell_px=0.0,
                               total_open_buy_notional=0.0, total_open_sell_notional=0.0,
                               total_open_exposure=0.0, total_fill_buy_qty=0,
                               total_fill_sell_qty=0, avg_fill_buy_px=0.0, avg_fill_sell_px=0.0,
                               total_fill_buy_notional=0.0, total_fill_sell_notional=0.0,
                               total_fill_exposure=0.0, total_cxl_buy_qty=0.0,
                               total_cxl_sell_qty=0.0, avg_cxl_buy_px=0.0, avg_cxl_sell_px=0.0,
                               total_cxl_buy_notional=0.0, total_cxl_sell_notional=0.0,
                               total_cxl_exposure=0.0, average_premium=0.0,
                               balance_notional=strat_limits_obj.max_single_leg_notional,
                               strat_status_update_seq_num=0)
    return strat_status


def create_stop_md_script(running_process_name: str, generation_stop_file_path: str):
    # stop file generator
    with open(generation_stop_file_path, "w") as fl:
        fl.write("#!/bin/bash\n")
        fl.write(f"PROCESS_COUNT=`pgrep {running_process_name} | wc -l`\n")
        fl.write('if [ "$PROCESS_COUNT" -eq 0 ]; then\n')
        fl.write('  echo "nothing to kill"\n')
        fl.write('else\n')
        fl.write('  echo "PC: $PROCESS_COUNT"\n')
        fl.write(f'  `pgrep {running_process_name} | xargs kill`\n')
        fl.write('fi\n')


def get_default_max_notional() -> int:
    return 300_000


class MobileBookMutexManager:
    def __init__(self, mobile_book_provider: ctypes.CDLL, *args):
        self.mobile_book_provider = mobile_book_provider
        self._mutex_list = []
        for arg in args:
            if arg is not None:
                try:
                    mutex = arg.get_mutex()
                except AttributeError as attr_err:
                    logging.exception(f"get_mutex failed for one of passed argument, exception: {attr_err}")
                except Exception as e_:
                    logging.exception(f"Something went wrong with get_mutex call for one of "
                                      f"passed argument, exception: {e_}")
                else:
                    self._mutex_list.append(mutex)

    def __enter__(self):
        for mutex in self._mutex_list:
            self.mobile_book_provider.lock_mutex(mutex)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for mutex in self._mutex_list:
            self.mobile_book_provider.unlock_mutex(mutex)
