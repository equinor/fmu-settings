from __future__ import annotations

import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models._enums import ChangeType, FilterType
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.diff import ListFieldDiff, ResourceDiff
from fmu.settings.models.log import Filter, Log, LogFileName

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        ProjectFMUDirectory,
    )


class ChangelogManager(LogManager[ChangeInfo]):
    """Manages the .fmu changelog file."""

    fmu_dir: ProjectFMUDirectory

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializes the Change log resource manager."""
        super().__init__(fmu_dir, Log[ChangeInfo])

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / LogFileName.changelog

    def log_update_to_changelog(
        self: Self,
        updates: dict[str, Any],
        relative_path: Path,
        *,
        structured_diff: list[ResourceDiff],
    ) -> None:
        """Logs the update of a resource to the changelog."""
        entries = self._group_diffs_by_update_key(updates, structured_diff)
        for key, diffs in entries.items():
            change_entry = ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=ChangeType.update,
                user=os.getenv("USER", "unknown"),
                path=self.fmu_dir.path,
                change=f"Updated field '{key}'.",
                structured_diff=diffs,
                hostname=socket.gethostname(),
                file=str(relative_path),
                key=key,
            )
            self.add_log_entry(change_entry)

    @staticmethod
    def _group_diffs_by_update_key(
        updates: dict[str, Any], diffs: list[ResourceDiff]
    ) -> dict[str, list[ResourceDiff]]:
        """Decide which changelog entry each change belongs to.

        One update can set several keys, for example ``model`` and ``model.name``.
        The changelog gets one entry for each key. This method puts each change
        from ``diffs`` into the entry of the key that it belongs to.

        How a change is placed:

        - It goes to the most specific key that contains it. A change to
          ``model.name`` goes to ``model.name`` if that key was updated.
          Otherwise, it goes to ``model``. Each change is placed only once.
        - If a whole section changed, the section gets one entry. For example,
          when ``rms`` is set for the first time, the updates to ``rms.path`` and
          ``rms.version`` are logged together as one ``rms`` entry.
        - If no key contains the change, the change gets its own entry.
        - A key with no changes is left out, so it is not logged. The value was
          saved, but it did not change.

        Examples:
            The examples show each change by its field path.

            Two keys where one is inside the other::

                updates: model, model.name
                changes: model.name, model.description
                entries: model      -> [model.description]
                         model.name -> [model.name]

            A section that is set for the first time::

                updates: rms.path, rms.version
                changes: rms
                entries: rms -> [rms]

            A value that is saved again without a change::

                updates: model.name
                changes: (none)
                entries: (none)
        """
        entries: dict[str, list[ResourceDiff]] = {key: [] for key in updates}
        for diff in diffs:
            # No item was added, removed or updated, e.g. the list was reordered.
            if isinstance(diff, ListFieldDiff) and not (
                diff.added or diff.removed or diff.updated
            ):
                continue

            changed_path = diff.field_path

            # If a whole section changed, keys inside it do not get their own entry.
            keys_inside_change = [
                key for key in entries if key.startswith(f"{changed_path}.")
            ]
            for key in keys_inside_change:
                del entries[key]

            # Use the most specific key that contains the change, else its own path.
            keys_containing_change = [
                key
                for key in entries
                if changed_path == key or changed_path.startswith(f"{key}.")
            ]
            entry_key = max(keys_containing_change, key=len, default=changed_path)
            entries.setdefault(entry_key, []).append(diff)
        return {key: key_diffs for key, key_diffs in entries.items() if key_diffs}

    def log_merge_to_changelog(
        self: Self, source_path: Path, incoming_path: Path, merged_resources: list[str]
    ) -> None:
        """Logs a change entry with merge details to the changelog."""
        resources_string = ", ".join([f"'{resource}'" for resource in merged_resources])
        change_string = (
            f"Merged resources {resources_string} from "
            f"'{incoming_path}' into '{source_path}'."
        )
        self.add_log_entry(
            ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=ChangeType.merge,
                user=os.getenv("USER", "unknown"),
                path=source_path,
                change=change_string,
                hostname=socket.gethostname(),
                file=resources_string,
                key=".fmu",
            )
        )

    def log_copy_revision_to_changelog(self: Self, source_path: Path) -> None:
        """Logs a change entry with revision copy details to the changelog."""
        self.add_log_entry(
            ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=ChangeType.copy,
                user=os.getenv("USER", "unknown"),
                path=source_path,
                change=f"Copied project revision from {source_path}.",
                hostname=socket.gethostname(),
                file="N/A",
                key="project_revision",
            )
        )

    def log_init_to_changelog(self: Self) -> None:
        """Logs a change entry indicating that the project was initialized."""
        self.add_log_entry(
            ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=ChangeType.init,
                user=os.getenv("USER", "unknown"),
                path=self.fmu_dir.path,
                change=f"Initialized .fmu directory at '{self.fmu_dir.path}'.",
                hostname=socket.gethostname(),
                file="N/A",
                key="project_initialization",
            )
        )

    def log_restore_to_changelog(self: Self, relative_path: Path, source: str) -> None:
        """Logs a change entry indicating that a resource was restored."""
        self.add_log_entry(
            ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=ChangeType.restore,
                user=os.getenv("USER", "unknown"),
                path=self.fmu_dir.path,
                change=f"Restored '{relative_path}' from {source}.",
                hostname=socket.gethostname(),
                file=str(relative_path),
                key=relative_path.stem,
            )
        )

    def _get_latest_change_timestamp(self: Self) -> datetime:
        """Get the timestamp of the latest change entry in the changelog."""
        return self.load()[-1].timestamp

    def get_changelog_diff(
        self: Self, incoming_changelog: ChangelogManager
    ) -> Log[ChangeInfo]:
        """Get new entries from the incoming changelog.

        All log entries from the incoming changelog newer than the
        log entries in the current changelog are returned.
        """
        if self.exists and incoming_changelog.exists:
            starting_point = self._get_latest_change_timestamp()
            return incoming_changelog.filter_log(
                Filter(
                    field_name="timestamp",
                    filter_value=str(starting_point),
                    filter_type=FilterType.date,
                    operator=">",
                )
            )
        raise FileNotFoundError(
            "Changelog resources to diff must exist in both directories: "
            f"Current changelog resource exists: {self.exists}. "
            f"Incoming changelog resource exists: {incoming_changelog.exists}."
        )

    def merge_changelog(
        self: Self, incoming_changelog: ChangelogManager
    ) -> Log[ChangeInfo]:
        """Add new entries from the incoming changelog to the current changelog.

        All log entries from the incoming changelog newer than the
        log entries in the current changelog are added.
        """
        new_log_entries = self.get_changelog_diff(incoming_changelog)
        return self.merge_changes(new_log_entries.root)

    def merge_changes(self: Self, change: list[ChangeInfo]) -> Log[ChangeInfo]:
        """Merge a list of changes into the current changelog.

        All log entries in the change object are added to the changelog.
        """
        for entry in change:
            self.add_log_entry(entry)
        return self.load()
