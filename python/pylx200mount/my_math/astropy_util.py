__all__ = [
    "get_altaz_at_different_time",
    "get_altaz_from_radec",
    "get_radec_from_altaz",
    "get_skycoord_from_alt_az",
    "get_skycoord_from_ra_dec",
    "get_skycoord_from_ra_dec_str",
]

from astropy import units as u
from astropy.coordinates import FK5, AltAz, Angle, BaseCoordinateFrame, SkyCoord

from ..datetime_util import DatetimeUtil
from ..observing_location import observing_location

DEFAULT_ATMOSPHERIC_PRESSURE = u.Quantity(101325.0 * u.Pa)
DEFAULT_TEMPERATURE = u.Quantity(-20.0 * u.deg_C)
DEFAULT_RELATIVE_HUMIDITY = 0.01
DEFAULT_WAVELENGTH = u.Quantity(0.550 * u.micron)

_fk5 = FK5(equinox=DatetimeUtil.get_datetime())


def get_skycoord_from_alt_az(
    alt: float,
    az: float,
    timestamp: float,
    frame: BaseCoordinateFrame = AltAz,
) -> SkyCoord:
    return SkyCoord(
        alt=Angle(alt * u.deg),
        az=Angle(az * u.deg),
        frame=frame,
        obstime=DatetimeUtil.get_datetime_at_timestamp(timestamp),
        location=observing_location,
        pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
        temperature=DEFAULT_TEMPERATURE,
        relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
        obswl=DEFAULT_WAVELENGTH,
    )


def get_altaz_at_different_time(
    alt: float,
    az: float,
    timestamp: float,
    timediff: float,
    frame: BaseCoordinateFrame = AltAz,
) -> AltAz:
    alt_az = get_skycoord_from_alt_az(
        alt=alt,
        az=az,
        timestamp=timestamp,
        frame=frame,
    )
    return alt_az.transform_to(
        AltAz(obstime=DatetimeUtil.get_datetime_at_timestamp(timestamp + timediff)),
    )


def get_altaz_from_radec(
    ra_dec: SkyCoord,
    timestamp: float,
    frame: BaseCoordinateFrame = AltAz,
) -> SkyCoord:
    alt_az = ra_dec.transform_to(
        AltAz(
            obstime=DatetimeUtil.get_datetime_at_timestamp(timestamp),
            location=observing_location,
            pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
            temperature=DEFAULT_TEMPERATURE,
            relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
            obswl=DEFAULT_WAVELENGTH,
        )
    )
    return get_skycoord_from_alt_az(alt_az.alt.deg, alt_az.az.deg, timestamp, frame)


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
