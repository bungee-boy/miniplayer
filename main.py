import io
import json
import os
import shutil
import threading
from time import strftime
from datetime import datetime
from math import floor
from sys import argv as launch_opt
from timeit import default_timer as timer
from uuid import getnode as get_mac
import paho.mqtt.client as mqtt_client
import pygame as pg
import requests

try:
    import pigpio
except ImportError:
    pigpio = False

DEBUG = False
LOGGING = False
Last_err = None


def handle(err: Exception or BaseException, save=True, repeat=False, traceback=True):
    global Last_err
    if type(err) is KeyboardInterrupt:
        return
    msg = "{0}: {1}".format(str(type(err)).replace("<class '", '').replace("'>", ''), err)
    if not repeat and msg == Last_err:
        return
    if DEBUG and traceback:  # Show traceback if debug is on
        import traceback
        traceback.print_exc()
    print(msg)
    Last_err = msg
    if save:
        try:
            if DEBUG or LOGGING:
                with open('miniplayer_err.log', 'a') as file:
                    file.write(msg + '\n')
        except:
            print('Failed to log handled error -> unknown')


try:
    with (open('user_settings.json') as launch_usr):
        launch_usr = json.load(launch_usr)  # Load settings file
        DEBUG = launch_usr['DEBUG']  # Enable debugging features
        LOGGING = launch_usr['LOGGING']  # Enable logging features
        NODERED_IP = launch_usr['NODERED_IP']  # Node-RED IP address (REQUIRED)
        NODERED_PORT = launch_usr['NODERED_PORT']  # Node-RED Port (default: 1880 )
        NODERED_USER = str(hex(get_mac())) if not launch_usr['NODERED_USER']\
            else launch_usr['NODERED_USER']  # Node-RED username (default: '' = MAC_ADDRESS)
        MQTT_IP = launch_usr['MQTT_IP']  # MQTT IP address (REQUIRED)
        MQTT_PORT = launch_usr['MQTT_PORT']  # MQTT Port (default: 1883 )
        MQTT_USER = launch_usr['MQTT_USER']  # MQTT username (if required) (default: '' )
        MQTT_PASS = launch_usr['MQTT_PASS']  # MQTT password (if required) (default: '' )
        MQTT_AUTO_RECONNECT = launch_usr['MQTT_AUTO_RECONNECT']  # Reconnect if no traffic for x ms (default: 900000 )
        TOUCHSCREEN = launch_usr['TOUCHSCREEN']  # Enable touchscreen mode (hides cursor, no clicking ect)
        FULLSCREEN = launch_usr['FULLSCREEN']  # Enable fullscreen mode (takes over entire screen)
        BACKLIGHT_CONTROL = launch_usr['BACKLIGHT']  # Type of backlight control (0=Off, 1=Software, 2=GPIO)
        MINIMUM_BRIGHTNESS = launch_usr['MIN_BRIGHTNESS']  # Minimum brightness 0 - 100%
        BACKLIGHT_PIN = launch_usr['BACKLIGHT_PIN']  # Pin (BCIM) to use if BACKLIGHT_CONTROL = 2
        FPS = launch_usr['FPS']  # Frames per second (default: 30 )
        RESOLUTION = launch_usr['RESOLUTION']  # Width and height of the display or window (default: 1280, 720 )
        SCREEN = launch_usr['SCREEN']  # Screen number (for multiple displays)
        SCREENSAVER_DELAY = launch_usr['SCREENSAVER']  # Active if no movement after x ms and enabled (default: 120000 )

        if BACKLIGHT_CONTROL == 2 and not pigpio:
            print("\nWARNING: BACKLIGHT_CONTROL is set to Hardware ('2'), but pigpio is not present!\n"
                  "         Fallback to Software mode ('1') to prevent crash...")
            BACKLIGHT_CONTROL = 1
        pg.display.init()
        if SCREEN > pg.display.get_num_displays() - 1:
            print(f"\nWARNING: SCREEN is set to display {SCREEN} which does not exist!\n"
                  "         Fallback to screen 0 to prevent crash...")
            SCREEN = 0
except FileNotFoundError or KeyError:
    print("\nWARNING: 'user_settings.json' failed, attempting to fix.\n")
    try:
        with open('user_settings.json', 'w') as launch_usr:
            launch_usr.seek(0)
            json.dump({
                "DEBUG": False,
                "LOGGING": False,
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
                "BACKLIGHT": 0,
                "MIN_BRIGHTNESS": 5,
                "BACKLIGHT_PIN": 0,
                "FPS": 30,
                "RESOLUTION": [1280, 720],
                "SCREEN": 0,
                "SCREENSAVER": 120000}, launch_usr, indent=2)
        print("'user_settings.json' fixed successfully, please edit to correct settings!")
        try:
            import webbrowser
            webbrowser.open('user_settings.json')
        finally:
            quit()
    except Exception or BaseException as error:
        handle(error)
        quit()
    except:
        print('Unhandled exception -> creating user_settings.json')
        quit()
except Exception or BaseException as error:
    handle(error)
    quit()
except:
    print('Unhandled exception -> reading user_settings.json')
    quit()

# UNHANDLED INIT
if len(launch_opt) >= 1:  # LAUNCH OPTIONS
    if '--debug' in launch_opt:
        DEBUG = bool(int(launch_opt[launch_opt.index('--debug') + 1]))
        print('Forced DEBUG ' + 'On' if DEBUG else 'Off')
    if '--logging' in launch_opt:
        LOGGING = bool(int(launch_opt[launch_opt.index('--logging') + 1]))
        print(f'Forced LOGGING {"On" if LOGGING else "Off"}')

WIDTH, HEIGHT = RESOLUTION
CENTER = WIDTH // 2, HEIGHT // 2
Button_cooldown = 0
Button_cooldown_length = 500 if TOUCHSCREEN else 100
Mouse_pos = -1, -1
Prev_mouse_pos = -2, -2
Loaded_fonts = {}
Colour = {'key': (1, 1, 1), 'black': (0, 0, 0), 'white': (255, 255, 255), 'grey': (155, 155, 155),
          'd grey': (80, 80, 80), 'red': (251, 105, 98), 'yellow': (252, 252, 153), 'l green': (121, 222, 121),
          'green': (18, 115, 53), 'amber': (200, 140, 0), 'l blue': (3, 140, 252)}
Info = '', Colour['white'], 2000  # txt, colour, ms

Loading_ani = None
Menu = None

Display = pg.display.set_mode(RESOLUTION, flags=pg.FULLSCREEN if FULLSCREEN else 0, display=SCREEN)
Clock = pg.time.Clock()
pg.display.set_caption('Miniplayer v2')
pg.init()


def load(img: str, size: tuple[int, int], alpha=True) -> pg.surface:
    try:
        if alpha:
            return pg.Surface.convert_alpha(pg.image.load(img))
        else:
            return pg.Surface.convert(pg.image.load(img))

    except Exception or BaseException as err:
        handle(err, traceback=False)  # No traceback as too fast
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


try:
    pg.font.Font('assets/thinfont.ttf', 15)
except Exception or BaseException as error:
    handle(error, traceback=False)
try:
    pg.font.Font('assets/boldfont.ttf', 15)
except Exception or BaseException as error:
    handle(error, traceback=False)

Img = {  # ASSET DIRECTORIES / PATHS
    'bg': load('assets/bg.jpg', (1280, 720), alpha=False),
    'icon': load('assets/icon.ico', (32, 32), alpha=False),
    'menu': {
        'menu': load('assets/menu.png', (50, 50)),
        'settings': load('assets/settings.png', (50, 50)),
        'cross': load('assets/cross.png', (50, 50))},
    'weather': {
        'storm': pg.transform.smoothscale(load('assets/weather/storm.png', (100, 100)), (300, 300)),
        'storm_2': pg.transform.smoothscale(load('assets/weather/storm_2.png', (100, 100)), (300, 300)),
        'storm_3': pg.transform.smoothscale(load('assets/weather/storm_3.png', (100, 100)), (300, 300)),
        'rain': pg.transform.smoothscale(load('assets/weather/rain.png', (100, 100)), (300, 300)),
        'rain_2': pg.transform.smoothscale(load('assets/weather/rain_2.png', (100, 100)), (300, 300)),
        'rain_3': pg.transform.smoothscale(load('assets/weather/rain_3.png', (100, 100)), (300, 300)),
        'rain_4': pg.transform.smoothscale(load('assets/weather/rain_4.png', (100, 100)), (300, 300)),
        'rain_5': pg.transform.smoothscale(load('assets/weather/rain_5.png', (100, 100)), (300, 300)),
        'hail': pg.transform.smoothscale(load('assets/weather/hail.png', (100, 100)), (300, 300)),
        'snow': pg.transform.smoothscale(load('assets/weather/snow.png', (100, 100)), (300, 300)),
        'snow_2': pg.transform.smoothscale(load('assets/weather/snow_2.png', (100, 100)), (300, 300)),
        'snow_3': pg.transform.smoothscale(load('assets/weather/snow_3.png', (100, 100)), (300, 300)),
        'mist': pg.transform.smoothscale(load('assets/weather/mist.png', (100, 100)), (300, 300)),
        'dust': pg.transform.smoothscale(load('assets/weather/dust.png', (100, 100)), (300, 300)),
        'haze': pg.transform.smoothscale(load('assets/weather/haze.png', (100, 100)), (300, 300)),
        'fog': pg.transform.smoothscale(load('assets/weather/fog.png', (100, 100)), (300, 300)),
        'wind': pg.transform.smoothscale(load('assets/weather/wind.png', (100, 100)), (300, 300)),
        'tornado': pg.transform.smoothscale(load('assets/weather/tornado.png', (100, 100)), (300, 300)),
        'sun': pg.transform.smoothscale(load('assets/weather/sun.png', (100, 100)), (300, 300)),
        'cloud_2': pg.transform.smoothscale(load('assets/weather/cloud_2.png', (100, 100)), (300, 300)),
        'cloud': pg.transform.smoothscale(load('assets/weather/cloud.png', (100, 100)), (300, 300))},
    'spotify': {
        'logo': load('assets/spotify/logo.png', (295, 89)),
        'pause': (load('assets/spotify/pause_0.png', (50, 50)),
                  load('assets/spotify/pause_1.png', (50, 50))),
        'play': (load('assets/spotify/play_0.png', (50, 50)),
                 load('assets/spotify/play_1.png', (50, 50))),
        'shuffle': (load('assets/spotify/shuffle_1.png', (50, 50)),
                    load('assets/spotify/shuffle_1.png', (50, 50))),
        'playlist': load('assets/spotify/playlist_1.png', (50, 50)),
        'skip': (load('assets/spotify/skip_0.png', (50, 50)),
                 load('assets/spotify/skip_1.png', (50, 50))),
        'mute': load('assets/spotify/mute.png', (50, 50)),
        'vol 0': load('assets/spotify/vol_0.png', (50, 50)),
        'vol 50': load('assets/spotify/vol_50.png', (50, 50)),
        'vol 100': load('assets/spotify/vol_100.png', (50, 50)),
        'vol -': (load('assets/spotify/vol_-_0.png', (50, 50)),
                  load('assets/spotify/vol_-_1.png', (50, 50))),
        'vol +': (load('assets/spotify/vol_+_0.png', (50, 50)),
                  load('assets/spotify/vol_+_1.png', (50, 50)))}}

Bg = pg.transform.scale(Img['bg'], (WIDTH, HEIGHT))
Bg.set_alpha(130)
pg.display.set_icon(Img['icon'])


# CLASSES
class Window:
    def __init__(self, name: str):
        self.name = name
        self.active = False
        self.message = {}
        self.timestamp = '--:--'
        self._timestamp_color = Colour['yellow']

    def _load_default(self):
        pass

    def log(self, msg, cat=None):
        try:
            msg = f"[{datetime.now().strftime('%x %X')}][{cat if cat else 'LOG'}][{self.name}] {msg}."
            print(msg)
            if LOGGING:
                with open('miniplayer.log', 'a') as file:
                    file.write(msg + '\n')
        except (Exception, BaseException) as err:
            handle(err, save=False)  # Do not save as error with log
        except:
            print('Failed log msg -> unknown')

    def err(self, msg, cat=None, data=None):
        try:
            msg = '[{0}][{1}][{2}] {3}!{4}'.format(datetime.now().strftime('%x %X'), cat if cat else 'ERR', self.name,
                                                   msg, f' ({data})' if data else '')
            print(msg)
            with open('miniplayer_err.log', 'a') as file:
                file.write(msg + '\n')
            if LOGGING:
                with open('miniplayer.log', 'a') as file:
                    file.write(msg + '\n')
        except (Exception, BaseException) as err:
            handle(err, save=False)  # Do not save as error with log
        except:
            print('Failed log error -> unknown')

    def receive(self, client, data, message: mqtt_client.MQTTMessage):
        pass

    def start(self):
        pass

    def stop(self):
        Menu.allow_screensaver = True
        self.log('Allowed screensaver')

    def draw(self, surf=Display):
        surf.fill(Colour['black'])
        surf.blit(*render_text(self.name, 20, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(*render_text(self.timestamp, 15, self._timestamp_color, bottomleft=(5, HEIGHT - 3)))

    def update(self):
        pass


class LoadingAni(Window):
    def __init__(self):
        super().__init__('Loading Ani')
        self._running = False
        self._event = threading.Event()
        self.thread = threading.Thread(name='loading ani', target=self.ani)
        self.msg = ''
        self.msg_colour = None

    def ani(self, pos=CENTER, colour=Colour['white'], size=(125, 125), dot_size=25, speed=18):
        surf = Display
        self._running = True
        self._event = threading.Event()

        dots = []
        for dot in range(0, 8):
            dots.append(pg.surface.Surface((dot_size, dot_size)))
            dots[dot].fill(Colour['key'])
            dots[dot].set_colorkey(Colour['key'])
            pg.draw.circle(dots[dot], colour, (dot_size // 2, dot_size // 2), dot_size // 2)
            dots[dot].set_alpha(255 // 8 * dot)
            dots[dot] = dots[dot], dots[dot].get_rect()
        dots[0][1].center = pos[0], pos[1] - size[1] // 2
        dots[1][1].center = pos[0] + size[0] // 3, pos[1] - size[1] // 3
        dots[2][1].center = pos[0] + size[0] // 2, pos[1]
        dots[3][1].center = pos[0] + size[0] // 3, pos[1] + size[1] // 3
        dots[4][1].center = pos[0], pos[1] + size[1] // 2
        dots[5][1].center = pos[0] - size[0] // 3, pos[1] + size[1] // 3
        dots[6][1].center = pos[0] - size[0] // 2, pos[1]
        dots[7][1].center = pos[0] - size[0] // 3, pos[1] - size[1] // 3

        try:
            while not self._event.is_set():
                if Menu and Menu.allow_screensaver:
                    Menu.allow_screensaver = False

                Clock.tick(FPS)

                for event in pg.event.get():
                    if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                        raise KeyboardInterrupt

                for dot in dots:  # Loop alpha for each dot to create animation
                    alpha = dot[0].get_alpha()
                    if alpha - speed < 0 and alpha != 0:
                        alpha = 0
                    elif alpha - speed <= 0:
                        alpha = 255
                    else:
                        alpha -= speed
                    dot[0].set_alpha(alpha)

                surf.fill(Colour['black'])
                surf.blit(Bg, (0, 0))
                surf.blit(dots[0][0], dots[0][1].topleft)
                surf.blit(dots[1][0], dots[1][1].topleft)
                surf.blit(dots[2][0], dots[2][1].topleft)
                surf.blit(dots[3][0], dots[3][1].topleft)
                surf.blit(dots[4][0], dots[4][1].topleft)
                surf.blit(dots[5][0], dots[5][1].topleft)
                surf.blit(dots[6][0], dots[6][1].topleft)
                surf.blit(dots[7][0], dots[7][1].topleft)
                if self.msg:
                    self.msg_colour = Colour['white'] if not self.msg_colour else self.msg_colour
                    surf.blit(*render_text(self.msg, 30, colour=self.msg_colour, bold=True,
                                           midtop=(pos[0], pos[1] + size[1])))
                pg.display.update()

            self.thread = threading.Thread(target=self.ani)
            self._event = threading.Event()
            self._running = False
            return

        except Exception or BaseException as err:
            handle(err)
            self._running = False
            return

        except:
            self.err('Animation stopped -> unknown')
            self._running = False
            return

    def start(self, msg=None, msg_colour=None, **kwargs):
        self.msg = msg
        self.msg_colour = msg_colour
        if not self.thread.is_alive() and not self._running:
            self.thread = threading.Thread(name='loading ani', target=self.ani, kwargs=kwargs)
            self.thread.start()
            self.log('Started')
        else:
            self.log('Prevented multiple threads from starting', cat='WRN')

    def stop(self):
        self._event.set()
        if self.thread.is_alive():
            self.thread.join()
        self.msg = ''
        self.msg_colour = None
        self.thread = threading.Thread(name='loading ani', target=self.ani)
        self._running = False
        self.log('Stopped')


class BACKLIGHT(Window):
    _mqtt_request = '/miniplayer/backlight/request'
    _mqtt_response = '/miniplayer/backlight'
    pin = BACKLIGHT_PIN
    freq = 500

    def __init__(self):
        super().__init__('Backlight')
        if BACKLIGHT_CONTROL == 2 and pigpio:
            self._pi = pigpio.pi()
            self._pi.set_mode(self.pin, pigpio.OUTPUT)
        self.software_dim = pg.surface.Surface((WIDTH, HEIGHT))
        self.brightness = 0
        self.state = False
        Mqtt.subscribe(self._mqtt_response, self.receive, retain=True)
        self.log(f"Running in mode {BACKLIGHT_CONTROL}")
        self.set(100)
        if BACKLIGHT_CONTROL:  # If enabled, request from Node-Red
            Mqtt.send(self._mqtt_request, True)

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                msg = json.loads(message.payload.decode('utf-8'))
                if msg['brightness'] != self.brightness:
                    self.set(msg['brightness'])
            except:
                self.err('MQTT receive error')
                self.set(100)

    def set(self, brightness: int):
        self.brightness = 100 if brightness > 100 else (0 if brightness < 0 else brightness)  # Constrain to 0-100
        if BACKLIGHT_CONTROL == 2 and pigpio:
            self._pi.hardware_PWM(self.pin, self.freq, self.brightness * 10000)
        elif BACKLIGHT_CONTROL == 1:  # Software dimming
            self.brightness = MINIMUM_BRIGHTNESS if self.brightness < MINIMUM_BRIGHTNESS else self.brightness  # Limit
            self.software_dim.set_alpha(255 - round(self.brightness / 100 * 255))
        self.log(f'Set brightness to {self.brightness}')

    def stop(self):
        self.set(0)
        if BACKLIGHT_CONTROL == 2 and pigpio:
            self._pi.stop()
        self.log('Backlight stopped')


class MENU(Window):
    screensaver = False
    allow_screensaver = True
    allow_controls = True

    def __init__(self):
        super().__init__('Menu')
        self.windows = []
        self._retained_windows = []
        self.right = Img['menu']['menu']
        self.right = self.right, self.right.get_rect(midright=(WIDTH - 20, 40))
        self.left = pg.transform.flip(self.right[0], True, False)
        self.left = self.left, self.left.get_rect(midleft=(20, 40))
        self.settings = Img['menu']['settings']
        self.settings = self.settings, self.settings.get_rect(midright=(WIDTH - 80, 40))
        self.cross = Img['menu']['cross']
        self._screensaver_timer = 0

    def start_retained(self):
        if self._retained_windows:
            self.log('Starting windows')
            for window in self._retained_windows:
                window.start()
                self._retained_windows.remove(window)

    def stop(self, retain=False):
        self.log('Stopping windows')
        if retain:
            for window in self.windows:
                if window.active:
                    window.stop()
                    self._retained_windows.append(window)
        else:
            for window in self.windows:
                if window.active:
                    window.stop()

    def move_left(self):
        global Current_window
        Current_window.stop()
        index = self.windows.index(Current_window)
        if index > 0:
            Current_window = self.windows[index - 1]
        Current_window.start()

    def move_right(self):
        global Current_window
        Current_window.stop()
        index = self.windows.index(Current_window)
        if index < len(self.windows) - 1:
            Current_window = self.windows[index + 1]
        Current_window.start()

    def draw(self, surf=Display):
        if self.allow_controls:
            if self.windows.index(Current_window) > 0:
                surf.blit(*self.left)
            if self.windows.index(Current_window) < len(self.windows) - 1:
                surf.blit(*self.right)
                surf.blit(*self.settings)
            else:
                surf.blit(self.settings[0], self.right[1])

    def update(self):
        global Button_cooldown
        if Mouse_pos != Prev_mouse_pos or not self.allow_screensaver or not Settings.value['Screensaver']:
            self.screensaver = False
            self._screensaver_timer = pg.time.get_ticks() + SCREENSAVER_DELAY
        if not self.screensaver and pg.time.get_ticks() >= self._screensaver_timer and \
                self.allow_screensaver and Settings.value['Screensaver']:
            self.screensaver = True
            self.log('Started screensaver')
        elif self.screensaver and pg.time.get_ticks() < self._screensaver_timer:
            self.screensaver = False
            self.log('Stopped screensaver')

        # Page navigation
        if (not TOUCHSCREEN and not pg.mouse.get_pressed()[0] or
                TOUCHSCREEN and Mouse_pos == Prev_mouse_pos) or Button_cooldown:
            return
        settings = self.settings[1] if self.windows.index(Current_window) < len(self.windows) - 1 else self.right[1]
        if settings.collidepoint(Mouse_pos):  # Settings
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            Settings.active = True
            self.allow_screensaver = False
        elif self.left[1].collidepoint(Mouse_pos):
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.move_left()
        elif self.right[1].collidepoint(Mouse_pos):
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.move_right()


class SETTINGS(Window):
    def __init__(self):
        super().__init__('Settings')
        self.shadow = pg.surface.Surface((WIDTH, HEIGHT))
        self.shadow.set_alpha(160)
        self.value = {}
        self.load()

    def load(self):
        try:
            with open('settings.json') as file:
                self.value = json.load(file)
                self.log('Successfully loaded settings from file')

        except FileNotFoundError:
            self.err("Failed to load settings -> 'settings.json' not found")
            try:
                with open('settings.json', 'w') as file:
                    json.dump({
                        "Timestamps": True,
                        "Device Info": True,
                        "Screensaver": True,
                        "Screensaver Info": True,
                        "Playlist Order": []}, file, indent=2)
            except Exception or BaseException as err:
                handle(err)
                self.err('Failed to create settings file, using defaults')
                self.value = {
                    "Timestamps": True,
                    "Device Info": True,
                    "Screensaver": True,
                    "Screensaver Info": True,
                    "Playlist Order": []}
            except:
                self.err('Unhandled exception -> SETTINGS.load() 2')
                self.value = {
                    "Timestamps": True,
                    "Device Info": True,
                    "Screensaver": True,
                    "Screensaver Info": True,
                    "Playlist Order": []}
        except Exception or BaseException as err:
            handle(err)
        except:
            self.err('Unhandled exception -> SETTINGS.load()')

    def save(self):
        try:
            with open('settings.json', 'w') as file:
                file.seek(0)
                json.dump(self.value, file, indent=2)
                file.truncate()
                self.log('Successfully saved settings to file')
        except Exception or BaseException as err:
            handle(err)
        except:
            self.err('Unhandled exception -> SETTINGS.save()')

    def update_draw(self, surf=Display):
        global Button_cooldown

        surf.blit(self.shadow, (0, 0))
        surf.blit(*render_text('Settings', 50, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(Menu.settings[0], Menu.right[1])

        screensaver = render_button(self.value['Screensaver'], midleft=(Menu.left[1].centerx + 50, 150))
        device_info = render_button(self.value['Device Info'], midleft=(screensaver.left, screensaver.centery + 100))
        playlists = render_button(Colour['grey'], midleft=(device_info.left, device_info.centery + 100))
        reconnect = render_button(Colour['amber'], midleft=(playlists.left, playlists.centery + 100))
        close = render_button(Colour['red'], midleft=(reconnect.left, reconnect.centery + 100))

        temp = 30
        # SCREENSAVER
        surf.blit(*render_text('Screensaver', 35, bold=True, midleft=(screensaver.right + temp, screensaver.centery)))
        # DEVICE INFO
        surf.blit(*render_text('Device Info', 35, bold=True, midleft=(device_info.right + temp, device_info.centery)))
        # RELOAD PLAYLISTS
        surf.blit(*render_text('Reload playlists', 35, bold=True, midleft=(playlists.right + temp, playlists.centery)))
        # RECONNECT
        surf.blit(*render_text('Reconnect', 35, bold=True, midleft=(reconnect.right + temp, reconnect.centery)))
        # CLOSE
        surf.blit(*render_text('Close', 35, bold=True, midleft=(close.right + temp, close.centery)))
        # MQTT INFO
        surf.blit(*render_text(f'Connection: {MQTT_IP}   Username: {Mqtt.mac_address}', 30, bold=True,
                               midbottom=(CENTER[0], HEIGHT - 10)))

        if (not TOUCHSCREEN and not pg.mouse.get_pressed()[0] or
                TOUCHSCREEN and Mouse_pos == Prev_mouse_pos) or Button_cooldown:
            return
        elif Menu.right[1].collidepoint(Mouse_pos):
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False
            Menu.allow_screensaver = True
            self.save()
        elif screensaver.collidepoint(Mouse_pos):  # Screensaver
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.value['Screensaver'] = False if self.value['Screensaver'] else True
        elif device_info.collidepoint(Mouse_pos):  # Device info
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.value['Device Info'] = False if self.value['Device Info'] else True
        elif playlists.collidepoint(Mouse_pos):  # Reload
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False  # Close settings automatically
            if Spotify.reload_playlists():
                set_info('Reloaded playlists')
            else:
                set_info('Playlist reload failed!', Colour['red'])
        elif reconnect.collidepoint(Mouse_pos):  # Reconnect
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False  # Close settings automatically
            Mqtt.reconnect()
        elif close.collidepoint(Mouse_pos):  # Close
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            raise KeyboardInterrupt('Close button pressed')


class MQTT(Window):
    mac_address = NODERED_USER

    def __init__(self):
        super().__init__('MQTT')
        self.connected = False
        self.retained = {}  # {'topic': response()}
        self.subscribed = {}
        self._last_msg_time = pg.time.get_ticks() + MQTT_AUTO_RECONNECT
        self._mqtt = mqtt_client.Client(self.mac_address)
        self._mqtt.will_set(f'/miniplayer/connection/{self.mac_address}', payload='disconnected')
        self._mqtt.on_message = self._global_response
        self._mqtt.loop_start()
        self.reconnect_pending = not self.connect()  # If not connected on boot, set to start reconnect.

    def _set_reconnect(self, client=None, data=None, message=None):
        if client or data or message:
            pass
        self.reconnect_pending = True

    def _global_response(self, client, data, message):
        self._last_msg_time = pg.time.get_ticks() + MQTT_AUTO_RECONNECT  # Update last msg time
        for topic in self.subscribed:
            if topic == message.topic:  # Find corresponding topic
                self.subscribed[topic](client, data, message)  # Run appropriate response function on data
                break

    def connect(self, ani=False):
        if not self.connected or not self._mqtt.is_connected():
            self.connected = False
            self._mqtt.loop_stop()
            self._mqtt.reinitialise(self.mac_address)
            if MQTT_USER and MQTT_PASS:  # If username and password
                self._mqtt.username_pw_set(MQTT_USER, MQTT_PASS)
                self.log(f'Set credentials: {MQTT_USER}, {MQTT_PASS}')
            self._mqtt.will_set(f'/miniplayer/connection/{self.mac_address}', payload='disconnected')
            self._mqtt.on_message = self._global_response
            self._mqtt.loop_start()
            self.log(f"Connecting to '{MQTT_IP}' with username '{self.mac_address}'")
            if ani:
                Loading_ani.start(msg='Connecting...', msg_colour=Colour['amber'])
            else:
                Loading_ani.msg, Loading_ani.msg_colour = 'Connecting...', Colour['amber']
            temp = timer()
            try:
                self._mqtt.connect(MQTT_IP, port=MQTT_PORT)  # Start connection
                while not self._mqtt.is_connected():  # Wait for MQTT to connect
                    pg.time.wait(250)
                    if round(timer() - temp, 2) >= 10:  # Timeout after 10s
                        self.err(f'Connection to {MQTT_IP} failed: Timed out', data=f'username={self.mac_address}')
                        Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                        pg.time.wait(1500)
                        if ani:
                            Loading_ani.stop()
                        return False

            except Exception as err:  # If failure to connect
                self.err(f'Connection to {MQTT_IP} failed: {err}', data=f'username={self.mac_address}')
                Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                pg.time.wait(1500)
                if ani:
                    Loading_ani.stop()
                return False

            self.send(f'/miniplayer/connection/{self.mac_address}', 'connected')  # If connected
            self.connected = True
            self._last_msg_time = pg.time.get_ticks() + MQTT_AUTO_RECONNECT
            self._mqtt.on_disconnect = self._set_reconnect
            Loading_ani.msg, Loading_ani.msg_colour = 'Connected!', Colour['green']
            pg.time.wait(1500)
            if ani:
                Loading_ani.stop()
            self.log(f"Connected to '{MQTT_IP}' with username '{self.mac_address}'")
            return True

    def disconnect(self):
        if self.connected or self._mqtt.is_connected():
            self.send(f'/miniplayer/connection/{self.mac_address}', 'disconnected')
            self.unsubscribe(None, unsub_all=True)
            self.connected = False

    def reconnect(self):
        self.log('Reconnecting..')
        self.reconnect_pending = False
        Loading_ani.thread = threading.Thread(name='loading ani', target=Loading_ani.ani)
        Loading_ani.start(msg='Reconnecting', msg_colour=Colour['red'])
        Menu.stop(retain=True)
        Menu.allow_screensaver = False
        self.disconnect()
        retry_delay = 9  # Start at 9s and double per retry (to cap at 30 minutes exactly)
        pg.time.wait(500)
        while True:
            self.connect()  # Attempt connection
            if self.connected:
                break
            else:
                self.log(f'Waiting for {convert_s(retry_delay)}s')
                for temp in range(0, round(retry_delay)):
                    Loading_ani.msg = f'Reconnecting (retry in {convert_s(retry_delay - temp)})'
                    pg.time.wait(1000)
                if retry_delay < 1800:  # Cap at half an hour between attempts
                    retry_delay *= 2
                elif retry_delay > 1800:
                    retry_delay = 1800

        self.log('Reconnect complete')
        Loading_ani.stop()
        self.start_retained()
        Menu.start_retained()

    def subscribe(self, topics: str or tuple, response, retain=False):
        if type(topics) is str:
            topics = [topics]
        for topic in topics:
            if topic not in self.subscribed:
                self._mqtt.subscribe(topic)
                if retain:
                    self.retained.update({topic: response})
                self.subscribed.update({topic: response})
                self.log(f"Subscribed to '{topic}'{' (retained)' if retain else ''}")
            else:
                self.log(f"Already subscribed to '{topic}'{' (retained)' if retain else ''}", cat='WRN')

    def unsubscribe(self, topics: str or tuple, unsub_all=False):
        if unsub_all:
            for topic in self.subscribed:
                self._mqtt.unsubscribe(topic)
            self.subscribed = {}
            self.log('Unsubscribed from all topics.')
        else:
            if type(topics) is str:  # If only one topic then pass as list
                topics = [topics]

            for topic in topics:
                self._mqtt.unsubscribe(topic)
                if topic in self.subscribed:
                    self.subscribed.pop(topic)
                    self.log(f"Unsubscribed from '{topic}'")
                else:
                    self.log(f"'{topic}' not in subscriptions", cat='WRN')

                if topic in self.retained:
                    self.retained.pop(topic)
                    self.log(f"Removed '{topic}' from retained subscriptions")

    def start_retained(self):
        self.log('Starting retained topics')
        for topic in self.retained:
            self.subscribe(topic, self.retained[topic])

    def send(self, topic: str, payload):
        msg = str(payload).replace("'", "\"")
        self._mqtt.publish(topic, msg)
        self.log(f"Sent '{msg}' to '{topic}'")

    def update(self):
        if self._last_msg_time < pg.time.get_ticks():  # If no msg since auto_reconnect ms
            self.log('Auto reconnect set', cat='WRN')
            self._set_reconnect()  # Automatically start reconnect as no traffic sent


class LOCALWEATHER(Window):
    _mqtt_active = f'/miniplayer/weather/local/active/{MQTT.mac_address}'
    _mqtt_response = '/miniplayer/weather/local/response'

    def __init__(self):
        super().__init__('Local Weather')
        self._snow = False
        self.icon = pg.surface.Surface((128, 128)), pg.rect.Rect((70, 40, 128, 128))
        self.value = {}
        self._data = {}
        Menu.windows.append(self)

    def _load_default(self):
        self._data = {}
        self._data.update({'temp': render_text(
            '- °c', 100, bold=True, midleft=(self.icon[1].right + 60, self.icon[1].centery - 25))})
        self._data.update({'state': render_text(
            'Unknown', 50, topleft=(self._data['temp'][1].left, self._data['temp'][1].bottom + 10))})
        self._data.update({'temp f': render_text(
            'Feels like: - °c', 35, midtop=(CENTER[0] / 2, self._data['state'][1].bottom + 70))})
        self._data.update({'temp r': render_text(
            'L: - °c  H: - °c', 35, midtop=(CENTER[0] + CENTER[0] / 2, self._data['temp f'][1].top))})
        self._data.update({'hum': render_text(
            'Humidity: - %', 35, midtop=(self._data['temp f'][1].centerx, self._data['temp f'][1].bottom + 45))})
        self._data.update({'rain': render_text(
            ('Snow' if self._snow else 'Rain') + ': - mm/h', 35,
            midtop=(self._data['temp r'][1].centerx, self._data['temp r'][1].bottom + 45))})
        self._data.update({'wind': render_text(
            'Wind: - mph               Unknown               - mph avg', 35,
            midtop=(CENTER[0], self._data['hum'][1].bottom + 45))})
        self._data.update({'clouds': render_text(
            'Clouds: - %', 35, midtop=(self._data['hum'][1].centerx, self._data['wind'][1].bottom + 45))})
        self._data.update({'vis': render_text(
            'Visibility: - km', 35, midtop=(self._data['rain'][1].centerx, self._data['wind'][1].bottom + 45))})
        self.value = {
            'wind': {'cardinal': 'Unknown', 'speed': 0, 'gust': 0},
            'clouds': 0, 'snow': None, 'state': 'Unknown', 'icon': 'cloud',
            'temp': {'real': 0, 'feels': 0, 'min': 0}, 'rain': 0, 'hum': 0, 'vis': 0}
        self.icon = Img['weather']['cloud'], pg.rect.Rect((CENTER[0] - 30 - 300, 50, 300, 300))

    def get_icon(self, icon: str):
        try:
            self.icon = Img['weather'][icon]
            self.icon = self.icon, self.icon.get_rect(topright=(CENTER[0] - 30, 50))
        except Exception or BaseException as err:
            handle(err)
            self.err('Failed to load icon', data=f'id={icon}')
            self.icon = Img['weather']['cloud'], pg.rect.Rect((CENTER[0] - 30 - 300, 50, 300, 300))
        except:
            print('Unhandled exception -> LOCALWEATHER.get_icon()')
            self.err('Failed to load icon', data=f'id={icon}')
            self.icon = Img['weather']['cloud'], pg.rect.Rect((CENTER[0] - 30 - 300, 50, 300, 300))

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                self.value = json.loads(message.payload.decode('utf-8'))
                self.value['state'] = self.value['state'].replace('Clouds', 'Cloudy')
                self._snow = self.value['snow']
                self.get_icon(self.value['icon'])
                self._data['temp'] = render_text(str(self.value['temp']['real']) + '°c', 100, bold=True,
                                                 midleft=(self.icon[1].right + 60, self.icon[1].centery - 25))
                self._data['state'] = render_text(self.value['state'], 50, topleft=(self._data['temp'][1].left,
                                                                                    self._data['temp'][1].bottom + 10))
                self._data['temp f'] = render_text(f"Feels like: {round(self.value['temp']['feels'], 1)}°c", 35,
                                                   midtop=(CENTER[0] / 2, self._data['state'][1].bottom + 70))
                self._data['temp r'] = render_text(f"Lo: {self.value['temp']['min']}°c  "
                                                   f"Hi: {self.value['temp']['max']}°c", 35,
                                                   midtop=(CENTER[0] + CENTER[0] / 2, self._data['temp f'][1].top))
                self._data['hum'] = render_text(f"Humidity: {self.value['hum']}%", 35,
                                                midtop=(self._data['temp f'][1].centerx,
                                                        self._data['temp f'][1].bottom + 45))
                self._data['rain'] = render_text(
                    ('Snow' if self._snow else 'Rain') + f": {self.value['rain']}mm/h", 35,
                    midtop=(self._data['temp r'][1].centerx, self._data['temp r'][1].bottom + 45))
                self._data['wind'] = render_text('Wind: {0}mph             {1}             {2}mph avg'.format(
                    self.value['wind']['gust'], self.value['wind']['cardinal'], self.value['wind']['speed']), 35,
                    midtop=(CENTER[0], self._data['hum'][1].bottom + 45))
                self._data['clouds'] = render_text(f"Clouds: {self.value['clouds']}%", 35,
                                                   midtop=(self._data['hum'][1].centerx,
                                                           self._data['wind'][1].bottom + 45))
                self._data['vis'] = render_text(f"Visibility: {int((self.value['vis'] / 10000) * 100)}%", 35,
                                                midtop=(self._data['rain'][1].centerx,
                                                        self._data['wind'][1].bottom + 45))
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f'ERR: {err}'
                self._load_default()
            except:
                self.err('MQTT receive error -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

    def start(self):
        if self.active:
            self.err('Start called without stopping', cat='WRN')
            return

        self.log('Starting..')
        Mqtt.subscribe(self._mqtt_response, self.receive)
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED weather is active
        self.active = True
        self.log('Started')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        self.log('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED weather is not active
        Mqtt.unsubscribe(self._mqtt_response)
        Menu.allow_screensaver = True
        self.log('Allowed screensaver')
        self.active = False
        self.log('Stopped')

    def draw(self, surf=Display):
        surf.fill(Colour['black'])
        surf.blit(Bg, (0, 0))
        surf.blit(*render_text('Local weather', 35, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(*self.icon)
        surf.blit(*self._data['temp'])
        surf.blit(*self._data['state'])
        surf.blit(*self._data['temp f'])
        surf.blit(*self._data['temp r'])
        surf.blit(*self._data['hum'])
        surf.blit(*self._data['rain'])
        surf.blit(*self._data['wind'])
        surf.blit(*self._data['clouds'])
        surf.blit(*render_bar((350, 18), self.value['clouds'], 0, 100, fill_color=Colour['grey'],
                              midtop=(self._data['clouds'][1].centerx, self._data['clouds'][1].bottom + 20)))
        surf.blit(*self._data['vis'])
        surf.blit(*render_bar((350, 18), self.value['vis'], 0, 100, fill_color=Colour['grey'],
                              midtop=(self._data['vis'][1].centerx, self._data['vis'][1].bottom + 20)))

        surf.blit(*render_text(self.timestamp, 30, self._timestamp_color,
                               bold=True if 'ERR' in self.timestamp else False, bottomleft=(5, HEIGHT - 3)))

    def update(self):
        if ((not Mqtt.connected or self._mqtt_response not in Mqtt.subscribed) and
                self._timestamp_color != Colour['red']):
            self._timestamp_color = Colour['red']
            if Mqtt.connected:
                Mqtt.subscribe(self._mqtt_response, self.receive)


class SPOTIFY(Window):
    _mqtt_active = f'/miniplayer/spotify/active/{MQTT.mac_address}'
    _mqtt_action = '/miniplayer/spotify/action'
    _mqtt_response = '/miniplayer/spotify/response'
    _mqtt_device_response = '/miniplayer/spotify/device'
    _pending_action_length = 12000

    def __init__(self):
        super().__init__('Spotify')
        self._playing = False
        self._update_ms = 0
        self._pending_action = None
        self._pending_value = None
        self._action_time = 0
        self._timeout_time = 0
        self._prev_value = None
        self._data = {}
        self._playlists = []
        self._active_playlist = None
        self.value = {}
        self.device_value = {}
        self.show_playlists = False
        Menu.windows.append(self)
        self._load_default()
        Menu.message = 'Loading playlists...'
        self._get_playlists()

    @staticmethod
    def _shorten(txt: str):
        remove = False
        new_txt = ''
        for char in range(0, len(txt)):
            if (txt[char] == '(' or txt[char] == '[') and not remove:
                remove = True
            elif (txt[char - 1] == ')' or txt[char - 1] == ']') and remove:
                remove = False
            if not remove:
                new_txt += txt[char]

        return new_txt.strip()

    def _fetch_image(self, url: str):
        response = requests.get(url)  # Request playlists
        if response.status_code == 200:
            try:
                surf = pg.transform.smoothscale(pg.image.load(io.BytesIO(response.content)), (140, 140))
                return surf
            except:
                self.err(f'Failed to load playlist image (url={url})')
                return pg.surface.Surface((140, 140))
        else:
            self.err(f'Failed to get playlist image (code={response.status_code}, url={url})')
            return pg.surface.Surface((140, 140))

    def _load_default(self):
        icon = pg.transform.scale(Img['spotify']['logo'], (212, 64))
        cover = pg.surface.Surface((300, 300))
        cover.set_alpha(150)
        self._data = {'icon': (icon, icon.get_rect(center=(CENTER[0], Menu.left[1].centery))),
                      'bg': None,
                      'album_cover': (cover, cover.get_rect(topleft=(100, 125))),
                      'pause': Img['spotify']['pause'],
                      'play': Img['spotify']['play'],
                      'shuffle': Img['spotify']['shuffle'],
                      'shuffle_active': (Img['spotify']['shuffle'][0].copy(), Img['spotify']['shuffle'][1].copy()),
                      'playlist': Img['spotify']['playlist'],
                      'skip_l': (pg.transform.flip(Img['spotify']['skip'][0], True, False),
                                 pg.transform.flip(Img['spotify']['skip'][1], True, False)),
                      'skip_r': Img['spotify']['skip'],
                      'volume': {
                          'left': pg.rect.Rect(0, 0, 50, 50),
                          'right_1': pg.rect.Rect(0, 0, 50, 50),
                          'right_2': pg.rect.Rect(0, 0, 50, 50),
                          'm': Img['spotify']['mute'],
                          '0': Img['spotify']['vol 0'],
                          '50': Img['spotify']['vol 50'],
                          '100': Img['spotify']['vol 100'],
                          '-': Img['spotify']['vol -'],
                          '+': Img['spotify']['vol +']}}
        for index in range(0, len(self._data['shuffle_active'])):  # Duplicate shuffle as green from white
            pg.transform.threshold(self._data['shuffle_active'][index], self._data['shuffle_active'][index],
                                   search_color=(255, 255, 255), set_color=(24, 216, 97), inverse_set=True)
        surf = pg.surface.Surface((50, 50))
        self._data.update({'center': surf.get_rect(center=(CENTER[0], CENTER[1] + 160))})
        top = self._data['center'].top
        self._data.update({'left': surf.get_rect(topright=(self._data['center'].left - 50, top))})
        self._data.update({'far_left': surf.get_rect(topright=(self._data['left'].left - 50, top))})
        self._data.update({'right': surf.get_rect(topleft=(self._data['center'].right + 50, top))})
        self._data.update({'far_right': surf.get_rect(topleft=(self._data['right'].right + 50, top))})

        self._data.update({'plist': {  # PLAYLISTS
            'pause': self._data['pause'][1].copy(),
            'scroll_u': (pg.transform.rotate(self._data['skip_r'][0], 90),
                         pg.transform.rotate(self._data['skip_r'][1], 90),
                         surf.get_rect(topleft=(Menu.right[1].left, Menu.right[1].bottom + 32))),
            'scroll_d': (pg.transform.rotate(self._data['skip_r'][0], -90),
                         pg.transform.rotate(self._data['skip_r'][1], -90),
                         surf.get_rect(bottomleft=(Menu.right[1].left, HEIGHT - 16))),
            'move_u': (pg.transform.rotate(self._data['play'][0], 90),
                       pg.transform.rotate(self._data['play'][1], 90)),
            'move_d': (pg.transform.rotate(self._data['play'][0], -90),
                       pg.transform.rotate(self._data['play'][1], -90)),
            'page': 0}})
        pg.transform.threshold(self._data['plist']['pause'], self._data['plist']['pause'],
                               search_color=(255, 255, 255), set_color=(24, 216, 97), inverse_set=True)
        pos = 30, 100, 140, 140, 10  # x, y, width, height, spacing
        temp = [{'cover': pg.surface.Surface((pos[2], pos[3])).get_rect(topleft=(pos[0], pos[1]))},
                {'cover': pg.surface.Surface((pos[2], pos[3])).get_rect(topleft=(pos[0], pos[1] + pos[3] + pos[4]))},
                {'cover': pg.surface.Surface((pos[2], pos[3])).get_rect(
                    topleft=(pos[0], pos[1] + ((pos[3] + pos[4]) * 2)))},
                {'cover': pg.surface.Surface((pos[2], pos[3])).get_rect(
                    topleft=(pos[0], pos[1] + ((pos[3] + pos[4]) * 3)))}]
        for index in range(0, len(temp)):
            temp[index].update({'play': pg.surface.Surface((50, 50)).get_rect(
                bottomleft=(temp[index]['cover'].right + 20, temp[index]['cover'].bottom - 10))})
            temp[index].update({'move_u': pg.surface.Surface((50, 50)).get_rect(
                midright=(Menu.right[1].left - 30, temp[index]['cover'].centery))})
            temp[index].update({'move_d': pg.surface.Surface((50, 50)).get_rect(
                midright=(temp[index]['move_u'].left - 40, temp[index]['cover'].centery))})
        self._data.update({'plist_rect': temp})

        self.value = {  # DEFAULT VALUES
            'playlist_uri': '',
            'progress_ms': 0,
            'progress': '0:00',
            'album': {
                'cover_url': '',
                'name': 'Loading...'},
            'artists': [{'name': 'Loading...'}],
            'duration_ms': 0,
            'duration': '-:--',
            'explicit': False,
            'song_name': 'Loading...',
            'is_playing': False,
            'shuffle': False}
        self.device_value = {
            'name': '',
            'type': '',
            'volume_percent': 0
        }

    def _get_playlists(self) -> bool:
        self.log('Fetching playlists..')
        try:  # Request data from Node-RED
            response = requests.get(f'http://{NODERED_IP}:{NODERED_PORT}/spotify/playlists', timeout=10)
        except Exception as err:
            self._playlists = []
            self.err('Playlist fetch failed', data=err)
            return False

        if response.status_code == 200:
            self.log('Playlists fetched successfully')
            try:
                playlists = json.load(io.BytesIO(response.content))  # Decode response
                temp = {}  # Playlist by id
                for playlist in playlists:  # For each playlist
                    temp.update({playlist['id'].replace('spotify:playlist:', ''): playlist})  # Set id as key to dict
                playlists = temp  # Reuse playlists as playlist by id
                self._playlists = []  # Clear previous playlists
                for key in Settings.value['Playlist Order']:  # For each ordered playlist add known playlists in order
                    try:
                        self._playlists.append(playlists[key.replace('spotify:playlist:', '')])
                    except KeyError:
                        Settings.value['Playlist Order'].remove(key)
                        self.log(f"Removed invalid playlist from settings ('{key}')")
                for key in playlists:  # For every playlist
                    if key not in Settings.value['Playlist Order']:  # If unknown
                        self._playlists.append(playlists[key])  # Add unknown playlists to end
                        Settings.value['Playlist Order'].append(playlists[key]['id'])  # Add to known playlists
                self.log('Playlists ordered successfully')
                Settings.save()  # Save playlist order
                self.log('Loading playlist images...')
                temp = timer()
                cache = {}
                if not os.path.isdir('playlists'):
                    self.log("Folder 'playlists' not found, attempting to fix..")
                    try:
                        os.mkdir('playlists')
                    except PermissionError:
                        self.err("Failed to create folder 'playlists' -> write permission denied")
                    except TypeError:
                        self.err('Failed to create folder -> type error')
                    except:
                        self.err("Failed to create folder 'playlists' -> unknown")
                try:
                    files = os.listdir('playlists/')
                    for file in files:
                        cache.update({file.replace('.png', ''): pg.image.load_extended('playlists/' + file, 'png')})
                except PermissionError:
                    self.err('Failed to read cache -> read permission denied')
                except TypeError:
                    self.err('Failed to read cache -> type error')
                except:
                    self.err('Failed to read cache -> unknown')

                for playlist in self._playlists:
                    if playlist['id'] not in cache:
                        playlist['images'] = self._fetch_image(playlist['images'][0]['url'])  # Load img
                        if os.path.isdir('playlists'):
                            try:
                                pg.image.save_extended(playlist['images'], f"{playlist['id']}.png", 'png')
                                shutil.move(f"{playlist['id']}.png",
                                            f"playlists/{playlist['id']}.png")
                                self.log(f"Cached image (id:{playlist['id']})")
                            except PermissionError:
                                self.err('Failed to cache image -> write permission denied')
                            except TypeError:
                                self.err('Failed to cache image -> type error')
                            except:
                                self.err('Failed to cache image -> unknown')
                    else:
                        playlist['images'] = cache[playlist['id']]
                        self.log(f"Loaded cache (id:{playlist['id']})")

                self.log(f"Loaded playlist images (took {round(timer() - temp, 2)}s)")
                return True

            except Exception as err:
                self._playlists = []
                handle(err)
                self.err('Playlist ordering failed')
                return False
        else:
            self._playlists = []
            self.err(f"Playlist fetch failed (code={response.status_code} "
                     f"url={f'http://{NODERED_IP}:{NODERED_PORT}/spotify/playlists'})")
            return False

    def _update_playlists(self, uid: str):
        response = requests.get(f'http://{NODERED_IP}:{NODERED_PORT}/spotify/playlists?id={uid}')
        if response.status_code == 200:  # Fetch playlist
            try:
                playlist = json.load(io.BytesIO(response.content))  # Decode response
                if playlist['id'] == 'spotify:user:ag.bungee:collection':
                    return False
                else:
                    self._playlists.append(playlist)
                    Settings.value['Playlist Order'].append(playlist['id'])
                    Settings.save()
                    playlist['images'] = self._fetch_image(playlist['images'][0]['url'])
                    self.log(f"Playlist updated (id={uid}, name={playlist['name']})")
                    return playlist['id']

            except:
                self.err(f'Failed to decode playlist during update (id={uid})')
                return False
        else:
            if response.status_code != 500:
                self.err(f'Failed to update playlists (code={response.status_code}, id={uid})')
            return False

    def _save_playlists(self):
        temp = []
        for plist in self._playlists:
            temp.append(plist['id'])
        Settings.value['Playlist Order'] = temp
        Settings.save()

    def reload_playlists(self) -> bool:
        self._playlists = []
        self._active_playlist = None
        return self._get_playlists()

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                msg = json.loads(message.payload.decode('utf-8'))
                if not msg:
                    self._playing = False
                    return
                else:
                    self._playing = True

                if msg['album']['cover_url'] != self.value['album']['cover_url']:  # Fetch album artwork
                    temp = WIDTH if WIDTH > HEIGHT else HEIGHT  # Fit to screen (keep aspect ratio 1:1)
                    cover = pg.transform.smoothscale(pg.image.load(io.BytesIO(
                        requests.get(msg['album']['cover_url']).content)), (temp, temp))
                    cover_crop = pg.surface.Surface((WIDTH, HEIGHT))
                    cover_crop.blit(cover, (CENTER[0] - cover.get_rect().centerx, CENTER[1] - cover.get_rect().centery))
                    cover_crop.set_alpha(80)
                    self._data['bg'] = cover_crop, (0, 0)
                    cover = pg.transform.smoothscale(cover, (300, 300))
                    self._data['album_cover'] = cover, cover.get_rect(topleft=(100, 125))

                self.value = msg  # Copy response and convert values
                if self.value['playlist_uri']:
                    self.value['playlist_uri'] = self.value['playlist_uri'].replace('spotify:playlist:', '')
                self.value['song_name'] = self._shorten(self.value['song_name'])
                self.value['duration_ms'] = int(self.value['duration_ms'])
                self.value.update({'duration': convert_s(self.value['duration_ms'] // 1000)})
                self.value['progress_ms'] = int(self.value['progress_ms'])
                self.value.update({'progress': convert_s(self.value['progress_ms'] // 1000)})
                self.value['album']['name'] = self._shorten(self.value['album']['name'])

                # If current song is in playlist
                if self.value['playlist_uri'] and self.value['playlist_uri'] != 'spotify:user:ag.bungee:collection':
                    if self.value['playlist_uri'] not in Settings.value['Playlist Order']:  # If unknown playlist
                        self._update_playlists(self.value['playlist_uri'])  # Fetch new playlist
                    try:
                        self._active_playlist = self._playlists[Settings.value[
                            'Playlist Order'].index(self.value['playlist_uri'])]  # Set current playlist
                    except:
                        self._active_playlist = None
                else:
                    self._active_playlist = None

                self._update_ms = pg.time.get_ticks() - 30  # Set time for progress bar

                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f'ERR: {err}'
                self._load_default()
            except:
                self.err('MQTT receive error -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

        elif message.topic == self._mqtt_device_response:
            try:
                self.device_value = json.loads(message.payload.decode('utf-8'))
                self.device_value['name'] = self.device_value['name'].lower().title().replace("'S", "'s")

                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f'ERR: {err}'
                self._load_default()
            except:
                self.err('MQTT receive error 2 -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

    def start(self):
        if self.active:
            self.err('Start called without stopping', cat='WRN')
            return

        self.log('Starting..')
        Mqtt.subscribe((self._mqtt_response, self._mqtt_device_response), self.receive)
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED spotify is active
        self.active = True
        self.log('Started')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        self.log('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED spotify is not active
        Mqtt.unsubscribe((self._mqtt_response, self._mqtt_device_response))
        Menu.allow_screensaver = True
        self.log('Allowed screensaver')
        self.active = False
        self.log('Stopped')

    def draw(self, surf=Display):
        surf.fill(Colour['black'])
        try:
            if self._data['bg']:
                surf.blit(*self._data['bg'])
            else:
                draw_bg(surf=surf)
            if self._playing and self._data['album_cover']:
                surf.blit(*self._data['album_cover'])
        except:
            draw_bg(surf=surf)

        surf.blit(*self._data['icon'])
        if not self._playing:
            surf.blit(*render_text('Not Playing', 80, bold=True, center=CENTER))
        else:
            txt = render_text(self.value['song_name'], 35, bold=True,
                              bottomleft=(self._data['album_cover'][1].right + 25,
                                          self._data['album_cover'][1].top + self._data['album_cover'][1].height / 4))
            surf.blit(*txt)  # SONG DETAILS
            surf.blit(*render_text(self.value['artists'][0]['name'], 35,
                                   midleft=(txt[1].left, self._data['album_cover'][1].centery)))
            surf.blit(*render_text(self.value['album']['name'], 35,
                                   topleft=(txt[1].left, self._data['album_cover'][1].centery +
                                            self._data['album_cover'][1].height / 4)))

            surf.blit(self._data['playlist'], self._data['far_left'])  # BUTTONS
            surf.blit(self._data['skip_l'][1 if self._pending_action != 'rewind' else 0], self._data['left'])
            surf.blit(self._data['pause' if self.value['is_playing'] else 'play']
                      [1 if self._pending_action != ('pause' if self.value['is_playing'] else 'play') else 0],
                      self._data['center'])
            surf.blit(self._data['skip_r'][1 if self._pending_action != 'skip' else 0], self._data['right'])
            surf.blit(self._data['shuffle_active' if self.value['shuffle'] else 'shuffle']
                      [1 if self._pending_action != 'shuffle' else 0], self._data['far_right'])

            bar = render_bar((800, 16), self.value['progress_ms'], 0, self.value['duration_ms'],  # PROGRESS BAR
                             midtop=(CENTER[0], self._data['center'].bottom + 40))
            surf.blit(*bar)
            surf.blit(*render_text(self.value['progress'], 30, Colour['white'], bold=True,  # PROGRESS
                                   midright=(bar[1].left - 30, bar[1].centery + 1)))
            surf.blit(*render_text(self.value['duration'], 30, Colour['white'], bold=True,  # DURATION
                                   midleft=(bar[1].right + 30, bar[1].centery + 1)))

            bar = render_bar((300, 14), self.device_value['volume_percent'], 0, 100,  # VOLUME BAR
                             midtop=(CENTER[0], bar[1].bottom + 45))
            surf.blit(*bar)
            self._data['volume']['left'].midright = bar[1].left - 20, bar[1].centery  # VOLUME ICON
            self._data['volume']['right_1'].midleft = bar[1].right + 20, bar[1].centery
            self._data['volume']['right_2'].midleft = self._data['volume']['right_1'].right + 20, bar[1].centery
            if self.device_value['volume_percent'] == 0:
                surf.blit(self._data['volume']['m'], self._data['volume']['left'])
            elif self.device_value['volume_percent'] >= 65:
                surf.blit(self._data['volume']['100'], self._data['volume']['left'])
            elif self.device_value['volume_percent'] >= 35:
                surf.blit(self._data['volume']['50'], self._data['volume']['left'])
            else:
                surf.blit(self._data['volume']['0'], self._data['volume']['left'])

            if self.device_value['volume_percent'] >= 0:  # VOLUME CONTROLS
                surf.blit(self._data['volume']['-'][1 if self._pending_action != 'decrease_volume' else 0],
                          self._data['volume']['right_1'])
            if self.device_value['volume_percent'] <= 100:
                surf.blit(self._data['volume']['+'][1 if self._pending_action != 'increase_volume' else 0],
                          self._data['volume']['right_2'])

        if self.show_playlists:
            surf.blit(Settings.shadow, (0, 0))
            surf.blit(Menu.cross, Menu.right[1])
            temp = render_text('Playlists', 35, bold=True, center=(CENTER[0], Menu.right[1].centery - 5))
            surf.blit(*temp)
            if self._playlists:  # If there are playlists
                if self._active_playlist and 'name' in self._active_playlist.keys():
                    surf.blit(*render_text(f"Currently playing: {self._active_playlist['name']}", 30,
                                           midtop=(CENTER[0], temp[1].bottom + 10)))
                for index in range(0, len(self._data['plist_rect']) if len(
                        self._playlists) > len(self._data['plist_rect']) else len(self._playlists)):  # For shown plists
                    rect = self._data['plist_rect'][index]
                    index += self._data['plist']['page'] * len(self._data['plist_rect'])  # Offset index by page
                    if index >= len(self._playlists):
                        break
                    plist = self._playlists[index]

                    surf.blit(plist['images'], rect['cover'])  # Image
                    surf.blit(*render_text(plist['name'], 45, bold=True,  # Name
                                           midleft=(rect['cover'].right + 20,
                                                    rect['cover'].centery - rect['cover'].height / 4)))
                    surf.blit(self._data['play'][1] if self._active_playlist != plist else
                              self._data['plist']['pause'], rect['play'])  # Play button
                    surf.blit(*render_text(f"{plist['tracks']['total']} Songs", 35,
                                           midleft=(rect['play'].right + 20, rect['play'].centery)))  # Song count
                    surf.blit(self._data['plist']['move_d'][1 if index < len(
                              self._playlists) - 1 else 0], rect['move_d'])
                    surf.blit(self._data['plist']['move_u'][1 if index > 0 else 0], rect['move_u'])

                surf.blit(self._data['plist']['scroll_u'][1 if self._data['plist']['page'] > 0 else 0],
                          self._data['plist']['scroll_u'][2])
                surf.blit(self._data['plist']['scroll_d'][1 if self._data['plist']['page'] <
                          floor(len(self._playlists) / len(self._data['plist_rect'])) else 0],
                          self._data['plist']['scroll_d'][2])

        if Settings.value['Device Info']:
            surf.blit(*render_text(self.device_value['name'], 30, Colour['grey'], bottomright=(WIDTH - 5, HEIGHT - 3)))
        if self._timeout_time > pg.time.get_ticks() and not self.show_playlists:  # Action status
            set_info('Action timed out!', Colour['red'])
        if not self.show_playlists:  # Timestamp
            surf.blit(*render_text(self.timestamp, 30, self._timestamp_color, bottomleft=(5, HEIGHT - 3)))

    def update(self):
        global Button_cooldown
        if (self.value['is_playing'] or self.show_playlists) and Menu.allow_screensaver and not Settings.active:
            Menu.allow_screensaver = False
            self.log('Disabled screensaver')
        elif (not self.value['is_playing'] and not self.show_playlists and not Menu.allow_screensaver and
              not Settings.active):
            Menu.allow_screensaver = True
            self.log('Allowed screensaver')
        if not self._playing and self.show_playlists:  # Disable playlists if not playing
            self.show_playlists = False
        if self._playing:
            # UPDATE PROGRESS BAR
            if pg.time.get_ticks() - self._update_ms >= 1000 and self.value['is_playing'] and \
                    self.value['progress_ms'] + 1000 < self.value['duration_ms']:
                self._update_ms = pg.time.get_ticks()
                self.value['progress_ms'] += 1000
                self.value['progress'] = convert_s(self.value['progress_ms'] // 1000)
            elif self.value['progress_ms'] + 1000 >= self.value['duration_ms']:
                self.value['progress_ms'] = self.value['duration_ms']
                self.value['progress'] = convert_s(self.value['progress_ms'] // 1000)

            # CONTROLS
            action = None
            if not Settings.active and not self.show_playlists and not Button_cooldown and (
                    not TOUCHSCREEN and pg.mouse.get_pressed()[0] or
                    TOUCHSCREEN and pg.mouse.get_pos() != Prev_mouse_pos):
                if self._data['center'].collidepoint(Mouse_pos):
                    action = 'pause' if self.value['is_playing'] else 'play'
                    self._prev_value = self.value['is_playing']
                elif self._data['left'].collidepoint(Mouse_pos):
                    action = 'rewind'
                    self._prev_value = self.value['song_name']
                elif self._data['right'].collidepoint(Mouse_pos):
                    action = 'skip'
                    self._prev_value = self.value['song_name']
                elif self._data['far_right'].collidepoint(Mouse_pos):
                    action = 'shuffle'
                    self._prev_value = self.value['shuffle']
                elif (self._data['volume']['right_1'].collidepoint(Mouse_pos) and
                      self.device_value['volume_percent'] > 0):
                    action = 'decrease_volume'
                    self._prev_value = self.device_value['volume_percent']
                elif (self._data['volume']['right_2'].collidepoint(Mouse_pos) and
                      self.device_value['volume_percent'] < 100):
                    action = 'increase_volume'
                    self._prev_value = self.device_value['volume_percent']

                if action and not self._pending_action and not self._action_time:
                    Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                    self._action_time = pg.time.get_ticks() + self._pending_action_length
                    self._pending_action = action
                    if action == 'decrease_volume':
                        Mqtt.send(self._mqtt_action, self.device_value['volume_percent'] - 5
                                  if self.device_value['volume_percent'] - 5 >= 0 else 0)
                    elif action == 'increase_volume':
                        Mqtt.send(self._mqtt_action, self.device_value['volume_percent'] + 5
                                  if self.device_value['volume_percent'] + 5 <= 100 else 100)
                    else:
                        Mqtt.send(self._mqtt_action, action)
                    self.log(f'{action.title()} requested')

                if self._data['far_left'].collidepoint(Mouse_pos):  # PLAYLIST (open)
                    Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                    Menu.allow_controls = False
                    self.show_playlists = True
                    self.log('Opened playlists')

            if self._pending_action == 'pause' and self.value['is_playing'] != self._prev_value or \
                    self._pending_action == 'play' and self.value['is_playing'] != self._prev_value or \
                    self._pending_action == 'skip' and self.value['song_name'] != self._prev_value or \
                    self._pending_action == 'rewind' and self.value['song_name'] != self._prev_value or \
                    self._pending_action == 'increase_volume' and \
                    self.device_value['volume_percent'] > self._prev_value or \
                    self._pending_action == 'decrease_volume' and \
                    self.device_value['volume_percent'] < self._prev_value or \
                    self._pending_action == 'shuffle' and self.value['shuffle'] != self._prev_value:
                self.log(f'{self._pending_action.title()} confirmed')
                set_info(f"{self._pending_action.title().replace('_', ' ')} confirmed")
                self._action_time = 0
                self._prev_value = None
                self._pending_action = None

            if self._action_time and pg.time.get_ticks() >= self._action_time:
                self.err(f'{self._pending_action} timed out')
                self._timeout_time = pg.time.get_ticks() + 5000
                self._action_time = 0
                self._prev_value = None
                self._pending_action = None

            if self.show_playlists:
                if not Button_cooldown and (not TOUCHSCREEN and pg.mouse.get_pressed()[0] or
                                            TOUCHSCREEN and pg.mouse.get_pos() != Prev_mouse_pos):
                    if Menu.right[1].collidepoint(Mouse_pos):  # PLAYLIST (close)
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._save_playlists()
                        Menu.allow_controls = True
                        self.show_playlists = False
                        self.log('Closed playlists')
                    elif self._data['plist']['scroll_u'][2].collidepoint(Mouse_pos) and self._data['plist']['page'] > 0:
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._data['plist']['page'] -= 1
                        self.log('Scroll up')
                    elif (self._data['plist']['scroll_d'][2].collidepoint(Mouse_pos) and   # Scroll down
                          self._data['plist']['page'] < floor(len(self._playlists) / len(self._data['plist_rect']))):
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._data['plist']['page'] += 1
                        self.log('Scroll down')

                    else:
                        for index in range(0, len(self._data['plist_rect'])):  # For each shown playlist
                            rect = self._data['plist_rect'][index]
                            index += self._data['plist']['page'] * len(self._data['plist_rect'])  # Offset index by page
                            if index >= len(self._playlists):
                                break
                            plist = self._playlists[index]
                            if rect['play'].collidepoint(Mouse_pos):  # Play
                                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                                Mqtt.send(self._mqtt_action, plist['uri'])
                                self.log(f"Playlist '{plist['id']}' ({plist['name']}) requested")
                            elif rect['move_u'].collidepoint(Mouse_pos) and index > 0:  # Move up
                                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                                self._playlists[index] = self._playlists[index - 1]
                                self._playlists[index - 1] = plist
                                self.log(f"Move playlist '{plist['id']}' ({plist['name']}) up")
                            elif rect['move_d'].collidepoint(Mouse_pos) and index < len(self._playlists) - 1:  # Down
                                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                                self._playlists[index] = self._playlists[index + 1]
                                self._playlists[index + 1] = plist
                                self.log(f"Move playlist '{plist['id']}' ({plist['name']}) down")


class OCTOPRINT(Window):
    _mqtt_active = f'/miniplayer/octoprint/active/{MQTT.mac_address}'

    def __init__(self):
        super().__init__('OctoPrint')
        temp = '/miniplayer/octoprint/'
        self._mqtt_responses = temp + 'progress/printing', temp + 'position', temp + 'temperature'
        self._data = {}
        self.value = {}
        self.printing = False
        self._load_default()
        # Menu.windows.append(self)

    def _load_default(self):
        self._data = {
            'state': render_text('Unknown: -%', 25, bold=True, topleft=(15, Menu.left[1].bottom + 15)),
            'pos': {
                'x': render_bar((140, 10), 0, 0, 320),
                'y': render_bar((140, 10), 0, -10, 340),
                'z': render_bar((140, 10), 0, 0, 330)
            }
        }
        self._data.update({'state_bar': render_bar((self._data['state'][1].width, 10), 0, 0, 100,
                                                   topleft=(self._data['state'][1].left,
                                                            self._data['state'][1].bottom + 5))})
        self.value = {
            'path': '',
            'progress': {
                'completion': 0,
                'printTime': 0,
                'printTimeLeft': 0},
            'state': {'text': 'Unknown',
                      'flags': {
                          'operational': False,
                          'printing': False,
                          'cancelling': False,
                          'pausing': False,
                          'resuming': False,
                          'finishing': False,
                          'closedOrError': False,
                          'error': False,
                          'paused': False,
                          'ready': False,
                          'sdReady': False},
                      'error': ''},
            'pos': {
                'x': 0,
                'y': 0,
                'z': 0},
            'temp': {
                'bed': {
                    'actual': 0,
                    'target': 0},
                'tool': {
                    'actual': 0,
                    'target': 0}}}

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_responses[0]:
            try:
                msg = json.loads(message.payload.decode('utf-8'))
                self.value['path'] = msg['path']
                self.value['progress'] = msg['progress']
                self.value['state'] = msg['state']
                self.printing = self.value['state']['flags']['printing']
                self._data['state'] = render_text(
                    f'{self.value["state"]["text"]}: {round(self.value["progress"]["completion"])}%', 25, bold=True,
                    topleft=(15, Menu.left[1].bottom + 15))
                self._data['state_bar'] = render_bar((self._data['state'][1].width, 10),
                                                     round(self.value['progress']['completion']), 0, 100,
                                                     topleft=(self._data['state'][1].left,
                                                              self._data['state'][1].bottom + 5))
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f'ERR: {err}'
                self._load_default()
            except:
                self.err('MQTT receive error (state) -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

        elif message.topic == self._mqtt_responses[1]:
            try:
                msg = json.loads(message.payload.decode('utf-8'))
                self.value['pos'] = msg['position']
                self._data['pos']['x'] = render_bar((140, 10), self.value['pos']['x'], 0, 320)
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f'ERR: {err}'
                self._load_default()
            except:
                self.err('MQTT receive error (pos) -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

        elif message.topic == self._mqtt_responses[2]:
            try:
                msg = json.loads(message.payload.decode('utf-8'))
                self.value['temp'] = msg
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: {err}'
                self._load_default()
            except:
                self.err('MQTT receive error (temp) -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

    def start(self):
        if self.active:
            self.err('Start called without stopping', cat='WRN')
            return

        Mqtt.subscribe(self._mqtt_responses, self.receive)
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED octoprint is active
        self.active = True
        self.log('Started.')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED octoprint is not active
        Mqtt.unsubscribe(self._mqtt_responses)
        Menu.allow_screensaver = True
        self.log('Allowed screensaver')
        self.active = False
        self.log('Stopped.')

    def draw(self, surf=Display):
        surf.fill(Colour['black'])
        draw_bg()
        surf.blit(*render_text(self.name, 20, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(*render_text(self.timestamp, 15, self._timestamp_color, bottomleft=(5, HEIGHT - 3)))
        surf.blit(*self._data['state'])
        surf.blit(*self._data['state_bar'])
        # surf.blit(*self._data['pos']['x'])
        # surf.blit(*self._data['pos']['y'])
        # surf.blit(*self._data['pos']['z'])

    def update(self):
        Menu.allow_screensaver = not self.printing


def convert_s(sec: int) -> str:
    minutes = 0
    hours = 0
    if sec >= 60:
        minutes = sec // 60
        sec -= minutes * 60
        if sec < 10:
            sec = f'0{sec}'
    elif sec < 10:
        sec = f'0{sec}'
    if minutes >= 60:
        hours = minutes // 60
        minutes -= hours * 60
    if not sec:
        sec = '00'
    if not minutes and not hours:
        minutes = '0'
    elif not minutes and hours:
        minutes = '00'
    if not hours:
        return str(minutes) + ':' + str(sec)
    else:
        return str(hours) + ':' + str(minutes) + ':' + str(sec)


def convert_ms(timestamp: timer) -> float:
    return round((timer() - timestamp) * 1000, 2)


def render_text(text: str or int, size: int, colour=Colour['white'], bold=False, **kwargs)\
        -> tuple[pg.surface, pg.rect]:
    global Loaded_fonts
    font = 'assets/boldfont.ttf' if bold else 'assets/thinfont.ttf'
    font_name = str(size) + font
    try:
        loaded_font = Loaded_fonts[font_name]
    except KeyError:
        try:
            loaded_font = pg.font.Font(font, size)
            Loaded_fonts[font_name] = loaded_font
        except Exception or BaseException:
            loaded_font = pg.font.Font(None, size)
    surf = loaded_font.render(str(text), True, colour)
    return surf, surf.get_rect(**kwargs)


def render_bar(size: tuple[int, int], value: int or float, min_value: int or float, max_value: int or float,
               fill_color=Colour['white'], border_width=2, border_radius=7, border_color=Colour['white'], **kwargs)\
        -> tuple[pg.surface, pg.rect]:
    value = float(value)

    surf = pg.surface.Surface((size[0], size[1]))
    surf.fill((1, 1, 1))
    surf.set_colorkey((1, 1, 1))

    if min_value < 0:
        min_value = -min_value  # Convert min value to positive number
        ratio = ((size[0] - border_width - 1) / (max_value + min_value)) * (value + min_value)
        if value > 0 - min_value:
            pg.draw.line(surf, fill_color, (border_width, (size[1] / 2) - 1),
                         (ratio, (size[1] / 2) - 1), width=size[1] - border_width * 2)

        ratio = round((size[0] - border_width - 1) / max_value * value)
        if value > min_value and ratio > border_width:
            pg.draw.line(surf, Colour['white'] if value < 0 else Colour['grey'],
                         (ratio, border_width), (ratio, size[1] - border_width))

    else:
        try:
            ratio = round((size[0] - border_width - 1) / max_value * value)
        except ZeroDivisionError:
            ratio = 0
        if value > min_value and ratio > border_width:
            pg.draw.line(surf, fill_color, (border_width, (size[1] / 2) - 1),
                         (ratio, (size[1] / 2) - 1), width=size[1] - border_width * 2)

    pg.draw.rect(surf, border_color, (0, 0, size[0], size[1]), width=border_width, border_radius=border_radius)

    return surf, surf.get_rect(**kwargs)


def render_button(state: bool or tuple[int, int, int] or None, size=(70, 35), surf=Display, **kwargs) -> pg.rect:
    surface = pg.surface.Surface((64, 32))
    surface.fill(Colour['key'])
    surface.set_colorkey(Colour['key'])
    rect = surface.get_rect(**kwargs)

    shade = pg.surface.Surface((64, 32))  # SHADING
    shade.fill(Colour['key'])
    shade.set_colorkey(Colour['key'])
    shade.set_alpha(100)
    if type(state) is tuple:
        color = state
    else:
        if state:
            color = Colour['l green']
        elif state is None:
            color = Colour['grey']
        else:
            color = Colour['red']
    pg.draw.circle(shade, color, (16, 16), 14, draw_top_left=True, draw_bottom_left=True)
    pg.draw.rect(shade, color, (16, 2, 32, 28))
    pg.draw.circle(shade, color, (48, 16), 14, draw_top_right=True, draw_bottom_right=True)
    surf.blit(pg.transform.scale(shade, size), rect.topleft)

    if state and type(state) is bool:  # PIN
        pg.draw.circle(surface, Colour['white'], (48, 16), 12, width=2)
        pg.draw.circle(surface, Colour['green'], (48, 16), 10)
    elif state is None or type(state) is tuple:
        surface.blit(*render_text('Press', 18, bold=True, center=surface.get_rect().center))
    else:
        pg.draw.circle(surface, Colour['white'], (16, 16), 12, width=2)
        pg.draw.circle(surface, Colour['red'], (16, 16), 10)

    pg.draw.circle(surface, Colour['white'], (16, 16), 16, width=2, draw_top_left=True, draw_bottom_left=True)  # BORDER
    pg.draw.line(surface, Colour['white'], (16, 0), (48, 0), width=2)
    pg.draw.line(surface, Colour['white'], (16, 30), (48, 30), width=2)
    pg.draw.circle(surface, Colour['white'], (48, 16), 16, width=2, draw_top_right=True, draw_bottom_right=True)
    surf.blit(pg.transform.scale(surface, size), rect.topleft)

    return rect


def draw_bg(txt=False, surf=Display):
    surf.blit(Bg, (0, 0))
    if txt:
        txt = render_text('Miniplayer', 64, bold=True, center=CENTER)
        surf.blit(*txt)
        surf.blit(*render_text('v2.0', 32, midtop=(txt[1].centerx, txt[1].bottom + 20)))


def set_info(txt: str, colour=Colour['green'], timeout=2000):
    global Info  # txt, colour, ms
    if not Info[0] or Info[2] < pg.time.get_ticks():  # If not showing or timeout
        Info = txt, colour, pg.time.get_ticks() + timeout


def main():
    global Current_window, Button_cooldown, Mouse_pos, Prev_mouse_pos
    while True:  # Forever loop
        # mainloop_time = timer()
        while Loading_ani.active:
            pg.time.wait(250)  # Wait for animation to finish if playing
        if Mqtt.reconnect_pending:
            Mqtt.reconnect()  # Reconnect sequence in main thread instead of threaded (issues if threaded)

        Clock.tick(FPS)
        for event in pg.event.get():  # Pygame event handling
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                raise KeyboardInterrupt
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN:
                    Mqtt.disconnect() if Mqtt.connected else Mqtt.connect()
                elif event.key == pg.K_r:
                    Mqtt.reconnect_pending = True

        Mouse_pos = pg.mouse.get_pos()

        try:
            if not Menu.screensaver:
                if not Current_window.active:  # ALL WINDOWS
                    print('[Main] Starting Current_window...')
                    Current_window.start()
                # update_time = timer()
                Current_window.update()
                # update_time = convert_ms(update_time)
                # draw_time = timer()
                Current_window.draw()
                # print(f'Update: {update_time}ms, Draw: {update_ms(draw_time)}ms')

                if Settings.active:  # SETTINGS
                    Menu.allow_screensaver = False
                    Settings.update_draw()
                else:
                    Menu.update()
                    Menu.draw()
            else:
                Display.fill(Colour['black'])
                txt = render_text('Miniplayer v2', 20, Colour['d grey'], center=CENTER)
                Display.blit(*txt)
                if type(Current_window) is LOCALWEATHER:
                    txt2 = render_text(Current_window.value['state'], 25, Colour['d grey'],
                                       midtop=(txt[1].centerx, txt[1].bottom + 15))
                    Display.blit(*txt2)
                    Display.blit(*render_text(Current_window.value['temp']['real'], 25, Colour['d grey'],
                                              midtop=(txt2[1].centerx, txt2[1].bottom + 10)))
                elif type(Current_window) is SPOTIFY:
                    Display.blit(*render_text('(Not playing)', 25, Colour['d grey'],
                                              midtop=(txt[1].centerx, txt[1].bottom + 15)))
                elif type(Current_window) is OCTOPRINT:
                    Display.blit(*render_text('(Not printing)', 25, Colour['d grey'],
                                              midtop=(txt[1].centerx, txt[1].bottom + 15)))

                Current_window.update()
                Menu.update()
            Mqtt.update()  # Update mqtt every loop
        except KeyboardInterrupt:
            return
        except (Exception, BaseException) as err:
            handle(err)
        except:
            print('main() failed -> unknown')

        if pg.time.get_ticks() >= Button_cooldown:  # Button cooldown reset
            Button_cooldown = 0

        if Info[0] and Info[2] > pg.time.get_ticks():  # Show info
            Display.blit(*render_text(Info[0], 30, Info[1], bold=True, midbottom=(CENTER[0], HEIGHT - 10)))

        if BACKLIGHT_CONTROL == 1:  # Display brightness through software
            Display.blit(Backlight.software_dim, (0, 0))

        Prev_mouse_pos = Mouse_pos
        pg.display.update()
        # print(f'Mainloop: {convert_ms(mainloop_time)}ms')


def quit_all():
    if Loading_ani:
        Loading_ani.stop()
    if Settings.active:
        Settings.save()
    Menu.stop()
    if Backlight:
        Backlight.stop()
    if Mqtt.connected:
        Mqtt.disconnect()
    pg.quit()
    quit()


# RUN
if __name__ == '__main__':
    try:  # Create log files for debugging
        if LOGGING:
            with open('miniplayer.log', 'a') as log:
                log.write(f"\n[{datetime.now().strftime('%x %X')}][NEW][Main] NEW_INSTANCE.\n")
                if DEBUG:
                    log.write(f"\n[{datetime.now().strftime('%x %X')}][DBG][Main] DEBUG ON.\n")
        with open('miniplayer_err.log', 'a') as error:
            error.write(f"\n[{datetime.now().strftime('%x %X')}][NEW][Main] NEW_INSTANCE.\n")
            if DEBUG:
                error.write(f"\n[{datetime.now().strftime('%x %X')}][DBG][Main] DEBUG ON.\n")

    except (Exception, BaseException) as error:
        handle(error, save=False)  # Do not save as error with logging
        LOGGING = False
    except:
        print('Failed to start log -> unknown')
        LOGGING = False

    if TOUCHSCREEN:  # Hide mouse if touchscreen
        pg.mouse.set_visible(False)

    draw_bg(txt=True)  # Splashscreen
    pg.display.update()
    for g_temp in range(0, 3):  # Wait 3s while allowing to quit
        try:
            pg.time.wait(1000)
        except KeyboardInterrupt:
            pg.quit()
            quit()

    g_temp = None  # Start backlight if enabled
    if BACKLIGHT_CONTROL == 2 and pigpio:
        try:
            g_temp = pigpio.pi()
            g_temp.set_mode(BACKLIGHT.pin, pigpio.OUTPUT)
            g_temp.hardware_PWM(BACKLIGHT.pin, BACKLIGHT.freq, 1000000)
        except (Exception, BaseException) as error:
            handle(error)
        except:
            print('Failed to start backlight -> unknown')

    try:  # Start all windows
        Loading_ani = LoadingAni()
        Loading_ani.start(msg='Connecting...', msg_colour=Colour['amber'])
        Mqtt = MQTT()
        Loading_ani.msg, Loading_ani.msg_colour = 'Loading Settings', Colour['l blue']  # Sets colour and msg of ani
        Settings = SETTINGS()
        Loading_ani.msg = 'Loading Menu'  # Update animation msg to see which window is loading
        Menu = MENU()
        Loading_ani.msg = 'Loading OctoPrint'
        Octo_print = OCTOPRINT()
        Loading_ani.msg = 'Loading LocalWeather'
        Local_weather = LOCALWEATHER()
        Loading_ani.msg = 'Loading Spotify'
        Spotify = SPOTIFY()
        if g_temp:
            g_temp.stop()
        Backlight = BACKLIGHT()
        Loading_ani.stop()
    except (Exception, BaseException) as error:
        handle(error)
        if Loading_ani:
            Loading_ani.stop()
        pg.quit()
        quit()
    except:
        print('Failed to start windows -> unknown')
        if Loading_ani:
            Loading_ani.stop()
        pg.quit()
        quit()

    Current_window = Local_weather  # Default window
    if DEBUG:  # Start main() without error handling if debugging
        try:
            main()
        except KeyboardInterrupt:  # If CTRL+C stop all windows and close
            quit_all()

    else:  # Start main() with error handling
        try:
            main()
        except KeyboardInterrupt:
            quit_all()
        except (Exception, BaseException) as error:
            handle(error)
        except:
            print('Unhandled exception -> main()')
        finally:  # Stop all windows and close after error handling
            quit_all()
