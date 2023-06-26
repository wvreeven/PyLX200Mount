from __future__ import annotations

__all__ = ["BaseMotorController"]

import logging
import types
from abc import ABC, abstractmethod

import astropy.units as u
from astropy.coordinates import Angle

from ..enums import MotorControllerState, SlewRate
from .trajectory import accelerated_pos_and_vel

# An angle of 180º.
ONE_EIGHTY = Angle(180.0 * u.deg)
# An angle of 360º.
THREE_SIXTY = Angle(360.0 * u.deg)
# Wrap angle for altitude.
ALT_WRAP = ONE_EIGHTY
# Wrap angle for azimuth.
AZ_WRAP = THREE_SIXTY


class BaseMotorController(ABC):
    def __init__(
        self, log: logging.Logger, is_alt: bool, conversion_factor: Angle
    ) -> None:
        self.is_alt = is_alt
        self.log = log.getChild(
            f"{type(self).__name__} {'Alt' if self.is_alt else 'Az'}"
        )

        self._position = 0.0
        self._velocity = 0.0
        self._max_velocity = 0.0
        self._max_acceleration = 0.0
        self._conversion_factor = conversion_factor
        self._position_offset = 0.0
        self.state = MotorControllerState.STOPPED

        # Some necessary constants that need to be computed once the conversion factor is known.
        self._one_eighty_steps = (ONE_EIGHTY / self._conversion_factor).value
        self._three_sixty_steps = (THREE_SIXTY / self._conversion_factor).value

    @property
    def position(self) -> Angle:
        pos = round(self._position + self._position_offset) * self._conversion_factor
        return pos.wrap_at(ALT_WRAP if self.is_alt else AZ_WRAP)

    @position.setter
    def position(self, position: Angle) -> None:
        position_value = (position / self._conversion_factor).value
        self._position_offset = round(position_value - self._position)
        self.log.debug(f"{self._position_offset=}")

    @property
    def velocity(self) -> Angle:
        return round(self._velocity) * self._conversion_factor

    @property
    def max_velocity(self) -> Angle:
        return self._max_velocity * self._conversion_factor

    @property
    def max_acceleration(self) -> Angle:
        return self._max_acceleration * self._conversion_factor

    def get_target_position_in_steps(self, target_position: Angle) -> int:
        target_position_in_steps = (
            round((target_position / self._conversion_factor).value)
            - self._position_offset
        )
        while (target_position_in_steps - self._position) > self._one_eighty_steps:
            target_position_in_steps = (
                target_position_in_steps - self._three_sixty_steps
            )
        while (target_position_in_steps - self._position) < -self._one_eighty_steps:
            target_position_in_steps = (
                target_position_in_steps + self._three_sixty_steps
            )

        return target_position_in_steps

    @abstractmethod
    def on_attach(self) -> None:
        """On attach callback."""
        raise NotImplementedError

    @abstractmethod
    def on_detach(self) -> None:
        """On detach callback."""
        raise NotImplementedError

    def on_position_change(self, current_position: int) -> None:
        """On position change callback.

        Parameters
        ----------
        current_position: `int`
            The current position of the stepper motor [steps].
        """
        raise NotImplementedError

    @abstractmethod
    def on_velocity_change(self, current_velocity: int) -> None:
        """On velocity change callback.

        Parameters
        ----------
        current_velocity: `int`
            The current velocity of the stepper motor [steps/sec].
        """
        raise NotImplementedError

    @abstractmethod
    async def connect(self) -> None:
        """Connect the stepper motor."""
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect the stepper motor."""
        raise NotImplementedError

    async def stop_motion(self) -> None:
        """Stop the current motion.

        If currently moving, this will slow down the motion at the maximum acceleration until stopped.
        If already stopped then this will have no effect.
        """
        self.state = MotorControllerState.STOPPING
        position_to_start_stopping = self._position
        max_velocity_in_steps = self._velocity
        if max_velocity_in_steps >= 0:
            accel = -self._max_acceleration
        else:
            accel = self._max_acceleration
        time_needed_to_stop = abs(max_velocity_in_steps / accel)
        target_position_in_steps, _ = accelerated_pos_and_vel(
            position_to_start_stopping,
            max_velocity_in_steps,
            accel,
            time_needed_to_stop,
        )
        target_position = (
            target_position_in_steps + self._position_offset
        ) * self._conversion_factor
        target_position_in_steps = self.get_target_position_in_steps(target_position)

        await self.set_target_position_and_velocity(
            target_position_in_steps, max_velocity_in_steps
        )

    async def move(
        self, target_position: Angle, slew_rate: SlewRate = SlewRate.HIGH
    ) -> None:
        """Move to the indicated target position at the maximum velocity.

        Parameters
        ----------
        target_position: `Angle`
            The target position to slew to [º].
        slew_rate: `SlewRate`
            The slew rate to apply. This determines the maximnum speed at which a slew is performed. Defaults
            to HIGH, which is the highest rate.
        """
        self.state = MotorControllerState.SLEWING
        target_position_in_steps = self.get_target_position_in_steps(target_position)
        max_velocity_in_steps = self._max_velocity * slew_rate / SlewRate.HIGH

        await self.set_target_position_and_velocity(
            target_position_in_steps, max_velocity_in_steps
        )

    async def track(self, target_position: Angle, timediff: float) -> None:
        target_position_in_steps = self.get_target_position_in_steps(target_position)
        max_velocity_in_steps = (self._position - target_position_in_steps) / timediff
        if not self.is_alt:
            self.log.debug(
                f"tracking from {self._position=} to {target_position_in_steps=} at {max_velocity_in_steps}"
            )
        await self.set_target_position_and_velocity(
            target_position_in_steps, max_velocity_in_steps
        )

    @abstractmethod
    async def set_target_position_and_velocity(
        self, target_position_in_steps: float, max_velocity_in_steps: float
    ) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> BaseMotorController:
        await self.connect()
        return self

    async def __aexit__(
        self,
        type: None | BaseException,
        value: None | BaseException,
        traceback: None | types.TracebackType,
    ) -> None:
        await self.disconnect()
