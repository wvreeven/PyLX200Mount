__all__ = ["MountController"]

import asyncio
import logging

from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

from ..emulation.emulated_motor_controller import EmulatedMotorController
from ..enums import MotorControllerState, SlewDirection, SlewRate
from ..motor.base_motor_controller import BaseMotorController
from ..my_math.astropy_util import (
    compute_slew_time,
    get_altaz_at_different_time,
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_alt_az,
    get_skycoord_from_ra_dec_str,
)
from ..observing_location import ObservingLocation
from ..utils import get_time

# AltAz task interval [sec].
ALTAZ_INTERVAL = 0.1
# A limit to decide between slewing and tracking.
TRACKING_LIMIT = Angle(1.0, u.arcmin)
# Angle of 360º
THREE_SIXTY = Angle(360.0, u.deg)
# Angle of 180º
ONE_EIGHTY = Angle(180.0, u.deg)
# Angle of 90º.
NINETY = Angle(90.0, u.deg)
# Angle of 0º.
ZERO = Angle(0.0, u.deg)
# Position loop task interval [sec].
POSITION_INTERVAL = 2.0


class MountController:
    """Control the Mount."""

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.observing_location = ObservingLocation()

        # The motor controllers.
        self.motor_controller_alt: BaseMotorController = EmulatedMotorController(
            initial_position=Angle(0.0, u.deg),
            log=self.log,
            conversion_factor=Angle(0.0001 * u.deg),
            hub_port=0,
        )
        self.motor_controller_az: BaseMotorController = EmulatedMotorController(
            initial_position=Angle(0.0, u.deg),
            log=self.log,
            conversion_factor=Angle(0.0001 * u.deg),
            hub_port=1,
        )

        # Slew related variables
        self.slew_ref_time = get_time()
        self.target_ra_dec: SkyCoord | None = None
        self.slew_direction = SlewDirection.NONE
        self.slew_rate = SlewRate.HIGH

        # Create a Future that is done, so it can be safely canceled at all times.
        self._position_loop_task: asyncio.Future = asyncio.Future()
        self._position_loop_task.set_result(None)

    @property
    def telescope_alt_az(self) -> SkyCoord:
        alt_az = get_skycoord_from_alt_az(
            alt=self.motor_controller_alt.position.deg,
            az=self.motor_controller_az.position.deg,
            observing_location=self.observing_location,
            timestamp=get_time(),
        )
        return alt_az

    @property
    def ra_dec(self) -> SkyCoord:
        ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
        return ra_dec

    async def start(self) -> None:
        """Start the mount controller.

        The main actions are to start the position loop, to connect the motors and to perform other start up
        actions.
        """
        self.log.info("Start called.")
        await self.attach_motors()
        if not self._position_loop_task.done():
            self._position_loop_task.cancel()
        self._position_loop_task = asyncio.create_task(self.position_loop())
        self.log.info("Started.")

    async def attach_motors(self) -> None:
        """Attach the motors."""
        await self.motor_controller_alt.connect()
        await self.motor_controller_az.connect()

    async def position_loop(self) -> None:
        start_time = get_time()
        self.log.debug(f"position_loop starts at {start_time}")
        while True:
            self.check_motor_stopped(self.motor_controller_az)
            self.check_motor_stopped(self.motor_controller_alt)

            timediff = 2.0 * POSITION_INTERVAL
            target_alt_az = get_altaz_at_different_time(
                alt=self.motor_controller_alt.position.deg,
                az=self.motor_controller_az.position.deg,
                observing_location=self.observing_location,
                timestamp=get_time(),
                timediff=timediff,
            )

            if self.motor_controller_az.state == MotorControllerState.TRACKING:
                await self.motor_controller_az.track(target_alt_az.az, timediff)
            if self.motor_controller_alt.state == MotorControllerState.TRACKING:
                await self.motor_controller_alt.track(target_alt_az.alt, timediff)

            remainder = (get_time() - start_time) % POSITION_INTERVAL
            await asyncio.sleep(POSITION_INTERVAL - remainder)

    def check_motor_stopped(self, motor: BaseMotorController) -> None:
        if motor.state != MotorControllerState.STOPPED and motor.velocity == ZERO:
            motor.state = MotorControllerState.TRACKING

    async def stop(self) -> None:
        """Stop the mount controller.

        The main actions are to stop the position loop, to disconnect the motors and to perform other shut
        down actions.
        """
        self.log.info("Stop called.")
        if not self._position_loop_task.done():
            self._position_loop_task.cancel()
        await self.detach_motors()

    async def detach_motors(self) -> None:
        """Detach the motors.

        Subclasses will need to implement this method. If any other show down actions need to be performed,
        they can be implemented in this method as well.
        """
        await self.motor_controller_alt.disconnect()
        await self.motor_controller_az.disconnect()

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
        self.target_ra_dec = get_skycoord_from_ra_dec_str(
            ra_str=ra_str, dec_str=dec_str
        )
        alt_az = get_altaz_from_radec(
            self.target_ra_dec, self.observing_location, get_time()
        )
        self.motor_controller_az.position = alt_az.az
        self.motor_controller_alt.position = alt_az.alt

    async def set_slew_rate(self, cmd: str) -> None:
        """Set the slew rate.

        The command is part of the LX200 protocol.

        Parameters
        ----------
        cmd : `str`
            A set slew rate command.
        """
        if cmd not in ["RC", "RG", "RM", "RS"]:
            raise ValueError(f"Received unknown slew rate command {cmd}.")
        if cmd == "RC":
            self.slew_rate = SlewRate.CENTERING
        elif cmd == "RG":
            self.slew_rate = SlewRate.GUIDING
        elif cmd == "RM":
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
        now = get_time()
        ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        alt_az = get_altaz_from_radec(
            ra_dec=ra_dec, observing_location=self.observing_location, timestamp=now
        )

        # Compute slew times.
        az_slew_time = compute_slew_time(self.motor_controller_az, alt_az.az.deg)
        alt_slew_time = compute_slew_time(self.motor_controller_alt, alt_az.alt.deg)

        # Compute az and alt at the end of the respective slews.
        alt_az_at_az_time = get_altaz_from_radec(
            ra_dec=ra_dec,
            observing_location=self.observing_location,
            timestamp=now + az_slew_time,
        )
        alt_az_at_alt_time = get_altaz_from_radec(
            ra_dec=ra_dec,
            observing_location=self.observing_location,
            timestamp=now + alt_slew_time,
        )

        self.slew_direction = SlewDirection.NONE
        if alt_az_at_alt_time.alt.value > 0:
            self.slew_ref_time = get_time()
            self.target_ra_dec = ra_dec
            self.slew_rate = SlewRate.HIGH
            await self.motor_controller_az.move(alt_az_at_az_time.az)
            await self.motor_controller_alt.move(alt_az_at_alt_time.alt)
            return "0"
        else:
            return "1"

    async def slew_in_direction(self, cmd: str) -> None:
        match cmd:
            case "Mn":
                self.slew_direction = SlewDirection.UP
                await self.motor_controller_alt.move(NINETY, self.slew_rate)
            case "Me":
                self.slew_direction = SlewDirection.LEFT
                await self.motor_controller_az.move(
                    self.motor_controller_az.position - NINETY, self.slew_rate
                )
            case "Ms":
                self.slew_direction = SlewDirection.DOWN
                await self.motor_controller_alt.move(ZERO, self.slew_rate)
            case "Mw":
                self.slew_direction = SlewDirection.RIGHT
                await self.motor_controller_az.move(
                    self.motor_controller_az.position + NINETY, self.slew_rate
                )
            case _:
                self.slew_direction = SlewDirection.NONE
                raise ValueError(f"Received unknown slew direction command {cmd}.")
        self.log.debug(f"SlewDirection = {self.slew_direction.name}")
        self.slew_ref_time = get_time()

    async def stop_slew(self) -> None:
        await self.motor_controller_az.stop_motion()
        await self.motor_controller_alt.stop_motion()

    async def location_updated(self) -> None:
        """Update the location.

        Also stay pointed at the same altitude and azimuth.
        """
        pass
