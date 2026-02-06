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
   * - ``--simulator``
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
     - Path to ``.f`` filelist; resolved to absolute and passed as ``-f <path>`` to the simulator
   * - ``--includes``
     - ``[]``
     - Include directories (repeatable)
   * - ``--defines NAME VALUE``
     - ``[]``
     - Preprocessor defines as name/value pairs (repeatable)
   * - ``--build-args``
     - ``[]``
     - Extra build arguments, shlex-split (repeatable)
   * - ``--parameters NAME VALUE``
     - ``[]``
     - HDL parameters as name/value pairs (repeatable); passed to ``runner.build(parameters={...})``
   * - ``--waves``
     - ``False``
     - Enable waveform capture
   * - ``--clean``
     - ``False``
     - Force clean rebuild
   * - ``--sim-build``
     - ``sim_build``
     - Base output directory
   * - ``--regress``
     - ``False``
     - Create a timestamped subdirectory for this run (useful for regression tracking)
   * - ``--modules``
     - ``[]``
     - Environment modules to load before simulation (repeatable; see :doc:`hpc`)

Fixtures
--------

``testrun_uid`` *(session)*
    Timestamp string (``YYYYMMDD_HHMMSS``) identifying this pytest invocation.

``sim_build_dir`` *(session)*
    ``Path`` to the base output directory for this run.  When ``--regress`` is
    passed this is ``<sim-build>/<testrun_uid>/``; otherwise it is simply
    ``<sim-build>/``.

``build_dir`` *(session)*
    ``Path`` to the compiled HDL directory.  Defaults to
    ``<sim_build_dir>/build/``.  When ``--waves`` is enabled a separate
    ``build_waves/`` directory is used instead, so that wave-enabled and
    non-wave builds do not clobber each other.

``runner`` *(session)*
    The cocotb runner instance.  Compiles the HDL design **once** per session
    using ``cocotb_tools.runner.get_runner()``.  When pytest output capture is
    active, build output is redirected to ``build_dir/build.log``.

``test_session`` *(function)*
    A :class:`~pytest_cocotb.session.TestSession` bound to a unique per-test
    directory.

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
       log_file: Path | None = None

**run(\*\*kwargs) -> Path**

Delegates to ``runner.test()`` with sensible defaults derived from the
dataclass fields.  Any keyword argument accepted by ``runner.test()`` can be
passed to override the defaults (e.g. ``test_module``, ``waves``).

``run()`` may only be called **once** per ``TestSession`` instance; a second
call raises ``RuntimeError``.

When pytest output capture is active (the default), the ``log_file`` field is
automatically set to ``<test_dir>/sim.log`` so that simulator output is
captured to a file instead of being printed to stdout.

.. autoclass:: pytest_cocotb.session.TestSession
   :members:

Build behaviour
---------------

* The ``runner`` fixture compiles HDL **once** at session scope.
* Subsequent tests reuse the compiled build in ``build_dir``.
* When ``--waves`` is enabled the build is placed in ``build_waves/`` instead
  of ``build/``, so you can switch between wave and non-wave runs without
  forcing a rebuild.
* Pass ``--clean`` to force a full rebuild.

Output directory layout
-----------------------

**Without ``--regress``** (default):

::

   sim_build/
   ├── build/                                      # compiled HDL (build_dir)
   ├── test_counter__test_counter_basic/
   │   ├── sim.log                                  # simulator stdout
   │   └── ...                                      # simulator output
   └── ...

**With ``--regress``**:

::

   sim_build/
   └── 20250101_120000/                             # testrun_uid
       ├── build/                                    # compiled HDL (build_dir)
       ├── test_counter__test_counter_basic/
       │   ├── sim.log
       │   └── ...
       └── ...
