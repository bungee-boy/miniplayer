import unittest
# import pygame as pg
import main


class TestVariables(unittest.TestCase):
    def test_default(self):
        self.assertEqual(main.CENTER, (main.WIDTH // 2, main.HEIGHT // 2))  # Center
        self.assertEqual(main.Button_cooldown, 0)  # Btn cooldown
        self.assertEqual(main.Button_cooldown_length, 100 if main.Conf.Touchscreen == 'Windows' else 500)  # Btn length
        self.assertEqual(main.Mouse_pos, (-1, -1))  # Mouse pos
        self.assertEqual(main.Prev_mouse_pos, (-2, -2))  # Prev mouse pos
        self.assertEqual(type(main.Loaded_fonts), dict)  # Loaded fonts
        # noinspection DuplicatedCode
        self.assertDictEqual(main.Colour, {'key': (1, 1, 1), 'black': (0, 0, 0), 'white': (255, 255, 255),
                                           'grey': (155, 155, 155), 'd grey': (80, 80, 80), 'red': (251, 105, 98),
                                           'yellow': (252, 252, 153), 'l green': (121, 222, 121),
                                           'green': (18, 115, 53), 'amber': (200, 140, 0), 'l blue': (3, 140, 252)})
        # if main.Last_err:
        #     self.assertEqual(type(main.Last_err), str)  # Last err
        # else:
        #     self.assertIsNone(main.Last_err)  # Last err
        # self.assertEqual(type(main.Display), pg.display)  # Display


if __name__ == '__main__':
    unittest.main()
