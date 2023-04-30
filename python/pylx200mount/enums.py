import enum

import numpy as np

__all__ = [
    "IDENTITY",
    "TELESCOPE_REDUCTION_06INCH",
    "TELESCOPE_REDUCTION_12INCH",
    "TELESCOPE_REDUCTION_20INCH",
    "AlignmentState",
    "MountControllerState",
    "SlewDirection",
    "SlewMode",
    "SlewRate",
]


# Reduction of the telescope gear additional to the motor gear reduction.
TELESCOPE_REDUCTION_06INCH = 10.82
TELESCOPE_REDUCTION_12INCH = 20.95
TELESCOPE_REDUCTION_20INCH = 34.91

# Identity (transformation) matrix.
IDENTITY = np.identity(3)


class MountControllerState(enum.Enum):
    """State of the mount controller."""

    STOPPED = enum.auto()
    TO_TRACKING = enum.auto()
    TRACKING = enum.auto()
    SLEWING = enum.auto()


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
    NONE = "None"


class SlewRate(float, enum.Enum):
    """Slew rate [deg/sec]."""

    CENTERING = 0.5
    GUIDING = 1.0
    FIND = 2.0
    HIGH = 3.0


class AlignmentState(enum.IntEnum):
    """Alignment state."""

    UNALIGNED = enum.auto()
    STAR_ONE_ALIGNED = enum.auto()
    ALIGNED = enum.auto()
