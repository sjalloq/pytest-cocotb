HPC support
===========

pytest-cocotb can submit simulation jobs to HPC cluster schedulers instead of
running them locally.  This is useful when simulations are resource-intensive
and need to run on dedicated compute nodes.

Overview
--------

The HPC support is built on two layers:

1. **hpc-runner** — an external package that provides job submission to
   schedulers (local, SGE, SLURM).
2. **HPC runner classes** — wrappers around cocotb's simulator runners that
   redirect execution through hpc-runner.

The ``--modules`` option allows loading environment modules (e.g.
``verilator/5.024``) on the compute node before the simulator runs.

Supported simulators
--------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Simulator
     - HPC class
     - Base cocotb class
   * - Verilator
     - ``HpcVerilator``
     - ``cocotb_tools.runner.Verilator``
   * - Icarus Verilog
     - ``HpcIcarus``
     - ``cocotb_tools.runner.Icarus``
   * - Xcelium
     - ``HpcXcelium``
     - ``cocotb_tools.runner.Xcelium``
   * - VCS
     - ``HpcVcs``
     - ``cocotb_tools.runner.Vcs``
   * - Questa
     - ``HpcQuesta``
     - ``cocotb_tools.runner.Questa``

How it works
------------

Each HPC runner class uses Python's MRO (method resolution order) to override
execution.  The ``HpcExecutorMixin`` is placed **before** the simulator class
in the inheritance chain:

.. code-block:: python

   class HpcVerilator(HpcExecutorMixin, Verilator):
       pass

This ensures that ``_execute_cmds()`` resolves to the mixin's version, which
submits commands through the scheduler instead of running them as local
subprocesses.  All other simulator-specific logic (build commands, test
commands, etc.) is inherited unchanged from the base cocotb class.

The mixin:

- Skips local PATH checks for the simulator binary (it will be available
  after module loading on the compute node).
- Extracts cocotb's environment variable changes and passes them to the job
  as ``env_vars`` and ``env_append`` dictionaries.
- Redirects simulator output to ``log_file`` when set.

Scheduler configuration
-----------------------

The scheduler is configured by hpc-runner and is selected automatically based
on the environment.  By default:

- If running on a node with SGE (``SGE_ROOT`` set), the SGE scheduler is used.
- If running on a node with SLURM (``SLURM_CONF`` or ``squeue`` available),
  the SLURM scheduler is used.
- Otherwise, the **local** scheduler runs jobs as subprocesses.

The local scheduler still supports module loading, so ``--modules`` works even
without a cluster.

Environment modules
-------------------

Use ``--modules`` to load environment modules before simulation:

.. code-block:: bash

   pytest --simulator xcelium --hdl-toplevel top --sources rtl/top.sv \
       --modules xcelium/23.09 --modules python/3.11

Modules are loaded in the order specified, before the simulator command runs.

Example usage
-------------

Run on an HPC cluster with Xcelium, loading the required modules:

.. code-block:: bash

   pytest --simulator xcelium --hdl-toplevel top --sources rtl/top.sv \
       --modules xcelium/23.09 --modules python/3.11

The plugin automatically:

1. Creates an HPC-enabled runner via ``get_hpc_runner("xcelium")``.
2. Attaches the scheduler from ``hpc_runner.get_scheduler()``.
3. Submits build and test commands as cluster jobs.
4. Waits for each job to complete and raises on failure.

API reference
-------------

.. autofunction:: pytest_cocotb.runners.get_hpc_runner

.. autoclass:: pytest_cocotb.mixin.HpcExecutorMixin
   :members:
