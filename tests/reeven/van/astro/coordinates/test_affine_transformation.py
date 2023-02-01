import unittest

import astropy.units as u
import pytest
from astropy.coordinates import AltAz
from reeven.van.astro.pmc.coordinates import AffineTransformation


class TestAffineTransformation(unittest.IsolatedAsyncioTestCase):
    async def test_skimage_transform(self) -> None:
        altaz_coord1 = AltAz(az=1.0 * u.deg, alt=1.0 * u.deg)
        altaz_coord2 = AltAz(az=1.0 * u.deg, alt=2.0 * u.deg)
        altaz_coord3 = AltAz(az=2.0 * u.deg, alt=1.0 * u.deg)
        telescope_coord1 = AltAz(az=2.4142135623 * u.deg, alt=5.732050807 * u.deg)
        telescope_coord2 = AltAz(az=2.7677669529 * u.deg, alt=6.665063509 * u.deg)
        telescope_coord3 = AltAz(az=2.7677669529 * u.deg, alt=5.665063509 * u.deg)
        affine_transformation = AffineTransformation(
            altaz_coord1,
            altaz_coord2,
            altaz_coord3,
            telescope_coord1,
            telescope_coord2,
            telescope_coord3,
        )

        telescope2 = affine_transformation.matrix_transform(altaz_coord1)
        assert telescope2.alt.deg == pytest.approx(telescope_coord1.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope_coord1.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(telescope_coord1)
        assert altaz2.alt.deg == pytest.approx(altaz_coord1.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz_coord1.az.deg)
