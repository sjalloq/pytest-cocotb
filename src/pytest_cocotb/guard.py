# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

"""NFS-safe call-once guard for pytest-xdist workers."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pytest_cocotb.nfs_lock import NFSLock

log = logging.getLogger(__name__)


def _fsync_directory(dir_path: Path) -> None:
    """fsync a directory fd to flush metadata (new/renamed entries) to disk."""
    fd = os.open(str(dir_path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _create_marker(path: Path, content: str = "") -> None:
    """Create a marker file with fsync on both the file and its parent dir."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        if content:
            os.write(fd, content.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_directory(path.parent)


def _nfs_file_exists(path: Path) -> bool:
    """Check file existence in an NFS-cache-safe way.

    Opening the parent directory forces the NFS client to revalidate its
    dentry cache.  Then we attempt ``os.open(O_RDONLY)`` on the file itself
    instead of relying on ``stat()`` which may return cached results.
    """
    parent = path.parent
    try:
        dfd = os.open(str(parent), os.O_RDONLY)
        os.close(dfd)
    except OSError:
        return False

    try:
        fd = os.open(str(path), os.O_RDONLY)
        os.close(fd)
    except OSError:
        return False
    return True


@dataclass
class CallOnce:
    """Ensures a callable is executed exactly once across processes.

    Uses an NFS-safe ``mkdir``-based lock and completion/failure markers so
    that exactly one caller executes the callable while others wait and then
    reuse the result.

    Example::

        guard = CallOnce(
            path=build_dir,
            name="hdl_compile",
            fn=lambda: runner.build(...),
        )
        guard.ensure_done()
    """

    path: Path
    name: str
    fn: Callable[[], Any]
    timeout: float = 3600.0

    @property
    def _lock_dir(self) -> Path:
        return self.path / ".locks"

    @property
    def _lock_path(self) -> Path:
        return self._lock_dir / f"{self.name}.lock"

    @property
    def _done_file(self) -> Path:
        return self._lock_dir / f"{self.name}.done"

    @property
    def _fail_file(self) -> Path:
        return self._lock_dir / f"{self.name}.failed"

    def ensure_done(self) -> None:
        """Execute the callable if it hasn't been run yet."""
        self.path.mkdir(parents=True, exist_ok=True)
        self._lock_dir.mkdir(parents=True, exist_ok=True)

        with NFSLock(self._lock_path, timeout=self.timeout):
            if _nfs_file_exists(self._done_file):
                log.info("CallOnce %r already complete", self.name)
                return

            if _nfs_file_exists(self._fail_file):
                try:
                    error_msg = self._fail_file.read_text()
                except OSError:
                    error_msg = "<unreadable>"
                raise RuntimeError(
                    f"Previous execution of {self.name!r} failed: {error_msg}"
                )

            log.info("Executing CallOnce %r in %s", self.name, self.path)
            try:
                self.fn()
                _create_marker(self._done_file)
                log.info("CallOnce %r complete", self.name)
            except Exception as e:
                _create_marker(self._fail_file, str(e))
                raise

    def clean(self) -> None:
        """Remove marker files to allow re-execution."""
        self._done_file.unlink(missing_ok=True)
        self._fail_file.unlink(missing_ok=True)
