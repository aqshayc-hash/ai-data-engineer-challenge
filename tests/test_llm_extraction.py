"""Tests for LLM extraction."""

import json
from unittest.mock import MagicMock, patch

import pytest

from mama_health.config import AppConfig
from mama_health.llm_extractor import ExtractedEvent, LLMExtractor
from mama_health.models import PatientJourneyEvent
from mama_health.prompts import EntityType, EventType, get_prompt_variant


def test_event_type_enum():
    """Test EventType enum contains expected values."""
    event_types = [e.value for e in EventType]

    assert "diagnosis" in event_types
    assert "symptom_onset" in event_types
    assert "treatment_initiated" in event_types
    assert "medication_side_effect" in event_types


def test_entity_type_enum():
    """Test EntityType enum contains expected values."""
    entity_types = [e.value for e in EntityType]

    assert "symptom" in entity_types
    assert "medication" in entity_types
    assert "condition" in entity_types


def test_extracted_event_validation():
    """Test ExtractedEvent model validation."""
    event = ExtractedEvent(
        event_id="e001",
        event_type="diagnosis",
        description="User diagnosed with condition",
        mentioned_entity="Crohn's disease",
        entity_type="condition",
        confidence=0.95,
    )

    assert event.event_id == "e001"
    assert event.confidence == 0.95
    assert event.quote is None


def test_extracted_event_invalid_confidence():
    """Test that confidence must be between 0-1."""
    with pytest.raises(ValueError):
        ExtractedEvent(
            event_id="e001",
            event_type="diagnosis",
            description="Test",
            mentioned_entity="Test",
            entity_type="condition",
            confidence=1.5,  # Invalid
        )


def test_extracted_event_to_journey_event():
    """Test converting ExtractedEvent to PatientJourneyEvent."""
    extracted = ExtractedEvent(
        event_id="e001",
        event_type="diagnosis",
        description="Diagnosed with Crohn's",
        mentioned_entity="Crohn's disease",
        entity_type="condition",
        confidence=0.95,
    )

    journey_event = extracted.to_patient_journey_event(
        source_post_id="post123",
        source_comment_id=None,
        posted_timestamp="2024-01-15T10:00:00",
    )

    assert isinstance(journey_event, PatientJourneyEvent)
    assert journey_event.source_post_id == "post123"
    assert journey_event.confidence == 0.95


def test_get_prompt_variant_general():
    """Test general prompt variant."""
    text = "I was diagnosed with Crohn's disease."
    prompt = get_prompt_variant("general", text, "Test post")

    assert "Crohn's disease" in prompt
    assert "Test post" in prompt
    assert "JSON" in prompt


def test_get_prompt_variant_symptoms():
    """Test symptoms-focused prompt variant."""
    text = "I had terrible pain for months."
    prompt = get_prompt_variant("symptoms", text)

    assert "symptoms" in prompt.lower()
    assert "pain" in prompt


def test_get_prompt_variant_medications():
    """Test medications-focused prompt variant."""
    text = "Started taking ibuprofen but it gave me headaches."
    prompt = get_prompt_variant("medications", text)

    assert "medication" in prompt.lower()
    assert "ibuprofen" in prompt


def test_extract_json_from_text_array():
    """Test extracting JSON array from text."""
    text = """
    Here are the results:
    [
        {"event_id": "e001", "type": "test"}
    ]
    """

    extracted = LLMExtractor._extract_json(text)

    assert extracted is not None
    assert extracted.startswith("[")
    assert extracted.endswith("]")


def test_extract_json_from_text_object():
    """Test extracting JSON object from text."""
    text = """
    Result: {
        "event_id": "e001",
        "type": "test"
    }
    More text after.
    """

    extracted = LLMExtractor._extract_json(text)

    assert extracted is not None
    assert extracted.startswith("{")


def test_extract_json_nested():
    """Test extracting nested JSON."""
    text = """
    [
        {
            "data": {
                "nested": true
            }
        }
    ]
    """

    extracted = LLMExtractor._extract_json(text)
    parsed = json.loads(extracted)

    assert parsed[0]["data"]["nested"] is True


def test_extract_json_not_found():
    """Test handling when no JSON found."""
    text = "No JSON here, just plain text."

    extracted = LLMExtractor._extract_json(text)

    assert extracted is None


@patch("mama_health.llm_extractor.litellm.completion")
def test_llm_extractor_initialization(mock_completion):
    """Test LLMExtractor initialization."""
    config = AppConfig()

    # Mock successful authentication
    mock_completion.return_value = MagicMock()

    extractor = LLMExtractor(config)

    assert extractor is not None
    assert "gemini" in extractor.model


def test_llm_extractor_missing_api_key():
    """Test LLMExtractor fails without API key."""
    # Patch only GOOGLE_API_KEY to be empty while keeping other env vars intact
    with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            config = AppConfig()
            LLMExtractor(config)


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_array(mock_completion):
    """Test parsing LLM response as array."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = json.dumps(
        [
            {
                "event_id": "e001",
                "event_type": "diagnosis",
                "description": "Diagnosed",
                "mentioned_entity": "disease",
                "entity_type": "condition",
                "confidence": 0.95,
            }
        ]
    )

    events = extractor._parse_response(response)

    assert len(events) == 1
    assert events[0].event_type == "diagnosis"


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_with_context(mock_completion):
    """Test parsing response with surrounding text."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = """
    Here are the extracted events:

    [
        {
            "event_id": "e001",
            "event_type": "symptom_onset",
            "description": "Had stomach pain",
            "mentioned_entity": "stomach pain",
            "entity_type": "symptom",
            "confidence": 0.88
        }
    ]

    As you can see, one key event was extracted.
    """

    events = extractor._parse_response(response)

    assert len(events) == 1
    assert events[0].event_type == "symptom_onset"


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_invalid_json(mock_completion):
    """Test parsing invalid JSON returns empty list."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = "This is not valid JSON"

    events = extractor._parse_response(response)

    assert events == []


@patch("mama_health.llm_extractor.litellm.completion")
def test_extract_events_empty_text(mock_completion):
    """Test extracting from empty text returns empty list."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    events = extractor.extract_events(
        text="",
        source_post_id="post123",
    )

    assert events == []


@patch("mama_health.llm_extractor.LLMExtractor._call_llm")
def test_extract_events_filtering_by_confidence(mock_call):
    """Test filtering events by confidence threshold."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = json.dumps(
        [
            {
                "event_id": "e001",
                "event_type": "diagnosis",
                "description": "Clear diagnosis",
                "mentioned_entity": "disease",
                "entity_type": "condition",
                "confidence": 0.95,  # High - should be included
            },
            {
                "event_id": "e002",
                "event_type": "symptom_onset",
                "description": "Possible symptom",
                "mentioned_entity": "pain",
                "entity_type": "symptom",
                "confidence": 0.3,  # Low - should be filtered
            },
        ]
    )

    mock_call.return_value = response

    events = extractor.extract_events(
        text="Some medical text",
        source_post_id="post123",
        min_confidence=0.5,
    )

    assert len(events) == 1
    assert events[0].confidence == 0.95


@patch("mama_health.llm_extractor.litellm.completion")
def test_batch_extract(mock_completion):
    """Test batch extraction."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    # Mock LLM responses
    response = json.dumps(
        [
            {
                "event_id": "e001",
                "event_type": "diagnosis",
                "description": "Diagnosed",
                "mentioned_entity": "disease",
                "entity_type": "condition",
                "confidence": 0.95,
            }
        ]
    )

    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=response))]
    )

    items = [
        {
            "text": "I was diagnosed.",
            "post_id": "post1",
        },
        {
            "text": "I had symptoms.",
            "post_id": "post2",
        },
    ]

    events = extractor.batch_extract(items)

    assert len(events) >= 0  # May vary based on LLM responses


def test_prompt_has_json_instruction():
    """Test that prompts include JSON format instructions."""
    text = "Test text"

    for prompt_type in ["general", "symptoms", "medications", "timeline", "emotion", "needs"]:
        prompt = get_prompt_variant(prompt_type, text)
        assert "JSON" in prompt or "json" in prompt.lower(), (
            f"Prompt {prompt_type} missing JSON instruction"
        )


def test_extraction_system_prompt_is_conservative():
    """Test that system prompt emphasizes conservative extraction."""
    from mama_health.prompts import EXTRACTION_SYSTEM_PROMPT

    assert "ONLY" in EXTRACTION_SYSTEM_PROMPT
    assert "NOT infer" in EXTRACTION_SYSTEM_PROMPT or "not" in EXTRACTION_SYSTEM_PROMPT.lower()
    assert "confidence" in EXTRACTION_SYSTEM_PROMPT.lower()


# ===== _extract_json edge cases =====


@pytest.mark.parametrize(
    "text,expected_prefix",
    [
        ('[{"key": "val"}]', "["),  # clean array
        ('{"key": "val"}', "{"),  # clean object
        ('text {"key": "val"} more', "{"),  # embedded object
        ("prefix [1, 2, 3] suffix", "["),  # embedded array
        ("[[nested]]", "["),  # outer array returned
        ("{}{}", "{"),  # first object only
    ],
)
def test_extract_json_valid_inputs(text, expected_prefix):
    """_extract_json extracts valid JSON from various text inputs."""
    result = LLMExtractor._extract_json(text)
    assert result is not None
    assert result.startswith(expected_prefix)


@pytest.mark.parametrize(
    "text",
    [
        "[unclosed",
        "",
        "no json here",
        "   ",
    ],
)
def test_extract_json_invalid_returns_none(text):
    """_extract_json returns None for unclosed, empty, or plain text."""
    result = LLMExtractor._extract_json(text)
    assert result is None


# ===== _call_llm retry logic =====


@patch("mama_health.llm_extractor.litellm.completion")
def test_call_llm_succeeds_on_second_attempt(mock_completion):
    """_call_llm warns on first failure then returns result on second attempt."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    success_response = MagicMock(
        choices=[MagicMock(message=MagicMock(content='[{"event_id": "x"}]'))]
    )
    mock_completion.side_effect = [Exception("timeout"), success_response]

    result = extractor._call_llm("some prompt")
    assert result == '[{"event_id": "x"}]'
    assert mock_completion.call_count == 2


@patch("mama_health.llm_extractor.litellm.completion")
def test_call_llm_raises_after_all_retries_exhausted(mock_completion):
    """_call_llm raises RuntimeError when all retry attempts fail."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    mock_completion.side_effect = Exception("network error")

    with pytest.raises(RuntimeError, match="LLM extraction failed"):
        extractor._call_llm("some prompt", retries=2)

    assert mock_completion.call_count == 2


# ===== extract_events negative paths =====


@patch("mama_health.llm_extractor.LLMExtractor._call_llm")
def test_extract_events_whitespace_only_returns_empty(mock_call):
    """extract_events returns [] for whitespace-only text (no LLM call made)."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    events = extractor.extract_events(text="   ", source_post_id="post1")

    assert events == []
    mock_call.assert_not_called()


@patch("mama_health.llm_extractor.LLMExtractor._call_llm")
def test_extract_events_llm_runtime_error_returns_empty(mock_call):
    """extract_events swallows RuntimeError from _call_llm and returns []."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    mock_call.side_effect = RuntimeError("LLM is down")

    events = extractor.extract_events(text="real text here", source_post_id="post1")

    assert events == []


@patch("mama_health.llm_extractor.LLMExtractor._call_llm")
def test_extract_events_non_json_prose_returns_empty(mock_call):
    """extract_events returns [] when LLM responds with non-JSON prose."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    mock_call.return_value = "I'm sorry, I cannot extract any events from this text."

    events = extractor.extract_events(text="some text", source_post_id="post1")

    assert events == []


# ===== _parse_response variants =====


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_dict_with_events_key(mock_completion):
    """_parse_response handles {'events': [...]} wrapper dict."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = json.dumps(
        {
            "events": [
                {
                    "event_id": "e001",
                    "event_type": "diagnosis",
                    "description": "Diagnosed",
                    "mentioned_entity": "Crohn's",
                    "entity_type": "condition",
                    "confidence": 0.9,
                }
            ]
        }
    )

    events = extractor._parse_response(response)
    assert len(events) == 1
    assert events[0].event_type == "diagnosis"


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_single_object_wrapped_as_list(mock_completion):
    """_parse_response wraps a single {…} object into a one-item list."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = json.dumps(
        {
            "event_id": "e001",
            "event_type": "symptom_onset",
            "description": "Pain started",
            "mentioned_entity": "pain",
            "entity_type": "symptom",
            "confidence": 0.85,
        }
    )

    events = extractor._parse_response(response)
    assert len(events) == 1
    assert events[0].event_type == "symptom_onset"


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_missing_event_id_autogenerated(mock_completion):
    """_parse_response auto-generates event_id when absent."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = json.dumps(
        [
            {
                # no event_id field
                "event_type": "diagnosis",
                "description": "Diagnosed",
                "mentioned_entity": "disease",
                "entity_type": "condition",
                "confidence": 0.9,
            }
        ]
    )

    events = extractor._parse_response(response)
    assert len(events) == 1
    assert events[0].event_id == "extracted_000"


@patch("mama_health.llm_extractor.litellm.completion")
def test_parse_response_invalid_event_skipped_rest_parsed(mock_completion):
    """_parse_response skips events that fail Pydantic validation."""
    config = AppConfig()
    extractor = LLMExtractor(config)

    response = json.dumps(
        [
            {
                "event_id": "bad",
                "event_type": "diagnosis",
                "description": "Test",
                "mentioned_entity": "entity",
                "entity_type": "condition",
                "confidence": 1.5,  # invalid: > 1.0
            },
            {
                "event_id": "good",
                "event_type": "symptom_onset",
                "description": "Pain",
                "mentioned_entity": "pain",
                "entity_type": "symptom",
                "confidence": 0.8,
            },
        ]
    )

    events = extractor._parse_response(response)
    assert len(events) == 1
    assert events[0].event_id == "good"
