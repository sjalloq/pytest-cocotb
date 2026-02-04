# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

"""Tests for CallOnce guard with NFS-safe locking."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pytest_cocotb.guard import CallOnce, _nfs_file_exists


@pytest.fixture()
def build_dir(tmp_path: Path) -> Path:
    return tmp_path / "build"


class TestEnsureDone:
    def test_uses_nfs_lock(self, build_dir):
        """ensure_done should use NFSLock, not FileLock."""
        fn = MagicMock()
        guard = CallOnce(path=build_dir, name="test", fn=fn)

        with patch("pytest_cocotb.guard.NFSLock") as mock_lock_cls:
            mock_lock = MagicMock()
            mock_lock_cls.return_value = mock_lock
            mock_lock.__enter__ = MagicMock(return_value=mock_lock)
            mock_lock.__exit__ = MagicMock(return_value=False)
            guard.ensure_done()

            mock_lock_cls.assert_called_once_with(
                guard._lock_path, timeout=guard.timeout
            )

    def test_fn_called_once(self, build_dir):
        """Callable is only invoked on the first ensure_done call."""
        fn = MagicMock()
        guard = CallOnce(path=build_dir, name="test", fn=fn)

        guard.ensure_done()
        guard.ensure_done()

        fn.assert_called_once()

    def test_fsync_called_not_sync(self, build_dir):
        """os.fsync is used instead of os.sync for marker creation."""
        fn = MagicMock()
        guard = CallOnce(path=build_dir, name="test", fn=fn)

        with (
            patch("pytest_cocotb.guard.os.fsync") as mock_fsync,
            patch("pytest_cocotb.guard.os.open", wraps=__import__("os").open),
            patch(
                "pytest_cocotb.guard.os.sync",
                side_effect=AssertionError("os.sync must not be called"),
            ),
        ):
            guard.ensure_done()

        assert mock_fsync.call_count >= 2  # file fd + parent dir fd

    def test_failure_creates_fail_marker(self, build_dir):
        fn = MagicMock(side_effect=RuntimeError("compile error"))
        guard = CallOnce(path=build_dir, name="test", fn=fn)

        with pytest.raises(RuntimeError, match="compile error"):
            guard.ensure_done()

        assert guard._fail_file.exists()

    def test_previous_failure_raises(self, build_dir):
        """If a failure marker exists, ensure_done raises without re-running."""
        fn = MagicMock(side_effect=RuntimeError("first"))
        guard = CallOnce(path=build_dir, name="test", fn=fn)

        with pytest.raises(RuntimeError):
            guard.ensure_done()

        fn.reset_mock()
        with pytest.raises(RuntimeError, match="Previous execution"):
            guard.ensure_done()
        fn.assert_not_called()


class TestClean:
    def test_clean_removes_markers(self, build_dir):
        fn = MagicMock()
        guard = CallOnce(path=build_dir, name="test", fn=fn)
        guard.ensure_done()
        assert guard._done_file.exists()

        guard.clean()
        assert not guard._done_file.exists()


class TestNfsFileExists:
    def test_returns_true_for_existing_file(self, tmp_path):
        f = tmp_path / "marker"
        f.touch()
        assert _nfs_file_exists(f) is True

    def test_returns_false_for_missing_file(self, tmp_path):
        f = tmp_path / "no_such_file"
        assert _nfs_file_exists(f) is False

    def test_returns_false_for_missing_parent(self, tmp_path):
        f = tmp_path / "no_dir" / "file"
        assert _nfs_file_exists(f) is False
