from ui import *
from mqtt import MqttClient
import json  # To decode messages from MQTT (used by subclasses)

class WindowBase(Log):
    _Mqtt = MqttClient
    _Ui = Ui

    def __init__(self, name: str):
        super().__init__(name)
        self._is_active = False

    @staticmethod
    def set_mqtt(mqtt: MqttClient):
        WindowBase._Mqtt = mqtt

    @staticmethod
    def set_ui(ui: Ui):
        WindowBase._Ui = ui

    def _start(self) -> None:
        """
        To be overwritten by subclasses.
        Called by start()
        """
        pass

    def _stop(self) -> None:
        """
        To be overwritten by subclasses.
        Called by stop()
        """
        pass

    def _update(self) -> None:
        """
        To be overwritten by subclasses.
        Called by update()
        """
        pass

    def _receive(self, client, userdata, msg) -> None:
        """
        To be overwritten by subclasses.\n
        Passed to MQTT to be called on message receive when subscribing, eg:\n
        self._Mqtt.sub("miniplayer/window/topic", self._receive)
        """
        pass

    def start(self) -> None:
        """
        Run when the window becomes active
        """
        if self._is_active:
            self.log('Started without stopping, aborted', LogLevel.WRN)
            return

        self._start()
        self._is_active = True
        self.log('Started', LogLevel.INF)

    def stop(self) -> None:
        """
        Run when the window becomes inactive
        """
        if not self._is_active:
            self.log('Stopped without starting, aborted', LogLevel.WRN)
            return

        self._stop()
        self._is_active = False
        self.log('Stopped', LogLevel.INF)

    def draw(self) -> None:
        """
        Draws the window to the screen
        """
        self._Ui.background()
        self._Ui.text(self.name, 20)#, center=(self._Ui.Center, 25))

    def update(self) -> None:
        """
        Update the window (run inputs, updates, etc)
        """
        pass
