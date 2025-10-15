# Authenticity Ratio (AR) Tool

## Overview
Authenticity Ratio (AR) is a KPI that measures authentic vs. inauthentic brand-linked content across channels. It reframes authenticity as a brand health metric for CMOs/boards.

## Formula
**Core:** AR = (Verified Authentic Content ÷ Total Brand-Linked Content) × 100

**Extended (with suspect):** AR = (A + 0.5S) ÷ (A + S + I) × 100
- A = Authentic, S = Suspect, I = Inauthentic

## 5D Trust Dimensions
Content is scored on:
- **Provenance** – origin, traceability, metadata (20%)
- **Verification** – factual accuracy vs. trusted DBs (20%)
- **Transparency** – disclosures, clarity (20%)
- **Coherence** – consistency across channels (20%)
- **Resonance** – cultural fit, organic engagement (20%)

## Pipeline
Ingest → Normalize → Enrich (metadata + fact-check) → Score (5D rubric) → Classify (A/S/I) → Compute AR → Report

## Project Structure
```
AR/
├── config/                 # Configuration files
├── data/                   # Data storage and processing
├── ingestion/              # Data collection modules
├── scoring/                # 5D scoring and classification
├── reporting/              # Report generation and dashboards
├── utils/                  # Shared utilities and helpers
├── tests/                  # Test files
├── docs/                   # Documentation
└── scripts/                # Deployment and maintenance scripts
```

## Quick Start
1. Set up configuration in `config/`
2. Run data ingestion: `python -m ingestion.reddit_crawler`
3. Process and score content: `python -m scoring.pipeline`
4. Generate reports: `python -m reporting.generator`

## Database
Uses AWS Athena with S3 storage for normalized content and scores.

## Brave Search integration

This project includes a Brave Search ingestion module and a small Streamlit web UI for quick runs.

Brave API configuration

- `BRAVE_API_KEY`: Your Brave subscription token or API key. If set, the pipeline will prefer the API.
- `BRAVE_API_ENDPOINT`: Optional API endpoint (defaults to `https://api.search.brave.com/res/v1/web/search`).
- `BRAVE_API_AUTH`: Auth style for API calls. Supported values:
	- `subscription-token` (default) — sends header `X-Subscription-Token: <key>`
	- `x-api-key` — sends header `x-api-key: <key>`
	- `bearer` — sends `Authorization: Bearer <key>`
	- `query-param` — appends `apikey=<key>` to the query string
- `BRAVE_REQUEST_INTERVAL`: Minimum seconds to wait between outbound Brave requests (default `1.0`)
- `BRAVE_ALLOW_HTML_FALLBACK`: If set to `1` the client will fall back to HTML scraping when the API returns no results (default: `0` — disabled when API key present)
- `BRAVE_USE_PLAYWRIGHT`: If set to `1`, the client will attempt a Playwright-rendered fetch when HTML scraping is needed (install Playwright separately)

Quick examples

- Using the API (recommended):

```bash
export BRAVE_API_KEY="<your_key_here>"
export BRAVE_API_AUTH="subscription-token"
export BRAVE_REQUEST_INTERVAL=1.0
python scripts/debug_brave.py --query "nike" --size 4
```

- Enable Playwright-based rendering (heavy):

```bash
pip install playwright
playwright install
export BRAVE_USE_PLAYWRIGHT=1
export BRAVE_ALLOW_HTML_FALLBACK=1
python scripts/debug_brave.py --query "nike" --size 4
```

Notes

- When `BRAVE_API_KEY` is present the client prefers API responses and will not fall back to HTML scraping unless `BRAVE_ALLOW_HTML_FALLBACK=1`.
- Rate limiting is enforced by `BRAVE_REQUEST_INTERVAL` to respect one request per second default.


## YouTube Data API integration

This project also includes a YouTube ingestion module that talks to the YouTube Data API v3 for searching videos and fetching comments. The YouTube integration is API-key based and uses the Google API client under the hood.

YouTube configuration

- `YOUTUBE_API_KEY`: Your YouTube Data API v3 developer key (required for video search and comment fetches). If not present, the `YouTubeScraper` will raise a configuration error.
- `youtube_rate_limit`: Configured in `config/settings.py` (defaults to `60` requests per minute); the scraper will respect this rate by inserting sleeps between calls.
- `include_comments`: When converting videos to normalized content you can choose to include top-level comments (configurable by the scraper helper functions).

Quick examples

- Basic search with the project's debug runner (recommended for dev):

```bash
export YOUTUBE_API_KEY="<your_key_here>"
python -c "from ingestion.youtube_scraper import YouTubeScraper; print(YouTubeScraper().search_videos('nike', max_results=3))"
```

- Convert found videos (and comments) into normalized content (used by pipeline):

```python
from ingestion.youtube_scraper import YouTubeScraper
yt = YouTubeScraper()
videos = yt.search_videos('nike', max_results=5)
# Convert videos to NormalizedContent objects (used by the scoring pipeline)
normalized = yt.convert_videos_to_normalized(videos, brand_id='nike', run_id='localtest', include_comments=True)
```

Notes

- The `google-api-python-client` package is required (already referenced in the project). Ensure your virtualenv has it installed.
- Comment fetching is rate-limited by the same `youtube_rate_limit` setting — fetching many comments across many videos may be slow or hit quota limits; consider sampling or limiting comments per video for large runs.


