import _thread
from machine import RTC


class TimeService:
    """RTC 동기화 상태와 현재 시각 조회를 한곳에서 관리한다."""

    def __init__(self):
        self._lock = _thread.allocate_lock()
        self._rtc = RTC()
        self._synchronized = False

    def synchronize(
        self,
        year,
        month,
        day,
        weekday,
        hour,
        minute,
        second,
    ):
        if year < 2024:
            raise ValueError("invalid year")
        if month < 1 or month > 12:
            raise ValueError("invalid month")
        if day < 1 or day > 31:
            raise ValueError("invalid day")
        if weekday < 0 or weekday > 6:
            raise ValueError("invalid weekday")
        if hour < 0 or hour > 23:
            raise ValueError("invalid hour")
        if minute < 0 or minute > 59:
            raise ValueError("invalid minute")
        if second < 0 or second > 59:
            raise ValueError("invalid second")

        self._lock.acquire()
        try:
            self._rtc.datetime((
                year,
                month,
                day,
                weekday,
                hour,
                minute,
                second,
                0,
            ))
            self._synchronized = True
        finally:
            self._lock.release()

    def is_synchronized(self):
        self._lock.acquire()
        try:
            return self._synchronized
        finally:
            self._lock.release()

    def now(self):
        self._lock.acquire()
        try:
            if not self._synchronized:
                raise RuntimeError("time is not synchronized")
            return self._rtc.datetime()
        finally:
            self._lock.release()
