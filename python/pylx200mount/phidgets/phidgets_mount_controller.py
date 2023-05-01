from datetime import datetime

import astropy.units as u
from astropy.coordinates import Angle, SkyCoord

from ..controller.base_mount_controller import BaseMountController
from ..enums import (
    TELESCOPE_REDUCTION_12INCH,
    MountControllerState,
    SlewDirection,
    SlewRate,
)
from ..my_math.astropy_util import get_radec_from_altaz, get_skycoord_from_alt_az
from .phidgets_stepper import PhidgetsStepper

# The maximum tracking speed.
TRACKING_SPEED = Angle(1.5, u.arcmin)


class PhidgetsMountController(BaseMountController):
    def __init__(self) -> None:
        super().__init__()
        self.stepper_alt = PhidgetsStepper(
            initial_position=self.telescope_alt_az.alt,
            telescope_reduction=TELESCOPE_REDUCTION_12INCH,
            log=self.log,
            hub_port=0,
            is_remote=True,
        )
        self.stepper_az = PhidgetsStepper(
            initial_position=self.telescope_alt_az.az,
            telescope_reduction=TELESCOPE_REDUCTION_12INCH,
            log=self.log,
            hub_port=1,
            is_remote=True,
        )

    async def attach_motors(self) -> None:
        try:
            await self.stepper_alt.connect()
            await self.stepper_az.connect()
        except RuntimeError:
            self.log.error("No stepper motors detected.")
            raise

    async def detach_motors(self) -> None:
        await self.stepper_alt.disconnect()
        await self.stepper_az.disconnect()

    async def track_mount(self) -> None:
        # TODO Split tracking for the motors because one can still be
        #  slewing while the other already is tracking.
        target_altaz = self._determine_target_altaz()
        await self.stepper_alt.move(target_altaz.alt, TRACKING_SPEED)
        await self.stepper_az.move(target_altaz.az, TRACKING_SPEED)
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=self.stepper_alt.current_position.deg,
            az=self.stepper_az.current_position.deg,
            observing_location=self.observing_location,
        )
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)

    async def slew_mount_altaz(self, now: datetime, target_altaz: SkyCoord) -> None:
        max_velocity = (
            self.stepper_alt.stepper.getMaxVelocityLimit()
            * self.slew_rate
            / SlewRate.HIGH
        )
        await self.stepper_alt.move(target_altaz.alt, Angle(max_velocity, u.deg))
        await self.stepper_az.move(target_altaz.az, Angle(max_velocity, u.deg))
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=self.stepper_alt.current_position.deg,
            az=self.stepper_az.current_position.deg,
            observing_location=self.observing_location,
            time=now,
        )

    async def stop_slew_mount(self) -> None:
        self.state = MountControllerState.TO_TRACKING
        self.stepper_alt.stepper.setVelocityLimit(0.0)
        self.stepper_az.stepper.setVelocityLimit(0.0)
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=self.stepper_alt.current_position.deg,
            az=self.stepper_az.current_position.deg,
            observing_location=self.observing_location,
        )
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
        if (
            self.stepper_alt.current_velocity.deg == 0.0
            and self.stepper_az.current_velocity.deg == 0.0
        ):
            self.state = MountControllerState.TRACKING
            self.slew_direction = SlewDirection.NONE
            self.target_ra_dec = self.ra_dec
