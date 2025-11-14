"""Tests for UserSessionLogManager."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.cache_manager import CacheManager
from fmu.settings._resources.user_session_log_manager import UserSessionLogManager
from fmu.settings.models.event_info import EventInfo


def test_user_session_log_manager_creates_fresh_log(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that UserSessionLogManager starts with no existing log file."""
    manager = UserSessionLogManager(fmu_dir)
    assert not manager.exists
    assert manager.relative_path == Path("logs") / "user_session_log.json"


def test_user_session_log_manager_add_log_entry(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that UserSessionLogManager can add log entries."""
    manager = UserSessionLogManager(fmu_dir)
    event = EventInfo(level="INFO", event="test_event")
    manager.add_log_entry(event)

    assert manager.exists
    log_entries = manager.load()
    assert len(log_entries) == 1
    assert log_entries[0].event == "test_event"
    assert log_entries[0].level == "INFO"


def test_user_session_log_manager_archives_previous_session(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that previous session log is cached on initialization."""
    manager1 = UserSessionLogManager(fmu_dir)
    event1 = EventInfo(level="INFO", event="session1_event")
    manager1.add_log_entry(event1)
    assert manager1.exists

    manager2 = UserSessionLogManager(fmu_dir)
    assert not manager2.exists

    cache_path = fmu_dir.path / "cache" / "user_session_log"
    cached_files = list(cache_path.glob("*.json"))
    assert len(cached_files) == 1

    event2 = EventInfo(level="INFO", event="session2_event")
    manager2.add_log_entry(event2)
    log_entries = manager2.load()
    assert len(log_entries) == 1
    assert log_entries[0].event == "session2_event"


def test_user_session_log_manager_trims_old_cache_on_init(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that old cached logs are trimmed with default and custom retention."""
    cache_dir = fmu_dir.path / "cache" / "user_session_log"
    cache_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    very_old_time = now - timedelta(days=CacheManager.RETENTION_DAYS + 5)
    old_time = now - timedelta(days=15)
    recent_time = now - timedelta(days=5)

    very_old_filename = very_old_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-very_old.json"
    old_filename = old_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-old.json"
    recent_filename = recent_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-recent.json"

    very_old_file = cache_dir / very_old_filename
    old_file = cache_dir / old_filename
    recent_file = cache_dir / recent_filename
    very_old_file.write_text('{"entries": []}', encoding="utf-8")
    old_file.write_text('{"entries": []}', encoding="utf-8")
    recent_file.write_text('{"entries": []}', encoding="utf-8")

    very_old_mtime = very_old_time.timestamp()
    old_mtime = old_time.timestamp()
    recent_mtime = recent_time.timestamp()
    os.utime(very_old_file, (very_old_mtime, very_old_mtime))
    os.utime(old_file, (old_mtime, old_mtime))
    os.utime(recent_file, (recent_mtime, recent_mtime))

    UserSessionLogManager(fmu_dir)

    remaining_files = sorted(cache_dir.glob("*.json"), key=lambda p: p.name)
    assert len(remaining_files) == 2  # noqa: PLR2004
    assert remaining_files[0].name == old_filename
    assert remaining_files[1].name == recent_filename

    UserSessionLogManager(fmu_dir, retention_days=10)

    remaining_files = list(cache_dir.glob("*.json"))
    assert len(remaining_files) == 1
    assert remaining_files[0].name == recent_filename


def test_user_session_log_manager_skip_trim_on_store_revision(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that UserSessionLogManager uses skip_trim=True when storing revisions."""
    for i in range(10):
        manager = UserSessionLogManager(fmu_dir)
        event = EventInfo(level="INFO", event=f"session_{i}_event")
        manager.add_log_entry(event)

    cache_dir = fmu_dir.path / "cache" / "user_session_log"
    cached_files = list(cache_dir.glob("*.json"))
    assert len(cached_files) == 9  # noqa: PLR2004


def test_user_session_log_manager_multiple_entries_in_session(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests handling multiple log entries in one session."""
    manager = UserSessionLogManager(fmu_dir)

    events = [
        EventInfo(level="INFO", event="event1"),
        EventInfo(level="WARNING", event="event2"),
        EventInfo(level="ERROR", event="event3"),
    ]

    for event in events:
        manager.add_log_entry(event)

    log_entries = manager.load()
    assert len(log_entries) == 3  # noqa: PLR2004
    assert [entry.event for entry in log_entries] == ["event1", "event2", "event3"]
    assert [entry.level for entry in log_entries] == ["INFO", "WARNING", "ERROR"]
