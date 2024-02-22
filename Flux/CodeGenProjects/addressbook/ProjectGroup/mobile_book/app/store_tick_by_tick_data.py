import logging
import os
from pendulum import DateTime
from pathlib import PurePath
from decimal import Decimal
from typing import Dict

from ibapi.common import TickerId, TickAttribBidAsk, TickAttribLast
from ibapi.utils import floatMaxString, decimalMaxString
from ibapi.ticktype import TickTypeEnum
from Flux.CodeGenProjects.addressbook.ProjectGroup.mobile_book.app.ib_api_client import IbApiClient
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, configure_logger

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.mobile_book.generated.mobile_book_service_web_client import MobileBookServiceWebClient
from Flux.CodeGenProjects.mobile_book.generated.mobile_book_service_model_imports import TickByTickBidAskBaseModel, \
    TickByTickAllLastBaseModel


class StoreTickByTickData(IbApiClient):
    project_root_path = PurePath(__file__).parent.parent
    config_file_path = project_root_path / "misc" / "config.yaml"
    log_dir_path = project_root_path / "generated" / "logs"
    config_yaml = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))

    def __init__(self, config_yaml: Dict | None = None):
        if config_yaml is None:
            config_yaml = self.config_yaml
        required_config_data_keys = ["tick_types"]
        super().__init__(config_yaml, required_config_data_keys)
        self.tick_types = config_yaml[required_config_data_keys[mobile_book]]
        self.mobile_book_service_web_client: MobileBookServiceWebClient = MobileBookServiceWebClient()

    def _get_ticker_id(self, tick_type_idx: int, contract_idx: int) -> int:
        """
        Concatenates tick_type list index with contract list index to generate unique ticker id
        For example: there are 3 type of supported ticker_id(s) and let assume there are 3 different
        contracts in contracts_list, then each ticker id will be like 1mobile_book,11,12... for first tick type
        in list, 2mobile_book,21,22... for second one and 3mobile_book,31,32... for third one.
        """
        return int(f"{tick_type_idx+1}{contract_idx}")

    def _get_contract_symbol_from_ticker_id(self, ticker_id: int) -> str:
        """
        breaks concatenated ticker_id back to get contract index of its list and returns contract symbol
        of contract present at that index
        """
        contract_idx = int(f"{ticker_id}"[1:])
        return self.contracts[contract_idx].symbol

    def nextValidId(self, req_id: TickerId):
        self.reqMobileBookType(StoreTickByTickData.live_mobile_book)
        for tick_type_idx, tick_type in enumerate(self.tick_types):
            for contract_idx, contract in enumerate(self.contracts):
                ticker_id = self._get_ticker_id(tick_type_idx, contract_idx)
                self.reqTickByTickData(ticker_id, contract, tick_type["tick_type"],
                                       tick_type["number_of_ticks"], tick_type["ignore_size"])

    def error(self, req_id: TickerId, error_code: int, error_string: str, advanced_order_reject_json=""):
        logging.debug(f"Error: {req_id}, {error_code}, {error_string}")

    def tickByTickBidAsk(self, ticker_id: int, time: int, bid_price: float, ask_price: float,
                         bid_size: Decimal, ask_size: Decimal, tick_attrib_bid_ask: TickAttribBidAsk):
        super().tickByTickBidAsk(ticker_id, time, bid_price, ask_price, bid_size, ask_size, tick_attrib_bid_ask)
        tick_by_tick_bid_ask: TickByTickBidAskBaseModel = \
            TickByTickBidAskBaseModel(symbol=self._get_contract_symbol_from_ticker_id(ticker_id),
                                      time=DateTime.fromtimestamp(time),
                                      bid_px=floatMaxString(bid_price), ask_px=floatMaxString(ask_price),
                                      bid_qty=decimalMaxString(bid_size), ask_qty=decimalMaxString(ask_size),
                                      bid_past_low=tick_attrib_bid_ask.bidPastLow,
                                      bid_past_high=tick_attrib_bid_ask.askPastHigh)
        logging.debug(f"Adding {tick_by_tick_bid_ask} in TickByTickBidAsk Collection")
        self.mobile_book_service_web_client.create_tick_by_tick_bid_ask_client(tick_by_tick_bid_ask)

    def tickByTickAllLast(self, ticker_id: int, tick_type: int, time: int, price: float,
                          size: Decimal, tick_attrib_last: TickAttribLast, exchange: str,
                          special_conditions: str):
        super().tickByTickAllLast(ticker_id, tick_type, time, price, size, tick_attrib_last,
                                  exchange, special_conditions)
        tick_type_str = TickTypeEnum.to_str(tick_type)
        # todo: Lazy: tick_attrib_last and special_conditions
        tick_by_tick_all_last: TickByTickAllLastBaseModel = \
            TickByTickAllLastBaseModel(symbol=self._get_contract_symbol_from_ticker_id(ticker_id),
                                       time=DateTime.fromtimestamp(time),
                                       px=floatMaxString(price), qty=decimalMaxString(size),
                                       exchange=exchange, special_conditions=special_conditions,
                                       past_limit=tick_attrib_last.pastLimit, unreported=tick_attrib_last.unreported)
        logging.debug(f"Adding {tick_by_tick_all_last} in TickByTickBidAsk Collection, with tick_type: {tick_type_str}")
        self.mobile_book_service_web_client.create_tick_by_tick_all_last_client(tick_by_tick_all_last)


if __name__ == "__main__":
    def main():
        configure_logger(StoreTickByTickData.config_yaml["log_level"], str(StoreTickByTickData.log_dir_path))

        ib_client = StoreTickByTickData()
        ib_client.setServerLogLevel(StoreTickByTickData.log_lvl_detail)

        host = StoreTickByTickData.config_yaml["host"]
        port = StoreTickByTickData.config_yaml["port"]
        client_id = StoreTickByTickData.config_yaml["client_id"]
        ib_client.connect(host, port, client_id)
        ib_client.run()

    main()
