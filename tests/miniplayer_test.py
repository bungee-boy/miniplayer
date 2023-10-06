import unittest
import pygame as pg
import miniplayer as mp


class TestVariables(unittest.TestCase):
    def test_default(self):
        self.assertEqual(mp.CENTER, (mp.WIDTH // 2, mp.HEIGHT // 2))  # Center
        self.assertEqual(mp.Button_cooldown, 0)  # Button cooldown
        self.assertEqual(mp.Button_cooldown_length, 100 if mp.SYSTEM == 'Windows' else 500)  # Button length
        self.assertEqual(mp.Mouse_pos, (-1, -1))  # Mouse pos
        self.assertEqual(mp.Prev_mouse_pos, (-2, -2))  # Prev mouse pos
        self.assertEqual(type(mp.Loaded_fonts), dict)  # Loaded fonts
        self.assertDictEqual(mp.Colour, {'key': (1, 1, 1), 'black': (0, 0, 0), 'white': (255, 255, 255),
                                         'grey': (155, 155, 155), 'd grey': (80, 80, 80), 'red': (251, 105, 98),
                                         'yellow': (252, 252, 153), 'l green': (121, 222, 121), 'green': (18, 115, 53),
                                         'amber': (200, 140, 0), 'l blue': (3, 140, 252)})  # Colour
        if mp.Last_err:
            self.assertEqual(type(mp.Last_err), str)  # Last err
        else:
            self.assertIsNone(mp.Last_err)  # Last err
        self.assertEqual(type(mp.Display), pg.display)  # Display


if __name__ == '__main__':
    unittest.main()
