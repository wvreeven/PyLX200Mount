from astroplan import Observer
from astropy import units as u


class Location:
    """
    Placeholder for an astroplan.Observer instance. This class has wrapper functions to set the Longitude
    and Latitude, which are immutable in an astroplan.Observer instance.
    """

    def __init__(self,):
        # Variables holding the site information
        self.loc = Observer(
            longitude="-071:14:12.5 degrees",
            latitude="-29:56:29.7 degrees",
            elevation=110.0 * u.meter,
            name="La Serena",
            timezone="America/Santiago",
        )

    def set_longitude(self, lon):
        """
        Set the longitude of the Observer. It will create a new astroplan.Observer instance with the new
        value of lan while copying the other values.

        Parameters
        ----------
        lon: `astropy.coordinates.Longitude`
            The new longitude
        """
        loc = Observer(
            longitude=lon,
            latitude=self.loc.location.lat,
            elevation=self.loc.location.height,
            name=self.loc.name,
            timezone=self.loc.timezone,
        )
        self.loc = loc

    def set_latitude(self, lat):
        """
        Set the longitude of the Observer. It will create a new astroplan.Observer instance with the new
        value of lan while copying the other values.

        Parameters
        ----------
        lat: `astropy.coordinates.Latitude`
            The new latitude
        """
        loc = Observer(
            longitude=self.loc.location.lon,
            latitude=lat,
            elevation=self.loc.location.height,
            name=self.loc.name,
            timezone=self.loc.timezone,
        )
        self.loc = loc
