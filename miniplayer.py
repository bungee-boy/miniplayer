from uuid import getnode as get_mac  # Used to set MQTT username as MAC address

import importlib  # Used to import windows dynamically
import windows  # Window subdirectory
from window import *

class Miniplayer:
    def __init__(self):
        self._log = Log("Miniplayer")
        self._log.log("Start", LogLevel.INF)

        self._Clock = pg.time.Clock()

        self._Mqtt = MqttClient(str(hex(get_mac())) + "V3", "homeassistant.local", "mosquitto", "bungeeboy12")
        self._Ui = Ui((1280, 720), display=1)

        timestamp = pg.time.get_ticks()

        self._loading_info("mqtt")
        self._Mqtt.connect()

        WindowBase.set_mqtt(self._Mqtt)
        WindowBase.set_ui(self._Ui)

        self._windows = {}
        for module_name in windows.__all__:
            module = importlib.import_module(f"windows.{module_name}")

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
        self.active_window_name = list(self._windows.keys())[0]  # Default to first window class
        self._windows[self.active_window_name].start()

    def load_window(self, name: str, window: type(WindowBase)):
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

        self._windows[self.active_window_name].update()
        self._windows[self.active_window_name].draw()

        self._display()

        self._Ui.prev_mouse_pos = self._Ui.mouse_pos

    def end(self):
        self._windows[self.active_window_name].stop()
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

        pg.display.update()
