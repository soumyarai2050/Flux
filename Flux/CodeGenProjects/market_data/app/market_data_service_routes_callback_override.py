import logging
from pendulum import DateTime
from typing import Type
# project imports
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.pair_strat_engine.generated.strat_manager_service_web_client import StratManagerServiceWebClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_routes_callback import \
    MarketDataServiceRoutesCallback
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import *

market_data_service_web_client_internal = MarketDataServiceWebClient()
market_data_service_web_client_external = StratManagerServiceWebClient(port=8080)


class MarketDataServiceRoutesCallbackOverride(MarketDataServiceRoutesCallback):

    def __init__(self):
        super().__init__()

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        from Flux.CodeGenProjects.market_data.generated.market_data_service_routes import underlying_read_top_of_book_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_top_of_book_from_symbol
        return await underlying_read_top_of_book_http(get_top_of_book_from_symbol(symbol))

    async def get_last_n_sec_total_qty_query_pre(self,
                                                 last_sec_market_trade_vol_class_type: Type[LastSecMarketTradeVol],
                                                 buy_symbol: str, sell_symbol: str, last_n_sec: int):
        from Flux.CodeGenProjects.market_data.generated.market_data_service_routes import \
            underlying_read_last_trade_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_last_n_sec_total_qty
        buy_last_trade_obj_list = await underlying_read_last_trade_http(get_last_n_sec_total_qty(buy_symbol,
                                                                                                 last_n_sec))
        sell_last_trade_obj_list = await underlying_read_last_trade_http(get_last_n_sec_total_qty(sell_symbol,
                                                                                                  last_n_sec))
        last_sec_market_trade_vol = LastSecMarketTradeVol(buy_side_last_sec_trade_vol=buy_last_trade_obj_list[-1].market_trade_volume.participation_period_last_trade_qty_sum,
                                                          sell_side_last_sec_trade_vol=sell_last_trade_obj_list[-1].market_trade_volume.participation_period_last_trade_qty_sum)

        return [last_sec_market_trade_vol]
