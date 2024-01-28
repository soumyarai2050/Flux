import datetime
import pendulum
from pendulum.parsing.exceptions import ParserError
import logging


def _handle_str_datetime(dt: datetime.datetime | str | None, datetime_format: str | None = None):
    if datetime_format is None:
        try:
            # convert from string format to datetime format
            ret_datetime = pendulum.parse(dt)
            return ret_datetime
        except ParserError as e:
            err_str = f"Pendulum parse could not parse datetime string {datetime_format}: {e}"
            logging.exception(err_str)
            raise Exception(err_str)
    else:
        try:
            # convert from string format to datetime format
            ret_datetime = pendulum.DateTime.strptime(dt, datetime_format)
            return ret_datetime
        except ValueError as e:
            logging.debug(f"Datetime str {dt} not of {datetime_format} format, returning as is")
            return dt


def validate_pendulum_datetime(dt: datetime.datetime | str | None, datetime_format: str | None = None):
    if dt == '':
        dt = None
    if dt is not None:
        if isinstance(dt, pendulum.DateTime) or isinstance(dt, datetime.datetime):
            if isinstance(dt, datetime.datetime):
                # convert from string format to datetime format
                v_str = str(dt)
                return _handle_str_datetime(v_str, datetime_format)
            return dt
        elif isinstance(dt, str):
            return _handle_str_datetime(dt, datetime_format)
        else:
            err_str = f"Unsupported type {type(dt).__name__} for datetime field"
            logging.exception(err_str)
            raise Exception(err_str)
    else:
        return dt
