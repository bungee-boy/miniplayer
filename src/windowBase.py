import pygame as pg
import paho.mqtt.client as mqtt_client
import threading
from timeit import default_timer as timer

from loader import ConfigLoader, load_img
from logger import Logging

Config = ConfigLoader()

WIDTH, HEIGHT = Config.conf['RESOLUTION']
CENTER = WIDTH // 2, HEIGHT // 2
Colour = {'key': (1, 1, 1), 'black': (0, 0, 0), 'white': (255, 255, 255), 'grey': (155, 155, 155),
          'd grey': (80, 80, 80), 'red': (251, 105, 98), 'yellow': (252, 252, 153), 'l green': (121, 222, 121),
          'green': (18, 115, 53), 'amber': (200, 140, 0), 'l blue': (3, 140, 252)}
Img = {  # ASSET DIRECTORIES / PATHS
    'bg': load_img('assets/bg.jpg', (1280, 720), alpha=False),
    'icon': load_img('assets/icon.ico', (32, 32)),
    'menu': {
        'menu': load_img('assets/menu.png', (50, 50)),
        'settings': load_img('assets/settings.png', (50, 50)),
        'cross': load_img('assets/cross.png', (50, 50)),
        'on': load_img('assets/on.png', (50, 50)),
        'off': load_img('assets/off.png', (50, 50)),
        'none': load_img('assets/none.png', (50, 50))}}

Button_cooldown = 0
Button_cooldown_length = 500 if Config.conf['TOUCHSCREEN'] else 100
Mouse_pos = -1, -1
Prev_mouse_pos = -2, -2

Bg = pg.transform.scale(Img['bg'], (WIDTH, HEIGHT))
Bg.set_alpha(130)
pg.display.set_icon(Img['icon'])

Display = pg.display.set_mode(Config.conf['RESOLUTION'],
                              flags=pg.FULLSCREEN if Config.conf['FULLSCREEN'] else 0, display=Config.conf['SCREEN'])
Clock = pg.time.Clock()
pg.display.set_caption('Miniplayer v2')
pg.init()


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


class MQTT(Logging):
    mac_address = Config.conf['NODERED_USER']
    _mqtt_window = '/miniplayer/window'

    def __init__(self):
        super().__init__('MQTT')
        self.connected = False
        self.retained = {}  # {'topic': response()}
        self.subscribed = {}
        self._last_msg_time = pg.time.get_ticks() + Config.conf['MQTT_AUTO_RECONNECT']
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
        self._last_msg_time = pg.time.get_ticks() + Config.conf['MQTT_AUTO_RECONNECT']  # Update last msg time
        if message.topic == self._mqtt_window and Config.setting['WINDOW_CHANGE']:  # If topic is to change windows
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
            if Config.conf['MQTT_USER'] and Config.conf['MQTT_PASS']:  # If username and password
                self._mqtt.username_pw_set(Config.conf['MQTT_USER'], Config.conf['MQTT_PASS'])
                self.log(f"Set credentials: {Config.conf['MQTT_USER']}, {Config.conf['MQTT_PASS']}")
            self._mqtt.will_set(f'/miniplayer/connection/{self.mac_address}', payload='disconnected')
            self._mqtt.on_message = self._global_response
            self._mqtt.loop_start()
            self.log(f"Connecting to '{Config.conf['MQTT_IP']}' with username '{self.mac_address}'")
            if ani:
                Loading_ani.start(msg='Connecting...', msg_colour=Colour['amber'])
            else:
                Loading_ani.msg, Loading_ani.msg_colour = 'Connecting...', Colour['amber']
            temp = timer()
            try:
                self._mqtt.connect(Config.conf['MQTT_IP'], port=Config.conf['MQTT_PORT'])  # Start connection
                while not self._mqtt.is_connected():  # Wait for MQTT to connect
                    pg.time.wait(250)
                    if round(timer() - temp, 2) >= 10:  # Timeout after 10s
                        self.err(f"Connection to {Config.conf['MQTT_IP']} failed: Timed out",
                                 data=f'username={self.mac_address}')
                        Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                        pg.time.wait(1500)
                        if ani:
                            Loading_ani.stop()
                        return False

            except Exception as err:  # If failure to connect
                self.err(f"Connection to {Config.conf['MQTT_IP']} failed: {err}", data=f"username={self.mac_address}")
                Loading_ani.msg, Loading_ani.msg_colour = 'Connection Failed!', Colour['red']
                pg.time.wait(1500)
                if ani:
                    Loading_ani.stop()
                return False

            self.send(f'/miniplayer/connection/{self.mac_address}', 'connected')  # If connected
            self.connected = True
            self._last_msg_time = pg.time.get_ticks() + Config.conf['MQTT_AUTO_RECONNECT']
            self._mqtt.on_disconnect = self._set_reconnect
            Loading_ani.msg, Loading_ani.msg_colour = 'Connected!', Colour['green']
            pg.time.wait(1500)
            if ani:
                Loading_ani.stop()
            self.log(f"Connected to '{Config.conf['MQTT_IP']}' with username '{self.mac_address}'")
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

    def send(self, topic: str, payload: dict or str):
        msg = str(payload).replace("'", "\"")
        self._mqtt.publish(topic, payload=msg)
        self.log(f"Sent {msg} to {topic}")

    def update(self):
        if self._last_msg_time < pg.time.get_ticks():  # If no msg since auto_reconnect ms
            self.log('Auto reconnect set', cat='WRN')
            self._set_reconnect()  # Automatically start reconnect as no traffic sent


class MENU(Logging):
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

    @staticmethod
    def set_window(window):
        global Current_window
        Current_window.stop()
        Current_window = window
        Current_window.start()

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
        if Mouse_pos != Prev_mouse_pos or not self.allow_screensaver or not Config.setting['Screensaver']:
            self.screensaver = False
            self._screensaver_timer = pg.time.get_ticks() + Config.conf['SCREENSAVER_DELAY']
        if not self.screensaver and pg.time.get_ticks() >= self._screensaver_timer and \
                self.allow_screensaver and Config.setting['Screensaver']:
            self.screensaver = True
            self.log('Started screensaver')
        elif self.screensaver and pg.time.get_ticks() < self._screensaver_timer:
            self.screensaver = False
            self.log('Stopped screensaver')

        # Page navigation
        if (not Config.conf['TOUCHSCREEN'] and not pg.mouse.get_pressed()[0] or
                Config.conf['TOUCHSCREEN'] and Mouse_pos == Prev_mouse_pos) or Button_cooldown:
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


class LoadingAni(Logging):
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

                Clock.tick(Config.conf['FPS'])

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
            Logging('main').handle(err)
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


class Window(Logging):
    def __init__(self, name: str):
        super().__init__(name)
        self.active = False
        self.message = {}
        self.timestamp = '--:--'
        self._timestamp_color = Colour['yellow']

    def _load_default(self):
        pass

    def receive(self, client, data, message):  # mqtt_client.MQTTMessage
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


class SETTINGS(Window):
    def __init__(self):
        super().__init__('Settings')
        self.shadow = pg.surface.Surface((WIDTH, HEIGHT))
        self.shadow.set_alpha(160)
        surf = Img['menu']['on']
        self._data = {}
        self._data.update({'screensaver': surf.get_rect(midleft=(Menu.left[1].centerx + 50, 150))})
        self._data.update({'device_info': surf.get_rect(midleft=(self._data['screensaver'].left,
                                                                 self._data['screensaver'].centery + 100))})
        self._data.update({'playlists': surf.get_rect(midleft=(self._data['device_info'].left,
                                                               self._data['device_info'].centery + 100))})
        self._data.update({'reconnect': surf.get_rect(midleft=(self._data['playlists'].left,
                                                               self._data['playlists'].centery + 100))})
        self._data.update({'close': surf.get_rect(midleft=(self._data['reconnect'].left,
                                                           self._data['reconnect'].centery + 100))})

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
        surf.blit(Img['menu']['on' if Config.setting['Screensaver'] else 'off'], self._data['screensaver'])
        surf.blit(*render_text('Screensaver', 35, bold=True,
                               midleft=(self._data['screensaver'].right + temp, self._data['screensaver'].centery)))
        # DEVICE INFO
        surf.blit(Img['menu']['on' if Config.setting['Device Info'] else 'off'], self._data['device_info'])
        surf.blit(*render_text('Device Info', 35, bold=True,
                               midleft=(self._data['device_info'].right + temp, self._data['device_info'].centery)))
        # RELOAD PLAYLISTS
        surf.blit(Img['menu']['none'], self._data['playlists'])
        surf.blit(*render_text('Reload playlists', 35, bold=True,
                               midleft=(self._data['playlists'].right + temp, self._data['playlists'].centery)))
        # RECONNECT
        surf.blit(Img['menu']['none'], self._data['reconnect'])
        surf.blit(*render_text('Reconnect', 35, bold=True,
                               midleft=(self._data['reconnect'].right + temp, self._data['reconnect'].centery)))
        # CLOSE
        surf.blit(Img['menu']['none'], self._data['close'])
        surf.blit(*render_text('Close', 35, bold=True,
                               midleft=(self._data['close'].right + temp, self._data['close'].centery)))
        # MQTT INFO
        surf.blit(*render_text(f"Connection: {Config.conf['MQTT_IP']}   Username: {Mqtt.mac_address}", 30, bold=True,
                               midbottom=(CENTER[0], HEIGHT - 10)))

        if (not Config.conf['TOUCHSCREEN'] and not pg.mouse.get_pressed()[0] or
                Config.conf['TOUCHSCREEN'] and Mouse_pos == Prev_mouse_pos) or Button_cooldown:
            return
        elif Menu.right[1].collidepoint(Mouse_pos):
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            self.active = False
            Menu.allow_screensaver = True
            Config.save_settings()
        elif self._data['screensaver'].collidepoint(Mouse_pos):  # Screensaver
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            Config.setting['Screensaver'] = False if Config.setting['Screensaver'] else True
        elif self._data['device_info'].collidepoint(Mouse_pos):  # Device info
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            Config.setting['Device Info'] = False if Config.setting['Device Info'] else True
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
        elif self._data['close'].collidepoint(Mouse_pos):  # Close
            Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
            raise KeyboardInterrupt('Close button pressed')


Loading_ani = LoadingAni()
Menu = MENU()
