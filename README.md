# Miniplayer

Miniplayer for integration with Node-RED with customisable windows.

![Local weather screenshot](/docs/images/local_weather_screenshot.png)\
![Spotify screenshot](/docs/images/spotify_screenshot.png)

## Quick start
### Linux
1. `git init -b main`
2. `git pull https://github.com/bungee-boy/miniplayer.git`
3. `python3 main.py`
4. `nano config.json`
5. `python3 main.py`
### Windows
1. `git init -b main`
2. `git pull https://github.com/bungee-boy/miniplayer.git`
3. `python3 main.py`
4. `notepad config.json`
5. `python3 main.py`

## Dependencies
### Miniplayer
+ Python v3.9.2+ (https://www.python.org/downloads/)
+ Connection to MQTT broker v2.0.17+ (https://mosquitto.org/download/)
+ Connection to Node-RED v3.0.2+ (using MQTT) (https://nodered.org/docs/getting-started/)
+ paho.mqtt.python v1.6.1+ (http://github.com/eclipse/paho.mqtt.python)
+ pygame v2.4.0+ (http://github.com/pygame/pygame)
+ requests v2.31.0 (http://github.com/psf/requests)
+ pigpio v1.78+  **OPTIONAL** (Enables PWM backlight control) (http://github.com/joan2937/pigpio)
### MQTT
+ none
### Node-RED
+ node-red-contrib-spotify v0.1.4 (https://flows.nodered.org/node/node-red-contrib-spotify)

## Node-RED Setup
1. If you already have a Node-RED installation,\
you need to set `NODERED_IP` and `NODERED_PORT` in [config.json](config.json)\
\
If you do not have Node-RED, please follow the 
[official documentation](https://nodered.org/docs/getting-started/)


2. If you have a username and password for MQTT, then you need to set\
`MQTT_USER` and `MQTT_PASS` in [config.json](config.json)\
\
If you do not have an MQTT broker, please follow
[this tutorial](https://microcontrollerslab.com/install-mosquitto-mqtt-broker-windows-linux/)


2. Once Node-RED is running, please import the [flows.json](flows.json) file into Node-RED.\
If you do not know how to, please follow the 
[official documentation](https://nodered.org/docs/user-guide/editor/workspace/import-export)


3. If you want to use the Local Weather function of the miniplayer,
you will need the weather_icons and an OpenWeatherMap account.\
Once you have an account, create an API key and paste the http link into the OpenWeatherMap http node in Node-RED.\
Your account services page should look like this: **(Make sure you sign up for the free plan!)**\
![Screenshot example of OpenWeatherMap services page](/docs/images/OpenWeatherMap.png)\
\
The Local Weather flow also requires the [/node_red/weather_icons](/node_red/weather_icons)
folder to be copied to the Node-RED user folder.\
This folder contains the weather icons that are sent to the miniplayer(s) from Node-RED.
**It does not need to be installed on the miniplayers, only where Node-RED is running!**\
For example, if Node-RED is running on linux, the [weather_icons](/node_red/weather_icons) folder should be copied to
`/home/nodered/weather_icons` by default.\
(If your Node-RED is located elsewhere, or you would like to change where the folder is located,\
edit the template node under the WEATHER section in Node-RED.)

## Miniplayer Setup
You must configure the miniplayer before launching it.\
To edit them, open [config.json](config.json)

1. Make sure that the IP address and port to your Node-RED installation is correct.\
To do this, change `NODERED_IP` and `NODERED_PORT` to the correct IP and Port.\
For example:\
`NODERED_IP: "192.168.1.201"`\
`NODERED_PORT: 1880`


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

Icons by https://icons8.com/ (https://icons8.com/icons/collections/PMwl5uMDr7mD)\
*Some icons may be modified in this repo compared to downloading them yourself.
