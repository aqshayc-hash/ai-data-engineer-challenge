"""Analytics utilities for patient journey analysis."""

import re
from collections import Counter, defaultdict
from typing import Optional

from mama_health.models import PatientJourneyEvent


class TemporalAnalyzer:
    """Analyze temporal aspects of patient journeys."""

    @staticmethod
    def extract_duration_from_text(text: str) -> Optional[dict]:
        """Extract duration mentions from text (e.g., '3 months', '2 years').

        Args:
            text: Text to search for duration mentions

        Returns:
            Dict with 'value' and 'unit' or None if no duration found
        """
        # Pattern: number + unit (days, weeks, months, years)
        duration_pattern = r'(\d+)\s*(day|week|month|year)s?'
        match = re.search(duration_pattern, text, re.IGNORECASE)

        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            return {'value': value, 'unit': unit}

        return None

    @staticmethod
    def duration_to_days(duration: dict) -> int:
        """Convert duration dict to days.

        Args:
            duration: Dict with 'value' and 'unit' keys

        Returns:
            Number of days
        """
        unit_to_days = {
            'day': 1,
            'week': 7,
            'month': 30,  # Approximate
            'year': 365,  # Approximate
        }

        return duration['value'] * unit_to_days.get(duration['unit'], 1)

    @staticmethod
    def symptom_to_diagnosis_timeline(
        events: list[PatientJourneyEvent],
    ) -> list[dict]:
        """Extract symptom onset to diagnosis timelines.

        Args:
            events: List of patient journey events

        Returns:
            List of timeline dicts with symptom_onset_date, diagnosis_date, duration_days
        """
        timelines = []

        # Group by post/comment
        by_source = defaultdict(list)
        for event in events:
            key = (event.source_post_id, event.source_comment_id)
            by_source[key].append(event)

        for source_key, source_events in by_source.items():
            # Find symptom_onset and diagnosis events
            symptom_events = [e for e in source_events if e.event_type == 'symptom_onset']
            diagnosis_events = [e for e in source_events if e.event_type == 'diagnosis']

            # If both exist, extract temporal info
            if symptom_events and diagnosis_events:
                for symptom in symptom_events:
                    for diagnosis in diagnosis_events:
                        # Use temporal indicators if available
                        # This is a simplified version - in reality would parse temporal_indicators
                        timeline = {
                            'post_id': symptom.source_post_id,
                            'symptom_description': symptom.description,
                            'diagnosis_description': diagnosis.description,
                            'symptom_confidence': symptom.confidence,
                            'diagnosis_confidence': diagnosis.confidence,
                            'symptom_posted_at': symptom.timestamp_posted.isoformat(),
                            'diagnosis_posted_at': diagnosis.timestamp_posted.isoformat(),
                        }
                        timelines.append(timeline)

        return timelines

    @staticmethod
    def treatment_phase_duration(
        events: list[PatientJourneyEvent],
    ) -> list[dict]:
        """Extract treatment phase durations.

        Args:
            events: List of patient journey events

        Returns:
            List of treatment phase dicts
        """
        phases = []

        # Group by post
        by_post = defaultdict(list)
        for event in events:
            by_post[event.source_post_id].append(event)

        for post_id, post_events in by_post.items():
            # Find treatment pairs (initiated → changed or outcome)
            treatment_events = [
                e for e in post_events
                if 'treatment' in e.event_type or e.event_type == 'medication_side_effect'
            ]

            # Sort by timestamp
            treatment_events.sort(key=lambda e: e.timestamp_posted)

            # Find sequential treatments
            for i in range(len(treatment_events) - 1):
                current = treatment_events[i]
                next_event = treatment_events[i + 1]

                if current.event_type == 'treatment_initiated':
                    duration_days = (next_event.timestamp_posted - current.timestamp_posted).days

                    phase = {
                        'post_id': post_id,
                        'treatment': current.mentioned_entity,
                        'initiated_date': current.timestamp_posted.isoformat(),
                        'next_event': next_event.event_type,
                        'next_event_date': next_event.timestamp_posted.isoformat(),
                        'phase_duration_days': duration_days,
                    }
                    phases.append(phase)

        return phases


class CoOccurrenceAnalyzer:
    """Analyze co-occurrence patterns in patient data."""

    @staticmethod
    def symptom_cooccurrence_matrix(
        events: list[PatientJourneyEvent],
    ) -> dict:
        """Build co-occurrence matrix of symptoms mentioned together.

        Args:
            events: List of patient journey events

        Returns:
            Dict with co-occurrence counts and matrix
        """
        # Get all symptom mentions
        symptom_events = [e for e in events if e.entity_type == 'symptom']

        # Group symptoms by post/comment
        by_source = defaultdict(list)
        for event in symptom_events:
            key = (event.source_post_id, event.source_comment_id)
            by_source[key].append(event.mentioned_entity)

        # Build co-occurrence matrix
        cooccurrence = Counter()
        for source_symptoms in by_source.values():
            # Count pairs
            for i in range(len(source_symptoms)):
                for j in range(i + 1, len(source_symptoms)):
                    pair = tuple(sorted([source_symptoms[i], source_symptoms[j]]))
                    cooccurrence[pair] += 1

        # Build result
        result = {
            'total_symptom_mentions': len(symptom_events),
            'unique_symptoms': len(set(e.mentioned_entity for e in symptom_events)),
            'cooccurrence_pairs': dict(cooccurrence.most_common(20)),
        }

        return result

    @staticmethod
    def medication_side_effect_associations(
        events: list[PatientJourneyEvent],
    ) -> dict:
        """Extract medication-side effect associations.

        Args:
            events: List of patient journey events

        Returns:
            Dict mapping medications to side effects
        """
        medications = {}

        # Find all medication and side effect events
        med_events = [e for e in events if e.entity_type == 'medication']
        side_effect_events = [e for e in events if e.event_type == 'medication_side_effect']

        # Group by post/comment
        by_source = defaultdict(list)
        for event in med_events + side_effect_events:
            key = (event.source_post_id, event.source_comment_id)
            by_source[key].append(event)

        # For each source, associate medications with side effects
        for source_events in by_source.values():
            meds = [e for e in source_events if e.entity_type == 'medication']
            side_effects = [e for e in source_events if e.event_type == 'medication_side_effect']

            for med in meds:
                med_name = med.mentioned_entity
                if med_name not in medications:
                    medications[med_name] = {
                        'count': 0,
                        'side_effects': Counter(),
                        'avg_confidence': [],
                    }

                medications[med_name]['count'] += 1
                medications[med_name]['avg_confidence'].append(med.confidence)

                # Associate side effects
                for se in side_effects:
                    medications[med_name]['side_effects'][se.mentioned_entity] += 1

        # Finalize
        for med_name in medications:
            confidences = medications[med_name]['avg_confidence']
            medications[med_name]['avg_confidence'] = (
                sum(confidences) / len(confidences) if confidences else 0
            )
            medications[med_name]['side_effects'] = dict(
                medications[med_name]['side_effects'].most_common(5)
            )

        return medications


class SentimentAnalyzer:
    """Analyze sentiment and emotional aspects of patient journeys."""

    @staticmethod
    def classify_journey_phase(event: PatientJourneyEvent) -> str:
        """Classify event into patient journey phase.

        Args:
            event: Patient journey event

        Returns:
            Phase name: symptom_phase, diagnosis_phase, treatment_phase, management_phase
        """
        event_type = event.event_type

        if event_type in ['symptom_onset', 'symptom_progression']:
            return 'symptom_phase'
        elif event_type == 'diagnosis':
            return 'diagnosis_phase'
        elif event_type in ['treatment_initiated', 'treatment_changed']:
            return 'treatment_phase'
        elif event_type in ['treatment_outcome', 'lifestyle_change']:
            return 'management_phase'
        else:
            return 'other_phase'

    @staticmethod
    def emotional_phase_distribution(
        events: list[PatientJourneyEvent],
    ) -> dict:
        """Distribute events across emotional journey phases.

        Args:
            events: List of patient journey events

        Returns:
            Dict with phase distribution
        """
        phase_events = defaultdict(list)

        for event in events:
            phase = SentimentAnalyzer.classify_journey_phase(event)
            phase_events[phase].append(event)

        result = {
            'phase_distribution': {
                phase: len(events) for phase, events in phase_events.items()
            },
            'avg_confidence_by_phase': {
                phase: (
                    sum(e.confidence for e in events) / len(events)
                    if events
                    else 0
                )
                for phase, events in phase_events.items()
            },
        }

        return result

    @staticmethod
    def emotional_events(events: list[PatientJourneyEvent]) -> list[dict]:
        """Extract emotional state events with sentiment indicators.

        Args:
            events: List of patient journey events

        Returns:
            List of emotional events
        """
        emotional_events_list = []

        for event in events:
            if event.event_type == 'emotional_state' or event.event_type == 'unmet_need':
                # Classify sentiment based on keywords in description
                sentiment = 'neutral'
                if any(
                    word in event.description.lower()
                    for word in ['improve', 'better', 'helped', 'great', 'excellent']
                ):
                    sentiment = 'positive'
                elif any(
                    word in event.description.lower()
                    for word in ['worse', 'terrible', 'awful', 'struggle', 'difficult', 'pain']
                ):
                    sentiment = 'negative'

                emotional_events_list.append(
                    {
                        'event_description': event.description,
                        'mentioned_entity': event.mentioned_entity,
                        'sentiment': sentiment,
                        'confidence': event.confidence,
                        'posted_at': event.timestamp_posted.isoformat(),
                    }
                )

        return emotional_events_list


class UnmetNeedsAnalyzer:
    """Identify and analyze unmet patient needs."""

    @staticmethod
    def identify_unmet_needs(events: list[PatientJourneyEvent]) -> list[dict]:
        """Identify unmet needs from events.

        Args:
            events: List of patient journey events

        Returns:
            List of identified unmet needs
        """
        unmet_needs = []

        for event in events:
            if event.event_type == 'unmet_need':
                need = {
                    'description': event.description,
                    'entity': event.mentioned_entity,
                    'confidence': event.confidence,
                    'posted_at': event.timestamp_posted.isoformat(),
                    'post_id': event.source_post_id,
                }
                unmet_needs.append(need)

        return unmet_needs

    @staticmethod
    def unmet_needs_summary(events: list[PatientJourneyEvent]) -> dict:
        """Summarize unmet needs.

        Args:
            events: List of events

        Returns:
            Summary statistics on unmet needs
        """
        needs = UnmetNeedsAnalyzer.identify_unmet_needs(events)

        # Group by entity type
        entities = Counter(n['entity'] for n in needs)
        avg_confidence = sum(n['confidence'] for n in needs) / len(needs) if needs else 0

        return {
            'total_unmet_needs_identified': len(needs),
            'unique_need_types': len(entities),
            'most_common_needs': dict(entities.most_common(10)),
            'avg_confidence': avg_confidence,
        }
