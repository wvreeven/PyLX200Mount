from dataclasses import dataclass

import numpy as np
from astropy.coordinates import SkyCoord
from skimage import transform

from ..my_math.astropy_util import get_skycoord_from_alt_az
from ..observing_location import ObservingLocation

__all__ = [
    "AffineTransformation",
    "AlignmentPoint",
    "AlignmentTriplet",
    "compute_transformation_matrix",
]


def _altaz_to_ndarray(altaz: SkyCoord) -> np.ndarray:
    return np.array([altaz.az.deg, altaz.alt.deg])


def _ndarray_to_altaz(
    array: np.ndarray, observing_location: ObservingLocation
) -> SkyCoord:
    return get_skycoord_from_alt_az(
        az=array[0], alt=array[1], observing_location=observing_location
    )


@dataclass
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

    def as_ndarrays(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the altaz and telescope coordinates of the three `AlignmentPoint`s as two arrays.

        Returns
        -------
        tuple of np.ndarray and np.ndarray
            The altaz coordinates and telescope coordinates in a Numpy array format.
        """
        return np.array(
            (
                _altaz_to_ndarray(self.one.altaz),
                _altaz_to_ndarray(self.two.altaz),
                _altaz_to_ndarray(self.three.altaz),
            )
        ), np.array(
            (
                _altaz_to_ndarray(self.one.telescope),
                _altaz_to_ndarray(self.two.telescope),
                _altaz_to_ndarray(self.three.telescope),
            )
        )


def compute_transformation_matrix(coords: AlignmentTriplet) -> np.ndarray:
    """Compute the transformation matrix between the altaz and telescope coordinates of the AlignmentTriplet.

    Parameters
    ----------
    coords : `AlignmentTriplet`
        The triplet of altaz and telescope coordinates to compute the transformation matrix for.

    Returns
    -------
    np.ndarray
        The array representing the transformation matrix between the provided altaz and telescope coordinates.
    """
    altaz_coords, telescope_coords = coords.as_ndarrays()
    return transform.estimate_transform("affine", altaz_coords, telescope_coords).params


class AffineTransformation:
    """Utility class for performing coordinate transformations from altaz to telescope frame coordinates and
    back.

    Parameters
    ----------
    matrix : `np.ndarray`
        The estimated affine transformation matrix based on the computed AltAz and observed telescope frame
        coordinates.

    Notes
    -----
    All computations done in this class are actually performed by the scikit image package. This is merely a
    convenience wrapper class tailored to the use case of performing a three star alignment with an AltAz
    telescope.
    """

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = matrix

    def matrix_transform(self, altaz_coord: SkyCoord) -> SkyCoord:
        """Perform an affine transformation of the computed AltAz coordinates to the observed telescope frame
        coordinates.

        Parameters
        ----------
        altaz_coord : `SkyCoord`
            The computed AltAz coordinates to transform to telescope frame coordinates.

        Returns
        -------
        SkyCoord
            The telescope frame coordinates after performing the affine transformation.
        """
        observing_location = ObservingLocation()
        observing_location.location = altaz_coord.location
        altaz = _altaz_to_ndarray(altaz_coord)
        telescope = transform.matrix_transform(altaz, self.matrix)[0]
        return _ndarray_to_altaz(telescope, observing_location)

    def reverse_matrix_transform(self, telescope_coord: SkyCoord) -> SkyCoord:
        """Perform an affine transformation of the observed telescope frame coordinates to AltAz coordinates.

        Parameters
        ----------
        telescope_coord : `SkyCoord`
            The observed telescope frame coordinates to transform to AltAz coordinates.

        Returns
        -------
        SkyCoord
            The AltAz coordinates after performing the affine transformation.
        """
        observing_location = ObservingLocation()
        observing_location.location = telescope_coord.location
        telescope = _altaz_to_ndarray(telescope_coord)
        altaz = transform.matrix_transform(telescope, np.linalg.inv(self.matrix))[0]
        return _ndarray_to_altaz(altaz, observing_location)
