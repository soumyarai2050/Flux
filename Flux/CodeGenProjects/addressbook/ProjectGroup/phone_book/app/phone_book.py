# python imports
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict
from threading import Lock

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    compress_eligible_broker_positions, except_n_log_alert, get_portfolio_limits, create_portfolio_limits,
    get_internal_web_client, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.model_extensions import (
    BrokerUtil, SecPositionUtil)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_client import (
    EmailBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import ChoreBrief


def retain_broker_and_position_disable(source_brokers: List[BrokerBaseModel],
                                       dest_broker_dict: Dict[str, Broker | BrokerOptional]):
    for broker in source_brokers:
        dest_broker: Broker | None = BrokerUtil.retain_broker_disable(broker, dest_broker_dict)
        if dest_broker is None:
            continue
        dest_sec_position_dict: Dict[str, SecPosition] = BrokerUtil.get_sec_position_dict(dest_broker)
        for sec_position in broker.sec_positions:
            SecPositionUtil.retain_position_disable(sec_position, dest_sec_position_dict)
    return dest_broker_dict


def merge_eligible_brokers_by_pos_type(source_brokers: List[BrokerBaseModel], dest_broker_dict: Dict[str, Broker],
                                       pos_type: PositionType):
    dest_broker_append_list: List[Broker] = list()
    for source_broker in source_brokers:
        # 1. Remove all current pos_type (example PTH) positions from source_broker to overwrite with new positions
        if BrokerUtil.remove_sec_position_by_type(source_broker, pos_type):
            # True return means after removing this pos type, source broker is empty
            continue
        # 2. find this broker in dest_broker_dict and merge source broker sec_positions into it
        dest_broker: Broker | None = dest_broker_dict.get(source_broker.broker)
        if dest_broker is None:
            # add source broker to dest broker append list (list allows duplicates if needed)
            dest_broker_append_list.append(source_broker)
        else:  # this broker has some positions (e.g. PTHs) to fill in
            # update non any position fields from source if available/applicable
            dest_broker.bkr_disable = source_broker.bkr_disable
            # now merge source into dest (dest is posted as updated value)
            BrokerUtil.merge(dest_broker, source_broker)
    merged_eligible_broker_list: List[Broker] = dest_broker_append_list + [*(dest_broker_dict.values())]
    return merged_eligible_broker_list


@except_n_log_alert()
def put_portfolio_limits_eligible_brokers(portfolio_limits: PortfolioLimitsBaseModel,
                                          new_eligible_brokers: List[Broker],
                                          dest_broker_dict: Dict[str, Broker], pos_type: PositionType):
    if portfolio_limits.eligible_brokers is not None:
        dest_broker_dict = retain_broker_and_position_disable(portfolio_limits.eligible_brokers, dest_broker_dict)
        # merge new and old (new_eligible_brokers are all inside dest_broker_dict)
        merged_eligible_broker_list = merge_eligible_brokers_by_pos_type(portfolio_limits.eligible_brokers,
                                                                         dest_broker_dict, pos_type)
    else:
        # since current portfolio_limits.eligible_brokers is None
        merged_eligible_broker_list = new_eligible_brokers

    compressed_eligible_broker_list = compress_eligible_broker_positions(merged_eligible_broker_list)
    portfolio_limits_updated: PortfolioLimitsBaseModel = PortfolioLimitsBaseModel.from_kwargs(
        _id=portfolio_limits.id, max_open_baskets=portfolio_limits.max_open_baskets,
        max_open_notional_per_side=portfolio_limits.max_open_notional_per_side,
        max_gross_n_open_notional=portfolio_limits.max_gross_n_open_notional,
        rolling_max_chore_count=portfolio_limits.rolling_max_chore_count,
        rolling_max_reject_count=portfolio_limits.rolling_max_reject_count,
        eligible_brokers=compressed_eligible_broker_list)  # new_eligible_brokers are all inside dest_broker_dict
    web_client_internal = get_internal_web_client()
    web_client_internal.put_portfolio_limits_client(portfolio_limits_updated)


@except_n_log_alert()
def create_or_update_portfolio_limits_eligible_brokers(eligible_brokers: List[Broker],
                                                       dest_broker_dict: Dict[str, Broker], pos_type: PositionType):
    portfolio_limits: PortfolioLimitsBaseModel | None = get_portfolio_limits()
    if portfolio_limits is None:  # no portfolio limits set yet - create one
        create_portfolio_limits(eligible_brokers)
    else:
        put_portfolio_limits_eligible_brokers(portfolio_limits, eligible_brokers, dest_broker_dict, pos_type)


# deprecated
def update_portfolio_alert(alert_brief: str, alert_details: str | None = None,
                           impacted_chores: List[ChoreBrief] | None = None,
                           severity: Severity = Severity.Severity_ERROR):
    logging.error(f"{alert_brief};;;{alert_details}")


update_portfolio_status_lock: Lock = Lock()


# deprecated
@except_n_log_alert()
def update_strat_alert_by_sec_and_side(sec_id: str, side: Side, alert_brief: str, alert_details: str | None = None,
                                       severity: Severity = Severity.Severity_ERROR):
    pass


# deprecated
@except_n_log_alert()
def block_active_strat_with_restricted_security(sec_id_list: List[str]):
    pass


def get_matching_pair_strat_and_sec_id_source(eqt_ticker: str | None, cb_ticker: str | None):
    sec_id_source: str | None = None
    matching_pair_strat: PairStratBaseModel | None = None
    pair_strat_list: List[PairStratBaseModel] = email_book_service_http_client.get_all_pair_strat_client()
    if pair_strat_list:
        for pair_strat in pair_strat_list:
            if cb_ticker is not None and eqt_ticker is not None:
                if cb_ticker == pair_strat.pair_strat_params.strat_leg1.sec.sec_id and (
                        eqt_ticker == pair_strat.pair_strat_params.strat_leg2.sec.sec_id):
                    sec_id_source = "CB-EQT-pair"
                    matching_pair_strat = pair_strat
                    break
            if cb_ticker is not None:
                if cb_ticker == pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
                    sec_id_source = "CB"
                    matching_pair_strat = pair_strat
                    break
                else:
                    continue
            elif eqt_ticker is not None:
                if eqt_ticker == pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
                    sec_id_source = "EQT"
                    matching_pair_strat = pair_strat
                    break
                else:
                    continue
            # else is not required both were sent None default return will handle this
    return sec_id_source, matching_pair_strat
