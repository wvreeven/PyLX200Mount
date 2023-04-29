from itertools import combinations

import numpy as np
from astropy.coordinates import SkyCoord

from ..controller.enums import IDENTITY
from .affine_transformation import (
    AlignmentPoint,
    AlignmentTriplet,
    compute_transformation_matrix,
)

__all__ = ["AlignmentHandler"]


class AlignmentHandler:
    def __init__(self) -> None:
        self._alignment_data: list[AlignmentPoint] = list()
        self.transformation_matrix = IDENTITY

    def add_alignment_position(self, altaz: SkyCoord, telescope: SkyCoord) -> None:
        self._alignment_data.append(AlignmentPoint(altaz=altaz, telescope=telescope))

    async def compute_alignment_matrix(self) -> None:
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
