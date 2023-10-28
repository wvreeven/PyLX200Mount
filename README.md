# PyLX200Mount

A mount controller implementing the Meade LX200 protocol and commanding stepper motors.
This allows for any dobson telescope to present itself as an LX200 mount.
Note that LX200 mounts generally are RaDec but under the hood this project uses AltAz.

## Run the code

To control a mount, clone the repo, install via pip and then issue

```run_lx200_mount```

This will run the controller with emulated motors.

## Use real motors

In order to run with your own motor controllers, create the 

```~/.config/pylx200mount/config.json```

according to the [configuration JSON schema](https://github.com/wvreeven/PyLX200Mount/blob/main/python/pylx200mount/controller/configuration_schema.json).

In it make sure to set the `module` and `class_name` for your motor controller class(es) and the `gear_reduction` which represents the angle (deg) for each (micro)step of your motors.
If you use Phidgets motor controllers, like me, then set `module` to `pylx200mount.phidgets.phidgets_motor_controller` and `class_name` to `PhidgetsMotorController`.

If you use different hardware then create a new subclass of `pylx200mount.motor.base_motor_controller.BaseMotorController` and implement the following methods:

  * connect: connect to a motor
  * disconnect: disconnect from a motor
  * set_target_position_and_velocity: set the target position \[steps] and the maximum velocity \[steps/sec] in the motor.

Then set `module` to the python module and `class_name` to the python class for your motor code.

## Connect to the running mount controller

On the computer from which you want to command the mount, do one or more of these:

  * Set up an INDI profile with a simulator CCD, and an `LX200 Basic` mount.
    You can then use KStars, Cartes du Ciel/skychart or any other application that supports INDI to control your mount.
  * Set up a `Meade LX200 Classic` mount in SkySafari.
  * Set up a `Meade: LX200 Classic` mount in AstroPlanner.

In case of SkySafari, I tested SkySafari 6 on macOS and SkySafari 6 and 7 on iOS.
In all cases, the connection must be set to Wi-Fi/Ethernet using the IP address of the computer running PyLX200Mount and port 11880.

I tried Stellarium on iOS and that appears to use a more modern LX200 protocol that is not supported by PyLX200Mount.
I may add support for that in a future version.