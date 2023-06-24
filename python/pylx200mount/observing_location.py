__all__ = ["ObservingLocation"]

from astropy import units as u
from astropy.coordinates import EarthLocation, Latitude, Longitude
from astropy.time import TimezoneInfo


class ObservingLocation:
    """
    The obsering observing_location. It contains an `astropy.coordinates.EarthLocation`
    instance, a name and a timzone. This class has wrapper functions to set the
    Longitude and Latitude, which are immutable in an
    `astropy.coordinates.EarthLocation` instance.
    """

    def __init__(
        self,
    ) -> None:
        # Variables holding the site information
        self.location: EarthLocation = EarthLocation.from_geodetic(
            lon=Longitude("00d00m00.0s"),
            lat=Latitude("00d00m00.0s"),
            height=0.0 * u.meter,
        )
        self.name: str = "La Serena"
        self.tz: TimezoneInfo = TimezoneInfo(tzname="America/Santiago")

    def set_longitude(self, longitude: Longitude) -> None:
        """
        Set the longitude of the ObservingLocation. It will create a new
        `astropy.coordinates.EarthLocation` instance with the new value of longitude
        while copying the other values.

        Parameters
        ----------
        longitude: `Longitude`
            The new longitude
        """
        self.location = EarthLocation.from_geodetic(
            lon=longitude,
            lat=self.location.lat,
            height=self.location.height,
        )

    def set_latitude(self, latitude: Latitude) -> None:
        """
        Set the latitude of the ObservingLocation. It will create a new
        `astropy.coordinates.EarthLocation` instance with the new value of latitude
        while copying the other values.

        Parameters
        ----------
        latitude: `Latitude`
            The new latitude
        """
        self.location = EarthLocation.from_geodetic(
            lon=self.location.lon,
            lat=latitude,
            height=self.location.height,
        )

    def set_height(self, height: float) -> None:
        """
        Set the height of the ObservingLocation. It will create a new
        `astropy.coordinates.EarthLocation` instance with the new value of latitude
        while copying the other values.

        Parameters
        ----------
        height: `float`
            The new height in `u.meter`
        """
        self.location = EarthLocation.from_geodetic(
            lon=self.location.lon,
            lat=self.location.lat,
            height=height,
        )

    def set_name(self, name: str) -> None:
        """
        Set the name of the ObservingLocation.

        Parameters
        ----------
        name: `str`
            The new name
        """
        self.name = name
