# Python imports
import logging
import os
from pathlib import PurePath
from decimal import Decimal
from pendulum import DateTime
from typing import Dict

# 3rd party module imports
from ibapi.contract import Contract
from ibapi.common import TickerId

# Local project imports
from Flux.CodeGenProjects.market_data.app.ib_api_client import IbApiClient
from FluxPythonUtils.scripts.utility_functions import yaml_loader, configure_logger

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import MarketDepthBaseModel, \
    RawMarketDepthHistoryBaseModel


class StoreDepthMarketDataClient(IbApiClient):
    project_root_path = PurePath(__file__).parent.parent
    log_dir_path = project_root_path / "generated" / "logs"
    config_file_path = project_root_path / "misc" / "config.yaml"
    config_yaml = yaml_loader(str(config_file_path))

    @staticmethod
    def get_side_str_from_side_int(side_int: int):
        """
        Converts received side integer to side string
        """
        match side_int:
            case 0:
                return "ASK"
            case 1:
                return "BID"

    @staticmethod
    def get_side_str_to_side_int(side: str):
        """
        Converts received side string to side integer as received from ibapi
        """
        match side:
            case "ASK":
                return 0
            case "BID":
                return 1

    def __init__(self, config_yaml: Dict = None, preserve_history: bool = True):
        if config_yaml is None:
            config_yaml = self.config_yaml
        required_config_data_keys = ["num_rows", "is_smart_depth"]
        super().__init__(config_yaml, required_config_data_keys)
        self.preserve_history = preserve_history
        self.num_rows: int = config_yaml["num_rows"]  # sample: 10
        self.is_smart_depth: bool = config_yaml["is_smart_depth"]  # sample: False
        self.market_data_service_web_client: MarketDataServiceWebClient = MarketDataServiceWebClient()
        self.__pos_side_sym_to_id_dict: Dict[str, int] = {}

    def get_ticker_id_from_symbol(self, symbol: str):
        for idx, contract in enumerate(self.contracts):
            if contract.symbol == symbol:
                return idx
        else:
            err_str = f"Contract with symbol - {symbol} not found in list of contracts"
            logging.exception(err_str)
            raise ValueError(err_str)

    def nextValidId(self, order_id: TickerId):
        """
        Requests the contract's market depth (order book). Note this request must be
        direct-routed to an exchange and not smart-routed. The number of simultaneous
        market depth requests allowed in an account is calculated based on a formula
        that looks at an accounts' equity, commissions, and quote booster packs.

        reqId:TickerId - The ticker id. Must be a unique value. When the market
            depth data returns, it will be identified by this tag. This is
            also used when canceling the market depth
        contract:Contact - This structure contains a description of the contract
            for which market depth data is being requested.
        numRows:int - Specifies the count of market depth rows to display.
        isSmartDepth:bool - specifies SMART depth request
        """
        self.reqMarketDataType(StoreDepthMarketDataClient.live_market_data)
        contract: Contract
        for idx, contract in enumerate(self.contracts):
            self.reqMktDepth(idx, contract, self.num_rows, self.is_smart_depth, [])

    def error(self, req_id: TickerId, error_code: int, error_string: str, advanced_order_reject_json=""):
        logging.debug(f"Error: , {req_id}, {error_code}, {error_string}")

    def _update_mkt_depth(self, operation: int, market_depth_base_model: MarketDepthBaseModel):
        match operation:
            case 0:
                # operation 0: Insert
                self.market_data_service_web_client.create_market_depth_client(market_depth_base_model)
            case 1:
                # operation 1: Update
                self.market_data_service_web_client.put_market_depth_client(market_depth_base_model)
            case 2:
                # operation 2: Delete
                logging.debug(f"{market_depth_base_model}: received with operation code 2(Delete)")

    def _get_document_id_value(self, ticker_id: TickerId, side: int, position: int):
        """
        Returns Document ID assigned to document according to its side(Ask or Bid) and number of required levels
        to make use of single collection for levels of both Bid and Ask
        """
        symbol = self.contracts[ticker_id].symbol
        if (stored_id := self.__pos_side_sym_to_id_dict.get(f"{position}_{side}_{symbol}")) is not None:
            return stored_id
        else:
            if self.__pos_side_sym_to_id_dict.values():
                last_max_id = max(self.__pos_side_sym_to_id_dict.values())
            else:
                last_max_id = 0
            self.__pos_side_sym_to_id_dict[f"{position}_{side}_{symbol}"] = last_max_id + 1
            return last_max_id + 1

    # Usage and difference of updateMktDepth and updateMktDepthL2 callbacks is mentioned on MarketMaker or Exchange
    # section of https://interactivebrokers.github.io/tws-api/market_depth.html
    def updateMktDepth(self, ticker_id: TickerId, position: int, operation: int, side: int, price: float,
                       size: Decimal):
        # forcing Decimal Size to Int as required by API
        # TODO - we don't need this call in simulated mode via test case - conditional(ize) ?
        super().updateMktDepth(ticker_id, position, operation, side, price, size)
        current_time = DateTime.utcnow()
        # market_maker and is_smart_depth fields of MarketDepthBaseModel skipped being optional
        market_depth_base_model = MarketDepthBaseModel(id=self._get_document_id_value(ticker_id, side, position),
                                                       symbol=self.contracts[ticker_id].symbol, time=current_time,
                                                       side=self.get_side_str_from_side_int(side), px=price,
                                                       qty=size, position=position)
        self._update_mkt_depth(operation, market_depth_base_model)
        logging.debug(f"Adding {market_depth_base_model} in MarketDepth collection")

        if self.preserve_history:
            raw_market_depth_history_base_model = \
                RawMarketDepthHistoryBaseModel(symbol=self.contracts[ticker_id].symbol, time=current_time,
                                               position=position, operation=operation,
                                               side=self.get_side_str_from_side_int(side),
                                               px=price, qty=size)
            self.market_data_service_web_client.create_raw_market_depth_history_client(
                raw_market_depth_history_base_model)
            logging.debug(f"Adding {raw_market_depth_history_base_model} in MarketDepthHistory collection")

    def updateMktDepthL2(self, ticker_id: TickerId, position: int, market_maker: str, operation: int, side: int,
                         price: float, size: Decimal, is_smart_depth: bool):
        # forcing Decimal Size to Int as required by API
        super().updateMktDepthL2(ticker_id, position, market_maker, operation, side,
                                 price, size, is_smart_depth)
        current_time = DateTime.utcnow()
        market_depth_base_model = MarketDepthBaseModel(id=self._get_document_id_value(ticker_id, side, position),
                                                       symbol=self.contracts[ticker_id].symbol, time=current_time,
                                                       side=self.get_side_str_from_side_int(side), px=price,
                                                       position=position, qty=size, market_maker=market_maker,
                                                       is_smart_depth=is_smart_depth)
        logging.debug(f"Adding {market_depth_base_model} in MarketDepth collection")

        if self.preserve_history:
            raw_market_depth_history_base_model = \
                RawMarketDepthHistoryBaseModel(symbol=self.contracts[ticker_id].symbol, time=current_time,
                                               position=position, operation=operation,
                                               side=self.get_side_str_from_side_int(side),
                                               px=price, qty=size, market_maker=market_maker,
                                               is_smart_depth=is_smart_depth)
            self.market_data_service_web_client.create_raw_market_depth_history_client(
                raw_market_depth_history_base_model)
            logging.debug(f"Adding {raw_market_depth_history_base_model} in MarketDepthHistory collection")


if __name__ == "__main__":
    def main():
        configure_logger(StoreDepthMarketDataClient.config_yaml["log_level"],
                         str(StoreDepthMarketDataClient.log_dir_path))

        ib_client = StoreDepthMarketDataClient()
        ib_client.setServerLogLevel(StoreDepthMarketDataClient.log_lvl_detail)

        host = StoreDepthMarketDataClient.config_yaml["host"]
        port = StoreDepthMarketDataClient.config_yaml["port"]
        client_id = StoreDepthMarketDataClient.config_yaml["client_id"]
        ib_client.connect(host, port, client_id)
        ib_client.run()


    main()
