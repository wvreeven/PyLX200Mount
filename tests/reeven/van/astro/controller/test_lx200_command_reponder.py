import logging
from unittest import IsolatedAsyncioTestCase

from reeven.van.astro import pmc

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.INFO,
)


class Test(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.responder = pmc.controller.lx200_command_reponder.Lx200CommandResponder()
        await self.responder.start()

    async def asyncTearDown(self) -> None:
        await self.responder.stop()

    def assertDoesNotEndInHash(self, s: str) -> None:
        self.assertFalse(
            s.endswith("#"), "This reply is expected to end in a hash symbol."
        )

    async def test_get_ra(self) -> None:
        ra = await self.responder.get_ra()
        self.assertDoesNotEndInHash(ra)

    async def test_get_dec(self) -> None:
        de = await self.responder.get_dec()
        self.assertDoesNotEndInHash(de)

    async def test_get_clock_format(self) -> None:
        clock_format = await self.responder.get_clock_format()
        self.assertDoesNotEndInHash(clock_format)

    async def test_get_tracking_rate(self) -> None:
        tracking_rate = await self.responder.get_tracking_rate()
        self.assertDoesNotEndInHash(tracking_rate)

    async def test_get_utc_offset(self) -> None:
        utc_offset = await self.responder.get_utc_offset()
        self.assertDoesNotEndInHash(utc_offset)

    async def test_get_local_time(self) -> None:
        local_time = await self.responder.get_local_time()
        self.assertDoesNotEndInHash(local_time)

    async def test_get_current_date(self) -> None:
        current_date = await self.responder.get_current_date()
        self.assertDoesNotEndInHash(current_date)

    async def test_get_firmware_date(self) -> None:
        firmware_date = await self.responder.get_firmware_date()
        self.assertDoesNotEndInHash(firmware_date)

    async def test_get_firmware_time(self) -> None:
        firmware_time = await self.responder.get_firmware_time()
        self.assertDoesNotEndInHash(firmware_time)

    async def test_get_firmware_number(self) -> None:
        firmware_number = await self.responder.get_firmware_number()
        self.assertDoesNotEndInHash(firmware_number)

    async def test_get_firmware_name(self) -> None:
        firmware_name = await self.responder.get_firmware_name()
        self.assertDoesNotEndInHash(firmware_name)

    async def test_get_telescope_name(self) -> None:
        telescope_name = await self.responder.get_telescope_name()
        self.assertDoesNotEndInHash(telescope_name)

    async def test_get_current_site_latitude(self) -> None:
        current_site_latitude = await self.responder.get_current_site_latitude()
        self.assertDoesNotEndInHash(current_site_latitude)

    async def test_set_current_site_latitude(self) -> None:
        current_site_latitude = await self.responder.set_current_site_latitude(
            "-29:56:29.7"
        )
        self.assertDoesNotEndInHash(current_site_latitude)

    async def test_get_current_site_longitude(self) -> None:
        current_site_longitude = await self.responder.get_current_site_longitude()
        self.assertDoesNotEndInHash(current_site_longitude)

    async def test_set_current_site_longitude(self) -> None:
        current_site_longitude = await self.responder.set_current_site_longitude(
            "-071:14:12.5"
        )
        self.assertDoesNotEndInHash(current_site_longitude)

    async def test_get_site_1_name(self) -> None:
        site_1_name = await self.responder.get_site_1_name()
        self.assertDoesNotEndInHash(site_1_name)

    async def test_set_slew_rate(self) -> None:
        self.responder.cmd = "RS"
        slew_rate = await self.responder.set_slew_rate()
        self.assertTrue(slew_rate is None, "Received a reply but didn't expect one.")
