import io
import os
import json
import shutil
import threading
from time import strftime
from math import floor
from timeit import default_timer as timer
import paho.mqtt.client as mqtt_client
import pygame as pg
import requests
from platform import system

from lib.logger import Logging
from lib.loader import ConfigLoader, ImgLoader

try:
    import pigpio
except ImportError:
    pigpio = False


# CONFIG / LOADING
Conf = ConfigLoader()
Img = ImgLoader()

WIDTH, HEIGHT = Conf.Resolution
CENTER = WIDTH // 2, HEIGHT // 2
Button_cooldown = 0
Button_cooldown_length = 500 if Conf.Touchscreen else 100
Mouse_pos = -1, -1
Prev_mouse_pos = -2, -2
Loaded_fonts = {}
Colour = {'key': (1, 1, 1), 'black': (0, 0, 0), 'white': (255, 255, 255), 'grey': (155, 155, 155),
          'd grey': (80, 80, 80), 'red': (251, 105, 98), 'yellow': (252, 252, 153), 'l green': (121, 222, 121),
          'green': (18, 115, 53), 'amber': (200, 140, 0), 'l blue': (3, 140, 252)}
Info = '', Colour['white'], 2000  # txt, colour, ms
Loading_ani = None
Menu = None

Display = pg.display.set_mode(Conf.Resolution, flags=pg.FULLSCREEN if Conf.Fullscreen else 0, display=Conf.Screen)
Img = ImgLoader()

Img.img.update({'bg': Img.load('assets/bg.jpg', (1280, 720), keep_alpha=False)})
Img.img.update({'icon': Img.load('assets/icon.ico')})
Bg = pg.transform.scale(Img.img['bg'], (WIDTH, HEIGHT))
Bg.set_alpha(130)
Clock = pg.time.Clock()
pg.display.set_caption('Miniplayer v2')
pg.display.set_icon(Img.img['icon'])
pg.init()

try:
    pg.font.Font('assets/thinfont.ttf', 15)
except Exception or BaseException as error:
    Logging('Main').handle(error, trace=False)
try:
    pg.font.Font('assets/boldfont.ttf', 15)
except Exception or BaseException as error:
    Logging('Main').handle(error, trace=False)


def folder():
    return "\\" if system() == "Windows" else "/"


# CLASSES
class Window(Logging):
    def __init__(self, name: str):
        super().__init__(name)
        self.active = False
        self.message = {}
        self.timestamp = '--:--'
        self._timestamp_color = Colour['yellow']

    def _load_default(self):
        pass

    def receive(self, client, data, message: mqtt_client.MQTTMessage):
        pass

    def start(self):
        pass

    def stop(self):
        Menu.allow_screensaver = True
        self.info('Allowed screensaver')

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

                Clock.tick(Conf.Fps)

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
            self.handle(err)
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
            self.info('Started')
        else:
            self.warn('Prevented multiple threads from starting')

    def stop(self):
        self._event.set()
        if self.thread.is_alive():
            self.thread.join()
        self.msg = ''
        self.msg_colour = None
        self.thread = threading.Thread(name='loading ani', target=self.ani)
        self._running = False
        self.info('Stopped')


class BACKLIGHT(Window):
    _mqtt_request = 'miniplayer/backlight/request'
    _mqtt_response = 'miniplayer/backlight'
    pin = Conf.Backlight_pin
    freq = 500

    def __init__(self):
        super().__init__('Backlight')
        if Conf.Backlight == 2 and pigpio:
            self._pi = pigpio.pi()
            self._pi.set_mode(self.pin, pigpio.OUTPUT)
        self.software_dim = pg.surface.Surface((WIDTH, HEIGHT))
        self.brightness = 0
        self.state = False
        Mqtt.subscribe(self._mqtt_response, self.receive, retain=True)
        self.info(f"Running in mode {Conf.Backlight}")
        self.set(100)
        if Conf.Backlight:  # If enabled, request from Node-Red
            Mqtt.send(self._mqtt_request, True)

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                msg = json.loads(message.payload.decode())
                if msg['brightness'] != self.brightness:
                    self.set(msg['brightness'])
            except:
                self.err('MQTT receive error')
                self.set(100)

    def set(self, brightness: int):
        brightness += Conf.Brightness_offset  # Add offset to brightness
        self.brightness = 100 if brightness > 100 else (0 if brightness < 0 else brightness)  # Constrain to 0-100
        if Conf.Backlight == 2 and pigpio:
            self._pi.hardware_PWM(self.pin, self.freq, self.brightness * 10000)
        elif Conf.Backlight == 1:  # Software dimming
            self.brightness = Conf.Min_brightness if self.brightness < Conf.Min_brightness else self.brightness  # Limit
            self.software_dim.set_alpha(255 - round(self.brightness / 100 * 255))
        self.info(f"Set brightness to {self.brightness}")

    def stop(self):
        self.set(0)
        if Conf.Backlight == 2 and pigpio:
            self._pi.stop()
        self.info('Stopped')


class MENU(Window):
    screensaver = False
    allow_screensaver = True
    allow_controls = True

    def __init__(self):
        super().__init__('Menu')
        Img.img.update({'menu': {
            'menu': Img.load('assets/menu.png', (50, 50)),
            'settings': Img.load('assets/settings.png', (50, 50)),
            'cross': Img.load('assets/cross.png', (50, 50)),
            'on': Img.load('assets/on.png', (50, 50)),
            'off': Img.load('assets/off.png', (50, 50)),
            'none': Img.load('assets/none.png', (50, 50))}})
        self.windows = []
        self._retained_windows = []
        self.right = Img.img['menu']['menu']
        self.right = self.right, self.right.get_rect(midright=(WIDTH - 20, 40))
        self.left = pg.transform.flip(self.right[0], True, False)
        self.left = self.left, self.left.get_rect(midleft=(20, 40))
        self.settings = Img.img['menu']['settings']
        self.settings = self.settings, self.settings.get_rect(midright=(WIDTH - 80, 40))
        self.cross = Img.img['menu']['cross']
        self._screensaver_timer = 0

    @staticmethod
    def set_window(window):
        global Current_window
        Current_window.stop()
        Current_window = window
        Current_window.start()

    def start_retained(self):
        if self._retained_windows:
            self.info('Starting windows')
            for window in self._retained_windows:
                window.start()
                self._retained_windows.remove(window)

    def stop(self, retain=False):
        self.info('Stopping windows')
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
            self._screensaver_timer = pg.time.get_ticks() + Conf.Screensaver_delay
        if not self.screensaver and pg.time.get_ticks() >= self._screensaver_timer and \
                self.allow_screensaver and Settings.value['Screensaver']:
            self.screensaver = True
            self.info('Started screensaver')
        elif self.screensaver and pg.time.get_ticks() < self._screensaver_timer:
            self.screensaver = False
            self.info('Stopped screensaver')

        # Page navigation
        if (not Conf.Touchscreen and not pg.mouse.get_pressed()[0] or
                Conf.Touchscreen and Mouse_pos == Prev_mouse_pos) or Button_cooldown:
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
        surf = Img.img['menu']['on']
        self._data = {}
        self._data.update({'screensaver': surf.get_rect(midleft=(Menu.left[1].centerx + 50, 150))})
        self._data.update({'device_info': surf.get_rect(midleft=(self._data['screensaver'].left,
                                                                 self._data['screensaver'].centery + 100))})
        self._data.update({'playlists': surf.get_rect(midleft=(self._data['device_info'].left,
                                                               self._data['device_info'].centery + 100))})
        self._data.update({'reconnect': surf.get_rect(midleft=(self._data['playlists'].left,
                                                               self._data['playlists'].centery + 100))})
        self._data.update({'quit': surf.get_rect(midleft=(self._data['reconnect'].left,
                                                          self._data['reconnect'].centery + 100))})
        self.load()

    def load(self):
        try:
            with open('settings.json') as file:
                self.value = json.load(file)
                self.info('Successfully loaded settings from file')

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
                self.handle(err)
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
            self.handle(err)
        except:
            self.err('Unhandled exception -> SETTINGS.load()')

    def save(self):
        try:
            with open('settings.json', 'w') as file:
                file.seek(0)
                json.dump(self.value, file, indent=2)
                file.truncate()
                self.info('Successfully saved settings to file')
        except Exception or BaseException as err:
            self.handle(err)
        except:
            self.err('Unhandled exception -> SETTINGS.save()')

    def update_draw(self, surf=Display):
        global Button_cooldown

        surf.blit(self.shadow, (0, 0))
        surf.blit(*render_text('Settings', 50, bold=True, center=(CENTER[0], Menu.right[1].centery)))
        surf.blit(Menu.settings[0], Menu.right[1])

        # screensaver = render_button(self.value['Screensaver'], midleft=(Menu.left[1].centerx + 50, 150))
        # device_info = render_button(self.value['Device Info'], midleft=(screensaver.left, screensaver.centery + 100))
        # playlists = render_button(Colour['grey'], midleft=(device_info.left, device_info.centery + 100))
        # reconnect = render_button(Colour['amber'], midleft=(playlists.left, playlists.centery + 100))
        # close = render_button(Colour['red'], midleft=(reconnect.left, reconnect.centery + 100))

        temp = 30  # Pad X
        # SCREENSAVER
        surf.blit(Img.img['menu']['on' if self.value['Screensaver'] else 'off'], self._data['screensaver'])
        surf.blit(*render_text('Screensaver', 35, bold=True,
                               midleft=(self._data['screensaver'].right + temp, self._data['screensaver'].centery)))
        # DEVICE INFO
        surf.blit(Img.img['menu']['on' if self.value['Device Info'] else 'off'], self._data['device_info'])
        surf.blit(*render_text('Device Info', 35, bold=True,
                               midleft=(self._data['device_info'].right + temp, self._data['device_info'].centery)))
        # RELOAD PLAYLISTS
        surf.blit(Img.img['menu']['none'], self._data['playlists'])
        surf.blit(*render_text('Reload playlists', 35, bold=True,
                               midleft=(self._data['playlists'].right + temp, self._data['playlists'].centery)))
        # RECONNECT
        surf.blit(Img.img['menu']['none'], self._data['reconnect'])
        surf.blit(*render_text('Reconnect', 35, bold=True,
                               midleft=(self._data['reconnect'].right + temp, self._data['reconnect'].centery)))
        # QUIT
        surf.blit(Img.img['menu']['none'], self._data['quit'])
        surf.blit(*render_text('Quit', 35, bold=True,
                               midleft=(self._data['quit'].right + temp, self._data['quit'].centery)))
        # MQTT INFO
        surf.blit(*render_text(f"Connection: {Conf.Mqtt_ip}   Username: {Mqtt.mac_address}", 30, bold=True,
                               midbottom=(CENTER[0], HEIGHT - 10)))

        if (not Conf.Touchscreen and not pg.mouse.get_pressed()[0] or
                Conf.Touchscreen and Mouse_pos == Prev_mouse_pos) or Button_cooldown:
            return
        elif Menu.right[1].collidepoint(Mouse_pos):
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False
            Menu.allow_screensaver = True
            self.save()
        elif self._data['screensaver'].collidepoint(Mouse_pos):  # Screensaver
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.value['Screensaver'] = False if self.value['Screensaver'] else True
        elif self._data['device_info'].collidepoint(Mouse_pos):  # Device info
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.value['Device Info'] = False if self.value['Device Info'] else True
        elif self._data['playlists'].collidepoint(Mouse_pos):  # Reload
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False  # Close settings automatically
            if Spotify.reload_playlists():
                set_info('Reloaded playlists')
            else:
                set_info('Playlist reload failed!', Colour['red'])
        elif self._data['reconnect'].collidepoint(Mouse_pos):  # Reconnect
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False  # Close settings automatically
            Mqtt.reconnect()
        elif self._data['quit'].collidepoint(Mouse_pos):  # Quit
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            raise KeyboardInterrupt('Quit button pressed')


class MQTT(Window):
    mac_address = Conf.Node_red_user
    _mqtt_window = 'miniplayer/window'

    def __init__(self):
        super().__init__('MQTT')
        self.connected = False
        self.retained = {}  # {'topic': response()}
        self.subscribed = {}
        self._last_msg_time = pg.time.get_ticks() + Conf.Mqtt_auto_reconnect
        self._mqtt = mqtt_client.Client(self.mac_address)
        self._mqtt.will_set(f"/miniplayer/connection/{self.mac_address}", payload='disconnected')
        self._mqtt.on_message = self._global_response
        self._mqtt.loop_start()
        self.reconnect_pending = not self.connect()  # If not connected on boot, set to start reconnect.

    def _set_reconnect(self, client=None, data=None, message=None):
        if client or data or message:
            pass
        self.reconnect_pending = True

    def _global_response(self, client, data, message):
        self._last_msg_time = pg.time.get_ticks() + Conf.Mqtt_auto_reconnect  # Update last msg time
        if message.topic == self._mqtt_window and Settings.value['WINDOW_CHANGE']:  # If topic is to change windows
            pass
        else:
            for topic in self.subscribed:
                if topic == message.topic:  # Find corresponding topic
                    self.subscribed[topic](client, data, message)  # Run appropriate response function on data
                    break

    def connect(self, ani=False):
        if not self.connected or not self._mqtt.is_connected():
            self.connected = False
            self._mqtt.loop_stop()
            self._mqtt.reinitialise(self.mac_address)
            if Conf.Mqtt_user and Conf.Mqtt_pass:  # If username and password
                self._mqtt.username_pw_set(Conf.Mqtt_user, Conf.Mqtt_pass)
                self.debug(f"Set credentials: {Conf.Mqtt_user}, {Conf.Mqtt_pass}")
            self._mqtt.will_set(f"/miniplayer/connection/{self.mac_address}", payload='disconnected')
            self._mqtt.on_message = self._global_response
            self._mqtt.loop_start()
            self.info(f"Connecting to '{Conf.Mqtt_ip}' with username '{self.mac_address}'")
            if ani:
                Loading_ani.start(msg='Connecting...', msg_colour=Colour['amber'])
            else:
                Loading_ani.msg, Loading_ani.msg_colour = 'Connecting...', Colour['amber']
            temp = timer()
            try:
                self._mqtt.connect(Conf.Mqtt_ip, port=Conf.Mqtt_port)  # Start connection
                while not self._mqtt.is_connected():  # Wait for MQTT to connect
                    pg.time.wait(250)
                    if round(timer() - temp, 2) >= 10:  # Timeout after 10s
                        self.err(f"Connection to {Conf.Mqtt_ip} failed: Timed out", data=f"username={self.mac_address}")
                        Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                        pg.time.wait(1500)
                        if ani:
                            Loading_ani.stop()
                        return False

            except Exception as err:  # If failure to connect
                self.err(f"Connection to {Conf.Mqtt_ip} failed: {err}", data=f"username={self.mac_address}")
                Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                pg.time.wait(1500)
                if ani:
                    Loading_ani.stop()
                return False

            self.send(f"/miniplayer/connection/{self.mac_address}", 'connected')  # If connected
            self.connected = True
            self._last_msg_time = pg.time.get_ticks() + Conf.Mqtt_auto_reconnect
            self._mqtt.on_disconnect = self._set_reconnect
            Loading_ani.msg, Loading_ani.msg_colour = 'Connected!', Colour['green']
            pg.time.wait(1500)
            if ani:
                Loading_ani.stop()
            self.info(f"Connected to '{Conf.Mqtt_ip}' with username '{self.mac_address}'")
            return True

    def disconnect(self):
        if self.connected or self._mqtt.is_connected():
            self.send(f"/miniplayer/connection/{self.mac_address}", 'disconnected')
            self.unsubscribe(None, unsub_all=True)
            self.connected = False

    def reconnect(self):
        self.info('Reconnecting..')
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
                self.info(f"Waiting for {convert_s(retry_delay)}s")
                for temp in range(0, round(retry_delay)):
                    Loading_ani.msg = f"Reconnecting (retry in {convert_s(retry_delay - temp)})"
                    pg.time.wait(1000)
                if retry_delay < 1800:  # Cap at half an hour between attempts
                    retry_delay *= 2
                elif retry_delay > 1800:
                    retry_delay = 1800

        self.info('Reconnect complete')
        Loading_ani.stop()
        self.start_retained()
        Menu.start_retained()

    def subscribe(self, topics: str or tuple, response, retain=False):
        if type(topics) is str:
            topics = [topics]
        for topic in topics:
            if topic not in self.subscribed:
                self._mqtt.subscribe(topic, qos=Conf.Mqtt_qos)
                if retain:
                    self.retained.update({topic: response})
                self.subscribed.update({topic: response})
                self.debug(f"Subscribed to '{topic}'{' (retained)' if retain else ''}")
            else:
                self.warn(f"Already subscribed to '{topic}'{' (retained)' if retain else ''}")

    def unsubscribe(self, topics: str or tuple, unsub_all=False):
        if unsub_all:
            for topic in self.subscribed:
                self._mqtt.unsubscribe(topic)
            self.subscribed = {}
            self.debug('Unsubscribed from all topics.')
        else:
            if type(topics) is str:  # If only one topic then pass as list
                topics = [topics]

            for topic in topics:
                self._mqtt.unsubscribe(topic)
                if topic in self.subscribed:
                    self.subscribed.pop(topic)
                    self.debug(f"Unsubscribed from '{topic}'")
                else:
                    self.warn(f"'{topic}' not in subscriptions")

                if topic in self.retained:
                    self.retained.pop(topic)
                    self.debug(f"Removed '{topic}' from retained subscriptions")

    def start_retained(self):
        self.info('Starting retained topics')
        for topic in self.retained:
            self.subscribe(topic, self.retained[topic])

    def send(self, topic: str, payload: dict or str):
        msg = str(payload).replace("'", "\"")
        self._mqtt.publish(topic, payload=msg, qos=Conf.Mqtt_qos)
        self.debug(f"Sent {msg} to {topic}")

    def update(self):
        if self._last_msg_time < pg.time.get_ticks():  # If no msg since auto_reconnect ms
            self.warn('Auto reconnect set')
            self._set_reconnect()  # Automatically start reconnect as no traffic sent


class LOCALWEATHER(Window):
    _mqtt_active = f"miniplayer/weather/local/active/{MQTT.mac_address}"
    _mqtt_response = 'miniplayer/weather/local/response'

    def __init__(self):
        super().__init__('Local Weather')
        temp = 'assets/weather/'
        Img.img.update({'weather': {
            'storm': pg.transform.smoothscale(Img.load(temp + 'storm.png', (100, 100)), (300, 300)),
            'storm_2': pg.transform.smoothscale(Img.load(temp + 'storm_2.png', (100, 100)), (300, 300)),
            'storm_3': pg.transform.smoothscale(Img.load(temp + 'storm_3.png', (100, 100)), (300, 300)),
            'rain': pg.transform.smoothscale(Img.load(temp + 'rain.png', (100, 100)), (300, 300)),
            'rain_2': pg.transform.smoothscale(Img.load(temp + 'rain_2.png', (100, 100)), (300, 300)),
            'rain_3': pg.transform.smoothscale(Img.load(temp + 'rain_3.png', (100, 100)), (300, 300)),
            'rain_4': pg.transform.smoothscale(Img.load(temp + 'rain_4.png', (100, 100)), (300, 300)),
            'rain_5': pg.transform.smoothscale(Img.load(temp + 'rain_5.png', (100, 100)), (300, 300)),
            'hail': pg.transform.smoothscale(Img.load(temp + 'hail.png', (100, 100)), (300, 300)),
            'snow': pg.transform.smoothscale(Img.load(temp + 'snow.png', (100, 100)), (300, 300)),
            'snow_2': pg.transform.smoothscale(Img.load(temp + 'snow_2.png', (100, 100)), (300, 300)),
            'snow_3': pg.transform.smoothscale(Img.load(temp + 'snow_3.png', (100, 100)), (300, 300)),
            'mist': pg.transform.smoothscale(Img.load(temp + 'mist.png', (100, 100)), (300, 300)),
            'dust': pg.transform.smoothscale(Img.load(temp + 'dust.png', (100, 100)), (300, 300)),
            'haze': pg.transform.smoothscale(Img.load(temp + 'haze.png', (100, 100)), (300, 300)),
            'fog': pg.transform.smoothscale(Img.load(temp + 'fog.png', (100, 100)), (300, 300)),
            'wind': pg.transform.smoothscale(Img.load(temp + 'wind.png', (100, 100)), (300, 300)),
            'tornado': pg.transform.smoothscale(Img.load(temp + 'tornado.png', (100, 100)), (300, 300)),
            'sun': pg.transform.smoothscale(Img.load(temp + 'sun.png', (100, 100)), (300, 300)),
            'moon': pg.transform.smoothscale(Img.load(temp + 'moon.png', (100, 100)), (300, 300)),
            'cloud_2': pg.transform.smoothscale(Img.load(temp + 'cloud_2.png', (100, 100)), (300, 300)),
            'cloud': pg.transform.smoothscale(Img.load(temp + 'cloud.png', (100, 100)), (300, 300))}})
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
        self.icon = Img.img['weather']['cloud'], pg.rect.Rect((CENTER[0] - 30 - 300, 50, 300, 300))

    def get_icon(self, icon: str):
        try:
            self.icon = Img.img['weather'][icon]
            self.icon = self.icon, self.icon.get_rect(topright=(CENTER[0] - 30, 50))
        except Exception as err:
            self.handle(err, data=f"cause: Loading icon, id: {icon}")
            self.icon = Img.img['weather']['cloud'], pg.rect.Rect((CENTER[0] - 30 - 300, 50, 300, 300))
        except:
            self.err('Failed to load icon', data=f"id={icon}")
            self.icon = Img.img['weather']['cloud'], pg.rect.Rect((CENTER[0] - 30 - 300, 50, 300, 300))

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                self.value = json.loads(message.payload.decode())
                self.value['state'] = self.value['state'].replace('Clouds', 'Cloudy')
                self._snow = self.value['snow']
                self.get_icon(self.value['icon'])
                self._data['temp'] = render_text(str(self.value['temp']['real']) + '°c', 100, bold=True,
                                                 midleft=(self.icon[1].right + 60, self.icon[1].centery - 25))
                self._data['state'] = render_text(self.value['state'], 50, topleft=(self._data['temp'][1].left,
                                                                                    self._data['temp'][1].bottom + 10))
                self._data['temp f'] = render_text(f"Feels like: {round(self.value['temp']['feels'], 1)}°c", 35,
                                                   midtop=(CENTER[0] / 2, self._data['state'][1].bottom + 70))
                self._data['temp r'] = render_text(f"Lo: {round(self.value['temp']['min'], 1)}°c  "
                                                   f"Hi: {round(self.value['temp']['max'], 1)}°c", 35,
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
                self.handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f"ERR: {err}"
                self._load_default()
            except:
                self.err('MQTT receive error -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

    def start(self):
        if self.active:
            self.warn('Start called without stopping')
            return

        self.debug('Starting..')
        Mqtt.subscribe(self._mqtt_response, self.receive)
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED weather is active
        self.active = True
        self.info('Started')

    def stop(self):
        if not self.active:
            self.warn('Stop called without starting')
            return

        self.debug('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED weather is not active
        Mqtt.unsubscribe(self._mqtt_response)
        Menu.allow_screensaver = True
        self.debug('Allowed screensaver')
        self.active = False
        self.info('Stopped')

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
        surf.blit(*render_bar((350, 18), int((self.value['vis'] / 10000) * 100), 0, 100, fill_color=Colour['grey'],
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
    _mqtt_active = f"miniplayer/spotify/active/{MQTT.mac_address}"
    _mqtt_action = 'miniplayer/spotify/action'
    _mqtt_response = 'miniplayer/spotify/response'
    _pending_action_length = 12000
    _playlist_dir = "playlists/"

    def __init__(self):
        super().__init__('Spotify')
        Img.img.update({'spotify': {
            'logo': pg.transform.smoothscale(Img.load('assets/spotify/logo.png', (295, 89)), (212, 64)),
            'explicit': Img.load('assets/spotify/explicit.png', (35, 35)),
            'pause': (Img.load('assets/spotify/pause_0.png', (50, 50)),
                      Img.load('assets/spotify/pause_1.png', (50, 50))),
            'play': (Img.load('assets/spotify/play_0.png', (50, 50)),
                     Img.load('assets/spotify/play_1.png', (50, 50))),
            'shuffle': (Img.load('assets/spotify/shuffle_1.png', (50, 50)),
                        Img.load('assets/spotify/shuffle_1.png', (50, 50))),
            'shuffle_active': (Img.load('assets/spotify/shuffle_active_1.png', (50, 50)),
                               Img.load('assets/spotify/shuffle_active_1.png', (50, 50))),
            'repeat': (Img.load('assets/spotify/repeat_0.png', (50, 50)),
                       Img.load('assets/spotify/repeat_1.png', (50, 50)),
                       Img.load('assets/spotify/repeat_2.png', (50, 50))),
            'save': (Img.load('assets/spotify/save_0.png', (50, 50)),
                     Img.load('assets/spotify/save_1.png', (50, 50))),
            'playlist': Img.load('assets/spotify/playlist_1.png', (50, 50)),
            'skip': (Img.load('assets/spotify/skip_0.png', (50, 50)),
                     Img.load('assets/spotify/skip_1.png', (50, 50))),
            'mute': Img.load('assets/spotify/mute.png', (50, 50)),
            'vol 0': Img.load('assets/spotify/vol_0.png', (50, 50)),
            'vol 50': Img.load('assets/spotify/vol_50.png', (50, 50)),
            'vol 100': Img.load('assets/spotify/vol_100.png', (50, 50)),
            'vol -': (Img.load('assets/spotify/vol_-_0.png', (50, 50)),
                      Img.load('assets/spotify/vol_-_1.png', (50, 50))),
            'vol +': (Img.load('assets/spotify/vol_+_0.png', (50, 50)),
                      Img.load('assets/spotify/vol_+_1.png', (50, 50)))}})
        self._playing = False
        self._liked_song = None
        self._update_ms = 0
        self._pending_action = {}
        self._pending_value = None
        self._action_time = 0
        self._timeout_time = 0
        self._prev_value = None
        self._data = {}
        self._playlists = []
        self._active_playlist = None
        self.value = {}
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

    def _config_params(self, msg: dict):
        """
        Some api calls require different msg.params:
        msg.params[{device_id}]
        msg.params[{other_value, device_id}]
        msg.params[other_value, {device_id}]

        _config_params(msg) will add device_id for you
        """
        if 'params' in msg.keys():  # If params are set already
            for index in range(0, len(msg['params'])):  # Loop through each parameter value
                if msg['params'][index] is dict:  # If dict found
                    if 'device_id' in msg['params'][index].keys():  # If device_id already set
                        msg['params'][index]['device_id'] = self.value['device']['id']  # Set to current device_id
                    else:  # If device_id is not set
                        msg['params'][index].update({'device_id': self.value['device']['id']})  # Add device_id
                    break  # Jump to return as set
            else:  # If end of params
                msg['params'].append({'device_id': self.value['device']['id']})  # Add device_id (end for loop)
        else:  # If no params are set
            msg.update({'params': [{'device_id': self.value['device']['id']}]})  # Set to current device_id

        return msg  # Return configured message

    def _fetch_image(self, url: str):
        response = requests.get(url)  # Request playlists
        if response.status_code == 200:
            try:
                surf = pg.transform.smoothscale(pg.image.load(io.BytesIO(response.content)), (140, 140))
                return surf
            except:
                self.err(f"Failed to load playlist image (url={url})")
                return pg.surface.Surface((140, 140))
        else:
            self.err(f"Failed to get playlist image (code={response.status_code}, url={url})")
            return pg.surface.Surface((140, 140))

    def _load_default(self):
        cover = pg.surface.Surface((300, 300))
        cover.set_alpha(150)
        self._data = {'icon': (Img.img['spotify']['logo'],
                               Img.img['spotify']['logo'].get_rect(center=(CENTER[0], Menu.left[1].centery))),
                      'bg': None,
                      'explicit': (Img.img['spotify']['explicit'], Img.img['spotify']['explicit'].get_rect()),
                      'album_cover': (cover, cover.get_rect(topleft=(100, 125))),
                      'pause': Img.img['spotify']['pause'],
                      'play': Img.img['spotify']['play'],
                      'shuffle': Img.img['spotify']['shuffle'],
                      'shuffle_active': Img.img['spotify']['shuffle_active'],
                      'repeat': Img.img['spotify']['repeat'],
                      'save': Img.img['spotify']['save'],
                      'playlist': Img.img['spotify']['playlist'],
                      'skip_l': (pg.transform.flip(Img.img['spotify']['skip'][0], True, False),
                                 pg.transform.flip(Img.img['spotify']['skip'][1], True, False)),
                      'skip_r': Img.img['spotify']['skip'],
                      'duration': pg.rect.Rect(0, 0, 50, 30),
                      'volume': {
                          'left': pg.rect.Rect(0, 0, 50, 50),
                          'right_1': pg.rect.Rect(0, 0, 50, 50),
                          'right_2': pg.rect.Rect(0, 0, 50, 50),
                          'm': Img.img['spotify']['mute'],
                          '0': Img.img['spotify']['vol 0'],
                          '50': Img.img['spotify']['vol 50'],
                          '100': Img.img['spotify']['vol 100'],
                          '-': Img.img['spotify']['vol -'],
                          '+': Img.img['spotify']['vol +']}}

        surf = pg.surface.Surface((50, 50))
        self._data.update({'center': surf.get_rect(center=(CENTER[0], CENTER[1] + 160))})  # Pause / Play
        top = self._data['center'].top
        self._data.update({'left': surf.get_rect(topright=(self._data['center'].left - 50, top))})  # Rewind
        self._data.update({'far_left': surf.get_rect(topright=(self._data['left'].left - 50, top))})  # Shuffle
        self._data.update({'far_left_2': surf.get_rect(topright=(self._data['far_left'].left - 50, top))})  # Playlist
        self._data.update({'right': surf.get_rect(topleft=(self._data['center'].right + 50, top))})  # Skip
        self._data.update({'far_right': surf.get_rect(topleft=(self._data['right'].right + 50, top))})  # Repeat
        self._data.update({'far_right_2': surf.get_rect(topleft=(self._data['far_right'].right + 50, top))})  # Save

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
        # noinspection PyTypeChecker
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
            'device': {
                'name': '',
                'type': '',
                'supports_volume': False,
                'volume_percent': 0},
            'shuffle_state': False,
            'repeat_state': 'off',
            'context': {
                'type': '',
                'uri': ''},
            'progress_ms': 0,
            'progress': '0:00',
            'item': {
                'album': {
                    'images': [{'url': ''}],
                    'name': 'Loading...'},
                'artists': [{'name': 'Loading...'}],
                'duration_ms': 0,
                'duration': '-:--',
                'explicit': False,
                'id': '',
                'name': 'Loading...',
            },
            'currently_playing_type': '',
            'is_playing': False
            }

    def _get_playlists(self) -> bool:
        self.debug('Fetching playlists...')
        try:  # Request data from Node-RED
            response = requests.get(f"http://{Conf.Node_red_ip}:{Conf.Node_red_port}"
                                    f"{'/endpoint' if Conf.Node_red_ha else ''}/spotify/playlists", timeout=10)
        except Exception as err:
            self._playlists = []
            self.warn('Playlist fetch failed', data=err)
            return False

        if response.status_code == 200:
            self.info('Playlists fetched successfully')
            try:
                playlists = json.load(io.BytesIO(response.content))  # Decode response
                temp = {}  # Playlist by id
                for playlist in playlists['items']:  # For each playlist
                    temp.update({playlist['id'].replace('spotify:playlist:', ''): playlist})  # Set id as key in dict
                playlists = temp  # Reuse playlists as playlist by id
                self._playlists = []  # Clear previous playlists
                for key in Settings.value['Playlist Order']:  # For each ordered playlist add known playlists in order
                    try:
                        self._playlists.append(playlists[key.replace('spotify:playlist:', '')])
                    except KeyError:
                        Settings.value['Playlist Order'].remove(key)
                        self.warn(f"Removed invalid playlist from settings ('{key}')")
                for key in playlists:  # For every playlist
                    if key not in Settings.value['Playlist Order']:  # If unknown
                        self._playlists.append(playlists[key])  # Add unknown playlists to end
                        Settings.value['Playlist Order'].append(playlists[key]['id'])  # Add to known playlists
                self.debug('Playlists ordered successfully')
                Settings.save()  # Save playlist order
                self.debug('Loading playlist images...')
                temp = timer()
                cache = {}
                if not os.path.isdir(self._playlist_dir):
                    self.warn(f"Playlists folder not found at \"{self._playlist_dir}\"")
                    try:
                        os.mkdir(self._playlist_dir)
                        self.info(f"Created new directory at \"{self._playlist_dir}\"")
                    except Exception as err:
                        self.handle(err, data=f"cause: Creating playlists folder, location: \"{self._playlist_dir}\"")
                    except:
                        self.err(f"Failed to create folder \"{self._playlist_dir}\"", data="reason: UnknownError")
                try:
                    for file in os.listdir(self._playlist_dir):
                        cache.update({
                            file.replace('.png', ''): pg.image.load_extended(self._playlist_dir + file, 'png')})
                except Exception as err:
                    self.handle(err, data=f"cause: Loading playlist image, location: \"{self._playlist_dir}\"")
                except:
                    self.err(f"Failed to load playlist image from \"{self._playlist_dir}\"",
                             data="reason: UnknownError")

                for playlist in self._playlists:
                    if playlist['id'] not in cache:
                        playlist['images'] = self._fetch_image(playlist['images'][0]['url'])  # Load img
                        if os.path.isdir(self._playlist_dir):
                            try:
                                pg.image.save_extended(playlist['images'], f"{playlist['id']}.png", 'png')
                                shutil.move(f"{playlist['id']}.png",
                                            self._playlist_dir + folder() + playlist['id'] + ".png")
                                self.debug("Cached image", data="id:" + playlist['id'])
                            except Exception as err:
                                self.handle(err,
                                            data=f"cause: Caching playlist image, location: \"{self._playlist_dir}\"")
                            except:
                                self.err("Failed to cache playlist image",
                                         data=f"reason: UnknownError, location: \"{self._playlist_dir}\"")
                        else:
                            self.err("Failed to cache playlist image",
                                     data=f"reason: FileNotFoundError, location: \"{self._playlist_dir}\"")
                    else:
                        playlist['images'] = cache[playlist['id']]
                        self.debug("Loaded playlist cache", data="id:" + playlist['id'])

                self.info("Loaded playlist images", data=f"time: {round(timer() - temp, 2)}s)")
                return True

            except Exception as err:
                self._playlists = []
                self.handle(err, data="cause: Playlist ordering failed")
                return False
        else:
            temp = (f"http://{Conf.Node_red_ip}:{Conf.Node_red_port}"
                    f"{'/endpoint' if Conf.Node_red_ha else ''}/spotify/playlists")
            self._playlists = []
            self.err("Playlist fetch failed",
                     data=f"code={response.status_code}, "
                          f"url={temp})")
            return False

    def _update_playlists(self, uid: str) -> bool:
        self.debug("Fetching new playlist",
                   data=f"url: http://{Conf.Node_red_ip}:{Conf.Node_red_port}"
                        f"{'/endpoint' if Conf.Node_red_ha else ''}/spotify/playlists?id={uid}")
        response = requests.get(f"http://{Conf.Node_red_ip}:{Conf.Node_red_port}"
                                f"{'/endpoint' if Conf.Node_red_ha else ''}/spotify/playlists?id={uid}")
        if response.status_code == 200:  # Fetch playlist
            try:
                playlist = json.load(io.BytesIO(response.content))  # Decode response
                if playlist['id'] == 'spotify:user:ag.bungee:collection':
                    self.debug("Not loading playlist as liked songs", data="id: " + uid)
                    return True  # Report successful as it didn't fail
                else:
                    self._playlists.append(playlist)
                    Settings.value['Playlist Order'].append(playlist['id'])
                    Settings.save()
                    playlist['images'] = self._fetch_image(playlist['images'][0]['url'])
                    self.info(f"Playlist updated", data=f"id={uid}, name={playlist['name']}")
                    return True  # Report successful

            except:
                self.err("Failed to decode playlist during update", data="id=" + uid)
                return False  # Report failed
        else:
            if response.status_code != 500:
                self.err("Failed to fetch new playlist during update", data=f"code={response.status_code}, id={uid}")
            return False  # Report failed

    def _save_playlists(self):
        temp = []
        for plist in self._playlists:
            temp.append(plist['id'])
        Settings.value['Playlist Order'] = temp
        Settings.save()
        self.info("Saved playlist order")

    def _liked(self, track_id: str, state=None):
        try:  # Request data from Node-RED
            self.debug("Requesting liked song status", data="id: " + track_id)
            request = (f"http://{Conf.Node_red_ip}:{Conf.Node_red_port}"
                       f"{'/endpoint' if Conf.Node_red_ha else ''}/spotify/saved?id={track_id}" +
                       (f"&state={state}" if state is not None else ''))
            response = requests.get(request, timeout=10)
        except Exception as err:
            self.handle(err)
            self._liked_song = None
            self.warn("Defaulting liked song status to None")
            return

        if response.status_code == 200:
            self._liked_song = json.load(io.BytesIO(response.content))[0]
            self.debug(f"Liked song response: {self._liked_song}")  # Decode response

        else:
            self._liked_song = None
            self.err("Liked song request failed", data=f"(code={response.status_code} url={request})")
            return

    def reload_playlists(self) -> bool:
        self.debug("Reloading playlists")
        self._playlists = []
        self._active_playlist = None
        return self._get_playlists()

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                msg = json.loads(message.payload.decode())
                self.debug("Received data")
                if msg != {}:
                    self._playing = True
                else:
                    self._playing = False
                    return

                if msg['currently_playing_type'] != 'track':
                    self.warn(f"Spotify is not playing a track! ('{msg['currently_playing_type']}')")

                # Fetch album artwork
                if msg['item']['album']['images'][0]['url'] != self.value['item']['album']['images'][0]['url']:
                    self.debug("Fetching album artwork", data="url: " + msg['item']['album']['images'][0]['url'])
                    temp = WIDTH if WIDTH > HEIGHT else HEIGHT  # Fit to screen (keep aspect ratio 1:1)
                    cover = pg.transform.smoothscale(pg.image.load(io.BytesIO(
                        requests.get(msg['item']['album']['images'][0]['url']).content)), (temp, temp))
                    cover_crop = pg.surface.Surface((WIDTH, HEIGHT))
                    cover_crop.blit(cover, (CENTER[0] - cover.get_rect().centerx, CENTER[1] - cover.get_rect().centery))
                    cover_crop.set_alpha(80)
                    self._data['bg'] = cover_crop, (0, 0)
                    cover = pg.transform.smoothscale(cover, (300, 300))
                    self._data['album_cover'] = cover, cover.get_rect(topleft=(100, 125))
                    self.debug("Album cover fetch complete")

                if msg['context'] is not None:
                    if msg['context']['type'] == 'playlist':
                        self.debug("Attempting to find playlist")
                        msg['context']['uri'] = msg['context']['uri'].replace('spotify:playlist:', '')
                        # If current song is in playlist
                        if msg['context']['uri'] and ':collection' not in msg['context']['uri']:
                            if msg['context']['uri'] not in Settings.value['Playlist Order']:  # If unknown
                                self._update_playlists(msg['context']['uri'])  # Fetch new
                            try:
                                self.debug("Loading existing playlist")
                                try:
                                    self._active_playlist = self._playlists[Settings.value[
                                        'Playlist Order'].index(msg['context']['uri'])]  # Set current
                                except Exception as err:
                                    self.handle(err, data="cause: Loading existing playlist from settings")
                            except Exception as err:
                                self.handle(err,
                                            data="cause: Loading existing playlist, context: " + str(msg['context']))
                                self.err("Loading existing playlist failed", data=f"context: {msg['context']}")
                                self._active_playlist = None
                        else:
                            self._active_playlist = None
                            self.debug("Set active_playlist to None")
                else:
                    self.value.update({'context': {'type': '', 'uri': ''}})
                    self.debug("Set value context to None")

                if msg['item']['id'] != self.value['item']['id']:  # If new song is playing
                    self._liked(msg['item']['id'])  # Ask nodered if it is liked or not

                msg['item']['name'] = self._shorten(msg['item']['name'])  # Format and convert values to look nice
                msg['item']['duration_ms'] = int(msg['item']['duration_ms'])
                msg['progress_ms'] = int(msg['progress_ms'])
                if not Settings.value['Duration']:
                    msg['item']['duration_ms'] = msg['item']['duration_ms'] - msg['progress_ms']
                msg['item'].update({'duration': convert_s(msg['item']['duration_ms'] // 1000)})
                msg.update({'progress': convert_s(msg['progress_ms'] // 1000)})
                msg['item']['album']['name'] = self._shorten(msg['item']['album']['name'])
                msg['device']['name'] = msg['device']['name'].lower().title().replace("'S", "'s")
                self.debug("Formatted values")

                self.value = msg  # Set values as msg (all data is now ready for display)

                self._update_ms = pg.time.get_ticks()  # Set time for progress bar

                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']
                self.debug("Receive complete")

            except Exception as err:
                self.handle(err, data="cause: Spotify receive")
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = "ERR: " + str(err)
                self._load_default()
            except:
                self.err("Failed to receive data", data="cause: UnknownError")
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

    def start(self):
        if self.active:
            self.warn('Start called without stopping')
            return

        self.debug('Starting..')
        Mqtt.subscribe(self._mqtt_response, self.receive)
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED spotify is active
        self.active = True
        self.info('Started')

    def stop(self):
        if not self.active:
            self.warn('Stop called without starting')
            return

        self.debug('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED spotify is not active
        Mqtt.unsubscribe(self._mqtt_response)
        Menu.allow_screensaver = True
        self.debug('Allowed screensaver')
        self.active = False
        self.info('Stopped')

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
            txt = render_text(self.value['item']['name'], 35, bold=True,
                              bottomleft=(self._data['album_cover'][1].right + 25,
                                          self._data['album_cover'][1].top + self._data['album_cover'][1].height / 4))
            surf.blit(*txt)  # Song name
            if self.value['item']['explicit']:  # Explicit
                self._data['explicit'][1].midleft = (txt[1].right + 15, txt[1].centery)
                surf.blit(*self._data['explicit'])
            surf.blit(*render_text(self.value['item']['artists'][0]['name'], 35,  # Artist name
                                   midleft=(txt[1].left, self._data['album_cover'][1].centery)))
            surf.blit(*render_text(self.value['item']['album']['name'], 35,  # Album name
                                   topleft=(txt[1].left, self._data['album_cover'][1].centery +
                                            self._data['album_cover'][1].height / 4)))

            pending_keys = self._pending_action.keys()  # BUTTONS
            if self._playlists:
                surf.blit(self._data['playlist'], self._data['far_left_2'])  # Playlist
                if self._active_playlist and 'name' in self._active_playlist.keys():  # Playlist name
                    surf.blit(*render_text(self._active_playlist['name'], 25, colour=Colour['grey'],
                                           midright=(self._data['far_left_2'].left - 20,
                                                     self._data['far_left_2'].centery)))
            surf.blit(self._data['skip_l'][0 if 'rewind' in pending_keys else 1], self._data['left'])  # Rewind
            surf.blit(self._data['pause' if self.value['is_playing'] else 'play']  # Pause / Play
                      [0 if ('pause' if self.value['is_playing'] else 'play') in pending_keys else 1],
                      self._data['center'])
            surf.blit(self._data['skip_r'][0 if 'skip' in pending_keys else 1], self._data['right'])  # Skip
            surf.blit(self._data['shuffle_active' if self.value['shuffle_state'] else 'shuffle']  # Shuffle
                      [0 if 'shuffle' in pending_keys else 1], self._data['far_left'])
            surf.blit(self._data['repeat'][0 if self.value['repeat_state'] == 'off' else   # Repeat
                                           1 if self.value['repeat_state'] == 'context' else 2],  # Off, Context, Track
                      self._data['far_right'])
            if self._liked_song is not None:
                surf.blit(self._data['save'][1 if self._liked_song else 0], self._data['far_right_2'])  # Save

            bar = render_bar((800, 16), self.value['progress_ms'], 0, self.value['item']['duration_ms'],  # PROGRESS BAR
                             midtop=(CENTER[0], self._data['center'].bottom + 40))
            surf.blit(*bar)
            surf.blit(*render_text(self.value['progress'], 30, Colour['white'], bold=True,  # PROGRESS
                                   midright=(bar[1].left - 30, bar[1].centery + 1)))
            temp = render_text(self.value['item']['duration'], 30, Colour['white'], bold=True,  # DURATION
                               midleft=(bar[1].right + 30, bar[1].centery + 1))
            self._data['duration'] = temp[1]  # Save rect to be able to press
            surf.blit(*temp)

            bar = render_bar((300, 14), self.value['device']['volume_percent'], 0, 100,  # VOLUME BAR
                             midtop=(CENTER[0], bar[1].bottom + 45))
            surf.blit(*bar)
            self._data['volume']['left'].midright = bar[1].left - 20, bar[1].centery  # VOLUME ICON
            self._data['volume']['right_1'].midleft = bar[1].right + 20, bar[1].centery
            self._data['volume']['right_2'].midleft = self._data['volume']['right_1'].right + 20, bar[1].centery
            if self.value['device']['volume_percent'] == 0:
                surf.blit(self._data['volume']['m'], self._data['volume']['left'])
            elif self.value['device']['volume_percent'] >= 65:
                surf.blit(self._data['volume']['100'], self._data['volume']['left'])
            elif self.value['device']['volume_percent'] >= 35:
                surf.blit(self._data['volume']['50'], self._data['volume']['left'])
            else:
                surf.blit(self._data['volume']['0'], self._data['volume']['left'])

            if self.value['device']['volume_percent'] >= 0:  # VOLUME CONTROLS
                surf.blit(self._data['volume']['-'][0 if 'volume_-' in pending_keys else 1],
                          self._data['volume']['right_1'])
            if self.value['device']['volume_percent'] <= 100:
                surf.blit(self._data['volume']['+'][0 if 'volume_+' in pending_keys else 1],
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
            surf.blit(*render_text(self.value['device']['name'], 30, Colour['grey'],
                                   bottomright=(WIDTH - 5, HEIGHT - 3)))
        if self._timeout_time > pg.time.get_ticks() and not self.show_playlists:  # Action status
            set_info('Action timed out!', Colour['red'])
        if not self.show_playlists:  # Timestamp
            surf.blit(*render_text(self.timestamp, 30, self._timestamp_color, bottomleft=(5, HEIGHT - 3)))

    def update(self):
        global Button_cooldown
        if (self.value['is_playing'] or self.show_playlists) and Menu.allow_screensaver and not Settings.active:
            Menu.allow_screensaver = False
            self.info('Disabled screensaver')
        elif (not self.value['is_playing'] and not self.show_playlists and not Menu.allow_screensaver and
              not Settings.active):
            Menu.allow_screensaver = True
            self.debug('Allowed screensaver')
        if not self._playing and self.show_playlists:  # Disable playlists if not playing
            self.show_playlists = False
        if self._playing:
            # UPDATE PROGRESS BAR
            if pg.time.get_ticks() - self._update_ms >= 1000 and self.value['is_playing'] and \
                    self.value['progress_ms'] + 1000 < self.value['item']['duration_ms']:  # If showing and needs update
                self._update_ms = pg.time.get_ticks()
                self.value['progress_ms'] += 1000
                self.value['duration'] = convert_s(self.value['progress_ms'] // 1000)
                self.value['progress'] = convert_s(self.value['progress_ms'] // 1000)
            elif self.value['progress_ms'] + 1000 >= self.value['item']['duration_ms']:
                self.value['progress_ms'] = self.value['item']['duration_ms']
                self.value['progress'] = convert_s(self.value['progress_ms'] // 1000)

            if self.show_playlists:  # PLAYLISTS
                if not Button_cooldown and (not Conf.Touchscreen and pg.mouse.get_pressed()[0] or
                                            Conf.Touchscreen and pg.mouse.get_pos() != Prev_mouse_pos):
                    if Menu.right[1].collidepoint(Mouse_pos):  # PLAYLIST (close)
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._save_playlists()
                        Menu.allow_controls = True
                        self.show_playlists = False
                        self.info('Closed playlists')
                    elif self._data['plist']['scroll_u'][2].collidepoint(Mouse_pos) and self._data['plist']['page'] > 0:
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._data['plist']['page'] -= 1
                        self.debug('Scroll up')
                    elif (self._data['plist']['scroll_d'][2].collidepoint(Mouse_pos) and   # Scroll down
                          self._data['plist']['page'] < floor(len(self._playlists) / len(self._data['plist_rect']))):
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._data['plist']['page'] += 1
                        self.debug('Scroll down')

                    else:
                        for index in range(0, len(self._data['plist_rect'])):  # For each shown playlist
                            rect = self._data['plist_rect'][index]
                            index += self._data['plist']['page'] * len(self._data['plist_rect'])  # Offset index by page
                            if index >= len(self._playlists):
                                break
                            plist = self._playlists[index]
                            if rect['play'].collidepoint(Mouse_pos):  # Play
                                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                                self.debug("Play button")
                                Mqtt.send(self._mqtt_action, {'playlist': 0,
                                                              'params': [{'device_id': self.value['device']['id'],
                                                                          'context_uri': plist['uri']}]})
                            elif rect['move_u'].collidepoint(Mouse_pos) and index > 0:  # Move up
                                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                                self._playlists[index] = self._playlists[index - 1]
                                self._playlists[index - 1] = plist
                                self.debug("Moved playlist up", data=f"name: {plist['name']}, id: {plist['id']}")
                            elif rect['move_d'].collidepoint(Mouse_pos) and index < len(self._playlists) - 1:  # Down
                                Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                                self._playlists[index] = self._playlists[index + 1]
                                self._playlists[index + 1] = plist
                                self.debug("Moved playlist down", data=f"name: {plist['name']}, id: {plist['id']}")

            else:  # CONTROLS
                action = {}
                if not Settings.active and not self.show_playlists and not Button_cooldown and (
                        not Conf.Touchscreen and pg.mouse.get_pressed()[0] or
                        Conf.Touchscreen and pg.mouse.get_pos() != Prev_mouse_pos):
                    if self._data['center'].collidepoint(Mouse_pos):  # Pause / Play
                        action.update({'pause': 0} if self.value['is_playing'] else {'play': 0})
                        self._prev_value = self.value['is_playing']
                    elif self._data['left'].collidepoint(Mouse_pos):  # Rewind
                        action.update({'rewind': 0})
                        self._prev_value = self.value['item']['name']
                    elif self._data['far_left'].collidepoint(Mouse_pos):  # Shuffle
                        action.update({'shuffle': 0, 'params': [str(not self.value['shuffle_state']).lower()]})
                        self._prev_value = self.value['shuffle_state']
                    elif self._data['right'].collidepoint(Mouse_pos):  # Skip
                        action.update({'skip': 0})
                        self._prev_value = self.value['item']['name']
                    elif self._data['far_right'].collidepoint(Mouse_pos):  # Repeat
                        action.update({'repeat': 0, 'params': [
                            'context' if self.value['repeat_state'] == 'off' else  # (Off, Context, Track)
                            'track' if self.value['repeat_state'] == 'context' else 'off']})
                        self._prev_value = self.value['repeat_state']
                    elif self._data['far_right_2'].collidepoint(Mouse_pos) and self._liked_song is not None:  # Like
                        self._liked(self.value['item']['id'], state=False if self._liked_song else True)  # http
                    elif self._data['duration'].collidepoint(Mouse_pos):
                        Settings.value['Duration'] = not Settings.value['Duration']
                    elif (self._data['volume']['right_1'].collidepoint(Mouse_pos) and
                          self.value['device']['volume_percent'] > 0):  # Vol -
                        action.update({'volume_-': 0, 'params': [
                            (self.value['device']['volume_percent'] - 5 if
                             self.value['device']['volume_percent'] - 5 >= 0 else 0)]})
                        self._prev_value = self.value['device']['volume_percent']
                    elif (self._data['volume']['right_2'].collidepoint(Mouse_pos) and
                          self.value['device']['volume_percent'] < 100):  # Vol +
                        action.update({'volume_+': 0, 'params': [
                            (self.value['device']['volume_percent'] + 5 if
                             self.value['device']['volume_percent'] + 5 <= 100 else 100)]})
                        self._prev_value = self.value['device']['volume_percent']

                    if action and not self._pending_action and not self._action_time:
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        self._action_time = pg.time.get_ticks() + self._pending_action_length
                        self.debug("Generating action", data="action: " + str(action))
                        action = self._config_params(action)  # Attach device_id to parameters
                        self._pending_action = action
                        self.debug("Requesting action", data="action: " + str(action))
                        Mqtt.send(self._mqtt_action, action)

                    if self._data['far_left_2'].collidepoint(Mouse_pos):  # PLAYLISTS (open)
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        Menu.allow_controls = False
                        self.show_playlists = True
                        self.info('Opened playlists')

                temp = tuple(self._pending_action.keys())  # Action confirmed
                if (('pause' in temp or 'play' in temp) and self.value['is_playing'] != self._prev_value or
                        ('skip' in temp or 'rewind' in temp) and self.value['item']['name'] != self._prev_value or
                        ('volume_+' in temp or 'volume_-' in temp) and
                        self.value['device']['volume_percent'] != self._prev_value or
                        'shuffle' in temp and self.value['shuffle_state'] != self._prev_value or
                        'repeat' in temp and self.value['repeat_state'] != self._prev_value):
                    self.info(f"{temp[0].title()} confirmed")
                    set_info(f"{temp[0].title().replace('_', ' ')} confirmed")
                    self._action_time = 0
                    self._prev_value = None
                    self._pending_action = {}

                if self._action_time and pg.time.get_ticks() >= self._action_time:  # Action timed out
                    self.err(f"{self._pending_action} timed out")
                    self._timeout_time = pg.time.get_ticks() + 5000
                    self._action_time = 0
                    self._prev_value = None
                    self._pending_action = {}


class OCTOPRINT(Window):
    _mqtt_active = f"miniplayer/octoprint/active/{MQTT.mac_address}"

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
                msg = json.loads(message.payload.decode())
                self.value['path'] = msg['path']
                self.value['progress'] = msg['progress']
                self.value['state'] = msg['state']
                self.printing = self.value['state']['flags']['printing']
                self._data['state'] = render_text(
                    f"{self.value['state']['text']}: {round(self.value['progress']['completion'])}%", 25, bold=True,
                    topleft=(15, Menu.left[1].bottom + 15))
                self._data['state_bar'] = render_bar((self._data['state'][1].width, 10),
                                                     round(self.value['progress']['completion']), 0, 100,
                                                     topleft=(self._data['state'][1].left,
                                                              self._data['state'][1].bottom + 5))
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                self.handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f"ERR: {err}"
                self._load_default()
            except:
                self.err('MQTT receive error (state) -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

        elif message.topic == self._mqtt_responses[1]:
            try:
                msg = json.loads(message.payload.decode())
                self.value['pos'] = msg['position']
                self._data['pos']['x'] = render_bar((140, 10), self.value['pos']['x'], 0, 320)
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                self.handle(err)
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = f"ERR: {err}"
                self._load_default()
            except:
                self.err('MQTT receive error (pos) -> unknown')
                if self._timestamp_color != Colour['red']:
                    self._timestamp_color = Colour['red']
                    self.timestamp = 'ERR: Unknown'
                self._load_default()

        elif message.topic == self._mqtt_responses[2]:
            try:
                msg = json.loads(message.payload.decode())
                self.value['temp'] = msg
                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                self.handle(err)
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
            self.warn('Start called without stopping')
            return

        Mqtt.subscribe(self._mqtt_responses, self.receive)
        self._load_default()
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED octoprint is active
        self.active = True
        self.info('Started.')

    def stop(self):
        if not self.active:
            self.warn('Stop called without starting')
            return

        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED octoprint is not active
        Mqtt.unsubscribe(self._mqtt_responses)
        Menu.allow_screensaver = True
        self.info('Allowed screensaver')
        self.active = False
        self.info('Stopped.')

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
            sec = f"0{sec}"
    elif sec < 10:
        sec = f"0{sec}"
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


def set_info(txt: str, colour=(24, 216, 97), timeout=2000):
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

        Clock.tick(Conf.Fps)
        for event in pg.event.get():  # Pygame event handling
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                raise KeyboardInterrupt
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN:
                    Mqtt.disconnect() if Mqtt.connected else Mqtt.connect()
                elif event.key == pg.K_r:
                    Mqtt.reconnect_pending = True
                elif event.key == pg.K_s:
                    pg.image.save(Display, "screenshot.png")

        Mouse_pos = pg.mouse.get_pos()

        try:
            if not Menu.screensaver:
                if not Current_window.active:  # ALL WINDOWS
                    Current_window.start()
                # update_time = timer()
                Current_window.update()
                # update_time = convert_ms(update_time)
                # draw_time = timer()
                Current_window.draw()
                # print(f"Update: {update_time}ms, Draw: {update_ms(draw_time)}ms")

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
            Logging('Main').handle(err)
        except:
            print('main() failed -> unknown')

        if pg.time.get_ticks() >= Button_cooldown:  # Button cooldown reset
            Button_cooldown = 0

        if Info[0] and Info[2] > pg.time.get_ticks():  # Show info
            Display.blit(*render_text(Info[0], 30, Info[1], bold=True, midbottom=(CENTER[0], HEIGHT - 10)))

        if Conf.Backlight == 1:  # Display brightness through software
            Display.blit(Backlight.software_dim, (0, 0))

        Prev_mouse_pos = Mouse_pos
        pg.display.update()
        # print(f"Mainloop: {convert_ms(mainloop_time)}ms")


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
    Logging.close_log()
    pg.quit()
    quit()


# RUN
if __name__ == '__main__':
    if Conf.Touchscreen:  # Hide mouse if touchscreen
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
    if Conf.Backlight == 2 and pigpio:
        try:
            g_temp = pigpio.pi()
            g_temp.set_mode(BACKLIGHT.pin, pigpio.OUTPUT)
            g_temp.hardware_PWM(BACKLIGHT.pin, BACKLIGHT.freq, 1000000)
        except (Exception, BaseException) as error:
            Logging('Main').handle(error, crit=True)
        except:
            print('Failed to start backlight -> unknown')

    try:  # Start all windows
        Loading_ani = LoadingAni()
        Loading_ani.start(msg='Connecting...', msg_colour=Colour['amber'])
        Mqtt = MQTT()
        Loading_ani.msg, Loading_ani.msg_colour = 'Loading Menu', Colour['l blue']  # Sets colour and msg of ani
        Menu = MENU()
        Loading_ani.msg = 'Loading Settings'  # Update animation msg to see which window is loading
        Settings = SETTINGS()
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
        Logging('Main').handle(error, crit=True)
        if Loading_ani:
            Loading_ani.stop()
        Logging.close_log()
        pg.quit()
        quit()
    except:
        print('Failed to start windows -> unknown')
        if Loading_ani:
            Loading_ani.stop()
        Logging.close_log()
        pg.quit()
        quit()

    Current_window = Local_weather  # Default window
    try:
        main()
    except KeyboardInterrupt:
        pass  # Jump to finally
    except (Exception, BaseException) as error:
        Logging('Main').handle(error, crit=True)
    except:
        print('Unhandled exception -> main()')
    finally:  # Stop all windows and close after error handling
        quit_all()
