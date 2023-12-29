import io
import json
import os
import shutil
from time import strftime
from datetime import datetime
from math import floor
from sys import argv as launch_opt
import requests
from windowBase import *
try:
    import pigpio
except ImportError:
    pigpio = None

if len(launch_opt) >= 1:  # LAUNCH OPTIONS
    if '--debug' in launch_opt:
        DEBUG = bool(int(launch_opt[launch_opt.index('--debug') + 1]))
        print('Forced DEBUG ' + 'On' if DEBUG else 'Off')
    if '--logging' in launch_opt:
        LOGGING = bool(int(launch_opt[launch_opt.index('--logging') + 1]))
        print(f'Forced LOGGING {"On" if LOGGING else "Off"}')

Loaded_fonts = {}
Info = '', Colour['white'], 2000  # txt, colour, ms

Loading_ani = None
Menu = None
Button_cooldown = None

try:
    pg.font.Font('assets/thinfont.ttf', 15)
except Exception or BaseException as error:
    Logging('main').handle(error, traceback=False)
try:
    pg.font.Font('assets/boldfont.ttf', 15)
except Exception or BaseException as error:
    Logging('main').handle(error, traceback=False)

Img.update({'weather': {
        'storm': pg.transform.smoothscale(load_img('assets/weather/storm.png', (100, 100)), (300, 300)),
        'storm_2': pg.transform.smoothscale(load_img('assets/weather/storm_2.png', (100, 100)), (300, 300)),
        'storm_3': pg.transform.smoothscale(load_img('assets/weather/storm_3.png', (100, 100)), (300, 300)),
        'rain': pg.transform.smoothscale(load_img('assets/weather/rain.png', (100, 100)), (300, 300)),
        'rain_2': pg.transform.smoothscale(load_img('assets/weather/rain_2.png', (100, 100)), (300, 300)),
        'rain_3': pg.transform.smoothscale(load_img('assets/weather/rain_3.png', (100, 100)), (300, 300)),
        'rain_4': pg.transform.smoothscale(load_img('assets/weather/rain_4.png', (100, 100)), (300, 300)),
        'rain_5': pg.transform.smoothscale(load_img('assets/weather/rain_5.png', (100, 100)), (300, 300)),
        'hail': pg.transform.smoothscale(load_img('assets/weather/hail.png', (100, 100)), (300, 300)),
        'snow': pg.transform.smoothscale(load_img('assets/weather/snow.png', (100, 100)), (300, 300)),
        'snow_2': pg.transform.smoothscale(load_img('assets/weather/snow_2.png', (100, 100)), (300, 300)),
        'snow_3': pg.transform.smoothscale(load_img('assets/weather/snow_3.png', (100, 100)), (300, 300)),
        'mist': pg.transform.smoothscale(load_img('assets/weather/mist.png', (100, 100)), (300, 300)),
        'dust': pg.transform.smoothscale(load_img('assets/weather/dust.png', (100, 100)), (300, 300)),
        'haze': pg.transform.smoothscale(load_img('assets/weather/haze.png', (100, 100)), (300, 300)),
        'fog': pg.transform.smoothscale(load_img('assets/weather/fog.png', (100, 100)), (300, 300)),
        'wind': pg.transform.smoothscale(load_img('assets/weather/wind.png', (100, 100)), (300, 300)),
        'tornado': pg.transform.smoothscale(load_img('assets/weather/tornado.png', (100, 100)), (300, 300)),
        'sun': pg.transform.smoothscale(load_img('assets/weather/sun.png', (100, 100)), (300, 300)),
        'cloud_2': pg.transform.smoothscale(load_img('assets/weather/cloud_2.png', (100, 100)), (300, 300)),
        'cloud': pg.transform.smoothscale(load_img('assets/weather/cloud.png', (100, 100)), (300, 300))}})
Img.update({'spotify': {
        'logo': pg.transform.smoothscale(load_img('assets/spotify/logo.png', (295, 89)), (212, 64)),
        'explicit': load_img('assets/spotify/explicit.png', (35, 35)),
        'pause': (load_img('assets/spotify/pause_0.png', (50, 50)),
                  load_img('assets/spotify/pause_1.png', (50, 50))),
        'play': (load_img('assets/spotify/play_0.png', (50, 50)),
                 load_img('assets/spotify/play_1.png', (50, 50))),
        'shuffle': (load_img('assets/spotify/shuffle_1.png', (50, 50)),
                    load_img('assets/spotify/shuffle_1.png', (50, 50))),
        'shuffle_active': (load_img('assets/spotify/shuffle_active_1.png', (50, 50)),
                           load_img('assets/spotify/shuffle_active_1.png', (50, 50))),
        'repeat': (load_img('assets/spotify/repeat_0.png', (50, 50)),
                   load_img('assets/spotify/repeat_1.png', (50, 50)),
                   load_img('assets/spotify/repeat_2.png', (50, 50))),
        'save': (load_img('assets/spotify/save_0.png', (50, 50)),
                 load_img('assets/spotify/save_1.png', (50, 50))),
        'playlist': load_img('assets/spotify/playlist_1.png', (50, 50)),
        'skip': (load_img('assets/spotify/skip_0.png', (50, 50)),
                 load_img('assets/spotify/skip_1.png', (50, 50))),
        'mute': load_img('assets/spotify/mute.png', (50, 50)),
        'vol 0': load_img('assets/spotify/vol_0.png', (50, 50)),
        'vol 50': load_img('assets/spotify/vol_50.png', (50, 50)),
        'vol 100': load_img('assets/spotify/vol_100.png', (50, 50)),
        'vol -': (load_img('assets/spotify/vol_-_0.png', (50, 50)),
                  load_img('assets/spotify/vol_-_1.png', (50, 50))),
        'vol +': (load_img('assets/spotify/vol_+_0.png', (50, 50)),
                  load_img('assets/spotify/vol_+_1.png', (50, 50)))}})


# CLASSES
class BACKLIGHT(Logging):
    _mqtt_request = '/miniplayer/backlight/request'
    _mqtt_response = '/miniplayer/backlight'
    pin = Config.conf['BACKLIGHT_PIN']
    freq = 500

    def __init__(self):
        super().__init__('Backlight')
        if Config.conf['BACKLIGHT_CONTROL'] == 2 and pigpio:
            self._pi = pigpio.pi()
            self._pi.set_mode(self.pin, pigpio.OUTPUT)
        self.software_dim = pg.surface.Surface((WIDTH, HEIGHT))
        self.brightness = 0
        self.state = False
        Mqtt.subscribe(self._mqtt_response, self.receive, retain=True)
        self.log(f"Running in mode {Config.conf['BACKLIGHT_CONTROL']}")
        self.set(100)
        if Config.conf['BACKLIGHT_CONTROL']:  # If enabled, request from Node-Red
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
        brightness += Config.conf['BRIGHTNESS_OFFSET']  # Add offset to brightness
        self.brightness = 100 if brightness > 100 else (0 if brightness < 0 else brightness)  # Constrain to 0-100
        if Config.conf['BACKLIGHT_CONTROL'] == 2 and pigpio:
            self._pi.hardware_PWM(self.pin, self.freq, self.brightness * 10000)
        elif Config.conf['BACKLIGHT_CONTROL'] == 1:  # Software dimming
            self.brightness = Config.conf['MINIMUM_BRIGHTNESS'] if (
                    self.brightness < Config.conf['MINIMUM_BRIGHTNESS']) else self.brightness  # Limit
            self.software_dim.set_alpha(255 - round(self.brightness / 100 * 255))
        self.log(f'Set brightness to {self.brightness}')

    def stop(self):
        self.set(0)
        if Config.conf['BACKLIGHT_CONTROL'] == 2 and pigpio:
            self._pi.stop()
        self.log('Backlight stopped')


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
            Logging('main').handle(err)
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
                Logging('main').handle(err)
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
    _mqtt_active = f'/miniplayer/spotify/active/{MQTT.mac_address}'
    _mqtt_action = '/miniplayer/spotify/action'
    _mqtt_response = '/miniplayer/spotify/response'
    _pending_action_length = 12000

    def __init__(self):
        super().__init__('Spotify')
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
                self.err(f'Failed to load playlist image (url={url})')
                return pg.surface.Surface((140, 140))
        else:
            self.err(f'Failed to get playlist image (code={response.status_code}, url={url})')
            return pg.surface.Surface((140, 140))

    def _load_default(self):
        cover = pg.surface.Surface((300, 300))
        cover.set_alpha(150)
        self._data = {'icon': (Img['spotify']['logo'],
                               Img['spotify']['logo'].get_rect(center=(CENTER[0], Menu.left[1].centery))),
                      'bg': None,
                      'explicit': (Img['spotify']['explicit'], Img['spotify']['explicit'].get_rect()),
                      'album_cover': (cover, cover.get_rect(topleft=(100, 125))),
                      'pause': Img['spotify']['pause'],
                      'play': Img['spotify']['play'],
                      'shuffle': Img['spotify']['shuffle'],
                      'shuffle_active': Img['spotify']['shuffle_active'],
                      'repeat': Img['spotify']['repeat'],
                      'save': Img['spotify']['save'],
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
        self.log('Fetching playlists..')
        try:  # Request data from Node-RED
            response = requests.get(
                f"http://{Config.conf['NODERED_IP']}:{Config.conf['NODERED_PORT']}/spotify/playlists", timeout=10)
        except Exception as err:
            self._playlists = []
            self.err('Playlist fetch failed', data=err)
            return False

        if response.status_code == 200:
            self.log('Playlists fetched successfully')
            try:
                playlists = json.load(io.BytesIO(response.content))  # Decode response
                temp = {}  # Playlist by id
                for playlist in playlists['items']:  # For each playlist
                    temp.update({playlist['id'].replace('spotify:playlist:', ''): playlist})  # Set id as key in dict
                playlists = temp  # Reuse playlists as playlist by id
                self._playlists = []  # Clear previous playlists
                for key in Config.setting['Playlist Order']:  # For each ordered playlist add known playlists in order
                    try:
                        self._playlists.append(playlists[key.replace('spotify:playlist:', '')])
                    except KeyError:
                        Config.setting['Playlist Order'].remove(key)
                        self.log(f"Removed invalid playlist from settings ('{key}')")
                for key in playlists:  # For every playlist
                    if key not in Config.setting['Playlist Order']:  # If unknown
                        self._playlists.append(playlists[key])  # Add unknown playlists to end
                        Config.setting['Playlist Order'].append(playlists[key]['id'])  # Add to known playlists
                self.log('Playlists ordered successfully')
                Config.save_settings()  # Save playlist order
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
                self.handle(err)
                self.err('Playlist ordering failed')
                return False
        else:
            self._playlists = []
            temp = f"http://{Config.conf['NODERED_IP']}:{Config.conf['NODERED_PORT']}/spotify/playlists"
            self.err(f"Playlist fetch failed (code={response.status_code} url={temp})")
            return False

    def _update_playlists(self, uid: str):
        response = requests.get(
            f"http://{Config.conf['NODERED_IP']}:{Config.conf['NODERED_PORT']}/spotify/playlists?id={uid}")
        if response.status_code == 200:  # Fetch playlist
            try:
                playlist = json.load(io.BytesIO(response.content))  # Decode response
                if playlist['id'] == 'spotify:user:ag.bungee:collection':
                    return False
                else:
                    self._playlists.append(playlist)
                    Config.setting['Playlist Order'].append(playlist['id'])
                    Config.save_settings()
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
        Config.setting['Playlist Order'] = temp
        Config.save_settings()

    def _liked(self, track_id: str, state=None):
        try:  # Request data from Node-RED
            request = (f"http://{Config.conf['NODERED_IP']}:{Config.conf['NODERED_PORT']}/spotify/saved?id={track_id}" +
                       (f"&state={state}" if state is not None else ''))
            response = requests.get(request, timeout=10)
        except Exception as err:
            self._liked_song = None
            self.err('Liked song failed', data=err)
            return

        if response.status_code == 200:
            self._liked_song = json.load(io.BytesIO(response.content))[0]
            self.log(f'Liked song response: {self._liked_song}')  # Decode response

        else:
            self._liked_song = None
            self.err(f"Liked song failed (code={response.status_code} "
                     f"url={request})")
            return

    def reload_playlists(self) -> bool:
        self._playlists = []
        self._active_playlist = None
        return self._get_playlists()

    def receive(self, client, data, message):
        if data or client:
            pass
        if message.topic == self._mqtt_response:
            try:
                msg = json.loads(message.payload.decode())
                if msg != {}:
                    self._playing = True
                else:
                    self._playing = False
                    return

                if msg['currently_playing_type'] != 'track':
                    self.err(f"Spotify is not playing a track! ('{msg['currently_playing_type']}')", cat='WRN')

                # Fetch album artwork
                if msg['item']['album']['images'][0]['url'] != self.value['item']['album']['images'][0]['url']:
                    temp = WIDTH if WIDTH > HEIGHT else HEIGHT  # Fit to screen (keep aspect ratio 1:1)
                    cover = pg.transform.smoothscale(pg.image.load(io.BytesIO(
                        requests.get(msg['item']['album']['images'][0]['url']).content)), (temp, temp))
                    cover_crop = pg.surface.Surface((WIDTH, HEIGHT))
                    cover_crop.blit(cover, (CENTER[0] - cover.get_rect().centerx, CENTER[1] - cover.get_rect().centery))
                    cover_crop.set_alpha(80)
                    self._data['bg'] = cover_crop, (0, 0)
                    cover = pg.transform.smoothscale(cover, (300, 300))
                    self._data['album_cover'] = cover, cover.get_rect(topleft=(100, 125))

                if msg['context'] is not None:
                    if msg['context']['type'] == 'playlist':
                        msg['context']['uri'] = msg['context']['uri'].replace('spotify:playlist:', '')
                        # If current song is in playlist
                        if msg['context']['uri'] and ':collection' not in msg['context']['uri']:
                            if msg['context']['uri'] not in Config.setting['Playlist Order']:  # If unknown
                                self._update_playlists(msg['context']['uri'])  # Fetch new
                            try:
                                self._active_playlist = self._playlists[Config.setting[
                                    'Playlist Order'].index(msg['context']['uri'])]  # Set current
                            except:
                                self._active_playlist = None
                        else:
                            self._active_playlist = None
                else:
                    self.value.update({'context': {'type': '', 'uri': ''}})

                if msg['item']['id'] != self.value['item']['id']:  # If new song is playing
                    self._liked(msg['item']['id'])  # Ask nodered if it is liked or not

                msg['item']['name'] = self._shorten(msg['item']['name'])  # Format and convert values to look nice
                msg['item']['duration_ms'] = int(msg['item']['duration_ms'])
                msg['item'].update({'duration': convert_s(msg['item']['duration_ms'] // 1000)})
                msg['progress_ms'] = int(msg['progress_ms'])
                msg.update({'progress': convert_s(msg['progress_ms'] // 1000)})
                msg['item']['album']['name'] = self._shorten(msg['item']['album']['name'])
                msg['device']['name'] = msg['device']['name'].lower().title().replace("'S", "'s")

                self.value = msg  # Set values as msg (all data is now ready for display)

                self._update_ms = pg.time.get_ticks()  # Set time for progress bar

                self.timestamp = strftime('%H:%M')
                if self._timestamp_color != Colour['green']:
                    self._timestamp_color = Colour['green']

            except Exception as err:
                self.handle(err)
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
        Mqtt.send(self._mqtt_active, True)  # Tell Node-RED spotify is active
        self.active = True
        self.log('Started')

    def stop(self):
        if not self.active:
            self.err('Stop called without starting', cat='WRN')
            return

        self.log('Stopping..')
        Mqtt.send(self._mqtt_active, False)  # Tell Node-RED spotify is not active
        Mqtt.unsubscribe(self._mqtt_response)
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
            surf.blit(*render_text(self.value['item']['duration'], 30, Colour['white'], bold=True,  # DURATION
                                   midleft=(bar[1].right + 30, bar[1].centery + 1)))

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

        if Config.setting['Device Info']:
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
                    self.value['progress_ms'] + 1000 < self.value['item']['duration_ms']:  # If showing and needs update
                self._update_ms = pg.time.get_ticks()
                self.value['progress_ms'] += 1000
                self.value['duration'] = convert_s(self.value['progress_ms'] // 1000)
                self.value['progress'] = convert_s(self.value['progress_ms'] // 1000)
            elif self.value['progress_ms'] + 1000 >= self.value['item']['duration_ms']:
                self.value['progress_ms'] = self.value['item']['duration_ms']
                self.value['progress'] = convert_s(self.value['progress_ms'] // 1000)

            if self.show_playlists:  # PLAYLISTS
                if not Button_cooldown and (not Config.conf['TOUCHSCREEN'] and pg.mouse.get_pressed()[0] or
                                            Config.conf['TOUCHSCREEN'] and pg.mouse.get_pos() != Prev_mouse_pos):
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
                                Mqtt.send(self._mqtt_action, {'playlist': 0,
                                                              'params': [{'device_id': self.value['device']['id'],
                                                                          'context_uri': plist['uri']}]})
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

            else:  # CONTROLS
                action = {}
                if not Settings.active and not self.show_playlists and not Button_cooldown and (
                        not Config.conf['TOUCHSCREEN'] and pg.mouse.get_pressed()[0] or
                        Config.conf['TOUCHSCREEN'] and pg.mouse.get_pos() != Prev_mouse_pos):
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
                    elif self._data['far_right_2'].collidepoint(Mouse_pos) and self._liked_song is not None:  # Save
                        self._liked(self.value['item']['id'], state=False if self._liked_song else True)  # http
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
                        action = self._config_params(action)  # Attach device_id to parameters
                        self._pending_action = action
                        Mqtt.send(self._mqtt_action, action)

                    if self._data['far_left_2'].collidepoint(Mouse_pos):  # PLAYLISTS (open)
                        Button_cooldown = pg.time.get_ticks() + Button_cooldown_length
                        Menu.allow_controls = False
                        self.show_playlists = True
                        self.log('Opened playlists')

                temp = tuple(self._pending_action.keys())  # Action confirmed
                if (('pause' in temp or 'play' in temp) and self.value['is_playing'] != self._prev_value or
                        ('skip' in temp or 'rewind' in temp) and self.value['item']['name'] != self._prev_value or
                        ('volume_+' in temp or 'volume_-' in temp) and
                        self.value['device']['volume_percent'] != self._prev_value or
                        'shuffle' in temp and self.value['shuffle_state'] != self._prev_value or
                        'repeat' in temp and self.value['repeat_state'] != self._prev_value):
                    self.log(f'{temp[0].title()} confirmed')
                    set_info(f"{temp[0].title().replace('_', ' ')} confirmed")
                    self._action_time = 0
                    self._prev_value = None
                    self._pending_action = {}

                if self._action_time and pg.time.get_ticks() >= self._action_time:  # Action timed out
                    self.err(f'{self._pending_action} timed out')
                    self._timeout_time = pg.time.get_ticks() + 5000
                    self._action_time = 0
                    self._prev_value = None
                    self._pending_action = {}


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
                msg = json.loads(message.payload.decode())
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
                self.handle(err)
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


def main():
    global Current_window, Button_cooldown, Mouse_pos, Prev_mouse_pos
    while True:  # Forever loop
        # mainloop_time = timer()
        while Loading_ani.active:
            pg.time.wait(250)  # Wait for animation to finish if playing
        if Mqtt.reconnect_pending:
            Mqtt.reconnect()  # Reconnect sequence in main thread instead of threaded (issues if threaded)

        Clock.tick(Config.conf['FPS'])
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
            Logging('main').handle(err)
        except:
            print('main() failed -> unknown')

        if pg.time.get_ticks() >= Button_cooldown:  # Button cooldown reset
            Button_cooldown = 0

        if Info[0] and Info[2] > pg.time.get_ticks():  # Show info
            Display.blit(*render_text(Info[0], 30, Info[1], bold=True, midbottom=(CENTER[0], HEIGHT - 10)))

        if Config.conf['BACKLIGHT_CONTROL'] == 1:  # Display brightness through software
            Display.blit(Backlight.software_dim, (0, 0))

        Prev_mouse_pos = Mouse_pos
        pg.display.update()
        # print(f'Mainloop: {convert_ms(mainloop_time)}ms')


def quit_all():
    if Loading_ani:
        Loading_ani.stop()
    if Settings.active:
        Config.save_settings()
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
        if Config.conf['LOGGER']:
            with open('miniplayer.log', 'a') as log:
                log.write(f"\n[{datetime.now().strftime('%x %X')}][NEW][Main] NEW_INSTANCE.\n")
                if Config.conf['DEBUG']:
                    log.write(f"\n[{datetime.now().strftime('%x %X')}][DBG][Main] DEBUG ON.\n")
        with open('miniplayer_err.log', 'a') as error:
            error.write(f"\n[{datetime.now().strftime('%x %X')}][NEW][Main] NEW_INSTANCE.\n")
            if Config.conf['DEBUG']:
                error.write(f"\n[{datetime.now().strftime('%x %X')}][DBG][Main] DEBUG ON.\n")

    except (Exception, BaseException) as error:
        Logging('main').handle(error, save=False)  # Do not save as error with logging
        LOGGING = False
    except:
        print('Failed to start log -> unknown')
        LOGGING = False

    if Config.setting['TOUCHSCREEN']:  # Hide mouse if touchscreen
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
    if Config.conf['BACKLIGHT_CONTROL'] == 2 and pigpio:
        try:
            g_temp = pigpio.pi()
            g_temp.set_mode(BACKLIGHT.pin, pigpio.OUTPUT)
            g_temp.hardware_PWM(BACKLIGHT.pin, BACKLIGHT.freq, 1000000)
        except (Exception, BaseException) as error:
            Logging('main').handle(error)
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
        Logging('main').handle(error)
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
    if Config.conf['DEBUG']:  # Start main() without error handling if debugging
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
            Logging('main').handle(error)
        except:
            print('Unhandled exception -> main()')
        finally:  # Stop all windows and close after error handling
            quit_all()
