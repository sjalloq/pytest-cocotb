# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

from pathlib import Path

# Directory containing this conftest
E2E_DIR = Path(__file__).parent

VERILATOR_MODULE = "verilator"


def pytest_configure(config):
    """Set default option values for the e2e test suite."""
    # Only override if the user didn't pass them explicitly
    if not config.getoption("hdl_toplevel"):
        config.option.hdl_toplevel = "counter"

    if not config.getoption("sources"):
        config.option.sources = [str(E2E_DIR / "rtl" / "counter.sv")]

    if not config.getoption("modules"):
        config.option.modules = [VERILATOR_MODULE]
