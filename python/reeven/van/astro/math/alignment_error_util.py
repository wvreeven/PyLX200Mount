import logging
import math
import typing

from astropy.coordinates import (
    AltAz,
    Angle,
    EarthLocation,
    Latitude,
    SkyCoord,
    SkyOffsetFrame,
)
from astropy.time import Time
import astropy.units as u

from ..observing_location import ObservingLocation

__all__ = ["AlignmentErrorUtil"]


class AlignmentErrorUtil:
    """Utility for alignment error computations."""

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.delta_alt: typing.Optional[Angle] = None
        self.delta_az: typing.Optional[Angle] = None

    def compute_alignment_error(
        self, lat: Latitude, s1: SkyCoord, s2: SkyCoord, err_ra: Angle, err_dec: Angle
    ) -> None:
        """Compute the alignment error for the given latitdue, the given measured sky
        coordinates and the given errors in right ascentsion and declination.

        This computation is based on the Two Star Polar Alignment paper by Ralph Pass in the
        misc/docs directory of the source tree on GitHub.

        Parameters
        ----------
        lat : `Latitude`
            The latitude of the observer.
        s1 : `SkyCoord`
            The right ascension and declination of the first alignment star.
        s2 : `SkyCoord`
            The right ascension and declination of the second alignment star.
        err_ra : `Angle`
            The error in right ascension as measured for the second star.
        err_dec : `Angle`
            The error in declination as measured for the second star.
        """
        # Compute the determinant
        d = (
            math.cos(lat.radian)
            * (math.tan(s1.dec.radian) + math.tan(s2.dec.radian))
            * (1 - math.cos(s1.ra.radian - s2.ra.radian))
        )

        # Compute the four matrix elements using the determinant
        a11 = (
            math.cos(lat.radian) * (math.sin(s2.ra.radian) - math.sin(s1.ra.radian)) / d
        )
        a12 = (
            -math.cos(lat.radian)
            * (
                math.tan(s1.dec.radian) * math.cos(s1.ra.radian)
                - math.tan(s2.dec.radian) * math.cos(s2.ra.radian)
            )
            / d
        )
        a21 = (math.cos(s1.ra.radian) - math.cos(s2.ra.radian)) / d
        a22 = (
            math.tan(s2.dec.radian) * math.sin(s2.ra.radian)
            - math.tan(s1.dec.radian) * math.sin(s1.ra.radian)
        ) / d

        # Compute the errors in altitude and azimuth using the four matrix elements
        self.delta_alt = a11 * err_ra + a12 * err_dec
        self.delta_az = a21 * err_ra + a22 * err_dec

        if self.delta_alt is not None and self.delta_az is not None:
            self.log.info(
                f"Alignment complete. AltAz offset ({self.delta_alt.arcmin},"
                f" {self.delta_az.arcmin}) [arcmin]."
            )

    def get_altaz_in_rotated_frame(
        self,
        time: Time,
        location: EarthLocation,
        altaz: SkyCoord,
    ) -> SkyCoord:
        """Rotates the given coordinates to the frame defined by given the altitude and
        azimuth offsets for the given time and observing_location.

        Parameters
        ----------
        time : `Time`
            The Time for which the AltAz coordinates are valid
        location : `EarthLocation`
            The observing_location for which the AltAz coordinates are valid
        altaz : `SkyCoord`
            The altitude and azimuth to rotate.

        Returns
        -------
        telescope_altaz: `SkyCoord`
            The altitude and azimuth rotated to the new frame.
        """
        telescope_altaz = AltAz(
            alt=self.delta_alt, az=self.delta_az, obstime=time, location=location
        )
        telescope_frame = altaz.transform_to(SkyOffsetFrame(origin=telescope_altaz))
        return SkyCoord(
            alt=Angle(telescope_frame.lon.deg * u.deg),
            az=Angle(telescope_frame.lat.deg * u.deg),
            frame="altaz",
            obstime=time,
            location=location,
        )

    def rotate_alt_az_if_necessary(
        self, alt_az: SkyCoord, observing_location: ObservingLocation
    ) -> None:
        # Prevent an astropy deprecation warning by explicitly testing for None here.
        if self.delta_alt is not None and self.delta_az is not None:
            time = Time.now()
            alt_az_rot = self.get_altaz_in_rotated_frame(
                time=time,
                location=observing_location.location,
                altaz=alt_az,
            )
            self.log.debug(
                f"AltAz {alt_az.to_string('dms')} is rotated "
                f"{alt_az_rot.to_string('dms')}"
            )
            # TODO Make sure that the rotated frame actually is used.
