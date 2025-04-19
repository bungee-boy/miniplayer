from plugin import *  # Plugin base class
from pygame import surface
import RPi.GPIO as GPIO

class ScreenBrightnessGpio(PluginBase):
    _mqtt_bl_set = "miniplayer/plugin/backlight/set"
    _mqtt_bl_brightness = "miniplayer/plugin/backlight/brightness"

    def __init__(self):
        super().__init__("Screen Brightness (gpio)")
        self.en_pin = 25
        self.on_state = "ON"  # Set to "OFF" to invert GPIO
        self.default_state = GPIO.HIGH

    def _enable(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.en_pin, GPIO.OUT)

        GPIO.output(self.en_pin, self.default_state)

        self._Mqtt.sub((self._mqtt_bl_set, self._mqtt_bl_brightness), self._receive)

    def _disable(self):
        GPIO.cleanup(self.en_pin)

        self._Mqtt.unsub((self._mqtt_bl_set, self._mqtt_bl_brightness))

    def _receive(self, client, userdata, msg) -> None:
        self.log("Received a message!", LogLevel.INF)

        if msg.topic == self._mqtt_bl_set:  # Turn on / off GPIO
            GPIO.output(self.en_pin, self.default_state if msg.payload.decode() == self.on_state else (GPIO.LOW if self.default_state == GPIO.HIGH else GPIO.HIGH))
            self.log("Set GPIO to " + msg.payload.decode(), LogLevel.INF)
            return

        elif msg.topic == self._mqtt_bl_brightness:  # Set backlight brightness
            msg = json.loads(msg.payload.decode())  # Convert string response to dict (json)
            GPIO.output(self.en_pin, True)
            self._Ui.set_brightness(msg)
            self.log("Set brightness to " + str(msg), LogLevel.INF)
            return
