import unittest

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import AltAz
from reeven.van.astro.pmc.alignment import (
    AffineTransformation,
    AlignmentPoint,
    AlignmentTriplet,
    compute_transformation_matrix,
)


class TestAffineTransformation(unittest.IsolatedAsyncioTestCase):
    async def test_skimage_transform_identity(self) -> None:
        telescope = AltAz(az=2.4142135623 * u.deg, alt=5.732050807 * u.deg)
        matrix = np.identity(3)
        affine_transformation = AffineTransformation(matrix)

        telescope2 = affine_transformation.matrix_transform(telescope)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

    async def test_skimage_transform(self) -> None:
        coords = AlignmentTriplet(
            AlignmentPoint(
                altaz=AltAz(az=1.0 * u.deg, alt=1.0 * u.deg),
                telescope=AltAz(az=2.4142135623 * u.deg, alt=5.732050807 * u.deg),
            ),
            AlignmentPoint(
                altaz=AltAz(az=1.0 * u.deg, alt=2.0 * u.deg),
                telescope=AltAz(az=2.7677669529 * u.deg, alt=6.665063509 * u.deg),
            ),
            AlignmentPoint(
                altaz=AltAz(az=2.0 * u.deg, alt=1.0 * u.deg),
                telescope=AltAz(az=2.7677669529 * u.deg, alt=5.665063509 * u.deg),
            ),
        )
        matrix = compute_transformation_matrix(coords)
        affine_transformation = AffineTransformation(matrix)

        telescope2 = affine_transformation.matrix_transform(coords.one.altaz)
        assert telescope2.alt.deg == pytest.approx(coords.one.telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(coords.one.telescope.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(coords.one.telescope)
        assert altaz2.alt.deg == pytest.approx(coords.one.altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(coords.one.altaz.az.deg)
