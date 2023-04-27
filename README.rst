================
Safe Exit
================

Safe Exit is a Python package that provides functionality to handle graceful process termination.
The package allows users to register functions that will be called when the program exits.

Difference from atexit
========================

Python has a standard module called ``atexit`` that does something similar,
but ``atexit`` cannot handle cases where a program is killed by a signal not handled by Python.

Python only handles the SIGINT signal and does not handle SIGTERM, SIGQUIT, and SIGHUP signals.
On Windows, programs can also be killed by SIGBREAK and CTRL_CLOSE_EVENT.

Safe Exit can handle all these signals:

* On POSIX systems: ``SIGINT``, ``SIGTERM``, ``SIGQUIT``, and ``SIGHUP``
* On Windows:

  - ``SIGINT``, ``SIGTERM``, ``SIGBREAK``

  - ``CTRL_CLOSE_EVENT``, ``CTRL_LOGOFF_EVENT``, ``CTRL_SHUTDOWN_EVENT``

Windows also has ``CTRL_C_EVENT`` and ``CTRL_BREAK_EVENT``
which Python translate to ``SIGINT`` and ``SIGBREAK`` signals, respectively.
On windows, ``SIGTERM`` is implemented only  for the current process,
there is no way to send ``SIGTERM`` to other processes.

Installation
============

To install Safe Exit, simply run:

.. code-block:: bash

    pip install safe-exit

Usage
=====

Just register a cleanup function like you would with `atexit`:

.. code-block:: python

    import safe_exit

    def cleanup_function():
        # Perform cleanup tasks

    safe_exit.register(cleanup_function)

The ``register`` function can also be used as a decorator:

.. code-block:: python

    @safe_exit.register
    def cleanup_function():
        # Perform cleanup tasks

Signal handling is configurable.
Call the ``config`` function before registering functions.
The following code configures ``safe_exit`` to handle SIGQUIT and SIGHUP signals:

.. code-block:: python

    from safe_exit import ConfigFlag, config, register
    config(ConfigFlag.SIGQUIT | ConfigFlag.SIGHUP)

    @register
    def cleanup()
        print("clean up")


To nicely kill a process, giving it a chance to clean up:

.. code-block:: python

    process_id = ...
    safe_exit.safe_kill(process_pid)

Contributing
============

Contributions to Safe Exit are welcome!
If you would like to contribute or have any ideas for improvements,
please feel free to open an issue on the project's issue tracker
or get in touch with the maintainer directly.

License
=======

Safe Exit is released under the MIT License. See the LICENSE.txt file for more details.
