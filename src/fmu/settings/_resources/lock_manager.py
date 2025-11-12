"""Manages a .lock file in a .fmu/ directory."""

from __future__ import annotations

import contextlib
import os
import socket
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, Self

from fmu.settings._logging import null_logger
from fmu.settings.models.lock_info import LockInfo

from .pydantic_resource_manager import PydanticResourceManager

if TYPE_CHECKING:
    from types import TracebackType

    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )

logger: Final = null_logger(__name__)

DEFAULT_LOCK_TIMEOUT: Final[int] = 1200  # 20 minutes


class LockError(Exception):
    """Raised when the lock cannot be acquired."""


class LockNotFoundError(FileNotFoundError):
    """Raised when the lock cannot be found."""


class LockManager(PydanticResourceManager[LockInfo]):
    """Manages the .lock file."""

    automatic_caching: bool = False

    def __init__(
        self: Self,
        fmu_dir: FMUDirectoryBase,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        """Initializes the lock manager.

        Args:
            fmu_dir: The FMUDirectory instance
            timeout_seconds: Lock expiration time in seconds (default 20 minutes)
        """
        super().__init__(fmu_dir, LockInfo)
        self._timeout_seconds = timeout_seconds
        self._acquired_at: float | None = None

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the .lock file."""
        return Path(".lock")

    def acquire(self: Self, wait: bool = False, wait_timeout: float = 5.0) -> None:
        """Acquire the lock.

        Args:
            wait: If true, wait for lock to become available
            wait_timeout: Maximum time to wait in seconds

        Raises:
            LockError: If lock cannot be acquired
        """
        if self._acquired_at is not None:
            raise LockError("Lock already acquired")

        if wait and wait_timeout <= 0:
            raise ValueError("wait_timeout must be positive")

        start_time = time.time()

        while True:
            if self.exists and self._is_stale():
                with contextlib.suppress(OSError):
                    self.path.unlink()

            if self._try_acquire():
                return

            if not wait:
                lock_info = self.safe_load()
                if lock_info:
                    raise LockError(
                        f"Lock file is held by {lock_info.user}@{lock_info.hostname} "
                        f"(PID: {lock_info.pid}). "
                        f"Expires at: {time.ctime(lock_info.expires_at)}."
                    )
                raise LockError(
                    f"Invalid lock file exists at {self.path}. "
                    "This file should be removed."
                )

            if time.time() - start_time > wait_timeout:
                raise LockError(f"Timeout waiting for lock after {wait_timeout}s")

            time.sleep(0.5)

    def _try_acquire(self: Self) -> bool:
        """Try to acquire lock. Returns True if successful.

        This method creates the lock as a temporary file first to avoid race conditions.
        Because we are operating on networked filesystems (NFS) the situation is a bit
        more complex, but os.link() is an atomic operation, so try to link the temp file
        after creating it.

        Returns:
            True if acquiring the lock succeeded
        """
        acquired_at = time.time()
        lock_info = LockInfo(
            pid=os.getpid(),
            hostname=socket.gethostname(),
            user=os.getenv("USER", "unknown"),
            acquired_at=acquired_at,
            expires_at=acquired_at + self._timeout_seconds,
        )

        temp_path = (
            self.path.parent
            / f".lock.{lock_info.hostname}.{lock_info.pid}.{uuid.uuid4().hex[:8]}"
        )
        lock_fd: int | None = None
        try:
            # O_WRONLY will allow only this process to write to the lock file.
            lock_fd = os.open(temp_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL)
            try:
                json_data = lock_info.model_dump_json(by_alias=True, indent=2)
                os.write(lock_fd, json_data.encode())
                os.fsync(lock_fd)
            except Exception:
                os.close(lock_fd)
                raise

            os.close(lock_fd)
            lock_fd = None

            try:
                os.link(temp_path, self.path)
                self._cache = lock_info
                self._acquired_at = acquired_at
                return True
            except (OSError, FileExistsError):
                return False
        finally:  # Clean up temp file before we leave
            if lock_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(lock_fd)
            with contextlib.suppress(OSError):
                temp_path.unlink()

    def is_locked(self: Self, *, propagate_errors: bool = False) -> bool:
        """Returns whether or not the lock is locked by anyone.

        This does a force load on the lock file.
        """
        lock_info = (
            self.load(force=True, store_cache=False)
            if propagate_errors
            else self.safe_load(force=True, store_cache=False)
        )
        if not lock_info:
            return False
        return time.time() < lock_info.expires_at

    def is_acquired(self: Self) -> bool:
        """Returns whether or not the lock is currently acquired by this instance."""
        if self._cache is None or self._acquired_at is None:
            return False

        current_lock = self.safe_load(force=True, store_cache=False)
        if current_lock is None:
            return False

        return self._is_mine(current_lock) and not self._is_stale()

    def ensure_can_write(self: Self) -> None:
        """Raise PermissionError if another process currently holds the lock."""
        lock_info = self.safe_load(force=True, store_cache=False)
        if (
            self.exists
            and lock_info is not None
            and not self.is_acquired()
            and not self._is_stale(lock_info=lock_info)
        ):
            raise PermissionError(
                "Cannot write to .fmu directory because it is locked by "
                f"{lock_info.user}@{lock_info.hostname} (PID: {lock_info.pid}). "
                f"Lock expires at {time.ctime(lock_info.expires_at)}."
            )

    def refresh(self: Self) -> None:
        """Refresh/extend the lock expiration time.

        Raises:
            LockError: If we don't hold the lock or it's invalid
        """
        if not self.exists:
            if self.is_acquired():
                self.release()
            raise LockNotFoundError("Cannot refresh: lock file does not exist")

        lock_info = self.safe_load()
        if not lock_info or not self._is_mine(lock_info):
            raise LockError(
                "Cannot refresh: lock file is held by another process or host."
            )

        lock_info.expires_at = time.time() + self._timeout_seconds
        self.save(lock_info)

    def release(self: Self) -> None:
        """Release the lock."""
        if self.exists:
            lock_info = self.safe_load()
            if lock_info and self._is_mine(lock_info):
                with contextlib.suppress(ValueError):
                    self.path.unlink()

        self._acquired_at = None
        self._cache = None

    def save(
        self: Self,
        data: LockInfo,
    ) -> None:
        """Save the lockfile in an NFS-atomic manner.

        This overrides save() from the Pydantic resource manager.
        """
        lock_info = self.safe_load()
        if not lock_info or not self._is_mine(lock_info):
            raise LockError(
                "Failed to save lock: lock file is held by another process or host."
            )

        temp_path = Path(f"{self.path}.tmp.{uuid.uuid4().hex[:8]}")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(data.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(self.path)
            self._cache = data
        except Exception as e:
            with contextlib.suppress(OSError):
                temp_path.unlink()
            raise LockError(f"Failed to save lock: {e}") from e

    def _is_mine(self: Self, lock_info: LockInfo) -> bool:
        """Verifies if the calling process owns the lock."""
        return (
            lock_info.pid == os.getpid()
            and lock_info.hostname == socket.gethostname()
            and lock_info.acquired_at == self._acquired_at
        )

    def safe_load(
        self: Self, force: bool = False, store_cache: bool = False
    ) -> LockInfo | None:
        """Load lock info, returning None if corrupted.

        Because this file does not exist in a static state, wrap around loading it.
        """
        try:
            return self.load(force=force, store_cache=store_cache)
        except Exception:
            return None

    def _is_stale(self: Self, lock_info: LockInfo | None = None) -> bool:
        """Check if existing lock is stale (expired or process dead)."""
        if lock_info is None:
            lock_info = self.safe_load()

        if not lock_info:
            return True

        if time.time() > lock_info.expires_at:
            return True

        # If we aren't on the same host, we can't check the PID, so assume it's
        # not stale.
        if lock_info.hostname != socket.gethostname():
            return False

        try:
            # Doesn't actually kill, just checks if it exists
            os.kill(lock_info.pid, 0)
            return False
        except OSError:
            return True

    def __enter__(self: Self) -> Self:
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(
        self: Self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Context manager exit."""
        self.release()
        return False

    def __del__(self: Self) -> None:
        """Clean-up if garbage collected."""
        if self._acquired_at is not None:
            self.release()
