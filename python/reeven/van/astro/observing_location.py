__all__ = ["ObservingLocation"]

from astropy import units as u  # type: ignore
from astropy.coordinates import EarthLocation, Longitude, Latitude  # type: ignore
from astropy.time import TimezoneInfo  # type: ignore


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
        self.location = EarthLocation.from_geodetic(
            lon=Longitude("00d00m00.0s"),
            lat=Latitude("00d00m00.0s"),
            height=0.0 * u.meter,
        )
        self.name = "La Serena"
        self.tz = TimezoneInfo(utc_offset=-4 * u.hour)

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
        loc = EarthLocation.from_geodetic(
            lon=longitude,
            lat=self.location.lat,
            height=self.location.height,
        )
        self.location = loc

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
        loc = EarthLocation.from_geodetic(
            lon=self.location.lon,
            lat=latitude,
            height=self.location.height,
        )
        self.location = loc

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
        loc = EarthLocation.from_geodetic(
            lon=self.location.lon,
            lat=self.location.lat,
            height=height,
        )
        self.location = loc

    def set_name(self, name: str) -> None:
        """
        Set the name of the ObservingLocation.

        Parameters
        ----------
        name: `str`
            The new name
        """
        self.name = name
