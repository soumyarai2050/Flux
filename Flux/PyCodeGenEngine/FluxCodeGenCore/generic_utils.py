import datetime
import pendulum
from pendulum.parsing.exceptions import ParserError
import logging


def validate_pendulum_datetime(v: datetime.datetime | str | None, datetime_format: str | None = None):
    if v == '':
        v = None
    if v is not None:
        if isinstance(v, pendulum.DateTime) or isinstance(v, datetime.datetime):
            return v
        elif isinstance(v, str):
            if datetime_format is None:
                try:
                    # convert from string format to datetime format
                    ret_datetime = pendulum.parse(v)
                    return ret_datetime
                except ParserError as e:
                    err_str = f"Pendulum parse could not parse datetime string {datetime_format}: {e}"
                    logging.exception(err_str)
                    raise Exception(err_str)
            else:
                try:
                    # convert from string format to datetime format
                    ret_datetime = pendulum.DateTime.strptime(v, datetime_format)
                    return ret_datetime
                except ValueError as e:
                    logging.debug(f"Datetime str {v} not of {datetime_format} format, returning as is")
                    return v
        else:
            err_str = f"Unsupported type {type(v).__name__} for datetime field"
            logging.exception(err_str)
            raise Exception(err_str)
    else:
        return v
