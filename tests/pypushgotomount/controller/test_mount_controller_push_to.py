import asyncio
import importlib
import logging
import math
import pathlib
from unittest import IsolatedAsyncioTestCase, mock

import astropy.units as u
import numpy as np
import pypushgotomount
from astropy.coordinates import SkyCoord
from pypushgotomount import datetime_util, observing_location

CONFIG_DIR = pathlib.Path(__file__).parents[1] / "test_data"

# RaDec of Polaris.
POLARIS = SkyCoord(37.95456067 * u.deg, 89.26410897 * u.deg)
# Camera offset for Alt [deg].
CAM_OFFSET_ALT = 0.0
# Camera offset for Az [deg].
CAM_OFFSET_AZ = 1.0
# Position offset tolerance [arcsec].
POSITION_OFFSET_TOLERANCE = 30.0


class TestMountControllerPushTo(IsolatedAsyncioTestCase):
    async def test_push_to(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        importlib.reload(datetime_util)
        importlib.reload(observing_location)
        self.config_file = CONFIG_DIR / "config_emulated_camera_only.json"
        self.target_radec = await pypushgotomount.my_math.get_skycoord_from_radec(0.0, 0.0)
        self.num_alignment_points_added = 0

        with mock.patch("pypushgotomount.controller.utils.CONFIG_FILE", self.config_file):
            async with pypushgotomount.controller.MountController(log=self.log) as self.mount_controller:
                self.mount_controller.plate_solver.solve = self.solve  # type: ignore
                await self.add_camera_position(target=POLARIS)
                polaris_altaz = self.mount_controller.camera_altaz
                assert polaris_altaz is not None

                altaz = await pypushgotomount.my_math.get_skycoord_from_altaz(
                    alt=polaris_altaz.alt.deg,
                    az=320.0,
                    timestamp=pypushgotomount.DatetimeUtil.get_timestamp(),
                )
                radec = await pypushgotomount.my_math.get_radec_from_altaz(altaz)
                await self.add_camera_position(target=radec)

                altaz = await pypushgotomount.my_math.get_skycoord_from_altaz(
                    alt=polaris_altaz.alt.deg,
                    az=243.0,
                    timestamp=pypushgotomount.DatetimeUtil.get_timestamp(),
                )
                radec = await pypushgotomount.my_math.get_radec_from_altaz(altaz)
                await self.add_camera_position(target=radec)

                target_altaz = await pypushgotomount.my_math.get_skycoord_from_altaz(
                    alt=polaris_altaz.alt.deg,
                    az=211.0,
                    timestamp=pypushgotomount.DatetimeUtil.get_timestamp(),
                )
                radec = await pypushgotomount.my_math.get_radec_from_altaz(target_altaz)
                self.target_radec = radec
                await asyncio.sleep(0.5)

                now = pypushgotomount.DatetimeUtil.get_timestamp()
                target_altaz = await pypushgotomount.my_math.get_skycoord_from_altaz(
                    target_altaz.alt.deg, target_altaz.az.deg, now
                )
                assert self.mount_controller.camera_altaz is not None
                camera_altaz = await pypushgotomount.my_math.get_skycoord_from_altaz(
                    self.mount_controller.camera_altaz.alt.deg,
                    self.mount_controller.camera_altaz.az.deg,
                    now,
                )
                telescope_radec = await self.mount_controller.get_radec()
                telescope_altaz = await pypushgotomount.my_math.get_altaz_from_radec(telescope_radec, now)

                target_camera_sep = target_altaz.separation(camera_altaz).arcsecond - CAM_OFFSET_AZ * 3600.0
                assert abs(target_camera_sep) < POSITION_OFFSET_TOLERANCE, (
                    f"{abs(target_camera_sep)=}, {POSITION_OFFSET_TOLERANCE=}"
                )

                telescope_camera_sep = telescope_altaz.separation(camera_altaz).deg
                assert math.isclose(
                    telescope_camera_sep,
                    math.sqrt(CAM_OFFSET_ALT**2 + CAM_OFFSET_AZ**2) * math.cos(telescope_altaz.alt.rad),
                    rel_tol=1e-3,
                )

    async def add_camera_position(self, target: SkyCoord) -> None:
        self.num_alignment_points_added += 1
        now = pypushgotomount.DatetimeUtil.get_timestamp()
        target_altaz = await pypushgotomount.my_math.get_altaz_from_radec(target, now)
        camera_altaz = await pypushgotomount.my_math.get_skycoord_from_altaz(
            target_altaz.alt.deg + CAM_OFFSET_ALT,
            target_altaz.az.deg + CAM_OFFSET_AZ,
            now,
        )
        camera_radec = await pypushgotomount.my_math.get_radec_from_altaz(camera_altaz)
        self.target_radec = camera_radec
        await asyncio.sleep(0.5)
        await self.mount_controller.set_radec(radec=target)
        await asyncio.sleep(0.2)

        if self.num_alignment_points_added < 3:
            np.testing.assert_array_equal(
                self.mount_controller.alignment_handler.matrix,
                pypushgotomount.IDENTITY,
            )
        else:
            np.testing.assert_raises(
                AssertionError,
                np.testing.assert_array_equal,
                self.mount_controller.alignment_handler.matrix,
                pypushgotomount.IDENTITY,
            )
        await self.mount_controller.get_radec()

    async def solve(self) -> SkyCoord:
        """Mock solve method."""
        return self.target_radec
