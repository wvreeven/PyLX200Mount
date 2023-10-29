__all__ = ["DatetimeUtil"]

from datetime import datetime


class DatetimeUtil:
    @classmethod
    def get_datetime(cls) -> datetime:
        """Convenience method to retrieve the current timezone datetime.

        Unit tests may replace this function for better time control.

        Returns
        -------
        `float`
            The current timezone datetime.
        """
        return datetime.now().astimezone()

    @classmethod
    def get_timestamp(cls) -> float:
        """Convenience method to retrieve the current time stamp.

        Returns
        -------
        `float`
            The current timezone time as timestamp.
        """
        return DatetimeUtil.get_datetime().timestamp()
