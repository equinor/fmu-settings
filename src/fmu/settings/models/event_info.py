"""Model for the log entries in the the userlog file."""

from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EventInfo(BaseModel):
    """Represents information about user session activity."""

    model_config = ConfigDict(extra="allow")

    level: str = "INFO"
    event: str = "unknown"
    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
