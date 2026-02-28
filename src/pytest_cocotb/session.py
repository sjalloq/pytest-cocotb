# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_MANAGED_KEYS = frozenset({"test_dir", "build_dir"})


@dataclass
class TestSession:
    __test__ = False  # prevent pytest collection
    runner: object
    directory: Path
    hdl_toplevel: str
    test_module: str
    waves: bool = False
    log_file: Path | None = None
    hdl_toplevel_lang: str | None = None
    verbose: bool = False
    gui: bool = False
    test_args: list[str] = field(default_factory=list)
    plusargs: list[str] = field(default_factory=list)
    extra_env: dict[str, str] = field(default_factory=dict)
    seed: str | int | None = None
    testcase: str | None = None
    test_filter: str | None = None
    results_xml: str | None = None
    _has_run: bool = field(default=False, repr=False)

    def run(self, **kwargs) -> Path:
        """Run cocotb test(s) in the simulator. Delegates to runner.test()."""
        if self._has_run:
            raise RuntimeError("run() can only be called once per test")

        conflicts = _MANAGED_KEYS & kwargs.keys()
        if conflicts:
            raise ValueError(
                f"Cannot override fixture-managed keys: {conflicts}. "
                f"Use CLI options (--sim-build, --waves) to control directories."
            )

        self._has_run = True
        defaults = dict(
            hdl_toplevel=self.hdl_toplevel,
            test_module=self.test_module,
            test_dir=self.directory,
            waves=self.waves,
        )
        if self.log_file is not None:
            defaults["log_file"] = self.log_file
        if self.hdl_toplevel_lang is not None:
            defaults["hdl_toplevel_lang"] = self.hdl_toplevel_lang
        if self.verbose:
            defaults["verbose"] = self.verbose
        if self.gui:
            defaults["gui"] = self.gui
        if self.test_args:
            defaults["test_args"] = self.test_args
        if self.plusargs:
            defaults["plusargs"] = self.plusargs
        if self.extra_env:
            defaults["extra_env"] = self.extra_env
        if self.seed is not None:
            defaults["seed"] = self.seed
        if self.testcase is not None:
            defaults["testcase"] = self.testcase
        if self.test_filter is not None:
            defaults["test_filter"] = self.test_filter
        if self.results_xml is not None:
            defaults["results_xml"] = self.results_xml

        # Resolve user-provided relative log_file against test_dir
        if "log_file" in kwargs:
            lf = Path(kwargs["log_file"])
            if not lf.is_absolute():
                kwargs["log_file"] = self.directory / lf

        defaults.update(kwargs)

        logger.debug("TestSession.run() final arguments:")
        for k, v in sorted(defaults.items()):
            logger.debug("  %-20s = %s", k, v)

        return self.runner.test(**defaults)  # type: ignore[attr-defined, no-any-return]
