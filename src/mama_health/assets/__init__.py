"""Dagster assets for mama health project."""

from mama_health.assets.analytics import (
    emotional_journey_phases,
    emotional_state_events,
    event_type_frequency,
    medication_side_effect_associations,
    patient_journey_analytics_summary,
    symptom_cooccurrence_mapping,
    symptom_mention_frequency,
    symptom_to_diagnosis_timeline,
    treatment_mention_frequency,
    treatment_phase_duration,
    unmet_needs_identification,
    unmet_needs_summary,
)
from mama_health.assets.llm_extraction import (
    all_extracted_events,
    extracted_comment_events,
    extracted_post_events,
    extraction_quality_metrics,
    llm_extractor,
    medication_mentions,
    symptom_mentions,
)
from mama_health.assets.reddit_ingestion import (
    posts_metadata,
    posts_with_comments,
    raw_posts_json,
    reddit_client,
)

__all__ = [
    # Reddit ingestion
    "reddit_client",
    "posts_with_comments",
    "raw_posts_json",
    "posts_metadata",
    # LLM extraction
    "llm_extractor",
    "extracted_post_events",
    "extracted_comment_events",
    "all_extracted_events",
    "symptom_mentions",
    "medication_mentions",
    "extraction_quality_metrics",
    # Analytics
    "symptom_to_diagnosis_timeline",
    "treatment_phase_duration",
    "symptom_cooccurrence_mapping",
    "medication_side_effect_associations",
    "emotional_journey_phases",
    "emotional_state_events",
    "unmet_needs_identification",
    "unmet_needs_summary",
    "event_type_frequency",
    "treatment_mention_frequency",
    "symptom_mention_frequency",
    "patient_journey_analytics_summary",
]
