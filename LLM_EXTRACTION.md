# LLM-Powered Patient Journey Extraction

## Overview

This phase uses Gemini API with structured prompts to extract patient journey events from unstructured Reddit text. The system converts free-form community narratives into structured, analyzable patient experiences.

## Architecture

### Components

1. **Prompt Templates** (`prompts.py`)
   - 6 specialized prompts for different extraction types
   - System prompt that guides LLM behavior
   - Confidence-aware extraction

2. **LLM Extractor Service** (`llm_extractor.py`)
   - Calls Gemini via litellm
   - Handles JSON parsing and validation
   - Retry logic and error handling
   - Confidence filtering

3. **Dagster Assets** (`assets/llm_extraction.py`)
   - `llm_extractor`: Service initialization
   - `extracted_post_events`: Extract from post titles/content
   - `extracted_comment_events`: Extract from comments
   - `all_extracted_events`: Combined results
   - `symptom_mentions`: Focused symptom extraction
   - `medication_mentions`: Focused medication extraction
   - `extraction_quality_metrics`: Quality analysis

## Setup

### 1. Get Gemini API Key

1. Visit https://aistudio.google.com/apikey
2. Click "Create API key in new project"
3. Copy the API key
4. Add to `.env`:
   ```
   GOOGLE_API_KEY=your_key_here
   ```

### 2. LLM Configuration (in `.env`)

```env
# Model and inference settings
LLM_MODEL=gemini-pro
LLM_TEMPERATURE=0.3          # Lower temp = more deterministic (better for structured extraction)
LLM_MAX_TOKENS=1000          # Sufficient for typical extractions
LLM_REQUEST_TIMEOUT=60       # Seconds to wait for response
```

## Prompt Design Decisions

### 1. System Prompt Strategy

**Decision**: Start with clear, conservative system prompt
```
"Extract ONLY events explicitly mentioned or strongly implied"
"Do NOT infer or hallucinate information"
```

**Rationale**: 
- Prevents hallucination of medical information (critical for safety)
- Reduces false positives in extraction
- Better for handling informal patient language

### 2. Confidence Scoring

**System includes confidence scoring (0-1):**
```
0.9-1.0: Verbatim mention ("I was diagnosed with Crohn's")
0.7-0.8: Clear but needs inference ("Started having issues 2 years ago")
0.5-0.6: Implied or inferred ("Things got worse after that")
<0.5:   Very uncertain or speculative
```

**Rationale**:
- Enables filtering by confidence threshold
- Allows downstream analysis to weight high-confidence events
- Honest about extraction uncertainty

### 3. Specialized Prompt Variants

**6 focused prompts for different extraction types:**

```python
- "general"      # All event types (default)
- "symptoms"     # Focus on symptoms with onset, duration, severity
- "medications"  # Medications with dosage, efficacy, side effects
- "timeline"     # Chronological sequence and durations
- "emotion"      # Emotional journey and support systems
- "needs"        # Patient challenges and unmet needs
```

**Rationale**:
- General extraction loses detail
- Specialized prompts yield richer structured output
- Can select prompts based on analysis objectives

### 4. JSON Output Structure

**Required fields per event:**
```json
{
  "event_id": "unique_id",
  "event_type": "symptom_onset|diagnosis|treatment_initiated|...",
  "description": "natural language description",
  "mentioned_entity": "Crohn's disease|ibuprofen|Dr. Johnson|...",
  "entity_type": "symptom|medication|specialist|...",
  "temporal_indicators": "time references from text",
  "confidence": 0.0-1.0,
  "quote": "direct quote from source (if available)"
}
```

**Rationale**:
- Pydantic models validate structure
- All fields enable rich downstream analysis
- Quotes aid human review and audit trails

### 5. Error Handling Approach

**Graceful degradation:**
- LLM call failures → returns empty list (no crash)
- JSON parse errors → attempts recovery
- Validation errors → logs warning, skips event
- Authentication errors → caught and reported clearly

**Rationale**:
- Pipeline robustness
- Logging enables debugging
- Partial results better than none

## Extraction Event Types

Extracted events map to 12 patient journey phases:

| Event Type | Example |
|-----------|---------|
| `symptom_onset` | "Started having stomach pain" |
| `symptom_progression` | "Pain got progressively worse" |
| `medical_visit` | "Went to urgent care" |
| `diagnosis` | "Diagnosed with Crohn's disease" |
| `treatment_initiated` | "Started taking mesalamine" |
| `treatment_changed` | "Switched from azathioprine to adalimumab" |
| `medication_side_effect` | "Got terrible headaches from the medication" |
| `treatment_outcome` | "Symptoms improved after 2 weeks" |
| `emotional_state` | "I was really depressed about the diagnosis" |
| `lifestyle_change` | "Had to change my diet significantly" |
| `unmet_need` | "No one could tell me when I'd feel better" |
| `other` | Fallback category |

## Running Extraction

### Option 1: Dagster UI (Recommended)

```bash
# Ensure Docker is running
docker compose up

# Visit http://localhost:3000

# In UI, trigger llm_extraction_job
# Or end_to_end_job for complete pipeline
```

### Option 2: Command Line

```bash
# With uv
uv run dagster job execute -f src/mama_health/dagster_definitions.py -j llm_extraction_job

# Or full pipeline
uv run dagster job execute -f src/mama_health/dagster_definitions.py -j end_to_end_job
```

## Asset Dependencies

```
posts_with_comments (from Reddit ingestion)
    │
    ├─→ extracted_post_events
    │       └─→ all_extracted_events → extraction_quality_metrics
    │                ↑
    ├─→ extracted_comment_events ─┘
    │
    ├─→ symptom_mentions
    │
    └─→ medication_mentions
```

## Configuration & Tuning

### Confidence Threshold

```python
# Default: 0.5 (include moderate-confidence extractions)
# Higher = fewer false positives but more misses
# Lower = more coverage but more noise

# In Dagster asset:
llm_extractor.extract_events(
    text=text,
    source_post_id=post_id,
    min_confidence=0.5,  # Adjust here
    prompt_type="general"
)
```

### Prompt Type Selection

```python
# General: Good for overview, mixed event types
prompt_type="general"

# Specialist: Better for specific extractions
prompt_type="symptoms"      # Best precision on symptoms
prompt_type="medications"   # Medication details
prompt_type="timeline"      # Chronological analysis
prompt_type="emotion"       # Emotional journey
prompt_type="needs"         # Patient needs
```

### Temperature Setting

```env
# In .env:
LLM_TEMPERATURE=0.3

# Lower (0.0-0.3): More deterministic, structured
# Higher (0.5-1.0): More creative, varied responses

# For extraction: Keep low (0.3) for consistency
```

## Example Extractions

### Input: Reddit Post

```
Title: "One year post Crohn's diagnosis"

Content: "I was diagnosed with Crohn's disease last year after 
experiencing severe abdominal pain and diarrhea for about 6 months. 
At first, my doctor tried me on mesalamine but it didn't help much. 
After that failed, I started adalimumab injections and my symptoms 
improved significantly within 2 weeks. The needles scared me at first 
but now it's routine. I still have flare-ups occasionally but my 
quality of life is so much better now."
```

### Extracted Events

```json
[
  {
    "event_id": "e001",
    "event_type": "symptom_onset",
    "description": "User experienced severe abdominal pain and diarrhea for about 6 months",
    "mentioned_entity": "severe abdominal pain and diarrhea",
    "entity_type": "symptom",
    "temporal_indicators": "for about 6 months",
    "confidence": 0.95,
    "quote": "experiencing severe abdominal pain and diarrhea for about 6 months"
  },
  {
    "event_id": "e002",
    "event_type": "diagnosis",
    "description": "User was diagnosed with Crohn's disease",
    "mentioned_entity": "Crohn's disease",
    "entity_type": "condition",
    "temporal_indicators": "last year",
    "confidence": 0.98,
    "quote": "diagnosed with Crohn's disease last year"
  },
  {
    "event_id": "e003",
    "event_type": "treatment_initiated",
    "description": "Doctor tried mesalamine treatment",
    "mentioned_entity": "mesalamine",
    "entity_type": "medication",
    "temporal_indicators": null,
    "confidence": 0.90,
    "quote": "my doctor tried me on mesalamine"
  },
  {
    "event_id": "e004",
    "event_type": "treatment_outcome",
    "description": "Mesalamine did not provide symptom improvement",
    "mentioned_entity": "mesalamine",
    "entity_type": "medication",
    "temporal_indicators": null,
    "confidence": 0.85,
    "quote": "it didn't help much"
  },
  {
    "event_id": "e005",
    "event_type": "treatment_changed",
    "description": "Switched from mesalamine to adalimumab injections",
    "mentioned_entity": "adalimumab",
    "entity_type": "medication",
    "temporal_indicators": "after that",
    "confidence": 0.92,
    "quote": "I started adalimumab injections"
  },
  {
    "event_id": "e006",
    "event_type": "medication_side_effect",
    "description": "Patient initially feared the needles",
    "mentioned_entity": "injection needles",
    "entity_type": "symptom",
    "temporal_indicators": "at first",
    "confidence": 0.75,
    "quote": "The needles scared me at first"
  },
  {
    "event_id": "e007",
    "event_type": "treatment_outcome",
    "description": "Adalimumab significantly improved symptoms within 2 weeks",
    "mentioned_entity": "adalimumab",
    "entity_type": "medication",
    "temporal_indicators": "within 2 weeks",
    "confidence": 0.96,
    "quote": "my symptoms improved significantly within 2 weeks"
  }
]
```

### Quality Metrics

```json
{
  "total_events": 7,
  "avg_confidence": 0.90,
  "min_confidence": 0.75,
  "max_confidence": 0.98,
  "high_confidence_count": 6,
  "medium_confidence_count": 1,
  "low_confidence_count": 0
}
```

## Specialized Extraction: Medications

### Input: Same Reddit Post

### Using Medication-Focused Prompt

```json
{
  "medications": [
    {
      "name": "mesalamine",
      "dosage": null,
      "indication": "Crohn's disease",
      "side_effects": [],
      "efficacy": "not effective",
      "discontinued": true,
      "confidence": 0.90
    },
    {
      "name": "adalimumab",
      "dosage": null,
      "indication": "Crohn's disease",
      "side_effects": ["needle anxiety"],
      "efficacy": "effective",
      "discontinued": false,
      "confidence": 0.95
    }
  ]
}
```

## Specialized Extraction: Timeline

### Extracted Timeline

```json
{
  "timeline_events": [
    {
      "sequence": 1,
      "event": "Symptom onset: severe abdominal pain and diarrhea",
      "time_reference": "6 months before diagnosis",
      "estimated_duration": "6 months",
      "confidence": 0.95
    },
    {
      "sequence": 2,
      "event": "Medical diagnosis of Crohn's disease",
      "time_reference": "1 year ago",
      "estimated_duration": null,
      "confidence": 0.98
    },
    {
      "sequence": 3,
      "event": "Started mesalamine treatment",
      "time_reference": "shortly after diagnosis",
      "estimated_duration": "unknown",
      "confidence": 0.85
    },
    {
      "sequence": 4,
      "event": "Switched to adalimumab injections",
      "time_reference": "after mesalamine failed",
      "estimated_duration": null,
      "confidence": 0.92
    },
    {
      "sequence": 5,
      "event": "Symptoms improved significantly",
      "time_reference": "2 weeks after starting adalimumab",
      "estimated_duration": null,
      "confidence": 0.96
    }
  ],
  "total_timeline_mentioned": "1 year"
}
```

## Monitoring & Debugging

### Check Extraction Quality

```bash
# View assets in Dagster UI
docker compose up
# Visit http://localhost:3000
# Click into extraction job run
# View extraction_quality_metrics asset output
```

### Review High-Confidence Events

```python
# Events with confidence >= 0.9 are high-confidence
# These are safest for analytics and reporting
```

### Debug Failed Extractions

```bash
# Check logs for extraction failures
docker compose logs -f dagster-daemon | grep "extraction"

# Look for JSON parse errors or API timeouts
# May indicate malformed LLM responses
```

## Limitations & Known Issues

### 1. Context Window
- Gemini Pro: ~30k tokens
- Very long posts may be truncated
- Mitigation: Could split very long texts

### 2. Informal Language
- Reddit uses casual/slang language
- LLM may miss medical terms written informally
- Mitigation: Prompt examples of informal medical language

### 3. Temporal Ambiguity
- "For ages" vs "for 3 months" both vague
- LLM captures but timestamps estimation challenging
- Mitigation: Use temporal_indicators field, human review for analysis

### 4. Medication Names
- Brand names vs generic names
- Spelling variations
- Non-standard abbreviations
- Mitigation: Curate list of known medications for validation

### 5. False Positives
- LLM may interpret figurative language as literal medical events
- Example: "My symptoms are killing me" → not actual death
- Mitigation: Human review of confidence < 0.7 events

## Cost Optimization

### Using Free Tier

Gemini API free tier: **60 requests per minute**

For Reddit posts with ~100 posts × ~30 comments = ~3,000 texts:
- At 60 req/min = 50 minutes
- Can process typical data run in < 1 hour

### Batching Strategy

Current implementation:
- Processes sequentially (slower, cheaper)
- Could batch for speed (Gemini API supports batching)

For production:
```python
# Future: Batch requests
batch_size = 10
for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    results = llm_extractor.batch_extract(batch)
```

## Next Steps

1. **Validate Extractions**
   - Manual review of sample posts
   - Adjust prompts based on results
   - Refine confidence thresholds

2. **Patient Journey Analytics** (Phase 3)
   - Build timeline analysis from extracted events
   - Compute symptom-to-diagnosis duration
   - Identify treatment efficacy patterns

3. **Scale Processing**
   - Add PostgreSQL persistence
   - Implement incremental runs
   - Add scheduled job execution

4. **Improve Prompts**
   - Add medical terminology examples
   - Include anti-patterns to avoid
   - Refine entity type taxonomy

## Testing

### Unit Tests

```bash
uv run pytest tests/test_llm_extraction.py -v
```

### Integration Test

```bash
# Run extraction on sample data
uv run python -c "
from mama_health.llm_extractor import LLMExtractor
from mama_health.config import AppConfig

config = AppConfig()
extractor = LLMExtractor(config)

sample_text = 'I was diagnosed with Crohn disease 2 years ago...'
events = extractor.extract_events(
    text=sample_text,
    source_post_id='test_001'
)
print(f'Extracted {len(events)} events')
for event in events:
    print(f'  - {event.event_type}: {event.description}')
"
```

## Reference Materials

- **LLM Extraction Code**: `src/mama_health/llm_extractor.py`
- **Prompt Templates**: `src/mama_health/prompts.py`
- **Assets**: `src/mama_health/assets/llm_extraction.py`
- **Models**: `src/mama_health/models.py`
- **Tests**: `tests/test_llm_extraction.py`
