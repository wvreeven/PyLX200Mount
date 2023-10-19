__all__ = ["get_time"]

from datetime import datetime


def get_time() -> float:
    """Convenience method to retrieve the current time stamp.

    Unit tests may replace this function for better time control.

    Returns
    -------
    `float`
        The current timezone time as timestamp.
    """
    return datetime.now().astimezone().timestamp()
