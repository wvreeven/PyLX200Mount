__all__ = [
    "get_altaz_from_radec",
    "get_radec_from_altaz",
    "get_skycoord_from_altaz",
    "get_skycoord_from_radec",
    "get_skycoord_from_radec_str",
]

import asyncio

from astropy import units as u
from astropy.coordinates import FK5, AltAz, Angle, BaseCoordinateFrame, SkyCoord

from ..alignment import TelescopeAltAzFrame
from ..datetime_util import DatetimeUtil
from ..enums import MILLISECOND
from ..observing_location import get_observing_location

DEFAULT_ATMOSPHERIC_PRESSURE = u.Quantity(101325.0 * u.Pa)
DEFAULT_TEMPERATURE = u.Quantity(-20.0 * u.deg_C)
DEFAULT_RELATIVE_HUMIDITY = 0.01
DEFAULT_WAVELENGTH = u.Quantity(0.550 * u.micron)

_fk5 = FK5(equinox=DatetimeUtil.get_datetime())


async def get_skycoord_from_altaz(
    alt: float, az: float, timestamp: float, frame: BaseCoordinateFrame = AltAz
) -> SkyCoord:
    await asyncio.sleep(MILLISECOND)

    return SkyCoord(
        alt=Angle(alt * u.deg).wrap_at(90.0 * u.deg),
        az=Angle(az * u.deg).wrap_at(360.0 * u.deg),
        frame=frame,
        obstime=DatetimeUtil.get_datetime_at_timestamp(timestamp),
        location=get_observing_location(),
        pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
        temperature=DEFAULT_TEMPERATURE,
        relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
        obswl=DEFAULT_WAVELENGTH,
    )


async def get_altaz_from_radec(
    radec: SkyCoord, timestamp: float, frame: BaseCoordinateFrame = AltAz
) -> SkyCoord:
    await asyncio.sleep(MILLISECOND)

    obstime = DatetimeUtil.get_datetime_at_timestamp(timestamp)
    if frame.name == "altaz":
        new_frame = AltAz(
            obstime=obstime,
            location=get_observing_location(),
            pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
            temperature=DEFAULT_TEMPERATURE,
            relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
            obswl=DEFAULT_WAVELENGTH,
        )
    elif frame.name == "telescopealtazframe":
        new_frame = TelescopeAltAzFrame(
            obstime=obstime,
            location=get_observing_location(),
            pressure=DEFAULT_ATMOSPHERIC_PRESSURE,
            temperature=DEFAULT_TEMPERATURE,
            relative_humidity=DEFAULT_RELATIVE_HUMIDITY,
            obswl=DEFAULT_WAVELENGTH,
        )
    else:
        raise ValueError(f"Unknown frame type: {frame}.")
    return radec.transform_to(new_frame)


async def get_skycoord_from_radec(ra: float, dec: float) -> SkyCoord:
    await asyncio.sleep(MILLISECOND)

    return SkyCoord(ra=Angle(ra * u.deg), dec=Angle(dec * u.deg), frame=_fk5)


async def get_skycoord_from_radec_str(ra_str: str, dec_str: str) -> SkyCoord:
    await asyncio.sleep(MILLISECOND)

    ra = Angle(ra_str + " hours")
    dec = Angle(dec_str.replace("*", ":") + " degrees")

    return await get_skycoord_from_radec(ra.deg, dec.deg)


async def get_radec_from_altaz(altaz: SkyCoord) -> SkyCoord:
    await asyncio.sleep(MILLISECOND)

    radec = altaz.transform_to(_fk5)
    return radec
