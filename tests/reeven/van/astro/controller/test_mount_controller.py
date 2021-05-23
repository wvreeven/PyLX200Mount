import asyncio
import logging
from unittest import IsolatedAsyncioTestCase

import astropy.units as u

from reeven.van.astro.controller.mount_controller import MountController
from reeven.van.astro.controller.enums import MountControllerState, SlewMode

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.DEBUG,
)


def format_ra_dec_str(ra_dec):
    ra = ra_dec.ra
    ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
    dec = ra_dec.dec
    dec_dms = dec.signed_dms
    dec_str = f"{dec_dms.sign * dec_dms.d:2.0f}*{dec_dms.m:2.0f}:{dec_dms.s:2.0f}"
    return ra_str, dec_str


class Test(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mount_controller = MountController()
        alt_az = self.mount_controller.get_skycoord_from_alt_az(alt=45.0, az=175.0)
        ra_dec = self.mount_controller.get_radec_from_altaz(alt_az=alt_az)
        self.ra_str, self.dec_str = format_ra_dec_str(ra_dec)
        target_alt_az = self.mount_controller.get_skycoord_from_alt_az(
            alt=48.0, az=179.0
        )
        target_ra_dec = self.mount_controller.get_radec_from_altaz(alt_az=target_alt_az)
        self.target_ra_str, self.target_dec_str = format_ra_dec_str(target_ra_dec)
        await self.mount_controller.start()
        await self.mount_controller.set_ra_dec(ra_str=self.ra_str, dec_str=self.dec_str)

    async def asyncTearDown(self):
        await self.mount_controller.stop()

    async def test_slew_to_altaz(self):
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)
        while self.mount_controller.state != MountControllerState.TRACKING:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, SlewMode.ALT_AZ)
            await asyncio.sleep(0.5)

    async def test_slew_to_radec(self):
        self.mount_controller.slew_mode = SlewMode.RA_DEC
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)
        while self.mount_controller.state != MountControllerState.TRACKING:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, SlewMode.RA_DEC)
            await asyncio.sleep(0.5)

    async def test_slew_bad(self):
        bad_mode = "Bad"
        self.mount_controller.slew_mode = bad_mode
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)

        while self.mount_controller.state != MountControllerState.STOPPED:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, bad_mode)
            await asyncio.sleep(0.5)

    async def test_slew_down(self):
        await self.mount_controller.slew_in_direction("Ms")
        alt = self.mount_controller.alt_az.alt.value
        while alt >= 44:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            await asyncio.sleep(0.5)
            alt = self.mount_controller.alt_az.alt.value
        await self.mount_controller.stop_slew()
        self.assertEqual(self.mount_controller.state, MountControllerState.TRACKING)
