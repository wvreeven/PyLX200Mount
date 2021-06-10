import asyncio
import logging
import socket
from typing import Optional

from .controller import Lx200CommandResponder, REPLY_SEPARATOR

# ACK symbol sent by Ekos
ACK = b"\x06"

# Command start with a colon symbol
COLON = ":"

# Commands and replies are terminated by the hash symbol
HASH = b"#"


class SocketServer:
    def __init__(
        self,
    ) -> None:
        self.host = None
        self.port = 11880
        self._server: Optional[asyncio.AbstractServer] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self.responder = Lx200CommandResponder()

        self.log = logging.getLogger(type(self).__name__)

    async def start(self) -> None:
        """Start the TCP/IP server."""
        self.log.info("Start called.")
        await self.responder.start()
        self._server = await asyncio.start_server(
            self.cmd_loop, port=self.port, family=socket.AF_INET
        )
        self.log.info(
            f"Server started on host "
            f"{self._server.sockets[0].getsockname()[0]}"  # type: ignore
            f":{self._server.sockets[0].getsockname()[1]}"  # type: ignore
        )
        await self._server.wait_closed()

    async def stop(self) -> None:
        """Stop the TCP/IP server."""
        self.log.info("Stop called.")
        await self.responder.stop()
        if self._server is None:
            return

        server = self._server
        self._server = None
        self.log.info("Closing server.")
        server.close()
        self.log.info("Done closing.")

    async def write(self, st: str) -> None:
        """Write the string st appended with a HASH character.

        Parameters
        ----------
        st: `str`
            The string to append a HASH character to and then write.
        """
        reply = st.encode() + HASH
        self.log.debug(f"Writing reply {st}")
        if self._writer is not None:
            self._writer.write(reply)
            await self._writer.drain()

    async def cmd_loop(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Execute commands and output replies."""
        # self.log.info("Waiting for client to connect.")
        self._writer = writer

        # Just keep waiting for commands to arrive and then just process them and send a
        # reply.
        try:
            while True:
                # First read only one character and see if it is 0x06
                c = (await reader.read(1)).decode()
                self.log.debug(f"Read char {c!r}.")
                if c != ":":
                    self.log.debug(f"Writing ACK {c!r}.")
                    await self.write("A")
                else:
                    # All the next commands end in a # so we simply read all incoming
                    # strings up to # and
                    # parse them.
                    line_b = await reader.readuntil(HASH)
                    line = line_b.decode().strip()
                    if line not in ["GR#", "GD#"]:
                        self.log.info(f"Read command line: {line!r}")

                    # Almost all LX200 commands are unique but don't have a fixed length.
                    # So we simply loop over all implemented commands until we find
                    # the one that we have received. None of the implemented commands
                    # are non-unique so this is a safe way to do this without having
                    # to write too much boiler plate code.
                    cmd = ""
                    for key in self.responder.dispatch_dict.keys():
                        if line.startswith(key):
                            cmd = key

                    # Log a message if the command wasn't found.
                    if cmd not in self.responder.dispatch_dict:
                        self.log.error(f"Unknown command {cmd!r}.")

                    # Otherwise process the command.
                    else:
                        self.responder.cmd = cmd
                        (func, has_arg) = self.responder.dispatch_dict[cmd]
                        kwargs = {}
                        if has_arg:
                            # Read the function argument from the incoming command line
                            # and pass it on to the function.
                            data_start = len(cmd)
                            kwargs["data"] = line[data_start:-1]
                        output = await func(**kwargs)  # type: ignore
                        if output:
                            if REPLY_SEPARATOR in output:
                                # dirty trick to be able to send two output
                                # strings as is expected for e.g. "SC#"
                                outputs = output.split(REPLY_SEPARATOR)
                                for i in range(len(outputs) - 1):
                                    await self.write(output[0])
                                output = outputs[-1]
                            await self.write(output)

        except ConnectionResetError:
            pass


async def main() -> None:
    await socket_server.start()


if __name__ == "__main__":
    socket_server = SocketServer()
    try:
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        asyncio.run(socket_server.stop())
