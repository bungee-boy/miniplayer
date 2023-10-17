import io
import json
import os
import platform
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
    pigpio = None

SYSTEM = platform.system()


# ----- SETTINGS -----
DEBUG = False  # Enable debugging features
LOGGING = False  # Enable logging features

NODERED_IP = '192.168.1.201'  # NodeRed IP address (REQUIRED)
NODERED_PORT = 1880  # NodeRed Port (default: 1880 )
NODERED_USER = str(hex(get_mac()))  # NodeRed Username (default: str(hex(get_mac())) )(MAC Address)

MQTT_IP = '192.168.1.201'  # MQTT IP address (REQUIRED)
MQTT_PORT = 1883  # MQTT Port (default: 1883 )
MQTT_USER = ''  # MQTT username (if required) (default: '' )
MQTT_PASS = ''  # MQTT password (if required) (default: '' )
MQTT_AUTO_RECONNECT = 900000  # MQTT reconnects after ms if no traffic (default: 900000 (15 minutes))

TOUCHSCREEN = False  # Enable touchscreen mode (hides cursor, no clicking ect)
BACKLIGHT_CONTROL = False  # Enable backlight control through GPIO pins (Requires pigpio!)
FPS = 16 if SYSTEM == 'Windows' else 8  # 16fps on Windows, 8 on Pi (default: 16 if SYSTEM == 'Windows' else 8 )
WIDTH, HEIGHT = 480, 320  # Width and height of the display / window (default: 480, 320 )
SCREENSAVER_DELAY = 120000  # Delay in milliseconds before screensaver activates (default: 120000 (2 minutes))
# ----- SETTINGS -----


# UNHANDLED INIT
if len(launch_opt) >= 1:  # LAUNCH OPTIONS
    if '--debug' in launch_opt:
        DEBUG = bool(int(launch_opt[launch_opt.index('--debug') + 1]))
        print('Forced DEBUG to {0}'.format('On' if DEBUG else 'Off'))
    if '--logging' in launch_opt:
        LOGGING = bool(int(launch_opt[launch_opt.index('--logging') + 1]))
        print('Forced LOGGING {0}'.format('On' if LOGGING else 'Off'))
    if '--nodered' in launch_opt:
        NODERED = str(launch_opt[launch_opt.index('--nodered') + 1])
        print('Forced NODERED to {0}'.format(NODERED))
    if '--noderedusername' in launch_opt:
        NODERED_USER = str(launch_opt[launch_opt.index('--noderedusername') + 1])
        print('Forced NODERED_USER to {0}'.format(NODERED_USER))
    if '--mqttusername' in launch_opt:
        MQTT_USER = str(launch_opt[launch_opt.index('--mqttusername') + 1])
        print('Forced MQTT_USER to {0}'.format(MQTT_USER))
    if '--mqttpassword' in launch_opt:
        MQTT_PASS = str(launch_opt[launch_opt.index('--mqttpassword') + 1])
        print('Forced MQTT_PASS to {0}'.format(MQTT_PASS))
    if '--fps' in launch_opt:
        FPS = str(launch_opt[launch_opt.index('--fps') + 1])
        print('Forced FPS to {0}fps'.format(FPS))
    if '--width' in launch_opt:
        WIDTH = str(launch_opt[launch_opt.index('--width') + 1])
        print('Forced WIDTH to {0}px'.format(WIDTH))
    if '--height' in launch_opt:
        HEIGHT = str(launch_opt[launch_opt.index('--height') + 1])
        print('Forced HEIGHT to {0}px'.format(HEIGHT))
    if '--screensaverdelay' in launch_opt:
        SCREENSAVER_DELAY = str(launch_opt[launch_opt.index('--screensaverdelay') + 1])
        print('Forced SCREENSAVER_DELAY to {0}ms'.format(SCREENSAVER_DELAY))

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
Last_err = None
Display = None
Clock = None
Bg = pg.surface.Surface((1, 1))
Menu = None
Loading_ani = None
Mqtt = None
Octo_print = None
Local_weather = None
Spotify = None
Backlight = None

Display = pg.display.set_mode((WIDTH, HEIGHT), flags=0 if SYSTEM == 'Windows' else pg.FULLSCREEN)
Clock = pg.time.Clock()
pg.display.set_caption('Miniplayer v2')
pg.init()


def handle(err: Exception or BaseException, save=True, repeat=False, traceback=True):
    global Last_err
    if err is KeyboardInterrupt:
        return
    msg = '{0}: {1}'.format(str(type(err)).replace("<class '", '').replace("'>", ''), err)
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
                with open('miniplayer.err.log', 'a') as file:
                    file.write(msg + '\n')
        except:
            print('Failed to log handled error -> unknown')


def load(img: str, size: tuple[int, int]):
    try:
        return pg.image.load(img)

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
    'bg': load('assets/bg.png', (480, 320)),
    'icon': load('assets/icon.ico', (32, 32)),
    'menu': {
        'menu': load('assets/menu.png', (32, 32)),
        'settings': load('assets/settings.png', (32, 32)),
        'cross': load('assets/cross.png', (32, 32))},
    'l weather': {
        'unknown': load('assets/unknown.png', (128, 128))},
    'spotify': {
        'logo': load('assets/spotify/logo.png', (295, 89)),
        'pause': (load('assets/spotify/pause_0.png', (32, 32)),
                  load('assets/spotify/pause_1.png', (32, 32))),
        'play': (load('assets/spotify/play_0.png', (32, 32)),
                 load('assets/spotify/play_1.png', (32, 32))),
        'shuffle': (load('assets/spotify/shuffle_0.png', (32, 32)),
                    load('assets/spotify/shuffle_1.png', (32, 32))),
        'playlist': load('assets/spotify/playlist_1.png', (32, 32)),
        'skip': (load('assets/spotify/skip_0.png', (32, 32)),
                 load('assets/spotify/skip_1.png', (32, 32))),
        'mute': load('assets/spotify/mute_1.png', (32, 32)),
        'vol 0': load('assets/spotify/vol_0_1.png', (32, 32)),
        'vol 50': load('assets/spotify/vol_50_1.png', (32, 32)),
        'vol 100': load('assets/spotify/vol_100_1.png', (32, 32)),
        'vol d': (load('assets/spotify/vol_decrease_0.png', (32, 32)),
                  load('assets/spotify/vol_decrease_1.png', (32, 32))),
        'vol i': (load('assets/spotify/vol_increase_0.png', (32, 32)),
                  load('assets/spotify/vol_increase_1.png', (32, 32)))}}

Bg = pg.transform.scale(Img['bg'], Display.get_size())
Bg.set_alpha(130)
pg.display.set_icon(Img['icon'])

if __name__ == '__main__':
    try:
        if LOGGING:
            with open('miniplayer.log', 'a') as log:
                log.write('\n[{0}][NEW][Main] NEW_INSTANCE.\n'.format(datetime.now().strftime('%x %X')))
                if DEBUG:
                    log.write('\n[{0}][DBG][Main] DEBUG ON.\n'.format(datetime.now().strftime('%x %X')))
        with open('miniplayer.err.log', 'a') as error:
            error.write('\n[{0}][NEW][Main] NEW_INSTANCE.\n'.format(datetime.now().strftime('%x %X')))
            if DEBUG:
                error.write('\n[{0}][DBG][Main] DEBUG ON.\n'.format(datetime.now().strftime('%x %X')))

    except (Exception, BaseException) as error:
        handle(error, save=False)  # Do not save as error with logging
        LOGGING = False
    except:
        print('Failed to start log -> unknown')
        LOGGING = False


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
            msg = '[{0}][{1}][{2}] {3}.'.format(datetime.now().strftime('%x %X'), cat if cat else 'LOG', self.name, msg)
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
                                                   msg, ' ({0})'.format(data) if data else '')
            print(msg)
            with open('miniplayer.err.log', 'a') as file:
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

    def ani(self, pos=CENTER, colour=Colour['white'], size=(100, 100), dot_size=20, speed=18):
        surf = Display
        self._running = True
        self._event = threading.Event()
        prev_frame_timestamp = pg.time.get_ticks()

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

                if prev_frame_timestamp != pg.time.get_ticks():  # Loop alpha for each dot
                    for dot in dots:
                        alpha = dot[0].get_alpha()
                        if alpha - speed < 0 and alpha != 0:
                            alpha = 0
                        elif alpha - speed <= 0:
                            alpha = 255
                        else:
                            alpha -= speed
                        dot[0].set_alpha(alpha)
                    prev_frame_timestamp = pg.time.get_ticks()

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
                    surf.blit(*render_text(self.msg, 20, colour=self.msg_colour, bold=True,
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
    pin = 18
    freq = 500

    def __init__(self):
        super().__init__('Backlight')
        if BACKLIGHT_CONTROL and pigpio:
            self._pi = pigpio.pi()
            self._pi.set_mode(self.pin, pigpio.OUTPUT)
        self.brightness = 0
        self.state = False
        Mqtt.subscribe(self._mqtt_response, self.receive, retain=True)
        self.set(100)
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
        if BACKLIGHT_CONTROL:
            self._pi.hardware_PWM(self.pin, self.freq, self.brightness * 10000)
        self.log('Set brightness to {0}'.format(self.brightness))

    def stop(self):
        self.set(0)
        if BACKLIGHT_CONTROL:
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
        self.right = self.right, self.right.get_rect(midright=(WIDTH - 20, 26))
        self.left = pg.transform.flip(self.right[0], True, False)
        self.left = self.left, self.left.get_rect(midleft=(20, 26))
        self.settings = Img['menu']['settings']
        self.settings = self.settings, self.settings.get_rect(midright=(WIDTH - 64, 26))
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
        self.shadow.set_alpha(180)
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
                    default_settings = {
                        "Timestamps": True,
                        "Device Info": True,
                        "Screensaver": True,
                        "Screensaver Info": True,
                        "Playlist Order": []}
                    json.dump(default_settings, file, indent=2)
            except:
                self.value = {
                    "Timestamps": True,
                    "Device Info": True,
                    "Screensaver": True,
                    "Screensaver Info": True,
                    "Playlist Order": []}
        except KeyError or TypeError:
            self.err('Failed to load settings -> key/type error')
        except PermissionError:
            self.err('Failed to load settings -> permission denied')
        except:
            self.err('Failed to load settings -> unknown')

    def save(self):
        try:
            with open('settings.json', 'w') as file:
                file.seek(0)
                json.dump(self.value, file, indent=2)
                file.truncate()
                self.log('Successfully saved settings to file')

        except FileNotFoundError:
            self.err("Failed to save settings -> 'settings.json' not found")
        except KeyError or TypeError:
            self.err('Failed to save settings -> key/type error')
        except PermissionError:
            self.err('Failed to save settings -> permission denied')
        except:
            self.err('Failed to save settings -> unknown')

    def update_draw(self, surf=Display):
        global Button_cooldown

        surf.blit(self.shadow, (0, 0))
        surf.blit(*render_text('Settings', 20, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(Menu.settings[0], Menu.right[1])
        # SCREENSAVER
        screensaver = render_text('Screensaver', 20, bold=True, midleft=(20, 100))
        surf.blit(*screensaver)
        # DEVICE INFO
        device_info = render_text('Device Info', 20, bold=True, midleft=(20, screensaver[1].bottom + 40))
        surf.blit(*device_info)
        # RELOAD PLAYLISTS
        playlists = render_text('Reload', 20, bold=True, midleft=(CENTER[0] + 10, 100))
        surf.blit(*playlists)
        # RECONNECT
        reconnect = render_text('Reconnect', 20, bold=True, midleft=(playlists[1].x, playlists[1].bottom + 40))
        surf.blit(*reconnect)
        # CLOSE
        close = render_text('Close', 20, bold=True, midleft=(reconnect[1].x, reconnect[1].bottom + 40))
        surf.blit(*close)
        # MQTT INFO
        surf.blit(*render_text('Connection: {0}   Username: {1}'.format(MQTT_IP, Mqtt.mac_address),
                               15, bold=True, midbottom=(CENTER[0], HEIGHT - 3)))

        screensaver = render_button(self.value['Screensaver'], center=(200, screensaver[1].centery))
        device_info = render_button(self.value['Device Info'], center=(200, device_info[1].centery))
        playlists = render_button(Colour['grey'], center=(410, playlists[1].centery))
        reconnect = render_button(Colour['amber'], center=(410, reconnect[1].centery))
        close = render_button(Colour['red'], center=(410, close[1].centery))

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
        self._mqtt.will_set('/miniplayer/connection/{0}'.format(self.mac_address), payload='disconnected')
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
                self.log('Set credentials: {0}, {1}'.format(MQTT_USER, MQTT_PASS))
            self._mqtt.will_set('/miniplayer/connection/{0}'.format(self.mac_address), payload='disconnected')
            self._mqtt.on_message = self._global_response
            self._mqtt.loop_start()
            self.log("Connecting to '{0}' with username '{1}'".format(MQTT_IP, self.mac_address))
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
                        self.err('Connection to {0} failed: Timed out'.format(MQTT_IP),
                                 data="username={0}".format(self.mac_address))
                        Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                        pg.time.wait(1500)
                        if ani:
                            Loading_ani.stop()
                        return False

            except Exception as err:  # If failure to connect
                self.err('Connection to {0} failed: {1}'.format(MQTT_IP, err),
                         data="username={0}".format(self.mac_address))
                Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                pg.time.wait(1500)
                if ani:
                    Loading_ani.stop()
                return False

            self.send('/miniplayer/connection/{0}'.format(self.mac_address), 'connected')  # If connected
            self.connected = True
            self._last_msg_time = pg.time.get_ticks() + MQTT_AUTO_RECONNECT
            self._mqtt.on_disconnect = self._set_reconnect
            Loading_ani.msg, Loading_ani.msg_colour = 'Connected!', Colour['green']
            pg.time.wait(1500)
            if ani:
                Loading_ani.stop()
            self.log("Connected to '{0}' with username '{1}'".format(MQTT_IP, self.mac_address))
            return True

    def disconnect(self):
        if self.connected or self._mqtt.is_connected():
            self.send('/miniplayer/connection/{0}'.format(self.mac_address), 'disconnected')
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
                self.log('Waiting for {0}s'.format(convert_s(retry_delay)))
                for count in range(0, round(retry_delay)):
                    Loading_ani.msg = 'Reconnecting (retry in {0})'.format(convert_s(retry_delay - count))
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
        if topics is str:
            topics = [topics]
        for topic in topics:
            if topic not in self.subscribed:
                self._mqtt.subscribe(topic)
                if retain:
                    self.retained.update({topic: response})
                self.subscribed.update({topic: response})
                self.log("Subscribed to '{0}'{1}".format(topic, ' (retained)' if retain else ''))
            else:
                self.log("Already subscribed to '{0}'{1}".format(topic, ' (retained)' if retain else ''), cat='WRN')

    def unsubscribe(self, topics: str or tuple, unsub_all=False):
        if unsub_all:
            for topic in self.subscribed:
                self._mqtt.unsubscribe(topic)
            self.subscribed = {}
            self.log('Unsubscribed from all topics.')
        else:
            if topics is str:  # If only one topic then pass as list
                topics = [topics]

            for topic in topics:
                self._mqtt.unsubscribe(topic)
                if topic in self.subscribed:
                    self.subscribed.pop(topic)
                    self.log("Unsubscribed from '{0}'".format(topic))
                else:
                    self.log("'{0}' not in subscriptions".format(topic), cat='WRN')

                if topic in self.retained:
                    self.retained.pop(topic)
                    self.log("Removed '{0}' from retained subscriptions".format(topic))

    def start_retained(self):
        self.log('Starting retained topics')
        for topic in self.retained:
            self.subscribe(topic, self.retained[topic])

    def send(self, topic: str, payload):
        msg = str(payload).replace("'", "\"")
        self._mqtt.publish(topic, msg)
        self.log("Sent '{0}' to '{1}'".format(msg, topic))

    def update(self):
        if self._last_msg_time < pg.time.get_ticks():  # If no msg since auto_reconnect ms
            self.log('Auto reconnect set', cat='WRN')
            self._set_reconnect()  # Automatically start reconnect as no traffic sent


class LOCALWEATHER(Window):
    _mqtt_active = '/miniplayer/weather/local/active/{0}'.format(MQTT.mac_address)
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
            '-°c', 64, bold=True, midleft=(self.icon[1].right + 20, self.icon[1].centery - 17))})
        self._data.update({'state': render_text(
            'Unknown', 32, topleft=(self._data['temp'][1].left, self._data['temp'][1].bottom + 5))})
        self._data.update({'temp f': render_text(
            'Feels like: -°c', 18, midtop=(130, self._data['state'][1].bottom + 25))})
        self._data.update({'temp r': render_text('L: -°c  H: -°c', 18, midtop=(350, self._data['temp f'][1].top))})
        self._data.update({'hum': render_text(
            'Humidity: -%', 18, midtop=(self._data['temp f'][1].centerx, self._data['temp f'][1].bottom + 15))})
        self._data.update({'rain': render_text(
            ('Snow' if self._snow else 'Rain') + ': -mm/h', 18,
            midtop=(self._data['temp r'][1].centerx, self._data['temp r'][1].bottom + 15))})
        self._data.update({'wind': render_text(
            'Wind: -mph, Unknown, -mph avg', 18, midtop=(CENTER[0], self._data['hum'][1].bottom + 15))})
        self._data.update({'clouds': render_text(
            'Clouds: -%', 18, midtop=(self._data['hum'][1].centerx, self._data['wind'][1].bottom + 15))})
        self._data.update({'vis': render_text(
            'Visibility: -km', 18, midtop=(self._data['rain'][1].centerx, self._data['wind'][1].bottom + 15))})
        self.value = {
            'wind': {'cardinal': 'Unknown', 'speed': 0, 'gust': 0},
            'clouds': 0, 'snow': None, 'state': 'Unknown', 'icon': 'unknown',
            'temp': {'real': 0, 'feels': 0, 'min': 0}, 'rain': 0, 'hum': 0, 'vis': 0}
        self.icon = Img['l weather']['unknown'], pg.rect.Rect((70, 40, 128, 128))

    def get_icon(self, icon: str):
        try:
            self.icon = pg.image.load(io.BytesIO(requests.get(
                'http://{0}:{1}/weather/icon?id={2}'.format(NODERED_IP, NODERED_PORT, icon)).content))
            self.icon = self.icon, self.icon.get_rect(topleft=(70, 40))
        except:
            self.err('Failed to load icon', data='id={0}'.format(icon))
            self.icon = Img['l weather']['unknown'], pg.rect.Rect((70, 40, 128, 128))

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                self.value = json.loads(message.payload.decode('utf-8'))
                self.value['state'] = self.value['state'].replace('Clouds', 'Cloudy')
                self._snow = self.value['snow']
                self.get_icon(self.value['icon'])
                self._data['temp'] = render_text(str(self.value['temp']['real']) + '°c', 64, bold=True,
                                                 midleft=(self.icon[1].right + 20, self.icon[1].centery - 17))
                self._data['state'] = render_text(self.value['state'], 32, topleft=(self._data['temp'][1].left,
                                                                                    self._data['temp'][1].bottom + 5))
                self._data['temp f'] = render_text('Feels like: {0}°c'.format(self.value['temp']['feels']),
                                                   18, midtop=(130, self._data['state'][1].bottom + 25))
                self._data['temp r'] = render_text('L: {0}°c  H: {1}°c'.format(self.value['temp']['min'],
                                                                               self.value['temp']['max']),
                                                   18, midtop=(350, self._data['temp f'][1].top))
                self._data['hum'] = render_text('Humidity: {0}%'.format(self.value['hum']), 18,
                                                midtop=(self._data['temp f'][1].centerx,
                                                        self._data['temp f'][1].bottom + 15))
                self._data['rain'] = render_text(
                    ('Snow' if self._snow else 'Rain') + ': {0}mm/h'.format(self.value['rain']),
                    18, midtop=(self._data['temp r'][1].centerx, self._data['temp r'][1].bottom + 15))
                self._data['wind'] = render_text('Wind: {0}mph, {1}, {2}mph avg'.format(
                    self.value['wind']['gust'], self.value['wind']['cardinal'], self.value['wind']['speed']), 18,
                    midtop=(CENTER[0], self._data['hum'][1].bottom + 15))
                self._data['clouds'] = render_text('Clouds: {0}%'.format(self.value['clouds']), 18,
                                                   midtop=(self._data['hum'][1].centerx,
                                                           self._data['wind'][1].bottom + 15))
                self._data['vis'] = render_text('Visibility: {0}%'.format(int((self.value['vis'] / 10000) * 100)), 18,
                                                midtop=(self._data['rain'][1].centerx,
                                                        self._data['wind'][1].bottom + 15))
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: {0}'.format(err)
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
        self.get_icon('unknown')
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell NodeRed weather is active
        self.active = True
        self.log('Started')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        self.log('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell NodeRed weather is not active
        Mqtt.unsubscribe(self._mqtt_response)
        Menu.allow_screensaver = True
        self.log('Allowed screensaver')
        self.active = False
        self.log('Stopped')

    def draw(self, surf=Display):
        surf.fill(Colour['black'])
        draw_bg(surf=surf)
        surf.blit(*render_text('Local weather', 20, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(*self.icon)
        surf.blit(*self._data['temp'])
        surf.blit(*self._data['state'])
        surf.blit(*self._data['temp f'])
        surf.blit(*self._data['temp r'])
        surf.blit(*self._data['hum'])
        surf.blit(*self._data['rain'])
        surf.blit(*self._data['wind'])
        surf.blit(*self._data['clouds'])
        surf.blit(*render_bar((140, 10), self.value['clouds'], 0, 100, fill_color=Colour['grey'],
                              midtop=(self._data['clouds'][1].centerx, self._data['clouds'][1].bottom + 10)))
        surf.blit(*self._data['vis'])
        surf.blit(*render_bar((140, 10), self.value['vis'], 0, 100, fill_color=Colour['grey'],
                              midtop=(self._data['vis'][1].centerx, self._data['vis'][1].bottom + 10)))
        surf.blit(*render_text(self.timestamp, 15, self._timestamp_color,
                               bold=True if 'ERR' in self.timestamp else False, bottomleft=(5, HEIGHT - 3)))

    def update(self):
        if ((not Mqtt.connected or self._mqtt_response not in Mqtt.subscribed) and
                self._timestamp_color != Colour['red']):
            self._timestamp_color = Colour['red']
            if Mqtt.connected:
                Mqtt.subscribe(self._mqtt_response, self.receive)


class SPOTIFY(Window):
    _mqtt_active = '/miniplayer/spotify/active/{0}'.format(MQTT.mac_address)
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
                surf = pg.transform.smoothscale(pg.image.load(io.BytesIO(response.content)), (80, 80))
                return surf
            except:
                self.err('Failed to load playlist image (url={0})'.format(url))
                return pg.surface.Surface((80, 80))
        else:
            self.err('Failed to get playlist image (code={0}, url={1})'.format(response.status_code, url))
            return pg.surface.Surface((80, 80))

    def _load_default(self):
        icon = pg.transform.scale(Img['spotify']['logo'], (106, 32))
        cover = pg.surface.Surface((128, 128))
        cover.set_alpha(150)
        self._data = {'icon': (icon, icon.get_rect(midtop=(CENTER[0], 10))),
                      'bg': None,
                      'album_cover': (cover, cover.get_rect(topleft=(20, 55))),
                      'pause': Img['spotify']['pause'],
                      'play': Img['spotify']['play'],
                      'shuffle': Img['spotify']['shuffle'],
                      'shuffle_active': Img['spotify']['shuffle'],
                      'playlist': Img['spotify']['playlist'],
                      'skip_l': (pg.transform.flip(Img['spotify']['skip'][0], True, False),
                                 pg.transform.flip(Img['spotify']['skip'][1], True, False)),
                      'skip_r': Img['spotify']['skip'],
                      'volume': {
                          'left': pg.rect.Rect(0, 0, 32, 32),
                          'right_1': pg.rect.Rect(0, 0, 32, 32),
                          'right_2': pg.rect.Rect(0, 0, 32, 32),
                          'm': Img['spotify']['mute'],
                          '0': Img['spotify']['vol 0'],
                          '50': Img['spotify']['vol 50'],
                          '100': Img['spotify']['vol 100'],
                          '-': Img['spotify']['vol d'],
                          '+': Img['spotify']['vol i']}}
        for index in range(0, len(self._data['shuffle_active'])):  # Duplicate shuffle as green from white
            pg.transform.threshold(self._data['shuffle_active'][index].copy(),
                                   self._data['shuffle_active'][index].copy(),
                                   search_color=(255, 255, 255), set_color=(24, 216, 97), inverse_set=True)
        surf = pg.surface.Surface((32, 32))
        self._data.update({'center': surf.get_rect(center=(CENTER[0], CENTER[1] + 60))})
        top = self._data['center'].top
        self._data.update({'left': surf.get_rect(topright=(self._data['center'].left - 32, top))})
        self._data.update({'far_left': surf.get_rect(topright=(self._data['left'].left - 32, top))})
        self._data.update({'right': surf.get_rect(topleft=(self._data['center'].right + 32, top))})
        self._data.update({'far_right': surf.get_rect(topleft=(self._data['right'].right + 32, top))})

        self._data.update({'plist': {
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
        pos = 15, 65, 80, 80, 3  # x, y, width, height, spacing
        temp = [{'cover': pg.surface.Surface((80, 80)).get_rect(topleft=(pos[0], pos[1]))},
                {'cover': pg.surface.Surface((80, 80)).get_rect(topleft=(pos[0], pos[1] + pos[3] + pos[4]))},
                {'cover': pg.surface.Surface((80, 80)).get_rect(topleft=(pos[0], pos[1] + ((pos[3] + pos[4]) * 2)))}]
        for index in range(0, len(temp)):
            temp[index].update({'play': pg.surface.Surface((32, 32)).get_rect(
                bottomleft=(temp[index]['cover'].right + 5, temp[index]['cover'].bottom - 5))})
            temp[index].update({'move_u': pg.surface.Surface((32, 32)).get_rect(
                midright=(Menu.right[1].left - 10, temp[index]['play'].centery))})
            temp[index].update({'move_d': pg.surface.Surface((32, 32)).get_rect(
                midright=(temp[index]['move_u'].left - 10, temp[index]['move_u'].centery))})
        self._data.update({'plist_rect': temp})

        self.value = {
            'playlist_uri': '',
            'progress_ms': 0,
            'progress': '0:00',
            'album': {
                'cover_url': '',
                'name': 'Unknown'},
            'artists': [{'name': 'Unknown'}],
            'duration_ms': 0,
            'duration': '-:--',
            'explicit': False,
            'song_name': 'Unknown',
            'is_playing': False,
            'shuffle': False}
        self.device_value = {
            'name': 'Unknown',
            'type': 'Unknown',
            'volume_percent': 0
        }

    def _get_playlists(self) -> bool:
        self.log('Fetching playlists..')
        try:  # Request data from NodeRed
            response = requests.get('http://{0}:{1}/spotify/playlists'.format(NODERED_IP, NODERED_PORT), timeout=10)
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
                        self.log("Removed invalid playlist from settings ('{0}')".format(key))
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
                        playlist['images'] = self._fetch_image(playlist['images'][(
                                len(playlist['images']) - 1) if len(playlist['images']) > 1 else 0]['url'])  # Load img
                        if os.path.isdir('playlists'):
                            try:
                                pg.image.save_extended(playlist['images'], '{0}.png'.format(playlist['id']), 'png')
                                shutil.move('{0}.png'.format(playlist['id']),
                                            'playlists/{0}.png'.format(playlist['id']))
                                self.log('Cached image (id:{0})'.format(playlist['id']))
                            except PermissionError:
                                self.err('Failed to cache image -> write permission denied')
                            except TypeError:
                                self.err('Failed to cache image -> type error')
                            except:
                                self.err('Failed to cache image -> unknown')
                    else:
                        playlist['images'] = cache[playlist['id']]
                        self.log('Loaded cache (id:{0})'.format(playlist['id']))

                self.log('Loaded playlist images (took {0}s)'.format(round(timer() - temp, 2)))
                return True

            except Exception as err:
                self._playlists = []
                handle(err)
                self.err('Playlist ordering failed')
                return False
        else:
            self._playlists = []
            self.err('Playlist fetch failed (code={0} url={1})'.format(
                response.status_code, 'http://{0}:{1}/spotify/playlists'.format(NODERED_IP, NODERED_PORT)))
            return False

    def _update_playlists(self, uid: str):
        response = requests.get('http://{0}:{1}/spotify/playlists?id={2}'.format(NODERED_IP, NODERED_PORT, uid))
        if response.status_code == 200:  # Fetch playlist
            try:
                playlist = json.load(io.BytesIO(response.content))  # Decode response
                if playlist['id'] == 'spotify:user:ag.bungee:collection':
                    return False
                else:
                    self._playlists.append(playlist)
                    Settings.value['Playlist Order'].append(playlist['id'])
                    Settings.save()
                    playlist['images'] = self._fetch_image(playlist['images'][len(playlist['images']) - 1]['url'])
                    self.log('Playlist updated (id={0}, name={1})'.format(uid, playlist['name']))
                    return playlist['id']

            except:
                self.err('Failed to decode playlist during update (id={0})')
                return False
        else:
            if response.status_code != 500:
                self.err('Failed to update playlists (code={0}, id={1})'.format(response.status_code, uid))
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
                    cover = pg.transform.smoothscale(pg.image.load(io.BytesIO(
                        requests.get(msg['album']['cover_url']).content)), (480, 480))
                    cover.set_alpha(80)
                    self._data['bg'] = cover, cover.get_rect(center=CENTER)
                    cover = pg.transform.smoothscale(cover, (128, 128))
                    cover.set_alpha(None)
                    self._data['album_cover'] = cover, cover.get_rect(topleft=(20, 55))

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
                    self.timestamp = 'ERR: {0}'.format(err)
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
                    self.timestamp = 'ERR: {0}'.format(err)
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
        Mqtt.send(self._mqtt_active, True)  # Tell NodeRed spotify is active
        self.active = True
        self.log('Started')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        self.log('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell NodeRed spotify is not active
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
            surf.blit(*render_text('Not Playing', 50, bold=True, center=CENTER))
        else:
            txt = render_text(self.value['artists'][0]['name'], 20,
                              midleft=(self._data['album_cover'][1].right + 20, self._data['album_cover'][1].centery))
            surf.blit(*txt)  # SONG DETAILS
            surf.blit(*render_text(self.value['song_name'], 20, bold=True, bottomleft=(txt[1].left, txt[1].top - 20)))
            surf.blit(*render_text(self.value['album']['name'], 20, topleft=(txt[1].left, txt[1].bottom + 20)))

            surf.blit(self._data['playlist'], self._data['far_left'])  # BUTTONS
            surf.blit(self._data['skip_l'][1 if self._pending_action != 'rewind' else 0], self._data['left'])
            surf.blit(self._data['pause' if self.value['is_playing'] else 'play']
                      [1 if self._pending_action != ('pause' if self.value['is_playing'] else 'play') else 0],
                      self._data['center'])
            surf.blit(self._data['skip_r'][1 if self._pending_action != 'skip' else 0], self._data['right'])
            surf.blit(self._data['shuffle_active' if self.value['shuffle'] else 'shuffle']
                      [1 if self._pending_action != 'shuffle' else 0], self._data['far_right'])

            bar = render_bar((300, 10), self.value['progress_ms'], 0, self.value['duration_ms'],  # PROGRESS BAR
                             midtop=(CENTER[0], self._data['center'].bottom + 20))
            surf.blit(*bar)
            surf.blit(*render_text(self.value['progress'], 15, Colour['white'], bold=True,  # PROGRESS
                                   midright=(bar[1].left - 15, bar[1].centery + 1)))
            surf.blit(*render_text(self.value['duration'], 15, Colour['white'], bold=True,  # DURATION
                                   midleft=(bar[1].right + 15, bar[1].centery + 1)))

            bar = render_bar((100, 8), self.device_value['volume_percent'], 0, 100,  # VOLUME BAR
                             midtop=(CENTER[0], bar[1].bottom + 20))
            surf.blit(*bar)
            self._data['volume']['left'].midright = bar[1].left - 10, bar[1].centery  # VOLUME ICON
            self._data['volume']['right_1'].midleft = bar[1].right + 10, bar[1].centery
            self._data['volume']['right_2'].midleft = self._data['volume']['right_1'].right + 10, bar[1].centery
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
            temp = render_text('Playlists', 25, bold=True, center=(CENTER[0], Menu.right[1].centery - 5))
            surf.blit(*temp)
            if self._playlists:  # If there are playlists
                if self._active_playlist and 'name' in self._active_playlist.keys():
                    surf.blit(*render_text('Currently playing: {0}'.format(self._active_playlist['name']), 20,
                                           midtop=(CENTER[0], temp[1].bottom + 5)))
                for index in range(0, len(self._data['plist_rect']) if len(
                        self._playlists) > len(self._data['plist_rect']) else len(self._playlists)):  # For shown plists
                    rect = self._data['plist_rect'][index]
                    index += self._data['plist']['page'] * len(self._data['plist_rect'])  # Offset index by page
                    if index >= len(self._playlists):
                        break
                    plist = self._playlists[index]

                    surf.blit(plist['images'], rect['cover'])  # Image
                    surf.blit(*render_text(plist['name'], 21, bold=True,  # Name
                                           topleft=(rect['cover'].right + 6, rect['cover'].top + 10)))
                    surf.blit(self._data['play'][1] if self._active_playlist != plist else
                              self._data['plist']['pause'], rect['play'])  # Play button
                    surf.blit(*render_text('{0} Songs'.format(plist['tracks']['total']), 20,
                                           midleft=(rect['play'].right + 5, rect['play'].centery)))  # Song count
                    surf.blit(self._data['plist']['move_d'][1 if index < len(
                              self._playlists) - 1 else 0], rect['move_d'])
                    surf.blit(self._data['plist']['move_u'][1 if index > 0 else 0], rect['move_u'])

                surf.blit(self._data['plist']['scroll_u'][1 if self._data['plist']['page'] > 0 else 0],
                          self._data['plist']['scroll_u'][2])
                surf.blit(self._data['plist']['scroll_d'][1 if self._data['plist']['page'] <
                          floor(len(self._playlists) / len(self._data['plist_rect'])) else 0],
                          self._data['plist']['scroll_d'][2])

        if Settings.value['Device Info']:
            surf.blit(*render_text(self.device_value['name'], 15, Colour['grey'], bottomright=(WIDTH - 5, HEIGHT - 3)))
        if self._timeout_time > pg.time.get_ticks() and not self.show_playlists:  # Action status
            set_info('Action timed out!', Colour['red'])
        if not self.show_playlists:  # Timestamp
            surf.blit(*render_text(self.timestamp, 15, self._timestamp_color, bottomleft=(5, HEIGHT - 3)))

    def update(self):
        global Button_cooldown
        if (self.value['is_playing'] or self.show_playlists) and Menu.allow_screensaver and not Settings.active:
            Menu.allow_screensaver = False
            self.log('Disabled screensaver')
        elif (not self.value['is_playing'] and not self.show_playlists and not Menu.allow_screensaver and
              not Settings.active):
            Menu.allow_screensaver = True
            self.log('Allowed screensaver')

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
            elif self._data['volume']['right_1'].collidepoint(Mouse_pos) and self.device_value['volume_percent'] > 0:
                action = 'decrease_volume'
                self._prev_value = self.device_value['volume_percent']
            elif self._data['volume']['right_2'].collidepoint(Mouse_pos) and self.device_value['volume_percent'] < 100:
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
                self.log('{0} requested'.format(action.title()))

            if self._data['far_left'].collidepoint(Mouse_pos):  # PLAYLIST (open)
                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                Menu.allow_controls = False
                self.show_playlists = True

        if self._pending_action == 'pause' and self.value['is_playing'] != self._prev_value or \
                self._pending_action == 'play' and self.value['is_playing'] != self._prev_value or \
                self._pending_action == 'skip' and self.value['song_name'] != self._prev_value or \
                self._pending_action == 'rewind' and self.value['song_name'] != self._prev_value or \
                self._pending_action == 'increase_volume' and \
                self.device_value['volume_percent'] > self._prev_value or \
                self._pending_action == 'decrease_volume' and \
                self.device_value['volume_percent'] < self._prev_value or \
                self._pending_action == 'shuffle' and self.value['shuffle'] != self._prev_value:
            self.log('{0} confirmed'.format(self._pending_action.title()))
            set_info('{0} confirmed'.format(self._pending_action.title().replace('_', ' ')))
            self._action_time = 0
            self._prev_value = None
            self._pending_action = None

        if self._action_time and pg.time.get_ticks() >= self._action_time:
            self.err('{0} timed out'.format(self._pending_action))
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
                            self.log("Playlist '{0}' ({1}) requested".format(plist['id'], plist['name']))
                        elif rect['move_u'].collidepoint(Mouse_pos) and index > 0:  # Move up
                            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                            self._playlists[index] = self._playlists[index - 1]
                            self._playlists[index - 1] = plist
                            self.log("Move playlist '{0}' ({1}) up".format(plist['id'], plist['name']))
                        elif rect['move_d'].collidepoint(Mouse_pos) and index < len(self._playlists) - 1:  # Move down
                            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                            self._playlists[index] = self._playlists[index + 1]
                            self._playlists[index + 1] = plist
                            self.log("Move playlist '{0}' ({1}) down".format(plist['id'], plist['name']))


class OCTOPRINT(Window):
    _mqtt_active = '/miniplayer/octoprint/active/{0}'.format(MQTT.mac_address)

    def __init__(self):
        super().__init__('OctoPrint')
        temp = '/miniplayer/octoprint/'
        self._mqtt_responses = temp + 'progress/printing', temp + 'position', temp + 'temperature'
        self._data = {}
        self.value = {}
        self.printing = False
        self._load_default()
        Menu.windows.append(self)

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
                self._data['state'] = render_text('{0}: {1}%'.format(self.value['state']['text'],
                                                                     round(self.value['progress']['completion'])),
                                                  25, bold=True, topleft=(15, Menu.left[1].bottom + 15))
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
                    self.timestamp = 'ERR: {0}'.format(err)
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
                    self.timestamp = 'ERR: '.format(err)
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
                    self.timestamp = 'ERR: {0}'.format(err)
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
        Mqtt.send(self._mqtt_active, True)  # Tell NodeRed octoprint is active
        self.active = True
        self.log('Started.')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        Mqtt.send(self._mqtt_active, False)  # Tell NodeRed octoprint is not active
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


def convert_s(sec: int):
    minutes = 0
    hours = 0
    if sec >= 60:
        minutes = sec // 60
        sec -= minutes * 60
        if sec < 10:
            sec = '0{0}'.format(sec)
    elif sec < 10:
        sec = '0{0}'.format(sec)
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


def render_text(text: str or int, size: int, colour=Colour['white'], bold=False, **kwargs):
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
               fill_color=Colour['white'], border_width=2, border_radius=7, border_color=Colour['white'], **kwargs):
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


def render_button(state: bool or tuple[int, int, int] or None, surf=Display, **kwargs):
    surface = pg.surface.Surface((64, 32))
    surface.fill(Colour['key'])
    surface.set_colorkey(Colour['key'])
    rect = surface.get_rect(**kwargs)

    # shading
    shade = pg.surface.Surface((64, 32))
    shade.fill(Colour['key'])
    shade.set_colorkey(Colour['key'])
    shade.set_alpha(100)
    if state is tuple:
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
    surf.blit(shade, rect.topleft)

    # nub
    if state and state is bool:
        pg.draw.circle(surface, Colour['white'], (48, 16), 12, width=2)
        pg.draw.circle(surface, Colour['green'], (48, 16), 10)
    elif state is None or state is tuple:
        pg.draw.circle(surface, Colour['white'], (16, 16), 12, width=2, draw_top_left=True, draw_bottom_left=True)
        surface.blit(*render_text('Press', 15, bold=True, center=surface.get_rect().center))
        pg.draw.circle(surface, Colour['white'], (48, 16), 12, width=2, draw_top_right=True, draw_bottom_right=True)
    else:
        pg.draw.circle(surface, Colour['white'], (16, 16), 12, width=2)
        pg.draw.circle(surface, Colour['red'], (16, 16), 10)

    # outline
    pg.draw.circle(surface, Colour['white'], (16, 16), 16, width=2, draw_top_left=True, draw_bottom_left=True)
    pg.draw.line(surface, Colour['white'], (16, 0), (48, 0), width=2)
    pg.draw.line(surface, Colour['white'], (16, 30), (48, 30), width=2)
    pg.draw.circle(surface, Colour['white'], (48, 16), 16, width=2, draw_top_right=True, draw_bottom_right=True)

    surf.blit(surface, rect.topleft)
    return rect


def draw_bg(txt=False, surf=Display):
    surf.blit(Bg, (0, 0))
    if txt:
        txt = render_text('Miniplayer', 32, bold=True, center=CENTER)
        surf.blit(*txt)
        surf.blit(*render_text('v2.0', 16, midtop=(txt[1].centerx, txt[1].bottom + 10)))


def set_info(txt: str, colour=Colour['green'], timeout=2000):
    global Info  # txt, colour, ms
    if not Info[0] or Info[2] < pg.time.get_ticks():  # If not showing or timeout
        Info = txt, colour, pg.time.get_ticks() + timeout


def main():
    global Current_window, Button_cooldown, Mouse_pos, Prev_mouse_pos
    while True:  # Forever loop
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
                Current_window.update()
                Current_window.draw()

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
                if Current_window is LOCALWEATHER:
                    txt2 = render_text(Current_window.value['state'], 25, Colour['d grey'],
                                       midtop=(txt[1].centerx, txt[1].bottom + 15))
                    Display.blit(*txt2)
                    Display.blit(*render_text(Current_window.value['temp']['real'], 25, Colour['d grey'],
                                              midtop=(txt2[1].centerx, txt2[1].bottom + 10)))
                elif Current_window is SPOTIFY:
                    Display.blit(*render_text('(Not playing)', 25, Colour['d grey'],
                                              midtop=(txt[1].centerx, txt[1].bottom + 15)))
                elif Current_window is OCTOPRINT:
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
            Display.blit(*render_text(Info[0], 15, Info[1], bold=True, midbottom=(CENTER[0], HEIGHT)))
        Prev_mouse_pos = Mouse_pos
        pg.display.update()


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
    if TOUCHSCREEN:
        pg.mouse.set_visible(False)
    draw_bg(txt=True)
    pg.display.update()
    pg.time.wait(5000)
    g_temp = None
    if SYSTEM != 'Windows' and pigpio:
        try:
            g_temp = pigpio.pi()
            g_temp.set_mode(BACKLIGHT.pin, pigpio.OUTPUT)
            g_temp.hardware_PWM(BACKLIGHT.pin, BACKLIGHT.freq, 1000000)
        except (Exception, BaseException) as error:
            handle(error)
        except:
            print('Failed to start backlight -> unknown')
    try:
        Loading_ani = LoadingAni()
        Loading_ani.start(msg='Connecting...', msg_colour=Colour['amber'])
        Mqtt = MQTT()
        Loading_ani.msg, Loading_ani.msg_colour = 'Loading Settings', Colour['l blue']
        Settings = SETTINGS()
        Loading_ani.msg = 'Loading Menu'
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

    Current_window = Local_weather  # Local_weather
    if DEBUG:
        try:
            main()
        except KeyboardInterrupt:
            quit_all()
    else:
        try:
            main()
        except KeyboardInterrupt:
            pass
        except (Exception, BaseException) as error:
            handle(error)
        except:
            print('main() Unhandled exception -> unknown')
        finally:
            quit_all()
