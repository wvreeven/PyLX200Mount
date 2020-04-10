import asyncio
import datetime
import logging
from astropy.coordinates import Longitude, Latitude
from astropy import units as u

logging.basicConfig(level=logging.INFO)

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

        # Variables holding the status of the mount
        self.azimuth = 0.0
        self.altitude = 45.0
        self.autoguide_speed = 0

        # Variables holding the site information
        self.longitude = Longitude("-071:14:12.5 degrees")
        self.latitude = Latitude("-29:56:29.7 degrees")
        self.height = 110.0 * u.meter
        self.observing_location_name = "La_Serena"

        # Dictionary of the functions to execute based on the commando received.
        self.dispatch_dict = {
            "Gc": (self.get_clock_format, False),
            "GC": (self.get_current_date, False),
            "GD": (self.get_dec, False),
            "Gg": (self.get_current_site_longitude, False),
            "GG": (self.get_utc_offset, False),
            "GL": (self.get_local_time, False),
            "GM": (self.get_site_1_name, False),
            "GR": (self.get_ra, False),
            "Gt": (self.get_current_site_latitude, False),
            "GT": (self.get_tracking_rate, False),
            "GVD": (self.get_firmware_date, False),
            "GVF": (self.get_firmware_name, False),
            "GVN": (self.get_firmware_number, False),
            "GVP": (self.get_telescope_name, False),
            "GVT": (self.get_firmware_time, False),
            "RM": (self.set_slew_rate, False),
            "Sg": (self.set_current_site_longitude, True),
            "St": (self.set_current_site_latitude, True),
        }
        self.add_hash = False

    async def start(self):
        """Start the TCP/IP server."""
        self.log.info("Start called")
        self._server = await asyncio.start_server(self.cmd_loop, port=self.port)
        await self._server.serve_forever()

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
        if self.add_hash:
            reply = reply + HASH
        self.log.info(f"Writing reply {reply!r}")
        self._writer.write(reply)
        await self._writer.drain()

    async def cmd_loop(self, reader, writer):
        """Execute commands and output replies."""
        self.log.info("The cmd_loop begins")
        self._writer = writer

        # Just keep waiting for commands to arrive and then just process them and send a reply.
        try:
            while True:
                self.add_hash = True
                # First read only one character and see if it is 0x06
                c = (await reader.read(1)).decode()
                self.log.debug(f"Read char {c}")
                if c is not ":":
                    self.log.info(f"Received ACK {c}")
                    self.add_hash = False
                    await self.write("A")
                else:
                    # All the next commands end in a # so we simply read all incoming strings up to # and parse them.
                    line = await reader.readuntil(HASH)
                    line = line.decode().strip()
                    self.log.info(f"Read command line: {line!r}")

                    # Almost all LX200 commands are unique but don't have a fixed length. So we simply loop over all
                    # implemented commands until we find the one that we have received. None of the implemented
                    # commands are non-unique so this is a safe way to do this without having to write too much
                    # boiler plate code.
                    cmd = None
                    for key in self.dispatch_dict.keys():
                        if line.startswith(key):
                            cmd = key

                    # Log a message if the command wasn't found.
                    if cmd not in self.dispatch_dict:
                        self.log.error(f"Unknown command {cmd!r}")

                    # Otherwise process the command.
                    else:
                        (func, has_arg) = self.dispatch_dict[cmd]
                        kwargs = {}
                        if has_arg:
                            # Read the function argument from the incoming command line and pass it on to the function.
                            data_start = len(cmd)
                            kwargs["data"] = line[data_start:-1]
                        output = await func(**kwargs)
                        self.log.info(f"Received output {output}")
                        if output:
                            await self.write(output)
        except ConnectionResetError:
            self.log.info("Ekos disconnected.")

    # noinspection PyMethodMayBeStatic
    async def get_ra(self):
        """"Get the RA that the mount currently is pointing at."""
        return "00:00:00"

    # noinspection PyMethodMayBeStatic
    async def get_dec(self):
        """"Get the DE that the mount currently is pointing at."""
        return "-90:00:00"

    # noinspection PyMethodMayBeStatic
    async def get_clock_format(self):
        """"Get the clock format: 12h or 24h. We will always use 24h."""
        return "24"

    # noinspection PyMethodMayBeStatic
    async def get_tracking_rate(self):
        """Get the tracking rate of the mount."""
        return "60.0"

    # noinspection PyMethodMayBeStatic
    async def get_utc_offset(self):
        """Get the UTC offset of the obsering site. The LX200 counts the number of hours that need to be added to get
        the UTC instead of the number of hours that the local time is ahead or behind of UTC. The difference is a
        minus symbol."""
        return "4"

    # noinspection PyMethodMayBeStatic
    async def get_local_time(self):
        """Get the local time at the observing site."""
        current_dt = datetime.datetime.now()
        return current_dt.strftime("%H:%M:%S")

    # noinspection PyMethodMayBeStatic
    async def get_current_date(self):
        """Get the local date at the observing site."""
        current_dt = datetime.datetime.now()
        return current_dt.strftime("%m/%d/%y")

    # noinspection PyMethodMayBeStatic
    async def get_firmware_date(self):
        """Get the firmware date which is just a date that I made up."""
        return "Apr 05 2019"

    # noinspection PyMethodMayBeStatic
    async def get_firmware_time(self):
        """Get the firmware time which is just a time that I made up."""
        return "18:00:00"

    # noinspection PyMethodMayBeStatic
    async def get_firmware_number(self):
        """Get the firmware number which is just a number that I made up."""
        return "1.0"

    # noinspection PyMethodMayBeStatic
    async def get_firmware_name(self):
        """Get the firmware name which is just a name that I made up."""
        return "Phidgets|A|43Eg|Apr 05 2019@18:00:00"

    # noinspection PyMethodMayBeStatic
    async def get_telescope_name(self):
        """Get the mount name which is just a name that I made up."""
        return "Phidgets"

    # noinspection PyMethodMayBeStatic
    async def get_current_site_latitude(self):
        """Get the latitude of the obsering site."""
        return self.latitude.to_string(unit=u.degree, sep=":", fields=2)

    async def set_current_site_latitude(self, data):
        """Set the latitude of the obsering site as received from Ekos."""
        self.log.info(f"set_current_site_latitude received data {data!r}")
        self.latitude = Latitude(f"{data} degrees")
        self.add_hash = False
        return "1"

    # noinspection PyMethodMayBeStatic
    async def get_current_site_longitude(self):
        """Get the longitude of the obsering site. The LX200 protocol puts West longitudes positive while astropy puts
        East longitude positive so we need to convert from the astropy longitude to the LX200 longitude."""
        longitude = self.longitude.to_string(unit=u.degree, sep=":", fields=2)
        if longitude[0] is "-":
            longitude = longitude[1:]
        else:
            longitude = "-" + longitude
        self.log.info(
            f"Converted internal longitude {self.longitude.to_string()} to LX200 longitude {longitude}"
        )
        return longitude

    async def set_current_site_longitude(self, data):
        """Set the longitude of the obsering site. The LX200 protocol puts West longitudes positive while astropy puts
        East longitude positive so we need to convert from the LX200 longitude to the astropy longitude."""
        self.log.info(f"set_current_site_longitude received data {data!r}")
        if data[0] is "-":
            longitude = data[1:]
        else:
            longitude = "-" + data
        self.longitude = Longitude(f"{longitude} degrees")
        self.log.info(
            f"Converted LX200 longitude {data} to internal longitude {self.longitude.to_string()}"
        )
        self.add_hash = False
        return "1"

    # noinspection PyMethodMayBeStatic
    async def get_site_1_name(self):
        """Get the name of the observing site."""
        return self.observing_location_name

    # noinspection PyMethodMayBeStatic
    async def set_slew_rate(self):
        """Set the slew rate. This can be ignored since we determine the slew rate ourself."""
        # self.add_hash = False
        # return "1"
        pass


async def main():
    socket_server = SocketServer()
    await socket_server.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
