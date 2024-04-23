__all__ = ["BaseCamera"]

import abc

import numpy as np


class BaseCamera(abc.ABC):
    def __init__(self) -> None:
        self.camera_id = 0
        self.img_width = 0
        self.img_height = 0

    @abc.abstractmethod
    async def open(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def set_max_image_size(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def set_gain(self, gain: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def set_exposure_time(self, exposure_time: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def take_and_get_image(self) -> np.ndarray:
        raise NotImplementedError
