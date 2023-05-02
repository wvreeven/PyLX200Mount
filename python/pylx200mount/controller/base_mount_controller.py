import asyncio
import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime

from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

from ..alignment.alignment_handler import AlignmentHandler
from ..enums import MountControllerState, SlewDirection, SlewMode, SlewRate
from ..my_math.astropy_util import (
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_alt_az,
    get_skycoord_from_ra_dec_str,
)
from ..observing_location import ObservingLocation

__all__ = ["BaseMountController"]

# AltAz task interval [sec].
ALTAZ_INTERVAL = 0.1
# A limit to decide between slewing and tracking.
TRACKING_LIMIT = Angle(1.0, u.arcmin)


class BaseMountController(ABC):
    """Control the Mount."""

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.observing_location = ObservingLocation()
        self.telescope_alt_az = get_skycoord_from_alt_az(
            90.0, 0.0, self.observing_location
        )
        self.state = MountControllerState.STOPPED
        self.position_loop: asyncio.Task | None = None
        self.ra_dec = get_radec_from_altaz(self.telescope_alt_az)

        # Slew related variables
        self.slew_ref_time = datetime.now().astimezone()
        self.target_ra_dec: SkyCoord | None = None
        self.slew_mode = SlewMode.ALT_AZ
        self.slew_direction = SlewDirection.NONE
        self.slew_rate = SlewRate.HIGH

        # Alignment related variables
        # TODO Actually use the AlignmentHandler to compute the telescope frame and convert between AltAz and
        #  the telescope frame.
        self.alignment_handler = AlignmentHandler()

    async def start(self) -> None:
        self.log.info("Start called.")
        await self.attach_motors()
        self.position_loop = asyncio.create_task(self._start_position_loop())
        self.log.info("Started.")

    @abstractmethod
    async def attach_motors(self) -> None:
        raise NotImplementedError()

    async def stop(self) -> None:
        self.log.info("Stop called.")
        if self.position_loop:
            self.position_loop.cancel()
        await self.detach_motors()

    @abstractmethod
    async def detach_motors(self) -> None:
        raise NotImplementedError()

    async def _start_position_loop(self) -> None:
        """Start the position loop."""
        start_time = datetime.now().astimezone().timestamp()
        while True:
            if self.state == MountControllerState.STOPPED:
                await self._stopped()
            elif self.state == MountControllerState.TO_TRACKING:
                await self._stop_slew()
            elif self.state == MountControllerState.TRACKING:
                await self._track()
            elif self.state == MountControllerState.SLEWING:
                await self._slew()
            else:
                msg = f"Invalid state encountered: {self.state}"
                self.log.error(msg)
                self.state = MountControllerState.STOPPED
                raise NotImplementedError(msg)

            remainder = (
                datetime.now().astimezone().timestamp() - start_time
            ) % ALTAZ_INTERVAL
            await asyncio.sleep(ALTAZ_INTERVAL - remainder)

    async def _stopped(self) -> None:
        """Mount behavior in STOPPED state."""
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)

    async def _track(self) -> None:
        """Mount behavior in TRACKING state."""
        self.log.debug(
            f"Tracking at AltAz {self.telescope_alt_az.to_string()}"
            f" == RaDec {'None' if None else self.ra_dec.to_string('hmsdms')}."
        )
        target_altaz = self._determine_target_altaz()
        await self.track_mount(target_altaz=target_altaz)
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)

    @abstractmethod
    async def track_mount(self, target_altaz: SkyCoord) -> None:
        raise NotImplementedError()

    async def _slew(self) -> None:
        """Dispatch slewing to the coroutine corresponding to the slew mode."""
        if self.slew_mode == SlewMode.ALT_AZ:
            await self._slew_altaz()
        else:
            msg = f"Invalid slew mode encountered: {self.slew_mode}"
            self.log.error(msg)
            self.state = MountControllerState.STOPPED
            raise NotImplementedError(msg)

    def _determine_target_altaz(self) -> SkyCoord:
        """Determine the target AltAz for the slew that currently is being
        performed.

        For a normal slew, the target AltAz is determined by the RaDec of the
        target object. For directional slews, the target AltAz is determined by
        the direction that the slew is performed in.
        """
        if self.slew_direction == SlewDirection.NONE:
            target_altaz = get_altaz_from_radec(
                ra_dec=self.target_ra_dec, observing_location=self.observing_location
            )
        elif self.slew_direction == SlewDirection.UP:
            target_altaz = get_skycoord_from_alt_az(
                alt=self.telescope_alt_az.alt.value + 1.0,
                az=self.telescope_alt_az.az.value,
                observing_location=self.observing_location,
            )
        elif self.slew_direction == SlewDirection.LEFT:
            target_altaz = get_skycoord_from_alt_az(
                alt=self.telescope_alt_az.alt.value,
                az=self.telescope_alt_az.az.value - 1.0,
                observing_location=self.observing_location,
            )
        elif self.slew_direction == SlewDirection.DOWN:
            target_altaz = get_skycoord_from_alt_az(
                alt=self.telescope_alt_az.alt.value - 1.0,
                az=self.telescope_alt_az.az.value,
                observing_location=self.observing_location,
            )
        else:
            target_altaz = get_skycoord_from_alt_az(
                alt=self.telescope_alt_az.alt.value,
                az=self.telescope_alt_az.az.value + 1.0,
                observing_location=self.observing_location,
            )
        return target_altaz

    def _determine_new_coord_value(
        self, time: datetime, curr: float, target: float
    ) -> float:
        """Determine the new value of a coordinate during a slew.

        This function works for RA, Dec, Alt and Az equally well and the new
        value is determined for the provided Time.

        Parameters
        ----------
        time: `datetime`
            The time for which to determine the new value for.
        curr: `float`
            The current value.
        target: `float`
            The target value to reach once the slew is done.

        Returns
        -------
        new_coord_value: `float`
            The new value of the coordinate.
        """
        diff = target - curr
        diff_angle = Angle(diff * u.deg)
        diff = diff_angle.wrap_at(180.0 * u.deg).value
        time_diff = time - self.slew_ref_time
        step = self.slew_rate.value * time_diff.total_seconds()
        if diff < 0:
            step = -step
        if abs(diff) < abs(step):
            new_coord_value = target
        else:
            new_coord_value = curr + step
        return new_coord_value

    async def _slew_altaz(self) -> None:
        """AltAz mount behavior in SLEWING state."""
        now = datetime.now().astimezone()
        target_altaz = self._determine_target_altaz()
        self.log.debug(
            f"Slewing from AltAz ({self.telescope_alt_az.to_string()}) "
            f"to AltAz ({target_altaz.to_string()})"
        )
        await self.slew_mount_altaz(target_altaz=target_altaz, now=now)

        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
        if self.telescope_alt_az.separation(target_altaz) <= TRACKING_LIMIT:
            self.state = MountControllerState.TRACKING
        self.slew_ref_time = now

    @abstractmethod
    async def slew_mount_altaz(self, now: datetime, target_altaz: SkyCoord) -> None:
        raise NotImplementedError()

    async def get_ra_dec(self) -> SkyCoord:
        """Get the current RA and DEC of the mount.

        Since RA and DEC of the mount are requested in pairs, this method computes both
        the RA and DEC.

        Returns
        -------
        The right ascention and declination.
        """
        return self.ra_dec

    async def set_ra_dec(self, ra_str: str, dec_str: str) -> None:
        """Set the current RA and DEC of the mount.

        In case the mount has not been aligned yet, the AzAlt rotated frame of the
        mount gets calculated as well.

        Parameters
        ----------
        ra_str: `str`
            The Right Ascension of the mount in degrees. The format is
            "HH:mm:ss".
        dec_str: `str`
            The Declination of the mount in degrees. The format is "+dd*mm:ss".
        """
        actual_telescope_alt_az = get_altaz_from_radec(
            self.ra_dec, self.observing_location
        )
        self.ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        self.telescope_alt_az = get_altaz_from_radec(
            ra_dec=self.ra_dec, observing_location=self.observing_location
        )
        self.alignment_handler.add_alignment_position(
            self.telescope_alt_az, actual_telescope_alt_az
        )
        await self.alignment_handler.compute_alignment_matrix()
        self.target_ra_dec = self.ra_dec
        self.state = MountControllerState.TRACKING

    async def set_slew_rate(self, cmd: str) -> None:
        if cmd not in ["RC", "RG", "RM", "RS"]:
            raise ValueError(f"Received unknown slew rate command {cmd}.")
        if cmd == "RC":
            self.slew_rate = SlewRate.CENTERING
        elif cmd == "RG":
            self.slew_rate = SlewRate.GUIDING
        elif cmd == "RG":
            self.slew_rate = SlewRate.FIND
        else:
            self.slew_rate = SlewRate.HIGH

    async def slew_to(self, ra_str: str, dec_str: str) -> str:
        """Instruct the mount to slew to the target RA and DEC if possible.

        Parameters
        ----------
        ra_str: `str`
            The Right Ascension of the mount in degrees. The format is
            "HH:mm:ss".
        dec_str: `str`
            The Declination of the mount in degrees. The format is "+dd*mm:ss".

        Returns
        -------
        slew_possible: 0 or 1
            0 means in reach, 1 not.
        """
        ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        alt_az = get_altaz_from_radec(
            ra_dec=ra_dec, observing_location=self.observing_location
        )
        self.slew_direction = SlewDirection.NONE
        if alt_az.alt.value > 0:
            self.slew_ref_time = datetime.now().astimezone()
            self.target_ra_dec = ra_dec
            self.state = MountControllerState.SLEWING
            self.slew_rate = SlewRate.HIGH
            return "0"
        else:
            return "1"

    async def slew_in_direction(self, cmd: str) -> None:
        if cmd not in ["Mn", "Me", "Ms", "Mw"]:
            raise ValueError(f"Received unknown slew direction command {cmd}.")
        if self.slew_mode == SlewMode.ALT_AZ:
            if cmd == "Mn":
                self.slew_direction = SlewDirection.UP
            elif cmd == "Me":
                self.slew_direction = SlewDirection.LEFT
            elif cmd == "Ms":
                self.slew_direction = SlewDirection.DOWN
            else:
                self.slew_direction = SlewDirection.RIGHT
        else:
            if cmd == "Mn":
                self.slew_direction = SlewDirection.NORTH
            elif cmd == "Me":
                self.slew_direction = SlewDirection.EAST
            elif cmd == "Ms":
                self.slew_direction = SlewDirection.SOUTH
            else:
                self.slew_direction = SlewDirection.WEST
        self.slew_ref_time = datetime.now().astimezone()
        self.state = MountControllerState.SLEWING

    @abstractmethod
    async def stop_slew_mount(self) -> None:
        """Stop the slew and start tracking where the mount is pointing at."""
        raise NotImplementedError()

    async def _stop_slew(self) -> None:
        await self.stop_slew_mount()
        self.state = MountControllerState.TRACKING
        self.slew_direction = SlewDirection.NONE
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
        self.target_ra_dec = self.ra_dec

    async def location_updated(self) -> None:
        """Update the location but stay pointed at the same altitude and
        azimuth."""
        alt = self.telescope_alt_az.alt.value
        az = self.telescope_alt_az.az.value
        if (
            math.isclose(az, 0.0, abs_tol=1e-9)
            and math.isclose(alt, 90.0, abs_tol=1e-9)
            and self.observing_location.location.lat < 0.0
        ):
            self.log.info(
                f"{self.observing_location.location.lat} so setting az to 180.0º."
            )
            az = 180.0
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=alt, az=az, observing_location=self.observing_location
        )
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
