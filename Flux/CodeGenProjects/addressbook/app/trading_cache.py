from typing import Tuple

from Flux.CodeGenProjects.addressbook.app.strat_cache import StratCache
from Flux.CodeGenProjects.addressbook.app.ws_helper import *
from pendulum import DateTime


class TradingCache:

    def get_portfolio_status(self, date_time: DateTime | None = None) -> Tuple[PortfolioStatusBaseModel, DateTime] | None:
        if date_time is None or date_time < self._portfolio_status_update_date_time:
            return self._portfolio_status, self._portfolio_status_update_date_time
        else:
            return None

    def set_portfolio_status(self, portfolio_status: PortfolioStatusBaseModel) -> DateTime:
        self._portfolio_status = portfolio_status
        self._portfolio_status_update_date_time = DateTime.utcnow()
        return self._portfolio_status_update_date_time

    def get_order_limits(self, date_time: DateTime | None = None) -> Tuple[OrderLimitsBaseModel, DateTime] | None:
        if date_time is None or date_time < self._order_limits_update_date_time:
            return self._order_limits, self._order_limits_update_date_time
        else:
            return None

    def set_order_limits(self, order_limits: OrderLimitsBaseModel) -> DateTime:
        self._order_limits = order_limits
        self._order_limits_update_date_time = DateTime.utcnow()
        return self._order_limits_update_date_time

    def __init__(self):
        self._portfolio_status: PortfolioStatusBaseModel | None = None
        self._portfolio_status_update_date_time: DateTime = DateTime.utcnow()

        self._order_limits: OrderLimitsBaseModel | None = None
        self._order_limits_update_date_time: DateTime = DateTime.utcnow()
