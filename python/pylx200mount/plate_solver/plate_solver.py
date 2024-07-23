__all__ = ["PlateSolver"]

import tetra3  # type: ignore
from astropy.coordinates import SkyCoord  # type: ignore

from ..camera import BaseCamera
from ..my_math import get_skycoord_from_ra_dec
from .base_plate_solver import BasePlateSolver

# Max FOV error [deg].
FOV_MAX_ERROR = 0.25


class PlateSolver(BasePlateSolver):
    """Plate solver that uses tetra3 to solve images."""

    def __init__(
        self, camera: BaseCamera, focal_length: float, save_images: bool = False
    ) -> None:
        super().__init__(camera=camera, focal_length=focal_length)
        self.t3 = tetra3.Tetra3(load_database="asi120mm_database")

        # Estimate of the size of the field of view [deg].
        min_img_size = min(self.camera.img_width, self.camera.img_height)
        self.fov_estimate = min_img_size * 3.76 * 202.265 / self.focal_length / 60 / 60

        self.save_images = save_images

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
        img = await self.take_image(save_image=self.save_images)
        try:
            centroids = tetra3.get_centroids_from_image(image=img)
            result = self.t3.solve_from_centroids(
                centroids,
                (img.width, img.height),
                fov_estimate=self.fov_estimate,
                fov_max_error=FOV_MAX_ERROR,
            )
            center = get_skycoord_from_ra_dec(result["RA"], result["Dec"])
            self.fov_estimate = result["FOV"]
        except Exception as e:
            raise RuntimeError(e)
        return center
