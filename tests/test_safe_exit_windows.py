import ctypes
import logging
import os
import re
import subprocess
import sys
import time

import pytest

import safe_exit


if os.name != "nt":
    pytest.skip(f"skipping posix tests on {sys.platform}", allow_module_level=True)


def check_log_ready(pid):
    log_file_name = f"{pid}.log"
    while True:
        time.sleep(1)
        if not os.path.exists(log_file_name):
            continue
        with open(log_file_name, 'r') as f:
            if f"{pid} ready" in f.read():
                return True


@pytest.mark.parametrize("signal_to_send",
                         [safe_exit.WinCtrlEvent.CTRL_C_EVENT.value, safe_exit.WinCtrlEvent.CTRL_BREAK_EVENT.value])
def test_console_signal(signal_to_send):
    # create process
    process = subprocess.Popen([sys.executable, __file__], creationflags=subprocess.CREATE_NEW_CONSOLE)
    check_log_ready(process.pid)

    # safe_kill process with signal
    run_result = subprocess.run(
        [sys.executable, __file__, 'kill', str(process.pid), str(signal_to_send)],
        creationflags=subprocess.DETACHED_PROCESS)
    if run_result.returncode != 0:
        logging.error(f"kill process error: {run_result.stdout} \n\n {run_result.stderr}")

    process.wait(timeout=20)

    log_file_name = f"{process.pid}.log"
    with open(log_file_name, "r") as f:
        logs = f.read()
        assert len(re.findall(f"process {process.pid} safe_exit", logs)) == 1

    os.unlink(log_file_name)


def test_wm_close():
    # create process
    process = subprocess.Popen([sys.executable, __file__, 'auto_create'], creationflags=subprocess.DETACHED_PROCESS)
    check_log_ready(process.pid)

    # safe_kill process with signal
    run_result = subprocess.run(
        [sys.executable, __file__, 'kill', str(process.pid), str(safe_exit.WinCtrlEvent.CTRL_CLOSE_EVENT.value)],
        creationflags=subprocess.DETACHED_PROCESS)
    if run_result.returncode != 0:
        logging.error(f"kill process error: {run_result.stdout} \n\n {run_result.stderr}")

    process.wait(timeout=20)

    log_file_name = f"{process.pid}.log"
    with open(log_file_name, "r") as f:
        logs = f.read()
        assert len(re.findall(f"process {process.pid} safe_exit", logs)) == 1

    os.unlink(log_file_name)


def test_no_handle_signal():
    # create process
    process = subprocess.Popen([sys.executable, __file__, 'no_signal'], creationflags=subprocess.DETACHED_PROCESS)
    check_log_ready(process.pid)

    # safe_kill process with signal
    run_result = subprocess.run(
        [sys.executable, __file__, 'kill', str(process.pid), str(safe_exit.WinCtrlEvent.CTRL_CLOSE_EVENT.value)],
        creationflags=subprocess.DETACHED_PROCESS)
    if run_result.returncode != 0:
        logging.error("kill process error")

    process.wait(timeout=20)

    log_file_name = f"{process.pid}.log"
    with open(log_file_name, "r") as f:
        logs = f.read()
        assert f"process {process.pid} safe_exit" not in logs

    os.unlink(log_file_name)


if __name__ == "__main__":
    logging.basicConfig(filename=f"{os.getpid()}.log", level=logging.DEBUG)

    if len(sys.argv) == 4 and sys.argv[1] == 'kill':
        try:
            kernel32 = ctypes.windll.kernel32
            hwnd = kernel32.GetConsoleWindow()
            print(f"killer's console window is {hwnd}")
            safe_exit.safe_kill(int(sys.argv[2]), int(sys.argv[3]), silence=False)
        except Exception as e:
            logging.exception(f"kill process {sys.argv[2]} error: {e}")
            exit(1)
        exit(0)


    def clean_func():
        logging.info(f"process {os.getpid()} safe_exit")

    if len(sys.argv) == 2:
        if sys.argv[1] == 'auto_create':
            safe_exit.config(safe_exit.DEFAULT_CONFIG | safe_exit.ConfigFlag.AUTO_CREATE_CONSOLE)
        elif sys.argv[1] == 'no_signal':
            safe_exit.config(safe_exit.ConfigFlag.AUTO_CREATE_CONSOLE)

    safe_exit.register(clean_func)

    try:
        logging.info(f"process {os.getpid()} ready")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
