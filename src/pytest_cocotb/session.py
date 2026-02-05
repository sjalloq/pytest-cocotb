# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

from dataclasses import dataclass, field
from pathlib import Path


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
        return self.runner.test(**defaults)  # type: ignore[attr-defined, no-any-return]
