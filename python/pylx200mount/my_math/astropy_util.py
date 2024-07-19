__all__ = [
    "get_altaz_at_different_time",
    "get_altaz_from_radec",
    "get_radec_from_altaz",
    "get_skycoord_from_alt_az",
    "get_skycoord_from_ra_dec",
    "get_skycoord_from_ra_dec_str",
]

from datetime import datetime

from astropy import units as u
from astropy.coordinates import FK5, AltAz, Angle, SkyCoord

from ..observing_location import ObservingLocation

DEFAULT_ATMOSPHERIC_PRESSURE = u.Quantity(101325.0 * u.Pa)
DEFAULT_TEMPERATURE = u.Quantity(-20.0 * u.deg_C)
DEFAULT_RELATIVE_HUMIDITY = 0.01
DEFAULT_WAVELENGTH = u.Quantity(0.550 * u.micron)

_fk5 = FK5(equinox=datetime.now().astimezone())


def get_skycoord_from_alt_az(
    alt: float, az: float, observing_location: ObservingLocation, timestamp: float
) -> SkyCoord:
    return SkyCoord(
        alt=Angle(alt * u.deg),
        az=Angle(az * u.deg),
        frame="altaz",
        obstime=datetime.fromtimestamp(timestamp, observing_location.tz),
        location=observing_location.location,
        pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
        temperature=DEFAULT_TEMPERATURE,
        relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
        obswl=DEFAULT_WAVELENGTH,
    )


def get_altaz_at_different_time(
    alt: float,
    az: float,
    observing_location: ObservingLocation,
    timestamp: float,
    timediff: float,
) -> AltAz:
    alt_az = get_skycoord_from_alt_az(
        alt=alt, az=az, observing_location=observing_location, timestamp=timestamp
    )
    return alt_az.transform_to(
        AltAz(
            obstime=datetime.fromtimestamp(timestamp + timediff, observing_location.tz)
        )
    )


def get_altaz_from_radec(
    ra_dec: SkyCoord, observing_location: ObservingLocation, timestamp: float
) -> SkyCoord:
    return ra_dec.transform_to(
        AltAz(
            obstime=datetime.fromtimestamp(timestamp, observing_location.tz),
            location=observing_location.location,
            pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
            temperature=DEFAULT_TEMPERATURE,
            relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
            obswl=DEFAULT_WAVELENGTH,
        )
    )


def get_skycoord_from_ra_dec(ra: float, dec: float) -> SkyCoord:
    return SkyCoord(
        ra=Angle(ra * u.deg),
        dec=Angle(dec * u.deg),
        frame=_fk5,
    )


def get_skycoord_from_ra_dec_str(ra_str: str, dec_str: str) -> SkyCoord:
    return SkyCoord(
        ra=Angle(ra_str + " hours"),
        dec=Angle(dec_str.replace("*", ":") + " degrees"),
        frame=_fk5,
    )


def get_radec_from_altaz(alt_az: SkyCoord) -> SkyCoord:
    ra_dec = alt_az.transform_to(_fk5)
    return get_skycoord_from_ra_dec(ra_dec.ra.deg, ra_dec.dec.deg)
