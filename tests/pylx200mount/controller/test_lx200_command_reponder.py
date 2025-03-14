import logging
import pathlib
from unittest import IsolatedAsyncioTestCase, mock

import pylx200mount
import pytest


class TestLx200CommandResponder(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        with mock.patch(
            "pylx200mount.controller.utils.CONFIG_FILE", pathlib.Path("/does_not_exist")
        ):
            log = logging.getLogger(type(self).__name__)
            self.responder = (
                pylx200mount.controller.lx200_command_reponder.Lx200CommandResponder(
                    log=log
                )
            )

    def assertEndsInHash(self, s: str) -> None:
        assert s.endswith("#")

    def assertDoesNotEndInHash(self, s: str) -> None:
        assert not s.endswith("#")

    async def test_get_ra(self) -> None:
        ra = await self.responder.get_ra()
        self.assertEndsInHash(ra)

    async def test_get_dec(self) -> None:
        de = await self.responder.get_dec()
        self.assertEndsInHash(de)

    async def test_set_ra(self) -> None:
        reply = await self.responder.set_ra("")
        assert reply == "1"

    async def test_set_dec(self) -> None:
        reply = await self.responder.set_dec("")
        assert reply == "1"

    async def test_get_clock_format(self) -> None:
        clock_format = await self.responder.get_clock_format()
        self.assertEndsInHash(clock_format)

    async def test_get_tracking_rate(self) -> None:
        tracking_rate = await self.responder.get_tracking_rate()
        self.assertEndsInHash(tracking_rate)

    async def test_get_utc_offset(self) -> None:
        utc_offset = await self.responder.get_utc_offset()
        self.assertEndsInHash(utc_offset)

    async def test_get_local_time(self) -> None:
        local_time = await self.responder.get_local_time()
        self.assertEndsInHash(local_time)

    async def test_get_current_date(self) -> None:
        current_date = await self.responder.get_current_date()
        self.assertEndsInHash(current_date)

    async def test_get_firmware_date(self) -> None:
        firmware_date = await self.responder.get_firmware_date()
        self.assertEndsInHash(firmware_date)

    async def test_get_firmware_time(self) -> None:
        firmware_time = await self.responder.get_firmware_time()
        self.assertEndsInHash(firmware_time)

    async def test_get_firmware_number(self) -> None:
        firmware_number = await self.responder.get_firmware_number()
        self.assertEndsInHash(firmware_number)

    async def test_get_firmware_name(self) -> None:
        firmware_name = await self.responder.get_firmware_name()
        self.assertEndsInHash(firmware_name)

    async def test_get_telescope_name(self) -> None:
        telescope_name = await self.responder.get_telescope_name()
        self.assertEndsInHash(telescope_name)

    async def test_get_current_site_latitude(self) -> None:
        current_site_latitude = await self.responder.get_current_site_latitude()
        self.assertEndsInHash(current_site_latitude)

    async def test_set_current_site_latitude_indi(self) -> None:
        current_site_latitude = await self.responder.set_current_site_latitude(
            "-29:56:29.7"
        )
        self.assertDoesNotEndInHash(current_site_latitude)

    async def test_set_current_site_latitude_misc(self) -> None:
        current_site_latitude = await self.responder.set_current_site_latitude("-29*56")
        self.assertDoesNotEndInHash(current_site_latitude)

    async def test_get_current_site_longitude(self) -> None:
        current_site_longitude = await self.responder.get_current_site_longitude()
        self.assertEndsInHash(current_site_longitude)

    async def test_set_current_site_longitude_indi(self) -> None:
        current_site_longitude = await self.responder.set_current_site_longitude(
            "-071:14:12.5"
        )
        self.assertDoesNotEndInHash(current_site_longitude)

    async def test_set_current_site_longitude_misc(self) -> None:
        current_site_longitude = await self.responder.set_current_site_longitude(
            "-071*14"
        )
        self.assertDoesNotEndInHash(current_site_longitude)

    async def test_get_site_1_name(self) -> None:
        site_1_name = await self.responder.get_site_1_name()
        self.assertEndsInHash(site_1_name)

    async def test_set_slew_rate(self) -> None:
        self.responder.cmd = pylx200mount.CommandName.RS.value
        await self.responder.set_slew_rate()

    async def test_stop_slew(self) -> None:
        with pytest.raises(AssertionError):
            await self.responder.stop_slew()

    async def test_set_utc_offset_time_date(self) -> None:
        reply = await self.responder.set_utc_offset("+1.0")
        assert reply == "1"
        reply = await self.responder.set_local_time("00:00:00")
        assert reply == "1"
        reply = await self.responder.set_local_date("02/02/22")
        assert reply[0] == "1"
