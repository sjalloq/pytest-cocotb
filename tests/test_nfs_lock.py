# Copyright (c) 2026 Shareef Jalloq. MIT License — see LICENSE for details.

"""Tests for the NFS-safe mkdir-based lock."""

from __future__ import annotations

import json
import os
import threading
import time

import pytest

from pytest_cocotb.nfs_lock import NFSLock, NFSLockTimeout


@pytest.fixture()
def lock_path(tmp_path: object) -> object:
    return tmp_path / "test.lock"  # type: ignore[operator]


class TestAcquireRelease:
    def test_acquire_creates_dir(self, lock_path):
        lock = NFSLock(lock_path)
        lock.acquire()
        try:
            assert lock_path.is_dir()
        finally:
            lock.release()

    def test_release_removes_dir(self, lock_path):
        lock = NFSLock(lock_path)
        lock.acquire()
        lock.release()
        assert not lock_path.exists()

    def test_context_manager_releases_on_exit(self, lock_path):
        with NFSLock(lock_path):
            assert lock_path.is_dir()
        assert not lock_path.exists()

    def test_context_manager_releases_on_exception(self, lock_path):
        with pytest.raises(RuntimeError), NFSLock(lock_path):
            raise RuntimeError("boom")
        assert not lock_path.exists()


class TestHolderInfo:
    def test_holder_info_is_valid_json(self, lock_path):
        lock = NFSLock(lock_path)
        lock.acquire()
        try:
            info = json.loads((lock_path / "holder.info").read_text())
            assert "hostname" in info
            assert "pid" in info
            assert "timestamp" in info
            assert info["pid"] == os.getpid()
        finally:
            lock.release()


class TestBlocking:
    def test_second_acquire_blocks_until_release(self, lock_path):
        """A second thread blocks on acquire until the first releases."""
        barrier = threading.Event()
        acquired = threading.Event()

        def holder():
            with NFSLock(lock_path):
                barrier.set()
                time.sleep(0.3)

        def waiter():
            barrier.wait()
            lock = NFSLock(lock_path, poll_interval=0.05)
            lock.acquire()
            acquired.set()
            lock.release()

        t1 = threading.Thread(target=holder)
        t2 = threading.Thread(target=waiter)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert acquired.is_set()


class TestTimeout:
    def test_timeout_raises(self, lock_path):
        os.mkdir(lock_path)
        # Write holder info for current host but a different (alive) PID
        # so it's not considered stale.
        info = {
            "hostname": "some-other-host",
            "pid": 999999,
            "timestamp": time.time(),
        }
        holder = lock_path / "holder.info"
        holder.write_text(json.dumps(info))

        with pytest.raises(NFSLockTimeout):
            NFSLock(lock_path, timeout=0.2, poll_interval=0.05).acquire()


class TestStaleLock:
    def test_stale_lock_dead_pid_is_broken(self, lock_path):
        """A lock held by a dead local process is considered stale."""
        os.mkdir(lock_path)
        import socket

        info = {
            "hostname": socket.gethostname(),
            "pid": 2**22 - 1,  # almost certainly not running
            "timestamp": time.time(),
        }
        (lock_path / "holder.info").write_text(json.dumps(info))

        lock = NFSLock(lock_path, timeout=1.0, poll_interval=0.05)
        lock.acquire()
        try:
            assert lock_path.is_dir()
        finally:
            lock.release()

    def test_stale_lock_old_timestamp_is_broken(self, lock_path):
        """A lock with an expired timestamp from a remote host is stale."""
        os.mkdir(lock_path)
        info = {
            "hostname": "remote-host-that-does-not-exist",
            "pid": 12345,
            "timestamp": time.time() - 99999,
        }
        (lock_path / "holder.info").write_text(json.dumps(info))

        lock = NFSLock(lock_path, timeout=1.0, stale_timeout=100, poll_interval=0.05)
        lock.acquire()
        try:
            assert lock_path.is_dir()
        finally:
            lock.release()


class TestConcurrency:
    def test_n_threads_no_races(self, lock_path):
        """N concurrent threads each acquire/release without data races."""
        counter = {"value": 0}
        n_threads = 10
        iterations = 5

        def worker():
            for _ in range(iterations):
                with NFSLock(lock_path, poll_interval=0.01):
                    val = counter["value"]
                    time.sleep(0.001)
                    counter["value"] = val + 1

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert counter["value"] == n_threads * iterations
