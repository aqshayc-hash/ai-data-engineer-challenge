"""Shared pytest fixtures for mama health test suite."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from mama_health.config import RedditConfig
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


@pytest.fixture
def large_sample_events():
    """Provide 20+ events covering all 12 event types across 5 posts."""
    return [
        # --- post_a: symptom onset → diagnosis → treatment arc ---
        PatientJourneyEvent(
            event_id="la001",
            source_post_id="post_a",
            event_type="symptom_onset",
            description="Severe abdominal cramping began",
            mentioned_entity="abdominal cramping",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 1),
            confidence=0.95,
        ),
        PatientJourneyEvent(
            event_id="la002",
            source_post_id="post_a",
            event_type="symptom_onset",
            description="Chronic fatigue started",
            mentioned_entity="fatigue",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 2),
            confidence=0.90,
        ),
        PatientJourneyEvent(
            event_id="la003",
            source_post_id="post_a",
            event_type="symptom_progression",
            description="Pain worsened over three months",
            mentioned_entity="abdominal pain",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 10),
            confidence=0.88,
        ),
        PatientJourneyEvent(
            event_id="la004",
            source_post_id="post_a",
            event_type="medical_visit",
            description="Saw gastroenterologist",
            mentioned_entity="gastroenterologist",
            entity_type="specialist",
            timestamp_posted=datetime(2024, 1, 20),
            confidence=0.97,
        ),
        PatientJourneyEvent(
            event_id="la005",
            source_post_id="post_a",
            event_type="diagnosis",
            description="Diagnosed with Crohn's disease",
            mentioned_entity="Crohn's disease",
            entity_type="condition",
            timestamp_posted=datetime(2024, 2, 1),
            confidence=0.99,
        ),
        PatientJourneyEvent(
            event_id="la006",
            source_post_id="post_a",
            event_type="treatment_initiated",
            description="Started budesonide",
            mentioned_entity="budesonide",
            entity_type="medication",
            timestamp_posted=datetime(2024, 2, 5),
            confidence=0.93,
        ),
        # --- post_b: treatment change + side effects ---
        PatientJourneyEvent(
            event_id="lb001",
            source_post_id="post_b",
            event_type="treatment_initiated",
            description="Started azathioprine",
            mentioned_entity="azathioprine",
            entity_type="medication",
            timestamp_posted=datetime(2024, 2, 10),
            confidence=0.91,
        ),
        PatientJourneyEvent(
            event_id="lb002",
            source_post_id="post_b",
            event_type="medication_side_effect",
            description="Nausea after azathioprine dose",
            mentioned_entity="nausea",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 2, 15),
            confidence=0.87,
        ),
        PatientJourneyEvent(
            event_id="lb003",
            source_post_id="post_b",
            event_type="medication_side_effect",
            description="Hair thinning noticed",
            mentioned_entity="hair loss",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 2, 20),
            confidence=0.82,
        ),
        PatientJourneyEvent(
            event_id="lb004",
            source_post_id="post_b",
            event_type="treatment_changed",
            description="Switched from azathioprine to mercaptopurine",
            mentioned_entity="mercaptopurine",
            entity_type="medication",
            timestamp_posted=datetime(2024, 3, 1),
            confidence=0.94,
        ),
        PatientJourneyEvent(
            event_id="lb005",
            source_post_id="post_b",
            event_type="treatment_outcome",
            description="Symptoms improved on new medication",
            mentioned_entity="mercaptopurine",
            entity_type="medication",
            timestamp_posted=datetime(2024, 4, 1),
            confidence=0.86,
        ),
        # --- post_c: emotional journey + lifestyle ---
        PatientJourneyEvent(
            event_id="lc001",
            source_post_id="post_c",
            event_type="emotional_state",
            description="Feeling anxious about diagnosis",
            mentioned_entity="anxiety",
            entity_type="emotion",
            timestamp_posted=datetime(2024, 2, 5),
            confidence=0.89,
        ),
        PatientJourneyEvent(
            event_id="lc002",
            source_post_id="post_c",
            event_type="emotional_state",
            description="Feeling hopeful after joining support group",
            mentioned_entity="hope",
            entity_type="emotion",
            timestamp_posted=datetime(2024, 3, 10),
            confidence=0.78,
        ),
        PatientJourneyEvent(
            event_id="lc003",
            source_post_id="post_c",
            event_type="lifestyle_change",
            description="Adopted low-residue diet",
            mentioned_entity="low-residue diet",
            entity_type="other",
            timestamp_posted=datetime(2024, 3, 15),
            confidence=0.84,
        ),
        PatientJourneyEvent(
            event_id="lc004",
            source_post_id="post_c",
            event_type="unmet_need",
            description="Struggling to find patient support resources",
            mentioned_entity="support resources",
            entity_type="other",
            timestamp_posted=datetime(2024, 3, 20),
            confidence=0.76,
        ),
        # --- post_d: symptom co-occurrence for association tests ---
        PatientJourneyEvent(
            event_id="ld001",
            source_post_id="post_d",
            event_type="symptom_onset",
            description="Bloating and gas after meals",
            mentioned_entity="bloating",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 15),
            confidence=0.91,
        ),
        PatientJourneyEvent(
            event_id="ld002",
            source_post_id="post_d",
            event_type="symptom_onset",
            description="Joint pain in knees",
            mentioned_entity="joint pain",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 1, 16),
            confidence=0.88,
        ),
        PatientJourneyEvent(
            event_id="ld003",
            source_post_id="post_d",
            event_type="symptom_progression",
            description="Fatigue worsening",
            mentioned_entity="fatigue",
            entity_type="symptom",
            timestamp_posted=datetime(2024, 2, 1),
            confidence=0.85,
        ),
        # --- post_e: other / edge cases ---
        PatientJourneyEvent(
            event_id="le001",
            source_post_id="post_e",
            event_type="medical_visit",
            description="Emergency room visit due to flare",
            mentioned_entity="emergency room",
            entity_type="procedure",
            timestamp_posted=datetime(2024, 2, 28),
            confidence=0.96,
        ),
        PatientJourneyEvent(
            event_id="le002",
            source_post_id="post_e",
            event_type="treatment_outcome",
            description="Colonoscopy showed remission",
            mentioned_entity="colonoscopy",
            entity_type="procedure",
            timestamp_posted=datetime(2024, 4, 15),
            confidence=0.93,
        ),
        PatientJourneyEvent(
            event_id="le003",
            source_post_id="post_e",
            event_type="other",
            description="Genetic testing recommended",
            mentioned_entity="genetic testing",
            entity_type="procedure",
            timestamp_posted=datetime(2024, 5, 1),
            confidence=0.70,
        ),
    ]


@pytest.fixture
def mock_reddit_config():
    """Provide a RedditConfig with dummy values for PRAW-mocked tests."""
    return RedditConfig(
        client_id="fake_client_id",
        client_secret="fake_client_secret",
        user_agent="test-agent/1.0",
    )


@pytest.fixture
def mock_submission():
    """Return a MagicMock shaped like a PRAW Submission."""
    submission = MagicMock()
    submission.id = "abc123"
    submission.title = "My Crohn's journey"
    submission.selftext = "I was diagnosed last year..."
    submission.author = MagicMock()
    submission.author.name = "test_redditor"
    submission.subreddit = MagicMock()
    submission.subreddit.display_name = "Crohns"
    submission.score = 42
    submission.num_comments = 5
    submission.created_utc = 1704067200.0  # 2024-01-01 00:00:00 UTC
    submission.url = "https://reddit.com/r/Crohns/comments/abc123/"
    submission.comments = MagicMock()
    submission.comments.replace_more = MagicMock()
    submission.comments.list = MagicMock(return_value=[])
    return submission
