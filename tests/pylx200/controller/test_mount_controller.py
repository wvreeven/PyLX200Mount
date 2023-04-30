import asyncio
from typing import Tuple
from unittest import IsolatedAsyncioTestCase

import astropy.units as u
import pylx200
from astropy.coordinates import Latitude, SkyCoord
from numpy import testing as np_testing


def format_ra_dec_str(ra_dec: SkyCoord) -> Tuple[str, str]:
    ra = ra_dec.ra
    ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
    dec = ra_dec.dec
    dec_dms = dec.signed_dms
    dec_str = f"{dec_dms.sign * dec_dms.d:2.0f}*{dec_dms.m:2.0f}:{dec_dms.s:2.0f}"
    return ra_str, dec_str


class Test(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.mount_controller = pylx200.controller.mount_controller.MountController(
            is_simulation_mode=True
        )
        alt_az = pylx200.my_math.get_skycoord_from_alt_az(
            alt=45.0,
            az=175.0,
            observing_location=self.mount_controller.observing_location,
        )
        ra_dec = pylx200.my_math.get_radec_from_altaz(alt_az=alt_az)
        self.ra_str, self.dec_str = format_ra_dec_str(ra_dec)
        target_alt_az = pylx200.my_math.get_skycoord_from_alt_az(
            alt=48.0,
            az=179.0,
            observing_location=self.mount_controller.observing_location,
        )
        target_ra_dec = pylx200.my_math.get_radec_from_altaz(alt_az=target_alt_az)
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
        while (
            self.mount_controller.state != pylx200.enums.MountControllerState.TRACKING
        ):
            self.assertEqual(
                self.mount_controller.state,
                pylx200.enums.MountControllerState.SLEWING,
            )
            self.assertEqual(
                self.mount_controller.slew_mode,
                pylx200.enums.SlewMode.ALT_AZ,
            )
            await asyncio.sleep(0.5)

    async def test_slew_to_radec(self) -> None:
        self.mount_controller.slew_mode = pylx200.enums.SlewMode.RA_DEC
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)
        while (
            self.mount_controller.state != pylx200.enums.MountControllerState.TRACKING
        ):
            self.assertEqual(
                self.mount_controller.state,
                pylx200.enums.MountControllerState.SLEWING,
            )
            self.assertEqual(
                self.mount_controller.slew_mode,
                pylx200.enums.SlewMode.RA_DEC,
            )
            await asyncio.sleep(0.5)

    async def test_slew_bad(self) -> None:
        bad_mode = "Bad"
        self.mount_controller.slew_mode = bad_mode
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        self.assertEqual("0", slew_to)

        while self.mount_controller.state != pylx200.enums.MountControllerState.STOPPED:
            self.assertEqual(
                self.mount_controller.state,
                pylx200.enums.MountControllerState.SLEWING,
            )
            self.assertEqual(self.mount_controller.slew_mode, bad_mode)
            await asyncio.sleep(0.5)

    async def test_slew_down(self) -> None:
        await self.mount_controller.slew_in_direction("Ms")
        alt = self.mount_controller.telescope_alt_az.alt.value
        while alt >= 44:
            self.assertEqual(
                self.mount_controller.state,
                pylx200.enums.MountControllerState.SLEWING,
            )
            await asyncio.sleep(0.5)
            alt = self.mount_controller.telescope_alt_az.alt.value
        await self.mount_controller.stop_slew()
        self.assertEqual(
            self.mount_controller.state,
            pylx200.enums.MountControllerState.TRACKING,
        )

    async def test_alignment(self) -> None:
        self.mount_controller.state = pylx200.enums.MountControllerState.STOPPED
        self.mount_controller.alignment_state = pylx200.enums.AlignmentState.UNALIGNED
        self.mount_controller.position_one_alignment_data = None
        self.mount_controller.position_two_alignment_data = None
        self.mount_controller.observing_location.set_latitude(
            Latitude((42 + (40 / 60)) * u.deg)
        )
        await self.mount_controller.location_updated()

        # s1 = 03h00m00s, +48d00m00s
        s1 = pylx200.my_math.get_skycoord_from_ra_dec_str(
            ra_str="03:00:00", dec_str="+48*00:00"
        )
        # s2 = 23h00m00s, +45d00m00s
        s2 = pylx200.my_math.get_skycoord_from_ra_dec_str(
            ra_str="23:00:00", dec_str="+45*00:00"
        )

        s1_ra_str, s1_dec_str = format_ra_dec_str(s1)
        await self.mount_controller.set_ra_dec(ra_str=s1_ra_str, dec_str=s1_dec_str)
        self.assertAlmostEqual(s1.ra.value, self.mount_controller.ra_dec.ra.value)
        self.assertAlmostEqual(s1.dec.value, self.mount_controller.ra_dec.dec.value)
        np_testing.assert_array_equal(
            self.mount_controller.alignment_handler.transformation_matrix,
            pylx200.enums.IDENTITY,
        )
        self.assertEqual(
            pylx200.enums.MountControllerState.TRACKING,
            self.mount_controller.state,
        )

        s2_ra_str, s2_dec_str = format_ra_dec_str(s2)
        self.mount_controller.ra_dec = s2
        await self.mount_controller.set_ra_dec(ra_str=s2_ra_str, dec_str=s2_dec_str)
        self.assertAlmostEqual(s2.ra.value, self.mount_controller.ra_dec.ra.value)
        self.assertAlmostEqual(s2.dec.value, self.mount_controller.ra_dec.dec.value)

        # Three alignment points have been added so the transformation matrix has been computed.
        with np_testing.assert_raises(AssertionError):
            np_testing.assert_array_equal(
                self.mount_controller.alignment_handler.transformation_matrix,
                pylx200.enums.IDENTITY,
            )
        self.assertEqual(
            pylx200.enums.MountControllerState.TRACKING,
            self.mount_controller.state,
        )