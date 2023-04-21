import asyncio
import logging
from datetime import datetime

from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

from ..my_math.astropy_util import (
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_alt_az,
    get_skycoord_from_ra_dec,
    get_skycoord_from_ra_dec_str,
)
from ..observing_location import ObservingLocation
from ..phidgets import MyStepper
from .enums import (
    TELESCOPE_REDUCTION_12INCH,
    AlignmentState,
    MountControllerState,
    SlewDirection,
    SlewMode,
    SlewRate,
)

__all__ = ["MountController"]

# AltAz task interval [sec].
ALTAZ_INTERVAL = 0.1
# A limit to decide between slewing and tracking.
TRACKING_LIMIT = Angle(1.0, u.arcmin)
# The maximum tracking speed.
TRACKING_SPEED = Angle(1.5, u.arcmin)


class MountController:
    """Control the Mount."""

    def __init__(self, is_simulation_mode: bool) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.observing_location = ObservingLocation()
        # TODO Use a telescope ALTAZ frame and SkyOffSet frame.
        self.telescope_alt_az = get_skycoord_from_alt_az(
            90.0, 0.0, self.observing_location
        )
        self.skyoffset_frame = self.telescope_alt_az.skyoffset_frame()
        self.state = MountControllerState.STOPPED
        self.position_loop: asyncio.Task | None = None
        self.ra_dec = get_radec_from_altaz(self.telescope_alt_az)
        self.stepper_alt = MyStepper(
            initial_position=self.telescope_alt_az.alt,
            telescope_reduction=TELESCOPE_REDUCTION_12INCH,
            log=self.log,
            hub_port=0,
            is_remote=True,
        )
        self.stepper_az = MyStepper(
            initial_position=self.telescope_alt_az.az,
            telescope_reduction=TELESCOPE_REDUCTION_12INCH,
            log=self.log,
            hub_port=1,
            is_remote=True,
        )
        self.is_simulation_mode = is_simulation_mode

        # Slew related variables
        self.slew_ref_time = datetime.now().astimezone()
        self.target_ra_dec: SkyCoord | None = None
        self.slew_mode = SlewMode.ALT_AZ
        self.slew_direction = SlewDirection.NONE
        self.slew_rate = SlewRate.HIGH

        # Alignment related variables
        self.alignment_state = AlignmentState.UNALIGNED
        self.position_one_alignment_data: SkyCoord | None = None
        self.position_two_alignment_data: SkyCoord | None = None

    async def start(self) -> None:
        self.log.info("Start called.")
        if not self.is_simulation_mode:
            try:
                await self.attach_steppers()
            except RuntimeError:
                self.log.warning("No stepper motors detected. Continuing.")
                self.is_simulation_mode = True
        self.position_loop = asyncio.create_task(self._start_position_loop())
        self.log.info("Started.")

    async def attach_steppers(self) -> None:
        await self.stepper_alt.connect()
        await self.stepper_az.connect()

    async def stop(self) -> None:
        self.log.info("Stop called.")
        if self.position_loop:
            self.position_loop.cancel()
        if not self.is_simulation_mode:
            await self.detach_steppers()

    async def detach_steppers(self) -> None:
        await self.stepper_alt.disconnect()
        await self.stepper_az.disconnect()

    async def _start_position_loop(self) -> None:
        """Start the position loop."""
        start_time = datetime.now().astimezone().timestamp()
        while True:
            if self.state == MountControllerState.STOPPED:
                await self._stopped()
            elif self.state == MountControllerState.TO_TRACKING:
                await self.stop_slew()
            elif self.state == MountControllerState.TRACKING:
                await self._track()
            elif self.state == MountControllerState.SLEWING:
                await self._slew()
            else:
                msg = f"Invalid state encountered: {self.state}"
                self.log.error(msg)
                self.state = MountControllerState.STOPPED
                raise NotImplementedError(msg)

            remainder = (datetime.now().timestamp() - start_time) % ALTAZ_INTERVAL
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
        if self.is_simulation_mode:
            self.telescope_alt_az = get_altaz_from_radec(
                ra_dec=self.ra_dec, observing_location=self.observing_location
            )
        else:
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
        if self.target_ra_dec is None:
            raise ValueError("self.target_ra_dec is None.")
        self.log.debug(
            f"Slewing from RaDec ({self.ra_dec.to_string('hmsdms')}) "
            f"to RaDec ({self.target_ra_dec.to_string('hmsdms')})"
        )
        now = datetime.now().astimezone()
        ra, diff_ra = self._determine_new_coord_value(
            time=now, curr=self.ra_dec.ra.value, target=self.target_ra_dec.ra.value
        )
        dec, diff_dec = self._determine_new_coord_value(
            time=now,
            curr=self.ra_dec.dec.value,
            target=self.target_ra_dec.dec.value,
        )
        self.ra_dec = get_skycoord_from_ra_dec(ra=ra, dec=dec)
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
    ) -> tuple[float, float]:
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
        diff: `float`
            The difference between the new value and the target.
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
            diff = 0
        else:
            new_coord_value = curr + step
        return new_coord_value, diff

    async def _slew_altaz(self) -> None:
        """AltAz mount behavior in SLEWING state."""
        now = datetime.now().astimezone()
        target_altaz = self._determine_target_altaz()
        self.log.debug(
            f"Slewing from AltAz ({self.telescope_alt_az.to_string()}) "
            f"to AltAz ({target_altaz.to_string()})"
        )
        if self.is_simulation_mode:
            alt, diff_alt = self._determine_new_coord_value(
                time=now,
                curr=self.telescope_alt_az.alt.value,
                target=target_altaz.alt.value,
            )
            az, diff_az = self._determine_new_coord_value(
                time=now,
                curr=self.telescope_alt_az.az.value,
                target=target_altaz.az.value,
            )
            self.telescope_alt_az = get_skycoord_from_alt_az(
                alt=alt, az=az, observing_location=self.observing_location
            )
            self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
            if diff_alt == 0 and diff_az == 0:
                self.state = MountControllerState.TRACKING
        else:
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

        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
        if self.telescope_alt_az.separation(target_altaz) <= TRACKING_LIMIT:
            self.state = MountControllerState.TRACKING
        self.slew_ref_time = now

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
        self.ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        self.telescope_alt_az = get_altaz_from_radec(
            ra_dec=self.ra_dec, observing_location=self.observing_location
        )

        # Either the mount still is unaligned, or the mount is being aligned
        # with the same position.
        if self.alignment_state == AlignmentState.UNALIGNED or (
            self.alignment_state == AlignmentState.STAR_ONE_ALIGNED
            and self.position_one_alignment_data is not None
            and self.position_one_alignment_data.ra == self.ra_dec.ra
            and self.position_one_alignment_data.dec == self.ra_dec.dec
        ):
            # If we use real motors, we need to add an offset so the motors
            # think we are where we actually are.
            if not self.is_simulation_mode:
                # await self.stepper_alt.set_real_position(
                #     self.telescope_alt_az.alt
                # )
                # await self.stepper_az.set_real_position(
                #     self.telescope_alt_az.az
                # )
                self.target_ra_dec = self.ra_dec

            self.position_one_alignment_data = self.ra_dec
            self.alignment_state = AlignmentState.STAR_ONE_ALIGNED
            self.log.info(
                f"First position aligned at RaDec ({self.ra_dec.to_string('hmsdms')})."
            )
        # Either the mount is aligned with the first position only, or the mount is
        # being aligned with the same, second, position.
        elif self.alignment_state == AlignmentState.STAR_ONE_ALIGNED or (
            self.alignment_state == AlignmentState.ALIGNED
            and self.position_two_alignment_data is not None
            and self.position_two_alignment_data.ra == self.ra_dec.ra
            and self.position_two_alignment_data.dec == self.ra_dec.dec
        ):
            # TODO Use a SkyOffsetFrame to store the tilt in the telescope
            #  plane w.r.t. the horizon.
            self.skyoffset_frame = self.telescope_alt_az.skyoffset_frame()
            alt_az = get_altaz_from_radec(self.ra_dec, self.observing_location)
            alt_az = alt_az.transform_to(self.skyoffset_frame)
            self.log.warning(
                f"SkyOffsetFrame = ({self.skyoffset_frame.origin.az}, "
                f"{self.skyoffset_frame.origin.alt}) == "
                f"alt_az {alt_az.to_string()}"
            )

            alt_az = get_altaz_from_radec(self.ra_dec, self.observing_location)
            self.log.warning(
                f"RaDec = {self.ra_dec.to_string('hmsdms')} == "
                f"alt_az {alt_az.to_string()}"
            )

            self.position_two_alignment_data = self.ra_dec
            self.log.info(
                f"Second position aligned at RaDec ({self.ra_dec.to_string('hmsdms')})."
            )
            self.target_ra_dec = self.ra_dec

            self.alignment_state = AlignmentState.ALIGNED

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

    async def stop_slew(self) -> None:
        """Stop the slew and start tracking where the mount is pointing at."""
        if self.is_simulation_mode:
            self.state = MountControllerState.TRACKING
            self.slew_direction = SlewDirection.NONE
        else:
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

    async def location_updated(self) -> None:
        """Update the location but stay pointed at the same altitude and
        azimuth."""
        alt = self.telescope_alt_az.alt.value
        az = self.telescope_alt_az.az.value
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=alt, az=az, observing_location=self.observing_location
        )
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
