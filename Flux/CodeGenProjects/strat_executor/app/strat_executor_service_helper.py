# standard imports
import logging
import sys
import threading

# project imports
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_key_handler import (
    StratExecutorServiceKeyHandler)
from FluxPythonUtils.scripts.utility_functions import get_symbol_side_key
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import (
    PairStrat, PairStratBaseModel, PortfolioStatusBaseModel, PairStratOptional, OrderLimitsBaseModel)
from Flux.CodeGenProjects.strat_executor.app.get_pair_strat_n_executor_client import *


update_strat_status_lock: threading.Lock = threading.Lock()


def is_pair_strat_engine_service_up(ignore_error: bool = False):
    try:
        portfolio_status_list: List[PortfolioStatusBaseModel] = (
            strat_manager_service_http_client.get_all_portfolio_status_client())
        if not portfolio_status_list:  # no portfolio status set yet, create one
            if not ignore_error:
                logging.exception("pair_strat_engine service is up but no portfolio_status exists", exc_info=True)
            return False
        order_limits: List[OrderLimitsBaseModel] = strat_manager_service_http_client.get_all_order_limits_client()
        if not order_limits:
            if not ignore_error:
                logging.exception("pair_strat_engine service is up but no order_limits exists", exc_info=True)
            return False
        portfolio_limits: List[OrderLimitsBaseModel] = (
            strat_manager_service_http_client.get_all_portfolio_limits_client())
        if not portfolio_limits:
            if not ignore_error:
                logging.exception("pair_strat_engine service is up but no portfolio_limits exists", exc_info=True)
            return False
        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_pair_strat_engine_service_up test failed - tried "
                              "get_all_portfolio_status_client, get_all_order_limits_client and "
                              "get_all_portfolio_limits_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def update_strat_alert_by_sec_and_side_async(sec_id: str, side: Side, alert_brief: str,
                                             alert_details: str | None = None,
                                             severity: Severity = Severity.Severity_ERROR,
                                             impacted_orders: List[OrderBrief] | None = None):
    impacted_orders = [] if impacted_orders is None else impacted_orders
    alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
    with update_strat_status_lock:
        pair_strat: PairStratBaseModel = \
            strat_manager_service_http_client.get_ongoing_strat_from_symbol_side_query_client(sec_id, side)
        updated_strat_status: StratStatus = pair_strat.strat_status
        updated_strat_status.strat_state = pair_strat.strat_status.strat_state
        updated_strat_status.strat_alerts.append(alert)
        pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=updated_strat_status)
        strat_manager_service_http_client.patch_pair_strat_client(pair_strat_updated.dict(by_alias=True,
                                                                                          exclude_none=True),
                                                                  return_obj_copy=False)


def update_strat_alert_async(strat_id: int, alert_brief: str, alert_details: str | None = None,
                             impacted_orders: List[OrderBrief] | None = None,
                             severity: Severity = Severity.Severity_ERROR):
    alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
    with update_strat_status_lock:
        pair_strat: PairStrat = strat_manager_service_http_client.get_pair_strat_client(strat_id)
        strat_status: StratStatus = StratStatus(strat_state=pair_strat.strat_status.strat_state,
                                                strat_alerts=(pair_strat.strat_status.strat_alerts.append(alert)))
        pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=strat_status)
    strat_manager_service_http_client.patch_pair_strat_client(pair_strat_updated.dict(by_alias=True,
                                                                                      exclude_none=True),
                                                              return_obj_copy=False)


def create_alert(alert_brief: str, alert_details: str | None = None, impacted_order: List[OrderBrief] | None = None,
                 severity: Severity = Severity.Severity_ERROR) -> Alert:
    kwargs = {}
    kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False, last_update_date_time=DateTime.utcnow(),
                  alert_count=1)
    if alert_details is not None:
        kwargs.update(alert_details=alert_details)
    if impacted_order is not None:
        kwargs.update(impacted_order=impacted_order)
    return Alert(**kwargs)


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


def except_n_log_alert(severity: Severity = Severity.Severity_ERROR):
    def decorator_function(original_function):
        def wrapper_function(*args, **kwargs):
            result = None
            try:
                result = original_function(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                alert_brief: str = f"exception: {e} while attempting {original_function.__name__}, " \
                                   f"date-time: {DateTime.now()}"
                alert_details: str = f"{exc_type}: file: {filename}, line: {exc_tb.tb_lineno}, args: {args}, " \
                                     f"kwargs: {kwargs}"
                logging.error(f"{alert_brief};;; {alert_details}")
            return result

        return wrapper_function

    return decorator_function


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
                                          max_participation_rate: float) -> int | None:
    executor_check_snapshot_list: List[ExecutorCheckSnapshot] = \
        strat_executor_http_client.get_executor_check_snapshot_query_client(symbol, side, applicable_period_seconds)
    if len(executor_check_snapshot_list) == 1:
        return get_consumable_participation_qty(executor_check_snapshot_list, max_participation_rate)
    else:
        logging.error("Received unexpected length of executor_check_snapshot_list from query "
                      f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                      f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
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
                                            max_cb_notional=300_000,
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
