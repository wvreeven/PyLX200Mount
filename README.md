PyLX200Mount
============

A mount controller implementing the Meade LX200 protocol and commanding stepper motors.
This allows for any dobson telescope to present itself as an LX200 mount.
Note that LX200 mounts generally are RaDec but under the hood this project uses AltAz.

To control a mount, clone the repo, install via pip and then issue

```run_lx200_mount```

This will run the controller with emulated motors.
In order to run with your own motor controllers, create the 

```~/.config/pylx200mount/config.json```

according to the configuration JSON schema found in the pylx200mount.controller module.
The contents are

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "description": "PyLX200Mount configuration schema.",
  "type": "object",
  "properties": {
    "alt": {
      "description": "The configuration for the altitude motor.",
      "$ref": "#/$defs/motor"
    },
    "az": {
      "description": "The configuration for the azimuth motor.",
      "$ref": "#/$defs/motor"
    }
  },
  "$defs": {
    "motor": {
      "type": "object",
      "properties": {
        "class_name": {
          "type": "string",
          "description": "The name of the motor class."
        },
        "module": {
          "type": "string",
          "description": "The Python module for the motor class."
        },
        "hub_port": {
          "type": "integer",
          "description": "The hub port motor. This defines in the Python code whether this is the alt or the az motor."
        },
        "gear_reduction": {
          "type": "number",
          "description": "Translate one step of the motor to what angle the telescope axis will move [deg]."
        }
      },
      "required": [
        "class_name",
        "module",
        "hub_port",
        "gear_reduction"
      ],
      "additionalProperties": false
    }
  },
  "required": [
    "alt",
    "az"
  ],
  "additionalProperties": false
}
```

In it make sure to set the `module` and `class_name` for your motor controller class(es) and the `gear_reduction` which represents the angle (deg) for each (micro)step of your motors.

Then, on the computer from which you want to command the mount, set up an INDI profile with a simulator CCD, and an `LX200 Basic` mount.
You can then use KStars, Cartes du Ciel/skychart or any other application that supports INDI to control your mount.
It is also possible to set up a `Meade LX200 Classic` mount in SkySafari or a `Meade: LX200 Classic` mount in AstroPlanner.
In all cases, the connection must be set to Wi-Fi/Ethernet using the IP address of the computer running PyLX200Mount, and port 11880.

Future plans
------------

Future plans include (and are not restricted to):

* Add three star alignment.
* Add a conda package.
