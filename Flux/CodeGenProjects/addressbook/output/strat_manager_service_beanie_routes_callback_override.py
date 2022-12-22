import os
import threading
import logging
import asyncio
from Flux.CodeGenProjects.addressbook.output.strat_manager_service_beanie_web_client import \
    create_order_limits_client as create_beanie_order_limits_client, \
    get_order_limits_client_ws as get_beanie_order_limits_client_ws, \
    get_all_order_limits_client_ws as get_all_beanie_order_limits_client_ws
from Flux.CodeGenProjects.addressbook.output.strat_manager_service_cache_web_client import \
    create_order_limits_client as create_cache_order_limits_client, \
    get_all_order_limits_client_ws as get_all_cache_order_limits_client_ws
from Flux.CodeGenProjects.addressbook.output.strat_manager_service_beanie_model import OrderLimitsBaseModel
from Flux.CodeGenProjects.addressbook.output.strat_manager_service_beanie_routes_callback import \
    StratManagerServiceBeanieRoutesCallback, OrderLimits, PortfolioLimits, PortfolioStatus


class WsGetOrderLimitsByIdCallback:
    def __call__(self, order_limits_base_model: OrderLimitsBaseModel):
        logging.debug(f"callback function: OrderLimits from DB: {order_limits_base_model}")


class StratManagerServiceRoutesBeanieCallbackOverride(StratManagerServiceBeanieRoutesCallback):

    def __init__(self):
        super().__init__()

    # intercept web calls via callback example
    def create_order_limits_pre(self, order_limits_obj: OrderLimits):
        logging.debug(f"OrderLimits From Ui: {order_limits_obj}")
        order_limits_obj.max_price_levels = 40
        logging.debug(f"OrderLimits pre test: {order_limits_obj}")

    def create_order_limits_post(self, order_limits_obj: OrderLimits):
        logging.debug(f"OrderLimits From Db: {order_limits_obj}")
        order_limits_obj.max_price_levels = 80
        logging.debug(f"OrderLimits Post test: {order_limits_obj}")

    # intercept web calls via callback and invoke another service on this very web server example
    def _http_create_order_limits_thread_func(self, obj):
        order_limits_obj = OrderLimitsBaseModel(id=obj.id, max_price_levels=2,
                                                max_basis_points=2, max_cb_order_notional=2, max_px_deviation=2)
        order_limits_obj = create_beanie_order_limits_client(order_limits_obj)
        logging.debug(f"Created OrderLimits obj from Another Document: {order_limits_obj}")

    def create_portfolio_limits_pre(self, portfolio_limits: PortfolioLimits):
        logging.debug(f"PortfolioLimits from UI: {portfolio_limits}")
        # To avoid deadlock triggering another thread to execute another document creation
        new_thread = threading.Thread(target=self._http_create_order_limits_thread_func, args=(portfolio_limits,), daemon=True)
        new_thread.start()

    def create_portfolio_limits_post(self, portfolio_limits: PortfolioLimits):
        logging.debug(f"PortfolioLimits From Db: {portfolio_limits}")
        portfolio_limits.max_cb_notional = 80
        logging.debug(f"PortfolioLimits Post test: {portfolio_limits}")

    # intercept web calls via callback and invoke another service on different web server example
    def create_portfolio_status_pre(self, portfolio_status_obj: PortfolioStatus):
        logging.debug(f"PortfolioStatus from UI: {portfolio_status_obj}")
        order_limits_obj = OrderLimitsBaseModel(id=portfolio_status_obj.id, max_price_levels=2,
                                                max_basis_points=2, max_cb_order_notional=2, max_px_deviation=2)
        # overriding port env var with port used in other server
        os.environ["PORT"] = "8080"
        order_limits_obj = create_cache_order_limits_client(order_limits_obj)
        # Reverting port env var with port this server is using
        os.environ["PORT"] = "8000"
        logging.debug(f"Created OrderLimits obj from Another Document: {order_limits_obj}")

    def create_portfolio_status_post(self, portfolio_status_obj: PortfolioStatus):
        logging.debug(f"PortfolioStatus From Db: {portfolio_status_obj}")
        portfolio_status_obj.overall_buy_notional = 80
        logging.debug(f"PortfolioStatus Post test: {portfolio_status_obj}")

    # intercept ws web calls via callback and invoke another service on this very web server example
    async def _ws_get_order_limits_by_id_thread_func(self, obj_id: int, ws_get_order_limits_by_id_callback):
        logging.debug("_ws_get_order_limits_by_id_thread_func: Connecting order_limits get_by_id ws:")
        await get_beanie_order_limits_client_ws(obj_id, ws_get_order_limits_by_id_callback)

    def read_by_id_ws_pair_strat_pre(self, obj_id: int):
        logging.debug(f"read_by_id_ws_pair_strat_pre: PairStrat id from UI: {obj_id}")
        ws_get_order_limits_by_id_callback: WsGetOrderLimitsByIdCallback = WsGetOrderLimitsByIdCallback()
        # running await function is different from running normal function in threading
        new_thread = threading.Thread(target=asyncio.run, args=(self._ws_get_order_limits_by_id_thread_func(obj_id, ws_get_order_limits_by_id_callback),), daemon=True)
        new_thread.start()

    def read_by_id_ws_pair_strat_post(self):
        logging.debug(f"closing pair_strat read ws in read_by_id_ws_pair_strat_post")

    # intercept ws web calls via callback and invoke another service on different web server example
    async def _ws_get_all_order_limits_thread_func(self, ws_get_order_limits_by_id_callback):
        logging.debug("_ws_get_order_limits_by_id_thread_func: Connecting another server order_limits get_all ws:")
        os.environ["PORT"] = "8080"
        await get_all_cache_order_limits_client_ws(ws_get_order_limits_by_id_callback)

    def read_all_ws_pair_strat_pre(self):
        logging.debug(f"triggered read_all_ws_pair_strat_pre")
        ws_get_order_limits_by_id_callback: WsGetOrderLimitsByIdCallback = WsGetOrderLimitsByIdCallback()
        # running await function is different from running normal function in threading
        new_thread = threading.Thread(target=asyncio.run, args=(
        self._ws_get_all_order_limits_thread_func(ws_get_order_limits_by_id_callback),), daemon=True)
        new_thread.start()
        os.environ["PORT"] = "8000"

    def read_all_ws_pair_strat_post(self):
        logging.debug(f"closing pair_strat read all ws in read_all_ws_pair_strat_post")
