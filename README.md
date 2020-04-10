# PhidgetMountController
A mount controller commanding Phidgets-driven stepper motors.

To run the code, cd into the python directory and issue

python3 reeven/van/astro/controller/socket_server.py

Then set up an Ekos profile with a simulator CCD and an Autostar mount. Connect via ethernet to the IP address 
of the computer running the socket_server and port 11880.
