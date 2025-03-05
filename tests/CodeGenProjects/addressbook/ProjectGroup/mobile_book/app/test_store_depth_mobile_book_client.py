from decimal import Decimal
from FluxPythonUtils.scripts.general_utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.store_depth_mobile_book_client import StoreDepthMobileBookClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.mobile_book_service_web_client import MobileBookServiceWebClient


class TestStoreDepthMobileBookClient:

    def __init__(self):
        configure_logger(StoreDepthMobileBookClient.config_yaml["log_level"],
                         str(StoreDepthMobileBookClient.log_dir_path))
        self.mobile_book_service_web_client = MobileBookServiceWebClient()
        self.store_depth_mobile_book_client = StoreDepthMobileBookClient(config_yaml=None, preserve_history=False)

    def test_update_mkt_depth(self):
        raw_market_depth_history_objs = self.mobile_book_service_web_client.get_all_raw_market_depth_history_client()

        for raw_market_depth_history_obj in raw_market_depth_history_objs:
            ticker_id, operation, position, price, side, size = \
                self.store_depth_mobile_book_client.get_ticker_id_from_symbol(
                    raw_market_depth_history_obj.symbol), \
                raw_market_depth_history_obj.operation, \
                raw_market_depth_history_obj.position, \
                raw_market_depth_history_obj.px, \
                raw_market_depth_history_obj.side, \
                raw_market_depth_history_obj.qty

            self.store_depth_mobile_book_client.updateMktDepth(int(ticker_id), int(position), int(operation),
                                                               StoreDepthMobileBookClient.get_side_str_to_side_int(
                                                                   side),
                                                               float(price), Decimal(size))

        assert True


def test_all():
    test_obj = TestStoreDepthMobileBookClient()
    test_obj.test_update_mkt_depth()
    assert True
