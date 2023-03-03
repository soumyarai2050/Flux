import logging
from typing import List, Tuple
import sys
import os
from pendulum import DateTime
from threading import Lock

from Flux.CodeGenProjects.addressbook.app.aggregate import get_pair_strat_sec_filter_json
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import  *
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient

# TODO: read host and port from env

strat_manager_service_web_client_internal = StratManagerServiceWebClient()

update_portfolio_status_lock: Lock = Lock()
update_strat_status_lock: Lock = Lock()


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
    from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
        underlying_read_pair_strat_http
    read_pair_strat_filter = get_pair_strat_sec_filter_json(sec_id)
    pair_strats: List[PairStrat] = await underlying_read_pair_strat_http(read_pair_strat_filter)
    match_level_1_pair_strats: List[PairStrat] = list()
    match_level_2_pair_strats: List[PairStrat] = list()
    for pair_strat in pair_strats:
        # TODO LAZY: move this to aggregate
        if is_ongoing_pair_strat(pair_strat):
            match_level: int = get_match_level(pair_strat, sec_id, side)
            if match_level == 1:
                match_level_1_pair_strats.append(pair_strat)
            elif match_level == 2:
                match_level_2_pair_strats.append(pair_strat)
            # else not a match ignore
        # else not required, ignore unspecified, ready, or done strats (ignore yet to start or completed, match ongoing)
    return match_level_1_pair_strats, match_level_2_pair_strats


def is_ongoing_pair_strat(pair_strat: PairStrat | PairStratBaseModel) -> bool:
    return pair_strat.strat_status.strat_state not in [StratState.StratState_UNSPECIFIED, StratState.StratState_READY,
                                                       StratState.StratState_DONE]


async def update_strat_alert_by_sec_and_side_async(sec_id: str, side: Side, alert_brief: str,
                                                   alert_details: str | None = None,
                                                   severity: Severity = Severity.Severity_ERROR,
                                                   impacted_orders: List[OrderBrief] | None = None):
    from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_routes import \
        underlying_partial_update_pair_strat_http
    impacted_orders = [] if impacted_orders is None else impacted_orders
    alert: Alert = create_alert(alert_brief, alert_details, impacted_orders, severity)
    with update_strat_status_lock:
        match_level_1_pair_strats, match_level_2_pair_strats = await get_ongoing_strats_from_symbol_n_side(sec_id, side)
        if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
            logging.error(f"error: {alert_brief} processing {sec_id}, side: {side} no viable pair_strat to report to"
                          f";;; alert_details: {alert_details}")
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
        await underlying_partial_update_pair_strat_http(pair_strat_updated)


async def get_single_exact_match_ongoing_strat_from_symbol_n_side(sec_id: str, side: Side) -> PairStrat | None:
    match_level_1_pair_strats, match_level_2_pair_strats = await get_ongoing_strats_from_symbol_n_side(sec_id, side)
    if len(match_level_1_pair_strats) == 0 and len(match_level_2_pair_strats) == 0:
        logging.error(f"error: No viable pair_strat for symbol {sec_id}, side: {side}")
        return
    else:
        pair_strat: PairStrat | None = None
        if len(match_level_1_pair_strats) == 1:
            pair_strat = match_level_1_pair_strats[0]
        else:
            logging.error(f"error: pair_strat should be found only one in match_lvl_1, "
                          f"found {match_level_1_pair_strats}")
        if len(match_level_2_pair_strats) == 1:
            pair_strat = match_level_2_pair_strats[0]
            logging.error(f"error: pair_strat should be found in level 1 only, when provided "
                          f"symbol: {sec_id} and side: {side}")
        else:
            logging.error(f"error: multiple ongoing pair strats matching symbol: {sec_id} & side: {side} found, one "
                          f"match expected, found: {len(match_level_1_pair_strats)}")
        return pair_strat


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
    kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False)
    if alert_details is not None:
        kwargs.update(alert_details=alert_details)
    if impacted_order is not None:
        kwargs.update(impacted_order=impacted_order)
    return Alert(**kwargs)


def update_portfolio_status(overall_buy_notional: float | None, overall_sell_notional: float | None,
                            portfolio_alerts: List[Alert] | None = None):
    """
    this function is generally invoked in extreme cases - best to not throw any further exceptions from here
    otherwise the program will terminate - log critical error and continue
    """
    try:
        kwargs = {}
        act = False
        if overall_buy_notional is not None:
            kwargs.update(overall_buy_notional=overall_buy_notional)
            act = True
        if overall_sell_notional is not None:
            kwargs.update(overall_sell_notional=overall_sell_notional)
            act = True
        if portfolio_alerts is not None:
            act = True
        if act:
            with update_portfolio_status_lock:
                portfolio_status_list: List[
                    PortfolioStatusBaseModel] = strat_manager_service_web_client_internal.get_all_portfolio_status_client()
                logging.debug(f"portfolio_status_list count: {len(portfolio_status_list)}")
                if 0 == len(portfolio_status_list):  # no portfolio status set yet - create one
                    kwargs.update(kill_switch=False)
                    kwargs.update(portfolio_alerts=portfolio_alerts)
                    portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
                    portfolio_status: PortfolioStatusBaseModel = \
                        strat_manager_service_web_client_internal.create_portfolio_status_client(portfolio_status)
                    logging.debug(f"created: portfolio_status: {portfolio_status}")
                elif 1 == len(portfolio_status_list):
                    # TODO: we may need to copy non-updated fields form original model
                    # (we should just update original model with new data (patch) and send)
                    kwargs.update(kill_switch=portfolio_status_list[0].kill_switch)
                    kwargs.update(_id=portfolio_status_list[0].id)
                    if 'overall_buy_notional' not in kwargs:
                        kwargs.update(overall_buy_notional=portfolio_status_list[0].overall_buy_notional)
                    if 'overall_sell_notional' not in kwargs:
                        kwargs.update(overall_sell_notional=portfolio_status_list[0].overall_sell_notional)
                    if portfolio_status_list[0].portfolio_alerts is not None \
                            and len(portfolio_status_list[0].portfolio_alerts) > 0:
                        # TODO LAZY : maybe deep copy instead
                        if portfolio_alerts is not None:
                            portfolio_alerts += portfolio_status_list[0].portfolio_alerts
                        else:
                            portfolio_alerts = portfolio_status_list[0].portfolio_alerts
                    kwargs.update(portfolio_alerts=portfolio_alerts)
                    portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
                    strat_manager_service_web_client_internal.put_portfolio_status_client(portfolio_status)
                else:
                    logging.critical(
                        "multiple portfolio limits entries not supported at this time! "
                        "use swagger UI to delete redundant entries from DB and retry - "
                        f"this blocks all alert form reaching UI!! alert being processed: {portfolio_alerts}")
        # else not action required - no action to take - ignore and continue
    except Exception as e:
        logging.critical(
            f"something serious is wrong: update_portfolio_status is throwing as exception!;;; exception: {e}",
            exc_info=True)


def is_service_up():
    try:
        strat_manager_service_web_client_internal.get_all_order_limits_client()
        return True
    except Exception as e:
        logging.error(f"service_up test failed - tried get_all_order_limits_client;;; exception: {e}", exc_info=True)
        return False


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None):
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    rolling_max_order_count = RollingMaxOrderCount(max_order_count=5, order_count_period_seconds=2)
    rolling_max_reject_count = RollingMaxOrderCount(max_order_count=5, order_count_period_seconds=2)

    portfolio_limits_obj = PortfolioLimitsBaseModel(_id=1, max_open_baskets=5, max_open_notional_per_side=7_000,
                                                    max_gross_n_open_notional=12_000,
                                                    rolling_max_order_count=rolling_max_order_count,
                                                    rolling_max_reject_count=rolling_max_reject_count,
                                                    eligible_brokers=eligible_brokers)
    return portfolio_limits_obj


@except_n_log_alert(severity=Severity.Severity_ERROR)
def create_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimitsBaseModel:
    portfolio_limits_obj = get_new_portfolio_limits(eligible_brokers)
    portfolio_limits: PortfolioLimitsBaseModel = strat_manager_service_web_client_internal.create_portfolio_limits_client(
        portfolio_limits_obj)
    logging.info(f"created portfolio_limits;;; (portfolio_limits_obj)")
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
        raise Exception(f"multiple: ({len(portfolio_limits_list)}) portfolio_limits entries not supported at this time!"
                        f" use swagger UI to delete redundant entries: {portfolio_limits_list} from DB and retry")
    else:
        return portfolio_limits_list[0]


def get_new_order_limits():
    ord_limit_obj = OrderLimitsBaseModel(_id=1, max_basis_points=20, max_px_deviation=1, max_px_levels=2,
                                         max_order_qty=10, max_order_notional=9_000)
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


def get_new_strat_limits(eligible_brokers: List[Broker] | None = None) -> StratLimits:
    cancel_rate: CancelRate = CancelRate(max_cancel_rate=20, applicable_period_seconds=0)
    market_trade_volume_participation: MarketTradeVolumeParticipation = \
        MarketTradeVolumeParticipation(max_participation_rate=30,
                                       applicable_period_seconds=180)
    market_depth: OpenInterestParticipation = OpenInterestParticipation(participation_rate=10, depth_levels=3)
    residual_restriction: ResidualRestriction = ResidualRestriction(max_residual=2500, residual_mark_seconds=4)
    strat_limits: StratLimits = StratLimits(max_open_orders_per_side=200,
                                            max_cb_notional=300_000,
                                            max_open_cb_notional=30_000,
                                            max_net_filled_notional=60_000,
                                            max_concentration=1,
                                            limit_up_down_volume_participation_rate=1,
                                            eligible_brokers=eligible_brokers,
                                            cancel_rate=cancel_rate,
                                            market_trade_volume_participation=market_trade_volume_participation,
                                            market_depth=market_depth,
                                            residual_restriction=residual_restriction
                                            )
    return strat_limits
