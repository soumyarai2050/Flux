from typing import List, Type
import threading
import logging
import asyncio
from pendulum import DateTime
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import TopOfBookBaseModel, TopOfBook, BarData, BBO, TickByTickBidAsk
from Flux.CodeGenProjects.market_data.generated.market_data_service_routes_callback import MarketDataServiceRoutesCallback
from Flux.CodeGenProjects.pair_strat_engine.generated.strat_manager_service_beanie_model import StratBrief, \
    PairSideBrief, Security, Side, SecurityType

market_data_service_web_client_internal = MarketDataServiceWebClient()
market_data_service_web_client_external = MarketDataServiceWebClient(port=8080)


class MarketDataServiceRoutesCallbackOverride(MarketDataServiceRoutesCallback):

    def __init__(self):
        super().__init__()

    def _get_pair_side_brief_from_symbol(self, symbol: str):
        from Flux.CodeGenProjects.pair_strat_engine.generated.strat_manager_service_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_pair_side_brief_from_side
        pair_side_brief_objs = await underlying_read_strat_brief_http(get_pair_side_brief_from_side(symbol))

        if len(pair_side_brief_objs) == 1:
            pair_side_brief_obj = pair_side_brief_objs[0]
            return pair_side_brief_obj.pair_side_brief
        else:
            err_str = f"Multi Pair_Side_brief can't exist for single symbol, for symbol - {symbol}," \
                      f" received {pair_side_brief_objs}"
            logging.exception(err_str)
            raise Exception(err_str)

    def create_top_of_book_pre(self, top_of_book_obj: TopOfBook):
        from Flux.CodeGenProjects.pair_strat_engine.generated.strat_manager_service_routes import \
            underlying_create_strat_brief_http

        security = Security(sec_id=top_of_book_obj.symbol, security_type=SecurityType.TICKER)
        side = ""   # how to find side from top_of_bool object?
        pair_side_brief = PairSideBrief(security=security, side=side,
                                        allowed_px_by_max_basis_points=0,
                                        allowed_px_by_max_deviation=0,
                                        allowed_px_by_max_level=0,
                                        cb_allowed_max_px=0,
                                        consumable_open_orders=0,
                                        consumable_notional=0,
                                        consumable_open_notional=0,
                                        consumable_concentration=0,
                                        consumable_cxl_qty=0,
                                        consumable_participation_qty=0,
                                        consumable_residual=0,
                                        residual_qty=0,
                                        all_bkr_cxlled_qty=0,
                                        open_notional=0,
                                        open_qty=0,
                                        filled_notional=0,
                                        filled_qty=0,
                                        participation_period_order_qty_sum=0
                                        )