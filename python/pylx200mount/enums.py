__all__ = [
    "IDENTITY",
    "TELESCOPE_REDUCTION_06INCH",
    "TELESCOPE_REDUCTION_12INCH",
    "TELESCOPE_REDUCTION_20INCH",
    "CoordinatePrecision",
    "MotorControllerState",
    "SlewDirection",
    "SlewRate",
]

import enum

import numpy as np

# Reduction of the telescope gear additional to the motor gear reduction.
TELESCOPE_REDUCTION_06INCH = 10.82
TELESCOPE_REDUCTION_12INCH = 20.95
TELESCOPE_REDUCTION_20INCH = 34.91

# Identity (transformation) matrix.
IDENTITY = np.identity(3)


class CoordinatePrecision(enum.IntEnum):
    """Coordinate precision."""

    LOW = enum.auto()
    HIGH = enum.auto()


class MotorControllerState(enum.IntEnum):
    """State of a motor controller."""

    STOPPED = enum.auto()
    STOPPING = enum.auto()
    TRACKING = enum.auto()
    SLEWING = enum.auto()


class SlewDirection(enum.StrEnum):
    """Slew direction."""

    UP = "Up"
    LEFT = "Left"
    DOWN = "Down"
    RIGHT = "Right"
    NONE = "None"


class SlewRate(float, enum.Enum):
    """Slew rate [deg/sec]."""

    CENTERING = 0.01
    GUIDING = 0.1
    FIND = 0.5
    HIGH = 1.0
