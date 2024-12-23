import pathlib
import tempfile
from unittest import IsolatedAsyncioTestCase, mock

import pylx200mount

tmp_dir = tempfile.TemporaryDirectory()
tmp_config_file = pathlib.Path(tmp_dir.name) / "config.json"


@mock.patch("pylx200mount.controller.utils.CONFIG_FILE", tmp_config_file)
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
