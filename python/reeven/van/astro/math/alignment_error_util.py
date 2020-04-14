from astropy.coordinates import SkyCoord, Angle, Latitude
import math


def compute_alignment_error(lat, s1, s2, err_ra, err_dec):
    """Compute the alignment error for the given latitdue, the given measured sky coordinates and the given
    errors in right ascentsion and declination.

    This computation is based on the Two Star Polar Alignment paper by Ralph Pass in the misc/docs
    directory of the source tree on GitHub.

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
    err_dec: `Angle`
        The error in declination as measured for the second star.

    Returns
    -------
    delta_e, delta_a: `tuple` of `Angle`
        The computed alignment errors given in offsets in elevation and azimuth.

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

    # Compute the errors in elevaqtion and azimuth using the four matrix elements
    delta_e = a11 * err_ra + a12 * err_dec
    delta_a = a21 * err_ra + a22 * err_dec
    return delta_e, delta_a
