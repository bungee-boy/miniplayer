from datetime import datetime
from platform import system
import os
import traceback


# def open_log(folder: str, filepath: str):

_Log_folder = "log" + ("\\" if system() == "Windows" else "/")
_Log_path = datetime.now().strftime(f"{_Log_folder}miniplayer-%y-%m-%d.log")
_Log_file = None

if not os.path.isdir(_Log_folder):  # If directory does not exist
    os.makedirs(_Log_folder)  # Create new
    print(f"[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
          f"Created new folder at \"{_Log_folder}\"")
try:
    _Log_file = open(_Log_path, 'a')
    print(f"[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
          f"Opened log at \"{_Log_path}\"")
except PermissionError:
    print(f"[{datetime.now().strftime('%x %X')}][CRITICAL][Logger] -> "
          f"Failed to open log at \"{_Log_folder}\" (reason: PermissionError)")
except FileNotFoundError:
    print(f"[{datetime.now().strftime('%x %X')}][WARNING][Logger] -> "
          f"Failed to open log at \"{_Log_folder}\" (reason: FileNotFoundError)")
    try:
        _Log_file = open(_Log_path, 'x')
        print(f"[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
              f"Created new log \"{_Log_path}\"")
    except:
        print(f"[{datetime.now().strftime('%x %X')}][CRITICAL][Logger] -> "
              f"Failed to open log at \"{_Log_folder}\" (reason: Unknown)")
except:
    print(f"[{datetime.now().strftime('%x %X')}][CRITICAL][Logger] -> "
          f"Failed to open log at \"{_Log_folder}\" (reason: Unknown)")

if _Log_file is not None:
    _Log_file.write(f"\n[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
                    f"*** New instance ***\n")


class Logging:
    CRITICAL = 1
    ERROR = 2
    WARNING = 3
    INFO = 4
    DEBUG = 5

    _Last_err = None
    Log_level = INFO

    def __init__(self, name: str) -> None:
        """
        Constructor.
        :param name: Instance name (to be included when logging)
        """
        self.name = name

    @staticmethod
    def close_log():
        if not _Log_file.closed:
            _Log_file.write(f"[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
                            f"*** End instance ***\n")
            _Log_file.close()
            print(f"[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
                  f"Closed the current log file")

    @staticmethod
    def convert_level(level: int) -> str:
        """
        Converts the given level to its corresponding string
        :param level: Level to convert
        """
        if level == Logging.CRITICAL:
            return 'CRITICAL'
        elif level == Logging.ERROR:
            return 'ERROR'
        elif level == Logging.WARNING:
            return 'WARN'
        elif level == Logging.INFO:
            return 'INFO'
        elif level == Logging.DEBUG:
            return 'DEBUG'

    @staticmethod
    def set_log_level(level: int):
        Logging.Log_level = level
        print(f"[{datetime.now().strftime('%x %X')}][INFO][Logger] -> "
              f"Set log level to {Logging.convert_level(Logging.Log_level)}.")

    def _log(self, msg: str, level: int, data=None, newline=True, save=True) -> None:
        """
        Save the message and data to the log file.
        :param msg: The message to save
        :param level: Message priority level
        :param data: String of data to include
        :param newline: Whether to include a newline after each message
        :param save: Whether to write to log file (used for handle)
        """
        try:
            if self.Log_level >= level:  # Filter priority
                msg = (f"[{datetime.now().strftime('%x %X')}][{self.convert_level(level)}][{self.name}] -> "
                       f"{msg}{f' ({data})' if data else ''}")  # Format message
                print(msg)  # Output message to console
                if save and not _Log_file.closed:
                    _Log_file.write(msg + '\n' if newline else msg)
                if save and _Log_file.closed:
                    print(f"[{datetime.now().strftime('%x %X')}][CRITICAL][Logger] -> "
                          f"Attempted log on closed logfile at \"{_Log_path}\"")
            else:
                return
        except (Exception, BaseException) as err:  # If logging failed
            self.handle(err, save=False)  # Do not save as error with log

    def debug(self, msg: str, data=None) -> None:
        """
        Logs a message with the priority DEBUG.
        Only used for very specific debugging info.
        :param msg: The message to save
        :param data: String of data to include
        """
        self._log(msg, Logging.DEBUG, data=data)

    def info(self, msg: str, data=None) -> None:
        """
        Logs a message with the priority INFO.
        Used for general info that isn't important.
        :param msg: The message to save
        :param data: String of data to include
        """
        self._log(msg, Logging.INFO, data=data)

    def warn(self, msg: str, data=None) -> None:
        """
        Logs a message with the priority WARNING.
        Used for specific info that isn't important.
        :param msg: The message to save
        :param data: String of data to include
        """
        self._log(msg, Logging.WARNING, data=data)

    def err(self, msg: str, data=None) -> None:
        """
        Logs a message with the priority ERROR.
        Used for non-critical errors.
        :param msg: The message to save
        :param data: String of data to include
        """
        self._log(msg, Logging.ERROR, data=data)

    def crit(self, msg: str, data=None) -> None:
        """
        Logs a message with the priority CRITICAL.
        Used for critical errors.
        :param msg: The message to save
        :param data: String of data to include
        """
        self._log(msg, Logging.CRITICAL, data=data)

    def handle(self, err: Exception or BaseException, data=None,
               save=True, repeat=False, trace=True, crit=False) -> None:
        """
        Handles and records exceptions as errors.
        KeyboardInterrupts are excluded from being recorded as they are used to cleanly exit.
        :param err: The exception to log
        :param data: String of data to be included in the log
        :param save: Toggle logging
        :param repeat: Toggle repeating the same error
        :param trace: Toggle including the traceback
        :param crit: Whether to log the exception as critical or error
        """
        if type(err) is KeyboardInterrupt:  # Exclude KeyboardInterrupt errors (clean exit)
            return
        msg = "{0}: {1}".format(str(type(err)).replace("<class '", '').replace("'>", ''), err)  # Format error
        if msg == self._Last_err and not repeat:  # Filter repeated errors
            return
        else:
            self._Last_err = msg  # Save message to know if it is repeated

        if trace:  # Toggle traceback
            self._log(traceback.format_exc(), self.CRITICAL if crit else self.ERROR, newline=False, save=save)
        if save:  # Toggle saving
            if crit:
                self.crit(msg, data=data)
            else:
                self.err(msg, data=data)
