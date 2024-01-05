from uuid import getnode as get_mac
from lib.logger import Logging
import webbrowser
import pygame as pg
import json

try:
    import pigpio
except ImportError:
    pigpio = None


class ConfigLoader(Logging):
    _config_file = 'config.json'
    _settings_file = 'settings.json'
    _default_config = {
        "LOGGING": 3,
        "NODERED_IP": "",
        "NODERED_PORT": 1880,
        "NODERED_USER": "",
        "MQTT_IP": "",
        "MQTT_PORT": 1883,
        "MQTT_USER": "",
        "MQTT_PASS": "",
        "MQTT_AUTO_RECONNECT": 900000,
        "TOUCHSCREEN": False,
        "FULLSCREEN": False,
        "BACKLIGHT_CONTROL": 0,
        "MIN_BRIGHTNESS": 0,
        "BRIGHTNESS_OFFSET": 0,
        "BACKLIGHT_PIN": 0,
        "FPS": 15,
        "RESOLUTION": [1280, 720],
        "SCREEN": 0,
        "SCREENSAVER_DELAY": 0}
    _default_settings = {
        "Timestamps": True,
        "Device Info": True,
        "Screensaver": True,
        "Screensaver Info": True,
        "Playlist Order": []}

    def __init__(self):
        super().__init__('Config Loader')
        self._conf = {}
        self._setting = {}
        self.load_config()  # Load config

        Logging.set_log_level(self._conf['LOGGING'])
        self.Node_red_ip = self._conf['NODERED_IP']
        self.Node_red_port = self._conf['NODERED_PORT']
        self.Node_red_user = str(hex(get_mac())) if not self._conf['NODERED_USER'] else self._conf['NODERED_USER']
        self.Mqtt_ip = self._conf['MQTT_IP']
        self.Mqtt_port = self._conf['MQTT_PORT']
        self.Mqtt_user = self._conf['MQTT_USER']
        self.Mqtt_pass = self._conf['MQTT_PASS']
        self.Mqtt_reconnect = self._conf['MQTT_AUTO_RECONNECT']
        self.Touchscreen = self._conf['TOUCHSCREEN']
        self.Fullscreen = self._conf['FULLSCREEN']
        self.Backlight = self._conf['BACKLIGHT_MODE']
        self.Min_brightness = self._conf['MIN_BRIGHTNESS']
        self.Brightness_offset = self._conf['BRIGHTNESS_OFFSET']
        self.Backlight_pin = self._conf['BACKLIGHT_PIN']
        self.Fps = self._conf['FPS']
        self.Resolution = self._conf['RESOLUTION']
        self.Screen = self._conf['SCREEN']
        self.Screensaver_delay = self._conf['SCREENSAVER_DELAY']

        if self.Backlight == 2 and not pigpio:
            self.warn("BACKLIGHT_MODE is set to Hardware (2), but pigpio is not present!\n"
                      "Falling back to Software mode (1) to prevent crash")
            self.Backlight = 1
        pg.display.init()
        if self.Screen > pg.display.get_num_displays() - 1:
            self.warn(f"SCREEN is set to display \"{self.Screen}\", which does not exist!\n"
                      f"Fallback to screen 0 to prevent crash")
            self.Screen = 0

        self.load_settings()

    def _load_default_settings(self):
        self.setting = self._default_settings.copy()
        self.debug("Loaded default settings")

    def load_config(self):
        try:
            self.debug(f"Loading config from \"{self._config_file}\"")
            with open(self._config_file) as config_file:  # Load config file
                self._conf = json.load(config_file)
                self.info(f"Loaded config from \"{self._config_file}\"")
        except PermissionError:
            self.err(f"Failed to load config from \"{self._config_file}\"", data="reason: PermissionError")
        except FileNotFoundError:
            self.err(f"Failed to load config from \"{self._config_file}\"", data="reason: FileNotFound")
            try:
                self.debug(f"Creating new config at \"{self._config_file}\"")
                with open(self._config_file, 'w') as config_file:  # Save default config file
                    json.dump(self._default_config, config_file, indent=2)
                    self.info(f"Created new config at \"{self._config_file}\"")
                    self.crit(f"Please edit \"{self._config_file}\" and restart the program")
                    webbrowser.open(self._config_file)
                    Logging.close_log()
                    quit()

            except Exception or BaseException as err:
                self.handle(err)
                self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
                self._conf = self._default_config.copy()  # Load default as last resort

        except Exception or BaseException as err:
            self.handle(err)
            self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
            self._conf = self._default_config.copy()  # Load default as last resort

    def load_settings(self):
        try:
            self.debug(f"Loading settings from \"{self._config_file}\"")
            with open('settings.json') as settings_file:  # Load settings file
                self._setting = json.load(settings_file)
                self.info(f"Loaded settings from \"{self._settings_file}\"")
        except PermissionError:
            self.err(f"Failed to load settings from \"{self._settings_file}\"", data="reason: PermissionError")
            self._load_default_settings()  # Load default as last resort
        except FileNotFoundError:
            self.warn(f"Failed to load settings from \"{self._settings_file}\"", data="reason: FileNotFound")
            self._load_default_settings()  # Load default as last resort
            self.save_settings()
        except Exception or BaseException as err:
            self.handle(err, data=f"Failed to create \"{self._config_file}\"")
            self._load_default_settings()  # Load default as last resort
        except:
            self.err('Unhandled exception -> SETTINGS.load() 2')
            self._load_default_settings()  # Load default as last resort

    def save_settings(self):
        try:
            self.debug(f"Saving settings to \"{self._settings_file}\"")
            with open(self._settings_file, 'w') as settings_file:  # Save default settings file
                json.dump(self.setting, settings_file, indent=2)
                self.info(f"Saved settings to \"{self._settings_file}\"")
        except Exception or BaseException as err:
            self.handle(err)
            self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
            self._load_default_settings()  # Load default as last resort
        except:
            self.err('Unhandled exception -> SETTINGS.load() 2')
            self._load_default_settings()  # Load default as last resort


class ImgLoader(Logging):
    _assets_folder = "assets\\"

    def __init__(self):
        super().__init__('Img Loader')
        pg.font.init()
        self.img = {}  # ASSET DIRECTORIES / PATHS

    def load(self, img: str, size=(32, 32), keep_alpha=True) -> pg.surface:
        try:
            if keep_alpha:
                return pg.Surface.convert_alpha(pg.image.load(img))
            else:
                return pg.Surface.convert(pg.image.load(img))

        except Exception or BaseException as err:
            self.handle(err, trace=False)  # No traceback as too fast
            surf = pg.surface.Surface(size)
            surf.fill((150, 150, 150))
            rect = surf.get_rect()
            pg.draw.line(surf, (255, 0, 0), rect.topleft, rect.bottomright, 2)
            pg.draw.line(surf, (255, 0, 0), rect.bottomleft, rect.topright, 2)

            try:
                temp = pg.font.Font('assets/thinfont.ttf', 15).render(img, False, (255, 255, 255))
            except Exception or BaseException:
                temp = pg.font.Font(None, 15).render(img, False, (255, 255, 255))

            surf.blit(temp, temp.get_rect(center=rect.center))
            return surf
