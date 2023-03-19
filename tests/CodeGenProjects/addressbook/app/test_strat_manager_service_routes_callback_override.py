# Before running this test case, keep in mind to put DB_NAME env var to
# - "market_data_test_fixture" for market_data_project
# - "addressbook_test" for pair_strat_project
import pytest
from pendulum import local_timezone
import time
import copy

from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import get_new_order_limits, \
    get_new_portfolio_limits
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import *
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from FluxPythonUtils.scripts.utility_functions import drop_mongo_collections, clean_mongo_collections
from Flux.CodeGenProjects.addressbook.app.static_data import SecurityRecordManager


strat_manager_service_web_client: StratManagerServiceWebClient = StratManagerServiceWebClient()
market_data_web_client: MarketDataServiceWebClient = MarketDataServiceWebClient()
static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)

def position_fixture():
    position_json = {
              "_id": Position.next_id(),
              "pos_disable": False,
              "type": PositionType.PTH,
              "available_size": 100,
              "allocated_size": 90,
              "consumed_size": 60,
              "acquire_cost": 160,
              "incurred_cost": 140,
              "carry_cost": 120,
              "priority": 60,
              "premium_percentage": 20
            }
    position = Position(**position_json)
    return position


def sec_position_fixture(sec_id: str):
    sec_position_json = {
          "_id": SecPosition.next_id(),
          "security": {
            "sec_id": sec_id,
            "sec_type": "SEC_TYPE_UNSPECIFIED"
          },
          "positions": [
              position_fixture(),
              position_fixture()
          ]
        }
    sec_position = SecPosition(**sec_position_json)
    return sec_position


def broker_fixture():
    sec_position_1 = sec_position_fixture("CB_Sec_1")
    sec_position_2 = sec_position_fixture("EQT_Sec_1")

    broker_json = {
          "bkr_disable": False,
          "sec_positions": [
            sec_position_1,
            sec_position_2
          ],
          "broker": "Bkr1",
          "bkr_priority": 5
        }
    broker1 = BrokerOptional(**broker_json)
    return broker1


def test_add_brokers_to_portfolio_limits():
    """Adding Broker entries in portfolio limits"""
    broker = broker_fixture()

    portfolio_limits_basemodel = PortfolioLimitsBaseModel(_id=1, eligible_brokers=[broker])
    strat_manager_service_web_client.patch_portfolio_limits_client(portfolio_limits_basemodel)

    stored_portfolio_limits_ = strat_manager_service_web_client.get_portfolio_limits_client(1)
    assert broker in stored_portfolio_limits_.eligible_brokers


def place_order(order_journal_obj: OrderJournalBaseModel):
    stored_order_journal_obj = \
        strat_manager_service_web_client.create_order_journal_client(order_journal_obj)
    return stored_order_journal_obj


def place_fill(fills_journal_obj: FillsJournalBaseModel):
    stored_fills_journal_obj = \
        strat_manager_service_web_client.create_fills_journal_client(fills_journal_obj)
    return stored_fills_journal_obj


def update_expected_strat_brief_for_buy(loop_count: int, expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                        expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                        expected_strat_limits: StratLimits,
                                        expected_strat_brief_obj: StratBriefBaseModel,
                                        date_time_for_cmp: DateTime):
    open_qty = expected_symbol_side_snapshot.total_qty - expected_symbol_side_snapshot.total_filled_qty - \
               expected_symbol_side_snapshot.total_cxled_qty
    open_notional = open_qty * expected_order_snapshot_obj.order_brief.px
    expected_strat_brief_obj.pair_buy_side_trading_brief.open_qty = open_qty
    expected_strat_brief_obj.pair_buy_side_trading_brief.open_notional = open_notional
    expected_strat_brief_obj.pair_buy_side_trading_brief.all_bkr_cxlled_qty = \
        expected_symbol_side_snapshot.total_cxled_qty
    if expected_order_snapshot_obj.order_status == OrderStatusType.OE_ACKED:
        expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_orders = 4
    else:
        expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_orders = 5
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_notional = \
        expected_strat_limits.max_cb_notional - expected_symbol_side_snapshot.total_fill_notional - open_notional
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_open_notional = \
        expected_strat_limits.max_open_cb_notional - open_notional
    total_security_size: int = \
        static_data.get_security_float_from_ticker(expected_order_snapshot_obj.order_brief.security.sec_id)
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_concentration = \
        (total_security_size / 100 * expected_strat_limits.max_concentration) - (open_qty + expected_symbol_side_snapshot.total_filled_qty)
    # currently assuming applicable_period_seconds = 0
    expected_strat_brief_obj.pair_buy_side_trading_brief.participation_period_order_qty_sum = expected_symbol_side_snapshot.total_qty
    expected_strat_brief_obj.pair_buy_side_trading_brief.consumable_cxl_qty = \
        (((open_qty + expected_symbol_side_snapshot.total_filled_qty +
           expected_symbol_side_snapshot.total_cxled_qty) / 100) * expected_strat_limits.cancel_rate.max_cancel_rate) - \
        expected_symbol_side_snapshot.total_cxled_qty
    expected_strat_brief_obj.pair_buy_side_trading_brief.indicative_consumable_participation_qty = \
        (15 * 40) - expected_strat_brief_obj.pair_buy_side_trading_brief.participation_period_order_qty_sum
    expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty = 40 * (loop_count-1)
    expected_strat_brief_obj.pair_buy_side_trading_brief.indicative_consumable_residual = \
        expected_strat_limits.residual_restriction.max_residual - \
        ((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * 116) - (0 * 116))
    expected_strat_brief_obj.pair_buy_side_trading_brief.last_update_date_time = date_time_for_cmp


def update_expected_strat_brief_for_sell(loop_count: int, total_loop_count: int,
                                         expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                         expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                         expected_strat_limits: StratLimits,
                                         expected_strat_brief_obj: StratBriefBaseModel,
                                         date_time_for_cmp: DateTime):
    open_qty = expected_symbol_side_snapshot.total_qty - expected_symbol_side_snapshot.total_filled_qty - \
               expected_symbol_side_snapshot.total_cxled_qty
    open_notional = open_qty * expected_order_snapshot_obj.order_brief.px
    expected_strat_brief_obj.pair_sell_side_trading_brief.open_qty = open_qty
    expected_strat_brief_obj.pair_sell_side_trading_brief.open_notional = open_notional
    expected_strat_brief_obj.pair_sell_side_trading_brief.all_bkr_cxlled_qty = \
        expected_symbol_side_snapshot.total_cxled_qty
    if expected_order_snapshot_obj.order_status == OrderStatusType.OE_ACKED:
        expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_orders = 4
    else:
        expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_orders = 5
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_notional = \
        expected_strat_limits.max_cb_notional - expected_symbol_side_snapshot.total_fill_notional - open_notional
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_open_notional = \
        expected_strat_limits.max_open_cb_notional - open_notional
    total_security_size: int = \
        static_data.get_security_float_from_ticker(expected_order_snapshot_obj.order_brief.security.sec_id)
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_concentration = \
        (total_security_size / 100 * expected_strat_limits.max_concentration) - (open_qty + expected_symbol_side_snapshot.total_filled_qty)
    expected_strat_brief_obj.pair_sell_side_trading_brief.participation_period_order_qty_sum = expected_symbol_side_snapshot.total_qty
    expected_strat_brief_obj.pair_sell_side_trading_brief.consumable_cxl_qty = \
        (((open_qty + expected_symbol_side_snapshot.total_filled_qty +
           expected_symbol_side_snapshot.total_cxled_qty) / 100) * expected_strat_limits.cancel_rate.max_cancel_rate) - \
        expected_symbol_side_snapshot.total_cxled_qty
    expected_strat_brief_obj.pair_sell_side_trading_brief.indicative_consumable_participation_qty = \
        (15 * 40) - expected_strat_brief_obj.pair_sell_side_trading_brief.participation_period_order_qty_sum
    expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty = 40 * (loop_count-1)
    expected_strat_brief_obj.pair_sell_side_trading_brief.indicative_consumable_residual = \
        expected_strat_limits.residual_restriction.max_residual - \
        ((expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * 116) - ((40 * total_loop_count) * 116))
    expected_strat_brief_obj.pair_sell_side_trading_brief.last_update_date_time = date_time_for_cmp


def check_placed_buy_order_computes(loop_count: int, expected_order_id: str, symbol: str,
                                    buy_placed_order_journal: OrderJournalBaseModel,
                                    expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                    expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                    expected_pair_strat: PairStratBaseModel,
                                    expected_strat_limits: StratLimits,
                                    expected_strat_status: StratStatus,
                                    expected_strat_brief_obj: StratBriefBaseModel,
                                    expected_portfolio_status: PortfolioStatusBaseModel):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after order is triggered
    """
    order_journal_obj_list = strat_manager_service_web_client.get_all_order_journal_client()

    assert buy_placed_order_journal in order_journal_obj_list

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = 100
    expected_order_snapshot_obj.order_brief.qty = 90
    expected_order_snapshot_obj.order_brief.order_notional = 9000
    expected_order_snapshot_obj.order_status = "OE_UNACK"
    expected_order_snapshot_obj.last_update_date_time = buy_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = buy_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.order_brief.text.extend(buy_placed_order_journal.order.text)

    order_snapshot_list = strat_manager_service_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None
    found_count = 0
    for order_snapshot in order_snapshot_list:
        if order_snapshot == expected_order_snapshot_obj:
            found_count += 1
    assert found_count == 1, f"Couldn't find expected_order_snapshot {expected_order_snapshot_obj} in " \
                             f"{order_snapshot_list}"

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = 100
    expected_symbol_side_snapshot.total_qty = 90 * loop_count
    expected_symbol_side_snapshot.last_update_date_time = buy_placed_order_journal.order_event_date_time
    expected_symbol_side_snapshot.order_create_count = loop_count
    if loop_count > 1:
        expected_symbol_side_snapshot.total_filled_qty = 50 * (loop_count - 1)
        expected_symbol_side_snapshot.total_fill_notional = 4500 * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_qty = 40 * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = 4000 * (loop_count - 1)
        expected_symbol_side_snapshot.avg_fill_px = 90
        expected_symbol_side_snapshot.last_update_fill_qty = 50
        expected_symbol_side_snapshot.last_update_fill_px = 90
        expected_symbol_side_snapshot.avg_cxled_px = 100

    symbol_side_snapshot_list = strat_manager_service_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list, f"{expected_symbol_side_snapshot} not found in " \
                                                                       f"{symbol_side_snapshot_list}"

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                        expected_strat_limits, expected_strat_brief_obj,
                                        buy_placed_order_journal.order_event_date_time)

    strat_brief_list = strat_manager_service_web_client.get_strat_brief_from_symbol_query_client([symbol])
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        # Since sell side of strat_brief is not updated till sell cycle
        strat_brief.pair_sell_side_trading_brief = expected_strat_brief_obj.pair_sell_side_trading_brief
    assert expected_strat_brief_obj in strat_brief_list, f"Couldn't find expected strat_brief {expected_strat_brief_obj} in " \
                                                         f"list {strat_brief_list}"

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = 90 * loop_count
    expected_strat_status.total_order_qty = 90 * loop_count
    expected_strat_status.total_open_buy_qty = 90
    expected_strat_status.avg_open_buy_px = 100
    expected_strat_status.total_open_buy_notional = 9000
    expected_strat_status.total_open_exposure = 9000
    expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg2.sec,
                                              residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_fill_buy_px = 90
        expected_strat_status.total_fill_buy_qty = 50 * (loop_count - 1)
        expected_strat_status.total_fill_buy_notional = 4500 * (loop_count - 1)
        expected_strat_status.total_fill_exposure = 4500 * (loop_count - 1)
        expected_strat_status.avg_cxl_buy_px = 100
        expected_strat_status.total_cxl_buy_qty = 40 * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = 4000 * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = 4000 * (loop_count - 1)
        residual_notional = abs((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty*116) - \
                            (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty*116))
        expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg1.sec,
                                                  residual_notional=residual_notional)

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.last_active_date_time = None
        pair_strat.frequency = None
    assert expected_pair_strat in pair_strat_list, f"{expected_pair_strat} not found in {pair_strat_list}"

    # # expected portfolio_status
    # expected_portfolio_status.overall_buy_notional = \
    #     ((9000 * loop_count) - (500*(loop_count-1)) - (4000*(loop_count-1))) * symbol_pair_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 0
    # if loop_count > 1:
    #     expected_portfolio_status.overall_buy_fill_notional = (4500 * (loop_count-1)) * symbol_pair_count
    #
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #
    # assert expected_portfolio_status in portfolio_status_list


def placed_buy_order_ack_receive(loop_count: int, expected_order_id: str, buy_order_placed_date_time: DateTime,
                                 expected_order_journal: OrderJournalBaseModel,
                                 expected_order_snapshot_obj: OrderSnapshotBaseModel):
    """Checking after order's ACK status is received"""
    order_journal_obj_list = strat_manager_service_web_client.get_all_order_journal_client()

    assert expected_order_journal in order_journal_obj_list

    # Checking order_snapshot
    expected_order_snapshot_obj.order_status = "OE_ACKED"
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = 100
    expected_order_snapshot_obj.order_brief.qty = 90
    expected_order_snapshot_obj.order_brief.order_notional = 9000
    expected_order_snapshot_obj.last_update_date_time = expected_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = buy_order_placed_date_time

    order_snapshot_list = strat_manager_service_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None

    assert expected_order_snapshot_obj in order_snapshot_list


def check_fill_receive_for_placed_buy_order(loop_count: int, expected_order_id: str,
                                            buy_order_placed_date_time: DateTime, symbol: str,
                                            buy_fill_journal: FillsJournalBaseModel,
                                            expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                            expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                            expected_pair_strat: PairStratBaseModel,
                                            expected_strat_limits: StratLimits,
                                            expected_strat_status: StratStatus,
                                            expected_strat_brief_obj: StratBriefBaseModel,
                                            expected_portfolio_status: PortfolioStatusBaseModel):
    """
    Checking resulted changes in OrderJournal, OrderSnapshot, SymbolSideSnapshot, PairStrat,
    StratBrief and PortfolioStatus after fill is received
    """
    fill_journal_obj_list = strat_manager_service_web_client.get_all_fills_journal_client()
    assert buy_fill_journal in fill_journal_obj_list

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = 100
    expected_order_snapshot_obj.order_brief.qty = 90
    expected_order_snapshot_obj.order_brief.order_notional = 9000
    expected_order_snapshot_obj.filled_qty = 50
    expected_order_snapshot_obj.avg_fill_px = 90
    expected_order_snapshot_obj.fill_notional = 4500
    expected_order_snapshot_obj.last_update_fill_qty = 50
    expected_order_snapshot_obj.last_update_fill_px = 90
    expected_order_snapshot_obj.last_update_date_time = buy_fill_journal.fill_date_time
    expected_order_snapshot_obj.create_date_time = buy_order_placed_date_time
    expected_order_snapshot_obj.order_status = "OE_ACKED"

    order_snapshot_list = strat_manager_service_web_client.get_all_order_snapshot_client()
    # removing below field from received_order_snapshot_list for comparison
    for symbol_side_snapshot in order_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_order_snapshot_obj in order_snapshot_list

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = 100
    expected_symbol_side_snapshot.total_qty = 90 * loop_count
    expected_symbol_side_snapshot.last_update_date_time = buy_fill_journal.fill_date_time
    expected_symbol_side_snapshot.order_create_count = 1 * loop_count
    expected_symbol_side_snapshot.total_filled_qty = 50 * loop_count
    expected_symbol_side_snapshot.avg_fill_px = 90
    expected_symbol_side_snapshot.total_fill_notional = 4500 * loop_count
    expected_symbol_side_snapshot.last_update_fill_qty = 50
    expected_symbol_side_snapshot.last_update_fill_px = 90
    if loop_count > 1:
        expected_symbol_side_snapshot.total_cxled_qty = 40 * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = 4000 * (loop_count - 1)
        expected_symbol_side_snapshot.avg_cxled_px = 100

    symbol_side_snapshot_list = strat_manager_service_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list

    # Checking start_brief
    update_expected_strat_brief_for_buy(loop_count, expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                        expected_strat_limits, expected_strat_brief_obj,
                                        buy_fill_journal.fill_date_time)

    strat_brief_list = strat_manager_service_web_client.get_strat_brief_from_symbol_query_client([symbol])
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        # Since sell side of strat_brief is not updated till sell cycle
        strat_brief.pair_sell_side_trading_brief = expected_strat_brief_obj.pair_sell_side_trading_brief
    assert expected_strat_brief_obj in strat_brief_list

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = 90 * loop_count
    expected_strat_status.total_order_qty = 90 * loop_count
    expected_strat_status.total_open_buy_qty = 40
    expected_strat_status.avg_open_buy_px = 100
    expected_strat_status.total_open_buy_notional = 4000
    expected_strat_status.total_open_exposure = 4000
    expected_strat_status.total_fill_buy_qty = 50 * loop_count
    expected_strat_status.avg_fill_buy_px = 90
    expected_strat_status.total_fill_buy_notional = 4500 * loop_count
    expected_strat_status.total_fill_exposure = 4500 * loop_count
    expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg2.sec,
                                              residual_notional=0)
    if loop_count > 1:
        expected_strat_status.avg_cxl_buy_px = 100
        expected_strat_status.total_cxl_buy_qty = 40 * (loop_count - 1)
        expected_strat_status.total_cxl_buy_notional = 4000 * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = 4000 * (loop_count - 1)
        residual_notional = abs((expected_strat_brief_obj.pair_buy_side_trading_brief.residual_qty * 116) - \
                                (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * 116))
        expected_strat_status.residual = Residual(security=expected_pair_strat.pair_strat_params.strat_leg1.sec,
                                                  residual_notional=residual_notional)
    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional
    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.frequency = None
        pair_strat.last_active_date_time = None
    assert expected_pair_strat in pair_strat_list

    # expected portfolio_status
    # expected_portfolio_status.overall_buy_notional = (9000 * loop_count) - (500*loop_count) - (4000*(loop_count-1))
    # expected_portfolio_status.overall_buy_fill_notional = 4500 * loop_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 0
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #     # portfolio_status.current_period_available_buy_order_count = 0
    #     # portfolio_status.current_period_available_sell_order_count = 0
    # assert expected_portfolio_status in portfolio_status_list


def check_placed_sell_order_computes(loop_count: int, total_loop_count: int, expected_order_id: str,
                                     symbol: str, sell_placed_order_journal: OrderJournalBaseModel,
                                     expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                     expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                     expected_pair_strat: PairStratBaseModel,
                                     expected_strat_limits: StratLimits,
                                     expected_strat_status: StratStatus,
                                     expected_strat_brief_obj: StratBriefBaseModel,
                                     expected_portfolio_status: PortfolioStatusBaseModel):
    order_journal_obj_list = strat_manager_service_web_client.get_all_order_journal_client()

    assert sell_placed_order_journal in order_journal_obj_list

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = 110
    expected_order_snapshot_obj.order_brief.qty = 70
    expected_order_snapshot_obj.order_brief.order_notional = 7700
    expected_order_snapshot_obj.order_status = "OE_UNACK"
    expected_order_snapshot_obj.last_update_date_time = sell_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = sell_placed_order_journal.order_event_date_time
    expected_order_snapshot_obj.order_brief.text.extend(sell_placed_order_journal.order.text)

    order_snapshot_list = strat_manager_service_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None
    assert expected_order_snapshot_obj in order_snapshot_list

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = 110
    expected_symbol_side_snapshot.total_qty = 70 * loop_count
    expected_symbol_side_snapshot.last_update_date_time = sell_placed_order_journal.order_event_date_time
    expected_symbol_side_snapshot.order_create_count = loop_count
    if loop_count > 1:
        expected_symbol_side_snapshot.total_filled_qty = 30 * (loop_count - 1)
        expected_symbol_side_snapshot.total_fill_notional = 3600 * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_qty = 40 * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = 4400 * (loop_count - 1)
        expected_symbol_side_snapshot.avg_fill_px = 120
        expected_symbol_side_snapshot.last_update_fill_qty = 30
        expected_symbol_side_snapshot.last_update_fill_px = 120
        expected_symbol_side_snapshot.avg_cxled_px = 110

    symbol_side_snapshot_list = strat_manager_service_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, total_loop_count, expected_order_snapshot_obj, expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_placed_order_journal.order_event_date_time)

    strat_brief_list = strat_manager_service_web_client.get_strat_brief_from_symbol_query_client([symbol])
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        # Since buy side of strat_brief is already checked
        strat_brief.pair_buy_side_trading_brief = expected_strat_brief_obj.pair_buy_side_trading_brief
    for strat_brief in strat_brief_list:
        if strat_brief.pair_sell_side_trading_brief == expected_strat_brief_obj.pair_sell_side_trading_brief:
            assert True
            break
    else:
        assert False, f"{expected_strat_brief_obj.pair_sell_side_trading_brief} not found in {strat_brief_list}"

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = 90 * total_loop_count
    expected_strat_status.total_sell_qty = 70 * loop_count
    expected_strat_status.total_order_qty = (90 * total_loop_count) + (70 * loop_count)
    expected_strat_status.total_open_sell_qty = 70
    expected_strat_status.avg_open_sell_px = 110
    expected_strat_status.total_open_sell_notional = 7700
    expected_strat_status.total_open_exposure = -7700
    expected_strat_status.avg_fill_buy_px = 90
    expected_strat_status.total_fill_buy_qty = 50 * total_loop_count
    expected_strat_status.total_fill_buy_notional = 4500 * total_loop_count
    expected_strat_status.total_fill_exposure = 4500 * total_loop_count
    expected_strat_status.avg_cxl_buy_px = 100
    expected_strat_status.total_cxl_buy_qty = 40 * total_loop_count
    expected_strat_status.total_cxl_buy_notional = 4000 * total_loop_count
    expected_strat_status.total_cxl_exposure = 4000 * total_loop_count
    residual_notional = abs(((40*total_loop_count) * 116) -
                            (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * 116))
    if ((40*total_loop_count) * 116) > (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * 116):
        residual_security = strat_brief.pair_buy_side_trading_brief.security
    else:
        residual_security = strat_brief.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=residual_security, residual_notional=residual_notional)
    if loop_count > 1:
        expected_strat_status.avg_fill_sell_px = 120
        expected_strat_status.total_fill_sell_qty = 30 * (loop_count - 1)
        expected_strat_status.total_fill_sell_notional = 3600 * (loop_count - 1)
        expected_strat_status.total_fill_exposure = (4500 * total_loop_count) - (3600 * (loop_count - 1))
        expected_strat_status.avg_cxl_sell_px = 110
        expected_strat_status.total_cxl_sell_qty = 40 * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = 4400 * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = (4000 * total_loop_count) - (4400 * (loop_count - 1))

    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional

    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.last_active_date_time = None
        pair_strat.frequency = None
    assert expected_pair_strat in pair_strat_list

    # expected portfolio_status
    # expected_portfolio_status.overall_sell_notional = \
    #     (7700 * loop_count) + (300*(loop_count-1)) - (4400 * (loop_count-1))
    # expected_portfolio_status.overall_sell_fill_notional = 3600 * (loop_count - 1)
    # expected_portfolio_status.overall_buy_notional = \
    #     (9000 * total_loop_count) - (500*total_loop_count) - (4000*total_loop_count)
    # expected_portfolio_status.overall_buy_fill_notional = 4500 * total_loop_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 4
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #     # portfolio_status.current_period_available_buy_order_count = 4
    #     # portfolio_status.current_period_available_sell_order_count = 4
    # assert expected_portfolio_status in portfolio_status_list


def placed_sell_order_ack_receive(loop_count: int, expected_order_id: str, sell_order_placed_date_time: DateTime,
                                  total_loop_count: int, expected_order_journal: OrderJournalBaseModel,
                                  expected_order_snapshot_obj: OrderSnapshotBaseModel):
    """Checking after order's ACK status is received"""
    order_journal_obj_list = strat_manager_service_web_client.get_all_order_journal_client()

    assert expected_order_journal in order_journal_obj_list

    # Checking order_snapshot
    expected_order_snapshot_obj.order_status = "OE_ACKED"
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = 110
    expected_order_snapshot_obj.order_brief.qty = 70
    expected_order_snapshot_obj.order_brief.order_notional = 7700
    expected_order_snapshot_obj.last_update_date_time = expected_order_journal.order_event_date_time
    expected_order_snapshot_obj.create_date_time = sell_order_placed_date_time

    order_snapshot_list = strat_manager_service_web_client.get_all_order_snapshot_client()
    # updating below field from received_order_snapshot_list for comparison
    for order_snapshot in order_snapshot_list:
        order_snapshot.id = None

    assert expected_order_snapshot_obj in order_snapshot_list


def check_fill_receive_for_placed_sell_order(loop_count: int, total_loop_count: int, expected_order_id: str,
                                             sell_order_placed_date_time: DateTime, symbol: str,
                                             sell_fill_journal: FillsJournalBaseModel,
                                             expected_order_snapshot_obj: OrderSnapshotBaseModel,
                                             expected_symbol_side_snapshot: SymbolSideSnapshotBaseModel,
                                             expected_pair_strat: PairStratBaseModel,
                                             expected_strat_limits: StratLimits,
                                             expected_strat_status: StratStatus,
                                             expected_strat_brief_obj: StratBriefBaseModel,
                                             expected_portfolio_status: PortfolioStatusBaseModel):

    fill_journal_obj_list = strat_manager_service_web_client.get_all_fills_journal_client()
    assert sell_fill_journal in fill_journal_obj_list

    # Checking order_snapshot
    expected_order_snapshot_obj.order_brief.order_id = expected_order_id
    expected_order_snapshot_obj.order_brief.px = 110
    expected_order_snapshot_obj.order_brief.qty = 70
    expected_order_snapshot_obj.order_brief.order_notional = 7700
    expected_order_snapshot_obj.filled_qty = 30
    expected_order_snapshot_obj.avg_fill_px = 120
    expected_order_snapshot_obj.fill_notional = 3600
    expected_order_snapshot_obj.last_update_fill_qty = 30
    expected_order_snapshot_obj.last_update_fill_px = 120
    expected_order_snapshot_obj.last_update_date_time = sell_fill_journal.fill_date_time
    expected_order_snapshot_obj.create_date_time = sell_order_placed_date_time
    expected_order_snapshot_obj.order_status = "OE_ACKED"

    order_snapshot_list = strat_manager_service_web_client.get_all_order_snapshot_client()
    # removing below field from received_order_snapshot_list for comparison
    for symbol_side_snapshot in order_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_order_snapshot_obj in order_snapshot_list

    # Checking symbol_side_snapshot
    expected_symbol_side_snapshot.avg_px = 110
    expected_symbol_side_snapshot.total_qty = 70 * loop_count
    expected_symbol_side_snapshot.last_update_date_time = expected_order_snapshot_obj.last_update_date_time
    expected_symbol_side_snapshot.order_create_count = 1 * loop_count
    expected_symbol_side_snapshot.total_filled_qty = 30 * loop_count
    expected_symbol_side_snapshot.avg_fill_px = 120
    expected_symbol_side_snapshot.total_fill_notional = 3600 * loop_count
    expected_symbol_side_snapshot.last_update_fill_qty = 30
    expected_symbol_side_snapshot.last_update_fill_px = 120
    if loop_count > 1:
        expected_symbol_side_snapshot.total_cxled_qty = 40 * (loop_count - 1)
        expected_symbol_side_snapshot.total_cxled_notional = 4400 * (loop_count - 1)
        expected_symbol_side_snapshot.avg_cxled_px = 110

    symbol_side_snapshot_list = strat_manager_service_web_client.get_all_symbol_side_snapshot_client()
    # removing id field from received obj list for comparison
    for symbol_side_snapshot in symbol_side_snapshot_list:
        symbol_side_snapshot.id = None
    assert expected_symbol_side_snapshot in symbol_side_snapshot_list

    # Checking pair_strat
    expected_pair_strat.last_active_date_time = None
    expected_pair_strat.frequency = None
    expected_pair_strat.strat_limits = expected_strat_limits
    expected_strat_status.total_buy_qty = 90 * total_loop_count
    expected_strat_status.total_sell_qty = 70 * loop_count
    expected_strat_status.total_order_qty = (90 * total_loop_count) + (70 * loop_count)
    expected_strat_status.avg_open_sell_px = 110
    expected_strat_status.total_open_sell_qty = 40
    expected_strat_status.total_open_sell_notional = 4400
    expected_strat_status.total_open_exposure = -4400
    expected_strat_status.total_fill_buy_qty = 50 * total_loop_count
    expected_strat_status.total_fill_sell_qty = 30 * loop_count
    expected_strat_status.avg_fill_buy_px = 90
    expected_strat_status.avg_fill_sell_px = 120
    expected_strat_status.total_fill_buy_notional = 4500 * total_loop_count
    expected_strat_status.total_fill_sell_notional = 3600 * loop_count
    expected_strat_status.total_fill_exposure = (4500 * total_loop_count) - (3600 * loop_count)
    expected_strat_status.avg_cxl_buy_px = 100
    expected_strat_status.total_cxl_buy_qty = 40 * total_loop_count
    expected_strat_status.total_cxl_buy_notional = 4000 * total_loop_count
    expected_strat_status.total_cxl_exposure = 4000 * total_loop_count
    residual_notional = abs(((40*total_loop_count) * 116) - (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * 116))
    if ((40*total_loop_count) * 116) > (expected_strat_brief_obj.pair_sell_side_trading_brief.residual_qty * 116):
        residual_security = expected_strat_brief_obj.pair_buy_side_trading_brief.security
    else:
        residual_security = expected_strat_brief_obj.pair_sell_side_trading_brief.security
    expected_strat_status.residual = Residual(security=residual_security, residual_notional=residual_notional)
    if loop_count > 1:
        expected_strat_status.avg_cxl_sell_px = 110
        expected_strat_status.total_cxl_sell_qty = 40 * (loop_count - 1)
        expected_strat_status.total_cxl_sell_notional = 4400 * (loop_count - 1)
        expected_strat_status.total_cxl_exposure = (4000 * total_loop_count) - (4400 * (loop_count - 1))
    if expected_strat_status.total_fill_buy_notional < expected_strat_status.total_fill_sell_notional:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_buy_notional
    else:
        expected_strat_status.balance_notional = \
            expected_strat_limits.max_cb_notional - expected_strat_status.total_fill_sell_notional
    expected_pair_strat.strat_status = expected_strat_status

    pair_strat_list = strat_manager_service_web_client.get_all_pair_strat_client()
    # removing id field from received obj list for comparison
    for pair_strat in pair_strat_list:
        pair_strat.id = None
        pair_strat.frequency = None
        pair_strat.last_active_date_time = None
    assert expected_pair_strat in pair_strat_list

    # Checking start_brief
    update_expected_strat_brief_for_sell(loop_count, total_loop_count, expected_order_snapshot_obj,
                                         expected_symbol_side_snapshot,
                                         expected_strat_limits, expected_strat_brief_obj,
                                         sell_fill_journal.fill_date_time)

    strat_brief_list = strat_manager_service_web_client.get_strat_brief_from_symbol_query_client([symbol])
    # removing id field from received obj list for comparison
    for strat_brief in strat_brief_list:
        strat_brief.id = None
        # Since buy side of strat_brief is already checked
        strat_brief.pair_buy_side_trading_brief = expected_strat_brief_obj.pair_buy_side_trading_brief
    for strat_brief in strat_brief_list:
        if strat_brief.pair_sell_side_trading_brief == expected_strat_brief_obj.pair_sell_side_trading_brief:
            assert True
            break
    else:
        assert False

    # # expected portfolio_status
    # expected_portfolio_status.overall_sell_notional = (7700 * loop_count) + (300*loop_count) - (4400 * (loop_count-1))
    # expected_portfolio_status.overall_sell_fill_notional = 3600 * loop_count
    # # computes from last buy test execution
    # expected_portfolio_status.overall_buy_notional = \
    #     (9000 * total_loop_count) - (500 * total_loop_count) - (4000 * total_loop_count)
    # expected_portfolio_status.overall_buy_fill_notional = 4500 * total_loop_count
    # expected_portfolio_status.current_period_available_buy_order_count = 4
    # expected_portfolio_status.current_period_available_sell_order_count = 4
    #
    # portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    # for portfolio_status in portfolio_status_list:
    #     portfolio_status.id = None
    #     portfolio_status.portfolio_alerts = []
    #     # portfolio_status.current_period_available_buy_order_count = 0
    #     # portfolio_status.current_period_available_sell_order_count = 0
    # assert expected_portfolio_status in portfolio_status_list


class TopOfBookSide(StrEnum):
    Bid = auto()
    Ask = auto()


def _create_tob(buy_symbol: str, sell_symbol: str, top_of_book_json_list: List[Dict]):
    buy_stored_tob: TopOfBookBaseModel | None = None

    # For place order non-triggered run
    for index, top_of_book_json in enumerate(top_of_book_json_list):
        top_of_book_basemodel = TopOfBookBaseModel(**top_of_book_json)
        if index == 0:
            top_of_book_basemodel.symbol = buy_symbol
        else:
            top_of_book_basemodel.symbol = sell_symbol
        top_of_book_basemodel.bid_quote.px -= 10
        top_of_book_basemodel.last_update_date_time = DateTime.utcnow()
        stored_top_of_book_basemodel = \
            market_data_web_client.create_top_of_book_client(top_of_book_basemodel)
        top_of_book_basemodel.id = stored_top_of_book_basemodel.id
        top_of_book_basemodel.last_update_date_time = stored_top_of_book_basemodel.last_update_date_time
        for market_trade_vol in stored_top_of_book_basemodel.market_trade_volume:
            market_trade_vol.id = None
        for market_trade_vol in top_of_book_basemodel.market_trade_volume:
            market_trade_vol.id = None
        assert stored_top_of_book_basemodel == top_of_book_basemodel
        if stored_top_of_book_basemodel.symbol == buy_symbol:
            buy_stored_tob = stored_top_of_book_basemodel

    # For place order trigger run
    buy_top_of_book_basemodel = TopOfBookBaseModel(_id=buy_stored_tob.id)
    buy_top_of_book_basemodel.symbol = buy_symbol
    buy_top_of_book_basemodel.bid_quote = Quote()
    buy_top_of_book_basemodel.bid_quote.px = buy_stored_tob.bid_quote.px + 10
    # update_date_time = DateTime.now(local_timezone())
    update_date_time = DateTime.utcnow()
    buy_top_of_book_basemodel.bid_quote.last_update_date_time = update_date_time
    buy_top_of_book_basemodel.last_update_date_time = update_date_time
    # top_of_book_basemodel.total_trading_security_size = 200
    updated_tob = market_data_web_client.patch_top_of_book_client(buy_top_of_book_basemodel)
    for market_trade_vol in updated_tob.market_trade_volume:
        market_trade_vol.id = None
    assert updated_tob.bid_quote.px == buy_top_of_book_basemodel.bid_quote.px


def _update_tob(stored_obj: TopOfBookBaseModel, px: int | float, side: Side):
    tob_obj = TopOfBookBaseModel(_id=stored_obj.id)
    # update_date_time = DateTime.now(local_timezone())
    update_date_time = DateTime.utcnow()
    if Side.BUY == side:
        tob_obj.bid_quote = Quote()
        tob_obj.bid_quote.px = px
        tob_obj.bid_quote.last_update_date_time = update_date_time
        tob_obj.last_update_date_time = update_date_time
    else:
        tob_obj.ask_quote = Quote()
        tob_obj.ask_quote.px = px
        tob_obj.ask_quote.last_update_date_time = update_date_time
        tob_obj.last_update_date_time = update_date_time
    updated_tob_obj = market_data_web_client.patch_top_of_book_client(tob_obj)

    for market_trade_vol in updated_tob_obj.market_trade_volume:
        market_trade_vol.id = None
    if side == Side.BUY:
        assert updated_tob_obj.bid_quote.px == tob_obj.bid_quote.px
    else:
        assert updated_tob_obj.ask_quote.px == tob_obj.ask_quote.px


def _update_buy_tob(buy_symbol: str):
    buy_stored_tob: TopOfBookBaseModel | None = None

    stored_tob_objs = market_data_web_client.get_all_top_of_book_client()
    for tob_obj in stored_tob_objs:
        if tob_obj.symbol == buy_symbol:
            buy_stored_tob = tob_obj

    # For place order non-triggered run
    _update_tob(buy_stored_tob, buy_stored_tob.bid_quote.px - 10, Side.BUY)
    # For place order trigger run
    _update_tob(buy_stored_tob, buy_stored_tob.bid_quote.px, Side.BUY)


def run_buy_top_of_book(loop_count: int, buy_symbol: str, sell_symbol: str, top_of_book_json_list: List[Dict]):
    if loop_count == 1:
        _create_tob(buy_symbol, sell_symbol, top_of_book_json_list)
    else:
        _update_buy_tob(buy_symbol)


def run_sell_top_of_book(sell_symbol: str):
    sell_stored_tob: TopOfBookBaseModel | None = None

    stored_tob_objs = market_data_web_client.get_all_top_of_book_client()
    for tob_obj in stored_tob_objs:
        if tob_obj.symbol == sell_symbol:
            sell_stored_tob = tob_obj

    # For place order non-triggered run
    _update_tob(sell_stored_tob, sell_stored_tob.ask_quote.px - 10, Side.SELL)

    # For place order trigger run
    _update_tob(sell_stored_tob, sell_stored_tob.ask_quote.px, Side.SELL)


def run_last_trade(buy_symbol: str, sell_symbol: str, last_trade_json_list: List[Dict]):
    obj_count = 10
    symbol_list = [buy_symbol, sell_symbol]
    for index, last_trade_json in enumerate(last_trade_json_list):
        for _ in range(obj_count):
            last_trade_obj = LastTradeBaseModel(**last_trade_json)
            last_trade_obj.symbol = symbol_list[index]
            last_trade_obj.time = DateTime.utcnow()
            created_last_trade_obj = market_data_web_client.create_last_trade_client(last_trade_obj)
            created_last_trade_obj.id = None
            created_last_trade_obj.market_trade_volume.id = last_trade_obj.market_trade_volume.id
            created_last_trade_obj.time = last_trade_obj.time
            assert created_last_trade_obj == last_trade_obj


def create_n_validate_strat(buy_symbol: str, sell_symbol: str, pair_strat_obj: PairStratBaseModel,
                            expected_strat_limits: StratLimits,
                            expected_strat_status: StratStatus) -> PairStratBaseModel:

    pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
    pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol
    stored_pair_strat_basemodel = \
        strat_manager_service_web_client.create_pair_strat_client(pair_strat_obj)

    assert pair_strat_obj.frequency == stored_pair_strat_basemodel.frequency, "Unmatched frequency "
    assert pair_strat_obj.pair_strat_params == stored_pair_strat_basemodel.pair_strat_params
    assert expected_strat_status == stored_pair_strat_basemodel.strat_status
    assert expected_strat_limits == stored_pair_strat_basemodel.strat_limits

    # Setting pair_strat to active state
    pair_strat_active_obj = PairStratBaseModel(_id=stored_pair_strat_basemodel.id)
    pair_strat_active_obj.strat_status = StratStatus(strat_state=StratState.StratState_ACTIVE)
    activated_pair_strat_basemodel = \
        strat_manager_service_web_client.patch_pair_strat_client(pair_strat_active_obj)

    assert stored_pair_strat_basemodel.frequency + 1 == activated_pair_strat_basemodel.frequency
    assert activated_pair_strat_basemodel.pair_strat_params == stored_pair_strat_basemodel.pair_strat_params
    assert activated_pair_strat_basemodel.strat_status.strat_state == \
           activated_pair_strat_basemodel.strat_status.strat_state
    assert activated_pair_strat_basemodel.strat_limits == expected_strat_limits

    return activated_pair_strat_basemodel


def create_if_not_exists_and_validate_strat_collection(pair_strat_: PairStratBaseModel):
    strat_collection_obj_list = strat_manager_service_web_client.get_all_strat_collection_client()

    strat_key = f"{pair_strat_.pair_strat_params.strat_leg2.sec.sec_id}-" \
                f"{pair_strat_.pair_strat_params.strat_leg1.sec.sec_id}-" \
                f"{pair_strat_.pair_strat_params.strat_leg1.side}-{pair_strat_.id}"
    if len(strat_collection_obj_list) == 0:
        strat_collection_basemodel = StratCollectionBaseModel(**{
          "_id": 1,
          "loaded_strat_keys": [
            strat_key
          ],
          "buffered_strat_keys": []
        })
        created_strat_collection = \
            strat_manager_service_web_client.create_strat_collection_client(strat_collection_basemodel)

        assert created_strat_collection == strat_collection_basemodel

    else:
        strat_collection_obj = strat_collection_obj_list[0]
        strat_collection_obj.loaded_strat_keys.append(strat_key)
        updated_strat_collection_obj = \
            strat_manager_service_web_client.put_strat_collection_client(strat_collection_obj)

        assert updated_strat_collection_obj == strat_collection_obj


def run_symbol_overview(buy_symbol: str, sell_symbol: str,
                        symbol_overview_obj_list: List[SymbolOverviewBaseModel]):
    for index, symbol_overview_obj in enumerate(symbol_overview_obj_list):
        if index == 0:
            symbol_overview_obj.symbol = buy_symbol
        else:
            symbol_overview_obj.symbol = sell_symbol
        symbol_overview_obj.id = None
        created_symbol_overview = market_data_web_client.create_symbol_overview_client(symbol_overview_obj)

        symbol_overview_obj.id = created_symbol_overview.id
        assert created_symbol_overview == symbol_overview_obj, f"Created symbol_overview {symbol_overview_obj} not " \
                                                               f"equals to expected symbol_overview " \
                                                               f"{created_symbol_overview}"


def create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list: List[MarketDepthBaseModel]):
    for index, market_depth_basemodel in enumerate(market_depth_basemodel_list):
        if index < 10:
            market_depth_basemodel.symbol = buy_symbol
        else:
            market_depth_basemodel.symbol = sell_symbol
        created_market_depth = market_data_web_client.create_market_depth_client(market_depth_basemodel)
        created_market_depth.id = None
        assert created_market_depth == market_depth_basemodel


def wait_for_get_new_order_placed(symbol_pair_count: int, wait_stop_px: int | float, buy_symbol: str,
                                  sell_symbol: str, last_update_date_time: DateTime | None, side: Side):
    loop_counter = 0
    loop_limit = 10
    while True:
        time.sleep(2)

        tob_obj_list = market_data_web_client.get_all_top_of_book_client()
        if side == Side.BUY:
            symbol_to_check = buy_symbol
        else:
            symbol_to_check = sell_symbol
        buy_index = 0+(2*(symbol_pair_count-1))
        sell_index = 1+(2*(symbol_pair_count-1))
        if last_update_date_time is None:
            if tob_obj_list[buy_index].symbol == symbol_to_check:
                if tob_obj_list[buy_index].bid_quote.px == wait_stop_px:
                    return tob_obj_list[buy_index].last_update_date_time
            else:
                if tob_obj_list[sell_index].ask_quote.px == wait_stop_px:
                    return tob_obj_list[sell_index].last_update_date_time
        else:
            if tob_obj_list[buy_index].symbol == symbol_to_check:
                if tob_obj_list[buy_index].last_update_date_time > last_update_date_time and \
                        tob_obj_list[buy_index].bid_quote.px == wait_stop_px:
                    return tob_obj_list[buy_index].last_update_date_time
            else:
                if tob_obj_list[sell_index].last_update_date_time > last_update_date_time and \
                        tob_obj_list[sell_index].ask_quote.px == wait_stop_px:
                    return tob_obj_list[sell_index].last_update_date_time

        loop_counter += 1
        if loop_counter == loop_limit:
            assert False, f"Could not find any update after {last_update_date_time} in tob_list {tob_obj_list}"


def set_n_verify_limits(expected_order_limits_obj, expected_portfolio_limits_obj):
    created_order_limits_obj = strat_manager_service_web_client.create_order_limits_client(expected_order_limits_obj)
    assert created_order_limits_obj == expected_order_limits_obj

    created_portfolio_limits_obj = \
        strat_manager_service_web_client.create_portfolio_limits_client(expected_portfolio_limits_obj)
    assert created_portfolio_limits_obj == expected_portfolio_limits_obj


def create_n_verify_portfolio_status(portfolio_status_obj: PortfolioStatusBaseModel):
    portfolio_status_obj.id = 1
    created_portfolio_status = strat_manager_service_web_client.create_portfolio_status_client(portfolio_status_obj)
    assert created_portfolio_status == portfolio_status_obj


def verify_portfolio_status(total_loop_count: int, symbol_pair_count: int,
                            expected_portfolio_status: PortfolioStatusBaseModel):
    # expected portfolio_status
    expected_portfolio_status.overall_sell_notional = ((7700 * total_loop_count) + (300 * total_loop_count) - (
                4400 * total_loop_count)) * symbol_pair_count
    expected_portfolio_status.overall_sell_fill_notional = (3600 * total_loop_count) * symbol_pair_count
    # computes from last buy test execution
    expected_portfolio_status.overall_buy_notional = \
        ((9000 * total_loop_count) - (500 * total_loop_count) - (4000 * total_loop_count)) * symbol_pair_count
    expected_portfolio_status.overall_buy_fill_notional = (4500 * total_loop_count) * symbol_pair_count
    expected_portfolio_status.current_period_available_buy_order_count = 4
    expected_portfolio_status.current_period_available_sell_order_count = 4

    portfolio_status_list = strat_manager_service_web_client.get_all_portfolio_status_client()
    for portfolio_status in portfolio_status_list:
        portfolio_status.id = None
        portfolio_status.portfolio_alerts = []
    assert expected_portfolio_status in portfolio_status_list


def get_latest_order_journal_with_status_and_order_id(stored_order_journal_list,
                                                      expected_order_event, expected_order_id):
    placed_order_journal = None
    for stored_order_journal in stored_order_journal_list:
        if stored_order_journal.order_event == expected_order_event and \
                stored_order_journal.order.order_id == expected_order_id:
            placed_order_journal = stored_order_journal
    assert placed_order_journal is not None, f"Can't find any order_journal with order_id {expected_order_id} " \
                                             f"order_event {expected_order_event}"
    return placed_order_journal


def get_latest_fill_journal_with_order_id(stored_fill_journals: List[FillsJournal], expected_order_id: str):
    found_fill_journal = None
    for stored_fill_journal in stored_fill_journals:
        if stored_fill_journal.order_id == expected_order_id:
            found_fill_journal = stored_fill_journal
    assert found_fill_journal is not None, f"Can't find any fill_journal with order_id {expected_order_id}"
    return found_fill_journal

def test_clean_and_set_limits(expected_order_limits_, expected_portfolio_limits_, expected_portfolio_status_):
    # cleaning all collections
    clean_mongo_collections(mongo_server="mongodb://localhost:27017", database_name="addressbook_test",
                            ignore_collections=["UILayout"])
    clean_mongo_collections(mongo_server="mongodb://localhost:27017", database_name="market_data_test_fixture",
                            ignore_collections=["UILayout"])

    # setting limits
    set_n_verify_limits(expected_order_limits_, expected_portfolio_limits_)

    # creating portfolio_status
    create_n_verify_portfolio_status(copy.deepcopy(expected_portfolio_status_))


@pytest.fixture(scope="session")
def total_loop_counts_per_side():
    total_loop_counts_per_side = 3
    yield total_loop_counts_per_side


@pytest.fixture(scope="session")
def buy_sell_symbol_list():
    yield [
        ("CB_Sec_1", "EQT_Sec_1"),
        ("CB_Sec_2", "EQT_Sec_2")
    ]


# Run Strat_executor before starting this test
def test_buy_sell_order(pair_securities_with_sides_, buy_order_, sell_order_, buy_fill_journal_,
                        sell_fill_journal_, expected_buy_order_snapshot_, expected_sell_order_snapshot_,
                        expected_symbol_side_snapshot_, pair_strat_, expected_strat_limits_, expected_start_status_,
                        expected_strat_brief_, expected_portfolio_status_, top_of_book_list_,
                        last_trade_fixture_list, symbol_overview_obj_list, market_depth_basemodel_list,
                        expected_order_limits_, expected_portfolio_limits_, total_loop_counts_per_side,
                        buy_sell_symbol_list):

    total_loop_count = total_loop_counts_per_side
    residual_test_wait = 10

    symbol_pair_counter = 0
    for buy_symbol, sell_symbol in buy_sell_symbol_list:
        symbol_pair_counter += 1

        # Creating Strat
        active_pair_strat = create_n_validate_strat(buy_symbol, sell_symbol, pair_strat_,
                                                    expected_strat_limits_, expected_start_status_)

        # running symbol_overview
        run_symbol_overview(buy_symbol, sell_symbol, symbol_overview_obj_list)

        # running Last Trade
        run_last_trade(buy_symbol, sell_symbol, last_trade_fixture_list)

        # creating market_depth
        create_market_depth(buy_symbol, sell_symbol, market_depth_basemodel_list)

        # Adding strat in strat_collection
        create_if_not_exists_and_validate_strat_collection(active_pair_strat)

        buy_tob_last_update_date_time_tracker: DateTime | None = None
        sell_tob_last_update_date_time_tracker: DateTime | None = None
        for loop_count in range(1, total_loop_count+1):
            expected_buy_order_snapshot = copy.deepcopy(expected_buy_order_snapshot_)
            expected_buy_order_snapshot.order_brief.security.sec_id = buy_symbol

            expected_buy_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[0])
            expected_buy_symbol_side_snapshot.security.sec_id = buy_symbol

            expected_pair_strat = copy.deepcopy(pair_strat_)
            pair_strat_.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
            pair_strat_.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol

            expected_strat_status = copy.deepcopy(expected_start_status_)
            expected_strat_status.strat_state = StratState.StratState_ACTIVE

            expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
            expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
            expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

            expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

            # placing order
            current_itr_expected_buy_order_journal_ = copy.deepcopy(buy_order_)
            current_itr_expected_buy_order_journal_.order.security.sec_id = buy_symbol

            # Running TopOfBook (this triggers expected buy order)
            run_buy_top_of_book(loop_count, buy_symbol, sell_symbol, top_of_book_list_)

            # Waiting for tob to trigger place order
            buy_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed(symbol_pair_counter, 110, buy_symbol, sell_symbol,
                                              buy_tob_last_update_date_time_tracker, Side.BUY)

            stored_order_journal_list = \
                strat_manager_service_web_client.get_all_order_journal_client()

            order_id = f"O{loop_count+((symbol_pair_counter-1)*(2*total_loop_count))}"
            placed_order_journal = get_latest_order_journal_with_status_and_order_id(stored_order_journal_list,
                                                                                     OrderEventType.OE_NEW,
                                                                                     order_id)
            create_buy_order_date_time: DateTime = placed_order_journal.order_event_date_time

            # Checking placed order computations
            check_placed_buy_order_computes(loop_count, order_id, buy_symbol,
                                            placed_order_journal, expected_buy_order_snapshot,
                                            expected_buy_symbol_side_snapshot, expected_pair_strat,
                                            expected_strat_limits_, expected_strat_status,
                                            expected_strat_brief_obj, expected_portfolio_status)

            TradeSimulator.process_order_ack(order_id, current_itr_expected_buy_order_journal_.order.px,
                                             current_itr_expected_buy_order_journal_.order.qty,
                                             current_itr_expected_buy_order_journal_.order.side,
                                             current_itr_expected_buy_order_journal_.order.security.sec_id,
                                             current_itr_expected_buy_order_journal_.order.underlying_account)

            stored_order_journal_list = \
                strat_manager_service_web_client.get_all_order_journal_client()
            placed_order_journal_obj_ack_response = \
                get_latest_order_journal_with_status_and_order_id(stored_order_journal_list,
                                                                  OrderEventType.OE_ACK, order_id)

            # Checking Ack response on placed order
            placed_buy_order_ack_receive(loop_count, order_id, create_buy_order_date_time,
                                         placed_order_journal_obj_ack_response, expected_buy_order_snapshot)

            buy_fill_journal_obj = copy.deepcopy(buy_fill_journal_)
            TradeSimulator.process_fill(order_id, buy_fill_journal_obj.fill_px, buy_fill_journal_obj.fill_qty,
                                        Side.BUY, buy_symbol, buy_fill_journal_obj.underlying_account)

            placed_fill_journal_objs = strat_manager_service_web_client.get_all_fills_journal_client()
            placed_fill_journal_obj = get_latest_fill_journal_with_order_id(placed_fill_journal_objs, order_id)

            # Checking Fill receive on placed order
            check_fill_receive_for_placed_buy_order(loop_count, order_id, create_buy_order_date_time,
                                                    buy_symbol, placed_fill_journal_obj,
                                                    expected_buy_order_snapshot, expected_buy_symbol_side_snapshot,
                                                    expected_pair_strat,
                                                    expected_strat_limits_, expected_strat_status,
                                                    expected_strat_brief_obj, expected_portfolio_status)

            # Sleeping to let the order get cxlled
            time.sleep(residual_test_wait)

        for loop_count in range(1, total_loop_count+1):
            expected_sell_order_snapshot = copy.deepcopy(expected_sell_order_snapshot_)
            expected_sell_order_snapshot.order_brief.security.sec_id = sell_symbol

            expected_sell_symbol_side_snapshot = copy.deepcopy(expected_symbol_side_snapshot_[1])
            expected_sell_symbol_side_snapshot.security.sec_id = sell_symbol

            expected_pair_strat = copy.deepcopy(pair_strat_)
            pair_strat_.pair_strat_params.strat_leg1.sec.sec_id = buy_symbol
            pair_strat_.pair_strat_params.strat_leg2.sec.sec_id = sell_symbol

            expected_strat_status = copy.deepcopy(expected_start_status_)
            expected_strat_status.strat_state = StratState.StratState_ACTIVE

            expected_strat_brief_obj = copy.deepcopy(expected_strat_brief_)
            expected_strat_brief_obj.pair_buy_side_trading_brief.security.sec_id = buy_symbol
            expected_strat_brief_obj.pair_sell_side_trading_brief.security.sec_id = sell_symbol

            expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)

            # placing order
            current_itr_expected_sell_order_journal_ = copy.deepcopy(sell_order_)

            # Running TopOfBook (this triggers expected buy order)
            run_sell_top_of_book(sell_symbol)

            # Waiting for tob to trigger place order
            sell_tob_last_update_date_time_tracker = \
                wait_for_get_new_order_placed(symbol_pair_counter, 120, buy_symbol, sell_symbol,
                                              sell_tob_last_update_date_time_tracker, Side.SELL)

            stored_order_journal_list = \
                strat_manager_service_web_client.get_all_order_journal_client()

            order_id: str = f"O{loop_count+total_loop_count+((symbol_pair_counter-1)*(2*total_loop_count))}"
            placed_order_journal = get_latest_order_journal_with_status_and_order_id(stored_order_journal_list,
                                                                                     OrderEventType.OE_NEW, order_id)
            create_sell_order_date_time: DateTime = placed_order_journal.order_event_date_time

            # Checking placed order computations
            check_placed_sell_order_computes(loop_count, total_loop_count, order_id,
                                             sell_symbol, placed_order_journal, expected_sell_order_snapshot,
                                             expected_sell_symbol_side_snapshot, expected_pair_strat,
                                             expected_strat_limits_, expected_strat_status,
                                             expected_strat_brief_obj, expected_portfolio_status)

            TradeSimulator.process_order_ack(order_id, current_itr_expected_sell_order_journal_.order.px,
                                             current_itr_expected_sell_order_journal_.order.qty,
                                             current_itr_expected_sell_order_journal_.order.side,
                                             current_itr_expected_sell_order_journal_.order.security.sec_id,
                                             current_itr_expected_sell_order_journal_.order.underlying_account)

            stored_order_journal_list = \
                strat_manager_service_web_client.get_all_order_journal_client()
            placed_order_journal_obj_ack_response = \
                get_latest_order_journal_with_status_and_order_id(stored_order_journal_list,
                                                                  OrderEventType.OE_ACK, order_id)

            # Checking Ack response on placed order
            placed_sell_order_ack_receive(loop_count, order_id, create_sell_order_date_time,
                                          total_loop_count, placed_order_journal_obj_ack_response,
                                          expected_sell_order_snapshot)

            sell_fill_journal_obj = copy.deepcopy(sell_fill_journal_)
            TradeSimulator.process_fill(order_id, sell_fill_journal_obj.fill_px, sell_fill_journal_obj.fill_qty,
                                        Side.SELL, sell_symbol, sell_fill_journal_obj.underlying_account)

            placed_fill_journal_objs = strat_manager_service_web_client.get_all_fills_journal_client()
            placed_fill_journal_obj = get_latest_fill_journal_with_order_id(placed_fill_journal_objs, order_id)

            # Checking Fill receive on placed order
            check_fill_receive_for_placed_sell_order(loop_count, total_loop_count, order_id,
                                                     create_sell_order_date_time, sell_symbol, placed_fill_journal_obj,
                                                     expected_sell_order_snapshot, expected_sell_symbol_side_snapshot,
                                                     expected_pair_strat, expected_strat_limits_,
                                                     expected_strat_status, expected_strat_brief_obj,
                                                     expected_portfolio_status)

            # Sleeping to let the order get cxlled
            time.sleep(residual_test_wait)

        assert True


def test_validate_portfolio_status_computes_after_test(expected_portfolio_status_,
                                                       buy_sell_symbol_list,
                                                       total_loop_counts_per_side):
    expected_portfolio_status = copy.deepcopy(expected_portfolio_status_)
    total_symbol_pairs = len(buy_sell_symbol_list)
    verify_portfolio_status(total_loop_counts_per_side, total_symbol_pairs, expected_portfolio_status)


def test_drop_test_environment():
    drop_mongo_collections(mongo_server="mongodb://localhost:27017", database_name="addressbook_test",
                           ignore_collections=["UILayout"])
    drop_mongo_collections(mongo_server="mongodb://localhost:27017", database_name="market_data_test_fixture",
                           ignore_collections=["UILayout"])


def test_clear_test_environment():
    clean_mongo_collections(mongo_server="mongodb://localhost:27017", database_name="addressbook_test",
                            ignore_collections=["UILayout"])
    clean_mongo_collections(mongo_server="mongodb://localhost:27017", database_name="market_data_test_fixture",
                            ignore_collections=["UILayout"])
