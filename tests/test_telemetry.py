"""Tests for optional application telemetry."""

import logging
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from fmu.settings.telemetry import Telemetry, configure_telemetry


class RecordingHandler(logging.Handler):
    """Store records and lifecycle calls for telemetry tests."""

    def __init__(self) -> None:
        """Create an empty recording handler."""
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.force_flush_calls = 0
        self.close_calls = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Store one emitted record."""
        self.records.append(record)

    def force_flush(self) -> None:
        """Record a forced flush."""
        self.force_flush_calls += 1

    def close(self) -> None:
        """Record close calls."""
        self.close_calls += 1
        super().close()


def _configure_telemetry_with_handler(
    handler: logging.Handler, minimum_level: int = logging.INFO
) -> Telemetry:
    """Configure telemetry with one mocked site plugin."""
    entry_point = Mock()
    entry_point.load.return_value.return_value = handler
    with patch(
        "fmu.settings.telemetry.metadata.entry_points", return_value=[entry_point]
    ):
        return configure_telemetry(
            app_name="fmu-settings-api",
            app_version="1.2.3",
            environment="development",
            run_id="run-123",
            minimum_level=minimum_level,
        )


def test_configure_telemetry_without_plugin_returns_noop() -> None:
    """A missing site plugin returns telemetry that safely accepts events."""
    with patch("fmu.settings.telemetry.metadata.entry_points", return_value=[]):
        telemetry = configure_telemetry(
            app_name="fmu-settings-api",
            app_version="1.2.3",
        )

    telemetry.emit("request_completed")

    assert telemetry.run_id


def test_configure_telemetry_plugin_load_failure_returns_noop(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A plugin load failure is reported and returns a no-op."""
    entry_point = Mock()
    entry_point.load.side_effect = RuntimeError("setup failed")
    with patch(
        "fmu.settings.telemetry.metadata.entry_points", return_value=[entry_point]
    ):
        telemetry = configure_telemetry(
            app_name="fmu-settings-api",
            app_version="1.2.3",
        )

    telemetry.emit("request_completed")

    assert "Telemetry is disabled: setup failed" in capsys.readouterr().err


def test_configure_telemetry_entry_point_discovery_failure_returns_noop(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A discovery failure is reported and returns a no-op."""
    with patch(
        "fmu.settings.telemetry.metadata.entry_points",
        side_effect=RuntimeError("discovery failed"),
    ):
        telemetry = configure_telemetry(
            app_name="fmu-settings-api",
            app_version="1.2.3",
        )

    telemetry.emit("request_completed")

    assert "Telemetry is disabled: discovery failed" in capsys.readouterr().err


def test_emit_adds_context_and_formats_attributes() -> None:
    """Add shared context, format structured values, and omit `None` values."""
    handler = RecordingHandler()
    telemetry = _configure_telemetry_with_handler(handler)

    telemetry.emit(
        "request_completed",
        path="/api/v1/project",
        status_code=200,
        details={"resources": ["config", "access"]},
        occurred_at=datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
        optional=None,
    )

    assert len(handler.records) == 1
    record = handler.records[0]
    properties = record.__dict__
    assert record.name == "fmu_settings_api.azure"
    assert record.getMessage() == "request_completed"
    assert properties["app_name"] == "fmu-settings-api"
    assert properties["app_version"] == "1.2.3"
    assert properties["environment"] == "development"
    assert properties["run_id"] == "run-123"
    assert properties["level"] == "info"
    assert properties["path"] == "/api/v1/project"
    assert properties["status_code"] == 200
    assert properties["details"] == '{"resources": ["config", "access"]}'
    assert properties["occurred_at"] == "2026-08-12T10:00:00+00:00"
    assert not hasattr(record, "optional")
    assert logging.getLogger("fmu_settings_api.azure").propagate is False

    telemetry.shutdown()


def test_emit_respects_minimum_level() -> None:
    """Events below the configured minimum level are not sent."""
    handler = RecordingHandler()
    telemetry = _configure_telemetry_with_handler(handler, logging.WARNING)

    telemetry.emit("debug_event", level=logging.INFO)
    telemetry.emit("warning_event", level=logging.WARNING)

    assert [record.getMessage() for record in handler.records] == ["warning_event"]
    telemetry.shutdown()


def test_emit_suppresses_handler_failure() -> None:
    """A handler failure does not escape from `emit()`."""
    handler = Mock(spec=logging.Handler)
    handler.level = logging.NOTSET
    handler.handle.side_effect = RuntimeError("send failed")
    telemetry = _configure_telemetry_with_handler(handler)

    telemetry.emit("request_completed")

    telemetry.shutdown()


def test_shutdown_uses_flush_when_force_flush_is_unavailable() -> None:
    """Standard logging handlers use their normal flush method."""
    handler = Mock(spec=logging.Handler)
    telemetry = _configure_telemetry_with_handler(handler)

    telemetry.shutdown()

    handler.flush.assert_called_once_with()
    handler.close.assert_called_once_with()


def test_repeated_shutdown_flushes_closes_and_detaches_handler_once() -> None:
    """Repeated shutdown calls clean up the handler only once."""
    handler = RecordingHandler()
    telemetry = _configure_telemetry_with_handler(handler)

    telemetry.shutdown()
    telemetry.shutdown()

    assert handler.force_flush_calls == 1
    assert handler.close_calls == 1
    assert handler not in logging.getLogger("fmu_settings_api.azure").handlers


def test_shutdown_closes_handler_when_force_flush_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A flush failure is reported without leaving the handler attached."""
    handler = RecordingHandler()
    telemetry = _configure_telemetry_with_handler(handler)

    with patch.object(handler, "force_flush", side_effect=RuntimeError("flush failed")):
        telemetry.shutdown()

    assert (
        "Unexpected telemetry shutdown error: flush failed" in capsys.readouterr().err
    )
    assert handler.close_calls == 1
    assert handler not in logging.getLogger("fmu_settings_api.azure").handlers


def test_shutdown_reports_close_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A close failure is reported after the handler is removed."""
    handler = RecordingHandler()
    telemetry = _configure_telemetry_with_handler(handler)

    with patch.object(handler, "close", side_effect=RuntimeError("close failed")):
        telemetry.shutdown()

    assert (
        "Unexpected telemetry shutdown error: close failed" in capsys.readouterr().err
    )
    assert handler not in logging.getLogger("fmu_settings_api.azure").handlers


def test_handler_configuration_failure_returns_noop(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A handler configuration failure is reported and returns a no-op."""
    handler = Mock(spec=logging.Handler)
    handler.setLevel.side_effect = RuntimeError("invalid handler")

    telemetry = _configure_telemetry_with_handler(handler)
    telemetry.emit("request_completed")

    assert "Telemetry is disabled: invalid handler" in capsys.readouterr().err
