# Python imports
import logging
import os
from pathlib import PurePath
from pendulum import DateTime
from typing import Dict

# 3rd party module imports
from ibapi.common import TickerId, TickAttrib
from ibapi.ticktype import TickTypeEnum, TickType

# Local project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.mobile_book.app.ib_api_client import IbApiClient
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, configure_logger

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.mobile_book.generated.mobile_book_service_web_client import MobileBookServiceWebClient
from Flux.CodeGenProjects.mobile_book.generated.mobile_book_service_model_imports import BBOBaseModel


class StoreMobileBookClient(IbApiClient):
    def __init__(self, config_yaml: Dict):
        required_config_data_keys = ["generic_tick_list", "snapshot", "regulatory_snapshot"]
        super().__init__(config_yaml, required_config_data_keys)
        self.generic_tick_list: str = self.config_yaml[required_config_data_keys[mobile_book]]  # sample: "233, 221"
        self.snapshot: bool = self.config_yaml[required_config_data_keys[1]]  # sample: False
        self.regulatory_snapshot: bool = self.config_yaml[required_config_data_keys[2]]  # sample: False
        self.mobile_book_service_web_client: MobileBookServiceWebClient = MobileBookServiceWebClient()

    def nextValidId(self, ticker_id: TickerId):
        """
        reqId: TickerId - The ticker id. Must be a unique value. When the
            market data returns, it will be identified by this tag. This is
            also used when canceling the market data.
        contract:Contract - This structure contains a description of the
            Contract for which market data is being requested.
        genericTickList:str - A comma delimited list of generic tick types.
            Tick types can be found in the Generic Tick Types page
            https://interactivebrokers.github.io/tws-api/classIBApi_1_1EClient.html#a7a19258a3a2mobile_book87cmobile_book7c1c57b93f659b63.
            Prefixing w/ 'mdoff' indicates that top mkt data shouldn't tick.
            You can specify the news source by post-fixing w/ ':<source>.
            Example: "mdoff,292:FLY+BRF"
        snapshot:bool - Check to return a single snapshot of Market data and
            have the market data subscription cancel. Do not enter any
            genericTicklist values if you use snapshots.
        regulatorySnapshot: bool - With the US Value Snapshot Bundle for stocks,
            regulatory snapshots are available for mobile_book.mobile_book1 USD each.
        """
        self.reqMobileBookType(StoreMobileBookClient.live_mobile_book)
        for idx, contract in enumerate(self.contracts):
            self.reqMktData(idx, contract, self.generic_tick_list, self.snapshot,
                            self.regulatory_snapshot, [])

    def error(self, ticker_id: TickerId, error_code: int, error_string: str, advanced_order_reject_json=""):
        logging.debug(f"Error: , {ticker_id}, {error_code}, {error_string}")

    def _add_to_db(self, ticker_id: int, tick_type: str, px: float | None = None, qty: float | None = None):
        get_all_db_obj = self.mobile_book_service_web_client.get_all_bbo_client()

        for db_obj in get_all_db_obj:
            if db_obj.tick_type == tick_type:
                bbo = BBOBaseModel(id=db_obj.id,
                                   symbol=self.contracts[ticker_id].symbol,
                                   tick_type=tick_type, date_time=DateTime.utcnow(),
                                   px=px, qty=qty)
                self.mobile_book_service_web_client.put_bbo_client(bbo)
                logging.debug(f"Adding {bbo} in DB")
                break
            # else not required: if tick type not present then adding new entry in this for loop's else block
        else:
            bbo = BBOBaseModel(req_id=ticker_id,
                               symbol=self.contracts[ticker_id].symbol,
                               tick_type=tick_type, date_time=DateTime.utcnow(),
                               px=px, qty=qty)
            self.mobile_book_service_web_client.create_bbo_client(bbo)
            logging.debug(f"Adding {bbo} in DB")

    def tickPrice(self, ticker_id: TickerId, tick_type: TickType, price: float, attrib: TickAttrib):
        tick_type_str = TickTypeEnum.to_str(tick_type)
        self._add_to_db(ticker_id, tick_type_str, px=price)

    def tickSize(self, ticker_id: TickerId, tick_type: TickType, size: float):
        tick_type_str = TickTypeEnum.to_str(tick_type)
        self._add_to_db(ticker_id, tick_type_str, qty=size)


if __name__ == "__main__":
    def main():
        project_root_path = PurePath(__file__).parent.parent
        config_file_path = project_root_path / "misc" / "config.yaml"
        config_yaml = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
        log_dir_path = project_root_path / "generated" / "logs"
        configure_logger(config_yaml["log_level"], str(log_dir_path))

        ib_client = StoreMobileBookClient(config_yaml)
        ib_client.setServerLogLevel(StoreMobileBookClient.log_lvl_detail)

        host = config_yaml["host"]
        port = config_yaml["port"]
        client_id = config_yaml["client_id"]
        ib_client.connect(host, port, client_id)
        ib_client.run()


    main()
