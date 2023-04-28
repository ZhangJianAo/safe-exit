import logging
import os
import signal
import sys
import ctypes
import atexit
from typing import List
from enum import IntEnum, Flag, auto

_logger = logging.getLogger("safe_exit")
_registered = False
_ctrl_handler = None
_exit_funcs = []


class ConfigFlag(Flag):
    """Configuration Flags:"""
    SIGQUIT = auto()
    """Handle SIGQUIT signal."""
    SIGHUP = auto()
    """Handle SIGHUP signal."""
    SIGBREAK = auto()
    """Handle SIGBREAK signal."""
    CTRL_CLOSE = auto()
    """Handle CTRL_CLOSE_EVENT."""
    CTRL_SHUTDOWN = auto()
    """Handle CTRL_SHUTDOWN_EVENT."""
    CTRL_LOGOFF = auto()
    """Handle CTRL_LOGOFF_EVENT."""
    AUTO_CREATE_CONSOLE = auto()
    """Alloc a console and set it hidden."""
    FORCE_HIDE_CONSOLE = auto()
    """If program is in a console, set the console hidden."""


CONFIG_CTRL_ALL = ConfigFlag.CTRL_CLOSE | ConfigFlag.CTRL_SHUTDOWN | ConfigFlag.CTRL_LOGOFF
"""All Windows ctrl events."""

DEFAULT_CONFIG = ConfigFlag.SIGQUIT | ConfigFlag.SIGHUP | ConfigFlag.SIGBREAK | CONFIG_CTRL_ALL
"""Default config: will handle all signals."""


class WinCtrlEvent(IntEnum):
    CTRL_C_EVENT = 0
    CTRL_BREAK_EVENT = 1
    CTRL_CLOSE_EVENT = 2
    CTRL_LOGOFF_EVENT = 5
    CTRL_SHUTDOWN_EVENT = 6


class SafeExitException(Exception):
    pass


@atexit.register
def _call_exit_funcs():
    global _exit_funcs

    for (func, args, kwargs) in _exit_funcs:
        try:
            func(*args, **kwargs)
        except Exception as e:
            _logger.exception(f"exit function {func} error: {e}")

    _exit_funcs = []


def _register_ctrl_handler(events: List[int]):
    from ctypes import wintypes

    global _ctrl_handler

    _HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    def ctrl_handler(ctrl_type):
        if ctrl_type in events:
            _logger.info(f"Ctrl handler received {ctrl_type}. Performing graceful shutdown...")
            _call_exit_funcs()
            return True

        return False

    _ctrl_handler = _HandlerRoutine(ctrl_handler)
    kernel32 = ctypes.windll.kernel32
    if not kernel32.SetConsoleCtrlHandler(_ctrl_handler, True):
        raise ctypes.WinError(ctypes.get_last_error())


def _signal_handler(sig, frame):
    _logger.info(f"Receive {sig}, Performing graceful shutdown...")
    _call_exit_funcs()
    sys.exit(0)


def _register_signals(flag: ConfigFlag):
    # Register the signal handler
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    if os.name == 'posix':
        if ConfigFlag.SIGQUIT in flag: signal.signal(signal.SIGQUIT, _signal_handler)
        if ConfigFlag.SIGHUP in flag: signal.signal(signal.SIGHUP, _signal_handler)
    if os.name == 'nt':
        if ConfigFlag.SIGBREAK in flag: signal.signal(signal.SIGBREAK, _signal_handler)
        events = []
        if ConfigFlag.CTRL_CLOSE in flag:
            events.append(WinCtrlEvent.CTRL_CLOSE_EVENT.value)
        if ConfigFlag.CTRL_LOGOFF in flag:
            events.append(WinCtrlEvent.CTRL_LOGOFF_EVENT.value)
        if ConfigFlag.CTRL_SHUTDOWN in flag:
            events.append(WinCtrlEvent.CTRL_SHUTDOWN_EVENT.value)
        if len(events) > 0:
            _register_ctrl_handler(events)

    global _registered
    _registered = True


def _win_console_event_kill(pid, kill_signal: int):
    kernel32 = ctypes.windll.kernel32

    if kernel32.AttachConsole(pid):
        # Send the CTRL_C_EVENT signal
        success = kernel32.GenerateConsoleCtrlEvent(kill_signal, 0)
        # Detach from the target process console
        kernel32.FreeConsole()
        if not success:
            error = ctypes.WinError(kernel32.GetLastError())
            raise SafeExitException(f"Failed to send CTRL EVENT {kill_signal} to process {pid}: {error}")
    else:
        error = ctypes.WinError(kernel32.GetLastError())
        raise SafeExitException(f"Can't attach console for process {pid}: {error}")


def _win_send_wm_close(pid):
    from ctypes import wintypes

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def find_main_window(pid):
        def enum_windows_callback(hwnd, lParam):
            window_pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.pointer(window_pid))
            if window_pid.value == lParam:
                found_windows.append(hwnd)
                return False  # Stop enumerating windows
            return True  # Continue enumerating windows

        found_windows = []
        ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_callback), pid)

        return found_windows[0] if found_windows else None

    def send_wm_close(hwnd):
        WM_CLOSE = 0x0010
        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    kernel32 = ctypes.windll.kernel32

    hwnd = find_main_window(pid)
    if hwnd:
        send_wm_close(hwnd)
    else:
        raise SafeExitException(f"Can't found windows for process {pid}")


def _win_nice_kill(pid, kill_signal: int = None):
    error_msg = []

    if kill_signal is None or kill_signal > WinCtrlEvent.CTRL_BREAK_EVENT:
        try:
            _win_send_wm_close(pid)
            return
        except Exception as e:
            error_msg.append(str(e))

    if kill_signal is None or kill_signal in (WinCtrlEvent.CTRL_C_EVENT, WinCtrlEvent.CTRL_BREAK_EVENT):
        try:
            _win_console_event_kill(pid, WinCtrlEvent.CTRL_C_EVENT if kill_signal is None else kill_signal)
            return
        except Exception as e:
            error_msg.append(str(e))

    raise SafeExitException(' and '.join(error_msg))


def config(flag: ConfigFlag = DEFAULT_CONFIG):
    """Configures which signals to register.

    This function must be called before the register() function.

    If the config() function is not called,
    the register() function will automatically call this function with DEFAULT_CONFIG,
    which will handle all signals.

    Using this function allows you to control which signals to handle. SIGINT and SIGTERM are always handled,
    and other signals can be set by this function.

    On Windows,
    ``config(DEFAULT_CONFIG | ConfigFlag.AUTO_CREATE_CONSOLE)`` checks if the program is attached to a console.
    If not, it allocates a console and sets it to invisible.

    If you want to hide the console window even if it is not allocated by the program,
    add ConfigFlag.FORCE_HIDE_CONSOLE,
    like ``config(DEFAULT_CONFIG | ConfigFlag.AUTO_CREATE_CONSOLE | ConfigFlag.FORCE_HIDE_CONSOLE)``.

    :param flag: Configuration flags
    :type flag: ConfigFlag
    """
    if os.name == 'nt':
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = kernel32.GetConsoleWindow()
        if hwnd and ConfigFlag.FORCE_HIDE_CONSOLE in flag:
            user32.ShowWindow(hwnd, 0)
        if not hwnd and ConfigFlag.AUTO_CREATE_CONSOLE in flag:
            kernel32.AllocConsole()
            sys.stdin = open("CONIN$", "r")
            sys.stdout = open("CONOUT$", "w")
            sys.stderr = open("CONOUT$", "w")
            hwnd = kernel32.GetConsoleWindow()
            user32.ShowWindow(hwnd, 0)

    _register_signals(flag)


def register(func, *args, **kwargs):
    """Register func as a function to be executed at termination.

    Any optional arguments that are to be passed to func must be passed as arguments to register().

    This function can be used as function decorator.
    """
    if not _registered:
        config(DEFAULT_CONFIG)
    _exit_funcs.append((func, args, kwargs))
    return func


def unregister(func):
    """Remove func from the list of functions to be run at interpreter shutdown."""
    idx = 0
    while idx < len(_exit_funcs):
        if _exit_funcs[idx][0] == func:
            _exit_funcs.pop(idx)
        else:
            idx += 1


def safe_kill(pid, kill_signal=None, timeout_secs=4, force_kill=True, silence=True):
    """Gracefully kills a process.

    :param pid: Process id to be killed.
    :type pid: int

    :param kill_signal: Which signal to send; can be None to use default signal
    :type kill_signal: int

    :param timeout_secs: How many seconds to wait for the process to terminate.
    :type timeout_secs: int

    :param force_kill: If True, force kill the process after timeout.
    :type force_kill: bool

    :param silence: If True, raise no exception if sending the signal results in an error.
    :type silence: bool

    This function first try to send kill_signal to the process,
    and wait for timeout_secs, if the process still alive, it then forces kill it.

    On windows, this function tries to find a window for the process, if found, it sends the WM_CLOSE event.
    If no window is found, it tries to find console for the process.
    If a console is found, it tries to attach the console and sends the CTRL_C_EVENT to the process.
    """
    import psutil

    proc = psutil.Process(pid)

    try:
        if os.name == 'posix':
            os.kill(pid, kill_signal if kill_signal is not None else signal.SIGTERM)
        if os.name == 'nt':
            _win_nice_kill(pid, kill_signal)

        proc.wait(timeout_secs)
    except Exception as e:
        if not silence:
            raise e
    finally:
        if force_kill and proc.is_running():
            proc.kill()
