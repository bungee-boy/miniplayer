from datetime import datetime
from enum import IntEnum
import os
import traceback


class LogLevel(IntEnum):
    ERR = 2  # Error - The program is attempting to fix an issue
    WRN = 3  # Warning - Encountered an issue but fine to continue
    INF = 4  # Info - Status updates

class Log:
    _Init = False
    _Folder = ".\\log\\"
    _Path = _Folder + datetime.now().strftime(f"%y-%m-%d.log")
    _File = None

    _Save_to_file = False  # Save the latest logs to disk?
    _Live_logging = False  # Save to file while running (slow, only for debug)
    _Level = LogLevel['INF']  # Filter by severity

    def __init__(self, name: str) -> None:
        """
        Constructor
        :param name: Instance name
        """
        self.name = name

        if not self._Init and self._Save_to_file:  # Run first time init
            self.open()
            self._Init = True

    def log(self, msg: str, level: LogLevel, data=None) -> None:
        """
        Logs a message
        :param msg: The message to save
        :param level: The message severity
        :param data: String of data to include
        """
        try:
            if self._Level.value >= level:  # Filter priority
                msg = (f"[{datetime.now().strftime('%X')}][{level.name}] {self.name} -> "
                       f"{msg}{f' ({data})' if data else ''}")  # Format message
                print(msg)  # Output message to console
                if self._Save_to_file:
                    if self._Live_logging:  # Save log to file on each message (slow!)
                        with open(self._Path, "a") as file:
                            file.write(msg + '\n')
                    else:  # File is already open (efficient mode)
                        if not self._File.closed:
                            self._File.write(msg + '\n')
                        else:
                            self._Save_to_file = False
                            self.log("Attempted log to closed file", LogLevel.ERR, "path: " + self._Path)

        except Exception as e:  # If logging failed
            self.handle(e)

    def handle(self, err: Exception or BaseException, data=None, level=LogLevel.ERR, trace=True) -> None:
        """
        Handles and records exceptions as errors.
        KeyboardInterrupts are excluded from being recorded as they are used to cleanly exit.
        :param err: The exception to log
        :param data: Variables/Info relating to the error
        :param level: The severity of the error
        :param trace: Includes the traceback to the error
        """
        if type(err) is KeyboardInterrupt:  # Exclude KeyboardInterrupt errors
            return

        msg = "{0}: {1}".format(str(type(err)).replace("<class '", '').replace("'>", ''), err)  # Format error

        if trace:  # Toggle traceback
            self.log(msg + traceback.format_exc(), level, data)

    @staticmethod
    def set_level(level: LogLevel) -> None:
        """
        Sets a new log level
        :param level: New logging level
        """
        Log("Log").log("Set new log level", LogLevel.INF, "level: " + level.name)
        Log._Log_level = level

    @staticmethod
    def open():
        if not os.path.isdir(Log._Folder):  # If directory does not exist
            os.makedirs(Log._Folder)  # Create new
            Log("Log").log("Created new folder", LogLevel.INF, "folder: " + Log._Folder)

        try:
            Log._File = open(Log._Path, 'a')
            Log("Log").log("Opened log", LogLevel.INF, "path: " + Log._Path)
        except FileNotFoundError as e:
            Log("Log").handle(e, "Path: " + Log._Path)
            Log._File = open(Log._Path, 'x')
            Log("Log").log("Opened log", LogLevel.INF, "path: " + Log._Path)
        except Exception as e:
            Log("Log").handle(e, "path: " + Log._Path)

        if Log._File is not None:
            Log._Save_to_file = True
            Log._File.write(f"\n[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
                             f"*** New instance ***\n")

    @staticmethod
    def close():
        if Log._Save_to_file:
            if Log._Live_logging:
                with open(Log._Path, "a") as log_file:
                    log_file.write(f"[{datetime.now().strftime('%x %X')}][INF][Log] -> "
                                   f"*** End instance ***\n")
            else:
                if not Log._File.closed:
                    Log._File.write(f"[{datetime.now().strftime('%x %X')}][INF][Log] -> "
                                    f"*** End instance ***\n")
                    Log._File.close()

            Log._Save_to_file = False
            print(f"[{datetime.now().strftime('%x %X')}][INF][Log] -> "
                  f"Closed the current log file at {Log._Path}\n")
