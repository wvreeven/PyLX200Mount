from astropy.coordinates import AltAz, Angle, SkyCoord
from astropy import units as u
import logging


class MountController:
    def __init__(self):
        self.log = logging.getLogger("MountController")
        self.tracking = False
        self.aligned = False
        self.ra_dec = None

    # noinspection PyMethodMayBeStatic
    # TODO Add with real implementation as soon as goto and tracking are implemented
    async def get_ra(self, time, location):
        zenith = SkyCoord(
            alt=Angle(90 * u.deg),
            az=Angle(0 * u.deg),
            frame="altaz",
            obstime=time,
            location=location,
        )
        self.ra_dec = zenith.transform_to("icrs")
        return self.ra_dec.ra

    # noinspection PyMethodMayBeStatic
    # TODO Add with real implementation as soon as goto and tracking are implemented
    async def get_dec(self, time, location):
        return self.ra_dec.dec
