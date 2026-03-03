"""Dagster definitions for mama health AI Data Engineer Challenge."""

from dagster import (
    AssetSelection,
    Definitions,
    FilesystemIOManager,
    build_schedule_from_partitioned_job,
    define_asset_job,
    in_process_executor,
    load_assets_from_package_module,
)

from mama_health import assets
from mama_health.partitions import daily_partitions, weekly_partitions  # noqa: F401

# Load all assets from the assets package
asset_list = load_assets_from_package_module(assets)


def get_definitions() -> Definitions:
    """Build and return Dagster definitions for the mama health pipeline.

    Registers all assets and defines four runnable jobs:
    - reddit_ingestion_job: fetch posts and comments from Reddit
    - llm_extraction_job: extract patient journey events via LLM
    - analytics_job: run all analytical assets
    - end_to_end_job: complete pipeline from ingestion to analytics

    Partition support: all data assets are daily-partitioned
    (DailyPartitionsDefinition starting 2024-01-01), enabling historical
    backfills and preventing re-processing of already-ingested days.

    Returns:
        Configured Dagster Definitions object
    """

    # Define the Reddit ingestion job (partitioned via assets)
    reddit_ingestion_job = define_asset_job(
        name="reddit_ingestion_job",
        selection=AssetSelection.groups("ingestion"),
        description="Fetch posts and comments from Reddit subreddit",
        tags={"team": "data-engineering", "phase": "ingestion"},
        executor_def=in_process_executor,
    )

    # Define the LLM extraction job (partitioned via assets)
    llm_extraction_job = define_asset_job(
        name="llm_extraction_job",
        selection=AssetSelection.groups("ingestion") | AssetSelection.groups("extraction"),
        description="Extract patient journey events using LLM",
        tags={"team": "ai-engineering", "phase": "extraction"},
        executor_def=in_process_executor,
    )

    # Define analytics job (partitioned via assets)
    analytics_job = define_asset_job(
        name="analytics_job",
        selection=AssetSelection.all(),
        description="Patient journey analytics and insights",
        tags={"team": "data-science", "phase": "analytics"},
        executor_def=in_process_executor,
    )

    # Define end-to-end job (ingestion + extraction + analytics, partitioned)
    end_to_end_job = define_asset_job(
        name="end_to_end_job",
        selection=AssetSelection.all(),
        description="Complete pipeline: fetch data, extract insights, analyze patterns",
        tags={"team": "data-engineering", "phase": "complete"},
        executor_def=in_process_executor,
    )

    # Daily schedule: run end_to_end_job at 2 AM UTC for the previous day's partition
    daily_pipeline_schedule = build_schedule_from_partitioned_job(
        end_to_end_job,
        hour_of_day=2,
        name="daily_pipeline_schedule",
    )

    # Weekly schedule: run end_to_end_job every Sunday at 2 AM UTC
    weekly_pipeline_schedule = build_schedule_from_partitioned_job(
        end_to_end_job,
        cron_schedule="0 2 * * 0",
        name="weekly_pipeline_schedule",
    )

    # Return definitions with assets, jobs, schedules, and IO manager
    defs = Definitions(
        assets=asset_list,
        jobs=[reddit_ingestion_job, llm_extraction_job, analytics_job, end_to_end_job],
        schedules=[daily_pipeline_schedule, weekly_pipeline_schedule],
        resources={
            "io_manager": FilesystemIOManager(base_dir="dagster_storage"),
        },
    )

    return defs


# Export for Dagster to discover
defs = get_definitions()
