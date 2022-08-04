from unittest import TestCase

from astropy import units as u
from astropy.coordinates import (
    AltAz,
    Angle,
    EarthLocation,
    Latitude,
    Longitude,
    SkyCoord,
)
from astropy.time import Time
from reeven.van.astro import pmc


class Test(TestCase):
    def test_compute_alignment_error(self) -> None:
        lat = Angle((42 + (40 / 60)) * u.deg)
        s1 = SkyCoord(ra=3 * u.hourangle, dec=48 * u.degree)
        s2 = SkyCoord(ra=23 * u.hourangle, dec=45 * u.degree)
        err_ra = Angle(-12.0 * u.arcmin)
        err_dec = Angle(-21.0 * u.arcmin)

        aeu = pmc.math.AlignmentErrorUtil()
        aeu.compute_alignment_error(lat, s1, s2, err_ra, err_dec)
        self.assertAlmostEqual(aeu.delta_alt.arcmin, 7.3897, 4)
        self.assertAlmostEqual(aeu.delta_az.arcmin, 32.2597, 4)

    def test_compute_zero_alignment_error(self) -> None:
        lat = Angle((42 + (40 / 60)) * u.deg)
        s1 = SkyCoord(ra=3 * u.hourangle, dec=48 * u.degree)
        s2 = SkyCoord(ra=23 * u.hourangle, dec=45 * u.degree)
        err_ra = Angle(0.0 * u.arcmin)
        err_dec = Angle(0.0 * u.arcmin)

        aeu = pmc.math.AlignmentErrorUtil()
        aeu.compute_alignment_error(lat, s1, s2, err_ra, err_dec)
        self.assertAlmostEqual(aeu.delta_alt.arcmin, 0.0)
        self.assertAlmostEqual(aeu.delta_az.arcmin, 0.0)

    def test_get_altaz_in_rotated_frame(self) -> None:
        location = EarthLocation.from_geodetic(
            lon=Longitude("-71d14m12.5s"),
            lat=Latitude("-29d56m29.7s"),
            height=110.0 * u.meter,
        )
        sirius = SkyCoord.from_name("Sirius")
        time = Time("2020-04-15 20:49:48.560642")
        sirius_altaz = sirius.transform_to(AltAz(obstime=time, location=location))

        aeu = pmc.math.AlignmentErrorUtil()
        aeu.delta_alt = Angle(7.3897 * u.arcmin)
        aeu.delta_az = Angle(32.2597 * u.arcmin)
        sirius_tel = aeu.get_altaz_in_rotated_frame(
            time=time,
            location=location,
            altaz=sirius_altaz,
        )
        self.assertAlmostEqual(sirius_tel.alt.deg, 50.36605878470352)
        self.assertAlmostEqual(sirius_tel.az.deg, 70.33162741801904)
