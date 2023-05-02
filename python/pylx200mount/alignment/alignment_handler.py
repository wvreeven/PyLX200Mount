from itertools import combinations

import numpy as np
from astropy.coordinates import SkyCoord

from ..enums import IDENTITY
from .affine_transformation import (
    AlignmentPoint,
    AlignmentTriplet,
    compute_transformation_matrix,
)

__all__ = ["AlignmentHandler"]


class AlignmentHandler:
    """Utility class for handling the alignment of a telescope.

    A three-star alignment is assumed to be done. The observer is free to select the three stars to perform
    the alignment with. If after the three-star alignment the telescope is synced with more objects, they get
    added to the alignment handler so an improved transformation matrix can be computed.

    Attributes
    ----------
    transformation_matrix : `np.ndarray`
        The Numpy array representing the transformation matrix.
    """

    def __init__(self) -> None:
        self._alignment_data: list[AlignmentPoint] = list()
        self.transformation_matrix = IDENTITY

    def add_alignment_position(self, altaz: SkyCoord, telescope: SkyCoord) -> None:
        """Add an alignment point.

        Parameters
        ----------
        altaz : `SkyCoord`
            The actual [azimuth, altitude].
        telescope : `SkyCoord`
            The telescope [azimuth, altitude].
        """
        self._alignment_data.append(AlignmentPoint(altaz=altaz, telescope=telescope))

    async def compute_transformation_matrix(self) -> None:
        """Compute the transformation matrix between the altaz and telescope coordinates.

        The transformation matrix only is computed if at least three alignment points have been added. If more
        thatn three alignment points have been added, the transformation matrix is computed for all unique
        combinations of three alignment points.

        If two or more alignment points are very close together, the resulting transformation matrix will
        contain one or more NaN values. In that case, the transformation matrix gets discarded. The mean
        matrix then is computed over the remaining matrices.
        """
        transformation_matrices: list[np.ndarray] = []
        alignment_triplets = [
            AlignmentTriplet(one=triplet[0], two=triplet[1], three=triplet[2])
            for triplet in combinations(self._alignment_data, 3)
        ]
        for alignment_triplet in alignment_triplets:
            matrix = compute_transformation_matrix(alignment_triplet)
            transformation_matrices.append(matrix)
        if len(transformation_matrices) == 0:
            self.transformation_matrix = IDENTITY
        elif len(transformation_matrices) == 1:
            self.transformation_matrix = transformation_matrices[0]
        else:
            # Filter out NaN values
            transformation_matrices = [
                tfm for tfm in transformation_matrices if not np.isnan(np.sum(tfm))
            ]
            # Compute the mean.
            self.transformation_matrix = np.mean(transformation_matrices, axis=0)
