# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

"""HPC executor mixin that redirects cocotb runner execution to hpc-runner."""

from __future__ import annotations

import logging
import os
import re
import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar, TextIO

from hpc_runner import Job, JobStatus

logger = logging.getLogger(__name__)

_VALID_ENV_KEY = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _cocotb_env_diff(env: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Separate cocotb env changes into replacements and appends.

    Returns:
        (env_vars, env_append) — full replacements and path-style appends.
    """
    base = os.environ
    env_vars: dict[str, str] = {}
    env_append: dict[str, str] = {}

    for k, v in env.items():
        if not _VALID_ENV_KEY.match(k):
            continue
        old = base.get(k)
        if old == v:
            continue  # unchanged
        if old is not None and v.startswith(old + os.pathsep):
            # cocotb appended to this var — extract only the new segment
            env_append[k] = v[len(old) + len(os.pathsep) :]
        else:
            env_vars[k] = v

    return env_vars, env_append


class HpcExecutorMixin:
    """Mixin that overrides cocotb runner execution to submit via hpc-runner.

    Place this before the simulator class in the MRO so that
    ``_execute_cmds`` is resolved from here first::

        class HpcXcelium(HpcExecutorMixin, Xcelium):
            pass

    All commands (build and test) are submitted through hpc-runner's
    auto-detected scheduler.  The ``local`` scheduler runs jobs as
    subprocesses with module-loading support; cluster schedulers
    (SGE, SLURM) submit to the grid.
    """

    job_name: str = "sim"
    modules: ClassVar[list[str]] = []

    def _simulator_in_path(self) -> None:
        """Skip local PATH check -- the simulator is available after module load."""

    def _execute(self, cmds, cwd):
        """Override to bypass cocotb's file-handle stdout routing.

        The HPC scheduler manages output redirection via Job.stdout
        (a path string used in the bash script's exec redirect), not
        via a Python file handle.
        """
        self._execute_cmds(cmds, cwd)

    def _execute_cmds(
        self,
        cmds: Sequence[list[str]],
        cwd: os.PathLike[str],
        stdout: TextIO | None = None,
    ) -> None:
        """Submit commands to the scheduler instead of running locally."""
        # Use self.log_file (set by cocotb build/test) as the Job stdout path.
        # When None, no redirection — output inherits parent stdout (terminal).
        log_file = getattr(self, "log_file", None)
        job_stdout = str(Path(log_file).resolve()) if log_file else None

        for cmd in cmds:
            command_str = " ".join(shlex.quote(c) for c in cmd)

            env_vars, env_append = _cocotb_env_diff(self.env)  # type: ignore[attr-defined]

            # Only pass non-empty kwargs so hpc-runner's config defaults
            # (tool-detected modules, config env_vars, etc.) are preserved.
            job_kwargs: dict[str, Any] = dict(
                command=command_str,
                name=self.job_name,
                workdir=str(cwd),
            )
            if self.modules:
                job_kwargs["modules"] = list(self.modules)
            if job_stdout:
                job_kwargs["stdout"] = job_stdout

            logger.debug("Creating Job with kwargs: %s", job_kwargs)

            job = Job(**job_kwargs)

            # Merge cocotb env changes *on top of* config-derived values
            # so that hpc-runner config (e.g. [defaults.env_vars]) is preserved.
            if env_vars:
                job.env_vars.update(env_vars)
            if env_append:
                job.env_append.update(env_append)

            logger.debug(
                "Job %r resolved — modules=%s, env_vars=%s, env_append=%s",
                job.name,
                job.modules,
                job.env_vars,
                job.env_append,
            )

            result = job.submit(interactive=(job_stdout is None))
            status = result.wait()

            logger.debug("Job %s finished with status %s", result.job_id, status.name)

            if status != JobStatus.COMPLETED:
                output = result.read_stdout(tail=50)
                msg = (
                    f"HPC job {result.job_id} {status.name}\n"
                    f"  workdir: {cwd}\n"
                    f"  command: {command_str}"
                )
                if output:
                    msg += f"\n  output:\n{output}"
                raise RuntimeError(msg)
