# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

import subprocess

import pytest

pytest_plugins = ["pytester"]

VERILATOR_MODULE = "verilator"


@pytest.fixture
def _needs_verilator():
    """Skip test if verilator module is not available."""
    try:
        result = subprocess.run(
            ["bash", "-lc", f"module load {VERILATOR_MODULE} && which verilator"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"module {VERILATOR_MODULE} not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("module system not available")
