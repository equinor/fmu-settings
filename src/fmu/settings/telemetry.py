"""Optional telemetry for FMU Settings applications."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from importlib import metadata
from typing import Any, Final
from uuid import uuid4

_TELEMETRY_ENTRY_POINT_GROUP: Final[str] = "fmu_settings"


def _telemetry_attribute(value: Any) -> str | bool | int | float:
    """Format structured values so telemetry backends can query them."""
    if isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return json.dumps(value, default=str, sort_keys=True)


class Telemetry:
    """Send explicit application events through an optional logging handler."""

    def __init__(
        self,
        *,
        app_name: str,
        app_version: str,
        environment: str | None,
        run_id: str,
        minimum_level: int,
        handler: logging.Handler | None,
    ) -> None:
        """Create telemetry with context shared by all emitted events."""
        self.run_id = run_id
        self._handler = handler
        self._logger = logging.getLogger(f"{app_name.replace('-', '_')}.azure")
        self._context = {
            "app_name": app_name,
            "app_version": app_version,
            "run_id": run_id,
        }
        if environment is not None:
            self._context["environment"] = environment

        if handler is not None:
            handler.setLevel(minimum_level)
            self._logger.addHandler(handler)
            self._logger.setLevel(minimum_level)
            self._logger.propagate = False

    def emit(
        self,
        event: str,
        *,
        level: int = logging.INFO,
        exc_info: Any = None,
        **attributes: Any,
    ) -> None:
        """Send one application event to the configured telemetry handler.

        Args:
            event: Name of the event, such as ``request_completed``.
            level: Python logging level for the event.
            exc_info: Exception information passed to the logging handler.
            **attributes: Event-specific values added as telemetry properties.
                Values that are not basic types are stored as JSON.

        Telemetry errors are ignored so they do not interrupt the application.
        """
        if self._handler is None or not self._logger.isEnabledFor(level):
            return

        try:
            properties = {
                "level": logging.getLevelName(level).lower(),
                **{
                    key: _telemetry_attribute(value)
                    for key, value in attributes.items()
                    if value is not None
                },
            }
            properties.update(self._context)
            self._logger.log(level, event, extra=properties, exc_info=exc_info)
        except Exception:
            return

    def shutdown(self) -> None:
        """Flush, remove, and close the optional telemetry handler."""
        if self._handler is None:
            return

        handler = self._handler
        self._handler = None
        try:
            force_flush = getattr(handler, "force_flush", None)
            if callable(force_flush):
                force_flush()
            else:
                handler.flush()
        except Exception as e:
            print(f"Unexpected telemetry shutdown error: {e}", file=sys.stderr)
        finally:
            self._logger.removeHandler(handler)
            try:
                handler.close()
            except Exception as e:
                print(f"Unexpected telemetry shutdown error: {e}", file=sys.stderr)


def configure_telemetry(
    *,
    app_name: str,
    app_version: str,
    environment: str | None = None,
    run_id: str | None = None,
    minimum_level: int = logging.INFO,
) -> Telemetry:
    """Configure optional telemetry for an FMU Settings application.

    The handler is loaded from the ``fmu_settings`` entry-point group. If no
    handler is available or setup fails, the returned telemetry object does
    nothing.

    Args:
        app_name: Name of the application that emits the events.
        app_version: Version of that application.
        environment: Optional runtime environment, such as a Komodo version.
        run_id: Identifier shared by events from one application run. A new
            UUID is created when this is not provided.
        minimum_level: Lowest Python logging level sent to the handler.

    Returns:
        A telemetry object that the application must shut down when it exits.
    """
    resolved_run_id = run_id or str(uuid4())
    try:
        entry_point = next(
            iter(metadata.entry_points(group=_TELEMETRY_ENTRY_POINT_GROUP)),
            None,
        )
    except Exception as e:
        print(f"Telemetry is disabled: {e}", file=sys.stderr)
        entry_point = None

    handler = None
    if entry_point is not None:
        try:
            handler = entry_point.load()()
        except Exception as e:
            print(f"Telemetry is disabled: {e}", file=sys.stderr)

    try:
        return Telemetry(
            app_name=app_name,
            app_version=app_version,
            environment=environment,
            run_id=resolved_run_id,
            minimum_level=minimum_level,
            handler=handler,
        )
    except Exception as e:
        print(f"Telemetry is disabled: {e}", file=sys.stderr)
        return Telemetry(
            app_name=app_name,
            app_version=app_version,
            environment=environment,
            run_id=resolved_run_id,
            minimum_level=minimum_level,
            handler=None,
        )
