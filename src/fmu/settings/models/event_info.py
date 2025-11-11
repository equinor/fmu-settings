"""Model for the log entries in the the eventlog file."""

from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EventInfo(BaseModel):
    """Log entry model for fmu-settings LogManager."""

    model_config = ConfigDict(extra="allow")

    level: str = "INFO"
    event: str = "unknown"
    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
