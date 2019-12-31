import datetime

class UnixTime:

    def __init__(self, value: int):
        self.value = value

    def to_datetime(self):
        return datetime.datetime.fromtimestamp(self.value)
    
    def humanize(self, fmt="%d.%m.%Y"):
        return self.to_datetime().strftime(fmt)

