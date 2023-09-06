import json
from typing import Type
# project imports
from Flux.CodeGenProjects.market_data.app.market_data_service_routes_callback_base_native_override import \
    MarketDataServiceRoutesCallbackBaseNativeOverride

from Flux.CodeGenProjects.market_data.generated.Pydentic.market_data_service_model_imports import *


class MarketDataServiceRoutesCallbackBeanieNativeOverride(MarketDataServiceRoutesCallbackBaseNativeOverride):

    def __init__(self):
        super().__init__()

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_top_of_book_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_objs_from_symbol
        return await underlying_read_top_of_book_http(get_objs_from_symbol(symbol))

    async def get_last_n_sec_total_qty_query_pre(self,
                                                 last_sec_market_trade_vol_class_type: Type[LastNSecMarketTradeVol],
                                                 symbol: str, last_n_sec: int) -> List[LastNSecMarketTradeVol]:
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_last_trade_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_last_n_sec_total_qty
        last_trade_obj_list = await underlying_read_last_trade_http(get_last_n_sec_total_qty(symbol, last_n_sec))
        last_n_sec_trade_vol = 0
        if last_trade_obj_list:
            last_n_sec_trade_vol = \
                last_trade_obj_list[-1].market_trade_volume.participation_period_last_trade_qty_sum

        return [LastNSecMarketTradeVol(last_n_sec_trade_vol=last_n_sec_trade_vol)]

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_symbol_overview_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_symbol_overview_from_symbol
        return await underlying_read_symbol_overview_http(get_symbol_overview_from_symbol(symbol))

    async def filtered_notify_tob_update_query_ws_pre(self):
        return tob_filter_callable

    async def get_bar_data_all_symbols_n_last_update_time_query_pre(self, bar_data_n_latest_update_date_time_class_type: Type[BarDataNLatestUpdateDateTime]):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_latest_bar_data_for_each_symbol
        bar_data_list = await underlying_read_bar_data_http(get_latest_bar_data_for_each_symbol())
        bar_data_n_latest_update_date_time = BarDataNLatestUpdateDateTime(symbol_n_last_update_datetime=[])
        for bar_data in bar_data_list:
            bar_data_n_latest_update_date_time.symbol_n_last_update_datetime.append(
                BarDataSymbolNLatestUpdateDateTime(symbol=bar_data.symbol_n_exch_id.symbol,
                                                   last_update_datetime=bar_data.start_time)
            )
        return [bar_data_n_latest_update_date_time]

    async def search_n_update_dash_query_pre(self, dash_class_type: Type[Dash], payload_dict: Dict[str, Any]):
        # To be implemented in main callback override file
        dash = payload_dict.get("dash")
        dash['rt_dash']["cb_leg"] = {"sec": {"sec_id": "check_cb_sec"}}
        dash['rt_dash']["eqt_leg"] = {"sec": {"sec_id": "check_eqt_sec"}}
        dash_obj = dash_class_type(**dash)
        return [dash_obj]

    async def get_vwap_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                          exch_id: str, start_date_time: DateTime | None = None,
                                                          end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_vwap_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_vwap_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForVwap)
        return bar_data_projection_list

    async def get_vwap_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.market_data.app.aggregate import get_vwap_projection_from_bar_data_agg_pipeline
        return get_vwap_projection_from_bar_data_filter_callable, get_vwap_projection_from_bar_data_agg_pipeline

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                        symbol: str, exch_id: str,
                                                                        start_date_time: DateTime | None = None,
                                                                        end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import (
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time,
                                                                         end_date_time),
            projection_model=BarDataProjectionContainerForVwapNVwapChange)
        return bar_data_projection_list

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.market_data.app.aggregate import (
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)
        return (get_vwap_n_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_vwap_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                                 exch_id: str, start_date_time: DateTime | None = None,
                                                                 end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_vwap_change_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForVwapChange)
        return bar_data_projection_list

    async def get_vwap_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.market_data.app.aggregate import get_vwap_change_projection_from_bar_data_agg_pipeline
        return (get_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                             exch_id: str, start_date_time: DateTime | None = None,
                                                             end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import get_premium_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_premium_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForPremium)
        return bar_data_projection_list

    async def get_premium_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.market_data.app.aggregate import get_premium_projection_from_bar_data_agg_pipeline
        return get_premium_projection_from_bar_data_filter_callable, get_premium_projection_from_bar_data_agg_pipeline

    async def get_premium_n_premium_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                              symbol: str, exch_id: str,
                                                                              start_date_time: DateTime | None = None,
                                                                              end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import \
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time,
                                                                               end_date_time),
            projection_model=BarDataProjectionContainerForPremiumNPremiumChange)
        return bar_data_projection_list

    async def get_premium_n_premium_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.market_data.app.aggregate import \
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline
        return (get_premium_n_premium_change_projection_from_bar_data_filter_callable,
                get_premium_n_premium_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                    symbol: str, exch_id: str,
                                                                    start_date_time: DateTime | None = None,
                                                                    end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.market_data.generated.FastApi.market_data_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.market_data.app.aggregate import \
            get_premium_change_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForPremiumChange)
        return bar_data_projection_list

    async def get_premium_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.market_data.app.aggregate import \
            get_premium_change_projection_from_bar_data_agg_pipeline
        return (get_premium_change_projection_from_bar_data_filter_callable,
                get_premium_change_projection_from_bar_data_agg_pipeline)


def tob_filter_callable(tob_obj_json_str, **kwargs):
    symbols = kwargs.get("symbols")
    tob_obj_json = json.loads(tob_obj_json_str)
    tob_symbol = tob_obj_json.get("symbol")
    if tob_symbol in symbols:
        return True
    return False


def get_vwap_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return True


def get_vwap_n_vwap_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return True


def get_vwap_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return True


def get_premium_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return True


def get_premium_n_premium_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return True


def get_premium_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return True
