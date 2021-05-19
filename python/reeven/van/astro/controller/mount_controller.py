from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.time import Time
from astropy import units as u
import logging

from reeven.van.astro.observing_location import ObservingLocation


class MountController:
    """Control the Mount."""

    def __init__(self):
        self.log = logging.getLogger("MountController")
        self.tracking = False
        self.aligned = False
        self.ra_dec = None
        self.observing_location = ObservingLocation()

    # TODO Add with real implementation as soon as goto and tracking are implemented
    async def get_ra_dec(self):
        """Get the current RA and DEC of the mount.

        Since RA and DEC of the mount are requested in pairs, this method computes both
        the RA and DEC.

        Returns
        -------
        The right ascention and declination.
        """

        time = Time.now()
        altaz = SkyCoord(
            alt=Angle(90 * u.deg),
            az=Angle(0 * u.deg),
            frame="altaz",
            obstime=time,
            location=self.observing_location.location,
        )
        self.ra_dec = altaz.transform_to("icrs")
        return self.ra_dec
