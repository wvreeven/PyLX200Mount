from __future__ import annotations

__all__ = ["POSITION_INTERVAL", "MountController"]

import asyncio
import importlib
import logging
import types

import numpy as np
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

from ..alignment import AlignmentHandler, TelescopeAltAzFrame
from ..camera import BaseCamera
from ..datetime_util import DatetimeUtil
from ..enums import IDENTITY, MILLISECOND, MotorControllerState, MotorControllerType, SlewDirection, SlewRate
from ..motor.base_motor_controller import BaseMotorController
from ..my_math.astropy_util import (
    get_altaz_frame,
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_altaz,
    get_skycoord_from_radec_str,
)
from ..plate_solver import BasePlateSolver
from .utils import load_config

# Angle of 90º.
NINETY = Angle(90.0, u.deg)
# Angle of 0º.
ZERO = Angle(0.0, u.deg)
# Position loop task interval [sec].
POSITION_INTERVAL = 0.25
# Track interval [sec].
TRACK_INTERVAL = 0.5


class MountController:
    """Control the Mount."""

    def __init__(self, log: logging.Logger) -> None:
        self.log = log.getChild(type(self).__name__)

        self.configuration: types.SimpleNamespace | None = None

        self.controller_type = MotorControllerType.NONE

        # The motor controllers.
        self.motor_controller_alt: BaseMotorController | None = None
        self.motor_controller_az: BaseMotorController | None = None
        self.motor_controller_alt_offset: Angle | None = None
        self.motor_controller_az_offset: Angle | None = None

        # Position loop that is done, so it can be safely canceled at all times.
        self._position_loop_task: asyncio.Future = asyncio.Future()
        self._position_loop_task.set_result(None)
        self.should_run_position_loop = False
        self.motor_altaz: SkyCoord | None = None

        # Target RaDec for moves and tracking.
        self.target_radec = SkyCoord(0.0 * u.deg, 0.0 * u.deg)
        self.track_start_datetime = 0.0

        # Position event to set in the position loop. Used by unit tests.
        self.position_event: asyncio.Event = asyncio.Event()

        # Slew related variables.
        self.slew_direction = SlewDirection.NONE
        self.slew_rate = SlewRate.HIGH

        # The plate solver.
        self.plate_solver: BasePlateSolver | None = None

        # Plate solve loop that is done, so it can be safely canceled at all times.
        self._plate_solve_loop_task: asyncio.Future = asyncio.Future()
        self._plate_solve_loop_task.set_result(None)
        self.should_run_plate_solve_loop = False
        self.camera_altaz: SkyCoord | None = None
        self.previous_camera_altaz: SkyCoord | None = None

        # Alignment handler.
        self.alignment_handler = AlignmentHandler()

    async def load_motors_camera_and_plate_solver(self) -> None:
        """Helper method to load the configured motors, camera, and plate solver."""
        zero_altaz = await get_skycoord_from_altaz(
            alt=0.0,
            az=0.0,
            timestamp=DatetimeUtil.get_timestamp(),
            frame=TelescopeAltAzFrame,
        )
        self.motor_altaz = zero_altaz
        self.camera_altaz = zero_altaz
        self.previous_camera_altaz = zero_altaz

        self.configuration = load_config()
        assert self.configuration is not None

        if hasattr(self.configuration, "alt_module_name"):
            self.log.debug(
                f"Loading ALT motor {self.configuration.alt_module_name}.{self.configuration.alt_class_name}."
            )
            self.log.debug(
                f"Loading AZ motor {self.configuration.az_module_name}.{self.configuration.az_class_name}."
            )
            alt_motor_module = importlib.import_module(self.configuration.alt_module_name)
            alt_motor_class = getattr(alt_motor_module, self.configuration.alt_class_name)
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
            if self.configuration.camera_class_name == "EmulatedCamera":
                from ..emulation import EmulatedCamera, EmulatedPlateSolver

                camera: BaseCamera = EmulatedCamera(log=self.log)
                self.plate_solver = EmulatedPlateSolver(
                    camera,
                    self.configuration.camera_focal_length,
                    self.log,
                )
            else:
                from ..plate_solver import PlateSolver

                camera_module = importlib.import_module(self.configuration.camera_module_name)
                camera_class = getattr(camera_module, self.configuration.camera_class_name)
                camera = camera_class(log=self.log)
                self.plate_solver = PlateSolver(
                    camera,
                    self.configuration.camera_focal_length,
                    self.log,
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

        The main actions are to start the position loop, to connect the motors, and to perform other startup
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
                self._plate_solve_loop_task = asyncio.create_task(self.plate_solve_loop())
                self.log.debug("Plate solver started.")
            except Exception:
                self.log.exception("Error loading configured camera. Continuing without camera.")
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
        start_time = DatetimeUtil.get_timestamp()
        self.log.debug(f"position_loop starts at {start_time}")
        while self.should_run_position_loop:
            await self.get_motor_positions()

            remainder = (DatetimeUtil.get_timestamp() - start_time) % POSITION_INTERVAL
            await asyncio.sleep(POSITION_INTERVAL - remainder)

    async def get_motor_positions(self) -> None:
        assert self.motor_controller_alt is not None
        assert self.motor_controller_az is not None
        now = DatetimeUtil.get_timestamp()

        self.motor_altaz = await get_skycoord_from_altaz(
            alt=self.motor_controller_alt.position.deg,
            az=self.motor_controller_az.position.deg,
            timestamp=now,
            frame=TelescopeAltAzFrame,
        )
        self.position_event.set()

        # Since the slew is performed to the AltAz at the end of the longest axis slew, tracking the position
        # should only start as soon as both motors are in TRACKING state.
        self.check_motor_tracking(self.motor_controller_az)
        self.check_motor_tracking(self.motor_controller_alt)
        if (
            self.motor_controller_az.state == MotorControllerState.TRACKING
            and self.motor_controller_alt.state == MotorControllerState.TRACKING
            and now - self.track_start_datetime >= TRACK_INTERVAL
        ):
            target_altaz = await get_altaz_from_radec(self.target_radec, now)
            motor_altaz = await self.alignment_handler.get_altaz_from_telescope_coords(self.motor_altaz)
            self.log.debug(f"{self.motor_altaz.to_string('dms')=}")
            self.log.debug(f"     {motor_altaz.to_string('dms')=}")
            self.log.debug(f"    {target_altaz.to_string('dms')=}")
            self.log.debug(f"{motor_altaz.separation(target_altaz).arcsecond=}")

            self.track_start_datetime = now
            time_diff = 2.0 * TRACK_INTERVAL
            fut_timestamp = now + time_diff
            target_altaz = await get_altaz_from_radec(self.target_radec, fut_timestamp)
            telescope_target_altaz = await self.alignment_handler.get_telescope_coords_from_altaz(
                target_altaz
            )

            await self.motor_controller_az.track(telescope_target_altaz.az, time_diff)
            await self.motor_controller_alt.track(telescope_target_altaz.alt, time_diff)

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

        The main actions are to stop the position loop, to disconnect the motors, and to perform other shut
        down actions.
        """
        self.log.info("Stop called.")
        await self.stop_plate_solver()
        await self.detach_motors()
        self.log.info("Stopped.")

    async def stop_plate_solver(self) -> None:
        """Stop the platesolve task and let the camera stop taking images."""
        if self.controller_type in [
            MotorControllerType.CAMERA_AND_MOTORS,
            MotorControllerType.CAMERA_ONLY,
        ]:
            self.log.debug(f"{self.controller_type=}")
            assert self.plate_solver is not None
            self.should_run_plate_solve_loop = False
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
        await self._position_loop_task

        await self.motor_controller_alt.disconnect()
        await self.motor_controller_az.disconnect()

    async def plate_solve_loop(self) -> None:
        start_time = DatetimeUtil.get_timestamp()
        self.log.debug(f"plate_solve_loop starts at {start_time}")
        while self.should_run_plate_solve_loop:
            await self.perform_plate_solve()

    async def perform_plate_solve(self) -> None:
        assert self.plate_solver is not None
        now = DatetimeUtil.get_timestamp()
        try:
            assert self.camera_altaz is not None
            self.previous_camera_altaz = self.camera_altaz
            camera_radec = await self.plate_solver.solve()
            self.camera_altaz = await get_altaz_from_radec(
                radec=camera_radec, timestamp=now, frame=TelescopeAltAzFrame
            )
            if self.controller_type == MotorControllerType.CAMERA_AND_MOTORS:
                # Make sure that the motors know the camera position as well.
                assert self.motor_controller_alt is not None
                assert self.motor_controller_az is not None
                if self.motor_controller_alt.state in [
                    MotorControllerState.TRACKING,
                    MotorControllerState.STOPPED,
                ] and self.motor_controller_az.state in [
                    MotorControllerState.TRACKING,
                    MotorControllerState.STOPPED,
                ]:
                    self.motor_controller_alt.position = self.camera_altaz.alt
                    self.motor_controller_az.position = self.camera_altaz.az

            self.log.debug("Camera RaDec = %s", camera_radec.to_string("hmsdms"))
            self.log.debug("Camera AltAz = %s", self.camera_altaz.to_string("dms"))

        except RuntimeError:
            self.log.exception("Error solving.")
            assert self.previous_camera_altaz is not None
            self.camera_altaz = self.previous_camera_altaz
        end = DatetimeUtil.get_timestamp()
        self.log.debug(f"Plate solve for mount AltAz took {end - now} s.")

    async def get_radec(self) -> SkyCoord:
        """Get the current RA and DEC of the mount.

        Since RA and DEC of the mount are requested in pairs, this method computes both
        the RA and DEC.

        Returns
        -------
        The right ascention and declination.
        """
        match self.controller_type:
            case MotorControllerType.CAMERA_ONLY:
                assert self.camera_altaz is not None
                mount_altaz = self.camera_altaz
            case MotorControllerType.MOTORS_ONLY:
                assert self.motor_altaz is not None
                mount_altaz = self.motor_altaz
            case MotorControllerType.CAMERA_AND_MOTORS:
                assert self.motor_controller_alt is not None
                assert self.motor_controller_az is not None
                if (
                    self.motor_controller_az.state == MotorControllerState.SLEWING
                    or self.motor_controller_alt.state == MotorControllerState.SLEWING
                ):
                    mount_altaz = self.motor_altaz
                else:
                    assert self.camera_altaz is not None
                    mount_altaz = self.camera_altaz
            case _:
                mount_altaz = await get_skycoord_from_altaz(
                    alt=0.0,
                    az=0.0,
                    timestamp=DatetimeUtil.get_timestamp(),
                    frame=TelescopeAltAzFrame,
                )

        sky_altaz = await self.alignment_handler.get_altaz_from_telescope_coords(mount_altaz)
        radec = await get_radec_from_altaz(altaz=sky_altaz)
        return radec

    async def determine_motor_offsets(self, sky_altaz: SkyCoord, telescope_altaz: SkyCoord) -> None:
        """Determine the motor offsets for the mount.

        Transform both SkyCoords to the same frame and compute the offsets between the two. This is only done
        if the motor offsets are zero and alignment has not yet been performed.

        Parameters
        ----------
        sky_altaz: `SkyCoord`
            The sky coordinates.
        telescope_altaz: `SkyCoord`
            The telescope coordinates.
        """
        if self.motor_controller_az_offset is None and np.array_equal(
            self.alignment_handler.matrix, IDENTITY
        ):
            temp_tel_altaz = await get_skycoord_from_altaz(
                telescope_altaz.alt.deg, telescope_altaz.az.deg, sky_altaz.obstime.datetime.timestamp()
            )
            temp_sky_altaz = await get_skycoord_from_altaz(
                sky_altaz.alt.deg, sky_altaz.az.deg, sky_altaz.obstime.datetime.timestamp()
            )
            self.motor_controller_az_offset, self.motor_controller_alt_offset = (
                temp_tel_altaz.spherical_offsets_to(temp_sky_altaz)
            )
            self.motor_controller_alt_offset = None
            self.motor_controller_az_offset = None

    async def set_radec(self, radec: SkyCoord) -> None:
        """Set the current RA and DEC of the mount.

        In case the mount has not been aligned yet, the AzAlt rotated frame of the
        mount gets calculated as well.

        Parameters
        ----------
        radec: `SkyCoord`
            The RA and Dec of the mount.
        """
        now = DatetimeUtil.get_timestamp()
        self.target_radec = radec

        # Determine the sky AltAz.
        sky_altaz = await get_altaz_from_radec(radec, now)

        if self.controller_type in [MotorControllerType.CAMERA_ONLY, MotorControllerType.CAMERA_AND_MOTORS]:
            assert self.camera_altaz is not None
            telescope_altaz = await get_skycoord_from_altaz(
                self.camera_altaz.alt.deg, self.camera_altaz.az.deg, now, TelescopeAltAzFrame
            )
            await self.determine_motor_offsets(sky_altaz, telescope_altaz)
        elif self.controller_type in [MotorControllerType.MOTORS_ONLY]:
            assert self.motor_controller_alt is not None
            assert self.motor_controller_az is not None
            telescope_altaz = await get_skycoord_from_altaz(
                self.motor_controller_alt.position.deg,
                self.motor_controller_az.position.deg,
                now,
                TelescopeAltAzFrame,
            )
            await self.determine_motor_offsets(sky_altaz, telescope_altaz)
        else:
            # Nothing to do.
            return

        await self.alignment_handler.add_alignment_position(altaz=sky_altaz, telescope=telescope_altaz)
        self.log.debug(
            "New alignment point SkyAltAz=%s and CameraAltAz=%s.",
            sky_altaz.to_string("dms"),
            telescope_altaz.to_string("dms"),
        )

        # Clean up motor offsets if alignment successful.
        if not np.array_equal(self.alignment_handler.matrix, IDENTITY):
            self.motor_controller_az_offset = None
            self.motor_controller_alt_offset = None

    async def set_slew_rate(self, cmd: str) -> None:
        """Set the slew rate.

        The command is part of the LX200 protocol.

        Parameters
        ----------
        cmd : `str`
            A set slew rate command.
        """
        await asyncio.sleep(MILLISECOND)

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
        self.target_radec = await get_skycoord_from_radec_str(ra_str=ra_str, dec_str=dec_str)
        self.log.debug("slew_to Set target_radec to %s.", self.target_radec.to_string("hmsdms"))
        target_altaz = await get_altaz_from_radec(radec=self.target_radec, timestamp=now)
        mount_altaz = await self.alignment_handler.get_telescope_coords_from_altaz(target_altaz)

        # Compute slew times.
        az_slew_time = await self.motor_controller_az.estimate_slew_time(mount_altaz.az)
        alt_slew_time = await self.motor_controller_alt.estimate_slew_time(mount_altaz.alt)

        slew_time = max(az_slew_time, alt_slew_time)

        # Compute AltAz at the end of the slew.
        fut_time = mount_altaz.obstime + slew_time * u.second
        fut_altaz_frame = await get_altaz_frame(fut_time)
        target_altaz_after_slew = self.target_radec.transform_to(fut_altaz_frame)
        mount_altaz_after_slew = await self.alignment_handler.get_telescope_coords_from_altaz(
            target_altaz_after_slew
        )

        self.slew_direction = SlewDirection.NONE
        if mount_altaz_after_slew.alt.value > 0:
            self.slew_rate = SlewRate.HIGH
            await self.motor_controller_az.move(mount_altaz_after_slew.az)
            await self.motor_controller_alt.move(mount_altaz_after_slew.alt)
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
        target_altaz = await get_skycoord_from_altaz(
            alt=self.motor_controller_alt.target_position.deg,
            az=self.motor_controller_az.target_position.deg,
            timestamp=DatetimeUtil.get_timestamp(),
            frame=TelescopeAltAzFrame,
        )
        sky_target_altaz = await self.alignment_handler.get_altaz_from_telescope_coords(target_altaz)
        self.target_radec = await get_radec_from_altaz(sky_target_altaz)
        self.log.debug("stop_slew Set target_radec to %s.", self.target_radec.to_string("hmsdms"))

    async def location_updated(self) -> None:
        """Update the location.

        Also stay pointed at the same altitude and azimuth.
        """
        pass

    async def __aenter__(self) -> MountController:
        await self.start()
        return self

    async def __aexit__(
        self,
        _type: None | BaseException,
        _value: None | BaseException,
        _traceback: None | types.TracebackType,
    ) -> None:
        await self.stop()
