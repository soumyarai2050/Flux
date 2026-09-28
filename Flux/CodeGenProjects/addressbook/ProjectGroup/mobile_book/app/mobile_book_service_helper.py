# standard import
from pathlib import PurePath
from typing import List
import logging
import pandas as pd
from ib_insync import *
from datetime import datetime
import pytz

# project imports
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.ORMModel.mobile_book_service_msgspec_model import UILayoutBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_client import MobileBookServiceHttpClient


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
md_host, md_port = (config_yaml_dict.get("server_host"),
                    parse_to_int(config_yaml_dict.get("main_server_beanie_port")))
md_view_port = parse_to_int(config_yaml_dict.get("view_port"))

mobile_book_service_http_view_client = MobileBookServiceHttpClient.set_or_get_if_instance_exists(md_host, md_port,
                                                                                            view_port=md_view_port)
mobile_book_service_http_main_client = MobileBookServiceHttpClient.set_or_get_if_instance_exists(md_host, md_port)

if config_yaml_dict.get("use_view_clients"):
    mobile_book_service_http_client = mobile_book_service_http_view_client
else:
    mobile_book_service_http_client = mobile_book_service_http_main_client

def is_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            mobile_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of dashboard project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def is_view_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            mobile_book_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of dashboard project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def calculate_exact_us_luld(ib: IB, contract: Contract, luld_tier: int) -> dict:
    """
    Calculates real-time LULD bands for a US stock using the full, complex
    LULD plan rules.

    The calculation logic is a client-side replication of the official rules
    published by the adminiplanors of the Limit Up-Limit Down National Plan,
    which can be reviewed at https://www.luldplan.com/.

    This implementation correctly accounts for:
    - NMS Tiers (1 and 2).
    - Different percentage or price bands based on the security's reference price.
    - Doubling of the bands during the market open (9:30-9:45 ET) and
      close (15:35-16:00 ET).

    Args:
        ib (IB): An active and connected ib_insync IB object.
        contract (Contract): The qualified contract object for the US stock.
        luld_tier (int): The NMS tier of the stock (1 or 2). You must determine
                         this externally as it is not provided by the API.
                         Tier 1 is for S&P 500/Russell 1000 stocks and specific
                         ETPs. Tier 2 is for all others.

    Returns:
        dict: A dictionary containing the detailed LULD data or an error message.
    """
    try:
        # Step 1: Calculate the 5-minute VWAP to get the Reference Price
        bars = ib.reqHistoricalData(
            contract, '', '300 S', '1 secs', 'TRADES', True, 1)
        if not bars:
            return {"error": "Could not retrieve historical data for VWAP."}

        df = util.df(bars)
        reference_price = (df['close'] * df['volume']).sum() / df['volume'].sum()

        # Step 2: Determine Time of Day for band selection
        now_et = datetime.now(pytz.timezone('US/Eastern'))
        market_open_period = now_et.time() >= datetime.strptime("09:30", "%H:%M").time() and \
                             now_et.time() < datetime.strptime("09:45", "%H:%M").time()
        market_close_period = now_et.time() >= datetime.strptime("15:35", "%H:%M").time() and \
                              now_et.time() < datetime.strptime("16:00", "%H:%M").time()

        is_opening_or_closing = market_open_period or market_close_period

        # Step 3: Apply the full LULD rule table from luldplan.com
        percentage_band = 0
        price_band = 0

        # Tier 1 Securities
        if luld_tier == 1:
            if reference_price > 3.00:
                percentage_band = 0.05
            elif 0.75 <= reference_price <= 3.00:
                percentage_band = 0.20
            elif reference_price < 0.75:
                price_band = 0.15
        # Tier 2 Securities
        elif luld_tier == 2:
            if reference_price > 3.00:
                percentage_band = 0.10
            elif 0.75 <= reference_price <= 3.00:
                percentage_band = 0.20
            elif reference_price < 0.75:
                price_band = 0.15
        else:
            return {"error": "Invalid LULD Tier specified. Must be 1 or 2."}

        # Double the bands during opening/closing periods
        if is_opening_or_closing:
            if percentage_band > 0:
                percentage_band *= 2
            if price_band > 0:
                price_band *= 2

        # Step 4: Calculate the final Limit Up/Down prices
        if percentage_band > 0:
            limit_up = reference_price * (1 + percentage_band)
            limit_down = reference_price * (1 - percentage_band)
            band_applied = f"{percentage_band:.0%}"
        else:  # Fixed price_band for low-priced stocks
            limit_up = reference_price + price_band
            limit_down = max(0, reference_price - price_band)
            band_applied = f"${price_band:.2f}"

        return {
            "symbol": contract.symbol,
            "tier": luld_tier,
            "reference_price_vwap": round(reference_price, 4),
            "is_opening_closing": is_opening_or_closing,
            "band_applied": band_applied,
            "limit_up_price": round(limit_up, 2),
            "limit_down_price": round(limit_down, 2)
        }
    except Exception as e:
        logging.exception(f"calculate_exact_us_luld failed: {e}")
        return {"error": str(e)}


def calculate_exact_ca_sscb(ib: IB, ticker: Ticker) -> dict:
    """
    Calculates the real-time Single-Stock Circuit Breaker (SSCB) trigger
    levels for a Canadian stock.

    The calculation logic is a client-side replication of the official SSCB
    rules governed by the Canadian Investment Regulatory Organization (CIRO).

    This implementation correctly distinguishes between:
    - The market opening period (9:30-9:40 AM ET), which uses a 20% band.
    - Core bartering hours, which use a 10% band.

    The reference price used is the real-time last sale price.

    Args:
        ib (IB): An active and connected ib_insync IB object.
        contract (Contract): The qualified contract object for the Canadian stock.

    Returns:
        dict: A dictionary containing the SSCB data or an error message.
    """
    try:
        # Step 1: Get the current last sale price
        if pd.isna(ticker.last):
            return {"error": "Could not retrieve a valid last price."}

        reference_price = ticker.last

        # Step 2: Determine the correct percentage based on CIRO time rules
        now_toronto = datetime.now(pytz.timezone('America/Toronto'))
        market_opening_period = now_toronto.time() >= datetime.strptime("09:30", "%H:%M").time() and \
                                now_toronto.time() < datetime.strptime("09:40", "%H:%M").time()

        if market_opening_period:
            percentage = 0.20  # 20% band at the open
            period = "Opening (9:30-9:40 ET)"
        else:
            percentage = 0.10  # 10% band for the rest of the day
            period = "Core Hours"

        # Step 3: Calculate Trigger Levels
        trigger_up = reference_price * (1 + percentage)
        trigger_down = reference_price * (1 - percentage)

        return {
            "symbol": ticker.contract.symbol,
            "bartering_period": period,
            "reference_price_last": round(reference_price, 4),
            "sscb_band_percentage": f"{percentage:.0%}",
            "limit_up_price": round(trigger_up, 2),
            "limit_dn_price": round(trigger_down, 2),
        }
    except Exception as e:
        logging.exception(f"calculate_exact_ca_sscb failed: {e}")
        return {"error": str(e)}


async def get_realtime_price_limits(ib: IB, symbol: str, currency: str, exchange: str = 'SMART',
                                    ticker: Ticker | None = None, luld_tier: int = None) -> dict:
    """
    A unified wrapper function that calculates the real-time price limits for
    a stock from either a US or Canadian exchange.

    It automatically detects the correct regulatory plan (LULD for USD stocks,
    SSCB for CAD stocks) and applies the corresponding complex rules.

    Args:
        ib (IB): An active and connected ib_insync IB object.
        symbol (str): The stock ticker symbol (e.g., 'AAPL', 'RY').
        currency (str): The stock's currency ('USD' or 'CAD'). This is used to
                        determine which calculation logic to apply.
        exchange (str): The exchange to route through. Defaults to 'SMART'.
                        For Canadian stocks, using 'TSE' can be more specific.
        luld_tier (int): The NMS tier (1 or 2) for the stock. This is REQUIRED
                         for US stocks (currency='USD') and ignored for others.

    Returns:
        dict: A dictionary containing the detailed price limit data from the
              appropriate underlying function, or an error message.
    """
    try:
        # For Canadian stocks, it's often better to specify the primary exchange directly
        primary_exchange = 'TSE' if currency == 'CAD' and exchange == 'SMART' else ''

        contract = Stock(symbol, exchange, currency)
        if primary_exchange:
            contract.primaryExchange = primary_exchange

        # Qualify the contract to ensure it's valid
        await ib.qualifyContractsAsync(contract)

        # Route to the correct function based on the contract's currency
        if contract.currency == 'USD':
            if luld_tier is None:
                return {"error": "luld_tier (1 or 2) must be provided for US stocks."}
            return calculate_exact_us_luld(ib, contract, luld_tier)

        elif contract.currency == 'CAD':
            return calculate_exact_ca_sscb(ib, ticker)

        else:
            return {"error": f"Unsupported currency for price limits: {contract.currency}"}

    except Exception as e:
        logging.exception(f"get_realtime_price_limits failed: {e}")
        return {"error": str(e)}
