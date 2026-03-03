"""Dagster partition definitions for mama health pipeline."""

from dagster import DailyPartitionsDefinition, WeeklyPartitionsDefinition

daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")
weekly_partitions = WeeklyPartitionsDefinition(start_date="2024-01-01")
