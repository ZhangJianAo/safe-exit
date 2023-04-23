import os
import signal
import subprocess
import sys
import time

import pytest

import safe_exit


if os.name != "nt":
    pytest.skip(f"skipping posix tests on {sys.platform}", allow_module_level=True)


@pytest.mark.parametrize("signal_to_send", [e.value for e in safe_exit.WinCtrlEvent])
def test_signal(signal_to_send):
    # create process
    process = subprocess.Popen(
        [sys.executable, __file__],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    time.sleep(1)

    # safe_kill process with signal
    subprocess.run(
        [sys.executable, __file__, 'kill', str(process.pid), str(signal_to_send)],
        creationflags=subprocess.DETACHED_PROCESS)

    # check process output match "safe_exit on signal %d"
    output, _ = process.communicate()
    assert f"process {process.pid} safe_exit" in output.decode('utf-8')


# @pytest.mark.parametrize("signal_to_send", [signal.SIGQUIT, signal.SIGHUP])
# def test_no_handle_signal(signal_to_send):
#     # create process
#     process = subprocess.Popen([sys.executable, __file__, 'no_extra_signal'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     time.sleep(1)
#
#     # safe_kill process with signal
#     safe_exit.safe_kill(process.pid, signal_to_send)
#
#     # check process output match "safe_exit on signal %d"
#     output, _ = process.communicate()
#     assert len(output) == 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == 'no_extra_signal':
        safe_exit.config(safe_exit.ConfigFlag(0))
    elif len(sys.argv) == 4 and sys.argv[1] == 'kill':
        safe_exit.safe_kill(int(sys.argv[2]), int(sys.argv[3]))

    def clean_func():
        print(f"process {os.getpid()} safe_exit")

    safe_exit.register(clean_func)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
