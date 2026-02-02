Examples
========

Basic counter test
------------------

.. code-block:: python

   # test_counter.py
   def test_counter_basic(test_session):
       test_session.run(test_module="cocotb_counter")

.. code-block:: bash

   pytest --sim verilator --hdl-toplevel counter --sources rtl/counter.sv

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

Using ``--waves`` and ``--build-dir``
-------------------------------------

Enable waveform dumping for a debugging session:

.. code-block:: bash

   pytest --sim verilator --hdl-toplevel counter --sources rtl/counter.sv --waves

Reuse a previous build to skip recompilation:

.. code-block:: bash

   pytest --sim verilator --hdl-toplevel counter --sources rtl/counter.sv \
       --build-dir sim_build/20250101_120000/build
