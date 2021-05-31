#!/usr/bin/env python

import asyncio
import logging

from reeven.van.astro import SocketServer


async def main():
    logging.info("main method.")
    server = SocketServer()
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
        level=logging.INFO,
    )

    try:
        logging.info("Calling main method.")
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
