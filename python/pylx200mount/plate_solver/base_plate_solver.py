__all__ = ["BasePlateSolver"]

import abc
import logging
import pathlib

from astropy.coordinates import SkyCoord  # type: ignore
from PIL import Image

from ..camera import BaseCamera
from ..datetime_util import DatetimeUtil

SAVE_DIR = pathlib.Path.home() / "PyLX200"


class BasePlateSolver(abc.ABC):
    """Base class for plate solvers."""

    def __init__(self, camera: BaseCamera, focal_length: float) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.camera = camera
        self.focal_length = focal_length
        self.out_dir: pathlib.Path = SAVE_DIR
        self.out_dir.mkdir(parents=True, exist_ok=True)

    async def open_camera(self) -> None:
        """Open the camera and make sure it uses the full sensor."""
        self.log.debug("Opening camera.")
        await self.camera.open()
        await self.camera.get_image_parameters()

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

    async def start_imaging(self) -> None:
        """Instruct the camera to start imaging."""
        await self.camera.start_imaging()

    async def get_image(self, save_image: bool = False) -> Image.Image:
        """Get the latest image from the camera.

        Parameters
        ----------
        save_image : `bool`, optional
            Save the image (True) or not (False). Defaults to False.

        Returns
        -------
        Image
            The image taken with the camera in PIL Image format.
        """
        data = await self.camera.get_image()
        img = Image.fromarray(data)

        if save_image:
            timestamp = DatetimeUtil.get_timestamp()
            img.save(self.out_dir / f"{timestamp}.png")

        return img

    async def stop_imaging(self) -> None:
        """Instruct the camera to stop imaging."""
        await self.camera.stop_imaging()

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
