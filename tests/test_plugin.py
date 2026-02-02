from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pytest_cocotb.session import TestSession


# ---------- TestSession.run() single-use guard ----------

class TestTestSession:
    def _make_session(self, **kwargs):
        defaults = dict(
            runner=MagicMock(),
            directory=Path("/tmp/test"),
            hdl_toplevel="top",
            test_module="test_example",
        )
        defaults.update(kwargs)
        return TestSession(**defaults)

    def test_run_delegates_to_runner(self):
        session = self._make_session()
        session.run(testcase="my_test", seed=42)

        session.runner.test.assert_called_once_with(
            hdl_toplevel="top",
            test_module="test_example",
            test_dir=Path("/tmp/test"),
            waves=False,
            testcase="my_test",
            seed=42,
        )

    def test_run_kwargs_override_defaults(self):
        session = self._make_session()
        session.run(test_module="overridden_module")

        call_kwargs = session.runner.test.call_args.kwargs
        assert call_kwargs["test_module"] == "overridden_module"

    def test_run_single_use_guard(self):
        session = self._make_session()
        session.run()

        with pytest.raises(RuntimeError, match="once per test"):
            session.run()

    def test_waves_passed_through(self):
        session = self._make_session(waves=True)
        session.run()

        session.runner.test.assert_called_once()
        call_kwargs = session.runner.test.call_args.kwargs
        assert call_kwargs["waves"] is True


# ---------- Name sanitisation ----------

from pytest_cocotb.plugin import _sanitise_name


class TestSanitiseName:
    def test_simple_name(self):
        assert _sanitise_name("test_foo") == "test_foo"

    def test_parametrize_brackets(self):
        assert _sanitise_name("test_foo[param1-param2]") == "test_foo_param1-param2"

    def test_path_separators(self):
        assert _sanitise_name("tests/test_foo.py::test_bar") == "tests_test_foo.py_test_bar"

    def test_collapses_underscores(self):
        assert _sanitise_name("a///b") == "a_b"

    def test_strips_leading_trailing(self):
        assert _sanitise_name("[hello]") == "hello"


# ---------- CLI option registration ----------

def test_options_registered(pytester):
    """Verify plugin options are registered when the plugin is loaded."""
    pytester.makeconftest("")
    result = pytester.runpytest("--help")
    result.stdout.fnmatch_lines([
        "*--sim*",
        "*--hdl-toplevel*",
        "*--sources*",
        "*--waves*",
        "*--clean*",
        "*--sim-build*",
    ])


def test_testrun_uid_fixture(pytester):
    """Verify testrun_uid fixture returns a timestamp-like string."""
    pytester.makepyfile("""
        import re

        def test_uid(testrun_uid):
            assert re.match(r"\\d{8}_\\d{6}", testrun_uid)
    """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


# ---------- Rebuild behaviour ----------

def _make_counter_project(pytester):
    """Create a minimal counter design + cocotb test in pytester's directory."""
    rtl_dir = pytester.path / "rtl"
    rtl_dir.mkdir()
    (rtl_dir / "counter.sv").write_text("""\
module counter (
    input  logic       clk,
    input  logic       rst,
    output logic [7:0] count
);
    always_ff @(posedge clk) begin
        if (rst) count <= 8'd0;
        else     count <= count + 8'd1;
    end
endmodule
""")

    pytester.makepyfile(cocotb_counter="""\
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
    await RisingEdge(dut.clk)
""")

    pytester.makepyfile("""\
def test_counter(test_session):
    test_session.run(test_module="cocotb_counter")
""")


def _get_build_artifact_mtimes(build_dir):
    """Return a dict of {relative_path: mtime} for all files in build_dir."""
    mtimes = {}
    for p in build_dir.rglob("*"):
        if p.is_file():
            mtimes[str(p.relative_to(build_dir))] = p.stat().st_mtime
    return mtimes


@pytest.mark.usefixtures("_needs_verilator")
def test_no_rebuild_without_clean(pytester):
    """Second run with same --build-dir should not recompile."""
    _make_counter_project(pytester)
    build_dir = pytester.path / "build"
    common_args = [
        "--sim", "verilator",
        "--hdl-toplevel", "counter",
        "--sources", str(pytester.path / "rtl" / "counter.sv"),
        "--build-dir", str(build_dir),
    ]

    # First run: builds and runs
    r1 = pytester.runpytest(*common_args)
    r1.assert_outcomes(passed=1)

    mtimes_after_first = _get_build_artifact_mtimes(build_dir)
    assert mtimes_after_first, "Build directory should contain artifacts"

    # Second run: same build dir, no --clean
    r2 = pytester.runpytest(*common_args)
    r2.assert_outcomes(passed=1)

    mtimes_after_second = _get_build_artifact_mtimes(build_dir)

    # Check that no build artifacts were modified
    changed = {
        path for path in mtimes_after_first
        if mtimes_after_first[path] != mtimes_after_second.get(path)
    }
    assert not changed, f"Build artifacts were modified on second run: {changed}"


@pytest.mark.usefixtures("_needs_verilator")
def test_rebuild_with_clean(pytester):
    """--clean should force a full rebuild."""
    _make_counter_project(pytester)
    build_dir = pytester.path / "build"
    common_args = [
        "--sim", "verilator",
        "--hdl-toplevel", "counter",
        "--sources", str(pytester.path / "rtl" / "counter.sv"),
        "--build-dir", str(build_dir),
    ]

    # First run
    r1 = pytester.runpytest(*common_args)
    r1.assert_outcomes(passed=1)

    mtimes_after_first = _get_build_artifact_mtimes(build_dir)

    # Second run with --clean
    r2 = pytester.runpytest(*common_args, "--clean")
    r2.assert_outcomes(passed=1)

    mtimes_after_second = _get_build_artifact_mtimes(build_dir)

    # At least some artifacts should have new timestamps
    changed = {
        path for path in mtimes_after_first
        if path in mtimes_after_second
        and mtimes_after_first[path] != mtimes_after_second[path]
    }
    assert changed, "Expected build artifacts to be rebuilt with --clean"
