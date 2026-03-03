"""LLM-based extraction service for patient journey events."""

import json
import logging
import os
from typing import Optional

import litellm
from pydantic import BaseModel, Field, ValidationError

from mama_health.config import AppConfig
from mama_health.models import PatientJourneyEvent
from mama_health.prompts import EXTRACTION_SYSTEM_PROMPT, get_prompt_variant

logger = logging.getLogger(__name__)

# Configure litellm for Gemini
litellm.verbose = False


class ExtractedEvent(BaseModel):
    """Extracted event from LLM."""

    event_id: str
    event_type: str
    description: str
    mentioned_entity: str
    entity_type: str
    temporal_indicators: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    quote: Optional[str] = None

    def to_patient_journey_event(
        self,
        source_post_id: str,
        source_comment_id: Optional[str] = None,
        posted_timestamp: Optional[str] = None,
    ) -> PatientJourneyEvent:
        """Convert to PatientJourneyEvent model."""
        from datetime import datetime

        posted_dt = (
            datetime.fromisoformat(posted_timestamp) if posted_timestamp else datetime.utcnow()
        )

        _valid_event_types = {
            "symptom_onset",
            "symptom_progression",
            "medical_visit",
            "diagnosis",
            "treatment_initiated",
            "treatment_changed",
            "medication_side_effect",
            "treatment_outcome",
            "emotional_state",
            "lifestyle_change",
            "unmet_need",
            "other",
        }
        _valid_entity_types = {
            "symptom",
            "condition",
            "medication",
            "procedure",
            "specialist",
            "emotion",
            "duration",
            "other",
        }
        event_type = self.event_type if self.event_type in _valid_event_types else "other"
        entity_type = self.entity_type if self.entity_type in _valid_entity_types else "other"

        return PatientJourneyEvent(
            event_id=self.event_id,
            source_post_id=source_post_id,
            source_comment_id=source_comment_id,
            event_type=event_type,  # type: ignore[arg-type]
            description=self.description,
            mentioned_entity=self.mentioned_entity,
            entity_type=entity_type,  # type: ignore[arg-type]
            timestamp_mentioned=None,  # Could be parsed from temporal_indicators
            timestamp_posted=posted_dt,
            confidence=self.confidence,
        )


class LLMExtractor:
    """Service for extracting patient journey events using LLM."""

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize LLM extractor.

        Args:
            config: AppConfig instance (loads from env if not provided)

        Raises:
            ValueError: If required config is missing
        """
        if config is None:
            config = AppConfig()

        self.config = config
        self.llm_config = config.llm
        self.google_config = config.google

        # Configure litellm for Gemini
        if not self.google_config.api_key:
            raise ValueError("GOOGLE_API_KEY is required")

        self.model = self.llm_config.model

        # Set API key once at initialization — litellm reads it from the environment
        os.environ["GOOGLE_API_KEY"] = self.google_config.api_key

        logger.info(f"Initialized LLM extractor with model: {self.model}")

    def extract_events(
        self,
        text: str,
        source_post_id: str,
        source_comment_id: Optional[str] = None,
        posted_timestamp: Optional[str] = None,
        min_confidence: float = 0.5,
        prompt_type: str = "general",
    ) -> list[PatientJourneyEvent]:
        """Extract patient journey events from text.

        Args:
            text: Text to extract from
            source_post_id: ID of source Reddit post
            source_comment_id: Optional ID if from a comment
            posted_timestamp: When the text was posted (ISO format)
            min_confidence: Minimum confidence threshold (0-1)
            prompt_type: Type of extraction (general, symptoms, medications, etc)

        Returns:
            List of extracted PatientJourneyEvent objects
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for extraction from post {source_post_id}")
            return []

        try:
            # Create prompt
            context = f"Post ID: {source_post_id}"
            if source_comment_id:
                context += f", Comment ID: {source_comment_id}"

            prompt = get_prompt_variant(prompt_type, text, context)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            events = self._parse_response(response)

            # Filter by confidence
            filtered_events = [event for event in events if event.confidence >= min_confidence]

            # Convert to PatientJourneyEvent (skip any that fail validation)
            journey_events = []
            for event in filtered_events:
                try:
                    journey_events.append(
                        event.to_patient_journey_event(
                            source_post_id=source_post_id,
                            source_comment_id=source_comment_id,
                            posted_timestamp=posted_timestamp,
                        )
                    )
                except Exception as conv_err:
                    logger.warning(
                        f"Skipping event {event.event_id} due to conversion error: {conv_err}"
                    )

            logger.info(
                f"Extracted {len(journey_events)} events from "
                f"{'comment' if source_comment_id else 'post'} {source_post_id} "
                f"(prompt_type={prompt_type}, min_confidence={min_confidence})"
            )

            return journey_events

        except Exception as e:
            logger.error(
                f"Failed to extract events from {'comment' if source_comment_id else 'post'} "
                f"{source_post_id}: {e}"
            )
            return []

    def _call_llm(self, prompt: str, retries: int = 2) -> str:
        """Call LLM with retry logic.

        Args:
            prompt: Prompt to send to LLM
            retries: Number of retries on failure

        Returns:
            LLM response text

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        for attempt in range(retries):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    timeout=self.llm_config.request_timeout,
                )

                return response.choices[0].message.content  # type: ignore[no-any-return]

            except Exception as e:
                if attempt < retries - 1:
                    logger.warning(f"LLM call failed (attempt {attempt + 1}/{retries}): {e}")
                    continue
                else:
                    raise RuntimeError(f"LLM extraction failed after {retries} retries: {e}") from e

        raise RuntimeError(f"LLM extraction failed: no retries configured (retries={retries})")

    def _parse_response(self, response: str) -> list[ExtractedEvent]:
        """Parse LLM response into structured events.

        Args:
            response: Raw LLM response text

        Returns:
            List of ExtractedEvent objects

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to extract JSON from response
            # LLM might include explanatory text before/after JSON
            json_str = self._extract_json(response)

            if not json_str:
                logger.warning("Could not find JSON in LLM response")
                return []

            data = json.loads(json_str)

            # Handle both array and object responses
            if isinstance(data, dict):
                # Could be {"events": [...]} or single event
                if "events" in data:
                    events_list = data["events"]
                else:
                    events_list = [data]
            elif isinstance(data, list):
                events_list = data
            else:
                logger.warning(f"Unexpected response structure: {type(data)}")
                return []

            # Parse each event
            parsed_events = []
            for i, event_data in enumerate(events_list):
                try:
                    # Generate event_id if missing
                    if "event_id" not in event_data:
                        event_data["event_id"] = f"extracted_{i:03d}"

                    event = ExtractedEvent(**event_data)
                    parsed_events.append(event)

                except ValidationError as e:
                    logger.warning(f"Failed to parse event {i}: {e}")
                    continue

            return parsed_events

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Extract JSON from text that may contain other content.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string or None
        """
        # Try to find JSON array
        start_idx = text.find("[")
        if start_idx >= 0:
            # Find matching closing bracket
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == "[":
                    depth += 1
                elif text[i] == "]":
                    depth -= 1
                    if depth == 0:
                        return text[start_idx : i + 1]

        # Try to find JSON object
        start_idx = text.find("{")
        if start_idx >= 0:
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start_idx : i + 1]

        return None

    def batch_extract(
        self,
        items: list[dict],
        min_confidence: float = 0.5,
        skip_errors: bool = True,
    ) -> list[PatientJourneyEvent]:
        """Extract events from multiple texts.

        Args:
            items: List of dicts with keys: text, post_id, comment_id (optional), timestamp (optional)
            min_confidence: Minimum confidence threshold
            skip_errors: Whether to continue on errors

        Returns:
            Combined list of extracted events
        """
        all_events = []

        for i, item in enumerate(items):
            try:
                events = self.extract_events(
                    text=item["text"],
                    source_post_id=item["post_id"],
                    source_comment_id=item.get("comment_id"),
                    posted_timestamp=item.get("timestamp"),
                    min_confidence=min_confidence,
                )
                all_events.extend(events)

            except Exception as e:
                if skip_errors:
                    logger.warning(f"Skipped item {i}: {e}")
                    continue
                else:
                    raise

        logger.info(f"Batch extraction completed: {len(all_events)} events from {len(items)} items")
        return all_events
