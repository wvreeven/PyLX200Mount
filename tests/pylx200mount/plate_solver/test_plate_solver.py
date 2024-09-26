import logging
import math
from unittest import IsolatedAsyncioTestCase

import pylx200mount


class TestPlateSolver(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        log = logging.getLogger(type(self).__name__)
        camera = pylx200mount.emulation.EmulatedCamera(log=log)
        self.plate_solver = pylx200mount.plate_solver.PlateSolver(
            camera=camera, focal_length=25.0, log=log
        )

    async def test_plate_solver(self) -> None:
        sky_coord = await self.plate_solver.solve()
        assert math.isclose(sky_coord.ra.deg, 0.0)
        assert math.isclose(sky_coord.dec.deg, 0.0)
