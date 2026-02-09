"""Diff models shared by resource managers and API consumers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ScalarFieldDiff(BaseModel):
    """Diff entry for non-list fields."""

    field_path: str
    before: Any
    after: Any


class ListUpdatedEntry(BaseModel):
    """Before and after values for an updated list item."""

    key: Any
    before: dict[str, Any]
    after: dict[str, Any]


class ListFieldDiff(BaseModel):
    """Diff entry for list fields with per-item changes."""

    field_path: str
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    updated: list[ListUpdatedEntry]


ResourceDiff = ScalarFieldDiff | ListFieldDiff
