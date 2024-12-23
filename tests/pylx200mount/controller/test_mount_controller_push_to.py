import asyncio
import logging
import math
import pathlib
from unittest import IsolatedAsyncioTestCase, mock

import astropy.units as u
import numpy as np
import pylx200mount
from astropy.coordinates import SkyCoord

CONFIG_DIR = pathlib.Path(__file__).parents[1] / "test_data"

# RaDec of Polaris.
POLARIS = SkyCoord(37.95456067 * u.deg, 89.26410897 * u.deg)
# Camera offset for Alt [deg].
CAM_OFFSET_ALT = 1.0
# Camera offset for Az [deg].
CAM_OFFSET_AZ = 2.0
# Position offset tolerance [arcsec].
POSITION_OFFSET_TOLERANCE = 10


class TestMountControllerPushTo(IsolatedAsyncioTestCase):
    async def test_push_to(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.config_file = CONFIG_DIR / "config_emulated_camera_only.json"
        self.target_radec = pylx200mount.my_math.get_skycoord_from_ra_dec(0.0, 0.0)
        self.num_alignment_points_added = 0

        with mock.patch("pylx200mount.controller.utils.CONFIG_FILE", self.config_file):
            async with pylx200mount.controller.MountController(
                log=self.log
            ) as self.mount_controller:
                self.mount_controller.plate_solver.solve = self.solve  # type: ignore
                await self.add_camera_position(target=POLARIS)

                altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
                    alt=78.0,
                    az=320.0,
                    observing_location=self.mount_controller.observing_location,
                    timestamp=pylx200mount.DatetimeUtil.get_timestamp(),
                )
                radec = pylx200mount.my_math.get_radec_from_altaz(altaz)
                await self.add_camera_position(target=radec)

                altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
                    alt=61.0,
                    az=243.0,
                    observing_location=self.mount_controller.observing_location,
                    timestamp=pylx200mount.DatetimeUtil.get_timestamp(),
                )
                radec = pylx200mount.my_math.get_radec_from_altaz(altaz)
                await self.add_camera_position(target=radec)

                target_altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
                    alt=63.0,
                    az=211.0,
                    observing_location=self.mount_controller.observing_location,
                    timestamp=pylx200mount.DatetimeUtil.get_timestamp(),
                )
                radec = pylx200mount.my_math.get_radec_from_altaz(target_altaz)
                self.target_radec = radec
                await asyncio.sleep(0.5)
                self.log.debug(target_altaz.to_string("dms"))
                self.log.debug(self.mount_controller.camera_alt_az.to_string("dms"))
                now = pylx200mount.DatetimeUtil.get_timestamp()
                target_altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
                    target_altaz.alt.deg,
                    target_altaz.az.deg,
                    self.mount_controller.observing_location,
                    now,
                )
                camera_altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
                    self.mount_controller.camera_alt_az.alt.deg,
                    self.mount_controller.camera_alt_az.az.deg,
                    self.mount_controller.observing_location,
                    now,
                )
                self.log.debug(target_altaz.to_string("dms"))
                self.log.debug(camera_altaz.to_string("dms"))

                sep = target_altaz.separation(camera_altaz).arcsecond
                assert sep < 6.0

                mount_radec = await self.mount_controller.get_ra_dec()
                sep = radec.separation(mount_radec).deg
                assert sep < math.sqrt(CAM_OFFSET_AZ**2 + CAM_OFFSET_ALT**2)

    async def add_camera_position(self, target: SkyCoord) -> None:
        self.num_alignment_points_added += 1
        now = pylx200mount.DatetimeUtil.get_timestamp()
        target_altaz = pylx200mount.my_math.get_altaz_from_radec(
            target, self.mount_controller.observing_location, now
        )
        camera_altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
            target_altaz.alt.deg + CAM_OFFSET_ALT,
            target_altaz.az.deg + CAM_OFFSET_AZ,
            self.mount_controller.observing_location,
            now,
        )
        camera_radec = pylx200mount.my_math.get_radec_from_altaz(camera_altaz)
        self.target_radec = camera_radec
        await asyncio.sleep(0.5)
        await self.mount_controller.set_ra_dec(ra_dec=target)
        await asyncio.sleep(0.2)

        if self.num_alignment_points_added < 3:
            np.testing.assert_array_equal(
                self.mount_controller.camera_alignment_handler.matrix,
                pylx200mount.IDENTITY,
            )
        else:
            np.testing.assert_raises(
                AssertionError,
                np.testing.assert_array_equal,
                self.mount_controller.camera_alignment_handler.matrix,
                pylx200mount.IDENTITY,
            )
        await self.mount_controller.get_ra_dec()

    async def solve(self) -> SkyCoord:
        """Mock solve method."""
        return self.target_radec
