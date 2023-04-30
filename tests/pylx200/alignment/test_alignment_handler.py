import unittest

import pylx200
import pytest
from numpy import testing as np_testing


class TestAlignmentHandler(unittest.IsolatedAsyncioTestCase):
    async def test_alignment_handler_with_tree_alignment_points(self) -> None:
        observing_location = pylx200.observing_location.ObservingLocation()
        alignment_handler = pylx200.alignment.AlignmentHandler()
        np_testing.assert_array_equal(
            alignment_handler.transformation_matrix, pylx200.enums.IDENTITY
        )
        await alignment_handler.compute_alignment_matrix()
        np_testing.assert_array_equal(
            alignment_handler.transformation_matrix, pylx200.enums.IDENTITY
        )

        altaz = pylx200.my_math.get_skycoord_from_alt_az(
            az=1.0, alt=1.0, observing_location=observing_location
        )
        telescope = pylx200.my_math.get_skycoord_from_alt_az(
            az=2.4142135623, alt=5.732050807, observing_location=observing_location
        )
        alignment_handler.add_alignment_position(
            altaz=altaz,
            telescope=telescope,
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200.my_math.get_skycoord_from_alt_az(
                az=1.0, alt=2.0, observing_location=observing_location
            ),
            telescope=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.7677669529, alt=6.665063509, observing_location=observing_location
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.0, alt=1.0, observing_location=observing_location
            ),
            telescope=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.7677669529, alt=5.665063509, observing_location=observing_location
            ),
        )
        await alignment_handler.compute_alignment_matrix()
        affine_transformation = pylx200.alignment.AffineTransformation(
            alignment_handler.transformation_matrix
        )

        telescope2 = affine_transformation.matrix_transform(altaz)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(telescope)
        assert altaz2.alt.deg == pytest.approx(altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz.az.deg)

    async def test_alignment_handler_with_four_alignment_points(self) -> None:
        observing_location = pylx200.observing_location.ObservingLocation()
        altaz = pylx200.my_math.get_skycoord_from_alt_az(
            az=1.0, alt=1.0, observing_location=observing_location
        )
        telescope = pylx200.my_math.get_skycoord_from_alt_az(
            az=2.4142135623, alt=5.732050807, observing_location=observing_location
        )
        alignment_handler = pylx200.alignment.AlignmentHandler()
        alignment_handler.add_alignment_position(
            altaz=altaz,
            telescope=telescope,
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200.my_math.get_skycoord_from_alt_az(
                az=1.0, alt=2.0, observing_location=observing_location
            ),
            telescope=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.7677669529, alt=6.665063509, observing_location=observing_location
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.0, alt=1.0, observing_location=observing_location
            ),
            telescope=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.7677669529, alt=5.665063509, observing_location=observing_location
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.1, alt=0.9, observing_location=observing_location
            ),
            telescope=pylx200.my_math.get_skycoord_from_alt_az(
                az=2.7777669529, alt=5.565063509, observing_location=observing_location
            ),
        )
        await alignment_handler.compute_alignment_matrix()
        affine_transformation = pylx200.alignment.AffineTransformation(
            alignment_handler.transformation_matrix
        )

        telescope2 = affine_transformation.matrix_transform(altaz)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(telescope)
        assert altaz2.alt.deg == pytest.approx(altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz.az.deg)