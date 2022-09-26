import asyncio
import logging
from datetime import datetime

import astropy.units as u
from astropy.coordinates import Angle, EarthLocation, Latitude, Longitude, SkyCoord
from reeven.van.astro.pmc.controller.enums import TELESCOPE_REDUCTION_06INCH
from reeven.van.astro.pmc.observing_location import ObservingLocation
from reeven.van.astro.pmc.phidgets.my_altaz import MyAltAz

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    level=logging.DEBUG,
)

log = logging.getLogger(__name__)

location = EarthLocation.from_geodetic(
    lon=Longitude("-71d14m12.5s"),
    lat=Latitude("-29d56m29.7s"),
    height=110.0 * u.meter,
)
observing_location = ObservingLocation()
observing_location.location = location
my_altaz = MyAltAz(
    observing_location=observing_location,
    telescope_reduction=TELESCOPE_REDUCTION_06INCH,
    log=log,
)


async def move() -> None:
    await my_altaz.attach_steppers()

    target_altaz = SkyCoord(
        alt=Angle(50.0, u.deg),
        az=Angle(320.0, u.deg),
        location=observing_location.location,
        frame="altaz",
        obstime=datetime.now(),
    )
    await my_altaz.slew(target_altaz)
    await asyncio.sleep(20)

    target_altaz = SkyCoord(
        alt=Angle(50.0, u.deg),
        az=Angle(178.5, u.deg),
        location=observing_location.location,
        frame="altaz",
        obstime=datetime.now(),
    )
    await my_altaz.slew(target_altaz)
    await asyncio.sleep(20)

    await my_altaz.stop_motion()
    await asyncio.sleep(5)

    target_altaz = SkyCoord(
        alt=Angle(70.0, u.deg),
        az=Angle(80.0, u.deg),
        location=observing_location.location,
        frame="altaz",
        obstime=datetime.now(),
    )
    await my_altaz.slew(target_altaz)
    await asyncio.sleep(5)

    await my_altaz.stop_motion()
    await asyncio.sleep(5)

    await my_altaz.detach_steppers()


asyncio.run(move())
