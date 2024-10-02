# project imports
from ProjectGroup.dept_book.app.yahoo_finance_base import *
from FluxPythonUtils.scripts.utility_functions import configure_logger, read_mongo_collection_as_dataframe
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.aggregate import get_bar_data_from_symbol_n_start_n_end_datetime


class GetAvgOpenForSymbols(YahooFinanceBase):
    """
        A class for retrieving and calculating the average open price for symbols.

        Inherits from YahooFinanceBase.
        """
    def __init__(self, file_path: str | None = None):
        """
         Initialize the GetAvgOpenForSymbols instance.

        """
        super().__init__(file_path)

    def load_collection_as_dataframe(self) -> None:
        """
        Load the collection as a DataFrame and calculate the average open price for symbols.

        Retrieves the necessary configurations from yaml configuration file and symbols from the superclass.

        """
        db: str = config_yaml_dict['db']
        collection: str = config_yaml_dict['collection']
        start_datetime_str: str = config_yaml_dict["bar_data_df_start_datetime"]
        end_datetime_str: str = config_yaml_dict["bar_data_df_end_datetime"]
        ticker_suffix: str = config_yaml_dict["ticker_suffix"]

        for symbol in self.symbols:
            symbol_with_suffix = symbol + ticker_suffix
            # pendulum.parse(datetime_str)
            if start_datetime_str.lower() == "none":
                start_datetime = None
            else:
                start_datetime = pendulum.parse(start_datetime_str)

            if end_datetime_str.lower() == "none":
                end_datetime = None
            else:
                end_datetime = pendulum.parse(end_datetime_str)

            agg_pipeline_dict = \
                get_bar_data_from_symbol_n_start_n_end_datetime(symbol_with_suffix, start_datetime, end_datetime)
            # Read the MongoDB collection as a DataFrame
            df: pl.DataFrame = \
                read_mongo_collection_as_dataframe(db, collection, agg_pipeline=agg_pipeline_dict["aggregate"])

            if not df.is_empty():
                # Calculate the average open price
                avg_open_price = df['open'].mean()
                logging.debug(f"Average Open Price of symbol {symbol_with_suffix}: {avg_open_price}")
            else:
                logging.info(f"No data available for symbol: {symbol_with_suffix}")


if __name__ == "__main__":
    from datetime import datetime

    log_dir: PurePath = PurePath(__file__).parent.parent / "log"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    configure_logger('debug', str(log_dir), f'get_avg_open_{datetime_str}.log')

    # Create an instance of the GetAvgOpenForSymbols class.
    get_avg_open = GetAvgOpenForSymbols()
    # Load the collection as a DataFrame and calculate the average open price for symbols
    get_avg_open.load_collection_as_dataframe()




