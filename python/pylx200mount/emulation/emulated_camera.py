__all__ = ["EmulatedCamera"]

import numpy as np

from ..camera import BaseCamera


class EmulatedCamera(BaseCamera):
    async def open(self) -> None:
        # Deliberately left empty.
        pass

    async def set_max_image_size(self) -> None:
        # Deliberately left empty.
        pass

    async def set_gain(self, gain: int) -> None:
        # Deliberately left empty.
        pass

    async def set_exposure_time(self, exposure_time: int) -> None:
        # Deliberately left empty.
        pass

    async def take_and_get_image(self) -> np.ndarray:
        return np.zeros([1280, 960])
