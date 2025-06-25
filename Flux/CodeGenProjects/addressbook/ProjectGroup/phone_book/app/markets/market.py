from socket import gethostname
from enum import auto
from pathlib import PurePath
from typing import Dict, List, Optional

from pendulum import DateTime
from fastapi_restful.enums import StrEnum

from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.in_market import INMarket

MARKETS_DATA_DIR = (
    PurePath(__file__).parent.parent.parent / "data"
)


class MarketID(StrEnum):
    MarketID_UNSPECIFIED = auto()
    IN = auto()


class Market:

    # Mapping of market identifiers to their respective classes
    MARKET_CLASSES = {
        MarketID.IN: INMarket
        # Additional markets can be added here as they are implemented
    }
    def __init__(self, market_ids: Optional[List[MarketID]] = None, primary_market_id: MarketID = MarketID.IN):
        self.is_dev_env = True

        config_file_path = MARKETS_DATA_DIR / "config.yaml"
        config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))

        self.market_config_dict: Dict[any, any] = config_yaml_dict["market"]  # NOQA

        # controls invocation of Test Plan Code vs Actual Plan COde
        self.is_sanity_test_run: bool = is_sanity_test_run if (
            is_sanity_test_run := self.market_config_dict.get("is_sanity_test_run")) else False

        # allows outside bartering hour testing + opts barter_simulator as bartering link
        self.is_test_run: bool = is_test_run if (is_test_run :=  self.market_config_dict.get("is_test_run")) else False
        self.primary_market_id = primary_market_id

        # self.in_market = INMarket()
        # self.market_id = market_id
        self.markets: Dict[MarketID, Market] = {}
        self._initialize_markets(market_ids)

    def _initialize_markets(self, market_ids: Optional[List[MarketID]]) -> None:
        init_markets = set(self.MARKET_CLASSES.keys()) if market_ids is None else set(market_ids)

        # Always ensure the primary market is initialized
        if self.primary_market_id not in init_markets:
            init_markets.add(self.primary_market_id)

        # Initialize each market and create direct attribute access
        for market_id in init_markets:
            if market_id in self.MARKET_CLASSES:
                market_instance = self.MARKET_CLASSES[market_id]()
                self.markets[market_id] = market_instance
                # Set direct attribute access (e.g., self.in_market)
                attr_name = f"{market_id.lower()}_market"
                setattr(self, attr_name, market_instance)

    def get_market(self, market_id: MarketID | None = None):
        if market_id is None:
            market_id = self.primary_market_id

        if market_id in self.markets:
            return self.markets[market_id]

        raise ValueError(f"Market {market_id} is not initialized")

    def is_non_bartering_time(self, market_id: MarketID | None = None, check_utc_time=DateTime.utcnow()) -> bool:
        return not self.is_bartering_time(market_id, check_utc_time)

    def is_bartering_time(self, market_id: MarketID | None = None, check_utc_time=DateTime.utcnow()) -> bool:
        # TODO get this via Market Data if MD provider has market session indicators
        return True

    def is_not_uat_nor_bartering_time(self, check_utc_time=DateTime.utcnow()):
        if self.is_uat():
            return False
        return self.is_non_bartering_time(market_id=None, check_utc_time=check_utc_time)

    def is_uat(self):
        return self.is_sanity_test_run or self.is_test_run or self.is_dev_env

    def is_bartering_session_not_started(self) -> bool:
        return False
