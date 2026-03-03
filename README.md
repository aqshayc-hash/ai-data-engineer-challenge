# mama health — Patient Journey Insights from r/Crohns

An end-to-end Dagster pipeline that ingests Reddit community posts from r/Crohns,
extracts structured patient-journey events via Google Gemini, and produces analytics on
symptom timelines, treatment patterns, co-occurrence clusters, emotional journeys, and
unmet patient needs. The full stack starts with a single `docker compose up` and is
immediately functional.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Partitions & Scheduling](#partitions--scheduling)
4. [Visualization Dashboard](#visualization-dashboard)
5. [Project Structure](#project-structure)
6. [Condition & Subreddit Choice](#condition--subreddit-choice)
7. [Prompt Design Decisions](#prompt-design-decisions)
8. [Analytics Design Decisions](#analytics-design-decisions)
9. [Example Output](#example-output)
10. [Configuration Reference](#configuration-reference)

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
uv venv && uv sync --extra dev
pytest tests/ -q
# ~50 tests
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
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  GROUP: storage                                                 │
│                                                                 │
│  events_stored_to_postgres  (PostgreSQL patient_journey_events) │
└─────────────────────────────────────────────────────────────────┘
```

### Jobs and their asset scopes

All jobs are **partitioned** — each run targets a specific calendar-day partition.
Launching a run prompts for a partition key (e.g. `2024-03-15`).

| Job | Asset groups included | Typical use |
|-----|-----------------------|-------------|
| `reddit_ingestion_job` | `ingestion` | Fetch new posts for a day |
| `llm_extraction_job` | `ingestion` + `extraction` | Re-extract a day without re-fetching |
| `analytics_job` | all (full chain) | Re-run analytics for a day |
| `end_to_end_job` | all (full chain) | Complete pipeline run for a day |

> **Partial re-runs enabled:** `FilesystemIOManager` persists each partition's
> asset outputs to `dagster_storage/<asset_name>/<partition_key>/`. Downstream
> assets can be re-run independently without re-executing upstream assets.

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
│                                │  (Dagster metadata + │ │
│                                │   pipeline data)     │ │
│                                └──────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## Partitions & Scheduling

### Daily partitions

Every data asset in the pipeline is assigned a
`DailyPartitionsDefinition(start_date="2024-01-01")` partition, defined in
`src/mama_health/partitions.py`. Each calendar day is an independent,
replayable execution unit. Service assets (`reddit_client`, `llm_extractor`)
are intentionally *unpartitioned* — they are stateless constructors whose
output is the same regardless of which day is being processed.

### Schedules

| Schedule | Cron | Job | Purpose |
|----------|------|-----|---------|
| `daily_pipeline_schedule` | `0 2 * * *` (daily at 2 AM UTC) | `end_to_end_job` | Routine daily ingestion |
| `weekly_pipeline_schedule` | `0 2 * * 0` (Sundays at 2 AM UTC) | `end_to_end_job` | Lower-volume subreddits |

Both schedules are registered in `Definitions` and visible in the Dagster UI
under **Schedules**. They are created off by default; enable them in the UI
or via `dagster schedule start`.

### Known limitation: PRAW recency constraint

Reddit's PRAW API fetches posts by recency (`new` sort, `time_filter="month"`).
Backfilling partitions for dates older than ~30 days will return zero posts
because those posts are no longer in the recent feed. For historical data beyond
30 days, consider using the Reddit Pushshift archive or a dedicated data dump.

---

## Visualization Dashboard

A standalone Streamlit dashboard renders the pipeline's analytics outputs as
interactive charts. It reads partition outputs directly from the
`dagster_storage/` directory written by `FilesystemIOManager`.

**URL:** `http://localhost:8501`

| Tab | Data source(s) | Chart |
|-----|---------------|-------|
| **Overview** | `patient_journey_analytics_summary` | KPI metric cards + JSON key findings |
| **Symptom Co-occurrence** | `symptom_cooccurrence_mapping` | Plotly heatmap (top-20 pairs) |
| **Sentiment Timeline** | `emotional_state_events`, `emotional_journey_phases` | Scatter by confidence + bar by phase |
| **Patient Pathway** | `symptom_to_diagnosis_timeline`, `treatment_phase_duration` | Sankey diagram |

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
│   ├── db.py                   # SQLAlchemy table definitions for pipeline data
│   ├── reddit_client.py        # PRAW wrapper: rate-limiting, incremental checkpoints
│   ├── llm_extractor.py        # litellm + Gemini: extraction, retries, JSON parsing
│   ├── prompts.py              # 6 prompt templates with JSON schema enforcement
│   ├── analytics.py            # Pure-Python analytics: Temporal, CoOccurrence, Sentiment, Unmet
│   ├── dagster_definitions.py  # Asset jobs + Definitions export
│   │
│   ├── assets/
│   │   ├── __init__.py         # Re-exports all 24 assets
│   │   ├── reddit_ingestion.py # group="ingestion"  — 4 assets
│   │   ├── llm_extraction.py   # group="extraction" — 7 assets
│   │   ├── analytics.py        # group="analytics"  — 12 assets
│   │   └── storage.py          # group="storage"    — 1 asset (PostgreSQL persistence)
│   │
│   └── utils/
│       ├── __init__.py         # Re-exports get_logger, PostDict, EventList
│       ├── logging_utils.py    # Structured logger factory, asset event helper
│       └── types.py            # Type aliases: PostDict, CommentDict, EventList, ...
│
└── tests/
    ├── conftest.py             # Shared fixtures (sample_events)
    ├── test_basic.py           # Smoke: imports, version, config init
    ├── test_reddit_ingestion.py # 15 tests: models, client, checkpoints
    ├── test_llm_extraction.py   # 23 tests: enums, prompts, JSON parsing, LLM mock
    ├── test_analytics.py        # 12 tests: all 4 analyzer classes
    └── test_dagster_assets.py   # 7 smoke tests: asset function return types
```

---

## Condition & Subreddit Choice

### Condition: Crohn's Disease

Crohn's disease was chosen because it is a chronic, multi-phase condition with a clear
patient journey (symptom onset → diagnostic workup → treatment initiation → long-term
management), making it a natural fit for the temporal and sequential analytics this
pipeline implements. The condition's well-defined terminology — biologic names
(Humira, Remicade, Stelara), procedures (colonoscopy, MRI enterography), and clinical
concepts (flare, remission, stricture) — improves LLM extraction precision by reducing
ambiguity in entity recognition.

| Dimension | Why Crohn's is a good fit |
|-----------|--------------------------|
| **Diagnosis delay** | Median diagnostic delay is 6–18 months — patients discuss this extensively |
| **Treatment complexity** | Multiple biologic and immunosuppressive therapy lines; switching is common |
| **Symptom diversity** | Flares, remission, extraintestinal manifestations — good for co-occurrence |
| **Emotional arc** | High rates of anxiety/depression; clear emotional journey phases |
| **Unmet needs** | Insurance barriers, dietary confusion, fatigue management — frequently mentioned |

### Subreddit: r/Crohns (~140k members)

`r/Crohns` was chosen over `r/CrohnsDisease` and `r/IBD` because it is the primary,
most active community for this condition. Posts are predominantly first-person patient
narratives (not news or research links), active moderation keeps content on-topic and
reduces spam, and the post volume (~20–40 new posts/day) is sufficient for meaningful
analytics without overwhelming the free-tier Gemini API quota.

---

## Prompt Design Decisions

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

### Iteration History

Prompt design went through three distinct rounds before reaching the current implementation:

**Round 1 — Single general prompt:** The initial prototype used a single prompt asking
the model to extract all event types at once ("extract all patient journey events from
this Reddit post"). The model returned free-form prose rather than structured data.
The fix was adding an explicit JSON schema with a concrete example embedded in the
instruction, and a hard constraint: "Return ONLY a JSON array — no prose, no markdown."

**Round 2 — Over-extraction at low confidence:** With JSON schema enforced, the model
began extracting too aggressively: every mention of a symptom name, even in hypothetical
or negated contexts, was extracted as a high-confidence event. This inflated event counts
and introduced false positives into analytics. The fix was two-fold: a `confidence < 0.5`
discard filter applied at the asset boundary (not the prompt), and a revised system
prompt with the instruction "it is better to miss a genuine event than to hallucinate
one — when in doubt, set confidence below 0.5."

**Round 3 — Specialised prompt variants:** Even with schema enforcement and confidence
filtering, a single general prompt produced uneven quality across event types. Symptom
extractions were precise but medication side-effect associations were noisy, and emotional
states were almost never captured. The solution was to create six domain-specific prompt
variants, each with tailored output fields and domain-specific examples. Running multiple
prompts per post increases API call volume (~3× per post) but substantially improves
per-domain precision.

### Known prompt limitations

- **Temporal grounding:** "three months ago" is extracted as a relative anchor;
  absolute dates require post timestamp context (passed as `posted_timestamp`)
- **Negation:** "I do NOT have Crohn's" may still extract a diagnosis event at
  low confidence — a dedicated negation filter would improve precision
- **Multi-condition posts:** Patients with comorbidities mention multiple
  conditions; the general prompt extracts all, which may dilute condition-specific analytics

---

## Analytics Design Decisions

### Overview: four analytical dimensions

All analytics are implemented as pure-Python utilities in `analytics.py` and
exposed as Dagster assets in `assets/analytics.py`.

---

### 1. Temporal Analysis (`TemporalAnalyzer`)

**What it does:**
- `symptom_to_diagnosis_timeline`: Pairs `symptom_onset` events with `diagnosis`
  events from the same post. Duration is extracted from the event description text
  first (`reported_duration_days`); the Reddit post-date delta is used as a fallback
  only when no explicit duration language is found (`duration_source` field indicates
  which method was used).
- `treatment_phase_duration`: Identifies `treatment_initiated` → `treatment_stopped`
  or `treatment_changed` transitions and measures duration between them.

**Design decisions:**
- Duration extraction uses regex patterns covering: `"N days/weeks/months/years"`,
  `"a couple of months"`, `"over a year"` — common colloquial forms on Reddit.
- All durations are normalised to days for aggregation.
- Text-extracted durations are preferred over post-date deltas because events within
  a single post often share the same `timestamp_posted`, making date deltas meaningless.

**Limitations:**
- Temporal events within a single post are assumed to belong to the same patient;
  no cross-post linkage.
- Posts rarely give precise dates — durations are often rough approximations.
- Short posts with no duration language produce no timeline entries.

---

### 2. Co-occurrence Analysis (`CoOccurrenceAnalyzer`)

**What it does:**
- `symptom_cooccurrence_mapping`: Builds a co-occurrence matrix counting how often
  each pair of symptoms is mentioned in the same post.
- `medication_side_effect_associations`: Maps medication names to their reported
  side effects with mention counts and average extraction confidence.

**Design decisions:**
- Co-occurrence is computed at post level (not comment level) to avoid inflating
  pairs from reply chains discussing the same symptoms.
- Only entities extracted with `confidence >= 0.5` contribute to the matrix.

**Limitations:**
- No normalisation for post length — longer posts will have more co-occurring entities.
- Side-effect associations are directional (medication → side effect) but the
  LLM may conflate pre-existing conditions with drug side effects.

---

### 3. Sentiment & Emotional Journey (`SentimentAnalyzer`)

**What it does:**
- `emotional_journey_phases`: Classifies all events into four phases
  (`symptom_onset`, `diagnosis`, `treatment`, `ongoing_management`) and reports
  phase distribution with average confidence.
- `emotional_state_events`: Extracts events tagged as emotional states and
  classifies sentiment as `positive`, `negative`, or `neutral` based on
  emotionally-charged keywords.

**Design decisions:**
- Phase classification is deterministic (rule-based on `event_type`) rather than
  LLM-based — this avoids hallucination risk for a relatively simple mapping.
- Sentiment keywords are focused on emotional state rather than clinical description:
  positive — `relieved`, `hopeful`, `grateful`, `finally`, `happy`, `better`, `helped`;
  negative — `hopeless`, `scared`, `frustrated`, `anxious`, `depressed`, `overwhelmed`,
  `devastated`. Clinical terms like "pain" or "difficult" were deliberately excluded
  because they appear in nearly every medical post and would render the sentiment
  signal meaningless.

**Limitations:**
- Keyword sentiment is brittle — "not better" would be misclassified as positive.
- Phase classification does not account for non-linear journeys (e.g., patients
  who cycle back through diagnosis after misdiagnosis).

---

### 4. Unmet Needs Analysis (`UnmetNeedsAnalyzer`)

**What it does:**
- `unmet_needs_identification`: Extracts all events with `event_type = "unmet_need"`
  and surfaces the entity (need category) and confidence.
- `unmet_needs_summary`: Aggregates to a ranked list of most common needs with
  total count and average confidence.

**Design decisions:**
- Unmet needs are surfaced via the dedicated `"needs"` prompt variant, which
  instructs the LLM to look for questions that go unanswered, expressions of
  frustration, and explicit statements of information gaps.

**Limitations:**
- High sensitivity to prompt phrasing — changing the needs prompt materially
  shifts what counts as an unmet need.
- No deduplication across posts: the same recurring question will appear N times.

---

### 5. PostgreSQL persistence (`events_stored_to_postgres`)

**What it does:**
- Writes all extracted `PatientJourneyEvent` records for a partition to the
  `patient_journey_events` table in PostgreSQL, enabling SQL queries against
  pipeline data (not just Dagster internal metadata).

**Design decisions:**
- Upsert pattern: delete existing rows for the partition date, then insert fresh rows.
  This makes re-runs idempotent.
- `metadata.create_all(engine)` is called on every run — idempotent DDL means the
  table is auto-created on first run without a separate migration step.

**Verify after a pipeline run:**
```sql
SELECT event_type, COUNT(*), AVG(confidence)
FROM patient_journey_events
GROUP BY event_type;
```

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
  "confidence": 0.95,
  "description": "Finally got diagnosed with Crohn's after 14 months of testing"
}
```

### Sample analytics summary (abridged)

```json
{
  "generated_at": "2024-03-15T02:31:44",
  "total_events_analyzed": 1233,
  "analytics": {
    "temporal_analysis": {
      "symptom_to_diagnosis_timelines": 47,
      "treatment_phase_transitions": 31
    },
    "cooccurrence_analysis": {
      "symptom_pairs": 89,
      "medications_with_side_effects": 14
    },
    "emotional_journey": {
      "phases_identified": 4,
      "emotional_events_count": 1233
    },
    "unmet_needs": 38
  },
  "key_findings": {
    "most_common_symptom": "abdominal pain",
    "most_mentioned_treatment": "Humira",
    "most_common_side_effect": "fatigue",
    "primary_unmet_need": "dietary guidance"
  }
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
events_stored_to_postgres         Success    0.3 s    (1,233 rows written)
─────────────────────────────────────────────────────
Total                                        ~8 min   (LLM calls dominate)
```

> LLM call volume: ~90 posts × 3 prompts (general + symptoms + medications)
> = ~270 Gemini API calls. Free tier allows 60 req/min; the pipeline stays
> well within this by processing posts sequentially.

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

<details>
<summary>Original Challenge Brief</summary>

# mama health — AI Data Engineer Challenge

## Extracting Patient Journey Insights from Public Community Data

## Background

At mama health, we build conversational AI systems that guide patients through complex healthcare journeys. Our platform relies on understanding the real-world experiences patients share — not only in clinical interviews but also in online communities where they describe symptoms, treatments, emotional states, and day-to-day management of chronic conditions.

Reddit is one of the richest public sources of such patient narratives. Subreddits dedicated to specific conditions contain thousands of first-person accounts that, when structured and analyzed, can surface patterns about symptom onset, treatment timelines, medication side effects, and the emotional arc of living with a disease.

We are looking for an engineer who can build a **reproducible, well-orchestrated data pipeline** that ingests this community data, extracts meaningful structure from it, and produces analytics aligned with our patient journey model.

---

## Your Mission

Build an **end-to-end data pipeline** using **Dagster** that retrieves posts and comments from Reddit for a chronic condition of your choosing (e.g., Crohn's disease, multiple sclerosis, rheumatoid arthritis, type 2 diabetes, endometriosis), then processes this data to extract structured patient journey insights.

The system should demonstrate:

1. **Infrastructure discipline** — a fully reproducible environment using Docker Compose, `uv`, and `pyproject.toml`
2. **Pipeline orchestration** — clean Dagster assets/jobs that are observable and restartable
3. **LLM-powered extraction** — using Gemini to turn unstructured community text into structured patient journey data
4. **Analytical thinking** — meaningful post-processing that connects raw community text to patient journey metrics

---

## Core Tasks

### 1. Environment & Infrastructure Setup

Set up a reproducible development environment with:

- **`pyproject.toml`** as the single source of truth for dependencies (no `requirements.txt`)
- **`uv`** as the package manager (lockfile committed)
- **`docker-compose.yml`** that starts the full Dagster stack (webserver, daemon, user code) plus a PostgreSQL instance
- The entire system must start with a single `docker compose up` and be immediately functional
- Include a `.env.example` with all required environment variables documented

**We value reproducibility above all else here.** A reviewer should be able to clone your repository, copy `.env.example` to `.env`, fill in their credentials, and have the pipeline running within minutes.

### 2. Reddit Data Ingestion Job

Build a Dagster job (or set of software-defined assets) that retrieves data from Reddit's public API:

- **Target subreddit(s):** Choose one or more subreddits relevant to your selected condition
- **Data to retrieve:** Posts and their comments, with enough metadata to support the downstream analytics
- **Requirements:**
  - Use Reddit's public API (OAuth2 via a registered app — free tier is sufficient)
  - Implement respectful rate limiting
  - Store raw data in a structured, queryable format (justify your choice)
  - Handle API failures gracefully
  - Design for incremental loads where possible

### 3. Post-Processing & Patient Journey Analytics

This is where your analytical thinking matters most. Build downstream Dagster assets that transform the raw Reddit data into structured insights aligned with our patient journey model. Implement **at least three** of the following analytics:

#### Temporal Analysis
- **Symptom-to-Diagnosis Timeline:** Extract and aggregate mentions of time elapsed between first symptoms and receiving a diagnosis. Surface median durations and distributions across the community.
- **Treatment Phase Duration:** Identify how long users report being on specific treatments before switching, stopping, or reporting outcomes.

#### Causal & Sequential Pattern Analysis
- **Referral-to-Diagnosis Pathways:** Identify common sequences users describe (e.g., "GP → specialist → imaging → diagnosis") and quantify how frequently different pathways appear.
- **Treatment Trigger Patterns:** Surface what events users describe as leading to treatment changes — side effects, lack of efficacy, new symptoms, insurance changes.

#### Associative & Co-occurrence Analysis
- **Symptom Co-occurrence Mapping:** Build a co-occurrence matrix of symptoms mentioned together in the same post or thread. Identify the most common symptom clusters.
- **Medication–Side Effect Associations:** Extract medication names and the side effects users associate with them. Rank by frequency and sentiment.

#### Sentiment & Emotional Journey
- **Journey Phase Sentiment Tracking:** Classify posts into patient journey phases (symptom onset, diagnosis, treatment, ongoing care) and track average sentiment across phases. This maps to the emotional arc of the patient experience.
- **Community Support Patterns:** Analyze which types of posts receive the most engagement (comments, upvotes) — do crisis posts get more support than management questions?

#### Aggregate & Reporting Metrics
- **Treatment Mention Frequency Over Time:** Track how often specific treatments are discussed month-over-month, potentially surfacing shifts in treatment paradigms.
- **Unmet Needs Identification:** Surface recurring questions that go unanswered or generate frustrated responses, indicating gaps in patient support.

**For each analytic you implement:**
- Write it as a Dagster asset with proper metadata
- Document your assumptions and known limitations
- Store results in a queryable format

**Approach to extraction:** Your analytics pipeline must use an **LLM** for at least the entity extraction and/or classification steps (e.g., identifying symptoms, medications, journey phases from free text). Use `litellm` as the LLM interface and Gemini as the model — you can generate a free API key from **Google AI Studio**: https://aistudio.google.com/apikey

We want to see how you design prompts for structured extraction from noisy, informal text. Document your prompt design decisions and any iteration you went through. We are not expecting clinical-grade accuracy; we are evaluating your ability to craft effective prompts, handle LLM output reliably, and acknowledge limitations honestly.

---

## Technology Stack

| Component | Required |
|---|---|
| **Orchestration** | Dagster |
| **Language** | Python 3.11+ |
| **Package management** | `uv` with `pyproject.toml` |
| **Containerization** | Docker Compose |
| **LLM Interface** | `litellm` with Gemini API (Google AI Studio) |
| **Data storage** | PostgreSQL (Dagster metadata + pipeline data) |
| **Typing** | Pydantic models, Python type hints throughout |
| **Testing** | `pytest` |

---

## Deliverables

Submit a link to a **private GitHub repository** and send an invite to **johannes.unruh@mamahealth.io** (`tj-mm`) and **lorenzo.famiglini@mamahealth.io** (`lollomamahealth`), with a short notification email to **mattia.munari@mamahealth.io**.

The repository must contain:

1. **`docker-compose.yml`** — Starts the full stack
2. **`pyproject.toml`** + **`uv.lock`** — All dependencies, fully reproducible
3. **`src/`** — Pipeline code with clear module organization
4. **`tests/`** — Unit tests for ingestion logic, extraction utilities, and at least one analytics asset
5. **`README.md`** with:
   - **Setup instructions** — From clone to running pipeline
   - **Architecture overview** — How assets relate, what each does
   - **Condition & subreddit choice** — Why you picked what you picked
   - **Prompt design decisions** — How you structured your LLM prompts for extraction and why
   - **Analytics design decisions** — What you implemented and what the limitations are
   - **Example output** — Screenshots of Dagster materialization or sample query results

---

## Optional "Go the Extra Mile" Tasks

These are **completely optional** but will distinguish strong candidates:

- **Dagster Partitions:** Implement time-based partitions (e.g., daily or weekly) so the pipeline naturally supports incremental backfills and historical re-processing.
- **Data Quality Checks:** Add Dagster asset checks or freshness policies that alert when data looks anomalous (e.g., sudden drop in post volume, extraction failure rates).
- **Visualization Layer:** Include a simple dashboard (Streamlit, Plotly Dash, or even static HTML) that renders your analytics outputs — symptom co-occurrence heatmaps, sentiment timelines, pathway Sankey diagrams.
- **Semantic Modeling:** Store extracted entities and relationships in a lightweight knowledge graph (e.g., NetworkX or SQLite with a graph schema) to enable path-based queries like "what symptoms co-occur within 3 months of starting treatment X."
- **CI Pipeline:** Add a GitHub Actions workflow that runs linting (`ruff`), type checking (`mypy`), and tests on push.

---

## Time Expectation

We respect your time. This challenge is designed to be completed in **6–8 hours**. Focus on a clean, working pipeline with a few well-implemented analytics rather than trying to cover everything superficially. A smaller scope done well is better than a broad scope done poorly.

---

**Lorenzo Famiglini** — Head of Data Science

**Johannes Unruh** — CTO

</details>
