import math
from unittest import IsolatedAsyncioTestCase

import numpy as np
import astropy.coordinates.representation as r
from astropy.coordinates import (
    BaseCoordinateFrame,
    DynamicMatrixTransform,
    ICRS,
    RepresentationMapping,
    SkyCoord,
    frame_transform_graph,
)


class TelescopeFrame(BaseCoordinateFrame):
    default_representation = r.UnitSphericalRepresentation

    frame_specific_representation_info = {
        r.SphericalRepresentation: [
            RepresentationMapping("lon", "az"),
            RepresentationMapping("lat", "alt"),
        ],
        r.UnitSphericalRepresentation: [
            RepresentationMapping("lon", "az"),
            RepresentationMapping("lat", "alt"),
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@frame_transform_graph.transform(DynamicMatrixTransform, ICRS, TelescopeFrame)
def equatorial_to_telescope(icrs_frame, telescope_frame):
    matrix = get_matrix(
        icrs_frame.ra, icrs_frame.dec, telescope_frame.ra, telescope_frame.dec
    )
    C0 = icrs_frame.represent_as(coord.CartesianRepresentation).xyz.value

    l0 = matrix.dot(C0)

    altAZ = SkyCoord(
        x=l0[0, 0],
        y=l0[0, 1],
        z=l0[0, 2],
        frame="altaz",
        representation="cartesian",
    ).represent_as(UnitSphericalRepresentation)

    return TelescopeFrame(az=altAZ.lon.to(u.deg), alt=altAZ.lat.to(*u.deg))


def get_matrix(ra, dec, ra_acc, dec_acc):
    sin_ra = math.sin(math.radians(ra))
    cos_ra = math.cos(math.radians(ra))
    sin_dec = math.sin(math.radians(90.0 - dec))
    cos_dec = math.cos(math.radians(90.0 - dec))
    sin_ra_acc = math.sin(math.radians(ra_acc))
    cos_ra_acc = math.cos(math.radians(ra_acc))
    sin_dec_acc = math.sin(math.radians(90.0 - dec_acc))
    cos_dec_acc = math.cos(math.radians(90.0 - dec_acc))

    x = sin_dec * cos_ra
    y = sin_dec * sin_ra
    z = cos_dec
    x_acc = sin_dec_acc * cos_ra_acc
    y_acc = sin_dec_acc * sin_ra_acc
    z_acc = cos_dec_acc

    a = (z - z_acc) / y
    numerator = x_acc * (y + z * a) - x * y_acc
    denominator = math.pow(x, 2) + math.pow(y + z * a, 2)
    b = math.asin(numerator / denominator)

    sin_a = math.sin(a)
    cos_a = math.cos(a)
    sin_b = math.sin(b)
    cos_b = math.cos(b)

    return np.matrix(
        (
            [cos_b, cos_a * sin_b, sin_a * sin_b],
            [-sin_b, cos_a * cos_b, sin_a * cos_b],
            [0, -sin_a, cos_a],
        )
    )


class Test(IsolatedAsyncioTestCase):
    async def test_transform_coordinate(self) -> None:
        ra = 10.0
        dec = 9.0
        ra_acc = 11.1
        dec_acc = 8.3

        sin_ra = math.sin(math.radians(ra))
        cos_ra = math.cos(math.radians(ra))
        sin_dec = math.sin(math.radians(90.0 - dec))
        cos_dec = math.cos(math.radians(90.0 - dec))
        sin_ra_acc = math.sin(math.radians(ra_acc))
        cos_ra_acc = math.cos(math.radians(ra_acc))
        sin_dec_acc = math.sin(math.radians(90.0 - dec_acc))
        cos_dec_acc = math.cos(math.radians(90.0 - dec_acc))

        x = sin_dec * cos_ra
        y = sin_dec * sin_ra
        z = cos_dec
        x_acc = sin_dec_acc * cos_ra_acc
        y_acc = sin_dec_acc * sin_ra_acc
        z_acc = cos_dec_acc

        a = (z - z_acc) / y
        numerator = x_acc * (y + z * a) - x * y_acc
        denominator = math.pow(x, 2) + math.pow(y + z * a, 2)
        b = math.asin(numerator / denominator)

        sin_a = math.sin(a)
        cos_a = math.cos(a)
        sin_b = math.sin(b)
        cos_b = math.cos(b)

        matrix = np.matrix(
            (
                [cos_b, cos_a * sin_b, sin_a * sin_b],
                [-sin_b, cos_a * cos_b, sin_a * cos_b],
                [0, -sin_a, cos_a],
            )
        )
