# Setup Guide

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- GitHub Copilot or a text editor (VS Code recommended)

## Quick Start

### 1. Clone and Navigate to Project
```bash
cd c:\Users\srini\Desktop\ai-data-engineer-challenge
```

### 2. Set Up Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials:
# - REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET (from https://www.reddit.com/prefs/apps)
# - GOOGLE_API_KEY (from https://aistudio.google.com/apikey)
```

### 3. Install `uv` Package Manager
If you don't have `uv` installed:
```bash
# on Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# or on other systems
curl -s https://astral.sh/uv/install.sh | sh
```

### 4. Create Python Virtual Environment with `uv`
```bash
# Create and sync dependencies
uv venv
uv sync
```

### 5. Start Dagster with Docker Compose
```bash
# Make sure .env file is properly configured
docker compose up
```

The system will:
- Start PostgreSQL database (with health checks)
- Start Dagster webserver (accessible at http://localhost:3000)
- Start Dagster daemon for job orchestration

### 6. Access Dagster UI
Open your browser and navigate to:
```
http://localhost:3000
```

## Environment Variables Explained

### Database Configuration
- `POSTGRES_USER`: Database user (default: dagster)
- `POSTGRES_PASSWORD`: Database password (CHANGE IN PRODUCTION)
- `POSTGRES_DB`: Database name (default: mama_health)
- `POSTGRES_PORT`: Database port (default: 5432)

### Reddit API
Get credentials from: https://www.reddit.com/prefs/apps
- `REDDIT_CLIENT_ID`: Your OAuth app client ID
- `REDDIT_CLIENT_SECRET`: Your OAuth app secret
- `REDDIT_USER_AGENT`: Custom user agent for API requests
- `REDDIT_USERNAME`: Your Reddit username (for authenticated requests if needed)
- `REDDIT_PASSWORD`: Your Reddit password (for authenticated requests if needed)

### Google Gemini API
Get free API key from: https://aistudio.google.com/apikey
- `GOOGLE_API_KEY`: Your Gemini API key

### Pipeline Configuration
- `TARGET_SUBREDDIT`: Which subreddit to analyze (e.g., Crohns, diabetes, MultipleSclerosis)
- `POSTS_LIMIT`: Maximum posts to retrieve
- `COMMENTS_LIMIT`: Maximum comments per post
- `SEARCH_LIMIT_DAYS`: How many days back to search

### LLM Configuration
- `LLM_MODEL`: Model to use (default: gemini-pro)
- `LLM_TEMPERATURE`: Temperature for LLM (0.0-1.0, lower = more deterministic)
- `LLM_MAX_TOKENS`: Maximum tokens in LLM response

## Troubleshooting

### Port Already in Use
If port 3000 is already in use:
```bash
docker compose down
# Edit docker-compose.yml and change DAGSTER_WEBSERVER_PORT=3001 (or another port)
docker compose up
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker compose logs postgres

# View database creation logs
docker compose logs -f postgres
```

### Permission Issues on Windows
If you get permission errors running PowerShell scripts:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Project Structure

```
.
├── pyproject.toml          # Dependencies and project metadata
├── docker-compose.yml      # Docker services configuration
├── workspace.yaml          # Dagster workspace configuration
├── .env.example           # Environment variables template
├── .env                   # Actual environment (create from .env.example)
├── .gitignore             # Git ignore rules
└── src/
    └── mama_health/
        ├── __init__.py
        ├── config.py      # Configuration management
        └── dagster_definitions.py  # Main Dagster definitions
```

## Next Steps

1. Create Dagster assets for Reddit data ingestion
2. Implement LLM-based text extraction
3. Build patient journey analytics
4. Create comprehensive testing

See README.md for detailed requirements.
