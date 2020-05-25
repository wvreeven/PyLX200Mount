from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.time import Time
from astropy import units as u
import logging

from reeven.van.astro.observing_location import ObservingLocation


class MountController:
    """Control the Mount.
    """

    def __init__(self):
        self.log = logging.getLogger("MountController")
        self.tracking = False
        self.aligned = False
        self.ra_dec = None
        self.observing_location = ObservingLocation()

    # noinspection PyMethodMayBeStatic
    # TODO Add with real implementation as soon as goto and tracking are implemented
    async def get_ra(self):
        """Get the current RA of the mount.

        Since RA and DEC of the mount are requested in pairs, this method computes both the RA and DEC.

        Returns
        -------
        The right ascention.
        """

        time = Time.now()
        zenith = SkyCoord(
            alt=Angle(90 * u.deg),
            az=Angle(0 * u.deg),
            frame="altaz",
            obstime=time,
            location=self.observing_location.location,
        )
        self.ra_dec = zenith.transform_to("icrs")
        return self.ra_dec.ra

    # noinspection PyMethodMayBeStatic
    # TODO Add with real implementation as soon as goto and tracking are implemented
    async def get_dec(self):
        """Get the current DEC of the mount.

        Since RA and DEC of the mount are requested in pairs, the get_ra method computes both the RA and
        DEC and this method simply returns the computed DEC.

        Returns
        -------
        The declination.
        """
        return self.ra_dec.dec
