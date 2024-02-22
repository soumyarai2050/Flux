from pendulum import DateTime

# project imports
from Flux.CodeGenProjects.dept_book.generated.Pydentic.dept_book_service_model_imports import *
from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_routes_callback import \
    DeptBookServiceRoutesCallback
from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.dept_book_service_helper import *


class DeptBookServiceRoutesCallbackBaseNativeOverride(DeptBookServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        pass

    def app_launch_pre(self):
        self.port = dsb_port

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
        from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import get_vwap_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_vwap_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForVwap)
        return bar_data_projection_list

    async def get_vwap_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import get_vwap_projection_from_bar_data_agg_pipeline
        return get_vwap_projection_from_bar_data_filter_callable, get_vwap_projection_from_bar_data_agg_pipeline

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                        symbol: str, exch_id: str,
                                                                        start_date_time: DateTime | None = None,
                                                                        end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import (
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time,
                                                                         end_date_time),
            projection_model=BarDataProjectionContainerForVwapNVwapChange)
        return bar_data_projection_list

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import (
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)
        return (get_vwap_n_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_vwap_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                                 exch_id: str, start_date_time: DateTime | None = None,
                                                                 end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import get_vwap_change_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForVwapChange)
        return bar_data_projection_list

    async def get_vwap_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import get_vwap_change_projection_from_bar_data_agg_pipeline
        return (get_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                             exch_id: str, start_date_time: DateTime | None = None,
                                                             end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import get_premium_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_premium_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForPremium)
        return bar_data_projection_list

    async def get_premium_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import get_premium_projection_from_bar_data_agg_pipeline
        return get_premium_projection_from_bar_data_filter_callable, get_premium_projection_from_bar_data_agg_pipeline

    async def get_premium_n_premium_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                              symbol: str, exch_id: str,
                                                                              start_date_time: DateTime | None = None,
                                                                              end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import \
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time,
                                                                               end_date_time),
            projection_model=BarDataProjectionContainerForPremiumNPremiumChange)
        return bar_data_projection_list

    async def get_premium_n_premium_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import \
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline
        return (get_premium_n_premium_change_projection_from_bar_data_filter_callable,
                get_premium_n_premium_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                    symbol: str, exch_id: str,
                                                                    start_date_time: DateTime | None = None,
                                                                    end_date_time: DateTime | None = None):
        from Flux.CodeGenProjects.dept_book.generated.FastApi.dept_book_service_http_routes import \
            underlying_read_bar_data_http
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import \
            get_premium_change_projection_from_bar_data_agg_pipeline
        bar_data_projection_list = await underlying_read_bar_data_http(
            get_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_model=BarDataProjectionContainerForPremiumChange)
        return bar_data_projection_list

    async def get_premium_change_projection_from_bar_data_query_ws_pre(self):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.dept_book.app.aggregate import \
            get_premium_change_projection_from_bar_data_agg_pipeline
        return (get_premium_change_projection_from_bar_data_filter_callable,
                get_premium_change_projection_from_bar_data_agg_pipeline)


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

