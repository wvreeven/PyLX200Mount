__all__ = ["DatetimeUtil"]

import logging
from datetime import datetime, timedelta, timezone

dt = datetime.now().astimezone()
assert dt is not None
utcoffset = dt.utcoffset()


class DatetimeUtil:
    """Utility class to work with datetime instances.

    Uisng a computer without internet connection and without a real time clock may result in inaccurate
    pointing due to time differences between the hardware clock and the world. This utility class aims to
    solve that for this project.
    """

    delta = timedelta()
    utc_offset = 0.0
    assert utcoffset is not None
    tz = timezone(utcoffset)

    @classmethod
    def get_datetime(cls) -> datetime:
        """Convenience method to retrieve the current timezone datetime.

        This takes both the timezone (either taken from the computer or set by the planetarium software) and
        the timedelta (taken from the time and date set by the planetarium software) into account.

        Unit tests may replace this function for better time control.

        Returns
        -------
        `float`
            The current timezone datetime.
        """
        return datetime.now().astimezone(DatetimeUtil.tz) + DatetimeUtil.delta

    @classmethod
    def get_timestamp(cls) -> float:
        """Convenience method to retrieve the current time stamp.

        Returns
        -------
        `float`
            The current timezone time as timestamp.
        """
        return DatetimeUtil.get_datetime().timestamp()

    @classmethod
    def set_datetime(cls, dt: datetime) -> None:
        """Set the date.

        The difference between the time reported by the hardware clock and reported by the planetarium
        software is determined and stored so the `get_datetime` method can use it. The timezone used by this
        class is also updated.

        Parameters
        ----------
        dt : `datetime`
            The datetime as set by the planetarium software.
        """
        logging.getLogger(cls.__name__).debug(f"{dt=}")
        # noinspection PyTypeChecker
        DatetimeUtil.delta = DatetimeUtil.get_datetime() - dt
        logging.getLogger(cls.__name__).debug(f"{DatetimeUtil.delta=}")
        utcoffset = dt.utcoffset()
        assert utcoffset is not None
        DatetimeUtil.tz = timezone(utcoffset)
        logging.getLogger(cls.__name__).debug(f"{DatetimeUtil.tz=}")
