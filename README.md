# PyLX200Mount

A mount controller implementing the Meade LX200 protocol and commanding stepper motors.
This allows for any dobson telescope to present itself as an LX200 mount.
Note that LX200 mounts generally are RaDec but under the hood this project uses AltAz.

## Running the code

To control a mount, clone the repo, install via pip and then issue

```run_lx200_mount```

This will run the controller with emulated motors.

## Using real motors

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

## Connecting to the running mount controller

Here are instructions to setup some popular planetarium applications on the computer or mobile device from which you want to command the mount.

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

I am working on support for an INDI profile so it can be used with a stand alone INDI server.
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

Stellarium may complain about the current time now being right. I am working on that.