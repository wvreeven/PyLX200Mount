from astropy.coordinates import (
    AltAz,
    Angle,
    EarthLocation,
    Latitude,
    SkyCoord,
    SkyOffsetFrame,
)
from astropy.time import Time
import astropy.units as u
import math

__all__ = ["compute_alignment_error", "get_altaz_in_rotated_frame"]


def compute_alignment_error(
    lat: Latitude, s1: SkyCoord, s2: SkyCoord, err_ra: Angle, err_dec: Angle
) -> tuple[Angle, Angle]:
    """Compute the alignment error for the given latitdue, the given measured sky
    coordinates and the given errors in right ascentsion and declination.

    This computation is based on the Two Star Polar Alignment paper by Ralph Pass in the
    misc/docs directory of the source tree on GitHub.

    Parameters
    ----------
    lat : `Latitude`
        The latitude of the observer.
    s1 : `SkyCoord`
        The right ascension and declination of the first alignment star.
    s2 : `SkyCoord`
        The right ascension and declination of the second alignment star.
    err_ra : `Angle`
        The error in right ascension as measured for the second star.
    err_dec : `Angle`
        The error in declination as measured for the second star.

    Returns
    -------
    delta_alt, delta_az: `tuple` of `Angle`
        The computed alignment errors given in offsets in altitude and azimuth.

    """
    # Compute the determinant
    d = (
        math.cos(lat.radian)
        * (math.tan(s1.dec.radian) + math.tan(s2.dec.radian))
        * (1 - math.cos(s1.ra.radian - s2.ra.radian))
    )

    # Compute the four matrix elements using the determinant
    a11 = math.cos(lat.radian) * (math.sin(s2.ra.radian) - math.sin(s1.ra.radian)) / d
    a12 = (
        -math.cos(lat.radian)
        * (
            math.tan(s1.dec.radian) * math.cos(s1.ra.radian)
            - math.tan(s2.dec.radian) * math.cos(s2.ra.radian)
        )
        / d
    )
    a21 = (math.cos(s1.ra.radian) - math.cos(s2.ra.radian)) / d
    a22 = (
        math.tan(s2.dec.radian) * math.sin(s2.ra.radian)
        - math.tan(s1.dec.radian) * math.sin(s1.ra.radian)
    ) / d

    # Compute the errors in altitude and azimuth using the four matrix elements
    delta_alt = a11 * err_ra + a12 * err_dec
    delta_az = a21 * err_ra + a22 * err_dec
    return delta_alt, delta_az


def get_altaz_in_rotated_frame(
    delta_alt: Angle,
    delta_az: Angle,
    time: Time,
    location: EarthLocation,
    altaz: SkyCoord,
) -> SkyCoord:
    """Rotates the given coordinates to the frame defined by given the altitude and
    azimuth offsets for the given time and observing_location.

    Parameters
    ----------
    delta_alt : `Angle`
        The altitude offset.
    delta_az : `Angle`
        The azimuth offset.
    time : `Time`
        The Time for which the AltAz coordinates are valid
    location : `EarthLocation`
        The observing_location for which the AltAz coordinates are valid
    altaz : `SkyCoord`
        The altitude and azimuth to rotate.

    Returns
    -------
    telescope_altaz: `SkyCoord`
        The altitude and azimuth rotated to the new frame.
    """
    telescope_altaz = AltAz(alt=delta_alt, az=delta_az, obstime=time, location=location)
    telescope_frame = altaz.transform_to(SkyOffsetFrame(origin=telescope_altaz))
    return SkyCoord(
        alt=Angle(telescope_frame.lon.deg * u.deg),
        az=Angle(telescope_frame.lat.deg * u.deg),
        frame="altaz",
        obstime=time,
        location=location,
    )
