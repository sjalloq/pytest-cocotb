Plugin reference
================

CLI options
-----------

All options belong to the ``cocotb`` option group.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Flag
     - Default
     - Description
   * - ``--sim``
     - ``$SIM`` or ``verilator``
     - Simulator name
   * - ``--hdl-toplevel``
     - ``$HDL_TOPLEVEL``
     - HDL top-level module name
   * - ``--hdl-library``
     - ``top``
     - HDL library name
   * - ``--sources``
     - ``[]``
     - HDL source files (repeatable)
   * - ``--filelist``
     - *None*
     - Path to ``.f`` filelist; passed as ``-f <path>`` to the simulator
   * - ``--includes``
     - ``[]``
     - Include directories (repeatable)
   * - ``--defines NAME VALUE``
     - ``[]``
     - Preprocessor defines as name/value pairs (repeatable)
   * - ``--build-args``
     - ``[]``
     - Extra build arguments, shlex-split (repeatable)
   * - ``--waves``
     - ``False``
     - Enable waveform capture
   * - ``--clean``
     - ``False``
     - Force clean rebuild
   * - ``--build-dir``
     - *None*
     - Explicit build directory (skip timestamped dir)
   * - ``--sim-build``
     - ``sim_build``
     - Base output directory

Fixtures
--------

``testrun_uid`` *(session)*
    Timestamp string (``YYYYMMDD_HHMMSS``) identifying this pytest invocation.

``sim_build_dir`` *(session)*
    ``Path`` to the base output directory for this run:
    ``<sim-build>/<testrun_uid>/``.

``build_dir`` *(session)*
    ``Path`` to the compiled HDL directory.  When ``--build-dir`` is given that
    path is used directly; otherwise it defaults to
    ``<sim_build_dir>/build/``.

``runner`` *(session)*
    The cocotb runner instance.  Compiles the HDL design **once** per session
    using ``cocotb_tools.runner.get_runner()``.

``test_session`` *(function)*
    A :class:`TestSession` bound to a unique per-test directory.

TestSession API
---------------

.. code-block:: python

   @dataclass
   class TestSession:
       runner: object
       directory: Path
       hdl_toplevel: str
       test_module: str
       waves: bool = False

**run(\*\*kwargs) -> Path**

Delegates to ``runner.test()`` with sensible defaults derived from the
dataclass fields.  Any keyword argument accepted by ``runner.test()`` can be
passed to override the defaults (e.g. ``test_module``, ``waves``).

``run()`` may only be called **once** per ``TestSession`` instance; a second
call raises ``RuntimeError``.

Build behaviour
---------------

* The ``runner`` fixture compiles HDL **once** at session scope.
* Subsequent tests reuse the compiled build in ``build_dir``.
* Pass ``--build-dir`` to point at a pre-existing build and skip
  recompilation (the directory must already contain compiled artefacts).
* Pass ``--clean`` to force a full rebuild.

Output directory layout
-----------------------

::

   sim_build/
   └── 20250101_120000/          # testrun_uid
       ├── build/                 # compiled HDL (build_dir)
       ├── tests_e2e_test_counter.py_test_counter_basic/
       │   └── ...                # simulator output for that test
       └── ...
