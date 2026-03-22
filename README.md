# Sentiment UT Backend

Backend API untuk Sentimen Analisis Dashboard Universitas Terbuka.

## Tech Stack

- **Framework**: FastAPI (Python 3.9+)
- **Database**: SQLite with SQLAlchemy (async)
- **Sentiment Analysis**: Sastrawi (Indonesian NLP)
- **Keyword Extraction**: YAKE
- **Scheduler**: APScheduler

## Installation

1. Buat virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment file dan isi API keys:
```bash
cp .env.example .env
```

4. Edit `.env` dengan API keys yang diperlukan:
- `YOUTUBE_API_KEY` - YouTube Data API v3
- `TWITTER_BEARER_TOKEN` - Twitter/X API v2
- `REDDIT_CLIENT_ID` - Reddit API
- `REDDIT_CLIENT_SECRET` - Reddit API

## Running

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Setelah server berjalan, buka:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/analytics/summary` | Sentiment summary |
| GET | `/api/analytics/trends` | Sentiment trends |
| GET | `/api/analytics/keywords` | Top keywords |
| GET | `/api/analytics/volume` | Volume over time |
| GET | `/api/analytics/by-source` | By source breakdown |
| GET | `/api/analytics/trending` | Trending topics |
| GET | `/api/mentions/recent` | Recent mentions |
| GET | `/api/mentions/{id}` | Mention detail |
| POST | `/api/sources/fetch` | Trigger manual fetch |

## Database Schema

- `sources` - Data sources (YouTube, Twitter, Reddit, RSS)
- `raw_mentions` - Raw fetched data
- `processed_mentions` - Sentiment analysis results
- `hourly_aggregates` - Hourly statistics
- `daily_aggregates` - Daily statistics
- `fetch_logs` - Fetch history

## Scheduler

Scheduler otomatis fetch data setiap 1 jam (configurable via `FETCH_INTERVAL_HOURS`).

## Demo Mode

Jika API keys tidak dikonfigurasi, sistem akan menggunakan mock data untuk demo.
