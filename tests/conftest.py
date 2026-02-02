import shutil

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def _needs_verilator():
    """Skip test if verilator is not on PATH."""
    if shutil.which("verilator") is None:
        pytest.skip("verilator not found")
