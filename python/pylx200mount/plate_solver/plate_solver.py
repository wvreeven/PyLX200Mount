__all__ = ["PlateSolver"]

import asyncio
import concurrent
import math

import tetra3  # type: ignore
from astropy.coordinates import SkyCoord  # type: ignore
from PIL import Image

from ..camera import BaseCamera
from ..datetime_util import DatetimeUtil
from ..my_math import get_skycoord_from_ra_dec
from .base_plate_solver import BasePlateSolver

# Max FOV error [deg].
FOV_MAX_ERROR = 0.25
FOV_FACTOR = 202.265 / 60 / 60


class PlateSolver(BasePlateSolver):
    """Plate solver that uses tetra3 to solve images."""

    def __init__(
        self, camera: BaseCamera, focal_length: float, save_images: bool = False
    ) -> None:
        super().__init__(camera=camera, focal_length=focal_length)
        self.t3 = tetra3.Tetra3(load_database="asi120mm_database")

        self.fov_estimate = 0.0

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
        start = DatetimeUtil.get_timestamp()
        if math.isclose(self.fov_estimate, 0.0):
            # Estimate of the size of the field of view [deg].
            min_img_size = min(self.camera.img_width, self.camera.img_height)
            self.fov_estimate = (
                min_img_size * self.camera.pixel_size * FOV_FACTOR / self.focal_length
            )
            self.log.info(
                f"{self.camera.img_width=}, {self.camera.img_height=}, "
                f"{self.focal_length=}, {self.fov_estimate=}"
            )

        img_start = DatetimeUtil.get_timestamp()
        img = await self.take_image(save_image=self.save_images)
        img_end = DatetimeUtil.get_timestamp()
        self.log.debug(f"Taking an image took {img_end - img_start} s.")
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                center = await loop.run_in_executor(pool, self._blocking_solve, img)
        except Exception as e:
            raise RuntimeError(e)
        finally:
            end = DatetimeUtil.get_timestamp()
            self.log.debug(f"Solving took {end - start} s.")
        return center

    def _blocking_solve(self, img: Image.Image) -> SkyCoord:
        centroids = tetra3.get_centroids_from_image(image=img)
        result = self.t3.solve_from_centroids(
            centroids,
            (img.width, img.height),
            fov_estimate=self.fov_estimate,
            fov_max_error=FOV_MAX_ERROR,
        )
        center = get_skycoord_from_ra_dec(result["RA"], result["Dec"])
        self.fov_estimate = result["FOV"]
        return center
