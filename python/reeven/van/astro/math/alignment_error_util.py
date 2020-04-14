from astropy import units as u
from astropy.coordinates import SkyCoord, Angle, Latitude
import math


def compute_alignment_error(lat, s1, s2, err_ra, err_de):
    """Compute the alignment error for the given latitdue given the measured sky coordinates and errors in
    right ascentsion and declination.

    Parameters
    ----------
    lat: `Latitude`
        The latitude of the observer.
    s1: `SkyCoord`
        The hour angle and declination of the first alignment star.
    s2: `SkyCoord`
        The hour angle and declination of the second alignment star.
    err_ra: `Angle`
        The error in right ascension as measured for the second star.
    err_de: `Angle`
        The error in declination as measured for the second star.

    Returns
    -------
    The computed alignment errors given in offsets in elevation and azimuth.

    """
    d = (
        math.cos(lat.radian)
        * (math.tan(s1.dec.radian) + math.tan(s2.dec.radian))
        * (1 - math.cos(s1.ra.radian - s2.ra.radian))
    )

    one = math.cos(lat.radian) * (math.sin(s2.ra.radian) - math.sin(s1.ra.radian)) / d
    two = (
        -math.cos(lat.radian)
        * (
            math.tan(s1.dec.radian) * math.cos(s1.ra.radian)
            - math.tan(s2.dec.radian) * math.cos(s2.ra.radian)
        )
        / d
    )
    three = (math.cos(s1.ra.radian) - math.cos(s2.ra.radian)) / d
    four = (
        math.tan(s2.dec.radian) * math.sin(s2.ra.radian)
        - math.tan(s1.dec.radian) * math.sin(s1.ra.radian)
    ) / d
    delta_e = one * err_ra + two * err_de
    delta_a = three * err_ra + four * err_de
    return delta_e, delta_a
