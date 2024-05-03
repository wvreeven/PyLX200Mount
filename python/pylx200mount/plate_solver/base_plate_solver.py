__all__ = ["BasePlateSolver"]

import abc
import logging

from astropy.coordinates import SkyCoord  # type: ignore
from PIL import Image

from ..camera import BaseCamera


class BasePlateSolver(abc.ABC):
    """Base class for plate solvers."""

    def __init__(self, camera: BaseCamera) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.camera = camera

    async def open_camera(self) -> None:
        """Open the camera and make sure it uses the full sensor."""
        await self.camera.open()
        await self.camera.set_max_image_size()

    async def set_gain_and_exposure_time(self, gain: int, exposure_time: int) -> None:
        """Set the gain and exposure time.

        Parameters
        ----------
        gain : `int`
            The gain.
        exposure_time : `float`
            The exposure time [ms]
        """
        await self.camera.set_gain(gain)
        await self.camera.set_exposure_time(exposure_time)

    async def take_image(self) -> Image.Image:
        """Use the camera to take an image.

        Returns
        -------
        Image
            The image taken with the camera in PIL Image format.
        """
        data = await self.camera.take_and_get_image()
        data_min = data.min()
        data_max = data.max()
        normalized_data = ((data - data_min) / (data_max - data_min)) * 255
        img = Image.fromarray(normalized_data).convert("L")
        return img

    @abc.abstractmethod
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
        raise NotImplementedError
