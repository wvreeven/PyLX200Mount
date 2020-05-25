from datetime import datetime
import logging
from astropy.coordinates import Longitude, Latitude
from astropy.time import Time
from astropy import units as u

from reeven.van.astro.controller.mount_controller import MountController
from reeven.van.astro.observing_location import ObservingLocation

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s", level=logging.INFO,
)

# Commands and replies are terminated by the hash symbol
HASH = "#"

# The number of seconds in an hour
NUM_SEC_PER_HOUR = 3600


class Lx200CommandResponder:
    """Implements the LX200 protocol.

    For more info, see the TelescopeProtocol PDF document in the misc/docs section.
    """

    def __init__(self,):

        self.log = logging.getLogger("Lx200CommandResponder")

        # Variables holding the status of the mount
        self.azimuth = 0.0
        self.altitude = 45.0
        self.autoguide_speed = 0

        self.observing_location = ObservingLocation()
        self.mount_controller = MountController()

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
            "RS": (self.set_slew_rate, False),
            "Sg": (self.set_current_site_longitude, True),
            "St": (self.set_current_site_latitude, True),
        }

    async def get_ra(self):
        """"Get the RA that the mount currently is pointing at."""
        time = Time.now()
        ra = await self.mount_controller.get_ra(time, self.observing_location.location)
        ra_str = ra.to_string(unit=u.hour, sep=":", precision=2, pad=True)
        return ra_str + HASH

    async def get_dec(self):
        """"Get the DEC that the mount currently is pointing at."""
        dec = await self.mount_controller.get_dec()
        # Use signed_dms here because dms will have negative minutes and seconds!!!
        dec_dms = dec.signed_dms
        # LX200 specific format
        dec_str = f"{dec_dms.sign*dec_dms.d:2.0f}*{dec_dms.m:2.0f}'{dec_dms.s:2.2f}"
        # dec_str = dec.to_string(unit=u.deg, sep=":", precision=0, pad=True)
        return dec_str + HASH

    # noinspection PyMethodMayBeStatic
    async def get_clock_format(self):
        """"Get the clock format: 12h or 24h. We will always use 24h."""
        return "(24)" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_tracking_rate(self):
        """Get the tracking rate of the mount."""
        # TODO Replace with real implementation
        return "60.0" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_utc_offset(self):
        """Get the UTC offset of the obsering site.

        The LX200 counts the number of hours that need to be added to get the UTC instead of the number of
        hours that the local time is ahead or behind of UTC. The difference is a minus symbol.
        """
        dt = datetime.now()
        tz = self.observing_location.tz.utcoffset(dt=dt)
        utc_offset = tz.total_seconds() / 3600
        self.log.info(f"UTC Offset = {utc_offset}")
        return f"{-utc_offset:.1f}" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_local_time(self):
        """Get the local time at the observing site."""
        current_dt = datetime.now()
        return current_dt.strftime("%H:%M:%S") + HASH

    # noinspection PyMethodMayBeStatic
    async def get_current_date(self):
        """Get the local date at the observing site."""
        current_dt = datetime.now()
        return current_dt.strftime("%m/%d/%y") + HASH

    # noinspection PyMethodMayBeStatic
    async def get_firmware_date(self):
        """Get the firmware date which is just a date that I made up."""
        return "Apr 05 2020" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_firmware_time(self):
        """Get the firmware time which is just a time that I made up."""
        return "18:00:00" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_firmware_number(self):
        """Get the firmware number which is just a number that I made up."""
        return "1.0" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_firmware_name(self):
        """Get the firmware name which is just a name that I made up."""
        return "Phidgets|A|43Eg|Apr 05 2020@18:00:00" + HASH

    # noinspection PyMethodMayBeStatic
    async def get_telescope_name(self):
        """Get the mount name which is just a name that I made up."""
        return "Phidgets" + HASH

    async def get_current_site_latitude(self):
        """Get the latitude of the obsering site."""
        return (
            self.observing_location.location.lat.to_string(
                unit=u.degree, sep=":", fields=2
            )
            + HASH
        )

    async def set_current_site_latitude(self, data):
        """Set the latitude of the obsering site as received from Ekos."""
        self.log.info(f"set_current_site_latitude received data {data}")
        if "*" in data:
            # SkySafari sends the latitude in the form "deg*min"
            lat_deg, lat_min = data.split("*")
            self.observing_location.set_latitude(Latitude(f"{lat_deg}d{lat_min}m"))
        else:
            # Ekos sends the latitude in the form of a decimal value
            self.observing_location.set_latitude(Latitude(f"{data} degrees"))
        return "1"

    async def get_current_site_longitude(self):
        """Get the longitude of the obsering site.

        The LX200 protocol puts West longitudes positive while astropy puts East longitude positive so we
        need to convert from the astropy longitude to the LX200 longitude.
        """
        longitude = self.observing_location.location.lon.to_string(
            unit=u.degree, sep=":", fields=2
        )
        if longitude[0] == "-":
            longitude = longitude[1:]
        else:
            longitude = "-" + longitude
        self.log.info(
            f"Converted internal longitude {self.observing_location.location.lon.to_string()} "
            f"to LX200 longitude {longitude}"
        )
        return longitude + HASH

    async def set_current_site_longitude(self, data):
        """Set the longitude of the obsering site.

        The LX200 protocol puts West longitudes positive while astropy puts East longitude positive so we
        need to convert from the LX200 longitude to the astropy longitude.
        """
        self.log.info(f"set_current_site_longitude received data {data}")
        if data[0] == "-":
            longitude = data[1:]
        else:
            longitude = "-" + data

        if "*" in data:
            # SkySafari sends the longitude in the form "deg*min"
            lon_deg, lon_min = longitude.split("*")
            self.observing_location.set_longitude(Latitude(f"{lon_deg}d{lon_min}m"))
        else:
            # Ekos sends the longitude in the form of a decimal value
            self.observing_location.set_longitude(Longitude(f"{longitude} degrees"))
        self.log.info(
            f"Converted LX200 longitude {data} to internal "
            f"longitude {self.observing_location.location.lon.to_string()}"
        )
        return "1"

    async def get_site_1_name(self):
        """Get the name of the observing site."""
        return self.observing_location.name + HASH

    # noinspection PyMethodMayBeStatic
    async def set_slew_rate(self):
        """Set the slew rate.

        This can be ignored since we determine the slew rate ourself.
        """
        pass
