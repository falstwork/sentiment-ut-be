from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sentiment UT API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentiment_ut.db"

    # YouTube API
    YOUTUBE_API_KEY: Optional[str] = None

    # Twitter API
    TWITTER_BEARER_TOKEN: Optional[str] = None

    # Reddit API
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "SentimentUT/1.0"

    # Scheduler
    FETCH_INTERVAL_HOURS: int = 1

    # Keyword extraction
    KEYWORD_LANGUAGE: str = "id"  # Indonesian
    KEYWORD_MAX_KEYWORDS: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
