from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.yahoo_finance_base import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.dept_book_service_helper import dashboard_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_msgspec_model import *
from FluxPythonUtils.scripts.general_utility_functions import configure_logger


# This class is to create objects that represent the concept of loading symbol overviews.
class SymbolOverviewLoader(YahooFinanceBase):
    """
    A class for loading symbol overviews from the file.
    """

    def __init__(self, file_path: str | None = None):
        super().__init__(file_path)
        self.fetched_symbol_overviews: List[SymbolOverviewBaseModel] = \
            dashboard_service_http_client.get_all_symbol_overview_client()
        self.symbol_to_symbol_overview_dict: Dict[str, SymbolOverviewBaseModel] = \
            {fetched_symbol_overview.symbol: fetched_symbol_overview
             for fetched_symbol_overview in self.fetched_symbol_overviews}

    # Create or update the symbol overview from the data source.
    def create_or_update_symbol_overview_from_source(self):
        """
        Fetch the latest data for each symbol and store it in the market data service.
        """
        for symbol in self.symbols:
            complete_symbol = f"{symbol}.SI"
            if is_valid_ticker(complete_symbol):
                ticker = yf.Ticker(complete_symbol)

                # check if symbol already in symbol_to_symbol_overview_dict as key
                if symbol in self.symbol_to_symbol_overview_dict:
                    # fetch symbol_overview object from dict using symbol as key
                    symbol_overview = self.symbol_to_symbol_overview_dict[symbol]
                else:
                    symbol_overview = SymbolOverviewBaseModel()
                    symbol_overview.symbol = complete_symbol

                # update the symbol_overview with ticker.info.get values
                symbol_overview.company = ticker.info.get("longName")
                symbol_overview.open_px = ticker.info.get("open")
                symbol_overview.closing_px = ticker.info.get("previousClose")
                symbol_overview.volume = ticker.info.get("volume")
                symbol_overview.high = ticker.info.get("dayHigh")
                symbol_overview.low = ticker.info.get("dayLow")
                symbol_overview.last_update_date_time = ticker.info.get("lastBarterDate")

                if symbol in self.symbol_to_symbol_overview_dict:
                    # instead of create this time use put_symbol_overview_client
                    updated_symbol_overview = dashboard_service_http_client.put_symbol_overview_client(symbol_overview)
                else:
                    created_symbol_overview = dashboard_service_http_client.create_symbol_overview_client(
                        symbol_overview)
                    # updating symbol_to_symbol_overview_dict with new created symbol_overview
                    self.symbol_to_symbol_overview_dict[created_symbol_overview.symbol] = created_symbol_overview
            else:
                add_symbol_to_invalid_cache(complete_symbol)


if __name__ == "__main__":
    #logging
    from datetime import datetime

    log_dir: PurePath = PurePath(__file__).parent.parent / "log"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    configure_logger('debug', str(log_dir), f'symbol_overview_loader_{datetime_str}.log')

    # Create an instance of the SymbolOverviewLoader class with the specified file path.
    symbol_overview_loader = SymbolOverviewLoader()
    # Execute the main processes of the SymbolOverviewLoader instance.
    symbol_overview_loader.create_or_update_symbol_overview_from_source()
