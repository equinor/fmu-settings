from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Self

import pandas as pd
from pydantic import ValidationError

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
            df_log = pd.DataFrame([entry.model_dump() for entry in log_model])
            self._cached_dataframe = df_log
        df_log = self._cached_dataframe

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
                if filter.filter_type == FilterType.text:
                    raise ValueError(
                        f"Invalid filter operator <= applied to '{FilterType.text}' "
                        f"field {filter.field_name} when filtering log resource "
                        f"{self.model_class.__name__} with value {filter.filter_value}."
                    )
                filtered_df = df_log[
                    df_log[filter.field_name] <= filter.parse_filter_value()
                ]
            case ">=":
                if filter.filter_type == FilterType.text:
                    raise ValueError(
                        f"Invalid filter operator >= applied to '{FilterType.text}' "
                        f"field {filter.field_name} when filtering log resource "
                        f"{self.model_class.__name__} with value {filter.filter_value}."
                    )
                filtered_df = df_log[
                    df_log[filter.field_name] >= filter.parse_filter_value()
                ]
            case _:
                raise ValueError(
                    "Invalid filter operator applied when "
                    f"filtering log resource {self.model_class.__name__} "
                )

        filtered_dict = filtered_df.to_dict("records")
        return self.model_class.model_validate(filtered_dict)
