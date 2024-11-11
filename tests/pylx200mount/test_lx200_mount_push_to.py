import asyncio
import pathlib
import tempfile

import astropy.units as u
import pylx200mount
from astropy.coordinates import SkyCoord
from base_lx200_mount_integration_test import BaseLx200MountIntegrationTest

# Position offset tolerance [arcsec].
POSITION_OFFSET_TOLERANCE = 10


class TestLx200MountPushTo(BaseLx200MountIntegrationTest):
    async def test_lx200_mount_push_to(self) -> None:
        config_file = (
            BaseLx200MountIntegrationTest.config_dir
            / "config_emulated_camera_only.json"
        )
        self.lx200_mount: pylx200mount.LX200Mount
        tmpdirname = tempfile.TemporaryDirectory()
        camera_offsets_file = pathlib.Path(tmpdirname.name) / "camera_offsets.ini"
        async with self.start_lx200_mount(config_file, camera_offsets_file):
            alt_az = pylx200mount.my_math.get_skycoord_from_alt_az(
                alt=40.0,
                az=179.0,
                observing_location=self.lx200_mount.responder.mount_controller.observing_location,
                timestamp=pylx200mount.DatetimeUtil.get_timestamp(),
            )
            self.target_ra_str, self.target_dec_str = self.get_ra_dec_str_from_alt_az(
                alt_az=alt_az
            )

            target = SkyCoord(
                self.target_ra_str,
                self.convert_lx200_coord_string(self.target_dec_str),
                unit=(u.hourangle, u.deg),
            )
            await asyncio.sleep(0.5)

            await self.write_command_string(f"{pylx200mount.CommandName.GR.value}")
            ra_bytes = await self.reader.readuntil(pylx200mount.HASH)
            ra_str = self.decode_binary_coord_string(ra_bytes)
            await self.write_command_string(f"{pylx200mount.CommandName.GD.value}")
            dec_bytes = await self.reader.readuntil(pylx200mount.HASH)
            dec_str = self.decode_binary_coord_string(dec_bytes)
            received = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg))
            sep = received.separation(target).arcsecond
            assert sep < POSITION_OFFSET_TOLERANCE

            assert not camera_offsets_file.exists()
            await self.write_command_string(
                f"{pylx200mount.CommandName.Sr.value}{self.target_ra_str}"
            )
            data = await self.reader.read(1)
            assert data == BaseLx200MountIntegrationTest.default_reply
            await self.write_command_string(
                f"{pylx200mount.CommandName.Sd.value}{self.target_dec_str}"
            )
            data = await self.reader.read(1)
            assert data == BaseLx200MountIntegrationTest.default_reply
            await self.write_command_string(f"{pylx200mount.CommandName.CM.value}")
            await self.reader.readuntil(pylx200mount.HASH)
            assert camera_offsets_file.exists()
