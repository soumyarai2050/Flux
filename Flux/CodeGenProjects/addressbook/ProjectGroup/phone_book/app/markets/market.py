from socket import gethostname
from enum import auto
from pathlib import PurePath

from pendulum import DateTime
from fastapi_restful.enums import StrEnum

from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.in_market import INMarket

MARKETS_DATA_DIR = (
    PurePath(__file__).parent.parent.parent / "data"
)


class MarketID(StrEnum):
    MarketID_UNSPECIFIED = auto()
    IN = auto()


class Market:
    def __init__(self, market_id: MarketID = MarketID.IN):
        self.is_dev_env = True

        config_file_path = MARKETS_DATA_DIR / "config.yaml"
        config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))

        self.market_config_dict: Dict[any, any] = config_yaml_dict["market"]  # NOQA

        # controls invocation of Test Strat Code vs Actual Strat COde
        self.is_sanity_test_run: bool = is_sanity_test_run if (
            is_sanity_test_run := self.market_config_dict.get("is_sanity_test_run")) else False

        # allows outside bartering hour testing + opts barter_simulator as bartering link
        self.is_test_run: bool = is_test_run if (is_test_run :=  self.market_config_dict.get("is_test_run")) else False

        self.in_market = INMarket()
        self.market_id = market_id

    def is_non_bartering_time(self, market_id: MarketID | None = None, check_utc_time=DateTime.utcnow()) -> bool:
        return not self.is_bartering_time(market_id, check_utc_time)

    def is_bartering_time(self, market_id: MarketID | None = None, check_utc_time=DateTime.utcnow()) -> bool:
        # TODO get this via Market Data if MD provider has market session indicators
        if market_id is None:
            market_id = self.market_id
        return True

    def is_not_uat_nor_bartering_time(self, check_utc_time=DateTime.utcnow()):
        if self.is_uat():
            return False
        return self.is_non_bartering_time(market_id=None, check_utc_time=check_utc_time)

    def is_uat(self):
        return self.is_sanity_test_run or self.is_test_run or self.is_dev_env

    def is_bartering_session_not_started(self) -> bool:
        return False
