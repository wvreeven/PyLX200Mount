import logging
import math
import typing

import astropy.units as u
from astropy.coordinates import Angle
from Phidget22.Devices.Stepper import Stepper
from Phidget22.Net import Net, PhidgetServerType
from Phidget22.PhidgetException import PhidgetException

__all__ = ["MyStepper"]

# The maximum acceleration of the stepper motor [deg/sec].
ACCELERATION = 60000
# Time to wait for the stepper motor to report that it is attached.
ATTACH_WAIT_TIME = 2000

# Gear ratio from the documentation at
# https://www.phidgets.com/?tier=3&catid=24&pcid=21&prodid=341
GEAR_RATIO = 99.0 + 1044.0 / 2057.0
# The angle that one step covers. Since there are 200 steps in 360 deg, this
# corresponds to 1.8 deg.
STEP_ANGLE = 360.0 / 200.0
# The angle that each microstep covers [deg]. The Phidget stepper controller
# can command 1/16th steps.
MICROSTEP_ANGLE = STEP_ANGLE / 16.0
# The conversion of the internal motor microstep angle to the geared one, which
# is how much the shaft coming out of the gear box rotates per step [deg].
GEARED_MICROSTEP_ANGLE = MICROSTEP_ANGLE / GEAR_RATIO


class MyStepper:
    def __init__(
        self,
        initial_position: Angle,
        telescope_reduction: float,
        log: logging.Logger,
        hub_port: int,
        is_remote: bool = False,
    ) -> None:
        self.log = log.getChild(
            f"{type(self).__name__} {'Alt' if hub_port==0 else 'Az'}"
        )

        if is_remote:
            Net.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)

        self.stepper = Stepper()
        self.stepper.setHubPort(hub_port)
        self.stepper.setIsRemote(is_remote)
        self.stepper.setOnAttachHandler(self.on_attach)
        self.stepper.setOnDetachHandler(self.on_detach)
        self.stepper.setOnPositionChangeHandler(self.on_position_change)
        self.stepper.setOnVelocityChangeHandler(self.on_velocity_change)
        self.stepper.setOnErrorHandler(self.on_error)

        self.telescope_step_size = GEARED_MICROSTEP_ANGLE / telescope_reduction

        self.initial_position = initial_position
        self.target_position = Angle(0.0, u.deg)

        self.attached = False
        self.hub_port = hub_port

    def on_attach(self, _: typing.Any) -> None:
        """On attach callback."""
        self.log.info("Attach stepper!")
        self.attached = True

    def on_detach(self, _: typing.Any) -> None:
        """On detach callback."""
        self.log.info("Detach stepper!")
        self.attached = False

    def on_position_change(self, _: typing.Any, current_position: float) -> None:
        """On position change callback."""
        curr_pos = Angle(current_position, u.deg).wrap_at(360.0 * u.deg)
        self.log.debug(
            f"current_position={curr_pos.to_string(u.deg)} "
            "and self.target_position="
            f"{self.target_position.wrap_at(360.0 * u.deg).to_string(u.deg)}"
        )

    def on_velocity_change(self, _: typing.Any, current_velocity: float) -> None:
        """On velocity change callback."""
        cur_vel = Angle(current_velocity, u.deg)
        self.log.debug(f"self.current_velocity={cur_vel.to_string(u.deg)} / sec ")

    def on_error(self, code: int, description: str) -> None:
        self.log.error(f"{code=!s} -> {description=!s}")

    async def connect(self) -> None:
        """Connect the stepper motor."""
        try:
            self.stepper.openWaitForAttachment(ATTACH_WAIT_TIME)
        except PhidgetException as e:
            raise RuntimeError(e)
        self.stepper.setEngaged(True)
        self.stepper.setAcceleration(ACCELERATION)
        self.stepper.setRescaleFactor(self.telescope_step_size)
        self.stepper.setDataInterval(self.stepper.getMinDataInterval())
        self.stepper.addPositionOffset(self.initial_position.deg)

    async def disconnect(self) -> None:
        """Disconnect the stepper motor."""
        self.stepper.setEngaged(False)
        self.stepper.close()

    async def move(self, target_position: Angle, velocity: Angle) -> None:
        """Move to the indicated target position at the indicated velocity.

        Parameters
        ----------
        target_position: `Angle`
            The target position to slew to [deg].
        velocity: `Angle`
            The velocity at which to move [deg /sec].
        """
        # Compute the shortest path to the target position.
        current_position = Angle(self.stepper.getPosition(), u.deg)
        self.log.debug(f"move from {current_position} to {target_position}")
        new_target_position = current_position + (
            target_position - current_position
        ).wrap_at(180.0 * u.deg)
        # Now move to this target position.
        self.target_position = new_target_position
        self.stepper.setVelocityLimit(math.fabs(velocity.deg))
        self.stepper.setTargetPosition(self.target_position.deg)
