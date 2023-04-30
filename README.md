# PyLx200
A mount controller implementing the Meade LX200 protocol and commanding stepper motors.

To run the code, cd into the python directory and issue

python3 pylx200mount/lx200_mount.py

Then set up an Ekos profile with a simulator CCD, and an Autostar mount.
It is also possible to set up a Meade LX200 Classic or (preferrably) a Meade LX200 GPS/ACF, LX600 mount in SkySafari.
In both cases, the connection must be set to Wi-Fi/Ethernet using the IP address of the computer running PyLX200Mount, and port 11880.