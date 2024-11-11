__all__ = ["load_camera_offsets", "load_config", "save_camera_offsets"]

import configparser
import json
import pathlib
import types
import typing

import jsonschema

CONFIG_PATH = pathlib.Path.home() / ".config" / "pylx200mount"
CONFIG_FILE = CONFIG_PATH / "config.json"
CAMERA_OFFSETS_FILE = CONFIG_PATH / "camera_offsets.ini"
JSON_SCHEMA_FILE = pathlib.Path(__file__).parents[0] / "configuration_schema.json"


def load_config() -> types.SimpleNamespace:
    """Load the configuration file.

    The configuration file is expected to be at ${HOME}/.config/pylx200mount/config.json
    If it doesn't exist then a default configuration with emulators only is loaded.

    Returns
    -------
    types.SimpleNamespace
        A SimpleNamespace containing the configuration.
    """
    config: dict[str, typing.Any] = {}

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

    with open(JSON_SCHEMA_FILE, "r") as f:
        json_schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema=json_schema)
    validator.validate(config)

    configuration = types.SimpleNamespace()
    if "alt" in config:
        configuration.alt_module_name = config["alt"]["module"]
        configuration.alt_class_name = config["alt"]["class_name"]
        configuration.alt_hub_port = config["alt"]["hub_port"]
        configuration.alt_gear_reduction = config["alt"]["gear_reduction"]
    if "az" in config:
        configuration.az_module_name = config["az"]["module"]
        configuration.az_class_name = config["az"]["class_name"]
        configuration.az_hub_port = config["az"]["hub_port"]
        configuration.az_gear_reduction = config["az"]["gear_reduction"]
    if "camera" in config:
        configuration.camera_module_name = config["camera"]["module"]
        configuration.camera_class_name = config["camera"]["class_name"]
        configuration.camera_focal_length = config["camera"]["focal_length"]

    return configuration


def load_camera_offsets() -> typing.Tuple[float, float]:
    """Load the camera offsets from file.

    Returns
    -------
    typing.Tuple[float, float]
        The camera [az, alt] offsets.
    """
    if CAMERA_OFFSETS_FILE.exists():
        config = configparser.ConfigParser()
        config.read(CAMERA_OFFSETS_FILE)
        camera_offsets = config["camera_offsets"]
        return camera_offsets.getfloat("az"), camera_offsets.getfloat("alt")

    return 0.0, 0.0


def save_camera_offsets(az: float, alt: float) -> None:
    with open(CAMERA_OFFSETS_FILE, "w") as f:
        config = configparser.ConfigParser()
        config["camera_offsets"] = {"az": str(az), "alt": str(alt)}
        config.write(f)
