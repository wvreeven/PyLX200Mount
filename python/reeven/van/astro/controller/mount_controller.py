import asyncio
import enum
import logging

from astropy.coordinates import AltAz, Angle, SkyCoord
from astropy.time import Time
from astropy import units as u

from reeven.van.astro import ObservingLocation


__all__ = ["MountController", "MountControllerState", "SlewMode"]

"""Fixed slew speed [deg/sec]."""
SLEW_SPEED = 3.0


class MountControllerState(enum.Enum):
    """State of the mount controller."""

    STOPPED = 0
    TRACKING = 1
    SLEWING = 2


class SlewMode(enum.Enum):
    """Slew modes"""

    ALT_AZ = "AltAz"
    RA_DEC = "RaDec"


class MountController:
    """Control the Mount."""

    def __init__(self):
        self.log = logging.getLogger("MountController")
        self.observing_location = ObservingLocation()
        self.alt_az = self.get_skycoord_from_alt_az(90.0, 0.0)
        self.state = MountControllerState.STOPPED
        self.position_loop = None
        self.ra_dec = None

        # Slew related variables
        self.slew_ref_time = 0.0
        self.target_ra_dec = None
        self.slew_mode = SlewMode.ALT_AZ

    async def start(self):
        self.log.info("Start called.")
        self.position_loop = asyncio.create_task(self._start_position_loop())
        self.log.info("Started.")

    async def stop(self):
        self.log.info("Stop called.")
        if self.position_loop:
            self.position_loop.cancel()

    async def _start_position_loop(self):
        """Start the position loop."""
        while True:
            if self.state == MountControllerState.STOPPED:
                await self._stopped()
            elif self.state == MountControllerState.TRACKING:
                await self._track()
            elif self.state == MountControllerState.SLEWING:
                await self._slew()
            else:
                msg = f"Invalid state encountered: {self.state}"
                self.log.error(msg)
                self.state = MountControllerState.STOPPED
                raise NotImplementedError(msg)
            # Loop at 10 Hz.
            await asyncio.sleep(0.1)

    async def _stopped(self):
        """Mount behavior in STOPPED state."""
        self.log.debug("Stopped.")
        self.ra_dec = self.get_radec_from_altaz(alt_az=self.alt_az)

    async def _track(self):
        """Mount behavior in TRACKING state."""
        self.log.debug("Tracking.")
        self.alt_az = self.get_altaz_from_radec(ra_dec=self.ra_dec)

    async def _slew(self):
        """Dispatch slewing to the coroutine corresponding to the slew mode."""
        if self.slew_mode == SlewMode.ALT_AZ:
            await self._slew_altaz()
        elif self.slew_mode == SlewMode.RA_DEC:
            await self._slew_radec()
        else:
            msg = f"Invalid slew mode encountered: {self.slew_mode}"
            self.log.error(msg)
            self.state = MountControllerState.STOPPED
            raise NotImplementedError(msg)

    async def _slew_radec(self):
        """RaDec mount behavior in SLEWING state."""
        self.log.debug(f"Slewing to RaDec ({self.target_ra_dec.to_string('hmsdms')})")
        now = Time.now()
        diff_ra = self.target_ra_dec.ra.value - self.ra_dec.ra.value
        diff_dec = self.target_ra_dec.dec.value - self.ra_dec.dec.value
        time_diff = now - self.slew_ref_time

        ra_step = SLEW_SPEED * time_diff.sec
        if diff_ra < 0:
            ra_step = -ra_step
        dec_step = SLEW_SPEED * time_diff.sec
        if diff_dec < 0:
            dec_step = -dec_step

        if abs(diff_ra) < abs(ra_step):
            ra = self.target_ra_dec.ra.value
            diff_ra = 0
        else:
            ra = self.ra_dec.ra.value + ra_step
        if abs(diff_dec) < abs(dec_step):
            dec = self.target_ra_dec.dec.value
            diff_dec = 0
        else:
            dec = self.ra_dec.dec.value + dec_step

        self.ra_dec = self.get_skycoord_from_ra_dec(ra=ra, dec=dec)
        if diff_ra == 0 and diff_dec == 0:
            self.state = MountControllerState.TRACKING

        self.slew_ref_time = now

    async def _slew_altaz(self):
        """AltAz mount behavior in SLEWING state."""
        now = Time.now()
        target_altaz = self.get_altaz_from_radec(ra_dec=self.target_ra_dec)
        self.log.debug(f"Slewing to AltAz ({target_altaz.to_string()})")
        diff_alt = target_altaz.alt.value - self.alt_az.alt.value
        diff_az = self.get_shortest_path(target_altaz.az, self.alt_az.az).value
        time_diff = now - self.slew_ref_time

        alt_step = SLEW_SPEED * time_diff.sec
        if diff_alt < 0:
            alt_step = -alt_step
        az_step = SLEW_SPEED * time_diff.sec
        if diff_az < 0:
            az_step = -az_step

        if abs(diff_alt) < abs(alt_step):
            alt = target_altaz.alt.value
            diff_alt = 0
        else:
            alt = self.alt_az.alt.value + alt_step
        if abs(diff_az) < abs(az_step):
            az = target_altaz.az.value
            diff_az = 0
        else:
            az = self.alt_az.az.value + az_step

        self.alt_az = self.get_skycoord_from_alt_az(alt=alt, az=az)
        self.ra_dec = self.get_radec_from_altaz(alt_az=self.alt_az)
        if diff_alt == 0 and diff_az == 0:
            self.state = MountControllerState.TRACKING

        self.slew_ref_time = now

    async def get_ra_dec(self):
        """Get the current RA and DEC of the mount.

        Since RA and DEC of the mount are requested in pairs, this method computes both
        the RA and DEC.

        Returns
        -------
        The right ascention and declination.
        """
        return self.ra_dec

    async def set_ra_dec(self, ra_str, dec_str):
        """Set the current RA and DEC of the mount.

        Parameters
        ----------
        ra_str: `str`
            The Right Ascension of the mount in degrees. The format is
            "HH:mm:ss".
        dec_str: `str`
            The Declination of the mount in degrees. The format is "+dd*mm:ss".
        """
        print(f"{ra_str} {dec_str}")
        self.ra_dec = self.get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        self.alt_az = self.get_altaz_from_radec(ra_dec=self.ra_dec)
        self.state = MountControllerState.TRACKING

    async def slew_to(self, ra_str, dec_str):
        """Instruct the mount to slew to the target RA and DEC if possible.

        Parameters
        ----------
        ra_str: `str`
            The Right Ascension of the mount in degrees. The format is
            "HH:mm:ss".
        dec_str: `str`
            The Declination of the mount in degrees. The format is "+dd*mm:ss".

        Returns
        -------
        slew_possible: 0 or 1
            0 means in reach, 1 not.
        """
        ra_dec = self.get_skycoord_from_ra_dec_str(ra_str=ra_str, dec_str=dec_str)
        alt_az = self.get_altaz_from_radec(ra_dec=self.ra_dec)
        if alt_az.alt.value > 0:
            self.slew_ref_time = Time.now()
            self.target_ra_dec = ra_dec
            self.state = MountControllerState.SLEWING
            return "0"
        else:
            return "1"

    async def stop_slew(self):
        """Stop the slew and start tracking where the mount is pointing at."""
        self.state = MountControllerState.TRACKING

    # noinspection PyMethodMayBeStatic
    def get_skycoord_from_ra_dec(self, ra, dec):
        return SkyCoord(
            ra=Angle(ra * u.deg),
            dec=Angle(dec * u.deg),
            frame="icrs",
        )

    # noinspection PyMethodMayBeStatic
    def get_skycoord_from_ra_dec_str(self, ra_str, dec_str):
        return SkyCoord(
            ra=Angle(ra_str + " hours"),
            dec=Angle(dec_str.replace("*", ":") + " degrees"),
            frame="icrs",
        )

    def get_skycoord_from_alt_az(self, alt, az):
        time = Time.now()
        return SkyCoord(
            alt=Angle(alt * u.deg),
            az=Angle(az * u.deg),
            frame="altaz",
            obstime=time,
            location=self.observing_location.location,
        )

    def get_altaz_from_radec(self, ra_dec):
        time = Time.now()
        return ra_dec.transform_to(
            AltAz(obstime=time, location=self.observing_location.location)
        )

    # noinspection PyMethodMayBeStatic
    def get_radec_from_altaz(self, alt_az):
        return alt_az.transform_to("icrs")

    # noinspection PyMethodMayBeStatic
    def get_shortest_path(self, a1, a2):
        return (a1 - a2).wrap_at(180.0 * u.deg)
