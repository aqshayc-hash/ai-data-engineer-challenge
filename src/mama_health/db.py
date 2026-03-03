"""SQLAlchemy table definitions for pipeline data persistence."""

from sqlalchemy import Column, DateTime, Float, MetaData, String, Table

metadata = MetaData()

patient_journey_events_table = Table(
    "patient_journey_events",
    metadata,
    Column("event_id", String, primary_key=True),
    Column("source_post_id", String, nullable=False, index=True),
    Column("source_comment_id", String, nullable=True),
    Column("event_type", String, nullable=False),
    Column("description", String, nullable=False),
    Column("mentioned_entity", String, nullable=False),
    Column("entity_type", String, nullable=False),
    Column("timestamp_mentioned", DateTime, nullable=True),
    Column("timestamp_posted", DateTime, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("partition_date", String, nullable=False),  # e.g. "2024-01-15"
)
