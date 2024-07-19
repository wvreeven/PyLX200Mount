__all__ = ["PlateSolver"]

import tetra3  # type: ignore
from astropy.coordinates import SkyCoord  # type: ignore

from ..camera import BaseCamera
from ..my_math import get_skycoord_from_ra_dec
from .base_plate_solver import BasePlateSolver

# Estimate of the size of the field of view [deg].
FOV_ESTIMATE = 7.92
# Max FOV error [deg].
FOV_MAX_ERROR = 0.05


class PlateSolver(BasePlateSolver):
    """Plate solver that uses tetra3 to solve images."""

    def __init__(self, camera: BaseCamera) -> None:
        super().__init__(camera=camera)
        self.t3 = tetra3.Tetra3(load_database="wouter_database")

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
        img = await self.take_image(save_image=True)
        try:
            centroids = tetra3.get_centroids_from_image(image=img)
            result = self.t3.solve_from_centroids(
                centroids,
                (img.width, img.height),
                fov_estimate=FOV_ESTIMATE,
                fov_max_error=FOV_MAX_ERROR,
            )
            center = get_skycoord_from_ra_dec(result["RA"], result["Dec"])
        except Exception as e:
            raise RuntimeError(e)
        return center
