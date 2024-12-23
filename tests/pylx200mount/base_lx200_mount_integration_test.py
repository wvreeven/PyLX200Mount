import asyncio
import contextlib
import datetime
import pathlib
import typing
from unittest import IsolatedAsyncioTestCase, mock

import astropy.units as u
import pylx200mount
from astropy.coordinates import SkyCoord


class BaseLx200MountIntegrationTest(IsolatedAsyncioTestCase):
    """Base class for LX200 mount integration tests."""

    target_ra_str = ""
    target_dec_str = ""
    config_dir = pathlib.Path(__file__).parent / "test_data"
    default_reply = b"1"

    @contextlib.asynccontextmanager
    async def start_lx200_mount(
        self, config_file: pathlib.Path
    ) -> typing.AsyncGenerator[None, None]:
        """Start the LX200 mount class and perform basic plumbing.

        Parameters
        ----------
        config_file : `str`
            The configuration file to load.

        Returns
        -------
        An empty generator.
        """
        tz_offset_hours = 1.0
        now = datetime.datetime.now(
            datetime.timezone(offset=datetime.timedelta(hours=tz_offset_hours))
        )

        with mock.patch("pylx200mount.controller.utils.CONFIG_FILE", config_file):
            async with pylx200mount.LX200Mount(run_forever=False) as self.lx200_mount:
                self.reader, self.writer = await asyncio.open_connection(
                    host="localhost", port=11880
                )

                # The order of commands as sent by SkySafari.
                # St set site latitude.
                await self.write_command_string(
                    f"{pylx200mount.CommandName.St.value}+40*30"
                )
                data = await self.reader.read(1)
                assert data == self.default_reply

                # Sg set site longitude.
                await self.write_command_string(
                    f"{pylx200mount.CommandName.S_LOWER_G.value}003*53"
                )
                data = await self.reader.read(1)
                assert data == self.default_reply

                # SG set site UTC offset.
                await self.write_command_string(
                    f"{pylx200mount.CommandName.S_UPPER_G.value}-01.0"
                )
                data = await self.reader.read(1)
                assert data == self.default_reply

                # SL set site local time.
                await self.write_command_string(
                    f"{pylx200mount.CommandName.SL.value}{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                )
                data = await self.reader.read(1)
                assert data == self.default_reply

                # SC set site local date.
                await self.write_command_string(
                    f"{pylx200mount.CommandName.SC.value}{now.month:02d}/{now.day:02d}/{now.strftime('%y')}"
                )
                data = await self.reader.read(1)
                assert data == self.default_reply
                data = await self.reader.readuntil(pylx200mount.HASH)
                assert data == b"Updating Planetary Data       #"
                data = await self.reader.readuntil(pylx200mount.HASH)
                assert data == b"                              #"

                # U set coordinate precision.
                await self.write_command_string(f"{pylx200mount.CommandName.U.value}")

                # RG set slew rate.
                await self.write_command_string(f"{pylx200mount.CommandName.RG.value}")

                yield

    async def write_command_string(self, command_str: str) -> None:
        self.writer.write(f":{command_str}#".encode())
        await self.writer.drain()

    async def solve(self) -> SkyCoord:
        """Mock solve method."""
        return pylx200mount.my_math.get_skycoord_from_ra_dec_str(
            self.target_ra_str, self.target_dec_str
        )

    def decode_binary_coord_string(self, coord_str: bytes) -> str:
        return self.convert_lx200_coord_string(coord_str.decode().strip("#"))

    def convert_lx200_coord_string(self, coord_str: str) -> str:
        return coord_str.replace("*", ":").replace("'", ":")

    def get_ra_dec_str_from_alt_az(self, alt_az: SkyCoord) -> tuple[str, str]:
        """Format the provided AltAz coordinates in RaDec string format as expected by the Meade LX200
        protocol.

        Parameters
        ----------
        alt_az : `SkyCoord`
            The AltAz cordinates.

        Returns
        -------
        `tuple`[`str`, `str`]
            The formatted right ascention and declination.
        """
        ra_dec = pylx200mount.my_math.get_radec_from_altaz(alt_az=alt_az)
        return self.get_ra_dec_str_from_ra_dec(ra_dec=ra_dec)

    def get_ra_dec_str_from_ra_dec(self, ra_dec: SkyCoord) -> tuple[str, str]:
        """Format the provided RaDec coordinates in RaDec string format as expected by the Meade LX200
        protocol.

        Parameters
        ----------
        ra_dec : `SkyCoord`
            The RaDec cordinates.

        Returns
        -------
        `tuple`[`str`, `str`]
            The formatted right ascention and declination.
        """
        ra = ra_dec.ra
        ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
        dec = ra_dec.dec
        dec_dms = dec.signed_dms
        dec_str = f"{dec_dms.sign * dec_dms.d:2.0f}*{dec_dms.m:2.0f}:{dec_dms.s:2.0f}"
        return ra_str, dec_str
