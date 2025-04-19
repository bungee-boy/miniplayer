# How to make a plugin

## Index
1. [What is a plugin?](#What is a plugin?)
2. [Getting started](#Getting started)

## What is a plugin?

A plugin is different to a window in that it doesn't require any visual effects.
They can be additions to the backend such as brightness or screen controls

## Getting started

The basic structure of a plugin is inherited from `PluginBase` via `from plugin import *` <br>
and your class should then inherit from `PluginBase`.<br>
The base class will load the logger by default (for debugging) but includes no functionality.

### Minimum required to create a window
```
from plugin import *  # Plugin base class

class MyPlugin(PluginBase):
    def __init__(self):
        super().__init__("My Plugin's Name")
```

By doing this, PluginBase provides you with a Mqtt class under `_Mqtt` just like a window.<br>
Note that there is no `_Ui` class provided though.

### The basics
Before you start talking over Mqtt and showing some pretty animations, let's go over what happens and when.

1. Miniplayer startup -> Your plugin will be loaded and the `__init__()` will be run. This creates variables etc.
2. Enabling a plugin -> Depending on settings, your plugin will be enabled via `_enable()`. This could subscribe to topics and setup functionality
3. Main loop -> `update()` will be run (if enabled). This will likely be where the main functionality of the plugin goes
4. Main loop -> `draw()` will be run (if enabled). This is optional and can be used to add screen effects etc. (drawn after windows)
5. Disabling a plugin -> If enabled, `_disable()` will be called. This should neatly close connections and stop functionality etc.
