__all__ = ["LX200Mount", "run_lx200_mount"]

import asyncio
import logging
import socket

from pylx200mount.controller import REPLY_SEPARATOR, Lx200CommandResponder

# ACK symbol sent by Ekos
ACK: bytes = b"\x06"

# Command start with a colon symbol
COLON: str = ":"

# Commands and replies are terminated by the hash symbol
HASH: bytes = b"#"

# Sleep time between sending replies that contain a newline character.
SEND_COMMAND_SLEEP = 0.01

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.DEBUG,
)


class LX200Mount:
    def __init__(self) -> None:
        self.port: int = 11880
        self._server: asyncio.AbstractServer | None = None
        self._writer: asyncio.StreamWriter | None = None
        # TODO Add configuration to select simulation mode and other settings.
        self.responder = Lx200CommandResponder()

        self.log: logging.Logger = logging.getLogger(type(self).__name__)

    async def start(self) -> None:
        """Start the TCP/IP server."""
        self.log.info("Start called.")
        await self.responder.start()
        self._server = await asyncio.start_server(
            self.cmd_loop, port=self.port, family=socket.AF_INET
        )
        self.log.info(
            f"Server started on host "
            f"{self._server.sockets[0].getsockname()[0]}"
            f":{self._server.sockets[0].getsockname()[1]}"
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

    async def write(self, st: str, append_hash: bool = True) -> None:
        """Write the string st appended with a HASH character.

        Parameters
        ----------
        st: `str`
            The string to append a HASH character to and then write.
        append_hash: `bool`
            Append a HASH to the reply or not? Defaults to True.
        """
        reply = st.encode()
        if append_hash:
            reply = reply + HASH
        # self.log.debug(f"Writing reply {st}")
        if self._writer is not None:
            # After a :SC command, multiple replies need to be send which may
            # lead to a broken pipe error because of the way SkySafari connects
            # and disconnects from the SocketServer all the time. We will just
            # simply ignore that here. It usually only happens once or twice
            # when SkySafari connects, and then it doesn't happen anymore.
            self._writer.write(reply)
            await self._writer.drain()

    async def cmd_loop(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Execute commands and output replies."""
        self._writer = writer

        # Just keep waiting for commands to arrive and then just process them and send a
        # reply.
        try:
            while True:
                # First read only one character.
                c = (await reader.read(1)).decode()
                # SkySafari connects and disconnects all the time and expects a reply when it does.
                if c == "":
                    await self.write("A")
                # AstroPlanner appends all commands with a HASH that can safely be ignored.
                elif c == "#":
                    pass
                # A colon indicates a command so process that.
                elif c == ":":
                    await self._read_and_process_line(reader)
                # Not sure what to do in this case, so long the character and do nothing else.
                else:
                    self.log.debug(f"{c=}")

        except (ConnectionResetError, BrokenPipeError):
            pass

    async def _read_and_process_line(self, reader: asyncio.StreamReader) -> None:
        # All the next commands end in a # so we simply read all incoming
        # strings up to # and parse them.
        line_b = await reader.readuntil(HASH)
        line = line_b.decode().strip()
        self.log.debug(f"Read command line: {line!r}")

        # Almost all LX200 commands are unique but don't have a fixed length.
        # So we simply loop over all implemented commands until we find
        # the one that we have received. All the implemented commands are
        # unique so this is a safe way to find the command without having to
        # write too much boilerplate code.
        cmd = ""
        for key in self.responder.dispatch_dict.keys():
            if line.startswith(key):
                cmd = key
                break

        # Log a message if the command wasn't found.
        if cmd not in self.responder.dispatch_dict:
            self.log.error(f"Unknown command {cmd!r}.")

        # Otherwise, process the command.
        else:
            await self._process_command(cmd, line)

    async def _process_command(self, cmd: str, line: str) -> None:
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
                for i in range(len(outputs)):
                    await self.write(outputs[i])
                    self.log.debug(f"Sleeping for {SEND_COMMAND_SLEEP} sec.")
                    await asyncio.sleep(SEND_COMMAND_SLEEP)
            else:
                append_hash = cmd not in ["MS"]
                await self.write(output, append_hash)


async def run_lx200_mount() -> None:
    lx200_mount = LX200Mount()
    try:
        await lx200_mount.start()
    except (asyncio.CancelledError, KeyboardInterrupt):
        await lx200_mount.stop()


if __name__ == "__main__":
    asyncio.run(run_lx200_mount())
