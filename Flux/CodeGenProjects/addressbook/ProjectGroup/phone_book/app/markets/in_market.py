from typing import Final
from pendulum import DateTime


class INMarket:
    def __init__(self):
        utc_hour_offset: Final[int] = 5
