from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Generic, Self, get_args, get_origin

import pandas as pd
from pydantic import AwareDatetime, ValidationError

from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager
from fmu.settings.models._enums import FilterType
from fmu.settings.models.log import Filter, Log, LogEntryType

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class LogManager(PydanticResourceManager[Log[LogEntryType]], Generic[LogEntryType]):
    """Manages the .fmu log files."""

    automatic_caching: bool = False

    def __init__(
        self: Self, fmu_dir: FMUDirectoryBase, model_class: type[Log[LogEntryType]]
    ) -> None:
        """Initializes the log resource manager."""
        self._cached_dataframe: pd.DataFrame | None = None
        super().__init__(fmu_dir, model_class)

    def add_log_entry(self: Self, log_entry: LogEntryType) -> None:
        """Adds a log entry to the log resource."""
        try:
            validated_entry = log_entry.model_validate(log_entry.model_dump())
            log_model: Log[LogEntryType] = (
                self.load() if self.exists else self.model_class([])
            )
            log_model.add_entry(validated_entry)
            self.save(log_model)
            self._cached_dataframe = None
        except ValidationError as e:
            raise ValueError(
                f"Invalid log entry added to '{self.model_class.__name__}' with "
                f"value '{log_entry}': '{e}"
            ) from e

    def filter_log(self: Self, filter: Filter) -> Log[LogEntryType]:
        """Filters the log resource with the provided filter."""
        if self._cached_dataframe is None:
            log_model: Log[LogEntryType] = self.load()
            if len(log_model) == 0:
                self._cached_dataframe = pd.DataFrame()
                return self.model_class([])
            df_log = pd.DataFrame([entry.model_dump() for entry in log_model])
            self._cached_dataframe = df_log
        df_log = self._cached_dataframe
        if df_log.empty:
            return self.model_class([])

        self._validate_filter_field(filter)

        if filter.filter_type == FilterType.text and filter.operator not in {
            "==",
            "!=",
        }:
            raise ValueError(
                f"Invalid filter operator {filter.operator} applied to "
                f"'{FilterType.text}' field {filter.field_name} when filtering "
                f"log resource {self.model_class.__name__} "
                f"with value {filter.filter_value}."
            )

        match filter.operator:
            case "==":
                filtered_df = df_log[
                    df_log[filter.field_name] == filter.parse_filter_value()
                ]
            case "!=":
                filtered_df = df_log[
                    df_log[filter.field_name] != filter.parse_filter_value()
                ]
            case "<=":
                filtered_df = df_log[
                    df_log[filter.field_name] <= filter.parse_filter_value()
                ]
            case "<":
                filtered_df = df_log[
                    df_log[filter.field_name] < filter.parse_filter_value()
                ]
            case ">=":
                filtered_df = df_log[
                    df_log[filter.field_name] >= filter.parse_filter_value()
                ]
            case ">":
                filtered_df = df_log[
                    df_log[filter.field_name] > filter.parse_filter_value()
                ]
            case _:
                raise ValueError(
                    "Invalid filter operator applied when "
                    f"filtering log resource {self.model_class.__name__} "
                )

        filtered_dict = filtered_df.to_dict("records")
        return self.model_class.model_validate(filtered_dict)

    def _validate_filter_field(self: Self, filter: Filter) -> None:
        """Validate that the filter matches a field on the log entry model."""
        entry_model = self._entry_model_class()
        if filter.field_name not in entry_model.model_fields:
            raise ValueError(
                f"Invalid filter field '{filter.field_name}' when filtering "
                f"log resource {self.model_class.__name__}."
            )

        field = entry_model.model_fields[filter.field_name]
        expected_filter_type = self._filter_type_for_annotation(field.annotation)
        if expected_filter_type is None or filter.filter_type != expected_filter_type:
            raise ValueError(
                f"Invalid filter type '{filter.filter_type}' applied to field "
                f"'{filter.field_name}' when filtering log resource "
                f"{self.model_class.__name__}."
            )

    def _entry_model_class(self: Self) -> type[LogEntryType]:
        """Return the concrete Pydantic model used for log entries."""
        model_args = self.model_class.__pydantic_generic_metadata__["args"]
        return model_args[0]

    @staticmethod
    def _filter_type_for_annotation(annotation: object) -> FilterType | None:
        """Return the supported filter type for a model field annotation."""
        origin = get_origin(annotation)
        if origin is not None:
            annotation_args = [
                arg for arg in get_args(annotation) if arg is not type(None)
            ]
            if len(annotation_args) == 1:
                return LogManager._filter_type_for_annotation(annotation_args[0])

        if annotation in {datetime, AwareDatetime}:
            return FilterType.date
        if isinstance(annotation, type):
            if issubclass(annotation, str):
                return FilterType.text
            if issubclass(annotation, (int, float)) and not issubclass(
                annotation, bool
            ):
                return FilterType.number
            if issubclass(annotation, datetime):
                return FilterType.date
        return None
