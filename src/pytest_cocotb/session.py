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
