import asyncio
import logging
from unittest import IsolatedAsyncioTestCase

from reeven.van.astro.controller.mount_controller import (
    MountController,
    MountControllerState,
    SlewMode,
)

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.INFO,
)


class Test(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mount_controller = MountController()
        await self.mount_controller.start()

    async def asyncTearDown(self):
        await self.mount_controller.stop()

    async def test_slew_to_altaz(self):
        ra_str = "13:00:00"
        dec_str = "+10*00:00"
        await self.mount_controller.set_ra_dec(ra_str=ra_str, dec_str=dec_str)
        target_ra_str = "13:10:00"
        target_dec_str = "+10*10:00"
        slew_to = await self.mount_controller.slew_to(
            ra_str=target_ra_str, dec_str=target_dec_str
        )
        self.assertEqual("0", slew_to)
        while self.mount_controller.state != MountControllerState.TRACKING:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, SlewMode.ALT_AZ)
            await asyncio.sleep(0.5)

    async def test_slew_to_radec(self):
        ra_str = "13:00:00"
        dec_str = "+10*00:00"
        await self.mount_controller.set_ra_dec(ra_str=ra_str, dec_str=dec_str)
        self.mount_controller.slew_mode = SlewMode.RA_DEC
        target_ra_str = "13:10:00"
        target_dec_str = "+10*10:00"
        slew_to = await self.mount_controller.slew_to(
            ra_str=target_ra_str, dec_str=target_dec_str
        )
        self.assertEqual("0", slew_to)
        while self.mount_controller.state != MountControllerState.TRACKING:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, SlewMode.ALT_AZ)
            await asyncio.sleep(0.5)
