"""Tests for LockManager."""

import json
import multiprocessing
import multiprocessing.queues
import os
import socket
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.lock_manager import (
    DEFAULT_LOCK_TIMEOUT,
    LockError,
    LockManager,
    LockNotFoundError,
)
from fmu.settings.models.lock_info import LockInfo


def test_lock_manager_instantiation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests basic facts about the LockManager."""
    lock = LockManager(fmu_dir)

    assert lock.fmu_dir == fmu_dir
    assert lock.model_class == LockInfo
    assert lock._cache is None
    assert lock._timeout_seconds == DEFAULT_LOCK_TIMEOUT
    assert lock._acquired_at is None

    # Resource manager requires this to be implemented
    assert lock.relative_path == Path(".lock")
    assert lock.path == fmu_dir.path / lock.relative_path


def test_lock_acquire_creates_lock_file(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that acquiring a lock creates a correct lock file."""
    monkeypatch.setenv("USER", "user")

    lock = LockManager(fmu_dir)

    assert lock.exists is False
    with pytest.raises(
        FileNotFoundError, match="Resource file for 'LockManager' not found"
    ):
        lock.load()

    lock.acquire()
    assert lock.exists
    assert lock._acquired_at is not None

    lock_info = lock.load()
    assert lock._cache == lock_info
    assert lock._acquired_at == lock_info.acquired_at
    assert lock_info.pid == os.getpid()
    assert lock_info.hostname == socket.gethostname()
    assert lock_info.user == "user"
    assert lock_info.expires_at == pytest.approx(
        lock_info.acquired_at + DEFAULT_LOCK_TIMEOUT, rel=1e-05
    )


def test_lock_as_context_manager(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that acquiring a ctx manager lock creates a correct lock file."""
    monkeypatch.setenv("USER", "user")

    with LockManager(fmu_dir) as lock:
        assert lock.exists
        assert lock._acquired_at is not None

        lock_info = lock.load()
        assert lock._cache == lock_info
        assert lock._acquired_at == lock_info.acquired_at
        assert lock_info.pid == os.getpid()
        assert lock_info.hostname == socket.gethostname()
        assert lock_info.user == "user"
        assert lock_info.expires_at == pytest.approx(
            lock_info.acquired_at + DEFAULT_LOCK_TIMEOUT, rel=1e-05
        )

    assert (fmu_dir.path / ".lock").exists() is False


def test_lock_acquire_raises_if_already_acquired(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that a lock cannot be acquired twice."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    assert lock.is_locked()
    assert lock.is_acquired()
    with pytest.raises(LockError, match="Lock already acquired"):
        lock.acquire()


@pytest.mark.xfail(reason="Lock is not race consistent yet")
def test_lock_acquire_race_in_threads(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that under thread race conditions one lock succeeds, one fails."""
    results = []
    errors = []

    def acquire_lock() -> None:
        """Creates, acquires, and releases a lock."""
        try:
            lock = LockManager(fmu_dir)
            lock.acquire()
            results.append("success")
        except LockError as e:
            errors.append(e)

    thread1 = threading.Thread(target=acquire_lock)
    thread2 = threading.Thread(target=acquire_lock)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    assert len(results) == 1
    assert len(errors) == 1


def _acquire_lock(
    fmu_dir: ProjectFMUDirectory,
    result_queue: multiprocessing.queues.Queue,  # type: ignore
) -> None:
    """Creates, acquires, and releases a lock.

    This is at the module level so it can be pickled by the process test.
    """
    try:
        lock = LockManager(fmu_dir)
        lock.acquire()
        result_queue.put(("success", None))
    except LockError as e:
        result_queue.put(("error", str(e)))


@pytest.mark.xfail(reason="Lock is not race consistent yet")
def test_lock_acquire_race_in_processes(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that under same process race conditions, one lock succeeds, one fails."""
    # See https://github.com/python/cpython/issues/99509 for type ignore
    result_queue = multiprocessing.Queue()  # type: ignore
    process1 = multiprocessing.Process(
        target=_acquire_lock, args=(fmu_dir, result_queue)
    )
    process2 = multiprocessing.Process(
        target=_acquire_lock, args=(fmu_dir, result_queue)
    )

    process1.start()
    process2.start()
    process1.join()
    process2.join()

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(successes) == 1
    assert len(errors) == 1


def test_lock_acquire_raises_if_invalid_wait_period(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that a lock acquire requires a positive timeout."""
    lock = LockManager(fmu_dir)
    with pytest.raises(ValueError, match="wait_timeout must be positive"):
        lock.acquire(wait=True, wait_timeout=-1)
    lock.acquire(wait=True, wait_timeout=0.01)


def test_lock_acquire_over_expired_lock(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that a stale lock file will be unlinked and overwritten."""
    stale_lock = LockManager(fmu_dir, timeout_seconds=-1)  # Expired
    stale_lock.acquire()
    assert stale_lock.is_locked() is False
    assert stale_lock.is_acquired() is False
    assert stale_lock._is_stale() is True
    stale_lock_info = stale_lock.load()

    lock = LockManager(fmu_dir)
    lock.acquire()
    lock_info = lock.load()

    assert lock.is_locked()
    assert lock.is_acquired()
    assert stale_lock.path == lock.path
    assert lock_info != stale_lock_info


def test_no_wait_invalid_lock_file_exists(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that an existing, invalid .lock file raises.

    This should not really occur, but it's theoretically possible the lock file is
    overwritten to an invalid state between its stale check.
    """
    fmu_dir.write_text_file(".lock", "")
    lock = LockManager(fmu_dir)

    # This shouldn't be possible, but test that it's caught anyway
    with (
        patch.object(lock, "_is_stale", return_value=False),
        pytest.raises(LockError, match="Invalid lock file exists"),
    ):
        lock.acquire()


def test_lock_acquire_when_fresh_lock_exists_without_timeout(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that trying to acquire a fresh lock without timeout fails."""
    monkeypatch.setenv("USER", "user")

    lock = LockManager(fmu_dir)
    lock.acquire()

    bad_lock = LockManager(fmu_dir)
    with pytest.raises(LockError, match="Lock file is held by user@"):
        bad_lock.acquire()


def test_lock_with_wait_timeout_raises_after_timeout(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that trying to acquire a fresh lock with timeout succeeds."""
    lock = LockManager(fmu_dir)
    lock.acquire()

    wait_lock = LockManager(fmu_dir)
    with pytest.raises(LockError, match="Timeout waiting for lock"):
        wait_lock.acquire(wait=True, wait_timeout=0.25)


def test_lock_with_wait_timeout_succeeds_after_release(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that trying to acquire a fresh lock with timeout succeeds."""
    lock = LockManager(fmu_dir)
    lock.acquire()

    def try_acquire_second_lock() -> LockManager:
        wait_lock = LockManager(fmu_dir)
        wait_lock.acquire(wait=True, wait_timeout=1.0)
        return wait_lock

    thread = threading.Thread(target=try_acquire_second_lock)
    thread.start()

    time.sleep(0.15)
    lock.release()
    thread.join()
    assert not thread.is_alive()


def test_is_stale_expired(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests is_stale if lock has expired."""
    lock = LockManager(fmu_dir, timeout_seconds=-1)  # Expired
    lock.acquire()
    assert lock._is_stale() is True


def test_is_stale_not_expired(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests is_stale if lock has not expired."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    assert lock._is_stale() is False


def test_is_stale_load_fails(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests is_stale if loading the lock file fails."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    with patch.object(lock, "safe_load", return_value=None):
        assert lock._is_stale() is True


def test_is_stale_bad_hostname(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests is_stale if lock check occurs from different host."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    assert lock._is_stale() is False
    with patch(
        "fmu.settings._resources.lock_manager.socket.gethostname", return_value="foo"
    ):
        assert lock._is_stale() is False


def test_is_stale_invalid_pid(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests helper method check if lock pid does not exist."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    assert lock._is_stale() is False
    assert lock._cache is not None
    lock._cache.pid = 99999999  # Should be an impossible pid
    assert lock._is_stale() is True


def test_try_acquire_succeeds_as_expected(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that try_acquire creates a correct lock file."""
    monkeypatch.setenv("USER", "user")
    time_time = 1234.5
    temp_uuid = uuid.uuid4()
    lock = LockManager(fmu_dir)
    with (
        patch("time.time", return_value=time_time),
        patch("os.getpid", return_value=123),
        patch("socket.gethostname", return_value="foo"),
        patch("pathlib.Path.unlink") as mock_unlink,
        patch("uuid.uuid4", return_value=temp_uuid),
    ):
        assert lock._try_acquire() is True
        assert lock._acquired_at == time_time
        assert lock._cache == LockInfo(
            pid=123,
            hostname="foo",
            user="user",
            acquired_at=time_time,
            expires_at=time_time + DEFAULT_LOCK_TIMEOUT,
        )
        mock_unlink.assert_called_once()

    lock_info = lock._cache
    assert lock_info is not None
    temp_lockfile = (
        fmu_dir.path / f".lock.{lock_info.hostname}.{lock_info.pid}.{temp_uuid.hex[:8]}"
    )
    # We mocked unlink(), so the temporary lockfile should still exist.
    assert temp_lockfile.exists()
    assert LockInfo.model_validate(json.loads(temp_lockfile.read_text())) == lock_info

    assert lock.path.exists()
    assert LockInfo.model_validate(json.loads(lock.path.read_text())) == lock_info


def test_try_acquire_fails_when_writing_temp_file(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that try_acquire raises when failing to write the lock file.."""
    lock = LockManager(fmu_dir)
    with (
        patch("os.write", side_effect=OSError("oops")),
        patch("os.close") as mock_close,
        patch("pathlib.Path.unlink") as mock_unlink,
        pytest.raises(OSError, match="oops"),
    ):
        lock._try_acquire()
        mock_close.assert_called_twice()
        mock_unlink.assert_called_once()


def test_try_acquire_fails_when_linking_temp_file(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that try_acquire raises when failing to link the lock file.."""
    lock = LockManager(fmu_dir)
    with (
        patch("os.link") as mock_link,
        patch("os.close", side_effect=FileExistsError) as mock_close,
        patch("pathlib.Path.unlink") as mock_unlink,
        pytest.raises(FileExistsError),
    ):
        assert lock._try_acquire() is False
        mock_link.assert_called_once_with(lock.path)
        mock_close.assert_called_twice()
        mock_unlink.assert_called_once()


def test_is_locked_expected(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests is_locked under expected, simple conditions."""
    lock = LockManager(fmu_dir)
    assert lock.is_locked() is False
    lock.acquire()
    assert lock.is_locked() is True
    lock.release()
    assert lock.is_locked() is False


def test_is_locked_by_other_process(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests is_locked when another process has the lock."""
    lock = LockManager(fmu_dir)
    assert lock.is_locked() is False
    with patch("os.getpid", return_value=-1234):
        lock.acquire()

    assert lock.is_locked() is True

    with patch("os.getpid", return_value=-1234):
        lock.release()
    assert lock.is_locked() is False


def test_is_locked_propagate_errors(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that load with propagate errors raises."""
    lock = LockManager(fmu_dir)
    lock.path.write_text("a")
    assert lock.is_locked() is False

    with pytest.raises(ValueError, match="Invalid JSON"):
        assert lock.is_locked(propagate_errors=True) is False


def test_is_acquired_expected(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests is_acquired under expected conditions."""
    lock = LockManager(fmu_dir)
    assert lock.is_acquired() is False
    lock.acquire()
    assert lock.is_acquired() is True


def test_is_acquired_unexpected_members(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests is_acquired under expected member conditions."""
    lock = LockManager(fmu_dir)
    assert lock.is_acquired() is False
    lock.acquire()
    assert lock.is_acquired() is True
    lock_info = lock._cache
    lock._cache = None
    assert lock.is_acquired() is False
    lock._cache = lock_info
    lock._acquired_at = None
    assert lock.is_acquired() is False


@pytest.mark.parametrize(
    "is_mine, is_stale, expected",
    [
        (True, True, False),
        (True, False, True),
        (False, True, False),
        (False, False, False),
    ],
)
def test_is_acquired_unexpected_methods(
    fmu_dir: ProjectFMUDirectory,
    monkeypatch: MonkeyPatch,
    is_mine: bool,
    is_stale: bool,
    expected: bool,
) -> None:
    """Tests is_acquired under expected method conditions."""
    lock = LockManager(fmu_dir)
    assert lock.is_acquired() is False
    lock.acquire()

    with (
        patch.object(lock, "_is_mine", return_value=is_mine),
        patch.object(lock, "_is_stale", return_value=is_stale),
    ):
        assert lock.is_acquired() is expected


def test_refresh_works_as_expected(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests refresh works as expected."""
    lock = LockManager(fmu_dir)

    start_time = 1234.5
    refresh_time = 2345.6
    with patch("time.time", return_value=start_time):
        lock.acquire()
    assert lock._cache is not None
    assert lock._cache.expires_at == start_time + DEFAULT_LOCK_TIMEOUT

    with patch("time.time", return_value=refresh_time):
        lock.refresh()
    assert lock._acquired_at == start_time
    assert lock._cache.expires_at == refresh_time + DEFAULT_LOCK_TIMEOUT

    lock_info = LockInfo.model_validate(json.loads(lock.path.read_text()))
    assert lock_info.expires_at == refresh_time + DEFAULT_LOCK_TIMEOUT


def test_refresh_without_lock_file(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests that if a user deletes anothers lock it's invalidated on a refresh."""
    with pytest.raises(LockNotFoundError, match="does not exist"):
        fmu_dir._lock.refresh()

    fmu_dir._lock.acquire()
    assert fmu_dir._lock.is_acquired() is True

    # Someone deletes the lock
    fmu_dir._lock.path.unlink()

    with pytest.raises(
        LockNotFoundError, match="Cannot refresh: lock file does not exist"
    ):
        fmu_dir._lock.refresh()
    assert fmu_dir._lock.is_acquired() is False


def test_refresh_missing_lock_releases_owned_lock(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests refresh releases cached state when lock file is missing."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    lock.path.unlink()

    with (
        patch.object(lock, "is_acquired", return_value=True),
        patch.object(lock, "release") as mock_release,
        pytest.raises(LockNotFoundError, match="lock file does not exist"),
    ):
        lock.refresh()

    mock_release.assert_called_once()


def test_refresh_without_owning_lock(
    fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch
) -> None:
    """Tests refresh when lock file is not owned by the process."""
    lock = LockManager(fmu_dir)
    with patch("os.getpid", return_value=-1234):
        lock.acquire()
    with pytest.raises(LockError, match="held by another process"):
        lock.refresh()


def test_lock_release_unlinks_lock_file(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that releasing a lock removes the lock file."""
    lock = LockManager(fmu_dir)

    assert lock.exists is False
    lock.acquire()
    assert lock.exists
    lock.release()
    assert lock.exists is False
    assert lock._cache is None
    assert lock.path.exists() is False


def test_safe_load(fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch) -> None:
    """Tests the safe load helper method."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    assert lock._cache is not None
    assert lock.safe_load() == lock._cache

    lock.release()
    lock.path.write_text("a")
    assert lock.safe_load() is None


def test_save_expected(fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch) -> None:
    """Tests that save works as expected."""
    lock = LockManager(fmu_dir)
    lock.acquire()

    lock_info = lock.load()
    new_expires_at = 123.4
    lock_info.expires_at = new_expires_at

    temp_uuid = uuid.uuid4()
    with patch("uuid.uuid4", return_value=temp_uuid):
        lock.save(lock_info)

    lock_info = lock.load()
    assert lock_info.expires_at == new_expires_at
    assert Path(f"{lock.path}.tmp.{temp_uuid.hex[:8]}").exists() is False
    assert LockInfo.model_validate(json.loads(lock.path.read_text())) == lock_info


def test_save_raises(fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch) -> None:
    """Tests that save fails as expected under failing conditions."""
    lock = LockManager(fmu_dir)
    lock.acquire()

    lock_info = lock.load()
    with (
        patch("pathlib.Path.replace", side_effect=OSError("oops")) as mock_replace,
        pytest.raises(LockError, match="oops"),
    ):
        lock.save(lock_info)
        mock_replace.assert_called_once_with(lock.path)


def test_save_not_owned(fmu_dir: ProjectFMUDirectory, monkeypatch: MonkeyPatch) -> None:
    """Tests that save fails when lock is not owned by process."""
    lock = LockManager(fmu_dir)
    lock.acquire()

    lock_info = lock.load()
    with (
        patch.object(lock, "_is_mine", return_value=False),
        pytest.raises(LockError, match="lock file is held by another"),
    ):
        lock.save(lock_info)


def test_ensure_can_write_no_lock(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests ensure_can_write when no lock exists."""
    lock = LockManager(fmu_dir)
    assert lock.exists is False
    lock.ensure_can_write()


def test_ensure_can_write_invalid_lock(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests ensure_can_write ignores unreadable lock info."""
    lock = LockManager(fmu_dir)
    lock.path.write_text("garbage")
    with patch.object(lock, "safe_load", return_value=None):
        lock.ensure_can_write()


def test_ensure_can_write_owned_lock(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests ensure_can_write passes when lock is owned by caller."""
    lock = LockManager(fmu_dir)
    lock.acquire()
    lock.ensure_can_write()
    lock.release()


def test_ensure_can_write_stale_lock(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests ensure_can_write ignores stale locks."""
    lock = LockManager(fmu_dir)
    future = time.time() + 10
    lock_info = LockInfo(
        pid=123,
        hostname="host",
        user="user",
        acquired_at=future - 100,
        expires_at=future,
    )
    lock.path.write_text(lock_info.model_dump_json(indent=2))
    with (
        patch.object(lock, "safe_load", return_value=lock_info),
        patch.object(lock, "is_acquired", return_value=False),
        patch.object(lock, "_is_stale", return_value=True),
    ):
        lock.ensure_can_write()


def test_ensure_can_write_foreign_lock(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests ensure_can_write raises on active locks owned by others."""
    lock = LockManager(fmu_dir)
    now = time.time()
    lock_info = LockInfo(
        pid=123,
        hostname="remote",
        user="user",
        acquired_at=now,
        expires_at=now + DEFAULT_LOCK_TIMEOUT,
    )
    lock.path.write_text(lock_info.model_dump_json(indent=2))
    with (
        patch(
            "fmu.settings._resources.lock_manager.socket.gethostname",
            return_value="current-host",
        ),
        pytest.raises(PermissionError, match="Cannot write to .fmu directory"),
    ):
        lock.ensure_can_write()
