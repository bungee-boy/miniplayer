from plugin import *  # Plugin base class
from pygame import surface
import RPi.GPIO

class ScreenBrightnessGpio(PluginBase):
    _mqtt_bl_set = "miniplayer/plugin/backlight/set"
    _mqtt_bl_brightness = "miniplayer/plugin/backlight/brightness"

    def __init__(self):
        super().__init__("Screen Brightness (gpio)")
        self.bl_pin = 16

    def _enable(self):
        self._Mqtt.sub((self._mqtt_bl_set, self._mqtt_bl_brightness), self._receive)

    def _disable(self):
        self._Mqtt.unsub((self._mqtt_bl_set, self._mqtt_bl_brightness))

    def _receive(self, client, userdata, msg) -> None:
        self.log("Received a message!", LogLevel.INF)

        if msg.topic == self._mqtt_bl_set:  # Turn on / off GPIO
            RPi.GPIO.output(self.bl_pin, msg.payload.decode() == "ON")
            self.log("Set GPIO to " + msg.payload.decode(), LogLevel.INF)
            return

        elif msg.topic == self._mqtt_bl_brightness:  # Set backlight brightness
            msg = json.loads(msg.payload.decode())  # Convert string response to dict (json)
            RPi.GPIO.output(self.bl_pin, True)
            self._Ui.set_brightness(msg)
            self.log("Set brightness to " + str(msg), LogLevel.INF)
            return
