import pytest
import os
import copy
from pendulum import DateTime

os.environ["DBType"] = "beanie"

# Project Imports
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import \
    MarketDepthBaseModel, TopOfBookBaseModel, SymbolOverviewBaseModel
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import *


@pytest.fixture(scope="session")
def market_data_service_web_client_fixture():
    market_data_service_web_client: MarketDataServiceWebClient = MarketDataServiceWebClient()
    yield market_data_service_web_client

@pytest.fixture(scope="session")
def strat_manager_service_web_client_():
    strat_manager_service_web_client: StratManagerServiceWebClient = StratManagerServiceWebClient()
    yield strat_manager_service_web_client


@pytest.fixture(scope="session")
def market_depth_basemodel_list():
    input_data = []

    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        for side, px, qty, dev in [("BID", 100, 90, -1), ("ASK", 110, 70, 1)]:
            input_data.extend([
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:30.165Z",
                    "side": side,
                    "px": px,
                    "qty": qty+10,
                    "position": 1,
                    "market_maker": "string",
                    "is_smart_depth": False,
                    "cumulative_notional": px*(qty+10),
                    "cumulative_qty": qty+10,
                    "cumulative_avg_px": (px*(qty+10))/(qty+10)
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:31.165Z",
                    "side": side,
                    "px": px+(dev*1),
                    "qty": qty-20,
                    "position": 2,
                    "market_maker": "string",
                    "is_smart_depth": False,
                    "cumulative_notional": (px*(qty+10))+((px+(dev*1))*(qty-20)),
                    "cumulative_qty": (qty+10) + (qty-20),
                    "cumulative_avg_px": ((px*(qty+10))+((px+(dev*1))*(qty-20)))/((qty+10) + (qty-20))
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:32.165Z",
                    "side": side,
                    "px": px+(dev*2),
                    "qty": qty+10,
                    "position": 3,
                    "market_maker": "string",
                    "is_smart_depth": False,
                    "cumulative_notional": (px*(qty+10))+((px+(dev*1))*(qty-20))+((px+(dev*2))*(qty+10)),
                    "cumulative_qty": (qty+10) + (qty-20) + (qty+10),
                    "cumulative_avg_px": ((px*(qty+10))+((px+(dev*1))*(qty-20))+((px+(dev*2))*(qty+10)))/((qty+10) + (qty-20) + (qty+10))
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:31.165Z",
                    "side": side,
                    "px": px+(dev*3),
                    "qty": qty-20,
                    "position": 4,
                    "market_maker": "string",
                    "is_smart_depth": False,
                    "cumulative_notional":
                        (px*(qty+10))+((px+(dev*1))*(qty-20))+((px+(dev*2))*(qty+10))+((px+(dev*3))*(qty-20)),
                    "cumulative_qty": (qty+10) + (qty-20) + (qty+10) + (qty-20),
                    "cumulative_avg_px": ((px*(qty+10))+((px+(dev*1))*(qty-20))+((px+(dev*2))*(qty+10))+((px+(dev*3))*(qty-20)))/((qty+10) + (qty-20) + (qty+10) + (qty-20))
                },
                {
                    "symbol": symbol,
                    "time": "2023-02-13T20:30:32.165Z",
                    "side": side,
                    "px": px+(dev*4),
                    "qty": qty+20,
                    "position": 5,
                    "market_maker": "string",
                    "is_smart_depth": False,
                    "cumulative_notional":
                        (px*(qty+10))+((px+(dev*1))*(qty-20))+((px+(dev*2))*(qty+10))+((px+(dev*3))*(qty-20))+((px+(dev*4))*(qty+20)),
                    "cumulative_qty": (qty+10) + (qty-20) + (qty+10) + (qty-20) + (qty+20),
                    "cumulative_avg_px": ((px*(qty+10))+((px+(dev*1))*(qty-20))+((px+(dev*2))*(qty+10))+((px+(dev*3))*(qty-20))+((px+(dev*4))*(qty+20)))/((qty+10) + (qty-20) + (qty+10) + (qty-20) + (qty+20))
                }
            ])

    market_depth_basemodel_list = [MarketDepthBaseModel(**market_depth_json) for market_depth_json in input_data]

    yield market_depth_basemodel_list


@pytest.fixture(scope="session")
def top_of_book_list_():
    input_data = []
    for index, symbol in enumerate(["CB_Sec_1", "EQT_Sec_1"]):
        input_data.extend([
            {
                "symbol": symbol,
                "bid_quote": {
                    "px": 110,
                    "qty": 20,
                    "last_update_date_time": "2023-02-13T20:30:33.165Z"
                },
                "ask_quote": {
                    "px": 120,
                    "qty": 40,
                    "last_update_date_time": "2023-02-13T20:30:31.165Z"
                },
                "last_trade": {
                    "px": 116,
                    "qty": 150,
                    "last_update_date_time": "2023-02-13T20:30:35.165Z"
                },
                "total_trading_security_size": 100,
                "market_trade_volume": [
                    {
                        "participation_period_last_trade_qty_sum": 90,
                        "applicable_period_seconds": 180
                    }
                ],
                "last_update_date_time": "2023-02-13T20:30:34.165Z"
            }

        ])
    yield input_data


@pytest.fixture(scope='session')
def set_market_depth(market_data_service_web_client_fixture, market_depth_basemodel_list):
    # Cleaning market data if already exists
    stored_market_depth_objs = market_data_service_web_client_fixture.get_all_market_depth_client()
    for market_depth_obj in stored_market_depth_objs:
        market_data_service_web_client_fixture.delete_market_depth_client(market_depth_obj.id)

    for idx, market_depth_basemodel in enumerate(market_depth_basemodel_list):
        stored_market_depth_basemodel = \
            market_data_service_web_client_fixture.create_market_depth_client(market_depth_basemodel)

        # to tackle format diff because of time zone (present in market_depth_basemodel but not
        # in stored_market_depth_basemodel) assigning both same time field
        stored_market_depth_basemodel.id = None
        stored_market_depth_basemodel.time = market_depth_basemodel.time
        assert stored_market_depth_basemodel == market_depth_basemodel, \
            f"stored obj {stored_market_depth_basemodel} not equal to " \
            f"created obj {market_depth_basemodel}"
    yield


@pytest.fixture(scope='session')
def set_top_of_book(market_data_service_web_client_fixture, top_of_book_list_):
    # Cleaning top of books if already exists
    stored_top_of_book_objs = market_data_service_web_client_fixture.get_all_top_of_book_client()
    for top_of_book_obj in stored_top_of_book_objs:
        market_data_service_web_client_fixture.delete_top_of_book_client(top_of_book_obj.id)

    for input_data in top_of_book_list_:
        top_of_book_basemodel = TopOfBookBaseModel(**input_data)
        stored_top_of_book_basemodel = \
            market_data_service_web_client_fixture.create_top_of_book_client(top_of_book_basemodel)

        top_of_book_basemodel.id = stored_top_of_book_basemodel.id
        # to tackle format diff because of time zone (present in top_of_book_basemodel but not
        # in stored_top_of_book_basemodel) assigning both same time field
        stored_top_of_book_basemodel.bid_quote.last_update_date_time = top_of_book_basemodel.bid_quote.last_update_date_time
        stored_top_of_book_basemodel.ask_quote.last_update_date_time = top_of_book_basemodel.ask_quote.last_update_date_time
        stored_top_of_book_basemodel.last_trade.last_update_date_time = top_of_book_basemodel.last_trade.last_update_date_time
        stored_top_of_book_basemodel.last_update_date_time = top_of_book_basemodel.last_update_date_time
        assert stored_top_of_book_basemodel == top_of_book_basemodel, \
            f"stored obj {stored_top_of_book_basemodel} not equal to " \
            f"created obj {top_of_book_basemodel}"
    yield


@pytest.fixture(scope='session')
def pair_securities_with_sides_():
    yield {
        "security1": {"sec_id": "CB_Sec_1", "sec_type": "TICKER"}, "side1": "BUY",
        "security2": {"sec_id": "EQT_Sec_1", "sec_type": "TICKER"}, "side2": "SELL"
    }


@pytest.fixture(scope="session")
def last_trade_fixture_list():
    input_data = []
    for index, symbol in enumerate(["CB_Sec_1", "EQT_Sec_1"]):
        input_data.extend([
            {
                "symbol": symbol,
                "time": "2023-03-10T09:19:12.019Z",
                "px": 116,
                "qty": 150,
                "exchange": "Exch",
                "special_conditions": "none",
                "past_limit": False,
                "unreported": False,
                "market_trade_volume": {
                    "participation_period_last_trade_qty_sum": 0,
                    "applicable_period_seconds": 0
                }
            }

        ])
    yield input_data


@pytest.fixture(scope="session")
def symbol_overview_obj_list():
    symbol_overview_obj_list = []
    for symbol in ["CB_Sec_1", "EQT_Sec_1"]:
        symbol_overview_obj_list.append(
            SymbolOverviewBaseModel(**{
              "symbol": symbol,
              "limit_up_px": 150,
              "limit_dn_px": 50,
              "conv_px": 90,
              "closing_px": 95,
              "open_px": 95,
              "last_update_date_time": "2023-03-12T13:11:22.329Z",
              "force_publish": False
            })
        )
    yield symbol_overview_obj_list


@pytest.fixture(scope='session')
def expected_start_status_(pair_securities_with_sides_):
    yield StratStatus(**{
      "strat_state": "StratState_READY",
      "total_buy_qty": 0,
      "total_sell_qty": 0,
      "total_order_qty": 0,
      "total_open_buy_qty": 0,
      "total_open_sell_qty": 0,
      "avg_open_buy_px": 0,
      "avg_open_sell_px": 0,
      "total_open_buy_notional": 0,
      "total_open_sell_notional": 0,
      "total_open_exposure": 0,
      "total_fill_buy_qty": 0,
      "total_fill_sell_qty": 0,
      "avg_fill_buy_px": 0,
      "avg_fill_sell_px": 0,
      "total_fill_buy_notional": 0,
      "total_fill_sell_notional": 0,
      "total_fill_exposure": 0,
      "total_cxl_buy_qty": 0,
      "total_cxl_sell_qty": 0,
      "avg_cxl_buy_px": 0,
      "avg_cxl_sell_px": 0,
      "total_cxl_buy_notional": 0,
      "total_cxl_sell_notional": 0,
      "total_cxl_exposure": 0,
      "average_premium": 0,
      "balance_notional": 0,
      "strat_alerts": []
    })


@pytest.fixture(scope="session")
def expected_strat_limits_():
    # TODO: find way to get it from override pre call of pair_strat create, hard-coding for now
    yield StratLimits(**{
      "max_open_orders_per_side": 5,
      "max_cb_notional": 300000,
      "max_open_cb_notional": 30000,
      "max_net_filled_notional": 160000,
      "max_concentration": 10,
      "limit_up_down_volume_participation_rate": 1,
      "cancel_rate": {
        "max_cancel_rate": 60,
        "applicable_period_seconds": 0,
        "waived_min_orders": 5
      },
      "market_trade_volume_participation": {
        "max_participation_rate": 40,
        "applicable_period_seconds": 180
      },
      "market_depth": {
        "participation_rate": 10,
        "depth_levels": 3
      },
      "residual_restriction": {
        "max_residual": 30_000,
        "residual_mark_seconds": 4
      },
      "eligible_brokers": []
    })


@pytest.fixture(scope='session')
def pair_strat_(pair_securities_with_sides_):
    yield PairStratBaseModel(**{
      "last_active_date_time": "2023-02-13T20:30:31.165Z",
      "frequency": 1,
      "pair_strat_params": {
        "strat_leg1": {
          "exch_id": "EXCH1",
          "sec": pair_securities_with_sides_["security1"],
          "side": pair_securities_with_sides_["side1"]
        },
        "strat_leg2": {
          "exch_id": "EXCH2",
          "sec": pair_securities_with_sides_["security2"],
          "side": pair_securities_with_sides_["side2"]
        },
        "exch_response_max_seconds": 5,
        "common_premium_percentage": 40,
        "hedge_ratio": 5
      }
    })


@pytest.fixture(scope='session')
def delete_existing_strats_and_snapshots(strat_manager_service_web_client_):
    # Cleaning order journal if already exists
    stored_order_journal_objs = strat_manager_service_web_client_.get_all_order_journal_client()
    for stored_order_journal_obj in stored_order_journal_objs:
        strat_manager_service_web_client_.delete_order_journal_client(stored_order_journal_obj.id)

    # Cleaning order snapshot if already exists
    stored_order_snapshot_objs = strat_manager_service_web_client_.get_all_order_snapshot_client()
    for stored_order_snapshot_obj in stored_order_snapshot_objs:
        strat_manager_service_web_client_.delete_order_snapshot_client(stored_order_snapshot_obj.id)

    # Cleaning symbol side snapshot if already exists
    stored_symbol_side_snapshot_objs = strat_manager_service_web_client_.get_all_symbol_side_snapshot_client()
    for stored_symbol_side_snapshot_obj in stored_symbol_side_snapshot_objs:
        strat_manager_service_web_client_.delete_symbol_side_snapshot_client(stored_symbol_side_snapshot_obj.id)

    # Cleaning pair_strats if already exists
    stored_pair_strat_objs = strat_manager_service_web_client_.get_all_pair_strat_client()
    for stored_pair_strat_obj in stored_pair_strat_objs:
        strat_manager_service_web_client_.delete_pair_strat_client(stored_pair_strat_obj.id)

    # Cleaning strat_brief if already exists
    stored_strat_brief_objs = strat_manager_service_web_client_.get_all_strat_brief_client()
    for stored_strat_brief_obj in stored_strat_brief_objs:
        strat_manager_service_web_client_.delete_strat_brief_client(stored_strat_brief_obj.id)

    # Cleaning portfolio_status if already exists
    stored_portfolio_status_objs = strat_manager_service_web_client_.get_all_portfolio_status_client()
    for stored_portfolio_status_obj in stored_portfolio_status_objs:
        strat_manager_service_web_client_.delete_portfolio_status_client(stored_portfolio_status_obj.id)
    yield


@pytest.fixture(scope='session')
def pair_strat_input_data(delete_existing_strats_and_snapshots, strat_manager_service_web_client_,
                          pair_strat_, expected_start_status_, expected_strat_limits_):
    stored_pair_strat_basemodel = \
        strat_manager_service_web_client_.create_pair_strat_client(pair_strat_)

    assert pair_strat_.frequency == stored_pair_strat_basemodel.frequency
    assert pair_strat_.pair_strat_params == stored_pair_strat_basemodel.pair_strat_params
    assert expected_start_status_ == stored_pair_strat_basemodel.strat_status
    assert expected_strat_limits_ == stored_pair_strat_basemodel.strat_limits

    # Setting pair_strat to active state
    pair_strat_active_obj = stored_pair_strat_basemodel
    pair_strat_active_obj.strat_status.strat_state = StratState.StratState_ACTIVE
    activated_pair_strat_basemodel = \
        strat_manager_service_web_client_.put_pair_strat_client(pair_strat_active_obj)

    assert stored_pair_strat_basemodel.frequency+1 == activated_pair_strat_basemodel.frequency
    assert activated_pair_strat_basemodel.pair_strat_params == pair_strat_active_obj.pair_strat_params
    assert activated_pair_strat_basemodel.strat_status == pair_strat_active_obj.strat_status
    assert activated_pair_strat_basemodel.strat_limits == expected_strat_limits_


def empty_pair_side_trading_brief_obj(symbol: str, side: str, sec_type: str | None = SecurityType.TICKER):
    return PairSideTradingBrief(**{
        "security": {
          "sec_id": symbol,
          "sec_type": sec_type
        },
        "side": side,
        "last_update_date_time": DateTime.utcnow(),
        "consumable_open_orders": 0,
        "consumable_notional": 0,
        "consumable_open_notional": 0,
        "consumable_concentration": 0,
        "participation_period_order_qty_sum": 0,
        "consumable_cxl_qty": 0,
        "indicative_consumable_participation_qty": 0,
        "residual_qty": 0,
        "indicative_consumable_residual": 0,
        "all_bkr_cxlled_qty": 0,
        "open_notional": 0,
        "open_qty": 0
    })


@pytest.fixture(scope="session")
def expected_strat_brief_(pair_securities_with_sides_):
    pair_buy_side_trading_brief = empty_pair_side_trading_brief_obj(pair_securities_with_sides_["security1"]["sec_id"],
                                                                    pair_securities_with_sides_["side1"])
    pair_sell_side_trading_brief = empty_pair_side_trading_brief_obj(pair_securities_with_sides_["security2"]["sec_id"],
                                                                     pair_securities_with_sides_["side2"])
    yield StratBriefBaseModel(pair_buy_side_trading_brief=pair_buy_side_trading_brief,
                              pair_sell_side_trading_brief=pair_sell_side_trading_brief,
                              consumable_nett_filled_notional=0)

@pytest.fixture(scope="session")
def expected_symbol_side_snapshot_():
    yield [
        SymbolSideSnapshotBaseModel(**{
            "security": {
              "sec_id": "CB_Sec_1",
              "sec_type": SecurityType.TICKER
            },
            "side": "BUY",
            "avg_px": 0,
            "total_qty": 0,
            "total_filled_qty": 0,
            "avg_fill_px": 0,
            "total_fill_notional": 0,
            "last_update_fill_qty": 0,
            "last_update_fill_px": 0,
            "total_cxled_qty": 0,
            "avg_cxled_px": 0,
            "total_cxled_notional": 0,
            "last_update_date_time": "2023-02-13T20:30:35.165Z",
            "order_create_count": 0
        }),
        SymbolSideSnapshotBaseModel(**{
            "security": {
                "sec_id": "EQT_Sec_1",
                "sec_type": SecurityType.TICKER
            },
            "side": "SELL",
            "avg_px": 0,
            "total_qty": 0,
            "total_filled_qty": 0,
            "avg_fill_px": 0,
            "total_fill_notional": 0,
            "last_update_fill_qty": 0,
            "last_update_fill_px": 0,
            "total_cxled_qty": 0,
            "avg_cxled_px": 0,
            "total_cxled_notional": 0,
            "last_update_date_time": "2023-02-13T20:30:36.165Z",
            "order_create_count": 0
        })
    ]


@pytest.fixture(scope="session")
def expected_portfolio_status_():
    yield PortfolioStatusBaseModel(**{
        "kill_switch": False,
        "portfolio_alerts": [],
        "overall_buy_notional": 0,
        "overall_sell_notional": 0,
        "overall_buy_fill_notional": 0,
        "overall_sell_fill_notional": 0,
        "current_period_available_buy_order_count": 0,
        "current_period_available_sell_order_count": 0
    })


@pytest.fixture(scope="session")
def buy_order_(pair_securities_with_sides_):
    yield OrderJournalBaseModel(**{
        "order": {
            "order_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 100,
            "qty": 90,
            "order_notional": 0,
            "underlying_account": "Acc1",
            "text": [
              "test_string"
            ]
        },
        "order_event_date_time": DateTime.utcnow(),
        "order_event": "OE_NEW"
    })


@pytest.fixture(scope="session")
def expected_buy_order_snapshot_(pair_securities_with_sides_):
    yield OrderSnapshotBaseModel(**{
        "order_brief": {
            "order_id": "O1",
            "security": pair_securities_with_sides_["security1"],
            "side": pair_securities_with_sides_["side1"],
            "px": 0,
            "qty": 0,
            "order_notional": 0,
            "underlying_account": "Acc1",
            "text": []
        },
        "filled_qty": 0,
        "avg_fill_px": 0,
        "fill_notional": 0,
        "last_update_fill_qty": 0,
        "last_update_fill_px": 0,
        "cxled_qty": 0,
        "avg_cxled_px": 0,
        "cxled_notional": 0,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "order_status": "OE_UNACK"
    })


@pytest.fixture(scope="session")
def buy_fill_journal_():
    yield FillsJournalBaseModel(**{
        "order_id": "O1",
        "fill_px": 90,
        "fill_qty": 50,
        "fill_notional": 0,
        "underlying_account": "Acc1",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F1"
    })


@pytest.fixture(scope="session")
def order_cxl_request(strat_manager_service_web_client_, buy_order_):
    placed_order_ack_obj = copy.deepcopy(buy_order_)
    placed_order_ack_obj.order_event = "OE_CXL"

    created_order_journal_obj = \
        strat_manager_service_web_client_.create_order_journal_client(placed_order_ack_obj)

    yield created_order_journal_obj


@pytest.fixture(scope="session")
def sell_order_(pair_securities_with_sides_):
    yield OrderJournalBaseModel(**{
        "order": {
            "order_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 110,
            "qty": 70,
            "order_notional": 0,
            "underlying_account": "Acc1",
            "text": [
              "test_string"
            ]
        },
        "order_event_date_time": DateTime.utcnow(),
        "order_event": "OE_NEW"
    })

@pytest.fixture(scope="session")
def expected_sell_order_snapshot_(pair_securities_with_sides_):
    yield OrderSnapshotBaseModel(**{
        "order_brief": {
            "order_id": "O2",
            "security": pair_securities_with_sides_["security2"],
            "side": pair_securities_with_sides_["side2"],
            "px": 0,
            "qty": 0,
            "order_notional": 0,
            "underlying_account": "Acc1",
            "text": []
        },
        "filled_qty": 0,
        "avg_fill_px": 0,
        "fill_notional": 0,
        "last_update_fill_qty": 0,
        "last_update_fill_px": 0,
        "cxled_qty": 0,
        "avg_cxled_px": 0,
        "cxled_notional": 0,
        "last_update_date_time": DateTime.utcnow(),
        "create_date_time": DateTime.utcnow(),
        "order_status": "OE_UNACK"
    })


@pytest.fixture(scope="session")
def sell_fill_journal_():
    yield FillsJournalBaseModel(**{
        "order_id": "O2",
        "fill_px": 120,
        "fill_qty": 30,
        "fill_notional": 0,
        "underlying_account": "Acc1",
        "fill_date_time": DateTime.utcnow(),
        "fill_id": "F2"
    })

