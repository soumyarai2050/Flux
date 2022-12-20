import os
import threading
import logging
from Flux.CodeGenProjects.pair_strat_engine.output.strat_manager_service_beanie_web_client import \
    create_order_limits_client as create_beanie_order_limits_client
from Flux.CodeGenProjects.pair_strat_engine.output.strat_manager_service_cache_web_client import \
    create_order_limits_client as create_cache_order_limits_client
from Flux.CodeGenProjects.pair_strat_engine.output.strat_manager_service_beanie_model import OrderLimitsBaseModel
from Flux.CodeGenProjects.pair_strat_engine.output.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback, OrderLimitsType, PortfolioLimitsType, PortfolioStatusType


class StratManagerServiceRoutesCallbackOverride(StratManagerServiceRoutesCallback):

    def __init__(self):
        super().__init__()

    # intercept web calls via callback example
    def create_order_limits_pre(self, order_limits_obj: OrderLimitsType):
        print("OrderLimits From Ui: ", order_limits_obj)
        logging.debug(f"OrderLimits From Ui: {order_limits_obj}")
        order_limits_obj.max_price_levels = 40
        print(f"OrderLimits pre test: {order_limits_obj}")
        logging.debug(f"OrderLimits pre test: {order_limits_obj}")

    def create_order_limits_post(self, order_limits_obj: OrderLimitsType):
        print("OrderLimits From Db: ", str(order_limits_obj))
        logging.debug(f"OrderLimits From Db: {order_limits_obj}")
        order_limits_obj.max_price_levels = 80
        print(f"OrderLimits Post test: {order_limits_obj}")
        logging.debug(f"OrderLimits Post test: {order_limits_obj}")

    # intercept web calls via callback and invoke another service on this very web server example
    def _create_order_limits_thread_func(self, obj_id: int):
        order_limits_obj = OrderLimitsBaseModel(id=obj_id, max_price_levels=2,
                                                max_basis_points=2, max_cb_order_notional=2, max_px_deviation=2)
        order_limits_obj = create_beanie_order_limits_client(order_limits_obj)
        print("Created OrderLimits obj from Another Document: ", order_limits_obj)
        logging.debug(f"Created OrderLimits obj from Another Document: {order_limits_obj}")

    def create_portfolio_limits_pre(self, portfolio_limits: PortfolioLimitsType):
        print("PortfolioLimits from UI: ", portfolio_limits)
        logging.debug(f"PortfolioLimits from UI: {portfolio_limits}")
        # To avoid deadlock triggering another thread to execute another document creation
        new_thread = threading.Thread(target=self._create_order_limits_thread_func, args=(portfolio_limits.id,), daemon=True)
        new_thread.start()

    def create_portfolio_limits_post(self, portfolio_limits: PortfolioLimitsType):
        print("PortfolioLimits From Db: ", str(portfolio_limits))
        logging.debug(f"PortfolioLimits From Db: {portfolio_limits}")
        portfolio_limits.max_cb_notional = 80
        print("PortfolioLimits Post test: ", str(portfolio_limits))
        logging.debug(f"PortfolioLimits Post test: {portfolio_limits}")

    # intercept web calls via callback and invoke another service on different web server example
    def create_portfolio_status_pre(self, portfolio_status_obj: PortfolioStatusType):
        print("PortfolioStatus from UI: ", portfolio_status_obj)
        logging.debug(f"PortfolioStatus from UI: {portfolio_status_obj}")
        order_limits_obj = OrderLimitsBaseModel(id=portfolio_status_obj.id, max_price_levels=2,
                                                max_basis_points=2, max_cb_order_notional=2, max_px_deviation=2)
        # overriding port env var with port used in other server
        os.environ["PORT"] = "8080"
        order_limits_obj = create_cache_order_limits_client(order_limits_obj)
        print("Created OrderLimits obj from Another Document: ", order_limits_obj)
        # Reverting port env var with port this server is using
        os.environ["PORT"] = "8000"
        logging.debug(f"Created OrderLimits obj from Another Document: {order_limits_obj}")

    def create_portfolio_status_post(self, portfolio_status_obj: PortfolioStatusType):
        print("PortfolioStatus From Db: ", str(portfolio_status_obj))
        logging.debug(f"PortfolioStatus From Db: {portfolio_status_obj}")
        portfolio_status_obj.overall_buy_notional = 80
        print("PortfolioStatus Post test: ", str(portfolio_status_obj))
        logging.debug(f"PortfolioStatus Post test: {portfolio_status_obj}")
