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
    },
}


def load_config() -> types.SimpleNamespace:
    configuration = types.SimpleNamespace()

    with open(JSON_SCHEMA_FILE, "r") as f:
        json_schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema=json_schema)
    validator.validate(DEFAULT_CONFIG)

    config = DEFAULT_CONFIG
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        validator.validate(config)

    setattr(
        configuration,
        "alt_module_name",
        (
            config["alt"]["module"]
            if config["alt"]["module"]
            else DEFAULT_CONFIG["alt"]["module"]
        ),
    )
    setattr(
        configuration,
        "alt_class_name",
        (
            config["alt"]["class_name"]
            if config["alt"]["class_name"]
            else DEFAULT_CONFIG["alt"]["class_name"]
        ),
    )
    setattr(
        configuration,
        "alt_hub_port",
        (
            config["alt"]["hub_port"]
            if config["alt"]["hub_port"]
            else DEFAULT_CONFIG["alt"]["hub_port"]
        ),
    )
    setattr(
        configuration,
        "alt_gear_reduction",
        (
            config["alt"]["gear_reduction"]
            if config["alt"]["gear_reduction"]
            else DEFAULT_CONFIG["alt"]["gear_reduction"]
        ),
    )
    setattr(
        configuration,
        "az_module_name",
        (
            config["az"]["module"]
            if config["az"]["module"]
            else DEFAULT_CONFIG["az"]["module"]
        ),
    )
    setattr(
        configuration,
        "az_class_name",
        (
            config["az"]["class_name"]
            if config["az"]["class_name"]
            else DEFAULT_CONFIG["az"]["class_name"]
        ),
    )
    setattr(
        configuration,
        "az_hub_port",
        (
            config["az"]["hub_port"]
            if config["az"]["hub_port"]
            else DEFAULT_CONFIG["az"]["hub_port"]
        ),
    )
    setattr(
        configuration,
        "az_gear_reduction",
        (
            config["az"]["gear_reduction"]
            if config["az"]["gear_reduction"]
            else DEFAULT_CONFIG["az"]["gear_reduction"]
        ),
    )
    setattr(
        configuration,
        "camera_module_name",
        (
            config["camera"]["module"]
            if config["camera"]["module"]
            else DEFAULT_CONFIG["camera"]["module"]
        ),
    )
    setattr(
        configuration,
        "camera_class_name",
        (
            config["camera"]["class_name"]
            if config["camera"]["class_name"]
            else DEFAULT_CONFIG["camera"]["class_name"]
        ),
    )
    return configuration
