import logging
from decimal import Decimal
from FluxPythonUtils.scripts.utility_functions import configure_logger
from Flux.CodeGenProjects.market_data.app.store_depth_market_data_client import StoreDepthMarketDataClient
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient


class TestStoreDepthMarketDataClient:

    def __init__(self):
        configure_logger(StoreDepthMarketDataClient.config_yaml["log_level"],
                         str(StoreDepthMarketDataClient.log_dir_path))
        self.market_data_service_web_client = MarketDataServiceWebClient()
        self.store_depth_market_data_client = StoreDepthMarketDataClient(config_yaml=None, preserve_history=False)

    def test_update_mkt_depth(self):
        raw_market_depth_history_objs = self.market_data_service_web_client.get_all_raw_market_depth_history_client()

        for raw_market_depth_history_obj in raw_market_depth_history_objs:
            ticker_id, operation, position, price, side, size = \
                self.store_depth_market_data_client.get_ticker_id_from_symbol(
                    raw_market_depth_history_obj.symbol), \
                raw_market_depth_history_obj.operation, \
                raw_market_depth_history_obj.position, \
                raw_market_depth_history_obj.px, \
                raw_market_depth_history_obj.side, \
                raw_market_depth_history_obj.qty

            self.store_depth_market_data_client.updateMktDepth(int(ticker_id), int(position), int(operation),
                                                               StoreDepthMarketDataClient.get_side_str_to_side_int(
                                                                   side),
                                                               float(price), Decimal(size))

        assert True


def test_all():
    test_obj = TestStoreDepthMarketDataClient()
    test_obj.test_update_mkt_depth()
    assert True
