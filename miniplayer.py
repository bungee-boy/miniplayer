from uuid import getnode as get_mac  # Used to set MQTT username as MAC address

import importlib  # Used to import windows dynamically
import windows  # Window subdirectory
import plugins  # Plugin subdirectory

from window import *
from plugin import *

class Miniplayer:
    def __init__(self):
        self._log = Log("Miniplayer")
        self._log.log("Start", LogLevel.INF)

        self._Clock = pg.time.Clock()

        self._Mqtt = MqttClient(str(hex(get_mac())) + "V3", "192.168.1.205", "mosquitto", "bungeeboy12")
        self._Ui = Ui((1024, 600), pg.FULLSCREEN)

        timestamp = pg.time.get_ticks()

        # LOAD MQTT
        self._loading_info("mqtt")
        self._Mqtt.connect()

        # LOAD PLUGINS
        PluginBase.set_mqtt(self._Mqtt)
        PluginBase.set_ui(self._Ui)

        self._plugins = {}
        for module_name in plugins.__all__:
            module = importlib.import_module("plugins." + module_name)

            # Dynamically load plugins from the plugin folder
            for plugin_name in dir(module):
                class_ref = getattr(module, plugin_name)
                if isinstance(class_ref, type) and issubclass(class_ref, PluginBase) and class_ref is not PluginBase:  # Only load subclasses of PluginBase
                    self.load_plugin(class_ref.__name__.replace("Plugin", ""), class_ref)  # Load plugin (with name)

        # LOAD WINDOWS
        WindowBase.set_mqtt(self._Mqtt)
        WindowBase.set_ui(self._Ui)

        self._windows = {}
        for module_name in windows.__all__:
            module = importlib.import_module("windows." + module_name)

            # Dynamically load windows from the window folder that inherits from WindowBase
            for window_name in dir(module):
                class_ref = getattr(module, window_name)
                if isinstance(class_ref, type) and issubclass(class_ref, WindowBase) and class_ref is not WindowBase:  # Only load subclasses of WindowBase
                    self.load_window(class_ref.__name__.replace("Window", ""), class_ref)  # Load window (with name)

        if timestamp + 1500 >= pg.time.get_ticks():  # Minimum splashscreen 1.5s
            self._Ui.clear_info()
            self._Ui.clear()
            self._Ui.background(txt=True)
            self._display()

            while timestamp + 1500 >= pg.time.get_ticks():  # Wait until 1.5s has passed
                for event in pg.event.get():  # Event handling
                    if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                        raise KeyboardInterrupt

        # Load and enable first window by default on start
        self._log.log("Loaded windows: " + str(list(self._windows.keys())), LogLevel.INF)
        self._log.log("Loaded plugins: " + str(list(self._plugins.keys())), LogLevel.INF)
        self._log.log("Enabled plugins: " + str(list(self._plugins.keys())), LogLevel.INF)
        try:
            self.active_window_name = list(self._windows.keys())[0]  # Default to first window class
        except IndexError:  # Error handling for no windows found
            self._log.log("No windows found!", LogLevel.ERR)
            raise KeyboardInterrupt
        self._windows[self.active_window_name].start()

    def load_plugin(self, name: str, plugin: type(PluginBase)):
        self._log.log("Loading plugin: " + name, LogLevel.INF)
        self._loading_info(name.lower())
        self._plugins[name] = plugin()
        self._plugins[name].enable()  # TODO: Enable plugins via settings (enables all for now), plugin settings?

    def load_window(self, name: str, window: type(WindowBase)):
        self._log.log("Loading window: " + name, LogLevel.INF)
        self._loading_info(name.lower())
        self._windows[name] = window()

    def set_window(self, window_name: str):  # Stops current window and starts another
        self._windows[self.active_window_name].stop()  # Stop current window
        self.active_window_name = window_name  # Update to new window name
        self._windows[self.active_window_name].start()  # Start new window

    def update(self):
        self._tick(15)  # FPS
        for event in pg.event.get():  # Event handling
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                raise KeyboardInterrupt

        self._Ui.mouse_pos = pg.mouse.get_pos()

        self._Ui.clear()

        self._windows[self.active_window_name].update()  # Only update active window
        for plugin in self._plugins.values(): plugin.update()  # Update all plugins

        self._windows[self.active_window_name].draw()  # Only draw active window

        self._display()

        self._Ui.prev_mouse_pos = self._Ui.mouse_pos

    def end(self):
        self._windows[self.active_window_name].stop()
        for plugin in self._plugins.values(): plugin.disable()  # Update all plugins
        self._Mqtt.disconnect()
        Log("Miniplayer").log("Stopped", LogLevel.INF)
        self._windows.clear()

    def _loading_info(self, window_name: str):
        self._Ui.show_info("Loading " + window_name, 'LBlue', force=True)
        self._Ui.background(txt=True)
        self._display()

    def _update_mouse(self):
        self._Ui.mouse_pos = pg.mouse.get_pos()

    def _tick(self, fps: int):
        self._Clock.tick(fps)

    def _display(self):
        if self._Ui.get_info()[0]:  # If there is a message to be shown
            self._Ui.text(self._Ui.get_info()[0], 30, self._Ui.get_info()[1], midbottom=(self._Ui.Center[0], self._Ui.Height - 10))

        if self._Ui.get_info()[2] != 0 and self._Ui.get_info()[2] != 0 and self._Ui.get_info()[2] <= pg.time.get_ticks():
            self._Ui.clear_info()

        self._Ui.apply_brightness()

        pg.display.update()
