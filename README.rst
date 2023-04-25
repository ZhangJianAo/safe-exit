================
Safe Exit
================

Safe Exit is a Python package that provides functionality to handle graceful process termination.
The package allows users to register functions that will be called when the program exits.

Different between atexit
========================

Python has standard module ``atexit`` do similar thing,
but ``atexit`` can't handle when program is killed by a signal not handled by Python.

Python only handle SIGINT signal, don't handle ``SIGTERM``, ``SIGQUIT``, ``SIGHUP`` signals.
On Windows, program will also killed by ``SIGBREAK`` and ``CTRL_CLOSE_EVENT``.

safe-exit can handle all this signals:

* On posix system: ``SIGINT``, ``SIGTERM``, ``SIGQUIT``, ``SIGHUP``
* On windows: ``SIGINT``, ``SIGTERM``, ``SIGBREAK``, ``CTRL_CLOSE_EVENT``, ``CTRL_LOGOFF_EVENT``, ``CTRL_SHUTDOWN_EVENT``

Windows also has ``CTRL_C_EVENT`` and ``CTRL_BREAK_EVENT`` which will translate to ``SIGINT``, ``SIGBREAK`` signal by python.
On windows, ``SIGTERM`` are implemented just for the current process, there is no way to send ``SIGTERM`` to other process.

Installation
============

To install Safe Exit, simply run:

.. code-block:: bash

    pip install safe-exit

Usage
=====

Just register clean up function like atexit:

.. code-block:: python

    import safe_exit

    def cleanup_function():
        # Perform cleanup tasks

    safe_exit.register(cleanup_function)

``register`` function can also used as function annotation

.. code-block:: python

    @safe_exit.register
    def cleanup_function():
        # Perform cleanup tasks

Nicely kill a process, giving it a chance to clean up:

.. code-block:: python

    process_id = ...
    safe_exit.nice_kill(process_id)

Contributing
============

Contributions to Safe Exit are welcome! Please read the contributing guidelines before submitting a pull request or reporting an issue.

License
=======

Safe Exit is released under the MIT License. See the LICENSE file for more details.
