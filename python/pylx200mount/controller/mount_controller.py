__all__ = ["MountController"]

import asyncio
import importlib
import json
import logging
import pathlib
import typing

import jsonschema
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

from ..alignment import AlignmentHandler
from ..camera import BaseCamera
from ..datetime_util import DatetimeUtil
from ..enums import MotorControllerState, SlewDirection, SlewRate
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

# Angle of 90º.
NINETY = Angle(90.0, u.deg)
# Angle of 0º.
ZERO = Angle(0.0, u.deg)
# Position loop task interval [sec].
POSITION_INTERVAL = 0.5

JSON_SCHEMA_FILE = pathlib.Path(__file__).parents[0] / "configuration_schema.json"
CONFIG_FILE = pathlib.Path.home() / ".config" / "pylx200mount" / "config.json"
DEFAULT_CONFIG: dict[str, typing.Any] = {
    "alt": {
        "module": "pylx200mount.emulation.emulated_motor_controller",
        "class_name": "EmulatedMotorController",
        "hub_port": 0,
        # 200 steps per revolution, 16 microsteps per step and a gear reduction of 2000x.
        "gear_reduction": 0.00005625,
    },
    "az": {
        "module": "pylx200mount.emulation.emulated_motor_controller",
        "class_name": "EmulatedMotorController",
        "hub_port": 1,
        # 200 steps per revolution, 16 microsteps per step and a gear reduction of 2000x.
        "gear_reduction": 0.00005625,
    },
    "camera": {
        "module": "pylx200mount.emulation.emulated_camera",
        "class_name": "EmulatedCamera",
    },
}


class MountController:
    """Control the Mount."""

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.observing_location = ObservingLocation()

        with open(JSON_SCHEMA_FILE, "r") as f:
            json_schema = json.load(f)
        self.validator = jsonschema.Draft7Validator(schema=json_schema)
        self.validator.validate(DEFAULT_CONFIG)

        config = DEFAULT_CONFIG
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            self.validator.validate(config)

        alt_module_name = (
            config["alt"]["module"]
            if config["alt"]["module"]
            else DEFAULT_CONFIG["alt"]["module"]
        )
        alt_class_name = (
            config["alt"]["class_name"]
            if config["alt"]["class_name"]
            else DEFAULT_CONFIG["alt"]["class_name"]
        )
        alt_hub_port = (
            config["alt"]["hub_port"]
            if config["alt"]["hub_port"]
            else DEFAULT_CONFIG["alt"]["hub_port"]
        )
        alt_gear_reduction = (
            config["alt"]["gear_reduction"]
            if config["alt"]["gear_reduction"]
            else DEFAULT_CONFIG["alt"]["gear_reduction"]
        )
        az_module_name = (
            config["az"]["module"]
            if config["az"]["module"]
            else DEFAULT_CONFIG["az"]["module"]
        )
        az_class_name = (
            config["az"]["class_name"]
            if config["az"]["class_name"]
            else DEFAULT_CONFIG["az"]["class_name"]
        )
        az_hub_port = (
            config["az"]["hub_port"]
            if config["az"]["hub_port"]
            else DEFAULT_CONFIG["az"]["hub_port"]
        )
        az_gear_reduction = (
            config["az"]["gear_reduction"]
            if config["az"]["gear_reduction"]
            else DEFAULT_CONFIG["az"]["gear_reduction"]
        )
        camera_module_name = (
            config["camera"]["module"]
            if config["camera"]["module"]
            else DEFAULT_CONFIG["camera"]["module"]
        )
        camera_class_name = (
            config["camera"]["class_name"]
            if config["camera"]["class_name"]
            else DEFAULT_CONFIG["camera"]["class_name"]
        )

        alt_motor_module = importlib.import_module(alt_module_name)
        alt_motor_class = getattr(alt_motor_module, alt_class_name)
        az_motor_module = importlib.import_module(az_module_name)
        az_motor_class = getattr(az_motor_module, az_class_name)
        camera_module = importlib.import_module(camera_module_name)
        camera_class = getattr(camera_module, camera_class_name)

        # The motor controllers.
        self.motor_controller_alt: BaseMotorController = alt_motor_class(
            initial_position=Angle(0.0, u.deg),
            log=self.log,
            conversion_factor=Angle(alt_gear_reduction * u.deg),
            hub_port=alt_hub_port,
        )
        self.motor_controller_az: BaseMotorController = az_motor_class(
            initial_position=Angle(0.0, u.deg),
            log=self.log,
            conversion_factor=Angle(az_gear_reduction * u.deg),
            hub_port=az_hub_port,
        )

        # The camera and plate solver.
        self.camera: BaseCamera = camera_class()
        if camera_class_name == "EmulatedCamera":
            from ..emulation import EmulatedPlateSolver

            self.plate_solver: BasePlateSolver = EmulatedPlateSolver(self.camera)
        else:
            from ..plate_solver import PlateSolver

            self.plate_solver = PlateSolver(self.camera)
        self.camera_mount_offset = SkyCoord(0.0 * u.deg, 0.0 * u.deg, frame="icrs")
        self.previous_camera_position: SkyCoord | None = None

        # Slew related variables.
        self.slew_direction = SlewDirection.NONE
        self.slew_rate = SlewRate.HIGH
        self.is_slewing = False

        # Position loop that is done, so it can be safely canceled at all times.
        self._position_loop_task: asyncio.Future = asyncio.Future()
        self._position_loop_task.set_result(None)
        self.should_run_loop = True

        # Alignment handler.
        self.alignment_handler = AlignmentHandler()

    def _get_mount_alt_az(self) -> SkyCoord:
        """Get the current motor positions as AltAz coordinates.

        Returns
        -------
        `SkyCoord`
            The current motor positions as AltAz coordinates.
        """
        alt_az = get_skycoord_from_alt_az(
            alt=self.motor_controller_alt.position.deg,
            az=self.motor_controller_az.position.deg,
            observing_location=self.observing_location,
            timestamp=DatetimeUtil.get_timestamp(),
        )
        return alt_az

    async def _get_camera_alt_az(self) -> SkyCoord:
        """Get the current AltAz cordinates for the camera, if present.

        Returns
        -------
        `SkyCoord`
            The current camera AltAz coordinates.

        Raises
        ------
        RuntimeError
            In case no camera is present or plate solving fails.
        """
        camera_ra_dec = await self.plate_solver.solve()
        camera_alt_az = get_altaz_from_radec(
            camera_ra_dec, self.observing_location, DatetimeUtil.get_timestamp()
        )
        return camera_alt_az

    async def start(self) -> None:
        """Start the mount controller.

        The main actions are to start the position loop, to connect the motors and to perform other start up
        actions.
        """
        self.log.info("Start called.")
        await self.attach_motors()
        self.should_run_loop = True
        self._position_loop_task.cancel()
        await self._position_loop_task
        self._position_loop_task = asyncio.create_task(self.position_loop())
        await self.plate_solver.open_camera()
        await self.plate_solver.set_gain_and_exposure_time(
            gain=80, exposure_time=150000
        )
        self.log.info("Started.")

    async def attach_motors(self) -> None:
        """Attach the motors."""
        await self.motor_controller_alt.connect()
        await self.motor_controller_az.connect()

    async def position_loop(self) -> None:
        """The position loop.

        Get the motor positions every `POSITION_INTERVAL` seconds and let the motors track if necessary. The
        loop delay is non-drifiting.
        """
        start_time = DatetimeUtil.get_timestamp()
        self.log.debug(f"position_loop starts at {start_time}")
        while self.should_run_loop:
            self.check_motor_tracking(self.motor_controller_az)
            self.check_motor_tracking(self.motor_controller_alt)

            if (
                self.motor_controller_az.state == MotorControllerState.SLEWING
                or self.motor_controller_alt.state == MotorControllerState.SLEWING
            ):
                self.is_slewing = True
            else:
                self.is_slewing = False

            timediff = 2.0 * POSITION_INTERVAL
            target_alt_az = get_altaz_at_different_time(
                alt=self.motor_controller_alt.position.deg,
                az=self.motor_controller_az.position.deg,
                observing_location=self.observing_location,
                timestamp=DatetimeUtil.get_timestamp(),
                timediff=timediff,
            )

            # Since the slew is performed to the AltAz at the end of the longest axis slew, tracking should
            # only start as soon as both motors have switched to tracking.
            if (
                self.motor_controller_az.state == MotorControllerState.TRACKING
                and self.motor_controller_alt.state == MotorControllerState.TRACKING
            ):
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
        self.should_run_loop = False
        self._position_loop_task.cancel()
        await self._position_loop_task
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
        try:
            camera_alt_az = await self._get_camera_alt_az()
            mount_alt_az = camera_alt_az.spherical_offsets_by(
                self.camera_mount_offset.ra, self.camera_mount_offset.dec
            )
            self.previous_camera_position = camera_alt_az
        except RuntimeError:
            if self.previous_camera_position is not None:
                mount_alt_az = self.previous_camera_position
            else:
                mount_alt_az = self._get_mount_alt_az()

        sky_alt_az = self.alignment_handler.reverse_matrix_transform(mount_alt_az)
        ra_dec = get_radec_from_altaz(alt_az=sky_alt_az)
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
        sky_ra_dec = get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        # Compute the sky AltAz from the sky RaDec.
        sky_alt_az = get_altaz_from_radec(
            sky_ra_dec, self.observing_location, DatetimeUtil.get_timestamp()
        )

        # Add an alignment point and compute the alignment matrix.
        self.alignment_handler.add_alignment_position(
            sky_alt_az, self._get_mount_alt_az
        )

        # Compute the mount AltAz from the sky AltAz and pass on to the motor controllers.
        mount_alt_az = self.alignment_handler.matrix_transform(sky_alt_az)
        self.motor_controller_az.position = mount_alt_az.az
        self.motor_controller_alt.position = mount_alt_az.alt

        # Get the camera AltAz and determine the offset w.r.t. the mount.
        try:
            camera_alt_az = await self._get_camera_alt_az()
            self.camera_mount_offset = camera_alt_az.spherical_offsets_to(mount_alt_az)
            self.log.info(f"{self.camera_mount_offset=}")
        except RuntimeError:
            # Deliberately left empty.
            pass

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
        await self.motor_controller_az.stop_motion()
        await self.motor_controller_alt.stop_motion()

    async def location_updated(self) -> None:
        """Update the location.

        Also stay pointed at the same altitude and azimuth.
        """
        pass
