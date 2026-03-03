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

## Project Structure

We expect a clean, navigable repository with logical module separation. How you organize it is up to you — just make sure a reviewer can quickly understand what lives where.

---

## What We're Looking For

- **Reproducibility:** `docker compose up` works. No hidden setup steps, no missing environment variables.
- **Clean Python Code:** Well-organized, typed, readable. Pydantic models for data schemas. Docstrings where they matter.
- **Dagster Proficiency:** Proper use of assets, resources, and metadata. The pipeline should tell a clear story in the Dagster UI.
- **Prompt Engineering:** Thoughtful prompts that produce consistent, structured output from messy Reddit text. We want to see how you handle ambiguity, enforce output schemas, and iterate on prompt design.
- **Analytical Substance:** The post-processing should produce insights a healthcare analyst would find genuinely useful — not just token counts.
- **Testing:** Tests that verify meaningful behavior.

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
