"""Tests for the events_stored_to_postgres Dagster asset.

The entire SQLAlchemy layer is mocked so no real database is required.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from dagster import build_op_context

from mama_health.models import PatientJourneyEvent


def _make_event(event_id: str = "e001", source_post_id: str = "post1") -> PatientJourneyEvent:
    return PatientJourneyEvent(
        event_id=event_id,
        source_post_id=source_post_id,
        event_type="diagnosis",
        description="Diagnosed with Crohn's",
        mentioned_entity="Crohn's disease",
        entity_type="condition",
        timestamp_posted=datetime(2024, 3, 15, 12, 0, 0),
        confidence=0.95,
    )


def _make_context(partition_key: str = "2024-03-15"):
    """Return a Dagster op context with the given partition key."""
    return build_op_context(partition_key=partition_key)


@patch("mama_health.assets.storage.metadata")
@patch("mama_health.assets.storage.create_engine")
@patch("mama_health.assets.storage.AppConfig")
def test_storage_empty_events_returns_zero(mock_app_config_cls, mock_create_engine, mock_metadata):
    """events_stored_to_postgres with [] returns 0 and skips INSERT."""
    from mama_health.assets.storage import events_stored_to_postgres

    # Wire up mocks
    mock_config = MagicMock()
    mock_config.database.connection_string = "postgresql://fake/db"
    mock_app_config_cls.return_value = mock_config

    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    context = _make_context("2024-03-15")
    result = events_stored_to_postgres(context=context, all_extracted_events=[])

    assert result == 0
    # DELETE should still be called (idempotency); INSERT should not
    assert mock_conn.execute.call_count == 1  # only the DELETE


@patch("mama_health.assets.storage.metadata")
@patch("mama_health.assets.storage.create_engine")
@patch("mama_health.assets.storage.AppConfig")
def test_storage_single_event_returns_one(mock_app_config_cls, mock_create_engine, mock_metadata):
    """events_stored_to_postgres with 1 event returns 1 and calls INSERT."""
    from mama_health.assets.storage import events_stored_to_postgres

    mock_config = MagicMock()
    mock_config.database.connection_string = "postgresql://fake/db"
    mock_app_config_cls.return_value = mock_config

    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    context = _make_context("2024-03-15")
    event = _make_event()
    result = events_stored_to_postgres(context=context, all_extracted_events=[event])

    assert result == 1
    # Both DELETE and INSERT should be called
    assert mock_conn.execute.call_count == 2


@patch("mama_health.assets.storage.metadata")
@patch("mama_health.assets.storage.create_engine")
@patch("mama_health.assets.storage.AppConfig")
def test_storage_row_contains_required_columns(
    mock_app_config_cls, mock_create_engine, mock_metadata
):
    """The row dict passed to INSERT contains all required column keys."""
    from mama_health.assets.storage import events_stored_to_postgres

    mock_config = MagicMock()
    mock_config.database.connection_string = "postgresql://fake/db"
    mock_app_config_cls.return_value = mock_config

    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    captured_rows = []

    def fake_execute(stmt, rows=None):
        if rows is not None:
            captured_rows.extend(rows)

    mock_conn = MagicMock()
    mock_conn.execute.side_effect = fake_execute
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    context = _make_context("2024-03-15")
    event = _make_event(event_id="e999")
    events_stored_to_postgres(context=context, all_extracted_events=[event])

    assert len(captured_rows) == 1
    row = captured_rows[0]
    for col in ("event_id", "event_type", "confidence", "partition_date"):
        assert col in row, f"Missing column: {col}"
    assert row["event_id"] == "e999"
    assert row["partition_date"] == "2024-03-15"
    assert row["confidence"] == pytest.approx(0.95)


@patch("mama_health.assets.storage.metadata")
@patch("mama_health.assets.storage.create_engine")
@patch("mama_health.assets.storage.AppConfig")
def test_storage_delete_called_before_insert(
    mock_app_config_cls, mock_create_engine, mock_metadata
):
    """DELETE must be called before INSERT to ensure idempotency."""
    from mama_health.assets.storage import events_stored_to_postgres

    mock_config = MagicMock()
    mock_config.database.connection_string = "postgresql://fake/db"
    mock_app_config_cls.return_value = mock_config

    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    call_order = []

    def fake_execute(stmt, rows=None):
        if rows is not None:
            call_order.append("INSERT")
        else:
            call_order.append("DELETE")

    mock_conn = MagicMock()
    mock_conn.execute.side_effect = fake_execute
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    context = _make_context("2024-03-15")
    event = _make_event()
    events_stored_to_postgres(context=context, all_extracted_events=[event])

    assert call_order == ["DELETE", "INSERT"]
