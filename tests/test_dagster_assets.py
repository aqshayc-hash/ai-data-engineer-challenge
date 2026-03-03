"""Smoke tests for Dagster asset functions.

These tests invoke asset functions directly (bypassing the Dagster execution
engine) to verify that they accept the expected input types and return the
expected output shapes. This catches broken asset dependency graphs and
type mismatches without requiring a running Dagster instance.
"""

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
    assert 'total_symptom_mentions' in result
    assert 'cooccurrence_pairs' in result


def test_medication_side_effect_associations_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = medication_side_effect_associations(all_extracted_events=sample_events)
    assert isinstance(result, dict)


def test_emotional_journey_phases_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = emotional_journey_phases(all_extracted_events=sample_events)
    assert isinstance(result, dict)
    assert 'phase_distribution' in result
    assert 'avg_confidence_by_phase' in result


def test_event_type_frequency_asset_returns_dict(sample_events):
    """Asset function accepts PatientJourneyEvent list and returns dict."""
    result = event_type_frequency(all_extracted_events=sample_events)
    assert isinstance(result, dict)
    assert 'total_events' in result
    assert 'event_type_distribution' in result


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

    assert 'generated_at' in result
    assert 'total_events_analyzed' in result
    assert 'analytics' in result
    assert 'key_findings' in result
