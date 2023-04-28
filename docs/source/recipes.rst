Recipes
=======


SIGTERM
-------

SIGTERM (signal 15) is a request to the program to terminate. This is the default signal sent by ``kill`` command.

It is typically better to issue SIGTERM rather than SIGKILL. If the program has a handler for SIGTERM,
it can clean up and terminate in an orderly fashion. Type:

.. code-block:: shell

    kill -term ProcessID

Unfortunately, ``atexit`` doesn't handle this signal, Safe-Exit handles this signal by default.


SIGQUIT
-------

SIGQUIT (signal 3) is the dump core signal.
The terminal sends it to the foreground process when the user presses ctrl-\.

The default behavior is to terminate the process and dump core, but it can be caught or ignored.
The intention is to provide a mechanism for the user to abort the process.
You can look at SIGINT as "user-initiated happy termination" and SIGQUIT as "user-initiated unhappy termination."

``atexit`` doesn't handle this signal, Safe-Exit handles this signal by default but can be configured to ignore it.


.. _SIGHUP:

SIGHUP
------

SIGHUP (signal 1) is a signal sent to a process when its controlling terminal is closed.
It was originally designed to notify the process of a serial line drop.

With the decline of access via serial line, the meaning of SIGHUP has changed somewhat on modern systems,
often meaning a controlling pseudo or virtual terminal has been closed.
If a command is executed inside a terminal window and the terminal window is closed while the command process is still running, it receives SIGHUP.

``atexit`` doesn't handle this signal, Safe-Exit handles this signal by default but can be configured to ignore it.


SIGBREAK
--------

SIGBREAK (value 21) is not a POSIX signal, it is used by Windows(`document <https://learn.microsoft.com/en-us/windows/console/ctrl-c-and-ctrl-break-signals>`_).

Its intention is to Interrupt from keyboard (CTRL + BREAK), which is the same as SIGINT.

``atexit`` doesn't handle this signal, Safe-Exit handles this signal by default but can be configured to ignore it.


CTRL_CLOSE_EVENT
----------------

CTRL_CLOSE_EVENT (value 2) is a signal that the system sends to all processes attached to a console when the user closes the console (either by clicking Close on the console window's window menu, or by clicking the End Task button command from Task Manager).

It's similar to :ref:`SIGHUP`, but only on Windows.

``atexit`` doesn't handle this signal, Safe-Exit handles this signal by default but can be configured to ignore it.


CTRL_LOGOFF_EVENT and CTRL_SHUTDOWN_EVENT
-----------------------------------------

CTRL_LOGOFF_EVENT (value 5) is a signal that the system sends to all console processes when a user is logging off.
This signal does not indicate which user is logging off, so no assumptions can be made.

.. note::
   This signal is received only by services.
   Interactive applications are terminated at logoff, so they are not present when the system sends this signal.

CTRL_SHUTDOWN_EVENT (value 6) is a signal that the system sends when the system is shutting down.
Interactive applications are not present by the time the system sends this signal, therefore it can be received only be services in this situation.
Services also have their own notification mechanism for shutdown events.

`Document about Windows Ctrl Event <https://learn.microsoft.com/en-us/windows/console/handlerroutine#parameters>`_

Safe-Exit handles these signals by default but can be configured to ignore them.


WM_CLOSE
--------

WM_CLOSE is a Windows message sent as a signal that a window or an application should terminate.

On Windows, ``taskkill /pid ProcessID`` command will send WM_CLOSE to process's main window.
If there is no window for the process, ``taskkill`` will report: ``The process could not be terminated.``.

Safe-Exit can create a hidden window if there is no window.
Call the config function and specify the AUTO_CREATE_CONSOLE flag:

.. code-block:: python

    import safe_exit
    safe_exit.config(safe_exit.DEFAULT_CONFIG | safe_exit.ConfigFlag.AUTO_CREATE_CONSOLE)
    @safe_exit.register
    def cleanup():
        # do cleanup

Safe-Exit will use the ``AllocConsole()`` function to create a new console window, and set this window invisible.


Safe Kill
---------

To safely kill a process:

* First, send a signal to it.
* Let the process perform some clean-up.
* If the process does not terminate in time, then force kill it.

Sending a signal to a process is simple on POSIX systems; just call ``os.kill()`` to do it.

However, it is more complex on Windows:

* If the process has a window, send the WM_CLOSE event to the window.
* If the process is a console program, attach to that console and send the CTRL_C_EVENT to the console.

Safe-Exit's ``safe_kill()`` function can do this automatically:

.. code-block:: python

    import safe_exit
    safe_exit.safe_kill(process_id)


.. warning::

   On Windows, a process can only attach to a console if it is not attached to another console.

   So, one console program cannot send Ctrl events to another program that is in a different console window.

   Use ``pythonw`` to start a program without a console.

   Use ``Popen()`` with DETACHED_PROCESS or CREATE_NO_WINDOW to start a process with no console.

    .. code-block:: python

        process = subprocess.Popen(["someprocess"], creationflags=subprocess.DETACHED_PROCESS)

