from datetime import datetime

from pytz import timezone


class JapanDatetimeHelper:
    __timezone__ = timezone("Asia/Tokyo")

    @classmethod
    def today(cls):
        return cls.now().date()

    @classmethod
    def now(cls):
        return datetime.now(tz=cls.__timezone__)
