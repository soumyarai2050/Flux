import logging
from typing import List
import sys
import os
from pendulum import DateTime
from threading import Lock

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import \
    PortfolioLimits, Broker, Severity, Alert, OrderBrief, PortfolioLimitsBaseModel, PortfolioStatus, \
    PortfolioStatusBaseModel, OrderLimits, OrderLimitsBaseModel, Side, PairStrat
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient

strat_manager_service_web_client_internal = StratManagerServiceWebClient()

update_portfolio_status_lock: Lock = Lock()
update_strat_status_lock: Lock = Lock()


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
                    PortfolioStatus] = strat_manager_service_web_client_internal.get_all_portfolio_status_client()
                logging.debug(f"portfolio_status_list: (portfolio_status_list]")
                if 0 == len(portfolio_status_list):  # no portfolio status set yet - create one
                    kwargs.update(kill_switch=False)
                    kwargs.update(portfolio_alerts=portfolio_alerts)
                    portfolio_status: PortfolioStatusBaseModel = PortfolioStatusBaseModel(**kwargs)
                    portfolio_status: PortfolioStatus = \
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
                        "use swagger UT to delete redundant entries from DB and retry - "
                        f"this blocks all alert form reaching UI!! alert being processed: {portfolio_alerts}")
        # else not action required - no action to take - ignore and continue
    except Exception as e:
        logging.critical(f"something serious is wrong: update portfolio_status is throwing!;;; exception: {e}")


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
                alert: Alert = create_alert(alert_brief, alert_details, None, severity)
                update_portfolio_status(None, None, [alert])
            return result

        return wrapper_function

    return decorator_function


def is_service_up():
    try:
        strat_manager_service_web_client_internal.get_all_order_limits_client()
        return True
    except Exception as e:
        logging.error(f"service_up test failed - tried get_all_order_limits_client;;; exception: {e}")
        return False


def get_new_portfolio_limits(eligible_brokers: List[Broker] | None = None):
    if eligible_brokers is None:
        eligible_brokers = []
    # else using provided value

    portfolio_limits_obj = PortfolioLimitsBaseModel(max_open_baskets=5, max_open_notional_per_side=7_000,
                                                    max_gross_n_open_notional=12_000,
                                                    eligible_brokers=eligible_brokers)
    return portfolio_limits_obj


@except_n_log_alert(severity=Severity.Severity_ERROR)
def create_portfolio_limits(eligible_brokers: List[Broker] | None = None) -> PortfolioLimits:
    portfolio_limits_obj = get_new_portfolio_limits(eligible_brokers)
    portfolio_limits: PortfolioLimits = strat_manager_service_web_client_internal.create_portfolio_limits_client(
        portfolio_limits_obj)
    logging.info(f"created portfolio_limits: (portfolio_limits_obj)")
    return portfolio_limits


@except_n_log_alert(severity=Severity.Severity_ERROR)
def get_portfolio_limits() -> PortfolioLimits | None:
    portfolio_limits_list: List[
        PortfolioLimits] = strat_manager_service_web_client_internal.get_all_portfolio_limits_client()
    if portfolio_limits_list is None or len(portfolio_limits_list) <= 0:
        return None
    elif len(portfolio_limits_list) > 1:
        # portfolio limits: PortfolioLimits = portfolio_limits_list[0]
        # for portfolio limits entry in portfolio limits list:
        #   if portfolio limits entry.id < portfolio_limits.id:
        #          portfolio_limits = portfolio_limits_entry
        # logging.debug(f"portfolio_limit_list: {portfolio_limits_list}, selected portfolio_limits: {portfolio_limits}")
        # return portfolio limits
        raise Exception(f"multiple: ({len(portfolio_limits_list)}) portfolio limits entries not supported at this time!"
                        f" use swagger UI to delete redundant entries: {portfolio_limits_list} from DB and retry")
    else:
        return portfolio_limits_list[0]


def get_new_order_limits():
    ord_limit_obj = OrderLimitsBaseModel(max_basis_points=20, max_px_deviation=1, max_px_levels=2,
                                         max_order_qty=10, max_order_notional=9_000)
    return ord_limit_obj


def get_order_limits() -> OrderLimits | None:
    order_limits_list: List[
        OrderLimits] = strat_manager_service_web_client_internal.get_all_order_limits_client()
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
