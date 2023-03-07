import logging

from pendulum import DateTime
from pydantic import BaseModel


class ServiceState(BaseModel):
    ready: bool = False
    last_exception: Exception | None = None
    error_prefix: str = ""
    first_error_time: DateTime | None = None

    class Config:
        arbitrary_types_allowed = True

    def record_error(self, e: Exception) -> int:
        """
        returns time in seconds since first error if error is repeated, 0 otherwise
        if new error - record error in last error and update first error time with current time
        """
        if self.last_exception == e:
            return self.first_error_time.diff(DateTime.utcnow()).in_seconds()
        else:
            self.last_exception = e
            self.first_error_time = DateTime.utcnow()
            return 0

    def handle_exception(self, e: Exception):
        error_str: str = f"{self.error_prefix}{e}"
        logging.error(error_str, exc_info=True)
        if (last_error_interval_in_sec := self.record_error(e)) == 0:
            # raise alert
            pass
        elif last_error_interval_in_sec > (60 * 5):
            # it's been 5 minutes the error is still not resolved - re-alert
            pass
