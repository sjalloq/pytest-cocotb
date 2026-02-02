from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestSession:
    runner: object
    directory: Path
    hdl_toplevel: str
    test_module: str
    waves: bool = False
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
        defaults.update(kwargs)
        return self.runner.test(**defaults)
