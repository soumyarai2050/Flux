import os

from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator

trade_simulator: TradeSimulator = TradeSimulator()


def get_trading_link() -> TradingLinkBase:
    return trade_simulator
