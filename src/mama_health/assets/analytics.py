"""Dagster assets for patient journey analytics."""

from collections import Counter
from datetime import datetime

from dagster import asset, get_dagster_logger

from mama_health.analytics import (
    CoOccurrenceAnalyzer,
    SentimentAnalyzer,
    TemporalAnalyzer,
    UnmetNeedsAnalyzer,
)
from mama_health.models import PatientJourneyEvent
from mama_health.partitions import daily_partitions

logger = get_dagster_logger()


# ===== Temporal Analysis =====
@asset(group_name="analytics", partitions_def=daily_partitions)
def symptom_to_diagnosis_timeline(
    all_extracted_events: list[PatientJourneyEvent],
) -> list[dict]:
    """Extract symptom onset to diagnosis timelines.

    This asset analyzes the time between when patients first experienced
    symptoms and when they received a diagnosis. This temporal data is
    valuable for understanding diagnostic delays in the patient journey.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        List of timeline dictionaries with onset/diagnosis info
    """
    timelines = TemporalAnalyzer.symptom_to_diagnosis_timeline(all_extracted_events)

    logger.info(f"Extracted {len(timelines)} symptom-to-diagnosis timelines")

    if timelines:
        # Log some statistics
        avg_post_count = len(set(t.get('post_id') for t in timelines if 'post_id' in t))
        logger.info(f"  Across {avg_post_count} posts")

    return timelines


@asset(group_name="analytics", partitions_def=daily_partitions)
def treatment_phase_duration(
    all_extracted_events: list[PatientJourneyEvent],
) -> list[dict]:
    """Extract treatment phase durations.

    This asset identifies how long patients report being on specific
    treatments before switching, stopping, or changing. This helps
    understand treatment efficacy and patient persistence patterns.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        List of treatment phase dictionaries with duration info
    """
    phases = TemporalAnalyzer.treatment_phase_duration(all_extracted_events)

    logger.info(f"Identified {len(phases)} treatment phase transitions")

    if phases:
        # Log treatment statistics
        treatments = Counter(p.get('treatment') for p in phases)
        logger.info(f"  {len(treatments)} unique treatments tracked")
        logger.info(f"  Most common: {treatments.most_common(3)}")

    return phases


# ===== Co-occurrence Analysis =====
@asset(group_name="analytics", partitions_def=daily_partitions)
def symptom_cooccurrence_mapping(
    all_extracted_events: list[PatientJourneyEvent],
) -> dict:
    """Build symptom co-occurrence matrix.

    This asset identifies which symptoms are frequently mentioned together
    in patient narratives, revealing symptom clusters and patterns that
    characterize the patient experience.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        Dictionary with co-occurrence matrix and statistics
    """
    cooccurrence = CoOccurrenceAnalyzer.symptom_cooccurrence_matrix(all_extracted_events)

    logger.info("Symptom analysis:")
    logger.info(f"  Total mentions: {cooccurrence['total_symptom_mentions']}")
    logger.info(f"  Unique symptoms: {cooccurrence['unique_symptoms']}")
    logger.info(f"  Co-occurrence pairs: {len(cooccurrence['cooccurrence_pairs'])}")

    return cooccurrence


@asset(group_name="analytics", partitions_def=daily_partitions)
def medication_side_effect_associations(
    all_extracted_events: list[PatientJourneyEvent],
) -> dict:
    """Extract medication-side effect associations.

    This asset maps medications to their reported side effects based on
    patient narratives, ranking by frequency and confidence.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        Dictionary mapping medications to side effects and frequency
    """
    associations = CoOccurrenceAnalyzer.medication_side_effect_associations(
        all_extracted_events
    )

    logger.info("Medication analysis:")
    logger.info(f"  {len(associations)} medications tracked")

    if associations:
        top_meds = sorted(associations.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        for med_name, med_data in top_meds:
            logger.info(
                f"    {med_name}: {med_data['count']} mentions, "
                f"confidence={med_data['avg_confidence']:.2f}"
            )

    return associations


# ===== Sentiment & Emotional Journey =====
@asset(group_name="analytics", partitions_def=daily_partitions)
def emotional_journey_phases(
    all_extracted_events: list[PatientJourneyEvent],
) -> dict:
    """Classify events into patient journey phases and track distribution.

    This asset maps emotional and clinical events onto distinct phases of
    the patient journey (symptom, diagnosis, treatment, management),
    enabling phase-specific sentiment analysis.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        Dictionary with phase distribution and confidence metrics
    """
    phases = SentimentAnalyzer.emotional_phase_distribution(all_extracted_events)

    logger.info("Emotional journey phase distribution:")
    for phase, count in phases['phase_distribution'].items():
        avg_conf = phases['avg_confidence_by_phase'].get(phase, 0)
        logger.info(f"  {phase}: {count} events (avg_conf={avg_conf:.2f})")

    return phases


@asset(group_name="analytics", partitions_def=daily_partitions)
def emotional_state_events(
    all_extracted_events: list[PatientJourneyEvent],
) -> list[dict]:
    """Extract emotional state events with sentiment classification.

    This asset identifies emotional and psychological aspects of patient
    journeys, classifying sentiment (positive, negative, neutral) based
    on language patterns.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        List of emotional events with sentiment labels
    """
    emotional_events = SentimentAnalyzer.emotional_events(all_extracted_events)

    logger.info("Emotional state analysis:")
    logger.info(f"  Total emotional events: {len(emotional_events)}")

    if emotional_events:
        sentiment_counts = Counter(e['sentiment'] for e in emotional_events)
        for sentiment, count in sentiment_counts.items():
            logger.info(f"    {sentiment}: {count}")

    return emotional_events


# ===== Unmet Needs =====
@asset(group_name="analytics", partitions_def=daily_partitions)
def unmet_needs_identification(
    all_extracted_events: list[PatientJourneyEvent],
) -> list[dict]:
    """Identify and organize unmet patient needs.

    This asset surfaces recurring patient challenges, information gaps,
    and support needs that go unmet or generate frustrated responses,
    indicating areas for intervention.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        List of identified unmet needs with confidence scores
    """
    unmet_needs = UnmetNeedsAnalyzer.identify_unmet_needs(all_extracted_events)

    logger.info("Unmet needs identification:")
    logger.info(f"  Total needs identified: {len(unmet_needs)}")

    if unmet_needs:
        entities = Counter(n['entity'] for n in unmet_needs)
        logger.info(f"  Unique need categories: {len(entities)}")
        for category, count in entities.most_common(5):
            logger.info(f"    {category}: {count}")

    return unmet_needs


@asset(group_name="analytics", partitions_def=daily_partitions)
def unmet_needs_summary(
    all_extracted_events: list[PatientJourneyEvent],
) -> dict:
    """Summarize identified unmet needs.

    This asset aggregates unmet needs into actionable insights,
    highlighting the most pressing and common patient challenges.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        Summary statistics on unmet needs
    """
    summary = UnmetNeedsAnalyzer.unmet_needs_summary(all_extracted_events)

    logger.info("Unmet needs summary:")
    logger.info(f"  Total identified: {summary['total_unmet_needs_identified']}")
    logger.info(f"  Unique types: {summary['unique_need_types']}")
    logger.info(f"  Avg confidence: {summary['avg_confidence']:.2f}")

    return summary


# ===== Reporting & Aggregation =====
@asset(group_name="analytics", partitions_def=daily_partitions)
def event_type_frequency(
    all_extracted_events: list[PatientJourneyEvent],
) -> dict:
    """Compute frequency distribution of event types.

    This asset provides a breakdown of which event types are mentioned
    most frequently in patient narratives.

    Args:
        all_extracted_events: All extracted patient journey events

    Returns:
        Dictionary with event type frequencies
    """
    event_types = Counter(e.event_type for e in all_extracted_events)

    result = {
        'total_events': len(all_extracted_events),
        'unique_event_types': len(event_types),
        'event_type_distribution': dict(event_types.most_common()),
    }

    logger.info("Event type frequency distribution:")
    logger.info(f"  Total events: {result['total_events']}")
    for event_type, count in event_types.most_common(5):
        pct = 100 * count / len(all_extracted_events) if all_extracted_events else 0
        logger.info(f"    {event_type}: {count} ({pct:.1f}%)")

    return result


@asset(group_name="analytics", partitions_def=daily_partitions)
def treatment_mention_frequency(
    medication_mentions: list[dict],
) -> dict:
    """Track frequency of treatment mentions.

    This asset identifies which treatments are most discussed in patient
    communities, potentially surfacing shifts in treatment paradigms or
    emerging therapies.

    Args:
        medication_mentions: Medication mention records

    Returns:
        Dictionary with treatment frequency tracking
    """
    if not medication_mentions:
        return {
            'total_medication_mentions': 0,
            'unique_medications': 0,
            'medication_frequency': {},
        }

    # Extract medication names and count
    medications = Counter(m.get('name') for m in medication_mentions if m.get('name'))

    # Group by efficacy if available
    efficacy_by_med = {}
    for mention in medication_mentions:
        med_name = mention.get('name')
        if med_name and med_name not in efficacy_by_med:
            efficacy_by_med[med_name] = Counter()

        if med_name and mention.get('efficacy'):
            efficacy_by_med[med_name][mention['efficacy']] += 1

    result = {
        'total_medication_mentions': len(medication_mentions),
        'unique_medications': len(medications),
        'medication_frequency': dict(medications.most_common()),
        'medication_efficacy': {
            med: dict(efficacy_by_med[med].most_common())
            for med in medications
        },
    }

    logger.info("Treatment mention frequency:")
    logger.info(f"  Total mentions: {result['total_medication_mentions']}")
    logger.info(f"  Unique treatments: {result['unique_medications']}")

    for med, count in medications.most_common(5):
        logger.info(f"    {med}: {count} mentions")

    return result


@asset(group_name="analytics", partitions_def=daily_partitions)
def symptom_mention_frequency(
    symptom_mentions: list[dict],
) -> dict:
    """Track frequency of symptom mentions.

    This asset identifies the most commonly reported symptoms and their
    associated characteristics (onset, duration, severity).

    Args:
        symptom_mentions: Symptom mention records

    Returns:
        Dictionary with symptom frequency and characteristics
    """
    if not symptom_mentions:
        return {
            'total_symptom_mentions': 0,
            'unique_symptoms': 0,
            'symptom_frequency': {},
        }

    # Extract symptom names and count
    symptoms = Counter(s.get('name') for s in symptom_mentions if s.get('name'))

    # Severity distribution
    severity_by_symptom = {}
    for mention in symptom_mentions:
        symptom_name = mention.get('name')
        if symptom_name and symptom_name not in severity_by_symptom:
            severity_by_symptom[symptom_name] = Counter()

        if symptom_name and mention.get('severity'):
            severity_by_symptom[symptom_name][mention['severity']] += 1

    result = {
        'total_symptom_mentions': len(symptom_mentions),
        'unique_symptoms': len(symptoms),
        'symptom_frequency': dict(symptoms.most_common()),
        'symptom_severity': {
            symptom: dict(severity_by_symptom[symptom].most_common())
            for symptom in symptoms
        },
    }

    logger.info("Symptom mention frequency:")
    logger.info(f"  Total mentions: {result['total_symptom_mentions']}")
    logger.info(f"  Unique symptoms: {result['unique_symptoms']}")

    for symptom, count in symptoms.most_common(5):
        logger.info(f"    {symptom}: {count} mentions")

    return result


# ===== Comprehensive Analytics Summary =====
@asset(group_name="analytics", partitions_def=daily_partitions)
def patient_journey_analytics_summary(
    all_extracted_events: list[PatientJourneyEvent],
    symptom_to_diagnosis_timeline: list[dict],
    treatment_phase_duration: list[dict],
    symptom_cooccurrence_mapping: dict,
    medication_side_effect_associations: dict,
    emotional_journey_phases: dict,
    unmet_needs_summary: dict,
    event_type_frequency: dict,
    treatment_mention_frequency: dict,
    symptom_mention_frequency: dict,
) -> dict:
    """Comprehensive summary of patient journey analytics.

    This asset aggregates all analytical outputs into a single summary
    document, suitable for reporting, visualization, and downstream use.

    Args:
        all_extracted_events: All extracted events
        symptom_to_diagnosis_timeline: Timeline analysis
        treatment_phase_duration: Treatment duration analysis
        symptom_cooccurrence_mapping: Symptom co-occurrence
        medication_side_effect_associations: Medication associations
        emotional_journey_phases: Emotional phase analysis
        unmet_needs_summary: Unmet needs summary
        event_type_frequency: Event frequency
        treatment_mention_frequency: Treatment frequency
        symptom_mention_frequency: Symptom frequency

    Returns:
        Comprehensive analytics summary
    """
    summary = {
        'generated_at': datetime.utcnow().isoformat(),
        'total_events_analyzed': len(all_extracted_events),
        'analytics': {
            'temporal_analysis': {
                'symptom_to_diagnosis_timelines': len(symptom_to_diagnosis_timeline),
                'treatment_phase_transitions': len(treatment_phase_duration),
            },
            'cooccurrence_analysis': {
                'symptom_pairs': len(symptom_cooccurrence_mapping.get('cooccurrence_pairs', {})),
                'medications_with_side_effects': len(medication_side_effect_associations),
            },
            'emotional_journey': {
                'phases_identified': len(emotional_journey_phases['phase_distribution']),
                'emotional_events_count': sum(
                    emotional_journey_phases['phase_distribution'].values()
                ),
            },
            'unmet_needs': unmet_needs_summary['total_unmet_needs_identified'],
            'event_frequencies': {
                'event_types': event_type_frequency['unique_event_types'],
                'treatments': treatment_mention_frequency['unique_medications'],
                'symptoms': symptom_mention_frequency['unique_symptoms'],
            },
        },
        'key_findings': {
            'most_common_symptom': (
                next(iter(symptom_mention_frequency['symptom_frequency']))
                if symptom_mention_frequency['symptom_frequency']
                else None
            ),
            'most_mentioned_treatment': (
                next(iter(treatment_mention_frequency['medication_frequency']))
                if treatment_mention_frequency['medication_frequency']
                else None
            ),
            'most_common_side_effect': (
                next(
                    (
                        side_effect
                        for med_data in medication_side_effect_associations.values()
                        for side_effect in med_data.get('side_effects', {}).keys()
                    ),
                    None,
                )
            ),
            'primary_unmet_need': (
                next(iter(unmet_needs_summary['most_common_needs'].items()))[0]
                if unmet_needs_summary['most_common_needs']
                else None
            ),
        },
    }

    logger.info("=" * 60)
    logger.info("PATIENT JOURNEY ANALYTICS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total events analyzed: {summary['total_events_analyzed']}")
    logger.info(f"Generated: {summary['generated_at']}")
    logger.info("\nKey Analytics:")
    logger.info(f"  Symptom-Diagnosis Timelines: {summary['analytics']['temporal_analysis']['symptom_to_diagnosis_timelines']}")
    logger.info(
        f"  Treatment Phase Transitions: {summary['analytics']['temporal_analysis']['treatment_phase_transitions']}"
    )
    logger.info(
        f"  Symptom Co-occurrence Pairs: {summary['analytics']['cooccurrence_analysis']['symptom_pairs']}"
    )
    logger.info(
        f"  Medications Tracked: {summary['analytics']['event_frequencies']['treatments']}"
    )
    logger.info(f"  Unmet Needs Identified: {summary['analytics']['unmet_needs']}")
    logger.info("\nKey Findings:")
    for key, value in summary['key_findings'].items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)

    return summary
