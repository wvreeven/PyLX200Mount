from datetime import datetime

from astropy.coordinates import SkyCoord

from ..my_math.astropy_util import get_radec_from_altaz, get_skycoord_from_alt_az
from .base_mount_controller import BaseMountController

__all__ = ["DemoMountController"]


class DemoMountController(BaseMountController):
    pass

    async def attach_motors(self) -> None:
        pass

    async def detach_motors(self) -> None:
        pass

    async def track_mount(self, target_altaz: SkyCoord) -> None:
        self.telescope_alt_az = target_altaz

    async def slew_mount_altaz(self, now: datetime, target_altaz: SkyCoord) -> None:
        alt = self._determine_new_coord_value(
            time=now,
            curr=self.telescope_alt_az.alt.value,
            target=target_altaz.alt.value,
        )
        az = self._determine_new_coord_value(
            time=now,
            curr=self.telescope_alt_az.az.value,
            target=target_altaz.az.value,
        )
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=alt, az=az, observing_location=self.observing_location
        )
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)

    async def stop_slew_mount(self) -> None:
        pass
