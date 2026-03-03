"""Smoke tests for get_definitions() in dagster_definitions.py."""

from dagster import Definitions


def test_get_definitions_returns_definitions_object():
    """get_definitions() must return a Dagster Definitions instance."""
    from mama_health.dagster_definitions import get_definitions

    defs = get_definitions()
    assert isinstance(defs, Definitions)


def test_expected_jobs_are_registered():
    """All four pipeline jobs must be present in the definitions."""
    from mama_health.dagster_definitions import get_definitions

    defs = get_definitions()
    job_names = {j.name for j in defs.jobs}
    assert "reddit_ingestion_job" in job_names
    assert "llm_extraction_job" in job_names
    assert "analytics_job" in job_names
    assert "end_to_end_job" in job_names


def test_expected_schedules_are_registered():
    """Both daily and weekly schedules must be present in the definitions."""
    from mama_health.dagster_definitions import get_definitions

    defs = get_definitions()
    schedule_names = {s.name for s in defs.schedules}
    assert "daily_pipeline_schedule" in schedule_names
    assert "weekly_pipeline_schedule" in schedule_names


def test_definitions_has_assets():
    """Definitions must include at least one asset."""
    from mama_health.dagster_definitions import get_definitions

    defs = get_definitions()
    assert len(defs.assets) > 0


def test_definitions_has_io_manager():
    """Definitions must register an io_manager resource."""
    from mama_health.dagster_definitions import get_definitions

    defs = get_definitions()
    assert "io_manager" in defs.resources
