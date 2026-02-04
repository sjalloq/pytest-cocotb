# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

"""NFS-safe locking using mkdir atomicity.

``os.mkdir()`` is atomic on all NFS versions — it either succeeds or raises
``FileExistsError``.  This avoids the unreliable ``fcntl.flock()`` behaviour
that many NFS configurations exhibit (flock may be local-only).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import socket
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class NFSLockTimeout(TimeoutError):
    """Raised when the lock cannot be acquired within the timeout."""


class NFSLock:
    """A cross-node lock backed by ``mkdir``/``rmdir``.

    Parameters
    ----------
    lock_path:
        Directory path used as the lock.  The directory is created on acquire
        and removed on release.
    timeout:
        Maximum seconds to wait for the lock.  ``-1`` means wait forever.
    poll_interval:
        Seconds between acquisition attempts.
    stale_timeout:
        Seconds after which a lock held by an unreachable host is considered
        stale and may be broken.
    """

    def __init__(
        self,
        lock_path: str | Path,
        timeout: float = 3600.0,
        poll_interval: float = 0.1,
        stale_timeout: float = 7200.0,
    ) -> None:
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.stale_timeout = stale_timeout

    @property
    def _holder_file(self) -> Path:
        return self.lock_path / "holder.info"

    # ------------------------------------------------------------------
    # Context-manager interface
    # ------------------------------------------------------------------

    def __enter__(self) -> NFSLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Acquire / release
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Block until the lock directory is created (= lock acquired)."""
        deadline = None if self.timeout < 0 else time.monotonic() + self.timeout

        while True:
            try:
                os.mkdir(self.lock_path)
            except FileExistsError:
                if self._try_break_stale():
                    continue  # stale lock broken — retry mkdir immediately
                if deadline is not None and time.monotonic() >= deadline:
                    raise NFSLockTimeout(
                        f"Could not acquire lock {self.lock_path} "
                        f"within {self.timeout}s"
                    ) from None
                time.sleep(self.poll_interval)
            else:
                break

        self._write_holder_info()
        log.debug("Acquired lock %s", self.lock_path)

    def release(self) -> None:
        """Remove sentinel files and the lock directory."""
        with contextlib.suppress(OSError):
            self._holder_file.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            os.rmdir(self.lock_path)
        log.debug("Released lock %s", self.lock_path)

    # ------------------------------------------------------------------
    # Holder info & staleness
    # ------------------------------------------------------------------

    def _write_holder_info(self) -> None:
        info = {
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
            "timestamp": time.time(),
        }
        # Write via low-level fd so we can fsync.
        fd = os.open(
            str(self._holder_file),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            os.write(fd, json.dumps(info).encode())
            os.fsync(fd)
        finally:
            os.close(fd)

    def _read_holder_info(self) -> dict[str, Any] | None:
        try:
            result: dict[str, Any] = json.loads(self._holder_file.read_text())
            return result
        except (OSError, json.JSONDecodeError):
            return None

    def _try_break_stale(self) -> bool:
        """Return True if a stale lock was successfully broken."""
        info = self._read_holder_info()
        if info is None:
            return False

        if not self._is_stale(info):
            return False

        log.info(
            "Breaking stale lock %s (holder: %s pid %s)",
            self.lock_path,
            info.get("hostname"),
            info.get("pid"),
        )
        with contextlib.suppress(OSError):
            self._holder_file.unlink(missing_ok=True)
        try:
            os.rmdir(self.lock_path)
        except OSError:
            return False
        return True

    def _is_stale(self, info: dict[str, Any]) -> bool:
        hostname = info.get("hostname", "")
        pid = info.get("pid", -1)
        timestamp = info.get("timestamp", 0.0)

        if hostname == socket.gethostname():
            # Same host — check if the process is alive.
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                # Process exists but we can't signal it.
                return False
            return False

        # Different host — fall back to time-based expiry.
        age = time.time() - float(timestamp)
        return bool(age > self.stale_timeout)
