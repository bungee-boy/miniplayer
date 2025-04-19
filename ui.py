from log import *
from enum import Enum
import pygame as pg


Colour = {
    'Key': pg.Color(1, 2, 3),
    'Error': pg.Color(255, 50, 50),
    'White': pg.Color(255, 255, 255),
    'Grey': pg.Color(150, 150, 150),
    'Black': pg.Color(0, 0, 0),
    'Amber': pg.Color(200, 140, 0),
    'LBlue': pg.Color(3, 140, 252),
}


class InputMethod(Enum):
    Mouse = 0
    Touch = 1


class Ui:
    _Assets = "./assets/ui/"
    _Fonts = {}
    _Images = {}

    def __init__(self, size: tuple[int, int], flags=0, display=0):
        self.Display = pg.display.set_mode(size, flags=flags, display=display)
        pg.display.set_caption("Miniplayer V3")
        pg.display.set_icon(pg.image.load(self._Assets + 'icon.ico'))

        Ui._Images['background'] = Ui.load_image(Ui._Assets + 'background.jpg', keep_alpha=False)

        # Screen anchor variables
        self.Width = self.Display.get_width()
        self.Height = self.Display.get_height()
        self.Center = self.Width / 2, self.Height / 2
        self.Top = 40
        self.Bottom = self.Height - 20
        self.Left = 20
        self.Right = self.Width - 20

        # Mouse / input variables
        self.Input_method = InputMethod.Mouse
        self.mouse_pos = 0, 0
        self.prev_mouse_pos = 0, 0

        self._info = '', 'Grey', 0  # Txt, Col, Time
        self._curr_brightness = 255
        self._brightnessSurf = pg.surface.Surface((self.Width, self.Height)).convert_alpha()

        self.set_brightness(self._curr_brightness)

    def set_brightness(self, brightness: int) -> None:
        self._curr_brightness = brightness
        self._brightnessSurf.set_alpha(255 - self._curr_brightness)

    def get_brightness(self) -> int:
        return self._curr_brightness

    def apply_brightness(self) -> None:
        self.Display.blit(self._brightnessSurf, (0, 0))

    def clear(self) -> None:
        self.Display.fill(Colour['Black'])

    def background(self, txt=False) -> None:
        self.Display.blit(Ui._Images['background'], (0, 0))
        if txt:
            txt = self.text('Miniplayer', 64, center=self.Center)
            self.text('v3.0', 32, bold=False, midtop=(txt[1].centerx, txt[1].bottom + 20))
            self.text('Anthony Guy', 20, bold=False, midbottom=(txt[1].centerx, self.Height - 80))

    def text(self, txt: str or int, size: int, colour='White', bold=True, draw=True, **kwargs)\
            -> tuple[pg.surface.Surface, pg.rect.Rect]:
        """
        :param txt: Text to render
        :param size: Font size
        :param colour: Font colour
        :param bold: Render in bold
        :param draw: Draw to display automatically
        :param kwargs: Arguments for pg.rect
        :return: A surface, rect tuple for blit
        """
        colour = Colour[colour]
        path = Ui._Assets + 'boldfont.ttf' if bold else Ui._Assets + 'thinfont.ttf'
        name = str(size) + path

        try:  # Cache loaded fonts in map
            loaded_font = Ui._Fonts[name]
        except KeyError:
            try:
                loaded_font = pg.font.Font(path, size)
            except FileNotFoundError or PermissionError:
                Log("UI").log("Failed to load font", LogLevel.WRN, "path: " + path)
                loaded_font = pg.font.Font(None, size)
            Ui._Fonts[name] = loaded_font

        surf = loaded_font.render(txt, True, colour)  # Render the text
        rect = surf.get_rect(**kwargs)

        if draw:
            self.Display.blit(surf, rect)
        return surf, rect  # Return surf rect pair with kwargs

    def bar(self, size: tuple[int, int], value: float, min_value: float, max_value: float, border_width=2,
            border_radius=7, fill_colour='White', border_colour='White', draw=True, **kwargs)\
            -> tuple[pg.surface.Surface, pg.rect.Rect]:
        """
        :param size: Bar size
        :param value: Bar value
        :param min_value: Bar minimum value
        :param max_value: Bar maximum value
        :param border_width: Border width
        :param border_radius: Border radius
        :param fill_colour: Bar inside colour
        :param border_colour: Bar outside colour
        :param draw: Automatically draw to display
        :param kwargs: Arguments for pg.rect
        :return: A surface, rect tuple for blit
        """
        fill_colour = Colour[fill_colour]
        border_colour = Colour[border_colour]
        value = float(value)

        surf = pg.surface.Surface((size[0], size[1]))
        surf.fill((1, 1, 1))
        surf.set_colorkey((1, 1, 1))

        if min_value < 0:
            min_value = -min_value  # Convert min value to positive number

            ratio = ((size[0] - border_width - 1) / (max_value + min_value)) * (value + min_value)
            if value > 0 - min_value:  # Handle negative values
                pg.draw.line(surf, fill_colour, (border_width, (size[1] / 2) - 1),
                             (ratio, (size[1] / 2) - 1), width=(size[1] - border_width * 2))

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
                pg.draw.line(surf, fill_colour, (border_width, (size[1] / 2) - 1),
                             (ratio, (size[1] / 2) - 1), width=size[1] - border_width * 2)

        pg.draw.rect(surf, border_colour, (0, 0, size[0], size[1]), width=border_width, border_radius=border_radius)

        rect = surf.get_rect(**kwargs)

        if draw:
            self.Display.blit(surf, rect)
        return surf, rect

    def button(self, state: bool or str or None, size=(70, 35), draw=True, **kwargs)\
            -> tuple[pg.surface.Surface, pg.rect.Rect]:
        """
        :param state: The state of the button (None = button, bool/colour = toggle)
        :param size: The size of the button
        :param draw: Automatically draw to display
        :param kwargs: Arguments for pg.rect
        :return: A surface, rect tuple for blit
        """
        surface = pg.surface.Surface((64, 32))
        surface.fill(Colour['key'])
        surface.set_colorkey(Colour['key'])

        shade = pg.surface.Surface((64, 32))  # SHADING
        shade.fill(Colour['key'])
        shade.set_colorkey(Colour['key'])
        shade.set_alpha(100)
        if type(state) is str:
            color = Colour[state]
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

        if state and type(state) is bool:  # PIN
            pg.draw.circle(surface, Colour['white'], (48, 16), 12, width=2)
            pg.draw.circle(surface, Colour['green'], (48, 16), 10)
        elif state is None or type(state) is tuple:
            surface.blit(*self.text('Press', 18, bold=True, center=surface.get_rect().center))
        else:
            pg.draw.circle(surface, Colour['white'], (16, 16), 12, width=2)
            pg.draw.circle(surface, Colour['red'], (16, 16), 10)

        pg.draw.circle(surface, Colour['white'], (16, 16), 16, width=2, draw_top_left=True,
                       draw_bottom_left=True)  # BORDER
        pg.draw.line(surface, Colour['white'], (16, 0), (48, 0), width=2)
        pg.draw.line(surface, Colour['white'], (16, 30), (48, 30), width=2)
        pg.draw.circle(surface, Colour['white'], (48, 16), 16, width=2, draw_top_right=True, draw_bottom_right=True)

        surface = pg.transform.scale(surface, size)
        rect = surface.get_rect(**kwargs)

        if draw:
            self.Display.blit(surface, rect)
        return surface, rect

    def show_info(self, txt: str, colour='Grey', timeout=3000, force=False) -> None:
        """
        :param txt: The message to display
        :param colour: The colour of the message
        :param timeout: How long the display shows (ms), set to 0 to disable
        :param force: Overwrite even if a message is being shown
        """
        if self._info[2] == 0:  # Enable force for info with no timeout by default
            force = True

        if not self._info[0] or force:  # If not showing another message
            self._info = txt, colour, pg.time.get_ticks() + timeout if timeout != 0 else timeout

    def clear_info(self) -> None:
        self._info = "", 'Grey', 0

    def get_info(self) -> tuple[str, str, int]:
        return self._info

    def input(self, rect: pg.rect.Rect) -> bool:
        if self.Input_method == InputMethod.Mouse:  # Mouse
            return rect.collidepoint(self.mouse_pos) and pg.mouse.get_pressed()[0]
        elif self.Input_method == InputMethod.Touch:  # Touchscreen
            return rect.collidepoint(self.mouse_pos) and self.mouse_pos != self.prev_mouse_pos
        else:
            return False

    @staticmethod
    def add_colours(colours: dict) -> None:
        Colour.update(colours)

    @staticmethod
    def load_image(path: str, size=(0, 0), keep_alpha=True, smooth_scale=True) -> pg.surface.Surface:
        img = pg.image.load(path)

        img = (pg.Surface.convert_alpha(img) if keep_alpha else pg.Surface.convert(img))
        if size != (0, 0):
            img = pg.transform.smoothscale(img, size) if smooth_scale else pg.transform.scale(img, size)

        return img

    @staticmethod
    def load_image_pair(path: str, size=(0, 0), keep_alpha=True, smooth_scale=True, **kwargs) -> tuple[
        pg.surface.Surface, pg.rect.Rect]:
        img = Ui.load_image(path, size, keep_alpha, smooth_scale)
        return img, img.get_rect(**kwargs)
