Developer guide
===============

Development setup
-----------------

Clone the repository and install in development mode:

.. code-block:: bash

   git clone <repo-url>
   cd pytest-cocotb
   python -m venv .venv
   source .venv/bin/activate
   uv pip install -e ".[dev,docs]"

Running tests
-------------

**Unit tests** (no simulator needed):

.. code-block:: bash

   pytest tests/test_plugin.py

**NFS lock and guard tests:**

.. code-block:: bash

   pytest tests/test_nfs_lock.py tests/test_guard.py

**End-to-end tests** (requires Verilator on PATH):

.. code-block:: bash

   pytest tests/e2e/test_counter.py --simulator verilator \
       --hdl-toplevel counter --sources tests/e2e/rtl/counter.sv

**Full suite:**

.. code-block:: bash

   pytest

Simulator-dependent tests auto-skip if Verilator is not found.

Building documentation
----------------------

.. code-block:: bash

   uv pip install -e ".[docs]"
   sphinx-build docs/source docs/build/html

Open ``docs/build/html/index.html`` in a browser to view the result.

Plugin architecture
-------------------

The plugin registers fixtures with the following dependency graph:

::

   testrun_uid (session)
       │
       ▼
   sim_build_dir (session)
       │
       ├──────────────┐
       ▼              ▼
   build_dir       test_session (function)
   (session)           │
       │               │
       ▼               ▼
   runner ──────► test_session.run()
   (session)

- ``testrun_uid`` generates a timestamp string.
- ``sim_build_dir`` creates the base output directory (with optional
  ``--regress`` timestamped subdirectory).
- ``build_dir`` creates the ``build/`` or ``build_waves/`` subdirectory.
- ``runner`` compiles HDL once at session scope using the build directory.
- ``test_session`` creates a unique per-test directory and yields a
  ``TestSession`` dataclass.

HPC mixin pattern
-----------------

The HPC runner classes use Python's MRO to override execution without
duplicating simulator logic:

.. code-block:: python

   class HpcVerilator(HpcExecutorMixin, Verilator):
       pass

``HpcExecutorMixin`` overrides ``_execute_cmds()`` to submit commands through
hpc-runner's scheduler.  All simulator-specific logic (build commands, test
commands, argument formatting) is inherited from the cocotb base class.

The mixin also overrides ``_simulator_in_path()`` to skip local PATH checks,
since the simulator binary is only available after module loading on the
compute node.

Code organisation
-----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - File
     - Purpose
   * - ``src/pytest_cocotb/plugin.py``
     - Pytest plugin entry point: CLI options, fixtures
   * - ``src/pytest_cocotb/session.py``
     - ``TestSession`` dataclass wrapping ``runner.test()``
   * - ``src/pytest_cocotb/runners.py``
     - HPC-enabled runner classes and ``get_hpc_runner()``
   * - ``src/pytest_cocotb/mixin.py``
     - ``HpcExecutorMixin`` for scheduler-based execution
   * - ``src/pytest_cocotb/nfs_lock.py``
     - ``NFSLock`` — NFS-safe mkdir-based locking
   * - ``src/pytest_cocotb/guard.py``
     - ``CallOnce`` — execute-once guard with NFS lock
   * - ``tests/test_plugin.py``
     - Unit and pytester integration tests
   * - ``tests/test_nfs_lock.py``
     - Tests for ``NFSLock``
   * - ``tests/test_guard.py``
     - Tests for ``CallOnce``
   * - ``tests/e2e/``
     - End-to-end test with real RTL and cocotb testbench

How to add a new simulator
--------------------------

1. **Create the HPC runner class** in ``runners.py``:

   .. code-block:: python

      from cocotb_tools.runner import NewSim
      from .mixin import HpcExecutorMixin

      class HpcNewSim(HpcExecutorMixin, NewSim):
          """NewSim runner with HPC job submission."""

2. **Register it** in the ``_HPC_RUNNERS`` dict in ``runners.py``:

   .. code-block:: python

      _HPC_RUNNERS: dict[str, type] = {
          ...
          "newsim": HpcNewSim,
      }

3. **Override build commands** if needed.  For example, ``HpcVerilator``
   overrides ``_build_command()`` to fix the executable path for remote
   execution.

4. **Test** with the new simulator:

   .. code-block:: bash

      pytest --simulator newsim --hdl-toplevel top --sources rtl/top.sv

Test suite structure
--------------------

**Unit tests** (``tests/test_plugin.py``):

- Tests for ``_sanitise_name()`` with various pytest node ID formats.
- Tests for ``TestSession`` (single-use guard, managed keys, defaults).
- Pytester-based integration tests that exercise CLI options and fixture
  wiring without a real simulator.
- The ``_needs_verilator`` fixture auto-skips simulator-dependent tests when
  Verilator is not available.

**NFS/guard tests** (``tests/test_nfs_lock.py``, ``tests/test_guard.py``):

- Lock acquisition, release, timeout, and stale lock detection.
- ``CallOnce`` success, failure, and re-execution semantics.

**End-to-end tests** (``tests/e2e/``):

- Real RTL (``counter.sv``) compiled and simulated with Verilator.
- cocotb testbench (``cocotb_counter.py``) with ``@cocotb.test()`` coroutines.
- Pytest test (``test_counter.py``) using the ``test_session`` fixture.
