__all__ = ["BasePlateSolver"]

import abc
import logging
import pathlib

from astropy.coordinates import SkyCoord  # type: ignore
from PIL import Image

from ..camera import BaseCamera
from ..datetime_util import DatetimeUtil

SAVE_DIR = pathlib.Path("/Users/wouter/PyLX200")


class BasePlateSolver(abc.ABC):
    """Base class for plate solvers."""

    def __init__(self, camera: BaseCamera) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.camera = camera
        now = DatetimeUtil.get_datetime()
        now_string = now.strftime("%Y-%m-%d")
        self.out_dir: pathlib.Path = SAVE_DIR / now_string
        self.out_dir.mkdir(parents=True, exist_ok=True)

    async def open_camera(self) -> None:
        """Open the camera and make sure it uses the full sensor."""
        self.log.debug("Opening camera.")
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
        self.log.debug(f"Setting {gain=} and {exposure_time=}.")
        await self.camera.set_gain(gain)
        await self.camera.set_exposure_time(exposure_time)

    async def take_image(self, save_image: bool = False) -> Image.Image:
        """Use the camera to take an image.

        Parameters
        ----------
        save_image : `bool`, optional
            Save the image (True) or not (False). Defaults to False.

        Returns
        -------
        Image
            The image taken with the camera in PIL Image format.
        """
        data = await self.camera.take_and_get_image()
        img = Image.fromarray(data)

        if save_image:
            timestamp = DatetimeUtil.get_timestamp()
            img.save(self.out_dir / f"{timestamp}.png")

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
