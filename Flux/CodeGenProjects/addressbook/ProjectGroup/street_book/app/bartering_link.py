from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link_base import BarteringLinkBase
# from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.barter_simulator import BarterSimulator
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.log_barter_simulator import LogBarterSimulator
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID

config_dict = BarteringLinkBase.pair_strat_config_dict
market = Market(MarketID.IN)

# barter_simulator: BarterSimulator = BarterSimulator() if market.is_test_run else None
barter_simulator: LogBarterSimulator = LogBarterSimulator() if market.is_test_run else None


def get_bartering_link() -> BarteringLinkBase:
    # select configuration based implementation
    if market.is_test_run:
        return barter_simulator
    else:
        raise NotImplementedError
