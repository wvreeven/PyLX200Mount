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


def compute_alignment_error(
    lat: Latitude, s1: SkyCoord, s2: SkyCoord, err_ra: float, err_dec: float
) -> tuple[float, float]:
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
    err_ra : `float`
        The error in right ascension as measured for the second star [arcmin].
    err_dec : `float`
        The error in declination as measured for the second star [arcmin].

    Returns
    -------
    delta_alt, delta_az: `tuple` of `float`
        The computed alignment errors given in offsets in altitude and azimuth
        [arcmin].

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
    err_ra_angle = Angle(err_ra * u.arcmin)
    err_dec_angle = Angle(err_dec * u.arcmin)
    delta_alt = a11 * err_ra_angle + a12 * err_dec_angle
    delta_az = a21 * err_ra_angle + a22 * err_dec_angle
    return delta_alt.arcmin, delta_az.arcmin


def get_altaz_in_rotated_frame(
    delta_alt: float,
    delta_az: float,
    time: Time,
    location: EarthLocation,
    altaz: SkyCoord,
) -> SkyCoord:
    """Rotates the given coordinates to the frame defined by given the altitude and
    azimuth offsets for the given time and observing_location.

    Parameters
    ----------
    delta_alt : `float`
        The altitude offset [armin].
    delta_az : `float`
        The azimuth offset [arcmin].
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
    delta_alt_angle = Angle(delta_alt * u.arcmin)
    delta_az_angle = Angle(delta_az * u.arcmin)
    telescope_frame = AltAz(
        alt=delta_alt_angle, az=delta_az_angle, obstime=time, location=location
    )
    telescope_altaz = altaz.transform_to(SkyOffsetFrame(origin=telescope_frame))
    return telescope_altaz
