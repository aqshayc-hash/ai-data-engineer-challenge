"""Assets for persisting pipeline data to PostgreSQL."""

from dagster import asset, get_dagster_logger
from sqlalchemy import create_engine

from mama_health.config import AppConfig
from mama_health.db import metadata, patient_journey_events_table
from mama_health.models import PatientJourneyEvent
from mama_health.partitions import daily_partitions

logger = get_dagster_logger()


@asset(group_name="storage", partitions_def=daily_partitions)
def events_stored_to_postgres(
    context,
    all_extracted_events: list[PatientJourneyEvent],
) -> int:
    """Write extracted events to PostgreSQL for downstream querying.

    Upserts all extracted events for the current partition date into the
    `patient_journey_events` table. Existing rows for the partition are
    deleted before inserting new ones to ensure idempotency.

    Args:
        context: Dagster asset execution context (provides partition key)
        all_extracted_events: Extracted patient journey events to persist

    Returns:
        Count of rows written to PostgreSQL
    """
    config = AppConfig()
    engine = create_engine(config.database.connection_string)
    partition_date = context.partition_key

    metadata.create_all(engine)  # idempotent DDL

    rows = [
        {
            **e.model_dump(),
            "partition_date": partition_date,
            "timestamp_mentioned": e.timestamp_mentioned,
            "timestamp_posted": e.timestamp_posted,
        }
        for e in all_extracted_events
    ]

    with engine.begin() as conn:
        # Upsert: delete existing rows for this partition, then insert
        conn.execute(
            patient_journey_events_table.delete().where(
                patient_journey_events_table.c.partition_date == partition_date
            )
        )
        if rows:
            conn.execute(patient_journey_events_table.insert(), rows)

    logger.info(f"Stored {len(rows)} events to PostgreSQL for partition {partition_date}")
    return len(rows)
