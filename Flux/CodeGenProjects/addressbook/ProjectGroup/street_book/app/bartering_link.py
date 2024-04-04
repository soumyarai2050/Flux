from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link_base import BarteringLinkBase
# from Flux.CodeGenProjects.street_book.app.barter_simulator import BarterSimulator
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.log_barter_simulator import LogBarterSimulator

config_dict = BarteringLinkBase.pair_strat_config_dict
is_test_run: bool = config_dict.get("is_test_run")

# barter_simulator: BarterSimulator = BarterSimulator() if is_test_run else None
barter_simulator: LogBarterSimulator = LogBarterSimulator() if is_test_run else None


def get_bartering_link() -> BarteringLinkBase:
    # select configuration based implementation
    if is_test_run:
        return barter_simulator
    else:
        raise NotImplementedError
