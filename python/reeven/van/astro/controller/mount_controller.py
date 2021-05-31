import asyncio
import logging
from typing import Optional

from astropy.coordinates import AltAz, Angle, SkyCoord  # type: ignore
from astropy.time import Time  # type: ignore
from astropy import units as u  # type: ignore

from reeven.van.astro.observing_location import ObservingLocation  # type: ignore
from reeven.van.astro.math.alignment_error_util import (  # type: ignore
    compute_alignment_error,
    get_altaz_in_rotated_frame,
)
from reeven.van.astro.controller.enums import (  # type: ignore
    MountControllerState,
    SlewMode,
    SlewDirection,
    SlewRate,
    AlignmentState,
)

__all__ = ["MountController"]


class MountController:
    """Control the Mount."""

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.observing_location = ObservingLocation()
        self.alt_az = self.get_skycoord_from_alt_az(90.0, 0.0)
        self.state = MountControllerState.STOPPED
        self.position_loop = None
        self.ra_dec = self.get_radec_from_altaz(self.alt_az)

        # Slew related variables
        self.slew_ref_time = 0.0
        self.target_ra_dec: SkyCoord = None
        self.slew_mode = SlewMode.ALT_AZ
        self.slew_direction: Optional[SlewDirection] = None
        self.slew_rate = SlewRate.HIGH

        # Alignment related variables
        self.alignment_state = AlignmentState.UNALIGNED
        self.position_one_alignment_data: Optional[SkyCoord] = None
        self.position_two_alignment_data: Optional[SkyCoord] = None
        self.delta_alt: Optional[float] = None
        self.delta_az: Optional[float] = None

    async def start(self) -> None:
        self.log.info("Start called.")
        self.position_loop = asyncio.create_task(self._start_position_loop())  # type: ignore
        self.log.info("Started.")

    async def stop(self) -> None:
        self.log.info("Stop called.")
        if self.position_loop:
            self.position_loop.cancel()

    async def _start_position_loop(self) -> None:
        """Start the position loop."""
        while True:
            self.log.debug(f"Mount state = {self.state.name}")
            if self.state == MountControllerState.STOPPED:
                await self._stopped()
            elif self.state == MountControllerState.TRACKING:
                await self._track()
            elif self.state == MountControllerState.SLEWING:
                await self._slew()
            else:
                msg = f"Invalid state encountered: {self.state}"
                self.log.error(msg)
                self.state = MountControllerState.STOPPED
                raise NotImplementedError(msg)
            # Loop at 10 Hz.
            await asyncio.sleep(0.1)

    async def _stopped(self) -> None:
        """Mount behavior in STOPPED state."""
        self.log.debug(
            f"Stopped at AltAz {self.alt_az.to_string()}"
            f" == RaDec {'None' if None else self.ra_dec.to_string('hmsdms')}."
        )
        self.ra_dec = self.get_radec_from_altaz(alt_az=self.alt_az)

    def _rotate_alt_az_if_necessray(self) -> None:
        if self.delta_alt and self.delta_az:
            time = Time.now()
            alt_az = get_altaz_in_rotated_frame(
                delta_alt=self.delta_alt,
                delta_az=self.delta_az,
                time=time,
                location=self.observing_location.location,
                altaz=self.alt_az,
            )
            self.log.debug(
                f"AltAz {self.alt_az.to_string('dms')} is rotated "
                f"{alt_az.to_string('dms')}"
            )

    async def _track(self) -> None:
        """Mount behavior in TRACKING state."""
        self.log.debug(
            f"Tracking at AltAz {self.alt_az.to_string()}"
            f" == RaDec {'None' if None else self.ra_dec.to_string('hmsdms')}."
        )
        self.alt_az = self.get_altaz_from_radec(ra_dec=self.ra_dec)
        self._rotate_alt_az_if_necessray()

    async def _slew(self) -> None:
        """Dispatch slewing to the coroutine corresponding to the slew mode."""
        if self.slew_mode == SlewMode.ALT_AZ:
            await self._slew_altaz()
        elif self.slew_mode == SlewMode.RA_DEC:
            await self._slew_radec()
        else:
            msg = f"Invalid slew mode encountered: {self.slew_mode}"
            self.log.error(msg)
            self.state = MountControllerState.STOPPED
            raise NotImplementedError(msg)

    async def _slew_radec(self) -> None:
        """RaDec mount behavior in SLEWING state."""
        self.log.debug(
            f"Slewing from RaDec ({self.ra_dec.to_string('hmsdms')}) "
            f"to RaDec ({self.target_ra_dec.to_string('hmsdms')})"
        )
        now = Time.now()
        ra, diff_ra = self._determine_new_coord_value(
            time=now, curr=self.ra_dec.ra.value, target=self.target_ra_dec.ra.value
        )
        dec, diff_dec = self._determine_new_coord_value(
            time=now, curr=self.ra_dec.dec.value, target=self.target_ra_dec.dec.value
        )
        self.ra_dec = self.get_skycoord_from_ra_dec(ra=ra, dec=dec)
        if diff_ra == 0 and diff_dec == 0:
            self.state = MountControllerState.TRACKING

        self.slew_ref_time = now

    def _determine_target_altaz(self) -> SkyCoord:
        """Determine the target AltAz for the slew that currently is being
        performed.

        For a normal slew, the target AltAz is determined by the RaDec of the
        target object. For directional slews, the target AltAz is determined by
        the direction that the slew is performed in.
        """
        if not self.slew_direction:
            target_altaz = self.get_altaz_from_radec(ra_dec=self.target_ra_dec)
        elif self.slew_direction == SlewDirection.UP:
            target_altaz = self.get_skycoord_from_alt_az(
                alt=90.0, az=self.alt_az.az.value
            )
        elif self.slew_direction == SlewDirection.LEFT:
            target_altaz = self.get_skycoord_from_alt_az(
                alt=self.alt_az.alt.value, az=self.alt_az.az.value - 1.0
            )
        elif self.slew_direction == SlewDirection.DOWN:
            target_altaz = self.get_skycoord_from_alt_az(
                alt=0.0, az=self.alt_az.az.value
            )
        else:
            target_altaz = self.get_skycoord_from_alt_az(
                alt=self.alt_az.alt.value, az=self.alt_az.az.value + 1.0
            )
        return target_altaz

    def _determine_new_coord_value(
        self, time: Time, curr: float, target: float
    ) -> tuple[float, float]:
        """Determine the new value of a coordinate during a slew.

        This function works for RA, Dec, Alt and Az equally well and the new
        value is determined for the provided Time.

        Parameters
        ----------
        time: `Time`
            The time for which to determine the new value for.
        curr: `float`
            The current value.
        target: `float`
            The target value to reach once the slew is done.

        Returns
        -------
        new_coord_value: `float`
            The new value of the coordinate.
        diff: `float`
            The difference between the new value and the target.
        """
        diff = target - curr
        diff_angle = Angle(diff * u.deg)
        diff = diff_angle.wrap_at(180.0 * u.deg).value
        time_diff = time - self.slew_ref_time
        step = self.slew_rate.value * time_diff.sec
        if diff < 0:
            step = -step
        if abs(diff) < abs(step):
            new_coord_value = target
            diff = 0
        else:
            new_coord_value = curr + step
        return new_coord_value, diff

    async def _slew_altaz(self) -> None:
        """AltAz mount behavior in SLEWING state."""
        now = Time.now()
        target_altaz = self._determine_target_altaz()
        self.log.debug(
            f"Slewing from AltAz ({self.alt_az.to_string()}) "
            f"to AltAz ({target_altaz.to_string()})"
        )

        alt, diff_alt = self._determine_new_coord_value(
            time=now, curr=self.alt_az.alt.value, target=target_altaz.alt.value
        )
        az, diff_az = self._determine_new_coord_value(
            time=now, curr=self.alt_az.az.value, target=target_altaz.az.value
        )
        self.alt_az = self.get_skycoord_from_alt_az(alt=alt, az=az)
        self._rotate_alt_az_if_necessray()
        self.ra_dec = self.get_radec_from_altaz(alt_az=self.alt_az)
        if diff_alt == 0 and diff_az == 0:
            self.state = MountControllerState.TRACKING

        self.slew_ref_time = now

    async def get_ra_dec(self) -> Optional[SkyCoord]:
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
        mount gets calclated as well.

        Parameters
        ----------
        ra_str: `str`
            The Right Ascension of the mount in degrees. The format is
            "HH:mm:ss".
        dec_str: `str`
            The Declination of the mount in degrees. The format is "+dd*mm:ss".
        """
        expected_ra_dec = self.ra_dec
        self.ra_dec = self.get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        self.alt_az = self.get_altaz_from_radec(ra_dec=self.ra_dec)
        self._rotate_alt_az_if_necessray()

        # Either the mount still is unaligned, or the mount is being aligned
        # with the same position.
        if self.alignment_state == AlignmentState.UNALIGNED or (
            self.alignment_state == AlignmentState.STAR_ONE_ALIGNED
            and self.position_one_alignment_data == self.ra_dec
        ):
            self.position_one_alignment_data = self.ra_dec
            self.alignment_state = AlignmentState.STAR_ONE_ALIGNED
            self.log.info(
                f"First position aligned at RaDec ({self.ra_dec.to_string('hmsdms')})."
            )
        # Either the mount is aligned with the first position only, or the mount is
        # being aligned with the same, second, position.
        elif self.alignment_state == AlignmentState.STAR_ONE_ALIGNED or (
            self.alignment_state == AlignmentState.ALIGNED
            and self.position_two_alignment_data == self.ra_dec
        ):
            self.position_two_alignment_data = self.ra_dec
            err_ra = self.ra_dec.ra.arcmin - expected_ra_dec.ra.arcmin
            err_dec = self.ra_dec.dec.arcmin - expected_ra_dec.dec.arcmin
            (self.delta_alt, self.delta_az,) = compute_alignment_error(
                lat=self.observing_location.location.lat,
                s1=self.position_one_alignment_data,
                s2=self.position_two_alignment_data,
                err_ra=err_ra,
                err_dec=err_dec,
            )
            self.alignment_state = AlignmentState.ALIGNED
            self.log.info(
                f"Second position aligned at RaDec ({self.ra_dec.to_string('hmsdms')})."
            )
            self.log.info(
                f"Alignment complete. AltAz offset ({self.delta_alt}, {self.delta_az}) "
                f"[arcmin]."
            )

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
        ra_dec = self.get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        alt_az = self.get_altaz_from_radec(ra_dec=self.ra_dec)
        self.slew_direction = None
        if alt_az.alt.value > 0:
            self.slew_ref_time = Time.now()
            self.target_ra_dec = ra_dec
            self.state = MountControllerState.SLEWING
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
        self.slew_ref_time = Time.now()
        self.state = MountControllerState.SLEWING

    async def stop_slew(self) -> None:
        """Stop the slew and start tracking where the mount is pointing at."""
        self.state = MountControllerState.TRACKING
        self.slew_direction = None

    async def location_updated(self) -> None:
        """Update the location but stay pointed at the same altitude and
        azimuth."""
        altitude = self.alt_az.alt.value
        azimuth = self.alt_az.az.value
        self.alt_az = self.get_skycoord_from_alt_az(alt=altitude, az=azimuth)
        self._rotate_alt_az_if_necessray()
        self.ra_dec = self.get_radec_from_altaz(alt_az=self.alt_az)

    # noinspection PyMethodMayBeStatic
    def get_skycoord_from_ra_dec(self, ra: float, dec: float) -> SkyCoord:
        return SkyCoord(
            ra=Angle(ra * u.deg),
            dec=Angle(dec * u.deg),
            frame="icrs",
        )

    # noinspection PyMethodMayBeStatic
    def get_skycoord_from_ra_dec_str(self, ra_str: str, dec_str: str) -> SkyCoord:
        return SkyCoord(
            ra=Angle(ra_str + " hours"),
            dec=Angle(dec_str.replace("*", ":") + " degrees"),
            frame="icrs",
        )

    def get_skycoord_from_alt_az(self, alt: float, az: float) -> SkyCoord:
        time = Time.now()
        return SkyCoord(
            alt=Angle(alt * u.deg),
            az=Angle(az * u.deg),
            frame="altaz",
            obstime=time,
            location=self.observing_location.location,
        )

    def get_altaz_from_radec(self, ra_dec: SkyCoord) -> SkyCoord:
        time = Time.now()
        return ra_dec.transform_to(
            AltAz(obstime=time, location=self.observing_location.location)
        )

    # noinspection PyMethodMayBeStatic
    def get_radec_from_altaz(self, alt_az: SkyCoord) -> SkyCoord:
        return alt_az.transform_to("icrs")
