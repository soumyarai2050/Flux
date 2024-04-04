# system imports
import pandas as pd
from pathlib import PurePath
import inspect
from typing import List

# third-party imports
import yfinance as yf
import os


# project imports
os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_client import MobileBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.Pydentic.mobile_book_service_model_imports import *
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager

host: str = "127.0.0.1" if ((env_var := os.getenv("HOST")) is None or len(env_var) == 0) else env_var
port: int = 8040 if ((env_var := os.getenv("PORT")) is None or len(env_var) == 0) else env_var
mobile_book_service_web_client: MobileBookServiceHttpClient = MobileBookServiceHttpClient(host, port)

config_file_path = PurePath(__file__).parent.parent / "data" / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))


# Function used to add the symbol to the invalid cache file
def add_symbol_to_invalid_cache(symbol: str) -> None:
    """
    Adds symbol to invalid cache file
    """
    # Check if the file "SGX_invalid_symbols.csv" exists
    invalid_symbols_file_path = PurePath(__file__).parent.parent / "data" / "SGX_invalid_symbols.csv"
    if os.path.exists(invalid_symbols_file_path):
        logging.debug("SGX_invalid_symbols file exists.")
        # To check if symbol is already present in file
        with open(invalid_symbols_file_path, "r") as file:
            symbol_list = file.readlines()
            if symbol in symbol_list:
                logging.debug(f"Symbol {symbol} already exists in SGX_invalid_symbols file.")
                return
            # else we come out of with to close read mode file and open again in append mode to update file
        logging.debug(f"Symbol {symbol} not found in SGX_invalid_symbols file - adding new")
        with open(invalid_symbols_file_path, "a") as file:
            file.write(symbol + "\n")
    else:
        logging.debug("SGX_invalid_symbols file doe not exist - creating new")
        with open(invalid_symbols_file_path, "a") as file:
            file.write(symbol + "\n")


def is_valid_ticker(symbol: str) -> bool:
    """
    Checks if the ticker symbol is valid.
    """
    # if symbol doesn't exist return False and add it to another csv file
    # else if symbol exist then return True
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        logging.debug(f"info: {info}, ticker: {ticker}")
        return True
    except Exception as e:
        logging.exception(f"yahoo_finance lib raised while querying symbol: {symbol};;;exception: {e}, "
                          f"inspect: {inspect.trace()}")
        add_symbol_to_invalid_cache(symbol)
        return False


class YahooFinanceBase:
    def __init__(self, file_path: str | None = None):
        """
        Params:
            file_path: str : complete path of file containing symbols
        """
        file_name = config_yaml_dict['symbol_cache_file_name']
        if file_path is None:
            self.file_path: PurePath = PurePath(__file__).parent.parent / "data" / file_name
        else:
            self.file_path = file_path
        self.df: pd.Dataframe = pd.read_csv(self.file_path, sep="\t")
        self.symbols: List[str] = self.df["Symbol"]



