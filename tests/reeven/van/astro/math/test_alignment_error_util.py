from reeven.van.astro.math import alignment_error_util
from astropy import units as u
from astropy.coordinates import SkyCoord, Angle
from unittest import TestCase


class Test(TestCase):
    def test_compute_alignment_error(self):
        lat = Angle((42 + (40 / 60)) * u.deg)
        s1 = SkyCoord(ra=3 * u.hourangle, dec=48 * u.degree)
        s2 = SkyCoord(ra=23 * u.hourangle, dec=45 * u.degree)
        err_ra = Angle(-12 * u.arcmin)
        err_de = Angle(-21 * u.arcmin)
        delta_e, delta_a = alignment_error_util.compute_alignment_error(
            lat, s1, s2, err_ra, err_de
        )
        self.assertAlmostEqual(delta_e.radian, Angle(7.3897 * u.arcmin).radian)
        self.assertAlmostEqual(delta_a.radian, Angle(32.2597 * u.arcmin).radian)
