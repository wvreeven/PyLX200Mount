# PyLX200Mount

A mount controller implementing the Meade LX200 protocol and commanding stepper motors.
This allows for any dobson telescope to present itself as an LX200 mount.
Support for ASI120MM-S/MC-S cameras is also built in.
Using one improves the accuracy of plate solving and allows for accurate push-to capabilities if no motors are used.
An optimized solver database has been created for the supported cameras.
Note that LX200 mounts generally are RaDec but under the hood this project uses AltAz.

> ***At the moment both the motor support and plate solving support are experimental.***

## Running the code

To control a mount, clone the repo, install via pip and then issue

```run_lx200_mount```

This will run the controller with emulated motors.

## Using real motors

In order to run with your own motor controllers, create a 

```~/.config/pylx200mount/config.json```

file according to the [configuration JSON schema](https://github.com/wvreeven/PyLX200Mount/blob/main/python/pylx200mount/controller/configuration_schema.json).

In it make sure to set the `module` and `class_name` for your motor controller class(es) and the `gear_reduction` which represents the angle (deg) for each (micro)step of your motors.
If you use Phidgets motor controllers, like me, then set `module` to `pylx200mount.phidgets.phidgets_motor_controller` and `class_name` to `PhidgetsMotorController`.
If you want use different motor hardware then create a new subclass of `pylx200mount.motor.base_motor_controller.BaseMotorController` and implement the following methods:

  * connect: connect to a motor
  * disconnect: disconnect from a motor
  * set_target_position_and_velocity: set the target position \[steps] and the maximum velocity \[steps/sec] in the motor

Then set `module` to the python module and `class_name` to the python class for your motor code.

## Using plate solving

You can also set the `module` and `class_name` for your camera, the focal length of the lens or telescope [mm] and whether or not to save the images taken with the camera to enable plate solving.
Currently only ASI120MM-S/MC-S cameras are supported.
If you want to use a different camera then create a new subclass of  `pylx200mount.camera.base_camera.BaseCamera` and implement the following methods:

  * open: open and connect to the camera
  * get_image_parameters: get the maximum image size and pixel size from the camera and set and the bit depth
  * set_gain: set the gain of the camera
  * set_exposure_time: set the exposure time of the camera
  * take_and_get_image: take an image with the camera and return it as a numpy araay

Note that the default tetra3 solver database may not work well with your camera.

### Under the plate solving hood

The idea for using a camera for plate solving came from the [PiFinder]()https://www.pifinder.io/ project.
The source code is open source and can be found [here](https://github.com/brickbots/PiFinder).
For rapid plate solving [tetra3](https://github.com/esa/tetra3) is used, just like in PiFinder.
I experimented with plate solving with tetra3 with images taken with an ASI120MM-S camera and a 25 mm CCTV lens.
In the end I created a plate solver database using tetra3 for which all those images, that don't show too much trailing due to telescope motion, solve within 150 ms.
The name of the db is hard coded in the source code for now but it will become a configuration option soon.

The database was created with:

```python
import tetra3
t3 = tetra3.Tetra3()
t3.generate_database(
    max_fov=11.0,
    min_fov=7.5,
    pattern_stars_per_fov=20,
    save_largest_edge=True,
    save_as="asi120mm_database",
)
```

It took about an hour on my 2020 Intel MacBook to create the db.
Note that the db is not included in this GitHub repo.
It can be downloaded [here](https://wvreeven.stackstorage.com/s/pylx200mount_databases).

As soon as a planetarium application connects to the PyLX200Mount software and the position loop starts, the camera starts taking images.
Those images are plate solved using tetra3.
The resulting position is returned to the planetarium application.

A sync on a known target with the planetarium application is necessary to determine the camera offset w.r.t. the telescope.
As soon as a sync is done in the planetarium position, the sync position in RaDec is converted to AltAz.
A picture is taken and solved and the resulting camera position RaDec is converted to AltAz as well.
The difference between the two positions is stored.
From then on, that difference is applied to the AltAz camera position resulting from yet more images and converted back to RaDec.
That corrected position is then returned to the planetarium application which then correctly shows where the telescope is pointing in the sky.

## Configuration examples

A configuration file for push-to with an ASI120MM-S camera looks like this:

```json
{
  "camera": {
    "module": "pylx200mount.asi",
    "class_name": "AsiCamera",
    "focal_length": 25.0,
    "save_images": true
  }
}
```

A configuration file for GOTO with Phidgets motor controllers looks like this:

```json
{
  "alt": {
    "module": "pylx200mount.phidgets",
    "class_name": "PhidgetsMotorController",
    "hub_port": 0,
    "gear_reduction": 0.00005625
  },
  "az": {
    "module": "pylx200mount.phidgets",
    "class_name": "PhidgetsMotorController",
    "hub_port": 1,
    "gear_reduction": 0.00005625
  }
}
```

A configuration file GOTO with Phidgets motor controllers and an ASI120MM-S camera for plate solving looks like this:

```json
{
  "alt": {
    "module": "pylx200mount.phidgets",
    "class_name": "PhidgetsMotorController",
    "hub_port": 0,
    "gear_reduction": 0.00005625
  },
  "az": {
    "module": "pylx200mount.phidgets",
    "class_name": "PhidgetsMotorController",
    "hub_port": 1,
    "gear_reduction": 0.00005625
  },
  "camera": {
    "module": "pylx200mount.asi",
    "class_name": "AsiCamera",
    "focal_length": 25.0,
    "save_images": true
  }
}
```

## Connecting to the running mount controller

Here are instructions to set up some popular planetarium applications on the computer or mobile device from which you want to command the mount.

In all cases, the connection must be set to Wi-Fi/Ethernet using the IP address of the computer running PyLX200Mount and port 11880.

### SkySafari 6 (macOS)

In the menu bar click Telescope and select Setup...  
Set the following properties:
  * Scope Type: `Meade LX200 Classic` 
  * Mount Type: `Alt-Az GoTo`
  * Connection: `WiFo or Ethernet (TCP/IP)`

Enter the IP address and port as indicated above and click the Connect button on the bottom left.

### SkySafari 7 (iOS)

Open the settings and scroll down to Telescope Presets.  
Press the `+ Add Preset` button.  
Select `Other`.  
Set the following properties:
  * Mount Type: `Alt-Az GoTo`
  * Scope Type: `Meade LX200 Classic`

Press `Next...` to the upper right.  
Enter the IP address and port as indicated above and press `Next...` to the upper right.  
Enter a name if you like and press `Save Preset`.  
Back in the main screen, press the `Scope` button and then the `Connnect` button.  

### AstroPlanner 2.3 and newer

Open the Telescope Resources and either select an exisiting telescope or add a new one.  
Under `Computerized Mount (if applicable)` select `Meade: LX200 Classic`.  
Click the `Edit` button.  
Enable `Use WiFi-to-Serial adapter or TCP/IP` and set it to `Direct TCP/IP`.  
Set `WiFi-to-Serial adapter or TCP/IP address` to the IP address and port as indicated above.  
Under Coordinates enable both `Convert coordinates TO mount to current epoch` and `Convert coordinates FROM mount to current epoch`.  
Press OK and close the Telescope Resources dialog.  
Select the telescope you just configured and toggle `Connect to telescope`.

### INDI

I am working on support for an INDI profile, so it can be used with a stand alone INDI server.
Until then KStars needs to be used.

In KStars, press CTRL-SHIFT-D to open the device manager.  
Under Telescopes, select either `LX200 Basic` or `LX200 Classic`.  
Click `Run Service`.  
Open the Connection tab and set the Connection Mode to `Network`.  
Enter the IP address and port as indicated above and click the Set button to the right of them.  
Open the Main Control tab and click `Connect`.

### Stellarium (iOS)

In the menu to the top left, select `Observing Tools` and enable `Telescope Control`.  
Enter the IP address and port as indicated above.  
Toggle the switch to the right of `Link`.