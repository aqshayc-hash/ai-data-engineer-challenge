"""Prompt templates for LLM-based patient journey extraction."""

from enum import Enum
from typing import Optional


class EventType(Enum):
    """Types of patient journey events."""

    SYMPTOM_ONSET = "symptom_onset"
    SYMPTOM_PROGRESSION = "symptom_progression"
    MEDICAL_VISIT = "medical_visit"
    DIAGNOSIS = "diagnosis"
    TREATMENT_INITIATED = "treatment_initiated"
    TREATMENT_CHANGED = "treatment_changed"
    MEDICATION_SIDE_EFFECT = "medication_side_effect"
    TREATMENT_OUTCOME = "treatment_outcome"
    EMOTIONAL_STATE = "emotional_state"
    LIFESTYLE_CHANGE = "lifestyle_change"
    UNMET_NEED = "unmet_need"
    OTHER = "other"


class EntityType(Enum):
    """Types of entities mentioned in text."""

    SYMPTOM = "symptom"
    CONDITION = "condition"
    MEDICATION = "medication"
    PROCEDURE = "procedure"
    SPECIALIST = "specialist"
    EMOTION = "emotion"
    DURATION = "duration"
    OTHER = "other"


# System prompt for LLM
EXTRACTION_SYSTEM_PROMPT = """You are an expert medical NLP engineer analyzing patient narratives from online communities.
Your task is to extract structured patient journey events from unstructured text.

IMPORTANT INSTRUCTIONS:
1. Extract ONLY events explicitly mentioned or strongly implied in the text
2. Do NOT infer or hallucinate information not present in the text
3. Assign confidence scores (0-1) based on how explicit the mention is:
   - 0.9-1.0: Very explicit, verbatim mention
   - 0.7-0.8: Clear statement but with some inference needed
   - 0.5-0.6: Implied or inferred from context
   - <0.5: Very uncertain or speculative (mark as low confidence)
4. Return multiple events if multiple occur in the text
5. Be conservative - it's better to miss an event than to hallucinate one
6. Return results as a JSON array

MEDICAL CONTEXT:
- You're analyzing accounts of chronic conditions (Crohn's disease, diabetes, MS, etc.)
- Comments often contain first-person medical experiences
- Users discuss symptoms, treatments, emotional impacts, lifestyle changes
- Look for temporal indicators (temporal keywords: "for months", "initially", "after 3 weeks", etc.)

RESPONSE FORMAT:
Return a JSON array of events. Each event object must have:
{
  "event_id": "unique_id",
  "event_type": "one of: symptom_onset, symptom_progression, medical_visit, diagnosis, treatment_initiated, treatment_changed, medication_side_effect, treatment_outcome, emotional_state, lifestyle_change, unmet_need, other",
  "description": "natural language description of what happened",
  "mentioned_entity": "the main entity (symptom name, medication, specialist type, etc.)",
  "entity_type": "one of: symptom, condition, medication, procedure, specialist, emotion, duration, other",
  "temporal_indicators": "any time-related mentions (e.g., '3 months', 'initially', 'over the course of 2 years')",
  "confidence": 0.0 to 1.0,
  "quote": "direct relevant quote from the text if available, null otherwise"
}

If no events can be extracted, return an empty array [].
"""


def create_extraction_prompt(text: str, context: Optional[str] = None) -> str:
    """Create a prompt for extracting patient journey events.

    Args:
        text: The text to extract events from
        context: Optional context about the source (post title, subreddit, etc.)

    Returns:
        Complete prompt for LLM
    """
    prompt = f"""Extract patient journey events from the following text:

{f"CONTEXT: {context}" if context else ""}

TEXT TO ANALYZE:
\"\"\"
{text}
\"\"\"

Return the extracted events as a JSON array. Include only events that are explicitly mentioned or clearly implied.
Be conservative - if uncertain, either omit the event or mark with low confidence (< 0.5).
"""

    return prompt


# Symptom-focused extraction prompt
SYMPTOM_EXTRACTION_PROMPT = """Extract all symptoms and health conditions mentioned. For each:
1. Identify the symptom/condition name
2. Note when it started (if mentioned)
3. How long it lasted or has persisted
4. Any triggers or patterns mentioned
5. Severity if indicated

Return as JSON:
{
  "symptoms": [
    {
      "name": "symptom name",
      "onset_mentioned": "time reference if any",
      "duration": "how long it lasted/persists",
      "severity": "mild|moderate|severe (if mentioned)",
      "confidence": 0.0-1.0
    }
  ]
}
"""

# Medication-focused extraction prompt
MEDICATION_EXTRACTION_PROMPT = """Extract all medications and treatments mentioned. For each:
1. Medication/treatment name
2. Dosage or regimen if mentioned
3. Why it was prescribed (indication)
4. Side effects experienced
5. Efficacy or outcome
6. Whether it changed or was stopped

Return as JSON:
{
  "medications": [
    {
      "name": "medication name",
      "dosage": "dosage if mentioned, null otherwise",
      "indication": "why it was prescribed",
      "side_effects": ["list of mentioned side effects"],
      "efficacy": "effective|not effective|unknown",
      "discontinued": true|false,
      "confidence": 0.0-1.0
    }
  ]
}
"""

# Timeline extraction prompt
TIMELINE_EXTRACTION_PROMPT = """Extract the timeline of the patient journey. Create a chronological sequence of events:

1. Identify temporal markers (examples: "for 3 months", "started in 2022", "initially", "after diagnosis")
2. Create chronological sequence of key events
3. Estimate durations between events if possible

Return as JSON:
{
  "timeline_events": [
    {
      "sequence": 1,
      "event": "description of event",
      "time_reference": "when it occurred (absolute or relative)",
      "estimated_duration": "how long it lasted",
      "confidence": 0.0-1.0
    }
  ],
  "total_timeline_mentioned": "estimated total time period covered"
}
"""

# Emotional journey extraction prompt
EMOTIONAL_JOURNEY_PROMPT = """Extract emotional and psychological elements of the patient journey:

1. Emotions explicitly mentioned
2. Emotional progression (did mood change?)
3. Impact on quality of life
4. Coping strategies mentioned
5. Support system (family, friends, online community)

Return as JSON:
{
  "emotional_journey": {
    "emotions": ["list of emotions mentioned"],
    "progression": "description of emotional arc",
    "quality_of_life_impact": "description of impact",
    "coping_strategies": ["list of strategies mentioned"],
    "support_system": "description of support mentioned",
    "confidence": 0.0-1.0
  }
}
"""

# Challenges and unmet needs prompt
UNMET_NEEDS_PROMPT = """Extract information about patient challenges and unmet needs:

1. What problems or challenges does the patient describe?
2. What questions do they ask (indicating gaps in information)?
3. What outcomes are they seeking?
4. What barriers do they face?
5. What would improve their situation (stated or implied)?

Return as JSON:
{
  "unmet_needs": [
    {
      "challenge": "description of the challenge",
      "type": "information_gap|symptom_management|treatment_efficacy|emotion_support|access|other",
      "impact": "how it affects the patient",
      "potential_solution": "what might help (if mentioned)",
      "confidence": 0.0-1.0
    }
  ]
}
"""


def get_prompt_variant(prompt_type: str, text: str, context: Optional[str] = None) -> str:
    """Get a specific prompt variant for focused extraction.

    Args:
        prompt_type: Type of extraction (general, symptoms, medications, timeline, emotion, needs)
        text: Text to extract from
        context: Optional context

    Returns:
        Prompt for LLM
    """
    context_str = f"\nCONTEXT: {context}" if context else ""

    base_text = f'TEXT TO ANALYZE:\n"""\n{text}\n"""'

    prompts = {
        "general": create_extraction_prompt(text, context),
        "symptoms": f"{SYMPTOM_EXTRACTION_PROMPT}\n{context_str}\n{base_text}",
        "medications": f"{MEDICATION_EXTRACTION_PROMPT}\n{context_str}\n{base_text}",
        "timeline": f"{TIMELINE_EXTRACTION_PROMPT}\n{context_str}\n{base_text}",
        "emotion": f"{EMOTIONAL_JOURNEY_PROMPT}\n{context_str}\n{base_text}",
        "needs": f"{UNMET_NEEDS_PROMPT}\n{context_str}\n{base_text}",
    }

    return prompts.get(prompt_type, prompts["general"])
