import asyncio
import logging
import math
from datetime import datetime, timedelta

import astropy.units as u
from astropy.coordinates import Angle, SkyCoord

from ..my_math.astropy_util import (
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_alt_az,
)
from ..observing_location import ObservingLocation
from .my_stepper import MyStepper

__all__ = ["MyAltAz"]

# AltAz task interval [sec].
ALTAZ_INTERVAL = 0.2
# A limit to decide between slewing and tracking.
TRACKING_LIMIT = Angle(1.0, u.arcmin)


class MyAltAz:
    def __init__(
        self,
        observing_location: ObservingLocation,
        telescope_reduction: float,
        log: logging.Logger,
        is_remote: bool = False,
    ) -> None:
        self.log = log.getChild(f"{type(self).__name__}")
        self.observing_location = observing_location
        self.telesope_reduction = telescope_reduction
        self.track_task: asyncio.Future = asyncio.Future()
        self.target_radec: SkyCoord = SkyCoord(0.0, 0.0, frame="icrs", unit="deg")
        self.current_altaz = get_skycoord_from_alt_az(
            alt=90.0, az=0.0, observing_location=observing_location
        )
        self.stepper_alt = MyStepper(
            initial_position=self.current_altaz.alt,
            telescope_reduction=self.telesope_reduction,
            log=self.log,
            hub_port=0,
            is_remote=True,
        )
        self.stepper_az = MyStepper(
            initial_position=self.current_altaz.az,
            telescope_reduction=self.telesope_reduction,
            log=self.log,
            hub_port=1,
            is_remote=True,
        )
        self.running = False
        self.mount_stopped = True

    async def timer_task(self) -> None:
        starttime = datetime.now()
        while self.running:
            now = datetime.now()
            dt = (now - starttime) % timedelta(seconds=ALTAZ_INTERVAL)
            delay = ALTAZ_INTERVAL - dt.seconds - dt.microseconds / 1000000.0
            self.log.debug(f"Sleeping for {delay} sec.")
            await asyncio.sleep(delay)

            if not self.mount_stopped:
                altaz_time = datetime.now()
                target_altaz = get_altaz_from_radec(
                    self.target_radec,
                    observing_location=self.observing_location,
                    time=altaz_time + timedelta(seconds=2.0 * ALTAZ_INTERVAL),
                )
                self.current_altaz = get_skycoord_from_alt_az(
                    alt=self.stepper_alt.stepper.getPosition(),
                    az=self.stepper_az.stepper.getPosition(),
                    observing_location=self.observing_location,
                    time=altaz_time,
                )
                obstime_diff = (
                    target_altaz.obstime.to_datetime()
                    - self.current_altaz.obstime.to_datetime()
                )
                obstime_diff_sec = (
                    obstime_diff.seconds + obstime_diff.microseconds / 1000000.0
                )
                diff_alt = Angle(
                    target_altaz.alt.deg - self.current_altaz.alt.deg, u.deg
                )
                diff_az = Angle(target_altaz.az.deg - self.current_altaz.az.deg, u.deg)
                velocity_alt = diff_alt / obstime_diff_sec
                velocity_az = diff_az / obstime_diff_sec
                if math.fabs(diff_alt.deg) >= TRACKING_LIMIT.deg:
                    velocity_alt = Angle(
                        self.stepper_alt.stepper.getMaxVelocityLimit(), u.deg
                    )
                await self.stepper_alt.move(target_altaz.alt, velocity_alt)
                if math.fabs(diff_az.deg) >= TRACKING_LIMIT.deg:
                    velocity_az = Angle(
                        self.stepper_az.stepper.getMaxVelocityLimit(), u.deg
                    )
                await self.stepper_az.move(target_altaz.az, velocity_az)

    async def attach_steppers(self) -> None:
        await self.stepper_alt.connect()
        await self.stepper_az.connect()
        self.running = True
        self.track_task = asyncio.create_task(self.timer_task())

    async def stop_motion(self) -> None:
        self.mount_stopped = True
        self.stepper_alt.stepper.setVelocityLimit(0.0)
        self.stepper_az.stepper.setVelocityLimit(0.0)

    async def slew(self, altaz: SkyCoord) -> None:
        self.mount_stopped = False
        self.target_radec = get_radec_from_altaz(alt_az=altaz)
        await self.stepper_alt.move(
            altaz.alt, Angle(self.stepper_alt.stepper.getMaxVelocityLimit(), u.deg)
        )
        await self.stepper_az.move(
            altaz.az, Angle(self.stepper_az.stepper.getMaxVelocityLimit(), u.deg)
        )

    async def detach_steppers(self) -> None:
        self.running = False
        await self.track_task
        await self.stepper_alt.disconnect()
        await self.stepper_az.disconnect()
