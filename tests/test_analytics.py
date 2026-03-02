"""Tests for patient journey analytics."""

import pytest
from datetime import datetime

from mama_health.analytics import (
    CoOccurrenceAnalyzer,
    SentimentAnalyzer,
    TemporalAnalyzer,
    UnmetNeedsAnalyzer,
)
from mama_health.models import PatientJourneyEvent


@pytest.fixture
def sample_events():
    """Provide sample patient journey events for testing."""
    return [
        PatientJourneyEvent(
            event_id="e001",
            source_post_id="post1",
            event_type="symptom_onset",
            description="Had stomach pain",
            mentioned_entity="stomach pain",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 1),
            confidence=0.95,
        ),
        PatientJourneyEvent(
            event_id="e002",
            source_post_id="post1",
            event_type="diagnosis",
            description="Diagnosed with Crohn's",
            mentioned_entity="Crohn's disease",
            entity_type="condition",
            timestamp_posted=datetime(2024, 2, 1),
            confidence=0.98,
        ),
        PatientJourneyEvent(
            event_id="e003",
            source_post_id="post1",
            event_type="treatment_initiated",
            description="Started mesalamine",
            mentioned_entity="mesalamine",
            entity_type="medication",
            timestamp_posted=datetime(2024, 2, 15),
            confidence=0.90,
        ),
        PatientJourneyEvent(
            event_id="e004",
            source_post_id="post1",
            event_type="medication_side_effect",
            description="Got headaches",
            mentioned_entity="headaches",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 3, 1),
            confidence=0.85,
        ),
        PatientJourneyEvent(
            event_id="e005",
            source_post_id="post2",
            event_type="symptom_onset",
            description="Joint pain",
            mentioned_entity="joint pain",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 5),
            confidence=0.92,
        ),
        PatientJourneyEvent(
            event_id="e006",
            source_post_id="post2",
            event_type="emotional_state",
            description="Feeling hopeless",
            mentioned_entity="depression",
            entity_type="emotion",
            timestamp_posted=datetime(2024, 2, 10),
            confidence=0.80,
        ),
        PatientJourneyEvent(
            event_id="e007",
            source_post_id="post3",
            event_type="unmet_need",
            description="No one told me how long recovery would take",
            mentioned_entity="timeline information",
            entity_type="other",
            timestamp_posted=datetime(2024, 3, 1),
            confidence=0.75,
        ),
    ]


def test_temporal_analyzer_duration_extraction():
    """Test extracting duration mentions from text."""
    text = "I had pain for 3 months"
    duration = TemporalAnalyzer.extract_duration_from_text(text)

    assert duration is not None
    assert duration['value'] == 3
    assert duration['unit'] == 'month'


def test_temporal_analyzer_duration_conversion():
    """Test converting duration to days."""
    duration = {'value': 3, 'unit': 'month'}
    days = TemporalAnalyzer.duration_to_days(duration)

    assert days == 90  # 3 * 30


def test_temporal_analyzer_symptom_to_diagnosis(sample_events):
    """Test extracting symptom to diagnosis timelines."""
    timelines = TemporalAnalyzer.symptom_to_diagnosis_timeline(sample_events)

    assert len(timelines) > 0
    assert 'symptom_description' in timelines[0]
    assert 'diagnosis_description' in timelines[0]


def test_temporal_analyzer_treatment_phase_duration(sample_events):
    """Test extracting treatment phase durations."""
    phases = TemporalAnalyzer.treatment_phase_duration(sample_events)

    assert len(phases) > 0
    assert 'treatment' in phases[0]
    assert 'phase_duration_days' in phases[0]


def test_cooccurrence_analyzer_symptom_matrix(sample_events):
    """Test symptom co-occurrence matrix."""
    cooccurrence = CoOccurrenceAnalyzer.symptom_cooccurrence_matrix(sample_events)

    assert 'total_symptom_mentions' in cooccurrence
    assert 'unique_symptoms' in cooccurrence
    assert 'cooccurrence_pairs' in cooccurrence
    assert cooccurrence['total_symptom_mentions'] >= 0


def test_cooccurrence_analyzer_medication_side_effects(sample_events):
    """Test medication-side effect associations."""
    associations = CoOccurrenceAnalyzer.medication_side_effect_associations(sample_events)

    assert isinstance(associations, dict)
    # May be empty or have entries depending on events


def test_sentiment_analyzer_journey_phase_classification():
    """Test classifying events into journey phases."""
    event = PatientJourneyEvent(
        event_id="e001",
        source_post_id="post1",
        event_type="symptom_onset",
        description="Had pain",
        mentioned_entity="pain",
        entity_type="symptom",
        timestamp_posted=datetime.now(),
        confidence=0.9,
    )

    phase = SentimentAnalyzer.classify_journey_phase(event)
    assert phase == 'symptom_phase'


def test_sentiment_analyzer_journey_phases(sample_events):
    """Test emotional phase distribution."""
    phases = SentimentAnalyzer.emotional_phase_distribution(sample_events)

    assert 'phase_distribution' in phases
    assert 'avg_confidence_by_phase' in phases
    assert len(phases['phase_distribution']) > 0


def test_sentiment_analyzer_emotional_events(sample_events):
    """Test extracting emotional events."""
    emotional_events = SentimentAnalyzer.emotional_events(sample_events)

    # Should extract emotional_state events
    assert any(e['event_description'] for e in emotional_events)


def test_sentiment_analyzer_sentiment_classification():
    """Test sentiment classification in emotional events."""
    event_positive = PatientJourneyEvent(
        event_id="e001",
        source_post_id="post1",
        event_type="emotional_state",
        description="Felt much better after treatment",
        mentioned_entity="improvement",
        entity_type="emotion",
        timestamp_posted=datetime.now(),
        confidence=0.9,
    )

    event_negative = PatientJourneyEvent(
        event_id="e002",
        source_post_id="post1",
        event_type="emotional_state",
        description="Really struggling with pain",
        mentioned_entity="struggle",
        entity_type="emotion",
        timestamp_posted=datetime.now(),
        confidence=0.9,
    )

    events = SentimentAnalyzer.emotional_events([event_positive, event_negative])

    sentiments = [e['sentiment'] for e in events]
    assert 'positive' in sentiments
    assert 'negative' in sentiments


def test_unmet_needs_analyzer_identification(sample_events):
    """Test identifying unmet needs."""
    unmet_needs = UnmetNeedsAnalyzer.identify_unmet_needs(sample_events)

    assert len(unmet_needs) > 0
    assert 'description' in unmet_needs[0]
    assert 'confidence' in unmet_needs[0]


def test_unmet_needs_analyzer_summary(sample_events):
    """Test unmet needs summary."""
    summary = UnmetNeedsAnalyzer.unmet_needs_summary(sample_events)

    assert 'total_unmet_needs_identified' in summary
    assert 'unique_need_types' in summary
    assert 'most_common_needs' in summary
    assert 'avg_confidence' in summary


def test_temporal_analyzer_no_duration():
    """Test extracting duration when none exists."""
    text = "I had a medical event"
    duration = TemporalAnalyzer.extract_duration_from_text(text)

    assert duration is None


def test_cooccurrence_analyzer_empty_events():
    """Test co-occurrence analysis on empty event list."""
    cooccurrence = CoOccurrenceAnalyzer.symptom_cooccurrence_matrix([])

    assert cooccurrence['total_symptom_mentions'] == 0
    assert cooccurrence['unique_symptoms'] == 0


def test_sentiment_analyzer_phase_for_treatment_event():
    """Test that treatment events map to treatment_phase."""
    event = PatientJourneyEvent(
        event_id="e001",
        source_post_id="post1",
        event_type="treatment_initiated",
        description="Started medication",
        mentioned_entity="medication",
        entity_type="medication",
        timestamp_posted=datetime.now(),
        confidence=0.9,
    )

    phase = SentimentAnalyzer.classify_journey_phase(event)
    assert phase == 'treatment_phase'


def test_temporal_analyzer_multiple_duration_units():
    """Test extracting different duration units."""
    test_cases = [
        ("3 days", 3, 'day'),
        ("2 weeks", 2, 'week'),
        ("6 months", 6, 'month'),
        ("1 year", 1, 'year'),
    ]

    for text, expected_value, expected_unit in test_cases:
        duration = TemporalAnalyzer.extract_duration_from_text(text)
        assert duration is not None
        assert duration['value'] == expected_value
        assert duration['unit'] == expected_unit
