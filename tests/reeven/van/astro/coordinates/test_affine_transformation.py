import unittest

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz
from reeven.van.astro.pmc.coordinates import AffineTransformation


class TestAffineTransformation(unittest.IsolatedAsyncioTestCase):
    async def test_skimage_transform(self) -> None:
        altaz = np.array([[1.0, 1.0], [1.0, 2.0], [2.0, 1.0]])
        telescope = np.array(
            [
                [2.4142135623730940, 5.732050807568877],
                [2.7677669529663684, 6.665063509461097],
                [2.7677669529663675, 5.665063509461096],
            ]
        )
        affine_transformation = AffineTransformation(altaz, telescope)

        altaz2 = altaz[0]
        telescope2 = affine_transformation.matrix_transform(altaz2)
        np.testing.assert_almost_equal(telescope2, telescope[0])

        altaz2 = telescope[0]
        telescope2 = affine_transformation.reverse_matrix_transform(altaz2)
        np.testing.assert_almost_equal(telescope2, altaz[0])

        altaz = AltAz(az=1.0 * u.deg, alt=1.0 * u.deg)
        telescope = AltAz(az=2.4142135623730940 * u.deg, alt=5.732050807568877 * u.deg)
