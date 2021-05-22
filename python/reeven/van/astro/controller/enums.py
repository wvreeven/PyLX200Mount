import enum

__all__ = ["MountControllerState", "SlewMode", "SlewDirection"]


class MountControllerState(enum.Enum):
    """State of the mount controller."""

    STOPPED = 0
    TRACKING = 1
    SLEWING = 2


class SlewMode(enum.Enum):
    """Slew modes"""

    ALT_AZ = "AltAz"
    RA_DEC = "RaDec"


class SlewDirection(enum.Enum):
    """Slew direction."""

    NORTH = "North"
    EAST = "East"
    SOUTH = "South"
    WEST = "West"
    UP = "Up"
    LEFT = "Left"
    DOWN = "Down"
    RIGHT = "Right"
