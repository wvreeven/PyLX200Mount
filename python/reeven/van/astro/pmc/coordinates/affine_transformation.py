import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz
from skimage import transform

__all__ = ["AffineTransformation"]


def _altaz_to_ndarray(altaz: AltAz) -> np.ndarray:
    return np.array([altaz.az.deg, altaz.alt.deg])


def _ndarray_to_altaz(array: np.ndarray) -> AltAz:
    return AltAz(az=array[0] * u.deg, alt=array[1] * u.deg)


class AffineTransformation:
    """Utility class for performing coordinate transformations from AltAz to
    telescope frame coordinates and back.

    Parameters
    ----------
    altaz_coord1 : `AltAz`
        The first computed AltAz altitude and azimuth coordinates.
    altaz_coord2 : `AltAz`
        The second computed AltAz altitude and azimuth coordinates.
    altaz_coord3 : `AltAz`
        The third computed AltAz altitude and azimuth coordinates.
    telescope_coord1 : `AltAz`
        The first observed telescope frame altitude and azimuth coordinates.
    telescope_coord2 : `AltAz`
        The first observed telescope frame altitude and azimuth coordinates.
    telescope_coord3 : `AltAz`
        The first observed telescope frame altitude and azimuth coordinates.

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

    def __init__(
        self,
        altaz_coord1: AltAz,
        altaz_coord2: AltAz,
        altaz_coord3: AltAz,
        telescope_coord1: AltAz,
        telescope_coord2: AltAz,
        telescope_coord3: AltAz,
    ) -> None:
        altaz_coords = np.array(
            (
                _altaz_to_ndarray(altaz_coord1),
                _altaz_to_ndarray(altaz_coord2),
                _altaz_to_ndarray(altaz_coord3),
            )
        )
        telescope_coords = np.array(
            (
                _altaz_to_ndarray(telescope_coord1),
                _altaz_to_ndarray(telescope_coord2),
                _altaz_to_ndarray(telescope_coord3),
            )
        )
        self.matrix = transform.estimate_transform(
            "affine", altaz_coords, telescope_coords
        ).params

    def matrix_transform(self, altaz_coord: AltAz) -> AltAz:
        """Perform an affine transformation of the computed AltAz coordinates
        to the observed telescope frame coordinates.

        Parameters
        ----------
        altaz_coord : `AltAz`
            The computed AltAz coordinates to transform to telescope frame
            coordinates.

        Returns
        -------
        AltAz
            The telescope frame coordinates after performing the affine
            transformation.
        """
        altaz = _altaz_to_ndarray(altaz_coord)
        telescope = transform.matrix_transform(altaz, self.matrix)[0]
        return _ndarray_to_altaz(telescope)

    def reverse_matrix_transform(self, telescope_coord: AltAz) -> AltAz:
        """Perform an affine transformation of the observed telescope frame
        coordinates to AltAz coordinates.

        Parameters
        ----------
        telescope_coord : `AltAz`
            The observed telescope frame coordinates to transform to AltAz
            coordinates.

        Returns
        -------
        AltAz
            The AltAz coordinates after performing the affine transformation.
        """
        telescope = _altaz_to_ndarray(telescope_coord)
        altaz = transform.matrix_transform(telescope, np.linalg.inv(self.matrix))[0]
        return _ndarray_to_altaz(altaz)
