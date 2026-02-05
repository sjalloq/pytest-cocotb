NFS locking and xdist support
=============================

When running tests in parallel with pytest-xdist on a shared NFS filesystem,
multiple workers may attempt to compile HDL simultaneously.  pytest-cocotb
provides NFS-safe locking primitives and a call-once guard to ensure the build
step executes exactly once.

Why NFS locking?
----------------

Standard POSIX file locks (``fcntl.flock()``) are unreliable on many NFS
configurations — they may be local-only, meaning a lock acquired on one node
is invisible to other nodes.  pytest-cocotb uses ``os.mkdir()`` as its atomic
primitive, which is guaranteed to be atomic across all NFS versions: the call
either succeeds or raises ``FileExistsError``.

NFSLock
-------

``NFSLock`` is a cross-node lock backed by ``mkdir``/``rmdir``.  It can be
used as a context manager:

.. code-block:: python

   from pytest_cocotb.nfs_lock import NFSLock

   with NFSLock("/shared/path/.build.lock", timeout=600):
       # critical section — only one process at a time
       run_build()

**Lock directory contents:**

When acquired, the lock directory contains a ``holder.info`` file with JSON
recording the holder's hostname, PID, and timestamp.  This enables stale lock
detection.

**Stale lock detection:**

- **Same host:** If the holding process is no longer alive (checked via
  ``os.kill(pid, 0)``), the lock is considered stale and is broken.
- **Different host:** If the lock age exceeds ``stale_timeout`` (default:
  2 hours), it is considered stale and is broken.

**Parameters:**

- ``lock_path`` — Directory path used as the lock.
- ``timeout`` — Maximum seconds to wait (default: 3600). ``-1`` means wait
  forever.
- ``poll_interval`` — Seconds between acquisition attempts (default: 0.1).
- ``stale_timeout`` — Seconds after which a remote lock is considered stale
  (default: 7200).

CallOnce
--------

``CallOnce`` ensures a callable is executed exactly once across multiple
processes.  It combines an ``NFSLock`` with completion and failure marker
files:

.. code-block:: python

   from pytest_cocotb.guard import CallOnce

   guard = CallOnce(
       path=build_dir,
       name="hdl_compile",
       fn=lambda: runner.build(...),
   )
   guard.ensure_done()

**How it works:**

1. Acquires the NFS lock.
2. Checks for a ``.done`` marker — if present, returns immediately.
3. Checks for a ``.failed`` marker — if present, raises ``RuntimeError``
   with the stored error message.
4. Executes the callable.
5. On success, creates the ``.done`` marker.
6. On failure, creates the ``.failed`` marker with the error message, then
   re-raises.

All marker files are written with ``fsync`` on both the file and its parent
directory to ensure visibility across NFS clients.

**Parameters:**

- ``path`` — Base directory for lock and marker files.
- ``name`` — Identifier used for the lock and marker filenames.
- ``fn`` — The callable to execute.
- ``timeout`` — Lock acquisition timeout (default: 3600).

The ``clean()`` method removes marker files to allow re-execution.

Plugin integration
------------------

The ``NFSLock`` and ``CallOnce`` primitives are available infrastructure for
future pytest-xdist integration, where the ``runner`` fixture would use
``CallOnce`` to ensure the HDL build happens exactly once even with multiple
xdist workers.

API reference
-------------

.. autoclass:: pytest_cocotb.nfs_lock.NFSLock
   :members:

.. autoexception:: pytest_cocotb.nfs_lock.NFSLockTimeout

.. autoclass:: pytest_cocotb.guard.CallOnce
   :members:
