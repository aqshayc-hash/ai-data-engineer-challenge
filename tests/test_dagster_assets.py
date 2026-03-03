"""Smoke tests for Dagster asset functions.

These tests invoke asset functions directly (bypassing the Dagster execution
engine) to verify that they accept the expected input types and return the
expected output shapes. This catches broken asset dependency graphs and
type mismatches without requiring a running Dagster instance.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from mama_health.assets.analytics import (
    emotional_journey_phases,
    event_type_frequency,
    medication_side_effect_associations,
    patient_journey_analytics_summary,
    symptom_cooccurrence_mapping,
    symptom_mention_frequency,
    symptom_to_diagnosis_timeline,
    treatment_mention_frequency,
    treatment_phase_duration,
    unmet_needs_summary,
)
from mama_health.assets.llm_extraction import (
    extraction_quality_metrics,
    medication_mentions,
    symptom_mentions,
)


def test_symptom_to_diagnosis_timeline_asset_returns_list(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns list."""
    result = symptom_to_diagnosis_timeline(all_extracted_events=sample_events)
    assert isinstance(result, list)


def test_treatment_phase_duration_asset_returns_list(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns list."""
    result = treatment_phase_duration(all_extracted_events=sample_events)
    assert isinstance(result, list)


def test_symptom_cooccurrence_mapping_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = symptom_cooccurrence_mapping(all_extracted_events=sample_events)
    assert isinstance(result, dict)
    assert "total_symptom_mentions" in result
    assert "cooccurrence_pairs" in result


def test_medication_side_effect_associations_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = medication_side_effect_associations(all_extracted_events=sample_events)
    assert isinstance(result, dict)


def test_emotional_journey_phases_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = emotional_journey_phases(all_extracted_events=sample_events)
    assert isinstance(result, dict)
    assert "phase_distribution" in result
    assert "avg_confidence_by_phase" in result


def test_event_type_frequency_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = event_type_frequency(all_extracted_events=sample_events)
    assert isinstance(result, dict)
    assert "total_events" in result
    assert "event_type_distribution" in result


def test_patient_journey_analytics_summary_asset_structure(sample_events):
    """Summary asset returns dict with required top-level keys."""
    # Build all upstream inputs by calling asset functions directly
    timelines = symptom_to_diagnosis_timeline(all_extracted_events=sample_events)
    phases = treatment_phase_duration(all_extracted_events=sample_events)
    cooccurrence = symptom_cooccurrence_mapping(all_extracted_events=sample_events)
    med_associations = medication_side_effect_associations(all_extracted_events=sample_events)
    journey_phases = emotional_journey_phases(all_extracted_events=sample_events)
    needs_sum = unmet_needs_summary(all_extracted_events=sample_events)
    event_freq = event_type_frequency(all_extracted_events=sample_events)
    treatment_freq = treatment_mention_frequency(medication_mentions=[])
    symptom_freq = symptom_mention_frequency(symptom_mentions=[])

    result = patient_journey_analytics_summary(
        all_extracted_events=sample_events,
        symptom_to_diagnosis_timeline=timelines,
        treatment_phase_duration=phases,
        symptom_cooccurrence_mapping=cooccurrence,
        medication_side_effect_associations=med_associations,
        emotional_journey_phases=journey_phases,
        unmet_needs_summary=needs_sum,
        event_type_frequency=event_freq,
        treatment_mention_frequency=treatment_freq,
        symptom_mention_frequency=symptom_freq,
    )

    assert "generated_at" in result
    assert "total_events_analyzed" in result
    assert "analytics" in result
    assert "key_findings" in result


# ===== symptom_mentions asset =====


def _make_posts_dict():
    """Return a minimal list[dict] as produced by posts_with_comments asset."""
    return [
        {
            "post_id": "post_a",
            "title": "My symptoms",
            "content": "I had stomach pain and nausea for weeks.",
            "created_at": "2024-01-01T00:00:00",
            "comments": [],
        },
    ]


def test_symptom_mentions_asset_returns_list_with_source_keys():
    """symptom_mentions returns a list; each item has source_post_id and source_created_at."""
    canned_symptoms = json.dumps(
        {
            "symptoms": [
                {"name": "stomach pain", "onset_mentioned": "weeks ago", "confidence": 0.9},
                {"name": "nausea", "onset_mentioned": None, "confidence": 0.85},
            ]
        }
    )

    mock_extractor = MagicMock()
    mock_extractor._call_llm.return_value = canned_symptoms

    with patch(
        "mama_health.assets.llm_extraction.LLMExtractor._extract_json", return_value=canned_symptoms
    ):
        # Call the raw function to bypass Dagster's type checker
        fn = symptom_mentions.op.compute_fn.decorated_fn
        result = fn(
            llm_extractor=mock_extractor,
            posts_with_comments=_make_posts_dict(),
        )

    assert isinstance(result, list)
    assert len(result) == 2
    for item in result:
        assert "source_post_id" in item
        assert "source_created_at" in item


def test_symptom_mentions_asset_empty_posts():
    """symptom_mentions with empty posts list returns empty list."""
    mock_extractor = MagicMock()
    fn = symptom_mentions.op.compute_fn.decorated_fn
    result = fn(
        llm_extractor=mock_extractor,
        posts_with_comments=[],
    )
    assert result == []
    mock_extractor._call_llm.assert_not_called()


# ===== medication_mentions asset =====


def test_medication_mentions_asset_returns_list_with_source_keys():
    """medication_mentions returns a list; each item has source_post_id and source_created_at."""
    canned_meds = json.dumps(
        {
            "medications": [
                {"name": "mesalamine", "dosage": "2.4g daily", "confidence": 0.92},
            ]
        }
    )

    mock_extractor = MagicMock()
    mock_extractor._call_llm.return_value = canned_meds

    with patch(
        "mama_health.assets.llm_extraction.LLMExtractor._extract_json", return_value=canned_meds
    ):
        fn = medication_mentions.op.compute_fn.decorated_fn
        result = fn(
            llm_extractor=mock_extractor,
            posts_with_comments=_make_posts_dict(),
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["source_post_id"] == "post_a"
    assert "source_created_at" in result[0]


def test_medication_mentions_asset_empty_posts():
    """medication_mentions with empty posts list returns empty list."""
    mock_extractor = MagicMock()
    fn = medication_mentions.op.compute_fn.decorated_fn
    result = fn(
        llm_extractor=mock_extractor,
        posts_with_comments=[],
    )
    assert result == []


# ===== extraction_quality_metrics asset =====


def test_extraction_quality_metrics_empty_events():
    """extraction_quality_metrics with empty list returns all-zero metrics."""
    result = extraction_quality_metrics(all_extracted_events=[])
    assert result["total_events"] == 0
    assert result["avg_confidence"] == 0
    assert result["min_confidence"] == 0
    assert result["max_confidence"] == 0


def test_extraction_quality_metrics_with_large_sample(large_sample_events):
    """extraction_quality_metrics with real events returns valid confidence range."""
    result = extraction_quality_metrics(all_extracted_events=large_sample_events)
    assert result["total_events"] == len(large_sample_events)
    assert 0.0 < result["avg_confidence"] <= 1.0
    assert result["min_confidence"] <= result["avg_confidence"] <= result["max_confidence"]
    assert result["high_confidence_count"] >= 0
    assert result["medium_confidence_count"] >= 0
    assert result["low_confidence_count"] >= 0
    total_buckets = (
        result["high_confidence_count"]
        + result["medium_confidence_count"]
        + result["low_confidence_count"]
    )
    assert total_buckets == len(large_sample_events)
