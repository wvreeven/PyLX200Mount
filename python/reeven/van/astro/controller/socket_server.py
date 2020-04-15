import asyncio
import logging

from reeven.van.astro.controller.lx200_command_reponder import Lx200CommandResponder

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s", level=logging.INFO,
)

# ACK symbol sent by Ekos
ACK = b"\x06"

# Command start with a colon symbol
COLON = ":"

# Commands and replies are terminated by the hash symbol
HASH = b"#"


class SocketServer:
    def __init__(self,):
        self.port = 11880
        self._server = None
        self._writer = None
        self.log = logging.getLogger("SocketServer")

    async def start(self):
        """Start the TCP/IP server."""
        self.log.info("Start called")
        self._server = await asyncio.start_server(self.cmd_loop, port=self.port)
        await self._server.wait_closed()

    async def stop(self):
        """Stop the TCP/IP server."""
        if self._server is None:
            return

        server = self._server
        self._server = None
        self.log.info("Closing server")
        server.close()
        self.log.info("Done closing")

    async def write(self, st):
        """Write the string st appended with a HASH character."""
        reply = st.encode()
        self.log.info("Writing reply {}".format(reply))
        self._writer.write(reply)
        await self._writer.drain()

    async def cmd_loop(self, reader, writer):
        """Execute commands and output replies."""
        self.log.info("The cmd_loop begins")
        self._writer = writer

        # Just keep waiting for commands to arrive and then just process them and send a reply.
        try:
            while True:
                # First read only one character and see if it is 0x06
                c = (await reader.read(1)).decode()
                self.log.debug("Read char {}".format(c))
                if c is not ":":
                    self.log.info("Received ACK {}".format(c))
                    await self.write("A")
                else:
                    # All the next commands end in a # so we simply read all incoming strings up to # and
                    # parse them.
                    line = await reader.readuntil(HASH)
                    line = line.decode().strip()
                    self.log.info("Read command line: {}".format(line))

                    # Almost all LX200 commands are unique but don't have a fixed length. So we simply loop
                    # over all implemented commands until we find the one that we have received. None of
                    # the implemented commands are non-unique so this is a safe way to do this without
                    # having to write too much boiler plate code.
                    responder = Lx200CommandResponder()
                    cmd = None
                    for key in responder.dispatch_dict.keys():
                        if line.startswith(key):
                            cmd = key

                    # Log a message if the command wasn't found.
                    if cmd not in responder.dispatch_dict:
                        self.log.error("Unknown command {}".format(cmd))

                    # Otherwise process the command.
                    else:
                        (func, has_arg) = responder.dispatch_dict[cmd]
                        kwargs = {}
                        if has_arg:
                            # Read the function argument from the incoming command line and pass it on to
                            # the function.
                            data_start = len(cmd)
                            kwargs["data"] = line[data_start:-1]
                        output = await func(**kwargs)
                        self.log.info("Received output {}".format(output))
                        if output:
                            await self.write(output)
        except ConnectionResetError:
            self.log.info("Ekos disconnected.")


async def main():
    socket_server = SocketServer()
    await socket_server.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
