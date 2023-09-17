# Miniplayer

# Installation
## Dependencies
### Miniplayer
+ Node-RED (running on a host machine or locally) and MQTT (host or local)
+ paho.mqtt.python (http://github.com/eclipse/paho.mqtt.python)
+ pygame (http://github.com/pygame/pygame)
+ requests (http://github.com/psf/requests)
+ pigpio - **OPTIONAL** (Allows backlight control through GPIO PWM) (http://github.com/joan2937/pigpio)

### Node-RED
+ node-red-contrib-spotify (https://flows.nodered.org/node/node-red-contrib-spotify)
+ node-red-dashboard - **OPTIONAL** (Shows info and controls) (https://flows.nodered.org/node/node-red-dashboard)

## Node-RED Setup
The miniplayer works by connecting to Node-RED through MQTT. Follow these steps to get it working:

1. If you already have a Node-RED installation, all you need to do is **set the IP in the miniplayer settings**.\
If you need to create a Node-RED instance, please follow the 
[official documentation](https://nodered.org/docs/getting-started/).


2. Once Node-RED is running, please **import the [necessary flow(s)](flows.json)** from this repo.\
If you do not know how to, please follow the 
[official documentation](https://nodered.org/docs/user-guide/editor/workspace/import-export).


3. If you want to use the Local Weather function of the miniplayer,
you need the weather_icons and an OpenWeatherMap account.\
Once you have an account, create an API key and paste the http link into the Weather flow in Node-RED.\
It should look like this: **(Make sure you sign up for the free plan!)**\
![Screenshot of example OpenWeatherMap API page](/docs/images/OpenWeatherMap.png)\
\
The Local Weather function also requires the [/Node-RED/weather_icons](/Node-RED/weather_icons) 
folder to be copied to the Node-RED user folder.\
This folder contains the weather icons that gets sent to the miniplayers.
**It does not need to be installed on the miniplayers!**\
For example, if Node-RED is running on linux, the [weather_icons](/Node-RED/weather_icons) folder should be copied to
`/home/nodered/weather_icons`

## Miniplayer Setup
The miniplayer has a few hard-coded settings that need to be set before it will work.\
To edit them, open [miniplayer.py](miniplayer.py) in a text editor. All settings are under `# SETTINGS` at the top. 

1. Make sure that the IP address to your Node-RED installation is correct.\
To do this, open miniplayer.py with a text editor and **change NODERED to the correct IP** (as a string).\
For example:\
`NODERED = '192.168.1.201'`


2. The miniplayer also has a built-in screensaver. The default timer is 2 minutes.\
To change it simply **set SCREENSAVER_DELAY to the amount of milliseconds** before activating.\
For example, to set the screensaver timer to 5 minutes:\
`SCREENSAVER_DELAY = 300000`


3. Depending on how big your screen is and how performant the machine is,\
you may also want to change the **FPS, WIDTH and HEIGHT** settings.\
For example, to run the miniplayer at 720p and 30FPS, you need to change the following:\
`FPS = 30`\
`WIDTH, HEIGHT = 1280, 720`
