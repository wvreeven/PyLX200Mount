from astropy.coordinates import AltAz, Angle, SkyCoord
from astropy.time import Time
from astropy import units as u

from ..observing_location import ObservingLocation

__all__ = [
    "get_skycoord_from_alt_az",
    "get_altaz_from_radec",
    "get_skycoord_from_ra_dec",
    "get_skycoord_from_ra_dec_str",
    "get_radec_from_altaz",
]


def get_skycoord_from_alt_az(
    alt: float, az: float, observing_location: ObservingLocation
) -> SkyCoord:
    time = Time.now()
    return SkyCoord(
        alt=Angle(alt * u.deg),
        az=Angle(az * u.deg),
        frame="altaz",
        obstime=time,
        location=observing_location.location,
    )


def get_altaz_from_radec(
    ra_dec: SkyCoord, observing_location: ObservingLocation
) -> SkyCoord:
    time = Time.now()
    return ra_dec.transform_to(
        AltAz(obstime=time, location=observing_location.location)
    )


def get_skycoord_from_ra_dec(ra: float, dec: float) -> SkyCoord:
    return SkyCoord(
        ra=Angle(ra * u.deg),
        dec=Angle(dec * u.deg),
        frame="icrs",
    )


def get_skycoord_from_ra_dec_str(ra_str: str, dec_str: str) -> SkyCoord:
    return SkyCoord(
        ra=Angle(ra_str + " hours"),
        dec=Angle(dec_str.replace("*", ":") + " degrees"),
        frame="icrs",
    )


def get_radec_from_altaz(alt_az: SkyCoord) -> SkyCoord:
    return alt_az.transform_to("icrs")
