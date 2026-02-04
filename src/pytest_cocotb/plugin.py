# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

import os
import re
import shlex
from datetime import datetime
from pathlib import Path

import pytest
from hpc_runner import get_scheduler

from .runners import get_hpc_runner
from .session import TestSession


def pytest_addoption(parser):
    group = parser.getgroup("cocotb", "cocotb simulation options")

    group.addoption(
        "--simulator",
        default=os.environ.get("SIM", "verilator"),
        help="Simulator name (default: $SIM or 'verilator')",
    )
    group.addoption(
        "--hdl-toplevel",
        default=os.environ.get("HDL_TOPLEVEL"),
        help="HDL top-level module name (default: $HDL_TOPLEVEL)",
    )
    group.addoption(
        "--hdl-library",
        default="top",
        help="HDL library name (default: 'top')",
    )
    group.addoption(
        "--sources",
        action="append",
        default=[],
        help="HDL source files (repeatable)",
    )
    group.addoption(
        "--filelist",
        default=None,
        help="Path to .f filelist; passed as -f <path> to the simulator",
    )
    group.addoption(
        "--includes",
        action="append",
        default=[],
        help="Include directories (repeatable)",
    )
    group.addoption(
        "--defines",
        nargs=2,
        action="append",
        default=[],
        metavar=("NAME", "VALUE"),
        help="Preprocessor defines as name/value pairs (repeatable)",
    )
    group.addoption(
        "--build-args",
        action="append",
        default=[],
        help="Extra build arguments (shlex-split, repeatable)",
    )
    group.addoption(
        "--waves",
        action="store_true",
        default=False,
        help="Enable waveform capture",
    )
    group.addoption(
        "--clean",
        action="store_true",
        default=False,
        help="Force clean rebuild",
    )
    group.addoption(
        "--build-dir",
        default=None,
        help="Explicit build directory (skip timestamped dir)",
    )
    group.addoption(
        "--sim-build",
        default="sim_build",
        help="Base output directory (default: 'sim_build')",
    )
    group.addoption(
        "--modules",
        action="append",
        default=[],
        help="Environment modules to load before simulation (repeatable)",
    )


def _sanitise_name(name: str) -> str:
    """Sanitise a test node ID into a filesystem-safe directory name."""
    # Replace path separators and brackets with underscores
    name = re.sub(r"[/\\:;<>|?*\[\](){}]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores
    return name.strip("_")


@pytest.fixture(scope="session")
def testrun_uid():
    """Timestamp string identifying this pytest invocation."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@pytest.fixture(scope="session")
def sim_build_dir(request, testrun_uid):
    """Base output directory for this test run."""
    base = Path(request.config.getoption("sim_build"))
    path = base / testrun_uid
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def build_dir(request, sim_build_dir):
    """Build directory for the compiled HDL."""
    explicit = request.config.getoption("build_dir")
    path = Path(explicit) if explicit else sim_build_dir / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def runner(request, build_dir):
    """Session-scoped fixture that compiles the HDL design once."""
    config = request.config

    sim = config.getoption("simulator")
    hdl_toplevel = config.getoption("hdl_toplevel")
    hdl_library = config.getoption("hdl_library")
    sources = config.getoption("sources")
    filelist = config.getoption("filelist")
    includes = config.getoption("includes")
    defines = config.getoption("defines")
    raw_build_args = config.getoption("build_args")
    clean = config.getoption("clean")

    # Flatten shlex-split build args
    build_args = []
    for arg in raw_build_args:
        build_args.extend(shlex.split(arg))

    # Handle filelist: prepend -f <path> to build_args
    if filelist:
        build_args = ["-f", filelist, *build_args]

    # Build defines dict
    defines_dict = {name: value for name, value in defines}

    modules = config.getoption("modules")

    runner_cls = get_hpc_runner(sim)
    runner = runner_cls()
    runner.scheduler = get_scheduler()
    runner.modules = modules

    runner.build(
        hdl_toplevel=hdl_toplevel,
        hdl_library=hdl_library,
        sources=[Path(s) for s in sources],
        includes=[Path(i) for i in includes],
        defines=defines_dict,
        build_args=build_args,
        build_dir=build_dir,
        clean=clean,
    )

    return runner


@pytest.fixture(scope="function")
def test_session(request, runner, sim_build_dir):
    """Per-test fixture providing a TestSession bound to a unique directory."""
    config = request.config
    hdl_toplevel = config.getoption("hdl_toplevel")
    waves = config.getoption("waves")

    # Derive test_module from the Python module containing the test
    test_module = request.module.__name__

    # Build a unique directory name from the test node ID
    node_id = request.node.nodeid
    safe_name = _sanitise_name(node_id)
    test_dir = sim_build_dir / safe_name
    test_dir.mkdir(parents=True, exist_ok=True)

    yield TestSession(
        runner=runner,
        directory=test_dir,
        hdl_toplevel=hdl_toplevel,
        test_module=test_module,
        waves=waves,
    )
