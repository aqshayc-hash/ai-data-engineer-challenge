"""Dagster definitions for mama health AI Data Engineer Challenge."""

from dagster import (
    Definitions,
    define_asset_job,
    in_process_executor,
    load_assets_from_package_module,
)

from mama_health import assets

# Load all assets from the assets package
asset_list = load_assets_from_package_module(assets)


def get_definitions() -> Definitions:
    """Build and return Dagster definitions for the mama health pipeline.

    Registers all assets and defines four runnable jobs:
    - reddit_ingestion_job: fetch posts and comments from Reddit
    - llm_extraction_job: extract patient journey events via LLM
    - analytics_job: run all analytical assets
    - end_to_end_job: complete pipeline from ingestion to analytics

    Returns:
        Configured Dagster Definitions object
    """

    # Define the Reddit ingestion job
    reddit_ingestion_job = define_asset_job(
        name="reddit_ingestion_job",
        description="Fetch posts and comments from Reddit subreddit",
        tags={"team": "data-engineering", "phase": "ingestion"},
        executor_def=in_process_executor,
    )

    # Define the LLM extraction job
    llm_extraction_job = define_asset_job(
        name="llm_extraction_job",
        description="Extract patient journey events using LLM",
        tags={"team": "ai-engineering", "phase": "extraction"},
        executor_def=in_process_executor,
    )

    # Define analytics job
    analytics_job = define_asset_job(
        name="analytics_job",
        description="Patient journey analytics and insights",
        tags={"team": "data-science", "phase": "analytics"},
        executor_def=in_process_executor,
    )

    # Define end-to-end job (ingestion + extraction + analytics)
    end_to_end_job = define_asset_job(
        name="end_to_end_job",
        description="Complete pipeline: fetch data, extract insights, analyze patterns",
        tags={"team": "data-engineering", "phase": "complete"},
        executor_def=in_process_executor,
    )

    # Return definitions with assets and jobs
    defs = Definitions(
        assets=asset_list,
        jobs=[reddit_ingestion_job, llm_extraction_job, analytics_job, end_to_end_job],
    )

    return defs


# Export for Dagster to discover
defs = get_definitions()
