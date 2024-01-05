# Miniplayer
Miniplayer is a python application used to integrate with Node-RED through MQTT.\
It is designed to be robust, adaptable and fully customisable!

Create your own interactive windows, with built-in settings and window management!

This example shows the data from local sensors and merges it from online sources in Node-RED,
before displaying all the information using a Raspberry PI LCD with touchscreen!\
![Miniplayer local weather window screenshot](/docs/images/local_weather.png)\
Enjoy quickly navigating between windows to get all the latest information,\
or maybe to control Spotify such as this one!\
![Miniplayer spotify window screenshot](/docs/images/spotify.png)

# Features
+ Works on any device with python (and dependencies) and a screen!
+ Fully customisable, develop your own windows to do anything!
+ Backlight control through GPIO and screensaver options
+ Standardised code to make creating windows easier
+ Automatic MQTT reconnection with animation and authentication
+ Launch options supported instead of or with settings
+ Resilient code, doesn't crash if there are missing assets or errors


# Installation
## Dependencies
Stated version numbers have been verified as running.\
Make sure your version numbers are equal or above the stated version!
### Miniplayer
+ Python v3.9.2 (Including several builtin libraries) (https://www.python.org/downloads/)
+ Node-RED v3.0.2 (Running on a host machine or locally) (https://nodered.org/docs/getting-started/)
+ MQTT broker v2.0.17 (Running on a host machine or locally) (https://mosquitto.org/download/)
+ paho.mqtt.python v1.6.1 (http://github.com/eclipse/paho.mqtt.python)
+ pygame v2.4.0 (http://github.com/pygame/pygame)
+ requests v2.31.0 (http://github.com/psf/requests)
+ pigpio v1.78 - **OPTIONAL** (Allows backlight control through GPIO PWM)\
(Ensure the pigpio daemon is running using `sudo pigpiod` if used) (http://github.com/joan2937/pigpio)

### Node-RED
+ node-red-contrib-spotify v0.1.4 (https://flows.nodered.org/node/node-red-contrib-spotify)
+ node-red-contrib-rfxcom v2.12.1 (https://flows.nodered.org/node/node-red-contrib-rfxcom)
+ node-red-contrib-image-tools v2.0.4 (https://flows.nodered.org/node/node-red-contrib-image-tools)
+ node-red-dashboard v3.6.0 - **OPTIONAL** (Shows info and controls)\
(If unused you need to disable or delete these nodes) (https://flows.nodered.org/node/node-red-dashboard)
+ node-red-contrib-ui-artless-gauge v0.3.12 - **OPTIONAL** (Cleaner, sleeker version of the default dashboard gauge)\
(If unused you need to convert these nodes to the default gauge type)
(https://flows.nodered.org/node/node-red-contrib-ui-artless-gauge/)
## Node-RED Setup
The miniplayer works by connecting to Node-RED through MQTT. Follow these steps to get it working:

1. If you already have a Node-RED installation,\
you need to set `NODERED_IP` and `NODERED_PORT` in [user_settings.json](config.json).\
\
If you do not have Node-RED, please follow the 
[official documentation](https://nodered.org/docs/getting-started/).


2. If you already have an MQTT broker connected to Node-RED and with no credentials or login,\
please skip to step 3.\
\
If you have a username and password for MQTT, then you need to set\
`MQTT_USER` and `MQTT_PASS` in [user_settings.json](config.json).\
\
If you do not have an MQTT broker, please follow
[this tutorial](https://microcontrollerslab.com/install-mosquitto-mqtt-broker-windows-linux/).


2. Once Node-RED is running, please import the [flows.json](flows.json) file into Node-RED.\
If you do not know how to, please follow the 
[official documentation](https://nodered.org/docs/user-guide/editor/workspace/import-export).


3. If you want to use the Local Weather function of the miniplayer,
you will need the weather_icons and an OpenWeatherMap account.\
Once you have an account, create an API key and paste the http link into the OpenWeatherMap http node in Node-RED.\
Your account services page should look like this: **(Make sure you sign up for the free plan!)**\
![Screenshot example of OpenWeatherMap services page](/docs/images/OpenWeatherMap.png)\
\
The Local Weather flow also requires the [/Node-RED/weather_icons](/node_red/)
folder to be copied to the Node-RED user folder.\
This folder contains the weather icons that are sent to the miniplayer(s) from Node-RED.
**It does not need to be installed on the miniplayers, only where Node-RED is running!**\
For example, if Node-RED is running on linux, the [weather_icons](/node_red/weather_icons) folder should be copied to
`/home/nodered/weather_icons` by default.\
(If your Node-RED is located elsewhere, or you would like to change where the folder is located,\
edit the template node under the WEATHER section in Node-RED.)

## Miniplayer Setup
The miniplayer has a few settings that need to be set before it will work.\
To edit them, open [user_settings.json](config.json) in a text editor.

1. Make sure that the IP address and port to your Node-RED installation is correct.\
To do this, change `NODERED_IP` and `NODERED_PORT` to the correct IP and Port.\
For example:\
`NODERED_IP: "192.168.1.201"`\
`NODERED_PORT: 1880`\
\
**THIS SETTING IS MANDATORY AND MUST BE SET!**


2. The miniplayer also has a built-in screensaver. The default timer is 2 minutes.\
To change it simply set SCREENSAVER_DELAY to the number of milliseconds of idle time\
before activating.\
For example, to set the screensaver timer to 5 minutes:\
`SCREENSAVER_DELAY = 300000` (The default is `120000`)


3. Depending on how big your screen is and how performant the machine is,\
you may also want to change the **FPS, WIDTH and HEIGHT** settings.\
For example, to run the miniplayer at 1080p and 60FPS, you need to change the following:\
`FPS = 60` (The default is `30`)\
`WIDTH, HEIGHT = 1920, 1080` (The default is `1280, 720`)

# Launch Options / Arguments
## Miniplayer
The miniplayer also supports launch arguments for debugging.\
Setting these will force the value to be set at launch regardless of the current settings,\
any settings not specified will still use the current value.\
More than one option can be used at a time by separating them with a space, for example:\
`python miniplayer.py --debug 1 --logging 0`\
This allows much more flexibility to the way you launch the miniplayer!

Note that passing an **incorrect value** to a **valid option** will result in a crash!\
Passing an incorrect option will have no effect.

+ `--debug {1=ON / 0=OFF}` - Forces debug mode on or off
+ `--logging {1=ON / 0=OFF}` - Forces logging on or off

Icons by https://icons8.com/ (https://icons8.com/icons/collections/PMwl5uMDr7mD)\
Some icons may be modified slightly
