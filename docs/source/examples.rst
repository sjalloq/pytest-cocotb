Examples
========

Basic counter test
------------------

.. code-block:: python

   # test_counter.py
   def test_counter_basic(test_session):
       test_session.run(test_module="cocotb_counter")

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv

Parametrised tests
------------------

Combine ``pytest.mark.parametrize`` with ``test_session`` to run the same
cocotb testbench against different configurations:

.. code-block:: python

   import pytest

   @pytest.mark.parametrize("width", [8, 16, 32])
   def test_counter_widths(test_session, width):
       test_session.run(
           test_module="cocotb_counter",
           parameters={"WIDTH": width},
       )

Each parametrised variant gets its own output directory automatically.

Overriding ``test_module`` in ``run()``
---------------------------------------

The ``test_session`` fixture derives ``test_module`` from the test file's
module name by default.  Override it to point at a different cocotb module:

.. code-block:: python

   def test_with_custom_module(test_session):
       test_session.run(test_module="my_other_cocotb_tests")

Using ``--waves``
-----------------

Enable waveform dumping for a debugging session:

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv --waves

When ``--waves`` is enabled the build is placed in a separate ``build_waves/``
directory, so you can switch between wave and non-wave runs without triggering
a rebuild.

Using ``--defines``
-------------------

Pass preprocessor defines as name/value pairs:

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv \
       --defines WIDTH 16 --defines DEPTH 32

Using ``--filelist``
--------------------

Point at a ``.f`` filelist instead of listing source files individually:

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --filelist sources.f

The filelist is passed as ``-f <path>`` to the simulator build command.

Using ``--includes``
--------------------

Add include directories for ``\`include`` directives:

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv \
       --includes rtl/includes --includes rtl/common

Using ``--build-args``
----------------------

Pass extra arguments to the simulator build step.  Arguments are shlex-split,
so quoting works as expected:

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv \
       --build-args "--trace-fst" --build-args "-Wno-fatal"

Using ``--regress``
-------------------

Create a timestamped output directory for each run, useful for regression
tracking:

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv --regress

This produces a layout like ``sim_build/20250101_120000/build/`` instead of
``sim_build/build/``.

Using ``--modules``
-------------------

Load environment modules before simulation (useful on HPC clusters):

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv \
       --modules verilator/5.024

See :doc:`hpc` for more details on HPC integration.

Setting defaults in ``conftest.py``
-----------------------------------

Rather than repeating CLI flags, you can set defaults in ``conftest.py``:

.. code-block:: python

   # conftest.py
   def pytest_addoption(parser):
       """Override defaults for this project."""
       parser.addini("simulator", default="verilator")
       parser.addini("hdl_toplevel", default="counter")

Or more commonly, use ``addopts`` in ``pyproject.toml``:

.. code-block:: toml

   [tool.pytest.ini_options]
   addopts = "--simulator verilator --hdl-toplevel counter --sources rtl/counter.sv"

Log file behaviour
------------------

When pytest output capture is active (the default), the ``test_session``
fixture automatically sets ``log_file`` to ``<test_dir>/sim.log``.  This
captures all simulator output to a file.

To disable capture and see simulator output live, run with ``-s``:

.. code-block:: bash

   pytest -s --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv

You can also provide a custom log file path in ``run()``:

.. code-block:: python

   def test_counter_basic(test_session):
       test_session.run(
           test_module="cocotb_counter",
           log_file="custom.log",  # relative to the test directory
       )
