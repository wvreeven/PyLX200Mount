import asyncio
import logging

from reeven.van.astro.controller.lx200_command_reponder import (
    Lx200CommandResponder,
    REPLY_SEPARATOR,
)

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.INFO,
)

# ACK symbol sent by Ekos
ACK = b"\x06"

# Command start with a colon symbol
COLON = ":"

# Commands and replies are terminated by the hash symbol
HASH = b"#"


class SocketServer:
    def __init__(
        self,
    ):
        self.host = None
        self.port = 11880
        self._server = None
        self._writer = None
        self.responder = Lx200CommandResponder()

        self.log = logging.getLogger(type(self).__name__)

    async def start(self):
        """Start the TCP/IP server."""
        self.log.info("Start called.")
        await self.responder.start()
        self._server = await asyncio.start_server(self.cmd_loop, port=self.port)
        msg = "Server started on host "
        i = 0
        for i in range(len(self._server.sockets) - 1):
            msg += f"{self._server.sockets[i].getsockname()[0]}:{self._server.sockets[i].getsockname()[1]}, "
        i = i + 1
        msg += f"{self._server.sockets[i].getsockname()[0]}:{self._server.sockets[i].getsockname()[1]}"
        self.log.info(msg)
        await self._server.wait_closed()

    async def stop(self):
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

    async def write(self, st):
        """Write the string st appended with a HASH character."""
        reply = st.encode()
        self.log.debug(f"Writing reply {reply}")
        self._writer.write(reply)
        await self._writer.drain()

    async def cmd_loop(self, reader, writer):
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
                    line = await reader.readuntil(HASH)
                    line = line.decode().strip()
                    if line not in ["GR#", "GD#"]:
                        self.log.info(f"Read command line: {line!r}")

                    # Almost all LX200 commands are unique but don't have a fixed length.
                    # So we simply loop over all implemented commands until we find
                    # the one that we have received. None of the implemented commands
                    # are non-unique so this is a safe way to do this without having
                    # to write too much boiler plate code.
                    cmd = None
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
                        output = await func(**kwargs)
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
            # self.log.info("Client disconnected.")
            pass


async def main():
    await socket_server.start()


if __name__ == "__main__":
    socket_server = SocketServer()
    try:
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        asyncio.run(socket_server.stop())