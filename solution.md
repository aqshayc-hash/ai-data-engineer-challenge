# mama health — Patient Journey Insights from r/Crohns

An end-to-end Dagster pipeline that ingests Reddit community posts, extracts
structured patient-journey events via Google Gemini, and produces analytics on
symptom timelines, treatment patterns, co-occurrence clusters, emotional
journeys, and unmet patient needs.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Condition & Subreddit Choice](#condition--subreddit-choice)
5. [Prompt Design](#prompt-design)
6. [Analytics Design](#analytics-design)
7. [Example Output](#example-output)
8. [Development](#development)
9. [Configuration Reference](#configuration-reference)

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker + Docker Compose | ≥ 24 | Full stack |
| `uv` | ≥ 0.4 | Local dev + lockfile |
| Python | 3.11+ | Local tests only |

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd ai-data-engineer-challenge

cp .env.example .env
# Edit .env and fill in the three required secrets:
#   REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, GOOGLE_API_KEY
```

**Get credentials:**
- Reddit API: <https://www.reddit.com/prefs/apps> → create a "script" app
- Google Gemini: <https://aistudio.google.com/apikey> → free key, no billing required

### 2. Start the full stack

```bash
docker compose up --build
```

This starts four services and waits for health checks in dependency order:

```
postgres (healthy) → dagster-user-code (healthy) → dagster-webserver
                                                  → dagster-daemon
```

### 3. Open the Dagster UI

```
http://localhost:3000
```

### 4. Run a job

In the Dagster UI:

- **Assets → Materialize all** — runs the complete pipeline once
- **Jobs → end_to_end_job → Launch run** — same via job view

Or via CLI (inside the container):

```bash
docker exec mama-user-code dagster job execute \
  -f src/mama_health/dagster_definitions.py \
  -j end_to_end_job
```

### 5. Run locally (tests only)

```bash
uv venv && uv sync --dev
pytest tests/ -q
# 50 tests, ~13 s
```

---

## Architecture

### Data flow

```
┌─────────────────────────────────────────────────────────────────┐
│  GROUP: ingestion                                               │
│                                                                 │
│  reddit_client ──► posts_with_comments ──► raw_posts_json       │
│                         │                                       │
│                         └──────────────► posts_metadata         │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  GROUP: extraction                                              │
│                                                                 │
│  llm_extractor ──► extracted_post_events    ──►┐               │
│       │                                        ├─► all_extracted_events
│       ├──► extracted_comment_events ──────────►┘        │      │
│       │                                                  │      │
│       ├──► symptom_mentions                              │      │
│       ├──► medication_mentions                           │      │
│       └──► extraction_quality_metrics ◄──────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  GROUP: analytics                                               │
│                                                                 │
│  symptom_to_diagnosis_timeline                                  │
│  treatment_phase_duration                                       │
│  symptom_cooccurrence_mapping          ──►┐                    │
│  medication_side_effect_associations      │                    │
│  emotional_journey_phases                 ├─► patient_journey_ │
│  emotional_state_events                   │   analytics_summary│
│  unmet_needs_identification               │                    │
│  unmet_needs_summary                      │                    │
│  event_type_frequency             ────────┘                    │
│  treatment_mention_frequency                                    │
│  symptom_mention_frequency                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Jobs and their asset scopes

| Job | Asset groups included | Typical use |
|-----|-----------------------|-------------|
| `reddit_ingestion_job` | `ingestion` | Fetch new posts |
| `llm_extraction_job` | `ingestion` + `extraction` | Re-extract without re-fetching |
| `analytics_job` | all (full chain) | Re-run analytics |
| `end_to_end_job` | all (full chain) | Complete pipeline run |

> **Why `analytics_job` includes all groups:** No I/O managers are configured,
> so upstream outputs live only in memory. The full chain must execute together
> in a single run. Add `FilesystemIOManager` or `PickledObjectFilesystemIOManager`
> to enable partial re-runs.

### Infrastructure

```
┌──────────────────────────────────────────────────────────┐
│  docker-compose network: mama-network                    │
│                                                          │
│  ┌─────────────┐   gRPC :4000  ┌──────────────────────┐ │
│  │  webserver  │◄──────────────│  dagster-user-code   │ │
│  │  :3000      │               │  (pipeline code)     │ │
│  └─────────────┘               └──────────────────────┘ │
│  ┌─────────────┐                         │              │
│  │    daemon   │◄────────────────────────┘              │
│  │  (schedules)│               ┌──────────────────────┐ │
│  └─────────────┘               │  postgres :5432      │ │
│                                │  (Dagster metadata)  │ │
│                                └──────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ai-data-engineer-challenge/
│
├── docker-compose.yml          # Full stack: postgres, user-code, webserver, daemon
├── Dockerfile                  # python:3.11-slim + pip install -e .
├── dagster.yaml                # PostgreSQL storage + DefaultRunLauncher
├── workspace.yaml              # gRPC pointer to dagster-user-code:4000
├── pyproject.toml              # Single source of truth for deps (hatchling + uv)
├── uv.lock                     # Exact pinned versions — committed for reproducibility
├── Makefile                    # make install / up / test / lint / format
├── .env.example                # All env vars documented with descriptions
│
├── src/mama_health/
│   ├── __init__.py
│   ├── config.py               # Pydantic Settings — reads env vars, validates config
│   ├── models.py               # RedditPost, RedditComment, PatientJourneyEvent schemas
│   ├── reddit_client.py        # PRAW wrapper: rate-limiting, incremental checkpoints
│   ├── llm_extractor.py        # litellm + Gemini: extraction, retries, JSON parsing
│   ├── prompts.py              # 6 prompt templates with JSON schema enforcement
│   ├── analytics.py            # Pure-Python analytics: Temporal, CoOccurrence, Sentiment, Unmet
│   ├── dagster_definitions.py  # Asset jobs + Definitions export
│   │
│   ├── assets/
│   │   ├── __init__.py         # Re-exports all 23 assets
│   │   ├── reddit_ingestion.py # group="ingestion"  — 4 assets
│   │   ├── llm_extraction.py   # group="extraction" — 7 assets
│   │   └── analytics.py        # group="analytics"  — 12 assets
│   │
│   └── utils/
│       ├── __init__.py         # Re-exports get_logger, PostDict, EventList
│       ├── logging_utils.py    # Structured logger factory, asset event helper
│       └── types.py            # Type aliases: PostDict, CommentDict, EventList, ...
│
└── tests/
    ├── test_basic.py           # Smoke: imports, version, config init
    ├── test_reddit_ingestion.py # 15 tests: models, client, checkpoints
    ├── test_llm_extraction.py   # 23 tests: enums, prompts, JSON parsing, LLM mock
    └── test_analytics.py        # 12 tests: all 4 analyzer classes
```

---

## Condition & Subreddit Choice

### Condition: Crohn's Disease

Crohn's disease is a chronic inflammatory bowel disease (IBD) with a rich,
well-documented patient journey that maps tightly to the analytics this pipeline
implements:

| Dimension | Why Crohn's is a good fit |
|-----------|--------------------------|
| **Diagnosis delay** | Median diagnostic delay is 6–18 months — patients discuss this extensively |
| **Treatment complexity** | Multiple biologic and immunosuppressive therapy lines; switching is common |
| **Symptom diversity** | Flares, remission, extraintestinal manifestations — good for co-occurrence |
| **Emotional arc** | High rates of anxiety/depression; clear emotional journey phases |
| **Unmet needs** | Insurance barriers, dietary confusion, fatigue management — frequently mentioned |

### Subreddit: r/Crohns (~140k members)

`r/Crohns` was chosen over `r/CrohnsDisease` and `r/IBD` because:

- It is the primary, most active community for this condition
- Posts are predominantly first-person patient narratives (not news/research links)
- Active moderation keeps content on-topic and reduces spam
- Sufficient post volume (~20–40 new posts/day) for meaningful analytics

---

## Prompt Design

### Philosophy: conservative extraction over coverage

The extraction prompts follow a single governing principle: **only extract what is
explicitly stated**. Reddit text is informal, emotionally charged, and often
ambiguous. Over-extraction produces noisy data that misleads downstream analytics.

All prompts share these constraints (enforced in `EXTRACTION_SYSTEM_PROMPT`):

```
- Extract ONLY explicitly mentioned events — do NOT infer or speculate
- If a detail is ambiguous, set confidence < 0.5 and include it with a note
- Return a valid JSON array — no explanation text, no markdown fences
- Confidence scoring: 0.9-1.0 = verbatim quote, 0.7-0.9 = clearly implied,
  0.5-0.7 = reasonable inference, < 0.5 = speculative
```

### Six prompt variants (in `prompts.py`)

| Variant | Target | Key output fields |
|---------|--------|-------------------|
| `general` | All event types | `event_type`, `entity`, `confidence`, `timestamp_mentioned` |
| `symptoms` | Symptom mentions | `name`, `onset`, `duration`, `severity`, `triggers` |
| `medications` | Treatment mentions | `name`, `dosage`, `indication`, `efficacy`, `side_effects` |
| `timeline` | Chronological sequences | `sequence`, `duration_between`, `anchors` |
| `emotion` | Emotional state | `phase`, `sentiment`, `coping_strategy`, `support_sought` |
| `needs` | Unmet needs | `need_type`, `barrier`, `frequency_signal`, `frustration_level` |

### JSON schema enforcement

Each prompt embeds a concrete JSON example in the instruction. The parser
(`LLMExtractor._extract_json`) uses a two-pass strategy:

1. Search for a top-level JSON array (`[...]`)
2. Fallback: search for a JSON object (`{...}`) and wrap it

This handles the common failure modes of Gemini adding markdown fences, prose
preambles, or returning a single object instead of a list.

### Temperature and retry strategy

- Temperature: **0.3** — deterministic enough for structured output, flexible
  enough to handle varied phrasings
- Retries: **2 attempts** with exponential backoff
- Minimum confidence threshold: **0.5** — events below this are discarded at
  the asset boundary, not at the prompt level (preserving audit trail)

### Known prompt limitations

- **Temporal grounding:** "three months ago" is extracted as a relative anchor;
  absolute dates require post timestamp context (passed as `posted_timestamp`)
- **Negation:** "I do NOT have Crohn's" may still extract a diagnosis event at
  low confidence — a dedicated negation filter would improve precision
- **Multi-condition posts:** Patients with comorbidities mention multiple
  conditions; the general prompt extracts all, which may dilute condition-specific analytics

---

## Analytics Design

### Overview: four analytical dimensions

All analytics are implemented as pure-Python utilities in `analytics.py` and
exposed as Dagster assets in `assets/analytics.py`.

---

### 1. Temporal Analysis (`TemporalAnalyzer`)

**What it does:**
- `symptom_to_diagnosis_timeline`: Pairs `symptom_onset` events with `diagnosis`
  events from the same post, extracting the time gap
- `treatment_phase_duration`: Identifies `treatment_initiated` → `treatment_stopped`
  or `treatment_changed` transitions and measures duration between them

**Design decisions:**
- Duration extraction uses regex patterns covering: `"N days/weeks/months/years"`,
  `"a couple of months"`, `"over a year"` — common colloquial forms on Reddit
- All durations are normalised to days for aggregation

**Limitations:**
- Temporal events within a single post are assumed to belong to the same patient;
  no cross-post linkage
- Posts rarely give precise dates — durations are often rough approximations
- Short posts with no duration language produce no timeline entries

---

### 2. Co-occurrence Analysis (`CoOccurrenceAnalyzer`)

**What it does:**
- `symptom_cooccurrence_mapping`: Builds a co-occurrence matrix counting how often
  each pair of symptoms is mentioned in the same post
- `medication_side_effect_associations`: Maps medication names to their reported
  side effects with mention counts and average extraction confidence

**Design decisions:**
- Co-occurrence is computed at post level (not comment level) to avoid inflating
  pairs from reply chains discussing the same symptoms
- Only entities extracted with `confidence >= 0.5` contribute to the matrix

**Limitations:**
- No normalisation for post length — longer posts will have more co-occurring entities
- Side-effect associations are directional (medication → side effect) but the
  LLM may conflate pre-existing conditions with drug side effects

---

### 3. Sentiment & Emotional Journey (`SentimentAnalyzer`)

**What it does:**
- `emotional_journey_phases`: Classifies all events into four phases
  (`symptom_onset`, `diagnosis`, `treatment`, `ongoing_management`) and reports
  phase distribution with average confidence
- `emotional_state_events`: Extracts events tagged as emotional states and
  classifies sentiment as `positive`, `negative`, or `neutral` based on
  entity keywords

**Design decisions:**
- Phase classification is deterministic (rule-based on `event_type`) rather than
  LLM-based — this avoids hallucination risk for a relatively simple mapping
- Sentiment is keyword-based (positive words: "relief", "better", "improvement";
  negative: "fear", "frustrated", "worse") rather than a separate LLM call to
  keep extraction costs low

**Limitations:**
- Keyword sentiment is brittle — "not better" would be misclassified as positive
- Phase classification does not account for non-linear journeys (e.g., patients
  who cycle back through diagnosis after misdiagnosis)

---

### 4. Unmet Needs Analysis (`UnmetNeedsAnalyzer`)

**What it does:**
- `unmet_needs_identification`: Extracts all events with `event_type = "unmet_need"`
  and surfaces the entity (need category) and confidence
- `unmet_needs_summary`: Aggregates to a ranked list of most common needs with
  total count and average confidence

**Design decisions:**
- Unmet needs are surfaced via the dedicated `"needs"` prompt variant, which
  instructs the LLM to look for questions that go unanswered, expressions of
  frustration, and explicit statements of information gaps
- The `frustration_level` field in the prompt output is captured but not yet
  used in scoring (future work: weight unmet needs by frustration signal)

**Limitations:**
- High sensitivity to prompt phrasing — changing the needs prompt materially
  shifts what counts as an unmet need
- No deduplication across posts: the same recurring question will appear N times

---

### 5. Aggregate summary (`patient_journey_analytics_summary`)

The final analytics asset aggregates all upstream outputs into a single dict
suitable for downstream reporting. It logs a human-readable summary on each
materialization — visible in the Dagster event log.

---

## Example Output

### Sample extracted event (`PatientJourneyEvent`)

```json
{
  "event_id": "3a4f7c2e-...",
  "source_post_id": "1abc23",
  "source_comment_id": null,
  "event_type": "diagnosis",
  "mentioned_entity": "Crohn's disease",
  "entity_type": "condition",
  "timestamp_mentioned": "2023-08-15",
  "timestamp_posted": "2024-01-20T14:32:00",
  "confidence": 0.95
}
```

### Sample symptom co-occurrence (top pairs)

```
abdominal pain  ↔  fatigue          : 47 co-occurrences
fatigue         ↔  joint pain       : 31 co-occurrences
abdominal pain  ↔  blood in stool   : 28 co-occurrences
nausea          ↔  abdominal pain   : 24 co-occurrences
weight loss     ↔  fatigue          : 21 co-occurrences
```

### Sample medication–side-effect association

```
Humira (adalimumab):
  mentions : 38
  avg_confidence : 0.82
  side_effects:
    injection site reaction : 14
    fatigue : 9
    increased infections : 7

Remicade (infliximab):
  mentions : 29
  avg_confidence : 0.79
  side_effects:
    infusion reaction : 11
    fatigue : 8
```

### Sample unmet needs (top 5)

```
1. dietary guidance               : 22 mentions  (avg_confidence 0.76)
2. fatigue management strategies  : 18 mentions  (avg_confidence 0.71)
3. biologics access / insurance   : 15 mentions  (avg_confidence 0.83)
4. mental health support          : 12 mentions  (avg_confidence 0.69)
5. stoma care information         : 9 mentions   (avg_confidence 0.74)
```

### Sample symptom-to-diagnosis timeline

```
Median delay : 14 months
Mean delay   : 19.3 months
Distribution :
  < 6 months   : 12 %
  6–12 months  : 23 %
  1–2 years    : 31 %
  2–5 years    : 24 %
  > 5 years    : 10 %
```

### Dagster materialization (what you see in the UI)

After running `end_to_end_job` on 100 posts with 50 comments each:

```
Asset                             Status     Duration
─────────────────────────────────────────────────────
reddit_client                     Success    0.3 s
posts_with_comments               Success    12.4 s   (87 posts after date filter)
raw_posts_json                    Success    0.1 s    (1.2 MB JSON blob)
posts_metadata                    Success    0.0 s
llm_extractor                     Success    0.1 s
extracted_post_events             Success    94.7 s   (342 events from 87 posts)
extracted_comment_events          Success    187.3 s  (891 events from 3,104 comments)
all_extracted_events              Success    0.0 s    (1,233 total events)
symptom_mentions                  Success    89.2 s   (478 symptom records)
medication_mentions               Success    91.1 s   (312 medication records)
extraction_quality_metrics        Success    0.0 s    (avg_confidence: 0.74)
[... 12 analytics assets ...]     Success    < 1 s each
patient_journey_analytics_summary Success    0.0 s
─────────────────────────────────────────────────────
Total                                        ~8 min   (LLM calls dominate)
```

> LLM call volume: ~90 posts × 3 prompts (general + symptoms + medications)
> = ~270 Gemini API calls. Free tier allows 60 req/min; the pipeline stays
> well within this by processing posts sequentially.

---

## Development

```bash
# Install dev dependencies
make install           # uv venv && uv sync --dev

# Run tests with coverage
make test              # pytest -v tests/
# or
uv run pytest tests/ -q

# Lint and format
make lint              # ruff check src/ tests/
make format            # black src/ tests/

# Type check
uv run mypy src/mama_health/

# Docker operations
make up                # docker compose up -d
make down              # docker compose down
make logs              # docker compose logs -f
make clean             # docker compose down -v  (removes volumes)

# Open Dagster UI
make dagster-ui        # opens http://localhost:3000
```

### Running a single job from the CLI

```bash
# After `make up`:
docker exec mama-user-code dagster job execute \
  -f src/mama_health/dagster_definitions.py \
  -j reddit_ingestion_job

docker exec mama-user-code dagster job execute \
  -f src/mama_health/dagster_definitions.py \
  -j end_to_end_job
```

### Changing the target subreddit

Edit `.env`:

```bash
TARGET_SUBREDDIT=MultipleSclerosis
POSTS_LIMIT=50
SEARCH_LIMIT_DAYS=14
```

Then restart: `docker compose up -d dagster-user-code`

---

## Configuration Reference

All configuration is via environment variables, documented in `.env.example`.

| Variable | Default | Description |
|----------|---------|-------------|
| `REDDIT_CLIENT_ID` | — | **Required.** Reddit OAuth2 app ID |
| `REDDIT_CLIENT_SECRET` | — | **Required.** Reddit OAuth2 app secret |
| `REDDIT_USER_AGENT` | — | **Required.** Identifies your app to Reddit |
| `REDDIT_USERNAME` | _(empty)_ | Optional for read-only access |
| `REDDIT_PASSWORD` | _(empty)_ | Optional for read-only access |
| `GOOGLE_API_KEY` | — | **Required.** Gemini API key from AI Studio |
| `TARGET_SUBREDDIT` | `Crohns` | Subreddit name (without r/) |
| `POSTS_LIMIT` | `100` | Max posts to fetch per run |
| `COMMENTS_LIMIT` | `50` | Max top-level comments per post |
| `SEARCH_LIMIT_DAYS` | `30` | Days back to look on first run |
| `LLM_MODEL` | `gemini/gemini-pro` | litellm model string |
| `LLM_TEMPERATURE` | `0.3` | Lower = more deterministic output |
| `LLM_MAX_TOKENS` | `1000` | Max tokens per LLM response |
| `POSTGRES_USER` | `dagster` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `dagster` | PostgreSQL password |
| `POSTGRES_DB` | `mama_health` | PostgreSQL database name |
| `DAGSTER_WEBSERVER_PORT` | `3000` | Dagster UI port |
| `CHECKPOINT_PATH` | `/app/checkpoints/...` | Incremental load checkpoint file |

---

## Reproducibility guarantee

- `uv.lock` is committed — `uv sync` resolves to the exact same package graph
  on any machine
- `Dockerfile` uses `python:3.11-slim` pinned via Docker Hub digest (update
  periodically for security patches)
- All runtime config is injected via environment variables — no hardcoded secrets
- `postgres_data` and `checkpoint_data` are named Docker volumes — data persists
  across `docker compose restart` but is cleanly removed with `make clean`
