from window import *  # Window base class

import io  # To decode http requests
import requests  # To call http requests
import threading  # To load playlists on start


class SpotifyWindow(WindowBase):
    _mqtt_active = 'miniplayer/spotify/active'  # MQTT topics
    _mqtt_action = 'miniplayer/spotify/action'
    _mqtt_response = 'miniplayer/spotify/response'

    _nodered_url = "http://homeassistant.local:1880/endpoint"  # Node-red HTTP request

    _guideline_mode = False  # Changes UI to adhere to spotify guidelines (https://developer.spotify.com/documentation/design#playing-views)

    def __init__(self):
        super().__init__('Spotify')

        self._Ui.add_colours({  # Add custom colours to Ui
            'Spotify': pg.Color(30, 215, 96)
        })

        # Create / setup drawing surfaces
        self._surf = {
            'logo': self._Ui.load_image('assets\\spotify\\logo.png', (212, 64)),
            'background': pg.surface.Surface((self._Ui.Width, self._Ui.Height)),
            'album_cover': pg.surface.Surface((300, 300)).convert_alpha(),
            'explicit': self._Ui.load_image('assets\\spotify\\explicit.png'),
            'pause': (self._Ui.load_image('assets\\spotify\\pause_0.png'),
                      self._Ui.load_image('assets\\spotify\\pause_1.png')),
            'play': (self._Ui.load_image('assets\\spotify\\play_0.png'),
                     self._Ui.load_image('assets\\spotify\\play_1.png')),
            'shuffle': (self._Ui.load_image('assets\\spotify\\shuffle_0.png'),
                        self._Ui.load_image('assets\\spotify\\shuffle_1.png')),
            'shuffle_active': (self._Ui.load_image('assets\\spotify\\shuffle_active_0.png'),
                               self._Ui.load_image('assets\\spotify\\shuffle_active_1.png')),
            'repeat': (self._Ui.load_image('assets\\spotify\\repeat_0.png'),
                       self._Ui.load_image('assets\\spotify\\repeat_1.png'),
                       self._Ui.load_image('assets\\spotify\\repeat_2.png')),
            'liked': (self._Ui.load_image('assets\\spotify\\like.png'),
                     self._Ui.load_image('assets\\spotify\\liked.png')),
            'skip': (self._Ui.load_image('assets\\spotify\\skip_0.png'),
                     self._Ui.load_image('assets\\spotify\\skip_1.png')),
            'rewind': (pg.transform.flip(self._Ui.load_image('assets\\spotify\\skip_0.png'), True, False),
                       pg.transform.flip(self._Ui.load_image('assets\\spotify\\skip_1.png'), True, False)),
            'mute': self._Ui.load_image('assets\\spotify\\mute.png'),
            'volume': (self._Ui.load_image('assets\\spotify\\vol_0.png'),
                       self._Ui.load_image('assets\\spotify\\vol_50.png'),
                       self._Ui.load_image('assets\\spotify\\vol_100.png')),
            'volume-': (self._Ui.load_image('assets\\spotify\\vol_-_0.png'),
                        self._Ui.load_image('assets\\spotify\\vol_-_1.png')),
            'volume+': (self._Ui.load_image('assets\\spotify\\vol_+_0.png'),
                        self._Ui.load_image('assets\\spotify\\vol_+_1.png'))
        }

        self._surf.update({
            'plist': {
                'button': self._Ui.load_image('assets\\spotify\\playlist_1.png'),
                'background': pg.surface.Surface((self._Ui.Width, self._Ui.Height)),
                'cross': self._Ui.load_image('assets\\ui\\cross.png')
            }
        })

        # Set playlist background to transparent
        self._surf['plist']['background'].set_alpha(150)

        # Draw rounded rect to album cover
        self._surf['album_cover'].fill(pg.Color(0, 0, 0, 0))
        self._surf['album_cover'].set_alpha(130)
        pg.draw.rect(self._surf['album_cover'], (0, 0, 0), self._surf['album_cover'].get_rect(), 0, 15)

        # Setup / create position & collision rectangles
        media_surf = pg.surface.Surface((50, 50))
        self._rect = {
            'logo': self._surf['logo'].get_rect(midtop=(self._Ui.Center[0], self._surf['logo'].get_rect().height / 2)),
            'album_cover': self._surf['album_cover'].get_rect(topleft=(100, 125)),
            'pause': media_surf.get_rect(center=(self._Ui.Center[0], self._Ui.Center[1] + 160)),
            'explicit': self._surf['explicit'].get_rect(),
            'plist': {  # Playlist
                'pause': media_surf.get_rect(center=(self._Ui.Center[0], self._Ui.Center[1] + 160)),
                'scroll_u': media_surf.get_rect(topright=(self._Ui.Right, self._Ui.Top + 82)),
                'scroll_d': media_surf.get_rect(bottomright=(self._Ui.Right, self._Ui.Bottom - 16)),
                'cross': self._surf['plist']['cross'].get_rect(topright=(self._Ui.Right, self._Ui.Top))
            },
            'volume': {
                'left': pg.rect.Rect(0, 0, 50, 50),
                'right_1': pg.rect.Rect(0, 0, 50, 50),
                'right_2': pg.rect.Rect(0, 0, 50, 50)
            }
        }

        top = self._rect['pause'].top
        self._rect.update({'rewind': media_surf.get_rect(topright=(self._rect['pause'].left - 50, top))})
        self._rect.update({'shuffle': media_surf.get_rect(topright=(self._rect['rewind'].left - 50, top))})
        self._rect['plist'].update({'button': media_surf.get_rect(topright=(self._rect['shuffle'].left - 50, top))})
        self._rect.update({'skip': media_surf.get_rect(topleft=(self._rect['pause'].right + 50, top))})
        self._rect.update({'repeat': media_surf.get_rect(topleft=(self._rect['skip'].right + 50, top))})
        self._rect.update({'liked': media_surf.get_rect(topleft=(self._rect['repeat'].right + 50, top))})

        # Song data
        self._is_cover_loaded = False
        self._is_active = False  # If song is open/active
        self._is_playing = None  # If song is playing
        self._is_shuffle = None  # If shuffling

        self._response = {
            'device': {
                'name': '',
                'type': '',
                'supports_volume': False,
                'volume_percent': 0
            },
            'shuffle_state': False,
            'repeat_state': 'off',
            'context': {
                'type': '',
                'uri': ''
            },
            'progress_ms': 0,
            'item': {
                'album': {
                    'images': [{ 'url': '' }, { 'url': '' }, { 'url': '' }],
                    'name': '-'
                },
                'artists': [{ 'name': '-' }],
                'duration_ms': 0,
                'duration': '-:--',
                'explicit': False,
                'id': '',
                'name': 'Not playing'
            },
            'currently_playing_type': '',
            'is_playing': False
        }

        self._action_pending = False
        self._actions = {
            'pause': 0,
            'play': 0,
            'shuffle': 0,
            'repeat': 0,
            'skip': 0,
            'rewind': 0,
            'params': []
        }

        self._liked_thread = threading.Thread(name='spotify_fetch_liked', target=self._fetch_liked_song)
        self._is_liked = None

        # TODO: Playlist image loading/cache/sorting
        self._playlist_thread = threading.Thread(name='spotify_fetch_playlists', target=self._fetch_playlists)
        self._playlists = []  # Playlists
        self._current_playlist = -1  # Index of current playlist in self._playlists (-1!)
        self._view_playlists = False
        self._playlist_liked_songs = False

        self._artists = 'None'  # Artists string

        self._duration_ms = 0  # Duration in ms
        self._duration = "0:00"  # Duration string
        self._progress_ms = 0  # Progress in ms
        self._progress = "0:00"  # Progress string
        self._progress_timestamp = 0  # Timestamp of last progress update

    def draw(self) -> None:
        if self._is_cover_loaded:
            self._Ui.Display.blit(self._surf['background'], (0, 0))
        else:
            self._Ui.background()

        self._Ui.Display.blit(self._surf['logo'], self._rect['logo'])

        # Album cover
        self._Ui.Display.blit(self._surf['album_cover'], self._rect['album_cover'])

        # Song, Artist, Album name
        txt = self._Ui.text(self._response['item']['name'], 35, bold=True,
                      bottomleft=(self._rect['album_cover'].right + 25,
                                  self._rect['album_cover'].top + self._rect['album_cover'].height / 4))

        if not self._is_active:  # Do not show more if not playing
            return

        self._Ui.text(self._artists, 35, bold=False,
                midleft=(txt[1].left, self._rect['album_cover'].centery))
        self._Ui.text(self._response['item']['album']['name'], 35, bold=False,
                topleft=(txt[1].left, self._rect['album_cover'].centery + self._rect['album_cover'].height / 4))

        # Explicit icon
        if self._response['item']['explicit']:
            self._rect['explicit'].midleft = (txt[1].right + 15, txt[1].centery)
            self._Ui.Display.blit(self._surf['explicit'], self._rect['explicit'])

        # Progress bar & timestamps
        bar = self._Ui.bar((800, 16), self._progress_ms, 0, self._duration_ms,
                     midtop=(self._Ui.Center[0], self._rect['pause'].bottom + 40))
        self._Ui.text(self._progress, 30, midright=(bar[1].left - 30, bar[1].centery + 1))
        self._Ui.text(self._duration, 30, midleft = (bar[1].right + 30, bar[1].centery + 1))

        # Buttons
        self._Ui.Display.blit(self._surf['pause' if self._is_playing else 'play']
                              [not (self._actions['pause'] or self._actions['play'])], self._rect['pause'])  # Pause/Play
        self._Ui.Display.blit(self._surf['skip'][not self._actions['skip']], self._rect['skip'])  # Skip
        self._Ui.Display.blit(self._surf['rewind'][not self._actions['rewind']], self._rect['rewind'])  # Rewind
        self._Ui.Display.blit(self._surf['shuffle_active' if self._is_shuffle else 'shuffle']
                              [not self._actions['shuffle']], self._rect['shuffle'])  # Shuffle
        self._Ui.Display.blit(self._surf['repeat'][1], self._rect['repeat'])  # Repeat
        if type(self._is_liked) is bool:
            self._Ui.Display.blit(self._surf['liked'][self._is_liked], self._rect['liked'])  # Liked
        if not self._view_playlists and self._playlists:
            self._Ui.Display.blit(self._surf['plist']['button'], self._rect['plist']['button'])  # Playlist button
            if self._current_playlist > -1:  # If current song is in playlist
                self._Ui.text(self._playlists[self._current_playlist]['name'], 20, colour="Grey", bold=False,  # Playlist name
                              midright=(self._rect['plist']['button'].left - 25, self._rect['plist']['button'].centery))
            elif self._playlist_liked_songs:
                self._Ui.text("Liked Songs", 20, colour="Grey", bold=False,  # Liked songs
                              midright=(self._rect['plist']['button'].left - 25, self._rect['plist']['button'].centery))

        # TODO: Playlist menu
        if self._view_playlists:
            self._Ui.Display.blit(self._surf['plist']['background'], (0, 0))
            self._Ui.Display.blit(self._surf['plist']['cross'], self._rect['plist']['cross'])

    def update(self) -> None:
        # Update progress bar (every second)
        if self._is_playing and pg.time.get_ticks() - self._progress_timestamp >= 1000:  # Increment /s
            self._progress_ms += pg.time.get_ticks() - self._progress_timestamp
            self._progress = self._convert_seconds(self._progress_ms // 1000)
            self._progress_timestamp = pg.time.get_ticks()

        elif self._is_playing and self._progress_ms != self._duration_ms and self._progress_ms + 1000 >= self._duration_ms:  # Stop at end
            self._progress_ms = self._duration_ms
            self._progress = self._duration
            self._progress_timestamp = pg.time.get_ticks()  # Always reset timestamp (disable updating)

        # Inputs / Actions
        if (self._is_active and not self._view_playlists and self._playlists and
                self._Ui.input(self._rect['plist']['button'])):  # Playlist
            self._view_playlists = True
            self.log("Opened playlist menu", LogLevel.INF)

        elif not self._view_playlists:
            if self._is_active and type(self._is_liked) is bool and self._Ui.input(self._rect['liked']):  # Liked song
                self.log("Liked song pressed, requesting...", LogLevel.INF)
                self._Ui.show_info("Adding to Liked Songs" if not self._is_liked else "Removing from Liked Songs",
                             colour='Spotify')
                # Change liked
                self._liked_thread = threading.Thread(name='spotify_fetch_liked', target=self._fetch_liked_song,
                                                      args=(self._response['item']['id'], not self._is_liked))
                self._liked_thread.start()

            if self._is_active and not self._action_pending:  # Check actions
                if not self._actions['pause'] and self._is_playing and self._Ui.input(self._rect['pause']):  # Pause
                    self._actions['pause'] = 1
                    self._action_pending = True
                    self.log("Pause button pressed!", LogLevel.INF)
                if not self._actions['play'] and not self._is_playing and self._Ui.input(self._rect['pause']):  # Play
                    self._actions['play'] = 1
                    self._action_pending = True
                    self.log("Play button pressed!", LogLevel.INF)

                for button in ['shuffle', 'skip', 'rewind', 'repeat']:  # Multiple buttons
                    if not self._actions[button] and self._Ui.input(self._rect[button]):
                        self._actions[button] = 1
                        self._action_pending = True
                        self.log(button.title() + " button pressed!", LogLevel.INF)

                if self._action_pending:  # If action has happened then send to node-red
                    if self._actions['shuffle']:  # Shuffle has been pressed
                        self._actions['params'].append(str(not self._is_shuffle).lower())  # Add desired state to params

                    self._actions['params'].append({"device_id": self._response['device']['id']})

                    self._Mqtt.pub(self._mqtt_action, self._actions)

        elif self._view_playlists:
            if self._Ui.input(self._rect['plist']['cross']):  # Cross
                self._view_playlists = False
                self.log("Closed playlist menu", LogLevel.INF)

    def _start(self) -> None:
        self._Mqtt.sub(self._mqtt_response, self._receive)
        self._Mqtt.pub(self._mqtt_active, { self._Mqtt.get_id(): 1 })  # Send active
        self._playlists = []  # Clear existing playlists
        self._playlist_thread = threading.Thread(name='spotify_fetch_playlists', target=self._fetch_playlists)
        self._playlist_thread.start()  # Load playlists on a thread

    def _stop(self) -> None:
        self._Mqtt.unsub(self._mqtt_response)
        self._Mqtt.pub(self._mqtt_active, { self._Mqtt.get_id(): 0 })

    def _receive(self, client, userdata, msg) -> None:
        self.log("Received a message!", LogLevel.INF)
        if msg.topic != self._mqtt_response:
            return  # Message not for me

        msg = json.loads(msg.payload.decode())  # Convert string response to dict (json)

        if msg is None:  # Check if currently playing
            self._is_playing = False
            self.log("Message was null!", LogLevel.WRN)
            return

        if not msg:  # Not active (no player open)
            self._response = {  # Reset response
                'device': {
                    'name': '',
                    'type': '',
                    'supports_volume': False,
                    'volume_percent': 0
                },
                'shuffle_state': False,
                'repeat_state': 'off',
                'context': {
                    'type': '',
                    'uri': ''
                },
                'progress_ms': 0,
                'item': {
                    'album': {
                        'images': [{ 'url': '' }, { 'url': '' }, { 'url': '' }],
                        'name': '-'
                    },
                    'artists': [{ 'name': '-' }],
                    'duration_ms': 0,
                    'duration': '-:--',
                    'explicit': False,
                    'id': '',
                    'name': 'Not playing'
                },
                'currently_playing_type': '',
                'is_playing': False
            }

            # Don't show album artwork
            self._is_cover_loaded = False

            # Draw rounded rect to album cover
            self._surf['album_cover'].fill(pg.Color(0, 0, 0, 0))
            self._surf['album_cover'].set_alpha(130)
            pg.draw.rect(self._surf['album_cover'], (0, 0, 0), self._surf['album_cover'].get_rect(), 0, 15)

            # Reset progress
            self._progress_ms = 0
            self._duration_ms = 0
            self._progress = "--:--"
            self._duration = "--:--"

            # Reset artists
            self._artists = ""

            self._is_active = False
            return

        if type(msg) != dict:  # Make sure message is dict
            self.log("Message was not a dict!", LogLevel.WRN, "type: " + str(type(msg)) + ", msg: " + str(msg))
            return

        # Spotify is active and either playing or paused, show song info

        # Load album cover (if changed)
        cover_url = msg['item']['album']['images'][0]['url']
        if cover_url != self._response['item']['album']['images'][0]['url']:
            self.log("Fetching album artwork", LogLevel.INF, data="url: " + cover_url)

            screen_size = self._Ui.Width if self._Ui.Width > self._Ui.Height else self._Ui.Height  # Get largest screen dimension (1:1 image)
            image = pg.transform.smoothscale(pg.image.load(io.BytesIO(
                requests.get(cover_url).content)), (screen_size, screen_size))  # Download image
            cover = pg.transform.smoothscale(image, self._rect['album_cover'].size)  # Scale image to album cover

            background = pg.surface.Surface((self._Ui.Width, self._Ui.Height))  # Create surf of screen size (efficient)
            if not self._guideline_mode:  # Show image as bg
                background.blit(image, (self._Ui.Center[0] - image.get_rect().center[0],
                    self._Ui.Center[1] - image.get_rect().center[1]))  # Blit image to screen (centered)
            else:  # Show most common colour
                background.fill(image.get_at(image.get_rect().midleft))  # Set bg to colour of artwork at mid-left
            background.set_alpha(80 if not self._guideline_mode else 100)  # Dim the background

            self._surf['album_cover'] = cover  # Update to show new images
            self._surf['background'] = background
            self._response['item']['album']['images'][0]['url'] = cover_url
            self._is_cover_loaded = True
            self.log("Album artwork loaded successfully!", LogLevel.INF)

        # Device data
        self._response['device'] = msg['device']

        # Song name, album name, duration etc...
        self._response['item']['name'] = self._shorten_name(msg['item']['name'])
        self._response['item']['duration_ms'] = int(msg['item']['duration_ms'])
        self._response['progress_ms'] = int(msg['progress_ms'])
        self._response['item']['album']['name'] = self._shorten_name(msg['item']['album']['name'])

        self._progress_ms = msg['progress_ms']
        self._duration_ms = msg['item']['duration_ms']
        self._progress = self._convert_seconds(self._progress_ms // 1000)
        self._duration = self._convert_seconds(self._duration_ms // 1000)

        # Artist name(s)
        self._response['item']['artists'] = msg['item']['artists']  # Copy artist data to response (not shown directly)
        self._artists = self._response['item']['artists'][0]['name']  # Always show first artist
        for index in range(1, len(self._response['item']['artists'])):  # If >1 artist, show all with ", "
            self._artists += ", " + self._response['item']['artists'][index]['name']

        self._progress_timestamp = pg.time.get_ticks()  # Refresh timestamp to known time

        # Set UI to show everything
        self._is_active = True
        self._response['is_playing'] = msg['is_playing']
        self._is_playing = self._response['is_playing']

        # Actions (reset)
        if self._action_pending:  # If waiting for action, check each for result
            if self._actions['pause'] and not self._is_playing:  # Pause
                self._actions['pause'] = 0
            if self._actions['play'] and self._is_playing:  # Play
                self._actions['play'] = 0
            if self._actions['shuffle'] and msg['shuffle_state'] != self._response['shuffle_state']:  # Shuffle
                self._actions['shuffle'] = 0
            if self._actions['skip'] and msg['item']['id'] != self._response['item']['id']:  # Skip
                self._actions['skip'] = 0
            if self._actions['rewind'] and msg['item']['id'] != self._response['item']['id']:  # Rewind
                self._actions['rewind'] = 0

            # If all actions have been met, clear pending
            pending_actions = 0
            for action_value in self._actions.values():  # Count pending actions
                if type(action_value) == int:
                    pending_actions += action_value

            if pending_actions == 0:
                self._action_pending = False
                self._actions['params'].clear()  # Clear params
                self.log("Actions reset", LogLevel.INF)

        # Sync shuffle state
        self._response['shuffle_state'] = msg['shuffle_state']
        self._is_shuffle = self._response['shuffle_state']

        # End of time-critical code, below takes longer to load and is done last

        # TODO: Find current playlist
        if msg['context'] is not None:
            if msg['context']['type'] == 'playlist':
                if self._current_playlist == -1:  # No active playlist
                    self._find_current_playlist(msg['context']['uri'])
                elif self._playlists[self._current_playlist]['uri'] == msg['context']['uri']:
                    pass  # Song is already in current playlist
                else:  # Active playlist, but doesn't match song
                    self._find_current_playlist(msg['context']['uri'])
                self._playlist_liked_songs = False
            elif msg['context']['type'] == 'collection':
                self._playlist_liked_songs = True
                self._current_playlist = -1
            else:
                self._current_playlist = -1

        self._response['context'] = msg['context']  # Update context to new

        if msg['item']['id'] != self._response['item']['id']:  # If new song is playing
            # Warning, blocking function! Takes a second or 2 to complete HTTP request/response
            self._fetch_liked_song(msg['item']['id'])  # Ask nodered if it is liked or not (already threading so okay to call directly)

        self._response['item']['id'] = msg['item']['id']  # Update current song to new one, end of song-related info

        #       if msg['context']['uri'] and ':collection' not in msg['context']['uri']:
        #           if msg['context']['uri'] not in Settings.value['Playlist Order']:  # If unknown
        #               self._update_playlists(msg['context']['uri'])  # Fetch new
        #           try:
        #               self.debug("Loading existing playlist")
        #               try:
        #                   self._active_playlist = self._playlists[Settings.value[
        #                       'Playlist Order'].index(msg['context']['uri'])]  # Set current
        #               except Exception as err:
        #                   self.handle(err, data="cause: Loading existing playlist from settings")
        #           except Exception as err:
        #               self.handle(err,
        #                           data="cause: Loading existing playlist, context: " + str(msg['context']))
        #               self.err("Loading existing playlist failed", data=f"context: {msg['context']}")
        #               self._active_playlist = None
        #       else:
        #           self._active_playlist = None
        #           self.debug("Set active_playlist to None")
        # else:
        #   self.value.update({'context': {'type': '', 'uri': ''}})
        #   self.debug("Set value context to None")

    def _fetch_liked_song(self, track_id: str, state=None) -> None:
        try:  # Request data from Node-RED
            url = self._nodered_url + "/spotify/liked"

            params = {"id": track_id}
            if state is not None:
                params.update({"state": state})

            self.log("Requesting liked song state", LogLevel.INF, data="url: " + url + ", params: " + str(params))
            response = requests.get(url, timeout=10, params=params)

        except Exception as err:
            self.handle(err, trace=False)
            self._is_liked = None
            self.log("Error fetching liked song state", LogLevel.WRN)
            return

        if response is not None and response.status_code == 200:  # Request succeeded
            self._is_liked = json.load(io.BytesIO(response.content))[0]  # Extract result (true/false)
            self.log("Liked song response: " + str(self._is_liked), LogLevel.INF,
                     data="code: " + str(response.status_code))  # Decode response
            return

        else:
            self._is_liked = None
            self.log("Liked song request failed", LogLevel.ERR, data="url: " + url)
            return

    def _fetch_playlists(self, uri=None) -> None:
        self._Ui.show_info("Loading playlists", colour='Spotify', timeout=0)
        try:  # Request data from Node-RED
            url = self._nodered_url + "/spotify/playlist"

            params = None
            if uri is not None:
                params = {"uri": uri}

            self.log("Requesting playlists", LogLevel.INF, data="uri: " + str(uri) + "url: " + url)
            response = requests.get(url, timeout=10, params=params)

        except Exception as err:
            self.handle(err, trace=False)
            self._playlists = []
            self.log("Error fetching playlists", LogLevel.WRN, data="uri: " + str(uri))
            self._Ui.show_info("Failed to load playlists", colour='Error')
            return

        if response is not None and response.status_code == 200:  # Request succeeded
            content = json.load(io.BytesIO(response.content))  # Decode response
            if "items" in content.keys():  # Multiple playlists
                for playlist in content["items"]:
                    self._playlists.append(playlist)  # Add results to playlists
            else:  # Single playlist
                self._playlists.append(content)  # Add result to existing playlists

            self.log("Playlist response: " + (str(self._playlists) if type(content) == dict else f"[{len(content)}]"),
                     LogLevel.INF, data="code: " + str(response.status_code) + "uri: " + str(uri))  # Output response
            self._Ui.clear_info()

        else:
            self._playlists = []
            self.log("Playlist request failed", LogLevel.ERR, data="uri: " + str(uri) + "url: " + url)
            self._Ui.show_info("Failed to load playlists", colour='Error')
            return

        if self._response['context'] is not None:  # If there is previous response, update to new playlists
            if self._response['context']['type'] == 'playlist':
                self._find_current_playlist(self._response['context']['uri'])

    def _find_current_playlist(self, uri: str) -> None:
        self.log("Finding playlist", LogLevel.INF, data="uri: " + uri)
        # Check if new playlist is in self._playlists
        for index in range(0, len(self._playlists)):
            if self._playlists[index]['uri'] == uri:
                self._current_playlist = index
                self.log("Found current playlist at index " + str(self._current_playlist), LogLevel.INF,
                         data="name: \"" + self._playlists[self._current_playlist]['name'] + "\"")
                break
        else:
            self._current_playlist = -1
            self.log("Could not find current playlist", LogLevel.INF, data="uri: " + uri)

    @staticmethod
    def _convert_seconds(seconds: int):
        minutes = 0
        hours = 0

        if seconds > 59:
            minutes = seconds // 60  # Evenly divide seconds into minutes
            seconds -= minutes * 60  # Subtract minutes from seconds

        if seconds < 10:
            seconds = '0' + str(seconds)

        if minutes > 59:
            hours = minutes // 60  # Evenly divide minutes into hours
            minutes -= hours * 60  # Subtract hours from minutes

        if not seconds:
            seconds = "00"

        if not minutes and not hours:
            minutes = '0'
        elif not minutes and hours:
            minutes = "00"

        if not hours:
            return str(minutes) + ':' + str(seconds)
        else:
            return str(hours) + ':' + str(minutes) + ':' + str(seconds)

    @staticmethod
    def _shorten_name(txt: str):
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
