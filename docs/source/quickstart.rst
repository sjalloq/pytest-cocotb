Quickstart
==========

pytest-cocotb is a pytest plugin that lets you drive cocotb HDL simulations
from pytest.  HDL is compiled once per session, and each test function
launches the simulator with its own cocotb test module.

Installation
------------

.. code-block:: bash

   pip install -e .

Minimal example
---------------

Given a simple counter RTL file ``rtl/counter.sv``:

.. code-block:: systemverilog

   module counter (
     input  logic       clk,
     input  logic       rst,
     output logic [7:0] count
   );
     always_ff @(posedge clk)
       if (rst) count <= '0;
       else     count <= count + 1;
   endmodule

Write a cocotb testbench in ``cocotb_counter.py``:

.. code-block:: python

   import cocotb
   from cocotb.clock import Clock
   from cocotb.triggers import RisingEdge

   @cocotb.test()
   async def counter_basic(dut):
       clock = Clock(dut.clk, 10, unit="ns")
       cocotb.start_soon(clock.start())

       dut.rst.value = 1
       for _ in range(3):
           await RisingEdge(dut.clk)
       dut.rst.value = 0

       await RisingEdge(dut.clk)
       prev = int(dut.count.value)
       await RisingEdge(dut.clk)
       curr = int(dut.count.value)
       assert curr == prev + 1

Then write a pytest test that uses the ``test_session`` fixture:

.. code-block:: python

   def test_counter_basic(test_session):
       test_session.run(test_module="cocotb_counter")

Single-file tests
-----------------

The ``test_session`` fixture defaults ``test_module`` to the current pytest
file's ``__name__``.  This means you can put cocotb coroutines and pytest
tests in the **same file** and omit the ``test_module`` argument entirely:

.. code-block:: python

   # test_counter.py
   import cocotb
   from cocotb.clock import Clock
   from cocotb.triggers import RisingEdge

   @cocotb.test()
   async def counter_basic(dut):
       clock = Clock(dut.clk, 10, unit="ns")
       cocotb.start_soon(clock.start())

       dut.rst.value = 1
       for _ in range(3):
           await RisingEdge(dut.clk)
       dut.rst.value = 0

       await RisingEdge(dut.clk)
       prev = int(dut.count.value)
       await RisingEdge(dut.clk)
       curr = int(dut.count.value)
       assert curr == prev + 1

   def test_counter(test_session):
       test_session.run()  # uses this file as the cocotb test module

Running
-------

.. code-block:: bash

   pytest --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv

Setting defaults
----------------

To avoid repeating CLI flags on every invocation, add them to ``addopts`` in
any of pytest's configuration files.

``pytest.ini``
~~~~~~~~~~~~~~

.. code-block:: ini

   [pytest]
   addopts = --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv

``pyproject.toml``
~~~~~~~~~~~~~~~~~~

.. code-block:: toml

   [tool.pytest.ini_options]
   addopts = "--simulator verilator --hdl-toplevel counter --sources rtl/counter.sv"

``setup.cfg``
~~~~~~~~~~~~~

.. code-block:: ini

   [tool:pytest]
   addopts = --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv
