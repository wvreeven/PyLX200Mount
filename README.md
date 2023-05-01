PyLX200Mount
============

A mount controller implementing the Meade LX200 protocol and commanding stepper motors.
This allows for any dobson telescope to present itself as an AltAz LX200 mount.

To run the code, clone the repo and then issue

```
pip install pylx200mount
run_lx200_mount
```

Then, on the xomputer from which you want to command the mount,  set up an Ekos profile with a simulator CCD, and an Autostar mount.
It is also possible to set up a Meade LX200 Classic or a Meade LX200 GPS/ACF, LX600 mount in SkySafari.
In both cases, the connection must be set to Wi-Fi/Ethernet using the IP address of the computer running PyLX200Mount, and port 11880.

Future plans
------------

Future plans include (and are not restricted to):

  * Support for ASCOM. 
    * Find a way to command the LX200 "mount" via ASCOM, so it can be used from Windows as well.
  * Support for equatorial mounts.
    * At the moment this project only supports AltAz mounts.
      However, nothing in the LX200 protocol prevents it from being used in equatorial mode as well.
      Find a way to implement and, more importantly, test that as well.
  * Add a conda package.

