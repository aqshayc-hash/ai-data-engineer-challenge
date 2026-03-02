# Reddit Data Ingestion Implementation

## Overview

The Reddit data ingestion pipeline fetches posts and comments from configured subreddits using the Reddit API, with proper error handling, rate limiting, and structured data models.

## Architecture

### Components

1. **RedditClient** (`reddit_client.py`)
   - Wrapper around PRAW (Python Reddit API Wrapper)
   - Handles authentication and API communication
   - Implements rate limiting (respects configured requests/minute)
   - Graceful error handling with logging

2. **Data Models** (`models.py`)
   - `RedditPost`: Represents a Reddit post with metadata
   - `RedditComment`: Represents a comment with context
   - `PatientJourneyEvent`: Extracted structured insights (for later use)

3. **Dagster Assets** (`assets/reddit_ingestion.py`)
   - `reddit_client`: Initializes and caches the API client
   - `raw_posts`: Fetches posts only
   - `posts_with_comments`: Fetches complete posts with comments
   - `raw_posts_json`: Archives raw data as JSON
   - `posts_metadata`: Computes ingestion statistics

## Setup

### 1. Register Reddit App

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create Another App" at the bottom
3. Fill in form:
   - **name**: "mama-health-ai-challenge"
   - **type**: Select "script"
   - **description**: "AI data engineer challenge - patient journey analysis"
   - **redirect uri**: http://localhost:3000 (not needed for script type)
4. Click "Create app"
5. Copy:
   - Client ID (shown under app name)
   - Client Secret
6. Add to `.env`:
   ```
   REDDIT_CLIENT_ID=your_id_here
   REDDIT_CLIENT_SECRET=your_secret_here
   REDDIT_USER_AGENT=mama-health-ai-challenge/0.1.0 (contact: your_email@example.com)
   ```

### 2. Configure in `.env`

```env
# Reddit API
REDDIT_CLIENT_ID=xxxxx
REDDIT_CLIENT_SECRET=xxxxx
REDDIT_USER_AGENT=mama-health-ai-challenge/0.1.0 (yourname@example.com)
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Pipeline
TARGET_SUBREDDIT=Crohns     # Options: Crohns, diabetes, MultipleSclerosis, endometriosis, etc
POSTS_LIMIT=100
COMMENTS_LIMIT=50
REDDIT_RATE_LIMIT_PER_MINUTE=60
```

## Asset Dependencies

```
reddit_client
    ↓
    ├→ raw_posts
    │
    └→ posts_with_comments
           ↓
           ├→ raw_posts_json
           │
           └→ posts_metadata
```

## Running the Pipeline

### Option 1: Dagster UI (Recommended)

```bash
# Start Dagster
docker compose up

# Visit http://localhost:3000

# Trigger reddit_ingestion_job from UI
```

### Option 2: Command Line

```bash
# With uv
uv run dagster job execute -f src/mama_health/dagster_definitions.py -j reddit_ingestion_job

# Or with Docker
docker exec mama-dagster-webserver dagster job execute -f /workspace/src/mama_health/dagster_definitions.py -j reddit_ingestion_job
```

## Data Storage

### Current (In-Memory)
Assets currently return Python objects/dictionaries. For production, add:

### Future Enhancements
1. **PostgreSQL Storage**
   - Create tables: `reddit_posts`, `reddit_comments`
   - Use Dagster's database I/O managers
   - Enable analysis queries across runs

2. **S3/Cloud Storage**
   - Archive raw JSON to cloud storage
   - Organize by date: `s3://bucket/year/month/day/posts.json`

3. **Data Warehouse**
   - Load into BigQuery or Snowflake
   - Enable BI tool integration
   - Long-term trend analysis

## Rate Limiting

The client respects configured rate limits:
- Default: 60 requests/minute
- Configurable: `REDDIT_RATE_LIMIT_PER_MINUTE`
- Automatic backoff between requests

```python
min_interval = 60 / rate_limit_per_minute
# For 60/min: waits ~1 second between requests
```

## Error Handling

### Authentication Errors
```
ValueError: Reddit authentication failed
→ Check REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
```

### Subreddit Not Found
```
ValueError: Cannot access subreddit r/InvalidName
→ Verify subreddit name
→ Check if subreddit is public/searchable
```

### Comment Fetching Issues
- Automatically skips deleted/removed comments
- Logs warnings for problematic comments
- Continues processing remaining comments

## Example Output

### posts_with_comments Asset

```json
[
  {
    "post_id": "abc123",
    "title": "Diagnosed with Crohn's at 25",
    "content": "I was just diagnosed...",
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
        "text": "I was diagnosed at 23, here's what helped...",
        "score": 42,
        "created_at": "2024-01-15T10:30:00",
        "parent_comment_id": null
      }
    ]
  }
]
```

### posts_metadata Asset

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

## Monitoring & Logging

Logs are captured with structured logging:
```
INFO: Successfully fetched 98 posts from r/Crohns
INFO: Fetched 45 comments from post abc123
WARNING: Failed to process comment xyz789: [error details]
```

Check logs:
```bash
# Dagster UI: click into job run → logs
# Command line
docker compose logs -f dagster-daemon
docker compose logs -f dagster-webserver
```

## Next Steps

1. **Data Extraction**: Build LLM-powered extraction for patient journey events
2. **Analytics**: Implement temporal analysis, symptom co-occurrence, etc
3. **Storage**: Add PostgreSQL backend for persistent data
4. **Scheduling**: Configure recurring job runs
5. **Testing**: Add unit and integration tests
