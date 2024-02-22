# system imports
import os
import json
from datetime import datetime
from pathlib import PurePath
import pytest
# other package imports
from ibapi.contract import Contract
from ibapi.common import BarData
# project imports
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, configure_logger
from FluxPythonUtils.scripts.utility_functions import str_from_file
from Flux.CodeGenProjects.addressbook.ProjectGroup.mobile_book.app.store_historical_data_client import StoreHistoricalDataClient

os.environ["DBType"] = "beanie"

project_root_path = PurePath(__file__).parent.parent
misc_dir_path = project_root_path / "misc"


@pytest.fixture(scope="session")
def config_yaml():
    config_file_path: PurePath = misc_dir_path / "config.yaml"
    config_yaml = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
    log_dir_path: PurePath = misc_dir_path
    configure_logger(config_yaml["log_level"], str(log_dir_path))
    yield config_yaml


@pytest.fixture(scope="session")
def contract():
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    yield contract


@pytest.fixture(scope="session")
def ib_client(config_yaml, contract):
    end_date_time = datetime.now().strftime("%Y%m%d-%H:%M:%S")
    req_id = config_yaml["req_id"]
    duration_str = config_yaml["duration_str"]
    bar_size_setting = config_yaml["bar_size_setting"]
    what_to_show = config_yaml["what_to_show"]
    use_rth = config_yaml["use_rth"]
    format_date = config_yaml["format_date"]
    keep_up_to_date = config_yaml["keep_up_to_date"]
    chart_options = config_yaml["chart_options"]
    ib_client = StoreHistoricalDataClient(req_id, contract, end_date_time, duration_str, bar_size_setting,
                                          what_to_show, use_rth, format_date, keep_up_to_date, chart_options)
    yield ib_client


def test_json_data_array() -> []:
    history_bar_data_sample_file_path: PurePath = misc_dir_path / "history_bar_data_sample.json"
    json_str = str_from_file(str(history_bar_data_sample_file_path))
    jason_data_array = json.loads(json_str)
    return jason_data_array


@pytest.mark.parametrize("test_json_data", test_json_data_array())
def test_history_data_publish(ib_client, test_json_data):
    try:
        bar: BarData = BarData()
        bar.date = test_json_data["date"]
        bar.open = test_json_data["open"]
        bar.high = test_json_data["high"]
        bar.low = test_json_data["low"]
        bar.close = test_json_data["close"]
        bar.volume = test_json_data["volume"]
        bar.barCount = test_json_data["barCount"]
        bar.average = test_json_data["average"]
        ib_client.historicalData(1, bar)
        assert True
    except Exception as e:
        assert False, f"error: {e}"
