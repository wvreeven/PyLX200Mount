import asyncio
import logging
from unittest import IsolatedAsyncioTestCase

import pylx200mount


class TestLx200Mount(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.lx200_mount = pylx200mount.LX200Mount(run_forever=False)
        self.log.debug("Before lx200_mount.start()")
        await self.lx200_mount.start()
        self.log.debug("After lx200_mount.start()")

    async def asyncTearDown(self) -> None:
        self.log.debug("Before lx200_mount.stop()")
        await self.lx200_mount.stop()
        self.log.debug("After lx200_mount.stop()")

    async def test_lx200_mount(self) -> None:
        reader, writer = await asyncio.open_connection(host="localhost", port=11880)
        writer.write(b"#")
        await writer.drain()
        # No reply expected.

        writer.write(b"\x06")
        await writer.drain()
        data = await reader.read(1)
        assert data == b"A"

        writer.write(b":H#")
        await writer.drain()
        # No reply expected.
