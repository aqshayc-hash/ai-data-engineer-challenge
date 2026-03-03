"""Dagster assets for LLM-powered patient journey extraction."""

import json

from dagster import asset, get_dagster_logger

from mama_health.config import AppConfig
from mama_health.llm_extractor import LLMExtractor
from mama_health.models import PatientJourneyEvent
from mama_health.partitions import daily_partitions
from mama_health.prompts import get_prompt_variant

logger = get_dagster_logger()


@asset(group_name="extraction")
def llm_extractor() -> LLMExtractor:
    """Initialize LLM extractor service.

    Returns:
        Configured LLMExtractor instance
    """
    config = AppConfig()
    return LLMExtractor(config)


@asset(group_name="extraction", partitions_def=daily_partitions)
def extracted_post_events(
    llm_extractor: LLMExtractor,
    posts_with_comments: list[dict],
) -> list[PatientJourneyEvent]:
    """Extract patient journey events from post content.

    This asset processes the main content of each post (title + selftext)
    to identify key patient journey milestones like diagnosis, treatment changes,
    symptom onset, etc.

    Args:
        llm_extractor: Configured LLM extraction service
        posts_with_comments: List of posts with comments from Reddit

    Returns:
        List of extracted patient journey events from posts
    """
    all_events = []

    for post in posts_with_comments:
        # Combine title and content for better context
        text = f"{post['title']}\n\n{post['content']}" if post['content'] else post['title']

        if not text or not text.strip():
            continue

        events = llm_extractor.extract_events(
            text=text,
            source_post_id=post['post_id'],
            posted_timestamp=post['created_at'],
            min_confidence=0.5,
            prompt_type="general",
        )

        all_events.extend(events)

    logger.info(f"Extracted {len(all_events)} events from {len(posts_with_comments)} posts")
    return all_events


@asset(group_name="extraction", partitions_def=daily_partitions)
def extracted_comment_events(
    llm_extractor: LLMExtractor,
    posts_with_comments: list[dict],
) -> list[PatientJourneyEvent]:
    """Extract patient journey events from comments.

    This asset processes comments to identify additional patient experiences,
    treatment responses, and community support patterns.

    Args:
        llm_extractor: Configured LLM extraction service
        posts_with_comments: List of posts with comments

    Returns:
        List of extracted patient journey events from comments
    """
    all_events = []
    total_comments = 0

    for post in posts_with_comments:
        for comment in post.get('comments', []):
            total_comments += 1

            text = comment['text']
            if not text or not text.strip():
                continue

            events = llm_extractor.extract_events(
                text=text,
                source_post_id=post['post_id'],
                source_comment_id=comment['comment_id'],
                posted_timestamp=comment['created_at'],
                min_confidence=0.5,
                prompt_type="general",
            )

            all_events.extend(events)

    logger.info(
        f"Extracted {len(all_events)} events from {total_comments} comments across all posts"
    )
    return all_events


@asset(group_name="extraction", partitions_def=daily_partitions)
def all_extracted_events(
    extracted_post_events: list[PatientJourneyEvent],
    extracted_comment_events: list[PatientJourneyEvent],
) -> list[PatientJourneyEvent]:
    """Combine all extracted events from posts and comments.

    Args:
        extracted_post_events: Events extracted from post content
        extracted_comment_events: Events extracted from comments

    Returns:
        Combined list of all extracted events
    """
    all_events = extracted_post_events + extracted_comment_events

    logger.info(f"Total extracted events: {len(all_events)}")
    logger.info(f"  From posts: {len(extracted_post_events)}")
    logger.info(f"  From comments: {len(extracted_comment_events)}")

    # Log event type distribution
    event_types = {}
    for event in all_events:
        event_type = event.event_type
        event_types[event_type] = event_types.get(event_type, 0) + 1

    logger.info("Event type distribution:")
    for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {event_type}: {count}")

    return all_events


@asset(group_name="extraction", partitions_def=daily_partitions)
def symptom_mentions(
    llm_extractor: LLMExtractor,
    posts_with_comments: list[dict],
) -> list[dict]:
    """Extract focused symptom information using specialized prompts.

    This asset uses a specialized prompt to extract symptoms with more
    detailed information: onset timing, duration, severity, triggers.

    Args:
        llm_extractor: Configured LLM extraction service
        posts_with_comments: Posts with comments to analyze

    Returns:
        List of extracted symptom information objects
    """
    all_symptoms = []

    for post in posts_with_comments:
        text = f"{post['title']}\n\n{post['content']}" if post['content'] else post['title']

        if not text or not text.strip():
            continue

        try:
            # Use symptom-specialized extraction
            prompt = get_prompt_variant("symptoms", text, f"Post: {post['post_id']}")

            response = llm_extractor._call_llm(prompt)
            json_str = LLMExtractor._extract_json(response)

            if json_str:
                data = json.loads(json_str)
                symptoms = data.get('symptoms', [])

                for symptom in symptoms:
                    symptom['source_post_id'] = post['post_id']
                    symptom['source_created_at'] = post['created_at']
                    all_symptoms.append(symptom)

        except Exception as e:
            logger.warning(f"Failed to extract symptoms from post {post['post_id']}: {e}")
            continue

    logger.info(f"Extracted symptom mentions from {len(posts_with_comments)} posts")
    logger.info(f"Total symptom records: {len(all_symptoms)}")

    return all_symptoms


@asset(group_name="extraction", partitions_def=daily_partitions)
def medication_mentions(
    llm_extractor: LLMExtractor,
    posts_with_comments: list[dict],
) -> list[dict]:
    """Extract focused medication and treatment information.

    This asset uses specialized prompts to extract medications with details:
    dosage, indication, efficacy, side effects.

    Args:
        llm_extractor: Configured LLM extraction service
        posts_with_comments: Posts with comments to analyze

    Returns:
        List of extracted medication information objects
    """
    all_medications = []

    for post in posts_with_comments:
        text = f"{post['title']}\n\n{post['content']}" if post['content'] else post['title']

        if not text or not text.strip():
            continue

        try:
            # Use medication-specialized extraction
            prompt = get_prompt_variant("medications", text, f"Post: {post['post_id']}")

            response = llm_extractor._call_llm(prompt)
            json_str = LLMExtractor._extract_json(response)

            if json_str:
                data = json.loads(json_str)
                medications = data.get('medications', [])

                for medication in medications:
                    medication['source_post_id'] = post['post_id']
                    medication['source_created_at'] = post['created_at']
                    all_medications.append(medication)

        except Exception as e:
            logger.warning(f"Failed to extract medications from post {post['post_id']}: {e}")
            continue

    logger.info(f"Extracted medication mentions from {len(posts_with_comments)} posts")
    logger.info(f"Total medication records: {len(all_medications)}")

    return all_medications


@asset(group_name="extraction", partitions_def=daily_partitions)
def extraction_quality_metrics(
    all_extracted_events: list[PatientJourneyEvent],
) -> dict:
    """Calculate metrics about extraction quality and coverage.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        Dictionary of quality metrics
    """
    if not all_extracted_events:
        return {
            "total_events": 0,
            "avg_confidence": 0,
            "min_confidence": 0,
            "max_confidence": 0,
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
        }

    confidences = [event.confidence for event in all_extracted_events]

    metrics = {
        "total_events": len(all_extracted_events),
        "avg_confidence": sum(confidences) / len(confidences),
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
        "high_confidence_count": sum(1 for c in confidences if c >= 0.8),
        "medium_confidence_count": sum(1 for c in confidences if 0.5 <= c < 0.8),
        "low_confidence_count": sum(1 for c in confidences if c < 0.5),
    }

    logger.info("Extraction quality metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            logger.info(f"  {key}: {value:.3f}")
        else:
            logger.info(f"  {key}: {value}")

    return metrics
