__all__ = ["PhidgetsStepper"]

import logging
import typing

from astropy.coordinates import Angle
from Phidget22.Devices.Stepper import Stepper
from Phidget22.Net import Net, PhidgetServerType
from Phidget22.PhidgetException import PhidgetException

from ..motor.base_motor_controller import BaseMotorController

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


class PhidgetsStepper(BaseMotorController):
    def __init__(
        self,
        initial_position: Angle,
        log: logging.Logger,
        conversion_factor: Angle,
        hub_port: int,
        is_remote: bool = True,
    ) -> None:
        is_alt = hub_port == 0
        super().__init__(log=log, is_alt=is_alt, conversion_factor=conversion_factor)

        if is_remote:
            Net.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)

        self._max_velocity = ACCELERATION
        self._max_acceleration = ACCELERATION

        self.stepper = Stepper()
        self.stepper.setHubPort(hub_port)
        self.stepper.setIsRemote(is_remote)
        self.stepper.setOnAttachHandler(self.on_attach)
        self.stepper.setOnDetachHandler(self.on_detach)
        self.stepper.setOnPositionChangeHandler(self.on_position_change)
        self.stepper.setOnVelocityChangeHandler(self.on_velocity_change)
        self.stepper.setOnErrorHandler(self.on_error)

        self._position_offset = round(
            (initial_position / self._conversion_factor).value
        )

        self.attached = False

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
        self._position = current_position

    def on_velocity_change(self, _: typing.Any, current_velocity: float) -> None:
        """On velocity change callback."""
        self._velocity = current_velocity

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
        self.stepper.setDataInterval(self.stepper.getMinDataInterval())

    async def disconnect(self) -> None:
        """Disconnect the stepper motor."""
        self.stepper.setEngaged(False)
        self.stepper.close()

    async def set_target_position_and_velocity(
        self, target_position_in_steps: float, max_velocity_in_steps: float
    ) -> None:
        assert self.stepper is not None
        self.stepper.setVelocityLimit(abs(max_velocity_in_steps))
        self.stepper.setTargetPosition(target_position_in_steps)
