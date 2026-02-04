# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

"""HPC-enabled cocotb runner classes."""

from cocotb_tools.runner import Icarus, Questa, Vcs, Verilator, Xcelium

from .mixin import HpcExecutorMixin


class HpcVerilator(HpcExecutorMixin, Verilator):  # type: ignore[misc]
    """Verilator runner with HPC job submission."""

    def _simulator_in_path_build_only(self) -> None:
        """Skip local PATH check; set executable for _build_command."""
        self.executable = "verilator"

    def _build_command(self):
        cmds = super()._build_command()
        # The base class emits ["perl", <resolved-path>, ...] because
        # verilator is a Perl script.  In the HPC case the path isn't
        # resolved locally; just invoke verilator directly via PATH
        # (available after module load).
        if cmds[0][0] == "perl":
            cmds[0][:2] = ["verilator"]
        return cmds


class HpcIcarus(HpcExecutorMixin, Icarus):  # type: ignore[misc]
    """Icarus Verilog runner with HPC job submission."""


class HpcXcelium(HpcExecutorMixin, Xcelium):  # type: ignore[misc]
    """Xcelium runner with HPC job submission."""


class HpcVcs(HpcExecutorMixin, Vcs):  # type: ignore[misc]
    """VCS runner with HPC job submission."""


class HpcQuesta(HpcExecutorMixin, Questa):  # type: ignore[misc]
    """Questa runner with HPC job submission."""


_HPC_RUNNERS: dict[str, type] = {
    "verilator": HpcVerilator,
    "icarus": HpcIcarus,
    "xcelium": HpcXcelium,
    "vcs": HpcVcs,
    "questa": HpcQuesta,
}


def get_hpc_runner(sim_name: str) -> type:
    """Get an HPC-enabled runner class for the given simulator name."""
    try:
        return _HPC_RUNNERS[sim_name]
    except KeyError:
        available = ", ".join(sorted(_HPC_RUNNERS))
        raise ValueError(
            f"Unknown simulator: {sim_name!r}. Available: {available}"
        ) from None
