# standard imports
import asyncio
from typing import Set

# project imports
from ProjectGroup.dept_book.app.yahoo_finance_base import *
from FluxPythonUtils.scripts.general_utility_functions import configure_logger
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.dept_book_service_helper import dashboard_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_msgspec_model import *


# This class is used to create objects that represent the concept of getting historical data.
class BarDataLoader(YahooFinanceBase):
    """
    A class for retrieving historical data from the file.
    """

    def __init__(self, file_path: str | None = None):
        super().__init__(file_path)
        self.bar_data_symbol_n_last_update_date_time_list: List[BarDataNLatestUpdateDateTime] = \
            dashboard_service_http_client.get_bar_data_all_symbols_n_last_update_time_query_client()
        self.symbol_to_last_update_datetime_dict: Dict[str, DateTime] = {}
        if self.bar_data_symbol_n_last_update_date_time_list:
            self.symbol_to_last_update_datetime_dict: Dict[str, DateTime] = {
                bar_data_symbol_n_datetime.symbol: bar_data_symbol_n_datetime.last_update_datetime
                for bar_data_symbol_n_datetime in self.bar_data_symbol_n_last_update_date_time_list[0].symbol_n_last_update_datetime
            }

    async def _create_update_bar_data_from_source(self, ticker: yf.Ticker, symbol: str) -> None:
        interval = config_yaml_dict["bar_data_fetch_interval"]
        period = config_yaml_dict["bar_data_fetch_period"]
        if symbol in self.symbol_to_last_update_datetime_dict:
            start_datetime = self.symbol_to_last_update_datetime_dict[symbol]
            start_date = pendulum.parse(str(start_datetime)).add(days=1)
            start_date_str = start_date.format("YYYY-MM-DD")
            symbol_history_df: pl.Dataframe = ticker.history(period=period, interval=interval, start=start_date_str)
        else:
            symbol_history_df: pl.Dataframe = ticker.history(period=period, interval=interval)
        if not symbol_history_df.empty:
            bar_data_list = []
            for timestamp, row in symbol_history_df.iterrows():
                if symbol in self.symbol_to_last_update_datetime_dict:
                    df_datetime = pendulum.parse(str(timestamp))
                    start_datetime = self.symbol_to_last_update_datetime_dict[symbol]
                    if not (df_datetime > start_datetime):
                        # to avoid any repeating value in db when start date is provided
                        continue
                bar_data = BarDataBaseModel(
                    symbol=symbol,
                    datetime=pendulum.parse(str(timestamp)),
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume'],
                    dividends=row['Dividends'],
                    stock_splits=row['Stock Splits'])
                bar_data_list.append(bar_data)
            dashboard_service_http_client.create_all_bar_data_client(bar_data_list)
        else:
            add_symbol_to_invalid_cache(symbol)

    # Fetches the historical data.
    async def create_update_bar_data_from_source(self) -> None:
        """
        Fetch historical data for each symbol and store it in the market data service.
        """
        task_list: List[asyncio.Task] = []
        for symbol in self.symbols:
            complete_symbol = f"{symbol}.SI"
            # checking if symbol is valid
            if is_valid_ticker(complete_symbol):
                ticker: yf.Ticker = yf.Ticker(complete_symbol)
                task: asyncio.Task = \
                    asyncio.create_task(self._create_update_bar_data_from_source(ticker, complete_symbol),
                                        name=complete_symbol)
                task_list.append(task)
            else:
                # else putting in another csv cache file
                add_symbol_to_invalid_cache(complete_symbol)
                logging.debug(f"invalid symbol - {complete_symbol}, added symbol to invalid symbol's cache csv")

        pending_tasks: Set[asyncio.Task] = set()
        completed_tasks: Set[asyncio.Task] = set()
        if task_list:
            try:
                # wait doesn't raise TimeoutError! Futures that aren't done when timeout occurs are returned in 2nd set
                completed_tasks, pending_tasks = await asyncio.wait(task_list, return_when=asyncio.ALL_COMPLETED,
                                                                    timeout=None)
            except Exception as e:
                logging.exception(f"await asyncio.wait raised exception: {e}")

        while completed_tasks:
            completed_task = None
            try:
                completed_task = completed_tasks.pop()
            except Exception as e:
                idx = int(completed_task.get_name())
                logging.exception(f"create_update_bar_data_from_source failed for task {task_list[idx]} "
                                  f"with exception: {e}")

        if pending_tasks:
            logging.error("Received timed out pending tasks in create_update_bar_data_from_source, dropping them. "
                          f"PendingTasks: {[pending_task for pending_task in pending_tasks]}")


if __name__ == "__main__":
    # logging
    from datetime import datetime

    log_dir: PurePath = PurePath(__file__).parent.parent / "log"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    configure_logger('debug', str(log_dir), f'bar_data_loader_{datetime_str}.log')

    # Create an instance of the GetHistoricalData class.
    bar_data_loader = BarDataLoader()
    # Execute the main processes of the GetHistoricalData instance.
    asyncio.run(bar_data_loader.create_update_bar_data_from_source())
