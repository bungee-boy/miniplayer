from window import *  # Window base class

class WeatherWindow(WindowBase):
    _mqtt_active = 'miniplayer/weather/active'  # MQTT topics
    _mqtt_response = 'miniplayer/weather/response'

    def __init__(self):
        super().__init__('Weather')

        # Create / setup drawing surfaces
        self._surf = {
            'logo': self._Ui.load_image('assets\\spotify\\logo.png', (212, 64))
        }

        # Setup / create position & collision rectangles
        self._rect = {
            'logo': self._surf['logo'].get_rect(midtop=(self._Ui.Center[0], self._surf['logo'].get_rect().height / 2))
        }

        self._response = {

        }
