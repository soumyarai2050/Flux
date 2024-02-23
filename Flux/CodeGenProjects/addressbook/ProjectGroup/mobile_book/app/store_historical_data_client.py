import logging
import os
from typing import Dict
from datetime import datetime
from pathlib import PurePath
from ibapi.common import BarData, TickerId
from Flux.CodeGenProjects.addressbook.ProjectGroup.mobile_book.app.ib_api_client import IbApiClient
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, configure_logger

os.environ["DBType"] = "beanie"
from Flux.CodeGenProjects.mobile_book.generated.mobile_book_service_web_client import MobileBookServiceWebClient
from Flux.CodeGenProjects.mobile_book.generated.mobile_book_service_model_imports import BarDataBaseModel


class StoreHistoricalDataClient(IbApiClient):
    def __init__(self, config_yaml: Dict):
        """
            reqId:TickerId - The id of the request. Must be a unique value. When the
                market data returns, it whatToShowill be identified by this tag. This is also
                used when canceling the market data.
            contract:Contract - This object contains a description of the contract for which
                market data is being requested.
            endDateTime:str - Defines a query end date and time at any point during the past 6 mos.
                Valid values include any date/time within the past six months in the format:
                yyyymmdd HH:mm:ss ttt

                where "ttt" is the optional time zone.
            durationStr:str - Set the query duration up to one week, using a time unit
                of seconds, days or weeks. Valid values include any integer followed by a space
                and then S (seconds), D (days) or W (week). If no unit is specified, seconds is used.
            barSizeSetting:str - Specifies the size of the bars that will be returned (within IB/TWS listimits).
                Valid values include:
                1 sec
                5 secs
                15 secs
                30 secs
                1 min
                2 mins
                3 mins
                5 mins
                15 mins
                30 mins
                1 hour
                1 day
            whatToShow:str - Determines the nature of data beinging extracted. Valid values include:
                TRADES
                MIDPOINT
                BID
                ASK
                BID_ASK
                HISTORICAL_VOLATILITY
                OPTION_IMPLIED_VOLATILITY
            useRTH:int - Determines whether to return all data available during the requested time span,
                or only data that falls within regular trading hours. Valid values include:

                0 - all data is returned even where the market in question was outside of its
                regular trading hours.
                1 - only data within the regular trading hours is returned, even if the
                requested time span falls partially or completely outside of the RTH.
            formatDate: int - Determines the date format applied to returned bars. validd values include:

                1 - dates applying to bars returned in the format: yyyymmdd{space}{space}hh:mm:dd
                2 - dates are returned as a long integer specifying the number of seconds since
                    1/1/1970 GMT.
        """
        required_config_data_keys = ["duration_str", "bar_size_setting", "what_to_show", "use_rth",
                                     "format_date", "keep_up_to_date"]
        super().__init__(config_yaml, required_config_data_keys)
        self.end_date_time: str = datetime.now().strftime("%Y%m%d-%H:%M:%S")  # sample:'20230116-16:11:27'
        self.duration_str: str = config_yaml[required_config_data_keys[0]]  # sample: "1 M"
        self.bar_size_setting: str = config_yaml[required_config_data_keys[1]]  # sample: "1 day"
        self.what_to_show: str = config_yaml[required_config_data_keys[2]]  # sample: "TRADES"
        self.use_RTH: int = config_yaml[required_config_data_keys[3]]    # sample: 1
        self.format_date: int = config_yaml[required_config_data_keys[4]]    # sample: 1
        self.keep_up_to_date: bool = config_yaml[required_config_data_keys[5]]    # sample: False
        self.mobile_book_service_web_client: MobileBookServiceWebClient = MobileBookServiceWebClient()
        self.bar_date_format: str = "%Y%m%d"
        self.last_bar_data_date_time: datetime | None = self._get_last_db_obj_date_time()

    def _get_last_db_obj_date_time(self) -> datetime | None:
        try:
            db_max_id_obj = self.mobile_book_service_web_client.get_bar_data_query_client()
            return db_max_id_obj.date
        except Exception as e:
            if '{"detail":"No Data available for query in BarData"}' in str(e):
                # when db is empty
                return None
            else:
                err_str = f"Error occurred while fetching last dat from db: {e}"
                logging.exception(err_str)
                raise Exception(err_str)

    def nextValidId(self, req_id: TickerId):

        for idx, contract in enumerate(self.contracts):
            self.reqHistoricalData(idx, contract, self.end_date_time, self.duration_str,
                                   self.bar_size_setting, self.what_to_show, self.use_RTH, self.format_date,
                                   self.keep_up_to_date, [])

    def error(self, req_id: TickerId, error_code: int, error_string: str, advanced_order_reject_json=""):
        logging.debug(f"Error: , {req_id}, {error_code}, {error_string}")

    def historicalData(self, ticker_id: int, bar: BarData):
        do_add_to_db: bool = False
        if self.last_bar_data_date_time is None:
            # when db is empty
            do_add_to_db = True
        else:
            if datetime.strptime(bar.date, self.bar_date_format) > self.last_bar_data_date_time:
                do_add_to_db = True
            elif datetime.strptime(bar.date, self.bar_date_format) < self.last_bar_data_date_time:
                err_str = "Database can't have last date greater than received date from TWS api"
                logging.exception(err_str)
                raise Exception(err_str)
            # else not required: if last data entry in db is having equal date as of received then
            # avoiding data insertion to db

        if do_add_to_db:
            bar_data_base_model: BarDataBaseModel = BarDataBaseModel(symbol=self.contracts[ticker_id].symbol,
                                                                     date=bar.date, open=bar.open, high=bar.high,
                                                                     low=bar.low, close=bar.close, volume=bar.volume,
                                                                     barCount=bar.barCount)
            logging.debug(f"Adding {bar_data_base_model} in BarData Collection")
            self.mobile_book_service_web_client.create_bar_data_client(bar_data_base_model)
        # else not required: avoiding data insertion to db if above requirements doesn't met

    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)
        logging.debug(f"HistoricalDataEnd. ReqId: {req_id} from {start} to {end}")

    def historicalDataUpdate(self, req_id: int, bar: BarData):
        logging.debug(f"HistoricalDataUpdate. ReqId: {req_id} BarData. {bar}")


if __name__ == "__main__":
    def main():
        project_root_path = PurePath(__file__).parent.parent
        config_file_path = project_root_path / "misc" / "config.yaml"
        config_yaml = YAMLConfigurationManager.load_yaml_configurations(str(config_file_path))
        log_dir_path = project_root_path / "generated" / "logs"
        configure_logger(config_yaml["log_level"], str(log_dir_path))

        ib_client = StoreHistoricalDataClient(config_yaml)
        ib_client.setServerLogLevel(StoreHistoricalDataClient.log_lvl_detail)

        host = config_yaml["host"]
        port = config_yaml["port"]
        client_id = config_yaml["client_id"]
        ib_client.connect(host, port, client_id)
        ib_client.run()

    main()
