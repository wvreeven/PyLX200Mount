import asyncio
import logging
from typing import Tuple
from unittest import IsolatedAsyncioTestCase

from astropy.coordinates import Angle, Latitude, SkyCoord
import astropy.units as u

from reeven.van.astro.controller.mount_controller import MountController
from reeven.van.astro.controller.enums import (
    MountControllerState,
    SlewMode,
    AlignmentState,
)

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.DEBUG,
)


def format_ra_dec_str(ra_dec: SkyCoord) -> Tuple[str, str]:
    ra = ra_dec.ra
    ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
    dec = ra_dec.dec
    dec_dms = dec.signed_dms
    dec_str = f"{dec_dms.sign * dec_dms.d:2.0f}*{dec_dms.m:2.0f}:{dec_dms.s:2.0f}"
    return ra_str, dec_str


class Test(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
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

    async def asyncTearDown(self) -> None:
        await self.mount_controller.stop()

    async def test_slew_to_altaz(self) -> None:
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)
        while self.mount_controller.state != MountControllerState.TRACKING:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, SlewMode.ALT_AZ)
            await asyncio.sleep(0.5)

    async def test_slew_to_radec(self) -> None:
        self.mount_controller.slew_mode = SlewMode.RA_DEC
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)
        while self.mount_controller.state != MountControllerState.TRACKING:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            self.assertEqual(self.mount_controller.slew_mode, SlewMode.RA_DEC)
            await asyncio.sleep(0.5)

    async def test_slew_bad(self) -> None:
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

    async def test_slew_down(self) -> None:
        await self.mount_controller.slew_in_direction("Ms")
        alt = self.mount_controller.alt_az.alt.value
        while alt >= 44:
            self.assertEqual(self.mount_controller.state, MountControllerState.SLEWING)
            await asyncio.sleep(0.5)
            alt = self.mount_controller.alt_az.alt.value
        await self.mount_controller.stop_slew()
        self.assertEqual(self.mount_controller.state, MountControllerState.TRACKING)

    async def test_alignment(self) -> None:
        self.mount_controller.state = MountControllerState.STOPPED
        self.mount_controller.alignment_state = AlignmentState.UNALIGNED
        self.mount_controller.position_one_alignment_data = None
        self.mount_controller.position_two_alignment_data = None
        self.mount_controller.observing_location.set_latitude(
            Latitude((42 + (40 / 60)) * u.deg)
        )
        await self.mount_controller.location_updated()

        # s1 = 03h00m00s, +48d00m00s
        s1 = self.mount_controller.get_skycoord_from_ra_dec_str(
            ra_str="03:00:00", dec_str="+48*00:00"
        )
        # s2 = 23h00m00s, +45d00m00s
        s2 = self.mount_controller.get_skycoord_from_ra_dec_str(
            ra_str="23:00:00", dec_str="+45*00:00"
        )
        # s2_real = 23h00m48s, +45d21m00s
        s2_real_ra = s2.ra + Angle(12 * u.arcmin)
        s2_real_dec = s2.dec + Angle(21 * u.arcmin)
        s2_real = SkyCoord(ra=s2_real_ra, dec=s2_real_dec, frame="icrs")

        s1_ra_str, s1_dec_str = format_ra_dec_str(s1)
        await self.mount_controller.set_ra_dec(ra_str=s1_ra_str, dec_str=s1_dec_str)
        self.assertEqual(
            AlignmentState.STAR_ONE_ALIGNED, self.mount_controller.alignment_state
        )
        self.assertAlmostEqual(s1.ra.value, self.mount_controller.ra_dec.ra.value)
        self.assertAlmostEqual(s1.dec.value, self.mount_controller.ra_dec.dec.value)

        s2_ra_str, s2_dec_str = format_ra_dec_str(s2)
        self.mount_controller.ra_dec = s2
        await self.mount_controller.set_ra_dec(ra_str=s2_ra_str, dec_str=s2_dec_str)
        self.assertEqual(AlignmentState.ALIGNED, self.mount_controller.alignment_state)
        self.assertAlmostEqual(s2.ra.value, self.mount_controller.ra_dec.ra.value)
        self.assertAlmostEqual(s2.dec.value, self.mount_controller.ra_dec.dec.value)
        self.assertAlmostEqual(0.0, self.mount_controller.delta_alt)
        self.assertAlmostEqual(0.0, self.mount_controller.delta_az)

        self.mount_controller.alignment_state = AlignmentState.STAR_ONE_ALIGNED
        self.mount_controller.position_two_alignment_data = None
        self.mount_controller.ra_dec = s2_real
        await self.mount_controller.set_ra_dec(ra_str=s2_ra_str, dec_str=s2_dec_str)
        self.assertEqual(AlignmentState.ALIGNED, self.mount_controller.alignment_state)
        self.assertAlmostEqual(s2.ra.value, self.mount_controller.ra_dec.ra.value)
        self.assertAlmostEqual(s2.dec.value, self.mount_controller.ra_dec.dec.value)
        self.assertAlmostEqual(7.3897, self.mount_controller.delta_alt, 4)
        self.assertAlmostEqual(32.2597, self.mount_controller.delta_az, 4)
        self.assertEqual(MountControllerState.TRACKING, self.mount_controller.state)
