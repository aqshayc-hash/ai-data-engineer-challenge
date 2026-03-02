# LLM-Powered Extraction - Implementation Summary

## ✅ What Was Built

A complete LLM-powered extraction pipeline using Gemini API that converts free-form patient narratives from Reddit into structured patient journey events with confidence scores.

## Files Created

### Core Components

1. **`src/mama_health/prompts.py`** (450 lines)
   - 6 specialized prompt templates for different extraction types
   - System prompt emphasizing conservative, non-hallucinating extraction
   - Enums for event types and entity types
   - Helper functions for prompt generation
   - **Features:**
     - Event types: 12 patient journey phases (diagnosis, treatment, symptoms, etc)
     - Entity types: symptom, medication, condition, procedure, specialist, emotion, duration
     - Confidence guidance (0.9-1.0 = verbatim, 0.7-0.8 = clear, 0.5-0.6 = implied)

2. **`src/mama_health/llm_extractor.py`** (350 lines)
   - `LLMExtractor` class for Gemini API integration
   - litellm library for model abstraction
   - Robust JSON parsing with error recovery
   - Batch extraction support
   - **Features:**
     - Retry logic for API failures
     - Confidence filtering
     - Graceful error handling
     - Detailed logging

3. **`src/mama_health/assets/llm_extraction.py`** (250 lines)
   - 7 Dagster assets for extraction workflow
   - `llm_extractor`: Service initialization
   - Post-level and comment-level extraction
   - Specialized symptom and medication extraction
   - Quality metrics computation
   - **Features:**
     - Processes posts and comments separately
     - Combines results with deduplication
     - Event type distribution analysis
     - Confidence-based filtering

### Configuration & Infrastructure

4. **`pyproject.toml`** - Updated
   - Added: `litellm`, `google-generativeai`
   - All LLM dependencies properly versioned

5. **`docker-compose.yml`** - Updated
   - `GOOGLE_API_KEY` passed to containers
   - All LLM environment variables configured

6. **`.env.example`** - Updated
   - `GOOGLE_API_KEY`: Gemini API key
   - `LLM_MODEL`: Model selection (default: gemini-pro)
   - `LLM_TEMPERATURE`: Inference temperature
   - `LLM_MAX_TOKENS`: Response length limit

7. **`src/mama_health/dagster_definitions.py`** - Updated
   - Added `llm_extraction_job` for extraction phase
   - Added `end_to_end_job` for complete pipeline (ingestion + extraction)
   - All new assets automatically loaded

### Documentation

8. **`LLM_EXTRACTION.md`** (600+ lines)
   - Complete architecture overview
   - Setup instructions
   - Prompt design decisions and rationale
   - Example extractions with full output
   - Specialized extraction examples (symptoms, medications, timeline)
   - Monitoring and debugging guide
   - Cost optimization strategies
   - Known limitations and workarounds

9. **`validate_llm_setup.py`** (300 lines)
   - Pre-flight validation script
   - Checks: API key, config, prompt templates, LLMExtractor init, assets, live API
   - Actionable error messages
   - Provides setup guidance

### Testing

10. **`tests/test_llm_extraction.py`** (350 lines)
    - 25+ unit tests covering:
      - Model validation
      - Prompt generation
      - JSON parsing from LLM responses
      - Event extraction with confidence filtering
      - Error handling
      - Batch processing
    - Mock LLM calls for deterministic testing

## Architecture

### Asset Dependencies

```
Reddit Ingestion (previous phase)
    └─ posts_with_comments (list of dicts)
            │
            ├─→ llm_extractor (service init)
            │       │
            │       ├─→ extracted_post_events
            │       │       └─→ all_extracted_events
            │       │               ├─→ extraction_quality_metrics
            │       │               └─ (feed to analytics)
            │       │
            │       ├─→ extracted_comment_events ──┘
            │       │
            │       ├─→ symptom_mentions (focused extraction)
            │       │
            │       └─→ medication_mentions (focused extraction)
```

## Key Design Decisions

### 1. Confidence Scoring (Conservative Approach)

**Design:**
- 0.9-1.0: Verbatim mention ("I was diagnosed with X")
- 0.7-0.8: Clear statement with some inference
- 0.5-0.6: Implied or inferred
- <0.5: Uncertain or speculative

**Rationale:**
- Enables filtering by confidence threshold
- Honest about uncertainty
- Prevents false confidence in extractions

### 2. Specialized Prompt Variants

**6 prompt types:**
- `general`: All event types (default)
- `symptoms`: Focus on onset, duration, severity
- `medications`: Dosage, efficacy, side effects
- `timeline`: Chronological sequence
- `emotion`: Emotional journey, support
- `needs`: Challenges, unmet needs

**Rationale:**
- General extraction loses detail
- Specialized prompts yield richer, structured output
- Can select based on analysis objective

### 3. Conservative Extraction (No Hallucination)

**System prompt emphasizes:**
- "Extract ONLY events explicitly mentioned"
- "Do NOT infer or hallucinate information"
- Include confidence scores for transparency
- Better to miss an event than invent one

**Rationale:**
- Medical information must be accurate
- Patient safety critical
- Prevents misleading analytics

### 4. JSON Parsing with Error Recovery

**Implementation:**
- Finds JSON boundaries in raw LLM response
- Handles LLM wrapping response in explanatory text
- Falls back to empty array on parse error
- Logs warnings but doesn't crash

**Rationale:**
- LLMs often wrap JSON in prose
- Graceful degradation
- Pipeline robustness

### 5. Separate Post & Comment Processing

**Design:**
- Extract from post title + content separately
- Extract from comments separately
- Combine results
- Keep source tracking for audit

**Rationale:**
- Different context and detail level
- Enables separate analysis
- Preserves data provenance

## Usage

### 1. Setup Gemini API

```bash
# Get free API key
Visit: https://aistudio.google.com/apikey

# Add to .env
GOOGLE_API_KEY=your_key_here
```

### 2. Validate Setup

```bash
uv run python validate_llm_setup.py
```

Expected output:
```
✅ Google API Key
✅ LLM Configuration
✅ Prompt Templates
✅ LLMExtractor Init
✅ Dagster Assets
✅ Live Gemini API
```

### 3. Run Extraction

```bash
# Start Dagster
docker compose up

# Visit http://localhost:3000

# Trigger llm_extraction_job
# Or end_to_end_job for complete pipeline
```

### 4. View Results

In Dagster UI, view asset outputs:
- `all_extracted_events`: List of PatientJourneyEvent objects
- `extraction_quality_metrics`: Confidence and coverage stats
- `symptom_mentions`: Focused symptom data
- `medication_mentions`: Focused medication data

## Example Output

### Input: Reddit Post

```
Title: "One year post Crohn's diagnosis"
Content: "I was diagnosed with Crohn's disease last year after 
experiencing severe abdominal pain for 6 months. My doctor tried 
mesalamine but it didn't help. Started adalimumab and symptoms 
improved within 2 weeks..."
```

### Extracted Events (7 events)

```json
[
  {
    "event_type": "symptom_onset",
    "description": "Severe abdominal pain for ~6 months",
    "mentioned_entity": "abdominal pain",
    "confidence": 0.95
  },
  {
    "event_type": "diagnosis",
    "description": "Diagnosed with Crohn's disease",
    "mentioned_entity": "Crohn's disease",
    "confidence": 0.98
  },
  {
    "event_type": "treatment_initiated",
    "description": "Doctor prescribed mesalamine",
    "mentioned_entity": "mesalamine",
    "confidence": 0.90
  },
  {
    "event_type": "treatment_outcome",
    "description": "Mesalamine did not help",
    "mentioned_entity": "mesalamine",
    "confidence": 0.85
  },
  {
    "event_type": "treatment_changed",
    "description": "Switched to adalimumab",
    "mentioned_entity": "adalimumab",
    "confidence": 0.92
  },
  {
    "event_type": "treatment_outcome",
    "description": "Symptoms improved within 2 weeks",
    "mentioned_entity": "adalimumab",
    "confidence": 0.96
  },
  {
    "event_type": "emotional_state",
    "description": "Initial needle anxiety",
    "mentioned_entity": "needle anxiety",
    "confidence": 0.75
  }
]
```

### Quality Metrics

```json
{
  "total_events": 234,
  "avg_confidence": 0.87,
  "high_confidence_count": 201,     # >= 0.8
  "medium_confidence_count": 28,    # 0.5-0.8
  "low_confidence_count": 5         # < 0.5
}
```

## Prompt Design Examples

### General Prompt
```
System: "Extract ONLY events explicitly mentioned. Do NOT hallucinate.
         Return as JSON array with confidence scores."

User: "I was diagnosed with Crohn's last year..."

Result: [{"event_type": "diagnosis", "confidence": 0.98, ...}, ...]
```

### Symptom-Focused Prompt
```
User: "I had terrible pain for months before diagnosis"

Result: {
  "symptoms": [
    {
      "name": "pain",
      "onset_mentioned": "months before diagnosis",
      "severity": "severe",
      "confidence": 0.95
    }
  ]
}
```

### Medication-Focused Prompt
```
User: "Started ibuprofen but got headaches, then switched to naproxen"

Result: {
  "medications": [
    {
      "name": "ibuprofen",
      "side_effects": ["headaches"],
      "discontinued": true,
      "confidence": 0.90
    },
    {
      "name": "naproxen",
      "side_effects": [],
      "discontinued": false,
      "confidence": 0.85
    }
  ]
}
```

## Testing

### Run Unit Tests

```bash
uv run pytest tests/test_llm_extraction.py -v
```

All 25+ tests pass:
- Model validation
- Prompt generation
- JSON parsing
- Event extraction
- Confidence filtering
- Batch processing
- Error handling

### Test Live Extraction

```bash
uv run python -c "
from mama_health.llm_extractor import LLMExtractor
from mama_health.config import AppConfig

config = AppConfig()
extractor = LLMExtractor(config)

text = 'I was diagnosed with Crohns disease 2 years ago...'
events = extractor.extract_events(
    text=text,
    source_post_id='test_001',
    min_confidence=0.5
)

print(f'Extracted {len(events)} events')
for e in events:
    print(f'  {e.event_type}: {e.description} (conf={e.confidence:.2f})')
"
```

## Configuration Tuning

### Confidence Threshold

```env
# In code: min_confidence parameter in extract_events()
# Lower = more coverage but more noise
# Higher = fewer false positives but more misses

Default: 0.5  (include moderate-confidence)
```

### Model Settings

```env
LLM_TEMPERATURE=0.3      # Lower = more deterministic
LLM_MAX_TOKENS=1000      # Response length
LLM_REQUEST_TIMEOUT=60   # Seconds to wait
```

### Cost Optimization

- Free tier: ~60 requests/minute
- For ~3000 texts: ~50 minutes
- Can process typical dataset in < 1 hour
- Batch requests for production use

## Known Limitations

### 1. Context Window
- Gemini Pro: ~30k tokens
- Workaround: Split very long posts

### 2. Informal Language
- Reddit uses slang, abbreviations
- Mitigation: LLM handles reasonably well with examples

### 3. Temporal Ambiguity
- "For ages" vs "for 3 months" both vague
- Mitigation: Captured in temporal_indicators field

### 4. Medication Names
- Brand vs generic, spelling variations
- Mitigation: Can add post-processing validation

### 5. False Positives
- LLM may misinterpret figurative language
- Mitigation: Confidence filtering, human review for < 0.7

## Next Steps

1. **Patient Journey Analytics** (Phase 3)
   - Timeline analysis: symptom-to-diagnosis duration
   - Treatment efficacy: medication outcomes
   - Symptom co-occurrence mapping
   - Medication side effect associations

2. **Data Storage**
   - PostgreSQL persistence
   - Historical tracking
   - Query interface

3. **Scaling**
   - Batch API requests
   - Parallel processing
   - Scheduled runs

4. **Improvement**
   - Refine prompts based on results
   - Add medical term validation
   - Human-in-the-loop feedback loop

## Files Summary

```
src/mama_health/
├── prompts.py              # Prompt templates (450 lines)
├── llm_extractor.py        # Extraction service (350 lines)
└── assets/
    └── llm_extraction.py   # Dagster assets (250 lines)

tests/
└── test_llm_extraction.py  # Unit tests (350 lines)

validate_llm_setup.py       # Setup validation (300 lines)
LLM_EXTRACTION.md           # Full documentation (~600 lines)
```

## Quality Metrics

- **Test Coverage**: 25+ unit tests, all passing
- **Code Quality**: Pydantic validation, type hints, comprehensive logging
- **Error Handling**: Graceful failures, detailed error messages
- **Documentation**: Inline comments, docstrings, comprehensive guides
- **Reproducibility**: Works with `.env`, Docker Compose, `uv`

## Support

### Debugging

```bash
# Validate setup
uv run python validate_llm_setup.py

# Check logs
docker compose logs -f dagster-daemon

# Test extraction directly
uv run python -c "...see testing section..."
```

### Common Issues

**Missing GOOGLE_API_KEY**
- Get from: https://aistudio.google.com/apikey
- Add to `.env`

**API Rate Limit**
- Free tier: 60 requests/minute
- Check request timing, consider batching

**JSON Parse Errors**
- LLM response structure changed
- Check logs for actual response
- May need prompt adjustment

**Timeout**
- Increase LLM_REQUEST_TIMEOUT
- Check internet connection
- Verify API key is valid

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **LLM Framework** | litellm | 1.40+ |
| **Model** | Google Gemini | Pro |
| **Data Validation** | Pydantic | 2.0+ |
| **Orchestration** | Dagster | 1.7+ |
| **Testing** | pytest | 7.4+ |
| **Language** | Python | 3.11+ |

## References

- **Prompts**: `src/mama_health/prompts.py`
- **Extraction Logic**: `src/mama_health/llm_extractor.py`
- **Assets**: `src/mama_health/assets/llm_extraction.py`
- **Models**: `src/mama_health/models.py`
- **Tests**: `tests/test_llm_extraction.py`
- **Documentation**: `LLM_EXTRACTION.md`
