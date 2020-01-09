import datetime
import time


class UnixTime:

    def __init__(self, value):
        self.value = value

    @classmethod
    def now(cls):
        return cls(time.time())

    @property
    def timestamp(self):
        return self.value

    def to_datetime(self):
        return datetime.datetime.fromtimestamp(self.value)
    
    def humanize(self, fmt="%d.%m.%Y"):
        return self.to_datetime().strftime(fmt)

    def __add__(self, timedelta: datetime.timedelta):
        now = self.now()
        now.value += timedelta.total_seconds()
        return now

    def __sub__(self, timedelta: datetime.timedelta):
        now = self.now()
        now.value -= timedelta.total_seconds()
        return now

    def passed_seconds(self) -> int:
        now = self.now()
        return now.timestamp - self.value
