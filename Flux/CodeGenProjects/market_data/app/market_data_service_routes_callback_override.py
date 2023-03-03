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

    async def get_last_n_sec_total_qty_query_pre(self, last_trade_class_type: Type[LastTrade], symbol: str, last_n_sec: float):
        from Flux.CodeGenProjects.market_data.generated.market_data_service_routes import underlying_read_last_trade_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_last_n_sec_total_qty
        return await underlying_read_last_trade_http(get_last_n_sec_total_qty(symbol, last_n_sec))
