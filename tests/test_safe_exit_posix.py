import os
import re
import signal
import subprocess
import sys
import time

import pytest

import safe_exit


if os.name != "posix":
    pytest.skip(f"skipping posix tests on {sys.platform}", allow_module_level=True)


@pytest.mark.parametrize("signal_to_send", [signal.SIGINT, signal.SIGTERM, signal.SIGQUIT, signal.SIGHUP])
def test_signal(signal_to_send):
    # create process
    process = subprocess.Popen([sys.executable, __file__], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)

    # safe_kill process with signal
    safe_exit.safe_kill(process.pid, signal_to_send)

    # check process output match "safe_exit on signal %d"
    output, _ = process.communicate()
    expect = f"process {process.pid} safe_exit"
    actual = output.decode('utf-8')
    assert len(re.findall(expect, actual)) == 1


def test_sys_exit():
    # create process
    process = subprocess.Popen([sys.executable, __file__, 'sys_exit'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)

    # check process output match "safe_exit on signal %d"
    output, _ = process.communicate()
    assert len(re.findall(f"process {process.pid} safe_exit", output.decode('utf-8'))) == 1


@pytest.mark.parametrize("signal_to_send", [signal.SIGQUIT, signal.SIGHUP])
def test_no_handle_signal(signal_to_send):
    # create process
    process = subprocess.Popen([sys.executable, __file__, 'no_extra_signal'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)

    # safe_kill process with signal
    safe_exit.safe_kill(process.pid, signal_to_send)

    # check process output match "safe_exit on signal %d"
    output, _ = process.communicate()
    assert len(output) == 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == 'no_extra_signal':
        safe_exit.config(safe_exit.ConfigFlag(0))

    def clean_func():
        print(f"process {os.getpid()} safe_exit")

    safe_exit.register(clean_func)

    if len(sys.argv) == 2 and sys.argv[1] == 'sys_exit':
        sys.exit(0)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
