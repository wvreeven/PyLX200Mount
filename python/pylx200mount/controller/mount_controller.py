__all__ = ["MountController"]

import asyncio
import importlib
import logging
import types

from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

from ..alignment import AlignmentHandler
from ..camera import BaseCamera
from ..datetime_util import DatetimeUtil
from ..enums import MotorControllerState, MotorControllerType, SlewDirection, SlewRate
from ..motor.base_motor_controller import BaseMotorController
from ..my_math.astropy_util import (
    get_altaz_at_different_time,
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_alt_az,
    get_skycoord_from_ra_dec_str,
)
from ..observing_location import ObservingLocation
from ..plate_solver import BasePlateSolver
from .utils import load_camera_offsets, load_config, save_camera_offsets

# Angle of 90º.
NINETY = Angle(90.0, u.deg)
# Angle of 0º.
ZERO = Angle(0.0, u.deg)
# Position loop task interval [sec].
POSITION_INTERVAL = 0.5
# Plate solve loop task interval [sec].
PLATE_SOLVE_INTERVAL = 0.5

ZERO_ALT_AZ = get_skycoord_from_alt_az(
    alt=0.0,
    az=0.0,
    observing_location=ObservingLocation(),
    timestamp=DatetimeUtil.get_timestamp(),
)


class MountController:
    """Control the Mount."""

    def __init__(self, log: logging.Logger) -> None:
        self.log = log.getChild(type(self).__name__)
        self.observing_location = ObservingLocation()

        self.configuration: types.SimpleNamespace | None = None

        self.controller_type = MotorControllerType.NONE

        # The motor controllers.
        self.motor_controller_alt: BaseMotorController | None = None
        self.motor_controller_az: BaseMotorController | None = None

        # Position loop that is done, so it can be safely canceled at all times.
        self._position_loop_task: asyncio.Future = asyncio.Future()
        self._position_loop_task.set_result(None)
        self.should_run_position_loop = False
        self.motor_alt_az: SkyCoord = ZERO_ALT_AZ

        # Slew related variables.
        self.slew_direction = SlewDirection.NONE
        self.slew_rate = SlewRate.HIGH
        self.is_slewing = False

        # The plate solver.
        self.plate_solver: BasePlateSolver | None = None
        self.camera_mount_offset = (0.0 * u.deg, 0.0 * u.deg)

        # Plate solve loop that is done, so it can be safely canceled at all times.
        self._plate_solve_loop_task: asyncio.Future = asyncio.Future()
        self._plate_solve_loop_task.set_result(None)
        self.should_run_plate_solve_loop = False
        self.camera_alt_az = ZERO_ALT_AZ
        self.previous_camera_alt_az = ZERO_ALT_AZ

        # Alignment handler.
        self.alignment_handler = AlignmentHandler()

    async def load_motors_camera_and_plate_solver(self) -> None:
        """Helper method to load the configured motors, camera and plate solver."""
        self.configuration = load_config()
        assert self.configuration is not None

        if hasattr(self.configuration, "alt_module_name"):
            self.log.debug(
                f"Loading ALT motor "
                f"{self.configuration.alt_module_name}.{self.configuration.alt_class_name}."
            )
            self.log.debug(
                f"Loading AZ motor "
                f"{self.configuration.az_module_name}.{self.configuration.az_class_name}."
            )
            alt_motor_module = importlib.import_module(
                self.configuration.alt_module_name
            )
            alt_motor_class = getattr(
                alt_motor_module, self.configuration.alt_class_name
            )
            az_motor_module = importlib.import_module(self.configuration.az_module_name)
            az_motor_class = getattr(az_motor_module, self.configuration.az_class_name)

            # The motor controllers.
            self.motor_controller_alt = alt_motor_class(
                initial_position=Angle(0.0, u.deg),
                log=self.log,
                conversion_factor=Angle(self.configuration.alt_gear_reduction * u.deg),
                hub_port=self.configuration.alt_hub_port,
            )
            self.motor_controller_az = az_motor_class(
                initial_position=Angle(0.0, u.deg),
                log=self.log,
                conversion_factor=Angle(self.configuration.az_gear_reduction * u.deg),
                hub_port=self.configuration.az_hub_port,
            )
        else:
            self.log.warning("No motors connected.")

        if hasattr(self.configuration, "camera_module_name"):
            self.log.debug(
                f"Loading camera "
                f"{self.configuration.camera_module_name}.{self.configuration.camera_class_name}."
            )
            camera_module = importlib.import_module(
                self.configuration.camera_module_name
            )
            camera_class = getattr(camera_module, self.configuration.camera_class_name)
            camera: BaseCamera = camera_class(log=self.log)
            if self.configuration.camera_class_name == "EmulatedCamera":
                from ..emulation import EmulatedCamera, EmulatedPlateSolver

                camera = EmulatedCamera(log=self.log)
                self.plate_solver = EmulatedPlateSolver(
                    camera,
                    self.configuration.camera_focal_length,
                    self.log,
                )
            else:
                from ..plate_solver import PlateSolver

                self.plate_solver = PlateSolver(
                    camera,
                    self.configuration.camera_focal_length,
                    self.log,
                )

            camera_mount_offset = load_camera_offsets()
            self.camera_mount_offset = (
                camera_mount_offset[0] * u.deg,
                camera_mount_offset[1] * u.deg,
            )
        else:
            self.log.debug("No camera connected.")

        if self.motor_controller_alt and self.motor_controller_az:
            if self.plate_solver:
                self.controller_type = MotorControllerType.CAMERA_AND_MOTORS
            else:
                self.controller_type = MotorControllerType.MOTORS_ONLY
        elif self.plate_solver:
            self.controller_type = MotorControllerType.CAMERA_ONLY
        self.log.debug(f"{self.controller_type=}")

    async def start(self) -> None:
        """Start the mount controller.

        The main actions are to start the position loop, to connect the motors and to perform other start up
        actions.
        """
        self.log.info("Start called.")
        await self.load_motors_camera_and_plate_solver()
        await self.attach_motors()
        await self.start_plate_solver()
        self.log.info("Started.")

    async def start_plate_solver(self) -> None:
        """Let the camera start taking images and start the plate solve task."""
        if self.controller_type in [
            MotorControllerType.CAMERA_ONLY,
            MotorControllerType.CAMERA_AND_MOTORS,
        ]:
            assert self.plate_solver is not None
            try:
                self.log.debug("Starting plate solver.")
                await self.plate_solver.open_camera()
                await self.plate_solver.start_imaging()

                self.should_run_plate_solve_loop = True
                self._plate_solve_loop_task.cancel()
                await self._plate_solve_loop_task
                self._plate_solve_loop_task = asyncio.create_task(
                    self.plate_solve_loop()
                )
                self.log.debug("Plate solver started.")
            except Exception:
                self.log.exception(
                    "Error loading configured camera. Continuing without camera."
                )
                self.should_run_plate_solve_loop = False
                self.plate_solver = None
                if self.controller_type == MotorControllerType.CAMERA_AND_MOTORS:
                    self.controller_type = MotorControllerType.MOTORS_ONLY
                else:
                    self.controller_type = MotorControllerType.NONE

    async def attach_motors(self) -> None:
        """Attach the motors."""
        if self.motor_controller_alt is None or self.motor_controller_az is None:
            if self.controller_type == MotorControllerType.CAMERA_AND_MOTORS:
                self.controller_type = MotorControllerType.CAMERA_ONLY
            elif self.controller_type == MotorControllerType.MOTORS_ONLY:
                self.controller_type = MotorControllerType.NONE
            return

        await self.motor_controller_alt.connect()
        await self.motor_controller_az.connect()

        self.should_run_position_loop = True
        self._position_loop_task.cancel()
        await self._position_loop_task
        self._position_loop_task = asyncio.create_task(self.position_loop())

    async def position_loop(self) -> None:
        """The position loop.

        Get the motor positions every `POSITION_INTERVAL` seconds and let the motors track if necessary. The
        loop delay is non-drifiting.
        """
        assert self.motor_controller_alt is not None
        assert self.motor_controller_az is not None

        start_time = DatetimeUtil.get_timestamp()
        self.log.debug(f"position_loop starts at {start_time}")
        while self.should_run_position_loop:
            self.motor_alt_az = get_skycoord_from_alt_az(
                alt=self.motor_controller_alt.position.deg,
                az=self.motor_controller_az.position.deg,
                observing_location=self.observing_location,
                timestamp=DatetimeUtil.get_timestamp(),
            )

            self.check_motor_tracking(self.motor_controller_az)
            self.check_motor_tracking(self.motor_controller_alt)

            self.is_slewing = (
                self.motor_controller_az.state == MotorControllerState.SLEWING
                or self.motor_controller_alt.state == MotorControllerState.SLEWING
            )

            # Since the slew is performed to the AltAz at the end of the longest axis slew, tracking should
            # only start as soon as both motors have switched to tracking.
            if (
                self.motor_controller_az.state == MotorControllerState.TRACKING
                and self.motor_controller_alt.state == MotorControllerState.TRACKING
            ):
                timediff = 2.0 * POSITION_INTERVAL
                target_alt_az = get_altaz_at_different_time(
                    alt=self.motor_controller_alt.position.deg,
                    az=self.motor_controller_az.position.deg,
                    observing_location=self.observing_location,
                    timestamp=DatetimeUtil.get_timestamp(),
                    timediff=timediff,
                )

                await self.motor_controller_az.track(target_alt_az.az, timediff)
                await self.motor_controller_alt.track(target_alt_az.alt, timediff)

            remainder = (DatetimeUtil.get_timestamp() - start_time) % POSITION_INTERVAL
            try:
                await asyncio.sleep(POSITION_INTERVAL - remainder)
            except asyncio.CancelledError:
                # Ignore.
                pass

    def check_motor_tracking(self, motor: BaseMotorController) -> None:
        """Check if the provided motor is stopped.

        If the motor state is not stopped but the motor velocity is 0 deg/sec, then the motor state is set to
        `MotorControllerState.TRACKING`.

        Parameters
        ----------
        motor : `BaseMotorController`
            The motor to check.
        """
        if motor.state != MotorControllerState.STOPPED and motor.velocity == ZERO:
            motor.state = MotorControllerState.TRACKING

    async def stop(self) -> None:
        """Stop the mount controller.

        The main actions are to stop the position loop, to disconnect the motors and to perform other shut
        down actions.
        """
        self.log.info("Stop called.")
        await self.stop_plate_solver()
        await self.detach_motors()
        self.log.info("Stopped.")

    async def stop_plate_solver(self) -> None:
        """Stop the plate solve task and let the camera stop taking images."""
        if self.controller_type in [
            MotorControllerType.CAMERA_AND_MOTORS,
            MotorControllerType.CAMERA_ONLY,
        ]:
            self.log.debug(f"{self.controller_type=}")
            assert self.plate_solver is not None
            self.should_run_plate_solve_loop = False
            self._plate_solve_loop_task.cancel()
            await self._plate_solve_loop_task
            await self.plate_solver.stop_imaging()

    async def detach_motors(self) -> None:
        """Detach the motors and stop the position loop."""
        if self.motor_controller_alt is None or self.motor_controller_az is None:
            if self.controller_type == MotorControllerType.CAMERA_AND_MOTORS:
                self.controller_type = MotorControllerType.CAMERA_ONLY
            elif self.controller_type == MotorControllerType.MOTORS_ONLY:
                self.controller_type = MotorControllerType.NONE
            return

        self.should_run_position_loop = False
        self._position_loop_task.cancel()
        await self._position_loop_task

        await self.motor_controller_alt.disconnect()
        await self.motor_controller_az.disconnect()

    async def plate_solve_loop(self) -> None:
        start_time = DatetimeUtil.get_timestamp()
        self.log.debug(f"plate_solve_loop starts at {start_time}")
        assert self.plate_solver is not None
        while self.should_run_plate_solve_loop:
            now = DatetimeUtil.get_timestamp()
            try:
                self.previous_camera_alt_az = self.camera_alt_az
                camera_ra_dec = await self.plate_solver.solve()
                self.camera_alt_az = get_altaz_from_radec(
                    camera_ra_dec, self.observing_location, now
                )
                # Make sure that the motors know the camera position as well.
                if self.controller_type == MotorControllerType.CAMERA_AND_MOTORS:
                    assert self.motor_controller_alt is not None
                    assert self.motor_controller_az is not None
                    self.motor_controller_az.position = self.camera_alt_az.az
                    self.motor_controller_alt.position = self.camera_alt_az.alt
                self.log.debug(f"Camera RaDec = {camera_ra_dec.to_string('hmsdms')}")
                self.log.debug(f"Camera AltAz = {self.camera_alt_az.to_string('dms')}")

            except RuntimeError:
                self.log.exception("Error solving.")
                self.camera_alt_az = self.previous_camera_alt_az
            end = DatetimeUtil.get_timestamp()
            self.log.debug(f"Plate solve for mount AltAz took {end - now} s.")

            remainder = (
                DatetimeUtil.get_timestamp() - start_time
            ) % PLATE_SOLVE_INTERVAL
            try:
                await asyncio.sleep(PLATE_SOLVE_INTERVAL - remainder)
            except asyncio.CancelledError:
                # Ignore.
                pass

    async def get_ra_dec(self) -> SkyCoord:
        """Get the current RA and DEC of the mount.

        Since RA and DEC of the mount are requested in pairs, this method computes both
        the RA and DEC.

        Returns
        -------
        The right ascention and declination.
        """
        match self.controller_type:
            case MotorControllerType.CAMERA_ONLY:
                mount_alt_az = self.camera_alt_az.spherical_offsets_by(
                    self.camera_mount_offset[0], self.camera_mount_offset[1]
                )
            case MotorControllerType.MOTORS_ONLY:
                mount_alt_az = self.motor_alt_az
            case MotorControllerType.CAMERA_AND_MOTORS:
                if self.is_slewing:
                    mount_alt_az = self.motor_alt_az
                else:
                    mount_alt_az = self.camera_alt_az.spherical_offsets_by(
                        self.camera_mount_offset[0], self.camera_mount_offset[1]
                    )
            case _:
                mount_alt_az = ZERO_ALT_AZ

        ra_dec = get_radec_from_altaz(alt_az=mount_alt_az)
        return ra_dec

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
        now = DatetimeUtil.get_timestamp()

        # Determine the sky AltAz.
        sky_ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        sky_alt_az = get_altaz_from_radec(sky_ra_dec, self.observing_location, now)

        if self.controller_type in [
            MotorControllerType.CAMERA_ONLY,
            MotorControllerType.CAMERA_AND_MOTORS,
        ]:
            camera_alt_az = get_skycoord_from_alt_az(
                self.camera_alt_az.alt.deg,
                self.camera_alt_az.az.deg,
                self.observing_location,
                now,
            )
            # Get the camera AltAz and determine the offset w.r.t. the sky.
            self.camera_mount_offset = camera_alt_az.spherical_offsets_to(sky_alt_az)
            save_camera_offsets(
                self.camera_mount_offset[0].deg, self.camera_mount_offset[1].deg
            )
            self.log.debug(f"{self.camera_mount_offset=}")
        if self.controller_type in [
            MotorControllerType.MOTORS_ONLY,
            MotorControllerType.CAMERA_AND_MOTORS,
        ]:
            # Add an alignment point and compute the alignment matrix.
            assert self.motor_controller_alt is not None
            assert self.motor_controller_az is not None
            mount_alt_az = get_skycoord_from_alt_az(
                alt=self.motor_controller_alt.position.deg,
                az=self.motor_controller_az.position.deg,
                observing_location=self.observing_location,
                timestamp=DatetimeUtil.get_timestamp(),
            )
            self.alignment_handler.add_alignment_position(sky_alt_az, mount_alt_az)

            # Compute the mount AltAz from the sky AltAz and pass on to the motor controllers.
            sky_alt_az = self.alignment_handler.matrix_transform(sky_alt_az, now)
            self.motor_controller_az.position = sky_alt_az.az
            self.motor_controller_alt.position = sky_alt_az.alt

    async def set_slew_rate(self, cmd: str) -> None:
        """Set the slew rate.

        The command is part of the LX200 protocol.

        Parameters
        ----------
        cmd : `str`
            A set slew rate command.
        """
        match cmd:
            case "RC":
                self.slew_rate = SlewRate.CENTERING
            case "RG":
                self.slew_rate = SlewRate.GUIDING
            case "RM":
                self.slew_rate = SlewRate.FIND
            case "RS":
                self.slew_rate = SlewRate.HIGH
            case _:
                raise ValueError(f"Received unknown slew rate command {cmd}.")

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
        assert self.motor_controller_alt is not None
        assert self.motor_controller_az is not None

        now = DatetimeUtil.get_timestamp()
        ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        alt_az = get_altaz_from_radec(
            ra_dec=ra_dec, observing_location=self.observing_location, timestamp=now
        )

        # Compute slew times.
        az_slew_time = await self.motor_controller_az.estimate_slew_time(alt_az.az)
        alt_slew_time = await self.motor_controller_alt.estimate_slew_time(alt_az.alt)

        slew_time = max(az_slew_time, alt_slew_time)

        # Compute AltAz at the end of the slew.
        alt_az_after_slew = get_altaz_from_radec(
            ra_dec=ra_dec,
            observing_location=self.observing_location,
            timestamp=now + slew_time,
        )

        self.slew_direction = SlewDirection.NONE
        if alt_az_after_slew.alt.value > 0:
            self.slew_rate = SlewRate.HIGH
            await self.motor_controller_az.move(alt_az_after_slew.az)
            await self.motor_controller_alt.move(alt_az_after_slew.alt)
            return "0"
        else:
            return "1"

    async def slew_in_direction(self, cmd: str) -> None:
        """Slew the mount in the provided direction.

        Parameters
        ----------
        cmd : `str`
            The command that specifies which direction to slew to.
        """
        assert self.motor_controller_alt is not None
        assert self.motor_controller_az is not None

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

    async def stop_slew(self) -> None:
        """Stop the slew of both motors."""
        assert self.motor_controller_alt is not None
        assert self.motor_controller_az is not None

        self.slew_direction = SlewDirection.NONE
        await self.motor_controller_az.stop_motion()
        await self.motor_controller_alt.stop_motion()

    async def location_updated(self) -> None:
        """Update the location.

        Also stay pointed at the same altitude and azimuth.
        """
        pass
