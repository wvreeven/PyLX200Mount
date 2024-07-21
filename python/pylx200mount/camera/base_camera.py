__all__ = ["BaseCamera"]

import abc

import numpy as np


class BaseCamera(abc.ABC):
    """Interface for all camera implementations."""

    def __init__(self) -> None:
        self.camera_id = 0
        self.img_width = 0
        self.img_height = 0

    @abc.abstractmethod
    async def open(self) -> None:
        """Open the camera."""
        raise NotImplementedError

    @abc.abstractmethod
    async def set_max_image_size(self) -> None:
        """Set the maximum image size.

        Also set the bit depth to the required value.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_gain(self, gain: int) -> None:
        """Set the gain.

        Parameters
        ----------
        gain : `int`
            The gain to set.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set_exposure_time(self, exposure_time: int) -> None:
        """Set the exposure time.

        Parameters
        ----------
        exposure_time : `int`
            The exposure time [microseconds] to set.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def take_and_get_image(self) -> np.ndarray:
        """Take and image and return it.

        Returns
        -------
        numpy.ndarray
            The image as a numpy array.
        """
        raise NotImplementedError
