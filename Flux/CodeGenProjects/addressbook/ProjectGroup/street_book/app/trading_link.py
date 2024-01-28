from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.trading_link_base import TradingLinkBase
# from Flux.CodeGenProjects.street_book.app.trade_simulator import TradeSimulator
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.log_trade_simulator import LogTradeSimulator

config_dict = TradingLinkBase.pair_strat_config_dict
is_test_run: bool = config_dict.get("is_test_run")

# trade_simulator: TradeSimulator = TradeSimulator() if is_test_run else None
trade_simulator: LogTradeSimulator = LogTradeSimulator() if is_test_run else None


def get_trading_link() -> TradingLinkBase:
    # select configuration based implementation
    if is_test_run:
        return trade_simulator
    else:
        raise NotImplementedError
