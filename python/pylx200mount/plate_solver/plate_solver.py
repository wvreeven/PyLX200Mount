__all__ = ["PlateSolver"]

import astropy.units as u  # type: ignore
import tetra3  # type: ignore
from astropy.coordinates import SkyCoord  # type: ignore

from .base_plate_solver import BasePlateSolver

# Estimate of the size of the field of view [deg].
FOV_ESTIMATE = 11.0
# Number of stars to use for solving an image.
PATTERN_CHECKING_STARS = 15


class PlateSolver(BasePlateSolver):
    """Plate solver that uses tetra3 to solve images."""

    async def solve(self) -> SkyCoord:
        """Take an image and solve it.

        Returns
        -------
        SkyCoord
            The RA and Dec of the center of the image taken.

        Raises
        ------
        RuntimeError
            In case no image can be taken or solving it fails.
        """
        img = self.take_image()
        try:
            t3 = tetra3.Tetra3()
            result = t3.solve_from_image(
                img,
                fov_estimate=FOV_ESTIMATE,
                pattern_checking_stars=PATTERN_CHECKING_STARS,
            )
            center = SkyCoord(result["RA"], result["Dec"], unit=u.deg, frame="icrs")
        except Exception as e:
            raise RuntimeError(e)
        return center
