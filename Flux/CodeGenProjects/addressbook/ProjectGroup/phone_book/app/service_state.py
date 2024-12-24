import logging

from pendulum import DateTime


class ServiceState:

    def __init__(self, error_prefix: str):
        self.ready: bool = False
        self.last_exception: Exception | None = None
        self.error_prefix: str = ""
        self.first_error_time: DateTime | None = None

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

    def handle_exception(self, e: Exception, inspect_trace=None):
        error_str: str = f"{self.error_prefix} failed;;;exception: {e}, " \
                         f"{inspect_trace[-1][3] if inspect_trace else None}"
        logging.error(error_str, exc_info=True)
        if (last_error_interval_in_sec := self.record_error(e)) == 0:
            # raise alert
            pass
        elif last_error_interval_in_sec > (60 * 5):
            # it's been 5 minutes the error is still not resolved - re-alert
            pass
