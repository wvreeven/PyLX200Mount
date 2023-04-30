import unittest

import pylx200mount
import pytest


class TestAffineTransformation(unittest.IsolatedAsyncioTestCase):
    async def test_skimage_transform_identity(self) -> None:
        observing_location = pylx200mount.observing_location.ObservingLocation()
        telescope = pylx200mount.my_math.get_skycoord_from_alt_az(
            alt=5.732050807, az=2.4142135623, observing_location=observing_location
        )
        affine_transformation = pylx200mount.alignment.AffineTransformation(
            pylx200mount.enums.IDENTITY
        )

        telescope2 = affine_transformation.matrix_transform(telescope)
        assert telescope2.alt.deg == pytest.approx(telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(telescope.az.deg)

    async def test_skimage_transform(self) -> None:
        observing_location = pylx200mount.observing_location.ObservingLocation()
        coords = pylx200mount.alignment.AlignmentTriplet(
            pylx200mount.alignment.AlignmentPoint(
                altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                    az=1.0, alt=1.0, observing_location=observing_location
                ),
                telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                    az=2.4142135623,
                    alt=5.732050807,
                    observing_location=observing_location,
                ),
            ),
            pylx200mount.alignment.AlignmentPoint(
                altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                    az=1.0, alt=2.0, observing_location=observing_location
                ),
                telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                    az=2.7677669529,
                    alt=6.665063509,
                    observing_location=observing_location,
                ),
            ),
            pylx200mount.alignment.AlignmentPoint(
                altaz=pylx200mount.my_math.get_skycoord_from_alt_az(
                    az=2.0, alt=1.0, observing_location=observing_location
                ),
                telescope=pylx200mount.my_math.get_skycoord_from_alt_az(
                    az=2.7677669529,
                    alt=5.665063509,
                    observing_location=observing_location,
                ),
            ),
        )
        matrix = pylx200mount.alignment.compute_transformation_matrix(coords)
        affine_transformation = pylx200mount.alignment.AffineTransformation(matrix)

        telescope2 = affine_transformation.matrix_transform(coords.one.altaz)
        assert telescope2.alt.deg == pytest.approx(coords.one.telescope.alt.deg)
        assert telescope2.az.deg == pytest.approx(coords.one.telescope.az.deg)

        altaz2 = affine_transformation.reverse_matrix_transform(coords.one.telescope)
        assert altaz2.alt.deg == pytest.approx(coords.one.altaz.alt.deg)
        assert altaz2.az.deg == pytest.approx(coords.one.altaz.az.deg)
