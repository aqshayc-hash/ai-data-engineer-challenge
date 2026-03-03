"""Shared pytest fixtures for mama health test suite."""

from datetime import datetime

import pytest

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
