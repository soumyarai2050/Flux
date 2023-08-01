import asyncio
from typing import Tuple
import sys
from pathlib import PurePath

from Flux.CodeGenProjects.addressbook.app.aggregate import get_ongoing_pair_strat_filter
from Flux.CodeGenProjects.addressbook.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.StratExecutor.strat_manager_service_key_handler import \
    StratManagerServiceKeyHandler
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int, \
    get_native_host_n_port_from_config_dict


config_yaml_path = PurePath(__file__).parent.parent / "data" / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

host, port = get_native_host_n_port_from_config_dict(config_yaml_dict)
strat_manager_service_web_client_internal = \
    StratManagerServiceWebClient.set_or_get_if_instance_exists(host, port)

update_portfolio_status_lock: asyncio.Lock = asyncio.Lock()
update_strat_status_lock: asyncio.Lock = asyncio.Lock()


def get_match_level(pair_strat: PairStrat, sec_id: str, side: Side) -> int:
    match_level: int = 6
    if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == sec_id:
        if pair_strat.pair_strat_params.strat_leg1.side == side:
            match_level = 1
        else:
            match_level = 2
    elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == sec_id:
        if pair_strat.pair_strat_params.strat_leg2.side == side:
            match_level = 1
        else:
            match_level = 2
    return match_level  # no match


# caller must take any locks as required for any read-write consistency - function operates without lock
async def get_ongoing_strats_from_symbol_n_side(sec_id: str, side: Side) -> Tuple[List[PairStrat], List[PairStrat]]:
    from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
        underlying_read_pair_strat_http
    read_pair_strat_filter = get_ongoing_pair_strat_filter(sec_id)
    pair_strats: List[PairStrat] = await underlying_read_pair_strat_http(read_pair_strat_filter)
    match_level_1_pair_strats: List[PairStrat] = list()
    match_level_2_pair_strats: List[PairStrat] = list()
    for pair_strat in pair_strats:
        match_level: int = get_match_level(pair_strat, sec_id, side)
        if match_level == 1:
            match_level_1_pair_strats.append(pair_strat)
        elif match_level == 2:
            match_level_2_pair_strats.append(pair_strat)
        # else not a match ignore
    return match_level_1_pair_strats, match_level_2_pair_strats


def is_ongoing_pair_strat(pair_strat: PairStrat | PairStratBaseModel) -> bool:
    return pair_strat.strat_status.strat_state not in [StratState.StratState_UNSPECIFIED, StratState.StratState_READY,
                                                       StratState.StratState_DONE]


async def update_strat_alert_by_sec_and_side_async(sec_id: str, side: Side, alert_brief: str,
                                                   alert_details: str | None = None,
                                                   severity: Severity = Severity.Severity_ERROR,
                                                   impacted_orders: List[OrderBrief] | None = None):
    from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
        underlying_partial_update_pair_strat_http
    impacted_orders = [] if impacted_orders is None else impacted_orders
    alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
    async with update_strat_status_lock:
        match_level_1_pair_strats, match_level_2_pair_strats = await get_ongoing_strats_from_symbol_n_side(sec_id, side)
        if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
            logging.error(f"error: {alert_brief}; processing {get_symbol_side_key([(sec_id, side)])} "
                          f"no viable pair_strat to report to;;; alert_details: {alert_details}")
            return
        else:
            pair_strat: PairStrat | None = None
            if len(match_level_1_pair_strats) != 0:
                pair_strat = match_level_1_pair_strats[0]
            else:
                pair_strat = match_level_2_pair_strats[0]
            updated_strat_status: StratStatus = pair_strat.strat_status
            updated_strat_status.strat_state = pair_strat.strat_status.strat_state
            updated_strat_status.strat_alerts.append(alert)
        pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=updated_strat_status)
        await underlying_partial_update_pair_strat_http(pair_strat_updated.dict(by_alias=True, exclude_none=True))


async def get_single_exact_match_ongoing_strat_from_symbol_n_side(sec_id: str, side: Side) -> PairStrat | None:
    match_level_1_pair_strats, match_level_2_pair_strats = await get_ongoing_strats_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
        logging.error(f"error: No viable pair_strat for symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
        return
    else:
        pair_strat: PairStrat | None = None
        if len(match_level_1_pair_strats) == 1:
            pair_strat = match_level_1_pair_strats[0]
        else:
            logging.error(f"error: processing {get_symbol_side_key([(sec_id, side)])} pair_strat should be "
                          f"found only one in match_lvl_1, found {match_level_1_pair_strats}")
        if pair_strat is None:
            if len(match_level_2_pair_strats) == 1:
                pair_strat = match_level_2_pair_strats[0]
                logging.error(f"error: pair_strat should be found in level 1 only, symbol_side_key: "
                              f"{get_symbol_side_key([(sec_id, side)])}")
            else:
                logging.error(
                    f"error: multiple ongoing pair strats matching symbol_side_key: "
                    f"{get_symbol_side_key([(sec_id, side)])} found, one "
                    f"match expected, found: {len(match_level_2_pair_strats)}")
        return pair_strat


async def update_strat_alert_async(strat_id: int, alert_brief: str, alert_details: str | None = None,
                                   impacted_orders: List[OrderBrief] | None = None,
                                   severity: Severity = Severity.Severity_ERROR):
    alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
    from Flux.CodeGenProjects.addressbook.generated.FastApi.strat_manager_service_routes import \
        underlying_read_pair_strat_by_id_http, underlying_partial_update_pair_strat_http
    async with update_strat_status_lock:
        pair_strat: PairStrat = await underlying_read_pair_strat_by_id_http(strat_id)
        strat_status: StratStatus = StratStatus(strat_state=pair_strat.strat_status.strat_state,
                                                strat_alerts=(pair_strat.strat_status.strat_alerts.append(alert)))
        pair_strat_updated: PairStratOptional = PairStratOptional(_id=pair_strat.id, strat_status=strat_status)
    await underlying_partial_update_pair_strat_http(pair_strat_updated.dict(by_alias=True, exclude_none=True))


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

#
# def update_portfolio_status(overall_buy_notional: float | None, overall_sell_notional: float | None,
#                             portfolio_alerts: List[Alert] | None = None):
#     """
#     this function is generally invoked in extreme cases - best to not throw any further exceptions from here
#     otherwise the program will terminate - log critical error and continue
#     """
#     try:
#         kwargs = {}
#         act = False
#         if overall_buy_notional is not None:
#             kwargs.update(overall_buy_notional=overall_buy_notional)
#             act = True
#         if overall_sell_notional is not None:
#             kwargs.update(overall_sell_notional=overall_sell_notional)
#             act = True
#         if portfolio_alerts is not None:
#             act = True
#         if act:
#             with update_portfolio_status_lock:
#                 portfolio_status_list: List[
#                     PortfolioStatusBaseModel] = strat_manager_service_web_client_internal.get_all_portfolio_status_client()
#                 logging.debug(f"portfolio_status_list count: {len(portfolio_status_list)}")
#                 if 0 == len(portfolio_status_list):  # no portfolio status set yet - create one
#                     kwargs.update(kill_switch=False)
#                     kwargs.update(portfolio_alerts=portfolio_alerts)
#                     portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
#                     portfolio_status: PortfolioStatusBaseModel = \
#                         strat_manager_service_web_client_internal.create_portfolio_status_client(portfolio_status)
#                     logging.debug(f"created: portfolio_status: {portfolio_status}")
#                 elif 1 == len(portfolio_status_list):
#                     # TODO: we may need to copy non-updated fields form original model
#                     # (we should just update original model with new data (patch) and send)
#                     kwargs.update(kill_switch=portfolio_status_list[0].kill_switch)
#                     kwargs.update(_id=portfolio_status_list[0].id)
#                     if 'overall_buy_notional' not in kwargs:
#                         kwargs.update(overall_buy_notional=portfolio_status_list[0].overall_buy_notional)
#                     if 'overall_sell_notional' not in kwargs:
#                         kwargs.update(overall_sell_notional=portfolio_status_list[0].overall_sell_notional)
#                     if portfolio_status_list[0].portfolio_alerts is not None \
#                             and len(portfolio_status_list[0].portfolio_alerts) > 0:
#                         # TODO LAZY : maybe deep copy instead
#                         if portfolio_alerts is not None:
#                             portfolio_alerts += portfolio_status_list[0].portfolio_alerts
#                         else:
#                             portfolio_alerts = portfolio_status_list[0].portfolio_alerts
#                     kwargs.update(portfolio_alerts=portfolio_alerts)
#                     portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
#                     strat_manager_service_web_client_internal.put_portfolio_status_client(portfolio_status)
#                 else:
#                     logging.critical(
#                         "multiple portfolio limits entries not supported at this time! "
#                         "use swagger UI to delete redundant entries from DB and retry - "
#                         f"this blocks all alert form reaching UI!! alert being processed: {portfolio_alerts}")
#         # else not action required - no action to take - ignore and continue
#     except Exception as e:
#         logging.critical(
#             f"something serious is wrong: update_portfolio_status is throwing an exception!;;; exception: {e}",
#             exc_info=True)


def is_service_up(ignore_error: bool = False):
    try:
        portfolio_status_list: List[
            PortfolioStatusBaseModel] = strat_manager_service_web_client_internal.get_all_portfolio_status_client()
        if 0 == len(portfolio_status_list):  # no portfolio status set yet, create one
            portfolio_status: PortfolioStatusBaseModel = \
                PortfolioStatusBaseModel(_id=1, kill_switch=False,
                                         portfolio_alerts=[],
                                         overall_buy_notional=0,
                                         overall_sell_notional=0,
                                         overall_buy_fill_notional=0,
                                         overall_sell_fill_notional=0,
                                         alert_update_seq_num=0)
            strat_manager_service_web_client_internal.create_portfolio_status_client(portfolio_status)
        return True
    except Exception as e:
        if not ignore_error:
            logging.exception("service_up test failed - tried get_all_portfolio_status_client (and maybe create);;;"
                          f"exception: {e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    rolling_max_order_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_rolling_tx_count=5, rolling_tx_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=20, max_open_notional_per_side=100_000,
                                                    max_gross_n_open_notional=2_400_000,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=eligible_brokers)
    return portfolio_limits_obj


@except_n_log_alert(severity=Severity.Severity_ERROR)
def create_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    portfolio_limits_obj = get_new_portfolio_limits(eligible_brokers)
    portfolio_limits: PortfolioLimitsBaseModel = \
        strat_manager_service_web_client_internal.create_portfolio_limits_client(portfolio_limits_obj)
    logging.info(f"created portfolio_limits;;; {portfolio_limits_obj}")
    return portfolio_limits


@except_n_log_alert(severity=Severity.Severity_ERROR)
def get_portfolio_limits() -> PortfolioLimitsBaseModel | None:
    portfolio_limits_list: List[
        PortfolioLimitsBaseModel] = strat_manager_service_web_client_internal.get_all_portfolio_limits_client()
    if portfolio_limits_list is None or len(portfolio_limits_list) <= 0:
        return None
    elif len(portfolio_limits_list) > 1:
        # portfolio limits: PortfolioLimits = portfolio_limits_list[0]
        # for portfolio limits entry in portfolio limits list:
        #   if portfolio limits entry.id < portfolio_limits.id:
        #          portfolio_limits = portfolio_limits_entry
        # logging.debug(f"portfolio_limit_list: {portfolio_limits_list}, selected portfolio_limits: {portfolio_limits}")
        # return portfolio limits
        err_str_ = f"multiple: ({len(portfolio_limits_list)}) portfolio_limits entries not supported at this time!" \
                   f" use swagger UI to delete redundant entries: {portfolio_limits_list} from DB and retry"
        raise Exception(err_str_)
    else:
        return portfolio_limits_list[0]


def get_new_order_limits():
    ord_limit_obj = OrderLimitsBaseModel(_id=1, max_basis_points=1500, max_px_deviation=20, max_px_levels=5,
                                         max_order_qty=500, min_order_notional=100, max_order_notional=90_000)
    return ord_limit_obj


def get_order_limits() -> OrderLimitsBaseModel | None:
    order_limits_list: List[
        OrderLimitsBaseModel] = strat_manager_service_web_client_internal.get_all_order_limits_client()
    if order_limits_list is None or len(order_limits_list) <= 0:
        return None
    elif len(order_limits_list) > 1:
        # order_limits: OrderLimits = order_limits_list[0]
        # for order_limits_entry in order_limits_list:
        #   if order_limits_entry.id < order_limits.id:
        #          order_limits = order_limits_entry
        # logging.debug(f"order_limits_list: {order_limits_list}, selected order_limits: {order_limits}")
        # return order_limits
        raise Exception(f"multiple: ({len(order_limits_list)}) order limits entries not supported at this time!"
                        f" use swagger UI to delete redundant entries: {order_limits_list} from DB and retry")
    else:
        return order_limits_list[0]


def create_order_limits():
    ord_limit_obj = get_new_order_limits()
    strat_manager_service_web_client_internal.create_order_limits_client(ord_limit_obj)


def get_symbol_side_key(symbol_side_tuple_list: List[Tuple[str, str]]) -> str:
    key_str = ",".join([f"symbol-side={symbol}-{side}" for symbol, side in symbol_side_tuple_list])
    return f"%%{key_str}%%"


def get_pair_strat_log_key(pair_strat: PairStrat | PairStratBaseModel | PairStratOptional):
    leg_1_sec_id = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
    leg_1_side = pair_strat.pair_strat_params.strat_leg1.side
    if pair_strat.pair_strat_params.strat_leg2 is not None:
        leg_2_sec_id = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        leg_2_side = pair_strat.pair_strat_params.strat_leg2.side
        symbol_side_key = get_symbol_side_key([(leg_1_sec_id, leg_1_side), (leg_2_sec_id, leg_2_side)])
    else:
        symbol_side_key = get_symbol_side_key([(leg_1_sec_id, leg_1_side)])
    base_pair_strat_key = StratManagerServiceKeyHandler.get_log_key_from_pair_strat(pair_strat)
    return f"{symbol_side_key}-{base_pair_strat_key}"


def get_strat_brief_log_key(strat_brief: StratBrief | StratBriefBaseModel | StratBriefOptional):
    buy_sec_id = strat_brief.pair_buy_side_trading_brief.security.sec_id
    buy_side = strat_brief.pair_buy_side_trading_brief.side
    sell_sec_id = strat_brief.pair_sell_side_trading_brief.security.sec_id
    sell_side = strat_brief.pair_sell_side_trading_brief.side
    symbol_side_key = get_symbol_side_key([(buy_sec_id, buy_side), (sell_sec_id, sell_side)])
    base_strat_brief_key = StratManagerServiceKeyHandler.get_log_key_from_strat_brief(strat_brief)
    return f"{symbol_side_key}-{base_strat_brief_key}"


def get_order_journal_log_key(order_journal: OrderJournal | OrderJournalBaseModel | OrderJournalOptional):
    sec_id = order_journal.order.security.sec_id
    side = order_journal.order.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_order_journal_key = StratManagerServiceKeyHandler.get_log_key_from_order_journal(order_journal)
    return f"{symbol_side_key}-{base_order_journal_key}"


def get_fills_journal_log_key(fills_journal: FillsJournal | FillsJournalBaseModel | FillsJournalOptional):
    sec_id = fills_journal.fill_symbol
    side = fills_journal.fill_side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_fill_journal_key = StratManagerServiceKeyHandler.get_log_key_from_fills_journal(fills_journal)
    return f"{symbol_side_key}-{base_fill_journal_key}"


def get_order_snapshot_log_key(order_snapshot: OrderSnapshot | OrderSnapshotBaseModel | OrderSnapshotOptional):
    sec_id = order_snapshot.order_brief.security.sec_id
    side = order_snapshot.order_brief.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_order_snapshot_key = StratManagerServiceKeyHandler.get_log_key_from_order_snapshot(order_snapshot)
    return f"{symbol_side_key}-{base_order_snapshot_key}"


def get_symbol_side_snapshot_log_key(symbol_side_snapshot: SymbolSideSnapshot | SymbolSideSnapshotBaseModel | SymbolSideSnapshotOptional):
    sec_id = symbol_side_snapshot.security.sec_id
    side = symbol_side_snapshot.side
    symbol_side_key = get_symbol_side_key([(sec_id, side)])
    base_symbol_side_snapshot_key = \
        StratManagerServiceKeyHandler.get_log_key_from_symbol_side_snapshot(symbol_side_snapshot)
    return f"{symbol_side_key}-{base_symbol_side_snapshot_key}"


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
        strat_manager_service_web_client_internal.get_executor_check_snapshot_query_client(symbol, side,
                                                                                           applicable_period_seconds)
    if len(executor_check_snapshot_list) == 1:
        return get_consumable_participation_qty(executor_check_snapshot_list, max_participation_rate)
    else:
        logging.error("Received unexpected length of executor_check_snapshot_list from query "
                      f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                      f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                      f"get_executor_check_snapshot_query pre implementation")
        return
