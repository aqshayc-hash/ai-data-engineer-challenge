# Reddit Data Ingestion - Implementation Summary

## ✅ What Was Built

A complete, production-ready Reddit data ingestion pipeline for the mama health AI Data Engineer Challenge.

## Files Created

### Core Components

1. **`src/mama_health/models.py`** - Data Models
   - `RedditPost`: Represents a Reddit post with metadata
   - `RedditComment`: Represents individual comments
   - `PatientJourneyEvent`: Structured patient journey insights (foundation for later use)
   - All models use Pydantic for validation and serialization

2. **`src/mama_health/reddit_client.py`** - Reddit API Client
   - `RedditClient` class wrapping PRAW
   - Authentication with OAuth2
   - Rate limiting (configurable requests/minute)
   - Error handling for API failures
   - Methods:
     - `fetch_posts()`: Get posts from subreddit
     - `fetch_comments()`: Get comments from a post
     - `fetch_posts_with_comments()`: Complete data retrieval

3. **`src/mama_health/assets/reddit_ingestion.py`** - Dagster Assets
   - `reddit_client`: Initializes API client
   - `raw_posts`: Fetches posts only
   - `posts_with_comments`: Complete posts + comments
   - `raw_posts_json`: Archives raw data
   - `posts_metadata`: Ingestion statistics

### Configuration & Infrastructure

4. **`pyproject.toml`** - Updated with all dependencies
   - PRAW for Reddit API
   - litellm and google-generativeai for LLM
   - Dagster for orchestration
   - Pydantic for data validation

5. **`docker-compose.yml`** - Updated with environment variables
   - All Reddit and Gemini credentials passed through
   - Health checks and proper logging

6. **`.env.example`** - Updated with all required variables
   - Reddit API credentials
   - Google API key
   - Pipeline configuration options

### Documentation

7. **`REDDIT_INGESTION.md`** - Complete Implementation Guide
   - Architecture overview
   - Setup instructions (Reddit app registration)
   - Asset dependency diagram
   - Data examples
   - Error handling and troubleshooting
   - Rate limiting details

8. **`validate_setup.py`** - Validation Script
   - Checks environment variables
   - Verifies dependencies installed
   - Tests Reddit authentication
   - Validates subreddit access
   - Confirms Dagster definitions load
   - Provides actionable troubleshooting

### Testing

9. **`tests/test_reddit_ingestion.py`** - Unit Tests
   - Model validation tests
   - RedditClient initialization tests
   - Authentication failure handling
   - Rate limiting verification

## Asset Flow

```
reddit_client (initialization)
    │
    ├─→ raw_posts
    │
    └─→ posts_with_comments
            │
            ├─→ raw_posts_json (archive)
            │
            └─→ posts_metadata (statistics)
```

## Key Features

### ✅ Reproducibility
- Single source of truth: `pyproject.toml`
- Configuration via `.env`
- Docker Compose for complete environment
- Validation script to verify setup

### ✅ Error Handling
- Graceful failures with detailed logging
- Skips deleted/removed comments
- Validates subreddit existence
- Handles API rate limits
- Clear error messages for troubleshooting

### ✅ Rate Limiting
- Configurable requests per minute
- Automatic backoff between requests
- Respects Reddit's API guidelines

### ✅ Data Quality
- Pydantic models for validation
- Timestamp conversion (UTC)
- Metadata enrichment (post score, comment count, etc.)
- Structured comment hierarchies

## How to Use

### 1. Quick Setup

```bash
# Copy environment template
copy .env.example .env

# Edit .env with Reddit credentials from:
# https://www.reddit.com/prefs/apps
```

See `REDDIT_INGESTION.md` for detailed Reddit app registration steps.

### 2. Run Validation

```bash
# Verify setup before starting Docker
uv run python validate_setup.py
```

### 3. Start Dagster

```bash
# Start Docker Compose
docker compose up

# Visit http://localhost:3000
```

### 4. Trigger Job

In Dagster UI:
1. Click "reddit_ingestion_job"
2. Click "Materialize"
3. Watch assets execute in order
4. View logs and outputs

### 5. View Results

Each asset produces outputs:
- **raw_posts**: List of post dictionaries
- **posts_with_comments**: Posts with nested comments
- **raw_posts_json**: Full JSON dump for archival
- **posts_metadata**: Statistics (post count, avg score, date range, etc)

## Configuration Options

In `.env`:

```env
# Target analysis
TARGET_SUBREDDIT=Crohns              # Change to any health-related subreddit
POSTS_LIMIT=100                      # Number of posts to fetch
COMMENTS_LIMIT=50                    # Comments per post
REDDIT_SEARCH_LIMIT_DAYS=30         # How far back to search

# Rate limiting
REDDIT_RATE_LIMIT_PER_MINUTE=60     # API requests per minute
```

### Tested Subreddit Values
- `Crohns`
- `diabetes`
- `MultipleSclerosis`
- `rheumatoidarthritis`
- `endometriosis`
- `asthma`
- `Eczema`
- Or any public health-related subreddit

## Example Output

### posts_with_comments
```json
[
  {
    "post_id": "abc123",
    "title": "Diagnosed with Crohn's at 25",
    "content": "I was just diagnosed and overwhelmed...",
    "author": "patient_user",
    "subreddit": "Crohns",
    "score": 156,
    "num_comments": 34,
    "created_at": "2024-01-15T08:00:00",
    "url": "https://reddit.com/r/Crohns/...",
    "comments": [
      {
        "comment_id": "xyz789",
        "post_id": "abc123",
        "author": "responder123",
        "text": "I was diagnosed at 23...",
        "score": 42,
        "created_at": "2024-01-15T10:30:00",
        "parent_comment_id": null
      }
    ]
  }
]
```

### posts_metadata
```json
{
  "ingestion_timestamp": "2024-01-15T14:30:00Z",
  "subreddit": "Crohns",
  "total_posts": 98,
  "total_comments": 2847,
  "avg_comments_per_post": 29.05,
  "total_score": 18374,
  "avg_post_score": 187.49,
  "date_range": {
    "earliest": "2023-12-15T09:00:00",
    "latest": "2024-01-15T12:00:00"
  }
}
```

## Testing

### Run Unit Tests
```bash
# With uv
uv run pytest tests/test_reddit_ingestion.py -v

# Or with Docker
docker exec mama-dagster-webserver pytest tests/
```

### Run Validation Script
```bash
# Quick pre-flight checks
uv run python validate_setup.py
```

## Troubleshooting

### Reddit Authentication Failed
1. Verify `.env` has `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
2. Get credentials from https://www.reddit.com/prefs/apps
3. Check that `REDDIT_USER_AGENT` is set (format: `app-name/version (contact: email)`)

### Subreddit Not Found
1. Check `TARGET_SUBREDDIT` spelling in `.env`
2. Verify it's a public subreddit
3. Try with a known subreddit: `Crohns`, `diabetes`, etc
4. Check [r/ + name] in Reddit to ensure it exists

### Port 3000 Already in Use
1. Edit `docker-compose.yml`
2. Change `DAGSTER_WEBSERVER_PORT=3001` (or another port)
3. Restart: `docker compose up`

### See All Logs
```bash
docker compose logs -f dagster-webserver
docker compose logs -f dagster-daemon
docker compose logs -f postgres
```

## Next Steps

After successfully running the ingestion pipeline:

1. **LLM-Powered Extraction** (Next Phase)
   - Use Gemini to extract structured patient journey events
   - Parse medications, symptoms, diagnoses from free text
   - Build prompt templates for reliable extraction

2. **Patient Journey Analytics** (Phase 3)
   - Symptom-to-diagnosis timelines
   - Treatment efficacy patterns
   - Medication side effect associations
   - Sentiment analysis across journey phases

3. **Data Persistence** (Phase 4)
   - Store posts/comments in PostgreSQL
   - Enable historical analysis
   - Track changes over time

4. **Scheduling** (Phase 5)
   - Configure periodic job runs
   - Monitor data freshness
   - Handle incremental updates

## Code Structure

```
src/mama_health/
├── __init__.py
├── config.py              # Pydantic configuration models
├── models.py              # Data models (Post, Comment, Event)
├── reddit_client.py       # PRAW wrapper with rate limiting
├── dagster_definitions.py # Main Dagster definitions
└── assets/
    ├── __init__.py
    └── reddit_ingestion.py # Dagster assets for ingestion
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | Dagster 1.7+ |
| **Reddit API** | PRAW 7.7+ |
| **HTTP/API** | httpx, requests |
| **Data Models** | Pydantic 2.0+ |
| **Configuration** | pydantic-settings |
| **Logging** | Python logging |
| **Testing** | pytest |
| **Storage** | PostgreSQL (future) |
| **LLM** | litellm + Google Gemini (future) |

## Validation Checklist

- [x] RedditClient authenticates with API
- [x] Rate limiting prevents API throttling
- [x] Posts and comments are properly structured
- [x] Error handling for deleted/removed content
- [x] Dagster assets materialize successfully
- [x] Data is JSON serializable
- [x] Logging captures execution details
- [x] Configuration is flexible
- [x] Reproducible setup with docker-compose
- [x] Comprehensive documentation

## Support

For issues:
1. Run `validate_setup.py` to diagnose problems
2. Check `REDDIT_INGESTION.md` for detailed troubleshooting
3. Review Dagster logs: `docker compose logs`
4. Verify `.env` configuration
