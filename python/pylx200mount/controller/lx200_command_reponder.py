import logging
from datetime import datetime

from astropy import units as u
from astropy.coordinates import Latitude, Longitude, SkyCoord

from .mount_controller import MountController

_all__ = ["Lx200CommandResponder", "REPLY_SEPARATOR"]

"""Default reply."""
DEFAULT_REPLY = "1"

"""A slew to the target position is possible."""
SLEW_POSSIBLE = "0"

"""Multiple strings which get sent as a reply to the SC command."""
UPDATING_PLANETARY_DATA1 = "Updating Planetary Data       "
UPDATING_PLANETARY_DATA2 = "                              "

"""Separator used for multiple replies."""
REPLY_SEPARATOR = "\n"


class Lx200CommandResponder:
    """Implements the LX200 protocol.

    For more info, see the TelescopeProtocol PDF document in the misc/docs section.
    """

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)

        # Variables holding the status of the mount
        self.autoguide_speed = 0

        # Variables holding the target position
        self.target_ra = "0.0"
        self.target_dec = "0.0"

        self.mount_controller = MountController()

        # The received command. This is kept as a reference for the slews.
        self.cmd: str = ""
        # Dictionary of the functions to execute based on the received command.
        self.dispatch_dict = {
            "CM": (self.sync, False),
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
            "Mn": (self.move_slew_in_direction, False),
            "Me": (self.move_slew_in_direction, False),
            "Ms": (self.move_slew_in_direction, False),
            "Mw": (self.move_slew_in_direction, False),
            "MS": (self.move_slew, False),
            "Qn": (self.stop_slew, False),
            "Qe": (self.stop_slew, False),
            "Qs": (self.stop_slew, False),
            "Qw": (self.stop_slew, False),
            # In general the keys should not contain the trailing '#' but in
            # this case it is necessary to avoid confusion with the other
            # commands starting with 'Q'.
            "Q#": (self.stop_slew, False),
            "RC": (self.set_slew_rate, False),
            "RG": (self.set_slew_rate, False),
            "RM": (self.set_slew_rate, False),
            "RS": (self.set_slew_rate, False),
            "SC": (self.set_local_date, True),
            "Sd": (self.set_dec, True),
            "Sg": (self.set_current_site_longitude, True),
            "SG": (self.set_utc_offset, True),
            "SL": (self.set_local_time, True),
            "Sr": (self.set_ra, True),
            "St": (self.set_current_site_latitude, True),
        }

    async def start(self) -> None:
        """Start the responder."""
        self.log.info("Start called.")
        await self.mount_controller.start()

    async def stop(self) -> None:
        """Stop the responder."""
        self.log.info("Stop called.")
        await self.mount_controller.stop()

    async def get_ra(self) -> str:
        """Get the RA that the mount currently is pointing at."""
        ra_dec: SkyCoord = await self.mount_controller.get_ra_dec()
        ra = ra_dec.ra
        ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
        return ra_str

    async def set_ra(self, data: str) -> str:
        """Set the RA that the mount should slew to.

        Parameters
        ----------
        data: `str`
            A sexagemal representation of the RA, HH:mm:ss

        Returns
        -------
        DEFAULT_REPLY
            The default reply accoring to the LX200 command protocol.
        """
        self.log.debug(f"Setting RA to {data}")
        self.target_ra = data
        return DEFAULT_REPLY

    async def get_dec(self) -> str:
        """Get the DEC that the mount currently is pointing at."""
        ra_dec: SkyCoord = await self.mount_controller.get_ra_dec()
        dec = ra_dec.dec
        # Use signed_dms here because dms will have negative minutes and seconds!!!
        dec_dms = dec.signed_dms
        # LX200 specific format
        dec_str = f"{dec_dms.sign*dec_dms.d:2.0f}*{dec_dms.m:2.0f}'{dec_dms.s:2.2f}"
        return dec_str

    async def set_dec(self, data: str) -> str:
        """Set the DEC that the mount should slew to.

        Parameters
        ----------
        data: `str`
            A sexagemal representation of the DEC, dd*mm:ss

        Returns
        -------
        DEFAULT_REPLY
            The default reply accoring to the LX200 command protocol.
        """
        self.log.debug(f"Setting DEC to {data}")
        self.target_dec = data
        return DEFAULT_REPLY

    # noinspection PyMethodMayBeStatic
    async def get_clock_format(self) -> str:
        """Get the clock format: 12h or 24h. We will always use 24h."""
        return "(24)"

    # noinspection PyMethodMayBeStatic
    async def get_tracking_rate(self) -> str:
        """Get the tracking rate of the mount."""
        return "60.0"

    # noinspection PyMethodMayBeStatic
    async def get_utc_offset(self) -> str:
        """Get the UTC offset of the obsering site.

        The LX200 counts the number of hours that need to be added to get the UTC instead
        of the number of hours that the local time is ahead or behind of UTC. The
        difference is a minus symbol.
        """
        dt = datetime.now().astimezone()
        tz = self.mount_controller.observing_location.tz.utcoffset(dt=dt)
        utc_offset = tz.total_seconds() / 3600
        self.log.debug(f"UTC Offset = {utc_offset}")
        return f"{-utc_offset:.1f}"

    # noinspection PyMethodMayBeStatic
    async def get_local_time(self) -> str:
        """Get the local time at the observing site."""
        current_dt = datetime.now().astimezone()
        return current_dt.strftime("%H:%M:%S")

    # noinspection PyMethodMayBeStatic
    async def get_current_date(self) -> str:
        """Get the local date at the observing site."""
        current_dt = datetime.now().astimezone()
        return current_dt.strftime("%m/%d/%y")

    # noinspection PyMethodMayBeStatic
    async def get_firmware_date(self) -> str:
        """Get the firmware date which is just a date that I made up."""
        return "Apr 05 2020"

    # noinspection PyMethodMayBeStatic
    async def get_firmware_time(self) -> str:
        """Get the firmware time which is just a time that I made up."""
        return "18:00:00"

    # noinspection PyMethodMayBeStatic
    async def get_firmware_number(self) -> str:
        """Get the firmware number which is just a number that I made up."""
        return "1.0"

    # noinspection PyMethodMayBeStatic
    async def get_firmware_name(self) -> str:
        """Get the firmware name which is just a name that I made up."""
        return "Phidgets|A|43Eg|Apr 05 2020@18:00:00"

    # noinspection PyMethodMayBeStatic
    async def get_telescope_name(self) -> str:
        """Get the mount name which is just a name that I made up."""
        return "Phidgets"

    async def get_current_site_latitude(self) -> str:
        """Get the latitude of the obsering site."""
        return self.mount_controller.observing_location.location.lat.to_string(
            unit=u.degree, sep=":", fields=2
        )

    async def set_current_site_latitude(self, data: str) -> str:
        """Set the latitude of the obsering site."""
        self.log.debug(f"set_current_site_latitude received data {data}")
        if "*" in data:
            # SkySafari sends the latitude in the form "deg*min"
            lat_deg, lat_min = data.split("*")
            self.mount_controller.observing_location.set_latitude(
                Latitude(f"{lat_deg}d{lat_min}m")
            )
        else:
            # Ekos sends the latitude in the form of a decimal value
            self.mount_controller.observing_location.set_latitude(
                Latitude(f"{data} degrees")
            )
        await self.mount_controller.location_updated()
        return DEFAULT_REPLY

    async def get_current_site_longitude(self) -> str:
        """Get the longitude of the obsering site.

        The LX200 protocol puts West longitudes positive while astropy puts East
        longitude positive, so we need to convert from the astropy longitude to the
        LX200 longitude.
        """
        longitude = self.mount_controller.observing_location.location.lon.to_string(
            unit=u.degree, sep=":", fields=2
        )
        if longitude[0] == "-":
            longitude = longitude[1:]
        else:
            longitude = "-" + longitude
        self.log.debug(
            f"Converted internal longitude "
            f"{self.mount_controller.observing_location.location.lon.to_string()} "
            f"to LX200 longitude {longitude}"
        )
        return longitude

    async def set_current_site_longitude(self, data: str) -> str:
        """Set the longitude of the obsering site.

        The LX200 protocol puts West longitudes positive while astropy puts East
        longitude positive, so we need to convert from the LX200 longitude to the
        astropy longitude.
        """
        self.log.debug(f"set_current_site_longitude received data {data}")
        if data[0] == "-":
            longitude = data[1:]
        else:
            longitude = "-" + data

        if "*" in data:
            # SkySafari sends the longitude in the form "deg*min"
            lon_deg, lon_min = longitude.split("*")
            self.mount_controller.observing_location.set_longitude(
                Latitude(f"{lon_deg}d{lon_min}m")
            )
        else:
            # Ekos sends the longitude in the form of a decimal value
            self.mount_controller.observing_location.set_longitude(
                Longitude(f"{longitude} degrees")
            )
        self.log.debug(
            f"Converted LX200 longitude {data} to internal longitude "
            f"{self.mount_controller.observing_location.location.lon.to_string()}"
        )
        await self.mount_controller.location_updated()
        return DEFAULT_REPLY

    async def get_site_1_name(self) -> str:
        """Get the name of the observing site."""
        return self.mount_controller.observing_location.name

    async def set_slew_rate(self) -> None:
        """Set the slew rate at the commanded rate."""
        self.log.debug(f"Setting slew rate to value determined by command {self.cmd}")
        await self.mount_controller.set_slew_rate(cmd=self.cmd)

    async def move_slew(self) -> str:
        """Move the telescope at slew rate to the target position."""
        self.log.debug(f"Slewing to RaDec ({self.target_ra}, {self.target_dec}).")
        slew_possible = await self.mount_controller.slew_to(
            self.target_ra, self.target_dec
        )
        return slew_possible

    async def move_slew_in_direction(self) -> str:
        """Move the telescope at slew rate in the commanded direction."""
        self.log.debug(f"Slewing in direction determined by cmd {self.cmd}")
        await self.mount_controller.slew_in_direction(cmd=self.cmd)
        return SLEW_POSSIBLE

    async def stop_slew(self) -> None:
        """Stop the current slew."""
        self.log.debug("Stopping current slew.")
        await self.mount_controller.stop_slew()

    async def set_utc_offset(self, data: str) -> str:
        """Set the UTC offset."""
        self.log.debug(f"set_utc_offset received data {data}")
        return DEFAULT_REPLY

    async def set_local_time(self, data: str) -> str:
        """Set the local time."""
        self.log.debug(f"set_local_time received data {data}")
        return DEFAULT_REPLY

    async def set_local_date(self, data: str) -> str:
        """Set the local date."""
        self.log.debug(f"set_local_date received data {data}")
        # Two return strings are expected so here we separate them by a new
        # line character and will let the socket server deal with it.
        return (
            DEFAULT_REPLY
            + REPLY_SEPARATOR
            + UPDATING_PLANETARY_DATA1
            + REPLY_SEPARATOR
            + UPDATING_PLANETARY_DATA2
        )

    async def sync(self) -> str:
        self.log.debug("sync received.")
        await self.mount_controller.set_ra_dec(
            ra_str=self.target_ra, dec_str=self.target_dec
        )
        return "RANDOM NAME"
