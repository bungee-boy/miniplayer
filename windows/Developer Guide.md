# How to make a window

## Index
1. [Getting started](#Getting started)

## Getting started

Everything you need for a basic window is included by adding `from window import *` <br>
and your class should then inherit from `WindowBase`.<br>
The base class will display the window name and background by default (for debugging).

### Minimum required to create a window
```
from window import *  # Window base class

class MyWindow(WindowBase):
    def __init__(self):
        super().__init__('My Window's Name')
```

By doing this, WindowBase provides you with a Mqtt class under `_Mqtt`, and a user interface class under `_Ui`

### The basics
Before you start talking over Mqtt and showing some pretty animations, let's go over what happens and when.

1. Miniplayer startup -> Your window will be created and the `__init__()` will be run. This creates variables etc.
2. Loading a window -> The window to be loaded will call `_start()`. This could subscribe to topics
3. Main loop -> `update()` will be run. This could handle inputs, actions and animations
4. Main loop -> `draw()` will be run. This should draw the entire window to the screen, and ideally be constant
5. Closing a window -> The window to be closed will call `_stop()`. This could unsubscribe from active topics
