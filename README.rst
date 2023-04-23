================
Safe Exit
================

Safe Exit is a Python package that provides functionality to handle graceful process termination.
The package allows users to register functions that will be called when the program exits,
and it also includes a utility to nicely kill processes,
giving them an opportunity to clean up before terminating.

Installation
============

To install Safe Exit, simply run:

.. code-block:: bash

    pip install safe-exit

Usage
=====

To use the Safe Exit package in your Python code, first import the necessary functions:

.. code-block:: python

    import safe_exit import

Register a function to be called when the program exits:

.. code-block:: python

    def cleanup_function():
        # Perform cleanup tasks

    safe_exit.register(cleanup_function)

`register` function can also used as function annotation

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
