import math
import pathlib
import tempfile
from unittest import IsolatedAsyncioTestCase, mock

import pylx200mount

tmp_dir = tempfile.TemporaryDirectory()
tmp_config_file = pathlib.Path(tmp_dir.name) / "config.json"
tmp_camera_file = pathlib.Path(tmp_dir.name) / "camera_offsets.ini"


@mock.patch("pylx200mount.controller.utils.CONFIG_FILE", tmp_config_file)
@mock.patch("pylx200mount.controller.utils.CAMERA_OFFSETS_FILE", tmp_camera_file)
class TestUtils(IsolatedAsyncioTestCase):
    async def test_utils(self) -> None:
        filename = f"{tmp_dir.name}/config.json"
        with open(filename, "w") as fp:
            fp.write(
                """
{
  "camera": {
    "module": "pylx200mount.asi",
    "class_name": "AsiCamera",
    "focal_length": 25.0
  }
}
"""
            )
        config = pylx200mount.controller.load_config()
        assert config.camera_module_name == "pylx200mount.asi"
        assert config.camera_class_name == "AsiCamera"
        assert config.camera_focal_length == 25.0

        az, alt = pylx200mount.controller.load_camera_offsets()
        assert math.isclose(az, 0.0)
        assert math.isclose(alt, 0.0)

        exp_az = 90.0
        exp_alt = 45.0
        pylx200mount.controller.save_camera_offsets(exp_az, exp_alt)
        az, alt = pylx200mount.controller.load_camera_offsets()
        assert math.isclose(az, exp_az)
        assert math.isclose(alt, exp_alt)
