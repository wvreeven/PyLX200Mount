from datetime import datetime

from astropy.coordinates import SkyCoord

from ..enums import MountControllerState, SlewDirection
from ..my_math.astropy_util import (
    get_altaz_from_radec,
    get_radec_from_altaz,
    get_skycoord_from_alt_az,
)
from .base_mount_controller import BaseMountController

__all__ = ["DemoMountController"]


class DemoMountController(BaseMountController):
    pass

    async def attach_motors(self) -> None:
        pass

    async def detach_motors(self) -> None:
        pass

    async def track_mount(self) -> None:
        self.telescope_alt_az = get_altaz_from_radec(
            ra_dec=self.ra_dec, observing_location=self.observing_location
        )

    async def slew_mount_altaz(self, target_altaz: SkyCoord, now: datetime) -> None:
        alt, diff_alt = self._determine_new_coord_value(
            time=now,
            curr=self.telescope_alt_az.alt.value,
            target=target_altaz.alt.value,
        )
        az, diff_az = self._determine_new_coord_value(
            time=now,
            curr=self.telescope_alt_az.az.value,
            target=target_altaz.az.value,
        )
        self.telescope_alt_az = get_skycoord_from_alt_az(
            alt=alt, az=az, observing_location=self.observing_location
        )
        self.ra_dec = get_radec_from_altaz(alt_az=self.telescope_alt_az)
        if diff_alt == 0 and diff_az == 0:
            self.state = MountControllerState.TRACKING

    async def stop_slew_mount(self) -> None:
        self.state = MountControllerState.TRACKING
        self.slew_direction = SlewDirection.NONE
