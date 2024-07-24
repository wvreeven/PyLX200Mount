import logging
import pathlib
from typing import Tuple
from unittest import IsolatedAsyncioTestCase, mock

import astropy.units as u
import pylx200mount
from astropy.coordinates import SkyCoord


def format_ra_dec_str(ra_dec: SkyCoord) -> Tuple[str, str]:
    ra = ra_dec.ra
    ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
    dec = ra_dec.dec
    dec_dms = dec.signed_dms
    dec_str = f"{dec_dms.sign * dec_dms.d:2.0f}*{dec_dms.m:2.0f}:{dec_dms.s:2.0f}"
    return ra_str, dec_str


class TestMountController(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        with mock.patch(
            "pylx200mount.controller.utils.CONFIG_FILE", pathlib.Path("/does_not_exist")
        ):
            log = logging.getLogger(type(self).__name__)
            self.mount_controller = pylx200mount.controller.MountController(log=log)
            alt_az = pylx200mount.my_math.get_skycoord_from_alt_az(
                alt=45.0,
                az=175.0,
                observing_location=self.mount_controller.observing_location,
                timestamp=pylx200mount.DatetimeUtil.get_timestamp(),
            )
            ra_dec = pylx200mount.my_math.get_radec_from_altaz(alt_az=alt_az)
            self.ra_str, self.dec_str = format_ra_dec_str(ra_dec)
            target_alt_az = pylx200mount.my_math.get_skycoord_from_alt_az(
                alt=48.0,
                az=179.0,
                observing_location=self.mount_controller.observing_location,
                timestamp=pylx200mount.DatetimeUtil.get_timestamp(),
            )
            target_ra_dec = pylx200mount.my_math.get_radec_from_altaz(
                alt_az=target_alt_az
            )
            self.target_ra_str, self.target_dec_str = format_ra_dec_str(target_ra_dec)
            await self.mount_controller.start()
            await self.mount_controller.set_ra_dec(
                ra_str=self.ra_str, dec_str=self.dec_str
            )

    async def asyncTearDown(self) -> None:
        await self.mount_controller.stop()

    async def test_slew_to_altaz(self) -> None:
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        assert "0" == slew_to

    async def test_slew_bad(self) -> None:
        bad_mode = "Bad"
        self.mount_controller.slew_mode = bad_mode  # type: ignore
        slew_to = await self.mount_controller.slew_to(
            ra_str=self.target_ra_str, dec_str=self.target_dec_str
        )
        assert "0" == slew_to

    async def test_slew_down(self) -> None:
        await self.mount_controller.slew_in_direction("Ms")
