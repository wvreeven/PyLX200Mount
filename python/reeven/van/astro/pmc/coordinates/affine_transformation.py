import numpy as np
from skimage import transform

__all__ = ["AffineTransformation"]


class AffineTransformation:
    """Utility class for performing coordinate transformations from AltAz to
    telescope frame coordinates and back.

    Parameters
    ----------
    altaz : `np.ndarray`
        An array with computed AltAz altitude and azimuth coordinates for the
        same 3 sources.
    telescope : `np.ndarray`
        An array with observed telescope frame altitude and azimuth coordinates
        for 3 sources.

    Attributes
    ----------
    matrix : `np.ndarray`
        The estimated affine transformation matrix based on the computed AltAz
        and observed telescope frame coordinates.

    Notes
    -----
    All computations done in this class are actually performed by the scikit
    image package. This is merely a convenience wrapper class tailored to the
    use case of performing a three star alignment with an AltAz telescope.
    """

    def __init__(self, altaz: np.ndarray, telescope: np.ndarray) -> None:
        self.matrix = transform.estimate_transform("affine", altaz, telescope).params

    def matrix_transform(self, altaz: np.ndarray) -> np.ndarray:
        """Perform an affine transformation of the computed AltAz coordinates
        to the observed telescope frame coordinates.

        Parameters
        ----------
        altaz : `np.ndarray`
            The computed AltAz coordinates to transform to telescope frame
            coordinates.

        Returns
        -------
        np.ndarray
            The telescope frame coordinates after performing the affine
            transformation.
        """
        telescope = transform.matrix_transform(altaz, self.matrix)
        return telescope[0]

    def reverse_matrix_transform(self, telescope: np.ndarray) -> np.ndarray:
        """Perform an affine transformation of the observed telescope frame
        coordinates to AltAz coordinates.

        Parameters
        ----------
        telescope : `np.ndarray`
            The observed telescope frame coordinates to transform to AltAz
            coordinates.

        Returns
        -------
        np.ndarray
            The AltAz coordinates after performing the affine transformation.
        """
        altaz = transform.matrix_transform(telescope, np.linalg.inv(self.matrix))
        return altaz[0]
