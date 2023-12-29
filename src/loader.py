from uuid import getnode as get_mac
from logger import Logging
import pygame as pg
import json

try:
    import pigpio
except ImportError:
    pigpio = None


def load_img(img: str, size: tuple[int, int], alpha=True) -> pg.surface:
    try:
        if alpha:
            return pg.Surface.convert_alpha(pg.image.load(img))
        else:
            return pg.Surface.convert(pg.image.load(img))

    except Exception or BaseException as err:
        Logging('load').handle(err, traceback=False)  # No traceback as too fast
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


class ConfigLoader(Logging):
    _config_file = '..\\config.json'
    _settings_file = '..\\settings.json'
    _default_config = {
        "DEBUG": False,
        "LOGGING": False,
        "NODERED_IP": "",
        "NODERED_PORT": 1880,
        "NODERED_USER": "",
        "MQTT_IP": "",
        "MQTT_PORT": 1883,
        "MQTT_USER": "",
        "MQTT_PASS": "",
        "MQTT_AUTO_RECONNECT": 0,
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
        super().__init__('Settings Loader')
        self.conf = {}
        self.setting = {}
        self.load_config()
        self.conf['NODERED_USER'] = str(hex(get_mac())) if not self.conf['NODERED_USER'] else self.conf['NODERED_USER']

        if self.conf['BACKLIGHT_CONTROL'] == 2 and not pigpio:
            print("\nWARNING: BACKLIGHT_CONTROL is set to Hardware ('2'), but pigpio is not present!\n"
                  "         Fallback to Software mode ('1') to prevent crash...")
            self.conf['BACKLIGHT_CONTROL'] = 1
        pg.display.init()
        if self.conf['SCREEN'] > pg.display.get_num_displays() - 1:
            print(f"\nWARNING: SCREEN is set to display {self.conf['SCREEN']} which does not exist!\n"
                  "         Fallback to screen 0 to prevent crash...")
            self.conf['SCREEN'] = 0
        self.load_settings()

    def load_config(self):
        try:
            with open(self._config_file) as config_file:  # Load config file
                self.conf = json.load(config_file)
                self.log(f"Loaded config file from \"{self._config_file}\"")
        except PermissionError:
            self.err(f"Failed to load config file from \"{self._config_file}\"", data="reason: PermissionError")
        except FileNotFoundError:
            self.err(f"Failed to load config file from \"{self._config_file}\"", data="reason: FileNotFound")
            try:
                with open(self._config_file, 'w') as config_file:  # Save default config file
                    json.dump(self._default_config, config_file, indent=2)
            except Exception or BaseException as err:
                self.handle(err)
                self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
                self.conf = self._default_config.copy()  # Load default as last resort
            except:
                self.err('Unhandled exception -> ConfigLoader.load_config()')
                self.conf = self._default_config.copy()  # Load default as last resort
        except Exception or BaseException as err:
            self.handle(err)
            self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
            self.conf = self._default_config.copy()  # Load default as last resort
        except:
            self.err('Unhandled exception -> ConfigLoader.load_config()')
            self.conf = self._default_config.copy()  # Load default as last resort

    def load_settings(self):
        try:
            with open('settings.json') as settings_file:  # Load settings file
                self.setting = json.load(settings_file)
                self.log(f"Loaded settings file from \"{self._settings_file}\"")
        except PermissionError:
            self.err(f"Failed to load settings file from \"{self._settings_file}\"", data="reason: PermissionError")
        except FileNotFoundError:
            self.err(f"Failed to load settings file from \"{self._settings_file}\"", data="reason: FileNotFound")
            self.setting = self._default_settings.copy()  # Load default as last resort
            self.save_settings()
        except Exception or BaseException as err:
            self.handle(err)
            self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
            self.setting = self._default_settings.copy()  # Load default as last resort
        except:
            self.err('Unhandled exception -> SETTINGS.load() 2')
            self.setting = self._default_settings.copy()  # Load default as last resort

    def save_settings(self):
        try:
            with open(self._settings_file, 'w') as settings_file:  # Save default settings file
                json.dump(self.setting, settings_file, indent=2)
        except Exception or BaseException as err:
            self.handle(err)
            self.err(f"Failed to create \"{self._config_file}\"", data="reason: Unknown")
            self.setting = self._default_settings.copy()  # Load default as last resort
        except:
            self.err('Unhandled exception -> SETTINGS.load() 2')
            self.setting = self._default_settings.copy()  # Load default as last resort
