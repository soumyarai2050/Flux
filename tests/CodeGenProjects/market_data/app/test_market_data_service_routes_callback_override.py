# Multi-stage tests all lower order tests serve as fixtures to higher order
# tests (result in DB serves as fixture to subsequent Tests)

# Test 1 - build the book test
# replay this to build market depth and partial top of the book
RawMarketDepthHistory = \
[]

# input:
# replay this to build rest of top of the book
TickBYTickAllLast = \
[
  {
    "_id": 1,
    "symbol": "CB_Sec_1",
    "tick_type": "BID",
    "time": "2023-02-10T07:35:24.878000",
    "px": 140,
    "qty": 50,
    "exchange": "SMART",
    "special_conditions": "string",
    "past_limit": False,
    "unreported": False,
    "last_n_sec_avg_px": 7000,
    "last_n_sec_total_qty": 50
  },
  {
    "_id": 2,
    "symbol": "EQT_Sec_1",
    "tick_type": "ASK",
    "time": "2023-02-10T07:35:24.878000",
    "px": 130,
    "qty": 30,
    "exchange": "SMART",
    "special_conditions": "string",
    "past_limit": False,
    "unreported": False,
    "last_n_sec_avg_px": 3900,
    "last_n_sec_total_qty": 30
  },
  {
    "_id": 3,
    "symbol": "EQT_Sec_1",
    "tick_type": "ASK",
    "time": "2023-02-10T07:35:24.878000",
    "px": 120,
    "qty": 50,
    "exchange": "SMART",
    "special_conditions": "string",
    "past_limit": False,
    "unreported": False,
    "last_n_sec_avg_px": 4950,
    "last_n_sec_total_qty": 80
  }
]


# Match this to validate expected behaviour
MarketDepth = \
[
  {
    "_id": 2,
    "symbol": "CB_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "BID",
    "px": 150,
    "qty": 60,
    "position": 0,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 9000,
    "cumulative_total_qty": 60
  },
  {
    "_id": 3,
    "symbol": "CB_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "BID",
    "px": 149,
    "qty": 50,
    "position": 1,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 8225,
    "cumulative_total_qty": 110
  },
  {
    "_id": 4,
    "symbol": "CB_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "BID",
    "px": 148,
    "qty": 80,
    "position": 2,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 9430,
    "cumulative_total_qty": 190
  },
  {
    "_id": 5,
    "symbol": "CB_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "ASK",
    "px": 152,
    "qty": 60,
    "position": 0,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 9120,
    "cumulative_total_qty": 60
  },
  {
    "_id": 6,
    "symbol": "CB_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "ASK",
    "px": 153,
    "qty": 50,
    "position": 1,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 8385,
    "cumulative_total_qty": 110
  },
  {
    "_id": 7,
    "symbol": "CB_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "ASK",
    "px": 154,
    "qty": 80,
    "position": 2,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 9696.666666666666,
    "cumulative_total_qty": 190
  },
  {
    "_id": 8,
    "symbol": "EQT_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "BID",
    "px": 140,
    "qty": 60,
    "position": 0,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 8400,
    "cumulative_total_qty": 60
  },
  {
    "_id": 9,
    "symbol": "EQT_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "BID",
    "px": 139,
    "qty": 80,
    "position": 1,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 9760,
    "cumulative_total_qty": 140
  },
  {
    "_id": 10,
    "symbol": "EQT_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "BID",
    "px": 138,
    "qty": 50,
    "position": 2,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 8806.666666666666,
    "cumulative_total_qty": 190
  },
  {
    "_id": 11,
    "symbol": "EQT_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "ASK",
    "px": 145,
    "qty": 50,
    "position": 0,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 7250,
    "cumulative_total_qty": 50
  },
  {
    "_id": 12,
    "symbol": "EQT_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "ASK",
    "px": 145,
    "qty": 23,
    "position": 1,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 5292.5,
    "cumulative_total_qty": 73
  },
  {
    "_id": 13,
    "symbol": "EQT_Sec_1",
    "time": "2023-02-10T06:46:54.488000",
    "side": "ASK",
    "px": 147,
    "qty": 70,
    "position": 2,
    "market_maker": "string",
    "is_smart_depth": False,
    "cumulative_avg_px": 6958.333333333333,
    "cumulative_total_qty": 143
  }
]
# Match this to validate expected behaviour
TopOfBook = \
[
  {
    "_id": "63e6023856bc3b2c81cd88b7",
    "symbol": "EQT_Sec_1",
    "bid_quote": {
      "px": 0,
      "qty": 0,
      "last_update_date_time": "2023-02-10T06:37:01.706000"
    },
    "ask_quote": {
      "px": 150,
      "qty": 60,
      "last_update_date_time": "2023-02-10T06:38:01.706000"
    },
    "last_trade": {
      "px": 150,
      "qty": 60,
      "last_update_date_time": "2023-02-10T06:38:01.706000"
    },
    "last_update_date_time": "2023-02-10T06:38:01.706000"
  }
]

# Test 2 - Pair Strat App launch test
# Match this to validate expected behaviour
OrderLimits = \
[
  {
    "_id": 1,
    "max_basis_points": 150,
    "max_px_deviation": 50,
    "max_px_levels": 80,
    "max_order_qty": 90,
    "max_order_notional": 6000
  }
]

PairSideMarketDataBrief = \
[] # TODO DATA ??


# Test 3 - validate pair strat creation
# populate only primary params
PairStrat = \
[
  {
    "_id": 2,
    "last_active_date_time": "2023-02-08T19:28:07.042000",
    "frequency": 8,
    "pair_strat_params": {
      "strat_leg1": {
        "exch_id": "string",
        "sec": {
          "sec_id": "CB_Sec_1",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "side": "BUY"
      },
      "strat_leg2": {
        "exch_id": "string",
        "sec": {
          "sec_id": "EQT_Sec_1",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "side": "SELL"
      },
      "exch_response_max_seconds": 0,
      "common_premium_percentage": 0,
      "hedge_ratio": 0
    },
    "strat_status": {
      "strat_state": "StratState_UNSPECIFIED",
      "total_buy_qty": 120,
      "total_sell_qty": 50,
      "total_order_qty": 170,
      "total_open_buy_qty": 10,
      "total_open_sell_qty": 10,
      "avg_open_buy_px": 100,
      "avg_open_sell_px": 140,
      "total_open_buy_notional": 1000,
      "total_open_sell_notional": 1400,
      "total_open_exposure": -400,
      "total_fill_buy_qty": 80,
      "total_fill_sell_qty": 40,
      "avg_fill_buy_px": 90,
      "avg_fill_sell_px": 90,
      "total_fill_buy_notional": 7200,
      "total_fill_sell_notional": 3600,
      "total_fill_exposure": 3600,
      "total_cxl_buy_qty": 30,
      "total_cxl_sell_qty": 0,
      "avg_cxl_buy_px": 90,
      "avg_cxl_sell_px": 0,
      "total_cxl_buy_notional": 2700,
      "total_cxl_sell_notional": 0,
      "total_cxl_exposure": 2700,
      "average_premium": 0,
      "residual": {
        "security": {
          "sec_id": "string",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "max_residual_notional": 0
      },
      "balance_notional": 0,
      "strat_alerts": []
    },
    "strat_limits": {
      "max_open_orders_per_side": 100,
      "max_cb_notional": 8000,
      "max_open_cb_notional": 7000,
      "max_net_filled_notional": 3000,
      "max_concentration": 2000,
      "limit_up_down_volume_participation_rate": 30,
      "cancel_rate": {
        "max_cancel_rate": 20,
        "applicable_period_seconds": 10
      },
      "market_trade_volume_participation": {
        "max_participation_rate": 40,
        "applicable_period_seconds": 8
      },
      "market_depth": {
        "participation_rate": 25,
        "depth_levels": 10
      },
      "residual_restriction": {
        "max_residual": 2000,
        "residual_mark_seconds": 9
      },
      "eligible_brokers": [
        {
          "bkr_disable": True,
          "sec_positions": [
            {
              "security": {
                "sec_id": "string",
                "sec_type": "SEC_TYPE_UNSPECIFIED"
              },
              "positions": [
                {
                  "pos_disable": True,
                  "type": "POS_TYPE_UNSPECIFIED",
                  "available_size": 0,
                  "allocated_size": 0,
                  "consumed_size": 0,
                  "acquire_cost": 0,
                  "incurred_cost": 0,
                  "carry_cost": 0,
                  "priority": 0,
                  "premium_percentage": 0
                }
              ]
            }
          ],
          "broker": "string",
          "bkr_priority": 0
        }
      ]
    }
  }
]
# Match this to validate expected behaviour
StratBrief = \
[
  {
    "_id": 0,
    "pair_side_brief": [
      {
        "security": {
          "sec_id": "EQT_Sec_1",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "side": "SELL",
        "last_update_date_time": "2023-02-10T08:58:59.351000",
        "allowed_px_by_max_basis_points": 0,
        "allowed_px_by_max_deviation": 0,
        "allowed_px_by_max_level": 0,
        "allowed_max_px": 0,
        "consumable_open_orders": 0,
        "consumable_notional": 0,
        "consumable_open_notional": 0,
        "consumable_concentration": 0,
        "participation_period_order_qty_sum": 0,
        "consumable_cxl_qty": 0,
        "consumable_participation_qty": 0,
        "residual_qty": 0,
        "consumable_residual": 0,
        "all_bkr_cxlled_qty": 0,
        "open_notional": 0,
        "open_qty": 0,
        "filled_notional": 0,
        "filled_qty": 0
      },
      {
        "security": {
          "sec_id": "CB_Sec_1",
          # "sec_type": null
        },
        "side": "BUY",
        "last_update_date_time": "2023-02-10T09:01:26.274000",
        "allowed_px_by_max_basis_points": 91.35,
        "allowed_px_by_max_deviation": 150,
        "allowed_px_by_max_level": 148,
        # "allowed_max_px": null,
        "consumable_open_orders": 90,
        "consumable_notional": 300,
        "consumable_open_notional": 7500,
        "consumable_concentration": -5700,
        "participation_period_order_qty_sum": 80,
        "consumable_cxl_qty": -29.94,
        "consumable_participation_qty": -73.6,
        "residual_qty": 0,
        "consumable_residual": 0,
        "all_bkr_cxlled_qty": 30,
        "open_notional": 500,
        "open_qty": 10,
        "filled_notional": 7200,
        "filled_qty": 80
      }
    ],
    "consumable_nett_filled_notional": 0
  }
]
# Match this to validate expected behaviour
SymbolSideSnapshot = \
[
  {
    "_id": 2,
    "security": {
      "sec_id": "CB_Sec_1",
      "sec_type": "SEC_TYPE_UNSPECIFIED"
    },
    "side": "BUY",
    "avg_px": 90,
    "total_qty": 120,
    "total_filled_qty": 80,
    "avg_fill_px": 90,
    "total_fill_notional": 7200,
    "last_update_fill_qty": 40,
    "last_update_fill_px": 40,
    "total_cxled_qty": 30,
    "avg_cxled_px": 90,
    "total_cxled_notional": 2700,
    "last_update_date_time": "2023-02-08T19:26:19.541000",
    "frequency": 2
  },
  {
    "_id": 3,
    "security": {
      "sec_id": "EQT_Sec_1",
      "sec_type": "SEC_TYPE_UNSPECIFIED"
    },
    "side": "SELL",
    "avg_px": 100,
    "total_qty": 50,
    "total_filled_qty": 40,
    "avg_fill_px": 90,
    "total_fill_notional": 3600,
    "last_update_fill_qty": 40,
    "last_update_fill_px": 40,
    "total_cxled_qty": 0,
    "avg_cxled_px": 0,
    "total_cxled_notional": 0,
    "last_update_date_time": "2023-02-08T19:28:07.031000",
    "frequency": 1
  }
]

portfolio_status = []

# Test 4
# Input
OrderJournal = \
[
  {
    "_id": 6,
    "order": {
      "order_id": "o1",
      "security": {
        "sec_id": "CB_Sec_1",
        "sec_type": "SEC_TYPE_UNSPECIFIED"
      },
      "side": "BUY",
      "px": 100,
      "qty": 50,
      "order_notional": 5000,
      "underlying_account": "string",
      "text": [
        "string"
      ]
    },
    "order_event_date_time": "2023-02-08T19:22:35.278000",
    "order_event": "OE_NEW"
  },
  {
    "_id": 7,
    "order": {
      "order_id": "o1",
      "security": {
        "sec_id": "CB_Sec_1",
        "sec_type": "SEC_TYPE_UNSPECIFIED"
      },
      "side": "BUY",
      "px": 100,
      "qty": 50,
      "order_notional": 5000,
      "underlying_account": "string",
      "text": [
        "string"
      ]
    },
    "order_event_date_time": "2023-02-08T19:22:35.278000",
    "order_event": "OE_ACK"
  },
  {
    "_id": 8,
    "order": {
      "order_id": "o2",
      "security": {
        "sec_id": "CB_Sec_1",
        "sec_type": "SEC_TYPE_UNSPECIFIED"
      },
      "side": "BUY",
      "px": 90,
      "qty": 70,
      "order_notional": 6300,
      "underlying_account": "string",
      "text": [
        "string"
      ]
    },
    "order_event_date_time": "2023-02-08T19:22:35.278000",
    "order_event": "OE_NEW"
  },
  {
    "_id": 9,
    "order": {
      "order_id": "o2",
      "security": {
        "sec_id": "CB_Sec_1",
        "sec_type": "SEC_TYPE_UNSPECIFIED"
      },
      "side": "BUY",
      "px": 90,
      "qty": 70,
      "order_notional": 6300,
      "underlying_account": "string",
      "text": [
        "string"
      ]
    },
    "order_event_date_time": "2023-02-08T19:22:35.278000",
    "order_event": "OE_ACK"
  },
  {
    "_id": 10,
    "order": {
      "order_id": "o2",
      "security": {
        "sec_id": "CB_Sec_1",
        "sec_type": "SEC_TYPE_UNSPECIFIED"
      },
      "side": "BUY",
      "px": 90,
      "qty": 70,
      "order_notional": 6300,
      "underlying_account": "string",
      "text": [
        "string"
      ]
    },
    "order_event_date_time": "2023-02-08T19:22:35.278000",
    "order_event": "OE_CXL_ACK"
  },
  {
    "_id": 11,
    "order": {
      "order_id": "o3",
      "security": {
        "sec_id": "EQT_Sec_1",
        "sec_type": "SEC_TYPE_UNSPECIFIED"
      },
      "side": "SELL",
      "px": 100,
      "qty": 50,
      "order_notional": 5000,
      "underlying_account": "string",
      "text": [
        "string"
      ]
    },
    "order_event_date_time": "2023-02-08T19:22:35.278000",
    "order_event": "OE_NEW"
  }
]

FillsJournal = \
[
  {
    "_id": 3,
    "order_id": "o1",
    "fill_px": 90,
    "fill_qty": 40,
    "fill_notional": 3600,
    "underlying_account": "string",
    "fill_date_time": "2023-02-08T10:04:18.141000",
    "fill_id": "string"
  },
  {
    "_id": 4,
    "order_id": "o2",
    "fill_px": 90,
    "fill_qty": 40,
    "fill_notional": 3600,
    "underlying_account": "string",
    "fill_date_time": "2023-02-08T10:04:18.141000",
    "fill_id": "string"
  },
  {
    "_id": 5,
    "order_id": "o3",
    "fill_px": 90,
    "fill_qty": 40,
    "fill_notional": 3600,
    "underlying_account": "string",
    "fill_date_time": "2023-02-08T10:04:18.141000",
    "fill_id": "string"
  }
]


# outputs - # Match these to validate expected behaviour

# OrderSnapshot
# TODO??

SymbolSideSnapshot = \
[
  {
    "_id": 2,
    "security": {
      "sec_id": "CB_Sec_1",
      "sec_type": "SEC_TYPE_UNSPECIFIED"
    },
    "side": "BUY",
    "avg_px": 90,
    "total_qty": 120,
    "total_filled_qty": 80,
    "avg_fill_px": 90,
    "total_fill_notional": 7200,
    "last_update_fill_qty": 40,
    "last_update_fill_px": 40,
    "total_cxled_qty": 30,
    "avg_cxled_px": 90,
    "total_cxled_notional": 2700,
    "last_update_date_time": "2023-02-08T19:26:19.541000",
    "frequency": 2
  },
  {
    "_id": 3,
    "security": {
      "sec_id": "EQT_Sec_1",
      "sec_type": "SEC_TYPE_UNSPECIFIED"
    },
    "side": "SELL",
    "avg_px": 100,
    "total_qty": 50,
    "total_filled_qty": 40,
    "avg_fill_px": 90,
    "total_fill_notional": 3600,
    "last_update_fill_qty": 40,
    "last_update_fill_px": 40,
    "total_cxled_qty": 0,
    "avg_cxled_px": 0,
    "total_cxled_notional": 0,
    "last_update_date_time": "2023-02-08T19:28:07.031000",
    "frequency": 1
  }
]

StratBrief = \
[
  {
    "_id": 0,
    "pair_side_brief": [
      {
        "security": {
          "sec_id": "EQT_Sec_1",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "side": "SELL",
        "last_update_date_time": "2023-02-10T08:58:59.351000",
        "allowed_px_by_max_basis_points": 0,
        "allowed_px_by_max_deviation": 0,
        "allowed_px_by_max_level": 0,
        "allowed_max_px": 0,
        "consumable_open_orders": 0,
        "consumable_notional": 0,
        "consumable_open_notional": 0,
        "consumable_concentration": 0,
        "participation_period_order_qty_sum": 0,
        "consumable_cxl_qty": 0,
        "consumable_participation_qty": 0,
        "residual_qty": 0,
        "consumable_residual": 0,
        "all_bkr_cxlled_qty": 0,
        "open_notional": 0,
        "open_qty": 0,
        "filled_notional": 0,
        "filled_qty": 0
      },
      {
        "security": {
          "sec_id": "CB_Sec_1",
          # "sec_type": null
        },
        "side": "BUY",
        "last_update_date_time": "2023-02-10T09:01:26.274000",
        "allowed_px_by_max_basis_points": 91.35,
        "allowed_px_by_max_deviation": 150,
        "allowed_px_by_max_level": 148,
        # "allowed_max_px": null,
        "consumable_open_orders": 90,
        "consumable_notional": 300,
        "consumable_open_notional": 7500,
        "consumable_concentration": -5700,
        "participation_period_order_qty_sum": 80,
        "consumable_cxl_qty": -29.94,
        "consumable_participation_qty": -73.6,
        "residual_qty": 0,
        "consumable_residual": 0,
        "all_bkr_cxlled_qty": 30,
        "open_notional": 500,
        "open_qty": 10,
        "filled_notional": 7200,
        "filled_qty": 80
      }
    ],
    "consumable_nett_filled_notional": 0
  }
]

# TODO with computed values updated
PairStrat = \
[
  {
    "_id": 2,
    "last_active_date_time": "2023-02-08T19:28:07.042000",
    "frequency": 8,
    "pair_strat_params": {
      "strat_leg1": {
        "exch_id": "string",
        "sec": {
          "sec_id": "CB_Sec_1",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "side": "BUY"
      },
      "strat_leg2": {
        "exch_id": "string",
        "sec": {
          "sec_id": "EQT_Sec_1",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "side": "SELL"
      },
      "exch_response_max_seconds": 0,
      "common_premium_percentage": 0,
      "hedge_ratio": 0
    },
    "strat_status": {
      "strat_state": "StratState_UNSPECIFIED",
      "total_buy_qty": 120,
      "total_sell_qty": 50,
      "total_order_qty": 170,
      "total_open_buy_qty": 10,
      "total_open_sell_qty": 10,
      "avg_open_buy_px": 100,
      "avg_open_sell_px": 140,
      "total_open_buy_notional": 1000,
      "total_open_sell_notional": 1400,
      "total_open_exposure": -400,
      "total_fill_buy_qty": 80,
      "total_fill_sell_qty": 40,
      "avg_fill_buy_px": 90,
      "avg_fill_sell_px": 90,
      "total_fill_buy_notional": 7200,
      "total_fill_sell_notional": 3600,
      "total_fill_exposure": 3600,
      "total_cxl_buy_qty": 30,
      "total_cxl_sell_qty": 0,
      "avg_cxl_buy_px": 90,
      "avg_cxl_sell_px": 0,
      "total_cxl_buy_notional": 2700,
      "total_cxl_sell_notional": 0,
      "total_cxl_exposure": 2700,
      "average_premium": 0,
      "residual": {
        "security": {
          "sec_id": "string",
          "sec_type": "SEC_TYPE_UNSPECIFIED"
        },
        "max_residual_notional": 0
      },
      "balance_notional": 0,
      "strat_alerts": []
    },
    "strat_limits": {
      "max_open_orders_per_side": 100,
      "max_cb_notional": 8000,
      "max_open_cb_notional": 7000,
      "max_net_filled_notional": 3000,
      "max_concentration": 2000,
      "limit_up_down_volume_participation_rate": 30,
      "cancel_rate": {
        "max_cancel_rate": 20,
        "applicable_period_seconds": 10
      },
      "market_trade_volume_participation": {
        "max_participation_rate": 40,
        "applicable_period_seconds": 8
      },
      "market_depth": {
        "participation_rate": 25,
        "depth_levels": 10
      },
      "residual_restriction": {
        "max_residual": 2000,
        "residual_mark_seconds": 9
      },
      "eligible_brokers": [
        {
          "bkr_disable": True,
          "sec_positions": [
            {
              "security": {
                "sec_id": "string",
                "sec_type": "SEC_TYPE_UNSPECIFIED"
              },
              "positions": [
                {
                  "pos_disable": True,
                  "type": "POS_TYPE_UNSPECIFIED",
                  "available_size": 0,
                  "allocated_size": 0,
                  "consumed_size": 0,
                  "acquire_cost": 0,
                  "incurred_cost": 0,
                  "carry_cost": 0,
                  "priority": 0,
                  "premium_percentage": 0
                }
              ]
            }
          ],
          "broker": "string",
          "bkr_priority": 0
        }
      ]
    }
  }
]

StratBrief = \
[]