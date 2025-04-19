from ui import *
from mqtt import MqttClient
import json  # To decode messages from MQTT (used by subclasses)

class PluginBase(Log):
    _Mqtt = MqttClient
    _Ui = Ui

    def __init__(self, name: str):
        super().__init__(name)
        self._is_enabled = False

    @staticmethod
    def set_mqtt(mqtt: MqttClient):
        PluginBase._Mqtt = mqtt

    @staticmethod
    def set_ui(ui: Ui):
        PluginBase._Ui = ui

    def _enable(self) -> None:
        """
        To be overwritten by subclasses.
        Called by enable()
        """
        pass

    def _disable(self) -> None:
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

    def enable(self) -> None:
        """
        Run when the plugin is enabled.
        """
        if self._is_enabled:
            self.log('Called enable whilst already enabled, aborted', LogLevel.WRN)
            return

        self._enable()
        self._is_enabled = True
        self.log('Enabled', LogLevel.INF)

    def disable(self) -> None:
        """
        Run when the plugin is disabled.
        """
        if not self._is_enabled:
            self.log('Called disable whilst already disabled, aborted', LogLevel.WRN)
            return

        self._disable()
        self._is_enabled = False
        self.log('Disabled', LogLevel.INF)

    def _receive(self, client, userdata, msg) -> None:
        """
        To be overwritten by subclasses.\n
        Passed to MQTT to be called on message receive when subscribing, eg:\n
        self._Mqtt.sub("miniplayer/window/topic", self._receive)
        """
        pass

    def update(self) -> None:
        """
        Update the plugin (main logic)
        """
        if self._is_enabled:
            self._update()
