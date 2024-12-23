import unittest

import numpy as np
import pylx200mount
import pytest
from numpy import testing as np_testing


class TestAlignmentHandler(unittest.IsolatedAsyncioTestCase):
    async def test_alignment_transform_identity(self) -> None:
        observing_location = pylx200mount.observing_location.ObservingLocation()
        now = pylx200mount.DatetimeUtil.get_timestamp()
        telescope = pylx200mount.my_math.get_skycoord_from_alt_az(
            alt=5.732050807,
            az=2.4142135623,
            observing_location=observing_location,
            timestamp=now,
        )
        alignment_handler = pylx200mount.alignment.AlignmentHandler()

        telescope2 = alignment_handler.matrix_transform(telescope, now)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

    async def test_alignment_handler_with_translation_only(self) -> None:
        observing_location = pylx200mount.observing_location.ObservingLocation()
        now = pylx200mount.DatetimeUtil.get_timestamp()
        alignment_handler = pylx200mount.alignment.AlignmentHandler()
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=1.0,
                alt=2.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.0,
                alt=0.0,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=120.0,
                alt=70.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=121.0,
                alt=68.0,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=300.0,
                alt=20.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=301.0,
                alt=18.0,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
            az=359.5,
            alt=-7.0,
            observing_location=observing_location,
            timestamp=now,
        )
        telescope = alignment_handler.matrix_transform(altaz, now)
        assert telescope.az.deg == pytest.approx(0.5)
        assert telescope.alt.deg == pytest.approx(-9.0)
        altaz = alignment_handler.reverse_matrix_transform(telescope, now)
        assert altaz.az.deg == pytest.approx(359.5)
        assert altaz.alt.deg == pytest.approx(-7.0)

    async def test_alignment_handler_with_tree_alignment_points(self) -> None:
        observing_location = pylx200mount.observing_location.ObservingLocation()
        now = pylx200mount.DatetimeUtil.get_timestamp()
        alignment_handler = pylx200mount.alignment.AlignmentHandler()
        np_testing.assert_array_equal(
            alignment_handler.matrix, pylx200mount.enums.IDENTITY
        )
        alignment_handler.compute_transformation_matrix()
        np_testing.assert_array_equal(
            alignment_handler.matrix, pylx200mount.enums.IDENTITY
        )

        altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
            az=1.0,
            alt=1.0,
            observing_location=observing_location,
            timestamp=now,
        )
        telescope = pylx200mount.my_math.get_skycoord_from_alt_az(
            az=2.4142135623,
            alt=5.732050807,
            observing_location=observing_location,
            timestamp=now,
        )
        alignment_handler.add_alignment_position(
            altaz=altaz,
            telescope=telescope,
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=1.0,
                alt=2.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.7677669529,
                alt=6.665063509,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.0,
                alt=1.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.7677669529,
                alt=5.665063509,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        assert (
            np.not_equal(alignment_handler.matrix, pylx200mount.enums.IDENTITY)
        ).any()

        telescope2 = alignment_handler.matrix_transform(altaz, now)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

        altaz2 = alignment_handler.reverse_matrix_transform(telescope, now)
        assert altaz2.alt.deg == pytest.approx(altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz.az.deg)

    async def test_alignment_handler_with_four_alignment_points(self) -> None:
        observing_location = pylx200mount.observing_location.ObservingLocation()
        now = pylx200mount.DatetimeUtil.get_timestamp()
        altaz = pylx200mount.my_math.get_skycoord_from_alt_az(
            az=1.0,
            alt=1.0,
            observing_location=observing_location,
            timestamp=now,
        )
        telescope = pylx200mount.my_math.get_skycoord_from_alt_az(
            az=2.4142135623,
            alt=5.732050807,
            observing_location=observing_location,
            timestamp=now,
        )
        alignment_handler = pylx200mount.alignment.AlignmentHandler()
        alignment_handler.add_alignment_position(
            altaz=altaz,
            telescope=telescope,
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=1.0,
                alt=2.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.7677669529,
                alt=6.665063509,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.0,
                alt=1.0,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.7677669529,
                alt=5.665063509,
                observing_location=observing_location,
                timestamp=now,
            ),
        )
        alignment_handler.add_alignment_position(
            altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.2,
                alt=0.9,
                observing_location=observing_location,
                timestamp=now,
            ),
            telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                az=2.80312229,
                alt=5.55836478,
                observing_location=observing_location,
                timestamp=now,
            ),
        )

        telescope2 = alignment_handler.matrix_transform(altaz, now)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

        altaz2 = alignment_handler.reverse_matrix_transform(telescope, now)
        assert altaz2.alt.deg == pytest.approx(altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(altaz.az.deg)
