from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.time import Time
from astropy import units as u
import logging

from reeven.van.astro.observing_location import ObservingLocation


class MountController:
    """Control the Mount."""

    def __init__(self):
        self.log = logging.getLogger("MountController")
        self.altitude = 90.0
        self.azimuth = 0.0
        self.tracking = False
        self.aligned = False
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
        alt_az = SkyCoord(
            alt=Angle(self.altitude * u.deg),
            az=Angle(self.azimuth * u.deg),
            frame="altaz",
            obstime=time,
            location=self.observing_location.location,
        )
        ra_dec = alt_az.transform_to("icrs")
        return ra_dec

    async def set_ra_dec(self, ra, dec):
        """Set the current RA and DEC of the mount.

        Parameters
        ----------
        ra: `str`
            The Right Ascension of the mount in degrees. The format is
            "HH:mm:ss".
        dec: `str`
            The Declination of the mount in degrees. The format is "+dd*mm:ss".
        """
        self.log.info(f"Setting (ra, dec) to ({ra}, {dec})")
        time = Time.now()
        ra_angle = Angle(ra + " hours")
        dec_angle = Angle(dec.replace("*", ":") + " degrees")
        ra_dec = SkyCoord(ra=ra_angle, dec=dec_angle, frame="icrs")
        alt_az = ra_dec.transform_to(
            AltAz(obstime=time, location=self.observing_location.location)
        )
        self.altitude = alt_az.alt.value
        self.azimuth = alt_az.az.value
