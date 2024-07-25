__all__ = ["EmulatedCamera"]

import numpy as np

from ..camera import BaseCamera


class EmulatedCamera(BaseCamera):
    async def open(self) -> None:
        # Deliberately left empty.
        pass

    async def start_imaging(self) -> None:
        # Deliberately left empty.
        pass

    async def stop_imaging(self) -> None:
        # Deliberately left empty.
        pass

    async def get_image_parameters(self) -> None:
        # Deliberately left empty.
        pass

    async def set_gain(self, gain: int) -> None:
        # Deliberately left empty.
        pass

    async def set_exposure_time(self, exposure_time: int) -> None:
        # Deliberately left empty.
        pass

    async def get_image(self) -> np.ndarray:
        return np.zeros([1280, 960])
