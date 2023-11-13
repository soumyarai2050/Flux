# standard imports
import logging
import sys
import threading

# project imports
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import *
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_key_handler import (
    StratExecutorServiceKeyHandler)
from FluxPythonUtils.scripts.utility_functions import get_symbol_side_key
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import (
    PairStrat, PairStratBaseModel, PortfolioStatusBaseModel, PairStratOptional, OrderLimitsBaseModel)
from Flux.CodeGenProjects.strat_executor.app.get_pair_strat_n_executor_client import *
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)

update_strat_status_lock: threading.Lock = threading.Lock()


def all_service_up_check(executor_client: StratExecutorServiceHttpClient, ignore_error: bool = False):
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            strat_manager_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            post_trade_engine_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            log_analyzer_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            executor_client.get_all_ui_layout_client())
        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("all_service_up_check test failed - tried "
                              "get_all_ui_layout_client of pair_strat_engine, strat_executor and log_analyzer ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


# def update_strat_alert_by_sec_and_side_async(sec_id: str, side: Side, alert_brief: str,
#                                              alert_details: str | None = None,
#                                              severity: Severity = Severity.Severity_ERROR,
#                                              impacted_orders: List[OrderBrief] | None = None):
#     impacted_orders = [] if impacted_orders is None else impacted_orders
#     alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
#     with update_strat_status_lock:
#         pair_strat: PairStratBaseModel = \
#             strat_manager_service_http_client.get_ongoing_strat_from_symbol_side_query_client(sec_id, side)
#         updated_strat_status: StratStatus = pair_strat.strat_status
#         updated_strat_status.strat_state = pair_strat.strat_status.strat_state
#         updated_strat_status.strat_alerts.append(alert)
#         pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=updated_strat_status)
#         strat_manager_service_http_client.patch_pair_strat_client(pair_strat_updated.dict(by_alias=True,
#                                                                                           exclude_none=True),
#                                                                   return_obj_copy=False)

#
# def update_strat_alert_async(strat_id: int, alert_brief: str, alert_details: str | None = None,
#                              impacted_orders: List[OrderBrief] | None = None,
#                              severity: Severity = Severity.Severity_ERROR):
#     alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
#     with update_strat_status_lock:
#         pair_strat: PairStrat = strat_manager_service_http_client.get_pair_strat_client(strat_id)
#         strat_status: StratStatus = StratStatus(strat_state=pair_strat.strat_status.strat_state,
#                                                 strat_alerts=(pair_strat.strat_status.strat_alerts.append(alert)))
#         pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=strat_status)
#     strat_manager_service_http_client.patch_pair_strat_client(pair_strat_updated.dict(by_alias=True,
#                                                                                       exclude_none=True),
#                                                               return_obj_copy=False)


def get_order_journal_log_key(order_journal: OrderJournal | OrderJournalBaseModel | OrderJournalOptional):
    sec_id = order_journal.order.security.sec_id
    side = order_journal.order.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_order_journal_key = StratExecutorServiceKeyHandler.get_log_key_from_order_journal(order_journal)
    return f"{symbol_side_key}-{base_order_journal_key}"


def get_fills_journal_log_key(fills_journal: FillsJournal | FillsJournalBaseModel | FillsJournalOptional):
    sec_id = fills_journal.fill_symbol
    side = fills_journal.fill_side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_fill_journal_key = StratExecutorServiceKeyHandler.get_log_key_from_fills_journal(fills_journal)
    return f"{symbol_side_key}-{base_fill_journal_key}"


def get_order_snapshot_log_key(order_snapshot: OrderSnapshot | OrderSnapshotBaseModel | OrderSnapshotOptional):
    sec_id = order_snapshot.order_brief.security.sec_id
    side = order_snapshot.order_brief.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_order_snapshot_key = StratExecutorServiceKeyHandler.get_log_key_from_order_snapshot(order_snapshot)
    return f"{symbol_side_key}-{base_order_snapshot_key}"


def get_symbol_side_snapshot_log_key(
        symbol_side_snapshot: SymbolSideSnapshot | SymbolSideSnapshotBaseModel | SymbolSideSnapshotOptional):
    sec_id = symbol_side_snapshot.security.sec_id
    side = symbol_side_snapshot.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_symbol_side_snapshot_key = \
        StratExecutorServiceKeyHandler.get_log_key_from_symbol_side_snapshot(symbol_side_snapshot)
    return f"{symbol_side_key}-{base_symbol_side_snapshot_key}"


def get_strat_brief_log_key(strat_brief: StratBrief | StratBriefBaseModel | StratBriefOptional):
    buy_sec_id = strat_brief.pair_buy_side_trading_brief.security.sec_id
    buy_side = strat_brief.pair_buy_side_trading_brief.side
    sell_sec_id = strat_brief.pair_sell_side_trading_brief.security.sec_id
    sell_side = strat_brief.pair_sell_side_trading_brief.side
    symbol_side_key = get_symbol_side_key([(buy_sec_id, buy_side), (sell_sec_id, sell_side)])
    base_strat_brief_key = StratExecutorServiceKeyHandler.get_log_key_from_strat_brief(strat_brief)
    return f"{symbol_side_key}-{base_strat_brief_key}"


def get_consumable_participation_qty(
        executor_check_snapshot_obj_list: List[ExecutorCheckSnapshot],
        max_participation_rate: float) -> int | None:
    if len(executor_check_snapshot_obj_list) == 1:
        executor_check_snapshot_obj = executor_check_snapshot_obj_list[0]
        participation_period_order_qty_sum = executor_check_snapshot_obj.last_n_sec_order_qty
        participation_period_last_trade_qty_sum = executor_check_snapshot_obj.last_n_sec_trade_qty

        return int(((participation_period_last_trade_qty_sum / 100) *
                    max_participation_rate) - participation_period_order_qty_sum)
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
    from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
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
    cancel_rate: CancelRate = CancelRate(max_cancel_rate=60, applicable_period_seconds=0, waived_min_orders=5)
    market_trade_volume_participation: MarketTradeVolumeParticipation = \
        MarketTradeVolumeParticipation(max_participation_rate=40,
                                       applicable_period_seconds=180)
    market_depth: OpenInterestParticipation = OpenInterestParticipation(participation_rate=10, depth_levels=3)
    residual_restriction: ResidualRestriction = ResidualRestriction(max_residual=30_000, residual_mark_seconds=4)
    strat_limits: StratLimits = StratLimits(max_open_orders_per_side=5,
                                            max_cb_notional=get_default_max_notional(),
                                            max_open_cb_notional=30_000,
                                            max_net_filled_notional=160_000,
                                            max_concentration=10,
                                            limit_up_down_volume_participation_rate=1,
                                            eligible_brokers=eligible_brokers,
                                            cancel_rate=cancel_rate,
                                            market_trade_volume_participation=market_trade_volume_participation,
                                            market_depth=market_depth,
                                            residual_restriction=residual_restriction
                                            )
    return strat_limits


def get_new_strat_status(strat_limits_obj: StratLimits) -> StratStatus:
    strat_state: StratState = StratState.StratState_READY
    strat_status = StratStatus(strat_state=strat_state,
                               fills_brief=[], open_orders_brief=[], total_buy_qty=0,
                               total_sell_qty=0, total_order_qty=0, total_open_buy_qty=0,
                               total_open_sell_qty=0, avg_open_buy_px=0.0, avg_open_sell_px=0.0,
                               total_open_buy_notional=0.0, total_open_sell_notional=0.0,
                               total_open_exposure=0.0, total_fill_buy_qty=0,
                               total_fill_sell_qty=0, avg_fill_buy_px=0.0, avg_fill_sell_px=0.0,
                               total_fill_buy_notional=0.0, total_fill_sell_notional=0.0,
                               total_fill_exposure=0.0, total_cxl_buy_qty=0.0,
                               total_cxl_sell_qty=0.0, avg_cxl_buy_px=0.0, avg_cxl_sell_px=0.0,
                               total_cxl_buy_notional=0.0, total_cxl_sell_notional=0.0,
                               total_cxl_exposure=0.0, average_premium=0.0, market_premium=0,
                               balance_notional=strat_limits_obj.max_cb_notional,
                               strat_status_update_seq_num=0)
    return strat_status


def is_ongoing_strat(strat_status: StratStatus | StratStatusBaseModel) -> bool:
    return strat_status.strat_state not in [StratState.StratState_UNSPECIFIED,
                                            StratState.StratState_READY,
                                            StratState.StratState_DONE,
                                            StratState.StratState_SNOOZED]


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
