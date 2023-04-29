import unittest

import numpy as np
import pytest
import astropy.units as u
from astropy.coordinates import AltAz
from numpy import testing
from reeven.van.astro.pmc.alignment import AffineTransformation, AlignmentHandler


class TestAlignmentHandler(unittest.IsolatedAsyncioTestCase):
    async def test_alignment_handler_with_tree_alignment_points(self):
        alignment_handler = AlignmentHandler()
        testing.assert_array_equal(
            alignment_handler.transformation_matrix, np.identity(3)
        )
        await alignment_handler.compute_alignment_matrix()
        testing.assert_array_equal(
            alignment_handler.transformation_matrix, np.identity(3)
        )

        altaz = AltAz(az=1.0 * u.deg, alt=1.0 * u.deg)
        telescope = AltAz(az=2.4142135623 * u.deg, alt=5.732050807 * u.deg)
        alignment_handler.add_alignment_position(
            altaz=altaz,
            telescope=telescope,
        )
        alignment_handler.add_alignment_position(
            altaz=AltAz(az=1.0 * u.deg, alt=2.0 * u.deg),
            telescope=AltAz(az=2.7677669529 * u.deg, alt=6.665063509 * u.deg),
        )
        alignment_handler.add_alignment_position(
            altaz=AltAz(az=2.0 * u.deg, alt=1.0 * u.deg),
            telescope=AltAz(az=2.7677669529 * u.deg, alt=5.665063509 * u.deg),
        )
        await alignment_handler.compute_alignment_matrix()
        affine_transformation = AffineTransformation(
            alignment_handler.transformation_matrix
        )

        telescope2 = affine_transformation.matrix_transform(altaz)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(telescope)
        assert altaz2.alt.deg == pytest.approx(altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz.az.deg)

    async def test_alignment_handler_with_four_alignment_points(self):
        altaz = AltAz(az=1.0 * u.deg, alt=1.0 * u.deg)
        telescope = AltAz(az=2.4142135623 * u.deg, alt=5.732050807 * u.deg)
        alignment_handler = AlignmentHandler()
        alignment_handler.add_alignment_position(
            altaz=altaz,
            telescope=telescope,
        )
        alignment_handler.add_alignment_position(
            altaz=AltAz(az=1.0 * u.deg, alt=2.0 * u.deg),
            telescope=AltAz(az=2.7677669529 * u.deg, alt=6.665063509 * u.deg),
        )
        alignment_handler.add_alignment_position(
            altaz=AltAz(az=2.0 * u.deg, alt=1.0 * u.deg),
            telescope=AltAz(az=2.7677669529 * u.deg, alt=5.665063509 * u.deg),
        )
        alignment_handler.add_alignment_position(
            altaz=AltAz(az=2.1 * u.deg, alt=0.9 * u.deg),
            telescope=AltAz(az=2.7777669529 * u.deg, alt=5.565063509 * u.deg),
        )
        await alignment_handler.compute_alignment_matrix()
        affine_transformation = AffineTransformation(
            alignment_handler.transformation_matrix
        )

        telescope2 = affine_transformation.matrix_transform(altaz)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(telescope)
        assert altaz2.alt.deg == pytest.approx(altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz.az.deg)
