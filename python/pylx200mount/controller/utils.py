__all__ = ["load_config"]

import json
import pathlib
import types
import typing

import jsonschema

JSON_SCHEMA_FILE = pathlib.Path(__file__).parents[0] / "configuration_schema.json"
CONFIG_FILE = pathlib.Path.home() / ".config" / "pylx200mount" / "config.json"
DEFAULT_CONFIG: dict[str, typing.Any] = {
    "alt": {
        "module": "pylx200mount.emulation.emulated_motor_controller",
        "class_name": "EmulatedMotorController",
        "hub_port": 0,
        # 200 steps per revolution, 16 microsteps per step and a gear reduction of 2000x.
        "gear_reduction": 0.00005625,
    },
    "az": {
        "module": "pylx200mount.emulation.emulated_motor_controller",
        "class_name": "EmulatedMotorController",
        "hub_port": 1,
        # 200 steps per revolution, 16 microsteps per step and a gear reduction of 2000x.
        "gear_reduction": 0.00005625,
    },
    "camera": {
        "module": "pylx200mount.emulation.emulated_camera",
        "class_name": "EmulatedCamera",
        "focal_length": 0.0,
        "save_images": False,
    },
}


def load_config() -> types.SimpleNamespace:
    """Load the configuration file.

    The configuration file is expected to be at ${HOME}/.config/pylx200mount/config.json
    If it doesn't exist then a default configuration with emulators only is loaded.

    Returns
    -------
    types.SimpleNamespace
        A SimpleNamespace containing the configuration.
    """
    config = DEFAULT_CONFIG
    loaded_config: dict[str, typing.Any] = {}

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            loaded_config = json.load(f)

    with open(JSON_SCHEMA_FILE, "r") as f:
        json_schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema=json_schema)
    validator.validate(DEFAULT_CONFIG)
    validator.validate(loaded_config)

    config = config | loaded_config

    configuration = types.SimpleNamespace(
        alt_module_name=config["alt"]["module"],
        alt_class_name=config["alt"]["class_name"],
        alt_hub_port=config["alt"]["hub_port"],
        alt_gear_reduction=config["alt"]["gear_reduction"],
        az_module_name=config["az"]["module"],
        az_class_name=config["az"]["class_name"],
        az_hub_port=config["az"]["hub_port"],
        az_gear_reduction=config["az"]["gear_reduction"],
        camera_module_name=config["camera"]["module"],
        camera_class_name=config["camera"]["class_name"],
        camera_focal_length=config["camera"]["focal_length"],
        camera_save_images=config["camera"]["save_images"],
    )

    return configuration
