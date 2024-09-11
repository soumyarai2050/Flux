import datetime
import pendulum
from pendulum.parsing.exceptions import ParserError
import logging

# 3rd party imports

# project imports
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import get_nested_field_max_id


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


async def init_max_id_handler(model_class_type):
    latest_obj = await model_class_type.collection_obj.find_one(sort=[("_id", -1)])
    if latest_obj is not None:
        max_val = latest_obj.get("_id")
        if max_val is None:
            max_val = 0
    else:
        max_val = 0
    latest_obj = await model_class_type.collection_obj.find_one(sort=[("update_id", -1)])
    if latest_obj is not None:
        max_update_val = latest_obj.get("update_id")
        if max_update_val is None:
            max_update_val = 0
    else:
        max_update_val = 0
    model_class_type.init_max_id(int(max_val), int(max_update_val))


async def init_nested_max_id_handler(model_class_type, nested_field_name, nested_field_type):
    get_nested_field_max_id_pipeline = get_nested_field_max_id(nested_field_name)
    result = model_class_type.collection_obj.aggregate(get_nested_field_max_id_pipeline)
    if result:
        res_list = await result.to_list(None)
        if res_list:
            max_id = res_list[0]["max_id"]
        else:
            max_id = 0
    else:
        max_id = 0
    nested_field_type.init_max_id(max_id, None)  # passing None as max_update_id will ignore update
