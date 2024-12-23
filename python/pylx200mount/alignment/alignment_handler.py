__all__ = [
    "AlignmentHandler",
    "AlignmentPoint",
]

import math
from dataclasses import dataclass
from itertools import combinations

import numpy as np
from astropy.coordinates import SkyCoord

from ..enums import IDENTITY
from ..my_math.astropy_util import get_radec_from_altaz, get_skycoord_from_alt_az
from ..observing_location import ObservingLocation


def _altaz_to_3d_ndarray(altaz: SkyCoord) -> np.ndarray:
    return np.array([altaz.az.deg, altaz.alt.deg, 1.0])


def _ndarray_to_altaz(
    array: np.ndarray, observing_location: ObservingLocation, timestamp: float
) -> SkyCoord:
    return get_skycoord_from_alt_az(
        az=float(array[0]),
        alt=float(array[1]),
        observing_location=observing_location,
        timestamp=timestamp,
    )


@dataclass(frozen=True)
class AlignmentPoint:
    """Class representing an alignment point.

    An alignment point consists of two points in the sky. One point is the actual [azimuth, altitude] and the
    other point is the [azimuth, altitude] where the telescope is pointing at. The difference is because of
    the telescope not havng been placed exactly horizontally.

    Parameters
    ----------
    altaz : `SkyCoord`
        The actual [azimuth, altitude].
    telescope : `SkyCoord`
        The telescope [azimuth, altitude].
    """

    altaz: SkyCoord
    telescope: SkyCoord

    def __str__(self) -> str:
        return (
            f"AltAz[az={self.altaz.az.deg}, alt={self.altaz.alt.deg}], "
            f"Telescope[az={self.telescope.az.deg}, alt={self.telescope.alt.deg}]"
        )

    def __repr__(self) -> str:
        return f"AlignmentPoint[{self}]"


@dataclass
class AlignmentTriplet:
    """A triplet of `AlignmentPoint`s.

    This is a utility class that is used to compute a transformation matrix for coordinate transformations
    between the actual and the telescope coordinate frames.

    Parameters
    ----------
    one : `AlignmentPoint`
        The first AlignmentPoint.
    two : `AlignmentPoint`
        The second AlignmentPoint.
    three : `AlignmentPoint`
        The third AlignmentPoint.
    """

    one: AlignmentPoint
    two: AlignmentPoint
    three: AlignmentPoint

    def as_3d_ndarrays(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the altaz and telescope coordinates of the three `AlignmentPoint`s as two 3D arrays.

        Each arrays contains three values: the azimuth [deg], the altitude [deg] and 1.0. The latter is needed
        for the affine transformation to work.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            The altaz coordinates and telescope coordinates in a numpy array format.
        """
        return np.array(
            (
                _altaz_to_3d_ndarray(self.one.altaz),
                _altaz_to_3d_ndarray(self.two.altaz),
                _altaz_to_3d_ndarray(self.three.altaz),
            )
        ), np.array(
            (
                _altaz_to_3d_ndarray(self.one.telescope),
                _altaz_to_3d_ndarray(self.two.telescope),
                _altaz_to_3d_ndarray(self.three.telescope),
            )
        )


class AlignmentHandler:
    """Utility class for handling the alignment of a telescope.

    A three-star alignment is assumed to be done. The observer is free to select the three stars to perform
    the alignment with. If after the three-star alignment the telescope is synced with more objects, they get
    added to the alignment handler so an improved transformation matrix can be computed.

    Attributes
    ----------
    matrix : `np.ndarray`
        The numpy array representing the transformation matrix.
    inv_matrix : `np.ndarray`
        The numpy array representing the inverse transformation matrix.
    """

    def __init__(self) -> None:
        self._alignment_data: list[AlignmentPoint] = list()
        self.matrix = IDENTITY
        self.inv_matrix = IDENTITY

    def add_alignment_position(self, altaz: SkyCoord, telescope: SkyCoord) -> None:
        """Add an alignment point and compute the alignment matrix.

        Parameters
        ----------
        altaz : `SkyCoord`
            The actual [azimuth, altitude].
        telescope : `SkyCoord`
            The telescope [azimuth, altitude].
        """
        alignment_point = AlignmentPoint(altaz=altaz, telescope=telescope)
        ra_dec = get_radec_from_altaz(altaz)
        for ad in self._alignment_data:
            ad_ra_dec = get_radec_from_altaz(ad.altaz)
            if math.isclose(ra_dec.ra.deg, ad_ra_dec.ra.deg) and math.isclose(
                ra_dec.dec.deg, ad_ra_dec.dec.deg
            ):
                self._alignment_data.remove(ad)
        self._alignment_data.append(alignment_point)
        self.compute_transformation_matrix()

    def compute_transformation_matrix(self) -> None:
        """Compute the transformation matrix between the altaz and telescope coordinates.

        The transformation matrix only is computed if at least three alignment points have been added. If more
        than three alignment points have been added, the transformation matrix is computed for all unique
        combinations of three alignment points.

        If two or more alignment points are very close together, the resulting transformation matrix will
        contain one or more NaN values. In that case, the transformation matrix gets discarded. The mean
        matrix then is computed over the remaining matrices.

        See https://stackoverflow.com/a/27547597/22247307
        """
        transformation_matrices: list[np.ndarray] = []
        alignment_triplets = [
            AlignmentTriplet(one=triplet[0], two=triplet[1], three=triplet[2])
            for triplet in combinations(self._alignment_data, 3)
        ]
        for alignment_triplet in alignment_triplets:
            altaz_coords, telescope_coords = alignment_triplet.as_3d_ndarrays()
            det = np.linalg.det(altaz_coords)
            if det != 0:
                matrix = np.dot(np.linalg.inv(altaz_coords), telescope_coords)
                transformation_matrices.append(matrix)
            else:
                print(f"Not using {altaz_coords=} because det == 0.")
        if len(transformation_matrices) == 0:
            self.matrix = IDENTITY
        elif len(transformation_matrices) == 1:
            self.matrix = transformation_matrices[0]
        else:
            # Filter out NaN values
            transformation_matrices = [
                tfm for tfm in transformation_matrices if not np.isnan(np.sum(tfm))
            ]
            # Compute the mean.
            self.matrix = np.mean(transformation_matrices, axis=0)
        self.inv_matrix = np.linalg.inv(self.matrix)

    def matrix_transform(self, altaz_coord: SkyCoord, timestamp: float) -> SkyCoord:
        """Perform a transformation of the computed AltAz coordinates to the telescope frame coordinates.

        Parameters
        ----------
        altaz_coord : `SkyCoord`
            The computed AltAz coordinates to transform to telescope frame coordinates.
        timestamp : `float`
            The timestamp to get the AltAz coordinates for.

        Returns
        -------
        SkyCoord
            The telescope frame coordinates after performing the transformation.
        """
        observing_location = ObservingLocation()
        observing_location.location = altaz_coord.location
        altaz = _altaz_to_3d_ndarray(altaz_coord)
        telescope = np.dot(altaz, self.matrix)
        return _ndarray_to_altaz(telescope, observing_location, timestamp)

    def reverse_matrix_transform(
        self, telescope_coord: SkyCoord, timestamp: float
    ) -> SkyCoord:
        """Perform a transformation of the observed telescope frame coordinates to AltAz coordinates.

        Parameters
        ----------
        telescope_coord : `SkyCoord`
            The observed telescope frame coordinates to transform to AltAz coordinates.
        timestamp : `float`
            The timestamp to get the AltAz coordinates for.

        Returns
        -------
        SkyCoord
            The AltAz coordinates after performing the transformation.
        """
        observing_location = ObservingLocation()
        observing_location.location = telescope_coord.location
        telescope = _altaz_to_3d_ndarray(telescope_coord)
        altaz = np.dot(telescope, self.inv_matrix)
        return _ndarray_to_altaz(altaz, observing_location, timestamp)
