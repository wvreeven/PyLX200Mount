import enum

__all__ = [
    "MountControllerState",
    "SlewMode",
    "SlewDirection",
    "SlewRate",
    "AlignmentState",
]


class MountControllerState(enum.Enum):
    """State of the mount controller."""

    STOPPED = 0
    TRACKING = 1
    SLEWING = 2


class SlewMode(enum.Enum):
    """Slew mode."""

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


class SlewRate(enum.Enum):
    """Slew rate [deg/sec]."""

    CENTERING = 0.5
    GUIDING = 1.0
    FIND = 2.0
    HIGH = 3.0


class AlignmentState(enum.IntEnum):
    """Alignment state."""

    UNALIGNED = 0
    STAR_ONE_ALIGNED = 1
    ALIGNED = 2
