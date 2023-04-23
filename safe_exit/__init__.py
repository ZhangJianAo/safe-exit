import logging
import os
import signal
import subprocess
import sys
import time
import ctypes
from enum import IntEnum, Flag, auto

_logger = logging.getLogger("safe_exit")
_registered = False
_ctrl_handler = None
_exit_funcs = []


class ConfigFlag(Flag):
    """Config Flags"""
    SIGQUIT = auto()
    SIGHUP = auto()
    SIGBREAK = auto()
    CTRL_CLOSE = auto()
    CTRL_SHUTDOWN = auto()
    CTRL_LOGOFF = auto()
    AUTO_CREATE_CONSOLE = auto()
    FORCE_HIDE_CONSOLE = auto()


CONFIG_CTRL_ALL = ConfigFlag.CTRL_CLOSE | ConfigFlag.CTRL_SHUTDOWN | ConfigFlag.CTRL_LOGOFF
DEFAULT_CONFIG = ConfigFlag.SIGQUIT | ConfigFlag.SIGHUP | ConfigFlag.SIGBREAK | CONFIG_CTRL_ALL


class WinCtrlEvent(IntEnum):
    CTRL_C_EVENT = 0
    CTRL_BREAK_EVENT = 1
    CTRL_CLOSE_EVENT = 2
    CTRL_LOGOFF_EVENT = 5
    CTRL_SHUTDOWN_EVENT = 6


class SafeExitException(Exception):
    pass


def _call_exit_funcs():
    for (func, args, kwargs) in _exit_funcs:
        try:
            func(*args, **kwargs)
        except Exception as e:
            _logger.exception(f"exit function {func} error: {e}")


def _register_ctrl_handler():
    from ctypes import wintypes

    global _ctrl_handler

    _HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    CTRL_CLOSE_EVENT = 2
    CTRL_LOGOFF_EVENT = 5
    CTRL_SHUTDOWN_EVENT = 6

    def ctrl_handler(ctrl_type):
        if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_SHUTDOWN_EVENT, CTRL_LOGOFF_EVENT):
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
        _register_ctrl_handler()

    global _registered
    _registered = True


def _win_console_event_kill(pid, kill_signal: int):
    kernel32 = ctypes.windll.kernel32

    if kernel32.AttachConsole(pid):
        # Send the CTRL_C_EVENT signal
        success = kernel32.GenerateConsoleCtrlEvent(kill_signal, pid)
        # Detach from the target process console
        kernel32.FreeConsole()
        if not success:
            error_code = kernel32.GetLastError()
            raise SafeExitException(f"Failed to send CTRL EVENT {kill_signal} to process {pid} Error:{error_code}")
    else:
        raise SafeExitException(f"Can't attach console for process {pid}")


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


def config(flag: ConfigFlag):
    """Config to register signals

    There is no need to call this function on Linux or other POSIX systems,
     this module will automatically register signal handlers.
    On Windows, ```config(ConfigFlag.AUTO_CREATE_CONSOLE)``` will check if program attach to a console,
     if not, it will alloc a console and set it to invisable.
    If you want to hide the console window even the window is not alloc by program, add ConfigFlag.FORCE_HIDE_CONSOLE,
     like ```config(ConfigFlag.AUTO_CREATE_CONSOLE | ConfigFlag.FORCE_HIDE_CONSOLE)```

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
    """Register function will call when program will exit

    This function can be used as function annot
    """
    if not _registered:
        config(DEFAULT_CONFIG)
    _exit_funcs.append((func, args, kwargs))


def unregister(func):
    """Unregister function"""
    idx = 0
    while idx < len(_exit_funcs):
        if _exit_funcs[idx][0] == func:
            _exit_funcs.pop(idx)
        else:
            idx += 1


def safe_kill(pid, kill_signal=None, timeout_secs=4, force_kill=True, silence=True):
    """Graceful kill a process

    This function first try to send SIGTERM signal to the process,
     and wait for timeout_secs, if the process still alive, then force kill it.
    On windows, this function will try to find window for process, if found, it will send WM_CLOSE event,
     if no window found, it will try to find console for process,
     if found console, it will try to attach the console and send CTRL_C_EVENT to process.
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

#############################################################
# Following code is only for test                           #
#############################################################

def _gracefully():
    _logger.info("Atexitex, Performing graceful shutdown...")
    time.sleep(2)
    _logger.info("Atexitex, Shutdown complete")


def _process_main():
    _logger.info(f"Running... PID:{os.getpid()} Press Ctrl+C to exit.")
    while True:
        # Your main program loop
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s %(levelname)s:%(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("signal_test.log"),
            logging.StreamHandler()
        ]
    )

    register(_gracefully)

    ops = sys.argv[1]
    if ops == "start":
        _process_main()
    elif ops == "kill":
        safe_kill(int(sys.argv[2]))
    elif ops == 'popen':
        p = subprocess.Popen(sys.argv[2])
        p.wait()
